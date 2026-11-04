"""FastAPI entry point. Database tables are managed only by Alembic."""

import logging
from contextlib import asynccontextmanager

from anyio.to_thread import current_default_thread_limiter
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import router as api_router
from app.core.concurrency import InFlightRequestLimitMiddleware
from app.core.settings import get_settings
from app.realtime.hub import RealtimeHub
from app.realtime.mqtt import MqttSubscriber
from app.realtime.websocket import router as websocket_router


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sync endpoints and dependencies share this worker pool. Keep its concurrency
    # below the SQLAlchemy connection pool so request cleanup cannot starve.
    current_default_thread_limiter().total_tokens = 16
    hub = RealtimeHub()
    hub.start()
    app.state.realtime_hub = hub
    subscriber = MqttSubscriber(get_settings(), hub) if get_settings().mqtt_enabled else None
    try:
        if subscriber:
            subscriber.start()
        yield
    finally:
        if subscriber:
            subscriber.stop()
        await hub.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="GridWatch API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts, www_redirect=False)
    app.include_router(api_router)
    app.include_router(websocket_router, prefix="/api/v1")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Database constraint rejected %s %s", request.method, request.url.path)
        return JSONResponse(status_code=409, content={"detail": "Data conflicts with an existing record or constraint"})

    @app.exception_handler(OperationalError)
    async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
        logger.error("Database unavailable during %s %s", request.method, request.url.path)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    app.add_middleware(InFlightRequestLimitMiddleware, limit=16)
    return app


app = create_app()
