"""Protect timestamp, sensor quality and threshold contracts."""

import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.time_window import validated_window
from app.db.models import AlertRule
from app.modules.alerts import RuleLimits, outside_limits
from app.modules.measurements import MeasurementInput


NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def test_measurement_requires_aware_time_and_one_finite_metric() -> None:
    base = {"equipment_id": uuid4(), "measured_at": NOW}
    valid = MeasurementInput(**base, active_power_kw=-12.5, source="simulator")
    assert valid.active_power_kw == -12.5

    invalid = (
        {},
        {"measured_at": NOW.replace(tzinfo=None), "frequency_hz": 50},
        {"frequency_hz": math.nan},
        {"voltage_l1_v": -1},
        {"source": "physical-device", "frequency_hz": 50},
    )
    for changes in invalid:
        with pytest.raises(ValidationError):
            MeasurementInput(**(base | changes))


def test_history_window_has_utc_and_size_limits() -> None:
    start, end = validated_window(NOW, NOW + timedelta(days=1))
    assert start.tzinfo is timezone.utc
    assert end - start == timedelta(days=1)

    with pytest.raises(ValueError):
        validated_window(NOW.replace(tzinfo=None), NOW + timedelta(days=1))
    with pytest.raises(ValueError):
        validated_window(NOW, NOW + timedelta(days=32))
    with pytest.raises(ValueError):
        validated_window(NOW, NOW)


def test_thresholds_open_only_outside_inclusive_range() -> None:
    rule = AlertRule(min_value=48.0, max_value=52.0)
    assert outside_limits(47.9, rule)
    assert not outside_limits(48.0, rule)
    assert not outside_limits(52.0, rule)
    assert outside_limits(52.1, rule)

    with pytest.raises(ValidationError):
        RuleLimits()
    with pytest.raises(ValidationError):
        RuleLimits(min_value=52, max_value=48)
