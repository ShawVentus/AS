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
        """
        # 安排每日任务在早上8:00执行
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=8, minute=0)
        self.scheduler.start()
        print("Scheduler started. Daily job scheduled for 08:00.")

    def run_crawler(self):
        """
        运行 ArXiv 爬虫任务。
        
        通过 subprocess 调用 Scrapy 爬虫，抓取最新的论文数据并存入数据库。
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
        
        1. 获取尚未分析的论文。
        2. 使用 paper_service.filter_papers 并发过滤相关性。
        3. 对相关论文进行深度分析 (生成摘要、动机等)。
        """
        print("Processing new papers...")
        from app.services.paper_service import paper_service
        from app.schemas.paper import PersonalizedPaper, PaperMetadata
        
        try:
            # 1. 获取尚未分析的论文 (tldr 为空)
            # 为安全起见,获取最近的论文(最近2天)
            response = self.db.table("papers").select("*").order("created_at", desc=True).limit(50).execute()
            raw_papers = response.data
            
            user_profile = user_service.get_profile()
            
            # 转换为 PersonalizedPaper 对象列表
            papers_to_process = []
            for p in raw_papers:
                if p.get("tldr"): # 已经分析过
                    continue
                # 构造 PersonalizedPaper，初始状态为 None
                # 注意：这里我们假设没有 user_state，因为是新论文。
                # 如果需要更严谨，应该先查询 user_state，但 filter_papers 会处理 upsert。
                metadata = PaperMetadata(**p)
                papers_to_process.append(PersonalizedPaper(**metadata.model_dump(), user_state=None))
            
            if not papers_to_process:
                print("No new papers to process.")
                return

            print(f"Found {len(papers_to_process)} papers to process.")

            # 2. 并发过滤
            # filter_papers 会并发调用 LLM 并更新 user_paper_states
            # 返回的是所有处理过的论文（包括 accepted 和 rejected，取决于 filter_papers 实现，目前是全部）
            # 我们只需要关注 accepted=True 的论文进行后续深度分析
            processed_papers = paper_service.filter_papers(papers_to_process, user_profile)
            
            # 3. 深度分析 (针对 accepted 的论文)
            for p in processed_papers:
                if p.user_state and p.user_state.accepted:
                    print(f"Paper {p.id} is relevant! Analyzing details...")
                    # analyze_paper 会更新 papers 表的 public metadata (tldr, details)
                    paper_service.analyze_paper(p, user_profile)
                else:
                    # 对于不相关的论文，标记为已处理 (tldr="N/A") 以免重复处理
                    # 也可以选择不更新 papers 表，只更新 user_state
                    # 但为了 process_new_papers 下次不重复抓取，我们需要标记 papers 表
                    print(f"Paper {p.id} is not relevant.")
                    try:
                        self.db.table("papers").update({
                            "tldr": "N/A",
                            "suggestion": p.user_state.why_this_paper if p.user_state else "Not Relevant"
                        }).eq("id", p.id).execute()
                    except Exception as e:
                        print(f"Error marking paper {p.id} as N/A: {e}")

        except Exception as e:
            print(f"Error processing papers: {e}")

    def generate_report_job(self):
        """
        生成并发送每日报告的任务。
        
        1. 获取今日相关的论文。
        2. 调用 ReportService 生成报告。
        3. 发送邮件通知用户。
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
        """
        print("Running daily workflow...")
        self.run_crawler()
        self.process_new_papers()
        self.generate_report_job()
        print("Daily workflow completed.")

scheduler_service = SchedulerService()
