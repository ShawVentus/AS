import os
import sys
# Ensure backend directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("-" * 50)
print("🔍 Environment Debug Info")
print("-" * 50)

url = os.environ.get("SUPABASE_URL")
service_key = os.environ.get("SUPABASE_SERVICE_KEY")
anon_key = os.environ.get("SUPABASE_KEY")

print(f"SUPABASE_URL: {url}")
print(f"SUPABASE_SERVICE_KEY present: {bool(service_key)}")
if service_key:
    print(f"SUPABASE_SERVICE_KEY length: {len(service_key)}")
    print(f"SUPABASE_SERVICE_KEY prefix: {service_key[:10]}...")
    if service_key == anon_key:
        print("⚠️ WARNING: SUPABASE_SERVICE_KEY is identical to SUPABASE_KEY (Anon Key)!")
    else:
        print("✅ SUPABASE_SERVICE_KEY is different from SUPABASE_KEY")

print("\n" + "-" * 50)
print("🔍 Database Query Debug")
print("-" * 50)

try:
    from app.core.database import get_db
    db = get_db()
    
    # 1. Query all profiles (limit 5)
    print("Attempting to query 'profiles' table (all)...")
    response = db.table("profiles").select("user_id, remaining_quota, receive_email, focus").limit(5).execute()
    print(f"Total profiles found (limit 5): {len(response.data)}")
    for p in response.data:
        print(f"  - User: {p.get('user_id')}")
        print(f"    Quota: {p.get('remaining_quota')}")
        print(f"    Receive Email: {p.get('receive_email')}")
        print(f"    Focus: {p.get('focus')}")
        
    # 2. Query with scheduler logic
    print("\nAttempting to query with scheduler logic (quota > 0 AND receive_email = True)...")
    filtered = db.table("profiles").select("focus").gt("remaining_quota", 0).eq("receive_email", True).execute()
    print(f"Filtered profiles found: {len(filtered.data)}")
    print(f"Data: {filtered.data}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
