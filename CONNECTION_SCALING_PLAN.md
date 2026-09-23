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

**Exactness of admission** — at burst = N, every N from 2 to 63 served exactly N with **zero**
rejections. Admission is exact at every count tried. This part is deterministic and stands.

**The latency claim is withdrawn too — see §8.3.2.** An earlier version reported "p50 grows about
1.3 ms per added connection" and used it as the second argument for 7. The sweep's burst was `2N`,
so the offered load grew with the setting under test; at fixed load the effect disappears.

### 8.3.1 The contiguity measurement was wrong, and is withdrawn

An earlier version of this section reported a "3.5x cliff in retained contiguity between 7 and 8"
and made it the deciding argument for `max_connections = 7`. **That result was an artifact.** Three
compounding defects, found by re-reading the harness after the owner asked how and when contiguity
was being sampled:

- **The sample was taken after the burst, not during it.** The probe ran once both
  `await asyncio.gather(...)` calls had completed and every connection was already closed, so it
  measured allocator residue at an uncontrolled GC state. Peak concurrent pressure was never
  sampled at all.
- **The instrument perturbed what it measured**, and this document misdescribed it. It was a
  doubling-then-bisecting `bytearray` probe — it allocates the largest block it can find and frees
  it, changing the fragmentation state. The text claimed `mem_info(1)` parsed by
  `tests_hardware/heap_map.py`, the documented non-perturbing instrument. It was not used, and
  `heap_map.py`'s own `gaps_at_least(size)` — the metric that matters — was sitting unused.
- **The normalisation hid the answer.** "% of the after-boot largest free run" turned 16,032 B into
  a "4.0% cliff". Against the 2,048 B that microdot's `readexactly()` allocates contiguously per
  connection (`max_content_length`, `asy_webserver_service.py:262`), that is 7.8x headroom — which
  is why function in fact survived to N = 46.

The tell was in the published table and was rationalised instead of investigated: the series was
non-monotonic (N = 6 above N = 4, N = 9 above N = 8). N = 6 was explained away as "the placement
lottery" while the adjacent 7-to-8 step was read as signal. Noise that can produce a 2.6x rise can
produce a 3.5x fall.

**Re-measured correctly** — sampling at true peak with all N connections parked mid-body in
`readexactly()` (asserted, `held = N`), `mem_info(1)` captured and parsed host-side by
`heap_map.py`, reporting placement capacity for 2,048 B blocks, 5 repeats per setting:

| N | placement slots >= 2048 B, per repeat | spread | median |
| --- | --- | --- | --- |
| 4 | 18, 19, 20, 24, 24 | 6 | 20 |
| 6 | 9, 12, 12, 14, 15 | 6 | 12 |
| 7 | 11, 11, 13, 18, 19 | 8 | 13 |
| 8 | 5, 9, 11, 13, 16 | 11 | 11 |
| 10 | 5, 9, 11, 13, 13 | 8 | 11 |
| 12 | 5, 6, 7, 11, 17 | 12 | 7 |
| 16 | 4, 8, 9, 10, 13 | 9 | 9 |

**The within-N spread exceeds the between-N step for every adjacent pair**, so no adjacent pair is
resolvable:

| pair | median step | within-N spread | resolvable |
| --- | --- | --- | --- |
| 4 vs 6 | 8 | 6 | yes |
| 6 vs 7 | 1 | 8 | no |
| **7 vs 8** | **2** | **11** | **no** |
| 8 vs 10 | 0 | 11 | no |
| 10 vs 12 | 4 | 12 | no |
| 12 vs 16 | 2 | 12 | no |

Correcting the sample point and the instrument was **not** enough: largest-free-run still fails a
monotonicity check even when sampled at true peak, and placement-slot count passed that check at 3
repeats only to fail it at 5. The honest conclusion is that **this metric resolves coarse
differences (4 versus 6) and cannot rank adjacent connection counts at all** at any repetition
count this project would pay for. Any future use of it needs its within-N spread established first,
and only differences larger than that spread may be read as signal.

### 8.3.2 The latency claim is withdrawn: the load grew with the setting

The sweep fired `burst = max_connections * multiplier`, so N = 4 was offered 8 requests and N = 11
was offered 22. "p50 grows 1.3 ms per added connection" therefore measured **latency when you also
offer twice as many requests**, not the cost of a larger ceiling. The independent variable was
entangled with the load — the same defect as §8.3.1, in a different dress.

The per-setting data was otherwise sound (5 repeats, medians 5.4, 6.7, 7.7, 9.0, 10.6, 12.0, 13.1,
14.4 ms for N = 4…11, monotone over all eight points, within-N spread 0.5 ms on the clean rows).
Monotone-over-eight is strong evidence of *something*; it just is not evidence about the ceiling.

**Re-measured at fixed offered load** — concurrency pinned at 4 for every setting, 25 rounds,
3 repeats, only served requests counted:

| `max_connections` | 4 | 7 | 8 | 12 | 16 |
| --- | --- | --- | --- | --- | --- |
| p50 (ms), per repeat | 4.69 4.30 4.53 | 4.68 4.54 4.40 | 4.17 4.23 4.25 | 4.27 4.40 4.37 | 4.36 4.28 4.22 |

**Flat.** The variation across settings (~0.3 ms) is smaller than the variation within one (~0.4 ms),
and if anything the higher ceilings are marginally faster. **Raising the ceiling costs no latency at
fixed load**, which is the question the decision actually needed answered. The rising curve was the
load, not the setting.

### 8.3.3 What a connection really costs — and why only one of the two numbers counts

Two costs, and they are **not the same kind of cost**. An earlier version of this section added them
together and reported "peak occupancy 27.6% → 31.9%", which treats transient allocation as if it
were permanently committed budget. It is not, and the distinction is the whole point.

**Permanent — 2,324 B per connection, survivor-class.** `.bss` grows by exactly that per added
connection across `max_connections` 4→16, **every step identical, zero variance**: arithmetic on
static array sizes from real ELFs, not a sample. It shrinks the GC heap available to everything
else, forever, whether or not the connection is ever used. This is the number that belongs in the
same conversation as boot survivors, and **it is the cost of the decision**.

**Transient — about 5,170 B live per connection while it is being served**, plus ~12,500 B of churn
the collector reclaims. It occupies the heap only between accept and close. Measuring it against a
survivor budget overstates it, because the heap gets it all back:

| N | requests served | total left behind after | per connection-cycle | gaps >= 2048 B, before → after |
| --- | --- | --- | --- | --- |
| 4 | 40 | 1,472 B | 36.8 B | 23 → 24 |
| 7 | 70 | 1,632 B | 23.3 B | 23 → 24 |
| 8 | 80 | 1,632 B | 20.4 B | 23 → 26 |

Ten rounds of N concurrent served requests, **one fresh process per repeat** (a shared process makes
a survivor number meaningless: each repeat inherits the last one's state, which produced *negative*
survivor deltas in a first attempt), both samples post-collect. The residue is **flat in total, not
per connection** — the same ~1.6 KB whether 40 or 80 requests were served — so it is one-off
lazily-created state, not per-connection accumulation. Placement capacity is unchanged or slightly
better afterwards, so the churn leaves no lasting fragmentation either.

**So the question to ask about transient allocation is not "how much budget does it eat" but "at
peak, are there enough sufficiently long free pieces to satisfy the whole simultaneous demand?"** —
a heap does not need to be unfragmented, it needs enough gaps of the right size. That is
`gaps_at_least(2048)` against N plus the response path (§8.3.1's corrected metric), not a fraction
of total heap.

**The decision figure for 7→8 is therefore 2,324 B permanent, not the 7,488 B a previous version of
this document claimed.** The transient 5,170 B is real but returned, and is bounded by placement
capacity rather than by budget.

**Caveat.** The transient figures are `[TWIN]`. MicroPython object sizes do not depend on heap size,
so they should transfer, but the twin has 1,200 KB where the board has ~190 KB — the *placement*
question is far tighter on silicon even though the *budget* question is not.

## 8.4 The wall — connections alone, and then with everything hammering

### 8.4.1 Connections alone — `[TWIN]`, and far too optimistic

- **Highest setting that passes: 63.** Serves 63 of 63 at burst = N and 126 of 126 at 2N.
- **First setting that fails: 47**, at a 3x burst: a `MemoryError` allocating 1,017 bytes appears
  **caught and degraded**, which under CLAUDE.md I.4(e) is already a failure.
- **At 63 with a 3x burst it is fatal**: uncaught `MemoryError` on 2,048 bytes, the process dies.

**These numbers describe a system doing nothing else, and that is not the bar.** §8.4.2 measures the
same thing with every module competing for the heap and lands roughly 3x lower. Read 47 and 63 as
an upper bound on the transport-facing path in isolation, never as the device's capacity.

### 8.4.2 Every module hammering at once — the real bar, `[TWIN]`

The owner's hardest requirement: maximum concurrent allocation pressure **from all sides at once**,
with **no `MemoryError` at `gc.threshold` unset**. The load is the real `sensortask_wozi` graph with
every timer and task started — three sensor drivers on the shared I2C bus, FRAM on its own SPI,
WiFi, the watchdog feed — plus six rounds of a full-ceiling REST burst landing mid-transaction, at
a heap sized to the board's own 44% fill fraction (§1.4's calibration, `-X heapsize=1200k`). Pass
requires **every** request served (not merely survived), every sensor still returning real data,
FRAM re-probing present, the watchdog never starved, and zero markers of either spelling.

| `max_connections` | requests served | sensors + FRAM | watchdog | `MemoryError` |
| --- | --- | --- | --- | --- |
| **7 (shipped)** | **42 / 42** | ok | never starved | **0** |
| 10 | 60 / 60 | ok | never starved | 0 |
| 14 | 84 / 84 | ok | never starved | 0 |
| 16 | 96 / 96 | ok | never starved | 0 |
| **18** | **108 / 108** | **ok** | **never starved** | **0** |
| 19 | — | — | — | **1** |
| 20 (x2) | — | — | — | **1** each |

**The bar is 18, against 47 for connections alone** — 19 fails, and 20 fails identically on both
repeats. The shipped 7 therefore keeps roughly a 2.5x margin under all-sides pressure, not the 6.7x
the isolated figure implied.

**One confound, and it is not small.** The failure at 19 and 20 alike is
`MemoryError: memory allocation failed, allocating 5509 bytes` inside
`digital_twin/_http_client.py`'s `_read_exact` — **the test client, not the firmware**. On the twin
both live in one process and share one heap, and at N = 20 the client is holding 20 concurrent
~5.5 KB response bodies, about 110 KB, beside the server it is testing. N = 18 passes with 163 KB
still free, so this is a transient spike rather than exhaustion. **So 18-20 is the bar for
*client-and-server-in-one-heap*; the device's own bar is higher and this tier structurally cannot
measure it.** On hardware the client is an external host and the confound disappears, which is the
sharpest reason the handover's bisection is the authoritative measurement rather than a formality.

### 8.4.3 How much free heap a connection needs

Separately from the count: how full can the heap already be and still serve a full ceiling? Ballast
of long-lived 512 B blocks (survivor-class, and small enough that the remaining free space is
genuinely broken up), then three rounds of a full ceiling of `PUT` requests with real bodies:

| free per connection | free at start | served | `MemoryError` |
| --- | --- | --- | --- |
| 65,536 B | 458,688 | 21 / 21 | 0 |
| 32,768 B | 229,120 | 21 / 21 | 0 |
| 16,384 B | 114,336 | 21 / 21 | 0 |
| **12,288 B** | **85,632** | **21 / 21** | **0** |
| 10,240 B | 71,488 | 18 / 21 | 3 |

**About 12 KB of free heap per admitted connection**, at `gc.threshold(-1)`. That is the live 5,170 B
(§8.3.3) plus room for the churn, which at the default threshold is not collected until an
allocation has already failed. At N = 7 the requirement is 86,016 B; the board boots 44% full [HW],
leaving ~106,500 B of its 190,164 B heap — so it **fits with roughly 24% margin**.

**Setting the threshold does not buy headroom here.** At 12,288 B per connection with
`GC_THRESHOLD=32768`, 0 of 21 were served — with **zero** memory markers, so those are timeouts from
collection frequency on a nearly-full heap, not allocation failures. At 8,192 B it was worse than
the default (10/21 and 9 markers, against 11/21 and 5). Consistent with CLAUDE.md's standing rule
that the threshold is defence in depth and never the fix.

## 8.5 Recommendation, and the trade in both directions

**`max_connections = 7`, `MEMP_NUM_TCP_PCB = 10`, `backlog = 8`, every buffer left alone.**
Shipped on all six devices (owner's decision, 2026-09-22).

**Two of the three original arguments did not survive scrutiny** (§8.3.1, §8.3.2). The contiguity
"cliff between 7 and 8" was an artifact of sampling after the burst with an allocating probe, and
re-measured correctly the metric cannot rank adjacent settings at any repeat count worth paying
for. The "1.3 ms per added connection" was an artifact of a sweep whose offered load scaled with
the setting; at fixed load, latency is **flat** from 4 to 16. Neither is evidence against 8.

**What the decision actually rests on, after that:**

- **Permanent memory, and only that.** A connection costs **2,324 B of `.bss` forever**, whether
  used or not — exact, zero variance, from ELF sizes. Going 7→8 costs **2,324 B permanently, 1.2%
  of the GC heap**. Its ~5,170 B of live runtime allocation is **transient**: measured in a fresh
  process, 70 served requests leave ~1.6 KB behind in total — flat, not per connection — and
  placement capacity is no worse afterwards (§8.3.3). Transient allocation is bounded by whether
  the heap has enough gaps of the right size at peak, not by a budget, and must not be added to a
  survivor figure. An earlier version of this section did exactly that and inflated the cost of
  7→8 to 7,488 B.
- **The PCB margin is architectural, not measured**: three spare slots cover the over-ceiling
  arrival `backlog` deliberately queues to be refused, plus TIME_WAIT churn in a design with no
  keep-alive, where every request burns a pcb (§2).
- **Admission is exact at 7**, deterministic, at every tier, and the backlog coupling closes a
  ceiling that was fiction above 5 whatever `max_connections` said.
- **Zero `MemoryError`** at either gc threshold, across every tier, at the shipped value.

**Against it.** The lwIP half is unconfirmed: if the board's PCB pool or pbuf supply binds before 7,
the firmware refuses connections its own config admits — which reads as an application bug and is
not one. And the runtime half of the cost figure is `[TWIN]`; object sizes should transfer, but that
is an argument, not a measurement.

**Why not 8, stated honestly.** Because it commits another 2,324 B of a ~190 KB heap permanently,
on a device whose known defect is memory, for a connection nobody has shown is needed. That is a
budget judgement on a small number, not a measured cliff — **the contiguity and latency evidence
that once appeared to condemn 8 is absent, not against it, and the memory case is 2,324 B rather
than the 7,488 B this document briefly claimed.** Anyone revisiting this should weigh 2,324 B
against the traffic they actually have; it is not much.

**What would settle it** is the functional wall on silicon, because a wall is a step change and so
robust to the noise that defeats gradient metrics: the first N at which a `MemoryError` appears at
all, caught or not. On the twin that is N = 47 (§8.4), far above either candidate.
`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §5 bisects to the board's own number rather than
gridding settings that cannot be told apart.

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

**The setting is unchanged — `max_connections = 7` — but the reasoning is narrower than this
section once claimed.** It asserted that "two independent curves stop in the same place". One of
those curves has since been withdrawn (§8.3.1): the twin's contiguity gradient was an artifact of
sampling after the burst with an allocating probe, and re-measured correctly it cannot rank
adjacent settings at all. What remains is one curve, not two:

- the ensemble cost, crossing 4% of the GC heap between 7 and 8 — deterministic, from ELF sizes.

What changes is the **price**: 3.73% of the GC heap, not the 0.50% §8.5 claimed. The trade stated
in both directions, corrected: 75% more connections, each of which the stack can genuinely push,
for 7,364 B of GC heap statically, plus ~5,170 B per connection live while it is being served
(§8.3.3). (Earlier versions of this sentence also charged "a ~30% relative loss of
largest-contiguous-free" and added p50 latency; both came from measurements since withdrawn
(§8.3.1, §8.3.2) and are removed rather than restated.)
`max_connections = 4` at a coherent ensemble costs only 392 B, so the whole price of this change is
the six thousand-odd bytes between them.

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


## 10.1 The CI flake: a port collision at module import, found by instrumenting CI

**What it was.** `digital_twin/unix_port_poll_prewarm.py`'s `prewarm_poll_set()` bound a *fixed*
loopback port, 18099. It runs as the first statement of every file that boots a device, and
`scripts/test.sh` dispatches up to 16 files concurrently as separate processes, so two importing
within the same ~45 ms window both tried to bind it. `SO_REUSEADDR` does not permit two live
listeners on one port - that is `SO_REUSEPORT` - so the loser died with `OSError: [Errno 98]
EADDRINUSE` at import, before any test body ran, in whichever lane happened to lose.

Three processes wanted that port, and this branch added the third:

| caller | port | added |
|---|---|---|
| `tests/test_digital_twin_uart_link.py` -> `prewarm_poll_set()` | 18099 | pre-existing |
| `tests/test_digital_twin_http_client.py:336` -> `start_server` | 18099 | pre-existing |
| `tests/test_digital_twin_bus_hazard_concurrency.py` -> `prewarm_poll_set()` | 18099 | **this branch** |

That is why six of twelve runs went red starting exactly at the commit that raised the ceiling:
that same commit added the bus-hazard file's prewarm call, which the new full-ceiling REST burst
needed to avoid the `modselect.c` segfault. The fixed port was a latent defect with two users; a
third made it fire about half the time. Note the prewarm's 18099 sat directly on the first port of
`test_digital_twin_http_client.py`'s own 18099-18103 canned-server band - a second collision,
between two different files, underneath the self-clash.

**The fix.** `_bind_free_listener()` scans upward from `_PORT_SCAN_BASE = 17400` across a 64-port
window, taking the first that binds and raising an `OSError` naming the window if none does - never
a silent fallback. A fresh socket per attempt, and 17400-17463 is a band nothing else in the repo
uses. Port 0 would be the obvious answer and is not available: the Unix port exposes no
`getsockname()`, so an ephemeral bind could never be read back to connect to (verified against the
pinned interpreter).

**Proven both ways, by experiment rather than reasoning.** Thirty concurrent prewarms:

| | EADDRINUSE |
|---|---|
| fixed port 18099 (old) | **28 / 30** |
| scanned window (new) | **0 / 30** |

`tests/test_digital_twin_poll_prewarm.py` pins it: a held base is skipped, a full window is walked
to its last port, an exhausted window fails loudly and names itself, the real entry point still
prewarms with its base taken, and the band stays clear of the canned-server range.

**How it was found, after everything else failed.** The failing log is unreachable from the
environment this was built in - GitHub serves runner logs from a storage host the network policy
denies (403 on CONNECT), job summaries are not in the REST API, and the web UI's log endpoints
reject a token. So `scripts/test.sh` now re-emits each red outcome as a workflow annotation, which
the checks API *does* serve. It caught the real failure on its first red run and named the file and
the traceback outright.

That mattered, because **every hypothesis formed without it was wrong.** The suspicion fell on this
branch's own ceiling-scaled concurrency scenarios, and none of it reproduced: 54 targeted runs of
the six concurrency files, a full suite at double CI's oversubscription, a full suite pinned to two
cores at a runner's exact 8-job shape, and the same six files under `build-settrace` - all clean.
Per-scenario timing ruled the budgets out too (the heaviest new scenario takes 2.5 s of its 40 s;
a whole file 36-48 s of a 240 s per-file timeout; the coverage lane's wall-clock inflation is 1.32x,
not the 4-5x its *allocation* inflation suggests, since these scenarios wait on sockets rather than
execute traced Python). None of that was near the truth, which was a fixed port in a file the
investigation never looked at. The lesson is the instrumentation, not the guesses.

**One hardening from that dead end was kept on its own merits**, and it is not a fix for anything
observed: the scenario demanding the whole ceiling three times in a row now starts each round from
an *asserted* zero - `_drained()` polls the service's own `_open_conns` counter with a bounded
budget and the scenario asserts it got there - rather than trusting Part I.6's post-close slot
release to have already happened. A control arm forcing the counter non-zero makes both scenarios
fail as intended, so it is live rather than vacuous, and it costs ~70 ms against the ~1 s a blind
sleep would have.

**An earlier attempt at a diagnostic channel was made and reverted, and the reason matters.**
`scripts/test.sh` was changed to append its verdict to `$GITHUB_STEP_SUMMARY`. That was wrong three
times over: `tests_scripts/test_test_sh.py` deliberately extracts the verdict block and runs it
standalone with only three variables set, so the new block hit `set -u` on the others and broke a
real test; a nested `scripts/test.sh` inherits the variable and appends to its parent's summary;
and - the deciding one - the job summary is not exposed through any API this environment can reach,
so the channel would never have delivered what it promised. Reverted in full; the annotation
channel is its replacement, and its escaping and its "a missing log must never abort the run it
reports on" property are executed against the real extracted source line rather than asserted by
eye.
