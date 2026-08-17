from __future__ import annotations

import json
import re
import time
from typing import Any

from log import append_qa_to_file
from providers.base import LLMProvider, StreamCallback


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

        system_prompt = """
You are a technical support decision-maker for banking equipment.
Your goal is to decide whether to answer a technical query, ask for clarification, or reject the query based on provided documents.

--- CONTEXT DATA ---

1. Previous conversation history:
{history}

2. User question:
{query}

3. Retrieved documents (Chunks):
{chunks}

--- MANDATORY DECISION RULES ---

1. Bank Specificity Check:
   - A document is "Bank-Specific" if its `customer_name` (or metadata/text) identifies a specific bank (e.g., refaah, sepah, melli).
   - A document is "General" if its `customer_name` is: General, All, Common, Unknown, None, or empty.
   - RULE: If retrieved chunks are Bank-Specific, but the bank name is NOT mentioned in the current query or history, you MUST return "clarify" and ask for the bank name.
   - EXCEPTION: If all relevant chunks are "General", do NOT ask for the bank name.

2. Decision Labels:
   - "answer": Use when documents clearly contain the solution and required technical context (model, bank, error code) is present in query, history, or chunks are general.
   - "clarify": Use when:
        a) Documents are bank-specific but bank is unknown.
        b) Documents are relevant but lack specific details like device model or error code needed to distinguish between two solutions.
        c) The query is ambiguous.
   - "insufficient": Use when documents are irrelevant, or the query is non-technical (e.g., political, social, or unrelated to banking hardware).

3. Handling OCR and Images:
   - If a chunk contains `ocr_text` or `visual_description`, treat it as high-priority technical evidence.
   - Do NOT ignore image-based data when making a decision.

4. Constraints:
   - Do NOT ask for clarification if the question is short but the solution is obvious from the documents.
   - Never invent technical solutions. If the info isn't in the chunks, it's "insufficient".
   - If the user asks for things like passwords, security bypasses, or political/economic opinions, return "insufficient" or ask for a technical context.

--- OUTPUT FORMAT (JSON ONLY) ---

Return a valid JSON object with these keys:

{{
  "decision": "answer | clarify | insufficient",
  "confidence": 0-100,
  "missing_information": [
    "List specific missing technical info (e.g., bank name, ATM model, error code)"
  ],
  "clarification_question": "A polite, technical Persian question to get the missing info, or null."
}}

Example for missing bank:
{{
  "decision": "clarify",
  "confidence": 95,
  "missing_information": ["bank_name"],
  "clarification_question": "لطفاً بفرمایید دستگاه یا سرویس مورد نظر مربوط به کدام بانک است؟"
}}
"""
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
        print(f"response: {response}", flush=True)
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
            print(f"Parsed decision: {decision}", flush=True)
            
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
            limit=20,
            filters=None,
        ) 
        append_qa_to_file(f"Rag search: {time.time() - start:.2f} seconds")
        start=time.time()
        if not results:
            on_chunk({"type": "token", "content": "هیچ سند مرتبطی یافت نشد."})
            return
        reranked_results = self.rag_service.rerank_results(
            query=message,
            results=results,
            history=history,
        )
        append_qa_to_file(f"Rank Query Time: {time.time() - start:.2f} seconds")
        start=time.time()
        prepared_chunks =self.prepare_chunks(reranked_results)

        on_chunk({
            "type": "source_chunks",
            "chunks": prepared_chunks,
        })

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
