"""TP2 - Step 3.1 / 3.3 (runs on the PC): compare sensor data and cloud data.

Subscribes at the same time to the raw sensor topic on the Edge broker and to
the reduced topic on the cloud broker (EC2), records DURATION seconds, then
plots both curves on the same time axis.

usage: python step3_cloud_viewer.py [duration_s] [output.png] [title]
"""
import json
import sys
import time

import matplotlib.pyplot as plt

import cloud_env
from sensor_sim import make_client

DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 60
OUT = sys.argv[2] if len(sys.argv) > 2 else None
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Sensor data vs cloud data"
env = cloud_env.load()

raw, reduced = [], []
raw_bytes = cloud_bytes = 0


def on_raw(client, userdata, msg):
    global raw_bytes
    raw_bytes += len(msg.payload)
    raw.append((time.time(), json.loads(msg.payload)["value"]))


def on_cloud(client, userdata, msg):
    global cloud_bytes
    cloud_bytes += len(msg.payload)
    m = json.loads(msg.payload)
    # centred moving average: plot the value at the centre of its window
    reduced.append((m.get("ts_center", time.time()), m["value"]))


edge = make_client("viewer-edge")
edge.on_message = on_raw
edge.connect("192.168.174.133", 1883)
edge.subscribe("sensors/temperature/raw")
edge.loop_start()

cloud = make_client("viewer-cloud")
cloud.on_message = on_cloud
cloud.username_pw_set(env["VIEWER_USER"], env["VIEWER_PASS"])
cloud.connect(env["CLOUD_HOST"], int(env["CLOUD_PORT"]))
cloud.subscribe("cloud/temperature")
cloud.loop_start()

print(f"recording {DURATION}s ...")
t0 = time.time()
time.sleep(DURATION)
edge.loop_stop()
cloud.loop_stop()

print(f"sensor side : {len(raw)} msgs, {raw_bytes} payload bytes")
print(f"cloud side  : {len(reduced)} msgs, {cloud_bytes} payload bytes")
if raw:
    print(f"reduction   : {100 * (1 - len(reduced) / len(raw)):.1f}% messages, "
          f"{100 * (1 - cloud_bytes / max(raw_bytes, 1)):.1f}% payload bytes")

plt.figure(figsize=(11, 4.5))
plt.plot([t - t0 for t, _ in raw], [v for _, v in raw], label="Original (sensor -> edge)",
         color="#1f77b4", linewidth=0.8)
plt.plot([t - t0 for t, _ in reduced], [v for _, v in reduced], label="Reduced (edge -> cloud)",
         color="#ff7f0e", linewidth=2, marker="o", markersize=3)
plt.xlabel("time (s)")
plt.ylabel("temperature (°C)")
plt.title(TITLE)
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
if OUT:
    plt.savefig(OUT, dpi=130)
    with open(OUT.rsplit(".", 1)[0] + ".json", "w") as f:
        json.dump({"t0": t0, "raw": raw, "reduced": reduced,
                   "raw_bytes": raw_bytes, "cloud_bytes": cloud_bytes}, f)
else:
    plt.show()
