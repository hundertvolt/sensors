
######## SubagentHandback 2026-10-13T21:03:50.137Z
U24 lane M hand-back. Commit cc8d32f on audit/u24-m (S/wt-u24m, base b76ddb7), not pushed. Nothing of mine is running.
Steps: 2 of 2 applied. Item 1: the five swallows now raise any errno other than the expected one. Item 2: the strict JSON check is now linear.
Errno each site absorbs, confirmed by running each case on the Unix port (S/u24/laneM/errno_probe.py, .log), plus the recv path in ports/unix/modsocket.c:284-325:
- captive_dns `_read_replies` and dns_client `answer_once`: EAGAIN only (an empty non-blocking UDP queue raised EAGAIN).
- webserver_service `_file_or_none`: ENOENT only.
- connections `_can_listen`: EADDRINUSE only. The second listener's bind raised it.
- connections `_refused_or_eof`, both clauses: ECONNREFUSED or ECONNRESET. A closed port gave ECONNREFUSED 5/5; a listener closed with the connect still in its backlog gave ECONNRESET 5/5.
Deviation: EPIPE is not in this build's errno module (py/moderrno.c:38-60), and it was never raised in 10 runs, so the rule names only ECONNREFUSED and ECONNRESET. The code comment says why EPIPE is left out.
Strict JSON: the check scans the body's UTF-8 bytes (a str's len() and index are O(n), py/objstrunicode.c:116-117, 164-186). Public names, signatures and messages are unchanged, and offsets still count characters, so no wording changed. Invalid UTF-8 is still refused (a UnicodeError, which is a ValueError, py/objexcept.c:364). Added to test_strict_json.py: raw non-ASCII valid and malformed cases, a check that offsets count characters, and a check that the scan reads bytes, never a str.
37 KB body, before → after:
- gc -1: check 2998 → 31 ms, strict_loads 3137 → 33 ms; non-ASCII body 3266 → 31 ms.
- gc 32768: check 3022 → 57 ms, strict_loads 2849 → 58 ms; non-ASCII body 3203 → 59 ms.
- For comparison json.loads takes 1-4 ms. Linearity: 40/80/160 KB bodies take 34/83/138 ms.
Seen failing first:
- S/u24/laneM/swallow_probe.py on b76ddb7 copies: 7 FAILs across the 5 helpers (6 except clauses). Each turned an injected wrong errno (EBADF, or a real EISDIR) into its expected answer: False, "timed out", None, False, True, True. On the new code: 15/15 pass.
- test_strict_json.py:113 (`test_the_scan_indexes_bytes_never_a_str`) failed on the old helper, which handed it str.
- Two guards bitten in scratch copies: :94 by injecting byte offsets (it reported offset 12, not 9), and :54 by rejecting bytes ≥ 0x80. Nothing injected was committed.
Test runs:
- My six files at -1, 32768 and settrace: all green, 0 MemoryError.
- 17 other importers at both stages: the same counts as base_times.tsv. Every failure is the existing "parked", "reset reached without a catch" or "UART poll teardown" kind; none involves the strict check.
Red checks, none caused by me:
- test_decision_vocabulary allow-list shrink (11 stale entries) and test_import_placement _PENDING (stale entries). Both texts were already gone at b76ddb7; these wait on the lead (U2's list).
- test_tunables_register waits on X. Note: U2's `l1.webserver_leak_rate_max_b` tag moved from :2697 to :2701 (4 lines added above it).
- mypy main pass: 27 errors in 9 driver-test files, identical on b76ddb7 (F's wave-2 consumer list). Twin pass: clean. Ruff: clean.
- The other 10 checks pass (pre-commit 12 plus test_twin_never_needs_tests_on_its_path).
Scan, all classes:
- Class 4, "a fake answers where the OS raises" / "a swallow hides an early raise": the five sites, fixed here (new).
- Inherently safe:
  - captive :979, dns :151: the AssertionError is not caught.
  - dns :728, connections :942: they absorb only the test's own cancel.
  - connections :287: re-raises.
  - dns :251: catches ValueError only.
  - `_refused_or_eof`'s wait_for timeout propagates (asyncio TimeoutError is an Exception, extmod/asyncio/core.py:22).
- Also checked, no finding: floors (bitten), stale generated tree (rebuilt), ports (own namespaces), aborted or incomplete files (summary lines present).
Facts owed:
- X: add to SPECIFICATION E.2 (or the :5348 F.1 paragraph) that tests/_strict_json.py scans UTF-8 bytes in linear time because str len() and index are O(n) in MicroPython, that offsets count characters, and that invalid UTF-8 is refused. No @tunable added.
- Lead: no allow-list lines retired by me. U2's g3 byte-for-byte workaround could now go back to strict_loads.
- Y: none.
After-times, none more than 10% over base:
- webserver_service 12.76 / 13.96 / 38.4 s (U2: 12.88 / 14.53 / 37.8).
- connections 1.23 / 1.46 / 1.37 s (+1.8% / +3.5% vs base).
- captive_dns, dns_client, strict_json: flat or faster.
- sensortask_* are faster, e.g. wozi 36.9 → 33.8 s (-1) and 55.1 → 49.8 s (32768).
Runs:
- batch.sh m1, pid 3695: rc=0.
- mypy: main pass twice, rc=1 (the existing 27 errors); twin pass rc=0.
- 13 tests_scripts checks: 10 rc=0, 3 rc=1 (the existing reds above).
- Short probes all exited.
Logs: S/u24/laneM/ (runs/, the probe logs, bite_A/B.log, strict37_before/after.log, mypy_*.log).
