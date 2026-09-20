from __future__ import annotations

from logging import Filter
import time
from typing import Any, Callable, Optional, Tuple
import uuid

from SQlDB.db import DatabaseConnection
# from SQlDB.message import update_and_get_bank_name
from SQlDB.dbManagement import SQL_SERVER_CONNECTION_STRING, get_conversation_history, save_conversation, save_message
from SQlDB.wallet import InsertIntoWallet
from Utility.log import append_qa_to_file,append_qa_to_filetest,append_qa_to_fileWithConvertion
from providers.base import LLMProvider
from service.customer_config import load_customers, resolve_customer_from_query
from fastapi import APIRouter, BackgroundTasks
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
        second_llm: LLMProvider,

        chat_agent: ChatAgent,
        document_agent: DocumentAgent,
        dashboard_agent=DashboardAgent

    ):
        self.llm = llm
        self.chat_agent = chat_agent
        self.document_agent = document_agent
        self.dashboard_agent = dashboard_agent
        self.second_llm = second_llm

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
    def rewrite_query(self, query: str, history_text: str) -> tuple[str, dict]:
        if not history_text:
            return query, {}
        prompt = rewriteQueryPrompt.format(
        history_text=history_text,
        query=query,)
        messages = [
            {"role": "system", "content": prompt},
        ]
        response = self.second_llm.chat(
            messages=messages,
            temperature=0,
        )
        print ("13333333",flush=True)
        print (response,flush=True)
        return str(response.content).strip(), (response.usage)
        
    
    
    def classify(self, query: str) ->  tuple[str, dict]:
        messages = [
        {"role": "system", "content": system_promptClassify},
        {"role": "user", "content": query.strip()},
    ]
        response = self.second_llm.chat(
            messages=messages,
            temperature=0, # برای دقت بالاتر در دسته‌بندی
        )

        result = (response.content or "").strip().lower()

        

        # اعتبارسنجی خروجی برای جلوگیری از خطاهای احتمالی
        valid_labels = {"technical", "general", "no_authorize","dashboard"}
        
        if result not in valid_labels:
            # در صورت خروجی نامعتبر، برای امنیت بیشتر روی no_authorize یا برای کارکرد روی technical ست کنید
            return "no_authorize" 

        return result,(response.usage)
   
    
        # def classify(self, query: str, history: str | None = None) ->  tuple[str, dict]:
        #     system_prompt=system_promptClassify
    
        #     history_text = history.strip() if history else "No previous conversation."
    
        #     user_content = f"""
        # Conversation history:
        # {history_text}
    
        # Current user query:
        # {query}
        # """                                                                                                                                   
    
        #     messages = [
        #         {"role": "system", "content": system_prompt},
        #         {"role": "user", "content": user_content},
        #     ]
    
        #     response = self.second_llm.chat(
        #         messages=messages,
        #         temperature=0, # برای دقت بالاتر در دسته‌بندی
        #     )
    
        #     result = (response.content or "").strip().lower()
    
            
    
        #     # اعتبارسنجی خروجی برای جلوگیری از خطاهای احتمالی
        #     valid_labels = {"technical", "general", "no_authorize","dashboard"}
            
        #     if result not in valid_labels:
        #         # در صورت خروجی نامعتبر، برای امنیت بیشتر روی no_authorize یا برای کارکرد روی technical ست کنید
        #         return "no_authorize" 
    
        #     return result,(response.usage)
       
    def handle_stream(
        self,
        background_tasks: BackgroundTasks,
        query: str,
        convertionId:str,
        UserKey:str,
        on_chunk: ChunkCallback,
        history: any,
        temperature: float = 0.1
       
        
    ) -> None:
        history_text= "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
      
        start1=time.time()
        print("12222",flush=True)
        rewrite_query,final_usage=self.rewrite_query(query,history_text)
        print("3333",flush=True)
        print(final_usage)
        #save usage 0   state provider
        background_tasks.add_task(
                        InsertIntoWallet,
                        final_usage.get("total_tokens", 0) * -1,
                        final_usage.get("output_tokens", 0),
                        final_usage.get("input_tokens", 0),
                        UserKey,
                        convertionId,
                        final_usage.get("Provider"),
                        "rewrite_query"
                    )                            
        
        print("4444",flush=True)
        append_qa_to_fileWithConvertion(f"rewrite_query time:  {time.time() - start1:.2f} seconds ",convertionId)
        append_qa_to_fileWithConvertion(f"rewrite_query: {rewrite_query} ",convertionId)
        start1=time.time()
        intent,ClassifyUsage = self.classify(rewrite_query)
        print("55555",flush=True)
        #save usage 1   state provider
        background_tasks.add_task(
                                InsertIntoWallet,
                                ClassifyUsage.get("total_tokens", 0) * -1,
                                ClassifyUsage.get("output_tokens", 0),
                                ClassifyUsage.get("input_tokens", 0),
                                UserKey,
                                convertionId,
                                ClassifyUsage.get("Provider"),
                                "classify"
                            )                        
        append_qa_to_fileWithConvertion(f"check question type Time: {time.time() - start1:.2f} seconds",convertionId)
        append_qa_to_fileWithConvertion(f"intent: {intent} ",convertionId)
        if intent == "general":
            self.chat_agent.answer_stream(
                message=rewrite_query,
                on_chunk=on_chunk,
                temperature=temperature,
                history=history_text
            )
            
            # self.second_llm.chat_stream(
            #                 message=rewrite_query,
            #                 on_chunk=on_chunk,
            #                 temperature=temperature
            #             )
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
        #save usage 2  state provider   ????
        append_qa_to_fileWithConvertion(f"vector Query Time: {time.time() - start:.2f} seconds",convertionId)
        query_filter = None
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
        append_qa_to_fileWithConvertion(f"query_filter{query_filter}",convertionId)      
        append_qa_to_fileWithConvertion(f"query_filter{query_filter}",convertionId)    
        self.document_agent.handle_stream(
            background_tasks= background_tasks,
            UserKey=UserKey,
            message=rewrite_query,
            convertionId=convertionId,
            original_query=  query,      
            on_chunk=on_chunk,
            query_vector=query_vector,
            temperature=temperature,
            history=history_text,
            query_filter=query_filter)
