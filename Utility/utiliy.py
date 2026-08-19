import base64
from datetime import datetime

import json
from pathlib import Path
from typing import Any, Dict, Tuple


from typing import Any, Dict, List, Optional
import uuid
import redis

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




    