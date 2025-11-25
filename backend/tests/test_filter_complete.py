# 2025-11-25 00:31:27
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, PaperMetadata, UserPaperState
from app.schemas.user import UserProfile, UserInfo, Focus, Context, Memory

class TestFilterComplete(unittest.TestCase):
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

        # 1. Define User Profile (Focus: LLM)
        self.user_profile = UserProfile(
            info=UserInfo(name="AI Researcher", email="researcher@example.com", avatar="", nickname="AI"),
            focus=Focus(domains=["Artificial Intelligence", "NLP"], keywords=["LLM", "Transformer", "RAG"], authors=[], institutions=[]),
            context=Context(currentTask="Researching efficient LLMs", futureGoal="", stage="", purpose=[]),
            memory=Memory(readPapers=[], dislikedPapers=[])
        )

        # 2. Define Papers (Mixed Relevance)
        self.raw_papers = [
            {
                "id": "p1",
                "title": "Efficient Large Language Models with RAG",
                "abstract": "This paper proposes a new method for RAG in LLMs...",
                "authors": ["Author A"],
                "category": "cs.CL",
                "published_date": "2025-01-01",
                "links": {"pdf": "url", "arxiv": "url", "html": "url"},
                "tldr": "",
                "tags": {}
            },
            {
                "id": "p2",
                "title": "Novel CRISPR Gene Editing Techniques",
                "abstract": "We explore new CRISPR methods for gene editing...",
                "authors": ["Author B"],
                "category": "q-bio.GN",
                "published_date": "2025-01-01",
                "links": {"pdf": "url", "arxiv": "url", "html": "url"},
                "tldr": "",
                "tags": {}
            }
        ]
        
        self.papers = [PersonalizedPaper(**p, user_state=None) for p in self.raw_papers]

    def tearDown(self):
        self.db_patcher.stop()

    @patch('app.utils.paper_analysis_utils.llm_service.call_llm')
    def test_filter_papers_logic(self, mock_call_llm):
        """
        Test the complete filtering logic.
        We simulate the LLM's decision making based on the prompt content.
        """
        
        # Mock LLM Logic
        def smart_llm_mock(prompt):
            # Simulate LLM reading the prompt
            # If prompt contains "LLM" or "RAG" -> Relevant
            # If prompt contains "CRISPR" -> Irrelevant
            
            if "LLM" in prompt or "RAG" in prompt:
                return json.dumps({
                    "why_this_paper": "Matches user focus on LLM and RAG.",
                    "relevance_score": 0.95,
                    "accepted": True
                })
            elif "CRISPR" in prompt:
                return json.dumps({
                    "why_this_paper": "Topic (Biology) is outside user domain (AI).",
                    "relevance_score": 0.1,
                    "accepted": False
                })
            else:
                return json.dumps({"why_this_paper": "Unsure", "relevance_score": 0.5, "accepted": False})

        mock_call_llm.side_effect = smart_llm_mock
        
        print("\n[Test] Running filter_papers with mixed content...")
        
        # Execute
        results = self.service.filter_papers(self.papers, self.user_profile)
        
        # Verify
        self.assertEqual(len(results), 2)
        
        # Check P1 (LLM Paper)
        p1 = next(p for p in results if p.id == "p1")
        self.assertTrue(p1.user_state.accepted)
        self.assertGreater(p1.user_state.relevance_score, 0.9)
        self.assertIn("Matches user focus", p1.user_state.why_this_paper)
        print(f"Paper '{p1.title}' -> Accepted: {p1.user_state.accepted} (Reason: {p1.user_state.why_this_paper})")
        
        # Check P2 (Bio Paper)
        p2 = next(p for p in results if p.id == "p2")
        self.assertFalse(p2.user_state.accepted)
        self.assertLess(p2.user_state.relevance_score, 0.2)
        self.assertIn("outside user domain", p2.user_state.why_this_paper)
        print(f"Paper '{p2.title}' -> Accepted: {p2.user_state.accepted} (Reason: {p2.user_state.why_this_paper})")
        
        # Verify DB Upserts
        # Should be called twice
        self.assertEqual(self.mock_table.upsert.call_count, 2)
        
        print("[Pass] Complete filtering logic verified.")

if __name__ == '__main__':
    unittest.main()
