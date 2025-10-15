"""LLM service port (interface).

Defines the contract for LLM operations (primarily coreference resolution).
"""
from typing import Protocol

from src.domain.value_objects import ConversationContext, EntityMention, ResolutionResult


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
