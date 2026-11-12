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

## 12.84 Trixie leg at TEST_PARALLELISM=4 (bench note ~10:2x); relay 10:24 (bench aed1a1a9)
Fresh chroot, clone of e43f381b: env, lint, typecheck 0; test.sh 1 - tests_scripts 6,966 passed, tests 5,838 passed,
8 failed, all in the scenario harness (dev uart_ring under load, gap 20,574 ms, wtc 1; klkizi two IncompleteRead with
gaps to 9,980 ms; klkizi and schlafzi hotspot toggle TimeoutError; schlafzi accept-queue twin killed -9 after ignoring
shutdown; wozi hung-shutdown watchdog late past its window). grkizi and arzi passed. No failing name shared with either
16-job leg of 2026-11-06 (trixie 16, noble 6). Bench's inference: host contention (the backgrounded pytest tier with
Chromium beside the 4 jobs). Not taken as root cause yet. Relay 10:24: no blind rerun at fewer jobs; vmstat -t 1 on the
host for the noble leg's test.sh, then read (b), then each failing device's scenario harness alone in the trixie
chroot with vmstat; a scenario failing alone is code. The test.sh / README / Part N corrections wait on that.

## 12.85 Noble leg at TEST_PARALLELISM=4 (bench note ~12:2x); relay 12:26 (bench e962e1e1)
f0238c4b: env, lint, typecheck 0; test.sh 1 (L0, L2 FAIL). tests_scripts 6,971 passed, 1 failed
(test_the_timeout_interrupts_the_files_process_once: "the interpreter got 0 SIGINTs"); 14 scenario failures on all six
devices, gaps over 6,000 ms on every device (largest wozi 17,131; first-boot-like 7.17-7.20 s on four). Two read as
more than timing: arzi/grkizi every_admitted_connection... got a GET answered 400; klkizi/schlafzi
a_command_right_after_the_first_answer... watchdog starved (gaps 8,403, 8,513). Names recur across legs (survives_bus...
on 5 jobs; every_admitted... noble both days). The 10:24 relay landed after the bench's last fetch: no noble vmstat.
Lead reading of the 400 (code, not yet confirmed in the log): per-call timeout 5 s; after a stall longer than that the
overdue wait_for_ms sleep pops before the IO-ready read (earlier heap key), the head read raises TimeoutError,
ext/microdot.py:1425 prints it and dispatch_request(None) answers 400. Signature asked: traceback + W49 + a gap over
5 s. Relay 12:26: read (b); then each of the six devices' scenario harness alone in the noble chroot with vmstat; then
test.sh at 4 jobs there with vmstat; three reads from saved logs first (the 400, the 7.2 s boot gaps' phase, the SIGINT
test). Trixie rebuild deferred.

## 12.86 Read (b) and reads (a)-(c) (bench note stamped 12:45, received 12:33 lead time); relay 12:34 (bench 06d88081)
Read (b), 3 readers, console host-stamped: no miss (uid [True, True, False]), 194 /status reads 200; 7 "callback
rejected command 7" lines, 0x00 to 0xFE 2.50 s, chunks 2 to 255 3.30 s; SGP40's backup (FRAM) right after 0xFE;
UART_init E85,E88 where the loaded misses logged E85,E81. Known procedure difference from the failing test: its
reset_all_error_logs() first. (a) the 400s: W49 then Microdot's catch, in boots with largest gaps 6,511/6,498 ms - the
per-call-timeout mechanism (span inferred: twin lines carry no times). (b) ~7.2 s gaps: first boots (shared_boots
twin_01/02, erasefram... twin_01), phase unreadable; ~9,0xx = watchdog_fault_block, deliberate. (c) SIGINT test: count 0
in a 1 s window, stalled counter (inferred). Relay 12:34: read (b') with the reset first, between step 2 and 3; the E88
console lines from read (b)'s saved log; the bench's clock (its stamps ~12 min ahead of the lead's date -u).

## 12.87 Bench clock and E88 settled (its note 12:35:06); a code reading of the uid miss; relay 12:38 (bench f4c49115)
The bench's 12:45/12:44/10:28 were estimates, not readings; the Pi's clock is synchronized (+9.7 ms). E88 belongs to
the crossing step (12:25:10-12), before the sweep: unrelated. Read (b) sweep stamps (host arrival): uid 0x00 reject
12:28:19.765, resync 21.270 (1.505 s), 0xFE reject 22.268 (2.503 s after 0x00's); chunks 2 to 255 3.30 s. Lead reading
(inferred, src/asy_uart_comm.py _accept_set -> _reject_wrn -> _resync; asy_print_log.py wrn_s; asy_uart_link_driver.py
_sweep_fields): the decline persists W56 to FRAM before the resync drain starts, and the console line prints after that
write; the sweep's 3 s wait runs from the ACK. Counted from the ACK the next value lands at 3.0 s and the drain ends at
D + 1.5 s, D the W56 write with its SPI lock waits (readers' /status FRAM reads, SGP40's backup). D > 1.5 s drains the
next frame: no ACK, E81. Read (b): D(0x00) about 0.5 s (3.0 - 2.50, 0xFE's own write taken as short), margin about
1.0 s. The withdrawn 08:35 reading had the right budget and the wrong hidden term. Signature asked of (b'): no 0xFE
reject line, 0x00's reject-to-resync over 1.505 s, D from the E81 time. No src/ change on an inference.

## 12.88 Step 2: each device's scenario harness alone, noble chroot, vmstat (12:33:00-13:33:04); relay 13:34 (bench 9dda941d)
dev, grkizi, klkizi, schlafzi pass alone; arzi 1 failure (mixed_healthy_and_flaky..., IncompleteRead) and wozi 1
(static_site_is_served_over_real_http), both in shared boot 1. Gaps over 5 s alone: arzi 7,683 and wozi 7,148 (shared
boot 1), and the deliberate watchdog_fault_block 9,016-9,032 on every device; every other first boot 2,012-2,022 ms.
Host: 7,082 MB available, swap unused, si/so 0; vmstat's own output has holes (7 s at 12:46:06, 6 s at 13:23:27, five
of 3-4 s) beside blocked processes and wa 18-65 - microSD write stalls. The two 6-7 s holes fall in arzi's and wozi's
first minute: the two ~7 s gaps and the two failures. Confirmed: that correlation. Inferred: write-back throttling of
a writer (the twin calls no fsync; test.sh's mktemp scratch sits under the chroot's /tmp on the microSD). Relay 13:34:
after (b'), step 3 = test.sh at 4 jobs with TMPDIR=/dev/shm (the remedy), then the default parallelism if green.

## 12.89 Read (b'): the miss reproduced at chunks 2; every logged miss sits inside a long SGP40 FRAM backup
reset_all_error_logs() 13:34:34-38, then the hazard run under 3 readers: chunks [False, False, False, True] (expected
[False, False, True, True]), uid right. SGP40 backup ("Writing backup" to "Backup written"): with readers 8.3-19.7 s
in both reads (b) and (b'), without them 0.5-1.06 s. At the miss the backup ran 13:36:50.479-58.799; the responder
printed "unexpected frame while listening" 44.151 (chunks 1, expected), resync 45.698, then nothing until a second
"unexpected frame" 59.174 (0.375 s after the backup ended), resync 13:37:00.875, then chunks 255 declined 08.308; no
decline line for chunks 2. uid 0xFE sat 1.3 s before a backup in (b) and 0.5 s after one in (b'). The initiator logs
nothing in the sweep, so 12.87's three numbers do not apply. Code (lead): the FRAM chunk ops hold the bus session lock
across their asyncio.sleep(0) (asy_fram_manager.py _clear_chunk/_write paths), and /status reads no FRAM (errcount and
get_mem_status are RAM), so under back-to-back readers each held yield costs a scheduler round and a backup holds the
FRAM bus for its whole 8-20 s (inferred); a persisted log write elsewhere waits that long (the second "unexpected frame"
line printing 0.375 s after the backup fits: its err_s writes FRAM before printing). Not shown: why the chunks 2 frame
was judged unexpected rather than ACKed, and what the responder awaited 45.698-59.174. 12.87's drain-margin reading
fits uid 0xFE but not this miss as logged. Next step needs an instrumented image (reflash) or a twin with slowed FRAM:
put to the owner with the FRAM lag (all devices, back-to-back /status only).

## 12.90 Step 3 green: test.sh at 4 jobs with its scratch in RAM (noble, 13:41:46-14:11:43); relay 14:14 (bench ea0971cc)
Exit 0, L0/L1/L2 PASS: 137 files, 5,846 tests, tests_scripts 6,972 (the SIGINT test included), all six scenario jobs;
the pytest tier's twins' largest gap 70 ms. TMPDIR=/dev/shm landed on devtmpfs (the chroot's /dev is a plain bind of
the host's devtmpfs, not its /dev/shm tmpfs): RAM all the same. Closed: the chroot legs' failures at 16 and 4 jobs are
the microSD's write stalls under test.sh's mktemp scratch (step 2's correlation plus this remedy), a host setting, not
code. Docs owed after the 16-job run (started ~14:13): README's recipe gains `mount -t tmpfs tmpfs "$CHROOT/tmp"` and
its umount; README's "~139 ms: 4x, 16 jobs, green" and test.sh's mid-band comment ("the bench Pi4's class" - the Pi4
probes in the fast band) corrected. Relay 14:14: trixie rebuilt with the tmpfs /tmp after the 16-job run; the hammer's
hold reason (the /status stall) is gone, its start waits on the owner's answer to the UART question (12.89).

## 12.91 Owner "B" (14:20:22): trace then fix the loaded UART miss; trace image to the bench (relay 14:23, head 989b8511)
Trace branch audit/uart-trace 421365bb on int 2f6d1453, bench commit 3c0fafe2 (also carrying 2f6d1453): board-clock
TRACE lines (print only) in asy_uart_comm.py (rx header + validation, ACK, fault and W56 persist times, drain start/end
and bytes, listen backoff), asy_uart_link_driver.py (sweep sends and replies), asy_fram_driver.py (bus wait or hold over
100 ms). Unit tests on it: uart_comm 199, uart_link_driver 51, fram_driver 94, fram_manager 148 passed; ruff fails by
design (prints); never merged to the main line. Bench order: after the 16-job noble run, reflash (owner's OK asked by
the bench), read (b') up to three times until a miss; every TRACE and SGP40 backup line from the reset to the run's end.

## 12.92 Owner on the microSD's wear (14:39:21); relay 14:40 (bench a3060dc9)
The owner: "I hope that's not wear of the card, and too heavy write cycles should not be conducted allover again..."
Applied as CLAUDE.md's standing wear rule (host storage included): the trixie rebuild from 14:14 is off (a fresh
chroot is the campaign's heaviest card write); the trixie leg stands at 12.84 (GCC 14 build, lint, typecheck, 5,838
unit tests) with its 8 failures attributed to the card by step 3's noble proof (inferred for trixie, not re-run). All
logs to /dev/shm. Lead's own slip: runs before 13:41 (both 16-job legs, the 4-job legs, step 2) wrote their scratch to
the card, sent without weighing the card's wear. Asked, read only: ext4 lifetime_write_kbytes vs card size, card
make, kernel-log card errors, the noble chroot's size (whole-chroot-in-RAM check), step 2's vmstat bo sum. Wear itself
is not established either way: microSD stalls under sustained small writes are normal behaviour, and errors in the
kernel log would be the sign.

## 12.93 The microSD's wear numbers (bench note 14:43, read only)
Root /dev/mmcblk0p2: ext4 lifetime writes 239 GiB on a 119 GiB card (Samsung, 10/2019, SDXC UHS-I): about two full
card-writes in its life. 20.8 GiB since this boot (07:25:58), most of it the two chroot legs; step 2's hour wrote only
92 MiB (vmstat bo sum). No mmc or I/O errors this boot; one hung-task report at 09:42:56 (card-detect worker waited
over 120 s to claim the host during the morning's chroot work): busy, not an error. Reading: no sign of wear; the card
keeps no wear counter of its own, so this is the best reading available. Revised: step 2's stalls came with little
volume, so the inferred cause is the card's own write latency (a writer waiting on a stalled card), not volume-driven
write-back throttling; the confirmed parts (the correlation, the RAM remedy) stand. The noble chroot is 7.9 GiB against
7.8 GiB RAM and a 3.9 GiB /dev/shm: a whole-chroot-in-RAM check is impossible on this Pi; the tmpfs /tmp is the
remedy. The README recipe gets only the tmpfs /tmp line, as planned.

## 12.94 Owner (14:46:59): the card's writes are a style matter, not a blocker
Scratch and logs in RAM stay (the better style); nothing further blocks on the card. The trixie rebuild stays off by
the lead's call: the morning's run covered trixie's purpose (GCC 14), and its failures are explained. Correction given
to the owner's reading: the SD bus was nowhere near full; the pauses are the card's controller reorganising flash under
many small scattered writes (inferred); parallel jobs hit it more often, but one job at a time (step 2) hit it too.

## 12.95 Trace read (b') x3 and the 16-job noble run (bench 16:27; head 7e2e628c)
16-job noble, scratch in RAM, 14:13:40-14:43:34: green (137 files, 5,846 tests, tests_scripts 6,972, six scenario jobs,
feed gaps <= 161/8000 ms, no vmstat hole >= 3 s): settles README's "16 jobs, green" and test.sh's band comment.
Reflash FC +1 16:10:30Z (owner "Yes go ahead" to the bench), trace image, flash cycles today 2. Read (b'): attempts 1-2
PASS, 3 misses uid 0xFE. Confirmed: uid 0's W56 FRAM write took 8,047 ms behind SGP40's backup (FRAM holds to 5.8 s,
waits to 5.9 s under the readers); uid 254 sent 3.07 s after the ACK; the resync's drain after the write swallowed its
53 B. Persist times 229-8,047 ms (7 of the three runs' writes over 1.5 s). Hidden case: attempt 2's cmd 5 drained the
same way after a 4,144 ms W56; the verdict cannot see it (cmd 5 expected un-ACKed), so a PASS can carry a loss.
Next: the receiver fix (owner B): the UART link never awaits its own FRAM log write; the resync print gains the
drained byte count so the fixed image's console shows any swallowed frame. Bench skill proposal (hand-back stamp from
$(date -u +%T) in the heredoc): no conflict.

## 12.96 Owner (16:36:16) questions the 8 s; the cause is the FRAM chunk code's CRC under the lock (code read)
Confirmed in code: the SGP40 backup chunk is 264 B (VOC state 256 + timestamp 8) with CRC32; _write_chunk() computes the
CRC inside `async with self.fram` (FRAM driver session lock + SPI bus lock), once per copy (two identical copies, so
computed twice), and CRCBase._crc/_crc_wide yield asyncio.sleep(0) after every byte: 264 handovers per copy held under
the lock. Reads (_read_chunk) do the same: incremental CRC per 8-byte slice under the lock, plus a sleep per slice.
Measured fit: holds to 5.8 s per copy under the readers = ~22 ms per handover; unloaded backups 0.5-1.06 s (12.89) =
~1-2 ms per handover. The FRAM transfers themselves are microseconds. So the 8-20 s is a defect (lock held across
hundreds of yields), not FRAM timing; every FRAM-backed log write waits behind it. Put to the owner: fix it at the
source (no CRC work under the lock), and whether the UART background writer (unit uartq, running) is still wanted.

## 12.97 Owner (16:45:25): B, and a design check against the pillars; the lead's two violations
Owner: only B stays (the UART link independent of FRAM timing, and the FRAM hold fixed at its source); the lead should
have checked the pillars before asking (FRAM and UART are unrelated devices: any coupling is a violation), and the 8 s
(0.5-1 s even unloaded) should have raised suspicion as overkill/runaway. Asked: is B sufficient; the affected parts
get a review and design check. Done: unit uartq stopped before its design was checked (S/wt-uartq, uncommitted, 11
files +370/-54, kept as one candidate); review unit designfu started read-only (brief S/u35r/r5/BRIEF_DESIGNFU.md,
hand-back S/u35r/r5/DESIGN_FU.md by 19:00 UTC): violations per part, the coupling sweep over src/, whether B suffices,
the smallest designs, the candidate's verdict. No code changes until the owner has its result.

## 12.98 Owner (16:55:48, 17:02:19): the coupling's origin, and the audit's missing lens; designfu's hand-back
Origin (git, lead): the per-byte CRC yield and the CRC under the FRAM session are original (07-13); the UART fault path
awaiting its log before resync is pre-audit (09-11/12); the UART's FRAM wiring pre-audit (09-16, WP3); the whole-bus hold
per block pre-audit (09-18, owner's heap decision); the decline path's every-time W56 await is audit (U2, 10-06; before:
the first refusal per id only - corrects the lead's 16:5x answer); nothing post-restart. The restart's scans took the
pre-audit tree as baseline, so nothing in it was questioned. Owner 17:02: every part, pre-audit included, gets the lens
"reasonable, minimal, efficient for its function; leaner without losing anything". Lead proposed a read-only
proportionality sweep of the rest of src/ (~11,000 lines, two agents, ~2 %): awaiting the owner's go.
designfu (S/u35r/r5/DESIGN_FU.md, 50 lines): B suffices for every cross-device coupling and both halves are needed; (ii)
is removal-only in asy_fram_manager.py (CRC once outside the lock, check after release, compare by ==, check_length and
the slice machinery go, ~-50 lines, format unchanged); (i) = the uartq candidate trimmed (MemoryError guard on the task
allocation; _err stays a coroutine); the remaining root is the per-byte CRC yield, owner-ruled 2026-09-18 "don't touch".
Lead's checks: both cited rulings found (SPEC :8847, :6743); check_length has no caller; normal reads already move the
whole block in one >=32 B transfer (F.5.2's handled EIO path), so (ii) adds no new transfer class; the supervisor awaits
_log_dead_task() before its feed (asy_system_service.py:531), so the 8-20 s watchdog row is structurally right, unseen.
Slip (designfu): two read-only tool outputs showed the dev hotspot field and one of its grep commands typed the literal;
in no file. Reported to the owner. Briefs from now on: read devices/*.toml and generated modules filtered, never whole.

## 12.99 Owner (17:07:53): the per-module promotion commands with the lean/efficiency questions - found
Found: PROJECT_AUDIT_PLAN.md:373, OR51 (2026-09-26, commit 22bd4c77), the only record: the owner showed two instruction
sets used before every session's merge (four and eight items); the row paraphrases them with a few verbatim fragments.
Its design questions: structure good, understandable, lean; setup reasonable, resilient, reliable; simplification
"especially as much code was accumulated"; anything missing; purpose fully met. Related verbatim: OR36 (:340) "lean,
clean, efficient, minimal, reliable, perfectly suited for the target hardware". OR51.a (1): the audit applies the
whole gate to the whole tree; the plan's 4.2 (:647): every file passes it, "the design questions" included. So the lens
was agreed and planned for every file, pre-audit code included, and was not applied to the CRC and FRAM chunk code
(U12, U16). OR51.a (4) put the quality bar into SPECIFICATION.md Part D: the design questions are not there (D.8 is a
weaker "improvement pass ... not a mandate to rewrite"), nor in Part K's checklist - a doc gap. The full verbatim sets
are in no file of the repo or its history.

## 12.100 Owner (17:16:12): why the agreed design questions were missed at every stage (lead, from git and docs)
(1) Per-file reading: the per-byte yield reads as D.5/F.3 compliance in asy_crc_checks.py ("so a large buffer can't
stall other tasks"); the CRC call reads as normal in asy_fram_manager.py; the cost exists only in their combination
under load. Promotions (07-15/07-18) and audit units read file by file; U16 (10-07) added more yields inside the lock.
(2) The one time it reached the owner (09-18, commit 23e54438, 16:58) it was framed as a heap-remediation side item,
"5.8x wall-time, latency only, no memory", Unix port, idle; not said: the CRC runs inside the FRAM session lock (since
07-18), and 8951387d (14:16 the same day) widened that hold to the SPI bus. Ruling recorded "decided, not deferred;
not to be modified". (3) U12 (10-07) had the routine open and kept the yield citing that ruling; no stage re-checked
its premise. (4) The hold on record (SPEC :7266-7282, 18-23 ms, 09-25) was a 1-byte write / 8-byte read, idle, with "a
second SPI device (none wired)" as the only named waiter; the real waiters were never listed; the backup's duration was
first measured in R5 (12.89). (5) Post-restart: the pre-audit tree as trusted baseline; the lead's 14:20 options again
let "the hold stays and is documented" stand. Common root: the design questions were answered by reading, never by one
number per operation - the function's physical need against its worst-case cost (largest buffer, under load) and who
waits meanwhile. Proposed (docs, in B's unit): Part D gets OR51's design questions with that check; a ruling records
the facts it rests on and returns to the owner when one is shown false; owner questions state a cost's context.

## 12.101 Owner (17:21:06): every agreement and the specs bind at every level; did the same happen elsewhere?
The 12.100 mechanism is general (per-file reading; rulings on the isolated case; the harmless case measured), so other
agreements can be affected; one more instance is known (designfu: F.3's hold.fram_block names a non-existent waiter).
SPEC 0.1 states breadth ("every principle binds the whole tree") but not depth (function to system): one sentence owed.
Proposed (replaces the 17:0x proportionality sweep; awaiting the owner's go): one read-only check, three passes over
existing inventories - (1) the rulings that keep or accept a cost (~79 owner-cited statements in SPEC by a rough grep,
plus matching OR rows): their premise at combination, worst-case load and system level; (2) F.3's 37 budget rows and
Part N's 191 rows: worst-case measurement condition and the real consumers from code; (3) the ~11,000 src/ lines outside
designfu: OR51's design questions at function, module/integration and system level. Ranked, capped, evidence only.

## 12.102 Owner go (17:31:00): the findings into the specs, the ruling's consequences, the levels check, run through
Snapshot 47 = 268ced51 (int 18e9d59c + records to 12.101; next PARENT). Relay 17:32 (bench 7b204269): the chip's CRC
timing read; the bench reports at 17:35 that the owner declined it for now ("No, not now"), nothing ran, the board keeps
the trace image. Started 17:3x: bfix (writing: (ii) + (i) per DESIGN_FU, docs, the rulings' consequences; the CRC
change waits for the chip figure), specfund (writing: levels and viewpoints into Parts 0, D, K, decision records,
CLAUDE.md's question practice), levels1-3 (read-only: rulings, budgets, code). API credits (owner's question, docs via
the guide agent): a cloud session cannot use them; a local Claude Code CLI signed in with the Console account can.

## 12.103 Owner (17:35:11): push regularly; the bench is off for today
A snapshot at every milestone (each unit merged into int, each records step worth keeping), only while no CI runs on
PR #107; no timers. The bench is shut down for the day: the bfix image and the CRC chip read wait for the next bench
day; nothing is relayed until then.

## 12.104 specfund merged (int b412d1b3); levels pass 1 back (S/u35r/r5/LEVELS_1.md)
specfund 6deb4c9f + lead fix b412d1b3, int fast-forwarded: Part 0.1 binds every level and viewpoint (owner 17:21:06);
D.8 = the design questions answered by cost against need at every level; P9 and CLAUDE.md's decision records name the
facts a decision rests on and send it back when one fails; CLAUDE.md's owner-question bullet (with the "flag, don't
guess" agreement lost from CLAUDE.md on 2026-10-06 restored, and K.0's two dangling citations repointed). 111
tests_scripts files that read the two docs: rc=0. Pass 1: of 79 keep/accept statements ~27 carry a runtime cost; four
premises fail and go back to the owner (with passes 2-3, in the OR51 question format): (1) ResetErrors' gather fan-out
and the accepted writer starvation rest on a "CPU-bound" curve that fits the FRAM hold; (2) a refused or dropped
connection awaits its FRAM entry before closing (network <- FRAM; leaner: close first); (3) SCD30's command-path 50 ms
wait sits inside the I2C bus session, legacy waited outside (bench proof owed); (4) the 256 B piece price was measured
idle, ~3x under load (doc). Restored by B(ii): OR69.a (1)'s exposure, the in-path persisted entries, OR72.a (2)'s UART
floor premise. Unverified: udp.poll_idle_ms, stagger.min_read_separation_ms. Slip (levels1): its grep displayed two
SPEC lines carrying the hotspot password; scrubbed from its scratch. The masked pattern counts: SPECIFICATION.md 3,
PROJECT_AUDIT_PLAN.md 1, ~20 audit/ files (doc copies beyond the two accepted code sites; for the owner). common_r1's
filter rule now covers every repo text view; the three running units were told.

## 12.105 levels pass 3 back (S/u35r/r5/LEVELS_3.md): 23 modules, 10 ranked findings
Back to the owner (a ruling's premise failed): #1 the boot stagger waits on a one-shot Timer + flag in task context,
where its own sleep fallback does the job; a dropped fire stalls boot to the watchdog; the 07-18 "watchdog is the
backstop" ruling dates from the old callback chain; #2b = pass 1's (2) (close before the FRAM trace); #6 = pass 1's
(3) (SCD30 holds the bus across its 50 ms waits; SGP40 and BMP3XX release it). Lean removals with no ruling found
(owner sees them before any change): #3 NTP's 1 Hz sync-age loop and notification's pause loop, redundant since
TickSeconds (-2 tasks, -1 of three 1 Hz soft timers, -529 B); #4 await-free _data_lock holds and the lock-less async
Locked* classes (D.10 two shapes; -703 B); #5 PieceBuffer frozen into the five production images, used only by dev's
UART (-803 B each); #7 neopixel overlay task -> a direct write (-1 task, -182 B); #9 product code only tests call
(three VOC port functions, get_last_ntp_sync: OR36; the VOC ones are Sensirion port API, owner's call); #10 captive
DNS builds strings only debug prints read. Doc only: #2a wifi_mode_lock is held across NTP's and Wi-Fi's FRAM log
writes; C.8's 9.1 s bound omits them (after B(ii) one term). With the CRC yield (4c): #8 COBS per-run yield.
Slip (levels3): one unfiltered view of the generated wozi module showed the WifiConfig credential pair; in no file.
Filter widened (common_r1 :55: hotspot|passw|psk|ssid|wificonfig|credential); bfix and levels2 told.

## 12.106 levels pass 2 back (S/u35r/r5/LEVELS_2.md): F.3's 37 rows and Part N's 191; eight fail
(1) FRAM-queue rows: feed.supervisor and system.scan_budget are budgeted at a log entry's own write (627-700 ms) and
checked with no other FRAM user, while the supervisor awaits each entry before its feed (behind a backup block hold,
3.8-4.6 s measured): a task end during the hourly verify likely resets by watchdog (I); rate.persisted_log names the
waiter backwards; hold.fram_block's figure is a synthetic idle block, F.3 and Part N disagree (23,148 vs 16,542 us);
hold.wifi_lock's 9.1 s omits NTP's in-lock FRAM entries; fram.verify_lock_timeout_ms rests on a false premise and
verify_present() has no src caller (removal). B(ii) closes all. (2) con.routine_stall (21 ms) is crossed on the board:
streaming a GET holds the loop 104-122 ms per /status after the stall fix (739 ms before), no F.3 row; stall.voc_process
measured 41.3 ms (3 runs) and its test fails, the row still "owed"; J.6's reply floor would accept a timeout these
stretches break (latent, dev runs 1,000 ms). (3) lag.loop: board 155 ms after the fix (p99 64 ms), cell "owed".
(4) web.chunk_bytes: margin vs an idle, stale 105 KB; under serving load the largest free run is 320-704 B against a
320 B need (1.0-2.2x: near-critical, for the free-heap wrap-up). (5) stall.fram_command is a 3-run worst; raw SPI tails
7.4-11.0 ms may cross the UART floor 6,944 us (I). (6) hold.scd30_*: idle value; byte-wise CRC in the bus session (+0.3-
0.4 s per snapshot loaded, I). (7) feed.reset_path omits the unfed flush on escalation (harmless). (8) runner timeout
margin vs one job alone, run 16 at once. Owed cells with board figures now: stall.crc_byte, uart.gc_pause_worst_ms's
run, web timeouts' /status part (2,591 ms max). con.watchdog holds (~4.5 s per round vs 6 s, I); the table never
states the sum. Credential: LEVELS_2.md 0 matches; its two scratch copies deleted.

## 12.107 Owner (17:57:27): go to all five; completeness and prevention; push first (weekly use at 99 %)
Go: (1) error-log reset sequential; (2) a refused/dropped connection closes before its FRAM entry; (3) SCD30 releases
the bus across its 50 ms waits (bench check before shipping); (4) boot stagger by plain sleep; (5) the lean removals of
12.105 (#3, #4, #5, #7, get_last_ntp_sync, #10) plus verify_present(); the three VOC port functions stay. Owed: a
completeness pass (every occurrence of the 12.100 mechanism: rulings without keep-words, Parts A-M beyond F.3/N, tests,
twin, build chain) and the prevention check (specfund's rules applied in every brief). Snapshot 48 pushed with CI 47
still running, on the owner's order. Next steps: S/u35r/r5/NEXT.md.

## 12.108 stretch back (S/u35r/r5/STRETCH.md)
(1) The 104-122 ms "serving stretch" is the sum of one slice per task queued ahead (C, asyncio order; Unix probe); the
longest /status slice is `system` ~41 ms, ~17-20 ms per errcount entry (I), and a build allocates 160 KB for ~7.4 KB of
JSON (C). Fix at source: `_write_errcount_entry()` writes each history item as one formatted fragment (bytes identical,
3.1x cheaper, 3.2x less allocation, C). (2) The 41.3 ms VOC step is the port's boxed 32-bit arithmetic (42 mul, 11 div,
79.5 constant conversions, 18.5 KB per step, C); need <=0.1 ms (I). Fix: fold the 53 constant expressions to ints and
compute mul/div as exact int products with libfixmath rounding: bit-identical (0/50k vectors, 4,000 steps, C), 2.5x
faster, 18.7 -> 6.4 KB per step. (3) The 21 ms bound has no consumer in the code; it is J.6's GC term; the smallest real
consumer is the 50 ms LED frame; the floor term should be the measured silicon lag. Both fixes are D.8 necessities
(identical results): added to the unit after bfix with the owner's five. Probes ran beside bfix's gate (ratios only).

## 12.109 Snapshot 49 green; prevention in every brief; the completeness passes started (lead, 2026-11-07 18:4x)
- Snapshot 49 (d703361f, int b412d1b3 with specfund): CI green, 34/34 (run 42400151259).
- Prevention, process level: common_r1.md (read by every unit brief) carries the every-level rule (Part 0.1), cost
  against need (D.8), measurement conditions and decision premises (P9), and a hand-back figure per changed operation.
- Completeness (owner 17:57:27 "be sure you really found all such occurrences"): r5/BRIEF_COMPLETE.md, two read-only
  passes, due 21:30. Pass 1: decision-citing statements outside LEVELS_1's 79 and CLAUDE.md's cost-keeping rules;
  figures in Parts A-M outside F.3. Pass 2: tests and twin (doubles that hide a cost, tests pinning a cost), buildgen
  and the five other generated modules, the build chain.

## 12.110 Resumed 2026-11-09 17:16 (owner: "Go on where the session limit interrupted you"); complete2 back
- bfix, complete1 and complete2 resumed by message (their work was saved; the worker restart killed no live run of
  ours: heavy.lock was absent, no process left). complete2 back 17:19: S/u35r/r5/COMPLETE_2.md (43 lines; COMPLETE_2.md
  and both ftmp_complete dirs checked by count against snapshot.sh's pattern: 0). Routing, lead's check:
  - Twin time has no fidelity row (C): host figures x130-190 faster than silicon stand against silicon consumers
    (loop-lag scenario, Run 3/supervisor scan, test_asy_webserver_connections.py:1074 and :1175). The missing guard of
    12.100(c). One fidelity row + the three checks' comments -> the P9 limit-row unit (after bfix; F.3 overlap).
  - SCD30 routine clock stretch (30 ms per frame, datasheet; 4 frames a sample, 12 a snapshot; loop held, rp2 I2C
    synchronous) never measured at any tier (C facts, I effect) -> bench day: one successful-frame figure on dev.
  - WLAN active()/deinit() instant in the twin, no row; stall.wlan_switch owed -> P9 unit row + bench day.
  - Tests pinning a cost (CRC per-byte turns, COBS per-block turns, ResetErrors' gather, _shape_errcount_entry) and the
    approved removals' pinning files -> the units that make those changes, listed first (common_r1's rule).
  - Generated modules: production clean. Gap: wozi's SGP40+BMP3XX pairing is on no flashed board; its 100 ms stagger
    separation has no figure at any tier -> named in the owed measurement, no code.
  - Build chain (C): the GC-threshold job reruns the host pytest tier (579 s single-process) for an identical result;
    every tier fans out over the three arzi-neu devices of one hardware_family (4 of 12 twin legs, 2 of 6 builds, a
    third of each test.sh job's per-device work). Lead's check before asking: the owner ruled on this on 2026-10-23
    (recovered rulings, "Final description": "matrix deduplication ... is a good thing as it saves time and is not
    actually device specific"; devices "treated the same, only depending on their hardware configuration"), and
    test_device_tomls.py pins that one family differs only in name and hostname. Applying the ruling, no question:
    unit bchain (r5/BRIEF_BCHAIN.md), the second writing slot (no file overlap with bfix; its gate waits on the lock).

## 12.111 complete1 back (S/u35r/r5/COMPLETE_1.md, 30 lines; count check 0); routing, lead's check
- (1) A commanded reboot/resetconfig/erasefram under load can end unfed: quiesce() waits each chunk's _op_lock and
  feeds once per chunk; a loaded SGP40 backup holds it 8.3-19.7 s against the 8,000 ms watchdog (I, ~0.5-20 % of such
  commands at that load). A.4 :403's margin is the idle need. Closed by B(ii) only if no op lock spans the CRC's
  yields; complete1 estimates ~5.8 s with the yield kept (2.2 s under the timeout: near-critical). -> bfix review:
  read what quiesce() waits on after (ii) and its worst case; then the CRC yield's urgency for the bench day.
- (2) "CPU-bound at ~2.2 req/s" (premise of max_connections = 6, owner 09-24; backlog; web.poll_interval_ms) is one
  /status build's CPU (~455 ms), which STRETCH's fix cuts. The limit errs safe; nothing moves before a re-measure
  after the fixes (bench) -> P9 unit names the premise; the re-measure joins the bench list.
- (3) C.7's "1 s UART cadence through near-continuous chunk writing" (09-17) predates 09-18's per-byte yield and SPI
  widening, false today (C) -> P9 unit, with the post-B silicon figure (bench).
- (4) Three more locks held across an awaited FRAM entry: _status_lock (any /status source exception), _set_lock/
  owner_lock (config GET/PUT, BMP3XX/SCD30 rungs), _threshold_lock (own module). With DESIGN_FU's _config_lock and
  LEVELS_3's wifi_mode_lock that is one pattern at five sites -> one decision for all five once bfix's post-(ii)
  entry cost and the _q form's final shape are known: the _q form (or the entry after release) where waiters pay far
  beyond need, else the doc names the bound.
- (5) A.4's "1 abrupt restart in 8" is a twin figure (FRAM without wire time) -> P9 unit, silicon figure after B.
- (6) Wi-Fi false-positive backstop needs a person's power cycle vs P1 "no step needs a person": both texts were
  confirmed by the owner on 2026-09-26, the backstop's stated facts hold, no premise failed -> decided, not re-asked.
- (7) BMP3XX polls STATUS every 2 ms through a ~130 ms conversion (~65 bus reads and rounds per measurement) -> the
  driver-side lean unit: sleep the computed conversion time, then poll; checked against the legacy driver first.
- The 26 decision lines complete1's filter withheld: the lead read them masked (quoted, backticked and the password
  pattern replaced; count 0 before printing). Wi-Fi fallback states, threat-model acceptances, bench capabilities,
  LED patterns: none keeps a time, hold or heap cost under combination or load. Clean.

## 12.112 Snapshot 50 pushed (e0e2266a, next PARENT); the owed hotspot-copies question checked and dropped
- Snapshot 50: records 12.109-12.111, COMPLETE_1/2, BRIEF_COMPLETE/BCHAIN; ftmp_complete1/2 excluded (0 in the tree).
- "Remove the hotspot password's doc copies?" (owed since 11-07): A.11 row 8 accepts the shared default permanently
  (owner, 2026-09-26) and row 15 names it the one accepted exception in the public repository; the same literal is in
  `src/` and `python/`, so the doc copies add no exposure. Decided by the owner; not asked (never re-ask a decided
  topic). The session's own rule (never print or write it) is unchanged.

## 12.113 Bench up 3:30 (owner 17:27:35); the CRC cost is the loop, not the yield; C and native forms; why missed
- Bench (17:30): trace image still on the board; at power-on it came up in its hotspot (Pi and board booted together;
  restored 17:28). Relays 17:32 (bench 6ebd0644: probes crc_chip.py and scd30_frames.py, RAM/read only) and 17:34
  (51be454b: probe 1 adds binascii.crc32 and a viper form). Fix image not tonight.
- The chip CRC figure existed since round 1 (bench HANDBACK.md, three runs of the same test): crc_total_us
  182,519-200,261 for 256 B, crc_gap_max_us 1,971-2,087. The lead's 11-07 relay asked for it again (a miss of the
  lead's: the evidence was not searched first). The 11-07 rule (drop the yield if 264 x per-byte < 21 ms, else one
  yield per 64 B) sized the yield, not the cost: at ~0.7 ms a byte even 64 B is ~45 ms. The cost is the bit-by-bit
  Python loop (8 shift/xor steps per byte in two 16-bit halves).
- Forms, same CRC-32/MPEG-2 value, host 264 B: bitwise 265 us, nibble table 67, byte table 35, viper 7 (all "same",
  residue 0). MicroPython's C binascii.crc32 (1 us) is CRC-32/ISO-HDLC, another CRC: a swap changes every stored
  chunk's checksum. No C exists for the CRC-8 (Sensirion's wire) or the CRC-16 (the UART's C-side contract); a viper
  engine keeps all three values (Class B, internal). rp2 v1.29.0: MICROPY_EMIT_THUMB 1, mpy-cross -march=armv6m.
  The tests already use CPython's binascii.crc_hqx and zlib.crc32 as oracles (test_asy_crc_checks.py:643): the C
  counterparts were in view, as test tools only.
- Owner 17:33:38 (why only now) and 17:35:55 (BMP3XX 2 ms polling: where, why; "major overkill", not small; all such
  places). BMP3XX: the deployed legacy driver's `_wait_time = 0.002` ("change this value to have faster reads if
  needed"), promoted unchanged 2026-07-21 (433e35ec), named `_STATUS_POLL_MS = 2` and budgeted by U31 2026-10-21
  (72b12815) without a count per measurement: x32/x32 ~130 ms -> ~65 bus reads where one read after the datasheet's
  computed conversion time does. complete1 called it "small" and the lead passed that on: wrong under D.8.
- Why missed (lead, from git and docs): reviews checked correctness against oracles and bounded loops with timeouts,
  and treated slowness as a scheduling problem (add a yield, name the poll step) instead of a cost against need;
  CLAUDE.md's version-bump practice ("is there a newer/better way") was run over constructs that call MicroPython
  APIs, so a pure-Python loop that could call one was never in its scope; OR36's "perfectly suited for the target
  hardware" (2026-09-26) had no check that makes it answerable.
- Prevention now: common_r1.md "The platform first" (every unit). Owed to the specs: D.8 names the platform check and
  the poll count per event; CLAUDE.md's standing practice extends to pure-Python loops (with the D.8 doc unit).
- Completeness: read-only unit cprim (r5/BRIEF_CPRIM.md, due 19:45): every src/ loop the platform does faster, every
  poll/wait/retry loop's reads per event, the native emitter as a mechanism (freeze, both Unix binaries, twin, mypy).

## 12.114 Bench probes back (17:39 bench clock; runs 17:35:45-17:37:32, owner OK "Yes, run both"; no flash cycle)
- CRC, 264 B on the chip (probe's 17:32 version): image's per-byte-yield form 129,756 us; bitwise without yield
  36,985-37,579 us (crosses 21 ms on its own); nibble table 10,179-10,261 us (2.1x margin); byte table 5,125-5,139 us
  (4.1x); all "same", residue 0; building both tables at runtime 47,637 us. Chip/host ratio ~140-150. Native form and
  C crc32 not yet timed: relay 17:38 (bench 59d14df4) asks probe 1's 17:34 version once more.
- SCD30 on dev i2c1 at 50 kHz, 90 s, 0 errors: write cmd 658-1,608 us; 3 B read 817-1,953 us; 18 B read 3,656-5,127
  us (wire 3,420): routine clock stretch <= ~1.7 ms in 396 frames; COMPLETE_2 #2's 30 ms-per-frame bound did not
  occur (C for this board and 90 s). A sample holds the loop ~6-9 ms in four transfers.
- 17:41 (bench clock; run 17:39:55-17:40:12): viper as first written 3,381-3,418 us (264 B, "same"); C binascii.crc32
  89 us (another CRC). The viper loop converts big 32-bit constants per use; relay 17:40 (bench ed207fcb) adds a
  hoisted form for one more run.
- 17:43 (run 17:42:23-17:42:40): viper_hoisted 946-956 us ("same", residue 0). Chunk CRC, 264 B on the chip: image
  130 ms; Python bit loop 37 ms; nibble table 10.2 ms; byte table 5.1 ms (+48 ms to build its tables at runtime, or a
  512-entry literal); native bit loop 0.95 ms (no table, no RAM); C crc32 0.09 ms (another CRC: the physical need's
  scale). Choice after cprim's mechanism check (freeze, both Unix binaries, twin, mypy): one native engine keeps all
  three widths' values (Sensirion CRC-8 wire, UART CRC-16 contract, FRAM CRC-32 chunks) and drops the yields and the
  16-bit split path; binascii would change the stored chunk format and still leave CRC-8/16 slow.

## 12.115 cprim back (S/u35r/r5/CPRIM.md, 38 lines; count check 0): every loop and poll in src/, lead's routing
- Scope: all 161 loop statements and comprehensions in src/, six generated modules, every non-zero sleep.
- Same-value faster forms (internal, no wire or stored change): one viper CRC engine for widths 8/16/32 replacing
  _crc/_crc_wide and the per-byte yield (CRC-16 on a crc16 UART link costs 20.7 ms per 53 B frame on silicon - the
  bench measured it 2026-11-05 and noted "a faster CRC"; the lead did not take it up); _rx_copy (viper or slices);
  FRAM verify compare by slice ==; _bytes_to_int -> int.from_bytes; VOC (STRETCH's folded ints ~16 ms est., 1.3x
  under 21 ms: near-critical; viper needs a 16x16 split). COBS (wired on no device) and _rx_line_len (no src caller):
  removal candidates, checked against their owner records first.
- The 2026-09-18 "pure wall clock time ... don't touch" yield ruling: its fact failed (12.100); the owner took it back
  on 2026-11-07 17:31 ("applying this already answers the open questions about the checksum"); not re-asked.
- Viper as mechanism: freezes into rp2's .text with -march=armv6m (C), runs on the RP2040 from RAM (C, bench 11-09),
  frozen run owed to the next image; same results on build-standard, build-settrace, lwip, i386; ruff needs one
  `builtins` line, mypy one arg-type ignore per viper function, module_sizes.sh needs -march; coverage shows a viper
  body unexecuted (I); no 64-bit product, x64 word must be masked.
- Polls: BMP3XX 30-73 STATUS reads per sample at x32/x32. Origin: legacy's `_wait_time = 0.002`; U15 (5689e2f4,
  2026-10-07) replaced it with the datasheet's computed sleep; the post-restart repair b4341646 (2026-11-03, "back to
  their pre-audit read paths") restored the 2 ms poll with a parity-with-legacy check and no count per read. Same
  pattern: 6c00e98e (2026-11-03, "LED back to the pre-audit forms") restored request_signal's 50 ms polling of a
  ramp's end (40-2,400 rounds per signal). UART: the validator admits poll_idle_ms = 1 (1,000 rounds/s idle per link);
  write gate 75 rounds per hold-off; notification pause tick (already approved for removal); captive DNS 10 polls/s
  in AP mode (no public UDP readiness wait in 1.29: judged with its unit).
- Lesson for the repair rounds: "back to pre-audit" was taken as "field-proven, therefore good" without the cost
  check; the 11-03 rollbacks (R1 batch) are re-read under D.8 in the driver unit.

## 12.116 Snapshot 50 green; bench released
- Snapshot 50 (e0e2266a): CI green, the pull_request run 42664651318 (34 jobs); the push run cancelled by concurrency,
  as before. Relay 17:56 (bench 6131fcfe): nothing more tonight. bfix told to drop its item 3 (the CRC engine is unit C).

## 12.117 bfix merged into int (a202591d = merge of f86e7612 over b412d1b3; clean merge)
- Lead's review: src +105/-149; fram_manager -814 B by removal (CRC once per write before the sessions; read checks
  after release; cross-check compares by ==, CRC only on mismatch; check_length and the slice machinery gone); print_log
  +554 B for err_q()/wrn_q() and one writer task per store (admitted fix; a task per burst of UART faults, not steady
  state); UART's _err no longer awaits FRAM. _read_into() has production callers (not test-only). The commit's diff
  removes 3 pattern-matching lines from a test, adds none (count only). Gate 11-09 17:17-18:09 green at both GC stages,
  twin suite and harness green, lint and mypy clean. dev imageFreeBytes 59,540 -> 59,780.
- Waits after (ii): a log entry 16-24 rounds (0.26-0.53 s loaded); supervisor pass 1.3-2.6 s against 6 s. Still open:
  the SGP40 chunk's _op_lock spans its own CRC, ~272 rounds (4.4-6.0 s loaded) - quiesce() and SGP40 sampling wait on
  it; on a fault 542-808 rounds cross the 8 s shutdown-step bound. Near-critical: 4.4-6.0 s of 8 s on the normal path.
  The native CRC engine (unit C, 0.95 ms per chunk on the chip) removes it: unit C goes first after this merge.
- Not yet run on the merged tree: lint, mypy, tests_scripts (bchain holds the host); CI on snapshot 51 runs them all.

## 12.118 Owner (18:25:25): native CRC engine welcomed; COBS has its record
- Evidence: owner 2026-11-02 20:58 ("why is nothing using COBS? I assumed it being run on the UART crossover test
  module!") and 21:01 ("Option 1, add the cobs mode in B6"): the flash-tier crossover test runs a `cobs` mode on
  silicon through the frozen FramingCOBS (tests_hardware/device_scripts/uart_crossover_exchange.py:13,60-64;
  tests_hardware/flash/test_uart_crossover.py:81; tests_hardware/README.md:1149). cprim's "wired on no device" meant
  the generated production wiring only, and the lead passed it on as a removal candidate without checking the record: a
  miss of the lead's. COBS stays; crceng told (item 3: same-result form if small, else its figure).

## 12.119 Owner standing rule (18:30:08): ask before removing a possibly unused feature
- Into common_r1.md (every unit). crceng told: run_inc()/check_inc() stay (ported to the engine), reported as an owner
  question; any other no-caller function likewise. _rx_line_len is already report-only.
- Check of what is already decided: 12.107 (5)'s removals were put to the owner and approved ("Go to all", 11-07
  17:57:27). The removals since then: bfix's check_length and slice machinery (internal mechanism, replaced) - none a
  feature. The P9 doc unit carries the rule into CLAUDE.md's working agreements.

## 12.120 Owner (18:31:40): yield inside the SGP40 backup, or was the CRC the issue? Lead's answer
- Three costs stacked: (1) the CRC itself, 130 ms per 264 B on the chip (~1,450x the C need) - the root; (2) the
  per-byte yield added because of (1): each yield costs one full scheduler round under load (16-22 ms with three
  /status readers), so 264 yields per copy became seconds; (3) the CRC ran inside the FRAM session/bus lock, so every
  FRAM user waited them (fixed by bfix). A finer or "smarter" yield cannot help: under load every yield is a round,
  more yields mean more wall time; a yield is harmless only where no shared lock is held across it. With the native
  engine (0.95 ms) the CRC needs no yield at all, and the backup's own _op_lock span drops from ~272 rounds to ~1 ms
  plus its two I/O rounds per block.

## 12.121 bchain merged (int f1a734f5); snapshot 51's CI run never started its jobs
- bchain 75eb43dd (HANDBACK_BCHAIN.md): distinct_devices in scripts/_devices.sh (one per hardware_family, the family's
  first in byte order; owner 2026-10-23 dedup), used by test.sh, _run_lower_levels.sh and CI's devices job (its own loop
  gone): CI twin legs 12 -> 8, firmware builds 6 -> 4; the GC stage skips the host tier (no host test reads the
  threshold) and drops its Node setup. Gate green both stages. Lead's review: lean (distinct_devices 14 lines; the CI
  loop removed; the devices-job test now runs the job's own lines, stronger than the string check it replaced). Size
  passed the brief's 60-line stop (84 changed outside tests and docs, net +16): reported after the fact, accepted on
  review. Findings carried: cross_browser_smoke.mjs could take the same dedup; .claude/skills/work-routines/SKILL.md:29
  still says the GC run includes tests_scripts (P9 doc unit).
- Snapshot 51 (790b8cad): the pull_request run 42673749242 created one job (zizmor, green) and ended "failure" at
  18:27 with no other job created; the push run was cancelled by concurrency after 6 green jobs. Not a test result:
  the jobs never started (GitHub side). Snapshot 52 (bfix + bchain) runs the whole workflow afresh; if it shows the same
  pattern, the cause is outside the tree (Actions availability or billing) and goes to the owner.

## 12.122 Snapshot 52 pushed (28371bca, next PARENT); crceng's source copy caught; weblog started
- The first snapshot 52 attempt refused: crceng had copied src/ (asy_wifi_service.py included) to r5/crceng_probe/,
  outside any ftmp_ folder; the snapshot's credential scan stopped it, nothing committed. crceng told to move it to
  ftmp_crceng/; common_r1 now states the scratch-copy rule; the snapshot excluded both names; pushed 28371bca.
- weblog (r5/BRIEF_WEBLOG.md, due 03:00) from f1a734f5: ResetErrors sequential, refusal closes before its entry,
  STRETCH's errcount fragment, the five lock sites. Writing units: crceng + weblog. Unit B (drivers) after crceng.

## 12.123 Owner (19:17:45): the principle is general, every level; a complete look started
- common_r1's goal line now states it for everything, at micro, intermediate and macro level (not only CRC, locks,
  timing): the default question before any change and in any review. Part 0 gets it in the P9 doc unit.
- r5/BRIEF_SIMPLER.md, four read-only passes, due 23:30: (1) macro - structure, tiers, CI, docs, the apparatus
  (volumes: src 15,750 lines; tests 106,667; tests_scripts 56,743; tests_hardware 26,701; SPECIFICATION.md 12,250);
  (2) firmware; (3) tests and twin; (4) build chain, website, docs. Each finding: the simpler form, what goes, why no
  function drops and no gap opens, feature-removal and owner-ruling flags; ranked by gain against risk.

## 12.124 simpler1 (macro) in: four findings, one owner question; snapshot 52's CI runs its jobs
- r5/SIMPLER_1.md (19:33). Lead-checked: package.json `test:unit`/`test:coverage` differ by `--coverage` only;
  ci.yml has both jobs (:148, :224); b8791e6b (2026-08-12) records the owner's "fully independent" twin instruction.
  (1) runner mechanisms in three languages (summary block, port lock, memory markers, twin launcher; ~800 lines of
  copies plus agreement tests) -> one Python implementation each; OR15.a(2)'s identical block kept (output rule).
  (2) `web-coverage` reruns `web-unit-tests`' selection; no owner ruling found -> one job (~3.4 min warm per run).
  (3) `tests/` and `digital_twin/` fakes share 512 identical lines, held by contracts, already drifted (rp2 DMA
  guard) -> owner question (2026-08-12 instruction); held until pass 3 is in. (4) one rule in up to five homes;
  work-routines SKILL :29/:48 false since bchain -> P9 doc unit.
- Triage of (1), (2) with passes 2-4 at 23:30. Snapshot 52 (28371bca) run 42681719499 is running its jobs (unlike 51).

## 12.125 simpler2 (firmware) in: twelve findings; three internal, the rest owner questions or unit B
- r5/SIMPLER_2.md (19:36). Lead-checked: `err_s()` awaits its FRAM write before printing, `err_q()` prints and
  records at once (`asy_print_log.py` :244-274); 262 `err_s`/`wrn_s` sites in src, 208 in tests and twin; SPEC
  :3811/:9765 accept "an entry logged just before a reset may not reach FRAM".
- Internal, to unit B (no feature, no ruling): (3) the FRAM driver's second lock (pass the bus lock as session lock,
  as SPIDevice/I2CDevice); (4) the five colour functions beside ISL29125 (-1,023 B per production image);
  (5) identical overrides (7 + 4); (6) SCD30's 12 wrappers through one helper pair (-644 B, all 12 kept);
  (12) the 22 starters as `asyncio.create_task`, BMP3XX's repeated type check.
- Owner questions (queued, one at a time after 23:30): (2) `err_q` as the one logging form plus a drain before the
  storage pause - removes the "waits on FRAM through its log" class at its cause and closes C.7.1's reset gap, but an
  entry followed by a synchronous hang before the task's next await is lost where today it lands (CLAUDE.md's FRAM
  diagnostic rule); weblog's item 4 uses `_q` at its sites, valid under either answer. (1) five timers that only
  wake a task -> sleeps (rulings 2026-07-18, 2026-10-13; `stop_uptime_timer`/`stop_check_timer` unused). Unused
  features (keep or remove, 18:30:08): (7) the wiring-defaults mechanism, (8) FRAM chunk `read()`/`write()`,
  (9) `post_fct` (and NTP's hook as a push callback), (12) `get_log(name)`. (10) NEOPIXEL's never-written FRAM log
  (RAM-only keeps `/status`; chunk layout shifts). (11) notification's runtime refusal -> a build-time check (codes
  44/45 leave the catalog).

## 12.126 simpler3 (tests, twin) and simpler4 (build, web, docs) in; the look's triage
- r5/SIMPLER_3.md (19:38), r5/SIMPLER_4.md (19:38); 0 password-pattern hits in either or their scratch. Slips:
  simpler3 views of tests/ and digital_twin/ unfiltered (no hit); simpler4 regenerated wt-u35int's ignored
  `build/generated_src/` from its own inputs (no tracked change; the `build_*.out` there date from 11-02).
- Unit B (firmware, internal, after crceng): 12.125's (3)(4)(5)(6)(12) beside its own list.
- Unit T (tests, after weblog; internal): S3 (1) 14 per-device scenarios the unit tier pins + the boot-order merge;
  (2) the twin's copied unretrieved report -> the product's PrintLog (one boot-contiguity run); (4) seven single
  cases a sweep proves; (6) ~300 lines of helper copies, the dead `rx_stall_ms` knob; S4 (5) tests_scripts' twin
  boots on `distinct_devices()` (bchain's agent decision, no ruling); S4 (10) help pins; S4 (11) the twin harness
  helpers into `_twin_process.py`.
- Unit C (build chain and CI; internal): S4 (1) `MICROPY_QSTR_BYTES_IN_LEN (2)` in the Unix variant header, the five
  launch guards and 19 tests go (rig-only row; rp2 untouched); S1 (2)/S4 (2) `web-coverage` folded into
  `web-unit-tests`; S4 (3) the port lock on flock (the takeover machinery goes) with S1 (1)/S4 (6)/S4 (12): one
  Python implementation per runner mechanism, the markers in one data file; S4 (4) the site stages the generator's
  definitions (~3 s per run).
- P9 docs: S1 (4), S4 (8) CLAUDE.md's UART/memory restatements -> rule + pointer, owner quotes moved whole into
  J.1/I.4 (actor, qualifier, scope unchanged); S4 (9) README's three stale bchain lines; S4 (13) BACKLOG :26-31.
- Owner queue, one at a time: the twin fakes (S1 (3) + S3 (3): rp2 and neopixel one copy; ruling 2026-08-12);
  the logging form (12.125 (2)) - prepped first by a read-only sizing (owner-prep); the timers (12.125 (1): the
  reset timer's 07-18 ruling rests on watchdog settings, not on an arm failing - pass 2 misread it);
  unused features (12.125 (7)(8)(9)(12), the two `stop_*`, S3 (5) launch.py's demo, S4 (4) the definitions CLI);
  12.125 (10)(11); S4 (7) setup's two throwaway images.
- Snapshot 52 (28371bca, int f1a734f5) CI green: run 42681719499, 19:16-19:43 (27 min; snapshot 50 took 29 min with
  the full device fan-out). 51's never-started run stays a GitHub-side event. Next PARENT 28371bca.

## 12.127 logprep in: the logging question's root is the FRAM command path; a bench probe sizes it
- r5/LOGPREP.md (19:56). (a) two forms: couplings remain (supervisor feed, six handler sites unless weblog item 2
  moves them, each logger's own task), no gate stops a new one. (b) `_q` + 2 drains: 253 sites lose `await`, 192 B
  per logged error, reset gap closed, 0 known hang sites; a hang before the writer lands loses the entry. (c)
  synchronous FRAM: 28-33 ms per entry today - over `con.routine_stall`.
- Root (C code, I silicon): a chunk write is 51 CS envelopes (four status pairs written byte by byte, each byte
  WREN/RDSR/WRITE/WRDI/RDSR), each envelope ~0.6 ms, ~90 % call overhead incl. `spi.init()` per CS cycle although
  the FRAM is spi0's sole device (6/6 TOMLs). Datasheet (MB85RS2MTA): WEL stays set after WRITE (continual
  programming), so a WRDI stays if WEL is to be cleared. Fewer, leaner commands may make (c) cheap; the question to
  the owner waits for the figures.
- Bench relay 20:00 (bench cd40e6dc): `fram_cmd.py`, reads only (RDSR, READ at 0; no WREN, no write, no manager),
  times configure, CS, settle, transfer, lock + yield. Host dry run on the fakes clean (lead_framcmd_host2).
- Finding (doc): F.3 `stall.fram_command` times one command; the chunk layer runs 10-20 envelopes between yields.

## 12.128 crceng merged (int 2fbad553); the bench's FRAM command figures
- crceng bb6e79cb (r5/HANDBACK_CRCENG.md): gate green at both stages (137 files, 5,854 tests; tests_scripts 6,970;
  dev twin both parts); dev imageFreeBytes 59,780 -> 59,548. Lead review: viper engine masks at return (32/64-bit
  same values); every `_ring_copy` caller sizes dest first (`_read_delimited` bound, readinto's `nbytes > len(buf)`,
  sized allocations); the write gate's one sleep is equivalent (hold-off armed and cleared only inside the same
  instance's `_busy` transactions). Merged over f1a734f5 clean; on 2fbad553: lint clean, mypy x3 clean, crc 76/76,
  fram_manager 142/142, uart_comm 202/202 at both stages, test_buildgen_validate 362 passed.
- Owner-bound: a CRC register over 4 bytes (built nowhere) now degrades to pass mode - a removal the 18:30:08 rule
  puts to the owner; snapshot 53 waits for that answer. Also asked then: `run_inc()`/`check_inc()` (kept, no caller),
  `_rx_line_len` (kept), plain functions vs the asy_ naming rule (kept coroutines, 160-192 B per call). Lead tooling:
  `module_sizes.sh` line 8 takes `-march=armv6m`. Finding (c): `test_digital_twin_uart_comm_hazard.py` hangs to its
  per-file timeout when its scenario raises (unit T).
- Bench 20:29 (78eb0357, owner-OK'd, reads only), dev idle, per call, median minus the 20 us call floor:
  `spi.init()` 126 us; a lean RDSR 44 us (one call 37); configure + settle + RDSR 198 us; READ 13 B 62 us, 268 B
  373 us (wire 268); an `async with Lock` plus one `sleep(0)` around a lean RDSR 770 us (min 560). So a firmware
  command's ~0.6 ms is ~0.15 configure + ~0.05 transfer + ~0.4-0.7 lock and yield (C); a lean synchronous command
  is 45-80 us, 8-12x less. A log entry as today's 51 commands, lean and synchronous: ~3-4 ms; the SGP40 backup ~5 ms,
  its hourly verify +~3 ms (I, from the figures). General (C): one yield round costs ~0.6 ms of loop on the chip.
- The bench's FRAM log gained E46 then W63 (status byte not idle; block 0 -> block 1): its harness's stop landed in
  an SGP40 backup write (8-20 s per write on the bench's pre-crceng image) and the next boot recovered it - the
  two-block design working, one entry per level. Not the probe (no WREN, no write). Window after crceng: 8 rounds.

## 12.129 Owner (20:43:39): settle the queue by evidence; decisions taken (lead, 2026-11-09)
- Logging -> unit fsync (after weblog): FRAM access lean and synchronous, one logging form that writes inside the
  call. Evidence 12.128: a firmware command is ~0.6 ms of which ~0.55 is configure + lock + yield; lean 45-80 us.
  Configure only when the bus's last device differs (FRAM is spi0's sole device on 6/6, so once; a second device
  stays served); no per-command lock or yield; the WEL/RDSR checks stay (datasheet: WEL survives WRITE). Goes: both
  FRAM locks, the per-command yields, the writer tasks, `err_s`/`err_q`, drains, reset windows, generation counters.
  Kept: every entry, now in FRAM before the call returns (CLAUDE.md's diagnostic rule in its strongest form), the
  two-block recovery, the storage pause (entries stay in RAM), boot load and erase stepped with feeds. Acceptance on
  the next image (bench): an entry <= 5 ms, the SGP40 backup <= 8 ms on the chip; if not met, fall back to `_q` + two
  drains (LOGPREP (b)). The UART rule (owner 2026-09-11) forbids waiting, not a bounded active step: RX runs by DMA,
  TX by IRQ, the reply has 925-946 ms slack (LOGPREP (c)); stated in the record. Weblog's item 4 `_q` sites fold in.
- Timers -> unit B: the two uptime ticks and NTP's check and retry wait by deadline sleeps (start tick + k x period,
  so nothing accumulates; the retry keeps 15 s): their arm-failure branches, flags and `arm_tick_timer()` go, and
  the 2026-07-18 uptime-degrade and 2026-10-13 streak-feed cases lose the event they handled. The reset timer stays
  (owner 2026-07-18's own choice of a ONE_SHOT Timer; pass 2 misread its premise).
- Twin fakes -> unit T: `rp2.py` and `neopixel.py` one copy each in a neutral directory both MICROPYPATH layouts
  read; the twin still imports nothing from tests/ and tests nothing from digital_twin/ (owner 2026-08-12's letter,
  "never imported by or importing it", kept); the 10-14 drift class goes. machine/network stay per tier.
- Notification codes 44/45 -> unit B: a build-time check on buildgen's fixed signal catalog replaces the runtime
  refusal; the two numbers stay reserved, never reused.
- NEOPIXEL's never-written FRAM log -> fsync evaluates: RAM-only only if buildgen can derive "this driver never logs"
  from its source in a few lines; otherwise unchanged (`/status` unchanged either way).
- Setup's two throwaway builds -> unit C: only a lossless form (the installer's from-scratch verification stays;
  jobs that need only the test rig skip what they do not use, if a path exists); else unchanged.
- CRC plain functions: fsync (synchronous FRAM needs a synchronous CRC; the asy_ naming rule's rename follows).
- What remains for the owner: the features with no caller (one question, per item its record and cost).

## 12.130 Owner (21:20:25): NEOPIXEL's FRAM log is intended - why it is empty; the RAM idea withdrawn
- C (git, code): at promotion (da9b4abb, 2026-08-05) the driver's header said it has no `err_s()`/`wrn_s()` call
  "because there is no failure path to report ... write() itself never fails"; the 08-06 docstring trim (4b7d4b2b)
  removed that sentence, so the reason left the code and pass 2 read the empty log as dead. Today: `pixel.write()` is
  a C bitstream call with no failure return; every colour is clamped (`_clamp_byte`) and the ramp floored before use;
  a busy external command answers "LED busy - retry later" (owner 2026-10-02: refused, not a fault); a crashed LED
  task is recorded by SYSTEM's supervisor, the level that handles it. The FRAM log stays wired as it is.
- One place to check (unit B, evidence first): `request_signal()` gives up after `_SIGNAL_WAIT_MS` (120 s) and then
  sets an event the running ramp clears at its end, so a request that times out is dropped without an entry (C code).
  External ramps are capped at 60 s (`T` 0.5-60); whether queued internal signals can exceed 120 s is unknown (I). If
  reachable, the drop is NEOPIXEL's own warning; if not, nothing changes. P9: the "no failure path" reason back as
  one line in the spec.

## 12.131 Owner (21:27:06): LED - FRAM if it can fail, else no logger; can it fail? (lead, evidence)
- Hardware path cannot fail (C, pinned v1.29.0): `NeoPixel.write()` is `bitstream(pin, 0, timing, buf)`, whose only
  raise is a bad encoding (`extmod/machine_bitstream.c`, fixed 0 here); `__setitem__` stores into a bytearray and
  every value reaching it is clamped 0-255. A WS2812 gives no feedback, so no read-back fault exists either.
- Oversight 1 (C): the ramp allocates every frame - rp2 boxes floats (no OBJ_REPR override in mpconfigport.h), so
  `int(r_s * n)` x3 makes three heap floats plus the tuple, ~80 allocations a second at 20 Hz. Under heap pressure a
  MemoryError ends the LED task (SYSTEM's supervisor records and restarts it). CLAUDE.md's ladder: design it away
  first - integer steps (`c * n // steps`) into one reused list, zero allocations per frame.
- Oversight 2 (C mechanism, I reachability): an internal request whose 120 s wait runs out is dropped without trace
  (12.130). To be made lossless by construction (the wait shown bounded by the ramps' own caps, or the drop made
  impossible), not logged.
- Decision: unit B does both; then the LED has nothing it can fail at, so it gets no error logger - its FRAM chunk,
  history, `/status` errcount entry and ResetErrors source go (owner 21:27:06 directs it). Its "command received /
  signal started" event lines stay on the plain console printer (no history, no store). The next image's relay says
  the FRAM chunk layout shifts (read errcount before the reflash, the standing rule). If oversight 2 cannot be made
  lossless, the LED keeps its FRAM log with that one warning.

## 12.132 Owner (21:33:48) on the five features; evidence per item (lead)
- (1) `run_inc()`/`check_inc()`: owner - drop (introduced for the FRAM, obsolete since bfix). -> unit fsync.
- (2) CRC over 4 bytes: no one added it. The owner's legacy module (`legacy/dev_drivers/crc_checks.py`) takes any
  `num_bytes` (Python big ints), so wider registers ran only as a side effect of that generic loop, never configured;
  U12 (2949ed97, 10-07) added the two-word path to speed 32-bit only. Owner: "probably can go" -> goes as merged
  (crceng: widths 1-4). Snapshot 53 is unblocked.
- (3) The wiring defaults are exactly what the owner describes (`[instance.wiring].<dep> = {default = true}` selects
  a module's own constant source: SGP40's T/RH, notification's no-op LED sink): they stay, a principle (modules
  self-contained). Pass 2's item 7 withdrawn.
- (4) The settings hook is used: every generated module wires `post_fct=conn.reconnect_wifi` on the Wi-Fi group and
  `post_asy_fct=ntp.ntp_force_sync` on NTP's (legacy parity: `legacy/firmware/modules/sensortask-*.py`
  `cmd_post_check(..., post_fct=conn.reconnect_wifi)`; owner 2026-10-08 "connect to it in reasonable time"). Pass 2
  missed it: the credential filter hides any line naming a Wi-Fi field, and that line names them. Stays; pass 2's
  item 9 (push callback, one PUT path) withdrawn. Rule added to common_r1 (a filtered-out line is unread, never
  evidence of absence; print only an identifier's match).
- (5) launch.py's demo: the real firmware on simulated hardware serves the real website today
  (`scripts/run_unix_port_integration.sh --device <d>`, README :879-885; CI's live put matrix and cross-browser smoke
  drive it every web run); the demo serves no website ("no website, twin only", README :679). -> goes in unit T; its
  --fault/--hang vocabulary moves into the runner.
- Slip (lead): one grep of a generated module printed its Wi-Fi settings-group line unfiltered (field names only, no
  value; 0 password-pattern hits in this session's outputs written to files).

## 12.133 Owner (21:36:14): the LED request timeout - origin and the general form (lead)
- Original firmware (`legacy/firmware/python/IndividualDrivers/neopixel_signal.py:101-122`): no timeout, no give-up;
  an internal request took `start_signal_lock` and waited until the running signal ended (by spinning on
  `sleep(0)`, itself ~0.6 ms of loop per round on the chip, 12.128). The 120 s deadline came with U9 (2f049a00,
  2026-10-07, audit) as "twice the REST ceiling of t (60 s)"; no owner ruling asked for it.
- It is unreachable (C): one warning-service loop awaits each request (FlashDur 0.5-10 s, FlashInterval >= 60 s),
  so a request waits at most one external ramp (<= 60 s) - the deadline and its drop never fire.
- General form (unit B): one LED lock held for whatever drives the pixel - a signal ramp or an overlay write (it
  replaces `_overlay_lock` too). An internal request waits its turn on it (FIFO, no polling, no deadline, never
  dropped); an external command is refused while it is held or one is pending (owner 2026-10-02); every wait ends
  because every ramp is finite (T <= 60 s, FlashDur <= 10 s). Goes: `_SIGNAL_WAIT_MS` and its tunable row, the
  polling loop, the second lock, the drop. With 12.131's allocation-free ramp the LED has no failure path left, so
  it gets no logger (owner 21:27:06).

## 12.134 weblog merged (int 8f04f2f1); units B and fsync started
- weblog f3886cb0 (r5/HANDBACK_WEBLOG.md): gate green at both stages (121 files, 5,504 tests; host 6,976; dev twin
  both parts); dev imageFreeBytes 59,780 -> 60,068. ResetErrors in turn; a refused/dropped connection frees its slot,
  closes at once, its entry written behind (the awaited-after-close form piled up tasks until the heap ran out under
  `uart_ring_under_concurrent_load`, reproduced twice - evidence for 12.129's one non-waiting form); errcount one
  fragment per slot (bytes identical, 5.2x faster, 4.3x less memory per 10-slot entry on 32-bit); 90 log sites under
  the five locks on the `_q` form. Agent decisions kept: the in-flight reset mask (two concurrent ResetErrors still
  possible). Open: a commanded reset holds `owner_lock` across a failed flush's entry (fsync removes the wait);
  SCD30's six single-field getters stay (OR36.a (3), decided - not an owner question).
- Merged over 2fbad553 clean. On 8f04f2f1: lint clean, mypy x3 clean; webserver_service 227, uart_comm 202,
  config_manager 246, print_log 110, fram_manager 142, each at both stages, 0 memory markers.
- Unit B (r5/BRIEF_B.md, due 06:00) and unit fsync (r5/BRIEF_FSYNC.md, due 07:00) started from 8f04f2f1; fsync owns
  the logging form and the FRAM path, B the drivers and services; fsync's call-site conversion is a saved transform
  the lead re-applies to B's files at the merge.

## 12.135 Owner (21:57:36): the LED give-up is a pattern - every bound traced to its source (lead)
- The lens the four simpler passes missed: an audit-added bound on a wait (timeout, deadline, retry cap, drop) with a
  magic number, on a wait that cannot fail from outside. They asked open questions; the LED's 120 s give-up passed them.
- Prevention: common_r1 "A bound needs a source" (outside party, legacy, or owner ruling; inside waits FIFO, no
  deadline; numbers derived or named; no silent give-up). Units B and fsync told by message (21:59).
- Sweep: BRIEF_GIVEUP.md, three read-only passes (network and link / drivers, system, generation / apparatus), each a
  mechanical enumeration with a per-hit ledger (rows = hits = sum by verdict), due 01:30; candidate lines in src/ alone
  about 1,000 (name patterns, 8f04f2f1). Findings route to B/fsync merges, T, C; the rule goes to P9 as one Part D line.

## 12.136 Snapshot 54 red: the NTP no-reply scenario read its chunk-write count before a written-behind write (lead)
- unit-tests: `an_ntp_server_that_never_replies_...` failed on dev (both GC stages) and arzi (-1): storm (3, [..71], 1),
  final count 2. Cause: weblog made the no-reply entry `err_q` (written behind); the count was read while the writer
  still owed one write, which landed before the run ended. A test race the merge opened; product correct.
- Reproduced locally with one extra yield per chunk write (storm 1, writer active and due, end 2: CI's exact figures);
  without it the local host finished both writes in the attempt window. Fix 6aec784f: the scenario awaits the writer
  task before counting (no bound, no number). Green: six devices at -1, dev and arzi at 32768; lint and mypy clean.
- Lead slip: the weblog merge check ran five interacting files, not test_sensortask.py, whose scenarios count FRAM
  writes after log calls. The class goes with fsync (entries written inside the call); fsync removes this await then.
- Snapshot 55 = b4d87294 (parent fb9d8f17), pushed 22:3x; CI pending. Its scan (records only) was clean. The lead's
  extra count over every changed file matched 4 lines of tests/_sensortask_scenarios.py (since f1f800e7, 2026-10-08):
  private-range IP literals in the /status networking scenarios, which the pattern also covers; no credential (0
  matched strings shared with src; lines viewed through the filter). Lead slip: one command would have printed the
  scan pattern's own line; the permission check refused it, nothing printed. Pattern lines are never printed.
- giveup pass 2 handed back (GIVEUP_2.md, 1,190 rows); its slip: one pdftotext datasheet read (neither git nor grep).

## 12.137 giveup passes 1 and 2: triage and routing (lead, verified by reading)
- Pass 1 (848 hits = rows) and pass 2 (1,190 = rows); the counts close. Verified by the lead before routing:
  (1) v1.29.0 `Stream.wait_closed()` is `self.s.close()` with no yield (`extmod/asyncio/stream.py:19-21`, `aclose` the
  same, :220): the webserver's per-close `wait_for_ms` and the proxy's two bounded closes bound a call that cannot
  wait - REMOVE (G). (2) The UART write gate sleeps up to the resync window (1,000 x 3/2 = 1,500 ms) under the bus
  lock with no ready() round, so `cancel_read_timeout()`'s 1,000 ms gives up on a healthy holder and `clear()` persists
  W55: an inside wait whose deadline also misfires - REMOVE the deadline, the counter and W55 (code reserved), Class B
  entry (G). `clear()` stays (the module's own API, OR36.a (3)). (3) ISL29125's settle cap: the deadline moves only on
  the device's own CONFIG1 writes - REMOVE (B). (4) BMP3XX's cmd_rdy poll: ERR_REG after the reset already catches a
  refusal, a bus fault raises in the I2C layer - REMOVE (B).
- Routed to B by message (22:4x): (3), (4), SCD30 reset wait to the datasheet's < 2 s, SGP40 measure wait to Table 8's
  30 ms + one tick (bench flag), the webserver's false owner credit for the LED wait, NTP's stale doubling names.
- Unit G (bounds; after B, at most two writing): (1), (2), captive DNS backoff to the legacy fixed 3 s, the config
  store's `os.remove` retry, DERIVE: HTTP 5 s / 15 s from silicon's longest request, DNS 500 ms against lwIP's own
  1,000 ms per try, UART `_POLL_JITTER_MS` from one frame's wire time, the link's hazard recovery attempts, the
  `_BACKOFF_MAX_MULT` comment's source; plus pass 3's.
- Owner, after pass 3: ISL29125's calibration candidate cleared after 10 min (user-visible, no source); `dns.tries`
  (1 everywhere, a pre-audit session's knob that never repeats).
- The "owner-reviewed, 2026-11-06" tag (129 in SPECIFICATION.md, about 13 in code) marks an agent decision inside a
  topic the owner reviewed at big-picture level; the LED's 120 s carried it. Clarified in common_r1's bound rule.

## 12.138 giveup pass 3 (apparatus) and the owner's widening (22:27:31)
- Pass 3: 5,153 hits = rows; every apparatus bound was added by a session. Routing: unit T - the unit and twin tiers'
  wall-clock limits on the code's own coroutines (about 1,100 call-site numbers; the per-file timeout is the owner's
  hang backstop and names the hung file), the twin harness's product-timing numbers read from `src/` (its 10 s request
  wait sits below the product's 15 s cap), the async harness's reap limit in rounds; unit C - `build_firmware.py`'s
  `nm`/`git` timeouts (a silent "git cannot tell"), the toolchain's ~55 local-command bounds (one silently reinstalls
  Node when `node --version` is slow): they go, CI's job `timeout-minutes` is the backstop for setup (decided under
  20:43:39; not a test file, so outside the per-file rule), picotool's 5 x 2 s retry derived or named.
- Owner 22:27:31 widened the sweep: every pattern the audit added without his consent that kept growing, not only
  bounds; no real feature dropped, no gap opened or reopened, lean and efficient for the rp2. The bound sweep becomes
  one family of it; BRIEF_CONSENT.md (four read-only passes) covers the rest, building on scan/ and scan2/ (10-28).
- The two owner questions (ISL calibration candidate expiry, `dns.tries`) wait for the consent sweep, so they come as
  family-level questions with the rest.
- Snapshot 55 b4d87294 green: run 42711567341 (pull_request), 28/28 jobs success; the push run 42711553365 cancelled by concurrency.

## 12.139 consent pass 4 (documents and rules) and a lead error it caught
- Lead error, corrected: BRIEF_B item 7 ("codes 44 and 45 retired, kept reserved in the catalog, never reused") and
  12.137's "W55 (code reserved)" contradicted the owner's decision 6 (2026-10-28 14:23, "third option accepted": no
  placeholder rows for numbers retired before the release; SPEC near :3654 says the same). Verified in the record;
  B told to delete the rows and add none (23:0x), fsync told the same for any code it removes. A decided topic
  re-decided by the lead from memory: the record is read before a brief states a ruling's consequence.
- Pass 4: 2,590 items = mapped (873 to 31 mechanisms, 1,717 NOTMECH); 33 rows = KEEP 19 + ROUTED 7 + SIMPLIFY 4 +
  ASK 2 + REMOVE 1. SIMPLIFY: the 11-06 tag on 235 lines (about 60 files) to the plain "(agent, date)" the decision
  record rule asks for, plus one sentence that the 11-06 review accepted topics (P9, with code comments after B and
  fsync merge); I.2's per-module prose that a test demands per module (the owner's rule and the code check stay);
  A.11's exposure table and its check (A.8 lists every route); the changelog's constants table and its check (the
  entry rule stays). REMOVE: PAP:203-206's numbering rule (the owner dropped BACKLOG's on 11-06). ASK family F1: C.8's
  lock table and C.9's task table, each restating code under a test - judged with passes 1-3.
- Pass 4 slip: a first scratch extraction held unmasked added lines (deleted unviewed, rebuilt filtered; 0 matches).

## 12.140 consent pass 3 (tests and twin)
- 14,437 items = mapped (9,715 to 75 mechanisms, 4,722 NOTMECH); 75 rows = KEEP 43 + ROUTED 17 + REMOVE 10 +
  SIMPLIFY 4 + ASK 1. Most new test lines sit under topics the owner asked for (43 KEEP rows, each with a quote or an
  incident). Grew without consent: tests_scripts checks that pin SPECIFICATION.md tables (every product change edits
  them too), and 55 planted self-bite tests that survived 95e4fbde's `*_bites` removal under other names (owner,
  verified: "Planting errors for those straightforward tests would be complete overkill.").
- REMOVE (unit T, about 1.8k lines): the 55 self-bites; the definitions shape corpus (only with pass 2's validator);
  the checks pinning F.3's timing rows, I.2, C.9, the readiness-flag layout, A.11, the sleep forms, the suppression
  form, old legacy paths - each names its remaining catcher. SIMPLIFY: per-handler C-stack pins to one logger check
  (SCAN2); watchdog feed sites to one rule (feed only in the system service, never in a callback); counter steps to
  the cap rule; lock order keeps the order check, drops C.8's table match. ASK (C-stack family): the 1,227-line static
  await-depth analysis and its tunable against the bench measurement plus the approved reboot (image unchanged).
- KEEP noted: the bench FRAM-log check (it caught a flash script's SGP40 W33 entry in the production log, 11-06).
- Pass 3 slips: one unfiltered grep of PROJECT_AUDIT_PLAN.md printed OR70.a's line (the accepted fallback named as a
  limitation, no value); an overflowed output saved by the harness under /root/.claude/ (not opened); a stray
  /tmp/x1 (row IDs) removed at once.

## 12.141 consent pass 1 (firmware)
- 1,196 items = mapped (1,046 to 98 mechanisms, 150 NOTMECH); 98 rows = KEEP 72 (64 with the owner's words, 8 with a
  demonstrated need) + ROUTED 16 + SIMPLIFY 6 + ASK 4 + REMOVE 0. The 11-03 rollback round already removed most of
  SCAN2's eight patterns. Also confirms 12.139's catch (decision 6 on retired numbers).
- SIMPLIFY (unit G, after B and fsync): the UART's typing-only guards (owner 2026-10-27 "option b"; range checks and
  codes stay; Class B line); the 11-06 suffix on 14 code comments; the deferred flash write's per-store Event,
  `defer=`, `commit()` and hooks to "stage, push, write once" (the consented behaviour, its tests rewritten first;
  medium risk); the reset flags as one phase value (after fsync); UART discarded-byte accounting by the ring's
  received total (inferred: verify first).
- ASK families: A1 agent behaviours inside owner-specified sensor features (SCD30 FRC temperature guard, SCD30
  range gate E27, ISL29125 INT parking; with GIVEUP's ISL 10 min candidate expiry and `dns.tries`); A2 functions with
  no caller (`_rx_line_len`, `get_log(name)`, the definitions CLI; `UARTComm.clear()` stays, OR36.a (3)).
- Pass 1 slips: one `python3 -I -c` read of a JSON's keys; a scratch copy briefly held 9 unfiltered Wi-Fi timing rows
  (deleted, unprinted). Part N mislabels about ten legacy-sourced values as "estimated" (P9).

## 12.142 consent pass 2 (website and build chain); the owner-credit check
- 2,091 items = mapped (2,011 to 92 mechanisms, 80 NOTMECH); 92 rows = KEEP 72 + SIMPLIFY 7 + REMOVE 1 + ASK 1 +
  ROUTED 11. The website's growth is owner-asked (OR94/54/78/100/121/138, review "ok"s, B7/B8).
- SIMPLIFY: the page's background /status check skips while a section already polls /status (one request a minute per
  tab); the browser's per-hint re-validation of generated definitions to the pre-audit scope (~135 JS lines, +593 B gz
  per image; with pass 3's shape corpus); one shared errcount code table per page (~206 B gz per frozen page); the
  boot oracle out of `generate_device()` into the test generator (its third FRAM-consumer table goes); the stager's
  500-line JS lexer to about the pre-audit form (a duplicate name then fails at page load in the staged tiers); one
  module-to-file table in `buildspec.py`. REMOVE: `trigger_spread()` (one bench test, no device's order). Routing:
  W/S rows to unit C, website rows to C with the JS mirror rule, G rows to C.
- ASK candidate S18: the gc policy checker's per-test-function allowance table (38 rows; OR39's rule). Lead: the
  per-function grain is the guarantee (a new test propping a result in an allowed file is caught), so the form may
  lean (the allowance beside the site) but the grain stays - no owner question.
- Authority labels: 56 "(owner, date)" credits in this scope against 2 at the audit start; of 2 checked, one has no
  owner record ("never bundled with a suite runner", 09-26). With the webserver's LED credit (12.137) that makes two
  unbacked credits: every owner credit in the repo is now checked against the records (BRIEF_CREDIT.md, read-only).

## 12.143 The consent sweep's ASK items settled by evidence (lead, under the owner's 20:43:39 direction)
- SCD30 FRC temperature guard: KEEP. Its 2.5 ppm/degC is the datasheet's "Temperature stability +/- 2.5 ppm / degC
  (T = 0 ... 50 degC)" (Sensirion SCD30 datasheet, CO2 table, read 23:2x): a source.
- SCD30 range gate (E27): KEEP. Its bounds are the datasheet's I2C range "0 - 40'000 ppm", -40 to 70 degC, 0-100 %RH;
  BMP3XX's pre-audit Table 2 gate is its sibling; the non-finite half guards F.1's page break.
- ISL29125 INT parking: KEEP. The datasheet's flag is HIGH while green is outside the window and LOW once inside, with
  persistence control: left armed it re-asserts every persistence window (ISL29125 datasheet, CONFIG3 and the
  threshold-assignment text, read 23:3x).
- ISL29125 calibration candidate's 10 min expiry: REMOVE (the bound rule: no source; the owner ruled the run bounded,
  09-13, not the candidate): it stays until the next run starts or a reboot. Nothing lost (unit G).
- `_rx_line_len`: KEEP - `readline()` (:633) and `readline_until_complete()` (:669) call it (pass 1's no-caller row is
  wrong at 6aec784f); readline is driver API (OR36.a (3)). The definitions CLI: KEEP - `scripts/build_website.sh:61`
  runs `python3 -m buildgen.definitions` (SIMPLER_4 #4's no-caller claim is wrong).
- `get_log(name)`: the parameter goes - every `src/` call passes none; only tests set it (OR36.a (1), owner-ruled).
  Sent to fsync (its file).
- `dns.tries`: no question - unit G derives the DNS numbers from the platform's own resolver (lwIP, which legacy's
  getaddrinfo used: 1,000 ms per try, up to 4 tries), weighing C.8's NTP hold under the Wi-Fi mode lock; the knob
  stays only if the derivation gives more than one try.
- C-stack static analysis (pass 3's ASK): KEEP. The margin is near critical: limit 7,936 B (F.1), ~200 B per await
  level, depth 32 failed on silicon and depth 28 left three calls (2026-10-29), the longest static chain is held to
  25 and runs through the FRAM log path - fsync's flattening should widen it (re-measure at fsync's merge).
- C.8/C.9 tables (pass 4's F1): the checks stay; their per-lock and per-task data move beside the checks, the
  specification states each rule once (lossless, unit T with P9). S18: the per-function grain stays (12.142).
- No owner question remains from the consent sweep; the credit check (BRIEF_CREDIT.md) may add some (03:30).

## 12.144 The credit check: 1,456 owner credits, 146 not backed as written
- 2,265 hits = rows = BACKED 1,054 + TOPIC 256 + STRETCHED 37 + UNBACKED 109 + NOTCREDIT 809; 1,456 credits (1,402
  added in the audit, 54 pre-audit). By the credit's own date: 29 audit-era (STRETCHED 23, UNBACKED 6) - corrected by
  the record, no question (the backed quote, or "(agent, date)"); 117 dated July to September (STRETCHED 14,
  UNBACKED 103: 66 mechanisms, 10 numbers, 15 rules, 12 other) rest only on a session's commit message ("Per explicit
  direction ...", e.g. 90ced2b for the SGP40 reset, verified) or on nothing - put to the owner as one question.
- Verified by the lead: the SGP40 reset credit cites 90ced2b (2026-07-22), whose message says "Per explicit direction";
  no record file holds it. The webserver's LED credit is STRETCHED (the owner said internal LED commands are bounded in
  number and frequency, not the wait). Scratch check: ftmp_credit and ftmp_consent4 hold only IPv4 literals under the
  scan pattern (counts by class, nothing printed); all hand-backs and ledgers 0.
- Credit slips: raw grep lines (57 filter-matching) written to scratch before masking; raw record copies written and
  deleted in one command; chained `rm`s; an overflowed output saved under /root/.claude/ (not opened).
- Container restart ~00:57-01:00 UTC: units stopped; B committed 69c06662 (waiting for the gate lock), fsync committed 1547690d (gate2b rc=0 at 00:54, npm step killed; lock 'fsync' held); both resumed by message 01:0x. Owner question open: the 117 pre-audit-dated credits (12.144).

## 12.145 fsync handed back (1547690d); one follow-up commit asked
- Done: SPI configures only when another device took the bus; FRAM commands plain calls (WEL/RDSR kept); chunk ops
  synchronous (`_op_lock`, yields, `quiesce()`/`wait_idle()` gone; two-block recovery, stored format, pause, stepped
  boot load and erase kept); one log pair writes its entry inside the call (err_q/wrn_q, writer, windows, generations
  gone; flush_pending/ResetErrors answers kept); CRC plain functions, `crc_checks.py`, run_inc/check_inc and
  verify_present gone (E19's row deleted, none reserved); get_log lost its name. Gate: test.sh 5,418/0 at both
  stages, tests_scripts 6,975 + 1 failed (below), twin dev suite and harness PASS at both, npm 1,276. src -310 lines,
  -4,755 B mpy (only `asy_spi_driver.py` +84 B, admitted); imageFreeBytes dev 64,356 B (weblog head 60,068).
  Unix-port: entry 8.7 ms, SGP40 backup 8.6 ms, read 7.9 ms; counts 51/51/46 - the bench targets reachable by count.
- The red test: the boot-placement control arm (survivors must land high without the per-unit collects) fails - they
  land 659,040 B low without them. The collects' premise is gone: by the owner's 19:11:51 goal they go (decided under
  20:43:39; the owner's 09-18 approval gets its record line); the main arm stays; bench re-checks placement on silicon.
- Settled, no change: ResetErrors' 21 writes in one stretch (a user command below a config flush's stall: F.3 lists
  it among command stalls); endurance (no rate bound; FRAM effectively unbounded per CLAUDE.md; worst case continuous
  back-to-back 37 y on the 64 Kbit part, 370 on the 2 Mbit). Twin Run 3's 627 ms ceiling -> T.
- Open for the owner (after the credit question): the status pair written as one 2-byte write (51 -> 31 commands per
  entry, same crash states per both datasheets p.9) against his 2026-09-18 byte-at-a-time ruling - record to read.
- fsync slips: one test file and one rebuild outside run.sh; one unfiltered view of `_digital_twin_scenarios.py`
  818-862 (masked placeholders only).

## 12.146 ub handed back (39e18d2a) and merged: int ddf77ce8 (tree = 39e18d2a's)
- Gate on 39e18d2a: test.sh -1 and 32768 (121 files, 5,442 tests), tests_scripts 6,981, twin dev suite and harness at
  both stages (on 69c06662, only a test changed since), npm, lint, three mypy passes. Its run 1 hit the same NTP
  no-reply race as 12.136 on grkizi: ub's form (an attempt ends once the writer is idle) kept, int's await dropped at
  the merge, so the merged tree equals the gated one. Both go with fsync's synchronous log.
- Read by the lead for self-inflicted growth: the LED is one lock (overlay task, its lock, the 120 s wait and its
  tunable gone; integer ramp into one reused frame; no logger, LED FRAM chunk and wiring gone); TickGrid (15 lines,
  one form for three services' cadences, brief item 6) replaces their timer mechanisms; BMP3XX's wait is the
  datasheet's 3.9.2 formula x 6/5 (covering every Table 22 maximum) + one tick. src -407 lines, -6,737 B mpy; dev
  imageFreeBytes 65,740 B. VOC: bit-identical, 34,200 -> 8,727 B allocated per sample on the 32-bit port.
- Kept, with evidence: captive DNS strings (their decode is today's malformed-label refusal - not debug-only; 12.105
  #10's premise wrong); SGP40 100 ms (backed: DP A22 on 5ff8c0b, 12.144's ledger).
- Bench owed on the next image: SCD30 bus release, BMP3XX computed wait, FRAM layout shift (LED chunk gone: read
  errcount before the reflash), plus fsync's acceptance figures and boot placement.
- UART changelog: ub moved PieceBuffer into asy_uart_driver.py and touched asy_uart_comm/link (no wire change): one
  Class B entry owed, written at the fsync merge (after fsync's B99). Brief error: BRIEF_B said "UART changelog
  untouched (no UART change)" while item 8 moved code into the UART driver.
- ub slips: python3 edit scripts outside run.sh; unfiltered Read-tool views of SPECIFICATION.md and device-script
  ranges (checked after: no filtered line among them); test batches 23:53-00:30 ran beside fsync's gate.

## 12.147 fsync's follow-up (e1958815) and the merge unit
- e1958815: no `gc.collect()` in `src/` (run_setups/start_tasks lose their per-unit collects; `asy_system_service`
  -8 lines, -58 B); the site checker's src and probe rows, the suppressed control arm and `_ProbeGc` gone; the main arm
  passes on all six devices with margin (setup batch median >= 645,408 B below its seam, bound 307,200; whole boot
  830,304 B, bound 262,144). F.3 gains `stall.reset_errors` among command stalls and the wear worst case in one line.
  Gate pieces under the lock (02:30-03:05): tests_scripts 6,962 + 1 (a stale citation allowlist line, deleted, 15/15,
  amended), dev twin suite at both stages. fsync left CLAUDE.md's exception paragraph and the work-routines skill line
  111 unedited (a message is no authority for CLAUDE.md): the lead decided the removal (12.145) and gives both edits to
  the merge unit under CLAUDE.md's own stale-doc rule. Slip: the lock's `rm` shared a shell call with a grep.
- Lead trial merge of e1958815 over ddf77ce8: 18 files, 27 hunks; aborted, int unchanged. Unit mfs (BRIEF_MFS.md,
  worktree S/wt-mfs, branch audit/mfs at ddf77ce8) merges, applies fsync's transform to ub's files, drops the writer
  conditions, adds the UART Class B entry, fixes the two stale docs, gates; due 07:30.

## 12.148 Merge unit mfs: a293d6f9 = int (fast-forward), gate green
- 18 files, 27 hunks resolved, both intents kept (ub's deletions stand over fsync's conversions; ub's added calls take
  fsync's form); the transform over ub's 72 files made 2 rewrites (the SCD30 helpers), a second pass none; residue grep
  found one defect (the NTP scenario's `_writer` condition), removed; B100 Class B in the UART changelog.
- Docs the merge left stale, fixed: CLAUDE.md's exception paragraph and skill line 111 now state that the firmware
  calls no `gc.collect()` (read by the lead: accurate, minimal - kept), HEAP_FRAGMENTATION_MEASUREMENTS.md's two lines,
  F.3/C.7 (ResetErrors on dev is 19 writes, counted on the merged tree), I.2's timeout row, C.8's SCD30 reset 2 s.
- Gate (03:26-04:25, lock as mfs, removed): test.sh -1 PASS 121 files 5,354 tests + tests_scripts 6,964; 32768 PASS
  5,354; dev twin suite (329 + 15; NEOPIXEL's persistence check went with its logger) and harness at both; npm 1,276;
  lint and three mypy passes clean. Sizes vs 8f04f2f1 (armv6m): src -725 lines, -11,533 B mpy; dev imageFreeBytes
  59,836 -> 70,292 B (both built by mfs).
- Left: `tests_hardware/bench/_load.py:477`'s comment names `arm_tick_timer()` (ub's leftover) -> T. mfs slips: one
  unfiltered grep printed two lines with WifiConfig test-fixture arguments (fixture values, not the hotspot password;
  to be checked by count); helper scripts with python3 outside run.sh.
- Snapshot 56 = 512bb0dc (parent b4d87294), pushed 04:28; pattern check: counts unchanged per changed file except the CRC test's rename (same 4 hex strings). CI pending.
- (12.149) G's DNS derivation, accepted by the lead: per-server timeout 1,000 ms = lwIP's DNS_TMR_INTERVAL (dns.h:54,
  STABLE-2_2_1 at v1.29.0; rp2 lwipopts overrides neither it nor DNS_MAX_RETRIES 4, opt.h:1176); one try per server
  (the server list is the retry, as lwIP's backup step; NTP's 15 s / 60 s retries repeat the attempt; four tries would
  raise C.8's Wi-Fi-mode-lock hold from ~9 s to ~21 s): `dns.timeout_ms` 500 -> 1,000, `dns.tries` and its loop go.
  The values live in buildgen/codegen.py (product constants the generator emits): G edits those lines, C told.

## 12.150 Snapshot 56 CI: unit-tests-coverage red, 27 other jobs green
- `test_an_internal_request_waits_past_any_deadline_parks_no_sleep_and_is_never_dropped` (ub's new LED test):
  MemoryError allocating 8,192 B under build-settrace (4-5x allocations): 20 Hz ramps over 180 s recorded ~7,200 frames
  and one list entry per step - brute scale where the property needs none (CLAUDE.md's host-churn rule). Reproduced
  locally under build-settrace (41/42, the same 8,192 B). Fix (int, after a293d6f9): the same 180 s at 1 Hz (182
  frames), the most parked wakes kept as one number; a deadline or a poll still fails it. Green under coverage and
  at -1 and 32768 (42/42, 0 memory errors); lint and three mypy passes clean. Gap in the units' checks: neither ub's
  nor mfs's gate ran the coverage build, whose test result gates (owner 2026-09-22) - unit briefs name it from now on.
- Snapshot 57 = e8d48fab (parent 512bb0dc), pushed 04:59; pattern counts unchanged per file. CI pending.
- Snapshot 57 e8d48fab green: run 42759272501 (pull_request), 28/28 success incl. unit-tests-coverage; push run 42759267380 cancelled by concurrency. Next PARENT = e8d48fab.
- (12.151) Bench relay 05:45 (bench branch 24278836, [skip ci]): zero-flash work now - errcount read and archived first (the next image moves the FRAM chunks), FRAM timing with mounted .mpy from e8d48fab at addresses above the production layout (entry <= 5 ms, backup <= 8 ms, commands 51/51/46, viper CRC32 264 B), SCD30 bus release and BMP3XX's one wait with mounted drivers; full-image items after G's reflash.

## 12.152 Bench 06:03 (bench 4cd3fc2a): FRAM fails acceptance ~5x on per-command layering; I2C checks pass
- errcount archived first (errcount_20261110/20261110T055436Z_errcount.json); nothing cleared. Lead correction: the
  20:32 relay's "the entries stay" was wrong - the FRAM manager's own log is RAM-only (no fram_target), so its E46/W63
  went with a power-on.
- FRAM on silicon (e8d48fab's src/ mounted as armv6m .mpy, 125 MHz, idle, chunks from 0x30000, median of 30): entry
  write 26.3 ms (<= 5 asked), backup 26.9 ms (<= 8), reads 24.7 / 26.2 ms; commands 51/51/46 as counted; viper CRC32
  264 B 1.27 ms. Cause, measured: 0.46-0.60 ms per command, all Python layering (raw RDSR 61 us): SPIDevice
  session_begin+end 212 us per command, write_sync/readinto_sync +130 us, the driver's get_values path +250 us. The
  Unix-port 8.7 ms does not carry over (0.5 ms per command on silicon, not 0.17). The fsync acceptance stated in the
  brief was not met by the unit: its figures were host-only, and the bench caught it.
- Fix routed to G as item 13 (06:1x): one bus session per chunk operation (configure-once and the async-session refusal
  once per operation), per command a CS toggle and bound machine.SPI calls into preallocated buffers, get/set_values at
  the minimal path; every CS cycle, command order, stored byte, WEL/RDSR check and the crash ordering unchanged (owner
  2026-09-18); target ~60-80 us per command (entry ~4 ms, backup ~6 ms); G due 15:00. Bench re-measures on the image.
- I2C: in 38 SCD30 waits (51-59 ms) the ISL29125 completed 10-18 whole transactions each (1,697/1,697 ID reads OK), 6
  SCD30 samples, 0 faults; BMP3XX x32/x32 10/10 valid, 5 calls each with one 158.5-160.7 ms gap (no STATUS poll).
  Flash cycles today 0. The lead's reply to the bench session was refused by the bridge again.
- (12.153) Bench reachability, root-caused (owner 06:15:46): the bench is a Remote Control session on the owner's
  computer (environment_kind "bridge", CLI 2.1.321, cross_session_inbound available); its messages reach this session.
  This session's outbound SendMessage is refused by its own credential ("this cloud session cannot message other
  sessions yet"; container CLI 2.1.282, session from 2026-09-25; ListAgents lists no other session, no Remote Control
  here; no refusal carried a trust digest). The bench polls the bench branch ("polling lead for new image"), so a
  relay pushed there reaches it without the owner: relay 06:16 pushed (bench 967e2577). The lead's earlier "please let
  it know" was the wrong conclusion; the branch is the channel.

## 12.154 The FRAM status-pair ruling read at its source (lead, 06:4x)
- SPEC A.4's "What each protocol element is for (owner, 2026-09-18)" (SPEC:279-285) was ledgered BACKED via DP L02, but
  L02 is the bus-lock scope per block operation (8951387, item 6). The account itself is 6811f03 (agent commit,
  2026-09-18, pre-audit): HEAP_FRAGMENTATION_MEASUREMENTS.md 3B.1 "recorded as the owner gave them" - the same class
  as the 117 (a session's record of the owner).
- 3B.1's reason: the pair is written "separately, on purpose: a power loss between them leaves the pair inconsistent
  ... One 2-byte write would erase that signal". MB85RS2MTA WRITE (ds text :437-439): "When 8 bits of writing data
  is input, data is written to FRAM memory cell array" - each byte commits on its own, so a 2-byte write torn by
  power loss leaves the same (new, old) pair, detected the same way; only the window shrinks. The chip needs its
  WREN/RDSR/WRITE/WRDI/RDSR envelope per WRITE command, not per byte.
- No later owner decision on the pair. Explicit wording plus a contradicted reason: not settled by the 06:26:36
  rule; put to the owner (06:4x) as the status-pair question.
- G slip (G's own report, 06:3x): its targeted batch (FRAM, bus-hazard, twin files, some binding real ports) ran
  06:23-06:33 while C held heavy.lock (since 06:20:52). A port-collision-looking failure in C's gate in that window
  is read against this first. G item 13 committed locally (cae371b1), touched files green at both stages and under
  coverage; G waits for the lock.

## 12.155 cr2 handed back (07:03): the 117 pre-audit-dated credits resolved by the owner's 06:26:36 rule, none left
- Ledger `S/u35r/r5/CREDIT2_ledger.tsv` (117 rows, 6 columns), hand-back CREDIT2.md (29 lines); scan-pattern and
  filter counts 0 in both. R0 grew 11, R1 later decision 8, R2 record agrees 24, R3 session-only 8, R4 fits 66, R5 0,
  LEFT 0. No code consequence from R1-R5: every outcome is credit or wording text (code comments included).
- R2's new source: the owner's own commit 8c4a73d5 (2026-07-13, improved-quality WIP) by content (SCD30 50 ms, SGP40
  3 ms, storage pause, VOC state fields, reset never dropped, boot signature); each credit shrinks to what the code
  shows. Lead note for P9: DP E05 rows read "(owner, 2026-08-12, as recorded in DP E05)" - a deleted plan's record,
  never re-put to the owner.
- Lead correction: cr2's "idle-poll-rate still unanswered" is wrong - the page reply answered it and OR141 (owner,
  2026-10-05, "do all as you suggested") adopted it, OR141.a (5) "its measurement owed" (DR1:390-396). R4 for the
  20 ms stands.
- Routing: all 117 text changes -> P9 (code-file comments included, after G and C merge). R0 growths: the bench
  test's torn-FRAM tolerance, the import-placement rule and its test, the twin's not-loaded notice -> T; the
  starter-role definition and four doc-only rules -> P9; each judged by common_r1's source rules. The status pair
  (12.154) is apart: with the owner.
- cr2 slip: two scratch scripts held the filter pattern line (no source text); deleted by literal path.

## 12.156 C handed back (07:26, 7c4b21e3) and merged: int 26d7f317 (clean merge over c4fc72ac)
- 115 files, +1,211/-2,844 (tests +570/-1,460). C's gate on 5aebb51e (amend changes one Part N row): test.sh -1 and
  32768 121 files/5,354 tests, tests_scripts 6,809, twin dev suite + harness both stages, npm lint/typecheck/unit 1,192,
  coverage 1,192 (real node_modules), zero MemoryError. dev imageFreeBytes 70,292 -> 70,812 B; app.js gz 27,155 ->
  26,826 B per device.
- Diff read for added complexity: the generator's whole-tree flock (4 lines, FIFO, no deadline) answers a race #4's
  own change exposed (parallel website builds renaming each other's .tmp) - smallest fix, kept. The qstr width is a
  toolchain override with an anchor check and a 300-byte readback; CI's unix-port cache key hashes
  micropython_overrides, so CI rebuilds. G02 reads validate.py's consumer table (private import) instead of a third
  copy. Port lock, summary emitter, stager all shrink. Lint on int 26d7f317 clean.
- For the combined gate: PICO_TOOLCHAIN_DIR=S/tc-c (C's build with the qstr override; toolchain files identical after
  merge) or rebuild tc-int. Finding (c): web coverage fails with a linked node_modules (a293d6f9 too); the lead's
  gate runs npm test:unit locally, CI runs coverage with npm ci.
- Not done, stays (not lossless): SIMPLER_1's one-language twin launcher; SIMPLER_4 #7's two setup images. Queued for
  the owner (feature rule, after the status pair): buildgen.definitions' CLI main() has no caller since #4.
- Owner 08:46:45: option (a) - the status pair stays two WRITEs, each byte committed by a CS deselect, not by the
  per-byte storing within one command. No G item 14. P9: SPEC A.4's 09-18 paragraph takes the 11-10 ruling as the
  reason and credit (R1: a later clear decision), "one 2-byte write would erase that signal" not restated.
- Queued item settled by evidence (20:43:39), not asked: buildgen.definitions' main() was at 25caf528 an internal
  build step whose one caller was build_website.sh (:37); since C's #4 it has none but its tests (OR36.a (1)). The
  capability stays: `_generate_sensortask_modules.py --device-toml PATH --out-dir DIR` writes one device's
  definitions/<d>.json. Lossless removal -> T, with its tests.

## 12.157 G handed back (5a4d21f3) and merged: int 81e2ebcd (clean over 26d7f317; SPEC, codegen.py, validate.py and
## one tests_scripts file auto-merged)
- G's gate on 5a4d21f3 green: test.sh both stages 121 files/5,347 tests, tests_scripts 6,966, twin dev suite (329+15)
  and harness both stages, npm lint/typecheck/unit 1,276, lint and mypy clean, zero MemoryError. src -12 lines,
  -21 B bytecode; growth only item 13 (FRAM driver +350, SPI driver +317, FRAM manager +184 B). dev imageFreeBytes
  70,524 B (a293d6f9: 70,292).
- Diff read: item 13 binds CS value(), its level and machine.SPI write/readinto once per operation (begin() over
  SPIDevice.begin_sync()); an unbound command raises; settle stays blocking. Driver-layer Python calls per entry
  471 -> 138; Unix-port times unchanged (the fake dominates): silicon decides. Item 8 kept the isinstance halves
  (bool-as-int and `-> object` callbacks are runtime checks, not typing-only); item 10 partial (stores' close flags
  kept: a ConfigManager would otherwise see the system service); item 11 not done (DMA ring total would count
  validation-failed frames: E89 false positives); HTTP 5 s/15 s name their source (ResetErrors' PUT never measured).
- On int 81e2ebcd: lint clean; mypy main 283, twin 59, host 317 files clean, the conftest and network checks clean.
  Combined gate started 08:5x under heavy.lock 'lead' with PICO_TOOLCHAIN_DIR=S/tc-c (300-byte qstr readback ok).
  After it: the coverage-build check over the 24 tests/ files the two merges changed.

## 12.158 The combined gate on int 81e2ebcd green; the coverage-build check green; snapshot 58 (lead, 09:4x)
- gate_mg (09:41): unit tier 121 files, 5,347 tests passed at -1 and at 32768, tests_scripts 6,808 passed, zero
  MemoryError; twin suite and harness green at both stages; npm lint, typecheck, unit green. The port-53 listing
  printed "ss: command not found" on this host only (CONSENT_2 S36 kept it; CI has ss): no change.
- cov58 (09:48): the 23 tests/ files changed since c4fc72ac (24 counted earlier: the 23 test files plus a helper),
  26 jobs with the PER_DEVICE file's four devices, every one under build-settrace rc 0 with no memory marker.
- heavy.lock released 09:48. Snapshot 58 from int 81e2ebcd, parent e8d48fab.

## 12.159 Snapshot 58 CI: "Unit tests (shipped gc.threshold)" red in the toolchain install, no test ran (lead, 10:0x)
- Run 42793916276, job 129754408805: merge c's Unix-port override changes the toolchain cache key, so every job
  rebuilds; this runner's `apt-get install --download-only` (588 MB, the arm cross-compiler packages) hit
  `_APT_STEP_TIMEOUT_S` = 150 s three times while the mirror was still delivering libnewlib-arm-none-eabi (49.2 MB).
  web-unit-tests built the same toolchain in 4 min 22 s on another runner. apt's own Acquire::http(s)::Timeout = 30 s
  already ends a stalled read; the 150 s wall-clock limit also ends a slow live one.
- Origin: audit 65088dec (2026-10-08); 25caf528 bounds no apt call. GIVEUP_3 judged it DERIVE ("measurement owed");
  C kept "network steps and apt keep theirs". This run is the measurement: it gives up on a live download - the
  owner's give-up pattern (2026-11-09 21:57:36). The CI mirror check (apt-cache-restore's probe, bound-s) exists to
  dodge this same limit in the firmware and web jobs: if the limit goes, the probe has nothing to compare against.
- Now: one re-run of the failed job when the run completes (died in install, before any test body; the passing jobs
  save the new toolchain cache). One PR comment. Fix: a small unit after P9 (two-writer limit) - the apt wall-clock
  limits go (setup_toolchain, apt-cache-restore, playwright-chromium, setup_cross_browser_toolchain.sh), apt's
  Acquire timeouts and retries stay, the mirror probe judged with them (goes if it only served the limit); into
  snapshot 59 with T and P9.

## 12.160 P9 handed back (54bac5f8) and merged: int 6953c09f; the gc-threshold job re-run; unit APT started (lead, 10:5x)
- Read: comment-only in src/, scripts/, devices/ (one trailing credit form; mpy-cross output byte-identical per P9).
  CLAUDE.md 878 -> 801, the owner's words moved whole into SPEC J, D.3, I.4. The config-migration rulings (owner,
  2026-09-26) stand in SPEC :210/:3413, so BACKLOG's item could go. The settings-store growth goal went: written into
  BACKLOG during the audit (195f3ed3), its only source an agent commit (249f2ae); the general store stays in code.
  THIRD_PARTY_LICENSES: who flagged or found each origin goes, the checks stay (CREDIT2 R3 rows 60-64).
- P9's own checks on 54bac5f8: test.sh (tc-c) 121 files, 5,347 tests, tests_scripts 6,805, 0 failed, no MemoryError.
  The standalone default-toolchain twin-spawn failure is the missing qstr override, (c). No audit IDs in text
  (test_citations): owner forms carry dates instead.
- CI run 42793916276 completed with only the gc-threshold job red (12.159): failed jobs re-run once (10:5x).
- Unit APT (BRIEF_APT.md) started from 6953c09f beside T; ftmp_apt joins SNAP_EXCLUDE.

## 12.161 Snapshot 58 green; the image relay (lead, 11:0x)
- CI run 42793916276 attempt 2 green after the one re-run (12.159): 910a0a62 is the next PARENT.
- Bench branch 881562cf: code commit dab692d6 (int 81e2ebcd outside audit/, the bench evidence unchanged) plus the
  10:58 relay: build, the owner's reflash OK asked by the bench, first-boot FRAM lines and errcount, then FRAM entry
  and backup times, memory without collects, C-stack, req/s, UART cadence, stall.wlan_switch.
- Bench 11:10: snapshot 58 flashed (881562cf, BuildDate 2026-11-10T11:02:16Z, owner OK at the bench; FC +1 at
  11:07:25Z). First boot as expected: 17 chunks failed CRC/status and were set up afresh (16 both blocks, 1 blank
  block 0), no other FRAM line, no reset; then SGP40 verification 60, 9 "timestamp not valid" before NTP, SGP40 "No
  backup found!". errcount after the restore boot: 21 sources (NEOPIXEL gone with its logger), SGP40 W65, WIFI
  W38/W79 from the unkicked first boot's hotspot round, the rest empty. Items 1-6 running.

## 12.162 Bench item 1 on snapshot 58: FRAM entry 12.7 ms, backup 13.0 ms (targets 5 / 8 missed); item 6 method (lead, 11:2x)
- Bench (ac7fe7bd; its note stamped 11:30, received 11:1x): frozen path at 0x30000+, idle, 125 MHz, 32768. Commands
  51/51/46. Medians of 30: entry write 12.7 ms, backup write 13.0, entry read 10.9, backup read 13.2; max 15.8 / 21.1.
  Viper CRC32 over 264 B 1.31 ms. ~250 us per command (raw RDSR 54 us): begin() 185 us per operation, _read_status
  143 us, _send_command 119 us, get_values 1 B 245 us, set_values 13 B 809 us (5 commands). Per CS cycle 65-90 us
  over raw (two bound cs() calls, two sleep_us(2), try/finally, attribute loads); ~100 us of checks per get/set call.
- The 5 / 8 ms were 12.128's projection (45-80 us lean commands), made the acceptance in 12.129 with a recorded
  fallback (`_q` + two drains). What actually bounds a synchronous write: the UART DMA ring (rxbuf 512 B = ~44 ms at
  115200 of continuous wire), the reply slack ~925 ms, the watchdog 8.4 s. One entry is ~29 % of the ring; three
  back to back with the peer streaming would approach it. Not near a limit in normal operation.
- CS_SETTLE_US = 2 (pre-audit, 25caf528): the datasheets need tCSU/tCSH 10 ns and tD 40-60 ns; the Python gap between
  pin and transfer alone exceeds that. Removing the two sleep_us per command is datasheet-backed and lossless
  (estimate ~1-2 ms per entry). 5 ms needs fewer commands (the 31-command form the owner declined, 08:46:45).
- Question to the owner (one): keep the measured figures, or lean further, or the recorded fallback.
- Item 6: relay 11:16 (bench 7753f9ac): (b), the product's own switch under the lag wrapper, ap_down/ap_up, per switch
  max loop lag, UART failures, time to STA; no flash write.

## 12.163 Owner (11:21:35): would async FRAM help? Lead's answer; APT reviewed before hand-back (lead, 11:3x)
- No. Both datasheets (`datasheets/fram/`, p.1): a write "takes no wait time"; the 12.7 ms is CPU on ~51 commands, not
  waiting. (1) Per-command yields (pre-fsync form): longest single block ~1 ms (CRC 1.3 ms), but one round costs ~0.6 ms
  idle and 16-22 ms under three /status readers (12.120, 12.128): an entry ~30 ms idle, up to ~1 s loaded, and the
  bus lock held across them. (2) Queue + writer: the same 12.7 ms block, moved in time; entries in RAM until written,
  so the last error before a reset can be lost (CLAUDE.md's FRAM-log rule). Gain only below ~13 ms reaction needs;
  tightest limit is the UART ring at ~44 ms. The lever is per-command cost ((a) settle sleeps, (b) checks once).
  FRAM question (a)/(b)/(c) still open.
- APT (wt-apt, uncommitted, waiting on heavy.lock held by t): diff read, 7 files +51/-63. Sent back: the commit
  message credits the owner with common_r1's derived rule (fix; re-check the other two credits); the Playwright
  install's 5-min `timeout` (audit 2026-10-19, GIVEUP_3 KEEP "measured") also cuts apt (with-deps) - judge by the
  same rule, least mechanism for its mirror bound, or report options.
- Owner 11:25:20: "option a". The measured figures stand (entry 12.7 ms, backup 13.0, read 10.9 / 13.2, max 15.8 /
  21.1, snapshot 58); no new mechanism. Follow-up unit FS after T merges (it touches FRAM tests): the six per-command
  `sleep_us(CS_SETTLE_US)` in `asy_fram_driver.py` go (tCSU/tCSH 10 ns, tD 40/60 ns; the Python gap exceeds them),
  the generic SPIDevice's per-operation ones judged by the same datasheets; SPEC :272's "blocking 2 us settle", F.3
  `stall.fram_entry` (the 5/8 ms "acceptance" goes, silicon figures in), `stall.fram_command` (~250 us per command),
  `stall.reset_errors`, `rate.persisted_log` (its 3.5 ms basis was the projection) state the measured fact. The
  last-round image (two-image GC proof) carries it; the bench re-measures item 1 there, no extra flash cycle.
- Maxima read (bench HANDBACK FRAMCHUNK): backup write 21.05 ms, backup read 21.44 ms, entry read 15.6 ms; they sit at
  F.3 `con.routine_stall` (21 ms). The breakdown's maxima (begin 6.1 ms, set_values 6.6 ms vs medians 0.2 / 0.8) point
  to a collection inside the timed window. Hard limits unchanged (UART ring ~44 ms, reply slack ~925 ms, WDT 8.4 s).
  Brief `r5/BRIEF_FS.md` written (item 4: does the chunk path allocate); launches after T merges.

## 12.164 T handed back (777f7640) and merged: int a5c1dc93; unit FS launched (lead, 11:5x)
- T (r5/HANDBACK_T.md): 157 files +2,196/-6,512; src/ext/devices untouched; unit 5347 -> 5252 tests, tests_scripts
  6808 -> 6555; gate green at both stages but 3 tests_scripts red on doc lines (citations, level_containment,
  tunables_register); twin 327 + 13 green; coverage build 114 runs clean; wall 678 -> 677 s; imageFreeBytes 71,044.
- Lead review: the largest additions are the runner's fault vocabulary moved from launch.py (-557; --fault, --hang,
  --wifi-outcome each used by a test or CI script; --seed only by README and the chip fakes, kept: a user knob, not
  removed without the owner), the uart_comm call-site limits removed (mechanical), 17 tests moved. _REAP_ROUNDS = 2
  derived (a cancelled task ends at its next await). Merge: one conflict (scenarios :1254, P9's credit with T's
  renamed src_int), resolved; lint_direct clean (lead helper now lints fakes/ like lint.sh).
- T's slips: two grep -o outputs printed identifiers containing a filtered word (no value, per T); port-binding
  wifi_service 4x and udp_socket 1x ran while another unit held heavy.lock; single files via its own script.
- Left (R5 close list): the declared-stall drain (LISTENER_DRAIN_S/_STALL_DRAIN_S), caught listener wait_for's
  (uart_comm_hazard, ntp), _ESCALATION_WAIT_S and other twin numbers without a source, _cycle/_crc8 copies,
  device-script _REPORT copies.
- Unit FS launched (BRIEF_FS.md, from a5c1dc93): FRAM settle sleeps, F.3 silicon rows, item 4 (do the maxima carry a
  collection), T's doc list and its three red checks, the dead _record_reads. Writing units now: APT (full run), FS.

## 12.165 Bench 12:02, snapshot 58 items 2-6 (bench 5b8a96ed, 155727a8); relay 12:03 (bench 720df65d) (lead, 12:0x)
- 2 heap: BOOT_DONE free 76,656, largest 63,296; after 600 s 64,880 / 61,200; after one collect 81,552 / 61,200;
  range 61,200-82,416; imageFreeBytes 69,732 (entry under mpremote run, instrument not subtracted).
- 3 C-stack: deepest 5,636 B at FRAM _send_and_read (I2C 3,084, UART 3,060) of 7,936, all before BOOT_DONE; the
  webserver and log-store leaves not reached - re-run under item 4's load asked (12.137: near-critical margin). The
  run's RR 2 was the probe wrapper (no KeyboardInterrupt record), fixed by the bench; not firmware.
- 4 req/s: 6 readers on /status 60 s, 110 served = 1.83/s (premise 2.2); 41 refused (W60, HTTPDropped 41) with only 6
  readers: reject-when-full (owner 2026-08-12, baseline 25caf528:697) releases a slot in _serve's finally, after
  the close, so a reader's next connect can land first. Recorded; no change.
- 5 UART: idle one per 1.085 s over 601 s, 0 failures; under item 4's load one per 1.26 s, 0 failures.
- 6 WLAN switch (b): an established STA retries once a minute after an AP loss and never streaks (legacy
  python/CommonDrivers/async_connect.py:345, baseline the same): by design. Booted with the AP down: STA->AP max lag
  975 ms, AP->STA 979 ms (ap_up -> STA 483 s, the 8-min period); other windows <= 49 ms; 0 UART failures. Past
  con.uart_reply 925 ms by ~50 ms: F.3 already states the consequence (one counted transfer and a resync per
  crossing); the switch is rare (AP loss + streak, then the period). New errcount: WIFI W37/W79, NTP E67, SGP40 W35
  (boot with no AP).
- Doc facts (a)-(d) sent to FS as item 7. Relay 12:03 told the bench: FRAM (a) and the next image's re-measure,
  item 6 by design, item 4 recorded, one item 3 re-run under load, then idle. Cross-session reply to the bench is
  refused for this session (auth); the relay file is the channel.

## 12.166 APT handed back (64529e12); round 2 sent (lead, 12:1x)
- APT: the 150 s apt limit gone at every apt site; Acquire timeouts kept by the source rule; firmware's mirror bound
  = its job's timeout-minutes read from the tag (both sets on the 1 MB/s floor). Credits: the source-rule credit and
  "owner, 2026-09-26" removed (the record is the uv sync retry), "owner, 2026-10-27" kept (LN322, BACKED). Checks:
  930 touched passed, lint/mypy clean; tests_scripts 6803 passed, 1 failed (test_twin_process_spawn, "uncaught NLR":
  its run used tc-int, which lacks the qstr override; same on a5c1dc93 with tc-int - the gate uses tc-c).
- Playwright's 5-min `timeout`: playwright-core 1.63.0 ends a stalled read itself (30 s idle socket, 5 attempts) and
  apt.conf.d covers its apt part, so it only cuts a slow live install - the 12.159 pattern. Lead decision (source
  rule, lossless, net leaner): APT's option (D) - bound-s optional, floor alone when absent; the cut, its tunable and
  the bound step go. Playwright's 25.9 MB set is on the floor at any bound >= 52 s, so nothing is lost.
- APT finding (b): the download-only/install split and the outer retry lost their reason (a timeout kill reaching
  dpkg) with the limit: judged in round 2 by evidence (apt's own retries on noble, the cache's needs); back to the
  pre-audit single install unless a real case needs them. (d) the stale 15-minute figure fixed. (a) the 1800 s
  network-step limit stays: GIVEUP_3 DERIVE, decided.

## 12.167 Bench 12:23, item 3 under load (bench 268fe091); the heap side-finding; relay 12:23 (bench 795a0b19) (lead)
- C-stack under item 4's load, deepest per leaf of 7,936 B: FRAM _send_and_read 5,652 (71 %), _send_and_write 5,124,
  web _PieceWriter.flush 3,820, I2C read 3,100, UART _rx_copy 3,076, I2C writeto 2,876, log store _write 2,444. The
  load set no new maximum; ~2.3 KB margin. 39 refusals reached the log store (W60), 106 served = 1.77/s.
- Heap side-finding: under the load free fell to 16,224 B; after it the largest free block was 22,736 B with 72,960
  free, the same after a collect (before the load ~61-66 KB largest; collected free 81,552 at 600 s). So ~8.6 KB
  stays allocated and the largest block drops ~3x after one load. Against the product: a UART receive may allocate up
  to uart.max_transfer_bytes 12,192 B (J.8); the L3 headroom check requires 32,768 B after the full build (not after
  load). Plateau or creep unknown: relay 12:23 asks three 60 s loads with idle gaps (minimum of free and largest
  block during each, both after a collect after each) and one 2-reader run. Goes into the free-heap wrap-up.
- Void attempt 12:06: watchdog reset (RR 2) with the host no longer draining the CDC port: A.5's accepted console
  case (owner, 2026-09-30, 'a'), the bench's own wrapper; not firmware.

## 12.168 APT round 2 (226be25f) merged: int 146eb2e0 (lead, 12:2x)
- Playwright option (D) done: the 5-min cut, its 124 message, the bound step, its tag and Part N row gone (playwright-
  core 1.63.0: 30 s idle-socket timeout, 5 attempts; its apt calls read apt.conf.d). Rule.bound_s optional, floor
  alone without one; firmware keeps its job-limit bound.
- (b): back to the pre-audit single non-fatal update + one install with apt_options(); the download-only split and
  its outer retry gone (noble apt: 3 automatic retries since 2.3.2, growing pauses since 2.3.7; acquire-worker.cc
  1,2,4 s... capped 30 s - read on GitHub main, salsa blocked); the cache reads /var/cache/apt/archives after the
  install, so it never needed the split. run_retried back to timeout_s: float. (d) fixed (20-min job, 13x).
- Checks: 983 touched passed (7 seen red first), host mypy clean, tests_scripts 6804 passed 0 failed under
  heavy.lock with tc-c. Lead diff read: 9 files +98/-138, leaner, no new mechanism but one optional-bound branch.
  Merge clean; lint_direct on 146eb2e0 clean.
- Left: apt_options() Acquire::Retries=2 (below noble's 3; NETWORK_ATTEMPTS-derived, not changed); the derived
  mirror rate decides nothing for either set today (firmware 0.98 MB/s < 1 MB/s floor) - R5 close list. BACKLOG:404's
  owed split reading sent to FS (doc).

## 12.169 Bench 12:41: the post-load largest block, three 6-reader loads and one 2-reader load (lead, 12:4x)
- After each 120 s idle + one collect: largest block 23,040 -> 20,192 -> 18,336 B after 6-reader loads 1-3, then
  55,120 B after a 2-reader load; free flat 82,224 / 82,208 / 82,176 / 82,176 B: no leak, placement only. During the
  6-reader loads (1 s samples): largest block min 11,968 / 11,664 / 11,424 B, free min 15,728 / 15,216 / 16,176 B;
  2-reader load: largest min 18,336 (its start), free min 41,824. Before any load 64-66 KB. Served 113/108/108,
  refused 44/41/43 (+128 W60), 2 readers 100 served 0 refused. No MemoryError / allocation-failed text. NTP +1 E71.
  Instrument (wrapper, 1 s sampler, a mem_info heap walk each second) allocates and is not subtracted.
- Margin: the worst-case load's minimum largest block (11.4 KB) sits just under the UART receive cap
  (uart.max_transfer_bytes 12,192 B, J.8), but dev's real transfers are tens of bytes (banner "uart-crossover", echo
  "crossing"); the web path's largest allocation is one piece (J/H: <= chunk_bytes). Not critical for any current
  path; at the cap for a peer sending a near-maximal train under a 6-reader load. Each heavy load leaves the largest
  block smaller until a lighter one re-places (no plateau within three loads).
- Route: the free-heap wrap-up (owner: at the end), with this evidence; the last round's two-image GC proof runs the
  same pattern (3 x 6 readers + 1 x 2 readers, collect after each) on both images. No relay needed now: the bench
  idles on snapshot 58 until the next image relay (12:03).

## 12.170 FS reviewed and merged; T's reap round limit cut a probe's cleanup (lead, 2026-11-10 13:4x)
- FS 50004d8b read whole (code, tests, filtered SPEC diff): src -18 lines, the six FRAM settles and SPIDevice's two go
  (datasheet tCSU/tCSH 10 ns, tD 40/60 ns; MB85RS2MTA p.15, MB85RS64V p.14); no wire/CS/stored byte changes. The 5 ms
  entry budget it dropped was audit-added (U16, 2977c4e0, 2026-10-07; absent at 25caf528) and failed every silicon
  run: recorded, not judged, under the owner's 11:25:20 "option a". Merged clean: int 5621a24d.
- FS's 32768 red (test_sensortask[grkizi], "the reap could not end ... _read_loop") is NOT pre-existing: T's
  _REAP_ROUNDS = 2 (agent, 2026-11-10) cut a cancelled task whose finally awaits I2CDevice._probe_for_device()'s second
  100 ms settle while a stream wait held each round to 1 ms. Reproduced deterministically (reap_probe2.py). No fixed
  round count separates a timed cleanup from a task that runs on after cancellation, and the owner's direction leaves
  the hang to the per-file timeout: the reap now runs until every cancelled task ended or nothing else can run (a task
  nothing can wake is still named at once). The round-limit self-test goes; a three-cleanup test replaces it (red on
  the old reap, green on the new). grkizi file 5/5 at 32768; probe ends; harness 17/17 at both stages. int 651af010.
- con.routine_stall (FS: "back to its maker"): settled by evidence, no change. The row and stall.fram_entry state it:
  one FRAM operation alone stays under 21 ms, with a collection inside up to ~34 ms, inside con.uart_reply (925 ms on
  dev). J.6's floor (2 x poll_wait + poll_idle + 21 ms) is a configuration minimum, already crossed by stall.i2c_transfer
  and stall.flash_program by design; no device configures near it. Not near a critical margin.
- FS's lean candidate (CS helpers' heap frames, ~4 KB churn per entry): declined. mpy-tool preludes (armv6m): the
  read/write helpers are n_state 11 + 1 exc = 56 B, _send_command 52 B, against 44 B; dropping the two local aliases
  brings only _send_command under it (the try/finally that deasserts CS on an error keeps the others at 48 B). Gain
  ~3 collections over a 19-entry ResetErrors; a restructure for that is not lean. The F.3 row states the behaviour.
- FS's doc findings done in 651af010: C.3.1 SPI init once per device (not per CS cycle); stall.crc frozen engine
  1.31 ms / 264 B (bench FRAMCHUNK, snapshot 58 image, med of 30, max 1.56 ms); harness per-call cost re-measured
  (2 us at -1, 2-3 us at 32768, 0 B; medians of 501); twin typecheck.ini header; BACKLOG serving-rate item gone
  (1.83 req/s, H.7: no limit moves). The wlan-switch BACKLOG row is the role-reversal item, partly hidden by the
  filter and wider than the timing: left as is.
- Checks on 651af010: lint_direct rc 0; mypy main 283 / host 309 / twin 58 files clean; readers 703 passed. Combined
  gate (tc-c) running under heavy.lock (lead).

## 12.171 CS (close status) back: 154 items, 73 distinct OPEN, no firmware item open (lead, 14:1x)
- S/u35r/r5/CLOSE_STATUS.md + .tsv (read-only on 651af010). DONE 71, OPEN 77 rows (73 distinct; 36 bench-last-round,
  16 test, 12 final-report, 11 docs, 2 build, firmware 0), OWNER 6. New: N01, audit/sweeps/open_findings.md's 73
  open/partly closed rows never inventoried (PLAN R0 input to OR5.a): one disposition pass.
- Largest open items: P09 the D.15 order beyond src/ (~150 files; owner 10-27 "Option d", OR96 not the unit tests);
  B01 the mypy Any baselines (7 modules, owner 09-28 "do it in this audit"); U02 import-placement _PENDING 68 + PLC0415
  scope entries (U37.02; the 11-03 (i) permanent-list ruling covers only the citation and vocabulary checks, read at
  its record); the last round (two images x full flash + bench tiers, 25 never-run round-1 steps, 6 re-runs).
- Owner items, lead's reading: O1 (mirror rate decides nothing) keep, no change, final report; O2 (no-caller features)
  keep under the 18:30:08 rule, listed in the final report; O4 (65 agent decisions 11-06..11-10) reviewed by topic at
  the phase stop per rule 4.1.9 (final report); O6 chroot legs: (a) reused chroots with scratch in RAM, which the
  owner's 11-07 14:46:59 words ("better style yes, but no blocker") and task #68's method meet. Left for the owner, one
  at a time: O5 (release number 2.0, before W2's version change) and O3 (AmbPres PUT-half instrument: the Interface
  Description 1.4.1 says the continuous-measurement status, interval (1.4.3) and altitude persist in NVM, nothing for
  the ambient pressure argument; so the twin's persistence model has no source).
- Cost forecast revised: W1 (incl. P09, B01, U02, twin items) ~3-5 points, W2 ~1, N01 ~1, re-verification and image
  prep ~1-2, bench last round ~3-4, W3 final report ~1.5, D ~1, lead ~2: ~14-18 points -> ~54-58 % at the finish
  (13:43 answer said 47-50 %). Put to the owner before starting the units, as promised at 13:43.

## 12.172 gate59's one red: scenarios[dev] a_full_ceiling_of_concurrent_request_bodies at -1 (lead, 15:1x)
- gate59 (int 651af010, tc-c rebuilt 13:51 after APT changed setup_toolchain.py; the first gate attempt died in the
  namespace on the rebuild's git fetch): 32768 stage, twin suite and harness at both stages green; -1 stage one red:
  dev's six concurrent PUT /system writes all TimeoutError at 15 s (_REQUEST_TIMEOUT_S = the product's outer cap since
  T; 10 s before), 25.9 s against ~6 s in every gate since 11-09 (fsyncG..fs_e, 12 runs) and FS's gate on the same
  src/ and twin code. 6/6 alone at 5.8 s. dev's whole scenario set took 634 s against 661 s at 09:01: no general
  slowdown. The run was the first heavy run after the 13:5x container restart. Twin logs lost (test.sh's EXIT trap
  removes results_dir). Two hand repros under the four-device load refused to start (port 53's lock passes only
  through test.sh's owner chain). Rerun of the -1 stage running with TMPDIR in scratch and a watcher copying the dev
  scenario logs (S/u35/lead/rerun_e/); one rerun only, a second failure is real.
- Rerun (15:2x-15:5x, same tree, same tc-c, TMPDIR in scratch, dev logs kept at S/u35/lead/rerun_e/keep): -1 stage
  PASS, 5252 passed 0 failed; the scenario 5.8 s on dev. Unreproduced: identical src/ and twin code passed FS's gate,
  12 gates since 11-09, 6/6 alone and this rerun; it failed once, in the first heavy run after the container restart,
  its twin log lost. No cause is claimed. CI on snapshot 59 runs it again; a second failure anywhere is real.

## 12.173 cov59 green; snapshot 59 pushed (lead, 16:0x)
- cov59 (every tests/ file changed since snapshot 58, 59 files, 74 jobs with the per-device ones) under build-settrace:
  all rc 0, no MemoryError text. heavy.lock released to the units.
- Snapshot 59 a771238b (parent 910a0a62, tree = int 651af010 + records; SNAP_EXCLUDE + ftmp_apt ftmp_fs ftmp_cs
  ftmp_w1a ftmp_w2): the diff's PAT matches are 3, all 8-character hex (commit ids), none a withheld prefix. Pushed to
  claude/whole-project-audit-plan (hundertvolt/sensors#107); CI pending; a771238b is the next PARENT once green.

## 12.174 W2 merged (int 3bee346e); the releases made during execution become unit PIN (lead, 16:2x)
- W2 d7ac6018 read (golden tests compare against committed fixtures and name the regenerate command; README Release
  section, current fact, each fix with its test; BACKLOG P08, B40 (bootloader 2, harness hard reset 21), N05, N03).
  Merged clean: int 3bee346e. P05 (version) waits for the owner's number (asked 15:0x).
- W2's one red (test_twin_process_spawn "uncaught NLR") was S/tc-int, built from an older micropython_overrides.py;
  passes on S/tc-c. common_r1's four tc-int paths now name tc-c (old copy at S/u35/lead/common_r1_before_tcc.md).
- U01 (W2): MicroPython v1.29.0 and every firmware-side pin are newest; dev tools moved upstream (mypy 2.4.1, ruff
  0.17.4, pytest 9.2.0, coverage 7.17.2, zizmor 1.32.0, types-pyserial, uv 0.13.7, Node 26 LTS, the npm set with
  stylelint 18 and its config 41 as majors). A.SDEP.25 (OR129.a (1), owner 09-30): a new release becomes its family's
  action, the close's re-verification passes its gate; under the owner's 14:57:50 "(A), finish as planned" unit PIN
  (BRIEF_PIN.md) moves them, own venv and Node, beside W1a. Not an image change.
- Snapshot 59 CI green: run 42845410992, 28/28 jobs success (unit-tests with the dev scenarios at -1, the shipped
  threshold, coverage, twin e2e 8, firmware 4, web 6, lint 5); run 42845393906 cancelled by the newer push's
  concurrency group (no job ran). a771238b is the next PARENT. 12.172's scenario passed on CI too.

## 12.175 PIN merged (int 64b719c2); disk freed (lead, 16:4x)
- PIN 4242b1fd read: pins only (mypy 2.4.1, ruff 0.17.4, pytest 9.2.0, coverage 7.17.2, zizmor 1.32.0, types-pyserial,
  uv 0.13.7, Node 26.13.0 LTS with engines/devEngines >=26 <27, the npm set incl. stylelint 18 / config 41) plus the four
  ICN001 aliases ruff 0.17 demands (`import datetime as dt`); package-lock regenerated (vitest 5.1.0's peers). PIN's
  gate at -1 green on its own venv and Node 26; 32768, twin and CI owed (the re-verification pass). npm audit: 4
  moderate in eslint's minimatch chain, dev-only, no fixed release in range: recorded for the final report.
  Merged clean: int 64b719c2.
- Disk was 2.3 GB free (run.sh refuses below 3 GB): 14 merged, clean unit worktrees removed by literal path (each
  head an ancestor of int, no tracked change): fs w2 apt t p9 g c mfs fsync ub crceng weblog bchain bfix -> 5.8 GB.
  The owner-paused worktrees untouched.
- After W1a merges: the shared venv re-synced to the new lock (network, outside the namespace), run.sh's NODE to
  S/shared/node-v26.13.0-linux-x64 (moved there from ftmp_pin), then lint/mypy/gate on the combined tree.

### 12.176 P05 done: release version 2.0 (owner 16:40:55), int 5b8c3446 (2026-11-10)
Owner: "It's 2.0". buildgen/version.py both constants "2.0"; mockdata/samples.json build entry "2.0"; SPEC L.7 one
paragraph (release = tagged merge into main, first is 2.0, owner 2026-11-10); README Release's first sentence names 2.0.
Not changed: test_buildgen_version.py (its examples are format cases, no value pin needed), tests/test_asy_webserver_service.py
fixtures (arbitrary data). 6 tests_scripts files that read the sites: 492 passed. O5 closed; O3 is the last owner question.

### 12.177 O3 closed by the owner (16:47:07): SCD30 keeps every setting through a power cut; int 77a4e1e8 (2026-11-10)
Owner: "The SCD30 stores everything, including the "Go" for continuous measurements. It just starts as it ended,
when power is back. Field proven many times." No instrument. Removed: BACKLOG's owed item (12 lines), and from
tests_hardware/manual/manual_persistence.py the pressure reads, the `_served_after_power` amb_before parameter (4
callers) and `_boot_sends_continuous_measurement` (an 11-line AST walker over src/, added 2026-10-15 in U26, sole
user this question), `import ast` with it. Stated: SPEC M.2 NVM paragraph, twin fidelity row (accepted, owner's
words) and SCD30-persistence note, driver comment. ruff, host mypy, 8 tests_scripts files (809 passed). Every owner
item is now settled (O3/O5 by the owner, O1/O2/O4/O6 by evidence, listed in the final report). Row B29 DONE.

### 12.178 W1a merged (int 20629434) + two loose ends (886f8af0); tools moved to the new pins; gate60 started; W1b out (2026-11-10)
Reviewed b5f2978c (66 files, +535/-795): Any typed (type-only unions, generic _CallLog), _PENDING/regenerate gone,
bounds removed with probes, helpers shared, twin SGP40 528 ms model, F3 root cause = twin random walk (not src). The
smoke's JS device picker mirrors _devices.sh as derivedDevices() already mirrors _devices.py (pre-existing pattern,
kept). Merge auto-clean. Lead follow-ups (886f8af0): H03 settled by naming: _ESCALATION_WAIT_S states the measured
escalation (dev 15-20 s) and that it is a hang backstop (CLAUDE.md: no hanging tests); per-device derivation would add
a mechanism with no need. The off-list caught wait_for(10 s)+silent cancel in test_asy_uart_comm's heap-flat train
test -> plain await (listener ends inside the protocol reply timeout; 201/201 at -1 and 32768); _STEP_BOUND_S gone.
Environment: uv 0.13.7 moved to S/shared/uvenv-0.13.7 (from ftmp_pin); shared venv synced --locked (ruff 0.17.4, mypy
2.4.1, pytest 9.2.0, coverage 7.17.2, zizmor 1.32.0 = pins); int node_modules symlink removed, npm ci with Node 26
(192 packages, int-local); run.sh and tcc_setup.sh point at the new uv/Node (run_before_pin.sh kept). Checks c60:
lint_direct 0 (ruff 0.17.4 clean, zizmor clean), mypy 285/309/58 clean, readers 99 passed. Gate60 (lock lead) running.
W1b briefed (BRIEF_W1B.md: D.15 by hand outside src/, check widened, js by review, empty _PENDING_ASSERTS goes).
Open from W1a: (c) uart_ring_under_concurrent_load 32768 1/8 on W1a's tree - to root-cause, not a flake.

## 12.179 gate60 green on int 886f8af0; cov60 running; finding (c) read (lead, 18:4x)
- gate60: test_e 0, test_f 0, twin -1 suite/harness 0/0, twin 32768 suite/harness 0/0, npm 0. Lock released.
- cov60: every tests/ file changed since snapshot 59's tree (651af010) plus every importer of a changed helper
  (machine, _crc8, _notification_cycle, _uart_comm_harness, ...): 58 files, under build-settrace (lock lead).
- (c) read: scripts/_digital_twin_scenarios.py _uart_load(): ceiling()+1 hammer threads retry a refusal at once
  (_status_of returns "rejected" and loops); the one flusher sleeps _LINE_POLL_S (0.05 s) after each refusal. A freed
  slot is retaken by a hammer within microseconds, so the flusher only lands when it happens to try in that instant;
  a window where it never does gives puts == [] (the failure text). Test-side asymmetry, not src/: a client at the
  ceiling that polls slower than the ones holding it loses, as on any server. Planned check: instrument in the
  throwaway worktree wt-uload (puts and refusal counts, never committed), runs at 32768 before and after dropping the
  sleep (retry at once, as the hammers do). _LINE_POLL_S stays (5 other users).
- L07's "sgp40 serial read (no script found)" is DONE by evidence: the bench campaign's
  tests_hardware/device_scripts/sgp40_conformance_probe.py (via flash/test_chip_conformance.py) read all three words
  on the dev chip on 2026-10-28 18:00:39 (hw_handover/HANDBACK.md: A01_serial word 0 = 0x0000, A02_serial_stable=yes).
  No new script. Owed: src/asy_sgp40_driver.py:682-683's comment "The dev board's word 0 is still to be recorded on
  real hardware" is stale -> "and the dev board reads 0x0000 (bench, 2026-10-28)" (comment only; lead, after cov60).

## 12.180 RP hand-back read and checked (lead, 19:1x)
- r5/PROBES_RECHECK.md: the nine 11-04 probes byte-identical on the bench branch (d6bd2d45). OK: boot_stretch_final
  (12a; e1958815 changes its figures, not its code), dns_idle_poll + host_dns_query_timing (12c), host_reset_errors
  (12d), general_call_per_chip (12e), bmp3xx probe (16b), country_scan (13), long_fram (11), fram_raw_dump (1).
  STALE: ring_peak_final.py:33 comment "SCD30 reset alone waits 2.5 s" -> 2 s (2001 ms since 39e18d2a; its 15 s wait
  covers it). OBSOLETE: held_sda_reset (12f): ba671e7a put it in flash/test_bus_concurrency.py:300-337 (step 4b runs
  it; owner 11-06 "Option A, I have no oscilloscope at hand"); round1.sh row 12f and held_sda() go. Both ride the
  last-round relay (bench branch). F4 (peak=0 for a ring never up) not taken: no failure, no new mechanism.
- F1 checked, real: SPECIFICATION.md:932, :933, :12170, :12171 still name run_setups()'s first gc.collect() and
  start_tasks()' collects (N + 1); src/ has none since e1958815 (git grep: no gc.collect in src/ or buildgen/), and
  SPEC :909 and :9277-9278 already say so. Lead docs fix: 4 lines.
- F2 checked, real: BACKLOG.md:282-290 (bench ResetErrors budget) says "the concurrent reset the owner chose (owner,
  2026-09-26)"; the owner's later go (2026-11-07 17:57:27, "Go to all", item (1) error-log reset sequential, 12.107)
  made it one after another (f3886cb0). Lead docs fix; the code comment (asy_webserver_service.py:815) and SPEC A.8
  :1175 credit it "(agent, 2026-11-07)": the decision is the owner's go -> "(owner, 2026-11-07)".
- F3 (bench src older than int) is the planned last-round image push.
- Slip (lead, 19:0x): looking for the 16:35 package table, a grep's file list included the session transcript under
  /root/.claude/ (piped to head -0: nothing printed, nothing read into context). Rule: never open /root/.claude/. The
  16:35 table was not kept in the records; from now on the package list is the fixed 7-row list of 19:00 (NEXT.md).

## 12.181 cov60 green; snapshot 60 pushed (lead, 19:1x)
- cov60: 58 files, 79 jobs (per-device ones included) under build-settrace: all rc 0, no MemoryError text. Lock
  released (W1b waits for it).
- Snapshot 60 37216f41 (parent a771238b, tree = int 886f8af0 + records; SNAP_EXCLUDE + ftmp_pin ftmp_w1b ftmp_uload
  ftmp_rp): PAT matches in the added lines 0. Pushed to claude/whole-project-audit-plan; CI pending; 37216f41 is the
  next PARENT once green.

## 12.182 W1b reviewed and merged; docs batch committed (lead, 19:3x)
- W1b 3e35f5c9 (HANDBACK_W1B.md): 69 files reordered by hand (buildgen 13, digital_twin 2, scripts 13, toolchain 2,
  tests 18, tests_hardware 11, tests_scripts 10; js/ already in order). Lead's own AST check (u35/lead/ast_moves.py,
  module and class level, same-name pairs as multisets): 66 files identical; 3 differ only by method moves inside
  nested classes (tests/_protocols.py in TYPE_CHECKING, two test-local fakes), read by hand; test_code_conventions.py
  carries the intended change. Comments: one topical heading gone (driver_registry.py:95-96, cached-by-text note), its
  content visible in each function's lru_cache + text parameter + tuple return. Check: one condition (_TESTS_THEMSELVES)
  and one scope test; the empty _PENDING_ASSERTS, its loader and pin test gone; Module.generated now "build/" (same
  set for the fixture). Exemption of tests_hardware/manual/manual_*.py (5 files: pytest runs them in definition order
  = the manual session's steps) and tests/_*_scenarios.py (2: the scenarios are the tests) follows OR96 and the
  no-behaviour-change rule; credited (agent, 2026-11-10), goes to O4's list.
- W1b's tc-c incident: its test.sh on tc-c hit the toolchain-record staleness (setup_toolchain.py and
  micropython_overrides.py reordered change the input hashes), setup deleted tc-c's record and failed at the fetch;
  binaries untouched; it restored the record by hand at 19:08. Lead: re-record tc-c offline with the merged tree
  (setup_toolchain.py test --toolchain-dir) before the next gate; the hand restore is superseded by it.
- W1b slip: one early unfiltered grep printed a fake test SSID literal (tests/_sensortask_scenarios.py), not a secret.
  W1b finding: common_r1's MICROPYPATH lacked fakes -> fixed (common_r1.md:53, as test.sh's unit path).
- Lead: docs batch cf5724ae (12.180's F1/F2 + credits + SGP40 comment; 882 doc/credit/comment tests passed), merge
  w1b f0d59a75 (auto-clean, SPEC both sides).
- Snapshot 60 37216f41 CI green (run 42881699131, success). Next PARENT = 37216f41.

## 12.183 Finding (c) root-caused and fixed in the test; tc-c re-recorded; gate61 running (lead, 19:5x)
- Measured in wt-uload (scratch instrument, never committed), dev, gc 32768, 6 runs each:
  before (flusher sleeps 50 ms after a refusal): 2-4 PUTs per 20 s window, 0 in run 5's maximum-stall window (rc 1,
  "config PUTs under load answered []"); retry at once (my first hypothesis, asymmetric retry): 0 PUTs in 6 of 6, about
  675 refusals each - hypothesis refuted. Per-thread served counts [9, 9, 9, 9, 8, 8, 0] (2 runs): the six hammers
  first served keep their slots the whole window - a served client's reconnect retakes its own slot before any
  refused one's - so the seventh hammer and the flusher are never served; the twin log's 1401 "Connection refused at
  the ceiling" are real ceiling refusals. src/ refuses fairly (reject-when-full); the cause is the test's load design.
- Fix (int bfa240fa, scripts/_digital_twin_scenarios.py _uart_load, +15/-5): the flusher starts first, its first PUT
  lands, it keeps its slot with /status between its half-second PUTs and retries a refusal at once; the hammers start
  after (holding.wait bounded by the existing _UART_LOAD_REQUEST_S). 6 of 6 runs: 8 and 5 PUTs per window, two
  hammers refused throughout (the ceiling still exceeded, the refusal FRAM entries still written). c61: lint 0, mypy
  285/309/58 clean, 1031 reader tests passed.
- tc-c re-recorded offline after W1b's toolchain/ reorder (setup_toolchain.py test, rc 0, 91 s; the two "warning:"
  lines are uv's own notices). tests_hardware --collect-only: 217/250 (33 deselected), rc 0.
- Package 4 = gate61 (test.sh -1 and 32768, dev twin both stages, npm) + snapshot 61, whose CI runs coverage, the twin
  on every device and every device's firmware build (ci.yml devices matrix): the re-verification without duplicating
  CI locally.

## 12.184 LR draft read; the last round's relay prepared (lead, 20:2x)
- r5/LASTROUND_DRAFT.md (agent, read-only): every CLOSE_STATUS bench-last-round row mapped to a runner step. Missing
  in round1.sh: 5gh/5h (12.169's heap loads on both images, 2 rows + 8 lines) and 12g (L04's FRAM chunk re-measure,
  12f's row + 1 line); 12f and held_sda() go (PROBES_RECHECK); ring_peak_final.py:33 "2.5 s" -> "2 s". Diff kept at
  r5/ftmp_lr/round1_u1.diff (not applied).
- Lead settled the draft's disagreements by "current docs win": M1 before 7f (BACKLOG:35-40: M1 writes down the rig
  geometry S3b depends on; HANDOVER's day order is older); rings 512 B (dev.toml); no AmbPres read in the power cut
  (owner 16:47:07); current line numbers in the relay. 4a stays beside the chroot legs (4a is the runner's own
  lower-level prerequisite, ok() maps rc 4 on it; the legs verify a clean OS). BACKLOG:64-66 damaged-config boot: no
  instrument; W3 records it as derived (one config write's stall on a 0.93 s setup batch vs the 8 s watchdog).
- Relay text: u35/lead/lastround/relay.txt (29 lines, shas as placeholders; PAT 0). Goes to the owner first (one
  question: go, wear included or not), then to the bench after gate61 + snapshot 61 CI.
- gate61: test_e 0, test_f 0 so far.
- gate61 stopped by the harness's 30 min background limit (lead's slip: started without a timeout) after test_e 0 and
  test_f 0, inside twin -1 suite; no process left. The rest re-run as gate61b (u35/lead/gate_rest.sh: twin suite and
  harness at both stages, npm) with a 2 h limit, same tree bfa240fa, lock lead.
- Owner 20:37:10: wear accepted if the code behind the wear steps is final. Wear steps (round1.sh): 7f/7b persistence
  writes, SCD30 extra writes, NeoPixel sweep (config_manager, SCD30 NVM setters, notification/NeoPixel, the REST PUT
  path); 8f/8b flash cycles (reflash smoke, CRC16 image and back, lwIP control image); 10b; 15 the tick-offset image.
  Nothing planned changes that code (CLOSE_STATUS firmware 0; W3 is docs, records, twin; D merges and tags; no pin
  moves). Two unplanned paths only: a red elsewhere in the round, and H34 if 5gh/5h show the post-load largest block
  shrinking toward the 11.4 KB a UART receive needs (snapshot 58: 23.0/20.2/18.3 KB, recovering at 2 readers) - a fix
  there would touch the webserver path the persistence writes go through. Relay item i now runs the wear last: after
  a-h green, M1 done, and the lead's cleared: line, given after every result is read and H34 settled.
- Bench day-5 note (cross-session, 20:4x): snapshot 58 idle and serving; hand-back fc4e5708 (HANDBACK.md +7 only);
  no probe after 12:38; SysUptime 29,329 s, ResetReason 21, STA; errcount unchanged since the heap load series (NTP 2,
  SGP40 27, WEBSERVER 208, WIFI 26); flash cycles today 1. Bench head for the relay build: fc4e5708 (not bc53cdfa).
  The draft's round1.sh diff is against bc53cdfa; fc4e5708 touches HANDBACK.md only, so it applies unchanged.
- gate61 green on int bfa240fa: test_e 0, test_f 0 (gate61), twin -1 suite/harness 0/0, twin 32768 suite/harness 0/0,
  npm 0 (gate61b, 1,671 s). The suite outputs' 40 marker lines are its own "log carries none of" OK lines (as gate60).
  Lock released.
- Snapshot 61 4a0f1b76 (parent 37216f41, tree = int bfa240fa + records; SNAP_EXCLUDE + ftmp_lr): PAT matches in the
  added lines 0. Pushed; its CI is the rest of the re-verification (coverage, twin on every device, every firmware
  build, web). Next PARENT once green: 4a0f1b76.

## 12.185 Owner (21:23:14): last round option (a), wear last; bench commits prepared (lead, 21:3x)
- C1 609e4606 = bench_commit.sh bfa240fa on fc4e5708 (outside audit/ = int, audit/ = the bench's; both halves checked).
- C2 7cfeee71 on C1: round1.sh per ftmp_lr/round1_u1.diff (5gh, 5h heap loads on both images; 12g FRAM chunk
  re-measure; 12f and held_sda() gone; 304 lines, bash -n clean, mode 100644 kept - a first build with 100755 was
  discarded unpushed), ring_peak_final.py:33 "2 s" (the lead's scratch copy synced). The new steps' probes exist on
  the branch (probes_20261110: snap58_heap_loads.py with the exact gc.threshold(32768) line and print("DONE"),
  heap_loads_host.py with its SCRIPT line, heap_loads_summary.py, fram_chunk_timing_frozen.py with "FRAMCHUNK done");
  the heap probe's names exist at bfa240fa (write_reset_record, RR_INTERRUPTED 21, SystemService.boot_phase,
  sensortask_dev.main(*, watchdog)); src/ since snapshot 58 changed only the CS settles, comments and the version.
- Relay commit C3 and the fast-forward push after snapshot 61's CI (run 42899683439) is green.

## 12.186 Owner asked (21:26:30) whether everything now waits on the bench: no - W3 split (lead, 21:4x)
- Done now: H36 (int's six untracked build_*.out deleted, literal paths; figures already in the records); CLAUDE.md:688
  "each pass's shrinking per-module baseline is BACKLOG.md's open item" -> "no pass exempts a module" (int 51c9c75f;
  matches SPEC :2899 and W1a's removal).
- W3a (read-only, BRIEF_W3A.md) out: N01/N02 terminal states, O4's agent-credit list 11-06..11-10, the load entries
  re-read, D's do-not-reopen check, the final report's draft with <BENCH>/<D> placeholders.
- W3b after the bench: U05 + X1 + B49 (BACKLOG's owed list rewritten to what the round leaves), F.3/Part N figures
  (L04, L05), L06 twin corrections, H34, B27's bench half, U17 (needs the final coverage run), P01's second pass, D.

## 12.187 Snapshot 61 CI green; the last round's relay pushed (lead, 21:3x)
- Snapshot 61 4a0f1b76 CI green (run 42899683439): with gate61 the first re-verification pass is green (P01 pass 1:
  lint, 3 mypy, test.sh -1 and 32768, coverage, twin on every device, every firmware build, web, tests_hardware
  collect). Next PARENT = 4a0f1b76.
- Bench branch fast-forward fc4e5708 -> 609e4606 (final tree) -> 7cfeee71 (runner + probe) -> c972ea2b (relay
  21:29 UTC, stamped from date -u; 31 lines; PAT matches in the pushed lines 3, all 8-char hex commit ids, 0 withheld).
  Int head 51c9c75f differs from the bench's tree only by CLAUDE.md:688 (docs).
- Wear: the cleared: line goes into WEAR.txt only after every a-h result is read and H34 settled (owner 20:37:10).

## 12.188 Owner asked (21:32:13) about the PR's ~2M added lines and their cleanup (lead, 21:3x)
- Measured snapshot 61 4a0f1b76 against main's merge base 798e5a72 (numstat, ':!arduino'): +1,848,790 / -165,623.
  audit/ +1,639,270 (89 %; 14,817 files: artefacts/evidence 945,752, sweeps and index JSON ~450k, plans/harvest/
  consolidation ~245k). Outside audit/ +209,520 / -165,623: tests/ +71,330/-32,368, tests_scripts/ +52,486/-5,727,
  tests_hardware/ +22,630/-10,195, tests_js/ +8,501/-1,504, src/ +10,199/-8,673, root files +15,917/-7,829 (the
  plan file among them), datasheets/ -87,264 (a tree in main, a submodule here).
- The stage is D (PLAN; CLOSE_STATUS S05, S06): the last commit holding audit/ tagged and named in the final report,
  then audit/ and PROJECT_AUDIT_PLAN.md deleted, one merge into main as v2.0 with the owner's agreement. After D the PR
  reads about +210k / -166k. A merge keeps the history and the tag keeps audit/, so the repository's size keeps them.

## 12.189 Owner asked (21:34:58) whether all audit evidence survives D in git history: two gaps found (lead, 21:4x)
- Kept: everything under audit/ at the last snapshot (the scratch records are in it: FINDINGS.md and the owner record
  among 3 matches), reachable from the tag D names and from main's history after a normal merge.
- Gap 1: the bench branch's evidence is not on the audit branch: 112 files under audit/ only there (its HANDBACK.md,
  LEAD_RELAY.md, probes, logs), and its head c972ea2b is not in the audit branch's history.
- Gap 2: snapshot.sh commits the int tree with the previous snapshot as the only parent, so no int commit is on any
  remote branch (checked: bfa240fa, f3886cb0, e1958815, 20629434 on none); 541 commits reachable from int 51c9c75f are
  not reachable from snapshot 61. The records cite them by id; they exist only in this container.
- Proposed (to the owner): D also tags the bench head and the int head (or folds the bench's audit/ files into the
  last snapshot), all named in the final report; and the int history pushed now to a backup ref, since a container
  loss would lose it before D (the trees are safe in the snapshots, the commits are not).
- Owner 21:38:00 chose (a), backup now. The tag push (refs/tags/u35-int-backup) was refused twice with HTTP 403 by
  this session's git access (branch pushes to claude/* work), so the backup is a branch: claude/u35-int-backup at
  9d31adf2, a [skip ci] wrapper commit whose parent is int 51c9c75f and whose tree is the same (no CI run). Pre-push
  scan of the 5,816 newly published objects (541 commits, 3,279 blobs): PAT 3,124 = 1,543 IPv4-like + 1,581 8-char
  hex, 0 other, 0 withheld. Each later update: a new wrapper with parents (new int head, previous wrapper), so the
  branch only fast-forwards.
- Consequence for D: this session cannot create tags. D's archive refs become branches (or the owner tags them).
- Owner 21:55:27: D's archive refs are branches (option (i)): claude/u35-audit-archive (the audit branch's last
  commit holding audit/), claude/u35-bench-campaign (kept, never deleted), claude/u35-int-backup (its final update at
  D); all three named in the final report. Replaces PLAN D's "tagged" and CLOSE_STATUS S06's tag (this session's git
  access refuses tags, 12.189).

## 12.190 W3a handed back; verify_present() restored before the last round; two manual pulls join step j (lead, 22:2x)
- W3a (HANDBACK_W3A.md; W3A/N01.tsv, O4.tsv, LOAD.md, DNR.md; REPORT_DRAFT.md saved by the lead, the harness having
  refused the agent's write): N01 73 rows DONE 35 / PLACED 13 / TO PLACE 9 / DROPPED 8 / BENCH 7 / OWNER 1 (+5 unfilled:
  DONE 3, TO PLACE 2); 12 rows U24 closed at aa3530f7 still read open; N02 = DECREV 4's ninth place, done (87c14760),
  two record lines owed before the archive commit. O4 64 credits / 62 lines at 51c9c75f, 62 / 60 at eb8a214e. LOAD:
  LD 52 cells 43 right / 8 corrected / 1 owed (captive-DNS flood on silicon); R3 13: 8 / 5; OR49.a (3) 6 entries.
  DNR 271: 244 current, 6 superseded, 5 moot, 1 contradicted (V14), 11 not located, 4 filtered.
- V14: 1547690d (lead's merge, 2026-11-09 23:28) removed FRAM_SPI.verify_present() with the driver's lock, credited
  "(agent, 2026-11-09)" under the 20:43:39 direction - after the owner's 18:30:08 rule (ask before removing a function
  that is merely unused) and against the 2026-09-26 ruling that keeps it. A slip of mine: decided topic reversed
  without the ask. Not re-asked (decided): restored as a plain synchronous re-probe (int eb8a214e: 7 lines, 3 tests,
  the pinning assert in test_get_and_set_values_are_plain_calls_with_no_session_to_take narrowed to __aenter__,
  SPEC's FRAM API paragraph and initialized-flag line). The test comment at test_asy_webserver_service.py:1283 now
  credits the owner (2026-11-07), as src/asy_webserver_service.py:815 does.
- Checks at eb8a214e: the FRAM file 77/77 at -1, 32768 and under settrace, no allocation-failure text; the webserver
  file 225/225 at both stages; lint clean; the three mypy passes clean; 20 doc readers 1088 passed. gate62 (full unit
  gate) running as confirmation.
- The image changed after the 21:29 relay: bench C4 f02afce1 (main line eb8a214e), relay 22:19 C5 43834938 (pushed):
  every image from this head; a control or 3g-5h result taken on 7cfeee71 is redone. Step j gains
  manual_bus_electrical.py's test_fram_unplug_replug_recovery and test_uart_crossover_pull_recovery (OF-60, OF-70;
  owner's hands, no flash or NVM write). int backup 3f0933a2.
- Owed to W3b: OF-193 (_unix_port.sh check misses a stale binary; FINDINGS 12.174 is its evidence) - fix or one
  BACKLOG line; OF-239 (disallow_any_unimported) - to the owner at the phase stop with O4; CLOSE_STATUS P07's premise
  wrong: the load cells go into audit/b3/load.md at the next snapshot (scratch is not archived); the 12 stale "open"
  rows and N02's two record lines corrected; DNR's 11 not-located and 4 filtered rows read.
- Slip (W3a): one git grep ran unfiltered and printed a test function name holding a filtered word
  (tests/test_asy_wifi_service.py:2027); no secret value.
- Addendum (23:10): gate62 on eb8a214e green on every step (test.sh e and f, twin -1/32768 suite and harness, npm);
  allocation-failure text only in the twin checker's own "log carries none of" lines (40 each, as gate61b).
