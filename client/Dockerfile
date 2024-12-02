# Dockerfile
FROM client_base:latest

WORKDIR /app

COPY client/ /app/

RUN chmod +x /app/client.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "/app/client.sh && python /app/client.py"]