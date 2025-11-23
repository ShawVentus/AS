from typing import List, Optional
import json
from schemas.user import UserProfile, UserInfo, UserFeedback, Focus, Context, Memory
from services.mock_data import USER_PROFILE
from database import get_db

# MVP的硬编码用户邮箱(单用户模式)
DEFAULT_EMAIL = "student@uni.edu.cn"

class UserService:
    def __init__(self):
        self.db = get_db()

    def _get_user_id(self, email: str) -> Optional[str]:
        """从邮箱获取user_id的辅助方法"""
        try:
            response = self.db.table("users").select("id").eq("email", email).execute()
            if response.data:
                return response.data[0]["id"]
            return None
        except Exception as e:
            print(f"Error getting user ID: {e}")
            return None

    def _create_default_user(self) -> str:
        """如果不存在则创建默认用户"""
        try:
            # 检查是否存在
            user_id = self._get_user_id(DEFAULT_EMAIL)
            if user_id:
                return user_id
            
            # 创建用户
            user_data = {"email": DEFAULT_EMAIL}
            response = self.db.table("users").insert(user_data).execute()
            user_id = response.data[0]["id"]
            
            # 使用模拟数据创建初始画像
            profile_data = {
                "user_id": user_id,
                "info": USER_PROFILE["info"],
                "focus": USER_PROFILE["focus"],
                "context": USER_PROFILE["context"],
                "memory": USER_PROFILE["memory"]
            }
            self.db.table("profiles").insert(profile_data).execute()
            return user_id
        except Exception as e:
            print(f"Error creating default user: {e}")
            raise e

    def get_profile(self) -> UserProfile:
        """从数据库获取用户画像"""
        try:
            user_id = self._get_user_id(DEFAULT_EMAIL)
            if not user_id:
                # 如果数据库中没有用户,从模拟数据创建默认用户
                user_id = self._create_default_user()
            
            response = self.db.table("profiles").select("*").eq("user_id", user_id).execute()
            if response.data:
                data = response.data[0]
                return UserProfile(
                    info=data["info"],
                    focus=data["focus"],
                    context=data["context"],
                    memory=data["memory"]
                )
            else:
                # 如果画像缺失则退回模拟数据(由于_create_default_user不应该发生)
                return UserProfile(**USER_PROFILE)
        except Exception as e:
            print(f"Error fetching profile: {e}")
            # 出错时退回模拟数据以保持应用运行
            return UserProfile(**USER_PROFILE)

    def initialize_profile(self, user_info: UserInfo) -> UserProfile:
        """
        初始化用户画像
        Args:
            user_info: 用户提交的基础问卷信息
        Returns:
            UserProfile: 初始化的完整用户画像
        """
        try:
            # 确保用户存在
            user_id = self._create_default_user()
            
            # 更新画像中的info部分
            # 注意:在实际应用中,我们可能根据输入生成默认的Focus/Context
            # 现在我们只更新info部分
            
            # 获取当前画像以合并
            current_profile = self.get_profile()
            current_profile.info = user_info
            
            # 更新数据库
            self.db.table("profiles").update({
                "info": user_info.model_dump()
            }).eq("user_id", user_id).execute()
            
            return current_profile
        except Exception as e:
            print(f"Error initializing profile: {e}")
            return UserProfile(**USER_PROFILE)

    def update_profile_nl(self, user_id: str, feedback_text: str) -> UserProfile:
        """
        根据自然语言反馈更新画像
        Args:
            user_id: 用户ID (ignored in MVP, using DEFAULT_EMAIL)
            feedback_text: 用户的自然语言输入
        Returns:
            UserProfile: 更新后的用户画像
        TODO:
            1. 调用 LLM (Qwen) 提取 feedback_text 中的实体和意图。
            2. 更新 Focus (添加新关键词) 和 Context (调整短期关注点)。
            3. 记录此次交互到 Memory。
        """
        # 获取当前画像
        profile = self.get_profile()
        
        # 模拟实现:模拟从文本中添加关键词
        # 简单的模拟逻辑:如果文本包含"LLM",就将它添加到关键词中
        updated = False
        if "LLM" in feedback_text and "LLM" not in profile.focus.keywords:
            profile.focus.keywords.append("LLM")
            updated = True
            
        if updated:
            # 持久化到数据库
            uid = self._get_user_id(DEFAULT_EMAIL)
            if uid:
                self.db.table("profiles").update({
                    "focus": profile.focus.model_dump()
                }).eq("user_id", uid).execute()
                
        return profile

    def update_profile_from_selection(self, user_id: str, feedbacks: List[UserFeedback]) -> UserProfile:
        """
        根据行为反馈更新画像
        Args:
            user_id: 用户ID
            feedbacks: 用户对一组论文的反馈列表
        Returns:
            UserProfile: 更新后的用户画像
        TODO:
            1. 分析 Dislike 的论文，提取负面特征，更新 Memory 中的"屏蔽词/不感兴趣领域"。
            2. 分析 Like 的论文，强化 Focus 中的相关权重。
        """
        # 获取当前画像
        
        # 更新记忆
        updated = False
        for fb in feedbacks:
            if fb.is_like:
                if fb.paper_id not in profile.memory.readPapers:
                    profile.memory.readPapers.append(fb.paper_id)
                    updated = True
            else:
                if fb.paper_id not in profile.memory.dislikedPapers:
                    profile.memory.dislikedPapers.append(fb.paper_id)
                    updated = True
                    
        if updated:
             # 持久化到数据库
            uid = self._get_user_id(DEFAULT_EMAIL)
            if uid:
                self.db.table("profiles").update({
                    "memory": profile.memory.model_dump()
                }).eq("user_id", uid).execute()

        return profile

    def update_profile(self, profile_data: dict) -> UserProfile:
        """通用更新方法"""
        # 获取当前画像
        profile = self.get_profile()
        
        # 更新字段
        if 'info' in profile_data:
            # 深度更新info
            current_info = profile.info.model_dump()
            current_info.update(profile_data['info'])
            profile.info = UserInfo(**current_info)
            
        # 持久化到数据库
        uid = self._get_user_id(DEFAULT_EMAIL)
        if uid:
            self.db.table("profiles").update({
                "info": profile.info.model_dump()
            }).eq("user_id", uid).execute()
            
        return profile

user_service = UserService()
