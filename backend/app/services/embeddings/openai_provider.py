import logging
from openai import OpenAI
from app.services.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI API embedding provider (text-embedding-3-small or text-embedding-ada-002).
    Generates 1536-dimensional dense vectors.
    """

    def __init__(self, api_key: str, model_name: str = "text-embedding-3-small"):
        if not api_key:
            raise ValueError("OpenAI API key must be provided when using OpenAIEmbeddingProvider.")

        logger.info(f"Initializing OpenAI Embedding Provider with model: {model_name}")
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self._dimension = 1536  # Standard dimension for text-embedding-3-small / ada-002

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        cleaned_texts = [t if t.strip() else " " for t in texts]

        response = self.client.embeddings.create(
            input=cleaned_texts,
            model=self.model_name,
        )

        # Extract embeddings sorted by index
        data_sorted = sorted(response.data, key=lambda x: x.index)
        return [item.embedding for item in data_sorted]