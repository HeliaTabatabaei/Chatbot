from openai import OpenAI

from .openai_provider import OpenAIProvider
from .deepseewk_provider import DeepSeekProvider


PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "deepSeek":DeepSeekProvider
}


def create_provider(
    provider_name: str,
    base_uri: str,
    api_key: str,
    model: str,
    embed_model: str,
):
    provider_cls = PROVIDER_MAP.get(
        provider_name.lower(),
        OpenAIProvider,
    )
    
    if provider_cls is OpenAIProvider:
        client = OpenAI(
            base_url=base_uri,
            api_key=api_key,
        )

        return provider_cls(
            client=client,
            chat_model=model,
            embedding_model=embed_model,
        )

    return provider_cls(
        base_uri=base_uri,
        api_key=api_key,
        model=model,
        embed_model=embed_model,
    )
    
    
