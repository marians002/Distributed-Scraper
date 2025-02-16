# db.Dockerfile.base
FROM server_base:latest

WORKDIR /app

COPY server/ /app/

RUN chmod +x /app/server.sh

ENTRYPOINT ["/bin/bash", "-c", "/app/server.sh && python /app/server.py"]