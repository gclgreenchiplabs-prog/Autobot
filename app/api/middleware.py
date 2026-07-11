from __future__ import annotations

import logging
import uuid
from time import perf_counter
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("market_move_bot.api")


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        started = perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = round((perf_counter() - started) * 1000, 2)
            logger.info("request_completed", extra={"correlation_id": correlation_id, "path": request.url.path, "status_code": response.status_code, "elapsed_ms": elapsed_ms})
            response.headers["x-correlation-id"] = correlation_id
            return response
        except Exception as exc:
            logger.exception("request_failed", extra={"correlation_id": correlation_id, "path": request.url.path})
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": str(exc),
                        "correlation_id": correlation_id,
                    }
                },
            )


def add_exception_middleware(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "correlation_id": correlation_id,
                }
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exc.detail or "Request failed",
                    "correlation_id": correlation_id,
                }
            },
        )
