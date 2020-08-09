from os import environ
environ['PYTHONASYNCIODEBUG'] = '1'
import asyncio
from numbers import Number


async def tcp_recv(reader: asyncio.StreamReader, delimiter: bytes, timeout=None) -> bytes:
    try:
        data_length = await asyncio.wait_for(
            await reader.readuntil(delimiter), timeout=timeout
        )
    except TypeError:
        msg = "function 'tcp_recv' expects"
        if not isinstance(delimiter, bytes):
            print(msg, f"<bytes> for delimiter, got {type(delimiter)} instead.")

        if not isinstance(timeout, Number) and timeout is not None:
            print(msg, f"<numbers> for delimiter, got {type(timeout)} instead.")

        raise

    data = await asyncio.wait_for(reader.readexactly(int(data_length)), timeout=timeout)
    return data


async def tcp_send(data: bytes, sender: asyncio.StreamWriter, delimiter: bytes, timeout=None):
    try:
        data_length = len(data)
        sender.write(str(data_length).encode() + delimiter + data)  # will default to ascii

    except TypeError:
        msg = "function 'tcp_recv' expects"
        if not isinstance(delimiter, bytes):
            print(msg, f"<bytes> for delimiter, got {type(delimiter)} instead.")

        if not isinstance(timeout, Number) and timeout is not None:
            print(msg, f"<numbers> for delimiter, got {type(timeout)} instead.")

        raise

    await asyncio.wait_for(sender.drain(), timeout=timeout)


