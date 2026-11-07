K3 (tests/, 38 files, 39 blocks): commit c8940f7 on audit/u35-k3, worktree S/wt-u35k3, parent bc0d77b. Not pushed. Nothing is uncommitted.
Result: `show.py 120` on my 38 files prints TOTAL 0 (it was 39). `verify.py` ends `CODE-CHANGED FILES: 0`, saved at /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/laneK/k3/verify.txt. In measure.py at 120, the only tests/ entry left is tests/_sensortask_scenarios.py:477, which is lane V's file, not mine.

Blocks by kind:
- Rewrapped, same line count (9): _coverage_runner, _uart_comm_hazard_common:24, neopixel.py, notification_service:1208, launch, timer_pool, uart_link:496, wifi_modes:222, shared_helpers.
- Rewrapped across one extra line (4): allocation_budget, hot_replug:146, driven_time, write_counters.
- Tightened (8): construction_scenarios ("digital-twin-tier"→"twin-tier", dropped "real"/"own", "- the export is"→": it exports"); asy_scd30_driver ("Unit + integration tests for X (src/). Module-level tests exercise…Integration-level" became "Tests for src/X. Unit tests run…Integration"); bus_hazard:508 (inside the owner paraphrase, "while concurrent bus load is in flight"→"under concurrent bus load"); scd30 (dropped "own", +1 line); neopixel_wifi ("(and the patterns' sleeps)"); uart_comm_hazard:1394 ("and every"→", every", "so the"→";"); fake_time (more under Moved); udp_socket (more under Moved).
- Split, 13 blocks, text kept word for word unless named:
  - _fram_chip_fake: what the fake is / WEL citations and fault knobs
  - wire_trace: the traces / the restructure contract / the changes since (3 parts)
  - webserver_service: the suite and its Part A.8 pointer / response shapes and lifecycle doubles
  - bmp3xx: transaction logic / calibration round trip
  - isl29125: transaction logic / INT-pin scheduling
  - isl29125_autorange: what is tested / why only the twin can prove it
  - network_neopixel: neopixel.py's shape / network.py's WLAN / the boot test (3 parts)
  - run_generic_integration: what is tested / where every device's boot and the soak check live (its parentheses became a sentence)
  - bus_hazard:975: what the helper does / what it returns
  - fram_integration: the chain / the E.4 pointer
  - notification_neopixel and notification_scd30: what is wired / what is mocked or exercised
  - notification_scd30_sgp40 and notification_sgp40: what is wired / what the gap or mocking is
- Moved, each into the same file beside the code it explains (6):
  - _fake_time: "Every 2**30 clock…Ticks30Time" became a trailing comment on line 10's import. Smaller trims: "The shared"→"Shared", "the test"→"a test", "as given"→"given", "run on it too"→"run on it", "rp2's 8-field"→"8-field", "one timer flag"→"a timer flag", and one comma dropped.
  - _fast_sleep: the check_sleep_ms() sentence went to its comment (new line 21).
  - _cancel_sweep: "Called from a test's synchronous scope." went to cancel_at_each_await()'s comment (new line 148).
  - _uart_link_contract: "Each check takes a factory returning (…)" became a trailing comment on LinkFactory (line 21).
  - udp_socket: "stop_after > 0 ends…" became a trailing comment on line 591.
  - async_harness: the child-interpreter sentence went beside its test (new line 343).
  - Decision (agent, 2026-10-22): I chose a move over a split for _fast_sleep and async_harness because each moved sentence is about one code site and the docstring keeps its line count.
- Line growth for your citation remap (lines added; at the top of the file unless a line is named): _cancel_sweep +1 at 148; _fast_sleep +1 at 21; _fram_chip_fake +5; allocation_budget +1; wire_trace +6; webserver_service +5; async_harness +1 at 343; bmp3xx +3; bus_hazard +2 at 977; hot_replug +1 at 148; isl29125 +3; autorange +4; network_neopixel +5; run_generic +3; scd30 +1; driven_time +1; fram_integration +3; notif_neopixel +3; notif_scd30 +3; notif_scd30_sgp40 +4; notif_sgp40 +3; write_counters +1.

CAPMOVE lines: none. No relay lines written. Silent-failure scan: no code changed, so no new findings.

Checks (logs in /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/laneK/k3/):
- ruff on my 38 files: exit 0.
- The 12 commit checks plus test_device_tomls: 836 passed, 1 failed (exit 1). The failure is test_tunables_register "tags and Part N rows agree": tags with no Part N row in src/asy_config_manager.py:71, src/asy_uart_link_driver.py:51-55, tests/test_uart_comm_hazard.py:1397 and others, plus SPECIFICATION.md:11787 naming a row no file tags. My diff touches no @tunable line (they appear only as context) and no SPECIFICATION.md, so this red was already there. It waits on lane D's Part N rows and the lead.
- The 17 scans on c8940f7: 872 passed, 6 failed (exit 1):
  - test_tunables_register: the same red as above.
  - test_level_containment: fault_storm, ntp_unreachable_load, reader_saturation and watchdog_fault have no E.6.6 row.
  - test_task_inventory ×4: src/asy_uart_link_driver.py:221-222 `_two_initiations()` and asy_neopixel_driver.py:144/202 create tasks outside every task starter, with no C.9 row.
  - None of the three reads tests/ comments, so all six were already there; they wait on the src/ and SPECIFICATION.md owners and the lead.
- Reader test tests_scripts/test_coverage_runner.py (it reads tests/_coverage_runner.py's source), run in unshare/ns_xdg: 19 passed, exit 0, no memory markers.
- Every RUNS.md start/done line is written. I waited on the toolchain record as you asked; it was already present (04:37) before the checks started.

Nothing is left over the cap. nothing of mine is running