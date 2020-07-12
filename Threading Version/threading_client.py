import socket
import pickle
import threading
from itertools import chain
from queue import Queue
try:
    from SharedData import SharedModules
except ImportError:
    from sys import path
    path.insert(1, '..')
    from SharedData import SharedModules

# setup
config = SharedModules.prepare(__file__)
c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
read_b, write_b = SharedModules.rw_bytes(
    config.BYTE_SIZE, config.BYTE_ORDER, config.END_MARK, config.ENCODING)


# Wait for connection, or a proper IP:PORT input.
while True:
    # host, port = input("Host [IP:Port] >> ").split(":")
    host, port = '210.183.6.91:80'.split(":")
    port = int(port)
    try:
        c_sock.connect((host, port))
    except TypeError:
        print(f"[C][Warn] Cannot connect to - {host}:{port}")
    else:
        print("[C][Info] Connected")
        # c_sock.send(b'1')
        break


def worker(id_: int, send, recv, event: threading.Event):
    q: Queue
    send: Queue
    recv: Queue

    while not event.is_set():
        # announce server that the worker is ready.
        print(f"[CS{id_:2}][Info] Worker {id_:2} signals READY.")
        send.put(id_)

        data = recv.get()
        recv.task_done()

        p = data
        print(f"[CS{id_:2}][Info] Worker {id_} received {p}.")

        print(f"[CS{id_:2}][Info] Connecting Port {p}.")
        child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        child_sock.settimeout(config.TIMEOUT)

        try:
            child_sock.connect((host, p))
        except OverflowError:
            print(f"[CS{id_:2}][Info] Stop Signal received!")
            break

        except socket.timeout:
            print(f"[CS{id_:2}][Info] Port {p} timeout.")

        except OSError:
            print(f"[CS{id_:2}][Warn] Port {p} in use.")

        else:
            print(f"[CS{id_:2}][Info] Port {p} is open.")

        child_sock.close()


def send_thread(q: Queue, e: threading.Event):
    while not e.is_set():
        if q.empty():
            continue

        n = q.get()
        q.task_done()

        try:
            c_sock.send(write_b(n))
        except (ConnectionAbortedError, ConnectionResetError):
            break


def recv_thread(q: Queue, e: threading.Event):
    while not e.is_set():
        try:
            data = c_sock.recv(4096)
        except (ConnectionAbortedError, ConnectionResetError):
            break

        if data == config.END_MARK.encode(config.ENCODING):
            print(f"[C] Received {data.decode(config.ENCODING)}")
            break

        q.put(read_b(data))


def main():

    event = threading.Event()
    send_q = Queue()
    recv_q = Queue()

    server_thread = [
        threading.Thread(target=send_thread, args=[send_q, event]),
        threading.Thread(target=recv_thread, args=[recv_q, event])
    ]

    workers = [
        threading.Thread(target=worker, args=[i, send_q, recv_q, event])
        for i in range(config.WORKERS)
    ]

    # start threads
    for w in chain(server_thread, workers):
        w.start()

    # Check if any thread is still alive
    timer = threading.Event()

    try:
        while SharedModules.any_thread_alive(workers):
            timer.wait(timeout=0.1)

    except KeyboardInterrupt:
        event.set()
        for w in chain(workers):
            w.join()
        print("[C][Warn] All workers stopped.")

    else:
        event.set()
        for w in chain(workers):  # I need to stop server thread somehow..
            w.join()
        print("[C][info] All workers stopped.")

        # server_thread[1].join()

        # data = c_sock.recv(4096)
        # USED_PORTS, SHUT_PORTS = pickle.loads(data)
        # print(f"[C][Info] Received Port data from server.")
        #
        # print("\n[Results]")
        # print(f"Used Ports  : {USED_PORTS}")
        # print(f"Closed Ports: {SHUT_PORTS}")
        # print(f"Excluded    : {config.EXCLUDE}")
        # print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
