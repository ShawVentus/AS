import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.user_service import UserService
from app.schemas.user import UserFeedback

load_dotenv()

def verify_user_flow():
    print("🚀 Starting User Flow Verification...")
    
    service = UserService()
    
    # 1. Get Initial Profile (creates default if needed)
    print("\n1️⃣  Fetching Initial Profile...")
    try:
        profile = service.get_profile()
        print(f"✅ Got profile for: {profile.info.name}")
        print(f"   Current Keywords: {profile.focus.keywords}")
        print(f"   Read Papers: {len(profile.memory.readPapers)}")
    except Exception as e:
        print(f"❌ Failed to get profile: {e}")
        return

    # 2. Test NL Update
    print("\n2️⃣  Testing NL Update (Mock)...")
    try:
        # The mock logic adds "LLM" if present in text
        feedback = "I am interested in LLM agents."
        updated_profile = service.update_profile_nl("dummy_id", feedback)
        
        if "LLM" in updated_profile.focus.keywords:
            print(f"✅ NL Update successful! Added 'LLM' to keywords.")
            print(f"   New Keywords: {updated_profile.focus.keywords}")
        else:
            print("❌ NL Update failed. 'LLM' not found in keywords.")
            
    except Exception as e:
        print(f"❌ Failed NL update: {e}")

    # 3. Test Feedback Update
    print("\n3️⃣  Testing Feedback Update...")
    try:
        test_paper_id = f"test_paper_{int(datetime.now().timestamp())}"
        feedback = UserFeedback(paper_id=test_paper_id, is_like=True)
        
        updated_profile = service.update_profile_from_selection("dummy_id", [feedback])
        
        if test_paper_id in updated_profile.memory.readPapers:
            print(f"✅ Feedback Update successful! Added {test_paper_id} to readPapers.")
        else:
            print("❌ Feedback Update failed. Paper ID not found in memory.")
            
    except Exception as e:
        print(f"❌ Failed feedback update: {e}")

    print("\n🎉 User Flow Verification Complete!")

if __name__ == "__main__":
    verify_user_flow()
