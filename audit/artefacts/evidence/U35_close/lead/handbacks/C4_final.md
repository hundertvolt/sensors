C4 hand-back (lane C, audit/u35-c, S/wt-u35c). One commit, 8c2b458, on top of 0547def. Nothing uncommitted, nothing pushed. About 72 tool calls.

**Steps by verdict (all applied in 8c2b458)**
- **`ntp_clock_valid()`**: one bool. Set in `_handle_ntp_sync_success`, cleared in `ntp_force_sync`; staleness leaves it set. Three new tests in tests/test_asy_ntp_client.py: turns valid at a sync; a settings change unsets it until the next sync; it stays valid when the sync goes stale.
- **Codegen**: `UTCTime` and `SgpBackup(<fram>, ntp.ntp_clock_valid)` read the new check. SystemService keeps `ntp.ntp_issynced`. `/status` system gains `"TimeStale": None if utc_now() is None else not await ntp.ntp_issynced()` after `UnixTime`.
  - test_buildgen_generate: key order, the utc gate, the TimeStale expression, the SystemService argument; the SgpBackup test is renamed and re-pinned.
- **Website row and mock data**: definitions row `TimeStale`, "Time May Be Stale", readonly, with a description. samples.json gets `"TimeStale": false`. Pinned in test_buildgen_definitions, plus one new test in each of templates.test.js and definitions-mockdata-coverage.test.js.
- **asy_sgp40_driver.py**: comment only. mpy-cross: sgp40 bytes identical; ntp_client differs, 8710 → 8782 bytes (outputs in S/u35/laneC/c4/mpy/).

**Seen failing first** (logs in S/u35/laneC/c4/)
- ntp: all 3 new tests failed on the old code with AttributeError (189/192). Scratch bites, one per transition, each failed only its own test:
  - `ntp_clock_valid` returning `ntp_issynced` → the stale test;
  - no clear in force_sync → the settings-change test;
  - no set on sync → all 3.
- buildgen: 30 failures (5 tests × 6 devices).
- JS: templates failed on 6 devices ("no TimeStale field"); mockdata coverage failed with "expected undefined to be false".

**Per mode and device**
- All six devices take the same code path: each runs the NTP client and the generated module, and each has an SGP40 VOC backup on FRAM.
- STA: if every resync fails for 3 × NTPInterval, `UTCTime` stays shown, backups keep their timestamp, and `TimeStale` is true.
- AP, Silent, Off: no sync runs, so a clock set earlier this boot goes stale 3 × NTPInterval after its last sync and stays in use, with `TimeStale` true.
- USB: unaffected.
- After a settings change, `UTCTime` is null, backups wait for the next sync, and `TimeStale` is true.
- No bus, wiring, persistence or UART byte changes.

**Red checks**
- test_twin_record `test_every_entrys_hashes_are_the_current_files`: red, as expected.
- tests/_sensortask_scenarios.py:2728 (Y's file): `webserver_status_publishes_utc_time_only_after_the_first_ntp_sync` fails on all 6 devices at both stages, 90/91. Its :2726 patches `ntp_issynced`; it needs `ntp_clock_valid`. Waits on Y4; written in the `<CLOCK>` line.

**Relay**: `<CLOCK> 8c2b458` under `## C`; the A.8/F.1 facts and the stale SPECIFICATION/BACKLOG lines under `## D`.

**Not my files, owed to others**: buildgen/graph.py:65's comment ("built with ntp.ntp_issynced") is now stale. No allow-list row was orphaned.

**Runs** (all rc 0 and zero memory markers, except where noted)
- Pre-commit:
  - ruff and the 4 mypy passes: clean.
  - eslint, tsc and lint-ceilings: pass.
  - The 12 checks plus pure readers: 3020 passed, 1 failed (twin_record).
- Twin/runner readers: all pass.
- Generated-module files on the head at -1 and 32768:
  - test_sensortask ×6: red, as above.
  - The integration file per device: arzi 118 s, the others ~22 s.
  - bus_hazard_generated, launch, machine, run_generic, generated_boot_entry, neopixel_wifi, reset_invariant, wifi_modes, uart_link, bus_hazard_concurrency (150 s).
- JS on the head: templates 122/122, coverage 12/12.
- **NTP paired times (base → head)**: -1: 23.53/23.61 → 26.14/26.27; 32768: 24.16/24.17 → 26.74/26.76. **+11 %, +2.6 s, a file over 10 s: needs to be made efficient** (C5).
- RUNS.md has start and done lines for pids 21696 and batch2. Nothing of mine is running.

**Decisions (agent, 2026-10-21)**
- A config-read failure clears Synced but not the clock: it is not a settings change.
- The JS runs use a temporary ignored symlink `node_modules` → S/wt-u8/node_modules. The main repo's tree lacks `@eslint-community/eslint-plugin-eslint-comments`. The link is left in place for C5.

**C5 starts from 8c2b458**
- First: fold `test_the_clock_stays_valid_when_the_sync_goes_stale` (tests/test_asy_ntp_client.py, after the existing stale test) into `test_refresh_marks_the_sync_stale_three_intervals_after_the_last_success`. They run the same 1081-tick drive. Then re-time paired at both stages.
- Then: D.15 last edit, C's complete checks, and the 17 scans.
- The cancel in my stale test runs after the task has started (shim note).
