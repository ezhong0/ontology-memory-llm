"""FastAPI application entry point.

This module sets up the FastAPI application with all routes, middleware,
and lifecycle event handlers.
"""
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.middleware.logging import RequestLoggingMiddleware
from src.config.settings import Settings
from src.infrastructure.database.session import close_db, init_db

# Load settings
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events for database connections
    and other resources.
    """
    # Startup
    print("Starting up application...")
    init_db(settings)
    print(f"Database initialized: {settings.database_url}")

    yield

    # Shutdown
    print("Shutting down application...")
    await close_db()
    print("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="Ontology-Aware Memory System",
    description="A sophisticated memory system for LLM agents with domain ontology integration",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/response logging middleware
# Logs all HTTP requests and responses with timing and tracing
app.add_middleware(RequestLoggingMiddleware, log_bodies=False)


# Health check endpoint
@app.get("/api/v1/health", tags=["System"])
async def health_check(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Health check endpoint with actual database connectivity verification.

    Checks:
    - API responsiveness (implicit - endpoint responding)
    - Database connectivity (via SELECT 1 query)

    Returns:
        dict: System health status with component details
        HTTP 200: All components healthy
        HTTP 503: One or more components unhealthy
    """
    components = {"api": {"status": "up", "timestamp": datetime.now(UTC).isoformat()}}
    overall_status = "healthy"
    http_status = 200

    # Check database connectivity
    try:
        # Execute simple query to verify DB connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        components["database"] = {
            "status": "up",
            "message": "Database connection successful",
        }
    except Exception as e:
        overall_status = "unhealthy"
        http_status = 503
        components["database"] = {
            "status": "down",
            "error": str(e),
        }

    response_data = {
        "status": overall_status,
        "version": "1.0.0",
        "environment": settings.environment,
        "timestamp": datetime.now(UTC).isoformat(),
        "components": components,
    }

    return JSONResponse(content=response_data, status_code=http_status)


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information.

    Returns:
        dict: API metadata or redirect to demo UI
    """
    # If demo mode is enabled, redirect to demo UI
    if settings.DEMO_MODE_ENABLED:
        return RedirectResponse(url="/demo")

    return {
        "name": "Ontology-Aware Memory System API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "operational",
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found",
                "path": str(request.url),
            }
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred",
            }
        },
    )


# Include API routers
from src.api.routes import chat, conflicts, consolidation, memories, procedural

app.include_router(chat.router, tags=["Chat"])
app.include_router(conflicts.router, tags=["Conflicts"])
app.include_router(consolidation.router, tags=["Consolidation"])
app.include_router(memories.router, tags=["Memories"])
app.include_router(procedural.router, tags=["Procedural"])

# Include demo router if demo mode is enabled
# Use dynamic import to avoid contaminating production code
if settings.DEMO_MODE_ENABLED:
    try:
        import importlib
        demo_module = importlib.import_module("src.demo.api.router")
        demo_router = demo_module.demo_router

        app.include_router(demo_router, prefix="/api/v1")
        print("✓ Demo endpoints enabled at /api/v1/demo")

        # Mount frontend static files
        frontend_path = Path(__file__).parent.parent.parent / "frontend"
        if frontend_path.exists():
            app.mount("/demo", StaticFiles(directory=str(frontend_path), html=True), name="demo-ui")
            print(f"✓ Demo UI enabled at /demo (serving from {frontend_path})")
        else:
            print(f"⚠ Frontend directory not found at {frontend_path}")
    except (ImportError, AttributeError, RuntimeError) as e:
        print(f"⚠ Demo mode requested but failed to load: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload and settings.is_development(),
        log_level=settings.log_level.lower(),
    )
