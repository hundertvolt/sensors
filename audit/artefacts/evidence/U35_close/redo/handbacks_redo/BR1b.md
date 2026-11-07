BR1b hand-back, saved by the lead from the message it sent (2026-10-27). Commits b8c28a07, ca51f901, af4cd2eb, c942fef2 on audit/u35-braise (on 32a62f28).

## BR1b hand-back (U35 lane BR1b): asy_base_classes.py

All 120 call groups now have a terminal verdict, and so does the one raise. No defects turned up and nothing in `src/` changed. Four commits on `audit/u35-braise`, worktree `S/wt-u35braise`, stacked on 32a62f28. Not pushed, nothing uncommitted (node_modules was already untracked).

**Commits**
- **b8c28a07** (item 1, on its own): fixes BR1's stale lines.
  - The handled `_checked_write_results` raise proof now cites its callers at :514 (except :515) and :696 (except :697).
  - The walk's three debug print keys now point at 514, 696 and asy_fram_manager.py:817. That last one is the `self.fram.setup()` call inside FRAMManager.setup()'s try, except :818.
  - The diff is exactly those three lines: the JSON proof, the rendered raising.md row and the walk's key tuple.
- **ca51f901**: the primitives, 48 groups (handled 18, unreachable 30).
  - Covers the module-level calls, Lockable/DeviceSession, RegionBuffer, PieceBuffer, LockedCounter, HourlyWindowCounter, TickSeconds, `_checked_write_results`, `arm_tick_timer` (its Timer callback included) and `utc_now`.
  - Adds the verdict file's "conventions" key, modelled on asy_print_log's. It states three shared classes once: the C-stack overflow, CancelledError propagation, and the small fixed allocations. For the allocations it names where each one lands: the boot entry's except BaseException (sensortask_<device>_main.py:38), `_log_dead_task()` :326, `_run_timer_starter()` :432, or Microdot's dispatch catch (ext/microdot.py:1533) handing off to `_handle_unhandled_exception()` (asy_webserver_service.py:791).
- **af4cd2eb**: the reader base, 32 groups (handled 27, unreachable 5).
  - Covers the ladder, the error streak, the init hooks, the read-trigger timer, the `_trigger_loop()` task top, `_republish()`, and the error-counter and setup calls.
- **c942fef2**: the config paths, 40 groups (handled 26, unreachable 14).
  - Covers `_get_dict_cfg()`, `_set_dict_cfg()`, the snapshot and recovery path (`_recover_failed_push()`), and all of SensorReaderConfig.
- **Checks:** every commit passed the walk `--check`, `e51_sweep.py --check`, `review_rows.py --check` and test_citations/test_decision_vocabulary/test_comment_block_cap (666 passed). In every raising.md and e51.md diff, the only table rows that changed are asy_base_classes rows.

**Rows by verdict**
- **Before** (BR1's module-wide count): open 42, transitive 33, inherently safe 2, unreachable 1; the one raise was already handled.
- **After**, 120 per-function groups: handled 71, unreachable 49. In raising.md, counting the raise, that is handled 72 and unreachable 49, with nothing open.

**Special-attention items**
- **Task tops:** `_trigger_loop()` is the only one, and its single wait is the flag's one waiter.
- **Timer callbacks:** the `flag.set()` in `arm_tick_timer`'s callback, and `ThreadSafeFlag.set()` in general, is one attribute store and cannot raise.
- **`Lockable`:** release's RuntimeError is caught at :131.
- **Snapshot and recovery paths:** they run inside the `_get_mgr_cfg`/`_set_mgr_cfg` trys, at :457/:503 and :515/:697.
- **Widened excepts:** all eight `except Exception` clauses call `report_if_fatal()` first. None swallows CancelledError, because it is a BaseException subclass (extmod/asyncio/core.py:18).

**Defects:** none.

**e51 rows added:** 49 in the generated block (30 primitives, 5 reader base, 14 config).

**Points for you and the owner**
1. **The two extension points are guarded unevenly.** `_set_mgr_cfg`'s return shape is checked at run time (`_checked_write_results`, :366-371), although mypy already types it. `_get_mgr_cfg`'s snapshot is not checked, and it is used at :692 (`old_values.get`).
   - I marked :692 unreachable under D.2: every override returns a dict or None, and None becomes {} at :507-508.
   - Under CLAUDE.md's flag-don't-fix rule I changed nothing. The options are:
     - (a) leave both as they are;
     - (b) drop the check under D.2;
     - (c) add the matching check for the snapshot.
   - I recommend (a). A malformed snapshot would still end in Microdot's catch and be persisted.
2. **The PieceBuffer callers don't catch MemoryError — a defect candidate, but not in my file.** SPECIFICATION.md G.2 says "a MemoryError there is not caught", and none of the four callers (asy_uart_comm.py:278, :313, :1111; asy_uart_driver.py:660) catches it either. Yet each has a true alternative flow (None or `ListenResult(None, ...)`), and I.4(a) (owner, 2026-09-25) says a function with one should catch.
   - I marked my row handled: the raise ends at the UART task top. The fix would belong in the UART files, though.
   - :313 runs before any ACK, so catching there changes what the peer sees, which may make it protocol-level. That needs routing and a changelog classification. I recommend putting it to the owner.
3. **Two allocations in `_set_dict_cfg` grow with the request:** `dict.fromkeys(data, …)` at :493/:524 and `results.setdefault` at :530.
   - The 2048 B body cap (web.max_content_length) bounds them, and there is no true alternative flow, so I marked them handled by Microdot's dispatch catch rather than defects.
   - Please check that reasoning.
4. **The walk treats a lambda's body as part of the enclosing try.** For `arm_tick_timer`'s callback at :387, the e51 row's last column therefore names MemoryError/OSError (:388, :391), even though the callback runs outside that try. The proof says this.
   - Fixing the walk (making a lambda its own scope) is yours to decide after BR1-3 merge. I left the walk alone.
5. **Stale lines in BR3's file, which I didn't touch:** asy_fram_driver.json's two setup-raise proofs still cite asy_fram_manager.py:795 (except :796). On the head these are :817 (except :818).

**Runs:** 4, all through `S/u35/laneB/br1b/run.sh`, with RUNS.md lines naming `U35 lane BR1b`: item1_checks, a_checks, b_checks, c_checks, all rc=0. Logs, `checks.sh`, `sites.py` and `groups.txt` are in `S/u35/laneB/br1b/`. I did no MicroPython runs and no rebuild, since `src/` was untouched.

nothing of mine is running
