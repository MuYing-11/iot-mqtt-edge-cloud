"""Raspberry Pi edge gateway: filtering + data reduction between the sensors and the cloud.

    sensors/<name>/raw  (local Mosquitto, from the PC simulator)
          |  filter / reduce   (mode: sampling | moving (centred) | passthrough)
          v
    edge/<name>/filtered  (local, Node-RED dashboard)
    cloud/<name>          (EC2 broker, Next.js dashboard)

Also publishes edge/stats + cloud/edge/stats (throughput in/out every second),
cloud/edge/system (Pi health), cloud/alerts (threshold events detected at the edge).
The mode can be changed at runtime by publishing JSON on edge/control, e.g.
    {"mode": "moving", "period": 1.0, "window": 20}
"""
import collections
import json
import os
import socket
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tp2"))
import cloud_env  # noqa: E402
from sensor_sim import make_client  # noqa: E402

UNITS = {"temperature": "°C", "humidity": "%", "pressure": "hPa", "co2": "ppm"}
THRESHOLDS = {"temperature": 30.0, "humidity": 80.0, "co2": 600.0}
env = cloud_env.load()

config = {"mode": "moving", "period": 1.0, "window": 20}
windows = collections.defaultdict(lambda: collections.deque(maxlen=config["window"]))
batches = collections.defaultdict(list)
alarm_state = {}
counters = {"in_msgs": 0, "in_bytes": 0, "out_msgs": 0, "out_bytes": 0}
totals = dict(counters)
lock = threading.Lock()


def mqtt_size(topic, payload):
    """Size of a QoS 0 MQTT PUBLISH packet (fixed header + topic + payload)."""
    remaining = 2 + len(topic.encode()) + len(payload)
    return 1 + (1 if remaining < 128 else 2) + remaining


def publish_cloud(topic, payload, count=True, **kw):
    data = json.dumps(payload)
    cloud.publish(topic, data, **kw)
    if count:
        with lock:
            counters["out_msgs"] += 1
            counters["out_bytes"] += mqtt_size(topic, data.encode())


def reset_windows():
    for name in list(windows):
        windows[name] = collections.deque(windows[name], maxlen=config["window"])


def on_local_message(client, userdata, msg):
    if msg.topic == "edge/control":
        try:
            config.update({k: v for k, v in json.loads(msg.payload).items() if k in config})
            config["period"] = max(0.1, float(config["period"]))
            config["window"] = max(1, int(config["window"]))
            reset_windows()
            print("control ->", config, flush=True)
            local.publish("edge/config", json.dumps(config), retain=True)
            publish_cloud("cloud/edge/config", config, count=False, retain=True)
        except (ValueError, TypeError) as e:
            print("bad control message:", e)
        return
    name = msg.topic.split("/")[1]
    try:
        raw = json.loads(msg.payload)
        value = float(raw["value"])
        ts = float(raw.get("ts", time.time()))
    except (ValueError, KeyError, TypeError):
        return
    with lock:
        counters["in_msgs"] += 1
        counters["in_bytes"] += mqtt_size(msg.topic, msg.payload)
        windows[name].append((ts, value))
        batches[name].append(value)
    if config["mode"] == "passthrough":
        emit(name, value, 1, ts_center=ts)
    check_threshold(name, value)


def check_threshold(name, value):
    limit = THRESHOLDS.get(name)
    if limit is None:
        return
    active = value > limit
    if active != alarm_state.get(name, False):
        alarm_state[name] = active
        event = {"ts": round(time.time(), 3), "sensor": name, "value": round(value, 2),
                 "limit": limit, "state": "ALARM" if active else "OK"}
        local.publish("edge/alerts", json.dumps(event))
        publish_cloud("cloud/alerts", event)
        print("alert:", event, flush=True)


def emit(name, value, n, lo=None, hi=None, ts_center=None):
    payload = {"ts": round(time.time(), 3), "value": round(value, 3), "n": n,
               "unit": UNITS.get(name, ""), "method": config["mode"]}
    if ts_center is not None:
        payload["ts_center"] = round(ts_center, 3)
    if lo is not None:
        payload.update(min=round(lo, 3), max=round(hi, 3))
    local.publish(f"edge/{name}/filtered", json.dumps(payload))
    publish_cloud(f"cloud/{name}", payload)


def reducer_loop():
    while True:
        time.sleep(config["period"])
        if config["mode"] == "passthrough":
            continue
        with lock:
            work = {name: (list(batches[name]), list(windows[name])) for name in batches}
            for name in batches:
                batches[name].clear()
        for name, (batch, window) in work.items():
            if not batch:
                continue
            if config["mode"] == "moving":
                # centred moving average: mean of the window, dated at the centre of the window
                emit(name, sum(v for _, v in window) / len(window), len(batch), min(batch), max(batch),
                     ts_center=sum(t for t, _ in window) / len(window))
            else:
                # sampling: mean of the samples received during the period, dated at its end
                emit(name, sum(batch) / len(batch), len(batch), min(batch), max(batch))


def stats_loop():
    started = time.time()
    while True:
        time.sleep(1.0)
        with lock:
            snap = dict(counters)
            for k in counters:
                totals[k] += counters[k]
                counters[k] = 0
            tot = dict(totals)
        stats = {"ts": round(time.time(), 3), "uptime": round(time.time() - started),
                 "in_msgs_s": snap["in_msgs"], "in_bytes_s": snap["in_bytes"],
                 "out_msgs_s": snap["out_msgs"], "out_bytes_s": snap["out_bytes"],
                 "total_in_msgs": tot["in_msgs"], "total_in_bytes": tot["in_bytes"],
                 "total_out_msgs": tot["out_msgs"], "total_out_bytes": tot["out_bytes"],
                 "reduction_pct": round(100 * (1 - tot["out_bytes"] / tot["in_bytes"]), 1)
                 if tot["in_bytes"] else 0.0, **config}
        local.publish("edge/stats", json.dumps(stats))
        publish_cloud("cloud/edge/stats", stats, count=False)


def read_system():
    with open("/proc/loadavg") as f:
        load1 = float(f.read().split()[0])
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            k, v = line.split(":")
            mem[k] = int(v.split()[0])
    with open("/proc/uptime") as f:
        uptime = float(f.read().split()[0])
    return {"host": socket.gethostname(), "load1": load1, "cpus": os.cpu_count(),
            "mem_used_pct": round(100 * (1 - mem["MemAvailable"] / mem["MemTotal"]), 1),
            "uptime_s": round(uptime)}


def cpu_percent(prev=[None]):
    with open("/proc/stat") as f:
        fields = [int(x) for x in f.readline().split()[1:]]
    idle, total = fields[3] + fields[4], sum(fields)
    pct = 0.0
    if prev[0]:
        d_idle, d_total = idle - prev[0][0], total - prev[0][1]
        pct = round(100 * (1 - d_idle / d_total), 1) if d_total else 0.0
    prev[0] = (idle, total)
    return pct


def system_loop():
    cpu_percent()
    while True:
        time.sleep(5)
        info = {"ts": round(time.time(), 3), "cpu_pct": cpu_percent(), **read_system()}
        local.publish("edge/system", json.dumps(info))
        publish_cloud("cloud/edge/system", info, count=False)


def on_cloud_connect(client, userdata, flags, rc, props=None):
    print("cloud connected:", rc, flush=True)
    client.publish("cloud/edge/status", json.dumps({"state": "online", "ts": time.time()}), retain=True)
    client.publish("cloud/edge/config", json.dumps(config), retain=True)


def on_local_connect(client, userdata, flags, rc, props=None):
    print("local broker connected:", rc, flush=True)
    client.subscribe([("sensors/+/raw", 0), ("edge/control", 0)])
    client.publish("edge/config", json.dumps(config), retain=True)


cloud = make_client(f"edge-gateway-{socket.gethostname()}")
cloud.username_pw_set(env["EDGE_USER"], env["EDGE_PASS"])
cloud.will_set("cloud/edge/status", json.dumps({"state": "offline"}), retain=True)
cloud.on_connect = on_cloud_connect
cloud.reconnect_delay_set(1, 30)
cloud.connect_async(env["CLOUD_HOST"], int(env["CLOUD_PORT"]), keepalive=30)
cloud.loop_start()

local = make_client("edge-gateway-local")
local.on_connect = on_local_connect
local.on_message = on_local_message
local.connect("localhost", 1883)

for target in (reducer_loop, stats_loop, system_loop):
    threading.Thread(target=target, daemon=True).start()
print(f"edge gateway started, mode={config}", flush=True)
local.loop_forever()
