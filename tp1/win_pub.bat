@echo off
title TP1 - mosquitto_pub
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto_pub -h localhost -t sensors/drone01/altitude -m 120.5 -d
.\mosquitto_pub.exe -h localhost -t sensors/drone01/altitude -m 120.5 -d
echo.
echo C:\Users\LeMonde\mosquitto^> mosquitto_pub -h localhost -t sensors/machines/m1/temperature/celsius -m 22.4 -d
.\mosquitto_pub.exe -h localhost -t sensors/machines/m1/temperature/celsius -m 22.4 -d
echo.
echo C:\Users\LeMonde\mosquitto^> mosquitto_pub -h localhost -t sensors/machines/m2/temperature/fahrenheit -m 71.6 -d
.\mosquitto_pub.exe -h localhost -t sensors/machines/m2/temperature/fahrenheit -m 71.6 -d
