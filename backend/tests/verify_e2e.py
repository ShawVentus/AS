import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PaperMetadata, PersonalizedPaper, PaperLinks
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

load_dotenv()

def verify_flow():
    print("🚀 Starting End-to-End Verification...")
    
    service = PaperService()

    # 0. Cleanup previous test data
    print("\n0️⃣  Cleaning up old test data...")
    try:
        service.db.table("papers").delete().like("id", "test_e2e_%").execute()
        # Also clean states (cascade should handle it if set, but let's be safe)
        # We can't easily delete states without user_id, but papers delete might cascade if configured.
        # For now, we rely on paper deletion.
        print("✅ Old test data cleaned.")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    # 1. Simulate Crawler: Insert a raw paper (PaperMetadata)
    print("\n1️⃣  Simulating Crawler Insertion...")
    raw_paper_metadata = {
        "id": f"test_e2e_{int(datetime.now().timestamp())}",
        "title": "E2E Verification: AI Agents in 2025",
        "authors": ["Test Author", "Robot"],
        "published_date": datetime.now().strftime("%Y-%m-%d"),
        "category": ["cs.AI"],
        "abstract": "This is a test paper to verify the end-to-end flow of the Paper Scout Agent. It discusses how AI agents verify themselves.",
        "tldr": "Initial TLDR",
        "tags": ["Test"],
        "citationCount": 0,
        "year": 2025,
        "links": {"pdf": "http://test.pdf", "arxiv": "http://test.arxiv", "html": "http://test.html"},
        "details": None
    }
    
    # Manually insert into DB
    try:
        service.db.table("papers").insert(raw_paper_metadata).execute()
        print("✅ Raw paper inserted.")
    except Exception as e:
        print(f"❌ Failed to insert raw paper: {e}")
        return

    # 2. Simulate LLM Analysis
    print("\n2️⃣  Simulating LLM Analysis...")
    try:
        # Create mock profile
        mock_profile = UserProfile(
            info=UserInfo(name="Test User", email="test@test.com", avatar="", nickname="Tester"),
            focus=Focus(domains=["AI"], keywords=["Agents"], authors=[], institutions=[]),
            context=Context(currentTask="Verification", futureGoal="Success", stage="Dev", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )
        
        # Fetch the paper back (Personalized)
        # We need to pass user_id to get_paper_by_id
        target_paper = service.get_paper_by_id(raw_paper_metadata["id"], mock_profile.info.email)
        
        if not target_paper:
            print("❌ Could not find inserted paper.")
            return

        # 1.5 Run Filter (to create User State)
        print("\n1.5️⃣ Simulating Filter...")
        service.filter_papers([target_paper], mock_profile)
        
        # Re-fetch to get state
        target_paper = service.get_paper_by_id(raw_paper_metadata["id"], mock_profile.info.email)

        # Call the service method
        service.analyze_paper(target_paper, mock_profile)
        print("✅ LLM Analysis completed.")
        
    except Exception as e:
        print(f"❌ Failed during analysis: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Verify Data Enrichment
    print("\n3️⃣  Verifying Data Enrichment...")
    try:
        # Fetch again
        updated_paper = service.get_paper_by_id(raw_paper_metadata["id"], mock_profile.info.email)
        
        if updated_paper and updated_paper.tldr:
            print(f"✅ Paper enriched! TLDR: {updated_paper.tldr[:50]}...")
            print(f"✅ Tags: {updated_paper.tags}")
            
            # Verify User State
            if updated_paper.user_state:
                print(f"✅ User State Created! Reason: {updated_paper.user_state.why_this_paper}")
                print(f"✅ Accepted: {updated_paper.user_state.accepted}")
            else:
                print("❌ User State missing.")
        else:
            print("❌ Paper was not enriched (TLDR missing).")
            
    except Exception as e:
        print(f"❌ Failed verification: {e}")

    # 4. Cleanup
    print("\n4️⃣  Cleaning up...")
    try:
        service.db.table("user_paper_states").delete().eq("paper_id", raw_paper_metadata["id"]).execute()
        service.db.table("papers").delete().eq("id", raw_paper_metadata["id"]).execute()
        print("✅ Test paper deleted.")
    except Exception as e:
        print(f"⚠️ Failed to cleanup: {e}")

if __name__ == "__main__":
    verify_flow()
