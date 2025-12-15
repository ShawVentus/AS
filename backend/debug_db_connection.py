import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env vars
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key (first 10 chars): {key[:10] if key else 'None'}")

if not url or not key:
    print("❌ Missing URL or Key")
    sys.exit(1)

try:
    supabase = create_client(url, key)
    
    # Try to fetch latest execution
    print("\nFetching latest execution...")
    response = supabase.table("workflow_executions").select("*").order("created_at", desc=True).limit(1).execute()
    
    if response.data:
        latest = response.data[0]
        print(f"✅ Success! Latest Execution ID: {latest['id']}")
        print(f"Status: {latest['status']}")
    else:
        print("✅ Success! Connected but no executions found.")
        
except Exception as e:
    print(f"❌ Connection failed: {e}")
