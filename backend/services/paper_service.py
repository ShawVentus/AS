from typing import List, Optional
import json
import subprocess
import os
from schemas.paper import Paper, PaperAnalysis
from schemas.user import UserProfile
from services.mock_data import MOCK_PAPERS
from services.llm_service import llm_service
from database import get_db

class PaperService:
    def __init__(self):
        self.db = get_db()

    def get_papers(self) -> List[Paper]:
        """从数据库获取所有论文"""
        try:
            response = self.db.table("papers").select("*").order("created_at", desc=True).limit(50).execute()
            if response.data:
                papers = []
                for p in response.data:
                    try:
                        papers.append(Paper(**p))
                    except Exception as validation_error:
                        print(f"⚠️ Skipping invalid paper {p.get('id')}: {validation_error}")
                return papers
            return []
        except Exception as e:
            print(f"Error fetching papers: {e}")
            return []

    def crawl_arxiv_new(self, limit: int = 100) -> List[Paper]:
        """
        触发ArXiv爬虫并返回新论文
        """
        try:
            # 同步运行爬虫以响应API请求(可能较慢,但对于MVP的"获取"按钮来说可以接受)
            # 或者我们可以在触发后台任务后直接返回当前论文。
            # 现在,让我们尝试运行它然后获取。
            cwd = os.path.join(os.path.dirname(os.path.dirname(__file__)))
            subprocess.run(["scrapy", "crawl", "arxiv"], check=True, cwd=cwd)
            
            # 获取最新论文
            return self.get_papers()
        except Exception as e:
            print(f"Error crawling: {e}")
            return self.get_papers() # 出错时返回现有论文

    def filter_papers(self, papers: List[Paper], user_profile: UserProfile) -> List[Paper]:
        """
        使用LLM过滤论文
        Args:
            papers: 原始论文列表
            user_profile: 用户画像
        Returns:
            List[Paper]: 筛选后的高相关度论文列表
        TODO:
            1. 粗筛: 基于 Focus 关键词的文本匹配。
            2. 精筛: 调用 LLM (DeepSeek Chat) 判断 Abstract 与 User Context 的相关性。
            3. 为每篇通过筛选的论文打上 `relevance_score`。
        # 模拟：目前返回所有论文
        """
        # 实现LLM过滤
        filtered = []
        profile_str = json.dumps(user_profile.model_dump(), ensure_ascii=False)
        
        print(f"Filtering {len(papers)} papers with LLM...")
        for p in papers:
            # 跳过已经过滤/分析过的论文以节省token
            if p.suggestion and (p.suggestion.startswith("Not Relevant") or p.suggestion.startswith("Recommended")):
                if not p.suggestion.startswith("Not Relevant"):
                    filtered.append(p)
                continue

            # 调用LLM
            print(f"Checking relevance for: {p.title[:30]}...")
            result = llm_service.filter_paper(p.model_dump(), profile_str)
            
            if result.get("is_relevant", False):
                filtered.append(p)
                # 如果需要,更新数据库中的评分/原因,或者现在先保留它
                # 我们可以暂时将原因存储在suggestion中
                try:
                    self.db.table("papers").update({
                        "suggestion": f"Recommended: {result.get('reason', 'Relevant')}"
                    }).eq("id", p.id).execute()
                except Exception as e:
                    print(f"Error updating paper {p.id}: {e}")
            else:
                # 标记为不相关
                try:
                    self.db.table("papers").update({
                        "suggestion": f"Not Relevant: {result.get('reason', 'Irrelevant')}",
                        "tldr": "N/A"
                    }).eq("id", p.id).execute()
                except Exception as e:
                    print(f"Error updating paper {p.id}: {e}")
                    
        return filtered

    def analyze_paper(self, paper: Paper, user_profile: UserProfile) -> PaperAnalysis:
        """
        使用LLM分析单篇论文
        """
        # 检查数据库中是否已经分析过
        if paper.details and paper.details.motivation:
             return PaperAnalysis(
                summary=paper.tldr or "No summary",
                key_points=paper.details,
                recommendation_reason=paper.suggestion or "Recommended",
                score=0.9 # 占位符
            )

        # 如果没有,调用LLM
        profile_str = json.dumps(user_profile.model_dump(), ensure_ascii=False)
        paper_dict = paper.model_dump()
        
        analysis = llm_service.analyze_paper(paper_dict, profile_str)
        
        # 更新数据库
        if analysis:
            update_data = {
                "tldr": analysis.get("tldr", ""),
                "suggestion": analysis.get("why_this_paper", ""),
                "tags": analysis.get("tags", []),
                "details": {
                    **paper.details.model_dump(),
                    "motivation": analysis.get("motivation", ""),
                    "method": analysis.get("method", ""),
                    "result": analysis.get("result", ""),
                    "conclusion": analysis.get("conclusion", "")
                }
            }
            try:
                self.db.table("papers").update(update_data).eq("id", paper.id).execute()
            except Exception as e:
                print(f"Error updating paper analysis: {e}")
                
            return PaperAnalysis(
                summary=analysis.get("tldr", ""),
                key_points=update_data["details"],
                recommendation_reason=analysis.get("why_this_paper", ""),
                score=0.9
            )
            
        return PaperAnalysis(
            summary="Analysis failed",
            key_points={},
            recommendation_reason="",
            score=0.0
        )

    def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        try:
            response = self.db.table("papers").select("*").eq("id", paper_id).execute()
            if response.data:
                return Paper(**response.data[0])
            return None
        except Exception as e:
            print(f"Error fetching paper {paper_id}: {e}")
            return None

    def get_recommendations(self) -> List[Paper]:
        """获取推荐论文(相关的论文)"""
        try:
            # 过滤suggestion不是"Not Relevant"的论文
            # Supabase过滤器: not.ilike.suggestion.%Not Relevant%
            # 或者对于MVP版本,就在Python中获取所有并过滤
            response = self.db.table("papers").select("*").order("created_at", desc=True).limit(50).execute()
            if response.data:
                papers = [Paper(**p) for p in response.data]
                # 简单过滤
                return [p for p in papers if not (p.suggestion and p.suggestion.startswith("Not Relevant"))]
            return []
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []

paper_service = PaperService()
