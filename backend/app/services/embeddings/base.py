from abc import ABC, abstractmethod

class EmbeddingProvider(ABC):
    """
    Abstract interface for swappable vector embedding providers.
    All implementations must return a list of float vectors matching the provider's dimension.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns vector dimensionality (e.g. 384 for MiniLM, 1536 for OpenAI)."""
        pass

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds a batch of text strings into vector representations.
        Returns a list of float lists (one vector per input text).
        """
        pass