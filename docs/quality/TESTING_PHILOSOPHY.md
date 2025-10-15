# Testing Philosophy: Verifying Vision Through Code

**Status**: Design Complete - Ready for Implementation
**Purpose**: Comprehensive testing infrastructure that validates every vision principle and functional requirement

---

## Testing Thesis

> **Testing is not just verification of correctness - it's validation of philosophical alignment.**

Traditional testing asks: "Does the code work?"

Our testing asks:
1. **Does the code work?** (Functional correctness)
2. **Does it embody the vision?** (Philosophical alignment)
3. **Does it preserve invariants?** (Conceptual integrity)
4. **Does it fail gracefully?** (Resilience)
5. **Can we prove it?** (Evidence-based confidence)

---

## The Testing Pyramid (Vision-Aligned)

```
                   ┌──────────────┐
                   │  Philosophy  │  5% - Vision principle tests
                   │  Validation  │      (epistemic humility, dual truth)
                   ├──────────────┤
                   │   Scenario    │  10% - E2E scenario tests
                   │     E2E       │       (18 scenarios from ProjectDescription)
                   ├──────────────┤
                   │  Integration  │  20% - Database, LLM, domain DB
                   │     Tests     │       (infrastructure adapters)
                   ├──────────────┤
                   │  Domain Unit  │  50% - Business logic
                   │     Tests     │       (pure functions, domain services)
                   ├──────────────┤
                   │  Property-    │  15% - Invariant verification
                   │    Based      │       (confidence bounds, decay laws)
                   └──────────────┘
```

**Total Coverage Target**: 90%+ for domain layer, 80%+ overall

---

## Layer 0: LLM-Based Vision Validation (Foundation)

**Purpose**: Use LLMs to verify philosophical alignment where traditional assertions cannot.

### Why LLM for Testing?

**Philosophical principles are expressed in natural language, not code invariants.**

Traditional testing asks: "Does confidence == 0.4?"
LLM testing asks: "Does the TONE of this response reflect epistemic humility appropriate for confidence 0.4?"

Vision principles like "epistemic humility," "graceful forgetting," or "dual truth equilibrium" are **semantic concepts** that require natural language understanding to verify.

### The LLM Testing Pattern

```python
# tests/fixtures/llm_test_evaluator.py
from dataclasses import dataclass
import openai

@dataclass
class VisionEvaluation:
    """Result of LLM-based vision evaluation"""
    principle: str          # Which vision principle being tested
    score: float           # 0.0 (violation) to 1.0 (perfect alignment)
    reasoning: str         # Why this score?
    violations: List[str]  # Specific violations detected
    passes: bool           # True if score >= 0.8

class LLMTestEvaluator:
    """Uses LLM to evaluate system behavior against vision principles"""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.client = openai.AsyncOpenAI()

    async def evaluate_epistemic_humility(
        self,
        response: str,
        confidence: float,
        context: Dict
    ) -> VisionEvaluation:
        """
        Evaluate if response demonstrates epistemic humility.

        Traditional assertion: confidence <= MAX_CONFIDENCE (mechanical check)
        LLM evaluation: Does TONE match confidence level? (semantic check)
        """
        prompt = f"""
You are evaluating whether an AI system response demonstrates EPISTEMIC HUMILITY.

**Vision Principle**: "The system should know what it doesn't know"

**Context**:
- Confidence score: {confidence}
- Memory age: {context.get('memory_age_days', 'N/A')} days
- Conflicts detected: {context.get('conflicts_detected', [])}

**System Response**:
"{response}"

**Evaluation Criteria**:
1. Does the tone match the confidence level?
   - Low confidence (< 0.5) should use hedging language ("may", "likely", "based on limited info")
   - High confidence (> 0.8) can use definitive language
2. Are sources/dates cited for uncertain information?
3. Are conflicts acknowledged explicitly (not hidden)?
4. Does it admit lack of information rather than fabricate?

**Output JSON**:
{{
  "score": <float 0.0-1.0>,
  "reasoning": "<2-3 sentence explanation>",
  "violations": ["<specific violations>"],
  "passes": <true if score >= 0.8>
}}
"""

        response_json = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        result = json.loads(response_json.choices[0].message.content)

        return VisionEvaluation(
            principle="epistemic_humility",
            score=result["score"],
            reasoning=result["reasoning"],
            violations=result.get("violations", []),
            passes=result["passes"]
        )
```

### Example: Testing Epistemic Humility with LLM

```python
# tests/philosophy/test_epistemic_humility_llm.py
import pytest

class TestEpistemicHumilityWithLLM:
    """
    VISION: "System should know what it doesn't know"
    METHOD: LLM evaluates if response semantics match confidence level
    """

    @pytest.mark.philosophy
    @pytest.mark.asyncio
    async def test_low_confidence_triggers_hedging_language(self, api_client):
        """
        SCENARIO: System has low-confidence memory (0.4)
        TRADITIONAL TEST: Assert confidence < 0.5
        LLM TEST: Evaluate if TONE reflects uncertainty
        """
        # Setup: Create low-confidence memory
        await api_client.post("/api/v1/memories/semantic", json={
            "user_id": "test_user",
            "subject_entity_id": "customer:tc_123",
            "predicate": "payment_terms",
            "object_value": "NET30",
            "confidence": 0.4,  # Low confidence
            "last_validated_at": (datetime.utcnow() - timedelta(days=95)).isoformat()
        })

        # User query
        response = await api_client.post("/api/v1/chat", json={
            "user_id": "test_user",
            "message": "What are TC Boiler's payment terms?"
        })

        data = response.json()
        system_response = data["response"]

        # TRADITIONAL ASSERTION: Confidence value check
        assert data["augmentation"]["memories_retrieved"][0]["confidence"] == 0.4

        # LLM EVALUATION: Semantic alignment check
        evaluator = LLMTestEvaluator()
        result = await evaluator.evaluate_epistemic_humility(
            response=system_response,
            confidence=0.4,
            context={
                "memory_age_days": 95,
                "data_availability": "single_unconfirmed_memory"
            }
        )

        # Assert LLM detected appropriate epistemic humility
        assert result.passes, \
            f"Epistemic humility violation (score {result.score}/1.0):\n" \
            f"Reasoning: {result.reasoning}\n" \
            f"Violations: {result.violations}"

        # LLM should have detected hedging language
        assert "hedging" in result.reasoning.lower() or \
               "cautious" in result.reasoning.lower(), \
            f"LLM didn't detect hedging for low confidence: {result.reasoning}"

    @pytest.mark.philosophy
    @pytest.mark.asyncio
    async def test_no_data_acknowledges_gap_vs_hallucination(self, api_client):
        """
        SCENARIO: User asks about entity with no data
        CHALLENGE: Detecting hallucination vs honest acknowledgment

        Traditional assertion: Hard to write rule for "sounds plausible but is fabricated"
        LLM evaluation: Can detect semantic pattern of hallucination
        """
        response = await api_client.post("/api/v1/chat", json={
            "user_id": "test_user",
            "message": "What are the payment terms for NonexistentCorp?"
        })

        data = response.json()
        system_response = data["response"]

        # Traditional assertions
        assert len(data["augmentation"]["memories_retrieved"]) == 0
        assert len(data["augmentation"]["domain_facts"]) == 0

        # LLM evaluation - detects hallucination patterns
        evaluator = LLMTestEvaluator()
        result = await evaluator.evaluate_epistemic_humility(
            response=system_response,
            confidence=0.0,
            context={"data_availability": "none"}
        )

        # If hallucination detected, LLM will flag it
        assert result.passes, \
            f"LLM detected possible hallucination (score {result.score}/1.0):\n" \
            f"{result.reasoning}\n" \
            f"Violations: {result.violations}"

        # LLM should confirm gap acknowledgment, not fabrication
        assert "acknowledge" in result.reasoning.lower() or \
               "gap" in result.reasoning.lower(), \
            f"LLM didn't detect gap acknowledgment: {result.reasoning}"
```

### Use Cases for LLM Testing

| Test Type | Traditional Assertion | LLM Evaluation | Why LLM Adds Value |
|-----------|----------------------|----------------|-------------------|
| **Epistemic Humility** | `assert confidence < 0.5` | Evaluates if tone matches confidence | Can detect overconfident language despite low confidence score |
| **Dual Truth** | `assert len(db_facts) > 0` | Checks DB facts prioritized in response | Detects if memory overrides DB despite both being present |
| **Explainability** | `assert provenance_data exists` | Verifies sources are actually cited in text | Citations might exist in metadata but not be visible in response |
| **Graceful Forgetting** | `assert len(consolidated) < len(originals)` | Checks if summary preserves essence | Summary could be short but miss key facts |
| **Conflict Handling** | `assert conflict logged` | Verifies conflict acknowledged in response | Conflict might be logged but hidden from user |

### Edge Case Generation with LLM

```python
class VisionAlignedTestGenerator:
    """Use LLM to generate edge case tests from vision principles"""

    async def generate_edge_cases_for_principle(
        self,
        principle: str,
        count: int = 5
    ) -> List[Dict]:
        """
        LLM generates challenging test scenarios for a vision principle.

        Why LLM?
        - Can think creatively about edge cases humans might miss
        - Understands semantic nuances of principles
        - Generates realistic but challenging scenarios
        """
        prompt = f"""
You are a QA engineer designing edge case tests for an AI memory system.

**Vision Principle**: {principle}

**Task**: Generate {count} challenging edge case test scenarios that could reveal
violations of this principle.

For each scenario:
1. **Setup**: Initial state (DB data, memories, context)
2. **User Query**: What user asks
3. **Expected Behavior**: How system should respond to align with principle
4. **Failure Mode**: What violation would look like
5. **Why Challenging**: Why this tests the edge of the principle

**Output JSON array**:
[
  {{
    "scenario_name": "<descriptive name>",
    "setup": {{"db_data": {{}}, "memories": [], "context": {{}}}},
    "user_query": "<query>",
    "expected_behavior": "<detailed expectation>",
    "failure_mode": "<violation pattern>",
    "why_challenging": "<edge case explanation>"
  }},
  ...
]

Make scenarios REALISTIC and CHALLENGING - think about corner cases.
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7  # Higher temp for creativity
        )

        return json.loads(response.choices[0].message.content)["scenarios"]
```

### Example: LLM-Generated Edge Cases

```python
@pytest.mark.philosophy
@pytest.mark.asyncio
async def test_llm_generated_edge_cases():
    """
    Use LLM to generate edge case tests for epistemic humility.

    This test:
    1. Uses LLM to generate challenging scenarios
    2. Executes them against the system
    3. Uses LLM to evaluate results

    Meta-testing: LLMs test LLMs, but for different purposes
    - Generation LLM: Creative (temp=0.7), generates scenarios
    - Evaluation LLM: Analytical (temp=0.0), judges alignment
    """
    generator = VisionAlignedTestGenerator()

    # LLM generates edge cases
    scenarios = await generator.generate_edge_cases_for_principle(
        principle="epistemic_humility",
        count=5
    )

    evaluator = LLMTestEvaluator()

    # Run each LLM-generated scenario
    for scenario in scenarios:
        # Setup system state
        await setup_scenario(scenario["setup"])

        # Execute user query
        response = await api_client.post("/api/v1/chat", json={
            "message": scenario["user_query"]
        })

        # LLM evaluates result
        result = await evaluator.evaluate_epistemic_humility(
            response=response.json()["response"],
            confidence=...,
            context=scenario["setup"]["context"]
        )

        assert result.passes, \
            f"LLM-generated edge case failed:\n" \
            f"Scenario: {scenario['scenario_name']}\n" \
            f"Reasoning: {result.reasoning}"
```

### LLM Testing Best Practices

1. **Use LLM for Semantic Checks, Not Mechanical Checks**
   - ❌ Bad: Use LLM to check `if confidence == 0.4`
   - ✅ Good: Use LLM to check if tone reflects uncertainty

2. **Combine with Traditional Assertions**
   - Traditional: Verify mechanical correctness (`confidence <= MAX_CONFIDENCE`)
   - LLM: Verify semantic alignment (hedging language for low confidence)

3. **Use Deterministic Evaluation (temperature=0.0)**
   - LLM evaluation should be consistent
   - Generation can be creative (temperature=0.7)

4. **Verify LLM Evaluator with Known Cases**
   - Test the tester: Give LLM obvious violations to catch
   - Ensure LLM evaluator is calibrated

5. **Document LLM Evaluation Criteria Clearly**
   - Make prompts explicit about what constitutes pass/fail
   - Include examples of good and bad patterns

### Cost Considerations

**LLM testing is expensive - use strategically:**

- **Property tests**: Traditional (fast, free, exhaustive)
- **Unit tests**: Traditional (fast, free)
- **Integration tests**: Traditional (medium speed, free)
- **E2E tests**: Traditional + selective LLM (slow, costly)
- **Philosophy tests**: LLM-based (slow, costly, but irreplaceable)

**Budget allocation:**
- Run LLM tests on: Final E2E scenarios, philosophy validation, edge cases
- Skip LLM tests on: Unit tests, property tests, performance benchmarks

**Estimated cost:**
- ~5 LLM evaluations per E2E test × 18 scenarios = 90 evaluations
- ~$0.01 per evaluation (GPT-4o) = **~$0.90 per full test run**
- Acceptable for CI/CD on main branch

---

## Layer 1: Property-Based Tests (Philosophical Invariants)

**Purpose**: Verify that philosophical principles hold under ALL possible inputs, not just examples.

### 1.1 Epistemic Humility Properties

```python
# tests/property/test_epistemic_humility.py
from hypothesis import given, strategies as st
import pytest

class TestEpistemicHumilityProperties:
    """
    Vision: "The system should know what it doesn't know"
    Tests: Confidence never exceeds MAX_CONFIDENCE (0.95), decays properly
    """

    @given(
        base_confidence=st.floats(min_value=0.0, max_value=1.0),
        days_old=st.integers(min_value=0, max_value=365),
        decay_rate=st.floats(min_value=0.001, max_value=0.1)
    )
    def test_decay_never_exceeds_base_confidence(self, base_confidence, days_old, decay_rate):
        """
        INVARIANT: Decay can only decrease confidence, never increase it.
        VISION: "Unreinforced memories fade"
        """
        effective = calculate_effective_confidence(base_confidence, days_old, decay_rate)

        assert effective <= base_confidence, \
            f"Decay increased confidence: {base_confidence} → {effective}"
        assert effective >= 0.0, \
            f"Confidence went negative: {effective}"

    @given(
        confidence=st.floats(min_value=0.0, max_value=1.0),
        reinforcement_count=st.integers(min_value=1, max_value=100)
    )
    def test_reinforcement_never_exceeds_max_confidence(self, confidence, reinforcement_count):
        """
        INVARIANT: No matter how many reinforcements, confidence ≤ 0.95
        VISION: "Epistemic humility - never 100% certain"
        """
        boosted = confidence
        for i in range(reinforcement_count):
            boost = get_reinforcement_boost(i + 1)
            boosted = min(0.95, boosted + boost)

        assert boosted <= 0.95, \
            f"Reinforcement exceeded MAX_CONFIDENCE: {boosted}"

    @given(
        stored_confidence=st.floats(min_value=0.0, max_value=0.95),
        days_since_validation=st.integers(min_value=0, max_value=1000)
    )
    def test_passive_decay_is_idempotent(self, stored_confidence, days_since_validation):
        """
        INVARIANT: Computing decay twice gives same result (passive computation)
        VISION: "Passive computation - no background jobs"
        """
        decay1 = calculate_effective_confidence(stored_confidence, days_since_validation)
        decay2 = calculate_effective_confidence(stored_confidence, days_since_validation)

        assert abs(decay1 - decay2) < 1e-10, \
            f"Passive decay not deterministic: {decay1} != {decay2}"
```

### 1.2 Dual Truth Properties

```python
class TestDualTruthProperties:
    """
    Vision: "Database (correspondence truth) + Memory (contextual truth) in equilibrium"
    Tests: DB facts always authoritative, memory never contradicts without explicit conflict
    """

    @given(
        db_value=st.text(min_size=1, max_size=100),
        memory_value=st.text(min_size=1, max_size=100)
    )
    def test_db_memory_conflict_always_detected(self, db_value, memory_value):
        """
        INVARIANT: When DB and memory disagree, conflict MUST be logged
        VISION: "Never silently ignore conflicts"
        """
        if db_value != memory_value:
            conflict = detect_conflict(db_value, memory_value)

            assert conflict is not None, \
                f"Conflict not detected: DB={db_value}, Memory={memory_value}"
            assert conflict.conflict_type == 'memory_vs_db'
            assert conflict.resolution_strategy == 'trust_db'

    def test_db_facts_never_modified_by_memory(self):
        """
        INVARIANT: Memory operations never write to domain database
        VISION: "Ground first, enrich second - never fabricate DB facts"
        """
        # This is a contract test - domain DB connection must be read-only
        with pytest.raises(PermissionError):
            domain_db.execute("UPDATE domain.customers SET name = 'Modified'")
```

### 1.3 Memory Lifecycle Properties

```python
class TestMemoryLifecycleProperties:
    """
    Vision: "Graceful forgetting through state transitions"
    Tests: Valid state transitions, no orphaned states
    """

    @given(
        initial_state=st.sampled_from(['active', 'aging', 'superseded', 'invalidated']),
        transition=st.sampled_from(['decay', 'validate', 'supersede', 'invalidate'])
    )
    def test_state_transitions_are_valid(self, initial_state, transition):
        """
        INVARIANT: Only valid state transitions allowed
        VISION: "Memory lifecycle - active → aging → superseded"
        """
        valid_transitions = {
            'active': {'decay': 'aging', 'supersede': 'superseded', 'invalidate': 'invalidated', 'validate': 'active'},
            'aging': {'validate': 'active', 'supersede': 'superseded', 'invalidate': 'invalidated'},
            'superseded': {},  # Terminal state
            'invalidated': {}  # Terminal state
        }

        if transition in valid_transitions[initial_state]:
            # Transition should succeed
            result = apply_transition(initial_state, transition)
            expected = valid_transitions[initial_state][transition]
            assert result == expected
        else:
            # Invalid transition should raise error
            with pytest.raises(InvalidStateTransitionError):
                apply_transition(initial_state, transition)

    def test_superseded_memories_retain_provenance_chain(self):
        """
        INVARIANT: Superseded memories maintain superseded_by_memory_id chain
        VISION: "Don't delete - deprioritize and track provenance"
        """
        original = create_semantic_memory(subject="customer:1", predicate="pref", value="A")
        updated = supersede_memory(original, new_value="B")

        assert original.status == 'superseded'
        assert original.superseded_by_memory_id == updated.memory_id
        assert updated.status == 'active'

        # Can traverse provenance chain
        chain = get_provenance_chain(updated.memory_id)
        assert original.memory_id in chain
```

---

## Layer 2: Domain Unit Tests (Business Logic)

**Purpose**: Test pure domain logic in isolation (fast, no I/O)

### 2.1 Entity Resolution Tests

```python
# tests/unit/domain/test_entity_resolver.py
import pytest
from tests.fixtures.factories import EntityFactory, MockEntityRepository

class TestEntityResolver:
    """Test hybrid entity resolution algorithm"""

    @pytest.fixture
    def mock_repo(self):
        repo = MockEntityRepository()
        # Seed with test entities
        repo.add_entity(EntityFactory.create(
            entity_id="customer:acme_123",
            canonical_name="Acme Corporation"
        ))
        return repo

    @pytest.mark.asyncio
    async def test_exact_match_returns_confidence_1_0(self, mock_repo):
        """
        SCENARIO: User types exact canonical name
        EXPECTED: Instant resolution, confidence = 1.0, method = 'exact'
        VISION: "Deterministic fast path for 95% of cases"
        """
        resolver = EntityResolver(entity_repo=mock_repo)
        context = ResolutionContext(user_id="user_1", recent_entities=[])

        result = await resolver.resolve(mention="Acme Corporation", context=context)

        assert result.entity_id == "customer:acme_123"
        assert result.confidence == 1.0
        assert result.method == "exact"
        assert result.latency_ms < 50  # Fast path target

    @pytest.mark.asyncio
    async def test_fuzzy_match_above_threshold_creates_alias(self, mock_repo):
        """
        SCENARIO: User types "ACME Corp" (fuzzy match to "Acme Corporation")
        EXPECTED: Resolve with confidence based on similarity, learn alias
        VISION: "Self-improving - high-confidence resolutions create aliases"
        """
        resolver = EntityResolver(entity_repo=mock_repo)
        context = ResolutionContext(user_id="user_1", recent_entities=[])

        result = await resolver.resolve(mention="ACME Corp", context=context)

        assert result.entity_id == "customer:acme_123"
        assert 0.85 <= result.confidence < 1.0
        assert result.method == "fuzzy"

        # Verify alias was learned
        alias = await mock_repo.get_alias("ACME Corp", user_id=None)
        assert alias is not None
        assert alias.canonical_entity_id == "customer:acme_123"

    @pytest.mark.asyncio
    async def test_ambiguous_resolution_requires_disambiguation(self, mock_repo):
        """
        SCENARIO: "Apple" could be Apple Inc or Apple Farm Supply
        EXPECTED: Return candidates, require user selection
        VISION: "Disambiguate when multiple references possible"
        """
        mock_repo.add_entity(EntityFactory.create(
            entity_id="customer:apple_tech",
            canonical_name="Apple Inc"
        ))
        mock_repo.add_entity(EntityFactory.create(
            entity_id="customer:apple_farm",
            canonical_name="Apple Farm Supply"
        ))

        resolver = EntityResolver(entity_repo=mock_repo)
        context = ResolutionContext(user_id="user_1", recent_entities=[])

        with pytest.raises(AmbiguousEntityError) as exc_info:
            await resolver.resolve(mention="Apple", context=context)

        assert len(exc_info.value.candidates) == 2
        assert exc_info.value.disambiguation_required is True
```

### 2.2 Memory Extraction Tests

```python
class TestMemoryExtractor:
    """Test LLM-based semantic extraction"""

    @pytest.mark.asyncio
    async def test_explicit_preference_extracts_semantic_memory(self):
        """
        SCENARIO: User says "Remember: Gai Media prefers Friday deliveries"
        EXPECTED: Create semantic memory with confidence ~0.7
        VISION: "Explicit statements → immediate learning"
        """
        extractor = MemoryExtractor(llm_service=MockLLMService())
        event = ChatEvent(content="Remember: Gai Media prefers Friday deliveries", ...)
        entities = [Entity(entity_id="customer:gai_123", name="Gai Media")]

        result = await extractor.extract(event, entities)

        assert len(result.semantic_memories) == 1
        semantic = result.semantic_memories[0]

        assert semantic.subject_entity_id == "customer:gai_123"
        assert semantic.predicate == "delivery_preference"
        assert semantic.object_value == {"type": "day_of_week", "value": "Friday"}
        assert 0.6 <= semantic.confidence <= 0.8  # Explicit statement confidence
        assert semantic.source_type == "episodic"

    @pytest.mark.asyncio
    async def test_question_does_not_extract_semantic_memory(self):
        """
        SCENARIO: User asks "When should we deliver to Gai Media?"
        EXPECTED: No semantic extraction (questions don't assert facts)
        VISION: "Don't extract from questions - only statements"
        """
        extractor = MemoryExtractor(llm_service=MockLLMService())
        event = ChatEvent(content="When should we deliver to Gai Media?", ...)
        entities = [Entity(entity_id="customer:gai_123", name="Gai Media")]

        result = await extractor.extract(event, entities)

        assert len(result.semantic_memories) == 0
        assert result.event_type == "question"
```

### 2.3 Retrieval Scoring Tests

```python
class TestMultiSignalRetrieval:
    """Test deterministic multi-signal scoring"""

    def test_semantic_similarity_signal(self):
        """
        SCENARIO: Query about "delivery" should score delivery-related memories higher
        EXPECTED: Cosine similarity drives primary ranking
        VISION: "Semantic similarity - vector distance"
        """
        query = Query(
            embedding=generate_embedding("delivery schedule"),
            entities=[]
        )

        memory_relevant = Memory(
            embedding=generate_embedding("delivery preferences"),
            entities=[]
        )
        memory_irrelevant = Memory(
            embedding=generate_embedding("payment terms"),
            entities=[]
        )

        score_relevant = score_memory_relevance(memory_relevant, query)
        score_irrelevant = score_memory_relevance(memory_irrelevant, query)

        assert score_relevant > score_irrelevant

    def test_entity_overlap_signal(self):
        """
        SCENARIO: Query mentions "Gai Media" and "invoices"
        EXPECTED: Memories mentioning both entities score highest
        VISION: "Entity overlap - captures aboutness"
        """
        query = Query(
            embedding=np.random.rand(1536),
            entities=["customer:gai_123", "invoice:inv_1009"]
        )

        memory_both = Memory(entities=["customer:gai_123", "invoice:inv_1009"])
        memory_one = Memory(entities=["customer:gai_123"])
        memory_none = Memory(entities=[])

        score_both = score_memory_relevance(memory_both, query)
        score_one = score_memory_relevance(memory_one, query)
        score_none = score_memory_relevance(memory_none, query)

        assert score_both > score_one > score_none

    def test_confidence_penalty_applies_passive_decay(self):
        """
        SCENARIO: Two identical memories, one fresh (0.8 conf), one aged (0.4 conf)
        EXPECTED: Fresh memory scores higher due to confidence penalty
        VISION: "Passive decay - compute on-demand"
        """
        memory_fresh = SemanticMemory(
            confidence=0.8,
            last_validated_at=datetime.utcnow() - timedelta(days=5),
            ...
        )
        memory_aged = SemanticMemory(
            confidence=0.8,
            last_validated_at=datetime.utcnow() - timedelta(days=100),
            ...
        )

        query = Query(...)

        score_fresh = score_memory_relevance(memory_fresh, query)
        score_aged = score_memory_relevance(memory_aged, query)

        assert score_fresh > score_aged

        # Verify passive decay was applied
        effective_fresh = calculate_effective_confidence(memory_fresh)
        effective_aged = calculate_effective_confidence(memory_aged)
        assert effective_aged < effective_fresh
```

---

## Layer 3: Integration Tests (Infrastructure)

**Purpose**: Test database operations, external services, infrastructure adapters

### 3.1 Database Integration Tests

```python
# tests/integration/test_entity_repository.py
import pytest
from tests.fixtures.database import test_db_session

class TestEntityRepository:
    """Test PostgreSQL entity repository implementation"""

    @pytest.mark.asyncio
    async def test_fuzzy_search_uses_pg_trgm(self, test_db_session):
        """
        SCENARIO: Search for "Acme" using fuzzy matching
        EXPECTED: pg_trgm finds similar names with similarity scores
        VISION: "pg_trgm excellent at fuzzy text matching"
        """
        repo = PostgresEntityRepository(test_db_session)

        # Seed database
        await repo.create(Entity(canonical_name="Acme Corporation", ...))
        await repo.create(Entity(canonical_name="Acme Industries", ...))
        await repo.create(Entity(canonical_name="Beta Corp", ...))

        results = await repo.fuzzy_search(query="Acme", threshold=0.7)

        assert len(results) == 2
        assert all("Acme" in r.canonical_name for r in results)
        assert all(r.similarity_score >= 0.7 for r in results)
        assert results[0].similarity_score >= results[1].similarity_score  # Sorted desc

    @pytest.mark.asyncio
    async def test_pgvector_semantic_search(self, test_db_session):
        """
        SCENARIO: Semantic search for similar memories
        EXPECTED: pgvector returns top-k by cosine similarity
        VISION: "pgvector for semantic search <50ms"
        """
        repo = PostgresMemoryRepository(test_db_session)

        # Create memories with embeddings
        memory1 = await repo.create(SemanticMemory(
            fact="Gai Media prefers Friday deliveries",
            embedding=generate_embedding("Friday delivery preference")
        ))
        memory2 = await repo.create(SemanticMemory(
            fact="TC Boiler uses NET15 terms",
            embedding=generate_embedding("payment terms NET15")
        ))

        # Search for delivery-related memories
        query_embedding = generate_embedding("delivery schedule")

        import time
        start = time.time()
        results = await repo.semantic_search(query_embedding, limit=10)
        latency_ms = (time.time() - start) * 1000

        assert latency_ms < 50  # Performance target
        assert results[0].memory_id == memory1.memory_id  # Delivery memory ranks first
```

### 3.2 LLM Service Integration Tests

```python
class TestOpenAILLMService:
    """Test LLM integration (uses real OpenAI API in CI with test key)"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_semantic_extraction_quality(self):
        """
        SCENARIO: Extract facts from complex statement
        EXPECTED: LLM correctly parses triples with confidence
        VISION: "LLM for semantic parsing - genuinely hard with rules"
        """
        llm_service = OpenAILLMService()

        text = "Gai Media prefers Friday deliveries and NET30 payment terms"
        entities = [Entity(entity_id="customer:gai_123", name="Gai Media")]

        result = await llm_service.extract_triples(text, entities)

        assert len(result.triples) == 2

        # Verify delivery preference triple
        delivery_triple = next(t for t in result.triples if "delivery" in t.predicate)
        assert delivery_triple.subject_entity_id == "customer:gai_123"
        assert "Friday" in str(delivery_triple.object_value)

        # Verify payment terms triple
        payment_triple = next(t for t in result.triples if "payment" in t.predicate)
        assert payment_triple.subject_entity_id == "customer:gai_123"
        assert "NET30" in str(payment_triple.object_value)
```

---

## Layer 4: E2E Scenario Tests (Project Description)

**Purpose**: Test all 18 scenarios from ProjectDescription.md end-to-end

```python
# tests/e2e/test_scenarios.py
import pytest
from httpx import AsyncClient

class TestProjectScenarios:
    """
    Test all 18 scenarios from ProjectDescription.md
    Each test is a complete user journey
    """

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_scenario_01_overdue_invoice_with_preference_recall(self, api_client):
        """
        SCENARIO 1: Overdue invoice follow-up with preference recall

        Context: Finance agent wants to nudge customer while honoring delivery preferences.
        Prior memory/DB: domain.invoices shows Kai Media has INV-1009 due 2025-09-30;
                        memory: "prefers Friday deliveries".
        User: "Draft an email for Kai Media about their unpaid invoice and mention
               their preferred delivery day for the next shipment."
        Expected: Retrieval surfaces INV-1009 (open, amount, due date) + memory preference.
                 Reply mentions invoice details and references Friday delivery.
                 Memory update: add episodic note that an invoice reminder was initiated today.
        """
        # Step 1: Seed domain database
        await seed_domain_db({
            "customers": [{"name": "Kai Media", "customer_id": "kai_123"}],
            "invoices": [{
                "invoice_id": "inv_1009",
                "customer_id": "kai_123",
                "invoice_number": "INV-1009",
                "amount": 1200.00,
                "due_date": "2025-09-30",
                "status": "open"
            }]
        })

        # Step 2: Seed memory (prior session stated preference)
        await api_client.post("/api/v1/chat", json={
            "user_id": "finance_agent",
            "message": "Remember: Kai Media prefers Friday deliveries"
        })

        # Step 3: User query
        response = await api_client.post("/api/v1/chat", json={
            "user_id": "finance_agent",
            "message": "Draft an email for Kai Media about their unpaid invoice and mention their preferred delivery day for the next shipment."
        })

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Check response mentions invoice details
        assert "INV-1009" in data["response"]
        assert "1200" in data["response"] or "$1,200" in data["response"]
        assert "2025-09-30" in data["response"] or "September 30" in data["response"]

        # Check response mentions Friday delivery preference
        assert "Friday" in data["response"]

        # Check domain facts were retrieved
        assert any(
            fact["table"] == "domain.invoices" and fact["invoice_id"] == "inv_1009"
            for fact in data["augmentation"]["domain_facts"]
        )

        # Check memory was retrieved
        assert any(
            "Friday" in mem["fact"] and "delivery" in mem["fact"]
            for mem in data["augmentation"]["memories_retrieved"]
        )

        # Check episodic memory was created
        assert len(data["memories_created"]) >= 1
        episodic = next(m for m in data["memories_created"] if m["memory_type"] == "episodic")
        assert "invoice" in episodic["summary"].lower()
        assert "kai media" in episodic["summary"].lower()

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_scenario_07_conflicting_memories_consolidation(self, api_client):
        """
        SCENARIO 7: Conflicting memories → consolidation rules

        Context: Two sessions recorded delivery preference as Thursday vs Friday.
        User: "What day should we deliver to Kai Media?"
        Expected: Consolidation picks the most recent or most reinforced value;
                 reply cites confidence and offers to confirm.
                 If confirmed, demote conflicting memory via supersession.
        """
        # Session 1: State Thursday
        await api_client.post("/api/v1/chat", json={
            "user_id": "ops_manager",
            "session_id": "session_001",
            "message": "Kai Media prefers Thursday deliveries"
        })

        # Wait 5 days (simulated)

        # Session 2: State Friday (conflicting)
        await api_client.post("/api/v1/chat", json={
            "user_id": "ops_manager",
            "session_id": "session_002",
            "message": "Actually, Kai Media prefers Friday deliveries"
        })

        # Query for preference
        response = await api_client.post("/api/v1/chat", json={
            "user_id": "ops_manager",
            "message": "What day should we deliver to Kai Media?"
        })

        data = response.json()

        # Should use most recent (Friday)
        assert "Friday" in data["response"]

        # Should mention conflict or confidence
        assert "recently" in data["response"].lower() or \
               "updated" in data["response"].lower() or \
               "confidence" in data["response"].lower()

        # Check conflict was logged
        conflicts = await api_client.get("/api/v1/conflicts", params={"user_id": "ops_manager"})
        assert conflicts.status_code == 200

        conflict_data = conflicts.json()
        assert len(conflict_data["conflicts"]) >= 1

        conflict = conflict_data["conflicts"][0]
        assert conflict["conflict_type"] == "memory_vs_memory"
        assert "Thursday" in str(conflict["conflict_data"])
        assert "Friday" in str(conflict["conflict_data"])

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_scenario_10_active_recall_for_stale_facts(self, api_client):
        """
        SCENARIO 10: Active recall to validate stale facts

        Context: Preference older than 90 days with low reinforcement.
        User: "Schedule a delivery for Kai Media next week."
        Expected: Before finalizing, system asks: "We have Friday preference on record
                 from 2025-05-10; still accurate?" If confirmed, resets decay;
                 if changed, updates semantic memory.
        """
        # Create aged memory (91 days old)
        aged_memory = await create_semantic_memory(
            user_id="ops_manager",
            subject_entity_id="customer:kai_123",
            predicate="delivery_preference",
            object_value="Friday",
            confidence=0.7,
            last_validated_at=datetime.utcnow() - timedelta(days=91)
        )

        # User query
        response = await api_client.post("/api/v1/chat", json={
            "user_id": "ops_manager",
            "message": "Schedule a delivery for Kai Media next week."
        })

        data = response.json()

        # Should prompt for validation
        assert "still accurate" in data["response"].lower() or \
               "confirm" in data["response"].lower() or \
               "verify" in data["response"].lower()

        # Should mention the aged preference
        assert "Friday" in data["response"]
        assert "2025-05-10" in data["response"] or "May" in data["response"]

        # Memory should be marked for validation
        memory_status = await api_client.get(f"/api/v1/memories/{aged_memory.memory_id}")
        assert memory_status.json()["status"] == "aging"
```

---

## Layer 5: Philosophy Validation Tests

**Purpose**: Verify vision principles are actually embodied in behavior

### 5.1 Epistemic Humility Validation

```python
class TestEpistemicHumilityBehavior:
    """
    Vision: "The system should know what it doesn't know"
    Tests: System exhibits epistemic humility in edge cases
    """

    @pytest.mark.asyncio
    async def test_low_confidence_memory_triggers_hedging_language(self, api_client):
        """
        VISION: "Low confidence → cite source, hedge language"
        """
        # Create low-confidence memory
        await create_semantic_memory(
            subject="customer:test_123",
            predicate="payment_terms",
            object_value="NET30",
            confidence=0.4  # Low confidence
        )

        response = await api_client.post("/api/v1/chat", json={
            "message": "What are the payment terms for Test Corp?"
        })

        text = response.json()["response"].lower()

        # Should use hedging language
        hedging_phrases = [
            "based on limited information",
            "according to our conversation",
            "we believe",
            "may be",
            "suggest",
            "appears to be"
        ]

        assert any(phrase in text for phrase in hedging_phrases), \
            f"Low confidence memory did not trigger hedging language: {text}"

    @pytest.mark.asyncio
    async def test_no_information_acknowledges_gap(self, api_client):
        """
        VISION: "No information → acknowledge gap, don't fabricate"
        """
        response = await api_client.post("/api/v1/chat", json={
            "message": "What are the payment terms for NonexistentCorp?"
        })

        text = response.json()["response"].lower()

        # Should acknowledge lack of information
        gap_acknowledgments = [
            "don't have information",
            "no record",
            "unable to find",
            "not found",
            "no data"
        ]

        assert any(phrase in text for phrase in gap_acknowledgments)

        # Should NOT fabricate plausible-sounding answer
        assert "NET30" not in text  # Don't hallucinate common terms
```

### 5.2 Dual Truth Equilibrium Validation

```python
class TestDualTruthEquilibrium:
    """
    Vision: "Database (correspondence truth) + Memory (contextual truth) in equilibrium"
    Tests: System balances DB facts with memory context
    """

    @pytest.mark.asyncio
    async def test_db_facts_always_included_when_available(self, api_client):
        """
        VISION: "Ground first, enrich second"
        """
        # Seed domain DB
        await seed_domain_db({
            "invoices": [{
                "invoice_id": "inv_test",
                "amount": 5000.00,
                "status": "open",
                "due_date": "2025-12-31"
            }]
        })

        # Add memory context
        await create_semantic_memory(
            subject="invoice:inv_test",
            predicate="note",
            object_value="Customer is typically 2-3 days late"
        )

        response = await api_client.post("/api/v1/chat", json={
            "message": "Tell me about invoice INV-TEST"
        })

        data = response.json()

        # Response should include DB facts
        assert "5000" in data["response"]
        assert "open" in data["response"].lower()

        # DB facts should appear first in augmentation
        domain_facts = data["augmentation"]["domain_facts"]
        memories = data["augmentation"]["memories_retrieved"]

        assert len(domain_facts) > 0, "DB facts missing"

        # Memory context should enrich
        assert "2-3 days" in data["response"] or "late" in data["response"]

    @pytest.mark.asyncio
    async def test_memory_never_overrides_current_db_state(self, api_client):
        """
        VISION: "Memory vs DB conflict → trust DB but surface discrepancy"
        """
        # Seed DB with current state
        await seed_domain_db({
            "sales_orders": [{
                "so_id": "so_123",
                "status": "fulfilled"  # Current DB state
            }]
        })

        # Create outdated memory
        await create_semantic_memory(
            subject="sales_order:so_123",
            predicate="status",
            object_value="in_fulfillment",  # Outdated
            last_validated_at=datetime.utcnow() - timedelta(days=10)
        )

        response = await api_client.post("/api/v1/chat", json={
            "message": "What's the status of SO-123?"
        })

        data = response.json()

        # Should report current DB state
        assert "fulfilled" in data["response"].lower()

        # Should log conflict
        assert len(data["conflicts_detected"]) > 0
        conflict = data["conflicts_detected"][0]
        assert conflict["conflict_type"] == "memory_vs_db"
        assert conflict["resolution_strategy"] == "trust_db"
```

### 5.3 Graceful Forgetting Validation

```python
class TestGracefulForgetting:
    """
    Vision: "Forgetting is not a bug - it's essential to intelligence"
    Tests: System exhibits graceful forgetting behaviors
    """

    @pytest.mark.asyncio
    async def test_consolidation_replaces_many_episodes_with_summary(self, api_client):
        """
        VISION: "Replace many specific memories with one abstract summary"
        """
        # Create 15 episodic memories about same customer
        for i in range(15):
            await api_client.post("/api/v1/chat", json={
                "user_id": "test_user",
                "session_id": f"session_{i // 5}",  # 3 sessions
                "message": f"Discussed delivery preferences with Test Corp - iteration {i}"
            })

        # Trigger consolidation
        response = await api_client.post("/api/v1/consolidate", json={
            "user_id": "test_user"
        })

        assert response.status_code == 200
        summary_data = response.json()

        # Should create summary
        assert "summary_id" in summary_data

        # Summary should reference source episodes
        source_data = summary_data["source_data"]
        assert len(source_data["episodic_ids"]) >= 10
        assert len(source_data["session_ids"]) == 3

        # Retrieval should now prefer summary
        query_response = await api_client.post("/api/v1/chat", json={
            "message": "What do we know about Test Corp?"
        })

        retrieved = query_response.json()["augmentation"]["memories_retrieved"]

        # Summary should rank high
        summary_mem = next((m for m in retrieved if m["memory_type"] == "summary"), None)
        assert summary_mem is not None
        assert summary_mem["relevance_score"] > 0.8  # High relevance
```

---

## Layer 6: Performance & Cost Tests

### 6.1 Latency Benchmarks

```python
# tests/performance/test_latency.py
import pytest
import time

class TestPerformanceTargets:
    """Verify P95 latency targets from roadmap"""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_entity_resolution_fast_path_under_50ms(self, benchmark):
        """
        TARGET: Entity resolution (fast path) P95 < 50ms
        VISION: "Deterministic for 95%, LLM for 5%"
        """
        resolver = EntityResolver(...)

        def resolve():
            return asyncio.run(resolver.resolve("Acme Corporation", ...))

        result = benchmark(resolve)

        # P95 latency
        p95_latency_ms = result.stats.get('mean') * 1000
        assert p95_latency_ms < 50, \
            f"Fast path too slow: {p95_latency_ms}ms > 50ms target"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_semantic_search_under_50ms(self, benchmark, test_db_with_1000_memories):
        """
        TARGET: Semantic search P95 < 50ms
        VISION: "pgvector with IVFFlat index <50ms"
        """
        repo = PostgresMemoryRepository(test_db_with_1000_memories)
        query_embedding = np.random.rand(1536)

        def search():
            return asyncio.run(repo.semantic_search(query_embedding, limit=50))

        result = benchmark(search)

        p95_latency_ms = result.stats.get('mean') * 1000
        assert p95_latency_ms < 50

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_chat_endpoint_under_800ms(self, benchmark, api_client):
        """
        TARGET: /chat endpoint P95 < 800ms
        VISION: "End-to-end including LLM generation"
        """
        def chat():
            return asyncio.run(api_client.post("/api/v1/chat", json={
                "message": "What's the status of Gai Media's order?"
            }))

        result = benchmark(chat)

        p95_latency_ms = result.stats.get('mean') * 1000
        assert p95_latency_ms < 800
```

### 6.2 Cost Validation

```python
class TestCostTargets:
    """
    TARGET: ~$0.002 per conversational turn
    VISION: "Surgical LLM use - deterministic where it excels"
    """

    @pytest.mark.asyncio
    async def test_llm_usage_percentage_under_10_percent(self, api_client):
        """
        Verify that LLM is only used for ~5-10% of operations
        """
        # Run 100 diverse queries
        llm_call_count = 0
        deterministic_count = 0

        for i in range(100):
            with patch_llm_service() as mock_llm:
                await api_client.post("/api/v1/chat", json={
                    "message": f"Test query {i}: {generate_random_query()}"
                })

                if mock_llm.called:
                    llm_call_count += 1
                else:
                    deterministic_count += 1

        llm_percentage = (llm_call_count / 100) * 100

        assert llm_percentage < 15, \
            f"LLM used too frequently: {llm_percentage}% > 15% target"

        print(f"LLM usage: {llm_percentage}% (target: <10%)")
        print(f"Deterministic: {100 - llm_percentage}%")
```

---

## Testing Infrastructure

### Fixtures and Factories

```python
# tests/fixtures/factories.py
from dataclasses import dataclass
from typing import Any
import uuid
from datetime import datetime

class EntityFactory:
    """Factory for creating test entities"""

    @staticmethod
    def create(
        entity_id: str | None = None,
        entity_type: str = "customer",
        canonical_name: str = "Test Corp",
        **kwargs
    ) -> CanonicalEntity:
        return CanonicalEntity(
            entity_id=entity_id or f"{entity_type}:{uuid.uuid4().hex[:8]}",
            entity_type=entity_type,
            canonical_name=canonical_name,
            external_ref=kwargs.get('external_ref', {}),
            properties=kwargs.get('properties', {}),
            created_at=kwargs.get('created_at', datetime.utcnow()),
            updated_at=kwargs.get('updated_at', datetime.utcnow())
        )

class MemoryFactory:
    """Factory for creating test memories"""

    @staticmethod
    def create_semantic(
        subject_entity_id: str = "customer:test_123",
        predicate: str = "preference",
        object_value: Any = "test_value",
        confidence: float = 0.7,
        **kwargs
    ) -> SemanticMemory:
        return SemanticMemory(
            memory_id=kwargs.get('memory_id', None),
            user_id=kwargs.get('user_id', 'test_user'),
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            predicate_type=kwargs.get('predicate_type', 'preference'),
            object_value=object_value,
            confidence=confidence,
            confidence_factors=kwargs.get('confidence_factors', {}),
            reinforcement_count=kwargs.get('reinforcement_count', 1),
            last_validated_at=kwargs.get('last_validated_at', datetime.utcnow()),
            source_type=kwargs.get('source_type', 'episodic'),
            status=kwargs.get('status', 'active'),
            importance=kwargs.get('importance', 0.5),
            created_at=kwargs.get('created_at', datetime.utcnow()),
            updated_at=kwargs.get('updated_at', datetime.utcnow())
        )
```

### Mock Services

```python
# tests/fixtures/mock_services.py
class MockEntityRepository(EntityRepositoryPort):
    """In-memory entity repository for fast unit tests"""

    def __init__(self):
        self._entities: dict[str, CanonicalEntity] = {}
        self._aliases: dict[str, EntityAlias] = {}

    async def get_by_id(self, entity_id: str) -> Optional[CanonicalEntity]:
        return self._entities.get(entity_id)

    async def fuzzy_search(self, query: str, threshold: float) -> List[CanonicalEntity]:
        # Simple substring matching for testing
        results = []
        for entity in self._entities.values():
            if query.lower() in entity.canonical_name.lower():
                results.append(entity)
        return results

    def add_entity(self, entity: CanonicalEntity):
        """Test helper - add entity to mock repo"""
        self._entities[entity.entity_id] = entity

class MockLLMService(LLMServicePort):
    """Mock LLM service with deterministic responses"""

    def __init__(self):
        self.call_count = 0
        self.last_request = None

    async def extract_triples(self, text: str, entities: List[Entity]) -> ExtractionResult:
        self.call_count += 1
        self.last_request = {"text": text, "entities": entities}

        # Return deterministic test triples
        if "Friday" in text and "deliver" in text:
            return ExtractionResult(triples=[
                Triple(
                    subject_entity_id=entities[0].entity_id,
                    predicate="delivery_preference",
                    object_value="Friday",
                    confidence=0.75
                )
            ])

        return ExtractionResult(triples=[])
```

---

## Test Coverage Targets

| Layer | Coverage Target | Rationale |
|-------|----------------|-----------|
| Domain Services | 95% | Core business logic - must be thoroughly tested |
| Domain Entities/Value Objects | 90% | Pure logic, easy to test |
| Repository Implementations | 80% | Integration tests cover main paths |
| API Routes | 85% | E2E tests cover critical paths |
| Utils | 90% | Pure functions, high test value |
| **Overall** | **85-90%** | High confidence in correctness |

---

## Continuous Testing Strategy

### Pre-Commit Hooks
```bash
# .pre-commit-config.yaml
- hook: pytest
  stages: [commit]
  args: [--quick, tests/unit]  # Fast unit tests only

- hook: mypy
  stages: [commit]
  args: [--strict, src/]

- hook: ruff
  stages: [commit]
  args: [check, src/, tests/]
```

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
test-unit:
  runs-on: ubuntu-latest
  steps:
    - run: pytest tests/unit -v --cov --cov-fail-under=90

test-integration:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: ankane/pgvector:latest
  steps:
    - run: pytest tests/integration -v --cov-fail-under=80

test-e2e:
  runs-on: ubuntu-latest
  steps:
    - run: pytest tests/e2e -v --cov-fail-under=70

test-philosophy:
  runs-on: ubuntu-latest
  steps:
    - run: pytest tests/property tests/philosophy -v
    - name: Generate philosophy compliance report
      run: python scripts/generate_philosophy_report.py
```

---

## Success Criteria

### Quantitative
- ✅ 90%+ domain layer coverage
- ✅ 85%+ overall coverage
- ✅ All 18 project scenarios passing
- ✅ P95 latencies within targets
- ✅ LLM cost <$0.003 per turn

### Qualitative
- ✅ Every vision principle has explicit tests
- ✅ Philosophical invariants verified via property tests
- ✅ Confidence in production deployment
- ✅ Tests serve as executable documentation

---

## Philosophy → Code Traceability

| Vision Principle | Test Class | Verification Method |
|-----------------|------------|---------------------|
| Epistemic Humility | `TestEpistemicHumilityProperties` | Property-based confidence bounds |
| Dual Truth | `TestDualTruthEquilibrium` | DB vs memory conflict detection |
| Graceful Forgetting | `TestGracefulForgetting` | Consolidation behavior |
| Problem of Reference | `TestEntityResolver` | 5-stage resolution accuracy |
| Temporal Validity | `TestMemoryLifecycleProperties` | State transition invariants |
| Explainability | `TestProvenanceTracking` | All responses have citations |
| Learning | `TestMemoryTransformation` | Episodic→Semantic→Procedural flow |

**Every principle can be verified. Every test traces to vision.**

---

This testing infrastructure ensures that the implementation truly embodies the philosophical vision, not just implements functional requirements.
