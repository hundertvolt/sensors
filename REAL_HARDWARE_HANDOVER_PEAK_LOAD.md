# Real-hardware handover: connection limit, peak load and heap margin — every result of 2026-09-23

**Read this file alone.** It collects every real-hardware result of 2026-09-23 on the dev board
(RP2040 Pico W, MicroPython 1.29, lwIP 2.2.1) for choosing the webserver's connection limit, and
says what is still open. Raw result lines are reproduced verbatim where they are the evidence.
`BENCH_SITTING_2026-09-23_HANDOVER.md` §10 holds the same material as a sitting log, in the order
it happened; this file is the result-oriented summary. Temporary: listed in BACKLOG.md item 45 and
removed with the others before the branch merges.

## 1. The owner's requirements and rules, as stated during the day

1. **The wish was 10 concurrent connections, stable on every run**, with the shipped 8 as safety
   margin. Measured result: **10 is not reachable on this heap** (§5.2, §5.4); the owner is now
   choosing a smaller limit and asked for the free heap and failure rates at 4-10 to decide.
2. **"No gc threshold" means MicroPython's own default, `gc.threshold(-1)`.** The device scripts set
   it themselves, because `mpremote` does not reset the interpreter and the boot entry's
   `gc.threshold(32768)` would otherwise still be in force. Every result line carries `GC_THRESHOLD=`.
   The peak series was also run at `gc.threshold(32768)` (the firmware's own value), on request.
3. **Peak load means maximum connection load coinciding with maximum internal load** — the shape of
   the hammer test (`tests_hardware/bench/test_memory_stress_bench.py`: back-to-back clients at the
   ceiling plus `PUT /sensors {"SGP40": {"SGPResetVOC": true}}` every 3 s).
4. **Under hammering, a refused connection (connection count saturated) is expected behaviour, not a
   failure. A memory error is a true failure.** The sweep tool counts them separately since §4.3.
5. Report **number and percentage** of failures, and heap usage as a **percentage** of the GC heap.

## 2. State at the end of the day

- **Board**: image **F′** (branch tip, `max_connections = 8`), build `2026-09-23T20:55:14Z`, reset to
  normal operation, serving at `192.168.85.57`, `DebugLevel` 5.
- **Repo**: branch `claude/tcp-connection-scaling`, everything pushed. `devices/dev.toml` and
  `toolchain/versions.toml` are at the tip (images G′ and H were local edits only, never committed;
  their recipes are in §3).
- **Not run** (stopped by the owner before the first level finished): F′ at N = 7 and 8 under peak
  load — §7 item 1.

## 3. The images

| image | what | `max_connections` | `MEMP_NUM_TCP_PCB` / `_SEG` / `MEM_SIZE` | GC heap, linker (`0x20040000 − __GcHeapStart`) | `mem_info` total |
| --- | --- | --- | --- | --- | --- |
| F | tip before the static-file fix | 8 | 11 / 64 / 16,000 | 187,712 B | 183,360 B |
| G | F + over-provisioned lwIP (local) | 16 | 19 / 128 / 32,000 | 169,120 B | — |
| **F′** | **tip with the static-file fix (`db1866e`, `740fab5`)** — the shipped config | 8 | 11 / 64 / 16,000 | 187,712 B | 183,360 B |
| G′ | F′ + G's lwIP (local, handover §0.3) | 16 | 19 / 128 / 32,000 | 169,120 B | — |
| **H** | F′ + lwIP sized for exactly 10 (local) | 10 | 13 / 80 / 20,000 | 183,064 B | 178,816 B |

- All other lwIP macros are the tip's: PCB_LISTEN 8, PBUF 16, PBUF_POOL 16, UDP_PCB 5, STATS 0,
  TCP_MSS 800, TCP_WND 6,400, TCP_SND_BUF 6,400. Every image's macros were read back out of the
  firmware translation unit and matched; the ensemble check (`micropython_overrides.
  check_lwip_ensemble`) passed at each image's `max_connections`.
- H is the minimum coherent set for 10: PCB = limit + 3 (F′'s margin), SEG ≥ 10 × (SND_BUF / MSS)
  = 80, `MEM_SIZE` ≥ 10 × 2,000 B floor = 20,000.
- **Each connection of lwIP capacity costs exactly 2,324 B of GC heap** (static `.bss`): H is
  2 × 2,324 B below F′, G′ 8 × 2,324 B. The `mem_info` total is 4,352 B below the linker figure
  (the GC's own allocation and finaliser tables). **Percentages below are of the `mem_info` total.**
- Build: `uv run scripts/build_firmware.py dev`; flash: `Board().enter_bootloader()` then
  `picotool load -x -v build/firmware-dev.uf2`.

## 4. The instruments

### 4.1 `tests_hardware/combined_load_sweep.py` — one fresh boot per listed level

`DUT_IP=<ip> uv run python tests_hardware/combined_load_sweep.py <levels…> [--threshold T] [--peak] [--margin] [--raw-dir d]`

It runs `device_scripts/serving_stability_under_combined_load.py` (the real production task graph)
with `gc.threshold(T)` substituted (default −1), and drives load from the host. Path mix:
`/status /sensors / /measurements /status /networking /sensors /system /js/app.js`. Static bodies
(`/` 9,292 B, `/js/app.js` 16,292 B) must equal an idle reference fetch; JSON bodies must parse.
Between levels: `kick_all_stations()`, hard reset, 45 s settle.

| mode | load | device sampler | verdict is evidence? |
| --- | --- | --- | --- |
| (default) "rounds" | 12 rounds of N parallel GETs, 0.5 s pause between rounds; no forced internal work | full heap map (`mem_info(1)`) every ~5.3 s, no collect | yes |
| `--margin` | rounds | heap map every ~5.3 s after `gc.collect()` | no (the collect cleans the heap) |
| `--peak` | **N threads back to back for 60 s; thread 0 swaps one GET for the SGP40 reset PUT every 3 s** | 20 ms low-water sampler, never collects (§4.2) | **yes** |
| `--peak --margin` | peak | same sampler, `gc.collect()` before every read, 100 ms apart | no |

- **STABLE** = zero true failures (anything but `ok` and `refused`) and zero device lines matching
  `harness.MEMORY_ERROR_MARKERS`. A connection closed at the ceiling before any response
  (`http_client.is_ceiling_close()`, the hammer test's own classification) is `refused`, printed
  separately as expected (§1 rule 4). Result lines of runs before this rule print "failed" including
  refusals; the tables below separate them.
- The reference fetch is accepted only as a 200 whose non-empty body equals its `Content-Length`
  (every device-script boot drops and rejoins WLAN at ~6 s uptime and a reference once came back 0 B).
- A torn heap-map capture is reported, not fatal.
- **`refused` is cross-checked on the device** (added after this day's runs): in `--peak` the device
  script counts every `_serve()` reject-when-full close and prints it as `PEAK_SUMMARY … rejected=K`;
  the tool prints `refusals cross-check: host counted R, device rejected K`. `is_ceiling_close()`
  books any reset without a response as a refusal, so **R > K means resets the ceiling did not
  cause** (lwIP, a crash between accept and response) hiding among the "expected" ones. Validated
  in the twin: limit 4, 6 clients, host 1,549 resets = device 1,549 rejections.
- **`--margin`'s printed idle and median are fixed** (same commit): idle is now the settled idle (the
  window's last third), and min/median span only the load window (every sample up to the last one
  below 95 % of that idle) — the re-derivation of §5.3, done by the tool.

### 4.2 The peak sampler, and what its heap figure is worth

`_peak_sampler()` reads `gc.mem_free()` and the webserver's open-connection count every 20 ms and
prints only at a new minimum (`PEAK_NEW_MIN` + `mem_info()`), then `PEAK_SUMMARY` and one `PEAK_AT
conns=k samples=… min_free_after_gc=…` line per connection count seen.

- **Without `--margin` its failure counts and verdict are evidence, its heap figure is not.** It takes
  a rise of ≥ 2 KB between two reads as a GC and that reading as "heap minus live set". Under load
  the sampler ran every ~60 ms (not 20) while the heap churned ~250 KB/s at −1, so the reading lands
  anywhere in the refill and **understates free heap by up to ~15-30 KB** — visible at 0 open
  connections, where it read 47.8 KB against a settled idle of ~77 KB. An exact GC signal does not
  exist on this build: user-class instances are never allocated with the finaliser bit
  (`py/objtype.c`), so `__del__` never runs on them, and `MICROPY_PY_WEAKREF` is enabled only at the
  EVERYTHING ROM level (rp2 builds EXTRA_FEATURES).
- **With `--margin` the heap figure is exact** (the live set at each 100 ms collect), and the
  per-connection-count histogram proves it was taken at the ceiling; the collects make the threshold
  irrelevant and the verdict instrumentation only.
- The open-connection count **includes connections still closing** (§6.3), so it can exceed N.

### 4.3 Other instruments used

- `tests_hardware/bench/test_serving_heap_at_default_gc.py` — per-source/route allocation need, and
  an ascending sweep on one boot (levels 4, 6, …, ceiling + 2). Its assertion message keeps only the
  last 2,000 characters of device output, and its host tallies print after that assertion, so a
  failing sweep does not say which level broke.
- Largest free block: `mem_info()`'s `max free sz` is in 16 B blocks.

## 5. Results

### 5.1 The static-file fix on silicon (image F′): it holds

Before the fix (image F): the verified maximum at −1 was **4**; every failure up to 8 was the static
page, cut off behind a `200` with no `Content-Length` (microdot's `send_file` allocating 1,025 B per
1,024 B read). Fix: 256 B reads plus `Content-Length`, one `chunk_bytes` parameter shared with the
JSON pieces.

- On the wire: `/` → `Content-Length: 9292`, `/js/app.js` → `16292`, both pass `gzip -t`.
- Need test: **`route:/` 320 B** (was 1,536 B), `route:/status` 320 B, `/measurements` and
  `/sensors` 256 B, `/networking` 192 B, `/system` and `/notification` 160 B, every `errcount:*`
  96 B — the twin's figures to the byte.
- One-boot sweep, ceiling 8: N=4/6/8 → 48/72/96 × 200, every body equal to its `Content-Length`;
  N=10 → 96 + 24 refused; **0 allocation failures**. Idle largest free run before/after load
  8,944-11,424 → 6,752-10,672 B; free 82,128 → 80,720 B.
- Rounds sweep, one boot per level, 12 boots at 2/4/5/5/6/6/7/7/8/8 (+ 5/5 re-run): **zero device
  allocation lines in every boot**, no `1025` read, no JSON-route failure. One host UNSTABLE at N=5
  was the tool's own 0 B reference fetch during the boot-time WLAN drop (all 12 flagged pages were
  9,292 B, complete); one re-run's host tally was lost to a torn heap map (device side clean).

### 5.2 10 connections with over-provisioned lwIP (image G′): fails

One-boot sweep 4…18: **FAILED — the heap ran out entirely.** At uptime 381 s: `SCD30 PrintLog:
History write failed!`, `SCD30 Error reading config from sensor: memory allocation failed,
allocating 80 bytes`, the same for BMP3XX at 68 B, a route-handler `MemoryError` at 138 B in
`_get_sensors` → `_stream_dict_response` → `_PieceWriter.add_value` → `add`, and the device script
itself: `RESULT: FAIL MemoryError('memory allocation failed, allocating 72 bytes')`. Which level
broke is not recorded (§4.3).

Rounds sweep, one boot per level:

| N | complete | device allocation lines | failures |
| --- | --- | --- | --- |
| 8 | 94/96 | 4 | 2 × `/status` 500 (251, 256 B) |
| 10 | 106/120 | 28 | 14 × `/status` 500, every round |
| 10 | 107/120 | 26 | 13 × `/status` 500, every round |
| 10 | 108/120 | 24 | 12 × `/status` 500, every round |
| 12 | 120/144 | 47 | 21 × `/status` 500, 1 × `/sensors` 400, 1 timeout, 1 × `/` cut after headers; a supervised task restart and a BMP3XX read failure |
| 12 | 117/144 | 42 | 16 × `/status` 500, 1 × `/measurements` 500, 3 × 400, 5 × `/` and 4 × `/js/app.js` cut (`IncompleteRead` — now visible thanks to `Content-Length`) |

Every 500 at 8 and 10: `_get_status` → `_build_status_pieces` → `_write_errcount_entry` →
`_PieceWriter.add_value` → `add` → `flush`, failing to allocate one joined piece of 242-257 B. At 12
the 400s are microdot failing its 232 B `Request`.

### 5.3 Free heap under the rounds load (sampled — overstates free heap at the true peak)

`--margin` runs, re-derived from the raw maps (load window = samples up to the last one below
76,000 B; settled idle = median of the samples after it). The tool's own printed "idle" (a mid-boot
sample) and "median under load" (spanning the post-load idle) are mislabelled and not used.

| image | N | verdict (non-collecting arm) | settled idle | **min free under load** | median under load | min largest free run | load uses at most |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F′ | 4 | STABLE 48/48 | 82,528 B (45.0 %) | 61,136 B (33.3 %) | 63,840 B (34.8 %) | 2,192 B | 21,392 B |
| F′ | 5 | STABLE 60/60 | 82,592 B (45.0 %) | 50,784 B (27.7 %) | 63,096 B (34.4 %) | 1,760 B | 31,808 B |
| F′ | 6 | STABLE 72/72 | 82,528 B (45.0 %) | 47,200 B (25.7 %) | 60,256 B (32.9 %) | 1,728 B | 35,328 B |
| F′ | 7 | STABLE 84/84 | 82,592 B (45.0 %) | 45,168 B (24.6 %) | 50,016 B (27.3 %) | 1,200 B | 37,424 B |
| F′ | 8 | STABLE 96/96 | 82,656 B (45.1 %) | 37,872 B (20.7 %) | 48,944 B (26.7 %) | 992 B | 44,784 B |
| H | 8 | STABLE 96/96 | 78,112 B (43.7 %) | 38,000 B (21.3 %) | 44,096 B (24.7 %) | 1,408 B | 40,112 B |
| H | 9 | STABLE 108/108 | 77,472 B (43.3 %) | 34,800 B (19.5 %) | 56,528 B (31.6 %) | 1,024 B | 42,672 B |
| H | 10 | **UNSTABLE 117/120** (3 × `/status` 500, 249-257 B, in both arms) | 77,600 B (43.4 %) | 20,592 B (11.5 %) | 24,208 B (13.5 %) | 288 B | 57,008 B |

- Twin estimate on F′ for comparison: 6 ≈ 38 KB (20 %), 7 ≈ 27 KB (15 %), 8 ≈ 20 KB (11 %).
- 6-9 samples 5.3 s apart per load window, and pauses between rounds: **these minimums are not the
  peak** (the owner asked; §5.5 is the peak).

### 5.4 Peak load (image H, `--peak`, non-collecting sampler): failures

60 s of N back-to-back clients plus the SGP40 reset PUT every 3 s, one boot per row.

| N | threshold | requests | refused (expected) | **true failures** | of which `/status` 500 (piece, 252-257 B) | device allocation lines | GCs in window |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 6 | −1 | 132 | 0 | **0 (0.00 %)** | 0 | 0 | 206 |
| 7 | −1 | 133 | 0 | **0 (0.00 %)** | 0 | 0 | 219 |
| 8 | −1 | 133 | 1 | **0 (0.00 %)** | 0 | 0 | 245 |
| 9 | −1 | 180 | 53 | **3 (1.67 %)** | 3 | 6 | 267 |
| 6 | 32768 | 118 | 0 | **0 (0.00 %)** | 0 | 0 | 410 |
| 7 | 32768 | 125 | 0 | **0 (0.00 %)** | 0 | 0 | 416 |
| 8 | 32768 | 128 | 7 | **1 (0.78 %)** | 1 | 2 | 407 |
| 9 | 32768 | 185 | 60 | **6 (3.24 %)** | 6 | 12 | 395 |

(Device lines come in pairs per failure: the `MemoryError` and the `WEBSERVER Unhandled exception in
route handler` line.) Largest free block at the sampler's minimum: −1: 704 / 816 / 704 / 736 B;
32768: 3,600 / 1,520 / 448 / 672 B (N = 6 / 7 / 8 / 9) — at a biased minimum, §4.2.

Verbatim (run before the refusal rule, so "failed" includes refusals; `device: WEBSERVER …` lines
omitted):

```
N= 6 GC_THRESHOLD=-1 | STABLE | complete 132/132 | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=4458ms conns=6 free=6912): No. of 1-blocks: 4424, 2-blocks: 492, max blk sz: 64, max free sz: 44
     PEAK_SUMMARY heap=178816 min_free_after_gc=6912 collections=206
     PEAK_AT conns=0 samples=3524 min_free_after_gc=47840
     PEAK_AT conns=1 samples=10 min_free_after_gc=63808
     PEAK_AT conns=4 samples=6 min_free_after_gc=44720
     PEAK_AT conns=5 samples=3 min_free_after_gc=-1
     PEAK_AT conns=6 samples=684 min_free_after_gc=6912
     PEAK_AT conns=7 samples=274 min_free_after_gc=18176
     PEAK_AT conns=8 samples=22 min_free_after_gc=34448
     PEAK_AT conns=9 samples=1 min_free_after_gc=30736
N= 7 GC_THRESHOLD=-1 | STABLE | complete 133/133 | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=56399ms conns=6 free=15936): No. of 1-blocks: 3977, 2-blocks: 498, max blk sz: 64, max free sz: 51
     PEAK_SUMMARY heap=178816 min_free_after_gc=15936 collections=219
     PEAK_AT conns=0 samples=3502 min_free_after_gc=57264
     PEAK_AT conns=1 samples=2 min_free_after_gc=-1
     PEAK_AT conns=2 samples=9 min_free_after_gc=60960
     PEAK_AT conns=3 samples=7 min_free_after_gc=-1
     PEAK_AT conns=4 samples=4 min_free_after_gc=54144
     PEAK_AT conns=5 samples=11 min_free_after_gc=40912
     PEAK_AT conns=6 samples=4 min_free_after_gc=15936
     PEAK_AT conns=7 samples=635 min_free_after_gc=18096
     PEAK_AT conns=8 samples=272 min_free_after_gc=18768
     PEAK_AT conns=9 samples=35 min_free_after_gc=16448
     PEAK_AT conns=10 samples=5 min_free_after_gc=24624
N= 8 GC_THRESHOLD=-1 | UNSTABLE | complete 132/133 | failed 1 (0.75 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=37046ms conns=8 free=16384): No. of 1-blocks: 3215, 2-blocks: 549, max blk sz: 64, max free sz: 44
     PEAK_SUMMARY heap=178816 min_free_after_gc=16384 collections=245
     PEAK_AT conns=0 samples=3479 min_free_after_gc=48528
     PEAK_AT conns=1 samples=12 min_free_after_gc=-1
     PEAK_AT conns=2 samples=2 min_free_after_gc=70464
     PEAK_AT conns=3 samples=20 min_free_after_gc=55568
     PEAK_AT conns=4 samples=3 min_free_after_gc=52368
     PEAK_AT conns=5 samples=1 min_free_after_gc=-1
     PEAK_AT conns=7 samples=2 min_free_after_gc=-1
     PEAK_AT conns=8 samples=555 min_free_after_gc=16384
     PEAK_AT conns=9 samples=296 min_free_after_gc=18112
     PEAK_AT conns=10 samples=39 min_free_after_gc=18432
     1 x /system ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
N= 9 GC_THRESHOLD=-1 | UNSTABLE | complete 124/180 | failed 56 (31.11 %) | device allocation-failure lines 6 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=14889ms conns=9 free=8736): No. of 1-blocks: 4020, 2-blocks: 541, max blk sz: 64, max free sz: 46
     PEAK_SUMMARY heap=178816 min_free_after_gc=8736 collections=267
     PEAK_AT conns=0 samples=3443 min_free_after_gc=55088
     PEAK_AT conns=1 samples=8 min_free_after_gc=72704
     PEAK_AT conns=2 samples=5 min_free_after_gc=-1
     PEAK_AT conns=3 samples=9 min_free_after_gc=55664
     PEAK_AT conns=4 samples=12 min_free_after_gc=51696
     PEAK_AT conns=5 samples=9 min_free_after_gc=41968
     PEAK_AT conns=6 samples=1 min_free_after_gc=40528
     PEAK_AT conns=7 samples=11 min_free_after_gc=27216
     PEAK_AT conns=8 samples=6 min_free_after_gc=22016
     PEAK_AT conns=9 samples=545 min_free_after_gc=8736
     PEAK_AT conns=10 samples=297 min_free_after_gc=14640
     3 x / ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     7 x /js/app.js ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     4 x /measurements ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     9 x /networking ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     11 x /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     10 x /status ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     3 x /status status500
     5 x /system ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     4 x PUT /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     device: MemoryError: memory allocation failed, allocating 255 bytes
     device: MemoryError: memory allocation failed, allocating 253 bytes
     device: MemoryError: memory allocation failed, allocating 253 bytes
N= 6 GC_THRESHOLD=32768 | STABLE | complete 118/118 | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=27919ms conns=9 free=18320): No. of 1-blocks: 3007, 2-blocks: 518, max blk sz: 64, max free sz: 225
     PEAK_SUMMARY heap=178816 min_free_after_gc=18320 collections=410
     PEAK_AT conns=0 samples=3431 min_free_after_gc=51344
     PEAK_AT conns=1 samples=8 min_free_after_gc=44464
     PEAK_AT conns=2 samples=2 min_free_after_gc=-1
     PEAK_AT conns=3 samples=1 min_free_after_gc=39808
     PEAK_AT conns=4 samples=2 min_free_after_gc=-1
     PEAK_AT conns=5 samples=2 min_free_after_gc=34992
     PEAK_AT conns=6 samples=662 min_free_after_gc=20336
     PEAK_AT conns=7 samples=229 min_free_after_gc=28832
     PEAK_AT conns=8 samples=37 min_free_after_gc=18560
     PEAK_AT conns=9 samples=5 min_free_after_gc=18320
N= 7 GC_THRESHOLD=32768 | STABLE | complete 125/125 | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=33161ms conns=7 free=14080): No. of 1-blocks: 3452, 2-blocks: 522, max blk sz: 64, max free sz: 95
     PEAK_SUMMARY heap=178816 min_free_after_gc=14080 collections=416
     PEAK_AT conns=0 samples=3363 min_free_after_gc=59920
     PEAK_AT conns=1 samples=9 min_free_after_gc=70352
     PEAK_AT conns=2 samples=1 min_free_after_gc=-1
     PEAK_AT conns=3 samples=1 min_free_after_gc=-1
     PEAK_AT conns=4 samples=15 min_free_after_gc=49552
     PEAK_AT conns=5 samples=16 min_free_after_gc=47184
     PEAK_AT conns=6 samples=9 min_free_after_gc=44640
     PEAK_AT conns=7 samples=597 min_free_after_gc=14080
     PEAK_AT conns=8 samples=258 min_free_after_gc=16224
     PEAK_AT conns=9 samples=35 min_free_after_gc=17056
     PEAK_AT conns=10 samples=3 min_free_after_gc=30768
N= 8 GC_THRESHOLD=32768 | UNSTABLE | complete 120/128 | failed 8 (6.25 %) | device allocation-failure lines 2 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=35678ms conns=9 free=8832): No. of 1-blocks: 3164, 2-blocks: 527, max blk sz: 64, max free sz: 28
     PEAK_SUMMARY heap=178816 min_free_after_gc=8832 collections=407
     PEAK_AT conns=0 samples=3427 min_free_after_gc=61184
     PEAK_AT conns=1 samples=4 min_free_after_gc=-1
     PEAK_AT conns=2 samples=1 min_free_after_gc=-1
     PEAK_AT conns=3 samples=6 min_free_after_gc=52384
     PEAK_AT conns=4 samples=1 min_free_after_gc=48384
     PEAK_AT conns=5 samples=1 min_free_after_gc=-1
     PEAK_AT conns=6 samples=13 min_free_after_gc=24496
     PEAK_AT conns=7 samples=1 min_free_after_gc=-1
     PEAK_AT conns=8 samples=569 min_free_after_gc=11968
     PEAK_AT conns=9 samples=231 min_free_after_gc=8832
     PEAK_AT conns=10 samples=50 min_free_after_gc=19264
     1 x / ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     2 x /networking ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     2 x /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     1 x /status ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     1 x /status status500
     1 x PUT /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     device: MemoryError: memory allocation failed, allocating 257 bytes
N= 9 GC_THRESHOLD=32768 | UNSTABLE | complete 119/185 | failed 66 (35.68 %) | device allocation-failure lines 12 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=47587ms conns=9 free=10064): No. of 1-blocks: 3333, 2-blocks: 566, max blk sz: 64, max free sz: 42
     PEAK_SUMMARY heap=178816 min_free_after_gc=10064 collections=395
     PEAK_AT conns=0 samples=3371 min_free_after_gc=70288
     PEAK_AT conns=1 samples=10 min_free_after_gc=72736
     PEAK_AT conns=2 samples=2 min_free_after_gc=-1
     PEAK_AT conns=3 samples=3 min_free_after_gc=53024
     PEAK_AT conns=4 samples=21 min_free_after_gc=52544
     PEAK_AT conns=5 samples=1 min_free_after_gc=-1
     PEAK_AT conns=6 samples=15 min_free_after_gc=41760
     PEAK_AT conns=7 samples=1 min_free_after_gc=-1
     PEAK_AT conns=8 samples=11 min_free_after_gc=27680
     PEAK_AT conns=9 samples=512 min_free_after_gc=10064
     PEAK_AT conns=10 samples=266 min_free_after_gc=14096
     5 x / ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     9 x /js/app.js ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     6 x /measurements ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     7 x /networking ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     10 x /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     12 x /status ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     6 x /status status500
     6 x /system ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     5 x PUT /sensors ConnectionResetError:ConnectionResetError(104, 'Connection reset by peer')
     device: MemoryError: memory allocation failed, allocating 253 bytes
     device: MemoryError: memory allocation failed, allocating 253 bytes
     device: MemoryError: memory allocation failed, allocating 254 bytes
     device: MemoryError: memory allocation failed, allocating 252 bytes
```

### 5.5 Peak load, exact live set (image H, `--peak --margin`): only N = 6 measured

```
N= 6 GC_THRESHOLD=-1 | STABLE | complete 132/132 | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=52054ms conns=8 free=25360): No. of 1-blocks: 2874, 2-blocks: 491, max blk sz: 64, max free sz: 138
     PEAK_SUMMARY heap=178816 min_free_after_gc=25360 collections=1045
     PEAK_AT conns=0 samples=738 min_free_after_gc=75056
     PEAK_AT conns=1 samples=1 min_free_after_gc=66384
     PEAK_AT conns=3 samples=4 min_free_after_gc=48256
     PEAK_AT conns=5 samples=2 min_free_after_gc=41008
     PEAK_AT conns=6 samples=208 min_free_after_gc=26288
     PEAK_AT conns=7 samples=83 min_free_after_gc=30832
     PEAK_AT conns=8 samples=7 min_free_after_gc=25360
     PEAK_AT conns=9 samples=2 min_free_after_gc=47840
```

- **At peak, 6 clients on H leave 25,360 B free — 14.2 % of 178,816 B** — with a largest free block
  of 2,208 B; 26,288 B (14.7 %) at exactly 6 open. Idle at 0 open: 75,056 B (42.0 %).
- The rounds figure for N = 6 (§5.3: 47,200 B, 25.7 %, on F′) overstated free heap at the true
  peak by ~20 KB (~4.6 KB of the difference is F′'s larger heap).
- 7, 8, 9 were not measured: the owner stopped the run to prioritise the image built for 8 (§7).

## 6. Findings

1. **The wall is the `/status` JSON piece, not the static files any more.** Every true failure at
   8-10 on every image is `/status` failing to allocate one 242-257 B `_PieceWriter` piece
   (`chunk_bytes` = 256). No other route failed at those levels; bodies that were served were
   complete. At 12 the failures spread to microdot's 232 B `Request` (400s), static bodies cut after
   their headers, and non-web tasks.
2. **10 needs more heap than the board has.** G′ (169,120 B) fails 3/3 at 10 with ~1 `/status` in 10
   failing every round; H (183,064 B) still fails 10 in both arms (3 per run); the step 9 → 10 costs
   ~14 KB under rounds load against ~3 KB for 8 → 9.
3. **The connection counter includes closing connections.** `_serve()` decrements `_open_conns` only
   after `_close_writer()` (bounded `wait_closed()`), while the client already has its complete body
   (`Content-Length`) and has opened its next connection. With 8 back-to-back clients on H the count
   sat at 8 for ~560 samples, at 9 for ~230-300, at 10 for ~40-50 — so a limit of N refuses some of
   N back-to-back clients. Expected behaviour by the owner's rule; **whether the count should drop
   when the response is written instead of at close is a design question for the owner — not
   changed** (closing connections still hold lwIP PCBs, which is why the limit sits below
   `MEMP_NUM_TCP_PCB`).
4. **Throughput is flat at ~2.2 requests/s from 6 to 9 clients** under peak load: the board is the
   bottleneck; more clients only lengthen each request (and hold more heap at once).
5. **`gc.threshold(32768)` vs −1 under peak load**: ~1.7-2× the collections; more contiguous space at
   6 clients; **no fewer failures** (8: 1 vs 0; 9: 6 vs 3) — single runs, not separable from chance.
6. **Rounds load understates peak memory use by ~20 KB at 6 clients** (§5.5 vs §5.3): pauses between
   rounds and 5 s snapshots miss the moment when all N allocate at once.
7. **The board fell back to hotspot mode after a reset three times** (after a likely watchdog reset
   between two tests, after flashing F′, after flashing H), with the bench AP up and no station
   associated; `kick_all_stations()` + hard reset recovered it (once only on the second try). Not
   investigated.
8. **Likely watchdog reset**: a new `mpremote` session attached ~30 s after a test's own teardown
   reset, and the board reset ~9 s later (the 8,388 ms WDT), so the next test died on
   `OSError: [Errno 5]`. Cause not confirmed; leave > 45 s between runs.
9. **An empty `200` with no `Content-Length` came back twice** from an idle `GET /` fetched during the
   boot-time WLAN drop. The static route always sends `Content-Length`, so it cannot have come from
   `_serve_static()`; origin unexplained.
10. **Twin vs board**: the twin was optimistic about the wall (pre-fix G failed JSON at 10, the twin
    at none through 12) but pessimistic about free heap under rounds load (board +9 KB at 6, +18 KB
    at 7).

## 7. Open — next sitting

1. **Image built for 8 (F′), N = 7 and 8, peak load** (owner's request, not started): four commands,
   one boot per level, ~30 min:
   `… combined_load_sweep.py 7 8 --peak`, `… --peak --threshold 32768`,
   `… --peak --margin`, `… --peak --margin --threshold 32768`. Expected against H at 8: fewer
   connections in flight (anything above 8, closing ones included, is refused before a handler runs)
   and 4,648 B more heap — fewer memory failures, more refusals.
2. **The exact peak live set at 7, 8 (and 9 on H)** — `--peak --margin`; only N = 6 exists (§5.5).
3. **Repeats**: every peak row is one run. The 0-vs-1 failure differences at 8 need ≥ 3 boots per
   cell before they mean anything.
4. **Owner decisions**: the limit itself; whether `_open_conns` should drop at response-written
   (§6.3); whether to reduce what `/status` needs (a smaller `chunk_bytes`, or less per piece).
5. Deferred from the static-fix handover: H3 (`/status` p50/p95, `test_end_to_end_timing.py`) and
   H4 (full bench tier) on F′.

## 8. Traps paid for today

- `pkill -f` / `pgrep -f` with a pattern that also appears in the calling shell's own command line
  kills or matches that shell. List by PID (`ps … | awk '/[p]attern/'`) instead.
- `mpremote` does not reset the interpreter — every device script sets its own `gc.threshold`.
- Every device-script boot drops and rejoins WLAN at ~6 s uptime; the host's first "is it up"
  probe can succeed on the old link.
- Device scripts build their own `AsyFramManager` over the same FRAM, so `errcount` read after one is
  context, not evidence. Before today's runs it read (board on G′, uptime 4,666 s): WIFI 14, UART_init
  117, UART_resp 124, SGP40 10, NTP 11, SYSTEM 14, BMP3XX 12, WEBSERVER 412 (E4 = route-handler
  exceptions, E1 = unexpected connection errors), everything else 0.
- The pytest bench sweep truncates device output to 2,000 characters in its assertion message.
- A Python process already running keeps its loaded code; a new `combined_load_sweep.py` invocation
  re-reads both the tool and the device script, so do not edit either while a chained run is between
  invocations.
