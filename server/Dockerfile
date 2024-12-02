# Dockerfile
FROM base_server:latest

WORKDIR /app

COPY server/ /app/

RUN chmod +x /app/server.sh

EXPOSE 5002

ENTRYPOINT ["/bin/bash", "-c", "/app/server.sh && python /app/server.py"]