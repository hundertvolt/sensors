F scan, written by the lane (Wed Oct 28 07:54:05 UTC 2026)

Range `25caf528` (2026-09-25) .. `497b3eda`, read in `S/wt-u35int`, `arduino/` excluded. Read-only: nothing was
edited, run or built in the worktree. My working files (classifier, samples) are in `S/u35r/scan/Fwork/`.

## Method, and how far to trust the numbers

- **Unit.** "Added" means git numstat insertions (a rewritten line counts once as added, once as deleted). Blank
  lines are left out of every class count. Bytes (KB) are given too, because Part N's table rows are single lines of
  377 characters at the median (up to 1,971), so a line count understates them.
- **Mechanical pass** (`Fwork/classify2.py`): every added line sits in a block (paragraph, list item or table row).
  The block is split into sentences, and each sentence goes to one class. **Audit-process** means it names the audit,
  post-audit work, a lane, a hand-back, an owner Q&A ("asked, paraphrase", "the question, paraphrase") or a decision
  "on the owner's behalf for review". **History** means narrative markers: "used to", "no longer", "was fixed/
  removed/…", "found the hard way", dated event verbs, CI run ids. **Duplication** means at least half of its 8-word
  shingles also stand in another doc or another SPEC Part. Everything else is **knowledge**. Provenance
  parentheticals, "(owner|agent, date[, commit][: 'quote'])", are measured on their own: short tags in one bucket,
  quotes and Q&A in another. The mechanical pass gives *floors* for history and duplication, because it misses
  reworded restatements.
- **Calibration.** For SPEC A-M I read and classified 130 added sentences by hand, drawn at random and weighted by
  length. The split of knowledge into product / machinery / code restatement, and the history share, come from that
  sample (about ±8 points). Part N was counted row by row. For the other docs I read each section's growth and
  corrected the mechanical counts where whole sections are of one kind (BACKLOG's chroot log, tests_hardware's
  "N-th pass" sections).

## 1. Totals, permanent docs (everything but PROJECT_AUDIT_PLAN.md and audit/)

| doc | lines old -> new | KB old -> new | +added / -deleted |
|---|---|---|---|
| SPECIFICATION.md | 6,785 -> 13,360 | 514 -> 1,573 | +9,201 / -2,626 |
| tests_hardware/README.md | 1,414 -> 2,090 | 113 -> 176 | +1,266 / -590 |
| BACKLOG.md | 883 -> 1,284 | 76 -> 112 | +993 / -592 |
| digital_twin/README.md | 919 -> 1,246 | 72 -> 113 | +925 / -598 |
| CLAUDE.md | 1,067 -> 1,276 | 90 -> 109 | +598 / -389 |
| README.md | 795 -> 988 | 53 -> 68 | +467 / -274 |
| UART_C_PORT_CHANGELOG.md | 128 -> 241 | 34 -> 63 | +163 / -50 |
| THIRD_PARTY_LICENSES.md | 205 -> 280 | 15 -> 21 | +153 / -78 |
| DEVICE_REFERENCE.md | 101 -> 174 | 7 -> 12 | +92 / -19 |
| legacy/README.md (new) | 0 -> 53 | 0 -> 3 | +53 |
| HEAP_FRAGMENTATION_MEASUREMENTS.md | 393 -> 401 | 29 -> 30 | +30 / -22 |
| HARDWARE_TEST_HANDOVER.md, REAL_HARDWARE_TEST_QUEUE.md, dev_legacy/README.md (deleted) | 1,272 -> 0 | 97 -> 0 | -1,272 |
| **all permanent docs** | **13,962 -> 21,393 (+53 %)** | **1,099 -> 2,281 (+108 %)** | **+13,941 / -6,510** |
| PROJECT_AUDIT_PLAN.md (temporary) | 2,740 -> 3,335 | 217 -> 512 | +1,019 / -424, 217 commits |

SPECIFICATION.md accounts for +1,059 KB of the +1,182 KB. Its new Part N alone is 562 KB, 47 % of all doc growth in
bytes.

**Class totals over the ~13,390 added non-blank lines of the permanent docs** (estimates, see the method):

| class | lines | share | where |
|---|---|---|---|
| knowledge | ~11,620 | ~87 % | about half of it documents the test/CI/tooling machinery: SPEC ~2,510 + Part N's 1,127 test-tier rows + digital_twin 835 + tests_hardware ~975 + README ~275 + CLAUDE ~180. About 930 lines are SPEC prose restating code |
| history / narrative | ~1,145 | ~8.5 % | BACKLOG's chroot running list 447, SPEC ~360, tests_hardware's pass narratives ~180, CLAUDE 68 |
| audit-process | ~380 | ~3 % | owner Q&A quotes, "decided on the owner's behalf for review", "post-audit only"; SPEC ~220, CLAUDE ~95; plus PROJECT_AUDIT_PLAN's +1,019 |
| provenance tags (short) | ~145 | ~1 % | required by CLAUDE.md's "Decision records" rule; Part N's Basis cells add 21 KB inside its rows |
| duplication (literal) | ~110 | ~1 % | the floor; reworded restatement across CLAUDE/SPEC/READMEs comes on top (section 3) |

## 2. Per doc

### SPECIFICATION.md, by Part

| Part | lines old -> new | KB old -> new | added non-blank | what grew (largest sections) |
|---|---|---|---|---|
| A Overview | 659 -> 1,368 | 52 -> 126 | 1,077 | A.8 REST API reference 4 -> 27 KB; A.4 deep reference 12 -> 33 KB (FRAM semantics); A.11 threat model new, 12 KB; A.7 construction order 17 -> 23 KB |
| B Toolchain | 787 -> 1,598 | 56 -> 125 | 1,026 | B.14 build overrides 25 -> 51 KB; B.10 CI 8 -> 23 KB; B.15 mypy passes 5 -> 10; B.4 env isolation 0 -> 5 |
| C Drivers | 1,101 -> 1,752 | 91 -> 143 | 1,169 | C.7 error/log contract 24 -> 35; C.8 concurrency and lock table 14 -> 25; C.3 6 -> 15; C.9 task table 9 -> 16 |
| D Checklist | 156 -> 268 | 9 -> 19 | 132 | new checklist items |
| E Testing | 690 -> 1,186 | 50 -> 103 | 713 | E.6 tiers 10 -> 25; E.3; E.10 runner summary block new; E.1 |
| F Platform | 708 -> 1,400 | 53 -> 144 | 891 | F.1 core facts 12 -> 33; F.7 Unix-port rig new, 20 KB; F.3 timing table 0 -> 19; F.5 1.29 delta 28 -> 43; F.9 workarounds new, 10 |
| G Primitives | 130 -> 330 | 10 -> 27 | 240 | G.2 catalog 7 -> 25 |
| H Website | 504 -> 807 | 40 -> 70 | 501 | H.7 twin integration 13 -> 24; H.4 |
| I Memory | 384 -> 714 | 31 -> 58 | 487 | I.2 allocation-site catalog 3 -> 20 KB; I.4 13 -> 21 |
| J UART | 535 -> 795 | 39 -> 62 | 424 | J.7 testing 4 -> 15; J.6; J.8 |
| K New-module checklist | 302 -> 315 | 22 -> 23 | 44 | — |
| L Build chain | 587 -> 932 | 38 -> 71 | 497 | L.3 TOML key table 5 -> 16; L.5 build-script bar 10 -> 19; L.4; L.6 |
| M Chips | 214 -> 424 | 15 -> 31 | 223 | M.2 SCD30 new; M.1 ISL29125 |
| N Tunables (new) | 0 -> 1,442 | 0 -> 562 | 1,405 | N.3 register: 1,284 rows, 540 KB |

**Parts A-M** (7,424 added non-blank lines, ~718 KB):

| class | lines | share | mechanical floor |
|---|---|---|---|
| knowledge: product (firmware, buildgen, website contracts, platform facts with sources, rules) | ~3,220 | 43 % | — |
| knowledge: test/CI/tooling machinery | ~2,510 | 34 % | — |
| knowledge: code-level restatement | ~930 | 13 % | — |
| history / narrative | ~360 | 5 % | 285 |
| audit-process (Q&A quotes 150, audit references ~70) | ~220 | 3 % | 201 |
| provenance tags | ~110 | 1.5 % | 112 |
| duplication | ~70 | 1 % | 47 |

- **Product knowledge, worth keeping.** A.8's REST reference (each endpoint, its fields and refusals). A.11's threat
  model. F.3's stall/hold rows (e.g. `stall.fram_command`: 3,395 µs, dev, 2026-09-25). F.9's workarounds and what
  retires each. The FRAM protocol intent in A.4 (L173-300: why the status bytes are a lock, and why an abrupt
  reset's loss is all-or-nothing). The reset-reason codes (F, L~7026). L.3's key table.
- **Machinery** (knowledge about the test rig, not the product). B.10 ("Every job that syncs runs
  `scripts/uv_sync_retried.sh`…", the apt-mirror rate derivation). B.14's lwIP host build. E.10's `Result:` line
  grammar (`PASS (<reason>)`, `NOT CLEAN`). F.7's Unix-port differences. The E.6.6 containment rows
  (`twin-instrument`, `scd30-non-finite-words`). B.15's `mypy_path` entries.
- **Code-level restatement.** I.2 has one paragraph per module (e.g. L8954 "`asy_isl29125_driver.py` — construction,
  long-lived, fixed: the reader, its `ISL29125_I2C`, the 6-byte RGB burst buffer…"). A.7 lists construction steps
  (L805 "13b. *(`dev` only)* two buildgen-generated `[[instance]]` entries construct…"), and there are per-function
  behaviours such as "`feed_watchdog()` itself is a no-op on a watchdog-less build…" (A, L837). Much of this was moved
  there by the 3-line comment cap ("load-bearing detail … moves to SPECIFICATION.md"). Pointers to SPEC from `src/`
  went 221 -> 362.
- **History.** F L6728 "But `write_config()` itself no longer performs that write inline…". I.4 L~9245 "Searching for
  `MemoryError` alone — which all four gates did until 2026-09-22 — …". E.7 L6118 "Real GitHub-runner CI kept tripping
  the `gc.mem_free()` trend check occasionally even after that move (2026-09-14)". F.5 "That test's thresholds changed
  on 2026-09-19…". B.10 "Some `azure.archive.ubuntu.com` nodes … on run 40570757608…". C L4626 "(SGP40's own
  compensation-source dependency used to be a second wiring entry here…)". Kept, not pruned: I's opening "Written up
  during the 2026-09-07 systematic memory-safety audit…" (L8741).
- **Audit-process.** A.1 L40-44 "Post-audit only (owner, 2026-09-25: 'the C port stays out of scope…') … (secret
  scan: owner, 2026-09-30: 'No, it stays fully out of the audit', asked, paraphrase: whether the history secret scan
  reads arduino/)". A.4 L195 "the agent's decision (agent, 2026-10-22), accepted by the owner on its report …:
  "Solutions you proposed agreed."" (the same quote again at L1259). F L7054 "(owner, 2026-10-26: "B is fine, very
  rare edge case"; the question, paraphrase: …)". A.8 L1042 "…was decided on the owner's behalf for review". J L10055 "the
  hazard mode is the agent's form of that proof, decided on the owner's behalf for review". Permanent docs carry no
  unit, OR, PQ or AF ids: the citation rule holds.
- **Provenance.** Parenthesized owner/agent markers in SPEC went from 35 to 1,788 (1.3 -> 51.5 KB). 139 of them
  carry quotes or Q&A (17.4 KB); 1,105 of the agent markers are in Part N. Commit-hash citations went from 0 to 834
  (724 in N).

**Part N** (1,405 added lines, 562 KB) is the owner-requested register (owner, 2026-09-25). It is knowledge by kind,
but its scale stands out:

| rows | count | KB | basis |
|---|---|---|---|
| firmware / build (`web.`, `uart.`, `wifi.`, `system.`, `tool.`, …) | 157 | 72 | 98 "estimated (agent, `<commit>`) — measurement owed"; 27 legacy; 6 measured; 78 with Margin "unknown until measured" |
| test / CI / runner (`l0.`-`l4.`, `ci.`, `runner.`, `twin.`) | 1,127 | 466 | 951 estimated with measurement owed, 162 measured |
| rule rows and rules text (N.1, N.2, N.4) | ~120 lines | ~24 | — |

So 88 % of the register's rows record test-tier sleeps, bounds and timeouts. 84 % of those rows carry no measured
basis. "Measurement owed" appears 1,063 times in SPEC and once in BACKLOG.

### CLAUDE.md (+598 / -389, net +209)

| class | lines |
|---|---|
| knowledge | ~414: new rules ~85 (least wear in production, the dependency refresh, decision records, the workflow for substantial work, the subagent split, `@tunable`, branch-green, the `dev` bar); rule elaboration ~150; test/CI tooling ~180 |
| history | ~68 (e.g. "first accepted 'for now', owner 2026-07-13, `b64857d`"; "The one change it ever got is its byte-identical move into `legacy/`") |
| audit-process | ~95: 45 lines of quotes/Q&A, ~50 lines naming the audit (the `MemoryError` rule's "asked, paraphrase, to confirm an audit method…") |
| provenance tags | ~10 (markers 11 -> 91) |
| duplication | ~13 literal |

- **Rules have grown into essays.** The UART rule (L134) is 55 lines, with buildgen `_OVERRIDES`/
  `SINGLETON_SERVICE_DRIVERS` internals and a 5-line owner quote. Memory-safety discipline (L395) is 83 lines, test
  wear (L323) 45, the comment cap (L539) 45. "Work split across subagents" (L604) is a standing rule wrapped in a
  cost narrative ("a week's measured cost was about 81 % agents re-reading…") and four verbatim owner answers.
- **Kept although the rule says history goes:** the `improved-quality/` bullets (L70, L1058); the six "Known … cause,
  fixed" bullets (L790-895, 106 lines). Those do carry diagnostic value ("don't re-diagnose").

### BACKLOG.md (+993 / -592, net +401)

| section | lines old -> new | added | class |
|---|---|---|---|
| Real-hardware work still owed (new) | 0 -> 372 | 369 | knowledge (owed work). It consolidates the two deleted queue/handover files (-594 there), so net -225 |
| chroot-verification running list (one bullet, L576-1121) | 99 -> 546 | 447 | **history in log form**: dated per-change entries ("2026-09-22 adds a second override…", "**2026-10-26, …, by the leg that covers each change**"), 49 KB |
| open questions | 285 -> 146 | 65 | pruned. Still holds a resolved-bug narrative: the ISL29125 item (L50, "Root cause, traced through the real code … fixed, unit-tested and confirmed on silicon") |
| deferred / refactor / owner questions | — | ~107 | knowledge. The owner-question list is empty |

Totals: knowledge ~510, history ~480, audit-process ~10, duplication ~5.

### README.md (+467 / -274, net +193)

Knowledge ~420. Product and user material is ~163 lines: the new "Moving a legacy unit to this firmware (reflash
runbook)", 78 lines; building and flashing 37. Machinery is ~275 lines: dev environment 46, code quality 76, website
tooling 48, hardware tiers 30, twin 74. History 16, audit-process 13, duplication 2.

Stale text: "Further reading" still says PROJECT_AUDIT_PLAN.md is "Planning only: its execution is blocked until the
owner's explicit go-ahead". Execution has run since 2026-10-06 (the plan's own status line). It also says audit/
holds "later the findings register", which exists. The section keeps its pre-existing merge history ("Produced by a
first-pass doc-scatter cleanup that merged…", "`UART_PROMOTION_REQUIREMENTS.md` went the same way…", ~20 lines).

### digital_twin/README.md (+925 / -598, net +327)

All of it is harness knowledge (~835). The fidelity table is new: 84 rows, 21 KB, each twin fact with its evidence
and level, a real gain. Runner flags 60 lines new; "What's here" +161; the CI suite +197 rewritten. History ~17,
audit-process ~12 (e.g. L874 "(the owner's option 1 for the unit tests, owner, 2026-10-20, asked, paraphrase…)"),
duplication ~5. "Known gaps" shrank from 46 lines to 6, so it was pruned.

### tests_hardware/README.md (+1,266 / -590, net +676)

| section | lines | added | class |
|---|---|---|---|
| The dev bench (wiring, dated bench state, facts, br0 bridge, tools) | 198 | 197 | knowledge moved in from the deleted dev_legacy/README.md (-678), so consolidation |
| topic sections (bench traps, heap under load, reset codes, recovery rungs, hotspot role reversal, …) | 639 | 450 | harness knowledge |
| Known assumptions and open findings | 299 | 147 | mixed |
| "Third pass" … "Tenth pass" | 603 (49 KB) | 162 | **history**: pre-existing pass narratives, kept and edited in place (e.g. L1368 "Answer at the time, honestly: no…") |
| intro, prerequisites, environment, running, persistence gating, FRAM capacity | 351 | 310 | harness knowledge |

Totals: knowledge ~975, history ~180, duplication ~11, audit-process ~5.

### Other root *.md

- **DEVICE_REFERENCE.md** (+92, end-user facing): knowledge 73 (LED legend, Wi-Fi modes, the `ResetErrors`
  refusals). There are 11 lines of owner Q&A inside the user doc: L161-172 "(owner, 2026-10-13, asked "Clear nothing
  when ResetErrors answers Failed in…": '1 b'", "(owner, 2026-10-20, asked, paraphrase, whether to fix that case now
  or later: "I would like it to be fixed now")". That is audit-process text in the one doc written for end users.
- **UART_C_PORT_CHANGELOG.md** (+163): a sanctioned temporary log for the C port. It now carries a 35-row "Constants
  the check reads" table that `tests_scripts/test_uart_changelog.py` (263 lines) ties to the module. History-form
  entries ~16.
- **THIRD_PARTY_LICENSES.md** (+153): knowledge (Microdot 2.7.0, its stubs, freezefs by commit). History 6, Q&A 5.
- **HEAP_FRAGMENTATION_MEASUREMENTS.md** (+30): knowledge. It is method only; the results are archived at `12640c2`.
- **legacy/README.md** (new, 53 lines): knowledge (index of the reference tree), with 4 lines of Q&A provenance.
- **PROJECT_AUDIT_PLAN.md**: audit-process by kind, all +1,019 lines; 217 -> 512 KB during execution.
- **Deleted, a real consolidation:** HARDWARE_TEST_HANDOVER.md, REAL_HARDWARE_TEST_QUEUE.md (into BACKLOG's
  "Real-hardware work still owed") and dev_legacy/README.md (into tests_hardware/README.md's "The dev bench",
  legacy/README.md and SPEC B.13).

## 3. Cross-doc observations

- **Duplication is small as copied text and recurring as restatement.**
  - CLAUDE.md L380 (the dead-man's switch for destructive bench-network tests) and SPEC B.13 L2113 "**Standing
    rule** (owner, 2026-09-26): any destructive test of the bench host's own network/access config…".
  - CLAUDE.md L323 (test wear) and tests_hardware/README L1971 "Standing design (owner, 2026-09-16…): every write to a
    limited-endurance store that a test owns runs only behind a flag".
  - SPEC C.2 L3048 and G.2 L7715 define `DeviceSession` twice.
  - SPEC A.4 L307 and C.7 L3571: "Where no chip is declared, every module runs RAM-only", with the chunk-unreadable
    semantics written in both places.
  - SPEC A L686 and L L10606: the hardcoded 8000 ms watchdog, with the same owner quote.
  - The UART Class A/B rule stands three times: CLAUDE.md L134, UART_C_PORT_CHANGELOG.md's intro and SPEC J.
  - CLAUDE.md's tooling section restates B.15/E.5.2 (the three Unix-port builds, the mypy passes) and grows with them.
- **Docs became checked data.** Test files that read a doc as data went from 0 to 17. The pinned tables are:
  - I.2 allocation catalog: `test_memory_catalog.py`
  - C.8 lock table: `test_lock_order.py`, 367 lines
  - C.9 task table: `test_task_inventory.py`
  - F.3 timing rows: `test_timing_budget.py`
  - A.11 threat model: `test_threat_model_statement.py`
  - L.3 key table: `test_toml_schema_contract.py`
  - E.6.6 containment rows: `test_level_containment.py`
  - Part N: `test_tunables_register.py`, 371 lines
  - the UART constants: `test_uart_changelog.py`
  - every doc: `test_citations.py` (392 lines) and `test_decision_vocabulary.py`

  L.3 and A.11 are genuine contract checks. The tables are also where most of the code restatement lives, so code and
  doc now have to move together.
- **The decision-record retrofit is unfinished machinery.** `tests_scripts/_decision_vocab_allowlist.txt` holds 393
  allow-listed actorless sentences (SPEC 63, tests 23 + 14 + 14 + 13 …, CLAUDE 13) and `_citation_allowlist.txt` holds
  89. Both "only shrink".

## 4. Repo

### audit/: 14,052 tracked files, 126.6 MB (168 MB on disk), ~53 MB packed over the range (11,815 blob versions)

| kind | files | size | content |
|---|---|---|---|
| evidence logs (`artefacts/evidence/U*_close/`, `archive/`) | 13,142 | 84.9 MB | 8,724 .log (47 MB), 728 .gz (18 MB), 2,323 .txt (10 MB), 512 .md, 301 .out, 264 .json. Per unit close, largest U30 17 MB, U23 12, U18 11.6, U31 9.9, U19 9. Plus 473 copied lane scripts and patches (288 .py, 137 .sh) |
| records | 389 | 39.4 MB | **Planning:** PLANNING_SURVEY 2,497 lines; HARVEST and harvest/ 3.8 MB; hreq/ 1.4; refined/ 0.7; pass2-4/ 2.0; dprov/ and DECISION_PROVENANCE (263 decisions); do_not_reopen (339 lines); CONSOLIDATION and consolidation/ 5.9 MB, M_SPEC.md alone 7,309 lines. **Execution:** order/ 7.8 MB (graph.json 4.4, work_order.json 3.2); actions/ 7.1 MB (53 unit/action records + 47 verify); REGISTER 897 lines; b3/ 2.7 MB; review/ 0.7 MB; sweeps/scan_runs 54 records; sweeps JSON 6.2 MB (ac3_site_trace.json 5.1 MB); trace/UART_PART_J.md |
| scripts | 47 | 0.5 MB | sweeps/ 40 .py (6,864 lines) and 2 .sh, b3/ 3 .py, review/build_page.py, sec_history_scan.py (654 lines) |
| refs | 1 | 0.7 MB | Stull 2011 (wet-bulb paper) |

Nothing outside audit/ depends on it. Only `tests_scripts/_repo_scan.py`, `test_import_graph.py` and
`test_legacy_paths.py` name it, and only to exclude it. README.md describes it. Every file declares itself temporary,
"deleted with audit/ at phase D". **Nothing in it needs to stay in the tree.** Before the deletion:

1. Move `audit/refs/stull2011_jamc-d-11-0143.1.pdf` into the datasheets submodule. It is the source of
   `src/math_helpers.py`'s wet-bulb domain, cited by SPEC (L4768, L7828, L11809) and tests; the submodule is not
   checked out here, so I could not see whether it is already there.
2. Carry REGISTER.md's open findings, and any "measurement owed" that matters, into BACKLOG.
3. Check that each of do_not_reopen.md's decisions still stands at its cited doc site.
4. PLANNING_SURVEY.md is kept "because the owner asked for the overview to survive for later discussion" (plan
   3.1). Deleting it is the owner's call.

The evidence needs no migration: git history keeps it, ~53 MB packed. Deleting it frees the checkout, not the clone,
unless the history is rewritten, which is an owner decision.

Stale inside audit/: REGISTER.md's header still reads "current phase | B1 (unit U1)".

### Other clutter

- **Tracked, generated:** `tests_hardware/twin_record.json`, 1,466 lines, 122 dated entries (55 "exception", 67
  "pass"). `scripts/record_twin_instrument_runs.py` writes it and `tests_scripts/test_twin_record.py` pins it, so
  every change to a device script, the runner or `src/` forces a re-record (U26, `0c0ad52c`). It is logged output
  committed as source.
- **Tracked, temporary and audit-tied:** PROJECT_AUDIT_PLAN.md (512 KB); the two allow-lists above;
  UART_C_PORT_CHANGELOG.md with `test_uart_changelog.py` (kept until the post-audit C reconciliation).
- **Untracked, local only, not repo clutter:** `digital_twin_ci_logs/` (5.3 MB, gitignored), `build/` (47 MB with the
  evidence archive), `frozen_modules/`, caches. In this worktree `node_modules` is a symlink and shows as untracked
  (`?? node_modules`), because `.gitignore`'s `node_modules/` matches a directory only. This only happens in
  symlinked worktrees.
- **Stale text:** the README "Further reading" lines above. BACKLOG's chroot list still runs from "The legs were last
  satisfied 2026-09-12".
- **Pre-existing history the doc pass did not prune:**
  - tests_hardware/README.md "Third pass" … "Tenth pass", 603 lines
  - README "Further reading" merge history, ~20 lines
  - CLAUDE.md's `improved-quality/` bullets, ~20 lines

## 5. Runaway areas (docs and repo)

1. **The Part N register.** It went from 0 to 1,442 lines and 562 KB: 36 % of SPEC's bytes, 47 % of all doc growth.
   1,127 of its 1,284 rows are test/CI/runner values, and 951 of those are "estimated — measurement owed".
   `test_tunables_register.py` needs every Sites cell to list exactly its files and tag counts, so every test edit
   reopens the register. The chain runs U8 (`01e8e3eb`) -> U8C (`a47a1e69`, +510 SPEC lines) -> U8C2 (`95912579`)
   -> every later unit -> U35 `937ff3bc` ("Run 11's register rows carry the calibrated values…").
2. **Docs as checked mirrors of code.** 17 doc-reading tests pin doc tables against code: I.2 grew 3 -> 20 KB, C.8
   14 -> 25, F.3 0 -> 19, C.9, E.6.6. Each table restates code, each check pins the restatement, and SPEC's
   code-restatement share (~930 lines) lives mostly there.
3. **The provenance retrofit.** The "Decision records" rule (owner, 2026-09-26; U0 `195f3ed3`) took SPEC markers
   from 35 to 1,788 and CLAUDE's from 11 to 91, with 139 inline Q&A quotes in SPEC. It is checked by two tests over
   393 + 89 allow-listed sentences that are still pending, and it moved owner Q&A into the end-user
   DEVICE_REFERENCE.md.
4. **BACKLOG's chroot running list.** It went from 99 to 546 lines (49 KB): one dated entry appended per tooling
   change, history by form, and it is the largest single growth in BACKLOG.
5. **CLAUDE.md rules turned essays.** The UART rule is 55 lines, memory safety 83, test wear 45, the comment cap 45.
   Each carries implementation detail and verbatim owner quotes that SPEC also holds.
6. **audit/ evidence, committed per unit close.** 13,142 log files (85 MB) grew with every close (U30 alone 17 MB).
   Generated planning graphs add 7.8 MB of JSON, and the ac3 site trace 5.1 MB of JSON. ~53 MB stays in the packed
   history.
7. **PROJECT_AUDIT_PLAN.md.** It grew from 217 to 512 KB during execution, touched by 217 commits.
8. **Harness docs grew with the harness.** SPEC E +496 lines, F.7 new (20 KB), B.14 25 -> 51 KB, B.10 8 -> 23 KB,
   digital_twin/README +327 net, tests_hardware/README +676 net. Outside the register, the machinery's own
   documentation is about half of all doc growth.
