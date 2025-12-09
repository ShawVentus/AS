from fastapi import APIRouter, Depends, HTTPException, Response
from app.core.auth import get_current_user_id
from app.services.report_service import report_service
from pydantic import BaseModel

router = APIRouter()

@router.get("/track/{report_id}/{user_id}")
async def track_email_open(report_id: str, user_id: str):
    """
    追踪邮件打开事件
    
    主要功能：
    1. 记录邮件打开事件到数据库
    2. 返回 1x1 透明 GIF 图片
    
    Args:
        report_id (str): 报告ID
        user_id (str): 用户ID
        
    Returns:
        Response: GIF 图片数据
    """
    report_service._log_email_event(report_id, user_id, "opened")
    
    # 1x1透明GIF
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    return Response(content=pixel, media_type="image/gif")

class FeedbackRequest(BaseModel):
    """反馈请求模型"""
    report_id: str
    rating: int
    feedback_text: str = None

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    提交报告反馈
    
    主要功能：
    接收用户对报告的评分和反馈文本，并保存到数据库。
    
    Args:
        feedback (FeedbackRequest): 反馈数据
        user_id (str): 当前用户ID
        
    Returns:
        dict: 成功消息
    """
    success = report_service.submit_feedback(
        feedback.report_id,
        user_id,
        feedback.rating,
        feedback.feedback_text
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to submit feedback")
    
    return {"message": "Feedback submitted"}
