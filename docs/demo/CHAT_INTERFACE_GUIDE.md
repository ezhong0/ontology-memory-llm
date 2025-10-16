# Chat Interface Guide

## Overview

The Chat Interface demonstrates the **full memory system pipeline**:
```
User Query → Domain Fact Retrieval → Memory Retrieval → Context Building → LLM Reply
```

---

## How It Works

### 1. Domain Fact Retrieval
When you ask a question, the system automatically fetches relevant facts from the domain database:
- **Customers**: Recent customers with industry information
- **Invoices**: Open and paid invoices with amounts and due dates
- **Sales Orders**: Related sales orders

**Example Facts Retrieved:**
```
- Customer: Kai Media (Industry: Entertainment)
- Invoice INV-1009 for Kai Media: $1,200.00 (due 2025-09-30)
```

### 2. Memory Retrieval
The system fetches semantic memories about entities:
- **Preferences**: Contact methods, delivery days, payment terms
- **Patterns**: Behavior patterns learned from past interactions
- **Context**: Business relationships, timezone info, etc.

**Example Memories Retrieved:**
```
- Kai Media prefers_delivery_day: Friday (confidence: 85%)
- TechStart Inc prefers_contact_method: Slack @techstart-finance (confidence: 90%)
```

### 3. Context Building
Domain facts and memories are combined into a structured `ReplyContext`:
```json
{
  "query": "What invoices do we have?",
  "domain_facts": [4 facts],
  "retrieved_memories": [4 memories],
  "recent_chat_events": [],
  "user_id": "demo-user"
}
```

### 4. Reply Generation
- **With OpenAI API Key**: LLM generates natural language reply using context
- **Without API Key (Fallback)**: System shows the context that would be sent to LLM

---

## Demo Mode (Fallback)

When `OPENAI_API_KEY` is not set, the system runs in **demo mode**:

### What You See:
```
**[Demo Mode - No LLM]**
I would have used the following context to generate a reply:

**Domain Facts (4):**
- Customer: Kai Media (Industry: Entertainment)
- Invoice INV-1009 for Kai Media: $1,200.00 (due 2025-09-30)
...

**Memories (4):**
- Kai Media prefers_delivery_day: Friday (confidence: 85%)
...

**To enable full LLM replies**, set OPENAI_API_KEY environment variable.
```

### Why This is Useful:
- **Transparency**: You can see exactly what context the LLM would receive
- **Debugging**: Verify the system is retrieving the right facts and memories
- **Learning**: Understand how the memory system works

---

## Example Queries

### 1. Invoice Questions
**Query**: `"What invoices do we have?"`

**What You'll See**:
- All invoices from domain database (with amounts, due dates, status)
- Related customer information
- Payment preferences from memories

---

**Query**: `"Which invoices are overdue?"`

**What You'll See**:
- Invoices with due dates in the past
- Customer names and amounts
- Relevant payment behavior patterns

---

### 2. Customer Questions
**Query**: `"Tell me about Kai Media"`

**What You'll See**:
- Customer info (industry, notes)
- All related invoices and sales orders
- Semantic memories (preferences, patterns)

---

**Query**: `"What do we know about TechStart Inc?"`

**What You'll See**:
- Customer details
- Payment terms (NET45)
- Contact preferences (Slack)
- Timezone info (PST/PDT)

---

### 3. Preference Recall
**Query**: `"How should I contact TechStart Inc?"`

**What You'll See**:
- Contact method preference from memory: Slack @techstart-finance
- Customer info for context

---

**Query**: `"When does Kai Media prefer deliveries?"`

**What You'll See**:
- Delivery day preference from memory: Friday
- Related customer and order information

---

### 4. Financial Questions
**Query**: `"What's the total amount of open invoices?"`

**What You'll See**:
- All open invoices with amounts
- Sum would be calculated (if LLM enabled)
- Customer breakdown

---

**Query**: `"Who owes us money?"`

**What You'll See**:
- Customers with open invoices
- Invoice amounts and due dates
- Payment terms from memories

---

### 5. Business Context Questions
**Query**: `"What are the payment terms for TechStart Inc?"`

**What You'll See**:
- Payment terms memory: NET45 (reason: cash flow planning)
- Related invoices to show application of terms

---

## Debug Information

Click **"🔍 Show Debug Info"** to see:

### Domain Facts Used
```json
[
  {
    "type": "invoice_status",
    "content": "Invoice INV-1009 for Kai Media: $1,200.00 (due 2025-09-30)",
    "source": "domain.invoices"
  }
]
```

### Memories Used
```json
[
  {
    "type": "semantic",
    "content": "Kai Media prefers_delivery_day: Friday",
    "confidence": 0.85,
    "relevance": 0.8
  }
]
```

### Context Summary
```json
{
  "user_id": "demo-user",
  "domain_facts_count": 4,
  "memories_count": 4,
  "has_db_facts": true,
  "has_memories": true
}
```

---

## Enabling Full LLM Mode

To get natural language replies instead of fallback mode:

### 1. Set OpenAI API Key
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 2. Restart Server
```bash
make run
```

### 3. Try a Query
```
Query: "What invoices do we have?"

LLM Reply: "We currently have 2 open invoices:
- INV-1009 for Kai Media: $1,200 due September 30, 2025
- INV-2034 for TechStart Inc: $8,500 due October 15, 2025

Note: Kai Media prefers Friday deliveries, and TechStart Inc prefers
communication via Slack (@techstart-finance) with NET45 payment terms."
```

---

## Testing Scenarios

### Load Different Scenarios
Each scenario adds different data to test various memory system features:

**Scenario 1**: Single customer with delivery preference
```
Load Scenario 1 → Ask "What do we know about Kai Media?"
```

**Scenario 2**: Customer with multiple preferences
```
Load Scenario 2 → Ask "How should I contact TechStart Inc?"
```

**Scenario 3**: Past issue recall
```
Load Scenario 3 → Ask "Tell me about Design Studio Co"
```

**Scenario 4**: Payment behavior patterns
```
Load Scenario 4 → Ask "What are the payment patterns for Retail Chain LLC?"
```

**Scenario 5**: Corporate hierarchy
```
Load Scenario 5 → Ask "Tell me about Acme Corp and its subsidiaries"
```

**Scenario 6**: Multi-entity tasks
```
Load Scenario 6 → Ask "What tasks do we have?"
```

---

## Tips for Best Results

### 1. Load Multiple Scenarios
```
Load Scenario 1 + Scenario 2 → More diverse data to query
```

### 2. Use Specific Entity Names
```
✅ "What invoices does Kai Media have?"
❌ "What invoices are there?"
```

### 3. Check Debug Info
Always click "Show Debug Info" to see:
- What facts were retrieved
- What memories were found
- How the context was built

### 4. Compare Memory vs Database
```
Query: "What are TechStart Inc's payment terms?"

Memory: "NET45 (learned from past interactions)"
Database: [Current invoice with NET45 terms]
```

---

## Architecture Deep Dive

### Full Pipeline
```
1. User sends message via Chat UI
   ↓
2. POST /demo/chat/message
   ↓
3. _fetch_domain_facts()
   - Query domain.customers
   - Query domain.invoices (with JOINs)
   - Build DomainFact objects with full provenance
   ↓
4. _fetch_relevant_memories()
   - Query semantic_memories (with canonical_entity JOINs)
   - Build RetrievedMemory objects with confidence
   ↓
5. Build ReplyContext
   - Combine domain facts + memories
   - Add conversation history (future)
   - Add metadata (user_id, session_id)
   ↓
6. Generate Reply
   - LLM mode: Send to LLMReplyGenerator
   - Fallback mode: Format context for display
   ↓
7. Return Response
   - Reply text (natural language or formatted context)
   - Debug info (facts used, memories used, summary)
   ↓
8. Frontend displays
   - User message (right, purple)
   - Assistant reply (left, white)
   - Collapsible debug section
```

---

## Performance Notes

### Response Times
- **Domain fact retrieval**: ~10-50ms (2 database queries)
- **Memory retrieval**: ~10-30ms (1 database query with JOIN)
- **Context building**: ~1ms (in-memory)
- **Fallback reply**: ~1ms (string formatting)
- **LLM reply** (when enabled): ~500-2000ms (OpenAI API call)

**Total**: ~50-100ms in fallback mode, ~600-2100ms with LLM

### Data Volume
- Fetches up to **10 customers** (most recent)
- Fetches up to **10 invoices** (most recent)
- Fetches up to **10 memories** (all active for demo-user)

---

## Troubleshooting

### Issue: "Failed to process chat message"
**Cause**: Backend error or timeout

**Solution**:
1. Check server logs: `tail -20 /tmp/demo_server.log`
2. Verify database is running: `make docker-up`
3. Restart server: `make run`

---

### Issue: Empty context (no facts/memories)
**Cause**: No scenarios loaded

**Solution**:
1. Go to "Scenarios" tab
2. Click "Load Scenario 1" or "Load Scenario 2"
3. Try chat query again

---

### Issue: Chat not updating
**Cause**: JavaScript error

**Solution**:
1. Open browser console (F12)
2. Look for errors
3. Refresh page
4. Try again

---

## Future Enhancements (Phase 1C+)

### 1. Semantic Search
- Replace "fetch all memories" with pgvector similarity search
- Rank memories by relevance to query
- Only retrieve top-K most relevant

### 2. Intelligent Fact Selection
- Parse query to identify mentioned entities
- Fetch only relevant domain data (not all customers/invoices)
- Cross-table reasoning (SO → Invoice → Payment chain)

### 3. Conversation History
- Track recent chat events in session
- Use for context continuity
- Reference previous messages

### 4. Conflict Highlighting
- Detect Memory vs Database conflicts
- Show in UI when data disagrees
- Let user choose which to trust

---

## Summary

The Chat Interface is a **complete demonstration** of the memory system:
- ✅ Retrieves domain facts from database
- ✅ Retrieves semantic memories with confidence
- ✅ Builds structured context for LLM
- ✅ Shows full debug transparency
- ✅ Works in fallback mode (no API key required)
- ✅ Ready for LLM integration (set OPENAI_API_KEY)

**Try it now**: Load a scenario, click the Chat tab, and ask a question!
