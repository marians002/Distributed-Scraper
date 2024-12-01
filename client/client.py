import socket

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("10.0.11.2", 5000))
    print("Client says: Connected to server")
    while True:
        print("Waiting. Hit enter or type exit")
        input()
        if input() == "exit":
            break
    s.close()
    print("Client says: Connection closed")
