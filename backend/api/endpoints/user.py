from typing import List
from fastapi import APIRouter, HTTPException
from models.user import UserProfile, UserInfo, NaturalLanguageInput, UserFeedback
from services.user_service import user_service

router = APIRouter()

@router.get("/profile", response_model=UserProfile)

@router.put("/memory", response_model=UserProfile)
async def update_user_memory(profile: UserProfile):
    # 模拟实现
    return user_service.get_profile()
