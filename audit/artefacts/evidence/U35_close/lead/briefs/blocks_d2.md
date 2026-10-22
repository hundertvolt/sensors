# U35 lane D, blocks D2a and D2b (lead, 2026-10-22)

Read `S/CHECKLIST.md`, then `S/u35/briefs/common_u35.md` (Reading, Sites, Rules, Hand-back), then your section. About
60-80 tool calls: past 80, commit what is done and hand back the rest (CHECKLIST 21). CHECKLIST 22 (disk) is binding.
Batch independent reads and edits as parallel calls (CHECKLIST 17). Your start is the tree, not the plan's old lines.

## Both blocks
- Branch `audit/u35-d2` at `e06966b` (the integration head with block K merged and the 120-character count on), worktree
  `S/wt-u35d2` (`git -C /home/user/sensors worktree add -b audit/u35-d2 S/wt-u35d2 e06966b`), then
  `S/u23/rebuild.sh S/wt-u35d2`. D2b continues on the same branch and worktree. Logs in `S/u35/laneD/d2a/`, `d2b/`.
- Files: SPECIFICATION.md (both blocks); BACKLOG.md, tests_hardware/README.md and CLAUDE.md (D2b only). Nothing else.
- Sources, in this order: the tree; `S/u35/relay.md` (all of `## D`, and every `<TAG ...>` line in any section);
  the LEAD NOTES in `S/u35/lane_plan.md` that name D2 (grep `D2`); `S/u35/handbacks/D1_final.md` ("Left for D2/D3").
  A relay line cites lines of an older tree: locate each site by its quoted text. Where a relay value or name differs
  from the tree, the tree wins (a later block changed it); say so in the hand-back.
- Every new row and sentence carries its source's actor and date; a basis marked estimated stays marked estimated.
  Comment and doc lines wrap as the surrounding text does (at most about 120 characters, as Part N's table already is).
- Decision (lead, 2026-10-22): D2 starts before its W8 slot because its inputs (every lane, B1) are merged. B2's values
  (steps 146, 147, 105's Basis cells, 159, 162, 163) stay D3's; leave each cell or sentence they fill as it is.

## D2a: the machine-checked rows (SPECIFICATION.md only)
Goal: these tests_scripts files go green on your head, each with its red first seen on `e06966b`:
1. test_tunables_register.py: 16 tags without a Part N row and one row without a tag (run it for the list).
   - Each new row takes its `<TAG>` line's value, site and basis, in D1's row form (`git show 5f97080`).
   - `config.flush_slice_bytes` replaces P3's `config.flush_slice_chars` (P4's line); the comm hazard bound is U3a's 4,
     not U2's 14; `uart.hazard_recovery_attempts`'s constant is `_HAZARD_RECOVERY_ATTEMPTS` (U3f's line).
   - `l1.notification_neopixel_wait_until_timeout_ms` is withdrawn (N3's line under `## N`): withdraw its row as D1
     withdrew `l1.asy_notification_service_override_bound_ms`, and fix any row that names it.
   - Rows whose basis a lead line or LEAD NOTES changed (V1's flap window and feed interval, R2's
     `l3.uart_idle_poll_rate_cancel_settle_ms`, the driven-second bounds LEAD NOTES name as D2's): restate the basis.
2. test_level_containment.py: `fault_storm`, `ntp_unreachable_load`, `reader_saturation` and `watchdog_fault` have no
   E.6.6 row. Read each scenario in scripts/_digital_twin_scenarios.py and the test's rule for a counterpart; write
   each row as its neighbours are written, naming the level, the twin check and any L3/L4 counterpart or its absence.
3. test_task_inventory.py (4 reds): one C.9 row for `UARTLinkDriver._two_initiations()` (U3e's line as U3f amends
   it). The NeoPixel lines are the test's self-tests counting that one finding (LEAD NOTES 70); the row should turn all
   four green. If it does not, stop and report what remains.
4. U3e's E.6.6 `uart-hazards-under-api-load` row, I.2's run-phase catalog entry for `_hazard_facts` (the
   `_RUN_PHASE_ALLOWED` entry is the lead's, landed), and A.11's unauthenticated-writes row naming `UartHazards`
   (test_threat_model_statement.py). Run test_memory_catalog.py and test_threat_model_statement.py either way.
Checks: after each commit, those five files plus test_citations, test_decision_vocabulary, test_legacy_paths; at the
end, the 17 repo-wide scans once (`S/u32/briefs/common_u32.md`, "Before your lane's final"). Expected red there:
test_comment_block_cap's `tests/_sensortask_scenarios.py:477` (lane V's, merging next). Any other red: name it.
Commit subject `U35 lane D2a: <summary>`; the body names each row added, changed or withdrawn.
Hand-back (at most 35 lines): the commit; each test's red-then-green; every relay line or LEAD NOTES item you used,
and any relay value the tree overrode; what is left for D2b; last line "nothing of mine is running".

## D2b: the relay's prose into SPECIFICATION.md, and BACKLOG.md's questions 5 and 7
Start: branch `audit/u35-d2` at `5d0e16f` in `S/wt-u35d2` (D2a's work, merged into int as `85f3104`; the lead's fix
`5d0e16f` corrected two rows' attribution: the owner decided the hazards are proven under API load, the hazard mode is
the agent's form of that proof). Read `S/u35/handbacks/D2a_final.md`, its "Left for D2b" list: these are yours.
1. Each `## D` relay line not yet landed, into the section it names, each fact checked against the tree:
   - C4's `/status` `TimeStale` in A.8 and F.1's gate sentence, with the decision (LEAD NOTES 11), and BACKLOG.md's
     question 7 removed (its decision now lives in SPECIFICATION.md with the owner's words);
   - P1's and the lead's P1 line: E.5.1's two gone entries and its "six statements" paragraph;
   - U2's J.7 latency sentence; P2b's FRAM sentence (blank verdict, `verify_present()`); Q2's E.1 port sentence;
   - P3's and P4's lines: J.6, F.3's `stall.flash_program`, J.6's "littlefs runs without yielding" sentence, A.4,
     C.7.3, and Part N's `uart.flash_hold_max_ms` basis (D2a left it: one group of facts);
   - U3e's lines: J.7's "not written" sentence, A.8's `UartHazards` sentence, G.2's `_run_status_cmd()`, and
     BACKLOG.md's question 5 removed (its decision stated where A.8 and E.6.6 describe the mode); U3f's None verdict in
     J.7 and A.8; R2's Part J E22 fact; T2b's E.9 window sentence and Run 3 as a reader of `rate.persisted_log`.
2. An attribution rule this needs: a sentence naming the hazard mode credits the owner only with the requirement (the
   hazards proven under API load, quoted with its question) and the agent with the mode, as `5d0e16f`'s rows do.
Checks after each commit: test_citations, test_decision_vocabulary, test_legacy_paths, test_tunables_register,
test_threat_model_statement, test_level_containment, and every tests_scripts reader of a SPEC section you changed (grep
the section's name in tests_scripts/). No 17 scans in D2b: D2c runs them for both.
Commit subject `U35 lane D2b: <summary>`. Hand-back (at most 35 lines): the commits; each relay line used, landed or
found already landed; each relay fact the tree overrode; what is left; last line "nothing of mine is running".

## D2c: the owner answers, CLAUDE.md and tests_hardware/README.md
Start: branch `audit/u35-d2`, fast-forwarded by the lead to the integration head `03c46b6` (D2b merged as `57a005e`,
lane V's last block and a lead comment fix after it), in `S/wt-u35d2`; run `S/u23/rebuild.sh S/wt-u35d2` first. Read
`S/u35/handbacks/D2b_final.md`. The owner's words and questions: `audit/REGISTER.md`'s three "U33 | Owner answer"
rows (lines 783-785 at `03c46b6`), quoted exactly; LEAD NOTES 12-14 say what each answer asks of the documents.
1. BACKLOG.md's owner questions 1, 2, 3, 4 and 6 come out; each decision is stated, with the owner's words and the
   question, where SPECIFICATION.md describes the behaviour (rule 4):
   - 1 (a): where the twin suite's crash naming is described (a signal death fails Run 5c's check by name, and
     nothing retries a twin job: LEAD NOTES 13);
   - 2 (a): the read timer's failure path and the supervisor's restart budget; 4 (a): the SCD30 driver's start
     sequence (LEAD NOTES 12);
   - 3 (a): CLAUDE.md's `scd30_extra_write` sentence ("a *second* SCD30 NVM write beyond the routine per-session
     one") and the matching tests_hardware/README.md and SPECIFICATION.md text restated to what the flag admits: the
     four `scd30_extra_write` tests, up to 12 further writes, 13 per session with both flags, plus at most one start
     command (LEAD NOTES 14); check each figure against tests_hardware/ first;
   - 6 (c): CLAUDE.md's "How a block is counted" sentence gains the length rule, as the relay's block-K lead line
     words it; `tests_scripts/test_comment_block_cap.py` already counts it (`_WRAP_WIDTH = 120`, `e06966b`).
   BACKLOG.md's owner-question list then holds no open question: keep its heading and its rule.
2. tests_hardware/README.md: H3's two relay lines (the loop-lag test's stale facts, about :826-834, and the twin
   record's text), and U3e's item (the "not written" sentence, about :1090).
3. CLAUDE.md lines wrap at about 100 characters, as the file does; change nothing else there.
Checks after each commit: test_citations, test_decision_vocabulary, test_legacy_paths, and every tests_scripts reader
of a file you changed (grep `CLAUDE.md`, `BACKLOG.md` and `tests_hardware/README.md` in tests_scripts/). No 17 scans:
D2d runs them. Commit subject `U35 lane D2c: <summary>`. Hand-back (at most 35 lines): the commits; each answer with
where its decision now lives; each figure you checked; what is left; last line "nothing of mine is running".

## D2d: D1's open steps, then the 17 scans (D2's last block)
Start: branch `audit/u35-d2` at `5392e71` (D2c) in `S/wt-u35d2`, already rebuilt. Read `S/u35/handbacks/D2c_final.md`
and `S/u35/handbacks/D1_final.md`'s "Left for D2/D3" list.
1. D1's steps 34, 37 (5), 111, 112, 126, 128, 142, 143 and 144. Get each text with `python3 -I S/u35/tools/steps.py
   --standing <numbers>` and its P1 row from `S/u35/lane_plan.md`. D2a-D2c already landed parts of several (111's E.5.1
   register, 144's J.7 latency sentence, 128's dependency 143): check each against the tree first, and write only what
   is missing, into D's three files (SPECIFICATION.md, BACKLOG.md, tests_hardware/README.md). A step whose input is
   B2's measurement (146, 147, 105's Basis cells, 159, 162, 163) stays D3's, as do 158 (the unit's build-environment
   list) and the E.5.1 check against the gate's coverage report: leave those as they are.
2. Not yours, routed by the lead: digital_twin/README.md's twin-record text (lane T's T4) and
   HEAP_FRAGMENTATION_MEASUREMENTS.md:282 (U36).
3. At the end, the 17 repo-wide scans once (`S/u32/briefs/common_u32.md`, "Before your lane's final"), on your head, in
   one process; expected red: none now that lane V's block fits (any red: name it with its line).
Checks after each commit: test_citations, test_decision_vocabulary, test_legacy_paths and the readers of each section
you changed. Commit subject `U35 lane D2d: <summary>`. Hand-back (at most 35 lines): the commits; per step, landed by
you, found landed, or left with what it waits on; the 17 scans' result; last line "nothing of mine is running".

### D2d relaunch (lead, 2026-10-22)
The first D2d run was stopped at 06:02 UTC with no commit. Start now: `audit/u35-d2` fast-forwarded to `6dabd9b`
(the least-wear hard rule in CLAUDE.md), rebuilt. Not yours, held for D2e after block Z: every sentence describing
the config file's write path (SPECIFICATION.md A.4, C.7.3, F.3's stall.flash_program, J.6, Part N's
`config.flush_slice_bytes` row and `uart.flash_hold_max_ms`'s basis); leave them as they are. Every sentence you
edit keeps its meaning, actor, qualifier and scope unless the step itself changes them, and the commit says which.

## D2e: the least-wear rule's docs, the single write's sentences, and step 142 (lead, 2026-10-22)
Start: `audit/u35-d2` fast-forwarded to the integration head (named when starting you; Z, O, J merged), rebuilt. Your
files: SPECIFICATION.md, CLAUDE.md, BACKLOG.md, tests_hardware/README.md. Everything to land is in
`S/u35/lead/d2e_carry.md` (items 1-7) with its source; read the hand-backs it names (handbacks/Z1_final.md,
O1_final.md, J1_final.md, D2d_final.md) and LEAD NOTES 86, 95, 101 and 103 in `S/u35/lane_plan.md` for the owner's
words. Rules for every sentence: the owner's decisions quote the owner's words and the question; a paraphrase is
marked "paraphrase"; nothing cites an audit ID, a lane or a temporary plan; comment and doc lines as the tree has
them (about 100 characters for docs). The accepted degradation (item 2) states its consequences exactly as LEAD
NOTES 86 lists them, and the single write's power-cut fact (item 1, C.7.3) as Z found it. The guard's stated limit
(LEAD NOTES 103's last sentence) goes where the guard is described. Expected red until your Part N edit:
tests_scripts/test_tunables_register.py (`config.flush_slice_bytes`); it must be green after it. Checks after each
commit: test_citations, test_decision_vocabulary, test_legacy_paths, test_tunables_register and the readers of each
section you changed; at the end the 17 scans once. Commit subject `U35 lane D2e: <summary>`. Hand-back at most 35
lines: commits, per carry item landed or left with its reason, checks, anything for the lead (an allow-list line your
edit orphans is the lead's), last line "nothing of mine is running".
