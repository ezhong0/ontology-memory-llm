"""Anthropic LLM service implementation.

Implements ILLMService using Anthropic's Claude API for coreference resolution
and semantic triple extraction.
"""

import json
from typing import Any

import structlog
from anthropic import AsyncAnthropic

from src.config import heuristics
from src.domain.exceptions import LLMServiceError
from src.domain.ports import ILLMService
from src.domain.ports.llm_service import LLMToolResponse, ToolCall
from src.domain.value_objects import (
    ConversationContext,
    EntityMention,
    ResolutionMethod,
    ResolutionResult,
)

logger = structlog.get_logger(__name__)


class AnthropicLLMService(ILLMService):
    """Anthropic implementation of ILLMService using Claude Haiku 4.5.

    Uses Claude Haiku 4.5 for coreference resolution and semantic extraction.
    Optimized for cost-effectiveness while maintaining high accuracy.

    Pricing: $1.00 per 1M input tokens, $5.00 per 1M output tokens
    Context: 200K tokens
    """

    # Model configuration
    MODEL = "claude-haiku-4-5"
    MAX_TOKENS = 1000  # Claude's max_tokens parameter
    TEMPERATURE = 0.0  # Deterministic output for coreference
    TEMPERATURE_EXTRACTION = 0.1  # Slightly higher for extraction

    def __init__(self, api_key: str):
        """Initialize Anthropic LLM service.

        Args:
            api_key: Anthropic API key
        """
        self.client = AsyncAnthropic(api_key=api_key)
        self._total_tokens_used = 0
        self._total_cost = 0.0

    async def resolve_coreference(
        self, mention: EntityMention, context: ConversationContext
    ) -> ResolutionResult:
        """Resolve pronoun/coreference to a canonical entity using Claude.

        Uses Claude Haiku 4.5 with conversation context to determine which entity
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
                "calling_anthropic_for_coreference",
                mention=mention.text,
                model=self.MODEL,
            )

            # Call Anthropic
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=100,  # Short responses (just entity_id)
                temperature=self.TEMPERATURE,
                system="You are an expert at resolving pronoun references in conversations. "
                "Your task is to identify which entity a pronoun refers to based on conversation context.",
                messages=[{"role": "user", "content": prompt}],
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
                    tokens=response.usage.input_tokens + response.usage.output_tokens,
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

        Uses Claude Haiku 4.5 for intelligent entity extraction that handles:
        - Capitalized and lowercase entities
        - Typos and variations
        - Context-aware extraction
        - Pronouns and identifiers

        Args:
            text: Text to extract mentions from

        Returns:
            List of entity mentions found in text
        """
        if not text or not text.strip():
            logger.debug("empty_text_for_mention_extraction")
            return []

        try:
            # Build extraction prompt
            prompt = self._build_mention_extraction_prompt(text)

            logger.debug(
                "calling_anthropic_for_mention_extraction",
                text_length=len(text),
                model=self.MODEL,
            )

            # Call Anthropic
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE_EXTRACTION,
                system="You are an expert at extracting entity mentions from text. "
                "Extract all named entities, identifiers, and pronouns with precision. "
                "Always respond with valid JSON only, no other text.",
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            self._track_usage(response)

            # Parse response
            mentions = self._parse_mention_extraction_response(response, text)

            logger.info(
                "mention_extraction_success",
                text_length=len(text),
                mention_count=len(mentions),
                tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return mentions

        except Exception as e:
            logger.error(
                "mention_extraction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Fallback to empty list rather than failing
            # This allows graceful degradation
            logger.warning("falling_back_to_empty_mentions_due_to_error")
            return []

    async def extract_semantic_facts(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract semantic facts as entity-tagged natural language using Claude.

        Replaces triple extraction with natural language approach:
        - Instead of (subject, predicate, object), stores complete sentences
        - Tags facts with all relevant entity IDs
        - Calculates importance from confidence

        Args:
            message: Chat message content
            resolved_entities: Resolved entities from Phase 1A
                Each dict should have: entity_id, canonical_name, entity_type

        Returns:
            List of fact dictionaries with structure:
            {
                "content": str,  # Natural language fact
                "entities": list[str],  # Entity IDs mentioned
                "confidence": float,  # Extraction confidence [0.0, 1.0]
            }

        Example:
            Input: "Gai Media prefers Friday deliveries"
            Output: [{
                "content": "Gai Media prefers Friday deliveries",
                "entities": ["customer:gai_media_456"],
                "confidence": 0.9
            }]

        Raises:
            LLMServiceError: If extraction fails
        """
        if not message or not message.strip():
            logger.debug("empty_message_for_fact_extraction")
            return []

        if not resolved_entities:
            logger.debug("no_entities_for_fact_extraction")
            return []

        try:
            # Build extraction prompt
            prompt = self._build_fact_extraction_prompt(message, resolved_entities)

            logger.debug(
                "calling_anthropic_for_fact_extraction",
                message_length=len(message),
                entity_count=len(resolved_entities),
                model=self.MODEL,
            )

            # Call Anthropic
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE_EXTRACTION,
                system="You are an expert at extracting factual knowledge from conversations. "
                "Extract facts as clear, natural language sentences tagged with relevant entities. "
                "Always respond with valid JSON only, no other text.",
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            self._track_usage(response)

            # Parse response
            facts = self._parse_fact_extraction_response(response, message)

            logger.info(
                "fact_extraction_success",
                message_length=len(message),
                entity_count=len(resolved_entities),
                fact_count=len(facts),
                tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return facts

        except Exception as e:
            logger.error(
                "fact_extraction_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Semantic fact extraction failed: {e}"
            raise LLMServiceError(msg) from e

    async def extract_semantic_triples(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """DEPRECATED: Extract semantic triples (SPO) from message using Claude.

        This method is deprecated. Use extract_semantic_facts() instead for
        entity-tagged natural language approach.

        Phase 1B: Extract structured knowledge (subject-predicate-object triples)
        from natural language messages using Claude Haiku 4.5.

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
                "calling_anthropic_for_triple_extraction",
                message_length=len(message),
                entity_count=len(resolved_entities),
                model=self.MODEL,
            )

            # Call Anthropic
            # Claude excels at following structured instructions without needing special JSON mode
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE_EXTRACTION,
                system="You are an expert at extracting structured knowledge from conversations. "
                "Extract semantic triples (subject-predicate-object) following the exact JSON schema provided. "
                "Always respond with valid JSON only, no other text.",
                messages=[{"role": "user", "content": prompt}],
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
                tokens=response.usage.input_tokens + response.usage.output_tokens,
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

    def _build_fact_extraction_prompt(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> str:
        """Build prompt for semantic fact extraction (entity-tagged natural language).

        Args:
            message: Message content
            resolved_entities: Resolved entities

        Returns:
            Formatted prompt string
        """
        # Format entities as JSON
        entities_json = json.dumps(resolved_entities, indent=2)

        return f"""Extract semantic facts from the message as PURE NATURAL LANGUAGE sentences.

Resolved Entities:
{entities_json}

Message: "{message}"

Task: Extract all factual statements about the entities as complete, natural language sentences.

CRITICAL FORMATTING RULES:
- Extract facts as PURE NATURAL LANGUAGE ONLY
- DO NOT include JSON objects, dictionaries, or structured data in the sentence content
- DO NOT use formats like {{'key': 'value'}} or key:value in the content
- Write facts as if you were speaking to a human in plain English

Instructions:
1. SKIP QUESTIONS: Do NOT extract facts from questions (messages ending in '?' or asking about information). Questions are for retrieval, not extraction.
2. Identify factual statements about entities (preferences, attributes, relationships, actions)
3. Extract each fact as a complete, clear sentence IN PURE NATURAL LANGUAGE
4. Tag each fact with ALL relevant entity IDs mentioned in the fact
5. Assign confidence based on statement clarity (0.0-1.0):
   - Explicit statement: 0.9
   - Implicit statement: 0.7
   - Inferred: 0.5

EXAMPLES OF CORRECT OUTPUT:
✅ GOOD: "Kai Media prefers Friday deliveries"
✅ GOOD: "Kai Media's payment terms are NET15"
✅ GOOD: "Acme Corporation is located in San Francisco"
✅ GOOD: "Invoice INV-1009 is due on September 30, 2025"

EXAMPLES OF INCORRECT OUTPUT (DO NOT DO THIS):
❌ BAD: "Kai Media prefers delivery day {{'day': 'Friday'}}"
❌ BAD: "Kai Media has payment_terms: NET15"
❌ BAD: "Acme Corporation location={{'city': 'San Francisco'}}"
❌ BAD: "Invoice INV-1009 due_date: 2025-09-30"

Output Format (JSON):
{{
  "facts": [
    {{
      "content": "Kai Media prefers Friday deliveries",
      "entities": ["customer_kai_media_456"],
      "confidence": 0.9
    }}
  ]
}}

Respond with ONLY the JSON object. If no facts can be extracted, return {{"facts": []}}."""

    def _parse_fact_extraction_response(
        self,
        response: Any,
        message: str,
    ) -> list[dict[str, Any]]:
        """Parse Anthropic response for semantic fact extraction.

        Args:
            response: Anthropic API response
            message: Original message

        Returns:
            List of fact dictionaries

        Raises:
            LLMServiceError: If response cannot be parsed
        """
        if not response.content:
            logger.warning("empty_fact_extraction_response")
            return []

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        if not response_text:
            logger.warning("no_text_in_fact_extraction_response")
            return []

        try:
            # Strip markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON response
            parsed = json.loads(response_text)

            if not isinstance(parsed, dict):
                msg = "Response is not a JSON object"
                raise ValueError(msg)

            facts = parsed.get("facts", [])

            if not isinstance(facts, list):
                msg = "facts field is not a list"
                raise ValueError(msg)

            logger.debug(
                "parsed_fact_extraction_response",
                fact_count=len(facts),
            )

            return facts

        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_error_in_fact_extraction",
                response_text=response_text[:200],
                error=str(e),
            )
            return []
        except ValueError as e:
            logger.error(
                "invalid_fact_extraction_response_format",
                error=str(e),
            )
            return []

    def _build_extraction_prompt(
        self,
        message: str,
        resolved_entities: list[dict[str, Any]],
    ) -> str:
        """DEPRECATED: Build prompt for semantic triple extraction.

        Use _build_fact_extraction_prompt() instead for entity-tagged natural language.

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
1. Analyze the message for factual statements about the entities
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

Respond with ONLY the JSON object. If no triples can be extracted, return {{"triples": []}}."""

    def _parse_extraction_response(
        self,
        response: Any,
        message: str,
    ) -> list[dict[str, Any]]:
        """Parse Anthropic response for semantic triple extraction.

        Args:
            response: Anthropic API response
            message: Original message

        Returns:
            List of triple dictionaries

        Raises:
            LLMServiceError: If response cannot be parsed
        """
        if not response.content:
            logger.warning("empty_extraction_response")
            return []

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        if not response_text:
            logger.warning("no_text_in_extraction_response")
            return []

        try:
            # Strip markdown code blocks if present (```json ... ```)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]  # Remove ```json
            if response_text.startswith("```"):
                response_text = response_text[3:]  # Remove ```
            if response_text.endswith("```"):
                response_text = response_text[:-3]  # Remove trailing ```
            response_text = response_text.strip()

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
        response: Any,
        mention: EntityMention,
        context: ConversationContext,
    ) -> ResolutionResult:
        """Parse Anthropic response for coreference resolution.

        Args:
            response: Anthropic API response
            mention: Original mention
            context: Conversation context

        Returns:
            ResolutionResult with resolved entity or FAILED
        """
        if not response.content:
            return ResolutionResult.failed(
                mention_text=mention.text,
                reason="No response from LLM",
            )

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

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
            confidence=heuristics.CONFIDENCE_COREFERENCE,  # Claude coreference confidence
            method=ResolutionMethod.COREFERENCE,
            mention_text=mention.text,
            canonical_name=matching_entity[1],
            metadata={
                "llm_response": response_text,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "provider": "anthropic",
                "model": self.MODEL,
            },
        )

    def _build_mention_extraction_prompt(self, text: str) -> str:
        """Build prompt for entity mention extraction.

        Args:
            text: Text to extract mentions from

        Returns:
            Formatted prompt string
        """
        return f"""Extract all entity mentions from the text below.

Text: "{text}"

Entity Types to Extract:
1. Named Entities: Companies, people, products (e.g., "Acme Corporation", "John Smith", "Widget X")
2. Identifiers: Alphanumeric codes (e.g., "SO-1001", "INV-1009", "WO-123")
3. First-Person Pronouns: "I", "me", "my", "mine", "myself"
4. Third-Person Pronouns: "they", "them", "their", "it", "its", "he", "him", "she", "her"
5. Demonstratives: "the customer", "the client", "the company", "the order", "the invoice"

Instructions:
1. Extract ALL mentions of entities (don't skip lowercase, typos, or variations)
2. For each mention, provide:
   - text: exact text as it appears
   - position: character offset where it starts
   - is_pronoun: true if it's a pronoun/demonstrative, false otherwise
   - is_first_person: true only for I/me/my/mine/myself, false otherwise
3. Skip common stopwords UNLESS they're clearly part of an entity name
4. Skip action verbs at the start of sentences (e.g., "Reschedule" in "Reschedule Kai Media")
5. IMPORTANT: For meta-statements like "remember that X" or "note that X", extract entities from the X part

Output Format (JSON):
{{
  "mentions": [
    {{
      "text": "Acme Corporation",
      "position": 15,
      "is_pronoun": false,
      "is_first_person": false
    }},
    {{
      "text": "I",
      "position": 45,
      "is_pronoun": true,
      "is_first_person": true
    }},
    {{
      "text": "SO-1001",
      "position": 60,
      "is_pronoun": false,
      "is_first_person": false
    }}
  ]
}}

Respond with ONLY the JSON object. If no mentions found, return {{"mentions": []}}."""

    def _parse_mention_extraction_response(
        self,
        response: Any,
        text: str,
    ) -> list[EntityMention]:
        """Parse Anthropic response for mention extraction.

        Args:
            response: Anthropic API response
            text: Original text

        Returns:
            List of EntityMention objects
        """
        if not response.content:
            logger.warning("empty_mention_extraction_response")
            return []

        # Extract text from response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        if not response_text:
            logger.warning("no_text_in_mention_extraction_response")
            return []

        try:
            # Strip markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            parsed = json.loads(response_text)

            if not isinstance(parsed, dict):
                msg = "Response is not a JSON object"
                raise ValueError(msg)

            raw_mentions = parsed.get("mentions", [])

            if not isinstance(raw_mentions, list):
                msg = "mentions field is not a list"
                raise ValueError(msg)

            # Convert to EntityMention objects
            mentions: list[EntityMention] = []
            sentences = self._split_text_into_sentences(text)

            for raw in raw_mentions:
                try:
                    mention_text = raw["text"]
                    position = raw["position"]
                    is_pronoun = raw.get("is_pronoun", False)
                    is_first_person = raw.get("is_first_person", False)

                    # Get sentence and context
                    sentence = self._get_sentence_at_position(sentences, position)
                    context_before, context_after = self._get_context(
                        text, position, len(mention_text)
                    )

                    mention = EntityMention(
                        text=mention_text,
                        position=position,
                        context_before=context_before,
                        context_after=context_after,
                        is_pronoun=is_pronoun,
                        sentence=sentence,
                        is_first_person=is_first_person,
                    )
                    mentions.append(mention)

                except (KeyError, ValueError) as e:
                    logger.warning(
                        "invalid_mention_from_llm",
                        error=str(e),
                        raw_mention=raw,
                    )
                    continue

            logger.debug(
                "parsed_mention_extraction_response",
                mention_count=len(mentions),
            )

            return mentions

        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_error_in_mention_extraction",
                response_text=response_text[:200],
                error=str(e),
            )
            return []
        except ValueError as e:
            logger.error(
                "invalid_mention_extraction_response_format",
                error=str(e),
            )
            return []

    def _split_text_into_sentences(self, text: str) -> list[tuple[str, int]]:
        """Split text into sentences with positions.

        Args:
            text: Text to split

        Returns:
            List of (sentence, start_position) tuples
        """
        import re

        sentence_pattern = re.compile(r"([^.!?]+[.!?])")
        sentences: list[tuple[str, int]] = []
        pos = 0

        for match in sentence_pattern.finditer(text):
            sentence = match.group().strip()
            sentences.append((sentence, pos))
            pos = match.end()

        # Handle last sentence if no ending punctuation
        if pos < len(text):
            sentences.append((text[pos:].strip(), pos))

        return sentences if sentences else [(text, 0)]

    def _get_sentence_at_position(
        self, sentences: list[tuple[str, int]], position: int
    ) -> str:
        """Get the sentence containing a position.

        Args:
            sentences: List of (sentence, start_pos) tuples
            position: Character position

        Returns:
            Sentence text
        """
        for i, (sentence, start_pos) in enumerate(sentences):
            if i + 1 < len(sentences):
                next_start = sentences[i + 1][1]
                if start_pos <= position < next_start:
                    return sentence
            else:
                return sentence

        return sentences[0][0] if sentences else ""

    def _get_context(
        self, text: str, position: int, mention_length: int, window: int = 50
    ) -> tuple[str, str]:
        """Get context before and after a mention.

        Args:
            text: Full text
            position: Mention start position
            mention_length: Length of mention
            window: Context window size in characters

        Returns:
            (context_before, context_after) tuple
        """
        start = max(0, position - window)
        end = min(len(text), position + mention_length + window)

        context_before = text[start:position].strip()
        context_after = text[position + mention_length : end].strip()

        return context_before, context_after

    def _track_usage(self, response: Any) -> None:
        """Track token usage and costs.

        Args:
            response: Anthropic API response
        """
        if not hasattr(response, "usage"):
            return

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        total_tokens = input_tokens + output_tokens

        self._total_tokens_used += total_tokens

        # Claude Haiku 4.5 pricing: $1.00 per 1M input, $5.00 per 1M output
        input_cost = (input_tokens / 1_000_000) * 1.00
        output_cost = (output_tokens / 1_000_000) * 5.00
        cost = input_cost + output_cost

        self._total_cost += cost

        logger.debug(
            "llm_usage_tracked",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost=cost,
            total_cost=self._total_cost,
            provider="anthropic",
            model=self.MODEL,
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

    async def generate_structured_output(
        self,
        prompt: str,
        response_format: str = "json",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """Generate structured output (JSON) from a prompt.

        Used for consolidation, analysis, and other structured generation tasks.

        Args:
            prompt: User prompt
            response_format: Expected format (json, text)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text (JSON string if response_format=json)

        Raises:
            LLMServiceError: If generation fails
        """
        try:
            logger.debug(
                "calling_anthropic_for_structured_generation",
                prompt_length=len(prompt),
                format=response_format,
                model=self.MODEL,
            )

            system_prompt = "You are a helpful assistant that generates structured output."
            if response_format == "json":
                system_prompt += " Always respond with valid JSON only, no other text."

            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            # Track usage
            self._track_usage(response)

            # Extract text from response
            response_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Clean up JSON response if needed
            if response_format == "json":
                response_text = response_text.strip()
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            logger.info(
                "structured_generation_success",
                response_length=len(response_text),
                tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return response_text

        except Exception as e:
            logger.error(
                "structured_generation_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Structured output generation failed: {e}"
            raise LLMServiceError(msg) from e

    async def chat_with_tools(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str = "claude-haiku-4-5",
    ) -> LLMToolResponse:
        """Chat with tool calling support using Claude.

        Vision Alignment:
        - Emergent intelligence (LLM decides what to fetch)
        - No hardcoded query planning
        - Adaptive to context

        Args:
            system_prompt: System instructions
            messages: Conversation messages in Anthropic format
            tools: Available tools in Claude format
            model: Model to use (default: Claude 4.5 Haiku)

        Returns:
            Response with optional tool calls

        Raises:
            LLMServiceError: If API call fails
        """
        try:
            logger.debug(
                "calling_anthropic_with_tools",
                model=model,
                tool_count=len(tools),
                message_count=len(messages),
            )

            # Call Anthropic Messages API with tools
            response = await self.client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type] # Claude native tool calling
            )

            # Track usage
            self._track_usage(response)

            # Extract tool calls if present
            tool_calls = None
            if response.stop_reason == "tool_use":
                tool_calls = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_calls.append(
                            ToolCall(
                                id=block.id,
                                name=block.name,
                                arguments=block.input,  # type: ignore[arg-type]
                            )
                        )

                logger.info(
                    "llm_tool_calls_requested",
                    tool_count=len(tool_calls),
                    tools=[tc.name for tc in tool_calls],
                )

            # Extract text content
            content = None
            for block in response.content:
                if hasattr(block, "text"):
                    content = block.text
                    break

            result = LLMToolResponse(
                content=content,
                tool_calls=tool_calls,
            )

            logger.debug(
                "anthropic_tool_call_complete",
                has_content=content is not None,
                has_tool_calls=tool_calls is not None,
                tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

            return result

        except Exception as e:
            logger.error(
                "anthropic_tool_call_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            msg = f"Anthropic tool calling failed: {e}"
            raise LLMServiceError(msg) from e
