import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "ArxivScout Agent"
    API_V1_STR: str = "/api/v1"
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    # LLM 配置
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")

    # OpenRouter 配置
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-max")

    # DashScope 配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_MODEL: str = os.getenv("DASHSCOPE_MODEL", "qwen3-max")

    # Bohrium 配置
    BOHRIUM_API_KEY: str = os.getenv("BOHRIUM_API_KEY", "")
    BOHRIUM_MODEL: str = os.getenv("BOHRIUM_MODEL", "qwen3-max")

    # 成本控制与模型配置
    # 便宜的模型 (用于分析/筛选)
    OPENROUTER_MODEL_CHEAP: str = os.getenv("OPENROUTER_MODEL_CHEAP", "qwen/qwen-plus")
    # 高性能模型 (用于报告生成)
    OPENROUTER_MODEL_PERFORMANCE: str = os.getenv("OPENROUTER_MODEL_PERFORMANCE", "qwen/qwen3-max")
    
    # 通用模型配置（不绑定特定Provider）
    MODEL_CHEAP: str = os.getenv("MODEL_CHEAP", "qwen-plus")
    MODEL_PERFORMANCE: str = os.getenv("MODEL_PERFORMANCE", "qwen3-max")
    
    # Qwen-Plus 定价 (USD per 1M tokens)
    QWEN_PLUS_PRICE_INPUT: float = float(os.getenv("QWEN_PLUS_PRICE_INPUT", "0.40"))
    QWEN_PLUS_PRICE_OUTPUT: float = float(os.getenv("QWEN_PLUS_PRICE_OUTPUT", "1.20"))
    QWEN_MAX_PRICE_INPUT: float = float(os.getenv("QWEN_MAX_PRICE_INPUT", "1.60")) # 假设价格，需确认
    QWEN_MAX_PRICE_OUTPUT: float = float(os.getenv("QWEN_MAX_PRICE_OUTPUT", "4.80"))
    
    # Bohrium API 定价 (USD per 1M tokens)
    BOHRIUM_PLUS_PRICE_INPUT: float = float(os.getenv("BOHRIUM_PLUS_PRICE_INPUT", "0.40"))
    BOHRIUM_PLUS_PRICE_OUTPUT: float = float(os.getenv("BOHRIUM_PLUS_PRICE_OUTPUT", "1.20"))
    BOHRIUM_MAX_PRICE_INPUT: float = float(os.getenv("BOHRIUM_MAX_PRICE_INPUT", "1.20"))
    BOHRIUM_MAX_PRICE_OUTPUT: float = float(os.getenv("BOHRIUM_MAX_PRICE_OUTPUT", "6.00"))

    # LLM 批量处理配置
    LLM_ANALYSIS_BATCH_SIZE: int = int(os.getenv("LLM_ANALYSIS_BATCH_SIZE", "20"))  # 批量大小
    LLM_ANALYSIS_BATCH_DELAY: int = int(os.getenv("LLM_ANALYSIS_BATCH_DELAY", "60"))  # 批次间延迟（秒）
    LLM_MAX_WORKERS: int = int(os.getenv("LLM_MAX_WORKERS", "2"))  # 最大并发数

    # 兼容旧配置
    ACCESS_KEY: str = os.getenv("ACCESS_KEY", "")

    def get_llm_config(self) -> dict:
        """
        根据环境变量 LLM_PROVIDER 获取对应的 API 配置。
        
        Returns:
            dict: 包含 api_key, base_url, model 的配置字典。
            
        Raises:
            ValueError: 当 LLM_PROVIDER 无效或缺少必要的 API Key 时抛出。
        """
        provider = self.LLM_PROVIDER.lower()
        
        configs = {
            "openrouter": {
                "api_key": self.OPENROUTER_API_KEY,
                "base_url": "https://openrouter.ai/api/v1",
                "model": self.OPENROUTER_MODEL,
            },
            "dashscope": {
                "api_key": self.DASHSCOPE_API_KEY,
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": self.DASHSCOPE_MODEL,
            },
            "bohrium": {
                "api_key": self.BOHRIUM_API_KEY or self.ACCESS_KEY,
                "base_url": "https://openapi.dp.tech/openapi/v1",  # 修正为正确的玻尔API地址
                "model": self.BOHRIUM_MODEL,
            }
        }
        
        if provider not in configs:
            raise ValueError(f"无效的 LLM_PROVIDER: {provider}。可选值: {', '.join(configs.keys())}")
            
        config = configs[provider]
        if not config["api_key"]:
            raise ValueError(f"未设置 {provider} 的 API Key。")
            
        return config
    
    def get_model_pricing(self, model: str) -> dict:
        """
        根据模型名称获取定价信息。
        
        功能说明：
            根据当前配置的 LLM Provider 和模型名称，返回该模型的输入和输出token定价。
            支持 OpenRouter、Bohrium、DashScope 三种 Provider。
            使用模糊匹配查找模型定价，如果找不到则返回默认定价。
        
        Args:
            model (str): 模型名称（如 "qwen-plus", "qwen3-max", "qwen/qwen-plus"）
        
        Returns:
            dict: 包含以下字段的字典：
                - input_price (float): 输入token价格（USD per 1M tokens）
                - output_price (float): 输出token价格（USD per 1M tokens）
        
        示例：
            >>> settings.get_model_pricing("qwen-plus")
            {'input_price': 0.40, 'output_price': 1.20}
        """
        provider = self.LLM_PROVIDER.lower()
        
        # 模型定价映射表
        pricing_map = {
            "openrouter": {
                "qwen-plus": {
                    "input_price": self.QWEN_PLUS_PRICE_INPUT,
                    "output_price": self.QWEN_PLUS_PRICE_OUTPUT
                },
                "qwen3-max": {
                    "input_price": self.QWEN_MAX_PRICE_INPUT,
                    "output_price": self.QWEN_MAX_PRICE_OUTPUT
                }
            },
            "bohrium": {
                "qwen-plus": {
                    "input_price": self.BOHRIUM_PLUS_PRICE_INPUT,
                    "output_price": self.BOHRIUM_PLUS_PRICE_OUTPUT
                },
                "qwen3-max": {
                    "input_price": self.BOHRIUM_MAX_PRICE_INPUT,
                    "output_price": self.BOHRIUM_MAX_PRICE_OUTPUT
                }
            },
            "dashscope": {
                "qwen-plus": {
                    "input_price": self.QWEN_PLUS_PRICE_INPUT,
                    "output_price": self.QWEN_PLUS_PRICE_OUTPUT
                },
                "qwen3-max": {
                    "input_price": self.QWEN_MAX_PRICE_INPUT,
                    "output_price": self.QWEN_MAX_PRICE_OUTPUT
                }
            }
        }
        
        # 获取当前Provider的定价配置
        provider_pricing = pricing_map.get(provider, pricing_map["openrouter"])
        
        # 查找模型定价，使用模糊匹配（支持 "qwen/qwen-plus" 和 "qwen-plus" 两种格式）
        for model_key, pricing in provider_pricing.items():
            if model_key in model or model in model_key:
                return pricing
        
        # 默认返回 qwen-plus 的定价
        return provider_pricing.get("qwen-plus", {"input_price": 0.40, "output_price": 1.20})
    
    # 邮件配置
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 465))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")
    RECIPIENT_EMAILS: str = os.getenv("RECIPIENT_EMAILS", "")

    # 爬虫配置
    CATEGORIES: str = os.getenv("CATEGORIES", "cs.CV,cs.LG,cs.CL,cs.AI")
    
    # 定时任务配置
    DAILY_REPORT_TIME: str = os.getenv("DAILY_REPORT_TIME", "09:30")
    
    def get_daily_report_time(self) -> tuple[int, int]:
        """
        解析每日报告时间配置。
        
        Args:
            None
        
        Returns:
            tuple[int, int]: (小时, 分钟)，例如 (9, 30) 表示 09:30
        
        Raises:
            ValueError: 当时间格式不正确时抛出
        """
        try:
            time_parts = self.DAILY_REPORT_TIME.split(":")
            if len(time_parts) != 2:
                raise ValueError(f"时间格式错误: {self.DAILY_REPORT_TIME}，应为 HH:MM 格式")
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            # 验证时间范围
            if not (0 <= hour <= 23):
                raise ValueError(f"小时必须在 0-23 之间，当前值: {hour}")
            if not (0 <= minute <= 59):
                raise ValueError(f"分钟必须在 0-59 之间，当前值: {minute}")
            
            return hour, minute
        except Exception as e:
            print(f"解析 DAILY_REPORT_TIME 失败: {e}，使用默认值 09:30")
            return 9, 30

settings = Settings()
