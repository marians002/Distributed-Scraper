from python:3-alpine

run apk update && apk add iptables && echo "net.ipv4.ip_forward=1"

cmd /bin/sh