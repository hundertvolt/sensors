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
pool to **10** and `max_connections` to **7**, and made both settable from tracked files. **Nothing
about the lwIP half has ever run on a real board.** That is what you are here to establish.

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
4. Run `tests_hardware/bench/test_end_to_end_timing.py` and the rest of
   `test_network_resilience.py`. Both now scale their bursts with the configured ceiling.
5. Record §7's table for this one setting and stop.

## 5. The full sweep, if you have a longer sitting

The point is to find the wall **from both directions**: the highest setting that passes everything,
and the first that fails — and to characterise *how* it fails.

For each row: edit `toolchain/versions.toml`'s `[lwip].MEMP_NUM_TCP_PCB`, set every
`devices/*.toml`'s `[device].max_connections` to the paired value, rebuild, reflash, and record §7.

| # | `MEMP_NUM_TCP_PCB` | `max_connections` | why this row |
| --- | --- | --- | --- |
| H1 | 5 | 4 | the pre-branch baseline, for comparison |
| H2 | 10 | 7 | **the shipped setting** — the row that must pass |
| H3 | 12 | 9 | first row past the twin's own contiguity cliff (which is at 8) |
| H4 | 16 | 13 | |
| H5 | 24 | 21 | |
| H6 | 32 | 29 | the highest the host sweep built cleanly |

Stop one row after the first failure; two failing rows in a row is enough to call the wall.

**Buffers are a separate, later question.** The host sweep priced them at 5–10x the GC-heap cost of
a PCB slot per unit of benefit, and nothing measured says they bind. Only open that door if §7's
`LWIP_STATS` reading below says pbufs or lwIP's own heap are what actually ran out. The settings are
`[lwip].MEM_SIZE` / `TCP_MSS` / `TCP_WND` / `TCP_SND_BUF` / `MEMP_NUM_TCP_SEG` (which must move
**together** — they are one atomic upstream block) and `PBUF_POOL_SIZE` / `MEMP_NUM_PBUF`.

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
| largest contiguous free block, under full load | the same, taken while the ceiling is saturated |
| free heap, both points | the same dump's `GC: total/used/free` line |
| `.bss` / `.data` and GC heap from the map file | `arm-none-eabi-size -A firmware.elf` and `__GcHeapEnd - __GcHeapStart` |
| any `MemoryError` **or** `memory allocation failed` | both spellings; a caught-and-degraded one counts as a failure, not a pass |
| any watchdog reset | `GET /status`'s `errcount`, SYSTEM chunk |
| p50 / p95 response time under full load | `tests_hardware/bench/test_end_to_end_timing.py` |

**Where to write it**: `CONNECTION_SCALING_PLAN.md` §8, which already holds the host-side sweep and
the twin sweep in the same shape. Mark every hardware row `[HW]`, as the other measurement documents
in this repo do.

## 8. What the host side already established, so you do not repeat it

All of this is [TWIN] or from a real firmware build; none of it is silicon.

- **PCB slots cost 196 B of GC heap each**, measured across builds at
  `MEMP_NUM_TCP_PCB` ∈ {5, 6, 8, 10, 12, 16, 24, 32}. Every one of those built cleanly: **there is
  no compile-time wall in that range.** Baseline GC heap is 197,528 B.
- **Buffers cost far more**: `PBUF_POOL_SIZE` 16→32 is −15,644 B, and lwIP's own 16000/1460 preset
  is −19,932 B, a tenth of the whole GC heap.
- **Above the transport, the twin serves every connection count it was asked for, up to 63**, with
  zero rejections at burst = N and no allocation failure anywhere below N = 47.
- **The twin's wall is contiguity, then `MemoryError`.** At a board-calibrated heap, the largest
  contiguous free block retained under a 2x overload burst is 13.8% of its after-boot value at
  N = 7 and 4.0% at N = 8. At N = 47 with a 3x burst a `MemoryError` appears *caught and degraded*;
  at N = 63 it is uncaught and the process dies.
- **p50 latency grows about 1.3 ms per added connection** under a 2x burst (5.4 ms at N = 4,
  9.0 ms at N = 7, 14.4 ms at N = 11).

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
