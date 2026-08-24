from __future__ import annotations

import json
import re
import time
from typing import Any

from Utility.log import append_qa_to_file, append_qa_to_filetest
from providers.base import LLMProvider, StreamCallback
from Prompt.prompt_Analiys import system_promptAnaliys

class DocumentAgent:
    def __init__(self, llm_provider: LLMProvider, rag_service):
        self.llm_provider = llm_provider
        self.rag_service = rag_service

    # -------------------



    

    def analyze(
        self,
        message: str,     
        chunks: list[dict[str, Any]],
        history : str | None = None
    ) -> dict[str, Any]:
        system_prompt =system_promptAnaliys

        messages = [
            {
                "role": "system",
                "content": system_prompt.format(
                    query=message,
                    history=json.dumps(
                        history or [],
                        ensure_ascii=False,
                        indent=2
                    ),
                    chunks=json.dumps(
                        chunks,
                        ensure_ascii=False,
                        indent=2
                    ),
                ),
            },
            {
                "role": "user",
                "content": message,
            },
        ]

        response = self.llm_provider.chat(
            messages=messages,
            temperature=0,
        )
      
        raw_content = (response.content or "").strip()
        usage = getattr(response, "usage", {}) or {}
        # تلاش برای استخراج دقیق بلاک JSON
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(0)
        else:
            print(f"Failed to extract JSON from response: {raw_content}", flush=True)
            raw_content = ""

        try:
            result = json.loads(raw_content)
            
            valid_decisions = {"answer", "clarify", "insufficient"}
            decision = result.get("decision")
            
            
            if decision not in valid_decisions:
                decision = "insufficient"

            return {
                "decision": decision,
                "confidence": result.get("confidence", 0),
                "missing_information": result.get("missing_information", []),
                "clarification_question": result.get("clarification_question"),
                "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
    },
            }

        except (json.JSONDecodeError, Exception) as e:
            print(f"Parsing error: {e}", flush=True)
            return {
                "decision": "insufficient",
                "confidence": 0,
                "missing_information": [],
                "clarification_question": None,
                "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
    },
            }

        # =====================


    def prepare_chunks(
        self,
        chunks: list[Any],
        ) -> list[dict[str, Any]]:

        output = []
       
        for chunk in chunks:
            docid=chunk.payload.get("doc_id", "")

            output.append(
                {
                    "id": str(chunk.id),
                    "score": chunk.score,
                    "text": chunk.payload.get(
                        "text",
                        ""
                    ),
                    "meta": {
                        "customer_name": chunk.payload.get("customer_name", ""),
                        "vendor_name": chunk.payload.get("vendor_name", ""),
                        "service_type": chunk.payload.get("service_type", ""),
                        "keywords": chunk.payload.get("keywords", []),
                        "heading": chunk.payload.get("heading_path", ""),
                        "source_file": self.rag_service.getSourceFilePath(chunk.payload.get("source_file", ""), docid),
                        "image_paths": self.rag_service.getListofImagepath(chunk.payload.get("imgs_info", []), docid),

                    }        
                  
                }
            )

        return output
    


    def handle_stream(
        self,
        message: str,
        on_chunk: StreamCallback,
        query_vector: Any,
        temperature: float = 0.1,
        history: list[dict[str, Any]] | None = None,
    ) -> None:
        start=time.time()
        results = self.rag_service.search(
            query_vector=query_vector,
            limit=10,
            filters=None,
        ) 
        append_qa_to_file(f"Rag search: {time.time() - start:.2f} seconds")
        start=time.time()
        if not results:
            on_chunk({"type": "token", "content": "هیچ سند مرتبطی یافت نشد."})
            return
        append_qa_to_filetest(results)
        reranked_results = self.rag_service.rerank_results(
            query=message,
            results=results,
            history=history,
        )
        append_qa_to_file(f"Rank Query Time: {time.time() - start:.2f} seconds")
        append_qa_to_filetest(reranked_results)
        start=time.time()
        
        prepared_chunks =self.prepare_chunks(reranked_results)
        
        on_chunk({
            "type": "source_chunks",
            "chunks": prepared_chunks,
        })
        append_qa_to_file("anylis start")
        analysis = self.analyze(
            message=message,
            chunks=prepared_chunks,
            history=history,
        )
        append_qa_to_file(f"analysis time: {time.time() - start:.2f} seconds")
        decision = analysis.get("decision")

        if decision == "answer":
            append_qa_to_file(f"start genrate stream: {time.time():.2f} ")
            self.rag_service.answer_with_rag_stream(
                query=message,
                results=reranked_results,
                temperature=temperature,
                on_chunk=on_chunk,
                history=history
            )
            return

        usage_data = analysis.get("usage")
        if usage_data:
            on_chunk({
                "type": "meta",
                "response_id": "1111",
                "usage": usage_data
            })

        if decision == "clarify":
            question = analysis.get("clarification_question")
            on_chunk({
                "type": "token",
                "content": question or "لطفاً اطلاعات بیشتری درباره مشکل دستگاه ارسال کنید."
            })
            return

        on_chunk({
            "type": "token",
            "content": "اطلاعات کافی برای پاسخ دقیق پیدا نشد."
        })
