@echo off
title TP2 - PC sensor 1_4
cd /d %~dp0
echo %CD%^> python step1_4_poisson_pub.py 192.168.174.133 10 300
python step1_4_poisson_pub.py 192.168.174.133 10 300
