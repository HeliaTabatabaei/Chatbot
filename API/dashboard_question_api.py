import json

from fastapi import APIRouter,Body
from fastapi.responses import StreamingResponse

# مسیر import را با نام واقعی فایل Model خودت هماهنگ کن
from Models.dashboard_chat_models import (
    DashboardQuestionRequest,
    DashboardQuestionResponse,
)

from SQlDB.DashboardQuery import run_sql
from config import EMBED_MODEL, LLM_MODEL, OPENAI_API_KEY
from providers.factory import create_provider
from service.dashboard_chat_service import ask
from service.dashboard_llm_service import generate_answer_stream, generate_sql, llm
router = APIRouter(prefix="/api/DshboardDaftar", tags=["100 - DshboardDaftar"])
@router.post(
    "/question",
    response_model=DashboardQuestionResponse,
)
def ask_dashboard_question(
    request: DashboardQuestionRequest,
) -> DashboardQuestionResponse:
    # """
    # دریافت سؤال فارسی کاربر، تولید SQL،
    # اجرای آن در SQL Server و برگرداندن پاسخ فارسی.
    # """

    try:
        result = ask(
            llm=llm,
            question=request.question,
        )

        return DashboardQuestionResponse(
            success=True,
            question=request.question,
            normalized_question=request.question,
            answer=result["answer"],
            sql=result["sql"],
            data=result["data"],
            error=None,
        )

    except Exception as error:
        return DashboardQuestionResponse(
            success=False,
            question=request.question,
            normalized_question=request.question,
            answer="",
            sql=None,
            data=[],
            error=str(error),
        )
@router.post("/ask-dashboard-stream")
async def ask_dashboard_stream(question: str = Body(..., embed=True)):
    
    # 1. ایجاد LLM (بهتر است به صورت Dependency Injection باشد ولی اینجا برای سادگی مستقیم است)
    llm = create_provider(
        provider_name="openai",
        base_uri="https://api.gapgpt.app/v1",
        api_key=OPENAI_API_KEY,
        model=LLM_MODEL,
        embed_model=EMBED_MODEL,
    )

    def event_generator():
        # الف) مرحله تولید SQL (غیر استریم)
        # می‌توانیم اولین رویداد را برای اطلاع به کاربر بفرستیم
        yield f"event: status\ndata: {json.dumps({'message': 'در حال تحلیل سوال...'}, ensure_ascii=False)}\n\n"
        
        sql_query = generate_sql(llm=llm, user_question=question)
        
        # ب) اجرای SQL
        yield f"event: status\ndata: {json.dumps({'message': 'در حال استخراج داده از دیتابیس...'}, ensure_ascii=False)}\n\n"
        data = run_sql(sql_query)
        
        # ج) شروع استریم پاسخ LLM
        # چون chat_stream شما با callback کار می‌کند، از یک Queue برای تبدیل آن به Iterator استفاده می‌کنیم
        import queue
        from threading import Thread

        q = queue.Queue()

        def on_chunk(chunk):
            q.put(chunk)

        # اجرای LLM در یک ترد جداگانه تا ترد اصلی بلاک نشود
        def run_llm():
            try:
                generate_answer_stream(
                    llm=llm,
                    question=question,
                    data=data,
                    on_chunk=on_chunk
                )
            finally:
                q.put(None) # نشانه پایان

        Thread(target=run_llm).start()

        while True:
            item = q.get()
            if item is None:
                break
            
            # ارسال هر چانک به کلاینت
            # اگر type == token باشد، به عنوان چانک متنی و اگر meta باشد به عنوان دیتا
            event_type = item.get("type", "message")
            yield f"event: {event_type}\ndata: {json.dumps(item, ensure_ascii=False)}\n\n"

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no" # برای جلوگیری از بافر شدن در Nginx
        }
    )