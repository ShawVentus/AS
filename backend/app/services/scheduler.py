import os
import subprocess
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import get_db
from app.services.llm_service import llm_service
from app.services.report_service import report_service
from app.services.user_service import user_service

class SchedulerService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.db = get_db()

    def start(self):
        """
        启动后台调度器。
        
        配置每日任务 (run_daily_workflow) 在每天 08:00 执行。

        Args:
            None

        Returns:
            None
        """
        # 安排每日任务在早上8:00执行
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=8, minute=0)
        self.scheduler.start()
        print("Scheduler started. Daily job scheduled for 08:00.")

    def run_crawler(self):
        """
        运行 ArXiv 爬虫任务。
        
        通过 subprocess 调用 Scrapy 爬虫，抓取最新的论文数据并存入数据库。

        Args:
            None

        Returns:
            None
        """
        print("Starting ArXiv Crawler...")
        # 以子进程方式运行scrapy
        try:
            # cwd should be backend root (where scrapy.cfg is)
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=backend_root)
            print("Crawler finished.")
        except Exception as e:
            print(f"Crawler failed: {e}")

    def process_new_papers(self):
        """
        处理新抓取的论文。
        
        流程拆分为两步 (Decoupled):
        1. Public Analysis: 对所有未分析的新论文进行深度分析 (提取 tldr, motivation 等)。
        2. Personalized Filter: 对每个用户，筛选其未处理的论文。

        Args:
            None

        Returns:
            None
        """
        print("Processing new papers...")
        from app.services.paper_service import paper_service
        from app.schemas.paper import PersonalizedPaper, PaperMetadata
        from app.services.user_service import user_service
        
        try:
            # --- Step 1: Public Analysis (公共分析) ---
            print("--- Step 1: Public Analysis ---")
            # 获取尚未分析的论文 (status 为 completed)
            response = self.db.table("papers").select("*").eq("status", "completed").execute()
            raw_papers = response.data
            
            papers_to_analyze = []
            for p in raw_papers:
                # 构造 PersonalizedPaper (analysis=None, user_state=None)
                # 注意: 这里我们需要先构造 RawPaperMetadata
                meta_data = {
                    "id": p["id"],
                    "title": p["title"],
                    "authors": p["authors"],
                    "published_date": p["published_date"],
                    "category": p["category"],
                    "abstract": p["abstract"],
                    "links": p["links"],
                    "comment": p.get("comment")
                }
                meta = RawPaperMetadata(**meta_data)
                papers_to_analyze.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
            
            if papers_to_analyze:
                print(f"Found {len(papers_to_analyze)} papers needing public analysis.")
                paper_service.batch_analyze_papers(papers_to_analyze)
            else:
                print("No papers need public analysis.")

            # --- Step 2: Personalized Filter (个性化筛选) ---
            print("--- Step 2: Personalized Filter ---")
            # 获取所有活跃用户 (目前假设只有一个测试用户，或者遍历所有)
            # 这里简化为只处理当前获取到的 profile 用户
            # 在多用户系统中，应该遍历 user 表
            # users = self.db.table("users").select("*").execute().data
            
            # 暂时只处理当前测试用户
            user_profile = user_service.get_profile()
            if not user_profile:
                print("No user profile found. Skipping filter.")
                return

            # 获取该用户未筛选的论文
            # 逻辑：获取最近论文 -> 排除 user_paper_states 中已存在的
            # 1. 获取最近论文 (复用 raw_papers 或重新获取)
            user_id = user_profile.info.id
            state_response = self.db.table("user_paper_states").select("paper_id").eq("user_id", user_id).execute()
            processed_paper_ids = {s['paper_id'] for s in state_response.data} if state_response.data else set()
            
            papers_to_filter = []
            for p in raw_papers:
                if p['id'] in processed_paper_ids:
                    continue
                
                # 构造对象
                meta_data = {
                    "id": p["id"],
                    "title": p["title"],
                    "authors": p["authors"],
                    "published_date": p["published_date"],
                    "category": p["category"],
                    "abstract": p["abstract"],
                    "links": p["links"],
                    "comment": p.get("comment")
                }
                meta = RawPaperMetadata(**meta_data)
                # 注意：这里传入 user_state=None
                papers_to_filter.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
            
            if papers_to_filter:
                print(f"Found {len(papers_to_filter)} papers to filter for user {user_id}.")
                paper_service.filter_papers(papers_to_filter, user_profile)
            else:
                print(f"No new papers to filter for user {user_id}.")

        except Exception as e:
            print(f"Error processing papers: {e}")

    def generate_report_job(self):
        """
        生成并发送每日报告的任务。
        
        1. 获取今日相关的论文。
        2. 调用 ReportService 生成报告。
        3. 发送邮件通知用户。

        Args:
            None

        Returns:
            None
        """
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
            from app.schemas.paper import Paper
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
        """
        执行完整的每日工作流。
        
        顺序执行：
        1. run_crawler(): 抓取新论文。
        2. process_new_papers(): 分析和过滤论文。
        3. generate_report_job(): 生成并发送报告。

        Args:
            None

        Returns:
            None
        """
        print("Running daily workflow...")
        self.run_crawler()
        self.process_new_papers()
        self.generate_report_job()
        print("Daily workflow completed.")

scheduler_service = SchedulerService()
