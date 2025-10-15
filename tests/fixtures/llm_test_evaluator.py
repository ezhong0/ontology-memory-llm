"""
LLM-Based Test Evaluator for Vision Principle Validation

This module uses LLMs to evaluate whether system behavior aligns with
philosophical principles from VISION.md. Traditional assertions can't
capture semantic nuances like "epistemic humility" or "graceful forgetting" -
LLMs can evaluate natural language behaviors.

USAGE:
    - Generate test cases from vision principles
    - Evaluate responses for philosophical alignment
    - Score system behavior against vision criteria
    - Detect subtle violations humans might catch but code can't assert
"""
from dataclasses import dataclass
from typing import List, Dict, Optional, Literal
from enum import Enum
import openai
import json


class VisionPrinciple(str, Enum):
    """Core vision principles from VISION.md"""
    EPISTEMIC_HUMILITY = "epistemic_humility"
    DUAL_TRUTH = "dual_truth"
    GRACEFUL_FORGETTING = "graceful_forgetting"
    EXPLAINABILITY = "explainability"
    CONTEXT_AWARE = "context_aware"
    LEARNING_ADAPTATION = "learning_adaptation"
    IDENTITY_RESOLUTION = "identity_resolution"
    TEMPORAL_VALIDITY = "temporal_validity"


@dataclass
class EvaluationCriteria:
    """Criteria for LLM-based evaluation"""
    principle: VisionPrinciple
    description: str
    good_indicators: List[str]
    bad_indicators: List[str]
    context: Optional[str] = None


@dataclass
class EvaluationResult:
    """Result of LLM evaluation"""
    principle: VisionPrinciple
    score: float  # 0.0 to 1.0
    reasoning: str
    violations: List[str]
    passes: bool


class LLMTestEvaluator:
    """
    Uses LLM to evaluate system behavior against vision principles.

    Why LLM for testing?
    - Vision principles are expressed in natural language philosophy
    - Semantic nuances hard to capture with code assertions
    - LLM can detect subtle misalignments (e.g., overconfident tone)
    - Can generate edge cases based on principles
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.client = openai.AsyncOpenAI()

    async def evaluate_epistemic_humility(
        self,
        response: str,
        confidence: float,
        context: Dict
    ) -> EvaluationResult:
        """
        Evaluate if response demonstrates epistemic humility.

        Vision: "The system should know what it doesn't know"

        Good indicators:
        - Low confidence → hedging language ("likely", "may", "based on")
        - Aged memory → mentions validation date
        - Conflict → shows both sources
        - No data → acknowledges gap without fabrication

        Bad indicators:
        - Low confidence but certain tone
        - No data but plausible-sounding hallucination
        - Conflict but no acknowledgment
        """
        criteria = EvaluationCriteria(
            principle=VisionPrinciple.EPISTEMIC_HUMILITY,
            description="System demonstrates epistemic humility - knowing what it doesn't know",
            good_indicators=[
                "Uses hedging language when confidence is low",
                "Cites sources and dates for validation",
                "Acknowledges conflicts explicitly",
                "Admits lack of information rather than fabricating"
            ],
            bad_indicators=[
                "States uncertain facts with certainty",
                "Fabricates plausible-sounding information when data missing",
                "Ignores conflicts or contradictions",
                "Uses definitive language despite low confidence"
            ]
        )

        prompt = f"""
You are evaluating whether an AI system response demonstrates EPISTEMIC HUMILITY.

**Vision Principle**: "The system should know what it doesn't know"

**Context**:
- Confidence score: {confidence}
- Memory age: {context.get('memory_age_days', 'N/A')} days
- Conflicts detected: {context.get('conflicts_detected', [])}
- Data availability: {context.get('data_availability', 'unknown')}

**System Response**:
"{response}"

**Evaluation Criteria**:
Good indicators:
{chr(10).join('- ' + i for i in criteria.good_indicators)}

Bad indicators:
{chr(10).join('- ' + i for i in criteria.bad_indicators)}

**Task**: Evaluate this response on a scale of 0.0 (complete violation) to 1.0 (perfect alignment).

Consider:
1. Does the tone match the confidence level? (Low confidence should have hedging language)
2. Are sources/dates cited for uncertain information?
3. Are conflicts acknowledged explicitly?
4. Does it admit lack of information rather than fabricate?

**Output JSON**:
{{
  "score": <float 0.0-1.0>,
  "reasoning": "<2-3 sentence explanation>",
  "violations": ["<specific violation 1>", "<specific violation 2>"],
  "passes": <true if score >= 0.8>
}}
"""

        response_json = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        result_dict = json.loads(response_json.choices[0].message.content)

        return EvaluationResult(
            principle=VisionPrinciple.EPISTEMIC_HUMILITY,
            score=result_dict["score"],
            reasoning=result_dict["reasoning"],
            violations=result_dict.get("violations", []),
            passes=result_dict["passes"]
        )

    async def evaluate_dual_truth_equilibrium(
        self,
        response: str,
        db_facts: List[Dict],
        memory_facts: List[Dict]
    ) -> EvaluationResult:
        """
        Evaluate if response maintains dual truth equilibrium.

        Vision: "Database (correspondence truth) + Memory (contextual truth) in equilibrium"

        Good indicators:
        - DB facts always included when available
        - Memory enriches but doesn't override DB
        - Conflicts between DB and memory made explicit
        - Response grounds in DB first, then enriches with memory

        Bad indicators:
        - DB facts missing when available
        - Memory overrides current DB state
        - Conflicts ignored
        - Pure memory response when DB data exists
        """
        prompt = f"""
You are evaluating whether an AI system response maintains DUAL TRUTH EQUILIBRIUM.

**Vision Principle**: "Database (correspondence truth) + Memory (contextual truth) in equilibrium"

**Database Facts** (authoritative, current state):
{json.dumps(db_facts, indent=2)}

**Memory Facts** (contextual, learned understanding):
{json.dumps(memory_facts, indent=2)}

**System Response**:
"{response}"

**Evaluation Criteria**:
1. Are DB facts included in the response? (Ground first)
2. Does memory enrich without overriding DB? (Enrich second)
3. If DB and memory conflict, is it acknowledged?
4. Does response prioritize DB for current state, memory for context?

**Good Response Pattern**:
"According to our records [DB], invoice INV-1009 is due Sept 30 [DB fact].
Based on past interactions [Memory], customer typically pays 2-3 days late [Memory context]."

**Bad Response Pattern**:
"Customer prefers NET30 terms [Memory only, ignoring DB shows NET15]"

**Output JSON**:
{{
  "score": <float 0.0-1.0>,
  "reasoning": "<explanation>",
  "violations": ["<violations if any>"],
  "passes": <true if score >= 0.8>
}}
"""

        response_json = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        result_dict = json.loads(response_json.choices[0].message.content)

        return EvaluationResult(
            principle=VisionPrinciple.DUAL_TRUTH,
            score=result_dict["score"],
            reasoning=result_dict["reasoning"],
            violations=result_dict.get("violations", []),
            passes=result_dict["passes"]
        )

    async def evaluate_explainability(
        self,
        response: str,
        provenance_data: Dict
    ) -> EvaluationResult:
        """
        Evaluate if response is explainable (traceable to sources).

        Vision: "Transparency as trust - every response traceable"

        Good indicators:
        - Cites specific sources (memory IDs, DB tables)
        - Can explain why information was retrieved
        - Provenance clear for all facts stated
        - User can verify claims

        Bad indicators:
        - Unsourced assertions
        - Can't trace facts to memories/DB
        - Vague attributions ("we know that...")
        """
        prompt = f"""
You are evaluating whether an AI system response is EXPLAINABLE.

**Vision Principle**: "Transparency as trust - every response traceable to sources"

**System Response**:
"{response}"

**Available Provenance Data**:
{json.dumps(provenance_data, indent=2)}

**Evaluation**:
1. Does response cite sources for factual claims?
2. Can facts be traced to specific DB records or memories?
3. Is attribution clear and verifiable?
4. Could a user verify the claims made?

**Good patterns**:
- "According to invoice INV-1009 [cites DB source]..."
- "Based on our conversation from Sept 15 [cites date/session]..."
- "Customer preference confirmed 3x [explains confidence]..."

**Bad patterns**:
- "We know the customer prefers..." [unsourced]
- Vague claims without attribution
- Facts stated without provenance

**Output JSON**:
{{
  "score": <float 0.0-1.0>,
  "reasoning": "<explanation>",
  "violations": ["<violations>"],
  "passes": <true if score >= 0.8>
}}
"""

        response_json = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.0
        )

        result_dict = json.loads(response_json.choices[0].message.content)

        return EvaluationResult(
            principle=VisionPrinciple.EXPLAINABILITY,
            score=result_dict["score"],
            reasoning=result_dict["reasoning"],
            violations=result_dict.get("violations", []),
            passes=result_dict["passes"]
        )

    async def generate_edge_case_tests(
        self,
        principle: VisionPrinciple,
        count: int = 5
    ) -> List[Dict]:
        """
        Use LLM to generate edge case test scenarios for a vision principle.

        Why LLM?
        - Can think creatively about edge cases humans might miss
        - Understands semantic nuances of principles
        - Generates realistic but challenging scenarios

        Returns: List of test scenarios with inputs and expected behaviors
        """
        principle_descriptions = {
            VisionPrinciple.EPISTEMIC_HUMILITY: """
                System demonstrates epistemic humility - knowing what it doesn't know.
                Low confidence → hedging language.
                No data → acknowledge gap, don't fabricate.
                Conflicts → show both sources.
            """,
            VisionPrinciple.DUAL_TRUTH: """
                Database (correspondence truth) + Memory (contextual truth) in equilibrium.
                Ground in DB first, enrich with memory second.
                Never override DB with memory.
                Conflicts made explicit.
            """,
            VisionPrinciple.GRACEFUL_FORGETTING: """
                Forgetting is essential to intelligence.
                Decay unreinforced memories.
                Consolidate many episodes into summaries.
                Don't delete - deprioritize and abstract.
            """
        }

        prompt = f"""
You are a QA engineer designing edge case tests for an AI memory system.

**Vision Principle**: {principle.value}

**Principle Description**:
{principle_descriptions.get(principle, "Unknown principle")}

**Task**: Generate {count} challenging edge case test scenarios that could reveal
violations of this principle.

For each scenario, provide:
1. **Setup**: Initial state (DB data, memories, context)
2. **User Query**: What user asks
3. **Expected Behavior**: How system should respond to align with principle
4. **Failure Mode**: What wrong behavior would look like

**Output JSON array**:
[
  {{
    "scenario_name": "<descriptive name>",
    "setup": {{
      "db_data": {{}},
      "memories": [],
      "context": {{}}
    }},
    "user_query": "<query text>",
    "expected_behavior": "<detailed expectation>",
    "failure_mode": "<what violation looks like>",
    "why_challenging": "<why this tests edge of principle>"
  }},
  ...
]

Make scenarios REALISTIC and CHALLENGING - think about corner cases, conflicts, ambiguities.
"""

        response_json = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7  # Higher temperature for creativity
        )

        result = json.loads(response_json.choices[0].message.content)
        return result.get("scenarios", [])

    async def evaluate_comprehensive_alignment(
        self,
        response: str,
        context: Dict,
        principles: List[VisionPrinciple]
    ) -> Dict[VisionPrinciple, EvaluationResult]:
        """
        Evaluate response against multiple vision principles.

        Returns comprehensive alignment report.
        """
        results = {}

        for principle in principles:
            if principle == VisionPrinciple.EPISTEMIC_HUMILITY:
                result = await self.evaluate_epistemic_humility(
                    response,
                    context.get("confidence", 0.0),
                    context
                )
            elif principle == VisionPrinciple.DUAL_TRUTH:
                result = await self.evaluate_dual_truth_equilibrium(
                    response,
                    context.get("db_facts", []),
                    context.get("memory_facts", [])
                )
            elif principle == VisionPrinciple.EXPLAINABILITY:
                result = await self.evaluate_explainability(
                    response,
                    context.get("provenance_data", {})
                )
            # Add more principles as needed

            results[principle] = result

        return results


# ============================================================================
# Test Generation Helpers
# ============================================================================

class VisionAlignedTestGenerator:
    """
    Generates tests that verify vision alignment.

    Uses LLM to:
    1. Generate edge cases from principles
    2. Create realistic conversation flows
    3. Design scenarios that test philosophical boundaries
    """

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.client = openai.AsyncOpenAI()

    async def generate_conversation_flow_test(
        self,
        scenario_description: str,
        expected_learning: str
    ) -> Dict:
        """
        Generate multi-turn conversation test that validates learning behavior.

        Example:
        - Turn 1: User states preference
        - Turn 2: System should remember without re-asking
        - Turn 3: System should apply learned preference
        """
        prompt = f"""
You are designing a multi-turn conversation test for an AI memory system.

**Scenario**: {scenario_description}

**Expected Learning**: {expected_learning}

**Task**: Design a 3-5 turn conversation that tests if the system learns correctly.

**Output JSON**:
{{
  "test_name": "<descriptive name>",
  "turns": [
    {{
      "turn": 1,
      "user_message": "<what user says>",
      "expected_system_behavior": "<what system should do>",
      "memories_created": ["<expected memories>"],
      "assertions": ["<what to verify>"]
    }},
    ...
  ],
  "final_validation": "<how to verify learning succeeded>"
}}
"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )

        return json.loads(response.choices[0].message.content)


# ============================================================================
# Usage Examples (for documentation)
# ============================================================================

async def example_epistemic_humility_test():
    """
    Example: Test that system demonstrates epistemic humility with low confidence
    """
    evaluator = LLMTestEvaluator()

    # System response to evaluate
    response = "I don't have reliable information about TC Boiler's payment terms. Our records show a preference mentioned once on May 10, but it hasn't been confirmed since. I'd recommend verifying with them before assuming NET30."

    # Context
    context = {
        "confidence": 0.4,  # Low confidence
        "memory_age_days": 120,  # Aged memory
        "data_availability": "single_unconfirmed_statement"
    }

    # Evaluate
    result = await evaluator.evaluate_epistemic_humility(response, 0.4, context)

    # Assert passes
    assert result.passes, f"Epistemic humility test failed: {result.reasoning}"
    assert result.score >= 0.8


async def example_generate_edge_cases():
    """
    Example: Generate edge case tests for dual truth principle
    """
    evaluator = LLMTestEvaluator()

    scenarios = await evaluator.generate_edge_case_tests(
        principle=VisionPrinciple.DUAL_TRUTH,
        count=5
    )

    # LLM generates scenarios like:
    # - DB shows invoice paid, memory says "customer typically late" → test conflict handling
    # - DB has no customer data, memory has rich profile → test DB-first grounding
    # - DB updated recently, memory is stale → test DB priority

    for scenario in scenarios:
        print(f"Generated test: {scenario['scenario_name']}")
        print(f"Challenge: {scenario['why_challenging']}")


# Example generated test (what LLM might produce):
EXAMPLE_GENERATED_TEST = {
    "scenario_name": "Stale Memory vs Fresh DB Update",
    "setup": {
        "db_data": {
            "sales_order": {
                "so_id": "SO-1001",
                "status": "fulfilled",
                "updated_at": "2025-09-20"
            }
        },
        "memories": [
            {
                "fact": "SO-1001 is in_fulfillment",
                "confidence": 0.7,
                "last_validated_at": "2025-09-10"  # 10 days old
            }
        ]
    },
    "user_query": "What's the status of SO-1001?",
    "expected_behavior": "Should report 'fulfilled' from DB, acknowledge memory discrepancy, log conflict",
    "failure_mode": "Reports 'in_fulfillment' from memory, ignoring fresher DB state",
    "why_challenging": "Tests whether system truly prioritizes DB over memory when states diverge"
}
