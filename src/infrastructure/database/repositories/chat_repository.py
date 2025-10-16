"""Chat event repository implementation.

Implements IChatEventRepository using SQLAlchemy and PostgreSQL.
"""
from uuid import UUID

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import ChatMessage
from src.domain.exceptions import RepositoryError
from src.domain.ports import IChatEventRepository
from src.infrastructure.database.models import ChatEvent as ChatEventModel

logger = structlog.get_logger(__name__)


class ChatEventRepository(IChatEventRepository):
    """SQLAlchemy implementation of IChatEventRepository.

    Maps between ChatMessage domain entities and ChatEvent ORM models.
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def create(self, message: ChatMessage) -> ChatMessage:
        """Store a chat message/event.

        Args:
            message: Message to store

        Returns:
            Stored message (with event_id populated)

        Raises:
            RepositoryError: If message with same session+content_hash exists
        """
        try:
            # Check for duplicate (same session + content hash)
            existing_stmt = select(ChatEventModel).where(
                ChatEventModel.session_id == message.session_id,
                ChatEventModel.content_hash == message.content_hash,
            )
            result = await self.session.execute(existing_stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Return existing message instead of creating duplicate
                logger.info(
                    "duplicate_message_detected",
                    session_id=str(message.session_id),
                    content_hash=message.content_hash,
                    existing_event_id=existing.event_id,
                )
                return self._to_domain_message(existing)

            # Create new event
            model = ChatEventModel(
                session_id=message.session_id,
                user_id=message.user_id,
                role=message.role,
                content=message.content,
                content_hash=message.content_hash,
                event_metadata=message.event_metadata,
                created_at=message.created_at,
            )

            self.session.add(model)
            await self.session.flush()

            # Update domain object with generated ID
            message.event_id = model.event_id

            logger.info(
                "chat_event_created",
                event_id=message.event_id,
                session_id=str(message.session_id),
                role=message.role,
            )

            return message

        except Exception as e:
            logger.error(
                "create_chat_event_error",
                session_id=str(message.session_id),
                error=str(e),
            )
            msg = f"Error creating chat event: {e}"
            raise RepositoryError(msg) from e

    async def get_by_event_id(self, event_id: int) -> ChatMessage | None:
        """Get a chat message by event ID.

        Args:
            event_id: Event ID to retrieve

        Returns:
            ChatMessage if found, None otherwise
        """
        try:
            stmt = select(ChatEventModel).where(ChatEventModel.event_id == event_id)
            result = await self.session.execute(stmt)
            model = result.scalar_one_or_none()

            return self._to_domain_message(model) if model else None

        except Exception as e:
            logger.error("get_by_event_id_error", event_id=event_id, error=str(e))
            msg = f"Error getting chat event: {e}"
            raise RepositoryError(msg) from e

    async def get_recent_for_user(
        self, user_id: str, limit: int = 10
    ) -> list[ChatMessage]:
        """Get recent messages for a user (for context).

        Args:
            user_id: User ID
            limit: Maximum number of messages

        Returns:
            List of recent messages, most recent last
        """
        try:
            stmt = (
                select(ChatEventModel)
                .where(ChatEventModel.user_id == user_id)
                .order_by(desc(ChatEventModel.created_at))
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            models = list(result.scalars().all())

            # Reverse to get chronological order (oldest first)
            models.reverse()

            return [self._to_domain_message(model) for model in models]

        except Exception as e:
            logger.error("get_recent_for_user_error", user_id=user_id, error=str(e))
            msg = f"Error getting recent messages: {e}"
            raise RepositoryError(msg) from e

    async def get_recent_for_session(
        self, session_id: UUID, limit: int = 10
    ) -> list[ChatMessage]:
        """Get recent messages in a session (for context).

        Args:
            session_id: Session ID
            limit: Maximum number of messages

        Returns:
            List of recent messages in chronological order
        """
        try:
            stmt = (
                select(ChatEventModel)
                .where(ChatEventModel.session_id == session_id)
                .order_by(ChatEventModel.created_at)  # Chronological order
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            models = result.scalars().all()

            return [self._to_domain_message(model) for model in models]

        except Exception as e:
            logger.error(
                "get_recent_for_session_error",
                session_id=str(session_id),
                error=str(e),
            )
            msg = f"Error getting session messages: {e}"
            raise RepositoryError(msg) from e

    def _to_domain_message(self, model: ChatEventModel) -> ChatMessage:
        """Convert ORM model to domain entity.

        Args:
            model: SQLAlchemy model

        Returns:
            Domain ChatMessage
        """
        return ChatMessage(
            event_id=model.event_id,
            session_id=model.session_id,
            user_id=model.user_id,
            role=model.role,
            content=model.content,
            content_hash=model.content_hash,
            event_metadata=model.event_metadata or {},
            created_at=model.created_at,
        )
