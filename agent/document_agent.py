from __future__ import annotations

import json
import re
import time
from typing import Any

from Utility.log import append_qa_to_file, append_qa_to_filetest,append_qa_to_fileWithConvertion

from providers.base import LLMProvider, StreamCallback
from Prompt.prompt_Analiys import system_promptAnaliys

class DocumentAgent:
    def __init__(self, llm_provider: LLMProvider,second_llm: LLMProvider,
 rag_service):
        self.llm_provider = llm_provider
        self.second_llm = second_llm


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

        response = self.second_llm.chat(
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
                        "device_type": chunk.payload.get("device_type", ""),
                        "device_model": chunk.payload.get("device_model", ""),
                        "service_type": chunk.payload.get("service_type", ""),
                        "service_group": chunk.payload.get("service_group", ""),
                        "service_name": chunk.payload.get("service_name", ""),
                        "keywords": chunk.payload.get("keywords", []),
                        "heading": chunk.payload.get("heading_path", "") 
                    }        
                }
            )

        return output
    


    def handle_stream(
        self,
        message: str,  #rewritten_query
        convertionId:str,
        original_query:str,
        on_chunk: StreamCallback,
        query_vector: Any,
        temperature: float = 0.1,
        history: list[dict[str, Any]] | None = None,
        query_filter: list[dict[str, Any]] | None = None,
    ) -> None:
        start=time.time()
        results = self.rag_service.search(
            query_vector=query_vector,
            limit=10,
            filters=query_filter,
        ) 
        append_qa_to_fileWithConvertion(f"Rag search: {time.time() - start:.2f} seconds",convertionId)
        start=time.time()
        if not results:
            on_chunk({"type": "token", "content": "هیچ سند مرتبطی یافت نشد."})
            return
        reranked_results = self.rag_service.rerank_results(
            original_query=original_query,
            rewritten_query=message,
            results=results,
        ) or []
        if not reranked_results and results:
            append_qa_to_fileWithConvertion("not reranked_results and results",convertionId)
            reranked_results = results
        append_qa_to_fileWithConvertion(f"Rank Query Time: {time.time() - start:.2f} seconds",convertionId)
        start=time.time()
        append_qa_to_fileWithConvertion(f"reranked_results: {reranked_results} ",convertionId)
        prepared_chunks =self.prepare_chunks(reranked_results)
        
        on_chunk({
            "type": "source_chunks",
            "chunks": prepared_chunks,
        })
        append_qa_to_fileWithConvertion("anylis start",convertionId)
        analysis = self.analyze(
            message=message,
            chunks=prepared_chunks,
            history=history,
        )
        append_qa_to_fileWithConvertion(f"analysis time: {time.time() - start:.2f} seconds",convertionId)
        decision = analysis.get("decision")

        if decision == "answer":
            append_qa_to_fileWithConvertion(f"start genrate stream: {time.time() - start:.2f} seconds",convertionId)
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
