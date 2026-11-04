"""Installation management with role checks and audit records."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencies import CurrentUser, SessionDep, require_roles
from app.db.models import Installation, User
from app.modules.audit import record_audit


router = APIRouter(prefix="/installations", tags=["installations"])


class InstallationWrite(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["mine", "hydroelectric", "substation"]
    timezone: str = Field(default="America/Santiago", min_length=1, max_length=64)
    location: str | None = Field(default=None, max_length=160)
    is_active: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value


class InstallationRead(InstallationWrite):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


@router.get("", response_model=list[InstallationRead])
def list_installations(
    session: SessionDep,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Installation]:
    query = sa.select(Installation).order_by(Installation.name, Installation.id).offset(offset).limit(limit)
    return list(session.scalars(query))


@router.get("/{installation_id}", response_model=InstallationRead)
def get_installation(installation_id: UUID, session: SessionDep, _user: CurrentUser) -> Installation:
    installation = session.get(Installation, installation_id)
    if installation is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    return installation


@router.post("", response_model=InstallationRead, status_code=status.HTTP_201_CREATED)
def create_installation(
    payload: InstallationWrite,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> Installation:
    installation = Installation(**payload.model_dump())
    session.add(installation)
    session.flush()
    record_audit(
        session, actor_id=actor.id, action="installation.created",
        entity_type="installation", entity_id=installation.id,
    )
    session.commit()
    session.refresh(installation)
    return installation


@router.put("/{installation_id}", response_model=InstallationRead)
def update_installation(
    installation_id: UUID,
    payload: InstallationWrite,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> Installation:
    installation = session.get(Installation, installation_id)
    if installation is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    for name, value in payload.model_dump().items():
        setattr(installation, name, value)
    record_audit(
        session, actor_id=actor.id, action="installation.updated",
        entity_type="installation", entity_id=installation.id,
    )
    session.commit()
    session.refresh(installation)
    return installation
