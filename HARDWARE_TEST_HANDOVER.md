# Hardware test handover — the next dev-bench sitting

Handover for the real-hardware session that follows the 2026-09-24 cloud work (PR #58, branch
`claude/automated-build-chain-nuzumw`). A per-effort throwaway: delete it once the sitting's results
are migrated. **`REAL_HARDWARE_TEST_QUEUE.md` stays the single list of what is owed** — this file is
the briefing and the running order, and names queue rows by their IDs rather than restating them.
`tests_hardware/README.md` is the technical reference for every command below.

**Nothing here authorizes anything.** The session needs the owner's go-ahead in its own
conversation before any `mpremote`, `nmcli`, `iw`, `iptables`, `picotool` or `tests_hardware/` run
(CLAUDE.md). With it, it covers the whole conversation.

---

## 1. Where things stand

- **Board**: `dev` bench, image of tree `851e816` (`buildDate 2026-09-25T12:54:13Z`,
  `max_connections = 6`, `DebugLevel` 5) — current with every `src/` change on the branch,
  `83c9920`'s SGP40 fix included. Step 6 is done on it, clean (section 5).
- **This sitting (2026-09-24/25) is still in progress** — section 5 has every result so far, with
  suggested actions; it is the single place to read them.
- **Tree**: every host tier green at `gc.threshold(-1)` and `32768` (86/86 MicroPython files, 2,100
  pytest), CI green.
- **Settled, not to be re-measured**: the connection limit of 6 and its lwIP ensemble
  (SPECIFICATION.md H.7, B.14.2), the 256 B response bound (I.3), measures A and B (I.4(f.1)).
- **The owner's standing answers**: D1 — spend flash/NVM writes, but only after a clean default run;
  D2 — the NeoPixel light rig is in place. D3 is always "a `dev` build of the tree under test".

## 2. What is new on silicon since E6′ — why the reflash matters

The first real run of each of these is part of this sitting; a failure in one is this tree's, not a
known-broken test.

| Change | Where | Exercised by |
| --- | --- | --- |
| Header block sent as one write; no more writes once the peer has reset; a connection slot released even when closing raises `MemoryError` | `asy_webserver_service.py` | the whole bench tier (W4), the ceiling tests |
| SCD30 rejects a non-finite measurement word as a failed read instead of caching `nan`/`inf` | `asy_scd30_driver.py` | flash + bench tiers (no silicon trigger exists; it must simply stay quiet) |
| Trigger-event flags renamed to `base_trigger_event` / `read_event` in BMP3XX, SGP40, SCD30 | three drivers' read loops | every sensor test — behaviour-neutral, but the read loops are touched |
| `W4` ("WLAN authentication failed") wording; the outage check accepts `W4` beside `W5` | `asy_wifi_service.py`, `test_network_resilience.py` | W4 |
| NTP never ends its task on a failing server: unsynced retries back off 10 s → 600 s, a silent timeout logs `E21` (was nothing), `E20` is retired; notification keeps running on a config-read failure | `asy_ntp_client.py`, `asy_notification_service.py` | W4: `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` now expects `E21` and **no** `Task ended - attempting restart` line — the `E20` restart the owner's 2026-09-24 run saw is the bug this fixes |
| A failed config write keeps the new config running unpersisted (`E4` at setup, `E14` on a change) instead of failing the module | `config_manager.py` | flash + bench tiers — no silicon trigger for a write failure exists; it must simply stay quiet |
| WiFi refuses a radio string (`SSID`, `PW`, `Country`, `Hostname`, `HotspotPW`) whose UTF-8 bytes break the radio's limit (`"Invalid"`, persists nothing); a stored one that does falls back to the build default with `W8` | `asy_wifi_service.py` | W4 must stay quiet; optional zero-wear check: `PUT /networking` a 17-character `ä` hostname and expect `"Invalid"` |
| The hotspot timer is `PERIODIC`, so a dropped soft callback self-heals; `E19` is retired | `asy_wifi_service.py` | every hotspot fallback in W4/F17 and `test_hotspot_role_reversal.py` |
| Bench tests fail when any task ended during the run (`assert_no_task_ended`, SYSTEM counter must stay 0) | `test_network_resilience.py`, `test_bus_concurrency_under_api_load.py`, `test_uart_link_under_api_load.py`, `test_wifi_networking.py` | W4 — a red here is a new finding, not a flaky test: read the SYSTEM log before anything else |
| SGP40 `W13` (backup without timestamp) spends one slot per NTP outage, not one per backup | `asy_sgp40_driver.py` | any NTP outage longer than `SGPWaitTimeNTP`, e.g. a hotspot fallback: one `W13` in the ring, `ErrCount` still counting each backup |
| Every heap-measuring device script sets its own `gc.threshold` and prints `GC_THRESHOLD=` | `tests_hardware/device_scripts/` | T1 and the flash tier's memory tests |
| Bench config-write arms print `CEILING_RETRIES` | `test_bus_concurrency_under_api_load.py` | R1's first answer (step 6) |

## 3. Running order

Wear is marked where a step spends it. Stop and report if a step goes red in a way its row does not
anticipate; do not work around it.

1. **Read the board before anything writes.** `GET /status`, save the whole `errcount` table
   verbatim. Ask what was last run against this board: device scripts overwrite production's first
   FRAM chunks, so an older entry is evidence only if the board's recent history allows it.
2. **Build, flash, verify.** `scripts/build_firmware.py dev`, flash it, then confirm `/system`'s
   `build.buildDate` matches the build. Never a `wozi` build.
3. **G11, code at the sitting** (done 2026-09-25, 5.3) — switch `bmp3xx_plausibility_read.py` and
   `sgp40_fram_backup_restore.py` to the schema-derived cache (the queue row has the two lines), so
   step 4 validates them.
4. **Flash tier**: `scripts/run_flash_hardware_suite.sh`. Read the **deselected** count, not only
   "clean". Covers T1: record the in-suite AFTER `largest_block` with its `GC_THRESHOLD=` and
   `retained=` (a value of `192 KB >> k` with `retained` equal to it is the probe, not the heap).
5. **Bench tier**: `scripts/run_bench_hardware_suite.sh`. This is **W4** (first full bench tier at
   the limit of 6) and carries **R9** and **F17** (note every unexpected reset's
   `machine.reset_cause()` and every hotspot fallback). Then **W3**:
   `tests_hardware/bench/test_end_to_end_timing.py`.
6. **Wear-gated run, only once 4 and 5 are green** —
   `scripts/run_bench_hardware_suite.sh --allow-persistence-writes -s`. *Wear: real flash config
   writes.* It answers:
   - **R1**: read the two `CEILING_RETRIES` lines. ISL29125 retrying well above BMP3XX with no other
     failure → the connection ceiling; close BACKLOG 30 without bisecting. Otherwise do the
     `RangeAuto=false` bisection in the R1 row, and restore `RangeAuto`.
   - **R5**: the third BMP3XX config-write pass; green closes it (owner, 2026-09-24).
   - **T2**: bus-hazard tier 4 on the A + B code, including its three `persistence_write` tests.
   - **R4**: pre-populate several FRAM logs, sweep `ResetErrors` under R2's reader load, confirm all
     read back 0.
   - **W5**: set `NTP_Host` to its 1,024-character bound over REST, run `test_network_resilience.py`'s
     peak arm, confirm `/networking` and `/status` still arrive complete; restore the old value.
7. **Light rig**: M1 first (it records the rig geometry), then
   `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` (S3b, ~10 min).
8. **Targeted runs, in this order**:
   - **R2** — `ResetErrors` elapsed time at 0, 1, 2, 3, 4 and 6 concurrent `GET /status` readers.
     This curve is what BACKLOG 32's bench budget and BACKLOG 24's design question wait on.
   - **F1** — read the row in full first; one careful run of `wifi_service_reconnect_repro.py`.
     *Wear: one scratch-file write.*
   - **T4** — A6's timing script (queue section 1A) for the per-command hold time; the figure goes
     into SPECIFICATION.md F.5.8. Optionally T1's zero-wear threshold-race check (in the T1 row).
   - **R6 / R7** — FRAM setup cost on silicon and the unexplained +0.90 s; frame R7 as interpreter
     overhead, not wire time.
   - **R13 + N3** — one babbling-peer run over the crossover jumper: `W11` rather than `W10` for
     `UART_init`/`UART_resp`, and nothing persisted by a boot drain.
   - **N2** — one boot with `Hostname` absent from the persisted `config_WIFI.cfg`, to prove the
     build-time default substitution. *Wear: one config write to remove the key.*
9. **Scripts still to write** (code first, bench second), if the sitting has time: **G8** (the (e)
   stage under real load: import-boot, host-side load, assert no `MEMORY_ERROR_MARKERS`), **G12**
   (F.5.8's never-block invariant against the real `asy_uart_driver`), **G1**, **G3**, **G4**.

**Not in this sitting**: S4, the long soak (its own deliberate `run_bench_soak_tests.sh --tier`);
G6's ~12.4-day rollover run (deferred by decision); H1, the two-chroot check (the owner's own run,
no board needed).

If only one short sitting is possible, do steps 1, 2, 4, 5 and 7, then F1 and T4.

## 4. Recording and close-out

- **Per row**: migrate the result where the queue row says (SPECIFICATION.md, CLAUDE.md or
  BACKLOG.md), then delete the row. Measured values that only support a decision do not need a
  permanent home beyond the commit that records them.
- **R2** feeds BACKLOG 32 (add the bench budget to `tests_hardware/error_log_helpers.py`) and
  BACKLOG 24. **R1** closes or narrows BACKLOG 30. **T4** goes into SPECIFICATION.md F.5.8.
  **W4/W5** confirm SPECIFICATION.md H.7 and I.3 as they stand; a failure there reopens them.
- **Heap figures** follow `HEAP_FRAGMENTATION_MEASUREMENTS.md`: name the position and the threshold on
  every figure, and use `mem_info(1)` maps over the probe.
- **Before any `ResetErrors`**, save `errcount` again — it is the only record of what the sitting
  itself logged.
- When the queue's last row goes, delete `REAL_HARDWARE_TEST_QUEUE.md`; delete this file once the
  sitting's results are migrated.

## 5. Results of this sitting — IN PROGRESS (2026-09-24/25)

**The sitting is still running**: nothing below is final, and the board is still in use. Every
figure is from the `dev` bench. Raw logs sit in the session's scratchpad only; what matters is here.

### 5.1 Images and board state

| Image (`buildDate`) | Tree | Used for |
| --- | --- | --- |
| `2026-09-24T19:11:45Z` | `bf62580` | W4's first run |
| `2026-09-25T05:21:43Z` | `dd80eef` | T4, W3, R2 |
| `2026-09-25T07:31:00Z` | `3062cc7` | everything from 5.3 on, W4's clean re-run included |
| `2026-09-25T12:54:13Z` | `851e816` (SGP40 `W13` fix included) | step 6's wear-gated run; **on the board now** |

`errcount` was saved before every flash and before every `ResetErrors`. After W4's re-run (read
3.7 h later, no reset in between, STA, NTP synced): NTP `E21` ×3 and SGP40 `W13` ×1, both from the
suite's last test blocking UDP 123 — nothing else, SYSTEM clean. The reflash to `12:54:13Z` left
them as they were and added nothing (no FRAM `E31`/`W73` this time). After step 6 and W5 (last
read): NTP `E12` ×2 (W5's unresolvable 1,024-character host) and WEBSERVER `W2`/`W3`/`W2` (the peak
heap test holding the ceiling open) — designed reclaims, SYSTEM clean.

### 5.2 Measurements

| Row | Result | Suggested action |
| --- | --- | --- |
| **W4** | First run (image `19:11:45Z`): 103 passed, 2 failed, 4 skipped, 27 deselected, 49:29 — the page-load test bug (fixed, 1 s settle, `3062cc7`) and a USB drop mid-upload (F17). **Re-run on image `07:31:00Z`: CLEAN — 105 passed, 4 skipped (the two light programs, the UF2 reflash, the known-permanent spoofed-source test), 27 deselected, 49:43.** First silicon run of `assert_no_task_ended` (no task ended anywhere), the post-E6′ webserver changes and the rewritten ceiling instruments; no unexpected reset, no hotspot fallback, no `MemoryError` | W4 is done and confirms SPECIFICATION H.7 and I.3 as they stand. D1's condition for step 6 is met |
| **T4** | 1-byte write 2,833–3,395 us non-yielding (~0.6–0.7 ms per CS command), one read command 783–881 us, block operation holds the bus 18,089–23,148 us (3 runs). In SPECIFICATION F.5.8 | Owner: yield between the CS commands of one write (~3 ms → <1 ms), or keep as is; commit the timing script or not |
| **W3** | `/status` 6,859–6,865 B: median 1.36 s (1.30–1.43 s, 20 idle samples); `/networking` 0.34 s; `/measurements` 0.28 s | Owner: accept, or measure one 1,024 B-piece build for the comparison that does not exist yet |
| **R2** | `ResetErrors` 2.4 s at 0 readers, 5.6 / 10.6 / 13.2 s at 1 / 2 / 3 readers (worst 14.69 s); at 4 readers no result (starved at the ceiling, then over 30 s). Linear, ~+3.5 s per reader. In BACKLOG 24/32 | Owner: BACKLOG 24's design fix (batched or concurrent reset) first; BACKLOG 32's bench budget can only follow it |
| **T1** | In-suite (flash tier, `test_memory_stress.py`, the script's own module-level threshold): baseline `largest_block` 122,016 B → **after `build_system()` 84,112 B**, free 97,280 B, `retained` 0 — identical for the control and production-threshold arms; map: largest free run 84,112 B, highest new block at 55 %, none in the top 32 KB. The board prints `GC_THRESHOLD=` but the test does not echo it | The comparison T1 was written against (archive §7D.3, 20,592 → 28,864 B) is no longer in the tree after `HEAP_FRAGMENTATION_MEASUREMENTS.md`'s rewrite, and its magnitude suggests a different position. Owner: close T1 on this figure, or name the position it should be compared at; echo `GC_THRESHOLD=` in the test |
| **Step 6, wear-gated** | **CLEAN** on image `12:54:13Z`: 126 passed, 4 skipped (the expected four), 6 deselected (the other opt-in gates), 59:15. *Wear spent*: the suite's own config writes | None; D1's round is spent |
| **R1** | Both config-write arms passed, `CEILING_RETRIES` "none" for each — no ceiling refusal and **no reset at all**, so neither branch of the row applies and nothing is left to bisect | Owner: a dedicated repeat of the original PUT + 2 readers shape (18 attempts, 18 flash writes) to measure the rate on this image, or close BACKLOG 30 as not reproduced |
| **R5** | Third green BMP3XX config-write pass — **closed** (row and BACKLOG entry retired) | None |
| **T2** | All six `test_bus_concurrency_under_api_load.py` tests passed, the three `persistence_write` ones included — **done** | None |
| **R4** | Zero-wear variant: logs filled by refused hostname PUTs (WIFI `E20`) and a 4-reader burst (UART), next to NTP/SGP40's own. Round 1: 5 modules populated, `ResetErrors` under 3 readers in 14.58 s → **all 21 read back 0**. Round 2: 12.11 s, and the only entries afterwards were UART ones **absent before the sweep** — logged by the load during it, not skipped by it. **Done: the sweep is complete under contention** | None; see F18 for the UART half |
| **W5** | `NTP_Host` at 1,024 characters (1 write, restored with a 2nd): `/networking` complete (1,182 B), `/status` unchanged (6,871 B) — **it carries no configured host**, so SPECIFICATION I.3's "and in `/status`" was wrong (corrected). Full-ceiling burst and peak heap test both passed; worst of 72 peak samples: largest free run **36,864 B** (after boot 43,536 B). **Done** | None; I.3 now states the measured case |
| **F1** | `wifi_service_reconnect_repro.py`, once, through a wrapper (below): garbage SSID → hotspot phase at 23 s → real SSID restored → **reconnected 20.9 s after `reconnect_wifi()`**, no task death. `config_WIFI.cfg`'s SHA-256 identical before and after (`0c83e9b4…`), `config_HWTEST_WIFI.cfg` removed, board back on the bench AP after a reset with SSID/hostname/NTP host as before. *Wear*: the scratch file's writes. **Verified — row retired** | The script never feeds the watchdog, so on a board running `main.py` it dies ~8 s in; it ran here under a 4-line wrapper arming `WDT(8000)` and feeding it from a 2 s `machine.Timer`. Owner: fold that into the script, or accept the wrapper as the documented way to run it |
| **N2** | `Hostname` removed from `config_WIFI.cfg` (one write, keys confirmed), then one fresh boot: `GET /networking` → `SensorStationDev` (the `devices/dev.toml` default, not the schema's `SensorNode`); CFGMGR_WIFI `W4` ("Key Hostname … missing, using default!"); the boot wrote `Hostname = SensorStationDev` back (a second write). **The substitution path is proven — row retired** | None. Note the repair write: N2 costs two flash writes, not the one the queue stated |
| **T1 race check** | `gc.threshold()` read `-1` at 0.8 s after a reset and `32768` at 38 s uptime — §M3.8's race is confirmed | None; recorded |
| **R7** (partial) | Soft-reset capture (no USB re-enumeration, so the whole boot is visible): imports + `build_system()` + the first setup list take 1.15 s together (that list logs nothing); each FRAM-backed config manager then costs ~95 ms (~33 ms FRAM read, ~33 ms verify, ~25 ms file); 8 timers start 112 ms apart (0.78 s); WLAN up and RTC set at 16.3 s | Per-logger figures for the first list need an instrumented build — owner's call whether they are worth it |
| **R6** | Not measured. The +0.90 s is an A/B delta: the fix moved `fram.setup()` ahead of `sysfunct.setup()`, so only a pre-fix build answers it (2 extra flash cycles, ~30 min) | Owner: run the A/B, or close R6 as not worth the flash cycles (it does not threaten the watchdog) |

### 5.3 First silicon runs of this tree's changes (section 2's table)

| Change | Result |
| --- | --- |
| NTP never ends its task (`c20f80b`) | **PASS**: `test_real_ntp_handles_a_genuinely_unreachable_server_without_crashing` + the test before it, 2 passed. UDP 123 blocked: NTP `E21` (one slot, counter 3), no task ended, SYSTEM clean, no traceback |
| Radio byte bounds (`b5450aa`) | **PASS**: `PUT /networking` with 18 × `ä` (36 bytes, inside the 32-character schema) → `"Invalid"`, hostname unchanged, WIFI `E20` |
| `PERIODIC` hotspot timer (`b5450aa`) | **PASS**: after a real fallback the board returned to STA by itself after the 8 min window, with no reboot (uptime continuous) and no SYSTEM entry |
| G11, schema-derived cache in `bmp3xx_plausibility_read.py` / `sgp40_fram_backup_restore.py` | **PASS**: flash tier clean — 36 passed, 3 skipped (both light programs, the UF2 reflash), 12 deselected, 14:48 |

### 5.4 Findings

- **F18, four back-to-back `/status` readers saturate the board** (queue F18): the `ResetErrors`
  `PUT` starved at the ceiling, WEBSERVER `W2` ×20, UART link `E20`/`E22`/`W10`. No reboot, no task
  ended. **R4 showed the UART half starts earlier**: three readers during a sweep were enough for
  `E20`/`E22`/`W10` on both link ends. *Suggested*: owner decides whether zero-think-time clients are in contract; if yes, the
  admission policy needs fairness (a writer can be starved indefinitely today).
- **SGP40 `W13` fills its error history while NTP is absent**: one "backup written without
  timestamp" slot per backup (1 min), 9 slots after one hotspot episode, so the ring loses what
  preceded the outage. **Fixed in the tree since** (C.7.1's repeat rule: one slot per outage, the
  count still rises, a timestamped backup ends the episode), not on the board's current image —
  the next reflash should show `W13` once per outage, with `ErrCount` still counting every backup.
- **Three hotspot fallbacks, all the stale-AP-station mechanism, all caused by this session's own
  procedure** (WIFI `W6` ×5, `reset_cause()` = `WDT_RESET` where read): a reset with no
  `kick_all_stations()` *immediately* before it. Kicking 50 s early does not help — the board
  re-associates in between. *Suggested*: record in `tests_hardware/README.md` that the kick must be
  the step right before the reset, and give ad-hoc scripts a helper that does both.
- **FRAM `E31` + `W73` at the first boot after flashing**: `mpremote exec machine.bootloader()` most
  likely landed mid-write; the dual copy repaired it (block 1 rewritten from block 0). Designed
  behaviour, but it means entering BOOTSEL this way can cost one FRAM log entry. *Suggested*: none
  beyond noting it; the harness's `enter_bootloader()` has the same property.
- **An `mpremote` attach within ~1 s of boot parks the board at the REPL with no watchdog armed** —
  it never recovers on its own (no ~8 s reset), unlike a later attach. *Suggested*: add to section
  6's traps / `tests_hardware/README.md`.
- **The flash tier always leaves the board parked at the REPL.** Its last test,
  `test_watchdog_starvation_triggers_a_real_hardware_reset`, polls `board.is_reachable()` (a raw-REPL
  attach) every 0.5 s right after the real watchdog reset, so it attaches within ~1 s of boot — the
  case above — and `main.py` never arms the watchdog again: no WiFi, no serial output, until the
  next reset (found at `reset_cause()` = `WDT_RESET`, `ticks_ms()` pointing at that test). The bench
  tier survives it because its fixtures reset first. *Suggested*: end the test with a
  `hard_reset()` and a wait for REST, so a tier never ends on a dead board.
- **Two stale scratch configs on the board's flash**: `config_HWTEST_DEBUGLEVEL_BACKUP.cfg` and
  `config_HWTEST_REBOOT.cfg`, left by earlier device scripts (neither is F1's, which cleaned up
  after itself). Left untouched. *Suggested*: owner decides whether their scripts should remove
  them, as F1's now does; the DebugLevel backup in particular could mislead a later restore.
- **An attach at 1.0 s after reset is already too late to catch the board before its watchdog**:
  `main.py` had set its GC threshold and the watchdog reset followed. So "attach within ~1 s parks
  the board with no watchdog" (5.4 above) is a narrower window than 1 s, and not a usable way to
  get a watchdog-free board; feed the watchdog from the script instead (F1's wrapper).
- **F17, USB drop mid-upload during W4's first run**: still unexplained; the clean re-run did not
  reproduce it.
- **Own process error, recorded so it is not repeated**: R2's first script retried a refused `PUT`
  without bound and ran 1 h 40 min. Ad-hoc scripts now cap retries and run under `timeout`.

### 5.5 Still owed this sitting, shortest first

1. ~~W4 re-run~~ — done, clean (5.2).
2. ~~Step 6~~, ~~R4~~, ~~W5~~ — done (5.2).
3. ~~F1~~, ~~N2~~ — done (5.2).
4. M1 + S3b (needs the owner at the bench, ~30 min).
5. R13 + N3, and the step 9 scripts — code first.
6. Owner decisions from 5.2 and 5.4.

## 6. Traps that have actually cost time

The full list is the queue's section 6 and `tests_hardware/README.md`. The ones most likely to bite:

- **An unreachable DUT is usually your own `mpremote` call.** `exec`/`run` stop `main.py`, and the
  armed watchdog resets the board ~8 s later. Diagnose passively: `hard_reset()`, `tail_log()`, then
  curl; poll `SysUptime` to tell a reboot loop from replayed history.
- **Leave > 45 s between a reset and the next `mpremote` attach.**
- **An attach within ~1 s of boot parks the board with no watchdog** until the next reset; end any
  poll-after-reset with `hard_reset()` (`tests_hardware/README.md`).
- **At the connection ceiling a reset before any response is a refusal, not a failure**
  (`http_client.is_ceiling_close()`); assert the property the feature owns, plus a floor on how many
  were answered.
- **Deauth (`kick_all_stations()`) logs nothing on the DUT**; a WIFI-log check needs a real
  `bench.ap_down()` outage.
- **Destructive bench-host network tests keep a dead-man's switch armed for the whole window**
  (SPECIFICATION.md B.13).
