U30 lane C, C1 interim hand-back (C1 is done; I've stopped as the brief says).

Commit **475d9ac** on audit/u30-c (worktree S/wt-u30c, made from 5ba138c). I didn't push. The hash and the API summary are written under `## C` in S/u30/relay.md.

**What C1 adds (20 files):**
- `asy_print_log.report_if_fatal(e)` and `fatal_reported()`, with `_STACK_EXHAUSTED = const("maximum recursion depth exceeded")` and `_fatal`. The module docstring's line 1 now names the flag. `tests/microtest.py` clears `asy_print_log._fatal` after every test.
- `SystemService.is_reset_decided()` reads one new one-way flag, `_reset_decided`. It is set at a command's acceptance (beside `_feed_owned = True`) and at the start of the escalation block, before the entry write.
- `RouteSources` has a new 5th field, `is_reset_decided`, after `system_cmd`, typed with the new alias `ResetDecidedFct`. Codegen emits `is_reset_decided=sysfunct.is_reset_decided`. All 7 test construction sites are updated (the system-service rig passes the real accessor), plus `_ServiceKeywords`. The webserver does not use the field yet; that is lane N's change. `test_buildgen_generate.py` and `test_setter_contract.py` read the call by keyword, so they needed no edit.
- `_FramManager.get_pause()`, added to the 3 named fakes and to my own fakes in `test_asy_base_classes.py` and `test_asy_print_log.py`. Without it mypy fails; I checked this by removing it from one fake.
- The base half of the re-arm fix: `SensorReader._rearm_timer()` plus a `_timer_reported` flag. A failed arm is now persisted exactly once, then re-armed, and the base `_trigger_loop` uses it. Effect in every mode (STA, AP, Silent, Off, USB): an alarm-pool exhaustion at boot on BMP3XX/ISL29125 now leaves one persisted E17. The other C1 changes alter nothing at runtime until lanes N and S2 use them.
- The launch test now compares the twin's stack fault with `src_const(asy_print_log, _STACK_EXHAUSTED)`, and `_recursion_message()` is gone.

**Seen failing first:**
- print_log: the new tests failed on import (`fatal_reported` didn't exist yet).
- microtest_hooks: `test_b_sees_boot_state` failed, the flag still set from the previous test.
- system_service: both accessor tests failed with an `AttributeError`.
- base_classes: the boot-failure case persisted 0 entries instead of 1; the re-arm case recorded 1 instead of 2.

**Bites (scratch copies, nothing committed), each caught:** testing the class only; making the flag allocate; making it print; changing the text by one word (caught by the launch test and print_log); setting the decision flag at the sequence's start instead of acceptance; setting it after the entry write; persisting again on re-arm.

**Checks** at -1 and 32768, all green with 0 MemoryError/allocation markers: my tests/ files, `test_microtest_hooks`, the NTP integration files, `test_reset_call_site_invariant`, `test_readiness_gates`, all C1_extra MicroPython files, and as cross-checks the bmp3xx, isl29125, scd30 and sgp40 driver tests. `test_sensortask.py` for wozi and dev passes 90/90. The tests_scripts checks pass: the 12 doc/convention checks, watchdog_feed_sites, counter_steps, readiness_gates, buildgen_definitions/generate/reproducible, setter_contract, exception_handler_contract, suppression_form and digital_twin_generated_boot (22 passed). All four mypy passes are clean.

**Red, expected:**
- `test_twin_record.py` fails in `test_every_entrys_hashes_are_the_current_files` (stale api_sha256). The lead re-records at W1.

**Red, waiting on the lead:**
- ruff reports PLW0603 at `src/asy_print_log.py:409:12` (the step's `global _fatal`). The fix is a pyproject line outside my set, so I didn't add it: `"src/asy_print_log.py" = ["PLW0603"]`, with its comment text, is in the relay.

**Times** (before → after, -1 / 32768):
- system_service: 23.84/28.08 → 23.92/28.77
- webserver_service: 11.54/13.40 → 11.78/14.48 (+8%)
- digital_twin_launch: 8.06/8.13 → 8.07/8.12
- neopixel_driver: 9.54/9.64 → 9.52/9.64
- uart_link_driver: 2.36/2.54 → 2.41/2.60

Everything else is unchanged or under 1 s. Nothing is over 10%.

**Decisions taken (agent, 2026-10-20):**
- The names `is_reset_decided` and `ResetDecidedFct`, following the file's per-role aliases and `is_hotspot_active`.
- The field goes after `system_cmd`.
- One `_reset_decided` flag set at both decisions, rather than reading `_feed_owned`.
- The base re-arm and its tests landed in C1, so lane S2 can use the helper straight away.
- The `(owner, 2026-10-13)` comment is marked "paraphrase".

**Scan of C1's changed sites:** one new, harmless item. After a failed arm wakes the trigger task, the flag stays set, so the first read after recovery can come up to 1 s early, once per episode.

**Facts owed to lane X:** the two new primitives (SPEC G.2/C.7/F.1), the `RouteSources` field (SPECIFICATION.md:915), and `get_pause` on the Protocol.

**Runs:** two RUNS.md entries, batch pid 25493 (rc 0) and digital_twin_generated_boot (rc 0). Nothing of mine is running, and the typings symlink is removed.

Logs are in S/u30/laneC/logs/.
