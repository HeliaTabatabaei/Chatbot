import json
import sys
import time
import traceback



from fastapi import  FastAPI, HTTPException

from fastapi.security import HTTPBearer

from fastapi.staticfiles import StaticFiles
from fastapi_swagger import patch_fastapi


from Models.mainModels import  QueryRequest,     SearchResult
import uvicorn

from fastapi.middleware.cors import CORSMiddleware
#-----------
from API.admin_routes import router as admin_router
from API.Wallet_routes import router as wallet_router
from API.query_routes import router as query_router
#--------------------
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
app.include_router(query_router)

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
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
   
