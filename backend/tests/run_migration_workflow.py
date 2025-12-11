import os
import sys
from dotenv import load_dotenv

# 添加 backend 目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import get_db

def run_migration():
    """
    执行数据库迁移脚本。
    
    读取 migrations/create_workflow_tables.sql 并执行 SQL 语句。
    注意：Supabase Python 客户端通常不支持直接执行原始 SQL 脚本（取决于权限和客户端版本）。
    如果此脚本执行失败，请在 Supabase Dashboard 的 SQL Editor 中手动运行 SQL。
    """
    print("开始执行数据库迁移...")
    
    # 1. 读取 SQL 文件
    # __file__ = backend/tests/run_migration_workflow.py
    # dirname = backend/tests
    # ../migrations = backend/migrations
    sql_path = os.path.join(os.path.dirname(__file__), "../migrations/create_workflow_tables.sql")
    try:
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
    except FileNotFoundError:
        print(f"❌ 错误：找不到 SQL 文件: {sql_path}")
        return

    # 2. 执行 SQL
    # 由于 supabase-py 客户端主要用于 RESTful 操作，直接执行 DDL 可能受限。
    # 这里尝试使用 rpc (如果定义了 exec_sql 函数) 或者提示用户手动执行。
    # 为了安全起见，我们先提示用户。
    
    print(f"SQL 文件路径: {sql_path}")
    print("⚠️ 注意：Supabase Python 客户端可能不支持直接执行 DDL 语句。")
    print("请复制以下 SQL 内容并在 Supabase Dashboard -> SQL Editor 中执行：")
    print("-" * 50)
    print(sql_content)
    print("-" * 50)
    
    # 尝试一种可能的执行方式（如果配置了 postgres 直连，可以使用 psycopg2，但这里只有 supabase client）
    # 如果项目中有特定的执行 SQL 的方法，请使用它。
    # 目前仅打印提示。

if __name__ == "__main__":
    run_migration()
