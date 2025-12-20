"""
支付 API 接口模块

功能说明：
  提供用户购买研报次数的 HTTP 接口。
  负责参数验证、请求处理和响应格式化。

接口列表：
  - POST /consume - 购买研报生成次数
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.payment_service import process_purchase, ensure_user_exists
from app.services.bohrium_service import get_access_key_or_default


# ===================== 路由定义 =====================

router = APIRouter()


# ===================== 请求/响应模型 =====================

class ConsumeRequest(BaseModel):
    """
    购买请求体。
    
    Attributes:
        eventValue: 消费的光子数量（100/400/1200）
        quotaAmount: 购买的次数（1/5/20）
    """
    eventValue: int = Field(..., description="消费的光子数量", example=400)
    quotaAmount: int = Field(..., description="购买的次数", example=5)


class ConsumeResponseData(BaseModel):
    """
    购买成功时的响应数据。
    """
    outBizNo: Optional[str] = Field(None, description="玻尔平台交易流水号")
    requestId: Optional[int] = Field(None, description="玻尔平台请求 ID")
    newQuota: Optional[int] = Field(None, description="更新后的次数余额")


class ConsumeResponse(BaseModel):
    """
    购买响应体。
    
    Attributes:
        success: 是否购买成功
        message: 结果提示消息
        data: 购买成功时的详细数据
    """
    success: bool
    message: str
    data: Optional[ConsumeResponseData] = None


# ===================== 接口实现 =====================

@router.post("/consume", response_model=ConsumeResponse)
async def consume_payment(request: Request, body: ConsumeRequest):
    """
    用户购买研报生成次数。
    
    处理流程：
    1. 从 Cookie 读取 accessKey（开发环境使用环境变量默认值）
    2. 通过玻尔 SDK 获取/创建用户
    3. 调用玻尔扣费接口
    4. 扣费成功后：
       - 记录交易到 payment_transactions 表
       - 更新 profiles.remaining_quota
       - 记录变动日志到 quota_logs 表
    5. 返回购买结果
    
    三档价格：
    - 100 光子 → 1 次（单次生成）
    - 400 光子 → 5 次（一周研报，20% OFF）
    - 1200 光子 → 20 次（一月研报，40% OFF）
    
    Args:
        request: FastAPI Request 对象（用于读取 Cookie）
        body: 请求体，包含 eventValue 和 quotaAmount
    
    Returns:
        ConsumeResponse: 购买结果
    
    Example:
        请求:
        POST /api/payment/consume
        {"eventValue": 400, "quotaAmount": 5}
        
        成功响应:
        {
            "success": true,
            "message": "购买成功，已获得 5 次生成额度",
            "data": {
                "outBizNo": "customsku-xxx",
                "requestId": 7149196,
                "newQuota": 6
            }
        }
        
        失败响应:
        {
            "success": false,
            "message": "光子余额不足，请前往玻尔平台充值",
            "data": null
        }
    """
    # 1. 获取 accessKey 和 appKey
    try:
        access_key = request.cookies.get("appAccessKey")
        access_key = get_access_key_or_default(access_key)
        app_key = request.cookies.get("clientName")  # 玻尔平台设置的 appKey
    except ValueError as e:
        return ConsumeResponse(
            success=False,
            message="未登录或登录已过期，请刷新页面"
        )
    
    # 2. 确保用户存在
    try:
        user_info = await ensure_user_exists(access_key, app_key)
    except Exception as e:
        print(f"❌ [支付接口] 获取用户信息失败: {e}")
        return ConsumeResponse(
            success=False,
            message="获取用户信息失败，请刷新页面重试"
        )
    
    # 3. 参数验证
    valid_tiers = {100: 1, 400: 5, 1200: 20}
    if body.eventValue not in valid_tiers:
        return ConsumeResponse(
            success=False,
            message="无效的价格档位"
        )
    
    if body.quotaAmount != valid_tiers[body.eventValue]:
        return ConsumeResponse(
            success=False,
            message="次数与价格不匹配"
        )
    
    # 4. 执行购买流程（【修复】传入 app_key 以正确调用玻尔扣费接口）
    result = await process_purchase(
        user_id=user_info.user_id,
        access_key=access_key,
        event_value=body.eventValue,
        quota_amount=body.quotaAmount,
        app_key=app_key  # 传入 Cookie 中的 clientName
    )
    
    # 5. 返回结果
    if result.success:
        return ConsumeResponse(
            success=True,
            message=result.message,
            data=ConsumeResponseData(
                outBizNo=result.out_biz_no,
                requestId=result.request_id,
                newQuota=result.new_quota
            )
        )
    else:
        return ConsumeResponse(
            success=False,
            message=result.message
        )
