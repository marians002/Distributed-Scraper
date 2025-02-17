from flask import Flask, render_template, request
import requests
import json
from flask_cors import CORS
import socket
import threading
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Multicast settings
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000
SERVER_IP = None
SERVER_PORT = None


def discover_server():
    global SERVER_IP, SERVER_PORT

    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', MULTICAST_PORT))

    # Join the multicast group
    mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton('0.0.0.0')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    logging.info("Waiting to discover server...")
    while True:
        # Receive the server's broadcast message
        data, _ = sock.recvfrom(1024)
        message = data.decode('utf-8')
        if message.startswith('SERVER_ADDRESS:'):
            _, address = message.split(':')
            SERVER_IP, SERVER_PORT = address.split(',')
            SERVER_PORT = int(SERVER_PORT)
            logging.info(f"Discovered server at {SERVER_IP}:{SERVER_PORT}")
            break


# Start the server discovery in a separate thread
discovery_thread = threading.Thread(target=discover_server)
discovery_thread.daemon = True
discovery_thread.start()


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    urls = [request.form['url']]
    scrape_option = request.form['scrapeOption']
    logging.info(f"Received scrape request for URL: {urls[0]} with option: {scrape_option}")

    settings = {
        'extract_html': scrape_option == 'html',
        'extract_css': scrape_option == 'css',
        'extract_js': scrape_option == 'js'
    }

    response = send_request_to_server(urls, settings)
    return response


def send_request_to_server(url, settings):
    if SERVER_IP is None or SERVER_PORT is None:
        logging.warning("Server not discovered yet.")
        return "Server not discovered yet. Please try again."

    logging.info(f"Sending request to server at {SERVER_IP}:{SERVER_PORT}")
    response = requests.post(f'http://{SERVER_IP}:{SERVER_PORT}/scrape', json={'url': url, 'settings': settings})
    return format_response(response.text)


def format_response(response_text):
    try:
        # Parse the JSON response
        response_data = json.loads(response_text)

        # Extract the URL and content
        url = list(response_data.keys())[0]
        content = response_data[url].get("html", "") or response_data[url].get("css", "") or response_data[url].get(
            "js", "")
        content_type = "HTML" if "html" in response_data[url] else (
            "CSS" if "css" in response_data[url] else "JavaScript")

        # Format the output in a user-friendly way
        formatted_output = f"""
        Scraped URL: {url}
        Content Type: {content_type}
        Content:
        -------------------------
        {content}
        -------------------------
        """

        return formatted_output

    except json.JSONDecodeError:
        logging.error("Invalid JSON response.")
        return "Invalid JSON response."
    except KeyError:
        logging.error("The response format is not as expected.")
        return "The response format is not as expected."


if __name__ == '__main__':
    logging.info("Starting client application")
    app.run(host="0.0.0.0", port=5005)