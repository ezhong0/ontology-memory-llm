"""Unit tests for SimpleMentionExtractor.

Tests pattern-based entity mention extraction.
"""
import pytest

from src.domain.services import SimpleMentionExtractor
from src.domain.value_objects import EntityMention


@pytest.mark.unit
class TestSimpleMentionExtractor:
    """Test SimpleMentionExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create SimpleMentionExtractor instance."""
        return SimpleMentionExtractor()

    def test_extract_capitalized_entities(self, extractor):
        """Test extraction of capitalized named entities."""
        text = "I met with Acme Corporation and John Smith yesterday."

        mentions = extractor.extract_mentions(text)

        # Should extract "Acme Corporation" and "John Smith"
        assert len(mentions) >= 2
        mention_texts = [m.text for m in mentions]
        assert "Acme Corporation" in mention_texts
        assert "John Smith" in mention_texts

    def test_extract_coreference_terms(self, extractor):
        """Test extraction of pronouns and coreference terms."""
        text = "They said it was ready, and the customer confirmed."

        mentions = extractor.extract_mentions(text)

        # Should extract: they, it, the customer
        coreference_mentions = [m for m in mentions if m.is_pronoun]
        assert len(coreference_mentions) >= 2

        coreference_texts = {m.text.lower() for m in coreference_mentions}
        assert "they" in coreference_texts
        assert "it" in coreference_texts

    def test_skip_stopwords(self, extractor):
        """Test that common stopwords are not extracted."""
        text = "I went to The market with A friend."

        mentions = extractor.extract_mentions(text)

        # Should NOT extract: "I", "The", "A"
        mention_texts = [m.text for m in mentions]
        assert "I" not in mention_texts
        assert "The" not in mention_texts
        assert "A" not in mention_texts

    def test_skip_single_words_at_document_start(self, extractor):
        """Test that single-word entities at document start (position 0) are skipped."""
        text = "Hello there everyone."

        mentions = extractor.extract_mentions(text)

        # "Hello" should be skipped (position 0, single word)
        mention_texts = [m.text for m in mentions]
        assert "Hello" not in mention_texts

        # But after ". " single names like "Bob" ARE extracted (proper nouns)
        text2 = "Hi. Bob called."
        mentions2 = extractor.extract_mentions(text2)
        mention_texts2 = [m.text for m in mentions2]
        # "Bob" should be extracted (it's likely a proper name)
        assert "Bob" in mention_texts2

    def test_allow_multiword_entities_at_sentence_start(self, extractor):
        """Test that multi-word entities at sentence start ARE extracted."""
        text = "Acme Corporation confirmed the order."

        mentions = extractor.extract_mentions(text)

        # "Acme Corporation" should be extracted even though it's at sentence start
        mention_texts = [m.text for m in mentions]
        assert "Acme Corporation" in mention_texts

    def test_extract_context_around_mention(self, extractor):
        """Test that context before and after mention is captured."""
        text = "I spoke with Acme Corporation about their pricing model."

        mentions = extractor.extract_mentions(text)

        acme_mention = next((m for m in mentions if "Acme" in m.text), None)
        assert acme_mention is not None
        assert "spoke with" in acme_mention.context_before
        assert "about" in acme_mention.context_after

    def test_mention_has_sentence_context(self, extractor):
        """Test that each mention includes the full sentence."""
        text = "Hello. Acme Corporation is great. Thank you."

        mentions = extractor.extract_mentions(text)

        acme_mention = next((m for m in mentions if "Acme" in m.text), None)
        assert acme_mention is not None
        assert "Acme Corporation is great" in acme_mention.sentence

    def test_empty_text_returns_empty_list(self, extractor):
        """Test that empty text returns no mentions."""
        assert extractor.extract_mentions("") == []
        assert extractor.extract_mentions("   ") == []
        assert extractor.extract_mentions(None) == []

    def test_no_duplicates(self, extractor):
        """Test that duplicate mentions at same position are removed."""
        text = "Acme Corp and Acme Corp are the same."

        mentions = extractor.extract_mentions(text)

        # Should have two mentions (one for each occurrence)
        acme_mentions = [m for m in mentions if "Acme" in m.text]
        assert len(acme_mentions) == 2

        # But they should be at different positions
        positions = [m.position for m in acme_mentions]
        assert len(set(positions)) == 2

    def test_pronoun_flag(self, extractor):
        """Test that is_pronoun flag is set correctly."""
        text = "They met with Acme Corporation yesterday."

        mentions = extractor.extract_mentions(text)

        # "they" should have is_pronoun=True
        they_mention = next((m for m in mentions if m.text.lower() == "they"), None)
        assert they_mention is not None
        assert they_mention.is_pronoun

        # "Acme Corporation" should have is_pronoun=False
        acme_mention = next((m for m in mentions if "Acme" in m.text), None)
        assert acme_mention is not None
        assert not acme_mention.is_pronoun

    def test_requires_coreference_property(self, extractor):
        """Test that requires_coreference property works correctly."""
        text = "They said it works."

        mentions = extractor.extract_mentions(text)

        for mention in mentions:
            if mention.is_pronoun:
                assert mention.requires_coreference

    def test_complex_sentence_with_multiple_entities(self, extractor):
        """Test extraction from complex sentence with multiple entities."""
        text = (
            "I discussed the proposal with John Smith from Acme Corporation, "
            "and they agreed to the terms. The customer will sign next week."
        )

        mentions = extractor.extract_mentions(text)

        # Should extract: John Smith, Acme Corporation, they, the customer
        assert len(mentions) >= 4

        mention_texts = [m.text.lower() for m in mentions]
        assert any("john smith" in text for text in mention_texts)
        assert any("acme corporation" in text for text in mention_texts)
        assert "they" in mention_texts
        assert "the customer" in mention_texts
