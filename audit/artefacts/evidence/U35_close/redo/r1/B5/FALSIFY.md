B5 falsification, written by the agent (Tue Nov  3 10:59:49 UTC 2026)

Target: `21e12c76` in `S/wt-b5f` (base `3129bf21`, pre-audit `25caf528`), read with `git show`/`git diff`, plus the vendored
`ext/microdot.py`, `ext/freezefs/` and the pinned MicroPython/lwIP source under `S/tc-int/micropython` (v1.29.0). Runs (8 of
10, all through `run.sh`, logs in `S/u35/lead/`): `b5f_rebuild`, `b5f_probe1` (import-path slip, no result),
`b5f_probe2`-`b5f_probe5`, `b5f_sizes`, `b5f_fw`. The probe is `S/u35r/r1/B5/probe/probe_b5f.py` (Unix port, `build-standard`,
16M heap, run from the worktree root). No file in the worktree was changed (the one planted break, a copying
`_pieces_response()`, was planted in-process by the probe); `git status` is empty after the runs.

Verdicts: 1 STANDS, 2 STANDS, 3 STANDS, 4 STANDS, 5 REFUTED (narrow), 6 REFUTED, 7 STANDS, 8 STANDS, 9 STANDS,
10 STANDS, 11 REFUTED (narrow, pre-existing), 12 STANDS, 13 STANDS, 14 REFUTED, 15 STANDS.

## Per claim

1. STANDS. `_serve_loop()` (src/asy_webserver_service.py:884-889) calls `asyncio.start_server()` once and lets a raise
   end the task; the test `test_a_failed_start_ends_the_serve_task_for_the_supervisor` pins it. Rebind: `start_server()`
   sets `SO_REUSEADDR` before `bind()` (extmod/asyncio/stream.py), rp2 builds lwIP with `SO_REUSE 1`
   (extmod/lwip-include/lwipopts_common.h:75), and `tcp_bind()` skips the in-use check when both pcbs carry REUSEADDR
   (lib/lwip/src/core/tcp.c:719-734); `tcp_listen()` refuses only a port another LISTEN pcb holds (:867-879), which a failed
   start does not leave. Twin check, `b5f_probe3`: with a bound, never-listening REUSEADDR socket holding the port (what a
   failed `listen()` leaves), a new `start_server()` on it succeeded at once. W62: no emitter, catalog row, test, JS or
   tests_hardware reference (git grep over the tree, `:!arduino`); E62 (WLAN_STA_START) is the only "62" left. Edge outside
   "a failed start": see Outside, item 7.
2. STANDS. Refusals in the proxy: `readline()` past `max_readline` and `_check_head_line()` (byte cap, line count,
   Content-Length not `isdigit()` or repeated), src/asy_webserver_service.py:330-347, 391-406; nothing else calls `_refuse()`.
   `b5f_probe3` fed 16 heads through the real `_serve()` at DebugLevel 0 with the real rebound `print_exception` (the
   committed test replaces it with a recorder): two-token request line, version without "/", header without ":", non-UTF-8
   header, chunked PUT, body cut short (50 announced, 20 sent, EOF), `/%zz`, `?a=%zz`, `Cookie: novalue`, four-token request
   line, non-UTF-8 request line, empty request, empty header name, a 23-digit Content-Length, a non-UTF-8 JSON body, a
   bare `charset`. Answers 400/400/400/400/200(code 1)/400/404/400/200/400/400/400/200/413/200/200; every connection ended
   with ErrCount 0, no drop, 0 open slots; console lines at level 0: none; history used: none.
3. STANDS. `b5f_probe3`: 20 host strings (empty, ".", "..", "a..b", 200 empty-ended labels, 63/64-octet labels, 32 two-byte
   characters, IPv4 literals with and without leading zeros, 300 octets, NUL, space, "-", non-ASCII, emoji, a 320-octet
   name of 63-octet labels, "1.2.3.4.") against (), ("127.0.0.1",) and a list of junk servers ("", "1.2.3", "a.b.c.d",
   "256.1.1.1", Arabic-Indic digits, " 1.2.3.4") ending in 127.0.0.1: no raise, 30 queries sent, longest label 63, the only
   answers the two IPv4 literals returned as given. Receive size is `recvfrom(DNS_UDP_MAX)` = 512
   (src/asy_dns_client.py:30, 144). Note: "01.2.3.4" comes back unchanged (a dotted quad, not canonical).
4. STANDS. `DNSQuery.__init__` catches `Exception` (src/asy_captive_dns.py:172-177), so a `MemoryError` empties the domain
   and `response()` returns None, the loop goes on; `(None, None)` from `recvfrom()` logs W42 then backs off
   (:113-118), for a failed bind (`_connect()` swallows it, asy_udp_socket.py:68-75) as for a failed receive.
5. REFUTED (narrow). 44-47 B replies do set the clock as `25caf528` does (`b5f_probe5`: 44, 45, 47 and 48 B all return
   2026-01-01; the parser reads bytes 0, 1, 40-43). But the LI/stratum check runs first (src/asy_ntp_client.py:272, before
   the unpack at 277 and the zero check at 278), so a short or zero-timestamp reply whose LI is 3 or stratum is 0 logs W40,
   not E69. `b5f_probe2`: "40 B, stratum 0" -> W40; "43 B, LI 3" -> W40; "48 B zero transmit, stratum 0" -> W40 (while
   "43 B, stratum 2" and "48 B zero transmit, stratum 2" -> E69). Both still set nothing; only the logged code differs
   (as at `25caf528`; `3129bf21` checked the length first). The MemoryError half holds: the except is
   `(IndexError, OverflowError, ValueError, OSError)` (:292) and `_sync_loop()` has no handler (:393-404).
6. REFUTED, twice.
   (a) "after each failed attempt, the next one 60 s later, every time" fails when a check tick lands while an attempt runs
   with the wait still at 10 s (after boot, a sync or a forced resync: `_reset_backoff()`, :333-335, 502): `_refresh_loop()`
   adds 10, finds 10 >= 10 and sets the trigger (:321-327) before `_sync_loop()` sets 60 (:404), and the ThreadSafeFlag
   wakes the next `wait()` (:396) at once. `b5f_probe2` (real `_sync_loop()`/`_refresh_loop()`, attempt gated, one tick
   during it, no tick after): `attempts 2 retry_wait_seen [10, 60]` - the second attempt ran right after the first failed.
   The boot attempt (main()'s `ntp_force_sync()`, generated sensortask_dev.py:261) meets this whenever its 5 s fetch spans a
   tick; so SPECIFICATION.md's `l2.ntp_unreachable_failures` row (:12493, "a third is unreachable inside it") is not
   guaranteed (Run 9's `>= 2` check still passes).
   (b) SPECIFICATION.md:11188-11189 still lists the three removed rule ids of the doubling backoff's build check,
   `device.ntp-retry-below-tick`, `device.ntp-retry-max-below-retry`, `device.ntp-retry-max-range` (no buildgen site raises
   them; they were validate.py:842-859 at `3129bf21`). No device setting, validator field or generated value remains
   (devices/, buildgen/, the generated NtpTiming carries three fields).
   Lesser, pre-existing: the synced cadence counts check ticks again (:316), so each dropped or coalesced tick delays the
   resync 10 s; and a forced resync that succeeds before the next tick leaves `_ntp_sec_count` as it was, so the next due
   resync keeps the old cadence rather than coming one interval after the forced sync.
7. STANDS. `start_check_timer()` (:424-433) and `arm_tick_timer()` (asy_base_classes.py:390-401) print the refusal and
   return; nothing else reads their outcome; the twin test `test_the_tick_timers_degrade_in_place_and_rearm_once_the_pool_frees`
   pins it. Note: the print is level-gated and not persisted, so at DebugLevel 0 a refused NTP check timer leaves no trace,
   and NTP then never resyncs or goes stale for that boot (as at `25caf528`).
8. STANDS. Both timeout arms log `_WRN_HTTP_CALL_TIMEOUT` (src/asy_webserver_service.py:321, 860); catalog row 49 says
   both. No `const(50)`/`const(16)` warning or `const(73)`/`const(74)` error, no `HTTP_REQUEST_CAP`, `DNS_REPLY_TRUNCATED`,
   `NTP_DNS_NOT_SENT`, `NTP_DNS_NXDOMAIN` anywhere outside `audit/` (E50 FRAM_VERIFY and W73 SCD_NOT_READY are other rows).
9. STANDS. A GET closes the file through Microdot's body iterator (`aclose()`, ext/microdot.py:697-698, 753-757); a HEAD
   or an unmuted write error skips it. The site is mounted by freezefs without `--compress`
   (scripts/build_frozen_html.sh:76), so `VfsFrozen.open()` returns a plain `BytesIO` (ext/freezefs/ffsmount.py:87-89):
   no descriptor exists to exhaust; an unclosed one is ordinary garbage.
10. STANDS. `_body_as_dict()` catches `Exception` (src/asy_webserver_service.py:184-192) and every PUT handler answers
    `make_response(1)` on None; `test_a_body_parse_that_runs_out_of_heap_answers_invalid_json` pins it.
11. REFUTED (narrow, pre-existing). The poll loop ends within one round of its deadline (`b5f_probe4`: a bound socket,
    50 ms deadline, False after 61 ms), the lock is released by `async with` on every cancel, and all three product users
    disconnect in a `finally` (asy_dns_client.py:147-148, asy_ntp_client.py:228-229, asy_captive_dns.py:124-138). But
    `ready()` awaits `_connect()` before taking `t0` (asy_udp_socket.py:115, 119), and a failed setup sleeps
    `_RETRY_BACKOFF_MS` whatever the deadline (:72): `b5f_probe4`, bind refused, 50 ms deadline -> False after 502 ms,
    about 22 poll rounds late. Same at `3129bf21`; no shipped caller passes a deadline under 500 ms (generated
    `_DNS_TIMEOUT_MS` 500, fetch 5000).
12. STANDS. `asyncio.gather()` without `return_exceptions` (:800): a False answer gives FAILED via `all()`, a raise
    propagates to Microdot's dispatch and the `errorhandler(Exception)` catch-all answers 500 (ext/microdot.py:1533-1566);
    MicroPython's gather leaves the other sub-tasks running (extmod/asyncio/funcs.py:65-125).
13. STANDS (searched, found no ungated source). Every float a GET route writes: SCD30 CO2/T/RH `isfinite` gate
    (asy_scd30_driver.py:876), WetBulb/DewPoint behind range windows (math_helpers.py), BMP3XX operating-range gate
    (asy_bmp3xx_driver.py:552) and `pressure_at_height()` windows, ISL29125 counts-based values, CCT/chromaticity windows,
    gain-ratio window (:550-553), SGP40 VOC a fixed-point int, config floats range-checked at PUT (`checked_float()`,
    asy_config_manager.py:165) and at load (`type_or_range_error()`, :543), SCD30 chip config from uint16 words.
14. REFUTED. Several test changes follow product changes that no claim 1-13 names, and some retire product checks:
    - Pieces became `str` (not in 1-13): the serving-demand scenario lost its identity assertion
      (`sent[i] is pieces[i]`, "so an encode-copy fails here"). Planted break, in-process (`b5f_probe5`): a
      `_pieces_response()` that copies every piece's data passes the committed scenario for dev while adding 16,896 B live
      at the encode of `/status` (demand 69,336 + 16,896 > the 72,232 budget). The shipped encode shares the str's data
      (MicroPython's str-to-bytes keeps the buffer): measured +1,280 B for `/status`'s 30 pieces (`b5f_probe2`), so the
      product itself stays inside the budget (about 70,622 B); the check, not the product, got weaker.
      `test_h2_piece_writer_counts_bytes_not_characters` went and the multibyte-SSID test now bounds pieces in
      characters, so a write piece may exceed `chunk_bytes` in bytes (SPECIFICATION.md I.3 now says characters).
    - Captive DNS parse refusals (not in claim 4): `test_a_query_declaring_two_questions_is_dropped`,
      `test_a_name_of_255_octets_is_answered_and_256_is_dropped` removed with the QR/QDCOUNT/label/name-length checks.
    - Socket teardown warnings (W12) of the resolver and the NTP fetch: `test_a_failed_socket_teardown_logs_one_warning_and_keeps_the_answer`,
      `test_a_failed_teardown_leaves_one_socket_teardown_warning` removed.
    - Stored NTPHost/DNSFallback re-check (W10): `test_a_stored_host_that_is_not_a_host_name_uses_its_default`,
      `test_a_stored_fallback_that_is_not_an_ipv4_list_uses_its_default` removed.
    - `test_every_fetch_sends_the_one_request_built_at_import` removed (request built per attempt again).
    Mechanical and fine: the UDP cancel invariant (follows 11), `test_fatal_report_sites.py` (a logger entry runs
    `report_if_fatal()` on its arguments first, asy_print_log.py:89-95, so "logs it" is as strong as "starts with it"),
    twin Run 9's bound 3 -> 2 (follows 6's schedule; see 6a for its phase dependence), the five dropped-tick tests
    (follow 6), the start-retry, W50, W16, E73/E74, static-close, non-finite and ResetErrors test changes.
15. STANDS. `b5f_sizes` (`module_sizes.sh` at both revisions): total 205,681 -> 202,643 B (-3,038); changed modules all
    shrank: asy_webserver_service 15,306 -> 14,360, asy_ntp_client 8,935 -> 7,644, asy_dns_client 2,096 -> 1,670,
    asy_captive_dns 2,809 -> 2,498, asy_udp_socket 2,015 -> 1,951. `b5f_fw` (`build_firmware.py dev`): "49892 B free",
    record `imageFreeBytes` 49892.

## Outside the claims

1. digital_twin/README.md:800-808 still describes Run 9 as ending on "the third NTP failure event" with "the 10 s doubling
   backoff" failing at 4, 22 and 62 s (doc drift; the claim 6 wording names only SPECIFICATION.md).
2. digital_twin/unixport/_ntp_responder.py:20 cites `src/asy_ntp_client.py _NTP_REQUEST`, which no longer exists.
3. The resolver ignores `write()`'s result again (asy_dns_client.py:143), so a failed socket setup costs two 500 ms
   backoffs per server per try (the write's and the receive's `_connect()`), not the "0.5 s per failed socket setup" of
   SPECIFICATION.md:4054; the row's 9.1 s total still holds for four servers (worst mix about 8 s).
4. A stored DNSFallback is no longer re-checked: a config file written outside the PUT path passes the 47-character schema
   bound with up to six addresses, against the three the attempt bound (SPECIFICATION.md:4054) assumes. Low (needs a
   hand-written file).
5. Teardown failures of the resolver's and the NTP fetch's sockets leave no trail now (only the captive DNS keeps W12);
   with MEMP_NUM_UDP_PCB 5 a leaked pcb would show only as later E72/E71. Low (`close()` rarely fails).
6. A `MemoryError` decoding a PUT body or parsing a captive-DNS query is caught and not logged (only `report_if_fatal()`),
   so the four memory gates, which read logs, cannot see it - as the claims intend, same as `25caf528`, noted only against
   CLAUDE.md's "caught-and-logged included" bar.
7. If MicroPython's `Server._serve()` dies on an exception after `accept()` (e.g. `create_task()` out of heap), it does
   not close its listening socket; the serving task then ends and every restart's `listen()` is refused (EADDRINUSE,
   tcp.c:867-879) until a collection finalises the old socket. Edge; the old start retry also covered only 10 s of it.
8. `resolve_ipv4()`'s module comment says it never raises; with the overflow guard gone a `tries` past a machine word
   raises out (OverflowError on rp2). Unreachable from product code (generated `_DNS_TRIES` 1).
