"""Verify the demo MQTT boundary and authenticated live delivery without a broker."""

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_access_token
from app.core.settings import get_settings
from app.db.models import User
from app.db.session import get_session
from app.main import app
from app.realtime.mqtt import parse_message


PREFIX = "gridwatch/demo"


def test_mqtt_contract_rejects_wrong_topic_size_and_source() -> None:
    sample = {
        "equipment_id": "20000000-0000-4000-8000-000000000001",
        "measured_at": datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc).isoformat(),
        "voltage_l1_v": 13_800,
        "source": "simulator",
    }
    topic = f"{PREFIX}/measurements/{sample['equipment_id']}"
    parsed = parse_message(topic, json.dumps(sample).encode(), PREFIX)
    assert str(parsed.equipment_id) == sample["equipment_id"]
    assert parsed.source == "simulator"

    wrong_topic = f"{PREFIX}/measurements/{uuid4()}"
    with pytest.raises(ValueError, match="does not match"):
        parse_message(wrong_topic, json.dumps(sample).encode(), PREFIX)
    with pytest.raises(ValueError, match="payload size"):
        parse_message(topic, b"x" * 16_385, PREFIX)
    with pytest.raises(ValueError, match="Invalid simulator"):
        parse_message(topic, json.dumps(sample | {"source": "physical-device"}).encode(), PREFIX)


def test_websocket_requires_valid_user_and_delivers_measurements() -> None:
    user = User(id=uuid4(), email="live@example.com", password_hash="unused",
                full_name="Live Viewer", role="viewer", is_active=True)

    class FakeSession:
        def get(self, model, key):
            return user if key == user.id else None

    def fake_session():
        yield FakeSession()

    app.dependency_overrides[get_session] = fake_session
    try:
        token = create_access_token(user.id, get_settings())
        origin = {"origin": "http://127.0.0.1:5173"}
        with TestClient(app) as client:
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/api/v1/ws/measurements", headers=origin.copy(),
                                              subprotocols=["gridwatch"]) as socket:
                    socket.send_json({"type": "auth", "token": "invalid"})
                    socket.receive_json()
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/api/v1/ws/measurements",
                                              headers={"origin": "https://other.example"},
                                              subprotocols=["gridwatch"]):
                    pass
            with client.websocket_connect("/api/v1/ws/measurements", headers=origin.copy(),
                                          subprotocols=["gridwatch"]) as socket:
                assert socket.accepted_subprotocol == "gridwatch"
                socket.send_json({"type": "auth", "token": token})
                assert socket.receive_json() == {"type": "ready"}
                app.state.realtime_hub.publish_from_thread({"type": "measurement", "measurement": {"equipment_id": "demo"}})
                assert socket.receive_json()["measurement"]["equipment_id"] == "demo"
    finally:
        app.dependency_overrides.clear()
