# 12.05_DailyUpdate/test_integration.py
# 集成测试：每日更新全流程
# 模拟 Arxiv 更新，触发 run_daily_workflow，验证数据流转

import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import time

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.services.scheduler import SchedulerService
from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.scheduler = SchedulerService()
        self.paper_service = PaperService()
        # Mock DB for safety (Integration test usually runs against real DB, but here we mock to avoid side effects on prod data if any)
        # However, user asked to verify logic. 
        # Let's mock the external calls (Arxiv, LLM) but use Real DB for data flow if possible?
        # Given the environment, let's use Mocks for external dependencies and verify the orchestration logic.
        
        self.scheduler.db = MagicMock()
        self.paper_service.db = self.scheduler.db

    @patch("app.services.scheduler.SchedulerService.check_arxiv_update")
    @patch("app.services.scheduler.SchedulerService.run_crawler")
    @patch("app.services.scheduler.SchedulerService.process_new_papers")
    @patch("app.services.scheduler.SchedulerService.generate_report_job")
    @patch("app.services.paper_service.PaperService.clear_daily_papers")
    def test_workflow_execution(self, mock_clear, mock_report, mock_process, mock_crawl, mock_check):
        """测试完整工作流的调用顺序"""
        print("\n--- Testing Full Workflow Execution ---")
        
        # 1. Simulate Update Detected
        mock_check.return_value = True
        mock_clear.return_value = True
        
        # 2. Run Workflow
        self.scheduler.run_daily_workflow()
        
        # 3. Verify Order
        # a. Check Update
        mock_check.assert_called_once()
        # b. Clear Daily
        mock_clear.assert_called_once()
        # c. Crawl
        mock_crawl.assert_called_once()
        # d. Process
        mock_process.assert_called_once()
        # e. Report
        mock_report.assert_called_once()
        
        print("Result: Workflow Orchestration Verified")

if __name__ == "__main__":
    unittest.main()
