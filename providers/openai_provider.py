from __future__ import annotations
from typing import Any
from openai import OpenAI
from .base import ChatResponse, LLMProvider, StreamCallback

class OpenAIProvider(LLMProvider):
    def __init__(self, client: OpenAI, chat_model: str, embedding_model: str):
        print("OpenAIProvider",flush=True)
        self.client = client
        self.chat_model = chat_model
        self.embedding_model = embedding_model

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.3) -> ChatResponse:
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=temperature,
        )
        
        content = ""
        if response.choices:
            content = response.choices[0].message.content or ""
            
        usage: dict[str, int] = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens or 0,
                "output_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0
            }
            
        return ChatResponse(
            content=content,
            usage=usage,
            meta={"model": self.chat_model}
        )

    def chat_stream(
    self,
    messages: list[dict[str, str]],
    on_chunk: StreamCallback,
    temperature: float = 0.3,
) -> None:
        # اضافه کردن include_usage برای اطمینان از دریافت آمار توکن‌ها در استریم
        stream = self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=temperature,
            stream=True,
            stream_options={"include_usage": True} # <--- بسیار مهم
        )

        response_id = None
        for chunk in stream:
            # ذخیره ID پاسخ (معمولاً در اولین چانک می‌آید)
            if not response_id and chunk.id:
                response_id = chunk.id

            # ۱. هندل کردن متن (Tokens)
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    # ارسال به صورت دیکشنری برای تفکیک در لایه‌های بعد
                    on_chunk({"type": "token", "content": content})

            # ۲. هندل کردن Usage (معمولاً در چانک آخر می‌آید)
            if hasattr(chunk, "usage") and chunk.usage is not None:
                usage_data = {
                    "input_tokens": chunk.usage.prompt_tokens,
                    "output_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens
                }
                # ارسال متادیتا به عنوان چانک نهایی
                on_chunk({
                    "type": "meta",
                    "response_id": response_id,
                    "usage": usage_data
                })
