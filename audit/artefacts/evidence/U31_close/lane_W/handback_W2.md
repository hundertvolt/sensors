U31 lane W block W2 FINAL
Branch audit/u31-w, head a31c4da (from 9aadd93), worktree S/wt-u31w. Nothing pushed, nothing uncommitted. rebuild.sh at 9aadd93 rc 0.
Commits:
- bc27180: src/asy_udp_socket.py, `_RETRY_BACKOFF_MS = const(500)`, and the failed-setup arm now awaits `asyncio.sleep_ms(_RETRY_BACKOFF_MS)`. tests/test_asy_udp_socket.py reads `src_int(... "_RETRY_BACKOFF_MS")` at its 4 edge sites (`src_float` import dropped) and gains test_a_failed_setup_backs_off_with_one_sleep_ms_of_the_shipped_value.
- a31c4da: src/asy_captive_dns.py, `_RECV_FAIL_BACKOFF_INITIAL_MS = const(500)` and `_MAX_MS = const(5000)`, a `recv_fail_backoff_ms` int, `asyncio.sleep_ms()`. tests/test_asy_captive_dns.py gains 3 src_int reads, `_InstantSleepAsyncio` and test_run_recv_backoff_is_asked_in_milliseconds (500/1000/2000/4000/5000/5000, then 500 after a datagram).
Steps:
- Applied: step 17's M.SRC_NET.004 (backoff constants), .007 (ms backoff), .026 (`_RETRY_BACKOFF_MS`) and .027 (`sleep_ms`). The rest of .004/.007/.026/.027 was already in place: codes, imports, the lwIP comment, tuple-only `__init__`, the MemoryError console line.
- Landed, checks only: step 42 (tags at test_asy_captive_dns.py:44-85; the `:952` mirror reads `src_int("_ERROR_RETRY_WAIT_S")`, now :1217). Its `_REPLY_WAIT_MS = 200` has no site: I searched `_REPLY_WAIT_MS|reply_wait|\b200\b` and the only hit is `_STRAY_REPLY_WAIT_MS`. Step 43 is landed as test_run_bind_failure_logs_init_once_and_backs_off (:810). It uses a real blocking socket for EADDRINUSE, not `_RaisingSocketModule`, with the same assertions.
- Step 59 is W3's (twin integration file).
Seen failing first (my new tests, run against the base modules from `git show HEAD:` placed first on MICROPYPATH, nothing committed): the UDP test at test_asy_udp_socket.py:689 `AssertionError: []`; the DNS test at test_asy_captive_dns.py:1381 `AssertionError: []`.
Red checks: test_tunables_register.py::test_the_tags_and_the_part_n_rows_agree fails on "src/asy_udp_socket.py:30: udp.retry_backoff_ms is tagged but has no SPECIFICATION.md Part N row", the same for src/asy_captive_dns.py:40/:42, and "SPECIFICATION.md:11423/:11426/:11427 ... no file carries its @tunable tag". Plus W1's 9 wifi rows. All wait on the lead (R-24). Everything else is green: 17 scans + 5 readers 1705 passed; code_conventions/error_catalog/lint_ceilings/mypy_any_baseline 91 passed; ruff clean; mypy main pass and src/tests/device_scripts pass clean. twin_record not run (expected).
Renamed tags for Part N:
- udp.retry_backoff_s = 0.5 → udp.retry_backoff_ms = 500 (asy_udp_socket.py:30, `_RETRY_BACKOFF_MS` :31)
- dns_server.recv_backoff_initial_s = 0.5 → dns_server.recv_backoff_initial_ms = 500 (asy_captive_dns.py:40/:41)
- dns_server.recv_backoff_max_s = 5.0 → dns_server.recv_backoff_max_ms = 5000 (:42/:43)
- Dependant rows SPEC:11592-11601 name the old `_s` IDs, and SPEC:7331's prose names `udp.retry_backoff_s` (lane D or the lead).
Relay line I would write under ## W: "W2 bc27180 a31c4da (UDP + captive DNS backoffs in ms)".
Times (-1 / 32768): test_asy_udp_socket.py 7.22 / 7.14 s (base 7.21 / 7.22). test_asy_captive_dns.py has no base row, so I timed it on the base modules: 25.58 / 25.58 s before, 25.57 / 25.60 s after. The UDP test ends at its first sleep_ms (via `stop_after=1`) and the DNS test's sleeps cost no real time, so neither adds wall time. Zero MemoryError / "memory allocation failed" in every log.
Effect per mode: every wait keeps its value. STA (the DNS/NTP client setup backoff 500 ms) and AP (the captive DNS bind backoff, and its 500→5000 ms series) no longer allocate a float per pause (asyncio.sleep is `sleep_ms(int(t * 1000))`, extmod/asyncio/core.py v1.29.0). Silent, Off and USB: no change, and no new console line. Silent-failure scan of the 4 files (all classes, these modes plus a task restart): no new finding. The series is bounded and logged, and it restarts at 500 after a restart.
Decisions (agent, 2026-10-21):
- (1) Recorders stay local to each file: tests/_fast_sleep.py is outside my set. The repo now has three similar ms recorders (wifi `_MsSleep`, UDP `_RecordingAsyncio`, DNS `_InstantSleepAsyncio`); a shared one is the lead's call.
- (2) New helpers sit with the section they serve, as every existing helper in both test files does. No whole-file reorder: neither file's helpers are in alphabetical order today, and test_code_conventions only checks src/.
- (3) test_asy_captive_dns.py (marked "check only" in the plan) got the test the plan's seen-failing list asks for, since blocks.md gives W2 "with their tests".
W3 starts from a31c4da: asy_webserver_service.py, its two test files, the twin integration file (:98 `_STA_CONNECT_POLL_S`, `_SteppedWifiAsyncio` caps only `sleep`), then lane W's full checks. Nothing is half-done.
Runs, all logged in RUNS.md, all exited: DNS test 2× before (rc 0), 3× seen-failing (rc 1 ×2 on a MicroPython starred-display SyntaxError I then fixed; rc 1 expected), 2× after (rc 0); UDP test 2× seen-failing (rc 1 expected), 4× stage runs (rc 0); mypy in the background (rc 0); 2 pytest runs (rc 1 on the expected tunables red only; rc 0).
nothing of mine is running
