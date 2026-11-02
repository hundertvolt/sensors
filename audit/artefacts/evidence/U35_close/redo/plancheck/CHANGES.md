# Plan check: the change list (lead, 2026-10-28)

The owner asked: "Revise our current plans, so they do not contain such glitches anymore. The claim falsification
check agent scan seems reasonable, too. Add this as a final verification and adapt the run counts accordingly."
Every row of PLAN.md was checked: where it is, what governs it, who uses it, what the platform does, how big it is.
Evidence per row: `R1.md` (the batches), `R0R2_rest.md` (R0, R2, the remaining work, the appendices, the estimates).
The plan before the check: `PLAN_before.md`.

## Counts
- R1's batch table: 68 items checked, 28 changed. R0, R2, the remaining work, the appendices and the estimates: 24
  items checked, 12 changed, one of them a new clarification for the owner. In all 92 items, 40 changed.
- The 40 changes are grouped below in 34 entries: kind A, 9 entries, where carrying out the row as written would have
  changed behaviour or dropped an owner decision; B, 6, a basis attributed wrongly or a reader missed; C, 10, a file or
  an item without a phase; D, 9, duplicates, wording or a wrong number.

## Kind A: carried out as written, the row would have broken something
| row | as written | corrected | evidence |
|---|---|---|---|
| B6 PieceBuffer | `read_at()` and `trim()` go (dev's echo only) | only `read_at()` goes; `trim()` stays | `trim()` is called by `uart_get()` (asy_uart_comm.py:1119), the SET receive (:323) and `readline()` (asy_uart_driver.py:695); SCAN2 6 had already corrected this |
| B3 E28 | "back to the owner's FRAM_FULL scope" | one E28 at setup for an unreadable store; a full FRAM stays silent | owner, 2026-09-16: "we do not even add errno/wrnno for the out of FRAM memory" (REG:487, DR3) |
| B8 build checks | ~314 lines of checks no TOML trips go | except a rule whose violation would make a boot refuse or boot-loop: `bus.i2c-timeout-max` and the UART ranges stay | SCAN2 G3:431's condition, dropped in the plan |
| B5 NTP | "the cadence chain with its TickSeconds users" | the three chain rows NTP-12/13/15 go; TickSeconds and its owner-decided users stay | SysUptime (A-S19, OR101), LastSyncAge (NTP-14), WifiUptime (WF-18), the LED pause (NT-6, OR104) |
| B2 W69 | "back to its console line" | W69 and `absent_at_boot` go; a missing config file returns to the pre-audit persisted warning | 25caf528 config_manager.py:423-426 logged it (wrnno 3); the split came with W69 in 8d44fd14 |
| B7 NP-3 | the entry sanitiser goes | back to the pre-audit clamp (per channel, 0.1 s floor) | 25caf528 asy_neopixel_driver.py:29-39 |
| B6 E91/E92 | go | the construction refusals stay with their build mirrors (agent decision, smallest change) | the pre-audit module refused its own bad parameters (codes 10-15, 25caf528 :107-115); it is standalone (CLAUDE.md); the library ruling |
| R0 twin record | "about 2,260 lines with its tests" go | the record's 1,835 lines go; `twin_board.py` and `--twin` stay | the 2,260 include twin_board.py (E.md:375), which implements `--twin` (tests_hardware/conftest.py:96-480), needed by OR21.a and the hardware rule |
| R2 decision-records checks | `test_citations.py`, `test_decision_vocabulary.py` removed as audit machinery | they stay until a new clarification (i) at R2's checkpoint | CLAUDE.md:524-537: "the five prevention rules, answered '4. yes'" (OR68), rule (5) names both tests; against the owner's 2026-10-28 "The audit verification machinery is just a temporary tool" |

## Kind B: a basis attributed wrongly, or a reader missed
- B1, the logger-less console lines: "the owner's 'Option 1' direction" is wrong; Option 1 (2026-10-20) set the unit
  tests' log level (DECREV 4.7 had said so). The lines now belong to clarification (d), widened.
- B2, the `rel_humidity()` clamp: it is not part of clarification (h); it returns on the owner's note "Keep them ...
  Adapt the tests to be in line with the others". (h) is the wet bulb, which the row had not named.
- B2, `ResetBits` and `ConfigUnpersisted`: the website shows both (buildgen/definitions.py:636, :649); their website
  rows go with them. B7's `State` field likewise (B8 takes the website rows).
- B4, E27: also logged by the SCD30 (asy_scd30_driver.py:493), the same agent origin; it goes at both sites.
- R2, the repo scanner's own tests: they test the reader the owner's comment-cap gate runs on; kept.
- Appendix A rows 33-35: the counter caps are OR103's ("No unbounded counters anywhere"), now cited.

## Kind C: a file or an item without a phase
- `src/asy_framing_codecs.py` (+68/-62): joins B6. `devices/*.toml`, `html/`: join B8. `ext/` (Microdot v2.7.0, owner
  rows OR129.a, OR131.a) and `src/LICENSE-captive_dns`: named as outside R1.
- `scripts/`, `toolchain/`, `mockdata/`, `digital_twin/`, the CI files: named in R2's classification.
- B3: the CRC32 two-word form (a confirmed gap) and the H rows A-M9, A-M11 named.
- B4: the SPI half of the "no bus" contract; VOC-3 named for the ledger.
- B8: the bus-spread order of the read triggers (D.md G5b, refuted) was in no batch; the page build-date stamp moves
  from B5 (it lives in js/ and the stager).
- R0: every merged lane's worktree goes, not only the paused ones.
- R2: the SPECIFICATION.md-pinning files are classified one by one with their owner basis, not removed as a block.
- Round 1: REPORT 7's items 1, 2, 6 and 9 are not run (the owner's decisions settled them); item 11 is the owed rows.
- Round 1's queue: BACKLOG.md's "Real-hardware work still owed" replaced OR8.a's queue file.
- Section 1: snapshot 18 and the integration history's list in the evidence folder.

## Kind D: duplicates, wording, numbers
- B2: the mempause deadline was listed among the changes; it stays (decision 3, item 2). The "shared timed-wait
  primitive and its sweep" never existed in the tree (a planned, unmerged lane item); removed from B2.
- B3: the per-owner seed and the layout-shift fix were listed as two items; they are one.
- B5: the HTTP version refusal is part of WS-2.
- B8: "the I2C timeout build rule" and "the UART constant parse with no user" are restated (the parse keeps its users).
- B1: the explicit C-stack calls are 5 sites, now named.
- R0: "three static checks": one is a Unix-port run; its board half is REPORT 7 item 1.
- R0: the estimate is 1.5-2 h, not about 1 (twin-record edits, a Unix-port run, twelve baseline builds); its budget is
  2 h by decision 5's rule.
- R3/R4: "B3 rows" and "B4's rows" meant the audit plan's owner-row groups, not batches B3 and B4; renamed.
- Section 7's lead sentence.

## For the owner
- New clarification (i), asked at R2's checkpoint: the two decision-records checks.
- No fact under the seven decisions taken today changed.
- The budget table gains the plan check (22 h, 5 runs for its falsification agents) and R0's 2 h.

## The final verification: falsification agents (owner, 2026-10-28)
Independent agents got the revised plan and the sources, not the lead's evidence, and tried to refute every claim
(brief `S/u35r/briefs/plancheck_falsify.md`; hand-backs `falsify/F1.md`-`F4.md`). The lead verified each finding at the
source before it changed the plan. Changes: `PLAN_before_F1.md`, `PLAN_before_F2.md` are the states before them.

**F1, B1-B4 and the method (71 claims: 1 refuted, 15 partly, 55 hold).** Applied:
- E28's code lives in `asy_print_log.py`: it moves from B3 to B1 (refuted); its setup-write arm goes too.
- E115 stays: its handler writes no reset record, so without it a supervisor crash resets as reason 2 with nothing
  persisted (the scans' "the watchdog reset carries it" does not hold). The lead's own check had let this pass.
- E27 stays at the SCD30 (DECREV 3.1, DRX V5): the lead's own check had over-corrected it to both sites.
- The C-stack check sits at each logger entry, ahead of the level gate and any FRAM write: 12 handlers report only
  through `pr.err()`. The generated boot entry's dead call goes in B8.
- Clarification (d) covers every `console()` line in `src/` that prints a caught exception, by batch.
- B2 owns its `/status` emitter lines and website rows; the RUN-pin and HAD_POR hardware checks that read `ResetBits`
  are re-planned; the logger's `restored` flag goes with W69; a command-only schema keeps its printed note.
- The ladder is "changed to OR113's order", not "changed back" (no ladder before the audit).
- B3 keeps the setup's ID retries with W29 and the watch task's escalation; the SPI consumers and E52 in the FRAM
  driver go in B3; `erase_ready()`'s caller is named.
- The VOC "settled" wording names its two sites and the decision-vocabulary check.
- 2.1: DECREV 3.2-3.6; the `deinit()` and `set_level()` bools.

**F2, B5-B8, Order and done (81 claims: 0 refuted, 13 partly, 1 cannot tell, 67 hold).** Applied:
- `PieceBuffer.read_at()` stays: without it the echo copies the peer's 12,192-byte train per GET, the scans' one
  measured row (UC-5, UL-5 evidence F; OR143). The lead's own check had carried "read_at() goes" over from SCAN2.
- Order: the catalog, the `/status` emitter and its website rows are shared; each batch removes its own rows and keys
  there (two tests force it), and the lead merges parallel batches' hunks. B8 no longer claims B2's and B7's rows.
- B8: about 260 lines of TOML checks (not 314); four I2C timeout rules, of which the range and the maximum stay;
  `smallest_hard_consumer()` stays for its five readers; the build-date stamp's stager files named.
- The bus-spread order stays: OR47's owner words "it's always only about sensors with bus access" (cannot tell
  resolved to the smallest change).
- B6: E92 has no build mirror; `PieceBuffer` lives in B2's file. B7 names the `State` field's buildgen, catalog,
  mock-data and website sites. B5: the DNS client's console line joins (d). `LICENSE-captive_dns`: the holder line too.

## The final verification: F3 and F4 (2026-10-28)

F3 (sections 0-1, R0, R2, 3.1): 60 assertions, 2 refuted, 17 partly, 2 cannot tell. F4 (3.2, 4-7, appendices): 85
assertions, 2 refuted, 33 partly, 3 cannot tell. Each verified at the source before it changed the plan
(`falsify/F3.md`, `falsify/F4.md`; edits in `apply_f3f4.py`, backup `PLAN_before_F3F4.md`). All four agents: 297
assertions, 5 refuted, 78 partly, 6 cannot tell.

What changed the plan's substance:
- The twin runner stays (the owner's `twin-first-for-instruments` "ok", the only path to the twin hardware run at
  32768); R0 removes only the record's committed copy and its staleness test; R3 runs the runner once and commits the
  record again. The record's exception reasons become the first knowledge-list lines.
- REPORT 7 item 1, the bench's C-stack peak, runs in round 1: it is part of the `c-stack-reboot` "ok".
- Round 1 also works through the queue R3 prepares (OR8.a), C.md's surviving actions, the two review "ok"s that name
  the bench, and B2's RUN-pin and HAD_POR checks.
- CI: the 24 twin jobs and the coverage job have not run since 2026-10-21 (success-gated behind the red unit jobs);
  R0's close includes their first run.
- R2: the eight SPEC-table files are classified by what they check; product-property checks stay.
- R3: the OR37.a/OR38.a pass covers src/, scripts, runners and tools; OR19.a's carry-over keeps decision 4's condition;
  U35's 37 and 52 are named.
- R5: the D.15 sweep beyond src/ (OR96, "Option d is fine") and U37's 01 (2), 02, 04, 05 and 17.
- Clarification (j): the Stull paper's move needs write access and its terms. (h) and (d) reworded.
- Effort: the twin suite and the full CI time per batch (R1 24-31 h), R0 2-2.5 h, R3 9-15 h, R5 6-10 h, round 1 2-3
  sessions; before round 1 about 42-58 h (was 33-47), after it 16-26 h (was 13-21). Budgets by decision 5's rule: R0
  2.5 h, R1 31 h, R3 15 h, R5 10 h and 6 runs.
- Numbers: bytecode 161,626 -> 208,708 B (re-compiled, bare names), closure 2,129 rows, free flash about 42 KiB, warm
  CI unit run about 12 min, a full CI run 27 min (run 39665515089, checked on GitHub).

Under section 6 no decision's basis changed: D1's fact gains the owner's later word, D3's stale options went, D5's
budgets follow its own rule, D6's reason is attributed to the scan. Decision 4's "keeps every row's bar" now holds.

## The bench campaign folded in (2026-11-02, owner 15:21: "Fold into the plan now.")

Source: `bench/READING_20261029.md` (branch `claude/u35-bench-campaign` at `ec97953d`); backup `PLAN_before_bench.md`.
- Header, section 0 and section 1: the campaign, its one firmware defect, the answered round-1 items, the owner's
  decisions of 2026-10-29 (power save, storms) and 2026-11-02 (the storm stays unless a clean, lean Python-only fix
  exists; the hotspot's 2 UDP sockets are fine while the global config stays); seven clarifications, not six.
- R0: the findings list starts with two improvement items (FRAM SPI at 8 MHz; the lock-less `read()` spin).
- B1-B8: the silicon facts each batch's ledger uses. B6 admits the receive-ring teardown hang (4.2 (a)) with the bench
  branch's fix carried in test first (B93), corrects the UARTRSR comment, and reproduces the two crc16 results first.
- R3's round-1 preparation: the two hardware-test corrections, the twin fidelity inputs, the chip facts at the desk.
- Round 1: shortened to what needs the final firmware. Kept after checking `audit/review/decisions.json`:
  `scd30-calibration-readiness`'s provisional values (not measured by the bench) and `sgp40-chip-identity`'s serial read
  through the firmware. Removed: items 3, 5, 7, 9, 10, the W29 read, the DMA ring proof (unless B6 changes the ring),
  the HAD_POR check.
- R4: the bench's F.3 stall rows, Part F facts and the CLAUDE.md read-loop wording, placed by decision 7.
- Decision 3 item 4: answered (W29 cannot be in the FRAM: its log is RAM-only by design).
- Section 7: (c) gains the measured flash-write windows; (k) added, reset code 4 after a BOOTSEL round trip.
- Section 5: no hour changes. Appendix A item 21, Appendix C sources.
- Not adopted from FINDINGS: its prims11 caveat that the bare image lacked `modlwip_eagain` (`build_firmware()` always
  applies it). This fold-in has had the five checks by the lead but no falsification run (P's fifth run is unspent).

## The owner's answers on the open items (2026-11-02 15:39)

- Rule 11 extended: a falsification agent at the end of each R1 batch; section 5 and decision 5: R1 20 runs, 26-35 h,
  budget 35 h; totals before round 1 39 runs, about 44-62 h.
- B3: the FRAM's SPI clock to 4 MHz (the owner's choice), test first, one value at `asy_fram_driver.py:134`; round 1
  gains one overnight `long_fram.py` run at 4 MHz.
- The findings list starts empty again: both bench items settled. The R4 line on CLAUDE.md's UART read-loop wording
  is dropped (the lock-less early return is pre-audit design; no firmware caller reads without the lock).
- (15:51) B3's FRAM clock is 8 MHz, not 4 (owner: "Then let's take the 8mhz as initially suggested"), with its basis
  (24 MHz ceiling from the 48 MHz `clk_peri`; 20,741 1 KB reads at 8 MHz under load); round 1's overnight run at 8 MHz.

## The bench's open questions researched (2026-11-02, owner 15:53; `bench/RESEARCH_20261102.md`)

- Decision 3 item 4: the dump's entries named by their owner-seeded CRCs (WIFI W81 x2, CFGMGR_WIFI E21, SGP40 W34).
- B2: the BOOTSEL loss explained by the bootrom's `reset_usb_boot()` (scratch 0, 1 and the watchdog-boot vector 4-7).
- B4: the SGP40 NACKs are the bench script's timing; the bus-1 general call is the SGP40's soft reset; the SCD30's
  documented clock stretching (30 ms per ACK, 150 ms daily) keeps dev's 200 ms bus-1 timeout.
- B5: corrected: `network.country()`'s readback is MicroPython's own variable, and the country ioctl's result is
  discarded; the bench's "the chip accepts any string" was never measured.
- B6: the crc16 results did not reproduce in the twin, with or without silicon's CRC cost; knowledge until round 1.
- R3 and round 1: `loop_lag_under_combined_load` belongs to the flash tier; item 8 read by scanning channels; the
  crc16 diagnostic added.
- The storm: a Python-only disconnect from a soft callback is possible in principle by the source, unproven; not put
  into the plan (the owner decides).
- (16:25) Owner: "Live with the udp storm and defer the CRC until the next hardware run". Section 1 records the storm
  decision with the Python-only idea not adopted; B6 and round 1 carry the crc16 results as deferred by the owner.

## The working practices (2026-11-02, owner 16:42)

- Section 4.5 states them for every phase (owner: "this also applies to our new plan, wherever it is appropriate, as
  soon as we go for it"): fresh agents, slots kept full where the work allows, the lane efficiency rules, quality
  never cut. Applied: writing lanes stay at two (disjoint `src/` files, the shared files merged by the lead); the free
  slots take read-only work and machine runs.
- (16:42) Owner: "if the new plan has no more lanes, adapt the gist of the ideas to it". R1-R5 keep lanes; for R0
  (the lead alone) and round 1 (the bench session) section 4.5 states the gist adapted.

## The rewrite in the first units' spirit (2026-11-02, owner 17:03)

Owner: "rewrite the plan, and target that we are done with 50...60% of weekly budget (still a large Max plan)". The
2026-10-28 plan is kept as `plan/PLAN_before_rewrite.md`. PLAN.md went from 822 lines (13,125 words) to 343 (4,551).
- Kept: the target state, every owner decision and row, the 17 gaps, the UART ring fix, the bench's facts (cited, not
  repeated), the order (decision 1), test first, the gates, the falsification check per unit, the clarifications.
- Changed: phases and batches run as units like U1-U10 (one-page action list, one commit, one gate, a few report
  lines); the per-hunk six-column ledger gives way to the action list plus a throwaway script proving removals and
  restorations, the lead reading only the rest; the full gate runs once per unit; no follow-up lanes planned; no
  per-phase state ledgers; R3's rows are met mostly by R1 and R2's outputs (test reviews in the unit that changes a
  test); the budget is the owner's 50-60 % of a week, planned at 50 % with 23-24 agent runs instead of 55.
- Added: B8's unrecorded website items are named to the owner before they go (the aim "keeps all discussed
  features"); CI watching resumes with R0 (agent).
- (17:31, on the owner's "So by now it fulfills the criteria list I gave you recently?") Section 2, step 1: the
  safeguard of B8's website items widened to every user-visible removal without a recorded owner agreement (a REST
  or `/status` key, a website element), so the aim "keeps all discussed features" holds in every unit.
- (18:01) Owner: "The original goals from the audit and all discussed features all hold. No regressions, nothing bad
  reintroduced. Actually, the goal is how it was initially intended, only before the drift happened." Section 0 states
  the goal as `PROJECT_AUDIT_PLAN.md` 1.1's eight goals as first meant, with where each is met; section 2 adds that a
  test is read before it goes and a real defect's fix stays, that an original feature's test changes only
  mechanically (OR12), and that the falsification check also looks for a lost feature or a reintroduced defect.
- (18:03) Owner: "Also, nothing proven good shall be removed, but checked if it can be leaner". Section 0 defines
  proven good (fixes or prevents an observed or reproduced failure, measurably improves the device or the build, or
  owner-approved): it stays in its leanest form; the closure lists candidates, not verdicts. Section 2, step 1: each
  root marked to go is checked for proof first and, proven good, becomes a shrink item.
- (18:04) Owner: "In any case, no knowledge may be lost, and existing knowledge shall be smartly used wherever
  appropriate". Section 0: every removed item keeps a knowledge line in the evidence (decision 7 adds the doc lines);
  established facts are used, never re-derived. Section 2: action lists start from what is already known. D: findings
  with forward value placed, the last commit holding `audit/` tagged and named before it goes. 4.2: the knowledge list
  is a record, and scratch-only knowledge is summarised into the evidence by each phase end.

## The final check of the rewritten plan (2026-11-02, owner 18:16)

Owner: "Now ensure the plan is complete, consistent, according to our discussions, coherent and correct. Target final
quality of the plan itself." The version checked is `plancheck/final/PLAN_as_checked.md`; two independent agents
read it: C1 for completeness and accordance with the old plan, the rulings and the register (`final/C1.md`, 30
findings: 7 lost, 17 weakened, 3 contradicting, 3 unclear), C2 for falsification of every factual claim
(`final/C2.md`, 21 entries; no number wrong, the rest imprecise, misattributed or inconsistent). The lead verified
each at the source (the old plan, the rulings, the register, SCAN2, DECREV, git: 172 distinct closure roots,
`asy_uart_driver.py:80` unchanged at `916fb878`, three paused patches, REPORT 1's pinned compile figures) and applied
all of them, with a coherence pass of its own. The main changes:
- restored: the old 2.1's per-unit cleanups with `UARTDriver.deinit()`'s kept bool; the closure's five-item proviso
  (the Q6 handler kept in B1); the owner's bench decisions (power save, the storm, GPIO storms) as not admitted; the
  done-criteria of R2-R5; R0's register repointing and the open findings as input; (g) in R4; R2's classification
  detail and Part N's accuracy check; R3's B3 additions, OR49.a (1)'s load tests, U35's 09, the gap-gets-a-test and
  matrix-cell bars; round 1's channel-13 access point, the ring proof's repeat condition, C.md's four owner rows; the
  D.15 exclusion of test functions, OR11's link migration, U37's 14; rule 7's ".a" sentence; the owner's review of
  decisions taken on their behalf (OR2.c); "a failure on a kept behaviour is fixed in the code"; the removed tests
  listed; the action list shown at a unit's start; the bench sessions' interruptibility; the clarifications' both
  sides;
- corrected: the target formula with "proven good"; the unreachable-check rule in the owner's two-condition words and
  the library rule; the budget overrun now a stop and a report, never a cut; CI watching resumes only on the owner's
  word; the goal map (release, concept, parity with OR48.a's legacy check); B6's comment fix is written, not carried
  in, and its 66 B named an admitted fix; 172 roots; the bytecode figures' source; the unit-history figures (U8C, U15);
  rule 10 and 11's attribution (R2-R5's falsification is the agent's extension); decisions 2 and 3's wording;
  per-unit budgets summed per phase; one path scheme; DECREV 4's ninth place in R5.
PLAN.md: 434 lines (343 after the rewrite; the growth is restored content). No product file was touched.
