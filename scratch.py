import asyncio
from urllib import request
from asyncio import StreamWriter, StreamReader


ENCODING = 'utf-8' \
           ''

class Break(Exception):
    pass


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


async def works(max_size=66535, exclude=(80, 443)) -> asyncio.Queue:
    work = asyncio.Queue()
    for port in range(max_size):
        if port + 1 in exclude:
            continue
        await work.put(port + 1)

    return work


def server_main():

    loop = asyncio.get_event_loop()
    ip = get_external_ip()
    primary_port = 80

    work_queue: asyncio.Queue = loop.run_until_complete(works(20))

    async def handle_workers(reader: StreamReader, writer: StreamWriter):
        while True:
            work = await work_queue.get()
            writer.write(str(work).encode(ENCODING))
            await writer.drain()
            # Send port to test to client first, then create new server.
            child_server_coro = asyncio.start_server()
            loop.run_until_complete()

    # loop parameter deprecated, but using for now.
    server_coro = asyncio.start_server(handle_workers, port=primary_port, loop=loop)

    server = loop.run_until_complete(server_coro)
    print(f"[S] Started at {ip}:{primary_port}")

    try:
        loop.run_forever()
    except Break:
        # TODO: change these later
        print('Break!')
    except KeyboardInterrupt:
        print('ctrl + c!')

    print('[S] Server Shutdown.')
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()


if __name__ == '__main__':
    server_main()
