import threading
import socket
import pickle
from queue import Queue
try:
    from SharedData import SharedModules
except ImportError:
    from sys import path
    path.insert(1, '..')
    from SharedData import SharedModules


# setup
config = SharedModules.prepare(__file__)
IP = SharedModules.get_external_ip()
read_b, write_b = SharedModules.to_byte(config.BYTE_SIZE, config.BYTE_ORDER)


# Main connection start
s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"[S][Info] Connect client to: {IP}:{config.INIT_PORT}")
s_sock.bind(("", config.INIT_PORT))
s_sock.listen(1)
conn, addr = s_sock.accept()  # block until client signal
print(f"[S][Info] Connected.")


# Results
USED_PORTS = []
SHUT_PORTS = []


def generate_queue():
    print(f"Generating Queue from 1~{config.PORT_MAX}.")
    q = Queue()
    for i in range(1, config.PORT_MAX):
        q.put(i)

    return q


def worker(id_, q: Queue):
    while not q.empty():
        p: int = q.get()

        if p in config.EXCLUDE:
            print(f"[SS{id_:2}][Info] Skipping Port {p}.")
            continue

        # receive worker announcement.
        worker_id = read_b(conn.recv(1024))
        print(f"[SS{id_:2}][Info] Worker {worker_id} announce READY.")
        print(f"[SS{id_:2}][Info] Sending port {p} to Client.")
        conn.send(write_b(p))

        print(f"[SS{id_:2}][Info] Opening Port {p}.")
        child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        child_sock.settimeout(config.TIMEOUT)

        try:
            child_sock.bind(("", p))
            child_sock.listen(1)
            child_sock.accept()

        except socket.timeout:
            print(f"[SS{id_:2}][Info] Port {p} Timeout.")
            SHUT_PORTS.append(p)

        except OSError:
            print(f"[SS{id_:2}][Warn] Port {p} in use.")
            USED_PORTS.append(p)

        else:
            print(f"[SS{id_:2}][Info] Port {p} is open.")

        child_sock.close()
        q.task_done()

    # Send end signal to client.
    # first worker catching this signal will go offline.
    end: str = config.END_MARK
    conn.send(end.encode(config.ENCODING))


def main():
    # just wrapping in function makes global to local variable, runs faster.

    work = generate_queue()
    workers = [
        threading.Thread(target=worker, args=[i, work]) for i in range(config.WORKERS)
    ]

    for w in workers:
        w.start()

    for w in workers:
        w.join()

    used_data = pickle.dumps([USED_PORTS, SHUT_PORTS])
    conn.send(used_data)
    conn.close()

    print("\n[Results]")
    print(f"Used Ports  : {USED_PORTS}")
    print(f"Closed Ports: {SHUT_PORTS}")
    print(f"Excluded    : {config.EXCLUDE}")
    print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
