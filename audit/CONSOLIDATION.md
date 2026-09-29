# Consolidation — the audit's big picture (allover pass 2)

Audit working file (temporary, deleted with `audit/`, OR11.a). One picture of everything consolidation
knows: the owner requirements OR1-OR96 (PROJECT_AUDIT_PLAN.md 3.2), the requirements inside the harvest,
and the decision-provenance answers. History: requirement passes 1-2 and harvest pass 1 (2026-09-26,
section 8); allover pass 2 (2026-09-27) re-read all of it with everything known from the start and
produced one register (section 7). Passes 3+ run the question-raising scans (section 9).

## 1. The big picture

**Goal** (OR1, OR5): the complete, working prototype becomes a true release — consolidated,
harmonized, one material (OR24), with no leftovers; the release is a defined point (LEAD/R15).

**Concept** (OR44, owner's words): "a device which can run indefinitely long without any user
interaction once configured, handles all issues inside, and although barely reachable has multiple
fallback layers, has premium quality code, has all its main cases all the way through rare corner
cases tested, and runs efficiently and compact on a low end hardware device".

**Pillars.** Every live requirement carries one (count in brackets, from `audit/pass2/INDEX.md`); none is
unexplained. P1-P6 are OR44.a's, P7-P10 came from requirement pass 1, P11-P12 from harvest pass 1;
allover pass 2 found no further pillar and widened P11 by the provenance rules.

| # | Pillar | Samples |
|---|---|---|
| P1 (20) | Unattended indefinitely: nothing drifts, saturates or needs a person | OR31, OR35, OR42, OR47; driven-time and RTC-step proofs (LEAD/R04-R05); the website left open for days (LEAD/R09); the overnight notification window (OR69.a (6)) |
| P2 (66) | Handles everything inside, at the right layer | OR18, OR26, OR22.a (3); one event, one entry (OR56.a (1)); an unreadable config never overwritten (G5/R34); the C-stack budget (LEAD/R06) |
| P3 (32) | Layered fallbacks: degrade, retry, re-setup, restart, reboot, watchdog; hardware faults escalate | OR18.a, OR31.a, OR47.a; power-cycle backstop (OR70.a (2)); operator actions listed (LEAD/R14) |
| P4 (85) | Premium code, one material, nothing in the product for tests | OR24, OR36, OR46, OR51, OR53; config objects and `max-args = 8` (OR46.b); conventions machine-checked (LEAD/R17) |
| P5 (94) | Proven main to corner cases, by tests that bite at every layer and level | OR16, OR19, OR21, OR22, OR23, OR25, OR41, OR45, OR49; twin first for every instrument (LEAD/R01) |
| P6 (36) | Efficient and compact on low-end hardware | OR39, OR40, OR46.a (3); `mem_free` in `/status` (OR71.a (7)); image-size report (LEAD/R07) |
| P7 (34) | Evidence survives and stays readable | OR35, OR28.a (1), CLAUDE.md FRAM rule; `reset_reason` in `mem_backup()` (OR60.a) |
| P8 (35) | One source of truth, generated not copied | OR10.a, OR30, OR43.a (3), OR45.a (1), OR51.a (4); device set derived (OR54.a (1)) |
| P9 (33) | Operating and testing never wear or damage anything | OR37, OR42, OR49.a (2); no limited-endurance write without a user or API action (OR70.a (3), OR71.a (2)); standard board state (LEAD/R02) |
| P10 (13) | Extensible without edits elsewhere | OR10, OR43.a, OR44.a checklist; a device's TOML decides its sensors (OR71.a (4)) |
| P11 (21) | Grounded and traceable: every behaviour-bearing claim traces to a primary source at the pinned version, corrected in place when the source disagrees; every decision names its actor and date, an owner decision quotes the owner | OR2, OR4, OR55, OR68.a (4), CLAUDE.md standing practices; reproducible image (LEAD/R13) |
| P12 (25) | Contracts at boundaries: one normative text, a named owner of change and a conformance check per interface the project cannot change in one commit | OR24.a (2), OR52.a (2), OR56 (3), OR58, Part J; REST reference and golden fixture (LEAD/R08); TOML schema (LEAD/R11) |

Process requirements (23; OR2-OR9, OR11-OR14, OR33, OR34, OR51.a (3), OR68.a) serve the goal itself: an
audit that runs uninterrupted, decides conservatively, proves instead of assuming, and leaves nothing open.

## 2. Phases

| Phase | Content | Driven by |
|---|---|---|
| A. Consolidation (now) | Done: requirement passes 1-2, harvest pass 1, decision-provenance sweep, allover pass 2 (the register). Next, passes 3+: the question-raising scans (section 9). Owner questions in the owner's format. Exit: every foreseeable question answered | OR2.a/b, OR3, OR5, OR13.a, OR14.a, OR33.a, OR48.a, OR52.a (5), OR68.a (3) |
| B0. Baseline | Toolchain, every level once, both GC stages; counts, timings, peak memory, coverage, image sizes recorded; the five prevention rules and the reviewed-decision tag form written into CLAUDE.md with their `tests_scripts` check (allow-list for text the audit has yet to rewrite) | plan 4.6, OR39.a (3), OR68.a (4), LEAD/R07, LEAD/R16 |
| B1. Foundations | Global changes that later work builds on, in this order: legacy move to `legacy/`; error-number catalog; central log-repeat rule; shared compare-before-write primitive (SCD30 onto it); config objects and `max-args`; one-source website definitions; the L0-L4 tier ladder and runner summary block; `@tunable` scheme | OR32.a, OR28.a, OR35.b, OR42.c, OR46.b, OR43.a (3), OR45.a, OR15.a (2), OR21.a (3), OR30.a |
| B2. File-by-file | Per area, in dependency order (plan 4.1): four levels, every lens, the OR51 gate, dead code, staleness incl. non-code files; the register's work lines per unit (`audit/pass2/INDEX.md`) | OR46.a, OR51, OR18, OR26, OR31, OR36, OR47, OR50, OR53 |
| B3. Test campaign | Every test reviewed; one fault-planting campaign per module; intent map; combination and interaction matrices; generated code and build chain; load limits; races; hygiene; speed and footprint | OR16, OR19, OR21, OR22, OR23, OR25, OR37-OR41, OR49 |
| B4. Docs | History trace applied, content rules, provenance corrections (actor and date on every decision), principles Part and the one ordered checklist, skill proven on two baselines, README | OR10.b, OR13, OR14, OR15.a (1), OR27, OR44.a (3), OR51.a (4), OR68.a |
| B5. Close of execution | Cleanup; re-verification passes until one ends all green; hardware queue, knowledge base, twin fidelity; release note; final report with the load-test entries; owner review of decisions taken on the owner's behalf | OR5, OR8.a, OR9.a, OR11, OR17.a, OR29.a, OR49.a (3), OR2.c, LEAD/R15 |
| C. Hardware rounds | Go-ahead per session. FRAM logs read and saved first; lower levels run first; two-image GC proof; bench boot log and trigger timestamps; `reset_reason` codes proven; twin corrected until it agrees; standard board state at start and end; bench Pi package check | OR5.a, OR17, OR28.a (1), OR40.a (3), OR45.a (2), OR47.a, OR50.a (3), OR60.a (4), LEAD/R02 |
| D. Close | Plan and `audit/` deleted after the last hardware round; one merge into the frozen `main`, tagged as the release | OR11.a, OR52.a (4), LEAD/R15 |

Sync points after every unit in B (OR6.a): commit, push, full local suite at both GC stages, CI green
(event hooks only), register and PR status note, continue. No owner stop-points in B.

## 3. Harmonizations (one list; numbers are stable and cited elsewhere)

1. **"Goes to the owner" during execution** (OR36.a, OR43.a, OR48.a, OR50.a) means parked and logged
   for review under OR2.c, never a stop (OR2).
2. **Hardware queue**: "`REAL_HARDWARE_TEST_QUEUE.md`" in OR8.a/OR17.a/OR29.a means BACKLOG's
   "Real-hardware work still owed"; OR11.a's "close of the hardware session" means the last round.
3. **BACKLOG at the end** (OR5.a, OR27.a, plan goal 4): owed hardware, C-port items, owner-deferred
   future goals with their reason, and the owner-question list (OR68.a (4)). Nothing else.
4. **One ordered checklist** (OR10.a, OR44.a (3), OR51.a (4)): Part K is extended into the single
   ordered path for any addition (module = general case, sensor = extension); Part D's checklist and
   the OR51 gate fold into it; Parts C and G stay reference specs its steps cite. The OR10.b baseline
   runs are OR44.a's end-to-end proof — one exercise.
5. **Permanent checks are not control arms** (OR21.a): tests of a property (OR15.a, OR28.a, OR30.a,
   OR31.a, OR40.a, OR45.a, OR52.a (2), OR68.a (4)) are allowed; only deliberately failing sensitivity
   arms are not.
6. **Fix path**: OR12.a/OR2.c replace PQ3's sign-off; consistency changes are made directly (OR24.a).
7. **No owner stop-points** in execution (OR2, PQ8); the owner may look in at sync points.
8. **One branch, one PR** (#107), one merge commit into `main` (OR11.a, PQ2); autonomous commits.
9. **Parallel agents** cover the whole audit ("later work" in the 2026-09-25 permission, OR1.a).
10. **Address parameters** (OR36.a): BMP3XX's is hardware (SDO selects 0x76/0x77, set per TOML) and
    stays; ISL29125's (hard-wired 0x44) goes, with its wrong "as BMP3XX's" comment.
11. **Concurrency on hardware vs wear** (OR41.a, OR49.a): config-write concurrency on the board uses
    unchanged and rejected writes; a persisting write stays behind `persistence_write`.
12. **Lazy setup** (OR47.a): every FRAM logger's store setup moves into the boot batch (G5/R06); a
    sensor's re-init retry in its task stays (P3); where SCD30's reader shape differs, OR24 decides.
13. **No immediate SEV1 escalation**: nothing touches the board during execution.
14. **Severity** stays only as the register's ordering.
15. **Board-free collection** (`HW.T14`): the sandbox never has a board, so collection-only runs of
    `tests_hardware/` are safe; the owner's confirmation is part of the go-ahead record.
16. **Resumed sessions**: the owner's message that starts or continues a session is that session's
    confirmation for software work; the real-hardware go-ahead never carries over (CLAUDE.md).
17. **Convergence cap** (plan 4.4): after four passes the arbiter decides under OR2.c and logs it.
18. **Fault planting** appears in OR16.a (4), OR19.a (3), OR21.a (1), OR31.a (5): one campaign per
    module in throwaway worktrees, one record of which test catches which fault.
19. **Working files** (OR25.a map, OR41.a matrices, OR45.a matrix, OR46.a ledger, OR44.a concept, the
    pass-2 register) live in `audit/` and go at close; what outlives them is tests and permanent text.
20. **Tier names**: one ladder L0 host, L1 unit, L2 twin, L3 flash, L4 bench (OR45.a), used everywhere
    instead of "tiers"/"backends"; E.6's `manual` is an execution mode of L3/L4, not a level.
21. **Question-raising scans move forward** (OR52.a (5)): OR48.a (3)'s "along with the audit" and
    OR13.a's execution-time drift cases become consolidation work; execution fixes what they settled.
22. **Legacy REST paths go** (OR58.a): the new API is the only reference; no legacy path is restored.
23. **No migration** (OR52.a (1)): `PAR.T06`/`T07` become the reflash runbook; a filesystem `.py`/`.mpy`
    shadows a frozen module (`py/runtime.c:147-150`), so the runbook erases the filesystem and the boot
    entry puts `.frozen` first (OR59.a).
24. **Rank of a rule**: owner words > owner-confirmed > external fact > agent text > code convention;
    the most recent owner decision wins without asking (OR68.a (2)). A fact beats any text about it: a
    claim the primary source contradicts is corrected in place whoever wrote it; an owner rule with a
    wrong stated reason keeps its rule and gets its reason corrected (OR13.a).
25. **Agent rules** are adopted as project rules where they hold and fit the owner rows, labelled
    "(agent, date)" (OR71.a (0); list-L items with a verified owner source and no drift keep the owner label, OR82); they yield where an owner row says otherwise; a behaviour divergence
    from legacy that an agent decided alone goes to the owner (OR48.a (2)), unless it is an adaptation
    with no functional loss.
26. **Legacy parity is with intent** (OR57): a legacy bug that defeats legacy's own intent is a legacy
    defect, never a behaviour to keep.
27. **Lost owner decisions are restored**, not re-asked: D.15's 2026-09-13 ruling (class member order,
    comments move with their code), the SCD30/SGP40 delays the owner tested (`144873f`, `5ff8c0b`, G3/R30)
    and every other one pass 2 found.
28. **One event, one persisted entry** (OR56 (1)) makes OR35.b's newest-entry rule sufficient; no
    per-module exception.
29. **Tests take expected values from an independent source** (OR19.a (2)); D.12's "sanity bound"
    applies only where no reference value can be derived.
30. **Unreachable defensive branches** follow OR46.a: removed, except a guard of an overridable
    extension point or of a documented runtime failure (OR26.a), each listed with its reason.
31. **Hand-kept tables** stay only where the owner decided so (`buildspec.py`, the `status`/`errcount`
    catalog), each with an agreement test (LEAD/R11); everything else is derived (OR43.a (3)).
32. **Twin fakes stay independent of unit-tier fakes** (owner-confirmed `b8791e6`); where the two tiers
    expose the same test API they share one convention and a contract test.
33. **The new API is the only reference** (OR58): no legacy path or spelling is kept; keys follow one
    scheme before the release, then OR52.a (2) and LEAD/R08 freeze them.
34. **No trace is not "not decided"** (OR64): a decision without owner words is classified by its
    visible trail and confirmed by the owner, never declared an agent's.
35. **Every decision statement carries its actor and date** (OR68.a (4)): "(owner, date)" with the
    owner's words and question; "(agent, date)" for agent design; "(agent, date; owner-reviewed, date)"
    after an OR2.c review (LEAD/R16). Compaction never changes actor, qualifier or scope; nothing
    permanent cites a temporary plan by section or number.
36. **"Field" means the owner's own units** (OR61.a): every unit is reachable, legacy units run 1.24.1;
    no requirement rests on an unreachable fleet.
37. **Limited-endurance writes need a user or API action** (OR70.a (3)): the flash filesystem and SCD30
    NVM are written only by an accepted PUT that changed a value (or a command that always writes:
    `AmbPres`, `ForceCalRef`, OR42.c) and by one repair per boot of a readable config file (OR71.a (2));
    a missing file creates nothing, an unreadable one is never overwritten; FRAM is outside the rule.
38. **Buses are never stalled** (OR64.a): the SGP40 general-call reset is the one owner-decided reset
    that reaches other devices; nothing stalls, holds or restarts a bus or its controller.
39. **Reset evidence does not need FRAM** (OR60.a): `reset_reason` lives in `mem_backup()` region 0,
    owned by SystemService; FRAM logs stay the per-module evidence where fitted.
40. **`dev` meets every device's bar** (OR72.a (10)) and a device's TOML decides its sensors
    (OR71.a (4)): no per-driver device allow-lists; wozi stays never-flashed (A05).
41. **Load tests prove degradation and recovery** (OR49.a, OR72.a (1)): starvation under a
    hypothetical client (four zero-think readers) is accepted degradation, not a failure (owner,
    2026-09-28, OR83).
42. **Boot order** (OR47.a (1), OR75.a): strict sequencing, completeness and one fixed generated order:
    construction, setup batch, task starts, timer starts, then the first NTP force sync (last, as in
    legacy). Legacy started timers first too, so this is the owner's order, not a restoration.
43. **Adopted gaps** (OR44.a (1)): pillar gaps the groups found are agent-rank requirements (LEAD/R01-
    R17), on the owner-review list.
44. **No variant is hard-coded anywhere** (OR78): every board variant lives solely in its
    `devices/<name>.toml`; outside `devices/` no code, CI, test, tier, twin, website or script names a
    variant — sets are derived, a single device comes from data or an argument; no exceptions.
45. **Real-bench fault injection is attempted** (OR77, OR79): the off-subnet DNS spoofing test and the
    other real-bench injections are tried; one stays a listed exception only if the attempt shows
    unreasonable effort or no case beyond L1-L3.

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
| OR28, OR35, OR56 (1) | B1 | Part C.7.1; `print_log.py`; catalog test |
| OR30 | B1-B3 | new SPECIFICATION.md tunables section; `@tunable` tags; test |
| OR32 | B1 | `legacy/README.md`; CLAUDE.md paths |
| OR37, OR38, OR39, OR40, OR41, OR49, OR55 | B3, C | CLAUDE.md wear and memory rules; Part E; Part I.4; tests |
| OR42, OR70.a (3), OR71.a (2) | B1, B2 | Part G primitive; Part C.7.3; CLAUDE.md flash-write rule; SCD30 text |
| OR43, OR54 | B1, B2 | Part H placement rule; derived device set |
| OR45 | B1, B3 | Part E.6 (one ladder) |
| OR47 | B2, C | Parts A.7, C.9.1 |
| OR50 | B2, B5 | none (cleanup) |
| OR52, OR58 | all | config-key and REST stability rule (Parts A.8, L, C); threat model statement |
| OR53 | B2 | Part L.6.5; `buildgen/pico_gpio.py` |
| OR56 (2)(3), OR57 | B2 | Part C (DNS config value, FRAM layout per build); CLAUDE.md legacy-parity rule |
| OR59, OR61 | B2, C | boot entry (buildgen); reflash runbook; CLAUDE.md platform target (1.24.1) |
| OR60 | B2, C | Part A.7 and the `/status` field table; twin fidelity row |
| OR63 | B2 | none (removal) |
| OR64, OR65, OR66, OR67 | B2 | Part C.8 (general call, owner-decided); Part A.4 (SGP40 compensation) |
| OR68-OR72 | B0, B2, B4 | CLAUDE.md working agreements (prevention rules, workflow); each decision's own home text with "(owner, date)" |
| OR73 | B4 | SPECIFICATION.md scope line |
| OR74, OR76 | B2 | SPEC M.1/M.1.1 (ISL29125 scope fact; calibration-suitability field) and its `@web` tag |
| OR75 | B2, C | Part A.7 (boot order); generated `main()` |
| OR77, OR79 | B3, C | Part E.6 exception list; `tests_hardware/README.md` |
| OR80 | B2, B4 | `datasheets/` submodule; README, CLAUDE.md datasheet rule, SPEC A.6 |
| OR81 | B0-B2 | `pyproject.toml` and both `.ini` files; CLAUDE.md "Code quality tooling" |
| OR78 | B1-B4 | CLAUDE.md hard rule; `tests_scripts` variant-literal check; Part L |
| OR84 | B2 | `SystemService` setup runner; SPEC A.7, I.4(f.1); CLAUDE.md memory rule |
| OR85, OR86 | B2 | `scripts/build_firmware.py`; README build section; `--help` |

## 5. Interpretations overtaken by later rows (the later row wins)

- OR8.a, OR17.a (4), OR29.a (2): the queue file → BACKLOG's real-hardware section (fold `03f8bcf`).
- OR11.a (1): queue and handover already deleted; plan and `audit/` go after the last round (OR17).
- OR35.a (5) → OR35.b: no distinction by origin.
- OR47.a (3): the SCD30 tick stays 500 ms (rewritten in the row itself).
- OR48.a (3): the scan runs in consolidation (OR52.a (5)).
- OR51.a (4): "Part D" → the one ordered checklist absorbing Part D (harmonization 4).
- OR36 example "like BMP3XX's" → harmonization 10.
- PQ1-PQ10 recommendations → answers (plan section 3); PQ10's "legacy REST paths stay" → OR58.a.
- OR24.a (2) "legacy REST paths that external clients may use stay" → OR58.a: none stays.
- OR39.a (1) "don't measure in the next line" → OR55.a: `gc.collect()` is complete on return.
- OR62.a (addressed heater-off replaces the general call) → OR64.a/OR65.a: the general call stays.
- OR71.a (6) (C09: permanent bench skip of the spoofing test accepted) → OR79.a: attempt it.
- HARVEST_REQUIREMENTS 3.3's F18 row (admission fairness) → OR72.a (1): degradation check only.
- `368fa83`'s accepted uncompensated SGP40 fallback → OR66.a/OR67.a.
- Plan 2.3's settled `NTP_Host` 1,024 bound → OR70.a (4): re-decided with the key scheme.
- CLAUDE.md's "dev config quirks are not bugs" → OR72.a (10).
- SPEC M.1.1 item 18's "must not gain one" → OR71.a (4).
- Plan 4.1's waves, stop-points and delta passes → phases (plan 4.1, pass 2).

## 6. Research results

- MicroPython `v1.29.0` is still the latest release (`v1.30.0-preview` only): pin unchanged.
- Microdot `v2.7.0` adds a `QUERY` method, a `Vary` header for sessions/CSRF (unused here) and
  f-strings; `ext/microdot.py` stays on `v2.6.2`.
- Blocked hosts: `docs.micropython.org`, `microdot.readthedocs.io`, `sensirion.com`,
  `raspberrypi.com`, `datasheets.raspberrypi.com`, `adafruit.com`, doi.org and the paper publishers;
  both projects' docs are read from their GitHub `docs/` sources.
- `machine.mem_backup()` at `v1.29.0`: rp2 region 0 = watchdog `scratch[0..3]` (16 B), region 1 =
  `scratch[5..7]` (12 B); survives soft reset, `machine.reset()` and a watchdog timeout, cleared by
  power-on and RUN (OR60.a). Not on 1.24.1.
- The SGP40 general call is one bounded write (`ports/rp2/machine_i2c.c:147`); of the chips on the
  boards only the SGP40 documents a general-call reset (OR64.a).
- The Unix port at `v1.29.0` has no `socket.getsockname()` (`ports/unix/modsocket.c`), so
  MicroPython-side test listeners keep fixed, disjoint port bands; CPython-side tests use port 0 (G8).
- Datasheet licences: the two Raspberry Pi PDFs carry CC BY-ND; Fujitsu, Renesas and Sensirion state
  "All rights reserved"; Bosch, Winbond, Worldsemi and Infineon state no licence — hence OR80's private submodule.
- Stull (2011) checked against the owner-supplied paper; McCamy replaced by a Planck/CIE oracle
  (HARVEST_REQUIREMENTS 3.4).
- `ConfigManager.setup()` replaces a renamed or unknown key by its default and rewrites the file
  (`config_manager.py:446-462`) — the reason for OR52.a (2)'s golden stored-config test.

## 7. The register (allover pass 2)

`audit/pass2/G1.md`-`G10.md` (one per harvest group and its plan areas) and `audit/pass2/LEAD.md` (the
lead's resolutions, merges and adopted gaps) are the requirement register; `audit/pass2/INDEX.md`
(generated) lists every live requirement by pillar, execution unit and owner row. Each requirement
states its final text, sources, rank with the tag its permanent text carries, state at HEAD with unit,
permanent home, pillar and what pass 2 changed.

- **Inputs, all placed** (`audit/sweeps/pass2_check.py`): 965 harvest candidates, 213 clusters, 673
  plan topics and seeds, 263 provenance decisions, OR1-OR83.
- **Output**: 535 requirements, 6 merged into another, **529 live**; 74 hold at HEAD, 455 carry work
  (code 319, doc 260, test 182, rule 68, hardware 50 — one requirement may carry several). Rank: owner
  254, owner-confirmed 53, fact 68, agent 137, convention 17 (after verification, OR74-OR86 and the refined
  harvest). Files: `G1.md`-`G10.md`, `LEAD.md`, `REF.md` (the refined harvest's new requirements).
- **Plan**: 141 topics and seeds carry a ⟨pass 2 …⟩ note (110 answered, 17 overtaken, 12 duplicate,
  2 stale); the other 532 stay execution checklist items.
- **Verification** (four adversarial verifiers, `audit/pass2/verify/V1.md`-`V4.md`): 68 defects in 523
  requirements — mostly ranks and dates, some scope wording (dropped "until" and veto qualifiers, a
  missing repair exception, a web-search ban against OR4.a), a few counts; applied per
  `verify/RULINGS.md`; two became owner questions 3-4.
- **Superseded pass-1 files**: `audit/hreq/MERGE.md` and `ROUTING.md` (their clusters, routing, adoption
  check and homes are in the register); `audit/hreq/G*.md` stay as the per-candidate evidence.

What pass 2 changed, in kind: owner answers applied everywhere they reach (363 of the groups' 505
requirements changed or new, 142 unchanged); lost owner decisions found in history and restored (harmonization 27); agent widenings of owner
words narrowed back (`crc_checks.py`, M.1.1 item 18, the literal VOC port); restored legacy functions
(NTP `Synced` staleness and force-resync clear, G6/R30); factual corrections (FRAM SPI not
timeout-wrappable, the nested `asyncio.run()` mechanism); 17 gap requirements and one unplaced decision added by the lead (LEAD/R01-R18).

## 8. Method history (for the record)

- Requirement passes 1-2 (2026-09-26): OR1-OR53 read against each other, the plan and CLAUDE.md.
- Harvest pass 1 (2026-09-26): ten agents extracted 965 candidates from the 6,500 harvest items
  (`audit/HARVEST_REQUIREMENTS.md`, `audit/hreq/`); answers OR54-OR63.
- Decision-provenance sweep (2026-09-26): six agents, 366 hits, 263 decisions
  (`audit/DECISION_PROVENANCE.md`); answers OR64-OR73.
- Allover pass 2 (2026-09-27): ten agents, one per group with its plan areas, brief
  `audit/sweeps/pass2_prompt.md`, assignment `audit/pass2/ASSIGN.md`; the lead resolved cross-group
  points against sources (OR7.a) and adopted gaps.
- Refined harvest (2026-09-28, owner's request to re-harvest with the knowledge gained): 38 recurring
  patterns (`audit/refined/PATTERNS.md`), 13 pattern sweeps over the whole repo and its history
  (`S01.md`-`S13.md`), 354 undeclared or extended findings (`FINDINGS.md`, RF001-RF354), integrated by
  seven agents (ledgers `I1.md`-`I7.md`, lead placements `LEAD_APPLY.md`): 251 placed, 19 corrected,
  11 lost owner decisions restored (merges `e5d2c43`, `8d89ff5`, `7a7f4b6` and rewrites), 8 new
  requirements (G7/R45, LEAD/R23, REF/R01-R06), 23 rejected, 24 routed to
  the owner as 20 decisions (`QUESTIONS.md`). S02 is the OR13.a/OR14.a history trace and S13 the
  OR48.a legacy scan of section 9; their coverage limits are in their coverage tables.

## 9. Next: passes 3+ and open owner items

The question-raising scans (harmonization 21), read-only, parallel agents allowed (PQ9). The refined
harvest ran two of them: the rule and decision drift trace over the doc history (S02, with S01 for
merges; drift spread over several commits and the "reason swapped" shape on comments remain) and the
legacy-loss scan (S13; the dev bench and legacy UART modules excluded by G9/R02). Remaining: defect
candidates among the seeds and the harvest's 171-item bucket (OR12.a), necessity verdicts (OR33.a,
Appendix B), open and deferred items (OR5, OR51.a (2)), and the sweeps' own coverage gaps (sample-level
scopes named in S03, S04, S07, S10 and S12). Output: owner questions in the owner's format; settled items become register lines.

Open for the owner (asked with the pass-2 report, `audit/pass2/LEAD.md` section 4): (1) answered by OR80
(datasheets in a private submodule, history kept); (2) answered by OR81 (stricter typing in this audit); (4) answered by OR82/OR83 (21 owner — three restored
from drift — and 4 agent, `audit/pass2/verify/L25.md`). Question 3 (boot order) is answered by OR75; OR74-OR78 (2026-09-28) are
applied to the register (`audit/pass2/LEAD.md` 1 #13). The F18 reading is confirmed (OR83). Still open from before: C12/C13 are deferred to BACKLOG's owner-question list (OR69.a (7)).
