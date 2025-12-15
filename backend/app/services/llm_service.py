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

    def call_llm(self, prompt: str, model: str = None, response_format: Optional[Dict[str, Any]] = {"type": "json_object"}) -> tuple[str, Dict[str, Any]]:
        """
        调用 LLM API 执行请求 (包含重试机制)。
        支持动态切换模型，并解析 OpenRouter 的成本与缓存信息。

        Args:
            prompt (str): 发送给 LLM 的完整提示词字符串。
            model (str, optional): 指定使用的模型。如果为 None，使用默认配置的模型。
            response_format (Dict[str, Any], optional): API 返回格式配置。默认为 {"type": "json_object"}。

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
        import traceback
        
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
                    temperature=1.2,
                    response_format=response_format # 使用传入的格式配置
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
                import traceback
                traceback_str = traceback.format_exc()
                
                if "429" in error_str or "Rate limit" in error_str:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** attempt)
                        print(f"⚠️ LLM 速率限制 (429), {delay}秒后重试... ({attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue
                
                print(f"❌ LLM 调用错误: {e}")
                print(f"🔍 错误堆栈: {traceback_str}")
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
        import time
        import re
        
        current_date = datetime.now().strftime("%Y/%m/%d")
        prompt = template.replace("{user_profile}", user_profile).replace("{papers}", papers_text).replace("{date}", current_date)
        
        # 定义解析辅助函数
        def _parse_report_response(response_text: str) -> Optional[Dict[str, Any]]:
            """
            解析 LLM 返回的 XML 标签格式报告。
            
            Args:
                response_text (str): LLM 返回的原始文本。
                
            Returns:
                Optional[Dict[str, Any]]: 解析后的字典，包含 title, summary, content。解析失败返回 None。
            """
            try:
                # 使用非贪婪匹配提取标签内容，re.DOTALL 允许匹配换行符
                title_match = re.search(r'<title>(.*?)</title>', response_text, re.DOTALL)
                summary_match = re.search(r'<summary>(.*?)</summary>', response_text, re.DOTALL)
                content_match = re.search(r'<content>(.*?)</content>', response_text, re.DOTALL)
                
                if not (title_match and summary_match and content_match):
                    print(f"❌ Report parsing failed. Missing tags. Response preview: {response_text[:200]}...")
                    return None
                
                return {
                    "title": title_match.group(1).strip(),
                    "summary": summary_match.group(1).strip(),
                    "content": content_match.group(1).strip()
                }
            except Exception as e:
                print(f"❌ Report parsing exception: {e}")
                return None

        # 定义重试逻辑
        def try_generate(model_name, retries=3):
            """
            尝试使用指定模型生成报告。
            
            Args:
                model_name (str): 模型名称。
                retries (int): 重试次数。
                
            Returns:
                Optional[Dict[str, Any]]: 生成并解析后的结果字典。
            """
            for i in range(retries):
                print(f"Generating report with {model_name} (Attempt {i+1}/{retries})...")
                # 移除 response_format={"type": "json_object"}，允许自由格式输出
                # 显式传入 None 以覆盖默认的 JSON 模式
                response, usage = self.call_llm(prompt, model=model_name, response_format=None)
                
                if usage and response and response != "{}":
                    parsed_result = _parse_report_response(response)
                    if parsed_result:
                        parsed_result["_usage"] = usage
                        return parsed_result
                
                if i < retries - 1:
                    time.sleep(2) # 重试间隔
            return None

        # 1. 尝试主模型
        result = try_generate(settings.OPENROUTER_MODEL_PERFORMANCE, retries=3)
        
        # 2. 如果主模型失败，尝试备用模型
        if not result:
            print(f"⚠️ Primary model {settings.OPENROUTER_MODEL_PERFORMANCE} failed after 3 attempts. Switching to fallback...")
            fallback_model = "deepseek/deepseek-v3.2"
            result = try_generate(fallback_model, retries=3)
            
        if result:
            # 自动填充 ref_papers (直接使用输入的论文列表 ID)
            result["ref_papers"] = [p['id'] for p in papers]
            # 再次确认 fallback 模型成功日志
            if result.get("_usage", {}).get("model") == "deepseek/deepseek-v3.2":
                 print(f"✓ Report generated successfully with fallback model deepseek/deepseek-v3.2")
            return result
            
        print("❌ All report generation attempts failed.")
        return {"_usage": {}} # 返回空 usage 表示彻底失败

    def extract_categories(self, text: str) -> Dict[str, Any]:
        """
        从自然语言中提取 Arxiv 类别和作者。

        Args:
            text (str): 用户输入的自然语言文本。

        Returns:
            Dict[str, Any]: 包含 categories 和 authors 的字典 (包含 _usage)。
                            - categories: 提取出的 Arxiv 类别列表。
                            - authors: 提取出的作者列表。
        """
        template = self.read_prompt("extract_categories.md")
        prompt = template.replace("{user_input}", text)
        
        # 使用便宜的模型进行提取
        response, usage = self.call_llm(prompt, model=settings.OPENROUTER_MODEL_CHEAP)
        try:
            result = json.loads(response)
            result["_usage"] = usage
            return result
        except json.JSONDecodeError:
            print(f"extract_categories 解析 JSON 错误: {response}")
            # Fallback: 如果解析失败，尝试简单的关键词匹配或返回空
            return {"categories": [], "authors": [], "_usage": usage}

llm_service = QwenService()
