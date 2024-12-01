# Dockerfile
FROM base_server:latest

WORKDIR /app

COPY server/server.py ./server.py
COPY server/server.sh /usr/local/bin/server.sh

RUN chmod +x /usr/local/bin/server.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "/usr/local/bin/server.sh && python /app/server.py"]