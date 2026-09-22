# Connection-scaling investigation: plan, findings and evaluation protocol

Working plan for raising the number of simultaneous TCP connections/sockets this firmware can
serve, finding the **maximum still-working number**, and evaluating which combinations of settings
are actually viable. Temporary doc, like `REAL_HARDWARE_TEST_QUEUE.md`: it holds the plan, the
measured results as they land, and the recommendation — and is deleted once its conclusions are
migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`.

Branched off `claude/heap-fragmentation-remediation` at `b109ecc9`, so the whole
heap-fragmentation evidence base (`HEAP_FRAGMENTATION_MEASUREMENTS.md`, `SPECIFICATION.md` Part I)
is available and directly relevant: **every connection added is heap taken away**, and this
project's known defect is contiguity, not total free memory.

## 1. The question

1. How many simultaneous connections can this firmware actually hold, end to end, with every
   top-level requirement still met?
2. Which combination of knobs gets there at the lowest memory cost?
3. Where is the hard wall, and what does hitting it look like (clean rejection vs. degradation vs.
   `MemoryError` vs. watchdog)?

The answer is a **recommended setting plus the measured evidence for it**, not just a bigger
number. A raised ceiling that costs more contiguous heap than it is worth is a failed experiment,
and must be recorded as one.

## 2. Every ceiling in the path, verified against the pinned source

Verified 2026-09-22 against `v1.29.0` as actually fetched into `~/pico-toolchain/micropython`, not
from memory. **Re-verify each one before changing it** — that is the whole point of the anchor
checks in `toolchain/micropython_overrides.py`.

| # | Ceiling | Value today | Where | Injectable how |
| --- | --- | --- | --- | --- |
| 1 | `MEMP_NUM_TCP_PCB` | 5 (lwIP default) | `lib/lwip/src/include/lwip/opt.h`, `#if !defined` guarded | **plain `-D`** — nothing in MicroPython sets it |
| 2 | `MEMP_NUM_TCP_PCB_LISTEN` | 8 (lwIP default) | same, guarded | plain `-D` |
| 3 | `MEMP_NUM_TCP_SEG` | **32** | `extmod/lwip-include/lwipopts_common.h`, inside `#ifndef MEM_SIZE` | see trap A below |
| 4 | `MEM_SIZE` / `TCP_MSS` / `TCP_WND` / `TCP_SND_BUF` | 8000 / 800 / 6400 / 6400 | same block | see trap A below |
| 5 | `MEMP_NUM_UDP_PCB` | `4 + LWIP_MDNS_RESPONDER` = 5 | same file, **plain unguarded `#define`** | see trap B below |
| 6 | `asyncio.start_server(backlog=...)` | **5** (MicroPython default) | `extmod/asyncio/stream.py:179` | one-line `src/` change |
| 7 | `WebserverService(max_connections=...)` | 4 | `src/asy_webserver_service.py:263` | `src/` + `buildgen` |
| 8 | `Request.max_content_length` / `max_body_length` | 2048 each | `src/asy_webserver_service.py` (Part I.6) | `src/` |

### Trap A — `MEM_SIZE` and friends are one atomic group

`lwipopts_common.h` wraps `MEM_SIZE`, `TCP_MSS`, `TCP_WND`, `TCP_SND_BUF` and `MEMP_NUM_TCP_SEG`
in a single `#ifndef MEM_SIZE` block. Defining **only** `MEM_SIZE` on the command line disables the
entire block: `TCP_MSS` silently reverts to lwIP's own 536, `MEMP_NUM_TCP_SEG` to 16, and the
window collapses. Any change here must set the whole group together, and must be verified by
preprocessing the real translation unit — not by assuming the `-D` landed.

### Trap B — the unguarded defines cannot take a plain `-D`

`MEMP_NUM_UDP_PCB` is a bare `#define`, exactly like `MICROPY_ASYNC_KBD_INTR` in B.14.1: a later
plain `#define` beats an earlier `-D`, and the redefinition warning is a hard failure in this build
(warnings are errors). Raising it needs the `VARIANT_DIR`-style include-shim pattern
`apply_unix_kbd_intr_override()` already establishes — generate a header that `#include`s the real
one, then `#undef`/`#define`. Do **not** discover this by trying the `-D` and reading a wall of
build output.

### Correction owed to SPECIFICATION.md Part B.14.2

B.14.2 currently offers `-DMEMP_NUM_TCP_PCB=8 -DMEMP_NUM_NETCONN=8` as the example. **The
`MEMP_NUM_NETCONN` half is a no-op on this port**: `lwipopts_common.h` sets `LWIP_NETCONN 0` and
`LWIP_SOCKET 0`, so the netconn/sockets API is not compiled at all — MicroPython drives lwIP
through the raw/callback API in `extmod/modlwip.c`. B.14.2 also says "does not currently set any of
them", which is true for `MEMP_NUM_TCP_PCB` but false for `MEMP_NUM_UDP_PCB`, `MEMP_NUM_TCP_SEG`
and the `MEM_SIZE` group. Fix that Part as part of this work, with the evidence above.

### The likely real binding constraint

`MEM_SIZE` is **8000 bytes** for lwIP's own heap, while `TCP_SND_BUF` is **6400 bytes per
connection**. The PCB count is cheap; the per-connection send/receive buffering is not. Expect the
wall to be `MEM_SIZE`/pbuf exhaustion (stalled or reset connections under concurrent load), not
"no free PCB". Measure which one actually binds before tuning either — `LWIP_STATS` is `0` today
and turning it on for an experimental build is the direct way to see pool exhaustion instead of
inferring it.

### The other side of the trade

RP2040 has 264 KB SRAM and the Pico W's CYW43 firmware already takes roughly half of it
(Part I.1). Every byte added to lwIP's static pools and its `MEM_SIZE` heap comes **straight out of
the MicroPython GC heap** — the same heap whose contiguity defect this branch's parent has spent
its whole life measuring. So the evaluation is two-sided by construction:

- connections gained, and
- **largest contiguous free block** lost, measured the way `HEAP_FRAGMENTATION_MEASUREMENTS.md`
  already measures it (§0A, §7A), not just `gc.mem_free()`.

A setting that serves 8 connections but leaves the boot survivors unable to place is worse than the
5 we have. State that trade explicitly for every combination tried.

## 3. Mechanism: how the injection is wired

`toolchain/micropython_overrides.py` is the canonical home — read its module docstring and
`SPECIFICATION.md` Part B.14 first. Two shapes already exist to copy:

- **guarded macros** → extra `CFLAGS_EXTRA` in `build_firmware()`
  (`toolchain/setup_toolchain.py:292-302`, which already carries
  `_MBEDTLS_GCC14_ARRAY_BOUNDS_WORKAROUND`).
- **unguarded macros** → a generated out-of-tree header plus a `_DIR`-style redirect, exactly as
  `apply_unix_kbd_intr_override()` does.

Every override gets a `verify_*_anchor()` that fails loudly (`OverrideError`) when the pinned
source no longer matches, and unit coverage in `tests_scripts/test_micropython_overrides.py`
against synthetic fixture trees — no real compile. **Never edit the fetched checkout.**

The settings must be **parameterised, not hardcoded**, because the whole point is sweeping them:
put the target values in `toolchain/versions.toml` (single source of truth, like the MicroPython
`ref`) so one file drives a build, and the sweep is reproducible rather than a sequence of manual
edits.

## 4. What has to change in `src/` and `buildgen/`

- `asy_webserver_service.py::_run()` calls `asyncio.start_server(self._serve, host, port)` with no
  `backlog`, so it inherits **5**. Raising `max_connections` past that is pointless — the accept
  queue drops the rest. Make `backlog` a constructor knob, defaulted coherently with
  `max_connections`, and test that the coupling holds.
- `max_connections` is a constructor default that `buildgen/codegen.py::_emit_webserver()` never
  passes. Make it a per-device `devices/*.toml` key so the sweep is driven from config, and so a
  device with a smaller budget can differ. Keep the `SPECIFICATION.md` Part H.7 reasoning (one slot
  of margin below the lwIP PCB ceiling) intact as a **relationship**, not a frozen number.
- `max_content_length`/`max_body_length` interact multiplicatively: `max_connections` bodies can be
  in flight at once, each one a contiguous allocation (Part I.6). Raising the connection count
  raises the simultaneous contiguous demand by the same factor. This is the single most likely
  source of a new `MemoryError` — treat it as the headline risk, not a footnote.
- The `LockedCounter` admission path (`_serve()`'s reject-when-full) is `O(1)` and fine as is, but
  its *rejection* behaviour is now reachable far more often under the harder tests below. Confirm
  it still never writes a response and never leaks a writer.

## 5. Where the twin can and cannot answer this

**The digital twin runs on the Unix port, which has no lwIP at all** — its sockets are real host
sockets. So the twin can validate everything above the transport (admission, rejection, concurrent
body allocation, task explosion, timeouts, fairness) and **cannot** validate the PCB/`MEM_SIZE`
ceiling. Do not let a green twin run be mistaken for a validated connection ceiling; say so
explicitly wherever a result is recorded.

Two twin-side consequences of more concurrent sockets:

- `digital_twin/unix_port_poll_prewarm.py`'s `_DEFAULT_CEILING = 512` is sized against
  "`max_connections=4` plus background sockets, peaking near 18". Re-derive it, don't just raise
  it — its own docstring calls it a raised threshold rather than a fix.
- `tests/machine.py` / twin fakes and the `-X heapsize` the harness uses (SPECIFICATION.md Part
  E.3.1) may need re-deriving; **root-cause any new `MemoryError` there, never raise the heapsize
  to make it go away.** That history is a standing example against exactly that move.

## 6. Making every tier bite harder

Top-level requirements stay the same or get **harder**; only the load goes up. Concretely, each
tier's concurrency has to scale with the setting under test rather than stay pinned at today's
numbers — several of these files hardcode `4`:

| Tier | Files | What has to change |
| --- | --- | --- |
| Unit (MicroPython) | `tests/test_asy_webserver_service.py`, `tests/_webserver_concurrency_scenarios.py` | Parameterise every hardcoded ceiling (`_make_service(max_connections=...)`, the `range(1, 5)` sweep, the 8-client burst). Add backlog coupling and simultaneous-body-allocation cases |
| Twin (6 devices) | `tests/test_digital_twin_webserver_concurrency_*.py` | Drive bursts at N+1 and 2N+ for the N under test, on every device, not just wozi |
| Twin + real website | `tests/test_digital_twin_real_website_integration.py`, `tests/test_frozen_html_integration.py` | Real page loads concurrently, not one at a time |
| Browser | `tests_js/live-backend.test.js`, `live-backend-put-matrix.test.js`, `scripts/cross_browser_smoke.mjs` | Parallel real-browser sessions against one twin — the closest thing to the real multi-client scenario |
| Bus hazard | `tests/test_digital_twin_bus_hazard_concurrency.py` | API load and bus traffic together at the new ceiling (CLAUDE.md's four-tier bus-hazard rule) |
| Flash/bench (real HW) | `tests_hardware/bench/test_end_to_end_timing.py` (`_max_connections = 4`), `test_network_resilience.py` (`_MAX_CONNECTIONS = 4`, the 24-connection PUT storm), `test_memory_stress_bench.py`, `test_bus_concurrency_under_api_load.py` | Derive the ceiling from the build under test rather than restating `4`; add the sweep that finds the wall |

**The unchanged bar, from CLAUDE.md, applies to every one of these runs:**

- the full suite passes at `gc.threshold(-1)` **and** at `GC_THRESHOLD=32768`, both with **zero**
  `MemoryError` *or* `memory allocation failed` hits — caught-and-degraded included;
- no `gc.collect()` or nonstandard `gc` setting in business logic or test setup (the boot-confined
  I.4(f.1) placement reset is the only exception);
- a caught `MemoryError` that merely didn't crash anything is a **design defect**, not a pass;
- the four `MemoryError` gates stay in agreement
  (`tests_scripts/test_memory_error_gate_agreement.py`);
- lint/typecheck clean, 3-line comment cap everywhere, `method-assign` never suppressed in `src/`.

If a higher connection count can only pass by relaxing any of these, the honest result is **that
count does not work** — record it as the wall.

## 7. The evaluation protocol

1. **Baseline** the current build on every metric below, so every later number has something to be
   compared against.
2. Sweep `MEMP_NUM_TCP_PCB` ∈ {5 (baseline), 6, 8, 10, 12, 16} with `max_connections` = PCB − 1 and
   `backlog` ≥ `max_connections`, adjusting the `MEM_SIZE` group only when the evidence says that
   is what binds.
3. For each combination record: connections actually served concurrently; connections rejected
   cleanly; **largest contiguous free block** and free heap after boot and under load; firmware
   `.bss`/`.data` delta from the map file; any `MemoryError`/`memory allocation failed`; any
   watchdog reset; p50/p95 response time under full load.
4. Find the wall from **both** directions: the highest setting that passes everything, and the
   first setting that fails — and characterise *how* it fails.
5. Recommend one setting, with the trade stated in both directions.

**Real hardware is the only place items 1-5 of §2 can be finally confirmed**, and this session has
**no go-ahead** — CLAUDE.md's gate is per-session and does not carry over. So: build the firmware
(building is not running), do every twin/unit/browser measurement that does not need a board, and
**queue the hardware rows in `REAL_HARDWARE_TEST_QUEUE.md`** with exactly what to run and what to
record. Ask the owner for a go-ahead if one is wanted; do not assume it.

## 8. Standing constraints that bound this work

- `ext/microdot.py` is vendored — no edits, ever. Keep-alive stays unimplemented (Part H.7); a
  connection serves one request and closes. That is *why* concurrency matters here.
- `python/`, `modules/`, the four `build-*.sh` are reference-only, forever.
- Changes to `scripts/`, `pyproject.toml` or `toolchain/` get a `BACKLOG.md` entry for the owner's
  periodic manual chroot run. This work will touch `toolchain/` — that entry is owed.
- Report cross-file discrepancies rather than silently fixing them.
- No test may inflict avoidable wear on real hardware or the host SSD; prove invariants
  structurally rather than by brute-force scale.
