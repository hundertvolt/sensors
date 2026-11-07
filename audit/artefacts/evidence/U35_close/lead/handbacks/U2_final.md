U2 hand-back (lane U). Branch audit/u35-u, worktree S/wt-u35u. My one commit is f6f54cc, on top of 7158212. Nothing is uncommitted. Generated inputs were current: 7158212 changed no generator input since the 17:15 rebuild.

**Steps**
- **62, applied.** New test `test_cancelling_an_exercise_round_at_each_await_leaves_the_bus_unlocked` in tests/test_asy_uart_link_driver.py.
  - Form: `cancel_at_each_await` over `_exercise_loop()` on a pair built inside the coroutine, `PollRoundClock` unpaced. The responder's `uart_listen()` is cancelled together with the path.
  - Invariants: both ends have `_busy` and `_in_resync` False and both session locks free, and `(transfers, failures) == (GET returned, 0)`.
  - Floors: at least one cancel lands with a lock held, and at least one lands after the GET returned.
- **100, applied.** The coexistence test in tests/test_digital_twin_uart_link.py now runs a 140-byte `uart_set(0x02, …)`, asserted True. The noise consumers run through both exchanges and are checked still alive at the end. The banner check is now an exact byte compare.
- **148, applied, with a bound test.** The 20 ms plant left the clean hammers green, so I added `_check_a_clean_transaction_completes_within_its_virtual_time_bound` (both CRC modes) and `# @tunable l1.uart_comm_hazard_clean_transaction_virtual_ms = 14` (tests/test_uart_comm_hazard.py:1383).
  - On `DrivenTime(sleeps=True)` a clean `uart_set(1, b"x")` with its listener takes 4 virtual ms in both modes.
  - With the 20 ms plant it takes 44 ms; with 100 ms, 204 ms (CRC16) and 279 ms (no CRC, where the SET fails).
- **144's evidence:** relayed to D. The J.7 sentence itself is D2's.

**Plants** (`await asyncio.sleep_ms(N)` before `_write_frame_with_ack`'s frame write, in scratch only)
- 20 ms: 10 of the 12 own-clock hammer checks stay green in both CRC modes. Only the no-CRC faulted hammer and its host-stall variant go red ("never recovered once the fault was cleared", on the 30 ms budget).
- 100 ms: all 12 go red.

**Seen failing** (scratch copies under S/u35/laneU/u2/, nothing planted committed)
- bite62a, `_run_get` leaves `_busy` set on a cancel: "cancelled after 1 turns: UART_init is still marked busy".
- bite62b, the loop counts a cancelled GET as a failure: "counted (transfers, failures) (0, 1) with the GET returned 0 time(s)".
- bite100, one byte of the SET's second frame dropped: "the 140-byte SET failed while the noise tasks ran".
- b148_20 and b148_100, both modes: "a clean SET and its listener did not end within 14 virtual ms, a latency regression".

**Red check:** tests_scripts/test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree fails with "tests/test_uart_comm_hazard.py:1383: l1.uart_comm_hazard_clean_transaction_virtual_ms is tagged but has no SPECIFICATION.md Part N row". It is red until D's Part N row lands (R-17).

**Other checks**
- ruff is clean. All three mypy passes report 0: no args (264 files), `src tests tests_hardware/device_scripts` (230), and the twin pass (52).
- The 12 pre-commit checks plus suppression_form and uart_changelog ran in one process: 829 passed, 1 failed (the red check above).
- One warning: the datasheets submodule is not initialised in the worktree (test_citations.py:236).
- No explicit `Any` added and no allowlist row orphaned.

**Driven-clock site:** `_check_a_clean_transaction_completes_within_its_virtual_time_bound` cancels nothing under the shim. Both tasks run to their end; on a failure they stay parked. Steps 62 and 100 use `PollRoundClock`.

**Decisions (agent, 2026-10-21)**
- 62's invariant is stricter than "≤ 1": the "≤ 1" form would pass bite62b.
- 62's sweep is `endless` with `max_steps=40`. The loop's 1 s period sleep runs on the real asyncio, so the loop never ends by itself; the floors prove the counts reached past the round.
- 100's noise is now continuous (`_uptime_noise()`). The one-shot `get_uptime()` tasks finished at the GET's first yield, so they could not be running during the SET.
- 148's bound is 14: the 4 ms healthy figure plus a 10 ms margin.
- The plants ran from scratch directories placed first on the module path (U1's form), not from a separate git worktree. Each plant is a one-module change and none is committed.

**Scan and modes:** silent-failure scan of the three files, all classes and the brief's modes, found nothing new. Each `except CancelledError` swallows only the test's own cancel, and `run_until`'s failure is re-raised with its context. OF-111's refusal has no site in these files. The change is test-only: STA, AP, Silent, Off and USB are unaffected on every device, and the wire is untouched.

**Defect in another lane's file (to Y):** tests/test_asy_uart_comm.py:3116 and :3172 have one blank line, not two, around `test_cancelling_at_each_await_leaves_no_lock_or_busy_flag`. Ruff's E302 is preview-only, so lint does not catch it.

**Paired base/head times** (s), every run green, zero MemoryError and zero "memory allocation failed":
| file | -1 base → head | 32768 base → head |
|---|---|---|
| link_driver | 2.37 → 2.43 | 2.40 → 2.61 |
| hazard | 104.58 → 105.17 | 107.90 → 108.19 |
| twin uart_link | 54.90 → 55.05 | 59.12 → 59.27 |

Hazard (+0.6 s and +0.3 s) and twin (+0.15 s) are over 10 s at base and still grew slightly, which LEAD NOTES 4 does not allow; I made nothing more efficient to offset it, so this is for your ruling. The new hazard check costs about 0.1 s and the twin's added SET about 0.15 s; both heads are below U32's figures.

**Relay:** two lines written under `## D`: the `<TAG l1.uart_comm_hazard_clean_transaction_virtual_ms 14 …>` line and the J.7 latency line with the plant results.

**Runs** (logged in RUNS.md)
- runbites pid 12305: bite62a and bite62b ran, rc=1 each as intended. Then killed while waiting for a slot, to reorder.
- runbites pid 14511: m148_clean rc=0, m148_20 rc=0, m148_100 rc=1, plant148_20 rc=1 (181 s), plant148_100 rc=1 (783 s). Then killed while waiting for a slot.
- times pid 28443: killed before any run started, to reorder.
- times pid 4818: rc=0. It covered b148_20 and b148_100 (rc=1 as intended), bite100 (rc=1 as intended) and all 12 paired runs (rc=0).
- Foreground: the head link_driver file, ruff, three mypy passes, and the checks pytest run.

**U3 starts from** f6f54cc with nothing uncommitted.
- Work: owner question 5's dev hazard mode (LEAD NOTES 12), in src/asy_uart_link_driver.py, test_asy_uart_link_driver.py, test_digital_twin_uart_link.py and the bench/device-script files; then U's complete checks (the 17 scans, the readers, both-stage runs).
- Open threads: test_uart_comm_hazard.py:1383, which waits on D's Part N row; the timing deltas above, which need your ruling.

nothing of mine is running
