"""Opt-in demo assets; IDs match the local frontend preview and simulator."""

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import AlertRule, Equipment, Installation


def seed_demo(session: Session) -> None:
    if get_settings().app_env == "production":
        raise RuntimeError("Demo assets cannot be seeded in production")
    if session.scalar(sa.select(Installation.id).limit(1)) is not None:
        raise RuntimeError("Demo assets require an empty installations table")

    installations = [
        ("10000000-0000-4000-8000-000000000001", "MIN-NORTE", "Complejo Minero Norte", "mine", "Región de Antofagasta"),
        ("10000000-0000-4000-8000-000000000002", "CH-RIO", "Central Río Claro", "hydroelectric", "Región del Biobío"),
        ("10000000-0000-4000-8000-000000000003", "SE-VALLE", "Subestación Valle", "substation", "Región Metropolitana"),
    ]
    for id_, code, name, kind, location in installations:
        session.add(Installation(id=UUID(id_), code=code, name=name, kind=kind,
                                 timezone="America/Santiago", location=location, is_active=True))
    session.flush()

    equipment = [
        ("20000000-0000-4000-8000-000000000001", installations[0][0], "AL-01", "Alimentador principal", "feeder", "online", 13_800),
        ("20000000-0000-4000-8000-000000000004", installations[0][0], "MED-02", "Medidor de chancado", "meter", "online", 13_800),
        ("20000000-0000-4000-8000-000000000003", installations[1][0], "GEN-01", "Generador unidad 1", "generator", "online", 13_800),
        ("20000000-0000-4000-8000-000000000002", installations[2][0], "TR-01", "Transformador principal", "transformer", "maintenance", 110_000),
    ]
    for id_, installation_id, code, name, kind, status, voltage in equipment:
        session.add(Equipment(id=UUID(id_), installation_id=UUID(installation_id), code=code,
                              name=name, kind=kind, status=status, nominal_voltage_v=voltage))
    session.flush()

    rules = [
        ("30000000-0000-4000-8000-000000000001", equipment[0][0], "voltage_l1_v", 13_400, 14_200),
        ("30000000-0000-4000-8000-000000000002", equipment[2][0], "current_l1_a", None, 310),
        ("30000000-0000-4000-8000-000000000003", equipment[3][0], "frequency_hz", 49.5, 50.5),
    ]
    for id_, equipment_id, metric, minimum, maximum in rules:
        session.add(AlertRule(id=UUID(id_), equipment_id=UUID(equipment_id), metric=metric,
                              min_value=minimum, max_value=maximum, is_enabled=True))
    session.commit()
