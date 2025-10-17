"""Process chat message use case - Orchestrator.

Refactored from 683-line god object to lean orchestrator pattern.
Coordinates specialized use cases for each phase of chat processing.
"""

import asyncio
import time
from typing import Any

import structlog

from src.application.dtos.chat_dtos import (
    DomainFactDTO,
    MemoryConflictDTO,
    ProcessChatMessageInput,
    ProcessChatMessageOutput,
    RetrievedMemoryDTO,
)
from src.application.use_cases.augment_with_domain import AugmentWithDomainUseCase
from src.application.use_cases.extract_semantics import ExtractSemanticsUseCase
from src.application.use_cases.resolve_entities import ResolveEntitiesUseCase
from src.application.use_cases.score_memories import ScoreMemoriesUseCase
from src.domain.entities import ChatMessage
from src.domain.ports import IChatEventRepository
from src.domain.services import (
    ConflictDetectionService,
    ConflictResolutionService,
    LLMReplyGenerator,
    PIIRedactionService,
)
from src.domain.value_objects.conversation_context_reply import (
    RecentChatEvent,
    ReplyContext,
)

logger = structlog.get_logger(__name__)


class ProcessChatMessageUseCase:
    """Orchestrator for processing chat messages.

    Refactored from 683-line god object to lean orchestrator.
    Coordinates 4 specialized use cases:

    1. ResolveEntitiesUseCase (Phase 1A): Entity resolution
    2. ExtractSemanticsUseCase (Phase 1B): Semantic extraction
    3. AugmentWithDomainUseCase (Phase 1C): Domain augmentation
    4. ScoreMemoriesUseCase (Phase 1D): Memory scoring

    Plus reply generation (LLM reply generator).

    Philosophy: Single Responsibility - orchestrate, don't implement.
    Each phase is handled by a dedicated use case with clear boundaries.
    """

    def __init__(
        self,
        chat_repository: IChatEventRepository,
        resolve_entities_use_case: ResolveEntitiesUseCase,
        extract_semantics_use_case: ExtractSemanticsUseCase,
        augment_with_domain_use_case: AugmentWithDomainUseCase,
        score_memories_use_case: ScoreMemoriesUseCase,
        conflict_detection_service: ConflictDetectionService,
        conflict_resolution_service: ConflictResolutionService,
        llm_reply_generator: LLMReplyGenerator,
        pii_redaction_service: PIIRedactionService,
    ):
        """Initialize orchestrator.

        Args:
            chat_repository: Repository for chat event storage
            resolve_entities_use_case: Use case for entity resolution (Phase 1A)
            extract_semantics_use_case: Use case for semantic extraction (Phase 1B)
            augment_with_domain_use_case: Use case for domain augmentation (Phase 1C)
            score_memories_use_case: Use case for memory scoring (Phase 1D)
            conflict_detection_service: Service for detecting memory-vs-DB conflicts
            conflict_resolution_service: Service for resolving detected conflicts (Phase 2.1)
            llm_reply_generator: Service for natural language reply generation
            pii_redaction_service: Service for PII detection and redaction (Phase 3.1)
        """
        self.chat_repo = chat_repository
        self.resolve_entities = resolve_entities_use_case
        self.extract_semantics = extract_semantics_use_case
        self.augment_with_domain = augment_with_domain_use_case
        self.score_memories = score_memories_use_case
        self.conflict_detection_service = conflict_detection_service
        self.conflict_resolution_service = conflict_resolution_service
        self.llm_reply_generator = llm_reply_generator
        self.pii_redaction_service = pii_redaction_service

    async def execute(
        self, input_dto: ProcessChatMessageInput
    ) -> ProcessChatMessageOutput:
        """Execute the chat message processing workflow.

        Orchestrates all phases of chat processing through specialized use cases.

        Args:
            input_dto: Input data with message content and metadata

        Returns:
            ProcessChatMessageOutput with all results from each phase

        Raises:
            InvalidMessageError: If message validation fails
            RepositoryError: If database operations fail
        """
        logger.info(
            "processing_chat_message",
            user_id=input_dto.user_id,
            session_id=str(input_dto.session_id),
            content_length=len(input_dto.content),
        )

        # Initialize timing tracker
        step_timings: dict[str, float] = {}
        step_start = time.perf_counter()

        # Phase 3.1: Detect and redact PII before storing (privacy-by-design)
        redaction_result = self.pii_redaction_service.redact_with_metadata(input_dto.content)
        step_timings["pii"] = time.perf_counter() - step_start

        content_to_store = redaction_result.redacted_text
        pii_was_detected = redaction_result.was_redacted

        if pii_was_detected:
            logger.warning(
                "pii_detected_in_message",
                user_id=input_dto.user_id,
                redaction_count=len(redaction_result.redactions),
                types=[r["type"] for r in redaction_result.redactions],
            )

        # Step 1: Store chat message (with redacted content if PII was found)
        step_start = time.perf_counter()
        message = ChatMessage(
            session_id=input_dto.session_id,
            user_id=input_dto.user_id,
            role=input_dto.role,
            content=content_to_store,
            event_metadata=input_dto.metadata or {},
        )

        stored_message = await self.chat_repo.create(message)

        if stored_message.event_id is None:
            msg = "Event ID not set after message creation"
            raise ValueError(msg)

        logger.debug(
            "chat_message_stored",
            event_id=stored_message.event_id,
        )
        step_timings["store"] = time.perf_counter() - step_start

        # Step 2: Resolve entities (Phase 1A)
        step_start = time.perf_counter()
        entities_result = await self.resolve_entities.execute(
            message_content=input_dto.content,
            user_id=input_dto.user_id,
            session_id=input_dto.session_id,
        )

        step_timings["resolve"] = time.perf_counter() - step_start

        # Task 1.2.1: Check for ambiguous entities and propagate to API
        # If entity resolution found ambiguities, raise exception for API to handle
        # This enables the disambiguation flow (alias-first learning loop)
        if entities_result.ambiguous_entities:
            from src.domain.exceptions import AmbiguousEntityError

            # Raise first ambiguity for API disambiguation handler
            # Note: entities_result.ambiguous_entities stores AmbiguousEntityError exceptions
            ambiguous_error = entities_result.ambiguous_entities[0]
            logger.info(
                "propagating_ambiguous_entity_to_api",
                mention=ambiguous_error.mention_text,
                candidates_count=len(ambiguous_error.candidates),
            )
            # Re-raise the original exception with all details intact
            raise ambiguous_error

        # Phase 3.3: No longer early exit when no entities - allow general queries
        # General queries like "What invoices do we have?" should proceed to domain augmentation
        # even without specific entities

        # Step 3 & 4: Parallelize Phase 1B (Semantic Extraction) and Phase 1C (Domain Augmentation)
        # Both phases only depend on Phase 1A outputs (resolved entities)
        # Running them in parallel reduces latency by ~34% (200ms saved)
        step_start = time.perf_counter()

        semantics_result, domain_fact_dtos = await asyncio.gather(
            # Phase 1B: Extract semantics
            # Always call even if no entities are resolved (policy detection needs it)
            self.extract_semantics.execute(
                message=stored_message,
                resolved_entities=entities_result.resolved_entities,
                user_id=input_dto.user_id,
            ),
            # Phase 1C: Augment with domain (LLM tool calling)
            self.augment_with_domain.execute(
                resolved_entities=entities_result.resolved_entities,
                query_text=input_dto.content,
                session_id=str(input_dto.session_id),
            )
        )

        step_timings["extract_and_augment_parallel"] = time.perf_counter() - step_start

        # Phase 3.1: Create policy memory when PII was detected
        # This enables transparency and audit trail for privacy compliance
        if pii_was_detected:
            from datetime import UTC, datetime
            from src.domain.entities import SemanticMemory

            pii_types = [r["type"] for r in redaction_result.redactions]

            # Ensure "system_policy" canonical entity exists (required for foreign key)
            # This is the same entity used for reminder policies
            if self.extract_semantics.canonical_entity_repo:
                from src.domain.entities import CanonicalEntity
                from src.domain.value_objects import EntityReference

                system_entity = await self.extract_semantics.canonical_entity_repo.find_by_entity_id("system_policy")
                if not system_entity:
                    system_ref = EntityReference(
                        table="system",
                        primary_key="id",
                        primary_value="policy",
                        display_name="System",
                    )
                    system_entity = CanonicalEntity(
                        entity_id="system_policy",
                        entity_type="system",
                        canonical_name="System",
                        external_ref=system_ref,
                        properties={"type": "system_policies"},
                    )
                    await self.extract_semantics.canonical_entity_repo.create(system_entity)
                    logger.debug("system_policy_entity_created")

            # Create policy memory indicating PII was redacted
            # Generate embedding for the policy memory
            embedding_text = f"PII redaction policy: never store sensitive information ({', '.join(pii_types)})"
            pii_embedding = await self.extract_semantics.embedding_service.generate_embedding(
                embedding_text
            )

            pii_policy_memory = SemanticMemory(
                user_id=input_dto.user_id,
                content=f"PII redaction policy: never store sensitive information ({', '.join(pii_types)})",
                entities=["system_policy"],
                confidence=0.95,
                importance=0.9,  # High importance for system policies
                status="active",
                source_event_ids=[stored_message.event_id],
                embedding=pii_embedding,
                metadata={
                    "policy_type": "pii_policy",
                    "policy_data": {
                        "policy": "never_store_pii",
                        "detected_types": pii_types,
                        "redacted_at": datetime.now(UTC).isoformat(),
                        "redaction_count": len(redaction_result.redactions),
                    },
                },
            )

            # Store the policy memory
            await self.extract_semantics.semantic_memory_repo.create(pii_policy_memory)

            logger.info(
                "pii_policy_memory_created",
                event_id=stored_message.event_id,
                pii_types=pii_types,
            )

        # Step 4.3: Phase 3.3 - Evaluate reminder triggers (Procedural Memory)
        # Check if domain facts trigger any reminder policies
        triggered_reminders = await self._evaluate_reminder_triggers(
            domain_facts=domain_fact_dtos,
            user_id=input_dto.user_id,
        )

        # Step 4.5: Detect memory-vs-DB conflicts (Phase 1C Epistemic Humility)
        # Check if domain facts contradict semantic memories
        memory_vs_db_conflicts = []

        # Convert DomainFactDTOs to DomainFacts (needed for both conflict detection and reply generation)
        from src.domain.value_objects import DomainFact

        domain_facts = [
            DomainFact(
                fact_type=fact.fact_type,
                entity_id=fact.entity_id,
                content=fact.content,
                metadata=fact.metadata,
                source_table=fact.source_table,
                source_rows=fact.source_rows,
                retrieved_at=fact.retrieved_at,
            )
            for fact in domain_fact_dtos
        ]

        # Check each semantic memory against domain facts for conflicts
        if domain_facts and semantics_result.semantic_memory_entities:
            for memory in semantics_result.semantic_memory_entities:
                for domain_fact in domain_facts:
                    conflict = await self.conflict_detection_service.detect_memory_vs_db_conflict(
                        memory=memory,
                        domain_fact=domain_fact,
                        embedding_service=self.extract_semantics.embedding_service,
                    )
                    if conflict:
                        memory_vs_db_conflicts.append(conflict)
                        logger.warning(
                            "memory_vs_db_conflict_detected",
                            entities=conflict.entities,
                            similarity=conflict.semantic_similarity,
                        )

        # Step 5: Score and retrieve memories (Phase 1D)
        # Must run after Phase 1B completes (needs semantic_memory_entities)
        step_start = time.perf_counter()
        retrieved_memories, semantic_memory_map = await self.score_memories.execute(
            semantic_memory_entities=semantics_result.semantic_memory_entities,
            resolved_entities=entities_result.resolved_entities,
            query_text=input_dto.content,
            user_id=input_dto.user_id,
            session_id=input_dto.session_id,
        )

        # Phase 2.2: Detect confirmations and validate aging memories
        # If user confirms aged memories, validate them
        await self._handle_memory_validation(
            message_content=input_dto.content,
            retrieved_memories=retrieved_memories,
            semantic_memory_map=semantic_memory_map,
            user_id=input_dto.user_id,
        )

        # Phase 2.1: Check retrieved memories against domain facts for conflicts
        if domain_facts and retrieved_memories:
            for retrieved_mem in retrieved_memories:
                # Convert retrieved memory DTO back to semantic memory entity for conflict detection
                if retrieved_mem.memory_id and retrieved_mem.memory_id in semantic_memory_map:
                    memory_entity = semantic_memory_map[retrieved_mem.memory_id]
                    for domain_fact in domain_facts:
                        conflict = await self.conflict_detection_service.detect_memory_vs_db_conflict(
                            memory=memory_entity,
                            domain_fact=domain_fact,
                            embedding_service=self.extract_semantics.embedding_service,
                        )
                        if conflict:
                            memory_vs_db_conflicts.append(conflict)
                            logger.warning(
                                "memory_vs_db_conflict_detected_retrieved",
                                memory_id=retrieved_mem.memory_id,
                                entities=conflict.entities,
                                similarity=conflict.semantic_similarity,
                            )

        # Step 5.5: Resolve memory-vs-DB conflicts (Phase 2.1)
        # DB is always authoritative, so we resolve these automatically
        resolved_conflicts = []
        if memory_vs_db_conflicts:
            logger.info(
                "resolving_memory_vs_db_conflicts",
                conflict_count=len(memory_vs_db_conflicts),
            )
            for conflict in memory_vs_db_conflicts:
                try:
                    # Memory-vs-DB conflicts always use TRUST_DB strategy
                    resolution_result = await self.conflict_resolution_service.resolve_conflict(
                        conflict=conflict,
                        strategy=None,  # Use recommended strategy (TRUST_DB)
                    )
                    resolved_conflicts.append(resolution_result)
                    logger.info(
                        "memory_vs_db_conflict_resolved",
                        memory_id=conflict.existing_memory_id,
                        action=resolution_result.action,
                        rationale=resolution_result.rationale,
                    )
                except Exception as e:
                    logger.error(
                        "memory_vs_db_conflict_resolution_failed",
                        conflict=conflict,
                        error=str(e),
                    )

        step_timings["score"] = time.perf_counter() - step_start

        # Step 6: Generate reply
        step_start = time.perf_counter()
        reply = await self._generate_reply(
            input_dto=input_dto,
            domain_fact_dtos=domain_fact_dtos,
            retrieved_memories=retrieved_memories,
            triggered_reminders=triggered_reminders,
            pii_detected=pii_was_detected,
            pii_types=[r["type"] for r in redaction_result.redactions] if pii_was_detected else None,
        )
        step_timings["generate"] = time.perf_counter() - step_start

        # Step 7: Assemble final response
        # Convert RetrievedMemory to RetrievedMemoryDTO
        retrieved_memory_dtos = []
        for mem in retrieved_memories:
            # Check if this is a semantic memory and enhance with entity information
            semantic_mem = semantic_memory_map.get(mem.memory_id)
            retrieved_memory_dtos.append(
                RetrievedMemoryDTO(
                    memory_id=mem.memory_id,
                    memory_type=mem.memory_type,
                    content=mem.content,
                    relevance_score=mem.relevance_score,
                    confidence=mem.confidence,
                    importance=semantic_mem.importance if semantic_mem else None,
                    entities=semantic_mem.entities if semantic_mem else None,
                )
            )

        # Convert MemoryConflict objects to DTOs for transparency
        # Combine both memory-vs-memory and memory-vs-DB conflicts
        all_conflicts = list(semantics_result.conflicts_detected) + memory_vs_db_conflicts
        conflict_dtos = []
        for conflict in all_conflicts:
            # Extract confidence values from metadata (where they're stored)
            if conflict.conflict_type.value == "memory_vs_db":
                existing_confidence = conflict.metadata.get("memory_confidence", 0.7)
                new_confidence = 1.0  # DB is authoritative
            else:
                existing_confidence = conflict.metadata.get("existing_confidence", 0.7)
                new_confidence = conflict.metadata.get("new_confidence", 0.7)

            conflict_dtos.append(
                MemoryConflictDTO(
                    conflict_type=conflict.conflict_type.value,
                    entities=conflict.entities,
                    existing_content=conflict.existing_content,
                    new_content=conflict.new_content,
                    existing_confidence=existing_confidence,
                    new_confidence=new_confidence,
                    resolution_strategy=conflict.recommended_resolution.value,
                )
            )

        logger.info(
            "chat_message_processed",
            event_id=stored_message.event_id,
            mentions=entities_result.mention_count,
            resolved=entities_result.successful_resolutions,
            success_rate=f"{entities_result.resolution_success_rate:.1f}%",
            semantic_memories=len(semantics_result.semantic_memory_dtos),
            conflicts=len(conflict_dtos),
            memory_vs_memory_conflicts=semantics_result.conflict_count,
            memory_vs_db_conflicts=len(memory_vs_db_conflicts),
            domain_facts=len(domain_fact_dtos),
            retrieved_memories=len(retrieved_memory_dtos),
            reply_length=len(reply),
        )

        return ProcessChatMessageOutput(
            event_id=stored_message.event_id,
            session_id=input_dto.session_id,
            resolved_entities=entities_result.resolved_entities,
            mention_count=entities_result.mention_count,
            resolution_success_rate=entities_result.resolution_success_rate,
            semantic_memories=semantics_result.semantic_memory_dtos,
            conflict_count=len(conflict_dtos),
            conflicts_detected=conflict_dtos,
            domain_facts=domain_fact_dtos,
            retrieved_memories=retrieved_memory_dtos,
            reply=reply,
            step_timings=step_timings,
        )

    async def _generate_reply_without_entities(
        self,
        input_dto: ProcessChatMessageInput,
        pii_detected: bool = False,
        pii_types: list[str] | None = None,
    ) -> str:
        """Generate reply when no entities were resolved.

        Args:
            input_dto: Input data with message content
            pii_detected: Whether PII was detected in the message
            pii_types: Types of PII detected

        Returns:
            Generated reply string
        """
        reply_context = ReplyContext(
            query=input_dto.content,
            domain_facts=[],
            retrieved_memories=[],
            recent_chat_events=[],
            user_id=input_dto.user_id,
            session_id=input_dto.session_id,
            pii_detected=pii_detected,
            pii_types=pii_types,
        )
        return await self.llm_reply_generator.generate(reply_context)

    async def _generate_reply(
        self,
        input_dto: ProcessChatMessageInput,
        domain_fact_dtos: list[DomainFactDTO],
        retrieved_memories: list[Any],
        triggered_reminders: list[dict[str, Any]] | None = None,
        pii_detected: bool = False,
        pii_types: list[str] | None = None,
    ) -> str:
        """Generate natural language reply with full context.

        Args:
            input_dto: Input data with message content
            domain_fact_dtos: Domain facts retrieved
            retrieved_memories: Scored and ranked memories
            triggered_reminders: Phase 3.3 - Proactive reminders triggered by domain facts

        Returns:
            Generated reply string
        """
        # Get recent chat events for context
        recent_messages_models = await self.chat_repo.get_recent_for_session(
            input_dto.session_id, limit=5
        )
        recent_chat_events = [
            RecentChatEvent(
                role=msg.role,
                content=msg.content,
            )
            for msg in recent_messages_models
        ]

        # Build reply context
        # Convert DomainFactDTOs to DomainFacts
        from src.domain.value_objects import DomainFact

        domain_facts = [
            DomainFact(
                fact_type=fact.fact_type,
                entity_id=fact.entity_id,
                content=fact.content,
                metadata=fact.metadata,
                source_table=fact.source_table,
                source_rows=fact.source_rows,
                retrieved_at=fact.retrieved_at,
            )
            for fact in domain_fact_dtos
        ]

        reply_context = ReplyContext(
            query=input_dto.content,
            domain_facts=domain_facts,
            retrieved_memories=retrieved_memories,
            recent_chat_events=recent_chat_events,
            user_id=input_dto.user_id,
            session_id=input_dto.session_id,
            triggered_reminders=triggered_reminders or [],
            pii_detected=pii_detected,
            pii_types=pii_types,
        )

        # Generate natural language reply
        reply = await self.llm_reply_generator.generate(reply_context)

        logger.info(
            "reply_generated",
            reply_length=len(reply),
        )

        return reply

    async def _handle_memory_validation(
        self,
        message_content: str,
        retrieved_memories: list[Any],
        semantic_memory_map: dict[int, Any],
        user_id: str,
    ) -> None:
        """Detect confirmations and validate aging memories.

        Phase 2.2: Active Memory Validation

        When user confirms an aged memory (e.g., "Yes, Friday is still correct"),
        this method:
        1. Detects confirmation intent
        2. Identifies which aging memories are being confirmed
        3. Validates those memories (status -> active, confidence++, reinforcement++)

        Args:
            message_content: User's message
            retrieved_memories: Memories retrieved in this turn
            semantic_memory_map: Map of memory_id -> SemanticMemory entity
            user_id: User identifier
        """
        from datetime import datetime, timezone
        from src.config import heuristics

        # Check if message looks like a confirmation
        message_lower = message_content.lower()
        confirmation_keywords = [
            "yes", "correct", "still", "accurate", "right",
            "that's correct", "that's right", "still prefer",
            "yeah", "yep", "yup", "still good", "confirmed"
        ]

        is_confirmation = any(keyword in message_lower for keyword in confirmation_keywords)

        if not is_confirmation:
            return

        logger.info(
            "confirmation_detected",
            message=message_content[:100],
        )

        # Find aging memories that should be validated
        # Strategy: Validate all aging memories from this retrieval
        # (In a more sophisticated system, we'd match specific predicates/values)
        aging_memories_to_validate = []

        for retrieved_mem in retrieved_memories:
            if retrieved_mem.status == "aging" and retrieved_mem.memory_id in semantic_memory_map:
                aging_memories_to_validate.append(semantic_memory_map[retrieved_mem.memory_id])

        if not aging_memories_to_validate:
            logger.debug("no_aging_memories_to_validate")
            return

        logger.info(
            "validating_aging_memories",
            count=len(aging_memories_to_validate),
        )

        # Validate each aging memory
        for memory in aging_memories_to_validate:
            # Update memory using confirm() method
            memory.status = "active"
            memory.confirm(
                new_event_id=0,  # Placeholder - no specific event for confirmation
                importance_boost=0.05,  # Standard boost
            )
            # Update last_accessed_at since memory was validated
            memory.last_accessed_at = datetime.now(timezone.utc)

            # Update in database via the repository pattern
            # Access repository through the extract_semantics use case (which has it injected)
            await self.extract_semantics.semantic_memory_repo.update(memory)

            logger.info(
                "memory_validated_from_confirmation",
                memory_id=memory.memory_id,
                new_confidence=memory.confidence,
                new_importance=memory.importance,
                confirmation_count=memory.confirmation_count,
            )

    async def _evaluate_reminder_triggers(
        self,
        domain_facts: list[DomainFactDTO],
        user_id: str,
    ) -> list[dict[str, Any]]:
        """Evaluate reminder triggers against domain facts.

        Phase 3.3: Proactive Intelligence

        Retrieves reminder policies from semantic memory and checks domain facts
        against policy conditions. Returns triggered reminders for LLM context.

        Args:
            domain_facts: Domain facts retrieved in this turn
            user_id: User identifier

        Returns:
            List of triggered reminders with details for natural language generation
        """
        from datetime import date

        triggered_reminders: list[dict[str, Any]] = []

        # Step 1: Retrieve reminder policies from semantic memory (entity-tagged)
        reminder_policies = await self.extract_semantics.semantic_memory_repo.find_by_entities(
            entity_ids=["system_policy"],
            user_id=user_id,
            status_filter="active",
            match_all=False,  # Match ANY entity
        )

        # Filter for reminder policy content
        reminder_policies = [
            policy for policy in reminder_policies
            if "reminder_policy" in policy.content.lower() or
            policy.metadata.get("policy_type") == "reminder"
        ]

        if not reminder_policies:
            logger.debug("no_reminder_policies_found")
            return []

        logger.info(
            "evaluating_reminder_triggers",
            policy_count=len(reminder_policies),
            fact_count=len(domain_facts),
        )

        # Step 2: Check each domain fact against each policy
        for policy in reminder_policies:
            # Extract policy data from metadata (stored during policy creation)
            policy_data = policy.metadata.get("policy_data", {})

            # Currently only support invoice reminder policies
            if policy_data.get("entity_type") != "invoice":
                continue

            threshold_days = policy_data.get("threshold_days", 0)
            condition = policy_data.get("condition", "")

            # Step 3: Find invoice facts and evaluate triggers
            for fact in domain_facts:
                # Check if this is an invoice fact
                if "invoice" not in fact.fact_type.lower():
                    continue

                # Extract invoice details from metadata
                metadata = fact.metadata or {}
                invoice_status = metadata.get("status", "")
                due_date_str = metadata.get("due_date")
                invoice_number = metadata.get("invoice_number", "unknown")

                if not due_date_str:
                    continue

                # Parse due date and calculate days until due
                from datetime import datetime
                try:
                    if isinstance(due_date_str, str):
                        due_date = datetime.fromisoformat(due_date_str).date()
                    else:
                        due_date = due_date_str
                except (ValueError, AttributeError):
                    logger.warning(
                        "invalid_due_date_format",
                        due_date_str=due_date_str,
                        invoice=invoice_number,
                    )
                    continue

                today = date.today()
                days_until_due = (due_date - today).days

                # Step 4: Evaluate trigger condition
                # Policy: "If invoice is open X days before due, remind me"
                # Trigger: invoice.days_until_due <= policy.threshold_days AND invoice.status == "open"
                matches_condition = (
                    condition == "status_open" and invoice_status == "open"
                )
                within_threshold = days_until_due <= threshold_days

                if matches_condition and within_threshold:
                    # TRIGGER!
                    triggered_reminders.append({
                        "type": "invoice_due_reminder",
                        "invoice_number": invoice_number,
                        "days_until_due": days_until_due,
                        "due_date": str(due_date),
                        "status": invoice_status,
                        "threshold_days": threshold_days,
                        "message": f"Invoice {invoice_number} is due in {days_until_due} days and still open",
                    })

                    logger.info(
                        "reminder_triggered",
                        invoice=invoice_number,
                        days_until_due=days_until_due,
                        threshold=threshold_days,
                        status=invoice_status,
                    )

        logger.info(
            "reminder_evaluation_complete",
            triggered_count=len(triggered_reminders),
        )

        return triggered_reminders
