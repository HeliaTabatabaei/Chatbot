from typing import Any, Optional
from pydantic import BaseModel, Field

class DashboardQuestionRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="سؤال فارسی کاربر از داشبورد"
    )
class DashboardQuestionResponse(BaseModel):
    success: bool
    question: str
    normalized_question: Optional[str] = None
    answer: str
    sql: Optional[str] = None
    data: list[dict[str, Any]] =Field(default_factory=list)#  برای هر Response جدید یک لیست تازه می‌سازد
    error: Optional[str] = None