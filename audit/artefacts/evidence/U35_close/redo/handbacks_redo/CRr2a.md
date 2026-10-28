CRr2a hand-back, saved by the lead from the message it sent (2026-10-27). Commit 6416b3b2 on audit/u35-crr2 (on 6a0ebdbb).

U35 lane CRr2a hand-back (stopped at a seam past 80 tool calls). After the 00:32 restart nothing of mine was running and the worktree was clean at 6a0ebdbb. I had not edited or run anything yet, so nothing needed re-running.

**Commit:** 6416b3b2 on audit/u35-crr2 in S/wt-u35crr2. Not pushed; nothing uncommitted.

**Counts (review_rows.py):** 8,473 rows: weak 12, CRr2 167 (178 at base), fixed 21, justified 73, biting 8,200. `--check` rc=0; redflags `--self-test` 22/22 pass. review_rows.py now reads a device script's verdict from review_verdicts.json key `tests_hardware/device_scripts/<f>.py::<stem>` → `"ds_facts": [verdict, reason]`; without one the row stays CRr2.

**Item 2, all 5 named rows fixed** (new `error_log_helpers.assert_module_logged_one_code`: one used slot of kind+num, counted N times, or ≥1 when events=None):
- FRAM CS hijack: `errnos.count(54) == 1`, the driver's one entry per loss (src/asy_fram_driver.py:255-256).
- Hotspot malformed head: W HTTP_BAD_HEAD alone, counted once.
- Oversized body: W HTTP_CALL_TIMEOUT alone, counted once. A 413 logs nothing (tests/test_asy_webserver_connections.py:790-803), and a body that never arrives is one entry (tests/test_asy_webserver_service.py:4338-4346).
- Both NTP blocks (network_resilience, wifi_networking): E NTP_NO_REPLY alone, read before the clear. events=None, because the count is the attempts the block met. The "legitimately logged" seed comments are gone.
- UART echo: `total` is an int > 0 and `intact == total`.

**Item 1, re-found and re-landed:** CR3's 6 rows, 7 assertions, all fixed:
- cross-device: reset_sibling_reads > 0 and heater_off_sibling_reads > 0;
- bmp3xx: reset_window_reads > 0;
- fram rw: baseline_read is True;
- reset_reasons ×2: no_reset_after_ms absent;
- uart ring: `_setup_ok(facts, "rxdmae_setup")`.

**Bites:** 14/14 on synthetic output or errcount; each vacuous case passes HEAD's test and fails the new one, each healthy case passes both (S/u35/laneC/crr2/bites_seam1.out).

**Twin:** twin_bus has 15 passed and 3 failed; twin_uart has 9 passed and 7 failed. Every failure is a case twin_record.json's reason names as silicon-only (INT edge, held SDA, CS hijack, disable_irq, sendbreak, DMA soft reset, driver control). The cross-device, bmp3xx and fram rw tests pass on the twin with the new assertions. The other four new assertions are in silicon-only or bench cases, so they have the synthetic bite only.

**Item 1, left open, state:** 84 device-script rows are still CRr2. My extractor (S/u35/laneC/crr2/ds_keys.py) wrote ds_keys.txt and ds_open.txt (165 unasserted keys in 64 scripts, the 6 fixed included); the five conformance probes have no unasserted key.
- Likely fixes: reboot_persist_read.py remove_errno (test_reboot_persistence.py:35 lacks the absence check test_config_float_round_trip.py:24 makes); scratch_remove_errno in isl29125_mechanism_envelope.py:186 and uart_dma_ring_interrupts_off.py:309.
- Likely justified:
  - leftover_errno in 15 scripts: each is followed by os.mkdir() of the same path, which raises, so there is no DONE line. Check each script.
  - fram_raw_dump.py's facts are saved evidence (harness.py:699-700).
  - initialized and seeded_system, as CR3 classed them.
  - heap_* facts and result_note-only facts are diagnostics.
- f-string false flags are still to re-check.

**Item 3:** nothing to fix at this base. The test it names was CE3's addition ("the bus goes down between reset()'s two sessions", CE3_final.md:12); it was lost and has no redo. tests/test_asy_bmp3xx_driver.py has 138 tests and none takes the bus down between the sessions. The bound lands with CE3's redo.

**Item 4:** no. src/asy_system_service.py:753-756 logs W CONFIG_LOST only when the reset reason is neither _RR_CONFIG_RESET nor _RR_COMMAND_INCOMPLETE. tests/test_asy_system_service.py:4306-4307 pins 0 entries for both. The twin's one CONFIG_LOST (scripts/_digital_twin_ci_suite.py:1167-1180) is the reformat case, a provoked fault, class (b). So it is not A.U35.37 (a), and there is no product question. Silicon's log after a commanded reset is read by no test today; CRr2c's logs fact would cover it.

**Checks:**
- lint_direct rc=0; host mypy clean on 309 files (cold cache). The main pass was not needed: no device_scripts file changed.
- `--collect-only`: 201/232 collected (31 deselected by the wear gates).
- Readers and doc checks: 1,291 passed, 2 failed in test_twin_record, both the lead's. One is three un-recorded instruments that are not mine and were red at base (listener_close_leaves_the_pcb_pools, reset_code_loop_end, test_modlwip_listener_close); the other is the hash re-record.
- No MicroPython file changed, so no GC-stage runs and no timing rows. Silent-failure scan: no finding.

**Runs (all in RUNS.md):** the first three runs (twin_bus, twin_uart, collect) exited rc=1 within a second: uvenv's python came first on PATH. I fixed that and re-ran them. Then: twin_bus rc=1 (144 s), twin_uart rc=1 (123 s), collect rc=0, lint rc=0, mypy_host rc=0, readers rc=1, each failure explained above.

**Facts owed:** to the lead: the twin re-record for the 7 changed hardware files; no allow-list row needed. To CE3's redo: item 3's bound.

nothing of mine is running
