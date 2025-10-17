# Architecture Overview

**How the Memory System is Structured**

---

## System Purpose

The Memory System transforms conversational interactions into structured, retrievable knowledge. It enables LLM agents to:

- **Remember** conversations across sessions
- **Resolve** entity mentions ("Acme" → `customer:uuid`)
- **Learn** facts from conversations ("Acme prefers Friday deliveries")
- **Retrieve** relevant memories when needed
- **Adapt** confidence based on validation and decay

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       API Layer (FastAPI)                    │
│  • REST endpoints (/chat, /consolidate, /procedural)        │
│  • Request/Response models (Pydantic)                        │
│  • Dependency injection                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Application Layer                          │
│  • Use Cases (orchestrators)                                 │
│  • DTOs (data transfer objects)                              │
│  • Coordinate domain services + repositories                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    Domain Layer (Pure Python)                │
│  • Entities (CanonicalEntity, SemanticMemory, etc.)         │
│  • Services (business logic)                                 │
│  • Ports (interfaces/contracts)                              │
│  • Value Objects (immutable data)                            │
│  • NO infrastructure dependencies                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                 Infrastructure Layer                         │
│  • Repositories (PostgreSQL access)                          │
│  • LLM Service (OpenAI integration)                          │
│  • Embedding Service (OpenAI embeddings)                     │
│  • Database models (SQLAlchemy)                              │
│  • DI Container (dependency-injector)                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                ┌──────▼──────┐
                │  PostgreSQL  │
                │  + pgvector  │
                └──────────────┘
```

---

## Design Principles

### 1. Hexagonal Architecture (Ports & Adapters)

**Domain layer is pure Python** - no database, no HTTP, no external dependencies.

```python
# ✅ Domain layer depends on interfaces (ports)
class EntityResolutionService:
    def __init__(self, entity_repo: IEntityRepository):  # Port (ABC)
        self.entity_repo = entity_repo

# ✅ Infrastructure provides implementations (adapters)
class PostgresEntityRepository(IEntityRepository):  # Adapter
    def __init__(self, session: AsyncSession):
        self.session = session
```

**Benefits**:
- Domain logic testable without database
- Easy to swap implementations (e.g., PostgreSQL → MongoDB)
- Business rules isolated from technical concerns

### 2. Domain-Driven Design (Lite)

**Rich domain models with behavior**:

```python
class SemanticMemory:
    """Domain entity with business logic."""

    def reinforce(self, boost: float = 0.05) -> None:
        """Increase confidence from validation (capped at 0.95)."""
        self.confidence = min(0.95, self.confidence + boost)
        self.reinforcement_count += 1
        self.last_validated_at = datetime.now(UTC)
```

Not anemic data containers - entities know how to operate on themselves.

### 3. Async-First

**All I/O operations are async** for high throughput:

```python
# ✅ Async repository methods
async def create(self, memory: SemanticMemory) -> SemanticMemory:
    ...

# ✅ Async service methods
async def resolve_entity(self, mention: str) -> ResolutionResult:
    ...
```

**Benefits**:
- Handle 10x+ concurrent requests on same hardware
- Non-blocking I/O for database, LLM, embeddings
- FastAPI natively async

### 4. Type Safety (100% Coverage)

**Every public function has type hints**:

```python
async def resolve(
    self,
    mention: str,
    user_id: str,
    context: ResolutionContext,
) -> ResolutionResult:
    ...
```

**Enforced** by mypy in strict mode (CI/CD blocks untyped code).

### 5. Dependency Injection

**Dependencies injected via constructor**:

```python
class ProcessChatMessageUseCase:
    def __init__(
        self,
        chat_repository: IChatEventRepository,
        resolve_entities: ResolveEntitiesUseCase,
        extract_semantics: ExtractSemanticsUseCase,
        # ... all dependencies explicit
    ):
        self.chat_repo = chat_repository
        self.resolve_entities = resolve_entities
        # ...
```

**Benefits**:
- Testable (inject mocks)
- Clear dependencies
- Managed by `src/infrastructure/di/container.py`

---

## Layer Responsibilities

### API Layer (`src/api/`)

**Purpose**: HTTP interface, request/response handling

**Components**:
- **Routes** (`routes/chat.py`, `routes/consolidation.py`, `routes/procedural.py`)
  - Define endpoints
  - Handle HTTP concerns (status codes, headers)
  - Convert HTTP → DTOs → Domain

- **Models** (`models/chat.py`, `models/consolidation.py`)
  - Pydantic request/response schemas
  - Validation rules
  - OpenAPI documentation

- **Dependencies** (`dependencies.py`)
  - FastAPI dependency functions
  - Wire DI container to endpoints
  - Session management, authentication

**Example**:
```python
@router.post("/api/v1/chat/simplified")
async def simplified_chat(
    request: SimplifiedChatRequest,
    use_case: ProcessChatMessageUseCase = Depends(get_process_chat_use_case),
) -> SimplifiedChatResponse:
    # Convert HTTP → DTO
    input_dto = ProcessChatMessageInput(
        content=request.message,
        user_id=request.user_id,
        session_id=request.session_id,
        role="user",
    )

    # Execute business logic
    output = await use_case.execute(input_dto)

    # Convert DTO → HTTP
    return SimplifiedChatResponse(...)
```

**Key Files**:
- `src/api/main.py` - FastAPI app setup, middleware, lifecycle
- `src/api/routes/chat.py` - Chat endpoints (189 lines)
- `src/api/routes/consolidation.py` - Consolidation endpoints (344 lines)
- `src/api/dependencies.py` - Dependency injection wiring (282 lines)

---

### Application Layer (`src/application/`)

**Purpose**: Orchestrate domain services, coordinate workflows

**Components**:
- **Use Cases** (`use_cases/`)
  - Orchestrators for complex workflows
  - Coordinate multiple domain services
  - Return DTOs (not domain entities)

- **DTOs** (`dtos/chat_dtos.py`)
  - Data Transfer Objects
  - Cross-layer data contracts
  - Immutable, serializable

**Example - ProcessChatMessageUseCase**:
```python
class ProcessChatMessageUseCase:
    """Orchestrator for chat message processing."""

    async def execute(self, input_dto: ProcessChatMessageInput) -> ProcessChatMessageOutput:
        # Step 1: Store chat message
        message = await self.chat_repo.create(...)

        # Step 2: Resolve entities (Phase 1A)
        entities_result = await self.resolve_entities.execute(...)

        # Step 3: Extract semantics (Phase 1B)
        semantics_result = await self.extract_semantics.execute(...)

        # Step 4: Augment with domain facts (Phase 1C)
        domain_facts = await self.augment_with_domain.execute(...)

        # Step 5: Score memories (Phase 1D)
        retrieved_memories = await self.score_memories.execute(...)

        # Step 6: Generate reply
        reply = await self.llm_reply_generator.generate(...)

        return ProcessChatMessageOutput(...)
```

**Key Files**:
- `src/application/use_cases/process_chat_message.py` - Main orchestrator (279 lines)
- `src/application/use_cases/resolve_entities.py` - Entity resolution use case (230 lines)
- `src/application/use_cases/extract_semantics.py` - Semantic extraction use case (308 lines)
- `src/application/use_cases/augment_with_domain.py` - Domain augmentation (99 lines)
- `src/application/use_cases/score_memories.py` - Memory scoring (224 lines)

---

### Domain Layer (`src/domain/`)

**Purpose**: Business logic, entities, rules (pure Python, no infrastructure)

**Components**:

1. **Entities** (`entities/`)
   - Core business objects with identity
   - Mutable state, lifecycle management
   - Rich behavior (not anemic)

   ```python
   # src/domain/entities/semantic_memory.py
   class SemanticMemory:
       memory_id: int | None
       subject_entity_id: str
       predicate: str
       object_value: Any
       confidence: float
       reinforcement_count: int
       created_at: datetime
       last_validated_at: datetime | None

       def reinforce(self, boost: float) -> None: ...
       def calculate_effective_confidence(self) -> float: ...
   ```

   **Entities** (6 total):
   - `CanonicalEntity` - Resolved entities (customers, products, etc.)
   - `EntityAlias` - Alternative names for entities
   - `ChatMessage` - Raw conversation events
   - `SemanticMemory` - Extracted facts (triples)
   - `ProceduralMemory` - Learned patterns
   - `MemorySummary` - Consolidated memory summaries

2. **Services** (`services/`)
   - Stateless business logic
   - Coordinate between entities and repositories
   - Complex algorithms

   ```python
   # src/domain/services/entity_resolution_service.py
   class EntityResolutionService:
       """5-stage hybrid entity resolution."""

       async def resolve(self, mention: str, user_id: str) -> ResolutionResult:
           # Stage 1: Exact match
           if exact := await self._exact_match(mention):
               return exact

           # Stage 2: Alias lookup
           if alias := await self._alias_lookup(mention, user_id):
               return alias

           # Stage 3: Fuzzy matching (pg_trgm)
           if fuzzy := await self._fuzzy_match(mention):
               return fuzzy

           # Stage 4: LLM coreference
           if coref := await self._llm_coreference(mention, context):
               return coref

           # Stage 5: Lazy creation
           return await self._lazy_create(mention, user_id)
   ```

   **Services** (16 total):
   - `EntityResolutionService` - 5-stage entity resolution
   - `SemanticExtractionService` - LLM-based triple extraction
   - `MemoryValidationService` - Confidence decay, reinforcement
   - `ConflictDetectionService` - Detect memory conflicts
   - `MultiSignalScorer` - Multi-signal memory retrieval
   - `DomainAugmentationService` - Query domain database
   - `ConsolidationService` - Consolidate memories into summaries
   - `ProceduralMemoryService` - Extract procedural patterns
   - `LLMReplyGenerator` - Generate natural language replies
   - `MentionExtractor` - Extract entity mentions from text
   - ... and 6 more

3. **Ports** (`ports/`)
   - Interfaces (Abstract Base Classes)
   - Define contracts without implementation
   - Dependency inversion

   ```python
   # src/domain/ports/semantic_memory_repository.py
   class ISemanticMemoryRepository(ABC):
       @abstractmethod
       async def create(self, memory: SemanticMemory) -> SemanticMemory:
           """Create a new semantic memory."""
           pass

       @abstractmethod
       async def find_similar(
           self,
           query_embedding: list[float],
           user_id: str,
           limit: int = 10,
       ) -> list[tuple[SemanticMemory, float]]:
           """Find memories similar to query embedding."""
           pass
   ```

   **Ports** (11 total):
   - `IEntityRepository`
   - `ISemanticMemoryRepository`
   - `IProceduralMemoryRepository`
   - `IChatEventRepository`
   - `ISummaryRepository`
   - `IEpisodicMemoryRepository`
   - `IOntologyRepository`
   - `IEmbeddingService`
   - `ILLMService`
   - `ILLMProviderPort`
   - `DomainDatabasePort`

4. **Value Objects** (`value_objects/`)
   - Immutable data structures
   - No identity (equality by value)
   - Frozen dataclasses

   ```python
   @dataclass(frozen=True)
   class ResolutionResult:
       """Result of entity resolution."""
       entity_id: str
       confidence: float
       method: str  # "exact_match", "alias", "fuzzy", "llm", "lazy_creation"
       canonical_name: str
   ```

   **Value Objects** (14 total):
   - `ResolutionResult`, `EntityMention`, `EntityReference`
   - `SemanticTriple`, `MemoryConflict`, `MemoryCandidate`
   - `QueryContext`, `RetrievalResult`, `DomainFact`
   - `ConsolidationScope`, `ReplyContext`, `RecentChatEvent`
   - ... and 2 more

**Key Metrics**:
- **Domain Entities**: 6 files, 682 lines
- **Domain Services**: 16 files, 3,475 lines
- **Domain Ports**: 11 files, 664 lines
- **Value Objects**: 14 files, 1,210 lines
- **Total Domain**: ~6,000 lines of pure business logic

---

### Infrastructure Layer (`src/infrastructure/`)

**Purpose**: Adapt external systems (database, LLM, etc.) to domain ports

**Components**:

1. **Database** (`database/`)
   - SQLAlchemy models (ORM)
   - Alembic migrations
   - Session management

   ```python
   # src/infrastructure/database/models.py
   class SemanticMemoryModel(Base):
       __tablename__ = "semantic_memories"
       __table_args__ = {"schema": "app"}

       memory_id = Column(Integer, primary_key=True)
       user_id = Column(String, nullable=False, index=True)
       subject_entity_id = Column(String, nullable=False, index=True)
       predicate = Column(String, nullable=False)
       object_value = Column(JSON, nullable=False)
       confidence = Column(Float, nullable=False)
       embedding = Column(Vector(1536))  # pgvector
       # ... more fields
   ```

2. **Repositories** (`database/repositories/`)
   - Implement domain ports
   - Handle SQL queries
   - Convert between domain entities and database models

   ```python
   # src/infrastructure/database/repositories/semantic_memory_repository.py
   class SemanticMemoryRepository(ISemanticMemoryRepository):
       async def find_similar(
           self, query_embedding: list[float], user_id: str, limit: int = 10
       ) -> list[tuple[SemanticMemory, float]]:
           # Use pgvector cosine similarity
           stmt = text("""
               SELECT *, 1 - (embedding <=> :query_embedding::vector) as similarity
               FROM app.semantic_memories
               WHERE user_id = :user_id
               ORDER BY embedding <=> :query_embedding::vector
               LIMIT :limit
           """)

           result = await self.session.execute(stmt, {
               "query_embedding": query_embedding,
               "user_id": user_id,
               "limit": limit,
           })

           return [(self._to_domain(row), row.similarity) for row in result]
   ```

3. **LLM** (`llm/`)
   - OpenAI API integration
   - Prompt templates
   - Response parsing

   ```python
   # src/infrastructure/llm/openai_llm_service.py
   class OpenAILLMService(ILLMService):
       async def complete(self, prompt: str, **kwargs) -> str:
           response = await self.client.chat.completions.create(
               model="gpt-4o",
               messages=[{"role": "user", "content": prompt}],
               **kwargs,
           )
           return response.choices[0].message.content
   ```

4. **Embeddings** (`embedding/`)
   - OpenAI embeddings API
   - 1536-dimensional vectors

5. **DI Container** (`di/container.py`)
   - Wires everything together
   - Factories for services, repositories
   - Lifecycle management

**Key Files**:
- `src/infrastructure/database/models.py` - Database schema (10 tables, 655 lines)
- `src/infrastructure/database/repositories/` - 8 repository implementations
- `src/infrastructure/di/container.py` - Dependency injection (398 lines)
- `src/infrastructure/llm/openai_llm_service.py` - LLM integration
- `src/infrastructure/embedding/openai_embedding_service.py` - Embedding service

---

## Data Flow Example

**User sends**: "Acme Corporation prefers Friday deliveries"

```
1. API Layer (routes/chat.py)
   ↓ Receives HTTP POST /api/v1/chat/simplified
   ↓ Validates request with Pydantic
   ↓ Creates ProcessChatMessageInput DTO

2. Application Layer (use_cases/process_chat_message.py)
   ↓ Orchestrates workflow:
   ↓ a) Store chat event → ChatRepository
   ↓ b) Resolve entities → ResolveEntitiesUseCase
   ↓    - "Acme Corporation" → customer:uuid (Stage 1: exact or Stage 5: lazy creation)
   ↓ c) Extract semantics → ExtractSemanticsUseCase
   ↓    - LLM extracts: (customer:uuid, "delivery_preference", "Friday")
   ↓ d) Generate reply → LLMReplyGenerator

3. Domain Layer (services/)
   ↓ EntityResolutionService.resolve("Acme Corporation")
   ↓   - Check exact match (not found)
   ↓   - Check aliases (not found)
   ↓   - Fuzzy match (not found)
   ↓   - Lazy create: new CanonicalEntity(canonical_name="Acme Corporation")
   ↓
   ↓ SemanticExtractionService.extract(...)
   ↓   - LLM prompt: "Extract triples from: Acme Corporation prefers Friday deliveries"
   ↓   - Parse response: [(subject, predicate, object), ...]
   ↓   - Create SemanticMemory entities
   ↓   - Generate embeddings for each memory

4. Infrastructure Layer (repositories/)
   ↓ EntityRepository.create(entity)
   ↓   - INSERT INTO app.canonical_entities ...
   ↓
   ↓ SemanticMemoryRepository.create(memory)
   ↓   - INSERT INTO app.semantic_memories (subject, predicate, object, embedding, ...)

5. Database (PostgreSQL)
   ↓ Persist:
   ↓   - 1 CanonicalEntity row
   ↓   - 1 SemanticMemory row (with pgvector embedding)
   ↓   - 1 ChatEvent row

6. Response
   ← Return ProcessChatMessageOutput DTO
   ← API converts to SimplifiedChatResponse
   ← JSON response to client
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI 0.109+ | REST API, async, OpenAPI docs |
| **Language** | Python 3.13 | Modern async, type hints |
| **Database** | PostgreSQL 15 | Relational database |
| **Vector Search** | pgvector | Similarity search for embeddings |
| **ORM** | SQLAlchemy 2.0 (async) | Database access |
| **Migrations** | Alembic | Schema versioning |
| **Embeddings** | OpenAI text-embedding-3-small | 1536-dim vectors |
| **LLM** | OpenAI gpt-4o | Semantic extraction, replies |
| **DI** | dependency-injector | Dependency injection |
| **Logging** | structlog | Structured JSON logging |
| **Testing** | pytest + httpx | Unit, integration, E2E |
| **Type Checking** | mypy (strict) | Static type analysis |
| **Linting** | Ruff | Fast linter + formatter |
| **Dependency Mgmt** | Poetry | Lock file, virtual env |

---

## Code Statistics

```
Domain Layer:        ~6,000 lines (entities, services, ports, value objects)
Application Layer:   ~1,000 lines (use cases, DTOs)
API Layer:           ~1,700 lines (routes, models, dependencies)
Infrastructure:      ~3,000 lines (repositories, LLM, embedding, DI)
----------------------------------------------------------------------
Total Production:    ~12,000 lines

Tests:                26 files, 337 test functions
Documentation:        100+ pages (vision, design, guides)
```

---

## Architectural Decisions

### Why Hexagonal Architecture?

- **Testability**: Domain logic testable without database/HTTP
- **Flexibility**: Swap PostgreSQL for MongoDB without touching domain
- **Clarity**: Clear boundaries between layers

### Why Async-First?

- **Throughput**: Handle 10x+ concurrent requests
- **Latency**: Non-blocking I/O for database, LLM, embeddings
- **Modern**: FastAPI and SQLAlchemy 2.0 are natively async

### Why Dependency Injection?

- **Testability**: Inject mocks for unit tests
- **Maintainability**: Explicit dependencies
- **Flexibility**: Easy to swap implementations

### Why Type Safety?

- **Correctness**: Catch errors at compile time
- **Maintainability**: Types document intent
- **Refactoring**: Safe large-scale changes

---

## Next Steps

- **Understand the Database Schema** → [docs_new/database/SCHEMA.md](../database/SCHEMA.md)
- **Learn the API Endpoints** → [docs_new/api/ENDPOINTS.md](../api/ENDPOINTS.md)
- **Write Tests** → [docs_new/testing/GUIDE.md](../testing/GUIDE.md)
- **Read Development Workflow** → [docs_new/development/WORKFLOW.md](../development/WORKFLOW.md)

---

*This architecture is designed for production: testable, maintainable, and scalable.*
