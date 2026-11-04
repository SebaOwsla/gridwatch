"""Check alert transitions around duplicate, late and valid samples."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db.models import AlertEvent, AlertRule, Equipment
from app.modules.measurements import MeasurementInput
from app.modules.telemetry import ingest_measurement


class FakeSession:
    def __init__(self, equipment, rule, scalar_results):
        self.equipment = equipment
        self.rule = rule
        self.scalar_results = iter(scalar_results)
        self.added = []
        self.commits = 0

    def get(self, model, key, **kwargs):
        return self.equipment

    def scalar(self, statement):
        return next(self.scalar_results)

    def scalars(self, statement):
        return [self.rule]

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1


def test_ingestion_opens_and_resolves_one_alert() -> None:
    equipment = Equipment(id=uuid4())
    rule = AlertRule(id=uuid4(), equipment_id=equipment.id, metric="frequency_hz", min_value=49, max_value=51)
    first_time = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
    high = MeasurementInput(equipment_id=equipment.id, measured_at=first_time, frequency_hz=53)
    opening = FakeSession(equipment, rule, [equipment.id, first_time, None])

    result = ingest_measurement(opening, high)

    assert result.inserted and result.opened_alerts == 1
    assert len(opening.added) == 1
    assert isinstance(opening.added[0], AlertEvent)
    assert opening.added[0].status == "open"
    assert opening.commits == 1

    event = opening.added[0]
    next_time = first_time + timedelta(minutes=1)
    normal = MeasurementInput(equipment_id=equipment.id, measured_at=next_time, frequency_hz=50)
    resolving = FakeSession(equipment, rule, [equipment.id, next_time, event])

    result = ingest_measurement(resolving, normal)

    assert result.inserted and result.resolved_alerts == 1
    assert event.status == "resolved"
    assert event.resolved_at is not None


def test_duplicate_and_late_samples_do_not_change_alerts() -> None:
    equipment = Equipment(id=uuid4())
    rule = AlertRule(id=uuid4(), equipment_id=equipment.id, metric="frequency_hz", max_value=51)
    measured_at = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
    sample = MeasurementInput(equipment_id=equipment.id, measured_at=measured_at, frequency_hz=53)

    duplicate = FakeSession(equipment, rule, [None])
    assert not ingest_measurement(duplicate, sample).inserted
    assert duplicate.added == []

    late = FakeSession(equipment, rule, [equipment.id, measured_at + timedelta(minutes=1)])
    assert ingest_measurement(late, sample).inserted
    assert late.added == []
