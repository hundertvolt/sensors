V6 hand-back (lane V, last block). Branch audit/u35-v in S/wt-u35v. One commit, c9904c2, on 8edb5aa. Nothing pushed. Nothing uncommitted. No typings link left. Nothing of mine is running. About 62 tool calls.

**Parts by verdict**
- **Pin IRQs: applied.** tests/machine.py already kept a state table per GPIO (`Pin._states`), but nothing listed the wired pins. New test-only `Pin.wired_irqs()` (in TEST_API) returns a Pin for every GPIO with a handler. The new scenario helper `_fire_wired_irqs()` fires each one through its real handler. All three feed scenarios (stuck task, escaping exception, cancelled main) now do this next to the live Timers and assert no feed and irqs > 0. I left :598 as it was.
  - Seen failing: I planted an IRQ that feeds the watchdog directly, in a scratch copy of asy_system_service. All three scenarios go red on arzi and on dev, e.g. `{'after': 16, ..., 'armed': 15, 'irqs': 2}`. The base 8edb5aa passes 3/3 with the same plant.
- **New finding, fixed in my file:** `_arm_every_timer()` never called `_collect_trigger_starters()`. So the ISL29125's IRQ and the readers' trigger timers were never armed. On dev the scenarios fired 5 timers before and 8 now, plus GPIO6.
- **Forty days: partly applied.** New scenario `forty_days_keep_the_wifi_uptime_and_the_ntp_sync_age_on_the_driven_seconds`, next to the existing forty-days one. It runs the real WiFi uptime and NTP sync-age loops through five-day stalls, with a resync on day 20. Both values equal the driven seconds across four wraps.
  - Bites, each red on arzi and dev:
    - p2, no per-tick WiFi read: 234774 vs 3456000.
    - p3, an NTP read on every other tick only: age 0 vs 1728000.
  - Not written: NTP resync count, ring saturation per logger, ISL29125 stored ticks (asy_isl29125_driver.py:431, :567), UART stored ticks (asy_uart_comm.py:381).
- **Storm:**
  - Scan budget: already landed in `one_supervisor_pass_over_dead_tasks_persists_at_most_one_entry_per_end` (the SPEC row `system.scan_budget` names it).
  - Not written: periodic paths (bus NAK, NTP no reply, webserver drops), recovery, ladder rungs.
  - L2 half: T's Run 3 already carries it at b7d9f31 (scripts/_digital_twin_ci_suite.py:94-96 and :1258, the ceiling of window / 627 ms × 2). Run 5c covers one bounded fault per chip on its periodic bus call (:97-98). Both are on T's branch, not on V's tree.

**Findings for the lead** (none fixed: the tests belong in tests/test_fakes.py, which is not V's)
- tests/machine.py:150, `irq()` accepts an external pin. rp2 raises ValueError("expecting a regular GPIO Pin") (machine_pin.c:464-466).
- tests/machine.py:150, `irq()` with no arguments clears the handler. rp2 returns the IRQ object unchanged (machine_pin.c:473).
- Class 5, src/asy_ntp_client.py:374. The resync cadence counts delivered 10 s ticks, not elapsed time, so a dropped tick delays the resync. The stale rule at :372 reads elapsed time, so the status stays honest.

**Times** (test_sensortask, 8edb5aa → head, alternating, the runner beside each copy; seconds at -1 / 32768)

| Device | -1 | 32768 |
|---|---|---|
| arzi | 31.60→32.16 | 37.03→37.60 |
| dev | 51.29→51.42 | 60.04→61.06 |
| grkizi | 32.11→32.34 | 36.90→37.70 |
| klkizi | 32.78→33.26 | 37.28→37.50 |
| schlafzi | 32.56→32.80 | 37.15→37.93 |
| wozi | 35.86→35.84 | 41.57→41.96 |

- Every file grew under 2.2 %.
- The base passes 98/98, the head 99/99, on all six devices at both stages.
- Per part: the new forty-days scenario takes 181-341 ms. The IRQ firing adds -50 to +27 ms per feed scenario (noise).

**Checks**
- ruff is clean. All three mypy passes are rc=0 (cold cache).
- D.15 shows only the known `@_register` line.
- In one pytest process I ran the 12 commit checks, the 17 scans and every reader of my two files: 1697 passed, 4 red. The red lines are byte-identical to V5's:
  - test_tunables_register: asy_config_manager.py:71 and test_bus_hazard_multi_device.py:64, waiting on D;
  - test_microtest ×2: test_asy_config_manager.py:3325 and json.loads 10 vs 2, lane P's file;
  - test_twin_record: expected.
- test_digital_twin_generated_boot reads digital_twin/machine.py, not tests/machine.py, so I did not run it.
- Zero MemoryError and zero "memory allocation failed" in any output.

**Decisions (agent, 2026-10-22)**
- The registry reuses the existing state table and adds no new state.
- All three feed scenarios fire the IRQs, as the step's text asks ("every Pin IRQ fired").
- The planted feeding IRQ sits in the system service, the one module that holds the watchdog.
- Five-day stalls stay under the 2**29 ms horizon and keep the scenario cheap. The NTP refresh loop is not run, so Synced stays true.

**Effect per mode:** tests only. STA, AP, Silent, Off and USB are unchanged on every device.

**Runs** (each with RUNS.md lines): 15 short scenario runs (head, the plants p1-p3, the base under p1), all exits as expected; checks c1 rc=1 (the reds above); chain.sh, 24 runs, all rc=0.

Logs are in S/u35/laneV/v6/:
- a_*, a2_*: the IRQ case and bite p1;
- b_*: forty days and bites p2/p3;
- pb_*/ph_*: the paired times;
- c1_*: the checks.

The plant and run copies are deleted.