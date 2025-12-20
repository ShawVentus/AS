"""
progress.py
SSE 实时进度推送端点。
"""

import asyncio
import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/progress-stream/{execution_id}")
async def progress_stream(execution_id: str, request: Request):
    """
    SSE 端点：实时推送工作流进度。
    """
    async def event_generator():
        # [Fix] Use global get_db() to ensure correct Service Key configuration and connection pooling
        local_db = get_db()
        print(f"[DEBUG] SSE connection started for execution_id: {execution_id}")
        
        while True:
            if await request.is_disconnected():
                logger.info(f"Client disconnected from stream {execution_id}")
                break
                
            try:
                # 1. 查询执行状态
                # Use asyncio.to_thread to prevent blocking, but wrap in try/except for connection errors
                def fetch_data():
                    exec_res = local_db.table("workflow_executions").select("*").eq("id", execution_id).execute()
                    steps_res = local_db.table("workflow_steps").select("*").eq("execution_id", execution_id).order("step_order").execute()
                    return exec_res, steps_res

                exec_res, steps_res = await asyncio.to_thread(fetch_data)
                
                if not exec_res.data:
                    logger.warning(f"SSE: Execution {execution_id} not found")
                    yield f"event: system_error\ndata: Execution not found\n\n"
                    break
                
                execution = exec_res.data[0]
                steps = steps_res.data
                
                payload = {
                    "execution_id": execution.get("id"),
                    "status": execution.get("status"),
                    "current_step": execution.get("current_step"),
                    "total_steps": execution.get("total_steps"),
                    "completed_steps": execution.get("completed_steps"),
                    "total_cost": execution.get("total_cost"),
                    "steps": [
                        {
                            "name": s.get("step_name"),
                            "status": s.get("status"),
                            "duration_ms": s.get("duration_ms"),
                            "cost": s.get("cost"),
                            "progress": s.get("progress")
                        }
                        for s in steps
                    ]
                }
                
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                
                if execution.get("status") in ["completed", "failed"]:
                    break
                    
            except Exception as e:
                logger.error(f"SSE Error: {e}")
                # Wait a bit longer on error before retrying
                await asyncio.sleep(2)
                continue
                
            await asyncio.sleep(1)

    # 关键：添加必要的 HTTP 头部以支持反向代理环境（HTTP/2 兼容）
    # - Cache-Control: no-cache - 禁用缓存
    # - Connection: keep-alive - 保持长连接
    # - X-Accel-Buffering: no - 告知 Nginx 不要缓冲响应（关键！）
    # - Access-Control-Allow-Origin: * - 允许跨域（根据需要调整）
    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Nginx 专用：禁止响应缓冲
        "Content-Type": "text/event-stream; charset=utf-8",
    }
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers=headers
    )


# ===================== 轮询端点（替代 SSE）=====================

@router.get("/progress/{execution_id}")
async def get_progress(execution_id: str):
    """
    普通 HTTP 端点：获取当前工作流进度。
    
    用于轮询模式，替代 SSE 长连接。在 Bohrium 容器环境中，
    由于反向代理导致 SSE 连接不稳定，前端改用定时轮询此端点获取进度。
    
    Args:
        execution_id: 工作流执行 ID（UUID 格式，如 'abc123-def456'）
    
    Returns:
        dict: 工作流进度数据，包含以下字段：
            - execution_id (str): 执行 ID
            - status (str): 执行状态（running/completed/failed/stopped）
            - current_step (int): 当前步骤序号
            - total_steps (int): 总步骤数
            - completed_steps (int): 已完成步骤数
            - total_cost (float): 总花费（美元）
            - steps (list): 各步骤详情列表，每个元素包含：
                - name (str): 步骤名称
                - status (str): 步骤状态
                - duration_ms (int): 耗时（毫秒）
                - cost (float): 步骤花费
                - progress (dict): 进度信息
    
    Raises:
        HTTPException: 404 - 未找到指定的执行记录
    
    Example:
        GET /api/v1/workflow/progress/abc123
        Response: {"execution_id": "abc123", "status": "running", "steps": [...]}
    """
    from fastapi import HTTPException
    
    db = get_db()
    
    # 1. 查询执行状态
    exec_res = db.table("workflow_executions").select("*").eq("id", execution_id).execute()
    
    if not exec_res.data:
        raise HTTPException(status_code=404, detail=f"未找到执行记录: {execution_id}")
    
    execution = exec_res.data[0]
    
    # 2. 查询步骤详情
    steps_res = db.table("workflow_steps").select("*").eq("execution_id", execution_id).order("step_order").execute()
    
    # 3. 构建响应数据
    return {
        "execution_id": execution.get("id"),
        "status": execution.get("status"),
        "current_step": execution.get("current_step"),
        "total_steps": execution.get("total_steps"),
        "completed_steps": execution.get("completed_steps"),
        "total_cost": execution.get("total_cost"),
        "steps": [
            {
                "name": s.get("step_name"),
                "status": s.get("status"),
                "duration_ms": s.get("duration_ms"),
                "cost": s.get("cost"),
                "progress": s.get("progress"),
                "message": s.get("message")  # 新增：进度消息
            }
            for s in steps_res.data
        ]
    }

