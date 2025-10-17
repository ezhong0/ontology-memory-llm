# LLM Query Planner: Vision-Aligned Alternative

**Philosophy**: Instead of keyword matching → intent → hardcoded queries, let the LLM reason about what information is needed by looking at the ontology schema.

---

## The Fundamental Shift

### Current Approach (Brittle)
```python
# Step 1: Keyword match
if "invoice" in query: intent = "financial"

# Step 2: Hardcoded mapping
if intent == "financial": run_invoice_query()
```

**Problems**:
- Keywords miss synonyms, context, nuance
- Hardcoded mappings don't generalize
- No reasoning about relationships
- Adding domains = code changes

### Vision-Aligned Approach (Adaptive)
```python
# Step 1: LLM sees the schema
schema = ontology.get_schema()  # customer → sales_order → invoice

# Step 2: LLM reasons about what's needed
query_plan = await llm.plan_queries(query_text, schema, entities)

# Step 3: Execute plan dynamically
facts = await execute_plan(query_plan)
```

**Advantages**:
- LLM understands context, not just keywords
- Reasons about graph relationships
- Generalizes to new domains automatically
- No code changes needed

---

## Architecture: The Query Planner

### Core Component

```python
"""LLM-based query planner.

Vision Principle: "The graph structure enables multi-hop reasoning
grounded in domain semantics" (Vision lines 125-139)

Instead of hardcoded intent → query mappings, the LLM:
1. Sees the ontology schema (what tables exist, how they relate)
2. Sees resolved entities (what we're asking about)
3. Reasons about what information is needed
4. Returns a query plan (which tables to fetch, how to join)
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()

@dataclass
class QueryPlan:
    """LLM-generated query plan."""

    reasoning: str  # Why these queries are needed
    queries: List[Dict[str, Any]]  # List of {table, filters, joins}
    confidence: float  # How confident the LLM is

class LLMQueryPlanner:
    """Generate query plans using LLM + ontology schema.

    Philosophy: Let the LLM be the "experienced colleague" who knows
    what information to fetch by understanding the question + schema.
    """

    def __init__(
        self,
        llm_service: ILLMService,
        ontology_service: OntologyService,
    ):
        self.llm = llm_service
        self.ontology = ontology_service

    async def plan(
        self,
        query_text: str,
        resolved_entities: List[ResolvedEntity],
    ) -> QueryPlan:
        """Generate query plan for a user question.

        Args:
            query_text: User's question
            resolved_entities: Entities mentioned in question

        Returns:
            QueryPlan with queries to execute
        """
        # Get ontology schema
        schema = await self.ontology.get_schema_summary()

        # Build LLM prompt
        prompt = self._build_planning_prompt(
            query_text=query_text,
            entities=resolved_entities,
            schema=schema,
        )

        # Ask LLM to plan
        response = await self.llm.complete(prompt)

        # Parse response
        query_plan = self._parse_query_plan(response)

        logger.info(
            "query_plan_generated",
            query_count=len(query_plan.queries),
            reasoning=query_plan.reasoning[:100],
            confidence=query_plan.confidence,
        )

        return query_plan

    def _build_planning_prompt(
        self,
        query_text: str,
        entities: List[ResolvedEntity],
        schema: Dict[str, Any],
    ) -> str:
        """Build prompt for query planning."""

        # Format entities
        entities_str = "\n".join([
            f"- {e.canonical_name} (type: {e.entity_type}, id: {e.entity_id})"
            for e in entities
        ])

        # Format schema (tables + relationships)
        schema_str = self._format_schema(schema)

        return f"""You are a query planner for a business database system.

USER QUESTION: "{query_text}"

ENTITIES MENTIONED:
{entities_str}

DATABASE SCHEMA:
{schema_str}

TASK: Determine what information is needed to answer the user's question.

Think step-by-step:
1. What is the user asking about? (status, history, relationships, etc.)
2. Which entities are involved?
3. What database tables contain this information?
4. Are there relationships to traverse? (e.g., customer → orders → invoices)
5. What filters or conditions apply?

Respond in JSON format:
{{
  "reasoning": "Brief explanation of what information is needed and why",
  "confidence": 0.85,
  "queries": [
    {{
      "table": "invoices",
      "purpose": "Get invoice status for customer",
      "filters": {{"customer_id": "customer_uuid"}},
      "fields": ["invoice_number", "amount", "due_date", "status"],
      "joins": []
    }},
    {{
      "table": "work_orders",
      "purpose": "Check if work is complete before invoicing",
      "filters": {{"customer_id": "customer_uuid"}},
      "fields": ["wo_number", "status", "completed_at"],
      "joins": [
        {{"from": "work_orders.so_id", "to": "sales_orders.so_id"}}
      ]
    }}
  ]
}}

Guidelines:
- Only include queries that are NECESSARY to answer the question
- Use multi-hop joins when relationships matter (customer → SO → WO → invoice)
- Be specific about what fields are needed
- Confidence should reflect how certain you are about the query plan
- If question is ambiguous, lower confidence and explain in reasoning
"""

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format schema for LLM prompt."""

        lines = []

        lines.append("TABLES:")
        for table_name, table_info in schema.get("tables", {}).items():
            lines.append(f"\n{table_name}:")
            lines.append(f"  Description: {table_info.get('description', 'N/A')}")
            lines.append(f"  Key Fields: {', '.join(table_info.get('key_fields', []))}")

        lines.append("\n\nRELATIONSHIPS:")
        for rel in schema.get("relationships", []):
            lines.append(
                f"- {rel['from_table']} → {rel['to_table']} "
                f"(via {rel['join_condition']})"
            )

        return "\n".join(lines)

    def _parse_query_plan(self, llm_response: str) -> QueryPlan:
        """Parse LLM response into QueryPlan."""

        import json

        # Strip markdown code blocks if present
        response = llm_response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        # Parse JSON
        data = json.loads(response)

        return QueryPlan(
            reasoning=data["reasoning"],
            queries=data["queries"],
            confidence=data.get("confidence", 0.7),
        )
```

---

## Ontology Service Enhancement

The planner needs a clean schema summary from the ontology:

```python
# src/domain/services/ontology_service.py

class OntologyService:
    """Manage domain ontology for query planning."""

    async def get_schema_summary(self) -> Dict[str, Any]:
        """Get ontology schema for LLM query planning.

        Returns:
            Schema dictionary with tables + relationships
        """
        # Fetch from domain_ontology table
        tables = await self.ontology_repo.get_all_tables()
        relationships = await self.ontology_repo.get_all_relationships()

        schema = {
            "tables": {},
            "relationships": [],
        }

        # Format tables
        for table in tables:
            schema["tables"][table.table_name] = {
                "description": table.description,
                "key_fields": table.key_fields,
                "entity_type": table.entity_type,
            }

        # Format relationships
        for rel in relationships:
            schema["relationships"].append({
                "from_table": rel.from_table,
                "to_table": rel.to_table,
                "relationship_type": rel.relationship_type,  # "has_many", "belongs_to"
                "join_condition": rel.join_condition,
                "semantic_meaning": rel.semantic_meaning,  # "fulfills", "obligates"
            })

        return schema
```

---

## Integration: Replace Intent Classifier

```python
# src/domain/services/domain_augmentation_service.py

class DomainAugmentationService:
    """Orchestrate domain fact retrieval using LLM query planner."""

    def __init__(
        self,
        domain_db_port: DomainDatabasePort,
        llm_query_planner: LLMQueryPlanner,  # ✅ LLM instead of keywords
    ):
        self.domain_db = domain_db_port
        self.query_planner = llm_query_planner

    async def augment(
        self,
        entities: List[EntityInfo],
        query_text: str,
        intent: str | None = None,  # ⚠️  Deprecated, kept for compatibility
    ) -> List[DomainFact]:
        """Augment with relevant domain facts using LLM planning."""

        if not entities:
            logger.debug("domain_augmentation_skipped_no_entities")
            return []

        # ✅ LLM GENERATES QUERY PLAN (no keywords!)
        query_plan = await self.query_planner.plan(
            query_text=query_text,
            resolved_entities=entities,
        )

        logger.info(
            "llm_query_plan_generated",
            reasoning=query_plan.reasoning,
            query_count=len(query_plan.queries),
            confidence=query_plan.confidence,
        )

        # Execute queries from plan
        tasks = []
        for query_spec in query_plan.queries:
            task = self._execute_query_spec(query_spec)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        facts: List[DomainFact] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("query_execution_failed", error=str(result))
            elif isinstance(result, list):
                facts.extend(result)

        return facts

    async def _execute_query_spec(
        self,
        query_spec: Dict[str, Any],
    ) -> List[DomainFact]:
        """Execute a single query from the plan."""

        table = query_spec["table"]
        filters = query_spec.get("filters", {})
        fields = query_spec.get("fields", ["*"])
        joins = query_spec.get("joins", [])

        # Build SQL dynamically based on spec
        if joins:
            # Multi-hop query
            facts = await self.domain_db.execute_join_query(
                table=table,
                filters=filters,
                fields=fields,
                joins=joins,
            )
        else:
            # Simple query
            facts = await self.domain_db.execute_simple_query(
                table=table,
                filters=filters,
                fields=fields,
            )

        # Annotate with purpose from plan
        for fact in facts:
            fact.metadata["query_purpose"] = query_spec.get("purpose", "")

        return facts
```

---

## Example: How It Works

### User Query
```
"Can we invoice Gai Media?"
```

### Entities Resolved
```python
[
    ResolvedEntity(
        entity_id="customer_abc123",
        canonical_name="Gai Media",
        entity_type="customer"
    )
]
```

### LLM Sees Schema
```
TABLES:
customers:
  Description: Customer master data
  Key Fields: customer_id, name, payment_terms

sales_orders:
  Description: Sales orders from customers
  Key Fields: so_id, so_number, customer_id, status

work_orders:
  Description: Work orders fulfilling sales orders
  Key Fields: wo_id, wo_number, so_id, status, completed_at

invoices:
  Description: Customer invoices
  Key Fields: invoice_id, invoice_number, customer_id, amount, due_date, status

RELATIONSHIPS:
- customers → sales_orders (via customers.customer_id = sales_orders.customer_id)
- sales_orders → work_orders (via sales_orders.so_id = work_orders.so_id)
- sales_orders → invoices (via sales_orders.so_id = invoices.so_id)
```

### LLM Reasons (no keywords!)
```json
{
  "reasoning": "To determine if we can invoice Gai Media, I need to check:
    (1) Are there any sales orders for this customer?
    (2) Is the work complete? (work_order.status = 'done')
    (3) Has an invoice already been created?
    This requires traversing: customer → sales_order → work_order → invoice",

  "confidence": 0.92,

  "queries": [
    {
      "table": "sales_orders",
      "purpose": "Find active sales orders for Gai Media",
      "filters": {"customer_id": "customer_abc123", "status": "active"},
      "fields": ["so_id", "so_number", "status"]
    },
    {
      "table": "work_orders",
      "purpose": "Check if work is completed",
      "filters": {"so_id": "<from_previous_query>"},
      "fields": ["wo_number", "status", "completed_at"],
      "joins": [{"from": "work_orders.so_id", "to": "sales_orders.so_id"}]
    },
    {
      "table": "invoices",
      "purpose": "Check if invoice already exists",
      "filters": {"customer_id": "customer_abc123"},
      "fields": ["invoice_number", "status", "amount"]
    }
  ]
}
```

### System Executes Plan
```python
# Automatically fetch:
# 1. Sales orders for Gai Media
# 2. Work orders for those SOs (with join)
# 3. Existing invoices for Gai Media

# Returns comprehensive context for LLM to generate answer
```

### Response
```
"Gai Media has sales order SO-1001 with work order WO-5002. The work was completed
on Jan 10, 2025. No invoice exists yet. Yes, we can create invoice now."
```

---

## Why This Is Vision-Aligned

### 1. **No Keywords** ✅
The LLM understands context, not keyword buckets:
- "Can we invoice?" → LLM knows to check work completion + existing invoices
- "Is it ready to ship?" → LLM knows to check inventory + work status
- Same question, different entities → different queries automatically

### 2. **Graph-Aware Reasoning** ✅
Vision lines 125-139:
> "Multi-hop reasoning across entities... Customer → Sales Order → Work Order → Invoice"

The LLM traverses relationships in the prompt, generates join queries.

### 3. **Context is Constitutive** ✅
Vision lines 145-155:
> "Context is constitutive of meaning... Retrieval is reconstructing the minimal context necessary"

The LLM decides what context is needed for THIS specific question.

### 4. **Emergent Intelligence** ✅
Vision lines 467-485:
> "Intelligence emerges from interaction of simple mechanisms"

Mechanism: LLM + Ontology Schema → Query Plan
Emergent behavior: Correct queries for ANY question, ANY domain

### 5. **Epistemic Humility** ✅
The LLM can express uncertainty:
```json
{
  "reasoning": "The question is ambiguous - 'invoice' could mean create new invoice
    OR check existing invoice status. I'm querying both to be safe.",
  "confidence": 0.65
}
```

### 6. **Extensible** ✅
Add new table to ontology → LLM automatically uses it. Zero code changes.

---

## Performance Considerations

### Latency
- **LLM call**: ~200-500ms (similar to keyword approach + LLM generation)
- **Caching**: Cache query plans for similar questions
- **Fallback**: If LLM fails, use simple heuristic

### Cost
- **Per query**: ~500 input tokens (schema) + 200 output tokens = ~$0.0003 per planning call
- **Optimization**: Use smaller, faster model (Haiku, GPT-4o-mini)
- **Trade-off**: Slightly higher cost, massively better accuracy + flexibility

### Hybrid Approach
```python
# For simple queries, use deterministic rules (fast path)
if len(entities) == 1 and entities[0].entity_type == "customer":
    # Simple customer lookup, no LLM needed
    return await self.domain_db.get_customer_summary(entities[0].entity_id)

# For complex/ambiguous queries, use LLM planner
else:
    query_plan = await self.query_planner.plan(query_text, entities)
    return await self.execute_plan(query_plan)
```

---

## Migration Path

### Phase 1: Parallel Running (Week 1)
```python
# Run both approaches, log differences
keyword_queries = await self.select_queries_keyword(entities, intent)
llm_queries = await self.query_planner.plan(query_text, entities)

logger.info(
    "query_comparison",
    keyword_count=len(keyword_queries),
    llm_count=len(llm_queries.queries),
    match=(keyword_queries == llm_queries.queries),
)

# Use keyword approach, log LLM plan for analysis
```

### Phase 2: A/B Test (Week 2-3)
```python
# 50% traffic → keyword approach
# 50% traffic → LLM planner
# Measure: accuracy, latency, user satisfaction
```

### Phase 3: Full Migration (Week 4)
```python
# 100% LLM planner
# Remove keyword classification entirely
```

---

## The Fundamental Difference

### Keyword Approach (Current)
```
"Can we invoice Gai Media?"
    ↓ [Keyword Match]
"invoice" → intent=financial
    ↓ [Hardcoded Mapping]
financial + customer → run_invoice_query()
    ↓ [Execute]
Get invoice status for customer
```

**Problem**: No understanding. Just pattern matching.

### LLM Planner (Vision-Aligned)
```
"Can we invoice Gai Media?"
    ↓ [LLM Reasoning with Schema]
"To answer 'can we invoice', I need to check:
 - Is work complete? (work_orders.status)
 - Does invoice exist? (invoices table)
 - Are there pending SOs? (sales_orders table)
 → Multi-hop: customer → SO → WO → invoice"
    ↓ [Generate Query Plan]
[
  {table: sales_orders, filters: {customer_id}},
  {table: work_orders, joins: [SO→WO]},
  {table: invoices, filters: {customer_id}}
]
    ↓ [Execute Plan]
Comprehensive context for answer
```

**Advantage**: True understanding. Adaptive reasoning.

---

## Conclusion

You're absolutely right—**keywords are a hack**, even in configuration.

The vision-aligned approach is:
1. **LLM sees ontology schema** (what exists, how it relates)
2. **LLM reasons about question** (what information is needed)
3. **LLM generates query plan** (which tables, what joins)
4. **System executes plan** (fetch facts)
5. **LLM generates answer** (synthesize response)

This is:
- ✅ **No keywords** - LLM understands semantics
- ✅ **Graph-aware** - Multi-hop reasoning built-in
- ✅ **Adaptive** - New tables = automatic usage
- ✅ **Emergent** - Intelligence from LLM + Schema interaction
- ✅ **Extensible** - Zero code changes for new domains

**The ontology becomes the system's knowledge**, and the LLM becomes the reasoning engine that navigates it.

This is the **experienced colleague** the vision describes. 🚀
