FROM chord_base

WORKDIR /app

COPY chord/ /app/

RUN chmod +x /app/routing.sh

ENTRYPOINT /app/routing.sh