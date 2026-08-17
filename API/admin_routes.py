from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials

from   RAG_Management.vectorstore import get_client

from RAG_Management.ingestion import InsertDocsToSql,LogStatus

from RAG_Management.ingestion import DeleteDocPipLine, ingest, ingestQdrant, RebuildSparse, reset_rag, delete_doc_chunks,InsertDocsPipeLine,COLLECTION_NAME
import logging
# from ingestion import COLLECTION_NAME
#print("--- LOADING ADMIN_ROUTES ---")
import traceback # حتماً این بالا باشد
####################
import sys
import traceback
from datetime import datetime, time


def exception_handler(exception_type, exception, traceback_obj):
    print("--- FATAL ERROR DETECTED ---")
    traceback.print_exception(exception_type, exception, traceback_obj)

sys.excepthook = exception_handler
#################################



logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["02-Admin / Vector Store Management"])

ingest_progress = {"status": "idle", "message": "No task running"}

def run_ingest_safely():
    global ingest_progress
    ingest_progress["status"] = "running"
    ingest_progress["message"] = "Ingesting data from DB..."
    try:
        # صدا زدن تابع اصلی از فایل ingestion.py
        ingest()
        ingest_progress["status"] = "success"
        ingest_progress["message"] = "Full ingestion completed successfully."
    except Exception as e:
        ingest_progress["status"] = "error"
        ingest_progress["message"] = f"Failed: {str(e)}"

@router.post("/ingest-all")
async def trigger_full_ingest(background_tasks: BackgroundTasks):
    if ingest_progress["status"] == "running":
        return {"message": "A task is already running. Please wait."}

    background_tasks.add_task(ingest())
    return {"message": "Full ingestion started in background."}

@router.get("/ingest-status")
async def get_ingest_status():
    """از این API برای چک کردن وضعیت نهایی استفاده کن"""
    return ingest_progress
@router.post("/ingest/{doc_id}")
async def ingest_single_doc(doc_id: int, background_tasks: BackgroundTasks):
    """اینجست یک سند خاص بر اساس شناسه دیتابیس"""
    # توجه: تابع ingestQdrant در فایل شما تعریف شده بود
    background_tasks.add_task(ingestQdrant, doc_id)
    return {"message": f"Ingestion for doc_id {doc_id} started."}

@router.post("/rebuild-sparse")
async def rebuild_sparse_index(background_tasks: BackgroundTasks):
    """بازسازی مدل BM25 و اندیس‌های Sparse"""
    background_tasks.add_task(RebuildSparse)
    return {"message": "Sparse index rebuild started."}

@router.delete("/delete/{doc_id}")
async def delete_document(doc_id: int):
    """حذف چانک‌های مربوط به یک سند از وکتور استور"""
    try:
        qdrant = get_client()
        DeleteDocPipLine(doc_id)
        return {"message": f"Document {doc_id} deleted from vector store."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-store")
async def reset_vector_store():
    """پاکسازی کامل وکتور استور و فایل‌های مدل (خطرناک)"""
    error_message = None
    try:
        qdrant = get_client()
        result=reset_rag(qdrant)
        print("resultresultresultresultresultresultresultresult",flush=True)
        print(result,flush=True)
        if result==1:
            # ثبت لاگ موفقیت
            LogStatus(
            _DocID=0,
            _ActionName='ResetVectorStore',
            _FileName='ALL',
            _Step='ResetVectorStore',
            _Status='success',
            _ErrorMessage=None,
            _Timestamp=None 
        )
        else:
            # ثبت لاگ عدم موفقیت
            LogStatus(
            _DocID=0,
            _ActionName='ResetVectorStore',
            _FileName='ALL',
            _Step='ResetVectorStore',
            _Status='Fail',
            _ErrorMessage=None,
            _Timestamp=None 
        )
        return {"message": "Vector store and RAG states have been reset."}
    except Exception as e:
        error_message=str(e)
        LogStatus(
            _DocID=0,
            _ActionName='ResetVectorStore',
            _FileName='ALL',
            _Step='ResetVectorStore',
            _Status='Fail',
            _ErrorMessage=error_message,
            _Timestamp=None
        )  
@router.get("/stats")
async def get_vector_store_stats():
    """دریافت وضعیت و تعداد پوینت‌های موجود در کالکشن"""
    try:
        qdrant = get_client()

        collection_info = qdrant.get_collection(collection_name=COLLECTION_NAME)
        return {
            "collection_name": COLLECTION_NAME,
            "points_count": collection_info.points_count,
            "status": collection_info.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest-file")
async def ingest_document_by_path(file_path: str, background_tasks: BackgroundTasks):
    """ثبت در SQL و بلافاصله پردازش وکتورها (مطابق ساختار حذف)"""
    try:
      

        error_message = None
        Doc_id = -1
        try:
            print(file_path)
            Doc_id=InsertDocsToSql(file_path)

        except Exception as e:
            # اگر InsertDocsToSql خطا داد
            Doc_id = -1
            error_message = str(e)
            
        if Doc_id ==-1:#Doc_id!= -1:

          
            print(f"❌ Error: {error_message}", flush=True)
            LogStatus(
                _DocID=-1,
                _ActionName='Insert',
                _FileName=file_path,
                _Step='starting',
                _Status='FAILED',
                _ErrorMessage="Error in insert to document",
                _Timestamp=None#datetime.now()
            )

            return -1

         # اگر بدون خطا بود
        LogStatus(
            _DocID=Doc_id,
            _ActionName='Insert',
            _FileName=file_path,
            _Step='Starting',
            _Status='Success',
            _ErrorMessage=error_message,
            _Timestamp=None#datetime.now()

            )
        #return Doc_id

        background_tasks.add_task( InsertDocsPipeLine, file_path,Doc_id)

        return {
            "message": f"Document with ID:{Doc_id}  has been successfully processed and stored in SQL and Qdrant.",

        }
        # return {
        #     "status": "processing",
        #     "DocID": Doc_id,
        #     "message": f"Document with ID:{Doc_id} is being processed in the background (doing)."
        # }

    except Exception as e:
        error_message = str(e)
        LogStatus(
                _DocID=-1,
                _ActionName='Insert',
                _FileName=file_path,
                _Step='starting',
                _Status='FAILED',
                _ErrorMessage=error_message,
                _Timestamp=None#datetime.now()
            )
        logger.error(f"Ingestion failed for {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

