V2 hand-back (lane V, block 2). Branch audit/u35-v in S/wt-u35v. One commit, **83c9475**, on 97a034c. Only tests/_sensortask_scenarios.py changed (+269/-2); test_sensortask.py is untouched. Nothing pushed, nothing uncommitted. About 52 tool calls.

**Steps by verdict**
- **C4's red: applied.** At :3023 the scenario now patches `ntp_clock_valid`. Seen failing: the base (97a034c) fails only `webserver_status_publishes_utc_time_only_after_the_first_ntp_sync`, 90/91 on all 6 devices at both stages (12/12 runs). The head is 96/96.
- **Stale clock (LEAD NOTES 11): applied.** New `webserver_status_keeps_utc_time_through_a_stale_sync_and_flags_it` (:3037):
  - stale window: `UTCTime` is a dict, `TimeStale` is true, and the SGP40 backup's `write_into(require_ntp=True)` is stamped through the real `SgpBackup` callback;
  - after `ntp_force_sync()`: `UTCTime` is null, `TimeStale` is true, and the backup is refused with (False, False, None);
  - it asserts every device has an SGP40.
  - Seen failing on e6f8065 (the head before the merge, its own generated modules): the stale-window assertion fails with `UTCTime: None` and no `TimeStale` key.
- **Step 114: partly applied.** All four groups exist, run on every device and were each bitten. What is narrower than A.U35.28/.30/.33/.34:
  - **Stuck task** `a_task_that_keeps_ending_stops_every_feed_once_its_reboot_is_armed` (:1569). Under `DrivenTime(asy_system_service, sleeps=True)` the supervisor feeds twice, then one task ends at every pass. Asserted:
    - feeds from the first end to the armed reset equal the number of ends (the escalating pass feeds once);
    - ten more passes plus every live Timer except the reset's add no feed, and the supervisor keeps running;
    - the reset timer is armed and has not fired;
    - after a rebuild on the chip image, SYSTEM's restored log has ErrCount equal to the old count + ends + 1, and holds errnos 44 and 41.
    - Not written: (1) an exception escaping the supervisor, (2a) a cancelled `main()`, (3) the blocked loop's structural half. Pin IRQs are not fired, because tests/machine.py keeps no registry of pins.
  - **Forty days** `forty_days_of_uptime_keep_every_invariant` (:1614). The clock starts 1 h before a wrap and runs 960 one-hour `jump()`s, each delivering one uptime tick (4 wraps crossed). Asserted:
    - SysUptime and `LastTaskEnd.Uptime` equal the driven seconds;
    - at least 960 feeds and no reset;
    - one early end's charge has decayed: three ends in a row then arm nothing.
    - Not covered: WiFi uptime, NTP age and resync count, ring saturation per logger, ISL29125/UART stored ticks.
  - **Dropped tick** `dropped_one_second_wake_ups_never_skew_elapsed_values` (:1661). 600 driven seconds with every third tick dropped, a 5 s gap and a 7.5 s stall. SysUptime equals floor(elapsed), and a 10 s storage pause ends 0 to 1000 ms late.
  - **Fault storm** `fault_storm_keeps_every_module_within_its_persisted_log_rate` (:1707). Every FRAM-backed logger in one concurrent burst (5 repeats + 1 other code). Asserted:
    - each logger's chunk writes are between 1 and its number of entries;
    - a repeated newest code takes one slot while the count rises;
    - chip writes are no more than the chunk writes times the probe's cost per chunk write.
    - Not covered: the module periodic paths (bus NAK, NTP no reply, webserver drops), the scan budget, recovery and ladder rungs, and the L2 half.
- **Decisions (agent, 2026-10-21):**
  - Every slot except the system status loop is a planted stand-in under the real supervisor. The driven clock covers only asy_system_service and asy_base_classes.
  - The dropped-tick group uses the system storage pause, not the notification `PauseTime`, because every device has storage.
  - The storm group's L1 bound is "one entry per chunk write" (the `rate.persisted_log` row). The ms rate belongs at L3.
  - I count chunk writes by putting a stand-in on the instance's `write_into`, since tests/_fram_chip_fake.py has no counter per logger.

**Bites** (each in a scratch src copy put first on MICROPYPATH, then deleted; nothing planted is committed)
- feed ignores the starve flag → `{'after': 28, 'armed': 17}`
- a second `write_into` per entry → WIFI spent 12 > 6
- `now - self._last` in TickSeconds → forty days 4487790 vs 4502190
- delta capped at 1000 → dropped 396 vs 608 (forty days also red)

**Checks**
- ruff clean.
- Both main mypy passes rc=0: cold cache, typings symlink removed after.
- The 12 commit checks plus the readers device_tomls, test_sh and digital_twin_ci_suite_errcount: green except test_tunables_register, which is Y2's known red, waiting on D: `tests/test_bus_hazard_multi_device.py:64: l1.bus_fault_isolation_bound_s is tagged but has no SPECIFICATION.md Part N row`.
- No allow-list row orphaned. No relay lines written.

**Times** (test_sensortask, base 97a034c → head, alternating; s at -1 / 32768; zero MemoryError and zero "memory allocation failed" in every log)

| Device | -1 | 32768 |
|---|---|---|
| arzi | 28.14→37.22 | 32.08→40.68 |
| dev | 45.41→53.76 | 52.02→62.89 |
| grkizi | 27.62→36.09 | 31.36→41.58 |
| klkizi | 27.83→36.03 | 31.09→40.80 |
| schlafzi | 28.21→36.67 | 32.01→41.30 |
| wozi | 31.35→40.24 | 35.93→45.66 |

- Every file grew 8.2 to 10.9 s, all of it from the new groups. Each group's added time (s, range over devices and stages):

| Group | Added time |
|---|---|
| forty days | 4.89-5.35 |
| dropped tick | 2.05-2.27 |
| storm | 0.80-1.58 |
| stuck task | 0.36-0.65 |
| stale clock | 0.17-0.44 |

- The remaining 0-1 s is host noise: about 5 other heavy processes were running, and the C4 scenario now runs to its end.
- One wrinkle: the first pairing's 32768 base runs had imported the head scenarios, because `_threshold_runner` puts its own directory first on the path. I re-ran them with the runner placed beside each copy and deleted the wrong logs.

**V3's start:** audit/u35-v at 83c9475, clean tree, no typings symlink. Open:
- the A.U35.30 cases (1), (2a) and (3), plus Pin IRQs;
- the uncovered parts of forty days and the storm listed above;
- OF-200 / the forced 60 s retry (LEAD NOTES 30);
- the D.15 reorder of this file (LEAD NOTES 26). The new helpers sit at :1530-1566 and the scenarios at :1569-1740 and :3037.

Logs and scripts are in S/u35/laneV/v2/. RUNS.md has start and done lines for pids 6287, 12118 and 17284. Nothing of mine is running.