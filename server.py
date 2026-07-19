"""Vercel entrypoint for RUME AI."""
import sys
import traceback

try:
    from app.main import create_app
    app = create_app()
except Exception as exc:
    # Provide a helpful error response instead of a raw 500
    from flask import Flask, jsonify
    app = Flask(__name__)
    _startup_error = str(exc)
    _startup_traceback = traceback.format_exc()

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def startup_error(path):
        return jsonify({
            "error": "Application failed to start",
            "detail": _startup_error,
            "hint": "Check that SECRET_KEY, JWT_SECRET, and ENCRYPTION_KEY are set in Vercel Environment Variables",
        }), 500
