from typing import List, Optional
from pydantic import BaseModel

class UserInfo(BaseModel):
    """用户信息模型"""
    id: Optional[str] = None # 初始化的时候自动生成
    name: str = "" 
    email: str
    avatar: str = "" # 头像，初始化时根据name自动生成

class Focus(BaseModel):
    """用户关注模型"""
    category: List[str] = [] # 用于到 arxiv 检索的类别
    keywords: List[str] = []
    authors: List[str] = []
    institutions: List[str] = []

class Context(BaseModel):
    """用户状态模型"""
    preferences: str = "" # 为什么要使用本app，研读论文为了什么，必须填写
    currentTask: str = "" # 目前正在做的事情
    futureGoal: str = "" # 未来目的

class UserFeedback(BaseModel):
    """用户反馈模型"""
    paper_id: str
    action_type: str # read, like, dislike
    reason: Optional[str] = None
    timestamp: Optional[str] = None # ISO format string

class Memory(BaseModel):
    """用户记忆模型，存储用户的交互记录"""
    user_prompt: List[str] = [] # 存储用户历史给到的需求更新指令
    interactions: List[UserFeedback] = [] # 存储用户论文交互记录

class UserProfile(BaseModel):
    """用户画像总模型"""
    info: UserInfo
    focus: Focus
    context: Context
    memory: Memory

class NaturalLanguageInput(BaseModel):
    """自然语言输入模型"""
    text: str
    user_id: str
