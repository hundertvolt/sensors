# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## 19:04 UTC, 2026-11-06: the /status stall fix (new image); your noble note
New code on this branch: b28a9e2f, with this relay's commit on top. src/ changed: a new image. Reflash only after the
owner's OK; ask them yourself, as before. Gate green on it (lint, three type passes, both test stages, four twin runs,
npm, collect-only); imageFreeBytes 59,540 (was 59,916).
The fix: every streamed GET answer (/status and the five dict routes) now yields to the loop after each top-level
value, so no build holds the loop past its largest value. Small flat values (at most four scalars, no string over four
characters, keys included) are one json.dumps() instead of a walk: same bytes, about 1.8x fewer cycles on the Unix
port. Expected on the board: one /status build about 0.45 s of CPU instead of 0.74 s, spread over about 26 slices.
After the reflash, in this order, with no chroot leg running (the noble leg showed the Pi can pause for seconds):
  1. the /status timing probe as at 17:08 (per section, and the loop's longest hold during one build)
  2. test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer
  3. test_a_hazard_run_under_the_readers_load_reports_every_verdict (the 13 refusals should be gone)
  4. test_serving_sweep_at_the_reactive_default and test_heap_at_peak_while_a_full_ceiling_is_held: builds now
     interleave, so peak heap can move; serving_sweep left 368 B free at -1 before. Report both figures.
Your noble note: taken. 1. Node: right, the recipe as written cannot pass the host tier; its text gets the Node step in
the last round. 2. The six 7.6 s feed gaps: the six devices boot different object graphs, so a cost in the code would
not land within 61 ms six times; one pause of the Pi fits better. Your trixie leg settles it. If it shows a gap above
6,000 ms again, keep that job's twin logs and say which scenario was running. would_have_triggered_count 0 and the
memory-marker reread: taken.
Still owed, no new run: the boot console after real_sta_connect's teardown reset, if saved (the FRAM E51).

## 17:49 UTC, 2026-11-06: your 17:45 note; two test fixes (new head, same image); the stall fix is with the owner
New code on this branch: 78d2000a, with this relay's commit on top. Tests only, the image stays. No rerun needed for it.
Reason 2: the wordings say what a harness reset reads; 2 for a real expiry is the code's own meaning (the reset table's
row 2), and your fault_inside_the_running_graph boot (2, TIMER) is that. The REASON bits tell the two apart. No change.
hazard_run_under_the_readers_load: its session-end UART entries (W56, E80, E85, E81) are all in its provokes_log, so
they are its own. The 13 GET /status refusals are the stall: connections pile up behind a frozen loop, then pass the
ceiling of 6 together. It reruns after the stall fix, with loop_lag and serving_sweep.
answers_before_first_ntp: fixed. It now saves and clears the logs at its opening, since its task-ended check reads the
whole log and the flash line's E115 was not its own.
W35/W33: taken, thanks. The garbage NTP and DNS tests and the spoof test boot with no sync, as the first-sync test does,
so all three now declare SGP_WRITTEN_NO_TS and SGP_RESTORED_NO_TS. BootSignature is random when no sync came within
the boot's wait (src/asy_system_service.py:500-508), so 3274099019 just confirms that boot had no NTP: nothing to trace.
W65: taken, item 5's erase.
FRAM E51 at real_sta_connect's teardown, my reading: its hard reset can land between a chunk's two block writes, and
the next boot's read finds two valid, different copies (src/asy_fram_manager.py:243-246; the owner's 2026-07-18 rule
makes it a hard failure that the next write heals). One fact would confirm it, no new run: the boot console after that
reset, if saved; the lines around the E51 name the chunk being read. The handling goes to the last round's harness
item (a reset of a running board may leave one E51), not now.
Taken as figures: head guard 13 lines / 632 B against 32 / 2,048; radio re-init back in 8,216 ms against 20,000;
supervisor pass 2,316 ms between feeds; the c_stack and hard-reset reasons.
The /status fix: the owner agreed its shape (a yield per written value in the shared piece writer) and is deciding on
a lighter writing of small values in the same change. When it is built and gated, a new image comes here; reflash
only after the owner's OK, then: the /status timing probe again, loop_lag_under_http_load, serving_sweep, and
hazard_run_under_the_readers_load. The chroot legs can run meanwhile; say if a board run overlaps one.

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
