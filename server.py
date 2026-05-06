"""Vercel entrypoint for RUME AI."""
from app.main import create_app

app = create_app()
