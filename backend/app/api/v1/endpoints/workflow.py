from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.services.scheduler import scheduler_service
from app.services.workflow_service import workflow_service
import threading

router = APIRouter()

from pydantic import BaseModel
from typing import Optional

class TriggerWorkflowRequest(BaseModel):
    target_user_id: Optional[str] = None
    force: bool = False

@router.post("/trigger-daily")
async def trigger_daily_workflow(
    request: TriggerWorkflowRequest = TriggerWorkflowRequest(),
    user_id: str = Depends(get_current_user_id)
):
    """
    手动触发每日工作流。
    
    功能说明：
    1. 检查 Arxiv 更新。
    2. 爬取新论文。
    3. 个性化筛选。
    4. 生成报告 + 发送邮件。
    
    Args:
        request (TriggerWorkflowRequest): 请求体，包含 target_user_id 和 force。
        user_id (str): 当前用户 ID（用于验证权限）。

    Returns:
        dict: 包含状态和消息的字典。
    """
    # 异步执行工作流
    # 如果请求中没有指定 target_user_id，则默认处理所有用户 (或者根据业务逻辑，手动触发是否只处理自己?)
    # 通常手动触发如果是管理员，可能想跑全量。如果是普通用户，可能只想跑自己。
    # 这里我们允许前端显式传递 target_user_id。
    
    # [Logic] 如果前端传了 target_user_id，则只跑该用户。
    # 此外，为了方便调试，允许 force 参数。
    
    # 1. 预先创建 Execution Record，以便立即返回 ID
    from app.services.workflow_engine import WorkflowEngine
    engine = WorkflowEngine()
    # 初始上下文
    initial_context = {
        "force": request.force,
        "target_user_id": request.target_user_id
    }
    execution_id = engine.create_execution("daily_update", initial_context=initial_context)
    
    # 2. 启动后台线程，传入 execution_id
    thread = threading.Thread(
        target=scheduler_service.run_daily_workflow,
        kwargs={
            "force": request.force, 
            "target_user_id": request.target_user_id,
            "execution_id": execution_id
        }
    )
    thread.start()
    
    return {
        "status": "started",
        "message": f"每日工作流已启动 (Target User: {request.target_user_id or 'All'})",
        "execution_id": execution_id
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

from typing import List
from app.services.workflow_engine import WorkflowEngine

class ManualTriggerRequest(BaseModel):
    user_id: str
    natural_query: str
    categories: List[str]
    authors: List[str]

@router.post("/manual-trigger")
async def manual_trigger_workflow(request: ManualTriggerRequest):
    """
    手动触发每日工作流 (强制执行)。
    使用传入的参数覆盖用户默认设置。

    Args:
        request (ManualTriggerRequest): 手动触发请求对象。
            - user_id: 用户 ID。
            - natural_query: 自然语言查询描述。
            - categories: 关注的 Arxiv 分类列表。
            - authors: 关注的作者列表。

    Returns:
        dict: 包含执行 ID 和消息的字典。
    """
    try:
        # === 新增：额度前置校验 ===
        from app.services.user_service import user_service
        if not user_service.has_sufficient_quota(request.user_id):
            print(f"⚠️ 用户 {request.user_id} 尝试手动触发，但额度不足")
            raise HTTPException(
                status_code=403, 
                detail={
                    "error": "insufficient_quota",
                    "message": "您的额度不足，请充值后继续使用"
                }
            )

        # 构造上下文，包含手动输入的参数
        initial_context = {
            "target_user_id": request.user_id,
            "force": True, # 强制执行
            "natural_query": request.natural_query,
            "manual_categories": request.categories, # 传递手动选择的分类
            "manual_authors": request.authors,       # 传递手动输入的作者
            "categories": request.categories,        # 爬虫步骤直接使用这个 key
            "source": "manual"
        }
        
        # 初始化引擎
        engine = WorkflowEngine()
        
        # 先创建执行记录以获取 ID
        engine.create_execution("manual_report", initial_context=initial_context)
        
        # 注册步骤 (复用 daily_update 的步骤)
        from app.services.workflow_steps.run_crawler_step import RunCrawlerStep
        from app.services.workflow_steps.fetch_details_step import FetchDetailsStep
        from app.services.workflow_steps.analyze_public_step import AnalyzePublicStep
        from app.services.workflow_steps.archive_step import ArchiveStep
        from app.services.workflow_steps.personalized_filter_step import PersonalizedFilterStep
        from app.services.workflow_steps.generate_report_step import GenerateReportStep
        
        # 注意：手动触发不清除每日数据 (ClearDailyStep)，也不检查更新 (CheckUpdateStep)
        # 直接开始爬取 -> 详情 -> 分析 -> 归档 -> 筛选 -> 报告
        engine.register_step(RunCrawlerStep())
        engine.register_step(FetchDetailsStep())
        engine.register_step(AnalyzePublicStep())
        engine.register_step(ArchiveStep())
        engine.register_step(PersonalizedFilterStep())
        engine.register_step(GenerateReportStep())
        
        # 异步运行
        # 使用 execute_workflow 而不是 run
        thread = threading.Thread(
            target=engine.execute_workflow,
            kwargs={"workflow_type": "manual_report", "initial_context": initial_context}
        )
        thread.start()
        
        return {"message": "Manual workflow started", "execution_id": engine.execution_id}
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active")
async def get_active_workflow(user_id: str = Depends(get_current_user_id)):
    """
    获取当前活跃的工作流执行状态。
    """
    execution = workflow_service.get_active_execution(user_id)
    if not execution:
        return {"active": False}
        
    # Get steps for this execution
    try:
        steps_response = workflow_service.db.table("workflow_steps") \
            .select("*") \
            .eq("execution_id", execution["id"]) \
            .order("step_order") \
            .execute()
            
        return {
            "active": True,
            "execution_id": execution["id"],
            "status": execution["status"],
            "steps": steps_response.data
        }
    except Exception as e:
        print(f"Error fetching active steps: {e}")
        return {"active": False}


@router.get("/verify-execution/{execution_id}")
async def verify_execution(execution_id: str):
    """
    验证工作流执行是否真的在运行。
    
    检查逻辑：
    1. 数据库记录是否存在
    2. 状态是否为 running
    3. 最后更新时间是否在合理范围内（10 分钟）
    
    Args:
        execution_id: 执行记录 ID
    
    Returns:
        {
            "active": bool,
            "status": str (如果 active=True),
            "reason": str (如果 active=False: not_found/already_finished/stale),
            "current_step": str (如果 active=True),
            "message": str,
            "last_update": str (如果 reason=stale),
            "elapsed_seconds": float (如果 reason=stale)
        }
    """
    from datetime import datetime, timedelta
    from app.core.database import get_db
    import logging
    
    logger = logging.getLogger(__name__)
    db = get_db()
    
    try:
        # 1. 查询数据库
        exec_res = db.table("workflow_executions").select("*").eq("id", execution_id).execute()
        
        if not exec_res.data:
            return {
                "active": False,
                "reason": "not_found",
                "message": "执行记录不存在"
            }
        
        record = exec_res.data[0]
        status = record.get("status")
        
        # 2. 检查状态
        if status in ["completed", "failed"]:
            return {
                "active": False,
                "reason": "already_finished",
                "status": status,
                "message": f"任务已{status}"
            }
        
        # 3. 检查最后更新时间（防止僵尸任务）
        updated_at_str = record.get("updated_at")
        if updated_at_str:
            try:
                # Supabase 返回 ISO 格式时间字符串，可能包含 Z 或 +00:00
                if 'Z' in updated_at_str:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                else:
                    updated_at = datetime.fromisoformat(updated_at_str)
                
                # 使用 UTC 时间比较
                from datetime import timezone
                now = datetime.now(timezone.utc)
                
                # 确保 updated_at 有时区信息
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                elapsed = (now - updated_at).total_seconds()
                
                # 10 分钟阈值
                if elapsed > 600:
                    return {
                        "active": False,
                        "reason": "stale",
                        "last_update": updated_at_str,
                        "elapsed_seconds": elapsed,
                        "message": f"任务超过 10 分钟未更新（{int(elapsed/60)} 分钟前），可能已停止"
                    }
            except Exception as e:
                logger.error(f"解析时间失败: {e}")
                # 如果时间解析失败，仍然认为任务在运行（避免误杀）
        
        # 4. 任务仍在运行
        return {
            "active": True,
            "status": status,
            "current_step": record.get("current_step"),
            "message": "任务正在运行"
        }
        
    except Exception as e:
        logger.error(f"验证执行失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")

