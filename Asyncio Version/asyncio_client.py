import asyncio
import socket

INITIAL_PORT = 80
WORKERS = 3
EOF = b'E'
EOL = b'END'
PASS = b'P'
ENCODING = 'utf-8'


async def worker_client(id_: int, ip, work_queue: asyncio.Queue, results: asyncio.Queue):
    print(f"[C{id_}] Worker {id_} Started for {ip}")

    current_port = await work_queue.get()

    async def server(port):
        print(f"[C{id_}] Port {port} listening")
        s_reader, s_writer = await asyncio.open_connection(ip, port)
        print(f"[C{id_}] Port {port} Send")
        s_writer.write(PASS + EOL)
        await s_writer.drain()
        s_writer.close()
        data = await s_reader.readuntil(EOL)
        print(data.decode(ENCODING))

        if data == EOF:
            raise EOFError(f"Worker {id_} complete.")

    while True:
        try:
            await asyncio.wait_for(server(current_port), timeout=5)
        except asyncio.TimeoutError:
            print(f"Port {current_port} timeout!")
        else:
            await results.put(current_port)
            print(results)

        current_port = await work_queue.get()


async def main_client_run(ip):
    print(f"[C] Client Main Started")
    work_queue = asyncio.Queue()
    result = asyncio.Queue()

    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    reader, writer = await asyncio.open_connection(ip, INITIAL_PORT)

    server_hello = await reader.readuntil(EOL)
    print(f"[C] {server_hello.strip(EOL).decode(ENCODING)}")
    writer.write(b'Client Hello' + EOL)
    await writer.drain()

    tasks = []

    for i in range(WORKERS):
        tasks.append(asyncio.create_task(worker_client(i, ip, work_queue, result)))

    while True:
        data = await reader.readuntil(EOL)
        port = int(data.strip(EOL).decode(ENCODING))
        print(f"Got {port}")
        work_queue.put_nowait(port)


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
