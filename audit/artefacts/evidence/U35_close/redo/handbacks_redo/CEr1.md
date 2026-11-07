CEr1 hand-back, saved by the lead from the message it sent (2026-10-27). Commit 8d343d44 on audit/u35-cer1 (on 0dcc13d2).

## CEr1 hand-back: the coverage run, every uncovered src line classed

**Commit:** 8d343d44 on audit/u35-cer1 in S/wt-u35cer1 (base 0dcc13d2). Not pushed, nothing uncommitted. Files: audit/sweeps/e51_sweep.py (new), e51_verdicts.json, e51_hits.json (the run's src lines, so `--check` can re-run without the coverage data), and audit/b3/e51.md (rendered from them). Logs are in S/u35/laneE/cer1/.

**The run:** `scripts/test.sh --coverage`, run twice through tc-cer1, inside the namespace, at nice 19.
- Both runs ended rc 1. The only reds were test_twin_record's two rows, which wait on your re-record.
- 115 MicroPython jobs, 5546 tests passed, 0 failed. There was **no tracer note** (`Notes: none`) and 0 memory markers.
- Run 1 (1006 s) left no src data. In this container `uv run scripts/_render_coverage.py` cannot resolve its inline `coverage==7.16.2` offline (the uv cache has no index entry for it). test.sh's EXIT trap then deleted the raw dumps.
- Run 2 (1033 s) copied the 115 dumps out while it ran, finding the dump directory from a coverage runner's arguments. I rendered them with the shared venv's coverage. This only affects this offline container; CI has network.
- Result: 946 of 10,575 src statements were not recorded.

**Sweep:** red first twice (first on stubs, then on the two new artifact cases), then green: 6 sites, 7 artifact kinds, 4 check probes. Four planted faults all turned it red.
- It first removes lines the tracer never records even though they run: 793 private `const()`, 20 decorated `def` lines, 27 `while True:` headers.
- It found two such cases SPECIFICATION.md E.5.1 does not list, both confirmed on build-settrace:
  - 6 `elif` lines whose test is just a variable name (or and/or/not of names);
  - 5 class-level annotations with no value (`x: T`).
- The `elif` case also produces a false positive: the line before such an `elif` reads as run when only its test ran. Five lines sit in that position (fram_manager 222, 230, 249; isl29125 720; notification 294). A print planted before each fired in its own module's test file, so none of them hides an uncovered line.
- What remains is **63 sites, 95 lines**, all with a verdict; `--check` exits 0. lint_direct rc 0; test_citations and test_decision_vocabulary: 21 passed.

**Per class** (lines on this base):
- **(a) reachable, untested, 11:** bmp3xx 705; config_manager 510; crc_checks 102; isl29125 1519; scd30 319, 761; uart_driver 225-226, 342, 665-666; uart_link 110, 226-228.
- **(b) guard, kept, 31:** config_manager 559-560, 626-628; fram_manager 168-170, 424-425; i2c_driver 52, 63-64, 85, 96-97; isl29125 325-328, 829-832; scd30 735; sgp40 462; uart_comm 562, 784; uart_driver 212-213, 247-248, 256-257, 298-299, 317-318, 521, 561-562, 564-565, 567-568, 620-621, 623-624, 641, 646, 669-670, 672-673, 680-681; system_service 454 (the only one registered as untestable).
- **(c) type narrowing, 20:** fram_manager 487, 557, 573, 640; isl29125 1504; scd30 280; uart_comm 576, 601, 902, 1008-1009, 1111; uart_driver 183, 290, 357, 369, 810; uart_link 166, 186, 234; webserver 212.
  - uart_comm 601 and 902 and uart_link 186 have no "narrows the Optional" comment yet; that src comment is owed to the next block.
- **(d) feature, 1:** webserver 903 (a webserver built without a system-command handler answers Invalid).
- **(e) removal, 0.** I have no removal proposals.

**CE3's 35 rows:** all re-found, at CE3's own line numbers. I re-checked its three "unreachable" proofs on this tree:
- uart_driver's three `if not want:` branches: CE3's proof holds (ready() returns with no await right after it saw a non-zero level). Kept as the never-block guard, tested through a substituted `_rx_level`.
- scd30 735: the proof holds (one session under bus_lock). Kept as a guard, tested through a session double.
- system_service 454: CFr2's proof holds. Kept as the safety guard and registered as untestable.

**Owed tests** (one per row; each row names its input):
- test_asy_bmp3xx_driver: 705, bus down during reset()'s settle, under a run bound (CRr2a item 3).
- test_asy_config_manager: 510 (log reset() answers False); 559-560 (schema field with no default, no file written); 626-628 (compare raising a MemoryError worded clear of the gate markers).
- test_asy_crc_checks: 102 (add_into with init -1 or above all bits set).
- test_asy_fram_manager: 168-170, 424-425 (set_values_sync raising; the report_if_fatal re-raise bitten by a C-stack overflow).
- test_asy_i2c_driver: 52, 63-64, 85, 96-97 (an SCL pin double that is never released, in the pulses and at the STOP, both the sync and the awaiting form).
- test_asy_isl29125_driver: 325-328, 829-832 (configure() raising); 1519 (the bus refuses the reset write while up).
- test_asy_scd30_driver: 319 (ContMeas False through `_set_mgr_cfg()` on a down bus); 735 (session double whose readinto() answers False); 761 (stop command on a down bus).
- test_asy_sgp40_driver: 462 (pack_into answers False while a backup is due).
- test_asy_uart_comm: 562 (uart_listen() raising); 784 (a PieceBuffer double whose write_at() refuses).
- test_asy_uart_driver:
  - receive overrun: 247-248, 561-562, 641, 669-670;
  - lap during a copy: 256-257, 317-318, 521, 567-568, 623-624, 646, 680-681;
  - closed channel: 212-213, 298-299;
  - no ring: 342; mid-line timeout: 665-666; 225-226 through the readline failures;
  - never-block: 564-565, 620-621, 672-673.
- test_asy_uart_link_driver: 110 (echo GET before any SET); 226-228 (cancel during the double initiation).
- test_asy_webserver_service: 903 (routes without system_cmd).

**Proposed E.5.1 text for D3r.** Part E already holds the convention paragraph, so no change there.
- Append to the first paragraph: "Nor does an `elif` whose test is a bare name, or and/or/not of bare names (`c_if_cond()` compiles it with no line-carrying parse node, `py/compile.c:400`), or a value-less `x: T` in a class body (no bytecode, `py/compile.c:2029-2033`). The `elif` case also runs its test under the line before it, so that branch's last line can read as covered when only the test ran (agent, 2026-10-27)."
- Replace the "Separately …" and FRAM paragraphs with: "Kept and uncovered, each commented in place:"
  - "Type narrowing of an `Optional` the code before it settles:"
    - "`asy_fram_manager.py`'s four returns after a buffer accessor (a `RegionBuffer`'s buffer is fixed at construction);"
    - "`asy_uart_comm.py`: `_listen_unlocked()`, `_read_answer_header()` and `_recv_train()`'s `rx is None` (`_read_frame()` already failed), `_write_frame_with_ack()`'s second `get_buf()`, `uart_get()`'s `own is None`, and `_min_rx_ring()`'s and `_take_discarded()`'s `bus is None` (setup refuses a missing bus);"
    - "`asy_uart_driver.py` `_arm_rx()`, `_rx_copy()`, `_rx_line_len()`, `_rx_peek()` (each after a positive `_buffered()`) and `writefrom()`'s `crcsize is None`;"
    - "`asy_uart_link_driver.py` `_read_raw()`, `_write_raw()` and `_run_hazards()`'s `bus is None` (no hazard run without a set-up bus);"
    - "`asy_scd30_driver.py` `_set_mgr_cfg()`'s `outcome is None`; `asy_isl29125_driver.py` `read_counts()`'s `counts is None`; `asy_webserver_service.py` `_cfg_values()`'s `return {}`."
  - "Registered untestable: `asy_system_service.py` `_shutdown_sequence()`'s not-proven-stopped `return`. A cancel of the awaited supervisor is forwarded to it (`extmod/asyncio/task.py:164-166`), so the supervisor is done after the await, and only the supervisor sets the park flag. It is kept as the fallback that stops feeding so the watchdog resets."
- Drop from E.5.1: the print_log `_NO_WRN` sentence, the wifi `_push_wifi_led()` arm and the math_helpers note (all covered on this base). Also take `_recv_train()`'s destination bound out of the narrowing list: it guards the caller's buffer and gets a double test. The `finally:` paragraph stays.

**Findings for you:**
- The offline render failure above.
- A stray file written by a test: during run 1, at 03:17:08, a test wrote `config_SYSTEM.cfg` (`{"DebugLevel": 0}`) into the worktree root. It is gitignored, so git status does not show it. Run 2 did not rewrite it. I saved a copy at S/u35/laneE/cer1/stray_config_SYSTEM.cfg and could not find which test writes it. It may belong with N12.
- No product file changed, and no MicroPython test file, so there are no time rows. The silent-failure scan of my files found nothing.

**Cleanup:** S/tc-cer1, the raw dumps, the probe copies, `.coverage`, the htmlcov trees and build/archive are deleted. No process of mine is left (checked by /proc cwd).

nothing of mine is running
