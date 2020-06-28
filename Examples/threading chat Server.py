import threading
import socket
from urllib import request

INITIAL_PORT = 80
ENCODING = 'utf-8'


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


def send(sock: socket.socket):
    while True:
        msg = input("send << ")
        sock.send(msg.encode(ENCODING))


def recv(sock: socket.socket):
    while True:
        msg = sock.recv(1024)
        print(f'\nrecv >> {msg.decode(ENCODING)}')


def server(port):

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((socket.gethostname(), port))
    except OSError:
        print(f"[S][FATAL] Port 80 already in use!")
        return False

    sock.listen(1)

    other_sock, (c_ip, c_port) = sock.accept()
    print(f"Connection From {c_ip}:{c_port}")

    sender = threading.Thread(target=send, args=(other_sock,))
    receiver = threading.Thread(target=recv, args=(other_sock,))

    sender.start()
    receiver.start()

    sender.join()
    receiver.join()


if __name__ == '__main__':
    port_ = int(input("Port: "))
    ip = get_external_ip()
    print(f"Connect Client to {ip}:{port_}")
    server(port_)
