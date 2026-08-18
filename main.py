import json
import sys
import time
import traceback



from fastapi import  FastAPI, HTTPException

from fastapi.security import HTTPBearer

from fastapi.staticfiles import StaticFiles
from fastapi_swagger import patch_fastapi

from API.admin_routes import router as admin_router

from Models.mainModels import  QueryRequest,     SearchResult
from LLM.OpenAIManagment import  embed_query
from RAG_Management.QdrantManagment import checkQudrant, hybrid_search, init_history_collection, search

import uvicorn

from fastapi.middleware.cors import CORSMiddleware

from API.Wallet_routes import router as wallet_router
# from API.dashboard_question_api import router as DashboardDaftar_router
from API.query_routes import router as query_router
import json
from pathlib import Path
from fastapi import HTTPException

app = FastAPI(
    docs_url=None,
    swagger_ui_oauth2_redirect_url=None,
    title="Adonis Docs Assistant API",
    description="RAG-based technical support API for Adonis technicians",
    version="1.0.0"
)
patch_fastapi(app, docs_url="/docs")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # برای محیط توسعه؛ در محیط پروداکشن دامنه‌های خود را مشخص کنید
    allow_credentials=True,
    allow_methods=["*"],  # اجازه به تمام متدها (POST, GET, OPTIONS و...)
    allow_headers=["*"],  # اجازه به تمام هدرها
)
security = HTTPBearer()


BASE_DIR = Path(__file__).resolve().parent # تعریف مسیر پایه پروژه
MEDIA_ROOT = BASE_DIR / "data"  # مسیر دقیق پوشه داده‌ها

app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")
app.include_router(admin_router)
app.include_router(wallet_router)
# app.include_router(DashboardDaftar_router)
app.include_router(query_router)
# ایجاد کالکشن تاریخچه اگر وجود نداشته باشد
init_history_collection()
# @app.post("/api/query1", response_model=QueryResponse)
# async def query1_endpoint(request: QueryRequest):
#     """
#     پردازش سوال فنی و بازگشت پاسخ RAG-based

#     - **query**: سوال فنی تکنسین
#     - **limit**: تعداد اسناد مرتبط (پیش‌فرض: 5)
#     - **temperature**: دمای مدل (پیش‌فرض: 0.1)
#     - **use_hybrid**: استفاده از hybrid search (dense + sparse)
#     - **filters**: فیلترهای metadata (doc_ids, tags, keywords, date)
#     """
#     try:
#         # انتخاب نوع جستجو
#         if request.use_hybrid:
#             results = hybrid_search(
#                 query=request.query,
#                 limit=request.limit,
#                 filters=request.filters
#             )
#             search_mode = "hybrid"
#         else:
#             query_vector = embed_query(request.query)
#             results = search(
#                 query_vector=query_vector,
#                 limit=request.limit,
#                 filters=request.filters
#             )
#             print("QrantResult:  ",type(results))
#             search_mode = "dense"
  
#         if not results:
#             raise HTTPException(
#                 status_code=404,
#                 detail="هیچ سند مرتبطی یافت نشد"
#             )

#         # تولید پاسخ
#         answer = answer_with_rag(request.query, results, temperature=request.temperature)

#         # فرمت sources با metadata
#         sources = []
#         for r in results:

#             if isinstance(r, dict):
#                 payload = r["payload"]
#                 rid = r["id"]
#                 score = r["score"]
#             else:
#                 payload = r.payload
#                 rid = r.id
#                 score = r.score

#             sources.append(
#                 SearchResult(
#                     id=str(rid),
#                     score=score,
#                     text=payload.get("text", "")[:200] + "...",
#                     doc_id=payload.get("doc_id"),
#                     title=payload.get("title"),
#                     heading=payload.get("heading"),
#                     date=payload.get("date"),
#                     tags=payload.get("tags"),
#                     keywords=payload.get("keywords"),
#                     source_file=payload.get("source_file")
#                 )
#             )

#         return QueryResponse(
#             answer=answer,
#             sources=sources,
#             query=request.query,
#             search_mode=search_mode
#         )

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"خطا در پردازش درخواست: {str(e)}"
#         )
#-----------------------------------------------------
# @app.post("/api/query/stream")
# async def query_stream_endpoint(
#     request: QueryRequestStream,
#     background_tasks: BackgroundTasks,
#     credentials: HTTPAuthorizationCredentials = Depends(security)
# ):
#     try:
#         token = credentials.credentials
#         user_key = ""

#         try:
#             is_valid, message, user_key = get_current_user_payload(token)
#             if not is_valid:
#                 raise HTTPException(status_code=401, detail=message)
#         except ExpiredSignatureError:
#             raise HTTPException(status_code=401, detail="Token expired")
#         except JWTError as e:
#             raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

       
#         print(token, flush=True)

   

#         intent =  detect_intent(request.query)

#         print("intent", flush=True)
#         print(intent, flush=True)

#         if intent == "general":
#             return StreamingResponse(
             
#                 answer_general_stream(query=request.query,
#                                     userKey=user_key,
#                                     background_tasks=background_tasks),
#                 media_type="text/event-stream",
#                 headers={
#                     "Cache-Control": "no-cache",
#                     "Connection": "keep-alive",
#                     "X-Accel-Buffering": "no"
#                 }
#             )

#         query_vector = embed_query(request.query)

#         results = search(
#             query_vector=query_vector,
#             limit=5,
#             filters=None
#         )

#         if not results:
#             raise HTTPException(
#                 status_code=404,
#                 detail="هیچ سند مرتبطی یافت نشد"
#             )

#         reranked_results = rerank_results(request.query, results)

#         def event_stream():
#             try:
#                 for chunk in answer_with_rag_stream(
#                     query=request.query,
#                     userKey=user_key,
#                     background_tasks=background_tasks,
                    
#                     results=reranked_results,
#                     temperature=0.1
#                 ):
#                     if chunk:
#                         chunk_data = {
#                             "text": chunk
#                         }

#                         yield (
#                             "event: token\n"
#                             f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
#                         )

#                 yield "event: done\ndata: [DONE]\n\n"

#             except Exception as error:
#                 error_data = {
#                     "error": str(error)
#                 }

#                 yield (
#                     "event: error\n"
#                     f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
#                 )

#         return StreamingResponse(
#             event_stream(),
#             media_type="text/event-stream",
#             headers={
#                 "Cache-Control": "no-cache",
#                 "Connection": "keep-alive",
#                 "X-Accel-Buffering": "no"
#             }
#         )

#     except HTTPException:
#         raise

#     except Exception as error:
#         raise HTTPException(
#             status_code=500,
#             detail=f"خطا در جست‌وجو: {str(error)}"
#         )
#-----------------------------------------------------

# def search_documents(request: QueryRequest):
#     if request.use_hybrid:
#         results = hybrid_search(
#             query=request.query,
#             limit=request.limit,
#             filters=request.filters
#         )
#         search_mode = "hybrid"
#     else:
#         query_vector = embed_query(request.query)

#         results = search(
#             query_vector=query_vector,
#             limit=request.limit,
#             filters=request.filters
#         )
#         search_mode = "dense"

#     if not results:
#         raise HTTPException(
#             status_code=404,
#             detail="هیچ سند مرتبطی یافت نشد"
#         )

#     return results, search_mode
# def build_sources(results):
#     sources = []

#     for result in results:
#         if isinstance(result, dict):
#             payload = result["payload"]
#             result_id = result["id"]
#             score = result["score"]
#         else:
#             payload = result.payload
#             result_id = result.id
#             score = result.score

#         text = payload.get("text", "")

#         sources.append(
#             SearchResult(
#                 id=str(result_id),
#                 score=score,
#                 text=text[:200] + ("..." if len(text) > 200 else ""),
#                 doc_id=payload.get("doc_id"),
#                 title=payload.get("title"),
#                 heading=payload.get("heading"),
#                 date=payload.get("date"),
#                 tags=payload.get("tags"),
#                 keywords=payload.get("keywords"),
#                 source_file=payload.get("source_file")
#             )
#         )

#     return sources
 
sessions = {}

@app.get("/")
async def root():
    return {
        "message": "Adonis Tech Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "query": "/api/query",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """بررسی سلامت سرویس"""
    try:
        # qdrant.get_collections()
        # return {
        #     "status": "healthy",
        #     "qdrant": "connected",
        #     "collection": COLLECTION_NAME
        # }
        checkQudrant()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
# @app.post("/api/queryHistoryWithVectorDB", response_model=QueryResponseHistory)
# async def api_queryHistoryWithVectorDB(request: QueryRequestWithHistory,
#                          background_tasks: BackgroundTasks):
#     try:
#         query_vector = embed_query(request.query)

#         if request.use_hybrid:
#             results = hybrid_search(request.query, request.limit, request.filters)
#             search_mode = "hybrid"
#         else:
#             results = search(query_vector, request.limit, request.filters)
#             search_mode = "dense"

#         rag_result = answer_with_rag_withHistoryAndVectorDB(
#             query=request.query,
#             results=results,
#             background_tasks=background_tasks,
#             temperature=request.temperature,
#             conversation_id=request.conversation_id,
#             user_key=getattr(request, "user_key", None)
#         )

#         sources = []
#         for r in results:
#             payload = getattr(r, "payload", {}) or {}
#             sources.append({
#                 "id": str(getattr(r, "id", "")),
#                 "score": getattr(r, "score", None),
#                 "text": payload.get("text"),
#                 "doc_id": payload.get("doc_id"),
#                 "title": payload.get("title"),
#                 "heading": payload.get("heading"),
#                 "date": payload.get("date"),
#                 "tags": payload.get("tags"),
#                 "keywords": payload.get("keywords"),
#                 "source_file": payload.get("source_file"),
#             })

#         return {
#             "answer": rag_result["answer"],
#             "sources": sources,
#             "query": request.query,
#             "search_mode": search_mode,
#             "conversation_id": rag_result["conversation_id"]
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"/api/queryHistory failed: {str(e)}")
# @app.post("/api/querySummeryHistory", response_model=QueryResponseHistory)
# def api_querySummeryHistory(
#     request: QueryRequestWithHistory,
#     background_tasks: BackgroundTasks  # 1. Add BackgroundTasks to API inputs
# ):
#     try:
#         print("\n⏱️ === Operation Timing Start ===")
#         start_total = time.time()

#         start = time.time()
#         query_vector = embed_query(request.query)
#         print(f"1️⃣ First embedding generation time: {time.time() - start:.2f} seconds")

#         start = time.time()
#         if request.use_hybrid:
#             results = hybrid_search(request.query, request.limit, request.filters)
#             search_mode = "hybrid"
#         else:
#             results = search(query_vector, request.limit, request.filters)
#             search_mode = "dense"
#         print(f"2️⃣ Qdrant search execution time ({search_mode}): {time.time() - start:.2f} seconds")

#         start = time.time()
#         rag_result = answer_with_rag_with_summary(
#             query=request.query,
#             results=results,
#             background_tasks=background_tasks,  # Pass background tasks manager
#             temperature=request.temperature,
#             conversation_id=request.conversation_id,
#             user_key=getattr(request, "user_key", None)
#         )
#         print(f"3️⃣ RAG execution, SQL DB load + LLM time: {time.time() - start:.2f} seconds")

#         start = time.time()
#         sources = []
#         for r in results:
#             payload = getattr(r, "payload", {}) or {}
#             sources.append({
#                 "id": str(getattr(r, "id", "")),
#                 "score": getattr(r, "score", None),
#                 "text": payload.get("text", "")[:200] + "...",
#                 "doc_id": payload.get("doc_id"),
#                 "title": payload.get("title"),
#                 "heading": payload.get("heading"),
#                 "date": payload.get("date"),
#                 "tags": payload.get("tags"),
#                 "keywords": payload.get("keywords"),
#                 "source_file": payload.get("source_file"),
#             })
#         print(f"4️⃣ Output sources formatting time: {time.time() - start:.2f} seconds")

#         print(f"Total Time: {time.time() - start_total:.2f} seconds")
#         print("⏱️ === Operation Timing End ===\n")

#         return {
#             "answer": rag_result["answer"],
#             "sources": sources,
#             "query": request.query,
#             "search_mode": search_mode,
#             "conversation_id": rag_result["conversation_id"]
#         }

#     except HTTPException as e:
#         print(f"HTTPException Get! {e} ")
#         raise
#     except Exception as e:
#         print(f"Exception Get2! {e} ")
#         raise HTTPException(status_code=500, detail=f"Request processing failed: {str(e)}")
# #https://gapgpt.app/api/v1/get_chat/token/0c48c8c8-f054-420b-ae8f-070479e92789
      

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
   
