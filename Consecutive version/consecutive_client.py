import socket
import pickle
from SharedData import SharedModules

# setup
config = SharedModules.prepare(__file__)

# TODO: send configuration to server?

c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

while True:
    host, port = input('Host IP:Port >> ').split(':')
    port = int(port)
    try:
        c_sock.connect((host, port))
    except TypeError:
        print(f"[C][Warn] Cannot connect to - {host}:{port}")
    else:
        print('[C][Info] Connected')
        c_sock.send(b'1')
        break


# OPEN_PORTS = []
SHUT_PORTS = []

for p in range(1, config.PORT_MAX):
    # I really don't like putting if-block here and ruin program speed.
    if p in config.EXCLUDE:
        print(f"[CS][Info] Skipping Port {p}.")
        continue

    print(f"[CS][Info] Opening Port {p}.")
    child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    child_sock.settimeout(config.TIMEOUT)
    try:
        child_sock.connect((host, p))
    except socket.timeout:
        print(f"[CS][Info] Port {p} Timeout.")
        SHUT_PORTS.append(p)
    else:
        print(f"[CS][Info] Port {p} is open.")
        # OPEN_PORTS.append(p)

    child_sock.close()

    c_sock.recv(1024)
    c_sock.send(b'1')

data = c_sock.recv(4096)
USED_PORTS = pickle.loads(data)
print(f"[C][Info] Received In-use Port data from server.")

# print(f"Open Ports  : {OPEN_PORTS}")
print("\n[Results]")
print(f"Used Ports  : {USED_PORTS}")
print(f"Closed Ports: {SHUT_PORTS}")
print(f"Excluded    : {config.EXCLUDE}")
print(f"All other ports from 1~{config.PORT_MAX} is open.")
