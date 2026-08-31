# utils/stream_unmasker.py
import re
import json
from pathlib import Path
from typing import Dict, Optional


class StreamUnmasker:
    """
    Unmasking امن برای خروجی استریم LLM
    از شکسته‌شدن توکن‌ها (مانند [SEC_IP_1]) بین Chunkهای استریم جلوگیری می‌کند.
    """
    MAX_KEY_LEN = 32

    def __init__(self, vault_path: Optional[str] = None, vault_dict: Optional[Dict[str, str]] = None):
        self.vault: Dict[str, str] = {}
        self.buffer = ""

        if vault_dict:
            self.vault = vault_dict
        elif vault_path:
            p = Path(vault_path).resolve()
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    self.vault = json.load(f)

        if self.vault:
            # اسکیپ کاراکترهای رجکس مثل [ و ]
            escaped = "|".join(re.escape(k) for k in sorted(self.vault.keys(), key=len, reverse=True))
            self.pattern = re.compile(escaped)
        else:
            self.pattern = None

    def _is_potential_partial(self, text: str) -> bool:
        """بررسی اینکه آیا انتهای بافر شروع یک کلید ناتمام مانند '[SEC_' است یا خیر"""
        idx = text.rfind("[")
        if idx == -1:
            return False
        
        partial = text[idx:]
        if len(partial) > self.MAX_KEY_LEN or "]" in partial:
            return False
            
        return any(k.startswith(partial) for k in self.vault.keys())

    def feed(self, new_chunk: str) -> str:
        """دریافت چانک جدید از استریم و برگرداندن متن امن و جایگزین‌شده"""
        if not self.pattern or not new_chunk:
            return new_chunk

        self.buffer += new_chunk

        # جایگزینی توکن‌های کامل با مقادیر واقعی
        self.buffer = self.pattern.sub(
            lambda m: self.vault.get(m.group(0), m.group(0)),
            self.buffer
        )

        # اگر انتهای بافر یک توکن ناتمام باشد، آن بخش را نگه می‌داریم
        safe_len = len(self.buffer)
        if self._is_potential_partial(self.buffer):
            safe_len = self.buffer.rfind("[")

        safe_part = self.buffer[:safe_len]
        self.buffer = self.buffer[safe_len:]
        return safe_part

    def flush(self) -> str:
        """ارسال باقیمانده بافر در پایان استریم"""
        rest = self.buffer
        self.buffer = ""
        return rest
