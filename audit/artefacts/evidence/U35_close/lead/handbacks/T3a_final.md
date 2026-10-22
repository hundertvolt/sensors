T3a hand-back (lane T, audit/u35-t, S/wt-u35t). One commit: ffd742f, on f9569b9. Nothing uncommitted, and nothing of mine is running. 68 tool calls, so I stopped at the valve.

**Steps**
- **124, test 2: applied.** It is renamed `test_watchdog_is_never_starved_while_the_real_supervisor_runs` and drives `module.main()` under the tracked `run()`. `_feed_watchdog_periodically()` and the hand-started timers and tasks are gone.
  - A class-level wrap of `SystemService.boot_phase` wires the UART crossover at BOOT_SETUP and records the feeds at each mark. So the old assertions are kept: feeds == len(setups) == len(stamps), and the stamps run in order.
  - Boot is gated on an event at BOOT_DONE. Then the first supervisor feed, then `sleep(_WDT_OVERRUN_WAIT_S)`. It asserts `would_have_triggered_count == 0` and `not main_task.done()` (new).
  - Offline case: a stored SSID links the station. It asserts that an NTP attempt was sent (`ntp._retry_wait_s > ntp._retry_s`) and that the shim reads `(0, None)`.
- **Fold (12): applied** as `test_a_boot_without_ntp_reports_no_local_time` (arzi). With no clock it reports State 2 and no trigger; once synced, a cycle inside the window reports State 0.
- **Fold (14): not committed.** On unplanted head, dev's SCD30 snapshot fault (one EIO on `readfrom_into`) gives nulls, not the marker: `AssertionError: scd30's failed snapshot sent {'SCD30': {'SelfCal': None, ... 'FRCWindow': None}}`. bmp3xx gave the marker. The code reading (`_config_snapshot` returns None, so the marker) does not explain it. This may be a class-4 defect (a failure sent as nulls), owner of the site unknown. The draft test and plant are in S/u35/laneT/t3a_plant14/.
- **Folds (11), (13), (15), (16), (18): not started** (budget). Note for (16): the connect poll keeps its real 500 ms step, so each no-verdict cycle is about 5 s real, about 25 s per device.

**Bites** (scratch dirs ahead on MICROPYPATH, nothing committed)
- Supervisor feeds once: `AssertionError: [14]`, plus the PC-report test's "supervisor stopped passing", as expected.
- Public NTP destination: `the offline boot sent outside the twin: (1, ('8.8.8.8', 123))`.
- No clock read as off: `no clock reported as NOTIFY(Triggered=False, State=1, TS=None)`.

**Wait table (CG)**
| Wait | Verdict |
|---|---|
| Test 2 WDT period, 9 s, every device | Stays: the twin WDT counts real time (machine.py `_countdown`/`_arm`). |
| Test 10 idle window, 3 s, arzi | Stays: the rate is wake-ups per real ms. |
| `_hotspot_boot` streak, about 25 s × 2 on arzi | Moved to `_SteppedWifiAsyncio`. |
| Test 3 supervisor 2 s pass | Moved to `_FastSupervisorAsyncio`. |
| Test 2 boot | Event-gated. |

Left real, as candidates:
- test 4's link wait and its two uptime ticks: the timer callback could be fired (every device);
- the PC-report test's link wait: its drift bounds were measured with the real waits;
- the SGP40 init and cycle waits in tests 6-8, and test 9's SCD30 and monitor cycles (arzi).

**Times** (paired, base S/wt-u35base / head, -1 | 32768, all rc=0, mem=0)

| Device | -1 | 32768 |
|---|---|---|
| arzi | 118.04 / 68.22 | 118.08 / 68.65 |
| dev | 22.78 / 23.40 | 23.28 / 23.69 |
| grkizi | 21.49 / 21.69 | 21.62 / 21.89 |
| klkizi | 21.39 / 21.75 | 21.84 / 22.02 |
| schlafzi | 21.50 / 21.69 | 21.72 / 21.95 |
| wozi | 21.89 / 22.25 | 22.21 / 22.57 |

- The final file reran at dev -1 23.38 s and arzi 68.65 s.
- Added time: the no-clock test is about 1 s on arzi, inside arzi's -50 s. Test 2 nets about +0.3 s per device.

**Red, unexplained**
- `tests/test_digital_twin_sensortask_integration.py` :603 (that run's line), `test_a_supervised_task_death...`: `AssertionError: 56 B retained per supervised death: [1304832, 1304032, 1304032, 1303680, 1303456, 1303680, 1303680, 1303680, 1303680, 1303872]`.
  - It failed in the matrix's head dev -1 run, and twice more on an intermediate file whose test runner had been misplaced. It passed in h1 and on the final file (dev -1), and on dev at 32768.
  - Base passed in its one paired run.
  - The test is unchanged. One dip at death 4 against the window minimum sets the slope; the check limit is 32 B.
  - Root cause not found. The next block should run dev -1 several times on base and head.
- Logs: S/u35/laneT/t3a_pair_wt-u35t_dev_-1.log, t3a_re_*.log.

**Checks:** ruff clean; twin mypy 0 issues; the 12 checks plus gc_collect_sites passed (861). No allowlist or register row orphaned.

**Decisions (agent, 2026-10-21):**
- The offline case shares test 2's boot, linked through a stored SSID.
- The shim's knobs are zeroed at that boot's start.
- The paraphrase mark in test 2's comment is kept.

**Relay:** none written.

**Runs** (all logged in RUNS.md):
- h1 rc0; plants rc1 (bites);
- plantW and plant12 rc1 (bites); h14 rc1 (finding);
- pair rc1 (dev -1 drift red); re rc1 (intermediate file); fin rc0.

**T3b starts** from ffd742f, clean. Open threads:
- folds (11), (13)-(16), (18);
- the SCD30 nulls finding;
- the drift flake.
