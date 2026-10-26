@echo off
title TP1 - mosquitto_sub wildcard
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto_sub -v -h localhost -t sensors/machines/+/temperature/+
.\mosquitto_sub.exe -v -h localhost -t sensors/machines/+/temperature/+
