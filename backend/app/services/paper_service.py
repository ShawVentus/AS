from typing import List, Optional
import json
import subprocess
import os
from app.schemas.paper import PaperMetadata, UserPaperState, PersonalizedPaper, PaperAnalysis, PaperDetails, PaperLinks
from app.schemas.user import UserProfile
from app.services.llm_service import llm_service
from app.core.database import get_db

class PaperService:
    def __init__(self):
        self.db = get_db()

    def _merge_paper_state(self, paper: dict, state: Optional[dict]) -> PersonalizedPaper:
        """
        辅助方法：将论文元数据与用户状态合并。

        Args:
            paper (dict): 原始论文数据字典。
            state (Optional[dict]): 用户对该论文的状态数据字典 (可能为 None)。

        Returns:
            PersonalizedPaper: 合并后的个性化论文对象。
        """
        # Ensure details is a dict or None
        if paper.get('details') is None:
            paper['details'] = None
            
        # Ensure tags is a dict
        if paper.get('tags') is None:
            paper['tags'] = {}
            
        metadata = PaperMetadata(**paper)
        user_state = UserPaperState(**state) if state else None
        return PersonalizedPaper(**metadata.model_dump(), user_state=user_state)

    def get_papers(self, user_id: str) -> List[PersonalizedPaper]:
        """
        从数据库获取所有论文，并附加指定用户的状态信息。

        Args:
            user_id (str): 用户 ID，用于查询用户特定的论文状态 (如是否已读、评分等)。

        Returns:
            List[PersonalizedPaper]: 包含用户状态的论文列表，按创建时间倒序排列。
                                     如果获取失败，返回空列表。
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
                            "why_this_paper": None,
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
        触发 ArXiv 爬虫并返回最新的论文列表。

        Args:
            user_id (str): 用户 ID，用于获取爬取后的论文列表。
            limit (int, optional): 爬取或返回的论文数量限制 (目前爬虫逻辑可能未完全使用此参数)。默认为 100。

        Returns:
            List[PersonalizedPaper]: 爬取完成后的最新论文列表。
        """
        try:
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=backend_root)
            return self.get_papers(user_id)
        except Exception as e:
            print(f"Error crawling: {e}")
            return self.get_papers(user_id)

    def filter_papers(self, papers: List[PersonalizedPaper], user_profile: UserProfile) -> List[PersonalizedPaper]:
        """
        使用 LLM 批量过滤论文，判断其相关性。

        Args:
            papers (List[PersonalizedPaper]): 待过滤的论文列表。
            user_profile (UserProfile): 用户画像对象。

        Returns:
            List[PersonalizedPaper]: 过滤后的论文列表 (包含更新后的 user_state)。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from app.utils.user_profile_utils import get_user_profile_context
        from app.utils.paper_analysis_utils import analyze_single_paper

        filtered_papers = []
        # 获取用于 Prompt 的画像上下文 (目前是 Mock 数据，user_id 暂传空或从 profile 获取)
        # 注意：这里 user_profile 是 Pydantic 对象，utils 需要的是 dict 或特定结构
        # 根据 utils 定义，get_user_profile_context 返回 dict
        # 但这里传入了 user_profile 对象，我们可以直接用它，或者用 utils 获取
        # 鉴于 utils 封装了 mock 逻辑，我们优先使用 utils
        user_id = user_profile.info.email # 假设 email 作为 ID
        profile_context = get_user_profile_context(user_id)

        print(f"Filtering {len(papers)} papers with LLM (Concurrent)...")

        # 定义并发任务
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_paper = {}
            for p in papers:
                # 如果已经有分析结果且已接受，则跳过 (或者根据需求重新分析)
                # 这里假设如果已有 why_this_paper 则不重复分析
                if p.user_state and p.user_state.why_this_paper:
                    filtered_papers.append(p)
                    continue
                
                # 准备数据
                paper_dict = p.model_dump(exclude={'user_state'})
                future = executor.submit(analyze_single_paper, paper_dict, profile_context)
                future_to_paper[future] = p

            # 处理结果
            for future in as_completed(future_to_paper):
                p = future_to_paper[future]
                try:
                    analysis_result = future.result()
                    
                    # 更新状态数据
                    state_data = {
                        "user_id": user_id,
                        "paper_id": p.id,
                        "relevance_score": analysis_result["relevance_score"],
                        "why_this_paper": analysis_result["why_this_paper"],
                        "accepted": analysis_result["accepted"],
                        # 默认用户行为状态
                        "user_accepted": analysis_result["accepted"], # 默认采纳 LLM 建议
                        "user_liked": None,
                        "user_feedback": None,
                        "created_at": "now()" # Supabase 会自动处理，或者由 Python 生成
                    }

                    # 1. 持久化到数据库 (仅更新状态表)
                    # 注意: created_at 如果数据库有默认值可省略，否则需生成时间字符串
                    # 这里简单处理，移除 created_at 让 DB 处理默认值，或使用 isoformat
                    del state_data["created_at"] 
                    
                    self.db.table("user_paper_states").upsert(state_data).execute()

                    # 2. 更新内存对象
                    p.user_state = UserPaperState(**state_data)
                    
                    # 3. 加入返回列表 (根据需求，是否只返回 accepted? 用户说"依然返回处理后的列表")
                    # 这里我们将所有处理过的都返回，前端决定显示逻辑
                    filtered_papers.append(p)

                except Exception as e:
                    print(f"Error processing paper {p.id}: {e}")
                    # 出错也返回，保持原样
                    filtered_papers.append(p)

        return filtered_papers

    def analyze_paper(self, paper: PersonalizedPaper, user_profile: UserProfile) -> PaperAnalysis:
        """
        使用 LLM 对单篇论文进行深度分析。
        
        如果论文已有详细信息，则直接返回；否则调用 LLM 生成摘要、动机、方法、结果等信息，
        并更新 `papers` 表的元数据和 `user_paper_states` 表的用户状态。

        Args:
            paper (PersonalizedPaper): 需要分析的论文对象。
            user_profile (UserProfile): 用户画像，用于辅助生成个性化的推荐理由。

        Returns:
            PaperAnalysis: 包含分析结果的对象 (摘要、关键点、推荐理由等)。
        """
        # Check if already analyzed (metadata has details)
        if paper.details and paper.details.motivation:
             return PaperAnalysis(
                summary=paper.tldr or "No summary",
                key_points=paper.details,
                recommendation_reason=paper.user_state.why_this_paper if paper.user_state else "Recommended",
                score=paper.user_state.relevance_score if paper.user_state else 0.0,
                accepted=paper.user_state.accepted if paper.user_state else False
            )

        profile_str = json.dumps(user_profile.model_dump(), ensure_ascii=False)
        paper_dict = paper.model_dump(exclude={'user_state'})
        
        analysis = llm_service.analyze_paper(paper_dict, profile_str)
        
        if analysis:
            # 1. Update Public Metadata (papers table)
            current_details = paper.details.model_dump() if paper.details else {}
            update_data = {
                "tldr": analysis.get("tldr", ""),
                "tags": analysis.get("tags", {}), # Default to empty dict
                "details": {
                    **current_details,
                    "motivation": analysis.get("motivation", ""),
                    "method": analysis.get("method", ""),
                    "result": analysis.get("result", ""),
                    "conclusion": analysis.get("conclusion", "")
                }
            }
            try:
                self.db.table("papers").update(update_data).eq("id", paper.id).execute()
            except Exception as e:
                print(f"Error updating paper metadata: {e}")

            # 2. Update User State (user_paper_states table)
            # analyze.md 不再返回 why_this_paper，所以这里不需要更新它，除非我们想保留旧逻辑
            # 但为了安全，我们只在有值时更新
            state_update = {}
            if "why_this_paper" in analysis:
                 state_update["why_this_paper"] = analysis["why_this_paper"]
            
            if state_update:
                try:
                    # We need user_id. Assuming paper.user_state has it.
                    if paper.user_state:
                        self.db.table("user_paper_states").update(state_update).eq("user_id", paper.user_state.user_id).eq("paper_id", paper.id).execute()
                except Exception as e:
                    print(f"Error updating paper state: {e}")
                
            return PaperAnalysis(
                tldr=analysis.get("tldr", ""),
                motivation=analysis.get("motivation", ""),
                method=analysis.get("method", ""),
                result=analysis.get("result", ""),
                conclusion=analysis.get("conclusion", ""),
                tags=analysis.get("tags", {}),
                relevance_score=paper.user_state.relevance_score if paper.user_state else 0.0,
                accepted=paper.user_state.accepted if paper.user_state else False
            )
            
        return PaperAnalysis(
            summary="Analysis failed",
            key_points=PaperDetails(abstract=paper.abstract),
            recommendation_reason="",
            score=0.0,
            accepted=False
        )

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
