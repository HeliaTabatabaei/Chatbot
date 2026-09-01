
import os

from qdrant_client import QdrantClient
from openai import OpenAI

from agent.chat_agent import ChatAgent
from agent.document_agent import DocumentAgent
from agent.router import RouterAgent
from config import OPENAI_API_KEY,provider_URL,LLM_MODEL,EMBED_MODEL

from providers.factory import create_provider
from service.rag_service import RAGService





def build_router_agent() -> RouterAgent:
    """
    ساخت کامل Provider، Qdrant، RAGService و Agentها.
    """

    provider = create_provider(
        provider_name="openai",
        #base_uri="https://api.gapgpt.app/v1",
        base_uri=provider_URL,
        api_key=OPENAI_API_KEY,
        model=LLM_MODEL,
        embed_model=EMBED_MODEL,
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

  
