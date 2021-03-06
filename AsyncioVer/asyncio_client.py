# from os import environ
# environ['PYTHONASYNCIODEBUG'] = '1'


import json
import asyncio
from types import SimpleNamespace
from Shared import send_task, recv_task, tcp_recv

try:
    import SharedData

    print("DEBUGGING")
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


# Wait for connection, or a proper IP:PORT input.
async def get_connection():
    while True:
        host, port = input("Host [IP:Port] >> ").split(":")
        # host, port = '127.0.0.1:80'.split(":")  # debug
        port = int(port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except TypeError:
            print(f"[C][WARN] Cannot connect to - {host}:{port}")
        else:
            print("[C][INFO] Connected")
            return host, reader, writer


async def worker(id_: int, host, send, recv, event, delimiter, timeout=None):
    q: asyncio.Queue
    send: asyncio.Queue
    recv: asyncio.Queue
    event: asyncio.Event

    try:
        # if one thread crashes, will trigger event and gradually stop all threads.

        while not event.is_set():

            # announce server that the worker is ready.
            print(f"[CS{id_:2}][INFO] Worker {id_:2} READY.")
            await send.put(id_)

            try:
                p = await asyncio.wait_for(recv.get(), timeout=timeout)
                p = int(p)
                recv.task_done()
            except asyncio.TimeoutError:
                print(
                    SharedData.red(
                        f"[CS{id_:2}][WARN] Worker {id_:2} timeout fetching from Queue."
                    )
                )
                continue

            except ValueError:
                print(SharedData.cyan(f"[CS{id_:2}][INFO] Stop Signal received!"))
                break

            print(f"[CS{id_:2}][INFO] Connecting Port {p}.")
            try:
                child_recv, child_send = await asyncio.wait_for(
                    asyncio.open_connection(host, p), timeout
                )

            except asyncio.TimeoutError:
                print(SharedData.purple(f"[CS{id_:2}][INFO] Port {p} timeout."))

            except OSError:
                print(SharedData.red(f"[CS{id_:2}][WARN] Port {p} connection refused."))

            else:
                try:
                    print(await tcp_recv(child_recv, delimiter, timeout=timeout))

                except asyncio.TimeoutError:
                    print(SharedData.purple(f"[CS{id_:2}][INFO] Port {p} timeout."))

                except asyncio.IncompleteReadError:
                    print(SharedData.red(f"[CS{id_:2}][WARN] Port {p} disconnected!"))

                else:
                    print(f"[CS{id_:2}][INFO] Port {p} open.")
                    print(SharedData.green(f"[CS{id_:2}][INFO] Port {p} is available."))
                finally:
                    child_send.close()
                    await child_send.wait_closed()

    except Exception:
        # trigger event to stop all threads.
        print(SharedData.red(f"[CS{id_:2}][CRIT] Exception Event set!."))
        event.set()
        raise

    print(SharedData.bold(f"[CS{id_:2}][INFO] Task Finished."))


async def main():

    host, s_recv, s_send = await get_connection()

    print(f'Config received from {host}.')
    print(raw := await tcp_recv(s_recv))
    config_json = json.loads(raw)
    config = SimpleNamespace(**config_json)

    event = asyncio.Event()
    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()
    delimiter = config.READ_UNTIL.encode(config.ENCODING)

    server_task = (
        asyncio.create_task(
            send_task(s_send, send_q, event, delimiter, config.TIMEOUT)
        ),
        asyncio.create_task(
            recv_task(s_recv, recv_q, event, delimiter, config.TIMEOUT)
        ),
    )

    workers = [
        asyncio.create_task(worker(i, host, send_q, recv_q, event, delimiter, config.TIMEOUT))
        for i in range(config.WORKERS)
    ]

    # waiting for workers to complete.
    for t in workers:
        await t

    print(SharedData.bold("[C][INFO] All workers stopped."))

    if event.is_set():  # if set, then worker crashed and set the alarm!
        print("task failed! waiting for server task to complete.")
    else:
        event.set()

    for t in server_task:
        try:
            await t
        except ConnectionResetError:
            print("Connection reset!")
            continue

    # wait until server is closed - preventing RuntimeError.
    s_send.close()
    await s_send.wait_closed()


if __name__ == "__main__":
    # import logging
    # logging.getLogger("asyncio").setLevel(logging.DEBUG)

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

