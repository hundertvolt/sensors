R2 hand-back (root cause only). Nothing committed. Both worktrees are clean, the tree copy is deleted, and nothing of mine is running. I used about 37 tool calls.

Verdict: a stale test expectation. It is not a product defect and not a twin fidelity gap (agent, 2026-10-22).

Root cause, line by line (f3fff0e, the same code at 7a7d01a):
- clear() (src/asy_uart_comm.py:1053-1066) calls cancel_read_timeout(). The parked ready() sees `self._cancel`, acknowledges it and returns False (asy_uart_driver.py:710-712). So readinto_until_complete returns None (:612-614) and _read_frame returns False.
- Then _listen_unlocked (:569-573) calls `_fault(_ERR_TIMEOUT, "listen read failed or was cancelled")`, which runs _resync (:807). Its _drain (:486-514) waits one full quiet window, `_resync_window_ms()` = timeout x 3/2 (:836-837). At the default timeout of 1000 ms that is 1500 ms (dev's uart_link instances set no timeout). Only then does uart_listen() return _LISTEN_FAILED, with the lock released.
- The script waits only `_CANCEL_SETTLE_MS = 400` (uart_idle_poll_rate.py:40, :74). So all four arms cancel the listener and report [True]*4. The assert at test_uart_crossover.py:156 then fails.
- asyncio: the parked await is `asyncio.sleep_ms()` in ready() (asy_uart_driver.py:728). The cancel is a flag, so the pinned extmod/asyncio only comes in with the script's own listener.cancel() (task.py:157). Its CancelledError is a BaseException (core.py:18), and ready() does not catch it.
- Silicon behaves the same. The whole path is shared Python. Its one hardware read is _rx_level() (the DMA count plus UARTRSR through mem32), which reads 0 on a silent line on both the twin and rp2. ready()'s POLLIN path calls no machine.UART method.
- Part J agrees with the code. SPECIFICATION.md:9387-9390 says "The noticing side then resyncs (drain until quiet, bounded, then hold off initiating); `clear()` does the same from outside for a parked listener", and :9486 gives the quiet window as "1.5 × timeout".
- Since when: a cancelled listen has resynced since c63ef97 (2026-09-11). The 400 ms window (40 x 10 ms) dates from the script's first commit, dc05ce8 (2026-09-12). So the two always disagreed. The script cancelled the listener silently until 06a8ae5 (2026-10-20) reported it and :156 asserted it. The record's file-wide reason then hid the failure until 7a7d01a.

Evidence (S/u35/laneR2/):
- test_gc-1.log and test_gc32768.log: the unchanged test fails at :156 with [True]*4 at both stages (14.3 s each).
- probe_gc-1.log and probe_gc32768.log (probe/uart_idle_clear_probe.py): the listener ends on its own 1504-1511 ms after clear() at timeout 1000 (window 1500). At timeout 200 it ends after 303-305 ms (window 300), and at 2000 after 3003-3009 ms (window 3000). It made 684-689 drain poll rounds, returned (None, None, None), left the lock free and busy False, and logged one E22.
- fixed_gc-1.log and fixed_gc32768.log: the unchanged test against a scratch copy with the fix below gives "1 passed" at both stages (18.7 s).
- No MemoryError and no "memory allocation failed" in any of the six logs.

Fix:
- tests_hardware/device_scripts/uart_idle_poll_rate.py:74 becomes `outlived = not await _until(wdt, listener.done, comm._resync_window_ms() + _CANCEL_SETTLE_MS)`, with a comment: "The cancelled listen resyncs (J.5: drain until quiet), so it ends one quiet window after clear(), not at once."
- The comment at :58 changes "outlived comm.clear()" to "outlived clear()'s resync". test_uart_crossover.py stays as it is.
- The Part N row at SPECIFICATION.md:12374 (l3.uart_idle_poll_rate_cancel_settle_ms) changes: 400 ms becomes the slack past the quiet window, and the twin measurement above is recorded.
- The wait goes from 400 to 1900 ms. That raises a bound, so the lead rules on it (CHECKLIST 4).
- No src/ change, so there is no UART_C_PORT_CHANGELOG.md entry (neither Class A nor Class B). The wire format is untouched.
- Lane: neither file is in S/u35/lead/lanes.py, so the lead assigns it. Lane P is the natural owner, since it holds src/asy_uart_comm.py and the UART unit tests. The Part N row belongs to lane D. After the fix, the W6 re-record (H3's record.sh) should show this script passing with no reason.

Effect on dev: no firmware change. Nothing in src/ calls UARTComm.clear() (git grep), so STA, AP, Silent, Off and USB are all unaffected. wozi has no UART. This test gets about 4.4 s longer per stage on the twin and on L3.

Fact owed to lane P: every clear() of a healthy parked listener records a persisted E22 ("listen read failed or was cancelled"). On dev, UART_resp is FRAM-wired, so it reaches FRAM. Part J names this message (SPECIFICATION.md:9425), and today only test scripts call clear(). This is a fact, not a defect claim.

Decision (agent, 2026-10-22): I chose a test fix over a product change. J.5 specifies the resync after clear(), and removing it would change recovery in a two-implementation contract.

Runs, all lined in RUNS.md: runs.sh gave test -1 rc 1, test 32768 rc 1, probe -1 rc 0 and probe 32768 rc 0. runs2.sh gave fixed -1 rc 0 and fixed 32768 rc 0.