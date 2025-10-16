"""LLM Provider Port - Abstract interface for LLM services.

This port defines the contract for LLM providers (OpenAI, Anthropic, etc.)
without coupling the domain layer to any specific implementation.

Architecture: Pure domain layer (no infrastructure imports).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    """Response from LLM provider with metadata."""

    content: str
    tokens_used: int
    model: str
    cost_usd: float


class LLMProviderPort(ABC):
    """Abstract interface for LLM providers.

    Implementations:
    - OpenAIProvider (infrastructure layer)
    - AnthropicProvider (future)
    - MockProvider (testing)
    """

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        """Generate completion from LLM.

        Args:
            prompt: Input prompt text
            model: Model identifier (e.g., 'gpt-4o-mini', 'gpt-4o')
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with content and metadata

        Raises:
            LLMProviderError: If generation fails
        """
