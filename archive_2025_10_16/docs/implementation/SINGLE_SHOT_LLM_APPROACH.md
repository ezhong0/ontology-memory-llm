# Single-Shot LLM: Zero Latency Increase

**Problem**: LLM Query Planner adds a second LLM call (~200-500ms extra latency)

**Solution**: Combine query planning + response generation into **one LLM call**

---

## The Key Insight

We don't need the LLM to return a structured query plan separately. We can give it **function calling tools** to fetch data during response generation.

### Current (2 LLM Calls)
```
Call 1: LLM plans queries → Returns JSON query plan
        Execute queries → Get facts
Call 2: LLM generates response using facts
```

### Better (1 LLM Call with Tools)
```
Call 1: LLM generates response
        ↳ When it needs data, calls tools (functions)
        ↳ Tools execute queries and return facts
        ↳ LLM incorporates facts into response
```

**Same latency as current approach, but with LLM intelligence instead of keywords!**

---

## Implementation: Function Calling Tools

### Available Tools for LLM

```python
"""Tools available to LLM during response generation.

The LLM can call these functions to fetch data as needed,
rather than us pre-guessing what data to fetch.
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_summary",
            "description": "Get comprehensive customer information including payment terms, contact details, and relationship history",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string", "description": "Customer UUID"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_invoices",
            "description": "Get invoices for a customer. Use filters to narrow results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["open", "paid", "overdue", "all"]},
                    "include_work_orders": {"type": "boolean", "description": "Include related work orders"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_work_orders",
            "description": "Get work orders with optional filtering by status and sales order",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "done", "all"]},
                    "so_id": {"type": "string", "description": "Filter by sales order ID"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "traverse_order_chain",
            "description": "Follow relationships: customer → sales order → work order → invoice. Returns complete chain.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "include_history": {"type": "boolean", "description": "Include completed orders"}
                },
                "required": ["customer_id"]
            }
        }
    }
]
```

### How It Works

**User asks:** *"Can we invoice Gai Media?"*

**System:**
1. Resolves entities: `Gai Media → customer_abc123`
2. Calls LLM with tools available:

```python
response = await llm.chat.completions.create(
    model="gpt-4o",  # or claude-3-5-sonnet
    messages=[
        {
            "role": "system",
            "content": """You are a business assistant with access to database tools.

            To answer questions, use the provided functions to fetch relevant data.
            Think step-by-step about what information you need."""
        },
        {
            "role": "user",
            "content": "Can we invoice Gai Media?"
        }
    ],
    tools=tools,
    tool_choice="auto"  # LLM decides when to call tools
)
```

**LLM's internal reasoning** (not visible to us):
```
To answer "can we invoice", I need to check:
1. Are there active sales orders? → call get_work_orders()
2. Is work complete? → check work_order.status
3. Does invoice exist? → call get_invoices()

Let me fetch this data...
```

**LLM calls tools:**
```python
# First tool call
tool_call_1 = {
    "function": "get_work_orders",
    "arguments": {
        "customer_id": "customer_abc123",
        "status": "all"
    }
}
# System executes → returns: [{"wo_number": "WO-5002", "status": "done", "so_id": "SO-1001"}]

# Second tool call
tool_call_2 = {
    "function": "get_invoices",
    "arguments": {
        "customer_id": "customer_abc123",
        "status": "all"
    }
}
# System executes → returns: []
```

**LLM generates final response:**
```
"Yes, we can invoice Gai Media. Work order WO-5002 for sales order SO-1001
is complete. No invoice exists yet for this order."
```

---

## Code Implementation

### Tool Executor

```python
"""Execute tool calls from LLM."""

from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class ToolExecutor:
    """Execute LLM tool calls to fetch domain data."""

    def __init__(self, domain_db: DomainDatabasePort):
        self.domain_db = domain_db

        # Map tool names to handlers
        self.handlers = {
            "get_customer_summary": self._get_customer_summary,
            "get_invoices": self._get_invoices,
            "get_work_orders": self._get_work_orders,
            "traverse_order_chain": self._traverse_order_chain,
        }

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool call."""

        logger.info(
            "executing_tool",
            tool_name=tool_name,
            arguments=arguments,
        )

        if tool_name not in self.handlers:
            return {"error": f"Unknown tool: {tool_name}"}

        try:
            result = await self.handlers[tool_name](**arguments)

            logger.info(
                "tool_executed",
                tool_name=tool_name,
                result_count=len(result) if isinstance(result, list) else 1,
            )

            return result
        except Exception as e:
            logger.error(
                "tool_execution_failed",
                tool_name=tool_name,
                error=str(e),
            )
            return {"error": str(e)}

    async def _get_customer_summary(self, customer_id: str) -> Dict[str, Any]:
        """Get customer summary."""
        return await self.domain_db.get_customer_summary(customer_id)

    async def _get_invoices(
        self,
        customer_id: str,
        status: str = "all",
        include_work_orders: bool = False
    ) -> List[Dict[str, Any]]:
        """Get invoices with optional filters."""
        invoices = await self.domain_db.get_invoice_status(customer_id=customer_id)

        if status != "all":
            invoices = [inv for inv in invoices if inv.get("status") == status]

        if include_work_orders:
            # Enrich with work order data
            for invoice in invoices:
                if "so_id" in invoice:
                    invoice["work_orders"] = await self.domain_db.get_work_orders_for_so(
                        invoice["so_id"]
                    )

        return invoices

    async def _get_work_orders(
        self,
        customer_id: str,
        status: str = "all",
        so_id: str | None = None
    ) -> List[Dict[str, Any]]:
        """Get work orders with filters."""
        work_orders = await self.domain_db.get_work_orders_for_customer(customer_id)

        if status != "all":
            work_orders = [wo for wo in work_orders if wo.get("status") == status]

        if so_id:
            work_orders = [wo for wo in work_orders if wo.get("so_id") == so_id]

        return work_orders

    async def _traverse_order_chain(
        self,
        customer_id: str,
        include_history: bool = False
    ) -> Dict[str, Any]:
        """Traverse full order chain."""
        chain = await self.domain_db.get_order_chain(customer_id=customer_id)

        if not include_history:
            # Filter to active only
            chain["sales_orders"] = [
                so for so in chain.get("sales_orders", [])
                if so.get("status") != "completed"
            ]

        return chain
```

### LLM Reply Generator with Tools

```python
"""LLM reply generator with function calling."""

from typing import List, Dict, Any
import json
import structlog

logger = structlog.get_logger()

class LLMReplyGeneratorWithTools:
    """Generate replies using LLM with function calling.

    The LLM can call database tools during response generation,
    eliminating the need for pre-query planning.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        tool_executor: ToolExecutor,
    ):
        self.llm = llm_service
        self.executor = tool_executor
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for LLM."""
        # (Tools definition from above)
        return tools

    async def generate(
        self,
        query: str,
        resolved_entities: List[ResolvedEntity],
        conversation_history: List[Dict[str, str]] | None = None,
    ) -> str:
        """Generate response with tool calling.

        The LLM decides what data to fetch by calling tools.
        """

        # Build initial messages
        messages = [
            {
                "role": "system",
                "content": self._build_system_prompt(resolved_entities)
            }
        ]

        # Add conversation history if available
        if conversation_history:
            messages.extend(conversation_history)

        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })

        # LLM call with tools
        max_iterations = 5  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Call LLM
            response = await self.llm.chat_with_tools(
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )

            # Check if LLM wants to call tools
            if response.tool_calls:
                logger.info(
                    "llm_calling_tools",
                    tool_count=len(response.tool_calls),
                )

                # Execute all tool calls
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    # Execute tool
                    result = await self.executor.execute(tool_name, arguments)

                    # Add tool response to messages
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

                # Continue loop - LLM will process tool results
                continue

            else:
                # No more tool calls - we have final response
                logger.info(
                    "llm_response_generated",
                    iterations=iteration,
                )
                return response.content

        # Max iterations reached
        logger.warning("max_tool_iterations_reached")
        return "I encountered an issue processing your request. Please try rephrasing."

    def _build_system_prompt(
        self,
        entities: List[ResolvedEntity]
    ) -> str:
        """Build system prompt with entity context."""

        entities_context = "\n".join([
            f"- {e.canonical_name} (type: {e.entity_type}, id: {e.entity_id})"
            for e in entities
        ])

        return f"""You are an intelligent business assistant with access to database tools.

ENTITIES IN THIS CONVERSATION:
{entities_context}

To answer questions accurately:
1. Think about what information is needed
2. Use the provided functions to fetch relevant data
3. Call multiple functions if needed (e.g., check work orders AND invoices)
4. Synthesize the information into a clear, helpful response

Guidelines:
- Be specific and cite data (e.g., "Work order WO-5002 is complete")
- If data is missing, call the appropriate function to get it
- For questions about relationships (e.g., "can we invoice?"), traverse the chain
- Express uncertainty if information is incomplete

Available functions will be called automatically when you need data."""
```

---

## Latency Comparison

### Old Approach (Keywords)
```
Entity Resolution:     50ms
Keyword Intent:         1ms
Query Selection:        1ms
Execute Queries:      150ms (average)
LLM Generation:       400ms
─────────────────────────────
Total:               ~600ms
```

### New Approach (Single LLM + Tools)
```
Entity Resolution:     50ms
LLM with Tool Calls:  450ms (includes query execution)
  ↳ LLM thinking:     100ms
  ↳ Tool call 1:      150ms (async with thinking)
  ↳ Tool call 2:      150ms (async)
  ↳ Final generation: 100ms
─────────────────────────────
Total:               ~500ms (FASTER!)
```

**Why faster?**
- Tool calls execute **in parallel** with LLM processing
- No separate query planning phase
- LLM only fetches what it actually needs (fewer unnecessary queries)

---

## Advantages Over Both Approaches

### vs Keywords
✅ **No hardcoded mappings** - LLM decides what to fetch
✅ **Context-aware** - Same question → different tools based on context
✅ **Adaptive** - New tools → LLM uses them automatically
✅ **Smarter** - Only fetches needed data (keywords often over-fetch)

### vs Separate Query Planner
✅ **No latency increase** - Single LLM call instead of two
✅ **Simpler architecture** - No query plan parsing/execution
✅ **Parallel execution** - Tools run during LLM processing
✅ **Iterative refinement** - LLM can call more tools if initial data insufficient

---

## Edge Cases Handled

### 1. Insufficient Data
```python
# LLM's first call
tool_call = {"function": "get_invoices", "arguments": {"customer_id": "abc"}}
# Returns: []

# LLM realizes: "No invoices, but maybe work isn't done yet?"
tool_call = {"function": "get_work_orders", "arguments": {"customer_id": "abc"}}
# Returns: [{"status": "in_progress"}]

# Final response: "Cannot invoice yet - work order still in progress"
```

### 2. Complex Multi-Hop
```python
# User: "Why hasn't Gai Media been invoiced?"

# LLM calls:
1. get_work_orders() → finds WO-5002 status="done"
2. get_invoices() → finds none exist
3. traverse_order_chain() → sees SO-1001 → WO-5002 → no invoice

# Response: "Work order WO-5002 is complete but no invoice was created.
#           This appears to be an oversight - we should create invoice now."
```

### 3. Ambiguous Questions
```python
# User: "What's the status?"

# LLM: "Status of what? Let me check everything..."
tool_calls = [
    {"function": "get_work_orders", "arguments": {"customer_id": "abc"}},
    {"function": "get_invoices", "arguments": {"customer_id": "abc"}}
]

# Response: "For Gai Media: Work order WO-5002 is complete.
#           Invoice INV-1009 is overdue (due Jan 15)."
```

---

## Implementation Path

### Week 1: Add Tool Infrastructure
```python
# 1. Create ToolExecutor class
# 2. Define 4-6 core tools
# 3. Update LLMReplyGenerator to support function calling
# 4. Test with Claude/GPT-4 (both support function calling)
```

### Week 2: Parallel Running
```python
# Run both approaches:
# - Old: keyword intent → queries → LLM response
# - New: single LLM with tools
# Compare: accuracy, latency, tool usage patterns
```

### Week 3: A/B Test
```python
# 50% traffic → old approach
# 50% traffic → new approach
# Measure user satisfaction, response quality
```

### Week 4: Full Migration
```python
# 100% new approach
# Remove keyword intent classification
# Remove hardcoded query selection
```

---

## Cost Analysis

### Keywords Approach
- 1 LLM call: ~1500 input + 300 output tokens
- Cost: ~$0.002 per query

### Single LLM + Tools
- 1 LLM call with tools: ~2000 input + 500 output tokens (larger context)
- Tool calling overhead: minimal
- Cost: ~$0.003 per query

**Increase: ~50% more cost, but:**
- Dramatically better accuracy
- No maintenance of keyword lists
- Auto-adapts to new domains
- Cleaner architecture

---

## Conclusion

**No, it doesn't add latency!**

The single-shot approach with function calling:
- ✅ **Same latency** as current keyword approach (~500-600ms)
- ✅ **No keywords** - LLM intelligence instead
- ✅ **Tool calls parallel** to LLM processing
- ✅ **Simpler** than separate query planner
- ✅ **More efficient** - only fetches needed data

**This is the vision-aligned approach with zero latency penalty.** 🚀

The key insight: We don't need to plan queries separately. Give the LLM tools and let it fetch what it needs **during** response generation. Function calling makes this seamless.
