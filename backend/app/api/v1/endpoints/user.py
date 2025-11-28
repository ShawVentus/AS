from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user_id
from app.core.database import get_db
from app.schemas.user import UserProfile, Focus, UserInfo, Status, Memory

router = APIRouter()

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(user_id: str = Depends(get_current_user_id)):
    """获取当前用户画像"""
    db = get_db()
    
    # 查询 profiles 表
    response = db.table("profiles").select("*").eq("user_id", user_id).single().execute()
    
    if not response.data:
        # 理论上 Trigger 会自动创建，但如果失败或尚未触发，返回 404 或默认空值
        raise HTTPException(status_code=404, detail="Profile not found")
        
    data = response.data
    
    # 构造返回数据
    # 注意: 数据库字段是 info, focus, context, memory
    # Pydantic 模型是 info, focus, status, memory
    # 这里假设 context 对应 status
    
    return UserProfile(
        info=UserInfo(**data.get("info", {})),
        focus=Focus(**data.get("focus", {})),
        status=Status(**data.get("context", {})), # Map context to status
        memory=Memory(**data.get("memory", {}))
    )

@router.put("/me/focus", response_model=Focus)
def update_user_focus(focus: Focus, user_id: str = Depends(get_current_user_id)):
    """更新用户关注领域"""
    db = get_db()
    
    # 更新 focus 字段
    db.table("profiles").update({"focus": focus.dict()}).eq("user_id", user_id).execute()
    
    return focus

@router.put("/me/info", response_model=UserInfo)
def update_user_info(info: UserInfo, user_id: str = Depends(get_current_user_id)):
    """更新用户信息"""
    db = get_db()
    
    db.table("profiles").update({"info": info.dict()}).eq("user_id", user_id).execute()
    
    return info
