from __future__ import annotations

from typing import Any
from openai import OpenAI
from .base import ChatResponse, LLMProvider, StreamCallback


class DeepSeekProvider(LLMProvider):
    def __init__(
        self,
        base_uri: str = "https://api.deepseek.com",
        api_key: str = "",
        model: str = "deepseek-chat",
        embed_model: str | None = None,
    ):
        print("DeepSeekProvider",flush=True)
        self.client = OpenAI(api_key=api_key, base_url=base_uri)
        self.chat_model = model
        self.embedding_model = embed_model

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError(
            "DeepSeek does not provide embedding models; use a dedicated embedding provider."
        )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "DeepSeek does not provide embedding models; use a dedicated embedding provider."
        )

    def chat(
        self, messages: list[dict[str, str]], temperature: float = 0.3
    ) -> ChatResponse:
        request_params: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
        }
        # مدل reasoner در دیپ‌سیک پارامتر temperature نمی‌پذیرد
        if self.chat_model != "deepseek-reasoner":
            request_params["temperature"] = temperature

        response = self.client.chat.completions.create(**request_params)

        content = ""
        reasoning_content = ""
        if response.choices:
            message = response.choices[0].message
            content = message.content or ""
            reasoning_content = getattr(message, "reasoning_content", "") or ""

        usage: dict[str, int] = {}
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens or 0,
                "output_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
                "Provider":"DeepSeek"
            }
            prompt_tokens_details = getattr(
                response.usage, "prompt_tokens_details", None
            )
            if prompt_tokens_details:
                usage["cached_tokens"] = getattr(
                    prompt_tokens_details, "cached_tokens", 0
                )

        return ChatResponse(
            content=content,
            usage=usage,
            meta={
                "model": self.chat_model,
                "reasoning_content": reasoning_content,
            },
        )

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        on_chunk: StreamCallback,
        temperature: float = 0.3,
    ) -> None:
        request_params: dict[str, Any] = {
            "model": self.chat_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if self.chat_model != "deepseek-reasoner":
            request_params["temperature"] = temperature

        stream = self.client.chat.completions.create(**request_params)

        response_id = None
        for chunk in stream:
            if not response_id and chunk.id:
                response_id = chunk.id

            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    on_chunk({"type": "reasoning", "content": reasoning})
                content = getattr(delta, "content", None)
                if content:
                    on_chunk({"type": "token", "content": content})

            if hasattr(chunk, "usage") and chunk.usage is not None:
                usage_data = {
                    "input_tokens": chunk.usage.prompt_tokens or 0,
                    "output_tokens": chunk.usage.completion_tokens or 0,
                    "total_tokens": chunk.usage.total_tokens or 0,
                    "Provider":"DeepSeek"
                }
                prompt_tokens_details = getattr(
                    chunk.usage, "prompt_tokens_details", None
                )
                if prompt_tokens_details:
                    usage_data["cached_tokens"] = getattr(
                        prompt_tokens_details, "cached_tokens", 0
                    )
                on_chunk(
                    {
                        "type": "meta",
                        "response_id": response_id,
                        "usage": usage_data,
                    }
                )
