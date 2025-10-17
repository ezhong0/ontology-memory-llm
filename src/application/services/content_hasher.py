"""Content hashing for idempotency.

Generates deterministic hashes for content deduplication.
Prevents duplicate memories from repeated chat messages.

Vision Alignment:
- Idempotency (re-sending same message doesn't duplicate state)
- Time-aware (allows re-statements after time window)
- Deterministic (same input → same hash)
"""

import hashlib
from datetime import datetime, timezone


class ContentHasher:
    """Generate content hashes for deduplication.

    Philosophy: Time-bucketed hashing allows "I like pizza" to create a memory
    today, but if repeated tomorrow, creates a new confirmation rather than
    being rejected as duplicate. This models human conversation patterns.
    """

    @staticmethod
    def generate_memory_hash(
        user_id: str,
        content: str,
        timestamp: datetime | None = None,
        bucket_hours: int = 24,
    ) -> str:
        """Generate deterministic hash for memory content.

        Args:
            user_id: User identifier
            content: Memory content (natural language)
            timestamp: When memory was created (defaults to now)
            bucket_hours: Time bucket size in hours (default: 24)
                         Memories in same bucket are deduplicated,
                         different buckets are treated as confirmations.

        Returns:
            SHA-256 hash (hex string)

        Examples:
            >>> hasher = ContentHasher()
            >>> hash1 = hasher.generate_memory_hash("user123", "likes pizza", datetime(2025, 1, 1, 10, 0))
            >>> hash2 = hasher.generate_memory_hash("user123", "likes pizza", datetime(2025, 1, 1, 15, 0))
            >>> hash1 == hash2  # Same day, same hash
            True
            >>> hash3 = hasher.generate_memory_hash("user123", "likes pizza", datetime(2025, 1, 2, 10, 0))
            >>> hash1 == hash3  # Different day, different hash
            False
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Normalize timestamp to bucket boundary
        # Example: bucket_hours=24 → all times on 2025-01-01 map to 2025-01-01 00:00:00
        hours_since_epoch = int(timestamp.timestamp() / 3600)
        bucket = hours_since_epoch // bucket_hours

        # Normalize content: lowercase, strip whitespace
        normalized_content = content.strip().lower()

        # Combine components
        hash_input = f"{user_id}:{normalized_content}:{bucket}"

        # Generate SHA-256 hash
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    @staticmethod
    def generate_message_hash(
        user_id: str,
        message_content: str,
        timestamp: datetime | None = None,
    ) -> str:
        """Generate hash for raw chat message (stricter than memory hash).

        Used to detect exact message re-sends (e.g., API retry).
        Uses 1-hour bucket to allow re-sending after brief window.

        Args:
            user_id: User identifier
            message_content: Raw message text
            timestamp: When message was sent (defaults to now)

        Returns:
            SHA-256 hash (hex string)
        """
        return ContentHasher.generate_memory_hash(
            user_id=user_id,
            content=message_content,
            timestamp=timestamp,
            bucket_hours=1,  # Stricter bucket for message deduplication
        )
