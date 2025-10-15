"""
Test Helper Utilities

Provides reusable assertion helpers, validators, and test utilities.
These helpers make tests more readable and maintainable.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import re


# ============================================================================
# Assertion Helpers
# ============================================================================

def assert_confidence_in_range(
    confidence: float,
    min_val: float = 0.0,
    max_val: float = 0.95,
    name: str = "Confidence"
):
    """
    Assert confidence is in valid range.

    Args:
        confidence: Confidence value to check
        min_val: Minimum valid value (default: 0.0)
        max_val: Maximum valid value (default: 0.95 - MAX_CONFIDENCE)
        name: Name for error message

    Raises:
        AssertionError: If confidence is out of range
    """
    assert min_val <= confidence <= max_val, \
        f"{name} {confidence} not in valid range [{min_val}, {max_val}]"


def assert_valid_entity_id(entity_id: str):
    """
    Assert entity_id follows format: 'type:identifier'.

    Examples:
        - customer:acme_123 ✓
        - product:prod_456 ✓
        - sales_order:so_789 ✓
        - InvalidFormat ✗

    Args:
        entity_id: Entity ID to validate

    Raises:
        AssertionError: If format is invalid
    """
    pattern = r'^[a-z_]+:[a-zA-Z0-9_-]+$'
    assert re.match(pattern, entity_id), \
        f"Invalid entity_id format: '{entity_id}' (expected: 'type:identifier')"


def assert_valid_uuid(value: str, name: str = "UUID"):
    """
    Assert value is valid UUID format.

    Args:
        value: UUID string to validate
        name: Name for error message
    """
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, value.lower()), \
        f"{name} '{value}' is not a valid UUID"


def assert_timestamp_recent(
    timestamp: datetime,
    max_age_seconds: int = 60,
    name: str = "Timestamp"
):
    """
    Assert timestamp is recent (within last N seconds).

    Useful for testing created_at, updated_at fields.

    Args:
        timestamp: Timestamp to check
        max_age_seconds: Maximum age in seconds (default: 60)
        name: Name for error message
    """
    age_seconds = (datetime.utcnow() - timestamp).total_seconds()
    assert age_seconds <= max_age_seconds, \
        f"{name} is too old: {age_seconds}s > {max_age_seconds}s"


def assert_dict_contains(
    actual: Dict[str, Any],
    expected_subset: Dict[str, Any],
    path: str = ""
):
    """
    Assert dictionary contains expected key-value pairs (subset matching).

    Supports nested dictionaries.

    Args:
        actual: Actual dictionary
        expected_subset: Expected key-value pairs (subset)
        path: Current path (for error messages)

    Example:
        actual = {"user": {"name": "Alice", "age": 30}, "active": True}
        expected = {"user": {"name": "Alice"}, "active": True}
        assert_dict_contains(actual, expected)  # Passes
    """
    for key, expected_value in expected_subset.items():
        current_path = f"{path}.{key}" if path else key

        assert key in actual, \
            f"Missing key '{current_path}' in actual dictionary"

        actual_value = actual[key]

        if isinstance(expected_value, dict) and isinstance(actual_value, dict):
            # Recurse for nested dictionaries
            assert_dict_contains(actual_value, expected_value, current_path)
        else:
            assert actual_value == expected_value, \
                f"Value mismatch at '{current_path}': expected {expected_value}, got {actual_value}"


def assert_list_contains_items(
    actual: List[Any],
    expected_items: List[Any],
    name: str = "List"
):
    """
    Assert list contains all expected items (order doesn't matter).

    Args:
        actual: Actual list
        expected_items: Expected items (must all be present)
        name: Name for error message
    """
    for item in expected_items:
        assert item in actual, \
            f"{name} missing expected item: {item}"


# ============================================================================
# Response Validators
# ============================================================================

class APIResponseValidator:
    """Validates API response structure and content."""

    @staticmethod
    def validate_chat_response(response_data: Dict[str, Any]):
        """
        Validate chat API response structure.

        Expected structure:
        {
            "response": str,
            "augmentation": {
                "domain_facts": [...],
                "memories_retrieved": [...],
                ...
            },
            "memories_created": [...],
            "conflicts_detected": [...],
            ...
        }
        """
        # Required top-level keys
        required_keys = ["response", "augmentation", "memories_created"]
        for key in required_keys:
            assert key in response_data, \
                f"Chat response missing required key: '{key}'"

        # Validate augmentation structure
        augmentation = response_data["augmentation"]
        assert "domain_facts" in augmentation
        assert "memories_retrieved" in augmentation

        assert isinstance(response_data["response"], str)
        assert isinstance(response_data["memories_created"], list)

    @staticmethod
    def validate_memory_structure(memory: Dict[str, Any]):
        """
        Validate semantic memory structure.

        Expected fields:
        - memory_id
        - user_id
        - subject_entity_id
        - predicate
        - object_value
        - confidence
        - status
        ...
        """
        required_fields = [
            "memory_id", "user_id", "subject_entity_id",
            "predicate", "object_value", "confidence", "status"
        ]

        for field in required_fields:
            assert field in memory, \
                f"Memory missing required field: '{field}'"

        # Validate confidence
        assert_confidence_in_range(memory["confidence"])

        # Validate status
        valid_statuses = ["active", "aging", "superseded", "invalidated"]
        assert memory["status"] in valid_statuses, \
            f"Invalid memory status: '{memory['status']}'"

    @staticmethod
    def validate_conflict_structure(conflict: Dict[str, Any]):
        """
        Validate conflict structure.

        Expected fields:
        - conflict_id
        - conflict_type
        - conflict_data
        - resolution_strategy
        """
        required_fields = ["conflict_type", "conflict_data", "resolution_strategy"]

        for field in required_fields:
            assert field in conflict, \
                f"Conflict missing required field: '{field}'"

        # Validate conflict type
        valid_types = ["memory_vs_memory", "memory_vs_db", "temporal"]
        assert conflict["conflict_type"] in valid_types, \
            f"Invalid conflict type: '{conflict['conflict_type']}'"


# ============================================================================
# Entity Validators
# ============================================================================

def validate_entity_mention(mention: Any):
    """
    Validate entity mention structure.

    Args:
        mention: EntityMention object or dict
    """
    if isinstance(mention, dict):
        required_fields = ["text", "position", "is_pronoun"]
        for field in required_fields:
            assert field in mention, \
                f"EntityMention missing field: '{field}'"
    else:
        # Object validation
        assert hasattr(mention, "text")
        assert hasattr(mention, "position")
        assert hasattr(mention, "is_pronoun")
        assert isinstance(mention.text, str)
        assert isinstance(mention.position, int)
        assert isinstance(mention.is_pronoun, bool)


def validate_resolution_result(result: Any):
    """
    Validate entity resolution result structure.

    Args:
        result: ResolutionResult object or dict
    """
    if isinstance(result, dict):
        required_fields = ["entity_id", "confidence", "method"]
        for field in required_fields:
            assert field in result, \
                f"ResolutionResult missing field: '{field}'"

        if result.get("is_successful"):
            assert result["entity_id"] is not None
            assert_confidence_in_range(result["confidence"])
    else:
        # Object validation
        assert hasattr(result, "entity_id")
        assert hasattr(result, "confidence")
        assert hasattr(result, "method")

        if result.is_successful:
            assert result.entity_id is not None
            assert_confidence_in_range(result.confidence)


# ============================================================================
# Test Data Validators
# ============================================================================

def validate_embedding(embedding: Any, expected_dimension: int = 1536):
    """
    Validate embedding vector.

    Args:
        embedding: Numpy array or list
        expected_dimension: Expected dimension (default: 1536 for OpenAI)
    """
    import numpy as np

    if isinstance(embedding, list):
        embedding = np.array(embedding)

    assert isinstance(embedding, np.ndarray), \
        "Embedding must be numpy array"

    assert embedding.shape == (expected_dimension,), \
        f"Embedding dimension mismatch: {embedding.shape} != ({expected_dimension},)"

    # Check if normalized (unit vector)
    norm = np.linalg.norm(embedding)
    assert abs(norm - 1.0) < 0.01, \
        f"Embedding not normalized: norm={norm} (expected ~1.0)"


def validate_confidence_factors(factors: Dict[str, float]):
    """
    Validate confidence factors structure and values.

    Expected keys: base, reinforcement, recency, source

    Args:
        factors: Confidence factors dictionary
    """
    # Should have at least base
    assert "base" in factors, "Confidence factors missing 'base'"

    # All values should be floats in valid range
    for key, value in factors.items():
        assert isinstance(value, (int, float)), \
            f"Confidence factor '{key}' must be numeric, got {type(value)}"
        # Allow negative for decay
        assert -1.0 <= value <= 1.0, \
            f"Confidence factor '{key}' out of range: {value}"


# ============================================================================
# Time Helpers
# ============================================================================

class TimeHelper:
    """Helper for time-related test operations."""

    @staticmethod
    def days_ago(days: int) -> datetime:
        """Get datetime N days ago."""
        from datetime import timedelta
        return datetime.utcnow() - timedelta(days=days)

    @staticmethod
    def hours_ago(hours: int) -> datetime:
        """Get datetime N hours ago."""
        from datetime import timedelta
        return datetime.utcnow() - timedelta(hours=hours)

    @staticmethod
    def is_recent(timestamp: datetime, max_age_seconds: int = 60) -> bool:
        """Check if timestamp is recent (within last N seconds)."""
        age_seconds = (datetime.utcnow() - timestamp).total_seconds()
        return age_seconds <= max_age_seconds


# ============================================================================
# String Helpers
# ============================================================================

def contains_any(text: str, phrases: List[str], case_insensitive: bool = True) -> bool:
    """
    Check if text contains any of the phrases.

    Args:
        text: Text to search
        phrases: Phrases to look for
        case_insensitive: Whether to ignore case (default: True)

    Returns:
        True if any phrase found, False otherwise
    """
    if case_insensitive:
        text = text.lower()
        phrases = [p.lower() for p in phrases]

    return any(phrase in text for phrase in phrases)


def contains_all(text: str, phrases: List[str], case_insensitive: bool = True) -> bool:
    """
    Check if text contains all of the phrases.

    Args:
        text: Text to search
        phrases: Phrases to look for
        case_insensitive: Whether to ignore case (default: True)

    Returns:
        True if all phrases found, False otherwise
    """
    if case_insensitive:
        text = text.lower()
        phrases = [p.lower() for p in phrases]

    return all(phrase in text for phrase in phrases)


# ============================================================================
# Comparison Helpers
# ============================================================================

def approx_equal(a: float, b: float, tolerance: float = 1e-6) -> bool:
    """
    Check if two floats are approximately equal.

    Args:
        a: First value
        b: Second value
        tolerance: Tolerance for comparison

    Returns:
        True if values are within tolerance
    """
    return abs(a - b) < tolerance


def lists_equal_unordered(list1: List[Any], list2: List[Any]) -> bool:
    """
    Check if two lists have same elements (ignoring order).

    Args:
        list1: First list
        list2: Second list

    Returns:
        True if lists have same elements
    """
    return sorted(list1) == sorted(list2)
