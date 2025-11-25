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
    pdf: str
    arxiv: str
    html: str

class DislikeReason(BaseModel):
    """不感兴趣原因模型"""
    reason: str
    tags: List[str]

class RawPaperMetadata(BaseModel):
    """爬虫原始输出模型（不包含 LLM 生成内容）"""
    id: str
    title: str
    authors: List[str]
    published_date: str
    category: List[str]  # 保持为列表，插入数据库时取第一个作为主分类
    abstract: str
    links: PaperLinks
    comment: Optional[str] = None

# --- 核心模型 ---

class PaperMetadata(BaseModel):
    """
    论文公共元数据 (PaperMetadata)
    对应数据库 `papers` 表。
    存储论文的客观事实（爬虫获取）和通用的 AI 分析结果。
    所有用户共享。
    """
    # --- 基础信息 (Stage 1: Crawler) ---
    id: str
    title: str
    authors: List[str]
    published_date: str # 对应数据库 date 字段
    category: List[str] # 对应数据库 category 字段 (可能是字符串或数组，需注意兼容)
    abstract: str  # [MOVED] 移至基础信息，因为是爬虫获取的原始内容
    links: PaperLinks
    comment: Optional[str] = None # 备注，如获奖信息
    
    # --- 通用分析 (Stage 2: AI Analysis) ---
    tags: Dict[str, str] = {} # 通用标签 (AI 提取) - key: tag name, value: content/url
    details: Optional[PaperDetails] = None # 包含 motivation, method 等

    # --- 预留字段 ---
    # citationCount: int = 0 # 预留，目前暂不启用

    @field_validator('category', mode='before')
    @classmethod
    def parse_category(cls, v):
        if isinstance(v, str):
            return [v]
        return v

class UserPaperState(BaseModel):
    """
    用户个性化状态 (UserPaperState)
    对应数据库 `user_paper_states` 表。
    存储用户与论文的交互状态。
    每个用户独有。
    """
    paper_id: str
    user_id: str
    
    # --- 推荐引擎生成 (LLM) ---
    why_this_paper: str # 针对该用户的推荐理由，必须要有
    relevance_score: float = 0.0 # 0.0 ~ 1.0
    accepted: bool # LLM 建议是否接受

    # --- 用户交互状态 (User Action) ---
    user_accepted: bool = False # [RENAMED] 用户最终决定是否"接受" (生成报告用)
    user_liked: Optional[bool] = None # [RENAMED] Like (True) / Dislike (False) / None
    user_feedback: Optional[str] = None # [RENAMED] 用户反馈的具体原因

class PersonalizedPaper(PaperMetadata):
    """
    个性化论文 (API 响应模型)
    前端展示用的组合模型，包含所有信息。
    每个用户个性化信息的私有管理类
    避免数据污染、前端逻辑清晰
    """
    user_state: Optional[UserPaperState] = None

class PaperAnalysis(BaseModel):
    """论文深度分析模型 (用于 LLM 返回结果)"""
    # analyze.md 返回的其他字段需映射到 PaperDetails 或 PaperMetadata
    tldr: str
    motivation: str
    method: str
    result: str
    conclusion: str
    tags: Dict[str, str]

class PaperFilter(BaseModel):
    """论文筛选模型 (用于 LLM 返回结果)"""
    why_this_paper: str # 针对该用户的推荐理由
    relevance_score: float # 0.0 ~ 1.0
    accepted: bool # LLM 建议是否接受