from numbers import Number
import socket
import threading
from queue import Queue, Empty

try:
    import SharedData  # only works because pycharm set working directory to project.

    print("DEBUGGING")
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


def tcp_recv(conn: socket.socket, delimiter: bytes = b'\n'):
    data_length = b''
    try:
        for chunk in iter(lambda: conn.recv(1), delimiter):
            data_length += chunk
    # except socket.timeout:
    except ConnectionResetError:
        print("tcp_recv: Disconnected from Server.")
        raise

    data = conn.recv(int(data_length))

    return data.decode()


def tcp_send(data, conn: socket.socket, delimiter: bytes = b'\n'):
    data_byte = str(data).encode()

    data_length = len(data_byte)
    conn.send(str(data_length).encode() + delimiter + data_byte)


def send_task(conn: socket.socket, q: Queue, stop_e: threading.Event, delimiter: bytes, timeout=None):

    print("[SEND][INFO] Started")
    conn.settimeout(timeout)

    try:
        while True:
            try:
                n = q.get(timeout=timeout)
                q.task_done()
            except Empty:
                if stop_e.is_set():
                    print(SharedData.bold("[SEND][INFO] Event set!"))
                    return
            else:
                try:
                    tcp_send(n, conn, delimiter)

                except socket.timeout:
                    # really just want to use logging and dump logs in other thread..
                    print(SharedData.red("[Send][CRIT] Connection Broken!"))
                    break
    except Exception:
        print(SharedData.bold("[SEND][CRIT] Stopping SEND!"))
        stop_e.set()
        raise


async def recv_task(conn: socket.socket, q: Queue, e: threading.Event, delimiter: bytes, timeout=None):

    print("[RECV][INFO] Started")

    conn.settimeout(timeout)

    try:
        while True:
            try:
                data = tcp_recv(conn, delimiter)
            except socket.timeout:
                print('[RECV][WARN] TIMEOUT')
                if e.is_set():
                    print(SharedData.bold(f"[RECV][INFO] Event set!"))
                    return
            else:
                q.put(data)

    except Exception:
        print(SharedData.bold("[RECV][CRIT] Stopping SEND!"))
        e.set()
        raise
