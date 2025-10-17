# Hedging Language Implementation Options

## What is Hedging Language?

**Hedging language** adapts the LLM's response tone to match the confidence level of the data it's using. It's about **HOW** the system speaks, not WHAT it says.

## Examples

### Without Hedging (Current)
```
User: "What are TC Boiler's payment terms?"
System: "TC Boiler uses NET30 payment terms."
(confidence=0.4, 95 days old)
```

### With Hedging (Proposed)
```
User: "What are TC Boiler's payment terms?"
System: "Based on a conversation from 3 months ago, TC Boiler may use NET30 payment terms, though this hasn't been confirmed recently. Would you like me to verify this information?"
(confidence=0.4, 95 days old)
```

## Implementation Approaches

### Option 1: Prompt Engineering (Simple)

**Approach**: Add confidence metadata to the system prompt and instruct the LLM to modulate language.

**Implementation** (`conversation_context_reply.py:110-125`):
```python
# Section 3: Retrieved memories (contextual)
if self.retrieved_memories:
    sections.append("=== RETRIEVED MEMORIES (Contextual) ===")
    for mem in self.retrieved_memories:
        # Classify confidence level
        if mem.confidence < 0.5:
            confidence_label = "LOW CONFIDENCE"
        elif mem.confidence < 0.7:
            confidence_label = "MEDIUM CONFIDENCE"
        else:
            confidence_label = "HIGH CONFIDENCE"

        sections.append(
            f"[{mem.memory_type}] ({confidence_label}: {mem.confidence:.2f})\n"
            f"- {mem.content}"
        )
    sections.append("")

# Update response guidelines
sections.append(
    "=== RESPONSE GUIDELINES ===\n"
    "- Adapt your language to match confidence levels:\n"
    "  - LOW CONFIDENCE (<0.5): Use hedging ('may', 'possibly', 'based on limited info')\n"
    "  - MEDIUM CONFIDENCE (0.5-0.7): Use moderate language ('likely', 'typically', 'according to')\n"
    "  - HIGH CONFIDENCE (>0.7): Use confident language ('is', 'has', 'uses')\n"
    "- Be concise and direct (2-3 sentences preferred)\n"
    "- Cite sources when relevant (e.g., 'According to Invoice INV-1009...')\n"
    "- If uncertain or data is old, acknowledge it\n"
    "- If database and memory conflict, prefer database but mention the discrepancy\n"
    "- Use domain facts to answer current state, memories for preferences/context\n"
    "- Do not make up information - only use the facts and memories provided"
)
```

**Pros**:
- ✅ Simple (2 hours implementation)
- ✅ Uses LLM's natural language generation
- ✅ Flexible - adapts to context

**Cons**:
- ❌ Non-deterministic (LLM might not always hedge)
- ❌ Requires calibration (what confidence threshold triggers hedging?)
- ❌ Hard to test (LLM output varies)

**Effort**: 2-3 hours
**Phase**: Recommend Phase 2 (needs calibration)

---

### Option 2: Template-Based (Deterministic)

**Approach**: Pre-format memory content with explicit hedging before sending to LLM.

**Implementation**:
```python
def _format_memory_with_hedging(self, mem: RetrievedMemory) -> str:
    """Format memory content with confidence-appropriate hedging."""

    # Determine hedging template
    if mem.confidence < 0.5:
        template = "It's possible that {content} (low confidence, last confirmed {age} ago)"
    elif mem.confidence < 0.7:
        template = "Based on past information, {content} (medium confidence)"
    else:
        template = "{content}"

    # Calculate age
    age_text = self._format_age(mem.created_at) if hasattr(mem, 'created_at') else "some time"

    return template.format(content=mem.content, age=age_text)

# In to_system_prompt():
if self.retrieved_memories:
    sections.append("=== RETRIEVED MEMORIES (Contextual) ===")
    for mem in self.retrieved_memories:
        formatted_content = self._format_memory_with_hedging(mem)
        sections.append(f"[{mem.memory_type}] {formatted_content}")
    sections.append("")
```

**Pros**:
- ✅ Deterministic (always applies hedging correctly)
- ✅ Testable (check exact string output)
- ✅ Predictable user experience

**Cons**:
- ❌ Rigid (might sound formulaic)
- ❌ Less natural than LLM-generated hedging
- ❌ Still needs threshold calibration

**Effort**: 3-4 hours
**Phase**: Could be Phase 1 (deterministic, testable)

---

### Option 3: Hybrid (Best of Both)

**Approach**: Use templates for structure, LLM for natural phrasing.

**Implementation**:
```python
# Pre-process memories with confidence labels
formatted_memories = []
for mem in self.retrieved_memories:
    if mem.confidence < 0.5:
        label = "⚠️ UNCERTAIN"
    elif mem.confidence < 0.7:
        label = "⚡ MODERATE"
    else:
        label = "✓ CONFIDENT"

    formatted_memories.append({
        "label": label,
        "content": mem.content,
        "confidence": mem.confidence
    })

# In system prompt:
sections.append("=== RETRIEVED MEMORIES (Contextual) ===")
for mem_data in formatted_memories:
    sections.append(
        f"{mem_data['label']} (confidence: {mem_data['confidence']:.2f})\n"
        f"- {mem_data['content']}"
    )

sections.append(
    "\n**How to use these confidence labels**:\n"
    "- ⚠️ UNCERTAIN: Use tentative language, suggest verification\n"
    "- ⚡ MODERATE: Mention source and acknowledge limitations\n"
    "- ✓ CONFIDENT: State directly, cite source"
)
```

**Pros**:
- ✅ Clear signals to LLM
- ✅ Natural phrasing from LLM
- ✅ Visual indicators (emojis help LLM understand)

**Cons**:
- ❌ Still non-deterministic
- ❌ Requires threshold calibration

**Effort**: 2-3 hours
**Phase**: Recommend Phase 2 (needs calibration)

---

## Calibration Requirements

**All approaches need answers to**:
1. What confidence threshold triggers hedging? (0.5? 0.6? 0.7?)
2. What about age? Does a 90-day-old memory with 0.8 confidence need hedging?
3. Do users find hedging helpful or annoying?
4. Does hedging make the system sound less authoritative?

**You can't answer these without real usage data.**

---

## Test Compatibility

### Current Philosophy Test Expectations

The test `test_low_confidence_triggers_hedging_language` uses an **LLM evaluator** to check if the response matches the confidence level:

```python
# Test expects:
result = await evaluator.evaluate_response(
    system_response=data["response"],
    expected_behavior="System uses hedging language appropriate for low confidence",
    principle=VisionPrinciple.EPISTEMIC_HUMILITY,
    context={
        "confidence": data["augmentation"]["memories_retrieved"][0]["confidence"],
        "age_days": 95
    }
)

assert result.passes, f"Hedging language not detected: {result.reasoning}"
```

This test is **non-deterministic** (depends on LLM evaluation), so even with perfect implementation, it might occasionally fail.

---

## My Recommendation

### Phase 1: **Defer** hedging language

**Why**:
1. **Gap acknowledgment (completed) is higher priority** - Preventing hallucination is critical, hedging is UX polish
2. **Needs calibration** - You don't know what confidence thresholds to use without real usage
3. **Non-deterministic testing** - Hard to validate reliably
4. **Data structures already correct** - The system tracks confidence correctly, just doesn't express it verbally yet

### Phase 2: **Implement** after gathering data

**Approach**:
1. Ship Phase 1 with confidence tracking but no verbal hedging
2. Collect usage logs: Which low-confidence responses caused problems?
3. Calibrate thresholds based on real accuracy data
4. Implement Option 1 (Prompt Engineering) or Option 3 (Hybrid)
5. A/B test with real users to measure impact

---

## If You Want It In Phase 1 Anyway

If you decide hedging is essential for Phase 1 completion:

**I recommend**: **Option 2 (Template-Based)**
- **Why**: Deterministic, testable, doesn't require calibration (use conservative thresholds)
- **Thresholds** (conservative):
  - < 0.6: Hedge ("may", "possibly")
  - 0.6-0.8: Moderate ("likely", "typically")
  - > 0.8: Confident
- **Effort**: 3-4 hours
- **Test approach**: Mark `test_low_confidence_triggers_hedging_language` as Phase 1 (with simpler assertions)

---

## Implementation Checklist (If Phase 1)

If you decide to implement for Phase 1:

- [ ] Choose approach (recommend Option 2)
- [ ] Update `ReplyContext.to_system_prompt()` with hedging logic
- [ ] Add helper method `_format_memory_with_hedging()`
- [ ] Update philosophy test to check for specific hedging phrases
- [ ] Test with real E2E scenario
- [ ] Document hedging thresholds in `HEURISTICS_CALIBRATION.md`

**Estimated time**: 3-4 hours total

---

## Summary Table

| Approach | Effort | Phase | Deterministic | Natural Language | Testable |
|----------|--------|-------|---------------|------------------|----------|
| **Option 1: Prompt Engineering** | 2-3h | Phase 2 | ❌ | ✅ | ⚠️ |
| **Option 2: Template-Based** | 3-4h | Could be Phase 1 | ✅ | ⚠️ | ✅ |
| **Option 3: Hybrid** | 2-3h | Phase 2 | ❌ | ✅ | ⚠️ |
| **Defer to Phase 2** | 0h | - | - | - | - |

**My vote**: Defer to Phase 2. You've already implemented the critical piece (gap acknowledgment). Hedging is polish that benefits from calibration data.
