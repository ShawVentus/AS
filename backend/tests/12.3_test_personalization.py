import sys
import os
import asyncio
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(backend_path)

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, UserPaperState

async def test_get_papers_by_categories():
    print("\n--- Testing get_papers_by_categories ---")
    service = PaperService()
    
    # Mock DB
    service.db = MagicMock()
    
    # Mock existing states (simulate user has seen paper_1)
    service.db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"paper_id": "paper_1"}]
    
    # Mock papers response (return paper_2)
    mock_paper_2 = {
        "id": "paper_2",
        "title": "Test Paper 2",
        "authors": ["Author B"],
        "published_date": "2023-01-02",
        "category": ["cs.AI"],
        "abstract": "Abstract 2",
        "links": {"pdf": "", "arxiv": "", "html": ""},
        "comment": ""
    }
    
    # Setup chain for query
    # table -> select -> overlaps -> order -> not_.in_ -> limit -> execute
    # We need to ensure not_.in_ is called
    
    # Mock the chain step by step
    select_mock = service.db.table.return_value.select.return_value
    overlaps_mock = select_mock.overlaps.return_value
    order_mock = overlaps_mock.order.return_value
    not_in_mock = order_mock.not_.in_.return_value
    limit_mock = not_in_mock.limit.return_value
    
    # Set the return value for the final execute
    limit_mock.execute.return_value.data = [mock_paper_2]
    
    # Also handle the case where not_.in_ might be skipped (if existing_ids was empty, but here we mocked it as present)
    # But since we mocked existing_ids as present, the code WILL call not_.in_
    
    # Call method
    result = service.get_papers_by_categories(["cs.AI"], "user_123")
    
    # Verify upsert was called for the new paper
    # We expect: service.db.table("user_paper_states").upsert(...).execute()
    # Check if upsert was called
    # Note: service.db.table returns the same mock object for all calls
    table_mock = service.db.table.return_value
    upsert_calls = table_mock.upsert.call_args_list
    
    if upsert_calls:
        print("[OK] Success: Initial state persistence triggered.")
        args, _ = upsert_calls[0]
        print(f"Upsert data: {args[0]}")
    else:
        print("[FAIL] Failed: No upsert call detected.")
        # print("All mock calls:", service.db.mock_calls) # Too verbose

    if len(result) == 1 and result[0].meta.id == "paper_2":
        print("[OK] Success: Fetched new candidate paper (paper_2).")
        if result[0].user_state and result[0].user_state.why_this_paper == "Not Filtered":
             print("[OK] Success: User state initialized correctly.")
        else:
             print("[FAIL] Failed: User state not initialized.")
    else:
        print(f"[FAIL] Failed: Expected 1 paper, got {len(result)}")

async def test_update_user_feedback():
    print("\n--- Testing update_user_feedback ---")
    service = PaperService()
    service.db = MagicMock()
    
    # Call method
    success = service.update_user_feedback("user_123", "paper_1", True, "Good paper")
    
    if success:
        # Verify db call
        service.db.table.assert_called_with("user_paper_states")
        print("[OK] Success: Feedback update triggered.")
    else:
        print("[FAIL] Failed: Update returned False")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(test_get_papers_by_categories())
    loop.run_until_complete(test_update_user_feedback())
