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
        db = get_db()
        while True:
            # 检查客户端是否断开
            if await request.is_disconnected():
                logger.info(f"Client disconnected from stream {execution_id}")
                break
                
            try:
                # 1. 查询执行状态
                exec_res = db.table("workflow_executions").select("*").eq("id", execution_id).execute()
                if not exec_res.data:
                    yield f"event: error\ndata: Execution not found\n\n"
                    break
                
                execution = exec_res.data[0]
                
                # 2. 查询步骤状态
                steps_res = db.table("workflow_steps").select("*").eq("execution_id", execution_id).order("step_order").execute()
                steps = steps_res.data
                
                # 3. 构造 payload
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
                            "cost": s.get("cost")
                        }
                        for s in steps
                    ]
                }
                
                yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
                
                # 如果已完成或失败，发送最后一次后退出
                if execution.get("status") in ["completed", "failed"]:
                    break
                    
            except Exception as e:
                logger.error(f"SSE Error: {e}")
                yield f"event: error\ndata: {str(e)}\n\n"
                
            # 等待 1 秒
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
