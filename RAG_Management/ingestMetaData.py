import json
import os
from tqdm import tqdm
from qdrant_client.models import Distance, PointStruct, Filter, VectorParams
from qdrant_client import QdrantClient
from openai import OpenAI
from config import  COLLECTION_NAME, BATCH_SIZE, OPENAI_API_KEY, EMBED_MODEL, QDRANT_HOST, QDRANT_PORT
# تنظیمات
COLLECTION_NAME_Meta = "BankName"
BATCH_SIZE = 20


client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.gapgpt.app/v1"
)
def ensure_collection(qdrant):
    """مطمئن شدن از وجود کالکشن با تنظیمات درست"""
    collections = qdrant.get_collections().collections
    exists = any(c.name == COLLECTION_NAME_Meta for c in collections)
    
    if not exists:
        print(f"Creating collection: {COLLECTION_NAME_Meta}")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME_Meta,
            vectors_config={
                "dense": VectorParams(size=3072, distance=Distance.COSINE)
            }
        )
    else:
        print(f"Collection {COLLECTION_NAME_Meta} already exists.")

def embed_batch(texts):
    res = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in res.data]

def reset_rag(qdrant):
    try:
        qdrant.delete(
            collection_name=COLLECTION_NAME_Meta,
            points_selector=Filter()
        )
        print(f"Collection {COLLECTION_NAME_Meta} cleared.")
    except Exception as e:
        print(f"Error resetting collection: {e}")

def load_chunks():
    """خواندن فایل Bank.json از مسیر data"""
    json_path = os.path.join("data", "Bank.json")
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data.get("items", [])

def flush_batch(qdrant, batch_texts, batch_points):
    if not batch_texts:
        return
    
    print(f"Embedding and uploading batch of {len(batch_texts)} items...")
    dense_embeddings = embed_batch(batch_texts)
    
    points = []
    for i in range(len(batch_texts)):
        points.append(
            PointStruct(
                id=batch_points[i][0],
                vector={
                    "dense": dense_embeddings[i],
                },
                payload=batch_points[i][1]
            )
        )
    
    qdrant.upsert(
        collection_name=COLLECTION_NAME_Meta,
        points=points
    )

def ingestBank():

    try:
        qdrant = QdrantClient(
                host="127.0.0.1",
                port=int(QDRANT_PORT),
            )
        # تست اتصال
        qdrant.get_collections() 
    except Exception as e:
        print(f"CRITICAL: Could not connect to Qdrant at {QDRANT_HOST}  {QDRANT_PORT}.")
        print(f"Reason: {e}")
        print("Make sure Docker Desktop is running and Qdrant container is active.")
        return

    ensure_collection(qdrant)

    
    # پاکسازی داده‌های قبلی (اختیاری)
    reset_rag(qdrant)
    
    chunks = load_chunks()
    if not chunks:
        print("No data found to ingest.")
        return

    batch_texts, batch_points = [], []
    
    for chunk in tqdm(chunks, desc="Ingesting Bank Names"):
        # در فایل JSON شما فیلد نام بانک 'value' است
        text = chunk.get("value", "").strip()
        point_id = chunk.get("id")
        
        if not text or point_id is None:
            continue
            
        payload = {
            "text": text,
            "id": point_id,
            "entity_type": "bank"
        }
        
        batch_texts.append(text)
        batch_points.append((point_id, payload))
        
        # وقتی به اندازه BATCH_SIZE رسیدیم، آپلود کن
        if len(batch_texts) >= BATCH_SIZE:
            flush_batch(qdrant, batch_texts, batch_points)
            batch_texts, batch_points = [], [] # ریست کردن بچ
            
    # آپلود باقی‌مانده‌ها (اگر کمتر از BATCH_SIZE باشند)
    if batch_texts:
        flush_batch(qdrant, batch_texts, batch_points)

if __name__ == "__main__":
    ingestBank()
