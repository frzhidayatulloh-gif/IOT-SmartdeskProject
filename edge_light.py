"""HP A: light sensor -> moving average -> MQTT telemetry."""
import os
import time
from collections import deque

from mqtt_common import BASE, DEVICE_ID, connect, new_client, publish_json, read_sensor

SENSOR = os.getenv("LIGHT_SENSOR_NAME", "LIGHT")
INTERVAL = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "1"))
WINDOW = max(1, int(os.getenv("WINDOW_SIZE", "5")))
topic = f"{BASE}/edge/light/telemetry"
armed = True


def on_message(client, userdata, msg):
    global armed
    try:
        import json
        command = json.loads(msg.payload.decode()).get("command", "").upper()
        if command == "ARM":
            armed = True
        elif command == "DISARM":
            armed = False
        print(f"Monitoring: {'ARMED' if armed else 'DISARMED'}")
    except Exception as exc:
        print(f"Invalid control message: {exc}")


def main():
    client = new_client(f"smartdesk-{DEVICE_ID}-light")
    client.on_message = on_message
    connect(client)
    values = deque(maxlen=WINDOW)
    print(f"Light edge running; sensor={SENSOR}, topic={topic}")
    try:
        while True:
            try:
                sample = read_sensor(SENSOR)
                lux = sample[0]
                values.append(lux)
                average = sum(values) / len(values)
                publish_json(client, topic, {
                    "device_id": DEVICE_ID,
                    "sensor": "light",
                    "lux": round(lux, 2),
                    "lux_avg": round(average, 2),
                    "window": len(values),
                    "armed": armed,
                })
                print(f"Lux={lux:.1f}; moving_average={average:.1f}")
            except Exception as exc:
                print(f"Sensor read/publish error: {exc}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Stopping light edge...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
