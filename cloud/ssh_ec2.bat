@echo off
mode con: cols=135 lines=46
title EC2 cloud broker - ssh ubuntu@13.60.75.46
cd /d %~dp0..
echo C:\^> ssh -i crt.pem ubuntu@13.60.75.46
"C:\Program Files\Git\usr\bin\ssh.exe" -t -i crt.pem ubuntu@13.60.75.46 "bash ~/ec2_check.sh; exec bash"
