from typing import List
from fastapi import APIRouter, HTTPException, Body, Depends
from app.schemas.report import Report
from app.services.report_service import report_service
from app.services.paper_service import paper_service
from app.services.user_service import user_service
from app.core.auth import get_current_user_id

router = APIRouter()

@router.get("/", response_model=List[Report])
async def get_reports(user_id: str = Depends(get_current_user_id)):
    """获取当前用户的所有报告"""
    return report_service.get_reports(user_id)

@router.post("/generate", response_model=Report)
async def generate_report():
    profile = user_service.get_profile()
    papers = paper_service.get_papers() # 应该是筛选后的论文
    report, _, _ = report_service.generate_daily_report(papers, profile)
    return report

@router.post("/send")
async def send_report(report_id: str, email: str = Body(..., embed=True)):
    report = report_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到")
    success = report_service.send_email(report, email)
    return {"success": success}

@router.get("/{report_id}", response_model=Report)
async def get_report_detail(report_id: str):
    report = report_service.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告未找到")
    return report
