from alpine

run apk add iptables && echo "net.ipv4.ip_forward=1" | tee -a /etc/sysctl.conf

cmd /bin/sh