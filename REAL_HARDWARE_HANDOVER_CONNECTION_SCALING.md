# Real-hardware handover: the TCP connection-scaling ceiling

**Read this file alone.** It assumes no knowledge of the branch that produced it. Everything you
need to run, and everything you need to record, is here; the pointers into other documents are for
background you may not need.

This is the runnable form of the one question the digital twin structurally cannot answer. Temporary,
like `REAL_HARDWARE_TEST_QUEUE.md`: delete it once every row below is recorded and migrated.

---

## 00. THE NEXT SITTING — the static-file fix (written 2026-09-23 evening, after §0 ran)

**§0 ran on silicon the same afternoon** (`BENCH_SITTING_2026-09-23_HANDOVER.md` §10, results in
§0.5 below). The JSON fix held — every route's need matched the twin to the byte — but **the static
page failed from N = 6**: microdot's `send_file` read the page 1,024 B at a time, each read one
fresh 1,025 B allocation, and a failed one cut the body off behind a `200` that carried no
`Content-Length`, so the browser got a corrupt page and no error. This section is the follow-up:
**one flash** (the tip), about **30 minutes**.

### 00.1 What changed, in four lines

- **Static files go out in 256 B reads**, the same hole size as the JSON pieces: `_serve_static()`
  sets microdot's own per-response `Response.send_file_buffer_size`. `ext/microdot.py` is untouched.
- **Every static response carries `Content-Length`**, so a body cut off after the `200` is a
  client-visible short read, not a silently wrong page. (SPEC I.3, "Static files")
- **The instruments now see it**: the need test probes `route:/` through microdot's own body loop,
  and the sweep counts a response as served only if its body matches its `Content-Length`
  (`-truncated`, or `-unframed` when there is no length at all). Both gaps are §10.7's.
- **Why the twin missed it**: its default page is a sub-1 KB stub, and a failure in the write phase
  reaches only the FRAM log, which the twin never printed. Both are closed (MEASUREMENTS §7Q.14).

### 00.2 Before anything

§0.2 applies unchanged: go-ahead in your own conversation, `DebugLevel = 5`, **read `errcount`
before anything writes**. If §10.6's image-F sweep is still unrecorded, record it first — it is the
baseline this sitting is compared against.

### 00.3 Image F′ — the tip (rows W5, W6)

1. `uv run scripts/build_firmware.py dev`, flash. The lwIP verification must pass with 11 / 64 / 16,000.
2. `uv run pytest tests_hardware/bench/test_serving_heap_at_default_gc.py -s` (W5), ~10 minutes.
3. The per-boot combined-load sweep of §10.6 (fresh boot per level, body lengths checked), levels
   2, 4, 6, 8 (W6). Same definition of stable: every request `200` with a complete body **and** zero
   allocation-failure lines on the device.
4. If both are clean: W3 and W4 from §0.4, which §0 held back. **The board is left on F′.**

### 00.4 Recording table

| row | measurement | twin prediction (32-bit, F's heap) | `[HW]` |
| --- | --- | --- | --- |
| W5 | need of `route:/` / worst JSON route | 336 B / 320-336 B (pre-fix `route:/`: 1,536 B) | ___ |
| W5 | sweep N = 4 / 6 / 8 / 10: failures, and served-complete | 0 failures, every body complete; 48 / 72 / 96, then 96 + 24 refused at 10 (the refusal is the limit's, which this twin build did not set) | ___ |
| W6 | per-boot N = 2 / 4 / 6 / 8, complete / failure lines | 4 / 6 / 8 measured: all complete, 0 failures (pre-fix, the same twin: 6 pages cut off at 8) | ___ |
| — | `/` bytes on the wire vs an idle fetch | identical, with `Content-Length` equal to the file's size | ___ |

**Read the prediction with §7Q.14's caveat**: on image G the board's first JSON failures came at
N = 10, where the twin's same-arm run put them at 12 — the twin is about two levels optimistic near
the wall. At F's limit of 8 that margin is what W6 measures.

---

## 0. The first follow-up sitting — RUN 2026-09-23 afternoon (written after §1-§9 ran; results in §0.5)

**§1-§9 below were run on silicon on 2026-09-23**; `BENCH_SITTING_2026-09-23_HANDOVER.md` is their
record. That sitting found one thing they did not ask: **at MicroPython's own gc default the board
served at most 4 concurrent requests** — lwIP admitted 16, the GC heap could not serve them. This
section is the runnable follow-up. It needs **two flashes** and about **45 minutes** including both
builds. Everything it asks for has a twin prediction next to it; a result that disagrees is the
finding, not a harness bug to explain away — the instruments were all run against the twin first.

### 0.1 What changed since the sitting, in four lines

- **Every streamed GET route** (`/status`, `/sensors`, `/measurements`, `/networking`, `/system`,
  `/notification`) writes its JSON through a bounded writer: the largest allocation on the path is
  one 256 B piece, where it was up to ~880 B. The bytes on the wire are **identical**. (SPEC I.3)
- **`max_connections` is 8** (owner: "target 10 ground stable, keep the limit to 8 as safety
  margin"), lwIP ensemble `MEMP_NUM_TCP_PCB` 11 / `MEMP_NUM_TCP_SEG` 64 / `MEM_SIZE` 16,000. (SPEC H.7)
- **All evaluation is at `gc.threshold(-1)`** — the device scripts set it explicitly, because
  `mpremote` does not reset the interpreter and the boot entry's own threshold would still be set.
- The twin that predicted all this is a **32-bit** frozen Unix port at a heap calibrated to the
  board's own §4 curve — it reproduces the sitting's three failing call sites and sizes exactly.
  (MEASUREMENTS §7Q)

### 0.2 Before anything

- The owner's go-ahead **in your own conversation** (CLAUDE.md). `DebugLevel = 5`.
- **Read `GET /status`'s `errcount` and write it down before anything writes.** Both device scripts
  below build their own `AsyFramManager` over the same FRAM chip, so afterwards the log is not
  evidence (CLAUDE.md, the FRAM-log rule and its caveat).
- **Traps that cost the last sitting time**: a `pgrep -f "<pattern>"` or `pkill -f` wait loop
  matches its own command line; `mpremote` does not reset the interpreter; a host-side load thread
  that outlives its test takes every later test down (the new file joins and asserts on it).

### 0.3 Image G first — 10 served, and the board's real ceiling (row W2)

1. Edit **locally, never committed**: `devices/dev.toml` `max_connections = 16`, and
   `toolchain/versions.toml` `[lwip]` `MEMP_NUM_TCP_PCB = 19`, `MEMP_NUM_TCP_SEG = 128`,
   `MEM_SIZE = 32000` — image B's coherent ensemble (§5). `buildgen` refuses an incoherent set.
2. `uv run scripts/build_firmware.py dev`, flash (`tests_hardware/README.md`). Record `.bss` and
   the GC heap (`__GcHeapEnd - __GcHeapStart`) from the ELF — expect ~18,592 B less heap than F.
3. `uv run pytest tests_hardware/bench/test_serving_heap_at_default_gc.py -s` (the bench fixtures
   need the board and the bridge). The sweep reads the ceiling from your local `dev.toml`, so it
   runs levels **4, 6, … 18**, 12 rounds each, on one boot. ~12 minutes.
4. Record per level: served / 500 / 400 / refused, and every `memory allocation failed, allocating
   N bytes` with its traceback site. **Twin prediction: zero failures through 12**; from 14 on, failures
   at pieces (~250 B), at `microdot.py:383` (the `Request` object's own attribute table, ~232 B) and
   at the list holding a response's pieces — at the twin's harsher calibration. At its gentler one it
   is clean through 18, so the real wall anywhere in 12-18 is consistent with the twin; below 10 is
   not. G's extra `.bss` makes its wall, if anything, lower than a right-sized image's.
5. `git checkout -- devices/dev.toml toolchain/versions.toml` before the next build.

### 0.4 Image F — the tip as it ships (rows W1, W3, W4)

1. `uv run scripts/build_firmware.py dev`, flash. The build's own lwIP verification must pass with
   11 / 64 / 16,000.
2. `test_serving_heap_at_default_gc.py` again (W1), ~10 minutes. **Twin predictions**:
   `test_every_source_and_route_fits_a_small_free_run` — every route and every data source runs
   on a heap whose largest free run is 384 B (twin: worst route 320 B, every source ≤ 192 B); as shipped `/status` needed 1,024. The sweep —
   levels 4, 6, 8, 10: **zero allocation failures**, at N = 10 exactly 8 served per round and 2
   refused cleanly.
3. From the same run, the question the twin could not settle: **does the heap recover** after the
   load? Compare the `pre` and `post` dumps' `largest_free_run`/`runs`.
4. `test_end_to_end_timing.py` (W3): `/status` now goes out as 29 pieces instead of 11; compare
   against the sitting's own timing.
5. The full bench tier, default flags (W4): `scripts/run_bench_hardware_suite.sh`. Read the
   deselected count, not just "clean". **The board is left on F.**

### 0.5 Recording table

| row | image | measurement | twin prediction | `[HW]` |
| --- | --- | --- | --- | --- |
| W2 | G | failures at N = 10 / 12 / 14 / 16 / 18 | 0 / 0 / then 0 or >0 (bracket 12-18) | **FAILED below 10**: per-boot N=6: 10, N=8: 11, N=10: 36, N=12: 66 allocation lines; cumulative sweep 112 × 1025 B + ~180 route pieces, board reset itself at ~425 s (sitting doc §10.4/10.6) |
| W2 | G | first failing level, and its sizes and sites | 14-20; ~250 B pieces, `microdot.py:383` | **N=6: 1,025 B in microdot's `send_file` body read (`ext/microdot.py:746`) — a truncated 200 on `/`**. JSON pieces (251-256 B, `_PieceWriter`) and `microdot.py:383` (232 B) first at N=10 |
| W1 | F | largest need of any route / any source | 320 B / ≤ 192 B | **320 B (`/status`) / ≤ 144 B — matches**; but no static route is probed |
| W1 | F | failures at N = 4 / 6 / 8 / 10 | 0 / 0 / 0 / 0 | **FAILED: 11 × 1,025 B** across the run; tallies 48/72/96 served + 24 refused at N=10, but the tally counts truncated bodies as served |
| W1 | F | largest free run, idle before vs after the load | unsettled in the twin | before 10,080-15,232 B, after 7,008-9,760 B; free ~82 KB → ~80 KB. Partial recovery |
| W3 | F | `/status` p50 / p95 | not modelled (twin has no lwIP) | not run — stopped per the rule below |
| W4 | F | bench tier passed / skipped / deselected | — | not run — stopped per the rule below |

If W2 fails **below** 10 on silicon, 8 is not the margin it was meant to be: record it and stop —
that is the owner's decision, not the sitting's.

---

## 1. What this is about, in one paragraph

The firmware serves HTTP from `src/asy_webserver_service.py`. It admits at most
`max_connections` simultaneous connections and silently closes any beyond that ("reject-when-full").
Underneath it, lwIP holds a fixed, compile-time pool of TCP protocol control blocks —
`MEMP_NUM_TCP_PCB` — and a connection that cannot get one never reaches the application at all.
That pool used to be lwIP's own default of **5**, with `max_connections = 4`. This branch raised the
pool to **10** and `max_connections` to **7**, and made the whole lwIP option set settable from
tracked files. **Nothing about the lwIP half has ever run on a real board.** That is what you are
here to establish.

**These options are an ensemble, not independent knobs** — read §5A before changing any of them.

## 2. Why the twin could not do it

The digital twin runs on the MicroPython **Unix port**, which has no lwIP compiled in at all — its
sockets are ordinary host sockets with the host kernel's own limits. It therefore validates
everything *above* the transport (admission, rejection, concurrent request-body allocation, task
growth, timeouts, fairness, latency) and can say nothing whatever about PCB exhaustion, pbuf
exhaustion or lwIP's own heap. A green twin run is **not** a validated connection ceiling. Please
keep that distinction in anything you write down.

## 3. Before you start

- **You need the project owner's go-ahead in your own conversation.** CLAUDE.md's gate is
  per-session and does not carry over from the session that wrote this file. Ask; do not assume.
- `tests_hardware/README.md` is the technical reference — prerequisites, environment variables,
  the `--allow-flash-cycle` / long-soak opt-in gates, and the hotspot role-reversal risk. Read it.
- **The bench board carries a production `dev` image at `DebugLevel = 0`.** Several bench tests
  parse the serial log and fail silently at 0. Set `DebugLevel` back to **5** before any bench run.
- **Read the FRAM-persisted error logs before clearing anything.** `GET /status`'s `errcount`
  carries SGP40/BMP3XX/SCD30/SYSTEM/NEOPIXEL/NOTIFY history that survives a reboot, and a
  `PUT /status {"ResetErrors": true}` destroys it irreversibly. This has already cost real evidence
  once. Capture it first, then clear.
- Every measurement below is **read-only against the board** except §5, which reflashes. Nothing
  here writes to the board's own flash filesystem or to any sensor's NVM.

## 4. The fastest useful sitting (about 40 minutes, one image)

If you only have time for one thing, do this. It answers "does the shipped setting actually work on
silicon" and needs no sweep.

1. Build and flash this tree's own `dev` image:
   `uv run scripts/build_firmware.py dev` then flash per `tests_hardware/README.md`.
   The build itself already verifies that every lwIP option reached the firmware's real translation
   unit — it preprocesses lwIP's `opt.h` with the exact flags CMake compiled `firmware` with and
   fails loudly on any mismatch. **If that check fails, stop and record it: that is a result.**
2. Set `DebugLevel = 5`.
3. Run the bench tier's connection rows:
   `tests_hardware/bench/test_network_resilience.py::test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures`
   This opens connections one at a time until one is refused, and asserts the count equals what the
   tree configures (7). **It is the single most important row in this file.**
4. Run the two rows that check the board can *serve* what it admits rather than merely accept it —
   same file, and the silicon half of the twin's own scenarios of the same name:
   `test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body` (a full ceiling at
   once, each answered 200 with a complete parsed body inside 30 s) and
   `test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one` (a truncated stream still
   reads as a 200, so byte counts are compared against an uncontended load).
5. Run `tests_hardware/bench/test_end_to_end_timing.py` and the rest of
   `test_network_resilience.py`. Both now scale their bursts with the configured ceiling.
6. Record §7's table for this one setting and stop.

## 5. Finding the board's own wall in two images, not a bisection

**Read §5B before planning the sitting.** The short version: contiguity metrics cannot tell N = 7
from N = 8, so do not spend board time trying. What silicon can answer and the twin cannot is where
the **wall** is — and a wall is a step change, robust to the noise that defeats gradients.

**Two images, because the probe walks upward at runtime.** `max_connections` is compiled in, but
`discover_max_connections()` (`tests_hardware/harness.py`) opens connections one at a time until one
is refused, up to `probe_limit`. So a single over-provisioned image reports the board's real
concurrent-connection capacity in one run — whether the binding constraint is lwIP's PCB pool, its
pbuf supply, or the GC heap. A bisection over many images answers the same question and costs one
build-and-flash per step.

| image | `max_connections` | `MEMP_NUM_TCP_PCB` | `MEMP_NUM_TCP_SEG` | `MEM_SIZE` | what it answers |
| --- | --- | --- | --- | --- | --- |
| **A** | 7 | 10 | 56 | 14,000 | **the shipped setting works on silicon** — §4, do this first regardless |
| **B** | 16 | 19 | 128 | 32,000 | `discover_max_connections(probe_limit=64)` reports the real wall |
| C *(only if B finds none)* | 24 | 27 | 192 | 48,000 | same probe, higher ceiling |

Image B costs 16 x 2,324 B = 37,184 B of GC heap, leaving ~160,000 B against a graph that boots
~84,000 B full — about 52%, comfortable. Image C leaves ~141,000 B (~60% full), which is tight but
should boot; **32 is not recommended** (~68% full) and would confound a heap wall with a PCB wall.

**Read B's result like this:**
- **Probe returns < 16** → that is the wall. Record §7, then go to §6 to find out *which* pool ran
  out rather than inferring it. This is the interesting outcome.
- **Probe returns exactly 16** → no wall below 16, so the shipped 7 has at least 2.3x margin. That
  is very likely all the decision needs; image C is optional curiosity.

**Then check it can SERVE what it admits at that number**, not merely accept it: run
`test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body` and
`test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one` against image B. On silicon
every sensor task is always running, so a full-ceiling burst **is** the all-modules pressure case —
the twin needs `scripts/_digital_twin_ci_suite.py`'s Run 11b to arrange it deliberately, the board
gets it for free. The first of those two now also asserts that **no** FRAM-backed module logged a
new error during the burst, not just `WEBSERVER`, because a starved heap surfaces wherever it
surfaces.

Set every `devices/*.toml`'s `[device].max_connections` and `[lwip]` to the **whole coherent
ensemble** for the row (§5A). `buildgen` refuses an incoherent set by name before the build, and the
build itself verifies the macros reached the real translation unit — so neither can go wrong
silently.

**Flash-cycle cost: two writes, three if you run C.** Negligible against the part's endurance, but
it is real wear, so do not re-flash to re-run a test the same image can repeat.

## 5A. The options are an ensemble — read this before touching any of them

`lib/lwip/src/core/init.c` turns nine relationships between these options into compile-time
`#error`s, and `opt.h` derives `TCP_SND_QUEUELEN`, `TCP_SNDLOWAT`, `TCP_SNDQUEUELOWAT` and
`PBUF_POOL_BUFSIZE` from the ones you set. MicroPython's own pinned block is a tuned set sitting
exactly on one boundary (`MEMP_NUM_TCP_SEG` 32 = the derived `TCP_SND_QUEUELEN` 32). **Move one
value alone and you either fail the build or silently change something else.**

`toolchain/micropython_overrides.py`'s `check_lwip_ensemble()` restates all of it and refuses an
incoherent set by name before the build. It also enforces the two relationships lwIP does *not*
check, because lwIP sizes the shared pools for **one** connection while this firmware admits N:

- `MEMP_NUM_TCP_SEG >= max_connections x (TCP_SND_BUF / TCP_MSS)` — segments are a **global** pool
  against a **per-connection** `TCP_SND_QUEUELEN`, so without this one connection drains it and the
  rest hold data the stack accepted and cannot push.
- `MEM_SIZE / max_connections >= 2000 B` — every outbound byte is copied into that arena
  (`modlwip.c`'s `tcp_write()` always passes `TCP_WRITE_FLAG_COPY` → `PBUF_RAM` → `mem_malloc()`),
  and 2,000 B is the share the 4-connection design had.

**`PBUF_POOL_SIZE` is deliberately not scaled**, because it backs the *inbound* path (one small
request per connection, bodies capped at 2,048 B) and costs ~978 B of GC heap per pbuf. **That is
the assumption most worth testing on silicon** — if §6's `LWIP_STATS` shows pbuf-pool exhaustion,
this is the door to open, and `PBUF_POOL_SIZE` / `MEMP_NUM_PBUF` are the settings.

## 5B. How to measure contiguity — and what it cannot tell you

The host-side sweep got this wrong in three ways and the corrected result is in
`CONNECTION_SCALING_PLAN.md` §8.3.1. The rules below are what came out of it. They cost nothing to
follow and they save an entire sitting.

1. **Sample at true peak, and prove it.** The original probe ran after the burst had completed and
   every connection was closed — it measured allocator residue, not pressure. A valid sample is
   taken while all N connections are open *and parked mid-request*, with their bodies allocated;
   assert the count you actually held, and record it beside the figure.
2. **Use a non-perturbing instrument.** `micropython.mem_info(1)`, captured over serial and parsed
   host-side by `tests_hardware/heap_map.py`. Never a probe that allocates to find out how much it
   can allocate — that changes the fragmentation it is reporting. On the board this is *easier*
   than on the twin, because the dump goes to the serial console you are already reading.
3. **Report absolute bytes and placement capacity, never a percentage of the after-boot value.**
   The figure that predicts failure is `heap_map.gaps_at_least(2048)` — how many of microdot's
   per-connection `readexactly()` buffers (`max_content_length = 2048`) can still be placed. A
   percentage of the boot value made 16,032 B read as a "4.0% cliff" when it was 7.8x headroom.
4. **Establish the within-N spread before comparing any two settings.** Repeat the *same* N at
   least five times first. On the twin the spread was 6-12 slots while the step between adjacent
   settings was 0-4, so **no adjacent pair was resolvable**. Only differences larger than the spread
   you measured are signal.
5. **Run the monotonicity check as a validity gate.** Contiguity must not rise as N rises. If it
   does, the measurement is dominated by placement luck and must not be used to rank anything —
   report it as inconclusive rather than rationalising the outlier. (That rationalisation is exactly
   what produced the withdrawn result.)
6. **Collect immediately before any heap sample, and say that you did.** `used_bytes` at peak
   without a collect is live objects *plus* garbage the burst made and the collector has not swept:
   on the twin that is 71% garbage, enough to overstate per-connection cost 3.4x. A collect can
   only free unreferenced objects, so it yields the live set without disturbing what is under test.
7. **Never let the offered load scale with the setting under test.** The withdrawn latency result
   came from a sweep firing `burst = 2 x max_connections`, which measured "latency when you also
   offer twice as many requests". Pin the load and vary only the ceiling; at fixed concurrency,
   latency is flat from 4 to 16 on the twin. If you want a latency number for the board, measure
   *your realistic load* against the shipped setting and against the old ceiling of 4.
8. **Prefer the deterministic quantities**, which is where board time actually pays: the exact
   admission ceiling (§4, deterministic), heap and `.bss`/`.data` cost from the ELF (zero variance),
   latency percentiles (averaged over many requests, so noise averages down), and the wall itself
   (a step change). Gradients of contiguity against N are the one thing this instrument cannot give
   you.
9. **Do not measure a transient allocation with survivor methods.** A connection's runtime
   allocation is freed when the connection closes; a boot survivor is not. Never add the two into
   one "cost". For the permanent half measure `.bss`/GC-heap from the ELF. For the transient half
   ask the only two questions that matter: does it **fully return** (serve many rounds in a **fresh
   process**, collect, and compare live bytes to before — the residue must be flat in total rather
   than growing per connection), and does the churn **leave the heap no worse** (placement capacity
   before versus after). Neither is a budget fraction.
10. **At peak, ask whether there are enough sufficiently long pieces — not whether the heap is
   unfragmented.** The demand is N simultaneous 2,048 B request buffers plus the response path, so
   the figure is `gaps_at_least(2048)` against that demand. A heap with 40 KB free in 512 B pieces
   fails; one with the same free split into ten 4 KB gaps is fine. Total free bytes answers neither.

## 6. Seeing *which* pool ran out, rather than inferring it

`[lwip].LWIP_STATS` is `0` as shipped. Set it to `1`, rebuild and reflash, and lwIP keeps per-pool
exhaustion counters. This costs 1,916 B of GC heap, which is why it is not shipped on. It is the
direct way to tell "no free PCB" from "no free pbuf" from "lwIP heap exhausted" — worth one extra
image the moment a row in §5 fails for a reason you cannot name.

lwIP exposes these through `stats_display()` in C, which this firmware does not call. The cheapest
read is a device script that imports nothing and simply confirms the counters compiled in; if you
need the values themselves, add a tiny C-free probe or read them over the debug serial. **Record
what you had to do**, because nobody has done this on this project before and the next session
should not re-derive it.

## 7. What to record, per row

Everything below, for every setting you try. A row without these is not a result.

| field | how |
| --- | --- |
| connections actually served concurrently | `discover_max_connections()` in `tests_hardware/harness.py` |
| connections cleanly rejected | the same probe; a refusal is an empty read or a reset, both fine |
| **how a failure presents** | clean rejection / silent drop / stall / `MemoryError` / watchdog reset — this is the point of the exercise |
| largest contiguous free block, after boot | `micropython.mem_info(1)`, parsed by `tests_hardware/heap_map.py` |
| **placement slots at peak**, `gaps_at_least(2048)` | the same dump, taken while all N connections are open and parked mid-request — **record how many you actually held beside it**, and repeat 5x, reporting min/median/max, never one reading (§5B) |
| free heap, both points | the same dump's `GC: total/used/free` line |
| `.bss` / `.data` and GC heap from the map file | `arm-none-eabi-size -A firmware.elf` and `__GcHeapEnd - __GcHeapStart` |
| any `MemoryError` **or** `memory allocation failed` | both spellings; a caught-and-degraded one counts as a failure, not a pass |
| any watchdog reset | `GET /status`'s `errcount`, SYSTEM chunk |
| p50 / p95 response time under full load | `tests_hardware/bench/test_end_to_end_timing.py` |
| **every admitted connection actually SERVED** | `test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body` — a full ceiling of concurrent requests must each return a complete, correct body — not just a 200. A truncated stream and a response that arrives a minute late both pass a status check and both fail this |
| a concurrent page load's byte count vs an uncontended one | `test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one` — they must be equal; `ext/microdot.py` streams in `send_file_buffer_size` chunks, so a stack out of buffers truncates rather than failing |

**Where to write it**: `CONNECTION_SCALING_PLAN.md` §8, which already holds the host-side sweep and
the twin sweep in the same shape. Mark every hardware row `[HW]`, as the other measurement documents
in this repo do.

## 8. Every number the host side established, and what it is worth

Tier tags throughout: `[BUILD]` is a real firmware build (deterministic), `[TWIN]` is the Unix-port
digital twin (no lwIP at all), `[HOST]` is the CPython suite driving the twin as a subprocess.
**Nothing here is silicon.**

### 8.1 What survived scrutiny

| what | value | tier | why it is trustworthy |
| --- | --- | --- | --- |
| **Permanent cost of a connection** | **2,324 B of `.bss`** | `[BUILD]` | every step identical across `max_connections` 4→16; arithmetic on static array sizes from real ELFs, not a sample. Zero variance. |
| PCB slot alone | 196 B | `[BUILD]` | same, across `MEMP_NUM_TCP_PCB` ∈ {5,6,8,10,12,16,24,32}; all built cleanly, so **no compile-time wall in that range** |
| Baseline GC heap | 197,528 B stock; 190,164 B at the shipped ensemble | `[BUILD]` | `__GcHeapEnd - __GcHeapStart` |
| Buffer options cost far more | `PBUF_POOL_SIZE` 16→32 = −15,644 B; lwIP's 16000/1460 preset = −19,932 B | `[BUILD]` | a tenth of the whole heap for the preset |
| **Transient cost while serving** | **~5,170 B live per connection**, 0.5% spread | `[TWIN]` | measured with every connection parked mid-body, after a collect |
| **It is genuinely returned** | 40/70/80 served requests leave ~1.6 KB **in total, flat not per connection**; placement capacity no worse after | `[TWIN]` | fresh process per repeat; a shared one gives meaningless (even negative) survivor deltas |
| **All modules hammering, full ceiling** | **7/7 served every round, 0 `MemoryError`, clean shutdown — at `gc.threshold(-1)` AND 32768** | `[HOST]` | Run 11b, driver in its own process (Part E.9) |
| Admission exactness | exact at every count tried, 2→63 | `[TWIN]` | deterministic |
| Latency vs ceiling **at fixed load** | **flat**: 4.5 / 4.5 / 4.2 / 4.4 / 4.3 ms at `max_connections` 4 / 7 / 8 / 12 / 16 | `[TWIN]` | concurrency pinned at 4 for every setting |

### 8.2 What was measured and then withdrawn — do not re-derive these

Four claims this branch published and retracted. They are listed so the board's time is not spent
reproducing them, and because each names a measurement trap worth avoiding.

| withdrawn claim | why it was wrong |
| --- | --- |
| "3.5x contiguity cliff between 7 and 8" | sampled **after** the burst with an **allocating** probe, normalised against the after-boot value. Re-measured correctly, the within-N spread (6–12 slots) exceeds the between-N step (0–4) for **every** adjacent pair — the metric cannot rank adjacent settings at all |
| "p50 grows ~1.3 ms per added connection" | the sweep's burst was `2N`, so the offered **load scaled with the setting**. At fixed load it is flat (§8.1) |
| "the bar is 18 connections" | measured with the twin's own client **inside the DUT's process**. Every failure was `MemoryError` in `_http_client._read_exact` allocating a ~5.5 KB body the test never read — the harness, not the firmware |
| "~12 KB of free heap needed per connection" | same in-process harness. With the client draining instead of buffering, the same load passed 42/42 on a heavily fragmented heap |

Three repo mechanisms exist to prevent exactly these, and all three were found only after the fact:
SPECIFICATION.md **Part E.9** (driver/DUT process separation), `fetch(read_body=False)`'s **drain
siblings** (`tests/test_digital_twin_http_client.py` documents the CI regression that motivated
them), and `heap_map.gaps_at_least()` (**the** placement metric). §5B's rules are the distilled form.

### 8.3 The decision table — fill the `[HW]` column, then decide

This is what the sitting is for. Everything left of the last column is already known; the last
column is what only silicon can say.

| # | question | host-side answer | `[HW]` result | decides |
| --- | --- | --- | --- | --- |
| 1 | Does the board admit exactly the configured 7? | n/a — twin has no lwIP | ___ | whether `MEMP_NUM_TCP_PCB = 10` really took effect |
| 2 | Does it **serve** all 7 completely, bodies intact? | yes `[HOST]` | ___ | whether the ceiling is real or nominal |
| 3 | Is a concurrent page load byte-identical to an uncontended one? | yes `[TWIN]` | ___ | whether buffers truncate under load |
| 4 | Did **any** FRAM-backed module log a new error during the burst? | n/a | ___ | the all-sides memory bar on silicon |
| 5 | **Where is the board's wall?** (image B, `discover_max_connections`) | 47 caught / 63 fatal `[TWIN]`, transport path only | ___ | the real margin above 7 |
| 6 | Which pool runs out at the wall? | unknown | ___ | whether `PBUF_POOL_SIZE = 16` was the right call (§5A) |
| 7 | Largest contiguous free block after boot, and at peak with 7 held | n/a | ___ | headroom for everything else |
| 8 | `gaps_at_least(2048)` at peak | n/a | ___ | whether the simultaneous demand can be **placed** |
| 9 | p50/p95 at the shipped 7 vs at 4, under the same real load | flat `[TWIN]` | ___ | whether the raise costs users anything |
| 10 | Any watchdog reset across all of it? | none `[TWIN]`/`[HOST]` | ___ | stability |

Rows 1–4 come from image A (§4). Rows 5–8 come from image B (§5). Row 9 is
`test_end_to_end_timing.py` on both images. Row 6 needs §6's `LWIP_STATS` image and **only if row 5
finds a wall**.

**The instruments, by row:**

| row | test |
| --- | --- |
| 1 | `test_network_resilience.py::test_the_board_holds_exactly_the_connection_ceiling_this_tree_configures` |
| 2 | `test_network_resilience.py::test_a_full_ceiling_of_concurrent_requests_is_each_served_a_complete_body` |
| 3 | `test_network_resilience.py::test_a_concurrent_page_load_is_byte_identical_to_an_uncontended_one` |
| 4 | the same test as row 2 — it now snapshots **every** FRAM-backed module's counter and names any that grew |
| 5 | `test_heap_under_connection_ceiling.py::test_report_the_boards_own_connection_wall` (image B) |
| 7, 8 | `test_heap_under_connection_ceiling.py::test_heap_at_peak_while_a_full_ceiling_is_held` |
| 9 | `test_end_to_end_timing.py` |
| 10 | `GET /status`'s `errcount`, SYSTEM chunk, after every row |

**One caveat you need before you start.** `test_heap_at_peak_while_a_full_ceiling_is_held` and its
device script `heap_under_connection_ceiling.py` were **written without a board to try them on**.
They ride proven pieces — the device script runs the real `sensortask_dev.main()` and adds only a
`mem_info(1)` sampler, which is Part E.9's prescribed shape — but the READY/IP handshake between the
script and the host thread has never executed. **Run them last**, so nothing else in the sitting is
blocked if they need a fix, and treat a failure there as a harness bug until proven otherwise. Every
other row uses a test that has run before.

**The open question** is whether the board's own wall arrives before any of the twin's numbers — and
if so, which pool it is.

## 9. Traps

- A completed TCP `connect()` is **not** an accepted, counted connection. The accept loop has to run
  `_serve()` first. Every probe here sleeps between connecting and concluding anything.
- A slot is released in `_serve()`'s `finally`, *after* the writer close has been awaited — so it
  outlives the response the client already holds. Take a settle before a burst, and after it.
- A refusal is not always a clean FIN; depending on kernel TCP state it can be an RST. Both mean
  "closed without writing a response", and `src/` does not choose which.
- Do not raise a threshold, a heap size or a timeout to make a failure go away. If a row fails,
  that is the result this file exists to collect.
