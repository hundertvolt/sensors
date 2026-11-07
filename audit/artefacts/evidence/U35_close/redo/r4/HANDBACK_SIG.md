SIG hand-back, written by the agent (Fri Nov  6 05:34 UTC 2026). Replaces the 05:04 one.

**Cause: a defect in MicroPython itself, present in v1.29.0 and unchanged on the local `origin/master` checkout (`a39e77f08`, 2026-10-26).** The defect: a pending KeyboardInterrupt raised at the normal end of an `async with` body is replaced by `AttributeError: 'NoneType' object has no attribute '__aexit__'`. Its `__aexit__` never runs, so the lock stays held. In CI this happened in `_store_scd` (`src/asy_scd30_driver.py:508-512`). The SCD30 read task died, the event loop ran on, and that is why the twin "ignored" its SIGINT. No code changed, nothing committed. `S/wt-sig` was recreated at `f509c906`.

1. **Mechanism** (`S/tc-int/micropython`, v1.29.0):
   - SETUP_FINALLY is pushed with the context manager on top of the stack (`py/compile.c:1893`; it saves that stack depth, `py/vm.c:122-128`).
   - At the body's normal end the emitter writes `LOAD_CONST None; ROT_TWO; JUMP l_aexit_no_exc` (`py/emitbc.c:681-683`). The finally label comes only after that (`:686`).
   - ROT_TWO (`vm.c:557-561`) writes None into the slot the saved depth points at.
   - The JUMP checks for pending exceptions (`vm.c:572-575`, then `:1341-1371`), and that check raises the scheduler's pending KeyboardInterrupt (`py/scheduler.c:238`).
   - The recorded instruction position is the JUMP itself (`vm.c:222`, `:242/249`). That lies below the handler, so the handler is kept (`vm.c:1464`) and resumes with the saved stack depth plus the exception (`:1478-1484`). It therefore finds None where the context manager was.
   - The exception-path code then loads `__aexit__` from None (`compile.c:1913-1916`), raising the AttributeError. That error is raised past the handler, so it propagates, and the KeyboardInterrupt is lost.
   - Plain `with` is not affected: there, `LOAD_CONST None` falls straight into WITH_CLEANUP with no jump (`emitbc.c:666-670`).
2. **Reproducer, standard Unix build, not the twin** (`S/sig/repro_aexit.py` with the driver `S/sig/drive_sigint.py`): an `async with asyncio.Lock()` loop whose body ends in an allocation, and an outside driver that sends one SIGINT per cycle after a random 0-3 ms delay.
   - At gc.threshold 32768: 974 of 3,000 SIGINTs came out as this AttributeError, the rest as plain KeyboardInterrupts.
   - At -1: 542 of 3,000.
   - Control: with a branch after the allocation, so the body has its own last pending-exception check, it drops to 4 and 28. That confirms the window is the stretch from the body's last check to that JUMP. The 32768 stage widens it because a collection triggered by the body's allocation sits inside it.
3. **Product question: a CancelledError or wait_for timeout is never lost this way.**
   - Measured: 3,000 of 3,000 cancels came out as CancelledError and 3,000 of 3,000 `wait_for_ms` timeouts as TimeoutError, at both GC stages, with no lock left held.
   - Why: a cancel is thrown only where a task resumes at an await (`extmod/modasyncio.c:236`, `extmod/asyncio/core.py:193`), and the three-instruction window contains no await.
   - Which `src/` sites are exposed: to an asynchronous exception, all of the about 100 `async with` sites, widest where the body ends in an allocation with no branch after it (as in `_store_scd`). To cancellation and timeouts, none.
   - On rp2 the only asynchronous exception is a Ctrl-C on the console: USB CDC (`shared/tinyusb/mp_usbd_cdc.c`; the UART REPL is off, `ports/rp2/mpconfigport.h:49`). So the device-side effect is a lost console interrupt and a module lock left held, which the watchdog ends.
4. **Fix: in MicroPython itself, so not patched, and I stopped there.**
   - `toolchain/micropython_overrides.py` cannot carry it. Its mechanism only sets make variables and config macros through a variant directory, and never edits the checkout. No macro changes this emitted sequence, and `SELECTIVE_EXC_IP` is a plain `#define` in `vm.c`. A fix needs a source change in `py/emitbc.c`.
   - What an upstream report would say: title "async with: KeyboardInterrupt at the body's end becomes AttributeError ('NoneType' … `__aexit__`), `__aexit__` skipped"; versions v1.29.0 and master; the mechanism above; the reproducer and its rates.
   - Proposed upstream fix: emit the JUMP first and do `LOAD_CONST None; ROT_TWO` at its target, under a new label ahead of `l_aexit_no_exc`, so the context manager stays in its slot while a pending exception can still be raised.
5. **For the lead or owner to decide; not done, as briefed for a MicroPython cause:** until upstream changes, any SIGINT shutdown can lose its interrupt this way. The two hits both came in the hung-shutdown scenario, whose otherwise idle loop leaves the periodic sensor bodies as the likely landing places. The one twin-side remedy that does not weaken the scenario's check is the in-band stop. With the cause now known, it would no longer hide anything: SIGINT stays covered by the CI suite's own SIGINT runs. Its test would be a twin started with SIGINT blocked, red first.

Runs this round: three light ones, all unshare'd at nice 19 (`sig_rep0`, `sig_rep1`, `sig_rep2`; under 25 s each). No heavy slot was used.
nothing of mine is running
