@echo off
title TP1 - PC publishes to the Raspberry Pi broker
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto_pub -h 192.168.174.133 -t test -m "Hello MQTT" -d
.\mosquitto_pub.exe -h 192.168.174.133 -t test -m "Hello MQTT" -d
echo.
echo C:\Users\LeMonde\mosquitto^> mosquitto_pub -h 192.168.174.133 -t house/bulb1 -m on -d
.\mosquitto_pub.exe -h 192.168.174.133 -t house/bulb1 -m on -d
