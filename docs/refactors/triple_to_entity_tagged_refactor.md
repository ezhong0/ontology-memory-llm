# Refactor: Triple-Based → Entity-Tagged Natural Language

## Executive Summary

**Goal**: Transform semantic memories from structured triples (subject-predicate-object) to entity-tagged natural language with importance scoring.

**Rationale**:
1. ✅ **Simpler mental model** - "Memories are entity-tagged text" vs "Memories are SPO triples"
2. ✅ **Better semantic search** - Embed natural language, not structured data
3. ✅ **Flexible schema** - No predicate taxonomy to maintain
4. ✅ **Importance > Count** - Dynamic scoring replaces discrete reinforcement_count
5. ✅ **Multi-entity native** - List of entities, not single subject

---

## Schema Changes

### Before (Triple-Based)
```python
SemanticMemory(
    subject_entity_id="customer:gai_123",      # Single subject
    predicate="delivery_preference",            # Typed predicate
    predicate_type=PredicateType.PREFERENCE,   # Enum
    object_value={"value": "Friday"},           # Structured object
    reinforcement_count=3,                      # Discrete counter
    confidence=0.85,
    embedding=[...],  # Embedded from structured text
)
```

### After (Entity-Tagged Natural Language)
```python
SemanticMemory(
    content="Gai Media prefers Friday deliveries",  # Natural language
    entities=["customer:gai_123"],                   # Multiple entities
    importance=0.87,                                 # Dynamic score
    confidence=0.85,
    metadata={"confirmation_count": 3},              # Flexible metadata
    embedding=[...],  # Embedded from natural language
)
```

---

## Database Schema Changes

### Columns to Remove
- `subject_entity_id` (replaced by `entities` array)
- `predicate` (no longer needed)
- `predicate_type` (no longer needed)
- `object_value` (replaced by `content` text)
- `reinforcement_count` (replaced by `importance` + metadata)
- `last_validated_at` (replaced by `last_accessed_at`)
- `original_text` (replaced by `content`)
- `related_entities` (replaced by `entities`)

### Columns to Add
- `content` (TEXT NOT NULL) - The memory text
- `entities` (TEXT[] NOT NULL) - Entity IDs mentioned
- `importance` (FLOAT NOT NULL DEFAULT 0.5) - Dynamic importance score
- `metadata` (JSONB) - Flexible metadata (confirmation_count, tags, etc.)
- `last_accessed_at` (TIMESTAMP) - For decay calculation

### Columns to Keep
- `memory_id` (primary key)
- `user_id`
- `confidence`
- `status`
- `source_type`
- `source_memory_id`
- `extracted_from_event_id`
- `source_text` (original chat message)
- `superseded_by_memory_id`
- `embedding`
- `created_at`
- `updated_at`

### Index Changes

**Remove**:
- `idx_semantic_entity_pred` (subject_entity_id, predicate)
- `idx_semantic_memories_entity_pred_user` (subject_entity_id, predicate, user_id)

**Add**:
- `idx_semantic_entities_gin` (entities) using GIN for array contains queries
- `idx_semantic_importance` (user_id, importance DESC) for importance-based retrieval

**Keep**:
- `idx_semantic_user_status` (user_id, status)
- `idx_semantic_embedding` (embedding) using ivfflat
- `idx_semantic_memories_user_subject` → rename to `idx_semantic_user_entities`

---

## Code Changes by Layer

### 1. Domain Layer

#### `src/domain/entities/semantic_memory.py` ✅ DONE
- Remove: `subject_entity_id`, `predicate`, `predicate_type`, `object_value`, `reinforcement_count`, `last_validated_at`, `original_text`, `related_entities`
- Add: `content`, `entities`, `importance`, `metadata`, `last_accessed_at`
- Replace `reinforce()` → `confirm()`
- Add `mark_accessed()`, update `apply_decay()` to use importance
- Update validation, `to_dict()`, `__str__()`

#### `src/domain/value_objects/semantic_triple.py`
**Action**: DELETE entire file (no longer needed)

#### `src/domain/value_objects/__init__.py`
**Action**: Remove `SemanticTriple` export

#### `src/domain/value_objects/predicate_type.py`
**Action**: DELETE entire file (no longer needed)

#### `src/domain/services/semantic_extraction_service.py`
**Action**: DELETE entire file (replaced by simpler extraction)

#### `src/domain/services/conflict_detection_service.py`
**Action**: MAJOR REFACTOR - Conflicts now based on semantic similarity + entity overlap, not predicate matching

#### `src/domain/services/memory_validation_service.py`
**Action**: UPDATE - Replace `reinforce_memory()` with `confirm_memory()`, use importance

---

### 2. Infrastructure Layer

#### `src/infrastructure/database/models.py`
**Action**: UPDATE `SemanticMemory` ORM model
- Remove columns: `subject_entity_id`, `predicate`, `predicate_type`, `object_value`, `reinforcement_count`, `last_validated_at`, `original_text`, `related_entities`
- Add columns: `content`, `entities`, `metadata`, `last_accessed_at`
- Update `importance` (already exists, change default to 0.5)
- Update indexes

#### `src/infrastructure/database/repositories/semantic_memory_repository.py`
**Action**: MAJOR REFACTOR
- Remove `find_by_subject_predicate()` → Replace with `find_by_entities()`
- Update `_to_domain_entity()`, `_to_orm_model()`, `_row_to_domain_entity()`
- Update `find_similar()` SQL query
- Add `find_by_entity()` for single entity queries

#### `src/infrastructure/llm/openai_service.py`
**Action**: UPDATE
- Remove `extract_semantic_triples()` method
- Add `extract_semantic_facts()` method → Returns list of natural language facts with entities

---

### 3. Application Layer

#### `src/application/use_cases/extract_semantics.py`
**Action**: MAJOR REFACTOR
- Remove triple extraction flow
- Replace with: LLM extracts natural language facts + entities
- Remove predicate-based conflict detection
- Replace with: Semantic similarity-based conflict detection
- Update memory creation (no more `_triple_to_natural_language()`)
- Calculate importance from confidence: `importance = 0.3 + (confidence × 0.6)`

#### `src/application/use_cases/process_chat_message.py`
**Action**: UPDATE
- Update to handle new SemanticMemory structure
- No changes to high-level flow

#### `src/application/dtos/chat_dtos.py`
**Action**: UPDATE `SemanticMemoryDTO`
- Remove: `subject_entity_id`, `predicate`, `predicate_type`, `object_value`
- Add: `content`, `entities`, `importance`, `metadata`

---

### 4. API Layer

#### `src/api/models/memories.py`
**Action**: UPDATE `SemanticMemoryResponse`
- Match DTO changes above

#### `src/api/routes/chat.py`
**Action**: UPDATE
- Update response serialization for semantic memories
- Add `importance` to provenance info

---

### 5. LLM Prompts

#### Create new: `src/infrastructure/llm/prompts/extract_facts.py`
```python
"""
Extract semantic facts from conversation.

Input: "Remember: Gai Media prefers Friday deliveries and NET30 payment terms"

Output: [
    {
        "content": "Gai Media prefers Friday deliveries",
        "entities": ["customer:gai_123"],
        "confidence": 0.95
    },
    {
        "content": "Gai Media uses NET30 payment terms",
        "entities": ["customer:gai_123"],
        "confidence": 0.95
    }
]
"""
```

---

### 6. Tests

#### Unit Tests
- `tests/unit/domain/test_semantic_memory.py` - UPDATE validation, methods
- `tests/unit/domain/test_conflict_detection_service.py` - MAJOR REFACTOR
- `tests/unit/domain/test_memory_validation_service.py` - UPDATE for importance
- `tests/unit/infrastructure/test_semantic_memory_repository.py` - UPDATE queries

#### Integration Tests
- `tests/integration/test_semantic_extraction.py` - MAJOR REFACTOR

#### E2E Tests
- `tests/e2e/test_scenarios.py` - UPDATE expectations for new schema

#### Fixtures
- `tests/fixtures/memory_factory.py` - UPDATE `create_semantic_memory()`
- `tests/fixtures/factories.py` - UPDATE `SemanticMemoryBuilder`

---

## Migration Strategy

### Migration File: `20251017_0000-refactor_triples_to_entities.py`

```python
def upgrade():
    # Step 1: Add new columns (nullable initially)
    op.add_column('semantic_memories', Column('content', Text()))
    op.add_column('semantic_memories', Column('entities', ARRAY(Text())))
    op.add_column('semantic_memories', Column('metadata', JSONB, default={}))
    op.add_column('semantic_memories', Column('last_accessed_at', DateTime(timezone=True)))

    # Step 2: Migrate existing data
    op.execute("""
        UPDATE app.semantic_memories
        SET
            content = COALESCE(original_text, subject_entity_id || ' ' || predicate || ': ' || (object_value->>'value')),
            entities = ARRAY[subject_entity_id],
            metadata = jsonb_build_object(
                'confirmation_count', COALESCE(reinforcement_count - 1, 0),
                'migrated_from_triple', true,
                'original_predicate', predicate,
                'original_predicate_type', predicate_type
            ),
            last_accessed_at = COALESCE(last_validated_at, updated_at),
            importance = GREATEST(0.3, LEAST(1.0, 0.3 + (confidence * 0.6)))
        WHERE content IS NULL;
    """)

    # Step 3: Make new columns NOT NULL
    op.alter_column('semantic_memories', 'content', nullable=False)
    op.alter_column('semantic_memories', 'entities', nullable=False)
    op.alter_column('semantic_memories', 'last_accessed_at', nullable=False)

    # Step 4: Drop old columns
    op.drop_column('semantic_memories', 'subject_entity_id')
    op.drop_column('semantic_memories', 'predicate')
    op.drop_column('semantic_memories', 'predicate_type')
    op.drop_column('semantic_memories', 'object_value')
    op.drop_column('semantic_memories', 'reinforcement_count')
    op.drop_column('semantic_memories', 'last_validated_at')
    op.drop_column('semantic_memories', 'original_text')
    op.drop_column('semantic_memories', 'related_entities')

    # Step 5: Update indexes
    op.drop_index('idx_semantic_entity_pred', schema='app')
    op.drop_index('idx_semantic_memories_entity_pred_user', schema='app')

    op.create_index(
        'idx_semantic_entities_gin',
        'semantic_memories',
        ['entities'],
        postgresql_using='gin',
        schema='app'
    )

    op.create_index(
        'idx_semantic_user_importance',
        'semantic_memories',
        ['user_id', text('importance DESC')],
        schema='app'
    )

def downgrade():
    # Reverse migration (recreate triple structure)
    # Extract from metadata if available
    ...
```

---

## Conflict Detection Changes

### Before (Predicate-Based)
```python
# Conflict if same subject + predicate, different object
conflict = (
    memory1.subject_entity_id == memory2.subject_entity_id
    and memory1.predicate == memory2.predicate
    and memory1.object_value != memory2.object_value
)
```

### After (Semantic Similarity-Based)
```python
# Conflict if:
# 1. High entity overlap (>= 80% shared entities)
# 2. High semantic similarity (>= 0.85 cosine)
# 3. Low content similarity (indicating contradiction)

entity_overlap = len(set(m1.entities) & set(m2.entities)) / len(set(m1.entities) | set(m2.entities))
semantic_sim = cosine_similarity(m1.embedding, m2.embedding)

# Use LLM to detect contradiction
contradiction = await llm.detect_contradiction(m1.content, m2.content)

conflict = (
    entity_overlap >= 0.8
    and semantic_sim >= 0.85
    and contradiction
)
```

---

## Key Files Impacted

### Must Change (Breaking)
1. ✅ `src/domain/entities/semantic_memory.py` - DONE
2. `src/infrastructure/database/models.py`
3. `src/infrastructure/database/repositories/semantic_memory_repository.py`
4. `src/application/use_cases/extract_semantics.py`
5. `src/domain/services/conflict_detection_service.py`
6. `src/infrastructure/llm/openai_service.py`
7. `tests/fixtures/memory_factory.py`

### Must Update (Non-Breaking)
8. `src/application/dtos/chat_dtos.py`
9. `src/api/models/memories.py`
10. `src/domain/services/memory_validation_service.py`
11. All test files

### Can Delete
12. `src/domain/value_objects/semantic_triple.py`
13. `src/domain/value_objects/predicate_type.py`
14. `src/domain/services/semantic_extraction_service.py`

---

## Testing Strategy

### Phase 1: Unit Tests Pass
- Update domain entity tests
- Update repository tests (mocked)
- Update service tests

### Phase 2: Integration Tests Pass
- Test extraction flow end-to-end
- Test conflict detection with new logic
- Test importance calculation

### Phase 3: E2E Tests Pass
- Run all scenario tests
- Verify memory creation, retrieval, confirmation
- Verify conflicts still detected

### Phase 4: Manual Testing
- Run dev server
- Create memories via chat
- Verify database schema
- Test conflict scenarios

---

## Rollout Plan

### Step 1: Preparation (No Breaking Changes)
- ✅ Create design docs
- ✅ Update domain entity
- Create migration (with data migration)
- Update tests to be schema-agnostic

### Step 2: Database Migration
- Run migration on dev DB
- Verify data migrated correctly
- Check all indexes created

### Step 3: Code Updates (Parallel)
- Update repository layer
- Update extraction service
- Update conflict detection
- Update all usages

### Step 4: Testing
- Run full test suite
- Fix failures
- Manual QA

### Step 5: Cleanup
- Delete old files (SemanticTriple, PredicateType, etc.)
- Update documentation
- Archive old triple-based docs

---

## Risk Mitigation

### Risk 1: Data Loss During Migration
**Mitigation**:
- Store original triple data in `metadata` field
- Test migration on copy of production DB first
- Create backup before migration

### Risk 2: Conflict Detection Too Aggressive
**Mitigation**:
- Start with high thresholds (0.9 similarity)
- Monitor false positives
- Allow user to mark "not a conflict"

### Risk 3: Importance Decay Too Fast
**Mitigation**:
- Use conservative decay rate (0.01 → 69 day half-life)
- Phase 1: No automatic decay, only on-access
- Monitor memory importance distribution

### Risk 4: Breaking Changes Cascade
**Mitigation**:
- Update domain layer first (interfaces stable)
- Run tests after each layer update
- Keep old methods with deprecation warnings during transition

---

## Success Criteria

### Functional
- ✅ All tests pass
- ✅ Can create memories from natural language
- ✅ Can retrieve memories by entity
- ✅ Conflicts still detected (via semantic similarity)
- ✅ Importance scores reasonable (0.3-1.0 range)

### Performance
- ✅ Semantic search still fast (<200ms p95)
- ✅ Entity-based filtering uses GIN index efficiently
- ✅ No regression in retrieval quality

### Quality
- ✅ No mypy errors
- ✅ 90% domain test coverage maintained
- ✅ All E2E scenarios pass
- ✅ Documentation updated

---

## Timeline Estimate

- **Step 1** (Prep): 30 min ✅ DONE
- **Step 2** (Migration): 20 min
- **Step 3** (Code Updates): 2-3 hours
- **Step 4** (Testing): 1 hour
- **Step 5** (Cleanup): 30 min

**Total**: ~4-5 hours

---

## Next Steps

1. Update database model (`models.py`)
2. Create migration file with data migration
3. Update repository layer
4. Update extraction service
5. Update conflict detection
6. Update all tests
7. Run migration and verify
8. Delete deprecated files

Ready to proceed? 🚀
