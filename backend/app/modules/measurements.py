"""Historical and latest electrical measurements."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.dependencies import CurrentUser, SessionDep
from app.core.time_window import validated_window
from app.db.models import Equipment, Measurement


router = APIRouter(prefix="/measurements", tags=["measurements"])
METRIC_FIELDS = (
    "voltage_l1_v", "voltage_l2_v", "voltage_l3_v",
    "current_l1_a", "current_l2_a", "current_l3_a",
    "active_power_kw", "frequency_hz",
)


class MeasurementInput(BaseModel):
    """Message schema shared with the future MQTT consumer."""

    equipment_id: UUID
    measured_at: datetime
    voltage_l1_v: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    voltage_l2_v: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    voltage_l3_v: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    current_l1_a: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    current_l2_a: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    current_l3_a: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    active_power_kw: float | None = Field(default=None, allow_inf_nan=False)
    frequency_hz: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    quality: Literal["valid", "invalid"] = "valid"
    source: Literal["simulator"] = "simulator"

    @field_validator("measured_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("measured_at must include a timezone")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def require_metric(self) -> "MeasurementInput":
        fields = (
            self.voltage_l1_v, self.voltage_l2_v, self.voltage_l3_v,
            self.current_l1_a, self.current_l2_a, self.current_l3_a,
            self.active_power_kw, self.frequency_hz,
        )
        if all(value is None for value in fields):
            raise ValueError("At least one electrical metric is required")
        return self


class MeasurementRead(MeasurementInput):
    model_config = ConfigDict(from_attributes=True)

    received_at: datetime


class MetricStatistics(BaseModel):
    minimum: float | None
    average: float | None
    maximum: float | None


class TrendBucket(BaseModel):
    bucket_start: datetime
    sample_count: int
    voltage_l1_v: float | None
    voltage_l2_v: float | None
    voltage_l3_v: float | None
    current_l1_a: float | None
    current_l2_a: float | None
    current_l3_a: float | None
    active_power_kw: float | None
    frequency_hz: float | None


class TrendRead(BaseModel):
    equipment_id: UUID
    hours: Literal[24, 168]
    bucket_minutes: int
    valid_samples: int
    buckets: list[TrendBucket]
    statistics: dict[str, MetricStatistics]


def get_equipment_or_404(session: SessionDep, equipment_id: UUID) -> Equipment:
    equipment = session.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@router.get("", response_model=list[MeasurementRead])
def history(
    equipment_id: UUID,
    start: datetime,
    end: datetime,
    session: SessionDep,
    _user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0, le=100000)] = 0,
) -> list[Measurement]:
    try:
        start_utc, end_utc = validated_window(start, end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    get_equipment_or_404(session, equipment_id)
    query = (
        sa.select(Measurement)
        .where(
            Measurement.equipment_id == equipment_id,
            Measurement.measured_at >= start_utc,
            Measurement.measured_at < end_utc,
        )
        .order_by(Measurement.measured_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(query))


@router.get("/trend", response_model=TrendRead)
def trend(
    equipment_id: UUID,
    session: SessionDep,
    _user: CurrentUser,
    hours: Annotated[int, Query(ge=24, le=168)] = 24,
) -> TrendRead:
    """Return bounded TimescaleDB buckets and exact statistics for the full period."""
    if hours not in (24, 168):
        raise HTTPException(status_code=422, detail="hours must be 24 or 168")
    get_equipment_or_404(session, equipment_id)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    bucket_minutes = 5 if hours == 24 else 60
    filters = (
        Measurement.equipment_id == equipment_id,
        Measurement.measured_at >= start,
        Measurement.measured_at < end,
        Measurement.quality == "valid",
    )

    bucket = sa.func.time_bucket(
        sa.cast(sa.literal(f"{bucket_minutes} minutes"), sa.Interval()),
        Measurement.measured_at,
    ).label("bucket_start")
    bucket_query = (
        sa.select(
            bucket,
            sa.func.count().label("sample_count"),
            *(sa.func.avg(getattr(Measurement, field)).label(field) for field in METRIC_FIELDS),
        )
        .where(*filters)
        .group_by(bucket)
        .order_by(bucket)
        .limit(350)
    )
    buckets = [TrendBucket.model_validate(dict(row)) for row in session.execute(bucket_query).mappings()]

    statistics_query = sa.select(
        sa.func.count().label("valid_samples"),
        *(
            aggregate(getattr(Measurement, field)).label(f"{field}_{name}")
            for field in METRIC_FIELDS
            for name, aggregate in (("min", sa.func.min), ("avg", sa.func.avg), ("max", sa.func.max))
        ),
    ).where(*filters)
    summary = session.execute(statistics_query).mappings().one()
    statistics = {
        field: MetricStatistics(
            minimum=summary[f"{field}_min"],
            average=summary[f"{field}_avg"],
            maximum=summary[f"{field}_max"],
        )
        for field in METRIC_FIELDS
    }
    return TrendRead(
        equipment_id=equipment_id,
        hours=hours,
        bucket_minutes=bucket_minutes,
        valid_samples=summary["valid_samples"],
        buckets=buckets,
        statistics=statistics,
    )


@router.get("/latest/{equipment_id}", response_model=MeasurementRead)
def latest(equipment_id: UUID, session: SessionDep, _user: CurrentUser) -> Measurement:
    get_equipment_or_404(session, equipment_id)
    measurement = session.scalar(
        sa.select(Measurement)
        .where(Measurement.equipment_id == equipment_id)
        .order_by(Measurement.measured_at.desc())
        .limit(1)
    )
    if measurement is None:
        raise HTTPException(status_code=404, detail="No measurements for this equipment")
    return measurement
