FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -r ./requirements.txt
RUN chmod +x ./client.sh

EXPOSE 5000

ENTRYPOINT ["/bin/bash", "-c", "/app/client.sh && python /app/client.py"]