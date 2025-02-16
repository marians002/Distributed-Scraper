import socket
import struct
import ipaddress
from subprocess import check_output
from multiprocessing import Process

LOCAL_ADDRS = [x for x in check_output(['hostname', '-i']).decode().strip().split(' ')]
IP_RECVORIGDSTADDR = 20
RESERVED_ADDRS = ['127.0.0.1', '10.0.10.254', '10.0.11.254', '10.0.10.253', '10.0.11.253']
MIN_PORT = 10000
PROCESS_AMOUNT = 5

def proxy(port, read_buffer = 4196):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_address = ('', port)
    sock.bind(server_address)

    # kernel support for reaching destintation addr
    sock.setsockopt(socket.IPPROTO_IP, IP_RECVORIGDSTADDR, 1)
    sock.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)

    print(f"Listening on {server_address}")

    while True:
        data, ancdata, _, address = sock.recvmsg(read_buffer, socket.MSG_CMSG_CLOEXEC)

        client_net = address[0].split('.')[2]
        primary_net = LOCAL_ADDRS[1].split('.')[2]
        # Avoid addr loops and pck duplicates
        if address[0] in RESERVED_ADDRS or address[0] in LOCAL_ADDRS or client_net != primary_net:
            continue

        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.IPPROTO_IP and cmsg_type == IP_RECVORIGDSTADDR:
                family, port = struct.unpack('=HH', cmsg_data[0:4])
                port = socket.htons(port)

                if family != socket.AF_INET:
                    raise TypeError(f"Unsupported socket type '{family}'")

                ip = socket.inet_ntop(family, cmsg_data[4:8])
                print(f"Received data {data} from {address}, original destination: {(ip, port)}")
                ip_object = ipaddress.ip_address(ip)

                if ip_object.is_multicast:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                        s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
                        s.sendto(data, (ip, port))
                        print(f"Data sent to {(ip, port)}")

processes = []

for i in range(PROCESS_AMOUNT):
    p = Process(target=proxy, args=(MIN_PORT + i,))
    p.start()
    processes.append(p)

for p in processes:
    p.join()
