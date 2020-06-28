import asyncio

# TEST THIS BLOCK BY BLOCK IN CONSOLE SESSION TO SEE YOURSELF!
# Note to myself compiled with what I've found when doing this project.

# ┌─────────────────────────────────────────────┐
# │Getting Queue Object for demonstration       │
# └─────────────────────────────────────────────┘
loop = asyncio.get_event_loop()


async def get_que():
    # Queue MUST be created inside event loop
    # or get 'attached to different loop' error.
    work = asyncio.Queue()

    # got hang when returned none in REPL..
    # Can't reproduce it.
    return work

q = loop.run_until_complete(get_que())

# ──────────────────────────────────────────────
