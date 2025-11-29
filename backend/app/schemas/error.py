from typing import Optional
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: Optional[str] = None
    code: Optional[str] = None
