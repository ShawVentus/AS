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
from app.utils.error_notifier import error_notifier
import httpx
import re
from typing import Optional, List, Callable, Dict, Any

class SchedulerService:
    """
    后台任务调度服务
    
    负责管理 ArXiv 论文的自动爬取、公共分析、个性化筛选以及报告生成。
    支持每日定时执行和手动触发执行。
    """
    
    def __init__(self):
        """
        初始化调度服务。
        """
        self.scheduler = BackgroundScheduler()
        self.db = get_db()
    
    def _should_generate_report(self, user_profile, manual_query: Optional[str] = None) -> bool:
        """
        检查用户是否满足报告生成条件。
        
        核心条件：
        1. 用户必须有剩余额度 (remaining_quota > 0)。
        2. 用户必须开启了自动报告开关 (receive_email = True)（仅限自动任务）。
        3. 用户必须设置了研究偏好 (preferences)，至少包含一条偏好（仅限自动任务）。
        
        Args:
            user_profile: 用户画像对象。
            manual_query (Optional[str]): 手动查询字符串，如果存在则视为手动触发，豁免部分检查。
        
        Returns:
            bool: True 表示满足条件，应生成报告；False 表示不满足，跳过报告。
        """
        # 1. 检查额度（核心条件）
        if not user_service.has_sufficient_quota(user_profile.info.id):
            print(f"⏭️  跳过用户 {user_profile.info.name} ({user_profile.info.id}): 额度不足")
            return False

        # 2. 检查接收开关（仅限自动任务）
        if not manual_query and not user_profile.info.receive_email:
            print(f"⏭️  跳过用户 {user_profile.info.name} ({user_profile.info.id}): 已关闭自动报告推送")
            return False

        # 3. 检查偏好设置
        if manual_query:
            return True
        
        if not user_profile.context.preferences or len(user_profile.context.preferences) == 0:
            print(f"⏭️  跳过用户 {user_profile.info.name} ({user_profile.info.id}): 未设置研究偏好")
            return False
        
        return True

    def start(self):
        """
        启动后台调度器。
        
        配置每日任务 (run_daily_workflow)，执行时间从配置文件读取（默认 09:30）。
        """
        if self.scheduler.running:
            print("调度器已在运行中。")
            return

        from app.core.config import settings
        hour, minute = settings.get_daily_report_time()
        
        self.scheduler.add_job(self.run_daily_workflow, 'cron', hour=hour, minute=minute)
        self.scheduler.start()
        print(f"调度器已启动。每日任务安排在 {hour:02d}:{minute:02d}。")

    def check_arxiv_update(self) -> tuple[Optional[List[str]], Optional[str]]:
        """
        检查 Arxiv 是否有更新。
        
        比对 "Showing new listings for" 后的日期字符串。
        如果更新，则获取所有“额度充足且开启报告”的用户的关注类别并集。
        
        Returns:
            tuple: (categories, arxiv_date)
        """
        try:
            url = "https://arxiv.org/list/cs/new"
            print(f"正在检查 Arxiv 更新: {url}...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = httpx.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                print(f"获取 Arxiv 页面失败: {response.status_code}")
                return None, None
                
            html = response.text
            match = re.search(r"Showing new listings for (.*?)</h3>", html)
            if not match:
                print("未在 HTML 中找到日期信息。")
                return None, None
                
            current_date_str = match.group(1).strip()
            print(f"Arxiv 当前日期: {current_date_str}")
            
            status_row = self.db.table("system_status").select("*").eq("key", "last_arxiv_update").execute()
            last_date_str = status_row.data[0]["value"] if status_row.data else None
            
            if current_date_str != last_date_str:
                print(f"检测到更新！旧日期: {last_date_str}, 新日期: {current_date_str}")
                self.db.table("system_status").upsert({"key": "last_arxiv_update", "value": current_date_str}).execute()
                
                print("正在汇总符合条件用户的关注类别...")
                profiles = self.db.table("profiles").select("focus") \
                    .gt("remaining_quota", 0).eq("receive_email", True).execute().data
                
                all_categories = set()
                for p in profiles:
                    focus = p.get("focus", {})
                    if focus and "category" in focus:
                        cats = focus["category"]
                        if isinstance(cats, list): all_categories.update(cats)
                        elif isinstance(cats, str): all_categories.add(cats)
                
                if not all_categories:
                    print("未找到符合条件的用户类别，使用默认配置。")
                    default_cats = os.environ.get("CATEGORIES", "cs.CL").split(",")
                    return [c.strip() for c in default_cats], current_date_str
                        
                result_categories = list(all_categories)
                print(f"需要爬取的类别并集: {result_categories}")
                return result_categories, current_date_str
            else:
                print("未检测到更新。")
                return None, current_date_str
                
        except Exception as e:
            print(f"检查 Arxiv 更新时发生异常: {e}")
            return None, None

    def run_crawler(self):
        """
        运行 ArXiv 爬虫任务。
        """
        try:
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            print(f"正在运行爬虫，目录: {backend_root}")
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=backend_root)
            print("爬虫运行完成。")
            
            print("开始获取论文详细信息...")
            from crawler.fetch_details import fetch_and_update_details
            fetch_and_update_details(table_name="daily_papers")
            print("详细信息获取完成。")
        except Exception as e:
            print(f"爬虫执行失败: {e}")
            raise

    def process_public_papers(self):
        """
        处理公共论文分析。
        """
        try:
            from app.services.paper_service import paper_service
            from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
            
            print("开始公共论文分析...")
            response = self.db.table("daily_papers").select("*").eq("status", "fetched").execute()
            raw_papers = response.data
            
            if not raw_papers:
                print("没有待分析的新论文。")
                return
                
            papers_to_analyze = []
            for p in raw_papers:
                meta = RawPaperMetadata(
                    id=p["id"], title=p["title"], authors=p["authors"],
                    published_date=p["published_date"], category=p["category"],
                    abstract=p["abstract"], links=p["links"], comment=p.get("comment")
                )
                papers_to_analyze.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
            
            print(f"找到 {len(papers_to_analyze)} 篇论文待分析。")
            paper_service.batch_analyze_papers(papers_to_analyze)
            print("公共分析完成。")
        except Exception as e:
            print(f"公共分析失败: {e}")
            raise

    def process_personalized_papers(self):
        """
        处理个性化论文筛选。
        """
        try:
            from app.services.paper_service import paper_service
            from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
            
            print("开始个性化论文筛选...")
            raw_papers = self.db.table("daily_papers").select("*").execute().data
            if not raw_papers:
                print("没有论文待筛选。")
                return

            # 仅获取额度充足且开启报告的用户
            profiles_data = self.db.table("profiles").select("*") \
                .gt("remaining_quota", 0).eq("receive_email", True).execute().data
            if not profiles_data:
                print("没有符合条件的用户。")
                return

            print(f"正在为 {len(profiles_data)} 个用户进行筛选...")
            for profile_dict in profiles_data:
                try:
                    user_id = profile_dict.get("user_id")
                    user_profile = user_service.get_profile(user_id)
                    if not user_profile: continue

                    print(f"正在处理用户: {user_profile.info.name} ({user_id})")
                    daily_paper_ids = [p['id'] for p in raw_papers]
                    state_response = self.db.table("user_paper_states").select("paper_id") \
                        .eq("user_id", user_id).in_("paper_id", daily_paper_ids).execute()
                    processed_ids = {s['paper_id'] for s in state_response.data} if state_response.data else set()
                    
                    papers_to_filter = []
                    for p in raw_papers:
                        if p['id'] in processed_ids: continue
                        meta = RawPaperMetadata(
                            id=p["id"], title=p["title"], authors=p["authors"],
                            published_date=p["published_date"], category=p["category"],
                            abstract=p["abstract"], links=p["links"], comment=p.get("comment")
                        )
                        papers_to_filter.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
                    
                    if papers_to_filter:
                        print(f"为用户 {user_id} 筛选 {len(papers_to_filter)} 篇论文...")
                        paper_service.filter_papers(papers_to_filter, user_profile, user_id)
                except Exception as e:
                    print(f"处理用户 {profile_dict.get('user_id')} 时出错: {e}")
            print("个性化筛选完成。")
        except Exception as e:
            print(f"个性化筛选失败: {e}")
            raise

    def generate_report_job(self, force: bool = False, target_user_id: Optional[str] = None, progress_callback: Optional[Callable] = None, manual_query: Optional[str] = None, manual_categories: Optional[List[str]] = None, manual_authors: Optional[List[str]] = None, specific_paper_ids: Optional[List[str]] = None, context: Optional[Dict[str, Any]] = None) -> dict:
        """
        执行报告生成任务。
        """
        print("开始生成报告任务...")
        total_stats = {"tokens_input": 0, "tokens_output": 0, "cost": 0.0, "cache_hit_tokens": 0, "request_count": 0}
        
        try:
            if target_user_id:
                profiles_response = self.db.table("profiles").select("*").eq("user_id", target_user_id).gt("remaining_quota", 0).execute()
            else:
                profiles_response = self.db.table("profiles").select("*").gt("remaining_quota", 0).eq("receive_email", True).execute()
                
            profiles_data = profiles_response.data
            if not profiles_data:
                print("没有符合条件的用户。")
                if progress_callback: progress_callback(100, 100, "未找到用户")
                return total_stats
            
            total_users = len(profiles_data)
            for i, profile_dict in enumerate(profiles_data):
                user_id = profile_dict.get("user_id")
                if progress_callback: progress_callback(i+1, total_users, f"正在为用户 {user_id[:8]}... 生成报告")
                
                try:
                    user_profile = user_service.get_profile(user_id)
                    if not self._should_generate_report(user_profile, manual_query): continue
                    
                    custom_title = f"{manual_query} - 即时报告" if manual_query else None
                    if manual_authors: user_profile.focus.authors = manual_authors
                    if not user_profile.info.email: continue
                        
                    print(f"正在为用户生成报告: {user_profile.info.name}")
                    
                    if not force and not manual_query:
                        today_str = datetime.now().strftime("%Y-%m-%d")
                        if self.db.table("reports").select("id").eq("user_id", user_id).eq("date", today_str).execute().data:
                            print(f"用户 {user_profile.info.name} 今日已生成报告，跳过。")
                            continue
                    
                    if specific_paper_ids is not None:
                        if not specific_paper_ids and not manual_query: continue
                        states_res = self.db.table("user_paper_states").select("*").eq("user_id", user_id).in_("paper_id", specific_paper_ids).execute() if specific_paper_ids else None
                    else:
                        today = datetime.now().strftime("%Y-%m-%d")
                        states_res = self.db.table("user_paper_states").select("*").eq("user_id", user_id).eq("accepted", True).gte("created_at", f"{today} 00:00:00").order("relevance_score", desc=True).limit(50).execute()
                    
                    if (not states_res or not states_res.data) and not manual_query: continue
                    
                    papers = []
                    if states_res and states_res.data:
                        paper_ids = [s["paper_id"] for s in states_res.data]
                        papers_data = self.db.table("papers").select("*").in_("id", paper_ids).execute().data
                        state_map = {s["paper_id"]: s for s in states_res.data}
                        from app.services.paper_service import paper_service
                        for p in papers_data:
                            papers.append(paper_service.merge_paper_state(p, state_map.get(p["id"])))
                    
                    temp_context = context.copy() if context else {}
                    user_stats = temp_context.get("user_filter_stats", {}).get(user_id, {})
                    if user_stats:
                        temp_context["crawled_count"] = user_stats.get("analyzed", 0)
                        temp_context["actually_filtered_count"] = user_stats.get("analyzed", 0)
                    
                    report, usage, email_success = report_service.generate_daily_report(papers, user_profile, custom_title=custom_title, manual_query=manual_query, context=temp_context)
                    
                    if usage:
                        total_stats["tokens_input"] += usage.get("prompt_tokens", 0)
                        total_stats["tokens_output"] += usage.get("completion_tokens", 0)
                        total_stats["cost"] += usage.get("cost", 0.0)
                        total_stats["cache_hit_tokens"] += usage.get("cache_hit_tokens", 0)
                        total_stats["request_count"] += 1
                    
                    if email_success:
                        user_service.deduct_quota(user_id=user_id, amount=1, reason="report_generated", report_id=report.id)
                        print(f"✓ 报告已发送并扣减额度: {user_profile.info.name}")
                    else:
                        print(f"⚠️ 报告生成但发送失败: {user_profile.info.name}")
                        
                except Exception as e:
                    print(f"为用户 {user_id} 生成报告失败: {e}")
                    error_notifier.notify_warning("USER_REPORT_FAILED", f"为用户 {user_id} 生成报告失败: {e}", {"user_id": user_id})
            return total_stats
        except Exception as e:
            print(f"报告生成任务失败: {e}")
            return total_stats

    def run_daily_workflow(self, force: bool = False, target_user_id: Optional[str] = None, execution_id: Optional[str] = None):
        """
        运行每日工作流。
        """
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        print(f"正在运行每日工作流 (Force={force}, ExecutionID={execution_id})...")
        
        from app.services.workflow_engine import WorkflowEngine
        from app.services.workflow_steps.check_update_step import CheckUpdateStep
        from app.services.workflow_steps.clear_daily_step import ClearDailyStep
        from app.services.workflow_steps.run_crawler_step import RunCrawlerStep
        from app.services.workflow_steps.fetch_details_step import FetchDetailsStep
        from app.services.workflow_steps.analyze_public_step import AnalyzePublicStep
        from app.services.workflow_steps.personalized_filter_step import PersonalizedFilterStep
        from app.services.workflow_steps.generate_report_step import GenerateReportStep
        
        engine = WorkflowEngine()
        if execution_id: engine.execution_id = execution_id
        
        initial_context = {"force": force, "target_user_id": target_user_id}
        categories, arxiv_date = self.check_arxiv_update()
        
        if (force or target_user_id) and not categories:
            print("强制模式或指定用户模式：正在汇总类别...")
            try:
                if target_user_id:
                    profiles = self.db.table("profiles").select("focus").eq("user_id", target_user_id).execute().data
                else:
                    profiles = self.db.table("profiles").select("focus").gt("remaining_quota", 0).eq("receive_email", True).execute().data
                
                all_cats = set()
                for p in profiles:
                    focus = p.get("focus", {})
                    if focus and "category" in focus:
                        cats = focus["category"]
                        if isinstance(cats, list): all_cats.update(cats)
                        elif isinstance(cats, str): all_cats.add(cats)
                categories = list(all_cats) if all_cats else os.environ.get("CATEGORIES", "cs.CL").split(",")
            except Exception as e:
                print(f"汇总类别失败: {e}")
                categories = os.environ.get("CATEGORIES", "cs.CL").split(",")
        
        if not categories:
            print("Arxiv 未更新且非强制模式。跳过工作流。")
            return

        print(f"开始工作流，类别: {categories}")
        initial_context["categories"] = categories
        initial_context["arxiv_date"] = arxiv_date
        
        if not force and not target_user_id:
            engine.register_step(ClearDailyStep())
        
        engine.register_step(RunCrawlerStep())
        engine.register_step(FetchDetailsStep())
        engine.register_step(AnalyzePublicStep())
        engine.register_step(PersonalizedFilterStep())
        engine.register_step(GenerateReportStep())
        
        try:
            engine.execute_workflow("daily_update", initial_context=initial_context)
        except Exception as e:
            error_msg = f"每日工作流执行失败: {str(e)}"
            print(error_msg)
            import traceback
            error_notifier.notify_critical_error("DAILY_WORKFLOW_FAILED", error_msg, {"force": force, "target_user_id": target_user_id, "execution_id": execution_id, "categories": categories}, traceback.format_exc())
            raise

scheduler_service = SchedulerService()
