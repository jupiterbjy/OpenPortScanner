import threading
import socket
import pickle
from itertools import chain
from queue import Queue
try:
    from SharedData import SharedModules
except ImportError:
    from sys import path
    path.insert(1, '..')
    from SharedData import SharedModules

# TODO: move global variables to locals.


# setup
config = SharedModules.prepare(__file__)
IP = SharedModules.get_external_ip()
read_b, write_b = SharedModules.to_byte(config.BYTE_SIZE, config.BYTE_ORDER)


# Main connection start
s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"[S][Info] Connect client to: {IP}:{config.INIT_PORT}")
try:
    s_sock.bind(("", config.INIT_PORT))
except OSError:
    print(f"[S][CRIT] Cannot open server at port {config.INIT_PORT}, aborting.")
    exit()
else:
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


def worker(id_, q, send, recv, event: threading.Event):
    q: Queue
    send: Queue
    recv: Queue

    while not q.empty():

        # check eject event.
        if event.is_set():
            print(f"[SS{id_:2}][Warn] Worker {id_} stopping.")
            return

        # get next work.
        p: int = q.get()
        q.task_done()

        # check if port is in blacklist.
        if p in config.EXCLUDE:
            print(f"[SS{id_:2}][Info] Skipping Port {p}.")
            continue

        # receive worker announcement.
        worker_id = recv.get()
        recv.task_done()

        print(f"[SS{id_:2}][Info] Worker {worker_id} announce READY.")
        print(f"[SS{id_:2}][Info] Sending port {p} to Client.")

        send.put(p)

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

    # Send end signal to client.
    # first worker catching this signal will go offline.
    end: str = config.END_MARK
    conn.send(end.encode(config.ENCODING))


def send_thread(q: Queue, e: threading.Event):
    while not e.is_set():
        if q.empty():
            continue

        n = q.get()
        q.task_done()
        conn.send(write_b(n))


def recv_thread(q: Queue, e: threading.Event):
    while not e.is_set():
        q.put(read_b(conn.recv(1024)))


def main():
    # just wrapping in function makes global to local variable, runs faster.

    event = threading.Event()
    work = generate_queue()

    send_q = Queue()
    recv_q = Queue()

    server_thread = [
        threading.Thread(target=send_thread, args=[send_q, event]),
        threading.Thread(target=recv_thread, args=[recv_q, event])
    ]

    workers = [
        threading.Thread(target=worker, args=[i, work, send_q, recv_q, event])
        for i in range(config.WORKERS)
    ]

    for w in chain(server_thread, workers):  # just wanted to try out chain.
        w.start()

    try:
        for w in workers:
            w.join()

    except KeyboardInterrupt:
        event.set()
        for w in chain(workers, server_thread):
            w.join()
        print("[S][Warn] All workers stopped.")

    else:
        used_data = pickle.dumps([USED_PORTS, SHUT_PORTS])

        # blocking is ok as thread is completed.
        conn.send(used_data)
        conn.close()

        print("\n[Results]")
        print(f"Used Ports  : {USED_PORTS}")
        print(f"Closed Ports: {SHUT_PORTS}")
        print(f"Excluded    : {config.EXCLUDE}")
        print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
