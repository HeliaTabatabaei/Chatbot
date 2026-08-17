from __future__ import annotations

import time
from typing import Any, Callable, Optional, Tuple
import uuid

from SQlDB.db import DatabaseConnection
from SQlDB.message import update_and_get_bank_name
from dbManagement import SQL_SERVER_CONNECTION_STRING, get_conversation_history, save_conversation, save_message
from log import append_qa_to_file
from providers.base import LLMProvider
from .chat_agent import ChatAgent
from .document_agent import DocumentAgent

 
ChunkCallback = Callable[[Any], None]


class RouterAgent:
    def __init__(
        self,
        llm: LLMProvider,
        chat_agent: ChatAgent,
        document_agent: DocumentAgent,

    ):
        self.llm = llm
        self.chat_agent = chat_agent
        self.document_agent = document_agent
    # def prepare_final_query(self, history, current_user_message):
    #     if not isinstance(history, list):
    #      return current_user_message

    # # ۱. پیدا کردن آخرین پیام دستیار و موقعیت (Index) آن در تاریخچه
    #     last_assistant_idx = -1
    #     last_assistant_msg = None
        
    #     for idx, msg in enumerate(history):
    #         if isinstance(msg, dict) and msg.get("role") == "assistant":
    #             last_assistant_idx = idx
    #             last_assistant_msg = msg

    #     # اگر پیام دستیاری پیدا نشد، همان پیام فعلی را برگردان
    #     if not last_assistant_msg:
    #             return current_user_message

    #     assistant_content = str(last_assistant_msg.get("content") or "").strip()
        
    #     # بررسی اینکه آیا دستیار سوال پرسیده بود (پشتیبانی از هر دو علامت سوال فارسی و انگلیسی)
    #     is_question = "؟" in assistant_content or "?" in assistant_content
    #     is_short_answer = len(current_user_message.strip().split()) < 5

    #     if is_question and is_short_answer:
    #         # ۲. پیدا کردن سوال اصلی کاربر (اولین پیامِ کاربرِ قبل از پیام دستیار)
    #         original_user_msg = None
    #         for idx in range(last_assistant_idx - 1, -1, -1):
    #             if isinstance(history[idx], dict) and history[idx].get("role") == "user":
    #                 original_user_msg = history[idx]
    #                 break

    #         if original_user_msg:
    #             previous_query = str(original_user_msg.get("content") or "").strip()
    #             # ترکیب سوال اصلی با پاسخ شفاف‌سازی کاربر
    #             return f"{previous_query} {current_user_message}".strip()

    #     return current_user_message
    def rewrite_query(self, query: str, history_text: str) -> str:
       if not history_text:
         return query
       prompt = f"""
       شما یک بازنویس کوئری هستید. وظیفه شما فقط شفاف‌سازی ضمیرها و الحاق نام بانک/موضوع به پیام کاربر است.
       
       قوانین:
       - به هیچ وجه فرض نکن راهکارهای قبلی انجام شده یا شکست خورده است.
       - اگر کاربر گفت "درست نشد" یا "نشد"، سوال را به صورت کلی بازنویسی کن.
       - مثال: 
           تاریخچه: "عکس زرد است" -> کاربر: "نشد" 
           بازنویسی: "راه حل مشکل زرد بودن عکس در بانک فلان چیست؟" (فقط همین)
       - از عباراتی مثل "چه راهکار دیگری وجود دارد" یا "با وجود انجام فلان کار" استفاده نکن.
       
       تاریخچه: {history_text}
       آخرین پیام: {query}
       کوئری مستقل:"""
       
       messages = [
        {"role": "system", "content": prompt},
    ]
    
       response = self.llm.chat(
        messages=messages,
        temperature=0, 
    )
       return response.content.strip()


    def classify(self, query: str, history: str | None = None) -> str:
         
      
        # system_prompt = (
        #     "You are a specialized classifier for a Banking Technical Support system.\n"
        #     "Classify the user query into EXACTLY one of these three labels:\n\n"

        #     "1. technical: Questions about ATM hardware, banking equipment, device errors, "
        #     "troubleshooting, installation, maintenance, printer, pinpad, dispenser,camera "
        #     "card reader, cash handling, or software configuration.\n\n"

        #     "2. general: Greetings (hi, hello), thanks, and polite small talk.\n\n"
            
        #     "3. no_authorize: Any questions regarding politics, macroeconomics, "
        #     "system security bypasses, or sensitive non-technical banking information.\n\n"

        #     "Rules:\n"
        #     "- Use the conversation history only to resolve pronouns or context.\n"
        #     "- If the query is political or economic, it MUST be 'no_authorize'.\n"
        #     "- Return ONLY the label: technical, general, or no_authorize."
        # )
        system_prompt = (
            "You are a specialized classifier for a Banking Technical Support system.\n"
            "Classify the user query into EXACTLY one of these three labels:\n\n"

            "1. technical: Questions about ATM hardware, banking equipment, device errors, "
            "troubleshooting, installation, maintenance, printer, pinpad, dispenser, camera, "
            "card reader, cash handling, software configuration, AND inquiries about "
            "support contacts, help-desk numbers, and technical assistance procedures.\n\n"

            "2. general: Greetings (hi, hello), thanks, and polite small talk.\n\n"
            
            "3. no_authorize: Any questions regarding politics, macroeconomics, "
            "system security bypasses, sensitive non-technical banking account information, "
            "or personal financial details.\n\n"

            "Rules:\n"
            "- Use the conversation history only to resolve pronouns or context.\n"
            "- If the query is political or economic, it MUST be 'no_authorize'.\n"
            "- If the query is about support contact information, phone numbers, or how to get help for banking equipment, it MUST be 'technical'.\n"
            "- Return ONLY the label: technical, general, or no_authorize."
        )

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

        # برای دیباگ در کنسول
        print(f"--- Classification result: {result} ---", flush=True)

        # اعتبارسنجی خروجی برای جلوگیری از خطاهای احتمالی
        valid_labels = {"technical", "general", "no_authorize"}
        
        if result not in valid_labels:
            # در صورت خروجی نامعتبر، برای امنیت بیشتر روی no_authorize یا برای کارکرد روی technical ست کنید
            return "no_authorize" 

        return result
    # def resolve_customer_name(self, user_text: str) -> str | None:
        
    #     user_text = str(user_text or "").strip()
    #     if not user_text:
    #         return None

    #     try:
            
    #         query_vector = self.llm_provider.embed_query(user_text)
    #         append_qa_to_file(f"vector Query Time: {time.time() - start:.2f} seconds")
    #                 start=time.time()
    #                 results = self.rag_service.search(
    #                     query_vector=query_vector,
    #                     limit=20,
    #                     filters=None,
    #                 )

    #         # ۲. جستجو در کالکشن BankName
    #         search_result = self.qdrant.query_points(
    #             collection_name="BankName",
    #             query=query_vector,
    #             using="dense",
    #             limit=1,
    #             with_payload=True,
    #             score_threshold=0.80  # آستانه شباهت (قابل تنظیم)
    #         )

    #         if not search_result.points:
    #             return None

    #         # ۳. استخراج نام بانک از Payload (فیلد text در تصویر شما موجود است)
    #         payload = search_result.points[0].payload
    #         bank_name = payload.get("text")
            
    #         return bank_name.strip() if bank_name else None

    #     except Exception as e:
    #         print(f"Error in resolve_customer_name: {e}", flush=True)
    #         return None

    
    def handle_stream(
        self,
        query: str,
        convertionId:str,
        on_chunk: ChunkCallback,
        history: any,
        temperature: float = 0.1,
        
    ) -> None:
        history_text= "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        append_qa_to_file(history_text)
        # start=time.time()
        # query_vector = self.llm.embed_query(query)
        # append_qa_to_file(f"vector Query Time: {time.time() - start:.2f} seconds")
        #meta_hits= self.document_agent.rag_service.searchMetaData(
 


        start1=time.time()
        rewrite_query=self.rewrite_query(query,history_text)
        append_qa_to_file(f"rewrite_query : {rewrite_query}")
        append_qa_to_file(f"rewriteQuery: {time.time() - start1:.2f} seconds")

        start1=time.time()
        intent = self.classify(rewrite_query,history_text)
        append_qa_to_file(f"check question type Time: {time.time() - start1:.2f} seconds")
        append_qa_to_file(f"intent: {intent} ")
        print (intent,flush=True)


        if intent == "general":
            self.chat_agent.answer_stream(
                message=rewrite_query,
                on_chunk=on_chunk,
                temperature=temperature,
                history=history_text
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
        append_qa_to_file(f"vector Query Time: {time.time() - start:.2f} seconds")
        self.document_agent.handle_stream(
            message=query,        
            on_chunk=on_chunk,
            query_vector=query_vector,
            temperature=temperature,
            history=history_text,
        )
