"""Equipment management linked to installations."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.dependencies import CurrentUser, SessionDep, require_roles
from app.db.models import Equipment, Installation, User
from app.modules.audit import record_audit


router = APIRouter(prefix="/equipment", tags=["equipment"])


class EquipmentWrite(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=120)
    kind: Literal["meter", "transformer", "generator", "feeder", "breaker"]
    status: Literal["online", "offline", "maintenance"] = "offline"
    nominal_voltage_v: float | None = Field(default=None, gt=0, allow_inf_nan=False)

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class EquipmentCreate(EquipmentWrite):
    installation_id: UUID


class EquipmentRead(EquipmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


@router.get("", response_model=list[EquipmentRead])
def list_equipment(
    session: SessionDep,
    _user: CurrentUser,
    installation_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Equipment]:
    query = sa.select(Equipment)
    if installation_id is not None:
        query = query.where(Equipment.installation_id == installation_id)
    return list(session.scalars(query.order_by(Equipment.name, Equipment.id).offset(offset).limit(limit)))


@router.get("/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: UUID, session: SessionDep, _user: CurrentUser) -> Equipment:
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> Equipment:
    if session.get(Installation, payload.installation_id) is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    equipment = Equipment(**payload.model_dump())
    session.add(equipment)
    session.flush()
    record_audit(
        session, actor_id=actor.id, action="equipment.created",
        entity_type="equipment", entity_id=equipment.id,
    )
    session.commit()
    session.refresh(equipment)
    return equipment


@router.put("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(
    equipment_id: UUID,
    payload: EquipmentWrite,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> Equipment:
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    for name, value in payload.model_dump().items():
        setattr(equipment, name, value)
    record_audit(
        session, actor_id=actor.id, action="equipment.updated",
        entity_type="equipment", entity_id=equipment.id,
    )
    session.commit()
    session.refresh(equipment)
    return equipment
