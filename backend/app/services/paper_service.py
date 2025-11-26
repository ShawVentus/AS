from typing import List, Optional
import json
import subprocess
import os
from app.schemas.paper import RawPaperMetadata, UserPaperState, PersonalizedPaper, PaperAnalysis, PaperDetails, PaperLinks, PaperFilter, FilterResponse, FilterResultItem
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.core.database import get_db

class PaperService:
    def __init__(self):
        self.db = get_db()

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

    def filter_papers(self, papers: List[PersonalizedPaper], user_profile: UserProfile) -> FilterResponse:
        """
        使用 LLM 批量过滤论文 (Personalized Filter)。
        
        核心逻辑：
        1. 接收论文列表和用户画像。
        2. 将用户画像的关键部分 (Focus, Status) 序列化为 JSON 字符串，作为 LLM 的 Context。
        3. 并发处理每篇论文：
            a. 检查是否已处理过 (避免重复消耗 Token)。
            b. 将论文元数据 (Meta) 序列化为 JSON 字符串。
            c. 调用 `filter_single_paper` 工具函数，传入序列化后的画像和论文数据。
        4. 获取 LLM 结果 (Relevance Score, Reason, Accepted)。
        5. 将结果持久化到数据库 (`user_paper_states` 表) 并更新内存对象。
        6. 构造并返回包含统计信息的 FilterResponse。

        Args:
            papers (List[PersonalizedPaper]): 待过滤的论文列表。
            user_profile (UserProfile): 用户画像对象，包含 Focus (关注点) 和 Status (当前任务/阶段)。

        Returns:
            FilterResponse: 包含统计信息和所有处理过的论文结果列表。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.utils.paper_analysis_utils import filter_single_paper

        # 使用 id 作为 user_id
        user_id = user_profile.info.id
        
        # --- 1. 准备用户上下文 ---
        # 将用户画像中的 Focus (关注领域/关键词) 和 Status (当前任务/阶段) 提取并序列化
        # 目的：减少传递给 LLM 的 Token 数，仅保留筛选决策所需的核心信息
        profile_context = {
            "focus": user_profile.focus.model_dump(),
            "status": user_profile.status.model_dump()
        }
        profile_str = json.dumps(profile_context, ensure_ascii=False, indent=2)

        print(f"Filtering {len(papers)} papers with LLM (Concurrent)...")

        # 结果容器
        selected_papers: List[FilterResultItem] = []
        rejected_papers: List[FilterResultItem] = []
        accepted_count = 0
        rejected_count = 0

        # --- 2. 并发执行 LLM 筛选 ---
        with ThreadPoolExecutor(max_workers=5) as executor:
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
                    continue
                
                # 准备论文数据: 仅使用 meta 部分 (Title, Abstract 等)
                # 序列化为字符串，确保工具函数接收的是纯文本，避免在工具函数内重复序列化
                paper_dict = p.meta.model_dump()
                paper_str = json.dumps(paper_dict, ensure_ascii=False, indent=2)
                
                # 提交任务到线程池
                future = executor.submit(filter_single_paper, paper_str, profile_str)
                future_to_paper[future] = p

            # --- 3. 处理筛选结果 ---
            for future in as_completed(future_to_paper):
                p = future_to_paper[future]
                try:
                    filter_result = future.result()
                    
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
                    print(f"Error filtering paper {p.meta.id}: {e}")
                    # 发生错误时不计入统计或作为失败处理，这里简单跳过

        # --- 4. 排序与构造返回对象 ---
        # 按 relevance_score 降序排列
        selected_papers.sort(key=lambda x: x.relevance_score, reverse=True)
        rejected_papers.sort(key=lambda x: x.relevance_score, reverse=True)

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

        # Check if already analyzed
        if paper.analysis and paper.analysis.motivation:
             return None

        # 准备数据: 仅使用 meta
        paper_dict = paper.meta.model_dump()
        
        # 调用工具函数进行分析
        analysis_dict = analyze_paper_content(paper_dict)
        
        if analysis_dict:
            # Update Public Metadata (papers table) - Flattened structure
            # DB structure: tldr, tags (json), details (json)
            
            # Construct details json
            details_json = {
                "motivation": analysis_dict.get("motivation", ""),
                "method": analysis_dict.get("method", ""),
                "result": analysis_dict.get("result", ""),
                "conclusion": analysis_dict.get("conclusion", "")
            }
            
            update_data = {
                "tldr": analysis_dict.get("tldr", ""),
                "tags": analysis_dict.get("tags", {}),
                "details": details_json
            }
            
            try:
                self.db.table("papers").update(update_data).eq("id", paper.meta.id).execute()
                
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

    def get_recommendations(self, user_id: str) -> List[PersonalizedPaper]:
        """
        获取用户的推荐论文列表 (即已被标记为 accepted=True 的论文)。

        Args:
            user_id (str): 用户 ID。

        Returns:
            List[PersonalizedPaper]: 推荐的论文列表。
        """
        try:
            # 1. Get states where accepted=True
            state_resp = self.db.table("user_paper_states").select("*").eq("user_id", user_id).eq("accepted", True).execute()
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