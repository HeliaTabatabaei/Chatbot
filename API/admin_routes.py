from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials

from   RAG_Management.vectorstore import get_client

from RAG_Management.ingestion import InsertDocsToSql,LogStatus

from RAG_Management.ingestion import DeleteDocPipLine,  ingestQdrant,  reset_rag, InsertDocsPipeLine,COLLECTION_NAME
import logging

import traceback 

import sys
import traceback
from datetime import datetime, time
from pathlib import Path

from Utility.GlobalSensitiveDataMasker import GlobalSensitiveDataMasker
BASE_DIR = Path(__file__).resolve().parent.parent  # متناسب با ساختار پروژه شما
VAULT_FILE_PATH = BASE_DIR / "data" / "vault.json"
def exception_handler(exception_type, exception, traceback_obj):
   
    traceback.print_exception(exception_type, exception, traceback_obj)

sys.excepthook = exception_handler




logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["02-Admin / Vector Store Management"])

ingest_progress = {"status": "idle", "message": "No task running"}

@router.post("/ingest/{doc_id}")
async def ingest_single_doc(doc_id: int, background_tasks: BackgroundTasks):
    """اینجست یک سند خاص بر اساس شناسه دیتابیس"""
    # توجه: تابع ingestQdrant در فایل شما تعریف شده بود
    background_tasks.add_task(ingestQdrant, doc_id)
    return {"message": f"Ingestion for doc_id {doc_id} started."}

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
        try:
            masker = GlobalSensitiveDataMasker(vault_file_path=VAULT_FILE_PATH)
            masked_file_path = masker.process_file(file_path)
        except Exception as e:
            LogStatus(
                _DocID=-1,
                _ActionName='Insert',
                _FileName=file_path,
                _Step='Masking',
                _Status='FAILED',
                _ErrorMessage=str(e),
                _Timestamp=None
            )
            return -1
        error_message=None
        Doc_id=-1
        try:   
            Doc_id=InsertDocsToSql(masked_file_path)

        except Exception as e:
            # اگر InsertDocsToSql خطا داد
            Doc_id = -1
            error_message = str(e)
            
        if Doc_id ==-1:#Doc_id!= -1: 
            print(f" Error: {error_message}", flush=True)
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

        background_tasks.add_task( InsertDocsPipeLine, masked_file_path,Doc_id)

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

