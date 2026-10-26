@echo off
title TP1 - Python paho publisher (Windows)
cd /d %~dp0
echo %CD%^> python mqtt_publisher.py localhost control1 5
python mqtt_publisher.py localhost control1 5
