"""
workflow_management.py
工作流管理 API 端点。
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, Dict, Any
from pydantic import BaseModel

from app.services.workflow_engine import WorkflowEngine
from app.services.scheduler import scheduler_service

router = APIRouter()

class WorkflowRequest(BaseModel):
    workflow_type: str = "daily_update"
    params: Optional[Dict[str, Any]] = {}

class ResumeRequest(BaseModel):
    execution_id: str

@router.post("/trigger-daily")
async def trigger_daily_workflow(background_tasks: BackgroundTasks):
    """
    触发每日更新工作流 (异步)。
    """
    # 1. 预先创建执行记录以获取 ID
    engine = WorkflowEngine()
    execution_id = engine._create_execution_record("daily_update")
    
    # 2. 启动后台任务，传入 ID
    background_tasks.add_task(scheduler_service.run_daily_workflow, execution_id)
    
    return {
        "message": "Daily workflow triggered in background.",
        "execution_id": execution_id
    }

@router.post("/execute")
async def execute_workflow(request: WorkflowRequest, background_tasks: BackgroundTasks):
    """
    执行通用工作流。
    """
    engine = WorkflowEngine()
    # 这里需要根据 workflow_type 组装步骤，目前仅支持 daily_update
    if request.workflow_type == "daily_update":
        background_tasks.add_task(scheduler_service.run_daily_workflow)
        return {"message": "Daily update workflow started."}
    else:
        raise HTTPException(status_code=400, detail="Unsupported workflow type")

@router.post("/resume")
async def resume_workflow(request: ResumeRequest, background_tasks: BackgroundTasks):
    """
    恢复工作流。
    """
    def _resume_task(exec_id: str):
        engine = WorkflowEngine()
        try:
            engine.resume_workflow(exec_id)
        except Exception as e:
            print(f"Resume failed: {e}")

    background_tasks.add_task(_resume_task, request.execution_id)
    return {"message": f"Resuming workflow {request.execution_id} in background."}

@router.get("/status/{execution_id}")
async def get_workflow_status(execution_id: str):
    """
    获取工作流执行状态。
    """
    # TODO: 查询数据库
    return {"execution_id": execution_id, "status": "unknown"}

@router.get("/performance/{execution_id}")
async def get_workflow_performance(execution_id: str):
    """
    获取工作流性能报告。
    """
    # TODO: 查询数据库并聚合 metrics
    return {"execution_id": execution_id, "metrics": {}}
