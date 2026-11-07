import asyncio
from _async_harness import _await_each


async def fails():
    raise OSError(5)


async def main():
    t = asyncio.create_task(fails())
    await asyncio.sleep(0)  # t fails with no waiter: the loop queues it for its exception handler
    try:
        await t  # another task retrieves the failure first
    except OSError:
        pass
    await asyncio.sleep(0)  # the queued entry runs and clears t.data
    print("STATE", t.done(), t.state, t.data)
    errors = []
    await _await_each([t], errors)
    print("SURVIVED", errors)


asyncio.run(main())
