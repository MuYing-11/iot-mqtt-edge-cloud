@echo off
title TP1 - Python paho subscriber (Windows)
cd /d %~dp0
echo %CD%^> python mqtt_subscriber.py localhost
python mqtt_subscriber.py localhost
