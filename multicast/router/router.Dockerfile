from router:base

copy route.sh /root/route.sh

copy multicast_proxy.py /root/multicast_proxy.py

run chmod +x /root/route.sh

entrypoint /root/route.sh