"""Generate plausible, explicitly fictional three-phase electrical readings."""

import math
from datetime import datetime, timezone


PROFILES = (
    ("20000000-0000-4000-8000-000000000001", 13_800, 225),
    ("20000000-0000-4000-8000-000000000004", 13_800, 170),
    ("20000000-0000-4000-8000-000000000003", 13_800, 295),
    ("20000000-0000-4000-8000-000000000002", 110_000, 120),
)


def generate_samples(tick: int, measured_at: datetime | None = None) -> list[dict]:
    timestamp = (measured_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    samples = []
    for index, (equipment_id, nominal_v, nominal_a) in enumerate(PROFILES):
        wave = math.sin(tick / 9 + index * 1.3)
        voltage = nominal_v * (1 + 0.004 * wave)
        current = nominal_a * (1 + 0.025 * math.sin(tick / 11 + index))
        frequency = 50 + 0.025 * math.sin(tick / 13 + index)

        # Short, repeatable excursions demonstrate alert opening and resolution.
        if index == 0 and tick % 80 in range(36, 42):
            voltage = 14_300 + 10 * wave
        if index == 2 and tick % 100 in range(52, 58):
            current = 320 + 2 * wave
        if index == 3 and tick % 120 in range(70, 76):
            frequency = 49.4

        samples.append({
            "equipment_id": equipment_id,
            "measured_at": timestamp,
            "voltage_l1_v": round(voltage, 2),
            "voltage_l2_v": round(voltage * 0.998, 2),
            "voltage_l3_v": round(voltage * 1.002, 2),
            "current_l1_a": round(current, 2),
            "current_l2_a": round(current * 0.99, 2),
            "current_l3_a": round(current * 1.01, 2),
            "active_power_kw": round(math.sqrt(3) * voltage * current * 0.9 / 1000, 2),
            "frequency_hz": round(frequency, 3),
            "quality": "valid",
            "source": "simulator",
        })
    return samples
