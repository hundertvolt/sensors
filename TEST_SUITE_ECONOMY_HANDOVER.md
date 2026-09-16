# Test-suite economy handover — wall-clock + heap footprint

Temporary file, same convention as the `WP_RESTART_HANDOVER.md`/`REAL_HARDWARE_HANDOVER.md` pair
that preceded it (both since migrated and deleted): delete once
its findings are either implemented-and-migrated (SPECIFICATION.md Part E, CLAUDE.md, BACKLOG.md)
or confirmed not to apply. Written for a standalone session picking up this one unit of work.

## The task, stated precisely

`tests/test_sensortask.py` (and, separately, `tests/test_digital_twin_webserver_concurrency.py`) got
significantly slower and heavier once WP1/WP2 (implicit FRAM wiring for WiFi/NTP/webserver/every
`ConfigManager`) landed: `test_sensortask.py` alone went from ~12s to ~447s standalone, and the Unix-
port test heap needed raising from 8M to 32M to keep the suite from hitting real `MemoryError`s. Both
are real, root-caused, not bugs in WP1/WP2 itself (see "What's already known" below) — but the
project owner considers both increases disproportionate to what the underlying feature actually
needs, and wants them cut back **significantly**.

**The explicit constraint, stated directly by the project owner: do not reduce any testing.** Every
one of the 54 distinct scenario checks this file already runs, across all 6 real devices, must
remain independently verified. This is about **economizing the mechanism** — how expensively/how
many times the suite exercises the real code to get that same coverage — not about dropping checks,
sampling fewer devices, or weakening assertions. If any change under consideration would reduce
what's actually verified, stop and ask before making it; don't assume the owner would accept the
trade.

## What's already known (measured directly, this session — don't re-derive from scratch)

- **`tests/test_sensortask.py` calls the real `build_system()` 327 times in one process**: 54
  registered scenarios × 6 devices (`_SCENARIOS`/`_DEVICES`, iterated at the bottom of the file) +
  3 standalone test functions. Each of those 327 calls independently constructs the *entire* object
  graph for that device from scratch and runs every module's real `setup()` against the fake
  hardware — even when the scenario itself only checks one narrow thing (e.g. "does `PUT /system`
  with `DebugLevel` propagate to every logger?").
- **Every FRAM-backed logger's one-time `setup()` call costs a fixed ~170ms, regardless of how
  little data it stores** — confirmed by direct Unix-port instrumentation (wrap each
  `await X.setup()` call in the generated `build_system()` with `time.ticks_ms()` timing). This is
  **not new or a regression** — it's `PrintLogHistoryStore`/`AsyFramManager`'s existing chunked
  read/write path (`asy_fram_manager.py`'s `_read_chunk()`, ultimately `asy_spi_driver.py`'s real
  `await asyncio.sleep(0.001)` CS-settle delay on every SPI transaction), paid by every FRAM-backed
  logger that has ever existed. WP1/WP2/WP3 added **5-6 more instances of it per device**
  (`CFGMGR_WIFI`/`CFGMGR_NTP`/`CFGMGR_SYSTEM`/`CFGMGR_SGP40`/`CFGMGR_BMP3XX`/`CFGMGR_NOTIFY`), not a
  new per-instance inefficiency. 327 builds × ~5.5 new ~170ms operations ≈ 305s of new cost — the
  dominant share of the measured ~435s increase.
- **Per-build cost is flat, not growing, across repeated builds in one process** (confirmed:
  30 sequential `build_system()` calls for one device in one process, ~1420ms every single time,
  no upward trend) — this rules out a task-leak/quadratic-accumulation bug as the cause. The cost is
  genuinely proportional to "how many FRAM-backed loggers get built," not to "how many builds have
  already happened."
- **The heap bump (8M→32M) is a workaround masking the same underlying growth, not a fix** — see
  `BACKLOG.md`'s matching entry (search "masking WP1/WP2's real memory-footprint growth"). Not yet
  established by direct measurement exactly where the memory goes (inferred, not confirmed): most
  likely the same 5-6 new `PrintLogHistoryStore` instances per device, held for the life of each of
  the 327 builds' object graphs before being garbage-collected between iterations.
- **A separate, real correctness bug in this exact area was found and fixed in this same session**:
  `sysfunct.setup()` ran before `fram.setup()` in the generated boot sequence, so `CFGMGR_SYSTEM`'s
  own FRAM chunk was never actually read/written at boot (silently degrading instantly instead of
  paying the same ~170ms every other FRAM-backed `cfgmgr` pays) — fixed in `buildgen/codegen.py` by
  reordering `setup_order` so `fram` comes first. This is unrelated to the economy question and
  already done; don't re-investigate it, but do re-verify the fix is still present in whatever
  commit this session starts from (grep `buildgen/codegen.py` for "fram must come before sysfunct").

## Where to look (investigate and confirm — this is a starting list, not a prescription)

1. **Most of `test_sensortask.py`'s 327 builds don't need a *fresh* build.** Many of the 54
   scenarios test one narrow REST-route/behavior concern against *some* correctly-built device, not
   the construction/wiring process itself — for those, any already-built instance of the right
   device would do, as long as no earlier scenario left it in a state that would corrupt the next
   one's assertions. A smaller number of scenarios (e.g. `build_system_constructs_every_real_module`,
   `collect_task_starters_includes_every_constructed_module`,
   `fram_chunk_allocation_order_matches_the_documented_sequence`, the boot-order/watchdog-feed
   scenarios) *do* need to observe construction/wiring/boot-sequencing itself and must keep a fresh
   build. The core question: can the file be restructured so only the scenarios that genuinely need
   a fresh build get one, while the rest share a small number of already-built instances per device
   (ideally one, if state isolation allows) — without silently making any scenario's outcome
   dependent on what an earlier scenario did to that shared instance?
2. **State-isolation risk is the real design problem here, not the mechanics of sharing a build.**
   Scenarios mutate real state (write config files, arm reset timers, flip debug levels, push
   sensor readings). Before sharing instances across scenarios, establish exactly which scenarios
   mutate what, and whether a cheap, explicit reset-between-scenarios hook (not a full rebuild) can
   restore isolation cheaply — or whether some scenarios are irreducibly order-sensitive and must
   keep their own fresh build. Get this right per-scenario; don't assume uniformity.
3. **Whether running every scenario against all 6 devices is itself necessary, or whether some
   scenarios are meaningfully device-invariant enough to check on fewer devices without losing real
   coverage, is a real question — but resolving it in favor of fewer devices is a reduction in
   testing under the owner's own stated constraint unless the owner agrees device-invariance holds.
   Raise this explicitly as a clarifying question; don't decide it unilaterally.**
4. **`tests/test_digital_twin_webserver_concurrency.py`'s own growth (~230s pre-WP1 → ~268s+ now)
   may or may not share this file's root cause** — it drives real-socket concurrency scenarios, not
   327 repeated `build_system()` calls in the same way. Measure it independently; don't assume the
   same fix applies.
5. **`AsyFramManager`'s own chunk read/write path** (`_read_chunk()`'s loop, default
   `check_length=8` bytes per iteration) may be doing more real SPI transactions than a ~10-20 byte
   chunk needs — flagged as an open question, not investigated further, in a prior session (see
   `BACKLOG.md`'s heap-footprint entry and the git history around commit `e47d4e1` on
   `claude/wp-restart-handover-execction` / PR #101 for the full trace). A genuine efficiency win
   here would help real hardware boot time too, not just tests. **This touches heavily-audited,
   CRC/torn-write-resilient FRAM driver code (SPECIFICATION.md Part C.3.1)** — investigate and
   propose, but treat any actual change here as its own scoped unit of work needing explicit
   sign-off, not something to fold into this session's own implementation pass.
6. **Whether the heap bump can come down once (1) is addressed** — fewer concurrently-live full
   object graphs at once may be the real lever, not total builds-over-time. Measure before assuming.

## Explicit non-goals / guardrails

- **Do not reduce scenario coverage, device coverage, or assertion strength to hit a speed/memory
  target.** If a proposed change would do this, stop and ask first.
- **Do not shorten or remove `asy_spi_driver.py`'s real CS-settle delays** (`await
  asyncio.sleep(0.001)`) to make tests faster — that's deliberate hardware-timing fidelity in `src/`
  code shared with real firmware, not test-harness overhead.
- **Do not touch `asy_fram_driver.py`/`asy_fram_manager.py`'s CRC/redundancy/chunking mechanism**
  as a reflexive "make it faster" fix — audited, datasheet-driven code (SPECIFICATION.md Part
  C.3.1); if item 5 above turns up something concrete, propose it and stop, don't implement it
  in the same pass.
- **Do not just raise the heap or per-file timeout further** — those are already in place
  (`scripts/test.sh`, 32M heap / 600s+350s per-file overrides) as safety valves for the current
  state; this session's job is to reduce what they're compensating for, not add more headroom.
- **Follow the standing step-session workflow** (CLAUDE.md "Working agreements" → "Step-session
  workflow"): refine scope into a detailed list with real research first (read
  `tests/test_sensortask.py` in full, read the scenario registration mechanism, measure before
  proposing); ask clarifying questions up front, especially item 3 above; write tests for the new
  sharing/isolation mechanism itself before implementing it (TDD); implement; add coverage for the
  new mechanism; **stop and report back before merging or starting further work** — this is not a
  session that also gets to decide the outcome is good enough to ship on its own.

## Suggested first moves

1. Read `tests/test_sensortask.py` in full, including its own docstring, `_register()`/`_SCENARIOS`
   mechanism, and the `build()`/`_boot()` helpers.
2. Categorize all 54 scenarios: which ones test construction/wiring/boot-sequencing itself (need a
   fresh build) vs. which ones test a narrow behavior against an already-built device (candidates
   for sharing). Do this by reading each scenario's own assertions, not by guessing from its name.
3. Measure the real split of the ~447s: construction-only cost vs. per-scenario assertion cost, per
   category from step 2 — confirms how much wall-clock time is actually recoverable before
   committing to a design.
4. Propose a specific sharing/isolation mechanism (with its own tests) and get sign-off before
   wiring it into the real file.
5. Independently repeat steps 1-4's measurement (not necessarily the same fix) for
   `tests/test_digital_twin_webserver_concurrency.py`.
6. Re-measure suite-wide wall-clock and heap usage before/after, and re-run the full suite at
   `gc.threshold(-1)` with zero `MemoryError`s per CLAUDE.md's standing memory-safety rule before
   it's ever re-run at the project's chosen `gc.threshold(32768)`.

## Context / branch

Base this work on `claude/wp-restart-handover-execution` (PR #101) or whatever it has become by the
time this session starts — check current repository/PR state first rather than assuming. Relevant
docs: `BACKLOG.md`'s heap-footprint entry, `SPECIFICATION.md` Part E (test-tier rationale), CLAUDE.md's
memory-safety ladder and step-session workflow, and this repo's git history around commit `e47d4e1`
(PR #101) for the original timing investigation this handover is based on.
