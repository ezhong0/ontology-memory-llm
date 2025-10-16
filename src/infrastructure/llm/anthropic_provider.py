"""Anthropic LLM Provider - Infrastructure adapter for Anthropic API.

This adapter implements the LLMProviderPort interface using Anthropic's API.

Architecture: Infrastructure layer (depends on domain port, not vice versa).
"""

import structlog
from anthropic import (
    APIConnectionError,
    APIError,
    AsyncAnthropic,
    RateLimitError,
)

from src.domain.ports.llm_provider_port import LLMProviderPort, LLMResponse

logger = structlog.get_logger()


class AnthropicProvider(LLMProviderPort):
    """Anthropic API adapter with comprehensive error handling and cost tracking.

    Pricing as of 2025 (per 1M tokens):
    - claude-haiku-4-5: $1.00 input, $5.00 output
    - claude-3-5-haiku-20241022: $1.00 input, $5.00 output
    - claude-sonnet-4-5-20250929: $3.00 input, $15.00 output
    - claude-3-5-sonnet-20241022: $3.00 input, $15.00 output
    """

    # Pricing table (USD per 1M tokens)
    PRICING: dict[str, dict[str, float]] = {
        "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
        "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
        "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
        "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
        "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    }

    def __init__(self, api_key: str):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key

        Raises:
            ValueError: If API key is empty or invalid format
        """
        if not api_key or not isinstance(api_key, str):
            msg = "Anthropic API key must be a non-empty string"
            raise ValueError(msg)

        self._client = AsyncAnthropic(api_key=api_key)
        logger.info("anthropic_provider_initialized", model_support=list(self.PRICING.keys()))

    async def generate_completion(
        self,
        prompt: str,
        model: str = "claude-haiku-4-5",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate completion from Anthropic.

        Implements comprehensive error handling:
        - Rate limits - log and return error message
        - API errors - log and return error message
        - Network errors - log and return error message
        - All errors are graceful (no crashes)

        Args:
            prompt: Input prompt
            model: Model to use (default: claude-haiku-4-5 for best cost/performance)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate

        Returns:
            LLMResponse with content and cost tracking
        """
        logger.info(
            "llm_generation_started",
            model=model,
            prompt_length=len(prompt),
            temperature=temperature,
            max_tokens=max_tokens,
        )

        try:
            response = await self._client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract usage and calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            cost_usd = self._calculate_cost(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

            content = response.content[0].text if response.content else ""

            logger.info(
                "llm_generation_completed",
                model=model,
                tokens_used=total_tokens,
                cost_usd=cost_usd,
                response_length=len(content),
            )

            return LLMResponse(
                content=content,
                tokens_used=total_tokens,
                model=model,
                cost_usd=cost_usd,
            )

        except RateLimitError as e:
            logger.warning("anthropic_rate_limit_exceeded", error=str(e), model=model)
            return self._error_response(
                error_msg="Rate limit exceeded. Please try again in a moment.",
                model=model,
            )

        except APIConnectionError as e:
            logger.error("anthropic_connection_failed", error=str(e), model=model)
            return self._error_response(
                error_msg="Failed to connect to Anthropic. Check your network connection.",
                model=model,
            )

        except APIError as e:
            logger.error("anthropic_api_error", error=str(e), model=model, status_code=e.status_code)
            return self._error_response(
                error_msg=f"Anthropic API error: {e!s}",
                model=model,
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error("llm_generation_unexpected_error", error=str(e), model=model, error_type=type(e).__name__)
            return self._error_response(
                error_msg=f"Unexpected error: {e!s}",
                model=model,
            )

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for this request.

        Args:
            model: Model used
            input_tokens: Input token count
            output_tokens: Output token count

        Returns:
            Cost in USD
        """
        # Get pricing for model (fallback to haiku 4.5 if unknown)
        pricing = self.PRICING.get(model, self.PRICING["claude-haiku-4-5"])

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _error_response(self, error_msg: str, model: str) -> LLMResponse:
        """Create error response (graceful failure).

        Returns LLMResponse with error message as content.
        This allows system to continue operating even when LLM fails.
        """
        return LLMResponse(
            content=f"[LLM Error] {error_msg} Using fallback mode.",
            tokens_used=0,
            model=model,
            cost_usd=0.0,
        )
