import hashlib
from distributed.config import M
import threading

# --- Node State Management ---
class ChordNode:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.id = self._calculate_id()
        self.predecessor = None
        self.successor = None
        self.finger = [None] * M
        self.lock = threading.RLock()
        
    def _calculate_id(self):
        ip_port = f"{self.ip}:{self.port}"
        return get_hash(ip_port)
    
    def to_dict(self):
        predecessor_dict = None
        if self.predecessor is not None:
            predecessor_dict = {
                "id": self.predecessor.get("id"),
                "ip": self.predecessor.get("ip"),
                "port": self.predecessor.get("port")
            }
        successor_dict = None
        if self.successor is not None:
            successor_dict = {
                "id": self.successor.get("id"),
                "ip": self.successor.get("ip"),
                "port": self.successor.get("port")
            }
        return {
            "ip": self.ip,
            "port": self.port,
            "id": self.id,
            "predecessor": predecessor_dict,
            "successor": successor_dict
        }

def get_hash(key):
    return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**M)

current_node = None