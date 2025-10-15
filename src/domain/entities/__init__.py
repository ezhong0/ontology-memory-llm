"""Domain entities.

Core business entities with identity and lifecycle.
"""
from src.domain.entities.canonical_entity import CanonicalEntity
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.entity_alias import EntityAlias

__all__ = [
    "CanonicalEntity",
    "EntityAlias",
    "ChatMessage",
]
