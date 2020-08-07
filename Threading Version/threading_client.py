import socket
import pickle
import threading
from itertools import chain
from queue import Queue, Empty
try:
    import SharedData
except ImportError:
    from sys import path
    path.insert(1, '..')
    import SharedData


# setup
config = SharedData.prepare(__file__)
c_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
TIMEOUT_FACTOR = config.TIMEOUT * 2 if config.TIMEOUT < 2 else 5
read_b, write_b = SharedData.rw_bytes(
    config.BYTE_SIZE, config.BYTE_ORDER, config.END_MARK, config.ENCODING)


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

        try:
            data = recv.get()
        except Empty:
            continue

        recv.task_done()

        p = data
        print(f"[CS{id_:2}][Info] Worker {id_} received {p}.")

        print(f"[CS{id_:2}][Info] Connecting Port {p}.")
        child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        child_sock.settimeout(config.TIMEOUT)

        try:
            child_sock.connect((host, p))
        except OverflowError:
            print(SharedData.cyan(f"[CS{id_:2}][Info] Stop Signal received!"))
            break

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
                print("[C][SEND] Event set!")
                break
        else:
            q.task_done()

            try:
                c_sock.send(write_b(n))
            except (ConnectionAbortedError, ConnectionResetError):
                print("[C][SEND] Connection reset!")
                break


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
                print(SharedData.red(f"[C][RECV] Event set!"))
                break
        else:
            if data == config.END_MARK.encode(config.ENCODING):
                print(SharedData.green(f"[C][RECV] Received {data.decode(config.ENCODING)}"))
                break

            q.put(read_b(data))


def recv_while_timeout(sock: socket.socket, eof: bytes, buffer=4096, timeout=3):
    sock.settimeout(timeout)  # not sure this works while socket is open..

    # TODO: use := to add data in while loop, check python 3.9
    data = b''
    while True:
        try:
            data += sock.recv(buffer)
        except socket.timeout as err:
            raise IOError("Socket timeout.")
        else:
            if data.endswith(eof):
                return data


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
        while SharedData.any_thread_alive(workers):
            timer.wait(timeout=0.2)

    except KeyboardInterrupt:  # fix this
        event.set()
        for w in workers:
            w.join()
        print("[C][Warn] All workers stopped.")

    else:
        event.set()
        for w in workers:  # I need to stop server thread somehow..
            w.join()
        print("[C][info] All workers stopped.")

        # send stop signal to server side RECV
        # TODO: change config.END_MARK to bytes, removing need to encode every time.
        print(SharedData.cyan("[C][info] Sending kill signal to server RECV."))
        send_q.put(config.END_MARK.encode(config.ENCODING))
        for t in server_thread:
            t.join()
        print("[C][info] RECV/SEND stopped.")

        # load pickled result from INIT port
        print("[C][Info] fetching Port data from server.")
        data = recv_while_timeout(c_sock, config.END_MARK.encode(config.ENCODING))
        used_ports, shut_ports = pickle.loads(data)
        c_sock.close()

        # while True:
        #     try:
        #         USED_PORTS, SHUT_PORTS = pickle.loads(data)
        #     except pickle.UnpicklingError:
        #         data += c_sock2.recv(4096)
        #         continue
        #     else:
        #         c_sock2.close()
        #         break

        print("[C][Info] Received Port data from server.")

        print("\n[Results]")
        print(f"Used Ports  : {used_ports}")
        print(f"Closed Ports: {shut_ports}")
        print(f"Excluded    : {config.EXCLUDE}")
        print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
