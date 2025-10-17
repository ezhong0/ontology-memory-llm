"""LLM-based entity mention extractor.

Vision-aligned extraction using Claude Haiku 4.5 for intelligent entity recognition.
Replaces brittle regex patterns with semantic understanding.
"""
import structlog

from src.domain.ports.llm_service import ILLMService
from src.domain.value_objects import EntityMention

logger = structlog.get_logger(__name__)


class LLMMentionExtractor:
    """LLM-based entity mention extractor.

    Uses Claude Haiku 4.5 for intelligent entity extraction that handles:
    - Capitalized and lowercase entities ("Apple" and "apple")
    - Typos and variations ("Aple" → "Apple")
    - Context-aware extraction (knows when "Call" is a verb vs entity)
    - Complex patterns (multi-word entities, pronouns, identifiers)

    Vision Alignment:
    - Trust LLM intelligence over brittle patterns
    - Semantic understanding over regex matching
    - Graceful handling of edge cases
    - Composable with existing pipeline

    This is a drop-in replacement for SimpleMentionExtractor with the same interface.
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize LLM-based extractor.

        Args:
            llm_service: LLM service implementing extract_entity_mentions
        """
        self.llm_service = llm_service

    async def extract_mentions(self, text: str) -> list[EntityMention]:
        """Extract entity mentions from text using LLM.

        Args:
            text: Text to extract mentions from

        Returns:
            List of EntityMention objects (may be empty)
        """
        if not text or not text.strip():
            return []

        try:
            mentions = await self.llm_service.extract_entity_mentions(text)

            logger.info(
                "llm_mentions_extracted",
                count=len(mentions),
                text_length=len(text),
            )

            return mentions

        except Exception as e:
            logger.error(
                "llm_mention_extraction_failed",
                error=str(e),
                text_length=len(text),
            )
            # Graceful degradation: return empty list rather than crashing
            # The pipeline can continue with no mentions extracted
            return []
