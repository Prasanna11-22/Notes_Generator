"""
Request / response timing and logging middleware.

Logs every inbound request and its response status code + latency.
This gives an instant audit trail in both development and production.
"""

import time

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that logs request metadata and response timing.

    Log format::

        GET /api/v1/auth/me | 200 | 12.34ms | 127.0.0.1
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        client_ip = (
            request.headers.get("X-Forwarded-For", request.client.host)
            if request.client
            else "unknown"
        )

        logger.info(
            "{} {} | {} | {:.2f}ms | {}",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            client_ip,
        )

        # Add response-time header for monitoring / debugging
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"
        return response
