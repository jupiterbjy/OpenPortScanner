import asyncio
import socket
from urllib import request
from asyncio import StreamWriter, StreamReader


INITIAL_PORT = 80
WORKERS = 3
EOF = b'E'
PASS = b'P'
ENCODING = 'utf-8'


class Success(Exception):
    pass


async def worker(id_: int, port_queue: asyncio.Queue, pass_queue: asyncio.Queue):
    print(f"[S{id_}] Worker {id_} Started")
    current_port = await port_queue.get()
    await pass_queue.put(current_port)

    async def handler(reader: StreamReader, writer: StreamWriter):
        nonlocal current_port

        # TODO: add echo to port it's hosting on
        # Do i need to check if data is same? Client only sends PASS.
        data = await reader.readuntil(EOL)
        print(data.decode(ENCODING))

        if port_queue.empty():
            writer.write(EOF + EOL)
            await writer.drain()
            writer.close()
            raise EOFError(f"[S{id_}] Worker {id_} complete.")

        writer.write(PASS + EOL)
        await writer.drain()
        writer.close()

        raise Success

    async def server(port):
        server_coroutine = await asyncio.start_server(handler, port=port)

        async with server_coroutine:
            print(f"[S{id_}]Port {current_port} hosting")
            await server_coroutine.serve_forever()

    while True:
        try:
            await asyncio.wait_for(server(current_port), timeout=5)

        except asyncio.TimeoutError:
            print(f"[S{id_}] port {current_port} timeout!")

        except EOFError as err:
            print(f"[S{id_}] {err}")
            break

        current_port = await port_queue.get()
        await pass_queue.put(current_port)


async def main_server_run():
    print(f"[S] Async Server Started")
    pass_queue = asyncio.Queue()
    port_queue = await works(max_size=100)

    # tasks = [worker(i, port_queue, pass_queue) for i in range(WORKERS)]
    tasks = []
    for i in range(WORKERS):
        tasks.append(asyncio.create_task(worker(i, port_queue, pass_queue)))

    async def main_handler(reader: StreamReader, writer: StreamWriter):
        writer.write(b'Server Hello' + EOL)
        await writer.drain()
        recv = await reader.readuntil(EOL)
        print(f"[S] {recv.strip(EOL).decode(ENCODING)}")

        while True:
            if not pass_queue.empty():
                next_port = await pass_queue.get()

                writer.write(str(next_port).encode(ENCODING) + EOL)
                await writer.drain()
                print(f"[S] Sending Port {next_port}")

    try:
        server_coroutine = await asyncio.start_server(main_handler, port=80)
    except OSError:
        print(f"[S][FATAL] Port {INITIAL_PORT} in use. Cannot Start.")
    else:
        async with server_coroutine:
            await server_coroutine.serve_forever()


async def works(max_size=66535, exclude=(80, 443)):
    work = asyncio.Queue()
    for port in range(max_size):
        if port + 1 in exclude:
            continue
        await work.put(port + 1)

    return work


async def handler_new(reader: StreamReader, writer: StreamWriter):
    while True:
        writer.write()


def server_main():
    ip = get_external_ip()
    work = works(30)
    loop = asyncio.get_event_loop()
    server = loop.run_until_complete(main_server_run())

    if server_initial_connection(ip):
        loop.run(main_server_run())
    else:
        print(f"[S][FATAL] Server stopped.")


def server_initial_connection(ip):
    print(f"[S] Server started at {ip}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((socket.gethostname(), INITIAL_PORT))
    except OSError:
        print(f"[S][FATAL] Port 80 already in use!")
        return False

    sock.listen(2)
    client_socket, (client_ip, client_port) = sock.accept()

    print(f"[S] Connection from {client_ip}:{client_port}")
    print("[S] Connection successful, Starting asyncio Server")

    sock.close()
    return True


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


if __name__ == '__main__':
    server_main()
