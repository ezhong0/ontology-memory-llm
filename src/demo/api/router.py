"""Main demo API router.

This router aggregates all demo endpoints and can be mounted in the main
FastAPI application at /demo.
"""
from fastapi import APIRouter

from src.demo.api import memories, scenarios

# Create main demo router
demo_router = APIRouter(prefix="/demo", tags=["demo"])

# Include sub-routers
demo_router.include_router(scenarios.router)
demo_router.include_router(memories.router)
