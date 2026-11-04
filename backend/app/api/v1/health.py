"""Liveness and database readiness endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import SessionDep


router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(session: SessionDep) -> dict[str, str]:
    session.execute(text("SELECT 1"))
    return {"status": "ok"}
