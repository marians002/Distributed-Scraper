import threading
import time
import socket
import struct
import json
from chordReference import *
from copy import deepcopy
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEPTH = 1

class ChordNode:
    def __init__(self, ip: str, peerId=None, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.ip, self.port)
        self.pred = self.ref  # Initial predecessor is itself
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.lock = threading.Lock()
        self.succ2 = self.ref
        self.succ3 = self.ref
        self.data = dict()
        self.replics1 = dict()
        self.replics2 = dict()

        threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
        threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread

        #if peerId is not None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar la dirección
        sock.bind(('', BROADCAST_PORT))

        logging.info(f"Servidor escuchando en el puerto {BROADCAST_PORT}...")

        discovery_thread = threading.Thread(target=self.handle_discovery, args=(sock,), daemon=True)
        discovery_thread.start()

        
        # Crear socket multicast
        sock_m = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_m.bind(('', MULTICAST_PORT))

        # Unirse al grupo multicast
        group = socket.inet_aton(MULTICAST_GROUP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock_m.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        logging.info(f"Escuchando en {MULTICAST_GROUP}:{MULTICAST_PORT}...")
        multicast_thread = threading.Thread(target=self.handle_multicast_discover, args=(sock_m,), daemon=True)
        multicast_thread.start()

        self.new_ip = self.discover_server()
        print("discovery_ip: ", self.new_ip)
        if self.new_ip is not None:
            threading.Thread(target=self.join, args=(ChordNodeReference(self.new_ip, self.port),), daemon=True).start()
        self.start_server()

    @property
    def succ(self):
        return self.finger[0]

    @succ.setter
    def succ(self, node: 'ChordNodeReference'):
        with self.lock:
            self.finger[0] = node

    def _inbetween(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval [start, end)."""
        k = k % 2 ** self.m
        start = start % 2 ** self.m
        end = end % 2 ** self.m
        if start < end:
            return start <= k < end
        return start <= k or k < end

    def _inrange(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end)."""
        _start = (start + 1) % 2 ** self.m
        return self._inbetween(k, _start, end)

    def _inbetweencomp(self, k: int, start: int, end: int) -> bool:
        """Check if k is in the interval (start, end]."""
        _end = (end - 1) % 2 ** self.m
        return self._inbetween(k, start, _end)

    def find_succ(self, id: int) -> 'ChordNodeReference':
        node = self.find_pred(id)
        return node.succ

    def find_pred(self, id: int) -> 'ChordNodeReference':
        node = self
        try:
            if node.id == self.succ.id:
                return node
        except:
            print("ERROR IN FIND_PRED")
        while not self._inbetweencomp(id, node.id, node.succ.id):
            node = node.closest_preceding_finger(id)
            if node.id == self.id:
                break
        return node

    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        node = None
        for i in range(self.m - 1, -1, -1):
            try:
                if node == self.finger[i]:
                    continue
                self.finger[i].succ
                if self._inrange(self.finger[i].id, self.id, id):
                    return self.finger[i] if self.finger[i].id != self.id else self
            except:
                node = self.finger[i]
                continue
        return self

    def join(self, node: 'ChordNodeReference'):
        time.sleep(5)
        """Join a Chord network using 'node' as an entry point."""
        self.pred = self.ref
        print("before find succc")
        self.succ = node.find_successor(self.id)
        self.succ2 = self.succ.succ
        self.succ3 = self.succ2.succ
        print(self.succ)
        # print("self.succ: ", self.succ, "self.succ2: ", self.succ2)

    def stabilize(self):
        """Regular check for correct Chord structure."""
        time.sleep(5)
        while True:
            try:
                # checkea si hay un nuevo nodo x entre self y succ
                # resumen: nuevo nodo en el anillo como sucesor
                if self.succ:
                    x = self.succ.pred
                    change :bool = False

                    if x.id != self.id:
                        if self.succ.id == self.id or self._inrange(x.id, self.id, self.succ.id):
                            self.succ = x
                            change = True
                            # luego de hacer notify, mandar a x a hacerse cargo de las llaves entre x y self
                            # darle a x las réplicas de las cuales tiene que hacerse cargo
                            # Replicar llaves de x
                    self.succ2 = self.succ.succ
                    self.succ.notify(self.ref)
                    if change:
                        time.sleep(1)
                        self.send_msg(node_ip=self.succ.ip, op=NEW_NODE)
            except Exception as e:
                try:
                    # Sucesor 2 es ahora mi sucesor y le aviso que soy su predecesor
                    # resumen: perdí a mi sucesor
                    x = self.succ2
                    self.succ = x
                    self.succ2 = self.succ.succ
                    self.succ.notify1(ChordNodeReference(self.ip, self.port))
                    if self.succ.ip == self.ip:
                        time.sleep(1)
                        self.one_down()
                    else:
                        time.sleep(1) 
                        self.send_msg(node_ip=self.succ.ip, op=ONE_DOWN)
                except:
                    try:
                        # resumen: perdí dos nodos consecutivos en el anillo
                        x = self.succ3
                        self.succ = x
                        self.succ2 = self.succ.succ
                        self.succ3.notify1(self.ref)
                        
                        if self.succ.ip == self.ip:
                            time.sleep(1)
                            self.two_down()
                        else:
                            time.sleep(1)
                            self.send_msg(node_ip=self.succ.ip, op=TWO_DOWN)
                        
                    except Exception as h:
                        print(f"Error in stabilize: {h}")
            try:
                self.succ3 = self.succ.succ.succ
            except:
                try:
                    self.succ3 = self.succ3.succ
                except:
                    time.sleep(1)
                    continue
            print(f"successor : {self.succ}  succ2 {self.succ2} succ3 {self.succ3} predecessor {self.pred}")
            time.sleep(5)

    def notify(self, node: 'ChordNodeReference'):
        logging.info(f"en notify, yo: {self.ip} el entrante: {node.ip}")
        if node.id == self.id:
            return
        logging.info(f"notify with node {node.ip} self {self.ref.ip} pred {self.pred.ip}")
        if (self.pred.id == self.id) or self._inrange(node.id, self.pred.id, self.id):
            self.pred = node

    def notify1(self, node: 'ChordNodeReference'):
        self.pred = node
        logging.info(f"new notify1 por node {node} pred {self.pred}")
    
    # doing from node successor of the fallen down
    def one_down(self):
        logging.info(f'AJUSTANDO DATA Y REPLICAS CON one_down()')
        self.manage_info(1)     # data += replics1
        self.manage_info(3)     # replics1 = replics2
        self.succ._send_data(op=MANAGE_INFO, data=f'4,')     # succ.replics1 += succ.replics2
        self.replics2 = self.ask_4_info(self.pred.ip, option=2)     # replics2 = pred.replics1
        self.send_info(node_ip=self.succ.ip, to_send=2, to_store=3)     # succ.replics2 = replics1
        self.send_info(node_ip=self.succ2.ip, to_send=1, to_store=3)    # succ2.replics2 = data
        logging.info(f'Terminó el método: one_down()')
            
    # doing from node successor of the two fallen down
    def two_down(self):
        logging.info(f'AJUSTANDO DATA Y REPLICAS CON two_down()')
        self.send_msg(node_ip=self.succ.ip, op=MANAGE_INFO, data=f'5,')  # succ.replic1 += succ.replics2 + replics2
        self.manage_info(2)     # data += replics1 + replics2
        self.manage_info(node_ip=self.pred.ip, option=6)    # replics1 = pred.data
        self.manage_info(node_ip=self.pred.ip, option=8)    # replics2 = pred.replics1
        self.send_info(node_ip=self.succ.ip, to_send=2, to_store=3)     # succ.replcis2 = replics1(now)
        self.send_info(node_ip=self.succ2.ip, to_send=1, to_store=3)    # succ2.replics2 = data (now)
        logging.info(f'Terminó el método: two_down()')
        
    # doing from the new node
    def new_node(self):
        logging.info(f'AJUSTANDO DATA Y REPLICAS CON new_node()')
        self.manage_info(node_ip=self.pred.ip, option=6)    # replics1 <- pred.data
        self.manage_info(node_ip=self.pred.ip, option=8)    # replics2 <- pred.replics1
        self.send_msg(node_ip=self.succ.ip, op=MANAGE_INFO, data=f'10,')     # suc.replics2 <- succ.replics1
        self.manage_info(node_ip=self.succ.ip, option=9)    # data <- pred_keys, succ.datta <- my_keys
        self.send_info(node_ip=self.succ2.ip, to_send=1, to_store=3)    # succ2.replics2 <- data
        logging.info(f'Terminó el método: new_node()')
    
    def split_data(self):
        my_data, pred_data = dict(), dict()
        
        for key, value in self.data.items():
            key_hash = getShaRepr(key)
            if self._inbetweencomp(key_hash, self.pred.id, self.succ.id):
                my_data[key] = value
            else: pred_data[key] = value
        
        self.data.update(deepcopy(my_data))
        return my_data, pred_data

    def manage_info(self, option, node_ip=None):
        match int(option):
            case 1:
                # deepcopy para evitar compartir referencias :)
                self.data.update(deepcopy(self.replics1))
            case 2:
                self.data.update(deepcopy(self.replics1))
                self.data.update(deepcopy(self.replics2))
            case 3:
                self.replics1 = deepcopy(self.replics2)
            case 4:
                self.replics1.update(deepcopy(self.replics2))
            case 5:
                self.replics1.update(deepcopy(self.replics2))
                pred_replics2 = self.ask_4_info(node_ip=self.pred.ip, option=3)
                self.replics1.update(deepcopy(pred_replics2))
            case 6:
                self.replics1 = deepcopy(self.ask_4_info(node_ip=node_ip, option=1))
            case 7:
                self.replics2 = deepcopy(self.ask_4_info(node_ip=node_ip, option=1))
            case 8:
                self.replics2 = deepcopy(self.ask_4_info(node_ip=node_ip, option=2))
            case 9:
                self.data = deepcopy(self.ask_4_info(node_ip=self.succ.ip, option=4))
            case 10:
                self.replics2 = deepcopy(self.replics1)
            case _:
                logging.critical(f'OPCION INVÁLIDA en update info: {option}')
            
    def fix_fingers(self):
        time.sleep(5)
        while True:
            for i in range(self.m - 1, -1, -1):
                self.next = i
                with self.lock:
                    self.finger[self.next] = self.find_succ((self.id + 2 ** self.next) % (2 ** self.m))
            time.sleep(10)

    def handle_discovery(self, sock):
        while True:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode('utf-8')
                logging.info(f"Recibido mensaje de broadcast: {message} de {addr}")
                # Crear un hilo para manejar el mensaje
                threading.Thread(
                    target=self.handle_broadcast_message,
                    args=(sock, message, addr),
                    daemon=True
                ).start()

            except Exception as e:
                print(f"Error en el hilo de descubrimiento: {e}")
                break

    def handle_broadcast_message(self, sock, message, addr):
        try:
            if message == "DISCOVER_REQUEST":
                response = f"SERVER_IP:{SERVER_IP}"
                sock.sendto(response.encode('utf-8'), addr)
        except Exception as e:
            logging.critical(f"Error al manejar mensaje de broadcast: {e}")

    def handle_multicast_discover(self, sock):
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                if data == b"DISCOVER_NODE":
                    logging.info("RECIBIDO MENSAJE DE MULTICAST")
                    # Responder con la dirección IP del nodo
                    node_ip = socket.gethostbyname(socket.gethostname())
                    sock.sendto(node_ip.encode(), (MULTICAST_GROUP, MULTICAST_PORT))
                    logging.info(f"Respondí a {MULTICAST_GROUP} con mi IP: {node_ip}")
        except Exception as e:
            print(f"ERROR EN EL hilo de multicast: {e}")

    def discover_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  #Permite broadcast

        sock.settimeout(5)  # Tiempo máximo para esperar una respuesta

        message = "DISCOVER_REQUEST"
        try:
            sock.sendto(message.encode('utf-8'), (BROADCAST_ADDRESS, BROADCAST_PORT))
            print("Enviando solicitud de descubrimiento por broadcast...")
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode('utf-8')
                    print(f"Recibido respuesta de {addr}: {response}")

                    if response.startswith("SERVER_IP:"):
                        server_ip = response.split(":")[1]
                        if server_ip == self.ip:
                            continue
                        print("server_ip: ", server_ip, "self.ip: ", self.ip)
                        print(f"Servidor encontrado en la IP: {server_ip}")
                        return server_ip  # Devuelve la IP del primer servidor encontrado

                except socket.timeout:
                    print("No se encontraron servidores en el tiempo especificado.")
                    return None  # No se encontró ningún servidor

        except Exception as e:
            print(f"Error durante el descubrimiento: {e}")
            return None
        finally:
            sock.close()

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setblocking(True)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.serve_client, args=(conn,), daemon=True).start()

    def find_responsible(self, data, conn: socket.socket):
        url = data[1]
        logging.info(f"Resolve server_ip for URL: {url}")

        # Calcular hash de la URL
        url_hash = getShaRepr(url)

        # Encontrar nodo responsable
        responsible_node = self.find_succ(url_hash)
        conn.sendall(responsible_node.ip.encode())
    
    def scrape_resolve(self, data, conn: socket.socket):
        url = data[1]
        settings = data[2]
        logging.info(f"Received scrape request for URL: {url} with settings: {settings}")

        # Calcular hash de la URL
        url_hash = getShaRepr(url)

        # Encontrar nodo responsable
        responsible_node = self.find_succ(url_hash)

        if responsible_node.id == self.id:
            # Este nodo es responsable
            logging.info(f"Scrape request for {url} confirmed")
            json_str = self.scrape(url, settings)
            json_bytes = json_str.encode("utf-8")
            conn.sendall(struct.pack("!I", len(json_bytes)))  # Encabezado
            conn.sendall(json_bytes) 
        else:
            pass
    
    def save_replicas(self, result:dict):
        logging.info(f'GUARDANDO LLAVE EN SUCESORES')
        self.send_info(node_ip=self.succ.ip, to_send=4, to_store=4, info=result)
        self.send_info(node_ip=self.succ2.ip, to_send=4, to_store=5, info=result)
            
    def ask_4_info(self, node_ip, option: int) -> dict:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setblocking(True)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((node_ip, 8001))  # Conectar al puerto 8001 del nodo
                s.sendall(f"{SEND_INFO},{option}".encode('utf-8'))

                # Recibir el tamaño de los datos
                header = s.recv(4)
                size = struct.unpack("!I", header)[0]

                # Recibir los datos en bloques
                received = bytearray()
                while len(received) < size:
                    chunk = s.recv(1024000)
                    if not chunk:
                        break
                    received.extend(chunk)

                return json.loads(received.decode("utf-8"))
        except Exception as e:
            print(f"Error asking for data: {e}")
            return {}
    
    def send_msg(self, node_ip, op: int, data: str = None):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setblocking(True)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((node_ip, 8001))  # Conectar al puerto 8001 del nodo
                s.sendall(f"{op},{data}".encode('utf-8'))
                msg = s.recv(1024)
                return msg
        except:
            logging.critical(f'ERROR en: send_msg()')
            return b''
        
    def send_info(self , node_ip, to_send: int, to_store: int, info = None):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setblocking(True)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.connect((node_ip, 8001))  # Conectar al puerto 8001 del nodo
                s.sendall(f"{RECEIVE_INFO},{to_store}".encode('utf-8'))

                msg = s.recv(1024).decode()
                if msg == "READY":
                    logging.info(f'ME DIJERON READY')
                    match to_send:
                        case 1:
                            info = self.data
                        case 2:
                            info = self.replics1
                        case 3:
                            info = self.replics2
                        case 4:
                            pass
                        case _:
                            logging.critical(f'ERROR en SEND INFO, opción no válida')
                
                data_json = json.dumps(info).encode("utf-8")
                # tamaño de los datos
                s.sendall(struct.pack("!I", len(data_json)))
                # datos
                s.sendall(data_json)
        except Exception as e:
            print(f"Error asking for data: {e}")
            
    def serve_client(self, conn: socket.socket):

        data = conn.recv(1024).decode().split(',')
        data_resp = None
        if int(data[0]) not in [3, 4]:
            logging.info(f"Operation: {data[0]}")
        option = int(data[0])

        if option == FIND_SUCCESSOR:
            id = int(data[1])
            data_resp = self.find_succ(id)

        elif option == FIND_PREDECESSOR:
            id = int(data[1])
            data_resp = self.find_pred(id)

        elif option == GET_SUCCESSOR:
            data_resp = self.succ

        elif option == GET_PREDECESSOR:
            data_resp = self.pred

        elif option == CLOSEST_PRECEDING_FINGER:
            id = int(data[1])
            data_resp = self.closest_preceding_finger(id)
            
        elif option == NOTIFY:
            id = int(data[1])
            ip = data[2]
            self.notify(ChordNodeReference(ip, self.port))

        elif option == NOTIFY1:
            id = int(data[1])
            ip = data[2]
            self.notify1(ChordNodeReference(ip, self.port))

        elif option == IS_ALIVE:
            data_resp = 'alive'
            
        elif option == SCRAPE_REQUEST:
            self.scrape_resolve(data, conn)

        elif option == FIND_RESPONSIBLE:
            self.find_responsible(data, conn)

        elif option == SEND_INFO:
            match int(data[1]):
                case 1:
                    info = self.data
                case 2:
                    info = self.replics1
                case 3:
                    info = self.replics2
                case 4:
                    _, info = self.split_data()
                case _:
                    logging.critical(f'ERROR en SEND INFO, opción no válida')
            
            data_json = json.dumps(info).encode("utf-8")
            # tamaño de los datos
            conn.sendall(struct.pack("!I", len(data_json)))
            # datos
            conn.sendall(data_json)
            
        elif option == RECEIVE_INFO:
            # Recibir el tamaño de los datos
            conn.sendall(f'READY'.encode())
            
            header = conn.recv(4)
            size = struct.unpack("!I", header)[0]

            received = bytearray()
            while len(received) < size:
                chunk = conn.recv(1024000)
                if not chunk:
                    break
                received.extend(chunk)

            info = json.loads(received.decode("utf-8"))
            
            match int(data[1]):
                case 1:
                    self.data = deepcopy(info)
                case 2:
                    self.replics1 = deepcopy(info)
                case 3:
                    self.replics2 = deepcopy(info)
                case 4:
                    self.replics1.update(deepcopy(info))
                case 5:
                    self.replics2.update(deepcopy(info))
                case _:
                    logging.critical(f"ERROR in RECIEVE, wrong option: {option}")
        
        elif option == MANAGE_INFO:
            if len(data) >= 3:
                self.manage_info(option=data[1], node_ip=data[2])
            else: 
                self.manage_info(option=data[1])
                
        elif option == ONE_DOWN:
            self.one_down()
            
        elif option == TWO_DOWN:
            self.two_down()
            
        elif option == NEW_NODE:
            self.new_node()
        
        if data_resp == 'alive':
            response = data_resp.encode()
            conn.sendall(response)
            
        elif data_resp:
            response = f'{data_resp.id},{data_resp.ip}'.encode()
            conn.sendall(response)
        conn.close()

    def scrape(self, urls, settings,  depth=DEPTH):
        results = {}
        urls = [urls] if isinstance(urls, str) else urls
        logging.info(f"Starting scrape for URLs: {urls} with settings: {settings} and depth: {depth}")

        for url in urls:
            # Initialize the result dictionary for the current URL
            results[url] = {}

            # Fetch data from the provided dictionary
            response = self.data.get(url, {})
            html_content = response.get('html')
            css_content = response.get('css', [])
            js_content = response.get('js', [])

            # Check if HTML is requested and available in the dictionary
            if settings == 'html':
                if html_content:
                    results[url]['html'] = html_content
                    logging.info(f"HTML content for {url} found in dictionary")
                else:
                    # Fetch HTML from the web if not in the dictionary
                    logging.info(f"Fetching HTML content for {url} from the web")
                    html_contents, _ = self.fetch_html([url], {'extract_html': True}, depth)
                    results[url]['html'] = html_contents.get(url)

            # Check if CSS is requested and available in the dictionary
            if settings == 'css':
                if css_content:
                    results[url]['css'] = css_content
                    logging.info(f"CSS content for {url} found in dictionary")
                else:
                    # Fetch CSS from the web if not in the dictionary
                    logging.info(f"Fetching CSS content for {url} from the web")
                    _, extra_info = self.fetch_html([url], {'extract_css': True}, depth)
                    results[url]['css'] = extra_info.get(url, {}).get('css', [])

            # Check if JavaScript is requested and available in the dictionary
            if settings == 'js':
                if js_content:
                    results[url]['js'] = js_content
                    logging.info(f"JavaScript content for {url} found in dictionary")
                else:
                    # Fetch JavaScript from the web if not in the dictionary
                    logging.info(f"Fetching JavaScript content for {url} from the web")
                    _, extra_info = self.fetch_html([url], {'extract_js': True}, depth)
                    results[url]['js'] = extra_info.get(url, {}).get('js', [])

        logging.info(f"Scrape completed for URLs: {urls}")
        return json.dumps(results)

    def fetch_html(self, urls, settings, depth=DEPTH):
        html_contents = {}
        extra_info = {}
        logging.info(f"Fetching HTML for URLs: {urls} with settings: {settings} and depth: {depth}")

        for url in urls:
            try:
                logging.info(f"Fetching content from {url}")
                response = requests.get(url)
                response.raise_for_status()  # Check if the request was successful
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract HTML
                html_content = soup.prettify()
                # html_contents[url] = html_content if settings.get('extract_html', False) else None
                html_contents[url] = html_content
                
                # Extract CSS
                css_content = []
                
                # if settings.get('extract_css', False):
                # Inline CSS
                for style in soup.find_all('style'):
                    if style.string:
                        css_content.append(style.string)

                # External CSS
                for link in soup.find_all('link', rel='stylesheet'):
                    css_url = link.get('href')
                    if css_url:
                        # Handle relative URLs
                        if not css_url.startswith(('http://', 'https://')):
                            css_url = urljoin(url, css_url)
                        try:
                            logging.info(f"Fetching CSS from {css_url}")
                            css_response = requests.get(css_url)
                            css_response.raise_for_status()
                            css_content.append(css_response.text)
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching CSS {css_url}: {e}")

                # Extract JavaScript
                js_content = []
                # if settings.get('extract_js', False):
                # Inline JS
                for script in soup.find_all('script'):
                    if script.string:  # Check if the script tag contains JavaScript code
                        js_content.append(script.string)

                    # External JS
                    elif script.get('src'):
                        js_url = script.get('src')
                        if not js_url.startswith(('http://', 'https://')):
                            # Handle relative URLs
                            js_url = urljoin(url, js_url)
                        try:
                            logging.info(f"Fetching JavaScript from {js_url}")
                            js_response = requests.get(js_url)
                            js_response.raise_for_status()
                            js_content.append(js_response.text)
                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error fetching JavaScript {js_url}: {e}")

                # Store all extracted data in the dictionary
                self.data[url] = {
                    'html': html_content,
                    'css': css_content,
                    'js': js_content
                }
                
                result = dict()
                result[url] = {
                    'html': html_content,
                    'css': css_content,
                    'js': js_content
                }
                
                self.save_replicas(result)
                # Store all extracted data in extra_info
                extra_info[url] = {
                    'css': css_content,
                    'js': js_content,
                }

                # If depth is greater than 0, recursively fetch HTML from links found in the current page
                if depth > 0:
                    links = soup.find_all('a', href=True)
                    linked_urls = [urljoin(url, link['href']) for link in links]
                    linked_html_contents, linked_extra_info = self.fetch_html(linked_urls, settings, depth - 1)
                    html_contents.update(linked_html_contents)
                    extra_info.update(linked_extra_info)

            
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching {url}: {e}")
                html_contents[url] = None

        logging.info(f"HTML fetch completed for URLs: {urls}")
        return html_contents, extra_info


if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    node = ChordNode(ip)
