# db.Dockerfile.base
FROM client_base:latest

WORKDIR /app

COPY client/ /app/

RUN chmod +x /app/client.sh

ENTRYPOINT /app/client.sh