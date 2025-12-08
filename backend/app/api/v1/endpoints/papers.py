from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from fastapi.responses import PlainTextResponse
from app.schemas.paper import PersonalizedPaper, PaperAnalysis, PaperFeedbackRequest, PaperExportRequest
from app.services.paper_service import paper_service
from app.services.user_service import user_service
from app.core.auth import get_current_user_id, get_current_user_id_optional

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

async def fetch_papers(limit: int = 100, user_id: str = Depends(get_current_user_id)):
    return paper_service.crawl_arxiv_new(user_id, limit)

@router.get("/batch", response_model=List[PersonalizedPaper])
async def get_papers_by_ids(ids: List[str] = Query(...), user_id: Optional[str] = Depends(get_current_user_id_optional)):
    """
    批量获取论文详情。

    Args:
        ids (List[str]): 论文 ID 列表。
        user_id (Optional[str]): 当前用户 ID (可选)。如果提供，将返回个性化状态。

    Returns:
        List[PersonalizedPaper]: 论文对象列表。
    """
    return paper_service.get_papers_by_ids_with_user(ids, user_id)

@router.get("/daily", response_model=List[PersonalizedPaper])
async def get_daily_papers(user_id: str = Depends(get_current_user_id)):
    profile = user_service.get_profile(user_id)
    
    # 1. 同步用户私有库 (Sync)
    sync_log = paper_service.get_papers_by_categories(user_id=user_id)
    print(f"[Daily Sync] {sync_log}")
    
    # 2. 获取待处理的候选论文 (Pending)
    candidates = paper_service.get_pending_papers(user_id=user_id, limit=50)
    
    # 2. 如果没有候选论文 (或者都已处理过)，尝试获取一些最新的 (兜底)
    if not candidates:
        # 这里可以选择是否要兜底，或者直接返回空
        # 为了用户体验，如果完全没有新论文，可能需要触发爬虫或者返回空
        # 暂时返回空，由前端提示
        return []

    # 3. 使用 LLM 过滤
    return paper_service.filter_papers(candidates, profile, user_id)

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

@router.post("/export")
async def export_papers(
    request: PaperExportRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    导出论文接口。
    支持 Markdown 和 JSON 格式。
    """
    # 强制覆盖 user_id 为当前登录用户，防止越权
    request.user_id = user_id
    
    result = paper_service.export_papers(request)
    
    if request.format == "markdown":
        return PlainTextResponse(result)
    else:
        return result
