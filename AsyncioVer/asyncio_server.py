from os import environ
import json
from typing import Callable
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

# Results
USED_PORTS = []
SHUT_PORTS = []


# TODO: convert to queue


# Main server handler start
async def main_handler(
    recv: asyncio.StreamReader,
    send: asyncio.StreamWriter,
    send_q: asyncio.Queue,
    recv_q: asyncio.Queue,
    fail_ev: asyncio.Event,
    start_ev: asyncio.Event
):
    """
    Main handler of server.
    Feed additional parameters with use of <lambda send, recv: main_handler(...)>,
    """

    print(f"[S][INFO] Connected.")
    start_ev.set()  # start loading workers.

    server_tasks = (
        send_task(send, send_q, fail_ev, READ_UNTIL, TIMEOUT_FACTOR),
        recv_task(recv, recv_q, fail_ev, READ_UNTIL, TIMEOUT_FACTOR),
    )

    gather_task = asyncio.gather(*server_tasks)
    # cancellation on asyncio.gather cause all coroutines in seq to cancel.
    # gather_task.cancel()

    await gather_task
    send.close()


async def get_connection(handler: Callable):
    while True:
        try:
            port = int(input("Port >> "))
            if port > 65536:
                raise TypeError

        except TypeError:
            print(f"[S][WARN] Port invalid.")

        else:
            print(f"[S][INFO] Connect client to: {IP}:{port}")

            try:
                server_co = await asyncio.start_server(handler, port=port)

            except OSError:
                print(SharedData.red(f"[S][Crit] Cannot open server at {port}."))

            else:
                return server_co


def generate_queue():
    print(f"Generating Queue from 1~{config.PORT_MAX}.")
    q = asyncio.Queue()
    for i in range(1, config.PORT_MAX):
        q.put_nowait(i)

    return q


async def worker(id_, q, send, recv, event: asyncio.Event):
    q: asyncio.Queue
    send: asyncio.Queue
    recv: asyncio.Queue

    async def worker_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        print(f"[SS{id_:2}][INFO] Opening Port {p}.")
        try:
            writer.write(b"1")
            await asyncio.wait_for(writer.drain(), timeout=TIMEOUT_FACTOR)

        except asyncio.TimeoutError:
            print(SharedData.red(f"[SS{id_:2}][INFO] Port {p} Timeout."))
            SHUT_PORTS.append(p)
        else:
            print(SharedData.green(f"[SS{id_:2}][INFO] Port {p} is open."))
        finally:
            writer.close()
            handler_event.set()

    try:
        while not q.empty() and not event.is_set():

            # get next work.
            p: int = await q.get()
            q.task_done()

            # check if port is in blacklist.
            if p in config.EXCLUDE:
                print(SharedData.cyan(f"[SS{id_:2}][INFO] Skipping Port {p}."))
                continue

            # receive worker announcement.
            worker_id = await recv.get()
            recv.task_done()
            print(f"[SS{id_:2}][INFO] Worker {worker_id} announce READY.")

            print(f"[SS{id_:2}][INFO] Sending port {p} to Client.")
            await send.put(p)

            handler_event = asyncio.Event()
            child_sock = await asyncio.start_server(worker_handler, port=p)
            try:
                await child_sock.start_serving()

            except OSError:
                print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} in use."))
                USED_PORTS.append(p)

            else:
                await handler_event.wait()

            finally:
                child_sock.close()

        # Send end signal to client.
        # first worker catching this signal will go offline.

        print(SharedData.cyan(f"[SS{id_:2}][INFO] Done. Sending stop signal."))
        await send.put(READ_UNTIL)  # causing int type-error on client side workers.

    except Exception:
        # trigger event to stop all threads.
        print(SharedData.red(f"[SS{id_:2}][CRIT] Exception Event set!."))
        event.set()
        raise

    if event.is_set():
        print(SharedData.bold(f"[SS{id_:2}][WARN] Task Finished by event."))
    else:
        print(SharedData.bold(f"[SS{id_:2}][INFO] Task Finished."))


async def run_workers(
        workers_max: int,
        works: asyncio.Queue,
        send: asyncio.Queue,
        recv: asyncio.Queue,
        e: asyncio.Event,
):
    """
    Handle worker tasks.
    """

    workers = [
        asyncio.create_task(worker(i, works, send, recv, e)) for i in range(workers_max)
    ]

    for t in workers:  # wait until workers are all complete
        await t

    print(SharedData.bold("[S][info] All workers stopped."))


async def main():
    start_event = asyncio.Event()
    fail_event = asyncio.Event()
    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()
    work = generate_queue()

    async def handler(recv, send):
        await main_handler(recv, send, send_q, recv_q, fail_event, start_event)

    server_co = await get_connection(handler)

    await server_co.start_serving()
    await start_event.wait()
    await run_workers(config.WORKERS, work, send_q, recv_q, fail_event)

    if fail_event.is_set():
        print("task failed! waiting for server task to complete.")
        server_co.close()
        await server_co.wait_closed()

        print("all task completed.")
        return

    print("\n[Results]")
    print(f"Used Ports  : {USED_PORTS}")
    print(f"Closed Ports: {SHUT_PORTS}")
    print(f"Excluded    : {config.EXCLUDE}")
    print(f"\nAll other ports from 1~{config.PORT_MAX} is open.")

    fail_event.set()
    server_co.close()
    await server_co.wait_closed()


if __name__ == "__main__":
    import logging

    logging.getLogger("asyncio").setLevel(logging.DEBUG)
    asyncio.run(main(), debug=True)
