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
    
    # Qwen-Plus 定价 (USD per 1M tokens)
    QWEN_PLUS_PRICE_INPUT: float = float(os.getenv("QWEN_PLUS_PRICE_INPUT", "0.40"))
    QWEN_PLUS_PRICE_OUTPUT: float = float(os.getenv("QWEN_PLUS_PRICE_OUTPUT", "1.20"))
    QWEN_MAX_PRICE_INPUT: float = float(os.getenv("QWEN_MAX_PRICE_INPUT", "1.60")) # 假设价格，需确认
    QWEN_MAX_PRICE_OUTPUT: float = float(os.getenv("QWEN_MAX_PRICE_OUTPUT", "4.80"))

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
                "base_url": "https://api.bohrium.dp.tech/v1",
                "model": self.BOHRIUM_MODEL,
            }
        }
        
        if provider not in configs:
            raise ValueError(f"无效的 LLM_PROVIDER: {provider}。可选值: {', '.join(configs.keys())}")
            
        config = configs[provider]
        if not config["api_key"]:
            raise ValueError(f"未设置 {provider} 的 API Key。")
            
        return config
    
    # 邮件配置
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 465))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")
    RECIPIENT_EMAILS: str = os.getenv("RECIPIENT_EMAILS", "")

    # 爬虫配置
    CATEGORIES: str = os.getenv("CATEGORIES", "cs.CV,cs.LG,cs.CL,cs.AI")

settings = Settings()
