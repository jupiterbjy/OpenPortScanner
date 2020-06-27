import socket
import asyncio
from server import generate_works, get_ext_ip

# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort portNumber).OwningProcess


async def worker_client(result_q, primary, ip, timeout=4):
    port = None

    async def connect():
        nonlocal port

        try:
            reader: asyncio.StreamReader
            writer: asyncio.StreamWriter
            reader, writer = await asyncio.open_connection(ip, port, ssl=False)

        except (TypeError, OSError):
            # using this method to skip 'if' checking
            # checking if port is none is waste of time.

            reader, writer = await asyncio.open_connection(ip, primary, ssl=False)

        data: bytes = await reader.read(1024)
        print(data)
        port = int(data.decode())
        writer.close()
        # if not port:
        # using 0 to mean end of task.

    while True:

        try:
            result = await asyncio.wait_for(connect(), timeout=timeout) is not None
        except asyncio.TimeoutError:
            result = False

        print(port, result)
        await result_q.put((port, result))


async def client_sweep_port(ip, socket_primary, max_port=65535):
    results = asyncio.Queue()

    tasks = [worker_client(results, p + 1, ip) for p in range(6)]

    await asyncio.gather(*tasks)


def cli_main():
    """
    Assuming at least 80 port is open.
    """
    print("Started")
    ip = "218.148.42.133"
    client_primary = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_primary.connect((ip, 80))

    print("Handshake successful, starting sweep")
    asyncio.run(client_sweep_port(ip, client_primary, 300))


if __name__ == '__main__':
    cli_main()
