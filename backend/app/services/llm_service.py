import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings

class QwenService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.model = "qwen3-max"

    def read_prompt(self, filename: str) -> str:
        """
        从文件系统中读取提示词模板。

        Args:
            filename (str): 提示词模板的文件名 (例如 "filter.md")。

        Returns:
            str: 提示词模板的内容。
        """
        # backend/services/llm_service.py -> backend/prompt
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompt", filename)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def call_llm(self, prompt: str) -> str:
        """
        调用 Qwen API 执行 LLM 请求。

        Args:
            prompt (str): 发送给 LLM 的完整提示词字符串。

        Returns:
            str: LLM 返回的 JSON 格式字符串内容。如果调用失败，返回 "{}"。
        """
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
        """
        使用 LLM 检查论文是否与用户画像相关。

        Args:
            paper (Dict): 包含论文信息的字典 (如 title, abstract, category)。
            user_profile (str): 序列化后的用户画像字符串。

        Returns:
            Dict[str, Any]: 包含过滤结果的字典，例如 {"is_relevant": bool, "score": float, "reason": str}。
                            如果解析失败，返回默认的不相关结果。
        """
        template = self.read_prompt("filter.md")
        prompt = template.format(
            user_profile=user_profile,
            title=paper.get("title", ""),
            abstract=paper.get("abstract", ""),
            category=paper.get("category", "")
        )
        
        response = self.call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in filter: {response}")
            return {"is_relevant": False, "score": 0, "reason": "Parse Error"}

    def analyze_paper(self, paper: Dict, comment: str = "") -> Dict[str, Any]:
        """
        使用 LLM 分析论文详情，提取关键信息 (Public Analysis)。

        Args:
            paper (Dict): 包含论文信息的字典 (如 abstract)。
            comment (str): 论文的评论/备注信息 (用于辅助生成 tags)。

        Returns:
            Dict[str, Any]: 包含分析结果的字典，例如 {"tldr": str, "motivation": str, "method": str, ...}。
                            如果解析失败，返回空字典。
        """
        template = self.read_prompt("analyze.md")
        
        prompt = template.format(
            abstract=paper.get("abstract", ""),
            comment=comment
        )
        
        response = self.call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in analyze: {response}")
            return {}

    def generate_report(self, papers: list, user_profile: str) -> Dict[str, Any]:
        """
        使用 LLM 根据一组论文生成每日报告。

        Args:
            papers (list): 包含多篇论文信息的列表。
            user_profile (str): 序列化后的用户画像字符串。

        Returns:
            Dict[str, Any]: 包含报告内容的字典，例如 {"title": str, "summary": str, "content": List}。
                            如果解析失败，返回空字典。
        """
        template = self.read_prompt("report.md")
        
        # 为提示词格式化论文列表
        papers_text = ""
        for p in papers:
            papers_text += f"ID: {p['id']}\nTitle: {p['title']}\nAbstract: {p['abstract'][:200]}...\n\n"
            
        prompt = template.format(
            user_profile=user_profile,
            papers=papers_text
        )
        
        response = self.call_llm(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"JSON Decode Error in report: {response}")
            return {}

llm_service = QwenService()
