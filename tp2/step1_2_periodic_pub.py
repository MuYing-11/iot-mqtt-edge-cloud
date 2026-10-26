"""TP2 - Step 1.2: publish the dataset periodically to the Edge broker (Raspberry Pi).

usage: python step1_2_periodic_pub.py [broker] [period_s] [count]
"""
import json
import sys
import time

from sensor_sim import generate_dataset, make_client

broker = sys.argv[1] if len(sys.argv) > 1 else "192.168.174.133"
period = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
count = int(sys.argv[3]) if len(sys.argv) > 3 else 300

dataset = generate_dataset(count)
client = make_client("pc-sensor-periodic")
client.connect(broker, 1883)
client.loop_start()
print(f"publishing {count} values every {period}s to {broker} on sensors/temperature/raw")

t0 = time.time()
for i, v in enumerate(dataset):
    payload = json.dumps({"seq": i, "ts": round(time.time(), 3), "value": round(v, 3)})
    client.publish("sensors/temperature/raw", payload)
    print(f"[{time.time() - t0:7.2f}s] {payload}")
    time.sleep(period)

client.loop_stop()
client.disconnect()
