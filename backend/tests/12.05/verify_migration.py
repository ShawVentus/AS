import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.core.database import get_db
from dotenv import load_dotenv
import os

load_dotenv()

def verify_tables():
    db = get_db()
    print("Verifying tables...")
    
    try:
        # Check daily_papers
        print("Checking daily_papers...")
        res = db.table("daily_papers").select("count", count="exact").limit(1).execute()
        print(f"daily_papers exists. Count: {res.count}")
        
        # Check system_status
        print("Checking system_status...")
        res = db.table("system_status").select("count", count="exact").limit(1).execute()
        print(f"system_status exists. Count: {res.count}")
        
        print("Verification successful!")
        return True
    except Exception as e:
        print(f"Verification failed: {e}")
        return False

if __name__ == "__main__":
    verify_tables()
