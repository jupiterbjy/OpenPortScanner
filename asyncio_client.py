import asyncio
import socket


INITIAL_PORT = 80
WORKERS = 3
EOF = b'E'
PASS = b'P'
ENCODING = 'utf-8'


async def worker_client(id_: int, ip, work_queue: asyncio.Queue, results: asyncio.Queue):
    print(f"[C{id_}] Worker {id_} Started for {ip}")

    while work_queue.empty():
        await asyncio.sleep(0.05)
    current_port = await work_queue.get()
    print(current_port)

    async def server(port):
        print(f"Port {port} listening")
        s_reader, s_writer = await asyncio.open_connection(ip, port)
        s_writer.write(PASS)
        s_writer.close()
        data = await s_reader.read(1024)

        if data == EOF:
            raise EOFError(f"Worker {id_} complete.")

    while True:
        try:
            await asyncio.wait_for(server(current_port), timeout=5)
        except asyncio.TimeoutError:
            print(f"Port {current_port} timeout!")
        except EOFError as err:
            print(err)
            break
        else:
            await results.put(current_port)

        current_port = await work_queue.get()


async def main_client_run(ip):
    print(f"[C] Client Main Started")
    work_queue = asyncio.Queue()
    result = asyncio.Queue()

    # not running..

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    reader, writer = await asyncio.open_connection(ip, INITIAL_PORT)

    try:
        print("[C] Connection established, waiting for hello.")
        server_hello = await reader.read(1024)

    except ConnectionResetError as err:
        print(f"[C][FATAL] Server connection halted!")  # change this to logging
        writer.close()

        # This don't print..?
        raise asyncio.CancelledError('[C][FATAL] Stopping') from err

    print(f"[C] Message from Server: {server_hello.decode(ENCODING)}")

    tasks = []
    for i in range(WORKERS):
        data = await reader.read(1024)
        port = int(data.decode(ENCODING))
        print(f"Got {port}")
        work_queue.put_nowait(port)  # I doubt..
        tasks.append(asyncio.create_task(worker_client(i, ip, work_queue, result)))

    while True:
        data = await reader.read(1024)
        port = int(data.decode(ENCODING))
        print(f"Got {port}")
        await work_queue.put(port)


def client_main():
    # ip = input("[C] input server IP: ")
    ip = "218.148.42.133"
    if client_initial_connection(ip):
        try:
            asyncio.run(main_client_run(ip))
        except asyncio.CancelledError as err:
            # This section just don't run.
            print(err)


def client_initial_connection(ip):
    print(f"[C] Waiting for server at {ip}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((ip, INITIAL_PORT))

    print("[C] Connection successful, Starting asyncio Client")
    sock.close()
    # TODO: add timeout condition
    return True


if __name__ == '__main__':
    client_main()
