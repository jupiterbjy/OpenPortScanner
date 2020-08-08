import socket
import json
import threading
from itertools import chain
from queue import Queue, Empty

try:
    import SharedData
except ImportError:
    from sys import path

    path.insert(1, "../..")
    path.insert(2, "..")
    import SharedData


# setup
config = SharedData.load_config_new()
c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TIMEOUT_FACTOR = config.SOCK_TIMEOUT
read_b, write_b = SharedData.rw_bytes(
    config.BYTE_SIZE, config.BYTE_ORDER, config.END_MARK, config.ENCODING
)


# Wait for connection, or a proper IP:PORT input.
while True:
    host, port = input("Host [IP:Port] >> ").split(":")
    # host, port = ''.split(":")
    port = int(port)
    try:
        c_sock.connect((host, port))
    except TypeError:
        print(f"[C][Warn] Cannot connect to - {host}:{port}")
    else:
        print("[C][Info] Connected")
        c_sock.settimeout(TIMEOUT_FACTOR)
        # c_sock.send(b'1')
        break


def worker(id_: int, send, recv, event: threading.Event):
    q: Queue
    send: Queue
    recv: Queue

    while not event.is_set():
        # announce server that the worker is ready.
        print(f"[CS{id_:2}][Info] Worker {id_:2} READY.")
        send.put(id_)

        try:
            p = recv.get()
        except Empty:
            continue

        recv.task_done()
        print(f"[CS{id_:2}][Info] Worker {id_:2} received {p}.")

        if p > config.PORT_MAX:
            print(SharedData.cyan(f"[CS{id_:2}][Info] Stop Signal received!"))
            break

        print(f"[CS{id_:2}][Info] Connecting Port {p}.")
        child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        child_sock.settimeout(config.TIMEOUT)

        try:
            child_sock.connect((host, p))

        except socket.timeout:
            print(SharedData.red(f"[CS{id_:2}][Info] Port {p} Timeout."))

        except OSError:
            print(SharedData.red(f"[CS{id_:2}][Warn] Port {p} in use."))

        else:
            print(SharedData.green(f"[CS{id_:2}][Info] Port {p} is open."))

        child_sock.close()


def send_thread(q: Queue, e: threading.Event):
    while True:

        try:
            n = q.get(timeout=TIMEOUT_FACTOR)
        except Empty:
            if e.is_set():
                print(SharedData.green("[C][SEND] Event set!"))
                break
        else:
            q.task_done()

            try:
                c_sock.send(write_b(n))
            except (ConnectionAbortedError, ConnectionResetError):
                print(SharedData.red("[C][SEND] Connection reset!"))
                break
            except AttributeError:
                print(
                    SharedData.red(
                        f"[C][SEND] Tried to send <{type(n)}> type value {n}."
                    )
                )


def recv_thread(q: Queue, e: threading.Event):
    c_sock.settimeout(TIMEOUT_FACTOR)
    # making a vague assumption of timeout situation.

    while True:

        try:
            data = c_sock.recv(65536)
        except (ConnectionAbortedError, ConnectionResetError):
            break
        except socket.timeout:
            if e.is_set():
                print(SharedData.green(f"[C][RECV] Event set!"))
                break
        else:
            if data == config.END_MARK:
                print(SharedData.green(f"[C][RECV] Received eof <{data}>"))
                break

            q.put(read_b(data))


def recv_until_eof(sock: socket.socket, eof: bytes):

    data = b""
    while True:
        try:
            data += sock.recv(65536)
        except socket.timeout as err:
            raise IOError("Socket timeout.") from err
        else:
            if data.endswith(eof):
                return data.strip(eof)


def main():

    event = threading.Event()
    send_q = Queue()
    recv_q = Queue()

    server_thread = [
        threading.Thread(target=send_thread, args=[send_q, event]),
        threading.Thread(target=recv_thread, args=[recv_q, event]),
    ]

    workers = [
        threading.Thread(target=worker, args=[i, send_q, recv_q, event])
        for i in range(config.WORKERS)
    ]

    # start threads
    for w in chain(server_thread, workers):
        w.start()

    for w in workers:
        w.join()

    event.set()
    print(SharedData.bold("[C][info] All workers stopped."))

    # send stop signal to server side RECV
    print(SharedData.bold("[C][info] Sending kill signal to server RECV."))
    send_q.put(config.END_MARK)

    # waiting for SEND / RECV to stop
    for t in server_thread:
        t.join(timeout=5)

    # load pickled result from INIT port
    print("[C][Info] Fetching Port data from server.")
    data = recv_until_eof(c_sock, config.END_MARK)
    used_ports, shut_ports = json.loads(data.decode(config.ENCODING))
    c_sock.close()

    print("\n[Results]")
    print(f"Used Ports  : {used_ports}")
    print(f"Closed Ports: {shut_ports}")
    print(f"Excluded    : {config.EXCLUDE}")
    print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
