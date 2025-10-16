# Frontend Demo Overhaul - Comprehensive Roadmap

**Philosophy**: "Understanding before execution. Quality over speed. Incremental perfection."

This document follows CLAUDE.md principles: thorough investigation, comprehensive solutions, and incremental perfection (complete each piece fully before moving to next).

---

## Table of Contents

1. [Current State Analysis](#current-state-analysis)
2. [Vision & Design Philosophy](#vision--design-philosophy)
3. [Technical Architecture](#technical-architecture)
4. [Implementation Phases](#implementation-phases)
5. [Detailed Specifications](#detailed-specifications)
6. [Risk Assessment](#risk-assessment)
7. [Success Criteria](#success-criteria)

---

## Current State Analysis

### What Exists Today

**HTML Structure** (111 lines - basic):
- Simple 3-tab interface (Scenarios, Database, Memory)
- 6 hardcoded old scenarios (not matching ProjectDescription.md)
- Basic CSS with purple gradient background
- Minimal JavaScript for tab switching and scenario loading
- No dark mode, no debug features, no sophisticated UI

**Backend Status** (WORKING):
- ✅ 18 scenarios in `scenario_registry.py` matching ProjectDescription.md exactly
- ✅ Full 6-layer memory architecture implemented
- ✅ Demo API endpoints working (`/scenarios`, `/memories/*`, `/database/*`)
- ✅ Database schema complete (domain.* and app.* schemas)
- ✅ Scenario loading system functional

**Gap Analysis**:
1. ❌ Frontend shows only 6 old scenarios (backend has 18 new ones)
2. ❌ Database explorer is placeholder ("Coming soon!")
3. ❌ Memory explorer shows basic tables (not reflecting 6-layer architecture)
4. ❌ No dark mode
5. ❌ No debug/reasoning panel for chat messages
6. ❌ Design is dated (2020s early gradient style vs 2024 modern minimalism)

---

## Vision & Design Philosophy

### Design Principles

Following modern design systems (Linear, Vercel, Stripe, Arc Browser):

**1. Information Density with Clarity**
- Show maximum useful information without overwhelming
- Progressive disclosure: overview → detail on demand
- Clear visual hierarchy using type scale, not color

**2. Purposeful Motion**
- Transitions communicate state changes
- Loading states preserve spatial relationships
- No decoration motion (no gratuitous animations)

**3. Dark Mode as First-Class**
- Not an afterthought or inversion
- Careful color selection for readability
- Semantic color tokens (primary, surface, text) not absolute colors

**4. Data Transparency**
- "Show your work" - every claim is traceable
- Debug mode reveals system reasoning
- Database/memory views are ground truth, not summaries

**5. Technical Sophistication**
- This is a tool for engineers, not consumers
- Monospace fonts for data, code blocks for JSON
- Terminal-inspired aesthetics where appropriate
- Embrace complexity, don't hide it

### Visual Language

**Color System**:
```
Light Mode:
- Background: #FAFAFA (near-white, not pure white)
- Surface: #FFFFFF with subtle shadows
- Primary: #2563EB (blue, not purple - purple is dated)
- Text: #0F172A (slate-900, not black)
- Border: #E2E8F0 (slate-200)

Dark Mode:
- Background: #0A0A0A (near-black)
- Surface: #1A1A1A with subtle borders
- Primary: #60A5FA (lighter blue for dark bg)
- Text: #F1F5F9 (slate-100)
- Border: #2A2A2A
```

**Typography**:
```
Sans: -apple-system, 'Inter', 'SF Pro', system-ui
Mono: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace
Headings: 600 weight (semibold)
Body: 400 weight (regular)
Code/data: 500 weight (medium) in mono
```

**Spacing System** (8px base):
```
xs: 4px   (0.5 unit)
sm: 8px   (1 unit)
md: 16px  (2 units)
lg: 24px  (3 units)
xl: 32px  (4 units)
2xl: 48px (6 units)
```

**Component Patterns**:
- Cards: flat with 1px border (no shadows in dark mode)
- Buttons: solid primary, ghost secondary, danger outlined
- Tables: zebra striping in light mode, row borders in dark mode
- Tabs: underline indicator (not background change)
- Badges: outlined with semantic colors
- Code: syntax highlighting for JSON

---

## Technical Architecture

### Component Structure

```
index.html (single-file SPA)
├── CSS (Design System)
│   ├── CSS Custom Properties (theme tokens)
│   ├── Base Styles (reset, typography)
│   ├── Component Styles (modular, BEM-like)
│   └── Utility Classes (spacing, colors)
├── HTML (Semantic Structure)
│   ├── Header (title, theme toggle, global actions)
│   ├── Navigation (tabs with icons)
│   ├── Content Panes (scenarios, database, memory, chat)
│   └── Modals (debug panel, confirmation dialogs)
└── JavaScript (Vanilla, no framework)
    ├── State Management (reactive updates)
    ├── API Client (fetch with error handling)
    ├── Rendering Functions (template literals)
    ├── Event Handlers (delegated)
    └── Theme Controller (localStorage persistence)
```

### API Contract

**Endpoints to Use**:
```
GET  /api/v1/demo/scenarios          → List[ScenarioSummary]
POST /api/v1/demo/scenarios/{id}/load → ScenarioLoadResponse
POST /api/v1/demo/scenarios/reset     → ResetResponse

GET  /api/v1/demo/database/customers       → List[Customer]
GET  /api/v1/demo/database/sales_orders    → List[SalesOrder]
GET  /api/v1/demo/database/invoices        → List[Invoice]
GET  /api/v1/demo/database/work_orders     → List[WorkOrder]
GET  /api/v1/demo/database/payments        → List[Payment]
GET  /api/v1/demo/database/tasks           → List[Task]
GET  /api/v1/demo/database/stats           → DatabaseStats

GET  /api/v1/demo/memories/semantic        → List[SemanticMemory]
GET  /api/v1/demo/memories/entities        → List[CanonicalEntity]
GET  /api/v1/demo/memories/stats           → MemoryStats

POST /api/v1/chat                          → ChatResponse (with reasoning)
```

**Data Models** (TypeScript-style for documentation):
```typescript
interface ScenarioSummary {
  scenario_id: number;
  title: string;
  description: string;
  category: string;
  expected_query: string;
}

interface SemanticMemory {
  memory_id: string;
  subject_entity_id: string;
  subject_entity_name: string;
  predicate: string;
  predicate_type: string;
  object_value: any;
  confidence: number;
  reinforcement_count: number;
  status: string;
  created_at: string;
  last_validated_at: string;
}

interface CanonicalEntity {
  entity_id: string;
  entity_type: string;
  canonical_name: string;
  external_ref: { table: string; id: string } | null;
  alias_count: number;
  created_at: string;
}

interface ChatResponse {
  reply: string;
  reasoning: {
    entities_resolved: Array<{entity: string, method: string, confidence: number}>;
    memories_retrieved: Array<{memory_id: string, score: number}>;
    domain_facts_used: Array<{fact_type: string, content: string}>;
    llm_prompt: string;
    llm_model: string;
    tokens_used: number;
  };
  conversation_id: string;
}
```

### State Management Pattern

```javascript
// Simple reactive state (no framework needed)
const state = {
  theme: 'light',
  activeTab: 'scenarios',
  scenarios: [],
  selectedScenario: null,
  databaseData: {},
  memoryData: {},
  chatMessages: [],
  debugMode: false
};

// Reactive updates
function setState(updates) {
  Object.assign(state, updates);
  render();
}

// Persistent state
function loadState() {
  state.theme = localStorage.getItem('theme') || 'light';
  state.debugMode = localStorage.getItem('debugMode') === 'true';
}

function saveState() {
  localStorage.setItem('theme', state.theme);
  localStorage.setItem('debugMode', state.debugMode);
}
```

---

## Implementation Phases

### Phase 0: Foundation (1-2 hours)

**Goal**: Set up proper architecture without breaking existing functionality.

**Tasks**:
1. ✅ Extract current working JavaScript to understand data flow
2. ✅ Document all API endpoints being used
3. ✅ Create design system constants (colors, spacing, typography)
4. ✅ Set up CSS custom properties for theming
5. ✅ Implement theme toggle (light/dark)
6. ✅ Test theme persistence in localStorage

**Deliverable**: HTML with design system in place, theme toggle working, existing functionality intact.

**Validation**:
- [ ] Can switch between light/dark mode
- [ ] Theme persists on page reload
- [ ] All existing features still work
- [ ] No JavaScript errors in console

---

### Phase 1: Modern UI Foundation (2-3 hours)

**Goal**: Replace outdated styling with modern design system. No new features, just better design.

**Tasks**:

1. **Header Redesign**
   - Clean title with subtle tagline
   - Theme toggle in top-right (moon/sun icon)
   - Breadcrumb showing current location
   - Remove purple gradient background → flat surface color

2. **Navigation Redesign**
   - Horizontal tab bar with icons
   - Underline indicator (not background change)
   - Smooth transition on tab switch
   - Icon + label pattern

3. **Card System**
   - Flat cards with 1px border (not shadows)
   - Consistent padding (24px)
   - Hover state: subtle border color change
   - Section headers with border-bottom

4. **Button System**
   - Primary: solid blue, white text
   - Secondary: ghost (transparent with border)
   - Danger: red outline
   - Loading state: spinner + disabled
   - Consistent sizing (40px height)

5. **Typography Scale**
   - H1: 32px/600
   - H2: 24px/600
   - H3: 20px/600
   - Body: 14px/400
   - Small: 12px/400
   - Code: 13px/500 (mono)

**Deliverable**: Same functionality, dramatically better visual design.

**Validation**:
- [ ] Design feels modern (2024, not 2020)
- [ ] Light and dark modes both look polished
- [ ] Typography hierarchy is clear
- [ ] Interactive elements have proper states
- [ ] Existing features still work

---

### Phase 2: 18 Scenarios (1 hour)

**Goal**: Display all 18 scenarios from backend, matching ProjectDescription.md exactly.

**Tasks**:

1. **Update Scenario Grid**
   - Fetch from `/api/v1/demo/scenarios` (already returns 18)
   - Grid layout: 3 columns on desktop, 2 on tablet, 1 on mobile
   - Each card shows:
     - Scenario number badge
     - Title
     - Category badge (colored by type)
     - Description
     - Expected query (in code block style)
     - "Load Scenario" button
     - Result panel (collapsible)

2. **Category Color Coding**
   ```javascript
   const categoryColors = {
     'memory_retrieval': '#3B82F6',  // blue
     'memory_update': '#8B5CF6',     // purple
     'context_enrichment': '#10B981', // green
     'scheduling': '#F59E0B',        // amber
     'temporal_awareness': '#EC4899', // pink
     'relationship_mapping': '#6366F1', // indigo
     'confidence_management': '#14B8A6', // teal
     'conflict_resolution': '#EF4444', // red
     'entity_resolution': '#F97316', // orange
     'bulk_operations': '#6B7280',   // gray
     'pattern_recognition': '#84CC16', // lime
     'complex_reasoning': '#8B5CF6', // violet
     'pii_safety': '#DC2626',        // red
     'consolidation': '#0891B2',     // cyan
     'explainability': '#7C3AED',    // purple
     'procedural_memory': '#059669', // emerald
     'task_management': '#2563EB'    // blue
   };
   ```

3. **Scenario Loading**
   - Show loading spinner in button
   - Disable all other scenario buttons while loading
   - Display result with stats (customers, orders, invoices, memories created)
   - Success: green alert with checkmark
   - Error: red alert with error message
   - Keep result visible (don't auto-dismiss)

4. **Grid Search/Filter**
   - Search input at top
   - Filter by category dropdown
   - Clear filters button
   - Real-time filtering (no submit button)

**Deliverable**: All 18 scenarios visible, loadable, with filtering.

**Validation**:
- [ ] Exactly 18 scenarios displayed
- [ ] Titles match ProjectDescription.md
- [ ] Categories are correct
- [ ] Load button works for each
- [ ] Results display clearly
- [ ] Filter/search works

---

### Phase 3: Database Explorer (3-4 hours)

**Goal**: One-to-one view of domain database tables. See EXACTLY what's in PostgreSQL.

**Tasks**:

1. **Table Navigation**
   - Vertical tabs on left: Customers, Sales Orders, Invoices, Work Orders, Payments, Tasks
   - Count badge on each tab showing row count
   - Active tab highlighted
   - "Refresh All" button at top

2. **Table View Components**
   ```javascript
   // Pattern for each table
   function renderTable(tableName, data, columns) {
     return `
       <div class="table-container">
         <div class="table-header">
           <h3>${tableName}</h3>
           <span class="count-badge">${data.length} rows</span>
           <button onclick="exportCSV('${tableName}')">Export CSV</button>
         </div>
         <div class="table-scroll">
           <table class="data-table">
             <thead>
               <tr>${columns.map(col => `<th>${col.label}</th>`).join('')}</tr>
             </thead>
             <tbody>
               ${data.map(row => renderRow(row, columns)).join('')}
             </tbody>
           </table>
         </div>
       </div>
     `;
   }
   ```

3. **Column Specifications**

   **Customers**:
   ```javascript
   [
     { key: 'customer_id', label: 'ID', type: 'uuid', width: '200px' },
     { key: 'name', label: 'Name', type: 'text', width: 'auto' },
     { key: 'industry', label: 'Industry', type: 'text', width: '150px' },
     { key: 'notes', label: 'Notes', type: 'text', width: '300px' }
   ]
   ```

   **Sales Orders**:
   ```javascript
   [
     { key: 'so_number', label: 'SO #', type: 'text', width: '100px' },
     { key: 'customer_name', label: 'Customer', type: 'text', width: 'auto' },
     { key: 'title', label: 'Title', type: 'text', width: '200px' },
     { key: 'status', label: 'Status', type: 'badge', width: '120px' },
     { key: 'created_at', label: 'Created', type: 'datetime', width: '150px' }
   ]
   ```

   **Invoices**:
   ```javascript
   [
     { key: 'invoice_number', label: 'Invoice #', type: 'text', width: '100px' },
     { key: 'so_number', label: 'SO #', type: 'link', width: '100px' },
     { key: 'amount', label: 'Amount', type: 'currency', width: '120px' },
     { key: 'due_date', label: 'Due Date', type: 'date', width: '120px' },
     { key: 'status', label: 'Status', type: 'badge', width: '100px' },
     { key: 'issued_at', label: 'Issued', type: 'datetime', width: '150px' }
   ]
   ```

   **Work Orders**:
   ```javascript
   [
     { key: 'wo_id', label: 'WO ID', type: 'uuid', width: '200px' },
     { key: 'so_number', label: 'SO #', type: 'link', width: '100px' },
     { key: 'description', label: 'Description', type: 'text', width: 'auto' },
     { key: 'status', label: 'Status', type: 'badge', width: '120px' },
     { key: 'technician', label: 'Technician', type: 'text', width: '120px' },
     { key: 'scheduled_for', label: 'Scheduled', type: 'date', width: '120px' }
   ]
   ```

   **Payments**:
   ```javascript
   [
     { key: 'payment_id', label: 'Payment ID', type: 'uuid', width: '200px' },
     { key: 'invoice_number', label: 'Invoice #', type: 'link', width: '100px' },
     { key: 'amount', label: 'Amount', type: 'currency', width: '120px' },
     { key: 'method', label: 'Method', type: 'text', width: '100px' },
     { key: 'paid_at', label: 'Paid At', type: 'datetime', width: '150px' }
   ]
   ```

   **Tasks**:
   ```javascript
   [
     { key: 'task_id', label: 'Task ID', type: 'uuid', width: '200px' },
     { key: 'customer_name', label: 'Customer', type: 'text', width: '150px' },
     { key: 'title', label: 'Title', type: 'text', width: 'auto' },
     { key: 'status', label: 'Status', type: 'badge', width: '100px' },
     { key: 'created_at', label: 'Created', type: 'datetime', width: '150px' }
   ]
   ```

4. **Data Type Renderers**
   ```javascript
   function renderCell(value, type) {
     switch(type) {
       case 'uuid':
         return `<code class="uuid">${value.substring(0, 8)}...</code>`;
       case 'currency':
         return `<span class="currency">$${parseFloat(value).toFixed(2)}</span>`;
       case 'date':
         return `<span class="date">${formatDate(value)}</span>`;
       case 'datetime':
         return `<span class="datetime">${formatDateTime(value)}</span>`;
       case 'badge':
         return `<span class="badge badge-${value}">${value}</span>`;
       case 'link':
         return `<a href="#" class="table-link">${value}</a>`;
       default:
         return value || '<span class="null">NULL</span>';
     }
   }
   ```

5. **Table Features**
   - **Sorting**: Click column header to sort (asc/desc)
   - **Search**: Filter rows across all columns
   - **Row highlighting**: Hover effect
   - **Empty state**: "No data" message with "Load a scenario" CTA
   - **Loading state**: Skeleton rows while fetching

6. **Statistics Panel** (top of database tab)
   ```javascript
   // Aggregate stats across all tables
   {
     total_customers: 5,
     total_orders: 12,
     total_invoices: 8,
     open_invoices: 3,
     open_invoice_value: 15600.00,
     completed_work_orders: 6,
     pending_tasks: 4
   }
   ```

**Deliverable**: Complete database explorer showing live PostgreSQL data.

**Validation**:
- [ ] All 6 tables accessible
- [ ] Data matches PostgreSQL exactly (verify with SQL queries)
- [ ] Sorting works on all columns
- [ ] Search filters correctly
- [ ] Empty state shows when no data
- [ ] Stats panel accurate
- [ ] Export CSV works

---

### Phase 4: Memory Explorer (4-5 hours)

**Goal**: One-to-one view of 6-layer memory architecture. Show the ACTUAL memory data structures.

**Tasks**:

1. **Architecture Visualization**
   - Visual diagram showing 6 layers with counts
   - Click a layer to view its data
   - Show data flow: events → entities → semantics → episodic → procedural → summaries
   - Use color coding matching the domain (from DESIGN.md)

2. **Layer Navigation**
   ```
   [ Layer 1: Chat Events ]  [ Layer 2: Entities ]  [ Layer 3: Episodic ]
   [ Layer 4: Semantic ]  [ Layer 5: Procedural ]  [ Layer 6: Summaries ]
   ```
   - Horizontal tabs with layer numbers
   - Badge showing count for each layer
   - Active layer highlighted

3. **Layer 1: Chat Events** (`app.chat_events`)
   ```javascript
   columns: [
     { key: 'event_id', label: 'Event ID', type: 'number' },
     { key: 'session_id', label: 'Session', type: 'uuid' },
     { key: 'role', label: 'Role', type: 'badge' },  // user/assistant/system
     { key: 'content', label: 'Content', type: 'text-preview' },  // truncate
     { key: 'created_at', label: 'Timestamp', type: 'datetime' }
   ]
   ```
   - Expandable rows to see full content
   - Filter by session_id
   - Timeline view option

4. **Layer 2: Entity Resolution** (`app.canonical_entities` + `app.entity_aliases`)

   **Canonical Entities Table**:
   ```javascript
   columns: [
     { key: 'entity_id', label: 'Entity ID', type: 'code' },
     { key: 'entity_type', label: 'Type', type: 'badge' },
     { key: 'canonical_name', label: 'Name', type: 'text' },
     { key: 'external_ref', label: 'External Ref', type: 'json-preview' },
     { key: 'properties', label: 'Properties', type: 'json-preview' },
     { key: 'created_at', label: 'Created', type: 'datetime' }
   ]
   ```

   **Aliases Expandable View** (click entity to see aliases):
   ```javascript
   columns: [
     { key: 'alias_text', label: 'Alias', type: 'text' },
     { key: 'source', label: 'Source', type: 'text' },
     { key: 'metadata', label: 'Context', type: 'json-preview' },
     { key: 'created_at', label: 'Learned', type: 'datetime' }
   ]
   ```

5. **Layer 3: Episodic Memories** (`app.episodic_memories`)
   ```javascript
   columns: [
     { key: 'memory_id', label: 'Memory ID', type: 'uuid' },
     { key: 'event_type', label: 'Event Type', type: 'badge' },
     { key: 'summary', label: 'Summary', type: 'text' },
     { key: 'entities', label: 'Entities', type: 'json-preview' },
     { key: 'importance_score', label: 'Importance', type: 'score' },
     { key: 'created_at', label: 'Created', type: 'datetime' }
   ]
   ```
   - Expandable to show full JSON of entities, context
   - Filter by event_type
   - Sort by importance_score

6. **Layer 4: Semantic Memories** (`app.semantic_memories`)
   ```javascript
   columns: [
     { key: 'memory_id', label: 'Memory ID', type: 'uuid' },
     { key: 'subject_entity_name', label: 'Subject', type: 'entity-link' },
     { key: 'predicate', label: 'Predicate', type: 'code' },
     { key: 'predicate_type', label: 'Type', type: 'badge' },
     { key: 'object_value', label: 'Object', type: 'json' },
     { key: 'confidence', label: 'Confidence', type: 'progress-bar' },
     { key: 'status', label: 'Status', type: 'badge' },
     { key: 'reinforcement_count', label: 'Reinforced', type: 'number' },
     { key: 'last_validated_at', label: 'Last Validated', type: 'datetime' }
   ]
   ```
   - **Confidence visualization**: Progress bar with color (green ≥0.8, yellow 0.6-0.8, red <0.6)
   - **Expandable**: Click to see confidence_factors, provenance
   - **Grouping**: Group by subject entity
   - **Filter**: By predicate_type, status, confidence range

7. **Layer 5: Procedural Memories** (`app.procedural_memories`)
   ```javascript
   columns: [
     { key: 'memory_id', label: 'Memory ID', type: 'uuid' },
     { key: 'pattern_type', label: 'Pattern Type', type: 'badge' },
     { key: 'description', label: 'Description', type: 'text' },
     { key: 'trigger_pattern', label: 'Trigger', type: 'json-preview' },
     { key: 'action_pattern', label: 'Action', type: 'json-preview' },
     { key: 'support', label: 'Support', type: 'number' },
     { key: 'confidence', label: 'Confidence', type: 'progress-bar' },
     { key: 'status', label: 'Status', type: 'badge' }
   ]
   ```
   - Show as "IF trigger THEN action" format in preview
   - Expandable to see full pattern details
   - Sort by support (frequency)

8. **Layer 6: Summaries** (`app.memory_summaries`)
   ```javascript
   columns: [
     { key: 'summary_id', label: 'Summary ID', type: 'uuid' },
     { key: 'user_id', label: 'User', type: 'text' },
     { key: 'session_window', label: 'Window', type: 'number' },
     { key: 'summary', label: 'Summary', type: 'text-expandable' },
     { key: 'created_at', label: 'Created', type: 'datetime' }
   ]
   ```
   - Show summary in markdown-rendered format
   - Expandable to full text
   - Link to source sessions

9. **Cross-Layer Navigation**
   - Click entity ID → jump to entity layer
   - Click memory_id → show full details in modal
   - Click session_id → filter chat events by session
   - Breadcrumb trail: "Memory Layer 4 > Semantic Memory #abc123"

10. **Memory Statistics Dashboard** (top of memory tab)
    ```javascript
    {
      // Counts by layer
      chat_events: 45,
      canonical_entities: 12,
      entity_aliases: 28,
      episodic_memories: 15,
      semantic_memories: 34,
      procedural_memories: 8,
      summaries: 3,

      // Quality metrics
      avg_confidence: 0.82,
      high_confidence_memories: 28,  // ≥0.8
      stale_memories: 3,              // >90 days since validation

      // Activity
      memories_created_today: 8,
      last_consolidation: "2025-10-15T14:23:00Z"
    }
    ```

**Deliverable**: Complete 6-layer memory explorer with rich visualizations.

**Validation**:
- [ ] All 6 layers accessible
- [ ] Data matches PostgreSQL app.* schema
- [ ] Can navigate between layers
- [ ] JSON previews are readable
- [ ] Confidence bars render correctly
- [ ] Statistics are accurate
- [ ] Expandable details work

---

### Phase 5: Chat with Debug Mode (3-4 hours)

**Goal**: Add chat interface with expandable debug panel showing reasoning.

**Tasks**:

1. **Chat Interface** (new tab)
   - Chat message list (scrollable)
   - Input box at bottom (fixed position)
   - Send button (or Enter to send)
   - Clear conversation button
   - Example queries (clickable to populate input)

2. **Message Component**
   ```html
   <div class="message message-user">
     <div class="message-avatar">👤</div>
     <div class="message-content">
       <div class="message-text">{content}</div>
       <div class="message-meta">{timestamp}</div>
     </div>
   </div>

   <div class="message message-assistant">
     <div class="message-avatar">🤖</div>
     <div class="message-content">
       <div class="message-text">{content}</div>
       <div class="message-meta">
         {timestamp} · {tokens} tokens · ${cost}
         <button class="debug-toggle">Show Reasoning</button>
       </div>
       <div class="message-debug" style="display: none;">
         {debug panel content}
       </div>
     </div>
   </div>
   ```

3. **Debug Panel Structure**
   ```javascript
   // When "Show Reasoning" clicked, expand panel below message
   {
     entities_resolved: [
       { entity: "Kai Media", method: "exact_match", confidence: 1.0 }
     ],
     memories_retrieved: [
       { memory_id: "abc123", content: "prefers Friday deliveries", score: 0.92 }
     ],
     domain_facts_used: [
       { fact_type: "invoice_status", content: "INV-1009: $1200 due 2025-09-30" }
     ],
     llm_prompt: "...",  // full prompt sent to LLM
     llm_response: "...",  // raw LLM response
     model: "gpt-4o-mini",
     tokens_used: 342,
     cost: 0.00034
   }
   ```

4. **Debug Panel Rendering**
   ```
   ┌─ Reasoning Trace ─────────────────────────────────────────┐
   │                                                            │
   │ 1. Entity Resolution                                       │
   │    ✓ "Kai Media" → customer:abc123 (exact_match, 1.0)    │
   │                                                            │
   │ 2. Memory Retrieval (Top 3)                               │
   │    • Memory #abc123 (0.92): prefers Friday deliveries     │
   │    • Memory #def456 (0.78): NET30 payment terms           │
   │                                                            │
   │ 3. Domain Facts Retrieved                                 │
   │    • invoice_status: INV-1009 ($1200, due 2025-09-30)     │
   │                                                            │
   │ 4. LLM Generation                                          │
   │    Model: gpt-4o-mini                                      │
   │    Tokens: 342 (prompt: 267, completion: 75)              │
   │    Cost: $0.00034                                          │
   │                                                            │
   │ [View Full Prompt] [View Raw Response]                    │
   └────────────────────────────────────────────────────────────┘
   ```

5. **Expandable Sections in Debug Panel**
   - Click "View Full Prompt" → Modal with full LLM prompt (syntax highlighted)
   - Click "View Raw Response" → Modal with raw LLM JSON response
   - Click memory ID → Jump to memory explorer at that memory
   - Click entity → Jump to entity layer

6. **Debug Mode Toggle** (global)
   - Checkbox in header: "Always show reasoning"
   - If enabled, debug panels auto-expand
   - Persisted in localStorage

7. **Example Queries** (based on loaded scenario)
   ```javascript
   // Show example queries from currently loaded scenario
   // Or default queries if no scenario loaded
   const defaultQueries = [
     "What invoices do we have?",
     "Tell me about Kai Media",
     "Show me overdue invoices",
     "What's the status of SO-1001?"
   ];
   ```

8. **Chat Features**
   - Auto-scroll to bottom on new message
   - Loading indicator while waiting for response
   - Error handling (red message if API fails)
   - Copy message button
   - Regenerate response button (resend same query)

**Deliverable**: Chat interface with comprehensive debug/reasoning view.

**Validation**:
- [ ] Can send messages and get responses
- [ ] Debug panel shows all reasoning steps
- [ ] Links to entities/memories work
- [ ] Full prompt/response modals work
- [ ] Example queries populate input
- [ ] Always-show-debug toggle persists

---

## Risk Assessment

### Technical Risks

**1. API Response Shape Mismatches**
- **Risk**: Frontend expects fields that backend doesn't provide
- **Mitigation**: Test against live API, add null checks, graceful degradation
- **Detection**: Console errors, empty displays

**2. Large Data Sets Causing Performance Issues**
- **Risk**: 1000s of memories could slow table rendering
- **Mitigation**: Virtual scrolling, pagination, or lazy loading
- **Threshold**: >500 rows in a table

**3. Dark Mode Color Contrast Issues**
- **Risk**: Text unreadable in dark mode
- **Mitigation**: Test with WCAG contrast checker, use semantic tokens
- **Validation**: Check all text/background combinations

**4. Browser Compatibility**
- **Risk**: Modern CSS features not supported in old browsers
- **Mitigation**: Target modern browsers only (last 2 versions), document requirements
- **Features to check**: CSS custom properties, grid, fetch API

### Implementation Risks

**1. Scope Creep**
- **Risk**: Adding features beyond requirements
- **Mitigation**: Stick to roadmap, defer "nice to have" to Phase 6
- **Red flag**: "While we're at it, let's also..."

**2. Trying to Fix Backend While Building Frontend**
- **Risk**: Getting distracted by backend issues discovered during integration
- **Mitigation**: Document backend issues but don't fix them (unless blocking)
- **Rule**: Frontend work is frontend work

**3. Over-Engineering**
- **Risk**: Adding frameworks, build tools, etc.
- **Mitigation**: Keep it simple (vanilla JS), resist temptation to "do it properly"
- **Remember**: This is a demo, not a product

**4. Breaking Existing Functionality**
- **Risk**: Refactoring breaks scenario loading
- **Mitigation**: Test after each phase, incremental changes
- **Validation**: Run through all scenarios after each phase

---

## Success Criteria

### Phase Completion Criteria

Each phase is COMPLETE when:
1. ✅ All tasks in phase checklist done
2. ✅ Validation items pass
3. ✅ No console errors
4. ✅ Works in both light and dark mode
5. ✅ Previous phase functionality still works
6. ✅ Code is clean and commented

### Final Success Criteria

The frontend overhaul is SUCCESSFUL when:

**Functional Requirements**:
- [ ] All 18 scenarios load correctly
- [ ] Database explorer shows all 6 tables with accurate data
- [ ] Memory explorer shows all 6 layers with accurate data
- [ ] Chat works with reasoning panel
- [ ] Dark mode works throughout
- [ ] All navigation and filtering works

**Non-Functional Requirements**:
- [ ] Design feels modern and polished (2024 aesthetic)
- [ ] Information density is high but not overwhelming
- [ ] Interactive elements have proper hover/active states
- [ ] Loading states are clear
- [ ] Error states are helpful
- [ ] Mobile-responsive (at least tablet size)

**Quality Requirements**:
- [ ] No console errors or warnings
- [ ] No broken links or dead-end UIs
- [ ] All JSON displays are readable
- [ ] All timestamps are formatted consistently
- [ ] Color contrast passes WCAG AA

**Performance Requirements**:
- [ ] Initial page load < 1s
- [ ] Tab switching < 100ms
- [ ] Table rendering < 500ms (for <1000 rows)
- [ ] API calls display loading state immediately

---

## Development Guidelines

### Before Starting Each Phase

1. **Read the phase specification completely**
2. **Understand the goal** (not just the tasks)
3. **Check current state** (what works, what doesn't)
4. **Plan the order** (dependencies, critical path)
5. **Set up validation** (how will I know it's done?)

### During Each Phase

1. **Commit after each logical chunk** (not at end of phase)
2. **Test in both light and dark mode** (as you go)
3. **Check console for errors** (continuously)
4. **Verify existing features still work** (regression testing)
5. **Keep code clean** (format, comments, naming)

### After Each Phase

1. **Run through all validation items**
2. **Test all tabs and features**
3. **Check mobile view** (at least tablet)
4. **Review code quality** (DRY, clear naming, no TODOs)
5. **Commit with clear message** (what was accomplished)
6. **Document any issues found** (for later or escalation)

### Code Style

**HTML**:
- Semantic elements (`<nav>`, `<section>`, `<article>`)
- Accessible (ARIA labels where needed)
- Data attributes for state (`data-tab="scenarios"`)
- BEM-like class naming (`scenario-card__title`)

**CSS**:
- Mobile-first (base styles, then `@media` for larger)
- CSS custom properties for all colors, spacing
- Modular (one section per component)
- Commented sections

**JavaScript**:
- Pure functions where possible
- Clear function names (verb-noun: `loadScenarios`, `renderTable`)
- No global variables except `state` and `API_BASE`
- Error handling on all async calls
- Comments explaining "why", not "what"

---

## Appendix A: Color Palette Reference

### Light Mode
```css
--color-bg: #FAFAFA;
--color-surface: #FFFFFF;
--color-surface-hover: #F5F5F5;

--color-primary: #2563EB;
--color-primary-hover: #1D4ED8;
--color-primary-light: #DBEAFE;

--color-success: #10B981;
--color-success-light: #D1FAE5;
--color-warning: #F59E0B;
--color-warning-light: #FEF3C7;
--color-error: #EF4444;
--color-error-light: #FEE2E2;

--color-text-primary: #0F172A;
--color-text-secondary: #475569;
--color-text-tertiary: #94A3B8;

--color-border: #E2E8F0;
--color-border-light: #F1F5F9;
```

### Dark Mode
```css
--color-bg: #0A0A0A;
--color-surface: #1A1A1A;
--color-surface-hover: #2A2A2A;

--color-primary: #60A5FA;
--color-primary-hover: #3B82F6;
--color-primary-light: #1E3A8A;

--color-success: #34D399;
--color-success-light: #064E3B;
--color-warning: #FBBF24;
--color-warning-light: #78350F;
--color-error: #F87171;
--color-error-light: #7F1D1D;

--color-text-primary: #F1F5F9;
--color-text-secondary: #CBD5E1;
--color-text-tertiary: #64748B;

--color-border: #2A2A2A;
--color-border-light: #1A1A1A;
```

---

## Appendix B: Typography Scale

```css
/* Headings */
--font-size-h1: 32px;
--line-height-h1: 40px;
--font-weight-h1: 600;

--font-size-h2: 24px;
--line-height-h2: 32px;
--font-weight-h2: 600;

--font-size-h3: 20px;
--line-height-h3: 28px;
--font-weight-h3: 600;

/* Body */
--font-size-base: 14px;
--line-height-base: 20px;
--font-weight-base: 400;

--font-size-small: 12px;
--line-height-small: 16px;

/* Code */
--font-size-code: 13px;
--line-height-code: 20px;
--font-weight-code: 500;
```

---

## Appendix C: Implementation Checklist

Copy this checklist for tracking progress:

### Phase 0: Foundation
- [ ] Extract current working JavaScript
- [ ] Document all API endpoints
- [ ] Create CSS custom properties
- [ ] Implement theme toggle
- [ ] Test theme persistence
- [ ] Validation: All items pass

### Phase 1: Modern UI
- [ ] Header redesign
- [ ] Navigation redesign
- [ ] Card system
- [ ] Button system
- [ ] Typography scale
- [ ] Validation: All items pass

### Phase 2: 18 Scenarios
- [ ] Update scenario grid
- [ ] Category color coding
- [ ] Scenario loading
- [ ] Grid search/filter
- [ ] Validation: All items pass

### Phase 3: Database Explorer
- [ ] Table navigation
- [ ] Table view components
- [ ] All 6 tables implemented
- [ ] Data type renderers
- [ ] Table features (sort, search)
- [ ] Statistics panel
- [ ] Validation: All items pass

### Phase 4: Memory Explorer
- [ ] Architecture visualization
- [ ] Layer navigation
- [ ] Layer 1: Chat Events
- [ ] Layer 2: Entities
- [ ] Layer 3: Episodic
- [ ] Layer 4: Semantic
- [ ] Layer 5: Procedural
- [ ] Layer 6: Summaries
- [ ] Cross-layer navigation
- [ ] Memory statistics dashboard
- [ ] Validation: All items pass

### Phase 5: Chat with Debug
- [ ] Chat interface
- [ ] Message component
- [ ] Debug panel structure
- [ ] Debug panel rendering
- [ ] Expandable sections
- [ ] Debug mode toggle
- [ ] Example queries
- [ ] Chat features
- [ ] Validation: All items pass

### Final Validation
- [ ] All functional requirements met
- [ ] All non-functional requirements met
- [ ] All quality requirements met
- [ ] All performance requirements met
- [ ] No console errors
- [ ] Works in light and dark mode
- [ ] Mobile responsive

---

**END OF ROADMAP**

Next steps: Review this document, adjust if needed, then proceed with Phase 0.
