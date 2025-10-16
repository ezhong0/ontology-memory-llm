"""Conversation context value object.

Represents conversation context needed for entity resolution (immutable).
"""
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ConversationContext:
    """Immutable conversation context for entity resolution.

    Provides context needed for coreference resolution and disambiguation:
    - Recent messages for pronoun resolution
    - Recently mentioned entities
    - Current session information

    Attributes:
        user_id: User ID (for user-specific aliases)
        session_id: Current conversation session ID
        recent_messages: Recent messages (for coreference), most recent last
        recent_entities: Recently mentioned entity IDs (for coreference)
        current_message: The current message being processed
    """

    user_id: str
    session_id: UUID
    recent_messages: list[str]  # Last N messages for context
    recent_entities: list[tuple[str, str]]  # (entity_id, canonical_name) pairs
    current_message: str

    def __post_init__(self) -> None:
        """Validate conversation context invariants."""
        if not self.user_id:
            msg = "user_id cannot be empty"
            raise ValueError(msg)
        if not self.current_message:
            msg = "current_message cannot be empty"
            raise ValueError(msg)

    @property
    def has_recent_entities(self) -> bool:
        """Check if there are recently mentioned entities.

        Returns:
            True if recent_entities is not empty
        """
        return len(self.recent_entities) > 0

    @property
    def context_summary(self) -> str:
        """Get a summary of context for LLM prompts.

        Returns:
            Formatted context string with recent messages and entities
        """
        lines = []

        # Recent messages
        if self.recent_messages:
            lines.append("Recent conversation:")
            for i, msg in enumerate(self.recent_messages[-3:], 1):  # Last 3 messages
                lines.append(f"  {i}. {msg}")

        # Recently mentioned entities
        if self.recent_entities:
            lines.append("\nRecently mentioned entities:")
            for entity_id, name in self.recent_entities[-5:]:  # Last 5 entities
                lines.append(f"  - {name} (id: {entity_id})")

        return "\n".join(lines) if lines else "No recent context"

    def get_most_recent_entity(self) -> tuple[str, str] | None:
        """Get the most recently mentioned entity.

        Returns:
            (entity_id, canonical_name) tuple, or None if no recent entities
        """
        return self.recent_entities[-1] if self.recent_entities else None

    def __str__(self) -> str:
        """String representation for logging."""
        entity_count = len(self.recent_entities)
        message_count = len(self.recent_messages)
        return (
            f"Context(user={self.user_id}, session={self.session_id}, "
            f"recent_messages={message_count}, recent_entities={entity_count})"
        )
