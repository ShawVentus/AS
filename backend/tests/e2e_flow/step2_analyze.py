import sys
import os
import json
import asyncio

# 将backend添加到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.paper_service import paper_service
from schemas.paper import Paper
from services.mock_data import USER_PROFILE
from schemas.user import UserProfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE = os.path.join(DATA_DIR, "1_crawl_results.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "2_analysis_results.json")

async def run_step2():
    print("=== Step 2: Analyze Papers ===")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        sys.exit(1)
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers_data = json.load(f)
        
    papers = [Paper(**p) for p in papers_data]
    profile = UserProfile(**USER_PROFILE)
    
    analyzed_papers = []
    print(f"Analyzing {len(papers)} papers...")
    
    for p in papers:
        print(f"Analyzing: {p.title[:30]}...")
        try:
            # analyze_paper更新数据库并返回分析结果
            analysis = paper_service.analyze_paper(p, profile)
            
            # 为下一步更新本地论文对象的分析结果
            p.tldr = analysis.summary
            p.suggestion = analysis.recommendation_reason
            p.details.motivation = analysis.key_points.motivation
            p.details.method = analysis.key_points.method
            p.details.result = analysis.key_points.result
            p.details.conclusion = analysis.key_points.conclusion
            
            analyzed_papers.append(p.model_dump())
        except Exception as e:
            print(f"Error analyzing paper {p.id}: {e}")
            
    if not analyzed_papers:
        print("❌ No papers analyzed successfully!")
        sys.exit(1)
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(analyzed_papers, f, ensure_ascii=False, indent=2)
        
    print(f"✅ Analyzed {len(analyzed_papers)} papers.")
    print(f"Saved results to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_step2())
