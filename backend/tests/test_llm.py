import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import QwenService

class TestLLMService(unittest.TestCase):
    def setUp(self):
        self.llm_service = QwenService()

    def test_read_prompt(self):
        """Test if prompts can be read correctly"""
        # This assumes the prompt files exist. 
        # If we want to be pure unit test, we should mock open, 
        # but here we also want to verify the files exist.
        try:
            prompt = self.llm_service._read_prompt("filter.md")
            self.assertTrue(len(prompt) > 0)
            print("\n[Pass] Successfully read filter.md")
        except FileNotFoundError:
            self.fail("filter.md not found")

    def test_analyze_paper(self):
        """Test analyze_paper with mocked API response"""
        # Setup mock response
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = json.dumps({
            "tldr": "Test TLDR",
            "motivation": "Test Motivation",
            "method": "Test Method",
            "result": "Test Result",
            "conclusion": "Test Conclusion",
            "why_this_paper": "Test Reason",
            "tags": ["AI", "Test"]
        })
        
        # Mock the client instance directly
        self.llm_service.client = MagicMock()
        self.llm_service.client.chat.completions.create.return_value = mock_completion

        paper = {"title": "Test Paper", "abstract": "Test Abstract"}
        profile = "Test Profile"
        
        result = self.llm_service.analyze_paper(paper, profile)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['tldr'], "Test TLDR")
        print("\n[Pass] Successfully analyzed paper (Mocked)")

if __name__ == '__main__':
    unittest.main()
