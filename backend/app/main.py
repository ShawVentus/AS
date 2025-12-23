import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.api import api_router
from app.services.scheduler import scheduler_service
import logging

# 配置日志，屏蔽 httpx 的 INFO 日志
logging.getLogger("httpx").setLevel(logging.WARNING)


async def cleanup_stale_executions():
    """
    清理数据库中过期的 running 任务。
    
    定义过期：status='running' 且 updated_at 超过 10 分钟
    """
    from datetime import datetime, timedelta, timezone
    from app.core.database import get_db
    
    db = get_db()
    
    try:
        # 1. 查询所有 running 状态的任务
        exec_res = db.table("workflow_executions")\
            .select("*")\
            .eq("status", "running")\
            .execute()
        
        if not exec_res.data:
            print("✓ 无需清理的任务")
            return
        
        stale_count = 0
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        
        for record in exec_res.data:
            updated_at_str = record.get("updated_at")
            if not updated_at_str:
                continue
            
            try:
                # 解析时间字符串
                if 'Z' in updated_at_str:
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                else:
                    updated_at = datetime.fromisoformat(updated_at_str)
                
                # 确保有时区信息
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                
                # 检查是否过期
                if updated_at < cutoff_time:
                    # 标记为失败
                    db.table("workflow_executions").update({
                        "status": "failed",
                        "error": "任务因服务器重启而中断",
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }).eq("id", record["id"]).execute()
                    
                    stale_count += 1
                    print(f"✓ 已清理过期任务: {record['id']} (最后更新: {updated_at_str})")
            
            except Exception as e:
                print(f"✗ 清理任务 {record['id']} 失败: {e}")
        
        if stale_count > 0:
            print(f"✓ 共清理 {stale_count} 个过期任务")
        else:
            print("✓ 无过期任务")
    
    except Exception as e:
        print(f"✗ 清理过期任务失败: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    print("Starting up...")
    
    # 【修改】使用后台线程清理过期任务，不阻塞启动
    import threading
    import asyncio
    cleanup_thread = threading.Thread(
        target=lambda: asyncio.run(cleanup_stale_executions())
    )
    cleanup_thread.daemon = True  # 设为守护线程
    cleanup_thread.start()
    
    scheduler_service.start()
    yield
    # 关闭
    print("Shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# CORS跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境中应使用 settings.FRONTEND_URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API"}

if __name__ == "__main__":
    import uvicorn
    
    scheduler_service.start()
    
    # 从配置获取主机和端口
    host = settings.HOST
    port = settings.PORT
    uvicorn.run(app, host=host, port=port)
