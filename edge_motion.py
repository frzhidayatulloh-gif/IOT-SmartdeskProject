"""HP B: accelerometer -> dynamic acceleration RMS -> MQTT telemetry."""
import math
import os
import time
from collections import deque

from mqtt_common import BASE, DEVICE_ID, connect, new_client, publish_json, read_sensor

SENSOR = os.getenv("ACCEL_SENSOR_NAME", "ACCELEROMETER")
INTERVAL = float(os.getenv("SAMPLE_INTERVAL_SECONDS", "1"))
WINDOW = max(2, int(os.getenv("WINDOW_SIZE", "5")))
GRAVITY = 9.81
topic = f"{BASE}/edge/motion/telemetry"
errors = deque(maxlen=WINDOW)
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
    client = new_client(f"smartdesk-{DEVICE_ID}-motion")
    client.on_message = on_message
    connect(client)
    print(f"Motion edge running; sensor={SENSOR}, topic={topic}")
    try:
        while True:
            try:
                xyz = read_sensor(SENSOR)
                if len(xyz) < 3:
                    raise ValueError(f"Expected x,y,z accelerometer values; got {xyz}")
                x, y, z = xyz[:3]
                magnitude = math.sqrt(x*x + y*y + z*z)
                dynamic = magnitude - GRAVITY
                errors.append(dynamic * dynamic)
                rms = math.sqrt(sum(errors) / len(errors))
                publish_json(client, topic, {
                    "device_id": DEVICE_ID,
                    "sensor": "accelerometer",
                    "accel_x": round(x, 3),
                    "accel_y": round(y, 3),
                    "accel_z": round(z, 3),
                    "motion_rms": round(rms, 4),
                    "window": len(errors),
                    "armed": armed,
                })
                print(f"RMS={rms:.3f} m/s^2 (window={len(errors)})")
            except Exception as exc:
                print(f"Sensor read/publish error: {exc}")
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("Stopping motion edge...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
