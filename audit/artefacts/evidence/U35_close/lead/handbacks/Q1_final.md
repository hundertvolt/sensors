Q1 hand-back (lane Q, audit/u35-q in S/wt-u35q, from 1d77560). Commits: 8194466, e50f813, a87d1e9, 5fba3da. Nothing uncommitted, nothing pushed, no relay line written (the brief names none). About 62 tool calls.

**Steps**
- **65, connect half: applied.**
  - 8194466 adds C2b's test half, with its comment reworded for two paths. It is red on its own commit: `AssertionError: cancelled after 1 turns: a socket left half set up`, and the teardown adds "the next connect to a good address failed".
  - e50f813 is the fix: the self-heal moves into a `finally:` of that try. Line count stays at 173, and the header comment's line 55 names the cancel case in place. Udp is then 65/65.
- **Pinned asyncio check (v1.29.0): the await in the finally runs on a cancel.**
  - `Task.cancel()` sets `data=CancelledError` (extmod/asyncio/task.py:176). The loop clears it and calls `coro.throw` (core.py:192-193).
  - `sleep_ms`'s SingletonGenerator has no `throw()`, so `mp_resume` raises the cancel at the suspended await inside the except handler (py/runtime.c:1492-1501). The finally then runs.
  - `_disconnect_locked()` never suspends, so its await completes in that same resume. `Lock.__aexit__` releases synchronously (lock.py), and CancelledError (a BaseException, core.py:18) propagates.
- **mpy-cross compare** (S/u35/laneQ/mpy/compare.txt): 2060 → 2066 bytes, both default and armv6m. Only `_connect` changes: one SETUP_FINALLY, one END_FINALLY, exception stack 3→4. The other 10 functions are byte-identical, line info included.
- **Effect per mode:** latent on every device in every mode today.
  - STA: the DNS/NTP per-request sockets disconnect in their own finally (asy_dns_client.py:174-175, asy_ntp_client.py:265-266).
  - AP: the captive DNS loop disconnects at asy_captive_dns.py:139-142.
  - Silent and Off open no UDP socket; USB is unaffected.
  - The fix also tears down after an exception type the handler does not catch.
- **67: applied (a87d1e9).** `test_cancelling_a_connection_at_each_await_frees_its_slot` sweeps `_serve()` over a static GET. The route's `open()` is shadowed by a recording `_SiteFile`, and the body is three chunks: 20 counts.
  - Invariants: the slot count back to 0, the writer closed once `_serve()` began, every opened file closed. A control serves the whole body.
  - It passed at once, so I bit it three times in scratch copies:
    - release() removed: "cancelled after 3 turns: the held static stream left open". No other test in the file notices this one.
    - slot decrement removed: "…the connection's slot is still counted".
    - writer close removed: "…the writer left open".
- **D.15 module order: applied (5fba3da).** No content change. Both files' helper functions now form one sorted block (the dns form).
  - Checked: the line multiset and the top-level AST node multiset are unchanged, docstrings too. Class members were already in order.
  - Import-time names stay in place: `_head`, `_no_delay`, and udp's 7 arms.

**Decisions (agent, 2026-10-21)**
- Committed the test half red, before its fix, in the brief's order.
- The writer invariant holds only once `_serve()` began: a task cancelled before its first step runs none of its code, so it has nothing to close.
- `_REFUSED_OR_RESET` travels with `_refused_or_eof`, and the two new doubles join the doubles section.
- The importer set is the 19 files that load the module: 5 import it directly, the rest through the shim or the DNS/NTP clients. The 3 `PER_DEVICE` files ran on all 6 devices.

**Runs** (all rc 0, zero MemoryError and zero "memory allocation failed", no retries; RUNS.md pids 5407 and 15332)
- **Paired runs, base → head (2 rounds each):**

  | file | -1 | 32768 |
  |---|---|---|
  | udp | 6.43/6.41 → 5.92/5.92 | 6.42/6.43 → 5.94/5.94 |
  | webserver_connections | 1.21/1.22 → 1.21/1.23 | 1.23/1.23 → 1.27/1.28 (+3.6 %, 0.045 s, one test added) |

  Both are faster than or level with C2b's figures.
- **Importers on the head, both stages:** all green.
  - captive_dns 25.6, dns 0.89, ntp_client 23.7, wifi 24.5, driven_time 0.04.
  - ntp_fram 7.6, ntp_wifi_dns 1.5.
  - twin: clock_jump 24.5, fram 0.6, hot_replug 70.6, ntp 33.3, run_generic 1.4, uart_link 55.0/59.4, wifi_modes 25.7, bus_hazard 149.7/151.4.
  - timer_pool, construction and sensortask_integration on all 6 devices. Elsewhere sensortask_integration skips 8, by design: those tests run on arzi, the first device wiring their drivers.
- **Errors of mine in batch 1, re-run green in batch 2:** I dropped the `asy_` prefix on 4 names (rc 2, file not found). The 3 PER_DEVICE files ran without TEST_DEVICE (RuntimeError).
- Pre-commit before each commit: ruff 0, both mypy main passes 0, the 12 checks 799 passed.

**Silent-failure scan** of my 3 files (classes 1-7; STA, AP, Silent, Off, USB, boot, twin shutdown):
- Class 6, the setup self-heal: fixed (e50f813).
- Covered already: SF-B15 truncation (REGISTER.md:810) and SF-A12 (:825).
- A persistent bind failure is visible: captive DNS logs `_ERR_INIT` at asy_captive_dns.py:124-125.
- **New, for the lead to route (pre-existing, unchanged by the fix):** `_connect()` drops `_disconnect_locked()`'s bool at src/asy_udp_socket.py:76 (class 4). A close failure in the self-heal is never reported, while `disconnect()` returns it to its caller.
- **Fact for the lead:** tests_scripts/test_code_conventions.py:232-243 `_import_time_names` misses defaults of methods in a class body, which run at import time (`_no_delay` is one).

**Red, expected:** tests_scripts/test_twin_record.py, from the `src/` change (not run). No allowlist rows orphaned.

**Q2 starts from:** audit/u35-q at 5fba3da, clean, rebuilt at e50f813 (the commits after it are test-only). Q2 still owes:
- the OF-211 held-responder audit over every socket file at both stages, and its `## D` line;
- the wifi and captive sweeps;
- the lane-final checks: the 17 repo-wide scans, the readers of my changed files, its own files' runs.

Nothing of mine is running.