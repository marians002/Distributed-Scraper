# Dockerfile
FROM base_client:latest

WORKDIR /app

COPY client/client.py ./client.py
COPY client/client.sh /usr/local/bin/client.sh

RUN chmod +x /usr/local/bin/client.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "/usr/local/bin/client.sh && python /app/client.py"]