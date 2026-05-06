"""Application configuration for RUME AI."""
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent


def database_url() -> str:
    raw = os.getenv("DATABASE_URL")
    if not raw:
        return f"sqlite:///{(BASE_DIR / 'instance' / 'rume_ai.db').as_posix()}"
    if raw.startswith("sqlite:///"):
        db_path = raw.removeprefix("sqlite:///")
        if db_path and db_path != ":memory:" and not Path(db_path).is_absolute():
            return f"sqlite:///{(BASE_DIR / db_path).resolve().as_posix()}"
    return raw


class Config:
    """Runtime configuration with production secret validation."""

    ENV = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development")).lower()
    TESTING = os.getenv("TESTING", "0") == "1"

    _SECRET_KEY_ENV = os.getenv("SECRET_KEY")
    _JWT_SECRET_ENV = os.getenv("JWT_SECRET")
    _ENCRYPTION_KEY_ENV = os.getenv("ENCRYPTION_KEY")

    SECRET_KEY_CONFIGURED = bool(_SECRET_KEY_ENV)
    JWT_SECRET_CONFIGURED = bool(_JWT_SECRET_ENV)
    ENCRYPTION_KEY_CONFIGURED = bool(_ENCRYPTION_KEY_ENV)

    SECRET_KEY = _SECRET_KEY_ENV or secrets.token_urlsafe(48)
    JWT_SECRET = _JWT_SECRET_ENV or secrets.token_urlsafe(48)
    ENCRYPTION_KEY = _ENCRYPTION_KEY_ENV or ""

    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_SIZE", str(16 * 1024 * 1024)))
    MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "20"))
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    ALLOWED_MIME_PREFIXES = {
        "pdf": ("application/pdf",),
        "docx": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/zip",
            "application/octet-stream",
        ),
        "txt": ("text/plain", "application/octet-stream"),
    }

    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    FORCE_SECURE_COOKIES = os.getenv("FORCE_SECURE_COOKIES", "0") == "1"
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "200 per hour")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    @classmethod
    def validate(cls, values=None) -> None:
        """Fail fast when production security material is missing."""
        def get(name, default=None):
            if values is None:
                return getattr(cls, name, default)
            return values.get(name, default)

        if get("TESTING", cls.TESTING):
            return

        is_prod = str(get("ENV", cls.ENV)).lower() in {"production", "prod"}
        weak_values = {
            "",
            "replace-with-a-long-random-secret",
            "replace-with-a-different-long-random-secret",
            "your-secret-key-change-in-production",
            "your-jwt-secret-change-in-production",
            "dev-key-123",
            "jwt-secret-123",
        }

        if is_prod:
            secret_key = get("SECRET_KEY", "")
            jwt_secret = get("JWT_SECRET", "")
            encryption_key = get("ENCRYPTION_KEY", "")
            missing = []
            if (
                not get("SECRET_KEY_CONFIGURED", bool(secret_key))
                or secret_key in weak_values
                or len(str(secret_key)) < 32
            ):
                missing.append("SECRET_KEY")
            if (
                not get("JWT_SECRET_CONFIGURED", bool(jwt_secret))
                or jwt_secret in weak_values
                or len(str(jwt_secret)) < 32
            ):
                missing.append("JWT_SECRET")
            if not get("ENCRYPTION_KEY_CONFIGURED", bool(encryption_key)) or encryption_key in weak_values:
                missing.append("ENCRYPTION_KEY")
            if missing:
                joined = ", ".join(missing)
                raise RuntimeError(f"Production requires secure values for: {joined}")

            try:
                Fernet(encryption_key.encode("utf-8") if isinstance(encryption_key, str) else encryption_key)
            except (TypeError, ValueError):
                raise RuntimeError("Production requires ENCRYPTION_KEY to be a valid Fernet key")

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def extension(filename: str) -> str:
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    @staticmethod
    def allowed_mime(filename: str, mimetype: str) -> bool:
        ext = Config.extension(filename)
        if not mimetype:
            return True
        allowed = Config.ALLOWED_MIME_PREFIXES.get(ext, ())
        return any(mimetype == item or mimetype.startswith(f"{item};") for item in allowed)
