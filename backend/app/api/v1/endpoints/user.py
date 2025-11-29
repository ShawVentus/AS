from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas.user import UserProfile, Focus, UserInfo, Context, Memory, UserFeedback

router = APIRouter()

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(user_id: str = Depends(get_current_user_id)):
    """获取当前用户画像"""
    from app.services.user_service import user_service
    return user_service.get_profile(user_id)

@router.put("/me/focus", response_model=Focus)
def update_user_focus(focus: Focus, user_id: str = Depends(get_current_user_id)):
    """更新用户关注领域"""
    db = get_db()
    
    # 更新 focus 字段
    db.table("profiles").update({"focus": focus.dict()}).eq("user_id", user_id).execute()
    
    return focus

@router.put("/me/info", response_model=UserInfo)
def update_user_info(info: UserInfo, user_id: str = Depends(get_current_user_id)):
    """更新用户信息"""
    db = get_db()
    
    db.table("profiles").update({"info": info.dict()}).eq("user_id", user_id).execute()
    
    return info

@router.put("/me", response_model=UserProfile)
def update_current_user_profile(profile_data: dict, user_id: str = Depends(get_current_user_id)):
    """
    更新当前用户画像 (通用接口)。
    接受 info, focus, context 的部分更新。
    """
    from app.services.user_service import user_service
    return user_service.update_profile(user_id, profile_data)

@router.post("/me/nl", response_model=UserProfile)
def update_profile_nl(payload: dict, user_id: str = Depends(get_current_user_id)):
    """
    [Placeholder] 通过自然语言更新画像。
    目前仅为占位符，实际逻辑待实现。
    """
    # TODO: Implement LLM integration
    text = payload.get("text", "")
    from app.services.user_service import user_service
    # 暂时直接返回当前画像，不进行修改
    return user_service.get_profile(user_id)

@router.get("/me/check-initialization")
def check_user_initialization(user_id: str = Depends(get_current_user_id)):
    """
    检查用户是否已完成初始化
    
    Returns:
        dict: {"initialized": bool}
    """
    from app.services.user_service import user_service
    is_initialized = user_service.is_profile_initialized(user_id)
    return {"initialized": is_initialized}

@router.post("/me/interaction")
def record_user_interaction(feedback: UserFeedback, user_id: str = Depends(get_current_user_id)):
    """
    记录用户交互 (Read/Like/Dislike)
    """
    from app.services.user_service import user_service
    success = user_service.record_interaction(user_id, feedback)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to record interaction")
    return {"status": "success"}
