from __future__ import annotations

import asyncio
import json
import os
from queue import Queue
import queue
from threading import Thread
from typing import Any, Optional, Tuple
import uuid
import time
import datetime
from SQlDB.QueryDB import updateClarifyMessage
from agent.dashboard_agent import DashboardAgent
from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from qdrant_client import QdrantClient
from config import EMBED_MODEL, LLM_MODEL, OPENAI_API_KEY, provider_URL
from Models.mainModels import QueryRequestStream, QueryRequestStreamٌwithConversionId
from SQlDB.db import DatabaseConnection
from SQlDB.wallet import InsertIntoWallet
from config import QDRANT_HOST, QDRANT_PORT

from SQlDB.dbManagement import SQL_SERVER_CONNECTION_STRING,get_recent_history, save_message
from Utility.log import append_qa_to_file
from providers.factory import create_provider

from agent.chat_agent import ChatAgent
from agent.document_agent import DocumentAgent
from agent.router import RouterAgent
from service.rag_service import RAGService
from Utility.StreamUnmasker import StreamUnmasker

router = APIRouter(
    prefix="/api",
    tags=["query"],
)


STREAM_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

 
# def get_recent_history(
        
#         conversation_id: str,
#         query:str,
#         user_key:str,
#         limit: int = 6
#     ):
#         conversation_id, is_new_chat = normalize_conversation_id(conversation_id)

        
#         with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
#             if not is_new_chat:
#                 cursor.execute(
#                     "SELECT 1 FROM dbo.Conversations WHERE chatId = ?",
#                     (conversation_id,)
#                 )
#                 if not cursor.fetchone():
#                     is_new_chat = True


#             if is_new_chat:
#                 conversation_id=save_conversation(
#                     cursor=cursor,
#                     conversation_id=conversation_id,
#                     title=query,
#                     user_key=user_key,
#                     model_id=1
#                 )

#             history = get_conversation_history(
#                 cursor=cursor,
#                 conversation_id=conversation_id,
#                 limit=6
#             )

#             save_message(
#                 cursor=cursor,
#                 conversation_id=conversation_id,
#                 role="user",
#                 content=query
#             )
#             # "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
#             return history,conversation_id

def build_router_agent() -> RouterAgent:
    """
    ساخت کامل Provider، Qdrant، RAGService و Agentها.
    """

    provider = create_provider(
        provider_name="openai",
        #base_uri="https://api.gapgpt.app/v1",
        base_uri=provider_URL,
        api_key=OPENAI_API_KEY,
        model=LLM_MODEL,
        embed_model=EMBED_MODEL,
    )

    if not QDRANT_HOST:
        raise RuntimeError(
            "QDRANT_HOST is not configured"
        )

    if not QDRANT_PORT:
        raise RuntimeError(
            "QDRANT_PORT is not configured"
        )

    qdrant_client = QdrantClient(
        host=QDRANT_HOST,
        port=int(QDRANT_PORT),
    )

    rag_service = RAGService(
        llm=provider,
        qdrant_client=qdrant_client,
    )

    chat_agent = ChatAgent(
        llm=provider,
    )

    document_agent = DocumentAgent(
        llm_provider=provider,
        rag_service=rag_service,
    )
    # dashboard_llm_service=dashboard_llm_service(llm=provider)
    dashboard_agent=DashboardAgent(llm_provider=provider)
    return RouterAgent(
        llm=provider,
        chat_agent=chat_agent,
        document_agent=document_agent,
        dashboard_agent=dashboard_agent
    )


# یک نمونه مشترک برای API
router_agent = build_router_agent()
VAULT_FILE_PATH = os.getenv("VAULT_FILE_PATH", "/app/Data/1-IT0410-517-04_SamanSoft_Win10/1_vault.json")

# @router.post("/StreamQueryHistory")
# async def stream_queryHistory_endpoint(
#     request: QueryRequestStreamٌwithConversionId,
#     background_tasks: BackgroundTasks
# ):
#     user_key='9a6b7ba9-abfe-4207-97fe-02a1da750cb7'
#     history,c_id= get_recent_history( conversation_id= request.conversation_id,
#                 query=request.query,
#                 user_key=user_key,
#                 limit = 10)

#     chunks: Queue[Any] = Queue()
    
#     def on_chunk(chunk: Any) -> None:    
#         chunks.put(chunk)

#     def produce() -> None:
#         try:
#             router_agent.handle_stream(
#                 query=request.query,
#                 convertionId=c_id,
#                 on_chunk=on_chunk,
#                 history=history,
#                 temperature=request.temperature,           
#             )

#         except Exception as error:
#             chunks.put(
#                 {
#                     "type": "error",
#                     "error": str(error),
#                 }
#             )

#         finally:
#             # علامت پایان stream
#             chunks.put(None)

#     # شروع تولید پاسخ در پس‌زمینه
#     Thread(
#         target=produce,
#         daemon=True,
#     ).start()

#     def event_stream():
        
#         """
#         تبدیل chunkهای صف به فرمت SSE با تفکیک نوع رویداد.
#         """
#         unmasker = StreamUnmasker(vault_path=VAULT_FILE_PATH)
#         answer_parts = []
#         final_usage = {}
#         final_response_id = None
#         while True:
#             chunk = chunks.get()

#             # پایان stream
#             if chunk is None:
#                 break

#             # ۱. مدیریت خطاها
#             if isinstance(chunk, dict) and chunk.get("type") == "error":
#                 yield (
#                     "event: error\n"
#                     f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
#                 )
#                 continue
#             if isinstance(chunk, dict) and chunk.get("type") == "source_chunks":
           
#                 continue
#             # ۲. تفکیک متادیتا و Usage (ارسالی از openai_provider)
#             if isinstance(chunk, dict) and chunk.get("type") == "meta":             
#                 final_response_id = chunk.get("response_id")
#                 final_usage = chunk.get("usage", {}) # دریافت دیکشنری usage
#                 meta_payload = {
#                     **chunk,
#                     "conversation_id": c_id,}
#                 yield ("event: meta\n"f"data: {json.dumps(meta_payload, ensure_ascii=False)}\n\n")
#                 continue
#             # ۳. مدیریت توکن‌های متنی (Tokens)
#             if isinstance(chunk, dict) and chunk.get("type") == "token":
#                 # text = chunk.get("content", "")
#                 # answer_parts.append(text)
#                 # payload = {"text": chunk.get("content", "")}
#                 content = data.get("content", "")
#                 # برای تاریخچه (History) نسخه خام را نگه می‌داریم تا دیتای حساس به LLM در پرامپت‌های بعدی نرسد
#                 answer_parts.append(content)
#                 # جایگزینی توکن‌ها روی استریم ارسالی به فرانت‌اند
#                 unmasked_content = unmasker.feed(content)
#                 if unmasked_content:
#                     yield (
#                         f"event: token\n"
#                         f"data: {json.dumps({'content': unmasked_content}, ensure_ascii=False)}\n\n"
#                     )
#             elif isinstance(chunk, dict): 
#                 text = chunk.get("text")
#                 if text:
#                     answer_parts.append(str(text))
#                     payload = chunk
           
#             else:
              
#                 text = str(chunk)
#                 answer_parts.append(text)
#                 payload = {"text": text}

#             yield (
#                 "event: token\n"
#                 f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
#             )
#         final_answer = "".join(answer_parts).strip()
      
#         with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
#                 save_message(
#                     cursor=cursor,
#                     conversation_id=c_id,
#                     role="assistant",
#                     content=final_answer,
#                     provider_response_id="1111"
#                 )
#     # ذخیره سؤال و جواب در فایل
#         try:         
#             append_qa_to_file(request.query            
#         )
#             append_qa_to_file(
#                         final_answer                            
#                     )
#         except Exception as e:
#             print(f"Failed to save QA log: {e}", flush=True)    
#         if final_usage and final_response_id:
            
#             background_tasks.add_task(
#                 InsertIntoWallet,
#                 final_usage.get("total_tokens", 0) * -1,
#                 final_usage.get("output_tokens", 0), # output_tokens
#                 final_usage.get("input_tokens", 0),     # input_tokens
#                 user_key,
#                 final_response_id
#             )                              
#         # ارسال پایان قطعی استریم
#         yield "event: done\ndata: [DONE]\n\n"
#     return StreamingResponse(
#         event_stream(),
#         media_type="text/event-stream",
#         headers=STREAM_HEADERS,
#     )

@router.post("/StreamQueryHistory")
async def stream_queryHistory_endpoint(
    request: QueryRequestStreamٌwithConversionId,
    background_tasks: BackgroundTasks
):
    user_key = '9a6b7ba9-abfe-4207-97fe-02a1da750cb7'
    append_qa_to_file(f"VAULT_FILE_PATH:{VAULT_FILE_PATH}\n")
    history, c_id = get_recent_history(
        conversation_id=request.conversation_id,
        query=request.query,
        user_key=user_key,
        limit=10
    )
    chunks: Queue[Any] = Queue()
    def on_chunk(chunk: Any) -> None:    
        chunks.put(chunk)
    def produce() -> None:
        try:
            router_agent.handle_stream(
                query=request.query,
                convertionId=c_id,
                on_chunk=on_chunk,
                history=history,
                temperature=request.temperature,           
            )
        except Exception as error:
            chunks.put(
                {
                    "type": "error",
                    "error": str(error),
                }
            )
        finally:
            # علامت پایان stream
            chunks.put(None)
    # شروع تولید پاسخ در پس‌زمینه
    Thread(
        target=produce,
        daemon=True,
    ).start()
    def event_stream():
        """
        تبدیل chunkهای صف به فرمت SSE با تفکیک نوع رویداد و Unmask آنی.
        """
        unmasker = StreamUnmasker(vault_path=VAULT_FILE_PATH)
        answer_parts = []
        final_usage = {}
        final_response_id = None

        while True:
            chunk = chunks.get()

            # پایان stream
            if chunk is None:
                break

            # ۱. مدیریت خطاها
            if isinstance(chunk, dict) and chunk.get("type") == "error":
                yield (
                    "event: error\n"
                    f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                )
                continue

            # چانک‌های سورس داخلی
            if isinstance(chunk, dict) and chunk.get("type") == "source_chunks":
                continue

            # ۲. تفکیک متادیتا و Usage
            if isinstance(chunk, dict) and chunk.get("type") == "meta":             
                final_response_id = chunk.get("response_id")
                final_usage = chunk.get("usage", {})
                meta_payload = {
                    **chunk,
                    "conversation_id": c_id,
                }
                yield (
                    "event: meta\n"
                    f"data: {json.dumps(meta_payload, ensure_ascii=False)}\n\n"
                )
                continue

            # ۳. مدیریت توکن‌های متنی استاندارد (Tokens)
            if isinstance(chunk, dict) and chunk.get("type") == "token":
                content = chunk.get("content", "")
                
                # برای تاریخچه (History) نسخه خام را نگه می‌داریم تا دیتای حساس در DB ذخیره نشود
                answer_parts.append(content)

                # جایگزینی توکن‌ها روی استریم ارسالی به کلاینت
                unmasked_content = unmasker.feed(content)
                if unmasked_content:
                    yield (
                        "event: token\n"
                        f"data: {json.dumps({'content': unmasked_content}, ensure_ascii=False)}\n\n"
                    )
                continue

            # ۴. مدیریت سایر فرمت‌های دیکشنری (fallback)
            elif isinstance(chunk, dict): 
                text = str(chunk.get("text", ""))
                if text:
                    answer_parts.append(text)
                    unmasked_text = unmasker.feed(text)
                    if unmasked_text:
                        yield (
                            "event: token\n"
                            f"data: {json.dumps({'text': unmasked_text}, ensure_ascii=False)}\n\n"
                        )
                continue

            # ۵. چانک‌های رشته‌ای خام (fallback)
            else:
                text = str(chunk)
                answer_parts.append(text)
                unmasked_text = unmasker.feed(text)
                if unmasked_text:
                    yield (
                        "event: token\n"
                        f"data: {json.dumps({'text': unmasked_text}, ensure_ascii=False)}\n\n"
                    )

        # تخلیه باقیمانده بافر unmasker در پایان استریم
        remaining = unmasker.flush()
        if remaining:
            yield (
                "event: token\n"
                f"data: {json.dumps({'content': remaining}, ensure_ascii=False)}\n\n"
            )

        # متن خام برای ذخیره در دیتابیس (بدون دیتای حساس)
        final_answer = "".join(answer_parts).strip()
      
        with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
            save_message(
                cursor=cursor,
                conversation_id=c_id,
                role="assistant",
                content=final_answer,
                provider_response_id="1111"
            )

        # ذخیره سؤال و جواب در فایل لاگ
        try:         
            append_qa_to_file(request.query)
            append_qa_to_file(final_answer)
        except Exception as e:
            print(f"Failed to save QA log: {e}", flush=True)    

        if final_usage and final_response_id:
            background_tasks.add_task(
                InsertIntoWallet,
                final_usage.get("total_tokens", 0) * -1,
                final_usage.get("output_tokens", 0),
                final_usage.get("input_tokens", 0),
                user_key,
                final_response_id
            )                              

        # ارسال سیگنال پایان قطعی استریم
        yield "event: done\ndata: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=STREAM_HEADERS,
    )

@router.post("/QueryHistory")
async def query_history_endpoint(
    request: QueryRequestStreamٌwithConversionId,
    background_tasks: BackgroundTasks
):
   
    user_key = '9a6b7ba9-abfe-4207-97fe-02a1da750cb7'
    start = time.time()
    append_qa_to_file(f"===================================================")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_qa_to_file(
                question=request.query         
            )
    append_qa_to_file(f"Time: {timestamp}\n")
      # f.write()
                # f.write(f"Time: {timestamp}\n")
    history, c_id = get_recent_history(
        conversation_id=request.conversation_id,
        query=request.query,
        user_key=user_key,
        limit=3
    )
    append_qa_to_file(f"GetHistory Time: {time.time() - start:.2f} seconds")
    answer_parts = []
    final_usage = {}
    final_response_id = "1111"#شناسه پیش‌فرض پاسخ
    sql_query = None
    source_payload = {"chunks": [], "conversation_id": c_id}#برای نگه‌داشتن chunkهای منبع و conversation_id

    def on_chunk(chunk: Any) -> None:
        nonlocal final_usage, final_response_id, source_payload,sql_query#اینها توسط on_chunk میتوانند تغییر کنن

        if not isinstance(chunk, dict):
            return

        if chunk.get("type") == "token":
            content = chunk.get("content", "")
            if content:
                answer_parts.append(content)
        # elif isinstance(chunk, dict) and chunk.get("type") == "clarify":
        #         content = chunk.get("content", "")
        #         if content:
        #             answer_parts.append(content)
                
        elif chunk.get("type") == "sql":
            sql_query = chunk.get("content", "")
        
        elif chunk.get("type") == "meta":
            final_usage = chunk.get("usage", {})
            final_response_id = chunk.get("response_id", final_response_id)

        elif chunk.get("type") == "source_chunks":
            source_payload = {
                "chunks": chunk.get("chunks", []),
                "conversation_id": c_id,
            }

    try:
        router_agent.handle_stream(
            query=request.query,
            convertionId=c_id,
            on_chunk=on_chunk,
            history=history,
            temperature=request.temperature,
        )
    except Exception as error:
        return {"status": "error", "message": str(error)}

    final_answer = "".join(answer_parts).strip()

    try:
        with DatabaseConnection(SQL_SERVER_CONNECTION_STRING) as cursor:
            save_message(
                cursor=cursor,
                conversation_id=c_id,
                role="assistant",
                content=final_answer,
                provider_response_id=final_response_id
            )
    except Exception as e:
        print(f"Database save error: {e}", flush=True)

    try:
       
        append_qa_to_file(
                    question=final_answer                
                )
        append_qa_to_file(f"TotalTime: {time.time() - start:.2f} seconds")
    except Exception as e:
        print(f"Failed to save QA log: {e}", flush=True)

    if final_usage:
        background_tasks.add_task(
            InsertIntoWallet,
            final_usage.get("total_tokens", 0) * -1,
            final_usage.get("output_tokens", 0),
            final_usage.get("input_tokens", 0),
            user_key,
            final_response_id
        )

    return {
        "status": "success",
        "conversation_id": c_id,
        "answer": final_answer,
        "sql": sql_query,
        "usage": final_usage,
        "response_id": final_response_id,
        "source": source_payload
    }
