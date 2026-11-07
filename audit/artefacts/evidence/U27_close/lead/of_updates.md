# U27 close: open_findings.md updates and new rows (draft)

Base: `git show 7f34f35:audit/sweeps/open_findings.md` (W2 `6b953ae` plus lane E `58a8de5`; `git diff 0c0ad52 7f34f35 --
audit/` is empty, so the rows are U26's). 28 rows name U27: 25 target it (OF-60, 70, 89, 114, 118, 124, 126, 144, 147, 150,
151, 153, 154, 155, 157, 158, 162, 163, 164, 165, 166, 168, 181, 182, 186) and three name a U27 part (OF-125, OF-141 U28;
OF-183 C), as plan §6 lists. Every site below was read at `7f34f35` through git (lane E changed only
`tests_scripts/test_hardware_runners.py` and `test_stripped_image_boots.py`, which no row cites); `<FINAL>` is the unit's
squash, the lane commit is in the evidence line. Only the target cell (where it moves) and the state cell change; site,
class and from cells stay as at `7f34f35`. A moved row's unit follows the fallback rule (agent, 2026-10-15, the lead's
ruling at U27's close): the next unit whose `audit/order/work_order.json` file list holds the file; if none, U35 (the B3
test campaign) for a test file and U37 (the B5 close of execution) for any other.

Counts: 18 closed (89, 114, 118, 124, 126, 147, 153, 154, 155, 157, 158, 162, 163, 164, 165, 166, 168, 182); 4 partly
closed and moved (60 and 70 to C; 144 to U35; 151's ISL29125 half to U28); 3 moved with nothing landed (150 to U35, 181 to
C and U30, 186 to the owner-review list); 3 keep their target with U27's part landed or re-pointed (125, 141 U28; 183 C).
New: 12 rows, OF-191 to OF-202 (highest at `7f34f35`: OF-190).

## Rows routed to U27

### OF-60 - partly closed, moved (C)
- target: `C (round R2, item H17: the FRAM-pull latency read on silicon through the manual step U27 wrote; the read-path probe option stays with src/asy_fram_manager.py's next unit, U30; agent, 2026-10-15)`
- state: `open (the step written at U27, <FINAL>): the manual FRAM pull now waits for Enter at the pull, polls GET /status once a second and records the seconds to the first FRAM log entry, "none within 120 s" when none, as evidence fram-pull-latency.txt (tests_hardware/manual/manual_bus_electrical.py:117-126, the watch l4.manual_bus_electrical_fram_detect_watch_s :27-28, estimated, measurement owed in R2); pinned by tests_scripts/test_manual_runner_summary.py:212; no figure exists until R2 runs it`
- evidence: lane T `8c8a65d` (W1 merge `34a9924`); relay T :20; T's hand-back block 5.

### OF-70 - partly closed, moved (C)
- target: `C (round R2, item H37: the pulled crossover line on silicon through the manual step U27 wrote; the driver-side cause string, if the bench shows the causes need telling apart, stays src/asy_uart_comm.py's next unit, U28 (R-23); agent, 2026-10-15)`
- state: `open (the stalled-TX half done at U26, the pulled-line step written at U27, <FINAL>): uart_crossover_pull_recovery records the seconds to the link's first failed transfer, every code logged while the wires are off (a ring that dropped some counted "+N past the ring") and the seconds until Transfers resume, as evidence uart-crossover-pull.txt with the verbatim errcount (tests_hardware/manual/manual_bus_electrical.py:138-168); it fails on a reboot, no failed transfer, no resumption within 30 s or a device with no UARTLINK entry; pinned by tests_scripts/test_manual_runner_summary.py:219, :228, :238, :245`
- evidence: lane T `8c8a65d`; relay T :20.

### OF-89 - closed
- state: `closed at U27 (<FINAL>): the comment states the measured tier, "Its 1200 s is a hang backstop over the tier's measured 698 s (2026-10-15, either GC stage, beside the MicroPython tier; CI's figure: Part N, runner.tests_scripts_timeout_s)" (scripts/test.sh:337-339); the bound stays 1200 s (R-12); Part N's row states the basis, 1.7x the 698 s tier, with CI's 424 s and the bench Pi4's figure owed (SPECIFICATION.md:11810) (lanes T, X)`
- evidence: T `8c8a65d`, X `b483a40`. The 698 s is U26's gate2 tier (plan §9). The bench Pi4 figure is parked in R0 (`draft_parked.md`, agent, 2026-10-15); CI's figure on U27's push: GATE-TBD.

### OF-114 - closed
- state: `closed at U27 (<FINAL>): the shutdown line carries wdt_timeout_ms (digital_twin/run_generic_integration.py:418) and scripts/_twin_process.py's feed_gap_verdict() fails a largest feed gap above l2.feed_gap_share_max = 0.75 of the armed timeout (:39-40, :204-208), applied to every suite run (scripts/_digital_twin_ci_suite.py:401-403) and harness boot (scripts/_digital_twin_scenarios.py:282) except the runs that starve the watchdog by design; pinned by tests_scripts/test_digital_twin_ci_suite_errcount.py:570, :579 and tests_scripts/test_digital_twin_scenarios.py:206 (lane S)`
- evidence: lane S `c8c44e4` (W1 merge `afe12e2`); seen failing first (S's hand-back; `S/u27/laneS/sff.txt`: no `feed_gap_verdict`, no `starves_watchdog`).

### OF-118 - closed
- state: `closed at U27 (<FINAL>): the scripts/, toolchain/ and tests_scripts/ part: 707 sites in 90 files gained encoding="utf-8" and nothing else (each file's AST the old one plus the keyword); tests_scripts/test_host_text_encoding.py walks every tracked *.py of the three scopes and fails naming file:line on a text-mode open()/Path.open()/io.open(), read_text() or write_text() without encoding=, asserting its scan is not empty (195 files, 1263 calls, 0 without encoding at 14fe1ca); the tests_hardware/ part closed at U26; subprocess text streams stay out of scope, as in ruff's PLW1514 (R-13); the guard's blind spots are OF-197 (lane M)`
- evidence: lane M `14fe1ca` (W2 merge `febcadf`); the lead's AST check (`S/u27/close/ast_check.py`: 90 modified .py, 707 keywords, no other AST change). A read-only AST walk at `7f34f35` with the guard's rules finds 0 sites in `buildgen/` and the host modules of `tests_hardware/`, 13 in `digital_twin/` (MicroPython, UTF-8, out of the row's scope).

### OF-124 - closed
- state: `closed at U27 (<FINAL>): unix_port_ensure reruns setup when a recorded input_sha256 is missing or differs from this tree's toolchain/versions.toml, setup_toolchain.py or micropython_overrides.py (scripts/_unix_port.sh:8-9, :110-133, :221-240), and fails naming the input still stale after its one setup (:265); test.sh (:194-206) and both twin runners (scripts/run_digital_twin_ci.sh:73, scripts/run_unix_port_integration.sh:75) call it; pinned by tests_scripts/test_unix_port_sh.py:236, :260, :265, :276; a check-only caller trusts the record (OF-193) (lane T)`
- evidence: lane T T1 `cc6f671` (API `89b37a0`) and `8c8a65d`.

### OF-125 - target unchanged (U28), U27's part landed
- state: `open (the stub pins landed at U27, <FINAL>): typecheck.sh installs exactly toolchain/versions.toml's [stubs] board = "1.29.0.post1" and stdlib = "1.29.0.post2" (versions.toml:15-17; scripts/typecheck.sh:50-98), each checked against [micropython] ref; the stub install and the uv runs still have no bound of their own (U28's budgets)`
- evidence: lane B `f4f6a49`.

### OF-126 - closed
- state: `closed at U27 (<FINAL>): a run holds <toolchain>/.toolchain.lock shared and non-blocking for the calling shell's life (scripts/_unix_port.sh:53-63), the pytest tier for its session (tests_scripts/conftest.py:56-69); setup takes it exclusive (toolchain/setup_toolchain.py:1778-1785) and refuses at once naming a shared holder (:1796-1805); pinned by tests_scripts/test_unix_port_sh.py:334, :346 (lanes T, B)`
- evidence: T1 `cc6f671`, T `8c8a65d`, B `f4f6a49`; R-15. The lock contention with a whole-tier firmware build is OF-195.

### OF-141 - target unchanged (U28), U27's part landed
- state: `open (the wipe landed at U27, <FINAL>): --stage-only removes every staged page directory under its root at the start of the run (scripts/build_device_websites.sh:49-56), pinned by tests_scripts/test_build_device_websites_sh.py:99-101; lint:html:built's glob is A.U28.43's; how the wipe tells a staged page is OF-201`
- evidence: lane B `f4f6a49`.

### OF-144 - partly closed, moved (U35)
- target: `U35 (the page's comparison: js/shell.js's next unit; R-12, agent, 2026-10-15)`
- state: `open (the build-chain half closed at U27, <FINAL>): build_firmware.py takes one current_build_date() (scripts/build_firmware.py:254) into the generated module and build_website.sh --build-date (:111-117, :273), and the stager stamps it into the page as <meta name="build-date"> (scripts/_stage_website.py:474-476, :498-499); pinned by tests_scripts/test_build_firmware.py:79-82, test_stage_website.py:222, :235, test_build_website_sh.py:164; js/shell.js reads no build date yet`
- evidence: lane B `f4f6a49`; `git grep build-date 7f34f35 -- js` is empty.

### OF-147 - closed
- state: `closed at U27 (<FINAL>): the live commands start python3 directly for buildgen's ceiling and the evidence archive (tests_js/_live_twin_command.js:235, tests_js/_live_matrix_command.js:159), and the frame asks scripts/_unix_port.sh check standard once (tests_js/_twin_process.js:102): no uv run in the live tier, so no .venv or script environment lands in a worktree (lane S)`
- evidence: lane S `c8c44e4` (S's hand-back: the OF-147 grep went from 2 hits to 0). The web jobs now need python3 >= 3.11 on PATH (relay S :162, a U28 CI line).

### OF-150 - moved (U35), nothing written
- target: `U35 (the fallback rule: no later unit's work-order file list holds tests/test_voc_algorithm.py, a test file; measured at U27, R-12; agent, 2026-10-15)`
- state: `open (measured at U27): the time at 32768 is the product's allocation volume times the harness heap's sweep, not the file's pattern or imports: 389 MB allocated at either stage (313 MB the 20,000 vocalgorithm_process() calls), about 11,900 threshold collections at 32768 against about 25 heap-full ones at -1, about 1.24 ms each, the cost tracking the heap (0.31 ms at 4 MB, 0.86 ms at 16 MB, py/gc.c:719 gc_last_used_block, v1.29.0); 5.06/31.67 s at -1/32768 at U27 (base 3.85/27.75 s); the file changed only by its header`
- evidence: relay U :45, lane U `494cb74` (`S/u27/laneU/of150_measure.log`); R-12: "move the row on with the numbers".

### OF-151 - partly closed, moved (U28)
- target: `U28 (the ISL29125 sweep, tests/test_asy_isl29125_driver.py's next unit; the BMP3xx and SCD30 halves closed at U27; agent, 2026-10-15)`
- state: `open (BMP3xx and SCD30 closed at U27, <FINAL>): both sweeps let only the bus layer's OSError pass (tests/test_asy_bmp3xx_driver.py:2417, tests/test_asy_scd30_driver.py:2245), and the SCD30 sweep hands each call the replies it reads; the ISL29125 sweep still swallows every exception (tests/test_asy_isl29125_driver.py:4059)`
- evidence: lane U `494cb74`; a planted early raise bit both (U's hand-back).

### OF-153 - closed
- state: `closed at U27 (<FINAL>): typed readers src_bytes(), src_float(), src_int(), src_strs() (tests/_src_const.py:54, :83, :91, :98) and src_schema() (tests/_src_schema.py), each raising TypeError on a value of another type, pinned by tests/test_shared_helpers.py:91; no src_const() read carries a type: ignore in tests/, digital_twin/, tests_hardware/ or tests_scripts/ (0 at 7f34f35) (lane U; lead)`
- evidence: U `494cb74` (106 ignores and 7 isinstance-narrowed reads); the lead's W1 `e7fe9c7` (six reads outside every set; `src_schema()` moved to its own module since the host pass reaches `tests/_src_const.py` through `tests_hardware/bench/_load.py`). `tests/_sensortask_scenarios.py:2190` keeps its assert (no str reader).

### OF-154 - closed
- state: `closed at U27 (<FINAL>): the parse cache keys on the text alone, a SyntaxError never cached (buildgen/source_ast.py:9-19), and each file's imports are cached by its text (buildgen/frozen_modules.py:49-50); pinned by tests_scripts/test_buildgen_source_ast.py:16, :32, :41; test_buildgen_error_contract.py 46.35 s to 20.2 s alone (lane B)`
- evidence: lane B `f4f6a49`; the source-ast test diff applied by the lead at W1 (`e7fe9c7`).

### OF-155 - closed
- state: `closed at U27 (<FINAL>): the boot-entry harness re-raises any interrupt its stub did not plant (tests/test_generated_boot_entry.py:67-68, case :138), and both _raised() helpers re-raise KeyboardInterrupt first (tests/test_digital_twin_unix_port_unretrieved_report.py:114-120, case :222; tests/test_asy_system_service.py:3651-3656, case :3865), each seen failing first; microtest's drain was already pinned (tests_scripts/test_microtest.py:155) (lane U)`
- evidence: lane U `494cb74` (`S/u27/laneU/sff_of155_red.log`).

### OF-157 - closed
- state: `closed at U27 (<FINAL>): machine.Timer.drop_next_soft_callbacks (digital_twin/machine.py:1360-1363, :1413-1415, cleared by reset_test_state() :1748) drops the next N soft callbacks as rp2's full depth-8 queue does: a PERIODIC alarm re-arms, a ONE_SHOT is lost and frees its alarm, a hard callback is never dropped; off by default, reached only by a test (R-25); pinned by tests/test_digital_twin_machine.py:1417, :1436, :1193; the fidelity row is digital_twin/README.md:233, and SPECIFICATION.md F.7 row 17 names it (the lead's close edit) (lanes S, X; lead)`
- evidence: lane S `c8c44e4`; X `b483a40`; F.7 row 17 (`SPECIFICATION.md:6554`) edited by the lead at the close (`draft_lead_edits.md`). No scenario uses the knob on a product timer: OF-198.

### OF-158 - closed
- state: `closed at U27 (<FINAL>): the 35 module-level helper functions sit in one sorted block (tests/test_asy_ntp_client.py:121-480) before the tests (:499 on), a pure reorder checked by AST (lane U)`
- evidence: lane U `494cb74`; read at `7f34f35` (sorted on the name without its underscore: true).

### OF-162 - closed
- state: `closed at U27 (<FINAL>): Run 11's warm-up ends once no cycle has set a new MEM_SAMPLE floor for l2.soak_plateau_cycles = 20 cycles, l2.soak_warmup_cycles = 100 kept as the bound (scripts/_digital_twin_ci_suite.py:198-203, :1531-1546); on dev 84 and 63 cycles, about 70 s saved per stage (lane S)`
- evidence: lane S `c8c44e4`; relay S :156, :163.

### OF-163 - closed
- state: `closed at U27 (<FINAL>): Run 9 ends on the third NTP failure event, l2.ntp_unreachable_failures = 3, then one supervisor pass, l2.ntp_unreachable_watch_s = 90 kept as the bound (scripts/_digital_twin_ci_suite.py:128-133, :1412-1414); measured on dev: failures at about 4, 22.5 and 62.4 s, the 10 s doubling backoff making the old five-failure streak unreachable in 90 s; Run 9 75/76 s per stage (lane S)`
- evidence: lane S `c8c44e4` (S's deviation (c)).

### OF-164 - closed
- state: `closed at U27 (<FINAL>): each Run 10 hang run ends on the runner's WATCHDOG_WOULD_TRIGGER line, l2.hang_run_exit_wait_s = 45 bounding it, --duration 15 kept for a hang that fires late (scripts/_digital_twin_ci_suite.py:231, :758-765) (lane S)`
- evidence: lane S `c8c44e4`; Run 10 149.8 s for both stages against about 77 s per stage (relay S :163: about 2 s saved, each hang's line comes late).

### OF-165 - closed
- state: `closed at U27 (<FINAL>): the runner prints HUNG S1 when the rebound dead-task report is first entered (digital_twin/run_generic_integration.py:530) and S1's wait ends on it, the old 12 s kept as the bound (scripts/_digital_twin_scenarios.py:862-863) (lane S)`
- evidence: lane S `c8c44e4`; the hung-step scenario 99.6/111.5 s (S's hand-back).

### OF-166 - closed
- state: `closed at U27 (<FINAL>): the runner takes --test-flash-stall-max and --test-uart-over-cap (digital_twin/run_generic_integration.py:229-230, :360-362) and its shutdown line carries gc_block_bytes after a mem_info() GC summary (:381, :418-420); uart_ring_under_concurrent_load runs a typical and a maximum stall round, offers one over-cap train per initiator and expects it refused and logged once, and reads the largest free block, asserted at the threshold stage only (scripts/_digital_twin_scenarios.py:1604-1631) (lane S)`
- evidence: lane S `c8c44e4`. The -1 stage prints the block (11,872-30,080 B largest of about 870 KB free) and asserts nothing on it (S's deviation (b), agent, 2026-10-15; review list); the silicon reading is parked (`draft_parked.md`).

### OF-168 - closed
- state: `closed at U27 as measured (<FINAL>, no change): every booted case already ends on its event (a getter or a log count, 50 ms polls); the 34-35 s per stage are product waits: each 5 s fetch timeout of a silent responder (6.3 s from boot, twice), 1.3 s per boot to the first sync, 2.6-3.1 s to the first sensor readings, 1.7 s per read cycle (agent, 2026-10-15) (lane U)`
- evidence: relay U :45; `S/u27/laneU/of168_waits.log`. The file changed only by its header (`git diff 0c0ad52 7f34f35`).

### OF-181 - moved, nothing written
- target: `C (round R1: measured SGP40 raw steps from the flash tier's VOC script; then digital_twin/_sgp40_chip.py's next unit, U30, for a walk drawn from them; R-12, agent, 2026-10-15)`
- state: `open: the walk unchanged at U27 because the datasheet bounds no per-sample step: it gives the raw signal's sensitivity only, -870 ticks per doubling of VOC concentration (typical; -710 to -1030 for 5 to 10 ppm ethanol), datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf Table 1; the "frozen" assertion kept (tests_hardware/flash/test_sensor_accuracy.py:153); the R1 run of test_sgp40_voc_algorithm_produces_plausible_and_stable_results (:144, script sgp40_voc_algorithm_quality.py) reports raw ticks per sample (lane S)`
- evidence: S's hand-back step 6 ("the SGP40 walk is unchanged because the datasheet gives only −870 ticks per doubling and no per-sample step (R-12, measurement parked to R1)"); Table 1 read in the scratch text of that PDF; `git diff 0c0ad52 7f34f35 -- digital_twin/_sgp40_chip.py` is empty.

### OF-182 - closed
- state: `closed at U27 (<FINAL>): env --tier bench probes the spoof's own sudo call, sudo -k -n <venv python> tests_hardware/spoof_udp.py --help, root passing as it is, and fails naming the missing rule (toolchain/setup_toolchain.py:758-767, called :1558); pinned by tests_scripts/test_setup_toolchain_env.py:353, :364; the bench host's own run is R0 H57 (lane B)`
- evidence: lane B `f4f6a49`.

### OF-183 - target unchanged (C), the setup half re-pointed
- target: `C (round R1, the network-resilience run settles delivery); a fix, if it does not deliver, in the bench host's setup (toolchain/setup_toolchain.py, U28, its next unit after U27) or the redirect (tests_hardware/bench_control.py, U36)`
- state: `open: parked hardware item; no code at U27 (R-12)`

### OF-186 - moved (owner review)
- target: `owner review (R-5, agent, 2026-10-15: the exempt tags are CLAUDE.md's list, which grows only on the owner's word; on the owner-review list only, as OF-16)`
- state: `open: _TAGS still leaves @include out (tests_scripts/test_comment_block_cap.py:26-27), so each tag line now leaves the count line by line while an include line counts; until answered, includes sit in groups of at most three`
- evidence: lane U `494cb74` (the counting change, R-4/R-5); no BACKLOG.md question (the lead's ruling, OF-16's precedent).

## New rows (OF-191 to OF-202)

Appended after OF-190 in the file's own format. Sources: the T, B and S hand-backs (`S/u27/close/handbacks_TBS.md`), relay T
:21-:23, :30, :31; lead_todo "REVIEW/OF candidates" and its W2 notes; X's close items; M's "not covered" list; two reads of
the code at this close (OF-201, OF-202). Every site read at `7f34f35`; targets by the fallback rule above.

| # | site | class / mode | from | target | state |
|---|---|---|---|---|---|
| OF-191 | `scripts/_unix_port.sh:99`, `:275`: the probe runs the binary (`"$1" -c "$_UNIX_PORT_PROBE"`) with no time bound, so a binary that hangs at start hangs `scripts/test.sh` (`:198`, `:203`), both twin runners (`scripts/run_digital_twin_ci.sh:73`, `scripts/run_unix_port_integration.sh:75`) and the live JS frame (`tests_js/_twin_process.js:102`, `execFileSync` with no `timeout`) until CI's job limit; the pytest tier and the twin board bound their call at 60 s (`tests_scripts/conftest.py:41`, `tests_hardware/twin_board.py:25`, `:46`); SPECIFICATION.md E.5.2 states the gap (`:4927`) | 5 / a Unix-port binary that hangs at start (every runner) | U27 lane T scan (relay :21 (3)), lane X close item | U28 (the next unit holding `scripts/_unix_port.sh`; agent, 2026-10-15) | open: a `timeout -s KILL` around the probe with a `@tunable runner.unix_port_probe_timeout_s` (about 10 s, lane T's suggestion) and its Part N row, a timeout read as `unusable`; not taken at U27 (the lead's ruling: a new bound is a tunable decision, review list) |
| OF-192 | `scripts/test.sh:411-414`: each `scenarios[<device>]` job takes `runner.scenarios_timeout_s` = 1980 s per attempt over `runner.per_file_attempts` = 3 (5,940 s), beside the unit files, inside `unit-tests`/`unit-tests-gc-threshold`'s `timeout-minutes: 45` (`.github/workflows/ci.yml:463`, `:501`), so one hung scenario job has CI cancel the job before the summary block prints; Part N says so (SPECIFICATION.md:11809) | 5, 6 / a hung scenario job in CI's unit-test jobs | U27 lane T (relay :22), lane X close item | U28 (M.TOOL.019's re-measure; R-16: no lane raises a bound; agent, 2026-10-15) | open: from U27's first CI run (GATE-TBD), re-check the job's timeout against the per-device job count, or the override against CI's measured harness time (the 1980 s is 5x one standalone dev run, 396 s, a single observation) |
| OF-193 | `scripts/_unix_port.sh` `check` judges the build flavour only, the record and input hashes being `ensure`'s: the live JS frame and the smoke (`tests_js/_twin_process.js:102`), the pytest tier (`tests_scripts/conftest.py:60`) and the twin board (`tests_hardware/twin_board.py:64`) run whatever binary the record names when no `ensure` ran before them (a local `npm test` or pytest after an override edit), so stale Unix binaries pass | 3 / a stale toolchain record under the live JS tier, the smoke or a standalone pytest run | U27 lane S scan (3), lane T scan (relay :30) | U28 (CI's four build-if-missing steps become `scripts/_unix_port.sh ensure standard`, relay T :13, :26; agent, 2026-10-15) | open: CI is covered by its cache key (the three inputs, `.github/actions/setup-micropython-toolchain/action.yml:39`); locally the frame could call `ensure` once, or `check` could also compare the record (a rebuild then fails rather than runs stale) |
| OF-194 | `scripts/build_firmware.py:323`: `main()` turns `BuildError`, `StripError`, `SetupError`, `OverrideError` and `CalledProcessError` into one line, but an `OSError` from `write_image()` (`:194-200`, called `:310`), e.g. an unwritable `--output`, leaves as a traceback, against SPECIFICATION.md L.5's one-line user error | 4 / an unwritable firmware output path | U27 lane B scan ("left as is") | U28 (the next unit holding `scripts/build_firmware.py`; agent, 2026-10-15) | open: report an output path that cannot be written as a user error naming it (the image is never paired with an old record either way, SF-M4-07) |
| OF-195 | `tests_scripts/conftest.py:56-69` `micropython_bin` holds the toolchain lock shared for the whole pytest session, so a session that requests it and also runs the real firmware build (`RUN_SLOW_FIRMWARE_BUILD=1` over the whole tier, `tests_scripts/test_build_firmware.py:694`) has `build_firmware.py`'s exclusive lock refused (`scripts/build_firmware.py:259`; `toolchain/setup_toolchain.py:1796-1805`) | 6 / one local pytest session holding the toolchain lock and building firmware | U27 lane T (relay :23) | U28 (the next unit holding `scripts/build_firmware.py`; agent, 2026-10-15) | open: CI selects that test alone (`.github/workflows/ci.yml:693`), so CI is unaffected; locally the refusal names the holder; a fix keeps the slow build out of a session that holds the lock, or names the opt-in's limit in its skip reason |
| OF-196 | `scripts/_check_gc_collect_sites.py:96-109`, `:137-142`: with no `devices/*.toml` (or only `zz_test_` ones) the generated-module check reads nothing and the run passes, printing "generated modules checked: 0" | 3 / a check that matches nothing | U27 lane B scan ("left as is") | U30 (the next unit holding the checker; agent, 2026-10-15) | open: count zero generated modules as an error (exit 2), as an empty `src/` already is (`:116-117`) |
| OF-197 | `tests_scripts/test_host_text_encoding.py` (OF-118's guard): it walks only `scripts/`, `toolchain/`, `tests_scripts/` (`SCOPES`), so `buildgen/` and the host modules of `tests_hardware/` (clean at `7f34f35`) are unguarded; `encoding=None` or a variable passes (one: `tests_scripts/test_buildgen_error_contract.py:594`, a fake forwarding its caller's encoding); `tempfile` text mode, `io.TextIOWrapper`, `os.fdopen`, `codecs.open`, `gzip`/`bz2`/`lzma` `"t"` mode, `argparse.FileType` and an aliased `open` are not matched (none today); an untracked file is read only after `git add`; 154 `subprocess` calls with `text=True` and no `encoding=` in 68 files decode by the locale (out of scope by R-13, as PLW1514) | 4 / a non-UTF-8 locale | U27 lane M ("not covered"); the close draft's AST read (scopes) | U35 (the fallback rule: no later unit holds the guard, a test file; agent, 2026-10-15) | open: widen `SCOPES` to `buildgen/` and `tests_hardware/`'s host modules (both clean now, so it lands green), match a non-literal `encoding=`; `subprocess` stays out unless the owner widens R-13 |
| OF-198 | `src/asy_system_service.py:327` (the reset timer), `:701` (the boot sequencer), `src/asy_ntp_client.py:282` (the sync retry): each ONE_SHOT soft Timer's fire is lost on rp2 when the depth-8 scheduler queue is full, and no twin scenario sets `Timer.drop_next_soft_callbacks` against one, so what each loses (a commanded reset that never comes, a stalled sequencer, one retry) is shown nowhere above L1 | 5 / twin fidelity, a dropped ONE_SHOT fire | U27 lane S scan (2) | U31 (the next unit holding `scripts/_digital_twin_scenarios.py`, through A-C as a delta: no work-order step names it; agent, 2026-10-15) | open: one harness scenario per site, the knob set before its arm, the product's recovery (or its documented loss) asserted; the NTP comment states its loss (`src/asy_ntp_client.py:279`) |
| OF-199 | D.15 helper order not applied to six files whose helpers sat among the tests before U27: `tests_scripts/test_test_sh.py`, `test_digital_twin_boot_contiguity.py`, `test_port_lock.py`, `test_coverage_runner.py`, `test_tool_help.py`, `scripts/_archive_evidence.py` (lane T added members but did not reorder: the files could not be rerun after it on the faulted host) | 3 / convention (D.15) | U27 lane T (relay :31; T's hand-back) | U28 (`test_test_sh.py`), U36 (`test_digital_twin_boot_contiguity.py`, `test_coverage_runner.py`), U35 (`test_port_lock.py`, `test_tool_help.py`: no later unit holds them, test files), U37 (`scripts/_archive_evidence.py`: no later unit holds it); the fallback rule, agent, 2026-10-15 | open: D.15 order as each unit's last edit to the file, a pure reorder checked by AST |
| OF-200 | `tests/test_sensortask.py`, one job per device: 38/54 s (wozi) and 53/79 s (dev) at -1/32768 on the W1 tree, above R-17's 10 s bar; no U27 lane grew it, so it has no U27 base (Part N `runner.per_file_timeout_s` cites dev at 56/82 s, 2026-10-13) | 3 / test duration | U27 lead (W2 timing note) | U35 (the fallback rule: no later unit holds it, a test file; agent, 2026-10-15) | open: profile one device's job at 32768 (as OF-150's numbers did) before any change |
| OF-201 | `scripts/build_device_websites.sh:49-56` (`--stage-only`): the start-of-run wipe tells a staged page by one file, removing every subdirectory of the root that holds an `index.html` with all its contents (`rm -rf "$(dirname "$page")"`), while its comment says the root "may be any directory the caller names"; the test plants only a page-shaped directory (`tests_scripts/test_build_device_websites_sh.py:61-63`, `:99-101`), so no case shows a foreign directory surviving | 3 / a re-run over a caller-named root | the close draft's read of OF-141's fix (lane B `f4f6a49`) | U36 (the next unit holding the script; agent, 2026-10-15) | open: remove only what the stager writes (`index.html`, `js/app.js`, then the directory if empty), or tell a staged page by a marker the stager writes; the default root `build/staged_html` holds only staged pages, so no run of the repo's own commands has lost a file |
| OF-202 | `scripts/_check_gc_collect_sites.py:125-126`: an allowance row whose file no longer exists is skipped without a finding (`present` keeps only rows whose file is there), though the header promises exit 1 for "an allowed row with no site" (`:11-12`); a renamed function's row is reported (`tests_scripts/test_gc_collect_sites.py:64`), a deleted file's is not | 3 / a stale allowance row | the close draft's read | U30 (the next unit holding the checker; agent, 2026-10-15) | open: report a row whose file is gone as stale ("remove its row"), as a renamed function's already is; a renamed file's calls are still reported as outside the table, so no unallowed collect passes today |

## Candidates checked and not raised

- The three `devices/*.toml` globbers without the `zz_test_` skip (lead_todo 10:5x): at `7f34f35`, `tests_hardware/harness.py`'s
  bench scan skips them (`:433-435`); `tests_js/site-functions.test.js:16` indexes `TOML_FILES` only by `DEVICE_IDS`
  (`:106-108`), which `tests_js/_generated_definitions.js:44-46` builds without `zz_test_` stems; only
  `tests_hardware/website_identity.py:58` (`foreign_device_ids()`) keeps a leaked fixture's stem, which only adds an id the
  intruder check (`:45`) cannot find in a real page. Checked, not raised; no row for `website_identity.py` (the lead's
  ruling, 2026-10-15).
- `tests/test_digital_twin_machine.py` `_wire()` and `tests/test_digital_twin_run_generic_integration.py:215` name `wozi`: both
  files are rows of `_NOT_YET_CLEANED` (`tests_scripts/test_no_variant_literals.py`), next unit U36; tracked, not a new row.
- U26's review `:116` (a streaming run API as the hang tests' reversal): a reversal option with no M entry (gaps §5), not
  written; not a finding.
