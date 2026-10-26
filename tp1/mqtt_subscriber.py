"""TP1 - MQTT subscriber (paho). Works on Windows and on the Raspberry Pi.

usage: python mqtt_subscriber.py [broker] [topic ...]
default: localhost, topics "house/#" "sensors/#" "$SYS/broker/clients/connected"
"""
import sys

import paho.mqtt.client as mqtt

broker = sys.argv[1] if len(sys.argv) > 1 else "localhost"
topics = sys.argv[2:] or ["house/#", "sensors/#", "$SYS/broker/clients/connected"]


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc, properties=None):
    print("Connected with result code " + str(rc))
    for t in topics:
        client.subscribe(t)
        print("subscribed to", t)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic + " " + msg.payload.decode(errors="replace"))


if hasattr(mqtt, "CallbackAPIVersion"):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
else:
    client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(broker, 1883, 60)

# Blocking call that processes network traffic, dispatches callbacks and handles reconnecting.
client.loop_forever()
