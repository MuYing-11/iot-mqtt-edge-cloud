"""TP2 - Step 3.2 (runs on the Raspberry Pi edge): moving-average filtering.

Same reduction as step 2 (one message per PERIOD to the cloud), but the
value sent is the mean of a sliding window of the last WINDOW raw samples
instead of the mean of the samples received during the period only. The
window overlaps consecutive periods, so the reduced curve follows the sensor
curve more faithfully (less noise from small, uneven Poisson batches).

usage: python3 step3_edge_moving_avg.py [period_s] [window]
"""
import collections
import json
import sys
import threading
import time

import cloud_env
from sensor_sim import make_client

PERIOD = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
WINDOW = int(sys.argv[2]) if len(sys.argv) > 2 else 30
env = cloud_env.load()

window = collections.deque(maxlen=WINDOW)
received, lock = 0, threading.Lock()


def on_message(client, userdata, msg):
    global received
    with lock:
        m = json.loads(msg.payload)
        window.append((m.get("ts", time.time()), m["value"]))
        received += 1


edge = make_client("edge-mavg-in")
edge.on_message = on_message
edge.connect("localhost", 1883)
edge.subscribe("sensors/temperature/raw")
edge.loop_start()

cloud = make_client("edge-mavg-out")
cloud.username_pw_set(env["EDGE_USER"], env["EDGE_PASS"])
cloud.connect(env["CLOUD_HOST"], int(env["CLOUD_PORT"]))
cloud.loop_start()

print(f"edge moving average: window={WINDOW}, publish every {PERIOD}s -> cloud/temperature")
while True:
    time.sleep(PERIOD)
    with lock:
        if not window:
            continue
        window_average = round(sum(v for _, v in window) / len(window), 3)
        ts_center = round(sum(t for t, _ in window) / len(window), 3)
        n, received = received, 0
    payload = json.dumps({"ts": round(time.time(), 3), "value": window_average,
                          "ts_center": ts_center, "n": n, "window": len(window),
                          "method": "moving_average"})
    cloud.publish("cloud/temperature", payload)
    print(f"{n:3d} raw msgs -> 1 msg  {payload}")
