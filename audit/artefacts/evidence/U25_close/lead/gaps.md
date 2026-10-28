# U25 lane plan draft: gaps (sites checked against `e14d76f`; packet `pk/U25_steps.md`)

Planned against U24's v0 plan as written (`u24/lane_plan_draft.md`, `u24/gaps.md`); every default below is
conservative and reversible, decided on the owner's behalf for review at the close (agent, 2026-10-13). Section numbers
"A-n" are the plan's section 5.

## 1. Actions not placed in a U25 lane, or placed only in part

| action | why | where it lands |
|---|---|---|
| A.U25.61 (2)-(4) | the device scripts and the flash wrapper are `tests_hardware/` (U26's: device from data needs U26's harness helper, the shared probe is M.HW_DEV.116's U26 file); only (1), the L0 equality read of both scripts' probe constants, is written at U25 (P, `tests_scripts/test_digital_twin_boot_contiguity.py`) | U26 (M.HW_DEV.116/.117), A-17 |
| A.U25.64 (3) | the 50 x 2 reproduction is a twin CI run, which lanes never start (U23 common rules); S writes (1)-(2) (signal report, `--only`/`--repeat`) | the lead runs it after S's final (A-15); a reproduction becomes a root-cause item, "not reproduced" becomes Y's BACKLOG owner-question entry (M.DOCS.067) |
| A.U25.12 (7) | landed at U23 (lane M, A-14: `ForceCalRef` reads back the last applied value, 400 on a fresh mock; `tests_js/mock-server.test.js:591-599`) | C verifies only (steps 30, 31, 138) |
| A.U24.53 (deferred from U24) | the JS commands' per-run config dir needs R's `--config-dir` | S (wave 2) |
| A.U24.65, A.U24.70 (deferred from U24) | need A.U25.25's device helper | P (wave 1) |
| A.U24.34, .36, .37, .47 (deferred or carried) | travel host-side with the scenario rewrite (M.TEST_HELP.033, AC3_R R-08 (c)) | H (wave 2); .47's runner flag `--test-fault-status-interval-ms` is R's |
| A.U17.16, .24, .25 (deferred to their L2 files) | the two L2 UART files are born at U25 (A.U17.25's L3/L4 half stays U26) | G2 |
| A.U10.28, A.U18.26 | L2 clock-jump halves need the wall clock | M (`_wall_clock.py`), G2 (`test_digital_twin_clock_jump.py`) |
| A.U15.41, A.U18.23, A.U18.24, A.U10.12, A.S0930.36 | L2 timer-arm halves | G1 (`test_digital_twin_timer_pool.py`) |
| A.U14.38, A.U16.R01-R03, A.U15.R01-R05, A.U18.R01, A.U14.R01, A.U20.08 | twin knobs (M, C, N), L2 cases (C, G1), F.2 proof names (X) | as listed in plan section 1 |

## 1a. Steps whose site file no U25 lane edits (15; every other step's files are in a lane's set)

Placed through `tools/judged.json` ("verify only" = written early in end form by its own unit, the lane reads the file
and reports the line; "nothing at U25" = the lead records the owning unit at the close).

| step | change | file | lane | verdict |
|---|---|---|---|---|
| 5 | M.SCR.009 | scripts/micropypath.toml | LEAD | nothing at U25 (born U27 with R's `digital_twin/unixport` element) |
| 7 | M.SRC_CORE.011 | src/asy_system_service.py (M text: `src/system_service.py`) | LEAD | nothing at U25 (U11/U16/U19/U20 landed it; no U25 action) |
| 8 | M.SRC_NET.028 | src/asy_udp_socket.py | G2 | no `src/` edit: the owed twin measurement of the 100 ms idle rate is M.TWIN.144's test 10 |
| 13 | M.HW_DEV.116 | tests_hardware/device_scripts/heap_headroom_after_full_system_build.py | LEAD | nothing at U25 (U26); A.U25.61 (1) reads it from P's L0 file |
| 14 | M.HW_DEV.117 | tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py | LEAD | nothing at U25 (U26) |
| 28 | M.HW_DEV.047 | tests_hardware/device_scripts/uart_crossover_recovery.py | LEAD | nothing at U25 (A.U17.25: L3/L4 gaps stay with U26) |
| 30 | M.WEB.041 | js/mock-server.js | C | verify only: A.U25.12 (7) landed at U23 (lane M, A-14) |
| 31 | M.WEB.052 | tests_js/mock-server.test.js | C | verify only: `:591-599` asserts 900 after a 900 PUT and 400 fresh |
| 36 | M.HW_BENCH.030 | tests_hardware/http_client.py | LEAD | nothing at U25 (U26, after A.U25.31) |
| 38 | M.SCR.026 | scripts/typecheck.sh | LEAD | nothing at U25 (U27's help/summary; the new L0 files join the host pass by directory) |
| 70 | M.TOOL.017 | .github/workflows/ci.yml | S | verify only: `ci.yml:618` already passes `"${{ matrix.device }}"` |
| 71 | M.TOOL.019 | .github/workflows/ci.yml | S | verify only: S measures `digital-twin-e2e` per device against `timeout-minutes: 20` (`ci.yml:606`); the re-tag is U28's |
| 73 | M.TSC.065 | tests_scripts/test_comment_block_cap.py | LEAD | nothing at U25 (U27's counting; U25's blocks obey today's cap) |
| 95 | M.TWIN.054 | digital_twin/run_device_script.py | LEAD | nothing at U25 (born U26, A.U26.05) |
| 138 | M.WEB.045 | mockdata/samples.json (M text also names the deleted `dev.json`/`wozi.json`) | C | verify only: `ForceCalRef` 400 sampled since U23; A.U23.29's parts are U23's |

Also verify-only inside lanes that own the file: M.TEST_HELP.006/.012/.013/.015/.016/.048 (U24 writes them; "confirmed
in place here"), M.TEST_HELP.061 (`tests/_boot_recorder.py`, U20), M.GEN.001 (U20), M.SPEC.126 (X: nothing due), M.SCR.063 (S: the
smoke passes no `--test-` flag; S edits the file for M.SCR.064). No step needs a file that no lane owns and no verdict covers.

## 1b. Files no step names that U25 must edit (each with its default)

| file | why | default |
|---|---|---|
| `buildgen/twin_wiring.py` | A.U25.25 (3) and M.TSC.054/.151, M.TWIN.044/.045/.114/.126 read a plan `pins` key that the producer does not write (`TwinWiringPlan` `:35-40` has `device`, `buses`, `spi`, `uart`, `instances`) | A-5: P adds `pins: dict[str, dict[str, int]]` from the `[bus.*]` tables, one `TypedDict`, emitted by `compute_twin_wiring()`; the contract test pins it |
| `tests_hardware/isl29125_conformance.py:29-33` | A.U25.25 (1) removes `configure_i2c_wiring()`, which this L3 helper's `_TWIN_ENTRY` calls (`:32`); A.U26.45 rewrites it at U26, "same commit" by A.U25.25's Depends | A-6: M replaces the one call with the equivalent `configure_wiring(json.load(...))` over the same device's generated plan (the `"dev"` literal is A.U26.45's to remove); `pytest --collect-only tests_hardware` stays clean |
| `tests/test_digital_twin_wifi_modes.py` | born at U22 (no step names it); A.U25.03/.24/.27 change what it constructs (static buses, late configure raises, WLAN singletons) | G2 adapts it to C4 and writes OF-148's two twin pins in it (A-12) |
| `tests/test_fakes.py` | M.TEST_HELP.049's contract runs on both tiers; the L1 half needs a runner | M calls `_mem_backup_contract.ALL_CHECKS` from it (U24's renamed fake test file) |
| `digital_twin/rp2.py` | `configure_wiring()` closes DMA channels today (`machine.py:345-346`); `reset_peripherals()` takes that role | M moves the close into `reset_peripherals()`; rp2.py edited only if its registry API must change |
| `tests/_bus_hazard_catalog.py` (U24 D's; shared by the unit and twin bus-hazard tiers) | A.U25.10 makes the general call reset the twin SGP40, so the catalog's general-call scenario (`:502-524` HEAD) reads a zero reply on the twin until the next measure | A-26: G1 adapts the twin side through its own adapter in `tests/test_digital_twin_bus_hazard_concurrency.py` (the driver always measures first, `asy_sgp40_driver.py`); a catalog edit, if the scenario's own assertion needs one, is reported to the lead with the line, never made silently |
| `tests_scripts/test_fake_surface_conformance.py` (U24 F, new) | C6: every twin test-only name is listed in its class's `TEST_API` (A.U24.18's twin half) | M extends the surface check to the twin fakes only if U24's check scans `tests/` alone (read at U25's start) |

## 2. Premises that no longer hold, with their conservative defaults

| action | premise now (`e14d76f`, then U24 v0) | default |
|---|---|---|
| A.U25.03 | I2C static per id landed at U13 (`_I2C_OBJECTS` `machine.py:403`, `__new__` `:430-436`), but `configure_wiring()` clears it (`:344`), which A.U25.24 forbids | A-7: `configure_wiring()` stops clearing (and refuses after construction); `reset_peripherals()` clears all three registries and closes the DMA channels; every test that relied on the clear calls `reset_peripherals()` first |
| A.U25.05 | landed at U13 (`OPEN_DRAIN`, `ALT`, `ALT_I2C`, `set_external_level()` with a callable, `value_log()`, `machine.py:157-299`); only the `invalid pin af` check is missing | M adds the check; nothing else |
| A.U25.08 | U11 landed constants, regions, `mem_backup()`, `reset_cause()`, `power_on()`, the reset cause on `reset()`/`bootloader()` (`:1291-1384`); the state-file carry and the late-call check are missing | M writes `configure_mem_backup_state_path()`/`flush_mem_backup()` and the contract file |
| A.U25.16 | U24 F changes the twin's `MSB`/`LSB` and default `firstbit` (M.TEST_HELP.016, "same commit") | M writes only the constructor's LSB refusal and its test |
| A.U25.22 | a list-ring `_BoundedLog` with `dropped` exists in `machine.py:53-103` (U13/U17); `_schedule()` already checks `len()` first (`:763`) | M moves it to `_twin_common.BoundedLog` (M.TWIN.001's name), no second copy; the overflow-flag form is not needed (A.U25.22's own "or `_schedule()` checks `len()` first") |
| A.U25.31 | `CeilingRefusedError` exists (`_http_client.py:48`) | N adds `IncompleteResponseError` and the reclassification |
| A.U25.33 | the offline config writer exists in `tests/_generated_module.py:24, 69-77` (U20, keys `NTPHost`/`DNSFallback`) | R moves it to `digital_twin/unixport/_offline_ntp_config.py` (M.TWIN.053) and `_generated_module.py` imports it |
| A.U25.36 (4) | `_failure_events()` landed at U3 (register `:148`) | S keeps it; the rest of A.U25.36 stays |
| A.U25.45 | the 13 sleeps' HTTP readiness sites all move host-side with A.U25.46; in-process only `:586` and the four SGP40-init sites remain | A-13: `tests/_twin_readiness.py` holds only helpers an in-process file calls (`wait_for_value`); the host harness polls by its own HTTP/`CONN_SLOTS` reads |
| A.U25.47 | the L1 boot-sequence scenario landed at U20 (`tests/_sensortask_scenarios.py:822`, `_boot_recorder.py`) | P writes the L2 twin scenario with the same recorder |
| A.U25.50 | `test_digital_twin_sensortask_integration.py:558` already carries "(owner, 2026-08-13: an automated assertion"; `:423` (bus hazard) and `:1027` (sensortask) carry none | G1/G2 write the two missing tags |
| A.U25.60 | the dark/mid/bright `CalLight` scenes landed at U15 (`test_digital_twin_isl29125_autorange.py:434-441`) | G1 adds the fixed-range and settling scenes |
| A.U25.68 | Pin constants, `_SPI_DMA_MIN_SIZE` and the WDT cap are cited (U13/U14); UART constants are not; no pin test exists | M cites the rest and writes the test |
| A.U25.69 | the signature and keywords stand (U20, `buildgen/codegen.py:32`); the no-autostart start line (`:832`) prints no keyword comment | P adds the one comment line |
| A.U25.73 | SGP40's walk comment cites Table 1 (U5) but lacks "not datasheet-derived"; SCD30 holds | C completes both |
| A.U25.15 | U16's `_PagedMemory` fixed the size (`_fram_chip.py:45-114`): the "buffer growth" premise is gone; rollover, framing and knobs hold | C writes rollover on the paged store |
| A.U25.48 | Run 13 is A.S0930.27's (M.SCR.060), not A.U25.48's as U23's register draft row `:42` says | A-16: the put-matrix `ACTION_PROBES` comment names "the twin suite's Run 13" once S lands it; the lead corrects the draft row's wording at U23's close |
| M.TEST_HELP.032 | the concurrency library is deleted at U25 (M.TEST_HELP.033) | its U24.65/.70 parts are void; H records them |
| OF-25 | closed at U11 | - |

## 3. Work-order and register items, resolved

- Register `:148` (U3: A.U25.36 (4) landed early): S keeps `_failure_events()` and adds `_error_codes()`/`_reset_line()`.
- Register `:214`, `:309`, `:319` (U8/U8C/U8C2 rows removed or not written until U25): every row the host rewrite needs
  is written by H as `@tunable` tags in `scripts/_digital_twin_scenarios.py`; their Part N rows are X's (facts relayed);
  the 13 `l2.webserver_concurrency_scenarios_*` rows are not revived for a deleted file.
- Register `:370` (OF-42): M (`tests/test_digital_twin_machine_uart.py`, the frame-level FE/BE case).
- Register `:413`, `:432` (fakes clauses; F.7 pointer comments for the shim, prewarm and concurrency files): R writes
  the shim's and prewarm's one-line F.7 pointers; the concurrency file is deleted (H).
- Register `:448` (BMP3XX EVENT bit as a stand-in for `power_cycle()`): C's `power_cycle()` replaces the stand-in.
- Register `:476` (U15 step 190 "rest U25"): U15's step 190 is read from `u15/pk/` by the owning lane; its U25 part is in
  this packet's steps (M.TWIN.122 rebases U15's cases on C4, G1).
- Register `:524` (U18 wrote the run-7 sentence and the shim comment early): W and R keep them, verified.
- Register `:544` (U20 A-14: twin test names renamed at U25): the renames are G1/G2's (`test_wozi_*` → device-generic);
  the lead re-keys `test_import_placement.py`'s pending rows and later citations.
- Register `:623` (SF-B13, folded into M.TWIN.011/.013 part 1): C.
- U23 register draft `:14` (A.U25.12 (7) landed): C verifies; `:35` (OF-148): G2; `:42`/`:43` (Run 13; the
  `ACTION_PROBES` comment): S (A-16).
- Work order `hardware_rounds` R1-R3 (H16, H29, H30, H46, H73): phase C rounds that exercise U25's changes; nothing at
  U25 (no real hardware); the fidelity table's assumption rows name them (BACKLOG, Y).

## 4. Questions that might need the owner

None. Every gap above has a conservative default (plan section 5). Agent rulings for the owner's review at the close:
A-2 (the cut), A-5 (`pins`), A-6 (the L3 helper's one-line edit), A-7 (configure after construction), A-8 (lane twin
runs), A-9 (the harness invocation in `run_digital_twin_ci.sh` before U27), A-11 (`PER_DEVICE` twin files), A-12
(OF-148's home), A-13 (`_twin_readiness.py` scope), A-14 (twin-tier time stop rules), A-15 (the grkizi reproduction run by
the lead), A-19 (OF-116's form), A-20 (OF-112's twin half), A-21 (OF-67), A-22 (OF-74), A-23 (OF-108), A-25 (OF-19), A-26 (the shared catalog).
