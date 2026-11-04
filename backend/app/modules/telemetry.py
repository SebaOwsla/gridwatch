"""Persist simulated telemetry and transition threshold alerts atomically."""

from dataclasses import dataclass
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import AlertEvent, AlertRule, Equipment, Measurement
from app.modules.alerts import outside_limits
from app.modules.measurements import MeasurementInput


@dataclass(frozen=True)
class IngestResult:
    inserted: bool
    opened_alerts: int = 0
    resolved_alerts: int = 0


def ingest_measurement(session: Session, payload: MeasurementInput) -> IngestResult:
    """Accept one simulator sample; repeated or late samples do not change alert state."""
    equipment = session.get(Equipment, payload.equipment_id, with_for_update=True, populate_existing=True)
    if equipment is None:
        raise ValueError("Unknown equipment")

    statement = (
        insert(Measurement)
        .values(**payload.model_dump())
        .on_conflict_do_nothing(index_elements=[Measurement.equipment_id, Measurement.measured_at])
        .returning(Measurement.equipment_id)
    )
    inserted_id = session.scalar(statement)
    if inserted_id is None:
        session.commit()
        return IngestResult(inserted=False)

    latest_at = session.scalar(
        sa.select(Measurement.measured_at)
        .where(Measurement.equipment_id == payload.equipment_id)
        .order_by(Measurement.measured_at.desc())
        .limit(1)
    )
    if latest_at != payload.measured_at or payload.quality != "valid":
        session.commit()
        return IngestResult(inserted=True)

    opened = resolved = 0
    rules = list(session.scalars(
        sa.select(AlertRule)
        .where(AlertRule.equipment_id == payload.equipment_id, AlertRule.is_enabled.is_(True))
        .order_by(AlertRule.id)
    ))
    for rule in rules:
        value = getattr(payload, rule.metric)
        if value is None:
            continue
        active = session.scalar(
            sa.select(AlertEvent)
            .where(AlertEvent.rule_id == rule.id, AlertEvent.status.in_(["open", "acknowledged"]))
            .with_for_update()
        )
        if outside_limits(value, rule):
            if active is None:
                session.add(
                    AlertEvent(
                        rule_id=rule.id,
                        measurement_at=payload.measured_at,
                        observed_value=value,
                        status="open",
                    )
                )
                opened += 1
        elif active is not None:
            active.status = "resolved"
            active.resolved_at = datetime.now(timezone.utc)
            resolved += 1

    session.commit()
    return IngestResult(inserted=True, opened_alerts=opened, resolved_alerts=resolved)
