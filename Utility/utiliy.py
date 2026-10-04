import base64
from datetime import datetime

import json
from pathlib import Path
from typing import Any, Dict, Tuple


from typing import Any, Dict, List, Optional
import uuid
import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError



security = HTTPBearer()
r = redis.Redis(host="10.44.4.13", port=6379, db=1, decode_responses=True)

def get_current_user_payload(
  token
):
    """
    Dependency:
      - gets Bearer token
      - decodes payload (NO VERIFY, as per your current setup)
      - reads Redis by UserKey
      - checks token exists in stored sessions list
      - returns payload if authorized
    """
   

    
    try:
     
        payload = decode_token_no_verify(token)
      
        
       
    except Exception:
        return False,"Token invalid",""
      
    user_key = payload.get("UserKey")
   
    if not user_key:
       return False,"Token invalid",""
 
    
    Userkey = r.get(user_key)
    
    if not Userkey:
        return False,"Token invalid",""
        
  
    try:
       
        sessions = _parse_redis_sessions(Userkey)
       
    except Exception:
        return False,"Token invalid",""
      
   
    if not sessions:
           return False,"Token invalid",""
    return True,"OK",user_key
def _parse_redis_sessions(raw: Any) -> List[Dict[str, Any]]:
    """
    Redis might return bytes/str. Value is expected to be a JSON string of a list[dict].
    """
    if raw is None:
        return []

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")

    if not isinstance(raw, str) or not raw.strip():
        return []

    data = json.loads(raw)
   
    sessions = json.loads(data["Value"])
    
    return sessions##[x for x in data if isinstance(x, dict)]
def decode_token_no_verify(token: str) -> dict:#فهمیدن یوزر کی
   
    # دستی decode بدون verify
    parts = token.split(".")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)  # fix padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))
    
def normalize_conversation_id(conversation_id: Optional[str]) -> Tuple[str, bool]:
        
        try:
            if conversation_id is None:
                raise ValueError

            conversation_id = str(conversation_id).strip()

            if conversation_id in ("", "undefined", "null", "None"):
                raise ValueError

            normalized = str(uuid.UUID(conversation_id))
            return normalized, False

        except (ValueError, TypeError, AttributeError):
            return str(uuid.uuid4()), True
def generate_optimized_embedding_text(chunk: dict) -> str:
    metadata = chunk.get("metadata") or {}

    # heading_path داخل metadata قرار دارد
    heading_path = str(
        metadata.get("heading_path")
        or metadata.get("heading")
        or ""
    ).strip()

    # آخرین بخش مسیر، عنوان دقیق‌تر چانک است
    heading_parts = [
        part.strip()
        for part in heading_path.split(">")
        if part.strip()
    ]

    primary_heading = (
        heading_parts[-1]
        if heading_parts
        else ""
    )

    # حذف عنوان فایل/سند از ابتدای مسیر موضوعی
    semantic_path = (
        " > ".join(heading_parts[1:])
        if len(heading_parts) > 1
        else primary_heading
    )

    def join_metadata_values(key: str) -> str:
        value = metadata.get(key, [])

        if value is None:
            return ""

        if isinstance(value, (list, tuple, set)):
            return "، ".join(
                str(item).strip()
                for item in value
                if item is not None and str(item).strip()
            )

        return str(value).strip()

    customer = join_metadata_values("customer_name")
    device = join_metadata_values("device_type")
    model = join_metadata_values("device_model")
    service_type = join_metadata_values("service_type")
    service_group = join_metadata_values("service_group")
    service_name = join_metadata_values("service_name")

    # keywords در metadata و به‌صورت dict است
    raw_keywords = metadata.get("keywords") or {}

    if isinstance(raw_keywords, dict):
        # فقط عبارت کلیدی؛ scoreها وارد embedding نمی‌شوند
        keyword_values = list(raw_keywords.keys())

    elif isinstance(raw_keywords, (list, tuple, set)):
        keyword_values = list(raw_keywords)

    elif raw_keywords:
        keyword_values = [str(raw_keywords)]

    else:
        keyword_values = []

    # جلوگیری از نویز در صورت زیادبودن keywords
    keyword_values = keyword_values[:10]

    keywords = "، ".join(
        str(keyword).strip()
        for keyword in keyword_values
        if keyword is not None and str(keyword).strip()
    )

    # متن اصلی در سطح root چانک قرار دارد
    main_text = str(
        chunk.get("main_text")
        or chunk.get("maintext")
        or ""
    ).strip()

    sections = []

    # این دو قسمت برای افزایش وزن معنایی Heading هستند
    if primary_heading:
        sections.append(
            f"[عملیات و موضوع اصلی]: {primary_heading}"
        )

        sections.append(
            f"[عنوان اصلی بخش]: {primary_heading}"
        )

    # برای چانک‌های سطح پایین، مسیر موضوعی ارزشمند است
    if semantic_path and semantic_path != primary_heading:
        sections.append(
            f"[مسیر موضوعی]: {semantic_path}"
        )

    if heading_path:
        sections.append(
            f"[مسیر کامل سند]: {heading_path}"
        )

    technical_info = []

    if customer:
        technical_info.append(f"مشتری: {customer}")

    if device:
        technical_info.append(f"تجهیز: {device}")

    if model:
        technical_info.append(f"مدل تجهیز: {model}")

    if service_type:
        technical_info.append(f"نوع سرویس: {service_type}")

    if service_group:
        technical_info.append(f"گروه سرویس: {service_group}")

    if service_name:
        technical_info.append(f"نام سرویس: {service_name}")

    if technical_info:
        sections.append(
            "[اطلاعات فنی]: " + " | ".join(technical_info)
        )

    if keywords:
        sections.append(
            f"[کلمات کلیدی]: {keywords}"
        )

    if main_text:
        sections.append(
            f"[شرح و دستورالعمل]:\n{main_text}"
        )

    return "\n\n".join(sections).strip()

import re


def normalize_text(text: str) -> str:
    text = text.casefold()

    # تبدیل حروف عربی به فارسی
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # تبدیل نیم‌فاصله به فاصله
    text = text.replace("\u200c", " ")

    # حذف فاصله‌های اضافی
    text = re.sub(r"\s+", " ", text)

    return text.strip()
def get_current_user_key(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> str:
        """
        اعتبارسنجی توکن و بازگرداندن شناسه کاربر.
        """
        token = credentials.credentials
        try:
            is_valid, message, user_key = get_current_user_payload(token)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=message,
                )
            return user_key
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
            )