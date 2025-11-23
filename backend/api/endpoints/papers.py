from typing import List
from fastapi import APIRouter, HTTPException, Query
from models.paper import Paper, PaperAnalysis
from services.paper_service import paper_service
from services.user_service import user_service

router = APIRouter()

@router.get("/recommendations", response_model=List[Paper])
async def get_recommendations():
    return paper_service.get_recommendations()

@router.get("/", response_model=List[Paper])
async def get_papers():
    return paper_service.get_papers()

@router.post("/fetch", response_model=List[Paper])
async def fetch_papers(limit: int = 100):
    return paper_service.crawl_arxiv_new(limit)

@router.get("/daily", response_model=List[Paper])
async def get_daily_papers():
    # 模拟：首先获取用户画像（在真实应用中，应从认证上下文中获取）
    profile = user_service.get_profile()
    papers = paper_service.get_papers()
    return paper_service.filter_papers(papers, profile)

@router.get("/{paper_id}/analysis", response_model=PaperAnalysis)
async def analyze_paper(paper_id: str):
    paper = paper_service.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    profile = user_service.get_profile()
    return paper_service.analyze_paper(paper, profile)

@router.get("/{paper_id}", response_model=Paper)
async def get_paper_detail(paper_id: str):
    paper = paper_service.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper

@router.post("/{paper_id}/feedback")
async def submit_paper_feedback(paper_id: str):
    # 模拟反馈提交
    return {"status": "success", "message": "Feedback received"}
