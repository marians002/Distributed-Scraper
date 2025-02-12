FROM router:base
# rm router/
COPY router/route.sh /root/route.sh

RUN chmod +x /root/route.sh

ENTRYPOINT /root/route.sh