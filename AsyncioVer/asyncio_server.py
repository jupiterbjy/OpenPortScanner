from typing import Callable
from Shared import send_task, recv_task, tcp_send
import asyncio

try:
    import SharedData
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData

DEBUG = False


# TODO: change to logging instead of print
# TODO: change wrongful *task_done calls and move it to end of each iteration.
# TODO: set recv send task as daemon to prevent No running loop error on end of script.
# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort 80).OwningProcess


# Main server handler start
def handler_closure(
    send_recv: [asyncio.Queue, asyncio.Queue],
    fail_ev: asyncio.Event,
    start_ev: asyncio.Event,
    stop_ev: asyncio.Event,
    delimiter: bytes = b"\n",
    timeout=None,
):
    async def main_handler(
        recv: asyncio.StreamReader, send: asyncio.StreamWriter,
    ):
        """
        Main handler of server.
        """

        print(f"[S][INFO] Connected.")
        start_ev.set()  # start loading workers.

        send_q, recv_q = send_recv

        server_tasks = (
            send_task(send, send_q, fail_ev, delimiter, timeout),
            recv_task(recv, recv_q, fail_ev, delimiter, timeout),
        )

        gather_task = asyncio.gather(*server_tasks)

        try:
            await gather_task
        except ConnectionResetError:
            print("Connection reset!")
            gather_task.cancel()
        finally:
            send.close()
            await send.wait_closed()
            stop_ev.set()

    return main_handler


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
            return server_co, port


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
    timeout=None,
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

            print(f"[SS{id_:2}][INFO] Worker {worker_id} available.")

            # get next work.
            print(f"[SS{id_:2}][INFO] Getting new port.")

            # if timeout getting port, either task is empty or just coroutine delayed.
            try:
                p: int = await asyncio.wait_for(task_q.get(), timeout)
                task_q.task_done()
            except asyncio.TimeoutError:
                if task_q.empty():
                    break
                else:
                    await recv.put(worker_id)
                    continue
                    # put back in and run again.

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
            worker(
                i,
                works,
                send,
                recv,
                excl,
                in_use,
                unreachable,
                e,
                delimiter,
                config.TIMEOUT,
            )
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
    config = SharedData.load_json_config()

    work = generate_queue(config.PORT_MAX)
    delimiter = config.READ_UNTIL.encode(config.ENCODING)
    timeout = config.TIMEOUT

    started = asyncio.Event()
    fail_trigger = asyncio.Event()
    stop = asyncio.Event()

    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()

    in_use = asyncio.Queue()
    failed = asyncio.Queue()

    # handler for primary connection.
    handle = handler_closure([send_q, recv_q], fail_trigger, started, stop, delimiter, timeout)

    async def handler(recv, send):
        # send config to client.
        print("Sending config to client.")
        await tcp_send(SharedData.load_config_raw(), send)

        await handle(recv, send)
        send.close()

    # start server
    server_co, port_primary = await get_connection(handler)
    await server_co.start_serving()
    config.EXCLUDE.append(port_primary)

    # wait until connection is established, and handler started.
    await started.wait()

    # start workers
    await run_workers(config, work, send_q, recv_q, in_use, failed, stop)

    fail_trigger.set()
    await stop.wait()

    server_co.close()
    await server_co.wait_closed()

    last_port = config.PORT_MAX

    if not work.empty():
        last_port = await work.get()
        print(f"Task failed! Showing result before failed port {last_port}.")

    # overriding
    in_use = async_q_to_list(in_use)
    failed = async_q_to_list(failed)

    result = SharedData.get_port_result(in_use, failed, config.EXCLUDE, config.PORT_MAX)

    print("\n[Count Results]")
    print(f"Used Ports  : {result['Occupied']}")
    print(f"Closed Ports: {result['Unreachable']}")
    print(f"Excluded    : {result['Excluded']}")
    print(f"\nAll other ports from 1~{last_port} is open.")

    SharedData.dump_result(result, "tcp_scan_result")


if __name__ == "__main__":


    try:
        assert isinstance(loop := asyncio.new_event_loop(), asyncio.ProactorEventLoop)
        # No ProactorEventLoop is in asyncio on other OS, will raise AttributeError in that case.

    except (AssertionError, AttributeError):
        asyncio.run(main(), debug=False)

    else:
        print("Proactor Event loop wrapping Active.")

        async def proactor_wrap(loop_: asyncio.ProactorEventLoop, fut: asyncio.coroutines):
            await fut
            loop_.stop()

        loop.create_task(proactor_wrap(loop, main()))
        loop.run_forever()
