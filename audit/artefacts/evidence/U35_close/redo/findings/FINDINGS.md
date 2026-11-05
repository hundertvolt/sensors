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
