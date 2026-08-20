import logging
from app.config import settings
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.local import LocalSentenceTransformerProvider
from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)

_provider_instance: EmbeddingProvider | None = None

def get_embedding_provider() -> EmbeddingProvider:
    """
    Factory function returning the configured EmbeddingProvider singleton.
    Switches between local sentence-transformers and OpenAI API based on settings.
    """
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_type = settings.EMBEDDING_PROVIDER.lower()

    if provider_type == "local":
        _provider_instance = LocalSentenceTransformerProvider(
            model_name=settings.EMBEDDING_MODEL_NAME
        )
    elif provider_type == "openai":
        _provider_instance = OpenAIEmbeddingProvider(
            api_key=settings.OPENAI_API_KEY or "",
            model_name=settings.OPENAI_EMBEDDING_MODEL,
        )
    else:
        raise ValueError(
            f"Unsupported EMBEDDING_PROVIDER '{provider_type}'. Must be 'local' or 'openai'."
        )

    return _provider_instance

def reset_embedding_provider():
    """Resets the singleton instance (useful for unit testing switching providers)."""
    global _provider_instance
    _provider_instance = None