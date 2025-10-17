# Hybrid Semantic Memory Implementation

## Overview

Implemented hybrid approach combining **structured triples** (for fast queries) with **natural language context** (for readability and better embeddings).

## Changes Made

### 1. Domain Entity (`src/domain/entities/semantic_memory.py`)

Added three new fields to `SemanticMemory`:

```python
original_text: str | None = None  # Normalized triple text
source_text: str | None = None     # Original chat message
related_entities: list[str] = field(default_factory=list)  # All entities mentioned
```

**Example**:
```python
memory = SemanticMemory(
    subject_entity_id="customer:gai_123",
    predicate="delivery_preference",
    object_value={"value": "Friday"},

    # New fields
    original_text="Gai Media prefers Friday deliveries",
    source_text="Remember: Gai Media prefers Friday deliveries and NET30 payment terms",
    related_entities=["customer:gai_123"]
)
```

### 2. Database Model (`src/infrastructure/database/models.py`)

Added three columns to `semantic_memories` table:

```python
original_text = Column(Text)              # Natural language representation
source_text = Column(Text)                # Original chat message
related_entities = Column(ARRAY(Text))    # All entity IDs mentioned
```

### 3. Repository (`src/infrastructure/database/repositories/semantic_memory_repository.py`)

Updated all mapping functions to handle new fields:
- `_to_domain_entity()` - Map ORM → Domain
- `_row_to_domain_entity()` - Map SQL Row → Domain
- `_to_orm_model()` - Map Domain → ORM
- `find_similar()` - Include new columns in SQL query

### 4. Extraction Use Case (`src/application/use_cases/extract_semantics.py`)

Updated memory creation to populate new fields:

```python
# Generate natural language representation
original_text = self._triple_to_natural_language(triple, entity_name_map)

# Embed over natural language (better semantic matching)
embedding = await self.embedding_service.generate_embedding(original_text)

# Create memory with hybrid fields
memory = SemanticMemory(
    # ... structured triple fields ...
    original_text=original_text,
    source_text=message.content,
    related_entities=[e.entity_id for e in resolved_entities],
)
```

### 5. Database Migration

Created migration: `20251016_2345-add_context_fields_to_semantic_memories.py`

```sql
-- Add columns (all nullable for backward compatibility)
ALTER TABLE app.semantic_memories ADD COLUMN original_text TEXT;
ALTER TABLE app.semantic_memories ADD COLUMN source_text TEXT;
ALTER TABLE app.semantic_memories ADD COLUMN related_entities TEXT[];
```

### 6. Test Fixtures (`tests/fixtures/memory_factory.py`)

Updated `create_semantic_memory()` to support new fields with auto-generation:

```python
# Auto-generate original_text if not provided
if not original_text:
    original_text = f"{subject_entity_id} {predicate_natural}: {value_str}"

# Embed over natural language
embedding = await self.embedding_service.generate_embedding(original_text)
```

## Benefits

### 1. **Fast Structured Queries** (via triple)
```sql
-- Direct index lookup (20ms)
SELECT * FROM semantic_memories
WHERE subject_entity_id = 'customer:gai_123'
  AND predicate = 'delivery_preference';
```

### 2. **Human-Readable Display** (via original_text)
```
Memory: "Gai Media prefers Friday deliveries"
```
Instead of:
```
subject: customer:gai_123
predicate: delivery_preference
object: {"value": "Friday"}
```

### 3. **Better Embeddings** (natural language > structured)
```python
# Before: embed("customer:gai_123 delivery_preference Friday")
# After:  embed("Gai Media prefers Friday deliveries")
```

### 4. **Full Context Preservation** (via source_text)
```
User: "Remember: Gai Media prefers Friday deliveries and NET30 payment terms"
```
Enables explainability - can show user exactly what they said.

### 5. **Multi-Entity Retrieval** (via related_entities)
```python
related_entities: ["customer:gai_123", "customer:tc_456"]
```
Enables entity overlap scoring for better relevance.

### 6. **Conflict Detection** (structured predicate)
```python
# Still works - compares structured fields
if memory1.subject == memory2.subject and memory1.predicate == memory2.predicate:
    # Conflict detected!
```

## Architecture Principles Maintained

✅ **Hexagonal Architecture** - Domain entity unchanged externally, repository adapts internally
✅ **Type Safety** - All fields properly typed with `str | None` and `list[str]`
✅ **Backward Compatibility** - New columns are nullable, existing data unaffected
✅ **Vision Alignment** - "Explainability" and "Epistemic Humility" principles

## Migration Path

1. **Run migration**: `make db-migrate`
2. **New memories** will have all three fields populated
3. **Existing memories** will have `NULL` for new fields (graceful degradation)
4. **Future enhancement**: Backfill `original_text` from structured triple if needed

## Example: Full Flow

### User Message
```
"Remember: Gai Media prefers Friday deliveries"
```

### Extraction
```python
triple = SemanticTriple(
    subject_entity_id="customer:gai_123",
    predicate="delivery_preference",
    object_value={"value": "Friday"}
)
```

### Memory Creation
```python
original_text = "Gai Media prefers Friday deliveries"  # Natural language
embedding = embed(original_text)  # Better semantic matching

memory = SemanticMemory(
    subject_entity_id="customer:gai_123",      # Structured
    predicate="delivery_preference",            # Structured
    object_value={"value": "Friday"},           # Structured
    original_text=original_text,                # Natural language
    source_text=message.content,                # Full context
    related_entities=["customer:gai_123"],      # Multi-entity
    embedding=embedding                         # Over natural language
)
```

### Retrieval
```python
# Fast structured query
memories = await repo.find_by_subject_predicate(
    subject="customer:gai_123",
    predicate="delivery_preference"
)

# Display
print(memory.original_text)  # "Gai Media prefers Friday deliveries"

# Provenance
print(memory.source_text)    # Full original message
```

## Summary

This implementation gives you **best of both worlds**:
- ✅ Fast structured queries (triples)
- ✅ Human-readable display (original_text)
- ✅ Better embeddings (natural language)
- ✅ Full context (source_text)
- ✅ Multi-entity support (related_entities)

The system now has both precision (structured) and understanding (natural language).
