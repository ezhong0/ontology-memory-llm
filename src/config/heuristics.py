"""Heuristic parameters for Phase 1.

All values from docs/reference/HEURISTICS_CALIBRATION.md
These are first-principles estimates requiring Phase 2 calibration.
"""

# ==============================================================================
# LIFECYCLE MANAGEMENT
# ==============================================================================

# Reinforcement Boosts (confidence increase on validation)
REINFORCEMENT_BOOSTS = [0.15, 0.10, 0.05, 0.02]  # 1st, 2nd, 3rd, 4th+ validations
CONSOLIDATION_BOOST = 0.05  # Confidence boost from consolidation

# Decay
DECAY_RATE_PER_DAY = 0.01  # Exponential decay rate (1% per day)
VALIDATION_THRESHOLD_DAYS = 90  # Days before active recall triggered

# Confidence Limits
MAX_CONFIDENCE = 0.95  # Epistemic humility (never 100% certain)
MIN_CONFIDENCE_FOR_USE = 0.3  # Below this, memory marked for validation

# Importance Calculation
IMPORTANCE_BASE_WEIGHTS = {
    "question": 0.4,
    "statement": 0.6,
    "command": 0.7,
    "correction": 0.9,
    "confirmation": 0.8,
}
IMPORTANCE_ENTITY_BOOST = 0.05  # Per entity mentioned (max 0.2)
IMPORTANCE_DB_BOOST = 0.1  # If domain DB queried

# ==============================================================================
# ENTITY RESOLUTION
# ==============================================================================

# Confidence by Resolution Stage
CONFIDENCE_EXACT_MATCH = 1.0
CONFIDENCE_USER_ALIAS = 0.95
CONFIDENCE_FUZZY_HIGH = 0.85
CONFIDENCE_FUZZY_LOW = 0.70
CONFIDENCE_COREFERENCE = 0.60
CONFIDENCE_DISAMBIGUATION = 0.85  # After user selection

# Fuzzy Matching
FUZZY_MATCH_THRESHOLD = 0.70  # Minimum similarity to consider
FUZZY_MATCH_AUTO_RESOLVE = 0.85  # Auto-resolve if above this

# Disambiguation
DISAMBIGUATION_MIN_CONFIDENCE_GAP = 0.15  # Gap to avoid disambiguation
DISAMBIGUATION_MAX_CANDIDATES = 5  # Max candidates to present

# Alias Learning
ALIAS_CONFIDENCE_BOOST_PER_USE = 0.02  # Incremental boost per use (max 0.95)

# ==============================================================================
# RETRIEVAL SYSTEM
# ==============================================================================

# Retrieval Strategy Weights (Phase 1)
RETRIEVAL_STRATEGY_WEIGHTS = {
    # Factual/Entity-Focused: When query is about specific entities
    "factual_entity_focused": {
        "semantic_similarity": 0.25,
        "entity_overlap": 0.40,
        "temporal_relevance": 0.20,
        "importance": 0.10,
        "reinforcement": 0.05,
    },
    # Procedural: When query asks "how to" or about processes
    "procedural": {
        "semantic_similarity": 0.45,
        "entity_overlap": 0.05,
        "temporal_relevance": 0.05,
        "importance": 0.15,
        "reinforcement": 0.30,
    },
    # Exploratory: Open-ended queries
    "exploratory": {
        "semantic_similarity": 0.35,
        "entity_overlap": 0.25,
        "temporal_relevance": 0.15,
        "importance": 0.20,
        "reinforcement": 0.05,
    },
    # Temporal: Time-specific queries
    "temporal": {
        "semantic_similarity": 0.20,
        "entity_overlap": 0.20,
        "temporal_relevance": 0.40,
        "importance": 0.15,
        "reinforcement": 0.05,
    },
}

# Retrieval Limits
MAX_SEMANTIC_CANDIDATES = 50
MAX_ENTITY_CANDIDATES = 30
MAX_TEMPORAL_CANDIDATES = 30
MAX_SUMMARY_CANDIDATES = 5

# Type Boosts
SUMMARY_BOOST = 1.15  # Summaries get 15% boost in scoring

# Temporal Decay for Retrieval
EPISODIC_HALF_LIFE_DAYS = 30  # Episodic memories decay faster
SEMANTIC_HALF_LIFE_DAYS = 90  # Semantic facts decay slower

# ==============================================================================
# CONFLICT DETECTION
# ==============================================================================

# Conflict Resolution
CONFIDENCE_GAP_THRESHOLD = 0.30  # Gap to trust higher confidence
AGE_THRESHOLD_DAYS = 60  # Age to trust recency
MIN_CONFIDENCE_FOR_CONFLICT = 0.4  # Below this, just replace

# ==============================================================================
# CONSOLIDATION
# ==============================================================================

# Consolidation Triggers
CONSOLIDATION_MIN_EPISODIC = 10  # Min episodic memories to consolidate
CONSOLIDATION_MIN_SESSIONS = 3  # Min sessions in window
CONSOLIDATION_SESSION_WINDOW_DEFAULT = 5  # Last N sessions

# ==============================================================================
# EXTRACTION
# ==============================================================================

# Base Confidence for Extraction
EXTRACTION_CONFIDENCE = {
    "explicit_statement": 0.7,  # "Remember: X prefers Y"
    "inferred": 0.5,  # Inferred from context
    "consolidation": 0.75,  # From LLM consolidation
    "correction": 0.85,  # User corrects previous fact
}

# ==============================================================================
# CONTEXT WINDOW MANAGEMENT
# ==============================================================================

# Token Budget Allocation (% of max_context_tokens)
CONTEXT_DB_FACTS = 0.40  # 40% for authoritative DB facts
CONTEXT_SUMMARIES = 0.20  # 20% for memory summaries
CONTEXT_SEMANTIC = 0.20  # 20% for semantic facts
CONTEXT_EPISODIC = 0.15  # 15% for recent episodic
CONTEXT_PROCEDURAL = 0.05  # 5% for procedural hints

# Token Estimation
TOKENS_PER_CHAR = 0.25  # Rough estimate: 4 chars per token

# ==============================================================================
# PHASE 2 CALIBRATION REQUIREMENTS
# ==============================================================================

# Minimum data needed before Phase 2 calibration
MIN_SEMANTIC_MEMORIES = 100
MIN_RETRIEVAL_EVENTS = 500
MIN_ENTITY_RESOLUTIONS = 100
MIN_CONSOLIDATIONS = 50

def get_retrieval_weights(strategy: str = "factual_entity_focused") -> dict[str, float]:
    """Get retrieval weights for a given strategy.

    Args:
        strategy: Strategy name (factual_entity_focused, procedural, exploratory, temporal)

    Returns:
        Dictionary of signal weights

    Raises:
        KeyError: If strategy not found
    """
    if strategy not in RETRIEVAL_STRATEGY_WEIGHTS:
        # Default to exploratory if unknown
        return RETRIEVAL_STRATEGY_WEIGHTS["exploratory"]
    return RETRIEVAL_STRATEGY_WEIGHTS[strategy]


def get_reinforcement_boost(validation_count: int) -> float:
    """Get reinforcement boost for Nth validation.

    Args:
        validation_count: Number of times memory has been validated (1-indexed)

    Returns:
        Confidence boost amount
    """
    index = validation_count - 1
    if index >= len(REINFORCEMENT_BOOSTS):
        return REINFORCEMENT_BOOSTS[-1]  # Use last value for all subsequent
    return REINFORCEMENT_BOOSTS[index]
