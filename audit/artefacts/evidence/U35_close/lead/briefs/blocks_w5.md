# U35 wave 5 blocks: lanes Y, V and G (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here. About 60-80 tool calls each: count
them, and at 70 finish the step in hand, commit, and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.
LEAD NOTES 20 is the cut: lane V branches from Y3's head `949a68a` (S/wt-u35v), lane G from C2b's head `0547def`
(S/wt-u35g); both are rebuilt. The driven clock's cancel hang (`S/u35/briefs/blocks_w4.md`, first section) holds until
`<SHIMFIX>`: let tasks start before a cancel under `DrivenTime(sleeps=True)`, and name each such site. A lane's last
block runs its complete checks.

## Y4 (lane Y: `_sensortask_scenarios`' `Any`, then its handover)
Start: audit/u35-y at `949a68a` in S/wt-u35y; Y3's hand-back `S/u35/handbacks/Y3_final.md`. Files:
tests/_sensortask_scenarios.py, tests/test_sensortask.py, and Y's config files for the baseline lines.
- R-15 for `_sensortask_scenarios` (77 sites in `S/u34/handbacks/T1_final.md`): it leaves in one commit with its
  baseline line, its ANN401 entry and its `_RESIDUAL` row, or stays listed with its sites and why (U34 R-2's form).
  Typing only. Y3's facts hold: `Unpack[TypedDict]` checks under the main pass, and MicroPython rejects `{**kwargs}` in
  a dict display. `scripts/typecheck.sh` after the commit.
- Times (LEAD NOTES 4's annotation rule): test_sensortask per device at the head at both stages against U32's figures
  (arzi 36.89/33.50, dev 46.32/53.94, grkizi 28.91/32.62, klkizi 28.40/33.11, schlafzi 28.94/33.24, wozi 32.31/37.63); a
  paired run only where one is off by more than 10 %. Run the six devices under the 4-process cap.
- Then relay `<HANDOVER-SCEN> <hash>` under `## Y`: both files pass to lane V, and Y never edits them again.
- Hand-back: the verdict and sites; the baseline now per pass; Y5's start state.

## Y5 (lane Y: the two UART files' `Any`, `asy_system_service`, Y's checks)
Start: audit/u35-y at the lead's merge of P2a's `<TASKNONE>` `a77baac` onto Y4's `5ef18d4` (the lead states the hash in
your prompt); Y4's hand-back `S/u35/handbacks/Y4_final.md`. Files: tests/test_asy_uart_comm.py, tests/test_asy_uart_driver.py, src/asy_system_service.py and
Y's config files.
- R-15 for `test_asy_uart_comm` (26 lines) and `test_asy_uart_driver` (23), sites by `grep -n '\bAny\b'` (Y3), each
  in one commit as above. pyproject.toml's ANN401 reason (:267-269, "Unpack[TypedDict] is unavailable") is stale for
  mypy (Y3's probe); restate it for what stays, or remove it with its last entry.
- LEAD NOTES 25: two blank lines around `test_cancelling_at_each_await_leaves_no_lock_or_busy_flag`
  (tests/test_asy_uart_comm.py:3116, :3172).
- LEAD NOTES 30's residual: if digital_twin/machine.py:937 alone can pass an unbounded time to the flash-stall check,
  fix it there, seen failing first in tests/test_digital_twin_machine.py on a window exactly 2**30 us old; if the fix
  needs digital_twin/_flash_stall.py (V's) too, hand it back for the lead.
- LEAD NOTES 15: type src/asy_system_service.py with the TaskStarter alias Y1 tested and clear the module from the
  baseline (Y1's hand-back has the twin-pass and main-pass checks). The mpy-cross compare is byte-identical (LEAD NOTES 7).
- Times: the two files at the head at both stages against U32's (uart_comm 61.39/62.22) and U1's figures.
- Y's complete checks (typecheck.sh, lint.sh, the 17 scans, every reader of a Y file).
- Hand-back: each module's verdict; the baseline per pass; anything left listed and why.

## V1 (lane V: the flash stall's wrap, the twin bus hazard's real-time waits, two D.15 orders)
Start: audit/u35-v at `949a68a` in S/wt-u35v. Files: digital_twin/_flash_stall.py, tests/test_ticks_rollover.py,
tests/test_digital_twin_bus_hazard_concurrency.py, tests/_bus_hazard_catalog.py, tests/test_bus_hazard_multi_device.py.
- Y3's finding (class 5, twin only): digital_twin/_flash_stall.py:98 stores stall windows as `ticks_diff()` from
  EPOCH_US, so on a 2**30 build a window straddling the 2**29 us wrap reads as empty. Seen failing first on
  tests/_ticks30.py's clock (Y3's method; your test file is tests/test_ticks_rollover.py), then fixed the way Y3 fixed
  the UART link (`949a68a`). The 2**30 build's confirmation is B1's `<T30>`, not yours.
- CG's efficiency item (LEAD NOTES 20): the twin bus hazard file holds a slot for 160 s wall at 24 CPU-s under settrace
  (150 s plain). List each real-time wait (16 sleep sites) with what it waits for. Move each one that no assertion
  measures to a driven or event-gated form, every assertion kept. A wait whose real time is the scenario's subject
  stays, with a one-line reason in the hand-back. Each moved wait is seen failing on a planted defect (a missing
  release, a skipped step). If the twin's clock cannot be driven here, state why at line level and stop that item.
- D.15's module-level order for the catalog and multi_device (LEAD NOTES 18): one commit, no content change, checked by
  line multiset.
- Runs: paired base/head at both stages: twin bus hazard (U32 150.15/152.79), the rollover file, multi_device (U30
  3.3/3.6); the catalog's other importers at both stages on the head.
- Hand-back: steps by verdict; the wait table; V2's start state.

## V2 (lane V: step 114 and the stale clock's scenario assertions)
Start: audit/u35-v at `97a034c` in S/wt-u35v (rebuilt): V1's `fb9c0e1` plus the lead's merges of Y4's `<HANDOVER-SCEN>`
`5ef18d4` and lane C's `7442273` (`<CLOCK>` and `<SHIMFIX>`). V1's and Y4's hand-backs in `S/u35/handbacks/`. Files:
tests/_sensortask_scenarios.py, tests/test_sensortask.py. Y4's deep-read form is `_strict(body, "a")["b"]`.
- 114 (P1's row in lane_plan.md :302): the four scenario groups (fault storm, forty days by `jump`, a dropped
  one-second tick, the stuck task that stops every feed, with the persisted log), each bitten by a planted defect (the
  WDT fed despite a stuck task; a FRAM write storm over its bound).
- First, C4's red (LEAD NOTES 23): :2726 patches `ntp_issynced` to show `UTCTime`; on `<CLOCK>` it patches
  `ntp_clock_valid`, so `webserver_status_publishes_utc_time_only_after_the_first_ntp_sync` is green again on all six.
- LEAD NOTES 11's per-device assertions after `<CLOCK>`: in the stale window `UTCTime` is shown, `TimeStale` is true and
  a backup is stamped; after a settings change `UTCTime` is null and `TimeStale` true. Seen failing first against the
  head before the merge.
- Runs: test_sensortask per device at both stages, base and head paired (the figures in Y4); over 10 s, so each must not
  grow beyond what the new groups add, stated per group.
- Hand-back: steps by verdict; each group's added time; V3's start state.

## V3 (lane V: the scenarios' order, OF-200 with the new groups' time, the recombination retry)
Start: audit/u35-v at `58b0713` in S/wt-u35v (rebuilt): V2's `83c9475` plus the lead's merge of Y's final `5cf361c`
(LEAD NOTES 40), which also carries P2a's finished commits; V2's hand-back
`S/u35/handbacks/V2_final.md`; LEAD NOTES 26, 30 and 34. Files: V's (lanes.py).
- LEAD NOTES 26: D.15's module-level order for tests/_sensortask_scenarios.py, its own commit, no content change (line
  multiset), the scenario registration order kept.
- OF-200 (R-31): profile test_sensortask for one device at 32768 first, then make it efficient where the profile points,
  never by cutting strictness; any fix lands only in a U35 file. The profile names V2's groups' share; forty days
  (4.9-5.4 s) and dropped tick (2.1-2.3 s) drive the clock, so make them efficient where no assertion measures the
  time (LEAD NOTES 34), each assertion kept and each bite still biting.
- LEAD NOTES 30: the recombination test (tests/test_digital_twin_bus_hazard_concurrency.py, V1's flap test) forces one
  failed reconnect so the real 60 s ESTABLISHED-branch retry runs while the bus load is in flight; it asserts the bus
  work proceeds through the retry and the link returns after it; seen failing first on a planted retry that holds
  `wifi_mode_lock` or never ends. Restate its comment with the change named; the owner's paraphrase keeps its actor
  and date. State its added time as the scenario's subject.
- Paired runs (copy `_threshold_runner` beside each tree, LEAD NOTES 34): test_sensortask per device at both stages
  against `58b0713`, and the twin bus hazard file against `97a034c`.
- Hand-back: the profile, the fixes and their times; the recombination test; V4's start state.

## V4 (lane V: the flash stall's residual and the recombination retry's real minute)
Start: audit/u35-v at `e305fcd` in S/wt-u35v (rebuilt at `58b0713`; V3 changed no src/); V3's hand-back
`S/u35/handbacks/V3_final.md`, Y5's `Y5_final.md`; LEAD NOTES 40 and 47. Files: V's (lanes.py).
- LEAD NOTES 40, the flash stall's residual (twin only): digital_twin/machine.py and tests/test_digital_twin_machine.py
  are V's now. Store the stall windows in unbounded microseconds with a plain comparison in digital_twin/_flash_stall.py,
  and have digital_twin/machine.py:937 (`_stall_offset_us`, at `5cf361c`) pass unbounded time. Seen failing first in
  tests/test_digital_twin_machine.py or tests/test_ticks_rollover.py on a window recorded after 2**29 us and on a time
  one full period after a window (Y5's two aliasing cases), on tests/_ticks30.py's clock. Rebuild after the change.
- LEAD NOTES 47, the recombination test's real 60 s retry (85 → 147 s for the file): the retry's minute is waiting, not
  work. If the WiFi service's retry sleep can be driven alone (`DrivenTime(asy_wifi_service, ...)` while the bus load
  runs on real time), hold the retry open while the bus load runs a stated number of real cycles, assert the bus work
  proceeds and `wifi_mode_lock` stays free during it, then advance exactly the retry and assert the link returns; the
  retry's length is then asserted from the driven clock, exactly. Every assertion V3 wrote is kept and each of its four
  bites still bites. If the clocks cannot be split there, state why at line level, keep the real retry, and derive the
  75 s `l2.bus_hazard_concurrency_flap_window_s` bound from its parts (the retry, the twin's connect delay, the poll
  step) with the margin measured under the 4-process load; relay the row's basis to D.
- Runs: the twin bus hazard file paired against `e305fcd` at both stages; the stall files and test_ticks_rollover at
  both stages; the other importers of digital_twin/machine.py (grep) at both stages on the head.
- Hand-back: steps by verdict; the times; V5's start state.

## V5 (lane V: P4's write-then-rename in V's files, step 114's remaining parts, V's checks; V's last block)
Start: audit/u35-v at `c805172` in S/wt-u35v (rebuilt): V4's `a11603a`, the lead's fix to
tests/test_digital_twin_clock_jump.py (`a102ada`, LEAD NOTES 55) and the lead's merge of P4's `65f7454`; V4's and P4's
hand-backs; LEAD NOTES 46, 52 and 55. Files: V's. Run the twin mypy pass early (V4 removed its typings link): the
lead's a102ada was not type-checked.
- P4 writes a config file as `<file>.tmp`, then `os.rename()` over it, and slices the bytes through a `memoryview` in
  "wb" mode. Two reds follow in V's files, each seen red on the merged head first:
  - digital_twin/_flash_stall.py:68 takes `len(data.encode())`, which raises AttributeError on a memoryview (the twin
    CI installs it, digital_twin/run_generic_integration.py:908): a buffer's length is `len(data)`; the twin CI then
    passes for dev and arzi at both stages;
  - tests/_sensortask_scenarios.py:939's `_DirWrites` records the `.tmp` names: a write of `<x>.tmp` renamed onto `<x>`
    counts as a write of `<x>`; test_sensortask is green on all six at both stages.
- tests/test_bus_hazard_multi_device.py:1095 is green again on P4's head (the rename is atomic on posix too): confirm it
  on the merged head at both stages; P4's tests/_littlefs_fake.py is used there only if a look can still see a torn
  document.
- V2's narrower parts (LEAD NOTES 34), each where it fits V's files, seen failing first on a planted defect: the stuck
  task's escaping exception, cancelled `main()` and the blocked loop's structural half; forty days' WiFi uptime, NTP
  age and resync count, ring saturation per logger, the ISL29125 and UART stored ticks; the storm's module periodic
  paths, scan budget, recovery and ladder rungs. A part that needs another lane's file (Pin IRQs need a pin registry in
  tests/machine.py, Y's) is listed with its file and line for the lead. Each part's added time, test_sensortask per
  device at both stages against V4's head.
- V's complete checks: the 17 scans and every reader of a V file. C5's d15 checker counts `@_register` scenarios as
  sortable; their order is registration order (V3), so that one line is not a slip.
- Hand-back: each part by verdict; the times; the checks.

## V6 (lane V: step 114's last parts; V's last block)
Start: audit/u35-v at `8edb5aa` in S/wt-u35v (rebuilt at `c805172`; V5 changed no src/); V5's and V2's hand-backs;
LEAD NOTES 34 and 64. Files: V's, which now include tests/machine.py (lanes.py; the lead edits its :598 at W6 after
this block, LEAD NOTES 21, so leave that site as it is).
- Pin IRQs: tests/machine.py keeps no pin registry (:49); give it one, the smallest that lets a scenario fire a wired
  pin's IRQ through the real handler, and write the stuck-task group's pin-IRQ case (no IRQ feeds the watchdog once the
  reboot is armed), seen failing first on a planted feeding IRQ.
- Forty days' remaining invariants beside `forty_days_of_uptime_keep_every_invariant`: WiFi uptime, NTP age and resync
  count, ring saturation per logger, the ISL29125 and UART stored ticks.
- The storm's remaining parts beside `fault_storm_keeps_every_module_within_its_persisted_log_rate`: the module periodic
  paths (bus NAK, NTP no reply, webserver drops), the scan budget, recovery and the ladder rungs. The L2 half is the twin
  suite's (lane T, Run 3): state whether T's Run 3 already carries it, and list it for the lead if not.
- Each part seen failing first on a planted defect run from its own scratch tree; each part's added time; test_sensortask
  per device at both stages against `8edb5aa`, alternating, the runner copied beside each tree.
- V's checks again on the head: the 12 checks, the 17 scans, the readers of every V file changed in this block.
- Hand-back: each part by verdict; the times; the checks.

## G1 (lane G: two slow twin files' real-time waits; G's only block)
Start: audit/u35-g at `1d77560` (`<SHIMFIX>`) in S/wt-u35g. Files: tests/test_digital_twin_timer_pool.py,
tests/test_digital_twin_hot_replug.py.
- CG's item (LEAD NOTES 20): timer pool 36 s wall at 2.3 CPU-s per device under settrace, hot replug 72 s at 5. List
  each real-time wait with what it waits for; move each that no assertion measures to a driven or event-gated form,
  every assertion kept; a wait whose real time is the scenario's subject stays, with a one-line reason. Each moved wait
  is seen failing on a planted defect. If the twin's clock cannot be driven here, state why at line level.
- Runs: paired base/head at both stages: timer pool per device (TEST_DEVICE, all six, under the 4-process cap) and hot
  replug. Readers of your files.
- G's complete checks.
- Hand-back: the wait table; the times; the checks.
