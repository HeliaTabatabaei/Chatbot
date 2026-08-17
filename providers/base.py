from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ChatResponse:
    """
    پاسخ استاندارد متد chat.
    """

    content: str
    usage: dict[str, int] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamEvent:
    """
    رویداد استاندارد برای streaming.
    """

    type: str
    content: Any = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.type,
            "content": self.content,
        }

        if self.meta:
            payload["meta"] = self.meta

        return payload


StreamCallback = Callable[[dict[str, Any]], None]


class LLMProvider(ABC):
    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
    ) -> ChatResponse:
        raise NotImplementedError

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        on_chunk: StreamCallback,
        temperature: float = 0.3,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError
