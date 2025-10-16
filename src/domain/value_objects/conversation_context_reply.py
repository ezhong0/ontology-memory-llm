"""Conversation context for LLM reply generation.

Separate from the existing ConversationContext (used for entity resolution).
This context is specifically for building LLM prompts from domain facts and memories.
"""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.value_objects.domain_fact import DomainFact


@dataclass(frozen=True)
class RetrievedMemory:
    """Retrieved memory for reply generation.

    Simplified view of memory for prompt construction.
    """

    memory_id: int
    memory_type: str  # episodic, semantic, summary
    content: str
    relevance_score: float
    confidence: float


@dataclass(frozen=True)
class RecentChatEvent:
    """Recent chat event for conversation continuity."""

    role: str  # user, assistant, system
    content: str


@dataclass(frozen=True)
class ReplyContext:
    """Immutable context for LLM reply generation.

    Philosophy: Explicit is better than implicit.
    All inputs to LLM generation are visible in one place.

    Design: This context is passed to LLMReplyGenerator to build
    the system prompt that includes DB facts (authoritative) and
    memories (contextual).
    """

    query: str
    """User's original query"""

    domain_facts: list[DomainFact]
    """Domain facts retrieved from database (authoritative truth)"""

    retrieved_memories: list[RetrievedMemory]
    """Memories retrieved via semantic search (contextual truth)"""

    recent_chat_events: list[RecentChatEvent]
    """Last few messages for conversation continuity"""

    user_id: str
    """User identifier"""

    session_id: UUID
    """Session identifier"""

    def to_system_prompt(self) -> str:
        """Build system prompt from context.

        Philosophy: Prompt structure matches vision principles.
        DB facts first (authoritative), then memories (contextual).

        Structure:
            1. Role and capabilities
            2. Database facts (correspondence truth)
            3. Retrieved memories (contextual truth)
            4. Recent conversation (continuity)
            5. Response guidelines

        Returns:
            Complete system prompt for LLM
        """
        sections = []

        # Section 1: Role and capabilities
        sections.append(
            "You are a knowledgeable business assistant with access to:\n"
            "1. Authoritative database facts (current state of orders, invoices, customers)\n"
            "2. Learned memories (preferences, patterns, past interactions)\n\n"
            "Always prefer database facts for current state, and use memories for context and preferences.\n\n"
            "CRITICAL - Epistemic Humility:\n"
            "- If NO data is provided (no database facts AND no memories), you MUST acknowledge "
            "the information gap explicitly\n"
            "- DO NOT fabricate plausible-sounding information\n"
            "- DO NOT use generic industry defaults (like 'typical NET30 terms')\n"
            "- Instead, say: 'I don't have information about [entity]' or 'No records found'\n"
            "- Suggest checking source systems or asking the user for clarification"
        )
        sections.append("")

        # Section 2: Domain facts (authoritative)
        if self.domain_facts:
            sections.append("=== DATABASE FACTS (Authoritative) ===")
            for fact in self.domain_facts:
                sections.append(fact.to_prompt_fragment())
            sections.append("")
        else:
            sections.append("=== DATABASE FACTS (Authoritative) ===")
            sections.append("NO DATABASE FACTS FOUND - No records in domain database for this query")
            sections.append("")

        # Section 3: Retrieved memories (contextual)
        if self.retrieved_memories:
            sections.append("=== RETRIEVED MEMORIES (Contextual) ===")
            for mem in self.retrieved_memories:
                sections.append(
                    f"[{mem.memory_type}] (relevance: {mem.relevance_score:.2f}, "
                    f"confidence: {mem.confidence:.2f})\n"
                    f"- {mem.content}"
                )
            sections.append("")
        else:
            sections.append("=== RETRIEVED MEMORIES (Contextual) ===")
            sections.append("NO MEMORIES FOUND - No relevant memories from past conversations")
            sections.append("")

        # Section 4: Conversation continuity
        if self.recent_chat_events:
            sections.append("=== RECENT CONVERSATION ===")
            for event in self.recent_chat_events[-3:]:  # Last 3 turns
                sections.append(f"{event.role}: {event.content}")
            sections.append("")

        # Section 5: Response guidelines
        sections.append(
            "=== RESPONSE GUIDELINES ===\n"
            "- Be concise and direct (2-3 sentences preferred)\n"
            "- Cite sources when relevant (e.g., 'According to Invoice INV-1009...')\n"
            "- If uncertain or data is old, acknowledge it\n"
            "- If database and memory conflict, prefer database but mention the discrepancy\n"
            "- Use domain facts to answer current state, memories for preferences/context\n"
            "- Do not make up information - only use the facts and memories provided\n\n"
            "EMAIL FORMATTING:\n"
            "- When drafting emails, use proper structure with line breaks\n"
            "- Include Subject line, greeting, body paragraphs, and signature\n"
            "- Use \\n\\n for paragraph breaks to improve readability\n"
            "- Keep professional tone but friendly"
        )

        return "\n".join(sections)

    def to_debug_summary(self) -> dict[str, Any]:
        """Create debug summary for logging.

        Returns:
            Dictionary with context metadata
        """
        return {
            "user_id": self.user_id,
            "session_id": str(self.session_id),
            "query_length": len(self.query),
            "domain_facts_count": len(self.domain_facts),
            "memories_count": len(self.retrieved_memories),
            "recent_events_count": len(self.recent_chat_events),
            "has_db_facts": len(self.domain_facts) > 0,
            "has_memories": len(self.retrieved_memories) > 0,
        }
