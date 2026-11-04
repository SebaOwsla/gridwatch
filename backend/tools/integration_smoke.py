"""Exercise the local Docker stack through its public HTTP, WS and MQTT ports."""

import argparse
import ipaddress
import json
import os
import time
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import paho.mqtt.client as mqtt
from dotenv import dotenv_values
from openpyxl import load_workbook
from websockets.sync.client import connect


FEEDER_ID = "20000000-0000-4000-8000-000000000001"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
configured_bind_ip = dotenv_values(Path(__file__).resolve().parents[2] / ".env").get("GRIDWATCH_WEB_BIND_IP")
if configured_bind_ip:
    try:
        if ipaddress.ip_address(configured_bind_ip).is_private:
            LOCAL_HOSTS.add(configured_bind_ip)
    except ValueError:
        pass


def timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def publish_sample(host: str, port: int, measured_at: datetime, voltage: float) -> None:
    payload = {
        "equipment_id": FEEDER_ID,
        "measured_at": measured_at.isoformat(),
        "voltage_l1_v": voltage,
        "current_l1_a": 180.0,
        "active_power_kw": 2400.0,
        "frequency_hz": 50.0,
        "quality": "valid",
        "source": "simulator",
    }
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridwatch-smoke-{uuid4().hex[:12]}")
    client.connect(host, port, keepalive=15)
    client.loop_start()
    try:
        info = client.publish(f"gridwatch/demo/measurements/{FEEDER_ID}", json.dumps(payload), qos=1)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            raise RuntimeError("MQTT did not acknowledge the smoke sample")
    finally:
        client.disconnect()
        client.loop_stop()


def await_sample(socket, expected_at: datetime) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        frame = json.loads(socket.recv(timeout=max(0.1, deadline - time.monotonic())))
        measurement = frame.get("measurement") or {}
        if (
            frame.get("type") == "measurement"
            and measurement.get("equipment_id") == FEEDER_ID
            and timestamp(measurement["measured_at"]) == expected_at
        ):
            return
    raise RuntimeError("The WebSocket did not broadcast the MQTT sample")


def run(base_url: str, mqtt_host: str, mqtt_port: int, email: str, password: str) -> dict:
    origin = base_url.rstrip("/")
    ws_url = origin.replace("http://", "ws://", 1) + "/api/v1/ws/measurements"
    with httpx.Client(base_url=origin, timeout=10, trust_env=False) as client:
        ready = client.get("/api/v1/health/ready")
        ready.raise_for_status()
        if ready.json() != {"status": "ok"}:
            raise RuntimeError("API readiness returned an unexpected response")

        login = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        login.raise_for_status()
        token = login.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
        me = client.get("/api/v1/auth/me")
        me.raise_for_status()
        if me.json()["role"] != "admin":
            raise RuntimeError("The smoke account must be an administrator")

        sites = client.get("/api/v1/installations?limit=100")
        assets = client.get("/api/v1/equipment?limit=100")
        sites.raise_for_status()
        assets.raise_for_status()
        if len(sites.json()) < 3 or FEEDER_ID not in {asset["id"] for asset in assets.json()}:
            raise RuntimeError("Demo assets are missing")

        with connect(ws_url, origin=origin, subprotocols=["gridwatch"], open_timeout=5, proxy=None) as socket:
            socket.send(json.dumps({"type": "auth", "token": token}))
            if json.loads(socket.recv(timeout=5)).get("type") != "ready":
                raise RuntimeError("WebSocket authentication failed")

            healthy_at = datetime.now(timezone.utc)
            alert_at = healthy_at + timedelta(microseconds=1)
            publish_sample(mqtt_host, mqtt_port, healthy_at, 13_800.0)
            await_sample(socket, healthy_at)
            publish_sample(mqtt_host, mqtt_port, alert_at, 13_000.0)
            await_sample(socket, alert_at)

        start = healthy_at - timedelta(minutes=10)
        end = healthy_at + timedelta(minutes=1)
        params = {"equipment_id": FEEDER_ID, "start": start.isoformat(), "end": end.isoformat()}
        history = client.get("/api/v1/measurements", params={**params, "limit": 1000})
        history.raise_for_status()
        if not any(timestamp(row["measured_at"]) == alert_at for row in history.json()):
            raise RuntimeError("MQTT sample is missing from measurement history")

        trends = []
        for hours, expected_minutes in ((24, 5), (168, 60)):
            response = client.get(
                "/api/v1/measurements/trend",
                params={"equipment_id": FEEDER_ID, "hours": hours},
            )
            response.raise_for_status()
            trend = response.json()
            if (
                trend["bucket_minutes"] != expected_minutes
                or sum(bucket["sample_count"] for bucket in trend["buckets"]) != trend["valid_samples"]
                or not trend["statistics"]["voltage_l1_v"]["minimum"] <= 13_000.0
            ):
                raise RuntimeError("TimescaleDB trend or full-period statistics are inconsistent")
            trends.append(trend)

        alerts = client.get("/api/v1/alert-events?limit=100")
        alerts.raise_for_status()
        if not any(timestamp(event["measurement_at"]) == alert_at for event in alerts.json()):
            raise RuntimeError("The low-voltage sample did not open an alert")

        pdf = client.get("/api/v1/reports/measurements.pdf", params=params)
        excel = client.get("/api/v1/reports/measurements.xlsx", params=params)
        full_period = {
            "equipment_id": FEEDER_ID,
            "start": (end - timedelta(hours=24)).isoformat(),
            "end": end.isoformat(),
        }
        full_pdf = client.get("/api/v1/reports/measurements.pdf", params=full_period)
        summary_excel = client.get("/api/v1/reports/summary.xlsx", params=full_period)
        pdf.raise_for_status()
        excel.raise_for_status()
        full_pdf.raise_for_status()
        summary_excel.raise_for_status()
        if not pdf.content.startswith(b"%PDF-") or not full_pdf.content.startswith(b"%PDF-"):
            raise RuntimeError("The PDF export is invalid")
        book = load_workbook(BytesIO(excel.content), read_only=True)
        try:
            if book.active.max_row < 6:
                raise RuntimeError("The Excel export has no measurements")
        finally:
            book.close()
        summary_book = load_workbook(BytesIO(summary_excel.content), read_only=True)
        try:
            if summary_book.sheetnames != ["Resumen", "Intervalos"] or summary_book["Intervalos"].max_row < 2:
                raise RuntimeError("The summary Excel export is invalid")
        finally:
            summary_book.close()

        audit = client.get("/api/v1/audit-events?limit=100")
        audit.raise_for_status()
        if sum(event["action"] == "report.exported" for event in audit.json()) < 4:
            raise RuntimeError("Report exports are missing from the audit log")

        return {
            "status": "ok",
            "installations": len(sites.json()),
            "equipment": len(assets.json()),
            "history_rows": len(history.json()),
            "trend_samples_24h": trends[0]["valid_samples"],
            "trend_buckets_7d": len(trends[1]["buckets"]),
            "alerts": len(alerts.json()),
            "pdf_bytes": len(pdf.content),
            "xlsx_bytes": len(excel.content),
            "full_pdf_bytes": len(full_pdf.content),
            "summary_xlsx_bytes": len(summary_excel.content),
            "report_audit_events": sum(event["action"] == "report.exported" for event in audit.json()),
            "websocket_samples": 2,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Local GridWatch integration smoke test")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    args = parser.parse_args()
    target = urlparse(args.base_url)
    if target.scheme != "http" or target.hostname not in LOCAL_HOSTS:
        parser.error("Only a local HTTP base URL is allowed")
    if args.mqtt_host not in LOCAL_HOSTS or not 1 <= args.mqtt_port <= 65535:
        parser.error("Only a local MQTT broker is allowed")
    email = os.getenv("GRIDWATCH_SMOKE_EMAIL")
    password = os.getenv("GRIDWATCH_SMOKE_PASSWORD")
    if not email or not password:
        parser.error("Set GRIDWATCH_SMOKE_EMAIL and GRIDWATCH_SMOKE_PASSWORD")
    print(json.dumps(run(args.base_url, args.mqtt_host, args.mqtt_port, email, password), indent=2))


if __name__ == "__main__":
    main()
