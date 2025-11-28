from app.core.database import get_db
from dotenv import load_dotenv
import os

load_dotenv()

def check_status():
    db = get_db()
    
    # Debug: Check if key is service key (length usually > 200)
    import os
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
    print(f"Using key length: {len(key) if key else 0}")
    print(f"URL: {os.environ.get('SUPABASE_URL')}")
    
    try:
        # Try to insert a test paper
        test_id = "test.12345"
        print(f"Attempting to insert test paper {test_id}...")
        res = db.table("papers").upsert({
            "id": test_id,
            "category": "test",
            "status": "pending"
        }).execute()
        print(f"Insert result: {res}")
        
        # Check counts for each status
        pending = db.table("papers").select("id", count="exact").eq("status", "pending").execute()
        completed = db.table("papers").select("id", count="exact").eq("status", "completed").execute()
        failed = db.table("papers").select("id", count="exact").eq("status", "failed").execute()
        
        print(f"Pending: {pending.count}")
        print(f"Completed: {completed.count}")
        print(f"Failed: {failed.count}")
        
        # List a few pending IDs if any
        if pending.count > 0:
            print("Sample pending IDs:")
            sample = db.table("papers").select("id").eq("status", "pending").limit(5).execute()
            print(sample.data)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_status()
