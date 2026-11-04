"""Record user actions in the same transaction as the data change."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.dependencies import SessionDep, require_roles
from app.db.models import AuditEvent, User


router = APIRouter(prefix="/audit-events", tags=["audit"])


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    details: dict
    created_at: datetime


def record_audit(
    session: Session,
    *,
    actor_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    details: dict | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
    )


@router.get("", response_model=list[AuditEventRead])
def list_audit_events(
    session: SessionDep,
    _admin: Annotated[User, Depends(require_roles("admin"))],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> list[AuditEvent]:
    query = sa.select(AuditEvent).order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
    return list(session.scalars(query))
