import sys
import os
import json
import asyncio

# 将backend添加到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.paper_service import paper_service
from schemas.paper import Paper

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "1_crawl_results.json")

async def run_step1():
    print("=== Step 1: Crawl Papers ===")
    
    # 1. 触发爬取(测试速度限制为5)
    print("Triggering crawler (limit=5)...")
    try:
        # 注意: crawl_arxiv_new在当前实现中是同步的,但未来可能是异步的
        # 当前实现调用subprocess.run,所以它会阻塞。
        # 然而,服务方法在我之前查看的文件中定义为同步?
        # 让我们再次检查paper_service.py。它是: def crawl_arxiv_new(self, limit: int = 100) -> List[Paper]:
        # 但在endpoints中它被调用为: return paper_service.crawl_arxiv_new(limit) inside an async def.
        # 所以它是一个同步函数。
        papers = paper_service.crawl_arxiv_new(limit=5)
    except Exception as e:
        print(f"Error during crawl: {e}")
        # 如果爬取失败(例如网络问题),退回到只获取论文
        print("Fallback: Fetching existing papers from DB...")
        papers = paper_service.get_papers()

    if not papers:
        print("❌ No papers found!")
        sys.exit(1)

    print(f"✅ Found {len(papers)} papers.")
    
    # 2. 保存结果
    results = [p.model_dump() for p in papers[:5]] # 取前5篇
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
        
    print(f"Saved results to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_step1())
