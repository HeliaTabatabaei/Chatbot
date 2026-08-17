
import os

from qdrant_client import QdrantClient
from openai import OpenAI

from agent.chat_agent import ChatAgent
from agent.document_agent import DocumentAgent
from agent.router import RouterAgent
from config import OPENAI_API_KEY
from log import append_qa_to_file
from providers.factory import create_provider
from service.rag_service import RAGService



# from RAG_Management.ingestMetaData import ingestBank
# from log import append_qa_to_file

def build_router_agent() -> RouterAgent:
    """
    ساخت کامل Provider، Qdrant، RAGService و Agentها.
    """

    provider = create_provider(
        provider_name="openai",
        base_uri="https://api.gapgpt.app/v1",
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("LLM_MODEL", ""),
        embed_model=os.getenv("EMBED_MODEL", ""),
    )


    qdrant_client = QdrantClient(
        host="localhost",
        port=int(6333)
    )

    rag_service = RAGService(
        llm=provider,
        qdrant_client=qdrant_client,
    )

    chat_agent = ChatAgent(
        llm=provider,
    )

    document_agent = DocumentAgent(
        llm_provider=provider,
        rag_service=rag_service,
    )

    return RouterAgent(
        llm=provider,
        chat_agent=chat_agent,
        document_agent=document_agent,
    )




if __name__ == "__main__":
    path = r"C:\Users\asus\Desktop\test_chunkStudio_revision_08022026\input\2-IT9411-138-00_AudioSystem.docx"
    filename = os.path.basename(path)

    print(filename)
    # router_agent = build_router_agent()



    # def get_embedding(text):
    #   return  router_agent.llm.embed_query(text)
    # queries = [
    #     "شماره کارشناس مستقر در بانک سپه"]
      

    # for q in queries:
    #     results = router_agent.document_agent.rag_service.search(
    #         query_vector=get_embedding(q),
    #         limit= 5
    #     )
    #     print(f"Query: {q}")
    #     for r in results:
    #         text_content = r.payload.get("maintext") or r.payload.get("text") or ""
    #         print(f"  Score: {r.score} | Text: {text_content[:100]}")
    #         append_qa_to_file(f"  Score: {r.score} | Text: {text_content[:100]}")
    #         #print(f"  Score: {r.score} | Text: {r.payload.get('text')[:100]}")
    #     print("---")
