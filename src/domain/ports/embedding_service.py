"""Embedding service port (interface).

Defines the contract for generating embeddings.
"""
from typing import Protocol


class IEmbeddingService(Protocol):
    """Embedding service interface for generating vector embeddings.

    This is a port (interface) used by memory creation services.
    Infrastructure layer implements this using OpenAI Embeddings API.

    Not heavily used in Phase 1A (no retrieval yet), but needed for
    storing embeddings with messages.
    """

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        ...

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        More efficient than calling generate_embedding multiple times.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (same order as input)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        ...

    @property
    def embedding_dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions (e.g., 1536 for text-embedding-3-small)
        """
        ...
