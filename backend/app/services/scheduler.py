import os
import subprocess
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import get_db
from app.services.llm_service import llm_service
from app.services.report_service import report_service
from app.services.user_service import user_service
import httpx
import re

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
        if self.scheduler.running:
            print("Scheduler is already running.")
            return

        # 安排每日任务在早上8:00执行
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=8, minute=0)
        self.scheduler.start()
        print("Scheduler started. Daily job scheduled for 08:00.")

    def check_arxiv_update(self) -> bool:
        """
        检查 Arxiv 是否有更新。
        比对 "Showing new listings for" 后的日期字符串。
        """
        try:
            # 1. Get current status from Arxiv
            # Default to cs.CL, or get from env
            category = os.environ.get("CATEGORIES", "cs.CL").split(",")[0]
            url = f"https://arxiv.org/list/{category}/new"
            
            print(f"Checking Arxiv update at {url}...")
            # Use a browser-like header to avoid 403
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = httpx.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                print(f"Failed to fetch Arxiv page: {response.status_code}")
                return False
                
            html = response.text
            # Match: <h3>Showing new listings for Friday, 5 December 2024</h3>
            match = re.search(r"Showing new listings for (.*?)</h3>", html)
            if not match:
                print("Could not find 'Showing new listings for' in HTML.")
                return False
                
            current_date_str = match.group(1).strip()
            print(f"Arxiv Date: {current_date_str}")
            
            # 2. Get last status from DB
            status_row = self.db.table("system_status").select("*").eq("key", "last_arxiv_update").execute()
            last_date_str = status_row.data[0]["value"] if status_row.data else None
            
            if current_date_str != last_date_str:
                print(f"Update detected! Old: {last_date_str}, New: {current_date_str}")
                # Update DB
                self.db.table("system_status").upsert({
                    "key": "last_arxiv_update",
                    "value": current_date_str
                }).execute()
                return True
            else:
                print("No update detected.")
                return False
                
        except Exception as e:
            print(f"Error checking Arxiv update: {e}")
            return False

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
            # __file__ = backend/app/services/scheduler.py
            # dirname = backend/app/services
            # ../.. = backend
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            print(f"Running Scrapy in: {backend_root}")
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=backend_root)
            print("Crawler finished.")
            
            # Stage 2: Fetch Details (Arxiv API)
            print("Starting Stage 2: Fetching details...")
            from crawler.fetch_details import fetch_and_update_details
            fetch_and_update_details(table_name="daily_papers")
            print("Details fetched.")
        except Exception as e:
            print(f"Crawler failed: {e}")

    def process_public_papers(self):
        """
        处理公共论文分析。
        
        获取状态为 'fetched' 的新论文，并进行公共分析（如生成 TLDR、提取 Motivation 等）。
        这些分析结果是通用的，不针对特定用户。

        Args:
            None

        Returns:
            None
        """
        print("Starting Public Analysis...")
        from app.services.paper_service import paper_service
        from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
        
        try:
            print("--- Public Analysis ---")
            # 获取尚未分析的论文 (status 为 fetched)
            response = self.db.table("daily_papers").select("*").eq("status", "fetched").execute()
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

        except Exception as e:
            print(f"Error in process_public_papers: {e}")

    def process_personalized_papers(self):
        """
        处理个性化论文筛选。
        
        遍历所有用户，针对每个用户筛选其尚未处理的论文。
        根据用户的兴趣和历史行为，决定是否推荐该论文。

        Args:
            None

        Returns:
            None
        """
        print("Starting Personalized Filter...")
        from app.services.paper_service import paper_service
        from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
        from app.services.user_service import user_service
        
        try:
            print("--- Personalized Filter ---")
            
            # 1. 获取所有待处理的原始论文
            # 注意：这里我们再次获取 daily_papers，因为之前的步骤可能已经更新了某些状态，
            # 但对于个性化筛选，我们需要的是当天的所有论文数据。
            # 理论上应该只获取 status='analyzed' 的论文，但为了鲁棒性，我们获取所有 fetched/analyzed 的。
            # 简单起见，我们重新获取一次 daily_papers
            response = self.db.table("daily_papers").select("*").execute()
            raw_papers = response.data
            
            if not raw_papers:
                print("No papers found in daily_papers. Skipping personalized filter.")
                return

            # 2. 获取所有用户画像
            try:
                profiles_response = self.db.table("profiles").select("*").execute()
                profiles_data = profiles_response.data
            except Exception as e:
                print(f"Error fetching profiles: {e}")
                profiles_data = []

            if not profiles_data:
                print("No user profiles found. Skipping filter.")
                return

            print(f"Found {len(profiles_data)} users to process.")

            for profile_dict in profiles_data:
                try:
                    # 构造 UserProfile 对象
                    # 注意: 数据库里的 profile 结构可能需要清洗，这里假设 user_service.get_profile 里的清洗逻辑
                    # 为了复用清洗逻辑，最好调用 user_service.get_profile(user_id)
                    # 但为了效率，这里直接构造，或者在 user_service 中增加 get_all_profiles
                    
                    # 简单起见，我们直接用 user_service.get_profile(user_id) 来获取清洗后的对象
                    user_id = profile_dict.get("user_id")
                    if not user_id:
                        continue
                        
                    # 使用 user_service 获取完整的 profile 对象
                    user_profile = user_service.get_profile(user_id)
                    if not user_profile:
                        continue

                    print(f"Processing for user: {user_profile.info.name} ({user_id})")

                    # 优化：只查询今日候选论文中，用户已经处理过的那些
                    # 避免拉取用户所有的历史记录
                    daily_paper_ids = [p['id'] for p in raw_papers]
                    if not daily_paper_ids:
                        continue

                    state_response = self.db.table("user_paper_states") \
                        .select("paper_id") \
                        .eq("user_id", user_id) \
                        .in_("paper_id", daily_paper_ids) \
                        .execute()
                    
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
                        # 注意：这里传入 user_state=None，等待 filter_papers 填充
                        papers_to_filter.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
                    
                    if papers_to_filter:
                        print(f"Found {len(papers_to_filter)} papers to filter for user {user_id}.")
                        paper_service.filter_papers(papers_to_filter, user_profile, user_id)
                    else:
                        print(f"No new papers to filter for user {user_id}.")
                
                except Exception as e:
                    print(f"Error processing user {profile_dict.get('user_id')}: {e}")
                    continue

        except Exception as e:
            print(f"Error in process_personalized_papers: {e}")

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
        1. check_arxiv_update(): 检查更新。
        2. if updated:
            a. clear_daily_papers()
            b. run_crawler()
            c. process_new_papers()
            d. generate_report_job()
        """
        print("Running daily workflow...")
        
        # 1. Check Update
        if self.check_arxiv_update():
            print("Arxiv updated. Starting workflow...")
            
            # 2. Clear Daily DB
            from app.services.paper_service import paper_service
            if paper_service.clear_daily_papers():
                print("Daily papers cleared.")
            
            # 3. Crawl
            self.run_crawler()
            
            # 4. Process (Analyze & Filter)
            self.process_public_papers()
            self.process_personalized_papers()
            
            # 5. Report
            self.generate_report_job()
            
            print("Daily workflow completed.")
        else:
            print("Arxiv not updated. Skipping workflow.")

scheduler_service = SchedulerService()
