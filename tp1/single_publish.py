"""TP1 - Example publisher from the lab sheet (publish.single)."""
import paho.mqtt.publish as publish

publish.single(
    "iot/temp",
    "25",
    hostname="localhost"
)
print("published 25 on iot/temp")
