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

---

# 8. Results (2026-09-22)

**No real hardware this session** (owner, 2026-09-22: the bench is not reachable from here). The
lwIP half of every ceiling below is therefore priced from real firmware builds and **not** confirmed
on silicon; `REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` is the runnable form of what is owed,
written standalone for a session with no prior knowledge. Marked `[BUILD]`, `[TWIN]` and `[HW]`
throughout, and there is no `[HW]` yet.

## 8.1 What the mechanism turned out to need

§3 guessed "guarded macros → `-D`, unguarded → generated header". **Both halves go through the
generated header**, because the split cannot be made safely: `py/mkrules.cmake:81` folds
`$ENV{CFLAGS_EXTRA}` into `CMAKE_C_FLAGS`, and CMake emits `<DEFINES> <INCLUDES> <FLAGS>`, so an
`-I` in it lands *after* the rp2 port's own `target_include_directories(... PRIVATE lwip_inc)` and
loses. The redirect that works is `MICROPY_BOARD_DIR`, the rp2 analogue of B.14.1's `VARIANT_DIR`
and the mechanism MicroPython's own porting guide documents. Full account: `SPECIFICATION.md` Part
B.14.2, rewritten with the three corrections §2 owed it.

Two source facts §2 did not have, both verified against the pinned tree:

- `MEMP_NUM_PBUF` (16) and `PBUF_POOL_SIZE` (16) are **also** unset by MicroPython and
  `#if !defined`-guarded, so they belong in the same table. `PBUF_POOL` is the largest single lwIP
  pool in the shipped firmware at 14,275 B.
- **TIME_WAIT pcbs come from `MEMP_TCP_PCB`, the same pool as live connections**
  (`lib/lwip/src/core/tcp.c`'s `tcp_alloc()` only reclaims the oldest TIME_WAIT *after*
  `memp_malloc()` has already failed). Keep-alive is unimplemented, so every request churns one.
  This is why the shipped margin is three slots, not §2's assumed one.

## 8.2 The firmware sweep — `[BUILD]`, real builds, real ELFs

`RPI_PICO_W`, v1.29.0. Baseline `.bss` 46,312 B, `.data` 18,080 B, GC heap
(`__GcHeapEnd - __GcHeapStart`) **197,528 B**. Every option verified in the built translation unit,
not assumed.

| setting | `.bss` | GC heap | delta | TCP PCB pool | `ram_heap` | PBUF pool |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (PCB 5) | 46,312 | 197,528 | — | 983 | 8,019 | 14,275 |
| PCB 6 | 46,508 | 197,332 | −196 | 1,179 | 8,019 | 14,275 |
| PCB 8 | 46,900 | 196,940 | −588 | 1,571 | 8,019 | 14,275 |
| **PCB 10 (shipped)** | **47,292** | **196,548** | **−980** | **1,963** | 8,019 | 14,275 |
| PCB 12 | 47,684 | 196,156 | −1,372 | 2,355 | 8,019 | 14,275 |
| PCB 16 | 48,468 | 195,372 | −2,156 | 3,139 | 8,019 | 14,275 |
| PCB 24 | 50,036 | 193,804 | −3,724 | 4,707 | 8,019 | 14,275 |
| PCB 32 | 51,604 | 192,236 | −5,292 | 6,275 | 8,019 | 14,275 |
| PCB 12 + `MEMP_NUM_TCP_SEG` 64 | 48,196 | 195,644 | −1,884 | 2,355 | 8,019 | 14,275 |
| PCB 12 + `LWIP_STATS` 1 | 48,228 | 195,612 | −1,916 | 2,355 | 8,019 | 14,275 |
| PCB 12 + `MEM_SIZE` 12000 | 51,684 | 192,156 | −5,372 | 2,355 | 12,019 | 14,275 |
| PCB 12 + `MEM_SIZE` 16000 | 55,684 | 188,156 | −9,372 | 2,355 | 16,019 | 14,275 |
| PCB 12 + `PBUF_POOL_SIZE` 32 | 61,956 | 181,884 | −15,644 | 2,355 | 8,019 | 28,547 |
| PCB 12 + the 16000/1460 preset | 66,244 | 177,596 | **−19,932** | 2,355 | 16,019 | 24,835 |

**Every build succeeded, including `MEMP_NUM_TCP_PCB = 32`. There is no compile-time wall in this
range** — §2's expectation that the wall would be a build-level buffer limit is wrong, at least up
to here.

**PCB slots cost exactly 196 B each; buffers cost 5–10x that per unit of benefit.** That single
ratio is what decides the recommendation: the connection count is the cheap knob and the buffer
group is not, so the shipped setting moves only the PCB count and leaves the `MEM_SIZE` group and
the pbuf pools at their pinned values. §2's "likely real binding constraint" — that buffering, not
PCB count, is what binds — remains *plausible* but is now explicitly untested: nothing measurable
here says it binds, and only silicon can say whether it does.

## 8.3 The twin sweep — `[TWIN]`, above the transport only

The Unix port has **no lwIP**, so none of this is a connection-ceiling result. Heap calibrated by
fill fraction the way `HEAP_FRAGMENTATION_MEASUREMENTS.md` §1.4 prescribes: at
`-X heapsize=1200k` the booted `wozi` graph sits **42.8%** full against the board's 44%.
Instrument is `micropython.mem_info(1)` parsed by `tests_hardware/heap_map.py` (§7G.1's
non-perturbing instrument), not the allocating probe.

**Exactness of admission** — at burst = N, every N from 2 to 63 served exactly N with **zero**
rejections. Admission is exact at every count tried.

**The trade, ensembled over 5 runs per setting at burst = 2N:**

| `max_connections` | largest free run, after boot | under load | retained | p50 | `MemoryError` |
| --- | --- | --- | --- | --- | --- |
| 4 | 409,760 | 80,832 | 19.7% | 5.4 ms | 0 |
| 5 | 407,392 | 67,648 | 16.6% | 6.7 ms | 0 |
| 6 | 405,440 | 147,840 | 36.5% | 7.7 ms | 0 |
| **7 (shipped)** | **403,584** | **55,712** | **13.8%** | **9.0 ms** | **0** |
| 8 | 402,464 | 16,032 | **4.0%** | 10.6 ms | 0 |
| 9 | 399,584 | 23,104 | 5.8% | 12.0 ms | 0 |
| 10 | 387,456 | 8,032 | 2.1% | 13.1 ms | 0 |
| 11 | 385,472 | 7,808 | 2.0% | 14.4 ms | 0 |

**The cliff is between 7 and 8** — a 3.5x drop in retained contiguity, reproducible across all five
runs at each setting. N = 6's 36.5% is the placement lottery §1.3 of the measurements document
warns about (it too is stable across its five runs), which is exactly why adjacent settings are
ranked from an ensemble and not from single readings.

**p50 latency grows about 1.3 ms per added connection** under a 2x burst, linearly, all the way out
to N = 63 (83 ms). That is real scheduler cost, not noise, and it is the second reason not to push
the count further than the memory argument alone would allow.

## 8.4 The wall, from both directions — `[TWIN]`

- **Highest setting that passes everything: 63.** Serves 63 of 63 at burst = N and 126 of 126 at
  2N, zero rejections, no allocation failure. Admission itself does not break.
- **First setting that fails: 47, at a 3x burst.** A `MemoryError` allocating 1,017 bytes appears
  **caught and degraded** — the run's own assertions still passed. Under CLAUDE.md I.4(e) that is
  already a failure, not a pass, and it is exactly the silent case that rule exists to catch.
- **How it fails at 63 with a 3x burst: uncaught `MemoryError`** allocating 2,048 bytes, and the
  process dies. Not a clean rejection, not a stall, not a watchdog — heap exhaustion under
  contiguity collapse, on a small allocation.

So the failure mode is **contiguity collapse → `MemoryError` on a 1–2 KB allocation**, first caught,
then fatal. It is not the "no free PCB" wall §2 expected, because the twin has no PCBs at all; on
silicon that wall may well arrive first, and §5's warning stands — **a green twin run is not a
validated connection ceiling.**

## 8.5 Recommendation, and the trade in both directions

**`max_connections = 7`, `MEMP_NUM_TCP_PCB = 10`, `backlog = 8`, every buffer left alone.**
Shipped on all six devices (owner's decision, 2026-09-22).

**For it.** 75% more simultaneous connections for **980 B** of the 197,528 B GC heap — 0.50%.
Admission stays exact at 7; the three-slot PCB margin covers the accept-queue arrival being refused
plus TIME_WAIT churn from a design with no keep-alive; the backlog coupling closes a ceiling that
was fiction above 5 whatever `max_connections` said. Zero `MemoryError` at either gc threshold,
across every tier, at the shipped value.

**Against it.** Under a 2x overload burst the twin retains 13.8% of its after-boot largest
contiguous free block, against 19.7% at `max_connections = 4` — a real 30% relative loss of
contiguity on a project whose known defect *is* contiguity. p50 latency under that burst goes from
5.4 ms to 9.0 ms. And the lwIP half is unconfirmed: if the board's PCB pool or pbuf supply binds
before 7, the firmware will refuse connections its own config admits, which reads as an application
bug and is not one — that is precisely what the handover's §4 row exists to catch.

**Why not 8, which the connection count alone would have allowed.** 8 costs another 3.5x of
retained contiguity for one more connection. A setting that serves more connections but leaves the
boot survivors unable to place is a worse setting, and 8 is where that starts on the only evidence
available. If silicon disagrees, the number moves — the *relationship* in Part H.7 is what this
branch fixes, not the number.

## 8.6 What each tier does now, against §6's table

Every row derives the ceiling from the build under test rather than restating a literal, so raising
a device's own `max_connections` makes these bite harder instead of leaving them pinned.

| Tier | Done |
| --- | --- |
| Unit (MicroPython) | `_make_service(max_connections=...)` already parameterised; **Section G added** — the backlog default, an explicit backlog, the clamp when one is too shallow, and that the value really reaches `start_server()` rather than merely being stored. 163/163 |
| Twin (6 devices) | `_ceiling(module)`/`_backlog(module)` read off the real service; every burst now scales (exactly N, 2N, 3N, N of each kind, the 1..N sweep, held-open slots). **Two scenarios added**: the accept queue covering the ceiling, and a full ceiling of simultaneous request bodies. 17/17 per device |
| Twin + real website | **Row added**: a full ceiling's worth of *real* page loads concurrently (index + bundled `app.js`, the real 2-connections-per-tab footprint), asserting every tab got identical, non-truncated content |
| Browser | **`runLiveBackendConcurrentTabs` added**: parallel real Chromium tabs against one live twin, tab count derived from `devices/wozi.toml`, and every tab must load — not "at least one" |
| Bus hazard | **Two rows added** (wozi and dev): a full-ceiling REST burst landing mid-run while every sensor task is on the shared bus. The file needed `prewarm_poll_set()` for the first time — real client connections grow the Unix port's pollfds array, which is a segfault, not a failure. 12/12 |
| Flash/bench (real HW) | `configured_max_connections()` and `discover_max_connections()` added to `harness.py`; `test_end_to_end_timing.py`, `test_network_resilience.py` (including the PUT storm's repeat count), `test_memory_stress_bench.py` and `test_bus_concurrency_under_api_load.py` all derive from it. **One row added**: the board must admit exactly what this tree configures |

**Not changed, and why**: `scripts/cross_browser_smoke.mjs` stays single-session. Its own scope note
is that each real WebDriver round trip costs seconds and it is deliberately not a second exhaustive
matrix; the concurrency question is answered by the Chromium tier above, and engine diversity is
what that script exists for. Say so rather than widening it.

**The unchanged bar held**: `scripts/test.sh` and `GC_THRESHOLD=32768 scripts/test.sh` both pass,
85/85 MicroPython files and 1,496 pytest tests each, with **zero** `MemoryError` *or*
`memory allocation failed` in either run's captured output. Lint and all three typecheck passes
clean. One ratchet moved: `max-args` 22 -> 23, for the `backlog=` kwarg, which `pyproject.toml`'s own
comment sanctions as a deliberate reviewed one-parameter addition — flagged rather than done quietly.


---

# 9. Correction: the options are an ensemble (owner, 2026-09-22)

§8 priced the ceiling with only `MEMP_NUM_TCP_PCB` moved, concluded "PCB slots are cheap and
buffers are not", and recommended moving nothing else. **That was wrong, and the owner named it.**
lwIP's options are not independent, and the configuration §8.5 recommended could accept connections
it could not actually serve.

## 9.1 What the source says, verified

`lib/lwip/src/core/init.c` turns **nine** relationships between these options into compile-time
`#error`s, and `opt.h` **derives** four further values from the ones this override sets —
`TCP_SND_QUEUELEN`, `TCP_SNDLOWAT`, `TCP_SNDQUEUELOWAT`, `PBUF_POOL_BUFSIZE`. Both are now mirrored
in `toolchain/micropython_overrides.py` (`check_lwip_ensemble()`, `derive_lwip_dependents()`), so an
incoherent set is refused by name before it compiles.

**MicroPython's own pinned block is itself a tuned set**, and it sits *exactly* on one of those
boundaries: `MEMP_NUM_TCP_SEG` is 32, and the derived `TCP_SND_QUEUELEN` is
`(4 x 6400 + 799) / 800` = **32**. Nothing about 8000 / 800 / 6400 / 6400 / 32 is arbitrary, and
nothing in it can be moved alone.

## 9.2 The two relationships lwIP does not check, which are the ones that bind

lwIP's own checks size the shared pools for **one** connection. This firmware admits
`max_connections` at once, and both of the pools involved are **global**:

- **`MEMP_NUM_TCP_SEG` is global; `TCP_SND_QUEUELEN` is per connection.** At the pinned values one
  connection can drain the whole 32-segment pool. The rest then hold data the stack has accepted
  and cannot push — *admitted but not served*, which is precisely the failure the owner asked to
  rule out. The override now requires
  `MEMP_NUM_TCP_SEG >= max_connections x (TCP_SND_BUF / TCP_MSS)`.
- **`MEM_SIZE` is the arena every outbound byte passes through.** Traced through the real source:
  `extmod/modlwip.c:802` calls `tcp_write()` with `TCP_WRITE_FLAG_COPY` **unconditionally**, so the
  payload is copied into a `PBUF_RAM` pbuf, and `pbuf_alloc()` takes `PBUF_RAM` from `mem_malloc()`
  — the `MEM_SIZE` heap. Its per-connection share must not fall below the 2,000 B the 4-connection
  design gave (8000 / 4).

Run against what §8.5 recommended, both fail:

```
MEMP_NUM_TCP_SEG (32) < max_connections * (TCP_SND_BUF / TCP_MSS) (56)
    - 7 connections cannot each hold a full send window
MEM_SIZE (8000) leaves 1142 B per admitted connection, below the 2000 B floor
```

`PBUF_POOL_SIZE` is deliberately **not** scaled: it backs the *inbound* path, where demand is one
small request per connection (bodies capped at 2,048 B), against ~978 B of GC heap per pbuf — the
most expensive pool to grow. Stated rather than assumed; a `LWIP_STATS` row in the hardware handover
is what would settle it.

## 9.3 The honest cost — `[BUILD]`, coherent ensembles only

Each point is a **complete** set derived from its ceiling (`MEMP_NUM_TCP_PCB` = N + 3,
`MEMP_NUM_TCP_SEG` = N x 8, `MEM_SIZE` = N x 2000, the rest pinned), not one knob moved alone:

| `max_connections` | PCB | SEG | `MEM_SIZE` | `.bss` | GC heap | vs pinned | % of heap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 7 | 32 | 8,000 | 46,704 | 197,136 | -392 | 0.20% |
| 5 | 8 | 40 | 10,000 | 49,028 | 194,812 | -2,716 | 1.37% |
| 6 | 9 | 48 | 12,000 | 51,352 | 192,488 | -5,040 | 2.55% |
| **7 (shipped)** | **10** | **56** | **14,000** | **53,676** | **190,164** | **-7,364** | **3.73%** |
| 8 | 11 | 64 | 16,000 | 56,000 | 187,840 | -9,688 | 4.90% |
| 9 | 12 | 72 | 18,000 | 58,324 | 185,516 | -12,012 | 6.08% |
| 10 | 13 | 80 | 20,000 | 60,648 | 183,192 | -14,336 | 7.26% |

**A servable connection costs 2,324 B of GC heap — twelve times the 196 B §8.2 measured for a PCB
slot alone.** §8.2's per-option table is not withdrawn; it is just not the figure that decides
anything. "PCB slots are cheap" is true and irrelevant.

## 9.4 What this changes about the recommendation

**The setting is unchanged — `max_connections = 7` — and the reasoning for it is now stronger, not
weaker.** Two independent curves stop in the same place:

- the twin's contiguity cliff, 13.8% retained at 7 against 4.0% at 8 (§8.3, unaffected by this
  correction: the Unix port has no lwIP at all);
- the ensemble cost, crossing 4% of the GC heap between 7 and 8.

What changes is the **price**: 3.73% of the GC heap, not the 0.50% §8.5 claimed. The trade stated
in both directions, corrected: 75% more connections, each of which the stack can genuinely push,
for 7,364 B of GC heap and a ~30% relative loss of largest-contiguous-free under a 2x overload
burst. `max_connections = 4` at a coherent ensemble costs only 392 B, so the whole price of this
change is the six thousand-odd bytes between them.

## 9.5 Serving, not just surviving

The owner's second point: a setting must not merely bear the load, it must actually **serve** every
connection it offers. Two scenarios now assert that directly, on all six twin devices, rather than
inferring it from a status count:

- **`every_admitted_connection_is_actually_served_a_complete_correct_response`** — the full
  ceiling's worth of the heaviest real endpoints, three rounds back to back, each answered 200 with
  a body that parses to a non-empty dict inside a bounded time. A count of 200s would pass a
  truncated stream or a response that arrived minutes late; this does not.
- **`a_full_ceiling_of_real_page_loads_is_served_without_truncation`** — an uncontended load first,
  as the reference byte count, then the whole ceiling concurrently, every one of which must match
  it exactly. `ext/microdot.py` streams a file in `send_file_buffer_size` chunks, so a stack out of
  buffers mid-response **truncates rather than failing**, which is invisible to a status check.

Both are mount-independent, so they mean the same thing under the stub and the real website.

## 9.6 And the shim itself

Two hardenings, from the owner's first point — the override must survive a compatible MicroPython
release and fail loudly on an incompatible one:

- **A sentinel.** The generated header defines `MICROPY_SENSORS_LWIP_OVERRIDE_APPLIED`, and the
  post-build check demands it. Value comparison alone could not catch a shim that was never
  *found*: a build asking for values that happen to equal MicroPython's defaults would verify clean
  against a firmware the override never touched. It now fails.
- **The atomic-block trap is structurally impossible in this design, not merely checked.** The
  generated header `#include`s the real `lwipopts.h` *first*, so the `#ifndef MEM_SIZE` block
  executes in full with every upstream value intact, and only then are the options redefined. A
  future release adding a sixth macro to that block keeps its upstream value rather than losing it
  — the failure mode a command-line `-D` would have produced.


---

# 10. A real defect the harder bursts found (2026-09-22)

The point of §6 was that the tiers should *bite harder*, not merely tolerate more load. They did,
and the first thing they bit was this project's own twin HTTP client.

**The failure.** `test_digital_twin_webserver_concurrency_arzi.py` failed the (f) stage —
`gc.threshold(32768)` — while the (e) stage passed on the same tree, in
`high_concurrency_burst_at_historical_segfault_repro_scale_survives`:

```
ValueError: malformed HTTP status line: b''
```

**Root cause.** A connection refused by `_serve()`'s reject-when-full branch is closed **without a
response ever being written**, and the peer sees either an RST or a clean FIN — kernel TCP state
that `src/` does not choose. The RST arrives as an `OSError`, which every scenario's rejection
handler catches. The FIN arrives as an *empty read*, which `digital_twin/_http_client.py`'s
`parse_status_line()` raised as a `ValueError` — and eight call sites caught only `OSError`, so it
escaped as a test failure. **The bug is in the test client, not in `src/`.**

It surfaced now because this branch changed that scenario's burst from a fixed 12 to
`max(12, ceiling * 3)` = 21, which made FIN-without-bytes the common refusal rather than a rare one.
It is intermittent by nature, which is why it showed at (f) and not (e) — the shifted timing, not
the threshold itself.

**The tier that already had this right.** `tests_hardware/http_client.py` has carried the concept
since the bench runs: `CEILING_CLOSE` includes `http.client.BadStatusLine` precisely because an
empty status line *is* a ceiling refusal there, with a comment saying so and citing the measured
FIN/RST split. The twin client simply never learned it — a genuine cross-tier inconsistency.

**The fix, at the source rather than in eight `except` clauses.** `parse_status_line(b"")` now
raises `CeilingRefusedError`, an `OSError` subclass, so every existing call site classifies it
correctly without change and the meaning is explicit. A non-empty malformed line still raises
`ValueError`, and the body-read `EOFError` paths are untouched: those happen *after* a status line,
so they mean a truncated response, which is a real defect and must not be reclassified as a refusal.

**Verified**: the failure reproduces on the unfixed tree in a worktree, and all six devices pass
three consecutive (f)-stage rounds with the fix. `tests/test_digital_twin_http_client.py` pins both
halves — the refusal is raised, and it is catchable as a plain `OSError`.


## 10.1 The CI flake this branch could not reproduce, and the channel built to catch it

**The shape of it.** Six of this branch's twelve CI runs went red, and never twice in the same
place: `unit-tests` on three, `Unit tests (shipped gc.threshold)` on two, `unit-tests-coverage` on
one, with `d0ba4c2`, `73fcb68` and `50d47d1` fully green in between. All three lanes run the same
MicroPython suite, so that is one flaky suite, not three broken lanes - and the first red run is
`9751814`, the commit that raised the ceiling and scaled every burst to it. The correlation points
at this branch's own concurrency scenarios. It is a correlation; nothing here proves it.

**The log is unreachable from this environment.** GitHub serves runner logs from
`productionresultssa*.blob.core.windows.net`, and the gateway answers 403 to CONNECT for that host
(`connect_rejected`, policy - visible in `$HTTPS_PROXY/__agentproxy/status`). Job summaries are not
in the REST API either, verified by reading a failing check run's empty `output.summary`. The
github.com log endpoints the web UI uses answer 403 to a token. What *is* served is **check-run
annotations** - so `scripts/test.sh` now emits one `::error` per red outcome: a failed file with the
last 40 lines of its own captured output, a file that only logged an allocation failure, and the
pytest tier. Guarded on `GITHUB_ACTIONS`, so a local or clean-chroot run is unchanged.

**What reproduction attempts ruled out.** None of these reproduced a single failure:

| attempt | shape | result |
|---|---|---|
| Six concurrency files together, 9 rounds | 54 file runs, unfixed tree | 0 failures |
| Full suite, `TEST_PARALLELISM=32` | 2x CI's oversubscription | 85/85, 0 markers |
| Full suite, `taskset -c 0,1` | 2 cores x 4 = 8 jobs, a runner's exact shape | 85/85, 0 markers |
| Per-scenario timing, 6 devices on 2 cores | the wall-clock-budget hypothesis | see below |
| The same six files under `build-settrace` | the `unit-tests-coverage` lane specifically | 19/19 x 6, 0 markers |

The timing run kills the budget hypothesis outright: under 3x oversubscription on two cores,
`every_admitted_connection_is_actually_served_a_complete_correct_response` takes **2.5 s against
its 40 s budget**, consistent to within 60 ms across all six devices, and the heaviest scenario in
the file is 6.8 s against 60 s. No `run_timed()` budget is anywhere near firing.

The coverage lane is not the exception it looks like either. `build-settrace` inflates
*allocations* 4-5x (Part E.5.2), but these scenarios are dominated by real network waits rather
than traced execution, so the **wall-clock** inflation measured here is only **1.32x** - 47.6 s
against 36.2 s for the same six files under identical contention. Every budget keeps at least 4x
headroom in that lane too, including the two tightest ratios in the file
(`a_slot_freed_by_a_stale_connections_timeout...` at 5.8 s of 30 s, and the segfault-repro-scale
burst at 6.8 s of 60 s). The per-file 240 s timeout is never in reach either: a whole file is
36-48 s under 3x oversubscription.

**What was changed, and what it is not.** The scenario that demands the whole ceiling three times
in a row now starts each round from an asserted zero rather than a hoped-for one: `_drained()`
polls the service's own `_open_conns` counter to zero with a bounded budget, and the scenario
asserts it got there. This is motivated by Part I.6 - a slot is released in `_serve()`'s `finally`,
*after* the close is awaited, so it outlives the response the client already holds - and it is
strictly stronger than what it replaces: a slot that never comes back now fails immediately with
its own message, proven by a control arm that forces the counter to read non-zero and sees both
scenarios fail as intended. It costs ~70 ms, against the ~1 s a blind sleep would have cost.

**It is a hardening, not an established fix.** The lag it removes was never observed locally: a
direct mechanism probe measured 0 refusals with and without a settle, and the drain returns on its
first poll. Whether it is what CI was hitting is unknown until the annotations catch a real one.

**An earlier attempt to make this diagnosable was made and reverted, and the reason matters.**
`scripts/test.sh` was changed to append its verdict to `$GITHUB_STEP_SUMMARY`. That was wrong three
times over: `tests_scripts/test_test_sh.py` deliberately extracts the verdict block and runs it
standalone with only three variables set, so the new block hit `set -u` on the others and broke a
real test; a nested `scripts/test.sh` inherits the variable and appends to its parent's summary;
and - the deciding one - the job summary is not exposed through any API this environment can reach,
so the channel would never have delivered what it promised. Reverted in full; the annotation
channel above is the replacement, and its escaping and its "a missing log must never abort the run
it reports on" property are executed against the real extracted source line rather than asserted by
eye.
