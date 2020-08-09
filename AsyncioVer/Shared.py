from numbers import Number
from os import environ

environ["PYTHONASYNCIODEBUG"] = "1"
import asyncio

try:
    import SharedData  # only works because pycharm set working directory to project.

    print("DEBUGGING")
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


async def tcp_recv(reader: asyncio.StreamReader, delimiter: bytes, timeout=None) -> str:
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
    return data.decode()


async def tcp_send(data, sender: asyncio.StreamWriter, delimiter: bytes, timeout=None):
    data_byte = str(data).encode()
    try:
        data_length = len(data_byte)
        sender.write(str(data_length).encode() + delimiter + data_byte)
        # will default to ascii

    except TypeError:
        msg = "function 'tcp_recv' expects"
        if not isinstance(delimiter, bytes):
            print(msg, f"<bytes> for delimiter, got {type(delimiter)} instead.")

        if not isinstance(timeout, Number) and timeout is not None:
            print(msg, f"<numbers> for delimiter, got {type(timeout)} instead.")

        raise

    await asyncio.wait_for(sender.drain(), timeout=timeout)


async def send_task(
    s_sender: asyncio.StreamWriter,
    q: asyncio.Queue,
    e: asyncio.Event,
    delimiter: bytes,
    timeout=None,
):

    try:
        while True:
            try:
                n = await asyncio.wait_for(q.get(), timeout)
                q.task_done()
            except asyncio.TimeoutError:
                if e.is_set():
                    print(SharedData.bold("[SEND][INFO] Event set!"))
                    return
            else:
                try:
                    await tcp_send(str(n).encode(), s_sender, delimiter, timeout)

                except asyncio.TimeoutError:
                    # really just want to use logging and dump logs in other thread..
                    print(SharedData.red("[Send][CRIT] Connection Broken!"))
                    break
    finally:
        print(SharedData.bold("[SEND][CRIT] Stopping SEND!"))
        e.set()


async def recv_task(
    s_receiver: asyncio.StreamReader,
    q: asyncio.Queue,
    e: asyncio.Event,
    delimiter: bytes,
    timeout=None,
):

    try:
        while True:
            try:
                data = await tcp_recv(s_receiver, delimiter, timeout)
            except asyncio.TimeoutError:
                if e.is_set():
                    print(SharedData.bold(f"[RECV][INFO] Event set!"))
                    return
            else:
                await q.put(data)
    finally:
        print(SharedData.bold("[SEND][CRIT] Stopping SEND!"))
        e.set()
