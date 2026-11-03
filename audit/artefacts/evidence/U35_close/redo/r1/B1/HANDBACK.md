B1 hand-back, written by the agent (Mon Nov 02 23:24:55 UTC 2026)

Branch `audit/r1-b1` in `S/wt-b1`, from the integration head `4516e60e`. One commit: `39f1615b` "U35: the logger records a C-stack overflow at its entry; DebugLevel 0 prints nothing". Not pushed.

## Per item: outcome and its test

1. **C-stack record: one check at each logger entry point (done).** `PrintLog._line()` runs `report_if_fatal()` over
   its arguments ahead of the level gate; `err_s()`/`wrn_s()` run it ahead of `_store_err()`, so ahead of any FRAM write;
   the new `err_nomem()` (item 2) runs it too. 118 of the 123 calls went (116 by an AST pass over handlers that hand the
   same name to a logger call or `UARTComm._err()`, plus the webserver's connection-task arm, whose `err_s()` is the
   argument of `_trace_before_close()`, and `_put_status()`'s outcome loop). Kept explicit, as listed: `Lockable.__aexit__`
   (`asy_base_classes.py`), `DNSQuery.__init__` (`asy_captive_dns.py`), `FRAM_SPI.__aexit__` (`asy_fram_driver.py`),
   `_body_as_dict()` and the Microdot hook `_print_exception()` (`asy_webserver_service.py`; it returns unlogged for a
   traced timeout). Verified and gone: `asy_system_service.py:474` (the shutdown's await of a stopped task:
   `_shutdown_sequence()` cancels and awaits the supervisor task first and stops unless it is done, and
   `fatal_reported()`'s one reader is inside that supervisor's loop; the handler is now `except ...: pass`) and `:619`
   (the supervisor's own top, which logs `e`, so the logger records it anyway, a dead write either way). The
   `report_if_fatal` name left 13 imports (`asy_api_response.py`'s import line went whole).
   Tests: `test_every_entry_point_records_a_stack_overflow_at_level_0` and
   `test_err_s_and_wrn_s_record_the_overflow_ahead_of_their_fram_write` (red against the head's logger, green now);
   each explicit site got a test, red on a planted break (the record replaced by `_ = e`) and green: the lock-release
   exits (base, FRAM driver), the DNS parse, `_body_as_dict()`; the Microdot hook's test was already there
   (`test_h1_a_request_read_that_exhausts_the_c_stack_answers_400_and_reports_it`). The supervisor's reason-20 reboot
   tests stay green. The pinning tests changed with the mechanism: `tests_scripts/test_fatal_report_sites.py` now
   accepts a broad handler that hands its binding to a logger entry (a statement of its own body) or starts with the
   record (fabricated cases added for both sides, a conditional log refused), keeps the rebound printer strict, and
   exempts the shutdown's stopped-task await; `tests_scripts/test_task_tops.py` lost its record requirement and its two
   cases `fatal-not-reported`, `callback-fatal-not-reported`.
2. **Level 0 prints nothing (done).** `console()` and `_line()`'s below-level MemoryError branch went. `UDPSocket`
   (`logger=`, its three builders pass theirs: captive DNS, DNS client, NTP client), `RegionBuffer` (`logger=`; the FRAM
   chunk buffers get the chunk's `pr`, `UARTComm`'s TX/RX buffers the comm's), `FramingCOBS` (`logger=`, no product
   builder today) and the `UART` bus driver (`logger`, handed by `UARTComm.__init__`, so by the link driver too) print
   a caught MemoryError through the logger, silent without one. The attribute is `logger`, not `pr`: a class assigning
   `self.pr` counts as one with a logger of its own in `tests_scripts/test_readiness_gates.py`, which would drop
   `UART.deinit()`'s and `UDPSocket.disconnect()`'s answer-bool rule (its planted check went silent with `pr`). The logger-owning sites call their own logger (base tick
   timer, DNS query, FRAM check and erase buffers, the reboot entry, the Microdot hook, the logger's own four);
   `_copy_out()`'s console line folded into its existing `err_s()` entry line. The generated boot entry's loop-end text line
   ("event loop ended with an exception:") went with `console()`: a plain `print()` there breaks the print-only-in-the-
   logger convention (`tests_scripts/test_code_conventions.py`, `no_print`) and ruff's T20, and generated text carries no
   `noqa`; `sys.print_exception(ended)` still prints the traceback (B8 owns the entry; see Findings). Tests: `test_level_0_prints_nothing_for_a_
   caught_memory_error` (red, then green), `test_level_1_prints_a_caught_memory_errors_text_under_the_loggers_name`;
   the existing checks moved to level 1 in test_asy_print_log, test_asy_udp_socket, test_asy_uart_driver,
   test_asy_framing_codecs, test_asy_fram_manager, test_asy_base_classes, test_asy_dns_client,
   test_asy_webserver_connections, test_shared_helpers (and each layer's silence without a logger or at level 0 is
   asserted); hand-off tests for the builders (captive DNS, DNS client, NTP client, `UARTComm`, link driver).
   **Decision taken (agent, 2026-11-02): `PrintLog.err_nomem(what, e)`, `err()` with a fixed arity.** A star-call
   `err()` allocates its argument tuple, and `test_asy_system_service.py`'s two full-heap escalation tests (a heap
   full from the decision on: every star-call raises) went red with `self.pr.err()` in the reboot entry's
   `MemoryError` arm: the escalation no longer printed its cause and the arm raised. A kept behaviour, so fixed in the
   code: every former `console()` site prints through `err_nomem()`, which allocates nothing (heap-locked test
   `test_err_nomem_prints_its_line_from_level_1_and_allocates_nothing`) and is level-gated like `err()`. Five lines.
3. **E28 shrink (done).** Kept: one entry at setup for an unreadable store. Gone: the run flag `_write_failing` and
   `_write_through()`, the heap-failure arm `_heap_failed` (a heap failure building the chunk prints its line from
   level 1 and records nothing, as an allocator refusal), the setup-write arm. Catalog text says the one case. Tests
   removed first: `test_a_failed_write_after_setup_keeps_one_ram_only_entry_until_a_write_lands`,
   `test_a_reset_inside_a_failed_write_run_records_nothing_itself_and_starts_a_new_run`,
   `test_a_reset_whose_write_lands_after_a_failed_one_ends_the_run`,
   `test_an_entry_logged_during_the_setup_write_keeps_a_ram_only_entry_when_its_write_fails`; rewritten to the one
   case: `test_each_ram_only_store_shows_one_entry_under_its_own_name` → `test_only_an_unreadable_store_records_its_
   ram_only_entry` (red, then green); entry counts adjusted where a failed or paused write had added E28
   (test_asy_base_classes, test_asy_sgp40_driver, test_asy_system_service, test_fram_integration,
   test_readiness_gates, two in test_asy_print_log). The unreadable-store tests stay green
   (`test_an_unreadable_store_keeps_its_bytes_and_stays_ram_only`, the dead-chip scenario).
4. **Pre-setup merge (done).** `_pre_setup_slots`, the merge and the re-write after setup's write went; a valid read
   restores the stored ring and count, a blank or invalid store is written from RAM (the pre-audit setup), the
   unreadable branch and `restored` stay. Tests removed first: `test_entries_logged_before_setup_count_their_ram_slots`,
   `test_setup_merges_entries_logged_before_it_after_the_stored_ones`, `test_a_merged_count_saturates_at_the_cap`,
   `test_an_entry_logged_during_the_setup_write_still_lands_on_the_chunk`,
   `test_a_reset_whose_write_waits_behind_setups_read_keeps_only_what_arrived_since_it_began` (read first: it needs a
   `ResetErrors` during a logger's `setup()` read, which the device cannot meet, every logger setup running in the boot
   batch before the webserver serves; without the merge the restore overwrites what the reset window counted, as before
   the audit). Plain round trips stay green (`test_printloghistorystore_err_s_persists_and_survives_a_simulated_reboot`,
   `test_a_clean_read_of_a_valid_store_sets_up_without_writing`).
5. **Overlapping resets: kept, named.** `ResetErrors` resets do not run one at a time: `_put_status()`
   (`asy_webserver_service.py`) gathers every source's `reset_error_counter()` per request with no lock, Microdot serves
   up to 6 connections concurrently, and neither it nor `SystemService.reset_error_counter()` serialises them, so two
   PUTs overlap on every logger. `_kept`/`_counted` also carry the owner-approved single-reset window (`06a8ae5d`, A-P6);
   only the bit set came with `656fc82f`. Newest-entry tests green.
6. **`set_level()` (done).** No product caller reads the bool (`_apply_level()` drops it; the REST schema range-checks
   `DebugLevel`), so the pre-audit clamp returns, answering nothing; the level-setter types go back to
   `Callable[[int], None]` (`asy_system_service.py`, the emitter, as before the audit). The twin's `--debug-level`
   validator now refuses a level the clamp changes. Tests changed mechanically (the pre-audit clamp test restored, seen
   red against the head's logger, green now).
7. **Catalog (done).** The six retired rows E16, E65, W24, W43, W46, W47 went (searched: no reader but a bench-check
   test using `WLAN_OFF` as a refused name, still refused as unknown; its comment says so); no code retired by items
   1-6 (E28 stays, reworded). The `retired` mechanism stays for codes removed from the release on; SPECIFICATION.md's
   rule says so. Owners, bands, range kept.
8. **Kept as is:** `report_unretrieved()` and its install guard, the newest-entry rule, the counter caps.
9. **Other hunks of `asy_print_log.py` against `25caf528` (named, kept):** restored to the pre-audit text: `set_level()` (item 6),
   `__init__`'s order, the `setup()`s answering nothing (PLAN R1's per-unit rule: no product caller reads the logger's
   setup bool; `reset()` keeps its bool, which `ResetErrors` reads), the plain write-back in `_store_err()` and in a
   blank store's `setup()`. Kept and named, each with its basis: the newest-entry rule `_keep()` and `_count()`
   (owner, OR35.b); `reset()` writing the cleared image before RAM clears, `_pack_reset()`, `_clear()`,
   `_since_kept()`/`_since_counted()` and the pause refusal (owner, 2026-10-13 "1 b" and 2026-10-20, `06a8ae5d`); the
   overlapping-reset bit set (item 5); the write lock and generation count (`1cff5a26`, not a closure root: no item);
   the tri-state `_read()` and the unreadable branch (a confirmed gap); a negative code diagnosed and an empty warning
   slot reading 0 (`06a8ae5d`/`43aced07`, not a closure root); `owner=` and `get_pause` in the Protocols (follow other
   modules); `LogConfig`/`DEFAULT_LOG`/`make_logger(log, name)` (`41b47f1d`, U10's foundation); the `sep`/`end`
   keywords for `**kwargs` (typing), the `"<"` byte order (byte-identical on rp2), the removal of `get_level()` and the
   six level accessors (owner, OR36); `restored` (B2); `report_unretrieved()` (item 8); `err_nomem()` (decision below).
   The catalog: nothing else differs but its rows and texts (owners, bands, range kept by the list).

## Knowledge lines (removed items)
- `console(name, what, err=None)`: an ungated, fixed-arity console line for a layer with no logger and for the
  logger's own caught MemoryErrors, so the memory gates read their text at every level (`f1f800e7`, F3r `68224efb`).
  Went: level 0 prints nothing, ever (owner, 2026-11-02); its allocation-free arity lives on as `err_nomem()`. Code:
  `4516e60e:src/asy_print_log.py:456-463`.
- `_line()`'s below-level MemoryError arm: below its level a logger still printed the first caught MemoryError among its
  arguments (`68224efb`). Went with the same ruling. Code: `4516e60e:src/asy_print_log.py:91-101`.
- 118 `report_if_fatal()` calls as every broad handler's first statement (`06a8ae5d`). Went: the logger's entry records
  the overflow (owner's review "ok" holds; R0 item 3 measured the form). Code: `4516e60e`, every `src/` module.
- `report_if_fatal(e)` in the shutdown's await of a stopped task (`asy_system_service.py:474`): a dead write, the
  supervisor having stopped. Code: `4516e60e:src/asy_system_service.py:474`.
- The LOG_RAM_ONLY run (`_write_failing`, `_write_through()`; `f1f800e7`), the heap-failure arm (`_heap_failed`;
  `2977c4e0`) and the setup-write arm: one counted E28 per failed-write run, per chunk heap failure, per failed setup
  write. Went: hypotheses with no observed failure (a failing FRAM after boot; the FRAM layer's own entries show it),
  owner 2026-09-16 on FRAM capacity. Code: `4516e60e:src/asy_print_log.py:229-239, 290-298, 404-405, 435`.
- The pre-setup merge (`_pre_setup_slots`, the merge and the re-write after setup's write; `41b47f1d`, `2977c4e0`):
  entries logged before `setup()` kept as newest after a valid restore. Went: entries before setup occur only on a
  construction fault; with it went a reset-during-setup-read window the device cannot meet (setup runs before the
  webserver serves). Code: `4516e60e:src/asy_print_log.py:157, 194-195, 414-432`.
- `set_level()`'s refusal and bool (`8d44fd14`): no product caller read it; the REST schema range-checks. Code:
  `4516e60e:src/asy_print_log.py:103-110`.
- The logger's `setup()` bool: test-only (PLAN R1). Code: `4516e60e:src/asy_print_log.py:271-273, 398-436`.
- Catalog rows E16 CLOCK, E65 WLAN_OFF, W24 CFG_NO_STORED, W43 DNS_TEARDOWN, W46 NOTIFY_LATE_REGISTER, W47
  NOTIFY_FINALIZE_AGAIN: placeholders for numbers retired before the release (decision 6). Code:
  `4516e60e:buildgen/error_catalog.json`.
- The boot entry's "event loop ended with an exception:" line (`980c0f7d`'s `console()` form of an earlier `print()`).
  Went with `console()`; the traceback still prints. Code: `4516e60e:buildgen/codegen.py:873`.

## Gate
Once, on the committed tree `39f1615b`, through the run wrapper (`b1_gate2`, 22:08-23:23 UTC, rc=0):
- `PICO_TOOLCHAIN_DIR=S/tc-int scripts/test.sh`: PASS, files 137 passed / 0 failed (86 skipped, 6 deselected by
  design), tests 6,049 passed, tests_scripts 7,117 passed, no retry, no MemoryError marker.
- the same with `GC_THRESHOLD=32768`: PASS, the same counts.
- `scripts/run_digital_twin_ci.sh dev --part suite` at -1 and at 32768: PASS, 332 checks + 16 (every run's log free of
  both memory markers); `--part harness` at -1 and 32768: PASS, 65 scenarios (2 skipped by design).
- `npm run lint`, `npm run typecheck`, `npm run test:unit` (26 files, 1,340 tests): green.
- Lint (`lint_direct.sh`) and the three mypy passes on the same tree: clean (`b1_lint6`, `b1_tc4`).
- Before the gate, two whole-tier probes found what the action list missed (fakes of `UDPSocket`'s constructor, the
  boot entry's print conventions, the `pr` attribute's effect on the teardown rule); each was fixed, the failing files
  rerun alone. No failure in the gate; none outside the unit was reproduced.

## Sizes
- `src/` bytecode (`module_sizes.sh` at `39f1615b`, `u35r/r1/B1/sizes_b1.tsv`, against `r0/mpy/now.tsv`): 207,188 B,
  −1,520 B (R0 208,708 B); lines 16,517, −161. By module: `asy_print_log.py` 6,000 → 5,417 B (487 → 439 lines);
  `asy_isl29125_driver.py` −172, `asy_scd30_driver.py` −146, `asy_system_service.py` −138, `asy_wifi_service.py` −137,
  `asy_bmp3xx_driver.py` −102, `asy_webserver_service.py` −91, `asy_fram_manager.py` −67, `asy_sgp40_driver.py` −63,
  `asy_api_response.py` −52, `asy_notification_service.py` −47, `asy_config_manager.py` −31, `asy_uart_link_driver.py`
  −31, `asy_ntp_client.py` −24, `asy_base_classes.py` −18, `asy_uart_comm.py` −15, `asy_dns_client.py` −8,
  `asy_captive_dns.py` −1; grown (stated under Findings): `asy_framing_codecs.py` +105, `asy_uart_driver.py` +81,
  `asy_udp_socket.py` +20.
- dev's image (`scripts/build_firmware.py dev`, `build/firmware-dev.json`): `imageFreeBytes` 44,748 B (R0: 43,068 B,
  +1,680 B).
- Lines against the integration head: `src/` +147 −308, `buildgen/` +4 −11, tests and tools (tests, tests_scripts,
  digital_twin, tests_hardware) +514 −625, docs (SPECIFICATION.md, the UART changelog, the twin README) +70 −75.

## Decisions taken (agent, 2026-11-02)
- `PrintLog.err_nomem(what, e)` (item 2): the full-heap escalation tests showed a star-call `err()` raising in a
  `MemoryError` arm; every former `console()` site prints through this fixed-arity, level-gated form. It also runs the
  C-stack record, so it is an entry point like the others.
- The borrowed logger is the attribute `logger` on `UART` and `UDPSocket` (item 2), so neither counts as a class with a
  logger of its own and both keep the teardown-answers-bool rule.
- `UDPSocket._nomem(e)`: its seven arms share one helper (the module shrank back to +20 B over R0 from +121 B).
- The boot entry's loop-end text line dropped rather than kept as `print()` (the convention and T20 refuse a `print()`
  there; a pyproject exemption would touch the build environment).
- `_copy_out()`'s line folded into its existing `ALLOC` entry's `err_s()` line, which now carries the error's text.
- The pinning test of item 1 kept in a new form (a broad handler hands its binding to a logger entry or records first),
  with the shutdown's stopped-task await exempted, the record's reader having stopped.

## Findings
- (c) The generated boot entry still prints at DebugLevel 0: `sys.print_exception(ended)` after the loop ends, the
  one console write left outside a logger (`buildgen/codegen.py`, B8's entry). Against "level 0 prints nothing, ever"
  only if the owner counts a dying loop's traceback; B8 judges.
- (c) Other modules still log a caught MemoryError through a star-call (`UARTComm._allocate()`'s `self.pr.err()`, many
  `err_s()` arms, now `_copy_out()`'s too): on a heap with not even a small tuple free that call raises out of its arm.
  Pre-existing, not reproduced outside the escalation (which now uses `err_nomem()`); `err_nomem()` is the form for an
  arm that must not raise. For the units owning those modules.
- (c) Item 5 for the lead: a lock around `_put_status()`'s resets would make resets run one at a time and let the
  overlapping-reset bit set go; not on the list, not done.
- Bytecode growth (stated, PLAN 2 step 4): `asy_framing_codecs.py` +105 B (the `TYPE_CHECKING` block that types the
  optional logger), `asy_uart_driver.py` +81 B (the borrowed `logger`, `_report()`), `asy_udp_socket.py` +20 B (the
  borrowed `logger`, `_nomem()`): the mechanism of the owner's (d) decision ("loggers passed through"), not a fix.
