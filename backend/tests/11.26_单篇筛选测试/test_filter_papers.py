import sys
import os
import json
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata, UserPaperState
from app.schemas.user import UserProfile, UserInfo

class TestFilterPapers(unittest.TestCase):
    """
    测试论文筛选功能
    目标函数: paper_service.filter_papers
    """

    def setUp(self):
        # Mock DB to avoid real connection
        self.mock_db = MagicMock()
        self.mock_table = MagicMock()
        self.mock_db.table.return_value = self.mock_table
        self.mock_table.upsert.return_value.execute.return_value = None

        # Patch get_db used in PaperService
        with patch('app.services.paper_service.get_db', return_value=self.mock_db):
            self.service = PaperService()
            self.service.db = self.mock_db # Ensure instance uses mock

        # Test Data
        self.paper_data = {
            "id": "2511.16680",
            "category": ["cs.CL", "cs.AI"],
            "title": "Shona spaCy: A Morphological Analyzer for an Under-Resourced Bantu Language",
            "authors": ["Happymore Masoka"],
            "published_date": "2025-11-12",
            "links": {
                "pdf": "https://arxiv.org/pdf/2511.16680v1",
                "arxiv": "http://arxiv.org/abs/2511.16680v1",
                "html": "http://arxiv.org/html/2511.16680v1"
            },
            "comment": "",
            "abstract": "Despite rapid advances in multilingual natural language processing (NLP), the Bantu language Shona remains under-served in terms of morphological analysis and language-aware tools. This paper presents Shona spaCy, an open-source, rule-based morphological pipeline for Shona built on the spaCy framework. The system combines a curated JSON lexicon with linguistically grounded rules to model noun-class prefixes (Mupanda 1-18), verbal subject concords, tense-aspect markers, ideophones, and clitics, integrating these into token-level annotations for lemma, part-of-speech, and morphological features. The toolkit is available via pip install shona-spacy, with source code at https://github.com/HappymoreMasoka/shona-spacy and a PyPI release at https://pypi.org/project/shona-spacy/0.1.4/. Evaluation on formal and informal Shona corpora yields 90% POS-tagging accuracy and 88% morphological-feature accuracy, while maintaining transparency in its linguistic decisions. By bridging descriptive grammar and computational implementation, Shona spaCy advances NLP accessibility and digital inclusion for Shona speakers and provides a template for morphological analysis tools for other under-resourced Bantu languages."
        }

        # Construct PersonalizedPaper
        meta = RawPaperMetadata(**self.paper_data)
        self.paper = PersonalizedPaper(meta=meta, analysis=None, user_state=None)

        # Mock User Profile
        self.user_profile = UserProfile(
            info=UserInfo(
                id="test_user_id",
                email="test@example.com",
                name="Test User",
                avatar="",
                nickname="Tester"
            ),
            focus={
                "domains": [],
                "keywords": [],
                "authors": [],
                "institutions": []
            }, 
            status={
                "currentTask": "",
                "futureGoal": "",
                "stage": "",
                "purpose": []
            },
            memory={
                "readPapers": [],
                "dislikedPapers": []
            }
        )

        self.output_dir = os.path.join(os.path.dirname(__file__), "result")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "filter_result.json")

    @patch('app.utils.user_profile_utils.get_user_profile_context')
    def test_filter_papers(self, mock_get_context):
        """
        测试 filter_papers 函数
        """
        # Mock context return
        mock_get_context.return_value = {
            "focus": {
                "domains": ["cs.LG", "cs.AI"],
                "keywords": ["LLM", "Agent", "Med"],
                "authors": ["Junxian He"],
                "institutions": ["AI2", "DeepSeek"]
            },
            "status": {
                "currentTask": "尝试独立开发论文查询agent",
                "futureGoal": "agent/LLM赋能医疗",
                "stage": "初学者",
                "purpose": ["关注前沿技术发展", "未来准备走工业界"]
            }
        }

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始筛选论文: {self.paper.meta.title}")

        # Run filter
        # Note: filter_papers uses ThreadPoolExecutor which might swallow exceptions if not handled, 
        # but here we wait for results so exceptions should propagate or result in empty list/error print.
        response = self.service.filter_papers([self.paper], self.user_profile)

        self.assertEqual(response.total_analyzed, 1, "应返回 1 篇论文")
        
        # 之前测试结果显示该论文被拒绝，所以应该在 rejected_papers 中
        if response.accepted_count > 0:
            self.assertEqual(len(response.selected_papers), 1, "Selected papers 列表长度应为 1")
            result_item = response.selected_papers[0]
        else:
            self.assertEqual(len(response.rejected_papers), 1, "Rejected papers 列表长度应为 1")
            result_item = response.rejected_papers[0]
        
        print(f"  - Relevance Score: {result_item.relevance_score}")
        print(f"  - Accepted: {result_item.accepted}")
        print(f"  - Reason: {result_item.why_this_paper[:50]}...")

        # Save result
        output_data = response.model_dump()
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 筛选完成。结果已保存至: {self.output_file}")

if __name__ == "__main__":
    unittest.main()
