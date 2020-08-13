from typing import Callable
from Shared import send_task, recv_task, tcp_recv, tcp_send
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


# load config
IP = SharedData.get_external_ip()
config = SharedData.load_config_new()

# fetch config data for a tiny bit of better access speed.
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
    await send.wait_closed()


async def get_connection(handler: Callable):
    try:
        server_co = await asyncio.start_server(handler, port=config.INIT_PORT)
    except (TypeError, OverflowError):
        print(f"[S][CRIT] Port invalid.")
        raise

    except OSError:
        print(SharedData.red(f"[S][Crit] Cannot open server at {config.INIT_PORT}."))
        raise

    else:
        print(f"[S][INFO] Connect client to: {IP}:{config.INIT_PORT}")
        return server_co


def generate_queue():
    print(f"Generating Queue from 1~{config.PORT_MAX}.")
    q = asyncio.Queue()
    for i in range(1, config.PORT_MAX + 1):
        q.put_nowait(i)

    return q


async def worker(id_, q, send, recv, event: asyncio.Event):
    q: asyncio.Queue
    send: asyncio.Queue
    recv: asyncio.Queue

    async def worker_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter, port: int,
            handle_finished: asyncio.Event
    ):
        print(SharedData.green(f"[SS{id_:2}][INFO] --- IN HANDLER ---"))
        await tcp_send(p, writer, b'%', timeout=TIMEOUT_FACTOR)
        print(SharedData.green(f"[SS{id_:2}][INFO] Port {port} is open."))

        writer.close()
        await writer.wait_closed()
        handle_finished.set()

    try:
        while not q.empty() and not event.is_set():

            # get next work.
            print(f"[SS{id_:2}][INFO] Getting new port.")
            p: int = await q.get()
            q.task_done()

            # check if port is in blacklist.
            if p in config.EXCLUDE:
                print(SharedData.cyan(f"[SS{id_:2}][INFO] Skipping Port {p}."))
                continue

            # receive worker announcement.
            worker_id = await recv.get()
            recv.task_done()
            print(f"[SS{id_:2}][INFO] Worker {worker_id} requests task.")

            print(f"[SS{id_:2}][INFO] Sending port {p} to client.")
            await send.put(p)

            handle_ev = asyncio.Event()

            print(f"[SS{id_:2}][INFO] Trying to serve port {p}.")
            try:
                child_sock = await asyncio.wait_for(asyncio.start_server(
                    lambda r, w: worker_handler(r, w, p, handle_ev), port=p), TIMEOUT_FACTOR)

            except AssertionError:
                print(SharedData.red(f"[SS{id_:2}][INFO] Port {p} assertion failed!"))
                SHUT_PORTS.append(p)

            except OSError:
                print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} in use."))
                USED_PORTS.append(p)

            else:
                try:
                    await child_sock.start_serving()
                    await asyncio.wait_for(handle_ev.wait(), TIMEOUT_FACTOR)

                except asyncio.TimeoutError:
                    print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} timeout."))
                finally:
                    child_sock.close()
                    await child_sock.wait_closed()

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
