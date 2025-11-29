from typing import List
from fastapi import APIRouter, HTTPException, Query, Depends
from app.schemas.paper import PersonalizedPaper, PaperAnalysis
from app.services.paper_service import paper_service
from app.services.user_service import user_service
from app.core.auth import get_current_user_id

router = APIRouter()

@router.get("/calendar", response_model=List[str])
async def get_paper_calendar(year: int, month: int, user_id: str = Depends(get_current_user_id)):
    return paper_service.get_paper_dates(user_id, year, month)

@router.get("/recommendations", response_model=List[PersonalizedPaper])
async def get_recommendations(date: str = Query(None), user_id: str = Depends(get_current_user_id)):
    return paper_service.get_recommendations(user_id, date)

@router.get("/", response_model=List[PersonalizedPaper])
async def get_papers(user_id: str = Depends(get_current_user_id)):
    return paper_service.get_papers(user_id)

@router.post("/fetch", response_model=List[PersonalizedPaper])
async def fetch_papers(limit: int = 100, user_id: str = Depends(get_current_user_id)):
    return paper_service.crawl_arxiv_new(user_id, limit)

@router.get("/daily", response_model=List[PersonalizedPaper])
async def get_daily_papers(user_id: str = Depends(get_current_user_id)):
    profile = user_service.get_profile(user_id) 
    papers = paper_service.get_papers(user_id)
    return paper_service.filter_papers(papers, profile)

@router.get("/{paper_id}/analysis", response_model=PaperAnalysis)
async def analyze_paper(paper_id: str, user_id: str = Depends(get_current_user_id)):
    paper = paper_service.get_paper_by_id(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文未找到")
    profile = user_service.get_profile(user_id)
    return paper_service.analyze_paper(paper, profile)

@router.get("/{paper_id}", response_model=PersonalizedPaper)
async def get_paper_detail(paper_id: str, user_id: str = Depends(get_current_user_id)):
    paper = paper_service.get_paper_by_id(paper_id, user_id)
    if not paper:
        raise HTTPException(status_code=404, detail="论文未找到")
    return paper

@router.post("/{paper_id}/feedback")
async def submit_paper_feedback(paper_id: str):
    # 模拟反馈提交
    return {"status": "success", "message": "反馈已收到"}
