"""Tool usage repository implementation.

Implements IToolUsageTracker using SQLAlchemy and PostgreSQL.
Tracks LLM tool calling patterns for feedback loop and learning.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.exceptions import RepositoryError
from src.domain.ports import IToolUsageTracker
from src.infrastructure.database.models import ToolUsageLog

logger = structlog.get_logger(__name__)


class PostgresToolUsageRepository(IToolUsageTracker):
    """PostgreSQL implementation of IToolUsageTracker.

    Vision Alignment:
    - Learning from usage (track what works)
    - Feedback loop infrastructure
    - Phase 2: Analyze patterns to optimize tool selection
    """

    def __init__(self, session: AsyncSession):
        """Initialize repository.

        Args:
            session: SQLAlchemy async session
        """
        self.session = session

    async def log_tool_usage(
        self,
        conversation_id: str,
        query: str,
        tools_called: list[dict[str, Any]],
        facts_count: int,
    ) -> None:
        """Log tool usage for a query.

        Args:
            conversation_id: Conversation identifier
            query: User query text
            tools_called: List of {tool, arguments, iteration}
            facts_count: Number of facts retrieved
        """
        try:
            stmt = insert(ToolUsageLog).values(
                conversation_id=conversation_id,
                query=query,
                tools_called=tools_called,
                facts_count=facts_count,
            )

            await self.session.execute(stmt)
            await self.session.flush()

            logger.info(
                "tool_usage_logged",
                conversation_id=conversation_id,
                tools_count=len(tools_called),
                facts_count=facts_count,
            )

        except Exception as e:
            logger.error(
                "log_tool_usage_error",
                conversation_id=conversation_id,
                error=str(e),
            )
            msg = f"Error logging tool usage: {e}"
            raise RepositoryError(msg) from e

    async def log_outcome(
        self,
        conversation_id: str,
        user_satisfied: bool,
        feedback_text: str | None = None,
    ) -> None:
        """Log outcome of interaction (for learning).

        Args:
            conversation_id: Conversation identifier
            user_satisfied: Did user get what they needed?
            feedback_text: Optional explicit feedback
        """
        try:
            # Update most recent entry for this conversation
            stmt = (
                update(ToolUsageLog)
                .where(ToolUsageLog.conversation_id == conversation_id)
                .where(ToolUsageLog.outcome_satisfaction.is_(None))
                .values(
                    outcome_satisfaction=1 if user_satisfied else 0,
                    outcome_feedback=feedback_text,
                )
            )

            result = await self.session.execute(stmt)
            await self.session.flush()

            logger.info(
                "outcome_logged",
                conversation_id=conversation_id,
                satisfied=user_satisfied,
            )

        except Exception as e:
            logger.error(
                "log_outcome_error",
                conversation_id=conversation_id,
                error=str(e),
            )
            msg = f"Error logging outcome: {e}"
            raise RepositoryError(msg) from e

    async def get_usage_logs(
        self,
        user_id: str,
        since: datetime,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Retrieve tool usage logs for pattern mining.

        Args:
            user_id: User identifier (not used in Phase 1, but kept for future)
            since: Get logs since this timestamp
            limit: Maximum number of logs to return

        Returns:
            List of usage log dictionaries with fields:
            - conversation_id: str
            - query: str
            - tools_called: list[dict]
            - facts_count: int
            - timestamp: datetime
        """
        try:
            # Query logs since timestamp, ordered by most recent
            stmt = (
                select(ToolUsageLog)
                .where(ToolUsageLog.timestamp >= since)
                .order_by(ToolUsageLog.timestamp.desc())
                .limit(limit)
            )

            result = await self.session.execute(stmt)
            rows = result.scalars().all()

            # Convert to dict format for pattern detection
            logs = []
            for row in rows:
                logs.append({
                    "conversation_id": row.conversation_id,
                    "query": row.query,
                    "tools_called": row.tools_called,
                    "facts_count": row.facts_count,
                    "timestamp": row.timestamp,
                })

            logger.debug(
                "usage_logs_retrieved",
                user_id=user_id,
                since=since,
                count=len(logs),
            )

            return logs

        except Exception as e:
            logger.error(
                "get_usage_logs_error",
                user_id=user_id,
                since=since,
                error=str(e),
            )
            msg = f"Error retrieving usage logs: {e}"
            raise RepositoryError(msg) from e
