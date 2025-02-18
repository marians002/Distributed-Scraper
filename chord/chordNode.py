import threading
import time
import socket
import struct
from DB_manager import *
from chordReference import *
from html_fetcher import scrape as my_scrape
from flask import Flask, request, jsonify
import json


class ChordNode:
    def __init__(self, ip: str, peerId = None, port: int = 8001, m: int = 160):
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
        self.replics= []
        
        init_db()

        threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
        threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread

        #if peerId is not None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Permite reutilizar la dirección
        sock.bind(('', BROADCAST_PORT))

        logging.info(f"Servidor escuchando en el puerto {BROADCAST_PORT}...")

        discovery_thread = threading.Thread(target=self.handle_discovery, args=(sock,), daemon=True)
        discovery_thread.start()

        # region REPLICATION
        # replic_thread = threading.Thread(target=self.replicate)
        # replic_thread.daemon = True  # El hilo se cierra cuando el programa principal termina
        # replic_thread.start()


        # Crear socket multicast
        sock_m = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock_m.bind(('', MULTICAST_PORT))

        # Unirse al grupo multicast
        group = socket.inet_aton(MULTICAST_GROUP)
        mreq = struct.pack('4sL', group, socket.INADDR_ANY)
        sock_m.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        logging.info(f"Escuchando en {MULTICAST_GROUP}:{MULTICAST_PORT}...")
        multicast_thread = threading.Thread(target=self.handle_multicast_discover,args=(sock_m,), daemon=True)
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


    # def save_file(self, file_name, file_type, file_content,r):
    #     """Guarda un archivo en la base de datos."""
    #     with self.lock:
    #         file_hash = compute_hash(file_content)
    #         self.cursor.execute('SELECT id FROM files WHERE hash = ?', (file_hash,))
    #         file_record = self.cursor.fetchone()

    #         if file_record:
    #             file_id = file_record[0]
    #             self.cursor.execute('SELECT name FROM file_names WHERE file_id = ? AND name = ?', (file_id, file_name))
    #             name_record = self.cursor.fetchone()

    #             if not name_record:
    #                 self.cursor.execute('INSERT INTO file_names (file_id, name) VALUES (?, ?)', (file_id, file_name))
    #                 self.conn.commit()
    #                 if r == 0: 
    #                     print("PRIMERA VEZ, CREO PRIMERA REPLICA")
    #                     self.replics.append({'name':file_name,'type':file_type,'content':file_content,'nodes':[self.ip]})
    #                 return "Nombre agregado al archivo existente"
    #             return "El archivo ya existe con ese nombre"
    #         else:
    #             self.cursor.execute('INSERT INTO files (hash, content, type) VALUES (?, ?, ?)', (file_hash, file_content, file_type))
    #             file_id = self.cursor.lastrowid
    #             self.cursor.execute('INSERT INTO file_names (file_id, name) VALUES (?, ?)', (file_id, file_name))
    #             self.conn.commit()
    #             if r == 0: 
    #                 self.replics.append({'name':file_name,'type':file_type,'content':file_content,'nodes':[self.ip]})
    #                 print("PRIMERA VEZ, CREO PRIMERA REPLICA")
    #             return "Archivo subido correctamente"

    # def broadcast_search(self, file_name, file_type):
    #     """Realiza una búsqueda por broadcast en la red CHORD."""
    #     results = []
    #     print("CONFIGURANDO SOCKET")
    #     broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #     broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #     broadcast_socket.settimeout(3)  # Tiempo de espera para respuestas

    #     print("ENVIANDO MENSAJE")
    #     # Enviar mensaje de broadcast
    #     message = f"{SEARCH_FILE},{file_name},{file_type}"
    #     broadcast_socket.sendto(message.encode(), (BROADCAST_ADDRESS, BROADCAST_PORT))

    #     def handle_response(m):
    #         if m.startswith("SEARCH_RESULT~"):
    #                 print("TENGO RESPUESTA")
    #                 # Formato: SEARCH_RESULT:result1,result2,...
    #                 Elements=eval(m.split("~")[1])
    #                 with self.lock:
    #                     for e in Elements:
    #                         if e not in results: results.append(e)

    #     # Recibir respuestas de los nodos
    #     while True:
    #         try:
    #             data, addr = broadcast_socket.recvfrom(1024)
    #             response = data.decode()
    #             threading.Thread(
    #                 target=handle_response,
    #                 args=(response,),
    #                 daemon=True
    #             ).start()
    #         except socket.timeout:
    #             print("SE ACABO EL TIEMPO")
    #             break  # No hay más respuestas
    #     print("BUSQUEDA TERMINADA")
    #     broadcast_socket.close()
    #     print("DEVOLVIENDO RESULTADOS")
    #     print(results)
    #     return results


    # def search_file(self, file_name, file_type):
    #     """Busca un archivo en la base de datos."""
    #     query = '''SELECT fn.name, f.type, f.hash 
    #     FROM files f JOIN file_names fn ON 
    #     f.id = fn.file_id WHERE fn.name LIKE ?'''
    #     params = (f"%{file_name}%",)
    #     if file_type != "*":
    #         query += ' AND f.type = ?'
    #         params += (file_type,)
    #     self.cursor.execute(query, params)
    #     return [{"name": row[0], "type": row[1], "hash":row[2], "ip":self.ip} for row in self.cursor.fetchall()]

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

    def handle_multicast_discover(self,sock):
        try:
            while True:
                data, addr = sock.recvfrom(1024)
                if data == b"DISCOVER_NODE":
                    logging.info("RECIBIDO MENSAJE DE MULTICAST")
                    # Responder con la dirección IP del nodo
                    node_ip = socket.gethostbyname(socket.gethostname())
                    sock.sendto(node_ip.encode(), (MULTICAST_GROUP,MULTICAST_PORT))
                    logging.info(f"Respondí a {MULTICAST_GROUP} con mi IP: {node_ip}")
        except Exception as e:
            print(f"ERROR EN EL hilo de multicast: {e}")
    
    def discover_server(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #Permite broadcast

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
                        return server_ip # Devuelve la IP del primer servidor encontrado

                except socket.timeout:
                    print("No se encontraron servidores en el tiempo especificado.")
                    return None  # No se encontró ningún servidor

        except Exception as e:
            print(f"Error durante el descubrimiento: {e}")
            return None
        finally:
            sock.close()

    def replicate(self):
        time.sleep(5)
        while True:
            if self.replics:
                print("TENGO REPLICA, VOY A MANEJARLA")
                obj = self.replics.pop(0)
                if len(obj["nodes"])<3:
                    if self.ip not in obj["nodes"]:
                        print(f"REPLICANDO ARCHIVO EN NODO: {self.ip}")
                        self.save_file(obj['name'],obj['type'],obj['content'],1)
                        obj['nodes'].append(self.ip)
                    #pasarlo al sucesor
                    
                    message = self.succ.save_in_replics(obj)
                    if message == "error":
                        self.replics.append(obj)
                    time.sleep(5)
            else:
                time.sleep(5)

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
            s.setblocking(True)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.serve_client, args=(conn,), daemon=True).start() 

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
            json_str = my_scrape(url, settings)
            logging.info(f"RESULTADO DE MY_SCRAPE: {json_str}")
            json_bytes = json_str.encode("utf-8")
            conn.sendall(struct.pack("!I", len(json_bytes)))  # Encabezado
            conn.sendall(json_bytes)  # Datos
        else:
            pass
    
    def find_responsible(self, data, conn:socket.socket):
        url = data[1]
        logging.info(f"Resolve server_ip for URL: {url}")
        
        # Calcular hash de la URL
        url_hash = getShaRepr(url)
        
        # Encontrar nodo responsable
        responsible_node = self.find_succ(url_hash)
        conn.sendall(responsible_node.ip.encode())
        
    def serve_client(self, conn: socket.socket):
        
        data = conn.recv(1024).decode().split(',')
        data_resp = None
        if int(data[0]) not in [3,4]:
            logging.info(f"Operation: {data[0]}")
            # logging.info(f'Data content: ', data)
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
        elif option == SCRAPE_REQUEST :
            self.scrape_resolve(data, conn)
        elif option == FIND_RESPONSIBLE:
            self.find_responsible(data, conn)
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
