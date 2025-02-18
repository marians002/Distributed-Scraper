import hashlib
import socket
import logging

BROADCAST_PORT = 50000
SERVER_IP = socket.gethostbyname(socket.gethostname())
BROADCAST_ADDRESS = '<broadcast>'

MULTICAST_GROUP = '224.0.0.1'
MULTICAST_PORT = 10000

# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
CLOSEST_PRECEDING_FINGER = 6
IS_ALIVE = 7
NOTIFY1 = 8
STORE_KEY = 9
SCRAPE_REQUEST = 10
FIND_RESPONSIBLE = 11


def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)


class ChordNodeReference:
    def __init__(self, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    def _send_data(self, op: int, data: str = None) -> bytes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                s.sendall(f'{op},{data}'.encode('utf-8'))
                return s.recv(1024)
        except Exception as e:
            print(f"Error sending data: {e} operacion: {op} ")
            return b''

    def find_successor(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_SUCCESSOR, str(id)).decode().split(',')
        logging.info(f'Respuesta del sucesor: {response}')
        return ChordNodeReference(response[1], self.port)

    def find_predecessor(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_PREDECESSOR, str(id)).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    @property
    def succ(self) -> 'ChordNodeReference':
        response = self._send_data(GET_SUCCESSOR).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    @property
    def pred(self) -> 'ChordNodeReference':
        response = self._send_data(GET_PREDECESSOR).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    def notify(self, node: 'ChordNodeReference'):
        self._send_data(NOTIFY, f'{node.id},{node.ip}')

    def notify1(self, node: 'ChordNodeReference'):
        self._send_data(NOTIFY1, f'{node.id},{node.ip}')

    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(CLOSEST_PRECEDING_FINGER, str(id)).decode().split(',')
        return ChordNodeReference(response[1], self.port)

    def alive(self):
        response = self._send_data(IS_ALIVE).decode().split(',')
        return response

    def store_key(self, key: str, value: str):
        self._send_data(STORE_KEY, f'{key},{value}')

    def __str__(self) -> str:
        return f'{self.id},{self.ip},{self.port}'

    def __repr__(self) -> str:
        return self.__str__()
