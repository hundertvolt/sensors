Draft for the MicroPython issue tracker (lead, 2026-11-06). Not filed: the owner decides whether and how.

---

**Title:** `async with`: a pending KeyboardInterrupt raised at the body's normal end becomes `AttributeError: 'NoneType' object has no attribute '__aexit__'`, and `__aexit__` is skipped

**Version:** v1.29.0 (also present at master `a39e77f08`, 2026-10-26). Unix port, standard variant,
`MICROPY_ASYNC_KBD_INTR=0` (the default). Any port that delivers Ctrl-C as a pending exception should be affected.

**Reproducer (deterministic):**

```python
import asyncio
import ffi

libc = ffi.open("libc.so.6")
getpid = libc.func("i", "getpid", "")
kill = libc.func("i", "kill", "ii")


class CM:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        print("__aexit__ ran")
        return False


async def main():
    async with CM():
        kill(getpid(), 2)  # SIGINT: its KeyboardInterrupt is left pending


try:
    asyncio.run(main())
except BaseException as e:
    print(type(e).__name__, e)
```

**Expected:** `__aexit__ ran`, then `KeyboardInterrupt`.
**Actual (3 of 3 runs):** `AttributeError 'NoneType' object has no attribute '__aexit__'`. `__aexit__` never runs
(an `asyncio.Lock` stays locked), and the KeyboardInterrupt is lost. A plain `with` in the same position runs
`__exit__` and delivers the KeyboardInterrupt.

With an external SIGINT at a random moment, against an `async with asyncio.Lock()` loop whose body ends in an
allocation: 947 of 3,000 interrupts were lost this way at `gc.threshold(32768)`, and 522 of 3,000 at the default.
Cancelling the task (3,000 of 3,000) or a `wait_for_ms` timeout (3,000 of 3,000) was never affected: those are thrown
at an await.

**Cause:**
- At the body's normal end, `mp_emit_bc_async_with_setup_finally()` emits `LOAD_CONST None; ROT_TWO; JUMP`
  (`py/emitbc.c:681-683`). ROT_TWO puts None into the stack slot the finally handler's saved depth points at, where the
  context manager was.
- `MP_BC_JUMP` dispatches with a pending-exception check (`py/vm.c:572-575`). The pending exception is raised there,
  while the handler is still active.
- The handler resumes with None in the context manager's slot. The exception path's `load_method __aexit__`
  (`py/compile.c:1916`) then raises the AttributeError, which replaces the original exception.

**Possible fix:** emit the JUMP first and do `LOAD_CONST None; ROT_TWO` at its target, so the context manager is still
in its slot while a pending exception can be raised.
