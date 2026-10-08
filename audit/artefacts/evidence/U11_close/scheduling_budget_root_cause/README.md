# U11 root cause: three "flaky" failures, one mechanism

Worktree: `scratchpad/wt-u11rc` (detached at `d1f3878`, scratch edits only, nothing committed).
Every number below comes from a log in `logs/`. All reproduction is **in-process stall injection**:
the interpreter is blocked with `time.sleep_ms(D)` at one chosen point, which is exactly what a host
deschedule looks like to MicroPython (wall clock moves, no Python code runs). No host CPU load was
generated. Binary: `/root/pico-toolchain/micropython/ports/unix/build-standard/micropython`, env as
`scripts/test.sh` (`TZ=UTC`, `MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen`,
plus `ext` for the webserver file), `-X heapsize=16M`; the 32768 stage is `gc.threshold(32768)` set
the way `tests/_threshold_runner.py` sets it (the injectors take the threshold as an argument).

**Verdict for all three: test assumption about real-time scheduling, not a product bug.** Each test
needed two wall-clock events, started at different moments, to happen in a fixed order (or within a
fixed budget). A host stall longer than the gap between them swaps the order; the product then does
exactly what its spec says for the order that actually happened. Each fix removes the race
structurally (no wider tolerance, no retry), and each fixed test still fails on planted real defects.

| case | test | flip threshold | product verdict | fix |
| --- | --- | --- | --- | --- |
| 1 | `test_uart_comm_hazard.py` `..._size_mismatch_against_an_expected_size_..._nocrc` | one stall > 30 ms (31 ms flips 3/3, 30 ms flips 0/3) in 3 windows | correct per J.4/J.5 | peer's answer pre-queued |
| 2 | `test_asy_webserver_service.py` `test_a_read_timeout_then_a_capped_400_write_...` | one stall > 100 ms (102 ms flips, 98 ms does not) in 1 window | correct (cap fired first, so it is the cap's reclaim) | virtual clock for the module's `wait_for()` timers |
| 3 | `test_uart_comm_hazard.py` `..._lost_final_ack_..._nocrc` | one stall > 30 ms in 2 windows | correct per J.4 | initiator and responder run against pre-queued frames, real bytes chained |

---

## Case 1: size mismatch (`_check_a_size_mismatch_against_an_expected_size_reports_it_distinctly`)

### 1. What `errnos()` contains on the failing path

Clean run (`logs/` via `inject_stall.py ... count`): initiator `[84]` (UART_SIZE_MISMATCH),
responder `[81]` (UART_NO_ACK - expected: J.4 withholds the final ACK on a rejected train, so the
responder times out waiting for it).

Flipped runs (`logs/sweep_orig_*`, `logs/phase_trace_orig_post_D40.log`): the initiator holds
**exactly one** errno, never 84:

| stall lands while ... | initiator | responder |
| --- | --- | --- |
| initiator waits for the ACK of its GET (`I._read_frame#1`) | `[81]` UART_NO_ACK | `[81]` |
| responder waits for the ACK of its answer header (stall during `I._read_frame#2`) | `[22]` TIMEOUT | `[81]` |
| initiator waits for data chunk 2 (`I._read_frame#3`) | `[22]` TIMEOUT | `[81]` |

There is only ever one initiator entry because every fault path in `_get_unlocked()` returns after
its first `_fault()`. So SIZE_MISMATCH was not "recorded and then overwritten": it was **never
reached**. The gate log's empty `AssertionError` at line 671 (`last_errno(...) == 84`) is one of
`[81]` or `[22]`; which one cannot be read back from that log (no message), but all three windows
are equally reachable.

### 2. Causal chain

`asy_uart_driver.UART.ready()` (`src/asy_uart_driver.py`) takes `t0`, polls, and if no data is there
checks `ticks_diff(ticks_ms(), t0) > timeout_ms` before sleeping `poll_wait_ms` (1 ms here). The
mock link (`tests/machine.py` `UARTLink`) delivers synchronously, so the 30 ms `timeout` measures
nothing but how soon the peer task is scheduled (SPECIFICATION.md J.7 says exactly this). When the
whole process is descheduled for > 30 ms while one side is parked in that loop, the parked task's
deadline is the earliest overdue one in asyncio's queue, so it runs **before** the peer: it polls,
finds nothing (the peer has not run), sees elapsed > 30 and returns False. Then:

- window 1: `_write_frame_with_ack()` -> `_fault(UART_NO_ACK, "no ACK for frame")` -> resync drain;
  the responder later reads the GET, ACKs and sends its header into the initiator's drain, then
  times out on its own header ACK -> responder `[81]`.
- window 2 (trace in `logs/phase_trace_orig_post_D40.log`): the initiator had its header in time,
  but the **responder's** wait for the header ACK (`_write_frame_with_ack()` in `_send_train()`)
  ran first after the stall, saw 41 ms elapsed and failed with NO_ACK, then drained 45 ms; the
  initiator's header ACK went into that drain, so `_recv_train()` waited for chunk 2 in vain ->
  `_fault(TIMEOUT, "train stalled at chunk", 2)`.
- window 3: `_recv_train()`'s `_read_frame()` for chunk 2 -> same TIMEOUT.

Threshold (`logs/threshold_sweep_orig.log`, 3 repeats per cell, both stages):

| window | 20-29 ms | 30 ms | 31+ ms |
| --- | --- | --- | --- |
| GET ACK wait | 0/3 | 0/3 | 3/3 |
| header ACK wait (responder side) | 0/3 (29 ms: 2/3 at 32768) | 3/3 | 3/3 |
| chunk-2 wait | 0/3 | 0/3 | 3/3 |

The responder-side window flips 1-2 ms earlier because that side had already waited 1-2 ms before
the stall. GC threshold does not change the mechanism: it flips identically at -1 and 32768; 32768
only adds collection pauses, i.e. more chances of a stall. The gate ran this file first in its 32768
stage at minute 0-2, where vmstat shows a run queue of 13-36 on 4 cores - a > 30 ms deschedule of
one interpreter is routine there.

### 3. Protocol verdict

Correct per Part J. J.5: "Waiting for a *new* message is ... bounded by `timeout` (an initiator
awaiting a reply)", and "On any fault — ... size mismatch, missing ACK — the side that noticed drains
its receive path". A reply that has not arrived when the bound expires is a missing reply; the
module cannot tell a descheduled peer from a silent one, and on the real link the peer is a
separate MCU. J.4's order (incremental size check, final exact check, final ACK deferred until it
passes) is what the clean run shows; there is no errno-order rule that a late reply violates,
since each call reports the first fault it saw and stops. J.7 already names the cause: "The mock
tier's `timeout` is a scheduling budget, not a wire budget", with the no-CRC arm at **1.25x** margin.
No wire bytes are involved in either the cause or the fix. **Test assumption, not a protocol bug.**

Side finding (test defect, fixed by the same patch): the check took `crc` but built its `Pair`
without one, so the `_crc16` arm ran the no-CRC layout twice. The only other `_check_` that ignores
`crc` is `..._receive_buffer_smaller_than_a_frame_...`, where it is irrelevant by construction.

### 5. Fix (`fix_uart_hazard.patch`, first hunk)

The peer's whole answer (ACK for the GET, header echoing id 0x01, 2-byte data chunk) is queued on
the initiator's receive side **before** the call. `ready()` polls before it checks the deadline, so
every read finds its frame waiting and no stall can expire a budget. It also asserts more than
before: the exact errno list `[84]` (not just the last one), and the initiator's wire bytes equal
GET + header-ACK with **no final ACK** (J.4's deferred ACK); the `_crc16` arm now really uses CRC16.

Proof:
- Stall at **every** asyncio sleep point of the run, one at a time (`exposure_sweep.py`, stride 1),
  D = 40 ms and 250 ms, both stages (`logs/proof_fixed_vs_orig_ksweep.log`): original flips 7-12 of
  126-143 points in every cell; fixed **0 of 56-62** (nocrc) and **0 of 328-348** (crc16).
- Planted defects (`planted_A/B/C`, `logs/planted_defects.log`), each run on original and fixed test
  at both stages:
  - A, final exact-size check removed (mismatch never reported, short answer delivered): fixed FAILS (orig fails).
  - B, mismatch reported under errno 22: fixed FAILS with `got [22]` (orig fails).
  - C, final ACK sent before the size check (J.4 violation): fixed FAILS ("final chunk was acknowledged");
    **original PASSES** (it is still caught elsewhere, by `test_asy_uart_comm.py`'s
    `test_all_three_expected_size_modes`, `logs/planted_C_rest_of_suite.log`).
- Whole file with the patch: 98/98 plain and 98/98 at 32768, zero MemoryError markers
  (`logs/fixed_full_file_*.log`). ruff clean, `scripts/typecheck.sh` PASS (all passes),
  `tests_scripts/test_comment_block_cap.py` passes.

### 6. Failing test for a protocol bug

None: no protocol bug was found, so none is written.

---

## Case 3: lost final ACK (`_check_a_lost_final_ack_is_reported_as_failure_though_the_peer_acted`)

The handler's output (`scratchpad/u11h/uart_hazard_failure.txt`) fails at
`tests/test_uart_comm_hazard.py` line 1133, in `_clean_ack_bytes`: the probe's clean
`uart_set(0x02, b"acted-on")` returned False.

Reproduced with the same injection (`logs/lost_final_ack_orig_D40.log`, stride 1, D = 40 ms, both
stages): 18 of 177 stall points flip, in two windows:
- k = 40-51: **`AssertionError @ line 1133, in _clean_ack_bytes`** - the exact reported failure. The
  probe is a clean live SET at 30 ms; a > 30 ms stall while either side waits for an ACK or a chunk
  makes that side time out first (case 1's mechanism) and the SET returns False.
- k = 50-62: `the responder did not actually receive the train: []` (line 1177) - the stall lands in
  the real scenario before the train completes, so the initiator or the responder times out early
  and the responder never delivers.

Same mechanism, same verdict: product correct per J.4 ("a sender learns its transfer was rejected by
timing out"); the test needed two live 30 ms exchanges to be scheduled in time.

Fix (`fix_uart_hazard.patch`, second hunk), same technique, and `_clean_ack_bytes` is no longer
needed (its live probe was itself racy). Sequenced so every read finds its data waiting:
1. Only the header's ACK (uid 1) is queued for the initiator; `uart_set()` sends header + chunk 2,
   gets ACK 1, then times out on the final ACK - lost by construction (a timeout is the expected
   outcome here, and a stall can only make a timeout sooner). Asserts `False` and errnos
   `[81]` UART_NO_ACK exactly (stronger than "some errno").
2. The real responder then `uart_listen()`s the very bytes the initiator put on the wire (already in
   its receive queue): asserts payload `b"acted-on"` and that its wire output is exactly ACK(uid 1) +
   ACK(uid 2) - which also proves the scripted ACK in step 1 is byte-identical to the real one.

Proof:
- Stall sweep, every point, D = 40/250, both stages (`logs/lost_final_ack_fixed_proof.log`):
  **0 of 88-91** (nocrc) and **0 of 547-562** (crc16) flip; the original flips 18/177.
- Planted (`planted_L1/L2`, `logs/lost_final_ack_planted.log`), original and fixed, both stages:
  - L1, missing final ACK taken as success: fixed FAILS ("reported as success"), orig fails.
  - L2, responder drops the accepted payload: fixed FAILS ("did not actually receive"), orig fails.
- Whole file 98/98 at both stages after both hunks (`logs/fixed_full_file_*.log`).

---

## Case 2: webserver read timeout then capped 400 write

`test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code`: `_serve()` with
`per_call_timeout_s=0.2`, `outer_cap_s=0.3`, a reader that never yields and a writer that hangs.
Expected WEBSERVER history ends `[49 HTTP_CALL_TIMEOUT, 50 HTTP_REQUEST_CAP]`, ErrCount 2.

Injector `web_inject.py`: every `asyncio.wait_for()` that `src/asy_webserver_service.py` makes goes
through a shim; on the n-th call the interpreter blocks D ms before (`pre`) or right after (`post`)
that call's deadline is fixed. Clean trace (`logs/web_traces_orig.log`): `wait_for#1` (outer cap,
0.3) at 0 ms, `#2` (read, 0.2) at 0 ms -> TimeoutError at 201 ms (W49 logged by
`_TimeoutStreamProxy._bounded_read()`), `#3` (the 400's write, 0.2) at 201 ms -> cancelled at 300 ms
by the cap -> `_serve()` logs W50 because `timed_out[0]` is False.

**Reproduced** (`logs/web_sweep_orig.log`, 42 cells x 2 stages): flips exactly when D > 100 ms
(102, 110, 150, 250 flip; 50, 90, 98 do not) at `post#1` or `pre#2`, i.e. in the window **after
the cap's deadline is fixed and before the read's deadline is fixed** (the request task has been
created but has not yet reached microdot's first `readline()`). Failing history: `[..., 50]`,
ErrCount 1 - the W49 is missing.

Causal chain: the read deadline becomes `t_read_start + 0.2` while the cap stays `t0 + 0.3`; a stall
> 100 ms in that window puts the read deadline after the cap. The cap's `wait_for()` fires first and
cancels the request task while it is still inside the read's `wait_for()`; the read therefore ends
in `CancelledError`, not `TimeoutError`, so `_bounded_read()` correctly logs nothing, and `_serve()`
logs W50 (the cap). Stalls anywhere else do not flip (`post#2`, `pre#3` with 250 ms pass): once both
deadlines are fixed they keep their order, and asyncio pops the earliest-due task first.

**Product verdict: correct.** The connection really was reclaimed by the cap before any per-call
bound expired, so one W50 is the truthful history. The test assumed the request task reaches its
first read within 100 ms of `_serve()` starting.

Fix (`fix_webserver_capped_400.patch`): the module's `asyncio` is swapped, for this test only, for
a namespace whose `wait_for()` is MicroPython's own `wait_for()` given a virtual sleep (the third
argument `extmod/asyncio/funcs.py` already takes). Deadlines elapse only when the test advances
`clock.now`: after the read has started (0.2, read due, cap not), and after the 400 write has
started (0.3, cap due, the write's own 0.2+0.2 bound not). Same timeouts, same real `_serve()`,
proxy, microdot and fakes. One MicroPython detail is load-bearing and commented: the virtual sleep
must yield (`sleep_ms(0)` loop) rather than wait on an Event, because `wait_for()`'s runner only
cancels a waiter whose task `data` is `None`.

Proof:
- `web_inject_fixed.py` stalls the n-th virtual `wait_for()` pre/post, n = 1..4, D = 102, 250, 1500
  and 3000 ms, plus a stall on every call (8 x 100 ms, 8 x 400 ms), both stages:
  **68/68 PASS** (`logs/web_sweep_fixed.log`). The only wall-clock bound left is `run_timed()`'s
  hang backstop (default 5 s); an earlier draft kept the original 2 s and 8 x 400 ms then hit it as
  a loud `TimeoutError`, never as a wrong classification.
- Planted (`planted_W1/W2`, `logs/web_planted_defects.log`), original and fixed, both stages:
  - W1, a read timeout sets `timed_out[0]` (cap misclassified): fixed FAILS (history ends `[49]`), orig fails.
  - W2, the read-phase timeout is no longer logged: fixed FAILS (`[..., 50]`, ErrCount 1), orig
    fails. Note this defect's signature is **identical** to the stall flip of the original test - the
    original could not tell a real regression from a scheduling stall.
- The 42 fake-driven tests of the file (`web_exposure_names.txt`) with the patch: 42/42 plain and
  42/42 at 32768 (`logs/fixed_webserver_fakes_subset_th*.log`). The 6 tests that bind real sockets
  were not run here (other agents' suites bind ports on this host; CLAUDE.md's port rule).
  ruff clean, `scripts/typecheck.sh` PASS.

---

## 4. Exposure sweep

Method: `exposure_sweep.py` re-runs every test function of a file with **one** stall of D ms right
after the k-th `asyncio.sleep_ms()` inside `asy_uart_driver`/`asy_uart_comm` (deadline already
fixed, so the parked task is overdue on wake), for k over the whole run (stride 1, or about 150
evenly spaced points per test, `-N` = about N points). `web_exposure.py` does the same at each
`wait_for()` of `asy_webserver_service` (pre and post). "confirmed flip" = the test failed under
that single stall; numbers are flipping points / tested points. Run against the **original**
(`orig/`) files. Tests marked "no flip" were sampled, not proven immune, where stride > 1.

Summary (confirmed flips by one injected stall, original files):

| file | budget the stall must beat | confirmed flips | sampled, no flip |
| --- | --- | --- | --- |
| `test_uart_comm_hazard.py` `_nocrc` | 30 ms | **14** (incl. cases 1 and 3) | 35 |
| `test_uart_comm_hazard.py` `_crc16` | 240 ms | 9 (2 more not swept, > 4 s) | 38 |
| `test_asy_uart_comm.py` | 100 ms | 27 (6 not swept, > 4 s) | 118 |
| `test_asy_uart_link_driver.py` | 100 ms | 3 | 19 |
| `test_asy_uart_driver.py` | 40 ms upper bound | 1 | 113 |
| `test_asy_webserver_service.py` (fake-driven 42) | 100 ms gap (case 2) | 1 at 250 ms, 9 at 1000 ms | 40 / 32 |

Three shapes, and the technique that removes each:
1. **A live exchange must complete inside a short reply budget** (every "recovers to a working
   exchange", "round trip", "probe GET" check, the `_clean_ack_bytes`-style probes). Threshold =
   the budget. Fix shape: queue the peer's frames before the call (cases 1/3), or, where the test
   is about two live instances interoperating, accept that it is a scheduling-budget test and size
   the budget as J.7 already did for `_hammer_clean`/`_measure_retention` (that keeps a threshold,
   so it is mitigation, not independence). A deterministic alternative for those is a harness-level
   poll-round clock (patching `asy_uart_driver.time`/`asy_uart_comm.time` with a clock advanced
   only by the driver's own sleeps); not built here because it changes every UART test at once.
2. **Two wall-clock deadlines started at different moments must fire in order** (case 2 and the
   webserver flips at 1000 ms). Fix shape: the virtual `wait_for()` clock of case 2.
3. **A wall-clock upper bound on elapsed time** (`test_asy_uart_driver.py`'s
   `test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not`, `< 40 ms`; the two
   hammer/retention checks at 240 ms, whose retention figures change when a stall turns a clean
   transaction into a failed one - the nocrc `hammering_a_faulted_link` flip, 27.7 B/failure > 16,
   is this). Fix shape: assert on poll-round counts (the `_StepPoller` already counts rounds), not ms.

Only cases 1-3 were fixed here, as asked. Everything below is evidence for planning the rest.

### `tests/test_uart_comm_hazard.py`, `_nocrc` arm, D = 40 ms

Budget: `timeout` 30 ms (`_SUSTAINED_TIMEOUT_MS` 240 ms for the two clean-run tests). Threshold: one stall > 30 ms.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_break_like_run_of_nulls_recovers_to_a_working_exchange_nocrc` | confirmed flip | 10/124 |  AssertionError: the link never recovered from a break-like null run |
| `test_a_corrupted_byte_stream_recovers_to_a_working_exchange_nocrc` | confirmed flip | 8/183 |   |
| `test_a_dropped_byte_mid_frame_recovers_to_a_working_exchange_nocrc` | confirmed flip | 10/239 |  AssertionError: the link never recovered after a dropped byte |
| `test_a_frame_delivered_in_two_fragments_still_assembles_nocrc` | confirmed flip | 15/39 |   |
| `test_a_lost_final_ack_is_reported_as_failure_though_the_peer_acted_nocrc` | confirmed flip | 12/176 |   |
| `test_a_peer_initiating_mid_transaction_is_detected_and_both_recover_nocrc` | confirmed flip | 6/118 |   |
| `test_a_receive_overrun_recovers_to_a_working_exchange_nocrc` | confirmed flip | 9/203 |   |
| `test_a_second_call_during_a_transaction_is_refused_with_a_sentinel_nocrc` | confirmed flip | 10/35 |   |
| `test_a_size_mismatch_against_an_expected_size_reports_it_distinctly_nocrc` | confirmed flip | 9/145 |   |
| `test_a_truncated_frame_recovers_to_a_working_exchange_nocrc` | confirmed flip | 6/207 |   |
| `test_duplicated_bytes_on_the_wire_recover_to_a_working_exchange_nocrc` | confirmed flip | 6/244 |  AssertionError: the link never recovered after duplicated bytes |
| `test_hammering_a_faulted_link_never_raises_and_still_recovers_nocrc` | confirmed flip | 1/155 |  AssertionError: 832 bytes over 30 failures = 27.7 B/failure |
| `test_injected_noise_before_a_real_frame_is_recovered_from_nocrc` | confirmed flip | 7/184 |   |
| `test_one_sided_silence_recovers_once_the_direction_returns_nocrc` | confirmed flip | 7/210 |   |

No flip at any sampled point: 35 further tests (full list in `logs/exposure_hazard_nocrc_D40.log`).


### `tests/test_uart_comm_hazard.py`, `_crc16` arm, D = 250 ms, ~40 points per test

Budget: 240 ms (`_TIMEOUT_MS x _CRC_TIMEOUT_FACTOR`, and the sustained 240 ms). Threshold: one stall > 240 ms.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_break_like_run_of_nulls_recovers_to_a_working_exchange_crc16` | confirmed flip | 1/42 | line 904 AssertionError: the link never recovered from a break-like null run |
| `test_a_dropped_byte_mid_frame_recovers_to_a_working_exchange_crc16` | confirmed flip | 1/41 | line 694 AssertionError: the link never recovered after a dropped byte |
| `test_a_frame_delivered_in_two_fragments_still_assembles_crc16` | confirmed flip | 9/38 | line 731  |
| `test_a_long_run_of_transactions_retains_no_memory_crc16` | confirmed flip | 27/41 | line 575 AssertionError: 119 |
| `test_a_second_call_during_a_transaction_is_refused_with_a_sentinel_crc16` | confirmed flip | 12/35 | line 198  |
| `test_a_size_mismatch_against_an_expected_size_reports_it_distinctly_crc16` | confirmed flip | 3/48 | line 671  |
| `test_hammering_a_faulted_link_never_raises_and_still_recovers_crc16` | not swept (clean run > 4 s) | - | inspection only |
| `test_overrun_plus_duplication_still_converges_crc16` | not swept (clean run > 4 s) | - | inspection only |
| `test_sustained_hammering_never_degrades_or_grows_the_heap_crc16` | confirmed flip | 26/41 | line 1059 AssertionError: only 149/150 hammered transactions completed |
| `test_the_crc_appears_on_the_wire_big_endian_after_the_payload_crc16` | confirmed flip | 7/37 | line 1261  |
| `test_the_probed_payload_offset_lands_on_a_frames_payload_start_crc16` | confirmed flip | 12/37 | line 758 AssertionError: the probe GET did not complete, so no offset can be derived from it |

No flip at any sampled point: 38 further tests (full list in `logs/exposure_hazard_crc16_D250.log`).


### `tests/test_asy_uart_comm.py`, D = 110 ms, ~60 points per test

Budget: harness `TIMEOUT_MS` 100 ms (one test at `_SHORT_REPLY_TIMEOUT_MS` 30). Threshold: one stall > 100 ms.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_clean_write_round_trip_is_acknowledged` | confirmed flip | 8/29 | line 742  |
| `test_a_get_round_trip_returns_the_answer` | confirmed flip | 18/43 | line 1195  |
| `test_a_lost_final_ack_reports_failure_while_the_receiver_reports_success` | confirmed flip | 1/64 | line 807  |
| `test_a_multi_chunk_payload_arrives_byte_identical` | confirmed flip | 25/54 | line 1153  |
| `test_a_negative_expected_size_is_refused_not_read_as_dont_care` | not swept (clean run > 4 s) | - | inspection only |
| `test_a_payload_can_be_streamed_from_a_pull_callback` | confirmed flip | 20/44 | line 1402  |
| `test_a_payload_can_be_streamed_into_a_push_callback` | confirmed flip | 16/44 | line 1416  |
| `test_a_payload_less_command_still_produces_two_chunks` | confirmed flip | 8/29 | line 1081  |
| `test_a_peer_answering_a_different_question_is_refused` | confirmed flip | 1/65 | line 1898 AssertionError: ['E81'] |
| `test_a_pull_callback_failing_mid_train_quiesces_like_any_other_fault` | confirmed flip | 1/64 | line 2148 AssertionError: ('bool', ['E81']) |
| `test_a_raising_message_callback_does_not_kill_the_listen_loop` | confirmed flip | 22/46 | line 1677 AssertionError: the loop must survive its owner's raise |
| `test_a_read_only_destination_is_refused_before_the_train_starts` | confirmed flip | 7/37 | line 1550  |
| `test_a_received_train_that_cannot_be_right_sized_is_reported_not_over_reported` | confirmed flip | 9/31 | line 2024  |
| `test_a_recovered_link_counts_every_later_fault` | confirmed flip | 1/61 | line 1600  |
| `test_a_responder_still_answers_a_get_while_the_role_gate_is_active` | confirmed flip | 10/35 | line 1334  |
| `test_a_responder_that_never_finishes_its_rounds_fails_the_exchange` | not swept (clean run > 4 s) | - | inspection only |
| `test_a_right_sizing_copy_that_fails_returns_the_sentinel_not_the_padding` | confirmed flip | 11/36 | line 1975  |
| `test_a_stall_the_test_declares_is_not_a_failure` | not swept (clean run > 4 s) | - | inspection only |
| `test_a_write_failing_at_each_point_of_a_get_reports_and_resyncs` | not swept (clean run > 4 s) | - | inspection only |
| `test_a_write_that_never_reaches_the_peer_fails_the_same_way` | not swept (clean run > 4 s) | - | inspection only |
| `test_all_three_expected_size_modes` | confirmed flip | 2/62 | line 1170 AssertionError: exp_size=0 payload=b'' |
| `test_an_answer_buffer_the_heap_cannot_serve_fails_before_the_first_data_ack` | confirmed flip | 1/66 | line 1957  |
| `test_an_answer_that_exactly_fills_its_train_is_handed_back_uncopied` | confirmed flip | 8/35 | line 1753 AssertionError: None |
| `test_an_answer_the_train_could_never_carry_is_refused_at_its_header` | confirmed flip | 1/65 | line 1740 AssertionError: ['E81'] |
| `test_an_empty_payload_is_a_distinct_outcome_from_failure` | confirmed flip | 8/35 | line 1178  |
| `test_an_out_of_range_command_id_is_refused_not_truncated` | not swept (clean run > 4 s) | - | inspection only |
| `test_both_halves_of_each_pair_move_identical_bytes` | confirmed flip | 29/81 | line 1348  |
| `test_both_sync_and_async_callbacks_work` | confirmed flip | 12/37 | line 1246  |
| `test_listening_clears_the_hold_off` | confirmed flip | 13/36 | line 849  |
| `test_the_legacy_bsec_command_set_still_runs_end_to_end` | confirmed flip | 24/64 | line 2236 AssertionError: None |
| `test_the_owned_listen_loop_delivers_a_received_payload` | confirmed flip | 8/31 | line 1651  |
| `test_the_two_spellings_the_boards_own_uart_script_used_still_work` | confirmed flip | 2/65 | line 2258 AssertionError: None |
| `test_the_wire_log_of_a_multi_chunk_set_is_byte_exact` | confirmed flip | 17/37 | line 1093  |

No flip at any sampled point: 118 further tests (full list in `logs/exposure_asy_uart_comm_D110.log`).


### `tests/test_asy_uart_link_driver.py`, D = 110 ms

Budget: harness `TIMEOUT_MS` 100 ms.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_banner_get_across_a_real_responder_via_get_callback` | confirmed flip | 21/52 | line 212  |
| `test_echo_round_trip_across_a_real_responder_via_set_and_get_callbacks` | confirmed flip | 22/53 | line 231  |
| `test_exercise_loop_counts_a_transfer_for_a_correct_banner_answer` | confirmed flip | 21/50 | line 188  |

No flip at any sampled point: 19 further tests (full list in `logs/exposure_asy_uart_link_driver_D110.log`).


### `tests/test_asy_uart_driver.py`, D = 210 ms

Budgets: 20-200 ms deadlines; the one flip is a wall-clock *upper bound* (`< _IDLE_POLL_MS` = 40 ms on a bounded wait), so it flips at a stall > ~38 ms.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_deadlineless_wait_polls_at_the_idle_rate_and_a_bounded_one_does_not` | confirmed flip | 3/6 | line 1628  |

No flip at any sampled point: 113 further tests (full list in `logs/exposure_asy_uart_driver_D210.log`).


### `tests/test_asy_webserver_service.py` (42 fake-driven tests), D = 250 ms at every `wait_for()` pre/post

Budgets: per-call 0.05-1.0 s, cap 0.05-2.0 s.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code` | confirmed flip | 2/8 |  AssertionError: {'ErrType': ['N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'W'], 'ErrC |

No flip at any sampled point: 40 further tests (full list in `logs/exposure_webserver_D250.log.gz`).


### same file, D = 1000 ms

Flips here but not at 250 ms have a threshold between 250 and 1000 ms; `TimeoutError` = the `run_timed()` hang bound (1-2 s) overrun by the stall, the rest wrong verdicts.

| test | verdict | flipping / tested stall points | where it failed (when captured) |
| --- | --- | --- | --- |
| `test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code` | confirmed flip | 3/8 |  AssertionError: {'ErrType': ['N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'N', 'W'], 'ErrC |
| `test_an_outer_cap_timeout_logs_the_request_cap_code` | confirmed flip | 10/10 |   |
| `test_f2_content_length_larger_than_body_sent_then_silence_times_out` | confirmed flip | 10/16 |   |
| `test_f2_trickled_request_line_is_reclaimed_by_the_outer_cap_not_a_single_per_call_timeout` | confirmed flip | 10/10 |   |
| `test_f5_connection_close_header_present_on_every_response_including_errors` | confirmed flip | 10/16 |  AssertionError: /status |
| `test_f7_unknown_path_returns_404_shaped_response` | confirmed flip | 10/16 |   |
| `test_f7_wrong_http_method_on_a_known_path_returns_405_shaped_response` | confirmed flip | 10/16 |   |
| `test_h2_stream_response_has_an_explicit_correct_content_length_header` | confirmed flip | 15/16 |   |
| `test_nothing_is_written_to_a_peer_whose_read_saw_a_reset` | confirmed flip | 5/8 |  AssertionError: 1 |

No flip at any sampled point: 32 further tests (full list in `logs/exposure_webserver_D1000.log.gz`).


---

## Files

- `fix.patch` - both test files; `fix_uart_hazard.patch`, `fix_webserver_capped_400.patch` - split.
- `inject_stall.py` - case 1 phase/k injector with a full event trace (`count`, `sweep`, `phase:N`).
- `exposure_sweep.py` - per-file k-sweep (UART modules); `run_exposure_all.sh` - the sequential run.
- `web_inject.py`, `web_inject_fixed.py`, `web_exposure.py` (+ `web_exposure_names.txt`) - case 2.
- `run_only.py` - runs selected test functions (substring or `@names_file`) at a given threshold.
- `orig/` - the two test files as at `d1f3878`; `planted_*/` + `planted_*.diff` - the planted defects
  (each shadows one `src/` module via MICROPYPATH; `src/` itself is untouched).
- `logs/` - every run quoted above.

Commands (cwd = worktree, `ENV='TZ=UTC MICROPYPATH=build/generated_src:src:tests:ext:frozen_modules:.frozen'`,
`MP=.../build-standard/micropython -X heapsize=16M`, `S=scratchpad/u11rc`):

```
$ENV $MP $S/inject_stall.py -1 post 40 phase:1,2,3            # case 1 traces
$ENV $MP $S/inject_stall.py 32768 post 31 phase:1,2,3         # threshold
$ENV $MP $S/exposure_sweep.py $S/orig/test_uart_comm_hazard.py 40 100000 1 size_mismatch_against 32768
$ENV $MP $S/exposure_sweep.py tests/test_uart_comm_hazard.py 40 100000 1 lost_final_ack -1
$ENV $MP $S/web_inject.py tests/test_asy_webserver_service.py test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code post 1 110
$ENV $MP $S/web_inject_fixed.py tests/test_asy_webserver_service.py test_a_read_timeout_then_a_capped_400_write_logs_the_request_cap_code pre 2 3000 32768
MICROPYPATH=$S/planted_B:... $MP $S/run_only.py tests/test_uart_comm_hazard.py size_mismatch_against 32768
```
