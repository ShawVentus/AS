from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.llm_service import llm_service

router = APIRouter()

class TextToCategoriesRequest(BaseModel):
    text: str

class TextToCategoriesResponse(BaseModel):
    categories: List[str]
    authors: List[str]

@router.post("/text-to-categories", response_model=TextToCategoriesResponse)
async def text_to_categories(request: TextToCategoriesRequest):
    """
    使用 LLM 从自然语言中提取 Arxiv 类别和作者。

    Args:
        request (TextToCategoriesRequest): 请求体，包含自然语言文本。
            - text: 用户输入的自然语言描述。

    Returns:
        TextToCategoriesResponse: 包含提取出的类别和作者列表。
            - categories: 提取出的 Arxiv 类别列表。
            - authors: 提取出的作者列表。
    """
    if not request.text.strip():
        return {"categories": [], "authors": []}
        
    try:
        result = llm_service.extract_categories(request.text)
        return {
            "categories": result.get("categories", []),
            "authors": result.get("authors", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
