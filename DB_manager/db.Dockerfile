FROM db_base:latest

WORKDIR /app

COPY DB_manager/ /app/

ENTRYPOINT ["python", "/app/DB_manager.py"]
