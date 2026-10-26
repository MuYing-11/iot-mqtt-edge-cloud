"""TP1 - MQTT publisher (paho): switches a bulb and publishes temperature readings.

usage: python mqtt_publisher.py [broker] [client_id] [count]
"""
import random
import sys
import time

import paho.mqtt.client as paho

broker = sys.argv[1] if len(sys.argv) > 1 else "localhost"
client_id = sys.argv[2] if len(sys.argv) > 2 else "control1"
count = int(sys.argv[3]) if len(sys.argv) > 3 else 5
port = 1883


def on_publish(client, userdata, mid, *args):
    print("data published (mid=%d)" % mid)


if hasattr(paho, "CallbackAPIVersion"):
    client1 = paho.Client(paho.CallbackAPIVersion.VERSION2, client_id)
else:
    client1 = paho.Client(client_id)
client1.on_publish = on_publish
client1.connect(broker, port)
client1.loop_start()

ret = client1.publish("house/bulb1", "on")
time.sleep(0.5)
for i in range(count):
    temp = round(random.uniform(19, 24), 2)
    client1.publish(f"sensors/machines/{client_id}/temperature/celsius", temp)
    print(f"[{client_id}] sensors/machines/{client_id}/temperature/celsius -> {temp}")
    time.sleep(1)
client1.publish("house/bulb1", "off")
time.sleep(0.5)
client1.loop_stop()
client1.disconnect()
