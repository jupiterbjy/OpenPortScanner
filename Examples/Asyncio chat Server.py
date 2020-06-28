import asyncio
from aioconsole import ainput
from urllib import request
from asyncio import StreamReader, StreamWriter

INITIAL_PORT = 80
ENCODING = 'utf-8'


def get_external_ip():
    req = request.urlopen('https://api.ipify.org')
    data = req.read()
    return data.decode('utf-8')


async def send(writer: StreamWriter):
    while True:
        msg = await ainput("send << ")
        writer.write(msg.encode(ENCODING))


async def read(reader: StreamReader):
    while True:
        got = await reader.read(1024)
        print(f"recv >> {got.decode(ENCODING)}")


async def main_server():
    ip = get_external_ip()
    port = input("Enter port: ")
    print(f"Connect client to {ip}:{port}")

    async def handler(reader: StreamReader, writer: StreamWriter):
        tasks = [asyncio.create_task(send(writer)),
                 asyncio.create_task(read(reader))]

    try:
        server_coroutine = await asyncio.start_server(handler, port=port)
    except OSError:
        print(f"Port {port} already in use.")
    else:
        async with server_coroutine:
            await server_coroutine.serve_forever()
            # await server_coroutine.start_serving()


async def main_client():
    raw = input("Enter Address: ")
    ip, port = raw.split(':')

    try:
        reader, writer = await asyncio.open_connection(ip, port)
    except OSError:
        print(f"Port {port} already in use.")
    else:
        asyncio.create_task(send(writer))
        asyncio.create_task(read(reader))


if __name__ == '__main__':
    mode = input("Type 0 for server, 1 for client.\n >>")
    if '1' in mode:
        asyncio.run(main_client())
    else:
        asyncio.run(main_server())
