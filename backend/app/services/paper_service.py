from typing import List, Optional, Union, Callable, Dict, Any
from datetime import datetime, timedelta
import json
import subprocess
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm # 引入 tqdm 用于进度条
from app.schemas.paper import RawPaperMetadata, UserPaperState, PersonalizedPaper, PaperAnalysis, PaperDetails, PaperLinks, PaperFilter, FilterResponse, FilterResultItem, PaperExportRequest
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.core.database import get_db

# 从环境变量获取最大并发数，默认为 2
MAX_WORKERS = int(os.getenv("LLM_MAX_WORKERS", 2))

class PaperService:
    def __init__(self):
        self.db = get_db()
        # 加载类别映射表
        self._load_category_mapping()
    
    def _format_preferences_for_llm(self, preferences: List[str]) -> str:
        """
        将 preferences 列表格式化为 LLM 友好的 Markdown 格式
        
        将用户的研究偏好列表转换为 Markdown 无序列表格式，便于 LLM 理解和处理。
        
        Args:
            preferences (List[str]): 用户的研究偏好列表
        
        Returns:
            str: Markdown 格式化后的字符串，如果列表为空则返回提示文本
            
        Example:
            输入: ["寻找灵感", "跟进前沿"]
            输出: "- 寻找灵感\n- 跟进前沿"
        """
        if preferences and len(preferences) > 0:
            # 格式化为 Markdown 无序列表
            formatted = "\n".join([f"- {pref}" for pref in preferences])
            print(f"[LLM筛选] 格式化 preferences: {len(preferences)} 条")
            return formatted
        else:
            # 空列表，返回提示文本
            return "（用户未设置研究偏好）"
    
    def _load_category_mapping(self):
        """
        加载 arXiv 类别映射表。
        
        从 frontend/src/assets/arxiv_category_simple.json 加载类别映射关系，
        用于将主类别（如 'stat'、'q-fin'）展开为所有子类别。
        
        Args:
            None
            
        Returns:
            None
        """
        try:
            # 构造 JSON 文件的绝对路径
            # backend/app/services/paper_service.py -> backend/
            # 然后向上找到项目根目录，再定位到 frontend/src/assets/
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(os.path.dirname(current_dir))
            project_root = os.path.dirname(backend_root)
            json_path = os.path.join(project_root, "frontend", "src", "assets", "arxiv_category_simple.json")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                self.category_mapping = json.load(f)
            
            print(f"[类别映射] 已加载 {len(self.category_mapping)} 个主类别的映射表")
        except Exception as e:
            print(f"[类别映射] 加载失败: {e}，将使用空映射表")
            self.category_mapping = {}
    
    def expand_categories(self, categories: List[str]) -> List[str]:
        """
        展开类别列表，将主类别转换为所有子类别。
        
        功能：
            1. 遍历输入的类别列表
            2. 如果是主类别（存在于映射表中），展开为所有子类别
            3. 如果已经是子类别，保持不变
            4. 返回展开后的完整类别列表（去重）
        
        Args:
            categories (List[str]): 输入的类别列表，可能包含主类别或子类别
            
        Returns:
            List[str]: 展开后的类别列表
            
        Example:
            输入: ['stat', 'q-fin', 'cs.AI']
            输出: ['stat.AP', 'stat.CO', 'stat.ML', 'stat.ME', 'stat.OT', 'math.ST',
                   'q-fin.CP', 'econ.GN', 'q-fin.GN', ..., 'cs.AI']
        """
        expanded = []
        
        for cat in categories:
            # 检查是否为主类别（在映射表的键中）
            if cat in self.category_mapping:
                # 展开为所有子类别
                subcategories = self.category_mapping[cat]
                expanded.extend(subcategories)
                print(f"[类别展开] '{cat}' -> {len(subcategories)} 个子类别")
            else:
                # 已经是子类别或未知类别，直接添加
                expanded.append(cat)
        
        # 去重并保持顺序
        expanded = list(dict.fromkeys(expanded))
        
        if len(expanded) != len(categories):
            print(f"[类别展开] 输入 {len(categories)} 个类别，展开为 {len(expanded)} 个类别")
        
        return expanded


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

    def archive_daily_papers(self) -> bool:
        """
        将 daily_papers 中的数据归档到 papers 表。
        保留 daily_papers 中的数据。
        
        Args:
            None
            
        Returns:
            bool: 归档是否成功。
        """
        print("Starting archiving daily papers to public DB...")
        try:
            # 1. 获取所有 daily_papers
            # 假设数量不大，一次性获取。如果数量大需要分页。
            response = self.db.table("daily_papers").select("*").execute()
            daily_papers = response.data
            
            if not daily_papers:
                print("No papers in daily_papers to archive.")
                return True
                
            print(f"Found {len(daily_papers)} papers to archive.")
            
            # 2. 批量插入/更新到 papers 表
            # Supabase upsert
            res = self.db.table("papers").upsert(daily_papers).execute()
            
            print(f"Successfully archived {len(res.data)} papers.")
            return True
            
        except Exception as e:
            print(f"Error archiving papers: {e}")
            return False

    def export_papers(self, request: PaperExportRequest) -> Union[str, List[dict]]:
        """
        导出论文功能。
        根据用户请求的条件，从数据库中筛选并导出论文。

        Args:
            request (PaperExportRequest): 导出请求对象，包含筛选条件。
                - user_id: 用户ID
                - date_start: 开始日期（必填，格式：YYYY-MM-DD）
                - date_end: 结束日期（必填，格式：YYYY-MM-DD）
                - limit: 导出数量限制
                - format: 输出格式（markdown/json）
                - min_score: 最低相关性评分（可选）

        Returns:
            str | List[dict]: 如果格式为 markdown，返回字符串；如果为 json，返回字典列表。
        """
        try:
            print(f"开始导出论文: user_id={request.user_id}, 日期范围={request.date_start} 至 {request.date_end}")
            
            # 1. 构建查询 user_paper_states（时间范围为必填）
            query = (self.db.table("user_paper_states")
                    .select("*")
                    .eq("user_id", request.user_id)
                    .gte("created_at", request.date_start)
                    .lte("created_at", f"{request.date_end} 23:59:59"))

            # 评分筛选（可选）
            if request.min_score is not None:
                query = query.gte("relevance_score", request.min_score)

            # 排序并限制数量
            query = query.order("relevance_score", desc=True).limit(request.limit)
            
            # 执行查询
            response = query.execute()
            states = response.data
            
            if not states:
                print("未找到符合条件的论文")
                return "" if request.format == "markdown" else []

            print(f"找到 {len(states)} 篇符合条件的论文")
            paper_ids = [s["paper_id"] for s in states]
            
            # 2. 获取 papers 详情
            papers_resp = self.db.table("papers").select("*").in_("id", paper_ids).execute()
            papers_map = {p["id"]: p for p in papers_resp.data}

            # 3. 合并数据
            results = []
            for state in states:
                p_data = papers_map.get(state["paper_id"])
                if not p_data:
                    print(f"⚠️  警告: 在 papers 表中未找到论文 ID: {state['paper_id']}，跳过")
                    continue
                
                # 合并信息（仅输出需要的字段）
                paper_info = {
                    "id": p_data.get("id"),
                    "title": p_data.get("title"),
                    "authors": p_data.get("authors"),
                    "published_date": p_data.get("published_date"),
                    "abstract": p_data.get("abstract"),
                    "comment": p_data.get("comment"),
                    "why_this_paper": state.get("why_this_paper"),
                }
                results.append(paper_info)
            
            print(f"成功导出 {len(results)} 篇论文")
            
            # 4. 格式化输出
            if request.format == "json":
                return results
            else:
                return self._format_as_markdown(results)

        except Exception as e:
            print(f"导出论文时出错: {e}")
            import traceback
            traceback.print_exc()
            return "" if request.format == "markdown" else []

    def _format_as_markdown(self, papers: List[dict]) -> str:
        """
        将论文列表格式化为 Markdown 文本。

        Args:
            papers (List[dict]): 论文信息列表。

        Returns:
            str: Markdown 格式的文本。
        """
        md_lines = []
        for i, p in enumerate(papers, 1):
            # 添加空值保护
            title = p.get('title') or '无标题'
            paper_id = p.get('id') or '未知'
            authors = p.get('authors', [])
            if isinstance(authors, list) and authors:
                authors_str = ', '.join(authors)
            else:
                authors_str = '未知作者'
            
            why_this_paper = p.get('why_this_paper') or '无推荐理由'
            abstract = p.get('abstract') or '无摘要'
            
            md_lines.append(f"## {i}. {title}")
            md_lines.append(f"**ID**: {paper_id}")
            md_lines.append(f"**作者**: {authors_str}")
            md_lines.append(f"**推荐理由**: {why_this_paper}")
            md_lines.append(f"**摘要**: {abstract}")
            
            # comment 是可选字段
            if p.get('comment'):
                md_lines.append(f"**备注**: {p.get('comment')}")
            
            md_lines.append("---")
        return "\n".join(md_lines)

    def merge_paper_state(self, paper: dict, state: Optional[dict]) -> PersonalizedPaper:
        """
        将论文元数据与用户状态合并 (构造嵌套结构)。
        
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
            "created_at": paper.get("created_at"), # Map created_at
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
                "tldr": details.get("tldr"),
                "tags": details.get("tags") or {},
                "motivation": details.get("motivation"),
                "method": details.get("method"),
                "result": details.get("result"),
                "conclusion": details.get("conclusion")
            }
            analysis = PaperAnalysis(**analysis_data)

        # 3. Construct User State
        user_state = UserPaperState(**state) if state else None

        return PersonalizedPaper(meta=meta, analysis=analysis, user_state=user_state)

    def get_papers_by_categories(self, categories: List[str], user_id: str, limit: int = 1, table_name: str = "papers", force: bool = False, published_date: Optional[str] = None) -> List[PersonalizedPaper]:
        """
        根据用户关注的类别获取候选论文。
        排除已在 user_paper_states 中存在的论文。
        
        Args:
            categories (List[str]): 用户关注的类别列表。
            user_id (str): 用户 ID。
            limit (int): 限制数量。
            table_name (str): 表名。
            force (bool): 是否强制获取（忽略已存在的状态）。

        Returns:
            List[PersonalizedPaper]: 候选论文列表。
        """
        try:
            if not categories:
                return []

            # 1. 获取用户已真正处理过的 paper_ids (排除 "Not Filtered" 状态的论文)
            existing_ids = []
            if not force:
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
            print(f"[DEBUG] 查询参数: table={table_name}, categories={categories}, published_date={published_date}, limit={limit}")
            query = self.db.table(table_name).select("*").overlaps("category", categories).order("created_at", desc=True).limit(limit)
            
            # [NEW] Date Filtering
            if published_date:
                query = query.eq("published_date", published_date)
            
            # 排除已存在的
            if existing_ids:
                # not_in 过滤器
                # query = query.not_.in_("id", existing_ids) # Supabase Python client 语法可能略有不同，通常是 .not_in
                # 简单起见，如果不支持复杂链式，可以在内存中过滤，或者分批查询
                # 尝试使用 filter
                pass 

            response = query.execute()
            papers_data = response.data if response.data else []
            print(f"[DEBUG] 查询返回 {len(papers_data)} 篇论文")

            # 内存过滤 (为了保险起见，或者如果 not_in 语法有问题)
            candidates = []
            for p in papers_data:
                if force or p['id'] not in existing_ids:
                    # 构造默认状态 (None)
                    candidates.append(self.merge_paper_state(p, None))
            
            return candidates

        except Exception as e:
            print(f"Error fetching papers by categories: {e}")
            return []

    def update_user_feedback(self, user_id: str, paper_id: str, liked: Optional[bool], feedback: Optional[str], note: Optional[str] = None) -> bool:
        """
        更新用户对论文的反馈 (Like/Dislike, Reason, Note)。存储到数据库对应字段中

        Args:
            user_id (str): 用户 ID。
            paper_id (str): 论文 ID。
            liked (Optional[bool]): 是否喜欢。
            feedback (Optional[str]): 反馈内容。
            note (Optional[str]): 用户笔记。

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
            if note is not None:
                update_data["note"] = note
            
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
                            "user_feedback": None,
                            "note": None
                        }
                    results.append(self.merge_paper_state(p, state))
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

    def process_pending_papers(self, user_id: str, progress_callback: Optional[Callable[[int, int, str], None]] = None, manual_query: Optional[str] = None, manual_authors: Optional[List[str]] = None, manual_categories: Optional[List[str]] = None, force: bool = False, published_date: Optional[str] = None) -> FilterResponse:
        """
        处理用户的待处理论文 (Pending Papers)。
        
        流程:
        1. 获取用户画像 (Profile)。
        2. 根据画像中的关注类别 (Focus.category) 或手动输入的类别获取候选论文。
        3. 调用 filter_papers 进行批量筛选 (LLM)。
        
        Args:
            user_id (str): 用户 ID。
            progress_callback (Optional[Callable]): 进度回调函数，用于更新任务进度。
            manual_query (Optional[str]): 手动输入的自然语言需求 (覆盖用户画像中的描述)。
            manual_authors (Optional[List[str]]): 手动输入的作者列表 (覆盖用户画像中的作者)。
            manual_categories (Optional[List[str]]): 手动输入的类别列表 (覆盖用户画像中的类别)。
            
        Returns:
            FilterResponse: 筛选结果统计对象，包含已接受、已拒绝的论文列表及统计信息。
        """
        try:
            # 1. 获取用户画像
            # 局部导入以避免循环依赖
            from app.services.user_service import user_service
            profile = user_service.get_profile(user_id)
            print(f"Start processing pending papers for user: {profile.info.name}")
            
            # 2. 获取候选论文
            # 优先使用手动输入的类别，否则使用用户画像中的类别
            categories = manual_categories if manual_categories else profile.focus.category
            
            if not categories:
                print(f"User {profile.info.name} ({user_id}) has no focus categories (and no manual categories provided).")
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
            
            # [新增] 展开类别：将主类别转换为所有子类别
            # 例如: ['stat', 'q-fin'] -> ['stat.AP', 'stat.CO', ..., 'q-fin.CP', ...]
            expanded_categories = self.expand_categories(categories)
            print(f"[类别处理] 原始类别: {categories}")
            print(f"[类别处理] 展开后类别: {expanded_categories}")

            # 获取未处理的论文
            # 优先从 daily_papers 获取 (当日更新)
            # 如果 daily_papers 为空 (例如今天没有更新)，则逻辑上应该返回空，或者根据需求去查 papers
            # 这里按照需求：只关注当日更新
            
            # 临时修改 get_papers_by_categories 支持指定表名
            # [Fix] 增加 limit，否则默认只取 1 条，如果该条已处理则会导致无结果
            # [Fix] Pass force parameter
            # [Fix] Pass published_date parameter
            papers = self.get_papers_by_categories(expanded_categories, user_id, limit=200, table_name="daily_papers", force=force, published_date=published_date)
            
            
            paper_ids = [p.meta.id for p in papers]
            print(f"Collected Paper IDs for {profile.info.name}: {paper_ids}")
            print(f"User: {profile.info.name}, Pending Paper Count: {len(papers)}")
            
            if not papers:
                print(f"No pending papers found for user {profile.info.name} ({user_id}) in expanded categories {expanded_categories}.")
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
            return self.filter_papers(papers, profile, user_id, progress_callback, manual_query, manual_authors, force=force)

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

    def filter_papers(self, papers: List[PersonalizedPaper], user_profile: UserProfile, user_id: str, progress_callback: Optional[Callable[[int, int, str], None]] = None, manual_query: Optional[str] = None, manual_authors: Optional[List[str]] = None, force: bool = False) -> FilterResponse:
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
            progress_callback (Optional[Callable]): 进度回调函数。
            manual_query (Optional[str]): 手动输入的自然语言需求 (覆盖用户画像)。
            manual_authors (Optional[List[str]]): 手动输入的作者 (覆盖用户画像)。

        Returns:
            FilterResponse: 包含统计信息和所有处理过的论文结果列表。
        """
        from app.utils.paper_analysis_utils import filter_single_paper

        start_time = time.time()
        
        # --- 1. 准备用户上下文 ---
        # 将用户画像中的 Focus (关注领域/关键词) 和 Context (当前任务/偏好) 提取并序列化
        # 目的：减少传递给 LLM 的 Token 数，仅保留筛选决策所需的核心信息
        
        # [Manual Override] 如果有手动输入，完全替换为简洁的 Markdown 格式
        if manual_query or manual_authors:
            print(f"[DEBUG] Using manual query mode - replacing user profile")
            print(f"[DEBUG] Manual query: {manual_query}")
            print(f"[DEBUG] Manual authors: {manual_authors}")
            
            # 构建简洁的 Markdown 格式用户画像
            profile_parts = []
            
            if manual_query:
                profile_parts.append(f"**当前查询需求**：{manual_query}")
            
            if manual_authors:
                authors_str = "、".join(manual_authors)
                profile_parts.append(f"**关注作者**：{authors_str}")
            
            profile_str = "\n\n".join(profile_parts)
            
            print(f"[DEBUG] Manual profile (Markdown):\n{profile_str}")
            
        else:
            # 正常流程：使用用户画像
            # 移除 category 字段，避免传入 LLM
            focus_dict = user_profile.focus.model_dump()
            if "category" in focus_dict:
                del focus_dict["category"]
                
            # [Manual Override] 如果有手动输入，覆盖 focus 中的 keywords/description
            if manual_query:
                print(f"[DEBUG] Applying manual query override: {manual_query}")
                # 假设 natural_query 对应 description 或 keywords
                # 为了让 LLM 明确知道这是当前需求，我们可以直接替换 description
                focus_dict["description"] = manual_query
                # 清空 keywords 以避免干扰，或者保留？通常 description 更具体
                focus_dict["keywords"] = [] 
                
            if manual_authors:
                print(f"[DEBUG] Applying manual authors override: {manual_authors}")
                # 假设 focus 中有 authors 字段，如果没有则添加
                focus_dict["authors"] = manual_authors
            
            # 新增：格式化 context.preferences 列表为 Markdown 格式
            context_dict = user_profile.context.model_dump()
            context_dict["preferences"] = self._format_preferences_for_llm(
                context_dict.get("preferences", [])
            )

            profile_context = {
                "focus": focus_dict,
                "context": context_dict
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
        
        # Token 统计
        total_tokens_input = 0
        total_tokens_output = 0
        total_cost = 0.0
        total_cache_hit_tokens = 0
        
        # [Batch Update] 收集所有状态数据
        all_state_data = []

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
                # [Force] 如果 force=True，则忽略已处理状态，强制重新分析
                if not force and p.user_state and p.user_state.why_this_paper and p.user_state.why_this_paper != "Not Filtered":
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
            # 使用 tqdm 显示进度
            total_tasks = len(future_to_paper)
            
            for future in tqdm(as_completed(future_to_paper), total=total_tasks, desc="Filtering Papers"):
                p = future_to_paper[future]
                processed_count += 1
                
                if progress_callback:
                    progress_callback(processed_count, total_tasks, f"正在筛选: {p.meta.title[:30]}...")
                
                
                try:
                    filter_result, retries = future.result()
                    total_retries += retries
                    
                    # 累加 Token 消耗
                    usage = filter_result.get("_usage", {})
                    total_tokens_input += usage.get("prompt_tokens", 0)
                    total_tokens_output += usage.get("completion_tokens", 0)
                    total_cost += usage.get("cost", 0.0)
                    total_cache_hit_tokens += usage.get("cache_hit_tokens", 0)
                    
                    # 构造状态数据字典
                    state_data = {
                        "user_id": user_id,
                        "paper_id": p.meta.id,
                        "relevance_score": filter_result["relevance_score"],
                        "why_this_paper": filter_result["why_this_paper"],
                        "accepted": filter_result["accepted"],
                        "user_liked": None,
                        "user_feedback": None,
                        "note": None
                    }

                    # [Batch Update] 收集数据，不立即写入
                    all_state_data.append(state_data)

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

        # [Batch Update] 批量写入数据库
        if all_state_data:
            # print(f"Batch updating {len(all_state_data)} user paper states...")
            try:
                # 分批写入，防止一次性包过大
                batch_size = 100
                for i in range(0, len(all_state_data), batch_size):
                    batch = all_state_data[i:i + batch_size]
                    self.db.table("user_paper_states").upsert(batch).execute()
                # print("Batch update user states completed.")
            except Exception as e:
                print(f"Error batch updating user paper states: {e}")

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
        
        # 计算总 Token 消耗 (从 all_state_data 或重新遍历)
        # 由于我们没有在 all_state_data 保存 usage，我们需要在 future 处理循环中累加
        # 为了避免大规模重写，我们假设 _filter_with_retry 返回了 usage (需要修改 _filter_with_retry)
        # 但 _filter_with_retry 是内部函数，修改它需要修改 ThreadPoolExecutor 的调用
        # 让我们简化：在 future.result() 中获取 usage
        
        # 这里的代码块是 filter_papers 的尾部，无法访问 executor 循环中的局部变量
        # 因此必须重写 filter_papers 的 executor 循环部分
        
        from datetime import datetime
        return FilterResponse(
            user_id=user_id,
            created_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_analyzed=accepted_count + rejected_count,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            selected_papers=selected_papers,
            rejected_papers=rejected_papers,
            tokens_input=total_tokens_input,
            tokens_output=total_tokens_output,
            cost=total_cost,
            cache_hit_tokens=total_cache_hit_tokens,
            request_count=accepted_count + rejected_count
        )

    def analyze_paper(self, paper: PersonalizedPaper) -> Optional[dict]:
        """
        使用 LLM 对单篇论文进行深度分析 (Public Analysis)。
        仅当论文尚未分析 (analysis 为空) 时执行。
        
        Args:
            paper (PersonalizedPaper): 待分析的论文对象。

        Returns:
            Optional[dict]: 需要更新到 daily_papers 的数据字典 (包含 id, details, status)。
                            如果分析失败或无内容，返回 None。
        """
        from app.utils.paper_analysis_utils import analyze_paper_content

        # 准备数据: 仅使用 meta
        paper_dict = paper.meta.model_dump()
        
        # 调用工具函数进行分析
        analysis_dict = analyze_paper_content(paper_dict)
        
        # [Debug] 打印原始返回数据
        # if analysis_dict:
            # print(f"🔍 [DEBUG] Paper {paper.meta.id} LLM Raw Output Keys: {list(analysis_dict.keys())}")
            # 避免打印过长，只打印前 200 字符
            # print(f"🔍 [DEBUG] Content Preview: {str(analysis_dict)[:200]}...")
        
        # 检查返回结果是否有效 (必须包含关键字段，且不能只是空字典或仅有 _usage)
        if not analysis_dict or (len(analysis_dict) == 1 and "_usage" in analysis_dict):
            print(f"⚠️ 论文 {paper.meta.id} 分析结果为空或无效，跳过更新。")
            return None

        # 提取 usage，避免存入 details
        usage = analysis_dict.pop("_usage", {})
        
        # 构造更新数据
        # [Fix] 包含所有必要字段以避免 upsert 时的非空约束错误
        # 虽然理论上 upsert 只更新指定字段，但为了稳妥，我们带上所有元数据
        update_data = {
            "id": paper.meta.id,
            "title": paper.meta.title,
            "authors": paper.meta.authors,
            "published_date": str(paper.meta.published_date) if paper.meta.published_date else None,
            "category": paper.meta.category,
            "abstract": paper.meta.abstract,
            # [Fix] 序列化 links 对象为字典，避免 JSON 序列化错误
            "links": paper.meta.links.model_dump() if hasattr(paper.meta.links, 'model_dump') else paper.meta.links,
            "comment": paper.meta.comment,
            "details": analysis_dict,
            "status": "analyzed",
            "_usage": usage # 透传 usage 给调用者，但不存入 details 字段
        }
            
        return update_data
    def batch_analyze_papers(self, papers: List[PersonalizedPaper], progress_callback: Optional[Callable[[int, int, str], None]] = None) -> Dict[str, Any]:
        """
        并发批量分析论文 (Public Analysis)。
        [Modified] 并发分析后，批量写入 daily_papers 数据库。
        [Modified] 改为每 5 篇写入一次，以提供更快的反馈并防止数据丢失。
        [Optimized] 使用配置文件中的并发数，批量完成后输出汇总统计。

        Args:
            papers (List[PersonalizedPaper]): 待分析的论文列表。
            progress_callback (Optional[Callable]): 进度回调函数。
        
        Returns:
            Dict[str, int]: Token 消耗统计 {"tokens_input": int, "tokens_output": int}
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.core.config import settings
        
        # 筛选出未分析的论文
        papers_to_analyze = [p for p in papers if not (p.analysis and p.analysis.motivation)]
        
        if not papers_to_analyze:
            print("No papers need analysis.")
            return {"tokens_input": 0, "tokens_output": 0}

        print(f"Analyzing {len(papers_to_analyze)} papers content (Concurrent)...")
        
        results = []
        # 使用配置文件中的并发数
        max_workers = settings.LLM_MAX_WORKERS
        
        # 定义写入批次大小
        write_batch_size = 5
        
        # 统计数据
        stats = {
            "tokens_input": 0,
            "tokens_output": 0,
            "cost": 0.0,
            "cache_hit_tokens": 0,
            "request_count": 0
        }

        failed_count = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_paper = {executor.submit(self.analyze_paper, p): p for p in papers_to_analyze}
            
            # 使用 tqdm 显示进度
            completed_count = 0
            total_count = len(papers_to_analyze)
            
            for future in tqdm(as_completed(future_to_paper), total=total_count, desc="Analyzing Papers"):
                p = future_to_paper[future]
                completed_count += 1
                if progress_callback:
                    progress_callback(completed_count, total_count, f"正在分析: {p.meta.title[:30]}...")
                try:
                    data = future.result()
                    if data:
                        # 提取 usage (analyze_paper 已经将 _usage 放在顶层)
                        usage = data.pop("_usage", {})
                        
                        stats["tokens_input"] += usage.get("prompt_tokens", 0)
                        stats["tokens_output"] += usage.get("completion_tokens", 0)
                        stats["cost"] += usage.get("cost", 0.0)
                        stats["cache_hit_tokens"] += usage.get("cache_hit_tokens", 0)
                        stats["request_count"] += 1
                        
                        results.append(data)
                    else:
                        failed_count += 1
                        stats["request_count"] += 1 # 失败也算一次请求尝试
                except Exception as e:
                    print(f"Error analyzing paper {p.meta.id}: {e}")
                    failed_count += 1
                    stats["request_count"] += 1
                
                # 批量写入 (每 write_batch_size 篇)
                if len(results) >= write_batch_size:
                    try:
                        self.db.table("daily_papers").upsert(results).execute()
                        # print(f"Saved {len(results)} analyzed papers.")
                        results = []
                    except Exception as e:
                        print(f"Error saving batch analysis: {e}")

            # 写入剩余的
            if results:
                try:
                    self.db.table("daily_papers").upsert(results).execute()
                    # print(f"Saved {len(results)} analyzed papers.")
                except Exception as e:
                    print(f"Error saving remaining analysis: {e}")
        
        # [Optimized] 批量完成后输出汇总统计（使用 finally 确保一定输出）
        try:
            success_count = total_count - failed_count
            print(f"✅ 批量分析完成: 成功 {success_count}/{total_count} 篇 " +
                  f"| Tokens: {stats['tokens_input']}(输入) + {stats['tokens_output']}(输出) = {stats['tokens_input'] + stats['tokens_output']}(总计) " +
                  f"| 成本: ${stats['cost']:.4f}")
            
            if failed_count > 0:
                print(f"⚠️ Analysis completed with {failed_count} failures.")
        except Exception as e:
            print(f"Error printing summary: {e}")

        return stats

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
            
            return self.merge_paper_state(paper_data, state_data)
        except Exception as e:
            print(f"Error fetching paper {paper_id}: {e}")
            return None

    def get_papers_by_ids_with_user(self, paper_ids: List[str], user_id: str) -> List[PersonalizedPaper]:
        """
        批量获取论文详情，包含用户状态。

        Args:
            paper_ids (List[str]): 论文 ID 列表。
            user_id (str): 用户 ID。

        Returns:
            List[PersonalizedPaper]: 论文对象列表。
        """
        try:
            if not paper_ids:
                return []

            # 1. 查询公共论文库
            response = self.db.table("papers").select("*").in_("id", paper_ids).execute()
            papers_data = response.data if response.data else []
            
            # 2. 查询用户状态
            states_map = {}
            if user_id:
                state_resp = self.db.table("user_paper_states").select("*").in_("paper_id", paper_ids).eq("user_id", user_id).execute()
                if state_resp.data:
                    for s in state_resp.data:
                        states_map[s['paper_id']] = s
            
            # 3. 合并
            results = []
            for p in papers_data:
                state = states_map.get(p['id'])
                results.append(self.merge_paper_state(p, state))
                
            return results
        except Exception as e:
            print(f"批量获取论文失败: {e}")
            return []

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
            # 1. Get states where why_this_paper is not 'Not Filtered' (meaning it has been analyzed)
            # Previously filtered by accepted=True, now returning all analyzed papers for frontend filtering
            query = self.db.table("user_paper_states").select("*").eq("user_id", user_id).neq("why_this_paper", "Not Filtered")
            
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
                    results.append(self.merge_paper_state(p_data, s))
            return results
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []

    def archive_daily_papers(self) -> bool:
        """
        将 daily_papers 表中的数据归档到 papers 表。
        [Fix] 使用批处理以避免 Errno 35 资源耗尽错误。
        """
        print("Starting archiving daily papers to public DB...")
        try:
            # 1. 获取所有 daily_papers
            # 如果数据量非常大，这里也应该分页获取，但通常 daily_papers 不会太大 (几百条)
            response = self.db.table("daily_papers").select("*").execute()
            daily_papers = response.data
            
            if not daily_papers:
                print("No daily papers to archive.")
                return True
                
            print(f"Found {len(daily_papers)} papers to archive.")
            
            # 2. 批量插入到 papers 表
            # 使用 upsert (on_conflict="id") 避免重复
            # 分批处理，每批 50 条
            batch_size = 50
            total = len(daily_papers)
            
            for i in range(0, total, batch_size):
                batch = daily_papers[i:i + batch_size]
                try:
                    self.db.table("papers").upsert(batch).execute()
                    # print(f"Archived batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")
                    # 小睡一下，释放资源
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Error archiving batch {i}: {e}")
                    # 即使某批失败，也尝试继续下一批？或者直接失败？
                    # 这里选择记录错误但继续，尽可能多地归档
            
            print("Daily papers archived successfully.")
            return True
            
        except Exception as e:
            print(f"Error archiving papers: {e}")
            return False

paper_service = PaperService()