"""Shared MQTT and Termux:API helpers for SmartDesk."""
import json
import os
import ssl
import subprocess
import time
from pathlib import Path

from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv(Path(__file__).with_name(".env"))

PROJECT_ID = os.getenv("PROJECT_ID", "kelompok-ganti-id").strip()
DEVICE_ID = os.getenv("DEVICE_ID", "hpA").strip()
MQTT_HOST = os.getenv("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
BASE = f"smartdesk/{PROJECT_ID}"
CONTROL_TOPIC = f"{BASE}/control"


def new_client(client_id: str):
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
        protocol=mqtt.MQTTv311,
    )
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    return client


def _on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("MQTT connected securely")
        client.subscribe(CONTROL_TOPIC, qos=1)
    else:
        print(f"MQTT connection failed: {reason_code}")


def _on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    print(f"MQTT disconnected: {reason_code}")


def connect(client):
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_start()


def read_sensor(sensor_name: str, count: int = 1):
    """Read a sensor using Termux:API; returns list of numeric values."""
    proc = subprocess.run(
        ["termux-sensor", "-s", sensor_name, "-n", str(count)],
        capture_output=True, text=True, timeout=15, check=True
    )
    payload = json.loads(proc.stdout)
    # Usually output is {sensor_name: {"values": [...]}}; match case-insensitively if needed.
    item = payload.get(sensor_name)
    if item is None:
        item = next((v for k, v in payload.items()
                     if sensor_name.lower() in k.lower()), None)
    if item is None and len(payload) == 1:
        item = next(iter(payload.values()))
    if not isinstance(item, dict) or "values" not in item:
        raise ValueError(f"Sensor '{sensor_name}' not found in output: {list(payload)}")
    return [float(v) for v in item["values"]]


def publish_json(client, topic: str, data: dict):
    data["sent_at_ms"] = int(time.time() * 1000)
    info = client.publish(topic, json.dumps(data), qos=1)
    info.wait_for_publish(timeout=5)
