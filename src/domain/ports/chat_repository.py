"""Chat event repository port (interface).

Defines the contract for chat message persistence.
"""
from typing import Protocol
from uuid import UUID

from src.domain.entities import ChatMessage


class IChatEventRepository(Protocol):
    """Repository interface for chat events (messages).

    This is a port (interface) in hexagonal architecture.
    Infrastructure layer implements this using SQLAlchemy.
    """

    async def create(self, message: ChatMessage) -> ChatMessage:
        """Store a chat message/event.

        Args:
            message: Message to store

        Returns:
            Stored message (with event_id populated)

        Raises:
            ValueError: If message with same session_id + content_hash already exists
        """
        ...

    async def get_by_event_id(self, event_id: int) -> ChatMessage | None:
        """Get a chat message by event ID.

        Args:
            event_id: Event ID to retrieve

        Returns:
            ChatMessage if found, None otherwise
        """
        ...

    async def get_recent_for_user(
        self, user_id: str, limit: int = 10
    ) -> list[ChatMessage]:
        """Get recent messages for a user (for context).

        Args:
            user_id: User ID
            limit: Maximum number of messages to return

        Returns:
            List of recent messages, most recent last
        """
        ...

    async def get_recent_for_session(
        self, session_id: UUID, limit: int = 10
    ) -> list[ChatMessage]:
        """Get recent messages in a session (for context).

        Args:
            session_id: Session ID
            limit: Maximum number of messages to return

        Returns:
            List of recent messages in chronological order
        """
        ...
