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
  `persistence_write` where the fixture was its only write → M.HW_DEV.031 (`test_bus_concurrency.py`); the prerequisite
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

## tests_hardware/device_scripts/system_debug_level_raise_for_boot_log_check.py (deleted)

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
