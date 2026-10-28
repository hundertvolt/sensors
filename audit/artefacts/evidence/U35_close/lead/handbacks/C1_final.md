C1 hand-back (lane C, branch audit/u35-c, worktree S/wt-u35c, base f3fff0e). Nothing uncommitted; nothing of mine is running.

**Commits:** <CORE> 3700186, <SWEEP> 22ed989, <NTPF> 3c3166b (all three relayed under ## C), then feae592 (two scan fixes in the same helpers, no API change). C2 starts from feae592.

**Steps:**
- Applied: 32+97 (CORE), 36 (SWEEP), 57 (NTPF).
- Check-only, all landed on the base at the cited lines:
  - 30 `FastAsyncSleep(clock)`; 31 Ticks30Time :20-45; 38 harness :91/:95-96/:223/:234/:248/:253/:22.
  - 50 ntp :1266/:1306/:1337/:1344/:1356/:1399/:1407/:375/:93-108, invalid-addr tests gone.
  - 51 fram_driver :1557-1572/:1608/:1694 (no noqa)/:1713.
  - 54 ntp :1741/:1831/:88-96/:1780/:1852/:1870/:1899/:1923.
  - 63 udp :84-85, no `wait_time_ms`, withdrawn IDs absent.
  - 68 wifi: `_release_wifi_lock` gone, :1684-87/:1775/:2469, parks :861/:1380/:1417/:1421.
  - 69 wifi :3152/:3960/:4668. :1593-1694 builds no second client, so there is nothing to change for the shared WLAN.
  - 70 :3950-53/:3977/:66/:82, no `# ====`.
  - 72 no `logger=`, src :412, tests :1015/:1695.
  - 115 :119/:1871/:1894/:2086-87/:2161-2188.
  - 117 :2279-81/:3191/:3027, new tests :2285…:2568, fold :1624, no stale wording.

**API, as C2, N1 and Y4 will call it:**
- `DrivenTime(*modules, now=0, strict=False, sleeps=False)`: with `sleeps=True`, each module's `time` and `asyncio` are swapped for the block. The shim's `sleep`, `sleep_ms`, `wait_for` and `wait_for_ms` run on the clock; every other asyncio name is the real one.
- `await clock.elapse(ms)`: the packet's async advance. Wakes each sleeper at its own deadline, in order.
- `await clock.jump(ms)`: moves at once; every passed sleeper wakes once.
- `await clock.run_until(cond, limit_ms) -> int`: returns the virtual ms taken, or fails naming the virtual time reached.
- `clock.wakes() -> list[int]`: the parked wake times, earliest first.
- `clock.advance(ms)`: the old synchronous move; it now also releases a due driven sleeper (late, never lost).
- Bounds: `DrivenTime.ROUNDS = 1000` (busy-loop cap), `DrivenTime.SLEEPERS = 64`.
- `cancel_at_each_await(build, start, invariants, *, max_steps=200, turn=None, teardown=None, endless=False) -> int`, plus `assert_unlocked(**locks)` and `SocketLedger(*modules)` (`.assert_closed()`, `.still_open()`).
- `FakeNtpServer(port, *, poll_ms, poll_tries).serve_once(reply) -> bool`: True when the request was taken (answered or dropped), False when the budget ran out.

**Seen failing first:**
- test_driven_time: all 15 cases on the base (`sleeps=` TypeError at :39).
- The sweep tests: ImportError before the helper existed.
- serve_once: shared_helpers :541 and :552 against the None return.
- Scan fixes: the 2**29 sleep parked until run()'s 5 s bound fired; the teardown's OSError replaced the lock failure.

**Bites (12, all caught; nothing planted committed):**
- elapse: n+1 woken early, and n left parked.
- run_until: limit+1 accepted, and limit excluded.
- jump: ms-1.
- wait_for_ms: bound +1 and -1.
- Sweep: invariants not called, a blind ledger, a no-op assert_unlocked, the swallow check removed, the turn count off by one.

**Red checks:** none. ruff clean; mypy (no args, and `src tests tests_hardware/device_scripts`) at 0; the pre-commit tests_scripts checks plus the readers import_placement, microtest and radio_shape_corpus: 829 passed.

**Runs** (RUNS.md pids 4878 and 19750, both rc 0):
- Every importer of `_fake_time` and `_ntp_frames` (19 files, the 9 DrivenTime ones included) green at -1 and 32768, with zero MemoryError and zero "memory allocation failed".
- Head times at -1/32768: ntp 24.0/24.4, wifi 24.5/25.0, system 25.1/26.8, scd30 22.2/29.4, bmp3xx 13.8/13.9, notification 19.1/19.1.
- test_driven_time, after-only: 0.05/0.05 s.
- test_shared_helpers, clean base/head pair: 0.45→0.445 at -1 and 0.475→0.505 at 32768. After feae592 the re-pair was noisy on a loaded host (0.52→0.66 at 32768, one 0.84 outlier). That is under the 0.5 s bar.

**Decisions (agent, 2026-10-21):**
- Async advance is named `elapse`, so the 9 importers' synchronous `advance` stays.
- The opt-in is the `sleeps=` keyword; there is no install() method.
- "Runnable" is the run-queue head that is due by the real clock, not `peek() is None`. Otherwise a `run(coro, limit)` never settles.
- `wait_for` is funcs.py's own algorithm with its sleep parked on the clock, so a coroutine that swallows its cancel behaves as on the board. A zero bound calls the real `wait_for_ms`.
- ROUNDS and SLEEPERS are left untagged, like `FastAsyncSleep.CAP`.
- The sweep self-tests live in test_shared_helpers.py.
- The sweep has keyword-only `turn`, `teardown` and `endless` beyond the packet's signature.
- A dropped request counts as served.

**Scan findings:**
- New, fixed in feae592: a fake answering where silicon raises (the driven sleep and bound took 2**29 ms or more; rp2 raises OverflowError).
- New, fixed in feae592: a hook that raises (a failing teardown masked the count's own failure).
- Step 57: a None result conflated with "served".
- Covered: `_run` dropping the result after a timeout mirrors funcs.py.

**Modes:** test-only changes. No `src/`, generated or firmware change, so STA, AP, Silent, Off and USB are unaffected on every device.

**Facts owed:**
- C2: a sweep `turn` must be shorter than the path's shortest driven sleep. Otherwise elapse's settle runs past that await and it is never a cancel point.
- R-2: C2 deletes webserver_connections' `_DrivenClock` (virtual seconds) for `DrivenTime(sleeps=True)` (ms).
- The serve_once bool is discarded outside every lane at tests/test_ntp_fram_system_integration.py:171 and tests/test_ntp_wifi_dns_integration.py:515. Both assert the sync afterwards, so a False is caught there.
- No allowlist rows orphaned; no tunables added.
