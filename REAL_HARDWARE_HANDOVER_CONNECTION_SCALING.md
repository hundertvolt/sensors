# Real-hardware handover: the TCP connection-scaling ceiling

**Read this file alone.** It assumes no knowledge of the branch that produced it. Everything you
need to run, and everything you need to record, is here; the pointers into other documents are for
background you may not need.

This is the runnable form of the one question the digital twin structurally cannot answer. Temporary,
like `REAL_HARDWARE_TEST_QUEUE.md`: delete it once every row below is recorded and migrated.

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

## 8. What the host side already established, so you do not repeat it

All of this is [TWIN] or from a real firmware build; none of it is silicon.

- **PCB slots cost 196 B of GC heap each**, measured across builds at
  `MEMP_NUM_TCP_PCB` ∈ {5, 6, 8, 10, 12, 16, 24, 32}. Every one of those built cleanly: **there is
  no compile-time wall in that range.** Baseline GC heap is 197,528 B.
- **Buffers cost far more per option**: `PBUF_POOL_SIZE` 16→32 is −15,644 B, and lwIP's own
  16000/1460 preset is −19,932 B, a tenth of the whole GC heap.
- **A connection has two costs and they are different kinds of cost.** **Permanent: 2,324 B of
  `.bss`**, exact and linear across 4→16, from ELF sizes — gone from the GC heap forever, used or
  not. **Transient: ~5,170 B live while being served**, plus ~12,500 B of churn the collector takes
  back. Ten rounds of N concurrent requests leave ~1.6 KB behind *in total, flat rather than per
  connection*, and placement capacity is no worse afterwards — so the transient half is genuinely
  returned. **The cost of 7→8 is 2,324 B permanent, not 7,488 B**; an earlier version of this file
  added the transient half to the permanent one, which is the mistake §5B rule 9 exists to prevent.
  Two sampling traps, both hit here first: reading runtime cost *without* collecting first gives
  ~17,700 B of which **71% is garbage**, and reusing one process across repeats makes the survivor
  number meaningless (it produced negative survivors). The permanent half is `[BUILD]`; the
  transient half is `[TWIN]`.
- **Above the transport, the twin serves every connection count it was asked for, up to 63**, with
  zero rejections at burst = N and no allocation failure anywhere below N = 47.
- **The twin's wall is a `MemoryError` on a small allocation.** At N = 47 with a 3x burst one
  appears *caught and degraded*; at N = 63 it is uncaught and the process dies. The contiguity
  *gradient* that once accompanied this is withdrawn - `CONNECTION_SCALING_PLAN.md` §8.3.1 has
  why, and §5B above has what to do instead. Treat 47 and 63 as the twin's wall, nothing more.
- **Latency does NOT grow with the ceiling at fixed load.** An earlier claim of "1.3 ms per added
  connection" came from a sweep whose offered load scaled with the setting; pinned at concurrency 4,
  p50 is flat from `max_connections` 4 to 16 (§8.3.2). Do not spend board time re-deriving a
  gradient that is not there — measure latency under YOUR realistic load, against the shipped
  setting, and compare it to the same load at the old ceiling of 4.

The open question is whether the board's own wall arrives **before** any of that — and if so, which
pool it is.

## 9. Traps

- A completed TCP `connect()` is **not** an accepted, counted connection. The accept loop has to run
  `_serve()` first. Every probe here sleeps between connecting and concluding anything.
- A slot is released in `_serve()`'s `finally`, *after* the writer close has been awaited — so it
  outlives the response the client already holds. Take a settle before a burst, and after it.
- A refusal is not always a clean FIN; depending on kernel TCP state it can be an RST. Both mean
  "closed without writing a response", and `src/` does not choose which.
- Do not raise a threshold, a heap size or a timeout to make a failure go away. If a row fails,
  that is the result this file exists to collect.
