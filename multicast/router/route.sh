#!/bin/sh
iptables -t nat -A POSTROUTING -s 10.0.10.0/24 -o eth0 -j MASQUERADE
iptables -t nat -A POSTROUTING -s 10.0.11.0/24 -o eth0 -j MASQUERADE
sleep 5
ip route add 224.0.0.0/4 dev eth2
python /root/multicast_proxy.py