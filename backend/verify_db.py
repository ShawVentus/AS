import asyncio
import os
from database import get_db

output_file = "db_status.txt"

async def check():
    with open(output_file, "w") as f:
        try:
            client = get_db()
            # Supabase-py客户端的某些操作是同步的,但让我们检查一下使用情况
            # 实际上get_db()返回客户端。
            # client.table(...).select(...)在supabase-py中是同步的吗?
            # 通常是的。
            res = client.table("users").select("*").limit(1).execute()
            f.write(f"DB Check: OK. Found {len(res.data)} users.\n")
        except Exception as e:
            f.write(f"DB Check: FAILED. {e}\n")

if __name__ == "__main__":
    asyncio.run(check())
