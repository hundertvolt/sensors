"""C-stack use along a nested await chain in a task (REPORT 7 item 1, the product's 28 levels): at each depth the
stack in use at the innermost await on entry and after a real suspension, the plain-call headroom left below it, and
the depth where the chain ends in RuntimeError. Bare image, RAM only; SUM lines summarise."""

import asyncio
import micropython

OUT = [0, 0, 0, ""]


def _plain(k: int) -> int:
    try:
        return _plain(k + 1)
    except RuntimeError:
        return k


async def level(n: int) -> None:
    if n == 0:
        OUT[0] = micropython.stack_use()
        await asyncio.sleep_ms(0)  # resumed by the scheduler through every level, as a product task is
        OUT[1] = micropython.stack_use()
        OUT[2] = _plain(0)
        return
    await level(n - 1)


async def top(n: int) -> None:
    try:
        await level(n)
    except RuntimeError as e:
        OUT[3] = repr(e)


async def main() -> None:
    print("SUM cstack top_level_use=%d plain_headroom_in_task=%d" % (micropython.stack_use(), _plain(0)))
    first = last_ok = last_use = 0
    for d in range(1, 121):
        OUT[0] = OUT[1] = OUT[2] = 0
        OUT[3] = ""
        await asyncio.create_task(top(d))
        if OUT[3]:
            print("SUM cstack_await max_ok_depth=%d failed_at=%d error=%s" % (last_ok, d, OUT[3]))
            break
        if d == 1:
            first = OUT[1]
        last_ok, last_use = d, OUT[1]
        if d in (1, 2, 5, 10, 15, 20, 24, 26, 28, 30, 35, 40, 50) or d % 10 == 0:
            print("SUM cstack_await depth=%d entry_use=%d resumed_use=%d plain_headroom=%d" % (d, OUT[0], OUT[1], OUT[2]))
    if last_ok > 1:
        print("SUM cstack_await per_level_bytes=%d (resumed use, depth 1 to %d)" % ((last_use - first) // (last_ok - 1), last_ok))


asyncio.run(main())
print("DONE=1")
