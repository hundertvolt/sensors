# V_DT: verification of DOCS-1..DOCS-8 (+ Notes) and TESTS-1, TESTS-2, TESTS-4, TESTS-6, TESTS-7

Worktree `S/wt-final` (590cffcf), baseline `25caf528`. Every view filtered. Owner sources read: `owner_rulings_after_LN118.md`,
`picture/PICTURE.md`, `picture/or_quotes.txt`, archived `PROJECT_AUDIT_PLAN.md`, `audit/CONSOLIDATION.md`, `audit/FINAL_REPORT.md`,
`r5/W3A/O4.tsv`, `findings/FINDINGS.md` (archive branch).

## Summary table

| id | verdict | one-line reason | fix size (lines) | touches device behaviour? |
|---|---|---|---|---|
| DOCS-1 | CONFIRMED | Filtered greps confirm the restraining owner rulings (10-23..11-11) are absent from CLAUDE.md, SPEC and skills | +8-10 (SPEC 0.2 only) | n |
| DOCS-2 | CONFIRMED (narrowed) | The "never asked, decided on the owner's behalf" clause is superseded by later owner words. The "no stop-points" clause is still backed by the owner (11-02, 11-05, 11-07), so it stays | ~5 changed | n |
| DOCS-3 | CONFIRMED | The 11-10 precedence rule (restated by the owner 11-13 10:16) is in no standing doc. Only 09-26's narrower "my most recent decision" is | +2 | n |
| DOCS-4 | CONFIRMED-OWNER (part REFUTED) | The "every shared resource" four-tier rule is the owner's OR41.a(3) "yes". The E.2.3 Load sentence has an owner source (OR49/OR49.a), so "none found" is wrong | 2 (if reverted) | n |
| DOCS-5 | MINOR (dup of DOCS-1) | I.4(a) already limits catches to the owner's "expectable", true-alternative-flow rule (SPEC:9189-9194) and keeps the asyncio no-blanket-wrap. The missing word belongs in DOCS-1's paragraph | 1 clause | n |
| DOCS-6 | CONFIRMED (adjusted) | BACKLOG holds a "fulfilled" item, a done M1 and done VOC/CRC rows, and an audit-plan clause. But the 08-08 owner requirement must move its credit to SPEC A.10, not be dropped | ~-20, +1 | n |
| DOCS-7 | CONFIRMED (relabel) + CONFIRMED-OWNER (gc.collect) | The 3 "(lead, …)" credits fall outside O4's agent-only grep. No owner word ever agreed to retiring the boot collects | 3 words; 1 line or a restore | n (y if restored) |
| DOCS-8 | MINOR | Wording only. The owner's 11-06 quote at bench-routines:23-25 ("campaign plan") must stay verbatim | 3 words | n |
| TESTS-1 | CONFIRMED-OWNER | Growth verified (~8,400 lines across 14 files). Not all of it is free to cut: `test_driven_time.py` backs the driven-clock P1 proofs. The cut is itself test work (11-11) | 679 for the first bounded cut; up to ~7,000 | n |
| TESTS-2 | REFUTED (residue MINOR) | The owner accepted O4 topic G (the simulator-only list, these twin-runner knobs included) on 2026-11-12, later than OR20. The `block` near-duplicate of Run 10 is marginal | ~20 | n |
| TESTS-4 | CONFIRMED (narrowed) | Control arms, called "overkill" by the owner (OR21.a 09-25, and 11-11). The 11-02 "That's okay" kept the product guard, not its 769-line contract file | ~345 in 3 files | n |
| TESTS-6 | MINOR | Each of the 3 locks is live in its own runtime. The lock itself is owner-agreed (OR38.a(3)). Merging means a launcher chain and loses the direct-run lock. Its test-only probe belongs to TESTS-1's root | (~220 probe+test under TESTS-1) | n |
| TESTS-7 | CONFIRMED | `audit/` and `PROJECT_AUDIT_PLAN.md` are gone. 3 dead exclusion entries remain, nothing pins them | ~4 | n |

## Per finding

### DOCS-1: CONFIRMED
- **Checked:**
  - Filtered phrase counts over CLAUDE.md, SPECIFICATION.md and `.claude/skills/*`: "runaway", "deep dive", "temporary tool",
    "as libraries", "just unused", "ask me", "smart design", "negative test", "drift into", "cascade" and "non-hypothetical"
    each 0.
  - "hypothetical" has 1 hit: SPEC:8491, a 09-26 test-specific quote.
  - Part 0 (SPEC:37-80) carries only the 11-07 levels, the 11-03 "low complexity" and the 11-02/11-06 "proven good" lines.
- **Expanding citations hold:**
  - CLAUDE.md:224-231 (four-tier hazards);
  - CLAUDE.md:457-459 (CI flake rule);
  - work-routines:59 ("Passed only on retry" is a finding).
- **Decisive:** the owner's own 11-13 10:16 message lists exactly these as the audit's global view. The rulings file has them
  verbatim; no later word withdraws any.
- **Smallest fix:** one short paragraph after SPEC:80 ("P4 in practice"), quoting only the general rulings with their dates:
  - 10-28 hypothetical no-go, plus verifying suspicious hypotheticals;
  - free bound yes, mechanism for an unobserved trigger no;
  - 10-28 tiered rigor;
  - 10-23 modules as libraries;
  - 11-09 18:30:08 "ask me" (recorded as standing);
  - 11-07 target;
  - 11-09 smart design at every level;
  - 11-11 root causes, no runaway chains;
  - 11-11 negative tests.

  CLAUDE.md:3-6 and integrate-module:16 already point to Part 0, so no new pointers are needed. Audit-only words ("the audit
  verification machinery is just a temporary tool", "don't drift into fixing tests") stay in the archive.

### DOCS-2: CONFIRMED, narrowed
- **Fact verified:** CLAUDE.md:442-459 contains:
  - :446-448 "owner questions only at requirement recording and in a consolidation run, never during execution";
  - :451-452 "no owner stop-points inside a unit";
  - :452-454 "an unforeseen decision during execution is never asked … log it as decided on the owner's behalf".

  This replaced the baseline step-session rule (baseline CLAUDE.md:449, :461 "stop and report back").
- **Owner backing:** OR2.c (09-25, "yes, that matches") and PQ8 (09-26) in the archived plan.
- **Later owner words, other direction (for open decisions):**
  - 11-07 (CLAUDE.md:382-388: "flagged to the owner, never guessed");
  - 11-09 18:30:08 "Before removing any function which could be a feature which is just unused, ask me" (standing);
  - 11-09 20:43:39 "What remains then, come back at me";
  - 11-13 10:16 "most recent general decisions count and in doubt supersede".
- **Internal contradiction:** the release's own work-routines:139-141 says "a genuinely open decision still go[es] to the
  owner".
- **Not superseded: uninterrupted execution.** 11-02 20:42 "You don't need to wait for my go for every step"; 11-05 "Keep
  going"; 11-07 17:31 "run through". So DOCS's proposal to delete the stop-point clause (:451-452) is refuted.
- **Smallest fix:** replace the two clauses at :446-448 and :452-454 with "a genuinely open decision goes to the owner
  (rule above, 11-07; 11-09)". Keep research-first, tests-first, sync points, no stop-points, and the CI-flake clause.
  About 5 lines, doc only.

### DOCS-3: CONFIRMED
- **Fact verified:**
  - CLAUDE.md:350-352 says the work "follows the rule as it stands unless that breaks a test or the build".
  - CLAUDE.md:376-377 holds only the 09-26 "take my most recent decision".
  - "supersede" appears only in other senses.
- **The rule itself:** owner 11-10 06:26:36, quoted: "Generally ... the more recent ones sopersede the older ones". It is
  restated as general on 11-13 10:16 ("especially if the earlier ones lack backing"). No doc carries it.
- **Smallest fix:** one clause after :377 quoting 11-10/11-13: a later clear owner decision supersedes an earlier rule, and
  an agent- or session-written rule yields to it. Leave :350-352, which then governs only what the rule cannot resolve; that
  part matches 11-10's own "tell me in case there are leftovers you cannot resolve". About 2 lines.

### DOCS-4: CONFIRMED-OWNER for the CLAUDE.md clause; REFUTED for the E.2.3 "none found"
- **Fact verified:** CLAUDE.md:224-231 extends the rule to "every other shared resource … (every shared resource, owner,
  2026-09-26)".
- **Owner source:** archived plan, OR41.a: owner "1. yes 2. yes 3. yes". Item (3) reads "CLAUDE.md's four-tier bus-hazard
  rule is applied to every shared resource, not only I2C/SPI devices". The later restraint (10-28, 11-11) does not address
  this rule specifically.
- **E.2.3 "Load":** the sentence (SPEC:5287-5288, `656fc82f`) has an owner source, OR49 (09-26): tests "close to, or even
  above its load limits … search for gaps … create additional tests". OR49.a: "All of that exactly." So it stays.
- **Question for the owner:** "Should a new device's four-tier hazard tests stay required for every shared resource (your
  09-26 yes), or go back to I2C/SPI bus devices only (your 09-03 rule)?"

### DOCS-5: MINOR, duplicate root of DOCS-1
- **Fact verified:** "non-hypothetical" is gone. Baseline SPEC:3601 had it; the release has no occurrence.
- **Already covered:**
  - I.4(a) (SPEC:9189-9194) restricts catches to the owner's 09-25 "true alternative flow … on expectable memory errors" rule.
  - SPEC:9195-9196 keeps the asyncio no-blanket-wrap, which was the baseline sentence's actual subject.
- **Not an owner item:** PICTURE section 6 lists M1 as a lead cleanup item, not an owner answer.
- **Fix:** fold "concrete, non-hypothetical" into DOCS-1's paragraph. Optionally write "expectable" for "can raise" at
  SPEC:9187, one clause.

### DOCS-6: CONFIRMED, adjusted
- **(a) BACKLOG:368-380, the "fulfilled" wiring-stage item.** Verified. Its owner requirement (2026-08-08, `7f498c1`)
  exists nowhere else. SPEC A.10 (:1365ff) states the fact, but without the owner credit. Fix: add the credit to A.10's
  first sentence, then delete the item. Deleting outright would lose an owner-requirement record (11-02 "no knowledge may be
  lost").
- **(b) BACKLOG:31-44, M1.** FINAL_REPORT section 7: "M1 PASS on relative values (no reference meter, owner)". The rig
  geometry is at tests_hardware/README.md:157 and :508. Drop the M1 half. Keep S3b: the final report records no S3b run.
- **(c) BACKLOG:70-76.** The VOC step ran on 11-13: SPEC stall.voc_process is 9.81 ms, 2026-11-13. FINAL_REPORT also gives
  the 256-byte CRC as 1.75 ms. DOCS's claim that SPEC:6790 carries 1.75 ms is false: the row still reads 1.31 ms for 264 B
  from the 11-10 image. The flash-write loop-gap half is not evidenced, so keep it.
- **(d) BACKLOG:17-19.** "and the whole-project audit plan (on its own branch)": verified, drop it.
- **(e) The remaining "owed" rows (:23-30 and others):** unverified, and not acted on here.
- **Size:** about 20 lines out, 1 in. Doc only.

### DOCS-7: relabel CONFIRMED; the boot gc.collect() removal CONFIRMED-OWNER
- **Fact verified:** SPEC:9332 "(lead, 2026-11-10)" and UART_C_PORT_CHANGELOG.md:218-219 "(lead, 2026-11-03)". These are
  the only 3 such credits in the tree.
- **O4 never covered them.** `r5/W3A/O4.tsv` line 1 shows O4's list was built by grepping only `agent, 2026-11-(0[6-9]|10)`.
- **Was the removal ever agreed by the owner? No owner word found.** The record:
  - **Pre-audit code.** `25caf528:src/system_service.py:222,226` and `buildgen/codegen.py:459,466` had the collects. The
    release has none (filtered `git grep`); `512bb0dc` (2026-11-10, "the boot-time collects gone") removed them.
  - **Owner approvals:**
    - 09-18 (baseline CLAUDE.md exception);
    - OR39.a 09-26: "gc.collect is allowed IN THE CODE at exactly the place you found it: in the one-time executed boot
      procedure";
    - OR143 10-05: the owner placed the UART ring's allocation in "the init phase … with the interleaved gc.collect calls".
  - **How it was removed:** by the lead, from a unit's red control-arm test. FINDINGS 12.145: "by the owner's 19:11:51 goal
    they go (decided under 20:43:39; the owner's 09-18 approval gets its record line)". It was not a queued owner question.
    No owner response is found to the one clause in FINAL_REPORT section 7 ("the boot lists run with no `gc.collect()`").
  - **Silicon check not recorded:** SPEC:9330 still promises it "on the next image"; no recorded silicon placement pass was
    found in the filtered archive.
  - **Rule breached:** CLAUDE.md:378-379 itself sends a decision whose facts changed "back to its maker".
- **Mitigation, so the owner sees both sides:**
  - OR39's own base rule is "Never use gc.collect() in the code", and the approval was an allowance, not a requirement.
  - The twin evidence shows the survivors landing 659,040 B low without the collects (SPEC:9327-9329).
- **Question for the owner:** "The boot-time gc.collect() calls you allowed on 09-18/09-26 were removed by the lead on
  11-10, because the twin shows the boot survivors now land low without them. Do you accept the removal, or restore them?"
  - Accept: one record line becomes yours; no code change.
  - Restore: about 4 product lines (asy_system_service run_setups/start_tasks plus codegen's starter loop), plus the
    gc-site checker and the boot-contiguity test's allowance. That changes the device's boot.
- **Relabel:** "lead" becomes "agent" at the 3 sites (CLAUDE.md:363-366 admits only the two actors).

### DOCS-8: MINOR
- **Verified:** bench-routines:18, :22 and :38 say "the lead"; :23-25 is the owner's 11-06 quote, which contains "within the
  campaign plan".
- **The proposed "campaign plan → session's plan" edit would alter an owner quote.** Decision-records rule (2)-(3) at
  CLAUDE.md:364-369 forbids that.
- "Relays" is the owner's own 11-06 mechanism, not audit vocabulary.
- **Remaining fix:** at most 3 words ("the lead" → "the code session"). It is cosmetic.

### TESTS-1: CONFIRMED-OWNER
- **Sizes verified (baseline → now):**
  - test_test_sh 839 → 2,435 (151 tests);
  - ci_suite_errcount 377 → 977; soak 105 → 366; matrix, state and scenarios are new (128 / 107 / 693);
  - bench_harness_helpers 171 → 1,219;
  - run_generic_integration test 290 → 1,399; twin machine test 539 → 1,763;
  - test_shared_helpers (678) and test_driven_time (642) are new.

  Summed growth is about 8,400 lines. The headers confirm these are tests of test helpers.
- **Not all of it is free to cut:**
  - `test_driven_time.py` self-tests DrivenTime, which carries the driven-clock P1 proof (`forty_days_of_uptime…`,
    SPEC:5280-5282).
  - `test_digital_twin_machine.py` pins the twin fidelity that WoZi's correctness rests on (CLAUDE.md).
  - So "nothing a verdict depends on goes" holds only file by file.
- **Smallest bounded cut:** delete `tests/test_shared_helpers.py` (its header: behaviours "no consumer test pins yet").
  The only follow-on is `tests/_port_bands.py:34`. Total 679 lines.
- **Question for the owner:** "Cut the test-of-test-machinery growth (~8,400 lines) back now, or leave it per your
  'don't drift into fixing tests'?"

### TESTS-2: REFUTED (residue MINOR)
- **Facts verified:**
  - 14 `--test-*` flags;
  - hooks `_test_*` at run_generic_integration.py:777-1190;
  - the runner grew 439 → 1,503 lines;
  - the private-member rebinding is real (e.g. :1171ff rebinds the supervisor's dead-task report).
- **Owner coverage exists.** On 2026-11-12 08:25:46 the owner accepted O4 topic G, "the simulator-only test list, as a
  whole". It is later than OR20 and wins by the precedence rule. O4.tsv's G rows name exactly these knobs:
  - "the stalled loop and the held close are twin-runner knobs the firmware lacks";
  - "the client gone mid-response";
  - "the dropped fire's two halves";
  - "the two faults inside the graph".

  The report's "no owner decision on the hooks" is therefore wrong.
- **Residue:** `watchdog_fault_block` (`_digital_twin_scenarios.py:2228-2231`) is a near-duplicate of the pre-audit Run 10
  (`_digital_twin_ci_suite.py:777-794`). The baseline already had `--hang`. Removing it is about 20 lines across the
  scenario, the `block` branch, the E.6.6 row :5875 and its flag tests. That is marginal.

### TESTS-4: CONFIRMED, narrowed
- **Verified in test_exception_handler_contract.py (new, 769 lines):**
  - the real-tree checks at :275-295, :539, :666, :763;
  - the "Planted negatives" sections at :296-443, :561-611 and :694-731.
- **Verified in the other two named files:**
  - test_tunables_register.py:298-371: 13 synthetic-tree tests;
  - test_error_catalog.py:760-811: the "planted catalog".
- **Owner basis:** OR21.a (09-25) "yes, but the control arms are overkill", and 11-11 17:29 "be careful with such negative
  tests".
- **Not owner-kept:** R0_CHECKS item 6 shows the owner's 11-02 "That's okay." was said "on the guard shown at
  `src/asy_system_service.py:778`". That is the product guard, not this file.
- **Fix:** delete the planted/clean arms in these three files, about 345 lines. The real-tree checks stay, so no verdict is
  lost.
- **Out of scope here:** the other ~25 single planted/clean functions spread over ~25 files. Each needs reading
  (drift-into-tests risk), so leave them (MINOR).

### TESTS-6: MINOR
- **Verified:** the three files total 381 lines, none of them in the baseline. All three are live:
  - the `.sh` lock: test.sh:113, run_digital_twin_ci.sh:61, run_unix_port_integration.sh:82;
  - the `.py` lock: _digital_twin_ci_suite.py:1813 and _digital_twin_scenarios.py:2344;
  - the `.js` lock: cross_browser_smoke.mjs:11 and _twin_process.js:11.
- **Owner basis:** OR38.a(3) (09-26, "yes") requires the lock: "product-fixed ports … used by one tier at a time under a
  lock".
- **Why merging is a chain, not a deletion:** a single shell implementation would force the Python and Node launchers
  through shell wrappers, and the documented direct run would lose its lock (R2's own objection).
- **Clean part:** `probePortLock()` with its actor scaffolding (_port_lock.js, roughly :12-183 minus `holderOf`/`isListed`,
  plus :232-260) and `port-lock.test.js` (82 lines) are test-only ("no runner calls it", :3). They belong to TESTS-1's
  root.

### TESTS-7: CONFIRMED
- **Verified:**
  - tests_scripts/_repo_scan.py:25-28: the `"audit/"` and `"PROJECT_AUDIT_PLAN.md"` entries plus their sentence;
  - tests_scripts/test_import_graph.py:22-24: the `"audit/"` entry.
- Both paths are absent from the tree.
- The only consumers are `_repo_scan.py:263` and `test_import_graph.py:220`; nothing pins the tuples.
- **Fix:** delete the 3 entries and the clause, about 4 lines.

## Duplicates and notes
- **Duplicates:**
  - DOCS-5 has the same root as DOCS-1 (the restraining rulings are missing); keep DOCS-1.
  - TESTS-6's probe has the same root as TESTS-1 (tests of test machinery).
  - DOCS's Note on the gc.collect is the same item as DOCS-7.
  - DOCS's Note on "gates enforcing doc rules" is the same observation as TESTS's Note on the 43 static gates. Neither is a
    finding.
- **The brief's question on the gc.collect: owner agreement to retiring it is NOT found.** DOCS-7 gives the record and the
  one-line question.
- **SPEC 0.2's pillars:**
  - The audit's P7-P12 were agent-derived (archived CONSOLIDATION.md section 1: "P1-P6 are OR44.a's, P7-P10 came from
    requirement pass 1, P11-P12 from harvest pass 1"). The release's P7-P11 (agent, 11-05) re-cut is therefore no owner
    conflict.
  - The audit's P7 "evidence survives" is folded into P3's row (FRAM evidence surviving a reboot; that row carries a
    filtered word and was not quoted).
  - "Extensible without edits elsewhere" (audit P10) has no row in 0.2. It lives in Parts K/L and rests on owner rows OR10
    and OR43.a. One table row would restore it. Not worth a finding.
- **DOCS's Note on CLAUDE.md:470-479** ("every agreed-but-deferred item whose trigger is met is swept in"): owner-quoted
  09-26 text. It should be read against 11-11 "no runaway chains" when DOCS-1's paragraph lands, but it is not a separate
  finding.
- **Stale fact for the doc pass:** SPEC:6790's `stall.crc` reads 1.31 ms for 264 B (11-10 image), while the 11-13 final
  image measured 1.75 ms for 256 B (FINAL_REPORT section 7). DOCS's Note also flags SPEC:8898's 0.95 ms.
- **A slip on my side, disclosed:** one unfiltered `sed -n 60,64p SPECIFICATION.md` showed the P3 table row, whose
  filtered word is a concept name, not a credential. Nothing sensitive was printed, and nothing from it is quoted here.
