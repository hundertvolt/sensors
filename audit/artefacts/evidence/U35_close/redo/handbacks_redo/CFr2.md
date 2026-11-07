CFr2 hand-back, saved by the lead from the message it sent (2026-10-27). Commit 2e826c28 on audit/u35-cfr2 (on 12ba7203).

CFr2 hand-back (U35 lane C, S/wt-u35cfr2, branch audit/u35-cfr2, on 12ba7203). Commit 2e826c28. Not pushed, nothing uncommitted. Logs are in S/u35/laneC/cfr2/.

**Item 1: system_service:453-454. The draft test was wrong; the product has no defect.**
- **Root cause, from the v1.29.0 source.** Cancelling a task that is awaiting another task forwards the cancel to the awaited task (extmod/asyncio/task.py:164-166, extmod/modasyncio.c:208-211). So the cancel never reaches the sequence's `except CancelledError` at :451. It lands on the supervisor, and :451 only ever sees the supervisor's own end, at which point `task.done()` is true.
- **Why the draft hung.** Its stubborn supervisor swallowed the forwarded cancel. When the run bound timed out, `wait_for` cancelled its runner (asyncio/funcs.py:49-50); that cancel was forwarded down the same chain to the same stubborn supervisor, and `wait_for` then waited on the runner forever.
- **Probe** (S/u35/laneC/cfr2/probe_cancel_evidence.log):
  - With a real-style supervisor, the cancel landed in the supervisor (sup.cancelled#2) and the sequence ran on to the arm (record 3, REBOOT). The cancel is absorbed.
  - A cancel during the park wait ends the sequence by CancelledError (record 9).
  - With a stubborn supervisor the hang reproduces, and `wait_for(a, 0.05)` is still not done after 500 ms.
- **:454 is unreachable.** `task is None` needs the park flag set with no supervisor task, but only the supervisor sets it (:551), and that task is assigned first (:805). Nothing in src/ or buildgen ever cancels `_shutdown_task`.
- **For D3 / the E.5.1 register:** CE3's "unreachable" stands and F1's "reachable by a cancel" is refuted. Whether to remove the guard under the library rule is your call. No test was committed.

**Item 2: all four fixed.** Each is red on its re-plant by assertion at -1 and 32768, green unplanted, with 0 markers (S/u35/laneC/cfr2/replant.jsonl, plant_logs/):
- test_erase_chip_lets_another_task_run_between_every_two_units. CFr's erase_yield regex had actually hit the read loop's yield at :316, not the erase loop's at :795. I retargeted it and added a row asy_fram_manager.read_yield for the plant that really ran.
- test_a_read_lets_another_task_run_after_every_slice_it_compares (the read_yield row).
- test_cobs_decode_lets_another_task_run_after_every_code_block.
- test_each_recovery_try_first_waits_one_window.
- test_a_published_candidate_still_reads_one_tick_before_its_hold_ends_and_is_gone_at_it (isl29125 near :569, driven clock).
- After the re-plants I changed only the type annotation of the read test's recorder, for mypy. MicroPython never evaluates annotations, so the result stands; the file passes 152/152 at both stages after the change.

**Item 3, K.25-mask-drop: fixed.** test_a_cancel_at_the_counter_cap_wraps_and_is_acknowledged now reads `_cancel_ack` at the cancel's return and expects 0. It is red on the re-plant.

**Item 4, named.fram_alloc: still open, waiting on your ruling.**
- **What the test measures.** At 32768 a collection runs inside the priced window and frees the window's own garbage. Blank setup reads 9,952-12,160 B at 32768 against 28,544 B at -1; valid setup reads 6,528-6,592 against 20,256. The same window pinned to -1 reads 28,544 at both stages. So the plant's 16 B per call vanishes at the threshold stage.
- **Why the check misses it.** `allocated == consumed` is an identity: `gc.mem_alloc() + gc.mem_free()` was constant in all 12 windows I measured, so the check can never see a collection (S/u35/laneC/cfr2/probe_fram_budget.*.log).
- **Proposal, not applied:**
  - In `_priced()`, set `gc.threshold(-1)` (MicroPython's own default) for the window only, restore the stage's value after, and drop the vacuous check.
  - Alternative: `gc.disable()` for the window only.

**Item 5, modlwip control: done.**
- `make -n` showed every output under the private BUILD dir and upstream extmod/modlwip.c being compiled.
- One build in tc-cfr2 (a copy of tc-int) finished rc 0. The test was red as the control must be: 7 of 9 tests failed with "one write() took 10000 ms, bound 250 ms"; the 2 that passed are its spin-window self-checks. 0 markers.
- Copy and build dir removed and confirmed gone (S/u35/laneC/cfr2/modlwip_control_test.log, modlwip_make_n.txt).
- In my copy of CFr's script I changed the unguarded `rm -- "$patched"` to `rm -- "${patched:?}"`.

**Counts (faults.md, re-rendered by plant_faults.py; only the intended rows changed):**
- 112 planted: 91 biting, 16 fixed, 5 equivalent, 1 open (fram_alloc).
- 40 rows not planted.
- The modlwip control row is counted as biting. The system_service row is "justified, unreachable", counted as not planted.

**Checks:**
- lint_direct rc 0. mypy src tests clean (temporary typings link, removed after).
- 21 tests_scripts readers (comment cap, citations, decision vocabulary, tunables, import placement, exception contract, code conventions, ticks-wrap and others): 1038 passed.
- Every changed file is green at both stages with 0 markers.
- Times, measured back to back with each file's base copy (-1 / 32768):
  - uart_driver: 5.62 / 9.97 (base 5.55 / 9.32)
  - uart_link: 4.40 / 6.12 (base 4.18 / 6.06)
  - codecs: 0.70 / 0.81 (base 0.71 / 0.78)
  - fram_manager: 0.88 / 1.80 (CFr's base 0.67 / 1.37)
  - isl29125: 2.58 / 2.87 (CFr's base 2.52 / 2.72)
  - None is over 10 % and 0.5 s.
- Silent-failure scan: the only `except` in my additions is the deliberate swallow of the competitor task the test itself cancels; every test asserts values.

**Runs:** probe ×2, 5 files at both stages, 6 re-plants (all red, no timeouts), the modlwip build and test, checks. All exited. The copies, snapshot, /dev/shm dirs and tc-cfr2 are removed and checked gone. A /proc cwd scan finds no process of mine.

nothing of mine is running
