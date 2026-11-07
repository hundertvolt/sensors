# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## 14:40 UTC, 2026-11-07: the owner on the microSD's wear: no more heavy writes to it; the trixie rebuild is off
No new code on this branch; this relay's commit only.
- The owner, 14:39 UTC: "I hope that's not wear of the card, and too heavy write cycles should not be conducted
  allover again..." The standing wear rule already covers the host's own storage; this applies it to the microSD.
- Off: the trixie rebuild from 14:14. A fresh chroot (debootstrap, toolchain build, npm, Chromium) is the heaviest
  card write this campaign has. The trixie leg stays at this morning's run (GCC 14: env, lint, typecheck 0, 5,838 unit
  tests passed); its 8 failures are the freeze class step 3 traced to the card on noble.
- The 16-job noble run finishes as it is (scratch in RAM). After it: no new chroot, no rebuild and no test.sh leg on
  the card unless a relay asks. Every log, vmstat output and console capture stays in /dev/shm until you send it.
- Read only, nothing written; send the numbers: (1) the root filesystem's lifetime writes and the card's size:
  `findmnt -n -o SOURCE /`, then /sys/fs/ext4/<that partition>/lifetime_write_kbytes, and `lsblk -b -d -o NAME,SIZE`;
  (2) the card's make: /sys/block/mmcblk0/device/{name,manfid,oemid,date}; (3) any card errors in the kernel log
  (`dmesg | grep -iE 'mmc|i/o error'`, or `journalctl -k` if dmesg has rotated); (4) the noble chroot's size
  (`du -sxh`): whether a later periodic check can run with the whole chroot in RAM; (5) if the 12:33-13:33 vmstat log
  kept its bo column, its sum (KiB step 2 wrote).
- Unchanged: the reflash to the trace image after the owner's OK, read (b') up to three times, the hammer after the
  fixed image. Their logs follow the /dev/shm rule above.

## 14:23 UTC, 2026-11-07: the owner chose to trace, then fix, the UART miss: a trace image (new image)
New code on this branch: 3c0fafe2, with this relay's commit on top. src/ changed: a new image, bench only. It also
carries main line 2f6d1453 (the twin CI soak's fixed warm-up; nothing the board or test.sh runs).
- The owner, 14:20 UTC: "B" - trace the loaded UART miss with one instrumented image, then fix the UART receiver so it
  never waits on its own FRAM log write inside an exchange (a second image, later). The FRAM bus hold stays and gets
  documented unless the trace shows the receiver fix is not enough.
- The image adds board-clock lines prefixed TRACE (ticks_ms, print only, nothing persisted): each received frame's
  header and validation result ("TRACE rx"), the ACK ("TRACE acked"), each persisted fault and W56 decline with its
  FRAM write time ("TRACE fault persisted" / "TRACE W56 persisted ... ms"), the drain's start and end with bytes
  drained, the listen backoff, the initiator's sweep sends and replies ("TRACE sweep" / "TRACE sweep got"), and every
  FRAM bus wait or hold over 100 ms ("TRACE fram wait" / "TRACE fram hold"). Unit tests for the four touched modules
  pass on it; it fails lint by design (prints), and never reaches the main line.
- Order: let the 16-job noble run finish; then, before the trixie leg: build this head's image, reflash after the
  owner's OK (ask them yourself), and run read (b') as before (reset first, 3 readers, console with host stamps), up
  to three times until one misses. Send, for the run with a miss (or the last one if none misses): every TRACE line
  and SGP40 backup line from the reset to the hazard run's end, as a file, plus the run's verdicts. No miss in three
  is still an answer: the W56/fault persist times and the FRAM holds give D directly. Then the trixie leg as relayed.
- The hammer stays after the fixed image, per 14:14: it runs on the image that stays.

## 14:14 UTC, 2026-11-07: step 3 green - a host setting; after the 16-job run, trixie with a tmpfs /tmp; the hammer
No new code on this branch; this relay's commit only.
- Taken: test.sh at 4 jobs green with its scratch in RAM (devtmpfs, as you found; RAM all the same). The chroot
  failures are the microSD's write stalls under test.sh's scratch, not code. README's recipe gets
  `mount -t tmpfs tmpfs "$CHROOT/tmp"` beside the bind mounts (and its umount), and its "16 jobs, green" line and
  test.sh's band comment get corrected from your 16-job result. Use that tmpfs line from now on, TMPDIR unset.
- After the 16-job noble run: the trixie leg rebuilt on the current head with the tmpfs /tmp, at the default
  parallelism if the 16-job noble run is green, else at 4. That completes both legs for the owner's periodic check.
- The hammer (10f soak_long_hammer): its hold's reason, the /status stall, is gone, confirmed on the board this
  morning. One thing still sets its place: an open owner question on the UART miss, whose answer may bring a trace
  image and then a fixed one. So it starts after my next relay, which carries that answer, on the image that answer
  leaves; in the form the campaign plan gives it, its long-soak gate asked of the owner by you, as always.

## 13:34 UTC, 2026-11-07: step 2 read - microSD write stalls; step 3 tests the remedy, not the failure again
No new code on this branch; this relay's commit only. Step 2 is taken as read: alone, the two failures (arzi, wozi)
are the two boots whose first minute holds a 6-7 s vmstat hole with blocked processes and wa 18-65; no swap, no
memory pressure; every other first boot is about 2.0 s. The twin calls no fsync, so the stall is page-cache write-back
throttling a writer (inferred), and test.sh's scratch (mktemp: the twins' logs, FRAM and config state, pytest's
tmp_path) sits under the chroot's /tmp on the microSD.
- After read (b'), step 3 changed: test.sh at 4 jobs in the noble chroot with TMPDIR=/dev/shm exported inside the
  chroot (its /dev is the host's bind mount, so that is the host's tmpfs), vmstat to /dev/shm as you planned. First
  `df -h /dev/shm` inside the chroot; with under 2 GB free, say so and stop. This tests the remedy: green, or the
  failures and gaps gone, makes it a host setting; the same failures with the scratch in RAM put it back on code.
- If 3 is green: one more run at the default parallelism with the same TMPDIR, which decides what README's
  "16 jobs, green" and test.sh's band comment say. If 3 is red: its failing names, gaps over 5 s and vmstat holes.
- Either way it lowers the microSD's write load, which the host-wear rule asks for anyway.

## 12:38 UTC, 2026-11-07: clocks and E88 settled; a code reading of the uid miss for read (b') to confirm or kill
No new code on this branch; this relay's commit only. Clocks: settled, thank you. E88: taken as the crossing step's.
- The reading (inferred from the code; read (b') decides). The responder ACKs, then its callback declines command 7,
  and _reject_wrn() persists W56 to FRAM (wrn_s: the FRAM write first, then the console line) before _resync() starts
  its drain, which ends only after 1.5 s of quiet. The sweep's 3 s wait starts when the initiator has the ACK. So,
  counted from the ACK, the next value arrives at 3.0 s and the drain ends at D + 1.5 s, where D is that FRAM write's
  time, its SPI lock waits behind the readers' /status FRAM reads and SGP40's backup included. D over 1.5 s puts the
  next frame into the drain: drained, no ACK, E81. In read (b) the spacing gives D of about 0.5 s for uid 0x00 (3.0 s
  minus 2.50 s, if 0xFE's own write was short): a margin of about 1.0 s, where an idle board has 1.5 s.
- What read (b') shows if this holds and it misses: no reject line for 0xFE; 0x00's reject-to-resync interval longer
  than its usual 1.505 s (the drain swallowed 0xFE and waited another 1.5 s of quiet); and D = 0x00's reject time
  minus (UART_init's E81 time minus 8 s window minus 3 s wait). Send those three numbers. If it does not miss: each
  value's reject-to-reject spacing for all five fields, so D's spread under the reset is visible.
- Nothing changes in src/ on an inference; if (b') confirms it, the fix question (the decline's resync not waiting on
  a log write) comes to the owner with the numbers.

## 12:34 UTC, 2026-11-07: reads (a)-(c) and read (b) received; one more board read between your steps 2 and 3
No new code on this branch; this relay's commit only. Your plan stands (step 2 alone per device, then step 3), with
one insert after step 2 and before step 3, nothing else running:
- Read (b'): read (b) again exactly, but with the failing test's first step, reset_all_error_logs(), before it (FRAM
  only, no flash wear). Read (b) without it did not miss; the reset is the one procedure difference you know. Same
  console log with host stamps. A miss: send the console lines from the reset through the uid sweep. No miss: say so.
- From read (b)'s saved console, no rerun: the lines around UART_init's E88 (peer initiated), with stamps, against the
  sweep's lines. The loaded misses logged E85,E81 (no ACK); read (b) E85,E88.
- Taken as read: the 400s are the per-call timeout after a 6.5 s stall (W49, then Microdot's catch); the ~9,0xx gaps
  are the deliberate watchdog scenario; the SIGINT test's 1 s window was missed by a stalled counter (inferred). The
  ~7.2 s first-boot gaps: step 2's alone runs give their size without load; name them in its hand-back.
- Clocks: your 12:45 note reached me at 12:33 by my date -u, and your 10:28 one before 10:25. If your stamps come from
  the Pi's clock, it runs about 12 min ahead; fine for vmstat against the console, but say which clock you stamp with.

## 12:26 UTC, 2026-11-07: noble at 4 jobs - step 3 on the noble chroot first, no trixie rebuild yet; three reads
No new code on this branch; this relay's commit only. The missed vmstat is no loss: the steps below give it.
- Order: 1. read (b) now, nothing else running, as you planned. 2. Then my step 3 in the noble chroot as it stands:
  the scenario harness alone, one device at a time, all six (every one failed there), `vmstat -t 1` and `free -m` on
  the host. 3. Then test.sh at 4 jobs in that same chroot with vmstat running: my step 1. The trixie rebuild waits
  until these say host or code.
- Three reads from the noble logs you have, no rerun, before 2:
  a. arzi's and grkizi's 400 in every_admitted_connection...: the twin log around that request. My reading of the
     code: the per-call timeout is 5 s (web.per_call_timeout_s); after a loop stall longer than that, the overdue
     timeout runs before the read that is ready by then, the head read times out, and Microdot's read catch prints
     the TimeoutError and answers 400. If so, the log shows that traceback, W49 "Connection reclaimed (per-call
     timeout)" and a feed gap over 5 s across the request. A 400 without them is code: put it first.
  b. The ~7.2 s first-boot-like gaps: which boot phase each falls in (the runner's "boot phase:" lines around it).
  c. test_the_timeout_interrupts_the_files_process_once: its failure text and the timing it reports.
- Your recurring names (survives_bus_and_api_load... on 5 jobs, every_admitted_connection... noble both days,
  static_site_is_served_over_real_http and failed_config_snapshot_is_sent_as_unavailable) all run alone in 2.

## 10:24 UTC, 2026-11-07: trixie at 4 jobs - no blind rerun; host log during noble, then each failing device alone
No new code on this branch; this relay's commit only. Snapshot 46 is green on CI; its one code change is the twin CI
soak's warm-up (scripts/_digital_twin_ci_suite.py), which neither test.sh nor the board runs: nothing to pull.
- Not a full trixie rerun at 1 or 2 jobs: a pass there shows only that less load passes, not what stalled a twin for
  9-20 s. Three steps instead, in this order:
  1. Now, for the rest of the noble leg: on the host, outside the chroot, `vmstat -t 1` into
     logs/day3_20261107/chroot_evidence/noble/vmstat.txt until test.sh ends, and `free -m` once at its start. A feed
     gap over 6,000 ms on seconds with a deep run queue, swap traffic (si/so) or high wa is the host; one on quiet
     seconds is not.
  2. Then read (b), as relayed at 08:59, with nothing else running.
  3. Then in the trixie chroot, nothing else running, vmstat logging as in 1: the scenario harness alone for dev,
     klkizi, schlafzi and wozi, one device at a time, once each - test.sh's own job line:
     `uv run scripts/_digital_twin_scenarios.py --device <d> --logs-dir <dir> --shared-port-53` (after a test.sh run
     has built the toolchain and sites in that clone). A scenario failing alone is code: send its twin log. All four
     passing alone, with the noble gaps on loaded seconds, closes it as host capacity at these settings; then I correct
     test.sh's band comment, README's "16 jobs, green" and the Part N rows.
- With 3, say which scenario each ~9,0xx ms gap came from: a deliberate watchdog scenario's gap is its timeout plus
  window and does not count; wozi's hung-shutdown failure (watchdog late past its window) is the one to check there.

## 08:59 UTC, 2026-11-07: my 08:35 margin reading is wrong; two zero-wear reads for the uid miss; the harness fix; the address rule goes (new head, same image)
New code on this branch: a6357cc6, with this relay's commit on top. No src/ change: the image stays.
- The owner's go (08:42) for both fixes. The first is in: fram_evidence_saved saves /status over REST before it asks
  for the board fixture, whose reachability exec stopped main.py (tests_hardware/conftest.py, its test, one README
  line; main line d81a6620, and the address rule's removal 0d875688). Your next runner session should carry no
  "pre-session /status not saved" note: say so once. Until then, the hand saves before each runner start (08:35) stay.
- The second waits, because its reason was wrong. The responder does not wait 1 s for a second chunk: it declines the
  hazard command (id 7) right after its ACK (_accept_set, _set_callback, _reject_wrn: W56), then resyncs (1.5 s quiet
  drain, then a 1.5 s write hold-off). So the sweep's 3 s leaves 1.5 s, which 122 ms loop holds do not explain, and
  chunks 2 then 255 has the same shape and never missed. Cause open; no wait changes until it is found.
- Read (a), now, from files you have: the UART_resp counter the no-reader run added (hazard_noload.txt, if it holds a
  read before and after), against 23 in each loaded run. One more without readers: under load the responder never
  handled 0xFE (drained or never seen). Equal: it handled 0xFE as in a pass, and the miss is on the reading end.
- Read (b), after both chroot legs: your no-reader procedure again with 3 readers on GET /status for the run's length,
  and the board's console read throughout with host time stamped on each line as it arrives (Board.tail_log or a plain
  serial read; no exec). The responder's lines at the uid sweep say whether 0xFE was declined ("callback rejected
  command 7"), refused as a frame or drained, and when against 0x00's. Those lines go in the hand-back.
- The address finding: the repository is public, and the owner, 08:52: "A simple LAN IP is nothing to be worried
  about". Nothing is masked or rewritten, and bench-routines' address rule goes in this head (no mask, no per-address
  check before a commit). Passwords and config files stay as the Never list and the env-file line say.
The 20:38 order for day 3 is unchanged.

## 08:35 UTC, 2026-11-07: your 08:30 note - skills carried; the uid miss's margin; the pre-session save never runs
Skills: cb6a1b78, d2737a05, c55da08e and e5b28b9d read and carried into the main line (int a5d3296b, equal to your
head outside audit/); the doc, skill and shell gates pass (791 tests, shellcheck clean).
The uid miss: your reading fits the code, and it has a number. After an ACKed first chunk the sweep waits
_QUIET_TIMEOUTS x timeout = 3 x 1,000 ms (src/asy_uart_link_driver.py; dev keeps DEFAULT_LIMITS). The responder
waits 1,000 ms for chunk 2 (_recv_train), logs the timeout to FRAM, then drains until the line has been quiet for
the resync window, 1,500 ms (_resync, _drain). It listens again at about 2,500 ms plus those steps' delays, so the
sweep's slack is 500 ms. A frame that lands inside the drain is read as line noise, restarts the quiet wait and is
never seen as a frame: no ACK for that value and nothing else changes, which is [True, False, False]. Not the
limit: the ACK read window (8 x timeout, start_timeout_ms in _read_raw) and the write hold-off after the drain (ends
near 4,000 ms, inside that window). Under the readers' load the responder's side has several timed resumes (the chunk
wait, the FRAM write, the drain's wait), each of which can queue behind a /status build, while the sweep has one
sleep. Inferred, not traced. The other legal-after-legal pair, chunks 2 then 255, has the same 500 ms and passed.
So the repeat reads: a miss at uid 0xFE or chunks 255 is this margin; a miss anywhere else is not, and comes here
with its log. A missed value also costs the sweep its full 8 s window, so a run with a miss runs about 8 s long.
The fix would widen that wait in src/ (a new image, so the owner's OK); I take it to the owner, not you. After the
repeat, go on to trixie as ordered.
The pre-session /status: confirmed by reading, for every session on a running board since 2026-10-15.
fram_evidence_saved gets the `board` fixture first, and that fixture's is_reachable() runs `mpremote exec`, which
stops main.py (its own comment says so). Only then does session_start_evidence try REST at --dut-ip: connection
refused. The FRAM logs are still kept (the raw dump, then dut_ip's save after its reset), but /status's RAM-only
fields from before the session (ResetReason, SysUptime) are lost. Its unit test calls session_start_evidence
directly, so it never saw the fixture order. Until it is fixed, save /status by hand before every runner start,
not only at session start. The fix is host-side (no image); I take it to the owner with the sweep's.
WEBSERVER W51 in loop_lag's teardown is _WRN_HTTP_SOCKET_ERROR, a socket error on one connection; which connection,
not traced.
The 20:38 order for day 3 is unchanged.

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
