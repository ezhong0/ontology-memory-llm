"""Orchestrate domain queries using LLM tool calling.

Vision Alignment:
- Emergent intelligence (LLM decides what to fetch)
- Observable (track tool usage)
- Feedback-driven (log outcomes for learning)
- Epistemic humility (LLM expresses uncertainty)
"""

import json
from typing import Any

import structlog

from src.application.services.tool_executor import ToolExecutor
from src.application.services.tool_registry import ToolRegistry
from src.config.heuristics import (
    TOOL_ORCHESTRATION_MAX_ITERATIONS,
    TOOL_ORCHESTRATION_MODEL,
)
from src.domain.ports.domain_database_port import DomainDatabasePort
from src.domain.ports.llm_service import ILLMService
from src.domain.ports.tool_usage_tracker_port import IToolUsageTracker
from src.domain.value_objects.domain_fact import DomainFact

logger = structlog.get_logger(__name__)


class AdaptiveQueryOrchestrator:
    """Orchestrate domain queries using LLM intelligence.

    Philosophy:
    Instead of:
        if "invoice" in query: run_invoice_query()

    We have:
        llm.decide_what_to_fetch(query, available_tools)
        → LLM calls tools as needed
        → Returns enriched context

    This is:
    - Adaptive (learns from context)
    - Composable (tools are independent)
    - Observable (track which patterns work)
    - Emergent (intelligence from tool combinations)
    """

    def __init__(
        self,
        llm_service: ILLMService,
        domain_db: DomainDatabasePort,
        usage_tracker: IToolUsageTracker,
    ):
        """Initialize orchestrator.

        Args:
            llm_service: LLM for tool calling
            domain_db: Domain database port
            usage_tracker: Track tool usage patterns
        """
        self.llm = llm_service
        self.domain_db = domain_db
        self.tracker = usage_tracker

        # Generate tools from port interface
        # Note: We pass the class itself for inspection, not an instance
        registry = ToolRegistry(DomainDatabasePort)  # type: ignore[type-abstract]
        tool_definitions = registry.generate_tools()

        # Convert to Claude format
        self.tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tool_definitions
        ]

        # Executor for running tools
        self.executor = ToolExecutor(domain_db)

    async def augment(
        self,
        query: str,
        entities: list[dict[str, Any]],
        conversation_id: str,
    ) -> list[DomainFact]:
        """Augment query with domain facts using LLM tool calling.

        Args:
            query: User query text
            entities: Resolved entities (e.g., [{"entity_id": "customer_abc", "type": "customer"}])
            conversation_id: For tracking usage patterns

        Returns:
            List of domain facts retrieved by LLM
        """
        # Build system prompt with available tools and entity context
        system_prompt = self._build_system_prompt(entities)

        logger.info(
            "adaptive_query_orchestration_starting",
            query=query,
            entity_count=len(entities),
            available_tools=len(self.tools),
        )

        # Track tool calls for feedback loop
        tool_calls_made: list[dict[str, Any]] = []
        all_facts: list[DomainFact] = []

        # Iterative tool calling (max iterations to prevent loops)
        messages = [{"role": "user", "content": query}]

        for iteration in range(TOOL_ORCHESTRATION_MAX_ITERATIONS):
            # Call LLM with tools
            response = await self.llm.chat_with_tools(
                system_prompt=system_prompt,
                messages=messages,
                tools=self.tools,
                model=TOOL_ORCHESTRATION_MODEL,
            )

            # Check for tool calls
            if response.tool_calls:
                logger.info(
                    "llm_requesting_tools",
                    iteration=iteration,
                    tool_count=len(response.tool_calls),
                )

                # Execute all tool calls
                tool_results: list[dict[str, Any]] = []

                for tool_call in response.tool_calls:
                    tool_name = tool_call.name
                    arguments = tool_call.arguments

                    # Execute tool
                    result = await self.executor.execute(tool_name, arguments)

                    # Track for feedback
                    tool_calls_made.append(
                        {
                            "tool": tool_name,
                            "arguments": arguments,
                            "iteration": iteration,
                        }
                    )

                    # Collect facts
                    if isinstance(result, list):
                        all_facts.extend(result)

                    # Add to tool results for LLM
                    tool_results.append(
                        {
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                self._serialize_facts(result), default=str
                            ),
                        }
                    )

                # Add assistant message + tool results to conversation
                # Type: list[dict[str, Any]] for flexible message format
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                        for tc in response.tool_calls
                    ],
                }
                messages.append(assistant_msg)

                # Add tool results
                for tr in tool_results:
                    tool_msg: dict[str, Any] = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tr["tool_call_id"],
                                "content": tr["content"],
                            }
                        ],
                    }
                    messages.append(tool_msg)

                # Continue loop - LLM will process results
                continue

            else:
                # No more tool calls - LLM is done
                logger.info(
                    "llm_tool_orchestration_complete",
                    iterations=iteration + 1,
                    facts_retrieved=len(all_facts),
                    tools_used=len(tool_calls_made),
                )

                # Track usage for feedback loop
                await self.tracker.log_tool_usage(
                    conversation_id=conversation_id,
                    query=query,
                    tools_called=tool_calls_made,
                    facts_count=len(all_facts),
                )

                return all_facts

        # Max iterations reached
        logger.warning(
            "max_tool_iterations_reached",
            facts_retrieved=len(all_facts),
        )

        # Track even if max iterations reached
        await self.tracker.log_tool_usage(
            conversation_id=conversation_id,
            query=query,
            tools_called=tool_calls_made,
            facts_count=len(all_facts),
        )

        return all_facts

    def _build_system_prompt(self, entities: list[dict[str, Any]]) -> str:
        """Build system prompt with entity context.

        Args:
            entities: Resolved entities

        Returns:
            System prompt string
        """
        # Build entities context with extracted UUIDs for easy reference
        entities_lines = []
        for e in entities:
            name = e.get('canonical_name', e['entity_id'])
            entity_type = e['entity_type']
            entity_id = e['entity_id']

            # Extract UUID from entity_id (format: "customer_<uuid>")
            if '_' in entity_id:
                uuid_part = entity_id.split('_', 1)[1]
            else:
                uuid_part = entity_id

            entities_lines.append(
                f"- {name} (type: {entity_type}, customer_id: {uuid_part})"
            )

        entities_context = "\n".join(entities_lines) if entities_lines else "(No entities in this conversation yet)"

        return f"""You are an intelligent business data retrieval assistant.

ENTITIES IN THIS CONVERSATION:
{entities_context}

Your job is to fetch relevant business data by calling the available tools.

GUIDELINES:
1. Think about what information is needed to answer the query
2. Call tools to fetch that data (you can call multiple tools)
3. Use the customer_id value shown above when calling tools (it's the UUID without prefix)
4. For sales orders, extract SO number from canonical_name (e.g., "SO-1001")
5. Call tools in parallel when possible (e.g., invoices + work orders together)

IMPORTANT:
- You are ONLY responsible for DATA RETRIEVAL, not response generation
- Call the tools needed, then stop
- Do NOT generate a conversational response
- The retrieved data will be used by another system for response generation

Available tools will be provided. Use them to fetch all relevant business data."""

    def _serialize_facts(self, result: Any) -> Any:
        """Serialize DomainFacts to JSON-compatible format.

        Args:
            result: Tool execution result

        Returns:
            JSON-serializable result
        """
        if isinstance(result, list):
            return [
                fact.to_api_response() if hasattr(fact, "to_api_response") else str(fact)
                for fact in result
            ]
        elif hasattr(result, "to_api_response"):
            return result.to_api_response()
        else:
            return result
