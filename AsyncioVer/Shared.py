from numbers import Number
# from os import environ
#
# environ["PYTHONASYNCIODEBUG"] = "1"
import asyncio

try:
    import SharedData  # only works because pycharm set working directory to project.

    print("DEBUGGING")
except ImportError:
    from os import getcwd
    from sys import path

    path.append(getcwd() + "/..")
    import SharedData


async def tcp_recv(reader: asyncio.StreamReader, delimiter: bytes = b'\n', timeout=None) -> str:
    """
    Receives string result. Handle Incomplete error on your own.
    """

    try:
        data_length: bytes = await asyncio.wait_for(
            reader.readuntil(delimiter), timeout=timeout
        )
    except TypeError:
        msg = "tcp_recv: expects"
        if not isinstance(delimiter, bytes):
            print(msg, f"<bytes> for delimiter, got {type(delimiter)} instead.")

        if not isinstance(timeout, Number) and timeout is not None:
            print(msg, f"<numbers> for delimiter, got {type(timeout)} instead.")

        raise

    # why this is ignored??? why I am getting ConnReset directly??
    except ConnectionResetError:
        print("tcp_recv: Disconnected from Server.")
        raise

    except asyncio.IncompleteReadError:
        print("tcp_recv: Incomplete read error.")
        raise

    data = await asyncio.wait_for(
        reader.readexactly(int(data_length.strip(delimiter))), timeout=timeout
    )
    return data.decode()


async def tcp_send(data, sender: asyncio.StreamWriter, delimiter: bytes = b'\n', timeout=None):
    """
    Get data, convert to str before encoding for simplicity.
    DO NOT PASS BYTES TO DATA! Or will end up receiving b'b'1231''.
    Didn't put type checking for optimization factor.
    """

    data_byte = str(data).encode()
    try:
        data_length = len(data_byte)
        sender.write(str(data_length).encode() + delimiter + data_byte)

    except TypeError:
        msg = "tcp_send: expects"
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
    print("[SEND][INFO] Started")

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
                    await tcp_send(n, s_sender, delimiter, timeout)

                except asyncio.TimeoutError:
                    # really just want to use logging and dump logs in other thread..
                    print(SharedData.red("[Send][CRIT] Connection Broken!"))
                    break
    except Exception:
        print(SharedData.bold("[SEND][CRIT] Stopping SEND!"))
        e.set()
        raise


async def recv_task(
        s_receiver: asyncio.StreamReader,
        q: asyncio.Queue,
        e: asyncio.Event,
        delimiter: bytes,
        timeout=None,
):
    print("[RECV][INFO] Started")

    try:
        while True:
            try:
                data = await tcp_recv(s_receiver, delimiter, timeout)
            except asyncio.TimeoutError:
                print('[RECV][WARN] TIMEOUT')
                if e.is_set():
                    print(SharedData.bold(f"[RECV][INFO] Event set!"))
                    return
            except asyncio.IncompleteReadError:
                print(SharedData.red(f"[RECV][CRIT] Disconnected!"))
                e.set()
                return

            else:
                await q.put(data)

    except Exception:
        print(SharedData.bold("[RECV][CRIT] Stopping SEND!"))
        e.set()
        raise
