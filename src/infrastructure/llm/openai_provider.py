"""OpenAI LLM Provider - Infrastructure adapter for OpenAI API.

This adapter implements the LLMProviderPort interface using OpenAI's API.

Architecture: Infrastructure layer (depends on domain port, not vice versa).
"""


import structlog
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError

from src.domain.ports.llm_provider_port import LLMProviderPort, LLMResponse

logger = structlog.get_logger()


class OpenAIProvider(LLMProviderPort):
    """OpenAI API adapter with comprehensive error handling and cost tracking.

    Pricing as of 2025 (per 1K tokens):
    - gpt-4o: $0.0025 input, $0.01 output
    - gpt-4o-mini: $0.00015 input, $0.0006 output
    """

    # Pricing table (USD per 1000 tokens)
    PRICING: dict[str, dict[str, float]] = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4": {"input": 0.03, "output": 0.06},  # Fallback for older models
    }

    def __init__(self, api_key: str):
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key

        Raises:
            ValueError: If API key is empty or invalid format
        """
        if not api_key or not isinstance(api_key, str):
            msg = "OpenAI API key must be a non-empty string"
            raise ValueError(msg)

        self._client = AsyncOpenAI(api_key=api_key)
        logger.info("openai_provider_initialized", model_support=list(self.PRICING.keys()))

    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate completion from OpenAI.

        Implements comprehensive error handling:
        - Rate limits - log and return error message
        - API errors - log and return error message
        - Network errors - log and return error message
        - All errors are graceful (no crashes)

        Args:
            prompt: Input prompt
            model: Model to use (default: gpt-4o-mini for cost efficiency)
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
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Extract usage and calculate cost
            usage = response.usage
            cost_usd = self._calculate_cost(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )

            content = response.choices[0].message.content or ""

            logger.info(
                "llm_generation_completed",
                model=model,
                tokens_used=usage.total_tokens,
                cost_usd=cost_usd,
                response_length=len(content),
            )

            return LLMResponse(
                content=content,
                tokens_used=usage.total_tokens,
                model=model,
                cost_usd=cost_usd,
            )

        except RateLimitError as e:
            logger.warning("openai_rate_limit_exceeded", error=str(e), model=model)
            return self._error_response(
                error_msg="Rate limit exceeded. Please try again in a moment.",
                model=model,
            )

        except APIConnectionError as e:
            logger.error("openai_connection_failed", error=str(e), model=model)
            return self._error_response(
                error_msg="Failed to connect to OpenAI. Check your network connection.",
                model=model,
            )

        except APIError as e:
            logger.error("openai_api_error", error=str(e), model=model, status_code=e.status_code)
            return self._error_response(
                error_msg=f"OpenAI API error: {e!s}",
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
        # Get pricing for model (fallback to gpt-4 if unknown)
        pricing = self.PRICING.get(model, self.PRICING["gpt-4"])

        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

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
