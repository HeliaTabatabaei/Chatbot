from openai import OpenAI
from .base import LLMProvider


class GenericProvider(LLMProvider):


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = self.base_uri
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key or "not-needed",
            default_headers={self.auth_header_name: self._build_auth_value()},
        )

    def _normalize_response(self, completion, think: bool = False) -> str:

        message = completion.choices[0].message
        text = (message.content or "").strip()

        if think:
            extra = getattr(message, "model_extra", None) or {}
            reasoning = (
                extra.get("reasoning")
                or extra.get("thinking")
                or extra.get("reasoning_content")
                or ""
            ).strip()
            if reasoning:
                return f"{reasoning}\n\n{text}" if text else reasoning

        return text

    def chat(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=2000,
        )
        return self._normalize_response(completion)

    def chat_stream(self, system_prompt: str, user_prompt: str, temperature: float, on_chunk):

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=2000,
                stream=True,
            )

            any_chunk = False
            for chunk in stream:
                if not getattr(chunk, "choices", None):
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    on_chunk(content)
                    any_chunk = True

            if any_chunk:
                return

        except Exception:
            pass

        on_chunk(self.chat(system_prompt, user_prompt, temperature))