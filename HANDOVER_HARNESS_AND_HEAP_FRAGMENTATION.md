# Handover — bench harness fixes + the heap-fragmentation defect

Temporary file, same convention as the real-hardware handovers that preceded it (all since
migrated and deleted): delete
once its contents are migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, or confirmed not to
apply.

Written 2026-09-17 by a session that **had** the project owner's real-hardware go-ahead and used it.
Part 1 describes uncommitted working-tree changes that a following session must decide what to do
with. Part 2 is everything known about the heap-fragmentation defect, arranged so a session can
start testing solutions immediately — **including a working reproduction that needs no hardware.**

Provenance is marked throughout, because it matters here:
- **[HW]** = measured by this session on the real `dev` bench board.
- **[TWIN]** = measured host-side by a delegated analysis agent; **not independently verified**.
- **[SRC]** = read directly from the code in this repo, verified.
- **[EXT]** = external source, URL given.

---

# PART 1 — Harness changes (uncommitted)

## 1.0 State

Branch `claude/digital-twin-wifi-fram-persistence-fix` at `569c6bb`, identical to origin (no commits
ahead or behind). **Five modified tracked files, uncommitted, no untracked files.** Nothing pushed.

`ruff check tests_hardware/` is clean and the 41 tests in
`tests_scripts/test_persistence_write_marker_completeness.py`,
`test_require_clean_hardware_run_sh.py` and `test_test_sh.py` pass with these changes applied.

A separate, unmerged branch `claude/pr103-real-hardware-fram-validation` (6 commits) holds further
PR #84 carry-over work — errno 11 -> 35, the ISL29125 conformance stand-in table and its guard test,
the bench `"Unchanged"` fix, a twin bus-hazard settle fix, and `REAL_HARDWARE_FINDINGS_PR103.md`.
Only the lighting-scenario fix from it was brought onto this branch.

## 1.1 `tests_hardware/harness.py` — serial device re-resolution

**Problem [HW].** `Board.__init__` hardcoded `/dev/ttyACM0`. A hard reset re-enumerates the CDC-ACM
device and the kernel does not guarantee the same index: observed moving `ttyACM0 -> ttyACM1`
mid-suite, then back again. Every subsequent serial-using test then failed with mpremote's generic
`failed to access /dev/ttyACM0 (it may be in use by another program)` — which is misleading, the
node simply no longer existed. **This produced a 43-error cascade in a full bench run.**

**Fix.** New module-level `resolve_board_device()` prefers the stable
`/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_*-if00` symlink (named by USB serial number, so
it survives re-enumeration), falling back to the lowest `ttyACM*`, then to `/dev/ttyACM0` so the
error message stays familiar when no board is attached. `Board.__init__` stores `_pinned_device`
(constructor arg or `$MPREMOTE_DEVICE`) and only auto-resolves when nothing is pinned — an explicit
device is never second-guessed. New `_rebind_device_if_moved()` re-resolves inside `_mpremote()`'s
retry loop when the current node has vanished, rebuilding the command and retrying on the new node
before escalating to the USB unbind/rebind (which would not have helped).

**Evidence it works [HW].** Full bench run afterwards: the node moved `ttyACM0 -> 1 -> 0` across the
run with **zero** errors, versus 43 before.

## 1.2 `tests_hardware/bench/test_hotspot_role_reversal.py` — SSID restore in teardown

**Problem [HW]. This is the most serious of the four.** The `joined_hotspot` fixture's stage 0 does
`PUT /networking {"SSID": ""}` to force hotspot mode. That value is **persisted to the RP2040 flash
filesystem**. The fixture never restored it — restoration only happened inside stage 6's own
credential-push test. So any failure before or at stage 6 leaves the board permanently in hotspot
mode with no STA config, which no reset clears.

**This actually happened on 2026-09-17.** A mid-suite failure left the DUT unreachable; recovery
required reading `config_WIFI.cfg` over the serial REPL, confirming `"SSID": ""`, writing the real
SSID back, and hard-resetting. It is exactly the "stage-6 permanent-WLAN-deactivation risk"
`CLAUDE.md`/`tests_hardware/README.md` warn about, realised.

**Fix.** Stage 0 now reads the real SSID via `GET /networking` **before** clearing it, and asserts it
is non-empty (refusing to clear if it cannot be recorded). Stage 7 restores it via
`PUT /networking {"SSID": original_ssid}` **over the hotspot**, before
`leave_dut_hotspot_and_restore_bridge()` — over the hotspot is the only link to the DUT that still
exists at that point. The restore is best-effort and never raises (it prints a `RESULT NOTE` on
failure) so it cannot mask whatever real failure is unwinding the fixture; stage 8's reachability
check still fails loudly if the DUT does not come back.

**Evidence it works [HW].** Module run standalone: 10 passed, 1 skipped, and `GET /networking`
afterwards confirmed `SSID: 'sensors-bench-fa9707'` restored. Then survived a full-suite run.

## 1.3 `tests_hardware/flash/test_watchdog_starvation.py` + `harness.py` — `allow_recovery`

**Problem [HW].** `test_watchdog_starvation_triggers_a_real_hardware_reset` asserts the connection
drop is observed in `< 10.0s`. It measured **13.2s, reproducibly** (13.190s and 13.235s on two runs).
Cause: it calls `run_isolated()`, which goes through `_mpremote()` with `allow_recovery=True`, whose
transient-disconnect retry spends a full **10s grace window** before reporting. Watchdog arm (1.5s)
+ grace (10s) + overhead = 13.2s. **The assertion was measuring the harness's retry policy, not the
watchdog** — and could never pass as written.

**Fix.** `run_isolated()` gained an `allow_recovery: bool = True` passthrough to `_mpremote()`; this
test passes `allow_recovery=False`, because the disconnect here is the *expected* outcome and must
not be retried. The 10.0s assertion was **not** relaxed.

**Evidence it works [HW].** The test now passes in **3.31s**, versus failing at 13.2s.

## 1.4 `tests_hardware/conftest.py` — help text only

`--device`'s help string updated to describe the new default. No behaviour change.

## 1.5 `tests_hardware/device_scripts/isl29125_lighting_scenarios.py` — carried over, not a harness fix

The PR #84 `_park()` / declared-entry-range fix, brought across from
`claude/pr103-real-hardware-fram-validation`. Scenario tuples widened to include an entry light;
`_park()` forces the entry range before a scenario starts counting, deliberately **not** via
`rig.observe()`, so a range switch caused by *getting into position* is not charged to the
scenario's own switch budget. `W13` checking moved to run level.

**Evidence [HW].** This test failed before the fix and passed after it, in consecutive full-suite
runs on the same board.

## 1.6 Bench-suite results across the three runs [HW]

| Run | Result |
|---|---|
| 1 — as found | 6 failed, 34 passed, **43 errors** |
| 2 — after 1.1 only | 29 failed, 54 passed, 1 error (new cascade: the 1.2 SSID defect) |
| 3 — after all fixes | **1 failed, 82 passed**, 2 skipped, 37 deselected |

Run 3's single failure is the heap-fragmentation defect (Part 2). It is not a harness problem.

Runs were `scripts/run_bench_hardware_suite.sh` with **no** `--allow-persistence-writes`, so 37
tests were deselected and no flash cycles or SCD30 NVM writes were spent. The gate was verified by
collection: bench 48/71 default vs 71 with the flag; flash 42/51 vs 50/51 vs 51 with both flags;
`--allow-scd30-extra-write` alone changes nothing (the AND-gate holds).

## 1.7 Follow-up fixes from a host-side review (2026-09-18) — **re-verify on the bench**

Five defects found by reading Part 1's changes against the code they touch. All are committed.
The reviewing session had no real-hardware go-ahead, so it landed them as [SRC] only; the bench
session has since validated them from the bench host — see §1.7.1 for what that covered and what it
did not.

1. **`_usb_reset_device()` was silently dead on the new default path.** It does
   `name = Path(device).name` and looks for `/sys/class/tty/<name>/device`. With §1.1's by-id
   symlink as `self.device`, that name has no `/sys/class/tty` entry, so the function returned
   `False` and the documented unbind/rebind recovery for a wedged raw-REPL state never ran. The
   rebind path in §1.1 cannot cover it: a wedged-but-*present* node makes
   `_rebind_device_if_moved()` return `False`, which is exactly when the unbind/rebind was meant to
   fire. Fixed with `Path(device).resolve().name`. Confirmed on the bench (§1.7.1). **Still worth
   watching on the next wedge:** the unbind/rebind prints nothing, so look for the ~5s pause and
   recovery rather than a hard failure.
2. **`test_watchdog_starvation` could pass without the watchdog firing.** It treats any
   `HardwareTestFailureError` as the expected reset. With §1.3's `allow_recovery=False`, a transient
   `"may be in use by another program"` at connect — the case the retry existed to absorb — raises
   the same error just as fast, clears the `< 10.0s` bound, and then both `wait_until` probes pass
   instantly because the board never went away. It now asserts the device script's own
   `"WDT armed, starving now"` banner appears in the failure text, which only happens if the script
   really got onto the board. The banner check sits **after** the 10.0s timing bound, not before
   it: `_mpremote()`'s own `subprocess.TimeoutExpired` path (`harness.py:169`) reports with no
   stdout at all, and that case is a 15s hang the timing bound already names correctly — checking
   the banner first would relabel it as a script that never started. **On rerun:** this is the one
   fix that could turn a previously green test red. If it does, read whether the banner is
   genuinely absent (a real connect failure — the fix working) or merely not captured (mpremote
   dropping buffered device stdout when the link dies — in which case the marker is the wrong
   instrument and the reset needs proving another way).
3. **The rebind retry was unbounded**, unlike the deliberately once-only USB reset in the same loop:
   each rebind added another 10s of grace, and no single `subprocess` timeout breaks out of
   `_mpremote()`'s `while True`. Capped at `_MAX_DEVICE_REBINDS = 2`. The verifying run saw the node
   move twice across the whole suite, never twice within one call, so this should be invisible.
4. **The §1.2 teardown caught only `OSError`.** `fetch()` itself only raises `OSError` subclasses,
   but `.json()` on a 200 with a non-JSON body raises `ValueError`, which would escape the
   best-effort block and mask the failure unwinding the fixture — the one thing its comment says it
   must not do. Now `(OSError, ValueError)`.
5. **`tests_hardware/README.md` still documented the `/dev/ttyACM0` default.** §1.4 updated
   `conftest.py`'s help string but not the durable reference. Updated, including the note that
   `scripts/mpremote_connect.sh` genuinely does still default to `ttyACM0`.

### 1.7.1 Validation by the bench session (2026-09-18)

Run by the session that holds the bench, reported back rather than committed; recorded here by the
reviewing session, so this subsection is **relayed, not first-hand**. Nothing below needed a board
command — the empirical parts are filesystem reads and host-side test runs.

| Item | How verified |
|---|---|
| #1 `_usb_reset_device()` dead on the by-id path | **[HW-host]** On the bench: `resolve_board_device()` → `/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66130100f372d34-if00`; `Path(d).name` → no `/sys/class/tty` entry (old code: recovery dead), `Path(d).resolve().name` → `ttyACM0`, entry exists. The defect was real and the fix works. |
| #2 watchdog banner assertion | **[SRC]** Banner present at `watchdog_starvation_reset.py:10`; `run_isolated()`'s raise (`harness.py:241`) carries stdout, so the assertion has something to match. Not exercised — that needs the board. |
| #3 rebind cap | **[SRC]** No behaviour change when the node has not moved. |
| #4 `ValueError` on `.json()` | **[SRC]** `http_client.py:23` is a bare `json.loads`, so the escape route was real. |
| #5 README | **[SRC]** Text accurate, including that `scripts/mpremote_connect.sh` still defaults to `ttyACM0` (its line 8) and that a pinned path is never re-resolved (`harness.py:139`). |
| `c1ab149` — the vitest parametrisation | **[SRC]** Equivalent transformation: `"x".repeat(len)` is injective over lengths and `validLengths` is already `new Set`-deduped, so map-then-filter and filter-with-mapped-predicate select the same set; the added `CASE_TIMEOUT_MS` is the correct `it.each(...)(name, fn, timeout)` third argument. |
| `mock-server-put-matrix.test.js` | **[HW-host]** Re-run independently: 390/390 passed in 116s. |
| `live-backend-put-matrix.test.js` | **[HW-host]** 243/243 passed, 708s, exit 0, against a real twin in a real browser. |

The last row closes a gap `c1ab149` itself recorded as unclosable: its commit message and PR #103's
description both say that file's change rests on inference from its sibling plus eslint/tsc, because
that session had no live backend. The "live backend" turns out to be the Unix-port binary plus a
spawned twin — no hardware — and the bench host has both. It needs `scripts/build_website.sh wozi`
first (skipping the pretest build fails at `waitForSelector`).

**Still unvalidated, by nature:** #2 is the only one of the five that changes what a real board run
asserts, and nothing short of a bench go-ahead settles it.

**A flash-wear question §1.2 raised, now settled by the project owner (2026-09-18).** Six tests in
`test_hotspot_role_reversal.py` use the `joined_hotspot` fixture without carrying
`@pytest.mark.persistence_write`, so in a default run with no `--allow-persistence-writes` — §1.6's
run 3 — the fixture still instantiates, stage 0's SSID clear writes the RP2040 flash filesystem, and
the teardown restore writes it a second time (stage 6 is deselected in that mode, so the restore is
a real change, not an `"Unchanged"` no-op). **That is correct, not a gap**: the gate covers a write
a test *owns*, not one it is reached through, and these are prerequisite writes that exist so a
dozen other tests can run at all. Gating them would deselect exactly what they enable. The flag
chooses between "test everything and accept the higher wear" and "test everything that matters and
keep wear as low as it can go" — never "spend zero". Recorded in `CLAUDE.md`, `tests_hardware/
README.md` and the completeness guard itself, whose `joined_hotspot` entry had justified the
exemption on a different and untrue ground ("every dependent is marked").

**Closed by `9cfb3b3`** (bench session): `resolve_board_device()` no longer carries a second,
looser copy of device discovery — it imports `detect_pico_serial_devices()` from
`toolchain/setup_toolchain.py`, so the two cannot drift, and takes the same injectable directories.
Identification is by USB vendor ID, two boards attached is a hard error naming both, and no board
returns a path that cannot exist so the `board` fixture still skips rather than opening a stranger's
port. Named by the by-id symlink as before, now matched by target rather than by the hardcoded
product string. Seven host-side tests over fabricated `/sys`, `/dev` and by-id trees
(`tests_scripts/test_resolve_board_device.py`) cover the multi-device cases the one-board bench
cannot; on the bench itself the new implementation returns the previous answer byte for byte.

**One correction to this section's own framing, from that work:** the claim above that the bare
`ttyACM*` fallback "could select the Arduino UART peer rather than the Pico" was too strong. With
both devices present the old code already picked correctly — the by-id glob is Pico-specific and
runs first — so it could only pick a foreign device when **no board was attached at all**, opening
that peer's port to find out. Real, but never "drives the wrong board".

**Still open, deliberately not taken:** `scripts/mpremote_connect.sh:8`'s
`device="${MPREMOTE_DEVICE:-/dev/ttyACM0}"` is the last hardcoded node, and now the only entry point
an erratic re-enumeration can strand. A `scripts/` change owes CLAUDE.md's two-chroot pre-push gate,
which is the project owner's call rather than a drive-by edit; `tests_hardware/README.md` names it
as a known exposure in the meantime.

---

---

# PART 2 — The heap-fragmentation defect

## 2.1 The symptom

`tests_hardware/flash/test_memory_stress.py::test_real_gc_heap_headroom_survives_a_full_system_build`
fails. Device script: `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py`.
It asserts two floors: **100,000 B free** and **80,000 B largest contiguous block**.

**Real-hardware, both ends, bracketing WP1+WP2 (`9cf8a9c`, 2026-09-16):**

| | 2026-09-11 [HW, SPECIFICATION.md:3439] | 2026-09-17 [HW, this session] |
|---|---|---|
| baseline free / largest | 148,448 / 146,112 | 139,024 / 129,328 |
| after `build_system()` free / largest | 130,224 / **115,536** | 108,736 / **20,592** |
| `alloc` after build | — | 84,240 |

**Largest contiguous block collapsed 5.6x while free memory fell only 16%. Only the contiguity floor
fails — free is still above its own floor.** This is a layout defect, not a consumption defect.

**It is fully deterministic [HW].** Byte-identical free/alloc/largest across all three bench runs,
despite materially different FRAM states between them. Not a flake, not load-dependent.

**Ruled out on hardware [HW].** The "FRAM re-initialisation doubles the transaction burst" theory
(offered to explain an earlier *intermittent* 33,168 observation) does **not** explain the current
state: zero `Invalid data in block` / `Writing block` lines in the failing runs.

## 2.2 Mechanism [SRC]

MicroPython's GC is **mark-and-sweep, non-compacting** (`SPECIFICATION.md` I.1 states this already).
First-fit from a scan hint (`gc_last_free_atb_index`) that tracks the lowest known free *single*
block and is reset to 0 for every area by `gc_collect_end()`.

**The measurement is taken after a full `gc.collect()`** — `_report()` calls it (line 47) and
`_largest_block()` calls it again (line 29) before its binary search. This is the crux:

> On a non-compacting collector, dead allocation churn is reclaimed and its space coalesces.
> Churn therefore **cannot** leave a post-collect heap fragmented. The fragmenters can only be
> **surviving objects sitting at scattered addresses**.

Churn is the *mechanism that scatters them*: heavy churn forces repeated collect cycles, and any
object that survives is stranded wherever the allocation front had reached when it was born. The
largest free run is then bounded by the gaps between survivors — theory gives largest gap
~ `(H/N)*ln N`, so **a handful of well-spread survivors is enough**, regardless of their total size.

## 2.3 Allocation inventory [SRC] — scanned project-wide

Method: AST scan of `src/` for new objects bound to `self.*` outside `__init__`, plus module-level
and class-level allocation, plus mutation of retained containers. Two scan defects were found and
corrected during the sweep (annotated assignments `x: T = {}` are `ast.AnnAssign` not `ast.Assign`;
and `self.X = <local>` needs the local's own allocation tracked) — a naive scan **misses the
confirmed splitter**, so re-derive carefully if you redo this.

**Module / class level — clean.** Only namedtuple types and small constant tables, allocated at
import, packing low. One class-level attribute (a `struct.calcsize` int).

**Construction phase (`__init__`) — already correct, and this is most of the codebase.**
Bus objects (`I2C.init`/`SPI.init` are *called from* `__init__`), `PrintLogHistory.history` deque
(`print_log.py:141`), FRAM chunk + per-chunk `asyncio.Lock` (`asy_fram_manager.py:66`),
`PrintLogHistoryStore`'s chunk (`print_log.py:238`), `LockableBuffer` (`base_classes.py:56-73`),
`SCD30_I2C._buffer`, `SGP40_I2C._command_buffer`, ISL `_filtered` (`asy_isl29125_driver.py:277`),
webserver registries (`asy_webserver_service.py:293,298`). **Zero SPI transactions in this phase.**

**Build/setup phase — exactly ONE attribute splitter:**
- `config_manager.py:510` and `:522` — `self._cache = valid_cfg` **rebinds** to a dict built during
  `setup()` (the local is allocated at `:478`), discarding the `__init__` dict at `:251`. Both the
  dict *and* its JSON-derived string values are therefore born mid-churn.

**Task-loop phase — after `build_system()` returns, OUTSIDE the failing test's window:**
- `asy_sgp40_driver.py:661` — `self._voc_algorithm = VOCAlgorithm()`, guarded by `is None`,
  allocated inside `_read_sgp()`. Large: a params object with ~40 fields plus precomputed tables.
- `asy_bmp3xx_driver.py:527,532` — `_temp_calib` / `_pressure_calib` tuples, from
  `BMP3XX_I2C.setup()` reached via `BMP3xx_Reader._init_bmp()` (`:207`), which runs in the read task.
- **13** `await self.pr.setup()` sites in `src/`, most inside task loops. `SCD30_Reader`,
  `NeopixelDriver` and `WebserverService` have **no** `build_system()` `setup()` at all.
  Measured effect [TWIN]: 6s of real task graph took largest_block a further 29,184 -> 21,632.

**Correctly churning (~30 sites, no action needed).** `_cal_recent`, `rgbt`/`ext_rgbt`, SCD30 value
floats, all `*_ms` timestamps, `_staged`/`_pending_flush`, `dns_server_task`/`ledflash`.

**Retained-container mutation — overwhelmingly the good pattern.** `self._buffer[k]=v`,
`_cmd_buf[k]=v`, `_ack[k]=v`, `pixel[k]=v`, `_filtered[k]=v` are all fill-in-place into
pre-allocated buffers. `NotificationCoordinator._registered` grows only at wiring time, bounded by
device config.

**Scope limit of this inventory.** It covers attribute rebinds, module/class level, retained
container growth, and per-transaction churn in the FRAM/SPI path. It does **not** cover closure
captures, allocations inside composed third-party objects, or `ext/microdot.py` internals.

## 2.4 Why only ~5 of ~19 splitters could ever be named

[TWIN] reported ~19 surviving objects totalling only **~480 bytes** born during the setup batch, and
could name 5 by address — all `ConfigManager._cache` dicts. §2.3 explains the other 14: **they are
not attribute rebinds at all.** They are the JSON-derived *string values inside* `_cache` (dict
contents, not attributes; `str` is immutable so cannot be filled in place) plus interpreter-level
objects (qstrs, dict resizes, asyncio waiters). ~192 B allocated by the first
`PrintLogHistoryStore.setup()` was never identified — **still open**.

**This is the single most important strategic fact in this document:** the majority of the
build-phase problem is structurally out of reach of an `__init__`/`setup()` hoisting discipline,
because there is no attribute to hoist.

## 2.5 Churn sources, quantified

[TWIN], dev, one `build_system()`: **668 SPI CS sessions** and **~1.38 MB gross allocated** during
the setup batch, versus **2 CS sessions** pre-WP. Per-operation [TWIN], 64-bit: one bare SPI CS
session ~5,519 B; one FRAM `get_values()` ~8,794 B; one `set_values()` ~42,845 B;
`await asyncio.sleep(0)` ~896 B.

Structural multipliers [SRC]:
- `asy_fram_driver.py:135-148` — `_write()` envelope is **6 CS sessions per byte-level write**
  (WP check -> WREN -> RDSR -> WRITE -> WRDI -> RDSR), plus transient `bytearray([opcode])` at
  `:93`, `:105`, `:113`, `:220`.
- `asy_fram_manager.py` — `_read()` reads block 0 and re-reads block 1 to compare; `_write()` writes
  both. `get_buffer()` (`:384`) allocates a **fresh `AsyFramChunkBuffer` + backing bytearray on
  every call**, and `write()` (`:388`) calls it per operation, reached from
  `PrintLogHistoryStore._write()`/`_read()`.
- `asy_spi_driver.py:138` and `:154` — **two `asyncio.sleep(0.001)` per chip-select**.
- `print_log.py:217` — `reset()` allocates a throwaway `[_NO_ERR] * len(self.history)` list; a
  `ResetErrors` sweep allocates 21 of them, inside an operation already measured at 6.4s [HW].

**Do not rewrite `asy_fram_manager.py`/`asy_fram_driver.py` internals in response to this.**
`CLAUDE.md` and `SPECIFICATION.md` C.3.1 make them vendored-adjacent and needing their own scoped
review. The numbers are here to be weighed, and §2.7 shows churn reduction is the *wrong lever*
anyway.

## 2.6 Why the existing audit missed it

**`SPECIFICATION.md` Part I.2 is a size/consumption audit, not a placement/fragmentation audit.**
It explicitly cleared `ConfigManager` as "reviewed, found already safe ... each instance owns one
small file, no aggregation". That is true about *size*, and precisely why the layout problem was
invisible to it. Part I.1 already carries the "instantiate large permanent buffers early" guidance —
it was simply never turned into a checked rule. Any fix should close that gap, not just the instance.

## 2.7 Measured remedy data

### 2.7.1 Twin experiment matrix [TWIN — not independently verified]

Frozen Unix port, `-X heapsize=400k`, twin FRAM image and bus logs neutralised, reactive-only GC
default, measured after a full collect. Reported deterministic across repeats.

| variant | what it changes | largest_block | vs baseline |
|---|---|---|---|
| `no_setup_batch` | whole setup batch skipped — the ceiling | 152,256 | 4.2x |
| `no_fram_setup_io` | every `PrintLogHistoryStore.setup()` a no-op ~ pre-WP2 | 132,096 | 3.6x |
| `fram_io_deferred_to_end` | all logger FRAM I/O in one run, after the batch | **126,528** | **3.5x** |
| `deferred_plus_prealloc` | above + `_cache` pre-allocated | 121,312 | 3.3x |
| `fram_io_first_plus_prealloc` | consolidated pass first + `_cache` pre-allocated | 87,104 | 2.4x |
| `fram_io_first` | consolidated pass as first step of the batch | 79,872 | 2.2x |
| `prealloc_cache` | **only** `_cache` pre-allocated, filled in place | 50,016 | 1.4x |
| `baseline` | today | 36,576 | 1.0x |
| `cfg_parse_deferred_to_end` | config parsing deferred, I/O left interleaved | 31,552 | 0.9x |
| `no_cs_sleeps` | both `asyncio.sleep(0.001)` removed from `SPIDevice` | 31,328 | **0.9x** |

**`fram_io_deferred_to_end`'s 3.5x is NOT shippable as measured.** `PrintLogHistoryStore.setup()`
calls `_read()`, which does `self.history.extend(...)` into a **bounded** deque, and
`PrintLogHistory._store_err()` already returns early without persisting while `not self.initialized`
[SRC]. Running the consolidated pass *last* widens the window in which a logged error is never
persisted to the whole setup batch. It is a difference of degree (that window already exists today
for every module late in the batch), not a new failure class — but it must be a conscious choice.
The behaviour-preserving figure is **`fram_io_first`, 2.2-2.4x**.

### 2.7.2 Tier-0 synthetic model [verified by this session, host-side, reproducible in seconds]

Stock Unix port, `-X heapsize=400k`, no frozen build, no twin. 12 survivors of 24 bytes each,
interleaved with churn (200 x `bytearray(700)` per survivor):

| ordering | largest block |
|---|---|
| clean heap, no survivors | 398,624 |
| **interleaved (models today)** | **78,944** |
| survivors FIRST, then all churn (= `__init__` before `setup()`) | **394,720** |
| all churn FIRST, then survivors | 230,496 |

**~288 bytes of survivors destroyed a 398 KB contiguous region, with `mem_free` unchanged.** This is
the whole defect in miniature, and it confirms the twin's ordering result independently:
survivors-first (churn last) beats churn-first.

### 2.7.3 How much does PARTIAL hoisting buy? [verified by this session]

Same model, varying how many of the 12 survivors are allocated up-front. **Compare within this
table only** — its churn total differs from 2.7.2, so its 0/12 figure is not 2.7.2's 78,944.

| hoisted | largest block |
|---|---|
| 0/12 | 41,280 |
| 3/12 | 65,664 |
| 6/12 | 106,880 |
| 9/12 | 147,328 |
| 11/12 | 253,856 |
| **12/12** | **398,560** |

**Partial hoisting helps roughly proportionally — it is not all-or-nothing — but there is a cliff at
100%.** 11/12 gets 64% of the way; the last survivor is worth another 57%. Consistent with the
`(H/N)*ln N` theory: each remaining scattered survivor roughly halves the biggest run.

**Scaling to the board:** the floor demands largest >= 73.6% of free (80,000 of 108,736). In this
model that lands between 11/12 and 12/12 — i.e. **hoisting alone needs >90% exhaustiveness to clear
the floor.** Given §2.4's unhoistable residual, that is the quantitative case for compacting churn
as well as (or instead of) hoisting.

## 2.8 External prior art [EXT]

- **MicroPython's own guidance is the hoisting idea, verbatim, but only for *large* buffers.**
  `docs/reference/constrained.rst:359-363` (<https://docs.micropython.org/en/latest/reference/constrained.html>):
  "Where large permanent buffers or other objects are required it is best to instantiate these early
  in the process of program execution before fragmentation can occur." The sub-kilobyte regime this
  defect actually lives in appears undocumented anywhere.
- **No placement/lifetime API is exposed to Python.** `gc_alloc()` takes only `(n_bytes,
  alloc_flags)`. The only Python-visible knobs are `gc.collect()`, `gc.threshold()`,
  `gc.disable()/enable()` — all forbidden as fixes by `SPECIFICATION.md` I.4 or useless here.
- **`MICROPY_GC_SPLIT_HEAP` is unavailable on this board.** `ports/rp2/mpconfigport.h:100-101` gates
  it on `MICROPY_HW_ENABLE_PSRAM`; the Pico W has no PSRAM. It adds *areas*, not lifetime
  separation, in any case.
- **Upstream treats fragmentation as known and unfixed.**
  <https://github.com/micropython/micropython/issues/2057> — same symptom shape; remedies floated
  (compacting collector, fixed-block allocator) were rejected as too costly.
- **CircuitPython solved exactly this, and measured it.**
  <https://github.com/adafruit/circuitpython/pull/547> ("Introduce a long lived section of the
  heap", merged Jan 2018): short-lived objects allocate upward from the bottom, **long-lived
  downward from the top**, confining churn to one end. Source comment in the 6.3.x branch's
  `py/gc.c` states the rationale directly. Their measured result: *"a test import into a 20k heap
  that leaves ~6k free previously had the largest continuous free space of ~400 bytes. After this
  change, the largest continuous free space is over 3400 bytes."* — **8.5x**, the same symptom shape
  as ours.
  **It was removed in CircuitPython 9** (<https://github.com/adafruit/circuitpython/pull/8281>) —
  but because their `gc_make_long_lived()` *promotion* mechanism, which **moves** an existing
  object, collided with an upstream `const` field, plus merge cost. **Not** because lifetime
  separation failed. The maintainer's stated preference was to do long-lived "explicitly ... when
  they are allocated, instead of moving them later" — which is the owner's proposal, and never
  moves anything, so it cannot inherit that defect.
  The C-level technique is not available to us without forking vendored MicroPython (forbidden by
  `CLAUDE.md`); **the Python-level analogue — allocate long-lived first, in a phase with no churn —
  needs no fork.**
- **General embedded practice**: allocate everything during an init phase then stop; arena/pool
  allocators grouped by lifetime (e.g. TensorFlow Lite Micro's fixed arena,
  <https://arxiv.org/pdf/2010.08678>). The principle transfers; the mechanism does not, since we
  cannot install an allocator under MicroPython's GC and an asyncio webserver allocates
  continuously.

## 2.9 How to reproduce and measure WITHOUT hardware — the actionable part

### 2.9.1 The instrument: a portable free-run profiler

`micropython.mem_info(1)` prints a block-level heap map, but **its output cannot be captured
in-process** — MicroPython has no assignable `sys.stdout`, so parsing it means capturing the
process's stdout host-side. Use this instead: it needs only `gc` and `bytearray`, so it runs
**identically** in the Tier-0 model, in the twin, and on the real board.

```python
import gc

def largest_block(lo=16, hi=1 << 22):
    """Largest single contiguous allocation still obtainable. Same probe shape as
    heap_headroom_after_full_system_build.py's own _largest_block()."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        try:
            b = bytearray(mid)
            del b
            lo = mid
        except MemoryError:
            hi = mid - 1
    return lo

def free_run_profile(max_runs=12, floor=256):
    """Claim successively largest blocks and hold them; the sequence of sizes IS the free-run
    distribution. Releases everything before returning. This is what distinguishes 'one big run'
    from 'N medium runs' - largest_block() alone cannot."""
    gc.collect()
    held, prof = [], []
    try:
        for _ in range(max_runs):
            n = largest_block()
            if n < floor:
                break
            held.append(bytearray(n))
            prof.append(n)
    finally:
        del held
        gc.collect()
    return prof
```

A healthy heap profiles as `[<almost everything>, small, small, ...]`. A fragmented one profiles as
several comparable mid-size runs — which is exactly the failure signature.

### 2.9.2 Tier 0 — synthetic mechanism model. **Works today, zero infrastructure.**

Reproduces the defect's signature in under a second with the project's existing Unix-port binary at
`$PICO_TOOLCHAIN_DIR/micropython/ports/unix/build-standard/micropython` (or `~/pico-toolchain/...`).
Run with `-X heapsize=400k`. Core of it:

```python
def churn(rounds=200):
    for _ in range(rounds):
        t = bytearray(700)
        del t

S, R = 12, 200

def interleaved():                    # models today
    s = []
    for _ in range(S):
        churn(R)
        s.append(bytearray(24))
    return s

def survivors_first():                # models __init__-then-setup
    s = [bytearray(24) for _ in range(S)]
    for _ in range(S):
        churn(R)
    return s
```

Measure `free_run_profile()` after each, keeping the survivors alive. Results in §2.7.2/§2.7.3.

**What Tier 0 is good for:** ordering questions, exhaustiveness thresholds, whether a proposed
discipline works *in principle*, and regression-testing a proposed invariant. It is fast enough to
iterate on interactively.
**What it cannot tell you:** which real objects the survivors are. It models the mechanism, not the
codebase.

### 2.9.3 Tier 1 — the real `src/` object graph in the twin

Four requirements; three are already solved in-repo.

1. **A frozen Unix port. The machinery already exists and is currently thrown away.**
   `toolchain/setup_toolchain.py:319` `build_unix_port(..., frozen_manifest=...)` already builds
   one, and `write_freeze_manifest()` (`:405`) writes the manifest. Today it freezes only a trivial
   verification module, and **line 466 rebuilds a vanilla port as "the real test rig", discarding
   the frozen one.** Retaining a variant that freezes `src/` + `ext/` + `build/generated_src/` +
   `frozen_modules/` is a configuration change, not new machinery.
   **Why it is required:** importing `sensortask_dev` under a stock Unix port costs ~546 KB of heap
   (bytecode compiles *into* the heap rather than being frozen into flash) and leaves the heap
   already shredded before the measurement starts.
2. **Neutralise two twin artifacts** (at runtime in the harness, not by editing the repo):
   - `digital_twin/machine.py:13,252` — `SPI.log` / `I2C.log`, 200-entry deques (`_LOG_MAXLEN`)
     that capture a copy of **every** bus transaction. On a transaction-heavy run they saturate at
     ~20 KB and are counted as survivors. **This artifact invalidated an earlier "~16.5 KB of
     setup-phase survivors" figure; the real number is ~480 B.**
   - `digital_twin/_fram_chip.py:43` — `self.memory = bytearray(size)`, a 262 KB RAM image of a chip
     that is off-board on real hardware.
3. **Heap sizing** — choose `-X heapsize` so the twin's free-space-to-churn ratio matches the
   device's (~193 KB heap against ~1.38 MB of setup-batch churn).
4. **The instrument** — §2.9.1, unchanged.

### 2.9.4 Tier 2 — hardware, for final confirmation only

With Tiers 0 and 1 in place the board is needed only to confirm a chosen fix, not to develop it.

### 2.9.5 Fidelity bounds — state these with any twin number

- **The twin stays 64-bit; object sizes are roughly 2x.** `MICROPY_FORCE_32BIT` is **dead** — the
  Unix port Makefile (line 19-20) emits *"The MICROPY_FORCE_32BIT flag is no longer affecting
  builds"* — and the bench Pi4 has no armhf cross-gcc and no multilib. A 32-bit twin would need a
  cross toolchain or qemu. **Treat twin ratios as the result; re-measure absolutes on hardware.**
- Calibration [TWIN]: ~3% agreement at baseline, ~20% post-build, and the twin **understates** the
  achievable ceiling (it carries ~27 KB of import-phase holes the all-frozen rp2 firmware does not).

## 2.10 Ideas on the table, and what the evidence says about each

1. **Consolidate every FRAM-backed logger's `setup()` into one dedicated consecutive step of the
   generated setup batch.** Highest measured value (2.2-2.4x behaviour-preserving, 3.5x if run
   last). Mechanical: one change in `buildgen/codegen.py`'s setup-order emission (`:453-470`); the
   enumeration already exists as `module.get_loggers()`. `PrintLogHistoryStore.setup()` is
   **idempotent** [SRC] (`if self.fram is None or self.initialized: return`), so existing in-module
   calls can stay as no-ops — making the change purely additive and low-risk.
2. **The owner's `__init__`/`setup()` lifetime invariant** — all long-lived allocation in the
   synchronous `__init__`, all churn-prone I/O in `async setup()`; add a `setup()` to modules that
   lack one; promote it to downstream composed instances; extend beyond FRAM (the VOC algorithm
   object is a confirmed instance). **Correct in mechanism and confirmed optimal in Tier 0**
   (survivors-first recovered 99% of a clean heap). Its limits are §2.4 (unhoistable residual) and
   §2.7.3 (>90% exhaustiveness needed to clear the floor alone). Worth adopting as a documented,
   enforced rule regardless of its standalone number, and it is the only idea that also addresses
   the task-loop-phase instance.
3. **Reconsider WP2's per-`ConfigManager` boot-time chunk I/O** — e.g. make the `CFGMGR_*` chunk
   read lazy (first error, not boot), keeping persistence but removing it from the boot critical
   path. Unmeasured; speculation. Reverting WP2 outright recovers ~everything [TWIN] but throws away
   diagnostic value `CLAUDE.md` explicitly relies on — **not** recommended.
4. **Churn reduction — measured dead end. Do not spend effort here.** Removing both
   `asyncio.sleep(0.001)` calls from `SPIDevice` cut a large share of the 1.38 MB and made the
   result marginally *worse* (0.9x). The regime only changes if total churn drops below roughly one
   free-region's worth, i.e. ~8x, which is unreachable without the out-of-scope FRAM rewrite.

### 2.10.1 Enforcement — the obvious metric does not work

**"Assert `gc.mem_alloc()` grows by ~0 across the setup batch" already PASSES today, at 480 bytes,
on the currently-failing configuration.** It cannot detect this defect. The defect is not *how much*
survives but *at how many distinct addresses*.

Assert **contiguity** instead: take `largest_block()` after the construction phase and again after
the setup batch, and require the second to be at least ~90% of the first (today it loses ~78%).
That is a structural invariant, independent of heap size, device and MicroPython version, and it
fails the moment anyone re-interleaves long-lived allocation with bus churn. It needs one seam —
a hook between the two phases in `buildgen`'s generated `build_system()`, a no-op in production the
way `sysfunct.feed_watchdog()` already is on a watchdog-less build. `free_run_profile()` gives an
even sharper version (assert the setup batch adds at most N new runs).

## 2.11 Open / unresolved

- **14 of ~19 splitters unnamed by object identity.** §2.4 explains the class they fall into; nobody
  has identified them individually.
- **~192 B allocated by the first `PrintLogHistoryStore.setup()`** — interpreter-level by
  inspection, never pinned down.
- **No remedy has been measured on real hardware.** Every number in §2.7.1 is twin-only.
- **The reader-count curve for `ResetErrors`** (handover §2.1: 0/1/2/3/4/6 readers) is unmeasured
  and blocks **BACKLOG item 32** — the bench tier's 30.0s timeout has no compensating elapsed-time
  budget, and one cannot be sized honestly without knowing whether the curve flattens. Known points
  [HW]: 6.32s idle, 11.58s at 3 concurrent readers. Cheap: no flash cycles, no SCD30 writes.
- **Part I.2's audit needs re-running with a placement lens**, not just the one instance fixed.

## 2.12 What NOT to do

- **Do not "fix" this with `gc.collect()` or `gc.threshold()`.** `SPECIFICATION.md` I.4 forbids both
  as remedies. Note also [TWIN] that setting the threshold *before* `build_system()` makes the twin
  heap look healthy — that is the threshold masking a design defect, which is exactly the condition
  I.4(e) exists to detect, not evidence that nothing is wrong.
- **Do not lower the test's 80,000 B floor.** It encodes a real product property (an 80 KB
  contiguous allocation must remain obtainable after boot) and that property genuinely does not hold.
- **Do not rewrite `asy_fram_manager.py` / `asy_fram_driver.py` internals** off the back of §2.5.
- **Do not trust a digital-twin memory measurement taken before neutralising `SPI.log`/`I2C.log`** —
  §2.9.3. This applies retroactively to any past twin memory figure over a transaction-heavy run.
- **Do not treat the bench board's FRAM error logs as field evidence** without checking what has run
  against it (`CLAUDE.md`'s 2026-09-11 caveat). This session reset them during measurement.

## 2.13 Suggested first moves for the next session

1. Stand up Tier 0 (§2.9.2) — minutes, no board, and it immediately regression-tests any proposed
   invariant.
2. Stand up Tier 1 (§2.9.3) by retaining the frozen Unix port that is already built and discarded.
   This is the piece that turns "which objects?" from guesswork into measurement.
3. Only then choose between idea 1 and idea 2 in §2.10 — and measure the chosen one on hardware
   once, against the numbers in §2.1.
