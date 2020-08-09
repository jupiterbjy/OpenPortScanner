from os import environ
environ['PYTHONASYNCIODEBUG'] = '1'
import asyncio
from .Shared import tcp_recv, tcp_send


async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')

    print(f"Received {message!r} from {addr!r}")

    print(f"Send: {message!r}")
    writer.write(data)
    await writer.drain()

    print("Close the connection")
    writer.close()


async def server_main():
    server = await asyncio.start_server(handler, '127.0.0.1', 39)
    async with server:
        await server.serve_forever()


async def client_main():
    return await asyncio.open_connection('127.0.0.1', 39)


if __name__ == '__main__':
    if input() == 1:
        asyncio.run(server_main())

    else:
        asyncio.run(client_main())
