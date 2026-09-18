# Real-hardware handover — `claude/wp-restart-handover-execution`

Temporary file, like `WP_RESTART_HANDOVER.md` before it: delete once its findings have been either
confirmed-and-migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`, or confirmed not to apply.
Written by a session with **no real-hardware access this conversation** for a session that has (or
will get) the project owner's go-ahead to run against real hardware — see CLAUDE.md's standing gate
("A session needs the project owner's go-ahead, given directly in that session's own conversation,
before running anything against real hardware"). Nothing in this file authorizes skipping that gate.

## Context: why this file exists

This branch (`claude/wp-restart-handover-execution`, PR #101) implements WP1–WP8 from the now-deleted
`WP_RESTART_HANDOVER.md`. An independent review (from the session that originally wrote that handover
doc) read this branch and flagged one real bug (fixed here, see below) plus three items that need
real-hardware confirmation, not just twin/mock-tier confirmation. Separately: an **earlier, partial,
accidental push of WP1+WP2 alone** (before this branch's current, complete state) is what generated
the "~33x real-hardware slowdown" measurement the project owner already has. That partial state is
not what real hardware should be re-measured against — measure against this branch's current tip
instead, since WP3–WP8 (including the reboot-flush fix below) landed after that accidental push.

## What's already fixed here, no hardware needed

- **Commanded reboot could drop a still-staged config write.** `PUT /system` with both a
  settings-group change and `SystemCmd: reboot` in one body (the real shape this happens in —
  `asy_webserver_service.py`'s `_put_system()` applies settings before dispatching the command) used
  to arm the 4-second reset timer while `ConfigManager`'s deferred flash flush (WP5) was still only
  *scheduled*, not run. Fixed: `buildgen/codegen.py`'s generated `_flush_pending_configs()` now
  awaits every constructed module's `cfgmgr.flush_pending()` before `reboot_system()`/
  `reboot_bootloader()`. Regression test:
  `tests/_sensortask_scenarios.py`'s own
  `webserver_system_put_reboot_flushes_a_still_pending_config_write_first` scenario, registered into
  each of the six `tests/test_sensortask_<device>.py` files (so still all 6 devices).
  This closes the one *avoidable* residual-risk gap in WP5's design — the accepted,
  power-loss-only risk window (SPECIFICATION.md Part F.2) is unaffected and still applies.
- **CI red on the former monolithic `tests/test_sensortask.py` /
  `tests/test_digital_twin_webserver_concurrency.py`** — both outgrew `scripts/test.sh`'s 240s
  per-file default (measured standalone: ~447s / ~268s respectively, corroborated independently by
  two separate sessions measuring the identical ~447s figure for the first file). This is WP1/WP2's
  own heavier per-device object graph (more FRAM-backed loggers/`ConfigManager`s per device), an
  *intentional* consequence of decisions the project owner's own review already confirmed as wanted,
  not a defect to revert. **Resolved at the root** (2026-09-17), superseding the per-file timeout
  override (600s / 350s) this entry originally recorded: both files were split by device into a
  shared scenario library plus six thin per-device files each
  (`tests/_sensortask_scenarios.py` + `tests/test_sensortask_<device>.py`,
  `tests/_webserver_concurrency_scenarios.py` + `tests/test_digital_twin_webserver_concurrency_<device>.py`),
  so each device's own batch runs as its own parallelizable process (~90s / ~45s standalone) and
  `scripts/test.sh`'s override table is empty again. Same scenarios, same devices, same assertions —
  WP1/WP2 untouched. No hardware implication either way — this was purely a CI/test-harness timing
  budget.

## What still needs real hardware — in priority order

> **Status, 2026-09-18: nothing below still needs real hardware. Do not re-run any of it.** Steps 1,
> 2 and 2a were all executed on the `dev` bench on 2026-09-16 by the worker branch
> `claude/real-hardware-boot-latency-measurements` (PR #102, closed unmerged by owner decision —
> these branches were workers, never merge candidates). Their results are migrated and live here now,
> not in that closed PR: the real boot-latency figures and the disproven `webserver` hypothesis are
> in `SPECIFICATION.md`'s boot-latency note (Part A.7), and the one genuinely open part — the
> `CFGMGR_SYSTEM` setup-order fix's unexplained **+0.90s** — is `REAL_HARDWARE_TEST_QUEUE.md`'s R6.
> Step 4 (record the real figures next to the twin ones) is done. **This file is therefore
> deletable by its own criterion above**; it is kept for now only so its §2/§2a reasoning stays
> readable next to the measurement that settled it.


### 1. Boot-to-first-`200` latency, before anything else is decided

**Everything below this point is speculation until this measurement exists.** `SPECIFICATION.md`'s
boot-latency note (search for "Boot-latency note (WP1/WP2") documents ~1.9-2.2s → ~4.5-6.3s →
~6.1s(wozi)/~7.7s(dev) — **all three numbers are digital-twin measurements**
(`digital_twin/_fram_chip.py` is a pure in-memory SPI fake with zero wire time). The note has been
annotated in this branch to say so explicitly and to point here, but the real numbers do not exist
yet.

**What to measure**, on `dev` (the only device ever bench-tested — see CLAUDE.md's WoZi/dev
policy), at three points, each a clean flash + power-cycle, boot-to-first-`GET /status` returning
`200`:

| Point | Commit | What it represents |
|---|---|---|
| Pre-WP | `25e0e19` | Before any of this work — the real baseline |
| WP1 only | `9cf8a9c`'s first parent, or cherry-pick just the WP1 half | Isolates the FRAM-backed-webserver-logger cost alone |
| Current tip | this branch's HEAD | Everything, including WP3–WP8 |

Do **not** substitute a fresh digital-twin run for any of these three — that is the exact mistake
the note's own history shows already happened once (twin numbers get recorded as if they answered a
real-hardware question). If the "WP1 only" checkout is inconvenient to build/flash separately,
measuring pre-WP and current-tip first and treating "WP1 only" as optional follow-up is a reasonable
fallback — but get at least those two.

### 2. If boot latency is worse than expected: the `webserver` lazy-setup hypothesis

**Leading hypothesis, not yet confirmed.** Two independent signals point at the same thing:
- An earlier, since-rolled-back parallel attempt at this exact work wired `WebserverService`'s
  logger to FRAM, measured a real boot-latency regression on real hardware, and deliberately
  reverted it (that PR was titled "webserver deferred, measured regression") — a session with no
  knowledge of this one.
- This branch re-wired it anyway (correctly, per the project owner's decision that WiFi/NTP/webserver
  are all implicitly FRAM-wired) — making it the one module whose FRAM setup call lands in the
  *contended* window (see the mechanism below), i.e. the one module a previous attempt already found
  too slow is now sitting in the worst possible position for contention.

**The mechanism** (already true of the code, independent of whether it turns out to matter): every
FRAM-wired module's logger draws its chunk at construction (instant, bump-pointer), but the real
first chunk read/write happens later, inside that module's own `self.pr.setup()` call — and every
`setup()` call shares one process-wide `asyncio.Lock` (`FRAM_SPI`, `asy_fram_driver.py`).
`sysfunct → fram → conn → ntp → ...`'s own explicit boot setup batch runs every module's setup
*before* any asyncio task starts, so none of those calls ever contend with each other — including
every `SensorReaderConfig`-based module's own `cfgmgr.setup()` (WP2), which rides that same
uncontended batch. `WebserverService` is different: `asy_webserver_service.py`'s `_run()` calls
`await self.pr.setup()` **lazily**, inside the webserver's own task, and `system_service.py`'s
`start_and_check_tasks()` starts every task within one ~1-second stagger window with `webserver`'s
task always **last**. By the time it runs, every other FRAM-wired module's task-start-time FRAM
access is already contending for the same lock, so `webserver`'s first setup queues behind all of
it — and contention scales worse than linearly with chunk count, which went from 7 to 17(wozi)/21(dev)
chunks across WP1/WP2/WP3.

**If step 1's real-hardware numbers show this mattering**, the fix (not yet implemented — deliberately
left for after real measurement, per the review's own ordering): give `WebserverService` a real
`async def setup()` that awaits `self.pr.setup()`, and include `webserver` in `buildgen/codegen.py`'s
`setup_order` so it moves into the uncontended pre-task-start batch like everything else.
`WebserverService` currently has **no** `setup()` method at all — only `_run()` calls `pr.setup()` —
so this is a real gap to fill, not a reorder of an existing call. Keep `_run()`'s own call in place
and idempotent either way (`PrintLogHistoryStore.setup()` already early-returns once
`self.initialized`), so a double-call from both the boot batch and `_run()` is harmless. Re-measure
after, on the same `dev` board, same protocol as step 1.

**If step 1 shows the current numbers are fine on real hardware** (contention theory doesn't
materialize into a real problem at real SPI speeds), leave the code as-is and just correct
`SPECIFICATION.md`'s note to record the real measurement, closing this out as "checked, no change
needed" — a valid outcome, not a failure to find something.

### 2a. Why the slowdown is ~37x, not ~2.5x — root-caused in the mock tier, no hardware needed

The project owner flagged that a ~2.5-3x increase in FRAM-backed loggers per device (7→17/21
chunks) producing a ~37x mock-tier wall-clock slowdown (12s→447s, two independent sessions measured
the same 447s figure) is a disproportionate jump - correctly suspecting a pre-existing mechanism
WP1/WP2 simply exercises much harder, not a new inefficiency in this branch's own code. Confirmed
directly (Unix-port instrumentation, no hardware): **every FRAM-backed logger's one-time `setup()`
call costs a fixed ~170ms, regardless of how little data it actually stores** (`ConfigManager`'s own
FRAM-backed logger, e.g. `CFGMGR_WIFI`, stores a handful of bytes and still costs ~170ms). This cost
is **not new** - it is `PrintLogHistory` `Store`'s existing `_read()`/`_write()` -> `AsyFramManager`'s
chunked read/write path, unchanged by this branch, paid by every FRAM-backed logger that has ever
existed (`SystemService`/`SCD30`/`SGP40`/`BMP3XX`/`Neopixel`/`NotificationCoordinator`'s error logs,
pre-WP). WP1/WP2/WP3 didn't make each instance slower - they added **5-6 more instances** of an
already-expensive fixed cost per device (`CFGMGR_WIFI`/`CFGMGR_NTP`/`CFGMGR_SYSTEM`/`CFGMGR_SGP40`/
`CFGMGR_BMP3XX`/`CFGMGR_NOTIFY`), which is why the visible impact looks so much larger than the
2.5-3x chunk-count growth alone would suggest: 327 real `build_system()` calls (the scenario x
device matrix, as measured then — now `tests/_sensortask_scenarios.py`'s, split across six
per-device files) x ~5.5 new ~170ms operations each is
~305 real seconds of new cost on its own - the dominant share of the measured ~435s increase.
This is fully consistent with, and cross-confirms, `SPECIFICATION.md`'s own already-documented
twin measurement that WP2 alone added ~1.4-1.8s to boot-to-`200` (6 new loggers x ~170ms plus
scheduling overhead lands in that range) - three independent measurements (this mock-tier
instrumentation, the twin's own boot-latency note, and the other session's isolated 12s-vs-447s
commit-boundary measurement) now agree on the same root mechanism.

**One `CFGMGR_SYSTEM` anomaly worth noting while it's fresh**: in the generated boot-setup batch,
`sysfunct.setup()` runs *before* `fram.setup()` (`sysfunct` is first in `buildgen/codegen.py`'s
`setup_order`, `fram` second) - so `SystemService`'s own `cfgmgr.pr.setup()` call finds FRAM not yet
initialized and degrades instantly (0ms in this instrumentation) rather than paying the same ~170ms
every other FRAM-backed logger pays. That's very likely means `CFGMGR_SYSTEM`'s FRAM chunk never
actually gets read/written at boot at all, silently falling back to a failed/uninitialized state
every single boot - the opposite of WP2's own intent for it. **Worth a real-hardware check and,
separately, a closer read of `PrintLogHistoryStore.setup()`'s behavior when `self.fram` is
non-`None` but the owning `AsyFramManager` itself isn't `initialized` yet** - this was found
while investigating the timing question, not chased down further here, since it's a correctness
question for `system_service.py`/`buildgen/codegen.py`'s `setup_order`, not something this file's
own scope (a hardware-measurement handover) should decide unilaterally.

**Whether the underlying ~170ms-per-logger cost itself is excessive** (is `AsyFramManager`'s chunk
read/write path doing more real SPI transactions than a ~10-20 byte chunk should need?) is a
genuinely open, pre-existing question this investigation surfaced but did not chase to ground -
`asy_fram_manager.py`'s `_read_chunk()` loops over the buffer in `check_length`-sized pieces with a
default of 8 bytes, each iteration going through `asy_spi_driver.py`'s real ~2ms-per-transaction CS
settle-time sleep (`await asyncio.sleep(0.001)` on both assert and deassert) - worth a closer look
as separate follow-up work, not assumed to need fixing. **Do not "fix" this by touching
`asy_fram_driver.py`/`asy_fram_manager.py` in response to this note alone** - it's vendored-adjacent,
heavily-audited FRAM logic (SPECIFICATION.md Part C.3.1) and any change there needs its own scoped
review, not a drive-by from a timing investigation.

### 3. Heap-footprint growth (`-X heapsize`) — mock-tier only, resolved, but worth knowing about

Not itself a real-hardware task (the real rp2040 never builds more than one device's own object
graph once per boot — SPECIFICATION.md Part F.1), but kept here so a hardware session doesn't waste
time chasing it as a hardware symptom if it comes up. `scripts/test.sh`'s Unix-port test harness
heap had been raised 8M→32M to accommodate the former monolithic `tests/test_sensortask.py`'s ~330
repeated full-object-graph builds in one process. The underlying growth is real (WP1/WP2's ~2.5x
more `PrintLogHistoryStore` instances per device), but the heap bump itself was a workaround, and
**has since been resolved at the root** (2026-09-17): splitting that file and
`tests/test_digital_twin_sensortask_integration.py`'s own device-generic section by device cut the
worst case sharing one process from ~330/~29 real builds to ~55/~11, and `-X heapsize` came back
down to a measured, validated 16M floor across the whole suite. `scripts/test.sh`'s own
`-X heapsize` comment carries the full account, including the one test whose fixed real-clock budget
(not accumulation) sets that 16M floor. Nothing here has a real-hardware implication either way.

### 4. Once step 1/2 conclude: update `SPECIFICATION.md`

Whatever the real-hardware numbers show, `SPECIFICATION.md`'s boot-latency note needs the real
figures recorded next to the twin figures, explicitly labeled which is which. Don't overwrite the
twin numbers — they're still useful (they show the *shape* of the design's behavior even if not its
absolute real-world cost) — add to them.

## What NOT to do

- Don't revert WP1/WP2. The project owner's own review already confirmed the FRAM chunk growth (7→17
  wozi / →21 dev) is the correct, intentional consequence of approved decisions, not a defect.
- Don't re-run `scripts/build_firmware.py wozi`'s hardcoded pins on the `dev` bench board — CLAUDE.md's
  WoZi/dev policy is explicit that this "tests nothing at all" and has produced false bugs before.
  Use `dev`'s own real entry point/config for every measurement above.
- Don't touch `errno`/`wrnno` numbering in response to anything in this file — that's being handled
  in a separate session per the project owner's direction.
