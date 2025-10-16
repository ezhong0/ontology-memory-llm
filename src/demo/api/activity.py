"""Live activity feed endpoint.

Maintains a circular buffer of recent system activity for real-time monitoring.
"""
from collections import deque
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/activity", tags=["activity"])

# ============================================================================
# Global Activity Buffer
# ============================================================================

# Circular buffer to store last 100 activities
# Thread-safe with lock for concurrent access
_activity_buffer: deque[dict[str, Any]] = deque(maxlen=100)
_buffer_lock = Lock()


# ============================================================================
# Activity Models
# ============================================================================


class ActivityEvent(BaseModel):
    """Activity event for live feed."""

    activity_id: str
    timestamp: str
    event_type: str  # entity_resolution, memory_retrieval, database_query, llm_call, etc.
    summary: str  # Human-readable summary
    details: dict[str, Any]
    duration_ms: float | None = None


# ============================================================================
# Public API
# ============================================================================


def add_activity(
    event_type: str,
    summary: str,
    details: dict[str, Any],
    duration_ms: float | None = None,
) -> None:
    """Add an activity to the global buffer.

    Thread-safe. Can be called from any request context.

    Args:
        event_type: Type of activity
        summary: Human-readable summary
        details: Activity details
        duration_ms: Optional duration
    """
    activity = {
        "activity_id": f"{datetime.now(UTC).timestamp()}_{event_type}",
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "summary": summary,
        "details": details,
        "duration_ms": duration_ms,
    }

    with _buffer_lock:
        _activity_buffer.append(activity)


def clear_activities() -> None:
    """Clear all activities from buffer."""
    with _buffer_lock:
        _activity_buffer.clear()


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/recent", response_model=list[ActivityEvent])
async def get_recent_activities(limit: int = 20) -> list[ActivityEvent]:
    """Get recent system activities.

    Returns the most recent activities from the global buffer.

    Args:
        limit: Maximum number of activities to return (default: 20, max: 100)

    Returns:
        List of recent activities, newest first
    """
    with _buffer_lock:
        # Get last N activities, return newest first
        activities = list(_activity_buffer)[-min(limit, 100) :]
        activities.reverse()  # Newest first

    return [ActivityEvent(**activity) for activity in activities]


@router.delete("/clear")
async def clear_activity_feed() -> dict[str, str]:
    """Clear all activities from the feed.

    Returns:
        Success message
    """
    clear_activities()
    return {"message": "Activity feed cleared"}
