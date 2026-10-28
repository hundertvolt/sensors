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
