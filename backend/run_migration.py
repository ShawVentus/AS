import os
import sys
import psycopg2
from urllib.parse import urlparse

# Load .env manually since we are running as a script
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

DATABASE_URL = os.environ.get("DATABASE_URL")

def run_migration():
    print("Running migration: 20251212_add_workflow_progress.sql")
    
    if not DATABASE_URL:
        print("Error: DATABASE_URL not found in environment.")
        return

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        with open("migrations/20251212_add_workflow_progress.sql", "r") as f:
            sql = f.read()
            
        cur.execute(sql)
        conn.commit()
        
        print("Migration executed successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
