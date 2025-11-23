import asyncio
import os
from datetime import datetime
from services.paper_service import paper_service
from services.report_service import report_service
from services.user_service import user_service
from core.config import settings

async def verify_flow():
    print("=== Verifying Data Flow ===")
    
    # 1. 检查用户
    print("\n[1] Checking User...")
    user = await user_service.get_user_profile("user_123") # 模拟ID
    if not user:
        print("User not found, initializing...")
        # 如果需要,初始化模拟用户,但service通常返回模拟数据
    print(f"User: {user.info.name if user else 'None'}")

    # 2. 检查今天的论文(爬虫模拟/检查)
    print("\n[2] Checking Papers for Today...")
    papers = await paper_service.get_papers(limit=5)
    print(f"Found {len(papers)} papers in DB.")
    
    if len(papers) == 0:
        print("No papers found. Triggering crawler (mock/real)...")
        # 在实际场景中,我们会触发爬虫。
        # 现在,我们可能需要依赖数据库中的内容或如果爬虫未完全集成到此脚本中则模拟它。
        # 让我们看看是否可以获取每日论文。
        try:
            daily_papers = await paper_service.get_daily_papers()
            print(f"Fetched {len(daily_papers)} daily papers.")
        except Exception as e:
            print(f"Error fetching daily papers: {e}")

    # 3. 检查分析
    print("\n[3] Checking Analysis...")
    if papers:
        p = papers[0]
        print(f"Checking analysis for paper: {p.title}")
        analysis = await paper_service.get_paper_analysis(p.id)
        if analysis:
            print("Analysis found.")
        else:
            print("Analysis missing.")
            
    # 4. 检查报告生成
    print("\n[4] Checking Report Generation...")
    try:
        report = await report_service.generate_daily_report()
        print(f"Report generated: {report.title}")
        print(f"Summary length: {len(report.summary)}")
    except Exception as e:
        print(f"Report generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_flow())
