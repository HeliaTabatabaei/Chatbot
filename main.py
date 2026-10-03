import json
import sys
import time
import traceback

from fastapi import FastAPI, HTTPException, Request
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi_swagger import patch_fastapi
from fastapi.middleware.cors import CORSMiddleware

from Models.mainModels import QueryRequest, SearchResult
import uvicorn

from API.admin_routes import router as admin_router
from API.Wallet_routes import router as wallet_router
from API.query_routes import router as query_router

from pathlib import Path

app = FastAPI(
    docs_url=None,
    swagger_ui_oauth2_redirect_url=None,
    title="Adonis Docs Assistant API",
    description="RAG-based technical support API for Adonis technicians",
    version="1.0.0"
)
patch_fastapi(app, docs_url="/docs")

# ✅ CORSMiddleware باید اولین (و آخرین) میدل‌ور اضافه‌شده باشد
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://taftantest.adonistech.ir",
        "https://taftantest.adonistech.ir",
        "http://taftantest.adonistech.ir:8000",
        "https://taftantest.adonistech.ir:8000",
        "http://10.44.4.12",
        "https://10.44.4.12",
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_private_network=True,  # 👈 این پارامتر کافی است
)

# ❌ میدل‌ور سفارشی add_private_network_header را حذف کنید
# @app.middleware("http")
# async def add_private_network_header(request: Request, call_next):
#     ...

security = HTTPBearer()

BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT = BASE_DIR / "data"

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