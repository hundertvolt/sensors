complete2 hand-back, written by the agent (Mon Nov  9 17:19:02 UTC 2026)
Pass 2 of BRIEF_COMPLETE.md, read only, tree `S/wt-u35int` (b412d1b3); started 2026-11-07, stopped by the weekly limit, resumed 2026-11-09. C = confirmed (code, git, datasheet, recorded measurement), I = inferred. No probe ran. Not redone: LEVELS_2's twin-guarded rows (`lag.loop`, `rate.persisted_log`, `feed.supervisor`), bfix's removed slice tests, STRETCH's two fixes. Firmware-facing first, ranked.

## 1. tests/ and digital_twin/: models that hide a cost, tests on the harmless case, tests that pin a cost
1. **The twin's CPU speed has no fidelity row, so every twin time figure is the harmless case** ((a)+(c); C).
   - The README's contract is "every fact the fake does not model is a fidelity-table row" (`digital_twin/README.md:1211`). Rows 210-280 have none for interpreter speed. Heap has one ("a heap figure here is a tripwire only", `:267`); time has none.
   - Factor: the board is x132-141 slower on the serving walk and x186 on the VOC step (STRETCH). E.8 (SPEC :5944) says 50-100x and "throttle ... before trusting a limit", but applies that to heap only.
   - Host figures checked against silicon consumers: `loop_lag_under_combined_load` (`scripts/_digital_twin_scenarios.py:1268`, `:1301-1302`: host 21-74 ms against `smallest_hard_consumer`, board 155 ms, LEVELS_2 #3); Run 3 and the supervisor scan (LEVELS_2 #1); `tests/test_asy_webserver_connections.py:1074` (`< 2000`) and `:1175` (`< 500`), which compare a host loop gap with "the supervisor's 2 s check interval".
   - SPI wire time defaults to 0 (`digital_twin/machine.py:670`); one erase test sets it (`tests/test_digital_twin_bus_hazard_concurrency.py:1170`). About 1 us/B at 8 MHz, small next to the CPU factor.
   - Origin: table audit 10-14 (311aef80); lag scenario audit 10-21 (72b12815). Leaner, no code: one row giving the factor and saying a twin time figure is a tripwire, never a budget's evidence; the three checks' comments say the same. This row is the missing guard.
2. **I2C "zero transaction time" was accepted as "electrical" (README :212, agent 10-14; owner-reviewed 11-06), but the cost is timing: a clock stretch holds the whole loop** ((b); C facts, I effect).
   - Facts: rp2's `machine.I2C` is synchronous (SPEC :6750). SCD30 Interface Description 1.1: "Clock stretching period in write- and read-frames is 30 ms", 150 ms about once a day.
   - Frames: a sample is 4 (`asy_scd30_driver.py:820-824` via `:689-722`), a config snapshot 12 (`:740-745`). Bound: 120 ms loop stall per sample, 360 ms per snapshot (I: datasheet bound, frequency unknown).
   - Measured: failed transfers only (50.9 and 200.9 ms, :6750). The flash test watches only the once-a-day case and "proves only the absence of a failure" (`tests_hardware/flash/test_bus_electrical_timing.py:74-85`). The twin models 0. The routine stretch is measured at no tier.
   - Leaner, no code: measure a successful SCD30 frame on dev (its SCD30 is on i2c1) via `loop_stretch_timing.py`, then restate the row's premise. Origin: audit 10-14.
3. **WLAN `active()`/`deinit()` return at once in the twin** (`digital_twin/network.py:197-210`), with no fidelity row saying so (rows :271-277) (C; magnitude I). F.3 `stall.wlan_switch` is "owed" (SPEC :6759); its consumer is `con.uart_reply` on dev. The twin's mode-switch scenarios cannot show the CYW43 firmware upload's synchronous stall. Leaner: a row plus the owed bench figure. Origin: audit 10-14/10-21.
4. **Tests that pin a cost, not a function; each blocks an agreed or proposed lean fix** (C):
   - `tests/test_asy_crc_checks.py:836-863`: at least len/2 competitor turns per CRC, i.e. the per-byte yield (DESIGN_FU 4c). Pre-audit 08-11 (67dd1382). Keep the result check; drop the turn count.
   - `tests/test_asy_framing_codecs.py:93-115`: one turn per COBS block (LEVELS_3 #8). Audit 10-27 (2e826c28).
   - `tests/test_asy_webserver_service.py:1294-1301`: every source starts before any finishes, i.e. ResetErrors' `gather` (owner go 12.107(1): sequential). Audit 10-07 (8d44fd14). I: the in-flight reset mask tests (`tests/test_asy_print_log.py:1125-1181`) may lose their reason too; the unit should check.
   - `tests/test_asy_webserver_service.py:3719`, `:3738-3745` call `_shape_errcount_entry`, which STRETCH's fix drops; the bytes and the piece bound are the function and stay.
   - 12.107(5)'s pinning files (reference counts, C): `_sync_age` `test_asy_ntp_client.py` 30, `_sensortask_scenarios.py` 4, `test_digital_twin_clock_jump.py` 2; `_pause_loop` `test_asy_notification_service.py` 3; `Locked*` `test_asy_base_classes.py` 25; `PieceBuffer` 7 files (imports only); overlay `test_asy_neopixel_driver.py` 19, `test_neopixel_wifi_integration.py` 6, plus 4 `tests_scripts` inventories; `get_last_ntp_sync` 2 files; `verify_present` 4 files.
- **Checked and clean**: `_flash_stall.py` models a flush's pages at the largest file; UART wire time, DMA and FIFO are modelled; the Timer drop knob exists; NeoPixel has its row (about 30 us a pixel); SGP40's driver waits its own delays; BMP3XX's default OSR x1/x1 is about 4.8 ms, 2-3 STATUS polls, nothing beyond need; unit-tier DrivenTime clocks check function only; bfix's mock-tier round count (T2) is the right proxy for a hold.

## 2. buildgen/ and the five generated modules besides wozi
- **Production: clean** (C, filtered diffs of `build/generated_src/*.py`). grkizi, klkizi and schlafzi are identical apart from the header and identity lines. arzi is the same with wozi's SPI/FRAM pins. All four are wozi minus BMP3XX. Nothing wozi lacks: FRAM logging for all, SGP40 compensation through SCD30's await-free `ValueRef`, SCD30 alone on i2c0, the same `ServingLimits`. `ntp_force_sync()` before `supervise_tasks()` only sets an event (`asy_ntp_client.py:499-508`), so the watchdog feed never waits on NTP.
- **dev only** (C): SCD30 shares i2c1 with SGP40 and ISL29125, whose reads queue behind its held 50 ms sessions (LEVELS_3 #6). The 200 ms timeout covers their failed transfers too (in `stall.i2c_transfer`). FRAM is 256 KB against 8 KB. dev's silicon figures are therefore the worse case.
- **Gap** (C facts, I effect): wozi's own pairing, SGP40 + BMP3XX on i2c1, is on no flashed board (dev has BMP3XX alone on i2c0), and the twin models neither I2C nor conversion time. Its `stagger.min_read_separation_ms` (100, "estimated, measurement owed", `tests/_sensortask_scenarios.py:70-73`) therefore has no figure at any tier. Leaner: name it in that owed measurement; no code.

## 3. scripts/, toolchain/, ci.yml (headlines)
- **`unit-tests-gc-threshold` reruns the host pytest tier for an identical result** (C).
  - The job (`ci.yml:441-462`) runs `scripts/test.sh` whole, including the backgrounded `tests_scripts` tier (`test.sh:498`). No host test reads `GC_THRESHOLD`; the one reference (`tests_scripts/test_test_sh.py:695`) strips it.
  - Cost: 579 s single-process (SPEC :5509, 2026-10-13) in a 9.0-14.0 min job (:12180); at 16 jobs that tier is the binding constraint (`test.sh` comment).
  - Leaner: with `GC_THRESHOLD` set, skip it and say so in the summary (one condition). Origin 09-21 (1bbce052).
- **Every tier fans out over one hardware family of identical modules** (C facts; owner decision owed).
  - The three arzi-neu devices differ only in identity (owner 2026-10-23; SPEC :10822, a label "the test suite only" reads, since 10-08, f76385a6), yet every tier runs each.
  - Cost: 4 of 12 `digital-twin-e2e` legs (`ci.yml:549-569`; 9.3-10.6 min a leg, :12182); 2 of 6 firmware builds (2.1-2.9 min); 2 of 6 per-device files and scenario jobs in each of the three `test.sh` jobs; the live-backend web runs (SPEC :8306).
  - Leaner: one device per `hardware_family` in the twin, scenario and per-device tiers, with `tests_scripts/test_device_tomls.py:60` standing for the rest. For the owner, since E.6.1 says "every device".
- **Checked and clean**: the e2e harness part and `test.sh`'s scenario jobs split the port-53 scenarios with no overlap. The coverage job's pytest rerun feeds the host report its summary reads.

## Notes
- Slips: one `git grep wire_time_us_per_byte` over the whole tree ran without the filter and listed 9 `audit/` lines (that identifier only, nothing secret shown). One Python read of `build/generated_src/definitions/wozi.json` printed only its `PresOvers`/`TempOvers` entries.
- Scratch: `ftmp_complete2/ds/` (SCD30 datasheet text). Nothing of mine is running.
