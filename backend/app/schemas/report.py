from typing import List
from pydantic import BaseModel, Field, ConfigDict

class Report(BaseModel):
    """研读报告模型"""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str
    title: str
    date: str
    summary: str
    content: str  # 修改: List[ReportContent] -> str (markdown 字符串)
    ref_papers: List[str] = Field(alias='refPapers')  # 新增: 引用的论文 ID 列表

