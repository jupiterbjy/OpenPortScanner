# from os import environ
# environ['PYTHONASYNCIODEBUG'] = '1'

# TODO: fetch config from server

import asyncio
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
        # host, port = '127.0.0.1:39'.split(":")  # debug
        port = int(port)
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except TypeError:
            print(f"[C][WARN] Cannot connect to - {host}:{port}")
        else:
            print("[C][INFO] Connected")
            return host, reader, writer


async def worker(id_: int, host, send, recv, event, timeout=None):
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
                p = int(await asyncio.wait_for(recv.get(), timeout=timeout))
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
                    print(await tcp_recv(child_recv, b"%", timeout=timeout))

                except asyncio.TimeoutError:
                    print(SharedData.purple(f"[CS{id_:2}][INFO] Port {p} timeout."))

                except asyncio.IncompleteReadError:
                    print(SharedData.red(f"[CS{id_:2}][WARN] Port {p} disconnected!"))
                    child_send.close()
                    await child_send.wait_closed()

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

    config = SharedData.load_config_new(await tcp_recv(s_recv))

    event = asyncio.Event()
    send_q = asyncio.Queue()
    recv_q = asyncio.Queue()

    server_task = [
        asyncio.create_task(
            send_task(s_send, send_q, event, config.READ_UNTIL, config.TIMEOUT)
        ),
        asyncio.create_task(
            recv_task(s_recv, recv_q, event, config.READ_UNTIL, config.TIMEOUT)
        ),
    ]

    workers = [
        asyncio.create_task(worker(i, host, send_q, recv_q, event, config.TIMEOUT))
        for i in range(config.WORKERS)
    ]

    # waiting for workers to complete.
    for t in workers:
        await t

    print(SharedData.bold("[C][info] All workers stopped."))

    if event.is_set():  # if set, then worker crashed and set the alarm!
        # TODO: put some crash message

        print("task failed! waiting for server task to complete.")

        for t in server_task:
            await t

        print("all task completed.")
        return

    # waiting for SEND / RECV to stop
    # due to timeout feature, if event is set - they'll timeout and finish.
    event.set()
    for t in server_task:
        await t

    # wait until server is closed - preventing RuntimeError.
    s_send.close()
    await s_send.wait_closed()


if __name__ == "__main__":
    import logging

    logging.getLogger("asyncio").setLevel(logging.DEBUG)
    asyncio.run(main(), debug=True)
