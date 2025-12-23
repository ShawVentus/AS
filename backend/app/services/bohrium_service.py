"""
玻尔平台服务封装模块

功能说明：
  封装与玻尔平台（Bohrium）的所有交互，包括用户信息获取和积分消费。
  所有外部 API 调用都在此模块中处理，确保业务层代码与第三方 SDK 解耦。

主要功能：
  1. get_user_info() - 通过 accessKey 获取玻尔用户信息
  2. consume_integral() - 调用玻尔积分消费接口

依赖：
  - bohrium-open-sdk: 玻尔平台官方 SDK
  - httpx: 异步 HTTP 客户端
"""

import os
import time
import random
from typing import Optional
from dataclasses import dataclass

import httpx
from bohrium_open_sdk import OpenSDK


# ===================== 数据模型 =====================

@dataclass
class BohriumUserInfo:
    """
    玻尔平台用户信息数据类。
    
    Attributes:
        user_id: 用户唯一标识（如 '6z023dyl'），用于本系统的 profiles 表主键
        name: 用户显示名称
        bohr_user_id: 玻尔平台内部用户 ID（数字）
        org_id: 用户所属组织 ID
    """
    user_id: str
    name: str
    bohr_user_id: int
    org_id: int


@dataclass
class ConsumeResult:
    """
    积分消费结果数据类。
    
    Attributes:
        success: 是否消费成功
        biz_no: 本地生成的业务流水号
        out_biz_no: 玻尔平台返回的交易流水号（成功时有值）
        request_id: 玻尔平台返回的请求 ID（成功时有值）
        error: 错误信息（失败时有值）
    """
    success: bool
    biz_no: int
    out_biz_no: Optional[str] = None
    request_id: Optional[int] = None
    error: Optional[str] = None


# ===================== 配置常量 =====================

from app.core.config import settings

# 玻尔平台 API 端点
BOHRIUM_API_BASE = "https://openapi.dp.tech"
BOHRIUM_CONSUME_URL = f"{BOHRIUM_API_BASE}/openapi/v1/api/integral/consume"

# 商品 SKU ID（从配置获取）
BOHRIUM_SKU_ID = settings.BOHRIUM_SKU_ID

# 开发模式配置
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
DEV_ACCESS_KEY = os.getenv("DEV_BOHRIUM_ACCESS_KEY", "")

# ===================== 缓存配置 =====================
# accessKey -> { user_id, client_name, expires_at } 缓存，避免重复调用玻尔 API
CACHE_TTL = 300  # 缓存过期时间：5 分钟
_user_cache: dict = {}  # 内存缓存：{ accessKey: { "user_id": str, "client_name": str, "expires_at": float } }



# ===================== 核心功能函数 =====================

def get_user_info(access_key: str, app_key: Optional[str] = None) -> BohriumUserInfo:
    """
    通过玻尔平台 accessKey 获取用户信息。
    
    此函数调用玻尔 SDK 获取用户详细信息，用于：
    1. 用户首次访问时创建 profile 记录
    2. 验证用户身份后获取 user_id
    
    Args:
        access_key: 玻尔平台 accessKey（从 Cookie appAccessKey 获取）
        app_key: 玻尔平台 appKey（从 Cookie clientName 获取），必须传入才能正确调用 SDK
    
    Returns:
        BohriumUserInfo: 包含 user_id, name 等字段的用户信息对象
    
    Raises:
        ValueError: accessKey 为空
        RuntimeError: 玻尔 SDK 返回错误或网络异常
    
    Example:
        >>> user_info = get_user_info("sk-xxx", "arxivscout-uuid123")
        >>> print(user_info.user_id)  # '6z023dyl'
        >>> print(user_info.name)     # 'Ventus Shaw'
    """
    if not access_key:
        raise ValueError("accessKey 不能为空")
    
    try:
        # 根据玻尔官方文档，必须同时传入 access_key 和 app_key
        client = OpenSDK(access_key=access_key, app_key=app_key)
        result = client.user.get_info()
        
        # 检查返回结果
        if result.get("code") != 0:
            error_msg = result.get("message", "未知错误")
            raise RuntimeError(f"玻尔平台返回错误: {error_msg}")
        
        data = result.get("data", {})
        
        return BohriumUserInfo(
            user_id=data.get("user_id", ""),
            name=data.get("name", ""),
            bohr_user_id=data.get("bohr_user_id", 0),
            org_id=data.get("org_id", 0)
        )
    
    except Exception as e:
        # 统一包装异常，便于上层处理
        if isinstance(e, (ValueError, RuntimeError)):
            raise
        raise RuntimeError(f"获取玻尔用户信息失败: {str(e)}")


def generate_biz_no() -> int:
    """
    生成14位唯一业务流水号。
    
    格式: 10位时间戳 + 4位随机数
    用于玻尔扣费接口的 bizNo 参数，确保每次调用唯一。
    
    Returns:
        int: 14位整数业务流水号
    
    Example:
        >>> biz_no = generate_biz_no()
        >>> print(biz_no)  # 17348234561234
    """
    timestamp = int(time.time())
    rand_part = random.randint(1000, 9999)
    return int(f"{timestamp}{rand_part}")


async def consume_integral(access_key: str, event_value: int, client_name: str) -> ConsumeResult:
    """
    调用玻尔平台积分消费接口。
    
    此函数是异步的，使用 httpx 发送请求，避免阻塞主线程。
    
    Args:
        access_key: 用户的玻尔平台 accessKey（从 Cookie appAccessKey 获取）
        event_value: 消费的光子数量（100/400/1200）
        client_name: 用户标识（从 Cookie clientName 获取），用于 x-app-key header。
                     此参数必须提供，不能为空。
    
    Returns:
        ConsumeResult: 消费结果数据类，包含以下字段：
            - success (bool): 是否消费成功
            - biz_no (int): 本地生成的业务流水号
            - out_biz_no (str): 玻尔平台返回的交易流水号（成功时有值）
            - request_id (int): 玻尔平台返回的请求 ID（成功时有值）
            - error (str): 错误信息（失败时有值）
    
    Raises:
        ValueError: client_name 为空
    
    Example:
        >>> result = await consume_integral("sk-xxx", 100, "user123")
        >>> if result.success:
        >>>     print(f"扣费成功，流水号: {result.out_biz_no}")
        >>> else:
        >>>     print(f"扣费失败: {result.error}")
    """
    # 【修复】client_name 是用户标识，必须从 Cookie 获取，不能为空
    if not client_name:
        raise ValueError("clientName 不能为空，请确保从玻尔平台访问")
    
    biz_no = generate_biz_no()
    
    headers = {
        "accessKey": access_key,
        "x-app-key": client_name,  # 用户标识
        "Content-Type": "application/json"
    }
    
    print(f"[支付] 调用玻尔扣费接口: accessKey={access_key[:8]}..., x-app-key={client_name}, eventValue={event_value}")
    
    payload = {
        "bizNo": biz_no,
        "changeType": 1,
        "eventValue": event_value,
        "skuId": BOHRIUM_SKU_ID,
        "scene": "appCustomizeCharge"
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                BOHRIUM_CONSUME_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
        
        # 检查业务返回码
        if result.get("code") == 0:
            data = result.get("data", {})
            return ConsumeResult(
                success=True,
                biz_no=biz_no,
                out_biz_no=data.get("outBizNo"),
                request_id=data.get("requestId")
            )
        else:
            # 业务错误（如余额不足）
            error_msg = result.get("message", "扣费失败")
            return ConsumeResult(
                success=False,
                biz_no=biz_no,
                error=error_msg
            )
    
    except httpx.TimeoutException:
        return ConsumeResult(
            success=False,
            biz_no=biz_no,
            error="请求超时，请稍后重试"
        )
    
    except httpx.HTTPStatusError as e:
        return ConsumeResult(
            success=False,
            biz_no=biz_no,
            error=f"HTTP 错误: {e.response.status_code}"
        )
    
    except Exception as e:
        return ConsumeResult(
            success=False,
            biz_no=biz_no,
            error=f"扣费失败: {str(e)}"
        )


def get_access_key_or_default(access_key: Optional[str]) -> str:
    """
    获取有效的 accessKey，开发模式下可回退使用默认值。
    
    安全说明：
        仅当 DEV_MODE=true 且配置了 DEV_BOHRIUM_ACCESS_KEY 时才会回退。
        生产环境（DEV_MODE=false）下必须从 Cookie 获取 accessKey。
    
    Args:
        access_key: 从 Cookie 获取的 accessKey（可能为空）
    
    Returns:
        str: 有效的 accessKey
    
    Raises:
        ValueError: 无法获取有效的 accessKey
    """
    # 情况 1: Cookie 中有有效的 accessKey
    if access_key:
        return access_key
    
    # 情况 2: 开发模式下回退使用环境变量
    # 🔒 安全修复：必须同时满足 DEV_MODE=true 且有配置
    if DEV_MODE and DEV_ACCESS_KEY:
        print("[开发模式] 使用环境变量中的默认 accessKey")
        return DEV_ACCESS_KEY
    
    # 情况 3: 无法获取 accessKey
    raise ValueError("未找到有效的 accessKey，请确保从玻尔平台访问")


# ===================== 缓存功能函数 =====================

def get_user_id_cached(access_key: str, client_name: Optional[str] = None) -> str:
    """
    通过 accessKey 获取 user_id，带内存缓存。
    
    此函数用于后端认证，避免每次请求都调用玻尔 API。
    缓存 TTL 为 5 分钟，过期后自动重新获取。
    同时会缓存 client_name（用户标识），供后续扣费使用。
    
    Args:
        access_key: 玻尔平台 accessKey（从 Cookie appAccessKey 获取）
        client_name: 用户标识（从 Cookie clientName 获取），首次调用时必须提供
    
    Returns:
        str: 用户 ID（如 '6z023dyl'）
    
    Raises:
        ValueError: accessKey 为空
        RuntimeError: 玻尔 API 调用失败
    """
    global _user_cache
    
    if not access_key:
        raise ValueError("accessKey 不能为空")
    
    current_time = time.time()
    
    # 检查缓存
    if access_key in _user_cache:
        cached = _user_cache[access_key]
        if cached["expires_at"] > current_time:
            print(f"[缓存命中] user_id = {cached['user_id']}, client_name = {cached.get('client_name', 'N/A')}")
            return cached["user_id"]
        else:
            # 缓存过期，删除
            del _user_cache[access_key]
    
    # 缓存未命中，调用玻尔 API
    print("[缓存未命中] 调用玻尔 API 获取用户信息...")
    user_info = get_user_info(access_key, client_name)
    
    # 存入缓存（包含 client_name）
    _user_cache[access_key] = {
        "user_id": user_info.user_id,
        "client_name": client_name,  # 同时缓存 client_name
        "expires_at": current_time + CACHE_TTL
    }
    
    print(f"[缓存已更新] user_id = {user_info.user_id}, client_name = {client_name}, TTL = {CACHE_TTL}秒")
    return user_info.user_id


def get_client_name_cached(access_key: str) -> Optional[str]:
    """
    从缓存获取 client_name（用户标识）。
    
    用于需要 client_name 但没有直接从 Cookie 获取的场景（如扣费接口）。
    
    Args:
        access_key: 玻尔平台 accessKey
    
    Returns:
        Optional[str]: 缓存的 client_name，若缓存不存在或已过期则返回 None
    """
    if not access_key or access_key not in _user_cache:
        return None
    
    cached = _user_cache[access_key]
    current_time = time.time()
    
    if cached["expires_at"] > current_time:
        return cached.get("client_name")
    
    return None


def clear_user_cache(access_key: Optional[str] = None) -> None:
    """
    清除用户缓存。
    
    Args:
        access_key: 指定要清除的 accessKey，为 None 则清除全部缓存
    
    Returns:
        None
    """
    global _user_cache
    
    if access_key:
        if access_key in _user_cache:
            del _user_cache[access_key]
            print(f"[缓存已清除] accessKey = {access_key[:8]}...")
    else:
        _user_cache.clear()
        print("[缓存已全部清除]")

