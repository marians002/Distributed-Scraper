import hashlib
import json
import logging
import random
import socket
import string
import struct
from flask import Flask, render_template, request
from flask_cors import CORS

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)

# Multicast settings
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000
SERVER_IP = None
SERVER_PORT = None
SCRAPE_REQUEST = 9
FIND_RESPONSIBLE = 10


@app.route('/')
def home():
    return render_template('frontend.html')


def generate_pow_challenge():
    challenge = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return challenge


def validate_pow(challenge, nonce, difficulty=4):
    hash_input = challenge + str(nonce)
    hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
    return hash_result.startswith('0' * difficulty)


@app.route('/get-pow-challenge')
def get_pow_challenge():
    challenge = generate_pow_challenge()
    return json.dumps({'challenge': challenge})


@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form['url']
    settings = request.form['scrapeOption']
    depth = int(request.form.get('depth'))  # Get the depth parameter
    challenge = request.form['challenge']
    nonce = request.form['nonce']

    if not validate_pow(challenge, nonce):
        return "Invalid PoW solution. Please try again."

    logging.info(f"Initiating scrape for URL: {url}. Settings: {settings}")

    response = send_scrape_request(url, settings, depth)
    if response == "ERROR_CONEX":
        return f"""
                Error al conectarse. Enviar request nuevamente.
                """
    return format_response(response, url, settings)


def send_scrape_request(url, settings, depth):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(10)  # Esperar 10 segundos por una respuesta
    sock.bind(("", MULTICAST_PORT))

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

    try:
        # Buscar la IP del servidor responsable
        client_socket.send(f"{FIND_RESPONSIBLE},{url}".encode())
        node_ip = client_socket.recv(1024).decode()
        client_socket.close()

        # Asegurar que el servidor está descubierto
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setblocking(True)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.connect((node_ip, 8001))  # Conectar al puerto 8001 del nodo
        client_socket.send(f"{SCRAPE_REQUEST},{url},{settings},{depth}".encode())

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
    except Exception as e:
        logging.error("Error conectandose. Enviar request nuevamente")
        client_socket.close()
        return "ERROR_CONEX"


def prettify_css(css_code):
    """
    Formats the CSS code to make it more readable.
    """
    # Remove the list brackets and quotes
    if isinstance(css_code, list):
        css_code = css_code[0]

    # Split the CSS code into individual rules
    css_rules = css_code.split('}')

    # Format each rule with proper indentation and line breaks
    formatted_css = []
    for rule in css_rules:
        if rule.strip():
            # Split the rule into selector and properties
            parts = rule.split('{')
            if len(parts) == 2:
                selector = parts[0].strip()
                properties = parts[1].strip()

                # Split properties into individual lines
                properties = properties.split(';')
                properties = [prop.strip() for prop in properties if prop.strip()]

                # Format the rule with indentation
                formatted_rule = f"{selector} {{\n"
                for prop in properties:
                    formatted_rule += f"    {prop};\n"
                formatted_rule += "}"
                formatted_css.append(formatted_rule)

    # Join the formatted rules with line breaks
    return "\n\n".join(formatted_css)


def prettify_js(js_code):
    """
    Formats the JavaScript code to make it more readable by splitting lines
    based on semicolons, curly braces, and applying proper indentation.
    """
    # Remove the list brackets and quotes if the code is in a list format
    if isinstance(js_code, list) and js_code:
        js_code = js_code[0]

    # Initialize variables
    formatted_js = []
    indent_level = 0
    buffer = ""  # Temporary buffer to hold the current line being processed

    # Iterate through each character in the JavaScript code
    for char in js_code:
        buffer += char

        # Handle semicolons (end of statement)
        if char == ';':
            formatted_js.append('    ' * indent_level + buffer.strip())
            buffer = ""  # Reset the buffer for the next line

        # Handle opening curly braces (start of a block)
        elif char == '{':
            if buffer.strip():  # If there's content before the '{', add it as a line
                formatted_js.append('    ' * indent_level + buffer.strip())
            formatted_js.append('    ' * indent_level + '{')
            indent_level += 1  # Increase indentation for the block
            buffer = ""  # Reset the buffer for the next line

        # Handle closing curly braces (end of a block)
        elif char == '}':
            if buffer.strip():  # If there's content before the '}', add it as a line
                formatted_js.append('    ' * indent_level + buffer.strip())
            indent_level -= 1  # Decrease indentation after the block
            formatted_js.append('    ' * indent_level + '}')
            buffer = ""  # Reset the buffer for the next line

    # Add any remaining content in the buffer
    if buffer.strip():
        formatted_js.append('    ' * indent_level + buffer.strip())

    # Join the formatted lines with line breaks
    return "\n".join(formatted_js)


def format_response(response_text, url, settings):
    try:
        # Parse the JSON response
        response_data = json.loads(response_text)
        

        content = response_data[url][settings]
        
        
        # if not content:
        #     content = "No es usted, somos nosotros"
        
        content_type = "HTML" if "html" == settings else (
            "CSS" if "css" == settings else "JavaScript")

        # Prettify CSS or JavaScript based on content type
        if content_type == "CSS":
            content = prettify_css(content)
        elif content_type == "JavaScript":
            content = prettify_js(content)

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
