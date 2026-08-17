import json
import sys
import time
import traceback



from fastapi import Depends, FastAPI, HTTPException

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi_swagger import patch_fastapi

from API.admin_routes import router as admin_router

from Models.mainModels import BulkChargeRequest, QueryRequest, QueryRequestStream, QueryRequestWithHistory, QueryResponse, QueryResponseHistory, SearchResult
from LLM.OpenAIManagment import detect_intent, embed_query, rerank_results
from RAG_Management.QdrantManagment import checkQudrant, hybrid_search, init_history_collection, search
from RAG_Management.answerWithRAG import answer_general_stream, answer_stream_only_llm, answer_with_rag, answer_with_rag_WithImage, answer_with_rag_stream, answer_with_rag_with_summary, answer_with_rag_withHistory, answer_with_rag_withHistoryAndVectorDB
from SQlDB.IngestionQuery import bulk_charge_transactions
from SQlDB.wallet import InsertIntoWallet
from Utility.utiliy import  get_current_user_payload
from RAG_Management.bm25 import PersianBM25Encoder
import uvicorn
# import os
from config import LLM_MODEL, OPENAI_API_KEY
from RAG_Management.ingestion import ingest  
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from fastapi import BackgroundTasks
from typing import Tuple
import uuid
from jose import  JWTError, ExpiredSignatureError  
from API.Wallet_routes import router as wallet_router
from API.dashboard_question_api import router as DashboardDaftar_router
from API.query_routes import router as query_router
import json
import uuid
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from score.caculate_score_final import normalize_results,rerank_and_cut
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
from pathlib import Path, PureWindowsPath

BASE_DIR = Path(__file__).resolve().parent # تعریف مسیر پایه پروژه
MEDIA_ROOT = BASE_DIR / "data"  # مسیر دقیق پوشه داده‌ها

app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")
app.include_router(admin_router)
app.include_router(wallet_router)
app.include_router(DashboardDaftar_router)
app.include_router(query_router)
# ایجاد کالکشن تاریخچه اگر وجود نداشته باشد
init_history_collection()
from fastapi import BackgroundTasks


def search_documents(request: QueryRequest):
    if request.use_hybrid:
        results = hybrid_search(
            query=request.query,
            limit=request.limit,
            filters=request.filters
        )
        search_mode = "hybrid"
    else:
        query_vector = embed_query(request.query)

        results = search(
            query_vector=query_vector,
            limit=request.limit,
            filters=request.filters
        )
        search_mode = "dense"

    if not results:
        raise HTTPException(
            status_code=404,
            detail="هیچ سند مرتبطی یافت نشد"
        )

    return results, search_mode
def build_sources(results):
    sources = []

    for result in results:
        if isinstance(result, dict):
            payload = result["payload"]
            result_id = result["id"]
            score = result["score"]
        else:
            payload = result.payload
            result_id = result.id
            score = result.score

        text = payload.get("text", "")

        sources.append(
            SearchResult(
                id=str(result_id),
                score=score,
                text=text[:200] + ("..." if len(text) > 200 else ""),
                doc_id=payload.get("doc_id"),
                title=payload.get("title"),
                heading=payload.get("heading"),
                date=payload.get("date"),
                tags=payload.get("tags"),
                keywords=payload.get("keywords"),
                source_file=payload.get("source_file")
            )
        )

    return sources
 
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
@app.post("/api/queryHistoryWithVectorDB", response_model=QueryResponseHistory)
async def api_queryHistoryWithVectorDB(request: QueryRequestWithHistory,
                         background_tasks: BackgroundTasks):
    try:
        query_vector = embed_query(request.query)

        if request.use_hybrid:
            results = hybrid_search(request.query, request.limit, request.filters)
            search_mode = "hybrid"
        else:
            results = search(query_vector, request.limit, request.filters)
            search_mode = "dense"

        rag_result = answer_with_rag_withHistoryAndVectorDB(
            query=request.query,
            results=results,
            background_tasks=background_tasks,
            temperature=request.temperature,
            conversation_id=request.conversation_id,
            user_key=getattr(request, "user_key", None)
        )

        sources = []
        for r in results:
            payload = getattr(r, "payload", {}) or {}
            sources.append({
                "id": str(getattr(r, "id", "")),
                "score": getattr(r, "score", None),
                "text": payload.get("text"),
                "doc_id": payload.get("doc_id"),
                "title": payload.get("title"),
                "heading": payload.get("heading"),
                "date": payload.get("date"),
                "tags": payload.get("tags"),
                "keywords": payload.get("keywords"),
                "source_file": payload.get("source_file"),
            })

        return {
            "answer": rag_result["answer"],
            "sources": sources,
            "query": request.query,
            "search_mode": search_mode,
            "conversation_id": rag_result["conversation_id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"/api/queryHistory failed: {str(e)}")
@app.post("/api/queryHistory", response_model=QueryResponseHistory)
async def api_queryHistory(request: QueryRequestWithHistory):
    try:
        query_vector = embed_query(request.query)

        if request.use_hybrid:
            results = hybrid_search(request.query, request.limit, request.filters)
            search_mode = "hybrid"
        else:
            results = search(query_vector, request.limit, request.filters)
            search_mode = "dense"

        rag_result = answer_with_rag_withHistory(
            query=request.query,
            results=results,
            temperature=request.temperature,
            conversation_id=request.conversation_id,
            user_key=getattr(request, "user_key", None)
        )

        sources = []
        for r in results:
            payload = getattr(r, "payload", {}) or {}
            sources.append({
                "id": str(getattr(r, "id", "")),
                "score": getattr(r, "score", None),
                "text": payload.get("text"),
                "doc_id": payload.get("doc_id"),
                "title": payload.get("title"),
                "heading": payload.get("heading"),
                "date": payload.get("date"),
                "tags": payload.get("tags"),
                "keywords": payload.get("keywords"),
                "source_file": payload.get("source_file"),
            })

        return {
            "answer": rag_result["answer"],
            "sources": sources,
            "query": request.query,
            "search_mode": search_mode,
            "conversation_id": rag_result["conversation_id"]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"/api/queryHistory failed: {str(e)}")

@app.post("/api/querySummeryHistory", response_model=QueryResponseHistory)
def api_querySummeryHistory(
    request: QueryRequestWithHistory,
    background_tasks: BackgroundTasks  # 1. Add BackgroundTasks to API inputs
):
    try:
        print("\n⏱️ === Operation Timing Start ===")
        start_total = time.time()

        start = time.time()
        query_vector = embed_query(request.query)
        print(f"1️⃣ First embedding generation time: {time.time() - start:.2f} seconds")

        start = time.time()
        if request.use_hybrid:
            results = hybrid_search(request.query, request.limit, request.filters)
            search_mode = "hybrid"
        else:
            results = search(query_vector, request.limit, request.filters)
            search_mode = "dense"
        print(f"2️⃣ Qdrant search execution time ({search_mode}): {time.time() - start:.2f} seconds")

        start = time.time()
        rag_result = answer_with_rag_with_summary(
            query=request.query,
            results=results,
            background_tasks=background_tasks,  # Pass background tasks manager
            temperature=request.temperature,
            conversation_id=request.conversation_id,
            user_key=getattr(request, "user_key", None)
        )
        print(f"3️⃣ RAG execution, SQL DB load + LLM time: {time.time() - start:.2f} seconds")

        start = time.time()
        sources = []
        for r in results:
            payload = getattr(r, "payload", {}) or {}
            sources.append({
                "id": str(getattr(r, "id", "")),
                "score": getattr(r, "score", None),
                "text": payload.get("text", "")[:200] + "...",
                "doc_id": payload.get("doc_id"),
                "title": payload.get("title"),
                "heading": payload.get("heading"),
                "date": payload.get("date"),
                "tags": payload.get("tags"),
                "keywords": payload.get("keywords"),
                "source_file": payload.get("source_file"),
            })
        print(f"4️⃣ Output sources formatting time: {time.time() - start:.2f} seconds")

        print(f"Total Time: {time.time() - start_total:.2f} seconds")
        print("⏱️ === Operation Timing End ===\n")

        return {
            "answer": rag_result["answer"],
            "sources": sources,
            "query": request.query,
            "search_mode": search_mode,
            "conversation_id": rag_result["conversation_id"]
        }

    except HTTPException as e:
        print(f"HTTPException Get! {e} ")
        raise
    except Exception as e:
        print(f"Exception Get2! {e} ")
        raise HTTPException(status_code=500, detail=f"Request processing failed: {str(e)}")
#https://gapgpt.app/api/v1/get_chat/token/0c48c8c8-f054-420b-ae8f-070479e92789
@app.post("/api/queryScore", response_model=QueryResponse)
async def queryScore_endpoint(request: QueryRequest):
    """
    پردازش سوال فنی و بازگشت پاسخ RAG-based

    - **query**: سوال فنی تکنسین
    - **limit**: تعداد اسناد مرتبط (پیش‌فرض: 5)
    - **temperature**: دمای مدل (پیش‌فرض: 0.1)
    - **use_hybrid**: استفاده از hybrid search (dense + sparse)
    - **filters**: فیلترهای metadata (doc_ids, tags, keywords, date)
    """
    try:
        # انتخاب نوع جستجو
        if request.use_hybrid:
            results = hybrid_search(
                query=request.query,
                limit=request.limit,
                filters=request.filters
            )
            search_mode = "hybrid"
        else:
            query_vector = embed_query(request.query)
            results = search(
                query_vector=query_vector,
                limit=request.limit,
                filters=request.filters
            )
            print("QrantResult:  ",type(results))
            search_mode = "dense"
  
        if not results:
            raise HTTPException(
                status_code=404,
                detail="هیچ سند مرتبطی یافت نشد"
            )
        normalized = normalize_results(results)

        # rerank و انتخاب 5 تای برتر
        scored_results = rerank_and_cut(query=request.query, results=normalized, top_k=5)
        # تولید پاسخ
        answer = answer_with_rag(request.query, scored_results, temperature=request.temperature)

        # فرمت sources با metadata
        sources = []
        for r in scored_results:

            if isinstance(r, dict):
                payload = r["payload"]
                rid = r["id"]
                score = r["score"]
                score_diff=r["score_diff"]
            else:
                payload = r.payload
                rid = r.id
                score = r.score
                score_diff=r["score_diff"]
            sources.append(
                SearchResult(
                    id=str(rid),
                    score=score,
                    score_diff=score_diff,
                    text=payload.get("text", "")[:200] + "...",
                    doc_id=payload.get("doc_id"),
                    title=payload.get("title"),
                    heading=payload.get("heading"),
                    date=payload.get("date"),
                    tags=payload.get("tags"),
                    keywords=payload.get("keywords"),
                    source_file=payload.get("source_file")
                )
            )

        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            search_mode=search_mode
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطا در پردازش درخواست: {str(e)}"
        )
#https://gapgpt.app/api/v1/get_chat/token/0c48c8c8-f054-420b-ae8f-070479e92789
@app.post("/api/query1", response_model=QueryResponse)
async def query1_endpoint(request: QueryRequest):
    """
    پردازش سوال فنی و بازگشت پاسخ RAG-based

    - **query**: سوال فنی تکنسین
    - **limit**: تعداد اسناد مرتبط (پیش‌فرض: 5)
    - **temperature**: دمای مدل (پیش‌فرض: 0.1)
    - **use_hybrid**: استفاده از hybrid search (dense + sparse)
    - **filters**: فیلترهای metadata (doc_ids, tags, keywords, date)
    """
    try:
        # انتخاب نوع جستجو
        if request.use_hybrid:
            results = hybrid_search(
                query=request.query,
                limit=request.limit,
                filters=request.filters
            )
            search_mode = "hybrid"
        else:
            query_vector = embed_query(request.query)
            results = search(
                query_vector=query_vector,
                limit=request.limit,
                filters=request.filters
            )
            print("QrantResult:  ",type(results))
            search_mode = "dense"
  
        if not results:
            raise HTTPException(
                status_code=404,
                detail="هیچ سند مرتبطی یافت نشد"
            )

        # تولید پاسخ
        answer = answer_with_rag(request.query, results, temperature=request.temperature)

        # فرمت sources با metadata
        sources = []
        for r in results:

            if isinstance(r, dict):
                payload = r["payload"]
                rid = r["id"]
                score = r["score"]
            else:
                payload = r.payload
                rid = r.id
                score = r.score

            sources.append(
                SearchResult(
                    id=str(rid),
                    score=score,
                    text=payload.get("text", "")[:200] + "...",
                    doc_id=payload.get("doc_id"),
                    title=payload.get("title"),
                    heading=payload.get("heading"),
                    date=payload.get("date"),
                    tags=payload.get("tags"),
                    keywords=payload.get("keywords"),
                    source_file=payload.get("source_file")
                )
            )

        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            search_mode=search_mode
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطا در پردازش درخواست: {str(e)}"
        )
@app.post("/api/queryWithRank", response_model=QueryResponse)
async def queryWithRank_endpoint(request: QueryRequest):
    """
    پردازش سوال فنی و بازگشت پاسخ RAG-based

    - **query**: سوال فنی تکنسین
    - **limit**: تعداد اسناد مرتبط (پیش‌فرض: 5)
    - **temperature**: دمای مدل (پیش‌فرض: 0.1)
    - **use_hybrid**: استفاده از hybrid search (dense + sparse)
    - **filters**: فیلترهای metadata (doc_ids, tags, keywords, date)
    """
    try:
        # انتخاب نوع جستجو
        if request.use_hybrid:
            results = hybrid_search(
                query=request.query,
                limit=request.limit,
                filters=request.filters
            )
            search_mode = "hybrid"
        else:
            query_vector = embed_query(request.query)
            results = search(
                query_vector=query_vector,
                limit=request.limit,
                filters=request.filters
            )
            print("QrantResult:  ",type(results))
            search_mode = "dense"
  
        if not results:
            raise HTTPException(
                status_code=404,
                detail="هیچ سند مرتبطی یافت نشد"
            )
        reranked_results = rerank_results(request.query, results)
        # تولید پاسخ
        answer = answer_with_rag(request.query, reranked_results, temperature=request.temperature)
         
        # فرمت sources با metadata
        sources = []
        for r in results:

            if isinstance(r, dict):
                payload = r["payload"]
                rid = r["id"]
                score = r["score"]
            else:
                payload = r.payload
                rid = r.id
                score = r.score

            sources.append(
                SearchResult(
                    id=str(rid),
                    score=score,
                    text=payload.get("text", "")[:200] + "...",
                    doc_id=payload.get("doc_id"),
                    title=payload.get("title"),
                    heading=payload.get("heading"),
                    date=payload.get("date"),
                    tags=payload.get("tags"),
                    keywords=payload.get("keywords"),
                    source_file=payload.get("source_file")
                )
            )

        return QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            search_mode=search_mode
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"خطا در پردازش درخواست: {str(e)}"
        )        
@app.post("/api/query/stream")
async def query_stream_endpoint(
    request: QueryRequestStream,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    try:
        token = credentials.credentials
        user_key = ""

        try:
            is_valid, message, user_key = get_current_user_payload(token)
            if not is_valid:
                raise HTTPException(status_code=401, detail=message)
        except ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

       
        print(token, flush=True)

   

        intent =  detect_intent(request.query)

        print("intent", flush=True)
        print(intent, flush=True)

        if intent == "general":
            return StreamingResponse(
             
                answer_general_stream(query=request.query,
                                    userKey=user_key,
                                    background_tasks=background_tasks),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        query_vector = embed_query(request.query)

        results = search(
            query_vector=query_vector,
            limit=5,
            filters=None
        )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="هیچ سند مرتبطی یافت نشد"
            )

        reranked_results = rerank_results(request.query, results)

        def event_stream():
            try:
                for chunk in answer_with_rag_stream(
                    query=request.query,
                    userKey=user_key,
                    background_tasks=background_tasks,
                    
                    results=reranked_results,
                    temperature=0.1
                ):
                    if chunk:
                        chunk_data = {
                            "text": chunk
                        }

                        yield (
                            "event: token\n"
                            f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"
                        )

                yield "event: done\ndata: [DONE]\n\n"

            except Exception as error:
                error_data = {
                    "error": str(error)
                }

                yield (
                    "event: error\n"
                    f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                )

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"خطا در جست‌وجو: {str(error)}"
        )




@app.post("/api/query/streamWithMeta2")
async def query_streamWithMeta2_endpoint(request: QueryRequestStream,background_tasks: BackgroundTasks):
    try:
        user_key = "9a6b7ba9-abfe-4207-97fe-02a1da750cb7"

        intent = detect_intent(request.query)
        print(intent, flush=True)

        if intent == "general":
            return StreamingResponse(
                answer_general_stream(request.query),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        query_vector = embed_query(request.query)
        results = search(
            query_vector=query_vector,
            limit=5,
            filters=None,
        )
        if not results:
            raise HTTPException(status_code=404, detail="هیچ سند مرتبطی یافت نشد")

        reranked_results = rerank_results(request.query, results)
        request_id = str(uuid.uuid4())

        async def event_stream():
            llm_response_id = None
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

            try:
                yield (
                    "event: request_id\n"
                    f"data: {json.dumps({'request_id': request_id}, ensure_ascii=False)}\n\n"
                )

                for chunk in answer_with_rag_stream(
                    query=request.query,
                    results=reranked_results,
                    temperature=0.1,
                ):
                    if not chunk:
                        continue

                    if chunk.get("type") == "token":
                        text = chunk.get("content", "")
                        yield (
                            "event: token\n"
                            f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
                        )

                    elif chunk.get("type") == "meta":
                        llm_response_id = chunk.get("response_id")
                        usage = chunk.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        total_tokens = usage.get("total_tokens", 0)

                yield "event: done\ndata: [DONE]\n\n"

            except Exception as error:
                yield (
                    "event: error\n"
                    f"data: {json.dumps({'error': str(error)}, ensure_ascii=False)}\n\n"
                )

            finally:
                
                    background_tasks.add_task(
                     
                                         InsertIntoWallet,
                                         total_tokens,
                                         output_tokens,
                                         input_tokens,
                                         user_key,
                                         llm_response_id,
                                     )
                   

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"خطا در جست‌وجو: {str(error)}")

@app.post("/api/QueryWithRerank_WithImage")
async def query_endpointWithRerank_WithImage(request: QueryRequest):
    print("STEP 1: endpoint entered", flush=True)

    try:
        print("STEP 2: request received", flush=True)
        print("QUERY:", request.query, flush=True)
        print("USE HYBRID:", request.use_hybrid, flush=True)

        if request.use_hybrid:
            print("STEP 3: before hybrid_search", flush=True)

            results = hybrid_search(
                query=request.query,
                limit=request.limit,
                filters=request.filters
            )

            print("STEP 4: hybrid_search completed", flush=True)
            search_mode = "hybrid"

        else:
            print("STEP 3: before dense search", flush=True)

            query_vector = embed_query(request.query)

            print("STEP 4: embedding completed", flush=True)

            results = search(
                query_vector=query_vector,
                limit=request.limit,
                filters=request.filters
            )

            print("STEP 5: dense search completed", flush=True)
            search_mode = "dense"

        print("RESULT TYPE:", type(results), flush=True)
        print("RESULT COUNT:", len(results), flush=True)

        if not results:
            print("No search results", flush=True)
            raise HTTPException(
                status_code=404,
                detail="هیچ سند مرتبطی یافت نشد"
            )

        print("STEP 6: before rerank", flush=True)

        reranked_results = rerank_results(
            request.query,
            results
        )

        print("STEP 7: rerank completed", flush=True)
        print(
            "RERANKED COUNT:",
            len(reranked_results),
            flush=True
        )

        print("STEP 8: before answer_with_rag", flush=True)
        
       

        # answer = answer_with_rag_WithImage(
        #     request.query,
        #     reranked_results,
        #     temperature=request.temperature
        # )
        answer, input_tokens, output_tokens, total_tokens, response_id = answer_with_rag_WithImage(
    request.query,
    reranked_results,
    temperature=request.temperature
)

       
        print("STEP 9: answer generated", flush=True)
        print("ANSWER TYPE:", type(answer), flush=True)
        print("ANSWER:", answer, flush=True)
        
        print("STEP 10: before response", flush=True)
        
        
       
        sources = []
        
        for r in reranked_results:
            if isinstance(r, dict):
                payload = r.get("payload", {}) or {}
                rid = r.get("id")
                score = r.get("score")
            else:
                payload = getattr(r, "payload", {}) or {}
                rid = getattr(r, "id", None)
                score = getattr(r, "score", None)
              
            
            sources.append(
                SearchResult(
                    id=str(rid) if rid is not None else "",
                    score=score,
                    text=payload.get("text", ""),
                    doc_id=payload.get("doc_id"),
                    title=payload.get("title"),
                    heading=payload.get("heading"),
                    date=payload.get("date"),
                    tags=payload.get("tags"),
                    keywords=payload.get("keywords"),
                    source_file=payload.get("source_file"),
                    
                )
            )
        return QueryResponse(
             
            answer=answer,
            
            sources=sources,
            query=request.query,
            search_mode=search_mode,
           
        )
    except HTTPException:
        print("HTTPException occurred", flush=True)
        traceback.print_exc(file=sys.stderr)
        raise

    except Exception as exc:
        print("========== FULL ERROR ==========", flush=True)
        print("ERROR TYPE:", type(exc).__name__, flush=True)
        print("ERROR MESSAGE:", str(exc), flush=True)
        traceback.print_exc(file=sys.stderr)
        print("================================", flush=True)

        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {str(exc)}"
        )
        
      

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
   
