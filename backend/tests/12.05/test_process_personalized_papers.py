import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 添加 backend 目录到 sys.path，以便导入 app 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.services.scheduler import SchedulerService

class TestProcessPersonalizedPapers(unittest.TestCase):
    """
    测试 SchedulerService.process_personalized_papers 方法。
    
    主要测试逻辑：
    1. 模拟数据库返回的 daily_papers 和 profiles。
    2. 模拟 user_service.get_profile 返回的用户画像。
    3. 模拟 user_paper_states 检查已处理的论文。
    4. 验证 paper_service.filter_papers 是否被正确调用。
    """

    def setUp(self):
        """
        测试前的准备工作。
        初始化 SchedulerService 并 mock 其 db 属性。
        
        Args:
            None
        
        Returns:
            None
        """
        self.scheduler = SchedulerService()
        self.scheduler.db = MagicMock()

    @patch("app.services.scheduler.user_service")
    @patch("app.services.scheduler.paper_service")
    def test_process_personalized_papers_success(self, mock_paper_service, mock_user_service):
        """
        测试成功处理个性化论文的场景。
        
        场景描述：
        - 存在 2 篇新论文。
        - 存在 1 个用户。
        - 用户尚未处理过这两篇论文。
        
        预期结果：
        - filter_papers 被调用一次，传入包含 2 篇论文的列表。
        
        Args:
            mock_paper_service: 模拟的 paper_service 模块
            mock_user_service: 模拟的 user_service 模块
            
        Returns:
            None
        """
        # 1. Mock daily_papers
        mock_raw_papers = [
            {
                "id": "paper1",
                "title": "Title 1",
                "authors": "Author 1",
                "published_date": "2023-01-01",
                "category": "cs.AI",
                "abstract": "Abstract 1",
                "links": "http://link1",
                "comment": "Comment 1"
            },
            {
                "id": "paper2",
                "title": "Title 2",
                "authors": "Author 2",
                "published_date": "2023-01-02",
                "category": "cs.CL",
                "abstract": "Abstract 2",
                "links": "http://link2",
                "comment": "Comment 2"
            }
        ]
        # 模拟 self.db.table("daily_papers").select("*").execute().data
        self.scheduler.db.table.return_value.select.return_value.execute.return_value.data = mock_raw_papers
        
        # 为了区分不同的 table 调用，我们需要根据 table name 返回不同的 mock 对象
        # 这里简化处理，通过 side_effect 或者链式调用的返回值来控制
        # 由于 scheduler 代码中是 self.db.table("daily_papers")... 和 self.db.table("profiles")...
        # 我们可以通过 side_effect 来根据 table name 返回不同的 mock
        
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "daily_papers":
                mock_table.select.return_value.execute.return_value.data = mock_raw_papers
            elif table_name == "profiles":
                mock_table.select.return_value.execute.return_value.data = [{"user_id": "user1"}]
            elif table_name == "user_paper_states":
                # 模拟该用户没有处理过任何论文
                # 优化后的逻辑使用了 .in_()
                mock_query = mock_table.select.return_value.eq.return_value
                mock_query.in_.return_value.execute.return_value.data = []
                return mock_table
            return mock_table
            
        self.scheduler.db.table.side_effect = table_side_effect

        # 2. Mock user_service.get_profile
        mock_profile = MagicMock()
        mock_profile.info.name = "Test User"
        mock_user_service.get_profile.return_value = mock_profile

        # 3. Run the method
        self.scheduler.process_personalized_papers()

        # 4. Verify
        # 验证 user_service.get_profile 被调用
        mock_user_service.get_profile.assert_called_with("user1")
        
        # 验证 paper_service.filter_papers 被调用
        self.assertTrue(mock_paper_service.filter_papers.called)
        call_args = mock_paper_service.filter_papers.call_args
        # call_args[0] 是位置参数元组: (papers_to_filter, user_profile, user_id)
        papers_arg = call_args[0][0]
        profile_arg = call_args[0][1]
        user_id_arg = call_args[0][2]
        
        self.assertEqual(len(papers_arg), 2)
        self.assertEqual(papers_arg[0].meta.id, "paper1")
        self.assertEqual(papers_arg[1].meta.id, "paper2")
        self.assertEqual(profile_arg, mock_profile)
        self.assertEqual(user_id_arg, "user1")

    @patch("app.services.scheduler.user_service")
    @patch("app.services.scheduler.paper_service")
    def test_process_personalized_papers_skip_processed(self, mock_paper_service, mock_user_service):
        """
        测试跳过已处理论文的场景。
        
        场景描述：
        - 存在 2 篇新论文 (paper1, paper2)。
        - 用户已经处理过 paper1。
        
        预期结果：
        - filter_papers 仅接收 paper2。
        
        Args:
            mock_paper_service: 模拟的 paper_service 模块
            mock_user_service: 模拟的 user_service 模块
            
        Returns:
            None
        """
        mock_raw_papers = [
            {"id": "paper1", "title": "T1", "authors": "A1", "published_date": "D1", "category": "C1", "abstract": "Ab1", "links": "L1"},
            {"id": "paper2", "title": "T2", "authors": "A2", "published_date": "D2", "category": "C2", "abstract": "Ab2", "links": "L2"}
        ]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "daily_papers":
                mock_table.select.return_value.execute.return_value.data = mock_raw_papers
            elif table_name == "profiles":
                mock_table.select.return_value.execute.return_value.data = [{"user_id": "user1"}]
            elif table_name == "user_paper_states":
                # 模拟用户已处理 paper1
                # 优化后的逻辑使用了 .in_()
                mock_query = mock_table.select.return_value.eq.return_value
                mock_query.in_.return_value.execute.return_value.data = [{"paper_id": "paper1"}]
                return mock_table
            return mock_table
            
        self.scheduler.db.table.side_effect = table_side_effect

        mock_profile = MagicMock()
        mock_profile.info.name = "Test User"
        mock_user_service.get_profile.return_value = mock_profile

        self.scheduler.process_personalized_papers()

        # Verify
        # 验证 in_ 被调用
        # 这里的调用链比较长: table().select().eq().in_().execute()
        # 我们主要验证 filter_papers 的结果是否正确
        self.assertTrue(mock_paper_service.filter_papers.called)
        call_args = mock_paper_service.filter_papers.call_args
        papers_arg = call_args[0][0]
        
        self.assertEqual(len(papers_arg), 1)
        self.assertEqual(papers_arg[0].meta.id, "paper2")

if __name__ == "__main__":
    unittest.main()
