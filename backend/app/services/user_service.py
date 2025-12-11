from typing import List, Optional
import json
import os
from fastapi import HTTPException
from app.schemas.user import UserProfile, UserInfo, UserFeedback, Focus, Context, Memory
from app.services.mock_data import USER_PROFILE
from app.core.database import get_db

# MVP的硬编码用户邮箱(单用户模式)
DEFAULT_EMAIL = USER_PROFILE["info"]["email"]

class UserService:
    def __init__(self):
        self.db = get_db()

    def _get_user_id(self, email: str) -> Optional[str]:
        """
        根据邮箱获取用户 ID (从 profiles 表查询)。

        Args:
            email (str): 用户的电子邮件地址。

        Returns:
            Optional[str]: 用户的唯一 ID (UUID)。如果未找到用户，返回 None。
        """
        try:
            # 直接查 profiles 表中的 info->>email
            # Supabase JSONB query syntax: info->>email
            response = self.db.table("profiles").select("user_id").eq("info->>email", email).execute()
            if response.data:
                return response.data[0]["user_id"]
            return None
        except Exception as e:
            print(f"Error getting user ID: {e}")
            return None

    def _create_default_user(self) -> str:
        """
        检查并创建默认用户 (如果不存在)。
        
        用于 MVP 阶段的单用户模式。如果用户不存在，会创建用户记录并初始化空白画像。

        Args:
            None

        Returns:
            str: 默认用户的 ID。
        """
        try:
            # 检查是否存在
            user_id = self._get_user_id(DEFAULT_EMAIL)
            if user_id:
                return user_id
            
            # 创建用户 (仅在 Profiles 表中创建)
            # 生成一个固定的 UUID 或者随机 UUID
            import uuid
            user_id = str(uuid.uuid4())
            
            # 创建空白画像（让前端 Onboarding 填充）
            # 使用邮箱前缀作为临时名称，避免空字符串导致 Avatar 组件问题
            temp_name = DEFAULT_EMAIL.split('@')[0] if '@' in DEFAULT_EMAIL else "User"
            empty_profile = {
                "user_id": user_id,
                "info": {
                    "id": user_id,
                    "name": temp_name,
                    "email": DEFAULT_EMAIL,
                    "avatar": "",
                    "role": "researcher"
                },
                "focus": {
                    "category": [],
                    "keywords": [],
                    "authors": [],
                    "institutions": []
                },
                "context": {
                    "preferences": "",
                    "currentTask": "",
                    "futureGoal": ""
                },
                "memory": {
                    "user_prompt": []
                }
            }
            self.db.table("profiles").insert(empty_profile).execute()
            return user_id
        except Exception as e:
            print(f"Error creating default user: {e}")
            raise e

    def get_profile(self, user_id: Optional[str] = None) -> UserProfile:
        """
        获取当前用户的完整画像。
        
        如果提供了 user_id，则直接查询该用户的画像。
        如果未提供，则尝试使用默认用户（兼容旧逻辑）。

        Args:
            user_id (Optional[str]): 用户 ID。

        Returns:
            UserProfile: 用户画像对象。
        """
        try:
            if not user_id:
                user_id = self._get_user_id(DEFAULT_EMAIL)
                if not user_id:
                    # 如果数据库中没有用户,从模拟数据创建默认用户
                    user_id = self._create_default_user()
            
            response = self.db.table("profiles").select("*").eq("user_id", user_id).execute()
            if response.data:
                data = response.data[0]
                
                # --- 数据迁移与清洗逻辑 ---
                
                # 1. 清洗 Context
                context_data = data.get("context", {})
                # 迁移 purpose (List) -> preferences (str)
                if "preferences" not in context_data and "purpose" in context_data:
                    purpose = context_data.pop("purpose")
                    if isinstance(purpose, list):
                        context_data["preferences"] = ", ".join(purpose)
                    elif isinstance(purpose, str):
                        context_data["preferences"] = purpose
                
                # 确保必需字段存在 (Pydantic 会处理默认值，但为了安全起见)
                # stage 和 learningMode 已被移除，无需处理

                # 2. 清洗 Focus
                focus_data = data.get("focus", {})
                # 迁移 domains -> category
                if "category" not in focus_data and "domains" in focus_data:
                    focus_data["category"] = focus_data.pop("domains")
                
                # --- 构造对象 ---
                info_data = data.get("info", {})
                # [Fix] 确保 info 中包含 id，如果 JSON 中没有，从 user_id 列注入
                if not info_data.get("id"):
                    info_data["id"] = user_id
                
                return UserProfile(
                    info=info_data,
                    focus=focus_data,
                    context=context_data,
                    memory=data.get("memory", {})
                )
            else:
                # 数据库中没有该用户的 profile
                use_mock = os.getenv("USE_MOCK_FALLBACK", "false").lower() == "true"
                if use_mock:
                    print(f"Warning: Profile not found for user_id {user_id}, using mock data (USE_MOCK_FALLBACK=true).")
                    return UserProfile(**USER_PROFILE)
                else:
                    # 生产模式：抛出异常，让上层决定如何处理
                    raise HTTPException(
                        status_code=404,
                        detail="User profile not initialized. Please complete onboarding."
                    )
        except HTTPException as http_err:
            # 重新抛出 HTTP 异常（如 404）
            raise http_err
        except Exception as e:
            print(f"Error fetching profile: {e}")
            import traceback
            traceback.print_exc()
            
            use_mock = os.getenv("USE_MOCK_FALLBACK", "false").lower() == "true"
            if use_mock:
                print("Using mock data due to error (USE_MOCK_FALLBACK=true)")
                return UserProfile(**USER_PROFILE)
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve user profile due to server error: {str(e)}"
                )

    def initialize_profile(self, user_info: UserInfo) -> UserProfile:
        """
        使用用户提交的基础信息初始化画像。
        
        通常在用户首次设置时调用。会更新数据库中的 info 字段。

        Args:
            user_info (UserInfo): 用户提交的基础问卷信息。

        Returns:
            UserProfile: 更新后的完整用户画像。
        """
        try:
            # 确保用户存在
            user_id = self._create_default_user()
            
            # 更新画像中的info部分
            # 注意:在实际应用中,我们可能根据输入生成默认的Focus/Context
            # 现在我们只更新info部分
            
            # 确保 info 中包含 id
            user_info.id = user_id
            
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

    def is_profile_initialized(self, user_id: str) -> bool:
        """
        判断用户是否已完成初始化。
        
        Args:
            user_id (str): 用户 ID
            
        Returns:
            bool: True 表示已初始化，False 表示需要初始化
        """
        try:
            profile = self.get_profile(user_id)
            # 如果 category 为空列表或不存在，则需要初始化
            return bool(profile.focus.category)
        except Exception as e:
            print(f"Error checking initialization status: {e}")
            return False

    def update_profile_nl(self, user_id: str, feedback_text: str) -> UserProfile:
        """
        根据自然语言反馈更新用户画像。

        Args:
            user_id (str): 用户 ID (MVP 阶段可能忽略，使用默认用户)。
            feedback_text (str): 用户的自然语言输入 (例如 "我对 LLM 感兴趣")。

        Returns:
            UserProfile: 更新后的用户画像。

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
        根据用户的显式行为反馈 (Like/Dislike) 更新画像。

        Args:
            user_id (str): 用户 ID。
            feedbacks (List[UserFeedback]): 用户对一组论文的反馈列表。

        Returns:
            UserProfile: 更新后的用户画像。

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

    def update_profile(self, user_id: str, profile_data: dict) -> UserProfile:
        """
        更新用户画像。
        
        Args:
            user_id (str): 用户 ID。
            profile_data (dict): 包含要更新字段的字典 (info, focus, context)。

        Returns:
            UserProfile: 更新后的完整用户画像。
        """
        # 获取当前画像 (确保存在)
        current_profile = self.get_profile(user_id)
        
        updates = {}
        
        # 更新 Info
        if 'info' in profile_data:
            current_info = current_profile.info.dict()
            current_info.update(profile_data['info'])
            updates['info'] = current_info
            
        # 更新 Focus
        if 'focus' in profile_data:
            current_focus = current_profile.focus.dict()
            current_focus.update(profile_data['focus'])
            updates['focus'] = current_focus
            
        # 更新 Context
        if 'context' in profile_data:
            current_context = current_profile.context.dict()
            current_context.update(profile_data['context'])
            updates['context'] = current_context

        if updates:
            self.db.table("profiles").update(updates).eq("user_id", user_id).execute()
            
        return self.get_profile(user_id)

    def record_interaction(self, user_id: str, feedback: UserFeedback) -> bool:
        """
        记录用户与论文的交互 (Read/Like/Dislike)。
        
        Args:
            user_id (str): 用户 ID。
            feedback (UserFeedback): 反馈对象。
            
        Returns:
            bool: 是否成功记录。
        """
        try:
            # 获取当前画像
            profile = self.get_profile(user_id)
            
            # 添加到 interactions 列表
            # 简单的追加逻辑，实际应用可能需要去重或更新
            profile.memory.interactions.append(feedback)
            
            # 持久化到数据库
            self.db.table("profiles").update({
                "memory": profile.memory.model_dump()
            }).eq("user_id", user_id).execute()
            
            return True
        except Exception as e:
            print(f"Error recording interaction: {e}")
            return False

user_service = UserService()
