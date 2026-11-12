# U25 rulings (plan §5 defaults, `S/u25/lane_plan_v1.md`, with the lead's v0 rulings `S/u25/lead_rulings_v0.md` folded in)

Every ruling is conservative and reversible, decided on the owner's behalf and listed for their review at U25's close;
A-1..A-26 (agent, 2026-10-13) as re-checked on `8e7dedc`, A-27..A-36 new (agent, 2026-10-14). Reasons: `S/u25/refresh_delta.md` §5.

1. A-1 the U24 base: done; U24's API is in place by name on `8e7dedc`; anything else a lane finds missing stops that item with a report (lead v0: accepted).
2. A-2 the cut (v1): wave 1 MN (v0's M then N), C, R, P; wave 2 SH (S's steps, then H's), G (G1's, then G2's); the lead step; wave 3 D (X, Y, W) (rule 13).
3. A-3 the twin pending lists: `tests/test_digital_twin_machine.py:84-89` and `tests_scripts/test_fake_surface_conformance.py:27` (both MN's) shrink in the commit whose change makes the check pass; `check_inject_fault_fifo` on MN's api1 resume after C1.
4. A-4 U24's deferrals: as v0 §0; A.U24.65's third `PER_DEVICE` file (concurrency) is not created.
5. A-5 `pins`: P adds `pins` to `TwinWiringPlan` (`buildgen/twin_wiring.py:35-40`) from the `[bus.*]` tables; the contract test pins it.
6. A-6 the L3 helper: MN replaces `tests_hardware/isl29125_conformance.py:32`'s `configure_i2c_wiring("dev")` with `configure_wiring(json.load(...))` of the same plan; `pytest --collect-only tests_hardware` stays clean.
7. A-7 configure after construction: `configure_wiring()` stops clearing (`digital_twin/machine.py:345-347`) and refuses once a bus exists; `reset_peripherals()` clears the registries and closes the DMA channels.
8. A-8 lane twin runs (lead v0, narrowed): SH and G may start single suite or harness runs (one device, one GC stage), each a heavy run (RUNS.md, own `unshare -n`, nice 19, one per lane, only while ≤ 4 heavy run); the whole twin CI suite is the lead's.
9. A-9 the harness before U27 (lead v0: accepted): SH adds the two-line harness call to `scripts/run_digital_twin_ci.sh`, after the suite, inside the script's port lock.
10. A-10 in-process resets: assert at the armed reset, tear down from outside; the reset-and-relaunch is the suite's.
11. A-11 `PER_DEVICE` twin files: sensortask integration, timer pool, construction; a driver-specific case runs on `device_with(...)`'s device only, `Skip` elsewhere.
12. A-12 OF-148: G pins both failed-arm sites in `tests/test_digital_twin_wifi_modes.py` with `set_alarm_pool_free(0)`, asserting the owner's 2026-10-13 rule ("Take option b for 2").
13. A-13 `tests/_twin_readiness.py`: `wait_for_value()` only; no HTTP helper.
14. A-14 twin-tier time (lead v0: stop-and-report lines): above 15 of `digital-twin-e2e`'s 20 min, or 180 s per `PER_DEVICE` job, the lane measures and reports; a saving never drops a check.
15. A-15 the grkizi reproduction: the lead's, after SH's final, alone (50 x 2).
16. A-16 Run 13 in the put matrix: SH's one-line `ACTION_PROBES` comment (`tests_js/live-backend-put-matrix.test.js:104-106`) names the twin suite's Run 13; the backups-off step before the probe stays.
17. A-17 A.U25.61: only (1), P's L0 equality of both device scripts' probe constants; (2)-(4) at U26.
18. A-18 the suite's driver tables stay hand tables, tied by SH's two L0 tests.
19. A-19 OF-116: no invented RH model; the limit stated (C's comment, D's fidelity row).
20. A-20 OF-112's twin half: C's booted silent-FRAM case on `device_with("fram")`.
21. A-21 OF-67: C reads the datasheets for the undriven-SO level; 0x00 closes it as modelled, never an invented level.
22. A-22 OF-74: R's `_wire_log_clearer()` calls `clear()` on the bounded log, never rebinds.
23. A-23 OF-108: SH pins `_DRIVER_ERRCOUNT_NAME` against each driver's `_NAME` read by `ast`.
24. A-24 the chip renames: each lane in its own files; D in the docs; the lead's rows its own.
25. A-25 OF-19: `WallClock` returns rp2's 8-field tuple; R installs it, G in process, SH asserts `LocalTime` after the first sync.
26. A-26 the shared catalog (`tests/_bus_hazard_catalog.py:560-580`) stays out of every set; G adapts its twin side; a needed assertion change is reported to the lead.
27. A-27 the fault-queue match order: the twin fires the oldest queued entry whose `match` accepts the key (no `match`: any key), as the unit fake; the shared contract pins it once both tiers pass (C).
28. A-28 the moved NTP writer (R): keeps U24's derived file name (`config_filename()` and the store's own name), no literal path, no import from `tests/`; the name is read from the product module the runner already loads, or a named copy pinned equal by R's L0 case.
29. A-29 A.U25.49: C bites `tests_scripts/test_const_mirrors.py` on a planted drift of each copy; `tests_scripts/test_isl29125_copies.py` is written only for copies that check misses.
30. A-30 SH's set gains `tests_js/_twin_process.js` (U24's `spawnTwin()`: the per-run config dir and `--mem-backup-state-path ""` go there) and `tests_scripts/test_live_command_device_args.py`.
31. A-31 merge form: one API merge (`audit/u25-api1`: MN1, C1, R1, P1); SH and G run straight to their finals; SH's S1 is a commit, not a stop.
32. A-32 the twin UART counts real-poll queries as the unit fake (`tests/machine.py:752-761, 979-982`) with the same after-each check (MN, A.U25.04).
33. A-33 OF-149: G runs the rewritten file under settrace once per device in its checks; it closes only with a root cause, else stays open with the runs recorded, for the next unit editing the file.
34. A-34 wave 2's in-DUT HTTP tests: SH ports P's from `<U24>`'s text and G's from `<W1>`'s; G deletes its own in its final; no hand-over wait; the squash lands both.
35. A-35 out-of-set findings (OF-151 SCD30/ISL29125, OF-153, OF-154, OF-155's `tests/test_generated_boot_entry.py:61` and `tests/test_digital_twin_unix_port_unretrieved_report.py:84`): no lane takes them; the lead retargets each at the close to the next unit the work order has editing its file, U27 if none earlier.
36. A-36 SH's size: ~3500 changed lines, at the split line; kept whole (the split S | H adds a lane's fixed cost and no parallelism).

Carried (lead v0): F1 9(a) → A-27; 9(b) → A.U25.70's fresh exception (C); 9(c) → A-32; F final's mapping
(`check_inject_fault_fifo` → A.U25.70/M.TWIN.002; the pin checks → A.U25.02/.05/M.TWIN.021; `check_reset_never_returns`
→ A.U25.07/M.TWIN.034; surface → M.TWIN.020-036); TWIN.130's static object and clamp (MN); C5: M.TOOL.032's U24 stage
with M.TWIN.108 (the lead step; P). Evidence: `u25/tools/root_e14d76f/` is a tree copy, never evidence.
