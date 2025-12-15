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
from typing import Optional, List, Callable, Dict, Any

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

        # 安排每日任务在早上9:30执行
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=9, minute=30)
        self.scheduler.start()
        print("Scheduler started. Daily job scheduled for 09:30.")

    def check_arxiv_update(self) -> tuple[Optional[List[str]], Optional[str]]:
        """
        检查 Arxiv 是否有更新。
        比对 "Showing new listings for" 后的日期字符串。
        如果更新，则获取所有用户的关注类别并集返回。

        Args:
            None

        Returns:
            tuple: (categories, arxiv_date)
            - categories (List[str]): 需要爬取的类别列表，如果没有更新则为 None
            - arxiv_date (str): Arxiv 上的日期字符串，如果没有找到则为 None
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
                return None, None
                
            html = response.text
            # Match: <h3>Showing new listings for Friday, 5 December 2024</h3>
            match = re.search(r"Showing new listings for (.*?)</h3>", html)
            if not match:
                print("Could not find 'Showing new listings for' in HTML.")
                return None, None
                
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
                        return [c.strip() for c in default_cats], current_date_str
                        
                    result_categories = list(all_categories)
                    print(f"Categories to crawl: {result_categories}")
                    return result_categories, current_date_str
                    
                except Exception as e:
                    print(f"Error aggregating categories: {e}")
                    # Fallback to default
                    default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                    return [c.strip() for c in default_cats], current_date_str
            else:
                print("No update detected.")
                return None, current_date_str
                
        except Exception as e:
            print(f"Error checking Arxiv update: {e}")
            return None, None

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

    def generate_report_job(self, force: bool = False, target_user_id: Optional[str] = None, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        生成并发送每日报告的任务。
        
        功能说明：
        1. 获取所有用户画像。
        2. 为每个用户获取今日的个性化推荐论文。
        3. 调用 report_service.generate_daily_report() 生成报告（内部自动发送邮件）。

        Args:
            force (bool): 是否强制生成报告（即使今日已生成）。
            target_user_id (Optional[str]): 指定生成报告的用户 ID。
            progress_callback (Optional[Callable]): 进度回调。

        Returns:
            Dict[str, Any]: 统计数据 (tokens_input, tokens_output, cost, etc.)
        """
        print("开始生成每日报告...")
        
        # 统计数据
        total_stats = {
            "tokens_input": 0,
            "tokens_output": 0,
            "cost": 0.0,
            "cache_hit_tokens": 0,
            "request_count": 0
        }
        
        try:
            # === 1. 获取目标用户 ===
            if target_user_id:
                # 仅处理指定用户
                profiles_response = self.db.table("profiles").select("*").eq("user_id", target_user_id).execute()
            else:
                # 获取所有用户
                profiles_response = self.db.table("profiles").select("*").execute()
                
            profiles_data = profiles_response.data
            
            if not profiles_data:
                print("未找到任何用户")
                if progress_callback:
                    progress_callback(100, 100, "未找到用户")
                return total_stats
            
            print(f"找到 {len(profiles_data)} 个用户，开始生成报告...")
            
            total_users = len(profiles_data)
            processed_count = 0
            
            # === 2. 遍历每个用户 ===
            for profile_dict in profiles_data:
                processed_count += 1
                user_id = profile_dict.get("user_id")
                
                if progress_callback:
                    progress_callback(processed_count, total_users, f"正在为用户 {user_id[:8]}... 生成报告")
                
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

                    # [New] 检查今日是否已生成报告
                    if not force:
                        from datetime import datetime
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        existing_reports = self.db.table("reports") \
                            .select("id") \
                            .eq("user_id", user_id) \
                            .eq("date", today_str) \
                            .execute()
                        
                        if existing_reports.data:
                            print(f"用户 {user_profile.info.name} 今日已生成报告，跳过 (Force=False)")
                            continue
                    
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
                    report, usage = report_service.generate_daily_report(papers, user_profile)
                    
                    # 累加统计
                    if usage:
                        total_stats["tokens_input"] += usage.get("prompt_tokens", 0)
                        total_stats["tokens_output"] += usage.get("completion_tokens", 0)
                        total_stats["cost"] += usage.get("cost", 0.0)
                        total_stats["cache_hit_tokens"] += usage.get("cache_hit_tokens", 0)
                        total_stats["request_count"] += 1
                        
                    print(f"✓ 已为用户 {user_profile.info.name} 生成并发送报告: {report.title}")
                    
                except Exception as e:
                    print(f"✗ 为用户 {user_id} 生成报告失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                    
            return total_stats
                    
        except Exception as e:
            print(f"生成报告任务失败: {e}")
            import traceback
            traceback.print_exc()
            return total_stats

    def run_daily_workflow(self, force: bool = False, target_user_id: Optional[str] = None, execution_id: Optional[str] = None):
        """
        运行每日工作流。
        
        Args:
            force (bool): 是否强制运行（忽略日期检查）。
            target_user_id (Optional[str]): 指定运行的目标用户 ID。
            execution_id (Optional[str]): 指定执行 ID（用于前端追踪）。
        """
        # [Fix] 禁止 httpx 输出 INFO 日志
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        print(f"Running daily workflow (Force={force}, ExecutionID={execution_id})...")
        
        from app.services.workflow_engine import WorkflowEngine
        from app.services.workflow_steps.check_update_step import CheckUpdateStep
        from app.services.workflow_steps.clear_daily_step import ClearDailyStep
        from app.services.workflow_steps.run_crawler_step import RunCrawlerStep
        from app.services.workflow_steps.fetch_details_step import FetchDetailsStep
        from app.services.workflow_steps.analyze_public_step import AnalyzePublicStep
        from app.services.workflow_steps.archive_step import ArchiveStep
        from app.services.workflow_steps.personalized_filter_step import PersonalizedFilterStep
        from app.services.workflow_steps.generate_report_step import GenerateReportStep
        
        engine = WorkflowEngine()
        if execution_id:
            engine.execution_id = execution_id
        
        # 注册步骤
        # 1. 检查更新 (如果 force=True，此步骤内部逻辑可能会跳过检查或直接返回 True，需确认 CheckUpdateStep 逻辑)
        # CheckUpdateStep 目前只检查更新，不处理 force。
        # 如果 force=True，我们可以手动设置 context["force"] = True，并在 CheckUpdateStep 中处理，
        # 或者我们在这里手动检查，如果 force=True，则跳过 CheckUpdateStep 或忽略其 should_stop。
        # 但为了保持一致性，最好让 CheckUpdateStep 处理 force。
        # 目前 CheckUpdateStep 只是调用 scheduler_service.check_arxiv_update()。
        # 我们可以简单地注册所有步骤，并让 engine 处理。
        # 但 CheckUpdateStep 会返回 should_stop=True 如果没更新。
        # 如果 force=True，我们希望忽略 should_stop。
        
        # 方案：在 context 中传入 force=True 和 target_user_id
        initial_context = {
            "force": force,
            "target_user_id": target_user_id
        }
        
        # 1. Check Update & Get Categories
        categories, arxiv_date = self.check_arxiv_update()
        
        # [Fix] 如果是 force 模式 OR 指定了 target_user_id (手动触发)，则尝试聚合类别
        if (force or target_user_id) and not categories:
            print("Force mode or Target User detected. Aggregating user categories...")
            try:
                # 如果指定了用户，只获取该用户的类别？
                # 为了简单和数据完整性，我们还是获取所有用户的类别，或者至少包含该用户的类别。
                # 如果只获取该用户类别，可能会漏掉其他人的。
                # 但如果是手动触发，可能只关心该用户。
                # 策略：如果是 target_user_id，优先获取该用户的 focus。
                
                target_profiles = []
                if target_user_id:
                    p = self.db.table("profiles").select("focus").eq("user_id", target_user_id).execute().data
                    if p:
                        target_profiles = p
                else:
                    target_profiles = self.db.table("profiles").select("focus").execute().data

                all_categories = set()
                for p in target_profiles:
                    focus = p.get("focus", {})
                    if focus and "category" in focus:
                        cats = focus["category"]
                        if isinstance(cats, list):
                            all_categories.update(cats)
                        elif isinstance(cats, str):
                            all_categories.add(cats)
                
                if all_categories:
                    categories = list(all_categories)
                    print(f"Aggregated categories: {categories}")
                else:
                    # Fallback
                    default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                    categories = [c.strip() for c in default_cats]
            except Exception as e:
                print(f"Error aggregating categories: {e}")
                default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                categories = [c.strip() for c in default_cats]
        
        if not categories:
            print("Arxiv not updated and not in force mode. Skipping workflow.")
            return

        print(f"Starting workflow for categories: {categories}")
        initial_context["categories"] = categories
        initial_context["arxiv_date"] = arxiv_date
        
        # 注册后续步骤
        # 2. Clear Daily DB (只有非 force 且非单用户触发才清空?)
        # 如果是单用户触发，绝对不能清空 daily_papers，因为可能影响其他人或已有数据。
        if not force and not target_user_id:
            engine.register_step(ClearDailyStep())
        else:
            print("Force mode or Single User: Skipping ClearDailyStep.")
            
        engine.register_step(RunCrawlerStep())
        engine.register_step(FetchDetailsStep())
        engine.register_step(AnalyzePublicStep())
        engine.register_step(ArchiveStep())
        engine.register_step(PersonalizedFilterStep())
        engine.register_step(GenerateReportStep())
        
        # 执行工作流
        try:
            engine.execute_workflow("daily_update", initial_context=initial_context)
        except Exception as e:
            print(f"Workflow execution failed: {e}")

scheduler_service = SchedulerService()
