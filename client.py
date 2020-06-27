import socket
import asyncio
from server import generate_works, get_ext_ip

# find port with this Power-shell script
# Get-Process -Id (Get-NetTCPConnection -LocalPort portNumber).OwningProcess


async def worker_client(work_q, result_q, primary_socket, ip, timeout=4):
    while True:
        port = await work_q.get()

        fut = asyncio.open_connection(ip, port, ssl=False)
        try:
            result = await asyncio.wait_for(fut, timeout=timeout) is not None
        except asyncio.TimeoutError:
            result = False

        print(port, result)
        await result_q.put((port, result))
        work_q.task_done()


async def client_sweep_port(ip, p_socket, max_port=65535):
    works = generate_works(max_port)
    results = asyncio.Queue()

    tasks = []
    for _ in range(10):
        tasks.append(asyncio.create_task(worker_client(works, results, p_socket, ip)))

    await works.join()


def cli_main():
    """
    Assuming at least 80 port is open.
    """
    print("Started")
    ip = "218.148.42.133"
    client_primary = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_primary.connect((ip, 80))

    print("Handshake successful, starting sweep")
    asyncio.run(client_sweep_port(ip, client_primary))


if __name__ == '__main__':
    cli_main()
