from typing import List, Optional, Dict
from pydantic import BaseModel

class PaperDetails(BaseModel):
    """论文详细信息模型"""
    motivation: Optional[str] = None
    method: Optional[str] = None
    result: Optional[str] = None
    conclusion: Optional[str] = None
    abstract: str
    tldr: Optional[str] = None

class PaperLinks(BaseModel):
    """论文链接模型"""
    pdf: str
    arxiv: str
    html: str

class DislikeReason(BaseModel):
    """不感兴趣原因模型"""
    reason: str
    tags: List[str]

class Paper(BaseModel):
    """论文核心模型"""
    id: str
    title: str
    authors: List[str]
    date: str
    category: str
    tldr: Optional[str] = None
    suggestion: Optional[str] = None
    tags: List[str] = []
    details: PaperDetails
    links: PaperLinks
    citationCount: int
    year: Optional[int] = None
    isLiked: Optional[bool] = None
    whyThisPaper: Optional[str] = None

class PaperAnalysis(BaseModel):
    """论文深度分析模型"""
    summary: str
    key_points: PaperDetails
    recommendation_reason: str
    score: float
