U31 lead block L1 FINAL
Branch audit/u31-l1 (S/wt-u31l1), from 996a252, head 6819a40. Nothing pushed, nothing uncommitted. rebuild.sh rc 0. The before-timing worktree S/wt-u31l1b is removed.
Commits: 4d975ed (item 1), 143a555 (item 2), 6819a40 (item 3).
1. Applied. tests_scripts/test_watchdog_feed_sites.py: the 2 `no_fail = False` bites are re-anchored at 24 spaces and the escalation-feed bite at 20. I also re-anchored test_an_escalation_through_a_command_path_fails at 20 spaces; it was matching only as a line suffix. A script checked every `_edit` anchor in the file: each matches exactly once, and each indented one starts a line. The file is green (22 passed), so each bite fails the guard it targets again.
2. Applied. In src/asy_system_service.py `_supervise()`, `except MemoryError as e:` now sits beside TimeoutError and logs `self.pr.err("Reboot entry wait could not start:", e)`. That is the same form as the timeout branch and as `_reboot()`'s and `_request_shutdown()`'s handlers, so the gates read str(e). After it the code feeds, starves and calls `_reboot()` as on a timeout. wait_for allocates its generator, two Tasks and the `_run` generator (extmod/asyncio/funcs.py v1.29.0). It also re-raises the entry's own exception, so a MemoryError the entry write lets out now takes this path too. Effect per mode: STA, AP, Silent, Off and USB behave alike. On a full heap at an escalation the reset now arms with code 20 (stack) or 5 (budget). Before, it logged one E42 and the watchdog reset with code 2. The console line shows only at level ≥ 1, i.e. on a USB console.
3. Applied. tests/_fast_sleep.py records `(task, seconds, int given to sleep_ms or None)` and adds `ms_of(task)`. Moved onto it:
- wifi `_MsSleep` (deleted; its 7 users use FastAsyncSleep)
- SCD30 `_SleepForms` (deleted)
- the UDP backoff test, which now runs `_connect()` to its end with no stop_after
- the three readers of the record (scd30, sgp40, webserver_connections ×2) take the third field
Kept local:
- UDP `_RecordingAsyncio`: `_record_ready_sleeps` needs real waits against a wall-clock deadline and stop_after for a wait with no deadline; the queued-datagram test asserts real elapsed time.
- DNS `_InstantSleepAsyncio`: it replaces only the module's own name, so the fake's `sleep(3600)` park stays a real wait. A process-wide fast sleep would turn it into extra failures and a racy backoff series.
- `_BatchWaits`: left as it is (it lets every wait run).
Memory: each record grows from a 2-tuple to a 3-tuple, +1 GC block (32 B), at most 16 KB per instance at CAP. Every user shows 0 memory markers at both stages.
Seen failing on 996a252:
- the new system test: "the reset task never ran" (`_reboot()` never reached)
- the new shared-helper test (test_fast_sleep_keeps_the_form_each_wait_was_asked_in), run on the old _fast_sleep: "AttributeError: 'FastAsyncSleep' object has no attribute 'ms_of'"
Bites (scratch copies, nothing committed), each switching one wait to sleep() in seconds:
- UDP backoff → `AssertionError: ([], [0.5])`
- SCD30 response wait → `(<Task>, 0.05, None)` first
- wifi on-phase → 3 pattern tests fail
Checks, rc at -1 / 32768, all 0 / 0 with 0 memory markers. These are the 7 changed files plus the 14 FastAsyncSleep users (twin bus hazard concurrency included) and test_sensortask ×6 devices (91/91 each). tests_scripts: the 17 repo scans in one process passed 870; the 12 commit checks passed 788; the 25 readers each passed in their own process (watchdog_feed_sites, src_sleep_forms, await_depth, generated_boot, boot_contiguity and stripped_image_boots among them). ruff: clean. mypy main pass (no args, and src tests device_scripts), host pass and twin pass: clean.
Red: test_twin_record "changed since their twin run was recorded" (sha256 / api_sha256 drift; expected, the lead re-records).
Times, before → after (-1 / 32768):
- system_service 24.49→24.59 / 25.78→25.76
- wifi 24.45→24.42 / 24.83→24.75
- udp 7.22→7.13 / 7.22→7.22
- scd30 22.20→22.13 / 28.71→28.78
- sgp40 8.16→8.02 / 8.77→8.94
- webconn 1.20→1.21 / 1.25→1.25
- shared_helpers 0.42→0.44 / 0.45→0.46 (one test added)
- test_sensortask: every device within ±1.2 %
- watchdog_feed_sites (pytest): 12.85 s while red → 13.09 s green
Nothing is over 10 %.
For the lead: Part N's `system.escalation_entry_wait_ms` row says "on a timeout the feed, the starve and the reset follow". It should now read "on a timeout or a MemoryError". No new tag.
Decisions (agent, 2026-10-21):
- The command-path bite was re-anchored at its whole line too.
- The new test raises only the wait bounded at `_ESCALATION_ENTRY_WAIT_MS` (every other wait_for_ms runs as shipped), uses `_ExhaustionError` (worded clear of both markers) and runs at level ERR so the cause line is recorded.
- The record is a 3-tuple rather than a parallel list.
RUNS.md: before (rc 0), chain1 seen+bites (rc 0, the expected fails), after (stale generated tree; the src change needed a rebuild, then a re-run), after2 (rc 0), ts (rc 0 but twin_record).
nothing of mine is running
