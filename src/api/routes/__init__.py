"""API routes.

FastAPI routers for all endpoints.
"""
from src.api.routes import chat, consolidation, retrieval

__all__ = ["chat", "retrieval", "consolidation"]
