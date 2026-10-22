U1 hand-back (lane U). Branch audit/u35-u at feae592, worktree S/wt-u35u, set up with S/u23/rebuild.sh. Commit 7158212 is my only commit and my last. Nothing uncommitted.

**Steps**
- 59, applied: added `test_cancelling_at_each_await_leaves_no_lock_or_busy_flag` to tests/test_asy_uart_comm.py. It sweeps uart_set, uart_get and uart_listen with `cancel_at_each_await`. Each count builds a fresh pair inside the coroutine. The clock is `PollRoundClock` with `pace(real=False)`, so one turn is one await. The other end's call is cancelled at the same turn, never drained. Invariants on both ends: `_busy` False, `_in_resync` False, both session locks free. At least one count must cancel while a lock is held. Turns: set 16, get 16, listen 15. The earlier `session_lock` part had already landed (:3094/:3111).
- 60, applied: the wedged holder awaits `never_set.wait()`. The scenario cancels it in `finally` and awaits it out. The 50 ms bound keeps its comment line, and the assertions are unchanged.
- 61, applied: added `test_cancelling_a_session_at_each_await_releases_the_lock` to test_asy_uart_driver.py. It sweeps a locked `read_until_complete()` and a `write()` on a CRC16 `_make_uart()`, with the TX ring busy for 2 rounds. Invariants: lock free, `cancel_unacknowledged` still 0, ring position and fake call log the same as at the cancel. At least one count must cancel with the lock held. Turns: read 15, write 17.

**Seen failing** (scratch copies under S/u35/laneU/bite*, nothing planted committed)
- 59 bite, uart_set_into `_busy` not reset on cancel: "cancelled after 1 turns: UART_A is still marked busy".
- 59 bite, uart_listen `_busy` not reset on cancel: "cancelled after 1 turns: UART_B is still marked busy".
- 61 bite, `__aexit__` keeps the lock on cancel: "cancelled after 1 turns: session_lock is still locked".
- 61 bite, `__aexit__` writes on cancel: "read or written while unwinding: (0, 0) -> (0, 1)".
- 60 bite, holder never cancelled: fails on run()'s 5 s bound with a bare `TimeoutError`. That error carries no message.

**Red checks:** none. One red found and fixed before commit: test_decision_vocabulary flagged my comment "never touches the bus again, never set". I restored the allow-listed text exactly, so no allowlist row is orphaned.

**Checks**
- ruff clean.
- mypy at 0, both with no args and with `src tests tests_hardware/device_scripts`. No new explicit `Any`: a new helper is typed with TypeVars T and U in the TYPE_CHECKING block.
- One pytest process covering the 12 pre-commit checks, the 17 scans and the readers (uart_changelog, ticks_wrap_scan, exception_handler_contract, microtest): 1087 passed, plus the 2 vocabulary failures above. After the fix, those checks (with comment_block_cap and suppression_form) passed 658/658.

**Runs:** one background run, pid 22185, rc 0 (in RUNS.md); everything else ran in the foreground. All runs green, with zero MemoryError and zero "memory allocation failed". Paired base/head times in seconds:
| file | -1 base → head | 32768 base → head |
|---|---|---|
| uart_comm | 62.83 → 62.34 | 63.51 → 63.67 |
| uart_driver | 6.24 → 5.67 | 9.95 → 9.30 |
| cancel_sweep (reader, head only) | 40.32 | 40.54 |

The comm change is within noise; the new test alone runs in about 0.05 s. After a later type-only fix, uart_driver re-ran on the head at 5.59/9.09 s, 166/166.

**Disk:** the disk was full from about 17:05 to 17:15 UTC (ENOSPC), and my worktree setup ran in that window. After 17:15 the worktree checked clean at feae592 and I re-ran rebuild.sh (rc 0). Every test run started after 17:15.

**Relay:** wrote `<HANDOVER-UART> 7158212` under `## U`. The two UART test files now pass to Y.

**Decisions (agent, 2026-10-21)**
- The sweeps use the harness's `PollRoundClock` unpaced rather than DrivenTime. The UART sleeps are 1 ms, so no shorter driven turn exists.
- The peer end is cancelled with the path rather than drained. Draining through `with_listener` cost 5 s per count, because an idle listener has no deadline.

**Scan and modes**
- Silent-failure scan of both files, all classes: nothing new. Each `except CancelledError` swallows only a cancel the test made itself.
- No sweep found a product defect, so P's changelog gets nothing.
- Test-only change: STA, AP, Silent, Off and USB are unaffected on every device. The wire format is untouched.

**Facts owed:** to Y, explicit-`Any` counts in both files unchanged. Lead/D: none.

**U2 starts from:** 7158212 with link_driver, twin uart_link and the hazard plant (steps 62, 100, 148, 144's evidence), then U's checks.

nothing of mine is running
