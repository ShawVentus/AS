from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import supabase

# 定义 Bearer Token 模式
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    验证 Supabase JWT 并返回 user_id
    """
    token = credentials.credentials
    try:
        # 调用 Supabase Auth API 验证 Token
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return user.user.id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )

def get_current_user_id_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """
    可选的验证 Supabase JWT。如果验证成功返回 user_id，否则返回 None。
    不会抛出 401 异常。
    """
    if not credentials:
        return None
        
    token = credentials.credentials
    try:
        user = supabase.auth.get_user(token)
        if not user:
            return None
        return user.user.id
    except Exception:
        return None
