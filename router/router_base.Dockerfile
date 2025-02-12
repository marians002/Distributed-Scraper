FROM alpine

RUN apk add iptables && echo "net.ipv4.ip_forward=1" | tee -a /etc/sysctl.conf

CMD /bin/sh