"""Chat model for the agent: any OpenAI-compatible endpoint (Groq, Together, vLLM, Ollama)."""

from langchain_core.language_models import BaseChatModel

from app.config import get_settings


def get_chat_model() -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        base_url=s.llm_provider_base_url,
        api_key=s.llm_provider_api_key or "not-set",
        temperature=0,
        timeout=30,
        max_retries=1,
    )
