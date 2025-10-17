# Vision Violation Fixes: From Overfitting to Learning

**Philosophy**: The vision describes an adaptive, learning system. The implementation has hardcoded heuristics. This document provides a phased approach to align implementation with vision.

---

## Executive Summary

**Current State**: Codebase has solid architecture but violates core vision principles through:
- ❌ **Epistemic Humility**: `confidence=1.0` appears 4+ times (vision says max 0.95)
- ❌ **Overfitting**: Hardcoded keyword lists for intent classification
- ❌ **No Learning**: System told what patterns exist, not discovering them
- ❌ **Brittle Matching**: Hard string comparisons instead of fuzzy/probabilistic

**Vision State**: System should:
- ✅ **Learn patterns from usage** ("Track which memories prove useful")
- ✅ **Adapt automatically** ("Domain-specific learning happens through usage patterns")
- ✅ **Maintain epistemic humility** ("Max confidence = 0.95, never 100% certain")
- ✅ **Be extensible** ("Add queries via registry, not hardcoded if/elif")

**Impact**: 109 hardcoded confidence values, 6+ hardcoded intent keyword lists, 3 major services with overfitting

---

## Critical Violations (Must Fix)

### 1. Epistemic Humility: confidence=1.0

**Vision Principle** (lines 386-421 in VISION.md):
> "Max confidence = 0.95 (never 100%)" - "The system should know what it doesn't know"

**Violations Found**:

```python
# src/config/heuristics.py:39
CONFIDENCE_EXACT_MATCH = 1.0  # ❌ Even exact matches can have errors

# src/application/use_cases/process_chat_message.py:325
new_confidence = 1.0  # DB is authoritative  # ❌ DB not infallible

# src/domain/services/debug_trace_service.py:149
confidence=1.0  # ❌ Debug traces shouldn't claim perfect certainty

# src/demo/services/scenario_loader.py:492
confidence=1.0  # ❌ Demo data claiming 100% certainty
```

**Why This Violates Vision**:
- **Database facts can be stale** (Vision lines 347-365: "Staleness Problem")
- **Data entry errors exist** (Vision line 11: correspondence truth ≠ infallible)
- **Truth is temporal** (Vision lines 337-341: "Truth is temporal... false at time T2")
- **Epistemic humility is fundamental** (Vision line 20: "MAX_CONFIDENCE = 0.95")

**Philosophical Issue**:
The vision explicitly states the truth hierarchy (lines 186-199):
1. Current DB facts - **Authoritative, NOT perfectly certain**
2. Recently validated memories - High confidence
3. Highly reinforced memories - Stable facts

Notice: "Authoritative" ≠ "100% certain". The DB is the **most trusted source**, but epistemic humility applies to ALL sources.

---

### 2. Intent Classification: Pure Overfitting

**Vision Principle** (lines 507-522):
> "Adaptive Behavior: The system adapts to its user and domain... This adaptation happens **automatically through usage patterns** - no explicit configuration needed."

**Violation 1**: `src/domain/services/domain_augmentation_service.py:95-134`

```python
def _classify_intent(self, query_text: str) -> str:
    """Simple intent classification."""
    query_lower = query_text.lower()

    # ❌ HARDCODED KEYWORD LISTS - This is overfitting!
    if any(word in query_lower for word in ["invoice", "payment", "owe", "balance", "due", "pay"]):
        return "financial"
    elif any(word in query_lower for word in ["work order", "wo", "technician", "schedule"]):
        return "work_orders"
    elif any(word in query_lower for word in ["task", "todo", "doing", "complete"]):
        return "tasks"
    # ... 30 more lines of hardcoded keywords
```

**Violation 2**: `src/domain/services/procedural_memory_service.py:205-261`

```python
def _classify_intent(self, content: str) -> str:
    # ❌ SAME PATTERN - Different service, same anti-pattern!
    if any(word in content for word in ["payment", "invoice", "bill", "pay", "paid"]):
        if "history" in content or "past" in content:
            return "query_payment_history"
        elif "open" in content or "outstanding" in content:
            return "query_open_payments"
    # ... nested if/elif chains
```

**Violation 3**: `src/domain/services/procedural_memory_service.py:258-272`

```python
def _extract_topics(self, content: str) -> list[str]:
    # ❌ HARDCODED TOPIC KEYWORDS
    topic_keywords = {
        "payments": ["payment", "invoice", "bill", "pay", "paid", "charge"],
        "orders": ["order", "purchase", "transaction", "buy", "bought"],
        "products": ["product", "item", "inventory", "stock", "merchandise"],
        # ... more hardcoded dictionaries
    }
```

**Why This Violates Vision**:
1. **Not learning**: System doesn't discover patterns, they're hardcoded
2. **Not adaptive**: Adding new domain = code changes, not learning
3. **Brittle**: Synonym/variation = missed intent (e.g., "remittance" not in "payment" list)
4. **Not emergent**: Intelligence should emerge from simple rules + usage, not hardcoding

**Vision says** (lines 467-485):
> "Intelligence isn't programmed - it **emerges from interaction of simple mechanisms**... These simple rules, applied consistently, yield **emergent intelligent behavior**"

Hardcoded keywords ≠ emergent behavior. This is programmed behavior.

---

### 3. Query Dispatch: Inflexible if/elif Chains

**Vision Principle** (lines 42-44 in domain_augmentation_service.py):
> "Philosophy: Beautiful solutions are declarative and composable... **Extensible (add queries via registry)**"

**Violation**: `src/domain/services/domain_augmentation_service.py:98-112`

```python
# ❌ HARDCODED DISPATCH - Not extensible!
for query_type, params in queries_to_run:
    if query_type == "invoice_status":
        tasks.append(self.domain_db.get_invoice_status(**params))
    elif query_type == "order_chain":
        tasks.append(self.domain_db.get_order_chain(**params))
    elif query_type == "sla_risk":
        tasks.append(self.domain_db.get_sla_risks(**params))
    # ... elif elif elif
    else:
        # Extensibility: custom queries
        tasks.append(self.domain_db.execute_custom_query(query_type, params))
```

**The Irony**: Comment says "Extensibility: custom queries" but you must edit source code to add a new query type!

**Why This Violates Vision**:
- Not a registry pattern (claimed in docs)
- Adding query = code change, not configuration
- Violates Open/Closed Principle
- Not composable

---

## Design Philosophy: The Right Approach

### Core Principle: Bootstrap → Learn → Adapt

The vision describes a **3-stage evolution**:

```
Phase 1: Bootstrap (Necessary Evil)
├─ Hardcoded heuristics to get started
├─ Explicitly marked as temporary
└─ Minimal, documented assumptions

Phase 2: Learning (Transition)
├─ Track what works (usage patterns)
├─ Measure accuracy of heuristics
└─ Build training data from real usage

Phase 3: Adaptive (Vision Realized)
├─ Learned classifiers replace heuristics
├─ Self-calibrating confidence
└─ Automatic pattern discovery
```

**Current Problem**: We're stuck in Phase 1 with no path to Phase 2/3.

---

## The Fix: 3-Phased Approach

### Phase 0: Critical Fixes (1-2 hours)

**Goal**: Fix epistemic humility violations immediately

**Changes**:

1. **src/config/heuristics.py:39**
   ```python
   # BEFORE
   CONFIDENCE_EXACT_MATCH = 1.0

   # AFTER
   CONFIDENCE_EXACT_MATCH = 0.95  # Epistemic humility: even exact matches can have errors
   ```

2. **src/application/use_cases/process_chat_message.py:325**
   ```python
   # BEFORE
   new_confidence = 1.0  # DB is authoritative

   # AFTER
   new_confidence = heuristics.MAX_CONFIDENCE  # DB is authoritative, not infallible
   ```

3. **All other instances**:
   ```bash
   # Find and replace all confidence=1.0
   grep -r "confidence.*=.*1\.0" src --include="*.py"
   # Replace with heuristics.MAX_CONFIDENCE or 0.93-0.95
   ```

**Tests**: Must verify no regressions
```bash
poetry run pytest tests/e2e/test_scenarios.py -v
make test
```

**Commit**: `fix(confidence): enforce epistemic humility (max 0.95, never 1.0)`

---

### Phase 1: Configuration-Based Heuristics (4-6 hours)

**Goal**: Move hardcoded lists to configuration, mark as temporary

**Step 1.1: Intent Keywords Configuration**

Create: `src/config/intent_keywords.py`
```python
"""Intent classification keywords.

⚠️  PHASE 1 BOOTSTRAP: These are hardcoded heuristics.
    PHASE 2 PLAN: Replace with learned intent classifier from usage patterns.

Vision Principle: "Learn What Matters" - track which patterns prove useful,
    weight future classification toward proven patterns.

See: docs/implementation/VISION_VIOLATION_FIXES.md
"""

from typing import Dict, List

# Intent keyword mappings (Phase 1 bootstrap)
FINANCIAL_KEYWORDS = ["invoice", "payment", "owe", "balance", "due", "pay", "paid", "bill"]
WORK_ORDER_KEYWORDS = ["work order", "wo", "technician", "schedule", "reschedule", "pick-pack"]
TASK_KEYWORDS = ["task", "todo", "doing", "complete", "mark as done", "investigation"]
OPERATIONAL_KEYWORDS = ["order", "status", "delivery", "shipment"]
SLA_KEYWORDS = ["sla", "risk", "breach", "late", "overdue", "urgent"]

# Topic keyword mappings (Phase 1 bootstrap)
TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "payments": ["payment", "invoice", "bill", "pay", "paid", "charge", "remittance"],
    "orders": ["order", "purchase", "transaction", "buy", "bought", "so", "sales order"],
    "products": ["product", "item", "inventory", "stock", "merchandise", "sku"],
    "customers": ["customer", "client", "account", "user", "buyer"],
    "shipping": ["ship", "delivery", "shipment", "deliver", "freight", "dispatch"],
    "credit": ["credit", "balance", "limit", "outstanding", "ar", "receivable"],
    "preferences": ["prefer", "like", "want", "need", "requirement", "always", "usually"],
}

# Intent hierarchy (for nested classification)
INTENT_REFINEMENTS: Dict[str, Dict[str, List[str]]] = {
    "financial": {
        "query_payment_history": ["history", "past", "previous"],
        "query_open_payments": ["open", "outstanding", "unpaid"],
        "query_payment": [],  # Default financial
    },
    "operational": {
        "query_order_status": ["status", "where", "track"],
        "query_order_history": ["history", "past", "all orders"],
        "query_order": [],  # Default operational
    },
}

# Phase 2 TODO markers
"""
Phase 2 Replacement Plan:
1. Track intent classification accuracy (log predictions vs actual user satisfaction)
2. Build training dataset: (query_text, user_confirmed_intent) pairs
3. Train lightweight classifier (logistic regression, small NN, or few-shot LLM)
4. A/B test: heuristic vs learned classifier
5. Replace this file when learned classifier achieves >90% accuracy
"""
```

**Step 1.2: Update Services to Use Config**

`src/domain/services/domain_augmentation_service.py`:
```python
from src.config import intent_keywords

def _classify_intent(self, query_text: str) -> str:
    """Classify intent using keyword heuristics.

    ⚠️  Phase 1: Heuristic-based (see intent_keywords.py for replacement plan)
    """
    query_lower = query_text.lower()

    # Use configuration instead of hardcoding
    if any(word in query_lower for word in intent_keywords.FINANCIAL_KEYWORDS):
        return self._refine_intent("financial", query_lower)
    elif any(word in query_lower for word in intent_keywords.WORK_ORDER_KEYWORDS):
        return "work_orders"
    elif any(word in query_lower for word in intent_keywords.TASK_KEYWORDS):
        return "tasks"
    # ... etc

    return "general"

def _refine_intent(self, base_intent: str, query_lower: str) -> str:
    """Refine intent using hierarchy."""
    if base_intent in intent_keywords.INTENT_REFINEMENTS:
        for refined, keywords in intent_keywords.INTENT_REFINEMENTS[base_intent].items():
            if any(kw in query_lower for kw in keywords):
                return refined
    return base_intent
```

**Step 1.3: Query Registry Pattern**

`src/domain/services/domain_augmentation_service.py`:
```python
def __init__(self, domain_db_port: DomainDatabasePort) -> None:
    self.domain_db = domain_db_port

    # ✅ REGISTRY PATTERN - Truly extensible!
    self.query_registry: Dict[str, Callable] = {
        "invoice_status": self.domain_db.get_invoice_status,
        "order_chain": self.domain_db.get_order_chain,
        "sla_risk": self.domain_db.get_sla_risks,
        "work_orders": self.domain_db.get_work_orders_for_customer,
        "tasks": self.domain_db.get_tasks_for_customer,
    }

async def augment(self, entities: list[EntityInfo], query_text: str, intent: str | None = None):
    # ... existing code ...

    # ✅ DECLARATIVE DISPATCH - No if/elif chains!
    tasks = []
    for query_type, params in queries_to_run:
        if query_type in self.query_registry:
            query_fn = self.query_registry[query_type]
            tasks.append(query_fn(**params))
        else:
            # Truly custom queries
            tasks.append(self.domain_db.execute_custom_query(query_type, params))

    results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Step 1.4: Add Usage Tracking (Preparation for Phase 2)**

`src/infrastructure/tracking/intent_tracker.py` (NEW):
```python
"""Track intent classification for Phase 2 learning.

Logs predictions and outcomes to build training dataset.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import structlog

logger = structlog.get_logger()

@dataclass
class IntentPrediction:
    query_text: str
    predicted_intent: str
    confidence: float
    timestamp: datetime
    user_id: str
    session_id: str

class IntentTracker:
    """Track intent predictions for future learning."""

    async def log_prediction(
        self,
        query_text: str,
        predicted_intent: str,
        user_id: str,
        session_id: str,
    ) -> None:
        """Log intent prediction for analysis."""
        logger.info(
            "intent_predicted",
            query_text=query_text[:100],
            predicted_intent=predicted_intent,
            user_id=user_id,
            session_id=session_id,
            # Phase 2: Store in intent_predictions table for training
        )

    async def log_outcome(
        self,
        session_id: str,
        user_satisfaction_signal: str,  # "helpful" | "not_helpful" | "corrected"
    ) -> None:
        """Log user feedback for calibration."""
        logger.info(
            "intent_outcome",
            session_id=session_id,
            outcome=user_satisfaction_signal,
            # Phase 2: Join with predictions to build training data
        )
```

**Commit**: `refactor(intent): move keywords to config, add tracking for Phase 2 learning`

---

### Phase 2: Learned Classifiers (12-16 hours)

**Goal**: Replace heuristics with learned models

**Prerequisites**:
- ≥500 tracked intent predictions
- ≥100 user feedback signals
- Baseline heuristic accuracy measured

**Step 2.1: Build Training Dataset**

`scripts/build_intent_training_data.py`:
```python
"""Build training dataset from tracked predictions + outcomes.

Queries:
1. intent_predictions (query_text, predicted_intent, timestamp, session_id)
2. user_feedback (session_id, satisfaction_signal)

Output: training.jsonl
{"text": "query", "intent": "financial", "weight": 1.0}  # Positive example (user satisfied)
{"text": "query", "intent": "financial", "weight": -1.0}  # Negative example (user corrected)
"""
```

**Step 2.2: Train Lightweight Classifier**

Options (pick one based on data size):

**Option A: Logistic Regression** (if <1000 samples)
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

# Simple, interpretable, fast
vectorizer = TfidfVectorizer(max_features=500)
X = vectorizer.fit_transform(training_texts)
y = training_intents

clf = LogisticRegression(max_iter=1000)
clf.fit(X, y)

# Save model
joblib.dump((vectorizer, clf), "models/intent_classifier_v1.pkl")
```

**Option B: Few-Shot LLM** (if <100 samples but complex intents)
```python
# Use existing LLM with few-shot prompting
prompt = f"""
Classify query intent based on examples:

Examples:
- "Check invoice status" → financial
- "Reschedule work order" → work_orders
- "Mark task done" → tasks

Query: "{query_text}"
Intent: """
```

**Option C: Small NN** (if >2000 samples)
```python
# BERT-tiny or DistilBERT (fast, accurate)
from transformers import AutoModelForSequenceClassification, Trainer
```

**Step 2.3: Implement Learned Intent Service**

`src/domain/services/learned_intent_classifier.py`:
```python
"""Learned intent classifier (Phase 2).

Replaces hardcoded keywords with model trained on usage patterns.
"""

import joblib
from typing import Tuple

class LearnedIntentClassifier:
    """Intent classifier trained on real usage data."""

    def __init__(self, model_path: str):
        self.vectorizer, self.clf = joblib.load(model_path)

    async def classify(self, query_text: str) -> Tuple[str, float]:
        """Classify intent using learned model.

        Returns:
            (intent, confidence) tuple
        """
        X = self.vectorizer.transform([query_text])
        intent = self.clf.predict(X)[0]
        proba = self.clf.predict_proba(X).max()

        return (intent, proba)
```

**Step 2.4: A/B Test Heuristic vs Learned**

`src/config/settings.py`:
```python
USE_LEARNED_INTENT_CLASSIFIER = os.getenv("USE_LEARNED_INTENT", "false").lower() == "true"
INTENT_CLASSIFIER_MODEL_PATH = "models/intent_classifier_v1.pkl"
```

`src/domain/services/domain_augmentation_service.py`:
```python
from src.config import settings

def __init__(self, domain_db_port, intent_classifier=None):
    self.domain_db = domain_db_port

    # Phase 2: Swap classifier based on config
    if settings.USE_LEARNED_INTENT_CLASSIFIER:
        from src.domain.services.learned_intent_classifier import LearnedIntentClassifier
        self.intent_classifier = LearnedIntentClassifier(settings.INTENT_CLASSIFIER_MODEL_PATH)
        logger.info("using_learned_intent_classifier")
    else:
        self.intent_classifier = None  # Use heuristics
        logger.info("using_heuristic_intent_classifier")

async def _classify_intent(self, query_text: str) -> str:
    if self.intent_classifier:
        # ✅ LEARNED CLASSIFICATION
        intent, confidence = await self.intent_classifier.classify(query_text)
        logger.info(
            "intent_classified_learned",
            intent=intent,
            confidence=confidence,
        )
        return intent
    else:
        # Phase 1 heuristic fallback
        return self._classify_intent_heuristic(query_text)
```

**Step 2.5: Calibrate Confidence**

`src/domain/services/confidence_calibrator.py`:
```python
"""Calibrate confidence scores to match actual accuracy.

Vision: "Confidence should be calibrated - over time, learn what
confidence levels actually predict accuracy" (lines 240-243)
"""

from collections import defaultdict
from typing import Dict

class ConfidenceCalibrator:
    """Calibrate predicted confidence to actual accuracy."""

    def __init__(self):
        self.buckets: Dict[float, list[bool]] = defaultdict(list)

    def record(self, predicted_confidence: float, was_correct: bool):
        """Record prediction outcome."""
        bucket = round(predicted_confidence, 1)  # 0.7, 0.8, 0.9, etc.
        self.buckets[bucket].append(was_correct)

    def get_calibrated_confidence(self, predicted: float) -> float:
        """Get calibrated confidence based on observed accuracy."""
        bucket = round(predicted, 1)

        if bucket not in self.buckets or len(self.buckets[bucket]) < 10:
            return predicted  # Not enough data, use predicted

        # Actual accuracy in this bucket
        actual_accuracy = sum(self.buckets[bucket]) / len(self.buckets[bucket])

        # Calibrated confidence = actual observed accuracy
        return actual_accuracy
```

**Commit**: `feat(intent): implement learned intent classifier with calibration (Phase 2)`

---

### Phase 3: Automatic Pattern Discovery (Future)

**Goal**: Fully automated learning (no manual training)

**Techniques**:
1. **Online Learning**: Update model incrementally with each interaction
2. **Active Learning**: System asks for labels when uncertain
3. **Transfer Learning**: Pretrained models + domain adaptation
4. **Meta-Learning**: Learn which patterns generalize across domains

**Example: Self-Improving Intent Classifier**
```python
class SelfImprovingIntentClassifier:
    """Continuously learns from usage without manual retraining."""

    async def classify_and_learn(
        self,
        query_text: str,
        user_feedback: str | None = None,
    ) -> Tuple[str, float]:
        # Predict
        intent, confidence = await self.predict(query_text)

        # If user provides feedback, learn immediately
        if user_feedback:
            await self.online_update(query_text, user_feedback)

        # If uncertain, ask for clarification
        if confidence < 0.6:
            return ("UNCERTAIN", confidence)  # Trigger active learning

        return (intent, confidence)
```

---

## Implementation Checklist

### Phase 0: Critical (Week 1)
- [ ] Replace all `confidence=1.0` with `heuristics.MAX_CONFIDENCE`
- [ ] Update `CONFIDENCE_EXACT_MATCH = 0.95` in heuristics.py
- [ ] Run full test suite, ensure no regressions
- [ ] Commit: "fix(confidence): enforce epistemic humility"

### Phase 1: Configuration (Week 2)
- [ ] Create `src/config/intent_keywords.py` with all keyword lists
- [ ] Add Phase 2 TODO comments to mark temporary heuristics
- [ ] Refactor `_classify_intent()` in both services to use config
- [ ] Implement query registry pattern (replace if/elif dispatch)
- [ ] Add `IntentTracker` for usage logging
- [ ] Instrument all intent predictions with tracking
- [ ] Commit: "refactor(intent): move to config, add Phase 2 tracking"

### Phase 2: Learning (Month 2, after 500+ interactions)
- [ ] Verify ≥500 intent predictions logged
- [ ] Build training dataset from predictions + feedback
- [ ] Train initial classifier (logistic regression)
- [ ] Measure baseline: heuristic accuracy vs learned accuracy
- [ ] Implement `LearnedIntentClassifier`
- [ ] Add A/B test configuration toggle
- [ ] Run parallel: 50% heuristic, 50% learned
- [ ] Compare accuracy, latency, user satisfaction
- [ ] Switch to 100% learned if accuracy >90%
- [ ] Implement confidence calibrator
- [ ] Commit: "feat(intent): learned classifier with calibration"

### Phase 3: Automation (Month 3+)
- [ ] Implement online learning (update model per interaction)
- [ ] Add active learning (ask when uncertain)
- [ ] Auto-discover new intent categories
- [ ] Generalize to topic extraction, query selection
- [ ] Remove all Phase 1 heuristics
- [ ] Commit: "feat(learning): fully automated pattern discovery"

---

## Success Metrics

### Phase 0 Success (Immediate)
- ✅ Zero instances of `confidence=1.0` in codebase
- ✅ All tests passing
- ✅ MAX_CONFIDENCE enforced everywhere

### Phase 1 Success (Week 2)
- ✅ Zero hardcoded keyword lists in service files
- ✅ All heuristics in `config/` with Phase 2 TODOs
- ✅ Query registry pattern implemented
- ✅ Intent tracking operational (logs visible)

### Phase 2 Success (Month 2)
- ✅ Learned classifier accuracy ≥90% (vs heuristic baseline)
- ✅ Confidence calibrated (predicted ≈ actual accuracy)
- ✅ Latency <100ms for intent classification
- ✅ Zero manual keyword updates needed

### Phase 3 Success (Month 3+)
- ✅ System auto-discovers new intents from usage
- ✅ Accuracy improves over time without retraining
- ✅ Adapts to new domains automatically
- ✅ Vision fully realized: "Emergent intelligent behavior"

---

## Philosophical Notes

### Why This Matters

The vision describes **two types of systems**:

**Type 1: Programmed Intelligence** (current state)
- Developer encodes all patterns
- Hardcoded keyword lists
- Static behavior
- Requires code changes to adapt

**Type 2: Emergent Intelligence** (vision state)
- System discovers patterns from usage
- Learns what matters
- Adaptive behavior
- Improves automatically

The difference isn't just technical—it's **fundamental to the system's nature**.

A programmed system is a **sophisticated rule engine**.
A learning system is a **cognitive entity**.

The vision aims for the latter. The implementation is the former.

### The Bootstrap Paradox

There's a chicken-and-egg problem:
- Can't learn patterns without usage data
- Can't get usage data without working system
- Working system requires some initial heuristics

**Solution**: Accept Phase 1 as necessary bootstrap, but:
1. Mark it explicitly as temporary
2. Build toward Phase 2 from day 1
3. Track data needed for learning
4. Replace heuristics as soon as possible

### Epistemic Humility in Practice

The `confidence=1.0` violations aren't just bugs—they're **philosophical errors**.

Vision (lines 386-421):
> "A profound principle: The system should know what it doesn't know"

When we write `confidence=1.0`, we claim:
- Database facts are infallible (they're not—data entry errors, staleness)
- Exact matches are perfect (they're not—"Apple Inc" vs "Apple" different entities)
- Our extraction is flawless (it's not—LLM hallucinations, edge cases)

True intelligence requires **knowing the limits of your knowledge**.

---

## Appendix: File Change Summary

### Files to Modify (Phase 0)
- `src/config/heuristics.py` - Fix CONFIDENCE_EXACT_MATCH
- `src/application/use_cases/process_chat_message.py` - Fix memory-vs-DB confidence
- `src/domain/services/debug_trace_service.py` - Fix debug confidence
- `src/demo/services/scenario_loader.py` - Fix scenario confidence

### Files to Create (Phase 1)
- `src/config/intent_keywords.py` - Keyword configuration with Phase 2 TODOs
- `src/infrastructure/tracking/intent_tracker.py` - Usage tracking

### Files to Modify (Phase 1)
- `src/domain/services/domain_augmentation_service.py` - Use config, add registry
- `src/domain/services/procedural_memory_service.py` - Use config, add tracking

### Files to Create (Phase 2)
- `scripts/build_intent_training_data.py` - Training data builder
- `src/domain/services/learned_intent_classifier.py` - Learned classifier
- `src/domain/services/confidence_calibrator.py` - Confidence calibration
- `models/intent_classifier_v1.pkl` - Trained model artifact

### Configuration Changes
- `src/config/settings.py` - Add USE_LEARNED_INTENT_CLASSIFIER toggle

---

## Conclusion

The codebase has **excellent architecture** but **violates core vision principles** through hardcoded heuristics.

This document provides a **phased path** from current state to vision state:
- **Phase 0**: Fix critical violations (epistemic humility)
- **Phase 1**: Configuration-based heuristics (preparation)
- **Phase 2**: Learned classifiers (true learning)
- **Phase 3**: Automated discovery (vision realized)

**The key insight**: Don't try to build perfect learning from day 1. Bootstrap with heuristics, **but mark them as temporary and build toward learning from the start**.

This aligns with the vision's philosophy:
> "Intelligence isn't programmed - it **emerges from interaction of simple mechanisms**"

Our job: Build the mechanisms that enable emergence. 🚀
