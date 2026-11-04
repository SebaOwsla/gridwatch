"""Receive simulator-only MQTT messages and persist validated samples."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.db.session import get_engine
from app.modules.measurements import MeasurementInput
from app.modules.telemetry import ingest_measurement
from app.realtime.hub import RealtimeHub


logger = logging.getLogger(__name__)
MAX_PAYLOAD_BYTES = 16_384


def parse_message(topic: str, raw: bytes, prefix: str) -> MeasurementInput:
    topic_prefix = f"{prefix.strip('/')}/measurements/"
    if not topic.startswith(topic_prefix) or len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("Invalid telemetry topic or payload size")
    equipment_part = topic[len(topic_prefix):]
    try:
        equipment_id = UUID(equipment_part)
    except ValueError as exc:
        raise ValueError("Invalid equipment topic") from exc
    try:
        payload = MeasurementInput.model_validate_json(raw)
    except ValidationError as exc:
        raise ValueError("Invalid simulator measurement") from exc
    if payload.equipment_id != equipment_id:
        raise ValueError("Topic equipment does not match payload")
    return payload


class MqttSubscriber:
    def __init__(self, settings: Settings, hub: RealtimeHub) -> None:
        self.settings = settings
        self.hub = hub
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridwatch-api-{uuid4().hex[:12]}")
        self.client.on_connect = self._on_connect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_message = self._on_message

    def start(self) -> None:
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect(self, client: mqtt.Client, _userdata: object, _flags: object,
                    reason_code: mqtt.ReasonCode, _properties: object) -> None:
        if reason_code.is_failure:
            logger.warning("MQTT connection rejected: %s", reason_code)
            return
        client.subscribe(f"{self.settings.mqtt_topic_prefix.strip('/')}/measurements/+", qos=1)
        logger.info("Subscribed to simulated GridWatch telemetry")

    def _on_connect_fail(self, _client: mqtt.Client, _userdata: object) -> None:
        logger.warning("MQTT broker unavailable; retrying in background")

    def _on_message(self, _client: mqtt.Client, _userdata: object, message: mqtt.MQTTMessage) -> None:
        if message.retain:
            return
        try:
            payload = parse_message(message.topic, message.payload, self.settings.mqtt_topic_prefix)
            with Session(get_engine()) as session:
                result = ingest_measurement(session, payload)
            if result.inserted:
                measurement = payload.model_dump(mode="json")
                measurement["received_at"] = datetime.now(timezone.utc).isoformat()
                self.hub.publish_from_thread({
                    "type": "measurement", "measurement": measurement,
                    "alerts_changed": bool(result.opened_alerts or result.resolved_alerts),
                })
        except Exception:  # Validation and database errors must not kill the MQTT loop.
            logger.exception("Rejected simulated MQTT measurement on %s", message.topic)
