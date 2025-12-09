from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class Report(BaseModel):
    """
    报告数据模型
    
    主要功能：
    定义报告的数据结构，包括基本信息、引用论文列表以及统计数据。
    """
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    user_id: Optional[str] = None
    title: str
    date: str
    summary: str
    content: str
    ref_papers: List[str] = Field(alias='refPapers')
    
    # 统计字段
    total_papers_count: int = Field(default=0, alias='totalPapersCount')
    recommended_papers_count: int = Field(default=0, alias='recommendedPapersCount')

class ReportFeedback(BaseModel):
    """
    报告反馈模型
    
    主要功能：
    定义用户对报告的反馈数据结构。
    """
    id: Optional[str] = None
    report_id: str
    user_id: str
    rating: int
    feedback_text: Optional[str] = None
    created_at: Optional[str] = None
