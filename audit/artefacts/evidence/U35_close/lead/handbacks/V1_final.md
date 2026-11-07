V1 hand-back (lane V, block 1). Branch audit/u35-v in S/wt-u35v. Commits on top of 949a68a: 8fb2c49, 498b54b, fb9c0e1. Nothing pushed, nothing uncommitted. I used about 50 tool calls.

**Steps**
- **Flash stall wrap: applied, 8fb2c49.**
  - The change: `digital_twin/_flash_stall.py` now stores each window as (start, length). start is still `ticks_diff(start, EPOCH_US)`; `irqs_were_off()` checks `0 <= ticks_diff(at_us, start) < length`.
  - The test: `tests/test_ticks_rollover.py` has a new test plus a `_FlushClock` class and two helpers.
  - Seen failing on the old code: `AssertionError: (False, False, False)` against (True, True, False), at test_ticks_rollover.py:722.
  - Decision (agent, 2026-10-21): I compare through `ticks_diff()` in the frame machine.UARTLink already passes in, not with an accumulated clock. machine.py:937's offset wraps the same way, and reading a clock at query time would break test_digital_twin_machine.py:1593, which puts the real clock back before the burst is read.
  - Effect: twin only, STA/AP/Silent/Off/USB unchanged on every device. The 2**30 build's confirmation stays B1's `<T30>`.
- **Bus hazard waits: 2 moved, the rest stay, 498b54b.**
  - The flap test's fixed 75 s sleep is now `asyncio.wait_for(flap_task, _FLAP_WINDOW_S)`. A timeout fails with the reconnect assertion's own message, and every assertion stays.
  - The SCD30 healthy window's fixed 4 s sleep is now `_scd30_cycle()`: wait for one whole SCD30 cycle, bounded by the same 4 s. The old sleep passed even with no cycle at all.
- **D.15 order for the catalog and multi_device: applied, fb9c0e1.**
  - The helper functions in each file now sit in one sorted block, placed after the classes their unquoted annotations name: BusOccupant in the catalog, `_EraseWireMB85RS2MTA` in multi_device. Placing the block at the top hit F821 on those annotations.
  - Checks: non-blank line multiset identical, every top-level AST identical, fixed statements in their old order. Blank lines went 172→173 (catalog) and 195→195. No meaning change.

**Finding, owed to the lead (an owner question)**
- The flap test now ends about 1 s after the disconnect: 76.8 s → 11.3 s. `_run_sta_mode()` (src/asy_wifi_service.py:768-776) reconnects inside the lock and only waits 60 s, outside the lock, after a failed attempt. So the "genuine 60 s wifi_mode_lock hold" in the owner's recombination sentence (bus hazard :477-478) never happens, and it did not happen in the old 75 s either.
- Class: a check that matches nothing; twin, STA, the first shared-bus device.
- I left the owner's sentence and `_wait_established_then_flap_once`'s comment (:950-952) as they are. Whether to force a failed reconnect so the 60 s wait really runs is the owner's call.

**Wait table (bus hazard, line numbers at 949a68a; sleep(0) yields hold no wall time)**
| Line | Wait | What it waits for | Verdict |
|---|---|---|---|
| :119 | poll 0.1 s | `_reset_armed` | stays: already event-gated |
| :163 | sleep 1 s | watchdog feeder | stays: runs in the background; the twin WDT measures the gaps on the real clock (machine.py:1517) |
| :204, :218, :223 | polls 0.1 s | readers ready, rungs, streak unwinding | stays: event-gated, but the time is the real task graph's cadence, see clock note |
| :258 | sleep 9 s per device | concurrent bus load | stays: the length of real load is the scenario's subject |
| :304, :365, :723, :836 | sleep(0) | scheduler turns | stays |
| :493 | sleep 75 s | flap window | **moved**: ends at the reconnect, bound 75 s |
| :556 | poll 0.1 s | timed pause ends | stays: the real 2 s deadline and the uptime pass are the subject |
| :939, :942 | polls 0.5 s / 1 s | established, reconnected | stays: event-gated; these are tunables |
| :1021 | sleep 4 s | healthy window | **moved**: one whole SCD30 cycle, bound 4 s |
| :1029 | poll 0.1 s | each round re-sends the setter | stays: the poll is the test's action |

Why the twin's clock cannot be driven here: the twin Timer steps with real `asyncio.sleep_ms` (machine.py:1416), and the SCD30's readings come from it (_scd30_chip.py:232-236). DrivenTime caps parked sleepers at 64 (tests/_fake_time.py:63). This branch also lacks `<SHIMFIX>`, and every teardown cancels the started tasks (`_cancel_started_tasks`, :148).

**Seen failing and bites:** the stall test failed on the old code (above). A link that never reconnects failed at 77.1 s with "WiFi never recovered…". An SCD30 that makes no reading failed at 5.5 s with "no whole SCD30 measurement cycle…". The bite copies are deleted; nothing planted was committed.

**Runs (s at -1 / 32768; all rc=0, zero MemoryError and zero "memory allocation failed")**
- Paired base/head:
  - twin bus hazard 150.38/151.59 → 84.28/86.17
  - rollover 3.84/3.84 → 3.81/3.93 (one more test)
  - multi_device 3.24/3.60 → 3.01/3.48 (Y2 deleted a test before I branched)
- Head only:
  - i2c_driver 1.52/1.55; bus_hazard_generated 63.39/63.52
  - twin machine 1.23/1.19, machine_uart 3.67/3.87, run_generic_integration 1.44/1.44, uart_link 55.02/58.89
  - sensortask arzi 27.86/32.77, dev 45.34/52.58, grkizi 27.89/31.29, klkizi 27.97/31.72, schlafzi 27.81/31.20, wozi 31.55/35.21
- Nothing is more than 10 % slower. RUNS.md has two start and two done lines (pids 22434, 13301).

**Checks**
- ruff clean; all three mypy passes rc=0 (cold cache, the typings symlink removed after).
- The 12 commit checks plus the readers I chose (ticks_wrap_scan, no_variant_literals, fake_surface_conformance, twin_fake_catalog, twin_never_needs_tests_on_its_path, suppression_form, ruff_exemptions_live) passed, with one red: `tests/test_bus_hazard_multi_device.py:64: l1.bus_fault_isolation_bound_s is tagged but has no SPECIFICATION.md Part N row`. That is Y2's known red, waiting on D; the reorder moved it from :71 to :64.
- After the last comment edit, decision_vocabulary, comment_block_cap and citations passed again.
- No allow-list row orphaned, no relay lines written.

**Facts owed**
- To D (Part N): `l2.bus_hazard_concurrency_flap_window_s` keeps 75.0 but is now a bound, not a fixed window. `l2.twin_wdt_feed_interval_s`×4 is now the SCD30 cycle's bound.
- To the lead (residual, class 5, twin, 2**30 build): a window exactly 2**30 us (about 17.9 min) old still matches a byte due one period later. Fixing it needs machine.py:937, which is Y's file, to pass an unbounded time.

**V2's start state:** audit/u35-v at fb9c0e1 in S/wt-u35v, clean tree, no typings symlink. Every V1 step is complete. V2 waits for Y4's `<HANDOVER-SCEN>`, then takes tests/_sensortask_scenarios.py and tests/test_sensortask.py (step 114 and the `<CLOCK>` assertions). Logs and the per-test times are in S/u35/laneV/v1/ (times.txt, r_*.log, seen_failing_stall.log).

Nothing of mine is running.
