from fastapi import APIRouter
from app.api.v1.endpoints import papers, user, reports

api_router = APIRouter()

api_router.include_router(papers.router, prefix="/papers", tags=["papers"])
api_router.include_router(user.router, prefix="/user", tags=["user"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
