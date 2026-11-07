# Plan check, R0, R2, the remaining work, the appendices and the estimates (lead, 2026-10-28)

Same checks and verdicts as R1.md.

## R0 (2.2)
- R0.1 the paused lanes close; patches complete. W: S/u35r/paused_pub/ holds LD+CM3, CRr2c, IN2 (made 08:12-08:13);
  no file in those worktrees is newer (find -newer, 14:3x); CRr2d's worktree has only node_modules; CMr1n, RF1 and
  CM4 never started. Only audit/u35-in2 and audit/u35-ldcm3 have commits outside 497b3eda, both in their patches.
  HOLDS. FIX (scope): every other lane worktree (about 45, all merged into the integration head) goes too.
- R0.2 "The twin record goes ... about 2,260 lines with its tests". W: the 2,260 (E.md:375) counts the record chain
  plus `tests_hardware/twin_board.py` (143) and `tests_scripts/test_twin_board.py` (281). twin_board.py implements
  `--twin` (tests_hardware/conftest.py:96, :214-480), which OR21.a's hardware-tests-on-the-twin needs and which the
  standing hardware rule uses. FIX: R0 removes the record only: `tests_hardware/twin_record.json` (1,466),
  `tests_scripts/test_twin_record.py` (138), `scripts/record_twin_instrument_runs.py` (231), with their references
  (BACKLOG.md:942-943, HEAP_FRAGMENTATION_MEASUREMENTS.md:282, digital_twin/README.md:653-654,
  digital_twin/run_device_script.py:3, pyproject.toml:299-307, tests_hardware/README.md:557, SPECIFICATION.md:13198's
  Part N row): about 1,835 lines plus a few doc lines. twin_board.py and its test stay.
- R0.3 "DECREV 9's three static checks". Item 3 is a Unix-port run (a near-exhausted C stack), not static, and its
  board half ("against the board's peak") is REPORT 7 item 1. FIX: "three checks before B1: two reads, one Unix-port
  run". HOLDS otherwise.
- R0.4 the baseline numbers per device: a dev firmware build takes about 1 minute on a built toolchain (RUNS.md
  6293-6296); 12 builds (six devices, two trees) are about 15 minutes. With the C-stack run, the twin record's removal
  (its doc edits, the fast checks, one push) and the checklist, R0 is about 1.5-2 h, not "about 1". FIX: estimate
  1.5-2 h, budget 2 h (decision 5's rule: the top of the estimate).
- R0.5 rules into the checklist; lists start empty. HOLDS.

## R2 (2.4)
- R2.1 the twin record: see R0.2.
- R2.2 removed as "audit machinery or docs policing born in the audit": `test_citations.py`,
  `test_decision_vocabulary.py`. G: CLAUDE.md:524-537, "Decision records (owner, 2026-09-26: the five prevention
  rules, answered '4. yes')", rule (5) names both tests; the rules are DECISION_PROVENANCE.md 2.4 (rule 5: "A
  tests_scripts/ check fails on actorless decision vocabulary ... and on any citation to a miss..."), OR68 "4. yes".
  Against it, the owner's 2026-10-28 "The audit verification machinery is just a temporary tool" (rulings :189), said
  of the audit's verification machinery. FACT: two owner statements pull apart; a new clarification (i), asked at R2's
  checkpoint with both quotes; until then both checks stay, their allow-lists only shrinking.
- R2.3 "the repo-scan reader's own tests" removed. U: `tests_scripts/_repo_scan.py` is read by the comment-cap gate
  (an owner rule the plan keeps) and by both decision-records checks and 9 more gates. Its two tests
  (`test_repo_scan_template_literals.py`, `test_repo_scan_regex_literals.py`) test the reader the owner's gate runs on.
  FIX: they are "a tool test covered by an owner row": kept, slimmed where they repeat.
- R2.4 the ~1,700 lines that pin SPECIFICATION.md tables (E.md:141: tunables register, timing budget, lock and task
  tables, memory catalog, threat model, UART changelog). Some serve owner rows: the UART changelog rule (CLAUDE.md),
  Part N inside OR30.a's scope. FIX: the row says each file is classified with its owner basis checked, not removed
  as a block.
- R2.5 the bite self-tests: OR21.a (2) "Not adopted: no new permanent control arms in CI". HOLDS.
- R2.6 the seven fixed-time sleeps (DECREV 3 row 137, OR37.a (3) "yes, all exactly like this"), the 89 s
  retirement, the stop file and the rig override (DECREV 3.2-3.3). HOLDS.
- R2.7 CI timeouts from measured need, the two retries kept, the twin matrix sized, the hang backstop. HOLDS.
- R2.8 Part N to OR30.a's scope; the heap-floor row loses "measurement owed" (DECREV 4.6). HOLDS.
- R2.9 scripts/ and toolchain/ (build-chain tool files) and mockdata/ are classified in R2. FIX: named.

## The remaining work (3.1, 3.2)
- RW.1 the R3 rows cite OR16.a, OR19.a, OR21.a, OR22.a, OR23.a, OR25.a, OR37.a, OR38.a, OR39.a, OR40.a, OR41.a,
  OR49.a, OR26.a, OR8.a, OR17.a, OR29.a: each read in PROJECT_AUDIT_PLAN.md 3.2; the plan's summaries match. The
  planting-scope quote is the owner's of 2026-10-23 (rulings :40), refining OR16.a (4). HOLDS.
- RW.2 round 1's preparation, "the queue in order": OR8.a names `REAL_HARDWARE_TEST_QUEUE.md`, retired on 2026-09-25;
  the queue is BACKLOG.md's "Real-hardware work still owed" (PROJECT_AUDIT_PLAN.md:259-261). FIX: named.
- RW.3 round 1 "the twelve items of REPORT.md 7". Four of them now decide nothing: item 1 (C-stack depth; the reboot
  stays, "The OK in the review stay valid"), item 2 (the FRAM line with the chip absent; decision 3 item 1, "No
  measurement is needed"), item 6 (eight soft callbacks; decision 3 item 2, "No measurement"), item 9 (WS2812 state;
  NP-5 is reverted, DECREV 9.10 "only if a fix is ever wanted back"). Item 11 repeats the plan's own owed-rows line.
  FIX: round 1 runs items 3, 4, 5, 7, 8, 10, 11 and the optional 12; items 1, 2, 6 and 9 are not run (decided), each
  noted as knowledge not gathered.
- RW.4 R4, R5, the last round and D: the rows cited (OR27.a, OR13, OR14, OR15.a, OR44.a, OR10/OR10.b, OR68.a, OR9.a,
  OR11, OR5.a, OR52.a, OR40.a (3), OR11.a) read; HOLDS.

## Appendices
- AP.1 A's rows 33-35, "the caps are cheap bounds the owner wants": OR103, "No unbounded counters anywhere". HOLDS;
  FIX: cite OR103.
- AP.2 A's row 25-27, Run 11: "Question 1: This is okay, go ahead." (rulings :39). HOLDS.
- AP.3 A's row 49, the twin record retires in R0: with R0.2's narrowing, `--twin` stays for R3. FIX: worded.
- AP.4 the ledger items 1-9 and B's U36/U37 groups: their routing matches 3.1 and 3.2. HOLDS.

## Estimates (5) and budgets (decision 5)
- ES.1 R0: 1.5-2 h (R0.4). R1: the checks change content, not size: B6's construction refusals and trim() stay,
  B8's boot-loop rules stay (less removal), B2's W69 restore and B4's second E27 site add a few lines of work. R1
  stays 19-25 h. R2 stays 5-8 h with R2.2-R2.4 smaller. The rest unchanged.
- ES.2 a new row: the plan check, before R0, 22 h budget (about 1 h used), and the falsification agents as its final
  verification (owner, 2026-10-28: "Add this as a final verification and adapt the run counts accordingly").
