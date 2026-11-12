# Hand-back: the hung-shutdown root-cause agent (as received)

**I could not establish the mechanism.** The failure did not reproduce in about 1,900 deliberate SIGINTs. The code audit found
no place in the twin where a KeyboardInterrupt (KI) can be swallowed quietly. Nothing in the repo was changed.

1. The override is in today's binary (verified): `unix_mphal.o` (built 20:03:23, linked 20:03:24, gate started 20:19)
   disassembles to the deferred handler (compare pending against the kbd exception, `exit(1)`, else tail-call
   `mp_sched_keyboard_interrupt`; no `sigprocmask`/`nlr_jump`); the variant header forces `MICROPY_ASYNC_KBD_INTR (0)`; one
   SIGINT during a 4.2 s `sum()` lets the sum finish and raises the KI after it (rc 130); two SIGINTs give rc 1, no output.
2. What the log shows (inference): `count=2` is printed only by `machine.WDT._countdown`, an asyncio task
   (`digital_twin/machine.py:1514-1530`); the harness sends SIGINT about 50 ms after `count=1` shows
   (`_twin_process.py:319-334`), so the event loop kept running about 8 s after SIGINT. No `mem_info`, shutdown or
   "interrupted" line: the KI never reached `__main__`'s handler (`run_generic_integration.py:879`). The 110.7 s total fits the
   steps' isolated 12.2-14.3 s each.
3. Ruled out: Python handlers (an AST audit of src/, ext/, digital_twin/, generated_src and the frozen `extmod/asyncio`: only two
   BaseException/bare handlers that do not re-raise, neither able to see a KI here; `funcs._run`'s try body has no pending-check
   opcode, per `mpy-tool`); C handlers (re-raise, or print through `mp_call_function_1_protected`, and nothing was printed; no
   user `__del__`, no `micropython.schedule`/`kbd_intr`/`new_event_loop`; `mp_pending_exception` cleared only by
   `mp_handle_pending`); a parked or replaced KI (every `finally`-with-await site inactive in the S5reset state); U28's changes
   (comments, noqa, type-ignore and one fault-message choice in `asy_uart_comm._listen_unlocked`).
4. The stage: no evidence it matters; one sample; 0 of 300 KIs swallowed at -1 and 0 of 1,600 at 32768.
5. Classification: undetermined; not attributable by evidence to src/, the harness or the toolchain. Left: a runtime- or
   environment-level cause (unverified), e.g. SIGINT blocked or pending at kernel level, or MicroPython undefined behaviour
   (one example: `extmod/modselect.c:231-237`, an unhandled exception during `register()` leaving a poll entry unpopulated).
   The gate differed from these runs: 4 lanes in one netns (one twin holding NTP :123 for the others, :53 shared), heavy I/O
   (wa up to 38 %, disk 85 % full) and CPU load; only the :123/:53 traffic was replayed.

Side finding: about 92 % of KIs land in `asyncio/event.py` `ThreadSafeFlag.ioctl`: the neopixel overlay's flag puts a non-fd
object in asyncio's own poller, so the idle loop is a 1 ms modselect poll calling a Python ioctl.

Proposed: (a) `_proc_diagnostic_fields` adds SigBlk/SigPnd/ShdPnd/SigCgt; (b) before SIGKILL, a second SIGINT, its outcome
recorded (exit 1 within ms: the first KI was never consumed; a clean line: raised and absorbed; still running: SIGINT not
handled); (c) a runner test flag capturing the static KeyboardInterrupt object at start and printing its traceback on a stdin
trigger; (d) optional: stop scenario twins in-band through `--stop-file`, SIGINT as the fallback, seen failing first with a
twin spawned with SIGINT blocked; not without (a)-(c), which would hide the cause.

Runs (all in `unshare -n`, one twin at a time, every run rc 0): the SIGINT probe; `run1` 20 S5reset hangs at 32768, 20/20 clean
in 0.11 s; `run2` 25 with SIGINT sent in State R, 25/25 clean; `run3` 30 under the diagnostic runner, 30/30 escaped; `run4` the
real scenario alone at 32768, PASSED in 111.6 s; storms with each KI logged at its landing site: `storm0` 20 at 32768,
`storm1` 600 at 32768, `storm2` 600 at 32768 SIGSTOP-gated, `storm3` 300 at -1, `storm4` 300 at 32768 with NTP/DNS loopback
traffic: 0 swallowed, 0 silent.

Sources: micropython#19718 (a `new_event_loop` hang; no such call here), micropython#11682 (a bare `except` swallowing Ctrl-C;
not present).
