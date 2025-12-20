from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas.user import UserProfile, Focus, UserInfo, Context, Memory, UserFeedback, UserInitializationRequest

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
@router.post("/initialize", response_model=UserProfile)
def initialize_user_profile(
    init_data: UserInitializationRequest, 
    user_id: str = Depends(get_current_user_id)
):
    """
    初始化用户画像。
    如果用户不存在，会创建新用户。
    接收完整的初始化数据 (Info, Focus, Context)。
    """
    from app.services.user_service import user_service
    # 注意：这里我们无法直接从 get_current_user_id 获取 email，
    # 实际场景中应该从 JWT token claims 中解析 email，或者再次调用 auth API 获取。
    # 暂时我们在 init_data.info 中信任前端传来的 email，或者由 service 层处理默认值。
    return user_service.initialize_profile(init_data, user_id)

@router.patch("/me/complete-tour")
def complete_user_tour(user_id: str = Depends(get_current_user_id)):
    """
    标记用户已完成产品引导教程。
    
    该接口用于新用户首次使用时的引导流程。当用户完成或跳过引导后调用，
    确保下次登录时不再显示引导气泡。
    
    Args:
        user_id (str): 当前认证用户的ID（通过依赖注入自动获取）
    
    Returns:
        dict: 操作结果 {"success": bool, "message": str}
    """
    from app.services.user_service import user_service
    
    success = user_service.mark_tour_completed(user_id)
    
    if success:
        return {"success": True, "message": "已成功标记引导完成"}
    else:
        raise HTTPException(
            status_code=500, 
            detail="标记引导完成失败，请稍后重试"
        )


# ===================== 玻尔平台用户初始化（新） =====================

@router.post("/init-from-bohrium")
async def init_user_from_bohrium(request: Request):
    """
    通过玻尔平台 accessKey 初始化用户。
    
    此接口用于用户首次访问时自动创建/获取用户信息。
    前端应在应用启动时调用此接口初始化用户状态。
    
    处理流程：
    1. 从 Cookie 读取 appAccessKey
    2. 调用玻尔 SDK 获取用户信息（user_id, name）
    3. 检查 profiles 表中是否存在该用户
       - 存在 → 返回现有用户信息
       - 不存在 → 创建新用户（赠送 1 次额度）
    4. 返回完整的 UserProfile
    
    Args:
        request: FastAPI Request 对象（用于读取 Cookie）
    
    Returns:
        UserProfile: 用户画像对象
    
    Raises:
        HTTPException 401: accessKey 无效或缺失
        HTTPException 500: 服务器内部错误
    """
    from app.services.bohrium_service import get_access_key_or_default
    from app.services.payment_service import ensure_user_exists
    from app.services.user_service import user_service
    
    try:
        # 1. 获取 accessKey 和 appKey
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        app_key = request.cookies.get("clientName")  # 玻尔平台设置的 appKey
        
        # 2. 确保用户存在（不存在则创建）
        user_info = await ensure_user_exists(access_key, app_key)
        
        # 3. 返回完整的用户画像
        return user_service.get_profile(user_info.user_id)
        
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail="未登录或登录已过期，请刷新页面"
        )
    except Exception as e:
        print(f"❌ [用户初始化] 失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"用户初始化失败: {str(e)}"
        )
