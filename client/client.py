import socket

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("10.0.11.2", 5000))
    print("Client says: Connected to server")
    try:
        s.sendall(b'ping')
        print("Client says: Ping sent")
    except Exception as e:
        print(f"Client says: Error - {e}")
    finally:
        s.close()
