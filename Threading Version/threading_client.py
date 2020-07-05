import socket
import pickle
import threading
try:
    from SharedData import SharedModules
except ImportError:
    from sys import path
    path.insert(1, '..')
    from SharedData import SharedModules

# setup
config = SharedModules.prepare(__file__)
c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
read_b, write_b = SharedModules.to_byte(config.BYTE_SIZE, config.BYTE_ORDER)


# Wait for connection, or a proper IP:PORT input.
while True:
    host, port = input("Host IP:Port >> ").split(":")
    port = int(port)
    try:
        c_sock.connect((host, port))
    except TypeError:
        print(f"[C][Warn] Cannot connect to - {host}:{port}")
    else:
        print("[C][Info] Connected")
        # c_sock.send(b'1')
        break


def worker(id_: int):
    while True:
        # announce server that the worker is ready.
        print(f"[CS{id_:2}][Info] Worker {id_:2} signals READY.")
        c_sock.send(write_b(id_))

        data = c_sock.recv(1024)
        p = read_b(data)

        print(f"[CS{id_:2}][Info] Worker {id_} received {p}.")

        # Port connection Start
        if p > 65536:
            print(f"[CS{id_:2}][Warn] received wrong port.")
            break

        print(f"[CS{id_:2}][Info] Connecting Port {p}.")
        child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        child_sock.settimeout(config.TIMEOUT)

        try:
            child_sock.connect((host, p))

        except socket.timeout:
            print(f"[CS{id_:2}][Info] Port {p} Timeout.")
        else:
            print(f"[CS{id_:2}][Info] Port {p} is open.")

        child_sock.close()


def main():
    workers = [
        threading.Thread(target=worker, args=[i])
        for i in range(config.WORKERS)
    ]

    for w in workers:
        w.start()

    for w in workers:
        w.join()

    data = c_sock.recv(4096)
    USED_PORTS, SHUT_PORTS = pickle.loads(data)
    print(f"[C][Info] Received Port data from server.")

    # print(f"Open Ports  : {OPEN_PORTS}")
    print("\n[Results]")
    print(f"Used Ports  : {USED_PORTS}")
    print(f"Closed Ports: {SHUT_PORTS}")
    print(f"Excluded    : {config.EXCLUDE}")
    print(f"All other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
