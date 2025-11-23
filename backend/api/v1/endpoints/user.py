from typing import List
from fastapi import APIRouter, HTTPException
from schemas.user import UserProfile, UserInfo, NaturalLanguageInput, UserFeedback
from services.user_service import user_service

router = APIRouter()

@router.get("/profile", response_model=UserProfile)
async def get_profile():
    return user_service.get_profile()

@router.put("/nl", response_model=UserProfile)
async def update_profile_nl(input_data: NaturalLanguageInput):
    return user_service.update_profile_nl(input_data.user_id, input_data.text)

@router.put("/memory", response_model=UserProfile)
async def update_user_memory(profile: UserProfile):
    # 模拟实现
    return user_service.get_profile()
