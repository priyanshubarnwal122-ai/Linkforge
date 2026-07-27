"""
app/exceptions.py — Custom exceptions and global error handlers.
"""
from __future__ import annotations

import uuid

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)


def _err(status_code: int, code: str, message: str, request_id: str | None = None, details: list | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message, "request_id": request_id}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class LinkForgeError(Exception):
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred.") -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(LinkForgeError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(LinkForgeError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class AuthenticationError(LinkForgeError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(LinkForgeError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"



class RateLimitError(LinkForgeError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


class LinkExpiredError(LinkForgeError):
    status_code = status.HTTP_410_GONE
    error_code = "LINK_EXPIRED"



# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _domain_handler(request: Request, exc: LinkForgeError) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    log.warning("domain_error", code=exc.error_code, msg=exc.message, path=str(request.url), rid=rid)
    return _err(exc.status_code, exc.error_code, exc.message, rid)


async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    codes = {400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
    return _err(exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail), rid)


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return _err(status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", "Request validation failed.", rid, details)


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    log.exception("unhandled_error", path=str(request.url), rid=rid)
    return _err(500, "INTERNAL_ERROR", "An unexpected error occurred. Please try again later.", rid)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(LinkForgeError, _domain_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)
