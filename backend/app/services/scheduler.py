import os
import subprocess
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import get_db
from app.services.llm_service import llm_service
from app.services.report_service import report_service
from app.services.user_service import user_service
from app.services.workflow_service import workflow_service
import httpx
import re
from typing import Optional, List

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

    def check_arxiv_update(self) -> Optional[List[str]]:
        """
        检查 Arxiv 是否有更新。
        比对 "Showing new listings for" 后的日期字符串。
        如果更新，则获取所有用户的关注类别并集返回。

        Args:
            None

        Returns:
            Optional[List[str]]: 如果有更新，返回需要爬取的类别列表；否则返回 None。
        """
        try:
            # 1. Get current status from Arxiv
            # Default to cs.CL, or get from env
            url = f"https://arxiv.org/list/cs/new"
            
            print(f"Checking Arxiv update at {url}...")
            # Use a browser-like header to avoid 403
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = httpx.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                print(f"Failed to fetch Arxiv page: {response.status_code}")
                return None
                
            html = response.text
            # Match: <h3>Showing new listings for Friday, 5 December 2024</h3>
            match = re.search(r"Showing new listings for (.*?)</h3>", html)
            if not match:
                print("Could not find 'Showing new listings for' in HTML.")
                return None
                
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
                
                # 3. Aggregate User Categories
                print("Aggregating user categories...")
                try:
                    # 获取所有用户的 profile
                    profiles = self.db.table("profiles").select("focus").execute().data
                    all_categories = set()
                    
                    for p in profiles:
                        focus = p.get("focus", {})
                        if focus and "category" in focus:
                            cats = focus["category"]
                            if isinstance(cats, list):
                                all_categories.update(cats)
                            elif isinstance(cats, str):
                                all_categories.add(cats)
                    
                    # 如果没有用户类别，使用默认配置
                    if not all_categories:
                        print("No user categories found, using default.")
                        default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                        return [c.strip() for c in default_cats]
                        
                    result_categories = list(all_categories)
                    print(f"Categories to crawl: {result_categories}")
                    return result_categories
                    
                except Exception as e:
                    print(f"Error aggregating categories: {e}")
                    # Fallback to default
                    default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                    return [c.strip() for c in default_cats]
            else:
                print("No update detected.")
                return None
                
        except Exception as e:
            print(f"Error checking Arxiv update: {e}")
            return None

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
        
        功能说明：
        1. 获取所有用户画像。
        2. 为每个用户获取今日的个性化推荐论文。
        3. 调用 report_service.generate_daily_report() 生成报告（内部自动发送邮件）。

        Args:
            None

        Returns:
            None
        """
        print("开始生成每日报告...")
        try:
            # === 1. 获取所有用户 ===
            profiles_response = self.db.table("profiles").select("*").execute()
            profiles_data = profiles_response.data
            
            if not profiles_data:
                print("未找到任何用户")
                return
            
            print(f"找到 {len(profiles_data)} 个用户，开始生成报告...")
            
            # === 2. 遍历每个用户 ===
            for profile_dict in profiles_data:
                user_id = profile_dict.get("user_id")
                if not user_id:
                    continue
                
                try:
                    # 2.1 获取用户画像（使用 user_service 确保数据清洗）
                    user_profile = user_service.get_profile(user_id)
                    
                    # 检查用户是否有邮箱
                    if not user_profile.info.email:
                        print(f"用户 {user_profile.info.name} 未设置邮箱，跳过")
                        continue
                        
                    print(f"\n处理用户: {user_profile.info.name} ({user_id})")
                    
                    # === 3. 获取今日的个性化论文 ===
                    from datetime import datetime
                    today = datetime.now().strftime("%Y-%m-%d")
                    
                    # 3.1 查询今天筛选的、被接受的论文
                    states_response = self.db.table("user_paper_states") \
                        .select("*") \
                        .eq("user_id", user_id) \
                        .eq("accepted", True) \
                        .gte("created_at", f"{today} 00:00:00") \
                        .order("relevance_score", desc=True) \
                        .limit(int(os.environ.get("REPORT_PAPER_LIMIT", 50))) \
                        .execute()
                    
                    if not states_response.data:
                        print(f"用户 {user_id} 今天没有推荐论文，跳过")
                        continue
                    
                    print(f"找到 {len(states_response.data)} 篇推荐论文")
                    
                    # === 4. 获取完整论文数据 ===
                    paper_ids = [s["paper_id"] for s in states_response.data]
                    papers_response = self.db.table("papers") \
                        .select("*") \
                        .in_("id", paper_ids) \
                        .execute()
                    papers_data = papers_response.data
                    
                    if not papers_data:
                        print(f"未找到论文详细数据，跳过")
                        continue
                    
                    # === 5. 构建 PersonalizedPaper 对象 ===
                    from app.services.paper_service import paper_service
                    
                    papers = []
                    state_map = {s["paper_id"]: s for s in states_response.data}
                    
                    for p in papers_data:
                        state_data = state_map.get(p["id"])
                        # 使用 paper_service 的辅助方法合并数据
                        paper_obj = paper_service.merge_paper_state(p, state_data)
                        papers.append(paper_obj)
                    
                    # === 6. 生成报告（内部会自动发送邮件）===
                    # [Fix] 正确解包返回值 (report, usage)
                    report, _ = report_service.generate_daily_report(papers, user_profile)
                    print(f"✓ 已为用户 {user_profile.info.name} 生成并发送报告: {report.title}")
                    
                except Exception as e:
                    print(f"✗ 为用户 {user_id} 生成报告失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
        except Exception as e:
            print(f"生成报告任务失败: {e}")
            import traceback
            traceback.print_exc()

    def run_daily_workflow(self, force: bool = False):
        """
        执行完整的每日工作流。
        
        顺序执行：
        1. check_arxiv_update(): 检查更新并获取类别。
        2. if categories or force:
            a. clear_daily_papers() (仅当非 force 时，或 force 且确实有更新时？这里逻辑需要微调)
               - 如果是 force 模式，通常是为了断点续传，不应该 clear_daily_papers，除非明确是重新开始。
               - 但为了简单，force 模式下我们假设用户想继续跑流程。
               - 如果是断点续传，workflow_service.process_public_papers_workflow 内部会检查 status='fetched'，所以不会重复处理。
               - 关键是不要 clear_daily_papers 如果我们想保留已抓取的数据。
               - 让我们调整逻辑：
                 - 如果 force=True，跳过 check_arxiv_update 的"无更新"返回，强制使用默认或已有类别。
                 - 如果 force=True，跳过 clear_daily_papers (假设是续传)。
                 - 或者更智能点：force 只是绕过"今天已更新"的检查。
        
        Args:
            force (bool): 是否强制执行，忽略 Arxiv 更新检查。
        """
        print(f"Running daily workflow (Force={force})...")
        
        # 1. Check Update & Get Categories
        categories = self.check_arxiv_update()
        
        # 如果强制执行且没有检测到更新（categories 为 None），则尝试获取所有用户的关注类别
        if force and not categories:
            print("Force mode enabled. Aggregating user categories...")
            try:
                # 复用 check_arxiv_update 中的聚合逻辑
                # 为了避免代码重复，最好提取聚合逻辑为单独方法，或者在这里重新实现
                # 这里简单重新实现聚合逻辑
                profiles = self.db.table("profiles").select("focus").execute().data
                all_categories = set()
                
                for p in profiles:
                    focus = p.get("focus", {})
                    if focus and "category" in focus:
                        cats = focus["category"]
                        if isinstance(cats, list):
                            all_categories.update(cats)
                        elif isinstance(cats, str):
                            all_categories.add(cats)
                
                if all_categories:
                    categories = list(all_categories)
                    print(f"Aggregated categories in force mode: {categories}")
                else:
                    print("No user categories found in force mode, using default.")
                    default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                    categories = [c.strip() for c in default_cats]
            except Exception as e:
                print(f"Error aggregating categories in force mode: {e}")
                default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                categories = [c.strip() for c in default_cats]

        if categories:
            print(f"Starting workflow for categories: {categories}")
            
            # 2. Clear Daily DB
            # 只有在非强制模式（正常自动运行）或者确实检测到新更新时才清空
            # 如果是 force 模式且没有新更新（即断点续传），不要清空！
            if not force:
                from app.services.paper_service import paper_service
                if paper_service.clear_daily_papers():
                    print("Daily papers cleared.")
            else:
                print("Force mode: Skipping clear_daily_papers to allow resume.")
            
            # 3. Public Workflow (Crawl -> Fetch -> Analyze -> Archive)
            try:
                # 注意：process_public_papers_workflow 内部包含 run_crawler
                # 如果是断点续传，run_crawler 会重新爬取，但这通常没问题（Scrapy 会覆盖或忽略）
                # 或者我们可以让 process_public_papers_workflow 也支持 resume？
                # 目前保持简单：直接运行，依赖数据库状态去重
                workflow_service.process_public_papers_workflow(categories)
            except Exception as e:
                print(f"Public workflow failed, stopping daily workflow: {e}")
                return

            # 4. Personalized Filter
            self.process_personalized_papers()
            
            # 5. Report
            self.generate_report_job()
            
            print("Daily workflow completed.")
        else:
            print("Arxiv not updated. Skipping workflow.")

scheduler_service = SchedulerService()
