#!/bin/bash
# shown in the report: state of the cloud broker on EC2
p(){ printf '\033[1;32mubuntu@ec2\033[0m:\033[1;34m~\033[0m$ %s\n' "$1"; eval "$1"; }
p "lsb_release -ds; hostname -I"
p "systemctl is-active mosquitto nginx iot-dashboard"
p "cat /etc/mosquitto/conf.d/cloud.conf"
p "sudo cat /etc/mosquitto/acl"
p "sudo ss -tlnp | grep -E ':1883|:80 |:3000' | awk '{print \$1, \$4, \$6}'"
p 'mosquitto_sub -h localhost -t "cloud/#" -v -C 6 -u viewer -P "$(grep MQTT_PASS ~/dashboard/.env.mqtt | cut -d= -f2)" | cut -c1-150'
p 'mosquitto_pub -h localhost -t cloud/test -m anonymous-should-fail; echo "exit code: $?"'
