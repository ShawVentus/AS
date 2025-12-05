import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.core.database import get_db
from dotenv import load_dotenv
import os
import time

load_dotenv()

def test_db_access():
    db = get_db()
    print("Testing DB write access...")
    
    test_id = f"test.daily.{int(time.time())}"
    
    try:
        # Try to insert into daily_papers
        print(f"Inserting test paper {test_id} into daily_papers...")
        res = db.table("daily_papers").insert({
            "id": test_id,
            "title": "Test Paper",
            "category": ["cs.TEST"],
            "status": "pending"
        }).execute()
        
        print(f"Insert result: {res}")
        
        # Verify read
        print("Verifying read...")
        read_res = db.table("daily_papers").select("*").eq("id", test_id).execute()
        if read_res.data and read_res.data[0]['id'] == test_id:
            print("Read verification successful!")
            
            # Cleanup
            print("Cleaning up...")
            db.table("daily_papers").delete().eq("id", test_id).execute()
            print("Cleanup done.")
            return True
        else:
            print("Read verification failed: Data not found.")
            return False
            
    except Exception as e:
        print(f"DB Access failed: {e}")
        return False

if __name__ == "__main__":
    test_db_access()
