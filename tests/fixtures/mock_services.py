"""
Mock Services for Testing

Provides in-memory implementations of repository ports for fast unit tests.
No database, no external API calls - pure Python for speed.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import numpy as np

# These imports will work once domain layer is implemented
# from src.domain.ports.entity_repository import EntityRepositoryPort
# from src.domain.ports.memory_repository import MemoryRepositoryPort
# from src.domain.ports.llm_service import LLMServicePort
# from src.domain.entities.canonical_entity import CanonicalEntity
# from src.domain.entities.semantic_memory import SemanticMemory


class MockEntityRepository:
    """
    In-memory entity repository for unit tests.

    Simulates database operations without actual PostgreSQL.
    Used in: Domain unit tests (Layer 2)
    """

    def __init__(self):
        self._entities: Dict[str, Any] = {}  # entity_id → CanonicalEntity
        self._aliases: Dict[str, List[Any]] = {}  # alias_text → [EntityAlias]

    async def get_by_id(self, entity_id: str) -> Optional[Any]:
        """Get entity by canonical ID"""
        return self._entities.get(entity_id)

    async def get_by_name(self, canonical_name: str) -> Optional[Any]:
        """Get entity by exact canonical name (exact match)"""
        for entity in self._entities.values():
            if entity.canonical_name == canonical_name:
                return entity
        return None

    async def fuzzy_search(self, query: str, threshold: float = 0.7) -> List[Any]:
        """
        Fuzzy search for entities (simulates pg_trgm).

        For testing: uses simple substring matching instead of trigram similarity.
        Real implementation uses: SELECT *, similarity(canonical_name, query) as sim
                                  FROM canonical_entities
                                  WHERE similarity(canonical_name, query) > threshold
        """
        results = []
        query_lower = query.lower()

        for entity in self._entities.values():
            name_lower = entity.canonical_name.lower()

            # Simple similarity: Jaccard similarity of words
            query_words = set(query_lower.split())
            name_words = set(name_lower.split())

            if query_words & name_words:  # Any word overlap
                intersection = len(query_words & name_words)
                union = len(query_words | name_words)
                similarity = intersection / union if union > 0 else 0.0

                if similarity >= threshold:
                    entity.similarity_score = similarity  # Add for testing
                    results.append(entity)

        # Sort by similarity descending
        results.sort(key=lambda e: getattr(e, 'similarity_score', 0.0), reverse=True)
        return results

    async def create(self, entity: Any) -> Any:
        """Create new entity"""
        self._entities[entity.entity_id] = entity
        return entity

    async def create_alias(self, alias: Any) -> Any:
        """Create alias for entity resolution"""
        if alias.alias_text not in self._aliases:
            self._aliases[alias.alias_text] = []
        self._aliases[alias.alias_text].append(alias)
        return alias

    async def get_alias(self, alias_text: str, user_id: Optional[str] = None) -> Optional[Any]:
        """Get alias by text and optional user_id"""
        aliases = self._aliases.get(alias_text, [])

        # Filter by user_id if provided
        if user_id is not None:
            user_aliases = [a for a in aliases if a.user_id == user_id]
            if user_aliases:
                return user_aliases[0]

        # Return global alias (user_id = None)
        global_aliases = [a for a in aliases if a.user_id is None]
        return global_aliases[0] if global_aliases else None

    def add_entity(self, entity: Any):
        """Test helper - directly add entity to mock repo"""
        self._entities[entity.entity_id] = entity


class MockMemoryRepository:
    """
    In-memory memory repository for unit tests.

    Simulates pgvector operations without PostgreSQL.
    """

    def __init__(self):
        self._episodic: Dict[int, Any] = {}  # memory_id → EpisodicMemory
        self._semantic: Dict[int, Any] = {}  # memory_id → SemanticMemory
        self._next_id = 1

    async def create_episodic(self, memory: Any) -> Any:
        """Create episodic memory"""
        if memory.memory_id is None:
            memory.memory_id = self._next_id
            self._next_id += 1
        self._episodic[memory.memory_id] = memory
        return memory

    async def create_semantic(self, memory: Any) -> Any:
        """Create semantic memory"""
        if memory.memory_id is None:
            memory.memory_id = self._next_id
            self._next_id += 1
        self._semantic[memory.memory_id] = memory
        return memory

    async def get_semantic_by_id(self, memory_id: int) -> Optional[Any]:
        """Get semantic memory by ID"""
        return self._semantic.get(memory_id)

    async def semantic_search(
        self,
        query_embedding: np.ndarray,
        user_id: str,
        limit: int = 50,
        status: str = "active"
    ) -> List[Any]:
        """
        Semantic search using embedding similarity (simulates pgvector).

        For testing: uses cosine similarity on NumPy arrays.
        Real implementation uses: SELECT *, 1 - (embedding <=> query_embedding) as similarity
                                  FROM semantic_memories
                                  ORDER BY embedding <=> query_embedding
                                  LIMIT limit
        """
        results = []

        for memory in self._semantic.values():
            if memory.user_id != user_id or memory.status != status:
                continue

            if memory.embedding is None:
                continue

            # Cosine similarity
            dot_product = np.dot(query_embedding, memory.embedding)
            norm_query = np.linalg.norm(query_embedding)
            norm_memory = np.linalg.norm(memory.embedding)

            if norm_query > 0 and norm_memory > 0:
                similarity = dot_product / (norm_query * norm_memory)
                memory.similarity_score = similarity  # Add for testing
                results.append(memory)

        # Sort by similarity descending
        results.sort(key=lambda m: getattr(m, 'similarity_score', 0.0), reverse=True)
        return results[:limit]

    async def find_similar_semantic(
        self,
        subject_entity_id: str,
        predicate: str,
        user_id: str,
        similarity_threshold: float = 0.85
    ) -> List[Any]:
        """Find similar semantic memories for reinforcement detection"""
        results = []

        for memory in self._semantic.values():
            if (memory.user_id == user_id and
                memory.subject_entity_id == subject_entity_id and
                memory.predicate == predicate and
                memory.status == "active"):
                results.append(memory)

        return results


class MockLLMService:
    """
    Mock LLM service with deterministic responses.

    No OpenAI API calls - returns canned responses for testing.
    Tracks call count for cost testing.
    """

    def __init__(self):
        self.call_count = 0
        self.last_request: Optional[Dict] = None
        self.canned_responses: Dict[str, Any] = {}

    async def extract_triples(self, text: str, entities: List[Any]) -> Any:
        """
        Extract semantic triples from text (mocked).

        Real implementation: Calls OpenAI GPT-4 with extraction prompt
        Mock implementation: Pattern matching for test cases
        """
        self.call_count += 1
        self.last_request = {"operation": "extract_triples", "text": text, "entities": entities}

        # Pattern matching for common test cases
        text_lower = text.lower()

        triples = []

        # Delivery preference pattern
        if "friday" in text_lower and "deliver" in text_lower:
            triples.append({
                "subject_entity_id": entities[0].entity_id if entities else "unknown",
                "predicate": "delivery_preference",
                "predicate_type": "preference",
                "object_value": {"type": "day_of_week", "value": "Friday"},
                "confidence": 0.75
            })

        # Payment terms pattern
        if "net30" in text_lower or "net 30" in text_lower:
            triples.append({
                "subject_entity_id": entities[0].entity_id if entities else "unknown",
                "predicate": "payment_terms",
                "predicate_type": "attribute",
                "object_value": {"type": "payment_terms", "value": "NET30"},
                "confidence": 0.80
            })

        # Return mock result
        return type('ExtractionResult', (), {
            'triples': triples,
            'event_type': self._classify_event_type(text)
        })()

    def _classify_event_type(self, text: str) -> str:
        """Classify event type from text"""
        text_lower = text.lower()

        if "?" in text:
            return "question"
        elif "remember" in text_lower or "note" in text_lower:
            return "statement"
        elif "actually" in text_lower or "correction" in text_lower:
            return "correction"
        elif "yes" in text_lower or "correct" in text_lower:
            return "confirmation"
        else:
            return "statement"

    async def resolve_coreference(
        self,
        mention: str,
        context: List[Any],
        recent_entities: List[Any]
    ) -> Optional[str]:
        """
        Resolve coreference (e.g., "they", "it", "that customer").

        Real implementation: Calls OpenAI with context
        Mock implementation: Returns most recent entity for pronouns
        """
        self.call_count += 1
        self.last_request = {"operation": "resolve_coreference", "mention": mention}

        pronouns = ["they", "them", "it", "this", "that", "the customer", "the company"]

        if mention.lower() in pronouns and recent_entities:
            return recent_entities[0].entity_id

        return None

    def set_canned_response(self, operation: str, response: Any):
        """Test helper - set canned response for operation"""
        self.canned_responses[operation] = response


class MockEmbeddingService:
    """
    Mock embedding service (simulates OpenAI text-embedding-3-small).

    Returns random but consistent embeddings for same text.
    """

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self._cache: Dict[str, np.ndarray] = {}  # text → embedding
        self.call_count = 0

    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.

        Real implementation: Calls OpenAI embedding API
        Mock implementation: Deterministic random based on text hash
        """
        self.call_count += 1

        # Use cache for consistency
        if text in self._cache:
            return self._cache[text]

        # Generate deterministic "embedding" from text hash
        # This ensures same text always gets same embedding
        text_hash = hash(text)
        np.random.seed(text_hash % (2**32))  # Seed with hash
        embedding = np.random.rand(self.dimension).astype(np.float32)

        # Normalize to unit vector (like real embeddings)
        embedding = embedding / np.linalg.norm(embedding)

        self._cache[text] = embedding
        return embedding


class MockDomainDBService:
    """
    Mock domain database service (simulates domain.customers, domain.invoices, etc.).

    In-memory relational data for testing domain ontology integration.
    """

    def __init__(self):
        self._tables: Dict[str, List[Dict]] = {
            "customers": [],
            "invoices": [],
            "sales_orders": [],
            "products": []
        }

    async def query(self, table: str, filters: Dict[str, Any]) -> List[Dict]:
        """Query domain table with filters"""
        if table not in self._tables:
            return []

        results = self._tables[table]

        # Apply filters
        for key, value in filters.items():
            results = [row for row in results if row.get(key) == value]

        return results

    async def get_related(
        self,
        entity_type: str,
        entity_id: str,
        relation_type: str
    ) -> List[Dict]:
        """
        Get related entities via ontology join spec.

        Example: get_related("customer", "gai_123", "has") → returns orders
        """
        # Mock implementation - would use domain_ontology table in real system
        if entity_type == "customer" and relation_type == "has":
            # Return customer's orders
            return await self.query("sales_orders", {"customer_id": entity_id})

        return []

    def seed_data(self, table: str, rows: List[Dict]):
        """Test helper - seed domain database"""
        if table not in self._tables:
            self._tables[table] = []
        self._tables[table].extend(rows)

    def clear_data(self, table: Optional[str] = None):
        """Test helper - clear domain database"""
        if table:
            self._tables[table] = []
        else:
            for table_name in self._tables:
                self._tables[table_name] = []
