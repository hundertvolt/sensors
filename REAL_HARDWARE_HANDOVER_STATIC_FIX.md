# Real-hardware handover: the static-file fix and the shipped limit of 8, at the gc default

**Read this file alone.** It is the complete procedure for the next sitting: one build, one flash,
about 90 minutes including the full bench tier. Temporary: delete it once §4's table is filled in
and the results are migrated into `BENCH_SITTING_2026-09-23_HANDOVER.md` (or its successor) and
`REAL_HARDWARE_TEST_QUEUE.md` rows W3-W6. It supersedes
`REAL_HARDWARE_HANDOVER_CONNECTION_SCALING.md` §00, which asked for the same measurements before
the tool and the `chunk_bytes` parameter existed.

## 1. Why, in five lines

- On 2026-09-23 the board, at MicroPython's own `gc.threshold(-1)`, served only 4 concurrent
  requests reliably on the tip as it then was. **Every failure on the shipped image (limit 8) was the
  static page**: microdot's `send_file` read it 1,024 B at a time, each read a fresh 1,025 B
  allocation, and a failed one cut the page off behind a `200` with no `Content-Length`. No JSON route
  failed at any level up to 8 (`BENCH_SITTING_2026-09-23_HANDOVER.md` §10.6, §10.9).
- **Now**: static files are read in 256 B chunks and carry `Content-Length`; JSON pieces are capped
  at the same 256 B. Both come from **one** `WebserverService` parameter, `chunk_bytes` (default 256),
  so they cannot drift apart. `ext/microdot.py` is untouched (SPECIFICATION.md Part I.3).
- The question for silicon: **is the shipped image (limit 8) now stable at 8, at `gc.threshold(-1)`?**

## 2. Before anything

1. The owner's go-ahead **in your own conversation** (CLAUDE.md). Nothing here writes persistent
   config except what the bench tier's own default flags already do; no `--allow-persistence-writes`.
2. `DebugLevel = 5`.
3. **Read `GET /status`'s `errcount` and write it down before anything writes to the board.** Every
   device script below builds its own `AsyFramManager` over the same FRAM, so afterwards the log is
   not evidence (CLAUDE.md, the FRAM-log rule and its caveat).
4. Traps the last sitting paid for: a `pgrep -f`/`pkill -f` wait loop matches its own command line;
   `mpremote` does not reset the interpreter (the device scripts set `gc.threshold(-1)` themselves
   for exactly that reason, and every output must show `GC_THRESHOLD=-1`); a host load thread that
   outlives its test takes every later test down; two suites that bind real ports never overlap.

## 3. The procedure — image F′, the branch tip

| step | what | time |
| --- | --- | --- |
| 1 | `uv run scripts/build_firmware.py dev`, flash (`tests_hardware/README.md`). The build's own lwIP macro verification must pass with `MEMP_NUM_TCP_PCB` 11 / `MEMP_NUM_TCP_SEG` 64 / `MEM_SIZE` 16,000. Record the GC heap size (`__GcHeapEnd - __GcHeapStart`; the last image F was 187,712 B) | 10 min |
| 2 | Confirm the fix is on the wire: `curl -s -D - -o /tmp/idx.gz http://$DUT_IP/` shows `Content-Length: 9292` (dev's `index.html.gz`), and `gzip -t /tmp/idx.gz` passes. Same for `/js/app.js` (16,292 B) | 1 min |
| 3 | **H1** `uv run pytest tests_hardware/bench/test_serving_heap_at_default_gc.py -s`. Two tests: the per-source/route allocation need (now including `route:/`), and the ascending sweep N = 4, 6, 8, 10 on one boot, whose load now includes `/js/app.js` and which counts a response as served only if its body matches its `Content-Length` (`-truncated` / `-unframed` otherwise) | 12 min |
| 4 | **H2** the per-boot combined-load sweep: `DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py 2 4 5 5 6 6 7 7 8 8 --raw-dir <dir>` — one fresh boot per listed level, repeats deliberate (the pre-fix failures at 5-6 were probabilistic, 1 run in 2-3). Exit 0 only if every level is STABLE (every body complete, zero device allocation-failure lines). Commit the raw dir's summary lines verbatim, as §10.9 did | 35 min |
| 5 | **H3** only if H1 and H2 are clean: `uv run pytest tests_hardware/bench/test_end_to_end_timing.py -s` — `/status` now goes out as 29 writes instead of 11; compare with the sitting's own figures | 5 min |
| 6 | **H4** only if H1 and H2 are clean: the whole bench tier, default flags, `scripts/run_bench_hardware_suite.sh`. Read the *deselected* count, not only "clean" | 45 min |
| 7 | **Leave the board on F′.** | |

**Stop rule**: if H1 or H2 fails, record everything (sizes, sites, rounds, the device lines) and stop
before H3/H4 — which image to ship, and whether the limit moves, is the owner's decision.

**Not part of this sitting, owner's call**: re-measuring the ceiling on an over-provisioned image
(G′: `max_connections` 16, PCB 19 / SEG 128 / `MEM_SIZE` 32000, edited locally and never committed).
With the static path fixed, the next wall is the JSON pieces and microdot's own `Request` object
(~232 B); pre-fix, silicon G hit it at N = 10. One more build and flash.

## 4. Recording table

Twin figures are the 32-bit frozen Unix port with the board's own object sizes, at F's calibrated
heap, serving **dev's own website** (HEAP_FRAGMENTATION_MEASUREMENTS.md §7Q.14). The twin reproduced
the pre-fix failure exactly (first cut page at N = 6, on the 1,025 B read) but is **optimistic by two
levels or more near the wall**: pre-fix silicon G failed its first JSON route at 10, the twin at none
through 12.

| row | measurement | pre-fix silicon (§10.6/§10.9) | twin, fixed | `[HW]` |
| --- | --- | --- | --- | --- |
| H1 | need: `route:/` / worst JSON route / worst source | `/` not probed; JSON 320 B / ≤ 144 B | 320 B / 320 B / ≤ 192 B (pre-fix `/`: 1,536 B) | **320 B / 320 B (`/status`) / ≤ 160 B** — twin to the byte |
| H1 | sweep N = 4 / 6 / 8: device allocation lines | F: 11 × 1,025 B over the run | 0 / 0 / 0, every body complete | **0 / 0 / 0**, 48/72/96 × 200, every body = `Content-Length` |
| H1 | sweep N = 10: served complete + refused | 96 + 24, but truncated bodies counted as served | 96 + 24 refused, 0 lines (refusal not modelled by this twin build) | **96 + 24 refused, 0 lines** |
| H1 | idle largest free run, before vs after load | 10,080-15,232 → 7,008-9,760 B | — | **8,944-11,424 → 6,752-10,672 B** (free 82,128 → 80,720 B) |
| H2 | N = 2, 4: STABLE runs | 2: 1/1; 4: 2/2 (one host-side stall with no device line) | stable | **2: 1/1; 4: 1/1** |
| H2 | N = 5 (×2), 6 (×2): STABLE runs | 5: 2/3; 6: 1/2 — every failure `/`, 1,025 B | stable | **5: 3/3 device-clean** (1 host UNSTABLE = 0 B reference during the boot WLAN drop, all 12 flagged pages 9,292 B complete; 1 host tally lost to a torn heap map, device PASS, 0 lines) **; 6: 2/2** |
| H2 | N = 7 (×2), 8 (×2): STABLE runs | 7: 0/2; 8: 0/1 — every failure `/`, 1,025 B | stable at 8 (7 not run) | **7: 2/2; 8: 2/2** |
| H2 | any JSON-route failure at any level | none up to 8 | none up to 8 | **none up to 8** |
| H2 | host-side stalls with no device line (the pre-fix N = 4 `URLError`/timeout) | 2 in 4 runs at N = 4 | not modelled | **0 in 12 boots** |
| H3 | `/status` p50 / p95 | the sitting's own figures | not modelled | not run — deferred behind G′ (owner: 10 is the bar) |
| H4 | bench tier passed / skipped / deselected | 103 / 4 / 27 (image A, pre-fix) | — | not run — deferred behind G′ |

**Status of the tools as handed over**: `test_serving_heap_at_default_gc.py` and both its device
scripts were run end to end against the twin on this firmware (need test passes; sweep clean at
every level with every body complete). `combined_load_sweep.py` (committed by the hardware
session) was then run the same way — its own `run_level()` with the device script in the twin, on
this firmware and dev's site: **STABLE at N = 4, 6 and 8, every body complete, zero allocation
lines**. On the pre-fix firmware it reports UNSTABLE at N = 8, from its host-side body check alone
(`CATALOG_INSTRUMENTATION.md` §6).

**Result, 2026-09-23 evening** (`BENCH_SITTING_2026-09-23_HANDOVER.md` §10.10): F′ is stable
through its own ceiling of 8 — the static fix holds on silicon. **That is not the pass verdict**:
the owner restated that **10 concurrent connections must be stable on every run**, 8 being margin.
F′ refuses 2 of 10 by construction, so the question moved to G′ (§3's "not part of this sitting"),
now being run.

## 5. What a result means

- **H2 STABLE at every level through 8**: the shipped limit of 8 holds at the reactive default. The
  owner's target of 10 is then a question for G′ only.
- **Any `1025` line**: the firmware on the board is not the tip (step 2 would already have shown no
  `Content-Length`).
- **A failure at 256-257 B, 232 B (`microdot.py:383`) or in `_PieceWriter`**: the JSON wall has come
  down to ≤ 8 on silicon. That is the twin's optimism made concrete. Record the level and the site.
- **Host stalls with nothing on the device**, as at N = 4 before: a finding in its own right, not
  noise. Record the path, the round, and whether `/status` still answered afterwards.
