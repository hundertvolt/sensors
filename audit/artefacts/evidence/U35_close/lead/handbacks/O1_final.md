Lane O, block O is done: both parts are applied in commit 15da695 on audit/u35-o (worktree S/wt-u35o, base 6dabd9b). Nothing is left uncommitted and nothing of mine is running. Every check is green except the expected red, test_twin_record.

Steps:
- O1 applied: the int-address `try` in `CaptiveDNS.run()` and its comment are removed. The shim did not need changing.
- O2 kept: `DNSQuery`'s MemoryError re-raise is untouched. The re-raise in `run()` sat inside the removed `try`. A MemoryError now goes straight to the same outer catch-all (report_if_fatal, then err_s UNEXPECTED, then the 3 s pause), so the outcome is unchanged.
- O3 applied: the description now reads "Bench-only: the request is not stored; the faults the run provokes appear in both UART error logs." Its only readers were generated output, regenerated with S/u23/rebuild.sh.

Your addendum, construct by construct:

| Construct | Origin and what confirmed it | Affects | Change | Proving test |
|---|---|---|---|---|
| int-address `try` in `run()` | 639e992 (2026-07-21): comment "a raw sockaddr byte - see BACKLOG.md". 7c16ed0 (2026-08-08): "confirmed directly: plain int"; its commit message says "a real, reproduced Unix-port quirk". BACKLOG at 639e992, lines 1748-1757: "a second, distinct Unix-port-only quirk ... addr[0] was a raw int (a sockaddr struct byte)"; line 1493: "real hardware (always a tuple)". legacy captive_dns.py has no guard. Sources at v1.29.0: rp2 `recvfrom` gives a (str, int) tuple (extmod/modlwip.c:1357-1364, 417-425). The Unix port gives raw sockaddr bytes (ports/unix/modsocket.c:302-330), which the shim turns into (str, int). Without the shim a tuple `bind` raises TypeError, so `addr[0]` is never read. `ipv4_to_int` on any str: `isdigit()` is ASCII-only (py/unicode.c:133) and int is MPZ on rp2, so only a MemoryError can raise. | AP only (the captive DNS runs only on the hotspot); no change on rp2 in any mode | removed | the real-loopback test (test_asy_captive_dns.py:927, answered through the shim) and the new guard `test_run_reads_every_malformed_str_host_as_off_subnet_with_nothing_logged` |
| MemoryError re-raise in `run()` / in `DNSQuery` | screening item; lead decision (note 96) | AP | removed with the `try` (effect kept) / kept | existing tests unchanged |
| UartHazards text | bfc6519 (2026-10-21, lane U) | dev website only, STA and AP | reworded | new FRAM assertion in the twin hazard test |

Where the faults are persisted: asy_uart_comm.py:516-518 `_err` calls `err_s`; :804 calls `wrn_s`. These reach `_store_err`, then `_write_through`, then `fram.write_into` (asy_print_log.py:202-232, 329-355). dev.toml wires `fram_target = "fram"` on both instances.

Seen failing first:
- The 6dabd9b test file against the new src: `test_run_ignores_source_address_that_is_not_a_valid_ipv4_string` fails at :532. Its int row hit the 3 s pause, so that row pinned exactly the removed branch.
- Guard bite (a scratch `ipv4_to_int` with no `isdigit` check): the new test fails with "a malformed str host reached the catch-all: [(23, 'E')]".
- FRAM assertion written to expect no entries: it failed with initiator [E85 REENTRANT, E81 NO_ACK] and responder 10 slots alternating W56 CMD_DECLINED / E80 FRAME_INVALID. Those are now pinned.

Decisions (agent, 2026-10-22):
- The int row is dropped from that existing test; its assertions are unchanged.
- The uart test comment "no error logged" now reads "no webserver error", which is what it asserts.
- I did not run the whole `npm test`. I ran the 4 vitest files that render dev's generated definitions, one per process; no JS test checks description content.

Checks:
- captive DNS: 66/66 at -1 and 32768.
- uart_link: 22/22 at both stages.
- sensortask integration, all 6 devices × 2 stages: green, no failures (only skips).
- Zero memory markers in every run.
- mpy-cross: 2950 → 2814 bytes (S/u35/laneO/mpy/).
- ruff clean; mypy main (both forms), twin and host passes clean.
- 17 scans: 878 passed.
- 41 tests_scripts readers: green, except test_twin_record (2 failed, stale runner_sha256 records, expected).
- 4 vitest files: green.

Times (head vs base, -1/32768):
- captive DNS: 25.60/25.64 s vs 25.59/25.60 s.
- uart_link: 68.35/89.76 s vs 68.36/90.27 s.
No growth.

Scan findings:
- Class 4, a fake answering in a shape no port produces: test_asy_captive_dns.py's int row, removed. The inner swallow is gone too, so anything unexpected is now logged.
- Class 7: the old website text hid the logged faults; fixed.
- Class 2, new, dev only: one hazard run fills UART_resp's 10-slot FRAM ring and overwrites older history; the ErrCount header still counts everything. This bears on CLAUDE.md's rule to read the FRAM logs before clearing them.

For D: the try's removal makes no SPEC sentence stale; F.7 rows 1-2 (SPECIFICATION.md:7167-7168) already say this. SPEC A.8 at :1116-1122 is still true but could add that the provoked faults land in both FRAM logs, along with the ring-fill fact.

Runs (logged in RUNS.md): mprun 6568, run2 8932 and run3 13241 all finished with rc=0. The invalid runs inside them were superseded and deleted. Logs are in S/u35/laneO/.