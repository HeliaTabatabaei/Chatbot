
# Request/Response models
from typing import List, Optional

from pydantic import BaseModel, Field

class QueryRequestStream(BaseModel):
    query: str
    temperature: float = 0.1
class QueryRequestStreamٌwithConversionId(BaseModel):
    query: str
    temperature: float = 0.1
    conversation_id: Optional[str] = None  # اضافه شد
class SearchFilters(BaseModel):
    """فیلترهای metadata برای جستجو"""
    doc_ids: Optional[List[str]] = Field(None, description="فیلتر بر اساس doc_id")
    tags: Optional[List[str]] = Field(None, description="فیلتر بر اساس tags")
    keywords: Optional[List[str]] = Field(None, description="فیلتر بر اساس keywords")
    date_from: Optional[str] = Field(None, description="تاریخ شروع (ISO format)")
    date_to: Optional[str] = Field(None, description="تاریخ پایان (ISO format)")


class QueryRequest(BaseModel):
    query: str = Field(..., description="سوال فنی تکنسین", min_length=1)
    limit: Optional[int] = Field(5, description="تعداد نتایج جستجو", ge=1, le=20)
    temperature: Optional[float] = Field(0.1, description="دمای مدل", ge=0.0, le=1.0)
    use_hybrid: Optional[bool] = Field(True, description="استفاده از hybrid search (dense + sparse)")
    filters: Optional[SearchFilters] = Field(None, description="فیلترهای metadata")
class QueryRequestWithHistory(BaseModel):
    query: str
    limit: int = 5
    temperature: float = 0.1
    use_hybrid: bool = True
    conversation_id: Optional[str] = None
    user_key: Optional[str] = None
    filters: Optional[SearchFilters] = None


class SearchResult(BaseModel):
    id: str
    score: float
    text: str
    doc_id: Optional[str] = None
    title: Optional[str] = None
    heading: Optional[str] = None
    date: Optional[str] = None
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    source_file: str


class QueryResponse(BaseModel):
    answer: str
    sources: List[SearchResult]
    query: str
    search_mode: str  # "dense" یا "hybrid"
class QueryResponseHistory(BaseModel):
    answer: str
    sources: List[SearchResult]
    query: str
    search_mode: str
    conversation_id: Optional[str] = None  # اضافه شد
#  مدل درخواست ورودی از سوییگر
class BulkChargeRequest(BaseModel):
    amount: int = Field(..., gt=0, description="مقدار توکن برای شارژ همه کاربران")#gt=0بزرگتر از صفر باشه
    user_keys: List[str] = Field(..., min_items=1, description="لیست شناسه کاربران هدف")#min_items=1لیست خالی نفرسته