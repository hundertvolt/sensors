CEr2 hand-back, saved by the lead from the message it sent (2026-10-27). Commit 1298e714 on audit/u35-cer2 (on 843a4f72).

## CEr2 hand-back: a direct test for every owed uncovered src row

**Commit:** 1298e714 on audit/u35-cer2 in S/wt-u35cer2 (base 843a4f72). Not pushed, and the tree is clean. I did about 75 tool calls. Logs are in S/u35/laneE/cer2/.

**Changed files:**
- 12 test files: bmp3xx, config_manager, crc_checks, fram_manager, i2c, isl29125, scd30, sgp40, uart_comm, uart_driver, uart_link, webserver.
- `src/asy_uart_comm.py`, at `_min_rx_ring()` :600 and `_take_discarded()` :901, and `src/asy_uart_link_driver.py`, at `_run_hazards()` :185. Each gets a trailing "Unreachable: … - kept to narrow the Optional for the type checker" comment and nothing else. No line moved, so e51_hits.json still lines up.
- audit/sweeps/e51_verdicts.json and audit/b3/e51.md.

**Rows:** 42 of 42 are covered: 11 class (a), 30 class (b) and 1 class (d). system_service 454 stays registered as untestable. All line numbers matched CEr1's on this base, so none needed moving.

**Reach proof:** I ran `tests/_coverage_runner.py` on tc-int build-settrace for only the 12 changed files. After the last edits I re-ran it for the 5 files touched later. `cover.py` checked every line of each row against its own test file's dump: 42 reached, 0 missed. It found the rows through the sites of `e51_sweep.py --sites`. Every coverage job passed, with 0 runner notes and 0 memory markers. uart_link 226-228, the `finally` body that CEr1 suspected the tracer might miss, is recorded too.

**Tests per row** (all in the file the row names):
- **bmp3xx 705:** `test_reset_raises_oserror_when_the_bus_goes_down_between_its_two_sessions`. The bus goes down during the settle sleep. It runs under its own 2 s bound and asserts the 0xB6 write happened.
- **config_manager:**
  - 510: `test_reset_error_counter_answers_false_when_the_history_clear_fails`
  - 559-560: `test_a_schema_field_with_no_default_leaves_the_manager_invalid_and_writes_no_file`
  - 626-628: `test_a_compare_that_exhausts_the_heap_fails_the_write_with_no_file_io`. Its injected error text is "simulated allocation failure", clear of both gate markers.
- **crc 102:** `test_add_into_refuses_an_init_outside_the_crc_width_and_leaves_the_buffer_untouched`, for CRC8, CRC16 and CRC32, with init -1 and with all bits set plus one.
- **fram 168-170 and 424-425:** `test_an_unexpected_raise_in_the_chip_write_fails_the_clear_and_the_write_and_is_logged`. Both are driven with OSError and with a real stack overflow.
- **i2c 52, 63-64, 85, 96-97:** `test_a_clear_whose_scl_is_held_after_a_pulse_reports_it_and_sends_no_stop` and `test_a_clear_whose_scl_is_held_at_the_stop_lets_sda_go_and_reports_it`. Each covers both the boot clear (sync) and `clear()` (awaiting).
- **isl29125:**
  - 325-328: `test_an_interrupt_select_write_that_raises_is_logged_and_leaves_the_hold_state`
  - 829-832: `test_a_re_arm_write_that_raises_is_logged_and_writes_no_thresholds`
  - 1519: `test_a_reset_write_the_bus_refuses_while_up_raises_with_no_config_read`. Here `set_register_struct` is substituted to answer False. A NAK cannot reach this line, because the bus layer raises on a NAK rather than answering False.
- **scd30:**
  - 319, and 761 through the reader: `test_contmeas_false_with_the_bus_down_after_the_snapshot_comes_back_failed`. A down bus from the start cannot reach 319: the snapshot fails first and the whole body is refused, as the owner ruled. So the bus goes down after the snapshot.
  - 761 directly: `test_a_command_write_the_bus_refuses_raises_oserror`
  - 735: `test_a_register_read_the_session_refuses_raises_before_the_crc_check`
- **sgp40 462:** `test_a_due_backup_whose_state_does_not_pack_logs_the_algorithm_state_error`. The double sits one layer up: `measure_index_and_raw` reports the state not packed.
- **uart_comm:**
  - 562: `test_a_raising_uart_listen_is_logged_and_the_loop_backs_off_and_keeps_listening`
  - 784: `test_a_received_piece_its_destination_refuses_fails_the_transfer_as_a_size_mismatch`. A caller cannot hand in a PieceBuffer (`_check_buffer` refuses one), so the module's own PieceBuffer is rebound to a refusing subclass. The responder is declared to stall, since its train is cut.
- **uart_driver:**
  - Overrun (247-248, 561-562, 669-670): `test_a_receive_overrun_mid_read_fails_each_multi_round_read_and_counts_what_it_had_taken`
  - Overrun in readline (641): `test_a_receive_overrun_seen_by_readline_fails_it_and_the_next_read_is_whole`
  - Lap (256-257, 317-318, 521, 567-568, 623-624, 646, 680-681): `test_a_lap_during_the_copy_fails_every_read_path_and_no_phantom_byte_reaches_the_next_read`. The real DMA count is moved a ring plus one on.
  - Closed channel: `test_an_overrun_on_a_closed_receive_channel_still_fails_as_one_and_nothing_escapes` (212-213) and `test_a_channel_closed_during_the_copy_fails_the_copy_and_never_raises` (298-299)
  - No ring (342): `test_a_uart_with_no_receive_ring_is_never_ready_and_reads_nothing`
  - Mid-line timeout (665-666): `test_a_line_the_peer_stops_mid_way_times_out_and_counts_its_partial_discarded`
  - 225-226 is reached through the line overrun, line lap and mid-line timeout tests.
  - Never-block (564-565, 620-621, 672-673): `test_ready_with_nothing_to_clamp_to_yields_at_poll_wait_ms_and_the_read_completes`
- **uart_link:**
  - 110: `test_an_echo_get_before_any_echo_set_answers_valid_and_empty`
  - 226-228: `test_a_double_initiation_cancelled_at_its_first_await_leaves_no_transaction_behind`. The cancel is forwarded to `first`, which is MicroPython's own forwarding, so the line that bites is the finally's cancel of `second`.
- **webserver 903:** `test_a_webserver_built_without_a_system_command_handler_answers_invalid`. The route is PUT /system, not the /status that CEr1 wrote.

**Plants:** each went in a scratch copy of src/ (plant.sh), was never committed, and was removed afterwards. All 23 turned the named test red.
- uart_driver, 14: the 4 overrun guards, the 7 lap guards and the 3 never-block yields.
  - The readline overrun plant was missed at first. Without the guard, `bytearray(-1)` raises an allocation failure that is caught, so readline still answers None. I tightened the test to assert a silent console, and the re-plant bit.
- `report_if_fatal`, 5: fram ×2, isl ×2, uart_comm ×1.
- uart_link `task.cancel()`, 1.
- bmp3xx, 3: a hang, which the run bound caught while the file still finished at 138/139; the raise removed; the soft reset never written.

**Wrong behaviour found:** none, and no row went back to you.

**Times**, before → after, in seconds at -1 / 32768. The after figures come from the last run of each file. All runs passed with 0 memory markers.
- bmp3xx 13.9/13.9 → 13.8/13.9
- config 0.2/0.2 → 0.2/0.2
- crc 0.1/0.1 → 0.1/0.1
- fram 1.0/2.1 → 0.9/2.0
- i2c 1.6/1.6 → 1.6/1.6
- isl 2.6/3.0 → 2.9/3.2
- scd30 22.7/29.9 → 23.1/29.7
- sgp40 8.5/9.7 → 8.8/10.3
- uart_comm 62.5/63.6 → 62.5/63.7
- uart_driver 6.0/10.9 → 6.1/10.4
- uart_link 4.8/6.8 → 5.1/7.0
- webserver 5.1/8.2 → 5.2/8.6

The uart_comm and uart_link files ran at both stages after the src comments and `S/u23/rebuild.sh`.

**Checks:**
- `lint_direct.sh`: rc 0. The first run found 10 ruff findings (B023, RUF006) and I fixed them.
- mypy main pass, with `MYPYPATH` and `--custom-typeshed-dir` pointed at S/shared/typings: Success, 271 files. The first run found 5 findings and I fixed them.
- tests_scripts: comment_block_cap, citations, decision_vocabulary, code_conventions and memory_error_gate_agreement, 705 passed. Two test comments had tripped decision_vocabulary ("accepted", and "never … again"); I reworded them.
- e51 `--check` rc 0, and `--self-test` passes.

**Notes for you:**
- Some debug runs were made directly, without the namespace. RUNS.md records them in a summary line.
- e51.md's header has a new paragraph recording the covered rows.

nothing of mine is running
