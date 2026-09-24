# Real-hardware handover: confirm the committed limit of 6 (image E6′)

**Read this file alone.** One build, one flash, two boots — about 15 minutes. Temporary: its
results go into `REAL_HARDWARE_HANDOVER_PEAK_LOAD.md` (or its successor) and `REAL_HARDWARE_TEST_QUEUE.md`
row W8, then this file is removed with the rest (BACKLOG.md item 45).

## 1. What changed, and why this sitting

- **The owner chose `max_connections = 6`** (2026-09-24). The tip now sets it in every
  `devices/*.toml`, and `toolchain/versions.toml`'s `[lwip]` ensemble is sized for it:
  `MEMP_NUM_TCP_PCB` 9, `MEMP_NUM_TCP_SEG` 48, `MEM_SIZE` 12,000 (limit + 3, limit × 8, limit × 2,000).
  `WebserverService`'s own default is 6 too. The reasoning is SPECIFICATION.md Part H.7.
- **E6 — a local build of exactly this configuration — was already measured** (PEAK_LOAD handover
  §5.8): 0 true failures in 1,365 requests under peak load, ~21 % heap free at peak, a ~1.5 KB largest
  free block. **E6′ is the committed build.** This sitting only confirms two things: that E6′ is the
  same image as E6, and that it is clean under the same peak load. Nothing else is being measured.
- **Tool change since the last sitting** (`tests_hardware/device_scripts/serving_stability_under_combined_load.py`):
  in `--peak`, the device's rejection counter is now installed as soon as the webserver object
  exists, not at `READY`. **Host "refused" and device "rejected" must now match exactly** (twin: load
  started 3.3 s after boot, host 1,336 resets = device 1,336 rejections). A gap is now a finding.

## 2. Before anything

1. The owner's go-ahead **in your own conversation** (CLAUDE.md). Nothing here writes persistent
   config except what the bench tier's own default flags already do; no `--allow-persistence-writes`.
2. **Read `GET /status`'s `errcount` and write it down** — context only: the board has run device
   scripts since its last clean state (CLAUDE.md's FRAM rule and its caveat).
3. **The board is on E6 (local edits).** Discard any local edits to `devices/*.toml` and
   `toolchain/versions.toml` and pull the tip; the tip itself is now the limit-6 configuration.
4. "No gc threshold" = MicroPython's own `gc.threshold(-1)`, set by the device script itself; every
   result line must read `GC_THRESHOLD=-1`. Do not pass `--threshold`.
5. Traps: `pkill -f`/`pgrep -f` match their own command line — list by PID; two suites binding real
   ports never overlap; leave > 45 s between runs (the likely watchdog reset at `mpremote` attach);
   after a reset the board may fall back to hotspot mode — `kick_all_stations()` + hard reset.

## 3. Procedure — image E6′, the branch tip

Result lines verbatim into the recording table (§4) and commit them, as before. `DUT_IP=<ip>` in front
of every `combined_load_sweep.py` command; `--raw-dir <dir>` on every one.

| step | what | expected | time |
| --- | --- | --- | --- |
| 1 | `uv run scripts/build_firmware.py dev`, flash. lwIP read back from the firmware: **PCB 9 / SEG 48 / `MEM_SIZE` 12,000**. GC heap by the linker **192,360 B**, `mem_info` total **187,904 B** — E6's figures; a difference means E6′ is not E6, stop | identical to E6 | 5 min |
| 2 | **Clean under peak load, no instrumentation**: `combined_load_sweep.py 6 6 --peak --no-sampler` | 0 true failures, 0 allocation lines, ~70 % refused | 9 min |
| 3 | **Leave the board on E6′.** | | |

Not part of this sitting (optional, owner's call, none needed to confirm the limit): more exact-heap
boots for a spread (`6 6 6 --peak --margin`), 8 clients against the limit (`8 --peak --no-sampler`),
and `/status` timing plus the full bench tier, which belong to the regular pre-merge run.

**If a boot resets silently** (as one E6 collecting boot did): capture `machine.reset_cause()` at once
over `mpremote` before anything else touches the board, and record it with the uptime at which the
output stopped.

**Stop rule**: any true failure or allocation line at 6 — record everything (sizes, sites, raw output)
and stop. Whether 6 stands is then the owner's decision.

## 4. Recording table

E6 column: the local build of 2026-09-24 (PEAK_LOAD handover §5.8), production-equivalent heap
figures (+ 2,720 B, the device script's own footprint).

| step | measurement | E6 (2026-09-24) | `[HW]` E6′ |
| --- | --- | --- | --- |
| 1 | lwIP macros / linker heap / `mem_info` total | 9 / 48 / 12,000; 192,360 B; 187,904 B | ___ |
| 2 | true failures / requests, per boot | 0/467, 0/401, 0/497 | ___ |
| 2 | refused, per boot | 70.2 %, 69.8 %, 70.0 % | ___ |

## 5. What a result means

- **Step 1 identical and step 2 clean**: the committed limit of 6 is confirmed — E6's heap figures
  (~21 % free at peak) apply unchanged; BACKLOG item 7 stays closed.
- **Any true failure at 6**: the first evidence against 6 under peak load; stop and report.
