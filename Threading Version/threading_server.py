import threading
import socket
import json
from itertools import chain
from queue import Queue, Empty

try:
    import SharedData
except ImportError:
    from sys import path

    path.insert(1, "../..")
    path.insert(2, "..")
    import SharedData

# TODO: move global variables to locals.
# TODO: change to logging instead of print
# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort 80).OwningProcess


# setup
config = SharedData.load_json_config()
IP = SharedData.get_external_ip()
TIMEOUT_FACTOR = config.SOCK_TIMEOUT
read_b, write_b = SharedData.rw_bytes(
    config.BYTE_SIZE, config.BYTE_ORDER, config.END_MARK, config.ENCODING
)


# Main connection start
s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"[S][Info] Connect client to: {IP}:{config.INIT_PORT}")
try:
    s_sock.bind(("", config.INIT_PORT))
except OSError:
    print(SharedData.red(f"[S][Crit] Cannot open server at port {config.INIT_PORT}."))
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
            print(SharedData.purple(f"[SS{id_:2}][Warn] Worker {id_} stopping."))
            return

        # get next work.
        p: int = q.get()
        q.task_done()

        # check if port is in blacklist.
        if p in config.EXCLUDE:
            print(SharedData.cyan(f"[SS{id_:2}][Info] Skipping Port {p}."))
            continue

        # receive worker announcement.
        try:
            worker_id = recv.get(timeout=TIMEOUT_FACTOR)
        except Empty:  # Timeout
            worker_id = 'NULL'

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
            print(SharedData.red(f"[SS{id_:2}][Info] Port {p} Timeout."))
            SHUT_PORTS.append(p)

        except OSError:
            print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} in use."))
            USED_PORTS.append(p)

        else:
            print(SharedData.green(f"[SS{id_:2}][Info] Port {p} is open."))

        child_sock.close()

    # Send end signal to client.
    # first worker catching this signal will go offline.

    print(SharedData.cyan(f"[SS{id_:2}][Info] Done. Sending stop signal."))
    send.put(70000)  # causing overflow to socket in client, stopping it.


def send_thread(q: Queue, e: threading.Event):
    while True:

        try:
            n = q.get(timeout=TIMEOUT_FACTOR)
        except Empty:
            if e.is_set():
                print("[S][SEND] Event Set!")
                break
        else:
            q.task_done()

            try:
                conn.send(write_b(n))
            except (ConnectionAbortedError, ConnectionResetError):
                print("[S][SEND] Connection reset!")
                break


def recv_thread(q: Queue, e: threading.Event):
    conn.settimeout(TIMEOUT_FACTOR)
    # making a vague assumption of timeout situation.

    while True:

        try:
            data = conn.recv(65536)
        except (ConnectionAbortedError, ConnectionResetError):
            break
        except socket.timeout:
            if e.is_set():
                print(SharedData.red(f"[S][RECV] Timeout, closing RECV thread."))
                break
        else:
            if data == config.END_MARK:
                print(SharedData.green(f"[S][RECV] Received eof <{data}>"))
                break

            q.put(read_b(data))


def main():
    # just wrapping in function makes global to local variable, runs faster.

    event = threading.Event()
    work = generate_queue()

    send_q = Queue()
    recv_q = Queue()

    server_thread = [
        threading.Thread(target=send_thread, args=[send_q, event]),
        threading.Thread(target=recv_thread, args=[recv_q, event]),
    ]

    workers = [
        threading.Thread(target=worker, args=[i, work, send_q, recv_q, event])
        for i in range(config.WORKERS)
    ]

    # start threads
    for w in chain(server_thread, workers):  # just wanted to try out chain.
        w.start()

    for w in workers:  # I need to stop server thread somehow..
        w.join()

    event.set()
    print(SharedData.bold("[S][Info] All workers stopped."))

    # send stop signal to client side RECV
    print(SharedData.bold("[S][info] Sending kill signal to client RECV."))
    conn.send(config.END_MARK)

    for t in server_thread:
        t.join()
    print("[S][info] RECV/SEND stopped.")

    # sending pickled port results
    print(f"[S][Info] Sending port data.")
    used_data = json.dumps([USED_PORTS, SHUT_PORTS])

    if conn.send(used_data.encode(config.ENCODING) + config.END_MARK):
        print(f"[S][CRIT] Socket connection broken.")

    conn.close()

    print("\n[Results]")
    print(f"Used Ports  : {USED_PORTS}")
    print(f"Closed Ports: {SHUT_PORTS}")
    print(f"Excluded    : {config.EXCLUDE}")
    print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")


if __name__ == "__main__":
    main()
