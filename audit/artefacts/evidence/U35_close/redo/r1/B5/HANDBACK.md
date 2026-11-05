B5 hand-back, written by the agent (Tue Nov  3 10:26:33 UTC 2026)

Worktree `S/wt-b5`, branch `audit/r1-b5`, from 3129bf21. Commits: c29196b9 (items 3, 4, 7, 8, 15 and the
captive/UDP/NTP-7 rows of 18), 25a14b4f (items 5, 6, 9, 19 and NTP-7's receive), ce199ebb (items 1, 2, 10, 12, 13,
16 and the WS rows of 18), ce9b6be5 (a vocabulary allow-list line item 5 left stale), 21e12c76 (the rule checks and
twin tests the first gate run found, see Gate). Nothing pushed. Run logs: `S/u35/lead/b5_*.log`; the gate: `S/u35/lead/b5_gate.log` (first run) and `b5_gate2.log`.
Line numbers below are the action list's (`8019a9ef` tree) unless a file is named with a commit.

## Items

1. **Web server start retries and W62: removed** (ce199ebb). `_serve_loop()` is one `start_server()` and
   `wait_closed()`; a failed start raises out of the task and the supervisor's restart is the retry. `_START_RETRIES`,
   `_START_RETRY_S`, their two Part N rows and catalog W62 go (no placeholder). Tests: the two retry tests went first;
   `test_a_failed_start_ends_the_serve_task_for_the_supervisor` (one `start_server()` call, the OSError raised, nothing
   logged) red on the committed source (b5_ws_red), green (b5_ws_g4, b5_st3); the listening-port cancel test green.
2. **WS-2's head refusals and WS-9's merge list: removed** (ce199ebb). `_check_head_line()` works on the raw bytes and
   keeps the line, byte and count bounds and the `Content-Length` check (ASCII digits, once); the undecodable,
   request-line/version, missing-colon and `Transfer-Encoding` refusals go, as do `readexactly()`'s EOF refusal,
   `traced`, `_read_traced` and the skip; `_print_exception()` is one `self.pr.err("Microdot caught:", exc)` (no
   `report_if_fatal()`). W61's text narrows to "an oversized request head or a Content-Length that is not digits or
   comes twice was refused; answered 400". Tests changed first, red (b5_ws_red), then green:
   `test_a_body_cut_short_of_its_content_length_is_answered_by_microdot`,
   `test_malformed_head_lines_reach_microdot_which_answers_400` (the WS-2 cases now reach Microdot's 400),
   `test_a_silent_client_prints_two_lines_at_a_raised_level`. `test_client_faults_print_nothing_at_debug_level_zero`
   also read red: its per-wave tally counted the two refused heads that now reach Microdot, so it expects (40, 12, 0)
   and three codes; it still asserts nothing printed at level 0. The bound and `Content-Length` tests stayed green.
   Found by the first gate run (21e12c76): `tests_scripts/test_fatal_report_sites.py` wanted the rebound printer to
   start with `report_if_fatal()`; it now accepts a hook that logs its exception (the logger's entry records the
   overflow), as it already did for the errorhandler, with a case that a hook returning before its log still fails
   (red in b5_gate, green in b5_fix1); and the head-line count keeps its base form (`if ... <= _MAX_HEADER_LINES:
   step, else refuse`), which `test_counter_steps.py` reads as guarded.
3. **W16: removed** (c29196b9). The resolver receives `DNS_UDP_MAX` (512 B); a cut reply parses as no usable answer.
   `test_a_reply_longer_than_512_bytes_warns_and_tries_the_next_server` went first; the parse tests green.
4. **Captive DNS re-raise: removed** (c29196b9). A heap failure while parsing drops the query like a malformed one; the
   C-stack record stays. `test_a_heap_failure_while_parsing_the_query_drops_it_as_malformed` (nothing persisted, no
   pause) red (b5_cd_red), green (b5_c1b). The old test's second case, a heap failure at `run()`'s subnet check, is
   its own test now (`test_a_heap_failure_at_the_subnet_check_is_persisted`, green before and after: that path keeps
   its E UNEXPECTED slot).
5. **NTP 44-47-byte refusal and NTP-10's E20 arm: removed** (25a14b4f). The parse catch is the pre-audit
   `(IndexError, OverflowError, ValueError, OSError)` with E69, so a 44-47-byte reply parses; the zero timestamp stays.
   `test_parse_ntp_reply_zero_length_and_exact_boundary_lengths` (44 and 47 B set the clock) and
   `test_a_short_reply_fails_each_attempt_as_malformed` changed first, red (b5_ntp_red2), green (b5_ntp_g2);
   `test_an_allocation_failure_while_parsing_returns_none` went. The twin's NTP responder cuts its short mode at byte
   40 (before the Transmit Timestamp) so its malformed reply stays malformed. The removed test's vocabulary allow-list line went
   (ce9b6be5).
6. **NTP cadence chain: removed** (25a14b4f). The refresh loop counts ticks again (`_ntp_sec_count +=
   _NTP_CHECK_INTERV`, `_unsynced_wait_s += _NTP_CHECK_INTERV`); staleness keeps reading `_sync_age`. The five
   dropped-tick and boundary tests went first; the stale and unsynced-wait tests stayed green.
   `test_ntp_time_hours_counter_missing_config_falls_back_to_12h_default_without_raising` read measured time; it now
   presets the counted ticks (12 h less two ticks), a mechanical premise change with its assertions unchanged.
   `tests_scripts/test_counter_steps.py` now lists the two restored tick counts (`_ntp_sec_count`, `_unsynced_wait_s`)
   as bounded: each resets to 0 when `due`, which the check cannot see through the flag (found by the first gate run,
   21e12c76).
7. **Resolver cause and passed-in logger: shrunk** (c29196b9). `resolve_ipv4(host, dns_servers=(), timeout_ms=...,
   tries=..., *, logger=None) -> str | None`; the logger reaches only `UDPSocket` and the query-build `MemoryError` line;
   the write is unchecked and `disconnect()` in the finally unchecked (resolver and NTP fetch). NTP logs one E67 on
   `None`. Catalog E73, E74 go; W12 stays for captive DNS. Pinning tests went first (DNS :664, :747, :782, :794; NTP
   :1323, :1439); the return-shape and `logger=` tests red (b5_dns_red: 13 failed; b5_ntp7_red: NTP 10, the Wi-Fi/DNS
   integration 7, the FRAM integration 1), green (b5_udp1, b5_c1b, b5_ntp_g2). `test_readiness_gates.py`'s answer-bool
   rule was read first: it binds a teardown's own answer (`UDPSocket.disconnect()` still answers bool), not whether a
   caller reads it, so the unchecked calls are outside it.
8. **Stored NTPHost/DNSFallback re-check, DNS-1, CD-2, `DNS_NAME_MAX`: removed** (c29196b9). The PUT refusal is the
   one check; the resolver keeps the 63-octet label check; captive DNS parses as before. The six named tests went
   first; the PUT refusal and 63-octet tests green.
9. **NTP timer re-arm: removed** (25a14b4f). The pre-audit starters (a try around `init()` that logs the refusal);
   `start_sync_age_timer()` keeps `arm_tick_timer()`'s line; the retry timer's catch stays. The four re-arm tests went
   first; the four `degrades_gracefully` starter tests green. Found by the first gate run (21e12c76):
   `tests/test_digital_twin_timer_pool.py`'s pool test also pinned NTP's re-arm; its NTP part went (SYSTEM's degrade
   and WiFi's re-arm stay), red in b5_gate on all six devices, green in b5_fix2 (dev, wozi).
10. **W49/W50 split: removed** (ce199ebb). One code, W49, for both timeouts; `_bounded()` is one line; W49's text adds
    ", or the request exceeded outer_cap_s"; catalog W50 goes. `test_an_outer_cap_timeout_logs_the_call_timeout_code`
    and `test_a_read_timeout_then_a_capped_400_write_logs_the_call_timeout_code_twice` changed first, red (b5_ws_red),
    green; `test_a_timed_out_proxy_call_sets_the_shared_timed_out_flag` went (it pinned `timed_out`); :2732, :2753 green.
11. **Traces before a close: kept as landed** (owner-approved, named per (c)). Their tests green in every run.
12. **Static file hold: removed** (ce199ebb). `serve(filename)` opens the stream and Microdot closes it after the body;
    a HEAD or cut response's file closes at the next collection. Part B's "opened static stream held" row goes.
    `test_a_head_request_closes_the_opened_static_stream` and `test_a_failed_or_timed_out_static_body_write_closes_the_stream`
    went first. The static tests lost their `sock` holder fixture (mechanical); they read red against the committed
    source (its `hold()` call) and green after.
13. **Body heap failure: removed** (ce199ebb). `_body_as_dict()` answers the ERR envelope again; the C-stack record
    stays. `test_a_body_parse_that_runs_out_of_heap_answers_invalid_json` (200, code 1, "Invalid JSON request", no
    settings write, nothing persisted) red (b5_ws_red), green; :4399 green.
14. **Flat GET's unavailable marker: kept.** Its test green.
15. **UDP deadline precision: removed** (c29196b9). `ready()` is the pre-audit loop (poll, deadline check, sleep; at
    most one poll late) with the 100 ms idle rate and `_nomem()`. `test_ready_with_a_deadline_off_the_poll_rate_ends_at_the_deadline`
    went first; :597, :606, :614 green. `tests/test_ticks_rollover.py`'s no-datagram case now ends at the first poll
    past its bound: (False, 7) for (False, 6).
16. **Cleanups** (ce199ebb). `WebserverService.setup() -> None` (its asserts converted; `tests/test_readiness_gates.py`'s
    one found by the first gate run, 21e12c76); `_cfg_values()` returns
    `next(iter(values.values()))`, no unreachable `return {}`; `_Closable` folds into `_ClosableStream`. The rest of the
    row: nothing to change, as listed.
17. **Kept**: as listed; existing tests green.
18. **Other hunks.** First-scan rows: CD-4 restored (one warning for a `(None, None)` receive, bound or not; E10's arm
    and `_ERR_INIT` go; see Decisions for its text); CD-5 **kept, named below**; UDP-5 restored (a failed connect tears
    down after its backoff; the UDP test's invariant now disconnects first); NTP-7 restored (`recvfrom(1024)`, the
    request built per fetch; `_NTP_PACKET_LEN`/`_NTP_REQUEST` go); WS-15 restored (the raise handling only: `gather()`
    without `return_exceptions`, a raise reaches the catch-all's 500; the concurrent resets, the refusals and "Failed"
    for a false answer stay); WS-19 restored (the writer's non-finite-to-null branch and `import math` go; sources gate
    their own floats, F.1); WS-20 restored (pieces are str, encoded once in `_pieces_response()`); WS-22 **kept, named
    below**. Tests: `test_run_failed_receive_logs_one_warning_per_code` and the bind test (CD-4; the twin's
    `test_the_captive_dns_socket_whose_bind_fails_logs_once_then_rebuilds_binds_and_answers` found by the first gate
    run, now one W42, 21e12c76), the two WS-15 tests
    (500 through the catch-all) red (b5_cd_red, b5_ws_red), green; WS-19's `test_h2_a_non_finite_float_is_written_as_null`
    and the scenario `no_get_route_serialises_a_non_finite_float` went (it injects NaN/inf past every source gate; the
    PUT path refuses NaN/±inf and MicroPython's `json.loads()` gives no NaN, `1e400` reads inf and is range-refused);
    WS-20's `test_h2_piece_writer_counts_bytes_not_characters` went and the serving-demand scenario compares the body
    with the encoded pieces instead of their identity (renamed `..._and_sends_its_pieces`). The scenario's removal came
    after the source change: its red reading is b5_st2 (it failed on dev and wozi), green at b5_st3. Beyond these rows
    and items 1-17 I made no separate hunk-by-hunk pass of the six files; a hunk the review script marks outside them is
    unjudged by me.
19. **NTP unsynced retry: 60 s** (25a14b4f). `_NTP_RETRY_UNSYNCED_S = const(60)` with its `@tunable
    ntp.retry_unsynced_s = 60` row; until an attempt fails every check tries (the first at the first check with the
    network up); a failed unsynced attempt waits 60 s; a skipped one (no network) leaves the wait alone; a sync or a
    forced resync resets it and the forced one tries at once. The doubling, its 600 s cap, `ntp_retry_s`/
    `ntp_retry_max_s`, `_check_ntp_backoff()`, `ntp_backoff()` (with `_SMALL_INT_MAX`) and the generator's pair go;
    `NtpTiming` has three fields. Tests: `test_asy_ntp_time_failed_unsynced_attempts_wait_the_unsynced_retry_interval`
    (a second failed attempt waits 60 s) red (b5_ntp_red2), green; `test_ntp_timing_carries_the_dns_bounds_and_the_fetch_timeout`
    and `test_the_ntp_retry_keys_are_no_device_setting` (both keys refused as unknown) red (b5_ntp_red2: 3 failed),
    green; `test_an_unsynced_client_tries_at_every_check_until_an_attempt_fails_then_every_minute` green on both. The
    backoff tests (defaults, clamp, the validator's seven) went. Docs: C.7.2's NTP bullet and Part N (the row added;
    backoff_mult, retry_s_default, retry_max_s_default and the [device] rows removed). The twin suite's Run 9 waits for
    2 failures (about 4 s and 64 s into its 90 s watch) where the doubling gave 3; the bench helpers read the constant.

## Knowledge lines (removed items)

All removed code is at 3129bf21.
- Web start retries/W62: three `start_server()` tries 5 s apart before the task ended; the supervisor's restart
  retries the same way and `SO_REUSEADDR` rebinds at once.
- Head refusals (WS-2), `readexactly()`'s EOF refusal, `traced`/`_read_traced`/the print skip: refusals of request
  shapes Microdot already answers itself, and a flag that saved one console line per timeout.
- W16 and the 513-byte receive: a truncation warning for a reply no server sends (no EDNS in the query).
- Captive DNS `except MemoryError: raise`: persisted a parse-time heap failure the pre-audit code dropped as malformed.
- NTP 44-47-byte refusal and E20 arm: refused replies whose read bytes (0, 1, 40-43) are all present.
- NTP cadence (`_tick_gap`, `_cadence`, `_nearest_tick_s()`): counted measured time so a dropped tick did not delay a
  resync; the owner: "the 10s don't matter at all relative to the interval".
- Resolver `(address, cause)`, NXDOMAIN/not-sent codes, E73/E74, the write check, the tries guard, W12 at resolver and
  NTP: diagnostics beyond need; the lookup answers an address or None.
- Stored NTPHost/DNSFallback re-check, DNS-1, CD-2, `DNS_NAME_MAX`: second checks behind the PUT refusal, and captive
  DNS refusals of names the reply only echoes.
- NTP timer re-arm (`_check_armed`, `_tick_armed`, `_rearm_failed_timers()`): re-armed a refused timer whose trigger,
  alarm-pool exhaustion, is refuted.
- W50: a second code for the outer-cap timeout; W49 names both.
- Static hold (`hold()`/`release()`/`_held`): closed a HEAD or cut response's file at the connection's end rather than
  at the next collection.
- `_body_as_dict()`'s re-raise: made a body-decode heap failure a 500 the pre-audit code answered "Invalid JSON".
- UDP `_poll()`: ended a wait exactly at its deadline instead of at most one poll late.
- `setup() -> bool`, `_cfg_values()`'s `return {}`: test-only product code and an unreachable path.
- NTP backoff (doubling to 600 s, `ntp_retry_s`/`ntp_retry_max_s`, `_check_ntp_backoff()`, `ntp_backoff()`): replaced
  by one 60 s wait (owner, 2026-11-03: "Then let's actually take 1 minute").
- CD-4's E10 INIT arm: told a never-bound socket from a failed receive; both log the one warning again.
- WS-19's non-finite-to-null branch: a second gate behind every source's own.
- WS-20's byte-counting writer: encoded each fragment as it was written; the str pieces are garbage once the response
  is built, so it saved only a transient peak.
- WS-15's per-reset catch: persisted E14 for each raising reset and answered Failed.

## Proof check (PLAN 0) on the remove items

No remove item had proof that it is good: every row's "proof sought" was none or refuted, and none of the tests read
first reproduced a real failure (the non-finite scenario's values bypass every source gate; the PUT path refuses
them). Nothing became a shrink item beyond item 7, which the list names as one.

## Gate

`S/u35r/r1/B5/tools/gate.sh`: lint and the three mypy passes, `scripts/test.sh` at -1 and at 32768, dev's twin
suite and harness at both stages, `tests_hardware --collect-only`, `npm run lint`, `npm run typecheck`, `npm run
test:unit`.

**First run (b5_gate, on ce199ebb): stopped by me (pids) after its unit tier at -1 failed**; the 32768 stage had
just begun. All failures except the last two below were (b) defects in my deliverable, all fixed in ce9b6be5/21e12c76:
`test_fatal_report_sites.py` (the rebound printer without `report_if_fatal()`, item 2); `test_counter_steps.py`
(NTP's two restored tick counts, the head-line count's new form); `test_decision_vocabulary.py`'s stale allow-list
line (item 5); the twin timer-pool test on all six devices (NTP's re-arm, item 9); the twin captive DNS bind test on
dev, arzi and grkizi (CD-4); `tests/test_readiness_gates.py`'s setup assert (item 16). Two scenario failures were
(c), host load: dev's `loop_lag_under_combined_load` (settled p99 58 ms against 50 ms) and arzi's
`failed_config_snapshot_is_sent_as_unavailable` (1 GET marker, 0 verifies of 2 faults). Root cause, from the run's
own logs: every window of the dev run lagged about ten times its uncontended figure (the boot window, which carries
no scenario load, 341 ms; under load 389 ms; settled maximum 418 ms), while the twin ran beside the tier's parallel
twins and its 19-minute pytest tier on a 4-core host; in the arzi run the twin log shows `SCD30 Error in initial
setup: [Errno 5] EIO` after `FAULTS_ARMED`, i.e. the reader task's setup ran after the arm and took one of the two
faults, the scenario taking 8.4 s against 4.0 s alone. Alone (b5_lag1, two runs each, on the 21e12c76 tree just before its commit): dev's settled p99
5 ms both times (max 6.7 and 5.2 ms), arzi's scenario passed both times; and both passed inside gate2 at both stages.
Neither involves a B5 change: the lag is wall-clock starvation of the Unix port, and the SCD30 setup is B4's file.

**Second run (b5_gate2, on 21e12c76; 88 min): every step passes except the base-known vocabulary test.** Lint and the
three mypy passes clean. `scripts/test.sh` at -1 and at 32768: files 137 passed, 1 failed (the `tests_scripts` tier),
86 skipped by their own device/premise rules, 6 deselected; MicroPython tests 5,990 passed, 0 failed, at each stage;
`tests_scripts` 7,111 passed, 1 failed, 6 skipped. The one failure is
`test_decision_vocabulary.py::test_decision_vocabulary_names_its_actor_or_is_allow_listed` on exactly the six base
sentences the lead named (SPECIFICATION.md :1201 and :7878, `src/asy_system_service.py:378`,
`tests/test_asy_system_service.py:1393, 2103, 3727`), base-known and fixed on the integration branch in 942ca477; no
sentence of mine is flagged (b5_vocab2, b5_fix2). Dev's twin suite: 332 checks passed, 0 failed (16 more in its
second block, passed) at -1 and at 32768; dev's twin harness: 65 scenarios passed, 0 failed, 2 skipped by premise
(the 0444 config probe under root; the full-queue reset scenario, run on arzi only) at both stages; its loop-lag
scenario settled at p99 6 ms. `tests_hardware --collect-only`: 202/233 collected (31 deselected by the default
gates). `npm run lint`, `npm run typecheck` PASS; `npm run test:unit` 1,340 passed in 26 files.

## Sizes

`module_sizes.sh` (`S/u35r/r1/B5/sizes/`): `src/` 205,681 B at 3129bf21 to **202,643 B at 21e12c76 (-3,038 B)**,
16,400 to 16,181 lines; against R0's 208,708 B, -6,065 B. Per module: NTP client 8,935 to 7,644 (-1,291), web
server 15,306 to 14,360 (-946), DNS client 2,096 to 1,670 (-426), captive DNS 2,809 to 2,498 (-311), UDP socket
2,015 to 1,951 (-64). No module grows.

`scripts/build_firmware.py dev` at 21e12c76 (b5_fw, after the shared toolchain lock freed): image 1,178,908 B of
1,228,800 B, **imageFreeBytes 49,892 B** (R0: 43,068 B, +6,824 B; B2's 46,468 B at 8019a9ef, +3,424 B).

## Decisions (agent, 2026-11-03)

- CD-4 keeps W42's text "Receiving a DNS request failed." rather than the pre-audit "Invalid DNS request data or
  address": the arm only ever sees a local failure (`(None, None)` is never a client's datagram), so the old text
  names the wrong side; the restore is the one-warning shape.
- Item 4's old test is split so the subnet check's persisted heap failure stays pinned.
- Item 5: the twin responder's short mode cuts at byte 40, keeping the twin's malformed-reply scenarios on a reply
  that is still malformed.
- Item 6: the 12 h test presets the counted ticks (mechanical; it read measured time).
- Item 19: Run 9's failure bound is 2 (`l2.ntp_unreachable_failures`), from the retry's schedule inside the watch.
- WS-20: the serving-demand scenario keeps its demand formula (the largest body held once as its encoded pieces) and
  drops its no-copy identity; renamed to say only what it checks.
- One commit per area (resolver/DNS/UDP; NTP; web server): the items' hunks interleave inside each.

## Findings

- **CD-5 kept (named, basis):** restoring the pre-audit `except CancelledError: break` made
  `tests_scripts/test_task_tops.py` fail (`run()` must end in a top or a cleanup-only try); the task-top rule is a later
  standing rule, so the cancellation keeps propagating after the cleanup. Lead to decide whether the rule or the
  restore gives way.
- **WS-22 kept (named, basis):** the `counted` flag exists because the kept per-drop trace at the ceiling (W48) and the
  connection task's top (task-top rule) sit inside the try whose finally releases the count; the pre-audit order
  (increment outside the try) holds only without them.
- **WS-15:** without `return_exceptions`, the first raising reset ends the `gather()` and the other resets keep
  running unawaited while the 500 is sent (MicroPython's gather). A raise there is a defect's path only; noted, not
  changed.
- **NTP-7:** `recvfrom(1024)` allocates 1 KB per sync attempt (`extmod/modlwip.c`'s recvfrom allocates `len` before
  reading), against 48 B before; the scan judged it implausible as a failure.
- **WS-20:** encoding at the response briefly holds a body twice (str pieces and their bytes) per connection; the
  serving-demand formula counts it once. dev's margin is about 3.4 KB against an estimated budget.
- **Bench NTP timing:** `tests_hardware/bench/_load.py`'s `ntp_retry_period_s()` and the two block tests' waits now
  derive from 60 s; checked by `--collect-only` only, so their real timing is untested (hardware round).
- The 12 h test was changed mechanically (above); its subject (the 12 h default) is unchanged.
- **(c) Two host-load-sensitive scenarios** failed once in the first gate run (Gate, with root cause): dev's
  `loop_lag_under_combined_load` measures wall-clock lag, which a contended 4-core host inflates in every window;
  arzi's `failed_config_snapshot_is_sent_as_unavailable` assumes the SCD30 reader's setup read is done before
  `FAULT_ARM`, which a slow host breaks (the setup took an armed fault). Neither is pursued here.
- **Item 2's rule check:** `tests_scripts/test_fatal_report_sites.py` had pinned the rebound printer's
  `report_if_fatal()` as a separate rule; the action list's decision (the logger's entry records the overflow) made it
  accept a logging hook. Named so the lead sees a standing rule check was relaxed, with its new failing case.
- **Item 18's hunk pass** stopped at the named rows (see item 18).

## Fix round

Written by the agent (Tue Nov  3 11:44 UTC 2026), from `FIX_BRIEF.md`. One commit for all six: **60a88be1** on
`audit/r1-b5` (SPECIFICATION.md carries hunks of four fixes, so one commit). Nothing pushed. Runs: `S/u35/lead/b5x_*.log`;
the picker that runs single test functions at either stage is `S/u35r/r1/B5/fix/pick.sh` (env-driven `pick.py`).

- **F1 WS-20 restored (bytes pieces).** `_PieceWriter` encodes each fragment once and counts its pieces in bytes;
  pieces are `list[bytes]` (`_build_status_pieces()`, `_stream_dict_response()`); `_pieces_response()` sends them
  with no re-encode. Tests back to `3129bf21`'s form first: the serving-demand scenario's identity check
  (`all(sent[i] is pieces[i] ...)`, named `..._sends_its_pieces_uncopied` again),
  `test_h2_piece_writer_counts_bytes_not_characters`, the multibyte-SSID test bounding bytes (the 602 B SSID the
  one piece past the cap), the writer tests and `_written()` on bytes. The non-finite-float test stays removed (WS-19).
  Red on the str writer (b5x_f1_red: 0/9, the scenario failing at `/measurements` on dev and wozi); green at both
  stages (b5x_f1_green, 9/9 each). SPECIFICATION.md G.2 (the `_PieceWriter` bullet), I.3 and the serving-demand
  paragraph say bytes and the one-copy identity again; the bullet keeps WS-19's "Producers gate their own float
  values (F.1)". **The falsifier's planted copying `_pieces_response()`** (`B5/probe/probe_b5f.py h`) now fails the
  restored scenario: b5x_probe5 "COPYING scenario failed: /measurements" (b5f_probe5 at `21e12c76`: "passed").
  Sizes: `asy_webserver_service` 14,360 -> 14,335 B (the per-response encode is gone).
- **F2 a check tick during an NTP attempt starts none.** Test first, in `tests/test_asy_ntp_client.py`:
  `test_a_check_tick_during_a_failing_attempt_starts_no_other_before_the_retry_wait`. The real `_sync_loop()` and
  `_refresh_loop()` run, the boot's forced attempt is held, one check tick lands, then the attempt fails. Then
  5 more ticks: attempts expected `[1, 1, 1, 1, 1, 2]`. Red at `21e12c76`: `[2, 2, 2, 2, 2, 2]` (b5x_f2_red2), the second
  attempt right after the first. And `test_a_forced_resync_during_an_attempt_tries_again_once_it_ends`: `[2]`.
  It was green at `21e12c76` (b5x_f2_red), so it is a kept behaviour. A planted break turned it red: the naive fix, clearing
  the trigger after a failed unsynced attempt (b5x_f2_plant: `[1]`; that break also fails the tick test, `[1]*6`).
  Fix (`src/asy_ntp_client.py`, +41 B, an admitted fix): `_attempting`, set around the attempt in `_sync_loop()` and
  cleared at its start (a restart after a raise mid-attempt starts clear), read only by the unsynced due check.
  The tick during the attempt still counts, so the next attempt comes 60 s of check ticks after the failed one's
  trigger. Both green at both stages (b5x_f2_green, with the five existing retry/backoff/force tests, 7/7 each).
  Re-read against the fixed schedule: `l2.ntp_unreachable_failures` (2; second failure at ~64 s, "a third is unreachable
  inside it") now holds whatever the tick phase: before the fix a tick during the boot attempt made a third reachable.
  `l2.ntp_unreachable_watch_s` (90 s), and Run 9's `>= 2` check with the suite's comment (4 and 64 s, the next ~124 s),
  hold unchanged. C.7.2's NTP bullet now says the wait counts from the attempt's trigger, and that a tick during an
  attempt counts but starts none (agent, 2026-11-03). It adds that a forced resync during an attempt tries as soon as
  the attempt ends.
- **F3** SPECIFICATION.md L.5: `device.ntp-retry-below-tick`, `device.ntp-retry-max-below-retry`,
  `device.ntp-retry-max-range` dropped from the rule-id list (no buildgen site raises them). Doc only.
- **F4** `digital_twin/README.md` Run 9: ends on the second NTP failure; the unsynced retry (one attempt every 60 s
  after a failed one) puts the failures at about 4 and 64 s of serving and the third at about 124 s, past the bound.
- **F5** `digital_twin/unixport/_ntp_responder.py:20`: `_VERSION` cites `src/asy_ntp_client.py _fetch_ntp_reply()`'s
  first byte, 0x1b. The same stale `_NTP_REQUEST` citation in `tests/test_digital_twin_ntp.py:77` now names
  `_fetch_ntp_reply()` too (same fault, one comment).
- **F6** SPECIFICATION.md C.8, the NTP attempt's lock-hold row: a failed socket setup costs a 0.5 s backoff
  (`_RETRY_BACKOFF_MS`). A DNS server can cost two, because the resolver ignores its write's answer and the receive
  sets the socket up again. That is at most 0.5 s + 0.52 s per server (the write's setup fails, the receive's
  succeeds and waits out 500 ms + one 20 ms step), or 1.0 s if both fail. The fetch checks its write and stops after
  one. Total: <= 4 x 1.02 s + 5.02 s = 9.1 s, unchanged, so C.8's "<= 9.1 s" and `hold.wifi_lock` stand.

**Files run at both stages** (b5x_batch1, after a rebuild; every one passed, zero `MemoryError`/"memory allocation
failed" lines): `test_asy_ntp_client.py` 183/183, `test_asy_webserver_service.py` 223/223,
`test_asy_webserver_connections.py` 25/25, `test_ntp_wifi_dns_integration.py` 13/13,
`test_ntp_fram_system_integration.py` 12/12, `test_digital_twin_ntp.py` 17/17, `test_digital_twin_clock_jump.py` 6/6,
`test_digital_twin_http_client.py` 38/38, `test_setter_microdot_integration.py` 34/34,
`test_notification_neopixel_integration.py` 6/6, `test_digital_twin_sensortask_integration.py` dev 18/19 and wozi 11/19
(the rest skipped by their own device/premise rules), `test_digital_twin_timer_pool.py` dev 5/5,
`test_digital_twin_loop_end.py` dev 8/8, `test_sensortask.py` 103/103 on each of the six devices.

**Lint and typechecks** (on the final tree before the commit): `lint_direct.sh` clean (b5x_lint: ruff, shellcheck,
actionlint, zizmor, the method-assign guard, gc sites); mypy main 276, host 314, twin 59 files, no issues (b5x_mypy;
the typings link removed). Rule checks reading the touched files (b5x_pyt, 10 `tests_scripts` files): 806 passed, 1
failed. The failure is `test_decision_vocabulary.py` on exactly the six base-known sentences named in the Gate section
above (fixed on the integration branch in 942ca477), none of mine. (c).

**Sizes** (`sizes/fix.tsv` against `sizes/head.tsv`): `src/` 202,643 -> 202,659 B (+16): `asy_ntp_client` 7,644 ->
7,685 (+41, F2's admitted fix), `asy_webserver_service` 14,360 -> 14,335 (-25). Firmware image not rebuilt.

**Superseded above:** the item 18 WS-20 restore, its knowledge line and the WS-20 decision (the scenario dropping its
no-copy identity) no longer hold. WS-20 is back as at `3129bf21`.

**Decisions (agent, 2026-11-03):** F2's form is the in-flight flag. Other forms were rejected:
- Setting the 60 s wait at an attempt's start. It changes what `_retry_wait_s` reads during and after an attempt,
  which three stub tests and the twin clock-jump test read as "the attempt failed".
- Clearing the trigger after a failed attempt. It drops a forced resync made during the attempt (b5x_f2_plant).
- Keying on `wifi_mode_lock.locked()`. It would also defer a tick on Wi-Fi's own holds.

The tick during the attempt counts toward the wait, so attempts stay one per 60 s of ticks. The synced 12 h due
check is not guarded (unchanged); a stale transition during an attempt is now covered, since it goes through the
unsynced check.
