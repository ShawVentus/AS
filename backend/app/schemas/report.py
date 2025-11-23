from typing import List
from pydantic import BaseModel

class ReportContent(BaseModel):
    """报告内容段落模型"""
    text: str
    refIds: List[str]

class Report(BaseModel):
    """研读报告模型"""
    id: str
    title: str
    date: str
    summary: str
    content: List[ReportContent]
