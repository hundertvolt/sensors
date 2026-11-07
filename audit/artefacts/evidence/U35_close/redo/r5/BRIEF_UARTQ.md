# R5 unit uartq: the UART link never waits on its own FRAM log write (lead, 2026-11-07)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `uartq_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Then, in the integration tree
`S/wt-u35int` (head `2f6d1453`): `src/asy_print_log.py` (`PrintLogHistory._store_err()`, `err_s()`/`wrn_s()`,
`PrintLogHistoryStore._write()` with its generation skip, `reset()`), `src/asy_uart_comm.py` (`_err()`, `_fault()`,
`_accept_set()`, `_reject_wrn()`, `_resync()`, `_drain()`), `src/asy_uart_driver.py:676`, SPECIFICATION.md Parts C.7.1,
G (the logging primitive) and J (the UART recovery), and `UART_C_PORT_CHANGELOG.md`'s entry format.

## Owner ruling behind this unit (2026-11-07 14:20:22 UTC, verbatim)
"B" - answering: trace the loaded UART miss with one instrumented image, then fix the UART receiver so it never waits
on its own FRAM log write inside an exchange (a protocol change-log entry, internal); the FRAM bus hold stays as it is
and is documented; the FRAM driver changes only if the trace shows the UART fix is not enough.

## The evidence (bench, real board, 2026-11-07 16:26; the trace shows the UART fix is enough)
Three back-to-back /status readers plus the UART hazard sweep. The responder ACKs a SET (uid 0), its callback declines
it, and `_reject_wrn()` awaits `wrn_s()` (W56): that FRAM write waited 8,047 ms behind the SGP40 driver's FRAM backup,
which holds the FRAM bus up to 5.8 s at a time under the readers. The initiator sends its next frame 3.07 s after the
ACK; the responder's `_resync()` drain runs only after the write, finds that frame in the receive ring and swallows it
(53 B drained); the initiator gets no answer. Persist times across three runs: 229-8,047 ms. The same happens after
any fault, since `_fault()` awaits `_err()` (`err_s()`) before `_resync()`.

## Your work (worktree `S/wt-uartq`, branch `audit/uartq`, at int `2f6d1453`; create it; commit locally, never push)
1. `asy_print_log.py`: `err_q()` and `wrn_q()`, plain (not async) twins of `err_s()`/`wrn_s()`: the history and count
   change and the line prints at once, as now; the FRAM write runs in the background. At most one writer task per
   logger, created only when none is pending; it writes again while entries arrived during its write, then ends. The
   RAM-only `PrintLogHistory` starts no task. Split `_store_err()` so both forms share the record step; `err_s()` and
   `wrn_s()` keep their behaviour exactly.
2. `asy_uart_comm.py`: `_err()` becomes plain and uses `err_q()` (its 17 `await self._err(` sites follow);
   `_reject_wrn()` and `_resync()`'s W54 use `wrn_q()`; `asy_uart_driver.py:676` uses `err_q()`. Leave `_ready()`, the
   setup paths, the cancel path's W-unacked and the link driver's own logging as they are: none sits inside an
   exchange. `_resync()`'s routine print gains the drained byte count (print only), so a swallowed frame shows on the
   console without a trace image.
3. Tests first: (a) the logger: an entry is in `get_log()` before any await; FRAM holds it once the writer has run;
   N calls start one task; a call during a write lands too; uninitialised writes nothing; a failed write diagnoses;
   a `reset()` racing a pending write leaves FRAM and RAM agreeing. (b) The miss itself, the smallest reproduction:
   a responder whose FRAM write takes longer than the resync window; a declined SET, then the next frame one quiet
   window later: that frame is received, not drained. Seen red on `2f6d1453`, green after. The same for one fault
   path. Tests that read FRAM right after a UART fault let the writer run first; never weaken an assertion.
4. Docs, current state only: C.7.1 (the two forms and when a caller uses `_q`), Part G's logging row, Part J's
   recovery (the receiver resyncs without waiting on its log write), the trade-off in one line (an entry reaches FRAM
   shortly after the link moves on; a reset inside that window loses it), and the FRAM bus hold where Part A/C
   describes the FRAM: an SGP40 backup under three back-to-back /status readers takes 8-20 s, holding the bus up to
   5.8 s at a time; other FRAM writers wait that long (bench, 2026-11-07). `UART_C_PORT_CHANGELOG.md`: one entry,
   Python-internal (no C impact; the wire format, accept/reject rules and recovery windows are unchanged).

## Never
No hardware. Never read `arduino/`; never edit `ext/`; never open `/root/.claude/`. No `gc.collect()`, no new delay,
no per-frame allocation in the steady state (one task per burst of log entries is the allowance). Never print, copy
or write any Wi-Fi credential or the hotspot fallback password.

## Checks
Each touched test file at both GC stages while fixing; `lint_direct.sh`; the three mypy passes; then the gate as
common_r1 says. The host is free for it: before the gate create `S/u35/lead/heavy.lock` holding the line `uartq`
(if it already exists, wait for it to go), and `rm` it (literal path, its own command) when the gate ends.

## Limits
Write only the files above and their tests. One commit. Budget about 1 % of the week. Hand back by 19:30 UTC.

## Hand-back
`S/u35r/r5/HANDBACK_UARTQ.md`, at most 25 lines, as common_r1 says; plus the module sizes and `imageFreeBytes`.
