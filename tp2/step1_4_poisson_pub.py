"""TP2 - Step 1.4: Poisson publication of the dataset (lambda messages per second on average).

usage: python step1_4_poisson_pub.py [broker] [lambda] [count]
"""
import json
import math
import random
import sys
import time

from sensor_sim import generate_dataset, make_client


def next_time_interval(l):
    n = random.random() * 1.0
    inter_event_time = -math.log(1.0 - n) / l
    return inter_event_time


# l: lambda number of messages per second (poissonian arrival model)
def generation_pub_messages_one_topic(client, l, dataset):
    t = 0.0
    for i, value in enumerate(dataset):
        tt = next_time_interval(l)
        time.sleep(tt)  # wait
        t += tt
        payload = json.dumps({"seq": i, "ts": round(time.time(), 3), "value": round(value, 3)})
        client.publish("sensors/temperature/raw", payload)
        print(f"Publishing Time: {t:8.3f}s  (dt={tt:.3f}s)  {payload}")


broker_address = sys.argv[1] if len(sys.argv) > 1 else "192.168.174.133"
l = float(sys.argv[2]) if len(sys.argv) > 2 else 10
nbre_messages = int(sys.argv[3]) if len(sys.argv) > 3 else 300

print("Start message publication....")
client = make_client("Pub")
client.connect(broker_address)
client.loop_start()
print(f"start poisson publish, lambda={l} msg/s")
generation_pub_messages_one_topic(client, l, generate_dataset(nbre_messages))
client.loop_stop()
client.disconnect()
