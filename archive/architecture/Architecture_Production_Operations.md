# Production Operations Guide

**Supplement to Architecture Documents**
**Version:** 1.0
**Purpose:** Production-readiness specifications for intelligence components

---

## Overview

This document supplements the main architecture documents with operational details needed for production deployment:
- Error handling & resilience patterns
- Performance optimization strategies
- Monitoring & observability
- Async coordination patterns
- Rate limiting & circuit breakers

**Read this after:** Architecture_Master.md and Architecture_Intelligence_DecisionSupport.md

---

## 1. Error Handling & Resilience

### 1.1 Intelligence Component Error Patterns

```python
class IntelligenceComponent(ABC):
    """Base class for all intelligence components with standard error handling"""

    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = MetricsClient()
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=60  # seconds
        )

    @contextmanager
    def timeout_context(self, seconds: float):
        """Standard timeout wrapper for all intelligence operations"""
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation exceeded {seconds}s timeout")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        try:
            yield
        finally:
            signal.alarm(0)

    def handle_error(self, operation: str, error: Exception, entity_id: Optional[str] = None):
        """Standard error handling and logging"""
        self.logger.error(
            f"{operation} failed",
            extra={
                'operation': operation,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'entity_id': entity_id
            },
            exc_info=True
        )

        self.metrics.increment(
            f'{self.__class__.__name__.lower()}.error',
            tags={
                'operation': operation,
                'error_type': type(error).__name__
            }
        )
```

### 1.2 PatternAnalyzer Error Handling

```python
class PatternAnalyzer(IntelligenceComponent):
    """Pattern analysis with comprehensive error handling"""

    def analyze_entity(self, entity_id: str) -> List[PatternInsight]:
        """
        Analyze entity with graceful degradation.

        Error handling strategy:
        - Individual pattern failures don't block others
        - Timeouts return partial results
        - Database errors return cached results if available
        - All errors logged and metered
        """
        patterns = []

        # Try cache first (fast path with error handling)
        try:
            cached = self._get_cached_patterns(entity_id)
            if cached:
                self.logger.info(f"Pattern cache hit for {entity_id}")
                self.metrics.increment('pattern_analyzer.cache_hit')
                return cached
        except Exception as e:
            # Cache errors should not block analysis
            self.handle_error('cache_retrieve', e, entity_id)

        self.metrics.increment('pattern_analyzer.cache_miss')

        # Run each pattern detection independently
        pattern_methods = [
            ('rush_order', self.detect_rush_order_pattern),
            ('payment_timing', self.detect_payment_timing_shift),
            ('anomaly', self.detect_anomalies)
        ]

        for method_name, method in pattern_methods:
            try:
                with self.timeout_context(seconds=5.0):
                    result = method(entity_id)
                    if result:
                        patterns.append(result)
                        self.metrics.increment(
                            'pattern_analyzer.pattern_detected',
                            tags={'pattern_type': method_name}
                        )

            except TimeoutError:
                self.logger.warning(
                    f"Pattern detection timeout: {method_name} for {entity_id}",
                    extra={'pattern_type': method_name, 'entity_id': entity_id}
                )
                self.metrics.increment(
                    'pattern_analyzer.timeout',
                    tags={'pattern_type': method_name}
                )

            except DatabaseError as e:
                # Database errors are serious - log and alert
                self.handle_error(f'pattern_detection_{method_name}', e, entity_id)
                self.metrics.increment(
                    'pattern_analyzer.database_error',
                    tags={'pattern_type': method_name}
                )

            except Exception as e:
                # Unexpected errors - log but continue
                self.handle_error(f'pattern_detection_{method_name}', e, entity_id)

        # Store successful patterns in cache
        if patterns:
            try:
                self._cache_patterns(entity_id, patterns)
            except Exception as e:
                # Cache write failures shouldn't fail the request
                self.handle_error('cache_write', e, entity_id)

        return patterns

    def _get_cached_patterns(self, entity_id: str) -> Optional[List[PatternInsight]]:
        """Retrieve from cache with timeout"""
        cached = self.db.query("""
            SELECT pattern_type, confidence, significance, insight, data, recommendation
            FROM app.customer_patterns
            WHERE customer_id = %s
            AND computed_at > NOW() - INTERVAL '24 hours'
            AND confidence > 0.6
            ORDER BY significance DESC
        """, (entity_id,), timeout=1.0)  # 1 second timeout for cache reads

        if cached:
            return [PatternInsight(**row) for row in cached]
        return None

    def _cache_patterns(self, entity_id: str, patterns: List[PatternInsight]):
        """Store patterns in cache"""
        for pattern in patterns:
            self.db.execute("""
                INSERT INTO app.customer_patterns
                (customer_id, pattern_type, confidence, significance,
                 insight, data, recommendation, computed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (customer_id, pattern_type)
                DO UPDATE SET
                    confidence = EXCLUDED.confidence,
                    significance = EXCLUDED.significance,
                    insight = EXCLUDED.insight,
                    data = EXCLUDED.data,
                    recommendation = EXCLUDED.recommendation,
                    computed_at = NOW()
            """, (
                entity_id,
                pattern.pattern_type,
                pattern.confidence,
                pattern.significance,
                pattern.insight,
                json.dumps(pattern.data),
                pattern.recommendation
            ), timeout=2.0)  # 2 second timeout for cache writes
```

### 1.3 LLM Call Resilience (ResponseGenerator)

```python
class ResponseGenerator(IntelligenceComponent):
    """Response generation with LLM fallback and retry logic"""

    def __init__(self, config: Config):
        super().__init__(config)
        self.primary_llm = LLMClient(
            model="gpt-4",
            api_key=config.openai_api_key,
            timeout=30.0
        )
        self.fallback_llm = LLMClient(
            model="gpt-3.5-turbo",
            api_key=config.openai_api_key,
            timeout=15.0
        )
        self.retry_policy = RetryPolicy(
            max_attempts=3,
            backoff_multiplier=2,
            initial_delay=1.0
        )

    def generate(self, context: SynthesizedContext) -> GeneratedResponse:
        """Generate response with retry and fallback logic"""

        prompt = self.build_prompt(context)

        # Try primary LLM with retries
        for attempt in range(self.retry_policy.max_attempts):
            try:
                raw_response = self._call_llm_with_timeout(
                    self.primary_llm,
                    prompt,
                    context.synthesis_complexity
                )

                # Success - check quality and return
                passed, quality_score = self.apply_quality_gates(raw_response, context)

                if passed or quality_score > 0.5:
                    return self._build_response(raw_response, context, quality_score)

                # Quality too low - retry with stricter prompt
                self.logger.warning(
                    f"Response quality too low ({quality_score:.2f}), retrying",
                    extra={'attempt': attempt + 1, 'quality_score': quality_score}
                )
                prompt = self._enhance_prompt_for_quality(prompt, context)
                continue

            except RateLimitError as e:
                # Rate limit - wait and retry
                delay = self.retry_policy.get_delay(attempt)
                self.logger.warning(f"Rate limit hit, waiting {delay}s before retry {attempt+1}")
                self.metrics.increment('response_generator.rate_limit')
                time.sleep(delay)
                continue

            except TimeoutError as e:
                # Timeout on primary - try fallback immediately
                self.logger.error(f"Primary LLM timeout on attempt {attempt+1}")
                self.metrics.increment('response_generator.timeout', tags={'llm': 'primary'})

                if attempt == self.retry_policy.max_attempts - 1:
                    # Final attempt - try fallback
                    break
                continue

            except Exception as e:
                self.handle_error('llm_generation', e)
                if attempt < self.retry_policy.max_attempts - 1:
                    time.sleep(self.retry_policy.get_delay(attempt))
                    continue
                break

        # Fallback to faster model
        self.logger.info("Falling back to secondary LLM")
        self.metrics.increment('response_generator.fallback')

        try:
            raw_response = self._call_llm_with_timeout(
                self.fallback_llm,
                prompt,
                context.synthesis_complexity
            )
            passed, quality_score = self.apply_quality_gates(raw_response, context)
            return self._build_response(raw_response, context, quality_score)

        except Exception as e:
            # Final fallback - template-based response
            self.handle_error('fallback_llm_generation', e)
            self.metrics.increment('response_generator.template_fallback')
            return self._template_response(context)

    def _call_llm_with_timeout(self, llm: LLMClient, prompt: str, complexity: str) -> str:
        """Call LLM with timeout protection"""
        timeout = self._get_timeout_for_complexity(complexity)

        with self.timeout_context(seconds=timeout):
            start_time = time.time()
            response = llm.generate(
                prompt,
                max_tokens=self._get_max_tokens(complexity),
                temperature=0.3
            )
            duration = time.time() - start_time

            self.metrics.histogram(
                'response_generator.llm_duration',
                duration,
                tags={'llm': llm.model, 'complexity': complexity}
            )

            return response

    def _template_response(self, context: SynthesizedContext) -> GeneratedResponse:
        """Emergency template-based response when all LLMs fail"""

        # Build basic response from context
        text = f"""Based on the available information:

{context.primary_context}

I apologize, but I'm experiencing technical difficulties with generating a detailed response. The information above represents the key facts I have available."""

        if context.confidence_notes:
            text += f"\n\nNote: {'; '.join(context.confidence_notes)}"

        return GeneratedResponse(
            text=text,
            confidence=0.6,  # Lower confidence for template response
            sources=["Database", "Memory"],
            suggestions=[],
            quality_score=0.6,
            passed_quality_gates=False
        )

    def _get_timeout_for_complexity(self, complexity: str) -> float:
        """Get timeout based on response complexity"""
        timeouts = {
            "simple": 10.0,
            "medium": 20.0,
            "complex": 30.0
        }
        return timeouts.get(complexity, 20.0)
```

---

## 2. Performance Optimization

### 2.1 Required Database Indexes

```sql
-- ============================================================================
-- PERFORMANCE-CRITICAL INDEXES
-- Create these before going to production
-- ============================================================================

-- Pattern Analysis Indexes
-- -------------------------
-- Rush order detection
CREATE INDEX CONCURRENTLY idx_sales_orders_customer_priority_created
    ON domain.sales_orders(customer_id, priority, created_at)
    WHERE priority = 'rush';  -- Partial index for better performance

-- Payment timing analysis
CREATE INDEX CONCURRENTLY idx_payments_customer_paid
    ON domain.payments(invoice_id, paid_at);

CREATE INDEX CONCURRENTLY idx_invoices_customer_due
    ON domain.invoices(customer_id, due_date, created_at);

-- Cross-entity comparisons
CREATE INDEX CONCURRENTLY idx_sales_orders_customer_created
    ON domain.sales_orders(customer_id, created_at DESC);

-- Entity Resolution Indexes
-- --------------------------
-- Fuzzy matching requires trigram index
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX CONCURRENTLY idx_customers_name_trgm
    ON domain.customers USING gin (name gin_trgm_ops);

-- Alias lookup
CREATE INDEX CONCURRENTLY idx_entity_aliases_alias
    ON app.entity_aliases(alias);

-- Memory Retrieval Indexes
-- -------------------------
-- Entity link lookups
CREATE INDEX CONCURRENTLY idx_memories_entity_links
    ON app.memories USING gin (entity_links);

-- Temporal queries
CREATE INDEX CONCURRENTLY idx_memories_user_created
    ON app.memories(user_id, created_at DESC);

-- Pattern Cache Indexes
-- ----------------------
CREATE INDEX CONCURRENTLY idx_customer_patterns_computed
    ON app.customer_patterns(customer_id, computed_at DESC);

CREATE INDEX CONCURRENTLY idx_customer_patterns_confidence
    ON app.customer_patterns(customer_id, confidence DESC)
    WHERE confidence > 0.6;  -- Only index significant patterns

-- ============================================================================
-- QUERY OPTIMIZATION EXAMPLES
-- ============================================================================

-- BEFORE optimization:
EXPLAIN ANALYZE
SELECT COUNT(*)
FROM domain.sales_orders
WHERE customer_id = 'customer-123'
AND priority = 'rush'
AND created_at > NOW() - INTERVAL '6 months';
-- Result: Seq Scan on sales_orders (cost=0.00..10000.00 rows=50 width=8)

-- AFTER optimization (with index):
-- Result: Index Scan using idx_sales_orders_customer_priority_created
--         (cost=0.42..8.44 rows=2 width=8)
```

### 2.2 Query Performance Budget

```python
# Performance targets for intelligence components
PERFORMANCE_TARGETS = {
    # Entity Resolution
    'entity_resolver.resolve': {
        'p50': 50,   # 50ms
        'p95': 150,  # 150ms
        'p99': 300   # 300ms
    },

    # Pattern Analysis (cache hit)
    'pattern_analyzer.get_cached_patterns': {
        'p50': 20,
        'p95': 100,
        'p99': 200
    },

    # Pattern Analysis (cache miss - real-time)
    'pattern_analyzer.analyze_entity': {
        'p50': 500,
        'p95': 2000,
        'p99': 5000  # Will timeout at 5s
    },

    # Context Synthesis
    'context_synthesizer.synthesize': {
        'p50': 100,
        'p95': 300,
        'p99': 500
    },

    # Decision Support
    'decision_support.analyze_decision': {
        'p50': 800,
        'p95': 2000,
        'p99': 4000
    },

    # Response Generation (LLM call)
    'response_generator.generate': {
        'p50': 2000,   # 2s
        'p95': 8000,   # 8s
        'p99': 15000   # 15s (will timeout at 30s)
    },

    # Total request (end-to-end)
    'request_handler.handle_request': {
        'p50': 3000,
        'p95': 10000,
        'p99': 20000
    }
}

class PerformanceMonitor:
    """Monitor and alert on performance violations"""

    def __init__(self):
        self.metrics = MetricsClient()
        self.alert_manager = AlertManager()

    @contextmanager
    def measure(self, operation: str):
        """Measure operation duration and alert on violations"""
        start = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start) * 1000

            # Record metric
            self.metrics.histogram(
                f'{operation}.duration',
                duration_ms
            )

            # Check against budget
            if operation in PERFORMANCE_TARGETS:
                target_p95 = PERFORMANCE_TARGETS[operation]['p95']

                if duration_ms > target_p95 * 2:  # 2x over budget
                    self.alert_manager.send_alert(
                        severity='warning',
                        message=f'{operation} took {duration_ms:.0f}ms (target p95: {target_p95}ms)',
                        tags={'operation': operation}
                    )

# Usage in components:
class EntityResolver(IntelligenceComponent):
    def __init__(self, config):
        super().__init__(config)
        self.perf_monitor = PerformanceMonitor()

    def resolve(self, text: str, context: ConversationContext) -> List[ResolvedEntity]:
        with self.perf_monitor.measure('entity_resolver.resolve'):
            # ... implementation ...
            pass
```

### 2.3 Caching Strategy

```python
class CacheManager:
    """Multi-tier caching for intelligence components"""

    def __init__(self, redis_client: RedisClient, config: CacheConfig):
        self.redis = redis_client
        self.config = config
        self.local_cache = {}  # L1: In-memory LRU cache
        self.local_cache_size = 1000

    def get_pattern_insights(self, entity_id: str) -> Optional[List[PatternInsight]]:
        """
        Get patterns with two-tier caching.

        L1 (in-memory): ~1ms
        L2 (Redis): ~5ms
        L3 (PostgreSQL): ~50ms
        """

        # L1: Check in-memory cache
        cache_key = f'patterns:{entity_id}'

        if cache_key in self.local_cache:
            self.metrics.increment('cache.hit', tags={'tier': 'L1'})
            return self.local_cache[cache_key]

        # L2: Check Redis
        try:
            cached = self.redis.get(cache_key)
            if cached:
                self.metrics.increment('cache.hit', tags={'tier': 'L2'})
                patterns = json.loads(cached)

                # Populate L1 cache
                self._set_local_cache(cache_key, patterns)

                return [PatternInsight(**p) for p in patterns]
        except Exception as e:
            self.logger.error(f"Redis cache error: {e}")
            # Continue to L3 on cache errors

        # L3: Query PostgreSQL (and populate caches)
        self.metrics.increment('cache.miss')
        return None

    def set_pattern_insights(self, entity_id: str, patterns: List[PatternInsight]):
        """Store in multi-tier cache"""
        cache_key = f'patterns:{entity_id}'
        serialized = [p.to_dict() for p in patterns]

        # L1: In-memory
        self._set_local_cache(cache_key, patterns)

        # L2: Redis with TTL
        try:
            self.redis.setex(
                cache_key,
                time=86400,  # 24 hour TTL
                value=json.dumps(serialized)
            )
        except Exception as e:
            self.logger.error(f"Redis cache write error: {e}")
            # Cache write failures shouldn't block request

    def _set_local_cache(self, key: str, value: Any):
        """LRU local cache"""
        if len(self.local_cache) >= self.local_cache_size:
            # Remove oldest item
            oldest_key = next(iter(self.local_cache))
            del self.local_cache[oldest_key]

        self.local_cache[key] = value

    def invalidate_pattern_cache(self, entity_id: str):
        """Invalidate cache when underlying data changes"""
        cache_key = f'patterns:{entity_id}'

        # Invalidate L1
        if cache_key in self.local_cache:
            del self.local_cache[cache_key]

        # Invalidate L2
        try:
            self.redis.delete(cache_key)
        except Exception as e:
            self.logger.error(f"Redis cache invalidation error: {e}")
```

---

## 3. Async Coordination Patterns

### 3.1 Complete Request Flow with Async

```python
async def handle_chat_request(
    user_query: str,
    session_id: str,
    user_id: str
) -> GeneratedResponse:
    """
    Complete request flow with proper async coordination.

    Performance optimization through parallelization:
    - Entity resolution: 150ms
    - Memory + Pattern + DB retrieval (parallel): max(50ms, 100ms, 30ms) = 100ms
    - Synthesis: 100ms
    - Response generation: 2000ms

    Total: ~2400ms (vs ~4280ms if sequential)
    """

    # Phase 1: Entity Resolution (sequential - needed for next steps)
    with perf_monitor.measure('entity_resolution'):
        entities = await entity_resolver.resolve_async(user_query, session_id)

    if any(e.disambiguation_needed for e in entities):
        return generate_disambiguation_response(entities)

    # Phase 2: Information Retrieval (parallel - independent operations)
    with perf_monitor.measure('information_retrieval'):
        memory_task = memory_retriever.retrieve_async(user_query, entities, user_id)
        pattern_task = pattern_analyzer.get_patterns_async(entities)
        db_facts_task = database.query_facts_async(entities)

        # Wait for all to complete (or timeout)
        try:
            memories, patterns, db_facts = await asyncio.gather(
                memory_task,
                pattern_task,
                db_facts_task,
                timeout=5.0  # 5 second total timeout for retrieval
            )
        except asyncio.TimeoutError:
            # Partial results acceptable - continue with what we have
            logger.warning(f"Retrieval timeout for query: {user_query[:50]}")

            # Get partial results
            memories = await memory_task if memory_task.done() else []
            patterns = await pattern_task if pattern_task.done() else []
            db_facts = await db_facts_task if db_facts_task.done() else {}

    # Phase 3: Context Synthesis (sequential - needs all retrieval results)
    with perf_monitor.measure('context_synthesis'):
        synthesized = context_synthesizer.synthesize(
            query=user_query,
            entities=entities,
            memories=memories,
            patterns=patterns,
            db_facts=db_facts
        )

    # Phase 4: Decision Support (if applicable)
    decision_analysis = None
    if synthesized.intent == "decision_support":
        with perf_monitor.measure('decision_support'):
            decision_analysis = await decision_support.analyze_decision_async(
                user_query,
                entities,
                synthesized
            )
            synthesized.decision_analysis = decision_analysis

    # Phase 5: Response Generation (may take time due to LLM)
    with perf_monitor.measure('response_generation'):
        response = await response_generator.generate_async(synthesized)

    # Phase 6: Background tasks (non-blocking)
    # Memory storage and context updates happen asynchronously
    asyncio.create_task(
        memory_store.store_interaction(
            user_query=user_query,
            response=response,
            entities=entities,
            session_id=session_id,
            user_id=user_id
        )
    )

    asyncio.create_task(
        conversation_mgr.update_context(
            session_id=session_id,
            entities=entities,
            topics=synthesized.topics if hasattr(synthesized, 'topics') else [],
            intent=synthesized.intent
        )
    )

    return response


# Async implementations of key components
class PatternAnalyzer:
    async def get_patterns_async(self, entities: List[ResolvedEntity]) -> List[PatternInsight]:
        """Async pattern retrieval with caching"""
        all_patterns = []

        # Retrieve patterns for all entities in parallel
        tasks = [
            self._get_entity_patterns_async(entity.entity_id)
            for entity in entities
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Pattern retrieval error: {result}")
                continue
            all_patterns.extend(result)

        return all_patterns

    async def _get_entity_patterns_async(self, entity_id: str) -> List[PatternInsight]:
        """Get patterns for single entity"""
        # Check cache first
        cached = await self.cache_manager.get_patterns_async(entity_id)
        if cached:
            return cached

        # Compute if not cached (run in thread pool to avoid blocking)
        loop = asyncio.get_event_loop()
        patterns = await loop.run_in_executor(
            self.thread_pool,
            self.analyze_entity,
            entity_id
        )

        # Store in cache
        await self.cache_manager.set_patterns_async(entity_id, patterns)

        return patterns
```

### 3.2 Rate Limiting & Circuit Breakers

```python
class RateLimiter:
    """Token bucket rate limiter for LLM calls"""

    def __init__(self, requests_per_minute: int = 60):
        self.capacity = requests_per_minute
        self.tokens = requests_per_minute
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire token or wait"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on elapsed time
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.capacity / 60.0)
            )
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            # Need to wait
            wait_time = (1.0 - self.tokens) * 60.0 / self.capacity
            logger.info(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

            self.tokens = 0
            self.last_update = time.time()


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
        self.lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        async with self.lock:
            # Check circuit state
            if self.state == 'open':
                # Check if timeout expired
                if time.time() - self.last_failure_time > self.timeout:
                    self.state = 'half-open'
                    logger.info("Circuit breaker entering half-open state")
                else:
                    raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)

            # Success - reset circuit
            async with self.lock:
                if self.state == 'half-open':
                    self.state = 'closed'
                    self.failures = 0
                    logger.info("Circuit breaker closed after successful call")

            return result

        except Exception as e:
            # Failure - increment counter
            async with self.lock:
                self.failures += 1
                self.last_failure_time = time.time()

                if self.failures >= self.failure_threshold:
                    self.state = 'open'
                    logger.error(f"Circuit breaker opened after {self.failures} failures")
                    metrics.increment('circuit_breaker.opened', tags={
                        'service': func.__name__
                    })

            raise


# Usage in ResponseGenerator
class ResponseGenerator(IntelligenceComponent):
    def __init__(self, config):
        super().__init__(config)
        self.rate_limiter = RateLimiter(requests_per_minute=60)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

    async def generate_async(self, context: SynthesizedContext) -> GeneratedResponse:
        """Generate with rate limiting and circuit breaker"""

        # Wait for rate limit token
        await self.rate_limiter.acquire()

        # Call LLM with circuit breaker protection
        try:
            response = await self.circuit_breaker.call(
                self._call_llm_async,
                context
            )
            return response

        except CircuitBreakerOpen:
            logger.warning("LLM circuit breaker open, using template response")
            metrics.increment('response_generator.circuit_breaker_fallback')
            return self._template_response(context)
```

---

## 4. Monitoring & Observability

### 4.1 Key Metrics to Track

```python
# Comprehensive metrics specification
METRICS_SPEC = {
    # Throughput metrics
    'request_handler.requests': {
        'type': 'counter',
        'tags': ['endpoint', 'status'],
        'description': 'Total requests processed'
    },

    # Latency metrics
    'entity_resolver.duration': {
        'type': 'histogram',
        'unit': 'milliseconds',
        'tags': ['match_type'],
        'description': 'Entity resolution latency'
    },

    'pattern_analyzer.duration': {
        'type': 'histogram',
        'unit': 'milliseconds',
        'tags': ['pattern_type', 'cache_hit'],
        'description': 'Pattern analysis latency'
    },

    'response_generator.llm_duration': {
        'type': 'histogram',
        'unit': 'milliseconds',
        'tags': ['llm_model', 'complexity'],
        'description': 'LLM API call duration'
    },

    # Quality metrics
    'response_generator.quality_score': {
        'type': 'histogram',
        'tags': ['complexity'],
        'description': 'Response quality scores'
    },

    'pattern_analyzer.patterns_found': {
        'type': 'histogram',
        'tags': ['entity_type'],
        'description': 'Number of patterns detected per entity'
    },

    # Error metrics
    'pattern_analyzer.timeout': {
        'type': 'counter',
        'tags': ['pattern_type'],
        'description': 'Pattern analysis timeouts'
    },

    'response_generator.llm_error': {
        'type': 'counter',
        'tags': ['error_type', 'llm_model'],
        'description': 'LLM API errors'
    },

    # Resource metrics
    'cache.hit_rate': {
        'type': 'gauge',
        'tags': ['cache_type', 'tier'],
        'description': 'Cache hit rate percentage'
    },

    'circuit_breaker.state': {
        'type': 'gauge',
        'tags': ['service'],
        'description': 'Circuit breaker state (0=closed, 1=open, 0.5=half-open)'
    }
}
```

### 4.2 Structured Logging

```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Usage in components
class PatternAnalyzer:
    def detect_rush_order_pattern(self, customer_id: str) -> Optional[PatternInsight]:
        logger.info(
            "pattern_analysis_started",
            pattern_type="rush_order_frequency",
            customer_id=customer_id
        )

        try:
            # ... analysis logic ...

            logger.info(
                "pattern_detected",
                pattern_type="rush_order_frequency",
                customer_id=customer_id,
                confidence=result.confidence,
                significance=result.significance,
                rush_order_count=len(rush_orders)
            )

            return result

        except Exception as e:
            logger.error(
                "pattern_analysis_failed",
                pattern_type="rush_order_frequency",
                customer_id=customer_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise
```

### 4.3 Alert Configuration

```yaml
# alerts.yml - Example alert configuration
alerts:
  # High error rate
  - name: high_pattern_analysis_error_rate
    metric: pattern_analyzer.error
    condition: rate > 0.1  # More than 10% errors
    window: 5m
    severity: warning
    message: "Pattern analysis error rate is {{value}}%"

  # High latency
  - name: slow_response_generation
    metric: response_generator.duration
    condition: p95 > 10000  # p95 > 10s
    window: 5m
    severity: warning
    message: "Response generation p95 latency is {{value}}ms"

  # Circuit breaker opened
  - name: llm_circuit_breaker_open
    metric: circuit_breaker.state
    condition: value == 1
    severity: critical
    message: "LLM circuit breaker is open - {{service}}"

  # Low cache hit rate
  - name: low_pattern_cache_hit_rate
    metric: cache.hit_rate
    condition: value < 0.7  # Less than 70%
    window: 15m
    severity: info
    message: "Pattern cache hit rate is {{value}}%"
```

---

## 5. Testing Strategy for Production Readiness

### 5.1 Load Testing

```python
import locust
from locust import HttpUser, task, between

class IntelligentMemoryUser(HttpUser):
    """Load test scenario"""
    wait_time = between(1, 3)  # 1-3 seconds between requests

    @task(3)  # 60% of traffic
    def simple_query(self):
        """Simple fact lookup query"""
        self.client.post("/api/chat", json={
            "query": "What is the status of Delta Industries?",
            "session_id": f"session-{self.user_id}"
        })

    @task(1)  # 20% of traffic
    def decision_support_query(self):
        """Complex decision support query"""
        self.client.post("/api/chat", json={
            "query": "Should we extend payment terms to Delta Industries?",
            "session_id": f"session-{self.user_id}"
        })

    @task(1)  # 20% of traffic
    def pattern_query(self):
        """Query that triggers pattern analysis"""
        self.client.post("/api/chat", json={
            "query": "What patterns do you see with Delta Industries?",
            "session_id": f"session-{self.user_id}"
        })

    def on_start(self):
        """Setup user session"""
        self.user_id = f"user-{id(self)}"


# Load test targets:
# - 100 concurrent users (p95 < 5s)
# - 500 concurrent users (p95 < 10s)
# - Sustained load for 1 hour
# - No errors > 1%
```

### 5.2 Chaos Testing

```python
# chaos_tests.py - Test resilience under failure conditions

import pytest
import asyncio

@pytest.mark.chaos
class TestResilience:
    """Test system behavior under various failure conditions"""

    async def test_database_timeout(self, app):
        """System should degrade gracefully when DB times out"""
        # Inject database latency
        with inject_latency('postgresql', delay_ms=10000):
            response = await app.chat("What is Delta's status?")

            # Should return partial response (from cache) rather than error
            assert response.status_code == 200
            assert "cache" in response.sources

    async def test_llm_failure(self, app):
        """System should fallback to template when LLM fails"""
        with inject_failure('openai', error_rate=1.0):
            response = await app.chat("Should we extend terms?")

            # Should use template response
            assert response.status_code == 200
            assert response.quality_score < 0.7  # Lower quality

    async def test_partial_retrieval_failure(self, app):
        """System should continue with partial data"""
        # Make pattern analysis timeout
        with inject_timeout('pattern_analyzer', timeout_ms=1):
            response = await app.chat("What's going on with Delta?")

            # Should still respond using memory + DB
            assert response.status_code == 200
            # But patterns not included
            assert "Pattern Analysis" not in response.text
```

---

## Summary

This production operations guide provides:

✅ **Error Handling**
- Graceful degradation patterns
- Timeout handling
- Retry logic with exponential backoff
- Circuit breakers for external services

✅ **Performance**
- Required database indexes
- Multi-tier caching strategy
- Performance budgets and monitoring
- Query optimization guidelines

✅ **Async Coordination**
- Proper parallel execution patterns
- Timeout management
- Background task handling

✅ **Monitoring**
- Comprehensive metrics specification
- Structured logging
- Alert configuration
- Dashboard requirements

✅ **Testing**
- Load testing scenarios
- Chaos engineering tests
- Performance benchmarks

**Implementation checklist:**
- [ ] Create all database indexes before production
- [ ] Set up monitoring dashboards
- [ ] Configure alerts
- [ ] Run load tests to validate performance targets
- [ ] Test failure scenarios (chaos tests)
- [ ] Configure rate limiters for LLM calls
- [ ] Set up circuit breakers
- [ ] Implement multi-tier caching
- [ ] Add structured logging to all components
- [ ] Create runbook for common operational issues
