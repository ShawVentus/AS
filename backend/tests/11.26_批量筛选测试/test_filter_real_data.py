import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
from app.schemas.user import UserProfile
from app.services.mock_data import USER_PROFILE

class TestFilterRealData(unittest.TestCase):
    """
    测试使用真实数据进行论文筛选 (原生能力测试)
    目标函数: paper_service.filter_papers
    """

    # --- 配置参数 ---
    # 输入文件路径
    SOURCE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/crawler/stage2_api_details_20251124_213648.json"))
    # 输出目录
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "result")
    # 输出文件
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "filtered_papers.json")
    # 测试论文数量限制
    PAPER_LIMIT = 50

    def setUp(self):
        # 确保输出目录存在
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        # Mock DB (避免真实数据库连接)
        self.mock_db = MagicMock()
        self.mock_table = MagicMock()
        self.mock_db.table.return_value = self.mock_table
        self.mock_table.upsert.return_value.execute.return_value = None

        # Patch get_db
        with patch('app.services.paper_service.get_db', return_value=self.mock_db):
            self.service = PaperService()
            self.service.db = self.mock_db

        # 准备用户画像
        self.user_profile = UserProfile(**USER_PROFILE)

    def load_papers(self):
        """加载并转换真实论文数据"""
        print(f"Loading papers from: {self.SOURCE_FILE}")
        with open(self.SOURCE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        papers = []
        for item in data[:self.PAPER_LIMIT]:
            # 确保 category 是列表
            if isinstance(item.get("category"), str):
                item["category"] = [item["category"]]
            
            # 构造 RawPaperMetadata
            meta = RawPaperMetadata(**item)
            # 构造 PersonalizedPaper
            paper = PersonalizedPaper(meta=meta, analysis=None, user_state=None)
            papers.append(paper)
        
        return papers

    @patch('app.utils.user_profile_utils.get_user_profile_context')
    def test_filter_real_papers(self, mock_get_context):
        """
        使用真实数据测试 filter_papers
        """
        # 1. 加载数据
        papers = self.load_papers()
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(papers)} papers for testing.")

        # 2. 执行筛选 (核心测试目标)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting filtering process...")
        filter_response = self.service.filter_papers(papers, self.user_profile)

        # 3. 保存结果 (直接保存 FilterResponse 对象)
        # 将 Pydantic 对象转换为字典
        output_data = filter_response.model_dump()
        
        with open(self.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Test finished.")
        print(f"Task Created At: {filter_response.created_at}")
        print(f"Total Analyzed: {filter_response.total_analyzed}")
        print(f"Accepted: {filter_response.accepted_count} (Sorted by Score)")
        print(f"Rejected: {filter_response.rejected_count} (Sorted by Score)")
        print(f"Results saved to: {self.OUTPUT_FILE}")

if __name__ == "__main__":
    unittest.main()
