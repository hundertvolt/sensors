U35 lane M, block M: hand-back. Nothing committed, by decision: both parts stopped and left as they were (agent, 2026-10-22).
Branch audit/u35-m stays at 6dabd9b. Worktree S/wt-u35m is clean, nothing uncommitted, nothing of mine running.

**M.1, the gate's lock and tentative claim: STOPPED.**
- The only await is `erase_ready()`. The lock-free form (preflight first, then check and claim with no await between) passed every existing test.
- It still changes the gate's designed behaviour whenever the preflight suspends. Design rule 3 (audit/actions/SUPP_owner_0930.md:46-60) says the claim "is set before any await, so from here another purpose's command and `pause_permanent_storage()` answer False", and the lock makes a same-word command wait for the first command's own outcome.
- That suspension happens in the product. `_report_chip_lost()` (src/asy_fram_driver.py:254-259) awaits `err_s` after `initialized` is already False (:224, :501) and before `lost.set()`. In that window `erase_ready()` (src/asy_fram_manager.py:788-789) calls `get_write_protected()` (asy_fram_driver.py:346-348), which awaits `err_s` and suspends.
- Proof, a scratch guard with the erase preflight made to yield (S/u35/laneM/test_gate_guard.py, logs guard_sc_*.log):
  - base: passes;
  - lock-free form: gather(erase, mempause, reboot, erase) answers [False, True, True, False] where base answers [True, False, False, True]. The mempause and the reboot get in during the erase's preflight;
  - lock removed, claim kept: the same word answers True while the first one is refused ([False, True]).
- No existing test pinned this, so the change would have been a hidden regression, which the owner's condition rules out.

**M.2, the supervisor returning instead of being cancelled: STOPPED.**
- `test_after_the_takeover_no_other_site_feeds` asserts the cancel at tests/test_asy_system_service.py:2195: `raise AssertionError("the supervisor ended without its cancel")`.
- In the trial run (S/u35/laneM/sys_head_-1.log, 188/189 passed) this was the only test that failed.
- The bar lets an existing test's asserted outcome change only for Z, so M.2 can go ahead only if you extend that exception to this one assertion.
- Checked as asked: nothing restarts the supervisor (`supervise_tasks()` is called once, at buildgen/codegen.py:452), and every path after the Event ends in the armed reset or an unfed watchdog reset.
- The trial diff is kept at S/u35/laneM/m_attempt.diff.

**M.3** (kept by your decision): untouched.

**Origin table** (git log -S --all; S0930 = the owner session's 2026-09-30 requirements):

| Construct | Origin | Intended function | Change | Test proving it |
|---|---|---|---|---|
| `_command_lock` | 9735d02 U20 lane S WIP S1; SUPP gate design, A.S0930.31 (1) | two commands never interleave their checks; a second one waits and sees the first's outcome | kept | test_two_commands_at_once_start_one_sequence_and_one_reset (preflight that does not yield only); the guard covers the yielding case and is bitten by a lock-free gate |
| tentative claim `_shutdown = purpose` | 9735d02; rule 3, A.S0930.12 | from gate entry, a mempause and any other word answer Failed | kept | the guard (bitten by the lock-free form); test_the_same_command_again_answers_true_and_any_other_answers_false |
| the two rollbacks `_shutdown = 0` | 9735d02; rules 4 and 5 | a refusal, or a failed create_task, changes nothing | kept | test_every_refusal_answers_false_and_changes_nothing. Bite (refusal rollback removed): 4 tests fail, that one included |
| `_reset_armed` re-check | 9735d02; rule 4a, A.S0930.32 (1), a race | an escalation that arms during the preflight refuses the command | kept | test_an_escalation_armed_during_the_erase_preflight_refuses_the_command. Bite (re-check removed): exactly that test fails |
| supervisor park-and-cancel | park on `_never` 5eb81d0 (U11 lane A); Event and cancel 9735d02 (A.S0930.13 "parks and is proven stopped"); cancel pinned by 877c57d (U20 lane S proofs); `except CancelledError` shape 51c11aa (U32 lane C) | the supervisor stops at a pass start holding no lock and is cancelled and awaited, so watchdog ownership passes before any step that can hang | kept | test_after_the_takeover_no_other_site_feeds (:2195); test_a_command_before_the_supervisor_runs_waits_for_its_first_pass (boot-time window); test_a_supervisor_that_already_ended_lets_the_sequence_proceed_without_a_park |

**What each construct affects:**
- Callers: `reboot_system`, `reboot_bootloader`, `reset_to_defaults` and `erase_fram`, reached through the generated dispatch (buildgen/codegen.py:252-256: reboot, bootloader, resetconfig, erasefram). `mempause` reaches `pause_permanent_storage()`, which reads `_shutdown`.
- Boot-time window: a command accepted before `supervise_tasks()` makes the sequence wait on the Event until the supervisor's first pass.
- Watchdog hand-over: `_feed_owned` is set at acceptance; the supervisor's park keys on it; after that the sequence feeds alone.
- Modes: STA and AP reach the gate over REST. Silent, Off and USB have no API, so neither construct runs there.
- Devices: identical on all six (one SystemService each).

**Proposed guard, not committed:** the two tests in S/u35/laneM/test_gate_guard.py (0.28 s, passing at base) pin the currently unpinned rule 3. I did not add them because test_asy_system_service.py is over 10 s at base, and LEAD NOTES 4 says such a file must not grow. Whether to add them is your decision.

**Observation, not in my files:** in the chip-loss window `erase_ready()` answers True, because `get_write_protected()` returns False ("not protected") for a driver that is no longer initialised. An erase accepted then still ends in code 9, since `erase_chip` re-checks `erase_ready()` (asy_fram_manager.py:761), so it is not silent.

**If M is re-routed:** the trial makes these SPECIFICATION.md lines stale: 694, 1184 ("under one lock"), 1185 (park, cancel, await), 3863 (the `_command_lock` row) and 4124. Removing the lock without row 3863 also turns tests_scripts/test_lock_order.py red. The device-script comments "waits for it to park" (tests_hardware/device_scripts/system_command_*.py, reset_code_command_incomplete.py:73) would need rewording too.

**Not run, since nothing is committed:** the 32768 stage, the other check files, the mpy-cross compare, the tests_scripts readers and the 17 scans. No timings were taken either.

**Runs** (all in S/u35/laneM/, zero memory-error markers in every log):
- rebuild: rc 0;
- trial with both changes at -1: rc 1, 188/189, only the M.2 test failed;
- guard: base rc 0, lock-free form rc 1, lock removed rc 1 (the last two as intended);
- one pair of bite runs killed by pid: the scratch tree was incomplete (no buildgen/). Re-run on a full copy: re-check bite rc 1 and rollback bite rc 1, both bitten as intended.

RUNS.md lines are written for the background runs.
