import logging
from sentence_transformers import SentenceTransformer
from app.services.embeddings.base import EmbeddingProvider

logger = logging.getLogger(__name__)

class LocalSentenceTransformerProvider(EmbeddingProvider):
    """
    Local CPU/GPU embedding provider using sentence-transformers (all-MiniLM-L6-v2).
    Generates 384-dimensional dense vectors with zero API cost.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Initializing local SentenceTransformer model: {model_name}")
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        self._dimension = self._model.get_sentence_embedding_dimension()

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        # Convert empty or whitespace-only strings to a fallback placeholder space
        cleaned_texts = [t if t.strip() else " " for t in texts]

        # Generate embeddings as numpy array, convert to standard Python float lists
        embeddings = self._model.encode(
            cleaned_texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Cosine similarity optimization
        )

        return embeddings.tolist()