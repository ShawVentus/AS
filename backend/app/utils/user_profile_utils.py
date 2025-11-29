from typing import Dict, Any
from fastapi import HTTPException

# 延迟导入以避免循环依赖
# user_service 在函数中导入，但进行缓存优化
_user_service_cache = None

def _get_user_service():
    """获取 user_service 实例（带缓存）"""
    global _user_service_cache
    if _user_service_cache is None:
        from app.services.user_service import user_service
        _user_service_cache = user_service
    return _user_service_cache

def get_user_profile_context(user_id: str) -> Dict[str, Any]:
    """
    获取用于 LLM 上下文的用户画像信息。
    
    Args:
        user_id (str): 用户 ID。

    Returns:
        Dict[str, Any]: 用户画像字典，包含 focus, context 等关键字段。
        
    Raises:
        HTTPException: 如果用户画像不存在或获取失败
    """
    user_service = _get_user_service()
    
    try:
        profile = user_service.get_profile(user_id)
        return {
            "focus": profile.focus.model_dump(),
            "context": profile.context.model_dump()
        }
    except HTTPException as e:
        # 重新抛出，让调用方处理
        raise e
    except Exception as e:
        print(f"Error getting profile context for LLM: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve user context for AI analysis"
        )
