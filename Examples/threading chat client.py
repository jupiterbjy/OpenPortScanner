import threading
import socket
from urllib import request


INITIAL_PORT = 80
ENCODING = 'utf-8'


def send(sock: socket.socket):
    while True:
        msg = input("send << ")
        encode = msg.encode(ENCODING)
        sock.send(len(encode).to_bytes(32, 'big') + encode)


def recv(sock: socket.socket):
    while True:
        msg = sock.recv(1024)
        print(f'\nrecv >> {msg.decode(ENCODING)}')


def client(ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, port))
    print(f"Connected to Server")

    sender = threading.Thread(target=send, args=(sock,))
    receiver = threading.Thread(target=recv, args=(sock,))

    sender.start()
    receiver.start()

    sender.join()
    receiver.join()


if __name__ == '__main__':
    raw = input("Address: ")
    ip_, port_ = raw.split(':')
    client(ip_, int(port_))
