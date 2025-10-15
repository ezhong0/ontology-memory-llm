# Demo Implementation Roadmap

**Strategy**: Vertical slice with rapid iteration
**Timeline**: 4 weeks (aggressive but achievable)
**Philosophy**: Ship early, iterate often, validate continuously

---

## Executive Summary

### The Strategy: Modified Vertical Slice

Instead of building all backend then all frontend, we'll build **complete end-to-end features incrementally**:

1. **Week 1**: ONE scenario working end-to-end (but architected for all 18)
2. **Week 2**: Expand to 6 scenarios + database explorer
3. **Week 3**: Complete all 18 scenarios + memory explorer
4. **Week 4**: Chat interface + polish + documentation

**Why this works**:
- ✅ See working demo in days, not weeks
- ✅ Validate architecture early with real usage
- ✅ Stakeholders see progress weekly
- ✅ Can stop at any week and have something usable
- ✅ Each week builds on proven foundation

### Key Principles

1. **Start Concrete, Then Abstract** - Build Scenario 1 fully, extract patterns, apply to rest
2. **Working Software Over Perfect Code** - Refactor in week 4, not week 1
3. **Test Critical Paths Only** - 80/20 rule (focus on what breaks)
4. **UI Can Be Ugly** - Functionality first, polish later
5. **Defer Non-Essential Features** - Debug panel? Week 4. Core flow? Week 1.

---

## Phase 0: Foundation (Days 1-2)

**Goal**: Set up infrastructure so we can move fast

### Tasks

#### Backend Setup
- [ ] Create `src/demo/` directory structure
- [ ] Create `src/infrastructure/database/domain_models.py`
- [ ] Add domain schema migration (customers, sales_orders, invoices, work_orders, payments, tasks)
- [ ] Run migration: `make db-migrate`
- [ ] Verify tables created: `make db-shell` + `\dt domain.*`

#### Frontend Setup
- [ ] Initialize Vite + React + TypeScript in `demo-ui/`
- [ ] Install dependencies (TanStack Query, Zustand, shadcn/ui)
- [ ] Create basic layout (Header + Sidebar + Content)
- [ ] Set up API client (Axios)
- [ ] Add to docker-compose.yml

#### Testing Setup
- [ ] Create `tests/demo/` directory
- [ ] Add `conftest.py` with demo fixtures
- [ ] Verify `make test-demo` works (even with no tests yet)

### Acceptance Criteria
- [ ] `docker-compose up` starts backend + frontend + DB
- [ ] Can access frontend at `http://localhost:3000`
- [ ] Can access backend API docs at `http://localhost:8000/docs`
- [ ] Domain schema tables exist in database
- [ ] `make check-demo-isolation` passes

### Time Budget: 8 hours (1 full day)

**Risk**: Docker/environment issues
**Mitigation**: Use existing docker-compose, just add demo-ui service

---

## Phase 1: First Vertical Slice (Days 3-5)

**Goal**: Scenario 1 working end-to-end (minimal but complete)

### Scenario 1: "Overdue Invoice Follow-Up"
- Customer: "Kai Media"
- Invoice: INV-1009 ($1200, due 2025-09-30, open)
- Memory: "prefers Friday deliveries"
- Query: "Draft email about unpaid invoice mentioning delivery preference"

### Backend Tasks

#### 1.1 Domain Models (2 hours)
```python
# src/infrastructure/database/domain_models.py
class DomainCustomer(Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "domain"}
    customer_id = Column(UUID, primary_key=True)
    name = Column(Text, nullable=False)
    industry = Column(Text)
```

**Files to create**:
- [ ] `src/infrastructure/database/domain_models.py` (Customer, Invoice only for now)

**Test**:
```python
# tests/demo/test_domain_models.py
async def test_create_customer(test_db):
    customer = DomainCustomer(name="Test", industry="Tech")
    test_db.add(customer)
    await test_db.commit()
    assert customer.customer_id is not None
```

#### 1.2 Scenario Data Structure (1 hour)
```python
# src/demo/models/scenario.py
@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: int
    title: str
    setup_sql: str  # ← Start simple: raw SQL
    expected_query: str
```

**Files to create**:
- [ ] `src/demo/models/scenario.py`

#### 1.3 Scenario Loader (Minimal) (3 hours)
```python
# src/demo/services/scenario_loader.py
class ScenarioLoaderService:
    async def load_scenario_1(self):
        # Hardcode for now - we'll generalize later
        customer = DomainCustomer(name="Kai Media", industry="Entertainment")
        await self.customer_repo.create(customer)

        # Create invoice (need sales_order first)
        # Create semantic memory using production service
        entity = await self.entity_resolver.resolve("Kai Media", ...)
        memory = await self.memory_creator.create(
            subject_entity_id=entity.entity_id,
            predicate="prefers_delivery_day",
            object_value={"day": "Friday"}
        )
```

**Files to create**:
- [ ] `src/demo/services/scenario_loader.py`
- [ ] `src/demo/services/__init__.py`

**Test**:
```python
# tests/demo/test_scenario_loader.py
async def test_load_scenario_1(test_db, scenario_loader):
    result = await scenario_loader.load_scenario_1()

    # Verify customer created
    customers = await test_db.execute(select(DomainCustomer))
    assert len(customers.all()) == 1

    # Verify memory created
    memories = await test_db.execute(select(SemanticMemory))
    assert len(memories.all()) == 1
```

#### 1.4 Demo API Route (1 hour)
```python
# src/demo/api/scenarios.py
@router.post("/demo/scenarios/1/load")
async def load_scenario_1(loader: ScenarioLoaderService = Depends()):
    result = await loader.load_scenario_1()
    return {"message": "Scenario 1 loaded", "details": result}
```

**Files to create**:
- [ ] `src/demo/api/scenarios.py`
- [ ] `src/demo/api/__init__.py`

**Test** (manual):
```bash
curl -X POST http://localhost:8000/demo/scenarios/1/load
# Should return 200
```

### Frontend Tasks

#### 1.5 Scenario Card Component (2 hours)
```typescript
// src/features/scenarios/components/ScenarioCard.tsx
export function ScenarioCard({ scenario }) {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scenario {scenario.id}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{scenario.title}</p>
      </CardContent>
      <CardFooter>
        <Button onClick={handleLoad}>
          {isLoaded ? "Loaded ✓" : "Load Scenario"}
        </Button>
      </CardFooter>
    </Card>
  );
}
```

**Files to create**:
- [ ] `demo-ui/src/features/scenarios/components/ScenarioCard.tsx`
- [ ] `demo-ui/src/features/scenarios/api/scenarios.ts` (API client)
- [ ] `demo-ui/src/features/scenarios/hooks/useLoadScenario.ts` (TanStack Query)

#### 1.6 Scenarios Page (1 hour)
```typescript
// src/features/scenarios/ScenariosPage.tsx
export function ScenariosPage() {
  const scenarios = [
    { id: 1, title: "Overdue invoice follow-up", ... }
  ];

  return (
    <div className="grid grid-cols-1 gap-4">
      {scenarios.map(s => <ScenarioCard key={s.id} scenario={s} />)}
    </div>
  );
}
```

**Files to create**:
- [ ] `demo-ui/src/features/scenarios/ScenariosPage.tsx`
- [ ] `demo-ui/src/App.tsx` (add route)

### Acceptance Criteria (Phase 1)
- [ ] Visit `http://localhost:3000/scenarios`
- [ ] See one scenario card
- [ ] Click "Load Scenario" button
- [ ] Button changes to "Loaded ✓"
- [ ] Check database: `SELECT * FROM domain.customers;` shows "Kai Media"
- [ ] Check database: `SELECT * FROM app.semantic_memories;` shows Friday preference
- [ ] `make test-demo` passes (at least 3 tests)

### Time Budget: 10 hours (~1.5 days)

**Checkpoint**: Stop here and review. Does the architecture feel right? If yes, proceed. If no, refactor now before adding more.

---

## Phase 2: Pattern Extraction + Scale to 6 Scenarios (Days 6-9)

**Goal**: Generalize Phase 1 patterns, add 5 more scenarios

### Why These 6 Scenarios?

I picked scenarios that exercise different parts of the system:

1. ✅ **Scenario 1**: Memory retrieval (done)
2. **Scenario 4**: Memory extraction (user states fact)
3. **Scenario 5**: Domain grounding (partial payments calculation)
4. **Scenario 9**: Cold-start grounding (no memories, pure DB)
5. **Scenario 12**: Entity resolution (fuzzy matching)
6. **Scenario 15**: Explainability (trace provenance)

**Coverage**: Memory, DB queries, entity resolution, extraction, explainability

### Backend Tasks

#### 2.1 Generalize Scenario Loader (4 hours)

**Before** (hardcoded):
```python
async def load_scenario_1(self):
    customer = DomainCustomer(name="Kai Media", ...)
    # ...
```

**After** (data-driven):
```python
# src/demo/models/scenario.py
@dataclass(frozen=True)
class DomainSetup:
    customers: List[Dict[str, Any]]
    sales_orders: List[Dict[str, Any]]
    invoices: List[Dict[str, Any]]
    # ...

@dataclass(frozen=True)
class MemorySetup:
    type: str  # semantic, episodic
    data: Dict[str, Any]

@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: int
    title: str
    domain_setup: DomainSetup
    memory_setup: List[MemorySetup]
    expected_query: str

# src/demo/services/scenario_registry.py
SCENARIOS = {
    1: ScenarioDefinition(
        scenario_id=1,
        title="Overdue invoice follow-up",
        domain_setup=DomainSetup(
            customers=[{"name": "Kai Media", "industry": "Entertainment"}],
            invoices=[{"invoice_number": "INV-1009", ...}],
        ),
        memory_setup=[
            MemorySetup(type="semantic", data={
                "subject": "Kai Media",
                "predicate": "prefers_delivery_day",
                "object_value": {"day": "Friday"}
            })
        ],
        expected_query="Draft email about unpaid invoice..."
    )
}

# src/demo/services/scenario_loader.py
class ScenarioLoaderService:
    async def load_scenario(self, scenario_id: int):
        scenario = SCENARIOS[scenario_id]

        # Generic insertion logic
        for customer_data in scenario.domain_setup.customers:
            customer = DomainCustomer(**customer_data)
            await self.customer_repo.create(customer)

        # Generic memory creation logic
        for memory_data in scenario.memory_setup:
            await self._create_memory(memory_data)
```

**Files to modify**:
- [ ] `src/demo/models/scenario.py` (add data structures)
- [ ] `src/demo/services/scenario_registry.py` (NEW - define all scenarios)
- [ ] `src/demo/services/scenario_loader.py` (refactor to generic)

**Files to create**:
- [ ] `src/demo/repositories/domain_repository.py` (CRUD for domain tables)

**Tests**:
```python
async def test_load_scenario_generic(scenario_loader):
    """Test that generalized loader works for scenario 1"""
    result = await scenario_loader.load_scenario(1)
    assert result.entities_created == 1
    assert result.memories_created == 1
```

#### 2.2 Define Scenarios 4, 5, 9, 12, 15 (3 hours)

Add to `scenario_registry.py`:
```python
SCENARIOS = {
    1: ScenarioDefinition(...),  # Already done
    4: ScenarioDefinition(
        scenario_id=4,
        title="NET terms learning",
        domain_setup=DomainSetup(
            customers=[{"name": "TC Boiler", "industry": "Industrial"}]
        ),
        memory_setup=[],  # No initial memories - user will state them
        expected_query="Remember: TC Boiler is NET15 and prefers ACH"
    ),
    5: ScenarioDefinition(...),
    9: ScenarioDefinition(...),
    12: ScenarioDefinition(...),
    15: ScenarioDefinition(...),
}
```

**Files to modify**:
- [ ] `src/demo/services/scenario_registry.py`

#### 2.3 Update API to Support All Scenarios (1 hour)

```python
# src/demo/api/scenarios.py
@router.get("/demo/scenarios")
async def list_scenarios():
    return [
        {"id": s.scenario_id, "title": s.title}
        for s in SCENARIOS.values()
    ]

@router.post("/demo/scenarios/{scenario_id}/load")
async def load_scenario(scenario_id: int, loader: ScenarioLoaderService = Depends()):
    result = await loader.load_scenario(scenario_id)
    return result
```

**Files to modify**:
- [ ] `src/demo/api/scenarios.py`

### Frontend Tasks

#### 2.4 Dynamic Scenario List (1 hour)

```typescript
// src/features/scenarios/hooks/useScenarios.ts
export function useScenarios() {
  return useQuery({
    queryKey: ['scenarios'],
    queryFn: () => scenariosApi.list(),  // Fetch from backend
  });
}

// src/features/scenarios/ScenariosPage.tsx
export function ScenariosPage() {
  const { data: scenarios, isLoading } = useScenarios();

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {scenarios.map(s => <ScenarioCard key={s.id} scenario={s} />)}
    </div>
  );
}
```

**Files to modify**:
- [ ] `demo-ui/src/features/scenarios/hooks/useScenarios.ts`
- [ ] `demo-ui/src/features/scenarios/ScenariosPage.tsx`

#### 2.5 Database Explorer (Basic) (4 hours)

**Why now?** Need to verify data loaded correctly.

```typescript
// src/features/database/components/CustomerTable.tsx
export function CustomerTable() {
  const { data: customers } = useCustomers();

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Industry</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {customers.map(c => (
          <TableRow key={c.customer_id}>
            <TableCell>{c.name}</TableCell>
            <TableCell>{c.industry}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

**Files to create**:
- [ ] `src/demo/api/database.py` (backend endpoints for CRUD)
- [ ] `demo-ui/src/features/database/DatabasePage.tsx`
- [ ] `demo-ui/src/features/database/components/CustomerTable.tsx`
- [ ] `demo-ui/src/features/database/components/InvoiceTable.tsx`
- [ ] `demo-ui/src/features/database/hooks/useCustomers.ts`

**Keep it simple**: Read-only tables for now. Edit in Week 3.

### Acceptance Criteria (Phase 2)
- [ ] Visit `/scenarios` - see 6 scenario cards
- [ ] Load each scenario - all succeed
- [ ] Visit `/database` - see tabs for customers, invoices, etc.
- [ ] Each tab shows data loaded from scenarios
- [ ] `make test-demo` has tests for all 6 scenarios

### Time Budget: 12 hours (~2 days)

**Checkpoint**: Can load 6 scenarios, view data in database explorer. Architecture feels solid?

---

## Phase 3: Complete All 18 Scenarios + Memory Explorer (Days 10-14)

**Goal**: Production-complete backend, functional frontend for all scenarios

### Backend Tasks

#### 3.1 Define Remaining 12 Scenarios (4 hours)

Add scenarios 2, 3, 6, 7, 8, 10, 11, 13, 14, 16, 17, 18 to registry.

**Complexity tiers**:
- **Easy** (1-2 entities): 2, 3, 6, 8, 10, 13, 16
- **Medium** (3-4 entities): 7, 11, 14, 17
- **Complex** (multi-step): 18

**Files to modify**:
- [ ] `src/demo/services/scenario_registry.py`

**Strategy**: Copy-paste scenario 1 structure, modify data. Don't overthink.

#### 3.2 Handle Complex Scenarios (3 hours)

Some scenarios need special handling:

**Scenario 7 (Conflicting memories)**:
```python
memory_setup=[
    MemorySetup(type="semantic", data={
        "subject": "Kai Media",
        "predicate": "prefers_delivery_day",
        "object_value": {"day": "Thursday"},
        "confidence": 0.7,
        "created_at": datetime(2025, 1, 1)  # Older
    }),
    MemorySetup(type="semantic", data={
        "subject": "Kai Media",
        "predicate": "prefers_delivery_day",
        "object_value": {"day": "Friday"},
        "confidence": 0.85,
        "created_at": datetime(2025, 2, 1)  # Newer
    })
]
```

**Scenario 17 (DB vs memory conflict)**:
```python
domain_setup=DomainSetup(
    sales_orders=[{
        "so_number": "SO-1001",
        "status": "in_fulfillment"  # DB truth
    }]
),
memory_setup=[
    MemorySetup(type="semantic", data={
        "subject": "SO-1001",
        "predicate": "status",
        "object_value": {"status": "fulfilled"},  # Memory wrong
        "created_at": datetime(2025, 1, 1)  # Old
    })
]
```

**Files to modify**:
- [ ] `src/demo/services/scenario_loader.py` (handle backdating, conflicts)

#### 3.3 Reset Functionality (2 hours)

```python
# src/demo/api/scenarios.py
@router.post("/demo/reset")
async def reset_all(loader: ScenarioLoaderService = Depends()):
    """Delete all demo data."""
    await loader.reset()
    return {"message": "All demo data deleted"}

# src/demo/services/scenario_loader.py
async def reset(self):
    # Delete in correct order (foreign keys)
    await self.db.execute("DELETE FROM domain.payments")
    await self.db.execute("DELETE FROM domain.invoices")
    await self.db.execute("DELETE FROM domain.work_orders")
    await self.db.execute("DELETE FROM domain.sales_orders")
    await self.db.execute("DELETE FROM domain.tasks")
    await self.db.execute("DELETE FROM domain.customers")

    # Delete memories
    await self.db.execute("DELETE FROM app.semantic_memories WHERE user_id = 'demo-user'")
    await self.db.execute("DELETE FROM app.episodic_memories WHERE user_id = 'demo-user'")
    await self.db.execute("DELETE FROM app.entity_aliases WHERE user_id = 'demo-user'")

    await self.db.commit()
```

**Files to modify**:
- [ ] `src/demo/api/scenarios.py`
- [ ] `src/demo/services/scenario_loader.py`

### Frontend Tasks

#### 3.4 Memory Explorer (6 hours)

**Why now?** Users need to see memories created by scenarios.

```typescript
// src/features/memories/MemoriesPage.tsx
export function MemoriesPage() {
  return (
    <Tabs defaultValue="semantic">
      <TabsList>
        <TabsTrigger value="episodic">Episodic</TabsTrigger>
        <TabsTrigger value="semantic">Semantic</TabsTrigger>
        <TabsTrigger value="procedural">Procedural</TabsTrigger>
        <TabsTrigger value="summaries">Summaries</TabsTrigger>
      </TabsList>

      <TabsContent value="semantic">
        <SemanticMemoryList />
      </TabsContent>
      {/* ... */}
    </Tabs>
  );
}

// src/features/memories/components/SemanticMemoryList.tsx
export function SemanticMemoryList() {
  const { data: memories } = useSemanticMemories();

  return (
    <div className="space-y-2">
      {memories.map(m => (
        <Card key={m.memory_id}>
          <CardContent>
            <div className="flex justify-between">
              <div>
                <p className="font-medium">{m.subject_entity_name}</p>
                <p className="text-sm text-muted-foreground">
                  {m.predicate}: {JSON.stringify(m.object_value)}
                </p>
              </div>
              <Badge>{(m.confidence * 100).toFixed(0)}%</Badge>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

**Files to create**:
- [ ] `src/demo/api/memories.py` (backend endpoints)
- [ ] `demo-ui/src/features/memories/MemoriesPage.tsx`
- [ ] `demo-ui/src/features/memories/components/SemanticMemoryList.tsx`
- [ ] `demo-ui/src/features/memories/components/EpisodicMemoryList.tsx`
- [ ] `demo-ui/src/features/memories/hooks/useMemories.ts`

#### 3.5 Reset Button (1 hour)

```typescript
// src/features/scenarios/components/ResetButton.tsx
export function ResetButton() {
  const resetMutation = useMutation({
    mutationFn: scenariosApi.reset,
    onSuccess: () => {
      queryClient.invalidateQueries(['customers']);
      queryClient.invalidateQueries(['memories']);
      toast.success("All demo data deleted");
    }
  });

  return (
    <Button
      variant="destructive"
      onClick={() => resetMutation.mutate()}
    >
      Reset All Data
    </Button>
  );
}
```

**Files to create**:
- [ ] `demo-ui/src/features/scenarios/components/ResetButton.tsx`

### Acceptance Criteria (Phase 3)
- [ ] All 18 scenarios load successfully
- [ ] Can view all domain tables in database explorer
- [ ] Can view all memory types in memory explorer
- [ ] Reset button clears all data
- [ ] No crashes, no 500 errors
- [ ] `make test-demo` covers major scenarios

### Time Budget: 16 hours (~2.5 days)

**Checkpoint**: All 18 scenarios work. Basic exploration UI. Ready for chat?

---

## Phase 4: Chat Interface + Polish (Days 15-20)

**Goal**: Natural language interaction + production-ready quality

### Backend Tasks

#### 4.1 Enhanced Chat Endpoint (3 hours)

```python
# src/demo/api/chat.py
from src.demo.services.debug_trace import DebugTraceService

@router.post("/demo/chat")
async def demo_chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(),
    trace_service: DebugTraceService = Depends()
):
    """Enhanced chat with debug information."""

    # Start trace
    trace = trace_service.start_trace("chat")

    # Process message using production ChatService
    response = await chat_service.process_message(
        user_id=request.user_id,
        message=request.message
    )

    # Complete trace
    trace = trace_service.complete_trace()

    return {
        "reply": response.reply,
        "debug_trace": {
            "entities_resolved": trace.entity_resolutions,
            "memories_retrieved": trace.memory_retrievals,
            "db_queries": trace.database_queries,
            "reasoning_steps": trace.reasoning_steps,
            "duration_ms": trace.total_duration_ms
        }
    }
```

**Files to create**:
- [ ] `src/demo/api/chat.py`
- [ ] `src/demo/services/debug_trace.py`

**Challenge**: Instrumenting production services to collect traces
**Solution**: Use contextvars + decorator pattern (from DEMO_ARCHITECTURE.md)

#### 4.2 Trace Collection (4 hours)

Add tracing to production services (non-invasive):

```python
# src/domain/services/entity_resolution_service.py
from src.demo.services.debug_trace import DebugTraceService

class EntityResolver:
    async def resolve(self, mention: str, context: ResolutionContext):
        start = time.time()

        # ... existing logic ...

        # If in demo mode, record trace
        if settings.DEMO_MODE_ENABLED:
            DebugTraceService.trace_entity_resolution(
                EntityResolutionTrace(
                    mention=mention,
                    resolved_entity_id=result.entity_id,
                    confidence=result.confidence,
                    method=result.method,
                    duration_ms=(time.time() - start) * 1000
                )
            )

        return result
```

**Files to modify**:
- [ ] `src/domain/services/entity_resolution_service.py`
- [ ] `src/domain/services/memory_retriever.py`
- [ ] `src/infrastructure/database/repositories/*_repository.py` (for DB query traces)

**⚠️ Warning**: This violates pure demo isolation (production knows about demo)
**Mitigation**: Keep traces optional, guarded by `if settings.DEMO_MODE_ENABLED`
**Alternative**: Wrap services in demo proxies (cleaner but more work)

### Frontend Tasks

#### 4.3 Chat Interface (6 hours)

```typescript
// src/features/chat/ChatPage.tsx
export function ChatPage() {
  const { messages, sendMessage, isLoading } = useChat();
  const [input, setInput] = useState("");
  const debugPanelOpen = useUIStore(s => s.debugPanelOpen);

  return (
    <div className="flex h-full gap-4">
      <Card className="flex-1 flex flex-col">
        {/* Messages */}
        <ScrollArea className="flex-1 p-4">
          {messages.map(m => <MessageBubble key={m.id} message={m} />)}
        </ScrollArea>

        {/* Input */}
        <div className="p-4 border-t">
          <form onSubmit={handleSubmit}>
            <Textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type your message..."
            />
            <Button type="submit" disabled={isLoading}>Send</Button>
          </form>
        </div>
      </Card>

      {debugPanelOpen && <DebugPanel messages={messages} />}
    </div>
  );
}
```

**Files to create**:
- [ ] `demo-ui/src/features/chat/ChatPage.tsx`
- [ ] `demo-ui/src/features/chat/components/ChatWindow.tsx`
- [ ] `demo-ui/src/features/chat/components/MessageBubble.tsx`
- [ ] `demo-ui/src/features/chat/hooks/useChat.ts`

#### 4.4 Debug Panel (4 hours)

```typescript
// src/features/chat/components/DebugPanel.tsx
export function DebugPanel({ messages }) {
  const lastMessage = messages.filter(m => m.role === 'assistant').slice(-1)[0];
  const trace = lastMessage?.debug_trace;

  return (
    <Card className="w-96">
      <Tabs defaultValue="memories">
        <TabsList>
          <TabsTrigger value="memories">Memories</TabsTrigger>
          <TabsTrigger value="database">Database</TabsTrigger>
          <TabsTrigger value="entities">Entities</TabsTrigger>
        </TabsList>

        <TabsContent value="memories">
          {trace?.memories_retrieved.map(m => (
            <div key={m.memory_id}>
              <Badge>{m.type}</Badge>
              <p>{m.content}</p>
              <span>Score: {m.score.toFixed(3)}</span>
            </div>
          ))}
        </TabsContent>
        {/* ... */}
      </Tabs>
    </Card>
  );
}
```

**Files to create**:
- [ ] `demo-ui/src/features/chat/components/DebugPanel.tsx`

#### 4.5 Polish & Refinement (3 hours)

- [ ] Add loading states everywhere
- [ ] Add error boundaries
- [ ] Add toast notifications
- [ ] Improve responsive design
- [ ] Add keyboard shortcuts (Cmd+K for chat, etc.)
- [ ] Add empty states ("No scenarios loaded yet")

**Files to create/modify**:
- [ ] `demo-ui/src/components/common/LoadingSpinner.tsx`
- [ ] `demo-ui/src/components/common/ErrorBoundary.tsx`
- [ ] Various component files (add polish)

### Documentation Tasks

#### 4.6 Documentation (2 hours)

- [ ] Update `docs/demo/QUICK_START.md` with usage instructions
- [ ] Add screenshots to README
- [ ] Create video walkthrough (5 minutes)
- [ ] Document common issues

### Acceptance Criteria (Phase 4)
- [ ] Can chat with system for all 18 scenarios
- [ ] Debug panel shows traces for every response
- [ ] UI is polished (no ugly states)
- [ ] Documentation is complete
- [ ] Video walkthrough recorded

### Time Budget: 22 hours (~3 days)

**Final Checkpoint**: Demo is production-ready. Could show to customers today?

---

## Testing Strategy

### Unit Tests (Ongoing)

Write tests as you build:

**Week 1-2**:
- [ ] `test_scenario_loader.py` - Test scenario loading logic
- [ ] `test_domain_models.py` - Test domain models CRUD
- [ ] `test_scenario_registry.py` - Test scenario definitions parse correctly

**Week 3**:
- [ ] `test_reset_functionality.py` - Test cleanup works
- [ ] `test_scenario_edge_cases.py` - Test conflicts, complex scenarios

**Week 4**:
- [ ] `test_debug_trace.py` - Test trace collection
- [ ] `test_demo_api.py` - Test all API endpoints

**Target**: 60-70% coverage of demo code (not 100% - diminishing returns)

### Integration Tests

- [ ] `test_scenario_e2e.py` - Load scenario → query data → verify correct
- [ ] `test_chat_integration.py` - Send message → verify trace → verify response

### Manual Testing Checklist

Before declaring "done":

- [ ] Load each scenario individually
- [ ] Load all 18 scenarios at once
- [ ] Reset and reload
- [ ] Chat with each scenario's expected query
- [ ] Verify memories shown in memory explorer
- [ ] Verify DB data shown in database explorer
- [ ] Try on different browsers
- [ ] Try on mobile (responsive?)

---

## Risk Mitigation

### Risk 1: Production Services Not Ready

**Problem**: Demo needs working EntityResolver, MemoryRetriever, etc.

**Current Status** (from your context): 121/130 tests passing

**Mitigation**:
- Phase 1-2: Use mocks if services not ready
- Phase 3: Switch to real services
- Phase 4: Fix any integration issues

**Contingency**: If services broken, build minimal stubs:
```python
class StubEntityResolver:
    async def resolve(self, mention: str):
        # Just create entity without fancy resolution
        return CanonicalEntity(entity_id=f"stub-{mention}", ...)
```

### Risk 2: Domain Schema Changes

**Problem**: 18 scenarios need 6 tables. What if schema changes mid-development?

**Mitigation**:
- Lock schema in Phase 0 (Day 1)
- Use Alembic migrations (reversible)
- If schema changes, regenerate migration

**Contingency**: Keep domain schema simple (minimal columns)

### Risk 3: Frontend Complexity

**Problem**: React + TypeScript + TanStack Query steep learning curve

**Mitigation**:
- Use shadcn/ui (pre-built components)
- Copy-paste patterns (don't invent)
- Keep state simple (avoid premature abstraction)

**Contingency**: Simplify UI (tables instead of fancy visualizations)

### Risk 4: Time Overruns

**Problem**: 4 weeks is aggressive

**Mitigation**: **Stop gates** at each phase
- Phase 1 complete? Can stop with 1 working scenario demo
- Phase 2 complete? Can stop with 6 scenarios + data explorer
- Phase 3 complete? Can stop with all scenarios (no chat)

**Each phase delivers value independently**

---

## Decision Points

### After Phase 1 (Day 5)
**Question**: Does the architecture feel right?
- **If YES**: Continue to Phase 2
- **If NO**: Refactor now (add 2-3 days)

### After Phase 2 (Day 9)
**Question**: Are we on track for 4 weeks?
- **If YES**: Continue to Phase 3
- **If NO**: Cut scope
  - Option A: Reduce to 12 scenarios (drop 6 complex ones)
  - Option B: Skip chat interface (focus on data exploration)

### After Phase 3 (Day 14)
**Question**: Do we need chat interface?
- **If YES**: Continue to Phase 4
- **If NO**: Ship with data exploration only (still valuable)

---

## Success Metrics

### Week 1
- [ ] 1 scenario works end-to-end
- [ ] Basic UI loads
- [ ] Can demo to stakeholder

### Week 2
- [ ] 6 scenarios work
- [ ] Database explorer shows data
- [ ] Architecture patterns clear

### Week 3
- [ ] All 18 scenarios work
- [ ] Memory explorer shows memories
- [ ] No crashes

### Week 4
- [ ] Chat interface functional
- [ ] Debug panel shows traces
- [ ] Documentation complete
- [ ] Ready for customer demos

---

## Resource Requirements

### People
- **1 Full-stack developer** (you)
- **Optional**: Designer for UI polish (Phase 4)

### Infrastructure
- PostgreSQL (already have)
- OpenAI API (already have)
- Docker (already have)

### Tools
- VS Code
- Postman (API testing)
- Browser DevTools

---

## Daily Schedule (Example)

### Week 1
- **Mon**: Phase 0 setup
- **Tue**: Backend for Scenario 1
- **Wed**: Frontend for Scenario 1
- **Thu**: Integration + testing
- **Fri**: Review + refactor

### Week 2
- **Mon-Tue**: Generalize patterns
- **Wed-Thu**: Add 5 more scenarios
- **Fri**: Database explorer

### Week 3
- **Mon-Wed**: Add remaining 12 scenarios
- **Thu-Fri**: Memory explorer

### Week 4
- **Mon-Tue**: Chat interface
- **Wed**: Debug panel
- **Thu**: Polish
- **Fri**: Documentation + demo video

---

## Post-Launch (Week 5+)

### Enhancements (if time permits)

**Priority 1** (High value, low effort):
- [ ] Scenario descriptions in UI (show what each tests)
- [ ] Direct links: "Load Scenario X" → auto-open chat with expected query
- [ ] Export scenario results (JSON download)

**Priority 2** (Medium value, medium effort):
- [ ] Memory graph visualization (React Flow)
- [ ] Entity relationship diagram (database explorer)
- [ ] Search/filter in tables

**Priority 3** (Lower priority):
- [ ] Edit memories in UI
- [ ] Create custom scenarios in UI
- [ ] Multi-user support (separate demo instances)

### Maintenance

- [ ] Update scenarios as domain services evolve
- [ ] Fix bugs reported by users
- [ ] Keep documentation current

---

## The Bottom Line

### Minimum Viable Demo (2 weeks)
- Phases 0-2 only
- 6 scenarios
- Basic data exploration
- **Good enough** for internal demos

### Full Featured Demo (4 weeks)
- All phases
- All 18 scenarios
- Chat + debug panel
- **Production ready** for customer demos

### Choose Your Adventure
- Tight deadline? Ship Phase 2.
- Want polish? Complete Phase 4.
- Want to learn? Take 6 weeks and add enhancements.

**The roadmap is flexible. Each phase delivers value. You can't fail if you ship early and iterate.**

---

## Appendix: File Checklist

By end of Phase 4, these files should exist:

### Backend
```
src/demo/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── scenarios.py
│   ├── database.py
│   ├── memories.py
│   └── chat.py
├── services/
│   ├── __init__.py
│   ├── scenario_loader.py
│   ├── scenario_registry.py
│   ├── admin_database.py
│   ├── admin_memory.py
│   └── debug_trace.py
├── models/
│   ├── __init__.py
│   ├── scenario.py
│   ├── database.py
│   ├── memory.py
│   └── chat.py
└── repositories/
    ├── __init__.py
    └── domain_repository.py

src/infrastructure/database/
├── domain_models.py  # NEW

tests/demo/
├── conftest.py
├── test_scenario_loader.py
├── test_scenario_registry.py
├── test_domain_models.py
├── test_demo_api.py
└── test_debug_trace.py
```

### Frontend
```
demo-ui/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── features/
│   │   ├── scenarios/
│   │   │   ├── ScenariosPage.tsx
│   │   │   ├── components/ScenarioCard.tsx
│   │   │   ├── hooks/useScenarios.ts
│   │   │   └── api/scenarios.ts
│   │   ├── database/
│   │   │   ├── DatabasePage.tsx
│   │   │   ├── components/
│   │   │   │   ├── CustomerTable.tsx
│   │   │   │   └── InvoiceTable.tsx
│   │   │   └── hooks/useCustomers.ts
│   │   ├── memories/
│   │   │   ├── MemoriesPage.tsx
│   │   │   ├── components/
│   │   │   │   └── SemanticMemoryList.tsx
│   │   │   └── hooks/useMemories.ts
│   │   └── chat/
│   │       ├── ChatPage.tsx
│   │       ├── components/
│   │       │   ├── ChatWindow.tsx
│   │       │   ├── MessageBubble.tsx
│   │       │   └── DebugPanel.tsx
│   │       └── hooks/useChat.ts
│   ├── components/
│   │   ├── ui/  # shadcn/ui components
│   │   └── layout/
│   │       ├── DemoLayout.tsx
│   │       └── Sidebar.tsx
│   ├── lib/
│   │   └── api-client.ts
│   └── stores/
│       └── ui-store.ts
├── package.json
├── tsconfig.json
└── vite.config.ts
```

**Total**: ~50 files (~3000 lines of code)

---

**Ready to start? Begin with Phase 0 (Foundation). Come back to this roadmap weekly to track progress.**
