"""The fictional profiles stay compatible with the seeded assets and alerts."""

from datetime import datetime, timezone

from gridwatch_simulator.samples import generate_samples


def test_four_profiles_and_repeatable_threshold_excursions() -> None:
    at = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
    normal = generate_samples(0, at)
    assert len(normal) == 4
    assert len({sample["equipment_id"] for sample in normal}) == 4
    assert all(sample["source"] == "simulator" and sample["quality"] == "valid" for sample in normal)

    assert generate_samples(36, at)[0]["voltage_l1_v"] > 14_200
    assert generate_samples(52, at)[2]["current_l1_a"] > 310
    assert generate_samples(70, at)[3]["frequency_hz"] < 49.5
    assert generate_samples(77, at)[3]["frequency_hz"] >= 49.5
