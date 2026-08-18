from providers.base import LLMProvider, StreamCallback
from service.dashboard_llm_service import dashboard_llm_service



# class DashboardAgent:
#     def __init__(self, llm_provider: LLMProvider):
#         self.llm_provider = llm_provider

#     def handle_stream(
#         self,
#         question: str,
#         on_chunk: StreamCallback,
#     ) -> None:
#         generate_answer_stream(
#             llm=self.llm_provider,
#             question=question,
#             on_chunk=on_chunk,
#         )
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
        print("Endsql_query")
        data =self. dashboard_llm_service.run_sqlQuery(sql_query)
        print("Endrun_sqlQuery")
        self.dashboard_llm_service.generate_answer_stream(
         
            question=question,
            data=data,
            on_chunk=on_chunk,
        )
        print("Endgenerate_answer_stream")