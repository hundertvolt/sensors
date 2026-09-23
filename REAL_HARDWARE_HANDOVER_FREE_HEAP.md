# Real-hardware handover: free heap under full load at 4, 5, 6 and 7 connections

**Read this file alone.** One build, one flash, about 60 minutes. Temporary: its results go into
`BENCH_SITTING_2026-09-23_HANDOVER.md` (or its successor) and `REAL_HARDWARE_TEST_QUEUE.md` row W7,
then this file is deleted with the rest (BACKLOG.md item 45).

## 1. Why

- 10 concurrent connections is not reachable: on G′ (lwIP sized for 16, 169,120 B GC heap) N=10
  failed 3 of 3 per-boot runs, and H1's sweep ran the heap out entirely, 68-138 B allocations
  included (sitting §10.11). The twin, calibrated to that result, shows the same at N=10 for every
  response-side variant tried (gate, lazy streaming, 64/128/256 B chunks): the heap is exhausted,
  not only fragmented.
- **The owner is choosing a smaller limit**, and wants the real board's free heap under full load
  first: **4, 5, 6, 7**, as a percentage of the GC heap, at MicroPython's own gc default.
- The twin's estimate for comparison is in §4. It is a translation of twin figures to the board, so
  the board is the measurement that decides.

## 2. Before anything

1. The owner's go-ahead **in your own conversation** (CLAUDE.md). Nothing here writes persistent
   config; no `--allow-persistence-writes`.
2. **Read `GET /status`'s `errcount` and write it down before anything writes to the board.** The
   board has run device scripts since its last clean state, so it is context, not evidence
   (CLAUDE.md's FRAM rule and its caveat).
3. **"No gc.threshold" means MicroPython's own default, `gc.threshold(-1)`** — and the device
   script sets exactly that itself, because `mpremote` does not reset the interpreter and the boot
   entry's `gc.threshold(32768)` would otherwise still be in force. Do **not** pass `--threshold`.
   Every level's line must read `GC_THRESHOLD=-1`; a level that doesn't is void.
4. Known traps: a `pgrep -f`/`pkill -f` wait loop matches its own command line; two suites that bind
   real ports never overlap; after a watchdog reset the board may fall back to hotspot mode —
   `kick_all_stations()` + hard reset brought it back last time (§10.11.3).

## 3. Procedure — image F′, the unmodified branch tip

| step | what | time |
| --- | --- | --- |
| 1 | The board is on G′. Discard G′'s local edits (`git checkout devices/dev.toml toolchain/versions.toml`), pull the tip, `uv run scripts/build_firmware.py dev`, flash (`tests_hardware/README.md`). lwIP macros must read back PCB 11 / SEG 64 / `MEM_SIZE` 16,000; record the GC heap (`__GcHeapEnd - __GcHeapStart`, F′ was **187,712 B**) | 10 min |
| 2 | Sanity: `curl -s -D - -o /tmp/idx.gz http://$DUT_IP/` shows `Content-Length: 9292`, `gzip -t` passes | 1 min |
| 3 | **Stability arm** (the verdict): `DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py 4 5 6 7 --raw-dir <dir>` — one fresh boot per level, full task graph, 12 rounds of N concurrent GETs over all seven paths including `/js/app.js`. STABLE = every body complete and zero device allocation-failure lines | 22 min |
| 4 | **Margin arm** (the free heap): the same command plus **`--margin`**. The device script then runs `gc.collect()` before each 5 s heap sample, so every sample is the live set only, and each level prints one extra line: `margin (post-collect, heap H B): idle X B (x %) \| under load min Y B (y %), median … \| largest free run min …` | 22 min |
| 5 | **Leave the board on F′.** | |

**Why two arms.** At `gc.threshold(-1)` the heap fills with garbage until an allocation fails, so an
uncollected sample's "free" says nothing about headroom. The margin arm's collect makes the number
meaningful but also cleans the heap every 5 s, so **its STABLE/UNSTABLE is not evidence** — the
stability arm's is. The collect is instrumentation only, never a fix (CLAUDE.md memory-safety rule).

**Commit the raw dirs' summary lines verbatim**, both arms, as §10.9/§10.10 did.

## 4. Recording table

The percentage base is the GC heap `mem_info` reports on F′. For an image whose lwIP is sized for L
instead of 8, add **(8 − L) × 2,324 B** to both the heap and the free figure — exact, static
`.bss` (SPECIFICATION.md's lwIP table), not a measurement. Twin column: the 32-bit twin's
post-collect serving live set at the same N and full load, subtracted from F′'s idle free, 22-30
samples per level; 4 and 5 were not run in the twin.

| N | stability arm (step 3) | idle free, post-collect | min free under load | min free, % of heap | median free under load | min largest free run | twin estimate, min free on F′ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | ___ | ___ | ___ | ___ | ___ | ___ | not run |
| 5 | ___ | ___ | ___ | ___ | ___ | ___ | not run |
| 6 | ___ | ___ | ___ | ___ | ___ | ___ | ~38 KB, ~20 % (largest run ≥ 1.3 KB) |
| 7 | ___ | ___ | ___ | ___ | ___ | ___ | ~27 KB, ~15 % (largest run ≥ 0.9 KB) |
| 8 (reference, F′ §10.10) | STABLE 12/12 boots | — | not measured | — | — | — | ~20 KB, ~11 % (largest run ≥ 0.9 KB) |

## 5. What a result means

- **Published guidance** (research this session): no MicroPython maintainer, doc or web framework
  states a free-heap figure; the documented point is that the *largest free block* matters, not the
  total (a Pico W thread failed an allocation with 120 KB free and an 840 B largest block).
  General embedded practice keeps **20-30 % of the heap free at peak**. Record both numbers; the
  owner picks the limit.
- **A level where the stability arm is not STABLE**: record sizes, sites and rounds and carry on
  with the remaining levels — every level is its own boot, and the whole curve is what is asked for.
- **Idle free (post-collect) far from ~82 KB on F′**: the image or the boot is not what this file
  assumes; stop and record it.
