# Comprehensive User Scenarios: Intelligent Memory System

This document provides extensive scenario coverage for implementing the full UX vision. Each scenario specifies the context, prior state, user input, expected behavior, memory updates, and technical implementation notes.

---

## Table of Contents

**CORE PROJECT SCENARIOS** (Required for submission):
1. [Foundation Scenarios: Basic Memory Operations](#foundation-scenarios-basic-memory-operations) ✅
2. [Entity Intelligence: Linking & Disambiguation](#entity-intelligence-linking--disambiguation) ✅
3. [Contextual Synthesis: Deep Understanding](#contextual-synthesis-deep-understanding) ✅ / 🟢
6. [Cross-Object Reasoning: Entity Relationships](#cross-object-reasoning-entity-relationships) ✅ / 🟢
9. [Confidence & Uncertainty: Transparent Reasoning](#confidence--uncertainty-transparent-reasoning) ✅
10. [Conversation Continuity: Multi-Turn Intelligence](#conversation-continuity-multi-turn-intelligence) ✅ / 🟢

**STRETCH SCENARIOS** (Optional enhancements, LLM-powered):
4. [Pattern Recognition: Insight Discovery](#pattern-recognition-insight-discovery) 🟡
5. [Temporal Intelligence: Time-Based Analysis](#temporal-intelligence-time-based-analysis) 🟡
7. [Strategic Decision Support: Multi-Dimensional Analysis](#strategic-decision-support-multi-dimensional-analysis) 🟡
8. [Workflow Learning: Procedural Intelligence](#workflow-learning-procedural-intelligence) 🟡

---

## Foundation Scenarios: Basic Memory Operations

### S1.1: Explicit Fact Learning (Semantic Memory)

**Context**: User wants to teach the system a business fact not in the database.

**Prior state:**
- DB: Delta Industries exists in `domain.customers`
- Memory: No payment terms stored for Delta Industries

**User**: "Remember: Delta Industries is NET15 and prefers ACH payment."

**Expected behavior**:
```
System: "Noted. I've stored:
- Payment terms: NET15 for Delta Industries
- Payment method preference: ACH

I'll use this information whenever we discuss invoicing or payments for Delta Industries."
```

**Memory updates**:
- Create semantic memory: `kind=semantic, text="Delta Industries payment terms: NET15", entity_link=Delta_Industries, confidence=0.95`
- Create semantic memory: `kind=semantic, text="Delta Industries payment method preference: ACH", entity_link=Delta_Industries, confidence=0.95`
- Link to entity: `app.entities` entry for Delta Industries

**Technical notes**:
- NER should extract "Delta Industries", "NET15", "ACH"
- Entity linker should resolve to `domain.customers.customer_id`
- High confidence (0.95) because explicit user statement
- Tag memory as semantic (distilled fact)

---

### S1.2: Episodic Memory Creation

**Context**: User performs an action or asks a question that should be remembered as an event.

**Prior state:**
- DB: Invoice INV-2201 exists, status=open
- Memory: No prior queries about this invoice

**User**: "What's the balance on INV-2201?"

**Expected behavior**:
```
System: "Invoice INV-2201 for Delta Industries:
- Total: $3,500
- Paid: $1,500 (via ACH on Oct 1)
- Balance: $2,000 remaining
- Due date: Oct 30"
```

**Memory updates**:
- Create episodic memory: `kind=episodic, text="User inquired about invoice balance for INV-2201 on [date]", entity_link=INV-2201, confidence=0.8`
- This episodic memory increases weighting for future finance-related queries about Delta Industries

**Technical notes**:
- Episodic memories track that an inquiry happened, not just the answer
- Used for understanding user patterns and priorities
- Lower confidence (0.8) than explicit facts since it's an inferred interest

---

### S1.3: Memory Consolidation Across Sessions

**Context**: After multiple sessions discussing a customer, consolidate scattered memories into a summary.

**Prior state:**
- DB: Delta Industries with multiple orders, invoices, work orders
- Memory: 15+ individual memories from 4 sessions:
  - Session 1: NET15 payment terms mentioned
  - Session 2: Rush order discussion
  - Session 3: Payment preference (ACH)
  - Session 4: Expansion plans mentioned

**User**: Triggers `/consolidate` endpoint (or automatic after N sessions)

**Expected behavior**:
```
System: "Consolidated memory summary created for Delta Industries based on 4 sessions:

Delta Industries Profile:
- Payment: NET15 terms, ACH preferred
- Activity: 3 rush orders in past 6 months (increasing frequency)
- Context: Currently in expansion phase (capital allocation shift)
- Relationship: 18-month customer, high SLA compliance
- User priorities: Payment timing, rush order capacity

This summary will be used for faster, more comprehensive responses about Delta Industries."
```

**Memory updates**:
- Create consolidated memory: `app.memory_summaries` entry with synthesized summary
- Individual memories remain but lower priority vs consolidated summary
- Summary embedding captures semantic meaning for retrieval

**Technical notes**:
- LLM prompt: "Synthesize these 15 memories into a coherent customer profile"
- Summary should be 150-300 words (substantial but not overwhelming)
- Include confidence levels from source memories
- Tag with session_window (e.g., last 4 sessions)

---

### S1.4: Memory Recall in Context

**Context**: User asks a question that requires combining database facts with stored memories.

**Prior state:**
- DB: Invoice INV-2201, issued Oct 15, due Oct 30, amount $3,500, status=open
- Memory: Semantic memory "Delta Industries NET15 terms"

**User**: "When should we expect payment from Delta Industries on INV-2201?"

**Expected behavior**:
```
System: "Invoice INV-2201 for Delta Industries:
- Issued: Oct 15
- Amount: $3,500
- Due date: Oct 30 (NET15 terms from memory)
- Expected payment: Around Oct 28-29

Delta historically pays 2 days early (based on payment pattern analysis).
Since they prefer ACH, check for bank transfers around Oct 28."
```

**Memory updates**:
- Create episodic memory: User asked about payment timing for Delta Industries
- Reinforce semantic memory about NET15 terms (confidence += 0.02)

**Technical notes**:
- Retrieval combines: DB facts (issued_at, amount, due_date) + semantic memory (NET15) + pattern analysis (payment history)
- Calculate due date: issued_at + 15 days
- Query payment history: `SELECT paid_at - due_date FROM payments JOIN invoices...`
- Synthesize into coherent, forward-looking response

---

### S1.5: Conflict Detection and Resolution

**Context**: Two memories conflict; system must handle gracefully.

**Prior state:**
- Memory A: "Kai Media prefers Thursday deliveries" (created June 15, confidence 0.7)
- Memory B: "Kai Media prefers Friday deliveries" (created Sept 10, confidence 0.8)

**User**: "When should we deliver to Kai Media?"

**Expected behavior**:
```
System: "I have conflicting information about Kai Media's delivery preference:

- Earlier note (June 15): Thursday deliveries
- More recent note (Sept 10): Friday deliveries

Based on recency and reinforcement, I'd recommend Friday. However, since both
were stated explicitly, I want to confirm: is Friday still the current preference?"
```

**User response**: "Yes, Friday is correct."

**Expected follow-up**:
```
System: "Thank you. I've updated my memory:
- Friday delivery preference confirmed (confidence increased)
- Thursday preference marked as outdated

I'll use Friday for all future delivery scheduling for Kai Media."
```

**Memory updates**:
- Update Memory B: confidence = 0.95 (user confirmation)
- Update Memory A: add deprecation flag, reduce confidence to 0.2
- Create episodic memory: "User confirmed Friday delivery preference on [date]"

**Technical notes**:
- Conflict detection: same entity + same attribute type + different values
- Resolution strategy: recency + confidence + user confirmation
- Don't delete old memories (audit trail), just deprecate
- Confidence boost on confirmation: +0.15 to 0.20

---

## Entity Intelligence: Linking & Disambiguation

### S2.1: Exact Entity Matching

**Context**: User refers to entity by exact name.

**Prior state:**
- DB: Customer "Delta Industries" exists
- Memory: Previous conversations about Delta Industries

**User**: "What's the current status of Delta Industries?"

**Expected behavior**:
```
System: [Exact match, high confidence]

"Delta Industries current status:

Active Work:
- WO-5024 (valve replacement): 60% complete, estimated Friday completion
- Assigned to: Alex

Invoices:
- INV-2201: $3,500 open, due Oct 30 (8 days from now)

Payment pattern: Recently shifted from early payment to on-time
Context: Expansion phase (from our July conversation)"
```

**Memory updates**:
- Create episodic memory: User queried Delta Industries status
- Reinforce entity linking: "Delta Industries" → customer_id

**Technical notes**:
- Exact string match to `domain.customers.name`
- No disambiguation needed
- Pull all related entities (WOs, invoices) via foreign keys
- Include relevant memories linked to this customer entity

---

### S2.2: Ambiguous Entity - Intelligent Clarification

**Context**: User's reference matches multiple entities.

**Prior state:**
- DB: Three customers: "Delta Industries", "Delta Corp", "DeltaTech Solutions"
- Memory: 8 conversations about Delta Industries this month, 1 about Delta Corp (3 months ago), 0 about DeltaTech

**User**: "What's the latest order for Delta?"

**Expected behavior**:
```
System: "I found three matches for 'Delta'. Based on context:

Most likely: Delta Industries
- You've discussed them 8 times this month
- Active work order in progress
- Recent invoice due in 8 days

Less likely:
- Delta Corp (last discussed 3 months ago, no current activity)
- DeltaTech Solutions (new customer, no conversation history)

Should I proceed with Delta Industries, or did you mean one of the others?"
```

**User response**: "Delta Industries"

**Expected follow-up**:
```
System: "Got it. Delta Industries' latest order is SO-2002 (valve replacement, status: approved).

For future reference, when you say 'Delta', I'll default to Delta Industries unless
you specify otherwise."
```

**Memory updates**:
- Create entity alias: "Delta" → Delta Industries (confidence 0.9)
- Create episodic memory: User confirmed Delta = Delta Industries

**Technical notes**:
- Fuzzy match finds 3 candidates
- Scoring factors:
  - Conversation frequency (8 vs 1 vs 0) = +40 points
  - Recency (this month vs 3 months) = +30 points
  - Active work (WO in progress) = +20 points
  - Total: Delta Industries = 90, Delta Corp = 30, DeltaTech = 10
- Threshold for auto-selection: 80+ AND 2x next candidate
- Delta Industries = 90, next = 30 (3x) → still ask for confirmation first time
- After confirmation, store alias for future

---

### S2.3: Fuzzy Matching with Typos

**Context**: User misspells entity name.

**Prior state:**
- DB: Customer "Kai Media"
- Memory: No previous mentions of "Kay Media"

**User**: "Open a work order for Kay Media for packaging"

**Expected behavior**:
```
System: "I think you mean 'Kai Media' (fuzzy match confidence: 92%).

Should I create a work order for Kai Media? If yes, I'll remember that
'Kay' can refer to 'Kai Media' for future convenience."
```

**User response**: "Yes"

**Expected follow-up**:
```
System: "Work order created for Kai Media:
- Description: Packaging
- Status: Queued
- SO: [linked to existing SO or prompt for new SO]

I've noted that 'Kay' refers to 'Kai Media'—I'll recognize this next time."
```

**Memory updates**:
- Create entity alias: "Kay Media" → Kai Media (confidence 0.85)
- Create semantic memory: Fuzzy match learned
- Create episodic memory: WO creation for Kai Media

**Technical notes**:
- Levenshtein distance: "Kay Media" vs "Kai Media" = 1 character
- Fuzzy match threshold: 85%+ similarity
- First occurrence: ask for confirmation
- After confirmation: store in `app.entities` as alias
- Subsequent occurrences: auto-resolve with confidence note

---

### S2.4: Cross-Entity Reference Resolution

**Context**: User asks about entity by referring to a related entity.

**Prior state:**
- DB: SO-2002 belongs to Delta Industries
- Memory: Recent discussion about SO-2002

**User**: "What's the payment status for the customer with SO-2002?"

**Expected behavior**:
```
System: [Resolves SO-2002 → Delta Industries → Invoices]

"Delta Industries (customer for SO-2002) payment status:

Current invoice:
- INV-2201: $3,500 open, due Oct 30
- Payment history: Typically pays 2 days early
- Recent pattern: Shifted to on-time payment (last 60 days)
- Assessment: Still reliable, pattern shift due to expansion phase

Need more details on this invoice or their overall payment history?"
```

**Memory updates**:
- Create episodic memory: User inquired via SO reference (shows user thinking pattern)
- Reinforce relationship understanding: SO-2002 ↔ Delta Industries

**Technical notes**:
- Entity resolution chain: SO-2002 → domain.sales_orders.customer_id → Delta Industries
- Then query: domain.invoices WHERE customer_id = Delta_Industries
- Include payment pattern analysis from historical data
- Context enrichment from memory about expansion

---

### S2.5: Multilingual Entity Recognition

**Context**: User uses non-English language but references English entity.

**Prior state:**
- DB: Customer "Kai Media"
- Memory: No Spanish aliases stored

**User**: "Recuérdame que Kai Media prefiere entregas los viernes"
(Translation: "Remind me that Kai Media prefers Friday deliveries")

**Expected behavior**:
```
System: "Noted. I've stored:
- Kai Media prefers Friday deliveries

(I detected your message in Spanish and stored the preference in English
for consistency, but I can respond in Spanish if you prefer.)"
```

**Memory updates**:
- Create semantic memory: "Kai Media prefers Friday deliveries" (stored in English)
- Create metadata: original_text="Kai Media prefiere entregas los viernes", language=es
- Entity link: Kai Media (recognized despite language)

**Technical notes**:
- Language detection: identify Spanish
- Entity extraction: "Kai Media" (proper noun, language-invariant)
- Translation: "prefiere entregas los viernes" → "prefers Friday deliveries"
- Store canonical form (English) but preserve original for audit
- Future queries in English will retrieve this memory

---

## Contextual Synthesis: Deep Understanding

### S3.1: Basic Contextual Enrichment

**Context**: User asks simple status question; system provides enriched context.

**Prior state:**
- DB: WO-5024 for Delta Industries, status=in_progress, 60% complete
- Memory: Delta is NET15, prefers ACH, expansion phase

**User**: "What's the work order status for Delta?"

**Expected behavior**:
```
System: "Work order WO-5024 for Delta Industries (valve replacement):

Current status: In progress, 60% complete
- Started: 3 days ago
- Estimated completion: Friday
- Assigned technician: Alex

Related context:
- No invoice exists yet (typically created after WO completion)
- Delta is NET15, so invoice would be due ~Nov 14 if completed Friday
- They're in expansion phase, currently paying exactly on due dates

Anything specific you need about this work order?"
```

**Memory updates**:
- Create episodic memory: User checked WO status
- Increase importance of Delta Industries memories (user showing interest)

**Technical notes**:
- Query: work_orders WHERE customer = Delta AND status != done
- Enrich with: related invoice check, payment terms memory, contextual notes
- Proactive information: what typically comes next (invoice creation)
- Timeline projection: completion date → invoice due date

---

### S3.2: Intent Understanding and Context Provision

**Context**: User asks vague question; system infers intent and provides comprehensive answer.

**Prior state:**
- DB: Multiple activities for Delta Industries
- Memory: User recently discussed invoicing concerns

**User**: "How are things with Delta?"

**Expected behavior**:
```
System: "Delta Industries overview:

Active operations:
- WO-5024: 60% complete, on track for Friday
- No blockers or delays currently

Financial:
- Invoice INV-2201: $3,500 open, due Oct 30 (8 days)
- Payment pattern: Shifted to on-time (from early)
- Assessment: Healthy, pattern shift due to expansion

Relationship health:
- 18-month customer, 100% SLA compliance
- Increasing order frequency (3 rush orders in 6 months)
- Strong communication and working relationship

Given your recent focus on invoicing, the main flag is their payment
timing shift—but this appears tied to their expansion (capital allocation),
not financial distress.

What aspect would you like to explore further?"
```

**Memory updates**:
- Create episodic memory: User asked broad status check
- Recognize pattern: "how are things" = comprehensive status request
- Learn user prefers comprehensive summaries for important customers

**Technical notes**:
- Vague query triggers comprehensive mode
- Synthesize across: operations (WOs), finance (invoices, payments), relationship (history)
- Prioritize based on recent episodic memories (user recently discussed invoicing)
- Multi-dimensional summary with assessment
- End with open-ended offer to drill down

---

### S3.3: Implicit Context from Conversation History

**Context**: User's question references previous conversation without explicit mention.

**Prior state:**
- Previous turn: Discussed Delta Industries expansion plans
- Memory: Conversation context active

**User**: "Will that affect their payment timing?"

**Expected behavior**:
```
System: [Infers "that" = expansion plans, "their" = Delta Industries]

"The expansion is likely why Delta Industries' payment timing has already
shifted from early to on-time payment. Here's the pattern:

Current observation:
- Historically: Paid 2 days early on NET15 terms
- Last 60 days: Paying exactly on due date

Why expansion causes this:
Expansion projects tie up capital in upfront costs (equipment, hiring, etc.).
Companies often shift from 'pay early' to 'use full payment terms' to preserve
cash flow during growth phases.

What I've seen in similar cases:
5 other customers showed this pattern during expansions—all returned to early
payment within 4-6 months after expansion stabilized.

Bottom line: Their payment timing shift is consistent with expansion-driven
capital allocation, not financial distress. It's actually a healthy sign they're
investing in growth.

Want me to flag if payment timing degrades further (e.g., starts going late)?"
```

**Memory updates**:
- Create episodic memory: User asked about expansion impact on payments
- Create semantic connection: expansion → payment_timing_shift (learned correlation)
- Update conversation context: still discussing Delta Industries

**Technical notes**:
- Maintain conversation context (session-level memory)
- Pronoun resolution: "that" → previous topic, "their" → previous entity
- Retrieve: payment pattern analysis, similar customer patterns
- Synthesis: explain causal mechanism (why expansion → payment shift)
- Proactive offer: monitoring suggestion

---

### S3.4: Cross-Session Context Recall

**Context**: User returns after days/weeks; system recalls and applies previous context.

**Prior state:**
- Session 1 (Oct 10): User discussed Delta's expansion, asked about payment flexibility
- Session 2 (Oct 15): User mentioned considering offering NET30 extension
- Now: Oct 22, new session

**User**: "Did we decide on Delta's payment terms?"

**Expected behavior**:
```
System: "Recalling our previous discussions about Delta Industries payment terms:

Current state:
- Official terms: NET15
- Current invoice (INV-2201): Due Oct 30 under NET15

Our conversation history:
- Oct 10: You mentioned their expansion plans and payment timing shift
- Oct 15: You considered offering NET30 extension during expansion phase

Decision status: We discussed it but no final decision was recorded.

Delta's situation now:
- Still in expansion phase
- Payment pattern: On-time (shifted from early)
- Invoice due in 8 days

Would you like to proceed with extending to NET30 for this invoice, or continue
with NET15? If you decide, I'll remember it for future reference."
```

**Memory updates**:
- Create episodic memory: User followed up on previous discussion
- If decision made, create semantic memory with new terms
- Link all related episodic memories (Oct 10, Oct 15, Oct 22)

**Technical notes**:
- Retrieve episodic memories across sessions for Delta Industries + payment terms
- Temporal ordering of conversation thread
- Identify open question/unresolved decision
- Provide current context for informed decision
- Offer to close the loop with a decision

---

### S3.5: Context-Aware Suggestions

**Context**: User asks about an action; system provides context-appropriate suggestions.

**Prior state:**
- DB: WO-5024 status just changed from in_progress → done
- Memory: Delta is NET15, user typically invoices after WO completion

**User**: "The Delta work order is done"

**Expected behavior**:
```
System: "Great! WO-5024 for Delta Industries is now complete.

Next steps based on your typical workflow:

1. Invoice creation (recommended now):
   - No invoice exists yet for SO-2002
   - Amount: $3,500 (50% completion payment per their terms)
   - Due date: ~Nov 14 (NET15 from today)
   - Want me to draft INV-2202?

2. Quality check:
   - Technician: Alex
   - Duration: 5 days (within normal range for valve replacements)
   - Any issues to note before invoicing?

3. Customer notification:
   - Delta appreciates proactive communication
   - Should I draft a completion notification email?

What would you like to tackle first?"
```

**Memory updates**:
- Create episodic memory: WO-5024 completed
- Reinforce procedural memory: User workflow = WO done → invoice creation
- Update Delta customer timeline with completion

**Technical notes**:
- Trigger: WO status change to "done"
- Check for existing invoice (none found)
- Retrieve payment terms from memory (NET15)
- Recall learned workflow pattern
- Provide multi-option next steps (invoice, quality, communication)
- Action-oriented: offer to execute suggestions

---

## Pattern Recognition: Insight Discovery

**SECTION SCOPE: 🟡 STRETCH** - These scenarios demonstrate LLM-powered pattern analysis. Not required for core project, but achievable by providing rich historical context to GPT-4 for analysis.

### S4.1: Single-Entity Pattern Detection 🟡 STRETCH

**Context**: LLM analyzes assembled historical data to identify a pattern in one customer's behavior.

**Prior state:**
- DB: Delta Industries has placed 3 orders in past 6 months, all marked as "rush"
- Memory: Previous rush orders: June 5, August 12, October 3

**User**: "Review Delta Industries' recent activity"

**Expected behavior**:
```
System: [Queries order history + retrieves memories → LLM analyzes patterns]

"Delta Industries recent activity analysis:

Order pattern (past 6 months):
- 3 rush orders: June 5, Aug 12, Oct 3
- Increasing frequency: 68 days → 52 days between orders
- All rush status (higher margin: 32% vs standard 22%)

Pattern significance:
Looking at historical data across customers, those who place 3+ rush orders
within 6 months often convert to retainer agreements. Delta is showing similar signals:
✓ Increasing frequency (demand is growing)
✓ Consistent rush work (urgent, high-value needs)
✓ Strong payment history (reliable financial partner)
✓ 18-month relationship (past trial phase)

Strategic implication:
This is likely the optimal moment to discuss a retainer structure. They're
feeling the pain of unpredictable scheduling + costs, and you're managing
capacity challenges from rush requests.

Want me to prepare a retainer proposal outline based on their pattern?"
```

**Memory updates**:
- Create pattern memory: "Delta Industries shows retainer conversion signals"
- Create semantic memory: "3+ rush orders in 6 months = retainer opportunity signal"
- Tag as strategic opportunity for follow-up

**Technical notes**:
- Query: Count rush orders for Delta in last 6 months
- Assemble context: Order history, payment data, relationship metrics
- LLM analysis: GPT-4 analyzes patterns across historical data
- LLM synthesis: Multi-factor assessment + strategic recommendation
- Note: No pre-computed pattern cache needed - LLM discovers patterns from data

---

## Temporal Intelligence: Time-Based Analysis

**SECTION SCOPE: 🟡 STRETCH** - LLM-powered temporal analysis. Not required for core project, but achievable by querying time-series data and letting GPT-4 analyze trends.

### S5.1: Trend Detection 🟡 STRETCH

**Context**: LLM analyzes time-series data to identify changing patterns over time.

**Prior state:**
- DB: 6 months of payment timing data for Delta Industries
- Months 1-4: Avg 2.5 days early
- Months 5-6: Avg 0.2 days early (essentially on-time)

**User**: "Has Delta's payment behavior changed?"

**Expected behavior**:
```
System: [Queries payment history by month + retrieves memories → LLM analyzes trend]

"Yes—Delta Industries' payment timing has shifted significantly:

Trend analysis (6-month view):

Months 1-4 (Feb-May):
- Average: 2.5 days early
- Range: 1-4 days early
- Pattern: Consistently early, reliable

Months 5-6 (Jun-Jul):
- Average: 0.2 days early (essentially on-time)
- Range: 0-1 days early
- Pattern: Shifted to exact payment terms

Trend significance:
- This is a 2.3-day shift (statistically significant)
- Occurred gradually over 2 months (not sudden crisis)
- No late payments (still reliable)

Context from memory:
In our July conversation, you mentioned Delta is in expansion phase. This
explains the pattern—they're using full NET15 terms to preserve capital
during growth.

Comparison to similar patterns:
5 customers showed similar shifts during expansion phases:
- All returned to early payment within 4-6 months
- None developed late payment issues
- Signal was capital allocation, not distress

Assessment: HEALTHY shift, consistent with expansion. Not a concern unless
it degrades to late payments.

Want me to alert you if payment timing shifts further (e.g., starts going late)?"
```

**Memory updates**:
- Create temporal pattern: "Delta Industries payment timing trend shift detected"
- Create semantic memory: "Payment shift = expansion-related capital allocation"
- Set monitoring flag for further degradation

**Technical notes**:
- Query: Group payments by month, calculate average timing
- Assemble context: Time-series data + conversation memories
- LLM analysis: GPT-4 detects trend, assesses significance, explains cause
- LLM synthesis: Correlates with episodic memory (expansion mention)
- LLM comparison: Analyzes against similar historical patterns
- Note: No pre-computed pattern baselines needed - LLM analyzes raw data

---

## Cross-Object Reasoning: Entity Relationships

### S6.1: Simple Relationship Traversal

**Context**: User asks about one entity; answer requires traversing to related entities.

**Prior state:**
- DB: SO-2002 → WO-5024 → no invoice yet
- Memory: Delta is NET15

**User**: "Can we invoice for SO-2002?"

**Expected behavior**:
```
System: [Traces: SO-2002 → WO-5024 → status check → invoice check]

"SO-2002 (valve replacement for Delta Industries) invoice status:

Related work order: WO-5024
- Status: In progress (60% complete)
- Expected completion: Friday

Invoice status: No invoice exists yet

Recommendation:
Standard workflow is to invoice after WO completion. Based on Friday completion
estimate and Delta's NET15 terms:
- Invoice creation: Friday/Monday
- Due date: ~Nov 14
- Expected payment: ~Nov 12 (they typically pay 2 days early)

Want me to draft the invoice now (pending completion) or wait until Friday?"
```

**Memory updates**:
- Create episodic memory: User asked about invoicing for SO-2002
- Reinforce procedural knowledge: invoice after WO completion

**Technical notes**:
- Relationship chain: SO → WO → Invoice
- SQL joins: sales_orders → work_orders → invoices
- Status checking: WO not done → invoice shouldn't exist yet
- Business logic: Apply learned workflow (invoice after completion)
- Forward projection: Estimate invoice date and payment date

---

### S6.2: Multi-Hop Relationship Reasoning

**Context**: Answer requires traversing multiple relationships.

**Prior state:**
- DB: Complex relationship chain with multiple entities

**User**: "Which technician has been handling work for our entertainment customers?"

**Expected behavior**:
```
System: [Traces: Entertainment industry → Customers → SOs → WOs → Technicians]

"Technician assignment analysis for entertainment segment:

Entertainment customers (5 active):
- Kai Media (Album fulfillment work)
- Melody Records (Packaging and shipping)
- Sound Stage Inc (Equipment setup)
- [2 others]

Work order analysis (past 6 months):

Alex: 8 work orders (62% of entertainment work)
- Primary customers: Kai Media (5 WOs), Melody Records (3 WOs)
- Specialization: Album fulfillment, packaging operations
- Performance: 100% on-time completion
- Note: Seems to be your go-to for entertainment sector

Jordan: 3 work orders (23%)
- Customers: Sound Stage Inc (2 WOs), Kai Media (1 WO)
- Specialization: Equipment and technical setup
- Performance: 1 delay (external parts issue)

Taylor: 2 work orders (15%)
- Customers: Mixed (not entertainment-specific)
- Coverage: Backup when Alex unavailable

Pattern: Alex has become the de facto entertainment specialist. Entertainment
customers seem to value consistency (Kai Media specifically requests Alex
in 4 of 5 conversations).

Recommendation: Consider formalizing Alex as entertainment segment lead given
the specialization that's emerged.

Want details on any specific customer-technician pairing?"
```

**Memory updates**:
- Create pattern memory: "Alex specializes in entertainment segment work"
- Create semantic memory: "Kai Media prefers technician Alex"
- Suggest procedural rule: "Assign Alex to entertainment customers by default"

**Technical notes**:
- Multi-join query: customers → sales_orders → work_orders → (technician field)
- Filter: customers.industry = 'Entertainment'
- Aggregate: COUNT by technician
- Pattern discovery: Alex concentration in entertainment segment
- Context addition: Preference from conversation memory
- Strategic suggestion: Formalize emergent pattern

---

### S6.3: Relationship-Based Anomaly Detection

**Context**: Detect unusual pattern in related entities.

**Prior state:**
- DB: Epsilon Corp has 5 open work orders but no corresponding invoices

**User**: "Why do we have so much unbilled work?"

**Expected behavior**:
```
System: "Unbilled work analysis—anomaly detected:

Current unbilled work orders:

Epsilon Corp: 5 completed WOs, no invoices (UNUSUAL)
- WO-4821: Completed Sep 15 (28 days ago)
- WO-4892: Completed Sep 22 (21 days ago)
- WO-4903: Completed Sep 28 (15 days ago)
- WO-4917: Completed Oct 5 (8 days ago)
- WO-4928: Completed Oct 10 (3 days ago)

Total unbilled amount: ~$8,400 (estimated based on similar WOs)

Why this is unusual:
Your typical workflow: Invoice within 2-3 days of WO completion
Epsilon Corp pattern: 28 days since oldest completed WO, still no invoice

Possible explanations:
1. Intentional delay (did you discuss payment flexibility with Epsilon?)
2. Consolidated billing request (invoice monthly instead of per-WO?)
3. Process gap (WO completions weren't flagged for invoicing)

Checking memory:
- May conversation: Epsilon had supplier issues
- Aug 28: Small test order placed
- Recent: 8-week order gap, then sudden return with 5 WOs

Hypothesis: After their 8-week gap, Epsilon placed multiple quick orders.
The rapid sequence may have caused invoicing to lag behind completions.

Recommended action:
1. Immediate: Create consolidated invoice for all 5 completed WOs ($8,400)
2. Follow-up: Check if Epsilon prefers consolidated monthly billing going forward
3. Process: Review why 5 completions didn't trigger invoice workflow

Want me to draft a consolidated invoice for all 5 work orders?"
```

**Memory updates**:
- Create anomaly flag: "Epsilon Corp has unusual unbilled work"
- Create episodic memory: User identified invoicing gap
- Learn potential pattern: Multiple rapid WOs → consolidated invoice preference?

**Technical notes**:
- Relationship query: work_orders WHERE status='done' LEFT JOIN invoices ON so_id
- Identify: Completed WOs with no corresponding invoice
- Time-based severity: Days since completion
- Aggregate: Total unbilled amount
- Pattern comparison: This vs typical workflow
- Hypothesis generation: Why anomaly exists
- Context retrieval: Related episodic memories for explanation

---

## Strategic Decision Support: Multi-Dimensional Analysis

**SECTION SCOPE: 🟡 STRETCH** - LLM-powered decision support. Not required for core project, but achievable by assembling comprehensive context and letting GPT-4 perform multi-dimensional analysis.

### S7.1: Should We Take This Action? (Yes/No Decision) 🟡 STRETCH

**Context**: User asks for recommendation; LLM performs multi-dimensional analysis.

**Prior state:**
- DB: Delta Industries relationship data
- Memory: Expansion context, payment history, relationship quality

**User**: "Should we offer Delta Industries extended payment terms (NET30 instead of NET15)?"

**Expected behavior**:
```
System: [Retrieves memories + queries DB (payment history, orders, relationship) → LLM analyzes]

"Decision analysis: Extend Delta Industries to NET30

Let me analyze this from multiple angles:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINANCIAL HEALTH ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Positive signals (✓):
✓ 18-month relationship, zero late payments
✓ $127K annual revenue, growing 40% YoY
✓ 100% payment history (never missed or late)

Caution signals (⚠):
⚠ Payment timing shifted: 2 days early → exactly on-time (past 60 days)

Context assessment:
You mentioned expansion plans in July. Payment slowdown + order frequency
INCREASE = capital allocation (healthy), not financial distress.

Financial health: Strong (with explicable caution signal)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RELATIONSHIP VALUE ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Revenue contribution: $127K/year (2nd largest customer)
Margin quality: 32% on rush work vs 22% standard (high-value)
Growth trajectory: 3 rush orders in 6 months (accelerating)
Retention value: 18-month relationship, strong SLA compliance

Relationship strength: STRONG
Strategic importance: HIGH (growth customer, premium margins)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RISK ASSESSMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Risk of non-payment: LOW
- Perfect payment history
- Order frequency increasing (demand strong)
- Payment shift explained by expansion (temporary capital needs)

Risk vs reward:
- Extending NET15 → NET30 = 15 extra days float on ~$3,500/invoice
- Cash impact: ~$3,500 outstanding for 15 extra days = minimal
- Relationship benefit: Signals partnership during their growth phase

Historical precedent:
5 similar customers offered extended terms during expansion:
- 4 returned to shorter terms after 6 months (expansion stabilized)
- 1 maintained NET30 (mutual preference)
- 0 developed payment issues

Risk assessment: LOW

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGIC CONSIDERATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Timing: They're in expansion phase NOW (permits just cleared)
Opportunity: Offering flexibility BEFORE they ask shows partnership
Positioning: "Supporting your growth" vs reactive "dealing with problem"
Competitive advantage: Strengthens relationship during vulnerable period

Alternative consideration:
Instead of extending terms, consider proposing a RETAINER structure:
- They get: Budget predictability during expansion
- You get: Locked revenue + better planning than extended terms
- Win-win: Addresses their capital needs differently

Strategic value of flexibility offer: HIGH

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

YES, offer extended terms, but with structure:

Suggested approach:
- Offer: NET30 (15-day extension)
- Duration: 6 months with automatic review
- Framing: "Supporting your expansion phase"
- Condition: Maintain current order frequency (quality signal)
- Review trigger: If payment timing degrades further

Confidence in recommendation: HIGH

Alternative to consider:
Retainer structure might be MORE valuable than term extension:
- Addresses their budget predictability need
- Locks in your revenue during their growth
- Positions you as strategic partner, not just vendor
- Opens door to deeper relationship

Next step:
Would you like me to:
1. Draft a NET30 extension proposal
2. Compare NET30 extension vs retainer structure in detail
3. Prepare talking points for the conversation"
```

**Memory updates**:
- Create episodic memory: User considered extended terms for Delta
- Create semantic memory: Decision analysis performed (for future reference)
- If decision made: Store the outcome and reasoning

**Technical notes**:
- Assemble context: Revenue, margin, payment history (from DB) + memories (expansion context)
- LLM analysis: GPT-4 performs multi-dimensional synthesis
- LLM capabilities: Financial assessment, risk analysis, alternative generation
- LLM reasoning: Transparent explanation of recommendation logic
- No pre-computed decision engine needed - LLM does the analysis
- Alternative insight: LLM generates creative options (retainer vs terms)

---

## Workflow Learning: Procedural Intelligence

**SECTION SCOPE: 🟡 STRETCH** - LLM-powered workflow recognition. Not required for core project, but achievable by analyzing conversation history to recognize user patterns.

### S8.1: Implicit Workflow Detection 🟡 STRETCH

**Context**: LLM analyzes conversation history and notices user follows consistent pattern.

**Prior state:**
- User has drafted invoices within 1-2 days of WO completion 8 times in past month
- No explicit workflow rule taught

**User**: "WO-5024 for Delta is complete"

**Expected behavior**:
```
System: [Retrieves episodic memories about WO completions → LLM analyzes]

"WO-5024 for Delta Industries marked complete.

Looking at our conversation history, I've noticed a pattern in how you work:
Whenever a WO completes, you typically ask me to draft an invoice within
the same day or next day. This has happened 8 times in the past month.

Since WO-5024 is complete and no invoice exists yet for SO-2002:

Would you like me to draft invoice INV-2202 now?
- Amount: $3,500 (50% completion per Delta's payment structure)
- Terms: NET15
- Due date: ~Nov 14

Also: Should I start automatically suggesting invoice creation when WOs
complete? This could save you a step every time.

What would look like:
'WO-5024 complete. No invoice exists for SO-2002. Should I draft INV-2202
for $3,500 (NET15, due ~Nov 14)?'

Want me to start doing this?"
```

**User response**: "Yes, do that automatically"

**Expected follow-up**:
```
System: "Perfect. I've learned this workflow:

Trigger: Work order status → 'done'
Action: Check for existing invoice
If no invoice: Suggest drafting one with terms and amount
If invoice exists: Note completion and timeline

I'll apply this to all future WO completions.

For now, should I draft INV-2202 for this completed WO?"
```

**Memory updates**:
- Create procedural memory: `kind=procedural, text="When WO status=done, check for invoice and suggest drafting if none exists", confidence=0.90`
- Create episodic memory: User confirmed workflow automation preference
- Create trigger rule: WO.status change to 'done' → execute invoice check workflow

**Technical notes**:
- LLM analysis: Reviews conversation history for repeated sequences
- Pattern recognition: LLM identifies "WO done → invoice draft" pattern
- Confidence: Based on frequency (8 instances) and consistency
- User control: Always ask before automating behavior
- Storage: Can store pattern as semantic memory for future reference
- Note: No separate workflow engine needed - LLM recognizes patterns

---

### S8.2: Explicit Workflow Teaching 🟡 STRETCH

**Context**: User explicitly teaches system a workflow preference to remember.

**Prior state:**
- No existing workflow for customer communication after WO completion

**User**: "Whenever a work order for an entertainment customer is completed, remind me to send a completion notification email to the customer"

**Expected behavior**:
```
System: "Workflow rule created:

Trigger: Work order completion
Condition: Customer industry = 'Entertainment'
Action: Remind user to send completion notification

I'll apply this to entertainment customers:
- Kai Media
- Melody Records
- Sound Stage Inc
- [2 others]

Examples of when this will trigger:
- ✓ WO for Kai Media album fulfillment → complete → remind to notify
- ✗ WO for Delta Industries valve replacement → complete → no reminder (industrial, not entertainment)

Want me to also draft email templates for these notifications, or just remind you?"
```

**User response**: "Just remind me for now"

**Expected follow-up**:
```
System: "Got it. Workflow confirmed:

When entertainment customer WO completes → remind to send notification

I'll watch for this pattern. If I notice you don't send notifications for
a while, I'll check if you still want these reminders.

Saved for future reference."
```

**Memory updates**:
- Create procedural memory: `kind=procedural, text="Entertainment customer WO completion triggers customer notification reminder", confidence=0.95`
- Create conditional rule: IF customer.industry='Entertainment' AND WO.status='done' THEN suggest customer notification
- Link to entities: Tag all entertainment customers for this rule

**Technical notes**:
- Store as semantic memory: User preference with conditions
- LLM parsing: Extract trigger + condition from natural language
- Entity resolution: Identify which customers match (industry = entertainment)
- Example generation: LLM provides examples of when rule applies
- Retrieval: Future queries retrieve this preference and LLM applies it
- Note: No workflow execution engine needed - stored as memory, applied by LLM

---

## Confidence & Uncertainty: Transparent Reasoning

### S9.1: High Confidence Response

**Context**: System has strong evidence for answer.

**Prior state:**
- Memory: "Delta Industries NET15 terms" (explicit statement, reinforced 5 times over 3 months)

**User**: "What are Delta's payment terms?"

**Expected behavior**:
```
System: "Delta Industries operates on NET15 payment terms.

Confidence: Very high
- Source: Your explicit statement on July 12
- Reinforced: 5 invoice conversations since then
- Consistency: No conflicting information

Historical pattern:
They typically pay 2 days early, though that shifted to on-time payment
in the past 60 days (expansion-related capital allocation).

Current terms: NET15 (well-established)"
```

**Memory updates**:
- Reinforce semantic memory: confidence += 0.02 (retrieval reinforces)
- Create episodic memory: User asked about payment terms (interest signal)

**Technical notes**:
- Confidence calculation: Base (0.95) + reinforcement_count × 0.02
- Explicit confidence communication: "Very high" with reasoning
- Source attribution: Where knowledge came from
- Pattern addition: Related context (payment timing) even when not asked

---

### S9.2: Medium Confidence Response

**Context**: System has information but with lower certainty.

**Prior state:**
- Memory: "Epsilon Corp prefers email contact for non-urgent matters" (mentioned once, 60 days ago, not reinforced)

**User**: "How should I reach Epsilon Corp about the upcoming work order?"

**Expected behavior**:
```
System: "For Epsilon Corp contact:

Primary contact: Robert Chen (Operations Director)

Communication preference: Moderate confidence
I have a note from August 20 that they prefer email for non-urgent matters,
but this was mentioned only once and hasn't come up since.

Confidence level: Medium (6/10)
- Source: Single mention (Aug 20)
- Age: 60 days old
- Reinforcement: Not confirmed since

For an upcoming work order (somewhat time-sensitive):

Recommendation:
- Try email first (based on preference note)
- Include phone as follow-up option (if urgent response needed)
- If this contact goes well, I'll boost confidence in the email preference

Want me to confirm whether email is still their preferred method, or just
proceed based on what we have?"
```

**Memory updates**:
- Flag semantic memory for validation (age + low reinforcement)
- Create episodic memory: User asked about contact preference (opportunity to update)
- After contact occurs: Ask user if email worked (reinforcement or correction)

**Technical notes**:
- Confidence factors: Recency (0.7), reinforcement_count (0.6), source reliability (0.8)
- Aggregate: (0.7 + 0.6 + 0.8) / 3 = 0.70 (medium)
- Explicit qualification: State confidence level and reasoning
- Actionable recommendation despite uncertainty
- Offer to validate and update based on user feedback

---

### S9.3: Low Confidence - Acknowledge Uncertainty

**Context**: System has insufficient information to answer confidently.

**Prior state:**
- Memory: No information about preferred contact time for Gamma Ltd

**User**: "What time of day should I call Gamma Ltd?"

**Expected behavior**:
```
System: "I don't have reliable information about Gamma Ltd's preferred contact times.

What I do know:
- Primary contact: Jessica Martinez (Procurement)
- Communication: Email mentioned in initial onboarding
- Preferred method: Unknown for phone calls

Confidence: Low (2/10)
- No timing preferences discussed in our conversations
- Insufficient history to infer patterns

Recommendation:
Since Gamma is new (Month 2), standard business practices:
- Try mid-morning (9-11 AM) or mid-afternoon (2-4 PM)
- Avoid early morning, lunch, or end-of-day
- If you reach voicemail, try different time next day

After this call: Want me to remember when they're most responsive?
I can learn their optimal contact windows over time.

Should I note anything specific about contact timing preferences after
you connect with them?"
```

**Memory updates**:
- Create episodic memory: User asked about contact timing (interest in this information)
- Flag for learning: After call, prompt user to share when contact was successful
- Create placeholder: Gamma Ltd contact timing = unknown (explicit knowledge gap)

**Technical notes**:
- Honest uncertainty: Confidence 2/10, explicit acknowledgment
- Provide what IS known: Primary contact, general communication preferences
- Reasonable default suggestion: Based on general business norms
- Learning offer: Gather information for future
- Don't make up information when uncertain

---

### S9.4: Conflicting Information - Surface and Resolve

**Context**: System has contradictory memories and needs clarification.

**Prior state:**
- Memory A: "Kai Media prefers Thursday deliveries" (June 15, confidence 0.75)
- Memory B: "Kai Media prefers Friday deliveries" (Sept 3, confidence 0.80)

**User**: "Schedule a delivery for Kai Media"

**Expected behavior**:
```
System: "I have conflicting information about Kai Media's delivery preference
and need your help resolving it:

Conflict detected:
- Earlier preference (June 15): Thursday deliveries
  Source: Your statement during scheduling conversation
  Confidence: 0.75

- Recent preference (Sept 3): Friday deliveries
  Source: Your statement about their accounting week alignment
  Confidence: 0.80

Analysis:
The more recent mention (Friday) has slightly higher confidence and
includes reasoning (accounting week alignment), which suggests it might
be the current preference.

However, both were stated explicitly, so I want to confirm rather than assume.

Which is current?
1. Friday deliveries (recent mention, accounting alignment reasoning)
2. Thursday deliveries (earlier preference, possibly outdated)
3. Something else (neither is correct, different preference now)

Once confirmed, I'll:
- Update the preference with high confidence
- Mark the outdated one for deprecation
- Remember this is the verified current preference"
```

**User response**: "Friday is correct. Their accounting week changed, that's why."

**Expected follow-up**:
```
System: "Perfect, thank you for clarifying.

Updated memory:
- Current preference: Friday deliveries (confidence: 0.95)
- Reasoning: Aligns with their accounting week
- Verified: Today

Deprecated:
- Thursday preference marked as outdated (confidence lowered to 0.2)
- Kept for historical record but won't be used

Future deliveries for Kai Media will be scheduled for Friday unless you
specify otherwise.

Delivery for this request: Scheduling for Friday, Oct 27. Confirm?"
```

**Memory updates**:
- Update Memory B: confidence = 0.95, add validation flag, add reasoning
- Update Memory A: confidence = 0.2, add deprecated flag, keep for audit
- Create episodic memory: Conflict resolved, Friday confirmed
- Create semantic memory: "Kai Media accounting week aligns with Friday deliveries" (context)

**Technical notes**:
- Conflict detection: Same entity + same attribute + different values
- Surface both memories with source attribution
- Present analysis (which seems more likely and why)
- Request explicit resolution (don't guess)
- After confirmation: High confidence boost (0.95)
- Deprecate, don't delete: Audit trail preserved
- Add reasoning: Why preference exists (accounting alignment)

---

### S9.5: Stale Information - Proactive Validation

**Context**: System detects information is old and might be outdated.

**Prior state:**
- Memory: "Kai Media prefers Friday deliveries" (stored 180 days ago, not reinforced in past 90 days)
- Confidence decay: 0.95 → 0.60 due to age without reinforcement

**User**: "Schedule a delivery for Kai Media next week"

**Expected behavior**:
```
System: "I have a Friday delivery preference for Kai Media on record, but
I want to verify it's still current before scheduling:

Memory status:
- Preference: Friday deliveries
- Source: Your statement on April 15 (180 days ago)
- Last reinforced: July 10 (90 days ago)
- Current confidence: Medium (0.60)

Why I'm checking:
Preferences older than 120 days without reinforcement might have changed.
It's been 6 months—enough time for business processes to shift.

Options:
1. Use Friday (and I'll boost confidence if correct)
2. Different day needed (and I'll update preference)
3. Confirm Friday is still accurate (resets confidence to high)

Which should I do?"
```

**User response**: "Friday is still correct"

**Expected follow-up**:
```
System: "Great! Delivery scheduled for Friday, Oct 27.

Memory updated:
- Preference: Friday deliveries (verified)
- Last validated: Today
- Confidence: Restored to 0.90 (high)
- Next freshness check: April 2024 (~6 months)

Since this preference is now freshly validated, I won't ask again for
at least 6 months unless I see signals that it might have changed.

Scheduled delivery details:
- Customer: Kai Media
- Day: Friday, Oct 27
- Related: [SO if applicable]"
```

**Memory updates**:
- Update semantic memory: confidence = 0.90, last_validated = today
- Reset decay timer: next_validation = +180 days
- Create episodic memory: User revalidated Friday preference
- Reinforcement: Increases future decay resistance

**Technical notes**:
- Staleness detection: Age (180 days) + no recent reinforcement (90 days)
- Confidence decay function: base × (1 - days_since / decay_window)
- Proactive validation: Ask before using old information
- Confidence restoration: Validation brings confidence back to 0.90
- Adaptive freshness: Validated facts decay slower
- Next check: 6 months (or if conflicting information appears)

---

## Conversation Continuity: Multi-Turn Intelligence

### S10.1: Simple Pronoun Resolution

**Context**: User refers to entity from previous turn using pronouns.

**Prior state:**
- Turn 1: Discussed Delta Industries
- Conversation context: Delta Industries active

**Turn 1 User**: "What's Delta Industries' current status?"

**Turn 1 System**: "Delta Industries overview: [comprehensive status]"

**Turn 2 User**: "When will their work order be done?"

**Expected behavior**:
```
System: [Resolves "their" → Delta Industries from context]

"Delta Industries' work order (WO-5024) completion:

Current status: 60% complete
Estimated completion: Friday, Oct 27

[Rest of detailed response about Delta's WO]"
```

**Memory updates**:
- Maintain conversation context: Delta Industries is active referent
- Create episodic memory: Multi-turn conversation about Delta

**Technical notes**:
- Conversation context tracking: Last mentioned entity = Delta Industries
- Pronoun resolution: "their" → Delta Industries (high confidence)
- Context carries forward: No need to re-specify customer
- Context window: Typically lasts for session or until new entity introduced

---

### S10.2: Multi-Turn Context Building

**Context**: User explores topic across multiple turns; system builds deeper understanding.

**Turn 1 User**: "What's our largest customer by revenue?"

**Turn 1 System**: "Delta Industries at $127K YTD, followed by Apex Corp at $108K..."

**Turn 2 User**: "Tell me more about Delta"

**Expected Turn 2 behavior**:
```
System: [Understands "Delta" = Delta Industries from Turn 1 context]

"Delta Industries deep dive:

Revenue: $127K YTD (mentioned as your largest customer)
[Comprehensive customer analysis]

Want to explore any specific aspect?"
```

**Turn 3 User**: "What would a retainer look like?"

**Expected Turn 3 behavior**:
```
System: [Understands context: retainer FOR Delta Industries]

"Retainer structure for Delta Industries:

[Detailed retainer analysis specific to Delta's pattern]"
```

**Turn 4 User**: "Compare that to just extending their payment terms"

**Expected Turn 4 behavior**:
```
System: [Context chain: Delta Industries + retainer + payment terms]

"Comparative analysis: Retainer vs Extended Payment Terms for Delta Industries

[Side-by-side comparison]"
```

**Memory updates**:
- Maintain conversation thread: Delta Industries → retainer → payment terms
- Create episodic memory: Deep exploration of Delta strategic options
- Learn user interest: Delta is high-priority customer (depth of inquiry)

**Technical notes**:
- Context stacking: Each turn adds to conversation context
- Implicit referents: "that" (retainer), "their" (Delta's), no need for repetition
- Topic coherence: System maintains topic (Delta strategy) across 4 turns
- Context enrichment: Each turn deepens understanding of user's exploration

---

### S10.3: Context Switch Detection

**Context**: User shifts topic; system recognizes and adapts.

**Prior context**: Multi-turn conversation about Delta Industries

**Turn N User**: "What about Epsilon Corp's orders?"

**Expected behavior**:
```
System: [Detects topic shift: Delta → Epsilon Corp]

"Switching to Epsilon Corp:

[Epsilon Corp order analysis]

(Note: We were discussing Delta Industries' retainer options. Want to
return to that after we cover Epsilon, or should I consider that conversation
closed?)"
```

**Memory updates**:
- Create episodic memory: Conversation about Delta (turns 1-N)
- Update conversation context: Active entity = Epsilon Corp
- Store conversation thread state: Delta discussion paused

**Technical notes**:
- Topic shift detection: New entity mentioned explicitly
- Context switch acknowledgment: Recognize shift
- Conversation thread management: Offer to return to previous topic
- Multiple conversation threads: Can maintain paused conversations

---

## Implementation Priority Guide

Legend:
- ✅ **CORE PROJECT**: Directly specified in project description scenarios (1-18)
- 🟢 **ADJACENT**: Natural extension, same infrastructure, aligned with project spirit
- 🟡 **STRETCH**: More complex, requires additional capabilities beyond core
- 🔴 **OUT OF SCOPE**: Significantly beyond project requirements, advanced intelligence

---

### Phase 1: Foundation (Must Have for Project)

**✅ CORE PROJECT - These directly map to the 18 scenarios:**

- **S1.1: Explicit Fact Learning** ✅
  - Maps to: Scenario 4 (NET terms learning)
  - Project requirement: Store semantic memory from conversation

- **S1.2: Episodic Memory Creation** ✅
  - Maps to: Scenarios 1, 5, 6 (invoice queries, task queries)
  - Project requirement: Store salient events per session

- **S1.3: Memory Consolidation** ✅
  - Maps to: Scenario 14 (session window consolidation)
  - Project requirement: Write/update memory_summaries for user

- **S1.4: Memory Recall in Context** ✅
  - Maps to: Scenario 1 (combine invoice data + preference memory)
  - Project requirement: Retrieve memories + augment with DB facts

- **S1.5: Conflict Detection and Resolution** ✅
  - Maps to: Scenario 7 (conflicting delivery preferences)
  - Project requirement: Consolidation picks most recent/reinforced value

- **S2.1: Exact Entity Matching** ✅
  - Maps to: Scenario 9 (cold-start DB grounding)
  - Project requirement: Deterministic linking by exact names/IDs

- **S2.2: Ambiguous Entity Disambiguation** ✅
  - Maps to: Scenario 3 (Kai Media vs Kai Media Europe)
  - Project requirement: Single-step clarification with confidence scoring

- **S2.3: Fuzzy Matching with Typos** ✅
  - Maps to: Scenario 12 (Kay Media → Kai Media)
  - Project requirement: Fuzzy match with threshold, store alias

- **S2.5: Multilingual Entity Recognition** ✅
  - Maps to: Scenario 8 (Spanish input, English storage)
  - Project requirement: Canonical form storage with alias mapping

- **S3.1: Basic Contextual Enrichment** ✅
  - Maps to: Scenarios 1, 2, 5, 6, 11 (combine DB + memory in responses)
  - Project requirement: Augment domain facts with memory snippets

- **S6.1: Simple Relationship Traversal** ✅
  - Maps to: Scenario 11 (SO → WO → Invoice chain reasoning)
  - Project requirement: Use chain to recommend invoice generation

- **S9.1: High Confidence Response** ✅
  - Maps to: Scenario 15 (explainability with sources)
  - Project requirement: Return memory IDs, similarity scores, sources

- **S9.4: Conflicting Information** ✅
  - Maps to: Scenario 7 (conflicting memories, consolidation)
  - Project requirement: Cite confidence, offer to confirm

- **S9.5: Stale Information Validation** ✅
  - Maps to: Scenario 10 (active recall for 90+ day preferences)
  - Project requirement: Validate before use, reset decay if confirmed

- **S10.1: Simple Pronoun Resolution** 🟢
  - Maps to: Implicit in conversation flow
  - Project requirement: Maintain session context for natural dialogue

---

### Phase 2: Natural Extensions (Adjacent to Project)

**🟢 ADJACENT - Same infrastructure, aligned with project spirit:**

- **S2.4: Cross-Entity Reference Resolution** 🟢
  - Extension of: Entity linking (S2.1-S2.3)
  - Why adjacent: Uses same entity linking logic, just follows FK relationships
  - Complexity: LOW (SQL joins + entity resolution)

- **S3.2: Intent Understanding** 🟢
  - Extension of: Contextual enrichment (S3.1)
  - Why adjacent: Better prompt engineering + retrieval ranking
  - Complexity: MEDIUM (better LLM prompting)

- **S3.3: Implicit Context from Conversation** 🟢
  - Extension of: Memory recall (S1.4)
  - Why adjacent: Uses episodic memory to understand "that" and "their"
  - Complexity: LOW (session-level context tracking)

- **S3.4: Cross-Session Context Recall** 🟢
  - Extension of: Consolidation (S1.3)
  - Why adjacent: Retrieves episodic memories across sessions (already stored)
  - Complexity: LOW (temporal querying of existing memories)

- **S6.2: Multi-Hop Relationship Reasoning** 🟢
  - Extension of: Cross-object reasoning (S6.1)
  - Why adjacent: Multiple SQL joins instead of one
  - Complexity: MEDIUM (more complex queries, but same approach)

- **S9.2: Medium Confidence Response** 🟢
  - Extension of: Confidence scoring (S9.1)
  - Why adjacent: Same confidence calculation, different threshold
  - Complexity: LOW (already calculating confidence)

- **S9.3: Low Confidence - Acknowledge Uncertainty** 🟢
  - Extension of: Confidence scoring (S9.1)
  - Why adjacent: Honest communication when confidence < threshold
  - Complexity: LOW (threshold-based response style)

- **S10.2: Multi-Turn Context Building** 🟢
  - Extension of: Conversation continuity (S10.1)
  - Why adjacent: Session-level context maintenance (conversation stack)
  - Complexity: MEDIUM (track conversation thread through turns)

- **S10.3: Context Switch Detection** 🟢
  - Extension of: Multi-turn context (S10.2)
  - Why adjacent: Detect new entity mention, update context
  - Complexity: LOW (entity mention detection)

---

### Phase 3: Advanced Intelligence (Stretch Goals)

**🟡 STRETCH - Requires additional capabilities, more complex:**

- **S4.1: Single-Entity Pattern Detection** 🟡
  - Why stretch: Requires statistical analysis of order history
  - Complexity: HIGH (pattern detection algorithm, confidence scoring)
  - New capability: Historical pattern analysis, conversion prediction

- **S5.1: Trend Detection** 🟡
  - Why stretch: Time-series analysis, statistical significance testing
  - Complexity: HIGH (temporal aggregation, trend algorithms)
  - New capability: Detect shifts over time, classify as significant

- **S6.3: Relationship-Based Anomaly Detection** 🟡
  - Why stretch: Pattern baseline + deviation detection
  - Complexity: MEDIUM-HIGH (requires learned normal patterns)
  - New capability: Detect unusual relationship states (5 unbilled WOs)

- **S7.1: Basic Decision Support** 🟡
  - Why stretch: Multi-dimensional synthesis framework
  - Complexity: HIGH (complex prompt engineering, multi-factor analysis)
  - New capability: Strategic recommendations with transparent reasoning

- **S8.1: Implicit Workflow Detection** 🟡
  - Why stretch: Behavioral pattern recognition across sessions
  - Complexity: HIGH (sequence mining, pattern frequency analysis)
  - New capability: Learn procedural workflows from behavior

- **S8.2: Explicit Workflow Teaching** 🟡
  - Why stretch: Workflow rule storage and execution engine
  - Complexity: MEDIUM (rule parsing, conditional logic)
  - New capability: Store and execute user-defined workflows

- **S3.5: Context-Aware Suggestions** 🟡
  - Why stretch: Requires learned workflow patterns + proactive suggestion
  - Complexity: MEDIUM-HIGH (trigger detection + learned procedures)
  - New capability: Proactive next-step suggestions based on patterns

---

---

## Recommended Implementation Approach

### For the Project Submission (Meeting Requirements):

**Focus on ✅ CORE PROJECT scenarios:**
- Implement all S1 (memory operations) ✅
- Implement S2.1-2.3, 2.5 (entity linking) ✅
- Implement S3.1 (basic enrichment) ✅
- Implement S6.1 (simple cross-object) ✅
- Implement S9.1, 9.4, 9.5 (confidence) ✅
- Implement S10.1 (basic continuity) 🟢

**This gives you:**
- All 18 project scenarios covered ✅
- Solid memory infrastructure ✅
- Strong retrieval + augmentation ✅
- Entity linking working well ✅
- Performance target achievable ✅

**Time permitting, add 🟢 ADJACENT scenarios:**
- S2.4 (cross-entity reference)
- S3.2-3.4 (better context understanding)
- S6.2 (multi-hop reasoning)
- S9.2-9.3 (medium/low confidence)
- S10.2-10.3 (multi-turn conversations)

**These are LOW COMPLEXITY additions that make responses feel more intelligent without requiring new infrastructure.**

---

### For the Full Vision (Long-Term):

After the project submission, if building this as a product:

**Next phase (🟡 STRETCH):**
- S4.1, S5.1 (basic pattern detection)
- S7.1 (basic decision support)
- S8.1-8.2 (workflow learning)

---

## Summary

**✅ CORE: 15 scenarios** → Covers all 18 project requirements
**🟢 ADJACENT: 11 scenarios** → Natural extensions, low-medium complexity
**🟡 STRETCH: 7 scenarios** → Higher complexity, valuable but not required

**Recommendation for project:** Nail the ✅ CORE scenarios (maps to all 18 project requirements), add 🟢 ADJACENT if time permits. 🟡 STRETCH scenarios are valuable future enhancements that demonstrate the full vision but aren't required for the initial submission.

---

## Measurement Criteria

Each scenario should demonstrate:
1. **Correctness**: Accurate retrieval and reasoning
2. **Intelligence**: Beyond simple lookup (synthesis, patterns, insights)
3. **Transparency**: Confidence levels, source attribution, reasoning
4. **Learning**: Memory updates that improve future interactions
5. **Usefulness**: Actionable outputs for business decisions

---

**This comprehensive scenario set provides the blueprint for implementing the full UX vision. Each scenario is a test case and specification for development.**
