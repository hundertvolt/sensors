# U35 wave 2 blocks (lead, 2026-10-21)

Each block reads `S/u35/briefs/common_u35.md` first, then its own section here. About 60-80 tool calls each; at the
valve (CHECKLIST 21), stop at a seam, commit, and hand back what is left. Three W1 blocks ran 9, 23 and 36 calls
past it: count your calls, and at 70 finish the step in hand and hand back the rest.

## Y2 (lane Y: the bus-hazard catalog and the multi-device file)
Start: branch audit/u35-y at `6a59b8e` in S/wt-u35y, and Y1's hand-back `S/u35/handbacks/Y1_final.md` (its .venv and
typings/ copies stay until the lane's end).
Files this block: tests/_bus_hazard_catalog.py, tests/test_bus_hazard_multi_device.py, tests/test_bus_hazard_generated.py,
and Y's config files for the baseline lines (pyproject.toml, digital_twin/typecheck.ini, host_typecheck.ini,
tests_scripts/test_mypy_any_baseline.py).

**Steps 28, 29, 73, 74, 6, 76, 77, in that order.** P1a's rows 6, 28, 29 and P1b's rows 73, 74, 76, 77 hold the sites.
- 28: `releases_bus_mid_read` (True for sgp40) and `default_address` on `I2CHazardAdapter`.
- 29: `sibling_inside_window()`; the `switches >= len(occupants)` floor applies only to a bus with no flagged occupant.
- 73: `switches >= 2` (two sites) becomes `sibling_inside_window`. Seen failing: a switch planted outside the window
  is named.
- 74 and 6's left part (the same test): delete the `entry[1] != _BMP_ADDR` assert with its comment and the
  general-call mock test. Its silicon run is parked (hardware session 1); the device script stays.
- 76: the bus-fault test gets `wait_for(..., _ISOLATION_BOUND_S)` and `bus_lock` asserts. Seen failing on a planted
  `bus_lock` leak. It adds the tag `l1.bus_fault_isolation_bound_s = 5`; its Part N row is D's `5f97080`, not in your
  tree, so test_tunables_register.py is red on exactly that one named row (R-17): prove it is the only red. The
  reserved-address test loops the adapters' `default_address`, not the hand-kept list.
- 77: the two SPI tests still in SPIDevice/sync-worker form move to the shared `FRAM_SPI` form, each seen failing on a
  planted defect first.

**R-15 for three modules:** `_bus_hazard_catalog`, `test_bus_hazard_multi_device`, `test_bus_hazard_generated`.
- Each leaves in one commit with its baseline line, its ANN401 entry (if any) and its `_RESIDUAL` row; the catalog's
  commit also takes Y1's ready diff `S/u35/laneY/bhg_typed.diff` and retypes `build_bus_occupants` and
  `scenario_each_occupant_never_touches_an_unexpected_address`, which leaves bus_hazard_generated's three arg-type
  errors at zero.
- A module whose `Any` cannot go without a cast or an ignore stays listed with its sites.
- `scripts/typecheck.sh` after every module commit.

**Not this block:** OF-32 is Y3's first part; `asy_system_service` waits on P2's six `Task[None]` annotations in
tests/test_asy_system_service.py (Y1's hand-back), then leaves in a later Y block.

**Runs.**
- Paired base/head at both stages: test_bus_hazard_generated.py (U30 63.6/64.3) and test_bus_hazard_multi_device.py
  (U30 3.3/3.6). Each is wall-time-bound: CHECKLIST 12 (the lead's gate shares the host until about 17:20 UTC).
- Readers: every `tests_scripts` file that reads a file you changed (grep the names), tunables_register as above,
  mypy_any_baseline, ruff_exemptions_live; ruff on your files.

**Hand-back.** Steps by verdict with commits; the seen-failing cases; the baseline now per pass; the state Y3 starts from.

## Branch points for lanes N and U (lead, 2026-10-21)
N and U need C1's helpers, so their branches start at C1's final head `feae592` (f3fff0e plus C1's commits, all in
C's files), not at f3fff0e: no merge, and at W6 those commits are common ancestry. Their worktrees are set up with
`S/u23/rebuild.sh` like every lane's. Paired base times still run against S/wt-u35base (f3fff0e). C's helper API is in
the relay's `## C` lines and C1's hand-back `S/u35/handbacks/C1_final.md`.

## C2a (lane C: dns and ntp; OF-211)
Start: branch audit/u35-c at `feae592` in S/wt-u35c and C1's hand-back (its "Facts owed" bind you: a sweep's `turn` is
shorter than the path's shortest driven sleep). Files this block: tests/test_asy_dns_client.py, tests/test_asy_ntp_client.py.
C1 checked 50 and 54; not redone.
- 40: `test_cancelling_a_resolve_at_each_await_leaves_no_socket_open`, over <SWEEP>.
- 55: `test_the_sync_task_survives_a_cancel_at_every_await`, over <SWEEP>.
- 56: the four `await asyncio.wait_for(..., 5)` sites become `assert await server.serve_once(reply) is True`.
- Each sweep is seen failing on a planted leaked socket or unbalanced lock.
- OF-211 (R-28): try a deterministic guard that tells a test relying on 127.0.0.1:123/:53 being closed from one that
  redirects to its port band. If none can be made deterministic, rerun U27's held-responder audit over every file that
  touches a socket and state the result; relay D2's E.1 rule as one line under `## D`.
- Runs: paired base/head at both stages for the two files (ntp 23.9/25.6 is over 10 s, so it must not grow: LEAD NOTES
  4); readers per the common brief.
- Hand-back: steps by verdict, the OF-211 outcome, C2b's start state.

## C2b (lane C: udp and webserver connections; OF-211's audit)
Start: C2a's head `b6ef8d3` and hand-back `S/u35/handbacks/C2a_final.md`. Files: tests/test_asy_udp_socket.py,
tests/test_asy_webserver_connections.py, and for the first item tests/_fake_time.py and tests/test_asy_dns_client.py. C1
checked 63; not redone.
- First: C2a's last two-line fix came after its pre-commit run, so re-run the 12 pre-commit checks and dns/ntp on the head
  at both stages (one line each).
- C2a's fact: `DrivenTime.__enter__` reads `module.time` unconditionally; make it tolerate a module without `time` (seen
  failing first in test_driven_time.py), then drop test_asy_dns_client.py's `_LentTime` workaround. Every importer of
  `_fake_time` runs at both stages on the head (C1's list of 19).
- 64: the join test's real `asyncio.sleep(_FIRST_ATTEMPT_S)` moves to driven time (`run_until`, then `advance(500)`).
- 65: a new sweep in test_asy_udp_socket.py.
- 66 and R-2: test_asy_webserver_connections.py's file-local `_DrivenClock` (virtual seconds) goes for <CORE>'s
  `DrivenTime(sleeps=True)` (ms).
- 67 (R-19): the sweep over `_serve()` in test_asy_webserver_connections.py.
- Each sweep is seen failing on a planted leaked socket or unbalanced lock; each driven-time move on a planted bound.
- Runs: paired base/head at both stages (udp 7.2/7.2, webserver_connections 1.2/1.3); readers per the common brief.
- OF-211's fallback (C2a found no deterministic guard possible in lane C's files): re-run U27's held-responder audit
  (`S/u27/ci/repro/audit.sh`, extended to every `tests/` file that opens a socket, both stages) on your head, state
  the result, and relay D2's E.1 rule as one line under `## D`. If the valve comes first, hand the audit to C3.
- Hand-back: steps by verdict, the audit's result, C3's start state.

## U1 (lane U: the UART comm and driver sweeps, then the handover)
Start: new branch audit/u35-u at `feae592`, worktree S/wt-u35u. Files this block: tests/test_asy_uart_comm.py and
tests/test_asy_uart_driver.py, which pass to Y at your end (R-16). UART: test only; no emitted byte, accept/reject rule or
recovery timing changes (R-18); a defect a sweep finds goes in your hand-back for P's changelog.
- 59: the sweep test in test_asy_uart_comm.py, over <SWEEP>.
- 60: test_asy_uart_driver.py's `await asyncio.sleep_ms(400)` (the cancel-ack test) becomes an un-set Event, cancelled
  in `finally`, plus one comment line.
- 61: a new sweep in test_asy_uart_driver.py.
- Seen failing: each sweep on a planted missing cleanup; 60's Event on a planted leak.
- Time: test_asy_uart_comm.py is 61.39/62.22 at U32, over 10 s, so it must not grow (LEAD NOTES 4): make the sweep
  efficient, never less strict. uart_driver (U30 5.94/9.80) paired base/head. test_uart_comm_cancel_sweep.py (U32
  40.17/40.10) is a reader: run it on the head at both stages.
- Readers: import_placement, mypy_any_baseline, suppression_form, uart_changelog, and grep's.
- Last: relay `<HANDOVER-UART> <hash>` under `## U` (your final commit). U never edits those two files again.
- Hand-back: steps by verdict; U2's start state (U2 holds link_driver, the twin uart_link, the hazard plant).

## N1 (lane N: the neopixel driver's driven time)
Start: new branch audit/u35-n at `feae592`, worktree S/wt-u35n. File this block: tests/test_asy_neopixel_driver.py. It
moved at f3fff0e (U32's gate fix): re-locate every site by its text (LEAD NOTES 1).
- 43 and R-2: the local `_YieldOnlyAsyncio` and `_DrivenClock` go for <CORE>'s `DrivenTime`.
- 44: the real `sleep(1.5)` and `sleep(1.1)` move to `advance`; `>= 30` becomes `== 31`.
- 53: the 15 real sleeps P1b's row 53 lists move to driven time; the comment on the bound reads "a limit"; use
  `cancel_all` where the packet says `cancel(*tasks)`. The row's two conflicts stand as the tree has them: `debug=4`
  stays, and the product attribute is `neopixel_freq`.
- Seen failing: every converted assertion bitten by a planted driver at both stages (FX8's method: no restore, the lock
  ignored, t truncated); 44's `== 31` on a planted off-by-one.
- OF-233 (R-13) is lane N's: the steps above are its first part; say what N2 and N3 still owe it.
- Runs: paired base/head at both stages (U32 9.56/9.55; FX8's after-times 7.25/7.29). Readers: import_placement,
  ticks_wrap_scan, tunables_register.
- Hand-back: steps by verdict; N2's start state (N2: the notification service, 45-49, and <PARTN>'s row).

## T2a (lane T: T1's reds and carries, Run 1's baseline, the normal-boot cases)
Start: branch audit/u35-t at `dac9046` in S/wt-u35t and T1's hand-back `S/u35/handbacks/T1_final.md` (its "Red checks"
and "Owed to T2" parts are this block's first work). Files this block: scripts/_digital_twin_ci_suite.py,
tests_scripts/test_digital_twin_ci_suite_errcount.py, and two files the lead added to lane T for T1's reds (lead,
2026-10-21): tests/test_digital_twin_run_generic_integration.py, tests_scripts/test_digital_twin_scenarios.py.
- First commit: T1's two reds, each fixed as its hand-back says and seen green (the twin mypy pass's two call-arg
  errors included).
- T1's carries: the suite's `_shutdown()`/`_check_exit` fail on `run.stop_ignored` (seen failing on a planted ignored
  stop file); Run 12's SIGINT relaunch passes `interrupt=True`, so it keeps its meaning.
- 166: the normal-boot cases in the errcount file (one W entry fails; an NTP entry fails). T1 wrote the `fram_writes*`
  parser cases; not redone. R-4: no E and no W entry, read before `l2.scenario_shared_boot_deadline_s`; the NTPSynced
  case targets `_wait_for_ntp_sync`.
- 118: Run 1's baseline before the ResetErrors call: one `GET /status`/`/system` read kept as `run1_errcount.json`;
  every module's history holds no E and no W entry; fold (1), the reformat relaunch logs exactly one W `CONFIG_LOST`,
  kept as `run1_reformat_errcount.json`; files under `ctx.logs_dir/"runs"`. Seen failing: a planted W fails Run 1. No
  Run-1 NTPSynced poll: Run 1 has no station link (P1c's row 118, agent, 2026-10-21).
- Runs: the suite's changed runs for dev at both stages (`scripts/run_digital_twin_ci.sh dev --part suite --only 1,12,...`; run names as RUN_NAMES spells them), base and
  head; the T readers (P2.2) that read your files, paired. T4 runs the whole suite for dev and arzi.
- Hand-back: steps by verdict; T2b's start state.

## T2b (lane T: the soak window, the soak fixture, Run 3's FRAM write rate)
Start: T2a's head and hand-back. Files: scripts/_digital_twin_ci_suite.py, digital_twin/run_generic_integration.py,
tests_scripts/test_digital_twin_ci_suite_soak.py; scripts/_check_gc_collect_sites.py is read, not edited.
- 157 (1): the soak window moves from wall-clock timestamps to log byte offsets (the parser no longer returns
  `(float, int)`). 157 (2): the runner's `MEM_SAMPLE` stamp uses `ticks_ms`. 157 (3) is not yours: the sampler keeps
  its `gc.collect()`, comment and checker row until B2's run decides (R-22); 157 (4) is T4's.
- 164: offset cases and a backwards-clock fixture in the soak file, seen failing first.
- 160: Run 3 asserts the FRAM write-count rate from the shutdown line's fields. Its bound is window / 627 ms x 2, stated
  beside the assertion (R-24, P1d). Seen failing on a planted excess write rate. Relay its `audit/b3/load.md` entry as
  one line under `## B` (B holds audit/b3/).
- Runs: Runs 3 and 11 for dev at both stages, base and head (`--part suite --only 3,11`); the soak file and the T readers that read your
  files, paired.
- Hand-back: steps by verdict; T3's start state.
