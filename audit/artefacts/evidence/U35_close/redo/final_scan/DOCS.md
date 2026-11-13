# DOCS: the standing docs and rules (CLAUDE.md, SPECIFICATION.md, BACKLOG.md, README.md, DEVICE_REFERENCE.md, HEAP_FRAGMENTATION_MEASUREMENTS.md, UART_C_PORT_CHANGELOG.md, tests_hardware/README.md, digital_twin/README.md, legacy/README.md, .claude/skills/, THIRD_PARTY_LICENSES.md for stale entries)

## Verdict
The audit's own records are fully gone from the docs: no `audit/` path, no plan citation, no OR/OF/U/LN ID or lane vocabulary.
The rulings do not hold in the standing rules, though. Almost none of the owner's restraining rulings of 2026-10-28 to
2026-11-11 reached CLAUDE.md, SPECIFICATION.md Part 0/D/E or the skills: no hypotheticals, no runaway chains, no test-fixing
drift, tiered rigor, smart-design minimality, ask before removing an unused feature, the 11-10 precedence rule. The
expanding rules of the audit era still bind, many of them gate-enforced. These include the audit's execution workflow (no owner
stop-points, decisions taken on the owner's behalf), which the drift analysis names as a cause. A future session that
reads only the standing docs would get the drift's rule set back. Smaller leftovers: M1 was never restored, BACKLOG was not
reconciled with the final bench round, and a few credits name an audit role ("lead").

## Shape since the baseline
- Docs +14,304/-7,650 lines. SPECIFICATION.md grew from 6,785 to 12,224 lines: new Part 0 (principles/pillars), K (one
  checklist), M (chips) and N (tunables), and Parts E, F and I grew.
- CLAUDE.md went from 1,067 to 801 lines, rewritten as actor-tagged rules plus a "Code quality tooling" catalogue. BACKLOG.md
  went from 883 to 414 lines and is now mostly "Real-hardware work still owed" (lines 15-309). README.md went from 795 to
  1,285 lines and gained Release/Changes and the chroot recipe. tests_hardware/README.md went from 1,414 to 1,769 lines and
  digital_twin/README.md from 919 to 1,240.
- New: four skills (work-routines, bench-routines, tree-care, integrate-module; 425 lines) and legacy/README.md.
- The doc rules now lean on new meta-gates in tests_scripts/ (58 to 190 test files). Examples: test_decision_vocabulary.py
  (342-line allowlist), test_citations.py, test_ci_workflow.py, test_lint_type_scopes.py, test_tool_pins.py,
  test_ruff_exemptions_live.py and test_uart_changelog.py. CLAUDE.md cites them as the enforcement of its rules.

## Findings

### DOCS-1 [R] [VERIFIED] The owner's restraining rulings of 2026-10-28..11-11 are missing from every standing rule, while the expanding rules stand as gates
- Where:
  - Pointer chain: CLAUDE.md:3-6 says SPECIFICATION.md Part 0 "states the design principles every rule here serves".
  - Part 0 as it stands: SPECIFICATION.md:37-80.
  - Skills: .claude/skills/work-routines/SKILL.md:103-125 ("Rules that keep coming back") and
    .claude/skills/integrate-module/SKILL.md:16 ("Read SPECIFICATION.md Part 0 and Part K in full").
- What: filtered greps over CLAUDE.md, SPECIFICATION.md and all skills find no trace of any of these rulings:
  - "building upon hypothetical findings is a clear no-go" and "verified first" (10-28);
  - a free bound by construction is wanted, a mechanism for an unobserved trigger is not, and hardcoded timed checks are
    "a very bad, very awkward pattern" (10-28);
  - "The unit tests shall have good quality, but don't need deep dives. The audit verification machinery is just a
    temporary tool." (10-28);
  - fault planting only for complex measurement tests (10-23);
  - "Always regard the modules as libraries" (10-23), and "Before removing any function which could be a feature which is
    just unused, ask me" (11-09);
  - "all gaps closed, (really) agreed on features implemented, and from there on minimal, efficient and lean changes"
    (11-07);
  - "minimal and optimal at the same time through smart design" and the general simpler-or-more-efficient question at every
    level (11-09);
  - "address the root causes of issues, not something derived over multiple steps" (11-11);
  - "Minimal complexity, no dropped features, no known or new gaps, and no runaway fixing chains, and don't drift into
    fixing tests, concentrate on the quality of the firmware and the buildgen" (11-11);
  - "be careful with such negative tests" (11-11);
  - "conservative" meaning the smallest, most reversible change (PICTURE L7), and the cascade rule (DRIFT section 6.6).

  Only four restraining pieces made it in: 11-07 levels (SPEC:46-50), 11-07 proportionality (SPEC:4887-4893), 11-03 "low
  complexity" and 11-02 "proven good" (SPEC:74-80).

  The expanding side is complete and gate-backed, for example:
  - CLAUDE.md:224-231 hazard tests at four tiers, "never forget this";
  - SPEC:5264-5296 (E.2.3) with test_const_mirrors.py;
  - CLAUDE.md:458-459 "a CI failure is a flake only if the provider confirms an outage", and work-routines:59
    "`Passed only on retry` is a finding, not a pass". DRIFT 2.6(4) names this pull as what dragged the harness into
    investigations, and 10-27 "Don't care about proven external issues" plus 11-11 restrain it.

  This is exactly the asymmetry DRIFT 2.2 calls the root of the drift.
- Ruling/pillar it meets: L1-L4, L7; DRIFT section 6.2 "Restraint as a gate, not as prose"; 11-10 precedence.
- Decision record: owner rulings 2026-10-23, 10-28, 11-07, 11-09, 11-11 (quoted above, owner_rulings_after_LN118.md). None
  found that withdraws them.
- Smallest fix: add one short paragraph to SPECIFICATION.md 0.2 "P4 in practice" (SPEC:74-80) quoting these rulings with
  their dates. Then add one CLAUDE.md working-agreement line pointing to it, and one line in work-routines' "Rules that keep
  coming back". About 12 lines, no new gate.

### DOCS-2 [R] [VERIFIED] CLAUDE.md still binds the audit's no-owner-filter execution workflow
- Where: CLAUDE.md:442-459 ("Workflow for substantial work", written in U0 `bcfd11e4`, 2026-10-06). Within it:
  - :446-448 "owner questions only at requirement recording and in a consolidation run, never during execution";
  - :451-452 "no owner stop-points inside a unit, the report comes at its end";
  - :452-455 "an unforeseen decision during execution is never asked: take the more conservative, more easily reversible
    option ... and log it as decided on the owner's behalf for review".
- What: this is the mechanism DRIFT 2.5 names ("No owner filter during execution": 708 decisions taken on the owner's
  behalf; "conservative" read as "most protective"). It replaced the pre-audit step-session rule, whose step (6) was
  "stop and report back to the project owner before doing anything more" (baseline CLAUDE.md:449ff).
  - It contradicts the same file's later rule at CLAUDE.md:382-388 (owner, 2026-11-07): "what they leave genuinely open is
    flagged to the owner, never guessed".
  - It contradicts the owner on 2026-11-09 20:43: "What remains then, come back at me".
  - It contradicts PICTURE L7: "Conservative" means the smallest and most reversible change, usually none.
- Ruling/pillar it meets: L7; 11-10 precedence (the later clear rule wins); P11.
- Decision record: owner 2026-09-26, "superseded by the workflow description recorded in this session earlier" (the audit's
  OR2/OR2.c planning answers). It was superseded in direction by 2026-11-07 16:45 and 2026-11-09 20:43.
- Smallest fix: delete those three clauses from CLAUDE.md:446-455. Keep research-first, tests-first, the sync-point
  definition and the CI-flake clause. Where a decision is open, point to the 11-07 rule at CLAUDE.md:382.

### DOCS-3 [R] [VERIFIED] The 2026-11-10 precedence rule is absent, and CLAUDE.md makes a drifted rule bind "as it stands"
- Where:
  - CLAUDE.md:350-352: "Drift in a recorded rule or owner decision is not reworded: ... and the work follows the rule as it
    stands unless that breaks a test or the build".
  - CLAUDE.md:376-377 states only the 2026-09-26 "take my most recent decision", which covers the owner's own changes.
- What: the owner's 2026-11-10 06:26 rule is missing from every standing doc. That rule says: "if there are decisions into a
  different direction which are clear and came in later, the more recent ones supersede the older ones". It adds that
  promotion-session and agent text may be misread or session-only, and should be resolved by rule.
  - L7's "agent text stays a labelled proposal until the owner adopts it" is also missing. The nearest text is CLAUDE.md:367,
    "an agent recommendation stays the agent's even when accepted".
  - The 350-352 clause comes from the audit-process row OR13.a (09-25, "found during execution ... the work follows it as it
    stands"). It is the M10 mechanism: agent text kept binding until the owner happens to look.
- Ruling/pillar it meets: 11-10 precedence; L7; M10.
- Decision record: owner 2026-11-10 06:26:36 (verbatim above). OR13.a "yes, that's right" (09-25) is the older, superseded
  piece.
- Smallest fix: replace the second sentence of CLAUDE.md:350-352 with the 11-10 rule quoted, and add one clause to
  CLAUDE.md:376-377: an agent- or session-written rule is a proposal until adopted, and a later clear owner decision
  supersedes it.

### DOCS-4 [R] [VERIFIED provenance, SUSPECTED conflict] The audit's test-campaign scope is written as permanent test rules
- Where:
  - CLAUDE.md:224-231: "every other shared resource (locks, FRAM, the config file, sockets, the heap) — gets hazard test
    coverage across all four test tiers ... never forget this"; "every shared resource, owner, 2026-09-26".
  - SPEC:5287-5288 (E.2.3): "**Load**: every finite resource ... is loaded to its bound at the level that has it". No
    actor; added in U35 `656fc82f` on 2026-10-22, the test campaign itself.
  - SPEC:63 (P5) glosses the owner's concept as "combination and interleaving" (added `af531127`, 2026-11-05).
- What:
  - The "every shared resource" extension is OR41.a (3) of the audit plan: "CLAUDE.md's four-tier bus-hazard rule is applied
    to every shared resource". That row described the audit's own interaction-matrix campaign and said: "The combination
    and interaction matrix is an audit working file in `audit/` only and is deleted with it."
  - DRIFT 2.7 names that campaign ("interaction matrices") as the one-level-of-rigor drift.
  - The 10-28 ruling ("don't need deep dives ... just a temporary tool"), 10-23 (fault planting) and 11-11 (negative tests)
    restrain it later, yet it now binds every future module at four tiers.
  - The owner's own 2026-09-03 rule (`da3a5b5`) covered new I2C/SPI bus devices.
- Ruling/pillar it meets: L4 (tiered rigor), 10-28, 11-11, the 11-10 precedence rule.
- Decision record: owner "1. yes 2. yes 3. yes" to OR41.a on 2026-09-26 (archive branch, PROJECT_AUDIT_PLAN.md:351),
  which was an answer to the audit plan. For the E.2.3 Load sentence: none found.
- Smallest fix: return CLAUDE.md:224-227 to the I2C/SPI bus-device rule of 2026-09-03 and drop the "every other shared
  resource" clause. Delete SPEC:5287-5288, or give it an owner source. Because the owner said "yes" to OR41.a: owner must
  decide (one short question).

### DOCS-5 [L] [VERIFIED] M1 not restored: the memory-error rule still lacks the pre-audit "concrete, non-hypothetical" filter
- Where: SPEC:9184-9196 (I.4(a)); SPEC:6668 (F.2 now only points to I.4(a)); CLAUDE.md:180-188.
- What:
  - Pre-audit F.2 limited `MemoryError` handling to what is "only worth closing for a concrete, non-hypothetical threat"
    (baseline SPECIFICATION.md F.2).
  - The release's I.4(a) opens with "A call site that can raise `MemoryError` from a caller-controllable or growing
    allocation catches `(MemoryError, OSError)` and degrades locally". The criterion is "can raise", the hypothetical opening.
  - The owner's own word "expectable" appears only inside the 09-25 quote.
  - No doc contains "non-hypothetical" (grep).
  - PICTURE section 6 lists "restoring F.2's sentence (M1)" as a cleanup item that needs no owner question. It was not done.
- Ruling/pillar it meets: L2; 10-28 "building upon hypothetical findings is a clear no-go"; PICTURE M1.
- Decision record: PICTURE.md section 6 (marked for the cleanup). None found that withdraws it.
- Smallest fix: in SPEC:9187 change "that can raise" to "that meets an expectable, concrete (non-hypothetical) `MemoryError`
  threat", citing pre-audit F.2 and the owner's 2026-10-28 words. One clause.

### DOCS-6 [L] [VERIFIED for the items named, SUSPECTED for the rest] BACKLOG holds resolved items and was not reconciled with the final bench round
- Where: BACKLOG.md:368-380, :31-44, :70-76, :17-19 (and README.md:1180, which points at the list).
- What:
  - (a) :368-380 calls the wiring-stage requirement "fulfilled; held here only until the owner's audit of the whole refactor
    closes ... Comes out when that audit closes". The audit closed (owner 2026-11-13 09:09, 10:30).
  - (b) :31-44 lists "M1 + S3b" as needing the owner at the bench. M1 ran on 2026-11-13: tests_hardware/README.md:157 and
    :508 record its rig geometry, and the close report has "M1 PASS on relative values".
  - (c) :70-76 lists the VOC-step and CRC stretches as owed. SPEC:6789-6790 already carries their 2026-11-13 silicon
    figures (9.81 ms, 1.75 ms).
  - (d) :17-19 justifies the row IDs by "the whole-project audit plan (on its own branch)".
  - Other rows were probably covered by the final image's flash/bench tiers of 11-11..11-13 (SUSPECTED, not traced row by
    row): :23-30 "no full flash-tier run since" and :227-256 the tooling-consolidation round.
  - A stale "owed" row sends a bench session into repeat runs, some of them wear-gated.
- Ruling/pillar it meets: CLAUDE.md:353-362 ("once an item is resolved, it comes out"); P8 least wear.
- Decision record: none found keeping them.
- Smallest fix:
  - delete :368-380;
  - drop the M1 half of :31-44 and the VOC/CRC half of :70-76;
  - drop the audit-plan clause in :18-19;
  - do one pass of the "owed" list against the final round's hand-back.

### DOCS-7 [L] [VERIFIED] Decision credits name the audit role "lead", outside the decision-record rule's two actors
- Where: SPEC:9332 "(lead, 2026-11-10)"; UART_C_PORT_CHANGELOG.md:218-219 "(lead, 2026-11-03)".
- What:
  - CLAUDE.md:363-366 admits only "(owner, …)" or "(agent, …)".
  - SPEC:9331-9332 uses the "lead" credit to retire an owner-approved decision ("the owner's 2026-09-18 approval of the
    boot-confined collects went with the churn they swept"). CLAUDE.md:378-379 requires such a decision to go back to its
    maker.
  - No owner record of that withdrawal was found in owner_rulings_after_LN118.md (grep "collect").
  - O4 (2026-11-12) accepted agent credits dated 11-06..11-10. Whether it counted "(lead, …)" credits is not recorded.
- Ruling/pillar it meets: L7/P11; CLAUDE.md decision records (1).
- Decision record: none found for SPEC:9332's withdrawal.
- Smallest fix: write "agent" for "lead" at the three sites. If O4 did not cover SPEC:9332, put the withdrawal to the owner
  as one line.

### DOCS-8 [L] [VERIFIED] bench-routines is written for the audit's lead/bench relay setup
- Where: .claude/skills/bench-routines/SKILL.md:18-25 ("The lead's relays arrive on the bench branch", "within the campaign
  plan"), :22 ("Notes and questions to the lead"), :38 ("so the lead carries the fix into the main line");
  work-routines:129-130 ("writing a relay").
- What: the skill is owner-requested (2026-11-06 21:43) and useful. But its roles ("the lead", "relays", "the campaign plan")
  are the audit run's. After the close there is no lead or campaign, only a code session and a bench session.
- Ruling/pillar it meets: CLAUDE.md:353-362 (current state); the brief's rule that audit vocabulary stays out of standing text.
- Decision record: owner 2026-11-06 21:43 (skill requested), 2026-11-07 07:39 (bench may adapt it). None on the vocabulary.
- Smallest fix: "the lead" becomes "the code session" (3 places) and "the campaign plan" becomes "the session's plan". This is
  wording only.

## Checked and clean
- No `audit/`, `PROJECT_AUDIT_PLAN.md`, OR/OF/U/LN/W3b/P01 ID, "lane"-as-process, DECREV or FINDINGS reference in any scoped
  doc. The remaining "audit" words are platform audits, zizmor, or "post-audit" for the C port, which is owner-scoped.
- README.md "Further reading" lists every tracked doc, and no tracked .md outside it exists.
- Backticked repo paths in the docs resolve. The unresolved ones are runtime artifacts, upstream paths or ad-hoc harness
  names.
- THIRD_PARTY_LICENSES.md: every repo path it names exists, and no stale entry was found.
- HEAP_FRAGMENTATION_MEASUREMENTS.md: method only; archive commit `12640c2` is an ancestor of HEAD, and its §7R.5 and §9
  exist.
- legacy/README.md: consistent with the legacy rule.
- DEVICE_REFERENCE.md: no removed mechanism (TimeStale, timed checks) described as current.
- Removed mechanisms (TimeStale, run_inc/check_inc, the LED 120 s give-up, the NeoPixel 300 s rewrite, heap-unwedge,
  get_long_block_lock) appear nowhere as current.
- Owner credits spot-checked against the rulings file, all matching:
  - SPEC:3676 (10-28 decision 6);
  - SPEC:2494-2505 TCP_SND_BUF (11-11);
  - CLAUDE.md:255-258 SCD30 cap (10-21);
  - tests_hardware C-stack/heap bounds (11-11 "A").
- Present and correct: 11-07 levels (SPEC:46-50), 11-07 proportionality lens (SPEC:4887-4893), 11-03/11-02 lean (SPEC:74-80),
  the 10-22 least-wear rule (CLAUDE.md:232, SPEC:4788), and the 11-05 "keep going" (work-routines:139).
- BACKLOG.md: no open refactor target and no parked owner question (the one audit-planned mypy question was settled under
  the 11-11 rules).

## Notes
- The brief lists the boot-confined `gc.collect()` as decided. The release records it as removed: SPEC:9324-9332 and
  CLAUDE.md:312-313 "the firmware calls no `gc.collect()`". The code scanners should confirm which is true.
- Seven SPEC "Record:" lines (e.g. SPEC:4076-4080, 8921, 9331) narrate superseded decisions. They are allowed by the
  decision-record rule but read as history; consider a shorter form.
- Stale small facts:
  - SPEC:8898 gives the 264 B CRC32 as 0.95 ms, while `stall.crc` (SPEC:6790) gives 1.31 ms.
  - SPEC:9330 still says "re-checks it on silicon on the next image".
  - tests_hardware/README.md:134-135 says the DHCP re-keying is confirmed "at the first round".
- CLAUDE.md:470-479 ("every agreed-but-deferred item whose trigger is met is swept in and done") is a scope-growth clause.
  Worth reading against 11-11's "no runaway chains" when DOCS-1 is written.
- SPEC 0.2's pillar list (P1-P11, P7-P11 credited to the agent, 2026-11-05) differs from the audit's P1-P12. It has no
  "extensible without edits elsewhere" or "only the owner's words are decisions" pillar. K.6 (SPEC:10351-10357) lists about
  13 hand-kept per-driver rows across test machinery that a new module must extend. That is a tests-scope concern, noted
  here only.
- Many CLAUDE.md "Code quality tooling" bullets end in a `tests_scripts/test_*.py` that enforces a rule about the docs or
  tools. Most are new since the baseline (see Shape). Whether they count as the "temporary" verification machinery is for
  the tests/tooling scan.
