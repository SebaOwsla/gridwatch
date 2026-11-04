"""Reject values that would corrupt equipment and installation records."""

import math

import pytest
from pydantic import ValidationError

from app.modules.equipment import EquipmentWrite
from app.modules.installations import InstallationWrite


def test_installation_code_is_normalized_and_timezone_is_validated() -> None:
    installation = InstallationWrite(code="  mine-01  ", name=" Mina Norte ", kind="mine")
    assert installation.code == "MINE-01"
    assert installation.name == "Mina Norte"

    with pytest.raises(ValidationError):
        InstallationWrite(code="MINE-01", name="Mina Norte", kind="mine", timezone="Invalid/Zone")


@pytest.mark.parametrize("voltage", [0, -10, math.inf, math.nan])
def test_nominal_voltage_rejects_nonpositive_or_nonfinite_values(voltage: float) -> None:
    with pytest.raises(ValidationError):
        EquipmentWrite(code="TR-01", name="Transformer", kind="transformer", nominal_voltage_v=voltage)
