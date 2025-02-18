import threading
import time
import socket
import struct
from DB_manager import *
from chordReference import *
from html_fetcher import scrape as my_scrape
from flask import Flask, request, jsonify


# class ChordNode:

    # def __init__(self, ip: str, peerId=None, port: int = 8001, m: int = 160):
    #     self.id = getShaRepr(ip)
    #     self.ip = ip
    #     self.port = port
    #     self.ref = ChordNodeReference(self.ip, self.port)
    #     self.pred = self.ref  # Initial predecessor is itself
    #     self.m = m  # Number of bits in the hash/key space
    #     self.finger = [self.ref] * self.m  # Finger table
    #     self.lock = threading.Lock()
    #     self.succ2 = self.ref
    #     self.succ3 = self.ref
    #     self.data = {}

    #     threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
    #     threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread

    #     # If peerId is not None:
    #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar la dirección
    #     sock.bind(('', BROADCAST_PORT))

    #     print(f"Servidor escuchando en el puerto {BROADCAST_PORT}...")

    #     discovery_thread = threading.Thread(target=self.handle_discovery, args=(sock,))
    #     discovery_thread.daemon = True  # El hilo se cierra cuando el programa principal termina
    #     discovery_thread.start()
    #     self.new_ip = self.discover_server()
    #     print("discovery_ip: ", self.new_ip)
    #     if self.new_ip is not None:
    #         threading.Thread(target=self.join, args=(ChordNodeReference(self.new_ip, self.port),), daemon=True).start()
    #     self.start_server()



# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Multicast settings
MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000

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
        self.data = {}
        
        init_db()

        threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
        threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread

        # If peerId is not None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar la dirección
        sock.bind(('', BROADCAST_PORT))

        logging.info(f"Servidor escuchando en el puerto {BROADCAST_PORT}...")

        discovery_thread = threading.Thread(target=self.handle_discovery, args=(sock,), daemon=True)
        discovery_thread.start()
        
        self.multicast_server_address()        
        
        self.new_ip = self.discover_server()        
                
        if self.new_ip is not None:
            threading.Thread(target=self.join, args=(ChordNodeReference(self.new_ip, self.port),), daemon=True).start()
        
        self.start_flask_server()
        
    @property
    def succ(self):
        return self.finger[0]

    @succ.setter
    def succ(self, node: 'ChordNodeReference'):
        with self.lock:
            self.finger[0] = node

    def start_flask_server(self):
        @app.route('/scrape', methods=['POST'])
        def scrape_endpoint():
            data = request.json
            urls = data.get('url', [])
            settings = data.get('settings', {})
            logging.info(f"Received scrape request for URLs: {urls} with settings: {settings}")
            results = my_scrape(urls, settings)
            logging.info(f"Scrape completed for URLs: {urls}")
            return jsonify(results)

        app.run(host='0.0.0.0', port=self.port)

    def multicast_server_address(self):
        sock_m = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_m.bind(('', MULTICAST_PORT))

        # Unirse al grupo multicast
        group = socket.inet_aton(MULTICAST_GROUP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock_m.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        logging.info(f"Escuchando en {MULTICAST_GROUP}:{MULTICAST_PORT}...")
        
        multicast_thread = threading.Thread(target=self.handle_multicast_discover, args=(sock_m,), daemon=True)
        multicast_thread.start()

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
        print("before find succ")
        self.succ = node.find_successor(self.id)
        self.succ2 = self.succ.succ
        self.succ3 = self.succ2.succ
        print(self.succ)
        print("self.succ: ", self.succ, "self.succ2: ", self.succ2)

    def stabilize(self):
        time.sleep(5)
        """Regular check for correct Chord structure."""
        while True:
            try:
                if self.succ:
                    x = self.succ.pred

                    if x.id != self.id:
                        if self.succ.id == self.id or self._inrange(x.id, self.id, self.succ.id):
                            self.succ = x
                    self.succ2 = self.succ.succ
                    self.succ.notify(self.ref)
            except Exception as e:
                try:
                    x = self.succ2
                    self.succ = x
                    self.succ2 = self.succ.succ
                    self.succ.notify1(ChordNodeReference(self.ip, self.port))
                except:
                    try:
                        x = self.succ3
                        self.succ = x
                        self.succ2 = self.succ.succ
                        self.succ3.notify1(self.ref)
                    except:
                        print(f"Error in stabilize: {e}")
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
        print(f"en notify, yo: {self.ip} el entrante: {node.ip}")
        if node.id == self.id:
            return
        print(f"notify with node {node} self {self.ref} pred {self.pred}")
        if (self.pred.id == self.id) or self._inrange(node.id, self.pred.id, self.id):
            self.pred = node

    def notify1(self, node: 'ChordNodeReference'):
        self.pred = node
        print(f"new notify por node {node} pred {self.pred}")

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
                print(f"Recibido mensaje de broadcast: {message} de {addr}")
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
        # while True:
        #     try:
        #         data, addr = sock.recvfrom(1024)
        #         message = data.decode('utf-8')
        #         logging.info(f"Recibido mensaje de broadcast: {message} de {addr}")
        #         if message == "DISCOVER_REQUEST":
        #             response = f"SERVER_IP:{SERVER_IP}"
        #             sock.sendto(response.encode('utf-8'), addr)
        #     except Exception as e:
        #         logging.critical(f"Error en el hilo de descubrimiento: {e}")
        #         break

    def discover_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  #Permite broadcast

        sock.settimeout(10)  # Tiempo máximo para esperar una respuesta

        message = "DISCOVER_REQUEST"
        try:
            sock.sendto(message.encode('utf-8'), (BROADCAST_ADDRESS, BROADCAST_PORT))
            logging.info("Enviando solicitud de descubrimiento por broadcast...")
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    response = data.decode('utf-8')
                    logging.info(f"Recibido respuesta de {addr}: {response}")

                    if response.startswith("SERVER_IP:"):
                        server_ip = response.split(":")[1]
                        if server_ip == self.ip:
                            continue
                        logging.info(f"Servidor encontrado en la IP: {server_ip}")
                        return server_ip  # Devuelve la IP del primer servidor encontrado

                except socket.timeout:
                    logging.critical("No se encontraron servidores en el tiempo especificado.")
                    return None  # No se encontró ningún servidor

        except Exception as e:
            logging.critical(f"Error durante el descubrimiento: {e}")
            return None
        finally:
            sock.close()

    def handle_multicast_discover(self,sock):
        try:
            while True:
                data, _ = sock.recvfrom(1024)
                if data == b"DISCOVER_NODE":
                    logging.info("RECIBIDO MENSAJE DE MULTICAST")
                    # Responder con la dirección IP del nodo
                    node_ip = socket.gethostbyname(socket.gethostname())
                    sock.sendto(node_ip.encode(), (MULTICAST_GROUP,MULTICAST_PORT))
                    logging.info(f"Respondí a {MULTICAST_GROUP} con mi IP: {node_ip}")
        except Exception as e:
            logging.critical(f"ERROR EN EL hilo de multicast: {e}")
    

    def store_key(self, key, value):
        key_hash = getShaRepr(key)
        print("key: ", key, "hash: ", key_hash)
        if self._inrange(key_hash, self.id, self.succ.id):
            self.data[key] = value
        else:
            node = self.closest_preceding_finger(key_hash)
            print("node_succ_key: ", node.id)
            node.store_key(key, value)

    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, _ = s.accept()
                threading.Thread(target=self.serve_client, args=(conn,), daemon=True).start()

    def serve_client(self, conn: socket.socket):
        data = conn.recv(1024).decode().split(',')

        data_resp = None
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
        elif option == NOTIFY:
            id = int(data[1])
            ip = data[2]
            self.notify(ChordNodeReference(ip, self.port))
        elif option == CLOSEST_PRECEDING_FINGER:
            id = int(data[1])
            data_resp = self.closest_preceding_finger(id)
        elif option == NOTIFY1:
            id = int(data[1])
            ip = data[2]
            self.notify1(ChordNodeReference(ip, self.port))
        elif option == IS_ALIVE:
            data_resp = 'alive'
        elif option == STORE_KEY:
            print(data)
            key, value = data[1], data[2]
            self.store_key(key, value)
            print(self.data)
            conn.sendall(self.data)
        if data_resp == 'alive':
            response = data_resp.encode()
            conn.sendall(response)
        elif data_resp:
            response = f'{data_resp.id},{data_resp.ip}'.encode()
            conn.sendall(response)
        conn.close()



if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    node = ChordNode(ip)
