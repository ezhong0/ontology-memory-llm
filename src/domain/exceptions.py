"""Domain exceptions.

Custom exceptions for domain layer (business logic errors).
"""


class DomainError(Exception):
    """Base exception for all domain errors."""



class EntityResolutionError(DomainError):
    """Error during entity resolution."""



class AmbiguousEntityError(EntityResolutionError):
    """Multiple entities matched with equal confidence.

    Indicates ambiguity that requires clarification from user.

    Attributes:
        mention_text: The ambiguous mention
        candidates: List of (entity_id, confidence) tuples
        entities: Optional list of full entity dicts with details (canonical_name, properties, etc)
    """

    def __init__(
        self,
        mention_text: str,
        candidates: list[tuple[str, float]],
        entities: list[dict[str, any]] | None = None,
        message: str | None = None,
    ):
        self.mention_text = mention_text
        self.candidates = candidates
        self.entities = entities or []
        super().__init__(
            message or f'Ambiguous mention "{mention_text}": {len(candidates)} candidates'
        )


class InvalidMessageError(DomainError):
    """Invalid chat message (validation error)."""



class LLMServiceError(DomainError):
    """Error communicating with LLM service."""



class EmbeddingError(DomainError):
    """Error generating embeddings."""



class RepositoryError(DomainError):
    """Error in repository operation."""

