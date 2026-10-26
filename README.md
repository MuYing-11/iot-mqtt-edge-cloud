# IoT MQTT Edge to Cloud

MQTT pipeline from simulated sensors to a Raspberry Pi edge gateway, then to a cloud broker on AWS EC2.

```
PC simulator --MQTT--> Raspberry Pi (Mosquitto + edge filter, Node-RED) --MQTT--> EC2 (Mosquitto + Next.js dashboard)
```

- `tp1/` : first MQTT exchanges (Mosquitto on Windows and on the Pi, Python publisher/subscriber)
- `tp2/` : periodic and Poisson publishers, edge sampling and moving average, cloud viewer, analysis
- `edge/` : Raspberry Pi gateway (filtering / data reduction, runtime control on `edge/control`) and Node-RED flow
- `simulator/` : PyQt6 sensor simulator with live, 3D, data-flow and throughput views
- `cloud/` : EC2 broker config (Mosquitto, ACL), nginx, systemd service and the Next.js dashboard
- `report/` : report (HTML + PDF), screenshots and Wireshark captures

## Credentials

Broker address and passwords are read from `cloud/secrets.env` (not committed):

```
CLOUD_HOST=...
CLOUD_PORT=1883
EDGE_USER=...
EDGE_PASS=...
VIEWER_USER=...
VIEWER_PASS=...
```

The dashboard reads `MQTT_URL`, `MQTT_USER` and `MQTT_PASS` from its environment.
