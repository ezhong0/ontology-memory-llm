"""Conversation context for LLM reply generation.

Separate from the existing ConversationContext (used for entity resolution).
This context is specifically for building LLM prompts from domain facts and memories.
"""

from dataclasses import dataclass, field
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
    last_validated_at: Any | None = None  # datetime or None
    status: str = "active"  # active, aging, superseded, invalidated


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

    pii_detected: bool = False
    """Whether PII was detected and redacted in the current message (Phase 3.1)"""

    pii_types: list[str] | None = None
    """Types of PII detected (e.g., ['phone', 'email']) if pii_detected=True"""

    triggered_reminders: list[dict[str, Any]] = field(default_factory=list)
    """Phase 3.3: Proactive reminders triggered by domain facts (procedural memory)"""

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

        # Section 1.5: PII Detection Acknowledgment (Phase 3.1)
        if self.pii_detected:
            pii_types_str = ", ".join(self.pii_types) if self.pii_types else "sensitive information"
            sections.append("⚠️  PRIVACY NOTICE - PII DETECTED AND REDACTED:")
            sections.append(
                f"The user's message contained personally identifiable information ({pii_types_str}) "
                "which has been automatically redacted for privacy protection. "
                "You MUST acknowledge this redaction in your response with transparency. "
                "Use phrases like 'I've redacted the sensitive information', "
                "'For privacy, I've masked the [type]', or 'Your [type] has been protected'. "
                "This demonstrates epistemic humility and security practices."
            )
            sections.append("")

        # Section 1.7: Proactive Reminders (Phase 3.3 - Procedural Memory)
        if self.triggered_reminders:
            sections.append("⚠️  PROACTIVE REMINDERS - ACTION REQUIRED:")
            sections.append(
                "The following reminders have been triggered based on your policies and current data. "
                "You MUST mention these proactively in your response to demonstrate awareness and helpfulness:"
            )
            sections.append("")
            for reminder in self.triggered_reminders:
                reminder_type = reminder.get("type", "unknown")
                if reminder_type == "invoice_due_reminder":
                    invoice_num = reminder.get("invoice_number", "unknown")
                    days_until = reminder.get("days_until_due", 0)
                    sections.append(
                        f"📌 REMINDER: Invoice {invoice_num} is due in {days_until} days and still open. "
                        f"This triggers your reminder policy (threshold: {reminder.get('threshold_days')} days before due)."
                    )
                else:
                    sections.append(f"📌 REMINDER: {reminder.get('message', 'Unknown reminder')}")
            sections.append("")
            sections.append(
                "Include these reminders naturally in your response. For example: "
                "'I notice Invoice INV-3001 is due in 2 days and still open' or "
                "'By the way, INV-3001 is approaching its due date (2 days)'"
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

            # Check for aged memories requiring validation
            aged_memories = []
            for mem in self.retrieved_memories:
                memory_line = (
                    f"[{mem.memory_type}] (relevance: {mem.relevance_score:.2f}, "
                    f"confidence: {mem.confidence:.2f}"
                )

                # Add status and validation info if memory is aging
                if mem.status == "aging" and mem.last_validated_at:
                    from datetime import datetime, timezone
                    days_since_validation = (
                        datetime.now(timezone.utc) - mem.last_validated_at
                    ).days
                    memory_line += f", status: AGING - last validated {days_since_validation} days ago on {mem.last_validated_at.strftime('%Y-%m-%d')}"
                    aged_memories.append(mem)

                memory_line += f")\n- {mem.content}"
                sections.append(memory_line)

            # Add validation reminder if aged memories found
            if aged_memories:
                sections.append("")
                sections.append("⚠️  VALIDATION REQUIRED:")
                sections.append(
                    "Some memories are old and marked as AGING. You MUST ask the user to confirm "
                    "whether these memories are still accurate before using them in your response. "
                    "Include phrases like 'Is this still accurate?', 'Can you confirm this is still correct?', "
                    "'Is Friday still your preferred day?', etc. Mention the date of last validation "
                    "to show transparency (epistemic humility)."
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
            "=== RESPONSE GUIDELINES ===\n\n"
            "REASONING PROCESS (apply before responding):\n"
            "1. Analyze the information: What facts and memories are available?\n"
            "2. Notice patterns: Are there conflicts? Superseded memories? Recent changes? Uncertainty?\n"
            "3. Make decisions: Which source is authoritative? What confidence level?\n"
            "4. Explain your reasoning: Share relevant observations transparently\n\n"
            "RESPONSE STYLE:\n"
            "- Be concise and direct (2-3 sentences preferred)\n"
            "- Cite sources when relevant (e.g., 'According to Invoice INV-1009...', 'Based on our records from...')\n"
            "- Show your reasoning when making decisions (e.g., 'Previously it was X, but recently updated to Y', "
            "'I see conflicting information - trusting the database which shows...', 'This memory is 90 days old, "
            "so I should confirm...')\n"
            "- If uncertain or data is old, acknowledge it explicitly\n"
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
