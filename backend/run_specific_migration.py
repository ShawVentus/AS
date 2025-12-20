import os
import sys
import psycopg2
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

def run_migration(sql_file_path: str):
    """
    执行指定的 SQL 迁移文件。
    
    Args:
        sql_file_path (str): SQL 文件的路径。
    """
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("错误: 环境变量中未找到 DATABASE_URL。")
        return

    if not os.path.exists(sql_file_path):
        print(f"错误: 找不到 SQL 文件: {sql_file_path}")
        return

    print(f"正在执行迁移文件: {sql_file_path}")
    
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        with open(sql_file_path, "r", encoding="utf-8") as f:
            sql = f.read()
            
        cur.execute(sql)
        conn.commit()
        
        print("✅ 迁移成功执行。")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python run_specific_migration.py <sql_file_path>")
        sys.exit(1)
        
    run_migration(sys.argv[1])
