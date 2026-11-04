"""Threshold rules, alert history and operator acknowledgement."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.dependencies import CurrentUser, SessionDep, require_roles
from app.db.models import AlertEvent, AlertRule, Equipment, User
from app.modules.audit import record_audit


AlertMetric = Literal[
    "voltage_l1_v", "voltage_l2_v", "voltage_l3_v",
    "current_l1_a", "current_l2_a", "current_l3_a",
    "active_power_kw", "frequency_hz",
]
AlertStatus = Literal["open", "acknowledged", "resolved"]

rules_router = APIRouter(prefix="/alert-rules", tags=["alerts"])
events_router = APIRouter(prefix="/alert-events", tags=["alerts"])


class RuleLimits(BaseModel):
    min_value: float | None = Field(default=None, allow_inf_nan=False)
    max_value: float | None = Field(default=None, allow_inf_nan=False)
    is_enabled: bool = True

    @model_validator(mode="after")
    def validate_bounds(self) -> "RuleLimits":
        if self.min_value is None and self.max_value is None:
            raise ValueError("At least one threshold is required")
        if (
            self.min_value is not None and self.max_value is not None
            and self.min_value >= self.max_value
        ):
            raise ValueError("min_value must be lower than max_value")
        return self


class AlertRuleCreate(RuleLimits):
    equipment_id: UUID
    metric: AlertMetric


class AlertRuleRead(AlertRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class AlertEventRead(BaseModel):
    id: UUID
    rule_id: UUID
    equipment_id: UUID
    metric: AlertMetric
    measurement_at: datetime
    observed_value: float
    status: AlertStatus
    opened_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by: UUID | None
    resolved_at: datetime | None


def outside_limits(value: float, rule: AlertRule) -> bool:
    return (rule.min_value is not None and value < rule.min_value) or (
        rule.max_value is not None and value > rule.max_value
    )


def event_payload(event: AlertEvent, rule: AlertRule) -> AlertEventRead:
    return AlertEventRead(
        id=event.id, rule_id=event.rule_id, equipment_id=rule.equipment_id,
        metric=rule.metric, measurement_at=event.measurement_at,
        observed_value=event.observed_value, status=event.status,
        opened_at=event.opened_at, acknowledged_at=event.acknowledged_at,
        acknowledged_by=event.acknowledged_by, resolved_at=event.resolved_at,
    )


@rules_router.get("", response_model=list[AlertRuleRead])
def list_rules(
    session: SessionDep,
    _user: CurrentUser,
    equipment_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> list[AlertRule]:
    query = sa.select(AlertRule)
    if equipment_id is not None:
        query = query.where(AlertRule.equipment_id == equipment_id)
    return list(session.scalars(query.order_by(AlertRule.created_at.desc()).offset(offset).limit(limit)))


@rules_router.get("/{rule_id}", response_model=AlertRuleRead)
def get_rule(rule_id: UUID, session: SessionDep, _user: CurrentUser) -> AlertRule:
    rule = session.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@rules_router.post("", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: AlertRuleCreate,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> AlertRule:
    if session.get(Equipment, payload.equipment_id) is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    rule = AlertRule(**payload.model_dump())
    session.add(rule)
    session.flush()
    record_audit(session, actor_id=actor.id, action="alert_rule.created", entity_type="alert_rule", entity_id=rule.id)
    session.commit()
    session.refresh(rule)
    return rule


@rules_router.put("/{rule_id}", response_model=AlertRuleRead)
def update_rule(
    rule_id: UUID,
    payload: RuleLimits,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> AlertRule:
    rule = session.get(AlertRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    session.get(Equipment, rule.equipment_id, with_for_update=True, populate_existing=True)
    session.refresh(rule)
    for name, value in payload.model_dump().items():
        setattr(rule, name, value)
    if not rule.is_enabled:
        active = session.scalar(
            sa.select(AlertEvent).where(
                AlertEvent.rule_id == rule.id,
                AlertEvent.status.in_(["open", "acknowledged"]),
            )
        )
        if active is not None:
            active.status = "resolved"
            active.resolved_at = datetime.now(timezone.utc)
    record_audit(session, actor_id=actor.id, action="alert_rule.updated", entity_type="alert_rule", entity_id=rule.id)
    session.commit()
    session.refresh(rule)
    return rule


@events_router.get("", response_model=list[AlertEventRead])
def list_events(
    session: SessionDep,
    _user: CurrentUser,
    equipment_id: UUID | None = None,
    event_status: Annotated[AlertStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> list[AlertEventRead]:
    query = sa.select(AlertEvent, AlertRule).join(AlertRule, AlertEvent.rule_id == AlertRule.id)
    if equipment_id is not None:
        query = query.where(AlertRule.equipment_id == equipment_id)
    if event_status is not None:
        query = query.where(AlertEvent.status == event_status)
    rows = session.execute(query.order_by(AlertEvent.opened_at.desc()).offset(offset).limit(limit))
    return [event_payload(event, rule) for event, rule in rows]


@events_router.post("/{event_id}/acknowledge", response_model=AlertEventRead)
def acknowledge_event(
    event_id: UUID,
    session: SessionDep,
    actor: Annotated[User, Depends(require_roles("admin", "operator"))],
) -> AlertEventRead:
    event = session.get(AlertEvent, event_id, with_for_update=True)
    if event is None:
        raise HTTPException(status_code=404, detail="Alert event not found")
    if event.status != "open":
        raise HTTPException(status_code=409, detail="Only open alerts can be acknowledged")
    rule = session.get(AlertRule, event.rule_id)
    event.status = "acknowledged"
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by = actor.id
    record_audit(session, actor_id=actor.id, action="alert.acknowledged", entity_type="alert_event", entity_id=event.id)
    session.commit()
    session.refresh(event)
    return event_payload(event, rule)
