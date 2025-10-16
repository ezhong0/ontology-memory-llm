"""Chat message domain model.

Represents a message in a conversation (domain representation).
"""
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID


@dataclass
class ChatMessage:
    """Domain entity representing a chat message.

    This is the domain representation (not the persistence model).
    Maps to chat_events table but focuses on business logic.

    Attributes:
        event_id: Unique event identifier (set by repository after persistence)
        session_id: Conversation session ID
        user_id: User who sent/received the message
        role: Message role (user | assistant | system)
        content: Message content
        content_hash: Hash of content for deduplication
        event_metadata: Additional metadata (optional)
        created_at: Message timestamp
    """

    session_id: UUID
    user_id: str
    role: str  # user | assistant | system
    content: str
    event_id: int | None = None  # Set by repository after persistence
    content_hash: str | None = None  # Auto-computed if not provided
    event_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Validate message invariants and compute content hash."""
        if not self.user_id:
            msg = "user_id cannot be empty"
            raise ValueError(msg)
        if not self.content:
            msg = "content cannot be empty"
            raise ValueError(msg)

        valid_roles = {"user", "assistant", "system"}
        if self.role not in valid_roles:
            msg = f"role must be one of {valid_roles}, got: {self.role}"
            raise ValueError(msg)

        # Auto-compute content hash if not provided
        if self.content_hash is None:
            self.content_hash = self._compute_content_hash()

    def _compute_content_hash(self) -> str:
        """Compute SHA-256 hash of content for deduplication.

        Returns:
            Hex digest of content hash
        """
        content_bytes = self.content.encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    def is_user_message(self) -> bool:
        """Check if this is a user message.

        Returns:
            True if role is "user"
        """
        return self.role == "user"

    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message.

        Returns:
            True if role is "assistant"
        """
        return self.role == "assistant"

    def word_count(self) -> int:
        """Get word count of message content.

        Returns:
            Number of words in content
        """
        return len(self.content.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        result: dict[str, Any] = {
            "session_id": str(self.session_id),
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "content_hash": self.content_hash,
            "event_metadata": self.event_metadata,
            "created_at": self.created_at.isoformat(),
        }

        if self.event_id is not None:
            result["event_id"] = self.event_id

        return result

    def __str__(self) -> str:
        """String representation for logging."""
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        event_id_str = f"id={self.event_id}, " if self.event_id else ""
        return f'ChatMessage({event_id_str}role={self.role}, content="{preview}")'

    def __eq__(self, other: object) -> bool:
        """Messages are equal if they have the same event_id or same session+content_hash."""
        if not isinstance(other, ChatMessage):
            return False

        # If both have event_id, compare by that
        if self.event_id is not None and other.event_id is not None:
            return self.event_id == other.event_id

        # Otherwise, compare by session + content_hash (deduplication)
        return (
            self.session_id == other.session_id and self.content_hash == other.content_hash
        )

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        if self.event_id is not None:
            return hash(self.event_id)
        return hash((self.session_id, self.content_hash))
