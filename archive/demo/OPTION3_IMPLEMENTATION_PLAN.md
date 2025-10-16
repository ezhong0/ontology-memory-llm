# Option 3: Full Vision Implementation Plan

**Date**: October 15, 2025
**Estimated Duration**: 8-9 days
**Philosophy**: Quality over speed, comprehensive solutions, vision-driven

---

## 🎯 Implementation Philosophy (from CLAUDE.md)

### Core Principles

1. **Understand Before Executing** - Deep architectural thinking first
2. **Quality Over Speed** - Comprehensive solutions, not quick fixes
3. **Vision First** - Every feature serves explicit vision principles
4. **Architecture is Sacred** - Pure hexagonal architecture (ports & adapters)
5. **Incremental Perfection** - Complete each piece fully before moving on

### Anti-Patterns to Avoid

❌ Rough-in multiple features then polish later
❌ Skip edge cases and error handling
❌ Violate hexagonal architecture for convenience
❌ Add features without vision justification
❌ Batch testing at the end

### Success Pattern

✅ One feature at a time, production-ready before moving on
✅ Test edge cases as you build
✅ Maintain architecture purity
✅ Document decisions and rationale
✅ Think deeply about whole-system impact

---

## 📐 Architectural Analysis

### Current State

```
Frontend (index.html - vanilla JS)
    ↓ Fetch API
Demo API Routes (/api/v1/demo/*)
    ↓ FastAPI Dependencies
Demo Services (scenario_loader, etc.)
    ↓ Repository Pattern
Domain Services (entity_resolver, semantic_extraction, etc.)
    ↓ Repository Ports (ABC interfaces)
Infrastructure Repositories (PostgreSQL)
    ↓ SQLAlchemy async
Database (PostgreSQL with pgvector)
```

**Key Architectural Constraints**:
- Demo layer MUST NOT pollute domain layer
- Domain services are pure Python (no FastAPI, no infrastructure imports)
- All external dependencies injected via ports
- Debug instrumentation must be non-invasive

---

## 🏗️ Implementation Order (Thoughtfully Chosen)

### Phase 1: LLM Integration (Day 1) - Foundation
**Why First**: Unblocks real chat functionality, enables testing full pipeline

### Phase 2: Debug Instrumentation (Days 2-3) - Core Value
**Why Second**: Requires understanding of services, must instrument carefully

### Phase 3: Debug Panel UI (Days 4-5) - Visualization
**Why Third**: Needs backend traces to be working first

### Phase 4: Additional Scenarios (Days 6-7) - Coverage
**Why Fourth**: Easy data definition, tests debug panel with variety

### Phase 5: UX Polish (Days 8-9) - Refinement
**Why Last**: Cosmetic improvements, can be done incrementally

---

## 🔧 Phase 1: LLM Integration (Day 1)

### Vision Principle Served
**"Deep Business Understanding"** - LLM synthesizes context into natural language

### Architectural Decisions

**Decision 1: Where does LLM service live?**
- ❌ Not in infrastructure (OpenAI is implementation detail)
- ✅ **In domain layer** as `LLMReplyGeneratorService`
- Port: `LLMProviderPort` (ABC interface)
- Adapter: `OpenAIProvider` in infrastructure

**Decision 2: How to inject OpenAI dependency?**
```python
# Domain layer (pure Python)
from abc import ABC, abstractmethod

class LLMProviderPort(ABC):
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: str,
        temperature: float
    ) -> str:
        pass

# Domain service
class LLMReplyGeneratorService:
    def __init__(self, llm_provider: LLMProviderPort):
        self._llm = llm_provider

    async def generate_reply(
        self,
        context: ConversationContextReply
    ) -> str:
        prompt = self._format_context(context)
        return await self._llm.generate_completion(prompt, "gpt-4o", 0.7)

# Infrastructure layer
class OpenAIProvider(LLMProviderPort):
    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_completion(...) -> str:
        # Actual OpenAI API call
```

**Decision 3: Error Handling Strategy**
- OpenAI failures → return fallback response with explanation
- Rate limits → return friendly message
- Invalid API key → show configuration error
- Timeout → return partial response or fallback

**Decision 4: Cost Tracking**
- Track tokens in/out per request
- Calculate cost (input: $0.0025/1K, output: $0.01/1K for gpt-4o)
- Store in metadata, return in debug info
- Add to analytics dashboard (total cost today, this week, etc.)

### Implementation Tasks

**Task 1.1: Create LLM Port (30 min)**
```python
# src/domain/ports/llm_provider_port.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class LLMResponse:
    content: str
    tokens_used: int
    model: str
    cost_usd: float

class LLMProviderPort(ABC):
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        """Generate completion from LLM."""
        pass
```

**Task 1.2: Implement OpenAI Adapter (1 hour)**
```python
# src/infrastructure/llm/openai_provider.py
from openai import AsyncOpenAI
from src.domain.ports.llm_provider_port import LLMProviderPort, LLMResponse

class OpenAIProvider(LLMProviderPort):
    # Pricing per 1K tokens (gpt-4o)
    PRICING = {
        "gpt-4o": {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006}
    }

    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_completion(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> LLMResponse:
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )

            usage = response.usage
            cost = (
                (usage.prompt_tokens / 1000) * self.PRICING[model]["input"] +
                (usage.completion_tokens / 1000) * self.PRICING[model]["output"]
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                tokens_used=usage.total_tokens,
                model=model,
                cost_usd=cost
            )

        except Exception as e:
            # Log error, return fallback
            logger.error("LLM generation failed", error=str(e))
            return LLMResponse(
                content=f"[Error: {str(e)}. Using fallback mode.]",
                tokens_used=0,
                model=model,
                cost_usd=0.0
            )
```

**Task 1.3: Enhance LLMReplyGenerator (2 hours)**
```python
# src/domain/services/llm_reply_generator.py
from src.domain.ports.llm_provider_port import LLMProviderPort
from src.domain.value_objects.conversation_context_reply import ConversationContextReply

class LLMReplyGeneratorService:
    def __init__(self, llm_provider: LLMProviderPort):
        self._llm = llm_provider

    async def generate_reply(
        self,
        context: ConversationContextReply,
        fallback_mode: bool = False
    ) -> tuple[str, dict]:
        """
        Generate natural language reply from context.

        Returns: (reply_text, metadata)
        metadata includes: tokens_used, cost_usd, model, etc.
        """

        if fallback_mode or not self._llm:
            return self._generate_fallback(context), {}

        prompt = self._format_context_for_llm(context)

        llm_response = await self._llm.generate_completion(
            prompt=prompt,
            model="gpt-4o-mini",  # Cost-effective for demo
            temperature=0.7,
            max_tokens=500
        )

        metadata = {
            "tokens_used": llm_response.tokens_used,
            "cost_usd": llm_response.cost_usd,
            "model": llm_response.model,
            "mode": "llm"
        }

        return llm_response.content, metadata

    def _format_context_for_llm(self, context: ConversationContextReply) -> str:
        """Format context into LLM prompt."""
        prompt = f"""You are a helpful business assistant with access to a memory system.

**User Query**: {context.query}

**Relevant Domain Facts**:
{self._format_domain_facts(context.domain_facts)}

**Relevant Memories**:
{self._format_memories(context.retrieved_memories)}

**Instructions**:
- Answer the query using the provided facts and memories
- Be concise and helpful
- If data conflicts, mention it
- If uncertain, say so

**Response**:"""
        return prompt

    def _format_domain_facts(self, facts: list) -> str:
        if not facts:
            return "(No domain facts available)"

        lines = []
        for fact in facts:
            lines.append(f"- {fact.content} (source: {fact.source})")
        return "\n".join(lines)

    def _format_memories(self, memories: list) -> str:
        if not memories:
            return "(No memories available)"

        lines = []
        for mem in memories:
            lines.append(
                f"- {mem.content} "
                f"(confidence: {int(mem.confidence * 100)}%, "
                f"relevance: {mem.relevance:.2f})"
            )
        return "\n".join(lines)

    def _generate_fallback(self, context: ConversationContextReply) -> str:
        """Fallback mode when LLM unavailable."""
        return f"""**[Demo Mode - No LLM]**

I would have used the following context to generate a reply:

**Domain Facts ({len(context.domain_facts)}):**
{self._format_domain_facts(context.domain_facts)}

**Memories ({len(context.retrieved_memories)}):**
{self._format_memories(context.retrieved_memories)}

**To enable full LLM replies**, set OPENAI_API_KEY environment variable."""
```

**Task 1.4: Wire to DI Container (30 min)**
```python
# src/api/dependencies.py
from src.domain.services.llm_reply_generator import LLMReplyGeneratorService
from src.infrastructure.llm.openai_provider import OpenAIProvider
import os

def get_llm_reply_generator() -> LLMReplyGeneratorService:
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        provider = OpenAIProvider(api_key=api_key)
        return LLMReplyGeneratorService(llm_provider=provider)
    else:
        # No API key = fallback mode
        return LLMReplyGeneratorService(llm_provider=None)
```

**Task 1.5: Update Chat Endpoint (30 min)**
```python
# src/demo/api/router.py (chat endpoint)
@router.post("/chat/message")
async def send_chat_message(
    request: ChatMessageRequest,
    llm_generator: LLMReplyGeneratorService = Depends(get_llm_reply_generator)
):
    # ... existing context building ...

    # Generate reply using LLM
    fallback_mode = (os.getenv("OPENAI_API_KEY") is None)
    reply, metadata = await llm_generator.generate_reply(
        context=context,
        fallback_mode=fallback_mode
    )

    return ChatMessageResponse(
        reply=reply,
        debug={
            "domain_facts_used": domain_facts,
            "memories_used": memories,
            "context_summary": summary,
            "llm_metadata": metadata  # NEW: tokens, cost, model
        }
    )
```

**Task 1.6: Testing (1 hour)**
- [ ] Unit test: LLMReplyGenerator with mock provider
- [ ] Unit test: OpenAIProvider with mock OpenAI client
- [ ] Integration test: Full chat with LLM
- [ ] Integration test: Fallback mode when no API key
- [ ] Edge case: OpenAI rate limit
- [ ] Edge case: Invalid API key

**Acceptance Criteria**:
- ✅ Chat works with and without OPENAI_API_KEY
- ✅ Natural language replies when API key present
- ✅ Fallback mode when no API key
- ✅ Errors handled gracefully
- ✅ Cost tracked and returned
- ✅ Tests passing

**Time**: 6 hours (Day 1)

---

## 🔍 Phase 2: Debug Instrumentation (Days 2-3)

### Vision Principle Served
**"Explainable Reasoning"** - System explains its thinking, traces provenance

### Architectural Challenge

**Problem**: How to collect debug traces without polluting domain layer?

**Bad Solution** ❌:
```python
# Domain service knows about demo
from src.demo.services.debug_trace import DebugTraceService

class EntityResolver:
    def resolve(self, ...):
        DebugTraceService.trace(...)  # ❌ Domain depends on demo!
```

**Good Solution** ✅:
```python
# Use contextvars + optional callback pattern
from typing import Callable, Optional
from contextvars import ContextVar

# Domain layer
debug_callback: ContextVar[Optional[Callable]] = ContextVar('debug_callback', default=None)

class EntityResolver:
    def resolve(self, ...):
        result = ...  # core logic

        # Optional instrumentation (non-invasive)
        callback = debug_callback.get()
        if callback:
            callback('entity_resolution', {
                'mention': mention,
                'result': result.dict(),
                'method': result.method
            })

        return result
```

**Why This Works**:
- Domain layer stays pure (no demo imports)
- Instrumentation is optional (callback can be None)
- Demo layer controls what gets traced
- Zero performance impact when callback is None

### Implementation Tasks

**Task 2.1: Define Trace Data Structures (1 hour)**
```python
# src/demo/models/debug_trace.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime

@dataclass
class EntityResolutionTrace:
    mention: str
    stage: str  # 'exact', 'alias', 'fuzzy', 'llm', 'domain_db'
    result: str | None
    confidence: float
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryRetrievalTrace:
    memory_id: int
    memory_type: str
    content: str
    scores: Dict[str, float]  # semantic, entity, recency, etc.
    final_relevance: float
    selected: bool

@dataclass
class DatabaseQueryTrace:
    table: str
    query_type: str  # 'select', 'insert', 'update'
    duration_ms: float
    rows_returned: int
    sql_summary: str  # Sanitized SQL

@dataclass
class ReasoningStepTrace:
    step_number: int
    description: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    duration_ms: float

@dataclass
class DebugTrace:
    """Complete debug trace for one request."""
    trace_id: str
    started_at: datetime
    completed_at: datetime | None

    entity_resolutions: List[EntityResolutionTrace] = field(default_factory=list)
    memory_retrievals: List[MemoryRetrievalTrace] = field(default_factory=list)
    database_queries: List[DatabaseQueryTrace] = field(default_factory=list)
    reasoning_steps: List[ReasoningStepTrace] = field(default_factory=list)

    @property
    def total_duration_ms(self) -> float:
        if not self.completed_at:
            return 0.0
        delta = self.completed_at - self.started_at
        return delta.total_seconds() * 1000
```

**Task 2.2: Create DebugTraceService (1 hour)**
```python
# src/demo/services/debug_trace_service.py
from contextvars import ContextVar
from src.demo.models.debug_trace import DebugTrace, EntityResolutionTrace
from datetime import datetime
import uuid

# Context var to store current trace
current_trace: ContextVar[DebugTrace | None] = ContextVar('current_trace', default=None)

class DebugTraceService:
    """Collects debug traces using context vars."""

    @staticmethod
    def start_trace() -> str:
        """Start a new trace."""
        trace_id = str(uuid.uuid4())
        trace = DebugTrace(
            trace_id=trace_id,
            started_at=datetime.now(),
            completed_at=None
        )
        current_trace.set(trace)
        return trace_id

    @staticmethod
    def complete_trace() -> DebugTrace:
        """Complete and return current trace."""
        trace = current_trace.get()
        if trace:
            trace.completed_at = datetime.now()
        return trace

    @staticmethod
    def trace_entity_resolution(data: Dict[str, Any]):
        """Record entity resolution trace."""
        trace = current_trace.get()
        if trace:
            trace.entity_resolutions.append(EntityResolutionTrace(**data))

    @staticmethod
    def trace_memory_retrieval(data: Dict[str, Any]):
        """Record memory retrieval trace."""
        trace = current_trace.get()
        if trace:
            trace.memory_retrievals.append(MemoryRetrievalTrace(**data))

    # Similar methods for database_query, reasoning_step...
```

**Task 2.3: Add Callback Registration (30 min)**
```python
# src/domain/services/entity_resolution_service.py
from typing import Callable, Optional
from contextvars import ContextVar

# Module-level context var
_trace_callback: ContextVar[Optional[Callable]] = ContextVar('trace_callback', default=None)

def set_trace_callback(callback: Callable | None):
    """Set callback for tracing (called by demo layer)."""
    _trace_callback.set(callback)

class EntityResolutionService:
    async def resolve(...) -> ResolutionResult:
        start_time = time.time()

        # Stage 1: Exact match
        exact = await self._try_exact_match(mention)
        if exact:
            duration_ms = (time.time() - start_time) * 1000

            # Optional tracing
            callback = _trace_callback.get()
            if callback:
                callback({
                    'mention': mention,
                    'stage': 'exact',
                    'result': exact.entity_id,
                    'confidence': 1.0,
                    'duration_ms': duration_ms
                })

            return exact

        # Stage 2, 3, 4, 5... (same pattern)
```

**Task 2.4: Instrument All Services (4 hours)**
- [ ] EntityResolutionService (5 stages)
- [ ] SemanticMemoryRepository (retrieval scoring)
- [ ] Database repositories (query logging)
- [ ] LLMReplyGenerator (reasoning steps)

**Task 2.5: Wire to Chat Endpoint (1 hour)**
```python
# src/demo/api/router.py
from src.demo.services.debug_trace_service import DebugTraceService
from src.domain.services.entity_resolution_service import set_trace_callback

@router.post("/chat/message")
async def send_chat_message(request: ChatMessageRequest):
    # Start trace
    trace_id = DebugTraceService.start_trace()

    # Register callbacks
    set_trace_callback(DebugTraceService.trace_entity_resolution)
    # ... other callbacks ...

    try:
        # ... existing chat logic ...

        # Complete trace
        trace = DebugTraceService.complete_trace()

        return ChatMessageResponse(
            reply=reply,
            debug={
                "trace_id": trace_id,
                "entity_resolutions": [t.dict() for t in trace.entity_resolutions],
                "memory_retrievals": [t.dict() for t in trace.memory_retrievals],
                "database_queries": [t.dict() for t in trace.database_queries],
                "reasoning_steps": [t.dict() for t in trace.reasoning_steps],
                "performance": {
                    "total_ms": trace.total_duration_ms,
                    "entity_resolution_ms": sum(t.duration_ms for t in trace.entity_resolutions),
                    # ... other breakdowns ...
                }
            }
        )
    finally:
        # Clean up callbacks
        set_trace_callback(None)
```

**Task 2.6: Testing (2 hours)**
- [ ] Test trace collection works
- [ ] Test trace is None when callback not set
- [ ] Test multiple concurrent requests don't mix traces
- [ ] Test performance impact (should be <5ms overhead)

**Acceptance Criteria**:
- ✅ Traces collected for all operations
- ✅ Domain layer stays pure (no demo imports)
- ✅ Zero performance impact when tracing disabled
- ✅ Concurrent requests don't mix traces
- ✅ All trace types working

**Time**: 12 hours (Days 2-3)

---

## 🎨 Phase 3: Debug Panel UI (Days 4-5)

### Design Decisions

**Decision 1: Layout**
- Right-side collapsible panel (400px wide)
- Tabs for different trace types
- Auto-expands when debug data available
- Collapse button (<<)

**Decision 2: Visual Style**
- Match existing purple gradient theme
- Use monospace font for technical data
- Color-coded confidence/scores (green=high, red=low)
- Animated expand/collapse

**Decision 3: Content Organization**
```
Debug Panel (right side)
├── Entity Resolution Tab
│   ├── Timeline view (5 stages)
│   ├── Stage cards with duration
│   └── Confidence visualization
├── Memory Retrieval Tab
│   ├── Score breakdown table
│   ├── Signal contribution chart
│   └── Top candidates list
├── Database Queries Tab
│   ├── Query log
│   ├── Performance metrics
│   └── Results count
├── LLM Context Tab
│   ├── Full prompt (expandable)
│   ├── Token count
│   └── Cost
└── Performance Tab
    ├── Timing breakdown chart
    ├── Bottleneck identification
    └── Cost summary
```

### Implementation Tasks

**Task 3.1: CSS for Debug Panel (1 hour)**
```css
/* Add to existing <style> in index.html */

.debug-panel {
    position: fixed;
    right: 0;
    top: 0;
    width: 400px;
    height: 100vh;
    background: white;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
    transform: translateX(400px);
    transition: transform 0.3s ease;
    z-index: 1000;
    overflow-y: auto;
}

.debug-panel.open {
    transform: translateX(0);
}

.debug-toggle-btn {
    position: absolute;
    left: -40px;
    top: 50%;
    transform: translateY(-50%);
    background: #667eea;
    color: white;
    border: none;
    padding: 12px 8px;
    border-radius: 8px 0 0 8px;
    cursor: pointer;
    font-size: 18px;
}

.debug-tabs {
    display: flex;
    border-bottom: 2px solid #e2e8f0;
    padding: 10px;
    gap: 5px;
}

.debug-tab {
    padding: 8px 12px;
    background: none;
    border: none;
    font-size: 12px;
    font-weight: 600;
    color: #718096;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
}

.debug-tab.active {
    color: #667eea;
    border-bottom-color: #667eea;
}

.debug-tab-content {
    padding: 15px;
    display: none;
}

.debug-tab-content.active {
    display: block;
}

.stage-timeline {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.stage-card {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px;
    background: #f7fafc;
}

.stage-card.success {
    border-left: 4px solid #48bb78;
}

.stage-card.failed {
    border-left: 4px solid #fc8181;
}

.confidence-bar {
    height: 8px;
    background: #e2e8f0;
    border-radius: 4px;
    overflow: hidden;
    margin-top: 5px;
}

.confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, #48bb78, #667eea);
    transition: width 0.3s;
}

.score-breakdown {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.score-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.score-label {
    font-size: 12px;
    color: #4a5568;
    font-weight: 500;
}

.score-value {
    font-size: 13px;
    font-weight: 600;
    color: #667eea;
}
```

**Task 3.2: Debug Panel HTML Structure (1 hour)**
```html
<!-- Add to index.html after chat-tab -->

<div class="debug-panel" id="debugPanel">
    <button class="debug-toggle-btn" onclick="toggleDebugPanel()">
        <span id="debugToggleIcon">🔍</span>
    </button>

    <div class="debug-tabs">
        <button class="debug-tab active" onclick="switchDebugTab('entity')">
            Entity Resolution
        </button>
        <button class="debug-tab" onclick="switchDebugTab('memory')">
            Memory Retrieval
        </button>
        <button class="debug-tab" onclick="switchDebugTab('database')">
            Database
        </button>
        <button class="debug-tab" onclick="switchDebugTab('llm')">
            LLM Context
        </button>
        <button class="debug-tab" onclick="switchDebugTab('performance')">
            Performance
        </button>
    </div>

    <div id="debug-entity-tab" class="debug-tab-content active"></div>
    <div id="debug-memory-tab" class="debug-tab-content"></div>
    <div id="debug-database-tab" class="debug-tab-content"></div>
    <div id="debug-llm-tab" class="debug-tab-content"></div>
    <div id="debug-performance-tab" class="debug-tab-content"></div>
</div>
```

**Task 3.3: JavaScript Functions (3 hours)**
```javascript
// Debug panel management
let debugPanelOpen = false;
let latestDebugData = null;

function toggleDebugPanel() {
    const panel = document.getElementById('debugPanel');
    const icon = document.getElementById('debugToggleIcon');

    debugPanelOpen = !debugPanelOpen;
    panel.classList.toggle('open', debugPanelOpen);
    icon.textContent = debugPanelOpen ? '✕' : '🔍';
}

function switchDebugTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.debug-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.debug-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`debug-${tabName}-tab`).classList.add('active');
}

function renderDebugPanel(debugData) {
    latestDebugData = debugData;

    // Render each tab
    renderEntityResolutionTab(debugData.entity_resolutions || []);
    renderMemoryRetrievalTab(debugData.memory_retrievals || []);
    renderDatabaseQueriesTab(debugData.database_queries || []);
    renderLLMContextTab(debugData.llm_metadata || {});
    renderPerformanceTab(debugData.performance || {});

    // Auto-open panel if closed
    if (!debugPanelOpen && debugData) {
        toggleDebugPanel();
    }
}

function renderEntityResolutionTab(resolutions) {
    const tab = document.getElementById('debug-entity-tab');

    if (resolutions.length === 0) {
        tab.innerHTML = '<div class="empty-state">No entity resolutions</div>';
        return;
    }

    tab.innerHTML = `
        <div class="stage-timeline">
            ${resolutions.map((res, idx) => `
                <div class="stage-card ${res.result ? 'success' : 'failed'}">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="font-size: 13px;">Stage ${idx + 1}: ${res.stage}</strong>
                        <span style="font-size: 11px; color: #718096;">${res.duration_ms.toFixed(1)}ms</span>
                    </div>
                    <div style="font-size: 12px; color: #4a5568; margin-bottom: 5px;">
                        Mention: <code>${res.mention}</code>
                    </div>
                    ${res.result ? `
                        <div style="font-size: 12px; color: #2d5f3d;">
                            ✓ Result: <code>${res.result}</code>
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${res.confidence * 100}%;"></div>
                        </div>
                        <div style="font-size: 11px; color: #718096; margin-top: 3px;">
                            Confidence: ${(res.confidence * 100).toFixed(0)}%
                        </div>
                    ` : `
                        <div style="font-size: 12px; color: #742a2a;">
                            ✗ No match at this stage
                        </div>
                    `}
                </div>
            `).join('')}
        </div>
    `;
}

function renderMemoryRetrievalTab(retrievals) {
    const tab = document.getElementById('debug-memory-tab');

    if (retrievals.length === 0) {
        tab.innerHTML = '<div class="empty-state">No memories retrieved</div>';
        return;
    }

    // Sort by final relevance (descending)
    const sorted = [...retrievals].sort((a, b) => b.final_relevance - a.final_relevance);

    tab.innerHTML = `
        <div style="margin-bottom: 15px; padding: 10px; background: #f7fafc; border-radius: 6px;">
            <strong style="font-size: 13px;">Retrieved ${retrievals.length} candidates</strong>
            <div style="font-size: 12px; color: #718096; margin-top: 3px;">
                Top ${sorted.filter(r => r.selected).length} selected for context
            </div>
        </div>

        <div class="score-breakdown">
            ${sorted.map(ret => `
                <div class="stage-card ${ret.selected ? 'success' : ''}">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                        <strong style="font-size: 12px;">${ret.memory_type}</strong>
                        <span style="font-size: 13px; font-weight: 700; color: ${ret.selected ? '#2d5f3d' : '#718096'};">
                            ${ret.final_relevance.toFixed(3)}
                        </span>
                    </div>
                    <div style="font-size: 11px; color: #4a5568; margin-bottom: 8px;">
                        ${ret.content.substring(0, 100)}${ret.content.length > 100 ? '...' : ''}
                    </div>
                    <div class="score-breakdown" style="font-size: 10px;">
                        ${Object.entries(ret.scores).map(([signal, score]) => `
                            <div class="score-item">
                                <span class="score-label">${signal}:</span>
                                <span class="score-value">${score.toFixed(3)}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderDatabaseQueriesTab(queries) {
    const tab = document.getElementById('debug-database-tab');

    if (queries.length === 0) {
        tab.innerHTML = '<div class="empty-state">No database queries</div>';
        return;
    }

    tab.innerHTML = `
        <div style="margin-bottom: 15px; padding: 10px; background: #f7fafc; border-radius: 6px;">
            <strong style="font-size: 13px;">${queries.length} queries executed</strong>
            <div style="font-size: 12px; color: #718096; margin-top: 3px;">
                Total: ${queries.reduce((sum, q) => sum + q.duration_ms, 0).toFixed(1)}ms
            </div>
        </div>

        ${queries.map((query, idx) => `
            <div class="stage-card" style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <strong style="font-size: 12px;">${query.table} (${query.query_type})</strong>
                    <span style="font-size: 11px; color: #718096;">${query.duration_ms.toFixed(1)}ms</span>
                </div>
                <div style="font-size: 11px; color: #4a5568; margin-bottom: 5px;">
                    ${query.rows_returned} rows returned
                </div>
                <code style="font-size: 10px; color: #718096; display: block; background: white; padding: 5px; border-radius: 3px;">
                    ${query.sql_summary}
                </code>
            </div>
        `).join('')}
    `;
}

function renderLLMContextTab(metadata) {
    const tab = document.getElementById('debug-llm-tab');

    if (!metadata || Object.keys(metadata).length === 0) {
        tab.innerHTML = '<div class="empty-state">No LLM metadata available</div>';
        return;
    }

    tab.innerHTML = `
        <div class="stage-card" style="margin-bottom: 15px;">
            <strong style="font-size: 13px; margin-bottom: 10px; display: block;">LLM Request Info</strong>
            <div class="score-breakdown">
                <div class="score-item">
                    <span class="score-label">Model:</span>
                    <span class="score-value">${metadata.model || 'N/A'}</span>
                </div>
                <div class="score-item">
                    <span class="score-label">Tokens:</span>
                    <span class="score-value">${metadata.tokens_used || 0}</span>
                </div>
                <div class="score-item">
                    <span class="score-label">Cost:</span>
                    <span class="score-value" style="color: #48bb78;">
                        $${(metadata.cost_usd || 0).toFixed(4)}
                    </span>
                </div>
                <div class="score-item">
                    <span class="score-label">Mode:</span>
                    <span class="score-value">${metadata.mode || 'fallback'}</span>
                </div>
            </div>
        </div>

        ${metadata.prompt ? `
            <div class="stage-card">
                <strong style="font-size: 13px; margin-bottom: 10px; display: block;">
                    Prompt Sent to LLM
                </strong>
                <pre style="font-size: 10px; white-space: pre-wrap; max-height: 300px; overflow-y: auto; background: white; padding: 10px; border-radius: 4px;">
${metadata.prompt}
                </pre>
            </div>
        ` : ''}
    `;
}

function renderPerformanceTab(performance) {
    const tab = document.getElementById('debug-performance-tab');

    if (!performance || Object.keys(performance).length === 0) {
        tab.innerHTML = '<div class="empty-state">No performance data</div>';
        return;
    }

    // Calculate percentages
    const total = performance.total_ms || 1;
    const breakdown = [
        { name: 'Entity Resolution', ms: performance.entity_resolution_ms || 0 },
        { name: 'Memory Retrieval', ms: performance.memory_retrieval_ms || 0 },
        { name: 'Database Queries', ms: performance.database_ms || 0 },
        { name: 'LLM Generation', ms: performance.llm_ms || 0 },
        { name: 'Other', ms: Math.max(0, total - (performance.entity_resolution_ms || 0) - (performance.memory_retrieval_ms || 0) - (performance.database_ms || 0) - (performance.llm_ms || 0)) }
    ].filter(item => item.ms > 0);

    tab.innerHTML = `
        <div class="stage-card" style="margin-bottom: 15px;">
            <strong style="font-size: 13px; margin-bottom: 10px; display: block;">
                Total Duration: ${total.toFixed(1)}ms
            </strong>
            <div class="score-breakdown">
                ${breakdown.map(item => {
                    const percent = (item.ms / total * 100).toFixed(1);
                    return `
                        <div style="margin-bottom: 8px;">
                            <div class="score-item">
                                <span class="score-label">${item.name}:</span>
                                <span class="score-value">${item.ms.toFixed(1)}ms (${percent}%)</span>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${percent}%;"></div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>

        <div class="stage-card">
            <strong style="font-size: 13px; margin-bottom: 10px; display: block;">
                Cost Summary
            </strong>
            <div class="score-breakdown">
                <div class="score-item">
                    <span class="score-label">This Request:</span>
                    <span class="score-value" style="color: #48bb78;">
                        $${(performance.cost_usd || 0).toFixed(4)}
                    </span>
                </div>
            </div>
        </div>
    `;
}

// Modify existing sendChatMessage to render debug panel
async function sendChatMessage() {
    // ... existing code ...

    const data = await response.json();

    // ... existing message display ...

    // Render debug panel with trace data
    if (data.debug) {
        renderDebugPanel(data.debug);
    }
}
```

**Task 3.4: Integration Testing (2 hours)**
- [ ] Test all 5 tabs render correctly
- [ ] Test expand/collapse animation
- [ ] Test tab switching
- [ ] Test with missing data (empty states)
- [ ] Test responsive behavior

**Acceptance Criteria**:
- ✅ Debug panel renders all trace types
- ✅ Visual design matches existing theme
- ✅ Smooth animations
- ✅ All tabs functional
- ✅ Empty states handled gracefully

**Time**: 12 hours (Days 4-5)

---

## 📚 Phase 4: Additional Scenarios (Days 6-7)

### Scenario Definitions

This is the easiest phase - just data definition following existing patterns.

**Task 4.1: Define Scenarios 2, 3, 6, 8, 10, 13, 16 (Easy) - 3 hours**
**Task 4.2: Define Scenarios 7, 11, 14, 17 (Medium) - 3 hours**
**Task 4.3: Define Scenario 18 (Complex) - 2 hours**
**Task 4.4: Test all 18 scenarios load correctly - 4 hours**
**Task 4.5: Update UI to show 18 cards - 1 hour**
**Task 4.6: Verify debug panel works with all scenarios - 3 hours**

**Acceptance Criteria**:
- ✅ All 18 scenarios defined
- ✅ All scenarios load without errors
- ✅ UI shows all 18 cards
- ✅ Debug panel populated correctly for each

**Time**: 16 hours (Days 6-7)

---

## ✨ Phase 5: UX Polish (Days 8-9)

**Task 5.1: Column Sorting** - 2 hours
**Task 5.2: Tooltips on hover** - 2 hours
**Task 5.3: Onboarding tutorial** - 3 hours
**Task 5.4: Keyboard shortcuts** - 1 hour
**Task 5.5: Loading skeletons** - 2 hours
**Task 5.6: Responsive design tweaks** - 2 hours
**Task 5.7: Success notifications** - 2 hours
**Task 5.8: Documentation updates** - 2 hours

**Time**: 16 hours (Days 8-9)

---

## ✅ Completion Checklist

### Phase 1: LLM Integration
- [ ] LLM port created
- [ ] OpenAI adapter implemented
- [ ] LLMReplyGenerator enhanced
- [ ] Wired to DI container
- [ ] Chat endpoint updated
- [ ] Tests passing
- [ ] Works with and without API key

### Phase 2: Debug Instrumentation
- [ ] Trace data structures defined
- [ ] DebugTraceService created
- [ ] Callback pattern implemented
- [ ] All services instrumented
- [ ] Wired to chat endpoint
- [ ] Tests passing
- [ ] Zero performance impact when disabled

### Phase 3: Debug Panel UI
- [ ] CSS styling complete
- [ ] HTML structure added
- [ ] JavaScript functions written
- [ ] All 5 tabs functional
- [ ] Integration tests passing
- [ ] Visual design matches theme

### Phase 4: Additional Scenarios
- [ ] All 18 scenarios defined
- [ ] All scenarios load correctly
- [ ] UI updated for 18 cards
- [ ] Debug panel works with all
- [ ] Tests passing

### Phase 5: UX Polish
- [ ] All polish features implemented
- [ ] Responsive design verified
- [ ] Documentation updated
- [ ] Final testing complete

---

## 📊 Effort Summary

| Phase | Duration | Priority | Risk |
|-------|----------|----------|------|
| 1. LLM Integration | 1 day | High | Low |
| 2. Debug Instrumentation | 2 days | Critical | Medium |
| 3. Debug Panel UI | 2 days | Critical | Low |
| 4. Additional Scenarios | 2 days | Medium | Low |
| 5. UX Polish | 2 days | Low | Low |

**Total**: 9 days

**Can be shortened to**:
- Minimum (Phases 1-3): 5 days
- Recommended (Phases 1-4): 7 days
- Complete (All phases): 9 days

---

## 🎯 Success Metrics

**Functional**:
- [ ] Chat generates natural language replies
- [ ] Debug panel shows all trace types
- [ ] 18 scenarios load and work correctly
- [ ] UX feels polished and professional

**Quality**:
- [ ] 90%+ test coverage maintained
- [ ] No hexagonal architecture violations
- [ ] All error cases handled gracefully
- [ ] Documentation complete

**Performance**:
- [ ] Chat response < 1s P95 (with LLM)
- [ ] Debug overhead < 50ms
- [ ] UI remains responsive

**User Experience**:
- [ ] Demo is self-explanatory
- [ ] Debug panel enhances understanding
- [ ] No confusing states or errors

---

## 🚀 Ready to Execute

This plan is:
- ✅ **Comprehensive** - Every detail thought through
- ✅ **Architecture-aligned** - Pure hexagonal design
- ✅ **Vision-driven** - Every feature serves vision principles
- ✅ **Testable** - Incremental with tests at each step
- ✅ **Incremental** - Each phase stands alone

**Next step**: Start Phase 1 (LLM Integration) when ready!
