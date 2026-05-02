"""Application configuration for RUME AI."""
import os
import secrets
from pathlib import Path

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

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_SIZE", str(16 * 1024 * 1024)))
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
    def validate(cls) -> None:
        """Fail fast when production security material is missing."""
        if cls.TESTING:
            return

        is_prod = cls.ENV in {"production", "prod"}
        weak_values = {
            "",
            "your-secret-key-change-in-production",
            "your-jwt-secret-change-in-production",
            "dev-key-123",
            "jwt-secret-123",
        }

        if is_prod:
            missing = []
            if cls.SECRET_KEY in weak_values:
                missing.append("SECRET_KEY")
            if cls.JWT_SECRET in weak_values:
                missing.append("JWT_SECRET")
            if cls.ENCRYPTION_KEY in weak_values:
                missing.append("ENCRYPTION_KEY")
            if missing:
                joined = ", ".join(missing)
                raise RuntimeError(f"Production requires secure values for: {joined}")

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def extension(filename: str) -> str:
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""
