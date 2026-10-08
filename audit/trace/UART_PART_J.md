# UART Part J ↔ code traceability (M.PROC.017, A.U17.12)

Audit working file, deleted with `audit/` at phase D. One row per normative statement of SPECIFICATION.md Part J, the
code site that implements it (read by symbol: `src/asy_uart_comm.py` unless another file is named; `drv.` is
`src/asy_uart_driver.py`'s `UART`), the test that pins it with its level (L1 `tests/`, L2 digital twin, L3/L4 real
hardware) and its status. Read on the U17 integration tree `79b2cce` (every U17 code lane, H included) plus lane U,
2026-10-07; the lead re-checks it at the U17 close after D merges.

Status: **holds** (code and text agree, pinned); **holds, text at D** (the code holds a statement Part J does not yet
carry or carries in its pre-U17 wording; lane D's step adds or rewrites it at U17, quoted from the packet); **text
diverges** (Part J's current text is false against the code; the owning step is named). Unit-test names are from `tests/test_asy_uart_comm.py` unless another file is named; `hz.` is
`tests/test_uart_comm_hazard.py`, `tw.` is `tests/test_digital_twin_uart_link.py`, `dt.` is
`tests/test_asy_uart_driver.py`.

## Preamble and J.1 Scope and the two-implementation contract

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "a sync allocate-only constructor with a readiness gate" | `UARTComm.__init__` (`_validate_config()`, `_allocate()`, no bus call), `_ready()` | `test_construction_performs_no_bus_call`, `test_valid_construction_sets_the_gate_only_after_setup` (L1) | holds |
| "a never-raise contract on every entry point" | every entry point returns its sentinel; `PieceBuffer(...)` in `_get_unlocked()`/`_accept_set()`/`uart_get()` lets its `MemoryError` through (OR143.a, owner, 2026-10-05) | `test_every_public_entry_point_converges_on_its_own_sentinel` (L1) | text diverges: the module docstring now reads "answers a link fault with a sentinel"; the preamble and J.8's "never an exception" follow at D (A-8, A-25) |
| "`dev` carries two instances across its crossover jumper ... `wozi` carries none" | `devices/dev.toml` `uart_link` pair; buildgen `_check_uart_link_roles()` | `tw.test_both_instances_are_constructed_and_registered` (L2) | holds |
| "**One deployed value has to change in a faithful port**: `rxbuf` 32 is refused (`errno` 78) against this module's 80-byte per-poll-interval `rxbuf` floor" | `_validate_receive()` → `_min_rxbuf()` | `test_the_legacy_bsec_bus_parameters_meet_every_floor_but_one` (L1) | holds |
| "a GET declaring `exp_size=0` ... and a SET whose payload is an empty `bytearray()`" still work | `_dest_size()`, `uart_set_into()` | `test_the_two_spellings_the_boards_own_uart_script_used_still_work` (L1) | holds |
| "Every protocol-level change is logged in `UART_C_PORT_CHANGELOG.md` — a temporary file, deleted once the C side is reconciled." | `UART_C_PORT_CHANGELOG.md` header (step 87); `tests_scripts/test_uart_changelog.py` | `tests_scripts/test_uart_changelog.py` (L0) | text diverges: J.1 still says "a temporary file"; A.U17.08's SPEC blast ("kept until the post-audit C reconciliation deletes it") and A.U17.11's J.1 sentence ("`tests_scripts/test_uart_changelog.py` fails when a module constant changes without the changelog's constants table following it.") land at D |

## J.2 Role model

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "initiation is restricted to one side by construction" / "the initiation entry points refuse on the wrong role" | `_gate(ROLE_INITIATOR)` in `uart_get()`, `uart_get_into()`, `uart_get_stream()`, `uart_set_into()`, `uart_set_stream()` (`uart_set()` delegates); `_gate(ROLE_RESPONDER)` in `uart_listen()` | `test_the_role_gate_refuses_the_wrong_direction`, `test_a_responder_refuses_the_role_before_any_argument` (L1) | holds |
| "An initiator uses `uart_get()`/`uart_set()` and never listens" | `get_task_starters()` returns the listen starter only for `ROLE_RESPONDER` | `test_starter_lists_match_the_role` (L1) | holds |
| "The responder's own answer to a GET ... runs through the internal unlocked SET path" | `_answer_get()` → `_send_train()` | `test_a_responder_still_answers_a_get_while_the_role_gate_is_active` (L1) | holds |
| "simultaneous initiation is out of contract" | `_write_frame_with_ack()`: a data frame where an ACK is due → `_ERR_UART_PEER_INITIATED` | `hz._check_a_peer_initiating_mid_transaction_reports_peer_initiated`, `hz._check_a_peer_initiating_mid_transaction_is_detected_and_both_recover` (L1) | holds |

## J.3 Frame format

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "Every frame is exactly `5 + payload_size` bytes, the payload field zero-padded to its full width" | `_frame_size`; `_prepare_tx()` pads from `_zero` | `test_padding_is_zero_filled_from_the_preallocated_buffer`, `test_header_fields_land_at_their_documented_offsets` (L1) | holds |
| "this layer is entirely CRC-agnostic" | no CRC call in the module; `drv.write()`/`writefrom()`/`readinto_until_complete()` add/check it | `hz._check_with_a_crc_configured_the_same_payload_corruption_is_caught`, `hz._check_the_crc_appears_on_the_wire_big_endian_after_the_payload` (L1, both modes) | holds |
| "`FramingPass` is the default and adds nothing ... Selecting a delimited codec is a wire change" | `drv.UART.__init__` (`framing=None` → `FramingPass`) | `dt.test_writefrom_is_framed_exactly_like_write` (L1) | holds |
| (D, A.U17.22) "a delimited codec's `max_frame` is the raw frame (header, payload and CRC); `UARTComm` refuses one smaller than that" | `_validate_link()` → `_ERR_UART_CODEC_SIZE`; `FramingCOBS._checked_encoded()` | `test_a_codec_below_one_frame_is_refused`, `test_a_pair_on_exact_sized_codecs_completes_a_get_and_a_set`; `tests/test_asy_framing_codecs.py::test_a_262_byte_frame_bound_decodes_every_length_and_refuses_one_past` (L1) | holds, text at D |
| "The CRC algorithm and its byte order are part of the wire contract" | `asy_crc_checks.CRC16` (big-endian CCITT-FALSE) | `hz._check_the_crc_appears_on_the_wire_big_endian_after_the_payload` (L1) | holds |
| `UID` "incremented per transmitted frame, wrapping `0xFE → 0`" / "**Never `0xFF`**" | `_next_uid()`, `_UID_MAX`; `_write_frame_with_ack()` advances `_uid` only once a frame goes out | `test_the_uid_cycle_covers_every_legal_value_and_never_0xff`, `test_the_next_uid_prediction_is_correct_at_the_wrap_boundary` (L1) | holds |
| a received `UID` of `0xFF` is invalid ("a conforming peer never emits 0xFF") | `_validate()` (`buf[_MSG_UID] > _UID_MAX`) | `test_a_received_uid_of_0xff_is_rejected`, `hz._check_the_uid_field_sweep_stops_at_0xfe` (L1) | holds |
| "`CMD`: `ACK 0x01`, `GET 0x02`, `SET 0x04`" (exact match, changelog A1) | `_CMD_ACK`, `_CMD_GET`, `CMD_SET`; `_validate()` exact membership | `test_a_multi_bit_command_is_rejected_rather_than_falling_through`, `hz._check_the_command_field_sweep_accepts_only_the_expected_command` (L1) | holds |
| "`SIZE` ... (`0 … payload_size`)" | `_validate_data()`; `_prepare_tx()` range check | `test_out_of_range_header_fields_are_rejected_not_truncated`, `test_size_always_matches_the_bytes_actually_copied` (L1) | holds |
| "`CHUNKS` ... (`1 … 0xFF`)", "`CUR_CHUNK` ... 1-based" | `_validate_data()`; `_chunk_count()` ≤ `_CHUNKS_MAX` | `test_a_zero_chunk_train_is_rejected`, `hz._check_the_current_chunk_field_sweep_matches_only_the_expected_index` (L1) | holds |
| "An ACK frame carries the acknowledged frame's `UID`, `SIZE = 0`, `CHUNKS = 1`, `CUR_CHUNK = 1`. An ACK echoes the received `UID` and does not consume one of the sender's own." | `_allocate()` (fixed ACK fields), `_send_ack()` (received UID), `_validate_ack()` | `test_the_ack_frame_is_byte_exact`, `test_a_malformed_ack_is_rejected`, `test_a_stale_ack_uid_is_rejected` (L1) | holds |

## J.4 Transactions

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "Chunk 1 is always the command header: its payload is the single command-ID byte, `SIZE = 1`" | `_send_train()`/`_get_unlocked()` write `_cmd_buf` with size 1; `_validate_size_for_position()` `cur == 1` | `test_a_first_chunk_with_the_wrong_size_is_rejected`, `hz._check_the_first_chunk_size_field_sweep_accepts_only_one` (L1) | holds |
| "Every frame is individually acknowledged before the next is sent" | `_write_frame_with_ack()` (write, then `_read_frame()` for the ACK) | `test_a_missing_ack_at_each_train_position_aborts_and_resyncs` (L1) | holds |
| "SET ... `CHUNKS = ceil(len(payload) / payload_size) + 1`, floored at 2" | `_chunk_count()`; receive: `_validate_size_for_position()` (`chunks < _MIN_CHUNKS`) | `test_chunk_counts_at_the_payload_size_boundaries`, `test_a_set_declaring_a_single_chunk_is_rejected`, `hz._check_the_chunks_field_sweep_rejects_zero_and_one_for_a_set` (L1) | holds |
| "the initiator sends a one-chunk GET train" | `_get_unlocked()` (`_write_frame_with_ack(device, _CMD_GET, 1, 1, ...)`) | `test_a_get_round_trip_returns_the_answer` (L1) | holds |
| (D, A.U17.16) "A GET frame declaring any other `CHUNKS` is rejected like any invalid frame (no ACK)." | `_validate_size_for_position()` (`cmd == _CMD_GET and chunks != 1`); changelog A14 | `test_a_get_declaring_any_chunk_count_but_one_is_refused`, `hz._check_the_chunks_field_sweep_accepts_only_one_for_a_get` and the "GET with CHUNKS 2" case of `hz._check_no_ack_is_emitted_for_any_rejected_frame` (L1, both CRC modes) | holds, text at D |
| "the responder answers with a SET train ... whose chunk 1 echoes that same ID" | `_answer_get()` → `_send_train(device, cmd_id, ...)`; `_read_answer_header()` refuses another id (`_ERR_UART_GET_ID_MISMATCH`) | `test_the_get_answer_echoes_the_requested_command_id`, `test_a_peer_answering_a_different_question_is_refused` (L1) | holds |
| "validate each frame (command, chunk index exactly as expected, `SIZE` within bounds), append `SIZE` payload bytes, acknowledge" | `_recv_train()` → `_validate()` with `_next_uid(prev_uid)` and the latched `chunks` | `test_a_changed_chunks_total_is_rejected`, `test_a_stale_data_chunk_is_rejected_by_its_uid`, `test_a_short_middle_chunk_is_rejected` (L1) | holds |
| "`SIZE = 0` on chunk 2 means a genuinely empty payload, a distinct outcome from failure" | `_validate_size_for_position()` (empty only as a two-chunk train's last); `_accept_set()` (`written == 0`) | `test_an_empty_chunk_is_legal_only_as_a_two_chunk_trains_last`, `test_an_empty_payload_is_a_distinct_outcome_from_failure`, `test_an_empty_set_is_delivered_as_a_distinct_outcome` (L1) | holds |
| "An expected total size ... enforced both incrementally ... and finally (exact match)" | `_recv_train()` (`written + size > exp_size` before the copy; `written != exp_size` after); `_dest_size()` early refusal | `test_all_three_expected_size_modes`, `test_an_expected_size_the_train_could_never_deliver_is_rejected_early`, `test_an_answer_that_misses_its_expected_size_is_refused_before_its_final_ack` (L1) | holds |
| "Rejection is signalled by withholding an ACK" / "The final chunk's acknowledgement is deliberately deferred until after the total-size check passes" | `_recv_train()` (`break` before the final `_send_ack()`) | `hz._check_no_ack_is_emitted_for_any_rejected_frame`, `test_a_lost_final_ack_reports_failure_while_the_receiver_reports_success` (L1) | holds |

## J.5 Timing, flow control and recovery

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "Waiting for a *new* message is either unbounded (a responder listening) or bounded by `timeout` ...; once a frame has begun arriving, the inter-part timeout is always `timeout`" | `_listen_unlocked()` → `_read_frame(device, -1)`; `_read_frame()` passes `start_timeout_ms=timeout_ms, timeout_ms=self._timeout` | `hz._check_a_listener_whose_frame_never_arrives_reports_a_read_timeout`, `hz._check_a_truncated_frame_recovers_to_a_working_exchange` (L1) | holds |
| "Recovery is quiesce-and-resync, never retransmission" / drain "until the line has been quiet for `1.5 × timeout`, then holds off initiating for a further `1.5 × timeout`" | `_fault()` → `_resync()` → `_drain()` (`_resync_window_ms()`), `_hold_off_writes()`; constants `_RESYNC_NUM`/`_RESYNC_DEN` | `test_the_drain_ends_once_the_line_is_quiet`, `test_the_hold_off_window_derives_from_timeout` (L1) | holds |
| "**'Any fault' includes a purely local one raised mid-train**" | `_pull_chunk()` aborts through `_fault()` | `test_a_pull_callback_failing_mid_train_quiesces_like_any_other_fault` (L1) | holds |
| "The write hold-off gates *initiating* transmissions only: acknowledgements are always sent" | `_write_frame_with_ack()` → `_await_write_gate()`; `_send_ack()` ungated | `test_an_ack_is_sent_even_while_the_write_hold_off_is_active` (L1) | holds |
| (D, A.U17.06) "Its deadline is a `ticks_ms()` value one window ahead, so one found more than a window away has aged past `ticks_diff()`'s horizon (a link idle for over 6.2 days) and counts as expired." | `_await_write_gate()` (`remaining > self._resync_window_ms()`); changelog B72 | `test_a_hold_off_aged_past_the_tick_horizon_expires`, `test_the_aliased_band_holds_at_most_one_window`, `test_an_unaged_hold_off_releases_at_its_window`, `test_the_hold_off_deadline_survives_the_ticks_rollover` (L1, `tests/_ticks30.py`) | holds, text at D |
| (D, A.U17.17) "A responder's listen loop backs off only after a listen that returns no command kind; after a validated command that was answered, declined or aborted mid-train, it listens again at once." | `_listen_loop()` (`result.cmd is not None` → backoff reset, `continue`); changelog A15 | `test_a_declined_get_does_not_back_off_the_next_answer`, `test_a_dead_link_still_doubles_its_backoff`, `test_the_listen_loop_backs_off_on_a_dead_link_and_resets_after_success` (L1) | holds, text at D |
| "**Unsticking from outside.** ... cancel the in-flight read from outside the lock ... or ... take the lock and drain directly" / handshake "latched and bounded" | `clear()` → `drv.cancel_read_timeout()` (sequences masked to `COUNTER_CAP`, compared by `_SEQ_HALF` distance, changelog B70) | `test_clear_cancels_first_and_drains_exactly_once`, `test_clear_with_nothing_in_flight_takes_the_lock_and_drains`, `hz._check_clear_terminates_even_while_a_listener_is_parked_forever`; `dt.test_cancel_with_a_wedged_holder_is_bounded_and_counted`, `dt.test_a_cancel_at_the_counter_cap_wraps_and_is_acknowledged` (L1) | holds (C.3.2 "monotonic" wording follows at D) |
| "**The drain is bounded** (changelog A5)" | `_drain()` (`bound_ms = quiet_ms * _DRAIN_BOUND_MULT`) | `test_the_drain_is_bounded_against_a_peer_that_never_stops` (L1) | holds |
| "`setup()` runs one at boot before the readiness gate opens ... shortens only its *first* probe" | `setup()` → `_drain(device, first_ms=...)` before `initialized = True` | `test_setup_drains_a_partial_frame_left_over_from_before` (L1) | holds |
| "Hitting the bound is reported by flagging the caller ... only a drain that hits its bound persists its warning (`wrnno` 54)" | `_drain()` sets `_drain_bound_hit` (cleared before any early return, changelog B73); `_resync()` persists `_WRN_UART_DRAIN_BOUND` | `test_a_drain_that_hits_its_bound_persists_the_drain_warning`, `test_a_boot_drain_that_hits_its_bound_persists_nothing`, `test_a_drain_that_cannot_run_clears_the_previous_drains_verdict` (L1) | holds |

## J.6 Deployment parameters

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "`payload_size` and `timeout` are **agreed out of band and must match on both ends** — nothing is negotiated" | no negotiation code; `TransferLimits`/`DEFAULT_LIMITS` (`_DEFAULT_PAYLOAD_SIZE`, `_DEFAULT_TIMEOUT_MS`) | `tw.test_both_instances_share_one_set_of_protocol_parameters` (L2) | holds |
| "the module logs that signature (`errno` 89)" | `_resync()` (`drained and self._valid_frames == 0`, streak `_DIAG_RESYNC_STREAK`, saturating, changelog B74) | `test_the_blind_resync_streak_saturates`, `hz._check_a_peer_that_never_produces_a_valid_frame_is_diagnosed` (L1); `tw.test_a_payload_size_mismatch_is_diagnosed_as_unintelligible` (L2) | holds |
| "**That diagnostic has a known blind spot, accepted rather than fixed**" ... "`errno` 89 never fires" for a speak-when-spoken-to peer | `_resync()` adds `_take_discarded()` (driver `discarded_bytes`, changelog B26/B59); `_read_frame()` counts a wrong-length delimited frame (B76) | `test_bytes_a_failed_frame_read_dropped_count_toward_the_link_diagnostic`, `test_a_delimited_frame_of_the_wrong_length_counts_as_discarded`, `test_the_discard_count_is_read_across_its_wrap`, `hz._check_a_peer_that_never_produces_a_valid_frame_is_diagnosed`, `hz._check_a_peer_whose_frames_all_fail_their_crc_is_diagnosed` (L1); `tw.test_a_payload_size_mismatch_is_diagnosed_as_unintelligible` (L2) | text diverges: the blind spot is closed; A.U17.15's J.6 rewrite ("**Bytes a failed frame read drops count toward it** (owner, 2026-09-26) ...") lands at D, with `errno` 89 in place of the packet's 32 |
| "`payload_size` must be in `1 … 255` ... must never be silently clamped" | `_validate_link()` → `_ERR_UART_PAYLOAD_SIZE` | `test_payload_size_boundaries_are_accepted_and_refused`, `test_payload_size_is_never_silently_clamped` (L1) | holds |
| "Maximum transferable payload is `(0xFF - 1) × payload_size`" | `_chunk_count()`; the instance's `max_transfer_bytes` caps it further (`_over_cap()`, changelog A16/B65) | `test_a_stream_of_the_largest_declarable_size_completes_and_one_more_byte_is_refused`, `test_a_train_at_the_cap_is_accepted` (L1) | holds as the protocol bound; the cap sentence (J.6/J.8, OR143.a) lands at D |
| "**A `UART` instance driving this protocol must therefore be constructed with a single-digit `poll_wait_ms`**" | `_validate_link()` → `_ERR_UART_POLL_RATE` (`_POLL_WAIT_MAX_MS`) | `test_a_poll_rate_outside_one_to_nine_ms_is_refused` (L1) | holds; (D, A.U17.20) "Both also have a ceiling: `poll_wait_ms` is refused outside 1 … 9 ms (its own code, `UART_POLL_RATE`), and `timeout` above 89,478,485 ms ... Nothing is clamped." lands at D |
| (D, A.U17.20) `timeout` above 89,478,485 ms is refused | `_validate_link()` with `_max_timeout()` (`_TICKS_HORIZON_MS`) | `test_the_timeout_ceiling_keeps_every_deadline_a_valid_tick_delay`, `test_the_backoff_stays_a_valid_tick_delay_at_the_timeout_ceiling` (L1) | holds, text at D |
| "a second, slower `poll_idle_ms` for a wait with no deadline" | `drv.ready()` | `dt.test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not` (L1) | holds |
| "**That is a construction refusal, not just a rule** — `timeout`'s floor ... carries `poll_idle_ms`" | `_min_timeout()` in `_validate_link()` | `test_an_idle_poll_rate_the_reply_budget_cannot_cover_is_refused`, `test_timeout_below_the_gc_pause_floor_is_refused` (L1) | holds |
| "**`rxbuf` is checked at construction against two independent floors**" | `_min_rxbuf()` in `_validate_receive()` | `test_maximum_payload_size_against_the_default_rxbuf_is_refused`, `hz._check_a_receive_buffer_smaller_than_a_frame_is_refused_at_construction` (L1) | holds |
| "The bytes themselves land in the link's DMA receive ring ... a power of two of `rx_ring` bytes" | `drv.setup_rx_ring()` (`rx_ring` public, refusal cause in `rx_ring_refusal`, changelog B60) | `dt.test_the_ring_size_is_public_and_set_by_init`, `dt.test_a_refused_ring_names_its_cause`, `test_a_ring_refused_at_setup_names_its_cause` (L1) | holds |
| (D, OR141.a (4), A-37) the ring floor: one framed frame, one poll interval, and what the peer sends while one config flush holds the loop (`_FLASH_HOLD_MAX_MS`), rounded to a power of two, refused with `errno` 78 | `_min_rx_ring()` in `_validate_receive()`; changelog B68 | `test_a_ring_too_small_for_one_poll_interval_is_refused`, `test_the_ring_floor_covers_a_config_flush`, `test_a_ring_below_its_floor_is_refused`, `test_a_ring_at_its_floor_holds_a_config_flush` (L1) | holds, text at D |

## J.7 Testing: the loopback model

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "one Python instance as initiator and one as responder must interoperate perfectly" | `tests/_uart_comm_harness.py` (`Pair`), `tests/machine.py` `UARTLink`, `digital_twin/machine.py` | `test_a_clean_write_round_trip_is_acknowledged` (L1); `tw.test_a_get_and_a_set_both_complete_with_no_errors_counted` (L2) | holds |
| "a lap is the receive-buffer overrun of the fault list above — detected, counted and resynced, never read as data" | `drv._rx_copy()`/`_rx_discard()` (`rx_overruns`); `_read_frame()` persists `_WRN_UART_RX_OVERRUN` (changelog B75); `_drain()` treats an overrun as traffic | `dt.test_a_lap_is_an_overrun_never_data`, `test_a_lapped_ring_is_a_receive_overrun_and_the_link_resyncs`, `test_a_frame_read_failing_on_a_receive_error_persists_the_overrun_warning`, `test_a_flood_that_laps_the_ring_drains_to_its_bound_not_as_quiet` (L1) | holds |
| "All three therefore run on a poll-round clock" (hammer, retention, faulted hammer) | `tests/_uart_comm_harness.py` `PollRoundClock` | `hz._check_a_host_stall_cannot_fail_the_retention_check`, `hz._check_a_host_stall_cannot_fail_the_sustained_hammer`, `hz._check_a_host_stall_cannot_fail_the_faulted_hammer` (L1) | holds; the hazard file runs them on the shared harness clock (A-12) |
| "**Constraint — a loopback harness must never register a fake UART with a real `select.poll()`.**" | `tests/_uart_comm_harness.py` `LinkPoller`; `dt._StepPoller` | (structural; CLAUDE.md known hang) | holds |

## J.8 Memory model

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "**Two long-lived frame buffers per instance**, `RegionBuffer(framing.max_encoded(5 + payload_size + crc_length), ...)` ... Steady-state frame traffic allocates nothing." | `_allocate()` | `test_tx_and_rx_buffers_are_separate`, `hz._check_a_long_run_of_transactions_retains_no_memory` (L1) | holds |
| "**The receive DMA ring** ... allocated once in the link's `setup()` ... held for the program's life" | `setup()` → `drv.setup_rx_ring()` | `dt.test_the_ring_is_allocated_once_in_setup` (L1) | holds |
| "**Paired transfer APIs.**" | `uart_set()`/`uart_set_into()`/`uart_set_stream()`, `uart_get()`/`uart_get_into()`/`uart_get_stream()` | `test_both_halves_of_each_pair_move_identical_bytes`, `test_a_payload_can_be_streamed_from_a_pull_callback`, `test_a_payload_can_be_streamed_into_a_push_callback` (L1) | holds |
| "**Preallocate from `CHUNKS`, never grow.** The total upper bound `CHUNKS × payload_size`" | `_dest_size()` (`upper = (chunks - 1) * self._payload_size`) | `test_an_answer_that_exactly_fills_its_train_arrives_intact` (L1) | text diverges: the bound is `(CHUNKS − 1) × payload_size` (chunk 1 carries the id); A.U17.03's J.8 text lands at D |
| (D, OR143.a) a train with no caller destination is assembled in pieces of at most `chunk_bytes`; a declared size over `max_transfer_bytes` is refused before any allocation | `_get_unlocked()`/`_accept_set()` (`_over_cap()` before `PieceBuffer(room, self._chunk_bytes)` and before the ACK); `_recv_train()` → `PieceBuffer.write_at()`; changelog A16, B64, B65 | `test_a_dont_care_get_arrives_in_pieces_no_larger_than_chunk_bytes`, `test_a_dont_care_set_is_assembled_in_pieces_no_larger_than_chunk_bytes`, `test_a_declared_size_over_max_transfer_bytes_is_refused_before_any_allocation`, `test_an_expected_size_over_the_cap_is_refused_before_any_allocation`, `test_a_transfer_over_the_own_cap_is_refused_before_anything_is_sent`, `test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat` (L1) | holds, text at D |
| "**A failed allocation degrades to the module's normal failure sentinel** and the quiesce-and-resync path, never an exception (J.1)." | construction allocations still degrade (`_allocate()`, `_buffers_ready()`); the receive pieces' `MemoryError` is no longer caught (OR143.a, owner, 2026-10-05; the listen loop's broad catch and the task supervisor are the backstop) | `test_a_failed_buffer_allocation_degrades_every_entry_point`, `test_a_partially_failed_allocation_refuses_construction_outright` (L1) | text diverges: J.8's rewrite (A-8) lands at D |
| "**Padding must be zero-filled from a preallocated zero buffer**" | `_prepare_tx()` (`self._zero`) | `test_padding_is_zero_filled_from_the_preallocated_buffer` (L1) | holds |

## J.9 Module contract: shape, results and sentinels

| Part J statement (quoted) | code site | test (level) | status |
|---|---|---|---|
| "**A plain class, not a `SensorReader` subclass**" ... "A responder takes its callbacks as one `ResponderCallbacks(get, set, message)` object" | `class UARTComm`, `ResponderCallbacks`; `_validate_receive()` refuses a responder without both | `test_a_responder_without_callbacks_is_refused_at_construction` (L1) | holds |
| "`uart_get()` returns `None` or a right-sized buffer that may be zero-length; the `_into` and streaming forms mirror it as `None` versus 0 bytes written" | `uart_get()` returns a `PieceBuffer` trimmed to the bytes received (zero-length when empty); `uart_get_into()`/`uart_get_stream()` return the count | `test_an_empty_payload_is_a_distinct_outcome_from_failure`, `test_an_empty_answer_into_a_buffer_is_zero_not_none` (L1) | text diverges in shape only: A-25's "`None`, or the received bytes — a `PieceBuffer`, possibly empty, when no destination was given" lands at D |
| "`exp_size=None` is *don't care*, `exp_size=0` is *must be exactly empty*" | `_run_get()` → `_get_unlocked()` (`want = -1` for `None`), `_dest_size()` | `test_all_three_expected_size_modes` (L1) | holds |
| "**`uart_listen()` returns a `ListenResult` namedtuple** ... on every path" | `uart_listen()`, `_LISTEN_FAILED`, every `ListenResult(...)` return in `_listen_unlocked()`/`_answer_get()`/`_accept_set()` | `test_uart_listen_returns_the_namedtuple_on_every_path` (L1) | holds |
| "**A lost final ACK folds into failure**" | `_recv_train()` / `_write_frame_with_ack()` | `test_a_lost_final_ack_reports_failure_while_the_receiver_reports_success`, `hz._check_a_lost_final_ack_is_reported_as_failure_though_the_peer_acted` (L1) | holds |
| (D, A.U17.01) "Every initiation entry point checks in one order — role and readiness gate, command id, buffer or callback, size — and refuses with the first finding." | `uart_get()`, `uart_get_into()`, `uart_get_stream()`, `uart_set_into()`, `uart_set_stream()`, shared tail `_run_get()`; changelog B71 | `test_every_initiator_entry_point_answers_not_initialised_before_setup`, `test_a_responder_refuses_the_role_before_any_argument`, `test_the_command_id_is_checked_first_on_an_initiator` (L1) | holds, text at D |

## Findings of this trace

- No code site fails its statement: every "text diverges" row is Part J's text trailing the U17 code, and each names the
  lane D step that rewrites it at U17 (A.U17.03, A.U17.08, A.U17.11, A.U17.15, A-8, A-25).
- No Class A divergence beyond the changelog's A14-A16 (GET `CHUNKS`, listen re-listen, the receive cap); the ring is
  Class B (B68), as M.PROC.017 states.
- Lane H's hazard rows (the GET `CHUNKS` sweep, the inverted never-valid diagnostic and its CRC form, the shared
  poll-round clock) are in place at `79b2cce` and read above.
