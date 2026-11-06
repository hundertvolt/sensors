# Fix unit: three flash-tier test faults the bench read on day 2 (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `bfix_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. `tests_hardware/README.md` for the
flash tier's fixtures and helpers.

## The bench's report (2026-11-06 07:05 UTC, relayed by the owner; read from the code and numbers, not measured)
1. `flash/test_uart_crossover.py::test_no_frame_is_lost_while_interrupts_are_off[crc16]`: 2 of 22 frames intact in the
   3 ms window. Under CRC16, at about 21 ms a frame (the script's own comment), the reader drains about 2.6 B/ms against
   11.5 B/ms on the wire, so the 512 B ring fills in about 57 ms, around the window's start. A continuous sender is
   outside the ring's sizing (the commit that set 512 B ruled it out); the earlier 8,192 B ring hid it. `[none]` passes.
2. `flash/test_uart_crossover.py::test_get_and_set_and_a_multi_chunk_train_cross_the_jumper[none]` and `[cobs]`: the
   largest free block grew by 768 and 880 B against an exact-equality "nothing allocated" check; `[crc16]` passes.
   Likely a collection inside the search on the new layout.
3. `flash/test_watchdog_starvation.py`'s `closing_reset` hard-resets and waits only for USB; the session-end block in
   `tests_hardware/conftest.py` (`save_errcount(dut_ip, "session-end")`, :494) then makes one strict `GET /status`
   while the board boots: a teardown error that skips the SCD30 end snapshot, the board-state check and the session-end
   FRAM dump, so those session-end checks have not run on either bench day.

## Your work (worktree `S/wt-bfix`, branch `audit/bfix`, at int `8ea29293`; create it; commit locally, never push)
1. The stream in the frame-loss test stays within what the receiver drains in each CRC mode outside the
   interrupts-off window (paced from the mode's own per-frame cost), so a lost frame can only come from the window the
   test is about. Never an unchecked read: the CRC path is part of what the test proves.
2. The "nothing allocated" check reads `after >= before` (a retained allocation can only shrink the largest block; a
   collection can only grow it), unless the script already collects before measuring. Its message says so.
3. `closing_reset` leaves the board serving, through the harness's existing wait, before the next step reads it.
   No new helper where one exists.

## Never
No hardware: `tests_hardware` runs only with `--collect-only` or `--twin`. Never weaken what a test proves: no
retry, no skip, no wider bound than the reasoning above gives. Never edit `src/`, `ext/`, or any `tests_hardware`
file but the three named (another unit is writing other files there); never read `arduino/`; never open
`/root/.claude/`.

## Checks
`S/u35/lead/lint_direct.sh`; the three mypy passes; the three files with `--collect-only`, and `--twin` where they run
there; the tests_scripts files that read `tests_hardware/` (grep for them).

## Limits
Write only `tests_hardware/flash/test_uart_crossover.py`, its device script(s) if the pacing lives there,
`tests_hardware/flash/test_watchdog_starvation.py` and `tests_hardware/conftest.py`. One commit. Budget about 0.5 % of
the week. Hand back by 09:15 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_BFIX.md`, at most 15 lines, and return its path: per item the change (file:line) and the reasoning
in one line, each check with its result, and the `PYTEST_K` expression the bench reruns. Last line: "nothing of mine is
running".
