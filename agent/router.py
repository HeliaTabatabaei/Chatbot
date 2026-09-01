from __future__ import annotations

from logging import Filter
import time
from typing import Any, Callable, Optional, Tuple
import uuid

from SQlDB.db import DatabaseConnection
# from SQlDB.message import update_and_get_bank_name
from SQlDB.dbManagement import SQL_SERVER_CONNECTION_STRING, get_conversation_history, save_conversation, save_message
from Utility.log import append_qa_to_file,append_qa_to_filetest,append_qa_to_fileWithConvertion
from providers.base import LLMProvider
from service.customer_config import load_customers, resolve_customer_from_query

from .chat_agent import ChatAgent
from .document_agent import DocumentAgent
from .dashboard_agent import DashboardAgent
from Prompt.prompt_RewriteQuery import rewriteQueryPrompt 
from Prompt.prompt_Classify import system_promptClassify
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)
ChunkCallback = Callable[[Any], None]


class RouterAgent:
    def __init__(
        self,
        llm: LLMProvider,
        chat_agent: ChatAgent,
        document_agent: DocumentAgent,
        dashboard_agent=DashboardAgent

    ):
        self.llm = llm
        self.chat_agent = chat_agent
        self.document_agent = document_agent
        self.dashboard_agent = dashboard_agent
    def build_qdrant_filter(self,
            customer_name: str | None = None,
            device_type: str | None = None,
            device_model: str | None = None,
        ) -> Filter | None:
        must_conditions = []

        # (customer_name = مقدار کاربر OR customer_name = General)
        if customer_name:
            must_conditions.append(
                FieldCondition(
                    key="customer_name",
                    match=MatchAny(any=[customer_name, "General"]),
                )
            )

        # (device_type = مقدار کاربر OR device_type = General)
        if device_type:
            must_conditions.append(
                FieldCondition(
                    key="device_type",
                    match=MatchAny(any=[device_type, "General"]),
                )
            )

        # (device_model = مقدار کاربر OR device_model = General)
        if device_model:
            must_conditions.append(
                FieldCondition(
                    key="device_model",
                    match=MatchAny(any=[device_model, "General"]),
                )
            )

        return Filter(must=must_conditions) if must_conditions else None
    def rewrite_query(self, query: str, history_text: str) -> str:
        if not history_text:
            return query

        prompt = rewriteQueryPrompt.format(
        history_text=history_text,
        query=query,)
        messages = [
            {"role": "system", "content": prompt},
        ]
        response = self.llm.chat(
            messages=messages,
            temperature=0,
        )
        return response.content.strip()
    def classify(self, query: str, history: str | None = None) -> str:
        system_prompt=system_promptClassify

        history_text = history.strip() if history else "No previous conversation."

        user_content = f"""
    Conversation history:
    {history_text}

    Current user query:
    {query}
    """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        response = self.llm.chat(
            messages=messages,
            temperature=0, # برای دقت بالاتر در دسته‌بندی
        )

        result = (response.content or "").strip().lower()

        

        # اعتبارسنجی خروجی برای جلوگیری از خطاهای احتمالی
        valid_labels = {"technical", "general", "no_authorize","dashboard"}
        
        if result not in valid_labels:
            # در صورت خروجی نامعتبر، برای امنیت بیشتر روی no_authorize یا برای کارکرد روی technical ست کنید
            return "no_authorize" 

        return result
   
    
    def handle_stream(
        self,
        query: str,
        convertionId:str,
        on_chunk: ChunkCallback,
        history: any,
        temperature: float = 0.1,
        
    ) -> None:
        history_text= "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
      
        start1=time.time()
        rewrite_query=self.rewrite_query(query,history_text)
        
        append_qa_to_fileWithConvertion(f"rewrite_query: {rewrite_query} ",convertionId)
        start1=time.time()
        intent = self.classify(rewrite_query,history_text)
        append_qa_to_fileWithConvertion(f"check question type Time: {time.time() - start1:.2f} seconds",convertionId)
        append_qa_to_fileWithConvertion(f"intent: {intent} ",convertionId)
        if intent == "general":
            self.chat_agent.answer_stream(
                message=rewrite_query,
                on_chunk=on_chunk,
                temperature=temperature,
                history=history_text
            )
            return
        elif intent=="dashboard":
            self.dashboard_agent.handle_stream(
                    question=query,        
                    on_chunk=on_chunk,
                    
                )    
            return  
        elif intent=="no_authorize":
            on_chunk({
                            "type": "token",
                            "content": "من تنها قادر به پاسخگویی از داکیومنت های شرکت آدونیس می باشم"
                        })
            return
        start=time.time()
        query_vector = self.llm.embed_query(rewrite_query)
        append_qa_to_fileWithConvertion(f"vector Query Time: {time.time() - start:.2f} seconds",convertionId)
        query_filter = None
        # customers = load_customers()
        
        # resolved_customer = resolve_customer_from_query(
        # query=rewrite_query,
        # customers=customers,
        # )
        # if resolved_customer:
     
        #     query_filter=self.build_qdrant_filter(customer_name=resolved_customer["qdrant_customer_name"])
        #     append_qa_to_file(query_filter)      
        # # append_qa_to_file(resolved_customer)  
        query_filter = None
        customers = load_customers()
        
        resolved_customer = resolve_customer_from_query(
        query=rewrite_query,
        customers=customers,
        )
        if resolved_customer:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="customer_name",
                        match=MatchValue(
                            value=resolved_customer["qdrant_customer_name"],
                        ),
                    )
                ]
            )
        append_qa_to_fileWithConvertion(query_filter,convertionId)      
        append_qa_to_fileWithConvertion(resolved_customer,convertionId)    
        self.document_agent.handle_stream(
            message=rewrite_query,
            convertionId=convertionId,
            original_query=  query,      
            on_chunk=on_chunk,
            query_vector=query_vector,
            temperature=temperature,
            history=history_text,
            query_filter=query_filter
        )
