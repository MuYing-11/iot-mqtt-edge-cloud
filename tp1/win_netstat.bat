@echo off
title TP1 - netstat broker port
echo C:\> netstat -an ^| findstr 1883
netstat -an | findstr 1883
