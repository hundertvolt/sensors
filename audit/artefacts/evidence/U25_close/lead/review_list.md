# U25 close: decisions taken on the owner's behalf (draft review list)

One line per decision: what was decided (actor, date), its consequence, and how to reverse it. Sources: `S/u25/briefs/rulings.md`
(A-1..A-36), `S/u25/lead_rulings_v0.md` and `_v1.md`, plan section 0, the lanes' hand-backs, the lead's log from 2026-10-14. A-1..A-26
were set on 2026-10-13 and re-checked on 2026-10-14; everything else is (agent, 2026-10-14) unless it says otherwise. Lane D's
deviations follow its hand-back. Counts: 36 rulings, 10 lead rulings and process decisions, 19 lead decisions on the merged
trees, 84 lane decisions (MN 19, C 10, R 16, P 9, SH 13, G 9, E 3, D 5), 6 at the gate and the close; 155 lines.

## Rulings (plan section 5, `briefs/rulings.md`)

- A-1 U25 planned on U24's v0, re-located on `8e7dedc`; a missing API stops that item (agent, 2026-10-13; lead v0 accepted). Consequence: none stopped. Reverse: n/a (planning only).
- A-2 the cut MN, C, R, P / SH, G / lead / D (v1). Consequence: 7 lanes instead of 13, one API merge. Reverse: none needed; a later unit may cut finer.
- A-3 MN removes a twin pending-list entry only in the commit whose change makes its check pass (lead v1, a narrow reading of CHECKLIST 4). Consequence: `tests/test_digital_twin_machine.py:99` and `tests_scripts/test_fake_surface_conformance.py:27` emptied by MN. Reverse: restore the entries (the checks then fail as designed).
- A-4 U24's deferrals land as plan section 0 says; A.U24.65's third `PER_DEVICE` (concurrency) file is not created. Consequence: the concurrency scenarios run host-side, per device, in the harness. Reverse: create the in-DUT file (duplicates the harness).
- A-5 `pins` added to `TwinWiringPlan` from the `[bus.*]` tables. Consequence: every twin reader takes pins from the plan. Reverse: drop the key and read pins from the TOML (impossible inside the twin process).
- A-6 `tests_hardware/isl29125_conformance.py:32` configures the twin from dev's generated plan in place of `configure_i2c_wiring("dev")`. Consequence: the removed function is gone everywhere; the `"dev"` literal stays for U26. Reverse: restore the function (against A.U25.25).
- A-7 `configure_wiring()` refuses once a bus exists and no longer clears; `reset_peripherals()` clears all registries and DMA channels. Consequence: every twin file resets explicitly (C4). Reverse: restore the clearing (static peripherals then leak between tests silently).
- A-8 SH and G may start single suite or harness runs (one device, one stage, a heavy run each); the whole twin CI suite stays the lead's (lead v0 accepted, narrowed). Consequence: lanes saw their scenarios fail first. Reverse: forbid lane twin runs again.
- A-9 the harness runs from `scripts/run_digital_twin_ci.sh` at U25, before U27's wiring (lead v0 accepted). Consequence: no window in which a moved scenario runs nowhere. Reverse: remove the call (the moved scenarios then run in no CI job until U27).
- A-10 in-process files assert at the armed reset and tear down from outside; reset-and-relaunch is the suite's. Consequence: no in-process graph is stranded by `SimulatedRebootError`. Reverse: none sensible.
- A-11 sensortask integration, timer pool and construction are `PER_DEVICE`; driver-specific cases run on `device_with(...)`'s device only. Consequence: six jobs each, driver work once. Reverse: run every case on every device (more CPU, no new coverage).
- A-12 G pins both failed-arm sites in `tests/test_digital_twin_wifi_modes.py` with `set_alarm_pool_free(0)`. Consequence: OF-148 closed at L2; the pins assert the streak, not the budget's reboot. Reverse: move the pins to the timer-pool file.
- A-13 `tests/_twin_readiness.py` holds `wait_for_value()` only. Consequence: no dead HTTP helper. Reverse: add M.TEST_HELP.060's HTTP helpers.
- A-14 above 15 of `digital-twin-e2e`'s 20 min, or 180 s per `PER_DEVICE` job, the lane stops and reports (lead v0: stop-and-report lines, "a saving never drops a check"). Consequence: SH's report led to lane E and the CI split. Reverse: n/a (a reporting rule).
- A-15 the 50 x 2 grkizi reproduction is the lead's, after SH's final, alone. Consequence: not reproduced in 100 runs (BACKLOG.md owner question 1). Reverse: n/a.
- A-16 SH's one-line `ACTION_PROBES` comment names the twin suite's Run 13; the backups-off step stays. Consequence: `tests_js/live-backend-put-matrix.test.js:103-105`. Reverse: reword the comment.
- A-17 A.U25.61: only P's L0 equality of both device scripts' probe constants; (2)-(4) at U26. Consequence: the probe constants cannot drift apart. Reverse: n/a.
- A-18 the suite's driver tables stay hand tables, tied by SH's L0 tests. Consequence: a new driver fails the L0 until added. Reverse: derive the tables from `buildgen` (a larger change).
- A-19 OF-116: no RH model; the limit stated. Consequence: the twin's RH ignores the temperature offset, said in a comment and a fidelity row. Reverse: model RH from the dew point (a formula the datasheet does not give).
- A-20 OF-112's twin half: a booted silent-FRAM case on `device_with("fram")`. Consequence: landed as a silent-after-boot case plus the harness's `fram:silent` scenario, which accepts the dead chip's escalation (OF-20). Reverse: add the literal "silent before setup, no reset" case (it contradicts U16's escalation).
- A-21 OF-67: the undriven SO level read from the datasheets; 0x00 closes it as modelled. Consequence: the twin answers 0x00; the driver's detection need is OF-167. Reverse: n/a (the level is silicon's).
- A-22 OF-74: `_wire_log_clearer()` calls `clear()` on the bounded log. Consequence: the log stays bounded and counts drops. Reverse: drop the clearer (U35's A.U35.25/.26 decides its fate anyway).
- A-23 OF-108: `_DRIVER_ERRCOUNT_NAME` pinned to each driver's `_NAME` by `ast`. Consequence: a logger rename fails the L0. Reverse: derive the table from `buildgen`.
- A-24 the chip renames: each lane in its own files, D in the docs, the lead's rows his own. Consequence: old names left only in docs until D. Reverse: n/a.
- A-25 OF-19: `WallClock` answers rp2's 8-field tuple, installed by the runner and in-process; the suite asserts `LocalTime` after the first sync (Run 8 at U25's end). Consequence: twin notification windows evaluate. Reverse: normalise per test (leaves the runner blind).
- A-26 the shared bus-hazard catalog stays out of every set; G adapts its twin side. Consequence: no catalog edit at U25. Reverse: n/a.
- A-27 the twin fires the oldest queued fault whose `match` accepts the key, as the unit fake (agent, 2026-10-14). Consequence: a keyed fault never fires on another address; both tiers agree. Reverse: head-only firing (the tiers disagree again).
- A-28 the moved offline NTP writer imports the product's `config_filename()` (lead v1 accepted). Consequence: one source for the file name. Reverse: a named copy pinned by an L0 case.
- A-29 `tests_scripts/test_isl29125_copies.py` covers only the copies `test_const_mirrors.py` misses (lead v1 accepted). Consequence: lane C found 10 missed copies; 25 planted drifts all fail. Reverse: one file for all copies.
- A-30 SH's set gains `tests_js/_twin_process.js` and `tests_scripts/test_live_command_device_args.py`. Consequence: the per-run config dir lands where U24 moved `spawnTwin()`. Reverse: n/a.
- A-31 one API merge (MN1, C1, R1, P1); SH and G straight to their finals. Consequence: one WIP stop. Reverse: n/a (process).
- A-32 the twin UART counts real-poll queries as the unit fake, with the after-each check. Consequence: a real `select.poll()` over a twin UART fails the test (lead ruling 10 followed from it). Reverse: drop the count (a real poll then hangs silently on CI).
- A-33 OF-149: G runs the rewritten file under settrace per device; it closes only with a root cause. Consequence: six devices green, no root cause: OF-149 moved to U28. Reverse: n/a.
- A-34 SH ports P's in-DUT HTTP tests from `8e7dedc`'s text and G's from the W1 merge's; no hand-over wait. Consequence: both landed in the harness (`scripts/_digital_twin_scenarios.py:529, :928`). Reverse: n/a.
- A-35 out-of-set findings retargeted at the close to the next unit whose work-order file list holds the file, U27 if none (lead v1, refined). Consequence: OF-151, 153, 154, 155's rest and every new row targeted so. Reverse: hold them for a U25 follow-up commit.
- A-36 SH kept whole at ~3500 lines (lead v1 accepted). Consequence: one lane for suite and harness. Reverse: split S | H in a later unit.

## Lead rulings and process decisions

- Lead v1 (6): W3 (`e43c61d`, W2 plus the lead step) is D's base. Consequence: D writes against the tree the gate tests. Reverse: n/a.
- Lead v1 (7) launch hold: no heavy lane process until `S/u25/base_times.tsv` exists. Consequence: a clean base table (97 files x 2). Reverse: n/a.
- Lead v1 (8): `tests_scripts/test_device_tomls.py` joins P's set. Consequence: the family check accepts one `PER_DEVICE` file or one wrapper per device. Reverse: the old wrapper glob (red without the wrappers).
- Lead v1 (9): C refuses `inject_hang(times<1)` like `inject_fault`. Consequence: a zero-count hang fails loudly. Reverse: accept it again (silent).
- Lead v1 (10): `tests/_digital_twin_construction_scenarios.py` joins G's set for wave 2 (bounded pollers for the real `select.poll()`). Consequence: dev's boot-sequence scenario green. Reverse: n/a.
- Lane E launched as a fresh lane beside the lead step, not SH again (CHECKLIST rule 2), for boot sharing and the CI split. Consequence: one more lane's fixed cost; the twin CI job time fell under its limit. Reverse: n/a (done).
- MN's attribution drops accepted: `COUNTER_CAP` has no owner source; the packet's "Connection: close (owner, 2026-08-13)" had the wrong date (2026-08-12 in DECISION_PROVENANCE E05), so MN states the fact untagged. Consequence: no unverifiable owner tag in code. Reverse: re-add with a verified source.
- MN's `_http_client` file +20 % (+9-15 ms) accepted as new coverage (5 real-socket cases, one an irreducible 5 ms timeout). Reverse: drop or merge cases.
- C's after-times accepted as new coverage: FRAM 0.20/0.29 to 0.70/1.35 s (the A-20 boot, about 370 ms CPU); SGP40/BMP3XX/ISL29125 +50-60 ms (50 ms probe hangs). Reverse: shorten the probe hangs (tunable).
- `uart_link` 76.1 to 84.2 s at 32768 accepted after an A/B under equal load (+7.6 % with two new CRC16 cases, `S/u25/w3/ab.txt`). Reverse: n/a (under the 10 % line).

## The lead's decisions on the merged trees

- The twin AP keeps cyw43's layout (a /24, the AP its own gateway and DNS) on the loopback, 127.0.0.1/255.255.255.0, instead of A.U25.72's literal 192.168.4.1 (`digital_twin/network.py:38-40`). Consequence: the captive DNS answers twin clients, as it answers on-subnet clients on silicon; the address differs from silicon's. Reverse: 192.168.4.1 plus a query path from that subnet (none unprivileged exists).
- Shutdown hangs are armed only once every supervised task has started (`digital_twin/run_generic_integration.py:529-540`); cancelling the arming task ends its hold. Consequence: each step's target exists when armed. Reverse: arm at build (S1-S5 then miss their targets).
- The planted offline-NTP store holds all six keys, the four defaults as named copies pinned to the product schema (`tests_scripts/test_offline_ntp_config.py:51, :57`). Consequence: no W10 x4 into the FRAM-backed `CFGMGR_NTP` log on a fresh twin boot. Reverse: plant two keys (four warnings per boot).
- Two fresh-boot scenarios run with `offline_ntp=False`, so they see no planted store. Consequence: their fresh-filesystem premise holds. Reverse: plant the store and count it.
- Per-device scratch keys for `PER_DEVICE` files (`dtsi_<device>`, timer pool), checked by `tests_scripts/test_device_tomls.py`. Consequence: two devices' jobs can run at once. Reverse: shared keys (they collided on arzi).
- The CI twin job is split per device, GC stage and part (24 jobs, `ci.yml:621-632`, `run_digital_twin_ci.sh --gc-threshold --part`, local default both). Consequence: dev about 12.2 (suite) and 8.9 (harness) min per job at -1, under the 20-min limit, every check kept; more jobs and setups. Reverse: one job per device (about 36 min on dev, over the limit).
- The runner's WDT prints `WATCHDOG_WOULD_TRIGGER count=N` (`digital_twin/run_generic_integration.py:341-343, :679`) and the hung-step scenario ends on that line within the same bound. Consequence: about 68 s less per stage; the bite (callback removed) fails S1 "did not engage". Reverse: wait out the fixed window.
- W1 integration fixes: `_flash_stall.EPOCH_US` guarded so the twin machine imports under CPython; `machine._plan_table()` callers read with constant keys so the wiring contract's floor sees them; `_TestInertTimer.armed` saturating; `_flash_stall.py` a known ticks user. Consequence: host tests and the contract green on the merged tree. Reverse: n/a (each a check made to hold).
- The runner is a known ticks user and both tiers' detectors name `.ticks_diff(` (lead commit at the API merge). Consequence: an unlisted ticks user fails L1 (bite: passed before). Reverse: n/a.
- The lead step pruned the allow-lists and pending lists by regeneration (deletions only) and shrank the twin `Any` baseline from 16 sections to 2 (machine, bus hazard). Consequence: no stale row left. Reverse: n/a.
- The suite-time items (Run 11, Run 9, Run 10, S1's wait) and OF-149 go to open findings for the next unit holding the suite (CHECKLIST rule 2). Consequence: OF-162..165. Reverse: fix in U25 (a new lane).
- `test_digital_twin_ntp.py`'s 34-35 s left without the promised breakdown: draft default, an open finding (OF-168). Reverse: break it down in the next unit holding the file.
- After lane D (lead commits before the gate): the port-band table must name only live owners (`tests_scripts/test_port_bands.py`, seen failing on the two retired rows, which go). Consequence: a retired file's band is freed and named. Reverse: drop the check.
- The twin AP's link is asserted in the Wi-Fi modes test instead of poked (`tests/test_digital_twin_wifi_modes.py`). Consequence: a twin AP that stops reporting STAT_GOT_IP fails there. Reverse: restore the poke.
- OF-100's twin half closed in-unit rather than moved to U27 (SH's planned step, not in its tree): `_put_reset_errors_timed()` fails on any answer but Valid. Consequence: a "Failed" ResetErrors fails Run 1 and Run 5c on every device. Reverse: drop the word check.
- The timer-pool test's owner tag rescoped to the 2026-07-18 record's own scope (the uptime timer's failed arm), a reader's arm failure pointed at SPECIFICATION.md C.9. Consequence: no wider owner claim than the record carries. Reverse: n/a (the record is the scope).
- The grkizi reboot-relaunch crash not reproduced in 100 runs: BACKLOG.md owner question 1, default (a) close it (agent). Consequence: no rerun; a recurrence fails CI naming the signal. Reverse: (b), the reproduction at each gate.
- The gate's phase B runs as a queue of at most four heavy legs, longest first (gate_v13), since each twin now carries the harness at both stages (CONCURRENCY rule 6). Consequence: about twice U24's phase B wall time, no leg above the wall-time-bound limit. Reverse: gate_v12's seven at once.
- OF-114's flag (a feed gap above three quarters of the watchdog timeout) moved to U27, not done in-unit: the hung-step runs starve the watchdog by design, so the check needs a per-run exemption design. Consequence: the shutdown line carries the gap, nothing fails on it yet. Reverse: n/a.

## Lane deviations

### MN
- Whole Timer, step 90, step 21's behaviour and A-6 pulled into MN1 (C1's required RDID needed both table sizes). Consequence: an earlier, larger WIP. Reverse: n/a.
- `BoundedLog` keeps U24's in-place ring, generic through a runtime-subscriptable stand-in (no explicit `Any`). Reverse: a deque.
- `peripheral()` raises `ValueError` on a malformed name (the packet said return None; the lead accepted the louder form). Reverse: return None.
- `raise_on` entries are `(type, args, times[, params])`. Reverse: the packet's form.
- `ECONNREFUSED` stays a plain `OSError` (MicroPython's `open_connection` reports it only at the first write); no `from e` (no chaining). Reverse: a typed refusal at connect (not what the port does).
- The mem_backup state file holds cause/watchdog_reason/chip_reset/regions; a non-ENOENT `OSError` on its path raises; an empty path keeps it in memory. Reverse: boot as a power-on on a bad path (the silent form the scan fixed).
- The UART registry is the module-level `_UART_OBJECTS`; supersede semantics stay. Reverse: per-id static objects.
- FRAM RDID bytes taken from `asy_fram_driver._KNOWN_PRODUCT_IDS` (the datasheet PDFs could not be rendered). Reverse: re-read from the PDFs.
- NeoPixel writes stay RGB-tuple lists. Reverse: a byte buffer.
- `settle()`'s deadline is the last due time + 1 µs. Reverse: n/a.
- UART `deinit()` keeps U24's register reset; `Pin` keeps U24's line model. Reverse: n/a.
- `digital_twin/machine.py` keeps 3 explicit `Any` (`:134`, `:414`, `:459`; I2C devices by design). Reverse: typed wrappers.
- `FLUSH_EXTRA_PAGES = 36` from the ~1.6 KB config; tSE/tPP from the W25 flash datasheet text (`S/w25.txt:3103-3104`). Reverse: re-measure on silicon.
- The flash-stall windows live in `_flash_stall` (the main mypy pass resolves `machine` to `tests/machine.py`). Reverse: n/a.
- `UART.init()` takes txbuf/rxbuf/timeout/timeout_char/invert as `**settings` (max-args 8, no exemption added), refusing others with `TypeError("extra keyword arguments given")`. Reverse: explicit keywords plus an exemption.
- `_in_running_task` reads `asyncio.core.cur_task` (`core.py:259`) and allocates nothing. Reverse: n/a.
- Tunables estimated with measurements owed (agent, 2026-10-14): `l2.http_client_fetch_timeout_s` 0.001, `_silent_server_s` 2, `l2.machine_timer_short_period_ms` 5, `_rearm_window_ms` 18, `l2.machine_spi_wire_time_us_per_byte` 200, `l2.machine_uart_frame_wire_ms` 5, `_frame_timeout_ms` 50, `_stall_baud` 38400, `_stall_pages` 32. Reverse: measure and update the rows.
- `machine_wdt_short_timeout_ms` 150 to 100; `machine_timer_rearm_period_ms` withdrawn. Reverse: restore the rows.
- Old-API reds left for the lead and wave 2 rather than shimmed (the twin mypy pass carried 88-89 G errors until G's migration). Reverse: n/a.

### C
- The SGP40 VOCState case drives the real reader over `device_with("sgp40")`'s bus, not `build_system`; the silent-FRAM case uses `build_system`. Reverse: boot the whole graph for SGP40 too (slower).
- FRAM rollover copies at most two slices (same result as byte by byte). Reverse: n/a.
- An RDID read past 4 bytes holds the ID's last bit (both FRAM datasheets p10). Reverse: n/a (silicon's).
- `test_a_persistent_chip_read_fault...` and the timestamped case rewritten to rp2's outcome (only 32+ byte reads raise). Reverse: n/a.
- A-29's finding: `test_const_mirrors` missed 10 of 16 ISL copies; the new file covers those, the chip fake's 14 and autorange's 2; `_ADDR_CONFIG3` is not compared (the driver has no CONFIG3). Reverse: n/a.
- Two SCD30 booted cases under `FastAsyncSleep` (1.58 to 0.26 s); the PUT case gets a scratch `cfg_path` (it wrote into the cwd). Reverse: n/a.
- ISL topical section headings dropped with the D.15 reorder. Reverse: n/a.
- The fake's SCD30 rows recorded as assumptions (wrong-CRC, interval and FRC out-of-range answers, pressure persistence, the unknown SGP40 command, ISL's CONFIG1 restart, BMP calibration synthetic). Reverse: replace each when silicon is measured (phase C).
- Tags with a "bounded small hang" basis: `l2.bmp3xx_probe_hang_s` 0.05, `l2.isl29125_probe_hang_s` 0.05; `l2.fram_booted_until_yields` 2000. Reverse: re-basis.
- Counters saturate and FRAM fills use `fill_buffer` once MN's helpers existed (plain `+= 1` in C1 only). Reverse: n/a.

### R
- `RunConfig` groups its arguments (PLR0913): `listen=(host, port)`, keyword `run`, `environment`; flat attributes kept. Reverse: an exemption.
- `main()` runs `install()`, then the prewarm, then the shim (the exception-handler contract needs `install()` first). Reverse: n/a.
- `uart_link_<ext>:silent` finds its bus from the generated `<key> = UARTLinkDriver(uartN, ...)` line (not a private attribute); a plan `uart` block would replace it (P's). Reverse: read the plan block once it exists.
- The NTP responder holds 127.0.0.1:123 exclusively (a refused bind, then a retake) with the binary's CAP_NET_BIND_SERVICE, serving a host time bound at import. Reverse: an ephemeral port plus a product port seam (against "src/ never edited for the twin").
- The shutdown line prints `r0` as four `0x%08x` words. Reverse: n/a.
- `_NTP_STORE_NAME = "NTP"` a named copy (src's `_NAME` is a private const absent at run time), pinned by step 94's test. Reverse: n/a.
- The shim keeps a local counter cap (L1 tests put only `unixport/` on their path). Reverse: import `_twin_common`.
- The stack fault form landed at U25; a frozen `__file__` has no `.frozen` prefix; `.gitignore` keeps the coverage XML lines; S4 is not tested in-process. Reverse: n/a.
- The wall clock goes only into `src/`, `ext/` and generated modules. Reverse: rebind test modules too.
- `_Booted` is read-only (clears a uart_link mypy error). Reverse: n/a.
- No new L1 responder tunable: silent attempts reuse `l1.asy_ntp_client_no_reply_fetch_timeout_ms`. Reverse: a tag of its own.
- The L1 staleness test forces the 1 h and 2 h resyncs instead of 1080 ticks. Reverse: drive the ticks (slower).
- Booted NTP cases run the real `main()` via `load_device` with an SSID file written first; case (5) flashes through one fresh monitor cycle (FlashInterval at least 60 s). Reverse: n/a.
- `tests/test_asy_ntp_client.py` not D.15-reordered (out of order at base; sorting scatters 35 helpers): OF-158. Reverse: reorder now.
- Step 131's DUT side only: `overruns=` reads `UART.rx_overruns`, laps and receive errors together, named so in the suite (`rx_laps_and_errors`). Reverse: a separate lap counter (a `src/` change).
- Tunables: `l2.twin_test_stdin_poll_ms` 50, `twin.ntp_responder_take_rounds` 20, `twin.ntp_responder_poll_ms` 10 (estimated), `l2.twin_feed_gap_fold_ms` 5000, `l2.ntp_reply_wait_ms` 1000, `l2.ntp_run_bound_s` 10.0, `l2.ntp_sync_wait_timeout_s` 20.0. Reverse: re-basis.

### P
- The device set in `scripts/test.sh` comes from the generated wiring plans' stems (nothing re-globs `devices/` after generation). Reverse: glob the TOMLs (against test.sh's rule).
- Band rows follow the consumers' owner names; rows reserved for other lanes; the HTTP-client band widened to 18090-18119; a new row 17500-17509 for the L1 library's override ports. Reverse: n/a.
- `scripts/test.sh` stops when it cannot read a file's `PER_DEVICE` marker, as the memory gate does. Reverse: treat as no marker (the silent form fixed).
- `expected_entries()` moved into `tests/_boot_recorder.py` so both tiers share it. Reverse: n/a.
- The prewarm and UDP shim moved out of the construction library into its entry file (M.TWIN.108 over M.TEST_HELP.029). Reverse: n/a.
- The generated fixture TOML is `fixture_device` (a hyphen is no module name). Reverse: n/a.
- `test_device_tomls.py` accepts a family as one `PER_DEVICE` file or one wrapper per device (lead ruling 8). Reverse: wrappers only.
- Partly: steps 39 and 75 (the harness/scenario job parts are U27's), 41 (the in-memory default mode U27's). Reverse: n/a (staged).
- Bash `time` for timings (`/usr/bin/time` absent; every lane). Reverse: n/a.

### SH
- `TwinRun` landed early, in S1. Reverse: n/a.
- The capability check reads only the binary's xattr. Reverse: try a bind.
- Suite and harness each take a single `--gc-threshold` stage (for A-8 runs). Reverse: n/a.
- `--only` refuses 5b or 4 when their producer run is missing. Reverse: n/a.
- In the generated boot, "cause 3" is the mem-backup cause; `ResetReason` asserted as `_RR_TASK_BUDGET`. Reverse: n/a.
- Run 5 counts two events per failed read (READ + STREAK). Reverse: n/a.
- Config writes PUT `/system` `GMTOffset` (the product's section; the packet said `/networking`). Reverse: n/a (the product decides).
- Silent-chip erase: a refused erase may be followed by the dead chip's own escalation reset (ResetReason 5 asserted). Reverse: demand "no reset" (contradicts OF-20's escalation).
- The hang window is the reset deadline + 8.5 s (the runner prints HANG when it arms); since superseded by the would-trigger line. Reverse: n/a.
- The refusal count uses slow healthy PUTs as holders (an unserved hang-up is itself a drop). Reverse: n/a.
- The held-close burst fills the ceiling minus the probe's slot. Reverse: n/a.
- The harness family banners dropped for D.15, so scenarios run in alphabetical order. Reverse: n/a.
- Partly: step 32's U25 families only ((f)-(j), (1)-(3) are later units'); step 131's verdicts (OF-166); nothing at U25 for 40, 70, 71 (U6/U8/U28/U36, U28). Reverse: n/a (staged or moved).

### G
- UART hazard pairs run at J.6's 115200, set as attributes (the Pair's 9600 spent a frame's wire time twice in the budget; a fake `init()` undid DMA routing). Reverse: n/a.
- Field sweep: each verdict read after the listen returns; the clean exchange is a GET; the J.3/J.4 table restated (no importable L1 table). Reverse: import an L1 table once one exists.
- Hotspot reached by real failure cycles; its waits re-measured 25 to 40 s and 35 to 60 s. Reverse: n/a.
- Heap-drift baseline taken after death 1, each reading the floor of 3 between link exchanges. Reverse: n/a.
- `wifi_modes`: the WiFi service's sleeps divided by 5, poll 0.25 to 0.1 s (101 to 26 s). Reverse: real sleeps.
- Crash points: the next write is read back on the same board; a cut is skipped only for a byte-identical image. Reverse: n/a.
- `uart_link` CRC arms: (a) rounds back to back, (b) the first request corrupted. Reverse: n/a.
- Partly: bus hazard with no cancelled-session case (moved, register `:476`); crash points erase through `manager.erase_chip()`, no cut of the reset delete loop; step 102 without A.U16.17; step 103 one device per driver; system tier tests 11-18 (U35's stage); step 114's U17/U24/U30 stages. Reverse: n/a (later units or the gaps named).
- Not caught, judged inherently safe: a torn chunk write and an interleaved erase invalidation; the two-copy read refuses both (a blank plus E `FRAM_COPIES_DIFFER`). Reverse: n/a.

### E
- A sharing boot may add only `--test-conn-status-interval-ms` (its reading of "no extra runner arguments"); 30 scenarios share, 20 keep their own boot. Reverse: no sharing (170 s instead of 68 s on dev for the 30).
- S1's command waits `_TASK_CHECK_TIME` + the 10 s margin (a race found at base: the command beat the supervisor's next pass); OF-165 records the saving a line would give. Reverse: n/a.
- Families as required literals on `@scenario`, three new (system_commands, webserver_requests, uart_load). Reverse: n/a.

## Lane D

- A stub "Known gaps" heading kept in `digital_twin/README.md`, since eight test files cite it. Consequence: the citations resolve. Reverse: re-point the eight citations, drop the heading.
- SPECIFICATION.md E.8/E.9 `wire_log` now "bounded at 4096 B per direction" (left stale by U24's change). Consequence: the docs state the bound. Reverse: n/a (fact).
- An `sgp40` account added to the twin README's subtleties, since `scripts/_digital_twin_ci_suite.py:134-135` cites one the README never had. Consequence: the citation resolves. Reverse: drop the citation and the account.
- Run 5b's loss restored as "accepted (owner, 2026-09-11; confirmed 2026-09-26, paraphrase ...)", as SPECIFICATION.md A.4 has it (D's draft had quoted the paraphrase as the owner's words). Consequence: actor and qualifier as recorded. Reverse: n/a.
- Not applied, left to their units: A.U25.61's flash check (U26: `flash/test_heap_layout.py`, U26 plan), M.TWIN.064's Run 1 NTP sentence (U35); M.TWIN.072's pointer stays at C.11. Consequence: those texts follow with their units. Reverse: n/a.

## The gate and the close (lead)

- The gate ran twice: gate1 on `f69fc2a` found three reds, each fixed in-unit with a test seen failing first; gate2 on `e1106ac` re-ran only the legs the diff since reaches (lint, typecheck, `test.sh` at both stages with the `tests_scripts` tier, the harness part on six devices); the suite part, `npm test` and coverage stand on gate1. Consequence: about an hour of heavy runs saved, no leg left unchecked against its inputs. Reverse: re-run the whole gate.
- The installer's `run()` holds SIGINT, SIGTERM and SIGHUP only while a command starts, only where a Python handler would raise and only on the main thread, and raises each held signal inside its `try`. Consequence: an interrupted start stops its command; the child's signal mask is untouched (no `pthread_sigmask`). Reverse: n/a (a race fix).
- The twin CI runner builds the site each part boots from (the suite's `frozen_modules/`, the harness's `build/generated_html/<device>`), once per part. Consequence: a CI job builds only what its part reads. Reverse: the harness reads `frozen_modules/` (then it depends on which device was built last).
- OF-104's README sentence fixed by the lead in-unit rather than moved to U26 (the docs lane had left it). Consequence: the row closes at U25. Reverse: n/a.
- `S/CHECKLIST.md` rule 13: a run standing in for a CI job starts from a tree without gitignored build output; rule 14 times with bash `time`. Consequence: U26's lanes inherit both. Reverse: n/a.
- Evidence keeps each lane's hand-back and top-level logs, not the harness's per-scenario twin logs (about 200 MB). Consequence: the record cites summaries; the per-scenario logs stay in the session scratchpad until it ends. Reverse: stage them gzipped.

