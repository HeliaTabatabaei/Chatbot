from __future__ import annotations

import json
import os
from typing import Any, Optional

from qdrant_client import models

from Models.mainModels import SearchFilters
from SQlDB.IngestionQuery import load_chunks_from_dbByDocId
from config import COLLECTION_NAME, BaseUrl,COLLECTION_NAME_Meta
from log import append_qa_to_filetest
from prompts_config import SYSTEM_PROMPT, USER_PROMPT
from providers.base import LLMProvider, StreamCallback


class RAGService:
    def __init__(
        self,
        llm: LLMProvider,
        qdrant_client: Any,
        collection_name: Optional[str] = None,
        collection_name_meta: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name or COLLECTION_NAME
        self.collection_name_meta = collection_name_meta or COLLECTION_NAME_Meta

    def embed_query(self, text: str) -> list[float]:
        return self.llm.embed_query(text)

    @staticmethod
    def build_filter(
        filters: Optional[SearchFilters],
    ) -> Optional[models.Filter]:
        if not filters:
            return None

        conditions: list[models.FieldCondition] = []

        if getattr(filters, "doc_ids", None):
            conditions.append(
                models.FieldCondition(
                    key="doc_id",
                    match=models.MatchAny(any=filters.doc_ids),
                )
            )

        if getattr(filters, "tags", None):
            conditions.append(
                models.FieldCondition(
                    key="tags",
                    match=models.MatchAny(any=filters.tags),
                )
            )

        if getattr(filters, "date_from", None):
            conditions.append(
                models.FieldCondition(
                    key="date",
                    range=models.Range(gte=filters.date_from),
                )
            )

        if getattr(filters, "date_to", None):
            conditions.append(
                models.FieldCondition(
                    key="date",
                    range=models.Range(lte=filters.date_to),
                )
            )

        if not conditions:
            return None

        return models.Filter(must=conditions)

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        filters: Optional[SearchFilters] = None,
    ) -> list[Any]:
        query_filter = self.build_filter(filters)

        hits = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            using="dense",
            limit=limit,
            query_filter=query_filter,
        )

        return getattr(hits, "points", []) or []
    def searchMetaData(
            self,
            query_vector: list[float],
            limit: int = 1   
           
        ) -> list[Any]:
          
    
            hits = self.qdrant_client.query_points(
                collection_name=self.collection_name_meta,
                query=query_vector,
                using="dense",
                limit=limit,
                score_threshold=0.65   
            )
    
            return getattr(hits, "points", []) or []
    def getSourceFilePath(self,source ,docid)  :
        chunks,t,path = load_chunks_from_dbByDocId(docid)
        filename = source.replace("\\", "/").rsplit("/", 1)[-1]

        append_qa_to_filetest(filename)
        return  BaseUrl+ '/'+ path + '/' + filename
    def getListofImagepath(self,imageList: list[Any],docid):
        chunks,t,path = load_chunks_from_dbByDocId(docid)
        return [
         BaseUrl+ '/'+ path + '/'+ image["image_path"]
         for image in imageList
         if image.get("image_path")
          ]
    from typing import Any

   
        
    def _build_rerank_condidate(self,results: list[Any]) :
            candidates: list[dict[str, Any]] = []
            if not results:
                    return json.dumps([], ensure_ascii=False, indent=2)
        
            
            for result in results:
                payload = self._get_payload(result)
               
                candidates.append({
                "id": str(self._get_result_id(result)),
                "text": payload.get("maintext", ""),
                "customer_name": payload.get("customer_name", ""),
                "vendor_name": payload.get("vendor_name", ""),
                "service_type": payload.get("service_type", ""),
                "keywords": payload.get("keywords", []),
                "heading": payload.get("heading_path", ""),
                
        })
   
            return   json.dumps(candidates, ensure_ascii=False, indent=2)      
    def buildResponseCondidate(self,results: list[Any]) :
        candidates: list[dict[str, Any]] = []
        if not results:
                return json.dumps([], ensure_ascii=False, indent=2)
    
        
        for result in results:
            payload = self._get_payload(result)
            docid=payload.get("doc_id", "")
            candidates.append({
            "id": str(self._get_result_id(result)),
            "text": payload.get("maintext", ""),
            "meta": {
                "customer_name": payload.get("customer_name", ""),
                "vendor_name": payload.get("vendor_name", ""),
                "service_type": payload.get("service_type", ""),
                "keywords": payload.get("keywords", []),
                "heading": payload.get("heading_path", ""),
                "source_file": self.getSourceFilePath(payload.get("source_file", ""), docid),
                "image_paths": self.getListofImagepath(payload.get("imgs_info", []), docid),
    }
})
        return   json.dumps(candidates, ensure_ascii=False, indent=2)  
    
        
    def rerank_results(
        self,
        query: str,
        results: list[Any],
        history: str | None = None,
    ) -> list[Any]:
        candidates=self._build_rerank_condidate(results)
       
        system_prompt = """
You are a technical document reranker. Your job is to score relevance on a scale of 0.0 to 1.0.

Instructions:
- 1.0: The chunk contains the exact answer, error code explanation, or step-by-step solution.
- 0.8-0.9: Highly relevant. Provides critical context or strong supporting evidence for the answer.
- 0.5: Marginally relevant. Contains the right topic but lacks specific actionable details.
- 0.0-0.3: Irrelevant. Wrong device, wrong topic, or gibberish.

Examples:
Query: "How to fix ATM error 404?"
Chunk: "Error 404 indicates a network timeout in the X-500 module. Reset the router." -> Score: 1.0
Chunk: "The X-500 module operates at 24V power supply." -> Score: 0.3

Rules:
- You MUST score every candidate.
- Return ONLY valid JSON array: [{"id": "...", "score": ...}]
- Do not add explanations.
""".strip()

        history_text = history.strip() if history else "No previous conversation."
        user_prompt = (
            f"Conversation History:\n{history_text}\n\n"
            f"Query:\n{query}\n\n"
            f"Results to Score:\n{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
            f"Return exactly {len(candidates)} JSON items. One score for each ID."
        )

        try:
            response = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )

            content = (response.content or "").strip()
            scored_items = self._parse_json_array(content)

            # استخراج امتیازها در یک دیکشنری
            score_map: dict[str, float] = {}
            for item in scored_items:
                if isinstance(item, dict) and "id" in item:
                    try:
                        score_map[str(item["id"])] = float(item.get("score", 0.0))
                    except (TypeError, ValueError):
                        continue

            # --- بخش مهم: آپدیت کردن امتیاز واقعی روی آبجکت‌ها ---
            processed_results = []
            for result in results:
                res_id = str(self._get_result_id(result))
                # گرفتن امتیاز از LLM، اگر نبود از امتیاز اولیه استفاده شود
                llm_score = score_map.get(res_id, 0.0)
                
                # تزریق امتیاز ریرنک به فیلد اسکور (بسته به ساختار آبجکت Qdrant شما)
                if hasattr(result, 'score'):
                    result.score = llm_score
                elif isinstance(result, dict):
                    result['score'] = llm_score
                
                # همچنین ذخیره در payload برای اطمینان در مراحل بعدی
                payload = self._get_payload(result)
                payload["rerank_score"] = llm_score
                payload["retrieval_score"] = self._get_result_score(result) # ذخیره امتیاز اولیه برای دیباگ
                
                processed_results.append(result)

            # ۱. مرتب‌سازی بر اساس امتیاز جدید (LLM Score)
            processed_results.sort(key=lambda r: score_map.get(str(self._get_result_id(r)), 0.0), reverse=True)

            #۲. اعمال فیلتر 0.7 و محدودیت 5 عدد
            filtered_results = [r for r in processed_results if score_map.get(str(self._get_result_id(r)), 0.0) >= 0.2]
            final_output = filtered_results[:10]

           # فال‌بک در صورتی که هیچکدام بالای 0.7 نبودند (برای خالی نماندن پاسخ)
            if not final_output and processed_results:
                final_output = processed_results[:10]
           
            print(f"[RERANK] Expected: {len(results)}, Received: {len(score_map)}, Filtered (>=0.7): {len(filtered_results)}")
            return final_output

        except Exception as exc:
            print(f"Rerank failed: {exc}")
            # در صورت خطا، همان لیست اولیه را بر اساس امتیاز اولیه مرتب و برگردان
            return sorted(results, key=self._get_result_score, reverse=True)[:10]
  
    def answer_with_rag_stream(
        self,
        query: str,
        results: list[Any],
        on_chunk: StreamCallback,
        temperature: float = 0.1,
        history: str | None = None,
    ) -> None:
        context = self.buildResponseCondidate(results)#self._build_context(results)
        append_qa_to_filetest(context)
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

    # def _build_context(self, results: list[Any]) -> str:
    #     chunks = []   
    #     for i, r in enumerate(results, start=1):
    #         if isinstance(r, dict):
    #             payload = r["payload"]
    #         else:
    #             payload = r.payload
    #         # text = payload.get("text", "")
    #         maintext=payload.get("maintext", "")
    #         doc_id = payload.get("doc_id", "نامشخص")
    #         title = payload.get("title", "")
    #         heading = payload.get("heading", "")
    #         header = f"[سند {i}"
    #         if doc_id:
    #             header += f" - {doc_id}"
    #         if title:
    #             header += f" - {title}"
    #         if heading:
    #             header += f" > {heading}"
    
    #         header += "]"
    #         chunks.append(f"{header}\n{maintext}")
    #     return "\n\n".join(chunks)
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
