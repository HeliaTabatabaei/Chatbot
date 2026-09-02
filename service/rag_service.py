from __future__ import annotations

import json
from logging import Filter
import os
from typing import Any, Optional

from qdrant_client import models

from Models.mainModels import SearchFilters
from Prompt.promt_Rerank import RERANK_SYSTEM_PROMPT, build_rerank_user_prompt
from SQlDB.IngestionQuery import load_chunks_from_dbByDocId
from config import COLLECTION_NAME, BaseUrl, COLLECTION_NAME_Meta

from Prompt.prompts_config import SYSTEM_PROMPT, USER_PROMPT
from providers.base import LLMProvider, StreamCallback
from Prompt.promt_Rerank import RERANK_SYSTEM_PROMPT, build_rerank_user_prompt
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

class RAGService:
    def __init__(
        self,
        llm: LLMProvider,
        second_llm: LLMProvider,
        qdrant_client: Any,
        collection_name: Optional[str] = None,
        collection_name_meta: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.second_llm = second_llm
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or COLLECTION_NAME
        self.collection_name_meta = collection_name_meta or COLLECTION_NAME_Meta

    def embed_query(self, text: str) -> list[float]:
        return self.llm.embed_query(text)

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[Any]:
        hits = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="dense",
            limit=limit,
            query_filter=filters,
        )
        return getattr(hits, "points", []) or []

    def searchMetaData(
        self,
        query_vector: list[float],
        limit: int = 1,
    ) -> list[Any]:
        hits = self.qdrant_client.query_points(
            collection_name=self.collection_name_meta,
            query=query_vector,
            using="dense",
            limit=limit,
            score_threshold=0.65,
        )
        return getattr(hits, "points", []) or []

    def getSourceFilePath(self, source: str, docid: Any) -> str:
        chunks, t, path = load_chunks_from_dbByDocId(docid)
        filename = source.replace("\\", "/").rsplit("/", 1)[-1]
        return BaseUrl + "/" + path + "/" + filename

    def getListofImagepath(self, imageList: list[Any], docid: Any) -> list[str]:
        chunks, t, path = load_chunks_from_dbByDocId(docid)
        return [
            BaseUrl + "/" + path + "/" + image.get("image_path", "")
            for image in (imageList or [])
            if image.get("image_path")
        ]

    def _build_rerank_condidate(self, results: list[Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        if not results:
            return candidates

        for result in results:
            payload = self._get_payload(result)
            candidates.append({
                "id": str(self._get_result_id(result)),
                "text": payload.get("maintext", ""),
                "customer_name": payload.get("customer_name", ""),
                "device_type": payload.get("device_type", ""),
                "device_model": payload.get("device_model", ""),
                "service_type": payload.get("service_type", ""),
                "service_name": payload.get("service_name", ""),
                "service_group": payload.get("service_group", ""),
                "keywords": payload.get("keywords", []),
                "heading": payload.get("heading_path", ""),
            })

        return candidates

    def buildResponseCondidate(self, results: list[Any]) -> str:
        candidates: list[dict[str, Any]] = []
        if not results:
            return json.dumps([], ensure_ascii=False, indent=2)

        for result in results:
            payload = self._get_payload(result)
            docid = payload.get("doc_id", "")
            candidates.append({
                "id": str(self._get_result_id(result)),
                "text": payload.get("maintext", ""),
                "meta": {
                    "customer_name": payload.get("customer_name", ""),
                    "device_type": payload.get("device_type", ""),
                    "device_model": payload.get("device_model", ""),
                    "service_type": payload.get("service_type", ""),
                    "service_name": payload.get("service_name", ""),
                    "service_group": payload.get("service_group", ""),
                    "keywords": payload.get("keywords", []),
                    "heading": payload.get("heading_path", ""),
                    "source_file": self.getSourceFilePath(payload.get("source_file", ""), docid),
                    "image_paths": self.getListofImagepath(payload.get("imgs_info") or [], docid),
                },
            })
        return json.dumps(candidates, ensure_ascii=False, indent=2)

    def rerank_results(
        self,
        original_query: str,
        rewritten_query: str,
        results: list[Any],
        score_threshold: float = 0.7,
        top_k: int = 10,
    ) -> list[Any]:
        if not results:
            return []

        candidates = self._build_rerank_condidate(results) or []
        if not candidates:
            return sorted(results, key=self._get_result_score, reverse=True)[:top_k]

        user_prompt = build_rerank_user_prompt(
            original_query=original_query,
            rewritten_query=rewritten_query,
            candidates=candidates,
        )

        try:
            response = self.second_llm.chat(
                messages=[
                    {"role": "system", "content": RERANK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )

            content = (getattr(response, "content", "") or "").strip()
            scored_items = self._parse_json_array(content) or []

            if not isinstance(scored_items, list):
                scored_items = []

            score_map: dict[str, float] = {}

            for item in scored_items:
                if not isinstance(item, dict):
                    continue
                doc_id = str(item.get("id", "")).strip()
                if not doc_id:
                    continue
                try:
                    score = float(item.get("score", 0.0))
                except (TypeError, ValueError):
                    score = 0.0
                score_map[doc_id] = max(0.0, min(1.0, score))

            processed_results = []
            for result in results:
                doc_id = str(self._get_result_id(result)).strip()
                llm_score = score_map.get(doc_id)
                if llm_score is not None:
                    if hasattr(result, "score"):
                        result.score = llm_score
                    elif isinstance(result, dict):
                        result["score"] = llm_score

                    payload = self._get_payload(result)
                    if isinstance(payload, dict):
                        payload["score"] = llm_score
                        payload["rerank_score"] = llm_score

                    if isinstance(result, dict):
                        result["score"] = llm_score
                        result["rerank_score"] = llm_score

                processed_results.append(result)

            processed_results.sort(
                key=lambda r: score_map.get(str(self._get_result_id(r)).strip(), 0.0),
                reverse=True,
            )

            filtered_results = [
                r
                for r in processed_results
                if score_map.get(str(self._get_result_id(r)).strip(), 0.0) >= score_threshold
            ]

            final_output = filtered_results[:top_k]

            if not final_output and processed_results:
                final_output = processed_results[:top_k]

            if not final_output:
                final_output = sorted(results, key=self._get_result_score, reverse=True)[:top_k]

            return final_output

        except Exception as exc:
            print(f"[RERANK ERROR 1] Fallback to retrieval scores: {exc}")
            return sorted(results, key=self._get_result_score, reverse=True)[:top_k]

    def answer_with_rag_stream(
        self,
        query: str,
        results: list[Any],
        on_chunk: StreamCallback,
        temperature: float = 0.1,
        history: str | None = None,
    ) -> None:
        context = self.buildResponseCondidate(results)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(
                    context=context,
                    query=query,
                    history=history,
                ),
            },
        ]

        self.llm.chat_stream(
            messages=messages,
            on_chunk=on_chunk,
            temperature=temperature,
        )

    @staticmethod
    def _get_payload(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            payload = result.get("payload")
            return payload if isinstance(payload, dict) else {}
        payload = getattr(result, "payload", None)
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _get_result_id(result: Any) -> str:
        if isinstance(result, dict):
            return str(result.get("id", ""))
        return str(getattr(result, "id", ""))

    @staticmethod
    def _get_result_score(result: Any) -> float:
        if isinstance(result, dict):
            value = result.get("score", 0.0)
        else:
            value = getattr(result, "score", 0.0)

        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _parse_json_array(content: str) -> list[dict[str, Any]]:
        content = (content or "").strip()

        if not content:
            raise ValueError("Empty reranker response")

        code_fence = "```"

        if content.startswith(code_fence):
            lines = content.splitlines()

            if lines and lines[0].strip().startswith(code_fence):
                lines = lines[1:]

            if lines and lines[-1].strip() == code_fence:
                lines = lines[:-1]

            content = "\n".join(lines).strip()

        parsed = json.loads(content)

        if not isinstance(parsed, list):
            raise ValueError("Reranker response must be a JSON array")

        return parsed
