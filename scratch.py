import asyncio
from urllib import request
from asyncio import StreamWriter, StreamReader

ENCODING = 'utf-8'


class Break(Exception):
    # using this as ejection sit for debugging, or else
    pass


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


def works(max_size=66535, exclude=(80, 443)) -> asyncio.Queue:
    # RUN THIS INSIDE EVENT LOOP

    work = asyncio.Queue()
    for port in range(max_size):
        if port + 1 in exclude:
            continue
        work.put_nowait(port + 1)

    return work


def micro_handler(reader, writer, port, result_queue):
    reader: StreamReader
    writer: StreamWriter
    result_queue: asyncio.Queue

    loop = asyncio.get_event_loop()


async def handler(reader, writer, ports_queue, result_queue):
    reader: StreamReader
    writer: StreamWriter
    ports_queue: asyncio.Queue
    result_queue: asyncio.Queue

    # PEP don't like semicolons. I, for one, believe in PEP.

    while True:
        work = await ports_queue.get()
        writer.write(str(work).encode(ENCODING))
        await writer.drain()

        # Send port to client first, if they get,
        # , then create new server.

        child_server_coro = await asyncio.start_server()
        loop = asyncio.get_event_loop()
        loop.run_until_complete()

        # CLIENT CODE: MOVE LATER, GOT NO TIME TO MEMO THIS.
        fut = asyncio.open_connection()
        try:
            r, w = asyncio.wait_for(fut, timeout=)


def server_main():
    # loop parameter deprecated, but using for now.
    # Can't find example without those.

    loop = asyncio.get_event_loop()
    ip = get_external_ip()
    primary_port = 80
    work_q = works(20)
    result_q = asyncio.Queue()

    # For some reason I get coroutine object from lambda.
    # ref: stackoverflow.com/questions/50678184
    server_coro = asyncio.start_server(lambda r, w: handler(r, w, work_q, result_q),
                                       port=primary_port, loop=loop)

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
