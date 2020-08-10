import asyncio
from aioconsole import ainput
from urllib import request
from asyncio import StreamReader, StreamWriter

INITIAL_PORT = 80
ENCODING = "utf-8"
DELIMIT = b"%%"
KILL = "STOP"


# Type STOP on both side to Finish program.
# Call STOP on one side will finish send, and recv on opposing.


def get_external_ip():
    req = request.urlopen("https://api.ipify.org")
    data = req.read()
    return data.decode("utf-8")


# PROTOCOL START ---------------------------------------
# Just read until delimiter, then convert value to int.
# that's length of rest of message.

async def tcp_recv(reader: asyncio.StreamReader, delimiter: bytes) -> str:
    """
    Receives string result.
    """
    data_length: bytes = await reader.readuntil(delimiter)
    data = await reader.readexactly(int(data_length.strip(delimiter)))

    return data.decode()


async def tcp_send(data, sender: asyncio.StreamWriter, delimiter: bytes):
    """
    Get data, convert to str before encoding for simplicity.
    DO NOT PASS BYTES TO DATA! Or will end up receiving b'b'1231''.
    """
    data_byte = str(data).encode()
    data_length = len(data_byte)

    sender.write(str(data_length).encode() + delimiter + data_byte)

    await sender.drain()

# PROTOCOL END -----------------------------------------


async def send(writer: StreamWriter, e: asyncio.Event):
    while not e.is_set():
        msg = await ainput("send << ")
        await tcp_send(msg, writer, DELIMIT)
        await writer.drain()

        if KILL in msg:
            e.set()


async def read(reader: StreamReader, e: asyncio.Event):
    while not e.is_set():
        got = await tcp_recv(reader, DELIMIT)
        print(f"recv >> {got}")

        if KILL in got:
            e.set()


async def main_server():
    ip = get_external_ip()
    port = input("Enter port: ")
    event = asyncio.Event()
    print(f"Connect client to {ip}:{port}")

    async def handler(reader: StreamReader, writer: StreamWriter):
        event2 = asyncio.Event()
        sender = asyncio.create_task(send(writer, event2))
        reader = asyncio.create_task(read(reader, event2))
        print("[S] all task up and running!")
        await sender
        await reader

        writer.close()
        event.set()

    try:
        server_coroutine = await asyncio.start_server(handler, port=port)
    except OSError:
        print(f"Port {port} already in use.")
    else:
        async with server_coroutine:
            await server_coroutine.start_serving()
            await event.wait()  # Figured out that I need this to close server.
            server_coroutine.close()
            await server_coroutine.wait_closed()


async def main_client():
    raw = input("Enter Address: ")
    ip, port = raw.split(":")
    event = asyncio.Event()

    try:
        reader, writer = await asyncio.open_connection(ip, port)
    except OSError:
        print(f"Port {port} already in use.")
    else:
        s = asyncio.create_task(send(writer, event))
        r = asyncio.create_task(read(reader, event))
        await s
        await r

        writer.close()
        await writer.wait_closed()
        print("Bye!")


if __name__ == "__main__":
    import logging

    logging.getLogger("asyncio").setLevel(logging.DEBUG)

    mode = input("Type 0 for server, 1 for client.\n >>")
    if "1" in mode:
        asyncio.run(main_client(), debug=False)
    else:
        asyncio.run(main_server(), debug=False)
