FROM router:base

COPY route.sh /root/route.sh

COPY multicast_proxy.py /root/multicast_proxy.py

RUN chmod +x /root/route.sh

ENTRYPOINT /root/route.sh