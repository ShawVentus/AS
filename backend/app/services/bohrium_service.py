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

# 玻尔平台 API 端点
BOHRIUM_API_BASE = "https://openapi.dp.tech"
BOHRIUM_CONSUME_URL = f"{BOHRIUM_API_BASE}/openapi/v1/api/integral/consume"

# 应用标识（固定值）
BOHRIUM_CLIENT_NAME = os.getenv("BOHRIUM_CLIENT_NAME", "arxivscout")

# 商品 SKU ID（固定值）
BOHRIUM_SKU_ID = int(os.getenv("BOHRIUM_SKU_ID", "10020"))

# 开发环境默认 accessKey
DEV_ACCESS_KEY = os.getenv("DEV_BOHRIUM_ACCESS_KEY", "")


# ===================== 核心功能函数 =====================

def get_user_info(access_key: str) -> BohriumUserInfo:
    """
    通过玻尔平台 accessKey 获取用户信息。
    
    此函数调用玻尔 SDK 获取用户详细信息，用于：
    1. 用户首次访问时创建 profile 记录
    2. 验证用户身份后获取 user_id
    
    Args:
        access_key: 玻尔平台 accessKey（从 Cookie 或环境变量获取）
    
    Returns:
        BohriumUserInfo: 包含 user_id, name 等字段的用户信息对象
    
    Raises:
        ValueError: accessKey 为空
        RuntimeError: 玻尔 SDK 返回错误或网络异常
    
    Example:
        >>> user_info = get_user_info("4c97924ea86e4b40b9cf091dcfd20e44")
        >>> print(user_info.user_id)  # '6z023dyl'
        >>> print(user_info.name)     # 'Ventus Shaw'
    """
    if not access_key:
        raise ValueError("accessKey 不能为空")
    
    try:
        client = OpenSDK(access_key=access_key)
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


async def consume_integral(access_key: str, event_value: int) -> ConsumeResult:
    """
    调用玻尔平台积分消费接口。
    
    此函数是异步的，使用 httpx 发送请求，避免阻塞主线程。
    
    Args:
        access_key: 用户的玻尔平台 accessKey
        event_value: 消费的光子数量（100/400/1200）
    
    Returns:
        ConsumeResult: 消费结果，包含成功/失败状态和相关流水号
    
    Example:
        >>> result = await consume_integral("xxx", 100)
        >>> if result.success:
        >>>     print(f"扣费成功，流水号: {result.out_biz_no}")
        >>> else:
        >>>     print(f"扣费失败: {result.error}")
    """
    biz_no = generate_biz_no()
    
    headers = {
        "accessKey": access_key,
        "x-app-key": BOHRIUM_CLIENT_NAME,
        "Content-Type": "application/json"
    }
    
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
    获取有效的 accessKey，如果为空则使用开发环境默认值。
    
    Args:
        access_key: 从 Cookie 获取的 accessKey（可能为空）
    
    Returns:
        str: 有效的 accessKey
    
    Raises:
        ValueError: 无法获取有效的 accessKey
    """
    if access_key:
        return access_key
    
    if DEV_ACCESS_KEY:
        print("[开发模式] 使用环境变量中的默认 accessKey")
        return DEV_ACCESS_KEY
    
    raise ValueError("未找到有效的 accessKey")
