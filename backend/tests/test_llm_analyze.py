'''
2025-11-25 00:18:07 测试代码分析功能
'''

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.llm_service import QwenService

class TestLLMAnalyze(unittest.TestCase):
    def setUp(self):
        self.service = QwenService()

    @patch('app.services.llm_service.QwenService.read_prompt')
    @patch('app.services.llm_service.QwenService.call_llm')
    def test_analyze_paper_new_format(self, mock_call_llm, mock_read_prompt):
        """Test analyze_paper with the new prompt structure and tags dict"""
        
        # Mock Prompt Template
        mock_read_prompt.return_value = "Abstract: {abstract}"
        
        # Mock LLM Response (New Format)
        mock_response = {
            "tldr": "Summary",
            "motivation": "Motivation",
            "method": "Method",
            "result": "Result",
            "conclusion": "Conclusion",
            "tags": {
                "code": "https://github.com/example/code",
                "conference": "CVPR 2025"
            }
        }
        mock_call_llm.return_value = json.dumps(mock_response)
        
        # Input
        paper = {"abstract": "This is a test abstract."}
        user_profile = "{}" # Should be ignored by new logic
        
        # Execute
        result = self.service.analyze_paper(paper, user_profile)
        
        # Verify Prompt Formatting
        mock_read_prompt.assert_called_with("analyze.md")
        # Check if call_llm was called with formatted prompt
        # Since we mocked read_prompt to return "Abstract: {abstract}", 
        # the formatted prompt should be "Abstract: This is a test abstract."
        mock_call_llm.assert_called_with("Abstract: This is a test abstract.")
        
        # Verify Result Parsing
        self.assertEqual(result["tldr"], "Summary")
        self.assertIsInstance(result["tags"], dict)
        self.assertEqual(result["tags"]["code"], "https://github.com/example/code")
        self.assertEqual(result["tags"]["conference"], "CVPR 2025")
        
        print("\n[Pass] LLM Analyze Paper (New Format) Verified")

if __name__ == '__main__':
    unittest.main()
