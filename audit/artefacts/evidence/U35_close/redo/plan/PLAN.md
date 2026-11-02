# Finishing the audit, in the spirit of its first units

Rewritten by the lead on 2026-11-02 on the owner's go-ahead: "rewrite the plan, and target that we are done with
50...60% of weekly budget (still a large Max plan)". It replaces the plan of 2026-10-28, kept as
`redo/plan/PLAN_before_rewrite.md` for its item-by-item maps of the retired U35-U37 actions (its appendices A and B) and
the full wording of each batch row. Nothing here starts without the owner's go-ahead; R0 needs its own. Paths are
relative to the evidence folder `audit/artefacts/evidence/U35_close/` unless they name a repository file.

The owner's aims (2026-11-02): "takes the audit ideas back to the roots"; "simplifies workflow drastically"; "keeps our
high quality"; "avoids excursions and excessive / hypothetical excursions"; "will finish the audit well inside a week's
budget"; "tries to minimize the changes in src and codegen"; "keeps all discussed features"; "closes all gaps we found
which are still relevant". And: "keeping quality, closing gaps and saving on effort are not contradictory, but go into
the same direction".

## 0. The idea

- **The goal** (owner, 2026-11-02: "The original goals from the audit and all discussed features all hold. No
  regressions, nothing bad reintroduced. Actually, the goal is how it was initially intended, only before the drift
  happened."): the audit's eight goals (`PROJECT_AUDIT_PLAN.md` 1.1) as first meant. Broad and deep were the reading of
  U1-U34 and the whole-tree scan of 2026-10-28 (`scan/REPORT.md`), not repeated. Release: R1 and R2, with R5's version
  and note and D's tag. Concept: R1, R2 and R4 (the principles Part, OR44.a). Feature parity: R1 and R2 (OR12: "zero
  regressions"), with OR48.a's legacy check in every unit (section 2, step 1). Proven: R3. Converged and closed: R5.
- **Work the way U1-U10 worked.** One theme per unit, a one-page action list, tests first, source, tests and docs in one
  commit, one gate, a short report. Measured from git: U1-U10 added 37-409 lines of audit records per unit (U6 4,712;
  U8C 853 with its fix); from U11 on up to 147,000, 22 of 25 units above 8,000, while `src/` changes stayed in the
  hundreds of added lines (U15 1,017; U10's renames aside); U24-U26 changed 1, 0 and 0 `src/` lines. The code work never
  grew; the machinery around it did. This plan carries none of that machinery.
- **The target state is unchanged.** Each module is the pre-audit code (`25caf528`), plus the owner's foundations
  (U1-U8, U10's names and member order), plus the confirmed gaps' smallest fixes, plus the owner's decided features in
  their smallest form, plus the rare-but-real cases on the keep list, plus what is proven good (below) in its leanest
  form. Everything else goes and stays knowledge (decision 7). So the end diff against the pre-audit code is as small as
  the decisions allow.
- **Nothing proven good goes** (owner, 2026-11-02: "nothing proven good shall be removed, but checked if it can be
  leaner"). Proven good means shown: it fixes or prevents a failure that was observed or reproduced, it measurably
  improves the device or the build, or the owner approved it. Such an item stays, in its leanest form; what has no such
  proof goes: a mechanism built on a hypothesis, audit machinery, a check "fully covered by typing adherence alone, and
  ... unreachable with today's code" (owner, 2026-10-27). A real feature stays even if unused today: "Always regard the
  modules as libraries" (owner). The closure lists candidates, not verdicts.
- **No knowledge is lost, and what we know is used** (owner, 2026-11-02: "In any case, no knowledge may be lost, and
  existing knowledge shall be smartly used wherever appropriate"). Every removed item keeps one knowledge line in the
  evidence (what it was, why it went, the commit holding its code); decision 7 decides which lines also go into the
  docs. A fact already established (the scans, the bench, the research, the register, the review verdicts, the rulings,
  SPECIFICATION.md) is used where it applies, never re-derived: no reading, run or measurement repeats one whose result
  stands.
- **Quality stays where it lives:** tests first, the four memory gates at both GC stages, strict typing, the hang
  backstop, the comment cap, the bus-hazard and wear rules, the UART changelog, a falsification check per unit. All but
  the falsification check cost machine time, not tokens. What goes is what made U11-U35 heavy: records, repeated passes,
  inventories, matrices as work lists, and code for cases nobody showed can happen.
- **Budget:** the whole remainder within 50-60 % of one weekly budget of the large Max plan; planned at 50 %, the rest a
  reserve (section 5).

## 1. What we start from

- **The tree.** Integration head `497b3eda`, equal to the pushed product tree; audit branch head `06de7544` (snapshot
  21). All 6,058 unit-tier tests pass at both GC stages; CI on snapshots 16-18 was red only on the twin record's two
  checks.
- **The size against the pre-audit state** (`scan/REPORT.md` 1, 2, 9, 10): `src/` bytecode 161,626 B then, 208,708 B now
  (+29 %; recompiled with bare source names, `redo/plancheck/CHANGES.md`; REPORT 1's pinned compile reads 164,566 and
  211,648 B); free flash in the dev image about 107 KiB then, about 42 KiB now; test and tool lines 105,942 then,
  232,891 now; CI unit-tier timeout 45 min then, 175 min now; SPECIFICATION.md 514 KiB then, 1,573 KiB now.
- **The findings this plan keeps:**
  - the 17 confirmed gaps in the pre-audit code, all fixed at head, each kept in its smallest form (`REPORT.md` 3);
  - one defect found on silicon: stopping the UART receive ring hangs the board until the watchdog (bench; fixed on
    `claude/u35-bench-campaign` at `916fb878`, carried in by B6);
  - the removal closure: 2,129 dependent sites of 172 roots marked to go, losing no gap and no rare-but-real case
    (`scan/scan2/G4_closure.tsv`, `G4b_closure.tsv`), provided five items stay (`SCAN2.md` 1: the unreadable-log-store
    branch, captive DNS's 512-byte receive, the shutdown's report of an unpersisted store, the Q6 handler, a 3-4 line
    Microdot hook), candidates for every unit's action list (section 0);
  - the decision review: 82 decisions answered differently, 71 obsolete, 75 shrinking to a smaller form
    (`scan/decrev/DECREV.md`), and the nine places where the build or its records differ from the owner's words (DECREV
    4; each in its unit below);
  - the bench's measurements and platform facts (`redo/bench/READING_20261029.md`, `redo/bench/RESEARCH_20261102.md`),
    which the units cite instead of repeating;
  - every owner word since the audit start (`redo/recovered/owner_rulings_after_LN118.md`, the register, the review
    page's `audit/review/answers.json`, and `scan/decrev/inputs/owner_words_lane_plan.md` for 2026-10-22 to 10-28; LEAD
    NOTES 130 and 142 stay lost), among them the bench decisions: radio power save "is not an option"; a LAN UDP storm
    that stalls the loop is accepted with the watchdog as backstop ("No patching or tinkering."; 2026-11-02: "Live with
    the udp storm", the Python-only disconnect not adopted); GPIO interrupt storms "are not really an issue". None of
    these is admitted as work (4.2).
- **Retired, not followed:** the seven paused lanes (the three with work kept as patches in `redo/paused/`), the closing
  ledger's lane items, U35-U37's 170 planned actions, the per-hunk six-column ledgers, per-phase state ledgers and the
  2026-10-28 plan's run counts. Where an old action carries an owner row, the row is met in the unit named below
  (`PLAN_before_rewrite.md` appendices A and B).

## 2. How a unit runs

1. **The action list** (the lead, one page at most, at the unit's start). Built from the closure and scan rows of the
   unit's files, what is already known about them (bench, research, review verdicts, open findings) and the owner's
   words. Per item: what, the decision (keep, shrink, remove, restore, change), its basis (an owner word, a gap, a
   reproduction) and the test that shows it. The five checks (4.1, rule 10) hold for each item. Every item marked to go,
   closure root or not, is checked for proof first; proven good, it becomes a "shrink" item. A function of the legacy
   code found lost or changed without a recorded reason goes to the owner (OR48.a: "If you find a suspicious place, ask
   me"). The list is shown to the owner at the unit's start; the unit waits only where an item needs them. An item
   removing something a user can see (a REST or `/status` key, a website element) with no recorded owner agreement is
   named to the owner at the unit's start and goes only on their word (the aim "keeps all discussed features"; some
   records were lost in October).
2. **One fresh agent does the unit, test first.** A behaviour that changes: its test changes first and is seen red. A
   mechanism that goes: the tests pinning it go first, listed in the action list; the tests around it stay green. A kept
   behaviour without a test gets one, seen red on a planted break. Nothing real is reintroduced: a test is read before
   it goes with its mechanism, and if it reproduces a failure the device can really meet (observed, or reproduced
   against the real code on the pinned platform), its fix stays in its smallest form and the item is corrected. A test
   of an original feature changes only mechanically, never in its goal, and a failure on a kept behaviour is fixed in
   the code, never in the test (OR12). The unit's own doc lines and the knowledge line of every item it removes go in
   the same commit. While fixing, only the failing file runs.
3. **One gate on the finished unit** (scripted): lint, typecheck, the unit tier and dev's twin suite at both GC stages.
   The other devices' twins run in CI.
4. **The review.** A throwaway script (written in R0) marks every hunk it proves mechanically: a closure site gone with
   no reference left, or a region equal to the pre-audit text under U10's names (taken from U10's commit). The lead
   reads every other hunk against the action list. A hunk with no item goes, or goes to the owner. No module's bytecode
   grows, except by an admitted fix (4.2), stated in the report.
5. **The falsification check** (owner, 2026-11-02: "Falsification agent at the end: yes."). One agent gets the action
   list's claims and the numbers with the repository, without the lead's reasoning, and tries to refute them; it also
   looks for a lost feature or a reintroduced real defect against the pre-audit code and the gap list. The lead verifies
   every refutation at the source before the report.
6. **One commit (a few for a large unit), pushed, CI green.** The message states what changed and why, citing the
   owner's words; no audit IDs or lane names outside `audit/`. Nothing is pushed while CI runs.
7. **The report, a few lines:** `src/` lines and bytecode against the pre-audit code, free flash on dev, test and tool
   lines, the decisions taken on the owner's behalf with their reasons, and the budget used (section 5). The action list
   with its outcomes is the unit's close note in the evidence folder. Nothing else is recorded per unit (4.2).

## 3. The units, in order (decision 1)

R0, then R1's units B1 and B2, then B3-B7 two at a time on disjoint files, then B8; R2; R3; round 1; R4; R5; the last
round and D. A phase ends with a report and a stop; inside R1 the units run back to back, each with its report, waiting
only for a clarification (section 6), an owner word on a removal (section 2, step 1) or a budget stop (section 5).

### R0, settling (the lead alone, no product code)

- The paused lanes' and merged lanes' worktrees go; their patches stay in the evidence folder. The register's U35-U37
  rows point to this plan.
- The findings list starts empty. `audit/sweeps/open_findings.md`'s 73 open or partly closed rows are input to the
  units' action lists and to R5's OR5.a.
- The twin record's committed copy and its staleness test go (`tests_hardware/twin_record.json`,
  `tests_scripts/test_twin_record.py`, about 1,600 lines, with their references); its 35 distinct exception reasons
  become the first knowledge lines. The runner, `twin_board.py` and `--twin` stay; R3 re-records once.
- DECREV 9's items 3, 5 and 6, static or Unix-port checks that each decide an item of the unit owning its code: the
  logger-side C-stack check at a near-exhausted C stack, one Unix-port run (B1's form); the three BR2 fixes, read at the
  parent of `7008730e`; the 2026-10-07 proposal behind the exception-handler guard.
- The baseline numbers, scripted: per-module lines and bytecode against `25caf528` (compiled with `-s`, bare source
  names), image size and free flash per device, test and tool lines, CI time per job. The review script (section 2, step
  4).
- The first full CI run since 2026-10-21 (the 24 twin jobs and coverage included). A red job is root-caused in R0; its
  fix goes to the unit that owns the code. CI watching, paused by the owner on 2026-10-28 ("pause watching Github CI for
  now"), resumes only on the owner's word; the lead asks for it with R0's go-ahead.

### R1, the firmware and build chain (eight units)

Full rows with their silicon facts: `PLAN_before_rewrite.md` 2.3. Each unit's action list judges every hunk of its
files, named here or not. Three files are shared (`buildgen/error_catalog.json`, the status emitter in
`buildgen/codegen.py`, `definitions.py`): each unit removes its own rows and keys there, and the lead merges those hunks
of two parallel units. In every unit, for its own files (`PLAN_before_rewrite.md` 2.1, DECREV 3.2-3.6): test-only
product code goes (the `setup()` bools, except dev's `UARTComm.setup()`, whose caller reads it; the I2C and SPI
`deinit()` and `set_level()` bools, while `UARTDriver.deinit()` keeps its, which its `init()` reads;
`set_utc_valid(valid=)`; `_shutdown_task`); a narrowing branch that can never run becomes a typing-side form; the
per-episode log flags give way to the central newest-entry rule (OR35.b: "Pure and simple."); the whole-millisecond rule
stays only for waits in loops.

- **B1 logging and catalog** (`asy_print_log.py`, the catalog, every `report_if_fatal()` site; alone, it touches 18 of
  the 28 modules and every other unit's files). Change: the C-stack record (the owner's "ok") becomes one check at each
  logger entry point, ahead of the level gate and any FRAM write, plus explicit calls at the 5 handlers that log nothing
  and the Microdot hook, replacing 123 calls. Shrink: E28 to one entry at setup for an unreadable store; a full FRAM
  stays silent (owner, 2026-09-16). Go: the catalog rows of removed codes and the 6 placeholders (decision 6). Keep: the
  Q6 handler (owner: "Option a"), one of the closure's five, in the form (d) leaves. Clarification (d) first.
- **B2 core** (base classes, system service, config manager, `math_helpers.py`, API response; their `/status` keys). Go:
  `ResetBits` and `ConfigUnpersisted` in `/status` with emitter lines and website rows (the decoded `ResetReason` and
  the flush flag stay); W69 with `absent_at_boot` and the `restored` flag (a missing config file returns to the
  pre-audit warning, once per boot; OR136.a's write-once kept); the uptime re-arm; the 1,200 ms escalation bound.
  Change: a chip-setup failure follows OR113's order, mild rung first; `rel_humidity()` clamps again, as before the
  audit. Keep: E115, the mempause deadline (decision 3), the recovery ladder in a smaller form, the reset path, the
  system commands, the staged write, the newest-entry rule, the counter caps (OR103), the measured uptime (OR101).
  Clarifications (h) and (k) first.
- **B3 storage** (FRAM driver and manager, CRC checks, `erase_ready()`'s caller). Go: the lost-FRAM chain (decision 3)
  with `erase_ready()`'s shrink; the SPI "no bus" consumers and E52; the chunk read's `MemoryError` catch and the two
  rows beside it, judged in the action list. Keep: the identification retries with W29 (decision 3), the escalation for
  a FRAM that never sets up (OR89), the per-owner CRC seed (the layout-shift fix), the blank chunk, the unreadable
  store, CRC32 in two 16-bit words. Change: the FRAM's SPI clock from 1 to 8 MHz, one value at `asy_fram_driver.py:134`
  (owner, 2026-11-02: "Then let's take the 8mhz as initially suggested"). Clarification (e) first.
- **B4 buses and sensors** (I2C and SPI drivers; SCD30, SGP40 with `voc_algorithm.py`, BMP3XX, ISL29125). Go: the I2C
  "no bus" contract at every consumer and the SPI driver's side of it; the BMP3XX power-on detector with W71, its
  conversion wait and scratch view (back to the STATUS poll); E27 at the BMP3XX site; W73; the ISL shadow compare back
  to after a failed write, W75 back to the console line; the SGP40's sample-age check and `None` branch, its restart
  back to the restore, its own "no backup" warning back; the VOC constants back to the per-sample port. Shrink: the I2C
  clear to one clock-out routine, the short-ACK path to about 4 lines. Keep: I2C-6/7, the ISL settle horizon, the SGP40
  restore cycle, a wedged bus at boot, a chip failing in operation. The VOC "settled" wording is repaired to the owner's
  words.
- **B5 network** (Wi-Fi form only, NTP, DNS, captive DNS, UDP socket, web server). Go: the web server's start retries
  and W62; WS-2's head refusals except the `Content-Length` check (decision 3); WS-9's quiet print and merge list; W16;
  the captive DNS re-raise; the NTP 44-47-byte refusal; the NTP cadence chain; the resolver's passed-in logger and
  `(address, cause)` widening; the stored NTPHost/DNSFallback re-check. Keep: `TickSeconds` and its users, the Wi-Fi
  behaviour as decided, the zero NTP timestamp, the 512 B receive with one yield per datagram, the listener close, the
  head bounds, a trace per dropped connection, W12, the country-code check (the chip reports nothing).
- **B6 UART** (driver, comm, link driver, codecs, `PieceBuffer`). Carry in, test first: the receive-ring teardown fix
  (`_rx_stop()`, changelog B93, `916fb878`; `tests/rp2.py`'s fake raises where silicon hangs; it adds 66 B, an admitted
  fix). Correct the comment at `asy_uart_driver.py:80` (UARTRSR flags a line error only when the line then goes quiet;
  the bench branch did not change it). Go: the zero-length guard. Keep: `PieceBuffer.trim()` and `read_at()` with the
  piece replies, the construction refusals E91 (with its build mirror) and E92, the DMA ring, the hazard mode, the
  link's `initialized`. Judged in the action list: the codec's decode-size change and its removed counter. The wire
  format stays untouched; every change gets its changelog entry. Clarification (c) first. The crc16 hazard results wait
  for round 1 (owner, 2026-11-02).
- **B7 LED** (NeoPixel driver, notification service, the `State` field's sites). Back to the pre-audit form: the 300 s
  overlay rewrite (to the pre-audit wait), the entry sanitiser (to the per-channel clamp with the 0.1 s floor). Go: the
  notification's sample-age check and its `State` field with status key, website row, code table, mock data and website
  test. Change: the internal request queues at its deadline, as the approved text says, and W67 goes. NP-4's end state
  is settled in the action list. Keep: NP-1, NP-2, the REST refusal, the overnight window (OR69), the LED pause (OR104).
- **B8 build chain and generated code** (`buildgen/`, generated modules, device TOMLs, the frozen website and its
  stager). Go: the build checks no device TOML can trip (about 260 lines), except those whose violation would make a
  boot refuse or loop: the I2C timeout stays one 1-200,000 us range, `smallest_hard_consumer()` stays for its tests, the
  UART ranges stay as B6's build mirror; the boot entry's unread C-stack call. The website items with no recorded
  agreement, the page build-date stamp among them, are named to the owner first (section 2, step 1). Keep: the boot
  entry's confirmed gaps (the emergency exception buffer, the loop-end labels), the read triggers' bus-spread order
  (OR47). The device TOMLs follow their drivers.

`ext/` stays as re-vendored (Microdot v2.7.0, byte-identical upstream). **R1 is done when** every module's remaining
diff against `25caf528` is covered by action-list items, every removed item has its knowledge line (and its doc line
where decision 7 places one), the gate and the twin CI on all six devices are green, and image size and free flash are
reported per device.

### R2, tests, tooling, CI and the register (one unit)

- Each file in `tests/`, `tests_scripts/`, `tests_js/`, `tests_hardware/`, `digital_twin/`, `scripts/`, `toolchain/`,
  `mockdata/` and the CI files, outside what R1 already removed, is classified once: pins a product property (kept); a
  tool test covered by an owner row or an owner word (kept, slimmed where it repeats itself; among them OR23.a's build
  chain, OR15.a's summary block, the CI apt mirror check and cache, the repo scanner's own tests); audit machinery born
  in the audit (removed, proven by the script); one of the eight SPECIFICATION.md table pins (kept where it checks a
  product property through the table or carries an owner row, only its restatement of the table slimmed); harness (kept
  unless lighter). The list goes to the owner before anything is removed.
- Kept in full by owner rule: the comment-cap gate, the gc-site checker, the memory-gate agreement, the persistence
  marker completeness, the four-tier bus hazard files; the two decision-records checks until clarification (i), their
  allow-lists only shrinking.
- The seven fixed-sleep tests wait for their condition (OR37.a (3)); the shared twin's 89 s retirement gives way to its
  idle event; the launcher stop file and the rig override go.
- CI timeouts from measured need with a stated margin, the two retries kept; the twin matrix sized to the devices and
  stages it must cover (the per-device rule stays); the hang backstop as CLAUDE.md states it.
- Part N back to OR30.a's scope, shown to the owner with the list; `@tunable` tags outside it go; the values that stay
  are checked for accuracy; the heap-floor row loses "measurement owed".
- **R2 is done when** every file is classified and the agreed removals are made, CI is green with the new timeouts, Part
  N holds only OR30.a's scope with every value's basis, and test lines, CI time per job and the twin job count are
  reported.

### R3, the proof on the final tree (one unit; decision 4's lean form)

Each group-B3 owner row is met on the final tree. Most are met by R1 and R2's own outputs; R3 adds only the rest.
- OR16.a: the twin boots every device; one collection check, every skip with a reason; one coverage run, every
  unexecuted line classed feature, guard or dead; faults planted only in the owner's scope.
- OR19.a: a review verdict carries over only where neither the test nor its target changed; a unit reviews the tests it
  changed and those whose target it changed; R3 checks that every test has a current verdict.
- OR21.a and OR29.a (4): a check-style test whose subject changed is triggered once. The twin runner runs every device
  script and hardware test once at both GC stages; the record and its test are committed again, exceptions listed.
- OR22.a, OR23.a, OR25.a, OR26: the generated code and build chain checked once and the intent map updated by
  subtraction (a working file), a gap getting a test in each; the raising-call map redone only for the modules R1
  changed, a defect counting only with a reproduction.
- OR37.a and OR38.a: one pass over everything changed since the audit start for harmful constructs, races, leaked
  resources and hygiene.
- OR39.a, OR40.a, OR41.a, OR49.a: speed and footprint measured; the matrices as reading aids, each cell carrying a
  reason or naming its existing test, a new test only for a real interaction with none; each finite resource a test or a
  reason, with its report entry; OR49.a (1)'s two load tests (the full soft-callback queue, the DNS flood at the
  hotspot) taken from LD+CM3's patch.
- U35's 09 (the owner's two twin recombinations), 37 and 52; the bus hazard rule and the wear table, for the final
  tree's changes.
- Round 1's preparation: BACKLOG's owed-hardware queue in order with expected outcomes and the wear budget; the hardware
  tests linted, typechecked and collection-checked, with the bench's two corrections
  (`tests_hardware/bench/test_reset_reasons.py` after (k); `loop_lag_under_combined_load` in the flash tier); the twin
  fidelity table fed by the bench's probes; the chip facts set against the final code; the hardware knowledge
  cross-checked against the datasheets (OR29.a (2)).
- **R3 is done when** every group-B3 owner row (`audit/CONSOLIDATION.md` 2, with section 4's B3 additions OR20/OR36,
  OR45, OR55 and OR77/OR79) has its outcome on the final tree, met and where or one stated limit for the owner, and
  round 1 is fully prepared.

### Round 1, the bench session (its own go-ahead, the final firmware)

- REPORT 7's item 1 (B1's form on the final image), item 4 (the SGP40 through the restore cycle), item 8 (the country
  code read from the air by a channel scan under "DE" and "XX" against an access point on channel 13), optional item 12;
  item 11's rows that need the final firmware (reset reasons 21, 22 and 10+phase, the first unfed watchdog stretch,
  dev's ring peak); the DMA ring proof repeats only if B6 changes the ring beyond B93.
- The crc16 hazard results, rerun with both ends' logs and the ring counters at every failing exchange.
- The queue R3 prepared; `audit/actions/C.md`'s surviving actions (OR47.a's boot log and trigger stamps, OR60.a (4)'s
  reset codes 0, 9, 10+p and 20, OR50.a (3)(b)'s bench packages, OR79.a's off-subnet DNS attempt);
  `scd30-calibration-readiness`'s provisional values, `sgp40-chip-identity`'s serial read, B2's RUN-pin check, one
  overnight `long_fram.py` at 8 MHz.
- Not repeated: what the bench campaign answered (`redo/bench/READING_20261029.md`). FRAM logs are read and saved first.
  A confirmed failure gets its minimal fix on evidence; the twin is corrected until it agrees.

### R4, the docs, written once from the final state (one unit)

- OR27.a (facts, rules and agreements, no history); OR13 and OR14; OR15.a (the README's task-first layout with a checked
  CLI reference); OR44.a (the principles Part and one ordered checklist); OR51.a (4); OR68.a with DECREV 4's WoZi
  wording and the seven misattributed texts.
- OR10 and OR10.b: the new-module procedure proven by fresh builds against two baselines, at most three runs.
- Parts that describe only removed mechanisms go as whole blocks; the knowledge lines and the bench's facts are placed
  as decision 7 says, each checked against the final tree (Part F for platform facts, F.3 for the stall rows, F.2 naming
  the watchdog as the LAN storm's only recovery).
- U36's 96 actions are checklist inputs, dropped where their subject is gone; their rule actions are proposals shown to
  the owner, adopted only with an owner row behind them. `src/LICENSE-captive_dns`'s path and holder line.
- (g): A.11's owner-signed table restored; row 2 keeps naming the `UartHazards` dispatch field, marked as agent text.
- **R4 is done when** every row above is met on the final tree, every knowledge line is placed, and the docs' own checks
  pass.

### R5, the close of execution; the last round; D

- R5: OR9.a's re-verification until one pass is all green (at most three); OR11's stray files, their links migrated;
  OR5.a, every open finding and BACKLOG item at a terminal state (OF-16's record among them, DECREV 4's ninth place);
  OR52.a (2)'s golden fixtures; the version and release note; the final report with OR49.a (3)'s entries; the
  build-environment list; the D.15 order beyond `src/` (owner, 2026-10-27: "Option d is fine"; OR96: "2. a but not the
  unit tests themselves"); U37's 01 (2), 02, 04, 05, 14 and 17. **R5 is done when** one re-verification pass ends all
  green and every item has its terminal state.
- The last round: OR40.a (3)'s two-image GC proof, what round 1 left, OR17.a's twin corrections.
- D: the Stull paper after clarification (j); the do-not-reopen decisions checked at their doc sites; every finding with
  forward value placed in the docs or BACKLOG, and the last commit holding `audit/` tagged and named in the final
  report, so nothing is lost with it; then the plan and `audit/` deleted; one merge into `main`, tagged v2.0 with the
  owner's agreement.

## 4. Rules

### 4.1 For the work (DRIFT 6 and the owner's words, kept)

1. Product code changes only for an owner decision, an observed failure, or a reproduction against the real code. A
   hypothesis becomes knowledge, a hardware-round item, or at most one cheap test; never code.
2. The smallest change; for solid code that is often none. Every firmware or build-chain change test first (owner,
   2026-10-28).
3. Code that exists because of another addition questions its root first; a chain two deep goes to the owner.
4. Rigor is tiered: the firmware and build chain deep; tests good, no campaigns; the audit's own tools minimal and
   throwaway (no tests of them, no line-number records, no raw logs committed).
5. Inventories and matrices are reading aids, never work lists.
6. No new hardcoded delay check; a new wait uses an event, an order or the driven clock. The owner's deadlines and the
   hang backstop stay.
7. Only the owner's words bind; agent-written requirements are proposals. A planning-phase ".a" row the owner answered
   "yes" to is the owner's.
8. Every owner word goes into the rulings file, verbatim, with its time, as it is given.
9. Unforeseen decisions take the smallest change, are shown in the next report and are reviewed by the owner at each
   phase stop (OR2.c).
10. The five checks before anything is written or shown (the lead's form of the owner's 2026-10-28 "Revise our current
    plans, so they do not contain such glitches anymore."): where it is (now and at `25caf528`), what governs it
    (quoted), who uses it (searched), what the platform does (the pinned source), how big it is (counted from git).
11. A falsification check ends every unit that changes the tree, R1 to R5: owner, 2026-10-28 (the plan check) and
    2026-11-02 ("Falsification agent at the end: yes.", for R1's units); R2-R5 by the same rule (agent, 2026-11-02). R0,
    the rounds and D change no product code and have none.

### 4.2 Admission, caps and records

- New work joins only as (a) a firmware or build-chain defect with evidence, or (b) a defect that makes a unit's own
  deliverable wrong. Everything else goes to the findings list (starting empty) for the owner.
- No follow-up units are planned: a unit fixes its own reds. A done-criterion that proves unreachable goes back once,
  with the measured limit. OR9.a's passes stop after three.
- Records: this plan, one action list per unit (its close note), the knowledge list, the rulings file, the findings
  list, short lead notes. The evidence folder gets summaries, never logs. The container is not kept: whatever of
  knowledge value exists only in the session's scratch is summarised into the evidence by each phase end.

### 4.3 The working practices (owner, 2026-11-02: "this also applies to our new plan, wherever it is appropriate")

- Fresh agents for units; at most two writing units at a time (B3-B7), the free slots for read-only work (falsification
  checks) and machine runs; 4 slots, 3 while a whole tier runs.
- Briefs are the action list plus the binding rules; reads are targeted (the anchor, then the range; a log's summary and
  failing block); each agent writes its own hand-back file and returns its path.
- Long runs in the background, no polling; the formal run once on the finished change; checks are scripts; records state
  results. Every run in its own network namespace at nice 19, with 3 GB of disk kept free.
- Where no agent runs (R0, the lead; round 1, the bench session), the same gist holds: steps side by side, targeted
  reads, one formal run; the bench session runs long and unattended with one hand-back file and regular pushes,
  interruptible at any time without losses, at most 10 minutes' wait (owner, 2026-10-28).

### 4.4 What stays strict

Every owner decision and review "ok" in its smallest form; every confirmed gap and rare-but-real case; the four memory
gates with zero `MemoryError` or "memory allocation failed" at both GC stages; the hang backstop, strict mypy, ruff's
full rule set and the comment cap; the four-tier bus hazard rule and the wear rules on board and host; the UART wire
format, with a changelog entry for any change; CI green on every pushed head; no failure called a flake without a root
cause.

## 5. Budget

The owner's target: done within 50-60 % of one weekly budget of the large Max plan. Planned at 50 %, with 10 points of
reserve; tokens cannot be metered from inside the session, so the owner's meter is the control.

| unit | share of the week | agent runs | wall-clock (mostly machine) |
|---|---|---|---|
| R0 | 2 % | 0 (the lead) | 2-3 h |
| B1, B2, B8 | 4 % each | 2 each (unit, falsification) | 4-5 h each |
| B3-B7 | 3 % each | 2 each | 3-4 h each, two at a time |
| R2 | 5 % | 2 | 4-6 h |
| R3 | 5 % | 2 | 5-8 h |
| round 1 | 2 % | the bench session | the owner's bench time |
| R4 | 6 % | 2 | 5-8 h |
| R5, last round, D | 3 % | 1-2 | 3-5 h |
| **total** | **50 %** | **23-24** | **about 40-60 h** |

- **Basis (rough).** From 2026-10-26 17:00 to 2026-10-28 16:00 about 47 hours used nearly the whole week (27 % by the
  first morning, 1-2 % left at the end) with up to four agents and the lead: about 0.4-0.5 % per agent-hour of active
  work. A unit's agent is active about 3-5 hours, its falsification check under one; the gates are machine time. The
  2026-10-28 plan (55 runs, 60-88 h at two lanes, half the redo's rate) came to about 60-90 %.
- **The control** (decision 5's form, the owner's figures): at each report the lead states the shares spent by the
  proxies; the owner reads the meter at each phase stop and whenever they look. Budgets are set per unit and summed per
  phase; a unit reaching 80 % of its share stops with a report, and so does the work whenever the running total exceeds
  the plan by more than 5 points; the owner decides how to go on (decision 5). Quality and depth are never cut for
  budget (owner, 2026-10-27).

## 6. Decisions and clarifications

All seven decisions were taken by the owner on 2026-10-28 (full text: `PLAN_before_rewrite.md` 6):
1. The order R0, R1, R2, R3, round 1, R4, R5, the last round and D ("then take option a").
2. Work from the current files, restoring pre-audit regions where a mechanism goes, with the hunk gate, test first
   ("Option A, and keep TDD style"); the gate now takes section 2, step 4's form (action list and review script).
3. The hypotheticals: the lost-FRAM chain goes whole (concluded from the owner's fact that the line floats); the
   mempause deadline stays; WS-2 goes except the `Content-Length` check; the identification retries with W29 stay.
   Closed.
4. R3's lean form ("Yes, take A").
5. Budgets with a stop at 80 % ("A"); the figures are now the owner's 50-60 % of a week, set per unit and summed per
   phase (section 5).
6. No placeholder rows for numbers retired before the release; from the release on, a removed code keeps its number
   unused ("third option accepted").
7. Obsolete findings folded into the facts: one line at its module's Part where a reader might rebuild it, platform
   facts in Part F, unverified ones as owed-hardware rows, trivial ones only in the evidence ("C").

Clarifications, each asked once in prose at the start of its unit (full text: `PLAN_before_rewrite.md` 7):
- (d) B1: the console at DebugLevel 0 (OR35.a against Q6's "Option a") and every `console()` line in `src/` that prints
  a caught exception, weighed against "no evidence to a bug ... is silently lost" and the memory gates.
- (h) B2: whether "Adapt the humidity to the verified range" extends to the wet bulb's cold-dry corner.
- (k) B2: reset code 4, which never reads back after BOOTSEL (the bootrom overwrites the record): keep it documented as
  unreachable and correct the test, or remove it.
- (e) B3: FRAM's own log for one invalid block (OR56 against "stay as is").
- (c) B6: a lost UART frame during a flash erase (measured windows in `PLAN_before_rewrite.md` 7).
- (i) R2: the two decision-records checks: the owner's prevention rule 5 (OR68 "4. yes") against "The audit verification
  machinery is just a temporary tool".
- (j) D: the Stull paper's move: write access to the `datasheets` repository (the owner's grant names fetching only) and
  the paper's redistribution terms (OR52.a (7)).

Not asked: (b), settled by decision 4; (a), OR30.a's register scope, shown with R2's list; (f), Wi-Fi, decided by the
owner; (g), a records fix done in R4.

## Sources

`scan/REPORT.md`, `scan/scan2/SCAN2.md` with the closure tables, `scan/decrev/DECREV.md`, `scan/DRIFT.md`,
`scan/PICTURE.md`; `redo/bench/READING_20261029.md`, `redo/bench/RESEARCH_20261102.md`; the rulings file;
`PROJECT_AUDIT_PLAN.md` 1.1 and 3.2 (the goals, the owner rows) and `audit/CONSOLIDATION.md` 2;
`redo/plan/PLAN_before_rewrite.md` (the full batch rows, the item-by-item maps, the decisions' text); the unit history
measured from git (`git log --numstat` over the integration tree, 2026-11-02).
