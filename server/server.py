from flask import Flask, request, jsonify
from html_fetcher import fetch_html, scrape
from DB_manager import init_db, fetch_data_from_db
import socket
import threading
import time
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Multicast settings
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000


def broadcast_server_address():
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    logging.info("Starting server address broadcast")
    while True:
        # Broadcast the server's address
        message = f'SERVER_ADDRESS:10.0.11.2,5002'  # Replace with actual IP and port
        sock.sendto(message.encode('utf-8'), (MULTICAST_GROUP, MULTICAST_PORT))
        logging.info(f"Broadcasting server address: {message}")
        time.sleep(5)  # Broadcast every 5 seconds


# Start the broadcast thread
broadcast_thread = threading.Thread(target=broadcast_server_address)
broadcast_thread.daemon = True
broadcast_thread.start()


@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    data = request.json
    urls = data.get('url', [])
    settings = data.get('settings', {})
    logging.info(f"Received scrape request for URLs: {urls} with settings: {settings}")
    results = scrape(urls, settings)
    logging.info(f"Scrape completed for URLs: {urls}")
    return jsonify(results)


if __name__ == '__main__':
    logging.info("Initializing database")
    init_db()
    logging.info("Starting server application")
    app.run(host='0.0.0.0', port=5002)
