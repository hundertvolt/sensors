# MicroPython asyncio: a second await of an ended task can raise `None` (note, no issue filed)

Pinned v1.29.0 `extmod/asyncio/core.py`, `run_until_complete()`; identical on upstream master (fetched 2026-10-07).

## Mechanism
1. A detached task raises. Its first run ends in `except excs_all as er:` with `t.state is True` and nobody awaiting,
   so `t.state = None` and the task is pushed back on `_task_queue` "to handle the uncaught exception if no other task
   retrieves the exception in the meantime"; `t.data = er` (the exception).
2. Before that queued entry is popped, another task awaits it. `extmod/modasyncio.c` `task_getiter()` sees
   `TASK_IS_DONE` and sets `state = TASK_STATE_DONE_WAS_WAITED_ON` (False); `task_iternext()` raises `self->data`
   (the exception). The awaiter sees the exception correctly.
3. The queued entry is popped: `exc = t.data` (the exception), then `t.data = None; t.coro.throw(exc)`. The finished
   coroutine raises again, landing in `except excs_all as er:`. `assert t.data is None` holds. `t.state` is False, so
   the `if t.state:` block, the only place that does `t.data = er`, is skipped, and so is `elif t.state is None:`
   (the handler path, which would restore `t.data = exc`). The task is left done with `t.data = None`.
4. Any later await: `task_iternext()` runs `nlr_raise(self->data)`, i.e. `nlr_raise(mp_const_none)`. The Unix port
   segfaults; on rp2 it is undefined (a non-exception object propagated as an exception).

## Minimal reproduction (Unix port, v1.29.0, default handler or any handler)
```python
import asyncio
ev = asyncio.Event()
async def dies():
    await ev.wait()
    raise RuntimeError("boom")
async def main():
    t = asyncio.create_task(dies())
    await asyncio.sleep(0)
    ev.set()
    await asyncio.sleep(0)          # t has died; its handler entry is queued, not yet run
    try:
        await t                     # first await: raises RuntimeError, state -> False
    except Exception:
        pass
    for _ in range(3):
        await asyncio.sleep(0)      # the queued entry runs: t.data = None, handler skipped
    await t                         # nlr_raise(None): segfault
asyncio.run(main())
```
With one yield before the first await (instead of zero or two-plus) it segfaults; with two or more yields the handler
runs first (restoring `t.data`) and both awaits raise the RuntimeError.

## Possible upstream fix
In the `except excs_all as er:` path, keep the exception when the task is already done and was awaited: e.g. set
`t.data = er` (or restore `exc`) outside the `if t.state:` block, or make `task_iternext()` refuse to raise a
non-exception `data`.

## Where it bit this repo
`SystemService._supervise()`'s escalating pass broke out before replacing the dead task, so later passes awaited the
same ended task again; fixed on `audit/u11-handler` by retiring the slot right after `_log_dead_task()`. Test cleanups
that cancel-and-await every started task skip done ones. SPECIFICATION.md F.1 and F.9 record the fact and workaround.
