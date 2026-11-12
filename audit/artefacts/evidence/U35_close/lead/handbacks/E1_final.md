E1 hand-back (lane E, block 1). Commit 8fb6241 on audit/u35-e, on top of 1d77560. Worktree S/wt-u35e. Nothing is uncommitted and nothing of mine is running.

Steps by verdict:
- OF-81 (R-11): applied, no product change. tests/test_asy_base_classes.py gains `_BalanceLock` (an asyncio.Lock that counts the releases it refuses, lock.py:22-23) and `_assert_balanced` (assert_unlocked plus no refused release). The swallow test now uses the balance lock and checks that the invariant sees the swallowed double release. New `test_lockable_stays_balanced_when_cancelled_at_each_await` runs cancel_at_each_await over a contended Lockable: queued, handed the lock but not yet resumed, or inside its hold.
- 41: applied. The fram lock-busy test runs on DrivenTime(asy_fram_driver, sleeps=True): elapse(999) leaves it not done, elapse(1) gives False. LOCK_TIMEOUT is logged once, initialized stays True, lost is not set, and the lock is usable afterwards. `_RecordingWaitFor`, `check_sleep_ms` and `TypeVar T` are gone. I used elapse(), not advance(): advance() does not run the woken task.
- 52: applied. isl :4046 is now an Event gate set after the first read_status(). The :4075 comment is the given text.
- 58: applied. scd30 :2340 is now an Event gate set after the first read_measurement() returns.

Bites (scratch copies first on MICROPYPATH, deleted afterwards; the tests are guards because there is no behaviour change):
- A double release in Lockable.__aexit__: only the new sweep fails ("cancelled after 1 turns: the session lock refused 1 release(s): a double release"). The other 190 tests miss it.
- The fram bound at const(999): "verify_present() gave up before its 1000 ms bound".
- An unlocked isl configure(): "(2, True) landed inside a read cycle". The park test fails too.
- scd30 _send_command() without the session lock: "expected writeto(READ_MEASUREMENT) at index 6, got ('writeto', 97, b'T\x03...')".

Decisions (agent, 2026-10-21):
- The fake I2C's wire calls never yield, so without help no unlocked isl path could show. The isl test therefore makes the data burst's hold yield once, through a patched device.get_register_into, and asserts that every data burst directly follows its own status read. It also checks the burst count, so the check can never match nothing.
- The balance lock lives in my own test file. tests/_cancel_sweep.py is lane C's file.

Runs (logs in S/u35/laneE/; zero MemoryError and zero "memory allocation failed" in every log):
- checks_a.sh: 4 head files at gc -1 all green (191/104/246/131 passed). The 4 bites each rc=1 as planned.
- times_b.sh, paired base/head in seconds, -1 then 32768:
  - base_classes: 0.46/0.40, then 0.46/0.46
  - fram_driver: 0.16/0.17, then 0.20/0.21
  - isl: 2.59/2.56, then 2.93/2.88
  - scd30: 22.18/22.31, then 27.94/29.17
- The scd30 32768 pair was +1.2 s, so I re-timed it alternating head/base twice: head 28.90/28.39, base 29.09/28.68. No growth. The first pair was host noise (5-6 heavy processes on the host).
- RUNS.md has start and done lines for each run.
- mypy, both main passes, cold cache: clean (264 and 230 files).
- ruff: clean.
- The 12 commit checks plus readers test_microtest and test_radio_shape_corpus: 829 passed. One warning: datasheets submodule not initialised, from test_citations.py:236.
- Deviation: I ran that pytest batch as one process, without unshare -n, and alongside the timing run. test_microtest starts MicroPython, so CHECKLIST 12 was breached. It does not touch the scd30 result: the re-time ran alone.

Silent-failure scan, my 4 files, all classes, test-only changes: none found.

Facts owed:
- To lane C: _cancel_sweep.assert_unlocked alone can never see a double release, because the lock ends free either way. A counting lock like `_BalanceLock` is what shows one, and C may lift it into the sweep.
- To the lead: no allowlist row orphaned, no tag changed.

E2's start state: head 8fb6241, tree clean. File: tests/test_asy_bmp3xx_driver.py (step 39), then E's complete checks.
- Still owed in E's files: the D.15 module-level reorder. Out-of-order pairs: base_classes 15, isl 16, scd30 16 (all already out of order at base), fram 0. It is a pure move, checked by line multiset, done as its own last commit in the dns form (as C2a/Q1). I did not do it for lack of calls. E2 needs these files added to its set for that.
- E2's brief also names readers to run before the final: import_placement, microtest, radio_shape_corpus, plus the 17 scans.