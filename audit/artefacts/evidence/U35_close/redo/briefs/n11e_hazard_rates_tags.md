# N11e: the hazard tests at the device's rates, the run limit measured, the last wait tags (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back), then N11d's hand-back `S/u35r/handbacks_redo/N11d.md` (all of it: item 0's table and the two
options, item 2's classes and its list of sites left to tag, the open thread) and its tools in `S/u35/laneC/n11d/`
(`tm.sh`, `runset.sh`, `tools/waits3.py`, `tools/classify3.py`, `item2/rules.tsv`, `item2/classes_now.tsv`).
Worktree and base: in your launch message. Logs in `S/u35/laneC/n11e/`.

## The lead's review of N11d (binding)
- N11d's three commits are merged into int. In the merge, the captive-DNS burst's real-sleep tag
  (`l2.sensortask_integration_burst_poll_ms`) and its row were dropped, because lane CMr1j had already put that
  burst on the driven clock (`clock.elapse(1)`). The `_WAIT_TIMEOUT_MS` dependants cell now says "one driven ms per
  look". A site on the driven clock is V and gets no tag.
- Item 0 decision (agent, 2026-10-27), option (A): the L1 hazard tests' own `Pair` runs at the bench device's
  configured rates (devices/dev.toml: `poll_wait_ms` 2, `poll_idle_ms` 50), which the twin's hazard test already
  uses.
  - Why: the verdicts are unchanged and the CPU is about 3x lower, so the duration is fixed by efficiency, as the
    owner rules. The test then runs the configuration the firmware ships, where today it runs a 1/1 rate that no
    device uses. Option (B), a larger bound, would leave the cost where it is.
  - The bound `l1.uart_comm_harness_run_limit_s` (10 s) stays.
- Sites in files another lane is changing are not yours:
  - test_digital_twin_ntp.py and test_digital_twin_clock_jump.py belong to lane CMr1k (its item 6).
  - The UART lane (UM4) owns test_digital_twin_uart_link.py and test_digital_twin_generated_boot.py, plus every
    twin UART test it moves onto the driven clock. Check whether UM4's merge is in your base (`git log --oneline
    --grep 'merge lane.*UM'`). If it is, class the UART sites on your base. If it is not, leave twin machine_uart's
    :52/:53 and test_ticks_rollover's :457 `poll_wait_ms=1`, and list them as held for the UART lane.

## Items, in order (each committed green on its own, a formal pair where a time changed)
1. Option (A).
   - The hazard tests' `Pair` takes the two rates from devices/dev.toml through the repo's existing route for
     reading a device value in a test (no new literal: test_no_variant_literals stays green).
   - Re-measure `l1.asy_uart_link_driver_hazard_run_virtual_ms` exactly. Virtual time is exact, so its row states
     both CRC modes.
   - Bite: a planted hazard fault (a frame the receiver must refuse, or an ACK withheld) still fails the test at
     the new rates.
   - Then measure every `RUN_LIMIT_S` call, quiet and under the gate's load (N11d's `LOAD=4`), at both stages, and
     write `l1.uart_comm_harness_run_limit_s`'s row as measured from that basis.
   - If the slowest loaded call comes within half the bound, stop and put it to the lead with the numbers before
     any value change.
   - Formal pair for the file.
2. Item 2's remainder: every R and B site in N11d's "Left to tag" list that is still real-time on your base, tagged
   with a measured row at both stages, the way batch 1 was.
   - These include test_asy_system_service's `_real_time` literals, `_HANG_WATCH_MS` and `_SETTLE_MS`; rgi's
     `_WIRE_LOG_CLEAR_INTERVAL_MS` (:445) and `range(3)` (:702); and the twin bus_hazard's :104 and :393.
   - Lane CMr1k also edits digital_twin/run_generic_integration.py, at other sites, so touch only your two lines
     there.
   - Where a site could leave the real clock by efficiency at no loss of strictness, do that instead of tagging,
     with its bite. Say which you chose and why.
   - AST identical after substitution, and the register bite red, per commit.
3. Item 3's two sites outside CMr1k's files (test_digital_twin_bus_hazard_concurrency.py :99 `_POLL_S`,
   test_digital_twin_loop_end.py :69 `_POLL_MS`) the same way.
4. The open thread: test_digital_twin_sensortask_integration.py `_STREAK_JOIN_S` / `_STREAK_STEP_MS` (:132-133 at
   173b88ea).
   - Read them and class them.
   - If they are real waits, tag them as above.
   - If v3 missed them, fix `tools/waits3.py` (a plant of that shape found, the tagged control 0), so the
     scanner's last count on your head reports no real untagged wait. List anything it still cannot see.
5. Checks: every changed file at both stages (PER_DEVICE files on all six devices), zero memory markers; on the final
   head the whole tests_scripts tier; lint_direct, the six mypy passes, the three audit checks; review rows if a
   test's text changed.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; item 1's rates, virtual tag, bite and the RUN_LIMIT_S table (quiet and loaded, both stages); per site its
class, tag and row (or the efficiency change that removed the wait); held sites with their owner; the scanner's
final count; the checks; last line "nothing of mine is running".
