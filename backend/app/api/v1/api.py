from fastapi import APIRouter
from app.api.v1.endpoints import (
    user,
    papers,
    progress,
    workflow,
    email,
    reports,
    tools
)

api_router = APIRouter()
# api_router.include_router(login.router, tags=["login"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
# api_router.include_router(interaction.router, prefix="/interaction", tags=["interaction"])
# api_router.include_router(workflow_management.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(progress.router, prefix="/workflow", tags=["progress"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(email.router, prefix="/email", tags=["email"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])

