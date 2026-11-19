"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.errors import install_error_handlers
from app.api.routes import auth, canned, health
from app.container import Container
from app.core.clock import Clock, SystemClock
from app.core.config import Settings, get_settings


def create_app(*, settings: Settings | None = None, clock: Clock | None = None,
               container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    container = container or Container(settings=settings, clock=clock or SystemClock())

    app = FastAPI(title="Procurement Assistant API", docs_url="/api/docs",
                  openapi_url="/api/openapi.json")
    app.state.container = container
    install_error_handlers(app)
    for module in (health, auth, canned):
        app.include_router(module.router, prefix="/api")
    return app
