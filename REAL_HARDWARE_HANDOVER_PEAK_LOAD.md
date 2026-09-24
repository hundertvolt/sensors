# Real-hardware handover: connection limit, peak load and heap margin — every result of 2026-09-23/24

**Read this file alone.** It collects every real-hardware result of 2026-09-23 and 2026-09-24 on the dev board
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

## 1a. Scope: what exactly was tested, and what was not

Stated explicitly after the owner asked (2026-09-24) whether every test served all ports over
Microdot with no cap but lwIP's, at `gc.threshold(-1)`, hammered concurrently with high internal
load. The answer is **not entirely**; every figure in this file must be read with this scope.

1. **The application's own connection cap was in front of Microdot in every run.** Not only lwIP's
   caps applied:
   - `WebserverService._serve()` (`src/asy_webserver_service.py`) refused every connection above the
     image's `max_connections` (6, 7, 8, 10 or 16). **All refusals in this file come from that check**,
     not from lwIP; the device's own rejection count matches the host's within the known
     counter-installation gap (§6.5 item 16).
   - The lwIP caps never bound: every image carried `MEMP_NUM_TCP_PCB` = limit + 3 (G′: 19 for 16).
   - The production webserver's other bounds were active too: a listen queue (`backlog`) of
     `max_connections + 1`, a 5 s per-call read/write timeout, and a 15 s cap on each connection.
   - Microdot itself (`ext/microdot.py`) has no connection cap; this firmware does not use its
     `start_server()` but passes each accepted connection to `Microdot.handle_request()`.
   - **So the results describe the production webserver at limit N**, the value being chosen. An
     uncapped Microdot was never tested; that would need a code change, and the lwIP slots (or the
     heap) would then be the only bound.
2. **HTTP on port 80 only — not all ports.** The load mix: `/status` (twice per cycle), `/sensors`
   (twice), `/measurements`, `/networking`, `/system`, the static `/` (9,292 B) and `/js/app.js`
   (16,292 B); the only write is `PUT /sensors {"SGP40": {"SGPResetVOC": true}}` (dispatch-only,
   nothing persisted). **Not in the load**: `/notification`, every other PUT, and every other port
   (e.g. the captive-portal DNS on 53).
3. **`gc.threshold(-1)` for every verdict, with two labelled exceptions.** Every result line carries
   `GC_THRESHOLD=`: the `32768` series (H at 6-9, F′ at 7-8) were run on request and are labelled
   so. The collecting runs (`--margin`, `--peak --margin`) call `gc.collect()` before each sample
   (every 5 s in rounds mode, every 100 ms in peak mode); they are instrumentation, and their
   stability verdict is not counted as evidence (§8.2).
4. **Hammering — only in the peak runs.**
   - **Peak runs** (`--peak`: §5.4-§5.8, i.e. H at 6-9 and everything from 2026-09-24): N clients back
     to back for 60 s at the limit, no pauses.
   - **Not hammering**: every earlier series (§5.1-§5.3: the static-fix verification, G′, F′ at 4-8,
     H at 8-10) used rounds of N parallel requests with 0.5 s pauses, and is labelled "sampled, not
     peak".
5. **Internal load: the full production task graph plus the hammer test's trigger — not every
   internal load forced at once.**
   - Running throughout: `sensortask_dev.main()`'s whole task graph — SCD30, SGP40, BMP3XX, ISL29125,
     FRAM logging, NeoPixel, notifications, the WiFi and NTP services, the UART link pair with its
     continuous exerciser traffic, and the task supervisor.
   - Forced on top: the SGP40 reset PUT every 3 s (the hammer test's own internal-work trigger,
     `tests_hardware/bench/test_memory_stress_bench.py`).
   - **Not forced into the load window**: an NTP sync, a WLAN reconnect, an SCD30 read, an SGP40
     backup, a FRAM block write — each coincided with the load only as its normal schedule made it.
     This is the hammer test's definition of peak, not the maximum of every internal load at the
     same instant.
6. **The device script, not the production entry point, ran the task graph.**
   - It was started through `mpremote`; `run_isolated()` arms its own `machine.WDT(timeout=8000)`
     around every device script (production arms the same 8 s watchdog itself).
   - The script's own compiled code and globals cost **2,720 B** of heap that the frozen production
     `main.py` does not (§5.7); heap figures are given measured and production-equivalent.
   - Every device-script boot drops and rejoins WLAN at ~6 s uptime, before the load starts.

## 2. State (updated 2026-09-24)

- **Board**: image **E6** (built for 6, local edits only — recipe in §5.8), build
  `2026-09-24T05:20:20Z`, serving at `192.168.85.57`, `DebugLevel` 5. **The tip is now the limit-6
  configuration (E6′, owner's decision 2026-09-24)**; its confirmation is `REAL_HARDWARE_HANDOVER_LIMIT_6.md`.
- **Repo**: branch `claude/tcp-connection-scaling`, everything pushed. `devices/dev.toml` and
  `toolchain/versions.toml` are at the tip (images G′ and H were local edits only, never committed;
  their recipes are in §3).

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
| `--peak --no-sampler` | peak | **none** (no maps, no sampler, no rejection counter); prints the script's heap footprint once before boot | **yes** — the instrumentation control (§5.7) |

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

### 5.6 Peak load on the image built for 8 (F′), N = 7 and 8 — run 2026-09-24

Owner's request: an image built for 8, N = 7 and 8, at `-1` and at `32768`, true failures (refusals
excluded) and heap usage in %. Board on F′ (build `2026-09-23T20:55:14Z`, unchanged firmware since),
heap base 183,360 B (`mem_info`). Four runs, one fresh boot per level, with the tool of `53ac222`
(refusal cross-check). **Every row is one run.**

**True failures** — non-collecting sampler, so the verdict is evidence:

| N | threshold | requests | complete | refused (host / device) | **true failures** | what failed |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | −1 | 170 | 123 | 47 / 47 | **0 (0.00 %)** | — |
| 8 | −1 | 366 | 105 | 259 / 246 | **2 (0.55 %)** | 2 × `/status` 500, 252 B piece |
| 7 | 32768 | 167 | 120 | 47 / 45 | **0 (0.00 %)** | — |
| 8 | 32768 | 338 | 99 | 238 / 228 | **1 (0.30 %)** | 1 × `/status` 500, 255 B piece |

**Heap usage at peak** — collecting sampler (`--peak --margin`, `gc.collect()` every 100 ms; exact
live set; its verdict is instrumentation only, and the threshold is moot under it):

| N | threshold | min free overall (at conns) | **% free / % used** | min free with exactly N open | largest free block at the min | failures in this run |
| --- | --- | --- | --- | --- | --- | --- |
| 7 | −1 | 26,112 B (6) | **14.2 % / 85.8 %** | 28,128 B (15.3 %) | 1,440 B | 0 of 188 (54 refused) |
| 8 | −1 | 18,560 B (8) | **10.1 % / 89.9 %** | 18,560 B (10.1 %) | 512 B | 1 of 391 (0.26 %; 274 refused), `/status` 254 B |
| 7 | 32768 | 20,976 B (8) | **11.4 % / 88.6 %** | 25,824 B (14.1 %) | 1,152 B | 0 of 173 (48 refused) |
| 8 | 32768 | 20,624 B (8) | **11.2 % / 88.8 %** | 20,624 B (11.2 %) | 400 B | 0 of 386 (270 refused) |

- **At 7 no true failure in any of 4 runs; at 8 a `/status` piece failed in 3 of 4 runs** (twice
  0.26-0.55 %, once 0.30 %). H at 8 under the same load (§5.4): 0 at −1, 1 at 32768 — so F′'s extra
  4,544 B of heap and its harder ceiling did **not** make 8 clean, against expectation (§6.1 item 4).
- **Peak heap in use at 7: 85.8-88.6 % of the heap; at 8: 88.8-89.9 %.** The largest free block at
  8 falls to 400-512 B — two 256 B pieces' worth.
- **Refusals dominate at 8 on a limit of 8**: 65-71 % of all requests refused, because connections
  still closing count against the limit while their clients have already reconnected (§6.3); at 7,
  25-29 %. Completed requests per minute
  barely change (99-134): the board is the bottleneck.
- **Refusal cross-check gap** (host > device by 0-13): the load starts as soon as `/status` answers,
  a few seconds before the device script installs its rejection counter at `READY` (the board was
  already at 8 open 129 ms after `READY` in the −1 N=8 run), so early rejections reach only the host
  count. No `Connection reclaimed` or other socket-error line on the device in those runs. Tool fix
  pending: install the counter when the webserver exists, not at `READY`.
- **Owner's question: is the collecting instrumentation inflating heap use?** Against it: the
  non-collecting runs, whose sampler neither collects nor meaningfully allocates, show the same
  `/status` failures at 8; a collect can only raise free heap; the same method gave 14.2 % at N=6 on
  H the day before. The "better" figures of 2026-09-23 (§5.3: 24.6 % at 7, 20.7 % at 8) were the
  **rounds** load, not peak. Not excluded: the sampler's wake-ups and 100 ms collects stretch
  requests a little (more overlap), and the device script's own compiled code sits in the heap for
  the whole run (production's `main.py` is frozen) — a few KB, equal in every run. **Settled by the
  control in §5.7**: the wall is real without any sampler; the samplers cost some throughput.

Verbatim (`device: WEBSERVER …` lines omitted):

```
# m1
N= 7 GC_THRESHOLD=-1 | STABLE | complete 123/170 | refused 47 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=20197ms conns=7 free=11008): No. of 1-blocks: 4318, 2-blocks: 500, max blk sz: 64, max free sz: 46
     PEAK_SUMMARY heap=183360 min_free_after_gc=11008 collections=205 rejected=47
     PEAK_AT conns=0 samples=3487 min_free_after_gc=57008
     PEAK_AT conns=1 samples=2 min_free_after_gc=-1
     PEAK_AT conns=2 samples=8 min_free_after_gc=-1
     PEAK_AT conns=3 samples=2 min_free_after_gc=-1
     PEAK_AT conns=5 samples=7 min_free_after_gc=51792
     PEAK_AT conns=6 samples=4 min_free_after_gc=41696
     PEAK_AT conns=7 samples=667 min_free_after_gc=11008
     PEAK_AT conns=8 samples=257 min_free_after_gc=22416
     refusals cross-check: host counted 47, device rejected 47 (a gap means a reset the ceiling did not cause)
N= 8 GC_THRESHOLD=-1 | UNSTABLE | complete 105/366 | refused 259 (expected) | failed 2 (0.55 %) | device allocation-failure lines 4 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=540ms conns=8 free=12160): No. of 1-blocks: 3969, 2-blocks: 523, max blk sz: 64, max free sz: 77
     PEAK_SUMMARY heap=183360 min_free_after_gc=12160 collections=224 rejected=246
     PEAK_AT conns=0 samples=3487 min_free_after_gc=60224
     PEAK_AT conns=1 samples=9 min_free_after_gc=-1
     PEAK_AT conns=2 samples=1 min_free_after_gc=-1
     PEAK_AT conns=3 samples=11 min_free_after_gc=64016
     PEAK_AT conns=4 samples=9 min_free_after_gc=55872
     PEAK_AT conns=5 samples=3 min_free_after_gc=-1
     PEAK_AT conns=6 samples=5 min_free_after_gc=47008
     PEAK_AT conns=7 samples=76 min_free_after_gc=19008
     PEAK_AT conns=8 samples=744 min_free_after_gc=12160
     refusals cross-check: host counted 259, device rejected 246 (a gap means a reset the ceiling did not cause)
     2 x /status status500
     device: MemoryError: memory allocation failed, allocating 252 bytes
     device: MemoryError: memory allocation failed, allocating 252 bytes
# t32
N= 7 GC_THRESHOLD=32768 | STABLE | complete 120/167 | refused 47 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=34825ms conns=8 free=17344): No. of 1-blocks: 3106, 2-blocks: 522, max blk sz: 64, max free sz: 257
     PEAK_SUMMARY heap=183360 min_free_after_gc=17344 collections=412 rejected=45
     PEAK_AT conns=0 samples=3357 min_free_after_gc=68176
     PEAK_AT conns=1 samples=2 min_free_after_gc=78416
     PEAK_AT conns=2 samples=3 min_free_after_gc=-1
     PEAK_AT conns=3 samples=11 min_free_after_gc=66640
     PEAK_AT conns=4 samples=37 min_free_after_gc=62224
     PEAK_AT conns=5 samples=1 min_free_after_gc=63440
     PEAK_AT conns=6 samples=14 min_free_after_gc=45664
     PEAK_AT conns=7 samples=621 min_free_after_gc=17920
     PEAK_AT conns=8 samples=260 min_free_after_gc=17344
     refusals cross-check: host counted 47, device rejected 45 (a gap means a reset the ceiling did not cause)
N= 8 GC_THRESHOLD=32768 | UNSTABLE | complete 99/338 | refused 238 (expected) | failed 1 (0.30 %) | device allocation-failure lines 2 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=47541ms conns=8 free=11552): No. of 1-blocks: 3256, 2-blocks: 551, max blk sz: 64, max free sz: 30
     PEAK_SUMMARY heap=183360 min_free_after_gc=11552 collections=406 rejected=228
     PEAK_AT conns=0 samples=3364 min_free_after_gc=67744
     PEAK_AT conns=1 samples=14 min_free_after_gc=68208
     PEAK_AT conns=2 samples=13 min_free_after_gc=59888
     PEAK_AT conns=3 samples=9 min_free_after_gc=59792
     PEAK_AT conns=5 samples=7 min_free_after_gc=53040
     PEAK_AT conns=6 samples=2 min_free_after_gc=-1
     PEAK_AT conns=7 samples=68 min_free_after_gc=17744
     PEAK_AT conns=8 samples=737 min_free_after_gc=11552
     refusals cross-check: host counted 238, device rejected 228 (a gap means a reset the ceiling did not cause)
     1 x /status status500
     device: MemoryError: memory allocation failed, allocating 255 bytes
# m1live
N= 7 GC_THRESHOLD=-1 | STABLE | complete 134/188 | refused 54 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=57125ms conns=6 free=26112): No. of 1-blocks: 2949, 2-blocks: 496, max blk sz: 64, max free sz: 90
     PEAK_SUMMARY heap=183360 min_free_after_gc=26112 collections=1036 rejected=49
     PEAK_AT conns=0 samples=734 min_free_after_gc=69584
     PEAK_AT conns=1 samples=1 min_free_after_gc=69440
     PEAK_AT conns=2 samples=1 min_free_after_gc=64736
     PEAK_AT conns=3 samples=1 min_free_after_gc=55200
     PEAK_AT conns=4 samples=5 min_free_after_gc=43888
     PEAK_AT conns=6 samples=3 min_free_after_gc=26112
     PEAK_AT conns=7 samples=205 min_free_after_gc=28128
     PEAK_AT conns=8 samples=86 min_free_after_gc=29136
     refusals cross-check: host counted 54, device rejected 49 (a gap means a reset the ceiling did not cause)
N= 8 GC_THRESHOLD=-1 | UNSTABLE | complete 116/391 | refused 274 (expected) | failed 1 (0.26 %) | device allocation-failure lines 2 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=40761ms conns=8 free=18560): No. of 1-blocks: 3106, 2-blocks: 531, max blk sz: 64, max free sz: 32
     PEAK_SUMMARY heap=183360 min_free_after_gc=18560 collections=1017 rejected=267
     PEAK_AT conns=0 samples=727 min_free_after_gc=68912
     PEAK_AT conns=1 samples=1 min_free_after_gc=66080
     PEAK_AT conns=2 samples=1 min_free_after_gc=52560
     PEAK_AT conns=4 samples=2 min_free_after_gc=48720
     PEAK_AT conns=5 samples=6 min_free_after_gc=35712
     PEAK_AT conns=6 samples=2 min_free_after_gc=33808
     PEAK_AT conns=7 samples=29 min_free_after_gc=23248
     PEAK_AT conns=8 samples=249 min_free_after_gc=18560
     refusals cross-check: host counted 274, device rejected 267 (a gap means a reset the ceiling did not cause)
     1 x /status status500
     device: MemoryError: memory allocation failed, allocating 254 bytes
# t32live
N= 7 GC_THRESHOLD=32768 | STABLE | complete 125/173 | refused 48 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=34639ms conns=8 free=20976): No. of 1-blocks: 2932, 2-blocks: 502, max blk sz: 64, max free sz: 72
     PEAK_SUMMARY heap=183360 min_free_after_gc=20976 collections=1035 rejected=42
     PEAK_AT conns=0 samples=744 min_free_after_gc=78608
     PEAK_AT conns=1 samples=1 min_free_after_gc=76192
     PEAK_AT conns=3 samples=1 min_free_after_gc=61136
     PEAK_AT conns=4 samples=1 min_free_after_gc=59152
     PEAK_AT conns=5 samples=4 min_free_after_gc=55872
     PEAK_AT conns=6 samples=3 min_free_after_gc=44848
     PEAK_AT conns=7 samples=203 min_free_after_gc=25824
     PEAK_AT conns=8 samples=78 min_free_after_gc=20976
     refusals cross-check: host counted 48, device rejected 42 (a gap means a reset the ceiling did not cause)
N= 8 GC_THRESHOLD=32768 | STABLE | complete 116/386 | refused 270 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=27459ms conns=8 free=20624): No. of 1-blocks: 3053, 2-blocks: 516, max blk sz: 64, max free sz: 25
     PEAK_SUMMARY heap=183360 min_free_after_gc=20624 collections=1014 rejected=263
     PEAK_AT conns=0 samples=723 min_free_after_gc=77840
     PEAK_AT conns=1 samples=2 min_free_after_gc=76048
     PEAK_AT conns=2 samples=1 min_free_after_gc=70176
     PEAK_AT conns=3 samples=2 min_free_after_gc=57552
     PEAK_AT conns=4 samples=1 min_free_after_gc=46240
     PEAK_AT conns=5 samples=2 min_free_after_gc=43984
     PEAK_AT conns=6 samples=2 min_free_after_gc=42624
     PEAK_AT conns=7 samples=24 min_free_after_gc=22336
     PEAK_AT conns=8 samples=257 min_free_after_gc=20624
     refusals cross-check: host counted 270, device rejected 263 (a gap means a reset the ceiling did not cause)
```

### 5.7 Instrumentation control — the same peak load with no sampler at all (run 2026-09-24)

Owner's question after §5.6: does the instrumentation itself cause the heap use? Control:
`combined_load_sweep.py 8 8 8 --peak --no-sampler` on F′ at `gc.threshold(-1)` — the same 60 s
back-to-back load plus the SGP40 reset PUT, but on the device **no heap maps, no low-water sampler,
no rejection-counter wrapper**; only the host's failure count and the device's allocation-failure
lines. Three fresh boots.

| boot | requests | complete | refused | **true failures** | device allocation lines |
| --- | --- | --- | --- | --- | --- |
| 1 | 441 | 130 | 311 | **0 (0.00 %)** | 0 |
| 2 | 459 | 134 | 325 | **0 (0.00 %)** | 0 |
| 3 | 419 | 122 | 296 | **1 (0.24 %)**, `/status` 500, 252 B piece | 2 |

Against the instrumented N = 8 runs at −1 in §5.6: non-collecting sampler 2 failures (0.55 %) in
1 boot, collecting sampler 1 (0.26 %) in 1 boot.

- **The wall is real without any instrumentation**: the same `/status` piece (252 B) fails at 8 with
  nothing but the production task graph running. The instrumentation does **not** cause it.
- **The instrumentation does add some load**: completed requests per minute 122-134 without it
  against 105 (non-collecting sampler) and 116 (collecting) with it, i.e. the samplers cost ~10-20 %
  of throughput; and failures were 1 in 1,319 requests (1 of 3 boots) without it against 3 in 757
  (2 of 2 boots) with it. Few events, so a direction, not a factor.
- **The device script's own heap cost is 2.7 KB**: `FOOTPRINT script_before_boot alloc=55,680 B`
  (after a collect, before the task graph starts) against **52,960 B** for a two-line script that
  only imports `sensortask_dev` and collects — 2,720 B of this script's own compiled code and
  globals, present in every device-script run, absent in production (frozen `main.py`). All heap
  figures in this file are therefore ~2.7 KB (1.5 % of the heap) pessimistic against production.

Verbatim:

```
N= 8 GC_THRESHOLD=-1 | STABLE | complete 130/441 | refused 311 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=127680
N= 8 GC_THRESHOLD=-1 | STABLE | complete 134/459 | refused 325 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=127680
N= 8 GC_THRESHOLD=-1 | UNSTABLE | complete 122/419 | refused 296 (expected) | failed 1 (0.24 %) | device allocation-failure lines 2 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55696 free=127664
     1 x /status status500
     device: MemoryError: memory allocation failed, allocating 252 bytes
```

### 5.8 Images built for 6 (E6) and for 7 (E7), each at its own limit — run 2026-09-24

Owner's request: the full figures — failures, refusals, free percentage — without instrumentation,
for an image built for 6 and one built for 7, each tested at its maximum. `gc.threshold(-1)`, peak
load (N = limit back-to-back clients for 60 s + the SGP40 reset PUT every 3 s).

**Images** (local edits, never committed; the tip's per-connection pattern: PCB = limit + 3,
SEG = limit × 8, `MEM_SIZE` = limit × 2,000; every macro read back from the firmware, ensemble
check clean at the limit):

| image | `max_connections` | PCB / SEG / `MEM_SIZE` | GC heap, linker | vs F′ | `mem_info` total |
| --- | --- | --- | --- | --- | --- |
| E6 | 6 | 9 / 48 / 12,000 | 192,360 B | +4,648 B = 2 × 2,324 | 187,904 B |
| E7 | 7 | 10 / 56 / 14,000 | 190,036 B | +2,324 B = 1 × 2,324 | 185,664 B |

**Failures and refusals — no instrumentation** (`--peak --no-sampler`, three fresh boots each):

| image, N | boot | requests | complete | refused (expected) | **true failures** | device allocation lines |
| --- | --- | --- | --- | --- | --- | --- |
| E6, 6 | 1 | 467 | 139 | 328 (70.2 %) | **0** | 0 |
| E6, 6 | 2 | 401 | 121 | 280 (69.8 %) | **0** | 0 |
| E6, 6 | 3 | 497 | 149 | 348 (70.0 %) | **0** | 0 |
| **E6, 6** | **all** | **1,365** | **409** | **956 (70.0 %)** | **0 (0.00 %)** | **0** |
| E7, 7 | 1 | 453 | 134 | 319 (70.4 %) | **0** | 0 |
| E7, 7 | 2 | 466 | 136 | 330 (70.8 %) | **0** | 0 |
| E7, 7 | 3 | 415 | 123 | 292 (70.4 %) | **0** | 0 |
| **E7, 7** | **all** | **1,334** | **393** | **941 (70.5 %)** | **0 (0.00 %)** | **0** |

For comparison, F′ (built for 8) at 8, same load, no instrumentation (§5.7): 1,319 requests, 382
complete, 932 refused (70.7 %), **1 true failure (0.08 %)**.

**Free heap at peak** (`--peak --margin`, collect every 100 ms — the only exact method, so
instrumented; "production-equivalent" adds back the device script's own 2,720 B, §5.7):

| image, N | run | min free (measured) | % free | production-equivalent | % free | % used | largest free block at the min | idle (0 open) | failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E6, 6 | 1 | 38,032 B | 20.2 % | 40,752 B | **21.7 %** | 78.3 % | 1,504 B | 83,248 B (44.3 %) | 0 of 376 (263 refused) |
| E6, 6 | 2 | 37,056 B | 19.7 % | 39,776 B | **21.2 %** | 78.8 % | 1,456 B | 83,888 B (44.6 %) | 0 of 397 (278 refused) |
| E7, 7 | 1 | 23,824 B | 12.8 % | 26,544 B | **14.3 %** | 85.7 % | 528 B | 77,232 B (41.6 %) | 0 of 356 (250 refused) |
| F′, 7 (limit 8) | §5.6 | 26,112 / 20,976 B | 14.2 / 11.4 % | 28,832 / 23,696 B | 15.7 / 12.9 % | — | 1,440 / 1,152 B | — | 0 / 0 |
| F′, 8 (limit 8) | §5.6 | 18,560 / 20,624 B | 10.1 / 11.2 % | 21,280 / 23,344 B | 11.6 / 12.7 % | — | 512 / 400 B | — | 1 / 0 |

- **Both images are clean at their own limit**: 0 true failures in 2,699 uninstrumented requests,
  no device allocation line, and 0 failures in their collecting runs. F′ at 8 is the first level
  that fails (1 in 1,319 uninstrumented; 3 more in instrumented runs, §5.6).
- **Headroom at peak: 6 → ~21 % free (largest block ~1.5 KB); 7 → ~14 % free (largest block
  0.5 KB); 8 → ~12 % free (largest block 0.4-0.5 KB) and failing.** Each extra admitted connection
  costs ~13-14 KB at peak (live set) plus 2,324 B of static heap. Against general embedded practice
  of 20-30 % free at peak, **only 6 is inside it**; 7 is below it but stable here.
- **The refusal rate is ~70 % at every limit** under this load: clients reconnect immediately and a
  connection still closing counts (§6.3). Completed requests per boot are flat, 121-149 at 6 and
  123-136 at 7 (F′ at 8: 122-134) — the board, not the limit, sets throughput.
- The refusal cross-check gap (host 15-21 above device) is the known counter-installation timing
  (§5.6); no socket-error line on the device.

**One silent reset** — the first E6 collecting boot (not the uninstrumented ones): the device
output stops at uptime 54 s, ~40 s into the load, mid-way through a normal sensor/FRAM cycle, with
free heap still at 33.5 KB and no `MemoryError`, traceback or error line; USB re-enumerated at
06:40:13. The supervisor's watchdog feed ("All tasks running.", every 2 s) appears 11 lines before
the end, so a watchdog reset would need a ≥ 6 s block of the loop with no output; a hard fault in C
would look the same. `run_isolated()` arms its own `machine.WDT(timeout=8000)` around every device
script. The reset cause was lost (the chain flashed E7 one second later). Two repeat collecting
boots on the reflashed E6 did **not** reset; the re-run captures `machine.reset_cause()` if it ever
does. 1 occurrence in 9 peak-load collecting boots across two days; none in any uninstrumented boot.

Verbatim (`device: WEBSERVER …` lines omitted; the first E6 collecting boot produced no result
line, only the serial error):

```
# E6_ctrl
N= 6 GC_THRESHOLD=-1 | STABLE | complete 139/467 | refused 328 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=132224
N= 6 GC_THRESHOLD=-1 | STABLE | complete 121/401 | refused 280 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=132224
N= 6 GC_THRESHOLD=-1 | STABLE | complete 149/497 | refused 348 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55664 free=132240
# E6_live1
N= 6 GC_THRESHOLD=-1 | STABLE | complete 113/376 | refused 263 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=15314ms conns=6 free=38032): No. of 1-blocks: 2951, 2-blocks: 493, max blk sz: 64, max free sz: 94
     PEAK_SUMMARY heap=187904 min_free_after_gc=38032 collections=1036 rejected=242
     PEAK_AT conns=0 samples=741 min_free_after_gc=83248
     PEAK_AT conns=1 samples=4 min_free_after_gc=68528
     PEAK_AT conns=2 samples=4 min_free_after_gc=66480
     PEAK_AT conns=4 samples=3 min_free_after_gc=53072
     PEAK_AT conns=5 samples=18 min_free_after_gc=49424
     PEAK_AT conns=6 samples=266 min_free_after_gc=38032
     refusals cross-check: host counted 263, device rejected 242 (a gap means a reset the ceiling did not cause)
# E6_live2
N= 6 GC_THRESHOLD=-1 | STABLE | complete 119/397 | refused 278 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=55529ms conns=6 free=37056): No. of 1-blocks: 2990, 2-blocks: 505, max blk sz: 64, max free sz: 91
     PEAK_SUMMARY heap=187904 min_free_after_gc=37056 collections=1050 rejected=263
     PEAK_AT conns=0 samples=747 min_free_after_gc=83888
     PEAK_AT conns=3 samples=5 min_free_after_gc=54048
     PEAK_AT conns=5 samples=26 min_free_after_gc=38720
     PEAK_AT conns=6 samples=272 min_free_after_gc=37056
     refusals cross-check: host counted 278, device rejected 263 (a gap means a reset the ceiling did not cause)
# E7_ctrl
N= 7 GC_THRESHOLD=-1 | STABLE | complete 134/453 | refused 319 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=129984
N= 7 GC_THRESHOLD=-1 | STABLE | complete 136/466 | refused 330 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55680 free=129984
N= 7 GC_THRESHOLD=-1 | STABLE | complete 123/415 | refused 292 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     FOOTPRINT script_before_boot alloc=55712 free=129952
# E7_live
N= 7 GC_THRESHOLD=-1 | STABLE | complete 106/356 | refused 250 (expected) | failed 0 (0.00 %) | device allocation-failure lines 0 | worst largest free run -1 B | reference {'/': 9292, '/js/app.js': 16292}
     at the minimum (t=19725ms conns=7 free=23824): No. of 1-blocks: 3071, 2-blocks: 518, max blk sz: 64, max free sz: 33
     PEAK_SUMMARY heap=185664 min_free_after_gc=23824 collections=1023 rejected=235
     PEAK_AT conns=0 samples=746 min_free_after_gc=77232
     PEAK_AT conns=2 samples=2 min_free_after_gc=64256
     PEAK_AT conns=3 samples=2 min_free_after_gc=54064
     PEAK_AT conns=4 samples=1 min_free_after_gc=50592
     PEAK_AT conns=6 samples=20 min_free_after_gc=36128
     PEAK_AT conns=7 samples=252 min_free_after_gc=23824
     refusals cross-check: host counted 250, device rejected 235 (a gap means a reset the ceiling did not cause)
```

## 6. Findings

### 6.1 The connection limit

1. **Measured headroom per limit, each image at its own limit, peak load, `gc.threshold(-1)`**
   (§5.6-§5.8; production-equivalent free heap = measured + the device script's 2,720 B):

   | limit (image) | true failures, uninstrumented | free heap at peak | largest free block at peak | verdict |
   | --- | --- | --- | --- | --- |
   | 6 (E6) | 0 in 1,365 requests (3 boots) | 21.2-21.7 % | ~1.5 KB | clean, inside the 20-30 % practice |
   | 7 (E7) | 0 in 1,334 requests (3 boots) | 14.3 % | 528 B | clean, below the practice |
   | 8 (F′, shipped) | 1 in 1,319 (3 boots); 4 more in 4 instrumented boots | 11.6-12.7 % | 400-512 B | **fails** |
   | 9 (H) | 3 and 6 per run (1.7 %, 3.2 %) | — | — | fails |
   | 10 (G′, H) | ~1 `/status` in 10 fails every round (G′); 3 per run (H) | 11.5 % sampled (H) | 288 B (H) | fails |

2. **Each admitted connection costs ~13-14 KB of heap at peak** (the live set of one in-flight
   request with its streams, `Request`/`Response`, handler frame and pieces) **plus 2,324 B of static
   heap** for its lwIP share (one PCB, 8 segments, 2,000 B of `MEM_SIZE`). Measured exactly for the
   static part (E6/E7/F′/H/G′ linker figures), from the peak live set for the dynamic part.
3. **10 is not reachable on this heap**: G′ (169,120 B) fails 3/3 at 10, H (183,064 B) fails 10 in
   both arms; under rounds load the step 9 → 10 already cost ~14 KB against ~3 KB for 8 → 9, and at 12
   the failures spread from `/status` to microdot's `Request` (400s), static bodies and non-web tasks.
4. **An image built for 8 is not cleaner at 8 than one built for 10** (F′ at 8: failures in 4 of 7
   boots; H at 8: 0 and 1 in single runs), against the expectation that the tighter ceiling and
   4,544 B more heap would help. Not explained; one hypothesis, untested: with a tight ceiling,
   refused clients retry at once, and every refused accept still allocates its stream objects and a
   task before the close, so the churn is higher.

### 6.2 What fails, and what does not

5. **The wall is the `/status` JSON piece.** Every true failure at 8-10 on every image is `/status`
   failing to allocate one 242-257 B `_PieceWriter` piece (`chunk_bytes` = 256): `_get_status` →
   `_build_status_pieces` → `_write_errcount_entry` → `add_value` → `add` → `flush`. No other route
   failed at those levels; every body that was served was complete (static `Content-Length`
   verified on every response).
6. **The static-file defect of 2026-09-23 is fixed on silicon**: `route:/` needs 320 B instead of
   1,536 B, no `1025` read anywhere since, and a cut static body is now client-visible
   (`IncompleteRead` against `Content-Length`) instead of a silent `200`.
7. **At the limit, the free pool empties, it does not merely fragment**: on G′ the one-boot sweep
   failed allocations of 68-138 B in sensor config reads, FRAM history writes and the device script
   itself. Below the limit the largest free block (0.4-1.5 KB at peak) is still larger than any
   single serving allocation (≤ 257 B).

### 6.3 Behaviour under saturation

8. **The connection counter includes closing connections.** `_serve()` decrements `_open_conns` only
   after `_close_writer()` (bounded `wait_closed()`), while the client already has its complete body
   (`Content-Length`) and has opened its next connection. So a limit of N refuses some of N
   back-to-back clients; with 8 clients on H the count reached 10. Expected behaviour by the owner's
   rule; **whether it should drop when the response is written is an owner decision — not changed**
   (closing connections still hold lwIP PCBs, which is why the limit sits below `MEMP_NUM_TCP_PCB`).
9. **~70 % of requests are refused at every limit** (6, 7, 8) under back-to-back clients, and the
   completed count is flat: 121-149 per 60 s boot at 6, 123-136 at 7, 122-134 at 8 (~2.2 requests/s).
   **The board, not the limit, sets throughput**; a higher limit only makes each request slower and
   holds more heap at once.
10. **Refusals are cleanly separable from failures**: a reject-when-full close gives the client a
    reset before any response; the device's own count of rejections matches the host's to within
    the counter-installation window (host 0-21 higher, §6.5 item 16), and no socket-error line
    appears on the device.

### 6.4 The gc threshold

11. **`gc.threshold(32768)` vs −1 under peak load**: ~1.7-2× the collections and more contiguous
    space at 6 clients, but **no fewer failures** (H at 8: 1 vs 0, at 9: 6 vs 3; F′ at 8: 1 vs 2) —
    single runs per cell, not separable from chance. The limit decides, not the threshold.

### 6.5 The instruments themselves

12. **The instrumentation does not cause the wall** (§5.7): with no sampler at all, F′ at 8 still
    failed the same 252 B `/status` piece (1 in 3 boots).
13. **The samplers do cost something**: ~10-20 % of throughput (completed requests 105-116 with a
    sampler, 122-134 without), and the instrumented boots failed more often (at −1: 3 in 757 requests
    vs 1 in 1,319). Figures from instrumented runs are therefore pessimistic, not optimistic.
14. **The device script's own heap cost is 2,720 B** (55,680 B allocated before boot vs 52,960 B for an
    import-only script). Production (frozen `main.py`) does not pay it; every device-script heap
    figure is that much pessimistic.
15. **Rounds load understates peak memory use by ~20 KB at 6 clients** (§5.5 vs §5.3): pauses between
    rounds and 5 s snapshots miss the moment when all N allocate at once.
16. **The non-collecting sampler's heap figure is biased low by up to 15-30 KB**: it reads "just
    after a GC" late under load (every ~60 ms against a heap churning ~250 KB/s), and rp2 offers no
    exact GC signal (no `__del__` on user-class instances, no `weakref`). Only the collecting sampler
    gives an exact live set. The refusal cross-check has a known gap: the device counter is installed
    at `READY`, a few seconds after the host's load starts.
17. **Tool output labels can be wrong**: `--margin`'s printed "idle" was a mid-boot sample and its
    "median under load" spanned the post-load idle (fixed in `53ac222`); caught only by re-deriving
    from the raw maps.

### 6.6 Board and bench anomalies (recorded, not chased)

18. **One silent reset** in the first E6 collecting boot (§5.8): output stops ~40 s into the load
    with 33.5 KB free, no error line; watchdog (the harness arms `machine.WDT(timeout=8000)` around
    every device script) or a hard fault — cause lost. 1 in 9 peak-load collecting boots; none in any
    uninstrumented boot; two repeats clean.
19. **Hotspot fallback after a reset, three times** (after a likely watchdog reset between two tests,
    after flashing F′, after flashing H): bench AP up, no station associated; `kick_all_stations()` +
    hard reset recovered it (once only on the second try).
20. **Likely watchdog reset at `mpremote` attach**: a new session ~30 s after a test's own teardown
    reset, board reset ~9 s later, next test dead on `OSError: [Errno 5]`. Cause not confirmed.
21. **An empty `200` with no `Content-Length`**, twice, from an idle `GET /` during the boot-time WLAN
    drop — not from `_serve_static()`, which always sets it; origin unexplained.
22. **Twin vs board**: the twin was optimistic about the wall (pre-fix G failed JSON at 10, the twin
    at none through 12) and pessimistic about free heap under rounds load (board +9 KB at 6, +18 KB
    at 7).

## 7. Open

1. **Decided 2026-09-24: the limit is 6** (committed; confirmation `REAL_HARDWARE_HANDOVER_LIMIT_6.md`). §6.1 was the basis: 6 is the only limit inside 20-30 % free at
   peak; 7 is clean but at 14 %; 8 fails. Whichever is chosen, `devices/*.toml` `max_connections`
   and the `[lwip]` ensemble move together (PCB = limit + 3, SEG = limit × 8, `MEM_SIZE` = limit ×
   2,000 is the measured pattern; `check_lwip_ensemble()` enforces the floors).
2. **Owner decisions, design**: whether `_open_conns` should drop at response-written (§6.3 item 8);
   whether to reduce what `/status` needs (smaller `chunk_bytes`, or less per piece), which is what
   would move the wall.
3. **Repeats for the chosen limit**: the free-heap figures at peak rest on 1-2 collecting boots per
   image; ≥ 3 would give a spread.
4. **The silent reset** (§6.6 item 18) if it recurs: the re-run script captures
   `machine.reset_cause()` right after the serial error.
5. **Done 2026-09-24**: the device's rejection counter is installed as soon as the webserver exists,
   not at `READY` (§6.5 item 16); host and device counts now match exactly (twin: 1,336 = 1,336).
6. Deferred from the static-fix handover: H3 (`/status` p50/p95, `test_end_to_end_timing.py`) and
   H4 (full bench tier), on the image with the chosen limit.

## 8. Measurement principles

How the figures in this file were obtained, and the rules they rest on. Documentation, not code:
the tools that implement them are listed in §4, and a future instrument should follow the same
rules whatever its implementation.

### 8.1 Fix the question and the pass criterion before measuring

- **Every figure answers a stated question**: "is limit N stable", "how much heap is left at peak",
  "does the instrument cause the effect". A figure without its question is not reported.
- **The owner's definitions are the criteria, written down first** (§1): "no gc threshold" is
  MicroPython's own `gc.threshold(-1)`; peak load is maximum connection load coinciding with forced
  internal work; a refusal at a saturated ceiling is expected behaviour; a memory error is a true
  failure; stable means zero true failures **and** zero allocation-failure lines on the device,
  caught-and-logged ones included (CLAUDE.md's memory-safety bar).
- **The load must match the question.** Rounds with pauses measure typical load; they are not peak
  and overstate free heap by ~20 KB (§6.5 item 15). Peak means clients back to back at the ceiling
  for the whole window, plus the hammer test's internal-work trigger, on the full production task
  graph with every path the website really fetches.

### 8.2 Separate the verdict from the measurement

- **Every instrument is classified as invasive or non-invasive, and every run states which figures it
  is valid for.** An instrument that changes the system under test may measure, but may not judge:
  a `gc.collect()` before each sample cleans the heap, so a collecting run's stability verdict is
  never evidence (§4.1's table has a "verdict is evidence?" column for exactly this).
- **The verdict comes from the least-instrumented run that can give it**; the heap figure comes from
  the run that can measure it exactly. Where one run cannot give both, two runs are made rather than
  one run that gives both approximately — and when the owner asked for one run, the reason it could
  not be done exactly was stated, with the bias of the approximation (§6.5 item 16).
- **A collect or a threshold is only ever instrumentation or defence in depth, never the fix**
  (CLAUDE.md): no run's result is credited to a `gc.collect()`, and the threshold under test is set
  explicitly by every device script and printed in every result line (`GC_THRESHOLD=`). A line
  without it is void.

### 8.3 Controls: rule out the instrument as the cause

- **When the instrument could plausibly produce the effect it reports, the same load is run without
  it** (§5.7: no sampler, no counter, only host counts and device allocation lines). The control
  decides; argument alone does not.
- **The instrument's own cost is measured and reported**, not assumed away: the device script's heap
  footprint (2,720 B, from the same measurement taken with and without the script) and the samplers'
  throughput cost (~10-20 %). Heap figures are given both as measured and production-equivalent.

### 8.4 Two independent views, and a gap is a finding

- **Counts are taken on both sides where both sides can see them**: host refusals against the
  device's own reject-when-full count; host failures against device allocation-failure lines (two
  lines per failure: the `MemoryError` and the webserver's handler line). A mismatch is investigated
  before either number is trusted (§6.5 item 16: the device counter starts later than the load).
- **Every served body is checked, not only the status code**: static bodies against an idle
  reference and their `Content-Length`, JSON bodies by parsing. A `200` is not a success on its own
  — that is how the static-file defect hid.
- **The reference itself is validated** (a 200 whose non-empty body equals its `Content-Length`),
  because a reference taken during the boot-time WLAN drop once came back empty and made every
  correct page look truncated.

### 8.5 Verify the object under test

- **Every image is verified before its figures count**: every lwIP macro read back out of the built
  firmware's own translation unit; the ensemble check at the image's limit; the GC heap computed
  from the linker symbols and checked against the prediction (2,324 B per connection, matched to the
  byte on E6, E7, H, G′); the build date read back from the running board; `Content-Length` and
  `gzip -t` on the static files. The `mem_info` total (not the linker figure) is the percentage
  base, and it is stated.
- **Local-only images are recorded by recipe** (§3, §5.8) and never committed; the repo is returned to
  the tip after each build.

### 8.6 One fresh boot per data point, and enough of them

- **Each level is its own boot**, so no run inherits another's heap; a repeated level is a repeated
  run. Failures near the wall are probabilistic (1 in 2-3 boots before the static fix; 4 in 7 boots
  for F′ at 8), so **one clean run proves little**: per-boot rows are reported alongside totals, and
  a single-run difference (0 vs 1 failure) is called "not separable from chance", not a result.
- **Everything is reported as count and percentage**: failures of all requests, refusals separately,
  heap in bytes and in % of the stated base, plus the largest free block — the figure that decides
  whether the next allocation can be placed.

### 8.7 Know the instrument's limits, and state the bias direction

- **Sampling misses peaks**: a snapshot every 5 s cannot see the instant all N allocate; the
  interval is stated and a sampled minimum is labelled as bounding the true peak from one side only.
- **What the runtime cannot tell is not faked**: rp2 has no exact end-of-GC signal, so the
  non-collecting sampler's heap figure is documented as biased low and not reported as a peak.
- **Tool summaries are not taken for granted**: where a printed label looked wrong (`--margin`'s
  "idle" and "median"), the figure was re-derived from the raw maps and the tool fixed afterwards.

### 8.8 Evidence hygiene

- **FRAM error logs are read before anything writes to the board**, and treated as context, not
  evidence, once device scripts have run (they build their own `AsyFramManager` over the same chip).
- **The reset cause is captured immediately** after an unexpected reset, before any flash or reboot
  can overwrite it (lost once in §5.8; the re-run script now reads `machine.reset_cause()` at once).
- **Raw result lines go into the record verbatim**, alongside the derived tables, so every table can
  be recomputed.
- **Neither the tool nor the device script is edited while chained runs are pending** — each new
  invocation re-reads both.
- **Bench state is restored between runs**: stations kicked and the board hard-reset between levels,
  45 s settle, hotspot fallback recovered by kick + reset, and nothing attached to the serial port
  within ~45 s of a reset (the harness arms an 8 s watchdog on every device-script run).

## 9. Traps paid for these two days

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
