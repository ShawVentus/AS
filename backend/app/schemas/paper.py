from typing import List, Optional, Dict
from pydantic import BaseModel, field_validator

# --- 基础组件 ---

class PaperDetails(BaseModel):
    """论文详细信息模型 (深度分析)"""
    tldr: Optional[str] = None
    motivation: Optional[str] = None
    method: Optional[str] = None
    result: Optional[str] = None
    conclusion: Optional[str] = None

class PaperLinks(BaseModel):
    """论文链接模型"""
    pdf: Optional[str] = None
    arxiv: Optional[str] = None
    html: Optional[str] = None

class DislikeReason(BaseModel):
    """不感兴趣原因模型"""
    reason: str
    tags: List[str]

class RawPaperMetadata(BaseModel):
    """
    爬虫原始输出模型 (Meta)
    包含论文的客观事实，不包含 AI 分析结果。
    """
    id: str
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    published_date: Optional[str] = None
    category: List[str]  # 存储所有分类
    abstract: Optional[str] = None
    links: Optional[PaperLinks] = None
    comment: Optional[str] = None

    @field_validator('category', mode='before')
    @classmethod
    def parse_category(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class PaperAnalysis(BaseModel):
    """
    论文深度分析模型 (Analysis)
    包含 LLM 生成的所有分析字段。
    """
    tldr: Optional[str] = None
    motivation: Optional[str] = None
    method: Optional[str] = None
    result: Optional[str] = None
    conclusion: Optional[str] = None
    tags: Dict[str, str] = {}

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, list):
            return {} 
        if v is None:
            return {}
        return v

class UserPaperState(BaseModel):
    """用户个性化状态"""
    paper_id: str
    user_id: str # 用于确保仅对应用户可以访问
    
    # --- 推荐引擎生成 (LLM) ---
    why_this_paper: str # 针对该用户的推荐理由，必须要有
    relevance_score: float = 0.0 # 0.0 ~ 1.0
    accepted: bool # LLM 建议是否接受

    # --- 用户交互状态 (User Action) ---
    user_liked: Optional[bool] = None # Like (True) / Dislike (False) / None
    user_feedback: Optional[str] = None # 用户反馈的具体原因

class PersonalizedPaper(BaseModel):
    """
    个性化论文 (API 响应模型)
    结构化分离 Meta, Analysis 和 UserState。
    """
    meta: RawPaperMetadata
    analysis: Optional[PaperAnalysis] = None
    user_state: Optional[UserPaperState] = None

class PaperFilter(BaseModel):
    """论文筛选模型"""
    why_this_paper: str
    relevance_score: float
    accepted: bool

class FilterResultItem(BaseModel):
    """单篇论文的筛选结果 (API 响应子项)"""
    paper_id: str
    why_this_paper: str
    relevance_score: float
    accepted: bool

class FilterResponse(BaseModel):
    """filter_papers 的返回结构"""
    user_id: str
    created_at: str          # 任务处理时间
    total_analyzed: int      # 总分析论文数
    accepted_count: int      # 接受论文数
    rejected_count: int      # 拒绝论文数
    selected_papers: List[FilterResultItem] # 接受的论文 (按相关性排序)
    rejected_papers: List[FilterResultItem] # 拒绝的论文 (按相关性排序)

# Deprecated but kept for compatibility if needed, or remove
class PaperMetadata(BaseModel):
    pass

class PaperFeedbackRequest(BaseModel):
    """用户反馈请求模型"""
    liked: Optional[bool] = None
    feedback: Optional[str] = None
