import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class QwenService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = "qwen3-max"

    def _read_prompt(self, filename: str) -> str:
        """从文件读取提示词模板"""
        # backend/util/llm_service.py -> backend/prompt
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _call_llm(self, prompt: str) -> str:
        """调用Qwen API"""
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"} # 强制JSON格式(如果支持),或仅依赖提示词
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"LLM Call Error: {e}")
            return "{}"

    def filter_paper(self, paper: Dict, user_profile: str) -> Dict[str, Any]:
        """检查论文是否相关"""
        template = self._read_prompt("filter.md")
        prompt = template.format(
            user_profile=user_profile,
            title=paper.get("title", ""),
            abstract=paper.get("details", {}).get("abstract", ""),
            category=paper.get("category", "")
        )
        
        response = self._call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in filter: {response}")
            return {"is_relevant": False, "score": 0, "reason": "Parse Error"}

    def analyze_paper(self, paper: Dict, user_profile: str) -> Dict[str, Any]:
        """分析论文详情"""
        template = self._read_prompt("analyze.md")
        prompt = template.format(
            user_profile=user_profile,
            title=paper.get("title", ""),
            abstract=paper.get("details", {}).get("abstract", "")
        )
        
        response = self._call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in analyze: {response}")
            return {}

    def generate_report(self, papers: list, user_profile: str) -> Dict[str, Any]:
        """生成每日报告"""
        template = self._read_prompt("report.md")
        
        # 为提示词格式化论文列表
        papers_text = ""
        for p in papers:
            papers_text += f"ID: {p['id']}\nTitle: {p['title']}\nAbstract: {p['details']['abstract'][:200]}...\n\n"
            
        prompt = template.format(
            user_profile=user_profile,
            papers=papers_text
        )
        
        response = self._call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in report: {response}")
            return {}

llm_service = QwenService()
