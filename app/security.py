"""Security utilities for encryption, auth, sanitization, and audit logs."""
import hmac
import secrets
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
import bleach
import jwt
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app, jsonify, request
from werkzeug.utils import secure_filename

from app.main import db
from app.observability import log_event, request_id_from_context


class SecurityManager:
    _fernet = None
    _fernet_key = None

    @classmethod
    def _key(cls):
        key = current_app.config.get("ENCRYPTION_KEY", "")
        if not key:
            key = current_app.config.setdefault("_DEV_ENCRYPTION_KEY", Fernet.generate_key().decode())
            log_event("debug", "security.dev_encryption_key", message="Using temporary development encryption key")
        return key.encode() if isinstance(key, str) else key

    @classmethod
    def fernet(cls):
        key = cls._key()
        if cls._fernet is None or cls._fernet_key != key:
            cls._fernet = Fernet(key)
            cls._fernet_key = key
        return cls._fernet

    @classmethod
    def encrypt(cls, text):
        if text is None:
            return ""
        return cls.fernet().encrypt(str(text).encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, token):
        if not token:
            return ""
        try:
            return cls.fernet().decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            log_event("error", "security.decrypt_failed", message="Encrypted field could not be decrypted")
            return ""

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    @staticmethod
    def check_password(password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def generate_token(user_id: int) -> str:
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id),
            "csrf": secrets.token_urlsafe(32),
            "iat": now,
            "exp": now + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
        }
        return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])

    @staticmethod
    def sanitize(text, max_length=10000) -> str:
        if text is None:
            return ""
        clean = bleach.clean(str(text), tags=[], attributes={}, strip=True)
        return clean[:max_length].strip()

    @staticmethod
    def safe_filename(filename: str) -> str:
        safe = secure_filename(filename or "resume")
        return safe[:180] or "resume"

    @staticmethod
    def mask_email(email: str) -> str:
        if not email or "@" not in email:
            return ""
        user, domain = email.split("@", 1)
        if len(user) <= 2:
            masked_user = user[:1] + "*"
        else:
            masked_user = user[0] + "*" * max(2, len(user) - 2) + user[-1]
        return f"{masked_user}@{domain}"


def token_from_request():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip(), "header"
    return request.cookies.get("auth_token", ""), "cookie"


def requires_csrf(source: str) -> bool:
    return source == "cookie" and request.method not in {"GET", "HEAD", "OPTIONS"}


def validate_csrf(payload: dict) -> bool:
    expected = payload.get("csrf", "")
    header_token = request.headers.get("X-CSRF-Token", "")
    cookie_token = request.cookies.get("csrf_token", "")
    if not expected or not header_token or not cookie_token:
        return False
    return hmac.compare_digest(expected, header_token) and hmac.compare_digest(expected, cookie_token)


def require_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        token, source = token_from_request()
        if not token:
            return jsonify({"error": "Authentication required", "request_id": request_id_from_context()}), 401

        try:
            payload = SecurityManager.decode_token(token)
            request.user_id = int(payload["sub"])
            request.auth_source = source
            request.csrf_token = payload.get("csrf", "")
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Session expired", "request_id": request_id_from_context()}), 401
        except (jwt.InvalidTokenError, KeyError, ValueError):
            return jsonify({"error": "Invalid session", "request_id": request_id_from_context()}), 401

        if requires_csrf(source) and not validate_csrf(payload):
            return jsonify({"error": "CSRF validation failed", "request_id": request_id_from_context()}), 403

        return view(*args, **kwargs)

    return wrapped


def set_auth_cookie(response, token: str):
    secure_cookie = current_app.config.get("FORCE_SECURE_COOKIES") or request.is_secure
    csrf_token = ""
    try:
        csrf_token = SecurityManager.decode_token(token).get("csrf", "")
    except jwt.InvalidTokenError:
        csrf_token = ""
    response.set_cookie(
        "auth_token",
        token,
        httponly=True,
        secure=secure_cookie,
        samesite="Strict",
        max_age=current_app.config["JWT_EXPIRY_HOURS"] * 3600,
    )
    if csrf_token:
        response.set_cookie(
            "csrf_token",
            csrf_token,
            httponly=False,
            secure=secure_cookie,
            samesite="Strict",
            max_age=current_app.config["JWT_EXPIRY_HOURS"] * 3600,
        )
    return response


def clear_auth_cookie(response):
    response.delete_cookie("auth_token", samesite="Strict")
    response.delete_cookie("csrf_token", samesite="Strict")
    return response


def log_action(action, resource_type="", resource_id=None, detail=""):
    from app.models import AuditLog

    sanitized_detail = SecurityManager.sanitize(detail, 500)
    entry = AuditLog(
        user_id=getattr(request, "user_id", None),
        action=action,
        resource_type=resource_type or "",
        resource_id=resource_id,
        detail=sanitized_detail,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr or "")[:45],
    )
    db.session.add(entry)
    log_event(
        "info",
        "audit.action",
        action=action,
        resource_type=resource_type or "",
        resource_id=resource_id,
        audit_detail=sanitized_detail,
    )
