import socket

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 5000))
    s.listen(1)
    print("Server says: Listening on 0.0.0.0:5000")

    try:
        while True:
            client_socket, client_address = s.accept()
            # client_thread = threading.Thread(target=x, args=(client_socket, client_address))
            # client_thread.start()
    except KeyboardInterrupt:
        print("[INFO] Apagando el servidor.")
    finally:
        s.close()

