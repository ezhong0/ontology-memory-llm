# Phase 1B Implementation Plan: Semantic Memory Extraction

**Date**: October 15, 2025
**Status**: Planning
**Dependencies**: Phase 1A Complete ✅

---

## Executive Summary

Phase 1B extends Phase 1A by adding **semantic memory extraction and storage**. While Phase 1A focused on entity resolution, Phase 1B extracts semantic triples (subject-predicate-object relationships) from conversations and stores them as queryable memories.

### Key Deliverables

1. **Semantic Triple Extraction**: LLM-based extraction of SPO triples from chat messages
2. **Memory Storage**: Persist semantic memories with embeddings
3. **Memory Retrieval**: Query-based retrieval using vector similarity
4. **Memory Validation**: Confidence tracking and decay over time
5. **Conflict Detection**: Identify contradictory information

---

## Architecture Overview

### Data Flow

```
User Message
    ↓
[Phase 1A: Entity Resolution] ← Already implemented
    ↓
Resolved Entities + Original Message
    ↓
[Phase 1B: Semantic Extraction] ← NEW
    ├─ Extract SPO triples using LLM
    ├─ Generate embeddings for predicates
    ├─ Detect conflicts with existing memories
    └─ Store semantic memories
    ↓
Stored Semantic Memories (queryable)
```

### Layer Structure

```
API Layer (FastAPI)
  ↓
Application Layer (Use Cases)
  ├─ ProcessChatMessageUseCase (ENHANCED)
  └─ QueryMemoriesUseCase (NEW)
  ↓
Domain Layer (Business Logic)
  ├─ SemanticExtractionService (NEW)
  ├─ MemoryValidationService (NEW)
  └─ ConflictDetectionService (NEW)
  ↓
Infrastructure Layer
  ├─ SemanticMemoryRepository (NEW)
  ├─ OpenAILLMService (ENHANCED - add triple extraction)
  └─ OpenAIEmbeddingService (existing)
```

---

## Design Decisions

### 1. Surgical LLM Use (Continued)

**Philosophy**: Use LLMs only where they add clear value.

- **Entity Resolution**: 95% deterministic (Phase 1A) ✅
- **Semantic Extraction**: 100% LLM-based (Phase 1B) ← NEW
  - Reason: Natural language understanding requires LLM
  - Cost: ~$0.01 per message (acceptable for value provided)
- **Memory Retrieval**: 100% deterministic (vector similarity) ← NEW

**Total System Cost**: ~$0.015 per message (~$15 per 1,000 messages)

###  2. Semantic Triple Structure

**Format**: Subject-Predicate-Object (SPO) triples

```python
@dataclass(frozen=True)
class SemanticTriple:
    subject_entity_id: str  # From Phase 1A entity resolution
    predicate: str  # Normalized predicate (e.g., "prefers_delivery_day")
    predicate_type: str  # Type: attribute | preference | relationship | action
    object_value: dict[str, Any]  # Structured value
    confidence: float  # Initial confidence [0.0, 1.0]
    source_event_ids: list[int]  # Episodic evidence
```

**Example**:
```json
{
  "subject_entity_id": "customer_acme_123",
  "predicate": "prefers_delivery_day",
  "predicate_type": "preference",
  "object_value": {"type": "day_of_week", "value": "Friday"},
  "confidence": 0.85,
  "source_event_ids": [42, 57]
}
```

### 3. Predicate Taxonomy

**Four Core Types**:

1. **attribute**: Factual properties (`payment_terms`, `industry`, `size`)
2. **preference**: User/entity preferences (`prefers_x`, `dislikes_y`)
3. **relationship**: Inter-entity relationships (`supplies_to`, `is_customer_of`)
4. **action**: Completed actions (`ordered`, `cancelled`, `requested`)

### 4. Confidence & Validation

**Initial Confidence** (based on source):
- Explicit statement: 0.9 ("Acme prefers Friday deliveries")
- Implicit statement: 0.7 ("They usually want Friday")
- Inferred: 0.5 ("They mentioned Friday twice")

**Decay Function** (temporal):
```python
confidence(t) = initial_confidence * exp(-decay_rate * days_since_last_validation)
```

**Reinforcement** (repeated observations):
```python
new_confidence = min(0.95, old_confidence + 0.05 * reinforcement_count)
```

### 5. Conflict Detection

**Conflicting Memories**: Same subject + predicate, different object values

**Resolution Strategy**:
1. **Temporal**: Most recent wins (if >30 days difference)
2. **Confidence**: Highest confidence wins (if >0.2 difference)
3. **Reinforcement**: Most reinforced wins (if >3 observations difference)
4. **Default**: Mark as conflicting, require user clarification

---

## Implementation Steps

### Step 1: Domain Layer - Value Objects & Entities

**New Value Objects**:
- `SemanticTriple` - Immutable SPO triple
- `MemoryConflict` - Conflict detection result
- `PredicateType` - Enum for predicate types

**New Entities**:
- `SemanticMemory` - Mutable semantic memory with lifecycle
- `MemoryValidation` - Validation event

**Files**:
- `src/domain/value_objects/semantic_triple.py`
- `src/domain/value_objects/memory_conflict.py`
- `src/domain/entities/semantic_memory.py`

### Step 2: Domain Layer - Services

**New Services**:

**1. SemanticExtractionService**
```python
class SemanticExtractionService:
    async def extract_triples(
        self,
        message: ChatMessage,
        resolved_entities: list[ResolvedEntityDTO],
    ) -> list[SemanticTriple]:
        """Extract semantic triples from message using LLM."""
        # Build extraction prompt with resolved entities
        # Call LLM (GPT-4-turbo)
        # Parse and validate triples
        # Return structured triples
```

**2. MemoryValidationService**
```python
class MemoryValidationService:
    def calculate_confidence_decay(
        self,
        memory: SemanticMemory,
        current_date: datetime,
    ) -> float:
        """Calculate decayed confidence based on time."""

    async def reinforce_memory(
        self,
        memory: SemanticMemory,
        new_observation: SemanticTriple,
    ) -> SemanticMemory:
        """Reinforce existing memory with new observation."""
```

**3. ConflictDetectionService**
```python
class ConflictDetectionService:
    async def detect_conflicts(
        self,
        new_triple: SemanticTriple,
        existing_memories: list[SemanticMemory],
    ) -> Optional[MemoryConflict]:
        """Detect if new triple conflicts with existing memories."""
```

**Files**:
- `src/domain/services/semantic_extraction_service.py`
- `src/domain/services/memory_validation_service.py`
- `src/domain/services/conflict_detection_service.py`

### Step 3: Infrastructure Layer - Repositories

**New Repositories**:

**SemanticMemoryRepository**
```python
class SemanticMemoryRepository:
    async def create(self, memory: SemanticMemory) -> SemanticMemory:
        """Store semantic memory with embedding."""

    async def find_similar(
        self,
        query_embedding: list[float],
        user_id: str,
        limit: int = 50,
    ) -> list[SemanticMemory]:
        """Find similar memories using pgvector."""

    async def find_by_subject_predicate(
        self,
        subject_entity_id: str,
        predicate: str,
        user_id: str,
    ) -> list[SemanticMemory]:
        """Find memories for conflict detection."""
```

**Files**:
- `src/infrastructure/database/repositories/semantic_memory_repository.py`

### Step 4: Infrastructure Layer - Enhanced LLM Service

**Enhance OpenAILLMService**:
```python
class OpenAILLMService:
    # Existing method
    async def resolve_coreference(...) -> ResolutionResult:
        """Coreference resolution (Phase 1A)."""

    # NEW method
    async def extract_semantic_triples(
        self,
        message: str,
        resolved_entities: list[dict],
    ) -> list[dict]:
        """Extract semantic triples using GPT-4-turbo.

        Prompt includes:
        - Message content
        - Resolved entities with types
        - Predicate taxonomy
        - Output format (JSON)
        """
```

**Prompt Engineering**:
```python
EXTRACTION_PROMPT = """
You are an expert at extracting structured knowledge from conversations.

Extract semantic triples (subject-predicate-object) from the message below.

Resolved Entities:
{entities_json}

Predicate Types:
- attribute: Factual properties (payment_terms, industry)
- preference: User preferences (prefers_x, dislikes_y)
- relationship: Inter-entity relationships (supplies_to, works_with)
- action: Completed actions (ordered, cancelled)

Message: "{message}"

Output JSON array of triples:
[{
  "subject_entity_id": "customer_acme_123",
  "predicate": "prefers_delivery_day",
  "predicate_type": "preference",
  "object_value": {"type": "day_of_week", "value": "Friday"},
  "confidence": 0.85
}]
"""
```

### Step 5: Application Layer - Enhanced Use Case

**Enhance ProcessChatMessageUseCase**:
```python
class ProcessChatMessageUseCase:
    async def execute(self, input_dto: ProcessChatMessageInput) -> ProcessChatMessageOutput:
        # Phase 1A: Entity Resolution (existing)
        mentions = self.mention_extractor.extract_mentions(...)
        resolved_entities = await self._resolve_entities(...)

        # Phase 1B: Semantic Extraction (NEW)
        triples = await self.semantic_extraction_service.extract_triples(
            message=stored_message,
            resolved_entities=resolved_entities,
        )

        # Phase 1B: Store Memories (NEW)
        stored_memories = []
        for triple in triples:
            # Check for conflicts
            conflict = await self.conflict_detection_service.detect_conflicts(...)
            if conflict:
                log_conflict(conflict)

            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(...)

            # Store memory
            memory = await self.semantic_memory_repo.create(...)
            stored_memories.append(memory)

        # Return enhanced output
        return ProcessChatMessageOutput(
            ...existing fields...,
            semantic_memories=stored_memories,  # NEW
            conflict_count=len(conflicts),  # NEW
        )
```

### Step 6: API Layer - Enhanced Response

**Update ChatMessageResponse**:
```python
class SemanticMemoryResponse(BaseModel):
    memory_id: int
    subject_entity_id: str
    predicate: str
    predicate_type: str
    object_value: dict[str, Any]
    confidence: float

class ChatMessageResponse(BaseModel):
    # Phase 1A fields (existing)
    event_id: int
    session_id: UUID
    resolved_entities: list[ResolvedEntityResponse]

    # Phase 1B fields (NEW)
    semantic_memories: list[SemanticMemoryResponse]
    memory_count: int
    conflict_count: int
```

### Step 7: Testing

**Unit Tests**:
- `test_semantic_extraction_service.py` (triple extraction logic)
- `test_memory_validation_service.py` (confidence decay, reinforcement)
- `test_conflict_detection_service.py` (conflict detection logic)

**Integration Tests**:
- `test_semantic_memory_repository.py` (vector similarity search)
- `test_llm_service_extraction.py` (LLM prompt engineering)

**E2E Tests**:
- Full message → entities → triples → storage flow

---

## Database Schema (Already Exists from Week 0)

**semantic_memories table**:
```sql
CREATE TABLE app.semantic_memories (
    memory_id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    subject_entity_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    predicate_type TEXT NOT NULL,
    object_value JSONB NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    status TEXT NOT NULL DEFAULT 'active',
    reinforcement_count INT DEFAULT 1,
    last_validated_at TIMESTAMPTZ,
    source_event_ids BIGINT[] NOT NULL,
    embedding vector(1536),  -- pgvector
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_semantic_subject_pred ON app.semantic_memories (subject_entity_id, predicate);
CREATE INDEX idx_semantic_embedding ON app.semantic_memories USING ivfflat (embedding vector_cosine_ops);
```

---

## Cost Analysis

### Per-Message Costs

| Component | Frequency | Unit Cost | Cost per msg |
|-----------|-----------|-----------|--------------|
| Entity Resolution | 100% | $0 (95% deterministic) | $0.003 |
| Semantic Extraction | 100% | ~$0.01 (GPT-4-turbo) | $0.010 |
| Embeddings | 3-5 triples | $0.00002 per embedding | $0.0001 |
| **Total** | | | **~$0.013** |

**Cost per 1,000 messages**: ~$13
**Cost per 100,000 messages**: ~$1,300

### Token Estimates

**Semantic Extraction Prompt**:
- System prompt: ~200 tokens
- Message content: ~100 tokens
- Resolved entities: ~50 tokens
- Response: ~150 tokens
- **Total**: ~500 tokens per extraction

**GPT-4-turbo Pricing** (as of 2024):
- Input: $10 / 1M tokens
- Output: $30 / 1M tokens
- ~$0.01 per extraction (500 tokens)

---

## Success Criteria

### Functional Requirements
- ✅ Extract semantic triples from natural language
- ✅ Store triples with vector embeddings
- ✅ Detect conflicts between memories
- ✅ Calculate confidence decay
- ✅ Reinforce repeated observations

### Non-Functional Requirements
- **Accuracy**: >85% correct triple extraction (manual review of 100 samples)
- **Performance**: <2s end-to-end latency (P95)
- **Cost**: <$0.02 per message
- **Coverage**: 80%+ test coverage

### Quality Standards
- Clean hexagonal architecture (continued)
- Type-safe interfaces
- Comprehensive unit tests
- Integration tests with real LLM
- Documentation for all public APIs

---

## Implementation Timeline

### Phase 1B.1: Core Extraction (2-3 hours)
1. Create domain value objects and entities
2. Implement SemanticExtractionService
3. Enhance OpenAILLMService with triple extraction
4. Unit tests for extraction logic

### Phase 1B.2: Memory Storage (1-2 hours)
1. Implement SemanticMemoryRepository
2. Add embedding generation to workflow
3. Update ProcessChatMessageUseCase
4. Integration tests

### Phase 1B.3: Validation & Conflicts (1 hour)
1. Implement MemoryValidationService
2. Implement ConflictDetectionService
3. Add conflict detection to use case
4. Unit tests

### Phase 1B.4: API Enhancement (30 min)
1. Update response models
2. Add semantic memory fields to API
3. Update API documentation
4. E2E tests

### Phase 1B.5: Testing & Documentation (1 hour)
1. Comprehensive test suite
2. Update completion documentation
3. Performance benchmarking
4. Cost analysis validation

**Total Estimated Time**: 6-8 hours

---

## Risks & Mitigations

### Risk 1: LLM Extraction Accuracy
**Risk**: LLM may extract incorrect or irrelevant triples
**Mitigation**:
- Careful prompt engineering with examples
- Schema validation on LLM output
- Confidence thresholds for filtering
- Human-in-the-loop for low confidence

### Risk 2: Cost Overruns
**Risk**: Semantic extraction adds $0.01 per message
**Mitigation**:
- Cache extractions for duplicate messages
- Batch processing where possible
- Monitor costs with alerts
- Optimize prompts to reduce tokens

### Risk 3: Vector Search Performance
**Risk**: pgvector search may be slow at scale
**Mitigation**:
- Use IVFFlat index (already configured)
- Limit search to active memories only
- Add user_id filtering to reduce search space
- Consider ANN approximation

### Risk 4: Conflict Resolution Complexity
**Risk**: Handling conflicts may require complex logic
**Mitigation**:
- Start with simple temporal/confidence rules
- Log all conflicts for analysis
- Defer complex resolution to Phase 2
- Provide user override mechanism

---

## Post-Phase 1B: Future Enhancements

### Phase 1C: Domain Ontology Integration
- Connect to external domain database
- Lazy entity creation from domain DB
- Ontology-aware relationship validation

### Phase 2: Advanced Memory
- Episodic memory extraction
- Procedural memory (how-to knowledge)
- Memory consolidation (long-term storage)
- Context assembly for LLM prompts

---

## Appendix: Example Extraction

**Input Message**:
```
"Acme Corp prefers Friday deliveries and has NET30 payment terms.
They recently ordered 500 units of Widget X."
```

**Resolved Entities** (from Phase 1A):
```json
[
  {"entity_id": "customer_acme_123", "canonical_name": "Acme Corporation", "type": "customer"},
  {"entity_id": "product_widgetx_456", "canonical_name": "Widget X", "type": "product"}
]
```

**Extracted Triples** (Phase 1B):
```json
[
  {
    "subject_entity_id": "customer_acme_123",
    "predicate": "prefers_delivery_day",
    "predicate_type": "preference",
    "object_value": {"type": "day_of_week", "value": "Friday"},
    "confidence": 0.9
  },
  {
    "subject_entity_id": "customer_acme_123",
    "predicate": "payment_terms",
    "predicate_type": "attribute",
    "object_value": {"type": "payment_terms", "value": "NET30"},
    "confidence": 0.95
  },
  {
    "subject_entity_id": "customer_acme_123",
    "predicate": "ordered",
    "predicate_type": "action",
    "object_value": {
      "product_id": "product_widgetx_456",
      "quantity": 500,
      "timestamp": "2025-10-15T12:00:00Z"
    },
    "confidence": 0.95
  }
]
```

---

**Status**: Ready for Implementation
**Next Step**: Begin Phase 1B.1 - Core Extraction

*Plan created: October 15, 2025*
