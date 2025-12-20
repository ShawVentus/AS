"""
认证模块

功能说明：
    提供后端 API 的用户身份认证功能。
    所有需要用户身份的接口都通过此模块获取 user_id。

认证方式：
    - 生产模式：从 Cookie 获取玻尔平台 accessKey → 调用玻尔 SDK 获取 user_id
    - 开发模式：直接使用环境变量中的 DEV_USER_ID

主要函数：
    - get_current_user_id(): 必须登录的接口使用
    - get_current_user_id_optional(): 可选登录的接口使用
"""

import os
from typing import Optional
from fastapi import HTTPException, status, Request

# ===================== 配置常量 =====================

# 开发模式配置
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
DEV_USER_ID = os.getenv("DEV_USER_ID", "6z023dyl")


# ===================== 核心认证函数 =====================

def get_current_user_id(request: Request) -> str:
    """
    获取当前用户 ID（必须登录）。
    
    此函数是所有需要用户身份的 API 接口的依赖注入函数。
    通过以下流程获取用户身份：
    
    开发模式 (DEV_MODE=true):
        直接返回环境变量 DEV_USER_ID
    
    生产模式 (DEV_MODE=false):
        1. 从 Cookie 读取 appAccessKey
        2. 调用 get_user_id_cached() 获取 user_id（带缓存）
        3. 返回 user_id
    
    Args:
        request: FastAPI Request 对象（用于读取 Cookie）
    
    Returns:
        str: 用户 ID（如 '6z023dyl'）
    
    Raises:
        HTTPException 401: 未登录或认证失败
    """
    # 开发模式：直接返回固定 user_id
    if DEV_MODE:
        print(f"[Auth] 🔧 开发模式：使用固定 user_id = {DEV_USER_ID}")
        return DEV_USER_ID
    
    # 生产模式：从 Cookie 获取 accessKey 和 appKey
    from app.services.bohrium_service import get_user_id_cached, get_access_key_or_default
    
    try:
        # 1. 获取 accessKey 和 appKey
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        app_key = request.cookies.get("clientName")  # 玻尔平台设置的 appKey
        
        # 2. 获取 user_id（带缓存）
        user_id = get_user_id_cached(access_key, app_key)
        
        return user_id
        
    except ValueError as e:
        # accessKey 无效或缺失
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="获取您的信息失败，请刷新重试"
        )
    except Exception as e:
        # 其他错误（网络、玻尔 API 等）
        print(f"[Auth] ❌ 认证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="获取您的信息失败，请刷新重试"
        )


def get_current_user_id_optional(request: Request) -> Optional[str]:
    """
    获取当前用户 ID（可选登录）。
    
    与 get_current_user_id() 类似，但认证失败时返回 None 而不是抛出异常。
    用于不强制要求登录的接口（如公开论文详情页）。
    
    Args:
        request: FastAPI Request 对象
    
    Returns:
        Optional[str]: 用户 ID，未登录时返回 None
    """
    try:
        return get_current_user_id(request)
    except HTTPException:
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
        # 1. 获取 accessKey 和 appKey
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        app_key = request.cookies.get("clientName")  # 玻尔平台设置的 appKey
        
        # 2. 获取用户信息并确保用户存在
        user_info = await ensure_user_exists(access_key, app_key)
        
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
        app_key = request.cookies.get("clientName")  # 玻尔平台设置的 appKey
        user_info = get_user_info(access_key, app_key)
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
