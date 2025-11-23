import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.paper_service import PaperService
from app.schemas.paper import Paper

class TestPaperService(unittest.TestCase):
    @patch('app.services.paper_service.get_db')
    def setUp(self, mock_get_db):
        self.mock_db = MagicMock()
        mock_get_db.return_value = self.mock_db
        self.paper_service = PaperService()

    def test_get_papers(self):
        """Test fetching papers from DB"""
        # Mock DB response
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "test_1",
                "title": "Test Paper",
                "authors": ["Author A"],
                "date": "2023-11-22",
                "category": "cs.AI",
                "tldr": "TLDR",
                "suggestion": "Read",
                "tags": ["AI"],
                "details": {
                    "motivation": "Test Motivation",
                    "method": "Test Method",
                    "result": "Test Result",
                    "conclusion": "Test Conclusion",
                    "abstract": "Test Abstract"
                },
                "links": {"pdf": "", "arxiv": "", "html": ""},
                "citationCount": 0,
                "year": 2023
            }
        ]
        self.mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_response

        papers = self.paper_service.get_papers()
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].title, "Test Paper")
        print("\n[Pass] Successfully fetched papers (Mocked DB)")

    @patch('subprocess.run')
    def test_crawl_arxiv_new(self, mock_subprocess):
        """Test crawler triggering"""
        # Mock subprocess to avoid running actual crawler
        mock_subprocess.return_value.returncode = 0
        
        # Mock get_papers to return something after crawl
        with patch.object(self.paper_service, 'get_papers', return_value=[]):
            self.paper_service.crawl_arxiv_new()
            
        mock_subprocess.assert_called()
        print("\n[Pass] Successfully triggered crawler (Mocked)")

if __name__ == '__main__':
    unittest.main()
