import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import Paper
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

load_dotenv()

def verify_flow():
    print("🚀 Starting End-to-End Verification...")
    
    service = PaperService()

    # 0. Cleanup previous test data
    print("\n0️⃣  Cleaning up old test data...")
    try:
        service.db.table("papers").delete().like("id", "test_e2e_%").execute()
        print("✅ Old test data cleaned.")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    # 1. Simulate Crawler: Insert a raw paper
    print("\n1️⃣  Simulating Crawler Insertion...")
    raw_paper = {
        "id": f"test_e2e_{int(datetime.now().timestamp())}",
        "title": "E2E Verification: AI Agents in 2025",
        "authors": ["Test Author", "Robot"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "category": "cs.AI",
        "tldr": "Initial TLDR",
        "suggestion": "Initial Suggestion",
        "tags": ["Test"],
        "citationCount": 0,
        "year": 2025,
        "links": {"pdf": "http://test.pdf", "arxiv": "http://test.arxiv", "html": "http://test.html"},
        "details": {
            "abstract": "This is a test paper to verify the end-to-end flow of the Paper Scout Agent. It discusses how AI agents verify themselves."
        }
    }
    
    # Manually insert into DB (bypassing crawler logic for speed)
    try:
        service.db.table("papers").insert(raw_paper).execute()
        print("✅ Raw paper inserted.")
    except Exception as e:
        print(f"❌ Failed to insert raw paper: {e}")
        return

    # 2. Simulate LLM Analysis
    print("\n2️⃣  Simulating LLM Analysis...")
    try:
        # Fetch the paper back to get the object
        papers = service.get_papers()
        target_paper = next((p for p in papers if p.id == raw_paper["id"]), None)
        
        if not target_paper:
            print("❌ Could not find inserted paper.")
            return
            
        # Create mock profile
        mock_profile = UserProfile(
            info=UserInfo(name="Test User", email="test@test.com", avatar="", nickname="Tester"),
            focus=Focus(domains=["AI"], keywords=["Agents"], authors=[], institutions=[]),
            context=Context(currentTask="Verification", futureGoal="Success", stage="Dev", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )
        
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
        updated_papers = service.get_papers()
        updated_paper = next((p for p in updated_papers if p.id == raw_paper["id"]), None)
        
        if updated_paper and updated_paper.tldr:
            print(f"✅ Paper enriched! TLDR: {updated_paper.tldr[:50]}...")
            print(f"✅ Tags: {updated_paper.tags}")
        else:
            print("❌ Paper was not enriched (TLDR missing).")
            
    except Exception as e:
        print(f"❌ Failed verification: {e}")

    # 4. Cleanup
    print("\n4️⃣  Cleaning up...")
    try:
        service.db.table("papers").delete().eq("id", raw_paper["id"]).execute()
        print("✅ Test paper deleted.")
    except Exception as e:
        print(f"⚠️ Failed to cleanup: {e}")

if __name__ == "__main__":
    verify_flow()
