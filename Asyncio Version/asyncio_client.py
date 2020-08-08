import asyncio
import json
from itertools import chain

try:
    import SharedData
except ImportError:
    from sys import path

    path.insert(1, "../..")
    path.insert(2, "..")
    import SharedData


# setup
config = SharedData.load_config_new()
TIMEOUT_FACTOR = config.SOCK_TIMEOUT
read_b, write_b = SharedData.rw_bytes(
    config.BYTE_SIZE, config.BYTE_ORDER, config.END_MARK, config.ENCODING
)


# Wait for connection, or a proper IP:PORT input.
def get_connection():
    while True:
        host, port = input("Host [IP:Port] >> ").split(":")
        # host, port = ''.split(":")
        port = int(port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except TypeError:
            print(f"[C][Warn] Cannot connect to - {host}:{port}")
        else:
            print("[C][Info] Connected")
            return reader, writer


async def worker(id_: int, send, recv, event: asyncio.Event):
    q: asyncio.Queue
    send: asyncio.Queue
    recv: asyncio.Queue

    try:
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
    finally:
        # trigger event to stop all threads.
        event.set()


async def send_task(s_sender, q, e):
    s_sender: asyncio.StreamWriter
    q: asyncio.Queue
    e: asyncio.Event

    while True:
        try:
            n = await asyncio.wait_for(q.get(), timeout=TIMEOUT_FACTOR)
        except asyncio.TimeoutError:
            if e.is_set():
                print(SharedData.green("[C][SEND][INFO] Event set!"))
                break
        else:
            q.task_done()

            try:
                s_sender.write(write_b(n))
                await asyncio.wait_for(s_sender.drain(), timeout=TIMEOUT_FACTOR)

            except asyncio.TimeoutError:
                # really just want to use logging and dump logs in other thread..
                print(SharedData.red("[C][Send][CRIT] Timeout while sending!"))
                raise


async def recv_task(s_receiver, q, e):
    s_receiver: asyncio.StreamReader
    q: asyncio.Queue
    e: asyncio.Event

    while True:
        try:
            data = await asyncio.wait_for(
                s_receiver.readuntil(config.READ_UNTIL), timeout=TIMEOUT_FACTOR
            )
        except asyncio.TimeoutError:
            if e.is_set():
                print(SharedData.green(f"[C][RECV][INFO] Event set!"))
                break
        else:
            if data == config.END_MARK:
                print(SharedData.green(f"[C][RECV][INFO] Received eof <{data}>"))
                break

            await q.put(read_b(data))


async def main():

    s_recv, s_send = get_connection()

    event = asyncio.Event()
    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()

    server_task = [
        asyncio.create_task(send_task(s_send, send_q, event)),
        asyncio.create_task(recv_task(s_recv, recv_q, event)),
    ]

    workers = [
        asyncio.create_task(worker(i, send_q, recv_q, event))
        for i in range(config.WORKERS)
    ]

    # waiting for workers to complete.
    for t in workers:
        await t

    if event.is_set():  # if set, then worker crashed and set the alarm!
        # TODO: put some crash message

        print('task failed! waiting for server task to complete.')

        for t in server_task:
            await t

        print('all task completed.')

    else:

        event.set()
        print(SharedData.bold("[C][info] All workers stopped."))

        # waiting for SEND / RECV to stop
        # due to timeout feature, if event is set - they'll timeout and finish.
        for t in server_task:
            await t

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
    asyncio.run(main())
