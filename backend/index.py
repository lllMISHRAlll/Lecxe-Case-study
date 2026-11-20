"""Vercel entrypoint: exposes the FastAPI app (built by the factory) as `app`."""

from app.main import create_app

app = create_app()
