R2 falsification, written by the agent (Wed Nov  4 14:12:29 UTC 2026)

Tree: S/wt-r2f at 433d53b2 against 8a32d826, arduino excluded everywhere. Ten runs, one after another (S/u35/lead/
<label>.log): r2f_rebuild, r2f_reset_plant, r2f_await24, r2f_tunables, r2f_sleep_plant, r2f_ownbackup,
r2f_bmp_twin_head, r2f_bmp_twin_old, r2f_lint, r2f_dns_bind. Every plant was restored (git checkout, or the backed-up
generated file put back, sha256 checked); the worktree is clean at 433d53b2 and build/twin_board/ (a probe's) is gone.
Pinned sources: /root/pico-toolchain/micropython (v1.29.0), /root/pico-toolchain/pico-sdk (2.3.0).

## Verdicts

1. Loop end - REFUTED (doc part only); the mechanism stands.
   - Stands: buildgen/codegen.py:850 imports reset, :866-867 call record_loop_end() then reset(); all six
     build/generated_src/sensortask_<d>_main.py have one call, line 40, nowhere else; the noautostart entries
     have none. The Ctrl-C arm and the noautostart variant are unchanged (codegen diff).
   - Chip: ports/rp2/modmachine.c:74-79 calls watchdog_reboot(0, SRAM_END, 0); pico-sdk
     hardware_watchdog/watchdog.c:92-114 with pc=0 writes only scratch[4] (:107-109), then triggers at once
     (:65-66). src's record is mem_backup(0) = scratch[0..3] and the phase mem_backup(1) = scratch[5..7]
     (ports/rp2/machine_mem_backup.c:36-40). The reset selects every block but ROSC/XOSC (watchdog.c:53) and
     PSM_WDSEL has no watchdog bit (rp2040 psm.h:275-387), so both regions survive and begin_boot() reads the
     record first (src/asy_system_service.py:138-150): 22, or 10 + phase.
   - Invariant plant (r2f_reset_plant): machine.reset() added to the generated sensortask_dev.py fails
     test_reset_and_bootloader_calls_confined_to_system_service at tests/test_reset_call_site_invariant.py:92.
     Caveat: that file never scans the boot entries (_product_files(), :52-55, lists src/ and the device
     modules only), so a second reset in a *_main.py passes it; the arms are pinned instead by
     tests_scripts/test_buildgen_generate.py:153-157 and behaviourally by tests/test_generated_boot_entry.py.
   - Refuted: SPECIFICATION.md:7006-7010 (F.5.4) still says a friendly-REPL Ctrl-D soft reset "reports the 21 or
     22 recorded before it, or the 10 + p of a loop that ended during boot": after a loop end no REPL starts,
     so that soft reset no longer exists for the autostart entry. The same unreachable path is still pinned at
     L1: tests/test_asy_system_service.py:3666-3679 ("the regions keep the entry's 21 or 22") and :3700-3711.
   - Nothing prints: tests/test_generated_boot_entry.py:114-126 asserts no print and no traceback; the arm
     has no print. Hardware tier: nothing expects a REPL, but see D2 for two new races there.
2. Removals - REFUTED (the idle-check part); the rest stands.
   - git grep (':!arduino' ':!audit') finds no reader of A1-A3, fatal_err, rdy_stuck_high, power_dip,
     displayed, _fram_chip_fake's silent, the 89 s deadline or the launcher's stop file (the runner's own
     --stop-file stays, read by tests_scripts/test_digital_twin_generated_boot.py). 50 removed tests carry "bite",
     2 of them in A1/A3: 48 in 23 files, each file keeping at least one real-case test. Removed non-bite tests are
     knob self-tests, the stop-file and deadline tests, A1-A3, the two loop-end soft-reset cases, and one rename.
   - Refuted, constructed (r2f_ownbackup, a planted test in tests_scripts/test_digital_twin_scenarios.py, since
     removed): scenario a states SGP40 and logs E110; scenario b states nothing but repeats E110 in place
     (counter +1, no slot, SPEC C.7.1's newest-entry rule, src/asy_print_log.py:175-184). Alone, b fails the
     idle check; when the boot's W35 lands in the same window, _own_backup()
     (scripts/_digital_twin_scenarios.py:384-389) sees now[:-1] == before[-1:] == [E110] and excuses b's move:
     printed "R2F True [[], []]" against "R2F False [[], [... 'SGP40': (2, 3, ...)]]". It excuses any repeat of
     the source's previous newest code that coincides with the W35.
3. The seven sleeps - REFUTED (the captive DNS waits); the rest stands.
   - Plant (r2f_sleep_plant): the webserver ceiling case waiting for 3 held connections failed 1.02 s after the
     previous test (log timestamps), at tests/test_asy_webserver_service.py:2144-2160; the file otherwise passed.
   - All 5 wait_for_value() sites and the 4 _wait_until() sites assert the result; the NTP case's
     _attempt_ended() raises after 2 x 5000 ms (tests/test_asy_ntp_client.py:142-145). That is 10 s, not 1 s.
   - Refuted (r2f_dns_bind, a planted test, since removed): the captive DNS "bound" predicate
     `server._udps._sock is not None` is also true after a failed bind. src/asy_udp_socket.py sets _sock at :59
     before bind() at :67, and on OSError _nomem() (:101-103) leaves it set. With the port held, the plant
     printed "R2F (True, False, True)": the wait passed, connected stayed False, and the multi-cycle test's
     verdict `not task.done()` held. So test_run_reuses_same_dns_server_instance_across_multiple_hotspot_cycles
     (tests/test_asy_captive_dns.py:1118-1121) can pass with no bind. This was the same predicate before the
     change; the exact one is `server._udps.connected`.
   - The one-turn waits are ordered by the run queue: push keys are ticks() (extmod/modasyncio.c:115-125), the
     heap is stable for equal keys (py/pairheap.h:29, :89), and the holder is pushed before the test's
     sleep_ms(0), so it runs first. _PROBE_LEAD_MS = 5 (tests/test_digital_twin_run_generic_integration.py:85,
     :648) is the only fixed lead left among the seven; the hazard case's _LISTENER_SETTLE_MS sleep feeds no
     assertion.
4. CI - STANDS. A matrix count of ci.yml at both revisions gives 46 and 34 jobs, the twin job 24 to 12 (6 devices x
   2 stages). timeout-minutes, needs: and if: are identical for every job; scripts/test.sh is unchanged (per-file
   timeout, retry, stdbuf). select() (scripts/_digital_twin_scenarios.py:2381-2384) splits the 67 scenarios as
   66 shared in test.sh's scenarios[<device>] jobs at each job's stage (scripts/test.sh:680, :741-746) and the
   one needs_exclusive_port_53 scenario (:1024) in the twin leg (scripts/run_digital_twin_ci.sh:134-139).
   Device rules are identical on both sides, and test.sh builds every site, so needs_site holds. Margin:
   20 / (10.1 + 0.91 + 2) min = 1.54x, as the row states. actionlint and zizmor are clean (r2f_lint).
   Caveat: the 54.5 s figure is from this x86 host, not the GitHub runner Part N's Sizing rule names.
5. Part N - REFUTED.
   - Counts hold: 192 rows (188 ID, 4 rule); 1,086 rows went from 1,278.
   - Refuted: eight src/ rows went, so "every row for a src/ value" is not kept, and none of them is a single
     test's own value: uart.flash_hold_max_ms and uart.chunk_bytes (src/asy_uart_comm.py:96, :111 at base),
     uart.hazard_quiet_timeouts / _window_timeouts / _recovery_attempts (src/asy_uart_link_driver.py:51-55),
     bmp3xx.reset_settle_ms (src/asy_bmp3xx_driver.py:78), i2c.clear_half_period_us (src/asy_i2c_driver.py:24)
     and spi.cs_settle_us (src/asy_spi_driver.py:20).
   - Also gone: six devices/dev.toml rows (12 tags, :48-74, :180, :191), and shared harness or twin-model
     values that are not one test's own: l2.feed_gap_share_max (every twin run's feed-gap check,
     scripts/_twin_process.py:41, :270), l2.serving_poll_s, l2.kill_reap_timeout_s,
     l2.twin_wifi_connect_delay_s and twin.ntp_responder_*. No buildgen/ row went.
   - The five rule rows' content is in J.6 (SPECIFICATION.md:9820-9846) and F.3 (stall.sync_wait,
     stall.uart_call); the sync-wait rule text itself sits in D.4 (:4780-4783).
   - Literals: no code literal changed apart from mem.max_await_depth 28 to 25 and the sleep constants claim 3
     replaced.
   - Plant (r2f_tunables): tag and literal at 26 against the row's 25 fail
     test_the_tags_and_the_part_n_rows_agree ("Sites list ... '25', the tags say ... '26'").
   - The seven `# source:` comments: the exemption code is unchanged (tests_scripts/
     test_tests_hardware_product_copies.py:47), so nothing passes now that would not have passed at base. They
     disclaim a source instead of citing one, and nothing pins them (the file's :1-3 and :57 describe a cited,
     pinned source).
6. Await depth - STANDS. Plant budget 24 (r2f_await24): exactly one chain fails, "the first, 25 levels"
   (Microdot.handle_request ... PrintLogHistory._write). The fabricated budget+1 test passed. The walk is ast
   only (tests_scripts/_await_depth.py imports ast and buildgen.generate, with no clock). Caveat: the row's Basis
   cites fde57f45, which is not an ancestor of 433d53b2 (SPECIFICATION.md:12049).
7. Carries - STANDS. At base, .what and .relief are only constructed (buildgen/validate.py:1325, :1332); every
   reader takes .ms. SETTINGS_GROUPS is read by codegen.py:599/:748, test_setter_microdot_integration.py and
   test_buildgen_generate.py; _owns_config_store() by generate.py:76. The page-set assertion is at
   test_buildgen_generate.py:470-473 (notification excepted by name). The UART buffer citations match the pinned
   ports/rp2/machine_uart.c: 68/69 are the defines, 372-373/387-388 the floor, 374-375/389-390 the raise.
8. Nothing else changed - REFUTED as worded, low severity.
   - Holds: src/ changes are 20 comment tags plus one trailing comment on _FLASH_HOLD_MAX_MS, so the wire format
     is untouched. No audit IDs, lane or unit names appear outside audit/. No changed comment paragraph is over
     3 lines.
   - Refuted: four non-doc files grew too: buildgen/codegen.py +1, scripts/run_digital_twin_ci.sh +1,
     tests/test_generated_boot_entry.py +2, tests_scripts/test_buildgen_generate.py +5. Among the docs, only
     BACKLOG.md and README.md grew, by one line each.
9. Numbers - STANDS: 332 insertions and 3,745 deletions in 253 files. SPECIFICATION.md goes from 1,589,923 B /
   13,230 lines to 1,128,895 B / 12,143 lines.

## Defects outside the claims
D1 (twin fidelity regression, b315f98b). The BMP3xx twin's EVENT model (por_detected, clear-on-read) went with the
   fatal_err knob, but tests_hardware/device_scripts/bmp3xx_conformance_probe.py:42, :84-85 reads REG_EVENT on
   chip and twin alike. tests_hardware/conformance.py:44-57 compares it verbatim, since C03/C04 are not BMP3XX
   physical keys (tests_hardware/flash/test_chip_conformance.py:114-118). The twin now answers
   C03_por_after_softreset=0 (r2f_bmp_twin_head); the base model answered 1 (r2f_bmp_twin_old), as the chip
   does per DS001 4.3.7, cited by the removed model and the probe. test_bmp3xx_matches_its_twin_fake (:151-154)
   will name that divergence on the bench. The twin also reads 00 for B03, which is unmodelled and pre-existing.
D2 (L4 risk, unverified: no hardware). tests_hardware/bench/test_reset_reasons.py:230-232 keeps
   wait_until(not present) after run_isolated_expect_reset(). That suited the watchdog's late reset; with the
   immediate machine.reset() the board may already be back on USB when the first poll runs. The other
   immediate-reset cases in the file read the next boot directly. Also, reset_code_loop_end.py prints
   raised_in_phase just before the reset, and rp2's CDC write only queues the bytes
   (shared/tinyusb/mp_usbd_cdc.c:102-142), so the fact the test asserts (:231) can be lost.
   tests_hardware/README.md:923 still lists the test as "not yet run".
D3 (stale text).
   - src/asy_system_service.py:94 still says the watchdog reset follows code 22.
   - tests_scripts/test_device_script_watchdog.py:19-20 lists reset_code_loop_end.py among the scripts that
     "starve it on purpose"; it now resets.
   - SPECIFICATION.md:1036-1040 and error_catalog codes 11-15 name only "the watchdog reset or a console soft
     reset", not the entry's reset after an exception during boot.
   - Docstrings still announce removed bite tests: tests_scripts/test_timing_budget.py:3 ("each bites below"),
     tests_scripts/test_error_catalog.py:3, :760, :798, and the bites header at
     tests_scripts/test_fram_chunk_owner_sites.py:181.
Ignored __pycache__ directories from these runs remain in the worktree. nothing of mine is running.
