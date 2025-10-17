"""LLM service port (interface).

Defines the contract for LLM operations (primarily coreference resolution).
"""
from dataclasses import dataclass
from typing import Any, Protocol

from src.domain.value_objects import ConversationContext, EntityMention, ResolutionResult


@dataclass(frozen=True)
class ToolCall:
    """Represents a tool call from LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMToolResponse:
    """LLM response with optional tool calls."""

    content: str | None
    tool_calls: list[ToolCall] | None


class ILLMService(Protocol):
    """LLM service interface for coreference resolution.

    This is a port (interface) used by EntityResolutionService.
    Infrastructure layer implements this using OpenAI API.

    Used for Stage 4 of entity resolution: coreference (5% of cases).
    """

    async def resolve_coreference(
        self, mention: EntityMention, context: ConversationContext
    ) -> ResolutionResult:
        """Resolve a pronoun/coreference to a canonical entity.

        Used when mention is a pronoun ("they", "it", "the customer") that
        requires understanding conversation context to resolve.

        Args:
            mention: Entity mention (pronoun or demonstrative)
            context: Conversation context with recent messages and entities

        Returns:
            ResolutionResult with resolved entity (or FAILED if unresolvable)

        Example:
            User: "I need a quote for Acme Corporation"
            Assistant: "Sure, what products are they interested in?"
            User: "They want 100 units of Widget X"
                  ^ "They" should resolve to "Acme Corporation"
        """
        ...

    async def extract_entity_mentions(self, text: str) -> list[EntityMention]:
        """Extract entity mentions from text using LLM.

        This is optional for Phase 1A - we can use simple pattern matching initially.
        For Phase 1B+, LLM extraction provides better accuracy.

        Args:
            text: Text to extract mentions from

        Returns:
            List of entity mentions found in text
        """
        ...

    async def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "claude-haiku-4-5",
    ) -> LLMToolResponse:
        """Chat with tool calling support.

        Vision Alignment:
        - Emergent intelligence (LLM decides what to fetch)
        - No hardcoded query planning
        - Adaptive to context

        Args:
            system_prompt: System instructions
            messages: Conversation messages
            tools: Available tools in Claude format
            model: Model to use (default: Claude 4.5 Haiku)

        Returns:
            Response with optional tool calls
        """
        ...
