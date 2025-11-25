# 2025-11-25 00:21:37
import unittest
from unittest.mock import patch, MagicMock
import time
import json
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, PaperMetadata, UserPaperState
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

class TestFilterService(unittest.TestCase):
    def setUp(self):
        # Mock DB
        self.mock_db = MagicMock()
        self.mock_table = MagicMock()
        self.mock_db.table.return_value = self.mock_table
        
        # Patch get_db to return our mock
        self.db_patcher = patch('app.services.paper_service.get_db', return_value=self.mock_db)
        self.db_patcher.start()
        
        # Initialize Service (it will use the mocked get_db)
        self.service = PaperService()
        self.service.db = self.mock_db # Ensure instance uses mock

        # Prepare Mock Data
        self.user_profile = UserProfile(
            info=UserInfo(name="Test User", email="test@example.com", avatar="", nickname="Tester"),
            focus=Focus(domains=["AI"], keywords=["LLM"], authors=[], institutions=[]),
            context=Context(currentTask="Test", futureGoal="Test", stage="Test", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )
        
        self.papers = []
        for i in range(5):
            self.papers.append(PersonalizedPaper(
                id=f"p{i}",
                title=f"Paper {i}",
                authors=["Author A"],
                published_date="2025-01-01", # Added
                abstract="Test Abstract",    # Added
                category="cs.AI",
                tldr="Summary",
                links={"pdf": "#", "arxiv": "#", "html": "#"},
                user_state=None
            ))

    def tearDown(self):
        self.db_patcher.stop()

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_concurrent_filtering(self, mock_call_llm):
        """Test if filtering is performed concurrently"""
        
        # Mock LLM response with delay
        def delayed_response(prompt):
            time.sleep(0.5) # Simulate 0.5s latency per call
            return json.dumps({
                "why_this_paper": "Concurrent Test",
                "relevance_score": 0.9,
                "accepted": True
            })
        
        mock_call_llm.side_effect = delayed_response
        
        start_time = time.time()
        results = self.service.filter_papers(self.papers, self.user_profile)
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n[Performance] Processed {len(self.papers)} papers in {duration:.2f}s (Expected < 1.5s for 5x0.5s parallel)")
        
        # Assertions
        # 1. Time check: If serial, it would take 5 * 0.5 = 2.5s. Parallel should be much faster.
        self.assertLess(duration, 2.0, "Filtering took too long, concurrency might not be working")
        
        # 2. Result check
        self.assertEqual(len(results), 5)
        self.assertEqual(results[0].user_state.why_this_paper, "Concurrent Test")
        
        # 3. DB Check
        # upsert should be called 5 times
        self.assertEqual(self.mock_table.upsert.call_count, 5)

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_database_update_structure(self, mock_call_llm):
        """Test if the correct data structure is sent to the database"""
        
        mock_call_llm.return_value = json.dumps({
            "why_this_paper": "DB Test",
            "relevance_score": 0.85,
            "accepted": True
        })
        
        single_paper = [self.papers[0]]
        self.service.filter_papers(single_paper, self.user_profile)
        
        # Verify arguments passed to upsert
        call_args = self.mock_table.upsert.call_args[0][0]
        
        self.assertEqual(call_args['user_id'], "test@example.com")
        self.assertEqual(call_args['paper_id'], "p0")
        self.assertEqual(call_args['relevance_score'], 0.85)
        self.assertEqual(call_args['why_this_paper'], "DB Test")
        self.assertEqual(call_args['accepted'], True)
        self.assertNotIn('created_at', call_args) # We deleted it in code
        
        print("\n[Pass] Database update structure verified")

if __name__ == '__main__':
    unittest.main()
