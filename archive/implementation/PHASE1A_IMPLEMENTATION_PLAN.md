# Phase 1A Implementation Plan

**Date**: 2025-10-15
**Duration**: Week 1-2
**Status**: In Progress

---

## Overview

Phase 1A establishes the foundation: chat event storage and entity resolution. This is the most critical phase as it sets architectural patterns for the entire system.

---

## Architecture Decisions

### 1. Hexagonal Architecture (Ports & Adapters)

```
┌─────────────────────────────────────────────────────┐
│                    API Layer                        │
│  (FastAPI routes, Pydantic models, HTTP concerns)   │
└──────────────────┬──────────────────────────────────┘
                   │ depends on ↓
┌─────────────────────────────────────────────────────┐
│              Application Layer                      │
│   (Use cases, orchestration, transactions)          │
└──────────────────┬──────────────────────────────────┘
                   │ depends on ↓
┌─────────────────────────────────────────────────────┐
│                Domain Layer                         │
│  (Entities, value objects, domain services, ports)  │
│  ← Pure business logic, no framework dependencies   │
└──────────────────┬──────────────────────────────────┘
                   ↑ implements
┌─────────────────────────────────────────────────────┐
│            Infrastructure Layer                     │
│   (Repositories, LLM service, embedding service)    │
└─────────────────────────────────────────────────────┘
```

**Benefits**:
- Domain logic is framework-agnostic (testable without database/API)
- Easy to swap implementations (e.g., switch from OpenAI to local LLM)
- Clear boundaries and responsibilities
- Follows Dependency Inversion Principle

### 2. Repository Pattern

**Interface** (domain/ports/):
```python
class IEntityRepository(Protocol):
    async def find_by_canonical_name(self, name: str) -> Optional[CanonicalEntity]: ...
    async def find_by_alias(self, alias: str, user_id: Optional[str]) -> Optional[CanonicalEntity]: ...
    async def create(self, entity: CanonicalEntity) -> CanonicalEntity: ...
```

**Implementation** (infrastructure/database/repositories/):
- Maps between domain entities and SQLAlchemy models
- Handles all SQL/ORM concerns
- Returns domain objects (not ORM models)

### 3. Value Objects for Type Safety

```python
@dataclass(frozen=True)
class EntityMention:
    """Immutable value object for entity mentions in text."""
    text: str
    position: int
    is_pronoun: bool
    context: str

@dataclass(frozen=True)
class ResolutionResult:
    """Result of entity resolution."""
    entity_id: str
    confidence: float
    method: ResolutionMethod  # exact | alias | fuzzy | coreference | domain_db
    metadata: dict[str, Any]
```

### 4. Dependency Injection with Container

Use `dependency-injector` for clean DI:

```python
class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    # Infrastructure
    db_session = providers.Resource(get_db_session)
    llm_service = providers.Singleton(OpenAILLMService, api_key=config.openai_api_key)

    # Repositories
    entity_repository = providers.Factory(EntityRepository, session=db_session)

    # Domain Services
    entity_resolution_service = providers.Factory(
        EntityResolutionService,
        entity_repo=entity_repository,
        llm_service=llm_service
    )

    # Use Cases
    process_message_use_case = providers.Factory(
        ProcessChatMessageUseCase,
        entity_resolution=entity_resolution_service,
        entity_repo=entity_repository
    )
```

---

## Implementation Steps

### **Step 1: Domain Layer** (Day 1-2)

#### 1.1 Value Objects (`domain/value_objects/`)

- [ ] `EntityMention` - Represents a mention of an entity in text
- [ ] `ResolutionResult` - Result of entity resolution
- [ ] `EntityReference` - Reference to external domain entity
- [ ] `ConversationContext` - Context for resolution (recent messages, entities)

#### 1.2 Domain Entities (`domain/entities/`)

- [ ] `ChatMessage` - Domain representation of a chat message
- [ ] `CanonicalEntity` - Domain representation of resolved entity
- [ ] `EntityAlias` - Alias mapping

#### 1.3 Port Interfaces (`domain/ports/`)

- [ ] `IEntityRepository` - Entity persistence interface
- [ ] `IChatEventRepository` - Chat event persistence
- [ ] `ILLMService` - LLM service for coreference resolution
- [ ] `IEmbeddingService` - Embedding generation
- [ ] `IFuzzyMatcher` - Fuzzy matching interface (pg_trgm wrapper)

#### 1.4 Domain Services (`domain/services/`)

- [ ] `EntityResolutionService` - **Core**: Implements 5-stage hybrid algorithm
  - Stage 1: Exact match (70%)
  - Stage 2: User alias (15%)
  - Stage 3: Fuzzy match via pg_trgm (10%)
  - Stage 4: Coreference via LLM (5%)
  - Stage 5: Domain DB lookup (lazy entity creation)

#### 1.5 Custom Exceptions (`domain/exceptions.py`)

- [ ] `EntityResolutionError`
- [ ] `AmbiguousEntityError`
- [ ] `InvalidMessageError`

---

### **Step 2: Infrastructure Layer** (Day 3-4)

#### 2.1 Repositories (`infrastructure/database/repositories/`)

- [ ] `EntityRepository` - Implements `IEntityRepository`
  - `find_by_canonical_name(name: str)` - Exact match
  - `find_by_alias(alias: str, user_id: Optional[str])` - Alias lookup
  - `fuzzy_search(text: str, threshold: float)` - pg_trgm search
  - `create(entity: CanonicalEntity)` - Create new entity
  - `create_alias(entity_id: str, alias: EntityAlias)` - Learn alias

- [ ] `ChatEventRepository` - Implements `IChatEventRepository`
  - `create(message: ChatMessage)` - Store chat event
  - `get_recent(user_id: str, limit: int)` - Get conversation history

#### 2.2 LLM Service (`infrastructure/llm/`)

- [ ] `OpenAILLMService` - Implements `ILLMService`
  - `resolve_coreference(mention: str, context: ConversationContext)` - Coreference resolution
  - Prompt engineering for coreference
  - Error handling and retry logic
  - Cost tracking

#### 2.3 Embedding Service (`infrastructure/embedding/`)

- [ ] `OpenAIEmbeddingService` - Implements `IEmbeddingService`
  - `generate_embedding(text: str)` - Generate embedding
  - Batching support
  - Rate limiting

#### 2.4 Fuzzy Matcher (`infrastructure/database/fuzzy_matcher.py`)

- [ ] `PostgresFuzzyMatcher` - Implements `IFuzzyMatcher`
  - Uses `similarity(text, query)` from pg_trgm
  - Configurable threshold (default 0.6)

---

### **Step 3: Application Layer** (Day 5-6)

#### 3.1 Use Cases (`application/use_cases/`)

- [ ] `ProcessChatMessageUseCase`
  - Input: `ProcessChatMessageInput` (user_id, session_id, content)
  - Output: `ProcessChatMessageOutput` (event_id, resolved_entities)
  - Orchestrates:
    1. Extract entity mentions from message
    2. Resolve each mention via `EntityResolutionService`
    3. Store chat event with resolved entities
    4. Return result

#### 3.2 DTOs (`application/dtos/`)

- [ ] `ProcessChatMessageInput`
- [ ] `ProcessChatMessageOutput`
- [ ] `ResolvedEntityDTO`

---

### **Step 4: API Layer** (Day 7)

#### 4.1 Pydantic Models (`api/models/chat.py`)

- [ ] `ChatMessageRequest`
  ```python
  class ChatMessageRequest(BaseModel):
      session_id: UUID
      content: str
      role: Literal["user", "assistant"] = "user"
      metadata: Optional[dict[str, Any]] = None
  ```

- [ ] `ChatMessageResponse`
  ```python
  class ChatMessageResponse(BaseModel):
      event_id: int
      session_id: UUID
      created_at: datetime
      resolved_entities: list[ResolvedEntityResponse]
  ```

- [ ] `ResolvedEntityResponse`

#### 4.2 Routes (`api/routes/chat.py`)

- [ ] `POST /api/v1/chat/message` - Process chat message
  - Delegates to `ProcessChatMessageUseCase`
  - Handles authentication (user_id from JWT or header)
  - Error handling and HTTP status codes

#### 4.3 Dependencies (`api/dependencies.py`)

- [ ] `get_current_user()` - Extract user_id from auth
- [ ] `get_process_message_use_case()` - Inject use case from container

---

### **Step 5: Testing** (Day 8-10)

#### 5.1 Unit Tests (`tests/unit/domain/`)

- [ ] `test_entity_resolution_service.py`
  - Test each stage independently
  - Mock repositories and LLM service
  - Verify deterministic stages work offline
  - Test confidence calculations

- [ ] `test_value_objects.py`
  - Immutability
  - Validation

#### 5.2 Integration Tests (`tests/integration/`)

- [ ] `test_entity_repository.py`
  - Test against real database (test container)
  - Verify pg_trgm fuzzy matching
  - Test transaction handling

- [ ] `test_chat_event_repository.py`

#### 5.3 E2E Tests (`tests/e2e/`)

- [ ] `test_chat_api.py`
  - Full request/response cycle
  - Test entity resolution in realistic scenarios
  - Verify database state after API call

---

## Code Quality Standards

### Type Safety
```python
# ✅ Good: Full type hints
async def resolve_entity(
    self,
    mention: EntityMention,
    context: ConversationContext
) -> ResolutionResult:
    ...

# ❌ Bad: No type hints
async def resolve_entity(self, mention, context):
    ...
```

### Docstrings (Google Style)
```python
async def resolve_entity(
    self,
    mention: EntityMention,
    context: ConversationContext
) -> ResolutionResult:
    """Resolve an entity mention to a canonical entity.

    Uses a 5-stage hybrid algorithm:
    1. Exact match on canonical name
    2. User-specific alias lookup
    3. Fuzzy match using pg_trgm
    4. Coreference resolution via LLM
    5. Domain database lookup (lazy creation)

    Args:
        mention: The entity mention to resolve
        context: Conversation context for coreference

    Returns:
        ResolutionResult with entity_id, confidence, and method

    Raises:
        AmbiguousEntityError: If multiple entities match with equal confidence
        EntityResolutionError: If resolution fails
    """
```

### Error Handling
```python
# ✅ Good: Specific exceptions
try:
    entity = await self.repository.find_by_name(name)
except DatabaseError as e:
    logger.error("Failed to query entity", name=name, error=str(e))
    raise EntityResolutionError(f"Database error: {e}") from e

# ❌ Bad: Catching everything
try:
    entity = await self.repository.find_by_name(name)
except Exception:
    pass
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

# ✅ Good: Structured
logger.info(
    "entity_resolved",
    entity_id=result.entity_id,
    method=result.method,
    confidence=result.confidence,
    mention=mention.text
)

# ❌ Bad: String concatenation
logger.info(f"Resolved {mention.text} to {result.entity_id}")
```

---

## Success Criteria

**Phase 1A is complete when**:

1. ✅ `POST /api/v1/chat/message` endpoint functional
2. ✅ Entity resolution working for all 5 stages
3. ✅ Chat events persisted to database
4. ✅ Unit test coverage ≥ 80%
5. ✅ Integration tests passing
6. ✅ E2E test for full chat flow passing
7. ✅ All mypy checks passing (strict mode)
8. ✅ All ruff linting passing
9. ✅ Documentation updated

---

## Timeline

| Day | Focus | Deliverable |
|-----|-------|-------------|
| 1-2 | Domain layer | Value objects, entities, ports, services |
| 3-4 | Infrastructure | Repositories, LLM service, embedding service |
| 5-6 | Application | Use cases, DTOs |
| 7   | API | Routes, Pydantic models |
| 8-10 | Testing | Unit, integration, E2E tests |

---

**Next**: Begin Step 1 - Domain Layer implementation
