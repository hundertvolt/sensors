# Project audit — plan and topic catalog

**Status: EXECUTION (phase B), since 2026-10-06 (OR145).** The owner gave the execution go-ahead in the
conversation of session `01BWfjT6GSD7bxCP57j86vB8`, covering the whole implementation up to the point where real
hardware is the next required step. Phase C (hardware rounds) still needs its own go-ahead in its own
conversation. From the go-ahead on, the pillars, rules and specifications are fixed and binding: they are applied,
not changed. Work runs in `audit/order/WORK_ORDER.md` order; progress lives in `audit/REGISTER.md`.

**Temporary.** Like every other temporary plan doc here, this file is deleted once the audit closes. Its
permanent outcomes (fixed code, settled decisions, new rules) migrate into `SPECIFICATION.md`,
`CLAUDE.md` or `BACKLOG.md` first; silicon-owed items go to BACKLOG.md's "Real-hardware work still owed" section. The retired
`src/` audit's `AUDIT_PLAN.md` (closed 2026-08-10, see README "Further reading") is the precedent for
this file's shape; this one is broader (whole project, not only `src/`) and deeper (down to function
internals, across every tier). The ID prefixes below are chosen not to collide with `SPECIFICATION.md`
Part IDs (`A.1`…`M.1.6`), real-hardware row IDs (`R1`, `F17`, `S4`, …), BACKLOG item
numbers or the undefined `WP1`-`WP8` labels already in the tree: areas use mnemonic codes, severities
follow PQ3 (proposed `SEV1`-`SEV4`), register findings are `AF-<AREA>-<nnn>`, owner questions `PQ<n>`.

---

## 0. How to read this file

- **Areas** (section 5) partition the whole repository into audit units, each with a mnemonic code
  (`CORE`, `NET`, `WEB`, …). Every git-tracked file has exactly one **owning** area or is on the
  explicit out-of-scope list (section 2.2); section 5.0 is that mapping. Other areas may read a file
  (e.g. DOC reads every doc for contradictions, LIC reads licence headers) without owning it.
- **Topics** (`<AREA>.T<nn>`) are the checklist: questions a deep audit of that area must answer. Where
  two areas touch the same question, the topic names its **owner** ("owned by …") and the others only
  cite it, so the work is done once.
- **Seed observations** (`<AREA>.S<nn>`) are concrete, file:line-anchored things the planning survey
  noticed. **Every seed is UNVERIFIED** — recorded by a read-only survey agent, not reproduced, not
  confirmed, not triaged. Some will turn out wrong. Verifying them *is* audit work and is blocked like
  the rest. A seed tagged `[x2]`/`[x3]` was reported independently by two/three survey agents (a
  convergence signal, not a verification).
- **Cross-cutting lenses** (section 4.2) apply to every area on top of its own topics.
- **Owner requirements** (3.2, `OR<n>`) are the owner's record, verbatim; sections 1, 2 and 4 are their
  integrated reading, and `audit/CONSOLIDATION.md` holds the big picture (pillars, phases,
  harmonizations, requirement → phase → permanent home).
- **Register** (`audit/pass2/`, allover pass 2): every requirement the owner rows, the harvest and the
  decision-provenance answers yield, stated once with its state at HEAD, execution unit and permanent
  home; `audit/pass2/INDEX.md` lists them by unit. A topic or seed whose pass-2 status is not plain work
  carries a `⟨pass 2, <status>: … — <group>: <requirements>⟩` note (answered, overtaken, stale, dup).
- **Status markers**: `[ ]` open, `[x]` done, `[~]` partially done (used in 1.2, 4.6, 5 and 6). During
  execution, progress lives only in the register (4.5); topic boxes in section 5 are not ticked.
- **Where things live**: this file (plan, topics, seeds); `audit/` (temporary audit apparatus: planning
  survey notes, the harvest of what the project's own comments/docs/history record, and later the sweep
  scripts, register and unit artefacts — PQ2); section 3.1 (owner statements, verbatim).
- **Line anchors** are as of commit `4dc80ef` (planning baseline: `main`'s head after the automated-build-chain
  merge, PR #58, 2026-09-25 — the audit's real starting point, owner, 3.1). Resolve them with
  `git show 4dc80ef:<path>`; at HEAD they drift. They were moved from the first baseline `0615eba` (and the
  harvest's `2a88cc8`) by `audit/sweeps/reanchor.py`; section 6 V11 records the move.

---

## 1. Goals and definition of done

### 1.1 Goals

1. **Release**: the working prototype becomes a true release version — consolidated, harmonized,
   "one material", no leftovers (OR1, OR5, OR24).
2. **Concept**: every part serves the device concept and its pillars P1-P12 (OR44;
   `audit/CONSOLIDATION.md` section 1), which end as SPECIFICATION.md's "Design principles" Part.
3. **Broad**: every tracked file outside the out-of-scope list is looked at by an auditor with a
   stated lens — code, tests, tooling, CI, website, docs, config (OR46, OR50).
4. **Deep**: every in-scope file is read in full at four levels — micro, imports, seams, macro
   (OR46.a); every hardware and runtime claim is checked against datasheets, the pinned MicroPython
   1.29.0 source and current documentation, never memory (CLAUDE.md, Part D.1/D.9, OR51.a).
5. **Proven**: every property the audit claims is shown by a biting test or a run, not by reading
   (OR16.a, OR19.a, OR21.a, OR25.a).
6. **Converged**: each area's findings stabilise under independent re-audit (4.4); contradictions are
   arbitrated by the lead against sources (OR7.a); re-verification passes repeat until one ends all
   green (OR9.a).
7. **Closed**: every item ends in one of OR5.a's states (4.5). BACKLOG.md afterwards holds only owed
   real-hardware items, C-port items and owner-deferred future goals with their reason.
8. **Feature parity**: top-level features never change (OR12); a legacy function lost on the way is
   restored or raised (OR48).

### 1.2 Definition of done (whole audit)

- [ ] Every area in section 5: topics answered, seeds triaged, quality measure met; every lens (4.2)
      applied and recorded per area — "N/A, because …" is valid, silence is not.
- [ ] Every register finding terminal (4.5); the owner has reviewed every decision taken on the
      owner's behalf (OR2.c) and every change logged for review (OR12.a, OR13.a, OR24.a).
- [ ] Every owner requirement OR1-OR83 fulfilled, traced through `audit/CONSOLIDATION.md` section 4 and
      the register (`audit/pass2/INDEX.md`, by owner row); every live register requirement holds.
- [ ] Green with zero `MemoryError`/`memory allocation failed`, at both GC stages wherever MicroPython
      runs (OR40.a): `scripts/lint.sh`, `scripts/typecheck.sh`, `scripts/test.sh` (`-1` and
      `GC_THRESHOLD=32768`), `scripts/test.sh --coverage`, `scripts/run_digital_twin_ci.sh` for every
      device in `devices/`, the npm tier (`npm run lint`, `npm run typecheck`, `npm run lint:html`,
      `npm run lint:css`, `npm test`), `scripts/build_firmware.py` for every device, and
      `uv run pytest tests_hardware --collect-only`; the last re-verification pass adds no finding
      (OR9.a). No test deleted or weakened without a register entry saying why (OR33.a).
- [ ] Coverage recorded before and after for `src/`, generated code and the host build chain (OR22.a,
      OR23.a); every unexecuted line covered or listed with its reason (OR25.a (3)).
- [ ] The permanent checks the requirements add exist and pass: error-number catalog (OR28.a),
      `@tunable` register (OR30.a), README vs `--help` (OR15.a), one summary block per runner (OR15.a,
      OR21.a), one runtime watchdog feed site (OR31.a), `gc` sites (OR40.a), tier containment
      (OR45.a), stored-config golden file (OR52.a (2)), device set derived from `devices/*.toml`
      (OR43.a), no current file pointing at an old legacy path (OR32.a), `.frozen` first on `sys.path`
      (OR59.a), the `reset_reason` codes (OR60.a), one event one entry (OR56.a (1)), actorless decision
      vocabulary and dead citations (OR68.a (4)), the REST reference and TOML schema contracts
      (LEAD/R08, LEAD/R11), no board-variant literal outside `devices/` (OR78.a).
- [ ] Docs: the "Design principles" Part and the one ordered checklist in SPECIFICATION.md, the
      `integrate-module` skill proven on the ISL29125 and BMP3xx baselines (OR10.b, OR44.a); README
      (OR15.a); history trace resolved (OR14.a); content rules met everywhere (OR27.a, OR51).
- [ ] Hardware work prepared (OR8.a, OR29.a) and run in the hardware rounds (OR5.a, OR17), including
      the two-image GC proof (OR40.a (3)), the FRAM read before reflash (OR28.a (1)) and the bench boot
      and trigger timestamps (OR47.a), the `reset_reason` codes on silicon (OR60.a (4)) and the standard
      board state at each round's start and end (LEAD/R02).
- [ ] End-of-execution report in chat and in PR #107's description, with one entry per new load test
      (OR49.a (3)).
- [ ] CLAUDE.md side-obligations met for every change: BACKLOG's chroot-owed list for build-environment
      changes, `UART_C_PORT_CHANGELOG.md` for `asy_uart_comm.py` changes, the bird's-eye `src/` scan
      for any new `src/` file, README "Further reading" for any new doc.
- [ ] Worktrees, scratch branches and tags cleaned up; PR #107 merged into the frozen `main` by merge
      commit (PQ2, OR52.a (4)).
- [ ] Every permanent fact this file and the register hold has migrated; the owner agrees the audit
      is finished; this file and `audit/` are deleted after the last hardware round (OR11.a).

---

## 2. Scope

### 2.1 In scope

All of: `src/`, `ext/` (behaviour relied upon only — see 2.2), `buildgen/`, `devices/`, `toolchain/`,
`scripts/`, `.github/`, root config (`pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`,
`eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `.htmlvalidate.json`, `.stylelintrc.json`,
`host_typecheck.ini`, `.gitignore`, `.nvmrc`), `js/`, `html/`, `mockdata/`, `tests/`, `tests_js/`,
`tests_scripts/`, `tests_hardware/` (desk review; execution only in phase C), `digital_twin/`,
and every markdown doc (`*.md` at the root, `digital_twin/README.md`, `tests_hardware/README.md`,
`dev_legacy/README.md`), plus `update_and_install.txt`, `LICENSE`, `THIRD_PARTY_LICENSES.md`. Added by
the requirements: `.claude/skills/` (OR10.a), `legacy/` once B1 creates it (OR32.a), everything the
setup installs or downloads (OR50.a), and the redistribution terms of `datasheets/` (OR52.a (7)).

### 2.2 Out of scope, or in scope only as a reference

| Path | Treatment | Authority |
|---|---|---|
| `arduino/` | Out of scope entirely: no audit, no reconciliation, no findings about its contents (licensing included); stays at the root; anything about it is post-audit only (OR5.a (3)); README.md and THIRD_PARTY_LICENSES.md state the exclusion (`LIC.T04`, G9/R21) | BACKLOG (owner, 2026-09-24), OR5.a (3) |
| `python/`, `modules/`, `build-*.sh`, `html_raw/`, `dev_legacy/`'s driver copies | **Read-only reference**, moved unchanged into `legacy/` in B1 (OR32.a). Read for the legacy-loss scan (consolidation, OR48.a) and parity (`PAR`); may run in a scratch directory as a published-value reference, nothing committed (PQ10). Never edited | CLAUDE.md legacy rule |
| `ext/microdot.py`, `ext/freezefs/` | Never edited or restyled. Audited only for *what this project relies on* from it, and for whether our wrappers cover its gaps. Stays on Microdot `v2.6.2` (`v2.7.0` checked 2026-09-26: nothing this project needs) | CLAUDE.md vendoring rule |
| `datasheets/` | Reference material, complete (OR53); becomes a private submodule, history kept (OR80.a) | CLAUDE.md / Part A.6, OR52.a (7), OR80 |
| `dev_legacy/` session logs and snapshot | Reference only; `README.md`'s current bench content moves to its canonical living docs in B1 (OR32.a (3)) | Part A.1 |
| `modules/_boot.py`'s `import sensortask.py` | Never changed without real-hardware testing (path becomes `legacy/firmware/…`, rule unchanged) | CLAUDE.md hard rule |

### 2.3 Standing constraints and CLAUDE.md conformance

Every auditor receives the packet defined in 4.4 ("Auditor context") and works inside CLAUDE.md's
rules; where an owner requirement rewords a rule, the requirement is named and wins.

- **Questions** arise only in consolidation passes (OR2.a, OR52.a (5)), in the owner's format: a
  numbered list, at most 10 words per decision, then options and consequences (OR51.a (3)). Execution
  never stops: an unforeseen decision takes the more conservative, more easily reversible option,
  grounded in sources, and is logged as decided on the owner's behalf; hardware and out-of-scope
  items are parked (OR2.c).
- **Behaviour or formula discrepancy** (Part D.1): proven by datasheet or specification → fixed with a
  regression test and logged; anything less → logged, not changed (OR12.a). **Consistency** (naming,
  ordering, signatures, equivalent behaviour): changed directly and logged (OR24.a); CLAUDE.md's
  "report, don't silently fix" is reworded accordingly.
- **Drift**: rule or decision drift → owner question in consolidation, followed as it stands and
  logged during execution; factual doc drift → fixed in place (OR13.a).
- **Settled decisions** are not reopened (BACKLOG "SETTLED", Part A.4 "confirmed intentional", the
  wedged-I2C/WiFi backstop rules, FRAM `verify_present()`/`set_write_protected()`, buildspec
  hand-maintenance, no UART version negotiation (OR70.a (10)), the SGP40 general-call reset
  (OR64.a/OR65.a), the hotspot fallback password (OR70.a (1)), every decision OR54-OR73 records)
  unless the premise is factually wrong — then a consolidation question. `NTP_Host`'s bound is no
  longer settled: it is re-decided with the key scheme (OR70.a (4)). The most recent owner decision
  wins without asking (OR68.a (2)); a decision without owner words is never declared an agent's (OR64).
- **Interfaces** (OR24.a (2), OR52.a (2)): internal code changes freely; REST routes and JSON keys,
  `devices/*.toml` keys, `@web` tags and FRAM layout names change only together with every consumer;
  no legacy REST path stays and key names follow one scheme before the release (OR58.a); the UART wire
  format is untouched; persisted config keys, file names and the REST surface are free until the
  release and stable or migrated after it (OR52.a (2), LEAD/R08); `ext/` and the legacy tree are never
  edited.
- **Product purity**: nothing frozen into the firmware exists for a test (OR20.a, OR36.a); API that
  completes a driver for its hardware stays (OR36.a (3)).
- **Exceptions**: no blanket `MemoryError` wraps around asyncio primitives (F.2), but a real
  graceful-degradation alternative is implemented (OR26.a). A missing, defective or stalled chip, or
  a config not matching the hardware, escalates through the supervisor to a reboot by design (OR18.a).
- **Memory**: design for zero `MemoryError`; `gc.collect()` only at the boot sites (product) and for
  measurement baselines in tests, never as a tool; `gc.threshold(32768)` set once; both GC stages on
  every MicroPython level (OR39.a, OR40.a).
- **Threat model**: trusted home LAN; unauthenticated writes and `bootloader` are documented
  limitations; malformed or oversized input never crashes anything (OR52.a (3), OR49.a).
- **Real hardware**: only in phase C, with the owner's go-ahead *in the conversation that runs it* —
  CLAUDE.md: a go-ahead "given to a different session, or to an earlier session that already ended,
  does not carry over" and "covers the rest of that same conversation"; subagents and child sessions
  don't inherit it; wear gates; FRAM-forensics-first (twin included); dead-man's switch for host
  network changes; `br0` MAC pinning. Audit agents never run `setup_toolchain.py env --tier
  flash|bench`.
- **Wear**, host SSD included: no brute-force scale, no mass files; per-agent toolchain rebuilds only
  when unavoidable; find the invariant (CLAUDE.md, OR37.a). Load and concurrency tests write no
  limited-endurance store; FRAM writes are not wear (OR49.a (2)).
- **Hygiene**: every test cleans up on every path; ports are OS-assigned or taken under a lock; evidence
  is archived, never deleted (OR38.a).
- **Docs**: current state, one short reason plus a provenance tag per rule, no history (OR27.a);
  every decision statement names its actor and date, an owner decision quotes the owner's words,
  compaction never changes actor, qualifier or scope, nothing permanent cites a temporary plan
  (OR68.a (4), harmonization 35); comment rule — one concise header block, at most 3 lines inline —
  for every file (PQ6, OR51).
- **`main` is frozen** for the audit; one merge at close (OR52.a (4)).
- BACKLOG numbering: numbers are never reused — the next new item is ≥ 51 (check `git log` first).
  Real-hardware row IDs live on in BACKLOG.md's "Real-hardware work still owed" (the queue and handover
  files were folded in there, `03f8bcf`); retired row IDs are never reused either — C7, R10, F7, F10,
  F11, F13, G9, and since 2026-09-25 T2, G1, G3, G4, G8, G12, N2, R1, R4, R5, R6, R7, F1, W4, W5.
- **Step-session workflow**: the audit is one unit — tests first for every fix; its "stop and report"
  is the end of execution (PQ8).
- **Fix obligations**: UART changelog entry for any `asy_uart_comm.py` change; bird's-eye scan for a
  new `src/` file; BACKLOG chroot-owed entry for any build-environment change.

---

## 3. Owner decisions

The ten planning questions are answered (last column, 2026-09-26). New owner questions arise only in
consolidation passes, in the owner's format (OR51.a (3)), and are recorded in 3.2.

| ID | Question | Options | Answer (planner's recommendation until answered) |
|---|---|---|---|
| PQ1 | Output mode and phase rules | (a) findings register first, then owner-prioritised fix units; (b) fix-per-area once that area converges; (c) findings only. Also: SEV1 escalated immediately? May the findings phase add tests/harnesses (the REST/GEN quality measures need a test matrix and a fuzz harness)? Is audit-found doc drift fixed in place (stale-doc rule) or registered? | **Answered 2026-09-26** (OR2, OR2.c, OR12.a, OR24.a): fixes are made during execution; a behaviour change only when proven by datasheet or spec, logged; no immediate SEV1 escalation (nothing runs on hardware during execution); harnesses allowed in throwaway worktrees; factual doc drift fixed in place, rule drift logged (OR13.a) |
| PQ2 | Branching, register location, merge | Owner intent (3.1): this work has its own branch and PR. The feature branch it was stacked on merged into `main` on 2026-09-25 (PR #58, `4dc80ef`), and the PR now targets `main`; this file lives on the audit branch only (removed from `main`, PR #108). Open: which branch the execution phase runs on (this one, or a fresh one per session/wave); fixes here vs one branch + PR per fix unit; where the audit apparatus lives (proposed: a temporary `audit/` directory — register, sweep scripts, wave artefacts — outside the lint/typecheck scopes, deleted at close); may the arbiter commit and push audit files autonomously after each arbitration batch; merge strategy into `main` (~77 "archive §" citations point at `12640c2`, reachable from `main` since the PR #58 merge commit — `DOC.S04`) | **Answered 2026-09-26** (OR11.a, OR6.a): one audit branch, one PR, one merge into `main`; no per-fix-unit branches; autonomous commits and pushes; apparatus in `audit/`; merge commit, not squash |
| PQ3 | Severity scale and sign-off threshold | proposed: SEV1 board/host safety, bricking, data loss, evidence loss; SEV2 functional defect, SEV3 robustness/latent, SEV4 consistency/doc/style | **Answered 2026-09-26**: SEV1-SEV4 kept for ordering the register only; sign-off superseded by OR12.a/OR2.c |
| PQ4 | Real hardware inside the audit | (a) none — every silicon item becomes an entry in BACKLOG.md's "Real-hardware work still owed"; (b) gated bench sittings inside the audit. Also: sequencing with bench sittings other sessions run meanwhile (the 2026-09-24/25 sitting finished and was folded into BACKLOG, `03f8bcf`) | **Answered 2026-09-26** (OR5.a, OR8.a, OR17): (a) — no hardware during execution; hardware rounds at the end, each with its own go-ahead |
| PQ5 | Threat model for `SEC` | (a) trusted home LAN; (b) untrusted LAN peers (guest Wi-Fi, IoT neighbours, DNS rebinding via a browser); (c) radio-range attacker in hotspot mode | **Answered 2026-09-26** (OR52): (a) trusted home LAN |
| PQ6 | Documentation scope | (a) correctness only (stale/contradictory/dangling); (b) also placement (I.6 inside Part J, CLAUDE.md size/auto-load budget, history pruning). Comment-cap extension to `tsconfig*.json`, `.gitignore` and 400-700-character one-line docstrings (`CI.S10`, `TEST.S22`) — `html/index.html`'s inline script is already under the current rule (`WEB.S19`); and whether docs should state the settled `arduino/` exclusion (`LIC.T04`) | **Answered 2026-09-26** (OR27, OR51): (b), placement and history pruning included; comment rule applies to every file |
| PQ7 | Moving target | Other sessions keep committing to `main`, the audit's base since 2026-09-25. (a) freeze non-audit work during the audit; (b) audit a pinned baseline and run delta passes over files changed since each area's closure. Also: one arbiter across sessions? Does the audit go-ahead persist across sessions? | **Answered 2026-09-26** (OR52): (a) `main` is frozen for the audit; one final merge |
| PQ8 | Owner stop-points (CLAUDE.md step-session "stop and report") | After ENV; after each wave; only at the end | **Answered 2026-09-26** (OR2, OR6.a): no owner stop-points during execution; the owner may look in at any sync point |
| PQ9 | Resources | Agents per wave, token budget, execution host/egress. **Partly answered** (owner, 2026-09-25, verbatim in 3.1: parallel agents "as many as you like", with care, converging, not interfering — given for the planning session). Open: does that permission carry over to execution sessions; may ENV prep (toolchain build, baseline run) happen before the go-ahead? | **Answered 2026-09-26**: the parallel-agents permission covers the whole audit (its "later work" plus OR1.a); ENV prep follows the execution go-ahead |
| PQ10 | Owner inputs the plan cannot derive | Is a legacy→refactor reflash campaign planned (makes `PAR.T06`/`PAR.T07` SEV1)? External REST consumers of the legacy routes (`PAR.T05`)? The Sensirion VOC C reference (reachable since 2026-09-25: `Sensirion/gas-index-algorithm`, OR4.a); missing datasheets (none left: RP2040, WS2812, QSPI flash, CYW43439 and BMP390 added 2026-09-25)? Permission to run legacy code as an oracle (`PAR.T12`)? UF2 distribution scope and repo visibility (`LIC.T06`/`T07`)? Browser support floor (`WEB.T09`)? Is `pico_gpio.py`'s conservatism intended (`GEN.T07`)? | **Partly answered 2026-09-26** (OR52, OR24.a): no legacy config migration, a reflash runbook only; legacy REST paths stay (overtaken by OR58.a: none stays); public MIT repo; browser floor current Chromium, Firefox, Safari; legacy code may run in scratch as a published-value reference. Sensirion VOC notes uploaded; `GEN.T07` answered (OR53) |

### 3.1 Owner record (verbatim, dated)

Statements that shape this plan, quoted exactly so no session works from a paraphrase. Planning-session
statements bind the planning session; whether they carry over is asked in PQ2/PQ7/PQ9.

| Date | Statement (verbatim) | Scope |
|---|---|---|
| 2026-09-25 | "For the whole project, I want to do a substantial audit, broad (over the whole project) and deep (down to function internals) at a time. So this is really going to be a lot of work, it will probably run for days on its own. I am currently setting it up on a branch which is soon going to be merged into main, and it's currently the only branch off main, so there will be no difference between this branch and main in the future, and this PR will point at main - this is exactly my intention." | Audit scope; the feature branch merges into `main` |
| 2026-09-25 | "Scan through the whole project, its documentation, its code, and get a solid overview of what it does and how it works. We will need this overview in the discussion later in many aspects, so be thorough, take good care." | Planning survey; its residue is kept (`audit/PLANNING_SURVEY.md`) |
| 2026-09-25 | "The first step to be done is that we will record a large list of which topics to cover in the audit and how to proceed. This will take a while, the list will become huge, and you are always free to extend and check it whenever you see something missing or something which would make sense or improve it." | This file |
| 2026-09-25 | "The actual work on the audit remains blocked until my explicit go-ahead. Do not misunderstand any of the recorded topics as an implicit start. I will tell you when we are done." | Execution gate (header) |
| 2026-09-25 | "Throughout the whole session, both research, recording and later work, you have my explicit go to use parallel tasks and agents - as many as you like. Anyhow, do this with care and apply your best arbitration style. Always look out for the results to converge and for the agents not interfering each other." | Parallel agents, planning session (4.4; PQ9) |
| 2026-09-25 | On the committed bench password: "that is a generated login, I wonder why it got persisted in a file. It's a pure throwaway board-bench-password, low risk, no alarm here. The only topic to note and to check here throughout the audit is consistency. Such temp credentials are usually generated, and persisting one in a file rather is a stylistic (and not safety) breach which will need harmonization. One topic to record in our list." | `HW.T11`, `HW.S08`, `SEC.T07` |
| 2026-09-25 | "It is good that you already pre-record findings and details, this will be very useful for the discussion when I start adding my topics. You don't need to search for solutions right now, recoding all you find and all which is noted in comments and docs is sufficient, and it's more important not to miss anything there." | Planning records, never solves; the harvest (`audit/`, V10) |
| 2026-09-25 | "For this session we need our dedicated branch and our dedicated PR. Don't just push on the claude/automated-build-chain-nuzumw branch." | Planning work lives on `claude/whole-project-audit-plan` with its own PR (PQ2) |
| 2026-09-25 | "Our base branch was just merged into main, and therefore our PR should also point to main." | PR #107 targets `main` (PQ2) |
| 2026-09-25 | "There was a PROJECT_AUDIT_PLAN.md found in main - it actually does not belong there, only in our branch and it's to be deleted at the very end of the audit. And the other session wrote into it. So read what it added, don't lose anything, but remove the file from main then." | The other session's edits (`03f8bcf`: queue/handover references repointed to BACKLOG) are merged here; the file is removed from `main` by PR #108 and lives only on the audit branch until the audit closes (OR11.a) |
| 2026-09-25 | "From the scope of our branch, everything should be based on the head of main, as the actual real intended starting point of our audit." | Planning baseline `4dc80ef` (section 0; V11); the audit baseline (ENV.T08) is `main`'s head at go-ahead |
| 2026-09-26 | "Generally, stop timed checks. Do hooks only." | PR and CI watching (OR6.a's "wait for CI") uses only the GitHub event subscription; no scheduled check-ins or self-set timers in any session |

Go-ahead record (empty until given): date · session · scope (which phases) · `HW.T14` board-free
collection confirmed (y/n). Standing, from the PQ answers: autonomous commits of audit work (PQ2) and
parallel agents (PQ9) are authorised for the whole audit; the real-hardware go-ahead is never carried
over (per conversation, CLAUDE.md). PQ answers are recorded in the PQ table's last column.

### 3.2 Owner requirements (verbatim, collected with the owner; worked into sections 1, 2 and 4 by consolidation pass 2)

Read with the 2026-09-25 fold (`03f8bcf`): `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md` no
longer exist — every "queue row" or queue file named in an interpretation below means an entry in
BACKLOG.md's "Real-hardware work still owed", and OR11.a's deletion of those two files is already done.
The owner's words themselves are unchanged. Where a later row overtakes an earlier interpretation, the
later row wins; `audit/CONSOLIDATION.md` section 5 lists each case, section 4 maps every row to its
phase and permanent home.

| ID | Date | Requirement (verbatim) |
|---|---|---|
| OR1 | 2026-09-25 | General scope and principles: "The process in this repo up to now was dealing with picking up on existing code, gathering its ideas and notions, and promote it into a common, strong improvement direction. It also dealt with gathering as much detailed information as possible. A previously non-existent environment for building and testing was introduced. Finally, a working full prototype of both the sensors and the environment was the goal - complete, stable, working. Mostly correct, mostly good, but not finally perfect. This has been achieved. Therefore, the task of this session is consolidation, harmonization, and perfection as far as possible." |
| OR1.a | 2026-09-25 | Clarification of OR1's "this session": "yes, with \"this session\" I mean \"the global audit\"." (i.e. the whole multi-session audit, not one conversation) |
| OR2 | 2026-09-25 | Cross-checking and self-containment: "When we start actual work: For any topics or requirements which was added or recorded, cross-check them with the other found or recorded ones, with the code, with general project knowledge, with our documentation, with your harvest results, and very important with external sources like repos, documentation, datasheets etc. as a real-world, best practice grounding. You should be able to answer most imminent questions raised throughout the audit already with this. If there really is an open question or decision, ask immediately. Once the audit is started, it should run self-contained and uninterrupted." |
| OR2.a | 2026-09-25 | Clarification of OR2's "ask immediately" vs. "uninterrupted": "I mean that there are two places where the questions should go: at the recording of the requirements (as you just did), or at the pre-work consolidation and extension run which crosses the requirements and your findings with themselves exhaustively. I will tell you when to start that consolidation run; it will be at the time my requirements are all fully recorded." (i.e. questions are raised only in these two phases, never during execution; the consolidation run is a separate phase, started on the owner's word, and is not the execution go-ahead) |
| OR2.b | 2026-09-25 | Exit criterion of the consolidation run: "one that consolidation round is done, you should be at a knowledge level at which you can find all answers the work details will bring all by yourself and continue uniterrupted." (i.e. the consolidation run is complete only when every question execution can foresee is already answered) |
| OR2.c | 2026-09-25 | Unforeseen decisions during execution: owner answered "yes, that matches" to the proposal: never stop or ask; ground the decision in code, docs, datasheets and external sources; take the more conservative, more easily reversible option; record it in the register as a decision taken on the owner's behalf, with its reasoning, for review afterwards. Exception: anything needing real hardware or going beyond the agreed scope is not decided but parked for the owner. |
| OR3 | 2026-09-25 | Apparent contradictions: "In case you find topics I mentioned or findings of you might potentially be contradictory, they surely are not. Such cases always mean that there is a topic to be fine tuned - a reason to ask and clarify in the recording and / or preparation and consolidation run." |
| OR4 | 2026-09-25 | Depth of investigation and sources: "Investigate deeply and widely at a time if you find an open issue. Try to resolve as much as possible yourself. Apply general project patterns and styles, apply good coding practice and proven patterns, adhere to our rules and specifications, actively search for answers in web repos, documentations, forums, datasheets. Notify me if you cannot access a valuable source or a datasheet, I can try to download it for you." |
| OR4.a | 2026-09-25 | Inaccessible sources during execution: owner answered "yes, that's right." to the proposal: do not wait; continue from the next-best source; mark the affected finding "open until the owner provides X"; report it in the progress and final reports; re-check those findings once the source arrives. The consolidation run tests access to every source it anticipates and hands the owner one list of what is unreachable. Known gaps at recording time: RP2040 chip datasheet, BMP390, WS2812/NeoPixel, Pico W QSPI flash chip, Sensirion VOC algorithm reference, possibly CYW43439 (the owner is uploading them). Status 2026-09-25: BMP390, W25Q16JV, CYW43439 and WS2812 uploaded and added to `datasheets/`; `Sensirion/gas-index-algorithm` is reachable via GitHub (cloned for reference, not vendored); the RP2040 datasheet was pushed by the owner (`datasheets/pico w/RP-008371-DS-1-rp2040-datasheet.pdf`); the Sensirion VOC Index notes were uploaded by the owner on 2026-09-26 and added to `datasheets/sgp40/` (OR53); blocked by the session's network policy: `www.sensirion.com`, `pip-assets.raspberrypi.com`, `datasheets.raspberrypi.com` and `www.adafruit.com`. |
| OR5 | 2026-09-25 | No leftovers, release target: "Once the consolidation run is started, check for any documented issues, flagged items, still open or opened along the way topics, missing resolutions. There shall be no more leftovers after the audit, the target is a true release version. Verify the issues were not already resolved and are no stale leftovers." |
| OR5.a | 2026-09-25 | Closure states and real-hardware phase: owner answered "yes to 1, and add a real-hardware phase at the end. the C port stays out of scope, anything there is post-audit only," — (1) every item ends in exactly one of: fixed; verified already resolved/stale and removed; settled by decision and documented as a permanent fact (CLAUDE.md/SPECIFICATION.md); out of scope by owner decision and documented as a known limitation — nothing remains "open"/"TODO"; `UART_C_PORT_CHANGELOG.md` stays until the C side is reconciled. (2) The audit ends with a real-hardware phase on the dev bench that closes every item parked for real hardware; it starts only with the owner's go-ahead given in that session's own conversation (CLAUDE.md hard rule). (3) The Arduino C port stays out of scope; anything concerning it is post-audit only. |
| OR6 | 2026-09-25 | Sync points, tests and CI: "While doing the audit, allow pauses to sync up a meaningful intermediate state. Push regularly. Run the test suite, and watch CI. Do not ignore any test or run failures. Investigate every issue and be sure that it really was a flake we can't do anything about (e.g. verified temporary Gitlab outages) and which will resolve by themselves, otherwise investigate and resolve according to our rules." |
| OR6.a | 2026-09-25 | Owner answered "yes to both, GitHub is what I meant." — (1) a "pause" is a self-set sync point, not a wait for the owner: commit and push the finished unit, run the full local suite at both GC settings, wait for CI on that push to go green, update the register and a short status note on the PR, then continue at once; the owner may look in at any sync point. (2) "Gitlab" means GitHub (or any other external service CI depends on: PyPI, npm, download mirrors). A failure counts as a flake only if the provider's status page or error confirms the outage AND the same job passes on one re-run with no code change; anything else is root-caused and fixed. |
| OR7 | 2026-09-25 | Multi-agent coherence: "This is a genuinely large task with strict requirements and a high demand of quality. If you run multiple agents throughout the process, check what they return, keep the big picture in mind and check how it all fits together. Resolve contradicting results of different agents, monitor their convergence, resolve any conflicts. It is of major importance that the final result is 100% coherent and clean." |
| OR7.a | 2026-09-25 | Owner answered "yes, that's the split" — conflicting agent results are resolved by the lead, never by majority vote: each claim is checked against code, datasheets and external sources and the verdict is logged in the register. Only a conflict that traces back to an owner requirement or decision goes to the owner: as an OR3 question during the consolidation run, or decided under OR2.c during execution and logged for the owner's later review. |
| OR8 | 2026-09-25 | No hardware access yet: "For now, you do not have access to the real hardware, but be sure to prepare everything along the tests you can already conduct; once this passes, we will have a real hardware session as a follow-up." |
| OR8.a | 2026-09-25 | Owner answered "yes, that's right" — the audit completes every tier that needs no board (unit, twin, tests_scripts, web, CI) and fully prepares the hardware work: new/changed hardware tests written, linted, typechecked and collection-checked, wear budgets stated, and `REAL_HARDWARE_TEST_QUEUE.md` listing exactly what to run, in which order, with expected outcomes. OR5.a's real-hardware phase is that follow-up session; it works through the queue, closes every item parked for hardware, and starts only with the owner's go-ahead in that session. "No leftovers" at audit end therefore means: the only open items are those queued for that session; the release is final once it passes. |
| OR9 | 2026-09-25 | Final re-verification: "When you arrived at a point where you assume everything is really all done, re-verify all our rules, specifications, best practices and patterns were really correctly applied and did not accidentally break along some fix which came in after the initial scan. Run the full tests again. As the processes naturally apply in a serial manner, a second pass always knows more than the first, therefore double-check until everything is sane and sound is the word." |
| OR9.a | 2026-09-25 | Pass termination: "Not exactly, it's not necessary that every finding retriggers all. One pass finishes with all its new knowledge and fixes, the next pass starts, until all is green." — a finding does not restart the pass; each pass runs to completion, fixing what it finds along the way; the next complete pass then starts with that new knowledge; this repeats until a pass ends all green (no findings, full suite and CI green). |
| OR10 | 2026-09-25 | New-module integration procedure: "While you are sweeping through the repo: Starting from the first sensor driver promotions, all the way through the development and growth, until the most recent addition of the buildgen and the promoted UART and ISL sensor, gather information about what all needs to be done when adding modules, step by step. Gather information about which patterns and qualities are to be applied. You will find plenty of details in the documentation as well. My goal is to be able to do a full integration of a new sensor starting with just a datasheet, a discussion about top level features, API and website design. Apart from that, no additional explanation is required, a multi pass and multi staged build can be done fully agentic from that point on, reaching all qualities of integration, reliability, patterns, testing, and automation." (Existing starting point: SPECIFICATION.md Part K, the promotion checklist distilled from the UART and ISL29125 promotions, with Parts C and D.) |
| OR10.a | 2026-09-25 | Owner answers: "1. yes 2. yes, but sensor drivers are modules by themselves with a hardware counterpart - so modules are the general case, sensors a specific one with extensions 3. You mean, optimize the process starting from fresh against a baseline? That's a very good way to go, you could even do that against a BMP3xx as a baseline as well to cover possible gaps" — (1) SPECIFICATION.md Part K stays the single source of the procedure, extended with the owner-discussion stage (features, API, website) and its output record; a thin repo skill (e.g. `.claude/skills/integrate-module/`) is the entry point for the agentic multi-stage build and points into Part K rather than copying it. (2) Modules are the general case; sensor drivers are a specific module with a hardware counterpart and extra steps on top. (3) The procedure is validated and optimised against baselines: a fresh agent gets only a datasheet plus a short feature/API/website brief, follows the procedure, and its result is compared with what the real promotion needed; every gap closes back into Part K/the skill. Baselines: ISL29125 and BMP3xx. |
| OR10.b | 2026-09-25 | Owner answered "yes, that's right" to the baseline method: the fresh agent really builds the module in an isolated throwaway worktree from only the datasheet and the brief, through every test tier and the build; its driver, config, `@web` tags, twin model and tests are compared with the real ones; every divergence caused by the procedure (not by legitimate design freedom) becomes a fix in Part K or the skill; the run repeats (OR9.a-style passes) until one full run against both baselines shows no gaps; nothing from the throwaway worktree is ever merged. |
| OR11 | 2026-09-25 | Final cleanup of temporary and stray files: "There were many temporary files created in many branches. With this final cleanup, they are all obsolete, while it needs to be ensured that no valuable information is lost and no crosslinks are broken. Then, all of these temporary files can be removed. The same goes for autocreated files and directories which once landed in Git accidentially or which are no longer used / referenced." |
| OR11.a | 2026-09-25 | Owner answered "yes to 1, and nothing needs to do in any of the other branches. It happens in our branch alone, and is applied to main in the merge. that is all." — (1) Timing: every other temporary, stray, auto-created or unreferenced file goes in the audit's final cleanup, after its content and crosslinks are migrated; `REAL_HARDWARE_TEST_QUEUE.md`, `HARDWARE_TEST_HANDOVER.md`, `PROJECT_AUDIT_PLAN.md` and `audit/` (register included) go at the close of the hardware follow-up session; `UART_C_PORT_CHANGELOG.md` stays until the post-audit C reconciliation. (2) Other branches are out of scope: the cleanup happens only on the audit branch and reaches `main` through the merge. |
| OR12 | 2026-09-25 | Refactors, regressions and tests: "If you do larger refactors, which is fine in general if really required, ensure you do not change any functionality. My expectation is that the current features remains across the changes done here, and that our vast set of tests is an insurance to exactly achieve this with zero regressions. So if any test fails, fix the regression and do not try to work around. Adding new tests when finding gaps is very welcome, adding regression tests is very welcome as well. Adapting tests to firmware changes is only allowed for mechanical corrections, but not for changing the actual test goal." |
| OR12.a | 2026-09-25 | Owner answered "yes, that's the line" — regression vs defect: top-level features never change (CLAUDE.md). A defect (behaviour contradicting the datasheet, the specification or field-proven legacy behaviour) found in the consolidation run goes to the owner as a question before anything changes (CLAUDE.md "flag, don't silently change"). One found during execution and proven by datasheet or specification is fixed with a new regression test for the correct behaviour; an existing test's expectation is corrected only where that proof shows it pinned the defect; each such change is logged in the register with its proof for the owner's review (OR2.c). Anything less clear-cut is not changed during execution but logged for the owner's review. |
| OR13 | 2026-09-25 | Docs vs implementation, drift and under-used features: "Check if the documentation and the requirements match what has been implemented. The project as such and its setup is a statement of its own and must be complete and inherently sound. Check for places which seem not to make sense, contradict common sense and patterns. Deviations from the usual style are also a hint of misunderstandings. We had several cases where false decisions were written down or drifted away from focus and their goals over the development process and several textual refinements and cleanups, and were lateron strictly obeyed or referenced. This lead to discussion blockers which were hard to understand. Therefore, look out for strange formulations or contradicting decision or style recordings, and ask for clarification. Often, looking to some commits or states in the past may clarify as well and make drifts more visible. Look out for implemented features which are not or only partially exploited. Look out for missed opportunities where features could have been used, but were only partially or not at all. There is a long history of such oversights or misunderstandings. At many places, code grew over time, and either added features were incompletely retrofitted, or already existing ones forgotten in new code." |
| OR13.a | 2026-09-25 | Owner answered "yes, that's right" — drift in recorded rules and decisions (CLAUDE.md hard rules and working agreements, owner decisions quoted in SPECIFICATION.md or BACKLOG.md): found in the consolidation run, it goes to the owner as a question with its history (original wording and intent, what it drifted to) and nothing changes before the answer; found during execution, the rule or decision is not reworded or overridden but logged for the owner's review, and the work follows it as it stands unless that would break a test or the build (also logged). Plain factual docs (READMEs, SPECIFICATION.md facts, code comments) that contradict the code without recording a decision are fixed during execution like any other finding. Starting set: the 468 harvested DRIFT items plus git history. |
| OR14 | 2026-09-25 | Historical drift check of the docs: "Fitting to it: Pick several well fitting repo states (or the whole history) in the past and check that our documentation did not drift out of important scopes. Over the many iterations, topics may have been washed out or drifted into a wrong direction. This is especially important for all markdown files." |
| OR14.a | 2026-09-25 | Owner answered "yes, that's the method" — states: every merge (117 on the feature branch at recording time) as milestones, the full per-commit history of CLAUDE.md, SPECIFICATION.md, BACKLOG.md and README.md, and every other markdown file at the milestones. Each topic, rule and decision that ever appeared is traced to one outcome: still stands with the same meaning; resolved or migrated elsewhere (verified); pruned as history on purpose (legitimate, per CLAUDE.md's "current state, not the historic path"); lost (vanished with nothing in its place); or drifted (wording changed its meaning, scope or goal). Lost and drifted items enter the OR13.a flow. |
| OR15 | 2026-09-25 | README usability and end-of-run summaries: "The documentation in the repo root's main README.md must be very user friendly, descriptive, show all options in an ergonomic manner, and contain copy-paste examples for a complete installation from scratch, building and deploying firmware, running the test suites and test tiers, all with typical, everyday use examples for copy-pasting into the console. All commandline options to be listed and described. Also, running test suites must result in an automated summary at the end, so after multiple pages of results and console prints, the outcome is clear on first sight. Most of this is at least partially the case already." |
| OR15.a | 2026-09-25 | Owner answered "yes to both" — (1) README layout: a task-oriented top part with copy-paste recipes in the order people need them (install from scratch, build and flash, run tests per tier, everyday variants), then a complete command-line reference with one collapsible section per tool (every option, described); a `tests_scripts/` check compares each tool's own `--help` with the README reference and fails CI on any mismatch. (2) Every runner (`scripts/test.sh`, the digital-twin CI runner, `npm test`, `lint.sh`, `typecheck.sh`, the hardware-tier runners) ends with the same final block: one overall PASS/FAIL line; passed/failed/skipped/deselected counts; the names of failing files or tests; the exit code. |
| OR16 | 2026-09-25 | Silently broken chains: "Keep a sharp eye on incomplete or silently broken chains, both for the module and sensor assemblies as well as for all tests. There is a long history of accidentally stumbling upon such silent failures and losses during other, sometimes actually unrelated tasks. Trace all execution paths of functions and tests and ensure there are alive and sound." |
| OR16.a | 2026-09-25 | Owner answered "yes, including the fault-planting check" — "alive and sound" is proven by tools and runs, not by reading: (1) chain completeness per device TOML — every declared module constructed, set up, started and task-supervised, reachable through its REST route, rendered on the website through its tags, and logging into FRAM where wired, shown by the digital twin booting that device; (2) test liveness — every test file is collected by some runner and CI job, none is orphaned, and every skip, deselect and opt-in gate is inventoried with a still-valid reason; (3) execution — every `src/` line no test executes is covered by a new test, proven dead and removed, or justified (buildgen and scripts likewise where measurable); (4) tests bite — per module, a small set of planted faults (flipped comparison, dropped call, swallowed exception, …) in a throwaway worktree must each turn the suite red; a surviving fault is a gap and gets a new test; nothing from the throwaway worktree is kept; targeted per module, not full mutation testing. |
| OR17 | 2026-09-25 | Digital-twin fidelity: "Ensure that, with all knowledge which was gained over many real hardware runs, the digital twin models the real hardware as close and as correct as possible. During the runs on hardware, it was not always guaranteed that the twin setup was always tracked along, so make sure it fits, in case of any doubt, add items to the real hardware test list. We can spend multiple rounds of real tests once the general audit is done." (Amends OR8.a: the hardware follow-up may span multiple rounds.) |
| OR17.a | 2026-09-25 | Owner answered "yes, that's right" — twin-fidelity method: (1) inventory every hardware fact ever measured or observed, from the current docs (SPECIFICATION.md Parts F and I, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `tests_hardware/README.md`), the 20 deleted run logs/handovers/plans in git history (e.g. `REAL_HARDWARE_RUN_LOG.md`, `REAL_HARDWARE_HANDOVER_*.md`, `ISL29125_HARDWARE_VERIFICATION.md`, `UART_BENCH_SESSION_HANDOVER.md`) and hardware results quoted in commits and PR descriptions, each with source and date; (2) a fidelity table: how the twin models each fact — match, mismatch, or unmodelled; (3) mismatches and gaps are fixed in the twin where the evidence is solid, tuned to measured evidence only, never to assumptions; (4) every fact in doubt (old, measured on an older image, contradicted by another run, or never measured) becomes a `REAL_HARDWARE_TEST_QUEUE.md` row naming the exact measurement and the twin parameter it confirms; (5) the hardware rounds compare the results with the twin and correct it, repeating until they agree. |
| OR18 | 2026-09-25 | Larger-scale bad patterns: "Look out for larger scale bad patterns, e.g. we once stumbled upon the NTP servive just stalling its task if the server was unreachable instead of handling it internally and properly self-contained. It purely relied on the global task supervisor mechanics to restart it, and thereby even using a retry rate which would have been able to drive the system into a reboot by the repeat and decay counter rising over several minutes. This should be fixed, and a short scan for that pattern was run in the aftermath. Anyhow, scan thoroughly again, and generalize - it's not just that pattern, but similar ones (any abnormal, but harmless situation not handled but just ending the task), or even totally different ones, just generally abusing system methods for something they could handle themselves, or even more hidden ones just causing unexpected side-effects. This can also be hidden in an integration tree, not only single function or module. A strong hint for such bad pattern could be any place where tests for normal situations accept or even expect log entries for wrnno or errno. One situation is deliberately out of scope: a missing or defect chip, or a configuration not matching the hardware. This is inoperational by definition, and nothing which can be fixed by software alone, and does not need a special handling." ("wrnno"/"errno": the warning/error numbers logged through `print_log.py`'s `wrn_s()`/`err_s()`.) |
| OR18.a | 2026-09-25 | Scope of the exclusion: owner chose (b): "b, because a stalled chip may recover by a reboot, keeping it contained going so far may miss that opportunity" — for a missing, defective or stalled chip, or a configuration not matching the hardware, no requirement applies to the rest of the system: escalation through the task supervisor up to a reboot is acceptable and even intended, since a reboot may recover a stalled chip (the same reasoning as CLAUDE.md's watchdog backstop for a wedged I2C bus). The scan must not "fix" such cases by containing them. The exclusion covers only these hardware/config faults; abnormal but harmless situations (e.g. an unreachable server) must still be handled inside the module. |
| OR19 | 2026-09-25 | Biting tests: "Many tests were added to ensure high coverage. Yet, these tests were not always designed to be \"biting\", meaning that they just blindly execute the lines of code without actually testing what these lines are expected to do. We need to scan through the full test suite and turn such blank tests into biting tests." |
| OR19.a | 2026-09-25 | Owner answered "yes, that's right" — biting-test method (~4,500 tests at recording time: tests/ 3,194 in 87 files, tests_scripts/ 1,017, tests_js/ ~192, tests_hardware/ 136): (1) every test is reviewed, no sampling, and classified biting / weak / blank; red flags: no assertion, or only "no exception" / "not None" / type checks; a check that cannot fail or that re-asserts a stand-in's canned return; `except: pass` in the test; asserting a log line exists but not its content; loops that check nothing; tolerances wide enough to pass anything. (2) Expected values come from an independent source (datasheet, specification, hand calculation), never copied from current output; a copied value is re-derived, and a mismatch goes the OR12.a defect path. (3) Proof via OR16.a's fault planting, extended per test file against the code that file targets, recording which tests catch which fault; a test catching none of its target's faults is weak or blank however it looks. (4) Strengthening keeps each test's goal (OR12). |
| OR20 | 2026-09-25 | Test placement and isolation: "Important fact about unit tests. We had several cases where the unit tests were completely integrated into the digital twin or the real hardware, leading to memory contention or other crosstalk. This resulted in a number of false positive failures which were close to impossible to track. Therefore all tests are required to adhere to or to be retrofitted to the scheme: - No code added purely for tests in the business logic files ever - Try to avoid putting test code inside the digital twin or the test tier rigs as far as possible. Only if there is no alternative, and keep tiny anyway. - Implement tests in the host's native environment (e.g. CPython) as far as possible." |
| OR20.a | 2026-09-25 | Owner chose (a): "a, that's what I meant" — "host's native environment" means on the host, outside the device-under-test's process, not literally CPython for `src/`: the unit tier stays on the MicroPython Unix port (CLAUDE.md, SPECIFICATION.md Part E.1 unchanged); for the twin and hardware tiers, the test logic (driving, asserting, measuring) lives in a separate host-side CPython process that drives the DUT from outside (HTTP, serial, …), with at most a tiny stub inside the twin or on the board — SPECIFICATION.md Part E.9 "Driver/DUT process separation" made the rule everywhere and retrofitted. Plus: no test-only code in business-logic files, ever. |
| OR21 | 2026-09-25 | Silent test blindness: "Throughout the development, we stumbled upon \"silent test blindness\" by chance several times, both for software and for hardware tests - meaning that the test was testing something real, but still was insensitive to conditions which would be a failure and returning \"PASSED\" under all circumstances, making failures undetectable. The condition of this blindness itself was undetectable by regular runs as well, rendering the test functionally useless although intended correctly. We need to find all tests affected by such issues and correct them." |
| OR21.a | 2026-09-25 | Owner answered "yes, but the control arms are overkill" — (1) blindness is found by triggering, for every test (check-style tests first: memory gates, soak checks, log greps, timing bounds), the exact condition it exists to catch, which must turn it red: planted faults (OR16.a/OR19.a) for software tests; for hardware tests, their host-side logic (OR20.a) pointed at the digital twin with the fault injected there; what the twin cannot inject becomes a deliberate fault check in the hardware queue. (3) Every run reports skipped/deselected/gated counts, and a test that passes with nothing actually checked is reported as such (extends OR15.a's summary block). (2) Not adopted: no new permanent control arms in CI — the sensitivity proof is done once in the audit; existing control arms (e.g. `test_digital_twin_boot_contiguity.py`) are left as they are. |
| OR22 | 2026-09-25 | Tests for generated code: "Ensure that the scripts dynamically generated have the same, complete set of tests as the actual source code - full functional tests, all error paths, coverage and regression, with the resilience explicitly testing for clean error handling and communication, as well as self-healing." |
| OR22.a | 2026-09-25 | Owner answered "yes, that's the scope" — (1) "generated scripts": each device's generated `sensortask_<device>.py` and boot entry (the core), the generated website definitions (tested against the JS that consumes them), and the frozen-HTML/freezefs output (served content matches the source). (2) The same bar as `src/`, per device, all six (arzi, dev, grkizi, klkizi, schlafzi, wozi): full functional tests; every error path (each module's setup failure, task crash and supervisor restart, bad config); regression tests; line coverage of the generated code measured like `src/` — at recording time the tracer only records `src/` and `digital_twin/` (`tests/_coverage_runner.py:24`), so generated modules are unmeasured. (3) Resilience via faults injected into a booted device (unit and twin tiers), asserting clean handling, correct communication (REST error responses, error/warning numbers, FRAM logs, LED/notification signals) and self-healing (reconnect, re-setup, supervisor restart, return to normal readings); for hardware faults under OR18.a the expected outcome is escalation, not containment. |
| OR23 | 2026-09-25 | Tests for buildgen: "Ensure that the buildgen scripts themselves have the same, complete set of tests as the actual source code - full functional tests, all error paths, coverage and regression. The only difference with the error and resilience paths being that the build always aborts on errors and reports them such that a user can easily see what to do as a resolution." |
| OR23.a | 2026-09-25 | Owner answered "yes to all three" — (1) scope: the whole host-side build chain, i.e. `buildgen/` (22 files, ~18 `tests_scripts/` files at recording time) plus `scripts/build_firmware.py`, `build_frozen_html.sh`, `build_website.sh`, `toolchain/setup_toolchain.py` and `micropython_overrides.py`. (2) Coverage: host-side line coverage is added under the pytest tier (none measured at recording time), report-only and never gating, like `src/`. (3) Error contract: every error aborts with a nonzero exit (no warn-and-continue unless a documented rule allows it); every message names what rule was broken, where (file, TOML table/key or line) and how to fix it; user errors show the message without a Python traceback, tracebacks only for internal bugs; every error path has a test asserting the exit code and that the message carries what, where and the fix. |
| OR24 | 2026-09-25 | Uniform method naming, ordering and behaviour: "Check naming, sorting and functionality of the module's methods and apply consistently. Change, don't flag, if not according. The whole repo code shall be made out of one material once the audit is over." |
| OR24.a | 2026-09-25 | Owner answered "yes to both" — (1) Within the audit, OR24 is the owner's advance authorisation for consistency changes (naming, ordering, signatures, uniform behaviour of equivalent methods), overriding CLAUDE.md's "do not silently fix it … report it and discuss" for this class: changed directly, each change logged in the register; CLAUDE.md's rule is reworded afterwards so it no longer blocks such harmonisation. Formula/behaviour discrepancies (Part D.1) still go the OR12.a path. (2) Interfaces: internal code changes freely; public interfaces (REST routes and JSON keys, `devices/*.toml` keys, `@web` tags, FRAM layout names) change only together with every consumer in the same change (`src/`↔`js/` mirror, website, TOMLs, tests), and legacy REST paths that external clients may use stay; the UART wire format is not touched (C side out of scope); vendored `ext/` and the legacy tree are never touched. |
| OR25 | 2026-09-25 | Coverage of intent at every layer: "Extra carefully scan if at any of all single function, module, functional integration, system integration layer, all unit tests are covering 100% of the intended normal functionality, 100% of all error paths, 100% of resilience and self-healing, and as much coverage as sensible is implemented." |
| OR25.a | 2026-09-25 | Owner answered "yes" — (1) an intent inventory per layer (function, module, functional integration e.g. driver + bus + config + FRAM log, system integration i.e. a generated device booting in the twin): normal behaviour from spec, datasheets, docs and owner decisions; every error path enumerated mechanically (each `raise`, `except`, error return, timeout, every defined error/warning number); every resilience and self-healing path (retries, reconnects, re-setup, supervisor restarts, OR18.a escalation). (2) Traceability: each item maps to at least one biting test (OR19.a/OR21.a sensitivity proof); an unmapped item gets a test; a test proving no item is tied to an intent or removed as redundant. (3) Line coverage second: every unexecuted line in `src/`, generated code (OR22.a) and the build chain (OR23.a) is covered or listed with a stated reason. (4) The mapping is an audit working file in `audit/` only and is deleted with it (OR11.a); no permanent traceability upkeep. |
| OR26 | 2026-09-25 | No unhandled errors or incomplete construction: "Extra carefully and deeply analyze that in none of all single function, module, functional integration, system integration layer no unhandled errors, uncaught or unhandled exceptions, missing handling, missing functionality, incomplete construction is contained. This is crucial for system stability and also documented in the specification." (Spec anchors: SPECIFICATION.md Part D.2 "No uncaught, unhandled exceptions", D.3, D.7; Part C.13 readiness gates.) |
| OR26.a | 2026-09-25 | Owner confirmed the method ("yes, that's right") — map every raising call per layer from the pinned MicroPython source and check it is handled at the right layer; special attention to task tops, Timer/IRQ callbacks, Microdot handlers and the response-writing gap (A.5), and swallowing `except`s; construction completeness (setup really runs, C.13 gates honoured, no half-built object reachable after a failed setup); OR18.a hardware faults escalating via the supervisor are intended; every handling path gets a biting test (OR25.a). And sharpened the MemoryError rule: "This is only true if the function experiencing the MemoryError is doomed to fail on memory error (restarting the task or stalling the system into a watchdog reset is the only remedy then anyway) - but if the function has a true alternative flow for graceful degradation on expectable memory errors, this indeed shall be implemented." — the criterion is whether a real graceful-degradation alternative exists, not whether the threat is "concrete, non-hypothetical". Drift under OR13: CLAUDE.md's bullet and SPECIFICATION.md Part F.2 ("only worth closing for a concrete, non-hypothetical threat") state the narrower wording; Part I.4(b) is closer. This answer is the owner's confirmation to reword both during execution. |
| OR27 | 2026-09-25 | Documentation content: "Scan the documentation for all staleness, ambiguity, prose, historic descriptions. Only facts, agreements, rules and technical explanations are desirable. Future goals are still allowable as well, but only for as little topics as possible, the outcome here should be the resolution of most of them." |
| OR27.a | 2026-09-25 | Owner answered "yes, that's right" — rules and decisions keep one short technical reason (not the story of how it was found) plus a compact provenance tag ("(owner, YYYY-MM-DD)", needed for OR13/OR14 drift tracing); measured numbers stay only where they are the evidence behind a rule or a limit; incident stories, "this used to be…" and who-found-what-when go, with anything worth keeping folded into the fact or reason; remaining future goals are resolved during the audit where possible, the rest stay as one short BACKLOG.md item each with the reason they wait. Scope: every markdown file plus header and inline comments in code and config (already under the 3-line cap). Size at recording time: ~12,000 lines across SPECIFICATION.md (6,790), `tests_hardware/README.md` (1,414), CLAUDE.md (1,067), `digital_twin/README.md` (919), BACKLOG.md (883), README.md (795). |
| OR28 | 2026-09-25 | Global errno/wrnno harmonisation: "Globally harmonize errno and wrnno numbers. They have some reserved patterns inside System Service / Base Classes. Modules logging errors and warnings never using System Service / Base Classes at all can use these numbers with the identical descriptions and the same errors or warnings. Other numbers are common sense / project wide agreement, but not all modules adhere to them. Also with the more module specific numbers, same or similar issues shall get same numbers, so there is a global consistency. When you have finished your tasks about the errno and wrnno numbers, this non-overlap and consistent scheme shall be applied to every project member." |
| OR28.a | 2026-09-25 | Owner answered "This audit IS the next substantial change. And, yes to all." — (1) The 2026-09-24 decision in SPECIFICATION.md C.7.1 ("renumbered to 10+ on its next substantial change, not in one pass") is satisfied by this audit: every module is renumbered in one pass; the dev bench's FRAM logs are read before clearing (CLAUDE.md FRAM rule) at the start of the hardware session, which reflashes the board anyway. (2) One global catalog, one meaning per number project-wide: `errno` 1-9 / `wrnno` 1-2 are the base-class meanings, reusable by modules outside the base classes only for the identical condition with the identical description; a shared band for conditions common to many modules (init, periodic read, config read/write at init and store time, callback failure, lock timeout, allocation failure, not-initialized, invalid argument, timeout, …), one number each, used by every module that has it; module-specific codes in non-overlapping per-module ranges; the same for `wrnno`. (3) A test reads every `err_s`/`wrn_s` call in `src/` and generated code and checks it against the C.7.1 catalog (wrong number, duplicate meaning, uncatalogued number fail); code-to-text mappings (website, `/status`) are updated with it. |
| OR29 | 2026-09-25 | Hardware-test knowledge base: "When preparing tests for the real hardware (which you should do along the audit), make sure you are aware of all known properties and limitations. They are documented in docs and comments allover the repo, so collect all knowledge first, cross-check with the Pico datasheets and the Micropython repo if these facts are plausible, and store it to be at hand. Design tests for real hardware in a way they can be expected to work." |
| OR29.a | 2026-09-25 | Owner answered "yes, that's right" — (1) collect every known hardware property and limit from docs, code comments, the deleted run logs/handovers in git history (the OR17.a set) and commit/PR texts; (2) cross-check each against the RP2040, Pico W, W25Q16JV and CYW43439 datasheets and the pinned MicroPython source: confirmed (with datasheet page or file:line at the pinned tag), corrected, or unverifiable (a measurement row in the hardware queue, as OR17.a); (3) stored permanently: platform facts in SPECIFICATION.md Part F, bench- and test-facing properties in `tests_hardware/README.md`, each with its source, cross-linked rather than duplicated; (4) every hardware test asserts only within these verified limits (tolerances from datasheet or measurement, wear gates, watchdog budget), names the facts it relies on, and is run once against the digital twin before entering the queue (OR21.a). |
| OR30 | 2026-09-25 | Tunable-parameter register: "In the project, there are many tunable parameters which are substantial for correct functioning, but may be subject to change - for example, runtime and timeout parameters for test suites - essential for clear test result discrimination, but prone to changes on updates. Search the project globally for such parameters, make a list and document at an appropriate place. That list needs to be updated on changing parameters or whenever such parameter is added. Then check all of these parameters you found to be in an accuracy state, looking at the current project." |
| OR30.a | 2026-09-25 | Owner answered "yes to all three" — (1) scope: every tuned (not derived) value that must be retuned as the project changes: test-suite values (CI `timeout-minutes`, 16 in `ci.yml` at recording time; per-file timeouts and retries; Unix-port `-X heapsize`; twin run and soak durations; hardware-tier budgets) and firmware/build-time values of the same kind (watchdog timeout, NTP retry/backoff, notification timing, buildgen validation thresholds); contract constants (UART wire constants, FRAM layout) are excluded. (2) A permanent SPECIFICATION.md section lists each value with location, dependants, how it was determined (measured/derived/estimated), margin, and re-check trigger; each value carries a one-line machine-read `# @tunable` tag in code (like `@web`/`@limits`); a `tests_scripts/` test fails when a tagged value is unlisted, a listed value is untagged, or the listed number differs from the code. (3) Accuracy: each value is checked against the current project (timeouts vs measured run times from CI logs and local runs with a stated margin, heap sizes vs measured peak, durations vs need); board-dependent values go to the hardware queue; stale values are corrected with the measurement behind them. |
| OR31 | 2026-09-25 | Safe watchdog feeding: "Ensure that the watchdog is fed in a safe way in the actual code: Started as early as possible, before any code which could ever get stuck, and being fed between slow calls during boot-up, outside the main loop, to enable proper booting without accidentally resetting, but still resetting if something really is hung. Inside the main loop, it must be fed at some place which will go into exception if something really goes wrong (e.g. some undocumented exception, interpreter hiccup), and which will securely block if the asyncio loop blocks or breaks, so it can never be fed if some error unrecoverable by software occurs. Follow best practice here." |
| OR31.a | 2026-09-25 | Owner answered "yes, that's right, but not 4. Many tasks have multiple timer triggers, others actually DO await until some event. This would be extremely hard to fit into a heartbeat. Rather make sure the tasks themselves are written such that they either really work or return / end in any other case which cannot be handled internally (internal handling is absolutely preferred, anyhow)" — adopted: (1) the WDT is created as the first statement of the generated boot entry, before the device-module import (at recording time it is the first line of the generated `build_system()`, `buildgen/codegen.py:381`); pre-`main.py` code stays minimal (XCUT.T25). (2) Feeds between setup units stay; every inter-feed boot step is proven well inside 8,000 ms worst case, margin recorded in the OR30 register. (3) One runtime feed site only, the supervisor's asyncio loop (`system_service.py:249`), enforced by a test; never from a Timer/IRQ callback. (5) Planted faults (twin WDT model and unit tests) prove each failure class stops the feeding: exception escaping the supervisor, `asyncio.run()` exiting, blocked loop. Not adopted: (4) per-task heartbeats. Instead, every task either really works (handling abnormal situations internally, strongly preferred) or returns/ends when it meets something it cannot handle — never stalls silently; checked task by task together with OR18/OR26. |
| OR32 | 2026-09-25 | Legacy consolidation and repo cleanup: "We should also take care that the repo gets cleaned up. Especially all legacy code, scripts and functions should remain in the repo as a reference, but be all located in one /legacy folder, containing structured subfolders. Apart from that, the repo shall only contain current and living content. Be sure to update all documentation references to the legacy repo." |
| OR32.a | 2026-09-25 | Owner answered "yes to all three, especially move the bench references into the canonical places; the legacy readme shall only contain legacy descriptions in the end" — (1) legacy = `python/`, `modules/`, `html_raw/` (used only by the legacy build), the four `build-*.sh`, and `dev_legacy/`'s old driver copies; `arduino/` is not legacy and stays at the root (post-audit C reconciliation reference). (2) `legacy/firmware/` holds the whole legacy build set with its relative layout unchanged, so the legacy build still works from there without editing any legacy file (moves only; reference-only rule intact); `legacy/dev_drivers/` holds the old dev driver copies; `legacy/README.md` describes the subfolders and contains only legacy descriptions. (3) `dev_legacy/README.md`'s current bench content (wiring, chip identities, bench state, manual `br0` recipe) moves into the canonical living places (`tests_hardware/README.md` and the docs that own each fact), not into `legacy/`. (4) Every current reference (~30 files at recording time: CLAUDE.md, SPECIFICATION.md, README.md, BACKLOG.md, `.gitignore`, `pyproject.toml`, `scripts/lint.sh`, `toolchain/setup_toolchain.py`, `buildgen/codegen.py`, tests, `tests_hardware/README.md`, device TOMLs) is updated in the same change; a check confirms no current file points at an old path; CLAUDE.md rules naming these paths (e.g. `modules/_boot.py`) get the new paths with unchanged meaning. |
| OR33 | 2026-09-25 | Re-baseline and necessity of remaining work: "Check what has changed since, update your logs, harvests and findings thoroughly to reflect that state. There were some topics added to the backlog. Check and update here as well, but for all remaining tests and items, the question if it is really still necessary should be asked, there might be some deep tests without any real benefit left from several investigations which were actually closed in the meantime, with the tests remaining as undone." and "Scan through it and make a deep and broad at a time update." — Done for planning at `4dc80ef` (V11): anchors moved, 124 harvest items tagged with what became of their source, the 16-file delta harvested, the plan's topics and seeds updated, and Appendix B lists every open BACKLOG item, owed real-hardware entry and investigation-born test or script with a necessity pre-assessment. For the consolidation run and execution (confirmed in OR33.a): each of them gets one verdict — keep (with the standing regression or contract value named), retire (investigation closed and no standing value: deleted with its references, anything worth keeping migrated first, per OR11), or owner decision; a regression guard is never retired to save effort (OR12) and an owed silicon check is retired only when a lower tier already proves the same property. |
| OR33.a | 2026-09-26 | Owner answered "yes, that's right. If the remaining tests check something relevant, keep / make them work / adopt the idea elsewhere. If it tests something which has no power / does not matter /can only fail / can never fail, try to understand the actual idea, adopt it somehow. If it remains unreasonable or unrealistic, drop." — the three verdicts stand (keep, retire, owner decision), with this order of preference: (1) a test that checks something relevant is kept, made to work if it cannot run today (e.g. the rollover test's method, an orphan script without a runner or watchdog feeding), or its idea is moved into a better place (a lower tier, an existing suite); (2) a test with no power — one that checks nothing that matters, can only fail, or can never fail — is not dropped at once: its original intent is traced (commit, BACKLOG item, investigation) and adopted in a form that bites (OR19.a/OR21.a); (3) only if the intent stays unreasonable or unrealistic after that is it dropped, with anything worth keeping migrated first and the reason recorded in the register. Appendix B's "retire" entries are candidates for this path, not decisions. |
| OR34 | 2026-09-25 | Scope of every requirement: "For sure, my requirements recorded so far will also be valid for everything incoming with this merge and update, as will be the further requirements we will continue to record once the update with the main branch is done." — OR1-OR33 and every later requirement apply to the whole tree at the planning baseline `4dc80ef`, including everything `main` brought in (the 2026-09-24/25 bench results, the new device scripts and tests, the SGP40 `W13` change, BACKLOG's "Real-hardware work still owed"), and to whatever lands before the audit baseline is fixed at go-ahead (ENV.T08); nothing is exempt because it arrived after a requirement was recorded. |
| OR35 | 2026-09-26 | Log flooding: "Check errors and warnings (errno / wrnno) for risks of flooding the logfiles with the same error allover and thereby driving other evidence out of the logs." — Interpretation in OR35.a. Starting point: each history is a ten-slot ring per logger holding codes only (no timestamps, one shared `ErrCount`, `src/print_log.py:158-178`); C.7.1's repeat rule (SPECIFICATION.md:1917-1930) is applied by six modules today (FRAM manager, UART, WIFI, NTP, NOTIFY, SGP40 `W13`), each with its own episode flag, and the SGP40 `W13` flood (`83c9920`) was found only on the bench. Related: `XCUT.T07`, `PERF.T10`, lens L-DIAG, `SENS.S28`. |
| OR35.a | 2026-09-26 | Owner answered "It should be a feature of the print log module itself and apply to all its layers of error storage - RAM or FRAM. Console logs actually should keep printing all. Thereby, the short, limited error logs are protected, while the console carries the whole unfiltered truth. Protection over reboots is not required. Protection against alternating codes and layered limits are overkill on such limited device. External faults: no, only internal. It should be integrated into the print log in a rather simple and lean way." — (1) One lean mechanism inside `print_log.py`, the same for the RAM-only and the FRAM-backed history: a code identical to the newest entry of that logger's history is counted (`ErrCount`, and the FRAM write of the count as today) but spends no new slot. (2) The console is never filtered: every `err_s`/`wrn_s` still prints in full at the configured `DebugLevel`. (3) Not in scope: surviving reboots (no persisted episode state beyond what the ring already holds), alternating codes, per-module or layered limits. (4) The six modules' own episode flags (`repeat=` in FRAM manager, UART, WIFI, NTP, NOTIFY, SGP40) are reviewed against the central rule and removed where it covers them (OR24 one material); C.7.1's repeat-rule text is rewritten to describe the central rule. (5) Superseded by OR35.b: no distinction by origin. (6) Tests: per history type, a sustained identical fault leaves the earlier entries intact and raises the count; the console output still shows every occurrence. |
| OR35.b | 2026-09-26 | Owner confirmed OR35.a (including that a recovered-then-recurring identical fault stays one slot) and corrected (5): "All correct so far, but external events stay as they are. Actually, there shall be no distinction - the simple mechanism of log filtering for the slots are applied globally via the print log functionality. No distinction between internal, external, whatever - just don't repeat the same error in the slots. Pure and simple." — Every `err_s`/`wrn_s` call keeps logging exactly as today, whatever the fault's origin (a refused client request included); the only change is the one global rule in `print_log.py`: a code identical to the newest entry of that history spends no new slot (counted, printed, written through as today). No per-origin, per-module or per-episode special cases. |
| OR36 | 2026-09-26 | Production image purity: "Strictly ensure that the production code which is built for the real hardware is lean, clean, efficient, minimal, reliable, perfectly suited for the target hardware, and contains zero artifacts specifically added for testing, neither functions, nor specific variables. Testing must adapt to fit the code, never vice versa. If you need to clean something up to adhere this rule, ensure the test still works as before, only external to the code." — Extends OR20.a's "no test-only code in business-logic files" to everything frozen into the firmware (`src/`, the generated `sensortask_<device>.py` and boot entry). Interpretation in OR36.a. Examples found while recording: `asy_isl29125_driver.py:1064-1066` (an `address` parameter that "exists only for test injection", like BMP3XX's), `asy_ntp_client.py:44-45` (`_NTP_UDP_PORT` "not const()-wrapped so tests can redirect it"), `asy_uart_link_driver.py:57` (`self.uart` public "the digital twin reaches ... through it"). |
| OR36.a | 2026-09-26 | Owner answered "1. Yes 2. That is something special. It is indeed for testing purposes, but with a dedicated hardware part behind. So it is actually used as a test, but technically understand it as a driver which is only used in dev. 3. These are functions of the hardware items wired to the API and make the driver complete as a general purpose module. The sensor station firmware just doesn't use these features. So they remain as they are." — (1) A parameter, non-`const()` value, public attribute or function that exists only so a test, the twin or a hardware script can reach inside is a test artifact and is removed; the test is rebuilt outside the code (monkeypatching from outside, fake modules, subclassing, binding the real port) with the same goal and strength (OR12). A property that becomes untestable from outside goes to the owner. (2) The UART link exerciser (`asy_uart_link_driver.py`, `dev` only) is a regular driver that only `dev` wires, with dedicated hardware behind it — not a test artifact; like every driver it is held to the same bar, so its own test seams (e.g. `self.uart` public for the twin, `:57`) still go. (3) API that completes a driver as a general-purpose module for its hardware (FRAM `verify_present()`/`set_write_protected()`/`get_size()` and the like) is not a test artifact and stays, even with zero callers in the station firmware; the line is "a function of the hardware the driver drives" (stays) versus "a hook that exists for a test" (goes). |
| OR37 | 2026-09-26 | Awkward or harmful tests, and races: "Check that there are no awkward tests (example: \"that file deliberately creates 400,000 flat sibling dirs in the shared root\") which don't really make sense or which could even damage host or target hardware (the example would be very bad for SSD drives or SD cards). Such constructs are to be avoided in a general way - not just the same class, but such strange ideas, also in completely different contexts .Especially audit for race conditions both in the actual code as well as in the tests, focused on all sandbox, real machine and Git runners. Solve them properly." — Interpretation in OR37.a. Related: CLAUDE.md's wear rule (host SSD included) and its `test_tmp_scratch.py` precedent, lenses L-WEAR/L-CONC, `TEST.T04`, `HW.T01`, `HW.T04`, the port and toolchain sharing rules in 4.4. |
| OR37.a | 2026-09-26 | Owner answered "1. yes 2. yes 3. yes, all exactly like this." — (1) Harmful or pointless constructs: every test, script and tool is checked for anything that is pointless or can wear or damage the host (SSD/SD card), the board (flash, FRAM, SCD30 NVM), the bench host's network setup or third-party services — mass files, huge loops, brute-force proofs, unbounded retries or waits, writes a test does not need, destructive host operations without a safeguard — in any context, not only the 400,000-directory class; each is turned into a structural check of its intent (OR33.a path) or dropped. (2) Races in `src/` (async interleavings), in tests (shared state) and between tiers and parallel jobs (ports, directories, toolchain) are audited for the session sandbox, real machines (owner's box, bench Pi4) and GitHub runners, and fixed at their cause. A retry or a longer timeout never counts as a race fix; the two settled mechanisms stay: `test.sh`'s per-file timeout-and-retry (hang backstop) and the three-attempt `uv sync` retry (third-party outages). (3) A race is proven by analysis plus deterministic tests that force the interleaving (scripted schedule, fake clock, barrier); a bounded repeat run (about 20 runs at most, on tmpfs) may only confirm a fix, never replace the proof. (4) Real machines: analysis plus sandbox and GitHub-runner runs; anything that needs the bench Pi4 or the board is queued for the hardware phase (CLAUDE.md go-ahead gate). |
| OR38 | 2026-09-26 | Hygiene and isolation: "Both for the actual code as well as for the test suite, check for general sanity and hygiene - ressource cleanup, filesystem cleanup, no overlaps (for example ports, filenames, etc.) in general and especially for parallel running tasks and processes, no leaking, no blocking, no contention. We had several occasions where leftovers from previous operations - other test run, other tests in the same run, across tests - where such crosstalk lead to errors or false positive alarms which were racy and extremely hard to debug. So keeping hygiene by each test itself and maybe also before starting them in a programmatic way is the rule, while still being careful not to lose any real results." — Interpretation in OR38.a. Related: OR37.a, lens L-LIFE, `TEST.T07`, `TWIN.T10`, `SCR.T12`, 4.4's port and shared-output rules, CLAUDE.md's "two suites that bind real ports" rule. |
| OR38.a | 2026-09-26 | Owner answered "1. yes 2. yes 3. yes" — (1) Every module, test, runner and tool is checked for leaked resources (sockets, timers, tasks, files, locks, temp dirs), leftovers on disk, blocking, contention and anything shared between tests or parallel processes (ports, file names, directories, state files, the toolchain). Each test cleans up after itself on every path, failure and cancellation included, never relying on a later test or run; each runner also clears its own known scratch in code before it starts. (2) Evidence is never deleted by that pre-run step: the twin's FRAM/SCD30 state, twin CI logs, coverage reports and a failed run's output move into a timestamped archive folder, keeping the last 3 runs (SSD wear); only pure scratch is deleted. (3) Ports: a test that chooses its own port asks the OS for a free one (port 0, as `tests_scripts` does); product-fixed ports (DNS 53, NTP 123, the twin's 18080, and any other fixed one) are used by one tier at a time under a lock, and a taken port fails the run at once with a message naming it, never connecting to another suite's listener. (4) Board leftovers: each device script removes its own scratch files (e.g. `config_HWTEST_*.cfg`) on exit; that removal is an allowed prerequisite flash write, not a gated one; FRAM leftovers are never wiped automatically — `errcount` is read and saved first (CLAUDE.md FRAM rule). |
| OR39 | 2026-09-26 | Test-suite speed and footprint: "Look for opportunities for speeding up the test suite and to further reduce memory / heap footpring without any functional changes of the tests themselves - just architectural efficiency gain. Never use gc.collect() in the code or as tool, only for mem measurements baseline in tests, and respect it takes time to finish if you call it." — Interpretation in OR39.a. At recording time `gc.collect()` appears in `src/system_service.py:222, 226` and in the generated boot entry (`buildgen/codegen.py:459, 466`) — the boot-confined placement reset approved 2026-09-18 (CLAUDE.md, SPECIFICATION.md I.4(f.1)) — and in 21 files under `tests/`, `digital_twin/` and `tests_hardware/`. Related: CLAUDE.md's memory-safety rule, `TEST.T03`, `MEM`, `PERF`, `SCR`. |
| OR39.a | 2026-09-26 | Owner answered "1. gc.collect is allowed IN TESTS for getting a clean baseline for memory measurement tests (but it takes time to complete, don't call and measure in the next line of code).  gc.collect is allowed IN THE CODE at exactly the place you found it: in the one-time executed boot procedure. It is disallowed inside the main loop. This is all should match the exception descriptions on the docs. 2. Whichever needs to be measured. Just don't charge the actual business logic code. 3. The setup script and the whole test suite and tiers - basically everything except the actual business logic of the board." — (1) `gc.collect()` in production code exists only in the one-time boot procedure (`system_service.py:222, 226`, the generated boot entry `codegen.py:459, 466`), never in the main loop or any runtime path; in tests only to set a clean baseline for a memory measurement, followed directly by the measurement (the collection is complete when the call returns, OR55) and never inside a timed window; CLAUDE.md's and SPECIFICATION.md I.4(f.1)'s exception text and `tests_scripts/test_gc_collect_sites.py` are checked to state and enforce exactly this. (2) Speed and footprint work may measure and reduce whatever is useful — host RAM, Unix-port heap flags, parallel processes, twin boots, redundant object graphs, CI minutes — but never charges the board's business logic: no `src/` change is made for test speed or footprint. (3) Scope: the setup script (`toolchain/`, `scripts/`), every test tier and the CI pipeline — everything except the board's business logic; every job, gate and test keeps running, nothing is weakened or skipped, no timeout is tightened without a measurement, OR37's wear rules apply, and before/after wall-clock and peak memory are recorded per tier. |
| OR40 | 2026-09-26 | GC discipline and the two threshold stages: "Generally, check that in the business logic no gc.collect() is ever used outside the exceptions we just recorded, and that the only special use of gc is to set its threshold to the agreed value exactly once for the final build. The test structure which requires all tests to pass with gc threshold set to default, as well as to the agreed value as two full passes is correct and to be applied consistently allover. The firmware must be rock solid without the threshold, and the threshold is finally applied to move it even further into the stable region, but must be tested and verified by itself." — Interpretation in OR40.a. At recording time: the only threshold call in the firmware is the generated boot entry's `gc.threshold(32768)` (`buildgen/codegen.py:704`); the unit tier runs both stages (`unit-tests`, `unit-tests-gc-threshold`), the twin tier passes `--gc-threshold` per suite run (`scripts/_digital_twin_ci_suite.py:159-161`). Related: CLAUDE.md memory-safety rule, OR39.a, `TEST.T18`, `MEM`. |
| OR40.a | 2026-09-26 | Owner chose (b): "b, that's right" — (1) Business logic: `gc.collect()` only at OR39.a's boot sites; the only other `gc` use is the one `gc.threshold(32768)` the generated boot entry sets once for the final build; both are enforced by a test over `src/` and generated code. (2) Every tier that can runs the whole suite twice — at MicroPython's default `gc.threshold(-1)` first, then at 32768 — each pass verified on its own with zero `MemoryError`/`memory allocation failed` (CLAUDE.md's four gates): unit tier and twin tier already do; `tests_scripts`/web tiers do not run MicroPython and are exempt; any MicroPython-running tier found with one stage only is completed. (3) Hardware tier: two images once, in the final hardware phase, as release proof — a `dev` image built without the threshold runs the full default flash and bench tiers first, then the normal image; the extra flash cycle is a planned prerequisite write. Between now and then the existing partial `-1` coverage (device scripts at `-1`, the serving sweep at the reactive default) continues. |
| OR41 | 2026-09-26 | Recombination and concurrency coverage at every layer: "Extra carefully check all of single function, module, functional integration, system integration layer that recombinations and parallelism and concurrency of both functionality is given and unit tests cover these cases extensively." — The combination/concurrency counterpart of OR25 (intent coverage) and OR26 (no unhandled errors), same four layers. Interpretation in OR41.a. At recording time: 13 `src/` modules spawn tasks (`create_task`), 30 of 87 `tests/` files drive concurrent tasks, the dedicated concurrency files are the bus-hazard set (`test_bus_hazard_multi_device.py`, `test_bus_hazard_generated.py`, `test_digital_twin_bus_hazard_concurrency.py`), `test_uart_comm_hazard.py` and the per-device `test_digital_twin_webserver_concurrency_<device>.py`; six device TOMLs are the system-level recombinations. Related: lens L-CONC, OR25.a, OR26.a, OR37.a (races, deterministic interleaving proof), CLAUDE.md's four-tier bus-hazard rule, `TEST`, `TWIN`, `XCUT`. |
| OR41.a | 2026-09-26 | Owner answered "1. yes 2. yes 3. yes" — (1) Recombinations: every dimension along which the firmware can be assembled differently is inventoried — the driver set per device, which drivers share a bus, optional wiring (FRAM logging, UART links), config values that enable or disable behaviour, and the six device TOMLs as the combinations that actually ship. Small dimensions are tested exhaustively; large ones pairwise (all-pairs) plus the risky higher-order combinations (e.g. shared bus + shared FRAM + REST writes); all six devices are covered at system level. (2) Concurrency: an interaction matrix of every actor that can run at the same time (sensor tasks, REST requests, config writes, FRAM logging, WiFi reconnect, NTP, DNS, UART, supervisor restarts, watchdog feeding, Timer callbacks) against every shared resource (buses, locks, FRAM, the config file, heap, sockets, error logs). Each cell is either proven independent with a written reason or tested with forced deterministic interleavings (OR37.a); this covers pairs and the realistic three-way pile-ups (e.g. a reboot or reconnect while a REST write and a sensor read are in flight). (3) Tiers, as in OR25.a: every software tier at its own layer — function and module on the Unix port, functional integration there and in the twin, system integration as generated devices booting in the twin, and the host build chain's own parallel steps in `tests_scripts`; what needs real silicon (bus timing, the CYW43 under load) is queued for the hardware phase. CLAUDE.md's four-tier bus-hazard rule is applied to every shared resource, not only I2C/SPI devices. The combination and interaction matrix is an audit working file in `audit/` only and is deleted with it (OR11.a). |
| OR42 | 2026-09-26 | Flash and SCD30 NVM wear: "Check and search deeply for any situation which could do accidental heavy or even looped writes to the tinyfs / system Flash or the SCD30 storage and cause excessive wear." — Interpretation in OR42.a. At recording time the firmware's flash write sites are `config_manager.py:375-376` (`_flush_staged()`, only after a REST write that changed a value; unchanged values are reported "Unchanged" and not written) and `:476-477` (`setup()`, only when the file is missing, invalid, carries unknown keys or needed type coercion); the SCD30 NVM-persisted commands are 0x0010 (ambient pressure / start measurement), 0x4600, 0x5306, 0x5403, altitude and 0x5204, reached only through `_set_dict_cfg()` (`asy_scd30_driver.py:257-297`), which writes every submitted field with no compare against the chip's current value; `setup()`/`reset()` send only soft reset and a firmware-version read. Related: CLAUDE.md's wear rule and `persistence_write`/`scd30_extra_write` gates, OR37.a (harmful tests), OR38.a (4) (board scratch files), lens L-WEAR, `STOR`, `SENS`, `REST`, `HW`. |
| OR42.a | 2026-09-26 | Owner answered "1. yes 2. yes, but check again - as far as I remember, the current value inside the SCD30 storage is already checked and only written if different, 3. a" — (1) Every write site to the RP2040 flash filesystem and to SCD30 NVM is enumerated — `src/`, generated code, device scripts, `tests_hardware/`, and the tooling that talks to the board — and its worst-case rate derived under every trigger: watchdog reboot loop re-running `setup()`, supervisor task restarts, retries and timers, a REST client repeating PUTs, and a config that never settles (a value whose type or form changes across a save/reload, a default that fails its own validation). Each write is bounded to "once per explicit user change" or "at most once per boot, then stable"; proven by write counters in the fake filesystem and fake SCD30 kept outside the code (OR36.a), including "written once, read back, not written again". (2) Compare-before-write for NVM-backed setters. Rechecked as asked: the owner remembers correctly for the deployed firmware — legacy `sensortask-*.py` read all six values from the chip first (`modules/sensortask-arzi.py:274-287`) and `api_helpers.set_sensor_value()` (`python/CommonDrivers/api_helpers.py:185-192`) called the setter only when `update_valid_json()` found the value changed (`:101-108`), except `AmbPres` with `force=True` (resending it is the SCD30's documented command to resume continuous measurement). The promoted `src/asy_scd30_driver.py:257-297` lost this: it writes every submitted field unconditionally, so it is a parity regression (OR13, `PAR`), and `SPECIFICATION.md:237-240` still describes the `force=True` behaviour the promoted code no longer has. The website does not cover it: its sparse PUT skips only empty inputs and unchanged enum dropdowns (`js/render.js:115-121`), so a numeric field retyped with its current value is sent. Fix: restore the legacy rule — read the chip's current values, write only what differs and answer "Unchanged" for the rest (the same result word `config_manager.py` uses), `AmbPres` always sent, `ContMeas` a command; the same rule is applied to any other setter that writes persistent memory. (3) Chose (a): no write-rate limit in the firmware. Instead the project's own clients are audited to never write on their own — the website writes only on an explicit user action and never retries or repeats a PUT; the scripts and tools likewise — and the risk of a third-party client that loops PUTs is documented. |
| OR42.b | 2026-09-26 | Owner, on the SCD30 gap: "This is a serious gap. My goal is that the functionality you found in the legacy code is restored, and architectually fitted into the existing base classes setup such that it uses the same mechanism as the standard persistence to write only if a value differs. Look extra sharp - SCD30 has exceptions from this for certain fields, e.g. the ppm calibration value, this has a different writing mechanism (only an example, check each field individually!)" — Interpretation in OR42.c. Why the schema alone does not do it: the compare lives in `ConfigManager.write_config()` against its file cache (`config_manager.py:342-347`); `SensorReaderConfig._set_dict_cfg()` reaches it through the `_set_mgr_cfg()` extension point (`base_classes.py:290-300`, "a subclass with a different persistence backend can override just this"); `SCD30_Reader` is a plain `SensorReader` (`asy_scd30_driver.py:118`) with its own `_set_dict_cfg()` that uses the schema for validation only. Per field, from the Interface Description (v1.0, May 2020, `datasheets/scd30/`): TempOffs 0x5403, NVM, readable, 0.01 °C ticks (`int(x*100)`); MeasInt 0x4600, NVM, readable; Altitude 0x5102, NVM, readable, disregarded while an ambient pressure is set; SelfCal 0x5306, NVM, readable; AmbPres 0x0010, starts continuous measurement (status in NVM), overwrites altitude compensation, 0 = compensation off, readback of 0x0010 not documented there (the driver reads it as Adafruit does); ForceCalRef 0x5204, a calibration action that permanently changes the calibration curve, while its readback is volatile ("most recently used reference", 400 ppm after every power-up); ContMeas a command: 0x0104 stop (status in NVM), not readable. Field order: `_set_dict_cfg()` applies fields in the client's JSON order; legacy applied a fixed order (TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal, ContMeas — `modules/sensortask-arzi.py:290-303`), which matters because AmbPres starts and ContMeas=false stops measurement. |
| OR42.c | 2026-09-26 | Owner answered "Perfect match" — (1) Architecture: the validate → compare with current → "Valid"/"Unchanged" → write-only-what-changed step moves out of `ConfigManager.write_config()` into one shared primitive with two stores: the config file (current = file cache, write = flash flush) and the SCD30 (current = a fresh `get_config_snapshot()` on every PUT, the chip being the truth; write = each field's own command). `SCD30_Reader` moves onto `SensorReaderConfig`'s write path through the `_get_mgr_cfg()`/`_set_mgr_cfg()` extension points with the chip as its store; its separate `_set_dict_cfg()` goes. The compare works at chip resolution (TempOffs in 0.01 °C ticks). (2) Per field: TempOffs, MeasInt, Altitude, SelfCal — written only if different; AmbPres — always sent (legacy `force=True`; resending resumes continuous measurement); ForceCalRef — always carried out, never "Unchanged" (a calibration action whose readback is volatile — this fixes the legacy bug where FRC=400 after a reboot, or a repeat calibration within one uptime, was answered "Unchanged" and silently skipped); ContMeas — stays a command (true no-op, false stops). (3) Fixed application order independent of the client, restored from legacy: TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal, ContMeas (a stop in the same PUT wins). (4) Tests with a fake SCD30 counting NVM writes per command: repeated value not written, AmbPres and ForceCalRef always written, fixed order, file-backed modules unchanged in behaviour; `SPECIFICATION.md:237-240` corrected; the hardware tier's SCD30 write budget (`persistence_write`/`scd30_extra_write`) rechecked, since re-sending the same value will no longer spend a write. |
| OR43 | 2026-09-26 | API and website wiring: "Check and correct if required: Are all relevant values of all modules wired up to the API correctly and consistently? Are all API endpoints and values wired up to the website correctly and in an appropriate way to the dedicated pages?" — Interpretation in OR43.a. At recording time: eleven REST routes (`asy_webserver_service.py:372-382` — GET `/measurements`, GET/PUT `/sensors`, `/networking`, `/system`, `/status`, `/notification`) plus the static mount; the website is driven by `# @web` tags in eight `src/` modules (sections measurements 29, sensors 34, networking 11, notification 9, system 4) that buildgen turns into a per-device `definitions.json`, except `wozi` and `dev`, which keep hand-written `html/definitions/<device>.json` checked by a golden-file test (`tests_scripts/test_buildgen_definitions.py`; retiring them is deferred work, `scripts/build_website.sh:26-28`, SPECIFICATION.md Part L.4). Related: OR13 (docs vs implementation), OR16 (broken chains), OR24 (uniform naming), OR42.c (SCD30 result words), `REST`, `WEB`, `GEN`, `PAR`, SPECIFICATION.md Part H. |
| OR43.a | 2026-09-26 | Owner answered "1. yes 2. yes 3. yes and keep in mind that it stays extensible, it may become more than six devices in the future" — (1) Module → API: every value each module holds (readings, settings, status, counters, error logs, derived values) is inventoried and placed: readings in `/measurements`, settings in their GET/PUT route, health and errors in `/status`. "Relevant" means everything the legacy API exposed plus what a user needs to operate and diagnose the device. Checked per value: wired end to end, consistent naming, units, types and ranges (ranges against the datasheets), read-only vs writable, GET returns exactly what PUT accepts. Gaps are fixed, each added value recorded with its reason; removing an exposed value is a feature change and goes to the owner. (2) API → website: every route and value appears on the right page and in the right group, with the right control (read-only, input, dropdown, toggle), units, label, description and range; nothing missing, duplicated or orphaned; per-field write feedback shown. A placement rule is written into SPECIFICATION.md Part H (Measurements = live readings, Sensors = sensor settings, Networking = Wi-Fi/NTP/identity, System = system settings, Notification = LEDs and notifications, Status = health, errors, uptime) and every page checked against it; the mock server and mock data match the real API field for field. (3) One source: the hand-written `html/definitions/wozi.json`/`dev.json` are retired, the `@web` tags become the only source, and `tests_js/` loads generated definitions. Proof: JS tests against the mock, the PUT matrix against the live twin backend, and a browser run over every page. Extensibility: nothing may assume six devices. Every check, test and build step derives the device set from `devices/*.toml` at run time (parametrised, never a hard-coded list or count), so a new device TOML is picked up with no test or script edit; any hard-coded device list or count found in code, tests, CI or docs is replaced by that derivation (docs may state the current count as a fact, not rely on it). |
| OR44 | 2026-09-26 | The general concept: "Throughout the audit, grow and develop a general concept / idea / pattern from a bird's eye perspective. Every requirement, every decision, every coding pattern can be seen as samples of a larger concept, each has a specific value, but also a general one. The general concept must be coherent and sound seen from all perspectives. The general notion is \"a device which can run indefinitely long without any user interaction once configured, handles all issues inside, and although barely reachable has multiple fallback layers, has premium quality code, has all its main cases all the way through rare corner cases tested, and runs efficiently and compact on a low end hardware device\"" — Interpretation in OR44.a. At recording time SPECIFICATION.md has no single statement of design principles; standing principles are spread over CLAUDE.md's hard rules and SPECIFICATION.md Parts A, C, D, F, I. Related: OR1 (common improvement direction), OR2.c (decisions on the owner's behalf), OR3 (apparent contradictions), OR6 (sync points), OR9 (final re-verification). |
| OR44.a | 2026-09-26 | Owner answered "1. yes and extend if you find something - the pillars are only pillars, they may still have gaps you are invited to fill 2. yes 3. yes, and we will integrate a crystal clear pattern and checklist into the specification which, if applied thorougly to anything added lateron, will produce 100% fitting code on the first try." — (1) Pillars as a starting frame, not a closed list: P1 unattended indefinitely (nothing drifts or saturates over months or years — counter wrap, clock/NTP, heap fragmentation, log flooding, flash/NVM wear, no step needing a person); P2 handles everything inside (every error caught at the right layer, recovered locally, nothing left hanging); P3 layered fallbacks for a barely reachable device (degrade → retry → re-setup → task restart → reboot → watchdog, hotspot fallback, reboot-surviving FRAM evidence); P4 premium code (lean, consistent, one shape per job, no test artifacts in the product, current-state docs); P5 tested from main to rare corner cases (biting tests at every layer, combination and interleaving, both GC stages); P6 efficient and compact on low-end hardware (heap, frozen size, CPU and loop latency, never starving the watchdog). Checked from every perspective: runtime, code, tests, build chain and CI, docs, website and API, real-hardware operation. Gaps found in the frame are filled with new pillars or principles, each with its reasoning. (2) The concept grows in an `audit/` working file: each principle lists its samples (OR requirements, owner decisions, CLAUDE.md rules, coding patterns, findings); an unexplained sample yields a new principle; a clash is an OR3 fine-tune question at consolidation or an OR2.c decision during execution; the concept is the first criterion for unforeseen decisions; coherence is reviewed at every OR6 sync point and in OR9's final re-verification. (3) Before audit close it is distilled into a permanent "Design principles" Part near the front of SPECIFICATION.md — current state only, pointing to the rules and Parts that carry each principle out — with pointers from CLAUDE.md and README.md, and CLAUDE.md's bird's-eye scan for new `src/` files checks against it. It carries a crystal-clear pattern and checklist which, applied thoroughly to anything added later (a driver, a service, a route, a test, a build step, a device), produces fully fitting code on the first try: it unifies and supersedes overlapping checklists (Part C, D, G, OR10's new-module procedure) into one ordered path rather than adding a parallel one, and is proven during the audit by walking one real addition through it end to end and fixing every step that did not lead straight to fitting code. |
| OR45 | 2026-09-26 | Test levels build on each other: "We already have a concept of setup script tests, unit tests, digital twin tests, real hardware \"flash\" tier and \"bench\" tier. * Make sure these concepts are complete and cover the whole codebase, no gaps * These concepts are building upon each other * Unit, twin and tiers are intended to be subsets. Unit runs everywhere. Twin runs in the sandbox, flash runs with the board connected. Bench requires the host system on top. The concept is mentioned at several places; any higher level or tier requires to contain the sub levels, so I can trust that for example the flash runs contain all the twin runs, only adapted to real hardware, and that the bench tier contains all of the flash tier and only adds up onto it" — Interpretation in OR45.a. At recording time: the environment tiers are strict supersets (`generic` ⊂ `flash` ⊂ `bench`, `toolchain/setup_toolchain.py:1064-1066`, README.md:65-67); SPECIFICATION.md E.6.1 defines five backends (mock, twin, flash, bench, manual) and states `bench` ⊇ `flash`, which `scripts/run_bench_hardware_suite.sh:11` honours by running `tests_hardware/flash` + `tests_hardware/bench`; but flash ⊇ twin does not hold today — the flash tier is 11 files of its own, `run_flash_hardware_suite.sh` runs neither the unit nor the twin tier, and E.6.2's shared behaviour catalog deliberately leaves the twin's persistence/IRQ/random-walk behaviour out; in CI `digital-twin-e2e` needs `unit-tests` (the only built-in chaining). The concept is described in SPECIFICATION.md E.6, README.md, `tests_hardware/README.md` and CLAUDE.md, under two vocabularies (backends mock/twin/flash/bench vs. environment tiers generic/flash/bench). Related: OR20.a (driver/DUT separation), OR25.a/OR41.a (coverage at every layer), OR40.a (two GC stages per tier), CLAUDE.md's four-tier bus-hazard rule, `TEST`, `TWIN`, `HW`, `SCR`, `CI`. |
| OR45.a | 2026-09-26 | Owner answered "1. yes 2. yes 3. yes 4. yes - and it should mostly be the case like this already, at least that is what I would expect" — (1) One ladder, one definition: L0 host (setup/build-chain tests `tests_scripts`, website tests; runs everywhere), L1 unit (Unix port with fakes; runs everywhere), L2 twin (generic environment; sandbox and CI), L3 flash (L2 + board on USB), L4 bench (L3 + the host's WiFi bridge). SPECIFICATION.md E.6 is the one authoritative definition with one set of names; README.md, `tests_hardware/README.md` and CLAUDE.md point to it instead of restating it. (2) "Contains" means both: (a) execution — each tier's runner first runs every lower level, both GC stages, on the same commit, and stops before touching hardware if one fails; a clean flash/bench verdict names every level it includes; a skip-lower-levels flag exists only for iterative debugging and a run using it can never be reported clean; (b) scenarios — every twin scenario has a real-hardware counterpart, adapted. (3) Flash has no network, so network scenarios land in bench: bench ⊇ flash, and flash ∪ bench ⊇ twin. A twin scenario that relies on a software-only fault (FRAM bit flips, an I2C NAK at an exact byte, accelerated clocks) first gets a real-hardware equivalent searched for (a real fault from the bench, a real wait, a `dev`-only hardware provision); only if none exists is it a listed exception with its reason, reviewed at audit close. Wear rules apply unchanged (owned write gated, prerequisite write not). (4) "No gaps" is shown by a matrix mapping every file in the codebase (`src/`, generated code, `buildgen/`, `toolchain/`, `scripts/`, `digital_twin/`, `js/`, CI) to the levels that test it; each level's scope written down; every gap filled at the lowest level that can prove it; containment itself enforced by a test (every twin scenario has a flash/bench counterpart or a listed exception); no device-count assumption (OR43.a). The matrix is an `audit/` working file, deleted at close (OR11.a). On the owner's expectation that this mostly holds already: bench ⊇ flash does (`run_bench_hardware_suite.sh:11`); two points found at recording do not and are verified first in execution rather than assumed — the flash and bench runners run neither L1 nor L2, and E.6.2 leaves twin persistence/IRQ/random-walk behaviour out of the shared catalog, so scenario containment of the twin (31 `tests/test_digital_twin_*.py` files vs. 11 flash and 12 bench files) is unmeasured; the result is reported, not silently patched. |
| OR46 | 2026-09-26 | Everything, at every level, and leftovers: "When you audit the codebase, check EVERYTHING file by file, import by import, integration layer by integration layer up to full integrated board configs. So it is ensured on the micro, intermediate and macro level that everything is sane and sound. Thereby, also look out for staleness, code and doc leftovers, many changes were done over many iterations, unused code, overly complex functions." — Interpretation in OR46.a. At recording time: 1,103 tracked files, 474 outside the reference-only or excluded trees (`python/`, `modules/`, `arduino/`, `ext/`, `datasheets/`, `audit/`); no dead-code detector in the lint chain; ruff's complexity ceilings sit at the measured maximum and ratchet down only (`pyproject.toml:201-212`: max-complexity 20, max-branches 20, max-statements 80, max-returns 12, max-args 24). Related: OR5 (no leftovers), OR11 (stray files), OR13/OR27 (doc staleness), OR24 (uniform naming), OR25.a (line coverage), OR32 (repo cleanup), OR36.a (3) (general-purpose driver API stays), OR44 (the concept), CLAUDE.md's "current state, not history" rule. |
| OR46.a | 2026-09-26 | Owner answered "1. yes 2. a 3. yes. And: I for example found that the linter limit for fucntional arguments was risen again and again, especially the webserver wrapper collecting something around 24 arguments. That's not good style, think of something better and lower the linter limit again." — (1) Four provable levels: micro (every in-scope file read in full, no sampling; each function checked for correctness, complexity, naming, error handling, dead parts, stale comments); imports (per device build: every import resolves in the frozen image, no unused imports, no cycles, no test-only imports, late imports justified, heap cost at boot); intermediate (each integration seam as a unit, both sides agreeing on the contract: driver + bus + config + FRAM log, service + webserver, buildgen + generated module, API + website); macro (every generated device from `devices/*.toml` as a whole system: boot order, task graph, shared resources, memory budget, routes, website). A ledger in `audit/` records what was checked. (2) Chose (a): a dead-code tool is used during the audit only, never added to `scripts/lint.sh`; its output plus a repo-wide reference search (generated code included — buildgen resolves drivers and `@web` fields by name) is a candidate list confirmed by hand; confirmed leftovers (functions, constants, parameters, unreachable branches, config keys, never-raised errno/wrnno, JS functions, CSS rules, test helpers and fixtures, scripts, CI steps, docs describing removed things or history) are removed, except general-purpose driver API (OR36.a (3)). (3) Every function near a ruff ceiling is reviewed and simplified where it reads better (split by job, table-driven, a Part G shared primitive), tests first, no behaviour change (OR12), weighing each split's RAM and frozen-size cost on the board (P6); each ceiling is then lowered to the new measured maximum. (4) Argument counts: `max-args = 24` exists for `WebserverService.__init__` (`asy_webserver_service.py:295`), followed by `asy_uart_driver.py:42` (16) and eight `src/` signatures at 12; 34 `src/` functions take more than 5. The 24-parameter wrapper is redesigned and `max-args` lowered; design and target in OR46.b. |
| OR46.b | 2026-09-26 | Owner answered "yes, all three, 8 is fine, and apply coherently over the whole system, adopt the solutions at any place they improve code tidyness" — (1) `WebserverService.__init__`'s 24 flat parameters become three small fixed config objects — serving limits (`max_content_length`, `chunk_bytes`, `max_connections`, `backlog`, both timeouts, `host`, `port`), static website (`static_mount`, `static_index`, `is_hotspot_active`), route data sources (`sensors`, `settings`, `build_info`, `system_cmd`, the two notification callbacks, `status_sources`, `maintenance_sensors`, `error_sources`) — built by generated code in one place and passed in, so construction stays complete in one step (OR26.a); no post-construction registration methods (a half-configured object). (2) One small logging config object replaces `fram`/`history_length`/`debug` in every service and driver (about 16 `src/` modules, all passed straight to `make_logger()`), applied to all at once. (3) `max-args = 8`, then lowered to the new measured maximum after cleanup; every remaining signature above 8 is reviewed; a signature that mirrors an external API (e.g. `machine.UART`'s own parameters in `asy_uart_driver.py` and the test fakes) gets a central, reasoned per-file exemption in `pyproject.toml`, never a raised global limit. Scope: applied coherently across the whole system — `src/`, generated code, `buildgen/`, `digital_twin/`, tests, tooling — and the same grouping patterns are adopted wherever they make code tidier, not only where a limit forces it (SPECIFICATION.md D.10 "one shape for one job"); the patterns join Part G's shared-primitive catalog and the OR44.a checklist. Every change keeps behaviour (OR12), weighs heap and frozen-size cost (P6), and keeps OR36.a (no test artifacts in the product). |
| OR47 | 2026-09-26 | Boot queueing, FRAM allocation order and timer stagger: "Ensure that the startup procedures in the system service do queue correctly, ensure a guaranteed fixed order for the FRAM chunk allocations, give the FRAM allocations enough time, and that the sensor timer starters will be started in a way that prevents race conditions / timers firing at the same time over any harmonics of the multiple of 1s sensor read interval steps (look into the docs and code for details)." — Interpretation in OR47.a. At recording time: FRAM chunks are allocated synchronously at construction (`print_log.py:238` → `AsyFramManager.get_chunk()`), so their order is the generated construction order; chunk setup I/O (`pr.setup()`) runs in the sequential boot `setup()` batch for most modules but lazily inside tasks for some (`webserver`'s `_run()`, SPECIFICATION.md A.7; `SCD30_Reader._init_scd()` inside `read_loop`, `asy_scd30_driver.py:161-164`), i.e. inside the task-start window; tasks start via `asyncio.sleep(1/N)` with a `gc.collect()` after each (`system_service.py:216-227`); read-trigger timers start via a chain of one-shots `1000/(N+1)` ms apart (`system_service.py:148-175`), each armed from inside the previous soft callback. SPECIFICATION.md C.9.1 proves no coincidence for 1000 ms-based periods, but two points are open against it: (a) arming each one-shot from the previous callback adds that callback's dispatch latency to every later offset, so offsets are k·d plus accumulated jitter, and C.9.1 asks only that they be distinct, not that they keep a margin; (b) the 1000 ms periodic timers outside the sequencer (`system_service.py:204` uptime, `asy_wifi_service.py:662`, `asy_ntp_client.py:343`) start at arbitrary phases. The FRAM datasheets carry only a permissions encryption with an empty user password: they open freely and extract with `pypdf` plus `cryptography` (corrected 2026-09-26); MB85RS64V (wozi) needs CS held for tpu ≥ 0.6 ms after power-on at 3.3 V (p.18), MB85RS2MTA's (dev) power-on values sit in a table without a text layer. Related: OR26.a (construction completeness), OR31 (watchdog feeding), OR35 (log flooding), OR37.a (races, deterministic interleaving proof), OR39.a/OR40.a (boot `gc.collect()` sites), OR41.a (interaction matrix), CLAUDE.md FRAM and boot-latency rules, SPECIFICATION.md A.7, C.9, C.9.1, I.4(f.1), `CORE`, `STOR`, `SENS`, `PERF`. |
| OR47.a | 2026-09-26 | Owner answered "1. yes 2. fingerprinting on the fram is a waste of space. there is no requirement for the fram to stay consistent through firmware re-flashes. it only must be rock solid within one individual firmware build. 3. I don't know about a 500ms tick in scd30. if this is the missing interrupt recovery timer, it would be okay to set it to 1000ms as well, as all the others. and it's always only about sensors with bus access. 4. yes" — (1) Boot phases run strictly one after another — construction, the `setup()` batch, task starts, timer starts — each fully complete before the next, nothing fired off unawaited, order generated by buildgen and fixed; proven for every generated device by recording the real boot sequence in the twin and asserting it, and once on the bench with a timestamped boot log. (2) No FRAM layout fingerprint: FRAM content need not survive a reflash. Within one firmware build the allocation order must be fixed and deterministic — it is today (synchronous `get_chunk()` at construction, in generated construction order), which is asserted by a test per generated device and stated in SPECIFICATION.md A.7. Robustness still covers the first boot after a reflash as a within-build case: a chunk holding another build's bytes is handled gracefully (CRC mismatch → treated as empty and re-initialised, no crash, no error flood — OR35). "Enough time": every chunk setup (`pr.setup()`) moves into the one-time boot `setup()` batch, awaited in the fixed order with the watchdog fed in between (no lazy setup inside tasks — `webserver`'s `_run()`, `SCD30_Reader._init_scd()`), and the FRAM chip's power-up and access timing from its datasheet is respected before the first access. (3) The SCD30's 500 ms tick stays as it is: shorter than the shortest sensor interval, started with the timer starters like all timers. The stagger plan covers only timers that trigger bus access (sensor reads); the uptime, WiFi and NTP 1 s timers stay out of it. Gap (a) stays in scope: every start is scheduled against one shared starting point (target = t0 + k·slot) so callback latency cannot accumulate, and the guarantee is a minimum separation of one measured worst-case read duration, not mere distinctness; sensors sharing a bus are placed as far apart as possible. Proof: fake-clock tests of the real sequencer for every generated device, an exhaustive check over all period combinations in the allowed ranges, and bench timestamps of real trigger moments over a long run; SPECIFICATION.md C.9.1 corrected. (4) The task-start stagger (`asyncio.sleep(1/N)`) stays a coarse spread with no coincidence claim; checked for correct ordering and for the OR39.a/OR40.a boot `gc.collect()` rules. |
| OR48 | 2026-09-26 | Unexplained legacy divergences as hints: "Functional discrepancies from the legacy code without an obvious reason or recorded decision must be investigated, as they may be hints to something lost. Most prominent recent example: the only write on changes function for SCD30. But this is just an example, treat this requirement as a concept!" — Interpretation in OR48.a. At recording: the plan already carried the SCD30 case, but only as a harvested seed (`PAR.S02`); the parity topics look at the REST surface, the web UI, timing constants and published values (`PAR.T01`, `T04`, `T10`, `T12`), so a divergence that is invisible at the API — a write that is skipped, a command order, a delay, a retry, a readback check — has no systematic owner. Sources for "recorded decision": SPECIFICATION.md, CLAUDE.md, BACKLOG.md, code comments and the refactor's commit history (full, not shallow: 1636 commits, so `PAR.T15`'s "this checkout is shallow" is stale). Legacy's own history is not in the repo — it arrives in one import (`8c4a73d`, 2026-07-13) — so legacy's reasons can only come from its code and comments, the datasheets and the owner's memory. The legacy tree at HEAD is not purely the imported state: `2bda920` edited `python/IndividualDrivers/asy_bmp3xx_driver.py` and `modules/sensortask-wozi.py` (IIR coefficients), so which state is the comparison baseline matters (with `PAR.T15`). Related: OR12.a (regression vs defect, flag-before-change), OR42.b/OR42.c (the SCD30 instance, restored within the base classes), OR44.a (concept and checklist), OR46.a (file-by-file ledger), `PAR` area, CLAUDE.md "verify against the legacy driver's own actually-proven field behavior". |
| OR48.a | 2026-09-26 | Owner answered "1. Not in such detail. It's really about functional losses which were forgotten along the way. 2. Explained: adapted to our promoted scheme without functional losses, recorded decisions I took (not the session agent). If you find a suspicious place, ask me. 3. Scan along with the audit, make sure everything is found, but no list or permanent record. 4. The baseline should not matter much as the legacy was maybe moved around but not changed" — (1) Target: functions of the legacy code that got lost on the way into `src/`, not a line-by-line behavioural diff. (2) A divergence is explained only if it is an adaptation to the promoted scheme with no functional loss, or a decision the owner took and that is recorded; a decision a session agent took alone does not count. Every suspicious place goes to the owner as a question. (3) Done as part of the file-by-file pass (OR46.a), complete across all legacy code, with no separate list and no permanent record; only the owner questions and the resulting fixes remain. (4) Legacy HEAD is the baseline. |
| OR49 | 2026-09-26 | Load-limit coverage: "We already have several tests in place which drives the board / the system as a whole close to, or even above its load limits. This is restricted to software load of course, never hardware, never even potentially destructive, and never wearing any components. The goal of these tests is to ensure the behaviour is graceful and reversible degradation of functions, but never crashes, undefined or uncontrollable behaviour. Scan through the functions, check the specs and datasheets, search for gaps and yet partially or completely uncovered areas, create additional tests for them, and show and explain them to me at the very end of the session." — Interpretation in OR49.a. At recording, the existing load tests: twin — per-device real-socket webserver concurrency (`tests/_webserver_concurrency_scenarios.py`, `test_digital_twin_webserver_concurrency_<device>.py`) and bus-hazard concurrency; flash — heap headroom after a full build and single-core timing headroom under normal task load (`tests_hardware/flash/test_memory_stress.py`), direct-driver bus concurrency; bench — HTTP hammer and soak with MemoryError/reboot watch and FRAM diagnostics kept (`test_memory_stress_bench.py`), `GET /sensors` multi-client load combined with network degradation, NTP outage, WiFi flapping and config writes (`test_bus_concurrency_under_api_load.py`), UART link under API load (`test_uart_link_under_api_load.py`). Related: OR35 (log flooding), OR37.a (races), OR41.a (interaction matrix), OR42.a (wear), OR45.a (tier containment), CLAUDE.md memory-safety discipline and wear rule, SPECIFICATION.md F.1-F.3, I. |
| OR49.a | 2026-09-26 | Owner answered "All of that exactly. FRAM writes do not count as wear." — (1) Load goes onto every finite shared software resource: heap, sockets/connections, asyncio tasks, the 8-deep soft-IRQ scheduler queue and its drop behaviour (SPECIFICATION.md F.1), the timer alarm pool, bus locks, error-log slots, UART buffers, CPU time against the watchdog; on the input side request rates, DNS queries, malformed, partial and oversized requests. Each at every tier where the load is real (OR45.a). Pass means: graceful degradation; full return to baseline once the load stops, checked explicitly; no crash, reboot, WDT reset or MemoryError marker (CLAUDE.md gates); no log flood (OR35). A failure is a defect handled per OR12.a. (2) Load never writes a limited-endurance store: reads, rejected writes and unchanged writes only, the last only once write counters prove OR42.c's compare-before-write skips the write. No SCD30 NVM, no flash cycles, nothing that risks the permanent WLAN deactivation, no host disk churn (CLAUDE.md wear rule). FRAM writes are not wear. (3) At the end of the execution session: one entry per new test — the gap it closes, the load it applies, where the limit sits, how the system degrades there, and that it recovers — in the closing chat report and the PR description. |
| OR50 | 2026-09-26 | Staleness in non-code files: "When scanning for staleness, this also includes any non-code files like configuration file, test fixtures, setup scripts, installed packages, downloaded files, etc. There may be values or settings or sections included which affect targets which are gone or have changed along the development progress. Clean this up." — Interpretation in OR50.a. Two examples at recording: `.gitignore:75` explains its twin-state entries by `digital_twin/run_wozi_integration.py`, which is retired (the entries themselves may still be live via `run_generic_integration.py`); `pyproject.toml:59` justifies a RUF003 exception by `html/definitions/*.json`, which OR43.a retires. Related: OR32 (legacy consolidation), OR36 (image purity), OR38 (hygiene), OR46.a (staleness and leftovers, file by file), CLAUDE.md build-environment rule (BACKLOG chroot list). |
| OR50.a | 2026-09-26 | Owner answered "Yes to all" — (1) Scope: every non-code file in the repo (`pyproject.toml`, `uv.lock`, `package.json`/lock, `.nvmrc`, `eslint.config.js`, `tsconfig.json`, the `.ini` files, `toolchain/versions.toml` and its apt list, `ci.yml` and the composite action, `zizmor.yml`, `.gitignore`, `.gitattributes`, `devices/*.toml`, test fixtures and golden files, twin state defaults, bench configs) plus everything the setup installs or downloads (dev-group tools, npm packages, MicroPython stubs, Playwright browser, toolchain downloads). Rule: every entry has a live consumer and a current reason, otherwise it is removed or corrected — suppressions and excludes that no longer fire, ignore lines for paths nothing writes, CI steps or caches for gone paths, unused fixtures, dependencies nothing imports or calls, and comments that justify a setting by something gone. (2) Method: machine-checked where possible (every path a config names resolves; every suppression and exclude removed on trial and the check re-run; every dependency traced to a user). Build-environment changes get a BACKLOG chroot-list entry (CLAUDE.md). A setting whose only consumer is outside the repo goes to the owner. (3) Outside the repo: (a) the installer removes its own outdated leftovers in the toolchain directory (old MicroPython builds, old stub versions), proven by a test; (b) the bench Pi is checked for packages the current setup no longer installs in the hardware phase, with the owner's go-ahead. |
| OR51 | 2026-09-26 | Pre-merge quality gate, as the project standard: the owner showed two sets of the instructions used to prepare every session for merging (set 1: four, set 2: eight), then said "The examples contain general project style and quality requirements, so they should be treated as one essential part of the big picture - and of course live on in the project docs, but depending on which scope, a significant portion will land in the specifications". The sets cover: correctness and robustness per file (no oversights, bugs, strange behavior, unhandled/unplanned/accidental exceptions or conditions without a unit test; resilience, self-healing, full upstream and downstream handling, compliance); the specification walked paragraph by paragraph and re-checked against datasheets, MicroPython sources and docs and the sources found on the way; "full production / final release quality code allover"; temporary files (communication files, temp storage, session-limited items, session-only test code) persisted to the canonical single source of truth, crosslinked, stale-checked, then removed completely; closure of every opened issue, solved first by reasoning, project standards, similar project solutions, project rules and research (repos, forums, docs); the design questions (structure good, understandable, lean; setup reasonable, resilient, reliable; inheritance correct and complete; integration coherent as for other project code; module specialties; simplification "especially as much code was accumulated"; anything missing; purpose fully met); unit tests for intended behavior, all error paths with handling checked, maximum coverage "including biting tests", and regression; documentation (no knowledge, experience or agreements lost "also compared to the current state of the main branch", concise, no prose, unambiguous, no duplicates, single point of truth, no staleness, correct and complete current state, placed, cited and crosslinked correctly; comments one concise header block and at most 3 lines inline); a sweep for agreed-but-deferred items whose time has come; and owner questions as "a short numbered list with top level decisions - max 10 words for description. Then decision options and consequences", which the owner stressed ("many questions are asked way too verbose to read and understand"). Related: OR11, OR13, OR14, OR22, OR25, OR46. |
| OR51.a | 2026-09-26 | Recorded as one row per the owner's statement in OR51 — (1) The audit applies the whole gate to the whole tree; where the two sets differ, the stronger wording applies (final release quality everywhere; every touched file and every in-scope file). (2) Additions over the related rows: spec-first walk (every paragraph traced to the code that honors it); primary-source recheck of every hardware and runtime claim; temp classification by purpose (not serving the whole project), including session-only test code; closure of every opened issue (BACKLOG, TODOs, plan findings); biting tests proven to fail against broken code; doc loss check against main as at audit start, before any compression; deferral sweep (trigger met, work not done). (3) Owner questions only after self-resolution, in the owner's format, from now on. (4) Persisted by scope, single source of truth: the quality bar and test standard in SPECIFICATION.md (Part D, D.12 and Part E); session practice (close-out cleanup, closure, deferral sweep, question format) in CLAUDE.md's working agreements, citing the specification rather than repeating it. |
| OR52 | 2026-09-26 | Answers to consolidation pass 1 (`audit/CONSOLIDATION.md`): "1. a 2. a 3. a 4. a 5. a primarily, and b only in case of unexpected ones 6. retire if it's no longer needed but document how it was done in case we need it again 7. it's an open source repo (MIT license) 8. a" — to: (1) keep settings when legacy units are reflashed; (2) keep stored settings across later firmware updates; (3) network attackers the firmware must resist; (4) `main` during the audit; (5) when the question-raising scans run; (6) the twin's `gc.collect()` heap-unlock helper; (7) public distribution; (8) phase order, foundations first. |
| OR52.a | 2026-09-26 | Integrated — (1) No legacy config migration: legacy units get fresh setup after reflash, covered by a reflash runbook (`PAR.T06`/`T07`: hotspot permanent-deactivation hazard, littlefs residue `PAR.T08`, hostname/DHCP, SCD30 NVM survival). Config keys and file names may be renamed during the audit. (2) From the release on, persisted config keys and file names are a public interface (added to OR24.a (2)): a change needs a migration; a golden stored-config fixture from the release, loaded by a test, fails on an unmigrated change (today a renamed key silently falls back to its default, `config_manager.py:446-462`). (3) Threat model: trusted home LAN. Unauthenticated REST writes and `bootloader` are accepted properties, documented as known limitations; `SEC` keeps robustness against malformed or oversized input (a crash from bad input stays a defect, OR49.a); radio-range attacks are out. (4) `main` is frozen during the audit: no other session pushes to it; the audit baseline is its head at go-ahead; no delta passes; one final merge. (5) The question-raising scans run in consolidation passes 2+: rule and decision drift (OR13/OR14), legacy losses (OR48, moved from the file-by-file pass), defect candidates among the seeds (OR12.a), necessity verdicts (OR33), open items (OR5); only unexpected questions arise during execution and are parked (OR2.c). (6) `digital_twin/unix_port_gc_unwedge.py`, its test and its two call sites are retired once a test proves the `unix_kbd_intr` override is applied to every Unix-port build; SPECIFICATION.md F.6 keeps the mechanism and the recovery (`gc.collect()`, not `heap_unlock()`) so it can be restored. (7) Public MIT repo: `LIC.T06` (third-party notices for any published UF2) and `LIC.T07` (redistribution terms of every PDF in `datasheets/`) are in scope; a PDF that may not be redistributed is a consolidation question. (8) Phase order as in `audit/CONSOLIDATION.md` section 2. |
| OR53 | 2026-09-26 | GPIO table and Sensirion notes: "1. a 2. voc pdf files: attached here." — (1) `GEN.T07`: `buildgen/pico_gpio.py` accepts every pin function the RP2040 offers (datasheet Table 279), not only the Pico W pinout figure's labels; wireless-reserved GPIOs stay excluded; its wrong comments are corrected, with a test per newly legal pin. (2) Added to `datasheets/sgp40/`: `Info_Note_VOC_Index.pdf`, `Info_Note_Integration_VOC_NOx_Sensor.pdf`, `GAS_AN_SGP4x_BuildingStandards_D1_1.pdf`; their redistribution terms are checked with the rest under `LIC.T07` (public MIT repo, OR52.a (7)). |
| OR54 | 2026-09-26 | Two harvest-pass-1 findings: "\"the website tiers are still fixed to wozi and dev rather than derived from devices/*.toml.\" - a real gap that needs to be fixed. \"Against your garbage-collection rule: the twin's memory sampler calls gc.collect() itself.\" - that might be an issue, but also might be an allowed exception, if it is done to obtain a defined baseline for memory measurements." |
| OR54.a | 2026-09-26 | Integrated — (1) Every website tier (device list, site build, mock and live backends, cross-browser runs) derives its device set from `devices/*.toml`; no tier names a device (OR43.a; `audit/hreq/G7.md` G7.055/G7.056); a B1 foundation change (one-source website definitions). (2) The twin's `_mem_sampler()` (`digital_twin/run_generic_integration.py:288-295`) is the OR39.a (1) measurement-baseline exception: it runs only in the Run 11 soak (`--mem-sample-interval-ms`, `scripts/_digital_twin_ci_suite.py:1119`), and its `gc.collect()` exists to read the live set. It stays as the twin's one exception; B3 checks that its 25 ms collection does not decide Run 11's verdict (a sparser interval must agree) and that no other twin run collects. The exception is stated in SPECIFICATION.md I.4(e) and enforced by `tests_scripts/test_gc_collect_sites.py` extended to `digital_twin/`. `segfault_stress_repro.py:92` (a collect with no measurement) is a tool use and goes. |
| OR55 | 2026-09-26 | On the harvest finding that `gc.collect()` completes before it returns: "interesting, if that holds a real verification, my assumption that it needs time was wrong and you can replace it with the facts you found." |
| OR55.a | 2026-09-26 | Verified at `v1.29.0` — `gc.collect()` is synchronous and complete on return: `py/modgc.c:33-41` calls `gc_collect()`; the rp2 and Unix ports (`ports/rp2/main.c:314-321`, `ports/unix/gccollect.c:36-43`) run mark (`gc_collect_start`, register and stack roots, other threads' roots), then `gc_collect_end()` (`py/gc.c:604-620`: finalisers, freeing every unmarked block, clearing the collect flag) inside the call; nothing is deferred, and `gc.mem_free()` (`py/modgc.c:64-73`) reads the allocation table as that sweep left it. Rule replacing OR39.a (1)'s "don't measure in the next line": a test may read the heap in the statement after `gc.collect()`; because a collection costs time proportional to the heap, it never sits inside a timed window or a watchdog-sensitive stretch. |
| OR56 | 2026-09-26 | Three harvest-pass-1 findings: (1) "\"each UART fault writes an error entry and a warning entry into one shared log\" - that's already conceptually wrong. Either it's a fault or a warning, but never both at a time. That is common sense and should be globally checked and applied." (2) "Public DNS fallback: If that was just an added default value for the config it's okay" (3) "The FRAM layout text still says it \"must stay identical across firmware versions\" - genuine drift, I never required that, I even objected several times against it!" |
| OR56.a | 2026-09-26 | Integrated — (1) One event, one persisted entry: a single occurrence is logged either as an error or as a warning, never both, and never as two entries of the same kind; checked for every `err_s`/`wrn_s` pair in `src/` and the generated code. Known cases: UART's fault `errno` plus resync `wrnno` (`asy_uart_comm.py`, SPEC C.7.1 UART row), and a failed sensor read logging the driver's `errno` 11 and `_error_check()`'s streak `errno` 1 (`base_classes.py:223`); the streak and give-up stay visible as counters and as their own later event (the give-up `errno` 2). With this, OR35.b's newest-entry rule needs no exception. (2) `_FALLBACK_DNS_SERVERS` (`asy_dns_client.py:20`, hard-coded, appended after the DHCP server on every lookup, agent-added `a6abe13`) becomes a config value with today's servers as its default: a website-visible, user-changeable networking setting that can be emptied; no hard-coded server remains. (3) The FRAM layout is fixed only within one firmware build (OR47.a (2)); SPECIFICATION.md:216-217 and :379 and `tests/test_asy_fram_manager.py:90` (session-agent text: first written in `69d85b7`, 2026-07-18, promoting the FRAM manager; carried on by `7356bc8` and `e5f31f2`; never owner-attributed) are corrected, and no test, doc or comment may claim or enforce cross-version stability. |
| OR57 | 2026-09-26 | On the finding that legacy's SCD30 compare-before-write never matched (trailing commas in `modules/sensortask-*.py:317-321`): "it does not weaken the basis. The basis was intended as I described and your finding was a bug in that code, not a contradiction." |
| OR57.a | 2026-09-26 | Integrated — OR42.a/OR42.c stand on their stated basis: legacy intended to write SCD30 NVM only on change, and the trailing-comma readbacks are a legacy bug that defeated that intent. General rule for every legacy comparison (OR48): parity is with legacy's evident intent; where legacy code contradicts its own intent through a bug, the intent is the requirement and the bug is recorded as a legacy defect, never as a field behaviour to keep or as a contradiction of an owner row (`audit/hreq/G9.md` conflict 2 is read this way). |
| OR58 | 2026-09-26 | Legacy REST paths: "none of them needs to stay. The reference for us is the new API. There is no backward compatibility issue." |
| OR58.a | 2026-09-26 | Integrated — overtakes OR24.a (2)'s "legacy REST paths that external clients may use stay" and harmonization 22. The refactor's API (`/measurements`, `/sensors`, `/networking`, `/system`, `/status`, `/notification`, `asy_webserver_service.py:372-382`) is the only reference; none of the 14 legacy paths (`modules/sensortask-wozi.py:146-397`) is restored, and SPECIFICATION.md C.5.3's live `/net/cmd`/`/led/cmd` text is corrected. With no backward-compatibility constraint, key names inside the new API follow one scheme before the release (OR24, OR52.a (1)); legacy-derived spellings (`NTP_Host`, `TempOffs`, `lightCmdLED`, the `SGP`/`ISL` prefixes, `audit/hreq/G10.md` G10.009/G10.010) are harmonized with every consumer in the same change (OR24.a (2)). From the release on, OR52.a (2) applies. |
| OR59 | 2026-09-26 | Harvest-pass-1 question 1 (frozen modules shadowed by filesystem files): "c" — runbook and firmware guard both. |
| OR59.a | 2026-09-26 | Integrated — (1) The reflash runbook erases the filesystem on every reflash (harmonization 23). (2) The generated boot entry puts `.frozen` ahead of `''` and `/lib` on `sys.path` before importing any product module, so no filesystem `.py`/`.mpy` can replace frozen product code (`py/runtime.c:147-150`, rp2 adds `/lib`); a buildgen test pins the line, and a twin or Unix-port test shows a shadowing file on the filesystem is not imported. |
| OR60 | 2026-09-26 | Harvest-pass-1 question 2 (mark intended resets): "b, but don't use FRAM, as it's optional. Micropython 1.29 offers a special RAM storage area surviving reboots, several agents suggested this to me already. Use this mechanism, integrate it into the system service and its endpoints (e.g. \"reset_reason\" with a corresponding number code)" |
| OR60.a | 2026-09-26 | Integrated — Mechanism verified at `v1.29.0`: `machine.mem_backup()` (`docs/library/machine.rst:68-160`, `extmod/machine_mem.c:119-152`), enabled on rp2 (`ports/rp2/mpconfigport.h:209-212`); on RP2040, region 0 is watchdog `scratch[0..3]` (16 bytes) and region 1 `scratch[5..7]` (12 bytes), `scratch[4]` stays reserved for pico-sdk (`ports/rp2/machine_mem_backup.c:36-40`). The registers keep their content through soft reset, `machine.reset()` (`watchdog_reboot`, `ports/rp2/modmachine.c:75`) and a watchdog timeout, and are cleared by power-on and the RUN pin (RP2040 datasheet 4.7.4). Not available on 1.24.1 (OR61). Rule: (1) `SystemService` owns one reset-reason record in region 0 (a validity word plus a numeric code); every intended reset writes it immediately before resetting — `_reboot()` for the REST reboot and bootloader requests and the supervisor escalation (`system_service.py:117-129, 252, 347-351`), and the deliberate watchdog starve (`_force_watchdog_starve`). (2) At boot, `SystemService` reads the record with `machine.reset_cause()`, clears it, and publishes `reset_reason` as a numeric code in `/status` and its website field: power-on (`PWRON_RESET`, record cleared by hardware), watchdog without a record (starvation or an unexplained reset), and one code per intended path; an invalid record reads as unknown. The code table lives in SPECIFICATION.md with the other `/status` fields. (3) FRAM is not used (optional hardware). (4) The twin's `machine` fake models `mem_backup()` with the same survive/clear rules (a fidelity row), and each code is proven at L2 and on the dev bench (with the hardware go-ahead). |
| OR61 | 2026-09-26 | Harvest-pass-1 question 3 (MicroPython on the legacy units): "b all legacy real devices run 1.24.1. And: \"fielded\" is relative. I build all sensors and still own all of them - full access anytime." |
| OR61.a | 2026-09-26 | Integrated — (1) Every legacy unit runs MicroPython 1.24.1; the "1.26" statements (CLAUDE.md platform target and `modules/_boot.py` rule, BACKLOG.md, SPECIFICATION.md Part F, the runbook) are corrected to 1.24.1, and the `_boot.py` rule's "never separately verified" now names 1.24.1. (2) "Field", "fielded" and "deployed" mean the owner's own units in service: the owner builds and holds every unit with full access at any time, so no requirement may rest on units being out of reach; a legacy-vs-refactor difference is weighed by function (OR48, OR57), never by an unreachable fleet, and a reflash is always the owner's own operation. |
| OR62 | 2026-09-26 | Harvest-pass-1 question 4 (SGP40 general-call reset on every task restart): "b, and the recording as \"my decision\" is clearly wrong, I never decided that. Check if you can identify the mechanism how that sneaked into the docs and catch more of such occurrences." |
| OR62.a | 2026-09-26 | Overtaken by OR64.a (question 4 misdescribed the effect as resetting the whole bus). Was: (1) The SGP40 driver never broadcasts: `_reset()`'s general call (0x06 to 0x00, datasheet Table 17) is replaced by the addressed `sgp4x_turn_heater_off` (0x3615, Table 14), which returns the sensor to the same idle mode a soft reset reaches (datasheet: idle "after power-up, after calling the sgp4x_turn_heater_off command, or after a soft reset"), followed by the existing identity and self-test checks; the general-call hazard tests at every tier are replaced by tests that assert no general call is sent, and SPECIFICATION.md C.8's "accepted risk" paragraph and the structural exception 2 example are rewritten. (2) Attribution: the "accepted risk" was written by a session agent (`f5c9f90`, 2026-09-03), which judged the risk low itself, headed the paragraph "accepted risk" without naming who accepted it, and parked the fix as "flagged for a project-owner decision if ever revisited" instead of asking; no owner statement exists. Mechanism and repo-wide sweep: `audit/DECISION_PROVENANCE.md`. |
| OR63 | 2026-09-26 | Harvest-pass-1 question 5 (Codecov uploads): "b" — drop. |
| OR63.a | 2026-09-26 | Integrated — Both Codecov upload steps (`ci.yml:525-540`) and every mention (`zizmor.yml` comment, README.md:193, SPECIFICATION.md E.5 and :877/:925, CLAUDE.md "Code quality tooling") go; coverage stays in the Job Summary and the HTML artifact, advisory as today (E.5.3). |
| OR64 | 2026-09-26 | Correction to OR62: "Maybe I got something wrong. You said it \"resets the whole bus\", which I read as \"the whole I2C bus including the host controller gets stalled and restarted, and every device connected to it\". Now you mentioned the broadcast reset which resets *every SCD40 on the bus* but not *the whole bus*. That broadcast actually IS the accepted risk and this decision I really took. I only would not have accepted something stalling the bus itself." |
| OR64.a | 2026-09-26 | Integrated — overtakes OR62.a. (1) The SGP40 general-call reset stays: an owner decision, accepted risk. What it does: one ordinary I2C write of 0x06 to the reserved address 0x00 (datasheet Table 17); every device on that bus that implements the general-call reset restarts — the SGP40 itself; the SCD30, BMP3xx and ISL29125 datasheets document none. The controller and the bus are not stalled: rp2 passes address 0 unchanged to `i2c_write_timeout_us()`, bounded by the bus timeout (`ports/rp2/machine_i2c.c:147` at `v1.29.0`), the NAK is tolerated and the bus lock is held for that one write only (`asy_sgp40_driver.py:585-593`). (2) Boundary: nothing may stall, hold or restart the bus or its controller; a reset reaching other devices is allowed only as this recorded decision, with its hazard tests at every tier kept. (3) SPECIFICATION.md C.8 records it as the owner's decision (owner, 2026-09-26) and drops "flagged for a project-owner decision if ever revisited"; G1.046, G3.038, G9.070 and HR030 read as owner-decided. (4) The audit's question 4 misstated the effect ("resets the whole I2C bus"); an owner question describes the effect exactly, per device and per bus. |
| OR65 | 2026-09-26 | "The reset mechanism for SGP40 using the broadcast, as it currently is implemented, is the desired way. Do not replace it with something else." |
| OR65.a | 2026-09-26 | Integrated — confirms OR64.a (1): `SGP40_I2C._reset()` as implemented at HEAD (`asy_sgp40_driver.py:585-593`: general call 0x06 to 0x00, NAK tolerated, then `asyncio.sleep(1)`) is the required mechanism. No replacement is proposed or made — no addressed heater-off, no bus-wide quiesce mechanism; the audit only corrects its documentation (OR64.a (3)). |
| OR66 | 2026-09-26 | SGP40 compensation, on the sweep finding that SPECIFICATION.md A.4 says the SGP40 skips its read when SCD30 data is missing while `368fa83` recorded an accepted uncompensated fallback: "The current spec should be: * If configured (wired up between both sensors inside the TOML): Skip if unavailable, else runs. * Runs with a constant default which can be wired up inside the TOML if desired / no humidity sensor is on the board" |
| OR66.a | 2026-09-26 | Integrated — overtakes the `368fa83` "silent uncompensated-VOC fallback" record. (1) A temperature or humidity source wired in the device TOML (`[instance.wiring.temperature_source]`/`humidity_source`, e.g. `devices/wozi.toml:58-64`): while its value is unavailable the SGP40 skips its read (no VOC value, no fallback substitution); once available, it reads compensated. Today's code does this (`asy_sgp40_driver.py:270-280`). (2) No live source (not desired, or no humidity sensor on the board): the SGP40 reads with a constant compensation value — the datasheet default 25 °C / 50 %RH (Table 9) unless the TOML sets another constant (`{default = true, temperature = …}`, `_DefaultTemperatureSource`/`_DefaultHumiditySource`, `asy_sgp40_driver.py:100-125`). The constant is always stated explicitly in the TOML (owner, OR67): both `@value-wiring` tags stay `required` (`asy_sgp40_driver.py:96-97`), so an SGP40 with neither a live source nor an explicit `{default = true}` fails the build. (3) SPECIFICATION.md A.4 (:276-278) and its CLAUDE.md/SPEC mirrors state (1) and (2). |
| OR67 | 2026-09-26 | On whether the constant compensation default must be stated in the TOML: "yes, that is the case, so the current state looks correct to me." |
| OR67.a | 2026-09-26 | Integrated into OR66.a (2): the explicit `{default = true}` entry is required; the current `required` wiring tags and the build failure for an unwired SGP40 are correct and stay. |
| OR68 | 2026-09-26 | Decision-provenance questions (`audit/DECISION_PROVENANCE.md`): "1. a 2. b, but in case of changes by myself take my most recent decision 3. a 4. yes 5. b 6. a" |
| OR68.a | 2026-09-26 | Integrated — (1) List A (52) is confirmed as the owner's decisions; each gets "(owner, date)" in its text, with the dropped tags restored (A14, A23, A24, A48) and A37's "added later, not one of the original twenty" put back. (2) List B is decided per item in the question rounds; where the owner changed a decision themselves, the most recent owner decision applies without asking. Applied as a general rule, it settles without a question: A2-02/A2-03 (the buildspec schema stays hand-maintained, owner 2026-09-18, later than the 2026-09-09 L.1 criterion; L.1 criterion 1 names the one table edit per new driver); A2-04 (the owner-tagged WP5 deferred flush, `9ac59cf`, replaces "a write is fast enough not to matter"); A2-05 (the supervisor's counter decay stays intended, OR18.a); A2-06 (soak stays a dedicated opt-in run on top of the bench tier; OR45.a's levels do not include it). C04 is stale: `socket.getaddrinfo()` no longer appears in `src/`, so CLAUDE.md's getaddrinfo half goes. (3) The remaining A2, B, C and D items are asked in chat, about ten per round, in the owner question format. (4) The five prevention rules are adopted: every decision statement names its actor and date; an owner decision quotes the owner's words and the question; compaction, migration and proofreading never change actors, qualifiers or scope; owner questions live in one BACKLOG.md list and nothing cites a temporary plan by section or number; a `tests_scripts/` check fails on actorless decision vocabulary and on citations to missing files, headings or numbered decisions (existing text on an allow-list until the audit rewrites it). They become CLAUDE.md working agreements in B0. (5)/(6) Five questions were asked and six answers given; which answer belongs to question 5 (the 75 engineering-local choices) is asked back. |
| OR69 | 2026-09-26 | Provenance round 1: "1. a 2. a 3. a 4. a (res not \"OK\" means that the request itself was broken, not invalid content) 5. a 6. a 7. defer - we might need to decide if we need chunking or not 8. a 9. b" |
| OR69.a | 2026-09-26 | Integrated — each becomes the owner's decision, dated 2026-09-26, in its home text. (1) A2-01: an abrupt reset mid-write may lose a module's whole FRAM error history; the loss stays all-or-nothing, never a partial or garbled restore, and a commanded reboot loses nothing (SPEC A.4 :189-198). (2) A2-07: `FiltCoeff` keeps both meanings (BMP3xx IIR index, ISL29125 EMA coefficient), namespaced per sensor; the "deployed units" reason is replaced by this decision. (3) C01: a power loss between a PUT's response and its deferred flash write may lose that change silently; the write never corrupts (SPEC F.2 :3653-3657, `buildgen/codegen.py:502-503`). (4) C14: `res` is "OK" when the request itself was processed; a non-"OK" `res` means the request was broken (unparseable, wrong shape, unknown endpoint), never invalid or failed content, which is reported per field in `result` (Valid/Invalid/Failed/Unchanged); SPEC A.8/C and the nine test sites say this with the owner's reason. (5) C02: SCD30's data-ready-driven read may coincide with other reads on its bus; that is the chip's own timing and outside OR47.a's spacing. (6) C03: the notification active window supports a window that spans midnight (`OnH` > `OffH`, e.g. 22-6), legacy's evident intent (OR57.a); a product change with tests at L1/L2 and the website. (7) C12/C13: deferred — the owner first decides whether chunking is needed for UART peer-sized allocations (`_accept_set()`, up to ~64 kB) and the unbounded `readline_until_complete()`; entered in BACKLOG.md's owner-question list with both sites and the memory rule they touch. (8) C17: a connection counts until it has closed; ~70 % refusals of back-to-back clients at the limit stay expected. (9) C05: the refactor stays pinned to a chosen MicroPython version and moves only on the owner's call (SPEC :3441-3442 reworded; CLAUDE.md's re-check pass runs at each owner-approved bump). |
| OR70 | 2026-09-26 | Provenance round 2 (list B): "1. a 2. a 3. a (never write without user / api interaction as a standing rule) 4. b 5. b 6. a 7. a 8. i don't understand the issue, dev is different hardware, wozi cannot run on it and never will 9. i don't understand the issue at all 10. a" |
| OR70.a | 2026-09-26 | Integrated — owner decisions dated 2026-09-26. (1) B01: the shared hotspot fallback password is accepted permanently, a known limitation under OR52.a (3)'s trusted-LAN threat model; CLAUDE.md, SPEC :6053/:6136, `asy_wifi_service.py:50-52` and `pyproject.toml:233` say so with this date instead of the lost "for now". (2) B02: power-cycle recovery stays because the owner judged a reachability probe not worth its complexity (`655e4f9`); "intended recovery feature, don't propose" goes, and `tests_hardware/README.md:625-641`'s "not decided here" is updated. (3) B03: the SCD30 driver never starts continuous measurement on its own; a new sensor measures after its first ambient-pressure PUT. Standing rule: firmware never writes to a limited-endurance store (SCD30 NVM, the flash filesystem) without a user or API action; FRAM is outside it (OR37). Its reach over boot-time config repair is asked back (round 3). (4) B06: the `NTP_Host` 1,024-character bound is re-decided with the key harmonization (OR58.a), together with the other string bounds; the "fielded behaviour" reason, "do not re-raise" and SPEC :5308-5311's parked text go. (5) B07: the UART error-32 blind spot is fixed: bytes `readinto_until_complete()` discards on a short-frame timeout count toward `_resync()`'s drained total, so the mismatch diagnostic fires; tests at L1/L2; a receiver-side diagnostic, logged in UART_C_PORT_CHANGELOG.md as Python-internal. (6) B08: a `ResetErrors` whose `_write()` reports a detected failure answers "Failed" for that field (a content outcome, OR69.a (4)); an acknowledged write stays trusted. (7) B09: `ResetErrors` stays global only, permanently; "for now" goes. (8) B13: resolved without a decision — the owner's ruling stands (wozi's firmware on dev hardware is an invalid test; wozi never runs on dev); the doc keeps only that, drops "not a real bug", and Phase C's bench runs of dev's own firmware cover the shared SCD30/SGP40 bus. (9) B14: re-asked in plain terms (round 3). (10) B15: no version or capability negotiation, now or at the C reconciliation. Also settled from recorded owner words without a question: C07 (the hardcoded, uniform 8000 ms watchdog is the owner's "must be hardcoded so no error ever can circumvent it", FINAL_WIRING_PLAN.md Step 1; "flashing out of scope" states the build scheme's scope), B04 ((a) NVM write budget = CLAUDE.md's owner wear rule of 2026-09-17; (b) the driver-construction technique, protocol-layer classes only and no flash-filesystem I/O — actor corrected 2026-09-29: "project owner's second real-hardware constraint" (`7c8dbbc`, 2026-09-03; pass 3 H2.52), not agent design), C11 (the legacy BSEC `rxbuf` 32 concerns the out-of-scope BSEC use, A03; engineering-local). |
| OR71 | 2026-09-26 | Provenance round 3: "0. a 1. superseded by the workflow description recorded in this session earlier, but quite close to option a 2. a (which means, all stays as is, including the initial start of measurement at scd30) 3. a 4. a 5. a 6. a 7. b 8. b" |
| OR71.a | 2026-09-26 | Integrated — owner decisions dated 2026-09-26. (0) The 75 engineering-local decisions stay, each labelled "(agent, date)" as agent design, except where an OR row asks for a change. (1) B14: CLAUDE.md's step-session workflow is rewritten to the workflow recorded in this audit and stays a standing practice for substantial work: research and cross-check first (OR2); owner questions only at requirement recording and in the consolidation run, never during execution (OR2.a); tests first, then implementation, then coverage tests; a "pause" is a self-set sync point (commit, push, full suite at both GC stages, green CI, status note), not a wait for the owner (OR6.a); no owner stop-points inside a unit, the report comes at its end (PQ8). (2) OR70.a (3)'s no-write rule has one exception: a config file with a bad, missing or unknown key is repaired by at most one write per boot (`config_manager.py:471-480`); everything else stays as is — the SCD30's first start of continuous measurement is the first ambient-pressure PUT (`asy_scd30_driver.py:577-589`: setup only reads the firmware version and soft-resets), and a first boot with no config file writes nothing (harvest decision, HARVEST_REQUIREMENTS.md 3.3). (3) B10-B12: the owner's ISL29125 words stay as the owner's; "Settled; do not re-propose", the general "derived, never exposed" rule and "device and maths constants are not settings" are marked agent-derived and open to change. (4) C06: "and never will" goes from DEVICE_REFERENCE.md:100-101; a device's TOML decides its sensors. (5) C08: DHCP-client faults are a documented known limitation (OR5.a). (6) C09: the off-subnet spoofing test stays the one permanent bench skip. (7) C10: free heap (`gc.mem_free()`) becomes a `/status` field, entered in the OR43.a value inventory, so a loaded heap floor can be read on silicon. (8) C15: a live-readback `GET /sensors` reads all of a module's fields in one step, so a concurrent PUT cannot tear it; the characterization test in `tests/test_asy_webserver_service.py:1108-1137` turns into a consistency test. Settled from facts without a question: C16 (README.md:611-613 is wrong — an integer for a float field is coerced, `config_manager.py:163-164`; README corrected); B05 (the owner's 2026-09-15 words keep `test_bus_hazard_multi_device.py` as the permanent home for generic hazard shapes; its tests take OR33.a necessity verdicts one by one). |
| OR72 | 2026-09-26 | Provenance round 4: "1. Not sure. Only okay if it ever has a realistic chance to pass. Very hypothetical test. 2. Not sure. We added this once to reduce the yields and reduce churn. Probably better to keep,but check the evidence you can find. 3. a 4. a 5. b 6. does that make sense? It it is not connected, you cannot read the phase. It seems to be unreachable by definition. 7. a 8. a 9. a 10. a" |
| OR72.a | 2026-09-26 | Integrated — owner decisions dated 2026-09-26. (1) F18: the harvest-pass decision (admission fairness so a writer cannot starve) is withdrawn — four zero-think-time readers are a hypothetical client, and even a fairly admitted `ResetErrors` would likely miss the 15 s cap (three readers already land at 13.2-14.7 s, BACKLOG item 24). The test stays as an OR49.a degradation check only: no crash, reboot, task end or MemoryError marker, and full recovery once the load stops (all met on 2026-09-25); writer starvation under that load is accepted degradation, not a failure. Interpretation, open to the owner's veto. (2) T4: the FRAM per-command loop hold (~3 ms per 1-byte write) stays. Evidence: the 2026-09-18 heap remediation made the chip commands synchronous bodies under one bus-lock hold per block operation, with yields only between status pairs, payload and length slices (`c621cfb`, `8951387`, the latter the owner's answer to that plan's decision item 6); a blank logger `setup()` dropped from 122,880 B to 13,696 B of allocation (9.0x). Yielding between commands would turn each command back into its own coroutine, the churn that remediation removed; the UART per-poll floor (80 B, SPEC J.6) absorbs a 3 ms pause at 115200 baud (~35 B). (3) W3: the 256 B response pieces and their +17 % on `/status` are accepted as the price of SPEC I.3's bound. (4) T1: closed on the flash-tier figure (largest block 84,112 B after `build_system()`, control and production arms identical); `test_memory_stress.py` echoes its `GC_THRESHOLD`. (5) Item 24: `ResetErrors` resets the FRAM-backed logs concurrently rather than one after another, then a bench time budget is set (`tests_hardware/error_log_helpers.py`). (6) D03: no phase field — a reachable board on the bridge network is by definition STA-connected, so the indirect check stays. (7) D04: the littlefs resize (SPEC B.14.3) is dropped until flash space is actually short. (8) D05: the DNS server's error history is shown with the networking data under the OR43.a value inventory. (9) C18: the dead-man's switch before any destructive bench-network change is a standing rule (owner, 2026-09-26). (10) C19: the "dev config quirks are not bugs" rule goes; dev's generated config is held to the same standard as every device. |
| OR73 | 2026-09-26 | Single-board target (E02, `SPECIFICATION.md:6522`): "Only the Pico W." |
| OR73.a | 2026-09-26 | Integrated — the project targets the Raspberry Pi Pico W (RP2040 + CYW43439) only; SPECIFICATION.md:6522-6523 carries "(owner, 2026-09-26)" in place of the dead "(project owner confirmed, §6.5)". No other board is designed, built or tested for. |
| OR74 | 2026-09-28 | ISL29125 scope: "The Isl29125 is currently only wired up in Dev alone, but this is not a decision. It's the first place it was applied, others will follow. All decided inside TOML." |
| OR74.a | 2026-09-28 | Integrated — confirms the pass-2 resolution (`audit/pass2/LEAD.md` 1 #6, OR71.a (4)): SPEC M.1.1 requirement 18 ("Scope is the `dev` variant only … must not gain one") becomes a current wiring fact ("today only `devices/dev.toml` wires an ISL29125"), with no scope rule and no foreclosure; no allow-list, test or doc may restrict which device TOML wires which driver. |
| OR75 | 2026-09-28 | Boot order (pass-2 question 3): "Boot order is tasks before timers, and that should have been the case in legacy as well - please check" |
| OR75.a | 2026-09-28 | Integrated — checked: legacy started the timers first too — `timer_sequencer(timer_starters, 1000)` and `await timers_running.wait()`, then the task starts with `asyncio.sleep(1.0 / len(task_starters))`, then `ntp_force_sync()` (`modules/sensortask-wozi.py:575-583`; the same in arzi `:509-515`, dev `:593-599`, neu `:509-515`). So the order is the owner's decision, not a restored legacy behaviour. Order, generated and fixed (OR47.a (1)): construction, the one-time `setup()` batch, task starts, timer starts, then the first NTP force sync — last, as in legacy, so the webserver answers during the sync (today it waits for it, G1.091); the NTP placement is the lead's choice on that basis, on the owner-review list. Proven per generated device in the twin and once on the bench (OR47.a (1)). |
| OR76 | 2026-09-28 | ISL29125 calibration aid: "For the overlap calibration of the ISL29125, we should add a field to the measurements API, a numerical code which tells if the current brightness is suitable, too high or too low for determining the calibration factor and show this on the measurements webpage in a user friendly way. At the moment it's pure guessing if lighting conditions are fitting." |
| OR76.a | 2026-09-28 | Integrated — a new `/measurements` field of the ISL29125 driver, published on every read: a numeric code for whether the current light suits the gain-ratio calibration — suitable (green counts inside the auto-range overlap band, the same test the calibration run applies, `asy_isl29125_driver.py:638-641`), too dark, too bright, plus a code for "not applicable now" (fixed range, or the range still settling) if the band cannot be judged. The code table lives with the other measurement fields (SPEC M.1 and the `@web` tag); the website shows it on the Measurements page as a plain-language label (and colour cue) next to the calibration fields, via its `@web` tag. A feature addition by the owner's request (OR12 does not apply); tests at L1/L2 and the website; the code joins the OR43.a value inventory and LEAD/R08's API reference. |
| OR77 | 2026-09-28 | Bench fault injection: "Concerning the DNS spoofing and error injection in the real bench: we should try that under two circumstances: if the effort of this is reasonable and if we can cover test cases we cannot cover under any of the other tests." |
| OR77.a | 2026-09-28 | Integrated — refines OR71.a (6) (C09) and OR45.a (3): a real-bench fault injection (the off-subnet DNS spoofing test, and every twin fault that seeks a real-hardware equivalent) is built only if both hold: its effort is reasonable, and it covers a case no L1-L3 test can cover. Each candidate gets that two-part verdict with its reason in the register; a candidate failing either stays a listed exception (for C09, the permanent bench skip). |
| OR78 | 2026-09-28 | No hard-coded variants: "One important requirement I want to highlight, as it seems to be lost regularly: nothing about the WoZi and Dev build shall remain hardcoded at any place anymore. As those two were the basis for setting up the buildgen, they seem to have left traces allover, although I insisted several times on removing such traces. Meanwhile, we are in state where any board variant can live solely in one single TOML file per variant. This is a project wide truth, not limited to the firmware. It is valid for the tests, tiers, twins, website - and any other places." |
| OR78.a | 2026-09-28 | Integrated — (1) Every board variant lives solely in its `devices/<name>.toml`: no file outside `devices/` names a variant in code, config, CI, tests, tiers, twin, website, scripts or tooling. Device sets are derived from `devices/*.toml` (OR43.a (3), OR54.a (1)); where a run needs one device (the board on the bench, a twin default, a website demo, a test fixture), it comes from a TOML property, a runner argument or the derived set — never a literal. (2) No exceptions: `wozi` loses its role as the hard-coded default and golden reference (tests and twin runs go over every device or a derived one), and the bench board is named by data, not code, so the physical fact that only one board is flashed (A05) holds without any literal; the pass-2 exception "the hardware tier's fixed `dev`" (`audit/pass2/G1.md` R36) is withdrawn. (3) Docs may name a device as a current fact or an example, never as a rule. (4) A `tests_scripts` check fails on a variant name literal outside `devices/` and docs. (5) Starting point (2026-09-28): about 140 tracked files outside `devices/` name `wozi` or `dev` (e.g. `ci.yml`, `scripts/test.sh`, `scripts/build_firmware.py`, `digital_twin/run_generic_integration.py`, `js/app.js`, `js/mock-server.js`, 37 files in `tests/`, 28 in `tests_scripts/`, 32 in `tests_hardware/`); each is removed or derived in the unit that owns the file, with the check landing in B1 (one-source website definitions and the tier ladder). |
| OR79 | 2026-09-28 | On OR77: "Be aware that my decision to try dns fault injection reverts my prior answer to your question (don't do it) to \"let's at least try it\"" |
| OR79.a | 2026-09-28 | Integrated — overtakes OR71.a (6) (C09, "accept the permanent skip"): the off-subnet DNS spoofing test is attempted on the real bench. The default is to try; OR77.a's two conditions (reasonable effort, a case no L1-L3 test covers) are what the attempt must show, and only an attempt that fails them leaves the skip in place, recorded with its reason. The same applies to the other real-bench fault injections OR77 names. |
| OR80 | 2026-09-28 | Datasheet storage (pass-2 question 1, options: 1 where they live — a private companion repo cloned beside this one, b private repo as a git submodule, c encrypted files, d whole repo private; 2 the copies in history — a leave history alone, b rewrite at close): "1 b 2 a" |
| OR80.a | 2026-09-28 | Integrated — (1) The datasheets move to a private repository the owner creates and grants access to (the owner, the Claude GitHub App for sessions; nobody else), included in this repo as a git submodule at the same path `datasheets/`, so every citation of `datasheets/<chip>/<file>` stays valid; the public repo shows the folder and the private repo's URL, never the contents. The files leave this repo's tree in the same change. (2) History is not rewritten: earlier commits keep the PDFs; no commit hash changes. Consequences carried by execution: CI and public clones run without the submodule, so nothing in the build, lint, test or CI path may need a datasheet (checked); sessions that need one initialise the submodule (setup script or `git submodule update --init datasheets`), and a missing checkout is named, never silently skipped (CLAUDE.md datasheet rule); ENV.T04's extraction reads the submodule; README, CLAUDE.md and SPECIFICATION.md A.6 state where the datasheets live and how to get access; the Raspberry Pi PDFs (CC BY-ND 4.0) move with the rest, one place for all. |
| OR81 | 2026-09-28 | Stricter typing (pass-2 question 2, after the lead's explanation of what `disallow_any_explicit` changes): "do it in this audit" |
| OR81.a | 2026-09-28 | Integrated — overtakes the 2026-09-11 deferral (BACKLOG.md:39-51): mypy's `disallow_any_explicit` is switched on in all three passes (`[tool.mypy]`, `digital_twin/typecheck.ini`, `host_typecheck.ini`) within this audit. Typing only — no runtime change, the frozen image behaves identically. Scheme: task lists `Task[None]`; one named alias per repeated callback shape; one JSON type alias for REST payloads; small `Protocol` classes for "has this method" values and for the test fakes that impersonate MicroPython objects; `object` where a value is genuinely open (variadic logging arguments). Timing: B0 re-measures the counts per pass (last 224 main, 115 host, twin 45 stale); the flag is switched on right after the B1 foundations, so the signatures they rewrite (OR46.b, OR58.a, OR60.a) are typed once in final form, and each B2 unit resolves its files' findings; the flag is on and all passes clean before B5. `disallow_any_unimported` (54 at the last count) is measured in B0 and taken along where the same edits clear it; what remains goes to the owner as a consolidation question. BACKLOG's deferral item is removed. |
| OR82 | 2026-09-28 | Owner-tagged implementation choices (pass-2 question 4): "If you really verified me to be the source for the 25 decisions and could track them down to no drift they get an owner label." |
| OR82.a | 2026-09-28 | Integrated (result: 18 owner — L02, L04, L05, L08, L12, L13, L17, L21, L30, L33, L37, L39, L40, L47, L48, L50, L53, L72; 7 agent — L06, L44, L51 drifted, L11, L20, L74 source not verified, L62 no owner source) — refines OR71.a (0) for the 25 list-L decisions with an owner trail (`audit/pass2/G9.md` R38): each one is checked (`audit/pass2/verify/L25.md`) for (1) source — the owner's words, or an owner tag written in the introducing commit — and (2) drift — today's text keeps the original meaning, scope and qualifiers. Both verified: "(owner, date)" with the source cited. Either one not verified: "(agent, date)", as OR71.a (0) says for the rest, with the owner trail and the drift listed for the owner's review. |
| OR83 | 2026-09-28 | "restore the drifted ones, and F18: a" |
| OR83.a | 2026-09-28 | Integrated — (1) L06, L44 and L51 drifted from the owner's recorded words (`audit/pass2/verify/L25.md`); each is restored to its first record and labelled the owner's: L06 "leave as-is, no alternate documented read-back exists to switch to" (owner, 2026-07-22, `75f2e11`) replaces "confirmed intentional — don't fix"; L44 exemptions central "rather than as # noqa comments scattered inline" (owner, 2026-09-10, `2badee1`) replaces "never"; L51 "`dev`'s real website is the most biting test" (owner, 2026-09-23, `c349559`), whose device scope is carried today by OR54.a (1) and OR78.a (every device's real site, never a hard-coded one). Result of OR82/OR83: 21 owner, 4 agent (L11, L20, L74 source not verified; L62 no owner source). (2) F18: option (a) — the OR72.a (1) reading stands as the owner's: four zero-think-time readers are a degradation check (no crash, reboot, task end or MemoryError marker; full recovery after the load); a write that does not get through during that flood is accepted; no admission fairness. |
| OR84 | 2026-09-28 | Boot setup batch (after reading a generated `sensortask_dev.py`): "Technically this is correct, but I would have expected this to be implemented the same way as the task starters and the timer starters - a sysfunct function which gets the list of the setup functions to be called, and all of the looping, collecting and feeding is done automatically." |
| OR84.a | 2026-09-28 | Integrated — the generated `main()` hands one ordered list of setup functions (the fixed order OR75.a keeps: FRAM, `sysfunct`, `conn`, `ntp`, then every module needing setup in construction order) to one `SystemService` method, the same shape as `start_timers(timer_starters)` and `start_and_check_tasks(task_starters)`; that method does the loop, the watchdog feed after each setup and the placement collects (one before the batch, one after each unit, SPEC I.4(f.1)). The unrolled per-module block in `buildgen/codegen.py:455-467` goes. Consequences: the `gc.collect()` allowance moves from `codegen.py`'s emitted strings to that `system_service.py` method — `scripts/lint.sh`, `tests_scripts/test_gc_collect_sites.py`, SPEC I.4(f.1) and CLAUDE.md's exception text follow; the boot-contiguity test (`test_digital_twin_boot_contiguity.py`) must still pass unchanged. Register LEAD/R20; units U20 (GEN), U11 (CORE) (unit numbers corrected by the lead 2026-09-29: GEN is U20, CORE U11, plan 4.1). |
| OR85 | 2026-09-28 | Frozen-module staging kept for inspection: "I also once already demanded that the whole directory where the Python files for compiling the frozen modules (containing the py files, not the pyc) is preserved for inspection after the firmware was built. Deletion / cleaning happens at the beginning of a build process, not at its end. At the moment this was challenging, as the directory only existed in /tmp for some seconds and got immediately deleted again. So this should be changed." |
| OR85.a | 2026-09-28 | Integrated — (1) `scripts/build_firmware.py` stages into a persistent per-device directory under the gitignored `build/` (the staged `.py` files and the generated `manifest.py`) instead of `tempfile.TemporaryDirectory()` (`build_firmware.py:139`); it is wiped at the start of that device's next build and kept after the build, a failed build included; the run prints its path. (2) The owner's rule "deletion / cleaning happens at the beginning of a build process, not at its end" is applied to every intermediate of the firmware chain: `scripts/build_website.sh:19-24` and `scripts/build_frozen_html.sh:19-20` delete theirs on EXIT today (lead reading of the rule's scope, on the owner-review list). (3) The earlier demand has no trace in commits or docs (searched 2026-09-28); per OR64 that is not "not decided": it is a lost owner decision (harmonization 27) and a refined-harvest RP03/RP37 instance. Register LEAD/R21; unit U27 (SCR) (unit numbers corrected by the lead 2026-09-29: SCR is U27, GEN U20, plan 4.1). |
| OR86 | 2026-09-28 | Build without autostart: "I also want to have a command line option for building a firmware which builds a version without autostart. This is what I need if I want to e.g. start it manually in Thonny's REPL mode and watch the console logs and experiment with it." |
| OR86.a | 2026-09-28 | Integrated — `scripts/build_firmware.py <device>` gains a device-agnostic option (e.g. `--no-autostart`) that builds the same frozen image except that the frozen boot entry (staged as `main.py`, `build_firmware.py:95-99`) does not run `main()`: it keeps the boot entry's other settings (the `.frozen`-first path of OR59.a, `gc.threshold`), prints the one line that starts the firmware by hand and returns to the REPL; the manual start runs the identical `main()`. The image gets a distinct default name (`build/firmware-<device>-noautostart.uf2`) so it is never mistaken for the release image. Known pitfall carried into its docs: a frozen entry that returns lets a filesystem `boot.py`/`main.py` run (`dev_legacy/README.md:602-611`), so the VFS must be empty — the reflash runbook's erase (OR59.a) covers it. Tests: L0 (both entry variants generated; the option changes nothing else in the image). Register LEAD/R22; units U27 (SCR), U20 (GEN) (unit numbers corrected by the lead 2026-09-29: SCR is U27, GEN U20, plan 4.1). |
| OR87 | 2026-09-29 | Refined-harvest question 1 (five recorded decisions, yours or agent): "1. a: that was my comment during a session. It has no priority in terms of order now, it's only highly important to be applied. 1. b yes 1. c What was swapped there? 1. d yes 1. e which \"both bounds\"?" |
| OR87.a | 2026-09-29 | Integrated — (a) the tier-parity / wrongly-trusted-hazard sweep is the owner's "(owner, 2026-09-15)" (RF005): its "HIGH PRIORITY" is importance, not ordering — the sweep is to be applied, it ranks no work before other work; BACKLOG.md:81-82 and `tests_hardware/README.md:1188` keep the owner tag and replace "HIGH PRIORITY" with that meaning (G9/R27). (b) The chain-completeness rule (every module joins the twin, SPEC:672) is the owner's "(owner, 2026-08-20)", `00eb44d` (RF037); OR43.a (3)'s removal of its definitions clause stands (G9/R37 V28). (d) FRAM differing copies are a hard failure — owner-confirmed "(owner, 2026-07-18)", `69d85b7` (RF029); the tag returns at `src/asy_fram_manager.py:174-175`, `tests/test_asy_fram_manager.py:329-331`, SPECIFICATION.md:214 in U16 (G5/R25). (c) CRC-16 swap (RF001) and (e) `chunk_bytes` (RF043) stay open: the owner asked what each means; explained in session 2026-09-29. |
| OR88 | 2026-09-29 | Refined-harvest question 1c/1e after explanation: "1 b No matter what the decision was, the current state - adhering to the standards, using the CRC functions module - is the correct one. 1 e was actually at my request." |
| OR88.a | 2026-09-29 | Integrated — (c) the CRC-16 swap (RF001) is labelled "(agent, 2026-07-23)", `7f4ebc3`; its result — the standard CRC-16/CCITT-FALSE from `crc_checks.py` in place of the non-standard embedded routine — is owner-confirmed "(owner, 2026-09-29)" as the correct state; UCL A7's "Not a deliberate change" goes in U0, OR's "Python leads" (2026-09-11) is unchanged (G9/R35). (e) One `chunk_bytes` parameter for both bounds — JSON response pieces and static-file reads — is the owner's "(owner, 2026-09-23)" (RF043, G4/R43). |
| OR89 | 2026-09-29 | Refined-harvest questions 2-6: "2. There is no typical openhab load case, this can always be subject to change. So it should withstand b) 3. a 4. a 5. the same as all other chips 6. a" |
| OR89.a | 2026-09-29 | Integrated — (2) no client mix is typical: the webserver withstands any mix of clients (pollers, website tabs) filling the whole connection ceiling, however high it is set; the 2 + 2 = 4 example (2026-08-25) is one instance of it, not the contract; the widened scenario at `tests/_webserver_concurrency_scenarios.py:569-571` becomes the owner's (G6/R49, RF027). (3) Both frozen-port twins, 64-bit and 32-bit, are ad-hoc instruments, never a committed build variant or CI gate (A33, G9/R35, RF028). (4) Restored owner goal "(owner, 2026-07-24)", `cc911be`: every currently-unavoidable blocking call (I2C wedge, `getaddrinfo()`, …) keeps the watchdog backstop only until a genuine non-blocking alternative reliably exists, then that alternative is adopted; one BACKLOG deferred goal lists them, checked in each MicroPython version re-check (CLAUDE.md standing practice); CLAUDE.md's "settled, don't re-propose" for these calls is reworded to "current state, backstopped", not permanent (C04, G9/R36, RF012). (5) A FRAM chip declared in the device TOML but dead or absent is treated like every other declared chip: a configuration not matching the hardware escalates per OR18.a; OR "no module insists on FRAM" (2026-08-11) stays the consumers' rule — modules keep running without FRAM where no chip is declared, and the generated `fram.setup()` result is no longer discarded (G5/R32, RF153; PAR.S12's legacy-reboot comparison resolved). (6) An SCD30 PUT whose `get_config_snapshot()` read-back fails is refused as a whole, nothing written, as legacy did; the response reports the failure (G3/R36, RF347). |
| OR90 | 2026-09-29 | Refined-harvest question 7 (SCD30 bus-hazard fixture; after the lead's explanation that the fixture is both a prerequisite and the SCD30 read-while-write test, corrected option c' = split the two jobs): "7. c' and read the measurement interval first, wait at least 3 intervals for a measurement to arrive before writing" |
| OR90.a | 2026-09-29 | Integrated — the fixture's two jobs are split. (1) The prerequisite "continuous measurement is running" becomes an unmarked, session-scoped fixture pinned in `tests_scripts/test_persistence_write_marker_completeness.py`'s prerequisite set: it reads the stored measurement interval (0x4600) first, then polls data-ready (0x0202) for at least 3 intervals; a measurement arriving means the mode is on (Interface Description §1.4.1: the mode is kept in NVM across power-down) and nothing is written; only if none arrives does it send the start command (0x0010) once. The seven dependents (`flash/test_bus_concurrency.py`) lose `persistence_write` and run by default. (2) The SCD30 same-device read-while-write test (`scd30_same_device_rw_concurrency.py`) becomes its own test owning its write, gated by `persistence_write`. Lead readings: a failed interval or data-ready read fails the fixture instead of writing blind (OR89.a (6)); the wait feeds the watchdog and the host timeout scales with the read interval (3 × up to 1800 s); A16's "every real SCD30 NVM write is opt-in" narrows to owned writes, per the 2026-09-18 owned-vs-prerequisite rule. Register G1/R06; unit U26. |
| OR91 | 2026-09-29 | Refined-harvest questions 8-9: "8. a 9. a (and be sure they don't do it to get an actual memory baseline or something different which makes sense technically!)" |
| OR91.a | 2026-09-29 | Integrated — (8) `asy_uart_comm.py`'s `uart_set`/`uart_set_into`/`uart_set_stream`/`uart_get_into`/`uart_get_stream` (:808-888) stay as the standalone module's general-purpose API (OR36.a (3)), each pinned by contract tests although no product code calls it (G3/R21, RF236). (9) No `gc.collect()` in tests except a memory-measurement baseline (OR39.a (1)); the site check (`tests_scripts/test_gc_collect_sites.py`, `scripts/lint.sh`) extends to `tests/`, `tests_hardware/`, `digital_twin/` with a named baseline allow-list. Lead verification of the three sites (2026-09-29), none a baseline: `tests/test_digital_twin_uart_link.py:294-297` injects GC pauses mid-transfer — the tested property (a pause mid-frame is no inter-part timeout) is real, so it is rebuilt with a synchronous blocking pause (`time.sleep_ms`) sized to the measured worst-case collection pause, deterministic and not tied to today's heap; `:401` and `tests_hardware/device_scripts/uart_link_under_concurrent_system_load.py:101` collect after dropping the churn list on `MemoryError` — redundant, since `gc_alloc()` collects by itself before it fails (`py/gc.c` v1.29.0, :959-972), so the call is deleted and the churn keeps its pressure (G4/R50, RF196). |
| OR92 | 2026-09-29 | On OR90.a's "only if none arrives does it send the start command, once": "yes, and it's important that under all circumstances the start is only sent ONCE." |
| OR92.a | 2026-09-29 | Integrated — refines OR90.a (1): the start command (0x0010) is sent at most once per pytest session on every path. A session-level guard is set before the send and never reset; there is no retry — not after an I2C error, a timeout, a missing confirmation measurement, a fixture error or a re-request by a later dependent; a failure after the send fails the fixture and its dependents instead of sending again. Test (L0, `tests_scripts/`): the prerequisite fixture's send path is driven through each failure mode and asserts exactly one send. G1/R06, unit U26. |
| OR93 | 2026-09-29 | Refined-harvest question 10 (ignore lines whose writer is outside the repo), after the lead's explanation: "Yes, then keep it gitignored." |
| OR93.a | 2026-09-29 | Integrated — option (a): `.gitignore:1-3` (`config.json`, `modules/config.json` — a legacy unit's settings file with real Wi-Fi credentials, only ever copied in by hand) and `.gitignore:53-55` (`.claude/worktrees/` — the agent tool's nested checkouts) stay ignored, each comment naming its outside writer; the settled answer to OR50.a (2) for both (G8/R62, RF321, RF322). |
| OR94 | 2026-09-29 | Refined-harvest questions 11-15: "11 b 12 a 13 b 14 b and don't change the current look of the website, make the codes clickable and show the description on click 15 a" |
| OR94.a | 2026-09-29 | Integrated — (11) After Apply the website clears every input the device accepted (sent value applied, or "Unchanged") and keeps each rejected one with its value for correction; dispatch fields (`SystemCmd` and the like) reset to their no-action state; so a second Apply never re-sends `ForceCalRef`, `AmbPres` or a command by accident (G7/R31, RF346). (12) The `identity` and `ntp` groups' submit buttons read "Apply & Reconnect" and "Apply & Resync", carried by their `@web-group` tags (G7/R29 Part H operator text, RF348). (13) One staleness rule for every sensor driver: a failed or unprovable read keeps the last good sample with its original timestamp, never re-stamped, and the website shows each reading's age; ISL29125 follows it instead of publishing `None` — this overtakes the "reported as `None`" clause of SPEC M.1.1 item 16 (owner list), its "never reports a stale value as fresh, never re-stamped" half stands (G7/R45, G3, RF333, RF343). (14) Readable meanings for codes: a table generated at build time from the one error/status catalog gives each error/warning number and each published status code (`reset_reason`, …) its description; the website's look stays exactly as it is — the codes become clickable and show their description on click; `/status` is unchanged (no text on the wire); G7/R39's "maps no code to text" is gone (G7/R39, G5/R19, RF151, RF340). (15) `/status` publishes the current Unix time (epoch seconds, UTC) again, as legacy `/time/status` did, so every published epoch timestamp can be judged against it (G9/R05, RF344). |
| OR95 | 2026-09-29 | On OR80: "Note that I created a /datasheets private repo on my Git account. I granted access to you." |
| OR95.a | 2026-09-29 | Integrated — fact for OR80.a (1): the private repository is `hundertvolt/datasheets`, reachable from sessions (verified 2026-09-29: cloned, empty, default branch not yet created). OR80.a's move — populate it from `datasheets/` (44 MB: bmp3xx, fram, isl29125, pico w, scd30, sgp40, ws2812), replace the folder with the submodule at the same path, docs and CI checks as listed there — remains execution work, done when the go-ahead is given (unit U0/U36 per OR80.a); a session populating it needs push access to that repository. |
| OR96 | 2026-09-29 | Function ordering (lead's questions: 1 order by name within a role — a add alphabetical, b author decides; 2 scope — a every module and scope, b `src/` classes plus module-level functions, c `src/` classes only): "Concerning the function sorting: 1. a 2. a but not the unit tests themselves" |
| OR96.a | 2026-09-29 | Integrated — extends D.15 (G5/R50, owner-confirmed 2026-09-13/14): (1) within each role group (starters, getters, setters, others) members are sorted alphabetically by name, so the order is fully determined. (2) The rule applies to every module in all eight scopes and `js/` — class members and module-level functions alike — except the test functions of test files themselves (`tests/test_*.py`, `tests_scripts/test_*.py`, `tests_js/*.test.js`, `tests_hardware/**/test_*.py`), whose order stays the author's; fixtures, fakes, harnesses and helper modules inside the test trees are covered. Lead readings (agent, 2026-09-29): dunders keep the head, `__init__` first then the rest alphabetically; module-level functions follow the same private-then-public role order; a definition an import-time statement needs (decorator, module constant, `const` arrow function in JS) is the one allowed exception, named by the check; name comparison is case-sensitive ASCII on the name without its leading underscore. The reorder stays a pure AST-verified move (comments travel, text unchanged) and a lint-gate check enforces the full order in every covered scope so it cannot drift again (LEAD/R17). Units U10 (`src/`), U36 (other scopes). |
| OR97 | 2026-09-29 | Refined-harvest questions 16, 17, 19: "16 b 17 a 19 b" (18 asked back: "how should the software know that the sensor is \"ready\" for calibration? I don't even know which criterion that could be") |
| OR97.a | 2026-09-29 | Integrated — (16) SGP40 `BackupTS`/`RestoreTS` keep numbers on the wire; their special values are defined in SPEC and the `@web` tag — `null` "none since boot", one "no timestamp" value for both fields instead of today's `0` (backup) and `-1` (restore) — and the page shows text for them, never a date or an age (OR94.a (13)/(14) mechanisms) (G9/R05, RF345). (17) The SGP40 driver publishes its VOC-algorithm state (blackout, learning within the 24 h window, settled; restored or fresh) as one numeric code in LEAD/R19's form, with a SPEC table and a page label via OR94.a (14) (LEAD/R23, RF334). (19) The terminal Wi-Fi deactivation (and "Missing WLAN configuration") shows a distinct status-LED pattern, distinguishable from seeking/disconnected and honouring `LedWifiOn` (G6/R25, RF336). |
| OR98 | 2026-09-29 | Refined-harvest question 18 (SCD30 FRC readiness), on the lead's four datasheet conditions: "Condition 1 would work. Condition 2 is wrong, your conflict finding is correct: it must be at the desired rate. Condition 3 depends on the rare, as far as I I remember - there was something like \"it should be a certain number of measurements with that rate which ran continuously\" Check that again. Condition 4 is feasible with a change rate, a minimum duration and a noise floor. Would that make sense, would that match?" |
| OR98.a | 2026-09-29 | Integrated (criteria; the code-vs-refuse choice and the thresholds' values still open) — FRC readiness for the SCD30 is decided by: (1) continuous measurement running (data-ready arriving); (2) at the configured measurement interval, not a fixed 2 s (Field Calibration note: "the desired measurement period … the same as that used in the end user application"; the Interface Description's "2s" read as the default case); (3) uninterrupted operation at that interval for at least max(6 min, 5 × interval) — verified 2026-09-29 in `datasheets/scd30/Sensirion_CO2_Sensors_SCD30_Low_Power_Mode.pdf`: "operated at the newly set sampling rate for at least 6 minutes or 5 times the sampling interval (for sampling intervals larger than 72 seconds)", which covers the 2 min of the other two documents; the clock restarts on measurement start, an interval change, a sensor reset or a missed measurement; (4) a stable environment, measured over a minimum window by a change-rate limit (CO₂ slope) and a noise floor (spread), the floor anchored to the datasheet repeatability ±10 ppm, the window to the response time τ63 = 20 s (Datasheet Table 1). Lead readings (agent, 2026-09-29): statistics by running sums (fixed memory, no sample buffer); a temperature-change guard (±2.5 ppm/°C, Table 1); an interval change also clears readiness because the Low Power note says a changed interval needs a recalibration. G3 Gap 2 / REF/R06, unit U15. |
| OR99 | 2026-09-29 | On OR98 (1 code or refusal, 2 limit values): "1 a, 2 a. Conditions: * Do not use any measurement number or duration counter that could overflow even if only in the long run. A counter which counts up to the number of measurements or the duration and then stops is okay (probably even the best, as it's independent from the UTC timestamp and bounded by principle). * No flash writes, no extra FRAM chunk (FRAM stays optional) * The deliberately settable and possibly drifting over time criteria (like noise, change rate, etc.) become true config parameters with a reasonable default, but can be changed by the user (that is an allowed API triggered flash write)" |
| OR99.a | 2026-09-29 | Integrated — completes OR98.a: (1) the SCD30 publishes a readiness code naming what is missing (not measuring; settling, with time left; drifting; noisy; ready), code table in SPEC, page label via OR94.a (14); `ForceCalRef` is never refused on readiness grounds. (2) The change-rate limit and window length are measured on the bench in the hardware round; the noise floor starts at 1-2 × the datasheet repeatability ±10 ppm. (3) Counting is saturating: the uninterrupted-operation criterion counts measurements (not time, not UTC) up to its target and then stops, reset on measurement start, interval change, sensor reset or a missed measurement; no counter anywhere in it can overflow, however long the unit runs. (4) The whole state lives in RAM: no flash write, no FRAM chunk; after a reboot readiness starts over. (5) The noise floor, change-rate limit and window become ordinary SCD30 config parameters with bench-measured defaults, settable through the API (a user-triggered config write, the allowed kind); the 6-min / 5-interval target stays a datasheet constant. G3 Gap 2 / REF/R06, units U15 (driver, config), U23 (label), U26 (bench values). |
| OR100 | 2026-09-29 | Refined-harvest question 20 (SCD30 Altitude help), after the lead's research (owner: "I found it failing / being ignored without deactivating continuous measurements … wasn't it by setting the altitude compensation how continuous measurement is started? Research this!"): "20 c" |
| OR100.a | 2026-09-29 | Integrated — research (2026-09-29): continuous measurement is started by the ambient-pressure command 0x0010 (Interface Description 1.4.1), not by altitude; "Setting altitude is disregarded when an ambient pressure is given to the sensor" (1.4.8; Sensirion `embedded-scd` `scd30.h`; ESPHome docs); no source requires stopping continuous measurement — legacy's "Turn off continuous measurement for this setting" (`html_raw/wozi/sensorconfig.html:41`) is read as a misattribution of that pressure override. Decision (c): the `Altitude` help states the datasheet rule ("only used while Ambient Pressure is 0; a pressure value overrides it"), and the page warns whenever Altitude is changed while `AmbPres` is non-zero ("ignored: ambient pressure is set"). Open fact for the hardware round (U26, one gated `persistence_write`): with `AmbPres` 0, does a changed altitude take effect at once or only at the next 0x0010 / power-up — the help text adds the answer. G7 Part H operator text, unit U23 (page), U15 (`@web` tag). |
| OR101 | 2026-09-29 | Pass-3 question 1 (twelve proven product bugs, `audit/pass3/SUMMARY.md`), after the detailed explanation: "My decision: Fix the bugs, and make sure the fix of (4) does not depend on a UTC timestamp (ant not on UTC at all)" |
| OR101.a | 2026-09-29 | Integrated — option (a): all twelve are fixed, each with a regression test and a changelog line (D4.04, D4.11 G5/R02; D4.20 G5/R04; D4.36 REF/R03; D4.37 G3/R09; D4.53 G3/R38; D4.55 G3/R40; D4.62, D4.65 G3/R23; D4.64 G3/R06; D4.66 G3/R51; D4.61 extends G3/R36 with round-to-nearest). Bug (4), `SysUptime`: derived from wrap-safe `ticks_diff()` deltas of `ticks_ms()` taken at each wake-up and accumulated, never from the RTC, `time.time()`, NTP or any UTC value; REF/R03's "or RTC deltas" is struck for `SysUptime`. Accumulated as whole seconds plus a millisecond remainder, so it stays a small int (agent reading, in the spirit of OR99.a (3)). Whether REF/R03's other three values (WiFi uptime, NTP sync age, `PauseTime`) share that tick source stays REF/R03's "one tick source" (agent). |
| OR102 | 2026-09-29 | Pass-3 questions 3-10 (`audit/pass3/SUMMARY.md`): "3. a / 4. a (but legacy never PUT the mask accidentally, it was displayed separately, not inside the entry field!) / 5. a / 6. a, bot only if this is possible with the special RAM section, and for sure without flash writes and without FRAM. If not, leave it silent. / 7. adopt correct behavior adhering to the standards without raising complexity / 8. a / 9. c / 10. c" |
| OR102.a | 2026-09-29 | Integrated — (3) an NTP settings change clears `Synced`, as legacy (G6/R30 restored; D3.NET.N040). (4) a PUT carrying the mask answers "Unchanged" and never stores it (G6/R29, now owner rank). Owner correction: legacy's page never sent the mask, it showed the current value beside an empty entry field (`html_raw/general/nettimeconfig.html:45-47`); the new page does the same (`js/templates.js:160-170`, empty input, value as placeholder and caption), so the rule guards non-page clients only, not a legacy failure. (5) an LED command while a signal runs is refused at once with "Failed" (legacy's "LED is busy" in the new envelope). (6) a boot-phase crash leaves a `reset_reason` "boot failure" code with the phase index, held only in `machine.mem_backup()` region 1 (RP2040 watchdog scratch registers `scratch[5..7]`, 12 B; region 0, `scratch[0..3]`, holds G5/R03's reset-reason record; `ports/rp2/machine_mem_backup.c:38-41`, v1.29.0; SPEC F.5.4: survives WDT reset and `machine.reset()`, lost on power-off; region mapping corrected 2026-09-29): the owner's condition "special RAM section, no flash, no FRAM" is met, so the code is added; written at boot-phase transitions only, never per tick, which narrows the 2026-09-11 "not adopted" note in SPEC F.5.4 to per-tick breadcrumbs. (7) captive DNS answers an A (or ANY) query with the A record and every other type with NOERROR and zero answers (NODATA, RFC 1035/2308): one QTYPE check in `src/captive_dns.py` `response()`, no other change (G6/R24). (8) `WifiUptime`/`Connected` keep counting while the hotspot is up, as legacy, documented as "link up, hotspot included" (G6/R27 option a). (9) BACKLOG 30 stays closed (2026-09-25 closure); dropped connections get detection logging so a repeat leaves evidence (H2.99). (10) nobody files the Unix-port `modselect.c` poll bug upstream: a known limitation, removal trigger "fix seen at a pin re-check"; `segfault_stress_repro.py` retires. |
| OR103 | 2026-09-29 | On OR101.a's "whole seconds plus leftover milliseconds … small integer for about 34 years" reading: "I want to add a new central requirement for the whole code: No unbounded counters anywhere. In the legacy code, I added bounds for such things, like uptime counters. They were in that dimension, something in the 30 to 50 years range. Extremely improbable to ever be reached, but anyhow safely confined - a limit which is close to impossible to be ever hit, but if so, nothing bad except a wrong number happens." |
| OR103.a | 2026-09-29 | Integrated — central requirement, whole code (product `src/`, generated modules, `js/`; test and host code follow it where a counter lives): (1) no counter is unbounded: every value that grows with time or events saturates at a named constant cap and then stops. Wrap-by-design values (`ticks_ms()`, CRCs, protocol sequence or id bytes) are not counters in this sense and follow G5/R10. (2) The cap lies in the 30-50 year range at the counter's highest realistic rate: "close to impossible to be ever hit" — owner precedent `_50_YEARS_SEC = const(1576800000)` in legacy `TimeCounterManager.increment()` (`python/CommonDrivers/async_manager.py:6, 24`). (3) Hitting the cap changes nothing but the number: no exception, no allocation growth, no task end, no other behaviour change. (4) Agent reading, fact-checked: rp2 builds `MICROPY_OBJ_REPR_A` (`py/mpconfig.h:163`), so a small int holds up to 2**30 − 1 = 1,073,741,823 (`py/smallint.h:37-42, 62`), about 34.0 years in seconds; a cap at or below it keeps the counter allocation-free, one above it (legacy 50 years; `LastSyncAge` capped at 0xFFFFFFFF, `src/asy_ntp_client.py:209`, ≈136 years) turns into a heap int past 2**30. Seconds counters therefore cap at ≤ 2**30 − 1 (34 years, inside the owner's range); no counter counts milliseconds (2**30 ms is 12.4 days). (5) Execution inventories every counter (a source scan over `src/`, `buildgen/codegen.py` templates and `js/`), names each cap and its rate, and proves each cap by a driven-value unit test (set near the cap, step past it, assert saturation and no side effect), never by soak. Settles OR101.a's "agent reading" for `SysUptime`. New LEAD requirement, pillar P1 (OR44.a "nothing drifts or saturates over months or years"), units U10 (system counters), U35 (tests), SPEC Part G.2 primitive (`LockedCounter` with a cap). |
| OR104 | 2026-09-29 | On pass-3 questions 4 and 2 and the OR101.a scope question: "4 (password mask): Maybe we should not exclude a certain value of "*" but simply not display anything there. This would theoretically allow the "*", although this would be a nonsense password, but I don't want to restrict it in any way. Either display the usual dots there and have the entry field genuinely unfilled below (or equivalent), otherwise just display nothing at all, and nothing is the sentinel for "don't change" as already the case. / 2: option (a) / the "never UTC" goes for the others as well and might be a good candidate for a function which lives in the system service or the base classes, whichever fits best" |
| OR104.a | 2026-09-29 | Integrated — overtakes OR102.a (4). (1) Password: no value is excluded; a PUT storing `********` (or any valid 8-63 character string) stores it like any other password, and the "mask answers Unchanged" rule is dropped from G6/R29. The page shows the usual dots as the current value and leaves the entry field genuinely empty; an empty field is omitted from the PUT and means "don't change", as today. Both halves already hold on the page: `formatFieldValue()` renders a masked field as "••••••••" whatever the API sends (`js/field-format.js:19-20`), and the input starts empty with the dots only as placeholder and caption (`js/templates.js:160-170`); the GET's display value (`src/asy_wifi_service.py:197-201`) is kept for page parity and is never read back by the page. The owner's fallback "display nothing at all" applies only if the dots cannot be shown this way. An echoing non-page client can store `********` — accepted ("I don't want to restrict it in any way"). (2) SGP40 backup verification: option (a), `max(1, …)` on the existing formula; only `BackupPeriod` 67-1440 changes (every save verified), every other period keeps today's cadence; regression tests at p = 1, 7, 32, 60, 66, 67, 1440; G9/R03 extended. (3) "Never UTC" covers all four REF/R03 values — `SysUptime`, WiFi uptime, NTP sync age, `PauseTime` — through one shared primitive that accumulates `ticks_diff()` deltas of `ticks_ms()` into whole seconds plus a millisecond remainder and saturates per OR103.a (≤ 2**30 − 1 s), counting up or down. Home (agent choice, "whichever fits best"): `src/base_classes.py`, next to `LockedCounter`, as a SPEC Part G.2 primitive — every one of the four users already imports `base_classes` (`asy_wifi_service.py`, `asy_ntp_client.py`, `asy_notification_service.py`, `system_service.py`), while a home in `system_service.py` would make three services depend on the system service. |
| OR105 | 2026-09-29 | On OR103.a (4): "Concerning the counter cap, I want to exactly avoid allocations happening at some point. So a reasonable value should be found for that (I don't insist on that 50 year barrier!). / And in one of the upcoming scans, all candidates for such counters must be found." |
| OR105.a | 2026-09-29 | Integrated — overtakes OR103.a (2) and (5). (1) The binding goal is that no counter ever allocates: every cap is ≤ `MP_SMALL_INT_MAX` = 2**30 − 1 on rp2 (`py/smallint.h:37-42, 62`, `MICROPY_OBJ_REPR_A`); the 30-50 year range is no longer a requirement. (2) Proposed value (agent): one shared cap constant 2**30 − 1 for every counter, narrower only where the field's storage or wire width demands it (e.g. the 0xFFFF log counter); for a seconds counter that is 34.0 years, for a fast event counter it is reached sooner and simply saturates ("nothing bad except a wrong number", OR103). (3) Saturation checks before it steps (`if v < CAP: v += 1`, legacy's shape), never `min(v + 1, CAP)`: at the cap `v + 1` is 2**30 and allocates a heap int for that instant. Likewise no cap constant or intermediate may exceed the small-int range — `min(current + 1, 0xFFFFFFFF)` (`src/asy_ntp_client.py:209`) allocates on every step past 2**30 and its constant is itself a heap int. (4) The counter inventory is a consolidation scan before execution, not execution work: every candidate in `src/`, `buildgen/codegen.py` templates, `digital_twin/` and `js/` (JS numbers do not allocate but stay bounded by OR103), with its site, rate, cap, storage width and the allocation check of (3); each ends in a register line. |
| OR106 | 2026-09-29 | "I want two steps to be added before the actual execution: / 1. Step by step create a complete action list of which changes would be done in execution, including higher order changes in other parts ("blast radius") / 2. Once that list is done, scan the list for overlaps and conflicts (e.g. multiple changes at the same place) and consolidate everything, so even if multiple changes would happen to one place, they are then smoothed into a single change. / Where would that fit into?" |
| OR106.a | 2026-09-29 | Placement confirmed by OR108.a (1) — two read-only steps close phase A, after the last scan pass and the register merge, before B0: (A-L) action list: every register work line becomes one or more concrete changes (site: file and function or doc section; what changes; why, with the register ID), each with its blast radius — callers, generated code and buildgen templates, the `js/` mirror, tests at every tier, the digital twin, SPEC/CLAUDE.md/README text, TOMLs, UART_C_PORT_CHANGELOG entries; built unit by unit in plan 4.1 order. (A-C) consolidation: the list is scanned by site for overlaps and conflicts; all changes to one site merge into a single change; a conflict an owner row or the register settles is settled, any other goes to the owner in the owner's format; the merged list is ordered by dependency and becomes B1/B2's work order. The execution go-ahead is then given on the consolidated list. New work found during execution (B0 measurements, B3 fault planting, hardware rounds) passes the same consolidation as a delta against the list before it is applied. |
| OR107 | 2026-09-29 | "Generally, for the whole audit, prefer accuracy before speed. Parallelization is generally allowed, but don't overdo it it, the resulting syncing effort should stay reasonable." |
| OR107.a | 2026-09-29 | Standing rule for every phase: (1) accuracy wins over speed; a check is never cut short, sampled down or batched coarser to finish sooner. (2) Parallel agents stay allowed (PQ9, OR1.a), but this narrows 2026-09-25's "as many as you like": the agent count per wave is chosen so the arbiter can still read, check against sources and merge every result without shortcuts (4.4). If merging would need shortcuts, fewer agents run. |
| OR108 | 2026-09-29 | "1 fits / 2 yes, go ahead / 3 include and start after the merge of pass 3" |
| OR108.a | 2026-09-29 | Answers the three questions asked after OR107. (1) OR106.a's placement is confirmed: A-L and A-C close phase A, and the execution go-ahead is given on the consolidated list. (2) Pass 3's register lines and OR101-OR108 are merged into the register now, before any go-ahead (audit files only). (3) Pass 4 adds the fetched-source checks (v1.28 "unchanged" claims, upstream-tracker claims, lwIP connected-PCB filter NET.S19, paths-filter push base CI.S11, online-only deferral triggers) and a sample check of the 675 score-judged doc references; it starts after the merge. |
| OR109 | 2026-09-29 | Pass-4 answers (`audit/pass4/SUMMARY.md`): "Latent SGP40 race: Fix this. No races allowed (see specs). / 1. "On the board its 32-bit steps create temporary heap integers on every sample, about once a second, forever." - "temporary", that's the difference. Not something which grows on the heap and never can get collected by the gc. If the VOC algorithms allocates and the allocation goes after it's done and gc can clean the mess up, everything is settled. It appears and disappears, but does not grow. / 2. a / 3. a" |
| OR109.a | 2026-09-29 | Integrated — (0) the `SGP40_I2C.measure_raw()` race (pass 4 R.26) is fixed in execution: the shared `_measure_command` is staged inside the device-session hold, with the adapted `tests/test_bus_hazard_multi_device.py:356` as its regression test; the general rule "no races" (SPEC C.8 device-session model) is owner rank for every driver that keeps per-call input in a shared buffer. Recorded as register work, not executed: the execution go-ahead is still given on the consolidated action list (OR106.a, OR108.a (1)). (1) VOC fixed-point arithmetic: per-sample temporary heap ints that the GC reclaims are accepted; the binding property is that nothing grows (no allocation that survives its sample). No rework of the fix16 helpers; no exception clause needed. OR105.a's no-allocation rule for counters stands unchanged (a counter's stored value is state, not a temporary). (2) BMP3xx `SampleInterv` stays 1-3,600 s (legacy's field-proven range, same as ISL29125); the 2026-07-22 "1-600 seconds" (`604c7bb`) is overtaken by this answer. (3) ConfigManager errors keep their own rows (`CFGMGR_<name>` in `/status`, "<module> Config Store" on the page); the owner's 2026-09-16 "this chunking must be hidden" (`d4814cc`) is read as "no FRAM chunk structure shown". |
| OR110 | 2026-09-29 | "The no-allocation rule especially applies to permanent variables stored in the heap, staying there for the whole runtime. If a timer allocates, never reaches any critical value and frees some seconds later, it's less critical. Generally, objects which reside in the heap forever, never are eligible for gc collection, and which can grow, are the forbidden case." |
| OR110.a | 2026-09-29 | Integrated — general memory rule, refining OR105.a and OR109.a (1): (1) forbidden: an object that lives on the heap for the whole runtime (module-level, or an attribute of a long-lived instance), is never eligible for collection, and can grow (a list, dict, set, bytearray, string or int that gains size with time or events). Every such object is bounded by construction (fixed size, a cap, a ring, or eviction). (2) Counters are this case (their value is permanent state), so LEAD/R24 stands unchanged. (3) Temporary allocations that are released and collectable shortly after (a timer's, a request's, the VOC per-sample arithmetic) are less critical: accepted when bounded per operation, and still covered by the memory-discipline ladder (CLAUDE.md, SPEC I.4). (4) Pass 4 adds scan G, growable permanent objects beyond counters, across `src/`, generated code, `digital_twin/` and `js/`, since S07's RP20.f searched only `.append(`/`+=` on attributes in `src/`, the twin and unit fakes. Carried by LEAD/R24's Req (widened to the general rule). |
| OR111 | 2026-09-29 | "In Step 2, the final consolidation, also ensure the final state is complete, sound, and adheres to all our specifications we collected throughout this session." |
| OR111.a | 2026-09-29 | Integrated — "Step 2" is A-C (OR106 (2)). A-C gains an end-state check before the list goes to the owner for the go-ahead: the consolidated list, applied as a whole on top of HEAD, is read as the projected final state and must be (1) complete: every live register requirement is true in that state (a trace per requirement: the actions that make it true, or "holds at HEAD" with evidence), every owner row OR1-OR111 is honoured, no register work line, scan line or verifier finding is left without an action or a recorded reason; (2) sound: no conflict or contradiction between merged changes, no dependency cycle, no action undoing another, every blast radius closed (each caller, generated site, `js/` mirror, test at every level, twin, doc, TOML and changelog duty the merged change touches has its own change), and every test that pins today's behaviour is adapted or retired with the guard named; (3) adherent: every file's merged end state is read against every rule that applies to it — the owner rows (the most recent wins), the register, CLAUDE.md's hard rules and working agreements, SPECIFICATION.md as the list amends it, and the pillars. A gap, contradiction or breach found here becomes a new or changed action; one that no owner row or register line settles goes to the owner in the owner's format. |
| OR112 | 2026-09-30 | "1. Lwip heap stall:  option b as recommended, and thoroughly test this in the hardware session" |
| OR112.a | 2026-09-30 | Integrated; its `TCP_NODELAY` and sizing parts are overtaken by OR114.a — the 10 s modlwip write stall (`extmod/modlwip.c:800-812`, ERR_MEM retry 200 × 50 ms past the 8,388 ms watchdog) is closed by option (b) of the 2026-09-30 question (`audit/actions/verify/U14.md` V.U14.Q1): `TCP_SND_BUF` 1600 (2 × `TCP_MSS`), `MEMP_NUM_TCP_SEG` 72, `MEM_SIZE` 24,900 in `toolchain/versions.toml` `[lwip]`, and `TCP_NODELAY` on every accepted socket in the webserver's `_serve()`, so no pbuf is oversized and the arena bound holds for every peer (about 13.3 KB less GC heap). A-L actions A.U14.30 (lwIP sizing) and the U19 `TCP_NODELAY` action are no longer pending. The hardware session (phase C) tests it thoroughly: dead-client and slow-client page loads on every route at the connection ceiling, the arena/segment/queue limits driven to their edge, no WDT reset, no write stall, page-load time recorded before and after. |
| OR113 | 2026-09-30 | "2. I2c option a, clear at boot. My instructions anyway were meant in the way \"always try to solve / recover from issues with the smallest possible blast radius\" - not like \"never reset the bus\", also in mid operation! So if there is a an error on the bus and / or a participant, try to recover mildly, but escalating up to a full bus reset is absolutely allowed if the mild measures don't work out. Apply this idea throughout!" |
| OR113.a | 2026-09-30 | Integrated — overtakes the reading of OR64.a (2) ("nothing may stall, hold or restart the bus or its controller") and the lead's harmonization 38 built on it. (1) Boot: each I2C bus is cleared once before its controller is constructed — if SDA reads low, SCL is clocked up to 9 times as a plain GPIO, then STOP (option (a) of the 2026-09-30 question; A.U14.17 no longer pending). (2) Standing principle, applied throughout (every bus, every participant, boot and mid-operation): recover with the smallest possible blast radius and escalate only when the milder step does not work — retry the transaction; recover the one participant (its own reset command or re-configuration); clear the bus (release a held line: SCL clock-out and STOP, under the bus lock so no other device session is interleaved); re-initialise the bus controller; restart the task; reboot; the hardware watchdog stays the final backstop. A full bus reset is allowed mid-operation when the milder measures fail. Each rung is bounded, logged once per event (OR35.b, OR56.a (1)), race-free under the device-session model (OR109.a), and tested at every level that can reach it. OR64's own boundary keeps its meaning where it was about: the SGP40 general-call reset stays the one owner-accepted reset that reaches other devices. The rp2 fact stands that an in-flight `machine.I2C`/`SPI` transfer cannot be interrupted (G4/R22), so the ladder acts after a transfer returns an error or a participant misbehaves, never by aborting a transfer. CLAUDE.md's wedged-bus rule, SPEC F.2 and G4/R22 are rewritten to this ladder. |
| OR114 | 2026-09-30 | "If we go for lwip option a, as you suggested, and keep watching the fixes in upstream micropython and remove the patch as soon as it is really solved, we can add this the same way as we did for the connection count - in the build command, not in the source code?" — then: "Do it this way" |
| OR114.a | 2026-09-30 | Integrated — overtakes the `TCP_NODELAY` and sizing parts of OR112/OR112.a (root-cause check: `audit/actions/SUPP_lwip.md`; the `setsockopt(TCP_NODELAY)` path writes a pcb that a peer reset can NULL, `extmod/modlwip.c:1527-1535`, v1.29.0). (1) The 10 s modlwip write stall is fixed at its cause: a zero-touch override in `toolchain/micropython_overrides.py` (SPEC B.14) verifies the exact `ERR_MEM` retry loop in the pinned `extmod/modlwip.c`, generates a patched copy outside the checkout in which a non-blocking send returns `EAGAIN` on `ERR_MEM` (upstream PR 19708's change, issue 19704), and swaps it for the original through a generated `USER_C_MODULES` CMake file on the `make` line (`ports/rp2/Makefile:39-40`); the built image is checked to carry it; nothing is written into the checkout. (2) No `TCP_NODELAY` call. (3) The OR112 sizing (`TCP_SND_BUF` 1600, `MEMP_NUM_TCP_SEG` 72, `MEM_SIZE` 24,900) is withdrawn: `[lwip]` keeps its values unless another requirement moves them. (4) Upstream is watched: a BACKLOG.md entry names issue 19704 and PRs 19705/19708; the anchor check fails the build when upstream changes the loop, and the override is removed once the pin carries a real fix. (5) Phase C (OR112's "thoroughly test" stands): first reproduce the stall on HEAD firmware (clients that stop reading mid-`app.js`, then a further page load), then show no WDT reset, no VM stall and recovered service with the override. |
| OR115 | 2026-09-30 | "And add unit tests which hammer on it and prove it is solved and stable" |
| OR115.a | 2026-09-30 | Integrated — the OR114 modlwip override gets hammer tests at every level that can reach it, each proving the stall is gone and the path stays stable (no VM stall, no WDT reset, no `MemoryError` marker, data intact, service recovers), under the standing gc and memory bars: (1) L0: the override itself (anchor load-bearing, generated copy and CMake swap pinned, patched code present in the built image); (2) a host build that runs the real patched `modlwip.c` over lwIP (the Unix port has no lwIP today, so this is new tooling; feasibility is checked from source in A-L before it is planned as a gate): non-blocking writes against peers that stop reading, many connections at once, the arena, segment pool and queue limit driven to their edge — each write returns within a bound, every byte a reading peer is sent arrives, memory returns once peers close; (3) L1: the webserver when writes return `EAGAIN` repeatedly — other tasks keep running, the per-call timeout reclaims the connection, the slot and pcb are released (bounded fake pollers only, CLAUDE.md hang rule); (4) phase C: the stall reproduced on HEAD firmware, then the same hammer with the override (OR114.a (5)). |
| OR116 | 2026-09-30 | "Does the UART loopback module test with and without CRC? I want both." |
| OR116.a | 2026-09-30 | Integrated — at HEAD only L1 runs both modes (`tests/test_uart_comm_hazard.py`, `test_asy_uart_comm.py`: no CRC and CRC16); the generated `uart_link` wires no CRC (`buildgen/validate.py:258`), so L2-L4 carry frames without CRC only. (1) The UART link is exercised without CRC and with CRC16 at every level that can reach it (OR118.a). (2) Delivery (lead, from OR36/OR36.a (1)-(2): no runtime mode switch in the driver, which would be logic that exists only for a test): each `uart_link` instance takes a `crc` TOML key (none or crc16); buildgen refuses a pair whose two ends differ and its bus check counts the CRC length (today it adds 0); `dev.toml` keeps HEAD's no-CRC mode; L2 builds the twin pair in both modes; L3 runs a device script over the same crossover jumper in the other mode; L4 runs the bench suite once per mode, the second on a dev image built with the key flipped, a reflash behind `flash_cycle`. (3) The CRC16 mode is Python-internal wiring, no wire-format change (the CRC algorithm is already J.6's agreed parameter): UART_C_PORT_CHANGELOG gets a Class B entry. RP2040 has two UARTs, both in use, so a second loopback pair is not possible. |
| OR117 | 2026-09-30 | "To the system commands (currently reboot or bootloader, as far as I remember), I want to have added: \"Reset to defaults\" (reverting the whole config written by the Schema inside the tinyfs - SCD30 won't be affected) and \"Erase FRAM\", which plainly clears the whole chip." |
| OR117.a | 2026-09-30 | Integrated — `SystemCmd` today offers reboot, bootloader and mempause (`asy_webserver_service.py:95`, `buildgen/definitions.py:57-61`, generated `_system_cmd_callback`, `codegen.py:524-537`); two values join, labelled as the owner named them. (1) "Reset to defaults": finish every pending config flush, delete every schema-backed `config_<name>.cfg` from the flash filesystem, reboot; at boot each `ConfigManager.setup()` writes its defaults (the existing missing-file path, `config_manager.py:406-485`). "The whole config" includes Wi-Fi & Identity (lead reading of the owner's words): the unit comes back as the hotspot with the default hostname and hotspot password. The SCD30 is untouched: its schema stores no value (all defaults `None`, `asy_scd30_driver.py:57-62`), its settings live in the chip's NVM. (2) "Erase FRAM": pause every FRAM writer, take the FRAM lock, overwrite the whole chip with a pattern no valid chunk accepts (checked against `crc_checks.py` in A-L, since an all-zero block may pass a zero-init CRC), reboot so every chunk owner starts fresh; irreversible, it destroys the error logs CLAUDE.md says to read first. (3) The website asks for confirmation before either; both are as unauthenticated as reboot. |
| OR118 | 2026-09-30 | "All these options must get their full tests and tiers, with the reset config gated behind the flash write flag" |
| OR118.a | 2026-09-30 | Integrated — (1) every OR116/OR117 option (both CRC modes, both new commands) gets full tests at every level that can reach it: L0 (definitions, website, buildgen), L1, L2 twin, L3 flash, L4 bench, under the standing gc and `MemoryError` bars and the recovery-ladder rule. (2) A test whose owned write is the config reset carries `persistence_write` (`--allow-persistence-writes`, the RP2040 flash-filesystem gate); a hardware reset test saves the dev board's config files first and restores them after (inside the same gated test), since the reset drops the bench unit's Wi-Fi. (3) The Erase-FRAM test is not wear-gated (FRAM is outside every wear gate, G1/R04) but reads and archives the FRAM error logs before it erases (CLAUDE.md's FRAM-log rule). (4) The second CRC mode's L4 run reflashes, so it sits behind `flash_cycle`. |
| OR119 | 2026-09-30 | "The commands must fit and sync into the system flow, they might occur in any state and must take care not to break anything except what can be expected by the erase operation. It is also fully okay if they work by shutting down all processes and write access to any storage, apply their purpose and then reboot the system - probably this is the most elegant solution anyway, shut all down controlled, erase, reboot" |
| OR119.a | 2026-09-30 | Integrated — refines OR117.a (1)-(2). (1) Either command may arrive in any state: during the boot `setup()` batch, during a config flush or a FRAM chunk write, inside a bus session, while storage is paused (`mempause`), while a reboot or the other command is already under way, or twice at once; it breaks nothing beyond its own intended effect. (2) Shape: one controlled shutdown sequence — answer the request, refuse any further command, stop every supervised task without restart, let each in-flight storage write finish under its own lock, then close write access to the flash filesystem and the FRAM, apply the purpose (delete the config files / overwrite the chip), reboot through the existing reset path. (3) Each step is bounded, the watchdog is fed through the sequence (the whole-chip overwrite included), and every step is logged once. (4) A power loss at any point leaves a state the next boot handles: an interrupted delete leaves some files, which load or default as today; an interrupted overwrite leaves chunks that fail their check and start fresh. (5) Whether reboot and bootloader move onto the same shutdown sequence is an agent proposal for the OR2.c review, not part of this decision. |
| OR120 | 2026-09-30 | "The added system commands also must take care when shutting down the tasks and doing its work that the watchdog is fed. Probably it's best to completely stop the loop feeding the watchdog, really making sure it actually IS stopped, and feeding it inside the sequence doing the reset work. So neither the watchdog inteerrupts the sequence, nor is there any risk the watchdog is fed although something hangs. Both of these are extremely important!" |
| OR120.a | 2026-09-30 | Integrated — refines OR119.a (3). Today the supervisor loop `start_and_check_tasks()` feeds every `_TASK_CHECK_TIME` (2 s) through `SystemService.feed_watchdog()` (`system_service.py:111-116, 245-249`), plus the boot batch's feeds (generated, `codegen.py:465`); `WDT(timeout=8000)` (`codegen.py:381`). (1) Watchdog ownership passes to the sequence: it stops the supervisor loop and proves it stopped (the task is cancelled and awaited to done, never assumed), and from that moment every other feed site is a no-op (a one-way latch inside `feed_watchdog()`, so no other task, timer or boot step can feed). (2) The sequence feeds only through its own feed, once per bounded step, each step shorter than the WDT timeout with margin (the whole-chip FRAM overwrite in chunks); a step that hangs gets no feed, so the watchdog resets the unit. (3) Both properties are proven by tests at every level that can reach them: no feed from any other site after takeover, the sequence never trips the watchdog on a healthy run (worst-case chip and bus speed), and a hang injected in any step ends in a watchdog reset, not in a fed hang. Both are owner-marked "extremely important". |
| OR121 | 2026-09-30 | "The new system commands must go into the API and the website the same style as the already existing ones" |
| OR121.a | 2026-09-30 | Integrated — refines OR117.a. (1) API: two more `SystemCmd` enum values on `PUT /system` (`asy_webserver_service.py:494-501`), in `_SYSTEM_CMDS` (`:95`), dispatched by `_dispatch_system_cmd()` and answered in the same envelope and results (`"Valid"`, `"Invalid"`, `"Failed"`) as `reboot`/`bootloader`/`mempause`; no new route, field, key or response shape. (2) Website: two more options in the existing "System Command" dropdown (`_SYSTEM_COMMAND_GROUP`, `buildgen/definitions.py:55-62`), labels "Reset to defaults" and "Erase FRAM", sent with the same Apply button; no new group, control or dialog. OR117.a (3)'s confirmation step is overtaken (the existing commands have none); a confirmation for every destructive command alike is an agent proposal for the OR2.c review, not part of the decision. |
| OR122 | 2026-09-30 | "They must receive the full  types of unit tests, also including watchdog handling. No dialog required, it's secured by requiring the word of the action being sent over the API, not just a call" |
| OR122.a | 2026-09-30 | Integrated — refines OR118.a and OR121.a. (1) The two commands get every type of test the project uses, at each level that can reach it: function (each command does exactly its purpose), every refusal and error path, concurrency and race (the OR119.a states), bus and storage hazards, the watchdog handling of OR120.a (takeover, no other feed, a healthy run never trips, a hung step is not fed), power loss per step, and the standing gc and `MemoryError` bars. (2) No dialog, and none proposed: the agent proposal of OR121.a for a confirmation is withdrawn. The safeguard is the API itself: a command runs only when the request carries its exact action word as the `SystemCmd` value (the dispatch compares the whole string against `_SYSTEM_CMDS`, `asy_webserver_service.py:507`; no alias, prefix, case folding or number), so a bare call does nothing; the words are chosen to name the action unmistakably, and a test pins that near-misses are refused as `"Invalid"`. |
| OR123 | 2026-09-30 | Answer to "How should the dev board test the second CRC mode?" (options: (a) a `crc` setting per loopback in the TOML, the firmware runs without CRC and a flash-tier script runs CRC16 over the same jumper, no test-only code in the firmware; (b) a runtime mode switch in the loopback driver; (c) a second pair, impossible): "Option a." |
| OR123.a | 2026-09-30 | Integrated — confirms OR116.a's TOML reading. (1) Each `uart_link` instance takes a `crc` key (none or crc16), buildgen refuses a pair whose ends differ; `dev.toml` ships none. (2) L3: a device script builds its own CRC16 pair over the same crossover jumper, the firmware stays untouched. (3) No runtime switch and no test-only code in the firmware (OR36). OR118.a (4)'s L4 run in the second mode (a reflash with `crc = "crc16"`) stays, behind `flash_cycle`. |
| OR124 | 2026-09-30 | Answer to "Should \"Reset to defaults\" include the Wi-Fi settings?" (options: (a) yes, everything; the device comes back as the hotspot with the default hotspot password until set up again; (b) keep "Wi-Fi & Identity"): "Yes, option a." |
| OR124.a | 2026-09-30 | Integrated — confirms OR117.a's reading: the reset deletes every schema-backed `config_<name>.cfg`, Wi-Fi & Identity included (SSID, password, country, hostname); after the reboot the unit serves only its hotspot with the default password until reconfigured. SCD30 NVM is untouched. The L4 reset test saves and restores the dev board's config files inside the gated test (OR118.a (2)). |
| OR125 | 2026-09-30 | Answer to "How should the few twin scenarios that need control inside the running device be driven?": "Special test code in the twin runner: every scenario moves to the host, but the runner carries test-only code." |
| OR125.a | 2026-09-30 | Integrated — settles U25 Q2 as option (a). (1) Every webserver-concurrency scenario is driven host-side (G7/R19 met in full). (2) The twin runner (`digital_twin/`, never `src/` or the image) carries named instrumentation flags for the scenarios that need in-DUT control: holding a closing connection's slot (today a rebind of the webserver's `_close_writer`), stalling the DUT's loop, and reading slot and backlog state (`_open_conns`, `_backlog`). This is a stated G7/R01 exception for the runner alone, of the same kind as the UART crossover wiring's `poller` rebinding; product code gains no hook (OR36). (3) Each flag is test-only, named as such, off by default, and a check keeps it out of the production entry path. |
| OR126 | 2026-09-30 | Answers to the four open questions and the corrections: (1) the generated `main()` keywords: "a - they are worth for more than just testing."; (2) debug logging with a connected USB host that does not read: "a" (accept as a debug-mode limitation), asking to confirm it occurs only with a host that opened the port and does not read, never when merely plugged in and enumerated, never without a USB host; (3) reboot and bootloader on the controlled shutdown sequence: "a"; (4) wake the LED-pause task on change: "b" (keep the one-second check); "Corrections: all OK." |
| OR126.a | 2026-09-30 | Integrated — (1) U25 Q1 → (a): `cfg_path`, `debug`, `web_host`, `web_port` stay on the generated `main()` as documented manual-start options, not test-only artifacts under OR36 (A.U25.69 firm). (2) U19 Q2 → (a): at a raised debug level a connected, non-reading USB host may stall each console write up to 500 ms; documented for bench sessions, no code, tests cover the shipped level (A.U19.23). Confirmed at v1.29.0: a write waits only while the host holds DTR, i.e. a host program has the port open (`shared/tinyusb/mp_usbd_cdc.c:111-137`, TinyUSB `cdc_device.c:144-148, 426-433`); without DTR (plugged in and enumerated only, port closed, or no USB host) the TX FIFO is overwritable and a write never waits. (3) OR119.a (5) accepted: `reboot` and `bootloader` run the same controlled shutdown sequence as the two new commands (no apply step). (4) A.U22.03 withdrawn; the one-second LED-pause check stays. (5) Accepted corrections: OR90.a (1)'s "seven" reads five (the marker removal unchanged); CLAUDE.md's "Known hang cause" mechanism is replaced by the proven one (the fakes answer `GET_FILENO` with 0, so a real poll watches stdin; the bounded-fake rule stands); the history-pill border cue is dropped; UART controller re-init is not a recovery rung (U17 Q1 (a)). |
| OR127 | 2026-09-30 | Answer to "Should the secret scan cover `arduino/`'s history?": "No, it stays fully out of the audit." |
| OR127.a | 2026-09-30 | Integrated — confirms OR5.a (3): the history secret scan (A.U29.04) excludes `arduino/` by path; no finding about its contents, no reading of it. |
| OR128 | 2026-09-30 | Answer to "Keep showing which task ended last on the API?": "(a) Yes: publish it as `LastTaskEnd` in `/status`." |
| OR128.a | 2026-09-30 | Integrated — settles U32 Q1: the supervisor's last task end (task name and time) is published as `LastTaskEnd` in `GET /status`, the refactor's successor of the legacy `Task_LastErr` value (G9/R05, "same top-level features"); A.U32.06 firm, co-landing with A.U2.08/A.U3.06; the website shows it where the legacy value was shown, in the existing style. |
| OR129 | 2026-09-30 | "Write down one more important step for the actual implementation phase: - Check all external dependencies for updates - both modules, repos and tooling, just everything. - If you find updates, carefully check what was changed. - Solve possible breaking changes without any regressions. - Check for opportunities, improvements, fixes we can profit from and update our code accordingly. - Check especially for fixes we needed to implement workarounds for, if they were solved upstream, apply and fix no longer needed workarounds to clean implementations. Select an advantageous place in the implementation queue for the updates. If you implement things due to such updates, adhere to our existing guidelines and rules, as well as to those we defined in this session." |
| OR129.a | 2026-09-30 | Integrated — LEAD/R33. (1) Place: a dependency-refresh step inside B0 (U0), right after the baseline is recorded and before the first B1 change — every later unit then lands on current versions and is measured against a known baseline; a short second check at B5 (U37) catches releases made during execution. (2) Scope, everything external: the MicroPython pin (and through it lwIP, cyw43, pico-sdk, mbedtls), the ARM toolchain and every other pin in `toolchain/versions.toml`, the vendored Microdot (re-vendored only as an unmodified upstream tag, never edited), the MicroPython stub packages, every Python dev tool and `uv.lock`, Node (`.nvmrc`) and every npm package, the GitHub Actions pins, and any other fetched source. The legacy tree and `arduino/` are out (reference-only / out of scope). (3) Per update: read the upstream changelog and the diff that matters to this repo; fix breaking changes with no regression (every level at both GC stages against the B0 baseline, lint and typecheck clean; a ruff/mypy upgrade's new findings are decided one by one, never blanket-ignored); take the fixes and improvements the project profits from. (4) Workarounds first: each standing workaround is checked against the new upstream and, where fixed there, removed for the clean form — the modlwip `ERR_MEM` override (issue 19704), the stub repairs in `scripts/typecheck.sh`, the `MICROPY_ASYNC_KBD_INTR` override and the other `toolchain/micropython_overrides.py` anchors, the GCC 14 mbedtls workaround, the `unix_port_gc_unwedge` defence, zizmor's `self-repository` disable (actionlint syntax support), the Timer stub gap, `getaddrinfo()`'s timeout status and the `I2C`/`SPI` `deinit()` facts. (5) Rules unchanged: tools stay pinned; CLAUDE.md's version-bump re-check practice runs and its SPEC F.5 record is updated; the `uv.lock` merge check; a BACKLOG entry for the owner's chroot run; every A-L action citing a pinned upstream source line is re-checked against the new pin before it is executed; a firmware version change is validated on hardware in phase C under its own go-ahead. |
| OR130 | 2026-09-30 | Answer to "May the supervisor feed once more before a failure-budget reboot?" (options: (a) yes, at the first task end past the budget it feeds once, then stops feeding one-way and arms the reboot, so the controlled reboot lands before the watchdog with FRAM paused; (b) no, the scan stops but does not feed and under load the watchdog may reset mid-write): "Watchdog feed: option a as recommended" |
| OR130.a | 2026-09-30 | Integrated — settles U31 Q1, A.U31.07 firm. The supervisor escalates at the first task end past the task-error budget: it feeds once (inside the supervisor loop, only while it does not hold `_feed_owned` for the controlled sequence), then stops feeding one-way and arms the reboot. Refines G5/R02 ("… or the task-error budget is exceeded, the supervisor feeds once and then stops feeding one-way") and OR31.a (3) (the supervisor loop holds this second, budget-escalation feed call; a test pins both call sites and nothing else); OR120's rule holds, since a blocked loop cannot reach either call. |
| OR131 | 2026-10-01 | Answer to "Vendor Microdot's upstream stubs inside `ext/`?" (options: (a) yes, in U0's re-vendor of the same tag, byte-identical and hash-pinned, `ext/` still changing only by re-vendoring an unmodified tag; (b) a separate `stubs/microdot/`; (c) no stubs, the `microdot` ignores stay): "1a" |
| OR131.a | 2026-10-01 | Integrated — settles GEN Q1, M.GEN.050 firm under option (a): upstream's `typings/microdot/` stubs of the pinned tag land byte-identical in `ext/typings/microdot/` in U0's re-vendor commit, hash-pinned with `ext/microdot.py`, never edited; the `microdot` import ignores leave `src/`, tests and generated code; CLAUDE.md's vendoring rule names the stub files. Refines OR24.a (2) ("`ext/` never touched" means never edited, re-vendoring an unmodified upstream tag stays the one way it changes) and G8/R61. |
| OR132 | 2026-10-01 | Answer to "Darken three light-theme status colours for AA contrast?" (options: (a) apply: same hues, slightly darker success/danger/warn at ≥ 4.5:1, a 3:1 control border and `color-scheme`; (b) border and `color-scheme` only; (c) nothing): "2a" |
| OR132.a | 2026-10-01 | Integrated — settles GEN Q2, M.GEN.062 firm: the light-theme success/danger/warn tokens darken to ≥ 4.5:1 on their backgrounds with the same hues, a control-border token at ≥ 3:1 and `color-scheme: light dark` land in U23, with the token test. Refines OR94 ("don't change the current look") — an AA contrast correction at the same hues is not a look change — and LEAD/R10, G7/R40. |
| OR133 | 2026-10-01 | Answer to "`test.sh` usage and setting errors: exit 2 like every runner?" (options: (a) exit 2 for an unknown argument, a bad `GC_THRESHOLD`, a bad timeout variable and a bad heavy-file list, one rule across all runners, `test_test_sh.py`'s rejection tests expect 2; (b) keep exit 1 in `test.sh` as E.10's named exception): "I take: (a) Recommended: exit 2" |
| OR133.a | 2026-10-01 | Integrated — settles SCR Q1, M.SCR.035/.045 firm: every runner exits 2 on a usage or setting error (SPEC E.10), `test.sh` included; A.U7.06's new checks exit 2, not 1; E.10 lists no exception. Refines G8/R38. |
| OR134 | 2026-10-01 | Owner direction on execution pace: "Running the CI scripts locally takes most wall clock time. As it is script execution, it costs close to no tokens. Savvy planning when to test which scope in which order and in which pace, combined with high parallelization could help reduce time without touching quality or raising token usage" |
| OR134.a | 2026-10-01 | Integrated as LEAD/R34: the A-C2 work order carries a test schedule — scoped runs first inside a unit (from each change's Blast field), the full gate on every unit's final tree unchanged, background runs on worktree snapshots while independent units proceed, port-binding suites isolated by network namespace (proven equal to a serial run in U0 before relied on) or serialised, GitHub CI as a parallel lane, hardware rounds batched. No gate is weakened; agent parallelism stays at OR107's limit. |
| OR135 | 2026-10-01 | Owner direction on the A-C review: "When you are in the stage of preparing my review, be aware that I will do that review alone. So keep it at a level where I won't need to ask for details for every topic, but at the same time not overwhelming, not exhausting, human-oriented and friendly, so it will be a rewarding task for me." |
| OR135.a | 2026-10-01 | Integrated as LEAD/R35: the review package is self-contained and layered — a short overview first, then one page per topic in plain language with the decision, why, what changes for the owner and the consequence of saying no; detail stays one step away, never in the main path; decisions are grouped and pre-sorted by weight so routine ones can be approved as a batch. |
| OR136 | 2026-10-01 | Owner comment in the A-C review (area "System and memory safety"): "A missing config file writes nothing (the defaults stay in RAM until your first change) - does that mean that after a fresh flash or a flash erase, no config files are written at all until something is changed? This is not really intended, if the file is genuinely missing, it shall be written once with defaults." |
| OR136.a | 2026-10-01 | Integrated — supersedes OR71.a (2)'s "a first boot with no config file writes nothing" clause (most recent owner decision wins). (1) A config file that is genuinely absent (open fails with ENOENT) is written once, at that boot, with the schema defaults, through the same compare-before-write path as every other write; after a fresh flash or a filesystem erase every module's file therefore exists after the first boot. (2) Unchanged: an unreadable or corrupt file is never overwritten; a bad, missing or unknown key is repaired by at most one write per boot (OR71.a (2)). (3) A command-only schema persists no field, so it has no file to write; its absence stays a printed note. (4) Wear: one write per file per fresh filesystem; a test that boots a fresh filesystem reaches that write as a prerequisite, not as the write under test (CLAUDE.md wear rule). Carried into the merged changes before B0 with the other review answers. |
| OR137 | 2026-10-01 | Owner answer in the A-C review on the dropped-connection counter (`HTTPDropped`): "ResetErrors shall clear it, but more important: I would like the idea of showing the last 24h sliding through, so every count that raises the count will keep inside for 24h after happening and then be removed. But only if there is an elegant way to do this without allocating memory dynamically. Maybe something like using 24 hourly counter bins, shifting through, with 1h resolution (that would be enough)?" |
| OR137.a | 2026-10-01 | Integrated — (1) `HTTPDropped` reports the web connections dropped in the last 24 hours, kept in 24 hourly bins: one fixed 24-entry integer array allocated once at construction, so no event, read or hour change allocates. A drop adds one to the current hour's bin (each bin capped at `COUNTER_CAP`); the bins advance lazily on the next drop or read, from the device's uptime seconds (the `SysUptime` count, monotonic and untouched by NTP steps), zeroing every hour passed (all 24 after a gap of a day or more); the value is the sum of the bins, capped at `COUNTER_CAP`. A drop therefore leaves the window 23-24 hours after it happened. (2) `ResetErrors` clears all bins. (3) Each drop still traces once (A.5), without a running total. (4) The window is one small reusable primitive (an hourly window counter beside the other shared counters), entered in SPEC Part G's catalog and tested under a driven clock: the bin shift, a gap of a day or more, the cap, the reset, and no heap allocation per drop or read. (5) The field keeps its name; its description reads "in the last 24 hours, hourly resolution". |
| OR138 | 2026-10-01 | Owner answer in the A-C review on config files: "Unreadable or damaged files should be visible in some status field, not silently swallowed. And even such files must be deletable by the user when triggering the newly added \"delete config\" command." |
| OR138.a | 2026-10-01 | Integrated — (1) `/status` gains `ConfigFaults`: the names of the modules whose config file existed at this boot but could not be read, or was damaged (unparseable or invalid), an empty list when there are none. The set is fixed at the end of the boot `setup()` batch and bounded by the build's config stores; a module stays listed for the rest of that boot even when the boot repair rewrote its file. The module's persisted warning stays (one per boot). (2) "Reset to defaults" deletes every schema-backed config file whether readable or not: the delete never reads the file and does not depend on the store's readable state; a failed delete is logged and the command answers "Failed" [lead correction, 2026-10-05: the command is answered at acceptance, before the deletes run in the shutdown sequence, so a failed delete is logged and shows as reset reason 9 (command incomplete) at the next boot]. After the reboot each file is written once with its defaults (OR136.a). |
| OR139 | 2026-10-01 | Owner answer in the A-C review on the tick-rollover round: option 1, "Test build with a starting offset" (one extra flash; a run of about 1-2 hours instead of 12.4 days; it also crosses the 49.7-day 32-bit wrap). |
| OR139.a | 2026-10-01 | Integrated — (1) The rollover round runs a test build of the dev image that differs from it by one build define, applied by `toolchain/micropython_overrides.py` as a test-only override: `mp_hal_ticks_ms()` (MicroPython v1.29.0 `ports/rp2/mphalport.h`, which also feeds the soft-timer queue and lwIP's `sys_now()`) returns the time since boot plus 2**32 ms minus 15 minutes, so `time.ticks_ms()` (period 2**30) and the 32-bit millisecond count both wrap about 15 minutes after boot. The hardware timer is never written (RP2040 datasheet 4.6.2: the SDK expects it to increase monotonically). (2) One flash cycle, counted in the flash budget; the build info names the override, and a check fails any release build that carries it. (3) The rollover runner flashes the test image, polls for about two hours (the wrap plus margin) with the same health verdicts, then the next round flashes its own image. (4) The driven-clock proofs in the unit and twin tiers stay. (5) The round no longer needs its own session: the hardware phase becomes two sessions, the round joining session 1, and the release proof stays last. The override's anchors are re-verified with every MicroPython version bump (CLAUDE.md standing practice). |
| OR140 | 2026-10-02 | The owner's answers on the A-C review page: all 15 significant and 53 moderate decisions answered one by one (45 fine, 5 change, 18 with a question or an addition); the routine group left unanswered. Stored verbatim, with each note, in `audit/review/answers.json`. |
| OR140.a | 2026-10-02 | Integrated — every "fine" stands as an owner-confirmed decision; the notes add or change: (1) bench Wi-Fi password: a throwaway password used once, passed plainly; no interactive-mode workaround (still never committed). (2) the console-starvation bench test runs only behind the persistence-write flag. (3) the website asks for confirmation before every system command and before clearing the error history; the API stays one command per request. (4) `abs_humidity()`/`rel_humidity()` stay ("useful, complete the functional suite, small, lightweight"), their tests aligned with the other helpers' and the helpers with the no-clamp rule. (5) internal LED requests may queue because they are bounded in number and rate; external ones are refused when busy, and the refusal tells the caller to retry. (6) the old work-in-progress folder's code counts as reference for the owner's intent unless something states otherwise. (7) every layer that meets a fault keeps its own persisted entry, as today, so the history shows how far a fault reached; the planned "one entry per fault" change is dropped. (8) reset-reason codes are clickable on the website like errno/wrnno. (9) when the bench board is not in its standard state, a console message says what was found and which repair options exist. (10) `HTTPDropped` per OR137.a. (11) the MicroPython stub version moves with every MicroPython bump, enforced by a check. (12) no SCD30 write can happen while a system-command sequence runs, proven watertight by tests (only API-triggered writes exist, and API commands are refused while the sequence runs). (13) the twin gets a local NTP responder, also used for new NTP-client unit tests (function, error handling, biting, regression). (14) unreadable/damaged config files per OR138.a. (15) the browser's Back button walks back through the sensor subpages opened from the menu. (16) the website shows a sensible number of decimals per value (2-3), configured in the website configuration and derived from the value's source (schema or tagged config); the API keeps full resolution. (17) the Wi-Fi-off LED pattern respects the Wi-Fi LED setting (silent when off). (18) no build except `dev` has anything special; leftover WoZi-specific wording from the promotion is removed from the docs. Open, answered back to the owner in the conversation: the five hand-run hardware rows, the idle poll rate, the build date in a reproducible image, where the test-only device-file keys live, and the UART frame lost during a flash erase. |
| OR141 | 2026-10-05 | Owner answer, in the conversation, to the four questions left open on the A-C review page and the replies to their notes: "Concerning the answers to my questions: do all as you suggested, especially for the multiple choice questions - keep keys in the device files, and UART in the DMA ring buffer, but keep a strict eye on how that integrates with the heap allocation and fragmentation; to the usual unit tests also add hammering and concurrent load tests, and think about how we can test the interrupts off situation without actually writing the flash." |
| OR141.a | 2026-10-05 | Integrated — every recommendation stands as an owner decision. (1) `bench = true` and `hardware_family` stay in the device files' `[device]` section; the build checks both and never emits them. (2) The dynamic-import ban covers the firmware graph: every module frozen into an image and everything it imports. The host and test loaders that load by path or name (`tests_scripts/_script_loader.py`, `buildgen/validate.py`, `digital_twin/run_generic_integration.py`, `tests/_sensortask_scenarios.py` and the other current sites, each by name) are listed exceptions in SPEC F.1, a check fails on any site outside the list, and they need no code change; this supersedes the whole-repo reading of 2026-09-26. The once-at-module-load import rule is unchanged. (3) `voc_algorithm.py` stays a literal port: upstream names, casing and order. It is the one named exception to both the naming rules and the member-ordering rule; only the class other modules import follows the scheme. (4) Each UART link receives through a DMA ring, so no frame is lost while a flash write holds interrupts off (`ports/rp2/rp2_flash.c:170-174`, v1.29.0; W25Q16JV tSE 45/400 ms, tPP 0.4/3 ms). (a) A DMA channel paced by the UART's RX DREQ (RP2040 datasheet 2.5.3.1: UART0_RX 21, UART1_RX 23) writes into a naturally aligned power-of-two RAM ring (CTRL.RING_SIZE on the write address, 2-32768 bytes, 2.5.1.3 and the CH0_CTRL_TRIG register; UART DMA interface 4.2.5). (b) MicroPython's receive path is kept off the FIFO. `machine.UART` enables the RX and RX-timeout interrupts at init (`machine_uart.c:455`), and its IRQ handler, `any()` and `read()` all drain the FIFO (`:162-188, 506, 604`). So after every init the driver clears RXIM/RTIM in UARTIMSC and sets RXDMAE in UARTDMACR, and it never calls receive-side `any()`/`read()`/`readinto()`/poll. Transmit stays on `machine.UART`, whose receive buffer drops to its minimum. (c) Progress is read from TRANS_COUNT only, never WRITE_ADDR, which reads wrong during ring transfers (RP2040-E12). A second, chained channel reloads the count when it runs out, so reception never stops. The reload value stays at most 2**30 - 1, so reading `DMA.count` (`rp2_dma.c:392`) never allocates a big int. The fill level is the modular difference of totals. A lap (more unread bytes than the ring holds) is detected, counted and handled as J.7's receive overrun (resync), never read as data. (d) Heap: the ring is allocated once, at construction inside the boot setup batch (I.4(f.1) placement), with any alignment padding fixed and measured. It stays referenced for the program's life, and a task restart never reallocates it. Soft reset is safe because `rp2.DMA` has a finaliser that aborts the channel and soft reset runs `gc_sweep_all()` (`rp2_dma.c:365, 637-673`; `main.c:303`), proven on the bench. No byte, read or frame allocates: a read copies by index into the existing frame buffer, never through a slice. The net heap cost and the largest free block are measured before and after on the twin and on dev, and recorded in SPEC I; the boot contiguity test covers the ring. (e) Size: the larger of today's floors (one framed frame; one poll interval) and what the peer can send during the longest synchronous flash write under stop-and-wait (one frame plus every retransmission its timeout and backoff fit), rounded up to a power of two. It is derived and refused like `rxbuf` today, never a bare number. (f) `ready()` keeps its yield and its wait/idle rates (F.5.8/F.5.9), reading the fill level instead of `uart.any()`. No wire change: a "no C impact" changelog entry. (g) Tests. Unit: a time-driven fake DMA and UART register model fill the ring independently of the event loop; cases cover the count reload and modular wrap, a frame split across the ring end, a lap leading to an overrun, the mask cleared after every init, the refusals, and zero allocation per read at `gc.threshold(-1)`. Hammering: thousands of back-to-back transactions at the line rate with the ring at its fill boundary, plus random consumer stalls up to and beyond the bound (zero loss within it, a detected overrun beyond it). Concurrent load: both dev link instances under traffic alongside the webserver hammer, FRAM log writes and config PUTs, with the twin's flash write stalling the loop for the datasheet time; both GC stages, zero MemoryError. Bench, interrupts off without writing flash: a device script calls `machine.disable_irq()` and busy-waits on `time.ticks_us()` (hardware timer, readable with interrupts off) for 3 ms, 45 ms, 400 ms and one window past the ring bound. Meanwhile the other UART, fed by its own DREQ-paced DMA channel so it keeps sending with interrupts off, streams frames over the crossover jumper. Every frame within the bound must arrive intact with UARTRSR OE clear, and the over-bound window must read as an overrun. A one-time run of today's interrupt-driven path in the same setup shows it loses bytes (not a permanent control arm, OR21.a (2)). One real config write during traffic stays optional behind `--allow-persistence-writes`. (5) The replies to the five notes stand as written on the page: the three kept one-time measurements and the two dropped; the idle poll rate at 100 ms, its measurement owed; the build date as a build input with the two-build reproducibility check. |
| OR142 | 2026-10-05 | Owner answer, in the conversation, on whether the dynamic-import ban covers MicroPython's own modules bundled into the image: "Option 1, record the MicroPython sites in F.1. But the places you named so far are all harmless." |
| OR142.a | 2026-10-05 | Integrated — narrows OR141.a (2). (1) The ban covers all code this project writes, generates or vendors into an image: `src/`, `ext/`, the generated boot, device and website modules. That is zero sites at HEAD across all six devices, and the check enforces it per image. (2) MicroPython's own bundled modules are platform code, never edited. SPEC F.1 records their two sites as platform facts: `extmod/asyncio/__init__.py:29` (the lazy loader, run on first use of `Lock`, `Event`, `wait_for`, `gather`, `start_server`) and micropython-lib `dht.py:14` (frozen by the board manifest, never imported by this project); both are re-read at every MicroPython version bump. (3) The host and test exceptions are listed by name in F.1: `tests_scripts/_script_loader.py`, `tests_scripts/conftest.py`, two `tests_scripts/` tests, `buildgen/validate.py`, `digital_twin/run_generic_integration.py`, five `tests/` helpers, and `ext/freezefs/ffsextract.py` (vendored, build-time only; its extract mode is never used). The owner judges every named site harmless; none needs a change. |
| OR143 | 2026-10-05 | Owner's go-ahead note on the A-C review page, status "withheld" (execution not yet approved): "I want one parked item to be fixed: the UART chunking for large allocations. We already applied a very similar mechanism to the Webserver - a reasonably defaulted chunk size constructor argument which limits the maximum size of contiguous allocations. This shall be added here as well. A general maximum buffer size, catching uncapped heap flooding in general if too large incoming transmissions occur, is also to be implemented - probably this goes well along with the ring buffer size. Special care must be taken for the ring buffer allocation, this should probably happen during the init phase where the long term survivor allocations are done with the interleaved gc.collect calls, so the ring buffer lands at a benign place of the heap." |
| OR143.a | 2026-10-05 | Integrated — supersedes OR69.a (7)'s deferral; the parked item "Chunking large UART allocations" becomes work, and its BACKLOG owner question (M.DOCS.067 entry 1) is dropped. (1) `UART_Comm` takes a `chunk_bytes` constructor argument with a reasoned default, as `WebserverService` does (`asy_webserver_service.py:108, 312`). An incoming train that the caller did not give a destination for (`_accept_set()` for a don't-care `set_callback`; `_get_unlocked()` for `uart_get(exp_size=None)`) is assembled in pieces of at most `chunk_bytes`, so no receive allocation is larger than that. The pieces sit in a small shared primitive with length, iteration and copy-out, checked first against SPEC Part G's catalog (the webserver's `_PieceWriter` is the model). A caller-supplied destination (the zero-copy path) is unchanged. (2) A general receive cap: `max_transfer_bytes`, a constructor argument with a default. A train whose declared size (CHUNKS and `exp_size`) exceeds it is refused before anything is allocated, through J's existing rejection (withheld ACK), and logged once, so a large or hostile transmission cannot flood the heap. `readline_until_complete()` gets the same cap: it no longer grows by concatenation; over the cap it discards the line and returns None with a logged error. The cap and the DMA ring size (OR141.a (4)) are declared together in the bus/instance TOML and checked together by buildgen; they stay two values, since stop-and-wait means the ring never holds a whole transfer. Both count in SPEC I's heap budget, and the memory rule's caught-`MemoryError` sites at these allocations go. (3) Refusing an oversize train tightens receiver validation only: a Class A changelog entry ("must be mirrored in C"), of the kind CLAUDE.md prefers. (4) Tests: unit — no receive allocation exceeds `chunk_bytes` (largest-block measurement), refusal before any allocation, a maximum-size train assembled correctly, the readline cap; hammering — repeated maximum-size and over-cap trains; concurrent load — trains alongside the webserver hammer, both GC stages, zero MemoryError; bench — a maximum-size transfer over the crossover jumper. (5) The DMA ring is allocated in the link's `setup()`, a unit of the one-time setup list, so the boot placement reset (I.4(f.1)) puts it with the long-lived survivors. The boot contiguity test asserts where it lands, and the before/after heap measurement covers it. (6) The go-ahead stays withheld: execution (B0 onward) remains blocked. |
| OR144 | 2026-10-05 | Owner, in the conversation: "Yes, test if you can push to the datasheet repo. I generally give you permission to push to it." |
| OR144.a | 2026-10-05 | Integrated — the owner step "push access to `hundertvolt/datasheets` before U28" is done: standing push permission for the datasheet move (M.PROC.018, A.U28.35). Tested the same day: the repository is attached to the session with push access and a dry-run push was accepted; it is empty (no commits, no branches), so no real test push was made — the first push would become its default branch and could not be deleted. The move's initial commit creates `main`. |
| OR145 | 2026-10-06 | Execution go-ahead, in the conversation: "Then start the implementation now. Prefer accuracy before speed, use parallelization carefully and don't overdo it in the context of implementation. Parallelize strongly in the context of running unit tests and suites, as you already planned, to save wall clock time on computationally cheap, but slow processes. With this step, there is a paradigm change: the pillars and rules and specifications we wrote and refined are no longer subject to change, but become effective and need to be adhered to inside the implementation process. This is my explicit go-ahead for the full implementation part which runs up to the point where real hardware tests become the next required step. Keep me updated on the progress." |
| OR145.a | 2026-10-06 | Integrated — (1) phases B0-B5 run now, in the work order; phase C waits for its own go-ahead per session (OR5.a, CLAUDE.md). (2) Rules, pillars and SPEC Parts are applied as written; a conflict found during execution is parked and passes A-C as a delta (OR2.c, OR106.a), never settled by editing a rule. (3) Implementation agents stay few (at most OR107's 4, usually fewer, on disjoint files); test suites run in parallel up to the host's cores once U0 proves port isolation, serialised under the port lock until then. (4) Audit baseline: `origin/main` at the go-ahead, `798e5a7`. (5) Progress reports to the owner at each unit close. |
| OR146 | 2026-10-06 | Requirement given during execution, in the conversation: "One thing I want to mention. Probably you already planned it that way, but just to be sure - if the ring buffer of the UART ever is filled / overflows, the sender must be aware that something went wrong. This must be always reliable, even if interrupts are disabled in all that time. It's more about detecting such conditions, the answer to the sender can be just the failed transmission as many other conditions already use." |
| OR146.a | 2026-10-06 | Integrated — checked against the plan: the DMA ring of M.SRC_NET.221/.222 already receives with interrupts off and detects a ring lap from the DMA counters, failing the frame so the sender's transaction fails; the gap was a hardware FIFO overrun before the ring (UARTRSR OE, which `machine.UART` ignores, `machine_uart.c:170-172`, v1.29.0), which only the bench read. Folded into M.SRC_NET.221 as (6): OE read at the choke point and handled as the same receive overrun, tests at L1, twin and bench; no wire change; changelog Class A (receiver-side tightening). |
| OR147 | 2026-10-06 | Standing instruction during execution, in the conversation: "While implementing and writing code and tests, always keep an eye open for such tiny oversights - all places, not just UART. Do a scan if you found all such cases after each implementation throughout the process. This is really important, as it touches several of our core pillars (clean error handling, self-healing, etc.)" |
| OR147.a | 2026-10-06 | Integrated — `audit/sweeps/silent_failure_scan.md` defines the scan (seven classes, read against the pinned sources, a class found once swept project-wide, each finding checked against the work order and fixed in its unit or parked as an A-C delta). It runs after every unit's implementation, before the unit closes, and its result goes into the unit's record; one project-wide pass runs at the start of phase B. Implementing agents watch for the same classes (`exec_prompt.md` item 8). |
| OR148 | 2026-10-06 | Standing instruction during execution, in the conversation: "Generally, also look out for issues in special situations (like bootup, reset countdown, Flash writes, and anything else) in these checks, they also must be stable and well handled according to our rules and pillars. So also keep an extra eye on all operating modes, not just plain operation!" |
| OR148.a | 2026-10-06 | Integrated — `audit/sweeps/silent_failure_scan.md` gains an operating-mode section (boot, reset countdown, flash writes, FRAM writes, network, sensor modes, supervision, runtime reconfiguration, UART link, load and shutdown); every class is checked in each mode and at each transition, a finding records its mode, and a unit's record names the modes checked. `exec_prompt.md` item 8 and the REGISTER unit-close rule carry the same. The two running first-pass scan agents were extended to cover the modes. |
| OR148.b | 2026-10-06 | Completeness, after the owner asked "Is this really the complete list of situations?": the first list was enumerated, not derived. The mode section now names a derivation every unit re-runs (state in the changed code, REST commands and config fields, RP2040 and peripheral reset and power paths from the datasheets, lifecycle, environment, then pairs of rare modes), and adds the modes the first list missed: first boot and factory state, after a firmware change, each kind of restart including soft reset with live peripherals, power loss at any instruction, boot loop, long uptime, DHCP/IP change, NTP never reachable or stepping backwards, REST client edge cases, a peripheral resetting on its own, a wedged bus, outputs, degraded running, the USB console, interrupted host tooling. |
| OR148.c | 2026-10-06 | After the owner asked "Are you sure to have found really all special situations now and the running agents really acknowledged them if you told them mid run?": the two first-pass agents' transcripts show both read the extended mode section and acted on it, but what they had read before the message was not seen through the modes, so it does not count as covered. The scan now runs two crossed passes (by site and class, by mode as an end-to-end scenario); a mid-run brief change never counts for what was already read; the mode list is checked against an independent blind derivation, and a mode found later is swept across units already closed. A dedicated by-mode pass with the full list in its initial brief follows the first pass. |
| OR149 | 2026-10-06 | Owner, in the conversation: "One important addition: usually, the fixes required for such reliability (if required at all, if not already safe inherently) are minimal, low complexity. It's more about having such situation in mind and giving the code a simple inherent way of handling it." |
| OR149.a | 2026-10-06 | Integrated — the scan procedure (`silent_failure_scan.md`) and `exec_prompt.md` item 8 first ask whether a site is safe by construction, then for the smallest inherent change; new state, flags, timers, tasks or protocol fields only when nothing smaller closes it, with the reason. The parked first-pass rows were re-read under it: SF-B1 becomes a per-owner CRC seed (no new bytes, deterministic detection), SF-B3 first checks whether the existing persisted errno suffices, SF-B14 becomes a display change. |

---

## 4. Method

### 4.1 Execution order (phases; details and driving requirements in `audit/CONSOLIDATION.md` section 2)

- **Phase A — Consolidation** (before the go-ahead): requirement passes 1-2, harvest pass 1, the
  decision-provenance sweep and allover pass 2 (the register, `audit/pass2/`) are done; passes 3+ run
  the question-raising scans (OR52.a (5)). Exit: every foreseeable question answered (OR2.b).
- **B0 — ENV** (4.6): build the toolchain, run every level once at both GC stages, record the baseline
  (counts, timings, peak memory, coverage, warnings), build the do-not-reopen index (`DOC.T14`), commit
  the sweep scripts, and fix the two lens inputs — `SEC.T01` (the threat model, written from PQ5) and
  `PAR.T01`/`PAR.T02` (the legacy inventory, from the consolidation legacy scan); write the five
  prevention rules and the reviewed-decision tag form into CLAUDE.md with their `tests_scripts` check
  (OR68.a (4), LEAD/R16). Nothing is audited against an unmeasured tree. Then the dependency refresh (OR129.a, LEAD/R33): every external dependency updated against that baseline, workarounds fixed upstream removed, before the first B1 change; a short second check at B5.
- **B1 — Foundations**, in this order: legacy move to `legacy/`; error-number catalog; central
  log-repeat rule; compare-before-write primitive; config objects and `max-args`; one-source website
  definitions; tier ladder and runner summary block; `@tunable` scheme.
- **B2 — File-by-file pass**, per area, groups in dependency order: foundations `XCUT`, `CORE`,
  `ALGO`, `BUS`, `PLAT`; subsystems `SENS`, `STOR`, `UART`, `NET`, `REST`, `GEN`, `TOOL`, `LED`;
  consumers `WEB`, `TEST`, `TWIN`, `HW`, `SCR`, `CI`; synthesis `SEC`, `MEM`, `PERF`, `PAR`, then
  `DOC` and `LIC` (they absorb every other area's doc findings). `LED` (two files) runs first as the
  calibration pilot: cost, convergence rule, register format.
- **B3 — Test campaign**, **B4 — Docs**, **B5 — Close of execution**: `audit/CONSOLIDATION.md`
  section 2.
- **Phase C — Hardware rounds** and **Phase D — Close**: each round with its own go-ahead; plan and
  `audit/` deleted after the last one; one merge into `main`.

Each unit works through its register lines (`audit/pass2/INDEX.md`, by unit) together with its topics
and seeds. No owner stop-points in B (PQ8). After every unit: an OR6.a sync point (commit, push, full local
suite at both GC stages, CI green via event hooks, register and PR status note), then continue.

**Units** (the register's header tracks each; "the lowest open unit" in 4.7 means the lowest number
not `closed`, together with every other open unit of its group):

| Unit | Content | Unit | Content |
|---|---|---|---|
| U0 | B0 ENV (4.6) | U15-U22 | B2 subsystems: SENS, STOR, UART, NET, REST, GEN, TOOL, LED re-check |
| U1-U8 | B1 foundations, in the order above | U23-U28 | B2 consumers: WEB, TEST, TWIN, HW, SCR, CI |
| U9 | B2 pilot: LED | U29-U34 | B2 synthesis: SEC, MEM, PERF, PAR, DOC, LIC |
| U10-U14 | B2 foundations: XCUT, CORE, ALGO, BUS, PLAT | U35-U37 | B3, B4, B5 (sub-units set at their start) |

- A **pass** is auditor A + auditor B + the arbiter's merge of the two (4.4); verifiers run per pass.
- `converged@sha`: the 4.4 convergence rule is met. `closed@sha`: converged, every register entry of the
  unit terminal, the per-area lens record filled (1.2) and the quality measure met.
- A pass with no committed auditor report is restarted from scratch, never resumed from memory.

### 4.2 Cross-cutting lenses (apply to every in-scope area; "N/A, because …" allowed)

| Lens | Question every area answers |
|---|---|
| L-CORR | Correct against the authoritative source (datasheet, RFC, MicroPython 1.29.0 source, Microdot v2.6.2 source, browser spec) — verified, cited, not recalled |
| L-EXC | Exception net complete: nothing raises out of a never-raise contract; every raise has a catching caller (Part D.2), including import time and the pre-`WDT()` phase (`XCUT.T20`) — within CLAUDE.md's no-blanket-asyncio-wrap rule; a real graceful-degradation alternative is implemented (OR26.a); hardware faults escalate by design (OR18.a) |
| L-CONC | Every lock, shared state, await point and interleaving; lock-hold spans containing sleeps or I/O; lock order |
| L-BLOCK | Nothing blocks the loop beyond its budget (Part D.5, F.3, F.5.8) |
| L-TIME | Timers (soft-callback drop, ONE_SHOT vs PERIODIC, alarm pool), ticks wraparound *and* the age of stored ticks values (`ticks_diff()` is only valid under 2**29 ms), deltas passed to `ticks_add()`/`sleep_ms()`/`wait_for()` and `Timer(period=)` values (`XCUT.T25`), timeouts vs the configured 8000 ms watchdog (8388 ms is the rp2 cap) |
| L-MEM | Allocation bounded and not client-controllable; churn on hot paths; long-lived placement (Part I) |
| L-LIFE | Every resource (socket, timer, task, file, lock, buffer, FRAM chunk) released on every path incl. cancel/restart |
| L-STATE | State machines complete: every state × event, including task restart, reboot, power loss, and cancellation at every `await` |
| L-DIAG | Every failure mode leaves persisted, attributable evidence (errcount/FRAM entry, `reset_reason` in `mem_backup()`, OR60.a) — or is recorded as knowingly silent; routine events don't churn the evidence; one event is one entry (OR56.a (1)); a repeated code spends no new slot (OR35.b) |
| L-TGT | The property holds in target semantics, not only on the 64-bit double-precision Unix port or the twin (float32, 31-bit small ints, soft-callback drop, IRQ-off windows, blocking UART reads) |
| L-COMPAT | UART frames stay stable; REST shapes, persisted config keys and file names are free until the release (one key scheme, OR58.a), stable or migrated after it (OR52.a (2), LEAD/R08); FRAM content need not survive a reflash (OR47.a (2)); no legacy migration (OR52.a (1)) |
| L-WEAR | Flash/NVM/FRAM write frequency and who can trigger it (REST, loops, tests) — and host I/O (CLAUDE.md's SSD rule) |
| L-SEC | Trusted home LAN (PQ5): unauthenticated writes and `bootloader` are documented limitations; malformed, partial or oversized input never crashes anything |
| L-API | D.10 consistency within and across files; naming, ordering, signatures (OR24.a); argument grouping and `max-args` (OR46.b); return conventions; Part G reuse |
| L-DEAD | Dead code, unused parameters, test artifacts in the product (OR36.a), unreachable branches, stale non-code entries (OR50.a) |
| L-TEST | Tests bite — proven by planted faults (OR16.a, OR19.a, OR21.a) — at every layer and level L0-L4 (OR25.a, OR45.a) |
| L-DOC | Code, comments and docs agree; comment cap; no dangling citations |
| L-PAR | Behaviour equals legacy or the change is documented as deliberate; a lost legacy function is restored (OR48.a) |

Every file additionally passes the pre-merge gate (OR51): correctness and robustness, specification
conformance, documentation hygiene and the design questions.

### 4.3 Techniques catalogue

- **Line-by-line reading** of every in-scope source file (full reads, never grep-only), with the
  callers and callees of each function read alongside (Part D.0).
- **Source and documentation verification**: clone MicroPython `v1.29.0` (and Microdot `v2.6.2`) into the
  scratchpad; every runtime claim cites a file and line there *and* is checked against the current
  MicroPython, rp2-port and Microdot documentation (CLAUDE.md standing practice).
- **Datasheet verification** from `datasheets/` (text already extracted during planning to the session
  scratchpad; re-extract in a new session).
- **Differential testing**: mock tier vs twin tier; Python VOC port vs Sensirion's C reference
  (`Sensirion/gas-index-algorithm`, reachable); float32 vs double arithmetic for every formula that runs
  on rp2; legacy vs `src/` published values from the same raw bytes, legacy run in scratch (PQ10).
- **Fault planting** (OR16.a (4), OR19.a (3), OR21.a (1), OR31.a (5); the technique already used for UART):
  per module, a small set of planted faults (flipped comparison, dropped call, swallowed exception,
  removed guard) in a throwaway worktree, the mutated copy shadowing `src/` on `MICROPYPATH`; each must
  turn a named test red; one record of which test catches which fault; targeted, not full mutation.
- **Fake-mutation sweeps**: remove one fidelity rule from a chip fake and check some test notices.
- **Fuzzing** — bounded and structural (enumerate shapes and boundaries, not brute-force volume, per
  CLAUDE.md's wear rule): `buildgen.build_model()` with mis-shaped TOML (expect only `BuildError`); REST
  request lines/headers/bodies; DNS/NTP reply parsers; UART frames; stored config JSON; FRAM chunk
  images.
- **Interleaving exploration**: scripted asyncio schedules for every lock-protected sequence found by
  `L-CONC`.
- **Budget arithmetic**: worst-case watchdog-feed gap, lock-hold per bus, request ceiling, FRAM layout
  vs chip size, UDP PCB count, alarm-pool count — computed from code, cross-checked by measurement.
- **Static sweeps** (grep/AST scripts committed under `audit/sweeps/`; outputs regenerated, not
  committed): error-code catalogue, timer inventory, lock inventory, `create_task` inventory, `repeat=`
  usage, cross-reference resolver for docs.
- **Representation-faithful scratch Unix port**: a third, scratch-only build with 32-bit objects and
  single-precision floats (if buildable) for ALGO/SENS arithmetic parity and allocation counts — not a
  toolchain change.
- **Cancel-at-each-await sweep**: for each multi-step coroutine, inject `CancelledError` at the k-th
  await for every k and assert the post-state invariants (`XCUT.T19`).
- **Loop-lag sentinel**: a task measuring how late `sleep_ms()` wakes, under combined worst-case load
  (`PERF.T09`).
- **Crash-point enumeration** on a twin FRAM image: power loss after every SPI transaction k
  (`STOR.T12`).
- **Clock-jump injection** in the twin: RTC forwards/backwards, `NTP_Offset_S` changes (`NET.T11`).
- **Third-party HTTP client matrix**: curl with `Expect: 100-continue`, chunked bodies, browser
  keep-alive (`REST.T12`).
- **Rogue DNS/NTP responder at the twin tier**, not only on the bench (`SEC.T11`).
- **Datasheet golden vectors**: e.g. SGP40 Table 10 ticks (25 °C → 0x6666, 50 % → 0x8000), SCD30's CRC
  example, default command CRCs.
- **IRQ-line fault simulation**: floating, stuck-low and bouncing SCD30 RDY / ISL29125 INT lines — mock/twin
  tier only; no GPIO fault-injection hardware (BACKLOG 8, SETTLED).
- **Gate mutation**: plant each failure class a gate claims to catch (zero-test file, missing footer,
  async test, early `sys.exit(0)`, a `memory allocation failed` log line, unexpected skip, wrong binary
  variant) and require a red verdict.
- **Ship-vs-test differential**: run the Unix-port suite against the staged, `TYPE_CHECKING`-stripped
  tree that actually gets frozen (`SCR.T10`).
- **Determinism diff**: generate every artefact under two hash seeds and two host Python versions;
  diff.
- **Workflow truth table**: per CI job, the outcome under each upstream success/failure/skip/cancel.
- **Dependency scan**: vulnerabilities and licences for `uv.lock` and `package-lock.json`.
- **Fake-clock and exhaustive checks**: the real timer sequencer under a fake clock for every generated
  device, and every period combination in the allowed ranges (OR47.a (3)); the recorded boot sequence of
  every generated device asserted in the twin (OR47.a (1)).
- **Write counters** in the fake filesystem and fake SCD30, outside the product code (OR42.a, OR42.c).
- **Dead-code tool** during the audit only, never added to `lint.sh`; its output plus a repo-wide
  reference search is a candidate list confirmed by hand (OR46.a (2)).
- **Help-vs-README diff** per tool (OR15.a (1)).
- **Execution** only in isolated git worktrees or scratch directories (section 4.6).

### 4.4 Multi-agent orchestration and convergence (parallel agents approved for the whole audit, PQ9 — not an execution go-ahead; wave size bounded by merge effort, accuracy before speed, OR107.a)

- **Roles**: *auditor* agents (read-only on the repo; one area or sub-unit each, one lens set);
  *verifier* agents (adversarial: try to disprove findings, by execution where possible, batched by file
  or theme); the *arbiter* (the main session: dedups, resolves contradictions between agents, assigns
  severity/status, is the **only writer** of this file and of the findings register; resolves conflicting agent
  results against sources, never by majority (OR7.a)).
- **Per-unit pipeline**: auditor A (full deep read) → independent auditor B with a different lens
  emphasis, not shown A's output → arbiter merges → verifiers → confirmed / plausible / rejected.
  "Plausible" is not terminal: it ends in one of 4.5's terminal statuses.
- **Git archaeology before flagging**: `git log`/`blame`/commit messages for the line in question, to
  find the owner decision behind it (many "odd" lines are settled decisions).
- **Convergence**: an area closes when two consecutive fresh passes (new agents, blind to the register
  until their own report is written, new lens emphasis) add no SEV1/SEV2 and at most one SEV3 after the
  arbiter's diff. Cap at 4 passes, then the arbiter decides under OR2.c and logs it.
- **Contradiction handling**: when two agents disagree on a fact, the arbiter checks the source
  directly (planning example: one survey said the hotspot timeout is 5 min, another 8 min — the class
  default is 5 but every `devices/*.toml` sets `hotspot_time_min = 8`; both were right about different
  things).
- **Auditor context** (the one definition; 2.3 points here): CLAUDE.md (auto-loaded); sections 0-4 and
  5.0 of this plan; its own area section; the full text of every topic/seed that section cites, marked
  "context only, owned by X"; its area's harvested notes (`audit/`, V10); the do-not-reopen index and the
  answered section 3; the text of every SPECIFICATION Part its References line names; from the B2 subsystems group on, the
  committed `audit/artefacts/` it depends on. A committed `audit/sweeps/packet.py <AREA>` assembles it
  (measured at `2a88cc8`: 34-46 KB of plan text per area, XCUT largest). Each auditor also gets its lens
  emphasis (A vs B) and reports in the register's field order minus the arbiter's fields (severity,
  status, verdict).
- **Blindness**: auditors work in a worktree at the audit baseline, created before the register exists
  or with `audit/REGISTER.md` removed, so "blind to the register" is enforced rather than requested.
- **Non-interference rules**:
  - Auditors and verifiers never write inside the checkout. They use the scratchpad or their own
    `isolation: "worktree"`. No force-push by anyone; `git pull --rebase` before every push.
  - Two agents that execute tests never share a worktree: `scripts/test.sh`, `npm test`,
    `build_website.sh` and the twin CI suite all write shared outputs (`frozen_modules/`,
    `build/generated_src/`, `digital_twin/*_state.json`, `tests/_tmp`, rp2/mpy-cross build dirs).
  - **Ports are host-wide and fixed in code** (twin CI 18080 and 53, `test.sh`'s HTTP/DNS listeners,
    `npm test`'s 19420/19481/19482, Part E.1's 17400-19999 range); worktrees don't isolate them and no
    per-agent allocation exists without code changes. Every port-binding command (`scripts/test.sh` in
    any mode, `run_digital_twin_ci.sh`, `run_unix_port_integration.sh`, `npm test`,
    `cross_browser_smoke.mjs`, any twin boot) runs only under `flock /tmp/sensors-audit-ports.lock`.
  - The lock holder uses `test.sh`'s autodetected parallelism; a timing failure seen under contention
    stays "unconfirmed" until reproduced alone.
  - The toolchain directory (`$PICO_TOOLCHAIN_DIR`) is **not** read-only in use: `build_firmware.py`
    wipes `<toolchain>/micropython/mpy-cross/build` and rebuilds `ports/rp2/build-<board>`, and `test.sh`/
    `run_digital_twin_ci.sh` re-run `setcap` on the shared binary. Firmware builds run under
    `flock /tmp/sensors-audit-toolchain.lock` or on a private toolchain copy (its own `sudo setcap` —
    copies lose the capability). ENV builds and verifies both Unix-port variants first, so `test.sh`'s
    variant check never triggers a rebuild.
  - ENV's baseline runs in its own worktree. Twin FRAM/SCD30 state and `digital_twin_ci_logs/` are
    copied to `<scratchpad>/twin-evidence/<utc>/` before any rerun (CLAUDE.md's FRAM-evidence rule covers
    the twin).
  - Fix work: one writer per file at a time; fixes land on the audit branch (PQ2).

### 4.5 Findings register

`audit/REGISTER.md` (PQ2), listed in README "Further reading", created at execution
start — not now. Written only by the lease holder (4.7).

**Header fields**: lease (session ID and link, since UTC) · released (UTC, or —) · audit branch ·
go-ahead reference (3.1) · owner-review list (every entry decided on the owner's behalf or logged for
review, OR2.c/OR12.a/OR13.a/OR24.a) · planning baseline (`4dc80ef`) ·
audit baseline SHA (ENV.T08) · current phase and group · unit table (U0-U37 from 4.1: not started / pass k / converged@sha / closed@sha /
re-opened) · per-area lens record (every lens of 4.2: applied, or "N/A, because …" — DoD 1.2).

**Entries**: one `### AF-<AREA>-<nnn>` block per finding, plus a one-line-per-finding summary table at
the top (ID · title · area · severity · status). An AF ID is assigned at intake — when an auditor
reports a finding or picks up a seed or harvested note — and is kept whether the item is confirmed or
rejected. Fields:

`source` (seed/note ID, or auditor A/B of pass k) · title · file:line list (repo paths at
`observed@sha`; upstream sources as `<project>@<tag>:<path>:<line>`) · `observed@sha` (the worktree
SHA the auditor read) · `found-in-pass` and date · owning area · lenses (primary first) · severity
(PQ3; assigned by the arbiter) · class (defect / latent / doc-drift / test-gap / decision-needed) ·
evidence (repro, source citation) · CLAUDE.md rule involved (quoted heading) · touches-SETTLED
(do-not-reopen index entry, or none) · on-behalf (no / yes: the decision and its reasoning, OR2.c) · needs-silicon (no / yes: which BACKLOG real-hardware entry) · wear (none / flash /
NVM / FRAM / host) · related / duplicate IDs · verifier verdict · status · decision (owner text or
pointer) · moved-to (BACKLOG number or real-hardware entry) · fix unit (branch, PR link) · `re-verified@HEAD`.

**Status transitions**: `open` → verifier verdict (`confirmed` / `plausible` / `rejected`) → one
terminal status, matching OR5.a's closure states: `fixed` (verified); `resolved-stale` (verified already
resolved or stale, removed); `settled` (a decision documented as a permanent fact — the owner's, or
taken on the owner's behalf and on the owner-review list); `out-of-scope` (owner decision, documented as
a known limitation); `moved-to-hardware` (BACKLOG real-hardware entry, closed in phase C);
`deferred-by-owner` (a future goal, one BACKLOG item with its reason, OR27.a); `rejected` /
`duplicate-of` (with the reason). `plausible` is not terminal: it ends in one of these.

A rejected seed or note stays in the register with its reason while the audit runs, so it is not
rediscovered. When the register is deleted, only rejections whose rediscovery risk is real migrate — per
CLAUDE.md's working agreement (target pending `DOC.S10`; a BACKLOG "don't re-raise" note only if the
owner confirms); the rest go with the file (docs-current-state rule).

### 4.6 Execution environment (area `ENV`)

Per-session topics (a fresh container repeats them): T01, T03, T04. Once-only topics commit their
results to the register's header or `audit/artefacts/ENV/`: T02, T05-T11.

- [ ] **ENV.T01** (per session) Build the toolchain (`uv run toolchain/setup_toolchain.py`; skip when
      `setup_toolchain.py test` passes); note sandbox egress limits (CLAUDE.md: `astral.sh`;
      BACKLOG.md:631: `deb.debian.org`); build and verify **both** Unix-port variants
      (`hasattr(sys, "settrace")` False for `build-standard`, True for `build-settrace`) so no agent later
      triggers a rebuild.
- [ ] **ENV.T02** (once) Baseline run of every tier listed in 1.2, serialized under the port lock (4.4);
      record counts (files, tests, pass/fail), wall clock, host peak RAM, host SSD writes (`/proc/diskstats`)
      and the environment record, coverage per `src/` file, lint/typecheck finding counts (expected 0), npm results. `uv run pytest tests_hardware --collect-only` is board-free in the
      sandbox; `HW.T14`'s confirmation is part of the go-ahead record.
- [ ] **ENV.T03** (per session) Reference corpus: reuse `$PICO_TOOLCHAIN_DIR/micropython` at the
      pinned ref (`toolchain/versions.toml`) with the rp2 submodules (`lib/lwip`, `lib/cyw43-driver`, `lib/pico-sdk`,
      `lib/micropython-lib`) read-only; Microdot at the vendored tag; after the dependency refresh the previous pins
      (MicroPython `v1.29.0` with its submodules, Microdot `v2.6.2`) stay in the scratchpad read-only for the citation
      re-check.
- [ ] **ENV.T04** (per session) Re-extract datasheet text (`uv run --with pypdf --with cryptography
      audit/sweeps/extract_datasheets.py <scratchpad>`; several PDFs carry a permissions encryption that pypdf decrypts only with `cryptography`); list missing datasheets (seed `SENS.S20`).
- [ ] **ENV.T05** (once) Apply 4.4's non-interference rules: lock files, worktree per executing agent,
      toolchain copy policy.
- [ ] **ENV.T06** (once) Measure `disallow_any_explicit` (and `disallow_any_unimported`) counts per pass (BACKLOG's figures are dated
      2026-09-11) as the baseline for switching it on in this audit (OR81.a).
- [ ] **ENV.T07** (once) Build the do-not-reopen index (`DOC.T14`) and the cross-reference resolver
      (`DOC.T02`) before B1, committed under `audit/`. ⟨pass 2, overtaken: index built from DECISION_PROVENANCE's answers and OR54-OR73, actor-tagged; `NTP_Host` bound leaves the settled list (OR70.a (4)) — G10: R05⟩
- [ ] **ENV.T08** (once) Record the audit baseline SHA (`main`'s head at go-ahead, frozen from then on,
      OR52.a (4)) in the
      register header; anchors in this file resolve at the planning baseline (`git show 4dc80ef:<path>`;
      `git fetch --unshallow` first if `.git/shallow` exists). If `main` moved past `4dc80ef`, first repeat
      V11's move (`reanchor.py`, `harvest_check.py`, `baseline_fates.py`, a delta harvest) to the new SHA.
- [ ] **ENV.T09** (once) Commit `audit/sweeps/packet.py` (auditor packet, 4.4) and
      `audit/sweeps/owner_of.py` (file → owning area from 5.0, for routing findings and re-verification).
- [ ] **ENV.T10** (once) Commit the plan validators (`audit/sweeps/validate_plan.py`: V1 ownership, V3
      anchors in bounds, V4 ID uniqueness) and extend V3 from bounds to content where an anchor quotes
      text (planning found an in-bounds wrong anchor: BACKLOG.md:575 for :555 at `0615eba`) — the harvest
      already has that content check (`audit/sweeps/harvest_check.py`).
- [ ] **ENV.T11** (once) Dependency refresh after T02 and before B1 (LEAD/R33): every external dependency
      updated against the baseline, workarounds re-checked, the post-refresh baseline recorded; a short second check at B5.

### 4.7 State and resumption

- **All state lives in git on the audit branch.** Nothing needed to resume may live only in a session's
  context, the (session-specific) scratchpad or a subagent report. The arbiter commits after every
  arbitration batch (autonomous commits authorised, PQ2).
- **Resume procedure**:
  1. `git fetch origin`; check out the audit branch named in the register header (before the register
     exists: the branch the owner names at go-ahead). `git fetch --unshallow` if `.git/shallow` exists.
  2. Read CLAUDE.md, this plan (3.1 included) and the register header. No register means a first start.
  3. Confirm the go-ahead: 3.1 records it, and the owner's message that started or continued this
     session is its confirmation for software work (the real-hardware go-ahead never carries over). Never touch the board; check BACKLOG.md's "Real-hardware work still owed" (board
     state) and any handover file for a bench sitting in progress by another session.
  4. Take the lease: read the holder's last register commit (date, `Claude-Session` trailer) and confirm
     that session is idle, completed, failed or archived — otherwise ask the owner. Write your session
     and UTC time into the header, commit, push. A rejected push means re-read, never force. Write
     `Released` when stopping.
  5. Delta: `git diff --name-only <audit-baseline>..origin/<branch>` through `audit/sweeps/owner_of.py`;
     queue closed areas in the header; note the changed files for areas that are mid-pass.
  6. Per-session ENV: T01, T03, T04.
  7. Continue with the lowest open unit (4.1).
- **Shared docs**: from B1 on, the unit that makes a change also updates every doc it touches
  (current-state rule); the structural doc work is B4. Unit outputs and quality artefacts live in
  `audit/artefacts/<AREA>/` until the unit that migrates them. After any merge run every level, and
  after one touching `uv.lock` re-verify the installed tool versions against the pins (CLAUDE.md).
- **Frozen `main`** (OR52.a (4)): other sessions do not push to it during the audit. Auditors read a
  worktree at their unit's start commit; every finding is re-verified at the audit branch's HEAD before
  it is fixed or migrated (`re-verified@HEAD`).

---

## 5. Areas, topics and seed observations

### 5.0 Area index and file mapping

| Code | Area | Files (tracked) |
|---|---|---|
| XCUT | System-wide contracts (boot, supervision, watchdog, timers, concurrency, errors, persistence layout) | cross-file; anchored in `src/system_service.py`, generated `sensortask_<device>.py`, Part A.7/C.7-C.9/C.13-C.14 |
| CORE | Core runtime modules | `src/system_service.py`, `base_classes.py`, `config_manager.py`, `print_log.py`, `api_response.py` |
| ALGO | Pure algorithms and codecs | `src/math_helpers.py`, `voc_algorithm.py`, `crc_checks.py`, `framing_codecs.py` |
| BUS | Bus layer | `src/asy_i2c_driver.py`, `asy_spi_driver.py`, `asy_uart_driver.py` |
| SENS | Sensor drivers | `src/asy_scd30_driver.py`, `asy_sgp40_driver.py`, `asy_bmp3xx_driver.py`, `asy_isl29125_driver.py` |
| STOR | FRAM storage | `src/asy_fram_driver.py`, `asy_fram_manager.py` |
| UART | UART protocol | `src/asy_uart_comm.py`, `asy_uart_link_driver.py`, `UART_C_PORT_CHANGELOG.md`, Part J |
| NET | Networking | `src/asy_wifi_service.py`, `asy_ntp_client.py`, `asy_dns_client.py`, `asy_udp_socket.py`, `captive_dns.py`, `LICENSE-captive_dns` |
| REST | Web server and HTTP surface | `src/asy_webserver_service.py`, relied-upon behaviour of `ext/microdot.py` |
| LED | Notification and LED | `src/asy_neopixel_driver.py`, `asy_notification_service.py` |
| GEN | Build generator and device definitions | `buildgen/*`, `devices/*.toml` |
| TOOL | Toolchain installer and build overrides | `toolchain/*` |
| SCR | Scripts and test orchestration | `scripts/*`, `host_typecheck.ini`, `digital_twin/typecheck.ini` |
| CI | CI, dependency pins, supply chain | `.github/**`, `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, `.nvmrc`, `.gitignore`, `eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `.htmlvalidate.json`, `.stylelintrc.json` |
| WEB | Website | `js/*`, `html/*`, `mockdata/*`, `ext/freezefs/` except `LICENSE` (reliance only) |
| TEST | Software test tiers | `tests/*`, `tests_scripts/*`, `tests_js/*` |
| TWIN | Digital twin | `digital_twin/*` except `typecheck.ini` |
| HW | Real-hardware tier (desk review; execution gated) | `tests_hardware/**`, `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `dev_legacy/README.md`; BACKLOG.md's "Real-hardware work still owed" is read here though DOC owns the file |
| SEC | Security threat model | cross-cutting |
| MEM | Memory safety | cross-cutting, Part I |
| PERF | Timing and capacity budgets | cross-cutting |
| PLAT | MicroPython/RP2040 platform facts | Part F, `toolchain/versions.toml` pin |
| PAR | Legacy parity and field migration | refactor vs `python/`, `modules/`, `html_raw/` |
| DOC | Documentation set | `README.md`, `SPECIFICATION.md`, `CLAUDE.md`, `BACKLOG.md`, `DEVICE_REFERENCE.md`, `PROJECT_AUDIT_PLAN.md`, `update_and_install.txt` (reads every other doc without owning it) |
| LIC | Licensing and attribution | `LICENSE`, `THIRD_PARTY_LICENSES.md`, `ext/LICENSE-microdot`, `ext/freezefs/LICENSE`, attribution headers (reads `src/LICENSE-captive_dns`, owned by NET) |
| ENV | Audit execution environment | section 4.6; `audit/**` (temporary apparatus, PQ2) |

Out of scope/reference only: see 2.2. Every tracked file has exactly one owning area above (DOC reads
every doc, LIC reads every licence header, without owning them); checked by validation step V1.

---

### 5.1 XCUT — System-wide contracts

**Goal**: establish, from code, the device's real runtime contracts — boot order, supervision,
watchdog budget, timers, tasks, locks, error codes, persistence layout — as the reference every other
area audits against.
**References**: Parts A.4, A.7, C.7-C.9, C.13, C.14, G, I.4; generated
`build/generated_src/sensortask_<device>.py` for all 6 devices.

Topics:
- [ ] **XCUT.T01** Boot sequence per device, from `WDT(timeout=8000)` creation through the setup batch
      (`fram → sysfunct → conn → ntp → needs_setup…`) to the first supervisor feed: every feed point,
      the worst-case gap between feeds, and what happens when any `setup()` fails (legacy reboot-looped;
      the generated `build_system()` ignores the result — seed `PAR.S12`).
- [ ] **XCUT.T02** Task supervisor semantics: is restarting via the same captured starter safe for
      *every* task (state reset, double registration, leaked timers)? Undetected hung-but-alive tasks
      (flag never set, lock never released)? Decay/score arithmetic; wrnno `n+1` stability across
      devices and firmware versions; restart backoff.
- [ ] **XCUT.T03** Watchdog budget end to end: all feed sites, worst-case scan with *k* simultaneous
      task deaths each persisting to FRAM (~305 ms of *yielding* time per chunk, SPECIFICATION.md ~1854
      — distinct from the ~21 ms *non-yielding* bus hold in `PERF.T04`), commanded reset vs WDT reset
      (FRAM paused vs not), and the absence of any recorded `machine.reset_cause()`.
- [ ] **XCUT.T04** Timer inventory per device: every `machine.Timer`, ONE_SHOT vs PERIODIC, what a
      dropped soft callback costs (F.1), the rp2 alarm-pool limit vs simultaneous timers, every ENOMEM
      fallback and whether its failure is persisted or print-only.
- [ ] **XCUT.T05** Task inventory: every `create_task`, supervised or not (config flush, captive DNS,
      hotspot LED flash, per-connection HTTP tasks), lifetime, cancel path, exception visibility.
- [ ] **XCUT.T06** Lock map: every `asyncio.Lock`/`ThreadSafeFlag`/`Lockable`, holders, hold spans
      containing `sleep`/network/bus I/O, lock ordering (deadlock freedom), non-reentrancy hazards (seed
      `STOR.S02`).
- [ ] **XCUT.T07** Error-code catalogue: every `errno`/`wrnno` per module vs Part C.7.1; reserved
      ranges; dynamic codes; `repeat=` usage vs the per-episode rule; persisted vs print-only; whether
      client-input errors belong in the fault history. BACKLOG.md:21-35 (added at `03f8bcf`) itself
      records four changed modules still numbering inside the reserved range; OR28.a renumbers all in one
      pass.
- [ ] **XCUT.T08** Logger lifecycle: every FRAM-backed logger's `setup()` site; entries logged before
      `setup()`; `reset()` racing `setup()`; `set_level_setters` coverage; debug-level precedence.
- [ ] **XCUT.T09** FRAM layout per device: deterministic chunk order, total bytes vs chip size (8 KB on
      field devices, `dev` declares `max_size = 0x40000` — part number per `HW.T07`), what a firmware
      change that adds/reorders a chunk does to existing data, first boot on a chip written by another
      layout (legacy, other firmware). ⟨pass 2, answered: layout need not survive a reflash; a foreign layout reads invalid and re-inits (OR47.a (2), OR56.a (3)); the sum vs chip stays work in R33 — G5: R05, R33, HR156⟩
- [ ] **XCUT.T10** Config persistence end to end: per-module files, `setup()` repair, littlefs
      atomicity under power loss, flush before each reset path, concurrent writers, unsupervised flush
      task failure visibility.
- [ ] **XCUT.T11** Setter dispatch: `PUT /sensors` direct `_set_dict_cfg` vs settings-group
      `handle_set_cmd`; per-module serialization; failed-push recovery chain under concurrency;
      post-hook failure reporting; "Unchanged" semantics vs a diverged chip.
- [ ] **XCUT.T12** Readiness gates (C.13) for every module, including behaviour when `setup()` fails or
      is never reached.
- [ ] **XCUT.T13** Every reset/reboot path (REST reboot/bootloader, supervisor, WDT, alarm-pool
      fallback): FRAM pause, config flush, repeated requests, interaction with an in-flight PUT.
- [ ] **XCUT.T14** The generated `sensortask_<device>.py` modules as frozen firmware code in their own
      right: reviewed like `src/`, yet outside `src/` review, outside coverage (seed `TEST.S13`), and
      outside `test_reset_call_site_invariant.py`'s scan.
- [ ] **XCUT.T15** Part G.3 re-validation: grep-for-the-shape sweep for duplicated primitives across
      `src/`, `buildgen/`-generated code and `js/`.
- [ ] **XCUT.T16** Import graph: no cycles across `src/` + `ext/` + generated code; import-time side
      effects per module (allocations, hardware access), including the pre-`WDT()` phase (`XCUT.T20`);
      frozen set = transitive import closure (with `GEN.T05`).
- [ ] **XCUT.T17** Data freshness contract: what `TS` means per driver; can any cycle publish old
      values with a new timestamp (seed `SENS.S08`)? ⟨pass 2, answered: "never stale as fresh" binds every driver; SCD30 not-ready reuse the named exception (3.3) — G5: HR036 (G3)⟩
- [ ] **XCUT.T18** Time base: RTC set by NTP, `time.time()` vs `ticks_ms()`, `mktime` epoch/TZ,
      timestamps stored in FRAM, boot signature semantics.
- [ ] **XCUT.T19** Cancellation-safety map: every `await` reachable from a cancelling context
      (webserver `wait_for`s `src/asy_webserver_service.py:246, 708`, `src/asy_fram_driver.py:408`,
      supervisor restarts). For each multi-step sequence cut mid-way (`_set_dict_cfg`
      persist→push→recover, SCD30 command+wait, FRAM dual-copy write and BUSY marker, `write_config`
      staging, `_flush_pending_configs` before a reboot) state what the cut leaves behind.
- [ ] **XCUT.T20** Boot failure outside any exception net, by phase. (1) Before `WDT()` exists — the
      REPL or a block, i.e. a hang, not a reset loop: upstream `_boot.py`'s mount-or-format
      (`XCUT.S18`); a filesystem `boot.py` (`XCUT.S16`; a filesystem `main.py` never runs, `PLAT.T10`);
      the generated module's import closure — shadowing by filesystem modules (`XCUT.S17`, `PAR.T08`),
      frozen-set gaps (`GEN.T05`), import-time effects (`XCUT.T16`; today only `frozen_html`'s mount,
      `XCUT.S14`). (2) From `WDT()` to the first supervisor feed (`XCUT.T01`, `XCUT.S13`, `PAR.S12`): a
      constructor in `build_system()` raising, frozen `main.py` ending in the REPL with `WDT(8000)`
      armed and no FRAM logger yet. (3) An exception or return out of `main()` (`XCUT.S11`). For each:
      reset loop or hang? Does a power cycle recover it? Is it diagnosable at all? Is arming the
      watchdog before the boot entry's import feasible (8 s budget vs import time; USB/mpremote access)? ⟨pass 2, answered: phase (1): WDT before the import (OR31.a (1)) + `.frozen` first and runbook erase (OR59.a); phases (2)/(3) stay work (Gap 2) — G5: R01, R48, HR050⟩
- [ ] **XCUT.T21** Tick counting and `ThreadSafeFlag` semantics: counters that advance once per
      `wait()` (SysUptime, WiFi/NTP counters, hotspot timeout, sensor base triggers) lose ticks when the
      flag is set twice before the waiter runs, a soft callback is dropped, or the loop stalls > 1
      period. Which must be wall-clock accurate? Exactly one waiter per flag, across supervisor restarts
      too.
- [ ] **XCUT.T22** Soft-callback pile-up budget: callbacks that can fall due inside the longest
      no-yield or IRQ-off window (flash write, I2C `timeout`, GC pause, VOC step) vs the scheduler depth
      (8, F.1). Analysis only — F.1 settles the software-timeout mitigation as rejected.
- [ ] **XCUT.T23** Non-finite values on every output path: which floats can reach `json.dumps` (REST
      responses, config files) as NaN/±inf (MicroPython emits bare `nan`/`inf`, invalid JSON — verify at
      1.29.0)? Only SCD30 checks `isfinite` (`src/asy_scd30_driver.py:626`). One finiteness contract per
      layer (see `REST.T11`).
- [ ] **XCUT.T24** Post-mortem diagnosability (L-DIAG end to end): per failure class — WDT reset,
      supervisor reboot, boot crash, unsupervised-task death, FRAM write failure inside the logging
      layer (`_diag()` silent at level 0, `src/print_log.py:177-178`) — what persisted evidence
      survives?
- [ ] **XCUT.T25** Tick arithmetic on rp2's 2**30 period (`py/mpconfig.h:1924-1925`,
      `extmod/modtime.c:172-173, 191-192`); `ticks_diff()` is only valid for gaps under ±2**29 ms (~6.2
      days). (a) Every stored `ticks_ms()` value or deadline later passed to `ticks_diff()` —
      set/compare pairs: ISL `_last_switch_ms` (`src/asy_isl29125_driver.py:247, 610` / `:586`),
      `_cal_until_ms` (`:266, 1035` / `:633`), `_cal_meas_until_ms` (`:269, 703` / `:707`),
      `_settle_until_ms` (`:1078, 1383` / `:1293`), UART `_holdoff_deadline` (`src/asy_uart_comm.py:203, 528`
      / `:521`). (b) Every delta passed to `ticks_add()`, `asyncio.sleep_ms()`/`sleep()`/`wait_for()`
      (all via `ticks_add`, `extmod/asyncio/core.py:57, 62-63`, `funcs.py:34`): `OverflowError` at ≥
      2**29 on rp2 only, and near-2**29 keys breaking the task-queue order (`XCUT.S15`). (c)
      `Timer(period=)`'s C-int range (`ports/rp2/machine_timer.c:79, 99-103`). (d) Every source of such
      values without an upper bound (`UART.S08`, `GEN.S18`). The Unix port's period is 2**62, so no
      mock/twin test reaches any of it (`TEST.S25`): verify (a) with a module-level fake `time` with a
      2**30 period, and (b)/(c) and the queue order with a Unix build using
      `-DMICROPY_PY_TIME_TICKS_PERIOD='(1<<30)'` (the macro is `#ifndef`-guarded; whether anything else
      breaks is untested) — never by soak. F.1 (SPECIFICATION.md:3526-3527) claims every `src/` use is a
      short bounded timeout (`DOC.S23`).

Seeds:
- **XCUT.S01** A watchdog feed happens only after the supervisor's full scan; several task deaths, each
  costing two persisted FRAM writes, plus the 2 s sleep could approach the 8 s WDT and turn a commanded,
  FRAM-paused reboot into an unpaused WDT reset (`src/system_service.py:229-255`).
- **XCUT.S02** ONE_SHOT soft timers on critical paths contradict C.9's own "PERIODIC for anything that
  must fire" rule: `_reboot` (`system_service.py:126`), storage auto-unpause (`:365`),
  `_timer_sequencer` (`:164`); the arm-failure paths only cover ENOMEM.
- **XCUT.S03** Every `_reboot()` call deinits and re-arms the 4 s reset timer, so repeated reboot
  requests can postpone the reset indefinitely while FRAM stays paused (`system_service.py:118-126`).
- **XCUT.S04** A supervisor-triggered reboot does not flush pending configs, unlike the REST path
  (`src/system_service.py:251-253`; REST path `buildgen/codegen.py:501-514, 524-531`).
- **XCUT.S05** If `_timer_sequencer` cannot arm its next step, the remaining timer starters are skipped
  with only a print-level error; those drivers' tasks then wait forever and the supervisor, which only
  checks `done()`, cannot see it (`system_service.py:169-175, 209-214`).
- **XCUT.S06** C.9.1's stagger proof: the first starter fires at offset 0; offsets are relative to each
  callback's actual run time, so latency accumulates (`system_service.py:158-159`). The proof's own test re-implements the formula instead
  of reading it (seed `TEST.S06`). ⟨pass 2, answered: shared t0 and minimum separation (OR47.a (3)) — G5: R07⟩
- **XCUT.S07** Dynamic `wrnno = n+1` means a persisted W-code names different tasks on different
  devices/firmware versions and must stay ≤ 127 (`system_service.py:238-239`). ⟨pass 2, answered: restart logged once (OR56.a (1)); code meaning catalogued (OR28.a) — G5: R19, R20⟩
- **XCUT.S08** `[x2]` The FRAM chunk layer logs into the manager's RAM-only logger, not the owner's
  FRAM-backed history as C.7.1 states (`src/asy_fram_manager.py:622, 665-674, 716`).
- **XCUT.S09** A.4's "8 KB ample headroom over SGP40's ~250 B" predates WP1-WP3; ~17 logger/cfgmgr
  chunks on wozi and ~21 on dev now share the chip — never re-summed against 8 KB.
- **XCUT.S10** No `machine.reset_cause()` is recorded anywhere in `src/`, so post-mortems cannot tell a
  WDT reset from a commanded one. ⟨pass 2, answered: `reset_reason` via `mem_backup()` region 0 (OR60.a) — G5: R03⟩
- **XCUT.S11** The supervisor's reboot branch `return`s (`src/system_service.py:251-253`), so `main()`
  and `asyncio.run(main())` finish ~4 s before the reset fires (`buildgen/codegen.py:478, 705-708`):
  webserver, readers and any staged flush stop at once and `main.py` drops to the REPL. The REST reboot
  path keeps the loop running until the reset.
- **XCUT.S12** No `set_exception_handler()` anywhere in `src/` or codegen: an unretrieved exception
  from an unsupervised task (`src/config_manager.py:354`; `src/asy_wifi_service.py:394, 425`) only
  reaches MicroPython's default console print.
- **XCUT.S13** `WDT(timeout=8000)` is `build_system()`'s first statement (`buildgen/codegen.py:381`);
  the constructors after it run unguarded, so a construction-time exception becomes an 8 s WDT reset
  loop before any FRAM logger exists — nothing persisted, `reset_cause()` never read (`XCUT.S10`). ⟨pass 2, answered: WDT placement settled (OR31.a (1)); evidence of a construction crash is Gap 2 — G5: R01, Gap 2⟩
- **XCUT.S14** The boot entry's `from sensortask_<device> import main` sits before `WDT()`
  (`buildgen/codegen.py:703`; the entry's `try` has only a `finally`, `:705-708`, so moving the import
  inside it would still end in the REPL), and the generated module imports `frozen_html` at top level
  (`:301`), whose copied-in freezefs `mount_fs()` raises `OSError(EEXIST)` if `/html` already exists
  (`ext/freezefs/ffsmount.py:172-185`; `--on-import mount --target /html`,
  `scripts/build_frozen_html.sh:17, 33-34`). Any `/html` on the littlefs root (a manual `mpremote` copy
  or an interrupted deploy; unlikely from the legacy pipeline, whose freezefs default `--on_import mount`
  is a VFS mount that leaves no littlefs directory, `build-*.sh:15`) stops the import before
  `WDT(timeout=8000)` exists (`codegen.py:381`): REPL, no watchdog, no network, no FRAM logger — a hang
  until USB intervention or a filesystem erase — `/html` survives power cycles — not a reset loop. No
  tier reaches it (with `PAR.T08`). ⟨pass 2, answered: WDT before the import (OR31.a (1)); runbook erases the filesystem, `/html` included (OR59.a (1)) — G5: R01, HR050⟩
- **XCUT.S15** A legal but near-limit sleep can strand other tasks. asyncio's C `TaskQueue` orders tasks by `ticks_diff()` of their keys (`extmod/modasyncio.c:73-85`), so a key pushed close to 2**29 ms ahead compares as *earlier* than a queued task already overdue by at least the remaining margin; `SENS.S27`'s `sleep_ms(remaining)` (`asy_isl29125_driver.py:619-623`) creates such a key (up to 2**29-1 ms, accepted by `ticks_add()`). The far-future task becomes the heap root and `run_until_complete` waits on it (`extmod/asyncio/core.py:57, 161-177`): tasks woken later get fresh keys and run, but runnable tasks already queued are stranded ~6.2 days — a WDT reset if the supervisor is among them, else a hung-but-alive task (`XCUT.T02`). From source reading only; verify on a 2**30-period Unix build (`XCUT.T25`).
- **XCUT.S16** A filesystem `boot.py` runs before the frozen `main.py` and leaves no watchdog in three ways: if it raises, the frozen `main.py` never runs (rp2 has exit-code handling off, `py/mpconfig.h:1217-1218`, so an unhandled exception returns 0, `shared/runtime/pyexec.h:45-48`, and `main.py` runs only on non-zero, `ports/rp2/main.c:237, 246-247`) — REPL, no watchdog; if it blocks, it blocks before USB is initialised (`main.c:239-241`), so not even mpremote recovers the unit (unverified on hardware); `sys.exit()` in it soft-reset-loops (`main.c:243-245`). A filesystem `main.py`, by contrast, never runs — the frozen one is looked up first (`shared/runtime/pyexec.c:743-752`). `XCUT.T20` names both files together; their consequences differ. ⟨pass 2, answered: runbook erases the filesystem on every reflash (OR59.a (1)); a `boot.py` runs before any guard, so no firmware guard — G5: HR050, R01⟩
- **XCUT.S17** Filesystem modules shadow frozen ones: `sys.path` is `['', '.frozen', '/lib']`
  (`py/runtime.c:147-150`, `ports/rp2/main.c:208`). The `dev` bench's 2026-08-27 filesystem snapshot
  (`dev_legacy/README.md:667-672`; historical — that flash is empty now, but deployed legacy units may
  hold the same) held 17 modules named like the refactor's frozen set (`asy_i2c_driver`,
  `asy_spi_driver`, `asy_fram_driver`, `asy_fram_manager`, `asy_bmp3xx_driver`, `asy_scd30_driver`,
  `asy_sgp40_driver`, `asy_uart_comm`, `asy_udp_socket`, `base_classes`, `config_manager`, `print_log`,
  `system_service`, `crc_checks`, `math_helpers`, `voc_algorithm`, `microdot`) plus `typing.py`. Any
  leftover is imported instead of the frozen module: an incompatible one
  (`ImportError`/`AttributeError`, or a `MemoryError` compiling it from source) fails before `WDT()` —
  REPL, hang; a compatible one runs stale behaviour silently. A module missing from the frozen set
  (`GEN.S11`/`GEN.T05`) fails the same way. Inventory: `PAR.T08`; consequence: `XCUT.T20`. ⟨pass 2, answered: `.frozen` first + runbook erase (OR59.a) — G5: HR050⟩
- **XCUT.S18** (low) Upstream `_boot.py` formats the whole littlefs if mounting raises for any reason (bare `except:`, `ports/rp2/modules/_boot.py:8-12`, v1.29.0) — before the watchdog and silently: every `config_*.cfg`, Wi-Fi credentials included, is lost, nothing is logged (no FRAM logger yet), and the unit boots into hotspot mode where `PAR.T06`'s permanent-deactivation hazard applies. A littlefs region that changed size between 1.26 and 1.29 would take this path on migration (with `PAR.T06`, `PAR.T09`, `XCUT.T24`). ⟨pass 2, answered: runbook erase (OR59.a (1)); legacy units run 1.24.1, not 1.26 (OR61.a) — G5: HR050, HR209⟩

Quality measure: a written timer/task/lock/error-code/FRAM-layout inventory per device, derived from
code, with every discrepancy against Parts A.7/C.7-C.9 registered; worst-case watchdog gap computed.

---

### 5.2 CORE — Core runtime modules

**Goal**: Part D in full (D.0-D.16) for `system_service.py`, `base_classes.py`, `config_manager.py`,
`print_log.py`, `api_response.py`, function by function.
**References**: Parts C.4-C.7, C.13, G.2, I.4; legacy `python/CommonDrivers/async_manager.py`,
`api_helpers.py`, `system_service.py`.

Topics:
- [ ] **CORE.T01** `ConfigManager.setup()`: every read-failure class (ENOENT vs EIO vs `MemoryError` vs
      corrupt JSON vs wrong type) and whether each may overwrite user config with defaults. ⟨pass 2, answered: missing → print only, no write; unreadable → never overwritten; bad key → one repair (OR70.a (3), OR71.a (2)) — G5: R34, R38, R21⟩
- [ ] **CORE.T02** `write_config()`/`_flush_staged()`/`flush_pending()`: staging identity checks,
      superseded flushes, exceptions from an unsupervised flush task, `_cache` commit in `finally` after
      a failed write (C.7.3 "costs persistence, never the config").
- [ ] **CORE.T03** Validation primitives (`type_or_range_error`, `coerce_numeric`,
      `check_cfg_get_default`, `special` handling) on single-precision rp2 floats, bigints, ±inf/NaN,
      `bool`-is-`int`, enum sets; static rejection of malformed schemas (int bounds on float fields,
      tuple `special` on special-alone fields).
- [ ] **CORE.T04** `_set_dict_cfg` orchestration: snapshot → persist → push → recover under concurrent
      PUTs to the same module; interaction with `Unchanged`.
- [ ] **CORE.T05** (module-level half of `XCUT.T08`) `PrintLogHistory`/`PrintLogHistoryStore`: ring
      semantics, count saturation, code encoding (0x80 split), pre-setup entries, reset-vs-setup race,
      `errno=0`, allocation per entry.
- [ ] **CORE.T06** `SystemService`: uptime/boot-signature across task restart, debug-level application,
      `pause_permanent_storage` clamp and unpause, reboot timer re-arm.
- [ ] **CORE.T07** `api_response`: envelope catalogue vs what the webserver actually emits; code 100
      after a post-hook exception; unused catalogue codes. ⟨pass 2, answered: envelope contract C14 (OR69.a (4)); unused catalogue codes go (OR46.a (2)) — G5: R39⟩
- [ ] **CORE.T08** `Lockable`/`LockableBuffer`/`Locked*`: does any `Locked*` critical section contain
      an `await`? If none, each lock is pure cost under cooperative scheduling — justify, document or
      drop; swallowed `RuntimeError`; unused per-buffer locks; clamping.
- [ ] **CORE.T09** D.15 method ordering, D.6 typing, D.11 comments, D.10 shapes across the five files.
- [ ] **CORE.T10** Dead/test-only API (seed `CORE.S14`): keep, trim or document — each is frozen
      bytecode on the device. ⟨pass 2, answered: test hooks go (OR36.a (1)), hardware API stays (OR36.a (3)), other confirmed leftovers go (OR46.a (2)) — G5: R54, HR073, HR084⟩
- [ ] **CORE.T11** `PrintLogHistoryStore` evidence preservation: which `_read()` failures (blank chunk,
      CRC mismatch, transient SPI EIO, paused storage) make `setup()` write the RAM ring over the
      persisted one; does the chunk API distinguish "never written" from "unreadable"? (CLAUDE.md
      FRAM-forensics rule; with `STOR.T01`).
- [ ] **CORE.T12** `ConfigManager` repair fixpoint and file lifecycle: every `setup()` repair converges
      within one boot (int↔float coercion, float32 JSON repr, special-alone fields — C.7.3's boots-bound
      covers a failing write, not a successful one that never converges); orphaned `config_*.cfg` after
      an instance is renamed/removed; filename length with `name_ext`.

Seeds:
- **CORE.S01** A supervisor restart of the uptime task resets uptime to 0 and leaves the boot signature
  `None` for the rest of the boot (`start_time_set` stays True), silently faking "a reboot happened";
  untested (`src/system_service.py:375-394`).
- **CORE.S02** Any read failure in `ConfigManager.setup()` — `MemoryError` on a valid file, EIO,
  `TypeError` — is logged as wrnno 3 "not found" and the file is rewritten with defaults, destroying
  user config on a transient boot failure (`src/config_manager.py:407-426, 459`). ⟨pass 2, answered: unreadable file never overwritten (OR70.a (3)) — G5: R34⟩
- **CORE.S03** Errors logged before a logger's `setup()` are overwritten when `_read()` restores the
  FRAM ring (e.g. SYSTEM's `_apply_level` errno 7 during `sysfunct.setup()`, before SYSTEM's
  `pr.setup()` runs in `start_and_check_tasks`) — but survive on first boot, so behaviour is
  inconsistent (`src/print_log.py:173-176, 273-277`). ⟨pass 2, answered: `pr.setup()` into the boot batch (OR47.a (2)) — G5: R06⟩
- **CORE.S04** `reset()` during an in-flight `setup()` read restores the old ring into RAM while FRAM
  is cleared (`print_log.py:213-223` vs `:273-277`).
- **CORE.S05** No per-module serialization of `_set_dict_cfg`'s sequence; a failed push in one PUT can
  make `_recover_failed_push` persist its pre-write snapshot over another PUT's accepted value
  (`src/base_classes.py:302-358`).
- **CORE.S06** A post-hook that raises after fields were persisted and pushed yields code 100 with an
  empty result, and the webserver then marks every field "Failed" (`src/api_response.py:92-105`;
  `src/asy_webserver_service.py:463-470`). ⟨pass 2, answered: OK envelope, group fields "Failed", own errno (OR69.a (4)) — G5: R39⟩
- **CORE.S07** Every persisted log entry allocates a fresh `AsyFramChunkBuffer` with an unused
  `asyncio.Lock`, against G.2's one-long-lived-buffer rule; `LockableBuffer`'s lock is never used
  anywhere (`print_log.py:249, 262`; `base_classes.py:54-56`).
- **CORE.S08** Debug-level precedence: the persisted `DebugLevel` overrides the constructor `debug=`;
  CFGMGR loggers never receive `debug`; with an invalid cfgmgr `get_debug_level()` reports 0 while
  loggers keep their constructor level (`system_service.py:105, 287-296, 317, 340-341`;
  `config_manager.py:220`).
- **CORE.S09** `flush_pending()` is unguarded: a flush task that died with an unexpected exception
  re-raises through `_system_cmd_callback` and the reboot is never issued; re-await semantics of a
  finished task need checking against pinned `extmod/asyncio` (`config_manager.py:390-400`; also
  `system_service.py:184-196`).
- **CORE.S10** `write_config` validates against the caller's `cfg_vals` while `setup()`/`_cache` use
  `self.cfg_vals` — two sources of truth (`config_manager.py:299-347`).
- **CORE.S11** Each invalid key in a PUT is a persisted *error* (errno 10/12) and a FRAM write under
  `config_lock`; client input can evict real fault evidence from the 10-slot ring
  (`config_manager.py:319, 330`). ⟨pass 2, answered: every call keeps logging whatever the origin; newest-entry rule bounds eviction (OR35.b) — G5: R20, HR012⟩
- **CORE.S12** `get_int_values()` uses `int()`, silently truncating a float field or converting a bool,
  unlike `get_bool_values()`'s strict check (`config_manager.py:282-289`).
- **CORE.S13** Small: `Lockable.__aexit__` swallows `RuntimeError` on double release
  (`base_classes.py:47-50`); comment claims `pr.name == name` in the `logger=` branch without enforcing
  it (`:163-171`); `get_log()` reports ErrNum 128 for a raw 0x80 entry (`print_log.py:189-191`);
  `errno=0` counts but never persists (`:161-166`).
- **CORE.S14** Production API with no `src/` caller: `api_response.parse_cmd_request` (webserver
  re-implements it as `_body_as_dict`, a Part G duplicate), catalogue codes 2-5, `ok_descr`,
  `SystemService.get_debug_level`/`set_debug_level`/`stop_uptime_timer`, `LockedFlag`,
  `type_or_range_error(check_special=)`, `SensorReader(logger=)`. ⟨pass 2, answered: confirmed leftovers removed (OR46.a (2)); `parse_cmd_request` vs `_body_as_dict` one primitive (OR24) — G5: R54, HR073⟩
- **CORE.S15** Comment drift: `config_manager.py:126-127` says the generated `lightCmdLED` dispatch
  calls `coerce_numeric()`; it calls `type_or_range_error()` with synthetic schemas
  (`buildgen/codegen.py:538-556`).
- **CORE.S16** `PrintLogHistoryStore.setup()` calls `_write()` whenever `_read()` returns False, and
  `_read()` returns False on any failure, so a transient read fault at boot — not only a blank chunk —
  overwrites the persisted ring and count (`src/print_log.py:257-271, 276`).
- **CORE.S17** `write_config()` sets `self._staged` before `asyncio.create_task()`; a `MemoryError`
  there returns `(False, {})` (every field "Failed") while `_current()` keeps serving the staged value
  and no flush is ever scheduled (`src/config_manager.py:353-360`).
- **CORE.S18** SysUptime counts `uptime_event` wake-ups, not elapsed time: every loop stall > 1 s or
  dropped soft callback is a permanent undercount (`src/system_service.py:204, 379-380`; same mechanism
  as `NET.S02`).

Quality measure: each file passes Part D with every finding registered; each seed confirmed or
rejected by a verifier with a repro or a source citation.

---

### 5.3 ALGO — Pure algorithms and codecs

**Goal**: every formula and codec correct against its primary source, over its full domain, in the
target's arithmetic (float32 on rp2, arbitrary-precision ints in Python vs int32 in C references).
**References**: Part D.1/D.12, F.1 (float32), F.4; `math_helpers.py`'s cited literature; Sensirion
VOC Index algorithm (reference C source **not in the repo** — owner to supply or accept a gap).

Topics:
- [ ] **ALGO.T01** `math_helpers`: each formula vs its cited source, validity range vs the source's
      real domain vs the caller's hardware range (D.1), NaN/±inf, float32 behaviour.
- [ ] **ALGO.T02** `voc_algorithm`: port fidelity vs Sensirion's C reference, including every place C
      `int32` wraps and Python ints don't; state (de)serialization; blackout semantics after restore.
- [ ] **ALGO.T03** `crc_checks`: test vectors per polynomial/width, pass-mode parity with real mode,
      incremental API contract, per-byte `sleep(0)` cost and where it runs under a bus lock.
- [ ] **ALGO.T04** `framing_codecs`: COBS round-trip property over all lengths/zero patterns, in-place
      decode safety, scratch-aliasing contract with the UART write path; COBS is unused in production
      (UART defaults to `Framing_Pass`) — keep, test-only, or document. ⟨pass 2, answered: "keep, test-only, or document": keep as general-purpose API (OR36.a (3)); round-trip and aliasing tests stay work (U12) — G3: R05, R21⟩
- [ ] **ALGO.T05** Restored-state robustness: `unpack_from()` accepts any 32 int64 values; per field,
      does an out-of-int32 / out-of-domain value give a bounded wrong result, an exception, or a hang (→
      WDT reset restoring the same state = boot loop)? (with `PAR.S09`, `STOR`).
- [ ] **ALGO.T06** Runtime float32 vs compile-time double: C folds `F16(x)` in double at compile time,
      the port evaluates `_f16(x)` at run time in rp2 float32; enumerate every `_f16` argument and every
      frozen float literal/`const()` in `math_helpers`, prove equality — or precompute as integer
      `const()`s.
- [ ] **ALGO.T07** Oracle provenance for every ALGO test: literature/datasheet vectors, an independent
      implementation, or values the port generated itself (tautological).

Seeds:
- **ALGO.S01** `_FIX16_OVERFLOW`/`_FIX16_MINIMUM` are positive `0x80000000` in Python but `INT32_MIN`
  in C; `_fix16_div`'s `if not bit` overflow check cannot trigger; `F16(1)+FIX16_MAXIMUM` wraps negative
  in C but not here (`src/voc_algorithm.py:41-43, 248, 628, 675, 688`).
- **ALGO.S02** VOC state is packed as `"32q"` without a byte-order prefix, while F.1 says on-chip
  layouts pin `"<"` (`voc_algorithm.py:98, 141`).
- **ALGO.S03** `altitude_baro` returns a pressure, not an altitude (naming); the `abs_humidity` comment
  calls 7.6/240.7 "ice-phase" constants, which in the literature are the supercooled-water pair (ice is
  9.5/265.5) — legacy-identical, unused in `src/` (`src/math_helpers.py:86-98, 101-112`).
- **ALGO.S04** Pass-mode `add_into`/`check_from` skip the bounds validation real mode does, and
  pass-mode `add()`/`check()` return the caller's object where real mode returns a copy
  (`src/crc_checks.py:58-59, 73-74, 111-112, 131-132`).
- **ALGO.S05** `CRC16`, `rel_humidity`/`abs_humidity`, `Framing_COBS` have no production caller
  (`src/crc_checks.py:155-157`; `src/math_helpers.py:101, 119`; `src/framing_codecs.py:75`).
- **ALGO.S06** `_fix16_div()` masks a negative divisor to 32 bits; if `b` is a negative multiple of
  2**32, `divider` becomes 0 and `while divider < remainder` never ends while `bit` grows as a bigint —
  C's int32 can't produce such a `b`, Python's non-wrapping arithmetic or an unvalidated restore could
  (`src/voc_algorithm.py:139-178, 242, 245-247`).
- **ALGO.S07** `_f16()` runs in float32 on every sample and boxes floats each call; equality with C's
  compile-time double constants is unverified (`src/voc_algorithm.py:199-202`; uses e.g. `:417, 505, 510, 657, 761`).
- **ALGO.S08** rp2 small ints stop at 31 bits; the CRC32 register exceeds that on every shift, so each
  bit step allocates a bigint (`src/crc_checks.py:41-47`) — CRC32 guards SGP40's VOC chunk
  (`src/asy_sgp40_driver.py:182`), re-read every second during the NTP wait (`SENS.S05`). The 64-bit
  Unix port never shows this.

Quality measure: every formula has a cited source check and a float32 emulation check; VOC port has a
differential result or a recorded owner-accepted gap.

---

### 5.4 BUS — Bus layer

**Goal**: the I2C/SPI/UART wrappers' contracts (raise surface, never-block, locking, readiness) hold
exactly as Parts C.3, C.8, F.5.1/F.5.2/F.5.7-F.5.9 state, against the pinned rp2 port source.
**References**: `ports/rp2/machine_i2c.c`, `machine_spi.c`, `machine_uart.c`, `extmod/machine_i2c.c`
at `v1.29.0`.

Topics:
- [ ] **BUS.T01** Every public method's raise/sentinel contract vs Part D.2's per-bus `OSError`
      surface; every upstream caller catches what can propagate.
- [ ] **BUS.T02** Shared per-bus 32-byte I2C scratch: no await between fill and decode anywhere; no
      IRQ/Timer path touches I2C; copy-out on every return.
- [ ] **BUS.T03** Lock-hold spans that include sleeps (probe, SCD30 command waits) and their effect on
      sibling devices' timing on a shared bus.
- [ ] **BUS.T04** SPI session primitives: `configure()`/`machine.SPI.init()` per CS assertion — cost
      and whether it resets the peripheral each time; blocking `sleep_us(2)`.
- [ ] **BUS.T05** UART never-block invariant (CLAUDE.md hard rule): every read path clamped and
      yielding; write path waits; cancel handshake; `readinto(nbytes > len(buf))`.
- [ ] **BUS.T06** Uninitialised-bus behaviour (silent no-ops) and whether any caller can reach it.
- [ ] **BUS.T07** The deliberate I2C/SPI asymmetry (BACKLOG: SPI sync session, I2C none) stays
      deliberate; the D.10 note is current. ⟨pass 2, answered: stays deliberate (not equivalent methods, OR24.a); D.10/G.2 note rewritten as agent design — G3: R17⟩
- [ ] **BUS.T08** Unused public API (frozen bytecode that must still meet its bus contract): UART
      beyond `readinto_until_complete`/`writefrom`; I2C `scan`, `writeto_then_readfrom`,
      `write_then_readinto`; SPI `write_readinto` and the async transfers — keep, trim or test. ⟨pass 2, answered: keep (OR36.a (3)); each kept method gets a contract test — G3: R21⟩
- [ ] **BUS.T09** I2C bus recovery across an MCU-only reset: a WDT/`machine.reset()` mid-read resets
      the RP2040 but not the powered sensors; a slave holding SDA low survives into the next boot unless
      a bus clear is issued (check `ports/rp2/machine_i2c.c` init). Tests F.2's settled premise that a
      reboot reconstructs a wedged bus — raise, don't act (2.3).
- [ ] **BUS.T10** Worst-case synchronous block per I2C transaction (bus `timeout` from the TOML,
      `buildgen/codegen.py:386-387`, × transactions per locked section); per-port `machine.I2C`
      singleton silently reconfigured by a later construction with different freq/timeout (`HW.S18`).
- [ ] **BUS.T11** Pin states before `setup()` and across resets: FRAM CS pad default vs the FRAM
      power-up CS rule and any board pull-up; UART TX idle level before `init()` (with `STOR.T11`,
      `HW.T07`).
- [ ] **BUS.T12** IRQ-off windows vs peripheral buffering: littlefs program/erase (config flush, boot
      repair) vs the 32-byte UART RX FIFO (~2.8 ms at 115200, overrun absorbed silently, C.3.2), SPI DMA
      (F.5.2), CYW43. Window lengths need the Pico W QSPI flash datasheet (`datasheets/pico w/Winbond_W25Q16JV_Datasheet_RevF.pdf`, added 2026-09-25).

Seeds:
- **BUS.S01** `I2C.readfrom_into`/`writeto` are silent no-ops when `_i2c is None`; SCD30/SGP40 would
  then CRC-check stale buffer contents that pass — latent, unreachable today
  (`src/asy_i2c_driver.py:204-205, 222-223`).
- **BUS.S02** `I2CDevice._probe_for_device` sleeps 2×100 ms while holding the bus lock during every
  driver's `setup()` — boot cost is not a defect (CLAUDE.md WP6); relevant only where `setup()` re-runs
  at run time (e.g. `SENS.S22`) (`asy_i2c_driver.py:261-271`).
- **BUS.S03** `SPIDevice.session_begin` calls `machine.SPI.init(...)` on every chip-select (~25 per
  FRAM block); if rp2's `init` resets the peripheral this is real per-CS overhead (inferred; check
  `ports/rp2/machine_spi.c`) (`src/asy_spi_driver.py:67, 133-139`).
- **BUS.S04** `SPI.write_readinto()` returns `None` both on success and on a swallowed `ValueError`
  (`asy_spi_driver.py:83-97`).
- **BUS.S05** UART: `_read_delimited`'s delimiter/skip branches consume buffered bytes without yielding
  (bounded by `rxbuf`) (`src/asy_uart_driver.py:171-176`); `_write_all` waits on `ready(POLLOUT)` with
  no deadline at the *idle* poll rate (`:135, :267`); `readinto(buf, nbytes)` with `nbytes > len(buf)`
  relies on `machine.UART.readinto` clamping (`:353-354`).
- **BUS.S06** `readline()`/`readline_until_complete()` call `machine.UART.readline()` without the
  `any()` clamp, and `:415` has no length bound — a steady newline-free stream would hold the loop for
  its wire time; neither has a production caller (`src/asy_uart_driver.py:395, 410, 415`).
- **BUS.S07** Every I2C transaction allocates new memoryview objects around the long-lived scratch
  (`src/asy_i2c_driver.py:63, 208, 231`).
- **BUS.S08** `Pin(cs_pin)` is bound without a mode and first driven in `setup()`; until then the
  active-low FRAM CS sits at the pad reset default while `machine.SPI()` muxes SCK/MOSI
  (`src/asy_spi_driver.py:43, 117, 181-184`).

Quality measure: every seed confirmed/rejected against rp2 source; never-block invariant re-proven by a
clamp-removal sweep over the current driver.

---

### 5.5 SENS — Sensor drivers

**Goal**: SCD30, SGP40, BMP3xx, ISL29125 correct against their datasheets, robust in every recovery
path, consistent with Part C, and faithful to legacy field behaviour where legacy had one.
**References**: `datasheets/{scd30,sgp40,bmp3xx,isl29125}/`, Parts C, M; legacy
`python/IndividualDrivers/`; `Sensirion/gas-index-algorithm` (VOC reference, external); missing: Sensirion VOC
Index application note (A.6, OR4.a).

Topics:
- [ ] **SENS.T01** Every register/command, CRC, delay, unit conversion and scaling vs the datasheet;
      float32 vs double for every formula that runs on rp2 (BMP compensation, SCD30 offset).
- [ ] **SENS.T02** Config bounds vs helper domains vs datasheet ranges (e.g. `MeanAtmTemp` vs
      `altitude_baro`, `PressOffset` vs the plausibility gate, `BackupPeriod` vs verify period).
- [ ] **SENS.T03** Recovery paths per driver: failed read, CRC error, brownout, divergence re-apply,
      supervisor restart (is every piece of per-instance state re-initialised?).
- [ ] **SENS.T04** Stale-as-fresh, per driver (system-wide contract in `XCUT.T17`): can a cycle publish
      cached values with a new `TS`? ⟨pass 2, answered: rule binds every driver; SCD30 not-ready reuse the one named exception (3.3, `110f3db`); per-driver check of BMP/ISL fallback paths stays U15 — G3: R22⟩
- [ ] **SENS.T05** Interrupt semantics: SCD30 RDY fallback counter, ISL29125 INT thresholds vs the
      decision rule, soft-IRQ allocation, IRQ storms.
- [ ] **SENS.T06** Bus-time budget on `dev`'s shared i2c1 (SCD30 50 ms sleeps under the bus lock vs
      SGP40's 1 Hz cadence vs ISL29125 cycles); VOC processing time on target.
- [ ] **SENS.T07** NVM wear: every SCD30 persistent setter and who can trigger it (REST, loops, tests),
      incl. whether "Unchanged" writes are skipped as legacy did (seed `PAR.S02`). ⟨pass 2, answered: OR42.a/b/c: compare-before-write restored, AmbPres/ForceCalRef always sent — G3: R36⟩
- [ ] **SENS.T08** Part C conformance and D.10 across the four: constructor shape, snapshot-read
      failure logging, errno allocation, operating-range gates, `@web`/`@limits`/`@requires` tags.
- [ ] **SENS.T09** Unverified protocol assumptions: SCD30 reading back 0x0010
      (AmbPres/continuous-measurement command read-back — A.4's AmbPres note, with `PAR.S02`), SGP40
      serial word[0] `== 0x0000` (`SENS.S06`, `SENS.S21`). ⟨pass 2, answered: 0x0010 readback stays (owner-confirmed A.4, L06); 3-word serial read completed (3.3); `word[0]==0` kept on silicon evidence, checked in C — G3: R61, HR047⟩
- [ ] **SENS.T10** Four-tier bus-hazard coverage per driver (CLAUDE.md hard rule), checked against the
      real tier files rather than assumed.
- [ ] **SENS.T11** VOC 1 Hz sampling: Sensirion's algorithm expects one `measure_raw` per second; SGP40
      is driven by a soft PERIODIC timer + `ThreadSafeFlag` that merges ticks missed during loop stalls
      (`NET.S01`/`NET.S02`, FRAM writes, SCD30 bus holds). Measure lost samples and the effect on time
      constants, the 45-sample blackout and `backup_counter` (counts cycles, not seconds) (`XCUT.T21`).
- [ ] **SENS.T12** SGP40 compensation input: age of the wired T/RH (SCD30 `MeasInt` up to 1800 s, value
      cached through its error streak), plausibility/clamping before tick conversion (`SENS.S03`), SCD30
      `TempOffs`/self-heating interplay, `_Default*` sources, mismatched cadences.
- [ ] **SENS.T13** Datasheet operating procedures: SCD30 FRC needs continuous mode at 2 s for ≥ 2 min
      (Interface Description 1.4.5), ASC needs ≥ 7 days uninterrupted power with daily fresh air (1.4.6)
      — vs user-settable `MeasInt`, REST `ForceCalRef` with no precondition/warning, and the soft reset
      on every `setup()`; SGP40 heater-off/idle, self-test in measurement mode (3.3), serial read length
      (3.4); BMP3xx IIR in forced mode (time constant in samples × `SampleInterv` up to 3600 s; CONFIG
      write resets it, 3.4.3) and the recommended osr pairing (Table 5).
- [ ] **SENS.T14** A sensor missing or permanently failed, end to end: `setup()` retry rate,
      persisted-log volume per hour, whether the supervisor score ends in a device reboot, knock-on on
      SGP40 compensation and notifications, legacy parity.
- [ ] **SENS.T15** Persisted logs outside the `_error_check` streak: can a steady fault persist one
      entry per cycle forever, against C.7.1's once-per-episode rule (SGP40 errno 12-18 — 13 from
      `_check_storage` fires every second —, BMP errno 14/22, ISL errno 14/28/31-35, SCD30 forwards)?
      (with `XCUT.T07`). ⟨pass 2, answered: OR35.b + OR56.a (1): a steady identical fault spends one slot; per-code identity checked in U3 — G3: R01, R02⟩
- [ ] **SENS.T16** Hardware I/O triggered by a REST GET: every `_read_sensor_dict` callback (SCD30
      six-register snapshot, BMP bit-field snapshot, ISL snapshot + divergence re-apply + wrnno 11) —
      cost under the bus lock, side effects, GET safety/idempotency (with `REST.T10`).
- [ ] **SENS.T17** `@requires` tags vs each datasheet's bus limits: ISL29125 (400 kHz max) and BMP3xx
      carry none (with `GEN.T08`).

Seeds:
- **SENS.S01** SGP40 `get_raw()` points `self._command_buffer` at `_measure_command` and restores it
  without `try/finally`; after any failed read the alias persists across supervisor restarts, and
  `initialize()` then writes the serial/self-test commands into the 8-byte measure buffer and sends all
  8 bytes; untested (`src/asy_sgp40_driver.py:612-616, 673-687`).
- **SENS.S02** SGP40 FRAM verify period `int(math.ceil((10*60)/p)*0.1)` is 0 for `BackupPeriod` 67-1440
  (verification disabled) and off by one elsewhere (p=7 → 8, intended 9) (`asy_sgp40_driver.py:353, 410`).
- **SENS.S03** SGP40 compensation ticks are masked `& 0xFFFF` instead of clamped: RH −1 % → ~99 %, RH
  101 % → ~1 %, T 131 °C → ~−44 °C; inputs are not clamped upstream (`asy_sgp40_driver.py:599, 606`).
- **SENS.S04** VOC = 0 is stored as a valid reading during the 45-sample blackout after every
  init/reset; the datasheet index range is 1-500 (`voc_algorithm.py:761-762, 780`;
  `asy_sgp40_driver.py:448-451`).
- **SENS.S05** `_run_restore` re-reads the 260-byte FRAM chunk every second while waiting up to 600 s
  for NTP (`asy_sgp40_driver.py:213-216, 384-386`).
- **SENS.S06** SGP40 serial-number check `word[0] == 0x0000` is an undocumented Adafruit assumption
  (`asy_sgp40_driver.py:678-682`).
- **SENS.S07** SGP40 measure wait is 100 ms against a 30 ms datasheet maximum (inferred cost only)
  (`asy_sgp40_driver.py:614-615`). ⟨pass 2, answered: 100 ms is owner-directed (`5ff8c0b`, 2026-07-21); margin stated — G3: R30⟩
- **SENS.S08** SCD30 `scd_timer_triggers` accumulates across cycles (comment says "consecutive") and
  forces a read even when RDY is low; the not-ready read leaves the cache untouched and `_read_scd`
  re-stamps cached values as fresh — legacy-identical (`src/asy_scd30_driver.py:174-187, 412-420, 610-611`).
- **SENS.S09** SCD30 `int(offset*100)` truncates 0.01 K low for ~6.5 % of 0.01-step values in float32
  (0.53 → 52, 1.05 → 104) (`asy_scd30_driver.py:570`) — A.4 documents truncation as deliberate; the
  float32 representation effect is the new part.
- **SENS.S10** SCD30 has no CO2/RH/T plausibility gate (datasheet 0-40000 ppm), only finiteness, though
  C.3 says operating-range checks live in layer 2 (`asy_scd30_driver.py:621-630`).
- **SENS.S11** SCD30 sleeps 50 ms inside the bus lock per command/register read; `get_config_snapshot`
  holds i2c1 ≥ 6×50 ms (`asy_scd30_driver.py:471, 483, 514-520`). ⟨pass 2, answered: 50 ms owner-tested (`144873f`, 2026-07-13); snapshot hold measured under SENS.T06 — G3: R30⟩
- **SENS.S12** BMP3xx `MeanAtmTemp` accepts −50..50 but `altitude_baro` requires −40..85, so [−50, −40)
  silently yields `SLPres = None` (`src/asy_bmp3xx_driver.py:84`; `math_helpers.py:25-26, 92`).
- **SENS.S13** BMP3xx plausibility gate runs before `PressOffset` (±500 hPa) is applied, so a published
  `Pres` can leave the datasheet range and `SLPres` becomes `None` with no log
  (`asy_bmp3xx_driver.py:237`).
- **SENS.S14** BMP3xx `get_altitude()`/`get_pressure()`/`get_temperature()` have no production caller
  (`asy_bmp3xx_driver.py:555-577`). ⟨pass 2, answered: stay (OR36.a (3)) — G3: R21⟩
- **SENS.S15** ISL29125: in high range INT is armed on green ≤ down-threshold, but `_evaluate_range`
  decides on the peak of all three channels, so a colour-dominant scene (or `AutoRangeDwell`, or
  darkness on the low range's 0 threshold) can fire INT every PRST window and force a read cycle
  indefinitely (`src/asy_isl29125_driver.py:359-364, 577-583, 598-599`).
- **SENS.S16** ISL29125 `set_autorange_thresh()` does not rewrite the chip's threshold registers,
  unlike `set_resolution()` (`asy_isl29125_driver.py:981-988` vs `:941-945`).
- **SENS.S17** ISL29125 small: the 1-count dark offset is subtracted after `<<4`, so at 12 bit it is
  1/16 count (`:1262-1263`); `_filtered` survives a restart (`:270`); calibration legs stall the read
  loop.
- **SENS.S18** Part C divergences: ISL29125 constructor order/kw-only
  (`asy_isl29125_driver.py:197-212`); SGP40's `fram_storage`/`fram_ntp_callback` names
  (`asy_sgp40_driver.py:140-141`); snapshot-read failure logging differs (BMP errno 22
  `asy_bmp3xx_driver.py:177`, ISL errno 28 `asy_isl29125_driver.py:723`, SCD30 base errno 4
  `src/base_classes.py:210`).
- **SENS.S19** C.3 text is stale: BMP3xx "has no scratch buffer" (the I2C layer now has one)
  (SPECIFICATION.md ~1541-1543).
- **SENS.S20** Missing references: Sensirion's VOC Index application note (host blocked by the session's
  egress policy, OR4.a). Added 2026-09-25: BMP390, WS2812, W25Q16JV, CYW43439 and RP2040 datasheets; the VOC C reference is reachable at `Sensirion/gas-index-algorithm`. ⟨pass 2, stale: verified: `datasheets/sgp40/` holds the three VOC notes (OR53 (2)); `gia` reachable; nothing missing — G3: R29⟩
- **SENS.S21** The SGP40 serial-number read fetches 3 of the 9 bytes the datasheet specifies
  (`readlen=1`), so only word 0 is CRC-checked and compared (`asy_sgp40_driver.py:673-682`; datasheet
  3.4, Tables 8/16). ⟨pass 2, answered: 3-word read completed (3.3) — G3: HR047⟩
- **SENS.S22** `SCD30_I2C.setup()` sends a soft reset on every read-loop (re)start
  (`asy_scd30_driver.py:577-589`); 1.4.10 says it restores the power-up state, and 1.4.6 says ASC's
  first 7-day search aborts on power interruption — whether a soft reset aborts it is undocumented.
- **SENS.S23** BMP3xx polls STATUS every 2 ms (~60 bus transactions per ×32/×32 conversion on a
  possibly shared bus) although the conversion time is computable (3.9.2) (`asy_bmp3xx_driver.py:408, 541-553, 623`).
- **SENS.S24** An ISL29125 `GET /sensors` can write both the chip and the FRAM ring:
  `_read_sensor_dict()` → `_check_divergence()` → `configure(force=True)` + `wrn_s` 11
  (`asy_isl29125_driver.py:716-728, 745-755`) — possibly intended (comment `:717-719`); record either
  way.
- **SENS.S25** When a config read fails, BMP3xx and ISL29125 still publish a freshly stamped sample
  with hard-coded fallbacks, silently dropping the user's offsets/filter
  (`asy_bmp3xx_driver.py:231-234`; `asy_isl29125_driver.py:503-507`) (with `XCUT.T17`).
- **SENS.S26** No driver's `stop_timer()` has a production caller (`asy_scd30_driver.py:233`,
  `asy_sgp40_driver.py:484`, `asy_bmp3xx_driver.py:305`, `asy_isl29125_driver.py:871`; NET's
  `asy_ntp_client.py:357, 360`, `asy_wifi_service.py:677`).
- **SENS.S27** ISL29125 `time_to_settle_ms()` is `max(0, ticks_diff(_settle_until_ms, now))`
  (`asy_isl29125_driver.py:1292-1293`), with `_settle_until_ms` set only at start-up (`:1078`) and on a
  CONFIG1 write (`:1383`): after > 2**29 ms without a CONFIG1 write it returns up to ~6.2 days, so
  `_settle_wait()` sleeps that long (`:380-381, 614-623`) and `_evaluate_range()`, reached only after
  `_settle_wait()` returns, blocks no switch independently (`:575`) — the task stays alive but publishes
  nothing ~6.2 days of every 12.4 (masked by a CONFIG1 write only if it lands before the first read
  after the crossing — a PUT during the in-flight `sleep_ms(≈2**29)` does not wake it, and
  `_settle_wait`'s "bounded" comment at `:615-617` assumes a short deadline; likeliest with `RangeAuto`
  off; possible escalation `XCUT.S15`). Same class: `_measured_ratio()` republishes a stale `GainMeas`
  (`:699-709`, contradicting `:706`), and AutoRangeDwell blocks down-switches (`:586`) (`XCUT.T25`).
- **SENS.S28** SGP40 `W13` now spends one slot per NTP outage (`83c9920`): the episode is the in-RAM
  `_no_ts_episode` (`asy_sgp40_driver.py:167, 433, 440, 443-444`), so a reboot or a supervisor restart
  mid-outage opens a new episode and a new slot, and a deferred backup or an `E14` write failure does not
  end one (`tests/test_asy_sgp40_driver.py:1125-1128`). Check that against C.7.1's per-episode rule and
  the other episode flags (WIFI per connect episode, NTP until a sync) for one shared meaning (`XCUT.T07`). ⟨pass 2, answered: episode flag replaced by the central rule (OR35.a (4)); reboot/restart episode question has no object — G3: R01⟩

Quality measure: a datasheet-citation per register/formula; every seed resolved; a float32 emulation
run for each formula; restart-state table per driver.

---

### 5.6 STOR — FRAM storage

**Goal**: the dual-copy chunk store's integrity guarantees (all-or-nothing loss, busy markers, write
protection as an access gate, pause gating, determinism) hold under every fault and interleaving.
**References**: A.4 FRAM bullets, C.7.1 FRAM row, I.4(f.1); `datasheets/fram/` (MB85RS64V on field devices; dev's part per `HW.T07`).

Topics:
- [ ] **STOR.T01** Block/chunk state machine: UNINIT/IDLE/BUSY transitions for read, write, clear,
      repair; torn states at each step; blank-chunk reads.
- [ ] **STOR.T02** Dual-copy repair decisions (block 0 invalid, block 1 invalid, both valid-different)
      and their CRC coverage.
- [ ] **STOR.T03** Write-enable/WEL/WRDI handling, write verification cadence, status-register
      protection bits (volatile vs non-volatile), partial protection.
- [ ] **STOR.T04** (module half of `XCUT.T06`) Locking: driver lock + bus lock held together per block;
      chunk `_op_lock`; logging while holding the driver lock (deadlock invariant).
- [ ] **STOR.T05** Pause gating: who sets pause (`mempause` 300 s, reboot paths); writes during a pause
      are dropped, not deferred (a log entry is lost); `override_pause` has no production caller
      (`STOR.S07`); interplay with `XCUT.T13`/`CORE.T06`. ⟨pass 2, answered: `override_pause` is a test artifact and goes (OR36.a (1)); pause semantics in R02 — G5: R02, HR073⟩
- [ ] **STOR.T06** Timestamped chunks: NTP gating, `(ntp_synced, utc, success)` ordering.
- [ ] **STOR.T07** Address width / product-ID mapping for both chip sizes; wraparound; out-of-range.
- [ ] **STOR.T08** errno/wrnno ranges vs C.7.1 (drift noted; catalogue owned by `XCUT.T07`); the chunk
      layer's logger ownership (`XCUT.S08`) and the layout/8 KB budget (`XCUT.T09`, `XCUT.S09`) are this
      module's too.
- [ ] **STOR.T09** Timestamped chunks across clock changes: `age = now - ts` negative or jumping when
      the RTC is set backwards, `NTP_Offset_S` changes (±12 h, shifts the RTC itself) or a pre-NTP clock
      runs; `BackupMaxAge` accepts any negative age (`asy_fram_manager.py:609-614`;
      `asy_sgp40_driver.py:390`); `_TS_UNINIT = 0` as sentinel (with `XCUT.T18`, `NET.T11`).
- [ ] **STOR.T10** Reads are writes: every `_read_chunk` writes BUSY then IDLE to both status bytes
      (`:299, :343`) — refused under write protection/pause, power loss during a *read* leaves BUSY, and
      the status bytes are the most-written cells: compute per-byte endurance for the busiest ring vs
      10^12 (MB85RS64V) / 10^13 (MB85RS2MTA) — whichever part `dev` really has is `HW.T07`'s question.
- [ ] **STOR.T11** SPI electrical contract vs both FRAM datasheets: mode 0 at the 1 MHz default
      (`asy_spi_driver.py:55-57`; no baudrate from codegen) vs 20/40 MHz maxima, CS setup/hold, HOLD/WP
      tie-offs per board, power-up time before the first RDID; the FRAM driver has no `@requires` tag.
- [ ] **STOR.T12** Crash-consistency enumeration on a twin FRAM image: power loss after every SPI
      transaction k of write/read/clear/repair; classify the next boot per owner (log ring, SGP40
      backup) (with `TWIN.T04`/`TWIN.S04`).

Seeds:
- **STOR.S01** `_set_check_sb` writes BUSY even when it found UNINIT and `_read_chunk` returns early
  without restoring, so a second read of a never-written/cleared chunk reports errno 31/33 "invalid"
  instead of "uninitialised"; untested (`src/asy_fram_manager.py:235-250, 306-308`).
- **STOR.S02** `_write_chunk`/`_read_chunk` call `self.pr.err_s` while holding the FRAM driver lock —
  safe only because the chunk logger is RAM-only; a FRAM-backed logger (what C.7.1 says happens) would
  deadlock on the non-reentrant lock; nothing enforces it (`asy_fram_manager.py:278-289, 320-355`).
- **STOR.S03** `setup()` sets `_wp` only when the status register equals 0x8C exactly; a chip with BP
  bits partly set is treated as writable (`src/asy_fram_driver.py:388`).
- **STOR.S04** C.7.1's FRAM row: "manager errno 17-88" vs code using 10/11/19/20; C.3's "fresh buffer
  per call" for FRAM_SPI vs preallocated buffers and no `_send_opcode` (`asy_fram_driver.py:118-121`;
  SPECIFICATION.md ~1544-1545, ~1926).
- **STOR.S05** `verify_present()`/`set_write_protected()` have no production caller and are SETTLED as
  kept (`src/asy_fram_driver.py:357, 400`; BACKLOG.md:52) — record as settled-no-action. ⟨pass 2, answered: stays, settled-no-action (OR36.a (3), V14) — G5: HR084⟩
- **STOR.S06** `FRAM_SPI`'s `wp_pin` path is unreachable in production (`AsyFramManager` never forwards
  it, `asy_fram_manager.py:628`; codegen emits only `max_size`/`debug`, `buildgen/codegen.py:203`) and
  treats the pin as whole-array protection (`asy_fram_driver.py:217-220`), while the MB85RS64V WP pin
  only guards the status register when WPEN=1.
- **STOR.S07** No `src/`/`buildgen/` code passes `override_pause=True`; the parameter on every chunk
  method is test-only API (`asy_fram_manager.py:96, 128, 389`). ⟨pass 2, answered: test artifact, removed (OR36.a (1)) — G5: HR073⟩
- **STOR.S08** An out-of-memory FRAM allocation is reported only through print-only `pr.err`
  (`asy_fram_manager.py:649, 662, 691, 704`; `asy_sgp40_driver.py:187`): a layout overflowing 8 KB
  (`XCUT.S09`) silently drops owners to RAM-only with nothing persisted. ⟨pass 2, answered: no errno/wrnno for out-of-FRAM memory, mpremote check (owner, A12) — G5: R32, R33⟩

Quality measure: every state transition covered by a named test at mock and twin tier; seeds resolved.

---

### 5.7 UART — UART protocol

**Goal**: `UART_Comm` conforms to Part J exactly; Part J is complete and unambiguous as the
two-implementation contract; every change is logged in `UART_C_PORT_CHANGELOG.md` with its class.
**References**: Part J, F.5.7-F.5.9, `UART_C_PORT_CHANGELOG.md`; the C side is out of scope (owner),
so no reconciliation — but Part J must remain sufficient for someone who does one.

Topics:
- [ ] **UART.T01** Frame/transaction rules vs Part J line by line (UID, CMD, SIZE, CHUNKS, CUR_CHUNK,
      ACK withholding, GET as one-chunk train).
- [ ] **UART.T02** Recovery: resync drain window/bound, write hold-off, blind-resync diagnostic, cancel
      handshake, listen backoff.
- [ ] **UART.T03** Allocation: preallocated buffers, peer-declared `CHUNKS` allocation (BACKLOG
      accepted-with-caveat), rejection bitmap.
- [ ] **UART.T04** (with `XCUT.T07`, `CORE.T05`) Logging: per-episode dedupe keyed on last errno only,
      `_ready()` flooding, repeat-counting vs C.7.1. ⟨pass 2, answered: OR35.b central rule + OR56.a (1) one entry per event — G6: R20⟩
- [ ] **UART.T05** Construction validation (timeout floor, rxbuf floor) vs buildgen's own checks
      (`GEN.T01`, L.6.6).
- [ ] **UART.T06** `UartLinkExerciser` (bench-only): counters, supervision, FRAM wiring, whether its
      failure modes can pollute the persisted log at 1 Hz.
- [ ] **UART.T07** `UART_C_PORT_CHANGELOG.md` completeness vs git history of `asy_uart_comm.py`, and
      whether a "temporary" file with no reachable deletion trigger should be reclassified (touches
      SETTLED, see `DOC.S14`) (seed `DOC.S14`).
- [ ] **UART.T08** End-to-end delivery semantics: a lost final ACK makes the initiator report failure
      after the responder already delivered the SET / ran `get_callback` — at-least-once with caller
      retries, at-most-once without. What does Part J promise; must commands be idempotent? ⟨pass 2, answered: lost final ACK folds into failure (owner, 2026-09-11); at-least-once, caller tolerates duplicates — G6: R14⟩
- [ ] **UART.T09** Cancellation/restart mid-transaction (supervisor restart, reboot, `clear()`):
      `_busy`/`_in_resync`/hold-off state, a half-sent frame on the wire, peer recovery, a listen-task
      restart while the peer is mid-train (with `XCUT.T19`).
- [ ] **UART.T10** Measured constants the contract rests on: `_GC_PAUSE_WORST_MS = 21` (under what
      heap, threshold, firmware?) and J.6's floors re-derived from `devices/dev.toml`'s
      baudrate/rxbuf/poll_*; what would invalidate them (with `PLAT`, `MEM`).

Seeds:
- **UART.S01** `[x2]` `UART_Comm._err` sends repeats to the sync `pr.err()`, which neither persists nor
  counts, while C.7.1 says `repeat=True` "still counts it" — UART repeats never reach `ErrCount`
  (`src/asy_uart_comm.py:319-322`; sync `err()` `src/print_log.py:112-114` vs persisting `_store_err()`
  `:158-175`, which does count repeats). ⟨pass 2, overtaken: per-module repeat routing removed by the central rule (OR35.b) — G6: R20⟩
- **UART.S02** A GET frame's `CHUNKS=1` is not enforced (`asy_uart_comm.py:484-488`) though J.4 defines
  a GET as a one-chunk train.
- **UART.S03** Dedupe keyed only on the last errno, cleared by every valid frame: a link alternating
  good/bad or between two errnos persists on every fault (`:319, :658-661`); `_ready()` calls `err_s` on
  every call, so a failed `setup()` plus the exerciser's 1 Hz `uart_get` persists an entry per second
  (`:351-355`; `src/asy_uart_link_driver.py:110-120`). ⟨pass 2, answered: identical code spends no slot (OR35.b); alternation out of scope (OR35.a (3)) — G6: R20⟩
- **UART.S04** The `dev` link runs with `CRC_Pass`: codegen never passes `crc=`
  (`buildgen/codegen.py:396-397`) — a corrupted payload byte is caught only structurally. Enabling CRC
  alters emitted bytes — Class A, owner decision, changelog entry. ⟨pass 2, answered: `CRC_Pass` is the supported interim, Python leads a recorded flag day (A02); wire frozen for the audit — G6: R03⟩
- **UART.S05** A declined command returns `cmd_id=None`, sending `_listen_loop` into backoff up to
  5×timeout while the initiator may already be retrying (`asy_uart_comm.py:1116-1126`).
- **UART.S06** `UartLinkExerciser.reset_error_counter()` also zeroes `transfers`/`failures`, so
  `ResetErrors` wipes measurement data, not only error history (D.10 vs other modules)
  (`src/asy_uart_link_driver.py:157-160`).
- **UART.S07** `_holdoff_active` stays set after a resync (`src/asy_uart_comm.py:576`) until the next
  initiator write reads it (`:516-529, 630`); only `uart_listen` clears it early (`:990`). A first write
  > 2**29 ms after a resync can wait up to ~6.2 days in `_await_write_gate()` — hidden on `dev` by the 1 Hz
  exerciser, relevant because the module is standalone for other applications (`XCUT.T25`).
- **UART.S08** `UART_Comm.timeout`, `poll_wait_ms` and `poll_idle_ms` have lower bounds only (`asy_uart_comm.py:243-246, 252-258`; "never clamps" is the stated design), and large values fail on rp2 only: from timeout 107,374,183 the 5×timeout backoff cap (`:219`) makes `sleep_ms(backoff)` raise `OverflowError` at `:1125`, outside the loop's `try` (`:1114-1124`) — the task dies and burns the supervisor's error budget, which `:1109-1111` says must never happen; from ~89.5e6 the drain's 6×timeout "hard bound" (`:545-550`) can never fire; from ~3.58e8 `_hold_off_writes()`'s `ticks_add` (`:528`) raises; from 2**29-1 `asy_uart_driver.ready()` can never time out (`:284`); a poll value ≥ 2**29 makes `sleep_ms` raise at `asy_uart_driver.py:286`, which the `except` at `:287` does not catch (`XCUT.T25`).

Quality measure: Part J ↔ code traceability table; every seed resolved; changelog complete.

---

### 5.8 NET — Networking

**Goal**: the WiFi/NTP/DNS/UDP/captive-DNS state machines are complete, bounded, non-blocking and
match legacy field behaviour or document the change.
**References**: A.4 "confirmed intentional" WiFi rules, C.8 (WiFi locking), F.2 (backstops), H.7
(connection ceiling), B.14.2 (lwIP), legacy `python/CommonDrivers/async_connect.py`; RFC 1035/5905.

Topics:
- [ ] **NET.T01** WiFi state machine: every phase × event, incl. task restart in each phase, PUT during
      a mode switch, PUT while `DEACTIVATED`, a client joining as the hotspot timer fires, a router
      outage at boot longer than the fail-to-hotspot + hotspot window, mid-handshake interruption by the
      5 s poll (security/parity sides: `SEC.T04`, `PAR.S08`).
- [ ] **NET.T02** (with `XCUT.T06`; budget in `PERF.T05`) `wifi_mode_lock` hold spans (connect poll, 60
      s sleep, NTP attempt) and what stalls meanwhile (uptime counters, `/status` getters, reconnect,
      NTP).
- [ ] **NET.T03** (threat side in `SEC.T05`/`SEC.T11`) NTP: sync/backoff/retry schedule, stale-sync
      reachability, ONE_SHOT retry timer vs C.9, reply validation (mode, version, origin timestamp, LI,
      stratum, KoD), RTC set semantics, EU-only DST rule vs configurable offsets, socket cleanup on
      cancel.
- [ ] **NET.T04** DNS client: query building (labels, trailing dot, 255-octet limit), response parsing
      (TC bit, uncompressed names, CNAME chains), server order incl. the public fallback.
- [ ] **NET.T05** (with `PLAT.T04`, B.14.2) UDP socket: poll strategy and idle cost, sentinel contract,
      `disconnect()` on every exit path, PCB budget (`MEMP_NUM_UDP_PCB = 5`) across
      DHCP/DNS/mDNS/captive DNS/NTP and STA↔AP transitions.
- [ ] **NET.T06** Captive DNS: QTYPE handling, QR bit, TTL after leaving hotspot, allocation per query,
      unsupervised task lifetime across mode switches, subnet filter.
- [ ] **NET.T07** Radio-string bounds (C.7.4 bytes) at write and at use; hostname cap vs legacy.
- [ ] **NET.T08** CYW43 synchronous calls per request (`status("rssi")`, `ifconfig()`), their cost and
      behaviour in AP mode.
- [ ] **NET.T09** Hotspot/captive portal end to end: AP security mode actually set (no explicit
      `security=`, `asy_wifi_service.py:384`), channel/country, AP subnet and DHCP pool vs the captive
      subnet filter, station limit, OS probe URLs (`/generate_204`, `/hotspot-detect.html`,
      `/connecttest.txt`) → 302 → index, HTTPS/DoH/"Private DNS" bypassing the portal, the 60 s TTL
      after leaving hotspot mode (with `REST.T07`).
- [ ] **NET.T10** Sockets across WLAN mode switches and `wlan.deinit()`: listening HTTP socket,
      in-flight TCP connections, captive-DNS/NTP/DNS UDP PCBs when the netif is torn down (STA↔AP,
      deactivation) (with `NET.T05`, `PLAT.T04`).
- [ ] **NET.T11** Clock jumps: first RTC set from the boot default, `NTP_Offset_S` shifting the RTC,
      DST boundaries, and every wall-clock consumer (`TS`, FRAM backup age, notification window,
      `cettime`) (with `XCUT.T18`, `STOR.T09`, `SEC.T11`).
- [ ] **NET.T12** D.9 sweep of the network API on 1.29: magic `pm=0xA11140` vs `WLAN.PM_*` (`:386, :452`),
      `_STAT_OBTAINING_IP = 2` (`:128`), `status("stations")` shape, explicit `security=` for STA/AP,
      `network.hostname()` semantics (DHCP option, mDNS).
- [ ] **NET.T13** DHCP/IP lifecycle while connected: lease renewal, address/DNS-server change, gateway
      loss while `isconnected()` stays true (F.2 backstop — not re-opening it), hostname collisions.

Seeds:
- **NET.S01** `wifi_mode_lock` is held across `asyncio.sleep(60)` in `_on_sta_disconnected`, stalling
  NTP, uptime updates and PUT-triggered reconnects for 60 s (`src/asy_wifi_service.py:473` inside
  `:583-590`).
- **NET.S02** NTP holds `wifi_mode_lock` for its whole attempt (up to 3 DNS servers × 500 ms + 5000 ms
  fetch); meanwhile WiFi's 1 s `ThreadSafeFlag` ticks collapse, so `WifiUptime` undercounts and
  `/status` shows `IPv4`/`Rssi` as null (`src/asy_ntp_client.py:433-440`).
- **NET.S03** `[x2]` NTP "stale after 3× interval" can never trigger: `ntp_sec_count` resets at every
  due resync, failed ones included, so `Synced` stays True forever after the first success —
  legacy-identical and pinned by `tests/test_asy_ntp_client.py:1388-1410` (`asy_ntp_client.py:456-471`).
- **NET.S04** `[x2]` The DNS client falls back to `8.8.8.8` and `1.1.1.1` after the DHCP server —
  undocumented in SPECIFICATION/BACKLOG, a network/privacy behaviour change vs legacy's system resolver
  (`src/asy_dns_client.py:20, 110`). ⟨pass 2, answered: OR56.a (2): config value, today's servers default, emptiable — G6: R34⟩
- **NET.S05** `get_dns_server_ip()` returns `None` whenever the lock is held when NTP samples it, so
  NTP silently uses only the public resolvers — fails on networks that block external DNS
  (`asy_ntp_client.py:431`).
- **NET.S06** `ntp_force_sync()` no longer clears `Synced` (legacy did): after an NTP-settings PUT with
  a bad host, local time and notifications keep running on the old sync (`asy_ntp_client.py:416-422` vs
  legacy `async_connect.py:129-135`).
- **NET.S07** `_poll_sta_connect_status` does not break on `STAT_GOT_IP`; every successful connect
  costs the full 5 s under the lock (`asy_wifi_service.py:616-621`).
- **NET.S08** `_run_hotspot_mode` repeats the full mode switch (deinit + new `WLAN`) on any tick where
  AP status ≠ `STAT_GOT_IP`, re-setting `hotspot_started_once` (`asy_wifi_service.py:570`).
- **NET.S09** A task restart during HOTSPOT forces `reconn_wifi` and resets `hotspot_started_once`,
  which differs from the comment at `:305` and A.4's "left as-is" (`asy_wifi_service.py:311`).
- **NET.S10** `captive_dns` receives with `recvfrom(4096)` per datagram (16× I.3's 256 B design bound,
  contradicting I.2's "small, fixed" claim); NTP allocates 1024 B for a 48 B reply
  (`src/captive_dns.py:98`; `asy_ntp_client.py:185`).
- **NET.S11** Captive DNS polls at 50 Hz forever while the hotspot is up (`timeout_ms=-1` over a 20 ms
  `ipoll(0)` loop) — the idle-poll cost F.5.9 fixed for UART (`src/asy_udp_socket.py:126`).
- **NET.S12** Captive DNS answers every QTYPE (AAAA, HTTPS) with an A record while echoing the QTYPE,
  doesn't check QR, and builds f-strings for `pr.evt` on every query regardless of level
  (`captive_dns.py:109-121` f-strings, `:170-171` QR/opcode parsing, `:203-210` A answer).
- **NET.S13** `_fetch_ntp_reply` has no `disconnect()` in `finally`, unlike `resolve_ipv4`; a cancel
  mid-fetch leaks a UDP PCB until GC (`asy_ntp_client.py:183-188` vs `asy_dns_client.py:117-120`).
- **NET.S14** DNS query building: trailing dot/empty label → malformed query; no 255-octet QNAME check
  (`NTP_Host` allows 1024); TC bit unchecked; only answers starting with a compression pointer parsed
  (`asy_dns_client.py:44-62` query building, `:71-85` response parsing).
- **NET.S15** `get_wlan_rssi()` prints an error on every `/status` in hotspot mode;
  `WifiUptime`/`Connected` count up in AP mode (`asy_wifi_service.py:760`; AP counting `:503-512, 851-858`).
- **NET.S16** `PW` accepts 8-63 characters (excludes a raw 64-hex PSK); the masked `"********"` from a
  GET, if PUT back, would be stored as the password — check the JS client (`WEB.T02`)
  (`asy_wifi_service.py:46, 197-201`).
- **NET.S17** Bounds vs legacy: Hostname 1-63 → 1-32, SSID min 2 → 0, `PW` `""` = open network (legacy
  `""` meant "unchanged"), `HotspotPW` build-time only (not in any `SettingsGroup`,
  `buildgen/codegen.py:607`). ⟨pass 2, answered: new API is the reference (OR58.a); `""` = open, sparse PUT expresses "unchanged", UI sets no empty string (A24); hostname 32 is the port cap — G6: R28, R38⟩
- **NET.S18** Comment drift: `asy_udp_socket.py:176` names a nonexistent `_open()`;
  `asy_wifi_service.py:168-169` mentions a future "combined Networking endpoint".
- **NET.S19** NTP discards the reply's source address and sends an all-zero transmit timestamp, so an
  origin-timestamp check is impossible; whether lwIP's connected-PCB filter already enforces the source
  is unverified (`asy_ntp_client.py:183-184`) (feeds `SEC.T05`).
- **NET.S20** The hotspot AP is configured with `essid`/`password` only, so its auth mode is the cyw43
  default — verify on 1.29 that it is WPA2-AES, not mixed/open (`asy_wifi_service.py:384`).

Quality measure: complete phase × event table for WiFi; lock-hold table; every seed resolved.

---

### 5.9 REST — Web server and HTTP surface

**Goal**: every byte a client sends is bounded before it is allocated; every route validates and
answers with the documented envelope; the server survives hostile and pathological clients; our
wrappers cover every gap in vendored Microdot (A.5).
**References**: A.5, A.8, H.6, H.7, I.3, I.6; `ext/microdot.py` v2.6.2; MicroPython
`extmod/asyncio/stream.py`, `py/stream.c` at `v1.29.0`.

Topics:
- [ ] **REST.T01** (with `MEM.T03`, `SEC.T05`) Allocation-before-check sweep: Content-Length (negative,
      huge, non-numeric, duplicate), request line and header line length, header count, query string,
      JSON depth/size, path length — each against Microdot's actual order of operations.
- [ ] **REST.T02** Route table: every GET/PUT, validation, envelope, status codes, HEAD/OPTIONS
      behaviour, unknown keys, non-object bodies, wrong Content-Type.
- [ ] **REST.T03** `PUT /sensors` vs settings-group routes: guarding, post hooks, result shape (D.10) —
      owned by `XCUT.T11` (with `CORE.T04`, `CORE.S06`). ⟨pass 2, dup: of `XCUT.T11` (owner there) — G6: R41⟩
- [ ] **REST.T04** (with `SEC.T02`, `PERF.T03`, `HW.T02`) Command fields: `SystemCmd`, `lightCmdLED`,
      `PauseTime`, `ResetErrors` — validation, Invalid vs Failed semantics, blocking duration,
      idempotency, confirmation for irreversible ones.
- [ ] **REST.T05** Streaming (`_PieceWriter`): piece bound in bytes (not characters), exact
      Content-Length, per-source guarding in `/status`.
- [ ] **REST.T06** (budget in `PERF.T02`) Connection lifecycle: `_TimeoutStreamProxy`, `outer_cap_s`,
      `max_connections`, backlog, slot release lag (H.7.1), stream closing on HEAD/abort/error.
- [ ] **REST.T07** Static serving: `..` handling, `.gz` lookup, 302-in-hotspot, caching headers,
      Content-Type/charset.
- [ ] **REST.T08** (with `XCUT.T07`, `CORE.S11`) Logging from the webserver: `wrn_s` without `repeat=`
      on routine idle/aborted connections vs FRAM ring churn. ⟨pass 2, answered: central repeat rule (OR35.b) — G6: R20⟩
- [ ] **REST.T09** Verify A.5's gap list against v2.6.2 source and note what v2.7.0 changes; confirm
      every fix stays outside `ext/`.
- [ ] **REST.T10** GET routes with hardware side effects and latency: `/sensors` (live register
      snapshots, ISL re-apply), `/status` (`rssi`, `ifconfig`, every logger's `get_log()`) — worst-case
      duration vs `per_call_timeout_s`/`outer_cap_s`, bus-lock contention under 6 clients (with
      `SENS.T16`, `PERF.T02`/`T04`).
- [ ] **REST.T11** JSON-safety sweep: every float that can reach a body must be finite (bare
      `nan`/`inf` from MicroPython `json`, F.1) — BMP compensation, ISL HSB/CCT, `math_helpers`,
      NTP/notification values, stored config; non-ASCII SSID/hostname (with `XCUT.T23`).
- [ ] **REST.T12** HTTP framing interop: `Expect: 100-continue` (curl, bodies > 1 KB),
      `Transfer-Encoding: chunked` without Content-Length (→ `body=b''`, `ext/microdot.py:423-430`),
      keep-alive/pipelining vs HTTP/1.0, absolute-form targets, percent-encoded paths (routes match
      undecoded), query strings on API routes, gzip regardless of `Accept-Encoding`.
- [ ] **REST.T13** Client-triggerable stdout: Microdot `print_exception()` for every unparsable request
      (`ext/microdot.py:1407-1408`) plus every `pr.*` print; on rp2 1.29 `mp_usbd_cdc_tx_strn` may wait
      up to `MICROPY_HW_USB_CDC_TX_TIMEOUT` per print when a CDC host is attached but not reading — a
      LAN-triggerable loop stall on the bench (with `PERF.T11`, `PLAT.T03`).

Seeds:
- **REST.S01** `Content-Length: -1` appears to bypass the 2048 B body cap: `Request.create` does
  `int(value)` and reads the body when `content_length <= max_body_length`; `readexactly(-1)` becomes
  `read(-1)` = read-all (up to ~`TCP_WND` 6400 B), and a follow-up negative read hits `py/stream.c`'s
  `MemoryError` path — i.e. a client-triggered `MemoryError`, contradicting I.6 and the
  zero-`MemoryError` bar (`ext/microdot.py:417-426`; upstream `extmod/asyncio/stream.py:41-52`). Not
  executed. Any fix must live outside `ext/`.
- **REST.S02** Header lines and header count are unbounded before Microdot's `max_readline` check,
  because asyncio `readline()` grows with O(n²) copies until `\n`; bounded only by the 5 s per-call and
  15 s outer timeouts; untested (`ext/microdot.py:412-421, 533-537`).
- **REST.S03** `[x2]` (owned by `XCUT.T11`) `_put_sensors` calls `module._set_dict_cfg()` directly,
  bypassing `ar.handle_set_cmd` (no errno-99 guard, no post hooks), unlike the flat routes
  (`src/asy_webserver_service.py:420-432`).
- **REST.S04** `[x2]` `_put_status` resets every error source sequentially with no guard: an exception
  leaves a partial reset and a 500; no confirmation for an irreversible evidence wipe (`:631-637`). ⟨pass 2, answered: global only (OR70.a (7)), concurrent (OR72.a (5)), detected failure "Failed" (OR70.a (6)); no confirmation under the trusted-LAN model (OR52.a (3)) — G6: R50⟩
- **REST.S05** WEBSERVER `wrn_s` calls never pass `repeat=`, so every idle/reclaimed connection
  (browser speculative preconnects) spends a FRAM ring slot; same for DNSSRV (`:254, :715-724`;
  `src/captive_dns.py:119, 123`). ⟨pass 2, answered: OR35.b: no per-origin special case; identical codes spend no slot — G6: R20⟩
- **REST.S06** `_PieceWriter` counts characters, not bytes: non-ASCII SSID/hostname values make pieces
  larger than `chunk_bytes` (`:145-148`).
- **REST.S07** HEAD requests and aborted static responses never `aclose()` the opened stream (relies on
  GC) (`asy_webserver_service.py:655-667`; `ext/microdot.py:684-699`).
- **REST.S08** `[x2]` No `Cache-Control`/ETag on static files: every visit re-downloads index and
  `app.js` on a CPU-bound server with a ceiling of 6 connections (`asy_webserver_service.py:649-667`).
- **REST.S09** `[x3]` REST `lightCmdLED` goes through `request_signal()`, which spins until any running
  ramp ends; with `t` up to 60 s a request can exceed `outer_cap_s` = 15 s, where legacy answered "LED
  is busy" (error 8) at once; `led_signal()`/`start_asy_ext_cmd_watcher` look dead
  (`buildgen/codegen.py:555`; `src/asy_neopixel_driver.py:104, 137-153`).
- **REST.S10** `lightCmdLED` out-of-range/missing keys yield per-field `"Failed"` while `PauseTime`
  yields `"Invalid"`; H.6 reserves Invalid for structurally wrong payloads (`asy_webserver_service.py:533-566`). ⟨pass 2, answered: out-of-range/missing values are content: per-field `"Invalid"` (OR69.a (4)) — G6: R41⟩
- **REST.S11** Comment drift: `asy_webserver_service.py:725` "see module docstring" (which says nothing
  about it); I.6 still says `max_connections` is 4 and 4 × 2048 = 8192 B (now 6 → 12288 B).
- **REST.S12** `_put_status` returns code 0 with no `result` map, silently ignoring unknown keys and
  any `ResetErrors` value other than `True`, unlike every other PUT's per-field verdicts (D.10)
  (`asy_webserver_service.py:631-639`).
- **REST.S13** `_put_sensors` drops unknown sensor names and non-dict sub-objects with no result entry;
  the comment cites the per-key "Invalid" convention but nothing is emitted, so a typo returns
  `{"res":"OK","result":{}}` (`:425-430`).

Quality measure: an adversarial-client test matrix (mock + twin) with the `MemoryError` gates active;
every seed resolved.

---

### 5.10 LED — Notification and LED

**Goal**: LED arbitration and threshold signalling are bounded, non-blocking, and legacy-faithful.
**References**: A.4 (split, sequencing, midnight-window decision), `DEVICE_REFERENCE.md`, legacy
`neopixel_signal.py`.

Topics:
- [ ] **LED.T01** (owns `REST.S09`/`LED.S01`) Signal arbitration (internal vs external), queued vs
      running semantics, busy behaviour, ramp timing, overlay.
- [ ] **LED.T02** Input sanitisation: `t`, colours, brightness, frequency — floors and ceilings.
- [ ] **LED.T03** `NotificationCoordinator` staged construction (`register`/`finalize`), buffered
      rejections, per-signal schema injection, check order and sleeps.
- [ ] **LED.T04** Failure isolation: can a bad source value kill `monitor_loop`?
- [ ] **LED.T05** Signal machinery lifecycle: `neopixel_signal` cancelled mid-ramp leaves the pixel lit
      and `start_signal_event` set, so the restarted task replays the old `rgbt`; `request_signal()`
      callers spin with no deadline whenever that task isn't running (`asy_neopixel_driver.py:145-153, 155-187`).
- [ ] **LED.T06** Notification inputs: freshness (old `TS` can still trigger, `XCUT.T17`), `None` vs 0,
      `>=`/`<=` at exactly the threshold, ordering and total duration with several signals in one
      window.
- [ ] **LED.T07** WS2812 contract: `bitstream` timing and IRQ-off window per `write()` during 20 Hz
      ramps, GRB ordering (`bpp=3`); datasheet `datasheets/ws2812/WS2812.pdf`. Hardware (owner, 2026-09-25): a single-pixel
      Adafruit RGB NeoPixel (not RGBW) on a round PCB, driven by MicroPython's built-in `neopixel` driver, supplied from USB 5 V,
      behind a level shifter — "the voltage levels are all settled". The 3.3 V-vs-VIH question is closed; the exact WS2812/WS2812B
      revision is low priority ("don't worry about the neopixel so much").

Seeds:
- **LED.S01** `request_signal()` and `_led_ext_signal_starter` busy-wait with `sleep(0)` for the whole
  length of a running signal; the driver's `t` has a floor but no ceiling (REST caps it at 60 s,
  `buildgen/codegen.py:542`); `neopixel_freq=0` raises `ZeroDivisionError` in `__init__`
  (`src/asy_neopixel_driver.py:68, 84-85, 148-149, 162-169`).
- **LED.S02** `float(value)` sits outside the `try` in `_check_one`; a non-numeric field would end
  `monitor_loop` (`src/asy_notification_service.py:218`).
- **LED.S03** An extra `2×FlashDur` sleep follows the *last* warning too (legacy slept only between);
  minor parity delta (`asy_notification_service.py:369-374`).
- **LED.S04** `DEVICE_REFERENCE.md` describes the WiFi LED as a static preference, but the code still
  toggles/flashes it with connection state, as legacy did (`DEVICE_REFERENCE.md:11` vs
  `asy_wifi_service.py:344, 527-536, 594`; doc half owned by `DOC.T11`).

Quality measure: every seed resolved; busy/queue semantics written down and tested.

---

### 5.11 GEN — Build generator and device definitions

**Goal**: `buildgen` fails loudly (only `BuildError`) on every malformed input, never emits code it has
not validated, and generates what Part L says for all 6 devices.
**References**: Parts L (all), K.3-K.8, C.14, H.5.1; `tests_scripts/test_buildgen_*.py`.

Topics:
- [ ] **GEN.T01** L.5 contract fuzz: every table/field of the TOML with wrong types/shapes → only
      `BuildError`, never a raw exception.
- [ ] **GEN.T02** Every TOML value that reaches generated source via `str()`/`repr()` is type-checked;
      the generated module is `ast.parse`/`compile`d before being returned.
- [ ] **GEN.T03** Tag grammars (`@wiring`, `@value-wiring`, `@limits`, `@requires`, `@web`,
      `@web-group`): scope detection, near-miss detection, NaN/inf, false positives on prose.
- [ ] **GEN.T04** Multi-instance correctness (`name_ext`): no generated reference to a bare
      driver-named global; definitions and codegen agree.
- [ ] **GEN.T05** (staging side: `SCR.T03`) Frozen-module set: `CORE_MODULES` vs codegen's imports,
      `TYPE_CHECKING` handling, `else:` branches, generated module included.
- [ ] **GEN.T06** Hand-maintained catalogs vs "one new file" (L.1 criterion 2): `buildspec.py`,
      `_SENSOR_DRIVERS`, `_ERRCOUNT_CATALOG`, `_CFGMGR_LABEL`, `twin_wiring.FIXED_ADDRESSES`, the twin
      CI suite's `_DRIVER_ERRCOUNT_NAME`/`_BUS_FAULT_OPS`, hand-mirrored constants (`_NTP_CHECK_TICK_S`,
      `_SERVER_OUTER_CAP_S`, `_WARN_SIGNAL_WEB_CATALOG`) — which are cross-tested, which silently drift
      (buildspec itself is SETTLED as hand-maintained). ⟨pass 2, answered: buildspec and status/errcount catalog hand-kept (owner 2026-09-18/24, OR68.a (2)); L.1 names the one row edit; the rest derived or pinned (harmonization 31) — G8: R12⟩
- [ ] **GEN.T07** `pico_gpio.py` legality table vs RP2040 silicon. Checked 2026-09-26 against the RP2040
      datasheet's Table 279 (p.237-238): the table follows the Pico W pinout figure and is stricter than
      silicon — it rejects legal wirings: GP22 (I2C1 SDA, SPI0 SCK), GP28 (I2C0 SDA, SPI1 RX, UART0 TX),
      GP20/21 (SPI0 RX/CSn, UART1 TX/RX), GP26/27 (SPI1 SCK/TX); its comments "GP22/GP28 have no I2C
      function" and "GP20-22/GP26-28 have no SPI function" are wrong for the chip. Never accepts an
      illegal pin; a future device on e.g. SPI1 at GP26-28 would fail the build with a misleading error.
      Owner 2026-09-26 (OR53): (a) — the table follows the chip's function table; comments corrected. ⟨pass 2, answered: OR53 (1): the table follows RP2040 Table 279; comments corrected — G8: HR052 (G3)⟩
- [ ] **GEN.T08** `devices/*.toml`: values vs legacy pinning per unit, `SensorStation<Name>` rule,
      shared hotspot password (accepted-risk rule: not to be "fixed" without the owner's direction),
      `timeout`/`frequency` vs `@requires`.
- [ ] **GEN.T09** (root cause shared with `WEB.S13`) `definitions.py`: ordering vs codegen, string
      `specialValues`, UTF-8 byte bounds, NaN/inf defaults, `defaultValue` kind check, display identity
      (file stem vs `SensorStation`).
- [ ] **GEN.T10** Static/compile coverage of generated artefacts: `build/generated_src/*.py` is outside
      ruff scope and mypy reports nothing there (`follow_imports = "silent"`); fixture outputs are only
      `ast.parse`d, never compiled by MicroPython nor run (`GEN.S01`'s class). Decide ruff + mypy over
      generated output and an `mpy-cross`/Unix-port compile of every fixture's output (with `TEST.T09`). ⟨pass 2, answered: OR22.a (2): same bar as `src/` — ruff+mypy over generated output, fixtures compiled and executed — G8: R03⟩
- [ ] **GEN.T11** Determinism: same TOML + `src/` → byte-identical module/definitions/wiring plan
      (except `build_date`) across `PYTHONHASHSEED`s and host CPython 3.11-3.13 (with `SCR.T11`). ⟨pass 2, answered: 3.3: byte-reproducible outputs, build time only in `buildgen/version.py` (conservative, P11) — G8: R17, HR153⟩
- [ ] **GEN.T12** Error location (L.5): every `BuildError` names the right device/instance/field and
      file:line for tag errors — the fuzz asserts location, not only class (extends `GEN.T01`).
- [ ] **GEN.T13** `driver_registry.py`: `_OVERRIDES`, `SINGLETON_SERVICE_DRIVERS`, a module with zero
      or two `SensorReader` subclasses, a registered driver whose module is missing; line-by-line read
      of `limits.py`, `wiring.py`, `value_wiring.py`, `buildspec.py` (no topic reaches them otherwise).
- [ ] **GEN.T14** Boot entry and version stamping: `generate_boot_entry_source()`
      (`codegen.py:696-709`) runs in no automated tier; `version.py`'s hand-bumped constants vs their
      mirrors (hand-written definitions' `websiteVersion`, `/system`'s `build`); does 1.29 accept
      `const('<str>')` (`PLAT`)?
- [ ] **GEN.T15** Cross-tool contracts buildgen owns and which are cross-tested (extends `GEN.T06`):
      wiring-plan JSON → `digital_twin/machine.configure_wiring()` (no schema version); `SCHEMA_VERSION`
      ↔ js `SUPPORTED_SCHEMA_MAJOR`; `web_tag._MAX_DECIMALS` ↔ `validateFieldHints`;
      `validate._HOSTNAME_MAX_LEN` / `_WPA2_*` ↔ `asy_wifi_service._VAL_*`; `[lwip]` read by both
      `buildgen.model.lwip_macros` and `setup_toolchain.load_lwip_macros`;
      `tests_js/_live_twin_command.js:121` shelling out to buildgen.
- [ ] **GEN.T16** CLI entry points (`python -m buildgen.definitions`, `buildgen.generate`,
      `_generate_sensortask_modules.py`): exit codes, non-`BuildError` failures (OSError on write)
      ending as tracebacks, `build_website.sh:37` running buildgen under a bare `python3`.

Seeds:
- **GEN.S01** `_sgp_maintenance_status()` uses the bare global `sgp40` whenever any sgp40 instance
  exists; the `multi_instance.toml` fixture (`sgp40_a`/`sgp40_b`) generates `assert sgp40 is not None`
  with no such global — a runtime `NameError` swallowed by `_write_guarded`, invisible to the smoke test
  (`buildgen/codegen.py:563-567`; `definitions.py:430`).
- **GEN.S02** `irq_pull_up` is never validated and is emitted with `str()`; `"no way"` produced invalid
  generated source that was returned without complaint — a crafted value injects code
  (`codegen.py:194-195`; `validate.py:386`).
- **GEN.S03** A TOML with no `[bus]` table crashes with a raw `KeyError`, though `validate.py:280-282`
  declares that shape legal (`codegen.py:382, 489`).
- **GEN.S04** A non-table `wiring` (device or instance level) raises a raw `AttributeError`
  (`validate.py:645, 693-694`; `graph.py:26-27, 41, 50`; `codegen.py:111`; `model.py:116-121`).
- **GEN.S05** Stray `warn_*` keys are accepted on any instance and add dependency edges, but only the
  notification instance's reach codegen (`validate.py:646, 669-672`; `graph.py:50-52`).
- **GEN.S06** `{source, field}` value-wiring never checks `field` exists on the source's data, though
  L.6.3 says the build checks it (`validate.py:579-591`).
- **GEN.S07** (stripper file owned by `SCR.T03`/`SCR.T10`) The generated module's own `TYPE_CHECKING`
  block is frozen unstripped; the comment at `scripts/build_firmware.py:95-99` says there is nothing to
  strip (`codegen.py:336-343`).
- **GEN.S08** The `definitions.py` CLI path (used by `build_website.sh`) never builds
  `construction_order`, so sensor ordering can differ from codegen's (`definitions.py:522-524`).
- **GEN.S09** Codegen hardcodes `fram=` for device-level consumers and `conn.set_ext_led` instead of
  each tag's `target`; an instance-level setter-mode tag would validate and be silently dropped
  (`codegen.py:112, 429`).
- **GEN.S10** Fragility: `tag_comments.py:200` treats a column-0 comment inside a function body as
  module level; `requires_tag._coerce` (`requires_tag.py:40-44`) and `web_tag._coerce_default_value`
  accept `nan`/`inf` (the latter would emit JSON `NaN` and break the inlined page,
  `web_tag.py:123-134`); `defaults.default_init_params` ignores keyword-only args (`defaults.py:41`);
  `schema_ast._eval_literal` can recurse unboundedly (`schema_ast.py:26-28`); `twin_wiring.py:59` and
  `definitions._coerce_special_value` (`definitions.py:139-144`) raise raw `ValueError`.
- **GEN.S11** `frozen_modules.py:41` skips a whole `If` including its `orelse`; `:57` has no
  `SyntaxError → BuildError`; `CORE_MODULES` is a hand mirror of codegen's imports with no test.
- **GEN.S12** (file owned by `SCR.T03`) `scripts/_strip_type_checking.py:59-63` removes the `try: from typing import TYPE_CHECKING`
  guard unconditionally but keeps `if TYPE_CHECKING: … else:` and compound tests (not present in `src/`
  today).
- **GEN.S13** Dead generated global: `timers_running = ThreadSafeFlag()` is created in every generated
  module and never used (`codegen.py:367, 438`).
- **GEN.S14** Stale comments: `tag_comments.py:121-129, 142-143` ("`@web` planned"),
  `requires_tag.py:2, 59` (`_VAL_*`), `web_tag.py:21` ("see module docstring").
- **GEN.S15** The comment at `tag_comments.py:142-143` sits above `_PAYLOAD_SNAKE_RE`/`_CAMEL_RE` but
  seems to describe `_LEADING_WORD_RE` at `:149` (misplaced).
- **GEN.S16** `codegen.py:376-377` writes "mirrors … every hand-written sensortask_*.py" into every
  generated docstring; no hand-written module exists since L.2.
- **GEN.S17** Errors in generated modules are never reported: `pyproject.toml:359, 365` (silent
  follow-imports with `build/generated_src` on `mypy_path`) plus `scripts/lint.sh:13` (ruff scope). ⟨pass 2, dup: same evidence as GEN.T10 — G8: R03⟩
- **GEN.S18** buildgen type-checks but never range-checks the TOML ints that become timing values: `hotspot_time_min` (`validate.py:65, 106-108`) and the UART `poll_wait_ms`/`poll_idle_ms` (`:62, 304-306`; only the J.6 floor applies, `:258-276`). `hotspot_time_min` becomes `Timer(period=60000*min)` (`asy_wifi_service.py:165, 413-417`): 0 is clamped to a 1 µs PERIODIC timer (`ports/rp2/machine_timer.c:99-103`), flooding the soft-callback queue; a negative value is cast to `uint64_t` and never fires; ≥ 35,792 raises `OverflowError`, which the `except (OSError, MemoryError)` at `:419` does not catch (`XCUT.T25`).

Quality measure: fuzz harness result (only `BuildError`); generated output compiles for fixtures;
every seed resolved.

---

### 5.12 TOOL — Toolchain installer and build overrides

**Goal**: the installer and overrides are correct, idempotent, safe for the host, reproducible, and
fail loudly.
**References**: Parts B.1-B.14, CLAUDE.md "Build-environment verification", dead-man's-switch rule.

Topics:
- [ ] **TOOL.T01** Every subprocess (~50 `run()` calls): argument quoting, secrets in argv/logs, `sudo`
      environment (proxy/CA variables dropped by `env_reset`?), error propagation.
- [ ] **TOOL.T02** Downloads: pinning, checksum/signature verification, version floating (Node,
      picotool tag selection, MicroPython tag vs SHA), `git fetch --tags --force`.
- [ ] **TOOL.T03** Bench tier: bridge creation/modification with no in-code dead-man's switch, MAC
      pinning, `br_netfilter` persistence, temp files, idempotency, `--skip-apt` interactions.
- [ ] **TOOL.T04** Overrides framework: anchor checks, generated board/variant dirs, lwIP ensemble
      checks vs `lib/lwip` `init.c`/`opt.h`, post-build verification, path quoting.
- [ ] **TOOL.T05** Two Unix-port variants: detection, rebuild on mismatch, cache interactions (stale
      binaries: owned by `TOOL.T07`, with `CI.S01`, `SCR.S05`).
- [ ] **TOOL.T06** B.14.3 (`littlefs_flash_storage_size`, documented not implemented) — relevance to a
      1.26 → 1.29 reflash (seed `PAR.S10`). ⟨pass 2, answered: D04, OR72.a (7): littlefs resize dropped until flash space is short; B.14.3 goes — G8: R20⟩
- [ ] **TOOL.T07** Toolchain provenance and staleness: nothing records which ref/overrides/flags a
      toolchain dir was built from; `--micropython-ref` silently builds a non-pinned ref; test.sh and
      the twin/web runners check only binary existence (test.sh also the variant), so a moved ref or
      changed override is never rebuilt locally — the local twin of `CI.S01` (owns `SCR.S05`).
- [ ] **TOOL.T08** Concurrency/atomicity: two `setup` runs on one toolchain dir; interrupted
      clone/fetch/build after an rmtree; `build_firmware.py` wiping shared `mpy-cross/build` and
      `ports/rp2/build-<board>` during concurrent device builds — lock or documented single-writer rule?
- [ ] **TOOL.T09** Host-wide side effects and least privilege: picotool `sudo make install` into
      `/usr/local` on every `setup` (incl. test.sh's auto-build), apt packages, dialout group,
      `/etc/modules-load.d` + `/etc/sysctl.d` files, NetworkManager profiles, `setcap` — which tier
      needs which, and can each be undone? (with `SCR.T07`, `SEC.T06`).
- [ ] **TOOL.T10** Subprocess robustness: no timeouts on git/apt/make/curl; `run()` buffers output
      until exit; failure detection by grepping English `error:`/`warning:` (false +/- classes);
      `check=False` sites.
- [ ] **TOOL.T11** Post-build proof symmetry: lwIP has a sentinel + preprocessor readback,
      `unix_kbd_intr` only a source anchor; the 8-step chain doesn't prove the project's
      overrides/frozen modules landed.
- [ ] **TOOL.T12** Paths that move the pin: `--latest` + `write_micropython_ref()`'s regex and tag
      parsing (nothing prompts CLAUDE.md's mandatory re-check); the distro ARM GCC is unpinned
      (warnings-as-errors, reproducibility).
- [ ] **TOOL.T13** `env` tiers end to end (B.12): `run_env` always runs a full `setup`; Node
      `latest-v22.x` and an aarch64/x86_64-only arch map; non-fatal Playwright failure still reported
      "ready"; idempotent re-runs on the Pi4.

Seeds:
- **TOOL.S01** The bench AP password is echoed in the full argv by `run()` and printed again, and sits
  on the process command line (`toolchain/setup_toolchain.py:111, 916-921, 924`).
- **TOOL.S02** `ensure_node` uses `next(...)` without a default (raw `StopIteration` if SHASUMS changes
  between two fetches); checksum from the same origin, no signature; version floats within v22
  (`setup_toolchain.py:998-1003`).
- **TOOL.S03** `ensure_bench_bridge()`'s creation path enslaves `eth0` (`nmcli connection up br0-eth0`)
  with no dead-man's switch armed — the exact operation behind the 2026-09-04 lockout; B.13's manual
  recovery script hardcodes the profile name "Wired connection 1" (unverified on trixie)
  (`setup_toolchain.py:896-925`; SPECIFICATION.md:1051-1052).
- **TOOL.S04** `ensure_apt_packages` uses `sudo env DEBIAN_FRONTEND=…`, which likely drops proxy
  variables; `ensure_dialout_group` is skipped by `--skip-apt`; `ensure_br_netfilter` passes no `env=`
  and leaks its temp file if `sudo` fails (`setup_toolchain.py:169-172, 689, 815-840`).
- **TOOL.S05** `build_firmware.py` does not `.resolve()` `--toolchain-dir`; generated make/CMake
  `include` paths are unquoted, so relative paths or paths with spaces would break
  (`scripts/build_firmware.py:115-120`; `toolchain/micropython_overrides.py:78-83, 332-336`).
- **TOOL.S06** `--micropython-ref` builds a ref recorded nowhere while `typecheck.sh` still derives its
  stubs from the pin (`setup_toolchain.py:554-560, 1108, 1132`).
- **TOOL.S07** `unix_kbd_intr` is verified only by its anchor (`micropython_overrides.py:43-84`);
  unlike lwIP (`:448-466`) nothing proves `MICROPY_ASYNC_KBD_INTR == 0` in the built binary.
- **TOOL.S08** `run()` has no timeout and prints only after the command exits (`setup_toolchain.py:110-118`);
  `setup` always does `sudo make install` of picotool (`:258, 276`), so test.sh's auto-build needs root.
- **TOOL.S09** `write_micropython_ref()` rewrites the first `ref = "…"` line by regex and silently does
  nothing if there is no match (`setup_toolchain.py:154-157`); `--latest` moves the pin without
  prompting the PLAT re-check (`:555-558`).

Quality measure: every subprocess call reviewed; the two chroot legs' owed-list in BACKLOG kept current.

---

### 5.13 SCR — Scripts and test orchestration

**Goal**: the orchestration scripts are the gates everything else trusts; they must fail closed,
never report green on a run that did less than it claims, and be safe to run on a dev box.
**References**: CLAUDE.md "Code quality tooling", Parts E.1-E.5, B.10-B.11, L.5.

Topics:
- [ ] **SCR.T01** (zero-test/footer-less vacuity owned by `TEST.T12`; with `TEST.T01`) `test.sh`:
      argument/env validation, parallelism probe, per-file timeout/retry, `MemoryError` gate, exit codes
      0/1/3, annotation emission, backgrounded pytest tier, a file that runs zero tests, a file that
      `sys.exit(0)`s early.
- [ ] **SCR.T02** `lint.sh`/`typecheck.sh`: scope lists vs CLAUDE.md's eight directories; the
      `method-assign` and `gc.collect()` grep guards; stub repair conditions.
- [ ] **SCR.T03** `build_firmware.py`, `build_website.sh`, `build_frozen_html.sh`,
      `_strip_type_checking.py`, `_generate_sensortask_modules.py`: correctness, determinism (`gzip -n`),
      fail-loud, shared outputs.
- [ ] **SCR.T04** (the twin's gate — with `TWIN`) Twin CI suite and runners: fixed ports (18080, 53),
      run list, gates, log handling; Unix-port variant probe present only in `test.sh` (owned by
      `TOOL.T07`).
- [ ] **SCR.T05** Hardware runners and `_require_clean_hardware_run.sh`: flag parsing, `-m` last-wins,
      skip whitelist, messages.
- [ ] **SCR.T06** Concurrency safety of local runs: shared mutable outputs (`frozen_modules/`,
      `build/generated_src/`, twin state files, `tests/_tmp`, rp2/mpy-cross build dirs).
- [ ] **SCR.T07** `setcap cap_net_bind_service` on a general-purpose interpreter binary (three scripts)
      — host-security side effect.
- [ ] **SCR.T08** Shell quality beyond shellcheck, per script: `set` flags (note
      `_require_clean_hardware_run.sh` deliberately omits `-e`), traps, `mktemp` cleanup, unquoted loops
      (`SCR.S08`).
- [ ] **SCR.T09** Which interpreter runs what: bare `python3` (`build_website.sh:37`,
      `typecheck.sh:17`, `ci.yml:625`), `uv run`, the venv; host CPython unpinned (no `.python-version`)
      changes `ast.unparse` output (what ships), `tomllib`, `datetime.UTC`; `__pycache__` written into
      the tree.
- [ ] **SCR.T10** What ships vs what is tested: the firmware freezes `ast.unparse`d stripped copies
      plus the generated `main.py`; no tier executes either — ship-vs-test differential (with
      `GEN.T14`).
- [ ] **SCR.T11** Reproducibility end to end (owner decides whether it is a goal): gzip mtime
      (`SCR.S04`), `build_date`, host-dependent `ast.unparse`, freezefs walk order (any fix outside
      vendored `ext/freezefs/`), MicroPython's embedded version/date, distro GCC. ⟨pass 2, answered: 3.3 made reproducibility a goal: `gzip -n`, build time only in `version.py`; host `ast.unparse` in gap G3 — G8: R17, HR153⟩
- [ ] **SCR.T12** Stale/partial generated outputs: `build/generated_src/` never pruned (first on every
      `MICROPYPATH`), `frozen_modules/frozen_html.py` holds whichever device was built last, non-atomic
      writes while other processes read.
- [ ] **SCR.T13** Local-vs-CI gate parity matrix: npm tier not in lint.sh/test.sh, real firmware build
      behind `RUN_SLOW_FIRMWARE_BUILD`, CI's narrowed mypy scope (`CI.S03`) — DoD 1.2 depends on it.
- [ ] **SCR.T14** Script input validation and destructive side effects: unvalidated device names in
      paths, `--device` without a value under `set -u`, unvalidated numeric env knobs, tree mutation
      (`rm -f devices/zz_test_*.toml`, `rm -rf tests/_tmp`, the twin's `_clean_state()`, `/config_*.cfg`
      spilled into the repo root).
- [ ] **SCR.T15** The three hand-synced mypy configs: drift in strict flags, exclude lists vs real
      files, `tests_scripts/conftest.py` excluded, `typecheck.sh` needing network every run (`uv pip install --target typings`).

Seeds:
- **SCR.S01** `_require_clean_hardware_run.sh:106` prints a truncated sentence ("…flags) to."); the
  `--soak-tier=x` form is not recognised (`:20-23`); a caller's `-m` replaces the runner's soak
  exclusion (pytest `-m` is last-wins).
- **SCR.S02** No zero-tests-ran guard: `microtest` prints `0/0 passed` and exits 0, which `test.sh`
  records as PASS (`scripts/test.sh:373-376`).
- **SCR.S03** Stale comment `test.sh:296` (pytest "right after the toolchain check"); B.10.1 says "180
  s × 3" (SPECIFICATION.md:911) where the default is 240 (`test.sh:314`).
- **SCR.S04** `build_frozen_html.sh:25` runs `gzip -9` without `-n` (mtime embedded → non-deterministic
  firmware images).
- **SCR.S05** The Unix-port variant probe exists only in `test.sh`; `run_digital_twin_ci.sh`,
  `run_unix_port_integration.sh` and `cross_browser_smoke.mjs` only check `-x`.
- **SCR.S06** `setcap cap_net_bind_service` is applied to the Unix-port interpreter (`test.sh:284-288`
  and two other scripts), letting any local user bind privileged ports with it.
- **SCR.S07** `_generate_sensortask_modules.py` never deletes stale
  `sensortask_*.py`/`*_wiring_plan.json` (first on every `MICROPYPATH`) and writes with plain
  `write_text()` while typecheck.sh, test.sh, npm pretest and the twin runners regenerate or read it
  (`scripts/_generate_sensortask_modules.py:28-51`).
- **SCR.S08** `build_frozen_html.sh:22` iterates `for src_dir in $src_dirs` unquoted.
- **SCR.S09** `tests_js/_live_twin_command.js:154, 231` (`rmSync(digital_twin/config)`) and
  `_digital_twin_ci_suite.py:238-250` (`_clean_state`) wipe the same repo-level twin state; device
  scripts spill `config_*.cfg` (WiFi SSID/password) into the repo root (`.gitignore:84-89`).
- **SCR.S10** The shipped form is untested: stripped copies and the generated `main.py` are staged
  (`build_firmware.py:52-56, 92-93, 98-99`) and executed by no tier; the twin copies the boot entry's
  `gc.threshold(32768)` by hand (`tests/test_digital_twin_run_generic_integration.py:105-108`).
- **SCR.S11** The hand-curated `_heavy_files_priority` list silently drops renamed/split files
  (`test.sh:399-415`).

Quality measure: each gate script has a test proving it fails on each failure class it claims to
catch (many already exist in `tests_scripts/` — audit their bite).

---

### 5.14 CI — CI, dependency pins and supply chain

**Goal**: CI runs what the docs say, on the paths that can break it, reproducibly, with least
privilege, and a third party's outage never reads as a red test (CLAUDE.md).
**References**: `.github/workflows/ci.yml`, composite action, `zizmor.yml`, Parts B.10, H.8.

Topics:
- [ ] **CI.T01** Job graph: `needs`/`if` edges vs CLAUDE.md's sequencing-not-gating rule; timeouts;
      matrices; `continue-on-error` semantics; concurrency groups.
- [ ] **CI.T02** Path filters: the web tier's filter vs every input of the website build and the live
      twin tests.
- [ ] **CI.T03** Caching: keys vs every input that feeds compiled binaries; save-on-failure behaviour;
      misleading downstream errors on a cold cache.
- [ ] **CI.T04** Pins: uv itself, `uv sync --locked/--frozen`, `pytest`/`mpremote` unpinned vs the
      "every tool pinned" comment, stub post-release floating, `coverage` in a PEP 723 script,
      `@types/node` vs `.nvmrc`, sdist-only `actionlint-py` fetching a binary, micromamba/Firefox
      unpinned, hardcoded `amd64`.
- [ ] **CI.T05** mypy scope in CI vs `typecheck.sh` defaults vs B.15.
- [ ] **CI.T06** Permissions, credentials persistence, SHA vs tag pinning policy, no Dependabot (manual
      SHA bumps).
- [ ] **CI.T07** Hardcoded 6-device matrices vs L.1 criterion 2 (a new device = one new file).
- [ ] **CI.T08** Config-file comment cap: which config files are in the swept set (PQ6). ⟨pass 2, answered: PQ6/OR51: the comment rule applies to every file, config files included — G8: HR077 (G10)⟩
- [ ] **CI.T09** Trigger × concurrency × path filter: `cancel-in-progress` (`ci.yml:13-15`) with the
      per-push filter base (`:38-41`) — a cancelled run's web change never re-filtered; first push of a
      branch, force-pushes, push/PR dedupe.
- [ ] **CI.T10** Runner image and toolchain drift: `ubuntu-latest` floats (GCC 13 today, so CI never
      exercises the GCC-14 mbedtls path); cache keys include only `runner.os`; no scheduled run to catch
      upstream drift or 7-day cache eviction.
- [ ] **CI.T11** Gate vs advisory: `web-coverage`'s test step is `continue-on-error` (`ci.yml:226-228`)
      while E.5.3 made the Python coverage job's test result gating; which checks branch protection
      requires.
- [ ] **CI.T12** Copy-paste drift inside the workflow: retried `uv sync` in the composite action and
      again in several jobs; four copies each of the Playwright install and Unix-port build steps — any
      dedupe must keep CLAUDE.md's retried sync ahead of `test.sh` in `unit-tests`.
- [ ] **CI.T13** Test-runner config hardening: pytest without
      `--strict-markers`/`xfail_strict`/`filterwarnings`; Vitest preferring a sandbox Chromium over the lock-pinned build.
- [ ] **CI.T14** Dependency hygiene beyond pins: vulnerability scan of both lockfiles, npm lifecycle
      scripts run by `npm ci`, `curl | gpg` key fetches without fingerprint check, licence scan of dev
      dependencies (with `LIC`).
- [ ] **CI.T15** Artefact and log hygiene: can uploaded logs, coverage HTML or test.sh's annotations
      (`test.sh:508-538`) carry the hotspot password or `config_WIFI.cfg` contents? Retention.

Seeds:
- **CI.S01** The toolchain cache key hashes `versions.toml` and `setup_toolchain.py` but not
  `toolchain/micropython_overrides.py`, whose `unix_kbd_intr` override is compiled into the cached
  binary (`.github/actions/setup-micropython-toolchain/action.yml:38`).
- **CI.S02** `[x2]` The `web-changes` filter omits `src/**`, `buildgen/**`, `devices/**`,
  `digital_twin/**`, `toolchain/**`, yet the live-backend twin tests and generated definitions depend on
  them (`ci.yml:42-58`).
- **CI.S03** `lint-and-typecheck` narrows the main mypy pass to `src tests tests_hardware/device_scripts`
  (`ci.yml:339`), while `typecheck.sh:105-107`'s comment says CI passes `src tests`.
- **CI.S04** `pip install uv` is unpinned in every lane, and `uv sync` runs without `--locked`, so a
  drifted lock re-resolves silently (`ci.yml:323`; `action.yml:18`).
- **CI.S05** `[x2]` `pytest` and `mpremote` are unpinned in `pyproject.toml` despite its "PINNED like
  every tool" comment (`pyproject.toml:18-24`); the hardware harness depends on mpremote's exact
  raw-REPL/soft-reset behaviour.
- **CI.S06** (file owned by `SCR`) `setup_cross_browser_toolchain.sh:50` fetches micromamba `latest`
  with no checksum; Firefox/geckodriver unpinned (`:53`); `arch=amd64` hardcoded (`:30`); the Firefox
  cache key is a fixed string (`ci.yml:301-305`).
- **CI.S07** `package.json` pins `@types/node ^26` while `.nvmrc` pins Node 22 (`package.json:25`;
  `.nvmrc:1`).
- **CI.S08** The composite action's description lists six callers; there are nine. `pyproject.toml:233`
  says "three known credential sites", but S105/S106 are exempted in more files.
- **CI.S09** `actions/cache` saves only on job success: a cold-cache `unit-tests` failure makes
  `firmware-build-verify` (`!cancelled()`) fail with "no toolchain found" — documented as intended at
  `ci.yml:617-618`; question is only whether the message is acceptable. ⟨pass 2, answered: a cold cache fails loudly ("no toolchain found") by design, adopted in R51 (OR16 fail-loud) — G8: R51⟩
- **CI.S10** Comment blocks over 3 lines in files outside CLAUDE.md's swept config list: `.gitignore`
  (from lines 27, 33, 75, 84), `tsconfig.json` (11, 29), `tsconfig.node.json` (2, 17); `.gitignore:75`
  still names the retired `run_wozi_integration.py`.
- **CI.S11** `ci.yml:13-15` + `:38-41` together may skip the web tier permanently for a change whose
  run was cancelled (confirm dorny/paths-filter's push semantics first).
- **CI.S12** The web-coverage run's test result is advisory (`ci.yml:226-228`). ⟨pass 2, dup: same as CI.T11 — G8: R55⟩
- **CI.S13** No `--strict-markers` (`pyproject.toml:415-418`; markers registered at
  `tests_hardware/conftest.py:105-112`): a misspelled `persistence_write` would be a silent no-op and
  the write would run ungated.
- **CI.S14** The toolchain cache key carries no image, glibc or compiler identity (`action.yml:38`).
- **CI.S15** `vitest.config.js:18-19` uses `/opt/pw-browsers/chromium` when it exists.
- **CI.S16** `npm run preview` serves the repo root on all interfaces (`package.json:21`), which can
  include local `config_*.cfg` with real credentials and `.git/`.
- **CI.S17** `uv sync` is retried in `action.yml:22-30` and again at `ci.yml:440-447, 494-501` in the
  same jobs (CLAUDE.md protects the `unit-tests` retry — don't "simplify" it away).
- **CI.S18** (file owned by `SCR`) `setup_cross_browser_toolchain.sh:29` imports Microsoft's apt key
  via `curl | gpg` without a fingerprint check.
- **CI.S19** More stale `.gitignore` text: `:6` ".venv/ above" (it's at `:59`), `:38` pin v1.28.0,
  `:40` old `MICROPYPATH`.

Quality measure: every job's actual behaviour matches B.10/B.10.1; every pin decision recorded.

---

### 5.15 WEB — Website

**Goal**: the UI is correct, robust against a slow/failing device, mirrors `src/` validation exactly
(Part G.2 mirror obligation), is accessible, and its build is deterministic and fail-loud.
**References**: Parts H (all), A.9, G.2, L.4 (definitions generation).

Topics:
- [ ] **WEB.T01** Apply/PUT semantics: sparse bodies, dispatch toggles, baselines, result
      reconciliation and colouring, repeated Applies.
- [ ] **WEB.T02** Input parsing: whitespace, hex/exponent, locale decimal comma, empty vs zero, byte vs
      character length for strings.
- [ ] **WEB.T03** Request lifecycle: timeouts (headers vs body), single-flight queue, section switch
      cancellation, hidden-tab polling, client/server timeout race.
- [ ] **WEB.T04** `js/mock-server.js` ↔ `src/` parity (G.2): every validation rule, envelope, unknown
      key, malformed body, Content-Type gate, failure injections that model fixed server gaps.
- [ ] **WEB.T05** Definitions: hand-written wozi/dev vs generated (order-sensitive),
      `validateDefinitions` strictness vs H.4's claim, degraded `/status` sources. ⟨pass 2, overtaken: hand-vs-generated premise gone: files retired (OR43.a (3)); validator strictness and degraded sources continue in R38 — G7: R38, HR169⟩
- [ ] **WEB.T06** Build: bundle order, import stripping, duplicate exports, inlining/escaping, the
      staging test's bite.
- [ ] **WEB.T07** Accessibility: ids, labels, drawer focus/inert, contrast (light and dark),
      colour-only information, password inputs, `color-scheme`, reduced motion.
- [ ] **WEB.T08** Security: no-`innerHTML` rule enforcement, selector injection, CSRF/DNS
      rebinding/clickjacking posture (PQ5), password `autocomplete`.
- [ ] **WEB.T09** First define the browser floor (owner input, PQ10), then check it vs features used
      (media-range syntax, `replaceChildren`, private fields, `??=`). ⟨pass 2, answered: floor = current Chromium, Firefox, Safari, desktop and mobile (PQ10, owner 2026-09-26) — G7: R32⟩
- [ ] **WEB.T10** (owned by `TEST.T10`) Test coverage: live PUT matrix per device (dev/ISL29125), live
      tests that skip-and-pass without the toolchain, runtime DOM validation. ⟨pass 2, dup: TEST.T10 owns it — G7: —⟩
- [ ] **WEB.T11** H.3 layering contract vs code: the `data-*`/class contract, no DOM building in
      `render.js`/`nav.js`, no I/O in `templates.js`, controllers set only `data-apply-status`.
- [ ] **WEB.T12** Per-device end-to-end rendering: the 4 generated devices' definitions never pass the
      real `validateDefinitions()`/renderer in any tier; live tests, PUT matrix and cross-browser smoke
      run wozi only; `app.js` knows wozi/dev only; no mockdata for the others.
- [ ] **WEB.T13** How the frozen site is served (with `REST.T07`): encoding/type headers, caching
      (stale bundle after reflash), `/` → index, 404s, security headers such as CSP (PQ5).
- [ ] **WEB.T14** Captive-portal assistants (iOS CNA, Android WebView) as clients in hotspot mode.
- [ ] **WEB.T15** Mock-fixture fidelity: `mockdata/*.json` vs real twin GET bodies; the mock's random
      latency/jitter makes tests non-deterministic.
- [ ] **WEB.T16** Frozen-site footprint: per-device gzip sizes vs the flash budget (B.14.3) and
      requests per page load vs `max_connections` (with `PERF.T02`).

Seeds:
- **WEB.S01** After Apply a settings card is not rebuilt, so a dispatch toggle (`SGPResetVOC`,
  `ISLCalibrate`) stays On and its baseline moves to true; the next Apply on that card resends it and
  resets the VOC algorithm/backup again (`js/render.js:81, 252, 321-335`).
- **WEB.S02** Dispatch toggles in the Off position are always sent, so an Apply can never report
  "Nothing to submit" (`render.js:81`).
- **WEB.S03** A whitespace-only number field submits 0 (`Number(" ") === 0`); hex and `1e3` pass
  client-side; a decimal comma is sent as a string (`render.js:23-30, 101-102`).
- **WEB.S04** Per-field status colours go stale: fields not in the latest result keep the previous
  Apply's colour (`render.js:164-169`).
- **WEB.S05** `fetchWithTimeout` clears its timer once headers arrive; `response.text()` is unbounded,
  so a mid-body stall blocks the global single-flight queue for every section
  (`js/poll-manager.js:32-34, 63`).
- **WEB.S06** Client 15000 ms starts before connect, server `outer_cap_s` 15.0 at accept, so the client
  nearly always aborts first — undercutting H.4's stated rationale (`js/poll-manager.js:8`).
- **WEB.S07** Section switches never abort in-flight or queued requests; polling continues in hidden
  tabs on a server that saturates around ~2.2 requests/s (`poll-manager.js:126-131`).
- **WEB.S08** The errcount group is rebuilt every tick, losing keyboard focus; its rollup (history
  type) and row colour (`counter > 0`) can disagree (`render.js:296-312`; `js/templates.js:243-249` vs
  `:283`).
- **WEB.S09** A degraded `/status` source (`{"error":"unavailable"}`) renders as "—" with no signal.
- **WEB.S10** Latent: in-place caption refresh bypasses `resolveFieldValue` (`render.js:327, 331`); the
  baseline snapshot is frozen at first render (`:336`); an Apply with no `rest.put` silently does
  nothing and `validateDefinitions` doesn't require it (`:197-199`).
- **WEB.S11** `console.error("Poll failed:")`, cited by H.8 as the loop's only diagnostic, is dead:
  `fetchOnce` catches everything (`render.js:350-375`).
- **WEB.S12** Mock divergences: WiFi UTF-8 byte bounds not mirrored (`js/mock-server.js:59-61` counts
  UTF-16); unknown `/sensors` sub-key silently ignored vs the server's Invalid + errno 10, with a
  comment claiming parity (`:130-131`); `partial-result` injection models a server gap that is fixed
  (`render.js:133-135`, `mock-server.js:252-254`); malformed/non-object bodies behave differently
  (`:375, 383`); recursive jitter corrupts time structs and random-walks `BootSignature`/`NtpLastSync`
  (`:289-291`, stale comment `:481`).
- **WEB.S13** `[x3]` wozi/dev `html/definitions/*.json` are hand-written; the generator's output equals
  them only order-insensitively — field order differs (e.g. wozi SCD30), so generated devices show
  fields in a different order; the golden test is order-insensitive
  (`tests_scripts/test_buildgen_definitions.py:40-69`). ⟨pass 2, overtaken: hand-written wozi/dev definitions retired (OR43.a (3)); generated order is the only order — G7: R38, HR169⟩
- **WEB.S14** H.2 claims `build_website.sh` mechanically re-checks bundle order; no such check exists,
  and the order is violated (`templates.js` before `definitions.js`, `scripts/build_website.sh:78`),
  harmless only via hoisting; single-line `grep -v` import stripping; the staging test passes on a
  comment mention (`tests_scripts/test_build_website_sh.py:113-127`, stale comment `:26-29`).
- **WEB.S15** Duplicate DOM ids (`field-${key}` not namespaced by group: dev's
  `SampleInterv`/`FiltCoeff` twice); dangling `label htmlFor` targets (`templates.js:61, 71-78, 135-138`).
- **WEB.S16** Drawer not `inert` when closed, no focus management, static `aria-label`; colour-only
  errcount history; light-mode contrast below 4.5:1 (success 3.13, danger 3.74, warn 4.01; borders
  1.39); `input[type=password]` unstyled (`html/style.css:261-263`); no `color-scheme`.
- **WEB.S17** No ESLint rule enforces the no-`innerHTML` rule; selectors interpolate keys without
  `CSS.escape`; masked password inputs lack `autocomplete` (`templates.js:160`).
- **WEB.S18** Duplication/dead: `selectSection` and the startup banner duplicated in `js/app.js` and
  `js/main.js` (BACKLOG); `PollManager.isBusy` test-only; `"settings"`/`"none"` pollGroups identical;
  stale spec pointers (`templates.js:8, 340`; `render.js:127`); `validateDefinitions` shallow — an
  unknown kind renders as a text input (`templates.js:158`).
- **WEB.S19** `html/index.html:40-43` has a 4-line `//` block (comment cap).
- **WEB.S20** `/system`'s `build` entry is rendered nowhere: H.1 (SPECIFICATION.md:4277-4278, "every
  REST endpoint's functionality must be reachable in the GUI") contradicts L.7 (:6575-6576, "neither
  version nor build date is rendered") — doc contradiction owned by `DOC.T10`. ⟨pass 2, answered: `build` is rendered on the System page (OR43.a (2), V57); L.7 corrected — G7: R29⟩
- **WEB.S21** Stale pointers: `js/field-format.js:27`, `js/mock-server.js:179`,
  `tests_js/templates.test.js:41` cite `src/sensortask_wozi.py` (gone; helper at
  `buildgen/codegen.py:518`); `html/index.html:40-41` cites a removed "Inlining" comment;
  `tests_scripts/test_build_website_sh.py:26-29` a removed "Bundling" comment.
- **WEB.S22** `js/app.js:15-16` hardcodes `KNOWN_DEVICES = ["wozi","dev"]` (L.1 criterion 2; BACKLOG).
- **WEB.S23** `js/definitions.js:164-165` dereferences `g.key` before any null/object check (`groups: [null]`
  throws); duplicate section/group/field keys aren't detected (would have caught `WEB.S15`).

Quality measure: every seed resolved; mock ↔ src parity table; axe-style runtime check result.

---

### 5.16 TEST — Software test tiers

**Goal**: the suites prove what their names claim; failures are loud; no test is vacuous,
tautological, or propped up by `gc.collect()`; tier obligations (CLAUDE.md bus-hazard rule, E.6.6
parity) are met or recorded.
**References**: Parts E (all), K.6, C.11.1, C.12; CLAUDE.md hang/segfault/memory rules.

Topics:
- [ ] **TEST.T01** Vacuity sweep: tautologies, swallowed exceptions, negative-only assertions,
      early-return skips counted as PASS, overclaiming names.
- [ ] **TEST.T02** Mutation/clamp-removal sweeps: first every guard named in a seed, then one mutant
      per validation branch / clamp / early return per `src/` function (operators: invert condition,
      remove clamp, off-by-one bound, drop await); stop when a module's surviving-mutant rate is
      recorded and each survivor is triaged. Wear rule: each mutant runs only the test files covering
      the mutated function, on tmpfs/scratch; ENV estimates and records the total run count first. ⟨pass 2, overtaken: OR16.a (4)/OR19.a (3): a small targeted fault set per module and per test file, one campaign (harmonization 18), not one mutant per branch; record = which test catches which fault — G2: R12⟩
- [ ] **TEST.T03** `gc.collect()` and absolute heap bounds in tests/twin vs CLAUDE.md and E.8;
      root-cause any `MemoryError` a manual collect is hiding. ⟨pass 2, answered: OR39.a (1)/OR55.a: `gc.collect()` in tests only as a measurement baseline, readable in the next statement, never in a timed window; props root-caused; absolute bounds become rates — G2: HR115, HR124⟩
- [ ] **TEST.T04** Timing sensitivity: wall-clock bounds under parallelism, fixed sleeps, unbounded
      `asyncio.run()` helpers.
- [ ] **TEST.T05** (owns the mock↔twin divergences; `TWIN.T02`/`TWIN.T12` cite it) Mock ↔ twin semantic
      divergences (reset returns vs raises, WDT validation, `Pin.init` pull, IRQ edges, `scan()`, RTC
      set return). ⟨pass 2, answered: harmonization 32: fidelity may differ, semantics never; one shared contract per shared API; divergences closed — G2: R07, R06⟩
- [ ] **TEST.T06** Meta-tests: which CLAUDE.md rules are machine-enforced vs review-only; propose
      guards for review-only ones (four-tier bus-hazard rule, nested `asyncio.run`, port/scratch-key
      disjointness, `ALL_CHECKS` completeness, `gc.collect()` in tests/twin).
- [ ] **TEST.T07** Shared mutable class-level state across tests in one process + dict-order execution.
- [ ] **TEST.T08** Duplication of helpers (raise-on-arm context managers, `run()`, `_wait_until`).
- [ ] **TEST.T09** (with `GEN.T10`) Coverage: generated modules untraced; E.5.1's false-negative
      categories re-checked. ⟨pass 2, answered: OR22.a (2): generated modules traced like `src/`; report-only (OR23.a (2), E.5.3); Codecov gone (OR63.a) — G2: HR128, R13⟩
- [ ] **TEST.T10** (owns `WEB.T10`) `tests_js/`: live tests' skip behaviour, fixture reliance on
      hand-written definitions, mock-only coverage for dev fields. ⟨pass 2, answered: OR43.a (3)/OR54.a (1): generated definitions only, device set derived; OR21.a (3): a skip never passes — G2: R27, R19, HR169, HR019⟩
- [ ] **TEST.T11** Private-attribute coupling in tests: count SLF001-style accesses per `src/` module
      and decide whether the refactor-fragility cost is accepted. ⟨pass 2, answered: OR36.a (1): tests reach privates from outside (SLF001 exempt); the product adds no seam — G2: HR073, R05⟩
- [ ] **TEST.T12** Runner-level vacuity: an `async def test_*` counts as PASS without running; a file
      without the footer prints nothing and exits 0; a `BaseException` mid-file aborts the rest — a
      meta-test for all three.
- [ ] **TEST.T13** `tests_scripts/` quality: tests touching the real tree (`devices/zz_test_*`), no
      per-test timeout (only the suite-wide 1200 s), no order randomisation, real firmware build
      CI-only.
- [ ] **TEST.T14** `tests_js/` determinism and isolation: `installMockFetch` leaks between tests,
      `Math.random` in the mock, fixed ports 19420/19481/19482, shared `digital_twin/config`.
- [ ] **TEST.T15** Behaviour × tier matrix per `src/` module (mock, twin, host, web, hardware),
      extending E.6.5: risky behaviours covered by one tier or none. ⟨pass 2, answered: method: OR25.a intent map per layer + OR41.a matrices + OR45.a (4) file × level matrix, all `audit/` working files — G2: R13, R14, R09⟩
- [ ] **TEST.T16** Hang backstops for every runner, not only test.sh: `tests_scripts/` per test,
      Vitest, `cross_browser_smoke.mjs`, each twin-suite run, `tests_hardware/` (no per-test timeout).
- [ ] **TEST.T17** Oracle correctness: `digital_twin/_http_client.py`, `tests_hardware/http_client.py`,
      `_bus_hazard_catalog` adapters, `_tmp_scratch.py` — an oracle bug hides a real bug.
- [ ] **TEST.T18** Reach of the zero-`MemoryError` rule and its two GC stages beyond the four existing
      gates: MicroPython processes no gate scans — `tests_scripts/test_digital_twin_generated_boot.py:
      165-190` (output read only on nonzero exit), `tests_scripts/test_digital_twin_boot_contiguity.py:
      130-140`, the Vitest live twins (`tests_js/_live_twin_command.js:52-78`, `_live_matrix_command.js:57`,
      stdout `"ignore"` — where `src/` logs `memory allocation failed`), `scripts/cross_browser_smoke.mjs:
      92-110`, hardware tests outside the three `MEMORY_ERROR_MARKERS` importers; and these twin launches
      run only at `gc.threshold(32768)` (`run_generic_integration.py:39`), never at -1. Gate each or record
      it as knowingly outside the rule (with `SCR.T01`, `TEST.T06`, `HW.T05`). ⟨pass 2, answered: OR40.a (2): every MicroPython launch is gated and runs both stages; none stays "knowingly outside" — G2: HR100, HR114⟩
- [ ] **TEST.T19** Unit-tier fakes vs the real rp2 API: the main mypy pass resolves `machine` to
      `tests/machine.py`, so `src/` and `tests_hardware/device_scripts/` are type-checked against the fake,
      never the board stub. Scratch passes over `src` alone and `device_scripts` alone against `typings/`,
      triage every finding beyond the 12 known `Timer()` overloads, diff each fake's signatures (`machine`,
      `neopixel`) against the 1.29.0 rp2 source (with `SCR.T15`, `PLAT.T05`).
- [ ] **TEST.T20** (owns OR33 for the software tiers; `HW.T20` for the hardware tier) Necessity of tests
      and tools born of an investigation that has since closed: keep as a regression guard (name the
      property), fold into a cheaper test that proves the same, or retire. Candidates: the manual
      `digital_twin/segfault_stress_repro.py` (its segfault is root-caused and fixed, and the bench burst test
      covers the scenario), tests that re-demonstrate a retired implementation (the `test_tmp_scratch.py`
      pattern CLAUDE.md records), and tests pinned to closed BACKLOG items (5, 6, 9, 12, 29, 30). Never
      retire a guard to save effort (OR12). ⟨pass 2, answered: OR33.a verdict order (keep / make work or move / adopt intent / drop); `segfault_stress_repro.py`'s `gc.collect()` goes (OR54.a (2)) — G2: R17⟩

Seeds:
- **TEST.S01** Tautology: `test_*_bus_membership_matches_the_real_toml_group` is registered only when
  `len(attachments) >= 2` and then asserts exactly that (`tests/test_bus_hazard_generated.py:108-113`).
- **TEST.S02** `scenario_each_occupant_never_touches_an_unexpected_address` swallows exceptions and
  asserts only `touched <= allowed`; an early raise leaves the empty set, which passes
  (`tests/_bus_hazard_catalog.py:523-542`, swallow at `:538-539`).
- **TEST.S03** Step-bound override tests cannot fail: their scripted deltas lie inside both the
  overridden and the default bounds; comments say otherwise (`tests/test_digital_twin_scd30.py:202`;
  `tests/test_digital_twin_bmp3xx.py:151`).
- **TEST.S04** `_scenario_bus_fault_degrades` injects SGP40 faults, starts only the webserver, and GETs
  `/measurements`, which doesn't touch the bus — the fault is probably never consumed; its comment about
  `tests/machine.py` lacking a fault surface is stale (`tests/_digital_twin_construction_scenarios.py:164-193`,
  comment `:165-167`).
- **TEST.S05** The reserved-address check runs on constants defined in the test file itself, with its
  own copy of the range logic (`tests/test_bus_hazard_multi_device.py:63-66, 385`).
- **TEST.S06** The stagger no-coincidence proof re-implements `1000 // (n+1)`; no test reads the real
  `sequencer_timer.period` (`tests_scripts/test_timer_stagger_no_coincidence.py`;
  `src/system_service.py:159`). ⟨pass 2, overtaken: OR47.a (3): sequencer moves to t0 + k·slot with a minimum separation; proof by fake-clock tests of the real sequencer per device and an exhaustive period check — G2: R15, HR040⟩
- **TEST.S07** `_uart_comm_harness.build_pair()` discards `Pair.setup()`'s result (~60 call sites);
  negative-only tests would pass on a failed setup (`tests/_uart_comm_harness.py:116-119`;
  `tests/test_asy_uart_comm.py:687-691`).
- **TEST.S08** Overclaiming names in `_sensortask_scenarios.py`
  (`…light_cmd_led_dispatches_to_the_real_pixel_driver`,
  `…round_trips_a_real_scd30_field_through_the_real_driver` assert only "Valid"; `:897, 987`).
- **TEST.S09** Early `return` when a device lacks a module counts as PASS
  (`tests/_sensortask_scenarios.py:289, 890`); catalog no-op branches likewise.
- **TEST.S10** The cross-occupant write scenario uses `writers[0]` only; dev ISL29125's
  write-vs-siblings is never generated.
- **TEST.S11** `gc.collect()` added as a `MemoryError` workaround in tests
  (`tests/test_digital_twin_sensortask_integration.py:543-546, 627, 705, 779`;
  `tests/_webserver_concurrency_scenarios.py:861`; `tests/test_fram_integration.py:157-177`) —
  MicroPython collects on allocation failure anyway, so a collect that prevents a `MemoryError` points
  at retention or fragmentation. ⟨pass 2, answered: OR39.a (1): a collect propping a test is a defect fixed at its root (retention or fragmentation) — G2: HR115⟩
- **TEST.S12** Absolute heap bounds against E.8's "a leak is a rate"
  (`tests/test_asy_webserver_service.py:1833`; `tests/test_digital_twin_uart_link.py`
  `_hammer_with_the_graph_running`).
- **TEST.S13** Coverage traces `src/` and `digital_twin/` only; generated `sensortask_*.py` gets none. ⟨pass 2, dup: TEST.T09 — G2: HR128⟩
- **TEST.S14** Tight wall-clock bounds under 1-4× core parallelism (`test_asy_dns_client.py:332`,
  `test_captive_dns.py:482`, `test_asy_notification_service.py:1268`, `test_asy_udp_socket.py:926, 994, 1350`);
  fixed `sleep(1.0)` for bind; 43 of 47 local `run()` helpers unbounded.
- **TEST.S15** Mock/twin divergences: `reset()` returns in `tests/machine.py:700` but raises in the
  twin; mock WDT accepts any timeout/id; mock `Pin.init()` drops `pull` (`:51-54`); mock `trigger_irq()`
  ignores edge direction; mock `scan()` lists only seeded addresses.
- **TEST.S16** Helper bug suspicion: `AdversarialPeer.recv()` tests `poller.ipoll(0)` for truthiness,
  which this build reports as ready every tick (`tests/test_asy_udp_socket.py:291` vs
  `tests/test_asy_dns_client.py:350-353`).
- **TEST.S17** `test_reset_call_site_invariant.py` scans `src/` only; `WDT()` now lives in generated
  code; aliased imports (`from machine import reset`) escape the substring match
  (`tests/test_reset_call_site_invariant.py:7-11, 24`). ⟨pass 2, overtaken: OR31.a (1): WDT is the first statement of the generated boot entry; the invariant test scans generated code and asserts placement; aliased-import escape stays work — G2: R27, HR053⟩
- **TEST.S18** Duplication: 7 copies of the Timer raise-on-arm context manager; 47 local `run()`s; 20
  files with their own `run_timed`/`_wait_until`/`_cancel`. ⟨pass 2, dup: TEST.T08 — G2: R26⟩
- **TEST.S19** Live PUT matrix covers wozi only (`tests_js/live-backend-put-matrix.test.js:58`); live
  tests skip-and-pass without the toolchain (`tests_js/live-backend.test.js:13-16`). ⟨pass 2, answered: OR43.a (3)/OR54.a (1): live matrix per derived device; OR21.a (3): skip-and-pass goes — G2: R27, HR019⟩
- **TEST.S20** Only ISL29125 has a C.11.1 conformance probe; SCD30, SGP40, BMP3xx and FRAM fakes have
  none and nothing requires one.
- **TEST.S21** E.1 says TCP port bases lie in 17400-19999, but `_webserver_concurrency_scenarios.py:77`
  allocates `19700+200*i`, reaching 20700+. ⟨pass 2, overtaken: OR38.a (3): self-chosen ports OS-assigned (port 0), product-fixed ports under a lock; the band text goes (V74) — G2: HR130⟩
- **TEST.S22** The comment-cap gate counts physical lines, and E501 is ignored, so a docstring can pack
  a paragraph onto one 400-700-character line and pass (`digital_twin/_fault_injection.py:3`,
  `digital_twin/run_generic_integration.py:1-2`,
  `tests/test_digital_twin_run_generic_integration.py:1-2`, `buildgen/twin_wiring.py:1-2, 35-36`,
  `scripts/_digital_twin_ci_suite.py:5-7`, `scripts/_render_coverage.py:6-7`) — owner decision on a
  character bound (PQ6). ⟨pass 2, answered: PQ6/OR51: the comment rule applies to every file; a paragraph packed on one line breaks "concise" and is counted by length (HR077) — G2: HR077⟩
- **TEST.S23** `tests/microtest.py:17-28` counts a test as PASS whenever the call raises nothing: an
  async test would pass without running; a file with no footer exits 0 and `test.sh:374-376` records
  PASS; no instance today, nothing guards against it. ⟨pass 2, dup: TEST.T12 — G2: R02⟩
- **TEST.S24** Stale references to retired runners/hand-written modules
  (`tests/test_digital_twin_run_generic_integration.py:2, 137-138, 221`; `digital_twin/run_generic_integration.py:2, 34, 98, 312`;
  `.gitignore:75`).
- **TEST.S25** The existing rollover tests cannot fail for the `XCUT.T25` class: `tests/test_ticks_rollover.py:98-111` detects only raw `now - t0` subtraction, and its `_KNOWN_TICKS_USERS` inventory (`:10-17`) asserts nothing about stored-value age or delta size; its docstring (`:1-2`) repeats F.1's every-use-is-short claim (`DOC.S23`); `test_time_to_settle_stays_sane_across_a_ticks_wrap` (`test_asy_isl29125_driver.py:652-661`) and `test_the_hold_off_deadline_survives_the_ticks_rollover` (`test_asy_uart_comm.py:748-757`) probe deadlines within ~±1 s on a 2**62 period; no ticks fake exists (every `FakeTime` in `tests/` fakes the wall clock only).

Quality measure: every seed resolved; a mutation-sweep report per `src/` module; a list of CLAUDE.md
rules with their enforcing test (or "review-only, accepted").

---

### 5.17 TWIN — Digital twin

**Goal**: each fake models the real chip/port faithfully where tests depend on it, and every
known infidelity is documented where a test author will see it.
**References**: `digital_twin/README.md`, Parts A.10, C.11.1, E.6.5, E.7-E.9.

Topics:
- [ ] **TWIN.T01** Per chip fake: behaviours modelled vs datasheet (command gating, CRC on written
      arguments, execution-time NAKs, general call, soft reset, measurement interval 0).
- [ ] **TWIN.T02** Fake `machine`: Timer as asyncio task (no soft-callback drop), WDT enforcement,
      reset/bootloader exceptions, RTC return value, I2C bus-level faults (no busy knob).
- [ ] **TWIN.T03** Fake `network`: connect phase timing, AP-mode config validation.
- [ ] **TWIN.T04** FRAM fake: framing inferred from `write()` pairing instead of CS; wraparound;
      out-of-range writes growing the buffer.
- [ ] **TWIN.T05** Fault-injection catalogue: map the fault ops tests inject against the ops each
      driver actually issues (e.g. no BMP `writeto` hang).
- [ ] **TWIN.T06** 64-bit, non-frozen heap caveat applied to every twin-tier allocation assertion
      (E.8).
- [ ] **TWIN.T07** Unix-port helper modules (`unix_port_gc_unwedge.py`, `unix_port_poll_prewarm.py`,
      `_unix_port_udp_addr_shim.py`) — still needed after the root-cause fixes? ⟨pass 2, answered: unwedge retired after the override test (OR52.a (6)); prewarm and UDP shim stay until upstream fixes, each with its trigger — G7: R12, HR091, HR096⟩
- [ ] **TWIN.T08** Network-stack fidelity: the twin runs on the host's Linux stack — lwIP limits (TCP
      PCBs 9, pbuf pool, `MEM_SIZE`, TIME_WAIT/PCB reuse, backlog) are unmodelled; every twin claim
      about connection ceilings needs this caveat in the infidelity table.
- [ ] **TWIN.T09** Time fidelity: Timers as asyncio tasks, `ticks_ms` wraparound never reached,
      class-level `RTC._shared_datetime`, dependence on `TZ=UTC`.
- [ ] **TWIN.T10** Twin state files: `_load_state()` on corrupt files, repo paths shared across suites
      (`SCR.S09`), state flushed only at shutdown.
- [ ] **TWIN.T11** Files no other TWIN topic reaches: `launch.py`, `run_generic_integration.py`'s CLI,
      `segfault_stress_repro.py` (still needed?), `_http_client.py`, `neopixel.py` (colour order/timing
      unmodelled), `_isl29125_chip.py` vs its conformance probe.
- [ ] **TWIN.T12** Twin ↔ generator contract: `compute_twin_wiring()` vs `configure_wiring()` (no
      schema version); the deliberate `tests/machine.py` ↔ twin `machine.py` duplication, owned by
      `TEST.T05`.

Seeds:
- **TWIN.S01** SCD30 fake produces readings regardless of start/stop continuous measurement, never
  checks argument CRCs, accepts interval 0 (a 0 ms periodic timer), treats soft reset as a no-op
  (`digital_twin/_scd30_chip.py:145-153, 167-196`, soft reset `:175`).
- **TWIN.S02** SGP40 fake models no command execution time and doesn't validate compensation-word CRCs;
  the twin's general call reaches no chip, so the SGP40 self-reset is unmodelled
  (`digital_twin/_sgp40_chip.py:59-76`; general call dropped at `digital_twin/machine.py:266`).
- **TWIN.S03** BMP3xx fake: chip ID 0x60 only; no `writeto` hang knob
  (`digital_twin/_bmp3xx_chip.py:21, 177`).
- **TWIN.S04** (mock half owned by `TEST`) FRAM fakes (mock and twin) infer transaction framing from
  `write()` pairing, not CS, so a single write carrying opcode+address+data would lose the data; no
  wraparound (`digital_twin/_fram_chip.py:108-139`, buffer growth at `:116`).
- **TWIN.S05** Twin `RTC.datetime(set)` returns the tuple where the real call returns `None`; twin
  `network.py` validates no AP-mode config (`digital_twin/machine.py:906-913`;
  `digital_twin/network.py:145`).
- **TWIN.S06** `digital_twin/README.md:107-108` says `WLAN.connect()` connects "immediately", but
  `digital_twin/network.py` uses a 0.7 s async phase (`_CONNECT_DELAY_S`, `:33`).

Quality measure: an infidelity table in `digital_twin/README.md`, each row either fixed or accepted.

---

### 5.18 HW — Real-hardware tier (desk review; execution gated)

**Goal**: the hardware tier is safe for the board, the host and the evidence; its tests assert what
they claim; its docs are current. Desk review needs no go-ahead; anything touching the board or bench
network does (CLAUDE.md), and is otherwise queued in BACKLOG.md's "Real-hardware work still owed" section.
**References**: `tests_hardware/README.md`, Parts E.6, E.8, E.9, B.12, B.13; BACKLOG.md "Real-hardware work
still owed" (which absorbed `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md`, `03f8bcf`; both
readable at `2a88cc8`), `HEAP_FRAGMENTATION_MEASUREMENTS.md`, `dev_legacy/README.md`; Appendix B.

Topics:
- [ ] **HW.T01** Wear: every flash/NVM write a test *owns* vs its markers (`persistence_write`,
      `scd30_extra_write`), including `device_scripts/` — prerequisite writes stay unmarked by
      CLAUDE.md's rule, and FRAM writes are outside the gate (list them for evidence overwrite,
      `HW.T02`).
- [ ] **HW.T02** Evidence safety: automatic `errcount` snapshot before the first `ResetErrors`; which
      scripts overwrite production FRAM chunks; `_FRAM_BACKED_MODULES` completeness.
- [ ] **HW.T03** Board safety: scripts leaving non-volatile state behind (FRAM WPEN/BP, SCD30 NVM
      settings), watchdog-armed boards running long scripts, credentials files left on the board.
- [ ] **HW.T04** Host safety: bridge operations with/without a dead-man's switch; routine tests that
      rebuild the host environment (SSD wear, third-party dependency).
- [ ] **HW.T05** Oracle bite: every test's assertion vs its name; engagement floors for passive tail
      tests; `reset_cause()` checks.
- [ ] **HW.T06** Harness facts: what `hard_reset()` really does (mpremote source), out-of-band reset
      availability, raw-REPL side effects (stops `main.py` → WDT reset ~8 s later). ⟨pass 2, answered: `hard_reset()` = `mpremote reset` = `machine.reset()` via raw-REPL exec (v1.29.0 `main.py:407-411`); raw REPL Ctrl-C's `main.py`; no out-of-band power reset on the bench (A40); doc fixes owed in HR188 — G1: R14, R07; HR188⟩
- [ ] **HW.T07** Bench-rig facts vs docs: desk review only compares the docs with each other (MPRLS on
      i2c0? FRAM part number on dev); which version is physically true becomes a real-hardware entry (a
      bus scan), never settled from the docs.
- [ ] **HW.T08** Hardcoded pins/timeouts/addresses in device scripts vs `devices/dev.toml`.
- [ ] **HW.T09** Structural-exception claims (E.6.6, C.8, `tests_hardware/README.md` tenth pass)
      re-derived from source.
- [ ] **HW.T10** Real-hardware entry hygiene (the queue and handover are folded into BACKLOG,
      `03f8bcf`): owner decisions filed as hardware work (F18, T4, W3, T1 — `DOC.S28`), retired row IDs
      still cited from permanent code as "queue <ID>" (`DOC.S06`), entries that state board state which
      only holds until the next sitting (BACKLOG.md:353-361).
- [ ] **HW.T11** Bench credentials consistency (owner, 2026-09-25: low risk, **consistency not
      security**): throwaway bench credentials are generated or read at run time (`bench.ap_password()`)
      and never persisted in files; harmonise every script to that convention.
- [ ] **HW.T12** Harness library line by line: `harness.py`, `bench_control.py`, `http_client.py`,
      `error_log_helpers.py`, `conftest.py`, `soak_tiers.py`, `heap_map.py`, `ntp_probe.py`,
      `rogue_udp_responder.py`, `website_identity.py`, `isl29125_conformance.py`, `bench/dns_probe.py` —
      parsing, timeouts, exception mapping, teardown safe to run twice; host state left when pytest is
      killed mid-test (iptables DNAT/DROP, `tc netem` qdiscs, `ap_down()` without `ap_up()`) and whether
      anything restores it at session start (with `HW.T04`, `TOOL.T03`).
- [ ] **HW.T13** Opt-in gate mechanics per marker (`persistence_write`, `scd30_extra_write`,
      `flash_cycle`, `long_soak`, `multi_day_rollover`, `neopixel_sweep`): deselect vs in-test skip;
      `role_reversal`/`over_provisioned_image` are informational, not gates (`HW.S25`); and the
      interaction with `_require_clean_hardware_run.sh` (skip = failure; deselected count reported)
      (with `SCR.T05`, `TEST.T06`, `CI.S13`).
- [ ] **HW.T14** Board-free checks (run only on a host with no board attached, and confirmed with the
      owner at go-ahead — CLAUDE.md gates `tests_hardware/`'s runners, PQ4): `uv run pytest tests_hardware --collect-only`
      under each flag combination, marker completeness, mypy on `device_scripts/`; which of these CI
      runs.
- [ ] **HW.T15** Manual tier currency: every `manual/*.py` instruction vs today's firmware (routes,
      field names, units, bounds, chip names, the deferred config write) and whether each leaves the
      board as found (`HW.S03`, `HW.S04`, `HW.S21`, `HW.S22`).
- [ ] **HW.T16** Measurement provenance: every silicon figure in SPEC, BACKLOG, `tests_hardware/README.md`
      and `HEAP_FRAGMENTATION_MEASUREMENTS.md` names the image, commit and flags it was taken on; list
      figures whose code has moved since (image E6′ is already behind the tree; the 2026-09-25 figures
      came from image `12:54:13Z`, tree `851e816`, and from throwaway images that were never committed,
      `38b270d`).
- [ ] **HW.T17** Board-history provenance for CLAUDE.md's FRAM-evidence caveat: is there any host-side
      record of which device scripts ran against the board since its last flash (each builds its own
      `AsyFramManager` over production's first chunks)? If not, ask the owner whether one is wanted. ⟨pass 2, answered: no board-history record; save-first order suffices (section 4, 4) — G1: R11, R02⟩
- [ ] **HW.T18** Re-base HW desk findings on the 2026-09-24/25 sitting, which finished before the
      baseline: two clean default bench tiers, one clean wear-gated run (128 passed), R1/R4/R5/R6/R7/T2/
      W3/W4/W5/F1/N2/G3/G8/G12 closed or measured (`851e816`..`a9c8627`; Appendix B). Seeds written
      before it (`HW.S09`, `HW.S15`) are updated; any later sitting another session runs is folded in the
      same way. ⟨pass 2, overtaken: seeds already re-based (S09, S15, S26-S28); no later sitting can occur while `main` is frozen (OR52.a (4)) except Phase C, which R02 covers — G1: R02⟩
- [ ] **HW.T19** Image identity: can a run know which tree the board's image was built from? The image
      carries only hand-bumped versions (`buildgen/version.py:7-8`) and a build date (`buildgen/codegen.py:
      351, 603`) — no commit, no dirty flag; device scripts run against whatever frozen `src/` is on board
      (`tests_hardware/harness.py:440-447`); `configured_max_connections()` "describes the TREE, not
      necessarily the image" (`harness.py:40-41`). Propose a checkable identity (commit + dirty flag in
      `build_info`, verified before a run) or record the gap (with `HW.T16`, `GEN.T14`, `PAR.T06`). ⟨pass 2, answered: `buildDate` compared with the round's own build (owner D3), no product field — G1: R02⟩
- [ ] **HW.T20** (owns OR33 for this tier) Necessity of every owed real-hardware entry and every
      investigation-born test or device script: keep (standing regression or contract value, named), retire
      (investigation closed, a lower tier proves the same property, or the only purpose was a one-off
      measurement already migrated), or owner decision. Starting list: Appendix B (orphan scripts, one-off
      repros, measure-A/B instruments, the multi-day rollover test, the long soak).

Seeds:
- **HW.S01** `tests_hardware/flash/test_toolchain_flash_boot.py:30-42` is unmarked and runs
  `setup_toolchain.py env --tier flash` (~481 s): git fetch, toolchain rebuild, `uv sync` into the venv
  pytest runs from, `npm ci`, Playwright — host SSD wear, a third-party dependency inside a hardware
  run.
- **HW.S02** `[x2]` SCD30 NVM *is* reachable over REST (`asy_scd30_driver.py:257-275` dispatch;
  `asy_webserver_service.py:431`), contradicting E.6.6 exception 2 (SPECIFICATION ~3203), C.8 (~2153),
  `tests_hardware/README.md:758, 1139, 1182, 1205, 1249` and
  `bench/test_sensor_config_push_over_real_hardware.py:22`; the manual tier even instructs it.
- **HW.S03** `manual/manual_persistence.py:37-47` sets SCD30 `MeasInt=7` with no restore; later SCD30
  tests assume ~2 s (`device_scripts/scd30_real_irq_edge.py:11`).
- **HW.S04** The manual "FRAM" power-cycle test PUTs `WarnCO2=424242` (range 0..3000 → Invalid), the
  value lives in the flash config not FRAM, and it names the wrong chip (`manual_persistence.py:3, 14, 18-19`).
- **HW.S05** `device_scripts/isl29125_mechanism_envelope.py:100-108, 150-162` makes ~5 flash writes
  under `neopixel_sweep` only (9 `_set_dict_cfg` calls across `:150-193`); the marker-completeness guard
  excludes `device_scripts/` (`tests_scripts/test_persistence_write_marker_completeness.py:52-53`).
- **HW.S06** ~86 `ResetErrors`/`reset_all_error_logs` lines in 12 files (count depends on the grep), no
  automatic `errcount` snapshot; `bench/test_memory_stress_bench.py:120` resets at start; its
  `_FRAM_BACKED_MODULES` (`:22`) omits WIFI, NTP, WEBSERVER, DNSSRV, `CFGMGR_*`, `UART_*`.
- **HW.S07** `fram_write_protect_roundtrip.py` sets non-volatile WPEN|BP0|BP1 and restores only in
  `finally`; a WDT reset or killed mpremote would leave production FRAM silently write-protected.
- **HW.S08** `device_scripts/wifi_reconnect_after_failed_attempts_repro.py:9-10` persists a throwaway
  bench SSID/PSK in the file — owner: low risk, a consistency breach (see HW.T11), not a safety one;
  `dev_legacy/README.md:661` records the Pi's `eth0` MAC (minor, same topic).
- **HW.S09** `wifi_service_reconnect_repro.py` (row F1) runs up to 13 min without feeding the
  watchdog that production arms (`codegen.py:381`), so it is reset ~8 s in on a board running
  `main.py`, leaving `config_HWTEST_WIFI.cfg` (with the real WiFi password) behind. Confirmed and
  worked around on 2026-09-25 (`6f7eef7`): F1 passed only under an out-of-repo 4-line wrapper arming
  `WDT(8000)` and feeding it from a 2 s `Timer` (`tests_hardware/README.md:383-385`); BACKLOG.md:721-728
  asks the owner to fold that in or keep the wrapper, and whether stale `config_HWTEST_*.cfg` files left
  on the board by earlier scripts should be removed on exit. See Appendix B for whether the script is
  still needed at all. ⟨pass 2, answered: scratch removed on every path (OR38.a (4)); keep-and-fold or retire by OR33.a; fold as chunked feeds — G1: R09; HR191⟩
- **HW.S10** `bench/test_hotspot_role_reversal.py:58-89` persists `SSID=""` and calls `ap_down()`
  before `yield`; a stage 1-2 failure skips the teardown and strands board and bench AP.
- **HW.S11** Four role-reversal tests assert nothing of their own (`pass`, a constant equal to itself,
  non-empty) (`test_hotspot_role_reversal.py:132-156`).
- **HW.S12** `bus_topology_autodetect_and_hazard_sweep.py:33-44`: `_probe()` returns `None` for both
  NAK and ACK, so the address sweeps can't fail on either; self-hazard overlap unproven;
  `dev_legacy/README.md:48` lists an MPRLS on i2c0 while `tests_hardware/README.md:1107` says "i2c0:
  BMP3xx alone".
- **HW.S13** `bench/test_network_resilience.py:328-362` can't distinguish DNS garbage from silence;
  `tests_hardware/README.md` says DNAT-to-loopback does not deliver locally yet calls the
  `RogueUdpResponder` tests unaffected in the same bullet (671-680, claim at 678-679; restated
  993-1003).
- **HW.S14** Soak tests assert less than their names: no memory trend, no timing, "never observed"
  clock stretch; no engagement floor; `DebugLevel`-dependent; `is_reachable()` stops `main.py` and the
  WDT reboots ~8 s later (`bench/test_memory_stress_bench.py:136-174`,
  `flash/test_memory_stress.py:87-105`, `flash/test_bus_electrical_timing.py:83-93`).
- **HW.S15** Loose oracles: `"CFGMGR_" in log or "FRAM" in log` (`flash/test_reboot_persistence.py:66`,
  reused `test_network_resilience.py:311, 342`); watchdog-starvation doesn't check `reset_cause()` —
  its new sibling in the same file does (`flash/test_watchdog_starvation.py:74`, `HW.S26`), so the two
  now disagree.
- **HW.S16** Orphan device scripts with no wrapper (`wifi_country_hostname_edge_values.py` whose both
  branches print PASS, the two WiFi repros, `heap_layout_after_full_boot_sequence.py`).
- **HW.S17** Doc drift: README:1354 "73" bench tests (85 now); MB85RS64V named for dev while the device
  scripts and `dev_legacy` say MB85RS2MTA (which is physically true is `HW.T07`) at README:710,
  `flash/test_fram_storage.py:1`, `manual_persistence.py:3, 14`; `hard_reset()` described as DTR vs
  `machine.reset()`; stale `DebugLevel` comments (`test_reboot_persistence.py:52, 68, 77, 79`);
  README:503 rollover guidance; README:87 and `run_bench_soak_tests.sh:4` point at `conftest.py` for
  `SOAK_TIER_SECONDS` (it's `soak_tiers.py`); README:588 datasheet list omits isl29125 (also root
  `README.md:398-400` and `run_bench_soak_tests.sh:16` point at `conftest.py`);
  `bench_control.py:103-104` says OUTPUT/FORWARD.
- **HW.S18** Pins hardcoded in ~20 device scripts with no guard vs `devices/dev.toml`; two SGP40
  scripts omit `timeout=200000` on i2c1 (`sgp40_voc_algorithm_quality.py:46`,
  `sgp40_fram_backup_restore.py:54`), possibly resetting SCD30's bus timeout on the per-bus singleton.
- **HW.S19** Silent assumptions: stable DUT DHCP address across resets, passwordless `sudo`,
  `mpremote_connect.sh` default `/dev/ttyACM0` may be the Arduino, fixed 2 s link-local sleep, the "> 45
  s between reset and attach" trap unenforced.
- **HW.S20** `dev_legacy/README.md` stale: "MicroPython 1.28.0" (line 19), "Current bench state (as of
  2026-09-02)" (595-665), the superseded bench-frozen-firmware recipe.
- **HW.S21** `manual/manual_persistence.py:52` names a `config.json` write (the refactor writes
  `config_<NAME>.cfg`), and `:56-59` assumes the 200 response marks the flash write — since WP5 the
  write is deferred to a task after the response, so "cut power right after sending" hits another
  window.
- **HW.S22** `manual/manual_sensor_accuracy.py:24, 30` asks for a `Press` field in Pa; the driver
  publishes `Pres` in hPa with `PressOffset` applied (`src/asy_bmp3xx_driver.py:102, 106`).
- **HW.S23** `bench/test_memory_stress_bench.py:18-19` says WIFI, NTP and every `CFGMGR_*` logger are
  RAM-only; CLAUDE.md:367-376 says they joined the FRAM-backed set. ⟨pass 2, dup: same finding as HW.S06's `_FRAM_BACKED_MODULES` half — G1: R12⟩
- **HW.S24** `manual/manual_wifi.py:19, 30` hardcode the hotspot password `12345678`; the source of
  truth is `devices/dev.toml:7` (`HW.T11` consistency).
- **HW.S25** `role_reversal` (and `over_provisioned_image`) are informational markers, not gates
  (`tests_hardware/conftest.py:111-113`), and `run_bench_hardware_suite.sh:11` excludes only the soak
  markers — so the role-reversal scenario, with its documented stage-6 permanent-WLAN-deactivation risk
  (`HW.S10`), runs in every routine bench pass. Should it become a gate? ⟨pass 2, stale: verified at HEAD: stage 6 (`test_hotspot_role_reversal.py:394`) is `persistence_write`, deselected by default; routine passes run only read-only stages and the prerequisite SSID clear — G1: R28, R05⟩

- **HW.S26** `flash/test_watchdog_starvation.py`'s two tests differ in oracle and style: the G3 test
  (`:54-78`) asserts `reset_cause() == WDT_RESET` through a hardcoded `_WDT_RESET = 3` (`:51`, a mirror of
  `machine.WDT_RESET` no test pins), the original (`:16-47`) asserts no reset cause; both end with the
  same closing `hard_reset()` (`:43-47`, `:75-78`), duplicated rather than shared (OR24).
- **HW.S27** New device-script facts held only locally: `uart_driver_read_never_blocks_the_loop.py:27`
  `POLL_WAIT_MS = 2` "mirrors sensortask_dev.py's own transaction rate" (a generated value, `HW.T08`);
  `reboot_fallback_starves_the_watchdog.py:24` loops to 64 "the real pool is small and fixed" while the
  measured pool is 16 (`79423dd`, commit message only — a platform fact for Part F, OR29).
- **HW.S28** Two fixes are "not yet confirmed on silicon" (BACKLOG.md:362-367): SGP40 `W13`'s one slot
  per outage needs NTP blocked past `SGPWaitTimeNTP` (default 30 backups, ~30 min, `asy_sgp40_driver.py:53`);
  the flash tier's closing `hard_reset()` needs a full flash-tier run. Both are logic already pinned by
  unit tests (`tests/test_asy_sgp40_driver.py:1068-1128`) or by the test itself (Appendix B). ⟨pass 2, overtaken: W13 half: OR35.b replaces the episode flag; hard_reset half: confirmed by Phase C's first full flash run — G1: R02⟩

Quality measure: desk findings resolved or moved to BACKLOG's real-hardware section; every
silicon-needing check is an entry there with flags and wear stated.

---

### 5.19 SEC — Security threat model (cross-cutting)

**Goal**: the threat model (PQ5: trusted home LAN, OR52.a (3)) stated in SPECIFICATION.md and every exposure classified against it — defect, accepted
property (with the owner's decision recorded), or out of model.

Topics:
- [ ] **SEC.T01** Write the threat model: actors (LAN peer, browser page on the LAN via DNS rebinding,
      radio-range attacker in hotspot mode, local user on the dev/bench host, supply chain), assets
      (availability, config, FRAM evidence, flash/NVM endurance, credentials). ⟨pass 2, answered: trusted home LAN (PQ5, OR52.a (3)); the statement is U29 work — G5: R57⟩
- [ ] **SEC.T02** Unauthenticated write surface: `SystemCmd` (`bootloader` = offline until physical
      intervention; `reboot`; `mempause`), `ResetErrors` (irreversible evidence wipe), SSID/PW changes,
      every config write (flash/NVM wear by alternation). ⟨pass 2, answered: unauthenticated writes and `bootloader` accepted (OR52.a (3)); `ResetErrors` global (OR70.a (7)) — G5: R57, R02, R23⟩
- [ ] **SEC.T03** Browser-borne attacks: CSRF (blocked by JSON content-type + no CORS?), DNS rebinding
      (no Host check), clickjacking (no X-Frame-Options/CSP). ⟨pass 2, answered: browser-borne attacks = PQ5 option (b), not chosen; XSS-safety stays (R58) — G5: R57, R58⟩
- [ ] **SEC.T04** Radio-range: shared default hotspot password in all 6 TOMLs (accepted-risk rule in
      CLAUDE.md), captive DNS spoofing, bogus-SSID → hotspot → second streak → permanent WLAN
      deactivation (A.4 intentional; a remote DoS needing a power cycle). ⟨pass 2, answered: radio range out (OR52.a (3)); hotspot password permanent (OR70.a (1)); WLAN deactivation owner-directed (A49) — G5: R60, R57⟩
- [ ] **SEC.T05** Protocol-level: HTTP body/header bounds (`REST.S01`, `REST.S02`), NTP reply spoofing
      (no origin check), DNS response validation, captive-DNS subnet filter by source address.
- [ ] **SEC.T06** Host-side: `setcap` on the interpreter (owned by `SCR.T07`), secrets in argv/logs and
      `sudo` usage (owned by `TOOL.T01`), downloaded binaries without signatures (owned by
      `TOOL.T02`/`CI.T14`) — SEC only records the disposition.
- [ ] **SEC.T07** Credential hygiene consistency (owner, 2026-09-25: consistency, not safety) — see
      `HW.T11`; plus the known accepted hotspot fallback password in `src/asy_wifi_service.py`.
- [ ] **SEC.T08** Attack-surface inventory per mode (STA, AP, deactivated): HTTP 80 on all interfaces,
      captive DNS 53 (AP), cyw43 DHCP server (AP), mDNS 5353 if compiled into rp2 1.29 (unverified),
      ICMP; physical: USB-CDC/raw REPL (plaintext `PW` in `config_WIFI.cfg`), BOOTSEL/UF2, the dev UART
      jumper.
- [ ] **SEC.T09** Availability and evidence integrity vs a LAN peer: slot exhaustion (6 × 15 s, no
      per-peer limit), ring eviction via client-provoked entries (`CORE.S11`, `REST.S05`), repeated
      `mempause`/`reboot` (`XCUT.S03`), flash wear by alternating PUTs, stdout stalls (`REST.T13`). ⟨pass 2, answered: trusted LAN; eviction bounded by OR35.b; no write-rate limit, own clients audited (OR42.a (3)) — G5: R57, R34, HR012⟩
- [ ] **SEC.T10** Information exposure and outbound traffic: what unauthenticated GETs reveal (SSID,
      hostname, versions + build date, full error histories) and every outbound destination (DHCP DNS,
      8.8.8.8/1.1.1.1 `NET.S04`, NTP host) — disposition each under PQ5. ⟨pass 2, answered: exposure accepted (PQ5); DNS fallback becomes a config value (OR56.a (2)) — G5: R57⟩
- [ ] **SEC.T11** Trust in time and names: spoofed NTP → RTC, `TS`, FRAM backup age, notification
      window; spoofed DNS → NTP at an attacker's host; DNS id entropy (`os.urandom(2)`) and source-port
      predictability (`LWIP_RAND`) (with `NET.T03`/`T04`, `STOR.T09`). ⟨pass 2, answered: spoofing by a LAN peer out of model; parser robustness stays (NET) — G5: R57, R31⟩
- [ ] **SEC.T12** Secret scan of the full git history (all refs, unshallowed clone): real WiFi SSID/PSK in
      once-committed `config_*.cfg`, device scripts or logs (`.gitignore:84-89` only guards future
      commits), bench PSKs, tokens; cross-check GitHub's secret-scanning status; disposition under PQ5 and
      repo visibility under PQ10 (bench throwaways are a consistency matter per owner, `HW.T11`).

Seeds: `REST.S01`, `REST.S02`, `REST.S04`, `REST.S05`, `NET.S04`, `NET.S12`, `NET.S16`, `NET.S17`,
`NET.S19`, `CORE.S11`, `XCUT.S03`, `HW.S02`, `TOOL.S01`, `SCR.S06`, `WEB.S17`, `HW.S08`, `CI.S04`, `CI.S06`
(cross-referenced, not repeated).

Quality measure: a threat-model table with a disposition per exposure, signed off by the owner.

---

### 5.20 MEM — Memory safety (cross-cutting)

**Goal**: the Part I discipline holds everywhere: no client-controllable or unbounded allocation, no
churn of same-shaped objects on hot paths, long-lived objects placed at boot, zero `MemoryError` at
both GC stages without `gc.collect()` props.
**References**: Part I (esp. I.2, I.3, I.4, I.6), `HEAP_FRAGMENTATION_MEASUREMENTS.md`, E.8.

Topics:
- [ ] **MEM.T01** Re-walk I.2's hotspot catalogue against current code (it predates several modules).
- [ ] **MEM.T02** The placement-lens re-walk BACKLOG already names: which run-phase code allocates
      something long-lived while bus/network churn is in flight?
- [ ] **MEM.T03** Client-controllable allocation (HTTP, DNS/NTP replies, UART peer-declared sizes —
      `CHUNKS` deliberately left as is, BACKLOG: record, don't re-raise —, captive DNS datagrams) — each
      bounded before allocation.
- [ ] **MEM.T04** Per-cycle churn: log entries (fresh chunk buffer + lock), `pr.all()` argument tuples
      built at level 0, `write_config` dict copies, CRC `add()`/`check()` copies, f-strings in hot
      paths.
- [ ] **MEM.T05** Tests: `gc.collect()` props and absolute heap bounds — owned by `TEST.T03`
      (`TEST.S11`, `TEST.S12`). ⟨pass 2, dup: owned by `TEST.T03` (`TEST.S11`, `TEST.S12`) — G4: R50, R47⟩
- [ ] **MEM.T06** Does anything in `src/` still need one big contiguous allocation (I.4's forbidden-fix
      rule)?
- [ ] **MEM.T07** Target representation gap: rp2 small ints stop at ±2**30 and every float is a heap
      object (Unix port: ±2**62) — bigint/float churn in VOC, CRC32, `math_helpers` and driver formulas
      never reaches either tier's `MemoryError` gate; quantify per cycle (`ALGO.S07`, `ALGO.S08`).
- [ ] **MEM.T08** Per-call wrapper allocations on hot paths: `asyncio.wait_for()` (task + closure per
      call), memoryview slices (`BUS.S07`), `schema_dict()` rebuilt per field in `_set_dict_cfg`
      (`src/base_classes.py:346`), `*args` tuples.
- [ ] **MEM.T09** C-stack budget: rp2 main stack vs the deepest await chain; a `MICROPY_STACK_CHECK`
      `RuntimeError` would be swallowed by broad `except Exception` nets.

Seeds: `REST.S01`, `REST.S02`, `NET.S10`, `CORE.S07`, `TEST.S11`, `TEST.S12` (cross-referenced).

Quality measure: updated hotspot catalogue; every allocation site classified bounded/fixed/
client-controlled.

---

### 5.21 PERF — Timing and capacity budgets (cross-cutting)

**Goal**: every budget the system relies on is computed from code, checked against measurements, and
has a test that fails before the budget is crossed.
**References**: F.1, F.2, F.3, F.5.8/F.5.9, I.1 (GC pause), SPECIFICATION.md ~1854 (~305 ms yielding
per FRAM chunk), ~3985-3992 (~21 ms non-yielding block hold), BACKLOG 24/32.

Topics:
- [ ] **PERF.T01** Watchdog: worst-case feed gap (XCUT.T03). ⟨pass 2, dup: owned by `XCUT.T03`; PERF keeps the budget-table row — G4: R58, R64, HR053⟩
- [ ] **PERF.T02** HTTP capacity: ~2.2 requests/s saturation, `max_connections` 6, slot release lag, UI
      polling rates, hidden tabs, no caching of static assets.
- [ ] **PERF.T03** `ResetErrors` sweep cost vs `outer_cap_s` and the UI timeout (BACKLOG 24/32 — R2
      measured 2026-09-25: the curve does not flatten, ~+3.5 s per reader, 88-98 % of the cap at 3
      readers; F18 at 4 — budget and design fix are the owner's; R4 the same day: every populated log
      read back 0 at three readers in 14.58 s, and the UART exerciser's `E20`/`E22`/`W10` start at three). ⟨pass 2, answered: OR72.a (5): concurrent reset, then a bench budget; four readers a degradation check (OR72.a (1)) — G4: R62⟩
- [ ] **PERF.T04** Bus budgets: SCD30 50 ms sleeps under the bus lock, probe sleeps, FRAM block hold
      (~21 ms), SPI re-init per CS, VOC processing cost, CRC per-byte yield.
- [ ] **PERF.T05** Lock-hold stalls in networking (60 s sleep, 5 s connect poll, ~6.5 s NTP attempt) —
      owned by `NET.T02`; PERF records only the budget. ⟨pass 2, dup: owned by `NET.T02`; PERF records only the budget — G4: R64⟩
- [ ] **PERF.T06** Boot is not a metric to optimise (CLAUDE.md WP6): verify only that the setup batch
      never starves the WDT on the device with the most setup units (`dev`, ~21 FRAM loggers; silicon
      2026-09-25, R7: 79-91 ms per unit, the whole batch 0.93 s, import ~1.1 s, timer stagger 0.79 s —
      SPECIFICATION.md:542-547; the twin's ~170 ms per logger overstates it — OR17, `TWIN.T04`).
- [ ] **PERF.T07** Idle CPU: polling loops (captive DNS 50 Hz, UART idle rate, neopixel busy-waits).
- [ ] **PERF.T08** Inventory of no-yield stretches with durations (littlefs flush with IRQs off, I2C up
      to its `timeout`, GC pause ~15-21 ms, `vocalgorithm_process()` on target, CRC32 with bigints,
      `print()`), each against every timing-sensitive consumer's tolerance.
- [ ] **PERF.T09** Measured event-loop lag under combined worst-case load, twin and bench (a BACKLOG
      real-hardware entry).
- [ ] **PERF.T10** Persisted-log rate budget: every `err_s`/`wrn_s` costs a ~305 ms yielding FRAM chunk
      write queued on the FRAM lock (`src/print_log.py:167-178`); worst-case entries/s per module in a
      fault storm and what that queue delays (`XCUT.S01`).
- [ ] **PERF.T11** Console cost: at `DebugLevel` > 0 (REST-settable) every log line is a synchronous
      `print()`; with a USB-CDC host attached but not reading, each may wait up to the CDC TX timeout
      (`REST.T13`; verify at 1.29.0).

Seeds: cross-referenced from `XCUT.S01`, `SENS.S11`, `BUS.S02`, `BUS.S03`, `NET.S01`, `NET.S02`,
`NET.S07`, `NET.S11`, `LED.S01`, `REST.S08`, `WEB.S07`.

Quality measure: a budget table (value, derivation, measurement, guarding test).

---

### 5.22 PLAT — MicroPython/RP2040 platform facts

**Goal**: CLAUDE.md's standing practice run in full against 1.29.0 — every MicroPython-facing
construct checked for correctness *and* for a newer/better way (D.9), and every Part F fact re-verified
from source.

Topics:
- [ ] **PLAT.T01** asyncio semantics relied on: re-awaiting a finished/failed task, `Lock` FIFO order,
      `ThreadSafeFlag` from soft IRQs, `wait_for` cost, `Task.data`, cancellation delivery.
- [ ] **PLAT.T02** `const()` accepted types, `deque` features, `struct` truncation, `time.mktime`
      range/epoch, `random` seeding at boot, float32 behaviour.
- [ ] **PLAT.T03** rp2 port: soft-timer drop conditions, alarm-pool size, `machine.SPI.init()` cost,
      `UART.readinto` clamping, I2C/SPI `deinit()` no-ops, RX-overrun `EIO`, `mem_backup()` adoption
      (F.5.4), `reset_cause()`.
- [ ] **PLAT.T04** lwIP/modlwip: socket finalisers (PCB leak on GC), `tcp_write` retry blocking,
      `getaddrinfo` inside `asyncio.start_server`, UDP PCB pool.
- [ ] **PLAT.T05** Stub-package defects repaired by `typecheck.sh` — still present upstream?
- [ ] **PLAT.T06** Everything Part F.5 lists as "ruled out" — still ruled out.
- [ ] **PLAT.T07** Newer upstream (post-1.29.0) changes worth knowing before the next pin move (note
      only; the pin moves in its own session).
- [ ] **PLAT.T08** rp2 vs Unix-port number representation: small-int width, float boxing, mpz, float32
      libm accuracy (pico_float `pow`/`exp`/`log`/`atan`).
- [ ] **PLAT.T09** How mpy-cross freezes float literals and float `const()`s for a float32 target; does
      it fold float expressions in host double (`py/parse.c`, `MICROPY_COMP_CONST_FLOAT`)?
- [ ] **PLAT.T10** Boot chain: frozen `main.py` vs filesystem `boot.py`/`main.py` precedence
      (`shared/runtime/pyexec.c`); what runs after `main.py` returns or raises (REPL, soft timers); WDT
      across a soft reset and across `machine.bootloader()`.
- [ ] **PLAT.T11** `json`: `dumps()` of NaN/±inf, float32 round-trip through `dump`/`load`, how
      `dump()` writes to a littlefs stream.
- [ ] **PLAT.T12** `MICROPY_SCHEDULER_DEPTH` on rp2 and which sources share it; whether rp2 flash
      writes still disable IRQs / lock out core 1 at 1.29.0 and for how long; `ThreadSafeFlag`
      single-waiter rule.
- [ ] **PLAT.T13** Build-config diff: dump the effective `MICROPY_*` settings of the RPI_PICO_W build
      and of both Unix builds (`-dM -E`) and list every construct in `src/`, `ext/microdot.py` and the
      generated modules whose availability or behaviour differs (port-specific `select`/poll paths,
      error-reporting level, `MICROPY_CPYTHON_COMPAT`, unicode checks, `MICROPY_PY_TIME_TICKS_PERIOD` —
      the root of `XCUT.T25`; a scratch Unix build with `-DMICROPY_PY_TIME_TICKS_PERIOD='(1<<30)'` is
      the test-rig option).

Seeds: `CORE.S09` (task re-await), `BUS.S03` (SPI init), `BUS.S05` (UART readinto), `NET.S13` (socket
finaliser), `ALGO.S01` (int32 vs Python int).

- **PLAT.S01** (low) Seven comments say rp2's `mktime()`/`gmtime()` raise past a ~2037 32-bit epoch
  range (`system_service.py:144`, `asy_ntp_client.py:147, 408`, `asy_notification_service.py:184`,
  `asy_fram_manager.py:549, 613`, `asy_wifi_service.py:194`). At 1.29 on a 32-bit port `mp_timestamp_t`
  is `mp_uint_t` (`py/mpconfig.h:1060-1092`), so the range runs to 2106: `mktime()` never raises for
  in-range years and `gmtime()` only for negative inputs or inputs ≥ 2**32
  (`shared/timeutils/timeutils.h:75-92`, `py/objint_mpz.c:443-456`) — those `OverflowError` branches
  would never run on target.

Quality measure: each fact cited to a file:line in the pinned source; F.5 updated where it drifted.

---

### 5.23 PAR — Legacy parity and field migration

**Goal**: every deployed feature exists in the refactor or its removal/change is documented as
deliberate; the legacy → refactor reflash is understood and safe.
**References**: `python/`, `modules/sensortask-*.py`, `html_raw/`, `build-*.sh` (read-only); Parts A.4,
A.8, H.1, L.1; CLAUDE.md "same top-level features" agreement.

Topics:
- [ ] **PAR.T01** Full parity table: every legacy REST route/field/bound/default/behaviour → refactor
      location, "same" / "changed-documented" / "changed-undocumented" / "missing". ⟨pass 2, overtaken: OR48.a (1)(3): lost functions, no table or permanent record — G9: R02⟩
- [ ] **PAR.T02** Device mapping: legacy `arzi`/`neu`×3/`wozi`/`dev` → `devices/*.toml` pins and
      options.
- [ ] **PAR.T03** A.4 "confirmed intentional" behaviours still hold, one by one.
- [ ] **PAR.T04** Timing parity: supervisor period/reset delay, UI poll interval, LED sleeps, NTP
      retry.
- [ ] **PAR.T05** External REST consumers (scrapers, home automation) of the legacy routes — owner
      input. ⟨pass 2, answered: none: no legacy path stays (OR58.a) — G9: R06⟩
- [ ] **PAR.T06** Migration on reflash: stored `config.json` → per-module `.cfg` (never read), legacy
      FRAM contents under the new layout, littlefs region size across 1.26 → 1.29, hostname change and
      DHCP reservations, SCD30 NVM survival, first-boot hotspot → permanent-deactivation hazard. ⟨pass 2, answered: no migration, runbook (OR52.a (1)); FS erased (OR59.a (1)); 1.24.1 (OR61.a); FRAM need not survive (OR47.a (2)) — G9: R01 (HR209)⟩
- [ ] **PAR.T07** Whether a reflash runbook (or a first-boot migration/format step) is wanted (PQ10). ⟨pass 2, answered: runbook yes, first-boot migration no (OR52.a (1)) — G9: R01 (HR209)⟩
- [ ] **PAR.T08** Filesystem residue at reflash: what a legacy unit's littlefs holds (`config.json`,
      `boot.py`, `main.py`, `*.py`, `*.mpy`; dev snapshot at `dev_legacy/README.md:667`+) and whether
      any of it can run before, or shadow, the frozen refactor `main.py`/modules (`sys.path` order `''`
      vs `.frozen`; `pyexec` lookup in `ports/rp2/main.c` at 1.29.0) (with `PLAT.T10`, `XCUT.T20`). ⟨pass 2, answered: runbook erases the FS and `.frozen` first (OR59.a) — G9: HR050⟩
- [ ] **PAR.T09** Frozen-set and boot parity: legacy `python/Manifest/manifest.py` + frozen `_boot.py`
      vs the refactor's frozen set + `main.py`; mount/format behaviour on a filesystem the legacy build
      wrote (with `PAR.S10`, `TOOL.T06`).
- [ ] **PAR.T10** Web UI parity: every control, display and client-side bound in legacy
      `html_raw/{arzi,wozi,general}` mapped to the new UI or recorded as deliberately dropped
      (`PAR.S05`, `PAR.S07`, `WEB.S20`).
- [ ] **PAR.T11** HTTP behaviour across the Microdot jump (untagged ~2.0.x → v2.6.2) and 1.26 → 1.29:
      status codes for unknown routes/methods, error bodies, keep-alive, HEAD; legacy `api_helpers.py`
      codes 1-10 (e.g. 8 "LED busy", `REST.S09`) vs `api_response`'s catalogue. ⟨pass 2, overtaken: OR58.a: new API only reference, no compatibility; codes per R07 — G9: R06, R07⟩
- [ ] **PAR.T12** Published-value parity per sensor: from the same raw bytes, do legacy
      `python/IndividualDrivers/*` and `src/` publish the same numbers (scaling, rounding, offsets,
      filters, compensation, `None` on failure)? Desk comparison; running legacy code as an oracle needs
      the owner's permission (PQ10). ⟨pass 2, overtaken: OR48.a (1): value differences only as hints of a lost function; scratch runs allowed (PQ10) — G9: R02⟩
- [ ] **PAR.T13** Physical unit ↔ `devices/*.toml` mapping (L.1 names the three "ArZi neu" units);
      legacy `dev` recorded as not a parity target. ⟨pass 2, answered: owner holds every unit (OR61.a (2)); mapping in TOML headers; legacy dev no target — G9: R02⟩
- [ ] **PAR.T14** Rollback path: if a reflashed unit must go back to the legacy 1.26 build, what does legacy
      do with the refactor's state — leftover `config_<NAME>.cfg` and a missing/stale `config.json`, the
      refactor's FRAM layout read through legacy's chunk/timestamp/status logic
      (`python/IndividualDrivers/asy_fram_manager.py:50-110`) as SGP40 VOC state, SCD30 NVM values the
      refactor wrote, and can 1.26 mount a littlefs last written by 1.29? Feeds `PAR.T07`. ⟨pass 2, overtaken: no state survives either way (OR47.a (2), OR52.a (1)); rollback = owner's legacy reflash with fresh setup, in the runbook — G9: R01 (HR209)⟩
- [ ] **PAR.T15** Is the parity baseline right? `PAR.T01` assumes `python/`, `modules/`, `html_raw/` at HEAD
      are what each field unit runs; the legacy build exposes no version/build ID and this checkout is
      shallow. Establish which source state each unit runs (owner input, PQ10) before any row is scored
      "changed-undocumented". ⟨pass 2, answered: legacy HEAD baseline (OR48.a (4)); 1.24.1 (OR61.a); "shallow" stale — no `.git/shallow`, 1,691 commits — G9: R01⟩

Seeds:
- **PAR.S01** `WaitTimeNTP=0` disables the VOC restore entirely; legacy restored once, immediately; the
  web label "Never wait for NTP sync" implies the legacy meaning (`src/asy_sgp40_driver.py:53, 64, 356-359`).
- **PAR.S02** `[x2]` SCD30 PUT calls every setter unconditionally; legacy wrote only when the value
  differed from the readback (or forced `AmbPres`) — NVM wear and repeated `ForceCalRef` recalibration
  (`src/asy_scd30_driver.py:257-298` vs legacy `api_helpers.py:192`). ⟨pass 2, answered: compare-before-write (OR42.c); legacy compared only in intent (OR57.a) — G9: HR178, R36⟩
- **PAR.S03** SGP40 resets `voc_write = WaitTimeNTP` after every stamped write, so each later backup
  waits for NTP again; legacy set it to 0 for good (`asy_sgp40_driver.py:431-441`). ⟨pass 2, answered: owner's `improved-quality/` design (`8c4a73d`), kept; verified `asy_sgp40_driver.py:432, 439` — G9: R03⟩
- **PAR.S04** `[x2]` Supervisor: check period 3 s → 2 s (decay 1.5× faster), reset delay 5 s → 4 s,
  explicit `reboot_system()` instead of watchdog starvation; A.2 (SPECIFICATION.md:124-125) and I.4(d)
  (:5009-5010) still say "stops feeding the watchdog"; BACKLOG asks for the supervisor change "without
  changing observed behaviour".
- **PAR.S05** `/system`'s build info exists but no UI renders it (see `WEB.S20`). ⟨pass 2, answered: build info on its page or a listed Part H exception (OR43.a (2), V57) — G9: R05 (HR170)⟩
- **PAR.S06** Wire changes are documented as deliberate (six routes, sparse PUT, native bool/null,
  `BMP388` → `BMP3XX`, oversampling as values not indices, `Led` prefix dropped) — but old bookmarks
  (`/sensorconfig.html` etc.) now 404; confirm acceptable. ⟨pass 2, answered: old bookmarks 404 accepted (OR58.a) — G9: R06⟩
- **PAR.S07** UI measurement poll 2 s → 3 s (definitions `landingSection` poll 3000 ms).
- **PAR.S08** Config migration: nothing in `src/`/`buildgen/` reads `config.json`; after reflash every
  unit boots with SSID `""` → hotspot; if nobody joins within the hotspot window, the second streak
  permanently deactivates WLAN until a power cycle. BACKLOG #2's "avoids this structurally" covers
  key-adding updates, not this transition. ⟨pass 2, answered: runbook covers the first-boot hotspot hazard (OR52.a (1)) — G9: HR209⟩
- **PAR.S09** Legacy FRAM chunk 0 (SGP40 VOC state, no CRC, 248 B) sits where the refactor's first
  chunk now lives; expect CRC/status errors on first boot that seed misleading errcount entries (see
  CLAUDE.md's FRAM-evidence rule); VOC baseline lost (45-sample relearn). ⟨pass 2, answered: foreign bytes read as empty, no crash, no flood (OR47.a (2), OR35); VOC relearn accepted — G9: HR156⟩
- **PAR.S10** The littlefs region must survive a 1.26 → 1.29 swap (`MICROPY_HW_FLASH_STORAGE_BYTES`
  equal on both; B.14.3) — unverified. ⟨pass 2, overtaken: FS erased at reflash (OR59.a (1)); source is 1.24.1 (OR61.a) — G9: HR209⟩
- **PAR.S11** Hostname changes from `"SensorNode"`/user-set to `SensorStation<Name>` (DHCP
  reservations, DNS names, hotspot SSID). ⟨pass 2, answered: runbook item (OR52.a (1)) — G9: HR209⟩
- **PAR.S12** Legacy reboot-looped forever on a failed `fram.setup()` (WDT starved); the generated
  `build_system()` ignores `setup()` results — an undocumented, probably-better change (legacy
  `modules/sensortask-wozi.py:570-573, 604-606`).
- **PAR.S13** CLAUDE.md says the refactored wozi is "never physically flashed"; if the fielded wozi
  unit is ever reflashed, its first real flash is a production one — owner confirmation. ⟨pass 2, answered: wozi TOML never flashed (A05); reflashing the physical unit is the owner's operation (OR61.a (2)) — G9: R02⟩
- **PAR.S14** Legacy `modules/sensortask-dev.py:21` carries SHTC3/MPRLS/ISL keys while
  `devices/dev.toml` wires SCD30/SGP40/BMP3xx/ISL29125 — not a parity target (CLAUDE.md: `dev` is a
  bench rig). ⟨pass 2, answered: not a parity target; dev held to every device's bar (OR72.a (10)) — G9: R02⟩
- **PAR.S15** Legacy served `/favicon.ico` (`modules/sensortask-wozi.py:121`,
  `html_raw/general/favicon.ico`); the refactor suppresses it in HTML (`html/index.html:7` `data:,`) —
  check no browser still requests `/favicon.ico` against the 6-connection ceiling (404, or 302 in
  hotspot) (with `PERF.T02`).

Quality measure: complete parity table; each "changed-undocumented" row decided by the owner.

---

### 5.24 DOC — Documentation set

**Goal**: the docs hold current state, rules and targets only; every fact has one home; every
cross-reference resolves; the auto-loaded CLAUDE.md stays a rule set, not a reference manual.
**References**: CLAUDE.md "Working agreements"; README "Further reading".

Topics:
- [ ] **DOC.T01** Structural hygiene of `SPECIFICATION.md`: misplaced sections, heading levels,
      unnumbered subsections, a section-level table of contents.
- [ ] **DOC.T02** Cross-reference integrity: `Part X.Y` (all resolve today), BACKLOG numbers, real-hardware
      row IDs, archive `§`, named sections — and whether a CI lint should keep it that way. ⟨pass 2, answered: yes: a `tests_scripts` check fails on citations to missing files, headings, numbered decisions (OR68.a (4)) — G9: R12⟩
- [ ] **DOC.T03** Reference policy: permanent code citing temporary docs' row IDs (they dangle once
      rows are deleted); ID namespaces that collide visually (`F1` row vs `F.1` Part). ⟨pass 2, answered: nothing permanent cites a temporary plan or row by section or number (OR68.a (4)) — G9: R12, R27⟩
- [ ] **DOC.T04** Archive durability: `12640c2` reachability after merge (PQ2). ⟨pass 2, answered: merge commit keeps `12640c2` an ancestor (PQ2, OR52.a (4)) — G9: R12⟩
- [ ] **DOC.T05** History/narrative vs the current-state rule (tests_hardware README pass sections,
      README provenance paragraphs, CLAUDE.md incident bullets, BACKLOG item narratives, dated stamps).
- [ ] **DOC.T06** One home per fact: duplicated facts across CLAUDE.md/SPEC/BACKLOG/`tests_hardware/
      README.md`; open work scattered over several places (fewer since the queue and handover were folded
      into BACKLOG, `03f8bcf`).
- [ ] **DOC.T07** CLAUDE.md budget (~92 KB auto-loaded): rules vs facts vs narrative; relocation of the
      chroot recipe and "Known … fixed" bullets to SPEC with pointers (PQ6). ⟨pass 2, answered: PQ6 (b): rules with one short reason stay; facts, incidents, the chroot recipe move; no numeric size target — G9: R13⟩
- [ ] **DOC.T08** Every dated count/number claim (86/86, ~157, 21 chunks, suite counts) — keep, make
      generated, or make tested. ⟨pass 2, answered: OR27.a: a number stays only as evidence of a rule or limit, dated and sourced — G9: R11⟩
- [ ] **DOC.T09** Glossary for undefined labels (WP1-WP8, measure A/B, image E6′, S3, sittings). ⟨pass 2, overtaken: labels replaced by content plus actor tag (OR68.a (4)), no glossary — G9: R12, R27⟩
- [ ] **DOC.T10** Contradiction sweep (seeds below) and terminology drift.
- [ ] **DOC.T11** `DEVICE_REFERENCE.md`: which firmware does it document — the fielded legacy build or
      the refactor after reflash? Check it against that firmware (`LED.S04`, `DOC.S19`). ⟨pass 2, answered: the refactor after reflash (OR58.a, OR52.a (1)); C06 "never will" out — G9: R13, R06⟩
- [ ] **DOC.T12** Markdown mechanics: relative `[text](path)` links, in-file anchors, table integrity —
      a machine check next to `DOC.T02`'s ID resolver.
- [ ] **DOC.T13** README's first screen describes only the legacy builds (device table, "5 units
      deployed", `html_raw`, `BMP388`); bring the six `devices/*.toml` and the neu →
      klkizi/grkizi/schlafzi mapping (L.1) onto it.
- [ ] **DOC.T14** Do-not-reopen index: one list of every SETTLED/owner-decision marker in docs and code
      comments, every CLAUDE.md never/don't/deliberately rule (e.g. the `uv sync` retry,
      `self-repository` disabled, E402 noqa split, inline `method-assign` ignores, stub repairs not
      `type: ignore`, `-X heapsize` never the fix, the "don't re-diagnose" hang/segfault causes) and
      every BACKLOG "deliberately left"/"confirmed intentional" entry — the input 2.3's "settled — no
      action" triage needs; built in ENV (`ENV.T07`), kept current by DOC. ⟨pass 2, overtaken: DECISION_PROVENANCE's 263 classified decisions are the index; texts carry actor tags, foreclosures removed per the answers — G9: R27, R35-R38⟩
- [ ] **DOC.T15** Routing rule: contradictions between two doc statements (same or different file)
      belong to DOC; doc-vs-code or comment-vs-code drift found by an area stays with that area under
      L-DOC (e.g. `HW.S17`, `HW.S20`, `TWIN.S06`, `CI.S08`, `SCR.S03`, `REST.S11`, `NET.S18`, `GEN.S14`,
      `CORE.S15`, `WEB.S14`, `WEB.S18`).
- [ ] **DOC.T16** Code-identifier resolver next to `DOC.T02`'s ID resolver: every backticked function,
      class, constant, `path/file`, REST route and CLI flag in the docs and in pointer comments resolves at
      HEAD (upstream C symbols against the ENV.T03 corpus); ~495 distinct `name()` citations in the five
      main docs, ~42 unresolved in-repo (mostly upstream C names).

Seeds:
- **DOC.S01** `## I.6` sits inside Part J (SPECIFICATION.md:5178); `## E.2.1` (:2804) and `## H.5.1`
  (:4422) should be `###`; H.7 has two unnumbered subsections (:4542 connection ceiling — cited as "H.7"
  for lwIP facts — and :4676 cross-browser).
- **DOC.S02** F.5 is titled "MicroPython 1.29 delta" but F.5.7-F.5.9 are standing UART runtime facts
  CLAUDE.md's hard rules depend on; a future version audit replacing F.5 would orphan them.
- **DOC.S03** Contradiction on website definitions: H.5 (:4401) and `build_website.sh` say wozi/dev are
  hand-written; K.4 (:5781) says "never hand-maintained"; K.8 (:5895) "regenerates automatically"; C.11
  point 9 (:2331) says hand-update. ⟨pass 2, answered: OR43.a (3): hand-written definitions retire; `@web` tags only — G9: R18, R13⟩
- **DOC.S04** ~77 "archive §" citations resolve only against commit `12640c2`, reachable today only
  from this branch (PQ2). ⟨pass 2, answered: merge commit (PQ2) — G9: R12⟩
- **DOC.S05** Dangling named citations in code: `tests/machine.py:2`, `tests/test_captive_dns.py:230`,
  `src/asy_notification_service.py:3, 69`, `src/asy_neopixel_driver.py:3`,
  `tests/test_asy_wifi_service.py:1791`, `scripts/_strip_type_checking.py:13`,
  `tests_scripts/test_strip_type_checking.py:51`, `scripts/lint.sh:17`,
  `tests_hardware/bench/test_network_resilience.py:3`,
  `tests_hardware/flash/test_toolchain_flash_boot.py:14, 25, 46`,
  `tests_hardware/bench/test_heap_under_connection_ceiling.py:161`,
  `tests/test_asy_webserver_service.py:194` (F.6/F.7 from a retired audit, colliding with Part F),
  `tests_hardware/flash/test_bus_concurrency.py:122` (quotes item 8 as unsettled).
- **DOC.S06** Retired queue rows still cited as "queue <ID>" in code, after the queue itself is gone
  (`03f8bcf`): F10/F11 (`tests_hardware/http_client.py:48`, `tests_scripts/test_http_client_ceiling_close.py:19`),
  F7 (`device_scripts/uart_link_under_concurrent_system_load.py:109`), F10
  (`bench/test_network_resilience.py:877`), F13 (`bench/test_wifi_networking.py:32`), G9
  (`website_identity.py:2`, `bench/test_rest_endpoints_over_sta.py:35`), F1
  (`device_scripts/wifi_service_reconnect_repro.py:14, 34`), R2 (BACKLOG.md:264). Resolved at `4dc80ef`: C7
  and R10 (BACKLOG), and SPECIFICATION.md:5296's F11 now points at the archive (`DOC.S26`). The
  `tests/` hits `# F7`/`R9, R10` (`test_asy_isl29125_driver.py:404, 1314`, `test_asy_uart_comm.py:1264`)
  are a different namespace (requirement/feature numbers) that collides visually (`DOC.T03`).
- **DOC.S07** Dangling doc pointers: README.md:652-653 and 783-784 point at SPECIFICATION front matter
  that has no such text; CLAUDE.md:647 ("`_timer_sequencer()` fix above") points at nothing and :893-894
  points at "Platform target" (`CLAUDE.md:15`), which no longer carries the `universe` fact;
  BACKLOG.md:877 names a nonexistent README section.
- **DOC.S08** Stale: "86/86" (CLAUDE.md:350) and "85"
  (SPECIFICATION.md:2926, also 3071-3072, 5033) vs 87 test files; CLAUDE.md:773 "~157" method-assign sites vs 209;
  CLAUDE.md:725 names a split test file; A.6 datasheet list omits isl29125; B.9 (821-826) says
  `build-*.sh` still hardcode paths and firmware build is uncovered; C.11 "only"/"three" (2322, 2326)
  and C.4.1 "three drivers" (1630); L.6.4 "only `_LIMITS` driver" (isl29125:194 has one too);
  README.md:767-769 item 8 status; "pre-push verification" wording (SPECIFICATION.md:6-7,
  README.md:650).
- **DOC.S09** `[x3]` A.7 (SPECIFICATION.md:462, 491) states setup order `sysfunct → fram → …`; the
  generator emits `fram → sysfunct → …` (`buildgen/codegen.py:441-449`); A.2 supervisor text stale
  (`PAR.S04`); C.6 (:1802, :5666) describes a `repr()`-parsing `make_dict()` "landmine" the code no
  longer has; C.5.3 cites a nonexistent `_cfg_subset()` and `/net/cmd`/`/led/cmd`.
- **DOC.S10** Conflicting migration targets for resolved BACKLOG items (BACKLOG.md:5-7,
  README.md:656-657, CLAUDE.md:406-410 say CLAUDE/README; practice is mostly SPECIFICATION).
- **DOC.S11** Coverage gating stated both ways in README (192 "never fails the build" vs 176-178);
  CLAUDE.md chroot recipe contradicts itself (1026-1028 vs 968-971) and duplicates the libcap2-bin
  paragraph (936-953).
- **DOC.S12** CLAUDE.md:367-376's FRAM-log list omits ISL29125 (dev wires it to FRAM); SPEC cites
  "CLAUDE.md's implicit-FRAM-wiring rule" (376, 396) that CLAUDE.md never states as a rule.
- **DOC.S13** BACKLOG hygiene: stub list (15-18) omits item 29; items 2 and 4 are decided and uncited;
  a SETTLED entry filed under "not yet done" (72); several items carry "earlier version said" narrative.
- **DOC.S14** `UART_C_PORT_CHANGELOG.md` is "temporary until reconciled", but reconciliation is out of
  scope (owner) — no reachable deletion trigger; reclassify? (touches the owner's 2026-09-24 arrangement
  — triage "settled — no action" unless the premise is wrong, 2.3) ⟨pass 2, answered: changelog stays until the post-audit C reconciliation (OR5.a (1)(3), OR11.a) — G9: R24⟩
- **DOC.S15** `update_and_install.txt` is missing from README's "single complete map";
  `dev_legacy/README.md`'s "single source of truth" status vs BACKLOG.md's board-state entry
  (BACKLOG.md:353-361; OR32.a moves the bench content to its canonical homes). The queue/handover
  duplication of board state and running order ended with the fold (`03f8bcf`).
- **DOC.S16** Undefined labels: WP1-WP8 (36 files at baseline); "measure A/B", "image E6′", "S3" defined
  only in the git archive; "S3" (a bench sitting) also collides with the S-row IDs (S3b, S4) that
  BACKLOG's real-hardware section keeps (`DOC.T03`).
- **DOC.S17** Dated counts likely drifted: CLAUDE.md:821-840's per-file `call-overload` counts;
  BACKLOG's explicit-`Any` counts (2026-09-11); SPECIFICATION.md:3677-3680 suite counts (the queue's
  own counts went with it).
- **DOC.S18** `README.md:278-280` and `scripts/build_website.sh:11` say `<device>` must match an
  `html/definitions/<device>.json` ("wozi and dev today"); `build_firmware.py:60, 113` requires
  `devices/<device>.toml`, `build_website.sh:26-31` generates the other four, CI builds all six.
- **DOC.S19** `DEVICE_REFERENCE.md:3-4` addresses "a deployed unit" but documents refactor field names
  (`FlashBri` :17-18, `BackupPeriod` :31); fielded units use `LedAutoFlashBri`, `SGPBackupPeriod`
  (`modules/sensortask-wozi.py:21`). ⟨pass 2, answered: refactor field names are right (OR58.a); address a reflashed unit — G9: R13, R06⟩
- **DOC.S20** More sites of `PAR.S04`'s watchdog claim: BACKLOG.md:334-335 ("the only feed site") vs
  the per-setup-unit feed at `buildgen/codegen.py:465`.
- **DOC.S21** `build-*.sh` status told three ways: BACKLOG.md:877-878 "now fixed too"; B.9
  (SPECIFICATION.md:825-830) and A.3 (:133-134) "not covered"; CLAUDE.md "never gets work" — resolve
  toward CLAUDE.md's reference-only rule, never toward "covered". ⟨pass 2, answered: reference-only wins (V04, OR32); no "covered" framing — G9: R01⟩
- **DOC.S22** SPECIFICATION.md cites symbols that don't exist: `_send_opcode()` (~1545; `src/asy_fram_driver.py`
  has `_send_command()`/`_send_and_read()`/`_send_and_write()`) and K.5's `_build_spi_chip()` (~5800; the
  twin has `_wire_spi_device()`, `digital_twin/machine.py:326`, FRAM only, no `driver` dispatch).
- **DOC.S23** F.1 (SPECIFICATION.md:3526-3527) says every real `ticks_diff()` use in `src/` is a short
  bounded timeout; `XCUT.T25`'s stored-ticks sites contradict it; `tests/test_ticks_rollover.py:1-2`
  repeats the claim (`TEST.S25`).
- **DOC.S24** G3's closure (`79423dd`: `flash/test_watchdog_starvation.py:54-78` proves `_reboot()`'s
  alarm-pool fallback on silicon, 3/3) reached neither BACKLOG.md:89-90, which still names that test as
  an open follow-on, nor `tests_hardware/README.md:1280-1286`, which still calls the fallback mock-only.
- **DOC.S25** SPECIFICATION.md:6056-6059 says the `Hostname` default was "wrote it back once"; the commit
  that measured it says "two flash writes, not one" (`6f7eef7`, N2). Reconcile the count (L-WEAR: each is a
  flash write on every boot that lacks the key).
- **DOC.S26** SPECIFICATION.md:5296-5297 now sends F11's account to `HEAP_FRAGMENTATION_MEASUREMENTS.md`
  archive §7I-§7K, which exists only at `12640c2` (`DOC.S04`); confirm those sections hold it (the fold
  commit only repointed the reference).
- **DOC.S27** BACKLOG.md:389-449 keeps A6's FRAM timing script as "its only copy" inside a markdown code
  block: unlinted, untyped, never collected, outside the comment cap and every CI gate. T4's owner
  decision settles it — commit it as a device script under the normal gates, or drop it with the row. ⟨pass 2, answered: T4 settled (OR72.a (2)): row leaves; A6's script kept only on an OR33.a keep verdict (as a gated device script), else dropped — G9: R31, R34⟩
- **DOC.S28** BACKLOG's "Real-hardware work still owed" mixes three kinds: silicon work (M1 + S3b, R13 +
  N3, the two unconfirmed fixes), owner decisions that need no board (F18, T4, W3, T1, the device-script
  loose ends at :720-727) and pointers (:464-469). Under OR5.a the decisions need answers, not a sitting;
  file each where it belongs (`HW.T10`). ⟨pass 2, answered: F18/T4/W3/T1 answered (OR72.a (1)-(4)), loose ends deleted (V54); list keeps silicon work only — G9: R31, R36⟩
- **DOC.S29** One trap of the retired queue's §6 was not carried over: "a REST reboot issued by hand
  strands the DUT in hotspot mode" — kick the AP's stations, then `hard_reset()` (~40 s)
  (`git show 2a88cc8:REAL_HARDWARE_TEST_QUEUE.md`, lines 376-383). Nearest homes: `tests_hardware/README.md:394-395`
  (fallback after a reset or flash) and BACKLOG.md:462-464 (kick-then-reset helper); OR14's "lost"
  outcome unless one of them is judged to carry it.

Quality measure: cross-reference resolver clean for every ID family; contradiction list empty or
decided; CLAUDE.md size target agreed (PQ6) and met.

---

### 5.25 LIC — Licensing and attribution

**Goal**: every vendored or derived file carries correct attribution and `THIRD_PARTY_LICENSES.md` is
complete and accurate for what ships and what is stored in the repo.

Topics:
- [ ] **LIC.T01** Every Adafruit/DFRobot/Sensirion-derived file's header attribution vs
      `THIRD_PARTY_LICENSES.md` (F.4 allows rewriting, keeping attribution).
- [ ] **LIC.T02** Vendored `ext/` licences present and matching upstream tags.
- [ ] **LIC.T03** The captive_dns/NTP/UDP provenance entries (`src/LICENSE-captive_dns`): the licence
      doc now names a source for each — are README and the headers consistent with it (`LIC.S06`)?
- [ ] **LIC.T04** (touches SETTLED — route to the owner under PQ6, don't act) Scope statement only
      (BACKLOG SETTLED: `arduino/` incl. its licensing is out of scope): one sentence in
      `THIRD_PARTY_LICENSES.md` and README saying `arduino/` is excluded by owner decision — no audit of
      its contents. ⟨pass 2, answered: state it, "post-audit only" (OR5.a (3), V01) — G9: R21⟩
- [ ] **LIC.T05** What actually ships in the firmware image (frozen set) vs what the licence doc lists.
- [ ] **LIC.T06** What the UF2 contains beyond this repo: MicroPython (MIT), pico-sdk and lwIP (BSD-3),
      mbedTLS (Apache-2.0), cyw43-driver (its own licence), freezefs runtime if frozen — any notice
      duty? Only relevant if a UF2 leaves the owner's hands (distribution scope, PQ10). ⟨pass 2, answered: in scope: public MIT repo (OR52.a (7)); none published today — G9: R23⟩
- [ ] **LIC.T07** `datasheets/` holds vendor-copyrighted PDFs — do their redistribution terms fit the
      repo's visibility (PQ10)? ⟨pass 2, answered: in scope (OR52.a (7), OR53 (2)); checked in pass 2 → Q1 — G9: R23⟩
- [ ] **LIC.T08** Headers vs doc in both directions: every SPDX/attribution header in `src/` has a doc
      entry and vice versa, with matching scope (whole file vs portion).

Seeds:
- **LIC.S01** Two separate `src/asy_isl29125_driver.py` entries (THIRD_PARTY_LICENSES.md:34-39, 46-53);
  l.37 says the legacy copy is listed "below" while l.118-120 says the entry "moved up".
- **LIC.S02** THIRD_PARTY_LICENSES.md:52-53 credits "FRAM-persisted gain-ratio self-calibration"; M.1.5
  and the driver say calibration is RAM-only and user-applied.
- **LIC.S03** (touches SETTLED, see `LIC.T04`) README.md:719-724 calls the doc "every piece of vendored
  … third-party code in one place" without the `arduino/` exclusion sentence (`LIC.T04`). ⟨pass 2, dup: LIC.T04 — G9: R21⟩
- **LIC.S04** `src/captive_dns.py:1-2` declares a file-level `Apache-2.0` SPDX header while the doc
  (`THIRD_PARTY_LICENSES.md:5-7, 128`) scopes Apache-2.0 to `DNSQuery` (`:157`) only; the file also
  holds project-own `DNSServer` (`:56`) and `_ipv4_to_int` (`:41`).
- **LIC.S05** `THIRD_PARTY_LICENSES.md:203-205` says karfas attribution was "added to both files";
  `src/asy_ntp_client.py:1-3` names only micropython-lib, only `asy_udp_socket.py:1-3` names karfas.
- **LIC.S06** `README.md:721-723` still calls captive_dns/NTP/UDP the area whose "source couldn't be
  established", while the licence doc now names a source for each (:62-75, :123-155, :175-205).
- **LIC.S07** `THIRD_PARTY_LICENSES.md:3-7` says "MIT overall with that one documented exception" but
  also records a BSD-3 provenance (:93-105) and a reuse with no formal licence (:175-205).

Quality measure: per-file attribution table; doc accurate for the shipped image.

---

## 6. Plan validation (planning phase — this is the only work allowed before go-ahead)

Each step is its own dedicated pass; none is marked done by another's side effects (lesson from the
retired `AUDIT_PLAN.md`). Status as of this revision:

- [x] **V1 Inventory coverage and uniqueness**: every git-tracked file maps to exactly one owning area
      in 5.0 or to the 2.2 list (`audit/sweeps/validate_plan.py`, whose `owner_of.py` encodes 5.0: no file
      unowned, none double-owned). Re-run after any new file lands.
- [x] **V2 Completeness review by fresh eyes**: three rounds. Round 2 found the tooling/tests/docs half
      saturated and added two risk classes on the code side (stored ticks values, `XCUT.T25`; failure
      before the watchdog exists, `XCUT.S14`). Round 3, limited to those two classes, found the
      stored-ticks sites saturated (no new site) and added delta/upper-bound and scheduler-order seeds
      (`XCUT.S15`, `UART.S08`, `GEN.S18`), a test blind spot (`TEST.S25`), three pre-watchdog paths
      (`XCUT.S16`-`XCUT.S18`) and `PLAT.S01`; `XCUT.T25`/`XCUT.T20` rewritten. Closed without a round 4.
- [x] **V3 Reference reality check**: every seed anchor was checked against the code it describes, and a
      script (`validate_plan.py`) confirms every `path:line` reference — continuation `:N` refs included,
      ~1,130 in all — lies within its file at the planning baseline, `4dc80ef` since V11 (bare
      `asy_*.py`-style names resolve to `src/`). The first script checked range starts only (round 3
      caught `build_frozen_html.sh:36-37` in a 36-line file); range ends are checked since. Bounds only:
      an in-bounds wrong anchor passes (`ENV.T10`). Re-run after each revision.
- [x] **V4 Internal consistency**: every `<AREA>.[ST]nn` ID referenced in this file is defined exactly
      once and every PQ reference is PQ1-PQ10 (`validate_plan.py`). Harvest IDs (`<AREA>.Nnnn`) are
      defined in `audit/harvest/` and numbered by its generator.
- [x] **V5 Backward read**: done once; its contradictions (ownership, cross-references pointing at the
      wrong topic, facts stated two ways, SEV1 defined twice, pilot vs wave order, stale R2 status) are
      fixed in this revision.
- [x] **V7 CLAUDE.md conformance of the plan itself**: two reads; findings folded into 2.2, 2.3, 3, 4.1,
      4.3, 4.4, 4.5, 4.7 and the affected topics (per-conversation hardware gate quoted, merge and
      `uv.lock` rules, FRAM outside the wear gate, the protected `uv sync` retry, the do-not-reopen index
      widened to every CLAUDE.md "never/don't/deliberately" rule, boot cost not a defect, no GPIO
      fault-injection hardware, mutation bounded by the wear rule, documentation checked besides source,
      settled items tagged "touches SETTLED").
- [x] **V8 Dry run**: a fresh agent walked the resume procedure from git alone and drafted a register
      header plus entries for `REST.S01` and `CORE.S02`. Verdict: rich content, under-specified mechanics
      (~20 gaps). Folded in: 3.1 owner record, PQ2 (branch, `audit/`, commit authority), 4.1 unit table
      and pass/converged/closed definitions, 4.4 auditor packet and blindness, the port/toolchain facts
      (ports are fixed in code; `build_firmware.py` writes inside the toolchain dir), 4.5 rewritten
      (fields, intake-time IDs, status transitions), 4.6 per-session vs once topics, 4.7 numbered resume
      procedure with the lease steps, planning residue kept under `audit/`. Re-run once the register
      exists.
- [x] **V10 Harvest of what the project already records**: every comment and docstring, every doc, the
      git history and the GitHub PR/issue discussions, read by 17 partitioned read-only agents for
      self-declared limitations, accepted risks, settled decisions, assumptions, workarounds, unenforced
      invariants, mirror obligations, suppressions, open questions and drift — recorded, not solved
      (owner, 3.1). About 6,500 items in `audit/HARVEST.md` (index, method, untracked deferred work) and
      `audit/harvest/<AREA>.md`, each cross-referenced to the plan's topics/seeds by its agent and its
      quote checked against the snapshot by script. Not yet done: folding the items new to the plan into
      topics/seeds (owner's call on how, after reviewing them). Moved to `4dc80ef` and extended by V11.
- [x] **V11 Baseline move to `main`'s head** (owner, 3.1 and OR33; 2026-09-25): the planning baseline moved
      from `0615eba` (plan) and `2a88cc8` (harvest) to `4dc80ef`, `main` after PR #58 — 16 commits, 16 files
      (`git log 2a88cc8..4dc80ef`). Method, all scripts in `audit/sweeps/`: `reanchor.py` shifted every
      `path:line` anchor by the git diff (39 plan lines, ~1,290 harvest lines); `harvest_check.py`
      re-checked every harvest quote at the new baseline (at `4dc80ef`, delta included: ok 5,759, not a
      file 440, quote not found 119, no quote 49, out of bounds 13, file gone 92 — against 5,844 ok at
      `2a88cc8`); `baseline_fates.py` tagged the 124 items whose source left the tree — 111 citing the
      deleted queue/handover, 13 others whose quoted text was reworded or removed — with `⟨4dc80ef: what
      became of it⟩` (the row's fate from the commits, or where its content lives now); a delta harvest
      (`[D1]`, 24 items) recorded what the 16 files now say. The plan
      absorbed the fold (queue and handover → BACKLOG, `03f8bcf`), the closed rows (Appendix B), new seeds
      (`SENS.S28`, `HW.S26`-`HW.S28`, `DOC.S24`-`DOC.S29`) and topics (`HW.T20`, `TEST.T20`). Repeat the
      same steps whenever the baseline moves again (`ENV.T08`).
- [x] **V9** Owner questions: PQ1-PQ10 (answered 2026-09-26); later rounds in the owner's format
      (OR51.a (3)), recorded in 3.2.
- [x] **V12 Consolidation passes 1-2** (2026-09-26): the owner requirements read against each other, the
      plan and CLAUDE.md, then worked into sections 1, 2 and 4 (`audit/CONSOLIDATION.md`); harvest pass 1
      and the decision-provenance sweep followed (answers OR54-OR73).
- [x] **V13 Allover pass 2** (2026-09-27): ten agents re-read every requirement source with everything
      known from the start; the lead resolved cross-group points and adopted gaps. Result: the register
      (`audit/pass2/`, 518 live requirements), `audit/CONSOLIDATION.md` rewritten, sections 0-4 and 6
      updated, 141 topics and seeds annotated. `audit/sweeps/pass2_check.py`: every candidate, cluster,
      topic, seed, provenance decision and owner row placed; four adversarial verifiers found 68
      defects, applied (`audit/pass2/verify/`). Passes 3+ (question-raising scans, OR52.a (5)) follow.
- [ ] **V6 Owner review** (last): PQ1-PQ10 answered (done); consolidation complete (OR2.b); the owner
      declares the list complete and gives the execution go-ahead explicitly.

---

## Appendix A — System snapshot (planning baseline `4dc80ef`, for orientation)

- **Product**: MicroPython 1.29.0 firmware (frozen bytecode) for Raspberry Pi Pico W (RP2040) room
  air-quality units. 6 device variants from `devices/*.toml` (`wozi`, `dev`, `arzi`, `klkizi`, `grkizi`,
  `schlafzi`); field units still run the legacy 1.26 tree (`arzi`, `wozi`, 3× `neu`). Only `dev` is ever
  flashed/bench-tested; `wozi` is the exemplar validated by mock/twin tiers.
- **Runtime**: one asyncio loop; soft `machine.Timer`s set flags; a supervisor restarts dead tasks with
  a decaying score and reboots past a threshold; `WDT(8000)` fed by setup batch and supervisor.
- **Layers**: bus wrappers (`asy_i2c/spi/uart_driver`) → protocol classes → `*_Reader`
  (`SensorReader`/`SensorReaderConfig`) with per-module `ConfigManager` JSON files on littlefs and
  `PrintLogHistory(Store)` error rings, FRAM-backed via a dual-copy chunk allocator.
- **Sensors**: SCD30 (CO2/T/RH, NVM settings), SGP40 (VOC index, FRAM-backed algorithm state), BMP3xx
  (pressure), ISL29125 (RGB/lux, dev only); NeoPixel notifications; UART protocol pair (dev only).
- **Network**: STA with hotspot/captive-portal fallback and permanent deactivation after a second
  failure streak; NTP with EU DST; own non-blocking DNS; Microdot v2.6.2 REST (6 GET routes, PUTs,
  static gzip site), `max_connections` 6, 2048 B body cap, 15 s outer cap; lwIP options pinned via a
  build override.
- **Build**: `buildgen` turns a device TOML + AST-read `src/` tags into `sensortask_<device>.py`, a
  boot entry and `definitions.json`; `build_firmware.py` stages, strips `TYPE_CHECKING`, freezes the
  website (`build_website.sh` → freezefs) and builds the UF2 with a from-source toolchain
  (`toolchain/`).
- **Verification tiers**: `tests/` (87 files, mock and twin-integration, 3,198 static `def test_` plus
  scenario-generated ones, under the real Unix-port interpreter), digital twin (chip fakes + fake
  `machine`/`network`, CI suite of 14+ runs per device), host pytest (`tests_scripts/`, 58 test files +
  helpers), web (Vitest browser mode, cross-browser smoke), real hardware (flash 53, bench 85, soak 4,
  manual; owner go-ahead only).
- **Docs**: ~1.1 MB; SPECIFICATION.md (Parts A-M) is the central spec; CLAUDE.md the auto-loaded rule
  set; BACKLOG.md working memory, its "Real-hardware work still owed" the list of bench work.

---

## Appendix B — Remaining work at `4dc80ef`: necessity pre-assessment (OR33)

The planner's first view, **unverified** like every seed: one line per open BACKLOG item, owed
real-hardware entry and investigation-born test or script, with where the plan covers it and a proposed
verdict — **keep** (standing value named), **retire** (investigation closed, nothing left to prove, or a
lower tier proves the same — a candidate only: OR33.a first traces the intent and adopts it in a form that
bites; only what stays unreasonable is dropped), **do** (the audit resolves it), or **owner** (a decision only the owner can
take; collected for the consolidation run, OR2.a). `HW.T20`/`TEST.T20` turn each into a register verdict.

**B.1 Real-hardware work still owed (BACKLOG.md:345-470)**

| Entry | Plan | Proposed | Why |
|---|---|---|---|
| D1-D3 standing answers, board state (:352-360) | `HW.T10` | keep | Sitting rules; the board-state line goes stale at every sitting (`DOC.S15`) |
| SGP40 `W13` unconfirmed on silicon (:361-364) | `HW.S28`, `SENS.S28` | owner: retire or ride | Pure logging logic, four unit tests that each failed against a mutation (`83c9920`); the silicon check needs NTP blocked ~30 min. Ride the hardware phase only if a run blocks NTP anyway |
| Flash tier's closing `hard_reset()` (:364-366) | `HW.S28` | retire as an entry | Confirmed by the next full flash-tier run, which the hardware phase does anyway; nothing separate to schedule |
| M1 + S3b, ISL29125 light programs (:367-372) | `SENS`, `HW.T15` | keep S3b; owner on M1 | S3b is automated (~10 min, rig in place) and the only silicon run of `Overrange` (R9's other half); M1 is interactive and only needed once for the rig geometry S3b depends on. ISL29125 exists on `dev` only |
| R13 + N3, UART `wrnno` 11 vs a babbling peer (:373-379) | `UART.T06` | retire → known limitation | Needs peer hardware the bench does not have and none will be bought (owner, 2026-09-25; item 8's precedent); the mock tier covers the logic. N3's changelog half is already done (`UART_C_PORT_CHANGELOG.md:103`, B32) |
| F18, zero-think-time readers saturate the board (:380-387) | `PERF.T02`, `REST` | owner | A contract decision (are hammering clients in scope? admission fairness?), not bench work (`DOC.S28`) |
| T4, FRAM per-command hold, A6's script (:388-448) | `STOR`, `PERF.T04`, `DOC.S27` | owner | Yield between CS commands or not; commit or drop the script held only in BACKLOG |
| W3, +17 % `/status` at 256 B pieces (:449-452) | `PERF.T02`, `REST` | owner | Accept as the price of I.3's bound or not; measured like for like, nothing more to run |
| T1, in-suite placement figure (:453-460) | `MEM` | owner: close; do the echo | 84,112 B is recorded; the comparison figure is gone from the tree. Small test fix: echo `GC_THRESHOLD=` |
| Kick-then-reset helper (:461-463) | `HW.T12` | do | One harness helper removes a recurring hotspot-fallback trap (`DOC.S29`) |
| R2 → items 24/32 (:464) | `PERF.T03` | owner, then do | A real product limit under load: the design fix (batched or concurrent reset) and the bench budget |
| S4, 6 h soak (:465; :777-811) | `HW.S14` | keep | Never run; release evidence on silicon for leak and reboot freedom, zero wear |
| G6, multi-day rollover method (:466; item 12) | `XCUT.T25`, `HW` | owner | Decided "adapt now, measure later", but under OR5.a it must end as run or as a documented limitation; the enabled test fails by construction today (`HW.N277`) |
| H1, owner's two-chroot run (:467; :514-612) | `TOOL`, `ENV` | keep (owner-run) | Build-environment evidence for the release; the max-args trixie note (:625-636) folds into it |
| F17, item 44's anomalies (:329-343) | `XCUT.T13`, `HW.T17` | owner: close | The hotspot fallbacks are explained (stale AP station); the one silent reset has not recurred in two full default tiers, a gated run and 3.7 h idle (`851e816`, `a9c8627`) |
| G10, UART vs the C side (:468) | — | settled | `arduino/` is out of scope |

**B.2 Other open BACKLOG items**

| Item | Plan | Proposed | Why |
|---|---|---|---|
| Four modules not renumbered (:21-35) | `XCUT.T07`, OR28 | do | OR28.a renumbers every module in one pass |
| `disallow_any_explicit` (:36-51) | `ENV.T06` | do | In this audit (OR81.a) |
| Timeout/cancellation mechanism, PRIORITIZED (:58-67) | `PLAT.T06` | do (design first) | The owner's own "to be done soon"; the largest open refactor target |
| Supervisor error-budget counter (:68-72) | `XCUT.T02`, OR24 | do | Same behaviour, cleaner implementation |
| "Rough sequencing" (:73-79) | `DOC.S21` | retire | Narrative whose steps are done or superseded (OR27) |
| Test-suite scan re-run beyond its domains (:81-95) | OR16/OR19/OR21 | do | The audit's whole-suite review is that re-run; the entry's `_reboot()` follow-on is already done (`DOC.S24`) |
| ISL29125 divergence and W12 (:99-140) | `SENS` | retire into S3b | Fixed and confirmed on silicon; only `Overrange` owes a run (B.1) |
| Item 24 / item 32 | `PERF.T03` | owner, then do | See R2 above |
| Two device-script loose ends (:720-727) | `HW.S09` | owner | Fold the watchdog wrapper in, or retire the script (B.3) |
| wozi/dev hand-written definitions (:812-832) | `GEN.S16`, `WEB.T05` | do | The last hand-kept generated output; needs the `tests_js/` fixture audit |
| Manual cross-browser check (:833-837) | `WEB.T09` | keep (owner) | Only a human on real Safari/mobile can do it; hardware-phase companion |
| UART sensor integration (:838-846) | — | retire → known limitation | Owner-confirmed out of scope (not a legacy feature) |
| Owner requirement: final wiring (:847-858) | `TWIN` | retire at close | Fulfilled; the entry itself says it leaves when the audit closes |
| Config-duplication centralization (:859-863) | `GEN` | verify, likely retire | Cites the retired `sensortask-wozi.py`; generated wiring may already make each `_VAL_*` tuple the single source |
| `js/nav.js` listener, `selectSection()` duplicate (:866-874) | `WEB.S18` | do | Small; OR24 harmonisation |
| Dev/build environment setup (:875-882) | `DOC.S21`, `TOOL` | do | Half stale ("now fixed too"); `update_and_install.txt` vs `pico_setup.sh` is open |
| `network_available()` rename (:883-888) | `NET`, OR24 | do | Small; generated call site updated with it |
| SCD30 NVM endurance (:909-912) | `SENS` | keep → SPEC | A standing caution; belongs in Part C/F rather than BACKLOG (OR27) |
| NTP outage × bus load in the twin (:913-923) | `TWIN.T05` | owner | Worth adding to twin Run 9, or recorded as not needed |
| I.2 placement re-walk (:924-933) | `MEM.T02` | do | The audit's memory lens is that walk |
| Settled/record entries (:473-512, :613-676, :677-776, :864-865, :889-908) | `DOC.T14` | keep as do-not-reopen | Decisions and measured rejections; some carry narrative to prune (OR27) |

**B.3 Investigation-born tests and scripts**

| Test or script | Plan | Proposed | Why |
|---|---|---|---|
| `device_scripts/wifi_country_hostname_edge_values.py` (orphan) | `HW.S16` | retire | Its question (byte vs character caps) is answered by C.7.4's byte bounds, confirmed on silicon 2026-09-25 (`0154aec`) |
| `device_scripts/wifi_reconnect_after_failed_attempts_repro.py` (orphan) | `HW.S08`, `HW.S16` | retire | One-off repro of a delay root-caused on 2026-09-02 (`c43e177`: a CYW43 phantom disconnect, now SPECIFICATION.md F.2's backstop); also carries the persisted bench PSK (`HW.T11`) |
| `device_scripts/wifi_service_reconnect_repro.py` (orphan, F1) | `HW.S09` | owner: retire or fold | F1 is verified; keeping it means folding the watchdog wrapper in and adding a runner |
| `device_scripts/heap_layout_after_full_boot_sequence.py` (orphan) | `HW.S16`, `MEM` | retire | Report-only measure-B instrument (listed at `HEAP_FRAGMENTATION_MEASUREMENTS.md:273`); the effect it measured is guarded on the twin tier by `tests_scripts/test_digital_twin_boot_contiguity.py` |
| Measure-A/B instruments in the flash/bench tiers (`allocation_need_per_source.py`, `heap_headroom_after_full_system_build.py`, `fram_capacity_after_full_system_build.py`, `serving_at_default_gc.py`, `heap_under_connection_ceiling.py`) | `MEM`, `HW.T05` | keep where they assert | Each asserts a floor the heap design must keep; any part that only reports is a retire candidate |
| Platform-fact demonstrations (`bus_deinit_is_a_noop_on_real_hardware.py`, `float_boundary_2pow24.py`, `scheduler_saturation_drop.py`, `timer_alarm_pool_exhaustion.py`) | `PLAT` | keep, version-bump checks | They re-check Part F facts on silicon, which CLAUDE.md's standing practice asks for at every pin move |
| `uart_read_never_blocks_the_loop.py` (raw UART) next to the shipped-driver script | `BUS`, F.5.8 | owner: keep or fold | The driver script already runs an unclamped read as its control (`:163-164`); the raw one proves the peripheral property independently of the driver |
| `flash/test_bus_electrical_timing.py::test_ticks_ms_real_2pow30_rollover` | G6 | owner | Fails by construction until its method changes (B.1, G6) |
| `digital_twin/segfault_stress_repro.py` | `TEST.T20` | retire candidate | Manual tool for a root-caused, fixed segfault; the bench burst test covers the scenario |
| Tests pinned to closed BACKLOG items (5, 6, 9, 12, 29, 30) | `TEST.T20` | review | Keep each that guards a property; retire any that only re-demonstrates the closed symptom |
