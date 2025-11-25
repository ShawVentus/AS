from typing import Dict, Any
from app.services.mock_data import USER_PROFILE

def get_user_profile_context(user_id: str) -> Dict[str, Any]:
    """
    获取用于 LLM 上下文的用户画像信息。
    
    Args:
        user_id (str): 用户 ID。

    Returns:
        Dict[str, Any]: 用户画像字典，包含 focus, context 等关键字段。
    """
    # 目前使用 Mock 数据，后续可替换为数据库查询
    # 模拟根据 user_id 获取画像，这里直接返回默认的 USER_PROFILE
    return {
        "focus": USER_PROFILE["focus"],
        "context": USER_PROFILE["context"]
    }
