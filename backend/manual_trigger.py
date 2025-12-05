# manual_trigger.py
# 手动触发每日更新工作流 (强制执行，忽略日期检查)
# 用于验证：爬虫 -> Daily DB -> Analysis -> Public DB 的完整链路

import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.services.scheduler import SchedulerService
from app.services.paper_service import PaperService

load_dotenv()

def manual_run():
    print("🚀 Starting Manual Trigger...")
    
    scheduler = SchedulerService()
    paper_service = PaperService()
    
    # 1. Force Clear Daily DB
    print("\n🗑️  Step 1: Clearing Daily Papers...")
    if paper_service.clear_daily_papers():
        print("✅ Daily papers cleared.")
    else:
        print("❌ Failed to clear daily papers.")
        return

    # 2. Run Crawler
    print("\n🕷️  Step 2: Running Crawler...")
    try:
        scheduler.run_crawler()
        print("✅ Crawler finished.")
    except Exception as e:
        print(f"❌ Crawler failed: {e}")
        return

    # 3. Verify Daily DB has data
    print("\n🔍 Step 3: Verifying Daily DB Data...")
    res = paper_service.db.table("daily_papers").select("count", count="exact").execute()
    count = res.count
    print(f"📊 Found {count} papers in daily_papers.")
    
    if count == 0:
        print("⚠️  No papers found. Crawler might have failed or no new papers.")
        # Continue anyway to test logic
    
    # 4. Run Process (Analysis & Sync)
    print("\n🧠 Step 4: Processing (Analysis & Sync)...")
    try:
        scheduler.process_new_papers()
        print("✅ Processing finished.")
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        return
        
    # 5. Verify Public DB Sync
    print("\n🔍 Step 5: Verifying Public DB Sync...")
    # Check if papers in daily_papers are also in papers
    daily_papers = paper_service.db.table("daily_papers").select("id").limit(5).execute().data
    if daily_papers:
        sample_id = daily_papers[0]['id']
        public_res = paper_service.db.table("papers").select("*").eq("id", sample_id).execute()
        if public_res.data:
            print(f"✅ Sync Successful! Paper {sample_id} found in Public DB.")
        else:
            print(f"❌ Sync Failed! Paper {sample_id} NOT found in Public DB.")
    else:
        print("⚠️  Skipping sync verification (no papers).")

    print("\n🎉 Manual Run Completed!")

if __name__ == "__main__":
    manual_run()
