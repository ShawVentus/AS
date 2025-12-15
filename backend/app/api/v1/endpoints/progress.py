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

    return StreamingResponse(event_generator(), media_type="text/event-stream")
