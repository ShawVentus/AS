import os
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import supabase

# 开发模式配置
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
DEV_USER_ID = os.getenv("DEV_USER_ID", "6z023dyl")

# 定义 Bearer Token 模式（开发模式下可选）
security = HTTPBearer(auto_error=not DEV_MODE)

def get_current_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    验证用户身份并返回 user_id
    
    开发模式：直接返回环境变量中的固定 user_id
    生产模式：验证 Supabase JWT 并返回 user_id
    """
    # 开发模式：跳过验证，使用固定 user_id
    if DEV_MODE:
        print(f"[Auth] 🔧 开发模式：使用固定 user_id = {DEV_USER_ID}")
        return DEV_USER_ID
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭证",
        )
    
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


# ===================== 玻尔平台认证（新） =====================

async def get_bohrium_user_id(request: Request) -> str:
    """
    从 Cookie 获取玻尔平台用户 ID。
    
    此函数是支付系统的核心认证机制，通过以下流程获取用户身份：
    1. 从 Cookie 读取 appAccessKey（玻尔平台自动种植）
    2. 调用玻尔 SDK 获取用户信息
    3. 确保用户存在于 profiles 表中
    4. 返回用户 ID（如 '6z023dyl'）
    
    Args:
        request: FastAPI Request 对象（用于读取 Cookie）
    
    Returns:
        str: 玻尔平台用户 ID
    
    Raises:
        HTTPException 401: accessKey 无效或缺失
    """
    from app.services.bohrium_service import get_user_info, get_access_key_or_default
    from app.services.payment_service import ensure_user_exists
    
    try:
        # 1. 获取 accessKey
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        
        # 2. 获取用户信息并确保用户存在
        user_info = await ensure_user_exists(access_key)
        
        return user_info.user_id
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期，请刷新页面"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )


def get_bohrium_user_id_sync(request: Request) -> str:
    """
    同步版本的玻尔平台用户 ID 获取。
    
    用于不支持 async 的接口。直接从 Cookie 获取 accessKey 并调用玻尔 SDK。
    
    Args:
        request: FastAPI Request 对象
    
    Returns:
        str: 玻尔平台用户 ID
    
    Raises:
        HTTPException 401: accessKey 无效或缺失
    """
    from app.services.bohrium_service import get_user_info, get_access_key_or_default
    
    try:
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        user_info = get_user_info(access_key)
        return user_info.user_id
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或登录已过期，请刷新页面"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"认证失败: {str(e)}"
        )
