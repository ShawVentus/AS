from fastapi import APIRouter
from app.api.v1.endpoints import (
    users,
    papers,
    login,
    interaction,
    workflow_management,
    progress,
    workflow
)

api_router = APIRouter()
api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(interaction.router, prefix="/interaction", tags=["interaction"])
api_router.include_router(workflow_management.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(progress.router, prefix="/workflow", tags=["progress"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
