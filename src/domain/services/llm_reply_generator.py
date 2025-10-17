"""LLM reply generation service.

Generates natural language replies from context (domain facts + memories).

Architecture: Pure domain service using LLMProviderPort (hexagonal architecture).
No direct OpenAI dependency - uses port/adapter pattern.
"""

from datetime import UTC, datetime

import structlog

from src.domain.ports.llm_provider_port import LLMProviderPort, LLMResponse
from src.domain.services.debug_trace_service import DebugTraceService
from src.domain.value_objects.conversation_context_reply import ReplyContext

logger = structlog.get_logger(__name__)


class LLMReplyGenerator:
    """Generate natural language replies with context awareness.

    Philosophy: This is where LLM excels - synthesis and natural language.
    Everything else (retrieval, scoring, queries) is deterministic.

    Design: Takes ReplyContext (domain facts + memories) and generates
    concise, cited, contextual responses.

    Architecture: Depends on LLMProviderPort (not OpenAI directly).
    """

    # Default configuration (overridable per instance)
    MAX_TOKENS = 500  # Enforce conciseness
    TEMPERATURE = 0.7  # Balanced creativity/accuracy

    def __init__(
        self,
        llm_provider: LLMProviderPort | None,
        model: str = "gpt-4o-mini",
    ):
        """Initialize LLM reply generator.

        Args:
            llm_provider: LLM provider implementation (None = fallback mode)
            model: Model to use for generation (e.g., 'claude-haiku-4-5')
        """
        self._provider = llm_provider
        self._model = model
        self._total_tokens_used = 0
        self._total_cost = 0.0

    async def generate(self, context: ReplyContext) -> str:
        """Generate reply from query and context.

        Args:
            context: Full conversation context (domain facts + memories)

        Returns:
            Natural language reply

        Raises:
            LLMServiceError: If generation fails critically
        """
        # If no provider, use fallback mode
        if not self._provider:
            logger.info("llm_provider_not_available", mode="fallback")
            return self._fallback_reply(context)

        try:
            # Build system prompt from context
            system_prompt = context.to_system_prompt()

            # Log context summary
            logger.info(
                "generating_llm_reply",
                **context.to_debug_summary(),
            )

            # Combine system prompt and user query into single prompt
            # (LLMProviderPort uses simple user message format)
            full_prompt = f"{system_prompt}\n\nUser Query: {context.query}"

            # Generate reply via LLM provider
            start_time = datetime.now(UTC)
            llm_response = await self._provider.generate_completion(
                prompt=full_prompt,
                model=self._model,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS,
            )
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Track usage
            self._track_usage(llm_response)

            # Add debug trace
            DebugTraceService.add_llm_call_trace(
                model=llm_response.model,
                prompt_length=len(full_prompt),
                response_length=len(llm_response.content),
                tokens_used=llm_response.tokens_used,
                cost_usd=llm_response.cost_usd,
                duration_ms=duration_ms,
            )

            # Extract reply
            reply = llm_response.content.strip() if llm_response.content else ""

            if not reply:
                logger.warning("empty_reply_response")
                return self._fallback_reply(context)

            logger.info(
                "llm_reply_generated",
                user_id=context.user_id,
                reply_length=len(reply),
                tokens=llm_response.tokens_used,
                cost_usd=llm_response.cost_usd,
            )

            return reply

        except Exception as e:
            logger.error(
                "llm_reply_generation_failed",
                user_id=context.user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Graceful degradation - return fallback
            return self._fallback_reply(context)

    def _fallback_reply(self, context: ReplyContext) -> str:
        """Fallback reply when LLM fails.

        Philosophy: Fail gracefully - return DB facts, acknowledge limitation.

        Args:
            context: Reply context

        Returns:
            Fallback reply string
        """
        if context.domain_facts:
            # Build reply from domain facts
            facts_summary = "\n".join(
                f"- {f.content}" for f in context.domain_facts[:3]
            )
            return (
                f"Based on database records:\n{facts_summary}\n\n"
                "(Unable to generate detailed response - showing raw facts)"
            )
        elif context.retrieved_memories:
            # Build reply from memories
            memories_summary = "\n".join(
                f"- {m.content}" for m in context.retrieved_memories[:3]
            )
            return (
                f"Based on my memory:\n{memories_summary}\n\n"
                "(Unable to generate detailed response - showing raw memories)"
            )
        else:
            return "I don't have enough information to answer that question."

    def _track_usage(self, llm_response: LLMResponse) -> None:
        """Track token usage and costs.

        Args:
            llm_response: LLM provider response with usage metadata
        """
        tokens = llm_response.tokens_used
        cost = llm_response.cost_usd

        self._total_tokens_used += tokens
        self._total_cost += cost

        logger.debug(
            "llm_usage_tracked",
            tokens=tokens,
            cost=cost,
            model=llm_response.model,
            total_tokens=self._total_tokens_used,
            total_cost=self._total_cost,
        )

    @property
    def total_tokens_used(self) -> int:
        """Get total tokens used.

        Returns:
            Total tokens
        """
        return self._total_tokens_used

    @property
    def total_cost(self) -> float:
        """Get total estimated cost.

        Returns:
            Total cost in USD
        """
        return self._total_cost
