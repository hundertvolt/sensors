# B5 falsification brief (lead, 2026-11-03)

Your job: try to REFUTE the claims below about commit `21e12c76` (base `3129bf21`, pre-audit `25caf528`, where the
captive DNS file was `src/captive_dns.py`). You get the claims, not the reasoning behind them. A claim stands only if
you could not break it; say how hard you tried. Also look for a lost feature or a reintroduced real defect in these
files against the pre-audit code: `asy_ntp_client.py`, `asy_dns_client.py`, `asy_captive_dns.py`, `asy_udp_socket.py`,
`asy_webserver_service.py`, and `buildgen/` (codegen, validate, error catalog).

- Read-only worktree `S/wt-b5f` (detached at `21e12c76`); S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.
  You may plant a temporary break there to test a claim, then restore it (`git -C S/wt-b5f checkout -- <path>`).
  Never commit, never push, never touch any other worktree.
- `S/u35r/r1/common_r1.md` gives the environment, the run wrapper (`S/u35/lead/run.sh`, labels `b5f_`), the one-file
  test commands and `S/u23/rebuild.sh <worktree>` (run it once before any test file). Its binding rules apply. No whole
  gate: single test files only, at most ten runs in all. Never open anything under `/root/.claude/`. Never read
  `arduino/` (`':!arduino'` in every git grep and git log). `tests_hardware` only with `--collect-only` or `--twin`.
  No real network, no real hardware.
- The legacy tree (`python/`, `modules/`) is reference-only: read it, never run or change it.

## Claims
1. The web server calls `start_server()` once; a failed start raises out of the serving task and the supervisor's
   restart retries it, and a restart can bind the port again at once. Nothing emits, decodes or expects W62.
2. The reader proxy refuses only a line or a head past its bounds, too many header lines, and a `Content-Length` that
   is not ASCII digits or comes twice. Every other malformed head, and a body cut short of its `Content-Length`, reaches
   Microdot, which answers or drops it without ending the connection task abnormally, leaking the connection count, or
   printing anything at DebugLevel 0.
3. `resolve_ipv4()` never raises for any host string and any server list, returns a dotted-quad `str` or `None`,
   receives at most 512 B, and never sends a query with a label over 63 octets.
4. Captive DNS: a heap failure while parsing a query drops that query like a malformed one and the server keeps
   answering; a socket that never bound and a failed receive each log one warning (W42) and the loop retries.
5. NTP: a reply of 44-47 B sets the clock as `25caf528` does; a shorter reply, or one with a zero transmit timestamp,
   sets nothing and logs E69; a `MemoryError` while parsing ends the task for the supervisor.
6. NTP schedule: synced, a resync is due after the configured interval; unsynced, the first attempt runs at the first
   check with the network up and, after each failed attempt, the next one 60 s later, every time; an attempt skipped
   because the network is down does not count; a settings change or a forced resync tries at once. No device setting,
   validator field, generated value or SPECIFICATION.md text for the old doubling backoff remains.
7. With NTP's check timer or its sync-age timer refused at boot, the failure is logged and nothing else breaks.
8. W49 covers both the per-call timeout and the request cap; nothing emits, decodes or expects W50, W16, E73 or E74.
9. A served static file is closed after its response; a HEAD or a cut response leaves at most a file the next
   collection closes, so repeated HEAD requests do not exhaust file handles.
10. A PUT body whose decode runs out of heap answers the "Invalid JSON" error envelope.
11. UDP: `ready()` ends at most one poll round past its deadline; a cancel at any await of `_connect()` or `ready()`
    leaves the lock free; every product user of `UDPSocket` disconnects in its own `finally` or cleanup, so a cancel
    during the connect backoff leaks no socket.
12. `ResetErrors`: a reset answering false gives "Failed"; a raising reset reaches the catch-all (500); the resets still
    run concurrently.
13. No GET body can carry a non-finite float: every float any GET route writes is gated at its source.
14. No product check got weaker: every test change is the mechanical consequence of an item above. Look hardest at the
    serving-demand scenario in `tests/_sensortask_scenarios.py`, the cancel invariant in `tests/test_asy_udp_socket.py`,
    `tests_scripts/test_fatal_report_sites.py`, twin Run 9's failure bound, and every removed test and scenario.
15. Numbers: `src/` bytecode 202,643 B at `21e12c76` (-3,038 B against `3129bf21`), no module grew
    (`S/u35r/r0/module_sizes.sh`); dev's `imageFreeBytes` 49,892 B.

## Hand-back
Write `S/u35r/r1/B5/FALSIFY.md`, first line "B5 falsification, written by the agent (<date -u>)": per claim STANDS or
REFUTED, with file:line evidence (and the planted break or run label where you used one). Then any defect you found
outside the claims. Your final message: the path, one line per REFUTED claim, last "nothing of mine is running".
