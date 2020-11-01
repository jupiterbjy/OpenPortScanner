import trio


# HELP - Does socket transmission mixes up when client sends are
# happened to be delivered simultaneously to the server?
# Do I even need things like asyncio .readuntil()?


def encoding_protocol(data, delimiter: bytes) -> bytes:
    """
    Get data, convert to bytes. Pads byte length at front, separated by delimiter.
    """
    data_byte: bytes = str(data).encode()
    data_length: bytes = str(len(data_byte)).encode()

    return data_length + delimiter + data_byte


def decoding_protocol(raw_data, delimiter: bytes):
    pass


async def send_task(stream: trio.SocketStream, recv_c: trio.MemoryReceiveChannel, timeout: int):
    print("[SEND][INFO] Started")

    async for item in recv_c:
        if item is None:
            print("[SEND][INFO] Shutting down!")
            break

        try:
            with trio.move_on_after(timeout):
                await stream.send_all(str(item).encode())
                # await stream.send_all(encoding_protocol(item, delimiter))

        except trio.Cancelled:
            print("[SEND][WARN] Timeout on send_task")


async def recv_task(stream: trio.SocketStream, send_c: trio.MemorySendChannel):
    print("[RECV][INFO] Started")
    async for data in stream:
        try:
            decoded = data.decode()
        except AttributeError:
            print(f"[RECV][WARN] Received wrong data {data}")
        else:
            await send_c.send(decoded)
