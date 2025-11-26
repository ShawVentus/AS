import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
from typing import List

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, PaperAnalysis, UserPaperState
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

class TestServiceDecoupling(unittest.TestCase):
    def setUp(self):
        # Mock DB
        self.mock_db = MagicMock()
        self.mock_table = MagicMock()
        self.mock_db.table.return_value = self.mock_table
        
        # Patch get_db
        self.db_patcher = patch('app.services.paper_service.get_db', return_value=self.mock_db)
        self.db_patcher.start()
        
        self.service = PaperService()
        self.service.db = self.mock_db

        # Mock Data
        self.paper_meta_data = {
            "id": "test_paper_1",
            "title": "Test Paper",
            "authors": ["Author A"],
            "published_date": "2023-01-01",
            "category": ["cs.AI"],
            "abstract": "This is a test abstract.",
            "links": {"pdf": "url", "arxiv": "url", "html": "url"},
            "comment": "Test Comment"
        }
        self.meta = RawPaperMetadata(**self.paper_meta_data)
        self.paper = PersonalizedPaper(meta=self.meta, analysis=None, user_state=None)
        
        self.user_profile = UserProfile(
            info=UserInfo(name="Test User", email="test@example.com", avatar="", nickname="Tester"),
            focus=Focus(domains=["AI"], keywords=["LLM"], authors=[], institutions=[]),
            context=Context(currentTask="", futureGoal="", stage="", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )

    def tearDown(self):
        self.db_patcher.stop()

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_public_analysis_only(self, mock_call_llm):
        """
        Test that analyze_paper only updates public metadata (papers table).
        """
        # Mock LLM response for analysis
        mock_call_llm.return_value = json.dumps({
            "tldr": "Summary",
            "motivation": "Motivation",
            "method": "Method",
            "result": "Result",
            "conclusion": "Conclusion",
            "tags": {"tag1": "value"}
        })
        
        # Execute
        result = self.service.analyze_paper(self.paper)
        
        # Verify
        self.assertIsNotNone(result)
        self.assertEqual(result.tldr, "Summary")
        
        # Check DB calls
        # Should update 'papers' table
        self.mock_db.table.assert_any_call("papers")
        # Verify chain: table("papers").update(...).eq("id", ...).execute()
        self.mock_db.table("papers").update.assert_called_once()
        self.mock_db.table("papers").update.return_value.eq.assert_called_with("id", "test_paper_1")
        
        # Should NOT update 'user_paper_states' table (in this call)
        # Note: table() is called with "papers", verify it wasn't called with "user_paper_states"
        # Actually table() is called multiple times, we need to check the calls.
        
        # Get all calls to table()
        table_calls = [call.args[0] for call in self.mock_db.table.call_args_list]
        self.assertIn("papers", table_calls)
        self.assertNotIn("user_paper_states", table_calls)

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_personalized_filter_only(self, mock_call_llm):
        """
        Test that filter_papers only updates user states (user_paper_states table).
        """
        # Mock LLM response for filter
        mock_call_llm.return_value = json.dumps({
            "why_this_paper": "Reason",
            "relevance_score": 0.8,
            "accepted": True
        })
        
        # Execute
        results = self.service.filter_papers([self.paper], self.user_profile)
        
        # Verify
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].user_state.why_this_paper, "Reason")
        
        # Check DB calls
        # Should update 'user_paper_states' table
        # self.mock_db.table.assert_any_call("user_paper_states") # This might fail if table() called multiple times
        
        table_calls = [call.args[0] for call in self.mock_db.table.call_args_list]
        self.assertIn("user_paper_states", table_calls)
        
        # Should NOT update 'papers' table (in this call)
        # Wait, filter_papers doesn't touch papers table, correct.
        self.assertNotIn("papers", table_calls)

if __name__ == '__main__':
    unittest.main()
