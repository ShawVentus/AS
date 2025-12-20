"""
支付服务模块

功能说明：
  处理用户购买研报次数的完整业务流程，包括：
  1. 调用玻尔平台扣费接口
  2. 记录交易流水到数据库
  3. 更新用户次数余额

主要功能：
  - process_purchase() - 完整购买流程处理
  - record_transaction() - 记录交易到数据库
  - increase_user_quota() - 增加用户次数余额

设计原则：
  - 事务完整性：扣费成功后才更新数据库
  - 幂等性：bizNo 唯一约束防止重复扣款
  - 可回溯：完整记录交易和额度变动日志
"""

from typing import Optional
from dataclasses import dataclass

from app.core.database import get_db
from app.services.bohrium_service import (
    consume_integral,
    get_user_info,
    get_access_key_or_default,
    BohriumUserInfo,
    ConsumeResult
)


# ===================== 数据模型 =====================

@dataclass
class PurchaseResult:
    """
    购买结果数据类。
    
    Attributes:
        success: 是否购买成功
        message: 结果消息（成功/失败提示）
        out_biz_no: 玻尔平台交易流水号（成功时有值）
        request_id: 玻尔平台请求 ID（成功时有值）
        new_quota: 购买后的新余额（成功时有值）
    """
    success: bool
    message: str
    out_biz_no: Optional[str] = None
    request_id: Optional[int] = None
    new_quota: Optional[int] = None


# ===================== 价格档位配置 =====================

PRICE_TIERS = {
    100: {"quota": 1, "name": "单次生成"},
    400: {"quota": 5, "name": "购买一周研报"},
    1200: {"quota": 20, "name": "购买一月研报"},
}


# ===================== 核心业务函数 =====================

async def process_purchase(
    user_id: str,
    access_key: str,
    event_value: int,
    quota_amount: int,
    app_key: str = None  # 【修复】新增：用户的客户端标识（从 Cookie clientName 获取）
) -> PurchaseResult:
    """
    处理完整的购买流程。
    
    流程步骤：
    1. 验证参数有效性
    2. 调用玻尔平台扣费接口
    3. 扣费成功后记录交易
    4. 更新用户次数余额
    5. 返回购买结果
    
    Args:
        user_id: 用户 ID（来自玻尔平台）
        access_key: 用户的 accessKey
        event_value: 消费的光子数量（100/400/1200）
        quota_amount: 购买的次数（1/5/20）
    
    Returns:
        PurchaseResult: 包含成功状态、消息和相关数据
    
    Example:
        >>> result = await process_purchase('6z023dyl', 'xxx', 400, 5)
        >>> if result.success:
        >>>     print(f"购买成功，新余额: {result.new_quota}")
    """
    # 1. 验证价格档位
    if event_value not in PRICE_TIERS:
        return PurchaseResult(
            success=False,
            message=f"无效的价格档位: {event_value}"
        )
    
    expected_quota = PRICE_TIERS[event_value]["quota"]
    if quota_amount != expected_quota:
        return PurchaseResult(
            success=False,
            message=f"次数与价格不匹配: {event_value}光子应获得{expected_quota}次"
        )
    
    # 2. 调用玻尔扣费接口（【修复】传入 app_key 参数）
    consume_result = await consume_integral(access_key, event_value, app_key)
    
    if not consume_result.success:
        return PurchaseResult(
            success=False,
            message=consume_result.error or "扣费失败"
        )
    
    # 3. 扣费成功，记录交易
    try:
        record_transaction(
            user_id=user_id,
            biz_no=consume_result.biz_no,
            out_biz_no=consume_result.out_biz_no,
            request_id=consume_result.request_id,
            event_value=event_value,
            quota_amount=quota_amount,
            status="success"
        )
    except Exception as e:
        # 记录交易失败不影响用户体验，但需要告警
        print(f"⚠️ [支付] 记录交易失败: {e}")
    
    # 4. 增加用户次数余额
    try:
        new_quota = increase_user_quota(user_id, quota_amount)
    except Exception as e:
        # 额度更新失败是严重问题，需要记录并人工介入
        print(f"❌ [支付] 更新用户额度失败: {e}")
        return PurchaseResult(
            success=False,
            message="扣费成功但更新额度失败，请联系客服"
        )
    
    # 5. 返回成功结果
    tier_name = PRICE_TIERS[event_value]["name"]
    return PurchaseResult(
        success=True,
        message=f"购买成功，已获得 {quota_amount} 次生成额度",
        out_biz_no=consume_result.out_biz_no,
        request_id=consume_result.request_id,
        new_quota=new_quota
    )


def record_transaction(
    user_id: str,
    biz_no: int,
    out_biz_no: Optional[str],
    request_id: Optional[int],
    event_value: int,
    quota_amount: int,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """
    记录交易到 payment_transactions 表。
    
    Args:
        user_id: 用户 ID
        biz_no: 本地生成的业务流水号
        out_biz_no: 玻尔平台交易流水号
        request_id: 玻尔平台请求 ID
        event_value: 消费的光子数量
        quota_amount: 购买的次数
        status: 交易状态（success/failed）
        error_message: 失败原因（可选）
    """
    db = get_db()
    
    db.table("payment_transactions").insert({
        "user_id": user_id,
        "biz_no": biz_no,
        "out_biz_no": out_biz_no,
        "request_id": request_id,
        "event_value": event_value,
        "quota_amount": quota_amount,
        "status": status,
        "error_message": error_message
    }).execute()
    
    print(f"✅ [支付] 交易记录已保存: user={user_id}, biz_no={biz_no}, status={status}")


def increase_user_quota(user_id: str, amount: int) -> int:
    """
    增加用户次数余额。
    
    此函数会：
    1. 获取当前余额
    2. 计算新余额
    3. 更新 profiles 表
    4. 记录变动日志到 quota_logs 表
    
    Args:
        user_id: 用户 ID
        amount: 增加的次数
    
    Returns:
        int: 更新后的新余额
    
    Raises:
        Exception: 数据库操作失败
    """
    db = get_db()
    
    # 1. 获取当前余额
    response = db.table("profiles").select("remaining_quota").eq("user_id", user_id).execute()
    
    if not response.data:
        raise Exception(f"用户不存在: {user_id}")
    
    current_quota = response.data[0].get("remaining_quota", 0)
    new_quota = current_quota + amount
    
    # 2. 更新余额
    db.table("profiles").update({
        "remaining_quota": new_quota
    }).eq("user_id", user_id).execute()
    
    # 3. 记录变动日志
    db.table("quota_logs").insert({
        "user_id": user_id,
        "change_amount": amount,
        "reason": "purchase"
    }).execute()
    
    print(f"✅ [支付] 用户 {user_id} 额度已更新: {current_quota} → {new_quota}")
    
    return new_quota


async def ensure_user_exists(access_key: str, app_key: str = None) -> BohriumUserInfo:
    """
    确保用户存在于数据库中，不存在则创建。
    
    Args:
        access_key: 用户的玻尔平台 accessKey（从 Cookie appAccessKey 获取）
        app_key: 用户的玻尔平台 appKey（从 Cookie clientName 获取）
    
    Returns:
        BohriumUserInfo: 用户信息
    
    Raises:
        Exception: 获取用户信息或创建用户失败
    """
    # 1. 获取玻尔用户信息（需要同时传入 access_key 和 app_key）
    user_info = get_user_info(access_key, app_key)
    
    if not user_info.user_id:
        raise Exception("无法获取用户 ID")
    
    db = get_db()
    
    # 2. 检查用户是否存在
    response = db.table("profiles").select("user_id").eq("user_id", user_info.user_id).execute()
    
    if response.data:
        # 用户已存在
        return user_info
    
    # 3. 创建新用户
    print(f"[支付] 创建新用户: {user_info.user_id} ({user_info.name})")
    
    db.table("profiles").insert({
        "user_id": user_info.user_id,
        "info": {
            "id": user_info.user_id,
            "name": user_info.name,
            "email": "",
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
            "preferences": [],
            "currentTask": "",
            "futureGoal": ""
        },
        "memory": {
            "user_prompt": [],
            "interactions": []
        },
        "remaining_quota": 1  # 新用户赠送 1 次
    }).execute()
    
    print(f"✅ [支付] 新用户已创建: {user_info.user_id}")
    
    return user_info
