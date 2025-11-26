import sys
import os
import json
import unittest
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.paper_analysis_utils import analyze_paper_content

class TestPaperAnalysis(unittest.TestCase):
    """
    测试论文分析功能
    目标函数: paper_analysis_utils.analyze_paper_content
    """

    def setUp(self):
        # 测试数据
        self.paper_data = {
            "id": "2511.16680",
            "category": [
                "cs.CL",
                "cs.AI"
            ],
            "title": "Shona spaCy: A Morphological Analyzer for an Under-Resourced Bantu Language",
            "authors": [
                "Happymore Masoka"
            ],
            "published_date": "2025-11-12",
            "links": {
                "pdf": "https://arxiv.org/pdf/2511.16680v1",
                "arxiv": "http://arxiv.org/abs/2511.16680v1",
                "html": "http://arxiv.org/html/2511.16680v1"
            },
            "comment": "",
            "abstract": "Despite rapid advances in multilingual natural language processing (NLP), the Bantu language Shona remains under-served in terms of morphological analysis and language-aware tools. This paper presents Shona spaCy, an open-source, rule-based morphological pipeline for Shona built on the spaCy framework. The system combines a curated JSON lexicon with linguistically grounded rules to model noun-class prefixes (Mupanda 1-18), verbal subject concords, tense-aspect markers, ideophones, and clitics, integrating these into token-level annotations for lemma, part-of-speech, and morphological features. The toolkit is available via pip install shona-spacy, with source code at https://github.com/HappymoreMasoka/shona-spacy and a PyPI release at https://pypi.org/project/shona-spacy/0.1.4/. Evaluation on formal and informal Shona corpora yields 90% POS-tagging accuracy and 88% morphological-feature accuracy, while maintaining transparency in its linguistic decisions. By bridging descriptive grammar and computational implementation, Shona spaCy advances NLP accessibility and digital inclusion for Shona speakers and provides a template for morphological analysis tools for other under-resourced Bantu languages."
        }
        
        # 输出目录配置
        self.output_dir = os.path.join(os.path.dirname(__file__), "result")
        os.makedirs(self.output_dir, exist_ok=True)
        self.output_file = os.path.join(self.output_dir, "analysis_result.json")

    def test_analyze_paper_content(self):
        """
        测试 analyze_paper_content 函数
        """
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 开始分析论文: {self.paper_data['title']}")
        
        # 调用待测试函数
        try:
            result = analyze_paper_content(self.paper_data)
        except Exception as e:
            self.fail(f"分析过程发生异常: {e}")

        # 验证结果不为空
        self.assertIsNotNone(result, "分析结果不应为 None")
        
        # 验证返回字段 (预期 6 个字段)
        expected_fields = ["tldr", "motivation", "method", "result", "conclusion", "tags"]
        for field in expected_fields:
            self.assertIn(field, result, f"结果缺少字段: {field}")
            print(f"  - {field}: {str(result[field])[:50]}...") # 打印前50个字符预览

        # 验证 tags 类型
        self.assertIsInstance(result["tags"], dict, "Tags 应当是字典类型")

        # 保存结果到文件
        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 分析完成。结果已保存至: {self.output_file}")

if __name__ == "__main__":
    unittest.main()
