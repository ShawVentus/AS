# 2025-11-25 00:21:02
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.scheduler import SchedulerService
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

class TestSchedulerIntegration(unittest.TestCase):
    def setUp(self):
        # Mock DB
        self.mock_db = MagicMock()
        self.mock_table = MagicMock()
        self.mock_db.table.return_value = self.mock_table
        
        # Patch get_db
        self.db_patcher = patch('app.services.scheduler.get_db', return_value=self.mock_db)
        self.db_patcher.start()
        
        # Patch paper_service's db attribute directly because it's a singleton instantiated at import
        from app.services.paper_service import paper_service
        self.original_paper_db = paper_service.db
        paper_service.db = self.mock_db

        self.scheduler = SchedulerService()
        self.scheduler.db = self.mock_db

        # Mock User Service
        self.user_patcher = patch('app.services.scheduler.user_service')
        self.mock_user_service = self.user_patcher.start()
        self.mock_user_service.get_profile.return_value = UserProfile(
            info=UserInfo(name="Test", email="test@example.com", avatar="", nickname=""),
            focus=Focus(domains=[], keywords=[], authors=[], institutions=[]),
            context=Context(currentTask="", futureGoal="", stage="", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )

    def tearDown(self):
        self.db_patcher.stop()
        self.user_patcher.stop()
        # Restore paper_service db
        from app.services.paper_service import paper_service
        paper_service.db = self.original_paper_db

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_process_new_papers_flow(self, mock_call_llm):
        """
        Test the full flow:
        1. Fetch papers from DB
        2. Filter (Concurrent)
        3. Analyze (Deep Analysis)
        4. Update DB
        """
        # 1. Mock DB Response (Raw Papers)
        raw_papers = [
            {
                "id": "p1", "title": "Relevant Paper", "abstract": "...", "created_at": "2025-01-01", 
                "authors": ["A"], "category": "cs.AI", "links": {"pdf": "#", "arxiv": "#", "html": "#"}, "published_date": "2025-01-01"
            },
            {
                "id": "p2", "title": "Irrelevant Paper", "abstract": "...", "created_at": "2025-01-01",
                "authors": ["B"], "category": "cs.AI", "links": {"pdf": "#", "arxiv": "#", "html": "#"}, "published_date": "2025-01-01"
            }
        ]
        # Mock select().order().limit().execute() chain
        self.mock_table.select.return_value.order.return_value.limit.return_value.execute.return_value.data = raw_papers

        # 2. Mock LLM Responses
        # We need to handle multiple calls:
        # - 2 calls for filtering (p1, p2)
        # - 1 call for analysis (p1 only, since p2 is irrelevant)
        
        def llm_side_effect(prompt):
            if "筛选助手" in prompt: # Filter Prompt
                if "Relevant Paper" in prompt:
                    return json.dumps({"why_this_paper": "Good", "relevance_score": 0.9, "accepted": True})
                else:
                    return json.dumps({"why_this_paper": "Bad", "relevance_score": 0.1, "accepted": False})
            elif "分析助手" in prompt: # Analyze Prompt
                return json.dumps({
                    "tldr": "TLDR", "motivation": "M", "method": "M", "result": "R", "conclusion": "C",
                    "tags": {"tag1": "content1"}
                })
            else:
                # Fallback
                return "{}"

        # Since we can't easily distinguish filter vs analyze by prompt content alone without complex logic,
        # let's simplify: 
        # The code calls `analyze_single_paper` (uses filter.md) then `analyze_paper` (uses analyze.md).
        # `analyze_single_paper` calls `llm_service.call_llm`.
        # `analyze_paper` calls `llm_service.analyze_paper` -> `call_llm`.
        
        # Let's just return a generic successful response for everything, 
        # but we need to control 'accepted' status to test branching.
        # Actually, `analyze_single_paper` parses `accepted`.
        
        # We can use side_effect with an iterator or checking prompt content.
        # Checking prompt content is safer.
        
        mock_call_llm.side_effect = llm_side_effect
        
        # Run
        self.scheduler.process_new_papers()
        
        # Assertions
        # 1. DB Select called
        self.mock_table.select.assert_called()
        
        # 2. DB Upsert (User State) called 2 times (for p1 and p2)
        # We can check call_args_list of upsert
        upsert_calls = self.mock_table.upsert.call_args_list
        self.assertEqual(len(upsert_calls), 2)
        
        # 3. DB Update (Public Metadata) called 2 times
        # - Once for p1 (Analysis results)
        # - Once for p2 (Mark as N/A)
        update_calls = self.mock_table.update.call_args_list
        self.assertEqual(len(update_calls), 2)
        
        # Verify P1 update (Analysis)
        p1_update = [c for c in update_calls if c[0][0].get('tldr') == 'TLDR']
        self.assertTrue(p1_update, "P1 should be updated with analysis")
        
        # Verify P2 update (N/A)
        p2_update = [c for c in update_calls if c[0][0].get('tldr') == 'N/A']
        self.assertTrue(p2_update, "P2 should be marked as N/A")

        print("\n[Pass] Integration flow verified: Filter -> Analyze -> DB Update")

if __name__ == '__main__':
    unittest.main()
