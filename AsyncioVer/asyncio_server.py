from typing import Callable
from Shared import send_task, recv_task, tcp_send
import asyncio
import json

# TODO: clean this json mess

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


# Main server handler start
async def main_handler(
    recv: asyncio.StreamReader,
    send: asyncio.StreamWriter,
    send_q: asyncio.Queue,
    recv_q: asyncio.Queue,
    fail_ev: asyncio.Event,
    start_ev: asyncio.Event,
    delimiter: bytes = b"\n",
    timeout=None,
):
    """
    Main handler of server.
    Feed additional parameters with use of <lambda send, recv: main_handler(...)>,
    """

    print(f"[S][INFO] Connected.")
    start_ev.set()  # start loading workers.

    server_tasks = (
        send_task(send, send_q, fail_ev, delimiter, timeout),
        recv_task(recv, recv_q, fail_ev, delimiter, timeout),
    )

    gather_task = asyncio.gather(*server_tasks)
    # cancellation on asyncio.gather cause all coroutines in seq to cancel.
    # gather_task.cancel()
    try:
        await gather_task
    except ConnectionResetError:
        print('Connection reset!')

    send.close()
    await send.wait_closed()


async def get_connection(handler: Callable):
    ip = SharedData.get_external_ip()

    while True:
        try:
            port = int(input("Enter primary server port >> "))
            # port = 80
            if port > 65535:
                raise ValueError

        except ValueError:
            print("Wrong port value!")
            continue

        try:
            server_co = await asyncio.start_server(handler, port=port)

        except OSError:
            print(SharedData.red(f"[S][CRIT] Cannot open server at port."))
            raise

        else:
            print(f"[S][INFO] Connect client to: {ip}:{port}")
            return server_co


def generate_queue(max_port: int):
    print(f"Generating Queue from 1~{max_port}.")
    q = asyncio.Queue()
    for i in range(1, max_port + 1):
        q.put_nowait(i)

    return q


async def worker(
    id_,
    task_q: asyncio.Queue,
    send: asyncio.Queue,
    recv: asyncio.Queue,
    exclude: set,
    used: asyncio.Queue,
    unreachable: asyncio.Queue,
    event: asyncio.Event,
    delimiter: bytes,
    timeout=None
):
    async def worker_handler(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        port: int,
        handle_finished: asyncio.Event,
    ):
        print(SharedData.green(f"[SS{id_:2}][INFO] --- IN HANDLER ---"))
        await tcp_send(p, writer, delimiter, timeout=timeout)
        print(SharedData.green(f"[SS{id_:2}][INFO] Port {port} is open."))

        writer.close()
        await writer.wait_closed()
        handle_finished.set()

    try:
        while not task_q.empty() and not event.is_set():

            # receive worker announcement.
            try:
                worker_id = await asyncio.wait_for(recv.get(), timeout)
                recv.task_done()
            except asyncio.TimeoutError:
                print(SharedData.red(f"[SS{id_:2}][Warn] Timeout."))
                continue

            print(f"[SS{id_:2}][INFO] Worker {worker_id} requests task.")

            # get next work.
            print(f"[SS{id_:2}][INFO] Getting new port.")

            p: int = await task_q.get()
            task_q.task_done()

            # check if port is in blacklist.
            if p in exclude:
                print(SharedData.cyan(f"[SS{id_:2}][INFO] Skipping Port {p}."))
                continue

            print(f"[SS{id_:2}][INFO] Sending port {p} to client.")
            await send.put(p)

            handle_ev = asyncio.Event()

            print(f"[SS{id_:2}][INFO] Trying to serve port {p}.")
            try:
                # child_sock = await asyncio.wait_for(asyncio.start_server(
                #     lambda r, w: worker_handler(r, w, p, handle_ev), port=p), TIMEOUT_FACTOR)

                child_sock = await asyncio.start_server(
                    lambda r, w: worker_handler(r, w, p, handle_ev), port=p
                )

            # except asyncio.TimeoutError:
            #     # not sure why start_server gets timeout.
            #     # maybe I need to control number of task so opening server don't hang.
            #     print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} timeout while opening."))
            #     await unreachable.put(p)

            except AssertionError:
                print(SharedData.red(f"[SS{id_:2}][INFO] Port {p} assertion failed!"))
                await unreachable.put(p)

            except OSError:
                print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} in use."))
                await used.put(p)

            else:
                try:
                    await child_sock.start_serving()
                    await asyncio.wait_for(handle_ev.wait(), timeout)

                except asyncio.TimeoutError:
                    print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} timeout."))
                    await unreachable.put(p)
                finally:
                    child_sock.close()
                    await child_sock.wait_closed()

        # Send end signal to client.
        # first worker catching this signal will go offline.

        print(SharedData.cyan(f"[SS{id_:2}][INFO] Done. Sending stop signal."))
        await send.put("DONE")  # causing int type-error on client side workers.

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
    config,
    works: asyncio.Queue,
    send: asyncio.Queue,
    recv: asyncio.Queue,
    in_use: asyncio.Queue,
    unreachable: asyncio.Queue,
    e: asyncio.Event,
):
    """
    Handle worker tasks.
    """

    delimiter = config.READ_UNTIL.encode(config.ENCODING)
    excl = set(config.EXCLUDE)

    workers = [
        asyncio.create_task(
            worker(i, works, send, recv, excl, in_use, unreachable, e, delimiter, config.TIMEOUT)
        )
        for i in range(config.WORKERS)
    ]

    for t in workers:  # wait until workers are all complete
        await t

    print(SharedData.bold("[S][info] All workers stopped."))


def async_q_to_list(q: asyncio.Queue) -> list:
    out = []
    try:
        while True:
            out.append(q.get_nowait())
    except asyncio.queues.QueueEmpty:
        return out


async def main():

    config = SharedData.load_config_new()
    work = generate_queue(config.PORT_MAX)
    delimiter = config.READ_UNTIL.encode(config.ENCODING)

    start_event = asyncio.Event()
    stop_event = asyncio.Event()

    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()

    in_use = asyncio.Queue()
    unreachable = asyncio.Queue()

    # handler for primary connection.
    async def handler(recv, send):
        # send config to client.
        print("Sending config to client.")
        await tcp_send(json.dumps(SharedData.load_config_json()), send)

        await main_handler(
            recv,
            send,
            send_q,
            recv_q,
            stop_event,
            start_event,
            delimiter,
            config.TIMEOUT,
        )

    server_co = await get_connection(handler)
    await server_co.start_serving()
    await start_event.wait()

    # TODO: clean this mess

    # start workers
    await run_workers(
        config, work, send_q, recv_q, in_use, unreachable, stop_event,
    )

    stop_event.set()
    server_co.close()
    await server_co.wait_closed()

    print(SharedData.bold("[S][INFO] All workers stopped."))

    last_port = config.PORT_MAX

    if not work.empty():
        last_port = await work.get()
        print(f"Task failed! Showing test result before failed port {last_port}.")

    used = set(async_q_to_list(in_use))
    closed = set(async_q_to_list(unreachable))
    excluded = set(config.EXCLUDE)
    comb = used | closed | excluded

    print("\n[Results]")
    print(f"Used Ports  : {used}")
    print(f"Closed Ports: {closed}")
    print(f"Excluded    : {excluded}")
    print(f"Combined    : {comb}")
    print(f"\nAll other ports from 1~{last_port} is open.")

    SharedData.dump_result(list(comb), 'results.json')


if __name__ == "__main__":
    import logging

    logging.getLogger("asyncio").setLevel(logging.DEBUG)
    asyncio.run(main(), debug=True)
