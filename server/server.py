import socket

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 5000))
    s.listen(1)
    print("Server says: Listening on 0.0.0.0:5000")

    try:
        while True:
            client_socket, client_address = s.accept()
            data = client_socket.recv(1024)
            if data == b'ping':
                print(f"Server says: Received ping from {client_address}")
            client_socket.close()
    except KeyboardInterrupt:
        print("[INFO] Shutting down the server.")
    finally:
        s.close()