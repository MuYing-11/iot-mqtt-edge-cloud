@echo off
title TP2 - PC sensor pois60
cd /d %~dp0
echo %CD%^> python step1_4_poisson_pub.py 192.168.174.133 10 600
python step1_4_poisson_pub.py 192.168.174.133 10 600
