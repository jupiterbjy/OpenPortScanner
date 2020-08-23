import socket
import threading
import time


def worker_thread(id_, port):
    print(f"[{id_}] Connecting {port}!")
    worker_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    worker_sock.settimeout(2)

    start = time.time()
    try:
        worker_sock.connect(("127.0.0.1", port))
    except socket.timeout:
        print(f"[{id_}] {port} Timeout! took {time.time() - start:.2f}")


def main():
    target_ports = [100*i for i in range(1, 5)]
    threads = [
        threading.Thread(target=worker_thread, args=[i, p])
        for i, p in zip(range(4), target_ports)
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
