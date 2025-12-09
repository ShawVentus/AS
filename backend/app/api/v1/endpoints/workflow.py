from fastapi import APIRouter, Depends
from app.core.auth import get_current_user_id
from app.services.scheduler import scheduler_service
import threading

router = APIRouter()

@router.post("/trigger-daily")
async def trigger_daily_workflow(user_id: str = Depends(get_current_user_id)):
    """
    手动触发每日工作流。
    
    功能说明：
    1. 检查 Arxiv 更新。
    2. 爬取新论文。
    3. 个性化筛选。
    4. 生成报告 + 发送邮件。
    
    Args:
        user_id (str): 当前用户 ID（用于验证权限）。

    Returns:
        dict: 包含状态和消息的字典。
    """
    # 异步执行工作流
    thread = threading.Thread(target=scheduler_service.run_daily_workflow)
    thread.start()
    
    return {
        "status": "started",
        "message": "每日工作流已在后台启动，请查看服务器日志"
    }

@router.post("/trigger-report-only")
async def trigger_report_only(user_id: str = Depends(get_current_user_id)):
    """
    仅生成报告（不爬取新论文）。
    
    适用场景：
    - 测试邮件发送。
    - 重新生成报告。
    
    Args:
        user_id (str): 当前用户 ID（用于验证权限）。

    Returns:
        dict: 包含状态和消息的字典。
    """
    thread = threading.Thread(target=scheduler_service.generate_report_job)
    thread.start()
    
    return {
        "status": "started",
        "message": "报告生成已在后台启动"
    }
