"""PII redaction service.

Redacts personally identifiable information from text before storage or transmission.
"""

import re
from dataclasses import dataclass
from re import Pattern

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class RedactionResult:
    """Result of PII redaction operation.

    Philosophy: Make redaction explicit and auditable.
    """

    original_text: str
    redacted_text: str
    redactions: list[dict[str, str]]  # [{"type": "phone", "token": "[PHONE-xxx]"}]
    was_redacted: bool

    def __bool__(self) -> bool:
        """True if any redaction occurred."""
        return self.was_redacted


class PIIRedactionService:
    """Redact PII from text before storage or transmission.

    Philosophy: Defensive security - always redact, log when found.

    Design: Layered defense strategy:
    1. Chat event storage: Redact before storing
    2. Semantic extraction: Redact before LLM extraction
    3. Reply generation: Defensive redaction (should not be needed)

    This ensures PII never enters the memory system.
    """

    # PII Patterns (compiled regex)
    PII_PATTERNS: dict[str, Pattern] = {
        "phone": re.compile(
            r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
    }

    def redact(self, text: str, preserve_length: bool = False) -> str:
        """Redact PII from text.

        Args:
            text: Text to redact
            preserve_length: If True, use tokens that preserve original length

        Returns:
            Redacted text
        """
        result = self.redact_with_metadata(text, preserve_length)
        return result.redacted_text

    def redact_with_metadata(
        self, text: str, preserve_length: bool = False
    ) -> RedactionResult:
        """Redact PII and return full metadata.

        Philosophy: Full observability of redaction events.

        Args:
            text: Text to redact
            preserve_length: If True, use tokens that preserve original length

        Returns:
            RedactionResult with original, redacted, and metadata
        """
        if not text:
            return RedactionResult(
                original_text=text,
                redacted_text=text,
                redactions=[],
                was_redacted=False,
            )

        redacted = text
        redactions = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = list(pattern.finditer(redacted))

            for match in matches:
                original_value = match.group()

                # Generate token
                if preserve_length:
                    # Preserve length for alignment in logs
                    token = f"[{pii_type.upper()[:3]}-{'x' * (len(original_value) - 7)}]"
                else:
                    token = f"[{pii_type.upper()}-REDACTED]"

                # Replace
                redacted = redacted.replace(original_value, token, 1)

                # Log redaction
                redactions.append(
                    {
                        "type": pii_type,
                        "original_length": len(original_value),
                        "token": token,
                    }
                )

                logger.warning(
                    "pii_redacted",
                    pii_type=pii_type,
                    original_length=len(original_value),
                )

        return RedactionResult(
            original_text=text,
            redacted_text=redacted,
            redactions=redactions,
            was_redacted=len(redactions) > 0,
        )

    def validate_no_pii(self, text: str) -> bool:
        """Validate that text contains no PII.

        Used in assertions/tests to verify redaction worked.

        Args:
            text: Text to validate

        Returns:
            True if no PII detected, False otherwise
        """
        return all(not pattern.search(text) for pattern in self.PII_PATTERNS.values())
