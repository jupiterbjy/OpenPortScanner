import socket
import asyncio

from requests import get


def get_ext_ip() -> str:
    """
    return external ip of machine.
    """
    return get('https://api.ipify.org').text


async def show_progress():
    pass


async def worker_server(work_q: asyncio.Queue, timeout=400):

    # https://soooprmx.com/archives/11442
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        print(f"passing {port}")
        writer.write(port)
        writer.close()
        server.close()

        work_q.task_done()

    while True:
        port = await work_q.get()
        server = await asyncio.start_server(handler, port=port)
        print(f"Listening Port {port}")
        async with server:
            await server.start_serving()



async def server_sweep_port(socket_, max_port=66535):
    works = generate_works(max_port)

    tasks = [asyncio.create_task(worker_server(works)) for _ in range(max_port + 1)]

    socket_.listen(2)
    _, (address, port) = socket_.accept()

    print(f"Connection Successful At {address}:{port}")
    print("Starting Port Sweep.")

    tasks = [worker_server(works) for _ in range(6)]

    await asyncio.gather(*tasks)


def cli_server():
    ip = get_ext_ip()
    print(f"Connect Client to: {ip}")

    # Primary ports will be used to control, transmit results.
    server_primary = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_primary.bind((socket.gethostname(), 80))

    asyncio.run(server_sweep_port(server_primary, 300))


if __name__ == '__main__':
    cli_server()
