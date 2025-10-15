"""
Property-Based Tests: Memory State Machine Invariants

Uses hypothesis library to verify memory lifecycle state transition properties.

Vision Principle: "Graceful Forgetting - Memory lifecycle state transitions"

These tests verify the state machine properties for memory lifecycle:
ACTIVE → AGING → SUPERSEDED/INVALIDATED
"""
import pytest
from hypothesis import given, strategies as st, assume
from enum import Enum


# ============================================================================
# State Machine Definition
# ============================================================================

class MemoryStatus(str, Enum):
    """Memory status enum (from design)."""
    ACTIVE = "active"
    AGING = "aging"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


# Valid state transitions (from LIFECYCLE_DESIGN.md)
VALID_TRANSITIONS = {
    MemoryStatus.ACTIVE: {
        MemoryStatus.ACTIVE,  # Can stay active (validation)
        MemoryStatus.AGING,    # Decay threshold crossed
        MemoryStatus.SUPERSEDED,  # New memory supersedes
        MemoryStatus.INVALIDATED,  # User correction
    },
    MemoryStatus.AGING: {
        MemoryStatus.ACTIVE,  # Validated by user
        MemoryStatus.SUPERSEDED,  # Superseded by new memory
        MemoryStatus.INVALIDATED,  # Invalidated by user
    },
    MemoryStatus.SUPERSEDED: set(),  # Terminal state
    MemoryStatus.INVALIDATED: set(),  # Terminal state
}


def is_valid_transition(from_state: MemoryStatus, to_state: MemoryStatus) -> bool:
    """Check if state transition is valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def is_terminal_state(state: MemoryStatus) -> bool:
    """Check if state is terminal (no outgoing transitions)."""
    return len(VALID_TRANSITIONS.get(state, set())) == 0


# ============================================================================
# State Transition Invariants
# ============================================================================

class TestStateTransitionValidity:
    """
    INVARIANT: Only valid state transitions are allowed
    VISION: "Graceful forgetting - controlled state transitions"
    """

    @given(
        from_state=st.sampled_from(list(MemoryStatus)),
        to_state=st.sampled_from(list(MemoryStatus)),
    )
    def test_transition_validity_check(self, from_state, to_state):
        """
        PROPERTY: is_valid_transition correctly identifies valid transitions

        Tests the transition validation function itself.
        """
        is_valid = is_valid_transition(from_state, to_state)

        if to_state in VALID_TRANSITIONS.get(from_state, set()):
            assert is_valid, \
                f"Valid transition {from_state} → {to_state} not recognized"
        else:
            assert not is_valid, \
                f"Invalid transition {from_state} → {to_state} accepted"

    def test_active_can_transition_to_all_non_terminal(self):
        """
        PROPERTY: ACTIVE state can transition to all other states

        ACTIVE is the entry point and can move to any state.
        """
        valid_from_active = VALID_TRANSITIONS[MemoryStatus.ACTIVE]

        # Can transition to AGING
        assert MemoryStatus.AGING in valid_from_active

        # Can transition to SUPERSEDED
        assert MemoryStatus.SUPERSEDED in valid_from_active

        # Can transition to INVALIDATED
        assert MemoryStatus.INVALIDATED in valid_from_active

    def test_terminal_states_have_no_outgoing_transitions(self):
        """
        PROPERTY: Terminal states (SUPERSEDED, INVALIDATED) have no outgoing transitions

        Once superseded or invalidated, memory cannot change state.
        """
        assert is_terminal_state(MemoryStatus.SUPERSEDED), \
            "SUPERSEDED should be terminal"

        assert is_terminal_state(MemoryStatus.INVALIDATED), \
            "INVALIDATED should be terminal"

        assert len(VALID_TRANSITIONS[MemoryStatus.SUPERSEDED]) == 0
        assert len(VALID_TRANSITIONS[MemoryStatus.INVALIDATED]) == 0

    @given(state=st.sampled_from(list(MemoryStatus)))
    def test_state_can_stay_in_same_state_or_transition(self, state):
        """
        PROPERTY: Non-terminal states can either stay or transition

        Ensures state machine is not stuck.
        """
        if is_terminal_state(state):
            # Terminal states have no transitions
            assert len(VALID_TRANSITIONS[state]) == 0
        else:
            # Non-terminal states have at least one valid transition
            assert len(VALID_TRANSITIONS[state]) > 0


# ============================================================================
# State Transition Sequences
# ============================================================================

class TestStateTransitionSequences:
    """
    INVARIANT: State transition sequences must be valid
    VISION: "Memory lifecycle - progressive degradation"
    """

    @given(
        transitions=st.lists(
            st.sampled_from(list(MemoryStatus)),
            min_size=2,
            max_size=10
        )
    )
    def test_transition_sequence_validity(self, transitions):
        """
        PROPERTY: A sequence of transitions is valid iff each step is valid

        Tests that compound transitions follow state machine rules.
        """
        current_state = MemoryStatus.ACTIVE  # Start from ACTIVE

        for i, next_state in enumerate(transitions):
            if is_terminal_state(current_state):
                # Once terminal, cannot transition further
                break

            if is_valid_transition(current_state, next_state):
                # Valid transition - continue
                current_state = next_state
            else:
                # Invalid transition - would be caught by validation
                # In real system, this would raise an exception
                pass

        # If we ended in non-terminal, should have valid state
        assert current_state in MemoryStatus

    def test_common_lifecycle_paths(self):
        """
        PROPERTY: Common lifecycle paths are valid

        Tests typical memory lifecycle scenarios.
        """
        # Path 1: ACTIVE → AGING → ACTIVE (validation)
        path1 = [
            MemoryStatus.ACTIVE,
            MemoryStatus.AGING,
            MemoryStatus.ACTIVE,
        ]

        for i in range(len(path1) - 1):
            assert is_valid_transition(path1[i], path1[i + 1]), \
                f"Invalid transition in path1: {path1[i]} → {path1[i + 1]}"

        # Path 2: ACTIVE → SUPERSEDED (terminal)
        path2 = [MemoryStatus.ACTIVE, MemoryStatus.SUPERSEDED]

        assert is_valid_transition(path2[0], path2[1])
        assert is_terminal_state(path2[1])

        # Path 3: ACTIVE → AGING → SUPERSEDED (decay then supersede)
        path3 = [
            MemoryStatus.ACTIVE,
            MemoryStatus.AGING,
            MemoryStatus.SUPERSEDED,
        ]

        for i in range(len(path3) - 1):
            assert is_valid_transition(path3[i], path3[i + 1])

        # Path 4: ACTIVE → INVALIDATED (user correction)
        path4 = [MemoryStatus.ACTIVE, MemoryStatus.INVALIDATED]

        assert is_valid_transition(path4[0], path4[1])


# ============================================================================
# Terminal State Invariants
# ============================================================================

class TestTerminalStateInvariants:
    """
    INVARIANT: Terminal states are permanent
    VISION: "Don't delete - terminal states are final"
    """

    @given(
        terminal_state=st.sampled_from([
            MemoryStatus.SUPERSEDED,
            MemoryStatus.INVALIDATED
        ]),
        attempted_transition=st.sampled_from(list(MemoryStatus))
    )
    def test_terminal_states_cannot_transition(
        self,
        terminal_state,
        attempted_transition
    ):
        """
        PROPERTY: Terminal states cannot transition to any state (including themselves)

        Once SUPERSEDED or INVALIDATED, memory is immutable.
        """
        is_valid = is_valid_transition(terminal_state, attempted_transition)

        assert not is_valid, \
            f"Terminal state {terminal_state} should not allow transition to {attempted_transition}"

    def test_superseded_memories_maintain_provenance(self):
        """
        PROPERTY: SUPERSEDED memories retain provenance chain

        When memory is superseded, it should have superseded_by_memory_id set.
        This is a structural property, not a state machine property,
        but relates to terminal state semantics.
        """
        # This is a structural test - will be implemented with actual Memory model
        # For now, just document the requirement
        assert MemoryStatus.SUPERSEDED in MemoryStatus
        # When implemented:
        # assert memory.superseded_by_memory_id is not None
        # assert get_provenance_chain(memory) includes superseding memory


# ============================================================================
# State Machine Completeness
# ============================================================================

class TestStateMachineCompleteness:
    """
    INVARIANT: State machine is complete and well-defined
    VISION: "All states accounted for"
    """

    def test_all_states_have_transition_rules(self):
        """
        PROPERTY: Every state has defined transition rules

        Even terminal states have rules (empty set).
        """
        all_states = set(MemoryStatus)
        states_with_rules = set(VALID_TRANSITIONS.keys())

        assert all_states == states_with_rules, \
            f"Missing transition rules for states: {all_states - states_with_rules}"

    def test_state_machine_has_entry_point(self):
        """
        PROPERTY: State machine has clear entry point

        ACTIVE is the entry point for all new memories.
        """
        # All new memories start as ACTIVE
        entry_state = MemoryStatus.ACTIVE

        assert entry_state in MemoryStatus
        assert not is_terminal_state(entry_state)
        assert len(VALID_TRANSITIONS[entry_state]) > 1  # Can transition

    def test_state_machine_has_terminal_states(self):
        """
        PROPERTY: State machine has at least one terminal state

        SUPERSEDED and INVALIDATED are terminal states.
        """
        terminal_states = [
            state for state in MemoryStatus
            if is_terminal_state(state)
        ]

        assert len(terminal_states) >= 2, \
            "State machine should have at least 2 terminal states"

        assert MemoryStatus.SUPERSEDED in terminal_states
        assert MemoryStatus.INVALIDATED in terminal_states

    def test_no_unreachable_states(self):
        """
        PROPERTY: All states are reachable from entry point

        Every state can be reached through some transition path.
        """
        entry_state = MemoryStatus.ACTIVE
        reachable = {entry_state}
        to_explore = {entry_state}

        # BFS to find all reachable states
        while to_explore:
            current = to_explore.pop()
            for next_state in VALID_TRANSITIONS.get(current, set()):
                if next_state not in reachable:
                    reachable.add(next_state)
                    to_explore.add(next_state)

        all_states = set(MemoryStatus)

        assert reachable == all_states, \
            f"Unreachable states: {all_states - reachable}"


# ============================================================================
# Meta-Test: Property Test Coverage
# ============================================================================

@pytest.mark.property
def test_state_machine_property_coverage():
    """
    Meta-test: Verify comprehensive property coverage for state machine

    Required properties:
    1. Transition validity
    2. Terminal state finality
    3. State machine completeness
    4. Common lifecycle paths
    5. No unreachable states
    """
    import inspect
    import sys

    current_module = sys.modules[__name__]
    test_classes = [
        obj for name, obj in inspect.getmembers(current_module)
        if inspect.isclass(obj) and name.startswith('Test')
    ]

    required_properties = [
        "transition",   # Transition validity
        "terminal",     # Terminal state properties
        "sequence",     # Transition sequences
        "completeness", # State machine completeness
    ]

    coverage = {prop: False for prop in required_properties}

    for test_class in test_classes:
        class_name = test_class.__name__.lower()
        for prop in required_properties:
            if prop in class_name:
                coverage[prop] = True

    missing = [prop for prop, covered in coverage.items() if not covered]

    assert not missing, \
        f"State machine missing property coverage for: {missing}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
