from typing import List, Optional
import json
import os
from fastapi import HTTPException
from app.schemas.user import UserProfile, UserInfo, UserFeedback, Focus, Context, Memory
from app.schemas.user import UserInitializationRequest

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
                    "preferences": [],  # 修复：改为空数组
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

    def _migrate_preferences_to_list(self, preferences_value, user_id: str) -> list:
        """
        将 preferences 字段从旧格式（字符串）自动迁移为新格式（列表）
        
        采用渐进式迁移策略：仅在内存中转换，不立即写入数据库。
        用户下次保存时，新格式会自然写入数据库。
        
        Args:
            preferences_value: 从数据库读取的 preferences 值（可能是 str、list 或 None）
            user_id (str): 用户ID，用于日志记录
        
        Returns:
            list: 验证后的 preferences 列表（最多10条，每条最多200字符）
        """
        # 1. 处理 None 或缺失字段
        if preferences_value is None:
            return []
        
        # 2. 已经是列表格式（新版数据）
        if isinstance(preferences_value, list):
            # 进行数据验证和清洗
            # 过滤掉非字符串、空字符串，并截断超长字符串
            validated = [
                pref.strip()[:200]  # 截断到最多200字符
                for pref in preferences_value
                if isinstance(pref, str) and pref.strip()
            ][:10]  # 最多保留10条
            
            return validated
        
        # 3. 旧版字符串格式，需要迁移
        if isinstance(preferences_value, str):
            # 非空字符串，转为单元素列表（不分割，整体保留）
            if preferences_value.strip():
                print(f"[自动迁移] 用户 {user_id} 的 preferences 从字符串转为列表")
                return [preferences_value.strip()[:200]]
            # 空字符串
            else:
                return []
        
        # 4. 其他异常格式（防御性编程）
        print(f"⚠️ 用户 {user_id} 的 preferences 格式异常: {type(preferences_value)}，重置为空列表")
        return []


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
                
                # 迁移 purpose (List) -> preferences (兼容旧版)
                if "preferences" not in context_data and "purpose" in context_data:
                    purpose = context_data.pop("purpose")
                    if isinstance(purpose, list):
                        context_data["preferences"] = ", ".join(purpose)
                    elif isinstance(purpose, str):
                        context_data["preferences"] = purpose
                
                # 新增：自动迁移 preferences 从字符串到列表
                context_data["preferences"] = self._migrate_preferences_to_list(
                    context_data.get("preferences"), 
                    user_id
                )
                
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
                
                # 获取 has_completed_tour 字段（兼容旧数据，默认为 False）
                has_completed_tour = data.get("has_completed_tour", False)
                
                # 获取 remaining_quota 字段（核心：从独立列获取，不再依赖 info JSON）
                remaining_quota = data.get("remaining_quota", 1)
                info_data["remaining_quota"] = remaining_quota
                
                # 获取 receive_email 字段（核心：从独立列获取，不再依赖 info JSON）
                receive_email = data.get("receive_email", False)
                info_data["receive_email"] = receive_email
                
                return UserProfile(
                    info=info_data,
                    focus=focus_data,
                    context=context_data,
                    memory=data.get("memory", {}),
                    has_completed_tour=has_completed_tour
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

    def initialize_profile(self, init_data: "UserInitializationRequest", user_id: str, email: Optional[str] = None) -> UserProfile:
        """
        使用用户提交的基础信息初始化画像。
        
        Args:
            init_data (UserInitializationRequest): 用户提交的完整初始化信息(Info, Focus, Context)。
            user_id (str): 当前认证用户的 ID。
            email (Optional[str]): 当前认证用户的邮箱。

        Returns:
            UserProfile: 更新后的完整用户画像。
        """
        try:
            # 1. 检查 Profile 是否存在
            response = self.db.table("profiles").select("*").eq("user_id", user_id).execute()
            
            # 2. 如果不存在，创建新 Profile
            if not response.data:
                # 使用传入的 email，如果未提供则尝试从 user_info 获取，最后回退到默认
                user_email = email or init_data.info.email or DEFAULT_EMAIL
                temp_name = user_email.split('@')[0] if '@' in user_email else "User"
                
                empty_profile = {
                    "user_id": user_id,
                    "info": {
                        "id": user_id,
                        "name": temp_name,
                        "email": user_email,
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
                        "preferences": [],  # 修复：改为空数组
                        "currentTask": "",
                        "futureGoal": ""
                    },
                    "memory": {
                        "user_prompt": []
                    },
                    "remaining_quota": 1 # 新用户初始赠送 1 个额度
                }
                self.db.table("profiles").insert(empty_profile).execute()
            
            # 3. 更新画像数据
            # 确保 info 中包含正确的 id
            init_data.info.id = user_id
            if email and not init_data.info.email:
                init_data.info.email = email
            
            # 更新数据库 (Info, Focus, Context)
            # 核心：从 info 中移除已提升为独立列的字段，避免冗余
            info_to_save = init_data.info.model_dump()
            remaining_quota = info_to_save.pop("remaining_quota", 1)
            receive_email = info_to_save.pop("receive_email", False)

            self.db.table("profiles").update({
                "info": info_to_save,
                "focus": init_data.focus.model_dump(),
                "context": init_data.context.model_dump(),
                "remaining_quota": remaining_quota,
                "receive_email": receive_email
            }).eq("user_id", user_id).execute()
            
            return self.get_profile(user_id)
        except Exception as e:
            print(f"Error initializing profile: {e}")
            # 如果出错，尝试返回默认画像，但记录错误
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
            # 核心：如果更新了 info，从中移除冗余字段并同步到独立列
            if 'info' in updates:
                info_to_save = updates['info']
                # 提取并移除冗余字段
                if 'remaining_quota' in info_to_save:
                    updates['remaining_quota'] = info_to_save.pop('remaining_quota')
                if 'receive_email' in info_to_save:
                    updates['receive_email'] = info_to_save.pop('receive_email')
                updates['info'] = info_to_save

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
            return True
        except Exception as e:
            print(f"Error recording interaction: {e}")
            return False

    def get_all_active_users(self) -> List[str]:
        """
        获取所有活跃用户的 ID。
        
        Returns:
            List[str]: 用户 ID 列表。
        """
        try:
            # 简单起见，获取所有 profile
            response = self.db.table("profiles").select("user_id").execute()
            return [row["user_id"] for row in response.data]
        except Exception as e:
            print(f"Error fetching all users: {e}")
            return []
    
    def mark_tour_completed(self, user_id: str) -> bool:
        """
        标记用户已完成产品引导教程。
        
        此功能用于新用户首次登录后的引导流程。完成引导后，用户下次登录将不再显示引导气泡。
        
        Args:
            user_id (str): 用户的唯一标识符。
        
        Returns:
            bool: 操作是否成功。True 表示成功标记，False 表示操作失败。
        """
        try:
            print(f"[引导完成] 正在标记用户 {user_id} 已完成引导教程")
            
            # 更新 profiles 表中的 has_completed_tour 字段
            self.db.table("profiles").update({
                "has_completed_tour": True
            }).eq("user_id", user_id).execute()
            
            print(f"✅ 用户 {user_id} 引导状态已更新")
            return True
            
        except Exception as e:
            print(f"❌ 标记引导完成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_remaining_quota(self, user_id: str) -> int:
        """
        获取用户的剩余额度。

        Args:
            user_id (str): 用户的唯一标识符。

        Returns:
            int: 剩余额度数量。
        """
        try:
            response = self.db.table("profiles").select("remaining_quota").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0].get("remaining_quota", 0)
            return 0
        except Exception as e:
            print(f"❌ 获取额度失败: {e}")
            return 0

    def has_sufficient_quota(self, user_id: str, required: int = 1) -> bool:
        """
        检查用户额度是否充足。

        Args:
            user_id (str): 用户的唯一标识符。
            required (int): 所需的额度数量，默认为 1。

        Returns:
            bool: True 表示充足，False 表示不足。
        """
        current_quota = self.get_remaining_quota(user_id)
        return current_quota >= required

    def _update_quota_and_log(self, user_id: str, new_quota: int, change_amount: int, reason: str, related_report_id: Optional[str] = None) -> bool:
        """
        [内部方法] 更新额度并记录日志。
        
        Args:
            user_id (str): 用户 ID
            new_quota (int): 新的额度值
            change_amount (int): 变动数量（正数增加，负数减少）
            reason (str): 变动原因
            related_report_id (Optional[str]): 关联报告 ID
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # TODO: 高并发场景下存在竞态条件。
            # 建议未来迁移到 Supabase RPC (PostgreSQL存储过程) 以实现原子更新。
            # 示例: self.db.rpc('update_quota', {'uid': user_id, 'delta': change_amount}).execute()
            
            # 1. 更新额度
            self.db.table("profiles").update({
                "remaining_quota": new_quota
            }).eq("user_id", user_id).execute()
            
            # 2. 记录日志
            self.db.table("quota_logs").insert({
                "user_id": user_id,
                "change_amount": change_amount,
                "reason": reason,
                "related_report_id": related_report_id
            }).execute()
            
            return True
        except Exception as e:
            print(f"❌ 更新额度数据库失败: {e}")
            return False

    def deduct_quota(self, user_id: str, amount: int = 1, reason: str = "report_generated", report_id: Optional[str] = None) -> bool:
        """
        扣减用户额度，并记录日志。

        Args:
            user_id (str): 用户的唯一标识符。
            amount (int): 扣减的额度数量，默认为 1。
            reason (str): 扣减原因，默认为 'report_generated'。
            report_id (Optional[str]): 关联的报告 ID。

        Returns:
            bool: 是否扣减成功。
        """
        try:
            # 1. 获取当前额度
            current = self.get_remaining_quota(user_id)
            if current < amount:
                print(f"⚠️ 用户 {user_id} 额度不足: 当前 {current}, 需要 {amount}")
                return False
            
            # 2. 计算新额度
            new_quota = current - amount
            
            # 3. 执行更新
            if self._update_quota_and_log(user_id, new_quota, -amount, reason, report_id):
                print(f"✅ 用户 {user_id} 额度扣减成功: {current} -> {new_quota} (原因: {reason})")
                return True
            return False
            
        except Exception as e:
            print(f"❌ 扣减额度流程失败: {e}")
            return False

    def add_quota(self, user_id: str, amount: int, reason: str = "recharge") -> bool:
        """
        增加用户额度（如充值或系统赠送），并记录日志。

        Args:
            user_id (str): 用户的唯一标识符。
            amount (int): 增加的额度数量。
            reason (str): 增加原因，默认为 'recharge'。

        Returns:
            bool: 是否增加成功。
        """
        try:
            # 1. 获取当前额度
            current = self.get_remaining_quota(user_id)
            
            # 2. 计算新额度
            new_quota = current + amount
            
            # 3. 执行更新
            if self._update_quota_and_log(user_id, new_quota, amount, reason):
                print(f"✅ 用户 {user_id} 额度增加成功: {current} -> {new_quota} (原因: {reason})")
                return True
            return False
            
        except Exception as e:
            print(f"❌ 增加额度流程失败: {e}")
            return False

user_service = UserService()
