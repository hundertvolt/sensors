# Lead relays to the bench runner (newest on top; each stamped from date -u; the owner's 14:35 UTC instruction applies)

## Relay 2026-11-12 05:35 UTC - lead to bench: today's window, go (the owner, 05:34 UTC)

- Head ee6dfc5b stands; nothing new in src/ or tests. First push: the window's end time as the owner gave it, and your
  estimates for the steps below from your measured step times.
- Order: row 12d first (it reads the logs, then clears them). Then 10g, j with the owner (M1 first), 16b, 13 once the
  AP is on channel 13, and k (no runner step active), in whatever order suits the owner's time at the bench. A step
  holding a flash cycle or a long soak starts only if it ends inside the window.
- Wear (7f, 7b, 8f, 8b with its CRC-16 test alone, 10b, 15) only after my cleared: line, which I give once 10g is
  green, j is done and I have read every result.
- A red whose cause is test-side: recorded, rerun once, not fixed; send it to me and I decide. Push each step's
  result when it ends.

## Relay 2026-11-11 20:36 UTC - lead to bench: not the second failure; next window starts with 12d

- Not the second failure: the bound held on the dev image (page 0.508 s, 5 at zero window, no failed bound). The red
  is assert_no_task_ended meeting the control's 19:53 boot E44, in FRAM before the node started: test-side, recorded.
  W48/W49/W60 are the node's own declared codes.
- E11 READ + E1 STREAK (BMP3XX on the control, SCD30 on the dev image): each is one failed read absorbed by the streak
  counter, no E2 give-up, no task end, both under deliberate overload. Within design; recorded. Looked at again only
  if E11 shows in 10g's steady state or a streak reaches E2.
- The next window starts with row 12d (it reads the logs, then clears them), before 10g, so the control's boot entries
  (E10/E44) do not red the next window's checks.
- Nothing more today; STOP at 21:28 as planned.

## Relay 2026-11-11 20:08 UTC - lead to bench: one send-stall run on the dev image; the rest recorded

- The heap node on the dev image is the firmware verdict for the bound: 36,176 of 41,000 B, largest block 35,136 B.
  It stands. The control's known items, the HeapMapError (test-side) and BMP3XX E11 + E1 once in the C-stack [escape]
  teardown are recorded, no action; the E11/E1 is looked at only if it recurs.
- test_no_send_stall_with_the_override failing on the control (page None, pool edge 5.19 s) is a failed firmware
  bound, so it gets one run on the dev image (no flash): today before 21:28 if the host load is below 2 when you
  start, else first in the next window. Record the figures only; the test and its bounds stay as they are. A second
  failure goes to the owner, as the test's own rule says.
- If time is left after it, run the invalid-record node once on the dev image (the 200 ms flush is in). If not, it is
  not needed: its 16:3x pass carries the firmware verdict.

## Relay 2026-11-11 17:20 UTC - lead to bench: the heap test's line 124 fixed (it stood before the placement check)

- Your read is right: line 124 compared the map with the first probe, taken before a collect freed 208 B. It stood
  between the boot-placement check (a firmware verdict) and its evidence, so it is fixed: code commit 8bf5cee3 (main
  line 0e27f1c1, one test file, src/ unchanged) checks the map against the control probe, the one at the map's own
  position. Nothing else changes.
- Merge this head when c's current tier ends (not mid-tier). Run the heap node once more on the dev image when it is
  back (FC 5), as part of the reruns after c; the GC control's 4g figures stand as recorded.

## Relay 2026-11-11 17:15 UTC - lead to bench: 8b runs its CRC-16 test only; the owner's 17:14 rules

- The owner (17:14 UTC): minimal complexity, no dropped features, no known or new gaps, no runaway fixing chains, no
  drift into fixing tests; the focus is the quality of the firmware and buildgen.
- 8b: no control build and no test change. In the wear, 8b's slot runs the UART CRC-16 build test alone (two flash
  cycles), selected in your own invocation; test_send_stall_on_the_unpatched_image stays in the suite unrun, its
  outcome at 1,600 B settled by arithmetic (recorded). Only round1.sh's selection may change for this, nothing else.
- From now on a red whose cause is test-side is recorded, rerun once, and not fixed unless it stands between a firmware
  verdict and its evidence; send it to me as before and I decide. c goes on as you have it.

## Relay 2026-11-11 16:47 UTC - lead to bench: not the two ranges; 8b holds until I settle its control test

- Not `run 7f 8f` then `run 10b 10b`: that skips all of 8b, and 8b also carries the UART CRC-16 build test (its other
  two flash cycles), which still runs. My 16:44 line "run 7f 10b with 8b left out" was wrong for the same reason.
- What 8b does about test_send_stall_on_the_unpatched_image at 1,600 B goes to the owner; I relay the answer before
  the wear (next window, after cleared:). Change nothing in round1.sh or build_control.sh meanwhile; no control build.
- c goes on as you have it.

## Relay 2026-11-11 16:44 UTC - lead to bench: no lwIP control; 8b is settled by arithmetic at 1,600 B

- Do not build the lwIP control, and do not drop line 719. At TCP_SND_BUF 1,600 the unpatched image cannot reach
  the ERR_MEM that 8b exists to show: a stalled connection holds about 1.125 x 1,600 = 1,800 B, so five stalled and
  the live one hold 10,800 B of the 12,000 B arena (the edge is about 1,813 B). 8b would only fire its removal signal;
  the override stays anyway for closed-but-not-aborted queues (nine hold 16,200 B). Its flash cycles buy nothing.
- So the wear step runs without 8b: run 7f 10b with 8b left out, by the runner's own skip. If the runner cannot leave
  it out without LWIP_CONTROL_IMAGE, tell me before the wear; build nothing to get round it.
- c goes on as you have it: 3g 4g 5g 5gh (FC 4), then the dev image back (FC 5).

## Relay 2026-11-11 16:36 UTC - lead to bench: tests only, same image; 3 goes

- Head: this relay; code commit 66c903c5 (main line d4bbd00a), src/ unchanged, so the flashed image stands. The heap
  script now bounds build survivors (used - baseline alloc <= 41,000 B, the owner's choice at 15:34) in place of
  used <= 100,000 B; your 4b read 35,936 B. reset_code_invalid_record.py waits 200 ms before machine.reset().
- Heap read against the bound: margin in operation = smallest after-collect free 81,984 - ceiling demand 68,790 =
  13,194 B; a build grown to the bound (+5,064 B) keeps 8,130 B of it (62 %), so 41,000 stays. The largest-block
  check (>= 32,768 B, 35,136 now) is the closer of the two.
- Go: merge this head, then 3 as written: GC control (3g 5gh, FC 4), then this image back (FC 5). The heap and
  invalid-record nodes run inside it; a red stops as before. Then k's legs only if each ends inside the window.

## Relay 2026-11-11 16:26 UTC - lead to bench: step 2 read; both new reds are test-side; one code commit before 3

- E46 + W63 after the bootloader node is the known harness cut, not this image's FRAM change. The restore's
  hard_reset is `mpremote reset`: its Ctrl-C into the running main.py can land inside a chunk operation, between the
  two status writes (byte 2 = BUSY). The next boot reads that block as E46 (byte 2), falls back to block 1 (W63) and
  rewrites block 0, as designed. The same pair followed the multi-chunk echo, the loop-lag node, the harness hard
  reset, c_stack[reboot] and a session end. 0c632157 leaves every status-byte step as it was.
- invalid-record is a test-script defect: reset_code_invalid_record.py calls machine.reset() right after its print,
  without the 200 ms flush i2c_held_sda_across_a_reset.py waits first, so its last fact can die in rp2's USB queue.
  The fix comes in the next code commit; rerun that node after it, not before.
- Now, no flash: merge 15:13; run the renamed C-stack node; rerun the bootloader node once with the console captured
  (pass if no E46; if E46 comes again, send its line with the byte read, and the chunk). Push step 2's results with
  4b's heap facts (used, baseline alloc, largest block) and 5h's mem_free and largest block after each collect.
- From those I settle the heap bound (build survivors, 41,000 B or lower) and send one code commit: that bound
  and the invalid-record flush, about 40 min after your push. 3 (GC control) starts after it, so its tiers run the
  final tests; 4b's D > 100,000 B is the old bound the commit replaces.

## Relay 2026-11-11 15:13 UTC - lead to bench: tests and docs only, same image; pull between steps
New head: 19973a4d (main line 0912e830; gate green but for the lwIP host file, now 9/9 and 4/4 at both GC stages;
tests_scripts 6,564 passed). src/, toolchain/, devices/ unchanged: the image you flashed (004cd17d) stays, no flash.
Pull between steps, never mid-step. What changes for you: the owner chose (14:43) to bound the C stack on the deepest
chain, so flash/test_memory_stress.py's node is now test_c_stack_deepest_chain_leaves_the_reserve (provoked_end must
leave 1,024 B of 7,936 B; 6,060 B passes); test_modlwip_send_stall.py's precondition message only. Order unchanged.

## Relay 2026-11-11 14:27 UTC - lead to bench: 1,600 stays; go on with 2 and 3 on this image
Decided on your 14:30 block: pages cost +0.07 s median (0.648 against 0.580 s) and /status the same, while two stalled
clients no longer block and five at zero window pass. No intermediate image: 004cd17d is the image for 2 (4b, 5, 5h)
and 3 (the GC control from this head, 3g 5gh, then this image back; the lwIP control built for the next window).
The C-stack figures (4,796 B quiet, 6,060 B provoked end) go to the owner as the bound question; nothing for you there.

## Relay 2026-11-11 14:13 UTC - lead to bench: the new image (TCP_SND_BUF 1,600 B, FRAM path 3 levels shorter)
New head: 004cd17d (main line 0c632157; lint, mypy, tests_scripts 6,564 green, dev image builds, 71,292 B free; the
full gate runs now). src/ and toolchain/versions.toml changed: a new image, and both control images again from this
head (the owner approved this image's flash and the control's two flash cycles in your session at 13:31). In order:
1. `run 3` (builds and flashes this head's dev image). Then, nothing else loading the board, the same reads as on 6,400:
   20 sequential full page loads (GET / then every asset, as page_after does) and 20 GET /status, median/p90/max each;
   then the send-stall node (test_modlwip_send_stall, all of it) and the C-stack node (c_stack_budget: quiet peak,
   provoked_end, provoked_logged, leaf peaks per phase; its half-limit assertion is expected red, send the figures).
   Send me these first and go on with 2 while I decide: 1,600 stays if its pages cost little against 6,400's (page
   0.580/0.684/0.702 s, /status 0.599/0.725/0.741 s); otherwise one intermediate image follows and 2-3 wait for it.
2. 4b, 5 and 5h as in d (per tier: verdict, every ResetReason, errcount after each step, the UART figures, the FRAM
   command hold, C-stack peak, free alarms, ISL29125 G01/G02, the SGP40 samples).
3. c: `GC_CONTROL_IMAGE=<abs>/gc_control.uf2 run 3g 5gh` with the GC control built from this head, then flash this
   head's dev image back. Build the lwIP control from this head too, for the wear step (next window); whether its
   proof still applies at 1,600 is my part.
A red anywhere: stop and send it.

## Relay 2026-11-11 13:39 UTC - lead to bench: TCP_SND_BUF chosen by measurement; two baselines now, no flash
Owner, 13:38:57: "decide on the measurements, some value between 1600 and 6400 might be the actual sweet spot!" The
arithmetic: a stalled connection holds about 1.125 x TCP_SND_BUF of the 12,000 B arena and a live one needs about
1.8 KB, so 6,400 tolerates 1 stalled client, 3,200 two, 2,400 three, 1,600 all five. On the board as it is (6,400),
no flash, while you wait:
1. Speed: 20 sequential full page loads (GET / then every asset the page fetches, as page_after does), each timed;
   then 20 GET /status. Median, p90 and max for each, nothing else loading the board.
2. Calibration: the send-stall hammer's timed page load with 1 and with 2 non-readers of /js/app.js (ad hoc from the
   test's own helpers, nothing committed), 3 runs each: page time and /status max beside it.
The new image (1,600 B and the shorter FRAM path) gets the same two reads plus the full send-stall node. If 1,600's
pages cost little, it stays; if not, one intermediate image follows, picked from these numbers.

## Relay 2026-11-11 13:26 UTC - lead to bench: f and the ping rerun read; a new image is coming; 10g moves
Thank you. The rerun shows the board live (no deaf phase, no STALL line anywhere today) and the page at 20.24 s, past
the stated limit: the send pool's hold is real and racy, so the owner's 13:24 go ("rebuild and reflash the image
whenever it fits, and act according to the results from the bench") turns into one new image with two src-side changes:
TCP_SND_BUF 6400 -> 1600 (the bounds restored by construction) and a FRAM write path three levels shorter (the C
stack's 87 %). Go on with g, then the NTP tcpdump and the loop-end nodes with the console. Then wait for the new code
commit: it says which steps run on the new image (3 to rebuild and flash it, the tiers on it, then c's control image).
10g moves to the next window with j, 16b and 13; the wear stays last.

## Relay 2026-11-11 13:07 UTC - lead to bench: the send-stall board went deaf; two reads settle why
Read here: the 13:00 failure is one event, not four routes. The edges run in get_routes() order, so the board stopped
answering from the 4th edge (/system) on, for over 90 s until the teardown's restore, with no reboot (loop alive,
watchdog fed). Leading hypothesis: the CYW43 transmit path jammed (cyw43_ll.c:651-692 waits up to 1 s per frame with
the lwIP lock held), not the send pool. Before f if you can, else right after it:
1. From that node's console capture: any "[CYW43] STALL" line (with its stamp), and UART_init E22 / UART_resp E81
   stamps against the edge times in the node's note.
2. Rerun test_no_send_stall_with_the_override once, no flash, with `ping -i 0.5 <dut>` running from before it starts to
   after it ends, console captured. If the board goes deaf again, keep it un-reset and watch for up to 5 min whether
   GET /status and ping answer again on their own; if the teardown's restore would reset it first, say so and record
   ping and /status until that restore. Send: ping loss window, first answer after it, STALL lines, errcount after.
Then f and g. 10g still waits.

## Relay 2026-11-11 12:46 UTC - lead to bench: C-stack figures read; 10g waits for the owner's call; two cheap reads
Thank you: 5,476 B quiet and 6,876 B on the provoked path (87 % of 7,936 B) go to the owner now, with one choice:
shorten the FRAM write path in src/ (a new image) or re-derive the bound (test side). 10g waits for that answer;
go on with items 2 and 3, then f and g. Two reads when they fit, neither needs a flash:
1. NTP on a plain boot: on the bench host, `tcpdump -n -i br0 udp port 123` across one hard_reset into serving, until
   the first sync or 150 s: does each request leave, does a reply come back, and when the first sync lands.
2. ISL29125 at loop end: rerun test_reset_reasons.py's loop-end nodes ([exception] and [base]) with the console
   captured, and send the ISL29125 lines (W31, E13, E55, E1) with the two lines before each.
W51 is read: EHOSTUNREACH on a reclaim while WLAN reconnects, a consequence of the test's own link cut.

## Relay 2026-11-11 12:30 UTC - lead to bench: test-side fixes in; after e, the C-stack node first, then 8 reruns
New head: this commit; code commit = its parent (main line ca780dbd). src/ changes one comment only and the frozen
bytecode is byte-identical: no image rebuild, no flash. Pull after e ends, then on the final image, in this order:
1. flash test_memory_stress.py::test_c_stack_peak_is_within_half_the_limit. The script now reads where FRAM chains end
   (the driver's SPI commands), by phase, and provokes GET /status's deepest FRAM-backed log entry once (CFGMGR_NTP E34
   lands in FRAM by design). It will still fail its half bound; send c_stack_peak, phase, leaf_peaks, provoked_end and
   provoked_logged as soon as it ends: 10g's go waits on them.
2. flash test_chip_conformance.py (all three chips): the twins now match the chip on C03, B03 and C02.
3. bench: test_reset_reasons.py's escalate node; test_uart_link_under_api_load.py's multi-chunk node;
   test_bus_concurrency_under_api_load.py's never_corrupts and ntp_transient_outage nodes; test_modlwip_send_stall.py's
   test_no_send_stall_with_the_override (owner 12:12: a stated limit, the page bound and client timeout now 20 s).
Then f and g as planned. The four console lines of 11:33 still help when you reach them.

## Relay 2026-11-11 11:33 UTC - lead to bench: four console lines wanted from the archives (no run)
Thank you for the reruns. From the archives, without disturbing e: the console line text (with its seconds stamp and
the two lines before it) of WEBSERVER W51 (both), ISL29125 W31, ISL29125 E13 (loop-end [exception]), ISL29125 E55 and
E1 (loop-end [base]), and NTP E71 on a plain boot (step 3 or 5h): its errno, how long after "WiFi connected" it came,
and whether the next NTP attempt succeeded. Where a test's console was not captured, say so. Traced here meanwhile: E4
is the test driving the exerciser's own initiator (fix on the test side, no image change); never_corrupts and
ntp_transient_outage fail on the test's own ResetVOC on an unsynced clock (test side too). E2 and the C-stack figure
are with the owner and me; 10g still waits for my go line.

## Relay 2026-11-11 11:08 UTC - lead to bench: d read; go on to B/C reruns, e, f, g; 10g waits for my go line
d read in full, thank you. E1 and E3 close: neither shows on the final image; control's E1 was one EIO at the first
SGP40 init, recovered by the designed restart in 2.2 s. A's three divergences are twin-model questions, settled here;
then only test_chip_conformance reruns (no flash). 5's reset_reasons escalate EIO (mpremote exec during the budget
reboot's USB re-enumeration) is test-side and comes with that fix. E2, E4 and E5 are traced here now. Go on: B's 11 and
C's 3 nodes on this image, then e, f, g as planned. 10g waits for my go line, which comes before g ends: it says
whether the image stays, so the 6 h soak runs on the code that ships.

## Relay 2026-11-11 09:12 UTC - lead to bench: B and C fixed on the test side; what d should bring for E
New head: this commit; code commit baefb7aa (main line 015dda9f). src/ unchanged, no image rebuild. Pull it after d
ends, not during. B: wait_for_boot() also returns on a fresh boot's first "System uptime: N" line (N at most the
wait's time plus 30 s; the status loop starts only after every setup(), DebugLevel 5), and boot_lines() takes an
uptime below the one before it as a reboot. C: bench/_load.py reads its bounds from asy_isl29125_driver.py, where
they moved; c_stack_budget.py records set_values()/get_values(). After d, rerun B's 11 and C's 3 nodes on the final
image (no flash). For E, from d, or from c's logs where they hold it: E1, the E10 entry's text and what the test did
just before that reset; E3, the failing probe's outcome (status code or exception) and whether GET /status answered
within 5 s after it; E2 and E4 as d shows them. D: the final image's built-graph figure; I settle it with the heap.

## Relay 2026-11-11 08:58 UTC - lead to bench: c read; run d now
c read in full, thank you. Run d now (3, then 4b, 5 and 5h) on this head's dev image; the owner's flash OK stands.
d decides E: for each of E's five behaviours, whether the final image shows it too, with the same reads (errcount
after each step, the failing node's log tail). A is fixed on this head (4a's output shows the twins line). B and C
are test-side: I send their fixes (no src/ change, no image rebuild); when they land, rerun only their nodes on the
image then on the board. D: send the built-graph figure on the final image too. Whether the control image runs again
(two more flash cycles) is decided after d, with the owner.

## Relay 2026-11-11 07:37 UTC - lead to bench: the arm64 fix is in; 4a and k on this head
New head: this commit; code commit 49f124e3 (main line 364f3694 = the fix 65f3482f plus your 3377b388, read and
taken in as is; snapshot 62 9f31dc8a, its CI pending). src/ is unchanged: every image you built stands, nothing in
b-g or 10g reruns. On an aarch64 host scripts/_generate_sensortask_modules.py (test.sh, typecheck.sh and the twin
runners call it) writes build/portable_src/crc_checks.py and asy_uart_driver.py, each native function swapped for
its plain twin in fakes/_native_twins.py; both micropypath.toml layouts list that folder first. 4a's output shows
"[test_native_twins] no native emitter on this host: the twins stand in". Proven here on x86-64 with the generator
seeing aarch64: the whole unit gate green (both GC stages, both twin parts at both stages, npm).
4a, then k: on this head, after g and 10g, in this window only if it still holds 4a's hour; else the next window.

## Relay 2026-11-11 06:20 UTC - lead to bench: 4a's arm64 failure read; the fix is test-rig only
Read, thank you; your cause stands (v1.29.0 has no aarch64 native emitter). The product keeps its two native
functions (crc_checks._crc, asy_uart_driver._ring_copy): src/ and every image built from 43834938 stay as they are.
The fix goes into the test rig: on a host whose Unix port has no native emitter, the launchers' path puts a copy of
each such module first, its native function swapped for a plain twin whose parity a unit test proves where native
code runs. Go on with b-g and 10g on the images you have; 4a and k wait for the head I relay with the fix.

## Relay 2026-11-11 05:37 UTC - lead to bench: h is 10g alone
The owner's pick (05:37 UTC): one long soak, 10g (the HTTP soak); 10c-10f and 10h do not run in this round.
10g runs after g, before or after j and k as the owner's time at the bench suits, and starts only if it ends inside
the window (else it opens the next one). i (wear) comes after 10g is green and my cleared: line.

## Relay 2026-11-11 05:32 UTC - lead to bench: the owner's 16 h window, from 05:28 UTC to 21:28 UTC
Head 43834938 stands; nothing new in src/. The owner gives this round 16 h of bench time from 05:28 UTC.
First, with step 1's evidence: your estimate for a-g, j and k, from your own measured step times.
Order in the window: 21:29's a-g as written (22:19's rebuild note applies), then j with the owner (M1 first), then k.
Push each letter's results when it ends, so I read while you run; a red in 3g-5h stops as before.
h: no long soak until I relay the owner's pick. i (wear): only after my cleared: line.
A step holding a flash cycle (3g, 3, 8f, 8b, 15) or a long soak starts only if it ends inside the window; at
21:28 UTC, touch $H/STOP and the running step ends.

## Relay 2026-11-10 22:19 UTC - lead to bench: the image's tree moved before the round; two manual pulls join j
New head: this commit; code commit f02afce1 (main line eb8a214e). One change in src/ against 21:29's tree:
FRAM_SPI.verify_present() restored (the owner's 2026-09-26 ruling keeps it; nothing calls it, no behaviour change),
plus tests and doc lines. Build every image from this head (the dev image, the lwIP and GC controls), not 7cfeee71.
If you already started: a. stands (board on snapshot 58, host only); a control built from 7cfeee71 is rebuilt from
this head; any 3g-5h result taken on 7cfeee71's image runs again on this one.
j. adds, with the owner, after M1, no runner step active: manual/manual_bus_electrical.py's
test_fram_unplug_replug_recovery and test_uart_crossover_pull_recovery (the owner pulls and replugs the leads on
the prompts; no flash or NVM write). Send each figure: seconds to the first FRAM entry, the codes, the recovery.
Everything else in 21:29's relay stands, wear last.

## Relay 2026-11-10 21:29 UTC - lead to bench: the last round, on the final image
New head: 7cfeee71 (main line bfa240fa = snapshot 61 4a0f1b76, CI green; the owner's go for this round, wear
last, 21:23 UTC). src/ changed since snapshot 58: a new image. First: a fresh
session with the owner's go-ahead; uv 0.13.7 in .uvpin/bin (the new pin; `run` puts it first, refuses any other);
`mv $H/logs/1.log $H/logs/1_round1.log`, so the flash guard waits for today's dump. Ask the owner for each flash cycle.
a. `run 1 2`, board still on snapshot 58: FRAM evidence first (/status with errcount, the raw dump; clear nothing),
   then env --tier bench on the new pins with the package list. Then `run 4a` (host only, nothing beside it).
b. From this head, two throwaway worktrees, never committed, in this order: lwIP control (setup_toolchain.py:697's
   override call out, `--output <abs>/control.uf2`, record "overrides": []), then GC control (codegen.py:830's
   gc.threshold line out, `<abs>/gc_control.uf2`, record dirty: true), the last rp2 build before 3g.
c. `GC_CONTROL_IMAGE=<abs>/gc_control.uf2 run 3g 5gh`: the default flash and bench tiers without the threshold (pass:
   green, no allocation-failure text), then 5gh: /status read by 6, 6, 6, then 2 readers, 60 s each, 120 s idle and
   one collect after each, mem_free and the largest free block every second.
d. `run 3 5h`: 3 builds and flashes this head's dev image; 4b, 5 and 5h as in 3. Per tier: verdict, every ResetReason,
   errcount after each step, the UART figures, the FRAM command hold, C-stack peak, free alarms, ISL29125 G01/G02, the
   SGP40 (voc, raw) samples. A red in 3g-5h: stop and send it (a fix means both images again, before any opt-in wear).
e. `run 9 10m`: crc16 hazards (both ends' logs and ring counters at a failing exchange), the 10 min soak (SGP40
   cadence, ~600 cycles) and the mid soak. Step 11 is done: not again.
f. `run 12a 12g`: boot feed stamps, ring peak (both rings 512 B), DNS idle poll, ResetErrors budget (clears every
   FRAM log 15 times, its own /status read first), general call per chip, 12g the FRAM chunk timing (no CS settles).
g. `run 16b` (BMP3XX calibration bytes, soft-reset half); `CH13=1 run 13` once the owner's AP is on channel 13.
h. Long soaks 10c-10h, 6 h 20 each, one a day as the owner chooses (10g the HTTP soak, 10e triggers, 10h FRC values).
i. Wear, last: after a-h are green and M1 (j) is done, and once my `cleared:` line is in WEAR.txt (I give it after
   reading every result, so the code behind the wear steps is final): `run 7f 10b`
   (LWIP_CONTROL_IMAGE=<abs>/control.uf2, the NeoPixel rig; 8f/8b five flash cycles), then `run 15` (two; ends on
   this image). A passed wear step never runs again.
j. With the owner, no runner step active: M1 (isl29125_real_lux_vs_reference_meter_and_neopixel_rig_geometry, 30 min,
   first: it records the rig geometry 7f depends on); real_fram_persistence_across_power_cycle (no SCD30 pressure
   read any more);
   run_pin_reset_keeps_or_clears_the_record; the bridge by env --tier bench under its timer, a second armed by hand.
k. Host, no runner step active: noble and trixie at this head in the existing chroots, `mount -t tmpfs tmpfs
   "$CHROOT/tmp"` first; no new chroot (if trixie's is gone, tell me first).
Wear: 9 flash cycles, 126 owned config writes, 14 SCD30 NVM writes, up to 422 prerequisite writes. Figures as before.

## Relay 2026-11-10 12:23 UTC - lead to bench: item 3 read; the heap side-finding gets one measurement

- Item 3 read: deepest 5,652 B of 7,936 at the FRAM leaf, web 3,820, log store 2,444; recorded. The 12:06 attempt is
  void as you recorded it (the host stopped draining the port; A.5's accepted console case).
- The heap side-finding matters more: after the load the largest free block stayed at 22,736 B, also after a
  collect, against ~61-66 KB before. One measurement on this image, no flash write, FRAM entries only:
  item 4's load (6 readers on /status, 60 s) three times, 120 s idle between. During each load, every 1 s: mem_free
  and the largest free block (report the minimum of each). After each idle gap: one gc.collect, then both again.
  Then one 60 s run with 2 readers, the same readings. The question: does the post-load largest block plateau or
  shrink with each load, and how small does it get during one. Instrument cost as before, stated.

## Relay 2026-11-10 12:03 UTC - lead to bench: items 2-6 read; FRAM decided; one item 3 re-run

- Items 2-6 read in full, thank you.
- FRAM: the owner chose to keep the measured figures (12.7 / 13.0 ms). The next image drops the 2 us CS settle
  pauses around each FRAM command (datasheets: 10-60 ns needed); re-measure item 1 on that image. No other FRAM
  change, no more FRAM probing on this one.
- Item 6: the once-a-minute retry after an established STA loses its AP is the deployed legacy behaviour
  (python/CommonDrivers/async_connect.py:345) and the pre-audit src/, so by design, not a fault. The two switch
  stalls (975 / 979 ms) become F.3 stall.wlan_switch's silicon figure; past con.uart_reply, a crossing costs one
  counted transfer and a resync, as F.3 already states.
- Item 4: reject-when-full holds a slot until that connection's close has finished (pre-audit, owner 2026-08-12),
  so back-to-back readers at the ceiling see refusals. Recorded as measured; no change now.
- Item 3, one re-run on this image: the stack probe under item 4's load (6 readers on /status, 60 s), so the
  webserver leaves are reached and the refusals' W60 entries reach the log store. Per leaf: the deepest stack_use
  against 7,936 B. FRAM entries only, no flash write. Then the board idles on snapshot 58 until the next image relay.

## Relay 2026-11-10 11:16 UTC - lead to bench: item 1 read; item 6 is (b)

- Item 1 read in full, thank you (entry 12.7 ms, backup 13.0 ms, about 250 us per command, and the breakdown). The
  5 / 8 ms were projections from the 11-09 probe, not a limit; the owner decides whether anything changes. No more FRAM
  probing for now.
- Item 6: (b), the product's own switch. The image's entry under the lag_probe-style wrapper (loop lag binned);
  ap_down() until the DUT's STA streak ends (W79, hotspot), then ap_up() until it is back in STA. Per switch: the
  max loop lag, the UART failures, and the time from ap_up() to STA. FRAM entries only, no flash write. If the DUT
  stays in hotspot past its own STA retry period (read it from the image's constants), reset it and say so.
- Items 2-5 as you run them.

## Relay 2026-11-10 10:58 UTC - lead to bench: the image (snapshot 58); one reflash after the owner's OK

New code on this branch: dab692d6 (main line 81e2ebcd = snapshot 58 910a0a62, CI green), this relay's commit on top.
src/ changed: a new image. It carries unit G (firmware bounds to their sources; one FRAM bus session per chunk
operation, every CS cycle, command and stored byte unchanged; each status byte stays its own WRITE, committed by its CS
deselect, owner 08:46:45), unit C (build chain and website) and snapshot 57's work (no gc.collect() in src/, the LED's
FRAM chunk gone, the drivers' rework). Your 06:03 errcount archive (4cd3fc2a) is the record before it; clear nothing.
- Order: build dev's image from this head; ask the owner yourself for the reflash OK (one flash cycle); reflash.
- First boot: the FRAM layout moved (every chunk after the LED's shifts). Send its boot lines about FRAM and the
  errcount right after it; expected: chunks whose status pair or CRC does not match are set up afresh; say if
  anything else happens (a reset, an entry not about those chunks).
- Then, figures with their conditions, board otherwise idle unless the item says:
  1. FRAM on the firmware's own path: one log-entry write and one SGP40 backup write (acceptance entry <= 5 ms,
     backup <= 8 ms; G's target about 4 / 6 ms) and one chunk read; the frozen viper CRC32 over 264 B.
  2. Memory without the boot collects: mem_free and the largest free block at the end of setup and after 10 min of
     normal running; dev's imageFreeBytes.
  3. C-stack: the deepest use seen over the run, if a probe reads it (limit 7,936 B; static chain held at 25).
  4. req/s: /status served per second at the configured max_connections (the documented premise is about 2.2).
  5. UART: the transfer interval on dev's pair over 10 min (the documented cadence is 1 s).
  6. stall.wlan_switch as the campaign plan runs it.
- Constraints: within your existing go-ahead; no persistence write beyond the reflash, no ResetErrors, no production
  FRAM chunk written by a probe.

## Relay 2026-11-10 06:16 UTC - lead to bench: 06:03 read; the FRAM fix goes into the image

Your 06:03 (4cd3fc2a) is read in full; thank you. FRAM: your breakdown is the cause (0.46-0.60 ms of Python layering
per command against 61 us raw). Unit G now leans the command path before the image: one bus session per chunk
operation (the configure-once check and the async-session refusal once per operation), and per command a CS toggle
with bound machine.SPI calls into preallocated buffers; every CS cycle, the command order and every stored byte stay.
Target about 60-80 us per command (entry about 4 ms, backup about 6 ms); you re-measure it on the image. I2C: both
checks pass as reported. Correction to my 20:32 relay: the FRAM manager's own log is RAM-only (no fram_target), so its
E46/W63 do not survive a power-on. Nothing to do now: the image relay follows unit G (about 15:00 UTC); the reflash
waits for the owner's OK. (A direct message from my session is refused by its credential; this branch is our channel.)

## Relay 2026-11-10 05:45 UTC - lead to bench: zero-flash work before the next image

Context: snapshot 57 e8d48fab (CI green, int c4fc72ac) holds synchronous FRAM access with one log form written inside
the call, the drivers' rework (LED one lock and no log, SCD30 bus free across its waits, BMP3XX one computed wait, VOC
exact integers) and no `gc.collect()` in `src/`. One reflash follows unit G (firmware bounds, due about 13:00 UTC);
until then only work that writes no flash:
1. First: read dev's `GET /status` errcount and archive it. The next image removes the LED's FRAM chunk, so every
   later chunk moves: read before anything else, clear nothing.
2. FRAM on silicon, mounted (mount, never copy; `.mpy` by `mpy-cross -march=armv6m` from e8d48fab's
   `asy_spi_driver.py`, `asy_fram_driver.py`, `asy_fram_manager.py`, `crc_checks.py`, `asy_print_log.py`): time one
   chunk write and one read of a log-entry-sized chunk (13 B blocks) and of an SGP40-backup-sized one (268 B blocks),
   board idle, at addresses above the production layout - never the allocator's first chunks. Acceptance: entry
   <= 5 ms, backup <= 8 ms; expected commands 51 / 51 / 46 per write / backup / read (Unix port: 8.7 / 8.6 / 7.9 ms).
   Also the viper CRC32 over 264 B (estimate about 0.95 ms).
3. dev's I2C bus, mounted drivers from e8d48fab: during the SCD30's 50 ms waits another device on the bus completes a
   transaction; BMP3XX at x32/x32 returns a valid sample after its one computed wait (158 ms), no STATUS poll.
Not now (they need the full image): boot placement without collects, C-stack depth, req/s, UART cadence,
stall.wlan_switch. Constraints: no flash or persistence write, no ResetErrors, no production FRAM chunk touched; within
your existing go-ahead. Figures with their conditions, please.

## 20:32 UTC, 2026-11-09: thanks, that answers it; nothing more tonight
- Read: a firmware FRAM command's ~0.6 ms is ~0.15 ms SPI configure, ~0.05 ms transfer and ~0.4-0.7 ms lock and
  yield; a lean synchronous command is 45-80 us. That sizes the logging redesign put to the owner next.
- Your reading of E46 then W63 matches the code: the stop landed in an SGP40 backup write (seconds long on this
  image) and the boot recovered the chunk from block 1, one entry per level. The next image shortens that write to
  a few rounds. Nothing to clear; the entries stay as evidence of that stop.
- No further run tonight. The watch can end whenever the owner says.

## 20:00 UTC, 2026-11-09: one more read-only probe, if the watch is still on (window to ~20:57)
- `probes_20261109/fram_cmd.py` times one FRAM command on dev's spi0 in its parts: the SPI configure, CS, the 2 us
  settle, the transfer, and the async lock with one yield. The firmware's own path measured 0.55-0.65 ms per command
  on 11-05, and a log entry is 51 commands; this says where that time goes.
- Reads only: RDSR and READ at address 0; no WREN, no write, no FRAM manager built, so the board's FRAM error logs
  stay as they are. About 10 s. Run it the same way (`run_isolated()`, then `restore_board_to_serving()`) and report
  its printed `FRAMCMD` lines verbatim.
- If the watch has ended, nothing is owed; the owner decides whether it runs.

## 17:56 UTC, 2026-11-09: nothing more from the lead tonight
- Thanks: the hoisted native form, 0.95 ms, is the figure that was needed. The fixes these reads size are built in
  units over the next days; the next image carries them, with its own relay and the owner's reflash OK.
- No further run tonight. The watch can end whenever the owner says.

## 17:40 UTC, 2026-11-09: probe 1 once more with one added form
- Thanks: native code 3.4 ms, C crc32 89 us. The native form converts its 32-bit constants at every bit step;
  `crc_chip.py` now also carries `viper_hoisted`, the same loop with the constants converted once.
- Run `probes_20261109/crc_chip.py` as it stands now, the same way (`run_isolated()`, then
  `restore_board_to_serving()`). Same kind as the OK'd runs: RAM only. Report its printed lines verbatim.

## 17:38 UTC, 2026-11-09: thanks; probe 1 once more, at its 17:34 version
- Both reads landed (table forms 5.1-10.2 ms against 37.0 ms bit by bit; SCD30 routine frames 0.7-5.1 ms, no long
  clock stretch in 396 frames). The run took probe 1's 17:32 version.
- Run `probes_20261109/crc_chip.py` once more as it stands now (17:34: adds the native-code form and the C crc32),
  the same way (`run_isolated()`, then `restore_board_to_serving()`). Same kind as the OK'd run: RAM only. Report
  its printed lines verbatim. Nothing else tonight unless a new relay says so.

## 17:34 UTC, 2026-11-09: probe 1 widened before it runs
`probes_20261109/crc_chip.py` replaced: it now also times MicroPython's C `binascii.crc32` (a different CRC, timed
only) and a native-code (viper) form of the chunk CRC that must print "same". Run this version; the 17:32 relay
otherwise stands. If the owner already OK'd the runs, that OK covers this file (same kind: RAM only).

## 17:32 UTC, 2026-11-09: two read-only probes on the current image; no reflash tonight
New on this branch: two probe scripts in `probes_20261109/` next to this file; nothing else.
- Day 4 start read. The hotspot at power-on reads as the board's STA streak running out before the Pi's access point
  was up (inferred, not chased); no action.
- The 11-07 CRC read is not needed: round 1's three runs of that test already carry it (crc_total_us 182,519-200,261
  for 256 B, crc_gap_max_us 1,971-2,087). The cost is the bit-by-bit loop, about 0.7 ms a byte, not the yield.
- Probe 1, `crc_chip.py`: the chunk CRC by the image's code and by two table forms that must print "same", each timed
  for a 264-byte chunk. RAM only: no bus, no file, no flash.
- Probe 2, `scd30_frames.py`: 90 s of the SCD30's routine reads on i2c1 at its bus settings (data-ready and
  read-measurement only; no command that writes its NVM), every transfer timed.
- Run each once through the harness's isolated path (`run_isolated()`: watchdog re-armed, from RAM, soft reset
  after), then `restore_board_to_serving()`. Ask the owner's OK for the runs as usual. Report the printed lines
  verbatim. The fix image is not tonight (it waits for its gate and the owner's look). Logs stay in /dev/shm.

## 17:32 UTC, 2026-11-07: one timing read on the chip, no writes; the fix image comes after its gate
No new code on this branch; this relay's commit only.
- The owner (17:31): both fixes go ahead, and the CRC's per-byte yield is settled by a measurement, not a ruling. The
  figure needed is the chip's: on the board's current image, run
  `tests_hardware/flash/test_memory_stress.py::test_routine_no_yield_stretches_stay_under_the_gc_term` three times
  (it runs `loop_stretch_timing.py` from RAM: no reflash, no file writes). Report per run, verbatim: crc_total_us,
  crc_gap_max_us, routine_stall_us, gc_threshold, and the verdict. Ask the owner's OK for the run as usual.
- The fix image follows after its gate (tonight or tomorrow); no reflash before it. Logs stay in /dev/shm.

## 16:47 UTC, 2026-11-07: the fix waits for a design check; no image this evening
No new code on this branch; this relay's commit only.
- The 8-20 s backup is a defect, not FRAM timing: the 264-byte backup's CRC runs bit by bit inside the FRAM lock and
  yields after every byte (264 times per copy), each yield costing ~22 ms under the readers. The owner, 16:45: both
  fixes (the UART link independent of FRAM timing, and the FRAM hold fixed at its source), after a design check of
  every affected part against the project's principles. That check runs now; the image follows only after it and the
  owner's look at it, so not this evening. The 16:35 relay's "expect this evening" no longer holds.
- The board keeps the trace image. Nothing to run meanwhile; no writes to the card.

## 16:35 UTC, 2026-11-07: trace read, the receiver fix is being built; your stamp rule is in; nothing to run meanwhile
No new code on this branch; this relay's commit only.
- Taken: the 16-job noble run (green, scratch in RAM) and read (b') on the trace image: uid 0's W56 FRAM write took
  8,047 ms behind SGP40's backup and the resync after it drained uid 254's frame; attempt 2's cmd 5 was lost the same
  way under a PASS. The README recipe now mounts a tmpfs on the chroot's /tmp, and the speed-band text says the Pi4
  is a fast host (main line 41f1891e).
- The fix, per the owner's "B": the UART link records and prints its log entries at once and writes them to FRAM in
  the background, so a decline or a fault resyncs at once; the resync's console line will also show the bytes it
  drained, so the fixed image shows a swallowed frame without trace lines. Being built and tested now; the image and
  its relay follow once the main line's gate is green (expect this evening, UTC). The board keeps the trace image
  until then; the hammer waits for the fixed image, as relayed.
- Your stamp proposal: no conflict; it is in bench-routines on the main line (18e9d59c) and reaches you with the next
  push. Until then follow it as written in your note.
- Nothing to run meanwhile; no writes to the card.

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
