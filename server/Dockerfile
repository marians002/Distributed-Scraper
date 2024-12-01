FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt
RUN chmod +x /app/server.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "/app/server.sh && python /app/server.py"]