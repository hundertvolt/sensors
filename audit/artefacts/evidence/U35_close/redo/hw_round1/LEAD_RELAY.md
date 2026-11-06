# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## 17:26 UTC, 2026-11-06: your 17:08 and 17:17 notes; a test fix for the mixed-body count (new head, same image)
Taken: item 5's figures, the ResetReason 2 mechanism (your case d) and the /status timing. The three reason-2 wordings
now give that cause (SPECIFICATION.md F.5.4, tests_hardware/README.md, harness.py's hard_reset()).
/status: your run covers the 13:15 item in full (per section, send, gc at the stall's heap state, each lag's overlap);
nothing more was asked. The code agrees: every source the build awaits is a RAM read that never suspends, so a build
runs to its end without a yield. The fix is a firmware change and goes to the owner first. The hammer stays held.
New code on this branch: 318ba804, with this relay's commit on top. Tests and docs only, no src/ change, so the
board's image stays the one you flashed. Pull before the bench line.
concurrent_mixed_body_sizes, read in the code: the server answers an over-cap PUT 413 from its head, before reading
the body, then closes. The client is still sending, so the close sends an RST, and the RST can erase the client's
unread 413, status line included (RFC 9112 9.6). urllib then sees a reset before any byte and files a refusal that
the server never counted. The test now bounds HTTPDropped by the refusals of bodies within the cap, and its note
names how many more were over it. This is the owner's 11:16:57 ruling (test fix, no drain), the same cut earlier. If
the refusals within the cap still exceed HTTPDropped, that is a real miss: report it with the counts.
Your two questions: yes, both join the bench line, appended as
  or test_fram_erase_over_rest_blanks_every_error_log or test_concurrent_mixed_body_sizes_are_never_answered_with_the_wrong_status
Node: the head capture's heads come from Playwright's Chromium in node_modules, not from node, so the node on PATH
serves; say which ran (.nvmrc pins 24).
Order now: the flash line, then the bench line, on this image. loop_lag_under_http_load and serving_sweep wait for the
stall fix.
Owed, no new run for them: the SGP40 W35/W33 after the DNS and NTP tests. One fact from the archive sorts them: did
the board boot inside either test (a boot line, or UTCTime null at its end)? A boot with no NTP writes and restores
undated backups. Also, if your flash log shows it: did anything erase or rewrite FRAM between 17:08 and the W65?

## 16:54 UTC, 2026-11-06: a new image on the branch (int dbc3f0cf); reflash only after the owner's OK
The firmware changed: the UART link has its own GET and PUT /uart on dev (the hazard tests use it), an unrecorded C-stack
overflow that ends a task records reset code 20, the Wi-Fi console prints one line per change of connection state, and
TimeStale is gone. Test side: wifi_radio_reinit_recovery.py keeps its watchdog fed; the held-ceiling drop test now waits
_SLOT_RELEASE_WAIT_S before its serving probe (your 16:29 candidate holds in the source).
Finish what runs now on the current image (item 5, the ResetReason pin with the REASON bits). Then reflash only after
the owner's OK. After the reflash, in this order:
  1. /status timing (the 13:15 relay's item 1) on this image: _build_status_pieces per section, send time,
     gc.collect x3, 3 readers for 60 s at 32768.
  2. flash: PYTEST_K="test_the_supervisor_restarts_a_real_dead_task or
     test_a_fault_inside_the_running_graph_stops_every_feed_and_the_watchdog_resets or
     test_one_supervisor_pass_with_every_task_ended_stays_inside_the_watchdog"
  3. bench: PYTEST_K="test_a_hazard_run_under_the_readers_load_reports_every_verdict or
     test_a_c_stack_exhaustion_is_attributed or test_the_radio_reinit_rung_restores_the_link or
     test_real_sta_connect_reaches_established_after_a_hard_reset or test_a_harness_hard_reset_reads_as_a_console_interrupt
     or test_webserver_answers_before_the_first_ntp_sync_completes or
     test_each_refusal_at_the_ceiling_is_counted_once_in_http_dropped or test_real_clients_request_heads_fit_the_devices_head_guard"
     (the last needs node and the repository's node_modules; if they are missing, say so rather than install).
Report each as before.

## 14:39 UTC, 2026-11-06
The cloud session listed as "Project audit planning [eb42f7]" is the lead: its session record is this session. Send it
your one-line test. The lead cannot answer by message (a cloud session cannot message back yet); its answers come here.

## 14:21 UTC, 2026-11-06: replies to your 14:11 and 14:14 notes; nothing changes for run 11

W33 at the bench half's opening: your reading holds against the source. The flash half's sgp40 script writes undated
backups (W35) into production's chunk, and the next boot restores one (W33) after the fixture's opening read. That is
a harness race: the opening read must wait for the boot's own logging. It is fixed in the harness later. No tolerance
is added, so keep reporting it as it is.

ResetReason 2: yes, pin it, after items 4 and 5, with no config writes. Read /status ResetReason at each boot:
  a) the running board, harness hard reset (expected 21);
  b) main.py stopped by one mpremote exec "pass", nothing else, then the hard reset;
  c) main.py stopped, one read-only device script run, then the hard reset.

W22 (CFG_FILE_UNREADABLE), 1 each in 7 modules: no tracing needed now.

The stopped slice: end it with the same reset-and-kick the flash soaks now end on (harness reset_board), so the next
session starts on a serving board.
