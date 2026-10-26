@echo off
title Mosquitto broker - Windows PC
cd /d C:\Users\LeMonde\mosquitto
echo C:\Users\LeMonde\mosquitto^> mosquitto -v -c mosquitto-windows.conf
.\mosquitto.exe -v -c "%~dp0mosquitto-windows.conf"
