# Codebase Structure & Organization Guide

**Version:** 2.0 (Simplified Core)
**Purpose:** Prescriptive guide for implementing the intelligent memory system with extremely high code quality
**Status:** Ready for Implementation
**Scope:** Core project requirements only (memory + entity resolution + DB augmentation)

---

## Table of Contents

1. [Directory Structure](#directory-structure)
2. [Module Organization](#module-organization)
3. [Code Quality Standards](#code-quality-standards)
4. [Design Patterns & Principles](#design-patterns--principles)
5. [Testing Strategy](#testing-strategy)
6. [Configuration Management](#configuration-management)
7. [Dependency Management](#dependency-management)
8. [Development Workflow](#development-workflow)

---

## Directory Structure

### Complete Project Layout

```
intelligent-memory-system/
├── README.md
├── pyproject.toml                 # Poetry config, dependencies, tool configs
├── .python-version               # Python 3.11
├── .gitignore
├── .pre-commit-config.yaml       # Pre-commit hooks
├── Makefile                      # Common commands
│
├── docs/                         # Documentation
│   ├── architecture/             # Architecture documents (keep existing)
│   ├── api/                      # API documentation
│   ├── deployment/               # Deployment guides
│   └── development/              # Developer guides
│
├── scripts/                      # Utility scripts
│   ├── db/
│   │   ├── migrate.py           # Database migrations
│   │   ├── seed.py              # Seed data for development
│   │   └── backup.py            # Backup utilities
│   ├── dev/
│   │   ├── generate_test_data.py
│   │   └── benchmark.py
│   └── deployment/
│       ├── deploy.sh
│       └── health_check.py
│
├── sql/                          # SQL schemas and migrations
│   ├── schema/
│   │   ├── 001_domain_schema.sql
│   │   ├── 002_app_schema.sql
│   │   └── 003_indexes.sql
│   └── migrations/
│       └── README.md
│
├── config/                       # Configuration files
│   ├── development.yaml
│   ├── staging.yaml
│   ├── production.yaml
│   └── testing.yaml
│
├── src/                          # Main source code
│   └── intelligent_memory/       # Main package
│       │
│       ├── __init__.py
│       ├── __version__.py
│       │
│       ├── api/                  # HTTP API layer
│       │   ├── __init__.py
│       │   ├── main.py           # FastAPI app entrypoint
│       │   ├── dependencies.py   # Dependency injection
│       │   ├── middleware.py     # Request/response middleware
│       │   │
│       │   ├── routes/
│       │   │   ├── __init__.py
│       │   │   ├── chat.py       # POST /chat
│       │   │   ├── memory.py     # Memory CRUD
│       │   │   ├── entities.py   # Entity management
│       │   │   └── health.py     # Health checks
│       │   │
│       │   ├── schemas/          # Pydantic models (API contracts)
│       │   │   ├── __init__.py
│       │   │   ├── requests.py
│       │   │   ├── responses.py
│       │   │   └── common.py
│       │   │
│       │   └── errors/
│       │       ├── __init__.py
│       │       ├── handlers.py
│       │       └── exceptions.py
│       │
│       ├── core/                 # Core business logic
│       │   ├── __init__.py
│       │   │
│       │   ├── orchestration/    # Request orchestration
│       │   │   ├── __init__.py
│       │   │   ├── request_handler.py
│       │   │   ├── conversation_context.py  # ConversationContextManager
│       │   │   └── session.py
│       │   │
│       │   ├── intelligence/     # Intelligence components
│       │   │   ├── __init__.py
│       │   │   │
│       │   │   ├── entity_resolution/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── resolver.py        # EntityResolver
│       │   │   │   ├── ner_extractor.py   # NER extraction
│       │   │   │   ├── matcher.py         # Entity matching
│       │   │   │   ├── disambiguator.py   # Disambiguation logic
│       │   │   │   └── models.py          # ResolvedEntity, Match
│       │   │   │
│       │   │   ├── context_assembly/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── assembler.py       # ContextAssembler
│       │   │   │   ├── formatter.py       # Format memories + DB facts
│       │   │   │   └── models.py          # AssembledContext
│       │   │   │
│       │   │   └── response_generation/
│       │   │       ├── __init__.py
│       │   │       ├── generator.py       # ResponseGenerator
│       │   │       ├── prompt_builder.py  # LLM prompt construction
│       │   │       ├── quality_gates.py   # Response validation
│       │   │       └── models.py          # GeneratedResponse
│       │   │
│       │   └── memory/               # Memory management
│       │       ├── __init__.py
│       │       ├── store.py          # MemoryStore
│       │       ├── retriever.py      # MemoryRetriever
│       │       ├── consolidator.py   # MemoryConsolidator
│       │       ├── embeddings.py     # Embedding generation
│       │       └── models.py         # Memory, MemorySummary
│       │
│       ├── infrastructure/       # Infrastructure layer
│       │   ├── __init__.py
│       │   │
│       │   ├── database/
│       │   │   ├── __init__.py
│       │   │   ├── connection.py     # DB connection pool
│       │   │   ├── wrapper.py        # DatabaseWrapper
│       │   │   ├── query_builder.py  # Safe query construction
│       │   │   │
│       │   │   └── repositories/     # Repository pattern
│       │   │       ├── __init__.py
│       │   │       ├── customer.py   # CustomerRepository
│       │   │       ├── invoice.py    # InvoiceRepository
│       │   │       ├── payment.py    # PaymentRepository
│       │   │       └── base.py       # Base repository
│       │   │
│       │   ├── cache/
│       │   │   ├── __init__.py
│       │   │   ├── redis_client.py   # Redis connection
│       │   │   ├── cache_manager.py  # Caching layer
│       │   │   └── decorators.py     # @cache decorator
│       │   │
│       │   ├── llm/
│       │   │   ├── __init__.py
│       │   │   ├── client.py         # LLM client wrapper
│       │   │   ├── router.py         # GPT-4 vs GPT-3.5 routing
│       │   │   ├── fallback.py       # Fallback strategies
│       │   │   └── models.py
│       │   │
│       │   ├── background/           # Background tasks
│       │   │   ├── __init__.py
│       │   │   ├── task_manager.py   # Simple async task execution
│       │   │   ├── memory_tasks.py   # Memory storage tasks
│       │   │   └── consolidation_tasks.py  # Consolidation tasks
│       │   │
│       │   └── monitoring/
│       │       ├── __init__.py
│       │       ├── metrics.py        # Metrics collection
│       │       ├── logging_config.py
│       │       └── tracing.py        # Distributed tracing
│       │
│       ├── domain/                   # Domain models
│       │   ├── __init__.py
│       │   ├── customer.py
│       │   ├── sales_order.py
│       │   ├── invoice.py
│       │   ├── work_order.py
│       │   ├── payment.py
│       │   └── base.py               # Base domain model
│       │
│       ├── shared/                   # Shared utilities
│       │   ├── __init__.py
│       │   ├── types.py              # Custom types
│       │   ├── constants.py
│       │   ├── exceptions.py
│       │   ├── utils.py
│       │   ├── validators.py
│       │   └── security.py           # Security utilities
│       │
│       └── config/                   # Configuration management
│           ├── __init__.py
│           ├── settings.py           # Pydantic settings
│           ├── database.py           # DB config
│           ├── redis.py              # Redis config
│           └── llm.py                # LLM config
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   │
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_entity_resolver.py
│   │   ├── test_context_assembler.py
│   │   ├── test_response_generator.py
│   │   ├── test_memory_store.py
│   │   └── test_memory_retriever.py
│   │
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_chat_flow.py
│   │   ├── test_database.py
│   │   └── test_redis.py
│   │
│   ├── e2e/                      # End-to-end tests
│   │   ├── __init__.py
│   │   ├── test_scenarios.py     # Tests for all 18 core scenarios
│   │   └── test_api.py
│   │
│   ├── performance/              # Performance tests
│   │   ├── __init__.py
│   │   ├── test_latency.py
│   │   └── test_load.py
│   │
│   └── fixtures/                 # Test fixtures
│       ├── __init__.py
│       ├── mock_data.py
│       ├── mock_db.py
│       └── mock_llm.py
│
└── benchmarks/                   # Performance benchmarks
    ├── __init__.py
    ├── entity_resolution.py
    ├── memory_retrieval.py
    └── end_to_end.py
```

---

## Module Organization

### Core Principles

1. **One class per file** (except closely related dataclasses)
2. **Explicit dependencies** (no circular imports)
3. **Interface-first design** (ABC for base classes)
4. **Dependency injection** (constructor injection preferred)
5. **Immutability where possible** (dataclasses with frozen=True)

### Module Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| **Module** | `snake_case.py` | `entity_resolver.py` |
| **Class** | `PascalCase` | `EntityResolver` |
| **Function** | `snake_case()` | `resolve_entity()` |
| **Constant** | `UPPER_SNAKE_CASE` | `MAX_RETRY_ATTEMPTS` |
| **Private** | `_leading_underscore` | `_internal_method()` |
| **Type Alias** | `PascalCase` | `EntityID = str` |

### File Structure Template

Every Python file follows this structure:

```python
"""
Module: intelligent_memory.core.intelligence.entity_resolution.resolver

Purpose: Resolves natural language entity references to database entities.

Architecture: See System_Flow_Diagram_SIMPLIFIED.md

Dependencies:
    - spacy: NER extraction
    - fuzzywuzzy: Fuzzy string matching
    - intelligent_memory.infrastructure.database: DB access

Author: [Team]
Created: 2024
"""

# Standard library imports
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging

# Third-party imports
import spacy
from fuzzywuzzy import fuzz

# Local imports (use absolute imports)
from intelligent_memory.core.orchestration.conversation_context import ConversationContext
from intelligent_memory.infrastructure.database.wrapper import DatabaseWrapper
from intelligent_memory.shared.exceptions import EntityResolutionError
from intelligent_memory.shared.types import EntityID

# Constants
MAX_FUZZY_CANDIDATES = 5
FUZZY_MATCH_THRESHOLD = 0.85

# Type aliases
ConfidenceScore = float

# Logger
logger = logging.getLogger(__name__)


# Data classes (models)
@dataclass(frozen=True)
class ResolvedEntity:
    """
    Result of entity resolution.

    Attributes:
        entity_id: Unique identifier
        entity_type: Type (customer, invoice, etc.)
        entity_name: Canonical name
        confidence: Resolution confidence (0-1)
        disambiguation_needed: Whether user confirmation needed
        candidates: Alternative matches if ambiguous
    """
    entity_id: EntityID
    entity_type: str
    entity_name: str
    confidence: ConfidenceScore
    disambiguation_needed: bool
    candidates: List['Match'] = field(default_factory=list)

    def __post_init__(self):
        """Validate after initialization."""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be 0-1, got {self.confidence}")


# Interfaces (abstract base classes)
class EntityResolverInterface(ABC):
    """Interface for entity resolution strategies."""

    @abstractmethod
    def resolve(self, text: str, context: ConversationContext) -> List[ResolvedEntity]:
        """Resolve entities from text."""
        pass


# Main implementation
class EntityResolver(EntityResolverInterface):
    """
    Resolves natural language entity references to database entities.

    Strategy:
        1. NER extraction (spaCy)
        2. Exact match lookup
        3. Fuzzy match (if no exact match)
        4. Disambiguation (if multiple matches)
        5. Confidence scoring

    Example:
        >>> resolver = EntityResolver(db_wrapper, nlp_model)
        >>> entities = resolver.resolve("Delta Industries", context)
        >>> assert entities[0].entity_name == "Delta Industries"

    Thread Safety: This class is thread-safe.
    """

    def __init__(
        self,
        db: DatabaseWrapper,
        nlp: spacy.language.Language,
    ):
        """
        Initialize resolver.

        Args:
            db: Database wrapper for queries
            nlp: spaCy NLP model for NER

        Raises:
            ValueError: If db or nlp is None
        """
        if db is None or nlp is None:
            raise ValueError("db and nlp are required")

        self._db = db
        self._nlp = nlp

        logger.info("EntityResolver initialized")

    def resolve(
        self,
        text: str,
        context: ConversationContext
    ) -> List[ResolvedEntity]:
        """
        Resolve entities from user text.

        Args:
            text: User query text
            context: Current conversation context

        Returns:
            List of resolved entities with confidence scores

        Raises:
            EntityResolutionError: If resolution fails critically

        Example:
            >>> entities = resolver.resolve("What's Delta's status?", context)
            >>> assert len(entities) == 1
        """
        try:
            # Extract entity mentions
            mentions = self._extract_entities(text)

            # Resolve each mention
            resolved = []
            for mention in mentions:
                entity = self._resolve_single_mention(mention, context)
                if entity:
                    resolved.append(entity)

            return resolved

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}", exc_info=True)
            raise EntityResolutionError(f"Failed to resolve entities: {e}") from e

    def _extract_entities(self, text: str) -> List[str]:
        """Extract entity mentions using NER (private method)."""
        doc = self._nlp(text)
        return [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PERSON"]]

    # ... rest of implementation


# Module-level functions (if needed)
def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate string similarity using fuzzy matching.

    Args:
        str1: First string
        str2: Second string

    Returns:
        Similarity score (0-1)

    Example:
        >>> calculate_similarity("Kay Media", "Kai Media")
        0.92
    """
    return fuzz.ratio(str1.lower(), str2.lower()) / 100.0


# Module-level initialization (if needed)
def _initialize_nlp_model() -> spacy.language.Language:
    """Initialize spaCy NLP model (called once at module import)."""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        logger.warning("spaCy model not found, downloading...")
        import subprocess
        subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
        return spacy.load("en_core_web_sm")
```

---

## Code Quality Standards

### 1. Type Hints (Mandatory)

**All functions must have complete type hints.**

```python
# ✅ Good
def process_query(
    query: str,
    user_id: str,
    timeout: Optional[float] = None
) -> Dict[str, Any]:
    """Process user query."""
    pass

# ❌ Bad
def process_query(query, user_id, timeout=None):
    """Process user query."""
    pass
```

### 2. Docstrings (Google Style)

**All public classes and functions must have docstrings.**

```python
def retrieve_memories(
    query_embedding: List[float],
    customer_id: Optional[str] = None,
    limit: int = 10
) -> List[Memory]:
    """
    Retrieve relevant memories using vector similarity search.

    Searches the memory store for memories similar to the query embedding,
    optionally filtered by customer.

    Args:
        query_embedding: Query vector (1536 dimensions)
        customer_id: Optional customer ID to filter by
        limit: Maximum number of memories to return (default: 10)

    Returns:
        List of Memory objects ordered by relevance (highest first)

    Raises:
        DatabaseError: If database query fails
        ValueError: If query_embedding has wrong dimensions

    Example:
        >>> embedding = embeddings.generate("payment history")
        >>> memories = retriever.retrieve_memories(embedding, limit=5)
        >>> for memory in memories:
        ...     print(f"{memory.content} (confidence: {memory.confidence})")

    Note:
        Uses pgvector's <=> operator for cosine distance.
        Memories with confidence < 0.7 are filtered out.

    See Also:
        - MemoryStore.store() for storing new memories
        - MemoryRetriever.retrieve_by_entity() for entity-specific search
    """
    pass
```

### 3. Error Handling

**Use specific exceptions, not bare except.**

```python
# ✅ Good
try:
    result = db.query(sql, params)
except DatabaseConnectionError as e:
    logger.error(f"DB connection failed: {e}")
    raise ServiceUnavailableError("Database unavailable") from e
except QueryTimeoutError as e:
    logger.warning(f"Query timeout: {e}")
    return None
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise

# ❌ Bad
try:
    result = db.query(sql, params)
except:
    return None
```

### 4. Logging

**Use structured logging with appropriate levels.**

```python
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Log levels
logger.debug("Detailed debug information")              # Development only
logger.info("Normal operational messages")              # Production info
logger.warning("Warning about potential issues")        # Degraded but functional
logger.error("Error that needs attention")              # Failure, needs fixing
logger.exception("Error with stack trace")              # Like error + traceback

# Structured logging
logger.info(
    "Entity resolved",
    extra={
        "entity_id": "customer-123",
        "confidence": 0.95,
        "disambiguation_needed": False,
        "latency_ms": 15
    }
)

# Never log sensitive data
logger.info(f"Processing payment for customer {customer_id}")  # ✅
logger.info(f"Payment details: {payment_info}")               # ❌
```

### 5. Code Formatting

**Use Black for formatting, isort for imports.**

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true
strict_equality = true

[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "C",    # flake8-comprehensions
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
]
ignore = []

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=src/intelligent_memory --cov-report=html --cov-report=term-missing"
```

### 6. Code Complexity

**Keep functions short and focused.**

```python
# Cyclomatic complexity: Max 10
# Function length: Max 50 lines
# Class length: Max 300 lines

# ✅ Good - Single responsibility
def extract_customer_name(query: str) -> Optional[str]:
    """Extract customer name from query."""
    doc = nlp(query)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            return ent.text
    return None

def resolve_customer_entity(name: str) -> Optional[Customer]:
    """Resolve customer name to entity."""
    return db.query_one(
        "SELECT * FROM domain.customers WHERE name = %s",
        (name,)
    )

# ❌ Bad - Multiple responsibilities
def process_query_and_resolve_customer(query: str) -> Optional[Customer]:
    """Extract and resolve customer (too much in one function)."""
    doc = nlp(query)
    for ent in doc.ents:
        if ent.label_ == "ORG":
            customer = db.query_one(...)
            if customer:
                return customer
    return None
```

---

## Design Patterns & Principles

### 1. Dependency Injection

**Use constructor injection for testability.**

```python
# ✅ Good - Dependencies injected
class MemoryRetriever:
    def __init__(
        self,
        db: DatabaseWrapper,
        embeddings: EmbeddingsGenerator,
        config: MemoryConfig
    ):
        self._db = db
        self._embeddings = embeddings
        self._config = config

# ❌ Bad - Hard-coded dependencies
class MemoryRetriever:
    def __init__(self):
        self._db = DatabaseWrapper()  # Can't mock in tests
        self._embeddings = EmbeddingsGenerator()  # Global state
```

### 2. Factory Pattern

**Use factories for complex object creation.**

```python
# intelligent_memory/core/intelligence/factories.py

class IntelligenceComponentFactory:
    """Factory for creating intelligence components with proper dependencies."""

    def __init__(
        self,
        db: DatabaseWrapper,
        cache: CacheManager,
        llm: LLMClient,
        config: Config
    ):
        self._db = db
        self._cache = cache
        self._llm = llm
        self._config = config

    def create_entity_resolver(self) -> EntityResolver:
        """Create EntityResolver with all dependencies."""
        nlp = self._load_nlp_model()
        return EntityResolver(
            db=self._db,
            nlp=nlp,
            cache=self._cache
        )

    def create_memory_retriever(self) -> MemoryRetriever:
        """Create MemoryRetriever with all dependencies."""
        embeddings = EmbeddingsGenerator(self._config.embeddings)
        return MemoryRetriever(
            db=self._db,
            embeddings=embeddings,
            config=self._config.memory
        )

    def create_context_assembler(self) -> ContextAssembler:
        """Create ContextAssembler with all dependencies."""
        formatter = ContextFormatter(self._config.formatting)
        return ContextAssembler(
            formatter=formatter,
            config=self._config.context_assembly
        )

    def _load_nlp_model(self) -> spacy.language.Language:
        """Load spaCy NLP model."""
        return spacy.load("en_core_web_sm")
```

### 3. Repository Pattern

**Abstract database access behind repositories.**

```python
# intelligent_memory/infrastructure/database/repositories/customer_repository.py

from abc import ABC, abstractmethod

class CustomerRepositoryInterface(ABC):
    """Interface for customer data access."""

    @abstractmethod
    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        pass

    @abstractmethod
    def find_by_name(self, name: str, fuzzy: bool = False) -> List[Customer]:
        """Find customers by name."""
        pass


class CustomerRepository(CustomerRepositoryInterface):
    """PostgreSQL implementation of customer repository."""

    def __init__(self, db: DatabaseWrapper):
        self._db = db

    def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        row = self._db.query_one(
            "SELECT * FROM domain.customers WHERE customer_id = %s",
            (customer_id,)
        )
        return Customer.from_db_row(row) if row else None

    def find_by_name(self, name: str, fuzzy: bool = False) -> List[Customer]:
        """Find customers by name."""
        if fuzzy:
            sql = """
                SELECT * FROM domain.customers
                WHERE name % %s
                ORDER BY similarity(name, %s) DESC
                LIMIT 5
            """
            rows = self._db.query(sql, (name, name))
        else:
            sql = "SELECT * FROM domain.customers WHERE LOWER(name) = LOWER(%s)"
            rows = self._db.query(sql, (name,))

        return [Customer.from_db_row(row) for row in rows]
```

### 4. Builder Pattern

**Use builders for complex object construction.**

```python
# intelligent_memory/core/intelligence/response_generation/prompt_builder.py

class PromptBuilder:
    """Builder for constructing LLM prompts with memories and DB facts."""

    def __init__(self):
        self._system_prompt: str = ""
        self._user_query: str = ""
        self._memories: List[Memory] = []
        self._db_facts: Dict[str, Any] = {}
        self._instructions: List[str] = []

    def set_system_prompt(self, prompt: str) -> 'PromptBuilder':
        """Set system prompt."""
        self._system_prompt = prompt
        return self

    def set_user_query(self, query: str) -> 'PromptBuilder':
        """Set user query."""
        self._user_query = query
        return self

    def add_memories(self, memories: List[Memory]) -> 'PromptBuilder':
        """Add relevant memories."""
        self._memories.extend(memories)
        return self

    def add_db_facts(self, facts: Dict[str, Any]) -> 'PromptBuilder':
        """Add database facts."""
        self._db_facts.update(facts)
        return self

    def add_instruction(self, instruction: str) -> 'PromptBuilder':
        """Add instruction for the LLM."""
        self._instructions.append(instruction)
        return self

    def build(self) -> str:
        """Build final prompt."""
        parts = []

        # System prompt
        if self._system_prompt:
            parts.append(f"System: {self._system_prompt}")

        # User query
        parts.append(f"\nUser Query: {self._user_query}")

        # Memories
        if self._memories:
            parts.append("\nFrom Memory:")
            for mem in self._memories:
                parts.append(
                    f"- {mem.content} (confidence: {mem.confidence:.2f})"
                )

        # Database facts
        if self._db_facts:
            parts.append("\nFrom Database:")
            for category, facts in self._db_facts.items():
                parts.append(f"\n{category}:")
                parts.append(facts)

        # Instructions
        if self._instructions:
            parts.append("\nInstructions:")
            parts.extend([f"- {i}" for i in self._instructions])

        return "\n".join(parts)


# Usage
prompt = (
    PromptBuilder()
    .set_system_prompt("You are a business analyst assistant...")
    .set_user_query("Should we extend payment terms to Delta?")
    .add_memories(relevant_memories)
    .add_db_facts({"Payment History": payment_summary})
    .add_instruction("Analyze and provide recommendation")
    .add_instruction("Cite specific facts")
    .build()
)
```

---

## Testing Strategy

### Test Structure

```
tests/
├── unit/                      # Fast, isolated tests
│   ├── test_entity_resolver.py
│   ├── test_context_assembler.py
│   ├── test_memory_retriever.py
│   └── test_response_generator.py
├── integration/               # Tests with real dependencies
│   ├── test_database.py
│   └── test_redis.py
├── e2e/                       # End-to-end scenario tests
│   └── test_scenarios.py
└── performance/               # Performance benchmarks
    └── test_latency.py
```

### Unit Test Example

```python
# tests/unit/test_entity_resolver.py

import pytest
from unittest.mock import Mock, MagicMock

from intelligent_memory.core.intelligence.entity_resolution.resolver import EntityResolver
from intelligent_memory.core.intelligence.entity_resolution.models import ResolvedEntity


class TestEntityResolver:
    """Test suite for EntityResolver."""

    @pytest.fixture
    def mock_db(self):
        """Mock database wrapper."""
        db = Mock()
        db.query_one.return_value = {
            'customer_id': 'cust-123',
            'name': 'Delta Industries'
        }
        return db

    @pytest.fixture
    def mock_nlp(self):
        """Mock spaCy NLP model."""
        nlp = Mock()
        # Setup mock NER extraction
        return nlp

    @pytest.fixture
    def resolver(self, mock_db, mock_nlp):
        """Create resolver with mocks."""
        return EntityResolver(db=mock_db, nlp=mock_nlp)

    def test_exact_match_resolution(self, resolver, mock_db):
        """Test exact entity name match."""
        # Arrange
        context = Mock()

        # Act
        entities = resolver.resolve("Delta Industries", context)

        # Assert
        assert len(entities) == 1
        assert entities[0].entity_name == "Delta Industries"
        assert entities[0].confidence >= 0.95
        assert not entities[0].disambiguation_needed

        # Verify DB was called correctly
        mock_db.query_one.assert_called_once()

    def test_fuzzy_match_resolution(self, resolver, mock_db):
        """Test fuzzy entity name match."""
        # Arrange
        mock_db.query_one.return_value = None  # No exact match
        mock_db.query.return_value = [{
            'customer_id': 'cust-456',
            'name': 'Kai Media'
        }]
        context = Mock()

        # Act
        entities = resolver.resolve("Kay Media", context)

        # Assert
        assert len(entities) == 1
        assert entities[0].entity_name == "Kai Media"
        assert 0.85 <= entities[0].confidence < 0.95

    def test_disambiguation_needed(self, resolver, mock_db):
        """Test disambiguation when multiple matches found."""
        # Arrange
        mock_db.query_one.return_value = None
        mock_db.query.return_value = [
            {'customer_id': 'cust-1', 'name': 'Delta Industries'},
            {'customer_id': 'cust-2', 'name': 'Delta Corp'},
            {'customer_id': 'cust-3', 'name': 'DeltaTech'}
        ]
        context = Mock()
        context.recent_entities = []

        # Act
        entities = resolver.resolve("Delta", context)

        # Assert
        assert len(entities) == 1
        assert entities[0].disambiguation_needed
        assert len(entities[0].candidates) == 3

    def test_conversation_context_boosts_score(self, resolver, mock_db):
        """Test that conversation context boosts disambiguation score."""
        # Arrange
        mock_db.query_one.return_value = None
        mock_db.query.return_value = [
            {'customer_id': 'cust-1', 'name': 'Delta Industries'},
            {'customer_id': 'cust-2', 'name': 'Delta Corp'}
        ]

        context = Mock()
        context.recent_entities = ['cust-1']  # Delta Industries mentioned recently
        context.get_last_mention.return_value = 2  # 2 turns ago

        # Act
        entities = resolver.resolve("Delta", context)

        # Assert
        # Should auto-resolve to Delta Industries due to context boost
        assert not entities[0].disambiguation_needed
        assert entities[0].entity_id == 'cust-1'

    @pytest.mark.parametrize("query,expected_entity_count", [
        ("Delta Industries", 1),
        ("Delta and Kai Media", 2),
        ("", 0),
    ])
    def test_multiple_scenarios(self, resolver, mock_db, query, expected_entity_count):
        """Test multiple query scenarios."""
        # Setup appropriate mocks based on query
        # ...

        context = Mock()
        entities = resolver.resolve(query, context)
        assert len(entities) == expected_entity_count
```

### Integration Test Example

```python
# tests/integration/test_database.py

import pytest
from intelligent_memory.infrastructure.database.wrapper import DatabaseWrapper
from intelligent_memory.infrastructure.database.connection import create_connection_pool


@pytest.fixture(scope="module")
def db():
    """Create real database connection for integration tests."""
    pool = create_connection_pool(database_url="postgresql://localhost/test_db")
    db = DatabaseWrapper(pool)

    # Setup test data
    db.execute("TRUNCATE TABLE domain.customers CASCADE")
    db.execute("""
        INSERT INTO domain.customers (customer_id, name, status)
        VALUES ('test-1', 'Test Customer', 'active')
    """)

    yield db

    # Teardown
    db.execute("TRUNCATE TABLE domain.customers CASCADE")
    pool.close()


def test_customer_query(db):
    """Test actual database query."""
    result = db.query_one(
        "SELECT * FROM domain.customers WHERE customer_id = %s",
        ("test-1",)
    )

    assert result is not None
    assert result['name'] == 'Test Customer'
```

### E2E Test Example

```python
# tests/e2e/test_scenarios.py

import pytest
from httpx import AsyncClient

from intelligent_memory.api.main import app


@pytest.mark.asyncio
async def test_scenario_s31_entity_linking():
    """
    Test S3.1: Entity Linking scenario.

    User asks: "What's Delta's payment status?"
    Expected: System resolves "Delta" and retrieves payment info
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Act
        response = await client.post(
            "/chat",
            json={
                "user_id": "test-user",
                "session_id": "test-session",
                "message": "What's Delta's payment status?"
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "message" in data
        assert "entities" in data
        assert "sources" in data

        # Check entity resolution
        assert len(data["entities"]) >= 1
        assert data["entities"][0]["type"] == "customer"
        assert "Delta" in data["entities"][0]["name"]

        # Check response mentions payment information
        message = data["message"].lower()
        assert "payment" in message or "invoice" in message


@pytest.mark.asyncio
async def test_scenario_s61_memory_retrieval():
    """
    Test S6.1: Memory Retrieval scenario.

    User asks follow-up question referencing past conversation.
    Expected: System retrieves relevant memories
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Setup: Store initial memory
        await client.post(
            "/chat",
            json={
                "user_id": "test-user",
                "session_id": "test-session-2",
                "message": "Delta Industries is on NET15 terms"
            }
        )

        # Act: Ask related question
        response = await client.post(
            "/chat",
            json={
                "user_id": "test-user",
                "session_id": "test-session-2",
                "message": "What are their payment terms?"
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Check that memory was used
        assert "NET15" in data["message"]
        assert len(data.get("memories_used", [])) > 0
```

---

## Configuration Management

### Settings Structure

```python
# intelligent_memory/config/settings.py

from pydantic import BaseSettings, Field, SecretStr, validator
from typing import Optional
import os


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    host: str = Field(..., env="DB_HOST")
    port: int = Field(5432, env="DB_PORT")
    database: str = Field(..., env="DB_NAME")
    user: str = Field(..., env="DB_USER")
    password: SecretStr = Field(..., env="DB_PASSWORD")

    min_pool_size: int = Field(5, env="DB_MIN_POOL_SIZE")
    max_pool_size: int = Field(20, env="DB_MAX_POOL_SIZE")

    @property
    def url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class RedisSettings(BaseSettings):
    """Redis configuration."""

    host: str = Field(..., env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[SecretStr] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")

    max_connections: int = Field(50, env="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(5, env="REDIS_SOCKET_TIMEOUT")

    class Config:
        env_file = ".env"


class LLMSettings(BaseSettings):
    """LLM configuration."""

    openai_api_key: SecretStr = Field(..., env="OPENAI_API_KEY")

    quality_model: str = Field("gpt-4-turbo", env="LLM_QUALITY_MODEL")
    cheap_model: str = Field("gpt-3.5-turbo", env="LLM_CHEAP_MODEL")

    max_tokens_quality: int = Field(1000, env="LLM_MAX_TOKENS_QUALITY")
    max_tokens_cheap: int = Field(500, env="LLM_MAX_TOKENS_CHEAP")

    temperature: float = Field(0.3, env="LLM_TEMPERATURE")
    request_timeout: int = Field(30, env="LLM_REQUEST_TIMEOUT")

    class Config:
        env_file = ".env"


class Settings(BaseSettings):
    """Main application settings."""

    # Environment
    environment: str = Field("development", env="ENVIRONMENT")
    debug: bool = Field(False, env="DEBUG")

    # API
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")
    api_workers: int = Field(4, env="API_WORKERS")

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: str = "json"  # or "text"

    @validator("environment")
    def validate_environment(cls, v):
        """Validate environment value."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

### Environment Files

```bash
# .env.development
ENVIRONMENT=development
DEBUG=true

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=intelligent_memory_dev
DB_USER=dev_user
DB_PASSWORD=dev_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM
OPENAI_API_KEY=sk-...

# Logging
LOG_LEVEL=DEBUG
```

---

## Dependency Management

### pyproject.toml

```toml
[tool.poetry]
name = "intelligent-memory-system"
version = "0.1.0"
description = "Intelligent conversational memory system with entity resolution"
authors = ["Your Team <team@example.com>"]
readme = "README.md"
packages = [{include = "intelligent_memory", from = "src"}]

[tool.poetry.dependencies]
python = "^3.11"

# Web framework
fastapi = "^0.104.0"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = {extras = ["email"], version = "^2.5.0"}
python-multipart = "^0.0.6"

# Database
psycopg2-binary = "^2.9.9"
pgvector = "^0.2.3"
asyncpg = "^0.29.0"

# Caching
redis = {extras = ["hiredis"], version = "^5.0.1"}
hiredis = "^2.2.3"

# NLP
spacy = "^3.7.2"
fuzzywuzzy = {extras = ["speedup"], version = "^0.18.0"}
python-Levenshtein = "^0.23.0"

# LLM
openai = "^1.3.5"
tiktoken = "^0.5.1"

# Utilities
python-dateutil = "^2.8.2"
pytz = "^2023.3"
structlog = "^23.2.0"

[tool.poetry.group.dev.dependencies]
# Testing
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
pytest-mock = "^3.12.0"
httpx = "^0.25.1"

# Code quality
black = "^23.11.0"
isort = "^5.12.0"
mypy = "^1.7.0"
ruff = "^0.1.6"
pylint = "^3.0.2"

# Pre-commit
pre-commit = "^3.5.0"

# Documentation
mkdocs = "^1.5.3"
mkdocs-material = "^9.4.14"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## Development Workflow

### Makefile

```makefile
.PHONY: help install test lint format type-check clean run migrate

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	poetry install

test:  ## Run tests
	poetry run pytest tests/ -v --cov --cov-report=html

test-unit:  ## Run unit tests only
	poetry run pytest tests/unit/ -v

test-integration:  ## Run integration tests
	poetry run pytest tests/integration/ -v

test-e2e:  ## Run end-to-end tests
	poetry run pytest tests/e2e/ -v

lint:  ## Run linters
	poetry run ruff check src/ tests/
	poetry run pylint src/

format:  ## Format code
	poetry run black src/ tests/
	poetry run isort src/ tests/

type-check:  ## Run type checker
	poetry run mypy src/

quality:  ## Run all quality checks
	make format
	make lint
	make type-check
	make test

clean:  ## Clean generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov/

run:  ## Run development server
	poetry run uvicorn intelligent_memory.api.main:app --reload

migrate:  ## Run database migrations
	poetry run python scripts/db/migrate.py

seed:  ## Seed database with test data
	poetry run python scripts/db/seed.py

redis:  ## Start Redis (via Docker)
	docker run -d -p 6379:6379 redis:7-alpine

postgres:  ## Start PostgreSQL (via Docker)
	docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=dev_password postgres:14

docker-up:  ## Start all services via Docker Compose
	docker-compose up -d

docker-down:  ## Stop all services
	docker-compose down

benchmark:  ## Run performance benchmarks
	poetry run python benchmarks/end_to_end.py
```

### Pre-commit Configuration

```yaml
# .pre-commit-config.yaml

repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: [--ignore-missing-imports]
```

---

## Summary

This simplified codebase structure provides:

1. **Core Focus**
   - Entity Resolution (NER + fuzzy matching)
   - Memory System (storage, retrieval, consolidation)
   - Context Assembly (format memories + DB facts for LLM)
   - Response Generation (LLM synthesis)
   - Database Fact Augmentation

2. **Removed Complexity**
   - ❌ Pattern Analysis infrastructure
   - ❌ Decision Support Engine
   - ❌ Workflow Automation system
   - ❌ Complex Celery task queue (replaced with simple background tasks)

3. **High Code Quality**
   - Mandatory type hints
   - Comprehensive docstrings
   - Automated formatting
   - Type checking
   - Linting

4. **Testability**
   - Dependency injection
   - Repository pattern
   - Factory pattern
   - Clear interfaces

5. **Maintainability**
   - Design patterns
   - SOLID principles
   - Low coupling
   - High cohesion

6. **Developer Experience**
   - Make commands
   - Pre-commit hooks
   - Clear structure
   - Good examples

**This simplified structure focuses on core project requirements and can be implemented in 4 weeks instead of 12+ weeks.**
