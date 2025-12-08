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

    # Supabase配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # LLM配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    ACCESS_KEY: str = os.getenv("ACCESS_KEY", "")
    
    # 邮件配置
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 465))
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD: str = os.getenv("SENDER_PASSWORD", "")
    RECIPIENT_EMAILS: str = os.getenv("RECIPIENT_EMAILS", "")

    # 爬虫配置
    CATEGORIES: str = os.getenv("CATEGORIES", "cs.CV,cs.LG,cs.CL,cs.AI")

settings = Settings()
