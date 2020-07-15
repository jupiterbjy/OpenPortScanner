import threading
import socket
import pickle
from SharedData import modules

# setup
config = modules.prepare(__file__)
IP = modules.get_external_ip()

s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"[S][Info] Connect client to: {IP}:{config.INIT_PORT}")
s_sock.bind(('', config.INIT_PORT))
s_sock.listen(1)
conn, addr = s_sock.accept()  # block until client signal
print(f"[S][Info] Connected.")

# OPEN_PORTS = []
USED_PORTS = []
SHUT_PORTS = []
thread_pool = threading

for p in range(1, config.PORT_MAX):
    # I really don't like putting if-block here and ruin program speed.
    if p in config.EXCLUDE:
        print(f"[CS][Info] Skipping Port {p}.")
        continue

    print(f"[SS][Info] Opening Port {p}.")
    child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    child_sock.settimeout(config.TIMEOUT)
    try:
        child_sock.bind(('', p))
        child_sock.listen(1)
        child_sock.accept()
    except socket.timeout:
        print(f"[SS][Info] Port {p} Timeout.")
        SHUT_PORTS.append(p)
    except OSError:
        print(f"[SS][Warn] Port {p} in use.")
        USED_PORTS.append(p)
    else:
        print(f"[SS][Info] Port {p} is open.")
        # OPEN_PORTS.append(p)

    child_sock.close()

    conn.send(b'1')
    conn.recv(1024)


used_data = pickle.dumps(USED_PORTS)
conn.send(used_data)
conn.close()


# print(f"Open Ports  : {OPEN_PORTS}")
print("\n[Results]")
print(f"Used Ports  : {USED_PORTS}")
print(f"Closed Ports: {SHUT_PORTS}")
print(f"Excluded    : {config.EXCLUDE}")
print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")
