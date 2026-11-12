# U35 W6 lead items as one block (lead, 2026-10-22)

The block reads `S/u35/briefs/common_u35.md` first, then its section here. About 60-80 tool calls: at 70, finish the step
in hand, commit, and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.

## L1 (lane L: the lead's W6 test items on the merged lanes)
Start: create branch `audit/u35-l` at `152f1ca` (the integration head: U34's final and the finished lanes C, E, F, H,
N, P, Q, U, W, Y, B1 and D1 merged, plus two lead edits) and its worktree `S/wt-u35l`
(`git -C /home/user/sensors worktree add -b audit/u35-l S/wt-u35l 152f1ca`), then `S/u23/rebuild.sh S/wt-u35l`.
Lanes V, T and G are still running and merge later; do not touch their files (`S/u35/lead/lanes.py` "V", "T", "G").
Files: tests/_cancel_sweep.py, tests_js/live-backend-put-matrix.test.js, tests_js/source-constants.test.js,
tests/test_notification_neopixel_integration.py, tests/test_asy_ntp_client.py, tests/test_async_harness.py,
tests/test_asy_config_manager.py. LEAD NOTES 38, 55, 56 and 66 are the sources.
- LEAD NOTES 38: `tests/_cancel_sweep.py`'s lock check can never see a double release (the lock ends free either way).
  Lift E1's counting lock (`_BalanceLock` and `_assert_balanced` in tests/test_asy_base_classes.py) into the sweep's
  invariant so every sweep sees a refused release, a check strengthened. Seen failing first on E1's planted double
  release in `Lockable.__aexit__` (E1's hand-back `S/u35/handbacks/E1_final.md`). Then run every `tests/` file that
  imports `_cancel_sweep` on this branch at both stages; the lanes still running are covered by W6's gate.
- LEAD NOTES 66 (W3's hand-back `S/u35/handbacks/W3_final.md`): the put matrix's `NOT_DRIVEN` gains a stale-row check
  (a listed action the definitions no longer declare fails), seen failing on a planted stale row, run in a form that
  does not need the 12-minute matrix (the file's pure checks, or a scratch copy that runs only them); and
  tests_js/source-constants.test.js gains a `readStringSetConst` case, seen failing first. npm in
  `unshare -n S/u24/ns_xdg.sh`.
- LEAD NOTES 55: every test stand-in for an NTP sync (`_set_synced(value=True)`) in tests/test_notification_neopixel_
  integration.py and tests/test_asy_ntp_client.py is checked on this branch, which carries the clock-valid flag: one
  that stands for a real sync and reaches UTCTime or a VOC backup also sets the flag `_handle_ntp_sync_success()` sets
  (src/asy_ntp_client.py), seen red first where it matters; one that does not is named with why. Both files at both
  stages. (The twin integration file's stand-in is lane T's and waits for its merge.)
- LEAD NOTES 56 / P6: P6's `test_the_interrupt_runner_refuses_to_nest_inside_a_running_loop` tests the harness's
  `run_to_interrupt()`, so it moves from tests/test_asy_config_manager.py into tests/test_async_harness.py beside the
  harness's other refusal tests, unchanged; both files at both stages, and test_microtest.
- Runs: the 12 commit checks; every changed file's readers.
- Hand-back: each item by verdict; the runs; the branch head for the lead's merge.

## G2 (lane G: dev's twin cases on the driven clock, after V's merge)
Start: create branch `audit/u35-g2` at `3f2183c` (the integration head, lanes V and G merged) and its
worktree `S/wt-u35g2`, then `S/u23/rebuild.sh`. G1's hand-back `S/u35/handbacks/G1_final.md`, V4's `V4_final.md`;
LEAD NOTES 68. Files: tests/test_digital_twin_timer_pool.py, tests/test_digital_twin_hot_replug.py.
- G1 kept dev's cases on real time because digital_twin/machine.py:901 diffed against `_flash_stall.EPOCH_US`; V4's
  `094bc07` replaced that with one plain microsecond clock. Remove the `plan.get("uart")` guard in `_run_on_clock` (both
  files) if dev's readers, tick, bmp3xx, isl29125 and power-cycle cases pass on the driven clock at both stages, with G1's
  plants that apply to dev still biting there; else restate the guard's comment with the merged head's line-level
  reason. Either way the comments stop naming `EPOCH_US`.
- Runs: both files on dev at both stages, paired against the named head; the other five devices once each at -1.
- Hand-back: the verdict; the times; the branch head.

## V7 (lane V: step 114's remaining parts and the pin fake's fidelity; on the merged head)
Start: create branch `audit/u35-v7` at `3f2183c` (the integration head with lane V merged) and its worktree
`S/wt-u35v7`, then `S/u23/rebuild.sh`. V6's, V5's and V2's hand-backs; LEAD NOTES 34, 64 and 69. Files: lane V's
(lanes.py), which now include tests/machine.py and tests/test_fakes.py.
- The pin fake's two gaps against rp2 (V6, ports/rp2/machine_pin.c read only): tests/machine.py:150 `irq()` accepts an
  external pin, where rp2 raises ValueError("expecting a regular GPIO Pin") (:464-466); and `irq()` with no arguments
  clears the handler, where rp2 returns the IRQ object unchanged (:473). Fix both, each seen failing first in
  tests/test_fakes.py; then every test file that calls `Pin.irq` (grep) at both stages.
- Step 114's parts V6 could not write, beside their groups in tests/_sensortask_scenarios.py, each seen failing first on
  a planted defect from its own scratch tree: forty days' NTP resync count, ring saturation per logger, the ISL29125
  stored ticks (src/asy_isl29125_driver.py:431, :567) and the UART stored ticks (src/asy_uart_comm.py:381); the storm's
  module periodic paths (bus NAK, NTP no reply, webserver drops), recovery and the ladder rungs. One that cannot be
  written in-process is named with its line-level reason.
- Times: test_sensortask per device at both stages against `3f2183c`, alternating, the runner beside each tree.
- V's checks on the head: the 12 checks, the 17 scans, the readers of each changed file.
- Hand-back: each part by verdict; the times; the checks; the branch head.

## X1 (lane X: two cross-lane items on the merged head)
Start: create branch `audit/u35-x` at `2360470` (the integration head: every lane but L1 merged, the lead's edits) and
its worktree `S/wt-u35x`, then `S/u23/rebuild.sh`. LEAD NOTES 49, 55, 61 and 72. Files: src/asy_uart_link_driver.py,
tests/test_asy_uart_link_driver.py, tests/test_digital_twin_sensortask_integration.py.
- test_lock_order's 9 reds (V7): src/asy_uart_link_driver.py's `_read_raw()` (:164) and `_write_raw()` (:228) take
  `async with bus as device` on a parameter, which resolves to no row of SPECIFICATION.md C.8's lock table; every other
  driver takes its lock through its own attribute. Give both the attribute form the table names (the instance's UART,
  `self._uart`, which `_run_hazards()` already checks for None), with no behaviour change, so test_lock_order is green;
  the mpy-cross compare, the per-mode effect (dev only, STA and AP), and the link driver, twin link and webserver
  service tests at both stages.
- LEAD NOTES 55's twin half: tests/test_digital_twin_sensortask_integration.py's four NTP stand-ins
  (`_set_synced(value=True)` at :1083, :1165, :1224, :1293 on `2360470`): one that stands for a real sync and reaches
  UTCTime or a VOC backup also sets the clock-valid flag `_handle_ntp_sync_success()` sets (src/asy_ntp_client.py);
  one that does not is named with why. Seen red first where it matters; the file per device at both stages.
- Runs: the 12 checks, test_lock_order and test_task_inventory, the readers of the changed files.
- Hand-back: each item by verdict; the runs; the branch head.

## V8 (lane V: step 114's storm remainder and the dev sensors set; on the merged head)
Start: create branch `audit/u35-v8` at `2360470` and its worktree `S/wt-u35v8`, then `S/u23/rebuild.sh`. V7's hand-back
`S/u35/handbacks/V7_final.md`; LEAD NOTES 49, 69 and 72. Files: tests/_sensortask_scenarios.py, tests/test_sensortask.py.
- First, LEAD NOTES 49: `webserver_status_get_reflects_the_real_object_graph` (about :3125) fails on dev at both stages,
  since /status's `sensors` carries lane U's `UART_init` hazard report: the expected set gains the initiator's
  maintenance name where `_has_uart_link`, seen red first on dev.
- Step 114's storm parts V7 could not write, beside `fault_storm_keeps_every_module_within_its_persisted_log_rate`:
  the module periodic paths (a bus NAK, an NTP no-reply, a webserver drop), recovery, and the ladder rungs; each seen
  failing first on a planted defect from its own scratch tree. The NTP resync count stays out (V6's class-5 finding
  takes D.1's flag-first path).
- Times: test_sensortask per device at both stages against `2360470`, alternating, the runner beside each tree.
- V's checks on the head: the 12 checks, the 17 scans, the readers of each changed file.
- Hand-back: each part by verdict; the times; the checks; the branch head.

## V9 (lane V: the storm's NTP no-reply part and the paired times; V's last block)
Start: create branch `audit/u35-v9` at `0485607` (the integration head with V8 merged) and its worktree `S/wt-u35v9`,
then `S/u23/rebuild.sh`. V8's hand-back `S/u35/handbacks/V8_final.md`; LEAD NOTES 74. Files: tests/_sensortask_scenarios.py,
tests/test_sensortask.py.
- The storm's NTP no-reply part, beside V8's two storm scenarios: the NTP client's request gets no reply (an in-process
  UDP no-reply seam, the way the scenarios already stand in for the network), and the scenario asserts the logged code,
  the persisted-entry bound and recovery once replies return. Seen failing first on a planted defect from its own
  scratch tree. The resync count stays out (V6's flag-first finding).
- The paired times V8 could not run: test_sensortask per device at both stages, `2360470`'s scenarios file (V8's
  `S/u35/laneV/v8/vbase`) against this head, alternating, `_threshold_runner` beside each tree (V8's
  `S/u35/laneV/v8/r.sh` and `run.sh`); each new scenario's added time stated. Every file is over 10 s, so its growth is
  the new checks only, stated per scenario.
- V's checks on the head: the 12 checks, the 17 scans, the readers of the changed files.
- Hand-back: the part's verdict; the times; the checks; the branch head.

## V10 (lane V: test_sensortask's growth made efficient; after the toolchain setup)
Start: create branch `audit/u35-v10` at the integration head the lead names and its worktree `S/wt-u35v10`, then
`S/u23/rebuild.sh`. V9's hand-back `S/u35/handbacks/V9_final.md`; LEAD NOTES 4, 74 and 77. Files: tests/_sensortask_scenarios.py,
tests/test_sensortask.py. The owner (2026-10-08): "Test duration going up like this is anyhow something to fix - not
cutting back strictness, but making it more efficient".
- V9's paired times against `2360470`'s scenarios file (`S/u35/laneV/v8/vbase`) grew over 10 % on dev at 32768
  (72.97 -> 80.98 s, the repeat 68.28 -> 76.29 s) and on wozi at both stages (+10.0 %, +10.4 %). Root-cause both:
  - on dev the NAK storm's storm phase alone takes about 3.2 s (7 passes x 4 readers, SCD30's soft reset in the failure
    path): where that time goes, by measurement, real waits or work;
  - dev at 32768 grows about 8 s while its new scenarios sum to about 5.2 s: the other 2.8 s, by measurement.
  Make each cost efficient (a driven clock or event wait in place of a real wait, less repeated set-up), every assertion
  and pass kept; each change seen to keep the scenario's plants biting (V8's p2 at its line, V9's b1-b4). A cost that is
  real and irreducible is named with its line-level reason.
- The file's one over-cap block at the 120-character count (block K, `S/u35/briefs/blocks_k.md`): about
  tests/_sensortask_scenarios.py:477, "For the with block: each wait that ran its full time". Keep its line count.
- Times: test_sensortask per device at both stages, `vbase` against your head, alternating, `_threshold_runner` beside
  each tree (V8's `S/u35/laneV/v8/r.sh`, `run.sh`); every device at or under +10 % at both stages, or its reason stated.
- V's checks on the head: the 12 checks, the 17 scans, the readers of the changed files.
- Hand-back: each cost by verdict with its measurement; the times; the checks; the branch head.
