"""Entity mention value object.

Represents a mention of an entity in conversational text (immutable).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMention:
    """Immutable value object representing an entity mention in text.

    An entity mention is any reference to a real-world entity (person, company,
    order, product, etc.) in conversation. This value object captures the mention
    text, position, and whether it requires coreference resolution.

    Attributes:
        text: The actual text of the mention (e.g., "Acme Corp", "they", "the customer")
        position: Character position in the message where mention starts
        context_before: Text before the mention (for coreference resolution)
        context_after: Text after the mention (for coreference resolution)
        is_pronoun: Whether this is a pronoun requiring coreference (e.g., "they", "it")
        sentence: Full sentence containing the mention
    """

    text: str
    position: int
    context_before: str
    context_after: str
    is_pronoun: bool
    sentence: str

    def __post_init__(self) -> None:
        """Validate mention invariants."""
        if not self.text:
            msg = "Entity mention text cannot be empty"
            raise ValueError(msg)
        if self.position < 0:
            msg = "Entity mention position cannot be negative"
            raise ValueError(msg)
        if len(self.text) > 500:
            msg = "Entity mention text too long (max 500 characters)"
            raise ValueError(msg)

    @property
    def requires_coreference(self) -> bool:
        """Check if this mention requires coreference resolution.

        Returns:
            True if mention is a pronoun or demonstrative that needs context resolution
        """
        return self.is_pronoun

    @property
    def context_window(self) -> str:
        """Get full context window for coreference resolution.

        Returns:
            Combined context: before + mention + after
        """
        return f"{self.context_before} {self.text} {self.context_after}".strip()

    def __str__(self) -> str:
        """String representation for logging."""
        pronoun_marker = " [PRONOUN]" if self.is_pronoun else ""
        return f'"{self.text}"{pronoun_marker} at position {self.position}'
