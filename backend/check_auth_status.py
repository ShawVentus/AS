from app.core.database import get_db
from dotenv import load_dotenv
import os

load_dotenv()

def check_profiles():
    db = get_db()
    try:
        print("Checking profiles table...")
        # Use service key to bypass RLS for this check
        # Ensure SUPABASE_SERVICE_KEY is set in .env or use the one from database.py logic
        
        response = db.table("profiles").select("*").execute()
        
        profiles = response.data
        print(f"Total profiles found: {len(profiles)}")
        
        for p in profiles:
            print(f"User ID: {p.get('user_id')}")
            print(f"Email: {p.get('info', {}).get('email')}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_profiles()
