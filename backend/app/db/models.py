"""Relational entities and the measurement hypertable schema."""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
        sa.CheckConstraint(
            "role IN ('admin', 'operator', 'viewer')", name="ck_users_role"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    role: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()
    )


class Installation(Base):
    __tablename__ = "installations"
    __table_args__ = (
        sa.CheckConstraint(
            "kind IN ('mine', 'hydroelectric', 'substation')",
            name="ck_installations_kind",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(sa.String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    kind: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    timezone: Mapped[str] = mapped_column(sa.String(64), nullable=False, server_default="America/Santiago")
    location: Mapped[str | None] = mapped_column(sa.String(160))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class Equipment(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        sa.UniqueConstraint("installation_id", "code", name="uq_equipment_installation_code"),
        sa.CheckConstraint(
            "kind IN ('meter', 'transformer', 'generator', 'feeder', 'breaker')",
            name="ck_equipment_kind",
        ),
        sa.CheckConstraint(
            "status IN ('online', 'offline', 'maintenance')",
            name="ck_equipment_status",
        ),
        sa.CheckConstraint(
            "nominal_voltage_v IS NULL OR nominal_voltage_v > 0",
            name="ck_equipment_nominal_voltage_positive",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("installations.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    kind: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="offline")
    nominal_voltage_v: Mapped[float | None] = mapped_column(sa.Float(53))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        sa.CheckConstraint(
            "num_nonnulls(voltage_l1_v, voltage_l2_v, voltage_l3_v, "
            "current_l1_a, current_l2_a, current_l3_a, active_power_kw, frequency_hz) > 0",
            name="ck_measurements_has_value",
        ),
        sa.CheckConstraint(
            "(voltage_l1_v IS NULL OR voltage_l1_v >= 0) AND "
            "(voltage_l2_v IS NULL OR voltage_l2_v >= 0) AND "
            "(voltage_l3_v IS NULL OR voltage_l3_v >= 0) AND "
            "(current_l1_a IS NULL OR current_l1_a >= 0) AND "
            "(current_l2_a IS NULL OR current_l2_a >= 0) AND "
            "(current_l3_a IS NULL OR current_l3_a >= 0) AND "
            "(frequency_hz IS NULL OR frequency_hz >= 0)",
            name="ck_measurements_nonnegative_magnitudes",
        ),
        sa.CheckConstraint("quality IN ('valid', 'invalid')", name="ck_measurements_quality"),
        sa.CheckConstraint("source = 'simulator'", name="ck_measurements_demo_only"),
    )

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), primary_key=True
    )
    measured_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    voltage_l1_v: Mapped[float | None] = mapped_column(sa.Float(53))
    voltage_l2_v: Mapped[float | None] = mapped_column(sa.Float(53))
    voltage_l3_v: Mapped[float | None] = mapped_column(sa.Float(53))
    current_l1_a: Mapped[float | None] = mapped_column(sa.Float(53))
    current_l2_a: Mapped[float | None] = mapped_column(sa.Float(53))
    current_l3_a: Mapped[float | None] = mapped_column(sa.Float(53))
    active_power_kw: Mapped[float | None] = mapped_column(sa.Float(53))
    frequency_hz: Mapped[float | None] = mapped_column(sa.Float(53))
    quality: Mapped[str] = mapped_column(sa.String(12), nullable=False, server_default="valid")
    source: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="simulator")


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        sa.UniqueConstraint("equipment_id", "metric", name="uq_alert_rules_equipment_metric"),
        sa.CheckConstraint(
            "metric IN ('voltage_l1_v', 'voltage_l2_v', 'voltage_l3_v', "
            "'current_l1_a', 'current_l2_a', 'current_l3_a', "
            "'active_power_kw', 'frequency_hz')",
            name="ck_alert_rules_metric",
        ),
        sa.CheckConstraint(
            "min_value IS NOT NULL OR max_value IS NOT NULL", name="ck_alert_rules_has_bound"
        ),
        sa.CheckConstraint(
            "min_value IS NULL OR max_value IS NULL OR min_value < max_value",
            name="ck_alert_rules_bounds_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False
    )
    metric: Mapped[str] = mapped_column(sa.String(24), nullable=False)
    min_value: Mapped[float | None] = mapped_column(sa.Float(53))
    max_value: Mapped[float | None] = mapped_column(sa.Float(53))
    is_enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('open', 'acknowledged', 'resolved')",
            name="ck_alert_events_status",
        ),
        sa.Index("ix_alert_events_rule_status_opened", "rule_id", "status", "opened_at"),
        sa.Index(
            "uq_alert_events_one_active_per_rule",
            "rule_id",
            unique=True,
            postgresql_where=sa.text("status IN ('open', 'acknowledged')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("alert_rules.id", ondelete="RESTRICT"), nullable=False
    )
    measurement_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    observed_value: Mapped[float] = mapped_column(sa.Float(53), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(16), nullable=False, server_default="open")
    opened_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (sa.Index("ix_audit_events_created_at", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")
    )
    action: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=sa.text("'{}'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )
