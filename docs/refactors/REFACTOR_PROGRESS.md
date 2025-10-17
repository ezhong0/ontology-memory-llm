# Refactor Progress: Triple → Entity-Tagged

## ✅ Completed

### 1. Design & Planning
- ✅ **Importance calculation algorithm** (`docs/design/importance_calculation.md`)
- ✅ **Comprehensive refactor plan** (`docs/refactors/triple_to_entity_tagged_refactor.md`)

### 2. Domain Layer
- ✅ **SemanticMemory entity** (`src/domain/entities/semantic_memory.py`)
  - Removed: `subject_entity_id`, `predicate`, `predicate_type`, `object_value`, `reinforcement_count`, `last_validated_at`, `original_text`, `related_entities`
  - Added: `content`, `entities`, `importance`, `metadata`, `last_accessed_at`
  - Updated methods: `confirm()`, `apply_decay()`, `mark_accessed()`
  - New properties: `is_high_importance`, `days_since_last_access`, `confirmation_count`

### 3. Infrastructure Layer
- ✅ **Database model** (`src/infrastructure/database/models.py`)
  - Updated SemanticMemory ORM model with new schema
  - New indexes: `idx_semantic_entities_gin`, `idx_semantic_user_importance`
  - Removed indexes: `idx_semantic_entity_pred`, `idx_semantic_memories_entity_pred_user`

- ✅ **Migration** (`20251017_0000-refactor_triples_to_entities.py`)
  - Complete data migration preserving existing memories
  - Converts triple structure → natural language
  - Stores original predicate info in metadata for audit trail

- ✅ **Repository** (`src/infrastructure/database/repositories/semantic_memory_repository.py`)
  - Replaced `find_by_subject_predicate()` → `find_by_entities()`
  - Updated all mapping functions
  - Added `min_importance` filtering to `find_similar()`

---

## 🚧 In Progress / Remaining

### 4. Application Layer (CRITICAL - Needs Update)

#### A. Extraction Service
**File**: `src/application/use_cases/extract_semantics.py`

**Current Issues**:
- Still uses SemanticTriple extraction
- Calls `semantic_extraction_service.extract_triples()`
- Converts triples to natural language
- Uses predicate-based conflict detection

**Required Changes**:
```python
# REMOVE: Triple extraction
triples = await self.semantic_extraction_service.extract_triples(...)

# REPLACE WITH: Natural language fact extraction
facts = await self.llm_service.extract_facts(
    message=message.content,
    resolved_entities=[{...}]
)
# Returns: [{"content": "Gai Media prefers Friday", "entities": [...], "confidence": 0.9}]

# REMOVE: Triple to natural language conversion
original_text = self._triple_to_natural_language(triple, entity_name_map)

# REPLACE WITH: Facts are already natural language
content = fact["content"]
entities = fact["entities"]

# CREATE memory directly
memory = SemanticMemory(
    user_id=user_id,
    content=fact["content"],
    entities=fact["entities"],
    confidence=fact["confidence"],
    importance=0.3 + (fact["confidence"] * 0.6),  # Calculate importance
    embedding=await self.embedding_service.generate_embedding(fact["content"]),
    source_text=message.content,
    metadata={},
)
```

#### B. Conflict Detection Service
**File**: `src/domain/services/conflict_detection_service.py`

**Current Issues**:
- Compares `subject_entity_id` + `predicate`
- Checks if `object_value` differs

**Required Changes**:
```python
# OLD: Predicate-based
conflict = (
    memory1.subject_entity_id == memory2.subject_entity_id
    and memory1.predicate == memory2.predicate
    and memory1.object_value != memory2.object_value
)

# NEW: Semantic similarity-based
entity_overlap = len(set(m1.entities) & set(m2.entities)) / len(set(m1.entities) | set(m2.entities))
semantic_sim = cosine_similarity(m1.embedding, m2.embedding)

# Use LLM to detect contradiction
contradiction = await llm.detect_contradiction(m1.content, m2.content)

conflict = (
    entity_overlap >= 0.8  # High entity overlap
    and semantic_sim >= 0.85  # Semantically similar topic
    and contradiction  # But contradictory content
)
```

#### C. Memory Validation Service
**File**: `src/domain/services/memory_validation_service.py`

**Current Issues**:
- Uses `reinforce_memory()` method
- Updates `reinforcement_count`

**Required Changes**:
```python
# OLD:
def reinforce_memory(self, memory, new_observation, event_id):
    memory.reinforce(event_id)

# NEW:
def confirm_memory(self, memory, new_observation, event_id):
    memory.confirm(event_id)  # Updates importance + metadata
```

#### D. DTOs & API Models
**Files**:
- `src/application/dtos/chat_dtos.py` - SemanticMemoryDTO
- `src/api/models/memories.py` - SemanticMemoryResponse

**Required Changes**:
```python
# Remove fields:
- subject_entity_id
- predicate
- predicate_type
- object_value

# Add fields:
+ content: str
+ entities: list[str]
+ importance: float
+ metadata: dict
```

---

### 5. Test Layer (CRITICAL - Needs Update)

#### A. Test Fixtures
**File**: `tests/fixtures/memory_factory.py`

**Required Changes**:
```python
async def create_semantic_memory(
    self,
    user_id: str,
    content: str,  # NEW: Natural language
    entities: list[str],  # NEW: Entity list
    confidence: float = 0.7,
    importance: float | None = None,  # NEW
    metadata: dict | None = None,  # NEW
    # REMOVE: predicate, predicate_type, object_value, subject_entity_id
):
    if importance is None:
        importance = 0.3 + (confidence * 0.6)

    embedding = await self.embedding_service.generate_embedding(content)

    memory = SemanticMemory(
        user_id=user_id,
        content=content,
        entities=entities,
        confidence=confidence,
        importance=importance,
        metadata=metadata or {},
        embedding=embedding,
        ...
    )
    ...
```

#### B. Unit Tests
- `tests/unit/domain/test_semantic_memory.py` - Update entity tests
- `tests/unit/domain/test_conflict_detection_service.py` - Update for new conflict logic
- `tests/unit/infrastructure/test_semantic_memory_repository.py` - Update queries

#### C. E2E Tests
- `tests/e2e/test_scenarios.py` - Update expectations

---

### 6. Files to Delete (After Migration)

```bash
# Can delete after all tests pass:
rm src/domain/value_objects/semantic_triple.py
rm src/domain/value_objects/predicate_type.py
rm src/domain/services/semantic_extraction_service.py
```

---

## Migration Checklist

### Pre-Migration
- [ ] Backup database
- [ ] Run all tests (capture current state)
- [ ] Review migration SQL

### Run Migration
```bash
# Run migration
DATABASE_URL="postgresql+asyncpg://testuser:testpass@localhost:5433/testdb" \
  poetry run alembic upgrade head

# Verify data migrated
psql -h localhost -p 5433 -U testuser -d testdb -c \
  "SELECT memory_id, content, entities, importance FROM app.semantic_memories LIMIT 5;"
```

### Post-Migration
- [ ] Update extraction service
- [ ] Update conflict detection
- [ ] Update DTOs/API models
- [ ] Update test fixtures
- [ ] Run all tests
- [ ] Fix failures
- [ ] Delete deprecated files

---

## Quick Reference: Key Changes

| Old (Triple) | New (Entity-Tagged) |
|--------------|---------------------|
| `subject_entity_id: str` | `entities: list[str]` |
| `predicate: str` | (removed) |
| `predicate_type: PredicateType` | (removed) |
| `object_value: dict` | `content: str` |
| `reinforcement_count: int` | `importance: float` |
| `last_validated_at` | `last_accessed_at` |
| `reinforce()` | `confirm()` |

---

## Next Steps (Priority Order)

1. **Update extraction service** - No longer extract triples, extract facts
2. **Update memory_factory** - Tests will need this
3. **Update conflict detection** - New semantic similarity approach
4. **Update DTOs** - API contract changes
5. **Run migration** - Transform database
6. **Fix tests** - Update assertions
7. **Delete deprecated files** - Cleanup

---

## Estimated Time Remaining

- Extraction service: 30 min
- Test fixtures: 20 min
- Conflict detection: 30 min
- DTOs/API: 20 min
- Fix tests: 30 min
- Total: ~2.5 hours

**Current Progress: ~40% complete**
