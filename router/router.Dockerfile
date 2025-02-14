from router:base

copy route.sh /root/route.sh

run chmod +x /root/route.sh

entrypoint /root/route.sh