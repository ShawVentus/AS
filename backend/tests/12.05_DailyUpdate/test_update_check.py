# 12.05_DailyUpdate/test_update_check.py
# 测试 Arxiv 更新检测逻辑
# 功能: 模拟 Arxiv HTML 响应，验证 check_arxiv_update 的解析和状态对比逻辑

import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.services.scheduler import SchedulerService

class TestUpdateCheck(unittest.TestCase):
    def setUp(self):
        self.scheduler = SchedulerService()
        # Mock DB
        self.scheduler.db = MagicMock()

    @patch("httpx.get")
    def test_update_detected(self, mock_get):
        """测试检测到更新的情况"""
        print("\n--- Testing Update Detected ---")
        
        # 1. Mock Arxiv Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <h3>Showing new listings for Friday, 5 December 2025</h3>
            <ul>...</ul>
        </html>
        """
        mock_get.return_value = mock_response
        
        # 2. Mock DB (Last update was yesterday)
        mock_db_response = MagicMock()
        mock_db_response.data = [{"value": "Thursday, 4 December 2025"}]
        self.scheduler.db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_db_response
        
        # 3. Run Check
        result = self.scheduler.check_arxiv_update()
        
        # 4. Verify
        self.assertTrue(result)
        # Verify DB update called
        self.scheduler.db.table("system_status").upsert.assert_called_with({
            "key": "last_arxiv_update",
            "value": "Friday, 5 December 2025"
        })
        print("Result: Update Detected (Correct)")

    @patch("httpx.get")
    def test_no_update(self, mock_get):
        """测试未检测到更新的情况"""
        print("\n--- Testing No Update ---")
        
        # 1. Mock Arxiv Response (Same date)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <h3>Showing new listings for Friday, 5 December 2025</h3>
        </html>
        """
        mock_get.return_value = mock_response
        
        # 2. Mock DB (Last update was same)
        mock_db_response = MagicMock()
        mock_db_response.data = [{"value": "Friday, 5 December 2025"}]
        self.scheduler.db.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_db_response
        
        # 3. Run Check
        result = self.scheduler.check_arxiv_update()
        
        # 4. Verify
        self.assertFalse(result)
        print("Result: No Update (Correct)")

if __name__ == "__main__":
    unittest.main()
