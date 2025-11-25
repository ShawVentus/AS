import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PaperMetadata, PersonalizedPaper, PaperLinks, PaperDetails
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

load_dotenv()

def test_llm_filter():
    print("🚀 Testing LLM Filter Functionality...")
    
    service = PaperService()
    
    # 1. Create a Mock Paper (Real Metadata)
    # Source: https://arxiv.org/abs/2309.07864 (Mistral 7B)
    import uuid
    random_id = f"test_filter_{uuid.uuid4().hex[:8]}"
    mock_paper_metadata = PaperMetadata(
        id=random_id,
        title="Mistral 7B",
        authors=["Albert Jiang", "Alexandre Sablayrolles", "Arthur Mensch", "et al."],
        published_date="2023-09-27",
        category=["cs.CL"],
        abstract="We introduce Mistral 7B, a 7-billion-parameter language model engineered for superior performance and efficiency. Mistral 7B outperforms Llama 2 13B across all evaluated benchmarks, and Llama 1 34B on many benchmarks. It approaches CodeLlama 7B performance on code, while remaining good at English tasks. It uses Grouped-query attention (GQA) for faster inference and Sliding Window Attention (SWA) to handle longer sequences at smaller cost. We release Mistral 7B under the Apache 2.0 license.",
        tldr="",
        tags=[],
        citationCount=0,
        year=2023,
        links=PaperLinks(pdf="https://arxiv.org/pdf/2310.06825.pdf", arxiv="https://arxiv.org/abs/2310.06825", html="https://arxiv.org/html/2310.06825"),
        details=None
    )
    
    # Wrap in PersonalizedPaper for service input
    mock_paper = PersonalizedPaper(**mock_paper_metadata.model_dump(), user_state=None)
    
    # 2. Create a Mock User Profile (Interested in LLMs)
    user_profile = UserProfile(
        info=UserInfo(name="Tester", email="test@test.com", avatar="", nickname="T"),
        focus=Focus(
            domains=["Large Language Models", "NLP"],
            keywords=["LLM", "Transformer", "Efficient"],
            authors=[],
            institutions=[]
        ),
        context=Context(currentTask="Research", futureGoal="", stage="", purpose=[]),
        memory=Memory(readPapers=[], dislikedPapers=[])
    )
    
    print(f"\n📄 Paper: {mock_paper.title}")
    print(f"👤 User Focus: {user_profile.focus.keywords}")
    
    # 3. Run Filter
    print("\n🔍 Running filter_papers...")
    # We need to insert it into DB first because filter_papers updates DB
    try:
        # Ensure User Exists
        try:
            service.db.table("users").insert({"id": user_profile.info.email, "email": user_profile.info.email}).execute()
        except:
            pass # User likely exists

        # Cleanup first
        # Must delete dependent records first
        try:
            service.db.table("user_paper_states").delete().eq("paper_id", mock_paper.id).execute()
        except:
            pass
        service.db.table("papers").delete().eq("id", mock_paper.id).execute()
        
        # Insert Metadata
        service.db.table("papers").insert(mock_paper_metadata.model_dump()).execute()
    except Exception as e:
        print(f"DB Setup Error: {e}")
        return

    filtered_results = service.filter_papers([mock_paper], user_profile)
    
    # 4. Check Result
    if filtered_results:
        print(f"\n✅ Paper passed filter!")
        # Fetch from DB to see the suggestion
        updated_paper = service.get_paper_by_id(mock_paper.id, user_profile.info.email)
        if updated_paper and updated_paper.user_state:
            print(f"💡 Suggestion: {updated_paper.user_state.why_this_paper}")
            print(f"💡 Score: {updated_paper.user_state.relevance_score}")
            print(f"💡 Accepted: {updated_paper.user_state.accepted}")
        else:
            print("❌ Failed to fetch updated paper state.")
    else:
        print(f"\n❌ Paper was filtered out.")
        updated_paper = service.get_paper_by_id(mock_paper.id, user_profile.info.email)
        if updated_paper and updated_paper.user_state:
             print(f"💡 Reason: {updated_paper.user_state.why_this_paper}")

    # 5. Test Irrelevant Profile
    print("\n🔄 Testing with Irrelevant Profile (Biology)...")
    bio_profile = UserProfile(
        info=UserInfo(name="BioTester", email="bio@test.com", avatar="", nickname="B"),
        focus=Focus(
            domains=["Biology", "Genetics"],
            keywords=["Cell", "DNA", "Protein"],
            authors=[],
            institutions=[]
        ),
        context=Context(currentTask="", futureGoal="", stage="", purpose=[]),
        memory=Memory(readPapers=[], dislikedPapers=[])
    )
    
    # Ensure Bio User Exists
    try:
        service.db.table("users").insert({"id": bio_profile.info.email, "email": bio_profile.info.email}).execute()
    except:
        pass

    # Reset paper state (delete user state for bio user)
    service.db.table("user_paper_states").delete().eq("user_id", bio_profile.info.email).eq("paper_id", mock_paper.id).execute()
    
    # We need to re-wrap because filter_papers modifies the object in place or returns new ones
    # Let's fetch fresh or re-create
    mock_paper_bio = PersonalizedPaper(**mock_paper_metadata.model_dump(), user_state=None)
    
    filtered_bio = service.filter_papers([mock_paper_bio], bio_profile)
    
    if not filtered_bio:
        print(f"✅ Paper correctly filtered out for Biology profile!")
        updated_paper = service.get_paper_by_id(mock_paper.id, bio_profile.info.email)
        if updated_paper and updated_paper.user_state:
            print(f"💡 Reason: {updated_paper.user_state.why_this_paper}")
            print(f"💡 Accepted: {updated_paper.user_state.accepted}")
    else:
        print(f"❌ Paper should have been filtered out but wasn't.")

    # Cleanup
    service.db.table("user_paper_states").delete().eq("paper_id", mock_paper.id).execute()
    service.db.table("papers").delete().eq("id", mock_paper.id).execute()

if __name__ == "__main__":
    test_llm_filter()
