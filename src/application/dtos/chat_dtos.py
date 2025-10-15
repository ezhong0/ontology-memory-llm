"""DTOs for chat operations.

Data Transfer Objects for application layer.
"""
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID


@dataclass
class ResolvedEntityDTO:
    """DTO for resolved entity information.

    Attributes:
        entity_id: Canonical entity ID
        canonical_name: Display name
        entity_type: Type of entity (customer, order, etc.)
        mention_text: Original text that was resolved
        confidence: Resolution confidence [0.0, 1.0]
        method: Resolution method used (exact, alias, fuzzy, coreference)
    """

    entity_id: str
    canonical_name: str
    entity_type: str
    mention_text: str
    confidence: float
    method: str


@dataclass
class ProcessChatMessageInput:
    """Input DTO for processing a chat message.

    Attributes:
        user_id: User ID (from authentication)
        session_id: Conversation session ID
        content: Message content
        role: Message role (user | assistant | system)
        metadata: Optional metadata
    """

    user_id: str
    session_id: UUID
    content: str
    role: str = "user"
    metadata: Optional[dict[str, Any]] = None


@dataclass
class ProcessChatMessageOutput:
    """Output DTO for processed chat message.

    Attributes:
        event_id: Created chat event ID
        session_id: Conversation session ID
        resolved_entities: List of resolved entities from the message
        mention_count: Total number of mentions extracted
        resolution_success_rate: Percentage of mentions successfully resolved
    """

    event_id: int
    session_id: UUID
    resolved_entities: list[ResolvedEntityDTO]
    mention_count: int
    resolution_success_rate: float
