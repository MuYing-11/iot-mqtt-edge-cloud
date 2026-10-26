@echo off
title TP1 - mosquitto_sub drone01 (debug)
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto_sub -V mqttv311 -t sensors/drone01/altitude -d
.\mosquitto_sub.exe -V mqttv311 -t sensors/drone01/altitude -d
