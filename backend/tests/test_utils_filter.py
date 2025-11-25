import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.paper_analysis_utils import analyze_single_paper

class TestUtilsFilter(unittest.TestCase):
    
    @patch('app.utils.paper_analysis_utils.llm_service')
    def test_analyze_single_paper(self, mock_llm_service):
        """Test analyze_single_paper with mocked LLM service"""
        
        # Mock read_prompt
        mock_llm_service.read_prompt.return_value = "Profile: {user_profile}, Paper: {paper}"
        
        # Mock call_llm response
        mock_response = {
            "why_this_paper": "Relevant because...",
            "relevance_score": 0.85,
            "accepted": True
        }
        mock_llm_service.call_llm.return_value = json.dumps(mock_response)
        
        # Input
        paper = {"title": "Test Paper", "abstract": "Abstract"}
        user_profile = {"focus": "AI"}
        
        # Execute
        result = analyze_single_paper(paper, user_profile)
        
        # Verify Prompt Formatting
        # Check if call_llm was called with correctly formatted JSON strings
        args, _ = mock_llm_service.call_llm.call_args
        prompt_arg = args[0]
        self.assertIn('"title": "Test Paper"', prompt_arg)
        self.assertIn('"focus": "AI"', prompt_arg)
        
        # Verify Result
        self.assertEqual(result["why_this_paper"], "Relevant because...")
        self.assertEqual(result["relevance_score"], 0.85)
        self.assertTrue(result["accepted"])
        
        print("\n[Pass] Utils Filter Paper Verified")

if __name__ == '__main__':
    unittest.main()
