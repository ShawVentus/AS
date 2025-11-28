import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
# 优先使用 Service Key (Bypass RLS)，否则使用 Anon Key
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    raise ValueError("必须在环境变量中设置 Supabase URL 和 Key")

supabase: Client = create_client(url, key)

def get_db():
    return supabase
