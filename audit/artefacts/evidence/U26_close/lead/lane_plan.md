# U26 (HW: the real-hardware levels L3 flash and L4 bench, `tests_hardware/`) lane plan (sites at `a8dc1a1`)

**One pass (agent, 2026-10-14)**: plan, cut and briefs from the audit tree at `a8dc1a1` (U25's code tree: every U25 code
lane merged, branch `audit/u25-w2`), read only through git. U25 is still closing (a docs lane edits SPECIFICATION.md,
CLAUDE.md, README.md, BACKLOG.md, digital_twin/README.md; gate fixes may follow), so every site below is quoted text plus
`file:line` at `a8dc1a1`; the lead re-locates against U25's final (`<U25>`) before launch with the `S/u25/tools/relocate.py`
model (`RELOCATE_TARGET=<U25>`, file list from `git diff --stat a8dc1a1 <U25> -- ':!audit' ':!arduino'`). Rulings: `briefs/rulings.md`
(R-1..R-26). Placeholders kept literal: `<U25>` (the U26 base), `<API>` (`audit/u26-api1`), `<W1>`, `<W2>`, `<W3>`, `<BASE>`
(U25's close gate logs, the timing base the lead names at launch).

## 0. Sources and tools

`audit/actions/U26.md` (A.U26.01-.87, written at HEAD `f4298dd`; Ledger, Register fixes, Open points, Closing inventory),
`audit/order/work_order.json` (U26), the M entries its steps name (`audit/consolidation/M_*.md`), `audit/REGISTER.md` rows
naming U26 (`:52`, `:124`, `:125`, `:127`, `:140`, `:171`, `:214`, `:305`, `:315`, `:322`, `:327`, `:341`, `:395`, `:412`,
`:442`, `:473`, `:476`, `:486`, `:541`, `:726`, `:734`, `:736`, `:740`), `audit/sweeps/open_findings.md` (rows targeting
U26; OF-145/146 stay U30's), U25's relay (`S/u25/relay_w1.md`) and its docs-lane facts (R-25). Models: U25's plan, gaps,
packets, tools and briefs; command forms `S/u24/briefs/common.md` "Runs" (`:49-80`) and "Before every commit" (`:93-103`),
cited, never copied. Binding reading for every agent: `S/CHECKLIST.md`, `S/u21/CONCURRENCY.md` (rule 13 above all).

Tools (`S/u26/tools/`, each `python3 -I <tool>`): `root_a8dc1a1/` (git archive of `audit/` at `a8dc1a1`, never evidence);
`step_packet.py` (the audit tool, ROOT on that copy; lists the one open register delta instead of refusing); `steps.py`
→ `u26_steps.json`, `all_acts.txt`; `index.py` → `changes_index.txt`; `act_index.py` → `acts_index.txt`; `lanes.py` (the
sets, writes `../files_<L>.txt`, checks every pair disjoint); `place.py` + `judged.json` → `step_places.json`,
`lane_sets.txt`; `checks.py` + `checks_judged.json` → `checks.json` (seen-failing-first per change); `extract.py` →
`pk/packet_lane<L>.md`; `rounds.py` → `rounds.json`, `h_map.json`; `sizes.py` → `sizes.txt`; `table.py` → `step_table.md`
(§9); `show.py <ID>` prints any M entry or action. The full step packet is `pk/U26_steps.md` (1.4 MB).

## 1. Counted against the work order

- **Steps**: 325 changes in 250 numbered steps (311 explicit + 14 implicit), three co-landing groups: step 48 (73 changes,
  "the U26 bench rewrite": one squash lands it, each lane applies its own members), step 94 (M.HW_BENCH.093 E, M.HW_DEV.045
  and .052 D2), step 201 (M.HW_BENCH.121/.122, both X). Every change is placed (`step_places.json`, no unplaced): A 65 changes
  in 49 steps, B 56/41, D1 62/49, D2 61/43, E 41/28, X 50/49, lead 17/13 (a change held by several lanes counts in each:
  15 changes are a convention each lane applies in its own files, e.g. M.HW_DEV.001-.012, M.TSC.002; gaps.md §3).
- **Actions**: the work order's `actions` field and the union of the steps' `carries` are both **161** (87 A.U26, 35
  A.U8C, 11 A.S0930, 5 A.U25, 3 each A.U11/U16/U20, 2 each A.U24/U6/U7, 1 each A.U10/U13/U14/U15/U17/U18/U19/U8). The brief's
  162 matches no field at `a8dc1a1` (lead: check the count it came from). All 87 A.U26 actions are carried; every carried
  action's text is in at least one packet (62 in one lane, 99 in several: `tools/act_lanes.json`).
- **Files**: 313 in the work order's U26 list; the lane sets hold 249 repo paths (A 46, B 52, D1 56, D2 52, E 26, X 7,
  lead 10); the rest are read-only references (src/, upstream, datasheets) or paths already gone or not yet born (gaps.md §5).
- **Scoped tests**: 191 in the work order (127 tests_scripts, 57 tests, 7 tests_js), not the brief's 145. **Full gate**: the
  six items of `work_order.json` (lint, three mypy passes, unit tier at -1 and 32768 with the tests_scripts tier, the twin
  tier for every device, the web tier). **Hardware rounds**: R0-R7 with H items (§7); nothing runs on hardware in U26.
- **Register**: one open delta (`REGISTER.md:729`, STA mode at the bench start) is settled by R-5; three folded deltas
  (`:726`, `:734`, `:736`) are inside M.HW_BENCH.006 (4), .125 (1), .127 (1), M.TOOL.034 (1). **Open findings**: 31 rows
  name U26 (§6).

## 2. The cut (R-1): six lanes, three waves

| wave | lane | family | base | steps / changes | est. lines / files |
|---|---|---|---|---|---|
| 1 | **A** harness core, twin runner, board facts | `tests_hardware/{harness,evidence,error_log_helpers,bench_control,http_client,website_identity,bench_facts,twin_board,conformance,heap_map,heap_bounds,plausibility_bounds,kick_then_reset}.py`, `device_scripts/{bench_facts,_bench_device}.pyi`, `_shared/` (7 includes), `fram_raw_dump.py`, `digital_twin/run_device_script.py` (+`_http_client.py` verify), `buildgen/{validate,generate}.py`, `devices/dev.toml`, `tests_scripts/_devices.py`, `scripts/record_twin_instrument_runs.py`, 16 L0 files | `<U25>` | 49 / 65 | ~3400 / 46 |
| 1 | **B** session, gates, guards, runners | `tests_hardware/{conftest,markers,scd30_prerequisite,soak_durations,spoof_udp,rogue_udp_responder,ntp_probe}.py`, `{flash,bench}/conftest.py`, `tests_scripts/conftest.py`, 4 device scripts (SCD30 prerequisite, standard DebugLevel), `scripts/{build_firmware.py,_require_clean_hardware_run.sh,_hardware_verdict.py,run_bench_soak_tests.sh,run_flash_hardware_suite.sh,mpremote_connect.sh,run_manual_hardware_tests.sh,typecheck.sh}`, 30 L0 files (session tests and every device-script and module guard) | `<U25>`, resumed on `<API>` | 41 / 56 | ~3600 / 52 |
| 2 | **D1** FRAM, memory, system commands, reset codes, manual | `flash/test_{fram_storage,memory_stress,heap_layout,reboot_persistence,system_commands,task_supervisor,watchdog_starvation,config_float_round_trip,unretrieved_task_exception_handler,toolchain_flash_boot}.py`, `bench/test_{system_commands,reset_reasons}.py`, 35 device scripts (FRAM error logs/manager/pause/WP/busy/capacity/hold, heap, loop/stack, system commands, reset codes, reboot persistence, config float), `manual/` (7), `tests/test_asy_fram_manager.py`, `test_manual_runner_summary.py` | `<W1>` | 49 / 62 | ~3200 / 56 |
| 2 | **D2** buses, sensors, conformance, UART link | `flash/test_{bus_concurrency,bus_electrical_timing,sensor_accuracy,chip_conformance,uart_crossover}.py`, `_shared/{bus_reader_loops,isl_error_log}.py`, 45 device scripts (bus hazards, raw FRAM races, ISL29125, SCD30, SGP40, BMP3xx, conformance probes, electrical, country code, UART) | `<W1>` | 43 / 61 | ~3400 / 52 |
| 2 | **E** the bench over the network | `bench/` (19 modules: `_load.py`, `dns_probe.py`, 11 rewritten tests, 6 new), 5 bench-only scripts (heap under the ceiling, serving at default GC, allocation need, the echoed link, the radio re-init), the retired edge-value script, `test_dns_probe.py` | `<W1>` | 28 / 41 | ~3300 / 26 |
| 3 | **X** docs from the relay | SPECIFICATION.md, README.md, CLAUDE.md, BACKLOG.md, HEAP_FRAGMENTATION_MEASUREMENTS.md, tests_hardware/README.md, digital_twin/README.md | `<W3>` | 49 / 50 | ~1300 / 7 |
| — | **lead** | pyproject.toml, host_typecheck.ini, the shrink-only lists (`_citation_allowlist.txt`, `_decision_vocab_allowlist.txt`, `test_import_placement.py` `_PENDING`, `test_no_variant_literals.py` rows, `test_mypy_any_baseline.py`), `tests_hardware/twin_record.json`, the deletions `soak_tiers.py`, `isl29125_conformance.py` | merge points | 13 / 17 | ~300 / 10 |

Why this shape (rule 13): the infrastructure every instrument needs (render, facts, the twin runner, the session) must
exist before the instruments are rewritten and twin-run, so the importable harness (A) and the session with every guard
(B) come first; B's conftest imports A's names, hence one API stop inside wave 1 (R-1), the shape U25 used. Guards first
means each wave-2 lane's seen-failing-first is a wave-1 guard red on its own file at `<W1>`, green after its edit (R-15).
Each wave-2 lane owns a script together with the host test that reads its facts (the tight contract); the two script
families read across lanes are named in R-22. Six lanes is the cap and the size the work needs (~19,500 lines in all).

**Disjointness**: `cd S/u26; L="A B D1 D2 E X LEAD"; for a in $L; do for b in $L; do [[ $a < $b ]] && comm -12 <(sort
files_$a.txt) <(sort files_$b.txt); done; done` prints nothing (21 pairs), `cat files_{A,B,D1,D2,E,X,LEAD}.txt | sort |
uniq -d` prints nothing (checked by `tools/lanes.py`, 249 paths). A change that turns another file red carries that file
(U25 lead ruling v1 item 8) wherever the file is the breaking change's own family; the exceptions are the doc checks and
the shrink-only lists, which stay X's and the lead's (R-8, R-15).

## 3. Merge points, the API stop and the relay

1. **`<API>`**: A commits **A1** first: the public surface wave 1 and 2 call, each with its L0 cases green: harness
   `REPO_ROOT`, `bench_device()`, `hotspot_password()`, `configured_max_connections(device=None)`,
   `fram_backed_logger_names()`, `get_routes()`, `render_device_script(path, **extras)`, `parse_facts(output, *,
   allow_missing_done=False)`, `save_fram_raw(board, reason) -> FramDump`, `Board.run_isolated(..., **extras)`,
   `run_isolated_expect_reset(..., hold_unread_s=None, **extras)`, `Board.recovery_events`, `BOOT_COMPLETION_MARKERS`,
   `boot_lines()`, `crash_lines()`, `wait_for_boot()`, `observe_during()`, `kick_then_reset()`, `recover_by_reset()`,
   `reflash()`; `bench_facts.build()` and `device_scripts/bench_facts.pyi`; `evidence.{evidence_dir,save_json,save_text}`;
   `error_log_helpers.{save_errcount,reset_all_error_logs(dut_ip, reason),errcount_entry,get_errcount,ErrcountEntry}`;
   `bench_control.{clear_leftovers,block_udp_ports_from,unblock_udp_ports_from}`; `twin_board.TwinBoard` with
   `digital_twin/run_device_script.py`; `_shared/{facts,watchdog}.py`; the `[device].bench` key and `devices/dev.toml`'s
   `bench = true`. The lead merges A1 onto `<U25>` as `audit/u26-api1`, rebuilds (`S/u23/rebuild.sh`), runs ruff, the three
   mypy passes cold and `pytest --collect-only tests_hardware -q` (must collect: R-3), then resumes B on it. A continues to
   its final on its own branch.
2. **`<W1>`**: A's and B's finals merged (`audit/u26-w1`); rebuild; ruff, mypy (reds only in wave-2 files' calls of a
   final signature, listed in the relay), collect-only clean, A's and B's L0 files green; the expected reds (B's guards on
   today's scripts and modules, A's worker rule on today's bench modules, the doc checks) listed per wave-2 lane with their
   first failing line; the lead lands A's and B's relayed `pyproject.toml`/`host_typecheck.ini` lines and `--strict-markers`.
3. **`<W2>`**: D1, D2, E finals merged (`audit/u26-w2`); the **lead step** (brief_lead.md): deletions after the last importer,
   the relayed config lines, list shrinks, the twin record (`scripts/record_twin_instrument_runs.py`, one run, gc -1), every
   guard green; that tree is `<W3>`.
4. **`<W3>` → X**, then the unit gate (`S/gate_v12.sh` layout, plus `uv run pytest --collect-only tests_hardware -q`).

**The relay**: `S/u26/relay.md`, append-only. Each code lane appends, under its own heading, before hand-back: every new
or moved `@tunable` (ID, value, site, basis), each API end state another lane or X reads, fact lists of scripts read across
lanes (R-22), `COVERS_TWIN_SCENARIOS` it declared or dropped (for E.6.6), lines owed by the doc checks (citations, Part N,
L.3, E.6.6), relayed config lines (R-8), silicon-only twin reasons (R-11) and its run times. X reads only the relay, its
packet and the tree.

## 4. Sizes and the splits each lane would take (R-2)

Estimate (`tools/sizes.py`): rewritten or added lines; an existing file counts 45 % of its `a8dc1a1` length, a new file a
typical size for its kind (device script 95, flash test 120, bench test 150, L0 file 110, include 45), docs by hand.
Measured inputs: `tests_hardware/` is 15,985 lines at `a8dc1a1` (device scripts 6,752 in 62 files, bench 4,019 in 12,
flash 1,263 in 13, README 1,660, harness 568, conftest 298); 59 of 62 scripts print `RESULT:`, none reads `BENCH`, seven
import a generated module.

- A (~3400/46) → **A1** harness, render, twin runner, board facts, includes, buildgen key | **A2** error_log_helpers,
  evidence, bench_control, HTTP clients, website identity and their L0 files; costs a third API party and splits the hub
  test (`test_bench_harness_helpers.py` covers both halves).
- B (~3600/52) → **B1** conftest family, markers, prerequisite, network tools, session tests | **B2** the device-script and
  module guards and the image/runner tooling.
- D1 (~3200/56) → **D1a** FRAM error logs, persistence, the manual mode | **D1b** memory, system commands, reset codes.
- D2 (~3400/52) → **D2a** bus hazards and electrical (`test_bus_concurrency`, `test_bus_electrical_timing`) | **D2b**
  sensors, conformance and UART (`test_sensor_accuracy`, `test_chip_conformance`, `test_uart_crossover`).
- E (~3300/26) and X (~1300/7) are inside the bar.
Kept whole (rule 13): each split adds a lane's fixed cost (reading, worktree, rebuild, checks) for no gain the waves need.

## 5. Rulings

`briefs/rulings.md` R-1..R-26, one line each (agent, 2026-10-14), every one on the owner-review list at U26's close. The
points with no conservative default go to the owner through U25's unit-end report (none new; three pending answers keep
their stated defaults, R-13).

## 6. Open findings and register rows naming U26, by lane

| finding | what | lane, step | default |
|---|---|---|---|
| OF-06, OF-66 | `fram_pause_unpause_and_gating.py`: swallowed `hog.deinit()`; a skipped premise step reported as a failure | D1, 156 (M.HW_DEV.068) | the deinit failure is a fact; a dependent check skipped with its reason |
| OF-07, OF-08, OF-23 | ISL29125 envelope: restore results ignored; "no E entries" reads the capped history; freshness rests on `SETTLE_S` | D2, 183 (M.HW_DEV.142) and `_shared/isl_error_log.py` | results checked; `ErrCount` read beyond the history; freshness by a new `TS` |
| OF-08, OF-22 | lighting scenarios: capped history; one-second `TS` resolution misses a switch-and-back | D2, 209 (M.HW_DEV.143) | as above; chatter counted from the range field per poll, not `TS` alone |
| OF-09 | `wait_for_script_server()`: `main.py`'s server answering past the handover reads as the script's | A, 2 (M.HW_BENCH.015) | the wait checks the script's own marker route/facts |
| OF-10 | an admission above the ceiling retried and unreported | E, 61 (M.HW_BENCH.080) | every admitted-above attempt recorded and failed |
| OF-11 | tcpdump stderr to DEVNULL | A, 53 (M.HW_BENCH.021) | stderr kept; a start failure raises naming tcpdump/sudo |
| OF-14 | A.U8C2.25's conftest tags in no step | B, 48 (M.HW_BENCH.003) | written with the rewrite of those lines |
| OF-21, OF-109, OF-110 | heap layout: a degraded stagger unreported; `start_timers()` bounded past the watchdog; a dying task silent at level 0 | D1, 170/171 (M.HW_DEV.117/.118); OF-109's cadence site D2, 178 | SYSTEM log read; timers as a task with feeds; the always-printing report installed first |
| OF-36 | level-0 escape of an unsupervised task | none (pending owner answer) | R-13: L3 gates read `TASK_RAISED` for supervised tasks only |
| OF-40, OF-107 | soft vs hard reset bits; an exception after `BOOT_DONE` reads as code 2 | D1, 48 (M.HW_BENCH.083), parked R1 [H10, H12] | measured on silicon, no new code |
| OF-52 | float32 FRC sums over a 3600 s window, no on-target bound | D2, new device script + case in `flash/test_sensor_accuracy.py` (with 179, M.HW_DEV.137) | R-12: driver's FRC accumulation over a synthetic window on silicon, facts out, double-precision expectation host-side; no SCD30 command; parked R1 |
| OF-55 | `sgp40_sample_cadence.py` may write defaults to flash | D2, 178 (M.HW_DEV.136) | the host test checks the config files are present (read-only exec) before the run, else fails naming them |
| OF-60 | a lost FRAM chip detected late | D1, 48 (M.HW_BENCH.101) manual step | detection latency recorded in the unplug step; parked R2 [H17] |
| OF-70 | TX deadline, cancel and dead bus log the same E82 | D2, 94 (M.HW_DEV.052) stalled-TX case; D1 manual pulled-jumper step | the causes recorded; parked R1/R2 [H37] |
| OF-72, OF-73 | UART recovery/load scripts ignore `setup()` results | D2, 92 (M.HW_DEV.047), 153 (M.HW_DEV.051) | a refused setup is a fact and fails the host test |
| OF-100 | a "Failed" `ResetErrors` passes | A, 48 (M.HW_BENCH.050) | strict: anything but "OK" raises |
| OF-160 | A.U18.R01's L2 sentence (a WLAN status unreadable twice re-constructs the interface) against the product, which reads an unreadable status as "not down" (one W per tick, no re-construction) | E, 48g/66 (M.HW_DEV.113, M.HW_BENCH.096) | the rung's silicon steps trigger it by a failed hardware call, not an unreadable status; the L2 sentence is read so (retargeted at U25's close) |
| OF-101 | hotspot test asserts an empty WEBSERVER log after a malformed head | E, 48 (M.HW_BENCH.072) | W `HTTP_BAD_HEAD` allowed, `HTTPDropped` ≥ 1 |
| OF-102 | the "/" probe silently dropped | E, 172 (M.HW_DEV.119) | exactly one "/" handler asserted |
| OF-105, OF-119, OF-123 | dev's serving demand vs budget; the RX ring's 2x cost; ENOMEM after queued bytes | parked R1/R4 [H44, H37, H39] | measured on existing instruments; Part N follows (phase C) |
| OF-118 | host text I/O without `encoding=` in `tests_hardware/` (`bench/test_hotspot_role_reversal.py:127`, `isl29125_conformance.py:33, :35`) | E 59; A (conformance.py replaces the old module) | `encoding="utf-8"` on every host text read a lane writes |
| OF-122, OF-127 | listener-close NULL stores; root-equivalent sudoers | none (pending owner answer) | R-13 defaults (a) |
| OF-130 | README hotspot log level, `BENCH_AP_PASSWORD` paragraph; the bench fixture's dead "Permanently no WLAN connection" match | X (a)(b); B, 48 (M.HW_BENCH.007) (c) | the dead match removed |
| OF-131 | `ap_down()` tolerates an inactive profile; teardown `ap_up()` re-activates an active AP | A, 54 (M.HW_BENCH.023) primitive; E, 59 (M.HW_BENCH.071) | a primitive leaving the hotspot with the AP left down; no re-activation of an active AP |
| REGISTER `:740` | STA mode at the bench start | E, 48/59 | R-5 |
| U25 docs-lane facts | `fram_crash_points`, `uart_load`, A.U25.61's flash check | D1 162, E 94, D1 171 | R-25 |

Register rows `:124`/`:125` (FRAM CS power-off sentence, the manual SCD30 power-loss step up to 21 NVM writes behind
`confirm()`) are D1's manual steps (M.HW_BENCH.101 (6), .102 (6)) with X's text; `:127`/`:736` is R-23; `:140` (seeds in
the test band since U3) and `:171`, `:305`, `:341`, `:442`, `:473`, `:486` (scripts left in today's form for U26) are
the D1/D2 rewrites; `:214`, `:315`, `:322` are tag/name stages X and the lanes finish; `:395` (device scripts pass
`timeout`) is the `BENCH` bus form; `:541` (dev's `rx_ring = 512`) is read by D2's UART scripts through `BENCH`.

## 7. Parked hardware items, per round (nothing runs in U26)

Every round: the owner's go-ahead in its own conversation (H01, CLAUDE.md), the FRAM-backed `errcount` and the raw FRAM
saved before anything writes (H02: B's `fram_evidence_saved` through A's `save_errcount`/`save_fram_raw`; the
first-chunk caveat of CLAUDE.md's FRAM rule: an isolated-driver script lands on production's first chunk, so the logs are
read before any FRAM script), the lower levels L0-L2 at both GC stages first (H03, the runners), the image record and the
identity fixture (H04: B's record and `board_image`), the standard board state at start and end (H05: B's
`standard_state`), the boot log (H06), the bench network switch armed around every `br0` change (H07, the owner's
operation, SPECIFICATION.md B.13). Markers are deselecting gates (wear) or skips: `persistence_write`, `scd30_extra_write`
(AND-gated), `flash_cycle`, `soak_duration`, `multi_day_rollover`, `neopixel_sweep`, `toolchain_reverify`; pinned
prerequisites stay unmarked (the SCD30 start at most once, the `joined_hotspot` SSID clear and restore, the standard-state
repairs under `--repair-standard-state`).

| round | items (H) | what runs (lane that writes it) | gates |
|---|---|---|---|
| R0 | H65 bench facts; H01 prerequisites, H07 host network | README Prerequisites/host recipe (X); the sweep script's per-bus scan (D2 `bus_topology_autodetect_and_hazard_sweep.py`), FRAM RDID (A `fram_raw_dump.py`), rig, DHCP keying, BME688, host OS (the owner) | none (reads only) |
| R1 | H08 pre-audit capture; H10, H12, H14, H15 reset and reboot codes; H13 ungated command rows; H16, H18 (L3 case), H81 recovery rungs; H20, H21, H23 loop lag, stretches, C stack; H22, H72 FRAM hold, forensic scripts, reset-race seams; H25, H26, H27, H29 conformance probes, register volatility, PRST, lone BMP3xx; H31 SCD30 prerequisite and the five dependents; H37 UART hazards, multi-chunk SET, both CRC modes over the jumper; H39 (override half), H40, H41 lwIP hammer, PCB count at the ceiling, body cap; H44, H83 heap bounds, loaded `MemFree`; H48, H51 float boundary, deinit, scheduler drop, alarm pool, country code; H55 estimated tunables; H61 spoofing; H65 scan; H69 starvation test ends serving; H71 interaction cells; H73 every other new or changed test | D1 (reset codes, commands, FRAM, memory, loop scripts, starvation, supervisor), D2 (bus hazards, conformance, UART flash, electrical, rungs), E (STA, network resilience, ceiling, bus and link under API load, radio re-init, spoofing, boot order), B (session fixtures, prerequisite) | default run only: every wear gate off |
| R2 | H11 power-on code; H13 two manual power cuts; H17 SCD30/FRAM unplug-replug, SDA-to-GND (OF-60); H18 scope; H28 M1 rig geometry; H30 0x0010 across a power cycle; H49 power cut during a config write; H65 rig row; H66 Safari/mobile, captive portal | D1 `manual/` (persistence, bus electrical, sensor accuracy, wifi) | manual `confirm()` before each persisting step (`_MANUAL_PERSISTING_STEPS`); the SCD30 power-loss step's NVM writes declinable at the step (REGISTER `:125`) |
| R3 | H13 `resetconfig`; H28 S3b envelope with `Overrange`; H30 SCD30 argument reaction and the two owned offset writes; H31 read-while-write; H32 config-write arm under API load; H33 Altitude with `AmbPres` 0; H36 `TempOffs` 0.53 as typed; H42 console output with a non-reading host at level 0; H47 config float round trip; H62 role reversal, destructive stage last; H68 torn write on the reset race; H73 gated rows | D1 (commands, float round trip, reboot persistence), D2 (envelope, SCD30 writes), E (hazard arm, sensor push, network row (3), role reversal, end-to-end backup reset) | `--allow-persistence-write`; `--allow-scd30-extra-write` on top where marked; `--allow-neopixel-sweep` (envelope) |
| R4 | H38 CRC16 bench run on a reflashed image; H39 lwIP stall on the unpatched control image, then the override; H55; H70 reflash smoke test and toolchain re-verification | E (`test_uart_link_crc16.py`, `test_modlwip_send_stall.py`), D1 (`test_toolchain_flash_boot.py`), A (`reflash()`), B (image record, `--device-toml`) | `--allow-flash-cycle`; `--allow-toolchain-reverify`; evidence saved before each reflash; the round ends on the release image (`board_image`) |
| R5 | H19 trigger spacing; H34 FRC readiness defaults; H55; H64 6 h soak; H35 SGP40 cadence; the memory and clock-stretch soaks | E (boot order, FRC baseline, memory stress bench), D2 (cadence, electrical soak), D1 (memory stress soak) | `--soak-duration short|mid|long` through `scripts/run_bench_soak_tests.sh` |
| R6 | H63 rollover across the tick and 32-bit wraps, ~2 h, inside session 1 after R5 and before R4 | E (`test_ticks_ms_rollover.py`) | `--allow-multi-day-rollover` + `--allow-flash-cycle`; needs U27's tick-offset image and rollover runner (M.SCR.074): not runnable until U27 lands |
| R7 | H45 two-image GC proof | D1's heap-layout arms (`flash/test_heap_layout.py`) on two images | needs a second image per U27's test overrides; phase C |

H08, H18, H36, H45, H55, H69 are in the work order's U26 rounds but named by no U26 change's Kind; each maps above to
the instrument that serves it (A.C's phase-C round plan owns the order). M.HW_BENCH.104 (first flash of a blank board) is
in no round by its own text.

## 8. Operating modes and the shared-resource hazard tiers

| mode | steps that touch it (lane) |
|---|---|
| station (STA, over the bridge) | 48 `dut_ip` (B .007), image check (B .060), standard state (B .006); E 32, 48 (.065, .067, .076-.079), 56-66, 86, 87, 94, 96, 98, 120; D1 48 (.083 reset reasons, .088 commands over REST); R-5 for the STA reading |
| hotspot / AP | E 48 (.072 captive DNS, REST, client faults over the hotspot), 59 (.071); B 48 (.007 stale-credential path scans with the AP down); A 54 (.023 single radio), 48 (.024 spoof support); D1 69 (manual Wi-Fi); X 72 (.124) |
| silent mode | E 59 (.071: the window after stage 6, one more streak, then silent), 48 (.073); X 72 |
| role-reversal stages 0-8 | E 48 (.072 stages 0-5), 48 (.073 stage 6 last by `destructive_last`, the flip back its own test), 59 (.071 restore on every path, stages 7/8, OF-131); A 54 and the OF-131 primitive; B 48 (.003 destructive items last) |
| both GC stages | every wave-2 instrument's twin run at -1 and 32768 (48 M.HW_DEV.010); `gc_threshold` fact and its guard (B 147); A 48 (.038 conformance twin at both stages, .091 `TwinBoard(gc_threshold)`); D1 84, 169-171; E 87, 172-174 |
| each device the bench runs | only the board whose TOML sets `bench = true` (`dev`) is flashed (CLAUDE.md; A 48 GEN.025/.026/.052, .010); L0 checks iterate every derived device (A 229, 231, 244, 134; B 215, 216) |
| shared-resource hazards, real-hardware tiers | flash: D2 48 (`flash/test_bus_concurrency.py` .080 and scripts .081-.089), 160 (the sweep `bus_topology_autodetect_and_hazard_sweep.py`, .090), 163, 164; bench: E 48 (.065), 57 (.064) (`bench/test_bus_concurrency_under_api_load.py`); other shared resources: FRAM (D2 48 .069; D1 FRAM scripts), the config file (D1 commands, reboot persistence), sockets (E 62, 96), the heap (D1 84, E 86/87), the UART (D2 94, E 94) |

## 9. CI time (base `<BASE>`)

U26 adds 20 new L0 files (A 7, B 12, E 1) and grows about 20 more in the tests_scripts tier (`unit-tests*`, 45 min, `.github/workflows/ci.yml:454`; the tier's own
bound 1200 s, `scripts/test.sh:96`, run beside the MicroPython loop), one case in `tests/test_asy_fram_manager.py`, and
~90 files to the host and main mypy passes (`lint-and-typecheck`, 15 min, `ci.yml:330`). Most new L0 files are AST or
fake-board checks (under 2 s each); two start MicroPython (`test_twin_board.py` one twin process, `test_device_script_fram_regions.py`
one twin boot, ~5-10 s each) and one repeats collection (`test_tests_hardware_collect_matrix.py`: as written ~1,030
in-process collections, estimated 3-5 min, R-9's 60 s line). Estimate: tests_scripts tier +1-2 min after R-9, still under
the MicroPython loop it overlaps; `unit-tests` unchanged in wall time if the tier stays the shorter branch (the lead
checks against `<BASE>`'s tier time); mypy +20-40 s; `firmware-build-verify` (15 min, `ci.yml:654`) +<1 s for the image
record; `digital-twin-e2e` (20 min, `ci.yml:618`) untouched (no twin suite or harness change).

## 10. Per-step table

Every change in work-order order: step (`g` = co-landing group), change, lane(s), title, the seen-failing-first check
without hardware (or "verify only" with its proof), and the round it is parked in. Lanes read their rows in their packet's
index; the full texts are in the packets.

| step | change | lane | title | seen failing first (no hardware) / parked round |
|---|---|---|---|---|
| 1 | HW_BENCH.004 | B | Notes reach the run record: `result_note`, `record_session_note()` | verify only: result_note/record_session_note exist (conftest.py:139-160); test_tests_hardware_run_record's recovery-note case (M.TSC.216) green after B's rewrite |
| 2 | HW_BENCH.015 | A | Recovery by reset is one reported helper; serving waits are tunable | test_bench_harness_helpers: M.TSC.022's kick-before-reset order and recover_by_reset cases (ready at once / after reset / never), red at the base |
| 3 | HW_BENCH.016 | A | One boot-line, crash-line and fault-window observer | test_bench_harness_helpers: M.TSC.025's marker-vs-src/ and observer cases; test_memory_error_gate_agreement's harness row, red at the base |
| 4 | HW_BENCH.018 | A | The board resolver delegates to the installer's | test_resolve_board_device: the seven cases against the delegating resolver (M.TSC.171), red while harness keeps its own glob |
| 5 | HW_BENCH.020 | A | Every injection is undone and proven absent by state | test_bench_control_restore: '-D fails and the listing still shows the rule' raises (M.TSC.178), red at the base |
| 6 | HW_BENCH.022 | A | A run starts by clearing and reporting a killed run's leftovers | test_bench_control_restore: clear_leftovers() removes only the tagged rules/qdisc and reports each, red at the base |
| 7 | HW_BENCH.025 | A | Remove the confirmed leftovers | pure removal: `git grep` shows no caller of the three definitions (A.U26.83); ruff F401 on the dropped import |
| 8 | HW_BENCH.030 | A | The hardware client keeps the twin client's shape, typed and pinned | test_http_client_shape_parity (new, M.TSC.097) and test_http_client_ceiling_close (M.TSC.096: CeilingRefusedError before the first byte), red at the base |
| 9 | HW_BENCH.035 | A | The allocation marker is the shared one | test_memory_error_gate_agreement: the heap-map gate reads harness.MEMORY_ERROR_MARKERS (M.TSC.108), red at the base |
| 10 | HW_BENCH.042 | A | `kick_then_reset.py`: the ad-hoc reset never skips the kick | test_bench_harness_helpers: kick_then_reset() order case; the CLI exits 2 naming `env --tier bench` with no bridge (fake BenchBridge), red at the base (file absent) |
| 11 | HW_BENCH.043 | A | `plausibility_bounds.py`: one bound per quantity, each with its source | B's product-copies guard (test_tests_hardware_product_copies) reads every BOUNDS source at W1; A: import, ruff, host mypy clean |
| 12 | HW_BENCH.039 | B | No change beyond the sweep conventions | its L0 case red at the base (tests_hardware_product_copies) |
| 13 | HW_BENCH.051 | A | Log oracles fail closed and are typed | test_bench_harness_helpers: M.TSC.023's errcount_entry and shape-change cases, red at the base |
| 14 | HW_BENCH.052 | A | Remove the uncalled non-empty check; keep the clean check for its call | pure removal plus typing: no caller of the non-empty check (grep); test_bench_harness_helpers's clean-check case still green |
| 15 | HW_BENCH.062 | E | The DNS probe can ask for any QTYPE | E: a tests_scripts case for build_query(qtype) packing (QTYPE/QCLASS bytes) in a new tests_scripts/test_dns_probe.py, red at the base |
| 16 | HW_BENCH.100 | D1 | Manual tests can fail; the runner ends with the summary block | test_manual_runner_summary (M.TSC.203): a test returning with no judgment is FAIL; Ctrl-C prints the block, exit 130, red at the base |
| 17 | HW_BENCH.106 | D1 | `__main__.py` registers the tests and exits by the one idiom | `python tests_hardware/manual/__main__.py --list` from a fresh interpreter lists every manual test (U27 pins it in L0); ruff F401 reads the lead's allowed-unused-imports row |
| 18 | HW_DEV.012 | D1+D2 | Error numbers in scripts come from the catalog | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 19 | HW_DEV.013 | D2 | SPEC citations in this cluster follow the renumbered sections | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason; red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it |
| 20 | HW_DEV.021 | B | A flash session ends on a serving board | its L0 case red at the base (bench_restores_serving) · parked R1 |
| 21 | HW_DEV.096 | D1 | `resetconfig` through the generated callback over a scratch store set | B's guards red on the script at W1: device_script_config_flush, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 22 | HW_DEV.152 | D1 | The config float round trip on the board's single-precision floats | red at W1: level_containment, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R3 |
| 23 | SCR.029 | B | One board resolver, a retried sync, help | B: the stubbed-uv argv case asserts `--no-sync` (test_hardware_runners or a grep-backed case in test_require_clean_hardware_run_sh); the rest of the entry is U27's |
| 24 | SCR.032 | B | Soak runner: one duration, on top of a clean bench run | test_hardware_runners: the soak runner passes `-m soak_duration` and `--soak-duration` (A.U26.35 names), red at the base |
| 25 | DOCS.057 | X | Real hardware: levels L3 and L4, soak as durations, the verdict text | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 26 | DOCS.066 | X | The chroot list: one paragraph per landing unit, every build-environme | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 27 | HW_BENCH.040 | B+LEAD | Soak runs are named durations | B: soak_durations import and the conftest --soak-duration choices (test_tests_hardware_collect_matrix's soak arms), red at the base; the lead's soak_tiers.py deletion after W2 leaves `git grep soak_tiers` empty outside docs |
| 28 | SCR.033 | B | Manual runner: help, retried sync, `--no-sync` | test_hardware_runners: the manual runner's uv call carries --no-sync (A.U26.75 stage only), red at the base |
| 29 | SCR.034 | B | Hardware wrapper: run record, archive, `$EVIDENCE_DIR`, verdict in Pyt | test_require_clean_hardware_run_sh (M.TSC.122 names): the renamed flags pass through; uv run --no-sync, red at the base |
| 30 | SCR.067 | B | Image record and size report beside every `.uf2` | test_build_firmware: the image record beside the .uf2 holds buildDate equal to the staged module's date, dirty, lwip, overrides (A.U26.02), red at the base |
| 31 | DOCS.048 | X | Recipe "Build and flash", the flashing rule, and the reflash runbook | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 32 | HW_BENCH.075 | E | The lwIP stall proof: reproduce on the control image, then show the ov | red at W1: bench_no_task_ended_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R4 |
| 33 | SPEC.095 | X | F.2 the I2C recovery ladder per sensor, the boot clear, live reconnect | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 34 | TEST_UNIT.041 | D1 | Dual copy, status bytes and torn writes, by catalog code | new/changed cases red at the base: test_asy_fram_manager |
| 35 | TOOL.031 | LEAD | One pyflakes table names the side-effect imports | lead: site files |
| 36 | TOOL.034 | LEAD | pytest: strict markers and the repo root on the path | lead: site files |
| 37 | TOOL.041 | LEAD | Readback section: the timeout is tagged; three new post-build proofs | lead: verify only: U21 landed the readback tag and proofs (toolchain/micropython_overrides.py read_lwip_macros_from_build :841); A.U26.02's use is B's build_firmware.py record |
| 38 | TOOL.055 | LEAD | build_firmware(): two overrides in, both proven, no global flag | lead: verify only: U21 landed both overrides in build_firmware() (toolchain/setup_toolchain.py); A.U26.02's record reads the macros in B's scripts/build_firmware.py |
| 39 | TSC.022 | A | Serving restore and recovery-by-reset cases | new/changed cases red at the base: test_bench_harness_helpers |
| 40 | TSC.024 | A | The thread-worker rule sees every worker's fetch, and joins | new/changed cases red at the base: test_bench_harness_helpers |
| 41 | TSC.028 | B | Bench and flash tiers end on a serving board | new/changed cases red at the base: test_bench_restores_serving |
| 42 | TSC.096 | A | Ceiling-close cases follow the refused-connection class | new/changed cases red at the base: test_http_client_ceiling_close |
| 43 | TSC.097 | A | The hardware and twin HTTP clients keep one shape | new/changed cases red at the base: test_http_client_shape_parity |
| 44 | TSC.108 | A | Every allocation gate agrees, the JS and heap-map gates included | new/changed cases red at the base: test_memory_error_gate_agreement |
| 45 | TSC.120 | B | Marker registry: strict, every gate flag names its marker | new/changed cases red at the base: test_persistence_write_marker_completeness |
| 46 | TSC.122 | B | The hardware wrapper: pytest's exit kept, the verdict delegated, `-m`  | new/changed cases red at the base: test_require_clean_hardware_run_sh |
| 47 | TSC.138 | B | Wear-gate deselection with the new flags and the routine set | new/changed cases red at the base: test_tests_hardware_persistence_write_gating |
| 48g | GEN.025 | A | Validator tables: device keys, wiring consumers, comments | test_buildgen_validate: `bench = 1` refused naming the field; test_toml_schema_contract red until X's L.3 row (expected, relayed) |
| 48g | GEN.026 | A | Device table and source-reading helpers | test_buildgen_validate (M.TSC.056 bench rows), red at the base |
| 48g | GEN.052 | A | dev header and `[device]`: bench key, wiring comment | test_bench_device: exactly one derived TOML sets bench = true, red at the base (no TOML sets it) |
| 48g | HW_BENCH.001 | B | One option table: data-named board, image record, kebab gates | its L0 case red at the base (device_script_rig_parking, persistence_write_marker_completeness) |
| 48g | HW_BENCH.002 | B | Markers registered strictly, each naming what it spends | its L0 case red at the base (device_script_rig_parking, persistence_write_marker_completeness) |
| 48g | HW_BENCH.003 | B | The collection hook tags deselections and runs destructive tests last | test_tests_hardware_run_record (M.TSC.216): deselections carry deselected_by; collect-only puts destructive_last items last, red at the base |
| 48g | HW_BENCH.005 | B | Board, bridge and bench-device fixtures: twin-aware, leftovers cleared | test_bench_device (--bench-device usage error), test_twin_board (--twin yields TwinBoard), test_bench_control_restore (clear at start), red at the base |
| 48g | HW_BENCH.006 | B | A session starts with evidence, then checks the standard board state | its L0 case red at the base (device_script_config_flush) |
| 48g | HW_BENCH.007 | B | `dut_ip` reports its recoveries; the stale-credential path scans with  | test_tests_hardware_conftest_constants (M.TSC.173: password from the bench TOML through the harness helper), red at the base · parked R1 |
| 48g | HW_BENCH.010 | A | Board facts come from data: one helper each | test_bench_device (bench_device() over tmp devices/: zero or two flagged TOMLs raise naming the files) and the hub routes case (M.TSC.226), red at the base |
| 48g | HW_BENCH.011 | A | `_mpremote()`: a retry never re-runs a started script; every recovery  | test_harness_mpremote_retry (new, M.TSC.198): a retry never re-runs a started script; each recovery event recorded |
| 48g | HW_BENCH.012 | A | Isolated runs render board facts, run once, and return what they saw | its L0 case red at the base (device_script_bench_facts, device_script_facts, hardware_clones) |
| 48g | HW_BENCH.024 | A | Spoof support: hold the real reply back | test_bench_control_restore: block_udp_ports_from() then unblock verifies absence by listing, red at the base |
| 48g | HW_BENCH.036 | B | The rogue responder binds port 0 and counts what it answered | B: new tests_scripts/test_rogue_udp_responder.py on localhost: port 0 binds, .port is the bound port, answered_from counts each source, red at the base |
| 48g | HW_BENCH.038 | A+LEAD | One conformance gate for every bus chip, run through the twin board | test_twin_board/conformance: run_probe_on_twin() through TwinBoard at -1 and 32768 returns the probe's keys; D2's test_chip_conformance consumes it · parked R1 |
| 48g | HW_BENCH.041 | A | `bench_facts.py`: the bench board's facts as one rendered dict | its L0 case red at the base (device_script_bench_facts) |
| 48g | HW_BENCH.044 | B | `scd30_prerequisite.py`: start the measurement at most once per sessio | test_scd30_prerequisite (new, M.TSC.212): exactly one start send per session, each failure mode raises after at most one send · parked R1 |
| 48g | HW_BENCH.045 | B | `spoof_udp.py`: a hand-built datagram from a documentation address | B: new tests_scripts/test_spoof_udp.py (A.U26.56's L0): build_datagram() checksums against a hand-computed vector; a --src outside RFC 5737 exits 2, red at the base (module absent) · parked R1 |
| 48g | HW_BENCH.050 | A | Save, then clear: the one evidence primitive before any `ResetErrors` | test_evidence_snapshot: GET and the saved file before the PUT; a 'Failed' ResetErrors raises (OF-100), red at the base |
| 48g | HW_BENCH.055 | A | One evidence directory per run | test_evidence_snapshot: evidence_dir() honours $EVIDENCE_DIR; a second save of one name gains -1, red at the base (module absent) |
| 48g | HW_BENCH.060 | B | The bench tier proves the board runs this round's image first | test_board_image_fixture (new, M.TSC.180): equal dates pass; date, device, ensemble finding, missing record each exit naming the cause |
| 48g | HW_BENCH.061 | E | One shared reader worker for the bench load arms | A's thread-worker rule (M.TSC.024, test_bench_harness_helpers) red on today's nested workers at W1, green on E's _load.sensors_reader; B's clone guard |
| 48g | HW_BENCH.065 | E | The bench hazard arms: SCD30 write, re-trigger proof, erase and reboot | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 48g | HW_BENCH.067 | E | A commanded reboot over REST is attributed and bounded, waited for pas | red at W1: bench_no_task_ended_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.072 | E | Captive DNS, REST and client faults over the hotspot: every check prov | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.073 | E | Stage 6 runs last by marker; the flip back is a test of its own | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R3 |
| 48g | HW_BENCH.076 | E | Header, outage and flap tests: one recovery helper, catalog codes | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.077 | E | Network-degradation tests watch the whole fault window and make NTP ac | red at W1: bench_no_task_ended_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.078 | E | NTP retry and garbage-server tests prove the fault reached the DUT | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.079 | E | The connected-socket spoof lands while the DUT still waits | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.083 | D1 | Every reset code proven on the bench through `/status` | red at W1: bench_restores_serving, device_script_facts; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_BENCH.086 | E | Config pushes repair leftovers; the SCD30 Altitude question is measure | red at W1: level_containment, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 48g | HW_BENCH.088 | D1 | The system commands over REST: reset with save and restore, erase with | red at W1: device_script_facts, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 48g | HW_BENCH.091 | A | `TwinBoard`: `Board`'s API over the Unix-port twin | its L0 case red at the base (device_script_gc_threshold) |
| 48g | HW_BENCH.092 | A+LEAD | The twin-first record of every instrument | test_twin_record (M.TSC.219): every instrument has an entry with current hashes; red until the lead writes the record after W2 (expected) |
| 48g | HW_BENCH.101 | D1 | Rung steps judged against `/status`; WS2812 timing cited from its data | its L0 case red at the base (device_script_rig_parking) · parked R2 |
| 48g | HW_BENCH.104 | D1 | The first flash builds the bench board's own image | hub AST rule (M.TSC.026 (e)): `uv run` lists carry --no-sync; collect-only of tests_hardware/manual imports; harness.bench_device() used, no device literal (test_no_variant_literals row shrinks, lead) · parked R0/R7 |
| 48g | HW_DEV.003 | A+D1+D2+E | Shared script code lives in `_shared/`, inlined at render | B's guards red on the script at W1: hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.005 | D2 | Reader loops: one parameterised loop per chip, yielding every round | B's guards red on the script at W1: hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.006 | D1+D2 | A chunk-using script clears its chunk after setup and in `finally` | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.009 | D1+D2+E | Full-system scripts: required watchdog, a scratch config directory, th | B's guards red on the script at W1: device_script_config_flush, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.010 | D1+D2+E+LEAD | Every instrument runs in the twin first | each wave-2 lane: TwinBoard run of each script it writes or changes at -1 and 32768 (pass, or the silicon-only reason it records for the lead's record); lead: test_twin_record green after the record run |
| 48g | HW_DEV.020 | B | The SCD30 prerequisite: check first, start at most once | its L0 case red at the base (persistence_write_marker_completeness) · parked R1 |
| 48g | HW_DEV.026 | D1 | Restart and escalation modes over the split supervisor, with a log ora | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.036 | D1 | The boot check reads DebugLevel and watches for boot lines; it writes  | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 48g | HW_DEV.039 | D1 | Both DebugLevel scripts are deleted | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.040 | B | Repair DebugLevel to the standard value, only on request | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.055 | D1 | Toolchain checks: the re-verify gated, the reflash through the one hel | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R4 |
| 48g | HW_DEV.069 | D2 | FRAM read-vs-write concurrency over declared regions | B's guards red on the script at W1: device_script_facts, device_script_fram_regions; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.073 | D1 | Capacity check: derived logger set, scratch config, required watchdog, | B's guards red on the script at W1: device_script_bench_facts, device_script_config_flush, device_script_rig_parking, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.080 | D2 | The flash bus-hazard module: one prerequisite, two owned writes, the n | red at W1: device_script_facts, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 48g | HW_DEV.081 | D2 | SCD30 read-vs-write concurrency that re-sends the value the chip holds | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 48g | HW_DEV.082 | D2 | SCD30 reader vs snapshotter: bounds and schema ranges from their sourc | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.083 | D2 | SCD30 × SGP40 interleave, plus the two participant rungs mid-traffic | B's guards red on the script at W1: device_script_facts, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.084 | D2 | The SCD30 writer restores the offset it found: two owned NVM writes | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 48g | HW_DEV.085 | D2 | ISL29125 config writes among sibling reads, through the shared loops | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.086 | D2 | General-call regression: yielding loops, bounded records, rendered bou | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.087 | D2 | ISL29125 interleave across its i2c1 neighbours | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.088 | D2 | BMP3xx read-vs-write concurrency gains the reset-and-re-apply rung | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.089 | D2 | ISL29125 read-vs-write concurrency, constants named | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.095 | D1 | The system commands on the bench board over USB | red at W1: level_containment, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 48g | HW_DEV.112 | LEAD | Both WiFi reconnect repro scripts are deleted | lead: already landed at U5 (c3df14e): both repro scripts, their pyproject entry, the README recipe and the flush-guard comment are gone; verify by grep |
| 48g | HW_DEV.113 | E | The WiFi radio re-init rung on silicon, no config write | B's guards red on the script at W1: device_script_config_flush, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 48g | HW_DEV.130 | D2 | Plausibility from the shared bounds; envelope gated as a write; confor | red at W1: device_script_facts, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3/R5 |
| 48g | HW_DEV.132 | D2 | Four raw-bus conformance probes | B's bench-facts guard red on the four new probes until each reads BENCH; test_chip_conformance's twin half (conformance.run_probe_on_twin at both stages) passes per probe · parked R1 |
| 48g | HW_DEV.150 | A | Read-only raw FRAM dump, the evidence primitive's board half | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 48g | HW_DEV.157 | B | The SCD30 prerequisite's three scripts | test_scd30_prerequisite (fake board) plus each script's TwinBoard run on the twin SCD30 (measuring and not-measuring plans) · parked R1 |
| 48g | SCR.022 | A | Record every hardware instrument's twin run | the case its TSC sibling names, red at the base |
| 48g | TOOL.030 | LEAD | One per-file exemption block: two scope groups, every entry live and r | lead: site files |
| 48g | TSC.073 | B | Config-flush guard: scratch files removed, retired scripts gone | new/changed cases red at the base: test_device_script_config_flush |
| 48g | TSC.075 | B | Raw FRAM scratch regions lie outside the production layout | new/changed cases red at the base: test_device_script_fram_regions |
| 48g | TSC.119 | B | The wear guard derives its classes and sees every way a test writes | new/changed cases red at the base: test_persistence_write_marker_completeness |
| 48g | TWIN.054 | A | Device-script runner: the plan, a recording watchdog, the GC stage, th | test_twin_board: a one-line script through TwinBoard returns its output; run_device_script exits non-zero on a raising script, red at the base (file absent) |
| 49 | DOCS.037 | X | The twin-first instrument row names the committed runner | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 50 | GEN.019 | A | Device generation: expected facts, both boot entries, compile check | test_buildgen_generate (M.TSC.046): expected facts carry fram_backed_loggers per device, red at the base |
| 51 | HW_BENCH.013 | A | Reset, presence and exec state the raw-REPL facts; `soft_reset()` goes | pure removal of soft_reset() (no caller, grep); test_bench_harness_helpers's two-call _mpremote stubs green |
| 52 | HW_BENCH.017 | A | The ceiling instrument: tagged values, typed probe | test_request_timeout_ceiling reads the ceiling defaults by AST (unchanged values); test_tunables_register red until X's Part N rows (expected, relayed) |
| 53 | HW_BENCH.021 | A | Workaround comments name defect, bound and removal; owner tag restored | comment-only plus OF-11 (tcpdump stderr): a test_bench_control_restore case — a failing capture start raises naming tcpdump/sudo, red at the base |
| 54 | HW_BENCH.023 | A | The single radio never scans while it hosts the AP | test_bench_control_restore: is_ssid_visible() with the AP active raises HardwareTestFailureError, red at the base |
| 55 | HW_BENCH.037 | A | The website check names its device and reads every errcount group | B's test_tests_hardware_collect_matrix collects with the required device keyword; an A case: _errcount_keys(device) equals the union of the errcount groups for every derived device |
| 56 | HW_BENCH.063 | E | The boot order and the trigger spacing, observed on silicon | red at W1: bench_restores_serving, level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R5 |
| 57 | HW_BENCH.064 | E | One reader worker, counted floors, tagged bounds, derived checks | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 58 | HW_BENCH.068 | E | The burst, cold-boot and backup-reset tests claim only what they asser | red at W1: level_containment, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 59 | HW_BENCH.071 | E | The role-reversal fixture restores on every path and records what it p | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 60 | HW_BENCH.074 | E | The hammer and the soaks claim liveness, floor the readers, derive the | red at W1: bench_no_task_ended_completeness, level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R5 |
| 61 | HW_BENCH.080 | E | Config-fault tests repair leftovers and restore on every path | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R3 |
| 62 | HW_BENCH.081 | E | Ceiling, request and body-cap tests: traced drops expected, sets deriv | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 63 | HW_BENCH.084 | E | Every declared sensor is checked against its sourced bounds | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 64 | HW_BENCH.085 | E | The FRC readiness defaults measured on the bench | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R5 |
| 65 | HW_BENCH.095 | E | STA, NTP and DNS tests prove what they claim and report their recoveri | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 66 | HW_BENCH.096 | E | The WiFi radio re-init rung on silicon | red at W1: bench_restores_serving, device_script_facts, level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 67 | HW_BENCH.102 | D1 | Power-cycle steps: FRAM-backed evidence, restored writes, codes and th | B's wear guard manual branch (_MANUAL_PERSISTING_STEPS) red on the new power-cut step at W1, green when E's confirm() precedes it · parked R2 |
| 68 | HW_BENCH.103 | D1 | Accuracy steps cite the fitted part; M1 records the rig as evidence | its L0 case red at the base (device_script_bench_facts, device_script_rig_parking) · parked R2/R3 |
| 69 | HW_BENCH.105 | D1 | Hotspot steps match the firmware; the captive-portal item records its  | collect-only of the manual package; no PASS on Enter: a test_manual_runner_summary case (the captive-portal item counts as judged only with text), red at the base · parked R2 |
| 70 | HW_BENCH.116 | X | FRAM bullets: the chunk rule, the reset race, the codes, the flash-tie | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 71 | HW_BENCH.118 | X | "Chip conformance probes" replaces the ISL29125 probe section | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R1 |
| 72 | HW_BENCH.124 | X | The hotspot role reversal: ordered restore, stage-6 risk, serial repai | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 73 | HW_BENCH.125 | X | Prerequisites: commands per tier, sudo rules, picotool, uv | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R0 |
| 74 | HW_BENCH.129 | X | New "What the network-fault injections reach" and the DHCP limitation | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 75 | HW_BENCH.134 | X | FRAM capacity check: derived lists, no WP label | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 76 | HW_DEV.007 | D1+D2 | Raw FRAM addresses only inside declared scratch regions | B's guards red on the script at W1: device_script_fram_regions; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 77 | HW_DEV.062 | D1 | Error-log round trip with a test-band seed, cleared after | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 78 | HW_DEV.065 | D1 | Boot-window reset on the real chip, test-band seed, cleared after | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 79 | HW_DEV.066 | D1 | Busy-status lockout: its own chunk, facts, rewritten clean at the end | B's guards red on the script at W1: device_script_facts, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 80 | HW_DEV.067 | D1 | Write-protect round trip without the `override_pause` check | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 81 | HW_DEV.097 | D1 | `erasefram` with a recording watchdog proxy | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 82 | HW_DEV.098 | D1 | A shutdown step that never returns ends in the watchdog reset | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 83 | HW_DEV.099 | D1 | `reboot`/`bootloader` with the shutdown steps visible | B's guards red on the script at W1: hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 84 | HW_DEV.115 | D1 | Heap headroom with named thresholds; soak by duration; the timing scri | red at W1: device_script_facts, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R5 |
| 85 | HW_BENCH.046 | A | `heap_bounds.py`: the worst-case allocation defined once | B's product-copies guard; D1's flash/test_memory_stress imports heap_bounds (collect-only) |
| 86 | HW_BENCH.069 | E | The ceiling heap test names its threshold and its instrument values | red at W1: device_script_facts, level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 87 | HW_BENCH.087 | E | The serving sweep names its threshold and derives its routes | red at W1: device_script_facts; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 88 | HW_DEV.002 | A+D1+D2+E | Scripts report facts; the host gives the verdict | its L0 case red at the base (device_script_facts, device_script_gc_threshold, hardware_clones) |
| 89 | HW_DEV.032 | D1 | The fallback goes through the awaited `_reboot()` with its reset code | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 90 | HW_DEV.030 | D1 | Starvation tests: banner and action oracles, one closing reset, no `re | red at W1: device_script_facts; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 91 | HW_BENCH.127 | X | Bench traps: current facts, one closing reset, the REST-reboot trap | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 92 | HW_DEV.047 | D2 | Recovery: silence and baud desync, both timed against the resync bound | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 93 | HW_DEV.048 | D2 | The driver's read span, the folded POLLIN precondition and a readline  | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 94g | HW_BENCH.093 | E | The link under API load: counters read at the window's end, hazards an | red at W1: device_script_facts, level_containment (COVERS gains the harness family `uart_load`, scripts/_digital_twin_scenarios.py:1505 `uart_ring_under_concurrent_load`, beside `uart_link`), bench_restores_serving, bench_no_task_ended_completeness; collect-only clean · parked R1 |
| 94g | HW_DEV.045 | D2 | The UART flash module: both CRC modes, fail on a missing module, hazar | red at W1: device_script_facts; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 94g | HW_DEV.052 | D2 | UART comm hazards H1a/H1b/H2/H3 across the jumper | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 95 | HW_BENCH.014 | A | One `reflash()` helper: exit-249 retry only, passive end | test_bench_harness_helpers: _retryable_picotool_exit(249) true, any other false (M.TSC.026 (b)); reflash retries only 249 on a stubbed run, red at the base · parked R4 |
| 96 | HW_BENCH.082 | E | New bench rows: cap binding, the owner's OpenHAB mix, console starvati | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 97 | DOCS.086 | X | The wear rule: FRAM is not wear, the flag names, `resetconfig`, the in | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 98 | HW_BENCH.094 | E | The bench link suite in the CRC16 mode, behind `flash_cycle` | red at W1: level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R4 |
| 99 | HW_BENCH.119 | X | New "Reset codes proven on the bench" and "System commands" | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R1/R3 |
| 100 | HW_BENCH.128 | X | New "Workarounds" table | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 101 | HW_BENCH.132 | X | Measuring heap and serving under load: every figure names its threshol | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 102 | HW_DEV.001 | A+D1+D2+E | Board facts reach every script through one rendered `BENCH` dict | B's guards red on the script at W1: device_script_bench_facts, device_script_rig_parking; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 103 | HW_DEV.053 | E | L4: the serving board's initiator carries an echoed multi-chunk SET | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 104 | HW_DEV.093 | D2 | Three concurrent SGP40 measurements each get their own answer | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 105 | HW_DEV.100 | D1 | Read-only dump of every config file | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 106 | HW_DEV.101 | D1 | Write the saved config files back verbatim | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 107 | HW_DEV.106 | D2 | The scheduler probe forces the drop and counts it | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 108 | HW_DEV.074 | D2 | The deinit/singleton pin-move check on the TOML's buses, chunk left cl | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 109 | HW_DEV.107 | D2 | Alarm-pool exhaustion: header cites F.1, the count is `len(timers)` | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 110 | HW_DEV.108 | D2 | SCD30 RDY edge on the TOML's pin, new constructor shape | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 111 | HW_DEV.109 | D2 | The 2**24 boundary through the private float coercion | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 112 | HW_DEV.144 | D2 | The ISL29125 probe: constants from `BENCH`, settles named, run from th | B's guards red on the script at W1: device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 113 | HW_DEV.151 | D1 | The FRAM command and block holds against the UART poll floor | B's guards red on the script at W1: device_script_facts, device_script_fram_regions; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 114 | HW_DEV.154 | D1 | Four scripts that end in an attributed reset | B's guards red on the four new scripts until fact()/done() and BENCH; TwinBoard run: the runner reports the armed reset (exit code 3) for each · parked R1 |
| 115 | SCR.003 | LEAD | Timestamped evidence archive, last three kept per runner | lead: verify only: U7 landed scripts/_archive_evidence.py; A's evidence.py uses its API (A.U26.22) |
| 116 | SCR.005 | B | The hardware verdict from the run record | test_hardware_verdict: soak_duration/allow_multi_day_rollover/toolchain_reverify gate names (unset → accepted skip, set → fail), red at the base |
| 117 | SCR.028 | B | Generation, three passes and two single-file checks | typecheck.sh: its generator call carries --no-sync (grep); the lead's three mypy passes run it at the merge |
| 118 | SCR.030 | B | Flash runner: lower levels first, a floor the caller narrows | test_hardware_runners: the flash runner's renamed gate options, red at the base |
| 119 | SCR.065 | B | Firmware CLI: device TOML, no-autostart, lock, kept work dir, one erro | test_build_firmware: --device-toml builds the stage dir from the given TOML (tmp hostname lands in the staged module); a missing path fails before staging, red at the base |
| 120 | HW_BENCH.089 | E | The rollover is observed over REST on the tick-offset test image | red at W1: bench_no_task_ended_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R4/R5/R6 |
| 121 | DOCS.049 | X | Recipe "Tests per level": L0-L4, both GC stages, per device | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 122 | HW_BENCH.110 | X | Header: the levels by SPEC E.6.1's names, the bench board by data | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 123 | HW_BENCH.126 | X | Environment variables, Running, the soak durations and "Verify the ima | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 124 | SPEC.035 | X | B.11: building this project's firmware | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 125 | SPEC.085 | X | E.9: driver/DUT separation; the host-side scenario harness | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 126 | SPEC.089 | X | F.1 imports: the static-import rule and its named exceptions; `.frozen | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 127 | SPEC.090 | X | F.1 timers and the bus raise surface | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 128 | SPEC.109 | X | New F.9: standing workarounds for upstream defects, and what retires e | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 129 | SPEC.087 | X | Part F opens with the platform re-check; the one statement of the prac | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 130 | SPEC.146 | X | L.3: the device TOML schema and its checked key table | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 131 | TOOL.032 | LEAD | Main mypy pass: vendored Microdot stub, unixport shims, generated sour | lead: site files |
| 132 | TOOL.038 | LEAD | lwip_connection_counts: quoted includes, tagged floors, true comments, | lead: verify only: U21 landed it; A.U26.03's ensemble check calls check_lwip_ensemble() (micropython_overrides.py:275) from B's bench/conftest.py |
| 133 | TOOL.079 | LEAD | Host pass: scripts on the path, the strict flags, a true conftest reas | lead: site files |
| 134 | TSC.002 | A+B | No device-variant literal in `tests_scripts/` | new/changed cases red at the base: test_build_firmware, test_buildgen_generate, test_buildgen_validate, test_device_tomls, test_digital_twin_boot_contiguity, test_resolve_board_device, test_tests_hardware_conftest_constants |
| 135 | TSC.021 | A | Header, imports and the device loop | new/changed cases red at the base: test_bench_harness_helpers |
| 136 | TSC.023 | A | Errcount oracles fail closed; the clear saves first | new/changed cases red at the base: test_bench_harness_helpers |
| 137 | TSC.025 | A | Boot, crash and fault-window observers pinned against `src/` | new/changed cases red at the base: test_bench_harness_helpers |
| 138 | TSC.026 | A | Wrapper contracts: DebugLevel parse, picotool retry, iptables listing, | new/changed cases red at the base: test_bench_harness_helpers |
| 139 | TSC.027 | B | The no-task-ended guard covers methods, helpers, fixtures and flash | new/changed cases red at the base: test_bench_no_task_ended_completeness |
| 140 | HW_DEV.011 | B+D1+D2 | Flash modules: facts, scenarios, a serving board at the end | its L0 case red at the base (bench_no_task_ended_completeness, bench_restores_serving, device_script_facts) |
| 141 | HW_DEV.025 | D1 | The restart test asserts the restart facts and the log entries | red at W1: device_script_facts, level_containment; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1 |
| 142 | TSC.031 | B | Staged modules follow the import-seeded set and the staging split | new/changed cases red at the base: test_build_firmware |
| 143 | TSC.032 | B | CLI cases: device TOML, no-autostart, toolchain lock, record, work dir | new/changed cases red at the base: test_build_firmware |
| 144 | TSC.046 | A | `main()`, collectors and expected facts pinned per device | new/changed cases red at the base: test_buildgen_generate |
| 145 | TSC.056 | A | Device-table, field and range rejections | new/changed cases red at the base: test_buildgen_validate |
| 146 | TSC.074 | B | A script's `ConfigManager` on a production file takes the full schema | new/changed cases red at the base: test_device_script_config_schemas |
| 147 | TSC.076 | B | Every heap-measuring script sets and reports its GC stage, any spellin | new/changed cases red at the base: test_device_script_gc_threshold |
| 148 | TSC.078 | B | A long device script feeds the watchdog in short steps | new/changed cases red at the base: test_device_script_watchdog |
| 149 | HW_DEV.004 | A+D1+D2+E | One watchdog helper: armed once, fed every ≤ 2 s | its L0 case red at the base (device_script_watchdog, hardware_clones) |
| 150 | HW_DEV.046 | D2 | The exchange script takes its pair and CRC mode from `BENCH` | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 151 | HW_DEV.049 | D2 | The raw-UART stall script is deleted | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 152 | HW_DEV.050 | D2 | Idle poll rate: the pair stated explicitly from `BENCH` | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_rig_parking; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 153 | HW_DEV.051 | D2 | The loaded link: echo-checked multi-chunk SETs, both CRC modes, no rec | B's guards red on the script at W1: device_script_facts, device_script_gc_threshold, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 154 | HW_DEV.063 | D1 | The seed lands a reset on a named seam and seeds a nonce-chosen sequen | B's guards red on the script at W1: device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 155 | HW_DEV.064 | D1 | The verify accepts only the three outcomes of this run's sequence, the | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 156 | HW_DEV.068 | D1 | Pause gating proven by unpaused read-back; the waiter-task unpause; bo | B's guards red on the script at W1: device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 157 | HW_DEV.070 | D2 | CS hijack: two new rungs (dropped WREN, chip lost), regions declared,  | B's guards red on the script at W1: device_script_facts, device_script_fram_regions, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 158 | HW_DEV.071 | D2 | The raw reset race claims only what the part guarantees | B's guards red on the script at W1: device_script_fram_regions, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 159 | HW_DEV.072 | D2 | The raw verify accepts the old pattern or a torn prefix, nothing else | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 160 | HW_DEV.090 | D2 | The live sweep: addresses from `BENCH`, a recovery step, heater-off, s | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 161 | HW_DEV.061 | D1 | Chunk round trip: `BENCH` wiring, the part's RDID as a fact, chunk cle | B's guards red on the script at W1: device_script_bench_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 162 | HW_DEV.060 | D1 | FRAM flash module: facts per script, five reset seams, the command-hol | red at W1: device_script_facts (RESULT_RE gone, parse_facts), level_containment (COVERS gains `fram_crash_points` for the five-seam reset-race test, U25 docs-lane fact, tests/test_digital_twin_fram_crash_points.py exists), persistence_write_marker_completeness; collect-only clean; `--twin` run of the module · parked R1 |
| 163 | HW_DEV.091 | D2 | A held SDA made on silicon, cleared by the bus rung; the boot-time cle | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 164 | HW_DEV.092 | D2 | A lone BMP3xx keeps its state through general calls | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 165 | HW_DEV.110 | D2 | Record the radio's reaction to malformed country codes | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 166 | HW_DEV.105 | D2 | Electrical/timing module: rollover moves to the bench, soak by duratio | red at W1: bench_restores_serving; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R5 |
| 167 | HW_BENCH.131 | X | Known assumptions and open findings: current facts only | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 168 | HW_DEV.111 | E | The country/hostname edge script is deleted | B's guards red on the script at W1: device_script_bench_facts, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 169 | HW_DEV.116 | D1 | Headroom after the full boot batch, scratch config, facts, shared prob | B's guards red on the script at W1: device_script_bench_facts, device_script_config_flush, device_script_facts, device_script_gc_threshold, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 170 | HW_DEV.117 | D1 | Heap layout over the generated boot order, without entering the superv | B's guards red on the script at W1: device_script_config_flush, device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 171 | HW_DEV.118 | D1 | The flash wrapper asserts the twin's high-band bound on both arms | new flash/test_heap_layout.py (A.U25.61's flash check, left to U26 by U25): reads _HIGH_BAND_BLOCKS_MAX from tests_scripts/test_digital_twin_boot_contiguity.py:74 by ast; red at W1 on level_containment/device_script_facts; `--twin` run of both arms (live within the bound, suppressed over it) · parked R1 |
| 172 | HW_DEV.119 | E | Allocation need per source: rendered device, scratch config, routes fr | B's guards red on the script at W1: device_script_config_flush, device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 173 | HW_DEV.120 | E | Serving at the default GC stage: rendered device, `main(watchdog=…)`,  | B's guards red on the script at W1: device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 174 | HW_DEV.121 | E | Heap under the connection ceiling: rendered device, `main(watchdog=…)` | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 175 | HW_DEV.122 | D1 | The routine no-yield stretches timed on the chip | B's guards red on the script at W1: device_script_facts, device_script_gc_threshold, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 176 | HW_DEV.124 | D1 | Loop lag of the shipped `main()` under in-process load, in its own FRA | B's guards red on the script at W1: device_script_facts, device_script_fram_regions, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 177 | HW_DEV.125 | D1 | The deepest await chain's C-stack peak on silicon | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 178 | HW_DEV.136 | D2 | SGP40 cycles counted over ten minutes of the real task graph | B's guards red on the script at W1: device_script_config_flush, device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R5 |
| 179 | HW_DEV.137 | D2 | SCD30 plausibility read: values out, bounds host-side | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 180 | HW_DEV.138 | D2 | BMP3xx plausibility read: values out, comment names the divider | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 181 | HW_DEV.140 | D2 | VOC algorithm quality on the TOML's bus with its timeout; shared fixed | B's guards red on the script at W1: device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 182 | HW_DEV.141 | D1 | SGP40 FRAM backup/restore with the TOML's bus timeout and a cleared ch | B's guards red on the script at W1: device_script_facts, device_script_watchdog; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 183 | HW_DEV.142 | D2 | The envelope: scratch config flushed and removed, rig parked, private  | B's guards red on the script at W1: device_script_config_flush, device_script_facts, device_script_rig_parking, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 184 | HW_DEV.037 | D1 | The write phase removes a leftover first and spends exactly one owned  | B's guards red on the script at W1: device_script_config_flush, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 185 | HW_DEV.035 | D1 | Config persistence across a reset: one owned write, cleanup on every p | red at W1: device_script_facts, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R3 |
| 186 | HW_DEV.038 | D1 | The read phase reports the marker and removes the file in `finally` | B's guards red on the script at W1: device_script_config_flush, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 187 | HW_DEV.153 | D1 | Float idempotence and a reload through a scratch manager | B's guards red on the script at W1: device_script_bench_facts, device_script_config_flush, device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 188 | HW_DEV.155 | D1 | Power cut during a scratch config write: the writer and the read-back | its L0 case red at the base (device_script_config_flush, device_script_facts) · parked R2 |
| 189 | HW_DEV.156 | D2 | Record how the SCD30 treats a bad-CRC and a zero interval write | B's guards red on the script at W1: device_script_facts; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 190 | HW_DEV.159 | D2 | Interrupts off on the receiving board: no frame lost within the ring's | B's guards red on the script at W1: device_script_bench_facts, device_script_facts, device_script_watchdog, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 191 | HW_DEV.160 | D2 | The DMA receive ring on silicon: interrupts off, a soft reset during t | red at W1: persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 192 | DOCS.064 | X | "Real-hardware work still owed": one row per measurement, in round ord | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 193 | HW_BENCH.115 | X | The UART bullets state the link's current coverage | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 194 | HW_BENCH.133 | X | The ten "passes" become topic sections | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 195 | SPEC.083 | X | E.6.6: the one level-containment exception list | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 196 | SPEC.137 | X | J.7: the loopback model, both CRC modes, the tier map, the poll constr | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 197 | SPEC.156 | X | Part N rows: every tagging action's rows, at the end state | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 198 | SPEC.097 | X | F.3 the timing budget table | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 199 | SPEC.108 | X | F.8 `machine.UART` on rp2: the standing facts (HEAD F.5.7-F.5.9) | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 200 | TSC.077 | B | NeoPixel construction sits inside a parking `try` | new/changed cases red at the base: test_device_script_rig_parking |
| 201g | HW_BENCH.121 | X | Device-script habits: from four to the full set | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 201g | HW_BENCH.122 | X | New "Recovery rungs on silicon" | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R1/R2 |
| 202 | HW_BENCH.111 | X | New "The dev bench": wiring and chips, bench state, read from the boar | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 203 | HW_BENCH.112 | X | Host network: the manual br0 recipe as the installer runs it, switch a | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R0 |
| 204 | HW_BENCH.113 | X | What each tool writes to the board; testing a driver by hand | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 205 | HW_BENCH.114 | X | Rig sections: the NeoPixel sweep rig, the ISL29125 rig facts, the gate | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R2 |
| 206 | HW_BENCH.120 | X | New "Bench facts": a dated table read from the bench | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R0/R1/R2 |
| 207 | HW_DEV.008 | D1+D2 | The NeoPixel rig is parked on every exit | B's guards red on the script at W1: device_script_rig_parking; TwinBoard run at -1 and 32768 passes or records a silicon-only reason |
| 208 | HW_DEV.139 | D2 | ISL29125 plausibility read: rig parked, lux out, priming kept read-onl | B's guards red on the script at W1: device_script_facts, device_script_rig_parking; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 209 | HW_DEV.143 | D2 | Lighting scenarios: dead constant gone, private pixel, catalog codes,  | B's guards red on the script at W1: device_script_facts, device_script_rig_parking, hardware_clones; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R3 |
| 210 | HW_DEV.145 | D2 | ISL29125 INT edge: PRST verdict kept, rig parked, unit suffixes | B's guards red on the script at W1: device_script_facts, device_script_rig_parking; TwinBoard run at -1 and 32768 passes or records a silicon-only reason · parked R1 |
| 211 | HW_DEV.131 | D2 | One conformance gate per bus chip, real vs twin | red at W1: level_containment, persistence_write_marker_completeness; `pytest --collect-only` clean; `--twin` where TwinBoard runs it · parked R1/R3 |
| 212 | SPEC.077 | X | E.2, E.2.1, new E.2.2 and new E.2.3: microtest, per-device runs, test  | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 213 | SPEC.160 | X | E.2.3, E.6.6 and K.10 gain the test-standard items no Part E change ca | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 214 | TSC.079 | A | Device-TOML checks validate.py does not make | new/changed cases red at the base: test_device_tomls |
| 215 | TSC.081 | B | The contiguity probe follows the setup list now inside `SystemService` | new/changed cases red at the base: test_digital_twin_boot_contiguity |
| 216 | TSC.098 | B | The import graph: no cycles, no driver-to-driver edge, no dynamic impo | new/changed cases red at the base: test_import_graph |
| 217 | TSC.102 | B | Level containment is checked, not stated | new/changed cases red at the base: test_level_containment |
| 218 | TSC.137 | B | The hardware levels collect under every option with nothing attached | new/changed cases red at the base: test_tests_hardware_collect_matrix |
| 219 | SPEC.082 | X | E.6 to E.6.5: the level ladder, adapters, the harness, role reversal,  | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 220 | SPEC.065 | X | C.8: the general-call reset, the hazard standing rule, the SCD30 budge | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 221 | SPEC.161 | X | The renamed hardware gates in SPEC text | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 222 | HW_BENCH.130 | X | Persistence-write gating: one budget table, the checks, the flash-cycl | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) · parked R1/R3 |
| 223 | TSC.145 | A | SPEC L.3's key table equals the validator's | new/changed cases red at the base: test_toml_schema_contract |
| 224 | TSC.155 | B | The watchdog feed sites are exactly the pinned set | new/changed cases red at the base: test_watchdog_feed_sites |
| 225 | TSC.165 | B | Suite helpers: failure events, signals, strict readers, a missing log  | new/changed cases red at the base: test_digital_twin_ci_suite_errcount |
| 226 | TSC.166 | A | The heap-map parser reads the shared dump | new/changed cases red at the base: test_heap_map_parser |
| 227 | TSC.171 | A | The harness resolver keeps its seven cases | new/changed cases red at the base: test_resolve_board_device |
| 228 | TSC.173 | B | Hardware conftest constants: renamed schema, derived password | new/changed cases red at the base: test_tests_hardware_conftest_constants |
| 229 | TSC.175 | A | The derived device set gains the property queries the tests share | test_bench_device: _devices.bench_device()/devices_with() over a tmp devices/ (zero/two flagged), red at the base |
| 230 | TSC.178 | A | Bench network restores are proven by state; the host access path is un | new/changed cases red at the base: test_bench_control_restore |
| 231 | TSC.179 | A | Exactly one TOML names the bench board | new/changed cases red at the base: test_bench_device |
| 232 | TSC.180 | B | The bench tier proves the board runs this round's image | new/changed cases red at the base: test_board_image_fixture |
| 233 | TSC.185 | B | Device scripts take board facts from `BENCH` only | new/changed cases red at the base: test_device_script_bench_facts |
| 234 | TSC.186 | B | Device scripts report facts; the host gives the verdict; loops yield | new/changed cases red at the base: test_device_script_facts |
| 235 | TSC.187 | B | No new clone group in the hardware levels | new/changed cases red at the base: test_hardware_clones |
| 236 | TSC.188 | B | Product values the hardware levels copy are read or cited | new/changed cases red at the base: test_tests_hardware_product_copies |
| 237 | TSC.194 | A | Evidence is saved before anything clears it | new/changed cases red at the base: test_evidence_snapshot |
| 238 | TSC.198 | A | A transient mpremote retry never re-runs a script | new/changed cases red at the base: test_harness_mpremote_retry |
| 239 | TSC.203 | D1 | The manual runner can fail and ends with the block | new/changed cases red at the base: test_manual_runner_summary |
| 240 | TSC.212 | B | The SCD30 prerequisite starts measurement at most once | new/changed cases red at the base: test_scd30_prerequisite |
| 241 | TSC.216 | B | Collecting the hardware levels yields a run record with the gate flags | new/changed cases red at the base: test_tests_hardware_run_record |
| 242 | TSC.218 | A | `TwinBoard` keeps `Board`'s shape | new/changed cases red at the base: test_twin_board |
| 243 | TSC.219 | A | Every hardware instrument has a current twin-run record | new/changed cases red at the base: test_twin_record |
| 244 | TSC.226 | A | The bench's route set is the REST reference's, `/notification` include | new/changed cases red at the base: test_bench_harness_helpers |
| 245 | TWIN.013 | LEAD | SCD30 fake: measuring status, argument CRCs, power-up reset, volatile  | lead: verify only: U25 landed the SCD30 fake's measuring state and 0x0010/0x4600/0x0202 (digital_twin/_scd30_chip.py:39-47); B's three prerequisite scripts run on it |
| 246 | TWIN.016 | A | Twin HTTP client: refusal vs incomplete response, typed stream, timeou | verify only: U25 landed the twin client's shape (CeilingRefusedError, drained, read_body); test_http_client_shape_parity green once A's hardware client matches |
| 247 | TWIN.059 | X | New "Fidelity table" section | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 248 | TWIN.074 | X | New "Running device scripts in the twin" section | doc: test_citations, test_decision_vocabulary, test_comment_block_cap green on the touched lines (and any test that reads the section) |
| 249 | TWIN.102 | LEAD | Twin bus-hazard tier: devices from data, real recovery rungs, general  | lead: verify only: U25 landed the L2 SCD30 write arm (A.U26.32's twin counterpart exists); E writes the L4 arm |
| 250 | TWIN.120 | LEAD | ISL29125 fake tests: bounded PRST count, cited constants, grouped cons | lead: verify only: U25 landed the ISL29125 fake tests; A.U26.53's L2 equivalent is 'unchanged' |
