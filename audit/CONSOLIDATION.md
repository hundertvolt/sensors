# Consolidation — owner requirements OR1-OR53 as one picture

Audit working file (temporary, deleted with `audit/`, OR11.a). Pass 1 (2026-09-26) read the owner
requirements (PROJECT_AUDIT_PLAN.md 3.2) against each other, the plan and CLAUDE.md, learning as it
went. Pass 2 (2026-09-26) repeats that read with everything known from the start and works the result
into the plan's sections 1, 2 and 4. Passes 3+ run the question-raising scans (OR52.a (5)).

## 1. The big picture

**Goal** (OR1, OR5): the complete, working prototype becomes a true release — consolidated,
harmonized, one material (OR24), with no leftovers.

**Concept** (OR44, owner's words): "a device which can run indefinitely long without any user
interaction once configured, handles all issues inside, and although barely reachable has multiple
fallback layers, has premium quality code, has all its main cases all the way through rare corner
cases tested, and runs efficiently and compact on a low end hardware device".

**Pillars** — OR44.a's P1-P6 plus four found in pass 1 (P7-P10). Every requirement is a sample of at
least one; none is left unexplained.

| # | Pillar | Samples |
|---|---|---|
| P1 | Unattended indefinitely: nothing drifts, saturates or needs a person | OR31, OR35, OR42, OR47, OR52.a (2) |
| P2 | Handles everything inside, at the right layer | OR18, OR26, OR22.a (3), OR31.a |
| P3 | Layered fallbacks: degrade, retry, re-setup, restart, reboot, watchdog; hardware faults escalate | OR18.a, OR22.a, OR31.a, OR47.a (2) |
| P4 | Premium code, one material, nothing in the product for tests | OR24, OR28, OR36, OR46, OR51, OR53 |
| P5 | Proven main to corner cases, by tests that bite at every layer and tier | OR16, OR19, OR21, OR22, OR23, OR25, OR41, OR45, OR49 |
| P6 | Efficient and compact on low-end hardware | OR39, OR40, OR46.a (3) |
| P7 | Evidence survives and stays readable | OR35, OR38.a (2), OR28.a (1), CLAUDE.md FRAM rule |
| P8 | One source of truth, generated not copied | OR10.a, OR30, OR43.a (3), OR45.a (1), OR51.a (4) |
| P9 | Operating and testing never wear or damage anything | OR37, OR42, OR49.a (2), CLAUDE.md wear rule |
| P10 | Extensible without edits elsewhere | OR10, OR43.a (device set derived), OR44.a checklist, OR52.a (2) |

Process requirements (OR2-OR9, OR11-OR14, OR33, OR34, OR51.a (3)) serve the goal itself: an audit
that runs uninterrupted, decides conservatively, proves instead of assuming, and leaves nothing open.

## 2. Phases

| Phase | Content | Driven by |
|---|---|---|
| A. Consolidation (now) | Passes 1-2: requirements (done). Passes 3+: question-raising scans over harvest, seeds, code and history — rule and decision drift, legacy losses, defect candidates, necessity verdicts, open items. Owner questions in the owner's format. Exit: every foreseeable question answered | OR2.a/b, OR3, OR5, OR13.a, OR14.a, OR33.a, OR48.a, OR52.a (5) |
| B0. Baseline | Toolchain, every tier once, both GC stages; counts, timings, peak memory, coverage recorded | plan 4.6, OR39.a (3) |
| B1. Foundations | Global changes that later work builds on, in this order: legacy move to `legacy/` (moves the paths everything cites); error-number catalog; central log-repeat rule; shared compare-before-write primitive (SCD30 onto it); config objects and `max-args`; one-source website definitions; the L0-L4 tier ladder and runner summary block; `@tunable` scheme | OR32.a, OR28.a, OR35.b, OR42.c, OR46.b, OR43.a (3), OR45.a, OR15.a (2), OR21.a (3), OR30.a |
| B2. File-by-file | Per area, in dependency order (plan 4.1): four levels, every lens, the OR51 gate, dead code, staleness incl. non-code files, fixes for the losses and defects consolidation settled | OR46.a, OR51, OR18, OR26, OR31, OR36, OR47, OR50, OR53 |
| B3. Test campaign | Every test reviewed; one fault-planting campaign per module; intent map; combination and interaction matrices; generated code and build chain; load limits; races; hygiene; speed and footprint | OR16, OR19, OR21, OR22, OR23, OR25, OR37-OR41, OR49 |
| B4. Docs | History trace applied, content rules, principles Part and the one ordered checklist, skill proven on two baselines, README | OR10.b, OR13, OR14, OR15.a (1), OR27, OR44.a (3), OR51.a (4) |
| B5. Close of execution | Cleanup; re-verification passes until one ends all green; hardware queue, knowledge base, twin fidelity; final report with the load-test entries; owner review of decisions taken on the owner's behalf | OR5, OR8.a, OR9.a, OR11, OR17.a, OR29.a, OR49.a (3), OR2.c |
| C. Hardware rounds | Go-ahead per session. FRAM logs read first; lower levels run first; two-image GC proof; bench boot log and trigger timestamps; twin corrected until it agrees; bench Pi package check | OR5.a, OR17, OR28.a (1), OR40.a (3), OR45.a (2), OR47.a, OR50.a (3) |
| D. Close | Plan and `audit/` deleted after the last hardware round; one merge into the frozen `main` | OR11.a, OR52.a (4) |

Sync points after every unit in B (OR6.a): commit, push, full local suite at both GC stages, CI green
(event hooks only), register and PR status note, continue. No owner stop-points in B.

## 3. Harmonizations

1. **"Goes to the owner" during execution** (OR36.a, OR43.a, OR48.a, OR50.a) means parked and logged
   for review under OR2.c, never a stop (OR2).
2. **Hardware queue**: "`REAL_HARDWARE_TEST_QUEUE.md`" in OR8.a/OR17.a/OR29.a means BACKLOG's
   "Real-hardware work still owed"; OR11.a's "close of the hardware session" means the last round.
3. **BACKLOG at the end** (OR5.a, OR27.a, plan goal 4): owed hardware, C-port items and
   owner-deferred future goals with their reason. Nothing else.
4. **One ordered checklist** (OR10.a, OR44.a (3), OR51.a (4)): Part K is extended into the single
   ordered path for any addition (module = general case, sensor = extension); Part D's checklist and
   the OR51 gate fold into it; Parts C and G stay reference specs its steps cite. The OR10.b baseline
   runs are OR44.a's end-to-end proof — one exercise.
5. **Permanent checks are not control arms** (OR21.a): tests of a property (OR15.a, OR28.a, OR30.a,
   OR31.a, OR40.a, OR45.a, OR52.a (2)) are allowed; only deliberately failing sensitivity arms are not.
6. **Fix path**: OR12.a/OR2.c replace PQ3's sign-off; consistency changes are made directly (OR24.a).
7. **No owner stop-points** in execution (OR2, PQ8); the owner may look in at sync points.
8. **One branch, one PR** (#107), one merge commit into `main` (OR11.a, PQ2); autonomous commits.
9. **Parallel agents** cover the whole audit ("later work" in the 2026-09-25 permission, OR1.a).
10. **Address parameters** (OR36.a): BMP3XX's is hardware (SDO selects 0x76/0x77, set per TOML) and
    stays; ISL29125's (hard-wired 0x44) goes, with its wrong "as BMP3XX's" comment.
11. **Concurrency on hardware vs wear** (OR41.a, OR49.a): config-write concurrency on the board uses
    unchanged and rejected writes; a persisting write stays behind `persistence_write`.
12. **Lazy setup** (OR47.a): FRAM chunk setup moves into the boot batch; a sensor's re-init retry in
    its task stays (P3); where SCD30's reader shape differs from its peers, OR24 decides.
13. **No immediate SEV1 escalation**: nothing touches the board during execution.
14. **Severity** stays only as the register's ordering.
15. **Board-free collection** (`HW.T14`): the sandbox never has a board, so collection-only runs of
    `tests_hardware/` are safe; the owner's confirmation is part of the go-ahead record.
16. **Resumed sessions**: the owner's message that starts or continues a session is that session's
    confirmation for software work; the real-hardware go-ahead never carries over (CLAUDE.md).
17. **Convergence cap** (plan 4.4): after four passes the arbiter decides under OR2.c and logs it.
18. **Fault planting** appears in OR16.a (4), OR19.a (3), OR21.a (1), OR31.a (5): one campaign per
    module in throwaway worktrees, one record of which test catches which fault.
19. **Working files** (OR25.a map, OR41.a matrices, OR45.a matrix, OR46.a ledger, OR44.a concept) live
    in `audit/` and go at close; what outlives them is tests and SPECIFICATION.md text.
20. **Tier names**: one ladder L0 host, L1 unit, L2 twin, L3 flash, L4 bench (OR45.a), used everywhere
    instead of "tiers"/"backends"; E.6's `manual` is an execution mode of L3/L4, not a level.
21. **Question-raising scans move forward** (OR52.a (5)): OR48.a (3)'s "along with the audit" and
    OR13.a's execution-time drift cases become consolidation work; execution fixes what they settled.
22. **Legacy REST paths go** (OR58.a): the new API is the only reference; no legacy path is restored,
    key names are harmonized to one scheme before the release. Answers `PAR.T05`.
23. **No migration** (OR52.a (1)): `PAR.T06`/`T07` become the reflash runbook; `PAR.T08` (files left
    on a legacy unit's filesystem) stays a code question — can any of them shadow the frozen modules.

## 4. Requirement → phase → permanent home

| OR | Phase | Permanent home after close |
|---|---|---|
| OR1, OR34, OR44 | all | SPECIFICATION.md "Design principles" Part (new, front) |
| OR2, OR3, OR4, OR6, OR7, OR9, OR12, OR13 | A, B | CLAUDE.md working agreements (decision rule, sources, flakes, agents, re-verification, regression vs defect, drift) |
| OR5, OR11, OR33 | A, B5, D | BACKLOG content rule (harmonization 3); nothing else stays |
| OR8, OR17, OR29 | B5, C | BACKLOG real-hardware section; Part F; `tests_hardware/README.md`; `digital_twin/README.md` fidelity table |
| OR10, OR44.a (3), OR51 | B4 | Part K as the one ordered checklist; `.claude/skills/integrate-module/` |
| OR14, OR48 | A | none (findings only) |
| OR15 | B1, B4 | README.md; runner summary block; `tests_scripts` help-vs-README check |
| OR16, OR19, OR21, OR25 | B3 | Part E test standard; tests |
| OR18, OR26, OR31 | B2 | Parts A.7, C, D.2, F.2 (reworded MemoryError rule) |
| OR20, OR36 | B2, B3 | Part E.9; principles P4 |
| OR22, OR23 | B3 | tests; Part L error contract |
| OR24, OR46 | B1, B2 | Parts D.10, G; `pyproject.toml` limits; CLAUDE.md scan rule reworded |
| OR27 | B4 | CLAUDE.md docs rule |
| OR28, OR35 | B1 | Part C.7.1; `print_log.py`; catalog test |
| OR30 | B1-B3 | new SPECIFICATION.md tunables section; `@tunable` tags; test |
| OR32 | B1 | `legacy/README.md`; CLAUDE.md paths |
| OR37, OR38, OR39, OR40, OR41, OR49 | B3, C | CLAUDE.md wear and memory rules; Part E; tests |
| OR42 | B1, B2 | Part G primitive; SPECIFICATION.md SCD30 text |
| OR43 | B1, B2 | Part H placement rule |
| OR45 | B1, B3 | Part E.6 (one ladder) |
| OR47 | B2, C | Parts A.7, C.9.1 |
| OR50 | B2, B5 | none (cleanup) |
| OR52 | all | config-key stability rule (Part L/C); threat model statement (SPECIFICATION.md) |
| OR53 | B2 | Part L.6.5 |

## 5. Interpretations overtaken by later rows (the later row wins)

- OR8.a, OR17.a (4), OR29.a (2): the queue file → BACKLOG's real-hardware section (fold `03f8bcf`).
- OR11.a (1): queue and handover already deleted; plan and `audit/` go after the last round (OR17).
- OR35.a (5) → OR35.b: no distinction by origin.
- OR47.a (3): the SCD30 tick stays 500 ms (rewritten in the row itself).
- OR48.a (3): the scan runs in consolidation (OR52.a (5)).
- OR51.a (4): "Part D" → the one ordered checklist absorbing Part D (harmonization 4).
- OR36 example "like BMP3XX's" → harmonization 10.
- PQ1-PQ10 recommendations → answers (plan section 3).
- OR24.a (2) "legacy REST paths that external clients may use stay" → OR58.a: none stays.
- OR39.a (1) "don't measure in the next line" → OR55.a: `gc.collect()` is complete on return.
- Plan 4.1's waves, stop-points and delta passes → phases (plan 4.1, pass 2).

## 6. Research results

- MicroPython `v1.29.0` is still the latest release (`v1.30.0-preview` only): pin unchanged.
- Microdot `v2.7.0` adds a `QUERY` method, a `Vary` header for sessions/CSRF (unused here) and
  f-strings; `ext/microdot.py` stays on `v2.6.2`.
- Blocked hosts: `docs.micropython.org`, `microdot.readthedocs.io`, `sensirion.com`,
  `raspberrypi.com`, `datasheets.raspberrypi.com`, `adafruit.com`; both projects' docs are read from
  their GitHub `docs/` sources. The Sensirion VOC notes are in `datasheets/sgp40/` (OR53).
- Several datasheet PDFs carry a permissions encryption with an empty password; `pypdf` reads them
  with `cryptography` installed. MB85RS64V: tpu ≥ 0.6 ms at 3.3 V (p.18).
- RP2040 Table 279: `buildgen/pico_gpio.py` is stricter than silicon (`GEN.T07`, OR53).
- `ConfigManager.setup()` replaces a renamed or unknown key by its default and rewrites the file
  (`config_manager.py:446-462`) — the reason for OR52.a (2)'s golden stored-config test.
- `digital_twin/unix_port_gc_unwedge.py` uses `gc.collect()` as a tool; retired per OR52.a (6).

## 7. Harvest pass 1 — requirements inside the harvest (method)

Input: the whole harvest (6,500 items, `audit/harvest/*.md`, `HARVEST.md`) against OR1-OR53, the
pillars and harmonizations above. Output: `audit/HARVEST_REQUIREMENTS.md` (working file, OR11.a).

1. **Extract** (ten read-only agents, PQ9): nine over the catalogs in groups (HW; TEST; SENS+ALGO+BUS+
   LED; PLAT+MEM+PERF; CORE+STOR+XCUT+SEC+UNSORTED; UART+NET+REST; TWIN+WEB; GEN+TOOL+SCR+CI;
   DOC+PAR+LIC), one over the code for de-facto conventions no catalog item states (naming, idioms,
   structure). Each normative statement, explicit or implied, becomes one candidate requirement.
2. **Account**: every item ID lands in a candidate or in a named no-requirement bucket (descriptive,
   defect candidate, open item, suppression inventory, duplicate); a script checks that none is missed.
3. **Verify** each candidate: provenance (owner words, owner-confirmed proposal, session agent, external
   fact, code convention only — from the text's attribution, `git log -S`, commit and PR text); truth
   at HEAD against code, datasheets, MicroPython `v1.29.0` source and upstream docs; drift between the
   places that state it.
4. **Phrase** each verified candidate in the OR style: one plain normative statement, its evidence.
5. **Place**: pillar, and its relation to OR1-OR53 (restates, refines, extends, new, conflicts).
6. **Harmonize** across groups (merge duplicates, resolve contradictions by provenance and evidence),
   research what stays unclear, and list the rest as owner questions in the owner's format.

## 8. Next: passes 3+

The question-raising scans (harmonization 21), read-only, parallel agents allowed (PQ9): rule and
decision drift over the doc history (OR13.a, OR14.a), legacy losses (OR48.a), defect candidates among
the seeds and harvest (OR12.a), necessity verdicts (OR33.a, Appendix B), open and deferred items
(OR5, OR51.a (2)). Output: owner questions in the owner's format; settled items feed B1-B2.
