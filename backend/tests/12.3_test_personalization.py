import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
# Current file is in backend/tests/
# We need to add backend/ to sys.path so we can import app
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_path)

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, UserPaperState

async def test_get_papers_by_categories():
    print("\n--- Testing get_papers_by_categories ---")
    service = PaperService()
    
    # Mock DB
    service.db = MagicMock()
    
    # Mock existing states (empty)
    service.db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    
    # Mock papers response
    mock_paper = {
        "id": "test_paper_1",
        "title": "Test Paper",
        "authors": ["Author A"],
        "published_date": "2023-01-01",
        "category": ["cs.AI"],
        "abstract": "Abstract",
        "links": {"pdf": "", "arxiv": "", "html": ""},
        "comment": ""
    }
    service.db.table.return_value.select.return_value.overlaps.return_value.order.return_value.limit.return_value.execute.return_value.data = [mock_paper]
    
    # Call method
    result = service.get_papers_by_categories(["cs.AI"], "user_123")
    
    if len(result) == 1 and result[0].meta.id == "test_paper_1":
        print("✅ Success: Fetched candidate paper.")
    else:
        print(f"❌ Failed: Expected 1 paper, got {len(result)}")

async def test_update_user_feedback():
    print("\n--- Testing update_user_feedback ---")
    service = PaperService()
    service.db = MagicMock()
    
    # Call method
    success = service.update_user_feedback("user_123", "paper_1", True, "Good paper")
    
    if success:
        # Verify db call
        # service.db.table("user_paper_states").upsert(...).execute()
        service.db.table.assert_called_with("user_paper_states")
        print("✅ Success: Feedback update triggered.")
    else:
        print("❌ Failed: Update returned False")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_get_papers_by_categories())
    loop.run_until_complete(test_update_user_feedback())
