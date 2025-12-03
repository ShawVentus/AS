from typing import List
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from app.schemas.paper import PersonalizedPaper, PaperAnalysis, PaperFeedbackRequest
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
    
    # 1. 根据用户关注的类别获取候选论文
    candidates = paper_service.get_papers_by_categories(
        categories=profile.focus.category, 
        user_id=user_id,
        limit=50 # 每次处理 50 篇
    )
    
    # 2. 如果没有候选论文 (或者都已处理过)，尝试获取一些最新的 (兜底)
    if not candidates:
        # 这里可以选择是否要兜底，或者直接返回空
        # 为了用户体验，如果完全没有新论文，可能需要触发爬虫或者返回空
        # 暂时返回空，由前端提示
        return []

    # 3. 使用 LLM 过滤
    return paper_service.filter_papers(candidates, profile)

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
async def submit_paper_feedback(
    paper_id: str, 
    feedback_data: PaperFeedbackRequest,
    user_id: str = Depends(get_current_user_id)
):
    success = paper_service.update_user_feedback(
        user_id=user_id,
        paper_id=paper_id,
        liked=feedback_data.liked,
        feedback=feedback_data.feedback
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="反馈提交失败")
        
    return {"status": "success", "message": "反馈已收到"}
