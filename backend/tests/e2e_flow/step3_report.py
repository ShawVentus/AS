import sys
import os
import json
import asyncio

# 将backend添加到sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from services.report_service import report_service
from schemas.paper import Paper
from services.mock_data import USER_PROFILE
from schemas.user import UserProfile

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INPUT_FILE = os.path.join(DATA_DIR, "2_analysis_results.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "3_report_results.json")

async def run_step3():
    print("=== Step 3: Generate Report ===")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        sys.exit(1)
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        papers_data = json.load(f)
        
    papers = [Paper(**p) for p in papers_data]
    profile = UserProfile(**USER_PROFILE)
    
    print(f"Generating report for {len(papers)} papers...")
    
    try:
        report, usage, email_success = report_service.generate_daily_report(papers, profile)
        
        if not report:
            print("❌ Report generation returned None")
            sys.exit(1)
            
        print(f"✅ Report Generated: {report.title}")
        print(f"Summary: {report.summary[:50]}...")
        
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, ensure_ascii=False, indent=2)
            
        print(f"Saved results to {OUTPUT_FILE}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_step3())
