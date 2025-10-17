"""Request/response logging middleware.

Provides structured logging for all API requests and responses for debugging
and monitoring in production.
"""
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.api.metrics import http_request_duration_seconds, http_requests_total

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses.

    Logs:
    - Request: method, path, user_id, query params, request_id
    - Response: status code, duration, request_id

    Does not log request/response bodies by default for security and performance.
    """

    def __init__(self, app: ASGIApp, log_bodies: bool = False):
        """Initialize middleware.

        Args:
            app: ASGI application
            log_bodies: Whether to log request/response bodies (default: False)
        """
        super().__init__(app)
        self.log_bodies = log_bodies

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/route handler

        Returns:
            HTTP response
        """
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Extract user_id from header if present
        user_id = request.headers.get("x-user-id", None)

        # Log incoming request
        logger.info(
            "http_request_start",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            user_id=user_id,
            client_host=request.client.host if request.client else None,
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000
            duration_seconds = duration_ms / 1000.0

            # Record Prometheus metrics
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).observe(duration_seconds)

            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
            ).inc()

            # Log successful response
            logger.info(
                "http_request_complete",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=user_id,
            )

            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000
            duration_seconds = duration_ms / 1000.0

            # Record Prometheus metrics for failed request (500 status code)
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
            ).observe(duration_seconds)

            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
            ).inc()

            # Log failed request
            logger.error(
                "http_request_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Re-raise to let FastAPI handle the exception
            raise
