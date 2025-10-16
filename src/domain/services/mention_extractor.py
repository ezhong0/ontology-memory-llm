"""Simple entity mention extractor.

Pattern-based extraction for Phase 1A. LLM-based extraction can be added in Phase 1B+.
"""
import re

import structlog

from src.domain.value_objects import EntityMention

logger = structlog.get_logger(__name__)


class SimpleMentionExtractor:
    """Simple pattern-based entity mention extractor.

    Extracts:
    - Capitalized phrases (likely named entities: "Acme Corporation", "John Smith")
    - Common pronouns/demonstratives that need coreference resolution

    Limitations:
    - May miss entities in lowercase
    - May extract non-entities (e.g., sentence starts)
    - No semantic understanding

    For better accuracy, use LLM-based extraction (Phase 1B+).
    """

    # Pronouns and demonstratives that require coreference
    COREFERENCE_TERMS = {
        "they",
        "them",
        "their",
        "theirs",
        "it",
        "its",
        "he",
        "him",
        "his",
        "she",
        "her",
        "hers",
        "the customer",
        "the client",
        "the company",
        "the organization",
        "the vendor",
        "the supplier",
        "the order",
        "the invoice",
        "the product",
    }

    # Pattern for capitalized phrases (potential named entities)
    # Matches 1-5 consecutive capitalized words
    CAPITALIZED_PATTERN = re.compile(
        r"\b([A-Z][a-z]*(?:\s+[A-Z][a-z]*){0,4})\b"
    )

    # Pattern for alphanumeric identifiers (SO-1001, INV-1009, WO-123, etc.)
    # Matches: 2+ uppercase letters, hyphen, 1+ digits
    IDENTIFIER_PATTERN = re.compile(
        r"\b([A-Z]{2,}-\d+)\b"
    )

    # Common words to ignore (not entities)
    STOPWORDS = {
        "I",
        "The",
        "A",
        "An",
        "This",
        "That",
        "These",
        "Those",
        "Is",
        "Are",
        "Was",
        "Were",
        "Do",
        "Does",
        "Did",
        "Can",
        "Could",
        "Should",
        "Would",
        "Will",
        "May",
        "Might",
        "Must",
    }

    # Common action verbs that shouldn't be part of entity names
    # Used to filter out verb-entity combinations like "Reschedule Kai Media"
    ACTION_VERBS = {
        "Reschedule",
        "Schedule",
        "Cancel",
        "Update",
        "Create",
        "Delete",
        "Add",
        "Remove",
        "Send",
        "Draft",
        "Mark",
        "Complete",
        "Finish",
        "Start",
        "Begin",
        "Check",
        "Verify",
        "Review",
        "Approve",
        "Reject",
        "Contact",
        "Call",
        "Email",
        "Notify",
        "Remind",
        "Follow",
        "Track",
        "Monitor",
        "Generate",
        "Process",
        "Submit",
        "Confirm",
    }

    def extract_mentions(self, text: str) -> list[EntityMention]:
        """Extract entity mentions from text.

        Args:
            text: Text to extract mentions from

        Returns:
            List of EntityMention objects (may be empty)
        """
        if not text or not text.strip():
            return []

        mentions: list[EntityMention] = []
        text_lower = text.lower()

        # Split into sentences for better context
        sentences = self._split_sentences(text)

        # Extract coreference terms first (they need resolution)
        for term in self.COREFERENCE_TERMS:
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            for match in pattern.finditer(text_lower):
                position = match.start()
                sentence, sent_start = self._get_sentence_at_position(sentences, position)

                # Get context around mention
                context_before, context_after = self._get_context(text, position, len(term))

                mention = EntityMention(
                    text=match.group(),
                    position=position,
                    context_before=context_before,
                    context_after=context_after,
                    is_pronoun=True,
                    sentence=sentence,
                )
                mentions.append(mention)

                logger.debug(
                    "coreference_mention_extracted",
                    mention=mention.text,
                    position=position,
                )

        # Extract alphanumeric identifiers (SO-1001, INV-1009, etc.)
        for match in self.IDENTIFIER_PATTERN.finditer(text):
            identifier = match.group()
            position = match.start()

            sentence, sent_start = self._get_sentence_at_position(sentences, position)

            # Get context around mention
            context_before, context_after = self._get_context(
                text, position, len(identifier)
            )

            mention = EntityMention(
                text=identifier,
                position=position,
                context_before=context_before,
                context_after=context_after,
                is_pronoun=False,
                sentence=sentence,
            )
            mentions.append(mention)

            logger.debug(
                "identifier_mention_extracted",
                mention=mention.text,
                position=position,
            )

        # Extract capitalized phrases (potential named entities)
        for match in self.CAPITALIZED_PATTERN.finditer(text):
            candidate = match.group()

            # Skip if it's a stopword or single letter
            if candidate in self.STOPWORDS or len(candidate) == 1:
                continue

            # Get position before any modifications
            position = match.start()

            # Skip entities that start with action verbs
            # e.g., "Reschedule Kai Media" → extract "Kai Media" instead
            first_word = candidate.split()[0] if " " in candidate else candidate
            if first_word in self.ACTION_VERBS:
                # Try to extract the entity part (everything after the verb)
                entity_part = candidate[len(first_word):].strip()
                if entity_part and len(entity_part) > 1:
                    # Replace candidate with the entity part
                    # Adjust position to point to start of entity (skip verb + space)
                    position = position + len(first_word) + 1
                    candidate = entity_part
                else:
                    # No valid entity part, skip
                    continue

            # Skip single-word entities at sentence start (could be any word)
            # But allow multi-word entities (e.g., "Acme Corporation")
            is_sentence_start = match.start() == 0 or text[match.start() - 1:match.start() + 1] == ". "
            is_single_word = " " not in candidate

            if is_sentence_start and is_single_word:
                continue

            sentence, sent_start = self._get_sentence_at_position(sentences, position)

            # Get context around mention
            context_before, context_after = self._get_context(
                text, position, len(candidate)
            )

            mention = EntityMention(
                text=candidate,
                position=position,
                context_before=context_before,
                context_after=context_after,
                is_pronoun=False,
                sentence=sentence,
            )
            mentions.append(mention)

            logger.debug(
                "named_entity_mention_extracted",
                mention=mention.text,
                position=position,
            )

        # Remove duplicates (same text at same position)
        unique_mentions = self._remove_duplicates(mentions)

        logger.info(
            "mentions_extracted",
            count=len(unique_mentions),
            text_length=len(text),
        )

        return unique_mentions

    def _split_sentences(self, text: str) -> list[tuple[str, int]]:
        """Split text into sentences with positions.

        Args:
            text: Text to split

        Returns:
            List of (sentence, start_position) tuples
        """
        # Simple sentence splitting (improved regex can be added later)
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

        return sentences

    def _get_sentence_at_position(
        self, sentences: list[tuple[str, int]], position: int
    ) -> tuple[str, int]:
        """Get the sentence containing a position.

        Args:
            sentences: List of (sentence, start_pos) tuples
            position: Character position

        Returns:
            (sentence, sentence_start_position) tuple
        """
        for i, (sentence, start_pos) in enumerate(sentences):
            if i + 1 < len(sentences):
                next_start = sentences[i + 1][1]
                if start_pos <= position < next_start:
                    return sentence, start_pos
            else:
                # Last sentence
                return sentence, start_pos

        # Fallback
        return sentences[0][0] if sentences else ("", 0)

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
        context_after = text[position + mention_length:end].strip()

        return context_before, context_after

    def _remove_duplicates(self, mentions: list[EntityMention]) -> list[EntityMention]:
        """Remove duplicate mentions (same text at same position).

        Args:
            mentions: List of mentions

        Returns:
            List with duplicates removed
        """
        seen: set[tuple[str, int]] = set()
        unique: list[EntityMention] = []

        for mention in mentions:
            key = (mention.text.lower(), mention.position)
            if key not in seen:
                seen.add(key)
                unique.append(mention)

        return unique
