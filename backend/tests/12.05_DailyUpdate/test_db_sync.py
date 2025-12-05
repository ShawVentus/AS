# 12.05_DailyUpdate/test_db_sync.py
# 测试双数据库同步逻辑
# 功能: 模拟 analyze_paper 执行，验证 daily_papers 更新且 papers 表插入

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata

class TestDBSync(unittest.TestCase):
    def setUp(self):
        self.service = PaperService()
        self.service.db = MagicMock()

    @patch("app.utils.paper_analysis_utils.analyze_paper_content")
    def test_analyze_and_sync(self, mock_analyze):
        """测试分析后同步到公共库"""
        print("\n--- Testing Analyze and Sync ---")
        
        # 1. Mock Analysis Result
        mock_analysis = {
            "tldr": "Test TLDR",
            "motivation": "Test Motivation",
            "method": "Test Method",
            "result": "Test Result",
            "conclusion": "Test Conclusion",
            "tags": ["AI"]
        }
        mock_analyze.return_value = mock_analysis
        
        # 2. Prepare Input Paper
        meta = RawPaperMetadata(
            id="test.123",
            title="Test Paper",
            authors=["Author A"],
            published_date="2025-12-05",
            category=["cs.CL"],
            abstract="Abstract...",
            links={"pdf": "http://pdf", "arxiv": "http://arxiv", "html": "http://html"},
            comment=None
        )
        paper = PersonalizedPaper(meta=meta, analysis=None, user_state=None)
        
        # 3. Run Analyze
        result = self.service.analyze_paper(paper)
        
        # 4. Verify DB Calls
        # a. Update daily_papers
        self.service.db.table.assert_any_call("daily_papers")
        # b. Insert papers
        self.service.db.table.assert_any_call("papers")
        
        print("Result: DB Calls Verified (Daily Update + Public Insert)")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.tldr, "Test TLDR")

if __name__ == "__main__":
    unittest.main()
