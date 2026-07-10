"""Privacy-safe request correlation, logging, and error reporting."""

from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID, uuid4

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import Settings

REQUEST_ID_HEADER = "X-Request-ID"
_request_id: ContextVar[str] = ContextVar("request_id", default="-")
log = logging.getLogger("smile.http")

_LOG_FIELDS = (
    "event",
    "http_method",
    "http_path",
    "http_status",
    "duration_ms",
    "error_type",
    "generation_id",
    "lead_id",
    "clinic_id",
    "channel",
)


def get_request_id() -> str:
    return _request_id.get()


def _safe_request_id(value: str | None) -> str:
    if value:
        try:
            parsed = UUID(value)
            if parsed.version == 4:
                return str(parsed)
        except (AttributeError, ValueError):
            pass
    return str(uuid4())


class _RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        for field in _LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info and record.exc_info[0]:
            payload["error_type"] = record.exc_info[0].__name__
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging() -> None:
    """Use one machine-readable format and attach request IDs to every handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_RequestContextFilter())
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    for noisy_logger in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)


def _strip_query(url: str) -> str:
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return "redacted"


def scrub_sentry_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Remove request content, identities, exception messages, and local variables."""
    event.pop("user", None)
    event.pop("extra", None)
    event.pop("breadcrumbs", None)
    event.pop("logentry", None)
    event.pop("message", None)

    request = event.get("request")
    if isinstance(request, dict):
        safe_request = {}
        if isinstance(request.get("method"), str):
            safe_request["method"] = request["method"]
        if isinstance(request.get("url"), str):
            safe_request["url"] = _strip_query(request["url"])
        event["request"] = safe_request

    exception = event.get("exception")
    if isinstance(exception, dict):
        values = exception.get("values")
        if isinstance(values, list):
            for value in values:
                if not isinstance(value, dict):
                    continue
                value["value"] = str(value.get("type") or "error")
                stacktrace = value.get("stacktrace")
                frames = stacktrace.get("frames") if isinstance(stacktrace, dict) else None
                if isinstance(frames, list):
                    for frame in frames:
                        if isinstance(frame, dict):
                            frame.pop("vars", None)
    return event


def configure_sentry(settings: Settings, *, release: str) -> bool:
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=release,
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        max_breadcrumbs=0,
        traces_sample_rate=0.0,
        before_send=scrub_sentry_event,
    )
    return True


def capture_exception(exc: BaseException) -> None:
    """Capture a handled failure; the configured scrubber removes unsafe values."""
    sentry_sdk.capture_exception(exc)


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = _safe_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = _request_id.set(request_id)
        started = time.monotonic()
        with sentry_sdk.isolation_scope() as scope:
            scope.set_tag("request_id", request_id)
            try:
                response = await call_next(request)
                duration_ms = int((time.monotonic() - started) * 1000)
                log.info(
                    "request_completed",
                    extra={
                        "event": "request_completed",
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "http_status": response.status_code,
                        "duration_ms": duration_ms,
                    },
                )
                response.headers[REQUEST_ID_HEADER] = request_id
                return response
            finally:
                _request_id.reset(token)

    @app.exception_handler(Exception)
    async def unhandled_exception(_request: Request, exc: Exception) -> JSONResponse:
        capture_exception(exc)
        log.error(
            "unhandled_exception",
            extra={"event": "unhandled_exception", "error_type": type(exc).__name__},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal_error", "request_id": get_request_id()},
            headers={REQUEST_ID_HEADER: get_request_id()},
        )
