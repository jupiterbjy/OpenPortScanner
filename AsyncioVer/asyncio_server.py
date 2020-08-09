from os import environ
import json
from Shared import tcp_recv, tcp_send, send_task, recv_task

environ["PYTHONASYNCIODEBUG"] = "1"
import asyncio

try:
    import SharedData

    print("DEBUGGING")
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


# TODO: change to logging instead of print
# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort 80).OwningProcess


# setup
config = SharedData.load_config_new()
IP = SharedData.get_external_ip()
TIMEOUT_FACTOR = config.SOCK_TIMEOUT
READ_UNTIL = config.READ_UNTIL.encode()


async def main_handler(
    recv: asyncio.StreamReader,
    send: asyncio.StreamWriter,
    send_q: asyncio.Queue,
    recv_q: asyncio.Queue,
    e: asyncio.Event,
):
    server_task = [
        asyncio.create_task(send_task(send, send_q, e, READ_UNTIL, TIMEOUT_FACTOR)),
        asyncio.create_task(recv_task(recv, recv_q, e, READ_UNTIL, TIMEOUT_FACTOR)),
    ]

    workers =


# Main server start


async def get_connection():
    while True:
        try:
            port = int(input("Port >> "))
            if port > 65536:
                raise TypeError
        except TypeError:
            print(f"[S][WARN] Port invalid.")
        else:
            print(f"[S][Info] Connect client to: {IP}:{port}")
            try:
                server_co = await asyncio.start_server(main_handler, port=port)
            except OSError:
                print(SharedData.red(f"[S][Crit] Cannot open server at {port}."))
                exit()
            else:
                print(f"[S][Info] Connected.")
                return server_co


# Results
USED_PORTS = []
SHUT_PORTS = []


def generate_queue():
    print(f"Generating Queue from 1~{config.PORT_MAX}.")
    q = asyncio.Queue()
    for i in range(1, config.PORT_MAX):
        q.put_nowait(i)

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
            worker_id = "NULL"

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
    send.put()  # causing overflow to socket in client, stopping it.


async def main():

    server_co = await get_connection()

    event = asyncio.Event()
    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()
    work = generate_queue()

    workers = [
        asyncio.create_task(worker(i, host, send_q, recv_q, event))
        for i in range(config.WORKERS)
    ]

    for t in workers:  # I need to stop server thread somehow..
        await t

    if event.is_set():
        print("task failed! waiting for server task to complete.")
        server_co.close()
        await server_co.wait_closed()

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
