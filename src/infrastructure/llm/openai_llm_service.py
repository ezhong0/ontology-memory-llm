"""OpenAI LLM service implementation.

Implements ILLMService using OpenAI's API for coreference resolution
and semantic triple extraction.
"""

import json
from typing import Any

import structlog
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
            msg = f"LLM coreference resolution failed: {e}"
            raise LLMServiceError(msg) from e

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
        msg = (
            "LLM-based mention extraction not implemented in Phase 1A. "
            "Use simple pattern-based extraction for now."
        )
        raise NotImplementedError(
            msg
        )

    async def extract_semantic_triples(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract semantic triples (SPO) from message using LLM.

        Phase 1B: Extract structured knowledge (subject-predicate-object triples)
        from natural language messages using GPT-4-turbo.

        Args:
            message: Chat message content
            resolved_entities: Resolved entities from Phase 1A
                Each dict should have: entity_id, canonical_name, entity_type

        Returns:
            List of triple dictionaries with structure:
            {
                "subject_entity_id": str,
                "predicate": str,
                "predicate_type": str (attribute|preference|relationship|action),
                "object_value": dict (structured value),
                "confidence": float,
                "metadata": dict (optional)
            }

        Raises:
            LLMServiceError: If extraction fails
        """
        if not message or not message.strip():
            logger.debug("empty_message_for_extraction")
            return []

        if not resolved_entities:
            logger.debug("no_entities_for_extraction")
            return []

        try:
            # Build extraction prompt
            prompt = self._build_extraction_prompt(message, resolved_entities)

            logger.debug(
                "calling_openai_for_triple_extraction",
                message_length=len(message),
                entity_count=len(resolved_entities),
                model=self.MODEL,
            )

            # Call OpenAI with JSON mode for structured output
            response = await self.client.chat.completions.create(
                model=self.MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured knowledge from conversations. "
                        "Extract semantic triples (subject-predicate-object) following the exact JSON schema provided.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,  # Allow for multiple triples
                temperature=0.1,  # Low temperature for consistent extraction
                response_format={"type": "json_object"},
            )

            # Track usage
            self._track_usage(response)

            # Parse response
            triples = self._parse_extraction_response(response, message)

            logger.info(
                "triple_extraction_success",
                message_length=len(message),
                entity_count=len(resolved_entities),
                triple_count=len(triples),
                tokens=response.usage.total_tokens if response.usage else 0,
            )

            return triples

        except Exception as e:
            logger.error(
                "triple_extraction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Semantic triple extraction failed: {e}"
            raise LLMServiceError(msg) from e

    def _build_extraction_prompt(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> str:
        """Build prompt for semantic triple extraction.

        Args:
            message: Message content
            resolved_entities: Resolved entities

        Returns:
            Formatted prompt string
        """
        # Format entities as JSON
        entities_json = json.dumps(resolved_entities, indent=2)

        return f"""Extract semantic triples (subject-predicate-object) from the message below.

Resolved Entities:
{entities_json}

Predicate Types:
- attribute: Factual properties (payment_terms, industry, size, location)
- preference: User/entity preferences (prefers_delivery_day, dislikes_product)
- relationship: Inter-entity relationships (supplies_to, works_with, is_customer_of)
- action: Completed actions (ordered, cancelled, requested, confirmed)

Message: "{message}"

Task: Extract all semantic triples where the subject is one of the resolved entities.

Instructions:
1. Analyze the message for factual information about the entities
2. Extract each fact as a subject-predicate-object triple
3. Use entity_id from resolved entities as subject
4. Normalize predicates to snake_case (e.g., "prefers_delivery_day")
5. Structure object_value as a dictionary with "type" and "value" keys
6. Assign confidence based on statement clarity (0.0-1.0)
   - Explicit statement: 0.9 ("Acme prefers Friday")
   - Implicit statement: 0.7 ("They usually want Friday")
   - Inferred: 0.5 ("They mentioned Friday twice")

Output Format (JSON):
{{
  "triples": [
    {{
      "subject_entity_id": "customer_acme_123",
      "predicate": "prefers_delivery_day",
      "predicate_type": "preference",
      "object_value": {{"type": "day_of_week", "value": "Friday"}},
      "confidence": 0.9,
      "metadata": {{"source": "explicit"}}
    }}
  ]
}}

Respond with ONLY the JSON object. If no triples can be extracted, return {{"triples": []}}.
"""


    def _parse_extraction_response(
        self,
        response: ChatCompletion,
        message: str,
    ) -> list[dict[str, Any]]:
        """Parse OpenAI response for semantic triple extraction.

        Args:
            response: OpenAI API response
            message: Original message

        Returns:
            List of triple dictionaries

        Raises:
            LLMServiceError: If response cannot be parsed
        """
        if not response.choices:
            logger.warning("no_choices_in_extraction_response")
            return []

        response_text = response.choices[0].message.content
        if not response_text:
            logger.warning("empty_extraction_response")
            return []

        try:
            # Parse JSON response
            parsed = json.loads(response_text)

            if not isinstance(parsed, dict):
                msg = "Response is not a JSON object"
                raise ValueError(msg)

            triples = parsed.get("triples", [])

            if not isinstance(triples, list):
                msg = "triples field is not a list"
                raise ValueError(msg)

            logger.debug(
                "parsed_extraction_response",
                triple_count=len(triples),
            )

            return triples

        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_error_in_extraction",
                response_text=response_text[:200],
                error=str(e),
            )
            return []
        except ValueError as e:
            logger.error(
                "invalid_extraction_response_format",
                error=str(e),
            )
            return []

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

        return f"""Resolve the pronoun reference in this conversation.

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
