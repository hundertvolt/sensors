# Real-hardware handover: confirm the committed limit of 6 (image E6′)

**Read this file alone.** One build, one flash, about 2 hours with the bench tier. Temporary: its
results go into `REAL_HARDWARE_HANDOVER_PEAK_LOAD.md` (or its successor) and `REAL_HARDWARE_TEST_QUEUE.md`
row W8, then this file is removed with the rest (BACKLOG.md item 45).

## 1. What changed, and why this sitting

- **The owner chose `max_connections = 6`** (2026-09-24). The tip now sets it in every
  `devices/*.toml`, and `toolchain/versions.toml`'s `[lwip]` ensemble is sized for it:
  `MEMP_NUM_TCP_PCB` 9, `MEMP_NUM_TCP_SEG` 48, `MEM_SIZE` 12,000 (limit + 3, limit × 8, limit × 2,000).
  `WebserverService`'s own default is 6 too. The reasoning is SPECIFICATION.md Part H.7.
- **E6 — a local build of exactly this configuration — was already measured** (PEAK_LOAD handover
  §5.8): 0 true failures in 1,365 requests under peak load, ~21 % heap free at peak, a ~1.5 KB largest
  free block. **E6′ is the committed build**; this sitting confirms that it is the same image and
  closes what E6 left open: only 2 collecting boots (no spread), the refusal cross-check gap, one
  unexplained silent reset, and the bench tier and timing never run on it.
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
| 1 | `uv run scripts/build_firmware.py dev`, flash. lwIP read back from the firmware: **PCB 9 / SEG 48 / `MEM_SIZE` 12,000**, ensemble clean at 6. GC heap by the linker **192,360 B**, `mem_info` total **187,904 B** (E6's figures — a difference means E6′ is not E6) | identical to E6 | 10 min |
| 2 | On the wire: `GET /` `Content-Length: 9292`, `GET /js/app.js` `16292`, both pass `gzip -t` | as F′ | 1 min |
| 3 | **Failures, no instrumentation**: `combined_load_sweep.py 6 6 6 --peak --no-sampler` | 0 true failures, 0 allocation lines, ~70 % refused | 13 min |
| 4 | **Exact peak heap, three more boots** (the spread E6 lacked): `combined_load_sweep.py 6 6 6 --peak --margin`. Record per boot: min free (measured and + 2,720 B production-equivalent), % of `mem_info` total, largest free block at the min | ≥ ~21 % production-equivalent, largest block ≥ ~1.2 KB, 0 failures | 13 min |
| 5 | **Refusal cross-check** with the fixed counter: `combined_load_sweep.py 6 6 --peak`. The `refusals cross-check` line must read host = device | exact match | 9 min |
| 6 | **Over-subscription is refused, not failed**: `combined_load_sweep.py 8 8 --peak --no-sampler` — 8 clients against the limit of 6 | 0 true failures; refusals higher than at 6 | 9 min |
| 7 | `/status` timing: `uv run pytest tests_hardware/bench/test_end_to_end_timing.py -s` (the old H3) | passes; record p50/p95 | 5 min |
| 8 | **The whole bench tier**, default flags: `scripts/run_bench_hardware_suite.sh` (the old H4). It now runs at the limit of 6 wherever a test derives its load from `configured_max_connections()` (the hammer, the timing test, the ceiling test). Read the *deselected* count, not only "clean" | clean | 45 min |
| 9 | **Leave the board on E6′.** | | |

**If a boot resets silently** (as one E6 collecting boot did): capture `machine.reset_cause()` at once
over `mpremote` before anything else touches the board, and record it with the uptime at which the
output stopped.

**Stop rule**: any true failure, any allocation line, or a host/device refusal mismatch at 6 (steps
3-5) — record everything (sizes, sites, rounds, raw output) and stop before step 6. Whether 6 stands
is then the owner's decision.

## 4. Recording table

E6 column: the local build of 2026-09-24 (PEAK_LOAD handover §5.8), production-equivalent heap
figures (+ 2,720 B, the device script's own footprint).

| step | measurement | E6 (2026-09-24) | `[HW]` E6′ |
| --- | --- | --- | --- |
| 1 | lwIP macros / linker heap / `mem_info` total | 9 / 48 / 12,000; 192,360 B; 187,904 B | ___ |
| 3 | true failures / requests, per boot | 0/467, 0/401, 0/497 | ___ |
| 3 | refused, per boot | 70.2 %, 69.8 %, 70.0 % | ___ |
| 4 | min free at peak, production-equivalent, per boot | 40,752 B (21.7 %), 39,776 B (21.2 %) | ___ |
| 4 | largest free block at the min | 1,504 B, 1,456 B | ___ |
| 4 | failures in the collecting boots | 0, 0 (one further boot reset silently, cause lost) | ___ |
| 5 | refusals: host / device | 263 / 242, 278 / 263 (counter installed at `READY`) | ___ must be equal |
| 6 | 8 clients on limit 6: true failures / refused | not measured | ___ |
| 7 | `/status` p50 / p95 | not measured on 6 | ___ |
| 8 | bench tier passed / skipped / deselected | 103 / 4 / 27 (image A, 2026-09-23) | ___ |

## 5. What a result means

- **Steps 3-6 clean and step 4 at ≥ ~20 %**: the committed limit of 6 is confirmed; BACKLOG item 7
  stays closed and the PEAK_LOAD handover's §7 item 1 is done.
- **Step 4 clearly below E6's ~21 %** with an identical image (step 1): E6's two boots were the lucky
  end of the spread — record it; the margin, not the zero failures, is what 6 was chosen for.
- **Any true failure at 6**: the first evidence against 6 under peak load; stop (§3's stop rule).
- **Step 6 failing where step 3 was clean**: over-subscription reaching the heap despite the
  limit — the refused accepts' own stream objects and tasks (PEAK_LOAD handover §6.1 item 4's
  hypothesis) would be the first suspect.
