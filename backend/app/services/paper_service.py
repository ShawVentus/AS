from typing import List, Optional
from datetime import datetime, timedelta
import json
import subprocess
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.schemas.paper import RawPaperMetadata, UserPaperState, PersonalizedPaper, PaperAnalysis, PaperDetails, PaperLinks, PaperFilter, FilterResponse, FilterResultItem
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.core.database import get_db

MAX_WORKERS = 5

class PaperService:
    def __init__(self):
        self.db = get_db()

    def clear_daily_papers(self) -> bool:
        """
        清空每日更新数据库。
        """
        try:
            # delete all rows
            self.db.table("daily_papers").delete().neq("id", "00000").execute()
            return True
        except Exception as e:
            print(f"Error clearing daily papers: {e}")
            return False

    def _merge_paper_state(self, paper: dict, state: Optional[dict]) -> PersonalizedPaper:
        """
        辅助方法：将论文元数据与用户状态合并 (构造嵌套结构)。

        Args:
            paper (dict): 原始论文数据字典。
            state (Optional[dict]): 用户状态数据字典，如果不存在则为 None。

        Returns:
            PersonalizedPaper: 合并后的个性化论文对象。
        """
        # 1. Construct Meta
        meta_data = {
            "id": paper["id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "published_date": paper["published_date"],
            "category": paper["category"],
            "abstract": paper["abstract"],
            "links": paper["links"],
            "comment": paper.get("comment")
        }
        meta = RawPaperMetadata(**meta_data)

        # 2. Construct Analysis
        # 检查是否有分析数据 (details 或 tldr)
        analysis = None
        if paper.get("details") or paper.get("tldr"):
            details = paper.get("details") or {}
            analysis_data = {
                "tldr": paper.get("tldr"),
                "tags": paper.get("tags") or {},
                "motivation": details.get("motivation"),
                "method": details.get("method"),
                "result": details.get("result"),
                "conclusion": details.get("conclusion")
            }
            analysis = PaperAnalysis(**analysis_data)

        # 3. Construct User State
        user_state = UserPaperState(**state) if state else None

        return PersonalizedPaper(meta=meta, analysis=analysis, user_state=user_state)

    def get_papers_by_categories(self, categories: List[str], user_id: str, limit: int = 1, table_name: str = "papers") -> List[PersonalizedPaper]:
        """
        根据用户关注的类别获取候选论文。
        排除已在 user_paper_states 中存在的论文。

        Args:
            categories (List[str]): 用户关注的类别列表。
            user_id (str): 用户 ID。
            limit (int): 限制数量。

        Returns:
            List[PersonalizedPaper]: 候选论文列表。
        """
        try:
            if not categories:
                return []

            # 1. 获取用户已真正处理过的 paper_ids (排除 "Not Filtered" 状态的论文)
            existing_states = self.db.table("user_paper_states")\
                .select("paper_id")\
                .eq("user_id", user_id)\
                .neq("why_this_paper", "Not Filtered")\
                .execute()
            existing_ids = [row['paper_id'] for row in existing_states.data] if existing_states.data else []

            # 2. 查询符合类别的论文
            # 使用 overlaps (数组重叠) 匹配类别
            # 注意: Supabase (PostgREST) 的 overlaps 语法是 cs (contains) 或 cd (contained by) 或 ov (overlap)
            # 这里假设 category 字段是 text[] 类型
            query = self.db.table(table_name).select("*").overlaps("category", categories).order("created_at", desc=True).limit(limit)
            
            # 排除已存在的
            if existing_ids:
                # not_in 过滤器
                # query = query.not_.in_("id", existing_ids) # Supabase Python client 语法可能略有不同，通常是 .not_in
                # 简单起见，如果不支持复杂链式，可以在内存中过滤，或者分批查询
                # 尝试使用 filter
                pass 

            response = query.execute()
            papers_data = response.data if response.data else []

            # 内存过滤 (为了保险起见，或者如果 not_in 语法有问题)
            candidates = []
            for p in papers_data:
                if p['id'] not in existing_ids:
                    # 构造默认状态 (None)
                    candidates.append(self._merge_paper_state(p, None))
            
            return candidates

        except Exception as e:
            print(f"Error fetching papers by categories: {e}")
            return []

    def update_user_feedback(self, user_id: str, paper_id: str, liked: Optional[bool], feedback: Optional[str]) -> bool:
        """
        更新用户对论文的反馈 (Like/Dislike, Reason)。存储到数据库对应字段中

        Args:
            user_id (str): 用户 ID。
            paper_id (str): 论文 ID。
            liked (Optional[bool]): 是否喜欢。
            feedback (Optional[str]): 反馈内容。

        Returns:
            bool: 是否更新成功。
        """
        try:
            # 构造更新数据
            update_data = {
                "user_id": user_id,
                "paper_id": paper_id,
                # 仅更新非空字段，或者全部更新？通常是 patch 更新
            }
            if liked is not None:
                update_data["user_liked"] = liked
            if feedback is not None:
                update_data["user_feedback"] = feedback
            
            # 使用 upsert，确保如果记录不存在也能创建 (虽然理论上应该先有 filter 记录)
            # 但为了健壮性，如果用户直接对某篇未 filter 的论文操作 (极少情况)，也能记录
            self.db.table("user_paper_states").upsert(update_data).execute()
            return True
        except Exception as e:
            print(f"Error updating user feedback: {e}")
            return False

    def get_papers(self, user_id: str) -> List[PersonalizedPaper]:
        """
        从数据库获取所有论文，并附加指定用户的状态信息。

        Args:
            user_id (str): 用户 ID。

        Returns:
            List[PersonalizedPaper]: 个性化论文列表。
        """
        try:
            # 1. Fetch Papers
            response = self.db.table("papers").select("*").order("created_at", desc=True).limit(50).execute()
            papers_data = response.data if response.data else []
            
            # 2. Fetch User States
            states_map = {}
            if user_id:
                state_response = self.db.table("user_paper_states").select("*").eq("user_id", user_id).execute()
                if state_response.data:
                    for s in state_response.data:
                        states_map[s['paper_id']] = s

            # 3. Merge
            results = []
            for p in papers_data:
                try:
                    state = states_map.get(p['id'])
                    # If no state exists, create a default one (in memory only)
                    if not state:
                        state = {
                            "paper_id": p['id'],
                            "user_id": user_id,
                            "relevance_score": 0.0,
                            "why_this_paper": "Not Filtered", # Default
                            "accepted": False,
                            "user_accepted": False,
                            "user_liked": None,
                            "user_feedback": None
                        }
                    results.append(self._merge_paper_state(p, state))
                except Exception as validation_error:
                    print(f"⚠️ Skipping invalid paper {p.get('id')}: {validation_error}")
            return results
        except Exception as e:
            print(f"Error fetching papers: {e}")
            return []

    def crawl_arxiv_new(self, user_id: str, limit: int = 100) -> List[PersonalizedPaper]:
        """
        触发爬虫抓取最新的 Arxiv 论文。

        Args:
            user_id (str): 用户 ID。
            limit (int, optional): 抓取限制数量。默认为 100。

        Returns:
            List[PersonalizedPaper]: 抓取后最新的论文列表。
        """
        try:
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=backend_root)
            return self.get_papers(user_id)
        except Exception as e:
            print(f"Error crawling: {e}")
            return self.get_papers(user_id)

    def process_pending_papers(self, user_id: str) -> FilterResponse:
        """
        处理用户的待处理论文 (Pending Papers)。
        
        流程:
        1. 获取用户画像 (Profile)。
        2. 根据画像中的关注类别 (Focus.category) 获取候选论文。
        3. 调用 filter_papers 进行批量筛选 (LLM)。
        
        Args:
            user_id (str): 用户 ID。
            
        Returns:
            FilterResponse: 筛选结果统计。
        """
        try:
            # 1. 获取用户画像
            # 局部导入以避免循环依赖
            from app.services.user_service import user_service
            profile = user_service.get_profile(user_id)
            print(f"Start processing pending papers for user: {profile.info.name}")
            
            # 2. 获取候选论文
            # 使用用户关注的类别
            categories = profile.focus.category
            if not categories:
                print(f"User {profile.info.name} ({user_id}) has no focus categories.")
                # 返回空结果
                from app.schemas.paper import FilterResponse
                from datetime import datetime
                return FilterResponse(
                    user_id=user_id,
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    total_analyzed=0,
                    accepted_count=0,
                    rejected_count=0,
                    selected_papers=[],
                    rejected_papers=[]
                )

            # 获取未处理的论文
            # 优先从 daily_papers 获取 (当日更新)
            # 如果 daily_papers 为空 (例如今天没有更新)，则逻辑上应该返回空，或者根据需求去查 papers
            # 这里按照需求：只关注当日更新
            
            # 临时修改 get_papers_by_categories 支持指定表名
            papers = self.get_papers_by_categories(categories, user_id, table_name="daily_papers")
            
            # 如果 daily_papers 没有找到，是否回退到 papers? 
            # 根据 "减少计算量" 的初衷，应该只处理 daily_papers。
            # 但为了测试方便，如果 daily_papers 为空，暂时不回退，直接返回空。
            
            
            paper_ids = [p.meta.id for p in papers]
            print(f"Collected Paper IDs for {profile.info.name}: {paper_ids}")
            print(f"User: {profile.info.name}, Pending Paper Count: {len(papers)}")
            
            if not papers:
                print(f"No pending papers found for user {profile.info.name} ({user_id}) in categories {categories}.")
                from app.schemas.paper import FilterResponse
                from datetime import datetime
                return FilterResponse(
                    user_id=user_id,
                    created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    total_analyzed=0,
                    accepted_count=0,
                    rejected_count=0,
                    selected_papers=[],
                    rejected_papers=[]
                )

            # 3. 批量筛选
            return self.filter_papers(papers, profile, user_id)

        except Exception as e:
            print(f"Error processing pending papers: {e}")
            import traceback
            traceback.print_exc()
            # 返回空结果或抛出异常
            from app.schemas.paper import FilterResponse
            from datetime import datetime
            return FilterResponse(
                user_id=user_id,
                created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_analyzed=0,
                accepted_count=0,
                rejected_count=0,
                selected_papers=[],
                rejected_papers=[]
            )

    def filter_papers(self, papers: List[PersonalizedPaper], user_profile: UserProfile, user_id: str) -> FilterResponse:
        """
        使用 LLM 批量过滤论文 (Personalized Filter)。
        
        核心逻辑：
        1. 接收论文列表和用户画像。
        2. 将用户画像的关键部分 (Focus, Status) 序列化为 JSON 字符串，作为 LLM 的 Context。
        3. 并发处理每篇论文：
            a. 检查是否已处理过 (避免重复消耗 Token)。
            b. 将论文元数据 (Meta) 序列化为 JSON 字符串。
            c. 调用 `_filter_with_retry` 工具函数，传入序列化后的画像和论文数据。
        4. 获取 LLM 结果 (Relevance Score, Reason, Accepted)。
        5. 将结果持久化到数据库 (`user_paper_states` 表) 并更新内存对象。
        6. 构造并返回包含统计信息的 FilterResponse。

        Args:
            papers (List[PersonalizedPaper]): 待过滤的论文列表。
            user_profile (UserProfile): 用户画像对象，包含 Focus (关注点) 和 Status (当前任务/阶段)。
            user_id (str): 用户 ID。

        Returns:
            FilterResponse: 包含统计信息和所有处理过的论文结果列表。
        """
        from app.utils.paper_analysis_utils import filter_single_paper

        start_time = time.time()
        
        # --- 1. 准备用户上下文 ---
        # 将用户画像中的 Focus (关注领域/关键词) 和 Context (当前任务/偏好) 提取并序列化
        # 目的：减少传递给 LLM 的 Token 数，仅保留筛选决策所需的核心信息
        
        # 移除 category 字段，避免传入 LLM
        focus_dict = user_profile.focus.model_dump()
        if "category" in focus_dict:
            del focus_dict["category"]
            
        profile_context = {
            "focus": focus_dict,
            "context": user_profile.context.model_dump()
        }
        profile_str = json.dumps(profile_context, ensure_ascii=False, indent=2)

        print(f"Filtering {len(papers)} papers with LLM (Concurrent, Max Workers={MAX_WORKERS})...")

        # 结果容器
        selected_papers: List[FilterResultItem] = []
        rejected_papers: List[FilterResultItem] = []
        accepted_count = 0
        rejected_count = 0
        total_retries = 0
        processed_count = 0
        total_papers = len(papers)

        # 内部重试函数
        def _filter_with_retry(paper_str, profile_str):
            retries = 0
            max_retries = 3
            last_error = None
            while retries < max_retries:
                try:
                    result = filter_single_paper(paper_str, profile_str)
                    return result, retries
                except Exception as e:
                    retries += 1
                    last_error = e
                    print(f"Retry {retries}/{max_retries} failed: {e}")
                    time.sleep(1) # 简单的退避
            raise last_error

        # --- 2. 并发执行 LLM 筛选 ---
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_paper = {}
            for p in papers:
                # 优化：如果已经有推荐理由且不是默认值，说明已处理过
                if p.user_state and p.user_state.why_this_paper and p.user_state.why_this_paper != "Not Filtered":
                    # 已处理过的也要加入统计
                    item = FilterResultItem(
                        paper_id=p.meta.id,
                        why_this_paper=p.user_state.why_this_paper,
                        relevance_score=p.user_state.relevance_score,
                        accepted=p.user_state.accepted
                    )
                    if item.accepted:
                        selected_papers.append(item)
                        accepted_count += 1
                    else:
                        rejected_papers.append(item)
                        rejected_count += 1
                    
                    processed_count += 1
                    continue
                
                # 准备论文数据: 仅使用 meta 部分 (Title, Abstract 等)
                # 序列化为字符串，确保工具函数接收的是纯文本，避免在工具函数内重复序列化
                paper_dict = p.meta.model_dump()
                paper_str = json.dumps(paper_dict, ensure_ascii=False, indent=2)
                
                # 提交任务到线程池
                future = executor.submit(_filter_with_retry, paper_str, profile_str)
                future_to_paper[future] = p

            # --- 3. 处理筛选结果 ---
            for future in as_completed(future_to_paper):
                p = future_to_paper[future]
                processed_count += 1
                
                # 进度日志
                if processed_count % 10 == 0 or processed_count == total_papers:
                    print(f"Progress: {processed_count}/{total_papers} papers processed...")

                try:
                    filter_result, retries = future.result()
                    total_retries += retries
                    
                    # 构造状态数据字典
                    state_data = {
                        "user_id": user_id,
                        "paper_id": p.meta.id,
                        "relevance_score": filter_result["relevance_score"],
                        "why_this_paper": filter_result["why_this_paper"],
                        "accepted": filter_result["accepted"],
                        "user_liked": None,
                        "user_feedback": None
                    }

                    # a. 持久化到数据库 (Upsert: 存在则更新，不存在则插入)
                    self.db.table("user_paper_states").upsert(state_data).execute()

                    # b. 更新内存中的论文对象状态 (虽然不再直接返回列表，但更新对象是个好习惯)
                    p.user_state = UserPaperState(**state_data)

                    # c. 添加到结果列表
                    item = FilterResultItem(
                        paper_id=p.meta.id,
                        why_this_paper=filter_result["why_this_paper"],
                        relevance_score=filter_result["relevance_score"],
                        accepted=filter_result["accepted"]
                    )
                    
                    if item.accepted:
                        selected_papers.append(item)
                        accepted_count += 1
                    else:
                        rejected_papers.append(item)
                        rejected_count += 1

                except Exception as e:
                    print(f"Error filtering paper {p.meta.id} after retries: {e}")
                    # 发生错误时不计入统计或作为失败处理，这里简单跳过

        # --- 4. 排序与构造返回对象 ---
        # 按 relevance_score 降序排列
        selected_papers.sort(key=lambda x: x.relevance_score, reverse=True)
        rejected_papers.sort(key=lambda x: x.relevance_score, reverse=True)

        end_time = time.time()
        total_time = end_time - start_time
        
        # 汇总日志
        print(f"Filtering Completed.")
        print(f"Total Time: {total_time:.2f}s")
        print(f"Total Papers: {total_papers}")
        print(f"Accepted: {accepted_count}, Rejected: {rejected_count}")
        print(f"Total Retries: {total_retries}")

        from datetime import datetime
        return FilterResponse(
            user_id=user_id,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_analyzed=accepted_count + rejected_count,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            selected_papers=selected_papers,
            rejected_papers=rejected_papers
        )

    def analyze_paper(self, paper: PersonalizedPaper) -> Optional[PaperAnalysis]:
        """
        使用 LLM 对单篇论文进行深度分析 (Public Analysis)。
        仅当论文尚未分析 (analysis 为空) 时执行。

        Args:
            paper (PersonalizedPaper): 待分析的论文对象。

        Returns:
            Optional[PaperAnalysis]: 分析结果对象，如果分析失败或已存在则返回 None。
        """
        from app.utils.paper_analysis_utils import analyze_paper_content

        # Check if already analyzed (Optional, relying on scheduler to pass pending papers)
        # if paper.analysis and paper.analysis.motivation:
        #      return None

        # 准备数据: 仅使用 meta
        paper_dict = paper.meta.model_dump()
        
        # 调用工具函数进行分析
        analysis_dict = analyze_paper_content(paper_dict)
        
        if analysis_dict:
            # Update Public Metadata (papers table)
            # Store all 6 fields in 'details' jsonb and update status to 'completed'
            
            update_data = {
                "details": analysis_dict,
                "status": "analyzed"
            }
            
            try:
                # 1. Update daily_papers
                self.db.table("daily_papers").update(update_data).eq("id", paper.meta.id).execute()
                
                # 2. Insert into papers (Public DB)
                # 需要构造完整的 record
                full_paper_data = paper.meta.model_dump()
                full_paper_data.update(update_data)
                # category 是 list, 需要确保格式正确
                
                self.db.table("papers").upsert(full_paper_data).execute()
                
                return PaperAnalysis(**analysis_dict)
            except Exception as e:
                print(f"Error updating paper metadata: {e}")
                return None
            
        return None

    def batch_analyze_papers(self, papers: List[PersonalizedPaper]) -> None:
        """
        并发批量分析论文 (Public Analysis)。

        Args:
            papers (List[PersonalizedPaper]): 待分析的论文列表。

        Returns:
            None
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # 筛选出未分析的论文
        papers_to_analyze = [p for p in papers if not (p.analysis and p.analysis.motivation)]
        
        if not papers_to_analyze:
            print("No papers need analysis.")
            return

        print(f"Analyzing {len(papers_to_analyze)} papers content (Concurrent)...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_paper = {executor.submit(self.analyze_paper, p): p for p in papers_to_analyze}
            
            for future in as_completed(future_to_paper):
                p = future_to_paper[future]
                try:
                    future.result() 
                except Exception as e:
                    print(f"Error analyzing paper {p.meta.id}: {e}")

    def get_paper_by_id(self, paper_id: str, user_id: str) -> Optional[PersonalizedPaper]:
        """
        根据 ID 获取单篇论文的详细信息。

        Args:
            paper_id (str): 论文的唯一标识符。
            user_id (str): 用户 ID，用于获取该用户对该论文的状态。

        Returns:
            Optional[PersonalizedPaper]: 如果找到则返回论文对象，否则返回 None。
        """
        try:
            # 1. Fetch Paper
            response = self.db.table("papers").select("*").eq("id", paper_id).execute()
            if not response.data:
                return None
            paper_data = response.data[0]
            
            # 2. Fetch State
            state_data = None
            if user_id:
                state_resp = self.db.table("user_paper_states").select("*").eq("user_id", user_id).eq("paper_id", paper_id).execute()
                if state_resp.data:
                    state_data = state_resp.data[0]
            
            return self._merge_paper_state(paper_data, state_data)
        except Exception as e:
            print(f"Error fetching paper {paper_id}: {e}")
            return None

    def get_paper_dates(self, user_id: str, year: int, month: int) -> List[str]:
        """
        获取指定月份中存在已接受论文的日期列表。

        Args:
            user_id (str): 用户 ID。
            year (int): 年份。
            month (int): 月份。

        Returns:
            List[str]: 日期字符串列表 (YYYY-MM-DD)。
        """
        try:
            # 构建日期范围
            start_date = f"{year}-{month:02d}-01"
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"

            # 查询 user_paper_states
            # 筛选条件: user_id, accepted=True, created_at 在范围内
            response = self.db.table("user_paper_states") \
                .select("created_at") \
                .eq("user_id", user_id) \
                .eq("accepted", True) \
                .gte("created_at", start_date) \
                .lt("created_at", end_date) \
                .execute()

            if not response.data:
                return []

            # 提取日期并去重
            dates = set()
            for item in response.data:
                # created_at 是 ISO 格式 (e.g., 2023-11-29T10:00:00+00:00)
                # 截取前 10 位作为日期
                date_str = item["created_at"][:10]
                dates.add(date_str)

            return sorted(list(dates))
        except Exception as e:
            print(f"Error fetching paper dates: {e}")
            return []

    def get_recommendations(self, user_id: str, date: Optional[str] = None) -> List[PersonalizedPaper]:
        """
        获取用户的推荐论文列表 (即已被标记为 accepted=True 的论文)。
        支持按日期筛选。

        Args:
            user_id (str): 用户 ID。
            date (Optional[str]): 筛选日期 (YYYY-MM-DD)。如果为 None，则返回所有。

        Returns:
            List[PersonalizedPaper]: 推荐的论文列表。
        """
        try:
            # 1. Get states where accepted=True
            query = self.db.table("user_paper_states").select("*").eq("user_id", user_id).eq("accepted", True)
            
            if date:
                # 筛选指定日期的记录 (created_at >= date AND created_at < date + 1 day)
                # 注意：这里假设 date 是 YYYY-MM-DD 格式
                next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                query = query.gte("created_at", date).lt("created_at", next_day)
            
            state_resp = query.execute()
            
            if not state_resp.data:
                return []
            
            states = state_resp.data
            paper_ids = [s['paper_id'] for s in states]
            
            # 2. Get papers
            # Supabase 'in' filter: .in_("id", paper_ids)
            if not paper_ids:
                return []
                
            paper_resp = self.db.table("papers").select("*").in_("id", paper_ids).execute()
            papers_map = {p['id']: p for p in paper_resp.data}
            
            # 3. Merge
            results = []
            for s in states:
                p_data = papers_map.get(s['paper_id'])
                if p_data:
                    results.append(self._merge_paper_state(p_data, s))
            return results
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []

paper_service = PaperService()