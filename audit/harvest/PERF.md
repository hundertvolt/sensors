# Harvest — PERF: Timing and capacity budgets

What the project's own comments, docs and history already record for this area (snapshot `2a88cc8`).
Recorded, not verified or triaged; `audit/HARVEST.md` explains the kinds, tags and method.

Kinds: SETTLED 4, INVAR 4, LIMIT 2, RISK 4, ASSUME 31, OPENQ 8, NOTE 1 — 54 items.


## src/asy_udp_socket.py

- **PERF.N001** RISK · `src/asy_udp_socket.py:126-129` — "Busy-polls ipoll(0), yielding via
  sleep_ms(wait_time_ms) each cycle... (<=0 waits forever)" — Default 20 ms poll = 50 Hz forever for an
  unbounded wait (captive DNS) · covered-by: NET.S11 · [H02]

## src/asy_wifi_service.py

- **PERF.N002** RISK · `src/asy_wifi_service.py:593, 616-621` — "for _i in range(10):" — Loop does not
  break on `STAT_GOT_IP`, always 5 s under the lock · covered-by: NET.S07 · [H02]

## src/crc_checks.py

- **PERF.N003** RISK · `src/crc_checks.py:36-48` — "yields after every byte so a large buffer can't
  stall other tasks" — `sleep(0)` per byte (cost, and under whatever lock the caller holds); CRC32
  register exceeds rp2 small-int range each shift · covered-by: ALGO.S08 · [H02]

## tests/test_asy_uart_driver.py

- **PERF.N004** ASSUME · `tests/test_asy_uart_driver.py:1464-1465` — "4.4ms of held loop per 53-byte
  frame (SPECIFICATION.md Part F.5.8)" — single dated bench measurement underpinning the clamp design ·
  related: BUS.T05 · [H04]

## tests/test_asy_udp_socket.py

- **PERF.N005** ASSUME · `tests/test_asy_udp_socket.py:514-516` — "wait_time_ms defaulted to 0, which
  busy-polls ipoll(0)+sleep_ms(0) ~9000x/sec while idle (~180x the rate at 20ms)" — measured on the Unix
  port; fixed 20 ms default poll interval for the two real callers · related: NET.S11 · [H04]

## tests/test_asy_webserver_service.py

- **PERF.N006** ASSUME · `tests/test_asy_webserver_service.py:2306-2308` — "measured to cost ~53%
  throughput via per-write asyncio.wait_for()" — single measurement justifying per-source piece
  granularity · - (low) · [H04]

## tests_hardware/README.md

- **PERF.N007** ASSUME · `tests_hardware/README.md:271-277` — "concurrency 2 -> 0% reset, 4 -> 25%, 8 ->
  12%, 24 -> 25%" — Dated measurement at a limit of 4 (limit is now 6); resets begin at the ceiling. ·
  related: PERF.T02 · [H08]

## REAL_HARDWARE_TEST_QUEUE.md (snapshot only; being updated by another session)

- **PERF.N008** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:229` — "**Owner decisions left**: a single command
  is *below* the row's ~1 ms mark" — T4 MEASURED (write 2,833-3,395 us, read 783-881 us, block hold
  18,089-23,148 us): owner to decide per-CS-command yield and whether the script is committed. ·
  related: PERF.T04 · [H08]
- **PERF.N009** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:243` — "**The curve does not flatten**: ~+3.5 s per
  reader, so 3 readers reach 88–98 % of the 15 s cap." — R2 MEASURED; one sweep showed UART entries
  afterward ("most likely" logged after, R4 settles it); budget and design fix are the owner's. ·
  covered-by: PERF.T03 · [H08]
- **PERF.N010** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:246` — "**+0.90 s** is far more than one extra
  FRAM-backed logger's `setup()` should cost, and is unexplained" — R6 OPEN: boot-latency delta of the
  `CFGMGR_SYSTEM` setup-order fix. · related: PERF.T06 · [H08]
- **PERF.N011** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:262` — "whether zero-think-time readers are inside
  the product's contract" — F18 OPEN (owner): 4 readers → `ResetErrors` PUT refused 20× (no admission
  fairness), no answer in 30 s; UART link E20/E22/W10 under load. · related: PERF.T03 · [H08]
- **PERF.N012** SETTLED · `REAL_HARDWARE_TEST_QUEUE.md:289-291` — "The limit itself is settled and
  confirmed on the committed image" — `max_connections = 6` settled; W-rows ride the next regular run by
  owner decision (2026-09-24). · related: PERF.T02 · [H08]
- **PERF.N013** OPENQ · `REAL_HARDWARE_TEST_QUEUE.md:295` — "Owner to judge whether 1.36 s is
  acceptable" — W3 MEASURED: `/status` 6,859-6,865 B median 1.36 s; no 1,024 B-piece silicon figure
  exists; `test_end_to_end_timing.py` "times no `/status`". · related: PERF.T02 · [H08]
- **PERF.N014** ASSUME · `REAL_HARDWARE_TEST_QUEUE.md:359-365` — "(6 today; 4 when this was measured)
  ... back-to-back clients at the limit see ~70 % refused" — Ceiling reset rates measured at limit 4
  (2026-09-19). · related: PERF.T02 · [H08]

## HARDWARE_TEST_HANDOVER.md (snapshot only; sitting IN PROGRESS in another session)

- **PERF.N015** SETTLED · `HARDWARE_TEST_HANDOVER.md:23-24` — "**Settled, not to be re-measured**: the
  connection limit of 6 and its lwIP ensemble" — Also the 256 B response bound (I.3) and measures A and
  B (I.4(f.1)). · related: PERF.T02 · [H08]
- **PERF.N016** OPENQ · `HARDWARE_TEST_HANDOVER.md:140-142` — "Owner: yield between the CS commands of
  one write (~3 ms → <1 ms), or keep as is" — T4/W3/R2 owner decisions (R2: BACKLOG 24's
  batched/concurrent reset first, BACKLOG 32's budget after). · related: PERF.T03, PERF.T04 · [H08]
- **PERF.N017** ASSUME · `HARDWARE_TEST_HANDOVER.md:145` — "each FRAM-backed config manager then costs
  ~95 ms (~33 ms FRAM read, ~33 ms verify, ~25 ms file)" — R7 partial soft-reset capture: 1.15 s first
  list, 8 timers 112 ms apart, WLAN+RTC at 16.3 s; per-logger figures need an instrumented build. ·
  related: PERF.T06 · [H08]
- **PERF.N018** OPENQ · `HARDWARE_TEST_HANDOVER.md:146` — "only a pre-fix build answers it (2 extra
  flash cycles, ~30 min)" — R6: owner to run the A/B or close it. · related: PERF.T06 · [H08]

## scripts/_digital_twin_ci_suite.py

- **PERF.N019** ASSUME · `scripts/_digital_twin_ci_suite.py:108-116` — "twin 8.259s worst, hardware
  6.32s idle and 11.58s under load ... dev needs ~10 more sources to breach it" — ResetErrors budget
  (80% of cap) sized from dated measurements (BACKLOG item 24). · related: PERF.T03 · [H09]

## toolchain/versions.toml

- **PERF.N020** ASSUME · `toolchain/versions.toml:38` — "2,324 B of GC heap per connection" — Single
  measured figure behind the connection budget. · related: PERF.T02 · [H09]

## toolchain/micropython_overrides.py

- **PERF.N021** ASSUME · `toolchain/micropython_overrides.py:175-178` — "2,000 B = the pre-branch
  design's own MEM_SIZE 8000 over max_connections 4 ... the configuration this project already ran in
  the field" — MEM_SIZE per-connection floor anchored to a prior configuration; the fielded units run
  legacy 1.26 firmware. · related: PERF.T02 · [H09]

## tests_scripts/test_digital_twin_ci_suite_errcount.py

- **PERF.N022** ASSUME · `tests_scripts/test_digital_twin_ci_suite_errcount.py:277,300-302` — "the
  twin's worst observed dev sweep is 8.91s and real hardware is 6.32s idle / 11.58s under three
  concurrent readers" — `_RESET_ERRORS_BUDGET_S` sized from dated measurements; must sit between 8.91 s
  and the 15.0 s server cap (BACKLOG item 24) · related: PERF.T03 · [H10]

## tests_scripts/test_micropython_overrides.py

- **PERF.N023** ASSUME · `tests_scripts/test_micropython_overrides.py:627-647` — "The shipped pattern at
  6 (PCB 9, SEG 48, MEM_SIZE 12000) is clean" / "8000 / 4 = 2000. A relationship, not a tuning target" —
  Project rules beyond lwIP's own checks: shared pools must serve every admitted connection, 3 spare
  PCBs, MEM_SIZE >= 2000 B per connection (from the fielded design's share) · related: REST.T06 · [H10]

## SPECIFICATION.md Part A.4 (Architecture — deep reference, 148-285)

- **PERF.N024** ASSUME · `SPECIFICATION.md:228-230` — "Margin is ample (FRAM at 1MHz, 8KB chip ... low
  single-digit ms, three orders of magnitude under both the 4s reset delay and the ~8s watchdog-starve
  wait)" — Timing margin asserted from arithmetic, not measured here; C.7 later measures ~305 ms per
  chunk (yielding). · related: XCUT.T03 · [H12]

## SPECIFICATION.md Part A.7 (wozi's construction order and dependency graph, 358-569)

- **PERF.N025** ASSUME · `SPECIFICATION.md:500-509` — "boot-to-first-`200` was ~1.9-2.2s before WP1 ...
  ~6.1s (`wozi`) / ~7.7s (`dev`)" — Twin-only boot timings; 15s test budget raised from 6s. · related:
  PERF.T06 · [H12]
- **PERF.N026** SETTLED · `SPECIFICATION.md:510-512` — "not something to \"fix\" by reordering
  `webserver` in the stagger, or by treating the latency itself as a defect" — Boot latency not a defect
  (CLAUDE.md WP6). · covered-by: PERF.T06 · [H12]
- **PERF.N027** ASSUME · `SPECIFICATION.md:521-527` — "pre-WP baseline 7.74s, WP1+WP2 9.80s, WP1–WP8
  complete 9.76s, and 10.66s ... 23 consecutive reboots ... no `WDT_RESET`" — Single dated silicon
  series (dev, 2026-09-16), 5 samples each. · related: HW.T16 · [H12]
- **PERF.N028** OPENQ · `SPECIFICATION.md:535-537` — "the `CFGMGR_SYSTEM` fix's own +0.90s is far more
  than one extra FRAM-backed logger's `setup()` should cost, and is unexplained
  (`REAL_HARDWARE_TEST_QUEUE.md` R6)" — Unexplained boot-latency delta; queue row R6. · [H12]

## SPECIFICATION.md Part B.14.2 / B.14.2.1 (`lwip_connection_counts`, 1215-1379)

- **PERF.N029** ASSUME · `SPECIFICATION.md:1366-1368` — "A connection costs 2,324 B of GC heap, not 196
  B" — Derived per-connection cost. · related: PERF.T02 · [H12]

## SPECIFICATION.md Part C.7 (Error handling & logging contract, 1807-1891)

- **PERF.N030** ASSUME · `SPECIFICATION.md:1850-1854` — "All 21 of `dev`'s chunks ... concurrent `GET /status`
  stayed at 0.56-0.76s throughout a `PUT` lasting 8.1s ... Its cost is fixed per chunk (~305ms)" — Dated
  silicon figures; load-case concern open in BACKLOG item 24. · covered-by: PERF.T03 · [H12]

## SPECIFICATION.md Part D (src/ Production-Quality Checklist, 2576-2728)

- **PERF.N031** INVAR · `SPECIFICATION.md:2631-2632` — "No blocking I/O, `time.sleep`, or unbounded
  loops." — Absolute rule with stated exceptions elsewhere (C.3.1 blocking `sleep_us(2)`; FRAM sync
  path). · related: PERF.T08 · [H12]

## SPECIFICATION.md Part E.8 (Measurement traps, 3271-3362)

- **PERF.N032** LIMIT · `SPECIFICATION.md:3300-3301` — "An asyncio loop-latency probe cannot separate
  \"idle on a timer\" from \"blocked.\"" — Measurement limitation. · related: PERF.T09 · [H12]
- **PERF.N033** LIMIT · `SPECIFICATION.md:3304-3305` — "`I2C.scan()` is synchronous and blocks the loop
  for a 128-address sweep ... inflated a measured worst-case RTT from 112 ms to 574 ms" — Load-model
  trap. · [H12]

## SPECIFICATION.md Part F.1 — Core platform facts

- **PERF.N034** ASSUME · `SPECIFICATION.md:3536-3539` — "measured: ~20 pieces regressed a fixed workload
  +53% versus 5 pieces" — Single dated-less measurement behind the rule "keep piece count bounded to a
  small, fixed number of sections". · related: REST.S06 · [H13]

## SPECIFICATION.md Part F.3 — Long-blocking operations

- **PERF.N035** INVAR · `SPECIFICATION.md:3648-3650` — "Any new code that blocks the event loop for a
  noticeable time must not do so while timing-sensitive work like the Neopixel animation needs to run" —
  Design principle, no mechanical check; "noticeable" undefined. · related: PERF.T08 · [H13]

## SPECIFICATION.md Part F.5.3 — Free wins in the 1.29 build

- **PERF.N036** INVAR · `SPECIFICATION.md:3756-3758` — "the *benefit* ... has never been timed on this
  bench, and must not be quoted as a measured speedup" — Documentation discipline; claim unmeasured. ·
  [H13]

## SPECIFICATION.md Part F.5.8 — UART read() blocks the loop

- **PERF.N037** ASSUME · `SPECIFICATION.md:3890-3897` — "`readinto(buf, 53)` returned 53 ... 4195 us ...
  4370-4405 us" — Bench measurement (5 trials) motivating the clamp. · related: HW.T16 · [H13] ⟨quote
  not matched at the anchor⟩
- **PERF.N038** ASSUME · `SPECIFICATION.md:3937-3953` — "clamped **278 us** ... Re-measured on the dev
  bench (2026-09-12) ... clamped **137 us** ... scheduler noise floor ... 400-900us ... 3.1ms to 6.3ms"
  — Dated bench figures; the doc itself notes a loop-latency probe cannot distinguish idle from blocked.
  · related: HW.T16, PERF.T08 · [H13]
- **PERF.N039** ASSUME · `SPECIFICATION.md:3984-3992` — "the longest non-yielding stretch is **2,849
  us** ... a block operation holds the bus for **21,269 us** (measured on the dev board,
  HEAP_FRAGMENTATION_MEASUREMENTS.md archive §7D.6)" — Measurement cited to the git archive; "~90%
  interpreter overhead" is inferred from a ~300 us wire-time estimate. · related: PERF.T04, DOC.S04 ·
  [H13]
- **PERF.N040** ASSUME · `SPECIFICATION.md:3995-3998` — "**Per command (T.4, three runs, 2026-09-25)**:
  the 1-byte write took 2,833-3,395 us ... the whole block operation held the bus 18,089-23,148 us" —
  Newest dated figures; spread exceeds the single 21,269 us value quoted above. · related: HW.T16,
  PERF.T04 · [H13]

## SPECIFICATION.md Part F.5.9 — Idle ready() poll cost

- **PERF.N041** ASSUME · `SPECIFICATION.md:4018-4021` — "**14 039 poll rounds** over a ~60 s run with
  one rate, against **839** with the idle rate" — Twin-soak count (single run). · related: PERF.T07 ·
  [H13]
- **PERF.N042** ASSUME · `SPECIFICATION.md:4023-4027` — "**Confirmed on real hardware (2026-09-12, dev
  bench.)** ... **1244 / 1233 poll rounds over 3 s at 2 ms against 60 / 60 at 50 ms**" — Dated bench
  measurement. · related: HW.T16, PERF.T07 · [H13]
- **PERF.N043** ASSUME · `SPECIFICATION.md:4029-4035` — "an idle listener at 2 ms takes **~18-23 %** of
  that task's throughput ... and the inference is withdrawn" — Corroborating measurement only; notes
  heap-state-dependent spread (history narrative of a withdrawn inference). · related: PERF.T07, DOC.T05
  · [H13]

## SPECIFICATION.md Part H.4 — Architecture decisions table

- **PERF.N044** RISK · `SPECIFICATION.md:4354` — "The heaviest real request is `PUT /status {\"ResetErrors\": true}`
  ... this ceiling is a product constraint for its operators" — 15 s ceiling vs a sequential reset whose
  cost grows with readers (BACKLOG 24). · covered-by: PERF.T03 · [H13]

## SPECIFICATION.md Part H.7 — Digital twin integration / connection ceiling

- **PERF.N045** ASSUME · `SPECIFICATION.md:4570-4579` — "**6** — **0 of 2,255** (5 boots, E6′ among
  them) | **~21 %** ..." | Measured table cited to archive §7R; "E6′" undefined label. · related:
  HW.T16, DOC.S04, DOC.S16 · [H13]
- **PERF.N046** ASSUME · `SPECIFICATION.md:4581-4585` — "the board is CPU-bound at ~2.2 requests/s ...
  each open connection ~7.5-8 KB of live heap at peak" — Capacity figures from archive §7R.4. ·
  covered-by: PERF.T02 · [H13]
- **PERF.N047** ASSUME · `SPECIFICATION.md:4597-4598` — "`gc.threshold(32768)` does not move the limit
  ... A browser opens at most 6 connections per host and a page load here needs 2" — Measured/assumed;
  the browser figure is browser-dependent. · related: WEB.T16 · [H13]

## SPECIFICATION.md Part I.1 — MicroPython memory-management facts

- **PERF.N048** ASSUME · `SPECIFICATION.md:4790-4793` — "A real `gc.collect()` pause is ~1ms typically,
  up to ~15-21ms measured on real target hardware under hammer load ... conclusively ruled out as a
  cause of any real watchdog reset" — Dated silicon measurement used to exclude GC from WDT post-mortems
  and in no-yield budgets. · related: PERF.T08, HW.T16 · [H13]

## SPECIFICATION.md Part I.3 — Bounded response assembly

- **PERF.N049** ASSUME · `SPECIFICATION.md:4953-4955` — "**256, not smaller**: at 128 ... the measured
  ceiling does not move (archive §7Q), while the write count doubles" — Measurement cited to the git
  archive. · related: DOC.S04 · [H13]

## SPECIFICATION.md Part J.6 — Deployment parameters

- **PERF.N050** ASSUME · `SPECIFICATION.md:5520-5522` — "a 480-byte transfer spends roughly 1.1 s of
  wall clock ... about 4 % of link capacity" — Measurement at driver defaults (undated). · related:
  UART.T10 · [H13]

## CLAUDE.md

- **PERF.N051** INVAR · `CLAUDE.md:210-212` — "Long-blocking operations must not stall timing-sensitive
  work" — Standing design principle, convention only (`get_long_block_lock()` retired). · covered-by:
  PERF.T08 · [H14]
- **PERF.N052** SETTLED · `CLAUDE.md:213-220` — "Boot latency is not a metric to optimise for its own
  sake (WP6, owner-established requirement)" — Don't trim or reorder the setup batch for speed. The
  target is "does not starve the watchdog". · covered-by: PERF.T06 · [H14]

## BACKLOG.md

- **PERF.N053** ASSUME · `BACKLOG.md:278-284` — "The cost is fixed PER CHUNK (~305ms), not per history
  entry" — Single-sitting silicon figures (2026-09-17; curve 2026-09-25 image `05:21:43Z`), incl. "The
  event loop is not blocked". · related: HW.T16 · [H15]

## Commit messages (chronological)

- **PERF.N054** NOTE(OPEN) · `commit bc98d63` — "The RP2040 time factor is unmeasured and queued as a
  device script" (per-byte CRC yield cost on silicon) — Hardware measurement owed. · status: unknown —
  owner closed A.8 as "don't touch" (23e5443), so likely moot; queue row not verified | - · [H17]
