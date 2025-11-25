import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json
from typing import List

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, PaperMetadata, UserPaperState
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

# Configuration
TEST_DATA_LIMIT = 5 # Process only the first N papers
OUTPUT_DIR = "/Users/mac/Desktop/AS/backend/tests/pre_select"

class TestFilterRealData(unittest.TestCase):
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

        # 1. Define User Profile
        self.user_profile = UserProfile(
            info=UserInfo(name="Test User", email="test@example.com", avatar="", nickname="Tester"),
            focus=Focus(domains=["NLP", "LLM"], keywords=["Large Language Models", "RAG", "Reasoning"], authors=[], institutions=[]),
            context=Context(currentTask="Research", futureGoal="", stage="", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )

        # 2. Load Real Data
        json_path = os.path.join(os.path.dirname(__file__), "crawler/stage2_api_details_20251124_213648.json")
        if not os.path.exists(json_path):
            self.skipTest(f"Data file not found: {json_path}")
            
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        self.papers = []
        for item in raw_data:
            if "tags" not in item:
                item["tags"] = {}
            try:
                self.papers.append(PersonalizedPaper(**item, user_state=None))
            except Exception as e:
                print(f"Skipping invalid paper {item.get('id')}: {e}")

        print(f"\nLoaded {len(self.papers)} papers from JSON.")

    def tearDown(self):
        self.db_patcher.stop()

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_filter_real_papers(self, mock_call_llm):
        """
        Test filtering using the loaded real papers with limit and file output.
        """
        
        # Mock LLM Logic
        def mock_llm_response(prompt):
            if "LLM" in prompt or "Language Model" in prompt:
                return json.dumps({
                    "why_this_paper": "Relevant to LLM.",
                    "relevance_score": 0.9,
                    "accepted": True
                })
            else:
                return json.dumps({
                    "why_this_paper": "Not relevant.",
                    "relevance_score": 0.1,
                    "accepted": False
                })

        mock_call_llm.side_effect = mock_llm_response
        
        # Apply Limit
        papers_to_process = self.papers[:TEST_DATA_LIMIT]
        print(f"Processing first {len(papers_to_process)} papers (Limit: {TEST_DATA_LIMIT})...")
        
        # Execute
        results = self.service.filter_papers(papers_to_process, self.user_profile)
        
        # Verify
        accepted_count = sum(1 for p in results if p.user_state.accepted)
        rejected_count = sum(1 for p in results if not p.user_state.accepted)
        
        print(f"\nProcessing Complete.")
        print(f"Total Processed: {len(results)}")
        print(f"Accepted: {accepted_count}")
        print(f"Rejected: {rejected_count}")
        
        # Save Results
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        output_file = os.path.join(OUTPUT_DIR, "filtered_results.json")
        output_data = [p.model_dump() for p in results]
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"Results saved to: {output_file}")
        
        # Basic Assertions
        self.assertEqual(len(results), len(papers_to_process))
        self.assertEqual(self.mock_table.upsert.call_count, len(papers_to_process))
        
        print("[Pass] Real data filtering test passed.")

if __name__ == '__main__':
    unittest.main()
