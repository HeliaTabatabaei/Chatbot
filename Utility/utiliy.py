import base64
from datetime import datetime

import json
from pathlib import Path
from typing import Any, Dict


from typing import Any, Dict, List, Optional
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
   

    # 1) decode (your current approach)
    try:
        print('tokentokentokentokentokentokentokentokentokentoken',flush=True)
        print(token,flush=True)
        payload = decode_token_no_verify(token)
      
        
       
    except Exception:
        return False,"Token invalid",""
       #raise  HTTPException(status_code=401, detail="Token invalid")
    user_key = payload.get("UserKey")
    print("userkeyuserkeyuserkeyuserkeyuserkeyuserkeyuserkey",flush=True)
    print(user_key,flush=True)
  
    # print(payload)
    if not user_key:
       return False,"Token invalid",""
       # raise   HTTPException(status_code=401, detail="Token invalid")

    
    Userkey = r.get(user_key)
    print("userkeyRedisuserkeyRedisuserkeyRedisuserkeyRedisuserkeyRedisuserkeyRedisuserkeyRedis")
    print(Userkey)
    if not Userkey:
        return False,"Token invalid",""
        #raise  HTTPException(status_code=401, detail="No active session0")
        
    # 4) parse sessions + check token exists (multi-device allowed)
  
    try:
        print("RedisRedisRedis")
        sessions = _parse_redis_sessions(Userkey)
       
    except Exception:
        return False,"Token invalid",""
       #raise  HTTPException(status_code=401, detail="No active session1")
   
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
   

    print('data*******************')
    print(data)
    sessions = json.loads(data["Value"])
    # if not isinstance(data, list):
    #     raise ValueError("Redis session value is not a JSON list")
    # keep only dict items
    return sessions##[x for x in data if isinstance(x, dict)]
def decode_token_no_verify(token: str) -> dict:#فهمیدن یوزر کی
    print(token,flush=True)
    # دستی decode بدون verify
    parts = token.split(".")
    payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)  # fix padding
    return json.loads(base64.urlsafe_b64decode(payload_b64))


    