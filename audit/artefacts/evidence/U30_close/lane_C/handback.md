U30 lane C final hand-back. All of lane C's steps are done, plus the two items the lead added (the config store's half of the per-episode logging fix, the re-arm comment). Branch audit/u30-c (S/wt-u30c), merged the API branch at c253487; not pushed. Commits: **ce87287, 518afc3, c78c936, 60e1030, afef401**.

**Commits:**
- **ce87287 (R-3/R-4):** a handler that catches a C-stack overflow sets a flag; the supervisor's next pass skips its scan and reboots through the same block the task-budget reboot uses (log entry, command re-check, one feed, starve, `_reboot(code)`). New codes with catalog rows: E25 STACK_EXHAUSTED and ResetReason 20. Every broad handler in the system service now calls `report_if_fatal`. The re-arm helper's comment now states the real boot order (tasks start before timers).
- **518afc3:** two fixes.
  - (R-8) A FRAM-backed log's `reset()` answers False and clears nothing while the FRAM manager is paused.
  - (lead's item) A config store's failed reads (store not valid, unknown key, wrong-typed value) log one entry and one console line per run of failures; a good read or a log reset ends the run. One NTP test pinned the old per-read count; I updated it with the change.
- **c78c936:** two fixes.
  - (R-19) `resolve_ipv4()` returns (address, cause), cause ∈ DNS_RESOLVED / NOT_SENT / NXDOMAIN / FAILED, and checks its own send. NTP logs two new codes, E73 NTP_DNS_NOT_SENT and E74 NTP_DNS_NXDOMAIN; every other DNS failure stays E67. No new state. Resolver stubs in the integration tests and the bench file are updated.
  - (R-13) Out-of-memory errors while building the DNS query or arming a 1 s tick timer now print their text through `console()`.
- **60e1030 (R-6):** new `tests_scripts/test_fatal_report_sites.py` checks every broad handler in src/ and the generated modules. `report_if_fatal` added to every broad handler in base_classes, config_manager, api_response and ntp_client. `report_unretrieved` is exempt by name.
- **afef401:** the two slowest new tests made cheaper (in-memory FRAM fakes; the old single-server NXDOMAIN test folded into the new one).

**Steps with no code:** R-12 (that message already prints through `console()`, `asy_print_log.py:136`), R-24 (the default stands), R-15 (landed in C1), step 33's build-the-schema-once (already present at `asy_base_classes.py:486`).

**Deviation:** the C1 commit message's "a boot-time arm failure now leaves one E17" is wrong for the generated boot order, where the woken task already logs it; the helper covers an arm that fails while the task is down.

**Seen failing first:**
- Fatal-report check: 116 findings at BASE.
- C-stack reboot tests: "never escalated" / AssertionError.
- Paused reset: RAM was cleared (`test_asy_print_log.py:671`).
- Config store: one entry per read instead of one per run.
- Resolver and NTP tests: import error, then 22 failures in the NTP file.
- Tick-timer test: no line printed at level 0.

**Bites:** removed the post-entry command re-check; dropped NXDOMAIN detection; counted a failed send as sent; made a send reset the cause; made the DNS out-of-memory line level-gated; removed the pause check. All caught.

**Red checks:**
- `test_fatal_report_sites.py`: 97 findings, all in other lanes' files (0 in generated modules). Red until W1 by design.
- `test_watchdog_feed_sites.py:353` and `:362`: the bite tests' text anchors quote the old reboot call. The replacements are in the relay; I verified them green in a scratch copy. The lead must apply them.
- `test_twin_record.py`: hashes stale, as expected.

**Relay lines written:** the feed-site anchors; `tests_hardware/bench/test_reset_reasons.py:178-186` and its device script still expect ResetReason 5 (now 20); `UDPSocket.write_and_recvfrom()` has no src caller left; a residual race for the REGISTER; the facts X needs; the fatal-check counts.

**Scan, all classes:**
- Residual (class 4, new): a pause that starts while a reset's write waits for a lock still loses the cleared ring. Parked in the relay with the proposed fix.
- Class 5, new: after an arm fails while the trigger task is down, the first read can come up to 1 s early, once per episode. Same in STA, AP, Silent, Off and USB; harmless (one early sample).
- Effects per mode:
  - All modes: a recorded overflow reboots with ResetReason 20.
  - STA and AP only: ResetErrors refused during a pause; the DNS causes are STA only.
  - Silent, Off and USB: only the new out-of-memory console lines.
- A recurring overflow at boot becomes a reboot loop that stays diagnosable (code 20, one counted E25 per boot).

**Times, -1 / 32768 (before → after):**
- system_service: 23.8/28.1 → 23.9/28.6–29.5
- ntp_client: 23.9/25.6 → 23.7/25.1
- print_log: 0.33/0.49 → 0.32/0.45
- base_classes: 0.39/0.57 → 0.41/0.61
- dns_client: 0.79/0.81 → 0.87/0.90 (+11%, over the 10% limit): each new resolver exchange costs the product's 20 ms poll; already cut from 6 to 5 exchanges.

**Decisions (agent, 2026-10-20):**
- A failed query build counts as NOT_SENT.
- A log reset ends a run of failed config reads.
- Each escalation's message is named once, so the supervisor keeps a single `_reboot` call.

**Final runs:** 21 files at both stages and 7 driver/storage files at -1 all pass with 0 MemoryError/allocation-failure markers. Also passing: test_sensortask for wozi and dev (90/90), the twin generated-boot check (22 passed), the tests_scripts checks (except the reds above), all four mypy passes and ruff. Nothing of mine is running. Logs are in S/u30/laneC/.
