"""Extract semantics use case - Phase 1B extraction.

Extracts semantic extraction logic from ProcessChatMessageUseCase god object.
Handles triple extraction, conflict detection, and memory storage.
"""

from typing import Any

import structlog

from src.application.dtos.chat_dtos import (
    ResolvedEntityDTO,
    SemanticMemoryDTO,
)
from src.domain.entities import ChatMessage, SemanticMemory
from src.domain.ports import IEmbeddingService, ISemanticMemoryRepository
from src.domain.services import (
    ConflictDetectionService,
    ConflictResolutionService,
    MemoryValidationService,
    SemanticExtractionService,
)
from src.domain.value_objects import ConflictResolution, MemoryConflict, PredicateType, SemanticTriple

logger = structlog.get_logger(__name__)


class ExtractSemanticsResult:
    """Result of semantic extraction.

    Attributes:
        semantic_memory_dtos: List of semantic memory DTOs for API response
        semantic_memory_entities: List of full semantic memory entities for scoring
        conflict_count: Number of conflicts detected
        conflicts_detected: List of actual conflict objects for transparency
    """

    def __init__(
        self,
        semantic_memory_dtos: list[SemanticMemoryDTO],
        semantic_memory_entities: list[SemanticMemory],
        conflict_count: int,
        conflicts_detected: list[MemoryConflict] | None = None,
    ):
        self.semantic_memory_dtos = semantic_memory_dtos
        self.semantic_memory_entities = semantic_memory_entities
        self.conflict_count = conflict_count
        self.conflicts_detected = conflicts_detected or []


class ExtractSemanticsUseCase:
    """Use case for extracting semantic memories from chat messages.

    Extracted from ProcessChatMessageUseCase to follow Single Responsibility Principle.
    Handles Phase 1B: Semantic Extraction.

    Responsibilities:
    - Extract semantic triples using LLM
    - Detect conflicts with existing memories
    - Create or reinforce memories
    - Handle automatic conflict resolution
    """

    def __init__(
        self,
        semantic_extraction_service: SemanticExtractionService,
        memory_validation_service: MemoryValidationService,
        conflict_detection_service: ConflictDetectionService,
        conflict_resolution_service: ConflictResolutionService,
        semantic_memory_repository: ISemanticMemoryRepository,
        embedding_service: IEmbeddingService,
        canonical_entity_repository: Any = None,  # ICanonicalEntityRepository
    ):
        """Initialize use case.

        Args:
            semantic_extraction_service: Service for extracting semantic triples
            memory_validation_service: Service for memory reinforcement and decay
            conflict_detection_service: Service for detecting memory conflicts
            conflict_resolution_service: Service for resolving detected conflicts (Phase 2.1)
            semantic_memory_repository: Repository for semantic memory storage
            embedding_service: Service for generating embeddings
            canonical_entity_repository: Repository for canonical entities (optional, Phase 3.3)
        """
        self.semantic_extraction_service = semantic_extraction_service
        self.memory_validation_service = memory_validation_service
        self.conflict_detection_service = conflict_detection_service
        self.conflict_resolution_service = conflict_resolution_service
        self.semantic_memory_repo = semantic_memory_repository
        self.embedding_service = embedding_service
        self.canonical_entity_repo = canonical_entity_repository

    async def execute(
        self,
        message: ChatMessage,
        resolved_entities: list[ResolvedEntityDTO],
        user_id: str,
    ) -> ExtractSemanticsResult:
        """Extract semantic memories from message.

        Args:
            message: The stored chat message (must have event_id)
            resolved_entities: List of entities resolved from the message
            user_id: User identifier for memory ownership

        Returns:
            ExtractSemanticsResult with created/updated memories and conflict count
        """
        # Guard: message must have event_id (should be persisted before calling this)
        if message.event_id is None:
            msg = "Message must be persisted (have event_id) before semantic extraction"
            raise ValueError(msg)

        semantic_memory_dtos: list[SemanticMemoryDTO] = []
        semantic_memory_entities: list[SemanticMemory] = []
        conflict_count = 0
        conflicts_detected: list[MemoryConflict] = []

        # Phase 3.3: Check for policy statements (e.g., reminder policies)
        # Policy detection happens BEFORE entity check because policies are system-level
        # and don't require specific entities (subject_entity_id="system")
        policy_memory = await self._detect_and_create_policy(message, user_id)
        if policy_memory:
            logger.info("policy_detected_and_stored", policy_type="reminder")
            return ExtractSemanticsResult(
                semantic_memory_dtos=[self._memory_to_dto(policy_memory)],
                semantic_memory_entities=[policy_memory],
                conflict_count=0,
                conflicts_detected=[],
            )

        # Check for resolved entities (needed for semantic extraction)
        if not resolved_entities:
            logger.debug("no_resolved_entities_for_semantic_extraction")
            return ExtractSemanticsResult(
                semantic_memory_dtos=[],
                semantic_memory_entities=[],
                conflict_count=0,
                conflicts_detected=[],
            )

        # Note: We don't filter questions here. The LLM-based semantic extraction is smart enough to:
        # - Extract factual statements from preference statements: "I like chocolate"
        # - Extract factual statements from remember requests: "Can you remember I like butter?"
        # - NOT extract from pure information-seeking questions: "What invoices are outstanding?"
        # This aligns with the vision: "Memory is the transformation of experience into understanding."
        # The LLM's semantic understanding > brittle pattern matching.

        logger.info(
            "starting_semantic_extraction",
            event_id=message.event_id,
            entity_count=len(resolved_entities),
        )

        # Build entity_id -> canonical_name mapping for natural language embeddings
        entity_name_map = {
            e.entity_id: e.canonical_name
            for e in resolved_entities
        }

        # Step 1: Extract semantic triples
        triples = await self.semantic_extraction_service.extract_triples(
            message=message,
            resolved_entities=[
                {
                    "entity_id": e.entity_id,
                    "canonical_name": e.canonical_name,
                    "entity_type": e.entity_type,
                }
                for e in resolved_entities
            ],
        )

        logger.info(
            "semantic_triples_extracted",
            triple_count=len(triples),
        )

        # Step 2: Process each triple (conflict detection + storage)
        for triple in triples:
            try:
                # Check for conflicts with existing memories
                existing_memories = (
                    await self.semantic_memory_repo.find_by_subject_predicate(
                        subject_entity_id=triple.subject_entity_id,
                        predicate=triple.predicate,
                        user_id=user_id,
                        status_filter="active",
                    )
                )

                conflict = None
                if existing_memories:
                    # Check first memory for conflict
                    existing_memory = existing_memories[0]
                    conflict = self.conflict_detection_service.detect_conflict(
                        new_triple=triple,
                        existing_memory=existing_memory,
                    )

                    if conflict:
                        conflict_count += 1
                        conflicts_detected.append(conflict)  # Track for transparency
                        logger.warning(
                            "memory_conflict_detected",
                            conflict_type=conflict.conflict_type.value,
                            subject=triple.subject_entity_id,
                            predicate=triple.predicate,
                        )

                        # Phase 2.1: Use ConflictResolutionService for proper resolution
                        if conflict.is_resolvable_automatically:
                            resolution_result = await self.conflict_resolution_service.resolve_conflict(
                                conflict=conflict,
                                strategy=None,  # Use recommended strategy
                            )
                            logger.info(
                                "conflict_resolved",
                                action=resolution_result.action,
                                rationale=resolution_result.rationale,
                            )

                            # After resolution, create new memory if the new observation should persist
                            # (i.e., if it won or if we need both perspectives tracked)
                            # For supersede actions, we should create the new memory
                            # For invalidate actions (DB conflicts), we don't create new memory
                            if resolution_result.action == "supersede":
                                # Old memory was superseded, create new memory with the new value
                                # Fall through to memory creation logic below
                                pass
                            else:
                                # Invalidate or ask_user - don't create new memory
                                continue
                        else:
                            # Mark both as conflicted (requires user clarification)
                            existing_memory.mark_as_conflicted()
                            await self.semantic_memory_repo.update(existing_memory)
                            # Don't create new memory if unresolvable conflict
                            continue

                # No conflict or conflict was resolved - create/reinforce memory
                # Reinforce if: existing memories AND no conflict detected
                # Create new if: no existing memories OR conflict was resolved (old memory superseded)
                should_reinforce = existing_memories and not conflict
                should_create_new = not existing_memories or (conflict and conflict.is_resolvable_automatically)

                logger.debug(
                    "memory_creation_decision",
                    subject=triple.subject_entity_id,
                    predicate=triple.predicate,
                    has_existing_memories=bool(existing_memories),
                    has_conflict=bool(conflict),
                    conflict_resolvable=conflict.is_resolvable_automatically if conflict else None,
                    should_reinforce=should_reinforce,
                    should_create_new=should_create_new,
                )

                if should_reinforce:
                    # Reinforce existing memory (values match, increase confidence)
                    existing_memory = existing_memories[0]
                    self.memory_validation_service.reinforce_memory(
                        memory=existing_memory,
                        new_observation=triple,
                        event_id=message.event_id,
                    )
                    await self.semantic_memory_repo.update(existing_memory)

                    # Add to response
                    semantic_memory_dtos.append(
                        self._memory_to_dto(existing_memory)
                    )
                    semantic_memory_entities.append(existing_memory)
                elif should_create_new:
                    # Create new memory (first observation OR conflict resolved with new value)
                    # Generate embedding from natural language representation
                    embedding_text = self._triple_to_natural_language(
                        triple, entity_name_map
                    )
                    embedding = await self.embedding_service.generate_embedding(
                        embedding_text
                    )

                    logger.debug(
                        "generating_memory_embedding",
                        memory_predicate=triple.predicate,
                        embedding_text=embedding_text,
                    )

                    # Create semantic memory entity
                    memory = SemanticMemory(
                        user_id=user_id,
                        subject_entity_id=triple.subject_entity_id,
                        predicate=triple.predicate,
                        predicate_type=triple.predicate_type,
                        object_value=triple.object_value,
                        confidence=triple.confidence,
                        source_event_ids=[message.event_id],
                        embedding=embedding,
                    )

                    # Store in database
                    stored_memory = await self.semantic_memory_repo.create(memory)

                    # Add to response
                    semantic_memory_dtos.append(self._memory_to_dto(stored_memory))
                    semantic_memory_entities.append(stored_memory)

            except Exception as e:
                logger.error(
                    "semantic_memory_processing_error",
                    triple=str(triple),
                    error=str(e),
                )
                # Continue processing other triples

        logger.info(
            "semantic_extraction_complete",
            memory_count=len(semantic_memory_dtos),
            conflict_count=conflict_count,
        )

        return ExtractSemanticsResult(
            semantic_memory_dtos=semantic_memory_dtos,
            semantic_memory_entities=semantic_memory_entities,
            conflict_count=conflict_count,
            conflicts_detected=conflicts_detected,
        )

    # Phase 2.1: Removed _handle_auto_resolvable_conflict()
    # Now using ConflictResolutionService for proper resolution with status tracking

    # Note: Removed _is_question() method
    # Vision-aligned approach: Let the LLM-based semantic extraction determine what's extractable.
    # The extraction prompt instructs: "Analyze the message for factual statements about entities."
    # The LLM handles this intelligently without brittle pattern matching.

    def _triple_to_natural_language(
        self,
        triple: SemanticTriple,
        entity_name_map: dict[str, str],
    ) -> str:
        """Convert structured triple to natural language for embedding.

        Creates semantically meaningful text that will match user queries better
        than structured representations.

        Args:
            triple: Semantic triple to convert
            entity_name_map: Mapping of entity_id to canonical_name

        Returns:
            Natural language representation for embedding

        Examples:
            - "Kai Media prefers Friday deliveries"
            - "Kai Media's payment terms: NET15"
            - "TC Boiler prefers ACH payment method"
        """
        # Get canonical name (fallback to entity_id if not found)
        entity_name = entity_name_map.get(
            triple.subject_entity_id,
            triple.subject_entity_id
        )

        # Extract value from structured object_value
        if isinstance(triple.object_value, dict):
            value = triple.object_value.get("value", str(triple.object_value))
        else:
            value = str(triple.object_value)

        # Convert predicate to natural language
        # Remove underscores and convert to more natural phrasing
        predicate_natural = triple.predicate.replace("_", " ")

        # Build natural language based on predicate type
        if triple.predicate_type == PredicateType.PREFERENCE:
            # "Kai Media prefers Friday deliveries"
            return f"{entity_name} prefers {value} {predicate_natural}"
        elif triple.predicate_type == PredicateType.ATTRIBUTE:
            # "Kai Media payment terms: NET15"
            return f"{entity_name} {predicate_natural}: {value}"
        elif triple.predicate_type == PredicateType.RELATIONSHIP:
            # "Kai Media works with Supplier Co"
            return f"{entity_name} {predicate_natural}: {value}"
        elif triple.predicate_type == PredicateType.ACTION:
            # "Kai Media requested delivery on Friday"
            return f"{entity_name} {predicate_natural}: {value}"
        else:
            # Fallback for unknown types
            return f"{entity_name} {predicate_natural}: {value}"

    def _memory_to_dto(self, memory: SemanticMemory) -> SemanticMemoryDTO:
        """Convert SemanticMemory entity to DTO.

        Args:
            memory: Semantic memory entity

        Returns:
            SemanticMemoryDTO
        """
        return SemanticMemoryDTO(
            memory_id=memory.memory_id or 0,
            subject_entity_id=memory.subject_entity_id,
            predicate=memory.predicate,
            predicate_type=memory.predicate_type.value,
            object_value=memory.object_value,
            confidence=memory.confidence,
            status=memory.status,
        )

    async def _detect_and_create_policy(
        self, message: ChatMessage, user_id: str
    ) -> SemanticMemory | None:
        """Detect policy statements and create policy memories.

        Phase 3.3: Simple pattern matching for reminder policies.
        Pattern: "If [entity_type] is [condition] [threshold], remind me"

        Args:
            message: Chat message to analyze
            user_id: User identifier

        Returns:
            SemanticMemory if policy detected, None otherwise
        """
        import re
        from datetime import UTC, datetime

        content_lower = message.content.lower()

        # Pattern: "if [an] invoice is [still] open X days before due, remind me"
        # Capture: threshold (number of days)
        pattern = r"if.*invoice.*(?:still\s+)?open\s+(\d+)\s+days?\s+before\s+due.*remind"

        match = re.search(pattern, content_lower)
        if not match:
            return None

        # Extract threshold
        threshold_days = int(match.group(1))

        logger.info(
            "reminder_policy_detected",
            entity_type="invoice",
            condition="open",
            threshold_days=threshold_days,
        )

        # Create policy memory
        # Subject: system (user-specific policy)
        # Predicate: reminder_policy
        # Object: structured policy data
        policy_data = {
            "trigger_type": "time_based",
            "entity_type": "invoice",
            "condition": "status_open",
            "threshold_days": threshold_days,
            "threshold_type": "days_before_due",
            "action": "remind_user",
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Generate embedding for policy (for future retrieval)
        embedding_text = f"Reminder policy: notify user when invoices are open {threshold_days} days before due date"
        embedding = await self.embedding_service.generate_embedding(embedding_text)

        # Create semantic memory
        policy_memory = SemanticMemory(
            user_id=user_id,
            subject_entity_id="system_policy",  # System-level policy (matches canonical entity_id)
            predicate="reminder_policy",
            predicate_type=PredicateType.ACTION,
            object_value=policy_data,
            confidence=0.95,  # Explicit statement = high confidence
            source_event_ids=[message.event_id],
            embedding=embedding,
        )

        # Ensure "system" canonical entity exists
        # Policy memories use subject_entity_id="system" which requires a canonical entity
        if self.canonical_entity_repo:
            from src.domain.entities import CanonicalEntity
            from src.domain.value_objects import EntityReference

            # Check if system entity exists, create if not
            try:
                system_entity = await self.canonical_entity_repo.find_by_entity_id("system_policy")
            except Exception:
                system_entity = None

            if not system_entity:
                # Create system entity
                # System entity doesn't map to external database, use placeholder EntityReference
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
                await self.canonical_entity_repo.create(system_entity)
                logger.info("system_entity_created_for_policies")

        # Store policy memory in database
        stored_memory = await self.semantic_memory_repo.create(policy_memory)

        logger.info(
            "policy_memory_created",
            memory_id=stored_memory.memory_id,
            threshold_days=threshold_days,
        )

        return stored_memory
