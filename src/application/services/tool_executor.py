"""Execute LLM tool calls by invoking domain database port methods.

Vision Alignment:
- Thin wrapper (no business logic)
- Observable (structured logging)
- Fault-tolerant (graceful degradation)
"""

from typing import Any

import structlog

from src.domain.ports.domain_database_port import DomainDatabasePort
from src.domain.value_objects.domain_fact import DomainFact

logger = structlog.get_logger(__name__)


class ToolExecutor:
    """Execute tool calls from LLM.

    Philosophy: This is a translation layer, not business logic.
    It maps tool names → port method calls.

    Vision Alignment:
    - Graceful degradation (errors don't crash)
    - Observable (structured logging)
    - Simple (no complex logic)
    """

    def __init__(self, domain_db: DomainDatabasePort):
        """Initialize with domain database port.

        Args:
            domain_db: Domain database port for executing queries
        """
        self.domain_db = domain_db

    async def execute(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> list[DomainFact] | dict[str, Any]:
        """Execute a tool call.

        Args:
            tool_name: Name of tool (matches port method name)
            arguments: Tool arguments (matches method parameters)

        Returns:
            Tool result (typically list of DomainFacts, or error dict)
        """
        logger.info(
            "executing_tool",
            tool_name=tool_name,
            arguments=arguments,
        )

        # Get method from port
        if not hasattr(self.domain_db, tool_name):
            logger.error("unknown_tool", tool_name=tool_name)
            return {"error": f"Unknown tool: {tool_name}"}

        method = getattr(self.domain_db, tool_name)

        try:
            # Execute method with arguments
            result: Any = await method(**arguments)

            logger.info(
                "tool_executed_successfully",
                tool_name=tool_name,
                result_count=len(result) if isinstance(result, list) else 1,
            )

            # Type narrowing: result is either list[DomainFact] or raises exception
            return result  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(
                "tool_execution_failed",
                tool_name=tool_name,
                error=str(e),
                exc_info=True,
            )

            # Graceful degradation: return error dict instead of raising
            # This allows LLM to continue with partial information
            return {"error": str(e), "tool": tool_name}
