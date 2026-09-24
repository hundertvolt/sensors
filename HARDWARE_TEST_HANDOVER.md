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

- **Board**: `dev` bench, image E6′ (`buildDate 2026-09-24T06:45:32Z`, `max_connections = 6`,
  `DebugLevel` 5). It is **behind the tree** and must be reflashed (section 2).
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
3. **G11, code at the sitting** — switch `bmp3xx_plausibility_read.py` and
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

## 5. Traps that have actually cost time

The full list is the queue's section 6 and `tests_hardware/README.md`. The ones most likely to bite:

- **An unreachable DUT is usually your own `mpremote` call.** `exec`/`run` stop `main.py`, and the
  armed watchdog resets the board ~8 s later. Diagnose passively: `hard_reset()`, `tail_log()`, then
  curl; poll `SysUptime` to tell a reboot loop from replayed history.
- **Leave > 45 s between a reset and the next `mpremote` attach.**
- **At the connection ceiling a reset before any response is a refusal, not a failure**
  (`http_client.is_ceiling_close()`); assert the property the feature owns, plus a floor on how many
  were answered.
- **Deauth (`kick_all_stations()`) logs nothing on the DUT**; a WIFI-log check needs a real
  `bench.ap_down()` outage.
- **Destructive bench-host network tests keep a dead-man's switch armed for the whole window**
  (SPECIFICATION.md B.13).
