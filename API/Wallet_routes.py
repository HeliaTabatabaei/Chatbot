
from pathlib import Path

from fastapi import APIRouter,Depends,  HTTPException

from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from fastapi.middleware.cors import CORSMiddleware
from Models.mainModels import BulkChargeRequest
from SQlDB.IngestionQuery import bulk_charge_transactions
from Utility.utiliy import get_current_user_payload
from pathlib import Path
router = APIRouter(prefix="/api", tags=["99 - Wallet"])
security = HTTPBearer()

BASE_DIR = Path(__file__).resolve().parent # تعریف مسیر پایه پروژه
MEDIA_ROOT = BASE_DIR / "data"  # مسیر دقیق پوشه داده‌ها

@router.post("/api/bulk-charge")
async def bulk_charge_tokens(
    request: BulkChargeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security) # احراز هویت توکن سوییگر
):
    # بررسی احراز هویت کاربر لاگین شده در Swagger
    token = credentials.credentials
    try:
        is_valid = get_current_user_payload(token)
        if not is_valid:
            raise HTTPException(status_code=401, detail="عدم دسترسی: توکن نامعتبر است")
    except Exception:
        raise HTTPException(status_code=401, detail="خطا در احراز هویت")
    
    try:
        
        result = bulk_charge_transactions(
            user_keys=request.user_keys,
            amount=request.amount
                       
        )
        return {
            "success": True,
            "message": f"تعداد {result['inserted_count']} رکورد با موفقیت ثبت شد.",
            "total_tokens_charged": result['total_amount']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در ثبت اطلاعات: {str(e)}")

