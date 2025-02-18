from flask import Flask, render_template, request
import requests
import json
from flask_cors import CORS
import socket
import logging
import struct
import socket
import json


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
FIND_RESPONSIBLE = 11


@app.route('/')
def home():
    return render_template('frontend.html')


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    settings = request.form['scrapeOption']
    logging.info(f"Initiating scrape for URL: {url}. Settings: {settings}")
    
    response = send_scrape_request(url, settings)
    return format_response(response)

def send_scrape_request(url, settings):
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
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setblocking(True)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.connect((node_ip, 8001))  # Conectar al puerto 5000 del nodo
        logging.info(f"Conectado al nodo {node_ip}")
        
    except socket.timeout:
        logging.critical("No se recibió respuesta de ningún nodo.") 
    finally:
        sock.close()
    
    logging.info("Enviando petición de scrape")
    
    # Buscar el IP del servidor responsable
    client_socket.send(f"{FIND_RESPONSIBLE},{url}".encode())
    node_ip = client_socket.recv(1024).decode()
    client_socket.close()
    
    # Asegurar que el servidor está descubierto
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setblocking(True)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.connect((node_ip, 8001))  # Conectar al puerto 8001 del nodo
    client_socket.send(f"{SCRAPE_REQUEST},{url},{settings}".encode())
    
    # Leer tamaño
    header = client_socket.recv(4)
    size = struct.unpack("!I", header)[0]
    
    # Leer datos
    received = bytearray()
    while len(received) < size:
        chunk = client_socket.recv(1024000)
        if not chunk:
            break
        received.extend(chunk)
    
    # Procesar
    data = received.decode("utf-8")
    client_socket.close()
    return data   


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