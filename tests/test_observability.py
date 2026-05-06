import io
import json
import logging
import os
import unittest

from cryptography.fernet import Fernet
from flask import jsonify

os.environ["TESTING"] = "1"
os.environ["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET"] = "test-jwt-secret-with-more-than-32-bytes"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import create_app, db, limiter
from app.observability import JsonLogFormatter


class RumeObservabilityTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "PROPAGATE_EXCEPTIONS": False,
                "RATELIMIT_ENABLED": False,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": os.environ["SECRET_KEY"],
                "JWT_SECRET": os.environ["JWT_SECRET"],
                "ENCRYPTION_KEY": os.environ["ENCRYPTION_KEY"],
                "LOG_LEVEL": "DEBUG",
            }
        )
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.handler.setFormatter(JsonLogFormatter())
        self.app.logger.handlers.clear()
        self.app.logger.addHandler(self.handler)

        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        self.app.logger.removeHandler(self.handler)

    def log_events(self):
        self.handler.flush()
        return [json.loads(line) for line in self.stream.getvalue().splitlines() if line.strip()]

    def test_request_logs_are_structured_and_correlated_by_request_id(self):
        response = self.client.get("/", headers={"X-Request-ID": "req-test-123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-test-123")

        completed = [event for event in self.log_events() if event.get("event") == "request.completed"]
        self.assertTrue(completed)
        self.assertEqual(completed[-1]["request_id"], "req-test-123")
        self.assertEqual(completed[-1]["method"], "GET")
        self.assertEqual(completed[-1]["path"], "/")
        self.assertEqual(completed[-1]["status_code"], 200)
        self.assertIn("duration_ms", completed[-1])
        self.assertEqual(completed[-1]["level"], "info")

    def test_auth_errors_include_request_id_for_log_search(self):
        response = self.client.get("/api/jobs", headers={"X-Request-ID": "auth-missing"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["request_id"], "auth-missing")

    def test_audit_events_include_user_id_and_action_metadata(self):
        response = self.client.post(
            "/api/auth/register",
            headers={"X-Request-ID": "register-log"},
            json={
                "username": "logger",
                "email": "logger@example.com",
                "display_name": "Logger",
                "password": "password123",
            },
        )

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        audits = [event for event in self.log_events() if event.get("event") == "audit.action"]
        self.assertTrue(audits)
        self.assertEqual(audits[-1]["request_id"], "register-log")
        self.assertEqual(audits[-1]["action"], "register")
        self.assertEqual(audits[-1]["resource_type"], "user")
        self.assertIsInstance(audits[-1]["user_id"], int)

    def test_unhandled_errors_are_logged_without_exposing_details_to_client(self):
        @self.app.route("/boom")
        def boom():
            raise RuntimeError("broken for observability test")

        response = self.client.get("/boom", headers={"X-Request-ID": "boom-log"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json(), {"error": "Internal server error", "request_id": "boom-log"})
        errors = [event for event in self.log_events() if event.get("event") == "request.exception.stack"]
        self.assertTrue(errors)
        self.assertEqual(errors[-1]["level"], "error")
        self.assertEqual(errors[-1]["request_id"], "boom-log")
        self.assertEqual(errors[-1]["error_type"], "RuntimeError")
        self.assertIn("stack", errors[-1]["error"])

    def test_rate_limit_response_is_structured_and_logged(self):
        app = create_app(
            {
                "TESTING": True,
                "RATELIMIT_ENABLED": True,
                "RATELIMIT_STORAGE_URI": "memory://",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SECRET_KEY": os.environ["SECRET_KEY"],
                "JWT_SECRET": os.environ["JWT_SECRET"],
                "ENCRYPTION_KEY": os.environ["ENCRYPTION_KEY"],
                "LOG_LEVEL": "INFO",
            }
        )
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonLogFormatter())
        app.logger.handlers.clear()
        app.logger.addHandler(handler)

        def limited():
            return jsonify({"ok": True})

        app.add_url_rule("/limited", "limited", limiter.limit("1 per minute")(limited))
        client = app.test_client()

        first = client.get("/limited", headers={"X-Request-ID": "limit-log"})
        second = client.get("/limited", headers={"X-Request-ID": "limit-log"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        body = second.get_json()
        self.assertEqual(body["error"], "Rate limit exceeded")
        self.assertEqual(body["request_id"], "limit-log")
        self.assertIn("X-RateLimit-Limit", second.headers)

        events = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
        rate_limits = [event for event in events if event.get("event") == "rate_limit.exceeded"]
        self.assertTrue(rate_limits)
        self.assertEqual(rate_limits[-1]["request_id"], "limit-log")


if __name__ == "__main__":
    unittest.main()
