"""Demo adapter layer for the memory system.

This module provides demo functionality including:
- Scenario loading (18 test scenarios from ProjectDescription.md)
- Database admin tools (CRUD for domain data)
- Memory inspection tools (view/analyze memories)
- Enhanced chat with debug traces

The demo layer is completely isolated from production code and can be
disabled via DEMO_MODE_ENABLED=false.
"""
from src.config.settings import Settings

# Fail fast if demo mode is disabled
settings = Settings()
if not settings.DEMO_MODE_ENABLED:
    raise RuntimeError(
        "Demo mode is disabled. Set DEMO_MODE_ENABLED=true in .env to enable demo endpoints."
    )
