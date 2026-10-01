# A-C merge HW_DEV (HEAD 16e841a)

Scope: CLUSTERS.md "## HW_DEV" — `tests_hardware/flash/` (the flash-tier pytest files, L3) and
`tests_hardware/device_scripts/` (the MicroPython scripts the harness pushes to the board, checked by the main mypy
pass), every file there at HEAD and every new file an action creates there. Constituents per file: the index's
`by_file` actions plus every action whose Site, Change or Blast slot names the file or its basename (a script of 1,545
action blocks over `audit/actions/*.md`: 310 blocks hit, 126 through the index, 184 beyond it, each read at the hit;
blocks naming only "device scripts" in general were read too). `git diff --stat 8e36b1e 16e841a -- tests_hardware` is
empty, so every line cited holds at HEAD `16e841a`. Read in full at HEAD: all 11 `flash/*.py` and all 58
`device_scripts/*.py` (7,128 lines).

**Hardware rule, every change below.** Nothing here runs: a `test`/`hardware` change is written and checked board-free
(L0, mypy, `--collect-only`, twin run first, A.U26.05); it executes on silicon only in the phase-C round its "Round"
line names (A.C.02-A.C.09, inventory H01-H83 of `audit/actions/C.md`), under the owner's go-ahead given in that
round's own conversation (CLAUDE.md go-ahead rule; A.C.01 (1)). Only the bench board named by data
(`[device].bench`, today `dev`, A.U26.01) is flashed, with a dev-native image from its own TOML; `wozi` is never
flashed and no script carries a wozi pin (A.C.01 (5); CLAUDE.md WoZi rule).

## Conventions every merged change applies

The same B0-B9 conventions as `M_HW_BENCH.md` (B0 lines/units/rounds, B1 U10 rename sweep, B2 host annotations, B3
docstrings to comments, B4 `@tunable` tags, B5 permanent text, B6 imports, B7 ordering last, B8 `--no-sync`/no `Any`,
B9 wear and evidence) apply here unchanged and are not repeated per change; the device-script and flash-test contracts
below are this cluster's own and are written once, each as a merged change (M.HW_DEV.001-.012) that the per-file
changes cite.

- **B0** Line numbers are HEAD `16e841a`. Units run U0 (B0), U1-U8 (B1), U9-U34 (B2), U35-U37 (B3-B5), then phase-C
  rounds R0-R7. A merged change lands in the latest unit of its constituents unless stages are listed. "Round" names
  the C round (and inventory row) whose suite run first executes the change on silicon. Every action citing a pinned
  upstream line is re-checked against the refreshed pin (OR129.a (5), AC_NOTES 34 second).
- **B1** (renames, A.U10.35/.37/.38/.39/.43/.44 with M_SRC_SENS GAP-5 and GAP-8): device scripts and flash tests use
  the end-state names — modules `asy_system_service`, `asy_config_manager`, `asy_crc_checks`, `asy_print_log`,
  `asy_base_classes`, `asy_framing_codecs`; classes `FRAMManager`, `FRAMChunk*`, `WifiService`, `UARTComm`,
  `UARTLinkDriver`, `CRCBase`/`CRCPass`, `BMP3XX_Reader`; private attributes (`_pixel`, `_overlay_*` for the
  NeoPixel overlay state, `_trigger_timer`, `_cfg_schema` read through `get_cfg_schema()`, A.U24.61), starters
  `start_asy_<what>()`, task coroutines `_<what>_loop`, `trigger_s`. Device scripts are in the main mypy pass, so the
  sweep finds every reader by `attr-defined`/`name-defined` errors (A.U10.35's method); flash tests by `grep -rnw`.
- **B3** applies to `flash/*.py` and to every device script's functions: function/class docstrings become `#` blocks
  ≤ 3 prose lines (A.U10.34); module docstrings stay as the one header (≤ 3 lines, A.U27.28's counting).
- **B4** U8C/U8C2 tags (A.U8.02 grammar): every tagged literal becomes the module constant its row writes; a literal a
  later change deletes, moves host-side or replaces by a `BENCH` read loses its tag at that site (named per change; the
  row's site list follows, SPEC Part N — carried by SPEC as A.U8.01's table). U8C's "deferred U26" items: U26 made no
  keep-or-poll decision for any device-script sleep (its G7/R23 ledger row reads "U25/U8 parts: NO-CLAUSE"), so each is
  kept and becomes the named constant with the provisional ID U8C's table gives (U8C's own "if kept" branch; agent
  decision AD-1).

## Cluster-wide merged changes (the two contracts)

### M.HW_DEV.001 Board facts reach every script through one rendered `BENCH` dict
- **From**: A.U26.44 (3)(4), A.U26.49 (bounds as render extras), A.U26.48 (3) (`WORST_CASE_ALLOCATION` as an extra),
  A.S0930.05 (`crc` fact), A.U26.23 (3) (`fram_wired`/`fram_backed_loggers`), A.U8.06/A.U8C.91-.95 (the `dev.uart_*`
  mirrors), A.U27.25 (blast: `pyproject.toml:363, 370` "one static `import sensortask_dev`" texts).
- **Site**: new `tests_hardware/device_scripts/bench_facts.pyi`; every device script that constructs a bus or
  peripheral from literals (grep `I2C(|SPI(|UART(|NeopixelDriver(|Pin(`: 39 at HEAD), imports `sensortask_dev` (six
  scripts, 25 sites) or copies a driver constant (`_MODE_RGB = 0x05` at `bus_concurrency_scd30_write_vs_siblings.py:15`,
  `isl29125_cross_device_concurrency.py:16`, `isl29125_mock_conformance_probe.py:20`; the address table and bus tuple at
  `bus_topology_autodetect_and_hazard_sweep.py:23, 30`).
- **Change**: (1) `bench_facts.pyi`: `class BenchFacts(TypedDict, total=False)` with one key per fact
  `bench_facts.build()` returns (M.HW_BENCH.041) and per render extra a script reads (`SEAM`, `NONCE`, `CRC_MODE`,
  `COMMAND`, `bounds`, `worst_case_allocation`, `dump_size`, …), nested `TypedDict`s for `bus`/`instances`;
  `total=False` because extras are per script. (2) Each such script holds exactly one line `BENCH: "BenchFacts" = {}  #
  rendered by tests_hardware/harness.py` after an `if TYPE_CHECKING: from bench_facts import BenchFacts`, and reads
  every pin, bus parameter, address, UART pair, copied register constant and per-run value from it:
  `bus = BENCH["bus"]["i2c1"]` → `asy_i2c_driver.I2C(bus["id"], bus["scl_pin"], bus["sda_pin"],
  frequency=bus["frequency"], **({"timeout": bus["timeout"]} if "timeout" in bus else {}))` (a TOML without `timeout`
  keeps rp2's default); `import sensortask_dev` → `device = __import__(BENCH["device_module"])`; comments "sensortask_dev's
  own …" → "the generated device module's …". (3) Tags at those sites (B4): every `dev.uart_poll_wait_ms`,
  `dev.uart_poll_idle_ms`, `dev.uart_rxbuf` mirror (A.U8C.91-.95) is replaced by its `BENCH` read and loses the tag;
  the TOML is the source those Part N rows already name.
- **Resolved**: A.U26.44 allows "take … or are pinned" (G1/R40); rendering is the one form here because the module name
  cannot be pinned (OR78.a). A.U31.05/.06's "import frozen `sensortask_dev`" texts read `BENCH["device_module"]`
  (OR78.a postdates neither's wording; the owner row governs).
- **Unit**: U26 (the scripts written by later units are born in this form).
- **Depends**: M.HW_BENCH.012 (`render_device_script()`), M.HW_BENCH.041 (`bench_facts.build()`), A.U20.28 (`ast`
  address reader), A.S0930.01 (`crc` key).
- **Blast carried by**: the L0 guard `tests_scripts/test_device_script_bench_facts.py` (no pin/bus literal, no
  `import sensortask_`, no copied driver constant; every key read exists for every `bench = true` TOML) → A.U26.44
  (TSC); the `.pyi` key set equal to `bench_facts.build()`'s keys plus the declared extras → GAP-D1 (TSC);
  `pyproject.toml:363, 370` comments → A.U26.44/A.U27.25 (TOOL); README habit "take every board fact from `BENCH`" →
  M.HW_BENCH README change; SPEC E.6.5 → A.U26.44 (SPEC).
- **Kind**: code, test

### M.HW_DEV.002 Scripts report facts; the host gives the verdict
- **From**: A.U26.68, A.U26.48 (1) (`GC_THRESHOLD=` becomes a fact), A.U7.16 (blast: run record), OR20.a (owner,
  2026-09-25); every later action whose text says a new script "prints `RESULT: PASS/FAIL`" (A.U11.21, A.U15.20,
  A.U16.07, A.U26.07, A.U26.34, A.U26.82, A.U31.05, A.C.14, A.C.15, A.C.17, A.S0930.05/.28/.29/.39).
- **Site**: every device script printing `RESULT:` (53 at HEAD) and every host test that runs one; new
  `tests_hardware/device_scripts/_shared/facts.py`.
- **Change**: (1) `_shared/facts.py` (included, M.HW_DEV.003): `fact(key: str, value: object) -> None` prints
  `FACT <key>=<json.dumps(value)>`; `errors(name, total, first)` prints the bounded failure record as one fact
  (`{"total": n, "first": [..≤5]}`); `done() -> None` prints `DONE`. (2) Every script keeps its driving on the board and
  ends with `done()`; every pass condition it computes today moves into its host test as an assertion over
  `harness.parse_facts(output)`, bounds read from their single source (`plausibility_bounds.py`, `heap_bounds.py`,
  the script's own `@tunable` constants passed as facts); a script whose flow branches on an intermediate result keeps
  the branch and reports it as a fact. (3) The GC stage each script sets is reported as `fact("gc_threshold", n)`;
  `tests_scripts/test_device_script_gc_threshold.py`'s marker constant (`:16`) follows (A.U26.68 blast).
- **Resolved**: every later action that writes "prints `RESULT:`" for a new script is read as "reports a fact the host
  asserts" — G7/R19 and OR20.a govern every script, and A.U26.68's L0 ban fails any `print("RESULT:` left; each new
  script below is written in fact form, no `RESULT` stage first.
- **Unit**: U26 (scripts of later units born in this form).
- **Depends**: M.HW_BENCH.012 (`parse_facts`), M.HW_DEV.003.
- **Blast carried by**: the `print("RESULT:` ban and "every runner calls `parse_facts`" → A.U26.68 (TSC); `parse_facts`
  L0 → A.U26.68 (TSC); the eight flash modules' helpers go → M.HW_DEV.011; SPEC E.9 → A.U26.68 (SPEC).
- **Kind**: test

### M.HW_DEV.003 Shared script code lives in `_shared/`, inlined at render
- **From**: A.U26.78 (1)(3), A.U26.69 (the shared failure shape), A.U27.25/A.U27.24 (blast: the mypy pass holds
  `tests_hardware/device_scripts`).
- **Site**: new `tests_hardware/device_scripts/_shared/` (`__init__.py` empty; `facts.py`, `watchdog.py`,
  `heap_probe.py`, `map_dump.py`, `fixed_source.py`, `settle.py`, `bus_reader_loops.py`); the clone sites
  `heap_headroom_after_full_system_build.py:42, 73, 83`, `heap_layout_after_full_boot_sequence.py:78, 106, 116`,
  `serving_at_default_gc.py:39`, `heap_under_connection_ceiling.py:21`, `sgp40_voc_algorithm_quality.py:24`,
  `sgp40_fram_backup_restore.py:22`, `uart_crossover_exchange.py:60`, `uart_crossover_recovery.py:91`.
- **Change**: (1) Each clone group becomes one `_shared/<name>.py` holding the one body (the heap probe
  `largest_block()`/`report_checked()`, `dump_map()`; the map `dump()`; `FixedSource`; `settled()`). (2) A script that
  uses one carries the line `# @include _shared/<name>.py` at module top (replaced by the file's text at render,
  M.HW_BENCH.012) plus `if TYPE_CHECKING: from _shared.<name> import <names>` so the main mypy pass, which checks
  `device_scripts/` as a package root, resolves the names; at run time the inlined text binds them. (3) Included files
  import only MicroPython modules and `src/` modules, carry a ≤ 3-line header, and are never run on their own.
- **Resolved**: A.U26.78 names the include mechanism but not how mypy sees an inlined name; the `TYPE_CHECKING` import is
  agent decision AD-2 (the import never runs on the board: `TYPE_CHECKING` is false there, and `typing` is the stub
  every script already imports for annotations).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.012 (render-time include), M.HW_DEV.002.
- **Blast carried by**: the clone check over `tests_hardware/` (include files excluded) → A.U26.78 (3) (TSC); checks
  reading rendered vs raw sources stated per check → A.U26.78 (TSC); the twin renders includes → M.HW_BENCH.091; README
  habit "shared code lives in `_shared/`" → M.HW_BENCH README change.
- **Kind**: test

### M.HW_DEV.004 One watchdog helper: armed once, fed every ≤ 2 s
- **From**: A.U8.08 (the 28 literal and 3 named `WDT(timeout=8000)` device-script sites), the `wdt.timeout_ms` cells of
  A.U8C.58-.80, .82, .84, .87, .88, .90 and A.U8C.66/.69/.77 (mirror rows), A.U26.61 (≤ 2 s feeds; checked), A.U20.02
  (blast: `wdt.timeout_ms` moves to `codegen.py`'s `_WDT_TIMEOUT_MS`).
- **Site**: new `tests_hardware/device_scripts/_shared/watchdog.py`; the 31 constructing sites (grep `WDT(` in
  `device_scripts/`); every `sleep`/`sleep_ms` over 2 s in a script that can outlast 8 s.
- **Change**: (1) `_shared/watchdog.py`: `# @tunable wdt.timeout_ms = 8000` (mirror of the product value, Part N row
  `wdt.timeout_ms`) above `_WDT_TIMEOUT_MS = 8000`; `arm() -> machine.WDT` re-arms the watchdog the harness started
  (rp2 allows one instance; re-construction updates the timeout, `ports/rp2/machine_wdt.c:38, 47-59`, v1.29.0);
  `_FEED_STEP_MS = 2000` (`l3.device_script_feed_step_ms`, B4) and `async def fed_sleep_ms(wdt, total_ms)` /
  `def fed_wait_ms(wdt, total_ms)` that sleep in steps ≤ `_FEED_STEP_MS` with a feed between. (2) Every script's
  `machine.WDT(timeout=8000)` (and the named copies `_WDT_TIMEOUT_MS` in `fram_error_log_reset_race_seed_and_race.py:17`,
  `fram_pause_unpause_and_gating.py:20`, `system_service_restarts_a_real_dead_task.py:11`) → `wdt = arm()`, the comment
  "matches src/system_service.py's own production value" goes (the tag says it). The two starvation scripts keep their
  own short `l3.starvation_wdt_ms` arming (their subject is the reset). (3) Every wait over 2 s goes through the helper.
- **Resolved**: A.U8.08 tags all 31 sites; collapsing them to one mirror site is the same row with one site — the
  site list in SPEC Part N's `wdt.timeout_ms` row becomes `_shared/watchdog.py` (GAP-D2 for SPEC). A.U26.61's check (a)
  reads the helper's step constant.
- **Unit**: U26 (the U8 tags of these sites land with it; U8 tags the shared site once).
- **Depends**: M.HW_DEV.003; A.U8.01/.02 (grammar).
- **Blast carried by**: `tests_scripts/test_device_script_watchdog.py` (no single sleep > 2 s; a script whose host
  timeout exceeds 8 s arms and feeds) → A.U26.61 (TSC); Part N `wdt.timeout_ms` site list → GAP-D2 (SPEC); README habit
  "feed the watchdog every ≤ 2 s" → A.U26.61 (HW_BENCH).
- **Kind**: test

### M.HW_DEV.005 Reader loops: one parameterised loop per chip, yielding every round
- **From**: A.U26.78 (1) (the five scripts' `scd_loop`/`sgp_loop`/`isl_loop`), A.U26.69, A.U8C.60/.61/.63/.74/.88 (the
  sibling-step and cycle literals of those loops).
- **Site**: new `_shared/bus_reader_loops.py`; `bus_concurrency_cross_device_scd30_sgp40.py:34, 47`,
  `bus_concurrency_isl29125_write_vs_siblings.py:42, 56`, `bus_concurrency_scd30_write_vs_siblings.py:38, 54`,
  `isl29125_cross_device_concurrency.py:61, 77, 91`, `sgp40_general_call_reset_hazard.py:63, 87`; every other
  `async def .*_loop` the A.U26.69 check flags (17 at HEAD).
- **Change**: `async def read_loop(name, read, iterations, step_ms, wdt, record)` — awaits `asyncio.sleep_ms(step_ms)`
  (or `sleep(0)`) on every path of every iteration, failure branch included; failures go to `record` as
  `errors_total += 1; if len(first) < 5: first.append(msg)`; feeds every round; the per-script step and iteration
  values stay the scripts' own tagged constants passed in (B4 rows unchanged, the literal moves to a constant).
- **Resolved**: A-C merge of A.U26.78 and A.U26.69 on the same bodies, as A.U26.78 states.
- **Unit**: U26.
- **Depends**: M.HW_DEV.002, M.HW_DEV.003, M.HW_DEV.004.
- **Blast carried by**: the `ast` check "every loop in an `async def` awaits on every looping branch" with its bites
  case → A.U26.69 (TSC); the host tests read `errors` facts → per-file changes below.
- **Kind**: test

### M.HW_DEV.006 A chunk-using script clears its chunk after setup and in `finally`
- **From**: A.U26.22 (5), CLAUDE.md FRAM rule (the board-has-run caveat), A.C.01 (2) (evidence first in every round).
- **Site**: `fram_error_log_roundtrip.py`, `fram_error_log_reset_race_seed_and_race.py`,
  `fram_error_log_reset_race_verify.py`, `fram_error_log_reset_during_boot_window.py`, `fram_manager_roundtrip.py`,
  `fram_busy_status_lockout.py`, `fram_pause_unpause_and_gating.py`, `fram_write_protect_roundtrip.py`,
  `sgp40_fram_backup_restore.py`, `bus_deinit_is_a_noop_on_real_hardware.py` (its chunk at offset 0), and every
  script calling `make_logger(`/`get_chunk(`.
- **Change**: each such script runs only after the session's evidence save (M.HW_BENCH's `fram_evidence_saved`
  fixture), clears its own chunk right after `setup()` and again in a `finally` before `done()`, so no seeded entry
  (`"TEST"`, `"ERRRACE"`, a seeded errno) survives; the reset-race pair clears in the verify phase's `finally` (the
  seed phase ends in a reset by design). Scripts that write raw bytes follow M.HW_DEV.007 instead.
- **Resolved**: V15's "residue is the accepted outcome" is superseded by OR38.a (4) (owner); none of these scripts
  leaves a well-formed chunk.
- **Unit**: U26.
- **Depends**: M.HW_BENCH.012 (`save_fram_raw`), `fram_raw_dump.py` (M.HW_DEV new-file section).
- **Blast carried by**: the check "every script calling `make_logger(`/`get_chunk(` also clears in a `finally`" →
  A.U26.22 (TSC); README line `:481-485` → A.U26.22 (HW_BENCH/U36).
- **Kind**: test

### M.HW_DEV.007 Raw FRAM addresses only inside declared scratch regions
- **From**: A.U26.24, A.U16.07 (the T4 script's region), OR47.a (2).
- **Site**: `fram_same_device_rw_concurrency.py:13-14`, `fram_cs_hijack_fault_injection_and_recovery.py:13-16`,
  `fram_reset_race_during_write_seed_and_race.py:13-17`, `fram_reset_race_during_write_verify_recovery.py:13-17`,
  `fram_command_hold_timing.py` (new), `uart_link_under_concurrent_system_load.py` (its FRAM writes), every script
  issuing raw `set_values`/`get_values`.
- **Change**: each declares `_SCRATCH_REGIONS = ((start, length), …)` (and `_EVIDENCE_REGIONS` for a read of production
  bytes) covering every raw call, its address constants written from the tuples; regions are pairwise disjoint (the
  reset-race pair shares one, both phases of one host test) and lie above the bench build's allocation and inside the
  part (dev: MB85RS2MTA, 256 KB, `datasheets/` PDF read at execution).
- **Resolved**: the T4 script's 0x3FF00 region (A.U16.07) and the loop-lag script's region (A.U31.01) are checked by the
  same disjointness rule; the per-file sections give each its region.
- **Unit**: U26 (A.U16.07's script, U16, declares its region at birth; the check lands in U26).
- **Depends**: A.U26.22; the twin boot harness of `tests_scripts/test_digital_twin_boot_contiguity.py`.
- **Blast carried by**: `tests_scripts/test_device_script_fram_regions.py` → A.U26.24 (TSC); README convention line →
  A.U26.24 (HW_BENCH).
- **Kind**: test

### M.HW_DEV.008 The NeoPixel rig is parked on every exit
- **From**: A.U26.16, A.U26.11 (the envelope).
- **Site**: `isl29125_mechanism_envelope.py`, `isl29125_lighting_scenarios.py`, `isl29125_plausibility_read.py`,
  `isl29125_real_irq_edge.py`, `fram_capacity_after_full_system_build.py`.
- **Change**: the NeoPixel construction is the first statement inside a `try` whose `finally` sets it dark (`.off()` /
  all-zero `write()`); the envelope's setup (`:205-213`) moves inside its `try`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: `tests_scripts/test_device_script_rig_parking.py` with its synthetic non-conforming script →
  A.U26.16 (TSC); README habit "park the rig in `finally`" → A.U26.16 (HW_BENCH).
- **Kind**: test

### M.HW_DEV.009 Full-system scripts: required watchdog, scratch config, the generated order
- **From**: A.U26.10, A.U20.02 (required `watchdog=`), A.U20.06/A.U11.10/A.U10.12/A.U32.06 (the `main()` sequence and
  the split supervisor), A.U10.44 (starter names), A.U11.06 (a script that ran `build_system()` leaves a boot-phase
  breadcrumb), A.U26.06 (2) (the guard reads `build_system(` without the scratch path as persisting).
- **Site**: `allocation_need_per_source.py`, `fram_capacity_after_full_system_build.py`,
  `heap_headroom_after_full_system_build.py`, `heap_layout_after_full_boot_sequence.py`, `serving_at_default_gc.py`,
  `heap_under_connection_ceiling.py`, `uart_link_under_concurrent_system_load.py`, and every new script that builds the
  system.
- **Change**: (1) The four construction-only scripts pass `cfg_path=_SCRATCH_CFG_PATH` with `_SCRATCH_CFG_PATH =
  "hwtest-scratch-absent/"` and the comment "Absent on purpose: a full build here must not repair or create a
  production config file; setup() serves defaults and writes nothing." (2) Every `build_system(`/`main(` call passes
  `watchdog=wdt` (`arm()`, M.HW_DEV.004); a script that replays the boot uses the generated helpers in the generated
  order — `build_system()` → `run_setups(_collect_setups())` → `start_tasks(_collect_task_starters(),
  _collect_task_names())` → `start_timers(triggers, timers)` → `ntp_force_sync()` — and never `start_and_check_tasks()`
  (gone). (3) The two `main()`-based serving scripts keep `cfg_path=""` with one comment line beside the call: the
  only write they can cause is the repair a production boot of a malformed file makes anyway. (4) A script that ran
  `build_system()` ends by clearing FRAM region 1's boot-phase mark (or reports the phase it reached), so the reset after
  it reads as the boot phase it is and the reset-code oracle is not misled.
- **Resolved**: A.U32.06 offers `task_names=None`; M.SRC_CORE.016 settles it required (GAP-G5); scripts pass it.
- **Unit**: U26 (after U20/U11/U10's API lands).
- **Depends**: M.SRC_CORE (`start_tasks`, `run_setups`, `boot_phase`), M.GEN (`_collect_setups()`, required
  `watchdog`), A.U11.19 (absent file writes nothing).
- **Blast carried by**: `_PREREQUISITE_DEVICE_SCRIPTS` entries for the two serving scripts → A.U26.06/A.U26.10 (TSC);
  README tooling-write table row "full-build scripts: no write" → A.U26.10 (HW_BENCH).
- **Kind**: test

### M.HW_DEV.010 Every instrument runs in the twin first
- **From**: A.U26.05, A.U35.49, A.U35.03, A.U35.05, A.U35.51, A.U7.01/A.U7.18 (L3 runs L0-L2 first), A.C.01 (frame).
- **Site**: every script and flash module of this cluster at the tip; `tests_hardware/twin_record.json`.
- **Change**: each script and flash module written or changed here is first run through `TwinBoard` (both GC stages);
  its `twin_record.json` entry is `pass` or an `exception` with a silicon-only reason stated in the per-file section
  (the two starvation scripts, the real-IRQ edge scripts, the electrical-timing tests, the toolchain reflash). U35
  reviews every test here for bite (A.U35.03), proves the check-style gates by triggering them through the twin
  (A.U35.05), and re-checks every wear gate (A.U35.51).
- **Resolved**: —
- **Unit**: U26 (entries); U35 (B2/B3 re-runs).
- **Depends**: M.HW_BENCH.091/.092.
- **Blast carried by**: `tests_scripts/test_twin_record.py` → A.U26.05 (TSC); fidelity gaps found → U25-kind fixes
  (TWIN).
- **Kind**: test

### M.HW_DEV.011 Flash modules: facts, scenarios, a serving board at the end
- **From**: A.U26.68 (helpers go), A.U26.78 (2), A.U7.24/A.U26.51 (`COVERS_TWIN_SCENARIOS`), A.U26.17
  (`leave_board_serving`), A.U26.26 (boot-line helper), A.U26.74/A.U26.35 (marker and flag names), A.U26.75
  (`--no-sync`), A.U26.76 (no `Any`), A.U20.33 (B2), A.U26.62 (3) (`_FLASH_FAULT_SCRIPTS`), A.U8C.101-.111, A.U8C2.44-.46.
- **Site**: every `tests_hardware/flash/test_*.py`, `flash/conftest.py`.
- **Change**: (1) `RESULT_RE`/`_assert_pass`/`_parse_result`/`_run_and_assert_pass` go; each test calls
  `facts = harness.parse_facts(board.run_isolated(script, timeout_s=…, **extras))` and asserts its conditions with the
  values in the message. (2) Each module declares `COVERS_TWIN_SCENARIOS: tuple[str, ...]` (A.U26.51's lists).
  (3) Marker names `persistence_write`, `soak_duration`, `multi_day_rollover`; option texts `--allow-persistence-write`,
  `--soak-duration`. (4) Every `timeout_s=` and poll literal becomes the module constant its U8C row names (B4).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.002/.012/.016, M.HW_DEV.002.
- **Blast carried by**: `tests_scripts/test_level_containment.py` → A.U7.24 (TSC); `test_bench_restores_serving.py`
  flash case → A.U26.17 (TSC); `--strict-markers` and the kebab mapping → A.U26.74 (TSC/TOOL); the no-task-ended guard's
  flash scope → A.U26.62 (TSC).
- **Kind**: test

### M.HW_DEV.012 Error numbers in scripts come from the catalog
- **From**: A.U2.01, A.U2.02 (9), A.U2.03 (device-script `E_`/`W_` bindings), A.U2.12/A.U2.20 (blasts naming seed
  scripts).
- **Site**: `isl29125_lighting_scenarios.py:204, 336`, `isl29125_mechanism_envelope.py:217, 221`, the seed scripts'
  errnos (`fram_error_log_roundtrip.py` `TEST_ERRNO = 42`, `fram_error_log_reset_during_boot_window.py`
  `SEEDED_ERRNO = 5`, `fram_error_log_reset_race_seed_and_race.py` 5/6).
- **Change**: a product code a script compares against is a module constant `E_<NAME>`/`W_<NAME> = <n>` equal to the
  catalog's entry (e.g. `W_ISL_PERIODIC_ONLY = 32`); a seed errno is a code from the catalog's test band (125-127,
  A.U2.01's table) bound as `E_TEST_SEED_<n>`, never a product code a reader could mistake for a real fault.
- **Resolved**: the seeded `errno=5` that was once read back as SYSTEM's real entry (CLAUDE.md FRAM caveat) is what the
  test band prevents; the per-file sections name each value.
- **Unit**: U2 (catalog) for the bindings; the seed values move with U26's rewrite of those scripts.
- **Depends**: A.U2.01.
- **Blast carried by**: check (9) "every binding in `device_scripts/` equals the catalog" → A.U2.02 (TSC).
- **Kind**: test

## tests_hardware/flash/conftest.py

### M.HW_DEV.020 The SCD30 prerequisite: check first, start at most once
- **From**: A.U26.07 (5), A.U26.06 (blast: the fixture leaves the gated set), A.U4.08 (blast: the docstring rewording is
  U26's), A.U26.74 (old flag name), A.U20.33 (B2: quoted `"Board"`), A.U8C.101 (dropped, see Resolved).
- **Site**: `tests_hardware/flash/conftest.py:1-33`.
- **Change**: docstring `:1-3` → "Flash-tier fixtures: the SCD30 continuous-measurement prerequisite. The start command
  is NVM-persisted, so it is sent only when no measurement arrives within three intervals, and at most once per pytest
  session (owner, 2026-09-29; NVM never written more than once per session, owner, 2026-09-16)." (3 lines). Fixture
  `scd30_continuous_measurement_triggered` → `scd30_measuring(board: "Board", request) -> str`, session scope,
  unmarked, no option check: `note = ensure_scd30_measuring(board, _SESSION)`, then `record_session_note(request.config,
  note, source="scd30_measuring")`; `_SESSION = scd30_prerequisite.new_session()` at module level. `_DEVICE_SCRIPTS`
  goes (the helper owns the paths). `from __future__` goes (B2).
- **Resolved**: A.U8C.101's tag on `:32`'s `90.0` is withdrawn: the call it tags goes; the interval-read timeout is
  tagged in `scd30_prerequisite.py` (M.HW_BENCH.044, `l3.scd30_prerequisite_interval_read_timeout_s`).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.044, M.HW_BENCH.004 (`record_session_note`), the three new scripts (M.HW_DEV.150-.152).
- **Blast carried by**: every dependent test renames its fixture argument (`scd30_measuring`) and drops
  `persistence_write` where the fixture was its only write → M.HW_DEV.080 (`test_bus_concurrency.py`); the prerequisite
  set `_PREREQUISITE_DEVICE_SCRIPTS` names `scd30_start_continuous_measurement.py` → A.U26.06 (TSC); L0
  `tests_scripts/test_scd30_prerequisite.py` → A.U26.07 (TSC); budget texts (`tests_hardware/README.md:101-106,
  1063-1071, 1310-1325`, `conftest.py:90-99, 110`, CLAUDE.md `:252-259`) → A.U26.07/A.U4.08 (HW_BENCH, DOCS).
- **Kind**: test, hardware (Round: R1 [H31])

### M.HW_DEV.021 A flash session ends on a serving board
- **From**: A.U26.17, A.U26.26.
- **Site**: `tests_hardware/flash/conftest.py` (new fixture).
- **Change**: `leave_board_serving(board: "Board") -> Iterator[None]`: autouse, session scope; after `yield`:
  `board.hard_reset()`, `wait_until(board.is_device_present, timeout_s=_PRESENT_TIMEOUT_S)`, then
  `harness.wait_for_boot(board, _BOOT_TIMEOUT_S)`; a board that does not come back raises (a teardown error the verdict
  counts). `_PRESENT_TIMEOUT_S = 15.0`, `_BOOT_TIMEOUT_S = 30.0` tagged `l3.flash_leave_serving_present_timeout_s`,
  `l3.flash_leave_serving_boot_timeout_s` (B4, new rows).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.016 (`wait_for_boot`).
- **Blast carried by**: `test_the_flash_tier_leaves_the_board_serving` → A.U26.17 (TSC).
- **Kind**: test, hardware (Round: R1)

## tests_hardware/flash/test_task_supervisor.py

### M.HW_DEV.025 The restart test asserts the restart facts and the log entries
- **From**: A.U26.34 (1) (blast: asserts the new detail), A.U20.06/A.U32.06 (blast: name `start_tasks`), A.U26.68,
  A.U26.51 (`COVERS_TWIN_SCENARIOS` = the `ci_suite` supervisor run IDs), A.U20.33 (B2), A.U8C.108.
- **Site**: `tests_hardware/flash/test_task_supervisor.py:1-22`.
- **Change**: docstring `:1-3` names `SystemService.start_tasks()`/`supervise_tasks()`; `RESULT_RE` goes; the test
  `test_the_supervisor_restarts_a_real_dead_task(board: "Board")` runs the script with
  `timeout_s=_SCRIPT_TIMEOUT_S` (`= 15.0`, `# @tunable l3.task_supervisor_script_timeout_s = 15.0`), then asserts
  `facts["starter_calls"] >= 2` and `facts["restart_warnings"] == facts["starter_calls"] - 1` with every entry's wrnno
  equal to the catalog's restart code (`error_codes.code("W_TASK_RESTART")`, A.U2.03's host helper), the facts quoted in
  each message; `COVERS_TWIN_SCENARIOS` from `run_suite()`'s supervisor IDs read at execution.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.026, M.HW_DEV.011.
- **Blast carried by**: twin record entry → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H16])

## tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py

### M.HW_DEV.026 Restart and escalation modes over the split supervisor, with a log oracle
- **From**: A.U26.34 (1), A.U26.28 (2) (escalation mode run by `bench/test_reset_reasons.py`), A.U20.06 + A.U32.06
  (blast: `start_tasks()` then `supervise_tasks()`, `task_names` required — GAP-G5), A.U10.37 (`asy_system_service`),
  A.U8.08/A.U8C.90 (`:11`, `:38`), A.U8C2.38 (`:37`), A.U26.68, A.U26.61, A.U11.06 (boot-phase note: the script never
  ran `build_system()`, so no mark to clear).
- **Site**: `tests_hardware/device_scripts/system_service_restarts_a_real_dead_task.py:1-53` (HEAD numbering of the
  script body `:7-53` as cited by the actions).
- **Change**: header names `start_tasks()`/`supervise_tasks()`. Imports `from asy_system_service import SystemService`,
  `# @include _shared/watchdog.py`, `_shared/facts.py`. `wdt = arm()` (M.HW_DEV.004; the local `_WDT_TIMEOUT_MS`
  goes). `SystemService(_ntp_never_synced, watchdog=wdt, log=_RamLog())` with an in-RAM logger whose entries the
  script reads back; `await sysfunct.start_tasks([_dying_starter], ["dying"])`, then
  `supervisor = asyncio.create_task(sysfunct.supervise_tasks())`. Mode from `BENCH["mode"]` (render extra, default
  `"restart"`): `restart` watches `_WAIT_ROUNDS = 4` (`l3.system_service_restarts_a_real_dead_task_wait_rounds`) steps of
  `_WATCH_STEP_S = 0.9` (`l3.system_service_restarts_a_real_dead_task_watch_step_s`), feeding, cancels the supervisor
  and reports `starter_calls`, `restart_warnings` (the wrnnos in the RAM log), `done()`; `escalate` keeps the task
  dying and keeps feeding until the supervisor's budget reboots the board (100 per death, 300 budget), reporting each
  round as a fact before it (the host reads the reset as the outcome, code 5). The three-line comment `:56-58`
  becomes one line naming the budget constants by name, not value.
- **Resolved**: A.U26.28 extends this script "by a mode" and A.U26.34 rewrites its oracle; one script, the mode an
  extra. A.U32.06's default `task_names=None` is settled required (GAP-G5): the script passes `["dying"]`.
- **Unit**: U26.
- **Depends**: M.SRC_CORE (`start_tasks`, `supervise_tasks`, logger shape), M.HW_DEV.001-.004.
- **Blast carried by**: `bench/test_reset_reasons.py` escalation case → A.U26.28 (HW_BENCH); `_FLASH_FAULT_SCRIPTS`
  of the no-task-ended guard (the dying task is the injected fault) → A.U26.62 (TSC); README rungs table row "task
  restart" → A.U26.34 (4) (HW_BENCH); twin record → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H16]; escalation R1 bench [H12])

## tests_hardware/flash/test_watchdog_starvation.py

### M.HW_DEV.030 Starvation tests: banner and action oracles, one closing reset, no `reset_cause()`
- **From**: A.U26.25, A.U14.01 (blast: `:51, 73-74` treat `CAUSE 3` as proof — U26's), A.U11.03 (blast: markers
  unchanged), A.U10.09/A.U26.86 (blast: the README/SPEC text naming this test, holds), A.S0930.31 (blast: holds),
  A.U26.51, A.U20.33 (B2), A.U8C.111.
- **Site**: `tests_hardware/flash/test_watchdog_starvation.py:1-77`.
- **Change**: (1) `_WDT_RESET` (`:51`) and the `reset_cause()` exec/assert (`:73-74`) go; one comment line at `:69-70`
  states that the banner and the absent `action_fired=True` discriminate here and the reset code is proven on the bench
  (`bench/test_reset_reasons.py`, codes 2 and 6). (2) The post-reset `is_reachable()` polls (`:42`, `:58`) go:
  `is_device_present()` is the passive proof (an attach parks `main.py`); the fallback test's pre-run wait becomes
  `wait_until(board.is_device_present, …)`. (3) A module-scoped fixture `closing_reset(board: "Board")` yields, then
  does the one `hard_reset()` + presence wait both tests' `finally` blocks did (`:43-47`, `:75-77` go); both tests take
  it. (4) Docstring `:1-3` adds "the fallback's reset code is proven at L4". (5) Constants per A.U8C.111 (B4):
  `_SCRIPT_TIMEOUT_S`, `_RESET_ELAPSED_MAX_S`, `_DEVICE_PRESENT_TIMEOUT_S`, `_DEVICE_PRESENT_POLL_S`,
  `_FALLBACK_SCRIPT_TIMEOUT_S`, `_FALLBACK_ELAPSED_MAX_S`; the four `is_reachable` constants
  (`_REACHABLE_AFTER_RESET_*`, `_REACHABLE_*`) are not written — their call sites go (rows withdrawn). (6) The
  banners stay output lines read from the failure text (a script that never returns reports no `DONE`: these two are
  `parse_facts`'s stated exception, the host reading the captured stream).
- **Resolved**: A.U8C.111 tags `:42` and `:58`, which A.U26.25 (2) deletes — the later unit's deletion stands (B4).
  A.U26.68's "missing `DONE` fails" cannot apply to a script whose subject is never returning; the stream check is kept
  (agent decision AD-3).
- **Unit**: U26.
- **Depends**: M.HW_DEV.031, M.HW_DEV.032, A.U26.28 (bench code proofs).
- **Blast carried by**: twin record: both `exception` "the twin WDT does not reset the host process" → M.HW_DEV.010;
  README `:1280-1286` → A.U10.09/A.U26.86 (HW_BENCH).
- **Kind**: test, hardware (Round: R1 [H12])

## tests_hardware/device_scripts/watchdog_starvation_reset.py

### M.HW_DEV.031 The short starvation window is its tagged row
- **From**: A.U8.08 (`l3.starvation_wdt_ms`), A.U8C.97.
- **Site**: `tests_hardware/device_scripts/watchdog_starvation_reset.py:7`.
- **Change**: `# @tunable l3.starvation_wdt_ms = 1500` above `WATCHDOG_TIMEOUT_MS` (renamed `_WATCHDOG_TIMEOUT_MS`,
  module-private like every script constant); nothing else — the script's subject is a reset, so it neither includes
  `_shared/watchdog.py` nor reports `DONE` (AD-3).
- **Resolved**: —
- **Unit**: U8 (tag).
- **Depends**: A.U8.01/.02.
- **Blast carried by**: Part N row → A.U8.08 (SPEC).
- **Kind**: test

## tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py

### M.HW_DEV.032 The fallback goes through the awaited `_reboot()` with its reset code
- **From**: A.U11.03 (blast: `asyncio.run(svc._reboot(_RR_REBOOT, …))`), A.U5.02 (constructor: `fram=None,
  debug=None` → `log=`), A.S0930.12/.13/.31 (blast: holds — feeds through `feed_watchdog()`, no shutdown accepted),
  A.U10.37 (`asy_system_service`), A.U8.08/A.U8C.81, A.U26.28 (2) (run by the bench reset-code test), A.U26.68.
- **Site**: `tests_hardware/device_scripts/reboot_fallback_starves_the_watchdog.py:6-50` (HEAD lines as cited).
- **Change**: `from asy_system_service import SystemService, _RR_REBOOT`; `SystemService(_never_synced, watchdog=wdt)`
  (the `fram=None, debug=None` keywords go: `log` defaults); the call becomes `asyncio.run(svc._reboot(_RR_REBOOT,
  "reboot requested with the alarm pool exhausted", lambda: fired.append(True)))` (the `"G3: "` prefix goes: an audit
  ID in a permanent string, G9/R12); `_FEED_ATTEMPT_MS = 250` (`l3.reboot_fallback_starves_the_watchdog_feed_attempt_ms`)
  and `# @tunable l3.starvation_wdt_ms = 1500` on `_WATCHDOG_TIMEOUT_MS`; the pool-size loop bound `64` gets the
  comment's source (`timer_alarm_pool_exhaustion.py`'s measured pool). The early-failure branches report
  `fact("failure", …)` then `done()`; the success path keeps its banner and `FEED_CALLED … action_fired=` lines (the
  host reads the stream, AD-3).
- **Resolved**: —
- **Unit**: U11 (the `_reboot()` call, with A.U11.03), U26 (facts, constants).
- **Depends**: M.SRC_CORE (`_reboot()` async, `_RR_REBOOT`), M.HW_DEV.002.
- **Blast carried by**: `bench/test_reset_reasons.py` code-6 case → A.U26.28 (HW_BENCH); twin record `exception` (the
  twin cannot exhaust a real alarm pool) → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H12])

## tests_hardware/flash/test_reboot_persistence.py

### M.HW_DEV.035 Config persistence across a reset: one owned write, cleanup on every path
- **From**: A.U26.18 (host `try`/`finally` cleanup), A.U26.60 (docstring loses "DTR"; `:36` stays), A.U26.68 (`_parse_result`
  goes), A.U8C.106 (`:36`), A.U26.51, A.U20.33 (B2), A.U1.06 (blast: the scripts it names are fixed here).
- **Site**: `tests_hardware/flash/test_reboot_persistence.py:1-40`.
- **Change**: docstring `:1-3` → "Flash-tier reboot tests: a genuine `hard_reset()` (a raw-REPL `machine.reset()`, a
  real MCU reset that re-runs the frozen `main.py`), observed passively so the boot path runs undisturbed." `RESULT_RE`
  and `_parse_result` go. `test_config_value_survives_a_genuine_hard_reset` keeps `@pytest.mark.persistence_write`
  (the one write it owns): write phase → `parse_facts` (`facts["flushed"] is True`); `hard_reset()`; `wait_until(
  board.is_reachable, timeout_s=_REACHABLE_TIMEOUT_S, poll_interval_s=_REACHABLE_POLL_S, …)` (tags
  `l3.reboot_persistence_reachable_timeout_s`/`_poll_s`, the next step enters the raw REPL anyway); read phase asserts
  `facts["marker"] == facts["expected"]`. Both phases sit in a `try` whose `finally`, when the read phase never ran,
  runs `board.exec("import os\ntry:\n  os.remove('config_HWTEST_REBOOT.cfg')\nexcept OSError:\n  pass")` then
  `hard_reset()`. The `# Item 13 - …` divider becomes one `#` line naming the test's subject.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.037/.038.
- **Blast carried by**: the `config_HWTEST_*` removal check → A.U26.18 (TSC); twin record → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R3 [H47] — owned flash write)

### M.HW_DEV.036 The boot check reads DebugLevel and watches for boot lines; it writes nothing
- **From**: A.U26.12 (1)(2), A.U26.26, A.U26.45 (`:67` message goes), A.U26.60 (`:79` goes with A.U26.12), A.U1.25 +
  A.U20.15 + A.U36.544 + A.U1.11/A.U1.19 (blasts: the `:44-45` comment), A.U11.24 (blast: the scripts' schema argument
  goes with the scripts), A.U8C.106 (`:64`, `:79`).
- **Site**: `tests_hardware/flash/test_reboot_persistence.py:43-79`.
- **Change**: the comment block `:43-47` → "# This bench flashes only the generated boot entry, frozen as "main.py",
  never the legacy `legacy/firmware/modules/_boot.py` mechanism that CLAUDE.md's `_boot.py` rule describes. A real
  hard reset must bring the whole application layer back - ConfigManager/FRAM, not just the interpreter." (3 lines).
  `test_boot_import_mechanism_actually_boots_the_real_system(board)`: no marker, no scripts, no `finally`
  (DebugLevel 5 is checked by the autouse `standard_state` fixture before the first test); `board.hard_reset()`, then `lines = harness.wait_for_boot(board, _BOOT_LOG_TIMEOUT_S)` (`= 20.0`, tag
  `l3.reboot_persistence_boot_log_tail_s` keeps its ID) and `assert harness.boot_lines(lines) and not
  harness.crash_lines(lines)`, the message naming the generated device module generically ("the generated boot
  entry's startup lines").
- **Resolved**: three actions rewrite the `:44-45` comment's three phrases (A.U20.15 the boot-entry name, A.U1.25 the
  legacy path, A.U36.544 the BACKLOG pointer); the end state carries all three. A.U8C.106's `:79` tags go with the
  site (A.U26.12).
- **Unit**: U26 (the A.U1.25 path lands in U1 on the HEAD text; U26 rewrites the block to the end state above).
- **Depends**: M.HW_BENCH.006 (`standard_state` absorbs A.U26.12 (1)'s `debug_level_standard`), M.HW_BENCH.016.
- **Blast carried by**: the two raise/restore scripts deleted → M.HW_DEV.039; their
  `tests_scripts/test_device_script_config_flush.py` coverage goes → A.U26.12 (TSC); the persistence-marker guard
  sees the test unmarked and writing nothing → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R1 [H16])

## tests_hardware/device_scripts/reboot_persist_write.py

### M.HW_DEV.037 The write phase removes a leftover first and spends exactly one write
- **From**: A.U26.18, A.U11.24 (`write_config()` takes no schema), A.U10.37 (`asy_config_manager`), A.U11.33 (guard:
  `config_HWTEST_*` exempt), A.U1.06 (blast), A.U26.68, A.U11.19 (the absent-file `setup()` writes nothing).
- **Site**: `tests_hardware/device_scripts/reboot_persist_write.py:1-25` (HEAD script lines `:6-25`).
- **Change**: `import asy_config_manager as cm`; before constructing the manager: `os.remove(_PATH)` in a `try` where
  `ENOENT` passes and any other `OSError` reports `fact("leftover_remove_errno", e.errno)` then `done()`; then
  `setup()`, `write_config({"Marker": _MARKER_VALUE})` (no schema argument), `flush_pending()`, facts `written`,
  `flushed`, `done()`. The three-line comment `:20-22` becomes one line ("write_config() stages; the flush is its own
  task, so it is awaited here").
- **Resolved**: —
- **Unit**: U26 (U11 adapts the call shape first, A.U11.24's blast).
- **Depends**: A.U11.19, A.U11.24.
- **Blast carried by**: flush-guard check `tests_scripts/test_device_script_config_flush.py` (holds) → A.U26.18 (TSC).
- **Kind**: test

## tests_hardware/device_scripts/reboot_persist_read.py

### M.HW_DEV.038 The read phase reports the marker and removes the file in `finally`
- **From**: A.U26.18, A.U10.37, A.U11.33, A.U26.68.
- **Site**: `tests_hardware/device_scripts/reboot_persist_read.py:1-26` (HEAD script lines `:14-26`).
- **Change**: `import asy_config_manager as cm`; facts `valid`, `marker`, `expected` (the comparison moves host-side);
  a `finally` removes `config_HWTEST_REBOOT.cfg` (ENOENT passes), then `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: M.HW_DEV.035 asserts the facts.
- **Kind**: test

## tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py, system_debug_level_restore_after_boot_log_check.py (deleted)

### M.HW_DEV.039 Both DebugLevel scripts are deleted
- **From**: A.U26.12 (3), A.U26.18 (their backup scratch goes with them), A.U5.02/A.U11.24/A.U11.33/A.U1.06 (blasts on
  these files: moot).
- **Site**: `tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py`,
  `system_debug_level_restore_after_boot_log_check.py`.
- **Change**: both files deleted; nothing replaces them on the boot-check path (M.HW_DEV.036 reads, never writes).
- **Resolved**: the blasts that adapt their `write_config(…, schema)` calls and their schema copy (A.U11.24,
  A.U11.33) fall away with the files.
- **Unit**: U26.
- **Depends**: M.HW_DEV.036.
- **Blast carried by**: `tests_scripts/test_device_script_config_flush.py` references → A.U26.12 (TSC); twin record
  entries removed → A.U26.05's "no entry for a deleted file" (TSC).
- **Kind**: test

## tests_hardware/device_scripts/system_debug_level_set_standard.py (new)

### M.HW_DEV.040 Repair DebugLevel to the standard value, only on request
- **From**: A.U26.79 (1), A.U11.33 (guard: a production file takes the module's full production schema), A.U11.24,
  A.U26.06 (prerequisite listing).
- **Site**: new `tests_hardware/device_scripts/system_debug_level_set_standard.py`.
- **Change**: header (≤ 3 lines): "Restores SYSTEM DebugLevel to the standard board state; run only by the
  standard-state fixture under --repair-standard-state when no bench bridge is configured (one flash write)."
  Body: `cm.ConfigManager("config_SYSTEM.cfg", BENCH["system_schema"], "SYSTEM")`, `setup()`, read `DebugLevel`
  (fact `before`), when it differs from `BENCH["standard_debug_level"]` `write_config({"DebugLevel": …})` and
  `flush_pending()` (facts `written`, `validity`), `done()`; the host follows with `hard_reset()`.
- **Resolved**: A.U26.79 names `system_service._VAL_DEBUG_LEVEL` as the schema; A.U11.33's guard requires a production
  file's full production schema, and an underscore-named `const()` is not a module attribute on the board (MicroPython
  `micropython.const()` docs; re-checked at execution, CLAUDE.md docs rule), so the schema is a render extra built by
  `buildgen.schema_ast` from `src/asy_system_service.py` — the guard's own source (agent decision AD-4).
- **Unit**: U26.
- **Depends**: M.HW_BENCH.006 (`standard_state`, A.U26.79), M.HW_DEV.001/.002.
- **Blast carried by**: `_PREREQUISITE_DEVICE_SCRIPTS` entry "restores the standard board state" → A.U26.79/A.U26.06
  (TSC); A.U11.33's guard accepting `BENCH["system_schema"]` as production by construction → GAP-D3 (TSC); the two
  extras in `bench_facts.pyi` → M.HW_DEV.001.
- **Kind**: test, hardware (Round: R1 only on repair [H01-adjacent standard state])

## tests_hardware/flash/test_uart_crossover.py

### M.HW_DEV.045 The UART flash module: both CRC modes, fail on a missing module, hazards added
- **From**: A.S0930.05 (parametrise `crc_mode`), A.U7.16 (`_run_or_skip` → `_run_or_fail`, `pytest.fail`, "the bench
  device's TOML"), A.U26.45 (docstring "the dev bench's" → "the bench board's"), A.U26.59 (the raw-read test and script
  go), A.U26.33 (4) (message names the resync bound), A.U26.82 (new hazard test), A.U26.87 (1) (the load test asserts
  SET/GET echo counts), A.U13.13 (blast: must pass unchanged), A.U26.68, A.U26.51 (`uart_link`, `machine_uart`),
  A.U20.33 (B2), A.U8C.110, OR123 (both CRC modes over the same jumper, owner).
- **Site**: `tests_hardware/flash/test_uart_crossover.py:1-85`.
- **Change**: (1) Docstring `:1` → "…across the bench board's permanent UART crossover jumper…"; the comment `:18-21`
  names "the bench device's TOML `uart_link` instances" and states a missing module fails. (2) `_run_or_fail(board,
  script, timeout_s, **extras) -> dict[str, object]`: `parse_facts(board.run_isolated(…, **extras))`; on the
  `ImportError` text → `pytest.fail(…)`. `RESULT_RE`/`_assert_pass` go. (3) `@pytest.mark.parametrize("crc_mode",
  ["none", "crc16"])` on the exchange, recovery, hazards and load tests; each passes `CRC_MODE=crc_mode` and asserts
  `facts["crc_mode"] == crc_mode`. (4) `test_a_clamped_read_never_holds_the_cpu_for_a_frame_still_arriving` (`:58-63`)
  goes; the driver test asserts `facts["first_pollin_bytes"] < facts["frame"]` (the folded precondition),
  `facts["driver_span_us"] <= facts["span_max_us"]`, `facts["control_span_us"] >= facts["span_max_us"]` and the
  readline leg's span (A.U13.12). (5) Recovery asserts silence and desync each failed then recovered within
  `facts["resync_bound_ms"]` (the bound rendered from `src/asy_uart_comm.py`'s consts by `ast`, named in the message)
  and the mismatch failed with a logged error. (6) New `test_comm_hazards_are_serialised_refused_or_recovered(board,
  crc_mode)` runs `uart_comm_hazards.py`: H1a one completion and one re-entrant refusal with whole frames, H1b each
  point completes or fails cleanly and the next succeeds, H2 peer-initiated code then recovery within two attempts,
  H3 each boundary value accepted iff legal. (7) The load test asserts transfers ≥ floor, zero link failures, worst
  RTT ≤ bound, zero error counts, every load counter > 0, heap growth ≤ bound, and echo `intact == total` for the
  multi-chunk SETs. (8) Timeouts `_SCRIPT_TIMEOUT_S = 120.0`, `_LONG_SCRIPT_TIMEOUT_S = 180.0` (A.U8C.110's IDs); the
  hazard test's timeout is a new row `l3.uart_crossover_hazards_timeout_s` sized at execution from the twin run.
- **Resolved**: A.S0930.05 runs each script once per mode with no reflash (scripts run from RAM); A.U26.82's hazard
  script takes the same parameter. OR123's "L3 CRC16 device script over the same jumper" is this parametrisation, not
  a separate script.
- **Unit**: U26 (A.S0930's CRC arm lands with S0930's U-slot after U26's script rewrite; the parametrisation is
  written once in the end form).
- **Depends**: M.HW_DEV.046-.052; A.S0930.01 (`crc` key, `CRC16`).
- **Blast carried by**: SPEC J.7 tier map (L3 cells) → A.U36.539/A.U17.25 (SPEC); CLAUDE.md UART hazard clause →
  A.U36.539 (DOCS); twin record → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H37]; CRC16 arm R1 [H37], reflash-free)

## tests_hardware/device_scripts/uart_crossover_exchange.py

### M.HW_DEV.046 The exchange script takes its pair and CRC mode from `BENCH`
- **From**: A.S0930.05, A.U26.44, A.U5.12 (one callbacks object, one `log` object), A.U10.38 (`UARTComm`), A.U26.76
  (`Coroutine[object, object, T]`), A.U26.78 (`_settled` → `_shared/settle.py`), A.U2.20 (blast: the error print
  `:132` holds), A.U8C.91 (`:29, :32, :33` mirrors → `BENCH`; `JOIN_STEP_MS`, `JOIN_BUDGET_MS` tags; `:83` →
  `_shared/watchdog.py`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/uart_crossover_exchange.py:1-142`.
- **Change**: docstring `:1-3` drops the literal pins ("…across the bench board's UART crossover jumper…"); comment
  `:4-6` "never through sensortask_dev's full task graph" → "never through the generated device module's task graph".
  `uart0`/`uart1` from `BENCH["bus"]["uart0"]`/`["uart1"]` (id, tx, rx, baudrate, rxbuf, txbuf, poll_wait_ms,
  poll_idle_ms), `crc=CRC16()` when `BENCH["CRC_MODE"] == "crc16"` (else the default `CRCPass`); the `POLL_*`, `BUF_BYTES`,
  `BAUDRATE` constants and the comment `:30-31` go. `UARTComm(uart0, ROLE_INITIATOR, payload_size=…, timeout=…,
  name="UART_INIT")`, the responder with `callbacks=_Callbacks()` (get/set). `_settled` included from
  `_shared/settle.py`; `JOIN_STEP_MS`/`JOIN_BUDGET_MS` become `_JOIN_STEP_MS`/`_JOIN_BUDGET_MS` with their tags.
  Facts: `crc_mode`, `get_answer_ok`, `set_ok`, `empty_set_ok`, `train_bytes`, `error_counts` (per instance), `done()`.
- **Resolved**: —
- **Unit**: U26 (the A.U5.12/A.U10.38 call shapes land in U5/U10 on the HEAD text; U26 writes the end form).
- **Depends**: M.HW_DEV.001-.004.
- **Blast carried by**: UART changelog Class B entries for the API rename/constructor → A.U5.12/A.U10.38 (DOCS); twin
  record → M.HW_DEV.010.
- **Kind**: test

## tests_hardware/device_scripts/uart_crossover_recovery.py

### M.HW_DEV.047 Recovery: silence and baud desync, both timed against the resync bound
- **From**: A.U26.33, A.U26.86/A.U36.028 (the injector comment takes the one wording), A.S0930.05, A.U26.44, A.U5.12,
  A.U10.38, A.U26.76, A.U26.78 (`_settled`), A.U17.33/A.U17.25 (blast: stays the L3 silence/desync rung), A.U8C.92,
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/uart_crossover_recovery.py:1-159`.
- **Change**: docstring `:2` "within the specified window" → "within the protocol's resync bound (timed)"; comment
  `:4-6` → "The UART fault catalog is mock-only (no injection hardware will be bought, owner 2026-09-22); this injector
  reaches the two faults the bench can make: silence and a baud mismatch." `_build()` takes the pair, buffers and CRC
  mode from `BENCH` (`PeripheralInjector` gets the responder bus's id/tx/rx from `BENCH`, its `_reinit` the bus's
  rxbuf/txbuf). After the silence case, a desync case: `injector.desync()`, `uart_set(_CMD_ECHO, b"skew")` is False and
  the initiator log holds a frame/ACK error; `restore()`, `await responder.clear()`, the next transfer succeeds. Both
  recoveries timed (`ticks_ms()` from `restore()` to the first success) and reported against `BENCH["resync_bound_ms"]`
  (extra: `_DRAIN_BOUND_MULT`, `_RESYNC_NUM/_RESYNC_DEN` × timeout plus one timeout, read host-side by `ast`). Facts:
  `crc_mode`, `silence_failed`, `silence_recovery_ms`, `desync_failed`, `desync_logged`, `desync_recovery_ms`,
  `resync_bound_ms`, `mismatch_failed`, `mismatch_logged`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004; A.S0930.01.
- **Blast carried by**: the host bound check → M.HW_DEV.045; SPEC J.7 "baud desync: L3" → A.U26.33 (SPEC).
- **Kind**: test, hardware (Round: R1 [H37])

## tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py

### M.HW_DEV.048 The driver's read span, the folded POLLIN precondition and a readline leg
- **From**: A.U26.59, A.U13.12 (L3 readline leg), A.U17.05/A.U30.16 (the collects before timed windows are allowed),
  A.U28.30 (`:135` keeps its coded ignore with a reason), A.U8.19 (Part N `loop.uart_call_span_max_us` checked here),
  A.U26.44, A.U8C.93, A.U8C2.39, A.U26.68, AD-1 (deferred `:106`).
- **Site**: `tests_hardware/device_scripts/uart_driver_read_never_blocks_the_loop.py:1-168`.
- **Change**: (1) Fold: `_trial` records `uart.any()` at the first POLLIN of the measured frame (fact
  `first_pollin_bytes`); the comment `:107` → "(the copy into txbuf is timed separately and reported as
  `txcopy_us`)" — `ticks_us()` around the `write()`, outside the measured window. (2) Readline leg: one trial reading
  a `\n`-terminated frame through `readline_until_complete()`, its worst call span a fact (`readline_span_us`).
  (3) Pins and buffers from `BENCH` (the raw writer UART on `BENCH["bus"]["uart0"]`, the driver on `uart1`); `FRAME`
  stays (one framed frame at payload 48) with its comment no longer citing the deleted script. (4) Constants per
  A.U8C.93/A.U8C2.39: `_TRIALS`, `_START_TIMEOUT_MS`, `_READ_TIMEOUT_MS`, `_RAW_DEADLINE_MS`, `_IDLE_WINDOW_MS`,
  `_SPAN_FRACTION`; the `:106` settle `sleep_ms(5)` kept as `_TICKER_START_MS = 5`
  (`l3.uart_driver_read_never_blocks_the_loop_ticker_start_ms`, AD-1); `:126` → `arm()`. (5) `:135` →
  `drv._uart = timed  # type: ignore[assignment]  # the timed wrapper stands in for machine.UART`. (6) Facts:
  `frame`, `wire_us`, `span_max_us`, `driver_span_us`, `control_span_us`, `first_pollin_bytes`, `txcopy_us`,
  `readline_span_us`, `driver_gap_us`, `control_gap_us`, `idle_gap_us`, `intact` (per trial), `done()`.
- **Resolved**: the comparisons move host-side (A.U26.68), so Part N's `loop.uart_call_span_max_us` "Checked by"
  cell names the host test, not `:155-157` (GAP-D4, SPEC).
- **Unit**: U26.
- **Depends**: M.SRC_NET (A.U13.12 clamp), M.HW_DEV.001-.004.
- **Blast carried by**: GAP-D4 (SPEC Part N cell); U30 allow-list rows for the two pre-window collects → A.U30.16
  (TSC); host assertions → M.HW_DEV.045.
- **Kind**: test, hardware (Round: R1 [H37])

## tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py (deleted)

### M.HW_DEV.049 The raw-UART stall script is deleted
- **From**: A.U26.59, A.U26.61 (one of its three named feeders), A.U8C.96/A.U8C2.42 (withdrawn), A.SDEP.17 (blast:
  named beside the W25 names).
- **Site**: `tests_hardware/device_scripts/uart_read_never_blocks_the_loop.py`.
- **Change**: deleted; its precondition lives in M.HW_DEV.048, its host test goes (M.HW_DEV.045 (4)).
- **Resolved**: A.U8C.96/A.U8C2.42's rows on this file are withdrawn (B4); the shared ID
  `l3.uart_read_never_blocks_the_loop_span_fraction` keeps its other site (M.HW_DEV.048).
- **Unit**: U26.
- **Depends**: M.HW_DEV.048.
- **Blast carried by**: SPEC F.5.8 citations of this script → A.U26.59/A.SDEP.17 (SPEC); twin record entry removed →
  A.U26.05 (TSC).
- **Kind**: test

## tests_hardware/device_scripts/uart_idle_poll_rate.py

### M.HW_DEV.050 Idle poll rate: the pair stated explicitly from `BENCH`
- **From**: A.U13.17 (blast: passes both rates explicitly), A.U17.05/A.U30.16 (`:52` pre-window collect allowed),
  A.U5.12, A.U10.38, A.U26.44, A.U8C.94, A.U8C2.40, A.U26.68, AD-1 (`:64`, `:78`).
- **Site**: `tests_hardware/device_scripts/uart_idle_poll_rate.py:1-109`.
- **Change**: the bus from `BENCH["bus"]["uart1"]`, `poll_wait_ms`/`poll_idle_ms` from `BENCH`, passed explicitly in
  both arms (fast arm: idle = wait); `UARTComm(…, callbacks=_Callbacks())`. Constants: `_SAMPLE_MS`, `_MIN_RATIO`,
  `_SAMPLE_STEP_MS`, `_STOP_POLL_MS`, `_EXPECTED_ROUNDS_FACTOR`, `_STOP_POLL_TRIES` with their rows; the deferred
  sleeps kept as `_PARK_SETTLE_MS = 100` (`l3.uart_idle_poll_rate_park_settle_ms`) and `_CANCEL_SETTLE_MS = 20`
  (`l3.uart_idle_poll_rate_cancel_settle_ms`, AD-1). Facts `fast_rounds` (a, b), `idle_rounds` (a, b), `sample_ms`,
  `expected_idle_rounds`, `min_ratio`; the ratio and band checks move host-side; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004.
- **Blast carried by**: host assertions → M.HW_DEV.045.
- **Kind**: test, hardware (Round: R1 [H37])

## tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py

### M.HW_DEV.051 The loaded link: echo-checked multi-chunk SETs, both CRC modes, no recovery collect
- **From**: A.U26.87 (1), A.S0930.05, A.U17.05 (the churn loop's `gc.collect()` goes), A.U30.16 (`_heap_floor`,
  `_main` baseline rows), A.U1.25 (`:141` comment), A.U26.44 (pins), A.U26.24 (no raw FRAM write: no region needed),
  A.U5.12, A.U10.38 (`FRAMManager`, `UARTComm`), A.U10.44 (`_listen_loop` already the end name), A.U8C.95, A.U8C2.41,
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:1-232`.
- **Change**: (1) The responder keeps the last `_CMD_ECHO` SET payload (a script-local message callback in its
  callbacks object) and answers an `_CMD_ECHO` GET with it; the initiator loop alternates the banner GET with a
  multi-chunk `uart_set(_CMD_ECHO, <PAYLOAD_SIZE * 2 + 7 bytes, per-round pattern>)` and the echo GET, compared byte for
  byte; mismatches counted with the first five kept. (2) `_memory_churn_loop`'s `except MemoryError` keeps `held = []`
  and `load.alloc_failures += 1`, loses `gc.collect()`. (3) Pins, buses and FRAM from `BENCH` (i2c1 with its TOML
  frequency/timeout, SPI0, the FRAM CS and `fram_max_size`); the `:141` comment goes with the literals; `CRC_MODE` as
  in M.HW_DEV.046. (4) `print(f"GC_THRESHOLD=…")` → `fact("gc_threshold", …)`. (5) Constants per A.U8C.95/A.U8C2.41
  (`_RUN_MS`, `_MIN_TRANSFERS`, `_CHURN_BLOCK`, the step constants, `_MAX_RTT_FRACTION`, `_HEAP_FLOOR_SAMPLES`,
  `_HEAP_GROWTH_MAX_BYTES`), the `dev.uart_*` mirrors replaced by `BENCH`; `:121` → `arm()`. (6) Facts: `crc_mode`,
  `transfers`, `link_failures`, `worst_rtt_ms`, `timeout_ms`, `set_total`, `echo_intact`, `echo_mismatch` (bounded
  record), `error_counts`, the five load counters, `heap_at_third`, `heap_at_end`; the floors move host-side; `done()`.
- **Resolved**: A.U26.87 and A.S0930.05 edit the same script: the echo SET runs in both modes.
- **Unit**: U26 (A.U17.05's line lands in U17 on the HEAD text).
- **Depends**: M.HW_DEV.001-.005; U17's lock check (N.27) recorded either way.
- **Blast carried by**: README `:1265-1269` → A.U26.87 (3) (HW_BENCH); host assertions → M.HW_DEV.045.
- **Kind**: test, hardware (Round: R1 [H37])

## tests_hardware/device_scripts/uart_comm_hazards.py (new)

### M.HW_DEV.052 UART comm hazards H1a/H1b/H2/H3 across the jumper
- **From**: A.U26.82, A.U17.25 (the L3/L4 gap it closes), A.S0930.05 (both CRC modes), A.U36.539 (J.7 names it),
  A.U26.33 (`PeripheralInjector` the only fault source), A.U26.44, A.U26.68, LEAD/R28.
- **Site**: new `tests_hardware/device_scripts/uart_comm_hazards.py`.
- **Change**: as A.U26.82: two raw instances on `BENCH`'s UART pair, payload 48, timeout 100 ms, both poll rates 2 ms
  (a render extra overriding the TOML pair so the 30 ms floor holds), `CRC_MODE` from `BENCH`; H1a, H1b (three
  `clear()` points and `cancel_read_timeout()` mid-transaction), H2 (raw GET frame from the responder while the
  initiator awaits an ACK), H3 (the boundary value set of A.U17.25's CRC arm from the initiator's raw driver to a
  listening responder, one clean exchange after each); a recording wrapper on the responder driver's `read`; the
  injector shape of `uart_crossover_recovery.py`; `BENCH["part"]` (`"all"` | `"h1h2"`) selects the bench subset;
  every wait fed (`_shared/watchdog.py`), every loop yielding; facts per hazard, `done()`. Wear: none.
- **Resolved**: full value sweeps stay L1/L2 (wire cost on silicon); L3 proves the boundary set (A.U26.82).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005, A.U17.24 (verdict rules).
- **Blast carried by**: flash test → M.HW_DEV.045 (6); bench test under API load → A.U26.82 (HW_BENCH); J.7 tier
  map → A.U36.539 (SPEC); UART changelog — (a test).
- **Kind**: test, hardware (Round: R1 flash and bench [H37])

## tests_hardware/device_scripts/uart_link_echo_under_serving_load.py (new)

### M.HW_DEV.053 L4: the serving board's initiator carries an echoed multi-chunk SET
- **From**: A.U26.87 (2), A.U26.44 (device module from `BENCH`), A.U26.10 (the `main()`-based serving form keeps
  `cfg_path=""`), A.U20.02 (`watchdog=`), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/uart_link_echo_under_serving_load.py`.
- **Change**: boots `device = __import__(BENCH["device_module"])`'s `main(watchdog=arm())` as a task (the
  `serving_at_default_gc.py` pattern), waits for the webserver, then N times calls the initiator link's
  `uart_set(_CMD_ECHO, <multi-chunk>)` and `uart_get(_CMD_ECHO)` through its public API (no `src/` change), reporting
  `intact`/`total` and the exerciser's `Transfers`/`Failures` before and after as facts; every wait fed; `done()`.
  Wear: none beyond the serving boot's (listed in `_PREREQUISITE_DEVICE_SCRIPTS` with the serving scripts' reason).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.009, U17's lock check (N.27).
- **Blast carried by**: `bench/test_uart_link_under_api_load.py` new test → A.U26.87 (HW_BENCH); prerequisite listing
  → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R1 bench [H37])

## tests_hardware/flash/test_toolchain_flash_boot.py

### M.HW_DEV.055 Toolchain checks: the re-verify gated, the reflash through the one helper on the bench image
- **From**: A.U26.14 (2)-(4), A.S0930.06 (2) (the shared `reflash()`), A.C.06 (3)-(4) (R4 rows), A.U26.75 (`--no-sync`
  at `:35`, `:61`), A.U26.02 (blast: the build writes its image record beside the `.uf2`), A.U21.22 (blast: the build
  subprocess may now see the toolchain-lock message), A.U36.010 (blast: "hardcoded pins" text is A.U26.14's site),
  A.U1.06 (blast), A.U26.51, A.U20.33 (B2), A.U8C.109, A.U8C2.46.
- **Site**: `tests_hardware/flash/test_toolchain_flash_boot.py:1-92`.
- **Change**: (1) `test_env_tier_flash_recurring_run_is_idempotent` gains `@pytest.mark.toolchain_reverify` and the
  in-test skip "a full toolchain re-verification: network fetches and ~8 min of builds; pass
  --allow-toolchain-reverify"; its command is `["uv", "run", "--no-sync", "toolchain/setup_toolchain.py", …]`, timeout
  `_ENV_SETUP_TIMEOUT_S = 1200` (`l3.toolchain_flash_boot_env_setup_timeout_s`). (2) The smoke test takes
  `bench_device_name` (M.HW_BENCH.005): `uf2_path = REPO_ROOT / "build" / f"firmware-{name}.uf2"`, the build
  `["uv", "run", "--no-sync", "scripts/build_firmware.py", name, "--output", str(uf2_path)]` with
  `_BUILD_TIMEOUT_S = 600` (`l3.toolchain_flash_boot_build_timeout_s`), asserts the image record exists beside it,
  then `harness.reflash(board, uf2_path)`; the comment `:57-58` → "the bench board's image, built from its own TOML (a
  dev-native proof; wozi is never flashed, CLAUDE.md)"; the loop `:71-92` and its comment go into the helper. (3) The
  `Item 19/20/23` dividers become one `#` line each naming the check (no plan numbers, no "Part 2 item 8"); the
  BOOTSEL first-flash note keeps its one fact ("a blank board has no running firmware to enter the bootloader from").
  (4) `test_mpremote_connection_is_stable_across_repeated_calls`: `_REACHABILITY_CALLS = 5`
  (`l3.toolchain_flash_boot_reachability_calls`).
- **Resolved**: A.U26.14 (1) and A.S0930.06 (2) both rework the retry; one helper, M.HW_BENCH.014. A.U8C.109's
  `:82`/`:87` and A.U8C2.46's `:76` tags move with the loop into the helper (GAP-D5, HW_BENCH); the `:92` tags are
  withdrawn (the passive end has no `is_reachable()` poll).
- **Unit**: U26 (marker registration M.HW_BENCH.002).
- **Depends**: M.HW_BENCH.002/.005/.014, A.U26.02.
- **Blast carried by**: `_retryable_picotool_exit` L0 → A.U26.14 (TSC); `manual/manual_toolchain.py` the same device
  and path → A.U26.14 (HW_BENCH); twin record `exception` "needs the physical BOOTSEL path" → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R4 [H70]; re-verify R4)

## tests_hardware/flash/test_fram_storage.py

### M.HW_DEV.060 FRAM flash module: facts per script, five reset seams, the command-hold test
- **From**: A.U26.68 (`_run_and_assert_pass` goes), A.U26.43 (4) (seams × nonce), A.U16.07 (new test), A.U33.07 (its
  name), A.U35.22 (`:56` stays the N.28 proof), A.U16.19 (blast: `:97` keeps its subject), A.U0.28 (`:118` actor tag),
  A.U26.10/A.U26.22 (blasts: the capacity script builds over scratch; chunk scripts clear), A.U26.51 (`fram`,
  `construction`), A.U20.33 (B2), A.U8C.104.
- **Site**: `tests_hardware/flash/test_fram_storage.py:1-123`.
- **Change**: (1) Docstring `:1-3` → "Flash-tier tests of the real SPI FRAM chip (FRAMManager/asy_fram_driver): a
  mechanism separate from test_reboot_persistence.py's flash-filesystem config storage." (the part is the bench TOML's,
  not named here — see Adherence AF-2). (2) `RESULT_RE`/`_run_and_assert_pass` go; each test asserts its script's
  facts (named per script section below) with the values in the message. (3) The reset-race test is
  `@pytest.mark.parametrize("seam", [1, 2, 3, 4, 5])`: `nonce = secrets.randbelow(9000) + 1000`; phase 1
  `out = board.run_isolated_expect_reset(seed, timeout_s=…, SEAM=seam, NONCE=nonce)` asserts `SEEDED` and
  `LANDED seam=<seam>` in `out`; `wait_until(board.is_reachable, …)` (the next step enters the raw REPL anyway); phase 2
  with the same `NONCE` asserts `facts["history"]` is `[]` or three entries of `nonce` and the post-recovery write
  succeeded; the reached outcome goes to `result_note`. (4) New `test_fram_command_hold_stays_under_the_uart_poll_floor`
  runs `fram_command_hold_timing.py` and asserts `max(write_us, read_us) <= uart_floor_us` and `hold_us <=
  block_hold_budget_us` (facts). (5) Dividers: `:116` "WP4/Topic 6: …" → "# A firmware asking for more FRAM than its
  chip has is caught before flash, never as a boot-time console line nobody watches; mpremote-only by design, a
  one-time build-validity fact (owner, 2026-09-16)." (≤ 3 lines; the work label goes, G9/R12); `:59` "(owner,
  2026-09-11; Part C.3.1)" kept; `:105-107` "BACKLOG's SPI RX-overrun coverage" → "the SPI RX-overrun coverage" (no
  BACKLOG pointer for a closed item). (6) Timeouts: `_SHORT_SCRIPT_TIMEOUT_S = 30.0`, `_BACKUP_SCRIPT_TIMEOUT_S = 150.0`,
  `_SCRIPT_TIMEOUT_S = 60.0`, `_PAUSE_SCRIPT_TIMEOUT_S = 90.0`, `_LOCKOUT_SCRIPT_TIMEOUT_S = 45.0`,
  `_REACHABLE_TIMEOUT_S = 30.0`, `_REACHABLE_POLL_S = 1.0` (A.U8C.104's IDs); the hold test reuses
  `_SHORT_SCRIPT_TIMEOUT_S`.
- **Resolved**: A.U16.07 writes its test with `_run_and_assert_pass`, which A.U26.68 removes: it is written in fact
  form (M.HW_DEV.002). No marker on any test: FRAM is outside every wear gate (CLAUDE.md).
- **Unit**: U26 (A.U16.07's test lands in U16 in the HEAD helper form, rewritten here).
- **Depends**: M.HW_DEV.061-.071, M.HW_BENCH.012 (`run_isolated_expect_reset` returns output).
- **Blast carried by**: seam-count L0 (five `set_values_sync` per chunk write) → A.U26.43 (TSC); README FRAM reset-race
  section and the hold bullet → A.U26.43/A.U16.07 (HW_BENCH); twin record → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H22, H72])

## tests_hardware/device_scripts/fram_manager_roundtrip.py

### M.HW_DEV.061 Chunk round trip: `BENCH` wiring, the part's RDID as a fact, chunk cleared after
- **From**: A.U26.46 (RDID read and reported), A.U26.22 (5), A.U26.44, A.U5.02 (`debug=None` → `log`), A.U10.37
  (`asy_crc_checks`), A.U10.38 (`FRAMManager`), A.U16.R02 (blast: runs unchanged on a healthy chip), A.U26.79 (the
  write-protect read: see Resolved), A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_manager_roundtrip.py:1-43`.
- **Change**: `spi = asy_spi_driver.SPI(*BENCH["bus"]["spi0"] pins)`, `fram = FRAMManager(spi, BENCH["instances"]["fram"]
  ["cs_pin"], BENCH["fram_max_size"])` (the end-state signature `(spi_bus, spi_cs, max_size, log)`); `from
  asy_crc_checks import CRC8`; after `setup()` the RDID bytes are a fact (`rdid`, hex); write/read/compare as today
  reported as facts (`written`, `read_ok`, `matches`); the chunk is overwritten with zeros in a `finally` (production
  chunk 0 left holding no pattern); docstring keeps "the real FRAM part" without a part number (the part is the TOML's).
- **Resolved**: A.U26.79 (1) names "`fram_manager_roundtrip.py`'s WP read, a read-only fact" for the standard-state
  check, but this script writes chunk 0; the read-only WP status read lives in `fram_raw_dump.py` (which only reads),
  and the standard-state fixture reads it from the dump it already takes (agent decision AD-5; GAP-D6 for HW_BENCH).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.002/.006.
- **Blast carried by**: bench-facts table row "FRAM part (RDID)" → A.U26.46 (HW_BENCH); host assertions →
  M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_error_log_roundtrip.py

### M.HW_DEV.062 Error-log round trip with a test-band seed, cleared after
- **From**: A.U26.22 (5), A.U2.03 (seed code from the test band), A.U5.01 (`make_logger(LogConfig(…), name)`), A.U5.02,
  A.U10.37 (`asy_print_log`), A.U10.38, A.U28.28 (`:63` inline `noqa: B905` goes to central config), A.U26.44,
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_error_log_roundtrip.py:1-71` (HEAD lines `:25-63` as cited).
- **Change**: `TEST_ERRNO = 42` → `E_TEST_SEED = 125` (the catalog's test band, checked by A.U2.02 (9)); loggers via
  `make_logger(LogConfig(fram_a, history_length=_HISTORY_LENGTH), _LOG_NAME)`; managers from `BENCH`; facts
  `err_count`, `err_num`, `err_type`; the `zip(...)` line loses its inline `# noqa` (B905 is a central MicroPython-scope
  ignore, A.U28.28); `pr2.reset()` in a `finally` so the "TEST" entry never survives; the comment `:51-53` (three
  lines on narrowing) shortens to one.
- **Resolved**: —
- **Unit**: U26 (U5's `LogConfig` call shape lands in U5 on the HEAD text).
- **Depends**: M.HW_DEV.012, A.U2.01.
- **Blast carried by**: check (9) → A.U2.02 (TSC); central B905 entry → A.U28.28 (TOOL).
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py

### M.HW_DEV.063 The seed lands a reset on a named seam and seeds a nonce-chosen sequence
- **From**: A.U26.43 (2), A.U2.03 (test-band codes), A.U5.01, A.U5.02, A.U10.37, A.U10.38, A.U28.28 (`:49`),
  A.U8C.66 (`:17` → `_shared/watchdog.py`), A.U26.22 (5) (the seed ends in a reset by design; the verify clears),
  A.U26.44, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_error_log_reset_race_seed_and_race.py:1-71`.
- **Change**: `SEAM` (1-5) and `NONCE` from `BENCH`; the seed codes are `_SEED = [125 + (NONCE // 3 ** i) % 3 for i in
  range(3)]` and the raced entry `125 + NONCE % 3`; the script wraps its own driver instance's `set_values_sync` (an
  instance attribute set in the script, no product seam) to count the chunk write's transfers and, right after transfer
  `SEAM` returns, prints `LANDED seam=<SEAM>` and calls `machine.reset()`; the `reset_yanker` task and the stale comment
  `:60-64` go; `SEEDED` stays a banner (the stream is read before the reset, AD-3); `wdt = arm()`; facts for the
  pre-race failures (`seeded`, `baseline`) then `done()`.
- **Resolved**: A.U26.43 seeds "errno = `NONCE`" with a nonce of 1000-9999, but a log entry's code is 1..127
  (`src/print_log.py:61-64`, the range check `:168-172` drops anything larger) and A.U2.03 puts seed codes in the
  catalog's test band 125-127; so the nonce chooses one of 27 code sequences inside that band (AD-6). With the verify
  phase's `finally` clear (M.HW_DEV.064) and the `SEEDED`/`LANDED` banners, a stale seed still cannot pass.
- **Unit**: U26.
- **Depends**: M.HW_BENCH.012 (`run_isolated_expect_reset()` returns output), M.HW_DEV.004/.012.
- **Blast carried by**: seam-count L0 → A.U26.43 (TSC); host nonce `secrets.randbelow(27)` → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H72])

## tests_hardware/device_scripts/fram_error_log_reset_race_verify.py

### M.HW_DEV.064 The verify accepts only the three outcomes of this run's sequence, then clears
- **From**: A.U26.43 (3), A.U26.22 (5), A.U2.03, A.U5.01, A.U5.02, A.U10.37, A.U10.38, A.U28.28 (`:41`, `:57`),
  A.U26.44, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_error_log_reset_race_verify.py:1-69`.
- **Change**: the accepted outcomes are built from `NONCE` exactly as the seed builds them: `[]`, `_SEED`,
  `_SEED + [raced]` (the C.3.1 comment `:17-19` kept, owner 2026-09-11); any other history (a stale seed's included)
  is reported; the post-recovery entry uses `127`; facts `recovered`, `warnings`, `err_count`, `tail`, `outcome`; the
  chunk is reset in a `finally`; the comment `:31-32` ("Deliberately NOT cleared first") stays, now stating it is
  cleared last instead; the two inline `noqa` go (A.U28.28).
- **Resolved**: A.U26.43 (3) reads "exactly `[]` or three entries of `NONCE`"; a reset after the third or fourth
  transfer leaves the raced entry written too, which HEAD's `_ACCEPTED` (`:20`) already accepts as intact, so the
  four-entry outcome stays accepted (fact of the dual-block write order, C.3.1).
- **Unit**: U26.
- **Depends**: M.HW_DEV.063.
- **Blast carried by**: host per-seam outcome note → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H72])

## tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py

### M.HW_DEV.065 Boot-window reset on the real chip, test-band seed, cleared after
- **From**: A.U26.22 (5), A.U2.03 (`:12` seed 5 → test band), A.U5.01, A.U5.02, A.U10.37, A.U10.38, A.U26.44, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_error_log_reset_during_boot_window.py:1-65`.
- **Change**: `SEEDED_ERRNO = 5` → `E_TEST_SEED = 125`; loggers through `LogConfig`; managers from `BENCH`; the
  comment `:28-29` "Clear at the START, never at the end" → "Cleared at the start (a previous run's ring) and in
  `finally` (nothing seeded survives)"; facts `seeded_count`, `reset_persisted`, `after`, `persisted`; a `finally`
  resets the chunk.
- **Resolved**: the HEAD comment cites a README rule (clear at start only) that A.U26.22 (5)/OR38.a (4) replace.
- **Unit**: U26.
- **Depends**: M.HW_DEV.006/.012.
- **Blast carried by**: host assertions → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_busy_status_lockout.py

### M.HW_DEV.066 Busy-status lockout: its own chunk, facts, rewritten clean at the end
- **From**: A.U26.22 (5), A.U5.02, A.U10.37 (`asy_crc_checks`), A.U10.38, A.U26.44, A.U26.68, A.SDEP.08 (blast: the
  script is one of the on-target confirmations a pin move re-runs — listed in BACKLOG, no change here), B3 (the
  `_force_both_blocks_busy` docstring → `#` block).
- **Site**: `tests_hardware/device_scripts/fram_busy_status_lockout.py:1-73`.
- **Change**: wiring from `BENCH`; `check()` keeps its shape and its list feeds `fact("failures", …)` with the bounded
  record (`_shared/facts.py` `errors()`); facts `baseline_ok`, `locked_read_none`, `error_logged`, `recovered`; a
  `finally` rewrites the chunk with zeros (after the recovery write it holds `PATTERN_B`); the `_STATUS_BUSY`/`_STATUS_LEN`
  comment (const compiled away) stays.
- **Resolved**: the raw `set_values` calls address the script's own chunk (`chunk.block_addr`), not a scratch region;
  A.U26.24's region check must read calls addressed through a `get_chunk()` result as chunk-scoped (GAP-D7, TSC).
- **Unit**: U26.
- **Depends**: M.HW_DEV.006.
- **Blast carried by**: GAP-D7 (TSC); host assertions → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_write_protect_roundtrip.py

### M.HW_DEV.067 Write-protect round trip without the `override_pause` check
- **From**: A.U16.19 (`:42-43` override check goes), A.U16.10/A.U16.04 (blasts: the calls outside the lock hold),
  A.U26.22 (5), A.U5.02, A.U10.37, A.U10.38 (`FRAMChunk` type name), A.U26.44, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_write_protect_roundtrip.py:1-115` (HEAD `:42-43`, `:63`).
- **Change**: the `override_pause=True` read and its failure string go; `_while_protected` ends after the blocked read;
  wiring from `BENCH`; `TYPE_CHECKING` import names `FRAMChunk`; the phases' failure reasons become the fact
  `failure` (or none), plus `blocked_write`, `blocked_read`, `data_survived`; the `finally` still clears protection and
  then zeroes the chunk.
- **Resolved**: —
- **Unit**: U26 (A.U16.19's line lands in U16 on the HEAD text).
- **Depends**: M.SRC_CORE (A.U16.19 removes the keyword).
- **Blast carried by**: host assertions → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_pause_unpause_and_gating.py

### M.HW_DEV.068 Pause gating proven by unpaused read-back; the waiter-task unpause; bool-first writes
- **From**: A.U16.19 (steps 2-4, 10-11: the `override_pause` reads/writes/clear go; read back after `set_pause(False)`),
  A.U16.18 (`*_, written =` → `written, *_ =`, comment `:151-153`), A.U10.15 (the unpause callback only sets a flag: the
  script starts the waiter task), A.S0930.12 (blast: ignores `pause_permanent_storage()`'s result, holds; reads it
  where checked), A.U5.02 (`SystemService(…, fram=fram, debug=None)` → `storage=fram`), A.U10.37/A.U10.38 (`FRAMChunk`,
  `FRAMManager`, `asy_crc_checks`, `asy_system_service`), A.U26.22 (5), A.U26.44, A.U8C.67, A.U8C2.29, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_pause_unpause_and_gating.py:1-194`.
- **Change**: (1) Docstring `:1-3` → "…a pause genuinely prevents the bus write rather than only returning False, and a
  real machine.Timer auto-unpause fires (hardware-only, per Part F.1's soft-Timer gotcha)." (2) Step 2 proves the
  refused write by `set_pause(False)` then `read()` = `PATTERN_A`, then `set_pause(True)` again for step 3; step 4 goes
  (the seam is removed); step 10: a refused `clear()` is proven by unpausing and reading `PATTERN_A`, then an unpaused
  `clear()`; step 11: the paused timestamped write's refusal is proven by an unpaused read, and the "override" write
  becomes an unpaused write. (3) `written, *_ = await ts_chunk.write(…)` with the comment "write() returns
  (written, ntp_synced, utc); only the first is judged here (no NTP in an isolated script)". (4) `sysfunct =
  SystemService(_ntp_never_synced, storage=fram)` and the storage waiter task started (`asyncio.create_task(sysfunct.
  <waiter>())`, the method A.U10.15 names) before step 6, cancelled at the end. (5) `sleep_fed` and its docstring go:
  `fed_sleep_ms(wdt, …)` from `_shared/watchdog.py` (A.U8C.67's `feed_step_s` row withdrawn into the shared step);
  `_PAUSE_S = 2` (`l3.fram_pause_unpause_and_gating_pause_s`), `_REARM_S = 6` (`…_rearm_s`), `_PAUSE_MARGIN_S = 1.5`,
  `_REARM_MARGIN_S = 0.5` (A.U8C2.29); the alarm-pool loop bound `64` names its source as in M.HW_DEV.032.
  (6) `failures` → `fact("failures", …)` bounded; the chunk zeroed in a `finally`.
- **Resolved**: A.U16.19 removes the only means the HEAD script uses to look at the chip while paused; reading after
  unpausing proves the same thing (the bytes the paused write would have changed), as A.U16.19's blast states.
- **Unit**: U26 (U16/U10 call-shape edits land in their units on the HEAD text).
- **Depends**: M.SRC_CORE (A.U10.15 waiter, A.U16.18/.19, A.U5.02), M.HW_DEV.004/.006.
- **Blast carried by**: twin record (the auto-unpause is a real alarm-pool fact: `exception` for step 9 only, or a
  twin pool model → U25) → M.HW_DEV.010; host assertions → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/fram_same_device_rw_concurrency.py

### M.HW_DEV.069 FRAM read-vs-write concurrency over declared regions
- **From**: A.U26.24 (`READ_REGION` is production chunk 0 → evidence region; `WRITE_REGION` scratch), A.U13.08
  (blast: unchanged, must pass), A.U26.44, A.U26.69/A.U26.78 (loops), A.U8C.70, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_same_device_rw_concurrency.py:1-75` (`:13-14`, `:18`, `:22`, `:49`,
  `:61`).
- **Change**: `_EVIDENCE_REGIONS = ((0x0000, 32),)` (read only, under the session's evidence save) and
  `_SCRATCH_REGIONS = ((0x8000, 32),)`; `READ_REGION`/`WRITE_REGION` written from those tuples; the docstring's
  "datasheets/fram/" pointer kept; wiring from `BENCH`; `_READ_ITERATIONS = 30`, `_RUN_BOUND_S = 60.0`,
  `_WDT_FEED_EVERY = 5` (A.U8C.70's IDs); the reader/writer loops yield on every path and keep a bounded failure
  record; facts `reads_ok`, `reads_torn`, `write_ok`, `errors`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.004/.005/.007.
- **Blast carried by**: region check → A.U26.24 (TSC); host assertions → M.HW_DEV.080 (bus concurrency module).
- **Kind**: test, hardware (Round: R1 [H25-adjacent bus hazards])

## tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py

### M.HW_DEV.070 CS hijack: two new rungs (dropped WREN, chip lost), regions declared, owner tags
- **From**: A.U16.R01 (CS deasserted inside the first WREN: the write reads back intact), A.U16.R03 (CS held
  inactive across two block writes → errno 54 and `initialized` False; released → `setup()` succeeds, a write reads
  back), A.U0.18 (`:125`, `:161` "Hard requirement (owner, 2026-09-04):"), A.U13.09/A.U16.04 (blasts: unchanged),
  A.U26.24 (0x9000-0x93FF declared), A.U26.62 (3) (a fault-making script for `_FLASH_FAULT_SCRIPTS`), A.U26.44,
  A.U8C.65, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_cs_hijack_fault_injection_and_recovery.py:1-175`.
- **Change**: (1) `_SCRATCH_REGIONS = ((0x9000, 0x400),)`, the four address constants written from it, plus the new
  rungs' addresses inside it. (2) Scenario 3: `_CsHijack` gains an install point at the first WREN of a write
  (deassert inside it); the write's read-back equals the new pattern (the driver's one WREN retry). (3) Scenario 4: CS
  held inactive across two block writes; the driver logs errno 54 and `fram.initialized` is False; CS released,
  `await fram.setup()` succeeds and a write reads back. (4) `_CsHijack`'s docstring → `#` block: "Deasserts CS from
  inside the victim's own transfer, at the driver's synchronous seam: the CS window does not yield, so a racing task
  cannot land in it." (the "measure A"/archive-section history goes, G9/R12). (5) `:125`, `:161` → "# Hard requirement
  (owner, 2026-09-04): …". (6) `_VICTIM_BOUND_S = 30.0` (A.U8C.65); `arm()`; facts per scenario (`injected`,
  `readback_ok`, `raised`, `errno`, `recovered`), `done()`; the errno 54 compared host-side against the catalog name.
- **Resolved**: —
- **Unit**: U26 (the R01/R03 cases need U16's driver behaviour; written in U26 against it).
- **Depends**: M.SRC_CORE (A.U16.R01 WREN retry, A.U16.R03 chip-lost escalation), M.HW_DEV.004/.007/.012.
- **Blast carried by**: `_FLASH_FAULT_SCRIPTS` entry → A.U26.62 (TSC); README rungs table "participant: FRAM WREN" →
  A.U26.34 (HW_BENCH); twin `wren` fault op → A.U16.R01 (TWIN).
- **Kind**: test, hardware (Round: R1 [H16, H22])

## tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py

### M.HW_DEV.071 The raw reset race claims only what the part guarantees
- **From**: A.U26.52 (3), A.U26.24 (0xA000-0xA03F declared, shared with its verify phase), A.U13.09 (blast:
  unchanged), A.U26.44, A.U8C.68, A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_reset_race_during_write_seed_and_race.py:1-75` (`:1-3`, `:13-22`, `:56`,
  `:68`).
- **Change**: docstring and `:21` comment → "a reset landing before the payload transfer leaves the target unchanged;
  a reset during it may leave a prefix of the new bytes (MB85RS2MTA datasheet p.9: each byte is written as it is
  clocked in); the guards around the target are never touched" (the "must never land" claim goes); `_SCRATCH_REGIONS =
  ((0xA000, 0x40),)` with the four addresses from it; the comment naming the CS-hijack range goes (the check proves
  disjointness); the "measure A" wording at `:56` → the current fact (the write seam is synchronous); `arm()`;
  `_VICTIM_BOUND_S = 30.0`; the seeding failures are facts, the race keeps its banner (AD-3).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.004/.007.
- **Blast carried by**: host test (raw race in the bus-concurrency module) → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H72])

## tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py

### M.HW_DEV.072 The raw verify accepts the old pattern or a torn prefix, nothing else
- **From**: A.U26.52 (3), A.U16.04 (blast: unchanged), A.U26.24, A.U26.44, A.U8C.69 (`:25` → `arm()`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_reset_race_during_write_verify_recovery.py:1-70`.
- **Change**: the target region passes when it holds the original pattern, or a prefix of `_NEW_TARGET_PATTERN`
  followed by the original remainder (fact `target_state`: `"original"` | `"prefix:<n>"` | `"other"`); both guards
  must hold their patterns; the post-recovery write at `0xA030` (inside the declared region) reads back; the docstring
  says so; facts, `done()`; the region is restored to its seed state in a `finally` (scratch, but no stale torn bytes
  for the next run's assertion).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.071.
- **Blast carried by**: host assertion → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H72])

## tests_hardware/device_scripts/fram_capacity_after_full_system_build.py

### M.HW_DEV.073 Capacity check: derived logger set, scratch config, required watchdog, rig parked
- **From**: A.U26.23 (3) (`fram_wired`/`fram_backed_loggers` rendered; hand tuple goes), A.U20.06 (blast: setups run
  after construction), A.U20.11 (blast: the L1 half
  reads the same key), A.U26.10 (scratch `cfg_path`), A.U20.02 (`watchdog=`), A.U26.44 (device module from `BENCH`),
  A.U26.16 (the build constructs the NeoPixel: parked in `finally`), A.U36.544 (`:1` "WP4/Topic 6's real-hardware
  capacity check" → "the real-hardware FRAM capacity check"), A.U26.68.
- **Site**: `tests_hardware/device_scripts/fram_capacity_after_full_system_build.py:1-54`.
- **Change**: `device = __import__(BENCH["device_module"])`; `await device.build_system(watchdog=arm(),
  cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)` then `await device.sysfunct.run_setups(
  device._collect_setups())` (construction alone allocates no chunk once A.U20.06 moves the setup batch out of
  `build_system()`; A.U20.06's blast) (M.HW_DEV.009); `_CANDIDATE_MODULE_NAMES` and its
  comment go: for each label in `BENCH["fram_wired"]`, every logger of `getattr(device, label).get_loggers()` must
  have `fram is not None`; facts `found_fram_loggers` (sorted names), `ram_only` (labels/loggers without FRAM),
  `allocated_size`, `size`; the host asserts `found == BENCH["fram_backed_loggers"]` exactly (missing/extra named) and
  `ram_only == []`. The build's NeoPixel is set dark in a `finally`; the build's boot-phase mark cleared (M.HW_DEV.009
  (4)); the `assert device.fram is not None` becomes a fact. Header per A.U36.544 (≤ 3 lines).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.GEN (`expected_facts()` `fram_backed_loggers`, `get_loggers()`), M.HW_BENCH.010
  (`fram_backed_logger_names`), M.HW_DEV.001/.008/.009.
- **Blast carried by**: README capacity section → A.U20.11/A.U36.544 (HW_BENCH); host assertion → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py

### M.HW_DEV.074 The deinit/singleton pin-move check on the TOML's buses, chunk left clean
- **From**: A.U14.04 (`:29`, `:41` I2C constructed with the TOML's `timeout`), A.U26.58/A.C.03 (KEEP as a pin-move
  check, run in R1), A.U13.16 (blast: unchanged, raw `machine` objects), A.SDEP.08/A.SDEP.17 (the `:26-27` version
  floor follows the pin; re-run on a pin move), A.U26.22 (5) (its chunk at offset 0), A.U5.02, A.U10.37/38, A.U26.44,
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_deinit_is_a_noop_on_real_hardware.py:1-71`.
- **Change**: pins and bus parameters from `BENCH` (`:13-14` go): the I2C constructions pass `freq=bus["frequency"]`
  and `timeout=bus["timeout"]` when the TOML sets it (a re-construction resets both for every user of the static
  per-id object, `ports/rp2/machine_i2c.c:38, 50, 72, 87, 110`, v1.29.0); the SPI wrapper and FRAM from `BENCH`; the
  `:26` comment states the floor as "deinit() exists from 1.29 (raises AttributeError before)" against the pinned
  version; facts `i2c_has_deinit`, `scan_before`, `scan_after`, `i2c_singleton`, `spi_singleton`, `spi_read_after_deinit`;
  the chunk zeroed in a `finally`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.006.
- **Blast carried by**: SPEC F.5.1 on-target confirmation line and BACKLOG pin-move list → A.SDEP.08 (SPEC/DOCS);
  host assertions → M.HW_DEV.080 (bus concurrency module runs it).
- **Kind**: test, hardware (Round: R1 [H48])

## tests_hardware/flash/test_bus_concurrency.py

### M.HW_DEV.080 The flash bus-hazard module: one prerequisite, two owned writes, the new rungs
- **From**: A.U26.08 (1)-(4), A.U26.07 (fixture rename), A.U26.74 (old flag names in comments), A.C.19 (`:95-97`
  comment), A.U15.30 (blast: held), A.U26.43 (4) (raw race asserts its phase-1 banner), A.U13.R02 (4) (held-SDA
  recovery test beside the sweep), A.U35.21 (2) (lone-BMP3xx general-call test), A.U12.18 (SGP40 concurrent-sessions
  leg), A.S0930.28 (5) (erase racing a chunk write), A.S0930.39 (1) (reboot command, no torn chunk), A.U16.10/A.U13.08
  (blasts: must pass unchanged), A.U7.24 (3) (each test names its bench counterpart or exception row), A.U35.50/A.U35.09
  (blasts: matrix rows), A.U25.50 (blast: the twin comment naming this module's reset race, holds), A.U32.06/A.U26.32
  (blasts: holds; bench arm is HW_BENCH's), A.U26.68, A.U26.51, A.U20.33 (B2), A.U8C.102.
- **Site**: `tests_hardware/flash/test_bus_concurrency.py:1-149`.
- **Change**: (1) `RESULT_RE`/`_assert_pass` go; each test asserts its script's facts (per script section). (2) `:23-28`
  → `@pytest.mark.persistence_write def test_scd30_same_device_read_write_concurrency(board, scd30_measuring)` running
  `scd30_same_device_rw_concurrency.py` (it owns the ambient-pressure re-send); `:31, :38, :44, :68, :76` lose
  `persistence_write` and take `scd30_measuring`; their comments `:25-27, :70-71` say only what each test needs;
  `:85-92` keeps `persistence_write` + `scd30_extra_write`, takes `scd30_measuring`, comment `:88-90` → "owns two SCD30
  NVM writes (the offset and its restore), so it runs only with --allow-persistence-write and
  --allow-scd30-extra-write". No test depends on another's order. (3) `:95-97` → "# The script fails unless PRST counts
  whole RGB cycles, the unit persist_for_interval() assumes; / # whether a CONFIG1 write restarts a conversion is
  reported only." (4) The raw reset race: `out = board.run_isolated_expect_reset(…)` asserts its seeding banner and no
  failure fact, then `wait_until(board.is_reachable, …)` (the verify enters the raw REPL anyway), then the verify's
  `target_state` in `{"original", "prefix:<n>"}`; the comment `:132-134` shortens to one line. (5) New tests:
  `test_bmp3xx_alone_survives_a_general_call` (no marker; broadcasts ≥ planned, zero out-of-range reads, snapshot/ID/
  mode unchanged); `test_a_held_sda_line_is_cleared_and_every_device_answers` (beside the sweep); `test_sgp40_concurrent_
  sessions_each_get_a_tick` (three concurrent `measure_raw()` all return a tick); `test_fram_erase_racing_a_chunk_write_
  leaves_no_torn_chunk` and `test_reboot_command_shuts_down_then_resets` (each first `save_fram_raw(board, <name>)`, then
  `run_isolated_expect_reset()`, then after the production boot `fram_raw_dump.py`: no torn chunk, each ring's newest
  entry one the script reported written). (6) The `:122` comment's BACKLOG pointer ("open question 8's …") → "needs no
  separate fault-injection hardware: the RP2040 owns CS as a GPIO". (7) Each bus-hazard test's docstring-free `#` line
  names its bench counterpart (`bench/test_bus_concurrency_under_api_load.py::<fn>`) or the E.6.6 row ID. (8) Timeouts
  per A.U8C.102 (`_LONG_SCRIPT_TIMEOUT_S = 120.0`, `_SCRIPT_TIMEOUT_S = 90.0`, `_SHORT_SCRIPT_TIMEOUT_S = 60.0`,
  `_RESET_SCRIPT_TIMEOUT_S = 30.0`, `_REACHABLE_TIMEOUT_S = 30.0`, `_REACHABLE_POLL_S = 1.0`); new tests reuse them or
  take a row sized from the twin run.
- **Resolved**: A.U26.08 (1) keeps "asserts its RESULT line"; facts per A.U26.68 (later contract). A.S0930.28 (5) and
  A.S0930.39 (1) place one test each here as the flash tier of the four-tier rule; their scripts are new files below.
- **Unit**: U26 (SUPP_owner_0930 tests with U26).
- **Depends**: M.HW_DEV.020, M.HW_DEV.069-.074, .081-.098 (scripts), M.HW_BENCH.012/.044.
- **Blast carried by**: `test_level_containment.py` bench-counterpart check → A.U7.24 (TSC); budget text "two SCD30 NVM
  writes" → A.U26.09 (HW_BENCH); bench SCD30 write arm → A.U26.32 (HW_BENCH); four-tier matrix → A.U35.50 (U35 review);
  persistence-marker guard → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R1 default [H25, H29, H31]; R3 owned writes [H30, H31])

## tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py

### M.HW_DEV.081 SCD30 read-vs-write concurrency that re-sends the value the chip holds
- **From**: A.U26.08 (1) (docstring drops "the ONE script allowed…"; the writer re-sends `get_ambient_pressure()`
  instead of `1013` at `:67`), A.U26.07 (the start command moves to its own script; this one is no longer the
  prerequisite), A.U0.18 (`:2-3` owner tag), A.U26.49 (bounds from `plausibility_bounds.py` as render extras),
  A.U26.69 (bounded failure record), A.U26.44, A.U8C.84, A.U8C2.37, AD-1 (`:64`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/scd30_same_device_rw_concurrency.py:1-89`.
- **Change**: docstring → "Isolated-driver device script: the SCD30 same-device concurrency proof every device gets
  (owner, 2026-09-03; SPECIFICATION.md Part C.8): a reader against a concurrent ambient-pressure write that re-sends
  the value the chip reports, so its one NVM write leaves the setting unchanged." Bus from `BENCH`; the writer reads
  `prior = await scd.get_ambient_pressure()` first and sends it back (a failed read or a value neither 0 nor 700..1400
  → fact `write_skipped`, no send); CO2/humidity/temperature bounds from `BENCH["bounds"]`; the comment `:66` goes;
  `_READ_ITERATIONS = 40`, `_SETTLE_S = 12.0`, `_SETTLE_STEP_S = 0.5` (`:32`, `:35`), `_RUN_BOUND_S = 60.0`,
  `_WDT_FEED_EVERY = 10`, `_WRITER_DELAY_S = 0.2` (`l3.scd30_same_device_rw_concurrency_writer_delay_s`, AD-1); read
  errors as the bounded record; facts `read_completed`, `write_done`, `write_error`, `ambient_sent`, `errors`; `done()`.
- **Resolved**: A.U0.18 tags the HEAD sentence A.U26.08 rewrites; the tag is kept in the rewritten docstring.
- **Unit**: U26 (A.U0.18's tag lands in U0 on the HEAD text).
- **Depends**: M.HW_DEV.001-.005; M.HW_BENCH.043.
- **Blast carried by**: `_PERSISTING_DEVICE_CALLS` sees `set_ambient_pressure` and the runner is marked → A.U26.06
  (TSC); host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R3 [H31] — one owned NVM write)

## tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py

### M.HW_DEV.082 SCD30 reader vs snapshotter: bounds and schema ranges from their sources
- **From**: A.U26.49 (1)(4) (bounds rendered; `2..1800`/`400..2000` read from the driver's `_VAL_*` by `ast`), A.U26.07
  (blast: the `:18-20` comment naming the old fixture), A.U15.12 (blast: unchanged, must pass), A.U26.69, A.U26.44,
  A.U8C.62, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_concurrency_same_device_scd30.py:1-100`.
- **Change**: bus from `BENCH`; bounds `BENCH["bounds"]` and `BENCH["scd30_schema"]` (`MeasInterval`, `ForceCalRef`
  ranges, rendered from `src/asy_scd30_driver.py`); the comment `:29-31` → "# The SCD30 measurement prerequisite is the
  session's `scd30_measuring` fixture; this script writes nothing."; constants per A.U8C.62; bounded records; facts
  `reader_completed`, `snapshot_completed`, `errors`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: drift fence → A.U26.49 (4) (TSC); host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H31])

## tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py

### M.HW_DEV.083 SCD30 × SGP40 interleave, plus the two participant rungs mid-traffic
- **From**: A.U15.R01 (a step issuing `scd.reset()` while the SGP40 and ISL29125 loops run; every sibling read valid,
  SCD30 measuring again after 2.5 s), A.U15.R02 (a heater-off step, 0x3615, while the siblings run), A.U15.12 (blast:
  unchanged), A.U26.69/A.U26.78 (the `scd_loop`/`sgp_loop` bodies → `_shared/bus_reader_loops.py`; the failing branch
  yields; bounded record), A.U26.44, A.U26.07 (blast: comment `:23-25`), A.U8C.60, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_concurrency_cross_device_scd30_sgp40.py:1-104`.
- **Change**: bus and the ISL29125 mode constant from `BENCH`; the loops from the shared include; after the interleave
  phase: (a) an ISL29125 reader joins the siblings and `await scd.reset()` is issued mid-traffic (soft reset, no NVM),
  then the SCD30 must report a measurement within `_SCD30_RESUME_S = 2.5` (`l3.bus_concurrency_cross_device_resume_s`);
  (b) the SGP40 heater-off command mid-traffic, then one SGP40 read and sibling reads valid. Comment `:23-25` → "# The
  SCD30 measurement prerequisite is the session's `scd30_measuring` fixture; this script writes no NVM." Facts
  `scd_reads`, `sgp_cycles`, `interleaved_total`, `windows_with_interleaving`, `reset_sibling_errors`,
  `scd30_resumed`, `heater_off_sibling_errors`, `errors`; the interleave verdicts move host-side; `done()`.
- **Resolved**: A.U15.R01 and A.U15.R02 both add a step to this script; both kept, run in sequence after the
  interleave phase so its timing claim is measured unchanged.
- **Unit**: U26 (the rungs' product behaviour lands in U15).
- **Depends**: M.SRC_SENS (A.U15.R01/R02), M.HW_DEV.001-.005.
- **Blast carried by**: host assertions → M.HW_DEV.080; twin record → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H16, H25])

## tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py

### M.HW_DEV.084 The SCD30 writer restores the offset it found: two owned NVM writes
- **From**: A.U26.08 (3) (restore the prior offset read by `get_temperature_offset()`), A.U26.74 (`:3` flag names),
  A.U15.R01 (blast: holds), A.U26.44 (`_MODE_RGB` from `BENCH`), A.U26.69/A.U26.78, A.U26.32 (blast: bench arm is
  HW_BENCH's), A.U8C.63, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_concurrency_scd30_write_vs_siblings.py:1-112` (`:1-3`, `:15`, `:60-80`).
- **Change**: docstring `:1-3` → "…AND-gated behind --allow-persistence-write plus --allow-scd30-extra-write; it spends two
  SCD30 NVM writes (the offset and its restore)." The writer reads `prior = await scd.get_temperature_offset()` first
  (a failed read → fact `write_skipped`, no write), sends `4.0` mid-traffic, then after the siblings stop sends `prior`
  back; facts `prior_offset`, `write_done`, `write_error`, `restored`, `isl_windows`, `sgp_reads`, `errors`. The
  comment `:66-67` ("THE one extra real NVM write") → "# Owned writes: the offset, and its restore after the run."
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: budget text "two SCD30 NVM writes" → A.U26.09 (HW_BENCH); the persistence guard sees
  `set_temperature_offset` behind a marked runner → A.U26.06 (TSC); host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R3 [H30] — two owned NVM writes behind `scd30_extra_write`)

## tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py

### M.HW_DEV.085 ISL29125 config writes among sibling reads, through the shared loops
- **From**: A.U26.44 (`_MODE_RGB` copy), A.U26.69/A.U26.78, A.U15.S01/A.U15.R04/A.U15.33/A.U12.18 (blasts: unchanged,
  must pass), A.U8C.61, A.U8C2.27, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_concurrency_isl29125_write_vs_siblings.py:1-112`.
- **Change**: bus and `BENCH["isl29125"]["mode_rgb"]`; loops from the include; `_WRITE_DELAYS_MS` and
  `_DELAY_REPEATS` named with their rows; facts `write_count`, `isl_windows`, `scd_reads`, `sgp_reads`, `errors`;
  `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py

### M.HW_DEV.086 General-call regression: yielding loops, bounded records, rendered bounds
- **From**: A.U26.69 (`:63-85` named site: no yield on a failing read, one string per failure), A.U26.78 (the loops
  → include), A.U26.49 (bounds), A.U26.44 (`mode=0x05` at `:58` from `BENCH`), A.U15.15 (DONE-AT-HEAD: the ≥ 2 distinct
  CO2 values check, kept host-side), A.U15.13 (blast: unchanged), A.U26.07 (comment `:52-54`), A.U8C.88, A.U26.68.
- **Site**: `tests_hardware/device_scripts/sgp40_general_call_reset_hazard.py:1-130`.
- **Change**: `_failures()` goes (verdicts host-side); facts `sgp_completed`, `scd_completed`, `isl_completed`,
  `distinct_co2_count`, `errors` (bounded per chip); bounds from `BENCH["bounds"]`; the loops yield on every path;
  comment `:52-54` as M.HW_DEV.083's; constants per A.U8C.88; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: E.6.6 row `sgp40-general-call` (no L4 live-load counterpart) → A.U7.25 (SPEC); host assertions →
  M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/isl29125_cross_device_concurrency.py

### M.HW_DEV.087 ISL29125 interleave across its i2c1 neighbours
- **From**: A.U26.44 (`_MODE_RGB` `:16`), A.U26.69/A.U26.78 (`:61, 77, 91` loops), A.U8C.74, A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_cross_device_concurrency.py:1-125`.
- **Change**: `_failures()` goes; facts `isl_reads`, `scd_reads`, `sgp_cycles`, `interleaved`, `errors`; bus and mode
  from `BENCH`; loops from the include; the `:51` comment names the session fixture; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py

### M.HW_DEV.088 BMP3xx read-vs-write concurrency gains the reset-and-re-apply rung
- **From**: A.U15.R03 (a `reset()` + OSR/IIR re-apply concurrent with the read loop: reads in the reset window fail
  cleanly, after it valid with the re-applied OSR), A.U15.25 (blast: unchanged), A.U26.44 (i2c0, BMP3XX address from
  `BENCH`), A.U26.69, A.U8C.59, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bmp3xx_same_device_rw_concurrency.py:1-70`.
- **Change**: after the existing write-vs-read phase, a reset phase: the reader loop runs while one task calls the
  driver's reset path (soft reset plus stored-configuration re-apply, A.U15.R03's API); facts `reset_window_failures`
  (each a clean exception or `None`, no wrong value), `post_reset_valid`, `osr_after` (equal to the configured OSR);
  constants per A.U8C.59; bounded records; `done()`. Volatile registers only: no wear.
- **Resolved**: —
- **Unit**: U26 (the rung's product behaviour lands in U15).
- **Depends**: M.SRC_SENS (A.U15.R03), M.HW_DEV.001-.005.
- **Blast carried by**: host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H16, H25])

## tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py

### M.HW_DEV.089 ISL29125 read-vs-write concurrency, constants named
- **From**: A.U15.S01/A.U15.R04 (blasts: unchanged, must pass), A.U26.44, A.U26.69, A.U8C.80, AD-1 (`:53`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_same_device_rw_concurrency.py:1-90`.
- **Change**: bus and mode from `BENCH`; `_READ_ITERATIONS`, `_WRITE_ITERATIONS`, `_READ_STEP_MS`, `_WRITE_STEP_MS` with
  their rows; the `:53` settle kept as `_FIRST_CONVERSION_MS = 120` (`l3.isl29125_same_device_rw_concurrency_first_
  conversion_ms`, AD-1); facts `reads`, `torn_reads`, `writes_ok`, `errors`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.005.
- **Blast carried by**: host assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py

### M.HW_DEV.090 The live sweep: addresses from `BENCH`, a recovery step, heater-off, scan facts
- **From**: A.U26.44 (`KNOWN_ADDRESSES`/`_BUSES` `:23, :30` → `BENCH["addresses"]`/`BENCH["bus"]`), A.U13.R02 (4) (a step
  interleaving `recover()` with every discovered device's reads on a healthy bus), A.U15.R02 (the SGP40 command sweep
  adds 0x3615 and a sibling read after it), A.U15.28 (`:103, 110, 114` construct without `address=`), A.U28.28 (2)
  (the six `E731` lambdas become `def`s; their `noqa` go), A.U26.46 (the script prints `ADDRESSES bus=<id> <list>` →
  fact `addresses`), A.U15.13/A.U30.07/A.U12.18/A.U35.50 (blasts: unchanged, must pass), A.U8C.64, A.U8C2.28, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bus_topology_autodetect_and_hazard_sweep.py:1-180`.
- **Change**: buses and the address table from `BENCH`; drivers built without `address=` for the three hard-wired chips;
  the lambdas → named `async def`s; new step after the self-hazard branch: per bus, `recover()` interleaved with each
  discovered device's reads (status 0, reads unaffected); the SGP40 command list gains 0x3615 followed by one sibling
  read; facts `addresses` (per bus), `unknown_addresses`, `reserved_hits`, `self_hazard`, `recover_status`,
  `recover_sibling_errors`, `heater_off_ok`; constants `_BROADCAST_STEP_S`, `_RUN_BOUND_S`, `_SELF_READS`,
  `_BROADCASTS`; `arm()`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.SRC_SENS (A.U13.R02 `recover()`, A.U15.R02, A.U15.28), M.HW_DEV.001-.004.
- **Blast carried by**: README "Bench facts" table → A.U26.46 (HW_BENCH); central `E731`/`noqa` → A.U28.28 (TOOL); host
  assertions → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/i2c_held_sda_recovery.py (new)

### M.HW_DEV.091 A held SDA made on silicon, cleared by the bus rung; the boot-time clear
- **From**: A.U13.R02 (4) (the script), A.U26.34 (4) (second case: the boot-time bus clear before I2C construction),
  A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/i2c_held_sda_recovery.py`.
- **Change**: header ≤ 3 lines. Case 1: with the wrapper's bus lock held, bit-bang START, a discovered device's read
  address, the ACK clock, and stop SCL low after the ACK of a register whose first data bit is 0 (picked from the
  discovered set, recorded), so the slave keeps SDA low; a transfer then fails (`ETIMEDOUT`/`EIO`); `clear()` returns
  status 1 without 2; every device answers its identification and one valid read; the recovery's duration is a fact.
  Case 2: SDA held the same way, then the boot-time clear routine `build_system()` runs before constructing I2C is
  called; SDA reads high, the controller constructs and every device answers. Pins from `BENCH`; every wait fed;
  facts per case; `done()`. No write to any device register.
- **Resolved**: A.U26.34 adds case 2 to the script A.U13.R02 creates (A-C merge, as A.U26.34 states).
- **Unit**: U26 (U13's script, completed with U14's boot-clear function).
- **Depends**: M.SRC_SENS (A.U13.R02 `clear()`), A.U14.17 (boot clear), M.HW_DEV.001-.004.
- **Blast carried by**: flash test → M.HW_DEV.080 (5); README rungs table → A.U26.34 (HW_BENCH); BACKLOG hardware row
  (SCL/SDA behaviour on silicon) → A.U13.R02 (DOCS); `_FLASH_FAULT_SCRIPTS` entry → A.U26.62 (TSC).
- **Kind**: test, hardware (Round: R1 [H16])

## tests_hardware/device_scripts/bmp3xx_alone_survives_a_general_call.py (new)

### M.HW_DEV.092 A lone BMP3xx keeps its state through general calls
- **From**: A.U35.21 (1)(4), A.U26.44, A.U26.68, M.HW_DEV.004 (the script's `WDT(timeout=8000)` → `arm()`).
- **Site**: new `tests_hardware/device_scripts/bmp3xx_alone_survives_a_general_call.py`.
- **Change**: as A.U35.21 (1): i2c0 and the BMP3XX address from `BENCH`; distinctive volatile settings; snapshot, chip
  ID and PWR_CTRL bits before; a reader loop (range-checked against the datasheet operating range) concurrent with a
  broadcaster issuing `writeto(0x00, b"\x06")` through a lock-taking `I2CDevice(i2c0, 0x00)`, NAKs counted, fed between
  rounds; snapshot/ID/mode after; facts; schema defaults restored before exit; `done()`.
- **Resolved**: A.U35.21 writes `machine.WDT(timeout=8000)` "as every device script does"; the shared helper is that
  form now.
- **Unit**: U35 (B2's last hardware-facing pass), written in U26's form.
- **Depends**: M.HW_DEV.001-.004.
- **Blast carried by**: mock test `tests/test_bus_hazard_multi_device.py:271-306` deleted → A.U35.21 (TEST_UNIT); E.6.6
  row (no L4) → A.U35.21 (SPEC); flash test → M.HW_DEV.080.
- **Kind**: test, hardware (Round: R1 [H29])

## tests_hardware/device_scripts/sgp40_same_device_concurrent_sessions.py (new)

### M.HW_DEV.093 Three concurrent SGP40 measurements each get their own answer
- **From**: A.U12.18 (L3 script and flash leg), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/sgp40_same_device_concurrent_sessions.py`.
- **Change**: SGP40 on its `BENCH` bus; three concurrent `measure_raw()` calls with distinct T/RH; facts `ticks`
  (each a value in range, none `None`), `errors`; `done()`. Header states that silicon proves serialisation only (the
  chip CRC-checks what the overwriting caller also wrote), the payload being L1/L2's.
- **Resolved**: —
- **Unit**: U26 (A.U12.18 is U12; its L3 leg written in the fact form).
- **Depends**: M.HW_DEV.001/.002.
- **Blast carried by**: flash test → M.HW_DEV.080; SPEC C.8 sentence → A.U12.18 (SPEC).
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/flash/test_system_commands.py (new)

### M.HW_DEV.095 The system commands on the bench board over USB
- **From**: A.S0930.28 (1)-(4), (6)-(8), A.S0930.39 (2)-(5), A.S0930.19 (blast: `resetconfig` counts as persisting),
  A.S0930.33 (blast: the starve script holds), A.U26.22, A.U26.26, A.U26.47 (soak markers), A.U26.68, A.U26.51 (its
  `COVERS_TWIN_SCENARIOS`: the twin's command sequence runs, A.S0930.27), A.U31.01 (blast: the feed-gap figures are
  F.3 rows' measurements).
- **Site**: new `tests_hardware/flash/test_system_commands.py`.
- **Change**: header ≤ 3 lines; module constants for every bound (the 7.5-10.0 s hang window, the < 100 ms erase feed
  gap, `_TASK_CHECK_TIME + _RESET_DELAY` read from `src/asy_system_service.py` by `ast`). Tests, each saving FRAM
  evidence first where the command or a reset can touch it (`save_fram_raw(board, <name>)`): (1)
  `test_config_reset_deletes_every_config_file_and_reboots` `@pytest.mark.persistence_write` — production `config_*.cfg`
  names and bytes read before and after (read-only exec) unchanged, the scratch directory empty after; (2)
  `test_fram_erase_blanks_the_chip_and_every_logger_restarts_empty` — after the production boot `fram_raw_dump.py`: every
  byte outside the build's chunk layout 0x00, every chunk an empty ring or blank; (3) refusals — near-miss words
  "Invalid", no reset; `erasefram` with the chip write-protected → "Failed" and no reset for 10 s; (4) states — the erase
  and the reboot with a FRAM write and a bus session in flight, `mempause` active first; (6) the erase's feed gaps
  (< 100 ms inside S5, every gap < 8,000 ms) recorded through `result_note`;
  `test_a_hung_shutdown_step_ends_in_a_watchdog_reset` `@pytest.mark.persistence_write` (scratch writes) — reset
  7.5-10.0 s after the `HANG` line; (7) `test_a_reset_mid_erase_leaves_every_chunk_old_or_blank` — `hard_reset()` at
  0.2/1.0/2.0 s after `ERASE START`, raw dump: seeded ring or blank only; `test_bootloader_command_shuts_down_then_
  enters_bootsel` — step lines in order, serial loss, `sudo picotool reboot` exits 0, production boot serves; the hang
  case for `reboot`; (8) each test reads the output through `harness.MEMORY_ERROR_MARKERS`. The reboot no-tear test
  lives in `flash/test_bus_concurrency.py` (M.HW_DEV.080).
- **Resolved**: A.S0930.28's "prints the largest gap" and the step lines become facts/banners (AD-3 for the lines read
  before a reset); markers per A.U26.74's names (`--allow-persistence-write`).
- **Unit**: U26 (SUPP_owner_0930 with U26).
- **Depends**: M.SRC_CORE (A.S0930.09-.17 command sequence), M.HW_DEV.096-.101, M.HW_BENCH.012/.014.
- **Blast carried by**: persistence guard and marker completeness → A.U26.06/A.S0930.19 (TSC); `test_bench_restores_
  serving.py` covers the module → A.S0930.28 (TSC); README "System commands" subsection → A.S0930.28/.39 (HW_BENCH).
- **Kind**: test, hardware (Round: R1 default; R3 for the two `persistence_write` tests [H73])

## tests_hardware/device_scripts/system_command_config_reset.py (new)

### M.HW_DEV.096 `resetconfig` through the generated callback over a scratch store set
- **From**: A.S0930.28 (1)(4), A.U26.10/A.U26.18 (scratch path removed on every path), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/system_command_config_reset.py`.
- **Change**: builds the generated bench system over `_SCRATCH_CFG_PATH` with `watchdog=arm()` (M.HW_DEV.009), writes one
  changed value per store (each scratch file exists), reports the scratch listing, then calls the generated
  `_system_cmd_callback("resetconfig")` and lets the product reset end the run (`run_isolated_expect_reset()`); a
  pre-reset failure removes the scratch directory and reports; `STATE` extras select the in-flight variants of (4).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.009, M.SRC_CORE (A.S0930.11 callback).
- **Blast carried by**: `_PERSISTING_DEVICE_CALLS`/`build_system(` scratch rule (scratch writes are persisting; runner
  marked) → A.U26.06 (TSC); the post-reset read-only listing → M.HW_DEV.095.
- **Kind**: test, hardware (Round: R3 [H73])

## tests_hardware/device_scripts/system_command_fram_erase.py (new)

### M.HW_DEV.097 `erasefram` with a recording watchdog proxy
- **From**: A.S0930.28 (2)(4)(6)(7), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/system_command_fram_erase.py`.
- **Change**: builds the generated system over the scratch path; wraps `sysfunct.watchdog` from outside with a proxy that
  forwards `feed()` and records `ticks_ms()`; optional in-flight loads (a logger-write loop, an I2C read loop) and
  `mempause` by `STATE` extra; prints `ERASE START` before the callback, then the facts streamed before the reset
  (largest feed gap, erase duration) — read from the captured stream (AD-3).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.009.
- **Blast carried by**: M.HW_DEV.095 (2)(6)(7); M.HW_DEV.080's erase-race test.
- **Kind**: test, hardware (Round: R1 [H72, H73])

## tests_hardware/device_scripts/system_command_hang.py (new)

### M.HW_DEV.098 A shutdown step that never returns ends in the watchdog reset
- **From**: A.S0930.28 (6), A.S0930.39 (3), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/system_command_hang.py`.
- **Change**: builds the generated system over the scratch path; replaces, from outside, one store's `delete_file`
  (`COMMAND="resetconfig"`) or `flush_pending` (`COMMAND="reboot"`) with a never-ending coroutine; issues the command;
  prints `HANG <ticks>` after the last own feed; the host times the serial loss.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.009.
- **Blast carried by**: M.HW_DEV.095; `_FLASH_FAULT_SCRIPTS` → A.U26.62 (TSC).
- **Kind**: test, hardware (Round: R3 [H73])

## tests_hardware/device_scripts/system_command_reboot.py (new)

### M.HW_DEV.099 `reboot`/`bootloader` with the shutdown steps visible
- **From**: A.S0930.39, A.U25.69 (`debug` keyword kept), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/system_command_reboot.py`.
- **Change**: `COMMAND` from `BENCH`; builds the generated system over the scratch path with `debug=4`, starts
  `start_tasks(...)` and `supervise_tasks()` as its task, a logger-write loop and an I2C read loop, wraps the watchdog
  with the recording proxy, calls `_system_cmd_callback(COMMAND)`; each written log entry is reported before the reset
  so the host can check each ring's newest entry after the production boot.
- **Resolved**: A.S0930.39 shares the proxy with A.S0930.28 (6): one shape, written in each script (an `_shared/
  watchdog_proxy.py` include if the clone check flags the two copies, A.U26.78 (3)).
- **Unit**: U26.
- **Depends**: M.HW_DEV.009.
- **Blast carried by**: M.HW_DEV.080 (no-tear test), M.HW_DEV.095.
- **Kind**: test, hardware (Round: R1 [H72])

## tests_hardware/device_scripts/config_files_dump.py (new)

### M.HW_DEV.100 Read-only dump of every config file
- **From**: A.S0930.29 (1).
- **Site**: new `tests_hardware/device_scripts/config_files_dump.py`.
- **Change**: lists `config_*.cfg` and prints each verbatim as one fact (`files`: name → base64 text); opens read-only,
  writes nothing; `done()`.
- **Resolved**: the dump carries the real WiFi credential into the run's evidence directory (Adherence AF-4).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.002.
- **Blast carried by**: `bench/test_system_commands.py` (save through `evidence.save_text`) → A.S0930.29 (HW_BENCH).
- **Kind**: test, hardware (Round: R3 bench [H73])

## tests_hardware/device_scripts/config_files_restore.py (new)

### M.HW_DEV.101 Write the saved config files back verbatim
- **From**: A.S0930.29 (1), A.U26.06 (its writes are the owning test's).
- **Site**: new `tests_hardware/device_scripts/config_files_restore.py`.
- **Change**: takes `files` as a render extra and writes each verbatim (one flash write per file, owned by the gated
  bench test); reports `written`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.100.
- **Blast carried by**: the persistence guard (a raw `open(...,"w")` in a device script is persisting: add `write`-mode
  `open` to `_PERSISTING_DEVICE_CALLS`'s detection) → GAP-D8 (TSC).
- **Kind**: test, hardware (Round: R3 bench [H73])

## tests_hardware/flash/test_bus_electrical_timing.py

### M.HW_DEV.105 Electrical/timing module: rollover moves to the bench, soak by duration, country probe added
- **From**: A.U26.36 (`:95-138` removed: the rollover test moves to `bench/test_ticks_ms_rollover.py`), A.U26.35/A.U26.74
  (`soak_tiers`/`SOAK_TIER_SECONDS`/`--soak-tier`/`long_soak` → `soak_durations`/`SOAK_DURATION_SECONDS`/
  `--soak-duration`/`soak_duration`; docstring `:2-3`), A.U26.81 (the clock-stretch soak claims only the absence of
  failure over its window), A.U26.07 (`test_scd30_real_irq_edge_drives_a_real_read` takes `scd30_measuring`), A.U26.58
  (blast: asserts the forced drop's facts), A.C.14 (new `test_a_malformed_country_code_reaction_is_recorded` beside the
  float test), A.U36.544/A.U33.09 (the BACKLOG item 12 citations `:99, :135` go with the moved test), A.U26.68,
  A.U26.51 (`scd30`), A.U20.33 (B2), A.U8C.103 (`:59`; the `:107` row moves), A.U8C2.44 (moves), A.U8C.119 (blast:
  import renamed).
- **Site**: `tests_hardware/flash/test_bus_electrical_timing.py:1-138`.
- **Change**: (1) Docstring → "Flash-tier tests of real bus/electrical timing no simulation reproduces, through
  isolated-driver scripts. The clock-stretch soak needs --soak-duration." (2) `_parse_result` goes; facts asserted:
  scheduler (`dropped >= n_timers - depth`, `all_self_healed`, `arming_span_us <= 1500`), alarm pool (`errno ==
  ENOMEM`, `constructed` recorded through `result_note`), IRQ edge (`co2_within_deadline`), float boundary (`below_exact`,
  `above_rounded_to == 2**24`). (3) The soak test: `@pytest.mark.soak_duration`, `duration_s =
  SOAK_DURATION_SECONDS[request.config.getoption("--soak-duration")]`; boot/crash lines through `harness.crash_lines()`
  plus the SCD30/`ETIMEDOUT` filter; the skip text names `--duration`; its comment states it proves absence of failure
  over the window only. (4) `:95-138` (`_WRAP_FLOOR_MS`, the rollover test, its comments) deleted; their tags move with
  the test (HW_BENCH). (5) `test_a_malformed_country_code_reaction_is_recorded(board)`: runs
  `wifi_country_code_reaction.py`, asserts every step reported and `restored == "ok"`, records the facts, then
  `restore_board_to_serving()`. (6) Dividers "Item N - …" → one `#` line each naming the subject; `_IRQ_SCRIPT_TIMEOUT_S
  = 30.0`.
- **Resolved**: A.U8C.103's `:107` and A.U8C2.44's rows tag lines A.U26.36 moves: the tags go with them to the bench
  module (B4).
- **Unit**: U26 (A.C.14's test is a phase-C instrument written before R1, U26 form).
- **Depends**: M.HW_BENCH (soak durations, `bench/test_ticks_ms_rollover.py`), M.HW_DEV.020, .106-.110.
- **Blast carried by**: the rollover test and its two tag rows → A.U26.36 (HW_BENCH); twin record: IRQ edge, scheduler
  and pool `exception` ("needs the rp2 scheduler/alarm pool/GPIO") → M.HW_DEV.010.
- **Kind**: test, hardware (Round: R1 [H48, H51]; soak R5)

## tests_hardware/device_scripts/scheduler_saturation_drop.py

### M.HW_DEV.106 The scheduler probe forces the drop and counts it
- **From**: A.U26.58, A.U26.77 (README "a starting guess" goes with it), A.U35.28 (blast: the load cell names it),
  A.U8C.85, A.U26.68.
- **Site**: `tests_hardware/device_scripts/scheduler_saturation_drop.py:1-57`.
- **Change**: as A.U26.58: `_N_TIMERS = 12` periodic 1 ms timers armed back to back; three straight-line
  `time.sleep_us(900)` right after arming (no branch between them, so the VM drains nothing); `arming_span_us`
  reported; counts read once: `dropped = sum(1 for c in counts if c == 0)` with `depth` from `BENCH` (rendered from the
  pinned `ports/rp2/mpconfigport.h`); then the 500 ms heal window and every timer firing again; facts `dropped`,
  `depth`, `n_timers`, `arming_span_us`, `counts_busy`, `counts_heal`, `all_self_healed`; header states what it forces
  and why (≤ 3 lines; "Widen BUSY_WAIT_MS if …" goes). `_TIMER_PERIOD_MS` row reads 1; `_HEAL_WINDOW_MS = 500`;
  `l3.scheduler_saturation_drop_busy_wait_ms` withdrawn (the busy-wait is now three 900 µs calls,
  `l3.scheduler_saturation_drop_busy_step_us = 900`).
- **Resolved**: A.U8C.85 tags the HEAD constants A.U26.58 replaces; the rows follow the new form.
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.002.
- **Blast carried by**: twin fidelity row "scheduler queue not modelled" → A.U26.58 (TWIN); README `:514-515` → A.U26.77
  (HW_BENCH).
- **Kind**: test, hardware (Round: R1 [H48])

## tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py

### M.HW_DEV.107 Alarm-pool exhaustion: header cites F.1, the count is `len(timers)`
- **From**: A.U28.28 (6) (`for _ in range(64):`, reports read `len(timers)`, the `B007` noqa goes), A.U14.12 (header
  "confirming … Part F.2's claim" → F.1; `constructed` recorded with the image's other pool users), A.U26.58/A.C.03 (KEEP
  as a pin-move check), A.U25.01/A.U35.28 (blasts: hold), A.U26.68.
- **Site**: `tests_hardware/device_scripts/timer_alarm_pool_exhaustion.py:1-28`.
- **Change**: header → "…confirming SPECIFICATION.md Part F.1 against real silicon; `constructed` is the free alarms at
  that moment, not the pool size."; loop `for _ in range(64):` with a one-line comment naming 64 as the upper bound;
  facts `constructed` (`len(timers)`), `errno`, `raised`; `finally` deinit kept; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.002.
- **Blast carried by**: BACKLOG owed row "record `constructed=N`" → A.U14.12 (DOCS); host → M.HW_DEV.105.
- **Kind**: test, hardware (Round: R1 [H48])

## tests_hardware/device_scripts/scd30_real_irq_edge.py

### M.HW_DEV.108 SCD30 RDY edge on the TOML's pin, new constructor shape
- **From**: A.U5.02 (`SCD30_Reader(i2c1, 11, trigger_sec=…, max_module_error=999, fram=None, debug=None)` → the
  `log`-tail shape), A.U10.43 (`trigger_sec` unit suffix), A.U10.44 (`read_loop`/`scd_init_irq` → `_<what>_loop` names,
  found by mypy), A.U26.44 (bus and `irq_pin` from `BENCH`), A.U26.07 (runs under `scd30_measuring`), A.U8C.83,
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/scd30_real_irq_edge.py:1-48`.
- **Change**: `reader = SCD30_Reader(i2c, BENCH["instances"]["scd30"]["irq_pin"], trigger_s=_TRIGGER_S,
  max_module_error=999)`; task coroutines by their end names; `_FAST_PATH_DEADLINE_S = 5.0`, `_POLL_MS = 100`; facts
  `co2`, `elapsed_ms`, `deadline_ms`; `done()`. Header keeps "a scope on the pin is the only certain check" (E.6.6 row
  `scd30-rdy-irq-vs-fallback`).
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.SRC_SENS (constructor and loop names), M.HW_DEV.001/.002.
- **Blast carried by**: host → M.HW_DEV.105.
- **Kind**: test, hardware (Round: R1 [H48])

## tests_hardware/device_scripts/float_boundary_2pow24.py

### M.HW_DEV.109 The 2**24 boundary through the private float coercion
- **From**: GAP-G13 (M.SRC_CORE: `coerce_numeric()` becomes `_coerce_int()`/`_coerce_float()`; this script calls the
  private half), A.U10.37 (`asy_config_manager`), A.U26.58/A.C.03 (KEEP, R1), A.U14.28 (blast: an F.7 divergence row cites
  this style of check), A.U26.68.
- **Site**: `tests_hardware/device_scripts/float_boundary_2pow24.py:1-40`.
- **Change**: `from asy_config_manager import _coerce_float`; below and above the boundary through it; facts
  `below_exact`, `above_value`, `above_rounded_to_2pow24`; the comment at `:7-8` ("kept only for parity") and the
  `sys.path.insert` go (frozen modules import without it, as the comment itself says); `done()`.
- **Resolved**: the `sys.path` line is dead by its own comment; removed with the rewrite (agent decision AD-7).
- **Unit**: U26 (after U11's rename).
- **Depends**: M.SRC_CORE.047.
- **Blast carried by**: host → M.HW_DEV.105.
- **Kind**: test, hardware (Round: R1 [H48])

## tests_hardware/device_scripts/wifi_country_code_reaction.py (new)

### M.HW_DEV.110 Record the radio's reaction to malformed country codes
- **From**: A.C.14, A.U26.20 (its predecessor script is deleted), A.U26.44 (the TOML's country for the restore),
  A.U26.68, M.HW_DEV.004.
- **Site**: new `tests_hardware/device_scripts/wifi_country_code_reaction.py`.
- **Change**: as A.C.14: for `"ZZ"`, `"12"`, `"\x01\x02"`: `WLAN(STA_IF).deinit()`, `network.country(v)`, a fresh
  `WLAN(STA_IF).active(True)`, one `scan()`; one fact per value (`set`, `radio_on`, `scan_count`, `readback`); `finally`
  restores `BENCH`'s country and radio-on (`restored`); fed between steps; the sequence checked against
  `extmod/network_cyw43.c` at the pinned tag before it lands; `done()`.
- **Resolved**: —
- **Unit**: phase C (written before R1, U26 form).
- **Depends**: M.HW_DEV.001/.002/.004.
- **Blast carried by**: SPEC row for the reaction → A.C.14 (SPEC); host → M.HW_DEV.105.
- **Kind**: test, hardware (Round: R1 [H51])

## tests_hardware/device_scripts/wifi_country_hostname_edge_values.py (deleted)

### M.HW_DEV.111 The country/hostname edge script is deleted
- **From**: A.U26.20, A.C.14 (its "XX" was MicroPython's own default), A.U26.45/A.U26.61 (blasts on the deleted file).
- **Site**: `tests_hardware/device_scripts/wifi_country_hostname_edge_values.py`.
- **Change**: deleted; the byte-bound cases move to `bench/test_network_resilience.py` (A.U26.20, HW_BENCH), the country
  reaction to M.HW_DEV.110.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: —
- **Blast carried by**: `_JUSTIFIED_UNMARKED` reason → A.U26.20 (TSC); twin record entry removed → A.U26.05 (TSC).
- **Kind**: test

## tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py, wifi_service_reconnect_repro.py (deleted)

### M.HW_DEV.112 Both WiFi reconnect repro scripts are deleted
- **From**: A.U26.19 (deletes both; the committed PSK leaves the tree, its history is G5/R59's U29 scan), A.U29.04 (the
  history disposition), A.U26.61 (two of its three named feeders go with the files), A.U18.R01 (its planned L3 step
  moves to `wifi_radio_reinit_recovery.py`, A.U26.34 (3)), A.U26.45 (`sensornode-dev`, `wozi-diag…` identifiers go with
  the files), A.U1.06 (blast: `:41-52` broke the tool-write rules — moot), A.U5.02/A.U5.09/A.U10.43/A.U18.27/A.U18.40/
  A.U18.42/A.U28.29/A.U8C.98/A.U8C.99/A.U8C2.43 (edits of these files: moot).
- **Site**: `tests_hardware/device_scripts/wifi_reconnect_after_failed_attempts_repro.py`,
  `wifi_service_reconnect_repro.py`.
- **Change**: both files deleted (neither has a runner: "NOT part of the routine test suite", `:1`); `pyproject.toml:343`
  (their `S106` per-file ignore) goes and `:338` reads "# S105: tests that join …"; the comment at
  `tests_scripts/test_device_script_config_flush.py:70` names no deleted file; `tests_hardware/README.md:383-385` (the
  Timer-fed wrapper recipe) goes.
- **Resolved**: every other action editing these files (renames, tags, constructor shapes) is dropped: the file it
  edits is deleted in U26, and the edits in earlier units (U5, U10, U18) are skipped rather than made and deleted, since
  no runner exercises them (the U8C/U8C2 rows on them are withdrawn).
- **Unit**: U26 (earlier units skip these two files: a moot edit is not made; GAP-D9 tells U5/U10/U18 executors).
- **Depends**: M.HW_DEV.113.
- **Blast carried by**: `pyproject.toml` lines → A.U26.19 (TOOL); README recipe → A.U26.19 (HW_BENCH); flush-test
  comment → A.U26.19 (TSC); history scan of the PSK → A.U29.04 (SEC/TOOL); twin record entries removed → A.U26.05 (TSC).
- **Kind**: test

## tests_hardware/device_scripts/wifi_radio_reinit_recovery.py (new)

### M.HW_DEV.113 The WiFi radio re-init rung on silicon, no config write
- **From**: A.U26.34 (3), A.U18.R01 (`_recover_device()`), A.U26.10 (scratch config path), A.U26.44, A.U26.68,
  M.HW_DEV.004.
- **Site**: new `tests_hardware/device_scripts/wifi_radio_reinit_recovery.py`.
- **Change**: reads the production `config_WIFI.cfg` read-only (`json.load(open(...))`), constructs `WifiService` over
  `_SCRATCH_CFG_PATH` with its manager primed in RAM from those values (the priming pattern of
  `isl29125_plausibility_read.py`), connects, calls `_recover_device()` and reports `reconnected`, `ip`, `elapsed_ms`
  within the connect budget; fed throughout; no config write; `done()`. The credentials stay on the board (never
  printed).
- **Resolved**: A.U26.34 (3) names "its flash-tier caller" in Site and `bench/test_wifi_radio_reinit.py` (L4, the AP
  must be up) in Change; the Change governs: the runner is the bench module (HW_BENCH).
- **Unit**: U26 (after U18's rung).
- **Depends**: M.SRC_NET (A.U18.R01), M.HW_DEV.001/.004/.009.
- **Blast carried by**: `bench/test_wifi_radio_reinit.py` → A.U26.34 (HW_BENCH); README rungs table → A.U26.34
  (HW_BENCH).
- **Kind**: test, hardware (Round: R1 bench [H16])

## tests_hardware/flash/test_memory_stress.py

### M.HW_DEV.115 Heap headroom with named thresholds; soak by duration; the timing scripts' tests
- **From**: A.U26.48 (1)(3) (every `GC_THRESHOLD` fact extracted and named in each message; `WORST_CASE_ALLOCATION`
  imported from `heap_bounds.py`), A.U26.26 (the soak uses `boot_lines()`/`crash_lines()`; the inline marker comment
  goes), A.U26.35/A.U26.74 (`soak_duration`), A.U31.05 (two new tests), A.U31.06 (3) (the loop-lag test), A.U30.18 (the
  C-stack test, "U26's runner convention"), A.U30.04 (blast: the ≤ 100,000 B bound now counts the VOC algorithm — phase C
  re-reads), A.SDEP.08 (blast: a pin move re-runs the headroom test), A.U0.34 (blast: the `GC_THRESHOLD` echo is U26's
  code), A.U26.10 (blast: the headroom script builds over scratch), A.U26.68, A.U26.51 (`construction`), A.U20.33 (B2),
  A.U8C.105, A.U8C2.45.
- **Site**: `tests_hardware/flash/test_memory_stress.py:1-105`.
- **Change**: (1) `WORST_CASE_ALLOCATION` and its two comment blocks (`:22-28`) → `from heap_bounds import
  WORST_CASE_ALLOCATION`. (2) The headroom test: `facts = parse_facts(out)`; `thresholds = facts["gc_threshold"]` (each
  stage) printed through `result_note` beside the `HEAP` facts; assertions `facts["used"] <= facts["max_used"]` and
  `facts["largest_block"] >= facts["min_largest_block"]`, each message naming the threshold in force; the map checks keep
  `heap_map.parse_labelled(out)` (the `mem_info(1)` map is a raw block the script prints between facts) with
  `_PROBE_MAP_TOLERANCE_BLOCKS = 2`; the "archive 7F.6"/"MEASUREMENTS M2.x" history in comments `:36-38, :49-51,
  :58-66` → the current reason in ≤ 3 lines each (the owner tag "(owner, 2026-09-19)" kept). (3) The soak test:
  `@pytest.mark.soak_duration`, `SOAK_DURATION_SECONDS[...]`, `harness.boot_lines(lines)`/`crash_lines(lines)`.
  (4) New tests: `test_routine_no_yield_stretches_stay_under_the_gc_term(board)` (`loop_stretch_timing.py`: every max ≤
  `routine_stall_us`), `test_flash_write_loop_gap_is_recorded(board)` `@pytest.mark.persistence_write`
  (`flash_write_loop_gap.py`, recorded, never failed on the figure), `test_loop_lag_under_combined_load_stays_under_
  the_uart_reply_budget(board)` (bench round only, after the round's evidence save), `test_c_stack_peak_is_within_half_
  the_limit(board)` (`c_stack_budget.py`: `peak <= limit // 2`). (5) `_HEADROOM_SCRIPT_TIMEOUT_S = 120.0`.
- **Resolved**: A.U31.05/A.U31.06/A.U30.18 write "RESULT: PASS/FAIL" verdicts on the board; facts per M.HW_DEV.002.
- **Unit**: U26 (the U30/U31 tests written in U26 form when those units land).
- **Depends**: M.HW_BENCH.046, M.HW_BENCH.016, M.HW_DEV.116, .122-.125.
- **Blast carried by**: `tests_scripts/test_device_script_gc_threshold.py` alias resolution and `FACT gc_threshold=` marker
  → A.U26.48 (2) (TSC); `_PREREQUISITE`/marker guard for the flash-write gap test → A.U26.06 (TSC); F.3 budget rows →
  A.U31.01 (SPEC).
- **Kind**: test, hardware (Round: R1 [H23, H44]; soak R5; loop lag R1 bench [H20])

## tests_hardware/device_scripts/heap_headroom_after_full_system_build.py

### M.HW_DEV.116 Headroom after the full boot batch, scratch config, facts, shared probe
- **From**: A.U26.10 (`:105` scratch `cfg_path`), A.U20.02 (`watchdog=`), A.U20.06 (blast: setups run after
  construction), A.U26.44 (device module), A.U26.48 (3) (`WORST_CASE_ALLOCATION` rendered; actor comments), A.U26.78
  (`_largest_block`/`_report_checked`/`_dump_map` → `_shared/heap_probe.py`), A.U25.61 (probe constants equal across both
  scripts — structural once shared), A.U30.16 (baseline rows: in the include now), A.U0.28 (`:34` "(agent,
  2026-09-19)"), A.U8.14 (`:117` `gc.threshold(32768)` mirror tag), A.U27.09 (blast: the `typecheck.sh` comment naming
  this script's static import), A.U8C.71, A.U8C.72 (shared IDs), A.U8C2.30, A.U31.05 (blast: the stretch script builds
  as this one does), A.U26.68.
- **Site**: `tests_hardware/device_scripts/heap_headroom_after_full_system_build.py:1-131`.
- **Change**: `device = __import__(BENCH["device_module"])`; `await device.build_system(watchdog=arm(),
  cfg_path=_SCRATCH_CFG_PATH, web_host="127.0.0.1", web_port=8080)` then `await device.sysfunct.run_setups(
  device._collect_setups())` (the HEAD measurement point included the batch); `# @include _shared/heap_probe.py`
  (probe constants and their three tags live there once); `_WORST_CASE_ALLOCATION` → `BENCH["worst_case_allocation"]`
  (its tag withdrawn here: `heap_bounds.py` holds it); `_MIN_LARGEST_BLOCK = 2 * worst` with
  `l3.heap_headroom_after_full_system_build_worst_case_factor = 2` (A.U8C2.30's row, basis "a requirement"); `_MAX_USED
  = 100_000` tagged; the `:34` sentence gains "(agent, 2026-09-19)"; `gc.threshold(32768)` at `:117` gets
  `# @tunable` mirror tag `build.gc_threshold`; facts `gc_threshold` (both stages), `heap` per label (free, alloc,
  largest_block, retained), `used`, `max_used`, `largest_block`, `min_largest_block`; the `mem_info(1)` maps printed as
  labelled raw blocks (the host parser's input); `done()`.
- **Resolved**: A.U26.10 and A.U20.06 both touch the build call; the scratch path and the setup batch both apply.
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004, .009; M.HW_BENCH.046.
- **Blast carried by**: A.U25.61 (1)'s L0 equality check reads `_shared/heap_probe.py` once → GAP-D10 (TSC); the
  `typecheck.sh` comment → A.U27.09 (TOOL); host → M.HW_DEV.115.
- **Kind**: test, hardware (Round: R1 [H44])

## tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py

### M.HW_DEV.117 Heap layout over the generated boot order, without entering the supervisor
- **From**: A.U20.06 (blast: `start_and_check_tasks()` → `start_tasks()`, never the supervisor), A.U10.12 (`start_timers()`
  two-list form), A.U11.10 (`run_setups()`; the `_ProbeGc` rebinding wraps `system_service.gc`, labelled by method),
  A.U32.06 (`task_names`, GAP-G5), A.S0930.13 (blast: holds), A.U20.02, A.U26.10 (`:145` scratch), A.U26.44 (`:10`),
  A.U25.61 (2) (device module from the harness), A.U26.78/A.U30.16 (probe and map into the include; the `_ProbeGc`
  boot-mirror row stays here), A.U36.544 (`:199` "measure B" → "The boot placement reset (SPECIFICATION.md I.4(f.1))";
  the "(MEASUREMENTS M3.9)" citation → the archive section with commit, or dropped), A.U8.14 (`:213` mirror tag),
  A.U8C.01/A.U8C.72, A.U26.68.
- **Site**: `tests_hardware/device_scripts/heap_layout_after_full_boot_sequence.py:1-225`.
- **Change**: order: `build_system(watchdog=arm(), cfg_path=_SCRATCH_CFG_PATH, …)` → report → `run_setups(
  _collect_setups())` under the batch `_ProbeGc` label → report/map → `start_tasks(_collect_task_starters(),
  _collect_task_names())` awaited under `asyncio.wait_for(…, _STARTER_LOOP_TIMEOUT_MS / 1000)` (it returns once every
  starter ran; the `_counting_start_task` rebinding, the 20 ms poll and its `_STARTER_POLL_MS` row go, and the grace
  sleep stays only for the trailing collect) → report/map → `start_timers(triggers, timers)` (the two lists) → report
  → settle → reports; the supervisor never starts, so nothing to cancel; the boot-phase mark cleared at the end
  (M.HW_DEV.009 (4)). Every `RESULT:`/`HEAP`/`COUNTS`/`BOOT` line → facts; "Report only, no floors" stays (the wrapper
  asserts the twin's bound, M.HW_DEV.118). The comment `:146-148` explaining the seam goes.
- **Resolved**: A.U20.06 reorders the lists (setups, tasks, then timers) — the script follows the generated order, so
  HEAD's timers-before-tasks reading is not reproduced; the `starter_poll_ms` row (A.U8C.01/.72) is withdrawn with its
  loop.
- **Unit**: U26 (after U20/U11/U10).
- **Depends**: M.SRC_CORE (`start_tasks`, `run_setups`), M.GEN (`_collect_setups`, `_collect_task_names`),
  M.HW_DEV.001-.004, .009.
- **Blast carried by**: `tests_scripts/test_digital_twin_boot_contiguity.py` mirrored bounds → A.U11.10/A.U25.61 (TSC);
  `test_gc_collect_sites` boot-mirror row → A.U30.16 (TSC); host wrapper → M.HW_DEV.118.
- **Kind**: test, hardware (Round: R1 [H44])

## tests_hardware/flash/test_heap_layout.py (new)

### M.HW_DEV.118 The flash wrapper asserts the twin's high-band bound on both arms
- **From**: A.U25.61 (3), A.U26.68, A.U7.24 (`COVERS_TWIN_SCENARIOS`: `boot_contiguity`).
- **Site**: new `tests_hardware/flash/test_heap_layout.py`.
- **Change**: one test per arm (`ARM` render extra): parses the per-arm maps with `heap_map.parse_labelled()` and
  asserts the twin's `_HIGH_BAND_BLOCKS_MAX` (read from `tests_scripts/test_digital_twin_boot_contiguity.py` by `ast`)
  holds on the live arm and is violated on the suppressed arm; every quoted figure names its image (`result_note`).
  Header ≤ 3 lines; no marker.
- **Resolved**: A.U25.61 writes the wrapper in U25 "because the register gives the clause to U25"; written in U26's
  fact form (U25 < U26: the wrapper lands with the script's conversion).
- **Unit**: U26.
- **Depends**: M.HW_DEV.117.
- **Blast carried by**: twin record → M.HW_DEV.010; level containment → A.U7.24 (TSC).
- **Kind**: test, hardware (Round: R1 [H44])

## tests_hardware/device_scripts/allocation_need_per_source.py

### M.HW_DEV.119 Allocation need per source: rendered device, scratch config, routes from `ROUTES`, no `Any`
- **From**: A.U26.10 (`:112` scratch), A.U20.02 (`watchdog=`; `sensortask_dev.watchdog` global gone — the script feeds its
  own `arm()`), A.U26.44 (`:10`), A.U19.20 (blast: `:85` reads `ROUTES` by name — derived from the one table), A.U26.76
  (`:19, 46, 47, 68-69, 97`: `holes`/`keepers` typed `bytearray | None`, the probe list `list[tuple[str, Callable[[],
  Awaitable[object]]]]`, `_NO_REQUEST: object`), A.U30.16 (`_build_sieve`, `_release_sieve`, `_run` baseline rows),
  A.U26.68.
- **Site**: `tests_hardware/device_scripts/allocation_need_per_source.py:1-153`.
- **Change**: device from `BENCH`; `build_system(watchdog=wdt, cfg_path=_SCRATCH_CFG_PATH, …)` plus `run_setups(…)`;
  `_feed()` feeds `wdt`; route probes from the webserver module's `ROUTES`; the `CHURN`/rung lines become facts
  (`churn` per label, `block`, `probes`, `rungs`), `done()`; the comment `:30` keeps its fact about `feed()` allocating
  nothing.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.SRC_NET (A.U19.20 `ROUTES`), M.HW_DEV.001-.004, .009.
- **Blast carried by**: runner (bench memory tests) → HW_BENCH; host check `disallow_any_explicit` clean → A.U26.76 (TOOL).
- **Kind**: test, hardware (Round: R1 bench [H44])

## tests_hardware/device_scripts/serving_at_default_gc.py

### M.HW_DEV.120 Serving at the default GC stage: rendered device, `main(watchdog=…)`, shared dump
- **From**: A.U26.10 (`:93` keeps `cfg_path=""`, with the one-line comment), A.U20.02 (`main(watchdog=…)`), A.U26.44,
  A.U26.78 (`_dump` → `_shared/map_dump.py`), A.U30.16 (`_observe` row), A.U26.87 (blast: pattern reused by the echo
  script), A.U8C.86 (constants; `boot_wait_s` shared ID), A.U26.68.
- **Site**: `tests_hardware/device_scripts/serving_at_default_gc.py:1-140`.
- **Change**: `device = __import__(BENCH["device_module"])`; `asyncio.create_task(device.main(watchdog=arm()))`
  with the comment "production config path: the only write it can cause is the repair a production boot of a malformed
  file makes anyway"; boot wait polled on the webserver instead of a fixed `sleep(20)` where the module exposes
  readiness, else `_BOOT_WAIT_S` kept (AD-1); constants per A.U8C.86; the `HEAP`/state lines → facts (bounded per
  sample count), `done()` at the window end.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004, .009.
- **Blast carried by**: `_PREREQUISITE_DEVICE_SCRIPTS` (serving boot) → A.U26.10/A.U26.06 (TSC); bench
  `test_serving_heap_at_default_gc.py` reads the facts → HW_BENCH.
- **Kind**: test, hardware (Round: R1 bench [H44])

## tests_hardware/device_scripts/heap_under_connection_ceiling.py

### M.HW_DEV.121 Heap under the connection ceiling: rendered device, `main(watchdog=…)`, facts
- **From**: A.U26.10 (`:40` comment), A.U20.02, A.U26.44, A.U26.78 (`_dump` shared), A.U8.14 (`:15` mirror tag),
  A.U8C.73 (`sample_interval_ms`, `window_s`, `boot_wait_s`), A.U26.68 (HW_BENCH blast: its `FACT` lines).
- **Site**: `tests_hardware/device_scripts/heap_under_connection_ceiling.py:1-60`.
- **Change**: as M.HW_DEV.120 (device, `main(watchdog=arm())`, the comment on the production path, the shared dump);
  samples become one fact per sample (`heap` with t, free, largest), `done()` after the window; `RESULT PASS` goes.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.120.
- **Blast carried by**: `bench/test_heap_under_connection_ceiling.py` → HW_BENCH (M.HW_BENCH's change quoting its facts).
- **Kind**: test, hardware (Round: R1 bench [H44])

## tests_hardware/device_scripts/loop_stretch_timing.py (new)

### M.HW_DEV.122 The routine no-yield stretches timed on the chip
- **From**: A.U31.05, A.U31.01 (F.3 rows it measures), A.U26.44 (OR78.a: not "import frozen `sensortask_dev`"), A.U26.10,
  A.U26.68.
- **Site**: new `tests_hardware/device_scripts/loop_stretch_timing.py`.
- **Change**: as A.U31.05: builds the graph (device from `BENCH`, scratch path, `watchdog=arm()`), `gc.threshold(-1)`;
  times five `gc.collect()`, sixty `vocalgorithm_process()` steps (max over the last twenty), `CRC32().check_from()` over
  256 B (total and the largest gap between its yields via a `sleep_ms(0)` probe task); `_ROUTINE_STALL_US = 21_000`
  (derived, trailing comment naming F.3's `con.routine_stall`); facts `gc_max_us`, `voc_max_us`, `crc_total_us`,
  `crc_gap_max_us`, `routine_stall_us`; `done()`.
- **Resolved**: —
- **Unit**: U31 (written in U26's form).
- **Depends**: M.HW_DEV.001-.004, .009.
- **Blast carried by**: host → M.HW_DEV.115; F.3 measured cells → A.U31.01 (SPEC).
- **Kind**: test, hardware (Round: R1 [H20, H21])

## tests_hardware/device_scripts/flash_write_loop_gap.py (new)

### M.HW_DEV.123 One scratch flash write's synchronous span, measured
- **From**: A.U31.05, A.U26.18 (scratch removed on every path), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/flash_write_loop_gap.py`.
- **Change**: times each call of one `open()`/`write()`/`close()` of a 1 KiB `/_stretch.bin` and its `os.remove()`
  (`ticks_us()`, which counts with interrupts off); a leftover is removed first; facts `flash_call_max_us`,
  `flash_total_us`; never fails on the figure; no file left behind; `done()`.
- **Resolved**: —
- **Unit**: U31.
- **Depends**: M.HW_DEV.002.
- **Blast carried by**: the write is owned by its marked test → A.U26.06 (TSC: a raw `open(...,"w")` is persisting, GAP-D8).
- **Kind**: test, hardware (Round: R3 [H21])

## tests_hardware/device_scripts/loop_lag_under_combined_load.py (new)

### M.HW_DEV.124 Loop lag of the shipped `main()` under in-process load, in its own FRAM region
- **From**: A.U31.06 (3), A.U26.24 (scratch regions disjoint), A.U26.44, A.U26.22 (production chunks written: runs after
  the evidence save), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/loop_lag_under_combined_load.py`.
- **Change**: runs `device.main(watchdog=arm())` in a task beside a lag probe; adds an allocation-churn task and FRAM
  block writes through the FRAM driver at `_SCRATCH_REGIONS = ((0x3FE00, 0x100),)` (above every chunk, disjoint from the
  hold-timing script's `0x3FF00`); reports `lag_max_us`, `lag_p99_us`, `samples`, `bound_us` (the device's smallest hard
  consumer from F.3, rendered); `done()`.
- **Resolved**: A.U31.06 writes "at the scratch address the FRAM hold script uses (`0x3FF00`)"; A.U26.24's check allows a
  shared region only between phases of one host test, and these are two tests: this script takes its own region
  (agent decision AD-8).
- **Unit**: U31 (U26 form).
- **Depends**: M.HW_DEV.004/.007/.009.
- **Blast carried by**: region check → A.U26.24 (TSC); host → M.HW_DEV.115; BACKLOG owed row → A.U31.06 (DOCS).
- **Kind**: test, hardware (Round: R1 bench [H20])

## tests_hardware/device_scripts/c_stack_budget.py (new)

### M.HW_DEV.125 The deepest await chain's C-stack peak on silicon
- **From**: A.U30.18 (3), A.U26.44 (OR78.a: the device module from `BENCH`), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/c_stack_budget.py`.
- **Change**: builds the bench system (scratch path, `watchdog=arm()`), wraps the leaf of the deepest chain the analysis
  names from outside to record `micropython.stack_use()`, drives that path through the real product call, fed ≤ 2 s;
  facts `c_stack_peak`, `c_stack_limit` (7,936), `chain`; the half-limit verdict host-side; `done()`.
- **Resolved**: A.U30.18 routes the build "through U26's `run_device_script.py`"; on silicon that is the rendered
  device module (the twin uses the runner).
- **Unit**: U30 (U26 form).
- **Depends**: M.HW_DEV.001-.004, .009.
- **Blast carried by**: SPEC F.1 C-stack paragraph → A.U30.18 (SPEC); host → M.HW_DEV.115; the 2× margin on the OR2.c
  list → A.U30.18.
- **Kind**: test, hardware (Round: R1 [H23])

## tests_hardware/flash/test_sensor_accuracy.py

### M.HW_DEV.130 Plausibility from the shared bounds; envelope gated as a write; conformance moves out
- **From**: A.U26.68, A.U26.49 (bounds from `plausibility_bounds.py`), A.U26.07 (the SCD30 plausibility test takes
  `scd30_measuring`), A.U26.11 (1) (the envelope gains `persistence_write` beside `neopixel_sweep`, comment names the
  spend), A.U26.66 (3) (`:80-89` moves to `flash/test_chip_conformance.py`), A.U15.20 (new `test_sgp40_sample_cadence`),
  A.U26.35/A.U26.74 (`long_soak` → `soak_duration`, short duration), A.U26.51 (`scd30`, `sgp40`, `bmp3xx`, `isl29125`,
  `isl29125_autorange`), A.U20.33 (B2), A.U8C.107.
- **Site**: `tests_hardware/flash/test_sensor_accuracy.py:1-89`.
- **Change**: (1) `RESULT_RE` and the four inline matchers go; each test asserts its script's facts against
  `plausibility_bounds.BOUNDS[...]` (the bound and its source in the message); `isl29125_conformance` import goes.
  (2) `test_scd30_real_reading_is_within_datasheet_plausible_bounds(board, scd30_measuring)`. (3) The envelope test:
  `@pytest.mark.neopixel_sweep @pytest.mark.persistence_write`, comment "seven flash writes to a scratch config file (the
  range/resolution pushes)"; the in-test skip keeps `--allow-neopixel-sweep`. (4) `test_isl29125_register_probe_…`
  (`:80-89`) deleted here (moved, M.HW_DEV.131). (5) `@pytest.mark.soak_duration def test_sgp40_sample_cadence(board,
  request)`: runs `sgp40_sample_cadence.py` with `timeout_s=_CADENCE_TIMEOUT_S = 660.0`, asserts `cycles > 0` and
  records `cycles`, `elapsed_ms`, `lost`, `max_gap_ms`, `gaps_over_1500` (no pass threshold, owner). (6) Timeouts per
  A.U8C.107 (the conformance row moves with its test).
- **Resolved**: A.U15.20 marks the cadence test `long_soak` (short tier); A.U26.35 renames the marker — written once as
  `soak_duration`.
- **Unit**: U26 (A.U15.20's test lands in U15 on the HEAD helper form and is converted here).
- **Depends**: M.HW_BENCH.002/.043, M.HW_DEV.020, .136-.144.
- **Blast carried by**: `_KNOWN_PERSISTING_HELPERS`/marker guard → A.U26.06/A.U26.11 (TSC); flush-test exemption reason
  → A.U26.11 (3) (TSC); README device-script table row → A.U15.20 (HW_BENCH).
- **Kind**: test, hardware (Round: R1 [H25, H29]; envelope R3 [H28]; cadence R5 [H35])

## tests_hardware/flash/test_chip_conformance.py (new)

### M.HW_DEV.131 One conformance gate per bus chip, real vs twin
- **From**: A.U26.66 (3), A.C.15 (1) (the SCD30 argument-reaction test), A.C.16 (1) (BMP3xx probe keys C01/C02), A.C.19 (2)
  (the ISL29125 probe runs here in R1), A.U36.543 (blast: Part K names this file), A.U7.24.
- **Site**: new `tests_hardware/flash/test_chip_conformance.py`.
- **Change**: one test per probe (`isl29125_mock_conformance_probe.py`, `scd30_conformance_probe.py`,
  `sgp40_conformance_probe.py`, `bmp3xx_conformance_probe.py`, `fram_conformance_probe.py`): `real =
  conformance.parse(board.run_isolated(probe))`, `DONE` present, `twin = conformance.run_probe_on_twin(probe,
  gc_threshold)` at −1 and 32768, `compare(real, twin, PHYSICAL_KEYS, independent_checks)` → no divergences (each listed);
  the ISL29125 conversion-cycle figure recorded. `@pytest.mark.persistence_write @pytest.mark.scd30_extra_write
  test_scd30_argument_reaction_is_recorded(board, scd30_measuring)`: runs `scd30_argument_reaction.py`, asserts
  `restored == "ok"` and the interval equals the `standard_state` snapshot, records the facts. `COVERS_TWIN_SCENARIOS`
  names the chip-model scenarios.
- **Resolved**: the conformance comparison keeps its `KEY=VALUE` protocol (the probe output is the comparison's input on
  both sides, a documented exception to the `FACT` form: `conformance.parse` reads both).
- **Unit**: U26 (the A.C.15 test is phase-C instrumentation in U26 form).
- **Depends**: M.HW_BENCH.038 (`conformance.py`), M.HW_DEV.132-.135, .137, .145.
- **Blast carried by**: SPEC Part K paragraph → A.U36.543 (SPEC); budget row "at most 3 SCD30 NVM writes" → A.C.15
  (HW_BENCH); fidelity table rows → A.U25.01 (TWIN).
- **Kind**: test, hardware (Round: R1 [H25]; argument reaction R3 [H30])

## tests_hardware/device_scripts/scd30_conformance_probe.py, sgp40_conformance_probe.py, bmp3xx_conformance_probe.py, fram_conformance_probe.py (new)

### M.HW_DEV.132 Four raw-bus conformance probes
- **From**: A.U26.66 (2), A.C.16 (1) (BMP3xx `C01_osr_config_written`, `C02_osr_config_after_softreset`), A.U26.24 (the FRAM
  probe's round trip inside a declared scratch region), A.U26.44.
- **Site**: four new device scripts.
- **Change**: raw `machine.I2C`/`SPI` only, addresses and pins from `BENCH`; each prints its `KEY=VALUE` lines and
  `DONE=1` and declares `PHYSICAL_KEYS` with the independent check per key (a range, a CRC validity, a monotonic
  relation): SCD30 — firmware-version word and CRC, interval read and CRC, data-ready word, an 18-byte measurement's six
  CRCs, the NACK of a read before a command, the soft-reset recovery bound; SGP40 — serial words and CRCs, self-test word
  (0xD400 on a good part), a compensated raw read's CRC, heater-off acknowledgement; BMP3xx — chip ID, the 21-byte
  calibration block (raw), status and power-mode behaviour, plus C01/C02 (OSR 0x1C and CONFIG 0x1F written, then after
  soft reset 0xB6 → CMD 0x7E and the datasheet start-up time, back to defaults); FRAM — RDID (MB85RS2MTA p.10), WEL
  set/clear, a write/read round trip in `_SCRATCH_REGIONS = ((0x3FD00, 0x100),)`. Every wait fed; volatile registers
  only (no NVM).
- **Resolved**: the FRAM probe's region is chosen disjoint from M.HW_DEV.124 and the hold script (AD-8's rule).
- **Unit**: U26 (BMP3xx keys added in phase-C prep, A.C.16).
- **Depends**: M.HW_DEV.001/.004/.007.
- **Blast carried by**: chip fakes answering the probes → A.U26.66/A.U25 (TWIN); M.HW_DEV.131.
- **Kind**: test, hardware (Round: R1 [H25, H26])

## tests_hardware/device_scripts/sgp40_sample_cadence.py (new)

### M.HW_DEV.136 SGP40 cycles counted over ten minutes of the real task graph
- **From**: A.U15.20, A.U26.44 (device module), A.U26.10 (cfg path), A.U20.02, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/sgp40_sample_cadence.py`.
- **Change**: boots the generated bench system the way M.HW_DEV.117 does (scratch path, `watchdog=arm()`, setups, tasks,
  timers), wraps `sgp40._read_sgp` from outside to record `ticks_ms()` per cycle into a preallocated `array("I", …)` of
  1,200 slots, runs 600 s with the device's own tasks, feeding; facts `cycles`, `elapsed_ms`, `lost`, `max_gap_ms`,
  `gaps_over_1500`; boot-phase mark cleared; `done()`.
- **Resolved**: A.U15.20 lets the run use "FRAM backup at `BackupPeriod` 1" — on a scratch config path the backup period
  is the schema default; the script sets it on the reader in RAM (no config write), so the claim holds without a
  persisting write (agent decision AD-9).
- **Unit**: U15 (U26 form).
- **Depends**: M.HW_DEV.009, .117.
- **Blast carried by**: host → M.HW_DEV.130; L1 structural pin → A.U15.20 (TEST_UNIT).
- **Kind**: test, hardware (Round: R5 short [H35])

## tests_hardware/device_scripts/scd30_plausibility_read.py

### M.HW_DEV.137 SCD30 plausibility read: values out, bounds host-side
- **From**: A.U26.49 (bounds moved to `plausibility_bounds.py`; the script reports values), A.U26.07 (runs under
  `scd30_measuring`), A.U5.02 (reader constructor tail), A.U10.43 (`trigger_s`), A.U26.44, A.U8C.82, A.U8C2.36, A.U26.68.
- **Site**: `tests_hardware/device_scripts/scd30_plausibility_read.py:1-60`.
- **Change**: bus and pins from `BENCH`; reader constructed in the end-state shape; `_SETTLE_S = 45.0`, `_STEP_S = 0.5`,
  `_POLL_TRIES = 30` tagged; settle and poll waits through `fed_sleep_ms`; facts `co2`, `humidity`, `temperature`,
  `polls`; the in-script bound checks go; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004.
- **Blast carried by**: host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R1 [H31])

## tests_hardware/device_scripts/bmp3xx_plausibility_read.py

### M.HW_DEV.138 BMP3xx plausibility read: values out, comment names the divider
- **From**: A.U26.49, A.U15.40 (`:24` comment → `_divide_trigger()`), A.U15.25 (blast: unchanged), A.U1.06 (blast),
  A.U5.02, A.U26.44, A.U8C.58, A.U8C2.26, A.U26.68.
- **Site**: `tests_hardware/device_scripts/bmp3xx_plausibility_read.py:1-45`.
- **Change**: i2c0 and the address from `BENCH`; `:24` comment names `_divide_trigger()`; `_POLL_S = 0.5`, `_POLL_TRIES =
  30`; facts `pressure`, `temperature`, `polls`; bound checks host-side; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004.
- **Blast carried by**: host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R1 [H29])

## tests_hardware/device_scripts/isl29125_plausibility_read.py

### M.HW_DEV.139 ISL29125 plausibility read: rig parked, lux out, priming kept read-only
- **From**: A.U26.16 (NeoPixel parked in `finally`), A.U26.49 (lux bound FN8424 p.1 host-side; the room-light floor stays
  a tagged script fact), A.U26.34 (blast: its RAM-priming pattern `:32-37` is reused), A.U5.02, A.U26.44, A.U8C.78,
  A.U8C2.34, AD-1 (`:29`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_plausibility_read.py:1-60`.
- **Change**: NeoPixel constructed as the first statement in the `try` whose `finally` sets it dark; bus, pins and mode
  from `BENCH`; `_ROOM_LIGHT_MIN_LUX = 5.0`, `_POLL_S`, `_POLL_TRIES` tagged; the `:29` wait kept as
  `_FIRST_SAMPLE_MS = 300` (`l3.isl29125_plausibility_read_first_sample_ms`, AD-1); facts `lux`, `rgb`, `room_light_min`;
  `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004, .008.
- **Blast carried by**: host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py

### M.HW_DEV.140 VOC algorithm quality on the TOML's bus with its timeout; shared fixed source
- **From**: A.U14.04/A.U26.44 (`:46` i2c1 built with the TOML's `timeout`), A.U5.11 (`:47-56` constructor: value
  references and one backup group), A.U26.78 (`_FixedSource` → `_shared/fixed_source.py`), A.U28.28 (`:91` `B905`
  noqa), A.U26.49 (VOC index bound 0..500 host-side, M.HW_BENCH.043's D4), A.U8C.89 (the feed-interval ID shared with
  the backup script → the shared feed step), A.U26.68.
- **Site**: `tests_hardware/device_scripts/sgp40_voc_algorithm_quality.py:1-110`.
- **Change**: bus from `BENCH` (timeout passed); reader constructed in A.U5.11's shape; the fixed source included;
  `_BLACKOUT_WAIT_S`, `_SAMPLE_INTERVAL_S`, `_MAX_SINGLE_STEP_JUMP` tagged; the `_WDT_FEED_INTERVAL_S` row withdrawn
  into `_shared/watchdog.py`'s step; facts `samples` (bounded list), `max_step_jump`, `blackout_s`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.SRC_SENS (A.U5.11), M.HW_DEV.001-.004.
- **Blast carried by**: host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R1 [H35])

## tests_hardware/device_scripts/sgp40_fram_backup_restore.py

### M.HW_DEV.141 SGP40 FRAM backup/restore with the TOML's bus timeout and a cleared chunk
- **From**: A.U14.04/A.U26.44 (`:54` timeout), A.U5.11, A.U5.02, A.U26.78 (`_FixedSource`), A.U26.22 (5) (chunk cleared
  after), A.U15.17/A.U15.18 (blasts: defaults and the `restored_from is None` check hold), A.U8C.87, AD-1 (`:15`, `:16`
  kept), A.U26.68.
- **Site**: `tests_hardware/device_scripts/sgp40_fram_backup_restore.py:1-125`.
- **Change**: bus from `BENCH`; reader in A.U5.11's shape; fixed source included; `_BACKUP_WAIT_S = 75.0`
  (`l3.sgp40_fram_backup_restore_backup_wait_s`) and `_RESTORE_WAIT_S = 10.0` (`…_restore_wait_s`) tagged (AD-1), waited
  through `fed_sleep_ms`; facts `backup_written`, `restored_from`, `restored_state_matches`; the backup chunk cleared in
  `finally`; `done()`.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.SRC_SENS (A.U5.11), M.HW_DEV.001-.004, .006.
- **Blast carried by**: host → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/device_scripts/isl29125_mechanism_envelope.py

### M.HW_DEV.142 The envelope: scratch config flushed and removed, rig parked, private names, catalog codes
- **From**: A.U26.11 (2) (leftover `config_HWTEST_ISL29125.cfg` removed first; `finally` flushes then removes it; setup
  `:205-213` moves inside the `try`), A.U26.16 (rig parking), A.U10.35 + M_SRC_SENS GAP-5 (`:74-77` `pixel.led_overl_bri`/
  `led_overl_on` → the `_overlay_*` names), A.U10.39/A.U24.61 (`:109` `reader.cfg_schema` → `reader.get_cfg_schema()`),
  A.U10.44 (`:205-206` starters by end-state names), A.U11.24 (its `write_config(…, schema)` loses the schema), A.U17.27
  (blast: `:74` writes the attribute; holds), A.U9.07 (blast: superseded by A.U17.27 — no `neopixel_freq` refusal),
  A.U2.12/A.U2.03 (`:217, :221` `W13` → the catalog binding `W_ISL_PERIODIC_ONLY = 32`), A.U5.02, A.U26.44, A.U8C.76,
  A.U8C2.32, A.U1.06 (blast), A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_mechanism_envelope.py:1-240`.
- **Change**: start: `os.remove("config_HWTEST_ISL29125.cfg")` with ENOENT passing and any other errno a fact; NeoPixel
  and reader construction as the first statements of the `try`; `finally`: `pixel.off()` first, then `await
  reader.cfgmgr.flush_pending()`, then the scratch file removed; attributes through their end-state names and
  `get_cfg_schema()`; codes from the catalog bindings; constants per A.U8C.76/A.U8C2.32; facts per check (steps, ratios,
  bit-depth margins, `warnings` with codes), `done()`; verdicts host-side.
- **Resolved**: A.U9.07 is superseded by A.U17.27 (A.U17.27's Depends says so; the later unit's constant governs).
- **Unit**: U26.
- **Depends**: M.SRC_SENS (GAP-5 names, `get_cfg_schema()`), M.HW_DEV.001-.004, .008, .012.
- **Blast carried by**: flush-test exemption reason → A.U26.11 (3) (TSC); the `config_HWTEST_*` removal check → A.U26.18
  (TSC); host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R3 [H28])

## tests_hardware/device_scripts/isl29125_lighting_scenarios.py

### M.HW_DEV.143 Lighting scenarios: dead constant gone, private pixel, catalog codes, rig parked
- **From**: A.U26.83 (`:33` `_STEP_MS` removed), A.U10.35 (`:82` `self.pixel` → `_pixel`), A.U2.12/A.U2.03 (`:204, :336`
  `W13` → `W_ISL_PERIODIC_ONLY = 32`), A.U15.32 (blast: unchanged), A.U26.16, A.U5.02, A.U26.44, A.U8C.75 (its
  `step_ms` row withdrawn with `:33`), A.U8C2.31 (`isl29125.periodic_only_warn_at` mirror at `:335`), A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_lighting_scenarios.py:1-340`.
- **Change**: `_STEP_MS` deleted; the rig class reads `_pixel`; codes from the bindings; NeoPixel parked in `finally`;
  constants per A.U8C.75/A.U8C2.31 (minus `step_ms`); facts per scenario, `done()`.
- **Resolved**: A.U8C.75 tags `:33` (100), which A.U26.83 deletes as dead: the row is withdrawn (B4).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004, .008, .012.
- **Blast carried by**: host → M.HW_DEV.130.
- **Kind**: test, hardware (Round: R3 [H28])

## tests_hardware/device_scripts/isl29125_mock_conformance_probe.py

### M.HW_DEV.144 The ISL29125 probe: constants from `BENCH`, settles named, run from the conformance gate
- **From**: A.U26.66 (3) (its test moves to `flash/test_chip_conformance.py`), A.U26.44 (`:20` `_MODE_RGB` copy), A.C.16
  (blast: already reads the configuration before/after reset, keys A03-A05), A.C.19 (2) (runs in R1), A.U8C.77 (`:12`
  wdt → `arm()`), A.U8C2.33 (deferred settles `:87`, `:104, :134, …` kept as named constants, AD-1).
- **Site**: `tests_hardware/device_scripts/isl29125_mock_conformance_probe.py:1-160`.
- **Change**: bus, address and `_MODE_RGB` from `BENCH`; `_WDT = arm()`; `_WRITE_SETTLE_MS = 50`
  (`l3.isl29125_mock_conformance_probe_write_settle_ms`) and `_CONVERSION_SETTLE_MS`
  (`l3.isl29125_mock_conformance_probe_conversion_settle_ms`) named; output stays `KEY=VALUE` plus `DONE=1` (the
  comparison protocol, M.HW_DEV.131); the conversion-cycle series added as keys.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_BENCH.038.
- **Blast carried by**: M.HW_DEV.131.
- **Kind**: test, hardware (Round: R1 [H25])

## tests_hardware/device_scripts/isl29125_real_irq_edge.py

### M.HW_DEV.145 ISL29125 INT edge: PRST verdict kept, rig parked, unit suffixes
- **From**: A.C.19 (1) (DONE-AT-HEAD: fails unless PRST counts whole RGB cycles), A.U15.30 (blast: header held), A.U15.32/
  A.U15.R05 (blasts: unchanged), A.U10.43 (unit suffixes), A.U26.16, A.U5.02, A.U26.44, A.U8C.79, A.U8C2.35, A.U26.68.
- **Site**: `tests_hardware/device_scripts/isl29125_real_irq_edge.py:1-125`.
- **Change**: pins (INT) and bus from `BENCH`; NeoPixel parked in `finally`; identifiers with the end-state unit suffixes;
  constants per A.U8C.79/A.U8C2.35 (the deferred `first_conversion_cycles` kept, AD-1); facts `fast_path_ms`,
  `persist_unit`, `config1_restart` (reported only), `done()`; the PRST verdict host-side.
- **Resolved**: —
- **Unit**: U26.
- **Depends**: M.HW_DEV.001-.004, .008.
- **Blast carried by**: host → M.HW_DEV.080; SPEC M.1.2 rows → A.C.19 (SPEC).
- **Kind**: test, hardware (Round: R1 [H25, H27])

## tests_hardware/device_scripts/fram_raw_dump.py (new)

### M.HW_DEV.150 Read-only raw FRAM dump, the evidence primitive's board half
- **From**: A.U26.22 (3), A.U26.79 (the write-protect state for the standard-state check, AD-5), A.S0930.28 (2)(7) (the
  post-erase and post-reset dumps), A.U26.43/A.S0930.39 (no-torn-chunk reads), A.U26.44 (`dump_size` extra).
- **Site**: new `tests_hardware/device_scripts/fram_raw_dump.py`.
- **Change**: reads FRAM bytes `[0, BENCH["dump_size"])` through the driver's raw `get_values()` in 256 B pieces (no
  `get_chunk()`, no write), printing hex lines (the raw block the host saves verbatim); then the status register
  (WPEN/BP bits) and RDID as facts `status_register`, `write_protected`, `rdid`; feeds the watchdog every piece; `done()`.
- **Resolved**: AD-5 (the read-only WP read lives here, not in the chunk-writing round-trip script).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.002/.004.
- **Blast carried by**: `harness.save_fram_raw()` → M.HW_BENCH.012; `standard_state` reads `write_protected` from this
  dump → GAP-D6 (HW_BENCH); L0 "no `set_values`/`get_chunk`/`write` call" → A.U26.22 (TSC).
- **Kind**: test, hardware (Round: every round's start [H02])

## tests_hardware/device_scripts/fram_command_hold_timing.py (new)

### M.HW_DEV.151 The FRAM command and block holds against the UART poll floor
- **From**: A.U16.07, A.U33.07 (the owed-run text names it), A.U31.01 (`hold.fram_block` row cited by name), A.U26.24
  (`_SCRATCH_REGIONS = ((0x3FF00, 0x100),)`), A.U26.44 (pins from `BENCH`, not `SPI(0, 2, 3, 4)`/CS 5), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/fram_command_hold_timing.py`.
- **Change**: BACKLOG A6's body, header as A.U16.07 writes it (≤ 3 lines); `_UART_FLOOR_US = 80 * 10 * 1_000_000 // 115_200`
  (derived, no tag); `_BLOCK_HOLD_BUDGET_US` with its trailing comment citing F.3's `hold.fram_block` row; writes only
  inside its declared region; facts `write_us`, `read_us`, `hold_us`, `uart_floor_us`, `block_hold_budget_us`;
  verdicts host-side; `done()`.
- **Resolved**: A.U16.07 keeps the literal SPI pins "(their derivation from the TOML is U26's)" — U26's form applies.
- **Unit**: U16 (U26 form).
- **Depends**: M.HW_DEV.001/.002/.007.
- **Blast carried by**: BACKLOG `:389-449` script block deleted → A.U16.07 (DOCS); README FRAM bullet → A.U16.07
  (HW_BENCH); host → M.HW_DEV.060.
- **Kind**: test, hardware (Round: R1 [H22])

## tests_hardware/flash/test_config_float_round_trip.py (new)

### M.HW_DEV.152 The config float round trip on the board's single-precision floats
- **From**: A.U11.21 (L3), A.C.05 (R3 wear run), M_SRC_CORE GAP-G13 blast (the L3 pair is HW_DEV's).
- **Site**: new `tests_hardware/flash/test_config_float_round_trip.py`.
- **Change**: `@pytest.mark.persistence_write def test_config_floats_round_trip_unchanged(board)`: runs
  `config_float_round_trip.py`, asserts every probed value idempotent and the repeat PUT after the reload "Unchanged";
  header ≤ 3 lines; `COVERS_TWIN_SCENARIOS` names the config-manager twin scenario or its E.6.6 row.
- **Resolved**: —
- **Unit**: U11 (U26 form).
- **Depends**: M.HW_DEV.153.
- **Blast carried by**: marker guard → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R3 [H47])

## tests_hardware/device_scripts/config_float_round_trip.py (new)

### M.HW_DEV.153 Float idempotence and a reload through a scratch manager
- **From**: A.U11.21, A.U26.18 (scratch removed on every path, leftover first), A.U26.44/A.U26.49 (the float fields' ranges
  rendered from the `_VAL_*` tuples instead of embedded), A.U26.68.
- **Site**: new `tests_hardware/device_scripts/config_float_round_trip.py`.
- **Change**: for each float field's min/max and 200 evenly spaced values (ranges from `BENCH["float_fields"]`), checks
  idempotence of the stored form; writes one value through a `config_HWTEST_FLOAT.cfg` manager, rebuilds the manager
  from the file, a repeat write answers "Unchanged"; the scratch file removed first and in `finally`; facts
  `non_idempotent` (bounded), `repeat_validity`; `done()`.
- **Resolved**: A.U11.21 embeds the values "(device scripts cannot read host files)"; the rendering (A.U26.44) delivers
  them from the source tuples, which is the G1/R41 form (agent decision AD-10).
- **Unit**: U11 (U26 form).
- **Depends**: M.SRC_CORE (`_stored_float`), M.HW_DEV.001/.002.
- **Blast carried by**: `config_HWTEST_*` removal check → A.U26.18 (TSC).
- **Kind**: test, hardware (Round: R3 [H47])

## tests_hardware/device_scripts/reset_code_invalid_record.py, reset_code_command_incomplete.py, reset_code_boot_phase_hang.py, reset_code_stack_exhausted.py (new)

### M.HW_DEV.154 Four scripts that end in an attributed reset
- **From**: A.C.12 (1)-(4), A.U11.06 (boot phases 1-5), A.U20.02 (`main(watchdog=…, cfg_path=<scratch>)`), A.U26.10, A.U26.44,
  A.U26.68.
- **Site**: four new device scripts.
- **Change**: (1) `reset_code_invalid_record.py`: writes a non-magic word into `mem_backup(0)[0]`, then `machine.reset()`.
  (2) `reset_code_command_incomplete.py`: builds the generated system over the scratch path, rebinds from outside the FRAM
  erase's per-unit write so unit 2 raises `OSError(EIO)`, calls `_system_cmd_callback("erasefram")`. (3)
  `reset_code_boot_phase_hang.py`: `PHASE` (1-5) extra; runs the generated `main(watchdog=arm(), cfg_path=_SCRATCH_CFG_PATH)`
  with one callee of that phase rebound to `time.sleep_ms(10000)` (no feed follows). (4) `reset_code_stack_exhausted.py`:
  builds the system, rebinds one supervised reader's read coroutine to recurse until the stack check raises, lets the
  supervisor escalate. Each prints a banner before the reset (AD-3); no flash write (FRAM only, scratch config).
- **Resolved**: —
- **Unit**: phase C (written before R1, U26 form).
- **Depends**: M.HW_DEV.009; M.SRC_CORE (A.U11.05-.07).
- **Blast carried by**: `bench/test_reset_reasons.py` four tests → A.C.12 (HW_BENCH); E.6 row → A.U26.28 (SPEC).
- **Kind**: test, hardware (Round: R1 bench [H12])

## tests_hardware/device_scripts/config_write_loop_scratch.py, config_scratch_readback.py (new)

### M.HW_DEV.155 Power cut during a scratch config write: the writer and the read-back
- **From**: A.C.17, A.U26.18, A.U26.68.
- **Site**: two new device scripts (run by the manual step in `manual/manual_persistence.py`, HW_BENCH).
- **Change**: the writer builds a `ConfigManager` over `config_HWTEST_POWERLOSS.cfg` (two-field schema), writes
  alternating values through `write_config()` + `flush_pending()`, printing `WROTE <n> <value>` after each (a banner
  the operator watches), at most 20 writes, fed; the read-back loads the file through `setup()`'s read path, reports
  `parsed`, `values`, `repaired`, then removes the file (the allowed scratch cleanup); `done()`.
- **Resolved**: —
- **Unit**: phase C (U26 form).
- **Depends**: M.HW_DEV.002/.004.
- **Blast carried by**: the manual step → A.C.17 (HW_BENCH); persistence guard (scratch writes owned by a manual,
  operator-confirmed step) → A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R2 [H49])

## tests_hardware/device_scripts/scd30_argument_reaction.py (new)

### M.HW_DEV.156 Record how the SCD30 treats a bad-CRC and a zero interval write
- **From**: A.C.15 (1), A.U26.44, A.U26.68.
- **Site**: new `tests_hardware/device_scripts/scd30_argument_reaction.py`.
- **Change**: raw `machine.I2C` at `BENCH`'s bus/address: reads the interval (0x4600); sends it with a wrong argument CRC,
  reads back, times two data-ready periods; sends 0 with a correct CRC, reads back, times again; restores the original
  interval in `finally` if either changed it; facts `wrong_crc_accepted`, `zero_interval_accepted`, `restored`, each read
  value; fed throughout; `done()`. At most 3 SCD30 NVM writes.
- **Resolved**: —
- **Unit**: phase C (U26 form).
- **Depends**: M.HW_DEV.001/.002/.004.
- **Blast carried by**: M.HW_DEV.131 test; `_PERSISTING_DEVICE_CALLS` needs a raw 0x4600 write detected → GAP-D8 (TSC).
- **Kind**: test, hardware (Round: R3 [H30])

## tests_hardware/device_scripts/scd30_measurement_interval_read.py, scd30_data_ready_wait.py, scd30_start_continuous_measurement.py (new)

### M.HW_DEV.157 The SCD30 prerequisite's three scripts
- **From**: A.U26.07 (1)-(3), A.U26.06 (the start script pinned in `_PREREQUISITE_DEVICE_SCRIPTS`), A.U26.44, A.U26.68.
- **Site**: three new device scripts.
- **Change**: (1) interval read: driver on `BENCH`'s SCD30 bus, `setup()` (soft reset, no NVM), fact `interval`; writes
  nothing. (2) data-ready wait: polls `read_measurement()`/`get_CO2()` every 1 s for `3 * interval + 2` s, fed ≤ 2 s,
  facts `measuring`, `co2` or `waited_s`; writes nothing. (3) start: reads `get_ambient_pressure()` and re-sends it once
  when it is 0 or within 700..1400 (Interface Description §1.4.1), else reports `invalid_readback` and sends nothing;
  header names the altitude side effect; facts `sent`, `ambient`. All three end with `done()`; failures are facts, never
  `RESULT:` lines.
- **Resolved**: A.U26.07 writes `INTERVAL=`, `MEASURING`, `SENT`, `RESULT: FAIL` lines; facts per M.HW_DEV.002 (the
  helper `ensure_scd30_measuring()` parses them, M.HW_BENCH.044).
- **Unit**: U26.
- **Depends**: M.HW_DEV.001/.002/.004.
- **Blast carried by**: `scd30_prerequisite.py` → M.HW_BENCH.044; L0 failure modes → A.U26.07 (TSC); prerequisite pin →
  A.U26.06 (TSC).
- **Kind**: test, hardware (Round: R1 [H31])
