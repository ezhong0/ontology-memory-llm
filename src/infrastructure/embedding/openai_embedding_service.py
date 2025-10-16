"""OpenAI embedding service implementation.

Implements IEmbeddingService using OpenAI's embedding API.
"""

import structlog
from openai import AsyncOpenAI

from src.domain.exceptions import EmbeddingError
from src.domain.ports import IEmbeddingService

logger = structlog.get_logger(__name__)


class OpenAIEmbeddingService(IEmbeddingService):
    """OpenAI implementation of IEmbeddingService.

    Uses text-embedding-3-small model for generating embeddings.
    - 1536 dimensions
    - Cost: $0.00002 per 1K tokens
    - Fast and efficient for memory embeddings
    """

    # Model configuration
    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    MAX_BATCH_SIZE = 100  # OpenAI limit

    def __init__(self, api_key: str):
        """Initialize OpenAI embedding service.

        Args:
            api_key: OpenAI API key
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self._total_tokens_used = 0

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to embed (max ~8000 tokens for text-embedding-3-small)

        Returns:
            Embedding vector (1536 dimensions)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            if not text or not text.strip():
                msg = "Cannot generate embedding for empty text"
                raise EmbeddingError(msg)

            logger.debug(
                "generating_embedding",
                text_length=len(text),
                model=self.MODEL,
            )

            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=text,
                dimensions=self.DIMENSIONS,
            )

            if not response.data:
                msg = "No embedding data in response"
                raise EmbeddingError(msg)

            embedding = response.data[0].embedding

            # Track usage
            tokens_used = response.usage.total_tokens
            self._total_tokens_used += tokens_used

            logger.debug(
                "embedding_generated",
                text_length=len(text),
                tokens=tokens_used,
                total_tokens=self._total_tokens_used,
            )

            return embedding

        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(
                "embedding_generation_error",
                text_length=len(text),
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Failed to generate embedding: {e}"
            raise EmbeddingError(msg) from e

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts in batch.

        More efficient than calling generate_embedding multiple times.

        Args:
            texts: List of texts to embed (max 100 per batch)

        Returns:
            List of embedding vectors (same order as input)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        try:
            # Filter out empty texts
            valid_texts = [t for t in texts if t and t.strip()]
            if not valid_texts:
                msg = "All texts are empty"
                raise EmbeddingError(msg)

            if len(valid_texts) > self.MAX_BATCH_SIZE:
                msg = f"Batch size {len(valid_texts)} exceeds max {self.MAX_BATCH_SIZE}"
                raise EmbeddingError(
                    msg
                )

            logger.debug(
                "generating_embeddings_batch",
                count=len(valid_texts),
                model=self.MODEL,
            )

            response = await self.client.embeddings.create(
                model=self.MODEL,
                input=valid_texts,
                dimensions=self.DIMENSIONS,
            )

            if not response.data or len(response.data) != len(valid_texts):
                msg = f"Expected {len(valid_texts)} embeddings, got {len(response.data)}"
                raise EmbeddingError(
                    msg
                )

            # Extract embeddings in order
            embeddings = [item.embedding for item in response.data]

            # Track usage
            tokens_used = response.usage.total_tokens
            self._total_tokens_used += tokens_used

            logger.info(
                "embeddings_batch_generated",
                count=len(embeddings),
                tokens=tokens_used,
                total_tokens=self._total_tokens_used,
            )

            return embeddings

        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(
                "embeddings_batch_error",
                count=len(texts),
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Failed to generate embeddings batch: {e}"
            raise EmbeddingError(msg) from e

    @property
    def embedding_dimensions(self) -> int:
        """Get embedding vector dimensions.

        Returns:
            Number of dimensions (1536 for text-embedding-3-small)
        """
        return self.DIMENSIONS

    @property
    def total_tokens_used(self) -> int:
        """Get total tokens used by this service instance.

        Returns:
            Total tokens used for embeddings
        """
        return self._total_tokens_used

    @property
    def estimated_cost(self) -> float:
        """Get estimated cost for embeddings generated.

        Returns:
            Estimated cost in USD ($0.00002 per 1K tokens)
        """
        return (self._total_tokens_used / 1000) * 0.00002
