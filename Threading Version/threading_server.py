import threading
import socket
import json
from .Shared import tcp_recv, tcp_send, recv_task, send_task
from itertools import chain
from queue import Queue, Empty

try:
    import SharedData
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


# TODO: change to logging instead of print
# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort 80).OwningProcess


# Main connection start
def get_main_connection(config):
    ip = SharedData.get_external_ip()
    s_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while True:
        try:
            port = int(input("Enter primary server port >> "))
            # port = 80
            if port > 65535:
                raise ValueError

        except ValueError:
            print("Wrong port value!")
            continue

        print(f"[S][INFO] Connect client to: {ip}:{port}")

        try:
            s_sock.bind(("", port))

        except OSError:
            print(SharedData.red(f"[S][CRIT] Cannot open server at port."))
            raise

        else:
            conn, addr = s_sock.accept()  # block until client signal
            return conn, addr


def generate_queue(max_port: int):
    print(f"Generating Queue from 1~{max_port}.")
    q = Queue()
    for i in range(1, max_port + 1):
        q.put(i)

    return q


def run_workers(
    config,
    works: Queue,
    send: Queue,
    recv: Queue,
    in_use: Queue,
    blocked: Queue,
    e: threading.Event,
):

    delimiter = config.READ_UNTIL.encode(config.ENCODING)
    excl = set(config.EXCLUDE)

    workers = [
        threading.Thread(
            target=worker,
            args=[
                i,
                works,
                send,
                recv,
                excl,
                in_use,
                blocked,
                e,
                delimiter,
                config.TIMEOUT,
            ],
        )
        for i in range(config.WORKERS)
    ]

    for w in workers:
        w.start()

    for w in workers:
        w.join()

    print(SharedData.bold("[S][info] All workers stopped."))


def worker(
    id_,
    task_q,
    send,
    recv,
    exclude: set,
    used: Queue,
    blocked: Queue,
    event: threading.Event,
    delimiter: bytes,
    timeout=None,
):
    try:
        while not task_q.empty() and not event.is_set():

            # receive worker announcement.
            try:
                worker_id = recv.get(timeout=timeout)
                recv.task_done()
            except Empty:
                print(SharedData.red(f"[SS{id_:2}][Warn] Timeout."))
                continue

            print(f"[SS{id_:2}][INFO] Worker {worker_id} available.")

            # get next work.
            print(f"[SS{id_:2}][INFO] Getting new port.")

            # if timeout getting port, either task is empty or just coroutine delayed.
            try:
                p: int = task_q.get(timeout=timeout)
                task_q.task_done()
            except Empty:
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
            send.put(p)

            print(f"[SS{id_:2}][INFO] Trying to serve port {p}.")
            child_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            child_sock.settimeout(timeout)

            try:
                child_sock.bind(("", p))
                child_sock.listen(1)
                child_sock.accept()

            except socket.timeout:
                print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} timeout."))
                blocked.put(p)

            except OSError:
                print(SharedData.red(f"[SS{id_:2}][Warn] Port {p} in use."))
                used.put(p)

            else:
                print(SharedData.green(f"[SS{id_:2}][Info] Port {p} is open."))

            finally:
                child_sock.close()

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


def main():

    config = SharedData.load_json_config()
    conn, addr = get_main_connection(config)

    # Send config to client.
    tcp_send(SharedData.load_config_raw(), conn)

    work = generate_queue(config.PORT_MAX)
    delimiter = config.READ_UNTIL.encode(config.ENCODING)

    start_event = threading.Event()
    stop_event = threading.Event()

    send_q = Queue()
    recv_q = Queue()

    in_use = Queue()
    failed = Queue()

    server_thread = [
        threading.Thread(target=send_task, args=[send_q, stop_event, delimiter,]),
        threading.Thread(target=recv_task, args=[recv_q, stop_event]),
    ]

    for t in server_thread:
        t.start()

    run_workers(config, work, send_q, recv_q, in_use, failed, stop_event)

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
