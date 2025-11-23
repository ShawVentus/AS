import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from crawler.spiders.arxiv import ArxivSpider
from crawler.pipelines import ArxivApiPipeline
from crawler.items import PaperItem

def test_logic():
    print("Testing Spider Logic...")
    spider = ArxivSpider()
    # Mock response is hard, so let's just test the pipeline with a fake item
    
    print("Testing Pipeline Logic...")
    pipeline = ArxivApiPipeline()
    
    # Create a dummy item with a known valid ID
    item = PaperItem()
    item["id"] = "2310.12345" # Example ID, might not exist, let's use a real one
    item["id"] = "1706.03762" # Attention Is All You Need
    item["category"] = "cs.CL"
    item["tags"] = ["cs.CL"]
    item["title"] = ""
    item["authors"] = []
    item["published_date"] = ""
    item["tldr"] = ""
    item["details"] = {}
    item["links"] = {}
    item["citation_count"] = 0
    
    print(f"Processing item: {item['id']}")
    
    class MockSpider:
        class Logger:
            def info(self, msg): print(f"INFO: {msg}")
            def warning(self, msg): print(f"WARN: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
        logger = Logger()
        
    processed_item = pipeline.process_item(item, MockSpider())
    
    print("\nProcessed Item:")
    print(f"Title: {processed_item['title']}")
    print(f"Authors: {processed_item['authors']}")
    print(f"Abstract: {processed_item['details']['abstract'][:100]}...")
    
    if processed_item['title'] == "Attention Is All You Need":
        print("\n✅ Pipeline Test Passed!")
    else:
        print("\n❌ Pipeline Test Failed!")

if __name__ == "__main__":
    test_logic()
