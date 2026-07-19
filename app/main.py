"""Flask application factory for RUME AI."""
import os
import tempfile
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.exceptions import HTTPException
from collections import defaultdict

from app.config import Config
from app.observability import begin_request, complete_request, configure_logging, log_event, request_id_from_context

db = SQLAlchemy()

# Rate limit tracking for monitoring
rate_limit_stats = defaultdict(lambda: {"hits": 0, "blocked": 0})

def track_rate_limit(endpoint, blocked=False):
    rate_limit_stats[endpoint]["hits"] += 1
    if blocked:
        rate_limit_stats[endpoint]["blocked"] += 1


def get_rate_limit_key():
    """Combine user ID and IP address for rate limiting."""
    from flask import g
    if hasattr(g, 'user_id') and g.user_id:
        return f"user:{g.user_id}"
    return f"ip:{get_remote_address()}"


limiter = Limiter(key_func=get_rate_limit_key, default_limits=["200 per hour"])


def create_app(test_config=None):
    flask_kwargs = {"static_folder": "static", "template_folder": "templates"}
    if os.getenv("VERCEL"):
        flask_kwargs["instance_path"] = str(Path(tempfile.gettempdir()) / "rume_instance")
    app = Flask(__name__, **flask_kwargs)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    # Request validation middleware
    @app.before_request
    def validate_request():
        """Validate incoming requests for security."""
        # Check content length
        content_length = request.content_length
        max_length = app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
        if content_length and content_length > max_length:
            return jsonify({"error": "Request too large"}), 413
        
        # Validate Content-Type for POST/PUT requests
        if request.method in ("POST", "PUT", "PATCH"):
            if request.is_json:
                try:
                    data = request.get_json()
                    if data is None:
                        return jsonify({"error": "Invalid JSON"}), 400
                except Exception:
                    return jsonify({"error": "Invalid JSON"}), 400

    configure_logging(app)
    Config.validate(app.config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    limiter.init_app(app)

    from app.routes import api

    app.register_blueprint(api)

    @app.before_request
    def start_structured_request_log():
        begin_request()

    @app.after_request
    def add_security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if app.config.get("FORCE_SECURE_COOKIES"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    @app.after_request
    def finish_structured_request_log(response):
        return complete_request(response)

    @app.errorhandler(413)
    def payload_too_large(_):
        log_event("info", "upload.too_large", max_bytes=app.config.get("MAX_CONTENT_LENGTH"))
        return jsonify({"error": "Upload is too large", "request_id": request_id_from_context()}), 413

    @app.errorhandler(RateLimitExceeded)
    def rate_limit_exceeded(exc):
        retry_after = getattr(exc, "retry_after", None)
        limit = getattr(exc, "limit", None)
        endpoint = getattr(exc, "endpoint", "unknown")
        track_rate_limit(endpoint, blocked=True)
        log_event(
            "info",
            "rate_limit.exceeded",
            endpoint=endpoint,
            limit=str(limit or ""),
            retry_after_seconds=retry_after,
        )
        response = jsonify(
            {
                "error": "Rate limit exceeded",
                "request_id": request_id_from_context(),
                "retry_after_seconds": retry_after,
            }
        )
        response.status_code = 429
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
        return response

    @app.errorhandler(Exception)
    def unhandled_exception(exc):
        if isinstance(exc, HTTPException):
            return exc

        log_event("error", "request.exception", error_type=type(exc).__name__, message=str(exc))
        app.logger.exception(
            "Unhandled request exception",
            extra={
                "structured": {
                    "event": "request.exception.stack",
                    "request_id": request_id_from_context(),
                    "error_type": type(exc).__name__,
                }
            },
        )
        return jsonify({"error": "Internal server error", "request_id": request_id_from_context()}), 500

    @app.route("/")
    def landing():
        return render_template("landing.html")

    @app.route("/app")
    @app.route("/app/<path:path>")
    def app_index(path=""):
        return render_template("index.html")

    @app.route("/<path:path>")
    def catch_all(path):
        return render_template("index.html")

    with app.app_context():
        try:
            db.create_all()
            _ensure_sqlite_schema()
        except Exception as exc:
            app.logger.error(f"Database initialization error: {exc}")
            if not os.getenv("VERCEL"):
                raise

    return app


def _ensure_sqlite_schema():
    """Small compatibility guard for pre-market local SQLite databases."""
    if db.engine.url.get_backend_name() != "sqlite":
        return

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())

    def columns(table_name):
        if table_name not in tables:
            return set()
        return {column["name"] for column in inspector.get_columns(table_name)}

    statements = []
    resume_columns = columns("resume")
    if resume_columns:
        if "file_sha256" not in resume_columns:
            statements.append("ALTER TABLE resume ADD COLUMN file_sha256 VARCHAR(64)")
            statements.append("UPDATE resume SET file_sha256 = filename_hash WHERE file_sha256 IS NULL")
        if "candidate_phone_encrypted" not in resume_columns:
            statements.append("ALTER TABLE resume ADD COLUMN candidate_phone_encrypted TEXT")

    analysis_columns = columns("analysis_result")
    if analysis_columns:
        if "analyzed_at" not in analysis_columns:
            statements.append("ALTER TABLE analysis_result ADD COLUMN analyzed_at DATETIME")
            if "timestamp" in analysis_columns:
                statements.append("UPDATE analysis_result SET analyzed_at = timestamp WHERE analyzed_at IS NULL")
        if "evidence_encrypted" not in analysis_columns:
            statements.append("ALTER TABLE analysis_result ADD COLUMN evidence_encrypted TEXT")
        if "calibration_version_id" not in analysis_columns:
            statements.append("ALTER TABLE analysis_result ADD COLUMN calibration_version_id INTEGER")

    for statement in statements:
        db.session.execute(text(statement))
    if statements:
        db.session.commit()
