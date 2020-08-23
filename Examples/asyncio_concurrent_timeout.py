import asyncio
import time


async def worker_task(id_, port):
    print(f"[{id_}] Connecting {port}!")

    start = time.time()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), timeout=2
        )
    except asyncio.TimeoutError:
        print(f"[{id_}] {port} Timeout! took {time.time() - start:.2f}")


async def main():
    target_ports = [100*i for i in range(1, 5)]
    tasks = [
        asyncio.create_task(worker_task(i, p)) for i, p in zip(range(4), target_ports)
    ]

    for t in tasks:
        await t


if __name__ == "__main__":
    asyncio.run(main())
