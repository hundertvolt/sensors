# Real-hardware test queue

The single list of everything waiting on the dev bench, so one go-ahead session can run it all in
one go instead of rediscovering it from five documents. Temporary, like every other queue doc here:
each row is deleted once its result is migrated into `SPECIFICATION.md`/`CLAUDE.md`/`BACKLOG.md`,
and the file goes when the last row does.

**Nothing here authorizes anything.** CLAUDE.md's standing gate still applies: a session needs the
project owner's go-ahead, given in that session's own conversation, before any `mpremote`, `nmcli`,
`picotool` or `tests_hardware/` run. `tests_hardware/README.md` remains the technical reference for
prerequisites, flags and safety facts; this file only says *what* is owed and *why*.

Status values: **OPEN** (owed), **BLOCKED** (waiting on a decision or another row), **DONE**
(result migrated — row deleted at that point), **EXCLUDED** (belongs to another effort).

---

## 0. Decide before the run

These change what gets run, so settle them first.

| # | Decision | Why it matters | Status |
| --- | --- | --- | --- |
| D1 | **Does the bench spend flash/NVM writes this round?** A default run deselects 13 of the bench tier's 73 tests and 9 of the flash tier's 51; `--allow-persistence-writes` runs them and spends real cycles. `--allow-scd30-extra-write` is AND-gated on top for one further SCD30 NVM write. | Several rows below are *only* reachable with the flag — R1 and R4 in particular. Deselection is invisible to the pass/fail check, so this must be a knowing choice (CLAUDE.md's wear rule). | OPEN |
| D2 | **Is the NeoPixel-aimed-at-the-ISL29125 rig set up?** The gating question is **settled** — `main`'s `@pytest.mark.neopixel_sweep` + `--allow-neopixel-sweep` has been adopted here (2026-09-18), so `test_isl29125_survives_recombined_realistic_lighting_scenarios` (~8.5 min) and `test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration` (~99 s) now skip by default instead of failing on a bench without the rig. What remains is the physical question: decide whether to pass the flag this round. | The 2026-09-17 bench session ran both ungated and they passed after the `_park()` fix, which suggests the rig *is* in place — confirm rather than assume, and record the geometry via the manual tier's `isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` (M1) so the next session does not have to. Opting in costs ~10 min. | OPEN |
| D3 | **Which firmware image.** Every row below assumes a `dev` build from this branch's own tip via `scripts/build_firmware.py dev`. | CLAUDE.md's hard rule: a `wozi` build flashed onto the dev bench "tests nothing at all" and has produced false bugs before. | OPEN |

---

## 1. Suite runs

| # | Run | Notes | Status |
| --- | --- | --- | --- |
| S1 | `scripts/run_flash_hardware_suite.sh` | Full flash tier. Read the verdict's **deselected** count, not just "clean" (`scripts/_require_clean_hardware_run.sh`). | OPEN |
| S2 | `scripts/run_bench_hardware_suite.sh` | Full bench tier (strict superset of flash). Same deselected-count caveat. | OPEN |
| S3 | The same two with `--allow-persistence-writes` | Only if D1 says yes. This is what makes R1/R4 reachable at all. | BLOCKED on D1 |
| S3b | `scripts/run_flash_hardware_suite.sh --allow-neopixel-sweep` | Only if D2 says the rig is in place. Runs the two long ISL29125 light programs (~10 min combined); they skip otherwise. | BLOCKED on D2 |
| M1 | `scripts/run_manual_hardware_tests.sh --only isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry` | Interactive. Repeatability on an unchanged scene, continuity across the range switch, **and** setting up and writing down the rig geometry S3b depends on. Worth doing before S3b, not after. | OPEN |
| S4 | Long memory soak (`long_soak` tier), never bundled into S1/S2 | A real long-duration memory-soak run has still never been executed (README.md's own "Further reading" note, carried from the retired hardware-planning docs). Pick the tier deliberately: short=60 s / mid=600 s / long=6 h. | OPEN |

**Before any of this**: read `GET /status`'s `errcount` and record it. CLAUDE.md's rule — the
FRAM-persisted per-module logs are the one piece of diagnostic evidence a reboot does not erase, and
`ResetErrors` destroys them irreversibly. Also check what has already been run against the board: an
isolated-driver device script builds its own `AsyFramManager` over the same chip and can leave a
plausible-looking fabricated entry behind (`tests_hardware/README.md` has the mechanism).

---

## 2. Targeted investigations

| # | Investigation | Source | Status |
| --- | --- | --- | --- |
| R1 | **BACKLOG item 30 — the ISL29125 HTTP connection reset under concurrent API load.** Owner's direction is to root-cause and resolve, not re-measure. Shape is established: needs **both** a config-persisting PUT **and** ≥2 concurrent readers (PUT alone 0/10, PUT+1 reader 0/6, PUT+2 readers **6/18**, plain GET+2 readers 0/6); failures land at 21–72 ms against 0.5–2.2 s for successes, and `WEBSERVER`'s counter stays 0 so FRAM forensics will not help. **Do the no-code bisection first**: `PUT /sensors {"ISL29125": {"RangeAuto": false}}` drops `_switch_range()` from the three-step push, leaving only `configure()` + `_reapply_persist()`. Rate falls → the threshold re-arm is implicated; unchanged → it is the first two. Restore `RangeAuto` afterwards. | `REAL_HARDWARE_HANDOVER_PR103.md` §1; BACKLOG 30 | BLOCKED on D1 |
| R2 | **BACKLOG item 32 — the `ResetErrors` reader-count curve.** Elapsed time at **0, 1, 2, 3, 4, 6** concurrent `GET /status` readers. Two points exist (6.32 s idle, 11.58 s at 3 readers = 77 % of the 15 s server cap); two points cannot say whether the curve flattens. | `REAL_HARDWARE_HANDOVER_PR103.md` §2.1; BACKLOG 32 | OPEN |
| R3 | **BACKLOG item 29 — the spurious `W4`.** A real outage logged `W4` ("WLAN wrong password") twice alongside the expected `W5`, on a network whose password never changed. One look at whether CYW43 genuinely reports that mid-transition (making `_assert_wifi_log_has_only_benign_ap_not_found_warning()` wrong) or whether `_poll_sta_connect_status()` mis-maps it. Do not chase far. | `REAL_HARDWARE_HANDOVER_PR103.md` §2.3; BACKLOG 29 | OPEN |
| R4 | **`ResetErrors` completeness under contention.** Pre-populate the FRAM error logs on several modules, then sweep under R2's reader load and confirm every counter reads back 0. All previous correctness checks were made at idle or with the logs already empty; a silently skipped chunk is invisible today because the call still answers `200`. | `REAL_HARDWARE_HANDOVER_PR103.md` §3 | BLOCKED on D1 |
| R5 | **BACKLOG "Refactor targets" — the WP5 deferred-config-write re-confirmation.** The BMP3XX arm passed on 2026-09-17 on WP5 firmware; make that durable rather than one run. The ISL29125 arm is R1, not this row. | BACKLOG, first entry | BLOCKED on D1 |
| R6 | **Boot latency for WP1–WP8.** Already measured (pre-WP **7.74 s** → WP1+WP2 **9.80 s** → WP1–WP8 **9.76 s** → +`CFGMGR_SYSTEM` fix **10.66 s**, medians of 5, spread ±0.06 s; 23 reboots, no `WDT_RESET`) — but **only inside unmerged PR #102**. Re-run only if that PR is abandoned rather than landed. The open sub-question either way: the `CFGMGR_SYSTEM` setup-order fix costs **+0.90 s**, far more than one extra FRAM-backed logger's `setup()` should, and is unexplained. | PR #102; `REAL_HARDWARE_HANDOVER.md` | BLOCKED on the PR #102 decision |
| R8 | **Two newly adopted bench tests, never yet run on silicon** (ported from `main` 2026-09-18, see BACKLOG item 33). `test_isl29125_calibrate_command_push_over_real_rest` pins that a calibration run never moves the *applied* `GainRatio` and that `GainMeas` reaches `/measurements`; `test_isl29125_gain_ratio_survives_a_real_reboot_as_an_ordinary_config_value` pins that ratio across a real hard reset. The second is `@pytest.mark.persistence_write`-marked here (it owns two persisting PUTs) where `main` left it unmarked, so it needs D1. Both were written against `main`'s API shape and adapted to this branch's nested `PUT /sensors {"ISL29125": {...}}` body — expect the adaptation to be where a first run goes wrong, if anywhere. | BACKLOG 33 | calibrate: OPEN / reboot: BLOCKED on D1 |
| R7 | **`SPECIFICATION.md` Part A.7's FRAM setup-cost figures are twin-only.** `digital_twin/_fram_chip.py` answers SPI opcodes in memory with zero wire time, so every number there excludes the dominant real term (SPI wire time under lock contention). Re-measure on silicon. Largely the same instrumentation as R6. | SPECIFICATION.md Part A.7 | OPEN |

---

## 3. Coverage gaps that need a bench session to close

From `tests_hardware/README.md`'s "Tenth pass", which names these as owed rather than fixed. Each is
a test to *write* against real hardware, not just a run.

| # | Gap | Status |
| --- | --- | --- |
| C1 | **F.5.8's "UART never blocks the loop" is only proven against a hand-rolled clamp, never the shipped driver.** `device_scripts/uart_read_never_blocks_the_loop.py` uses raw `machine.UART` deliberately, so no real-hardware run ever exercises `asy_uart_driver`'s own `ready()`/`_buffered()`. F.5.9 already has its real-driver-object proof (`uart_idle_poll_rate.py`); F.5.8 needs the analogue. | OPEN |
| C2 | **The bench UART exerciser never issues a multi-chunk SET**, so "bench ⊇ flash" does not hold for the SET train the flash tier proves. Wire a periodic SET into `UartLinkExerciser._exercise_loop()`'s live load. | OPEN |
| C3 | **Decide whether the mock tier's ~20-scenario UART fault-injection catalog is a genuine structural exception** or needs a raw-second-UART injection technique on the bench. | OPEN |
| C4 | **`_reboot()`'s alarm-pool-exhaustion fallback (`_force_watchdog_starve = True`) is mock-only.** | OPEN |
| C5 | **NOTIFY's own FRAM chunk has no hard-reset-recovery bench test**, unlike SGP40's. Needs an observable-write signal analogous to SGP40's `BackupTS` first. | OPEN |
| C6 | **`BenchBridge.rotate_ap_password()` is built (real `nmcli`) but has zero call sites.** Needs a project-owner design review before any bench test — it rotates real AP credentials on the shared rig. | BLOCKED on owner |
| C7 | **`test_ticks_ms_real_2pow30_rollover` needs a measurement method that does not poll with `board.exec()`.** BACKLOG item 12 established on real hardware that every `exec` starves the watchdog and hard-resets the board ~8 s later, zeroing the counter — so the hour-by-hour poll can never climb toward 2**30, and a later read landing below an earlier one is the reboot, not a wrap. The vacuous-pass hole is closed (a drop now only counts as a wrap when the previous read was already within two hours of 2**30, so the ambiguity fails honestly), but that makes the test *fail* rather than measure. A real method has to leave the board running: feed or disable the watchdog from inside the polled code, or observe passively via `tail_log()`. Design decision, then a genuine ~12.4-day run behind `--allow-multi-day-rollover-wait`. | OPEN |

---

## 4. Bench-host tasks (not the board)

| # | Task | Status |
| --- | --- | --- |
| H1 | **The two-chroot pre-push gate, unsatisfied since 2026-09-12.** Everything this branch changed in `scripts/`, `pyproject.toml` and — the highest-risk part, which the lint/typecheck recipe never exercises — `toolchain/setup_toolchain.py` + the new `toolchain/micropython_overrides.py`. The bench Pi4 already runs trixie/GCC 14.2, so it is the right host for the leg that has never run. Full account and what changed: BACKLOG.md's own entry. | OPEN |
| H2 | **`scripts/test.sh`'s parallelism probe on the Pi4.** Report the `== Test parallelism: N (C usable cores x M, interpreter speed probe Xms)` line verbatim. Thresholds (4x ≤250 ms, 2x ≤900 ms, 1x beyond) were calibrated from an x86 sandbox plus a *simulated* slow host, never the real Pi4. Confirm it lands on 2x and that the previously-starved twin test (`test_digital_twin_sensortask_integration.py`'s hotspot/DNS case) passes. If it still starves at 2x, say so — the next step is 1x for that class, not re-tuning the probe. | OPEN |
| H3 | **Two bench-rig capabilities are not provisioned**, each of which would move one `[MANUAL]` test candidate to `[AUTO]`: a programmable GPIO fault-injection harness, and a second WiFi test client (BACKLOG item 8). Provisioning is a hardware decision, not a test run. | BLOCKED on owner |

---

## 5. Excluded on purpose

- **Heap fragmentation** — belongs to the session working PR #105
  (`HANDOVER_HARNESS_AND_HEAP_FRAGMENTATION.md` is its handover). The one failure left at PR #103's
  close is that defect. Not this queue's business; listed so it does not look forgotten.
- **PR #84's three bench passes** (`reactive` full suite 95 passed/2 skipped; `reactive` + churn
  pressure tests 3 passed; `threshold` full suite 95 passed/2 skipped) are already run, on that PR's
  own branch. They do not need repeating — but note **none of PR #84 is on this branch**, so its
  `--gc-policy` / `--memory-pressure` machinery is not available to any run listed above.
- **Round 1's three answered requests** — `ResetErrors` idle timing, WIFI's all-or-nothing log
  across an abrupt restart, and the two `uart_link` instances through the reset path. Answered and
  migrated (SPECIFICATION.md Part A.7, BACKLOG 24). Do not re-measure.

---

## 6. Standing traps for whoever runs this

Condensed from `REAL_HARDWARE_HANDOVER_PR103.md` §4 and CLAUDE.md, because they are the ones that
have actually cost something:

- **`bench.kick_all_stations()` (deauth) generates no WIFI log entries** — a persistence check built
  on it passes vacuously `0 → 0`. Use a real `bench.ap_down()` outage.
- **Any destructive test of the bench host's own network config keeps a recovery dead-man's-switch
  armed for the whole risk window.** A one-shot timer consumed by an earlier dry run gave zero
  protection to the real run that followed, and cost the Pi4 its own SSH access (SPECIFICATION.md
  Part B.13).
- **The hotspot role reversal's stage 0 clears the DUT's persisted SSID.** Stage 7 now restores it
  over the hotspot, but a failure between them used to leave the board permanently in hotspot mode
  with no STA config, recoverable only over the serial REPL. It has happened.
- **Don't chase `asy_fram_manager.py`/`asy_fram_driver.py` internals** from anything found here —
  heavily audited, and any real change there needs its own scoped review (SPECIFICATION.md C.3.1).
