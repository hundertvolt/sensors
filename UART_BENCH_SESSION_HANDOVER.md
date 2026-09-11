# UART crossover tiers — hardware session handover (2026-09-11)

**Temporary file.** Delete it once the open item below is closed and its content has moved into
`SPECIFICATION.md`/`BACKLOG.md`/`tests_hardware/README.md` (most of it already lives there; this
file exists so the *next* session can resume mid-investigation without re-deriving anything).

**This branch is pushed with one known-failing test.** That was the project owner's explicit
direction: stop, write everything down, push immediately, do not wait for tests to pass. Do not
read the red test as an accident.

---

## 1. What was done, and what is verified

First real-hardware run of the H3/H4 UART tiers, on the dev bench, with the owner's go-ahead given
in-session. Only the UART tests were run — the owner asked explicitly for the UART crossover link
tests alone, not a full tier sweep.

| Check | Result |
|---|---|
| `tests_hardware/flash/test_uart_crossover.py` | **2/2 pass** (real GP0↔GP9 / GP1↔GP8 jumper) |
| `tests_hardware/bench/test_uart_link_under_api_load.py` | **2/2 pass** (full HTTP stack over `br0`) |
| `scripts/lint.sh` | clean |
| `scripts/typecheck.sh` (all three passes) | clean |
| `scripts/test.sh` | **59/60 files** — see §4 |

The board arrived carrying a **pre-UART `dev` build**: `asy_uart_comm` was simply absent, so neither
tier could run at all. Rebuilt with `uv run scripts/build_firmware.py dev` and flashed with
`picotool load -x -v`. Neither tier's skip guard fired afterwards, which independently confirms
`asy_uart_comm` does reach a dev firmware behind `sensortask_dev` (closing the doubt recorded in
BACKLOG.md's auto-builder entry).

## 2. Findings, all reproduced on real hardware

### 2.1 The driver blocked the asyncio loop on every frame (fixed)

Owner's standing rule, given in this session: `asy_uart_driver.py`/`asy_uart_comm.py` may time out
and handle it, but **may never block the asyncio loop, not even in a wait state**. It was being
violated on the hot path.

`machine.UART.read()/readinto()` wait out `timeout_char` for every byte asked for that has not
arrived, inside `mp_event_handle_nowait()` — which runs scheduled callbacks but never yields to
asyncio. `POLLIN` fires on the *first* byte, so "read the whole frame after poll" blocks for the
frame's entire remaining wire time.

Full mechanism, all measurements and the two-part fix: **`SPECIFICATION.md` Part F.5.8**. Changelog
entry: **`UART_C_PORT_CHANGELOG.md` B24** (Class B). Standing rule: **`CLAUDE.md` hard rules**.

The one thing worth repeating here, because it is the trap: **clamping reads to `uart.any()` alone
made it worse, not better** (4.4ms → 14.6ms). `ready()` returns `True` with no `await` at all while
`POLLIN` stands, so the block simply moved into a Python loop one level up. The yield between rounds
is the half that actually fixes it. A future session tempted to "simplify" the fix by dropping
`_yield_between_rounds()` will silently reintroduce the defect, and **no test in `tests/` will catch
it** (see §2.4).

### 2.2 Device scripts died by watchdog instead of reporting (fixed)

Both `tests_hardware/device_scripts/uart_crossover_*.py` armed an 8s `machine.WDT` and joined their
responder task with `asyncio.wait_for(listener, 10/12)`. That join can never complete on its own
when the frame never arrived (`uart_listen()` parks in its one legitimate unbounded read), so the
watchdog fired first: an `mpremote` I/O error, no `RESULT:` line, no diagnosis. Fixed with bounded,
watchdog-feeding joins plus `UART_Comm.clear()` as the documented unstick. Detail in
`tests_hardware/README.md`.

### 2.3 A UART re-inited on other pins poisons that peripheral (documented, not fixed)

`deinit()` does not release the GPIO function select. Detail in `tests_hardware/README.md`. This is
a hardware property, not a defect to fix; it is written down because it cost real time here — it
made every subsequent crossover run fail deterministically, across soft resets, until a hard reset.

### 2.4 The fakes cannot catch a regression of §2.1 (open, logged in BACKLOG.md)

`tests/machine.py`'s and `digital_twin/machine.py`'s `UART.readinto()` return what is queued and
never wait — they model a non-blocking read the real peripheral does not provide. Both now expose
`any()` so the fixed code is exercised, but a regression would pass both tiers silently.

## 3. How the measurements were taken (reproduce before trusting new numbers)

Two of the three measurement approaches tried here were **unsound**, and both looked plausible:

- A `Window` context manager that read the peak *immediately* after the operation reported **0 µs
  for everything** — the probe task records a gap only when it next runs, so it must be given a turn
  (`await asyncio.sleep_ms(0)` a few times) before the peak is read.
- An `asyncio` loop-latency probe **cannot distinguish "the loop is idle waiting on a timer" from
  "the loop is blocked"**. The driver's own cooperative `sleep_ms(poll_wait_ms)` waits put both at
  ~2ms, which reads as a 2ms "stall" that is not a stall at all.

The sound measurement is **timing the C calls directly** with `time.ticks_us()` around
`uart.readinto()` / `uart.write()` / `uart.any()`, which is what Part F.5.8's table reports. Also
pin GC (`gc.threshold(-1)`) so a collection pause is never misattributed, and print nothing inside a
measurement window — a `print()` over USB CDC is itself a synchronous write.

Scratch measurement scripts from this session were left in the session scratchpad and are **not**
committed (they are throwaway diagnostics, not tests): `measure_block.py`, `measure_loop_stall.py`,
`measure_attributed.py`, `bisect_stall.py`, `bisect2.py`, `decompose.py`, `control.py`,
`raw_calls.py`, `ab_clamp.py`, `negative_control.py`. Any of them is a few minutes to rewrite from
Part F.5.8's description; the `ab_clamp.py` shape is the most useful one (defeat `_buffered()` at
runtime via `asy_uart_driver.UART._buffered = staticmethod(lambda uart, want: want)` to A/B the fix
on a single firmware).

## 4. THE OPEN ITEM — where the next session picks up

`scripts/test.sh` reports **59/60 files**. The failure is:

```
tests/test_digital_twin_run_dev_integration.py
  FAIL test_main_runs_a_tiny_bounded_soak_with_an_injected_fault_and_returns_a_clean_summary
  TimeoutError (the test's own run_timed(..., timeout_s=60.0))
```

**This is caused by this branch's driver change. It is not a pre-existing flake.** Investigation got
this far before the session was stopped — none of it needs redoing:

1. **Bisected to the driver, not the fakes.** `git stash` → 17/17 pass. Reverting only
   `src/asy_uart_driver.py` while keeping `digital_twin/machine.py`'s new `any()` → 17/17 pass. So
   the twin's `any()` is not the cause.
2. **Bisected within the driver to the clamp, not the yield.** Disabling only the
   `_yield_between_rounds()` calls while keeping `_buffered()` → still 16/17. So `_buffered()` is
   the cause.
3. **It is not a hang — it is a slowdown past the budget.** Run standalone with a 240s ceiling, the
   same config completes cleanly: `COMPLETED in 66171 ms`, `failures: []`,
   `would_have_triggered_count: 0`. The test allows 60s. So the work still finishes and still
   finishes *correctly*; it now takes ~66s where it used to fit inside 60s.
4. **Baseline timing was never captured.** The very next step was to run the same standalone probe
   with the original driver to get the before-number, and that is exactly where the session stopped.
   **Do that first** — without it there is no way to say whether this is a ~10% regression against a
   ~60s baseline (i.e. the test was always marginal) or a genuine multiple.

**Leading hypothesis, unconfirmed.** `digital_twin/machine.py`'s `UARTLink` models real per-byte
wire time (`_advance()` only delivers bytes whose `due` time has elapsed, against real host clock).
Clamping to `any()` turns one `readinto()` into many small rounds, each round re-entering
`ready()`/`_advance()`. If the twin's effective throughput is bounded by rounds rather than by bytes,
the dev soak gets slower in wall-clock terms while remaining functionally correct. Note this affects
**only the twin**, where wire time is simulated against the host clock — on real hardware the same
change measured *strictly better* (§2.1), so this is very unlikely to be a product defect.

**Candidate resolutions, in the order worth trying** (none chosen — this is the next session's call,
and the owner should probably decide between the last two):

- Get the baseline number first (step 4). The answer may simply be that the test's 60s budget was
  always marginal on this host and the honest fix is a larger budget with a comment saying why.
- Make the twin's `any()`/`_advance()` cheaper per call, if profiling shows per-round overhead
  dominates rather than modelled wire time.
- Reduce round count in the driver by waiting briefly for more bytes before reading — but **this
  must not reintroduce a synchronous wait**, and it would trade away some of §2.1's win. Needs the
  owner's view.

**Do not "fix" this by reverting `_buffered()`.** That would restore a measured 4.4ms synchronous
block of the event loop on real hardware, which is the thing the owner's standing rule forbids.

## 5. Also open, deliberately not decided

`UART_PROMOTION_REQUIREMENTS.md` H4's function test ("a transfer completes while the API is
hammered") is vacuous on an isolated run: `sensortask_dev.py` registers
`uart_initiator.get_task_starters()` as deliberately empty, so nothing on a live system ever
initiates and the test proves an idle link stays idle. **Owner direction (2026-09-11): H4 applies
sensibly once a full bench-tier run is actually started, which is the next session's job** — revisit
it in that context rather than treating it as a defect in the test on its own. Options are in
BACKLOG.md; nothing has been wired, and `sensortask_dev.py` is untouched.
