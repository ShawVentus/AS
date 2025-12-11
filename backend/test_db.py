import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

print(f"URL: {url}")
print(f"Key: {key[:5]}..." if key else "Key: None")

try:
    print("Creating client...")
    supabase: Client = create_client(url, key)
    print("Client created. Executing query...")
    print("Querying reports...")
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    reports = supabase.table("reports").select("id, user_id, date").eq("date", today).execute()
    print(f"Reports count for today ({today}): {len(reports.data)}")
    for r in reports.data:
        print(f"Report: {r}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
