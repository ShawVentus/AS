import os
import subprocess
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import get_db
from services.llm_service import llm_service
from services.report_service import report_service
from services.user_service import user_service

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db = get_db()

    def start(self):
        # 安排每日任务在早上8:00执行
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=8, minute=0)
        self.scheduler.start()
        print("Scheduler started. Daily job scheduled for 08:00.")

    def run_crawler(self):
        print("Starting ArXiv Crawler...")
        # 以子进程方式运行scrapy
        try:
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=os.path.dirname(__file__))
            print("Crawler finished.")
        except Exception as e:
            print(f"Crawler failed: {e}")

    def process_new_papers(self):
        print("Processing new papers...")
        # 获取尚未分析的论文(例如tldr为空的论文)
        # 注意: Supabase/PostgREST客户端有时不容易支持"is null"查询,
        # 但我们可以检查空字符串或使用过滤器
        try:
            # 为安全起见,获取最近的论文(最近2天)
            response = self.db.table("papers").select("*").order("created_at", desc=True).limit(50).execute()
            papers = response.data
            
            user_profile = user_service.get_profile()
            profile_str = str(user_profile.model_dump())

            for paper in papers:
                # 如果已经分析过则跳过
                if paper.get("tldr"):
                    continue
                
                print(f"Analyzing paper: {paper['id']}")
                
                # 1. 过滤
                filter_res = llm_service.filter_paper(paper, profile_str)
                if not filter_res.get("is_relevant", False):
                    print(f"Paper {paper['id']} is not relevant. Reason: {filter_res.get('reason')}")
                    # 标记为已处理但不相关?
                    # 我们可以将原因存储在suggestion或tags中
                    self.db.table("papers").update({
                        "suggestion": "Not Relevant: " + filter_res.get("reason", ""),
                        "tldr": "N/A" # 标记为已处理
                    }).eq("id", paper['id']).execute()
                    continue

                # 2. 分析
                print(f"Paper {paper['id']} is relevant! Analyzing...")
                analysis = llm_service.analyze_paper(paper, profile_str)
                
                # 更新数据库
                update_data = {
                    "tldr": analysis.get("tldr", ""),
                    "suggestion": analysis.get("why_this_paper", ""),
                    "tags": analysis.get("tags", []),
                    "details": {
                        **paper.get("details", {}), # 与现有详情(摘要)合并
                        "motivation": analysis.get("motivation", ""),
                        "method": analysis.get("method", ""),
                        "result": analysis.get("result", ""),
                        "conclusion": analysis.get("conclusion", "")
                    }
                }
                self.db.table("papers").update(update_data).eq("id", paper['id']).execute()
                
        except Exception as e:
            print(f"Error processing papers: {e}")

    def generate_report_job(self):
        print("Generating daily report...")
        try:
            # 获取今天的相关论文
            # 在实际应用中,应按日期和相关性过滤
            # 对于MVP版本,只获取tldr不为"N/A"且最近创建的论文
            response = self.db.table("papers").select("*").neq("tldr", "N/A").neq("tldr", "").order("created_at", desc=True).limit(20).execute()
            relevant_papers = response.data
            
            if not relevant_papers:
                print("No relevant papers for report.")
                return

            # 转换为对象
            from schemas.paper import Paper
            paper_objs = [Paper(**p) for p in relevant_papers]
            
            user_profile = user_service.get_profile()
            
            # 生成报告
            report = report_service.generate_daily_report(paper_objs, user_profile)
            print(f"Report generated: {report.title}")
            
            # 发送邮件
            report_service.send_email(report, user_profile.info.email)
            print("Email sent.")
            
        except Exception as e:
            print(f"Error generating report: {e}")

    def run_daily_workflow(self):
        print("Running daily workflow...")
        self.run_crawler()
        self.process_new_papers()
        self.generate_report_job()
        print("Daily workflow completed.")

scheduler_service = SchedulerService()
