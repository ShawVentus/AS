from typing import List, Optional
from pydantic import BaseModel

class UserInfo(BaseModel):
    """用户信息模型"""
    name: str
    email: str
    avatar: str
    nickname: str

class Focus(BaseModel):
    """用户关注领域模型"""
    domains: List[str]
    keywords: List[str]
    authors: List[str]
    institutions: List[str]

class Context(BaseModel):
    """用户上下文模型"""
    currentTask: str
    futureGoal: str
    stage: str
    purpose: List[str]

class Memory(BaseModel):
    """用户记忆模型"""
    readPapers: List[str]
    dislikedPapers: List[str]

class UserProfile(BaseModel):
    """用户画像总模型"""
    info: UserInfo
    focus: Focus
    context: Context
    memory: Memory

class UserFeedback(BaseModel):
    """用户反馈模型"""
    paper_id: str
    is_like: bool
    reason: Optional[str] = None

class NaturalLanguageInput(BaseModel):
    """自然语言输入模型"""
    text: str
    user_id: str
