from flask import Flask, render_template, request
import requests
import json
from flask_cors import CORS
import socket
import threading
import logging
import struct

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Multicast settings
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000
SERVER_IP = None
SERVER_PORT = None
SCRAPE_REQUEST = 10


# Añadir esta función en client.py
def send_scrape_request(url):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)  # Esperar 5 segundos por una respuesta
    sock.bind(("",MULTICAST_PORT))

    # Unirse al grupo multicast
    group = socket.inet_aton(MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    # Enviar solicitud de descubrimiento
    discover_message = b"DISCOVER_NODE"
    sock.sendto(discover_message, (MULTICAST_GROUP, MULTICAST_PORT))

    # Esperar respuesta de un nodo
    try:
        logging.info("Esperando respuesta de un nodo...")
        while True:
            data, addr = sock.recvfrom(1024)
            if data == b"DISCOVER_NODE":
                continue
            node_ip = data.decode()  # La IP del nodo activo
            logging.info(f"Nodo descubierto: {node_ip}")
            break

        # Ahora el cliente puede conectarse directamente al nodo
        # Ejemplo de conexión TCP:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setblocking(True)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.connect((node_ip, 8001))  # Conectar al puerto 5000 del nodo
        logging.info(f"Conectado al nodo {node_ip}")
        
    except socket.timeout:
        logging.critical("No se recibió respuesta de ningún nodo.") 
    finally:
        sock.close()
    
    # Asegurar que el servidor está descubierto
    client_socket.send(f"{SCRAPE_REQUEST},{url}".encode())  # 14 = SCRAPE_REQUEST
        
    # Recibir confirmación
    response = client_socket.recv(1024000).decode()
    client_socket.close()
    return response

def discover_server():
    # # Create a UDP socket
    # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # sock.bind(('', MULTICAST_PORT))

    # # Join the multicast group
    # mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton('0.0.0.0')
    # sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    # logging.info("Waiting to discover server...")
    # while True:
    #     # Receive the server's broadcast message
    #     data, _ = sock.recvfrom(1024)
    #     message = data.decode('utf-8')
    #     if message.startswith('SERVER_ADDRESS:'):
    #         _, address = message.split(':')
    #         SERVER_IP, SERVER_PORT = address.split(',')
    #         SERVER_PORT = int(SERVER_PORT)
    #         logging.info(f"Discovered server at {SERVER_IP}:{SERVER_PORT}")
    #         break
    # Crear socket multicast
    pass
    
    
            


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    logging.info(f"Initiating scrape for URL: {url}")
    response = send_scrape_request(url)
    logging.info(f'Respuesta del servidor: {response}')
    return f"Scrape Status: {response}"
    


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