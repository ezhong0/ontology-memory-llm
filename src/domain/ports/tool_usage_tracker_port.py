"""Port for tracking tool usage patterns.

Vision Alignment:
- Learning from usage (track what works)
- Feedback loop infrastructure
- Phase 2: Analyze patterns, optimize
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class IToolUsageTracker(ABC):
    """Port for tracking tool usage patterns.

    Philosophy: You can't learn if you don't track.
    This port enables the feedback loop that drives emergent intelligence.
    """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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
