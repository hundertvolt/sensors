# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## 08:15 UTC, 2026-11-07: your 08:11 skill proposals, cross-checked against the main line
Status taken: reflash 08:02, one flash cycle today; /status's longest loop hold 122 ms against yesterday's
747-2,313 ms; .data +128 B and .bss equal, so the bench image's heap is 128 B smaller than CI's (noted for the
free-heap wrap-up, not near a margin). handback(): no objection; restore from the last pushed HANDBACK.md plus the
blocks appended since.
Keep the skills generic: what only round1.sh or this campaign needs goes in HANDOVER. Fold each change into an
existing bullet or row where one fits. After any skill text change run
`.venv/bin/python -m pytest -q tests_scripts/test_decision_vocabulary.py tests_scripts/test_citations.py` (seconds;
both scan .claude/skills); after a helper change, test_work_routines_helpers.py as well.
Clashes, not to apply as written:
- 2, its last sentence: work-routines' "Show any message meant for another session to the owner in a copy-paste code
  block" carries the owner's rule to the lead, and narrowing it changes an owner rule's scope (CLAUDE.md's
  decision-record rule 3). Leave that line as it is. The rest of 2 with three changes: name no tool ("a cross-session
  message"; the tool differs by host); results stay in the hand-back, the record, and a message carries notes and
  questions; the relay sentence quotes the owner's 14:35 instruction verbatim with its (owner, date) tag.
- 7, "a runner's rc 0 only means the step ran": true of round1.sh, not of the tier runners, which exit with
  `_require_clean_hardware_run.sh`'s verdict (0: everything that ran passed; read the deselected count, as
  work-routines says). That half goes in HANDOVER. The FRAM half is right (conftest saves `errcount-session-start.json`
  into the archive): name it as START in "After every run".
- 3, the grep: 45 tracked lines hold 192.168. addresses legitimately (docs, the twin, test fixtures), so a count on
  it flags real changes. Check the staged diff for the bench's own addresses from your env file instead
  (`git diff --cached | grep -cF "$ADDR"` per address, expect 0), and mask those in printed output.
Wording:
- 1: one clause on the "Fetch before every new command" bullet: "and before answering the owner".
- 5: right. Spell the merge `git merge -m "[skip ci] Merge relays" FETCH_HEAD` (a default message would start CI on
  the push), then the ancestor check, then push. Change all three ff-only places alike (the standing rule, session
  start 1, before a reflash 3), and say build only from a pushed commit, so the image record's commit resolves here.
- 6: the journalctl row is fine. The soak runner joins the runner list in "Running" rather than a row:
  `scripts/run_bench_soak_tests.sh --duration {short,mid,long} [pytest args]`, `--duration` first; `--dut-ip` is a
  pytest option and passes through.
- 8: the port half exists: `harness.resolve_board_device()` picks the board by USB vendor ID and its by-id name, so
  the Arduino is never a candidate. Add "never a fixed /dev/ttyACM*" to the "Find the board" row and point an ad-hoc
  script at the resolver. The bounding line is fine.
- 9: one clause on the "Watch a long run" bullet.
- 10: 21 joins the existing ResetReason 2 row (tests_hardware/README.md "Bench traps" already says a hard_reset() of a
  running board reads 21). The ResetReason 1 row is fine.
- 11: the copy line is fine; drop its second half, session start step 4 already says it.
- 13: keep the pinned uv (0.8.17) outside the worktree, e.g. ~/.local/uv-0.8.17/bin: an untracked folder inside it
  shows in _tidy.sh's report and is copied into a chroot leg with the checkout.
- 15: date the owner's quote, and keep the owner's own exceptions in the same line: a reflash, a wear-gated run, work
  outside the plan, a budget stop and a genuinely open decision still go to the owner.
- 16: right for MPREMOTE_DEVICE (unset is OK with exactly one MicroPython board). BENCH_DEVICE defaults to the one
  devices/*.toml with bench = true, whatever the board count, so unset is OK there always. "Bench host
  configuration" then calls both optional overrides.
Fine as proposed: 4 (one line, a few words of reason per item), 12, 14.
Apply them in your own commits with skill: blocks; I carry each into the main line from the hand-back.
The 20:38 order for day 3 is unchanged.

## 08:09 UTC, 2026-11-07: your 08:00 note - the skill fix is in the main line; the two facts; the image's 1,304 B
No new code for you: the image you built from 7cd1a24a stays, and the reflash waits on the owner's OK, as you have it.
- Skill fix 105a9fd6: right (/status carries ResetReason and SysUptime in its system group; BuildDate is only in
  GET /system's build). Carried into the main line as 1461960b; outside audit/ it now equals your head dc3ee940.
- Fact 1: my 20:38 line was wrong. test.sh's comment calls the mid band "the bench Pi4's class", but README's
  TEST_PARALLELISM entry and Part N already record the Pi4 at ~139 ms, the 4x band; your 120 ms agrees. So 16 jobs is
  what the code picks on this host. Change nothing: that comment, README's "16 jobs, green" and Part N's band rows get
  corrected from what step 3's legs show.
- Fact 2: the same scenario on arzi, alone on my idle host at dbe46072: PASS in 3.2 s, feed_count=10,
  largest_feed_gap_ms=1037, would_have_triggered_count=0. The injected fault does not stall the boot by itself; your
  15,309 ms is the same ten feeds stretched about 15x. Inferred: host load. One difference between yesterday's legs:
  trixie had Node, so its host tier ran the browser tests beside the MicroPython tier, while noble's failed at once.
  Not tested on its own; step 3 runs both legs with Node at TEST_PARALLELISM=4.
- The 1,304 B: the firmware's inputs are the same at my gate build (6cc6af1a) and at 7cd1a24a. The ARM compiler is
  the host's apt gcc-arm-none-eabi, unpinned (SPECIFICATION.md B.3, step 4): mine is 13.2.1, Ubuntu noble's,
  as on CI's runners; Debian trixie's is a GCC 14 build. Inferred: the compiler. Not near any margin: 58,236 B stay
  before the filesystem, and the link refuses an overlap. Two reads while you wait, seconds, no board contact:
  `python3 -c "import json,os;print(json.load(open(os.environ.get('PICO_TOOLCHAIN_DIR',os.path.expanduser('~/pico-toolchain'))+'/toolchain-record.json'))['compilers'])"`
  `arm-none-eabi-size -A <toolchain dir>/micropython/ports/rp2/build-RPI_PICO_W/firmware.elf | awk '$2>0' | head -10`
  Mine: .text 494,672, .rodata 655,956, .data 18,080, .bss 51,352. If your .data and .bss match, the board's RAM
  heap is what CI's image has and only code size differs. Both lines go in the hand-back.
The 20:38 order for day 3 is unchanged.

## 07:49 UTC, 2026-11-07: use the three skills, and fix them where they do not fit; the chroot recipe's Node step (new head, same image)
New code on this branch: bd11c5b9, with this relay's commit on top. No src/ change: the image stays.
The skills are in .claude/skills/ on this branch (since 2ef970b2, the 23:15 relay): bench-routines (read it at every
session start), work-routines (which checks, reading any log, the symptom table) and tree-care (setup, readiness,
cleanup), with their helpers in scripts/: _preflight.sh --bench, _log_verdict.py, _errcount_digest.py,
_failed_tests.py, _run_checks.sh, _tidy.sh. Use them for all generic work; the campaign's step plan stays HANDOVER.md's
and the relays'.
The owner, 07:39 today: "The bench shall use them, but also be allowed to adapt and repair them in case something
does not fit or is missing, and shall communicate such things back to you." So:
- Where a skill's step, an index entry or a helper is wrong, missing or does not fit the bench, fix it on this branch,
  in its own commit, rather than working around it. After a helper fix, run
  `.venv/bin/python -m pytest -q tests_scripts/test_work_routines_helpers.py` first (seconds, no board contact).
- Append one block per fix to the hand-back, as bench-routines' "The hand-back" now shows:
  `<UTC> skill: <skill or helper>: <what did not fit or was missing>; changed: <what>; commit <short sha>`.
  I carry each fix into the main line and confirm it in a relay.
Also on this head:
- README.md's clean-chroot recipe runs `uv run toolchain/setup_toolchain.py env --tier generic` in place of `uv sync`
  and then puts the installed Node on PATH: day 3's noble leg follows it as written. That step is the full installer
  too (npm ci and Chromium on top of what test.sh's first run builds), so no separate installer leg.
- BACKLOG.md's chroot entry holds only what changes a run; CLAUDE.md is condensed (no rule changed);
  SPECIFICATION.md E.3's one-file command is `scripts/_run_checks.sh mpy:FILE`.
The 20:38 order for day 3 is unchanged.

## 23:15 UTC, 2026-11-06: three skills for bench and lead work (new head, same image); read them at day-3 start
New code on this branch: 2ef970b2, with this relay's commit on top. No src/ change: the image stays.
.claude/skills/ now holds bench-routines (read it at every session start: order of work, an index of the harness's
board-control functions, host configuration, the hand-back format), work-routines (which checks, reading any log)
and tree-care (setup, readiness, cleanup). Their helpers are in scripts/: _preflight.sh --bench first,
_log_verdict.py on every log, _errcount_digest.py START.json NOW.json after every run, _failed_tests.py for reruns,
_tidy.sh for space. What changes for you:
- The hand-back: append one block per run in bench-routines' format. No raw logs, consoles, FRAM dumps or progress
  bars in it (HANDBACK.md is 42,781 lines, rewritten 54 times); name the files under logs/, now git-ignored.
- Rerun selections come from the run record (_failed_tests.py), and the block logs the selection, HEAD and BuildDate.
- After every run, copy build/archive/<runner>/<UTC>/ to logs/ at once: each runner keeps only its newest three.
- A reflash: harness.reflash(), then harness.restore_board_to_serving(); one ledger line per real flash cycle.
- heap_probe's drivers, reset_and_kick.py and round1.sh's flash() redo harness functions: use the index's entries.
- HANDOVER.md is stale where it differs: the responder ring is 512 B since bd67db94, the runner's later fixes and
  the relay protocol are missing. Its step plan stays; for everything generic the skills win.
The 20:38 order for day 3 is unchanged.

## 20:38 UTC, 2026-11-06: for day 3, when the owner restarts you (nothing today); your trixie note
Taken: trixie (Node is the whole of noble's 66; ROOT_CAUSES 21), the E51 console not saved (stays inferred), and the
owner's stop for day 2. Day 3 keeps the owner's 19:15 choice, in this order:
1. Build the image from this head, reflash after the owner's OK (ask them yourself), then the five reruns of the 19:04
   entry in its order, with no chroot leg running.
2. Two facts, no new run: each chroot leg's "== Test parallelism:" line (jobs, cores, multiplier, probe ms), and
   would_have_triggered_count for the 15,309 ms boot. test.sh's own comment names this hazard as not closed: a twin
   budget in wall-clock measures host speed. Its band puts a Pi4 at 2x (8 jobs on 4 cores); you saw 16.
3. The trixie leg again on this head with TEST_PARALLELISM=4 (no board contact): if the 16 failures and the gaps go,
   it is load; any that stay are code, and come here with their logs. Then noble with Node, the same setting.

## 19:15 UTC, 2026-11-06: the owner's order for the rest of today: the reruns first, the trixie leg stops
The owner chose at 19:15:43: stop the trixie chroot leg now, then the reflash and the five reruns of the 19:04 entry,
in its order, with the rest of today's bench time. The reflash still needs the owner's OK asked by you, as before.
Before stopping it: if any scenario job's first shared boot has already shut down, keep its log and give its
largest_feed_gap_ms; partial is fine. The trixie leg (and the noble rerun) go to another time; nothing else changes.

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
