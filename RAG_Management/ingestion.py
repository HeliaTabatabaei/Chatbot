# ingestion.py
import json
import hashlib
import os
import sys
from tqdm import tqdm
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from RAG_Management.imageInfo import append_image_urls_to_maintext
from RAG_Management.vectorstore   import get_client, ensure_collection

from SQlDB.IngestionQuery import Deactivate_doc_from_sql, InsertDocsToSql, LogStatus, SetALLRecord_IsActiveFalse, SetIsActiveFalse, SetIsActiveTrue, load_chunks_from_db, load_chunks_from_dbByDocId
from config import  COLLECTION_NAME, BATCH_SIZE, OPENAI_API_KEY, EMBED_MODEL, QDRANT_HOST, QDRANT_PORT, BaseUrl
from RAG_Management.bm25 import PersianBM25Encoder
from openai import OpenAI
import pyodbc



client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.gapgpt.app/v1"
)

import re
from datetime import datetime, time


from pathlib import Path

from pathlib import PureWindowsPath  
BASE_DATA_DIR = Path("./data") 
def get_actual_filename_from_rid(source_file_path: str, rid: str) -> str:
    """
    در پوشه تصاویر میگردد تا فایلی که نامش با rId یکی است را با پسوند واقعی پیدا کند.
    مثلاً: rId5 -> rId5.jpeg
    """
    try:
        # استخراج نام پوشه داکیومنت از مسیر ویندوزی
        doc_folder_name = PureWindowsPath(source_file_path).stem
        img_folder_path = BASE_DATA_DIR / doc_folder_name / "img_folder"
       
      
        if not img_folder_path.exists():
            return None

        # جستجو در فایل‌ها برای پیدا کردن rId (بدون حساسیت به حروف بزرگ و کوچک)
        for file in img_folder_path.iterdir():
            if file.stem.lower() == rid.lower():
                print(f"filename:{file.name}")#rId18.png
                return file.name # نام کامل شامل پسوند را برمی‌گرداند
        
        return None
    except Exception:
        return None
#####ساخت url عکس
def get_resolved_image_url(source_file_path: str, actual_filename: str) -> str:
    """
    ساخت URL نهایی برای نمایش در FastAPI
    """
    doc_folder = PureWindowsPath(source_file_path).stem
    return f"/media/{doc_folder}/img_folder/{actual_filename}"


def extract_num(chunk_id) -> int:
    if isinstance(chunk_id, int):
        return chunk_id

    if not isinstance(chunk_id, str):
        raise TypeError(f"chunk_id must be str or int, got {type(chunk_id)}")
    #   raise TypeError(f"chunk_id must be str or int, got {chunk_id.__class__.__name__}")

    m = re.fullmatch(r"vec_(\d+)", chunk_id.strip())
    if not m:
        raise ValueError(f"Invalid chunk_id format: {chunk_id}")
    
    return int(m.group(1))
def embed_batch(texts):
   
        res = client.embeddings.create(model=EMBED_MODEL, input=texts)
        return [item.embedding for item in res.data]


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def already_indexed(client, hash_value):
    flt = Filter(must=[FieldCondition(key="text_hash", match=MatchValue(value=hash_value))])
    res = client.scroll(collection_name=COLLECTION_NAME, scroll_filter=flt, limit=1)
    return len(res[0]) > 0


def ingest():

    qdrant = get_client()

    # ensure_collection(qdrant)
    reset_rag(qdrant)
   
    # Initialize sparse encoder
    sparse_encoder = PersianBM25Encoder()
   
    # with open(JSON_PATH, "r", encoding="utf-8") as f:
    #     chunks = json.load(f)
    chunks = list(load_chunks_from_db())


    # ساخت vocabulary از تمام chunks (یک بار)
    print("Building BM25 vocabulary...")
    all_texts = [c["embedding_text"].strip() for c in chunks if c["embedding_text"].strip()]
    sparse_encoder.build_vocab_from_texts(all_texts)
    print(f"Vocabulary size: {len(sparse_encoder.vocab)}")

    batch_texts, batch_points = [], []

    # for chunk in tqdm(chunks, desc="Ingesting chunks"):
    for chunk in chunks:
    
      
        text = chunk["embedding_text"].strip()
        if not text:
          
            continue

        h = text_hash(text)
        if already_indexed(qdrant, h):
           
            continue

        payload = {"text": text, "text_hash": h, **chunk.get("metadata", {})}
        batch_texts.append(text)
        batch_points.append((chunk["id"], payload))
        
        if len(batch_texts) >= BATCH_SIZE:
           
            flush_batch(qdrant, batch_texts, batch_points, sparse_encoder)
            batch_texts.clear()
            batch_points.clear()

    if batch_texts:
       
        flush_batch(qdrant, batch_texts, batch_points, sparse_encoder)

    # ✅ ذخیره مدل
    sparse_encoder.save("bm25_model.pkl")
    print("BM25 model saved")

    print("✅ Ingestion completed successfully")
def RebuildSparse():
    qdrant = get_client()
    ensure_collection(qdrant)

    # Initialize sparse encoder
    sparse_encoder = PersianBM25Encoder()

    # with open(JSON_PATH, "r", encoding="utf-8") as f:
    #     chunks = json.load(f)
    chunks = load_chunks_from_db()
   
    # ساخت vocabulary از تمام chunks (یک بار)
    print("Building BM25 vocabulary...")
    all_texts = [c["embedding_text"].strip() for c in chunks if c["embedding_text"].strip()]
    sparse_encoder.build_vocab_from_texts(all_texts)
    print(f"Vocabulary size: {len(sparse_encoder.vocab)}")

    batch_texts, batch_points = [], []

    for chunk in tqdm(chunks, desc="Ingesting chunks"):
        text = chunk["embedding_text"].strip()
        if not text:
            continue

        h = text_hash(text)
        # if already_indexed(qdrant, h):
        #     continue

        payload = {"text": text, "text_hash": h, **chunk.get("metadata", {})}
        batch_texts.append(text)
        batch_points.append((chunk["id"], payload))

        if len(batch_texts) >= BATCH_SIZE:
            flush_batchSparse(qdrant, batch_texts, batch_points, sparse_encoder)
            batch_texts.clear()
            batch_points.clear()

    if batch_texts:
        flush_batchSparse(qdrant, batch_texts, batch_points, sparse_encoder)

    # ✅ ذخیره مدل
    sparse_encoder.save("bm25_model.pkl")
    print("BM25 model saved")

    print("✅ Ingestion completed successfully")
    
def ingestQdrant(docid):
 try:        
    LogStatus(
                _DocID=docid,_ActionName='ingestQdrant', _FileName='', _Step="start ingestQdrant",
                _Status="doing",_ErrorMessage="", _Timestamp=datetime.now()
                )
    qdrant = get_client()#اتصال به پایگاه داده Qdrant را برقرار می‌کند.
    ensure_collection(qdrant)# چک می‌کند که آیا کالکشن (میز) مورد نظر در Qdrant وجود دارد یا خیر (اگر نبود می‌سازد).
    chunks,t,path = load_chunks_from_dbByDocId(docid)
    batch_texts, batch_points = [], []
    index=0
    for chunk in tqdm(chunks, desc="Ingesting chunks"):
        if index==0:
            print (chunk,flush=True)
            index=1
            
        text = chunk["embedding_text"].strip()
        maintext= chunk["main_text"].strip()
        id=chunk["id"]
        if not text:
            continue
        h = text_hash(text) #هش کردن وکتور جهت مقایسه که تکراری نباشد
        if already_indexed(qdrant, h): #اگر این متن قبلا در کیودرنت ایندکس شده باشد
            LogStatus(
            _DocID=docid,_ActionName='Insert', _FileName='', _Step="setIsactiveToFalse",
            _Status="FAILED",_ErrorMessage="Hashfile is Existsted", _Timestamp=datetime.now()
            )
            
            return -1
           
        #############14050430
        # # --- بخش جدید برای پردازش عکس‌ها ---
        metadata = chunk.get("metadata", {}).copy()
       
       
       
        payload = {
                "id":id,
                "text": text, 
                "maintext":maintext,
                "text_hash": h, 
                **metadata  # تمام اطلاعات متادیتا + imgs_info اصلاح‌شده در اینجا هست
            }
        
        ###############################################################
        batch_texts.append(text)
        batch_points.append((chunk["id"], payload))
    
        if len(batch_texts) >= BATCH_SIZE:
            LogStatus(
                                    _DocID=docid,_ActionName='ingestQdrant', _FileName='', _Step="ingestQdrant  step 2",
                                    _Status="doing",_ErrorMessage="", _Timestamp=datetime.now()
                                    )
            flush_batchBachQdrantInsert(docid,qdrant, batch_texts, batch_points)
            batch_texts.clear()
            batch_points.clear()

    if batch_texts:
      #  print('%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%')
        LogStatus(
                                            _DocID=docid,_ActionName='ingestQdrant', _FileName='', _Step="ingestQdrant  step 3",
                                            _Status="doing",_ErrorMessage="", _Timestamp=datetime.now()
                                            )
        flush_batchBachQdrantInsert(docid,qdrant, batch_texts, batch_points)
    return 1    
 except Exception as e:
        LogStatus(
                                            _DocID=docid,_ActionName='ingestQdrant', _FileName='', _Step="ingestQdrant  step 4",
                                            _Status="doing",_ErrorMessage=e, _Timestamp=datetime.now()
                                            )
        print(f"Error: {e}")
        return -1

     
       
    # ✅ ذخیره مدل
    




def flush_batch(qdrant, batch_texts, batch_points, sparse_encoder):
 #   print('flush_batch')
    # Dense embeddings (OpenAI)

    dense_embeddings = embed_batch(batch_texts)

    # Sparse embeddings (BM25)
    sparse_embeddings = [sparse_encoder.encode_document(text) for text in batch_texts]

    # ساخت points با هر دو vector

    points = [
        PointStruct(
            id=batch_points[i][0],  ## [i][0]  ##i,  # chunk ID
            vector={
                "dense": dense_embeddings[i],
                "sparse": {
                    "indices": list(sparse_embeddings[i].keys()),
                    "values": list(sparse_embeddings[i].values())
                }
            },
            payload=batch_points[i][1]
        )
        for i in range(len(batch_texts))
    ]

    # for i in range(len(batch_texts)):
    #     print (extract_num([i][0]))
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
def flush_batchSparse(qdrant, batch_texts, batch_points, sparse_encoder):


    # Sparse embeddings (BM25)
    sparse_embeddings = [sparse_encoder.encode_document(text) for text in batch_texts]

    ids = [p[0] for p in batch_points]

    # گرفتن dense قبلی از Qdrant
    existing_points = qdrant.retrieve(
        collection_name=COLLECTION_NAME,
        ids=ids,
        with_vectors=True
    )

    dense_map = {p.id: p.vector["dense"] for p in existing_points}

    points = []
    for i in range(len(batch_texts)):
        pid = batch_points[i][0]
      
        points.append(
            PointStruct(
                id=pid,
                vector={
                    "dense": dense_map.get(pid),  # dense قبلی
                    "sparse": {
                        "indices": list(sparse_embeddings[i].keys()),
                        "values": list(sparse_embeddings[i].values())
                    }
                },
                payload=batch_points[i][1]
            )
        )

    
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
     
def flush_batchBachQdrantInsert(docid,qdrant, batch_texts, batch_points):
   
    LogStatus(
            _DocID=docid,_ActionName='flush_batchBachQdrantInsert', _FileName='', _Step="flush_batchBachQdrantInsert  step 1",
            _Status="doing",_ErrorMessage=str(batch_texts), _Timestamp=datetime.now()
            )
   
    dense_embeddings = embed_batch(batch_texts)
    
    LogStatus(
                _DocID=docid,_ActionName='flush_batchBachQdrantInsert', _FileName='', _Step="flush_batchBachQdrantInsert  step 2",
                _Status="doing",_ErrorMessage="", _Timestamp=datetime.now()
                )
    
    points = [
        PointStruct(
            id=batch_points[i][0],  ## [i][0]  ##i,  # chunk ID
            vector={
                "dense": dense_embeddings[i],
              
            },
            payload=batch_points[i][1]
        )
        for i in range(len(batch_texts))
    ]

    # for i in range(len(batch_texts)):
    #     print (extract_num([i][0]))
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    LogStatus(
                                                        _DocID=docid,_ActionName='flush_batchBachQdrantInsert', _FileName='', _Step="flush_batchBachQdrantInsert  step 3",
                                                        _Status="doing",_ErrorMessage="", _Timestamp=datetime.now()
                                                        )
        

def remove_dense_by_ids(qdrant, ids):
    """
    حذف vector dense برای pointهای مشخص و نگه داشتن sparse + payload.
    """
    if not ids:
        return

    # گرفتن pointها از Qdrant
    
    
    result = qdrant.retrieve(
    collection_name=COLLECTION_NAME,
    ids=ids
    )
   
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=ids # حذف برداشتهای با آی‌دی 1 و 2
    )


  #  print(f"✅ {deleted_rows} rows deleted for doc_id={doc_id}")   
def delete_doc_chunks( docid):
    
    
    qdrant = get_client()
    start = docid * 100000
    end = docid * 100000 + 99999

    offset = None
    ids_to_delete = []

    while True:

        points, offset = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            offset=offset,
            limit=1000,
            with_vectors=False,
            with_payload=False
        )

        for p in points:
            if start <= p.id <= end:
                ids_to_delete.append(p.id)

        if offset is None:
            break

    if ids_to_delete:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=ids_to_delete
        )
   
   
   
def DeleteDocPipLine(docid):
 
    try:
        print(docid)
        delete_doc_chunks(docid)
        
        LogStatus(
            _DocID=docid,_ActionName='Delete', _FileName='', _Step="DeleteQdrant",
            _Status="SUCCESS", _ErrorMessage=None, _Timestamp=datetime.now()
        )
        
        
    except Exception as e:
        print(f"❌ خطا در بخش Qdrant: {str(e)}")
        LogStatus(
            _DocID=docid,_ActionName='Delete', _FileName='', _Step="DeleteQdrant",
            _Status="FAILED", _ErrorMessage=str(e), _Timestamp=datetime.now()
        )
    
   
   
    try:
        Deactivate_doc_from_sql(docid)
        LogStatus(
            _DocID=docid,_ActionName='Delete', _FileName='', _Step="setIsactiveToFalse",
            _Status="SUCCESS", _ErrorMessage=None, _Timestamp=datetime.now()
        )
    except Exception as e:
        print(f"❌ خطا در بخش غیرفعال کردنisactive: {str(e)}")
        LogStatus(
            _DocID=docid,_ActionName='Delete', _FileName='', _Step="setIsactiveToFalse",
            _Status="FAILED", _ErrorMessage=str(e), _Timestamp=datetime.now()
        )
   
def UpdateDocPipLine(docid,target_file_path):
    DeleteDocPipLine(docid)
    InsertDocsPipeLine(target_file_path, docid)
    
    
def reset_rag(qdrant):
    
    print("🧹 Deleting all points from Qdrant...")

    try:
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter()   # DELETE ALL POINTS
        )
        print("✅ All points deleted.")
        
    except Exception as ex:
        print("⚠️ Warning: Failed to delete points:", ex)
        return -1
    # ----------------------------------
    # Remove BM25
    # ----------------------------------
    import os

    bm25_path = "bm25_model.pkl"

    if os.path.exists(bm25_path):
        try:
            os.remove(bm25_path)
            print("🗑️ BM25 model removed.")
        except Exception as ex:
            print("⚠️ Warning: Could not delete bm25_model.pkl:", ex)
            return -1
    else:
        print("ℹ️ No BM25 model found.")
    SetALLRecord_IsActiveFalse()
    print("🎉 RAG reset complete.")
    return 1





def clear_dense_by_ids(qdrant, ids):
    """
    حذف بخش dense و نگه داشتن فقط sparse و payload.
    """
    if not ids:
        return

    # استفاده از retrieve به جای scroll برای گرفتن نقاط با ID
    points = qdrant.retrieve(
        collection_name=COLLECTION_NAME,
        ids=ids,
        with_payload=True,
        with_vectors=True
    )
    
    if not points:
        print(f"هیچ نقطه‌ای با ID های {ids} یافت نشد.")
        return

    new_points = []
    for p in points:
        

        # فقط بخش sparse را در دیکشنری vector قرار می‌دهیم
        # با upsert کردن این، بخش dense قبلی پاک می‌شود (Overwrite)
        point_vector = {}
       

        new_points.append(
            PointStruct(
                id=p.id,
                vector={},
                
                payload= {}
            )
        )
   
    qdrant.upsert(collection_name=COLLECTION_NAME, points=new_points)
    print(f"بخش Dense برای {len(new_points)} نقطه حذف شد.")    


def InsertDocsPipeLine(target_file_path, Doc_id):
    print(f"DEBUG: Processing file {target_file_path}", flush=True)

    # --- مرحله ۱: اینجست در Qdrant ---
    try:
      
        result=ingestQdrant(Doc_id)
       
        #"ReadyToRebuild":یعنی اینجست کیو درنت با موفقیت انجام شده است
        if result==1:
           LogStatus(
            _DocID=Doc_id,_ActionName='ingestQdrant', _FileName=target_file_path, _Step="InsertDocsPipeLine",
            _Status="SUCCESS", _ErrorMessage=None, _Timestamp=datetime.now()
            )
           SetIsActiveTrue(target_file_path,Doc_id)
        else:
            LogStatus(
                       _DocID=Doc_id,_ActionName='ingestQdrant', _FileName=target_file_path, _Step="ingestoQdrant",
                       _Status="Fail", _ErrorMessage=None, _Timestamp=datetime.now()
                       )
            SetIsActiveFalse( Doc_id)    
        
      
    except Exception as e:
        print(f"❌ خطا در بخش Qdrant: {str(e)}")
        SetIsActiveFalse( Doc_id)    
        LogStatus(
            _DocID=Doc_id,_ActionName='Insert', _FileName=target_file_path, _Step="ingestoQdrant",
            _Status="FAILED", _ErrorMessage=str(e), _Timestamp=datetime.now()
        )
        return -1 # توقف عملیات

# def wrapper_pipeline(file_path: str, doc_id: int):
#     try:
#         # اجرای پایپ‌لاین اصلی پردازش متن و وکتورها
#         InsertDocsPipeLine(file_path, doc_id)
        
#         # ثبت لاگ موفقیت پس از اتمام کار پایپ‌لاین
#         LogStatus(
#             _DocID=doc_id,
#             _ActionName='Insert',
#             _FileName=file_path,
#             _Step='Pipeline Finished',
#             _Status='Success', # تغییر وضعیت به موفقیت پس از اتمام پردازش Qdrant
#             _ErrorMessage=None,
#             _Timestamp=None
#         )
#         print(f"✅ Document with ID:{doc_id} has been successfully processed and stored in SQL and Qdrant.")
        
#     except Exception as e:
#         # ثبت لاگ خطا در صورت بروز مشکل در فرآیند پس‌زمینه
#         LogStatus(
#             _DocID=doc_id,
#             _ActionName='Insert',
#             _FileName=file_path,
#             _Step='Pipeline Failed',
#             _Status='FAILED',
#             _ErrorMessage=str(e),
#             _Timestamp=None
#         )
#         print(f"❌ Pipeline failed for DocID {doc_id}: {str(e)}")

if __name__ == "__main__":

   
    InsertDocsToSql(r'K:\Learning\LLM\Mr.Laghaei\RAG_Adonis_V2\data\1-IT9210-19-00_Camera.json')

