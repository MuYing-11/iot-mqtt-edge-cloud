@echo off
title TP1 - PC broker receives the Pi data
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto_sub -h localhost -t sensors/machines/# -t house/# -v
.\mosquitto_sub.exe -h localhost -t sensors/machines/# -t house/# -v
