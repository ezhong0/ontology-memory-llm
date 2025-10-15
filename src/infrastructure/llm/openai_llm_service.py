"""OpenAI LLM service implementation.

Implements ILLMService using OpenAI's API for coreference resolution.
"""
import structlog
from typing import Optional

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from src.domain.exceptions import LLMServiceError
from src.domain.ports import ILLMService
from src.domain.value_objects import (
    ConversationContext,
    EntityMention,
    ResolutionMethod,
    ResolutionResult,
)

logger = structlog.get_logger(__name__)


class OpenAILLMService(ILLMService):
    """OpenAI implementation of ILLMService.

    Uses GPT-4 for coreference resolution (Stage 4 of entity resolution).
    Only called for ~5% of cases (pronouns and demonstratives).

    Cost: ~$0.003 per coreference resolution (GPT-4-turbo with short prompts)
    """

    # Model configuration
    MODEL = "gpt-4-turbo-preview"
    MAX_TOKENS = 100  # Short responses (just entity_id)
    TEMPERATURE = 0.0  # Deterministic output

    def __init__(self, api_key: str):
        """Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self._total_tokens_used = 0
        self._total_cost = 0.0

    async def resolve_coreference(
        self, mention: EntityMention, context: ConversationContext
    ) -> ResolutionResult:
        """Resolve pronoun/coreference to a canonical entity using LLM.

        Uses GPT-4 with conversation context to determine which entity
        a pronoun ("they", "it", "the customer") refers to.

        Args:
            mention: Entity mention (pronoun or demonstrative)
            context: Conversation context with recent entities

        Returns:
            ResolutionResult with resolved entity (or FAILED if unresolvable)
        """
        if not context.has_recent_entities:
            logger.debug(
                "no_recent_entities_for_llm",
                mention=mention.text,
            )
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason="No recent entities in context",
            )

        try:
            # Build prompt
            prompt = self._build_coreference_prompt(mention, context)

            logger.debug(
                "calling_openai_for_coreference",
                mention=mention.text,
                model=self.MODEL,
            )

            # Call OpenAI
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at resolving pronoun references in conversations. "
                        "Your task is to identify which entity a pronoun refers to based on conversation context.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
            )

            # Track usage
            self._track_usage(response)

            # Parse response
            result = self._parse_coreference_response(response, mention, context)

            if result.is_successful:
                logger.info(
                    "llm_coreference_success",
                    mention=mention.text,
                    resolved_to=result.entity_id,
                    confidence=result.confidence,
                    tokens=response.usage.total_tokens if response.usage else 0,
                )
            else:
                logger.debug(
                    "llm_coreference_failed",
                    mention=mention.text,
                    reason=result.metadata.get("reason"),
                )

            return result

        except Exception as e:
            logger.error(
                "llm_coreference_error",
                mention=mention.text,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise LLMServiceError(f"LLM coreference resolution failed: {e}") from e

    async def extract_entity_mentions(self, text: str) -> list[EntityMention]:
        """Extract entity mentions from text using LLM.

        This is optional for Phase 1A - we use simple pattern matching initially.
        Can be implemented in Phase 1B for better accuracy.

        Args:
            text: Text to extract mentions from

        Returns:
            List of entity mentions found in text

        Raises:
            NotImplementedError: Not implemented in Phase 1A
        """
        raise NotImplementedError(
            "LLM-based mention extraction not implemented in Phase 1A. "
            "Use simple pattern-based extraction for now."
        )

    def _build_coreference_prompt(
        self, mention: EntityMention, context: ConversationContext
    ) -> str:
        """Build prompt for coreference resolution.

        Args:
            mention: Mention to resolve
            context: Conversation context

        Returns:
            Formatted prompt string
        """
        # Format recent messages
        recent_msgs = ""
        if context.recent_messages:
            for i, msg in enumerate(context.recent_messages[-3:], 1):
                recent_msgs += f"{i}. {msg}\n"

        # Format recent entities (candidates)
        candidates = ""
        for entity_id, name in context.recent_entities[-5:]:
            candidates += f"- {name} (id: {entity_id})\n"

        prompt = f"""Resolve the pronoun reference in this conversation.

Recent conversation:
{recent_msgs}

Recently mentioned entities:
{candidates}

Current message: "{context.current_message}"
Mention to resolve: "{mention.text}"

Task: Determine which entity "{mention.text}" refers to.

Instructions:
1. Analyze the conversation context
2. Identify the most likely entity the pronoun refers to
3. Respond with ONLY the entity_id (e.g., "customer_123")
4. If uncertain or no clear referent, respond with "UNKNOWN"

Response (entity_id or UNKNOWN):"""

        return prompt

    def _parse_coreference_response(
        self,
        response: ChatCompletion,
        mention: EntityMention,
        context: ConversationContext,
    ) -> ResolutionResult:
        """Parse OpenAI response for coreference resolution.

        Args:
            response: OpenAI API response
            mention: Original mention
            context: Conversation context

        Returns:
            ResolutionResult with resolved entity or FAILED
        """
        if not response.choices:
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason="No response from LLM",
            )

        response_text = response.choices[0].message.content
        if not response_text:
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason="Empty response from LLM",
            )

        response_text = response_text.strip()

        # Check if LLM couldn't resolve
        if response_text.upper() == "UNKNOWN":
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason="LLM could not determine referent",
            )

        # Validate entity_id is in recent entities
        entity_id = response_text
        matching_entity = None
        for ent_id, ent_name in context.recent_entities:
            if ent_id == entity_id:
                matching_entity = (ent_id, ent_name)
                break

        if not matching_entity:
            logger.warning(
                "llm_returned_invalid_entity_id",
                mention=mention.text,
                returned_id=entity_id,
                valid_ids=[ent_id for ent_id, _ in context.recent_entities],
            )
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason=f"LLM returned invalid entity_id: {entity_id}",
            )

        # Success!
        return ResolutionResult(
            entity_id=matching_entity[0],
            confidence=0.75,  # LLM coreference has medium-high confidence
            method=ResolutionMethod.COREFERENCE,
            mention_text=mention.text,
            canonical_name=matching_entity[1],
            metadata={
                "llm_response": response_text,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
            },
        )

    def _track_usage(self, response: ChatCompletion) -> None:
        """Track token usage and costs.

        Args:
            response: OpenAI API response
        """
        if not response.usage:
            return

        tokens = response.usage.total_tokens
        self._total_tokens_used += tokens

        # GPT-4-turbo pricing (as of 2024): ~$0.01 per 1K prompt tokens, ~$0.03 per 1K completion
        # Rough estimate: $0.015 per 1K tokens average
        cost = (tokens / 1000) * 0.015
        self._total_cost += cost

        logger.debug(
            "llm_usage_tracked",
            tokens=tokens,
            cost=cost,
            total_tokens=self._total_tokens_used,
            total_cost=self._total_cost,
        )

    @property
    def total_tokens_used(self) -> int:
        """Get total tokens used by this service instance.

        Returns:
            Total tokens used
        """
        return self._total_tokens_used

    @property
    def total_cost(self) -> float:
        """Get total estimated cost for this service instance.

        Returns:
            Total cost in USD
        """
        return self._total_cost
