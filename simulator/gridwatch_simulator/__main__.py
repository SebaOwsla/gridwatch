"""Run with `python -m gridwatch_simulator` after seeding the demo database."""

import argparse
import json
import os
import time
from pathlib import Path
from uuid import uuid4

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

from gridwatch_simulator.samples import generate_samples


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    parser = argparse.ArgumentParser(description="Publish fictional GridWatch telemetry")
    parser.add_argument("--dry-run", action="store_true", help="Print one sample per asset without MQTT")
    parser.add_argument("--cycles", type=int, default=0, help="Publish this many batches, then exit; 0 runs continuously")
    parser.add_argument("--max-wait-seconds", type=float, default=30, help="Maximum wait for the broker in finite mode")
    args = parser.parse_args()
    if args.cycles < 0 or args.max_wait_seconds <= 0:
        parser.error("--cycles must be nonnegative and --max-wait-seconds positive")
    if args.dry_run:
        print(json.dumps(generate_samples(0), indent=2))
        return

    host = os.getenv("MQTT_HOST", "127.0.0.1")
    port = int(os.getenv("MQTT_PORT", "1883"))
    prefix = os.getenv("MQTT_TOPIC_PREFIX", "gridwatch/demo").strip("/")
    if prefix != "gridwatch/demo":
        parser.error("MQTT_TOPIC_PREFIX must be gridwatch/demo for the simulator")
    interval = max(0.5, float(os.getenv("SIMULATOR_INTERVAL_SECONDS", "2")))
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"gridwatch-simulator-{uuid4().hex[:12]}")
    client.connect_async(host, port, keepalive=30)
    client.loop_start()
    print(f"Simulating 4 assets every {interval:g}s; MQTT {host}:{port}. Ctrl+C to stop.")
    tick = 0
    deadline = time.monotonic() + args.max_wait_seconds
    try:
        while True:
            if client.is_connected():
                for sample in generate_samples(tick):
                    topic = f"{prefix}/measurements/{sample['equipment_id']}"
                    info = client.publish(topic, json.dumps(sample), qos=1, retain=False)
                    if args.cycles:
                        info.wait_for_publish(timeout=5)
                        if not info.is_published():
                            raise RuntimeError("MQTT did not acknowledge a sample")
                tick += 1
                deadline = time.monotonic() + args.max_wait_seconds
                if args.cycles and tick >= args.cycles:
                    print(f"Published {tick * 4} fictional measurements")
                    break
            elif args.cycles and time.monotonic() > deadline:
                raise RuntimeError("MQTT broker did not become available")
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == "__main__":
    main()
