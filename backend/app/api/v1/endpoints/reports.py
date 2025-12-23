from typing import List
from fastapi import APIRouter, HTTPException, Body, Depends, BackgroundTasks
from app.schemas.report import Report
from app.services.report_service import report_service
from app.services.paper_service import paper_service
from app.services.user_service import user_service
from app.core.auth import get_current_user_id

router = APIRouter()

@router.get("/", response_model=List[Report])
async def get_reports(user_id: str = Depends(get_current_user_id)):
    """
    获取当前用户的所有报告 (Get User Reports)
    
    Args:
        user_id (str): 当前登录用户的 ID。
        
    Returns:
        List[Report]: 报告对象列表。
    """
    return report_service.get_reports(user_id)

@router.post("/generate", response_model=Report)
async def generate_report(background_tasks: BackgroundTasks):
    """
    手动触发生成每日报告
    
    Args:
        background_tasks (BackgroundTasks): FastAPI 后台任务管理器
        
    Returns:
        Report: 生成的报告对象
    """
    profile = user_service.get_profile()
    papers = paper_service.get_papers() # 获取待处理论文
    
    # 生成报告，并传入 background_tasks 以实现异步邮件发送
    report, _, _ = report_service.generate_daily_report(papers, profile, background_tasks=background_tasks)
    
    return report

@router.post("/send")
async def send_report(report_id: str, background_tasks: BackgroundTasks, email: str = Body(..., embed=True)):
    """
    手动重发报告邮件
    
    Args:
        report_id (str): 报告 ID
        background_tasks (BackgroundTasks): FastAPI 后台任务管理器
        email (str): 目标邮箱地址
        
    Returns:
        dict: 包含成功状态的字典
    """
    report = report_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到")
    
    # 使用后台任务发送邮件，避免阻塞
    background_tasks.add_task(report_service.resend_daily_report, report_id)
    
    return {"success": True, "message": "邮件发送任务已提交至后台"}

@router.get("/{report_id}", response_model=Report)
async def get_report_detail(report_id: str):
    """
    获取报告详情 (Get Report Detail)
    
    Args:
        report_id (str): 报告的唯一标识。
        
    Returns:
        Report: 报告详细对象。
        
    Raises:
        HTTPException: 如果报告未找到，抛出 404 错误。
    """
    report = report_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到")
    return report
