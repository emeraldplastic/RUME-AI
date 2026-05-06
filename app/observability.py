"""Structured logging helpers for RUME AI."""
import json
import logging
import sys
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from flask import current_app, g, has_app_context, has_request_context, request


LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "error": logging.ERROR,
}


class JsonLogFormatter(logging.Formatter):
    """Emit newline-delimited JSON for Vercel Runtime Logs and log drains."""

    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            payload.update(_json_safe(structured))

        if record.exc_info:
            payload["error"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stack": self.formatException(record.exc_info),
            }

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_logging(app):
    level_name = str(app.config.get("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(level)
    app.logger.propagate = False


def begin_request():
    g.request_started_at = perf_counter()
    g.request_id = (
        request.headers.get("X-Request-ID")
        or request.headers.get("X-Vercel-ID")
        or uuid4().hex
    )[:120]
    log_event(
        "debug",
        "request.started",
        method=request.method,
        path=request.path,
        endpoint=request.endpoint,
    )


def complete_request(response):
    request_id = request_id_from_context()
    response.headers["X-Request-ID"] = request_id

    duration_ms = None
    started_at = getattr(g, "request_started_at", None)
    if started_at:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)

    status_code = response.status_code
    log_event(
        "error" if status_code >= 500 else "info",
        "request.completed",
        method=request.method,
        path=request.path,
        endpoint=request.endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
        response_bytes=response.calculate_content_length(),
    )
    return response


def request_id_from_context():
    if has_request_context():
        return getattr(g, "request_id", None) or request.headers.get("X-Request-ID") or uuid4().hex
    return uuid4().hex


def log_event(level, event, message=None, **fields):
    logger = current_app.logger if has_app_context() else logging.getLogger("rume_ai")
    level_name = str(level).lower()
    log_level = LOG_LEVELS.get(level_name, logging.INFO)
    payload = {
        "event": event,
        "service": "rume-ai",
        **fields,
    }

    if has_request_context():
        payload.update(
            {
                "request_id": request_id_from_context(),
                "user_id": getattr(request, "user_id", None),
                "auth_source": getattr(request, "auth_source", None),
                "remote_addr": _client_ip(),
                "user_agent": request.headers.get("User-Agent", "")[:240],
                "vercel_id": request.headers.get("X-Vercel-ID", ""),
            }
        )

    logger.log(log_level, message or event, extra={"structured": payload})


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",", 1)[0].strip() or request.remote_addr or "")[:45]


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items() if item is not None}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:1000] if isinstance(value, str) else value
    return str(value)[:1000]
