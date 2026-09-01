from providers.base import LLMProvider, StreamCallback
from service.dashboard_llm_service import dashboard_llm_service

class DashboardAgent:
    
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
       
        self.dashboard_llm_service=dashboard_llm_service(llm=self.llm_provider)

    
    def handle_stream(
        self,
        question: str,
        on_chunk: StreamCallback,
    ) -> None:
        sql_query = self.dashboard_llm_service.generate_sql( user_question=question)
        
        if "اطلاعات فقط از سال 1404 به بعد در دسترس است" in sql_query:
            on_chunk({
                "type": "token",
                "content": "اطلاعات فقط از سال 1404 به بعد در دسترس است."
        })
            return
       
        
        # ارسال خود SQL به خرجی Stream
        on_chunk({
            "type": "sql",
            "content": sql_query,
        })
        data =self.dashboard_llm_service.run_sqlQuery(sql_query)
     
        self.dashboard_llm_service.generate_answer_stream(
         
            question=question,
            data=data,
            on_chunk=on_chunk,
        )
     