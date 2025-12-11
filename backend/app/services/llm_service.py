import os
import json
from typing import Dict, Any, Optional
from openai import OpenAI
from app.core.config import settings

class QwenService:
    def __init__(self):
        """
        初始化 QwenService 服务。
        
        功能：
            从配置中加载 LLM 设置，初始化 OpenAI 客户端。
            支持动态切换 API 源 (OpenRouter, DashScope, Bohrium)。
        """
        try:
            config = settings.get_llm_config()
            self.client = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"]
            )
            self.model = config["model"]
            self.provider = settings.LLM_PROVIDER
            print(f"✓ LLM 服务初始化成功 | 源: {self.provider} | 模型: {self.model}")
        except Exception as e:
            print(f"✗ LLM 服务初始化失败: {e}")
            self.client = None
            self.model = ""

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

    def call_llm(self, prompt: str, model: str = None) -> tuple[str, Dict[str, Any]]:
        """
        调用 LLM API 执行请求 (包含重试机制)。
        支持动态切换模型，并解析 OpenRouter 的成本与缓存信息。

        Args:
            prompt (str): 发送给 LLM 的完整提示词字符串。
            model (str, optional): 指定使用的模型。如果为 None，使用默认配置的模型。

        Returns:
            tuple[str, Dict[str, Any]]: (内容字符串, 使用统计字典)。
                                        统计字典包含:
                                        - 'prompt_tokens': 输入 Token 数
                                        - 'completion_tokens': 输出 Token 数
                                        - 'total_tokens': 总 Token 数
                                        - 'cost': 预估或实际成本 (USD)
                                        - 'cache_hit_tokens': 缓存命中的 Token 数
                                        - 'model': 实际使用的模型名称
                                        如果调用失败，返回 ("{}", {})。
        """
        import time
        
        if not self.client:
            print("✗ LLM 客户端未初始化，无法执行请求")
            return "{}", {}

        # 使用指定模型或默认模型
        target_model = model if model else self.model
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries + 1):
            try:
                completion = self.client.chat.completions.create(
                    model=target_model,
                    messages=[
                        {"role": "system", "content": self.read_prompt("system.md")},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=1,
                    response_format={"type": "json_object"} # 强制JSON格式
                )
                response = completion.choices[0].message.content
                
                # 解析 Usage 和 Cost
                usage = completion.usage
                usage_dict = {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                    "model": target_model
                }

                # 尝试解析 OpenRouter 特有字段 (cost, cache)
                # 注意: OpenAI Python 客户端可能将额外字段放在 model_extra 或直接属性中
                # 这里的处理尝试兼容不同的返回结构
                
                # 1. 尝试获取缓存命中数
                # OpenRouter 通常在 prompt_tokens_details 中返回 cached_tokens
                if usage and hasattr(usage, 'prompt_tokens_details') and usage.prompt_tokens_details:
                     # 检查是否为对象或字典
                    details = usage.prompt_tokens_details
                    if isinstance(details, dict):
                        usage_dict["cache_hit_tokens"] = details.get("cached_tokens", 0)
                    elif hasattr(details, 'cached_tokens'):
                        usage_dict["cache_hit_tokens"] = details.cached_tokens
                    else:
                        usage_dict["cache_hit_tokens"] = 0
                else:
                    usage_dict["cache_hit_tokens"] = 0

                # 2. 尝试获取 Cost (OpenRouter 特有)
                # 某些客户端版本可能将非标准字段放在 extra_fields 或 model_extra
                # 如果无法直接获取，后续 WorkflowEngine 会根据 Token 计算
                if hasattr(completion, 'usage') and isinstance(completion.usage, dict):
                     usage_dict["cost"] = completion.usage.get("cost", 0.0)
                elif hasattr(completion, 'model_extra') and completion.model_extra:
                     usage_info = completion.model_extra.get('usage', {})
                     if isinstance(usage_info, dict):
                         usage_dict["cost"] = usage_info.get('cost', 0.0)
                
                # 清理可能的 markdown 代码块标记
                response = response.strip()
                if response.startswith("```"):
                    lines = response.split('\n')
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    response = '\n'.join(lines)
                
                return response.strip(), usage_dict
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Rate limit" in error_str:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ LLM 速率限制 (429), {delay}秒后重试... ({attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                
                print(f"❌ LLM 调用错误: {e}")
                # 非 429 错误或重试耗尽，返回空
                return "{}", {}
                
        return "{}", {}

    def filter_paper(self, paper: Dict, user_profile: str) -> Dict[str, Any]:
        """
        使用 LLM 检查论文是否与用户画像相关。

        Args:
            paper (Dict): 论文元数据字典。
            user_profile (str): 用户画像字符串。

        Returns:
            Dict[str, Any]: 筛选结果字典 (包含 _usage)。
        """
        template = self.read_prompt("filter.md")
        prompt = template.format(
            user_profile=user_profile,
            title=paper.get("title", ""),
            abstract=paper.get("abstract", ""),
            category=paper.get("category", "")
        )
        
        # 使用便宜的模型进行筛选
        response, usage = self.call_llm(prompt, model=settings.OPENROUTER_MODEL_CHEAP)
        try:
            result = json.loads(response)
            result["_usage"] = usage # 注入 usage 信息
            return result
        except json.JSONDecodeError:
            print(f"filter 解析 JSON 错误: {response}")
            return {"is_relevant": False, "score": 0, "reason": "Parse Error", "_usage": usage}

    def analyze_paper(self, abstract: str, comment: str = "") -> Dict[str, Any]:
        """
        使用 LLM 分析论文详情。

        Args:
            abstract (str): 论文摘要。
            comment (str): 论文备注 (可选)。

        Returns:
            Dict[str, Any]: 分析结果字典 (包含 _usage)。
        """
        template = self.read_prompt("analyze.md")
        
        prompt = template.format(
            abstract=abstract,
            comment=comment
        )
        
        # 使用便宜的模型进行分析
        response, usage = self.call_llm(prompt, model=settings.OPENROUTER_MODEL_CHEAP)
        try:
            result = json.loads(response)
            result["_usage"] = usage
            return result
        except json.JSONDecodeError:
            print(f"analyze 解析 JSON 错误: {response}")
            return {"_usage": usage}

    def generate_report(self, papers: list, user_profile: str) -> Dict[str, Any]:
        """
        使用 LLM 生成每日报告。

        Args:
            papers (list): 论文列表。
            user_profile (str): 用户画像字符串。

        Returns:
            Dict[str, Any]: 报告生成结果 (包含 _usage)。
        """
        template = self.read_prompt("report.md")
        
        # 为提示词格式化论文列表
        papers_text = ""
        for p in papers:
            papers_text += f"ID: {p['id']}\nTitle: {p['title']}\nAbstract: {p['abstract'][:200]}...\n\n"
            
        # 使用 replace 替代 format，避免 JSON 大括号冲突
        from datetime import datetime
        date_str = datetime.now().strftime("%Y/%m/%d")
        prompt = template.replace("{user_profile}", user_profile).replace("{papers}", papers_text).replace("{date}", date_str)
        
        # 使用高性能模型生成报告
        response, usage = self.call_llm(prompt, model=settings.OPENROUTER_MODEL_PERFORMANCE)
        try:
            result = json.loads(response)
            result["_usage"] = usage
            return result
        except json.JSONDecodeError:
            print(f"report 解析 JSON 错误: {response}")
            return {"_usage": usage}

llm_service = QwenService()
