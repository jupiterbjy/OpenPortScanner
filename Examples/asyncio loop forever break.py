import asyncio
import itertools
from sys import stdout


async def spiny_spin():
    # r"\-/|" works while r"-/|\" fails.
    # seems like \" can't be helped with raw.
    write, flush = stdout.write, stdout.flush

    for s in itertools.cycle(r"\-/|"):
        write(s)
        flush()
        try:
            await asyncio.sleep(0.1)
            # set this value lower in Terminals, pycharm 'Run' updates too slowly.
        except asyncio.CancelledError:
            break

        write('\x08')


def main():
    loop = asyncio.get_event_loop()
    loop.create_task(spiny_spin())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('Key Interrupted!')
        # pycharm debug can't send ctrl+c, it just copies!


if __name__ == '__main__':
    main()
