@echo off
title TP2 - PC sensor 1_2
cd /d %~dp0
echo %CD%^> python step1_2_periodic_pub.py 192.168.174.133 0.1 300
python step1_2_periodic_pub.py 192.168.174.133 0.1 300
