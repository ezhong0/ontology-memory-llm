# E2E Scenario Comparison: ProjectDescription.md vs Implementation

**Date**: 2025-10-16
**Purpose**: Verify all scenarios match ProjectDescription.md exactly

## Comparison Table

| # | ProjectDescription.md | My Implementation | Match? | Notes |
|---|----------------------|-------------------|--------|-------|
| 1 | Overdue invoice follow-up with preference recall | test_scenario_01_overdue_invoice_with_preference_recall | ✅ YES | Exact match |
| 2 | Reschedule work order based on technician availability | test_scenario_02_work_order_rescheduling | ✅ YES | Exact match |
| 3 | Ambiguous entity disambiguation (two customers) | test_scenario_03_ambiguous_entity_disambiguation | ✅ YES | Exact match |
| 4 | NET terms learning from conversation | test_scenario_04_net_terms_learning_from_conversation | ✅ YES | Exact match |
| 5 | Partial payments and balance calculation | test_scenario_05_partial_payments_and_balance | ✅ YES | Exact match |
| 6 | SLA breach detection from tasks + orders | test_scenario_06_sla_breach_detection | ✅ YES | Exact match |
| 7 | Conflicting memories → consolidation rules | test_scenario_07_conflicting_memories_consolidation | ✅ YES | Exact match |
| 8 | Multilingual/alias handling | test_scenario_08_multilingual_alias_handling | ✅ YES | Exact match |
| 9 | Cold-start grounding to DB facts | test_scenario_09_cold_start_grounding_to_db | ✅ YES | Exact match |
| 10 | Active recall to validate stale facts | test_scenario_10_active_recall_for_stale_facts | ✅ YES | Exact match |
| 11 | Cross-object reasoning (SO → WO → Invoice) | test_scenario_11_cross_object_reasoning | ✅ YES | Exact match |
| 12 | Conversation-driven entity linking (fuzzy match) | test_scenario_12_fuzzy_match_alias_learning | ✅ YES | Exact match |
| 13 | Policy & PII guardrail memory | test_scenario_13_pii_guardrail_memory | ✅ YES | Exact match |
| 14 | Session window consolidation example | test_scenario_14_session_window_consolidation | ✅ YES | Exact match |
| 15 | Audit trail / explainability | test_scenario_17_explainability_provenance_tracking | ⚠️ NUMBERING | Implemented as #17 (numbering mismatch) |
| 16 | Reminder creation from conversational intent | ❌ NOT IMPLEMENTED | ❌ NO | **MISSING SCENARIO** |
| 17 | Error handling when DB and memory disagree | test_scenario_15_memory_vs_db_conflict_trust_db | ⚠️ NUMBERING | Implemented as #15 (numbering mismatch) |
| 18 | Task completion via conversation | ❌ NOT IMPLEMENTED | ❌ NO | **MISSING SCENARIO** |

## Issues Identified

### 1. Numbering Mismatch
- **Scenario 15** (ProjectDescription): "Audit trail / explainability"
  - Implemented as: `test_scenario_17_explainability_provenance_tracking`
  - Fix: Rename to `test_scenario_15_...`

- **Scenario 17** (ProjectDescription): "Error handling when DB and memory disagree"
  - Implemented as: `test_scenario_15_memory_vs_db_conflict_trust_db`
  - Fix: Rename to `test_scenario_17_...`

### 2. Missing Scenarios

#### Missing: Scenario 16 - Reminder creation from conversational intent

**ProjectDescription.md text:**
```
User: "If an invoice is still open 3 days before due, remind me."
Expected: Store semantic policy memory; on future /chat calls that involve
invoices, system checks due dates and surfaces proactive notices.
```

**What I implemented instead:**
- `test_scenario_16_graceful_forgetting_consolidation` - This is NOT in ProjectDescription.md
- This appears to be a duplicate of consolidation logic already tested in Scenario 7 and 14

**Action needed:** Replace with correct Scenario 16

#### Missing: Scenario 18 - Task completion via conversation

**ProjectDescription.md text:**
```
User: "Mark the SLA investigation task for Kai Media as done and summarize
what we learned."
Expected: Return SQL patch suggestion (or mocked effect), store the summary
as semantic memory for future reasoning.
```

**What I implemented instead:**
- `test_scenario_18_privacy_user_scoped_memories` - This is NOT in ProjectDescription.md
- Privacy/user-scoping is a requirement throughout (user_id filtering), not a distinct scenario

**Action needed:** Replace with correct Scenario 18

### 3. Incorrectly Added Scenarios

#### test_scenario_16_graceful_forgetting_consolidation
- **Not in ProjectDescription.md**
- "Graceful Forgetting" is a vision principle, not a scenario
- Consolidation is already tested in:
  - Scenario 7: "Conflicting memories → consolidation rules"
  - Scenario 14: "Session window consolidation example"
- This is redundant

#### test_scenario_18_privacy_user_scoped_memories
- **Not in ProjectDescription.md**
- User scoping is a cross-cutting concern, not a distinct user journey
- Already validated implicitly by `user_id` parameter in all scenarios

## Verification Against Existing Design

Let me verify each scenario against DESIGN.md to ensure no additional features are required:

### Scenarios 1-14: Already Verified ✅
These match ProjectDescription.md exactly and map to existing design features.

### Scenario 15 (Explainability) - Check Design
**Requirement**: `/explain` endpoint to show memory IDs, similarity scores, chat events
**Design Status**: Check if explainability/provenance is in DESIGN.md

### Scenario 16 (Reminders) - Check Design
**Requirement**: Store policy memory for proactive notifications
**Design Status**: Check if policy memory + proactive checking is in DESIGN.md

### Scenario 17 (DB Conflict) - Check Design
**Requirement**: Detect memory vs DB conflict, trust DB, log conflict
**Design Status**: Conflict detection exists in Phase 1B ✅

### Scenario 18 (Task Completion) - Check Design
**Requirement**: Store semantic memory from task completion
**Design Status**: Semantic extraction exists in Phase 1B ✅

## Next Steps

1. **Rename scenarios 15 ↔ 17** to match ProjectDescription.md numbering
2. **Replace scenario 16** with "Reminder creation from conversational intent"
3. **Replace scenario 18** with "Task completion via conversation"
4. **Verify against DESIGN.md** that scenarios 16 and 18 don't require new features
5. **Update documentation** to reflect corrections

## Summary

**Status**: 14/18 scenarios match ProjectDescription.md exactly
**Issues**:
- 2 numbering mismatches (cosmetic)
- 2 missing scenarios (#16, #18)
- 2 incorrectly added scenarios (not in ProjectDescription)

**Action**: Fix numbering and implement missing scenarios 16 and 18
