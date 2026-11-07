U31 lane C block C3 FINAL
Branch audit/u31-c (S/wt-u31c), head daa589b, nothing uncommitted, nothing pushed. Commits: fbd0f77 "the supervisor records its own fault, bounds its escalation entry, and the uptime re-arm prints once" (src/asy_system_service.py, tests/test_asy_system_service.py +3 tests); daa589b "the boot scenario pins that no setup unit waits but a UART link's boot drain" (tests/_sensortask_scenarios.py).
Steps:
- OF-26 (R-9), applied: `_supervise()`'s loop sits in `try`. `except Exception` runs report_if_fatal(e), then one SYSTEM E42 "Supervisor ended with exception:". The task ends unfed, so the watchdog resets as code 2. Cancellation passes through.
- OF-222, applied: the escalation's entry write (both branches) is `asyncio.wait_for_ms(entry, _ESCALATION_ENTRY_WAIT_MS)`. On TimeoutError: one console line, then the feed, the starve and `_reboot()`, which records 20 or 5.
- OF-29 system half, applied: `_status_loop()`'s re-arm passes `quiet=reported`. The helper (`<CORE>`) was C1's.
- Step 14: landed. test_reset_reasons.py `test_the_supervisor_escalation_reboot_is_attributed` checks code 5 and the entry, in both modes. Nothing was left undone for R-17; not edited.
- Step 17 M.SRC_CORE.016: A.U31.07 (escalation inside the scan, fed once) and A.U31.17 (`sleep_ms(1000 // len(task_starters))`) landed.
- Step 27: A.U31.07's per-pass bound landed (`ends_logged = min(k, -(-(budget + 1) // increment))`). A.U31.03 applied, with one deviation: it is not "every wait 0". R-25's premise is wrong: on dev, both uart_link setup()s do a boot drain (`asy_uart_comm.py` `_drain`) of 5 × 2 ms polls. So each wait must equal its bus's `poll_wait_ms`, and their sum must stay within resync window × `_DRAIN_BOUND_MULT`. Every other unit on all six devices must not wait at all.
Seen failing first:
- OF-29: 30 "Could not arm uptime" lines where 1 is expected.
- OF-26: `assert asy_print_log.fatal_reported() is True` failed (only an UNRETRIEVED traceback, nothing persisted).
- OF-222: "the escalation never reached _reboot() within 6000 ms".
Bites (scratch, deleted):
- 10 ms in SystemService.setup() → "setup unit sysfunct waits 10 ms".
- sleep(0.005) in UARTLinkDriver.setup() → "setup unit uart_link_init waits 5.0 ms".
Checks, rc at -1 / 32768 (all both 0): test_asy_system_service 176/176; test_asy_base_classes 190/190; ntp_wifi_dns 13/13; ntp_fram_system 12/12; test_sensortask ×6 devices 91/91.
- tests_scripts: lane list 730 passed, 4 failed; the 17 repo scans 869 passed, 1 failed; 48 readers plus test_await_depth, one per process, all green except the reds below. collect-only, host mypy (303 files), both main mypy passes and ruff: clean. Zero MemoryError or "memory allocation failed" in any log.
Red:
- test_src_sleep_forms: 25 sites (expected until the wave-1 merge).
- test_tunables_register: "src/asy_system_service.py:68: system.escalation_entry_wait_ms is tagged but has no SPECIFICATION.md Part N row" (the lead's).
- test_watchdog_feed_sites, mine, file outside my set, waits on the lead: three planted bites anchor at the loop's old 16-space indent, and the try now puts it at 20. Failing: test_an_own_feed_outside_the_sequence_fails :296 and test_a_feed_inside_the_supervisor_scan_fails :341 (IndentationError at asy_system_service.py line 523), and test_a_dropped_escalation_feed_fails :347 ("the anchor is not unique: '                self.feed_watchdog()\n                self._force_watchdog_starve = True\n'"). Fix: re-anchor at 20 spaces. A wrapper method instead would break test_await_depth's `SystemService._supervise` top.
Part N tag (new): `system.escalation_entry_wait_ms = 1200` at src/asy_system_service.py:68 (`_ESCALATION_ENTRY_WAIT_MS`). Relation: 2000 + 4 entry writes + it < wdt.timeout_ms.
Relay lines I would write (## C): "C3 FINAL fbd0f77 daa589b"; the tunables and feed-sites reds above.
Times (base → after, -1 / 32768): test_asy_system_service 23.41 → 24.63 (+5 %) / 24.76 → 25.79 (+4 %); test_sensortask[dev] 45.27 → 45.34 / 53.19 → 53.54 (base_times.tsv has no test_sensortask rows, so I timed dev before).
Decisions (agent, 2026-10-21):
- The bound is 6000 / 5 ms (Part N system.scan_budget: five entry writes in the 6 s after the sleep; a loaded chunk write measured 627-700 ms). It covers both escalation branches.
- A timed-out entry stays in RAM only; the reset record is its persisted trace.
- The UART boot drain is the one wait allowed in a setup unit.
- The recorder passes every wait through unchanged.
Facts owed:
- D: A.7 and `boot.setup_unit_stretch_ms` must name the UART boot drain.
- D: CLAUDE.md's `UartLinkExerciser` is really `UARTLinkDriver` (src/asy_uart_link_driver.py:43).
- D: F.1/C.9.1 gain the supervisor-fault entry plus code 2; F.3/system.scan_budget gains the bounded entry.
- Lead: test_import_placement.py:50,52 list duplicate function-level `asy_system_service` imports (scenarios :468, :1572). Module line 57 already imports it, so both the imports and those rows could go.
Left (scan finding, class 6, heap near full, every mode): wait_for_ms allocates two tasks. A MemoryError there now ends the supervisor through its top catch (E42, code 2) where the escalation could go on to `_reboot()`. Proposed: catch MemoryError beside TimeoutError at that wait, with a test seen failing first. Rest of the silent-failure scan over lane C's files: no other findings.
Modes: STA, AP, Silent, Off, USB alike. The changes act only on a supervisor fault, an entry write held past 1.2 s, or an exhausted alarm pool (USB at level ≥1 loses the per-second re-arm line). daa589b is test-only.
nothing of mine is running
