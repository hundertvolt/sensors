# The findings list (PLAN.md 4.2; started empty in R0, 2026-11-02)

Items that are not admitted as work (4.2): improvements, stronger forms of a correct check, coverage beyond the
done-criteria, observations. Each with its evidence, for the owner.

- (R2 carry, read in R3 lane D1, 2026-11-04) `scripts/run_digital_twin_ci.sh --only` filters the suite's runs alone
  (`:51` to `:115`, `_digital_twin_ci_suite.py:352`); the harness part runs its whole port-53 set (`:133-137`), as
  `--help` states (`:18`). No harness scenario can be singled out through the runner.
- (R2 carry, read in R3 lane D1, 2026-11-04) On a host without `ss` (iproute2, not in `toolchain/versions.toml`'s apt
  list), `run_digital_twin_ci.sh:105` prints "command not found" at both calls; `|| true` keeps the run going and
  nothing reads the holder list, so only that diagnostic is lost.
- R3 falsification 10.4: `sgp40_voc_algorithm_quality.py` / `flash/test_sensor_accuracy.py` red 2 of 15 on the twin
  at gc.threshold(32768) only (twin runner, `r3/m/twin.md`); classed fidelity, the stage dependence unexplained.
- R3 falsification 10.5: `tests/test_asy_fram_allocation_budget.py` lets a 16 B allocation per `_write_chunk()`
  survive both stages (`r3/m/plants.md` `named.fram_alloc`, "not a gap"); its header's "comparable" is contested.
- R3 falsification 10.3: `r3/m/twin.md` row `flash/test_uart_crossover.py` (b) holds one (c) case,
  `test_no_frame_is_lost_while_interrupts_are_off` (dev's 512 B ring, BACKLOG; red on silicon too).
- 11.1 (round 1 prep, agent r1b_): `tests_hardware/README.md`'s hotspot case (b) soak invocation selects (b) alone
  (the soak runner ANDs `-m role_reversal` with its `soak_duration` floor), which fails without the module's earlier
  credential write; round 1 runs the module whole (step 10b). Route: R4 lane C (the README's invocation).
- 11.2 (round 1 prep, agent r1b_): the manual runner's DUT-address prompt cites a README passage that does not exist.
  Route: R4 lane C.
- 11.3 (R4 lane A): the L.6.6 knowledge line "a rule no device TOML can trip is not written" disagrees with the code:
  `bus.i2c-frequency-range` is still checked at `buildgen/validate.py:542`. Not placed. Route: R5 (OR5.a).
- 11.4 (R4 lane B): the owner's 2026-09-28 "do it in this audit" for mypy's `disallow_any_explicit` is not done:
  per-module exemptions remain (pyproject.toml:420, digital_twin/typecheck.ini:38, host_typecheck.ini:46). Route: R5.

## 12. Round 1, day 1 (bench hand-back 2026-11-05 09:27)
- 12.1 **The Unix port crashes (SIGSEGV, exit -11) on the bench Pi4 (arm64, trixie) in 21 twin files and all 65 dev
  scenarios**; the same commit is green on CI (x86). Passing on the Pi: the light twin files (scd30, sgp40, bmp3xx,
  isl29125, driven_clock, http_client, launch, rp2_constants, the unix_port_* ones). Root cause open: a backtrace from
  the Pi is requested. The hardware tiers do not depend on it (each runs with --skip-lower-levels).
- 12.2 tests_scripts/ exceeded its 1200 s limit on all three attempts on the Pi (4a's whole hour), two failures seen
  before the cut. Durations on the Pi requested after 12.1.
- 12.3 4g and 5g stopped at session start: the board held two scratch files (config_HWTEST_DEBUGLEVEL_BACKUP.cfg,
  config_HWTEST_REBOOT.cfg) from an earlier interrupted run; the harness behaved as designed (OR140.a (9)). No test
  ran, no owned write. Rerun with --repair-standard-state (a listed prerequisite write).
- 12.4 Lead's gap: the GC image build during 4a wrote its log under the checkout (hw_round1/logs/build_gc.out), which
  test.sh's checkout-write guard flagged. Builds during a run log outside the checkout.
- 12.5 (bench session, 09:56) The hardware session's start snapshot read GET /sensors by TOML label, the body is keyed
  by firmware name: every --dut-ip step stopped at setup. Fixed: int 1247d18d (bench facts carry `name`).
- 12.1, root cause (bench session): `super().__new__(cls)` in the twin's `UART(io.IOBase)` reaches `py/objtype.c:203`,
  which reads the class object's subobj[0] (its make_new pointer) as an object. Fixed: int f15ae3e7 (`object.__new__`).
  Why x86 survives is not verified (likely the pointer's alignment). A new test pinning it: not added (arm64 only).
- 12.6 (OR10.b prep, 2026-11-05) In the tree stripped of the ISL29125, dev's i2c1 holds only SCD30 + SGP40, and
  `tests/test_digital_twin_held_i2c_line.py`'s runtime held-SCL test fails at both GC stages ("reset reached without a
  catch"), deterministic. No device has that bus pairing in the full tree. Open: (a) a real gap or (c) the stripping;
  to be classified on the full tree with that pairing (a light run), before the comparison closes.
- 12.7 (OR10.b prep) The BMP3xx tree has no address-capable driver left, so two tests_scripts tests start red there
  (`test_every_rule_in_buildgen_has_exactly_one_row`, `test_the_reserved_range_sweep_actually_sees_a_declared_address`);
  they need such a driver by construction. Expected to go green when the module is back.
- 12.6, classified (diagnosis agent f126_, `r4/HANDBACK_F126.md`; lead read `src/asy_base_classes.py:599-614`): class
  (b) for the test, plus a firmware deviation. `_recover_bus` skips a bus rung whenever the bus's one `recoveries`
  count moved since the reader's episode began, whichever rung moved it; so when the reader that ran the clear stops
  failing (the SGP40 does no I2C once the SCD30 publishes no T/RH), the SCD30 skips the controller rung at its 4th
  failure too and no rebuild runs - against F.2's "a bus rung once per bus, whichever reader on it reaches it first".
  Reproduced on the full tree by starting the hold 500 ms later. The test frees SCL only after a rebuild, so it ends in
  the restart budget's reboot (F.2's planned end for an endless hold). On silicon, by F.2's own fact (one more failed
  transfer after a mid-transfer timeout without a re-construction), the inferred cost is one extra failed transfer
  after a hold ends, not a reset (not measured). Fix not made: the owner decides its timing against the final image.
- 12.8 (lead's read of the bench hand-back of 12:12, bench branch 8240e0a1) 4a: the 10 tests_scripts reds are all
  `test_live_twin_ceiling_parser.py`'s Node precondition (node v26 first on the Pi's PATH, `.nvmrc` pins 24), not code;
  the checkout guard's 8 paths are two hardware-tier sessions' evidence (build/archive/pytest/20261105T120455Z and
  T120620Z: errcount and fram-raw at start and end), which test.sh does not start - most likely sessions run by hand in
  the same checkout during 4a (the bench to confirm). 4g (UART crossover: crc16 trains, the interrupts-off ring,
  soft reset during traffic, 6 in all) and 5g (97: 46 "No route to host", the DUT leaving the network mid-run, the
  rest timeouts after it, plus UART_REENTRANT and SGP log entries) wait for the bench session's root causes; any that
  is firmware must land before the final image.
- 12.6, fixed (audit/rung 4aac0f38, 9c365a27, comment 8cd611b2/+1; int 5f763f25): a `rebuilds` counter stepped only by
  `recover()`; the controller rung is skipped only if a rebuild was entered since the reader's episode began. The
  falsification (`r5/FALSIFY_RUNG.md`) held all four claims. Known limit, older than the fix and kept (a fix would add
  a pending state): both counters step before the bus-lock wait, so a reader whose first failure lands while another
  reader's rung is parked on the lock counts that rung as before its episode and may run it once more (one extra
  clear or rebuild and one W15 entry; it needs a lock held across an await that then fails, not a held SCL).
- 12.9 (lead, rung gate rungL_gate on int 5f763f25, 13:35) one twin-suite check red at gc -1 only: Run 10 (isl29125)
  "would_have_triggered_count=None". Its log (build/archive/digital_twin_ci_dev/20261105T131920Z/.../run10_..._isl29125
  .log) holds WATCHDOG_WOULD_TRIGGER, the GC summary, then "interrupted" and no shutdown line. Cause, a race in the twin
  runner (test code, not the image): the run's own --duration end and the host's SIGINT (sent on WATCHDOG_WOULD_TRIGGER)
  coincide after the 12 s hang; the interrupt was raised inside main()'s finally after _print_shutdown_line() had set
  `_shutdown_printed` and printed mem_info() but before the line, so the __main__ handler's call found the flag set and
  printed nothing (digital_twin/run_generic_integration.py:524-529). Not from the rung fix: the hang is a blocking
  sleep, no I2C rung runs. Fix (lead, after a writer slot frees): set the flag after the print; one line still results
  (the parser needs exactly one, preceded by a GC summary).
- 12.10 (bench ROOT_CAUSES_20261105.md, 13:0x) harness items 1-7 and item 10's _seed() row go to unit HARN; item 8, the
  /status "memory allocation failed" (242-257 B) under three concurrent readers at gc -1, to unit MEM (root cause by
  15:15, else the image ships without); item 9 and the third 4a's two other Pi-only reds to read-only unit PIONLY.
- 12.11 (proof run 1 comparison, p10_lead/isl29125/COMPARE.md; two spot-checked by the lead) real in the full tree:
  (a) `_real_reading()` (scripts/_digital_twin_ci_suite.py:742-745) counts a nested group as a value, so an all-null
  RGB/HSB body passes Run 4 vacuously for the real ISL29125 (checked: a dict value is never None); (b) `_HEALTH_FIELD`
  is kept in five identical copies across the twin test files; (c) the comment-cap test counts a line over 120 chars as
  wrapped, which CLAUDE.md's rule does not state; (d) a frozen `math.inf` becomes a bare C `inf` (mpy-cross folds it,
  tools/mpy-tool.py:796 prints `%.16g`) and fails only the firmware build: a Part F.1 fact. Six Part K sentences cover
  the run's (K) entries (K.2, K.3, K.4, K.6, K.9, K.10): fixed after run 2, with run 2's own.
- 12.12 (unit PIONLY, bench/HANDBACK_PIONLY.md) the Pi-only 4a reds are test assumptions, none firmware: (1)
  test_two_concurrent_cancellers_both_return: a >=1 ms gap between the two cancellers' starts (tests/test_asy_uart_driver
  .py:962-963) lets the 1 ms-polling holder ack the first and free the lock, so the second rightly gets False
  (src/asy_uart_driver.py:390); reproduced 93/200 with a 2 ms stall, 0/200 without. (2) only_the_api_writes_the_scd30
  [wozi] (4, 3, 2): _scd30_cycles ticks before the SCD30 setup's idle-count reset (src/asy_scd30_driver.py:429), which
  sits behind two real 100 ms I2C waits; reproduced at 70 ms per tick. (3) test_sensortask.py[dev] attempt 2/3 = a
  240 s per-file timeout on the Pi: the Pi's archived log says hang or slow. Fixes (1)-(2) in the tests, after unit HARN.
- 12.13 (unit MEM, bench/HANDBACK_MEM.md; merged int 95cc5a65) the /status MemoryError, root-caused 14:23 on a 32-bit
  frozen twin at the board's free heap (60 KB, 93 places for a 256 B piece): concurrent /status builds each held a
  whole response (30 pieces) across ~28 awaits, bounded only by the 6-connection ceiling, and written pieces stayed held
  until the response was freed. Fixed at the source: one build at a time (asyncio.Lock) and a draining body generator;
  N=3 11-12/24 failing -> 0/24 x3; both parts needed (lock alone 8/24, drain alone 1-2/24); +213 B bytecode. Open, for
  the last round: (1) N=6 still fails 0-5/48 on the twin (six connections' own cost plus one build); (2) in lock-only
  runs a finished response stayed live past its connection, holder unknown; (3) /status now queues (~1 s per build on
  silicon). The unit installed gcc-multilib on this host (apt) to build the 32-bit twin.
- 12.14 (lead, gate bench1_gate on int 95cc5a65, 15:51) green but for 12 tests_scripts reds, all repo rules the two
  fix units' own checks (touched files only) never ran: the new `_status_lock` had no C.8 lock-table row (9 lock-order
  tests), `_drained` sat out of D.15's member order, one harness comment used decision vocabulary untagged, and three
  per-file S607 exemptions went stale once picotool moved into harness.py. Fixed by the lead (one commit); MicroPython
  tiers 5838/5838 and the twin suite and harness at both stages green; dev imageFreeBytes 60,164. Lesson for briefs: a
  unit touching src/, pyproject.toml or SPECIFICATION.md runs the tests_scripts tier whole, not its touched files.
- 12.15 (lead, 16:06) bench push b7533307 on claude/u35-bench-campaign (fast-forward of b2684c12; tree = int 767f0d79
  outside audit/). The bench's 13:55 silicon heap maps (ROOT_CAUSES 8, update): builds never overlapped (in-flight peak
  1); the sends did, each holding ~8.6 KB of 256 B pieces for ~1.4 s, so the failure is placement under held
  responses on both GC settings (largest free run at failure 12-15 blocks, 12-23 KB free); this matches the drain half
  of 12.13's fix (the lock half is harmless). Open for the last round: Part N's web.serving_demand_budget_b (72,232 B,
  from "about 105,000 B free", measurement owed) exceeds dev's measured idle free heap (57.6-58.2 KB). 4a's 32768 stage
  on the Pi: 4 files over the 240 s per-file timeout on all attempts, the slow-host class; PER_FILE_TIMEOUT_S is an
  environment setting (scripts/test.sh:91), so the bench raises it, no code change.
- 12.16 (proof run 2 comparison, p10_lead/bmp3xx/COMPARE.md; to check in the last round) about the real tree: (a) an
  address-capable driver with no TOML `address` raises KeyError in twin wiring (buildgen/twin_wiring.py:109-110) and
  the collision check skips it (validate.py:152), latent since every TOML sets one; (b) sibling_inside_window() would
  fail for a register-addressed chip flagged as releasing the bus mid-read, latent; (c) the real BMP3xx logs an
  out-of-range reading as READ 11 where the shared READ_RANGE 27 describes that case, and declares no precision on its
  values where the owner record's item 9 asks for one. Run 2 needed three K sentences beyond run 1's six (N1: lint and
  the pyproject/spec rows a red result names; N2: C.11.1's conformance probe in K.6/K.11; N3: the skill reads cited
  Parts step by step). The strip left module traces at SPECIFICATION.md lines 563, 4362, 5536, 7723, 8770-8773, 9347,
  11193, 11809, 11837 of the stripped tree, so run 2 was not fully blind.
- 12.17 (lead, 17:34; bench ROOT_CAUSES 12-13 at dad8d551) final image b7533307 on silicon: /status under 3 readers x
  60 s, three runs: 3 of 156 answered 500 ("allocating 250 bytes", flush()'s join), no reset; improved from 10/32 and
  8/45 on the control image, not clean, so 12.13's fix is partial on silicon (the twin predicted 0). 4b: 72 passed, 14
  failed, none new, the cascade gone. Heap after a full dev build 128,384-128,576 B against the owner's 100,000 B bound
  (2026-10-02: changes only through a new derivation), with 69,312 B already allocated before the build; the readings
  the bound came from were 84,112-87,968 B in all, so about 40 KB is unexplained, likely the same shortfall as 12.15's
  58 KB idle free heap. VOC: one vocalgorithm_process() 41,345 us against the 21,000 us GC term. C stack 4,020 B against
  half the 7,936 B limit (chain fram.get_values_sync). UART_init Failures 0 idle, 4/8/11 under the /status load (the
  control image shows the same resyncs). Decisions sent: no new image now; run 5 on b7533307 on day 2, then the
  remaining 4a twins; the /status fix with the heap root cause, VOC, C stack, UART under load and twin conformance go
  to round 2; HARN2 writes the held-SDA, BMP3xx general-call and FRAM-erase test fixes and round1.sh's flash() (kick
  plus a 9.5-minute /system wait); the board fixture's 16:44:30 skip is diagnosed before any fix (no blind retry);
  PER_FILE_TIMEOUT_S=900 accepted (hang backstop, no product bound).
- 12.18 (lead, 18:1x; MEMDX, S/u35r/bench/HANDBACK_MEMDX.md) correction to 12.17: 84,112 B is SPEC F.5.3's
  largest_block after the build, not an allocation; the bound's readings are 87,760-87,968 B (2026-09-18, image
  23e54438, script c486553a, no setups). Of today's +40.6 KB: +8.1 KB the script's own growth (U26 includes, rendered
  facts, the map dump), +20.2 KB the setups the script now runs (since U20; production pays them), about +6.8 KB
  imports and +5.6 KB build growth (inferred, flat since U17). Largest single contributor: 33974760 (U35, 2026-11-05
  07:24) raised dev's responder rx_ring 512 -> 8192 B for test_uart_crossover's precheck, which demands a continuous
  sender over a 400 ms erase; the driver allocates 2 x the ring for alignment (asy_uart_driver.py:744), so 16,384 B,
  +15,360 B, in both bench images. Part N's con.uart_rx_ring asks only for what the stop-and-wait peer sends during one
  flush (one frame), which 512 B holds. Production's idle free heap about 59.5-60.1 KB (inferred), below Part N's
  68,790 B demand. The "finished response stays live" of 12.13 is a stale child_last word in MicroPython's pairing heap
  pinning the last finished connection's task (~1 KB, not the body, with the drain): upstream behaviour, class (c).
  Proposed last-round /status design: one built piece list shared by every reader in flight, rebuilt only at zero
  readers. Put to the owner 18:1x: revert the ring to 512 B in a new image before run 5 (A, recommended) or in the last
  round (B).
- 12.19 (lead, 18:1x) proof formal ends: ISL tree e869c46 green in every step (twin suite and harness at -1 and 32768,
  collect 195/223), dev imageFreeBytes 72,660; BMP tree 139eec9 green except tests_scripts 1 of 6732
  (test_every_rule_in_buildgen_has_exactly_one_row: names.logger-collision has no row), red in the run's baseline g0
  before its first change: a strip artefact, class (S); dev imageFreeBytes 62,580 (baseline 71,048).
- 12.20 (lead, 18:1x; HARN2, S/u35r/bench/HANDBACK_HARN2.md) merged into int as e918200a (+f402c0f2, a line-length
  fix): held SDA probes with one pointer-write byte on the controller path (rp2 bit-bangs a zero-length write and
  reads a held SDA as an ACK; a read could clear BMP3xx ERR_REG); the BMP3xx general-call script reads "before" after
  one forced conversion (sec 3.3.2); the FRAM erase script counts its 16 s from the reset's arm. round1.sh (copy):
  flash() kicks after a successful load, the /system reads after a flash wait 720 s. The board fixture's 16:44:30 skip
  is not explained by the code: is_reachable()'s own Ctrl-C ends main.py (code 21) and the armed watchdog resets the
  board 6-8 s later at every real session start, but the probe takes 0.4 s; the bench's reset reason decides it. For
  the last round, class (A) harness: session_start_evidence() saves /status after that probe has already ended main.py,
  so the pre-session state it is meant to keep is gone, and every session start costs one watchdog reset.
- 12.21 (lead, 19:1x) owner 19:11 "Option A": int 4e05f80e reverts 33974760 (dev's uart1 rx_ring 8192 -> 512 B) and
  removes test_uart_crossover's ring precheck (a continuous sender over a 400 ms erase, beyond J.6's stop-and-wait
  floor, which the build checks); J.6, the memory section and the BACKLOG bench item updated. At 512 B the ring's bound
  is 44,444 us, so the device script's 45 ms window lies 0.6 ms past it (about 6 bytes): it should report an overrun;
  if it does not on silicon, look there first. Gate running (ring_gate); then a new image for the bench: day 2 starts
  with step 3, 4b and the /status load check, then run 5.
- 12.22 (lead, 20:11) ring gate on int 4e05f80e green in every step (rebuild, lint, mypy x3, unit tier and
  tests_scripts at -1 and 32768 with no allocation-failure line, dev twin suite and harness at both stages, npm, dev
  firmware), dev imageFreeBytes 60,172. Bench push 3: bd67db94 (fast-forward of a4ed871a): the image for day 2.
- 12.23 (lead, 20:20; PK, S/u35r/r4/HANDBACK_PK.md) merged into int 84a76ae8 (aff1af5c + e32e11c9, a wrap): Part K
  K.2, K.3 item 1, K.4, K.5, K.6 (head and twin paragraph), K.9, K.10, K.11 and the skill's step 1 carry the proof
  runs' sentences (net +19 lines in Part K and the skill); F.1 states the frozen math.inf/math.nan build failure with
  its v1.29.0 citations. Not written: CLAUDE.md's 120-character clause is already there (CLAUDE.md:534-536, since
  656fc82f), so that comparison finding was mistaken; C.9's one-Timer-per-starter rule has no basis in Part F and no
  product dependant, only a test count (tests/_sensortask_scenarios.py:1524-1530): open for the last round as (c), the
  rule or the count. tests_scripts whole 6,887 passed at aff1af5c.
- 12.24 (lead, 21:23; bench item 15, b82284ec) The final 4a on b7533307's tree (8 KB ring): GC stage red on one file,
  scenarios[dev] failed_config_snapshot_is_sent_as_unavailable ("SCD30: 1 GET(s) sent the marker and the verify took
  0 of 2 faults (38.6s)"), Pi load about 8; passes 3 of 3 alone. Open, no root cause: diagnose on this host, with the
  bench's log for the file. The 512 B ring itself: unit tier both stages and dev twin suite+harness both stages green
  here (S/u35/lead/ring_gate_*.out) and in snapshot 40's CI; no Pi run yet (b6a7bc1e already carried 8,192 B).
- 12.25 (lead, 21:23) ROWS row 8 was stale: the close-out bullet ("Closing a piece of work", OR51.a (2)/(4) with the
  owner's 2026-09-26 words) has been in CLAUDE.md since f9b907f1 (R4's rewrite). R4's report named it open in error;
  corrected to the owner.
- 12.26 (lead, 03:10 2026-11-06; proof run 3, S/p10_lead/sgp40/COMPARE.md) The comparison's four "record vs real"
  points are prep errors in S/p10/sgp40/BRIEF.md, not product deviations, each checked in the real tree (84a76ae8):
  a failed read keeps the last good sample (C.4.2's staleness rule, owner 2026-09-12/09-29; SPEC:3330-3334); a task
  restart restores the FRAM backup as a boot does (SPEC:443-445); BackupMaxAge 0 accepts any age, a future date
  expiring only under a nonzero one (SPEC:356, driver :525); an unsynced end of the NTP wait restores a dated backup
  with no warning, as legacy (driver :517-533; no owner word for a warning). The run's boot-warning question (log 19)
  is moot: the real module logs the same SGP_NO_BACKUP on a blank chunk and the real twin suite expects it.
  Procedure lesson: the build followed a record point that contradicts a standing owner rule without noticing.
- 12.27 (lead, 03:10) Real-tree doc/code mismatch: SPEC M.3 (11740) gives the heater-off wait as "2 ms
  (`_HEATER_OFF_MAX_MS` + 1)", src/asy_sgp40_driver.py:754 sleeps `_HEATER_OFF_MAX_MS` = 1 ms. Last round: make one
  match the other (sleep_ms(1) can end under 1 ms on a tick boundary, so the doc's +1 reads as the intent).
- 12.28 (lead, 03:10) Real-tree test fragility (compare (C) 11): tests/test_digital_twin_hot_replug.py:199 reads a
  reader's sources by getattr on `_temperature`/`_humidity`, a silent no-op for any other attribute name. Goes to
  the Part K fix unit (fail loudly, naming the attributes).
- 12.29 (lead, 03:58 2026-11-06) Snapshot 41's CI (run 42157783475, job 127696270505): "Unit tests (shipped
  gc.threshold)" red on scenarios[arzi] a_hung_shutdown_step_is_ended_by_the_watchdog, twin 7 ignored its SIGINT and
  was killed (exit -9, 114.7 s); the rest green. The push touched only SPECIFICATION.md and the hot-replug test; the
  same symptom as U28's on dev at 32768 (U28_close/lead/hang/handback.md, undetermined). Not re-run: root-cause unit
  sig launched (S/u35r/r4/BRIEF_SIG.md). The CI log's instrument output is not fetchable from this session (log host
  outside the allowlist, the tool returns the tail only). One PR comment posted (#107).
- 12.30 (lead, 05:06) Unit sig (S/u35r/r4/HANDBACK_SIG.md): not reproduced in 1,041 S5reset SIGINT shutdowns at 32768
  (four heavy runs up to load ~14); twin 7 is S5reset, as U28's dev case was. Static audit again finds no absorber.
  Since d0eb67f3 (2026-11-04, stop file removed) SIGINT ends every scenario twin again: 1 red in 8 shipped-gc runs.
  The deciding evidence is the three "DIAG: arzi twin 7:" lines in job 127696270505's console (scenarios[arzi]
  block); put to the owner to paste. Instrument gaps held until read: the 20-line tail can cut a traceback's top;
  the unit-test jobs upload no twin logs. In-band stop only if the lines show the signal held or never raised.
- 12.31 (lead, 05:27) The DIAG lines (owner's log archive; excerpt S/u35r/r4/ci41_diag_excerpt.txt): SIGINT "blocked in
  0 of 1 threads, caught"; second SIGINT "a clean exit: the first was raised and absorbed". The tail shows the
  KeyboardInterrupt raised at src/asy_scd30_driver.py:512 (_store_scd, inside `async with self._data_lock:`) and an
  unretrieved task exception from the same line, "AttributeError: 'NoneType' object has no attribute '__aexit__'":
  the async-with exit path replaced the interrupt, killing only SCD30's read task. Points at MicroPython's async-with
  exception handling under an asynchronously raised exception; product relevance (a thrown CancelledError) open.
- 12.32 (lead, 05:41) Unit sig's cause verified: a MicroPython defect (v1.29.0, master unchanged). At an async-with
  body's normal end the emitter writes LOAD_CONST None; ROT_TWO; JUMP (py/emitbc.c:681-683, read by the lead); the
  JUMP's pending-exception check raises a pending KeyboardInterrupt while None sits in the context manager's slot, so
  the finally path's load of __aexit__ raises AttributeError and the interrupt is lost. Lead rerun (a copy without the
  later tail branch, S/u35/lead/ftmp/sigrepro/): 947/3000 lost at 32768, 522/3000 at -1, cancel 3000/3000 clean,
  matching sig's 974/542. The left S/sig/repro_aexit.py carries the tail branch in both modes (1-4/3000): it is the
  control only. Cancellation and wait_for timeouts are not exposed (thrown at an await). Plain KeyboardInterrupts left
  the lock held in about a third of cycles (raised inside acquire/release): a second SIGINT-only hazard. Remedy taken:
  the launcher ends twins through the runner's existing --stop-file again (unit stop, S/u35r/r4/BRIEF_STOP.md), no
  SIGINT fallback; SIGINT stays where a run tests it on purpose. No MicroPython patch: the override mechanism cannot
  carry a source change and a patch would change the firmware's frozen bytecode. Upstream report drafted for the
  owner. The two held instrument gaps (20-line tail, no twin logs from unit-test jobs) are dropped: not needed.
- 12.33 (lead, 06:2x) 12.27 resolved: the spec is right, the code is wrong. SGP40 datasheet Table 8: heater-off 1 ms
  max. extmod/asyncio/core.py:57 sets the wake at ticks_add(ticks(), t) on a 1 ms tick, so sleep_ms(1) can end well
  under 1 ms; U15 waited _HEATER_OFF_MAX_MS + 1 for that reason, as SPEC M.3:11750 states. 1206e862 (2026-11-03,
  "back to pre-audit forms") dropped the + 1 as "the datasheet's 1 ms", but neither legacy nor pre-audit 25caf528 has a
  heater-off at all: no pre-audit form and no owner ruling behind it. Fix for R5: restore the + 1 and its comment
  (src/asy_sgp40_driver.py:754), one line; device effect: a command after heater-off could reach a still-busy chip.
- 12.34 (lead, 06:4x) Sweep swp (owner "B", 06:13; S/u35r/r5/SWEEP.md, 10 findings). Lead checks: 1 confirmed
  (flash/test_task_supervisor.py:13 claims twin Run 5, which is an SGP40 bounded read fault recovered in place, not a
  task restart). 2 rejected: the device script's 0.9 s feed runs on the same asyncio loop, so a console stall stops it
  too and hides nothing; the isolated script starts no product feeder and escalate/hold run 40 x 0.9 s > the 8.3 s
  watchdog, so dropping the feed would make the test fail always. At DebugLevel 0 nothing prints after HOLD, which is
  what the test proves on silicon (A.5). Plan: 1 fixed; 5 and 7 recorded (E.6.6 row lines, one BACKLOG line); 3, 4, 6, 8
  as silicon tests in R5 for the bench campaign, else E.6.6 rows; 9 and 10 to the owner after the seven questions.
- 12.35 (lead, 07:3x) U14 precompile (S/u35r/r5/U14_QUESTIONS.md, U14_TAGS.tsv): 466 tagged lines = 269 choices,
  197 records (each with its replacing citation); 15 realms in 11 questions. Lead check: counts match the TSV; Q4's
  "held SDA during the full system's boot" is already decided (owner 06:43, option A; unit r5c builds it), so Q4 asks
  only the other three scripts; Q6's scan-budget line matches the sweep's finding 7. Asked one at a time from 07:3x.
- 12.36 (lead, 07:23) Unit stop merged (e53ca758 + lead 21853aa7, the build-environment list's twin entry; merge
  2a1deb42); snapshot 42 3e1259ee pushed on ba581e5c (next PARENT). Diff read: net -55 code/test lines, no SIGINT
  fallback, SIGINT only in Run 12. Left for r5d: tests_js/_twin_process.js still stops live-tier twins by SIGINT (a
  lost interrupt there costs the SIGKILL bound and the flush, never a red test).
- 12.37 (lead, 07:5x) Bench day 2 (07:05 relay): /status load 0 of 331 failed, lowest MemFree 21,280 B; 4b 11 failed,
  75 passed, 1 teardown error. Three test faults read from code (crc16 frame-loss stream outside the 512 B ring's
  sizing; largest-block exact equality; closing_reset leaving the board booting, so 4b's session-end checks never ran):
  unit bfix (S/u35r/r5/BRIEF_BFIX.md). r5d merged (8ea29293). The three logs (c8887b35): dev's 32768 failure is 12.24's
  config-snapshot scenario, not the SIGINT defect; arzi's feed gaps 6795 ms (run 4, at boot) and 6290 ms (run 11):
  unit dx4a (S/u35r/r5/BRIEF_DX4A.md).
- 12.38 (lead, 07:5x) Snapshot 42 3e1259ee: CI green, run 42180510001, 34 of 34 jobs success, "Unit tests (shipped
  gc.threshold)" included (the push run 42180502365 cancelled itself by concurrency, as before). R4 closed. Next
  PARENT 3e1259ee.
- 12.39 (lead, 08:0x) r5c (ba671e7a) merged into int 54a769e1. Diff read: +376/-89 over 15 files; the held-SDA hold
  code shared (_shared/held_sda.py); the ResetErrors bench test re-tries the reboot only when its ResetErrors reached a
  closed listener (a window the server closes 0-2 s after Valid), any answer but Failed fails at once, the retries noted
  as recoveries: a precondition, not a re-run of a check. Class (c) from r5c: the harness hard-reset test expects 2,
  the product records RR_INTERRUPTED 21 after mpremote's Ctrl-C: to r5b, item 7. r5b launched (S/u35r/r5/BRIEF_R5B.md).
- 12.40 (lead, 08:1x) bfix (227b4ad8) merged into int ee162e86. Diff read: +36/-11 over 3 files. Frame loss: the
  stream is paced outside the interrupts-off window from the mode's own timed check_from() (about 27 ms a frame under
  CRC16, 5 ms with none) and runs at line rate across the window only; _drain ends only on a quiet line, not on the
  empty ring an overrun leaves. Over-cap: after >= before (largest_block() collects first). Session end: the wait went
  before the strict read in conftest.py, not into closing_reset, because flash/conftest.py's leave_board_serving
  hard-resets again between the two (agent's decision, sound). The dut_ip probe is now written twice in conftest.py;
  left as is (two copies). Latent, not run on either bench day (wear gate): the config_write state streams 400 ms at
  line rate (about 4.6 KB) with no reader into the 512 B ring, so it should fail by the same arithmetic. Whether a
  continuous stream across a real flush still belongs beside config_write_link under the 512 B sizing: last round.
- 12.41 (lead, 08:1x) dx4a (S/u35r/r5/DX4A.md). 12.24 root-caused: SCD30's start-up reads 0x5403 3.8-4.1 s after
  BOOT_TASKS (after BOOT_DONE), behind the soft reset's fixed 2.5 s wait, so on a loaded host its read task took the
  second armed fault before the second GET; product correct. Fixed by lead commit 4e7e8cab: the fault aims at 0x0010,
  which only the snapshot reads after boot (dx4a probe: 10 of 10 under 0-9 busy loops). arzi's 6795/6290 ms gaps:
  whole-process stalls of the loaded Pi (heap unchanged across a 5.2 s hole; 38 local logs peak at 2.0-2.1 s; silicon
  longest unyielded stretch 41 ms); the 6,000 ms check worked; no fix; rerun on an idle host. Gate bfixG running.
- 12.42 (lead, 08:3x) Gate bfixG on int (after bfix + the scenario fix): rebuild, lint, mypy x3 clean; tests_scripts
  6894 passed, 1 failed (my own comment block: 4 lines at the 120-col count), fixed and amended (8f758b6f), cap test
  657 passed; dev harness both stages PASS, but on this host the changed scenario is on the shared-port-53 side
  (scripts/test.sh runs it), so it ran alone with --only: pass at 32768 and -1. Bench head 549fe55a carries the
  bench's own harness fix (62.5 ms USB-gone poll in kick_after_reset) that int lacked (db6442b5 and bd67db94 were
  already in int): taken into int as b2524fd0, so the bench push does not revert it. Check harnC queued behind r5b's
  heavy run.
- 12.43 (lead, 08:41) harnC on int b2524fd0: lint, host mypy clean, the 4 files calling the changed harness code 745
  passed. Bench push a0503ca5 (fast-forward on 549fe55a, [skip ci]; audit/ unchanged, harness.py kept). Relay
  S/u35/lead/relay_bench_d2b.txt sent to the owner.
- 12.44 (lead, 09:1x) r5b (96d7d003) merged into int c1a84764 (clean). Diff read: +59/-84 over 23 files; the
  containment test shorter (+11/-14), ids 59 -> 122 (33 files, 22 cells, 67 scenarios; 72 covered, 50 excused);
  declarations narrowed to what each test does; harness hard reset now expects RR_INTERRUPTED 21 (renamed). Left (c):
  four places still say a harness hard reset reads 2 (harness.py:924-927, SPEC :1124 and :7015-7016,
  error_catalog.json:173): to the U14 apply unit. Owner Q3 direction (09:08): the webserver's add_status_command hook
  goes; the link module brings its own route (U14_ANSWERS.md). Gate r5bG running.
- 12.45 (lead, 09:1x) PR #111 (bench branch): the bench's own merge commit d3f10239 (no [skip ci]) ran CI, run
  42192434611; "Unit tests (shipped gc.threshold)" failed in setup_toolchain's apt download (azure.archive.ubuntu.com
  stalled, 3 x 150 s), before any test body: an install failure. Outside audit/ the branch equals a0503ca5; head
  4a2176ba is [skip ci]. One rerun of the failed job owed once the run completes (refused while it runs, 403).
- 12.46 (lead, 09:2x) Gate r5bG on int c1a84764: rebuild, lint, mypy x3 clean, tests_scripts 6896 passed. Bench push 2
  b969964f (fast-forward on 4a2176ba, [skip ci], audit/ and harness.py unchanged). Owner Q4 asked what "all tests"
  means: answered (8 writable at about 2 % of the week vs 0.8 % for A; #5 waits on the ring question; recommended B).
- 12.47 (lead, 09:3x) Bench relay 09:20 (owner_rulings 09:23:41). Flash reruns on d3f10239: 9/9 passed, session-end
  checks ran. 3 flash cycles today (bench's own 08:52 flash after a failed pull). 549fe55a already in int (12.42).
  Item 1 (test_reset_reasons, 15 failures, no kick after a provoked reset): lead commit dcb289b1, one helper that
  runs, kicks, parses; checks lint, host mypy, 26 guard files 904 passed, text guards 744; bench push 3 1f844c03.
  Item 4's question: an unknown sensor answers "Invalid" (SPEC A.8 :1144-1147), the test was stale: lead commit
  (test_network_resilience.py, 1 line), checked, for the next push. Open: items 2 (teardown W65/W35/W81), 3 (loop
  lag 967 ms vs 925 ms, IncompleteRead x7, ConnectionResetError, packet-fault REST, WEBSERVER W60) and the rest of 4:
  need a diagnosis unit; the week near the 80 % stop (estimate): put to the owner.
- 12.48 (lead, 10:2x) Owner Q4 (10:20:31): all board gap tests but #9. Unit gtest launched (S/u35r/r5/BRIEF_GTEST.md,
  int c4f56186, due 13:30 so the bench runs them today, about 1.5 %). Correction to my 09:19 answer: #5 does not wait
  on the ring question - on the bench tier the link runs its normal transactions, which the 512 B ring is sized for.
- 12.49 (lead, 10:2x) Owner go for the diagnosis (10:22:55). Unit dx5 launched (S/u35r/r5/BRIEF_DX5.md, read-only,
  due 12:30, about 0.8 %): bench items 2-4 from HANDBACK.md at 2745af2f; item 3 first.

## 12.50 Bench idle from 09:54 to 10:45 UTC (lead's miss), and the 09:18/09:35 bench results
The bench's 09:54 hand-back (c1f8076b) ended its reruns; no relay followed, so day 2's remaining range (9, 10a, 10m)
did not start. Owner asked at 10:36:40. Relay `S/u35/lead/relay_bench_d2f.txt`: run 9 10m, then the twin suites, the
gap tests at ~14:30-15:00, then run 11 16b. The 09:35 rerun: kick fix works; new reds a-f listed in the relay, to the
diagnosis (owner's budget call for adding them to the running unit).

## 12.51 Bench 10:41 relay answered (relay d2g); Q5 ruled C; dx5 items 2-4 in
Bench: twins arzi/schlafzi PASS (feed gaps ~2.2 s), dev ends ~10:59, then run 9 10m (~13:00), run 11 to ~15:05,
then the gap tests. Wear line given: the 420/422 is sheet maxima per started step; the gap tests may pass 422, run
them (owner chose them; prerequisite writes ungated). Lag probe (/status vs /measurements) asked at 13:00. Pi clock
looks ~5 min behind. dx5 hand-back 1 (S/u35r/r5/DX5.md): item 3 is two mechanisms (RST on unread close; W49 reclaim
from multi-second loop stalls, cause (d)); SGP40 W65 after an FRAM erase vs the owner's expected-situation rule: an
owner decision; mixed-body 413 RST: (b) or a bounded drain in `_serve()` (owner's call). dx5 resumed on b-f.

## 12.52 Correction to 12.51: the Pi's clock is right; the lead's relay stamps ran ahead
The bench's timedatectl: synchronized, offset +1.6 ms. The lead stamped relays d2f ("10:45") and d2g ("10:57") with
expected times, not `date -u`; both were ahead of the real send. From now on a relay's stamp is a `date -u` reading.
Bench's NTP E71 question (dx5 item 2) needs test_heap_at_peak to save its script output: goes to the test-fix unit.

## 12.53 dx5 complete (DX5.md, 35 lines); test-fix unit tfix launched (owner "A", 11:05:17)
tfix (BRIEF_TFIX.md, due 13:45): every (b) item, the (c) redirect, three (d) instrumentation changes (loop-lag time,
probe failure reasons, test_heap_at_peak's script output kept). Out, for the owner one at a time: SGP40 W65 after an
erase vs the expected-situation rule; the 413 body cut (test fix or server drain); the product finding (overflow
escaping while SYSTEM's FRAM lock is held reads as reset 2; proposed record in `_log_dead_task()`). "First 200 after
the RTC was set": the bench checks boot-log.txt's line order first.

## 12.54 Bench boot-log read (relay stamped 11:14 by the Pi): items e and 7 to tfix; a product question; the clock
Item e: "WLAN connection established" is `pr.one` (level 3, "once") in `_on_sta_connected()`
(src/asy_wifi_service.py:576-577), called on every 5 s `_connect_loop()` pass while connected (:487-489), with the
diagnostics block: printed ~every 5.55 s. Test side: tfix detects a real reconnect instead. Product question for the
owner (console only, no FRAM): print only on the transition into STA_ESTABLISHED. Item 7 (first 200 vs RTC set) to
tfix: the test races a 0.27 s gap with a 0.5 s poller; make it race-free or leave it, stated.
Clock: the container's date -u matched pypi.org's HTTPS Date header to the second (11:09:47); the bench's "11:14 by
date -u" arrived at 11:09 real. 12.52's "the Pi is right" is withdrawn: the lead's two stamps did run ahead (estimates),
and the Pi's latest stamp runs ~5 min ahead of real UTC. Bench to compare its date -u with an HTTPS Date header.

## 12.55 Diagnosis decision 1 ruled (owner 11:12:17): W65 stays for every invalid backup read, erase and first boot included
Code check: `_run_restore()` sets `_voc_init = 0` on an invalid read (src/asy_sgp40_driver.py:511-514) and returns
False, so the "Retrying initialization" path (:381-384) does not re-arm it: one W65 per boot or task start, matching
the owner's "record an error once". Apply unit: SPECIFICATION.md :444-445 / :3664 state the exception with the ruling.
Tests declare W65 where they provoke an erase or an early reset (tfix already does).

## 12.56 Diagnosis decision 2 ruled (owner 11:16:57): A, test fix; no drain in `_serve()`
A reset after the 413 status line counts as answered 413 (test_network_resilience.py ~1246-1250). Sent to tfix.

## 12.57 Clock settled: both clocks agree with pypi.org's Date header within 1 s; every disputed stamp was an estimate
The lead's d2f/d2g stamps and the bench's "10:56", "11:06" and "11:14" stamps were estimates labelled as readings.
Both sides now stamp from an actual `date -u`. 12.51, 12.52 and 12.54's clock lines are superseded by this entry.
Bench run 9 10m started 11:04:12 (real reading).

## 12.58 gtest reviewed and merged into int (b75928a6, merge of 63a0e4cf; +827/-32, 13 files); gate after tfix
Read: the flash tests (items 2-4, 8), items 1, 5, 7 in full, item 6 and SPEC E.6.6 rows by diff; no audit IDs outside
audit/. Accepted as stated: item 4 (stepped clock) cannot run under --twin (run_device_script.py installs no wall clock;
twin counterpart tests/test_digital_twin_clock_jump.py); not in any gate (the twin record's reasons file takes it).
Item 5 toggles GMTOffset default <-> default+60 s, one write a run, never restored: outside the standard state's fields
(DebugLevel, FRAM WP, scratch files, SCD30), so no check trips; local time may read 1 min off between runs. Item 7's
floor (10 of 20 per reader) is the twin's, untried on silicon. Two lines outside the write list (marker exemption,
stub), both guard-required. One gate for gtest + tfix together after tfix's merge; then the bench push.

## 12.59 tfix handed back (f9e62683, +178/-77, 14 files under tests_hardware/); reviewed; one follow-up sent
Read the network-resilience and boot-order diffs and every "not weaker" line. One check reshaped, flagged to the
owner: bus trigger spacing now needs median >= planned - 20 ms and min >= planned - 20 - 90 ms (one wake's loop lag;
host-side stamps), was min >= planned - 20 ms; board-side stamps need src/. Follow-up (lead's choice): each erasing
test (three erase tests, the incomplete-command test) waits for the SGP40's first backup before it ends, so no later
test meets W65 it does not provoke; due 12:45. Apply unit note: the stack test no longer exercises an overflow that
escapes its task unrecorded; once decision 3 (A) is in src/, add an escape mode that expects 20 on silicon.

## 12.60 Gate on int 03793ef9 (gtest + tfix) green; flash-reset harness gap put to the owner
rebuild 0, lint 0, mypy 282/312/59 clean, tests_scripts 6899 passed 6 skipped (9:04), collect-only 215/248 (33 wear-
deselected) and 244/248 with --allow-persistence-write. heavy.lock released. Bench relay 12:00:52: flash-tier and
session resets do no kick, so the board falls to hotspot (step 9 and damaged-config teardown timeouts; soak bench half
never ran in 10a/10m; the 10m headroom soak ran mostly in hotspot; one reset ~30 s after boot, reason overwritten).
Asked the owner for a small harness unit (A) before today's push.

## 12.61 Q7's serving memory is at a real margin; Q6's split corrected (serving demand is "bound")
Owner asked (12:24:10) whether Q7 sits near critical margins. From 12.15/12.18 and HANDBACK_MEMDX.md (silicon, images
with the 8 KB responder ring): idle free heap ~59.5-60.1 KB, largest free run ~2 KB; Part N's web.serving_demand_budget_b
(72,232 B) derives from a September 105 KB reading without setups, stale; dev's demand at 6 connections 68,790 B
(Oct; /status has grown since, 7,318 B on the bench today vs 6,993 B). Less the 32 KB reserve ~27 KB = ~2.4
connections; silicon: 3 /status readers -> 8-14/46 answered 500, no reset. The ring revert (owner A, 11-05; dev.toml
rx_ring 512 at int) adds back ~15.4 KB in d3f10239: ~3.7 connections, unmeasured. Q6 split: serving demand moves from
attention to bound (a shortfall is a caught MemoryError under ordinary load, a defect by CLAUDE.md's rule). Bench:
heap probe baseline on d3f10239 after the lag probe (the bound measurement already ruled at Q6).

## 12.62 Correction: U14 Q8's "ISL29125 config compared every read cycle" is wrong
src/asy_isl29125_driver.py: each cycle (SampleInterval default 1 s) reads STATUS (1 B) then the data burst (6 B,
_DATA_BURST_LEN :87); BOUTF in STATUS catches a brownout every cycle and re-applies the config. The 3-byte CONFIG1-3
snapshot (_CONFIG_BURST_LEN :88, get_config_snapshot :1194) is read only after a failed write
(_verify_after_failed_write :877, a no-op while the write-failure count is unchanged) and on each REST config read
(_read_sensor_dict :736). A corrupted config byte with no failed write and no brownout stays until the next REST read.
Addendum (lead, 12:5x): the question text came from SPECIFICATION.md:11543-11545 ("The shadow-vs-chip comparison runs
every read cycle ... (agent, 2026-10-06)"), which the code does not do (`_verify_after_failed_write` :881-883 returns
while the write-failure count is unchanged). Owner 12:45:47 "ISL sensor: keep as is." keeps the code; the apply unit
rewrites that paragraph to the code (and U14_TAGS.tsv:237's wording).

## 12.63 Bench soak mid (12:06-12:37, d3f10239): hammer's UART_init/UART_resp E81 UART_NO_ACK, 2 each
`test_real_hardware_survives_extended_max_speed_hammer_load...` (tests_hardware/bench/test_memory_stress_bench.py:91)
hammers every JSON GET route, /status included (:33), at the connection ceiling; both link ends logged E81 inside the
600 s, no reboot, no task end; short's 60 s hammer none. Same load class as day 1's 3-reader /status probe, which saw
stalls to 2,625 ms with UART "no ACK" lines (DX5.md:5; ROOT_CAUSES_20261105.md §14); the ACK wait is 1,000 ms. Reading:
the open loop-stall question, not a second defect. Held: no hammer rerun until the lag probe (DX5.md:6) names the stall's
source. Margins: watchdog 8.4 s vs worst stall seen 2.6 s; UART ACK 1 s crossed (dev's bench link only). FRAM counters
now count from ~12:37 (the tests clear them; saved file named in the 12:47:13 relay record).

## 12.64 hfix review (e08e76bc + dec0e314, merged into int as 964ee399)
Lead's review: the brief's "reset, then kick" had made a second kick order beside kick_then_reset() (~20 callers, the
CLI); follow-up: reset_board() delegates to it. The lead's second premise was wrong: standard_state already resolves
dut_ip at session start (conftest.py:485), so the stopped main.py after the flash half's sgp40 cadence soak predates
hfix, and is the likelier cause of day 2's "bench half never ran" (3 ERRORs in board_image) than the stale AP entry.
Fixed: every flash soak_duration test ends on reset_board(). The SCD30 clock-stretch soak only tails the log (main.py
keeps running), so its closing reset is redundant; kept as the uniform rule the new check pins (one reset, ~30 s).
The lead told the owner at 12:5x that hfix "would have broken" the combined run; corrected in the next message.

## 12.65 Bench 017f5f5d (ROOT_CAUSES_20261105.md section 18): the stall is in serving /status; the idle baseline
Lag probe, 3 readers 60 s, 32768: /status max 2,481 ms (16 lags >= 925 ms), a ~2.4 s stall about every 3.5 s, UART
"no ACK" pairs inside it; /measurements max 318 ms. Three CFGMGR_NTP "Reading config data into list" lines 0.7-0.85 s
apart in each stall (a dict lookup, asy_config_manager.py:363-366, so the time goes elsewhere): about 0.8 s of blocked
loop per /status request, serialized. Class (a), source not traced. Extrapolated, unmeasured: 6 concurrent /status
readers (max_connections 6) ~4.8 s, over half the 8.4 s watchdog. 12.63's E81 is this. Lead reads the path next.
Baseline idle, STA up, after gc.collect(), 32768, under mpremote run wrappers: free 72,288 / 73,072 B, used 115,616 /
114,832 B (heap ~187.9 KB), max free block 50,592 / 52,416 B. The "largest free run ~2 KB" fact was heapmap.py's
undercount (fixed by the bench). SYSTEM E42/E25 in the saved file: provoked by test_a_c_stack_exhaustion_is_attributed.
The 10m reboot: 1 of 2, ResetReason lost to the harness's own read (21); hfix now reads it at once.

## 12.66 Attention values (apa, ATTN.md) and the radio re-init drop (lead, 2026-11-06 13:48 UTC)
Of the 19 attention rows: 4 hold (plateau cycles, C-stack window, FRAM hold 25,000 us, scenarios timeout), 14 have no record, and 1 is
adjusted: web.serving_demand_budget_b reads ~40,304 B against today's free heap, which puts it in the owner's Q7 heap account. Rows 11 and 18 had their basis and margin folded in via apr.
Radio re-init (bench, 2 of 2 runs, USB lost after recover_returned=true): the script starves its own 8 s watchdog. Nothing feeds it from arm() through the
first connect, the 4 s of settles and the second connect poll. Class (b) test defect, no product sign: production's supervisor feeds during these awaits. Fix sent to apf; confirmed by the bench rerun.

## 12.67 Bench 40707982 (runner, 14:14 UTC): step 9 green, FRAM at 8 MHz clean, a refused pre-session read
Step 9 (crc16 hazards) passed on df8e640c's harness in 123 s, with no teardown error. Step 11 (FRAM at 8 MHz, 13:10-13:20): rdid, read256 and write1
ran 274,287 operations each with 0 OSErrors and 0 bad reads, worst 7.3 / 7.6 / 9.5 ms. The pre-session /status read was refused 9 s after a 200:
untraced, and nothing failed on it. It goes to the last round's session-start item. The bench branch now carries the runner's merge of ec5d656e, so the next bench push fast-forwards from 40707982.

## 12.68 Bench soak selection (runner's 14:11 note): W33 at the bench half's opening, ResetReason 2, W22, the stopped slice not serving
Soak mid: 4 tests passed, 0 of 854 requests failed over 600 s, sgp40 cadence 602 cycles with 0 lost. The bench half now starts after the flash half: proved.
W33 (SGP_RESTORED_NO_TS) charged to http_soak by no_unprovoked_log_entry: the flash half's sgp40 script writes undated backups (W35) into production's
chunk (CLAUDE.md's FRAM caveat), and the next boot restores one after the opening read. Class (b) harness race: the opening read must wait for the boot's own logging. It goes to
the last round's session-start item, with no tolerance added. ResetReason 2 at the boot after a flash-tier session vs 21 after resetting a running board: apf's
four-place wording corrected to the readings; the bench pins the mechanism after items 4-5. W22 = CFG_FILE_UNREADABLE, 1 each in 7 modules. That fits one
full-system build in a scratch config folder, which is likely, not traced. The stopped slice left the board not serving until the next reset; the runner's slice should end on the same reset and kick the flash soaks end on.

## 12.69 apr merged into int (28098b4f); the lead's follow-ups f6b7b70c and 7df914d3 (2026-11-06 14:57 UTC)
Reviewed: the retags follow U14_TAGS.tsv ("(structural, ...)" is the table's own citation for 11 E.6.6 rows). The twin fixes come with self-tests seen red
first. The two new zero-wear tests, the supervisor scan and the client-head capture, are what Q6 asked for. No self-inflicted growth found. The lead did CLAUDE.md's 11
rows and the skill's 1, labelled the serving budget attention with its 2026-11-06 measurement, pointed the scenario comment at that row, and stated W65's exception in
SPEC (missed by both briefs). Deferred to the last round: 5 toolchain rows (any edit rebuilds the Unix port) and twin_record.json's regeneration.

## 12.70 Bench run 11 (runner, 16:19 UTC and correction, 423152f5): FRAM 2 h clean; slice ends starve the script's watchdog
Run 11, 14:13:59-16:16:45: 13 slices rc=0, rdid/read256/write1 3,429,131 each (with the 13:10 slice 3,703,418), 0 OSErrors, 0 bad, bad_rate<8.1e-07;
the worst-case latency is bimodal (about 1.3 ms vs 7.3 ms), untraced. The bench's long_fram.py arms an 8 s WDT and feeds only in its loop, so ~8 s after a
slice the watchdog reboots into main.py with no kick: the AP's stale entry (tests_hardware/README.md "after a reset ... stale station entry")
gives W38 then W79, an 8 min hotspot, and undated SGP40 W35/W33 (no NTP), which also explains /status 000 and 13:26's "No route to host". This is the same class as
12.66's radio script. The runner's fram() now ends on reset_and_kick right after the last slice. The reason-2 pin now reads REASON (TIMER vs FORCE) and the seconds
from script end to reset, which supersedes the lead's a-c. Run 11's data point (21) is withdrawn by the runner.

## 12.71 Bench item 4 reruns (runner, 16:29 UTC): 9 of 10 pass; HTTPDropped +4 for 3 refusals is the test's own probe
Flash 6/6 (held SDA through both resets, emptied alarm pool, the two running-graph faults, stepped clock). The session-end gains fit the injections:
E17/E115 come from the graph faults, W34 from the stepped clock, W15 from held SDA, and W22 x7 from a scratch-folder full build. Bench 3/4: zero-think readers, negative
Content-Length, and the reboot at the first answer (SysUptime 9 s, ResetReason 3). FAILED test_each_refusal_at_the_ceiling_is_counted_once_in_http_dropped (0 -> 4): after
the holders close, wait_until(_load.serving) probes at once while their slots outlive the responses (Part I.6). Without the _SLOT_RELEASE_WAIT_S the test
already uses twice, a refused probe counts once. Class (b) test race, read in the source: the fix is that wait before the probe, which goes with the next bench push.
config_flush_during_link_traffic waits for WEAR.txt's cleared: line (planned after the bound measurements).

## 12.72 Bench item 5 and the reason-2 pin (runner, 17:08 UTC); the mixed-body count is the 413 cut again (lead, 17:14 UTC)
Item 5 on d3f10239 (archive 20261106T162825Z): 22 passed, 2 failed, 4 errors. loop_lag 1,006,799 us vs 925,000 (worst ended 16,583 ms after main() started,
p99 64 ms; teardown W51 EHOSTUNREACH): to the /status timing, whose window now starts at main()'s start. concurrent_mixed_body_sizes: HTTPDropped 11 < 24
client refusals. Read in the code: an over-cap PUT's 413 leaves before its body is read (Microdot), the close's RST can erase the client's unread 413, status
line included (RFC 9112 9.6), and urllib files a refusal the server never counted. Same cut as the owner's 11:16:57 ruling (test fix): the bound now counts
refusals within the cap, the note names the rest; to be confirmed by the rerun. fram_erase_over_rest did not run (setup: serving_sweep's carried UART E81
pair, a stall-window candidate). Teardown SGP40 W35/W33 after the DNS and NTP tests: a boot without NTP is the candidate, one archive fact asked.
Near a margin: serving_sweep at -1, 10 readers, 368 B free and a 320 B largest run, 0 allocation failures; heap_at_peak at 32768 after the script's boot
40,784 B free, largest 28,992 B, worst largest 21,552 B. For the heap account. Reason 2 pinned: a harness reset reads 21 (FORCE) unless a device script ran
begin_boot() (consuming record 21) and cleared the phase mark, then 2 (FORCE); an unfed expiry after a stop keeps 21 (TIMER). In operation every firmware
reset writes its record first, so 2 there stays a starvation; the three wordings now give the cause.

## 12.73 The /status stall measured (runner, 17:17 UTC, after the owner-approved reflash of 9c0699e4): the build holds the loop, errcount most of it
Reflash 17:08-17:12, BuildDate 2026-11-06T17:08:25Z, match=1; ResetReason 2 then SGP40 W65 (no valid backup at the new image's first boot; not traced). Probe
heap_probe/status_timing.py (ROOT_CAUSES section 20), 3 readers, 60 s, 32768, 51 x 200, 0 memory failures: build mean 739 ms (703-786), errcount 640 ms of
it (22 sources, 29 ms each, max 56), system 41, networking 14.5; lock wait 3 ms; send 32 pieces mean 1,052 ms (spans other tasks); gc.collect 19-21 ms.
Lags: 27 of >= 200 ms, in groups of one, two and three builds (747-852, 1,507-1,610, 2,267-2,313 ms); 24 of 27 match builds ending inside them. Lead,
read in the code: every source the build awaits is a RAM read that never suspends, so the build runs to its end without a yield (F.3's rule broken);
2.3 s passes the UART link's 1,000 ms ACK wait (E81) and the 925 ms bound; loop_lag's 1.0 s fits a build, not proven. The cost is the piece writer's
per-fragment calls: about seven per history entry. Fix proposal to the owner (needs a go): a yield after each section and each source.
Pushed 17:26: int 8053df32 (mixed-body bound, reason-2 cause in three docs; lint, three mypy passes, tests_scripts 6,931 passed / 6 skipped,
collect-only 218/251) as bench 318ba804, relay 17:26 a1f852a6 on top. Snapshot 44 CI green (run 42256926224): next PARENT 112a8906.

## 12.74 Reruns on the new image (runner, 17:45 UTC, bc2b92c7); two test fixes and relay 17:49 (lead, bench bc15db92, int 5536f8b1)
Flash 4/4 (supervisor pass 2,316 ms between feeds; a real expiry reads 2 with TIMER). Bench 8 passed, 2 failed, 2 errors, then 3/3 on 318ba804
(mixed body: 28 answered, 20 refused, 10 over the cap, bound holds; fram_erase_over_rest ResetReason 8; first 200 12.39 s after reset). Figures for
Part N: head guard 13 lines / 632 B vs 32 / 2,048; radio re-init 8,216 ms vs 20,000. hazard_run: 13 /status refusals = the stall (its UART entries
are all declared); reruns after the fix. answers_before_first_ntp: carried E115 from the flash line, test now saves and clears at its opening.
W35/W33: the garbage NTP/DNS and spoof tests boot with no sync, now declared as the first-sync test does; the odd BootSignature is the random
fallback. W65: item 5's erase (the 12.73 "not traced" is withdrawn). FRAM E51 at real_sta_connect: a hard reset between a chunk's two block
writes (asy_fram_manager.py:243-246), inferred; console fact asked; handling (a reset may leave one E51) goes to the last round's harness item.
Checks: lint, three mypy passes, 9 guard files 850 passed, collect-only 218/251.

## 12.75 The /status stall fix (owner go 17:56:47; int 6cc6af1a, bench b28a9e2f + relay 19:04, head 2c36040b)
Every streamed GET answer writes each top-level value through _PieceWriter.add_value_yielding() (one yield after it); a dict/list/tuple of at
most 4 scalars, no string over 4 characters keys included (_FLAT_MAX), is one json.dumps() (at most 224 B). The 4-character limit is a
technical necessity: without it two g3 memory tests (a 600-char string, the 253-char NTP host) would pass the piece cap. Unix port: 4.6/6.0 ms
to 2.6/3.4 ms (gc -1/32768), about 1.8x (the 2.3x first quoted was the prototype without the string check); board estimate 0.74 to ~0.45 s.
Bytecode +345 B; imageFreeBytes 59,916 to 59,540. Gate yfG green (rebuild, lint, m1-m3, test e/f, four twin runs, npm, coll 218/251, 247/251).
Reruns asked after the owner's reflash OK: /status probe, loop_lag, hazard_run (13 refusals), serving_sweep and heap_at_peak (interleaving).
Runner's noble chroot leg (bc2b92c7, 17:47-18:57): the recipe installs no Node, so the host tier cannot pass as written (66 E-lines; the recipe
text gets the Node step in the last round). Six twin scenario failures, one per device in the first shared boot, each with a feed gap of
7,567-7,628 ms (of 8,000; would_have_triggered 0): inferred one host pause (16 jobs on 4 cores, microSD), not proven; the trixie leg repeats it.

## 12.76 Trixie chroot leg; day 2 closed without the reflash (runner, 20:3x; ROOT_CAUSES 21, bench ddecc1b0)
The 19:15 order was not carried out (the runner did not fetch); the owner then said "okay, but don't start anything after this for today".
Board idle on the 17:08:25Z image; the stall fix (b28a9e2f) is on the branch, not flashed. Trixie (gcc 14.2.0, bc2b92c7, Node v24.22.2):
tests_scripts 6,931 passed, so Node is the whole of noble's 66. MicroPython tier 5,827 passed, 16 failed: feed gaps above 6,000 ms on all six
first boots (6,854-7,980 ms; noble 7,567-7,628), later up to 15,309 ms (arzi bus fault); dev loop_lag_under_combined_load 1,399 ms vs 925.
Reading (inferred): test.sh's own comment names this hazard as not closed - a twin budget in wall-clock measures host speed. The runner
reports 16 jobs on 4 cores; the band puts a Pi4 at 2x (8), so either its speed probe read the fast band or 16 was set: the log's
"== Test parallelism" line decides. Then a low-parallelism run on the new head separates load from code (day 3, after the reruns).
E51: no console saved, so the torn-write reading stays inferred; its handling stays with the last round's harness item.

## 12.77 Work-practice skills (owner go 21:43:14, scope widened 22:20:01; int f4b6775f, bench 2ef970b2 + relay 23:15, head 3dc93e54)
Surveys of the bench record, the docs and the lead's scratch (S/u35/skill/survey_*.md, WRITEUP.md). Built: three skills under
.claude/skills/ (work-routines 139 lines + 36-line symptom table, bench-routines 132, tree-care 57) and six private scripts/ helpers
(_run_checks.sh, _log_verdict.py, _errcount_digest.py, _failed_tests.py, _preflight.sh, _tidy.sh) with 13 tests; /logs/ git-ignored;
BACKLOG chroot-list line. Evaluation: 3 rounds, 16 agent runs with and without (eval/benchmark.md): correctness equal, mechanical tasks
8-23 % fewer tokens and up to 40 % fewer tool calls, planning tasks about even; 12 defects found by the runs and 5 by the gate, all fixed.
Gate on f7847acc: unit and twin tiers green at both stages; tests_scripts red on 4 rules the helpers broke -> fixed, tests_scripts rerun
on f4b6775f 6966 passed. Lint clean, three mypy passes clean. Not built: a /status watcher (perturbs the board), timed notifiers (owner
rule). Proposals left to the owner: CLAUDE.md about 240 lines restating SPECIFICATION.md; BACKLOG.md chroot list about 450 lines.

## 12.78 Doc cleanup; the bench may fix the skills (owner go 07:24:42, 07:39:04; int dbe46072, bench bd11c5b9 + relay 07:49, head 7cd1a24a)
BACKLOG.md 1,038 to 462 lines (chroot entry to what changes a run; the resolved ISL29125/W12 items out, S3b names the open
Overrange run); CLAUDE.md 1,023 to 867, no rule, tag or owner quote lost (checked mechanically); one agent-named change: a
build-environment change gets a BACKLOG line only when it changes how a chroot run goes. README's recipe runs env --tier
generic and puts its Node on PATH (the installer leg folds in; first chroot run is day 3's noble leg). SPEC E.3's one-file
command is _run_checks.sh mpy:FILE; typecheck.sh header says three. bench-routines carries the owner's 07:39 ruling and a
`skill:` hand-back block. Gate: doc checks, then tests_scripts 6966 passed / 6 skipped; decision-vocab allowlist -8.

## 12.79 Bench day 3 started (its note 08:00); relay 08:09 (int 1461960b, bench c500e7c3)
Skill fix 105a9fd6 (BuildDate is GET /system's build, not /status) verified against src and carried into int as 1461960b;
int equals the bench head outside audit/. Fact 1: the Pi4 probes 120 ms, the 4x band (16 jobs); my 20:38 relay took
test.sh's "the bench Pi4's class" comment on the mid band at its word, but README and Part N already had the Pi4 at
~139 ms - the comment is stale; correct it, README's "16 jobs, green" and Part N's band rows from step 3's legs. Fact 2:
the arzi bus-fault scenario alone on this idle host (dbe46072): PASS 3.2 s, 10 feeds, largest gap 1,037 ms, wdt 0 - the
bench's 15,309 ms is ~15x host stretch (inferred load); trixie's host tier ran the browser tests beside the MicroPython
tier, noble's failed at once for want of Node (untested difference). Image 1,304 B larger on the bench with identical
firmware inputs: the ARM compiler is the host's unpinned apt package (here 13.2.1, as on CI; trixie a GCC 14 build) -
inferred; the bench reads its toolchain record's compilers and the .data/.bss sizes (here 18,080 / 51,352) to confirm
whether the RAM heap differs. Not near a margin (58,236 B headroom). Held: any test.sh/README change until the legs report.

## 12.80 The bench's 16 skill proposals (its note 08:11) cross-checked; relay 08:15 (bench 85af49cf)
The owner, to the bench at about 08:08 (relayed by the bench, not said here): "You absolutely can scan through your
work styles and calls from this session and compare them to the newly added skills - if you find something missing or
could be improved, go ahead adding things. But cross check with the main session in order not to break anything."
Clashes: (2) narrowing work-routines' copy-paste line would change an owner rule's scope - keep it; results stay in the
hand-back, no tool named, the 14:35 instruction quoted. (7) "rc 0 only means the step ran" is round1.sh's, not the tier
runners' (they exit with _require_clean_hardware_run.sh's verdict) - HANDOVER. (3) a '192.168.' count flags 45
legitimate tracked lines - check the bench's own addresses. Wording for 1, 5, 6, 8-11, 13, 15, 16; 4, 12, 14 as proposed.
Status from the bench: reflash 08:02 (FC 1 today); /status longest loop hold 122 ms (yesterday 747-2,313 ms); compiler
confirmed (arm-none-eabi-gcc 14.2.1 on the bench), .data +128 B, .bss equal: the bench image's heap is 128 B smaller.

## 12.81 Bench reruns on the stall fix's image (its note 08:30); relay 08:35 (bench 2c971f8b, int a5d3296b)
Reruns: /status loop hold 122 ms (3 readers); loop_lag 155,249 us vs 925,000 (was 1,006,799), teardown E46/W63 (inferred:
the closing reset cuts the test's FRAM load) and WEBSERVER W51 (_WRN_HTTP_SOCKET_ERROR, untraced); serving_sweep -1 pass,
lowest free 7,744 B, largest run 704 B; heap_at_peak 32768 pass, 21,600 B. Hazard under readers' load: the 13 /status
refusals gone; FieldSweep uid [T,F,F] vs [T,T,F]. Code trace: the sweep waits 3 x 1,000 ms after an ACK; the responder
needs 1,000 ms chunk wait + FRAM log + 1,500 ms quiet drain = 2,500 ms + delays: 500 ms slack; a frame inside the drain
is drained as noise -> no ACK. ACK window (8 s) and hold-off (~4 s) not the limit. Inferred; chunks 2->255 is the same
shape and passed. Fix candidate: widen _QUIET_TIMEOUTS (src/, new image, owner's OK). Pre-session /status save: never
works on a running board since 0c0ad52c (2026-10-15): the board fixture's is_reachable() runs mpremote exec (stops
main.py) before session_start_evidence's REST save; FRAM logs still kept, pre-session RAM fields lost; its unit test
calls the function directly. Workaround relayed: save /status by hand before each runner start. Fix: host-side, no image.
Skills: 4 bench commits read and carried (cb6a1b78, d2737a05, c55da08e, e5b28b9d), gates 791 passed, shellcheck clean.

## 12.82 Owner go 08:42 for both fixes; LAN address ruling 08:52; relay 08:59 (int 0d875688, bench d1afd7cc)
Harness: fram_evidence_saved now saves /status over REST before it asks for the board fixture (whose is_reachable()
mpremote exec stopped main.py), then the raw dump and the reset; a run with no board records no note. Its test drives
the fixture itself (12 cases incl. no board and twin); on the old order 3 fail. Gate: lint_direct, host and main mypy,
--collect-only tests_hardware, tests_scripts 6,972 passed / 6 skipped (d81a6620). Sweep wait: NOT changed. 12.81's
margin reading is withdrawn: the responder declines the hazard cmd (id 7) right after its ACK (_accept_set ->
_set_callback -> _reject_wrn: W56 + resync: 1.5 s drain, 1.5 s hold-off), no 1 s chunk-2 wait, so the slack is
1.5 s; loop holds of 122 ms do not explain it, and chunks 2->255 (same shape) never missed. Bench repeat: 2/2 misses at
uid 0xFE under 3 readers, 0/1 without. Cause open; asked: (a) UART_resp counter delta no-load vs 23 loaded (from saved
files), (b) after both chroot legs, a loaded manual run with host-stamped console lines. LAN address (public repo, 11
tracked files on the bench branch, 4 on the audit branch, 1 on main): owner "A simple LAN IP is nothing to be worried
about" - nothing masked; bench-routines' address rule removed (0d875688).
Read (a), bench 09:06 (saved /status reads, no board contact): UART_resp +23 in each loaded run (rerun3 0->23; rerun3b
cleared first, 23 at end), +25 in the no-reader manual run (23->48, Runs 1); UART_init +2 in all three. Two fewer
responder events under load, not one; the counter counts repeats and the history keeps ten, so which two is open.
The procedures also differ (the bench test around the run vs a bare PUT /uart). Read (b) after both chroot legs.

## 12.83 Snapshot 45 CI red: Run 11's warm-up stopped mid-settle; it now runs in full (int 2f6d1453)
One check failed in run 42356435943, digital-twin-e2e (grkizi, -1): Run 11 trend 17,582 B decline against a 14,144 B
tolerance (early_avg 1,293,313, late_avg 1,275,731, 888 samples); 286 other checks passed. Its 868 requests are 44
warm-up cycles (7 endpoints): the plateau rule (no new MEM_SAMPLE floor for 20 cycles; agent 2026-10-15, owner-reviewed
2026-11-06 with its measurement owed) stopped the warm-up while the settle was still falling. The other 15 boots of the
family (arzi, grkizi, klkizi, schlafzi at both stages, this run and 42256926224) warmed 96-100 cycles: 4.2-8.9 KB
against 11.2-15.4 KB. Local, 0d875688, grkizi at -1, five boots: every warm-up ran to its 100 cap, free heap falls
about 70 KB from boot and is still falling at cycle 100; the 80 cycles after it read 5.3-7.2 KB against 12.2-13.6 KB.
The failed boot's early_avg (1,293.3 K) is where the local trace stands near cycle 44 (1,293.8 K). Per-cycle minima sit
4.9-5.1 K under the cycle mean (worst 9.2-10.0 K), so a floor held 20 cycles is a matter of chance mid-settle.
Pre-fix webserver file (5536f8b1's, on 0d875688), three boots: 4.0-5.9 KB against 13.0-17.0 KB, one warm-up stopped
at 96 by the same rule; per-cycle minima 5.2-5.6 K under the mean (worst 10.5-11.2 K), deeper than with the stall fix.
The stall fix raises neither; its yields lengthen a cycle about 7 % (window 868-876 samples against 927-938; CI 3-10 %).
Fix (2f6d1453): the warm-up always runs l2.soak_warmup_cycles = 100; l2.soak_plateau_cycles, its tag and Part N row
go; the warm-up row carries the measurement. A leak sets a new floor every cycle, so a leaking boot always warmed in
full: the planted-leak calibration is unchanged. The new test (one early dip) fails on the old rule as CI did (trend
18,000 vs 6,831). Cost: dev and wozi boots that stopped at 35-88 cycles now run 100 (up to about 1 min per stage).
The failed job's twin log artifact was not read: its storage host is blocked by this environment's network policy.
Gate on 2f6d1453: lint_direct, host mypy, tests_scripts 6,972 passed / 6 skipped; Run 11 grkizi -1 with the fixed
warm-up 7.6 KB vs 11.3 KB (67 %, as CI's worst at a full warm-up, 68 %): the margin is about a third, not wide.
