"""TP2 - Step 2.1 (runs on the Raspberry Pi edge): sampling reduction.

Receives the raw sensor data from the local Edge broker, stores it in a list,
and every PERIOD seconds publishes the average of that list to the cloud
broker (EC2), then empties the list.

usage: python3 step2_edge_sampling.py [period_s]
"""
import json
import sys
import threading
import time

import cloud_env
from sensor_sim import make_client

PERIOD = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
env = cloud_env.load()

buffer, lock = [], threading.Lock()


def on_message(client, userdata, msg):
    with lock:
        buffer.append(json.loads(msg.payload)["value"])


edge = make_client("edge-sampling-in")
edge.on_message = on_message
edge.connect("localhost", 1883)
edge.subscribe("sensors/temperature/raw")
edge.loop_start()

cloud = make_client("edge-sampling-out")
cloud.username_pw_set(env["EDGE_USER"], env["EDGE_PASS"])
cloud.connect(env["CLOUD_HOST"], int(env["CLOUD_PORT"]))
cloud.loop_start()

print(f"edge sampling: average every {PERIOD}s -> {env['CLOUD_HOST']} cloud/temperature")
while True:
    time.sleep(PERIOD)
    with lock:
        samples = buffer[:]
        buffer.clear()
    if not samples:
        continue
    avg = sum(samples) / len(samples)
    payload = json.dumps({"ts": round(time.time(), 3), "value": round(avg, 3),
                          "n": len(samples), "method": "sampling"})
    cloud.publish("cloud/temperature", payload)
    print(f"{len(samples):3d} raw msgs -> 1 msg  {payload}")
