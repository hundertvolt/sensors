# Project audit — plan and topic catalog

**Status: PLANNING. Audit execution is BLOCKED until the project owner gives an explicit go-ahead in
the conversation that starts it.** Nothing in this file authorizes any audit work: every topic, seed
observation and question below is a *recorded item to cover later*, never an implicit start. Until
the owner declares the planning phase finished, the only permitted work on this file is extending,
correcting and validating the list itself (section 6).

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
- **Status markers**: `[ ]` open, `[x]` done, `[~]` partially done (used in 1.2, 4.6, 5 and 6). During
  execution, progress lives only in the register (4.5); topic boxes in section 5 are not ticked.
- **Where things live**: this file (plan, topics, seeds); `audit/` (temporary audit apparatus: planning
  survey notes, the harvest of what the project's own comments/docs/history record, and later the sweep
  scripts, register and wave artefacts — proposed under PQ2); section 3.1 (owner statements, verbatim).
- **Line anchors** are as of commit `4dc80ef` (planning baseline: `main`'s head after the automated-build-chain
  merge, PR #58, 2026-09-25 — the audit's real starting point, owner, 3.1). Resolve them with
  `git show 4dc80ef:<path>`; at HEAD they drift. They were moved from the first baseline `0615eba` (and the
  harvest's `2a88cc8`) by `audit/sweeps/reanchor.py`; section 6 V11 records the move.

---

## 1. Goals and definition of done

### 1.1 Goals

1. **Broad**: every tracked file outside the out-of-scope list is looked at by an auditor with a
   stated lens — code, tests, tooling, CI, website, docs, config.
2. **Deep**: every in-scope source file — `src/`, `buildgen/`, `toolchain/`, `scripts/`, `js/`, the
   generated modules and the test/twin/hardware-harness infrastructure — is read line by line, down to
   function internals, not grepped; formulas and protocol facts are checked against datasheets, the
   pinned MicroPython 1.29.0 source and current documentation, never memory (CLAUDE.md, Part D.1/D.9).
3. **Converged**: each area's findings stabilise under independent re-audit (section 4.4), and
   cross-area contradictions are arbitrated rather than left as two reports.
4. **Actionable**: every finding ends as exactly one of: fixed-and-verified, owner decision recorded,
   moved to `BACKLOG.md` (silicon-owed ones to its real-hardware section) with enough context to act on, or rejected
   with the reason.
5. **Feature parity preserved**: the refactor keeps the deployed units' top-level features (CLAUDE.md
   working agreement); every behaviour change found is either documented-as-deliberate or raised.

### 1.2 Definition of done (whole audit)

- [ ] Every area in section 5 has its topics answered, its seeds triaged, and its quality measure met.
- [ ] Every finding in the register (section 4.5) has a terminal status.
- [ ] Every cross-cutting lens (section 4.2) has been applied to every in-scope area and recorded per
      area — "N/A, because …" is a valid record; silence is not.
- [ ] Green, with zero `MemoryError`/`memory allocation failed`: `scripts/lint.sh`,
      `scripts/typecheck.sh`, `scripts/test.sh` (both `gc.threshold(-1)` and `GC_THRESHOLD=32768`),
      `scripts/test.sh --coverage`, `scripts/run_digital_twin_ci.sh` for all 6 devices, the npm tier
      (`npm run lint`, `npm run typecheck`, `npm run lint:html`, `npm run lint:css`, `npm test`),
      `scripts/build_firmware.py` for all 6 devices, and `uv run pytest tests_hardware --collect-only`.
      No test deleted or weakened without a registered finding saying why (a vacuous test may
      legitimately go).
- [ ] Coverage recorded before and after; any drop explained.
- [ ] Every real-hardware item the audit produced is in BACKLOG.md's "Real-hardware work still owed" (or was run,
      if the owner granted a bench go-ahead inside the audit — PQ4).
- [ ] CLAUDE.md side-obligations met for every change the audit made: BACKLOG's chroot-owed list for
      build-environment changes, `UART_C_PORT_CHANGELOG.md` for `asy_uart_comm.py` changes, the
      bird's-eye `src/` scan for any new `src/` file, README "Further reading" for any new doc (incl. a
      sibling register file).
- [ ] Audit worktrees, scratch branches and scratch tags cleaned up (an archive tag chosen under PQ2 stays);
      every fix branch had a PR with a meaningful description and a PR-activity subscription (CLAUDE.md
      PR workflow).
- [ ] Every permanent fact this file (and the register) holds has migrated; the owner agrees the audit
      is finished; this file and the register are deleted.

---

## 2. Scope

### 2.1 In scope

All of: `src/`, `ext/` (behaviour relied upon only — see 2.2), `buildgen/`, `devices/`, `toolchain/`,
`scripts/`, `.github/`, root config (`pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`,
`eslint.config.js`, `tsconfig*.json`, `vitest.config.js`, `.htmlvalidate.json`, `.stylelintrc.json`,
`host_typecheck.ini`, `.gitignore`, `.nvmrc`), `js/`, `html/`, `mockdata/`, `tests/`, `tests_js/`,
`tests_scripts/`, `tests_hardware/` (desk review; execution only with a go-ahead), `digital_twin/`,
and every markdown doc (`*.md` at the root, `digital_twin/README.md`, `tests_hardware/README.md`,
`dev_legacy/README.md`), plus `update_and_install.txt`, `LICENSE`, `THIRD_PARTY_LICENSES.md`.

### 2.2 Out of scope, or in scope only as a reference

| Path | Treatment | Authority |
|---|---|---|
| `arduino/` | Out of scope entirely: no audit, no reconciliation, no findings about its contents (licensing included); the only open item is whether docs should state the exclusion (`LIC.T04`, owner) | BACKLOG (owner, 2026-09-24, SETTLED) |
| `python/`, `modules/`, `build-*.sh`, `html_raw/` | **Read-only reference** for the parity area (`PAR`): read to establish deployed behaviour; a finding about it is recorded only when it explains current behaviour, never as a to-do | CLAUDE.md legacy rule |
| `ext/microdot.py`, `ext/freezefs/` | Never edited or restyled. Audited only for *what this project relies on* from it, and for whether our wrappers cover its gaps | CLAUDE.md vendoring rule |
| `datasheets/` | Reference material. Gaps (missing datasheets) are recorded, not "fixed" by web memory | CLAUDE.md / Part A.6 |
| `dev_legacy/` session logs and snapshot | Reference only; its `README.md` is in scope as a doc | Part A.1 |
| `modules/_boot.py`'s `import sensortask.py` | Never changed without real-hardware testing | CLAUDE.md hard rule |
| `dev` bench quirks | Out of scope as bugs (e.g. routes to uninstantiated objects) | CLAUDE.md |

### 2.3 Standing constraints and CLAUDE.md conformance

Every auditor receives the packet defined in 4.4 ("Auditor context") and applies the lenses *inside*
CLAUDE.md's rules. Specifically:

- Flag, don't silently fix, any behaviour/formula discrepancy (Part D.1) and any cross-file consistency
  discrepancy found by a `src/` scan (CLAUDE.md "bird's-eye-view scan").
- Settled decisions are not re-opened (BACKLOG "SETTLED" entries, Part A.4 "confirmed intentional", the
  wedged-I2C/WiFi backstop rules, `NTP_Host`'s 1024 bound, FRAM
  `verify_present()`/`set_write_protected()`, buildspec hand-maintenance, no UART version negotiation). A seed that touches
  one is triaged "settled — no action" unless it shows the settled *premise* is factually wrong — then
  it is raised to the owner, never acted on.
- L-EXC does **not** flag missing blanket `MemoryError` wraps around asyncio primitives (CLAUDE.md
  forbids them, F.2); the boot-confined `gc.collect()` (I.4(f.1)) is approved.
- Real hardware: owner go-ahead *in the conversation that runs it* — CLAUDE.md: a go-ahead "given to a
  different session, or to an earlier session that already ended, does not carry over" and "covers the
  rest of that same conversation"; subagents and child sessions don't inherit it; wear gates;
  FRAM-forensics-first (twin included); dead-man's switch for host network changes; `br0` MAC pinning.
  Audit agents never run `setup_toolchain.py env --tier flash|bench`.
- Wear, host SSD included: no brute-force-scale fuzzing or mutation; per-agent toolchain rebuilds only
  when unavoidable; find the invariant (CLAUDE.md wear rule).
- Memory-safety discipline (design for zero `MemoryError`, no `gc.collect()` propping, both GC stages).
- Comment cap (3 lines) and docs-hold-current-state for anything the audit writes.
- BACKLOG numbering: numbers are never reused — the next new item is ≥ 51 (check `git log` first).
  Real-hardware row IDs live on in BACKLOG.md's "Real-hardware work still owed" (the queue and handover
  files were folded in there, `03f8bcf`); retired row IDs are never reused either — C7, R10, F7, F10,
  F11, F13, G9, and since 2026-09-25 T2, G1, G3, G4, G8, G12, N2, R1, R4, R5, R6, R7, F1, W4, W5.
- Step-session workflow for any **fix unit**: scope → ≤ 10 questions → tests first → implementation →
  coverage → stop and report. For the audit itself, the "stop and report" points are PQ8.
- Fix-unit obligations: UART changelog entry for any `asy_uart_comm.py` change; bird's-eye scan for a
  new `src/` file; BACKLOG chroot-owed entry for any build-environment change.
- Stale-doc rule (update the doc in the same session): during a findings-only phase this conflicts with
  "findings first" — resolved by PQ1.

---

## 3. Open decisions for the owner (needed before or at go-ahead)

These shape *how* the audit runs. None blocks further planning; all block execution. Ten questions,
per CLAUDE.md's step-session limit.

| ID | Question | Options | Planner's recommendation |
|---|---|---|---|
| PQ1 | Output mode and phase rules | (a) findings register first, then owner-prioritised fix units; (b) fix-per-area once that area converges; (c) findings only. Also: SEV1 escalated immediately? May the findings phase add tests/harnesses (the REST/GEN quality measures need a test matrix and a fuzz harness)? Is audit-found doc drift fixed in place (stale-doc rule) or registered? | (a); SEV1 immediately; findings phase may add harnesses in scratch/worktrees only; arbiter fixes SEV4 factual doc drift in place (satisfying CLAUDE.md's stale-doc rule), everything else registered |
| PQ2 | Branching, register location, merge | Owner intent (3.1): this work has its own branch and PR. The feature branch it was stacked on merged into `main` on 2026-09-25 (PR #58, `4dc80ef`), and the PR now targets `main`; this file lives on the audit branch only (removed from `main`, PR #108). Open: which branch the execution phase runs on (this one, or a fresh one per session/wave); fixes here vs one branch + PR per fix unit; where the audit apparatus lives (proposed: a temporary `audit/` directory — register, sweep scripts, wave artefacts — outside the lint/typecheck scopes, deleted at close); may the arbiter commit and push audit files autonomously after each arbitration batch; merge strategy into `main` (~77 "archive §" citations point at `12640c2`, reachable from `main` since the PR #58 merge commit — `DOC.S04`) | `audit/` directory, register `audit/REGISTER.md`; autonomous commits of audit files only; one branch per fix unit; merge commit (or tag `12640c2`) rather than squash + delete |
| PQ3 | Severity scale and sign-off threshold | proposed: SEV1 board/host safety, bricking, data loss, evidence loss; SEV2 functional defect, SEV3 robustness/latent, SEV4 consistency/doc/style | Owner sign-off before any fix that changes observable behaviour or a wire/storage format, regardless of severity |
| PQ4 | Real hardware inside the audit | (a) none — every silicon item becomes an entry in BACKLOG.md's "Real-hardware work still owed"; (b) gated bench sittings inside the audit. Also: sequencing with bench sittings other sessions run meanwhile (the 2026-09-24/25 sitting finished and was folded into BACKLOG, `03f8bcf`) | (a) by default — OR5.a/OR8.a add a real-hardware phase at the end; board/host-safety seeds (`HW.S01`, `HW.S06`, `HW.S07`, `HW.S09`, `HW.S10`, `HW.S25`, `TOOL.S03`) go to the owner *before* the next sitting, not at wave 3 |
| PQ5 | Threat model for `SEC` | (a) trusted home LAN; (b) untrusted LAN peers (guest Wi-Fi, IoT neighbours, DNS rebinding via a browser); (c) radio-range attacker in hotspot mode | Needs an explicit answer: it decides whether e.g. unauthenticated `bootloader` is a defect or an accepted property |
| PQ6 | Documentation scope | (a) correctness only (stale/contradictory/dangling); (b) also placement (I.6 inside Part J, CLAUDE.md size/auto-load budget, history pruning). Comment-cap extension to `tsconfig*.json`, `.gitignore` and 400-700-character one-line docstrings (`CI.S10`, `TEST.S22`) — `html/index.html`'s inline script is already under the current rule (`WEB.S19`); and whether docs should state the settled `arduino/` exclusion (`LIC.T04`) | (b), as its own late unit so it doesn't churn line refs mid-audit; cap extension is the owner's call |
| PQ7 | Moving target | Other sessions keep committing to `main`, the audit's base since 2026-09-25. (a) freeze non-audit work during the audit; (b) audit a pinned baseline and run delta passes over files changed since each area's closure. Also: one arbiter across sessions? Does the audit go-ahead persist across sessions? | (b) with a single-writer lease (4.7); go-ahead re-confirmed per session |
| PQ8 | Owner stop-points (CLAUDE.md step-session "stop and report") | After ENV; after each wave; only at the end | After ENV and after each wave |
| PQ9 | Resources | Agents per wave, token budget, execution host/egress. **Partly answered** (owner, 2026-09-25, verbatim in 3.1: parallel agents "as many as you like", with care, converging, not interfering — given for the planning session). Open: does that permission carry over to execution sessions; may ENV prep (toolchain build, baseline run) happen before the go-ahead? | Waves of ≤ 8 auditors + verifiers; ENV prep allowed early since it audits nothing |
| PQ10 | Owner inputs the plan cannot derive | Is a legacy→refactor reflash campaign planned (makes `PAR.T06`/`PAR.T07` SEV1)? External REST consumers of the legacy routes (`PAR.T05`)? The Sensirion VOC C reference (reachable since 2026-09-25: `Sensirion/gas-index-algorithm`, OR4.a); missing datasheets (none left: RP2040, WS2812, QSPI flash, CYW43439 and BMP390 added 2026-09-25)? Permission to run legacy code as an oracle (`PAR.T12`)? UF2 distribution scope and repo visibility (`LIC.T06`/`T07`)? Browser support floor (`WEB.T09`)? Is `pico_gpio.py`'s conservatism intended (`GEN.T07`)? | Owner input |

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

Go-ahead record (empty until given): date · session · scope (which steps/waves) · autonomous commits of
audit files authorised (y/n) · parallel-agents permission carried over (y/n) · real-hardware go-ahead
(never carried over; per conversation, CLAUDE.md). PQ answers are recorded in the PQ table's last column,
dated, replacing the recommendation.

### 3.2 Owner requirements (verbatim, collected with the owner; recorded, not yet worked into the plan)

Read with the 2026-09-25 fold (`03f8bcf`): `REAL_HARDWARE_TEST_QUEUE.md` and `HARDWARE_TEST_HANDOVER.md` no
longer exist — every "queue row" or queue file named in an interpretation below means an entry in
BACKLOG.md's "Real-hardware work still owed", and OR11.a's deletion of those two files is already done.
The owner's words themselves are unchanged.

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
| OR4.a | 2026-09-25 | Inaccessible sources during execution: owner answered "yes, that's right." to the proposal: do not wait; continue from the next-best source; mark the affected finding "open until the owner provides X"; report it in the progress and final reports; re-check those findings once the source arrives. The consolidation run tests access to every source it anticipates and hands the owner one list of what is unreachable. Known gaps at recording time: RP2040 chip datasheet, BMP390, WS2812/NeoPixel, Pico W QSPI flash chip, Sensirion VOC algorithm reference, possibly CYW43439 (the owner is uploading them). Status 2026-09-25: BMP390, W25Q16JV, CYW43439 and WS2812 uploaded and added to `datasheets/`; `Sensirion/gas-index-algorithm` is reachable via GitHub (cloned for reference, not vendored); the RP2040 datasheet was pushed by the owner (`datasheets/pico w/RP-008371-DS-1-rp2040-datasheet.pdf`); still missing: the Sensirion VOC Index application note — its host (`www.sensirion.com`) is blocked by the session's network policy, as are `pip-assets.raspberrypi.com`, `datasheets.raspberrypi.com` and `www.adafruit.com`. |
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
| OR39.a | 2026-09-26 | Owner answered "1. gc.collect is allowed IN TESTS for getting a clean baseline for memory measurement tests (but it takes time to complete, don't call and measure in the next line of code).  gc.collect is allowed IN THE CODE at exactly the place you found it: in the one-time executed boot procedure. It is disallowed inside the main loop. This is all should match the exception descriptions on the docs. 2. Whichever needs to be measured. Just don't charge the actual business logic code. 3. The setup script and the whole test suite and tiers - basically everything except the actual business logic of the board." — (1) `gc.collect()` in production code exists only in the one-time boot procedure (`system_service.py:222, 226`, the generated boot entry `codegen.py:459, 466`), never in the main loop or any runtime path; in tests only to set a clean baseline for a memory measurement, never followed by the measurement in the very next statement (let it complete and settle first) and never inside a timed window; CLAUDE.md's and SPECIFICATION.md I.4(f.1)'s exception text and `tests_scripts/test_gc_collect_sites.py` are checked to state and enforce exactly this. (2) Speed and footprint work may measure and reduce whatever is useful — host RAM, Unix-port heap flags, parallel processes, twin boots, redundant object graphs, CI minutes — but never charges the board's business logic: no `src/` change is made for test speed or footprint. (3) Scope: the setup script (`toolchain/`, `scripts/`), every test tier and the CI pipeline — everything except the board's business logic; every job, gate and test keeps running, nothing is weakened or skipped, no timeout is tightened without a measurement, OR37's wear rules apply, and before/after wall-clock and peak memory are recorded per tier. |
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
| OR47 | 2026-09-26 | Boot queueing, FRAM allocation order and timer stagger: "Ensure that the startup procedures in the system service do queue correctly, ensure a guaranteed fixed order for the FRAM chunk allocations, give the FRAM allocations enough time, and that the sensor timer starters will be started in a way that prevents race conditions / timers firing at the same time over any harmonics of the multiple of 1s sensor read interval steps (look into the docs and code for details)." — Interpretation in OR47.a. At recording time: FRAM chunks are allocated synchronously at construction (`print_log.py:238` → `AsyFramManager.get_chunk()`), so their order is the generated construction order; chunk setup I/O (`pr.setup()`) runs in the sequential boot `setup()` batch for most modules but lazily inside tasks for some (`webserver`'s `_run()`, SPECIFICATION.md A.7; `SCD30_Reader._init_scd()` inside `read_loop`, `asy_scd30_driver.py:161-164`), i.e. inside the task-start window; tasks start via `asyncio.sleep(1/N)` with a `gc.collect()` after each (`system_service.py:216-227`); read-trigger timers start via a chain of one-shots `1000/(N+1)` ms apart (`system_service.py:148-175`), each armed from inside the previous soft callback. SPECIFICATION.md C.9.1 proves no coincidence for 1000 ms-based periods, but three points are open against it: (a) the SCD30's base tick is 500 ms (`asy_scd30_driver.py:214-215`), so its ticks fire at its slot and 500 ms later, and whenever N+1 is even a slot (N+1)/2 away sits exactly there; (b) arming each one-shot from the previous callback adds that callback's dispatch latency to every later offset, so offsets are k·d plus accumulated jitter, and C.9.1 asks only that they be distinct, not that they keep a margin; (c) the 1000 ms periodic timers outside the sequencer (`system_service.py:204` uptime, `asy_wifi_service.py:662`, `asy_ntp_client.py:343`) start at arbitrary phases. The FRAM datasheet (`datasheets/fram/MB85RS64V-*.pdf`) is AES-encrypted for text extraction; its power-up and access timing is read in execution. Related: OR26.a (construction completeness), OR31 (watchdog feeding), OR35 (log flooding), OR37.a (races, deterministic interleaving proof), OR39.a/OR40.a (boot `gc.collect()` sites), OR41.a (interaction matrix), CLAUDE.md FRAM and boot-latency rules, SPECIFICATION.md A.7, C.9, C.9.1, I.4(f.1), `CORE`, `STOR`, `SENS`, `PERF`. |
| OR47.a | 2026-09-26 | Owner answered "1. yes 2. fingerprinting on the fram is a waste of space. there is no requirement for the fram to stay consistent through firmware re-flashes. it only must be rock solid within one individual firmware build. 3. I don't know about a 500ms tick in scd30. if this is the missing interrupt recovery timer, it would be okay to set it to 1000ms as well, as all the others. and it's always only about sensors with bus access. 4. yes" — (1) Boot phases run strictly one after another — construction, the `setup()` batch, task starts, timer starts — each fully complete before the next, nothing fired off unawaited, order generated by buildgen and fixed; proven for every generated device by recording the real boot sequence in the twin and asserting it, and once on the bench with a timestamped boot log. (2) No FRAM layout fingerprint: FRAM content need not survive a reflash. Within one firmware build the allocation order must be fixed and deterministic — it is today (synchronous `get_chunk()` at construction, in generated construction order), which is asserted by a test per generated device and stated in SPECIFICATION.md A.7. Robustness still covers the first boot after a reflash as a within-build case: a chunk holding another build's bytes is handled gracefully (CRC mismatch → treated as empty and re-initialised, no crash, no error flood — OR35). "Enough time": every chunk setup (`pr.setup()`) moves into the one-time boot `setup()` batch, awaited in the fixed order with the watchdog fed in between (no lazy setup inside tasks — `webserver`'s `_run()`, `SCD30_Reader._init_scd()`), and the FRAM chip's power-up and access timing from its datasheet is respected before the first access. (3) Confirmed: the SCD30's 500 ms tick is the missed-interrupt recovery timer — `scd_init_irq()` counts ticks while the data-ready pin stays high and forces a read after `trigger_half_sec = 2 * trigger_sec` of them (`asy_scd30_driver.py:143, 212-222, 413-421`). It moves to 1000 ms like every other sensor tick (threshold becomes `trigger_sec` ticks, the counter renamed accordingly), so every bus-accessing timer shares the 1000 ms base and C.9.1's proof holds again. The stagger plan covers only timers that trigger bus access (sensor reads); the uptime, WiFi and NTP 1 s timers stay out of it. Gap (b) stays in scope: every start is scheduled against one shared starting point (target = t0 + k·slot) so callback latency cannot accumulate, and the guarantee is a minimum separation of one measured worst-case read duration, not mere distinctness; sensors sharing a bus are placed as far apart as possible. Proof: fake-clock tests of the real sequencer for every generated device, an exhaustive check over all period combinations in the allowed ranges, and bench timestamps of real trigger moments over a long run; SPECIFICATION.md C.9.1 corrected (its SCD30 exception paragraph goes). (4) The task-start stagger (`asyncio.sleep(1/N)`) stays a coarse spread with no coincidence claim; checked for correct ordering and for the OR39.a/OR40.a boot `gc.collect()` rules. |
| OR47.b | 2026-09-26 | Owner: "Changing the SCD30 interrupt recovery from 500 to 1000 must then be validated working if course" — The 500 → 1000 ms move (OR47.a (3)) is done only when the recovery path is shown working at every tier, not just the counting. Found at recording: the change keeps the wall-clock threshold (2·`trigger_sec` ticks × 500 ms = `trigger_sec` ticks × 1000 ms), but nothing today proves the recovery end to end — the unit tests drive `scd_init_irq()`'s counter with a hand-set event and a fake pin (`tests/test_asy_scd30_driver.py:726-790`) and assert the old `period == 500` (`:652`); the twin's SCD30 fake always delivers the RDY edge (`digital_twin/_scd30_chip.py:163-165`), so the fallback never runs there; the one hardware script tests only the fast path and discloses it cannot tell which path fired (`tests_hardware/device_scripts/scd30_real_irq_edge.py:1-3`, `tests_hardware/README.md:653-658`). Validation: (1) unit, fake clock — period 1000, threshold `trigger_sec` ticks; a missed edge forces a read no earlier than `trigger_sec` s and no later than `trigger_sec` + 1 s after the pin went high; the read pulls the pin low and resets the counter, so exactly one forced read per miss and none while edges arrive; a tick that catches the pin high during a normal cycle (edge seen, read not yet done) leaves no stale count behind; `trigger_sec` range limits included. (2) twin — a fault switch on the SCD30 fake drops RDY edges; every generated device with an SCD30 boots, a dropped edge produces the recovery read and the "Interrupt Start Trigger" event within the bound above, the data keeps flowing, and the control arm (edges delivered) never logs that event. (3) flash — real silicon with the pin interrupt deliberately not delivered (handler detached, timer running), so only the fallback can fire: a real reading arrives within the bound and the pin drops; the existing fast-path script gains the converse check (reading arrives and no "Interrupt Start Trigger" event), which removes its disclosed ambiguity. (4) bench — full firmware over a long run: SCD30 readings keep their period, no unexpected recovery events, and the recovery tick's trigger moments are part of OR47.a's stagger timestamps. No NVM write is involved (reads only), so none of it is `persistence_write`-gated. Related: OR45.a (containment: the flash fallback case is the real equivalent of the twin fault), OR37.a, OR41.a, SPECIFICATION.md C.9.1, `tests_hardware/README.md` SCD30 RDY note (updated). |
| OR48 | 2026-09-26 | Unexplained legacy divergences as hints: "Functional discrepancies from the legacy code without an obvious reason or recorded decision must be investigated, as they may be hints to something lost. Most prominent recent example: the only write on changes function for SCD30. But this is just an example, treat this requirement as a concept!" — Interpretation in OR48.a. At recording: the plan already carried the SCD30 case, but only as a harvested seed (`PAR.S02`); the parity topics look at the REST surface, the web UI, timing constants and published values (`PAR.T01`, `T04`, `T10`, `T12`), so a divergence that is invisible at the API — a write that is skipped, a command order, a delay, a retry, a readback check — has no systematic owner. Sources for "recorded decision": SPECIFICATION.md, CLAUDE.md, BACKLOG.md, code comments and the refactor's commit history (full, not shallow: 1636 commits, so `PAR.T15`'s "this checkout is shallow" is stale). Legacy's own history is not in the repo — it arrives in one import (`8c4a73d`, 2026-07-13) — so legacy's reasons can only come from its code and comments, the datasheets and the owner's memory. The legacy tree at HEAD is not purely the imported state: `2bda920` edited `python/IndividualDrivers/asy_bmp3xx_driver.py` and `modules/sensortask-wozi.py` (IIR coefficients), so which state is the comparison baseline matters (with `PAR.T15`). Related: OR12.a (regression vs defect, flag-before-change), OR42.b/OR42.c (the SCD30 instance, restored within the base classes), OR44.a (concept and checklist), OR46.a (file-by-file ledger), `PAR` area, CLAUDE.md "verify against the legacy driver's own actually-proven field behavior". |

---

## 4. Method

### 4.1 Execution order (proposed, after go-ahead)

- **Step 0 — ENV**: build the toolchain, run every tier once, record the baseline (counts, timings,
  coverage, warnings), build the do-not-reopen index (`DOC.T14`) and commit the sweep scripts next to the
  register. Nothing is audited against an unmeasured tree. Owner stop-point (PQ8).
- **Step 1 — Prep**: the inputs every later lens needs — `PAR.T01`/`PAR.T02` (the legacy inventory for
  L-PAR) and `SEC.T01` (the threat model for L-SEC, needs PQ5) — plus a **pilot**: one small,
  self-contained area (`LED`, two files) run through the whole pipeline to calibrate cost, the
  convergence rule and the register format. Owner stop-point.
- **Wave 1 — foundations, in parallel**: `XCUT` (system contracts), `CORE`, `ALGO`, `BUS`, `PLAT`. Their
  outputs (error-code catalogue, lock/timer maps, FRAM layout, MicroPython facts) are inputs for
  everything else. Owner stop-point after each wave (PQ8).
- **Wave 2 — subsystems, in parallel**: `SENS`, `STOR`, `UART`, `NET`, `REST`, `GEN`, `TOOL` (`LED`
  re-checked against wave-1 outputs).
- **Wave 3 — consumers and verification tiers**: `WEB`, `TEST`, `TWIN`, `HW`, `SCR`, `CI`.
- **Wave 4 — cross-cutting synthesis**: `SEC`, `MEM`, `PERF`, the rest of `PAR`, then `DOC` and `LIC`
  last (they absorb every other area's doc findings).
- **Close-out**: delta passes over files changed since each area's closure (`git diff
  <closure-sha>..HEAD`), then a global convergence pass over the register, then owner review.

Recommended (PQ1/PQ3): SEV1 findings go to the owner immediately, whatever the wave.

**Units** (the register's header tracks each; "the lowest open unit" in 4.7 means the lowest number
not `closed`, together with every other open unit of its wave):

| Unit | Content | Unit | Content |
|---|---|---|---|
| U0 | ENV (4.6) | U9-U16 | wave 2: SENS, STOR, UART, NET, REST, GEN, TOOL, LED re-check |
| U1 | PAR.T01/PAR.T02 | U17-U22 | wave 3: WEB, TEST, TWIN, HW, SCR, CI |
| U2 | SEC.T01 (needs PQ5) | U23-U28 | wave 4: SEC, MEM, PERF, PAR (rest), DOC, LIC |
| U3 | LED pilot | U29 | close-out: delta passes, global convergence pass, owner review |
| U4-U8 | wave 1: XCUT, CORE, ALGO, BUS, PLAT | | |

- A **pass** is auditor A + auditor B + the arbiter's merge of the two (4.4); verifiers run per pass.
- `converged@sha`: the 4.4 convergence rule is met. `closed@sha`: converged, every register entry of the
  unit terminal or routed to the owner, the per-area lens record filled (1.2) and the quality measure met.
- A pass with no committed auditor report is restarted from scratch, never resumed from memory.
- A stop-point (PQ8) sets the register header's `Awaiting owner` field; nothing runs past it.

### 4.2 Cross-cutting lenses (apply to every in-scope area; "N/A, because …" allowed)

| Lens | Question every area answers |
|---|---|
| L-CORR | Correct against the authoritative source (datasheet, RFC, MicroPython 1.29.0 source, Microdot v2.6.2 source, browser spec) — verified, cited, not recalled |
| L-EXC | Exception net complete: nothing raises out of a never-raise contract; every raise has a catching caller (Part D.2), including import time and the pre-`WDT()` phase (`XCUT.T20`) — within CLAUDE.md's no-blanket-asyncio-wrap rule |
| L-CONC | Every lock, shared state, await point and interleaving; lock-hold spans containing sleeps or I/O; lock order |
| L-BLOCK | Nothing blocks the loop beyond its budget (Part D.5, F.3, F.5.8) |
| L-TIME | Timers (soft-callback drop, ONE_SHOT vs PERIODIC, alarm pool), ticks wraparound *and* the age of stored ticks values (`ticks_diff()` is only valid under 2**29 ms), deltas passed to `ticks_add()`/`sleep_ms()`/`wait_for()` and `Timer(period=)` values (`XCUT.T25`), timeouts vs the configured 8000 ms watchdog (8388 ms is the rp2 cap) |
| L-MEM | Allocation bounded and not client-controllable; churn on hot paths; long-lived placement (Part I) |
| L-LIFE | Every resource (socket, timer, task, file, lock, buffer, FRAM chunk) released on every path incl. cancel/restart |
| L-STATE | State machines complete: every state × event, including task restart, reboot, power loss, and cancellation at every `await` |
| L-DIAG | Every failure mode leaves persisted, attributable evidence (errcount/FRAM entry, reset cause) — or is recorded as knowingly silent; routine events don't churn the evidence |
| L-TGT | The property holds in target semantics, not only on the 64-bit double-precision Unix port or the twin (float32, 31-bit small ints, soft-callback drop, IRQ-off windows, blocking UART reads) |
| L-COMPAT | Persisted and wire formats (config files, FRAM layout, REST shapes, UART frames) stay stable across firmware updates, or a migration is defined |
| L-WEAR | Flash/NVM/FRAM write frequency and who can trigger it (REST, loops, tests) — and host I/O (CLAUDE.md's SSD rule) |
| L-SEC | Input from the network/LAN/radio/user treated as hostile per the PQ5 threat model |
| L-API | D.10 consistency within and across files; naming; return conventions; Part G reuse |
| L-DEAD | Dead code, unused parameters, test-only production API, unreachable branches |
| L-TEST | Tests bite (fail when the property breaks), not vacuous, not tautological; tiered per CLAUDE.md |
| L-DOC | Code, comments and docs agree; comment cap; no dangling citations |
| L-PAR | Behaviour equals legacy or the change is documented as deliberate |

### 4.3 Techniques catalogue

- **Line-by-line reading** of every in-scope source file (full reads, never grep-only), with the
  callers and callees of each function read alongside (Part D.0).
- **Source and documentation verification**: clone MicroPython `v1.29.0` (and Microdot `v2.6.2`) into the
  scratchpad; every runtime claim cites a file and line there *and* is checked against the current
  MicroPython, rp2-port and Microdot documentation (CLAUDE.md standing practice).
- **Datasheet verification** from `datasheets/` (text already extracted during planning to the session
  scratchpad; re-extract in a new session).
- **Differential testing**: mock tier vs twin tier; Python VOC port vs Sensirion's C reference (if the
  owner can supply it); float32 vs double arithmetic for every formula that runs on rp2.
- **Mutation / clamp-removal sweeps** (the technique already used for UART, BACKLOG): remove or invert
  a guard, shadow the mutated copy ahead of `src/` on `MICROPYPATH`, require a named test to fail.
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
- **Execution** only in isolated git worktrees or scratch directories (section 4.6).

### 4.4 Multi-agent orchestration and convergence (parallel agents approved 2026-09-25 — not an execution go-ahead)

- **Roles**: *auditor* agents (read-only on the repo; one area or sub-unit each, one lens set);
  *verifier* agents (adversarial: try to disprove findings, by execution where possible, batched by file
  or theme); the *arbiter* (the main session: dedups, resolves contradictions between agents, assigns
  severity/status, is the **only writer** of this file and of the findings register, and may fix SEV4
  factual doc drift itself if PQ1 allows).
- **Per-unit pipeline**: auditor A (full deep read) → independent auditor B with a different lens
  emphasis, not shown A's output → arbiter merges → verifiers → confirmed / plausible / rejected.
  "Plausible" is not terminal: it ends as an owner decision or a BACKLOG real-hardware entry.
- **Git archaeology before flagging**: `git log`/`blame`/commit messages for the line in question, to
  find the owner decision behind it (many "odd" lines are settled decisions).
- **Convergence**: an area closes when two consecutive fresh passes (new agents, blind to the register
  until their own report is written, new lens emphasis) add no SEV1/SEV2 and at most one SEV3 after the
  arbiter's diff. Cap at 4 passes, then escalate to the owner.
- **Contradiction handling**: when two agents disagree on a fact, the arbiter checks the source
  directly (planning example: one survey said the hotspot timeout is 5 min, another 8 min — the class
  default is 5 but every `devices/*.toml` sets `hotspot_time_min = 8`; both were right about different
  things).
- **Auditor context** (the one definition; 2.3 points here): CLAUDE.md (auto-loaded); sections 0-4 and
  5.0 of this plan; its own area section; the full text of every topic/seed that section cites, marked
  "context only, owned by X"; its area's harvested notes (`audit/`, V10); the do-not-reopen index and the
  answered section 3; the text of every SPECIFICATION Part its References line names; from wave 2 on, the
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
  - Fix work (if PQ1 allows): one writer per file at a time, one fix unit per branch/worktree.

### 4.5 Findings register

`audit/REGISTER.md` (location pending PQ2), listed in README "Further reading", created at execution
start — not now. Written only by the lease holder (4.7).

**Header fields**: lease (session ID and link, since UTC) · released (UTC, or —) · audit branch ·
go-ahead reference (3.1) · awaiting owner (stop-point name, or no) · planning baseline (`4dc80ef`) ·
audit baseline SHA (ENV.T08) · delta queue (areas and files changed since baseline or closure) ·
current wave · unit table (U0-U29 from 4.1: not started / pass k / converged@sha / closed@sha /
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
(do-not-reopen index entry, or none) · needs-silicon (no / yes: which BACKLOG real-hardware entry) · wear (none / flash /
NVM / FRAM / host) · related / duplicate IDs · verifier verdict · status · decision (owner text or
pointer) · moved-to (BACKLOG number or real-hardware entry) · fix unit (branch, PR link) · `re-verified@HEAD`.

**Status transitions**: `open` → verifier verdict (`confirmed` / `plausible` / `rejected`) → one
terminal status. Terminal statuses map onto the four outcomes of 1.1 goal 4: `fixed`/`fixed-elsewhere` →
fixed-and-verified; `decided`/`settled-no-action` → owner decision recorded;
`moved-to-backlog`/`moved-to-hardware` → moved; `rejected`/`duplicate-of` → rejected with the reason.
`plausible` is not terminal (4.4): it ends as an owner decision or a BACKLOG real-hardware entry. Under PQ1(c) (findings
only), a confirmed finding ends as `decided` or `moved-to-backlog`.

A rejected seed or note stays in the register with its reason while the audit runs, so it is not
rediscovered. When the register is deleted, only rejections whose rediscovery risk is real migrate — per
CLAUDE.md's working agreement (target pending `DOC.S10`; a BACKLOG "don't re-raise" note only if the
owner confirms); the rest go with the file (docs-current-state rule).

### 4.6 Execution environment (area `ENV`)

Per-session topics (a fresh container repeats them): T01, T03, T04. Once-only topics commit their
results to the register's header or `audit/artefacts/ENV/`: T02, T05-T10.

- [ ] **ENV.T01** (per session) Build the toolchain (`uv run toolchain/setup_toolchain.py`; skip when
      `setup_toolchain.py test` passes); note sandbox egress limits (CLAUDE.md: `astral.sh`;
      BACKLOG.md:630: `deb.debian.org`); build and verify **both** Unix-port variants
      (`hasattr(sys, "settrace")` False for `build-standard`, True for `build-settrace`) so no agent later
      triggers a rebuild.
- [ ] **ENV.T02** (once) Baseline run of every tier listed in 1.2, serialized under the port lock (4.4);
      record counts (files, tests, pass/fail), wall clock, coverage per `src/` file, lint/typecheck
      finding counts (expected 0), npm results. `uv run pytest tests_hardware --collect-only` only after
      `HW.T14`'s owner confirmation.
- [ ] **ENV.T03** (per session) Reference corpus: reuse `$PICO_TOOLCHAIN_DIR/micropython` (already at
      `v1.29.0` with the rp2 submodules: `extmod/asyncio`, `ports/rp2`, `lib/lwip`, `lib/cyw43-driver`)
      read-only; clone only Microdot `v2.6.2` into the scratchpad.
- [ ] **ENV.T04** (per session) Re-extract datasheet text (`uv run --with pypdf
      audit/sweeps/extract_datasheets.py <scratchpad>`); list missing datasheets (seed `SENS.S20`).
- [ ] **ENV.T05** (once) Apply 4.4's non-interference rules: lock files, worktree per executing agent,
      toolchain copy policy.
- [ ] **ENV.T06** (once) Measure `disallow_any_explicit` counts per pass (BACKLOG's figures are dated
      2026-09-11) as a baseline only — enabling it stays a separate owner-deferred session.
- [ ] **ENV.T07** (once) Build the do-not-reopen index (`DOC.T14`) and the cross-reference resolver
      (`DOC.T02`) before wave 1, committed under `audit/`.
- [ ] **ENV.T08** (once) Record the audit baseline SHA (`main`'s head at go-ahead, owner 3.1) in the
      register header; anchors in this file resolve at the planning baseline (`git show 4dc80ef:<path>`;
      `git fetch --unshallow` first if `.git/shallow` exists). If `main` moved past `4dc80ef`, first repeat
      V11's move (`reanchor.py`, `harvest_check.py`, `baseline_fates.py`, a delta harvest) to the new SHA.
- [ ] **ENV.T09** (once) Commit `audit/sweeps/packet.py` (auditor packet, 4.4) and
      `audit/sweeps/owner_of.py` (file → owning area from 5.0, for delta passes).
- [ ] **ENV.T10** (once) Commit the plan validators (`audit/sweeps/validate_plan.py`: V1 ownership, V3
      anchors in bounds, V4 ID uniqueness) and extend V3 from bounds to content where an anchor quotes
      text (planning found an in-bounds wrong anchor: BACKLOG.md:575 for :555 at `0615eba`) — the harvest
      already has that content check (`audit/sweeps/harvest_check.py`).

### 4.7 State and resumption

- **All state lives in git on the audit branch.** Nothing needed to resume may live only in a session's
  context, the (session-specific) scratchpad or a subagent report. The arbiter commits after every
  arbitration batch (if PQ2 authorises autonomous commits).
- **Resume procedure**:
  1. `git fetch origin`; check out the audit branch named in the register header (before the register
     exists: the branch the owner names at go-ahead). `git fetch --unshallow` if `.git/shallow` exists.
  2. Read CLAUDE.md, this plan (3.1 included) and the register header. No register means a first start.
  3. Confirm the go-ahead: 3.1 must record it *and* the owner confirms it in this conversation before
     any write. Never touch the board; check BACKLOG.md's "Real-hardware work still owed" (board
     state) and any handover file for a bench sitting in progress by another session.
  4. Take the lease: read the holder's last register commit (date, `Claude-Session` trailer) and confirm
     that session is idle, completed, failed or archived — otherwise ask the owner. Write your session
     and UTC time into the header, commit, push. A rejected push means re-read, never force. Write
     `Released` when stopping.
  5. Delta: `git diff --name-only <audit-baseline>..origin/<branch>` through `audit/sweeps/owner_of.py`;
     queue closed areas in the header; note the changed files for areas that are mid-pass.
  6. Per-session ENV: T01, T03, T04.
  7. If `Awaiting owner` is set, stop. Otherwise continue with the lowest open unit (4.1).
- **Shared docs**: while findings are gathered the audit writes only its own files (`audit/`, this file)
  plus these exceptions: the README "Further reading" entry for the register, this file's status line
  and 3.1, and in-place SEV4 doc-drift fixes if PQ1 allows. Wave outputs and quality artefacts live in
  `audit/artefacts/<AREA>/` until a migration unit moves what is permanent (e.g. TWIN's measure into
  `digital_twin/README.md`). Edits to shared docs happen in migration or fix units, merging both sides of
  any conflict; after any merge run every tier, and after one touching `uv.lock` re-verify the installed
  tool versions against the pins (CLAUDE.md).
- **Moving target**: other sessions push to `main`, this branch's base since 2026-09-25 (during planning
  they pushed to the since-merged feature branch, e.g. `0b7feae`, `3062cc7`, `21560a4`, and the 16
  commits V11 absorbed); they do not edit `audit/` or this file, which exists only on this branch. Auditors read a worktree
  at the audit baseline; every finding is re-verified at HEAD before it is fixed or migrated
  (`re-verified@HEAD`).

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
      layout (legacy, other firmware).
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
      values with a new timestamp (seed `SENS.S08`)?
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
      watchdog before the boot entry's import feasible (8 s budget vs import time; USB/mpremote access)?
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
  callback's actual run time, so latency accumulates; with SCD30's 500 ms base tick, `int(1000/(N+1))*j == 500`
  for N = 3, 7, 9 (`system_service.py:158-159`). The proof's own test re-implements the formula instead
  of reading it (seed `TEST.S06`).
- **XCUT.S07** Dynamic `wrnno = n+1` means a persisted W-code names different tasks on different
  devices/firmware versions and must stay ≤ 127 (`system_service.py:238-239`).
- **XCUT.S08** `[x2]` The FRAM chunk layer logs into the manager's RAM-only logger, not the owner's
  FRAM-backed history as C.7.1 states (`src/asy_fram_manager.py:622, 665-674, 716`).
- **XCUT.S09** A.4's "8 KB ample headroom over SGP40's ~250 B" predates WP1-WP3; ~17 logger/cfgmgr
  chunks on wozi and ~21 on dev now share the chip — never re-summed against 8 KB.
- **XCUT.S10** No `machine.reset_cause()` is recorded anywhere in `src/`, so post-mortems cannot tell a
  WDT reset from a commanded one.
- **XCUT.S11** The supervisor's reboot branch `return`s (`src/system_service.py:251-253`), so `main()`
  and `asyncio.run(main())` finish ~4 s before the reset fires (`buildgen/codegen.py:478, 705-708`):
  webserver, readers and any staged flush stop at once and `main.py` drops to the REPL. The REST reboot
  path keeps the loop running until the reset.
- **XCUT.S12** No `set_exception_handler()` anywhere in `src/` or codegen: an unretrieved exception
  from an unsupervised task (`src/config_manager.py:354`; `src/asy_wifi_service.py:394, 425`) only
  reaches MicroPython's default console print.
- **XCUT.S13** `WDT(timeout=8000)` is `build_system()`'s first statement (`buildgen/codegen.py:381`);
  the constructors after it run unguarded, so a construction-time exception becomes an 8 s WDT reset
  loop before any FRAM logger exists — nothing persisted, `reset_cause()` never read (`XCUT.S10`).
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
  tier reaches it (with `PAR.T08`).
- **XCUT.S15** A legal but near-limit sleep can strand other tasks. asyncio's C `TaskQueue` orders tasks by `ticks_diff()` of their keys (`extmod/modasyncio.c:73-85`), so a key pushed close to 2**29 ms ahead compares as *earlier* than a queued task already overdue by at least the remaining margin; `SENS.S27`'s `sleep_ms(remaining)` (`asy_isl29125_driver.py:619-623`) creates such a key (up to 2**29-1 ms, accepted by `ticks_add()`). The far-future task becomes the heap root and `run_until_complete` waits on it (`extmod/asyncio/core.py:57, 161-177`): tasks woken later get fresh keys and run, but runnable tasks already queued are stranded ~6.2 days — a WDT reset if the supervisor is among them, else a hung-but-alive task (`XCUT.T02`). From source reading only; verify on a 2**30-period Unix build (`XCUT.T25`).
- **XCUT.S16** A filesystem `boot.py` runs before the frozen `main.py` and leaves no watchdog in three ways: if it raises, the frozen `main.py` never runs (rp2 has exit-code handling off, `py/mpconfig.h:1217-1218`, so an unhandled exception returns 0, `shared/runtime/pyexec.h:45-48`, and `main.py` runs only on non-zero, `ports/rp2/main.c:237, 246-247`) — REPL, no watchdog; if it blocks, it blocks before USB is initialised (`main.c:239-241`), so not even mpremote recovers the unit (unverified on hardware); `sys.exit()` in it soft-reset-loops (`main.c:243-245`). A filesystem `main.py`, by contrast, never runs — the frozen one is looked up first (`shared/runtime/pyexec.c:743-752`). `XCUT.T20` names both files together; their consequences differ.
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
  (`GEN.S11`/`GEN.T05`) fails the same way. Inventory: `PAR.T08`; consequence: `XCUT.T20`.
- **XCUT.S18** (low) Upstream `_boot.py` formats the whole littlefs if mounting raises for any reason (bare `except:`, `ports/rp2/modules/_boot.py:8-12`, v1.29.0) — before the watchdog and silently: every `config_*.cfg`, Wi-Fi credentials included, is lost, nothing is logged (no FRAM logger yet), and the unit boots into hotspot mode where `PAR.T06`'s permanent-deactivation hazard applies. A littlefs region that changed size between 1.26 and 1.29 would take this path on migration (with `PAR.T06`, `PAR.T09`, `XCUT.T24`).

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
      corrupt JSON vs wrong type) and whether each may overwrite user config with defaults.
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
      after a post-hook exception; unused catalogue codes.
- [ ] **CORE.T08** `Lockable`/`LockableBuffer`/`Locked*`: does any `Locked*` critical section contain
      an `await`? If none, each lock is pure cost under cooperative scheduling — justify, document or
      drop; swallowed `RuntimeError`; unused per-buffer locks; clamping.
- [ ] **CORE.T09** D.15 method ordering, D.6 typing, D.11 comments, D.10 shapes across the five files.
- [ ] **CORE.T10** Dead/test-only API (seed `CORE.S14`): keep, trim or document — each is frozen
      bytecode on the device.
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
  user config on a transient boot failure (`src/config_manager.py:407-426, 459`).
- **CORE.S03** Errors logged before a logger's `setup()` are overwritten when `_read()` restores the
  FRAM ring (e.g. SYSTEM's `_apply_level` errno 7 during `sysfunct.setup()`, before SYSTEM's
  `pr.setup()` runs in `start_and_check_tasks`) — but survive on first boot, so behaviour is
  inconsistent (`src/print_log.py:173-176, 273-277`).
- **CORE.S04** `reset()` during an in-flight `setup()` read restores the old ring into RAM while FRAM
  is cleared (`print_log.py:213-223` vs `:273-277`).
- **CORE.S05** No per-module serialization of `_set_dict_cfg`'s sequence; a failed push in one PUT can
  make `_recover_failed_push` persist its pre-write snapshot over another PUT's accepted value
  (`src/base_classes.py:302-358`).
- **CORE.S06** A post-hook that raises after fields were persisted and pushed yields code 100 with an
  empty result, and the webserver then marks every field "Failed" (`src/api_response.py:92-105`;
  `src/asy_webserver_service.py:463-470`).
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
  (`config_manager.py:319, 330`).
- **CORE.S12** `get_int_values()` uses `int()`, silently truncating a float field or converting a bool,
  unlike `get_bool_values()`'s strict check (`config_manager.py:282-289`).
- **CORE.S13** Small: `Lockable.__aexit__` swallows `RuntimeError` on double release
  (`base_classes.py:47-50`); comment claims `pr.name == name` in the `logger=` branch without enforcing
  it (`:163-171`); `get_log()` reports ErrNum 128 for a raw 0x80 entry (`print_log.py:189-191`);
  `errno=0` counts but never persists (`:161-166`).
- **CORE.S14** Production API with no `src/` caller: `api_response.parse_cmd_request` (webserver
  re-implements it as `_body_as_dict`, a Part G duplicate), catalogue codes 2-5, `ok_descr`,
  `SystemService.get_debug_level`/`set_debug_level`/`stop_uptime_timer`, `LockedFlag`,
  `type_or_range_error(check_special=)`, `SensorReader(logger=)`.
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
      (UART defaults to `Framing_Pass`) — keep, test-only, or document.
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
      deliberate; the D.10 note is current.
- [ ] **BUS.T08** Unused public API (frozen bytecode that must still meet its bus contract): UART
      beyond `readinto_until_complete`/`writefrom`; I2C `scan`, `writeto_then_readfrom`,
      `write_then_readinto`; SPI `write_readinto` and the async transfers — keep, trim or test.
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
      cached values with a new `TS`?
- [ ] **SENS.T05** Interrupt semantics: SCD30 RDY fallback counter, ISL29125 INT thresholds vs the
      decision rule, soft-IRQ allocation, IRQ storms.
- [ ] **SENS.T06** Bus-time budget on `dev`'s shared i2c1 (SCD30 50 ms sleeps under the bus lock vs
      SGP40's 1 Hz cadence vs ISL29125 cycles); VOC processing time on target.
- [ ] **SENS.T07** NVM wear: every SCD30 persistent setter and who can trigger it (REST, loops, tests),
      incl. whether "Unchanged" writes are skipped as legacy did (seed `PAR.S02`).
- [ ] **SENS.T08** Part C conformance and D.10 across the four: constructor shape, snapshot-read
      failure logging, errno allocation, operating-range gates, `@web`/`@limits`/`@requires` tags.
- [ ] **SENS.T09** Unverified protocol assumptions: SCD30 reading back 0x0010
      (AmbPres/continuous-measurement command read-back — A.4's AmbPres note, with `PAR.S02`), SGP40
      serial word[0] `== 0x0000` (`SENS.S06`, `SENS.S21`).
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
      (with `XCUT.T07`).
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
  (`asy_sgp40_driver.py:614-615`).
- **SENS.S08** SCD30 `scd_timer_triggers` accumulates across cycles (comment says "consecutive") and
  forces a read even when RDY is low; the not-ready read leaves the cache untouched and `_read_scd`
  re-stamps cached values as fresh — legacy-identical (`src/asy_scd30_driver.py:174-187, 412-420, 610-611`).
- **SENS.S09** SCD30 `int(offset*100)` truncates 0.01 K low for ~6.5 % of 0.01-step values in float32
  (0.53 → 52, 1.05 → 104) (`asy_scd30_driver.py:570`) — A.4 documents truncation as deliberate; the
  float32 representation effect is the new part.
- **SENS.S10** SCD30 has no CO2/RH/T plausibility gate (datasheet 0-40000 ppm), only finiteness, though
  C.3 says operating-range checks live in layer 2 (`asy_scd30_driver.py:621-630`).
- **SENS.S11** SCD30 sleeps 50 ms inside the bus lock per command/register read; `get_config_snapshot`
  holds i2c1 ≥ 6×50 ms (`asy_scd30_driver.py:471, 483, 514-520`).
- **SENS.S12** BMP3xx `MeanAtmTemp` accepts −50..50 but `altitude_baro` requires −40..85, so [−50, −40)
  silently yields `SLPres = None` (`src/asy_bmp3xx_driver.py:84`; `math_helpers.py:25-26, 92`).
- **SENS.S13** BMP3xx plausibility gate runs before `PressOffset` (±500 hPa) is applied, so a published
  `Pres` can leave the datasheet range and `SLPres` becomes `None` with no log
  (`asy_bmp3xx_driver.py:237`).
- **SENS.S14** BMP3xx `get_altitude()`/`get_pressure()`/`get_temperature()` have no production caller
  (`asy_bmp3xx_driver.py:555-577`).
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
  egress policy, OR4.a). Added 2026-09-25: BMP390, WS2812, W25Q16JV, CYW43439 and RP2040 datasheets; the VOC C reference is reachable at `Sensirion/gas-index-algorithm`.
- **SENS.S21** The SGP40 serial-number read fetches 3 of the 9 bytes the datasheet specifies
  (`readlen=1`), so only word 0 is CRC-checked and compared (`asy_sgp40_driver.py:673-682`; datasheet
  3.4, Tables 8/16).
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
  the other episode flags (WIFI per connect episode, NTP until a sync) for one shared meaning (`XCUT.T07`).

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
      (`STOR.S07`); interplay with `XCUT.T13`/`CORE.T06`.
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
  kept (`src/asy_fram_driver.py:357, 400`; BACKLOG.md:52) — record as settled-no-action.
- **STOR.S06** `FRAM_SPI`'s `wp_pin` path is unreachable in production (`AsyFramManager` never forwards
  it, `asy_fram_manager.py:628`; codegen emits only `max_size`/`debug`, `buildgen/codegen.py:203`) and
  treats the pin as whole-array protection (`asy_fram_driver.py:217-220`), while the MB85RS64V WP pin
  only guards the status register when WPEN=1.
- **STOR.S07** No `src/`/`buildgen/` code passes `override_pause=True`; the parameter on every chunk
  method is test-only API (`asy_fram_manager.py:96, 128, 389`).
- **STOR.S08** An out-of-memory FRAM allocation is reported only through print-only `pr.err`
  (`asy_fram_manager.py:649, 662, 691, 704`; `asy_sgp40_driver.py:187`): a layout overflowing 8 KB
  (`XCUT.S09`) silently drops owners to RAM-only with nothing persisted.

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
      `_ready()` flooding, repeat-counting vs C.7.1.
- [ ] **UART.T05** Construction validation (timeout floor, rxbuf floor) vs buildgen's own checks
      (`GEN.T01`, L.6.6).
- [ ] **UART.T06** `UartLinkExerciser` (bench-only): counters, supervision, FRAM wiring, whether its
      failure modes can pollute the persisted log at 1 Hz.
- [ ] **UART.T07** `UART_C_PORT_CHANGELOG.md` completeness vs git history of `asy_uart_comm.py`, and
      whether a "temporary" file with no reachable deletion trigger should be reclassified (touches
      SETTLED, see `DOC.S14`) (seed `DOC.S14`).
- [ ] **UART.T08** End-to-end delivery semantics: a lost final ACK makes the initiator report failure
      after the responder already delivered the SET / ran `get_callback` — at-least-once with caller
      retries, at-most-once without. What does Part J promise; must commands be idempotent?
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
  `:158-175`, which does count repeats).
- **UART.S02** A GET frame's `CHUNKS=1` is not enforced (`asy_uart_comm.py:484-488`) though J.4 defines
  a GET as a one-chunk train.
- **UART.S03** Dedupe keyed only on the last errno, cleared by every valid frame: a link alternating
  good/bad or between two errnos persists on every fault (`:319, :658-661`); `_ready()` calls `err_s` on
  every call, so a failed `setup()` plus the exerciser's 1 Hz `uart_get` persists an entry per second
  (`:351-355`; `src/asy_uart_link_driver.py:110-120`).
- **UART.S04** The `dev` link runs with `CRC_Pass`: codegen never passes `crc=`
  (`buildgen/codegen.py:396-397`) — a corrupted payload byte is caught only structurally. Enabling CRC
  alters emitted bytes — Class A, owner decision, changelog entry.
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
  (`src/asy_dns_client.py:20, 110`).
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
  `buildgen/codegen.py:607`).
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
      owned by `XCUT.T11` (with `CORE.T04`, `CORE.S06`).
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
      on routine idle/aborted connections vs FRAM ring churn.
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
  leaves a partial reset and a 500; no confirmation for an irreversible evidence wipe (`:631-637`).
- **REST.S05** WEBSERVER `wrn_s` calls never pass `repeat=`, so every idle/reclaimed connection
  (browser speculative preconnects) spends a FRAM ring slot; same for DNSSRV (`:254, :715-724`;
  `src/captive_dns.py:119, 123`).
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
  yields `"Invalid"`; H.6 reserves Invalid for structurally wrong payloads (`asy_webserver_service.py:533-566`).
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
      (buildspec itself is SETTLED as hand-maintained).
- [ ] **GEN.T07** `pico_gpio.py` legality table vs RP2040 silicon (e.g. GP22/GP28 functions; RP2040 datasheet's function-select table) — is the
      conservatism intended?
- [ ] **GEN.T08** `devices/*.toml`: values vs legacy pinning per unit, `SensorStation<Name>` rule,
      shared hotspot password (accepted-risk rule: not to be "fixed" without the owner's direction),
      `timeout`/`frequency` vs `@requires`.
- [ ] **GEN.T09** (root cause shared with `WEB.S13`) `definitions.py`: ordering vs codegen, string
      `specialValues`, UTF-8 byte bounds, NaN/inf defaults, `defaultValue` kind check, display identity
      (file stem vs `SensorStation`).
- [ ] **GEN.T10** Static/compile coverage of generated artefacts: `build/generated_src/*.py` is outside
      ruff scope and mypy reports nothing there (`follow_imports = "silent"`); fixture outputs are only
      `ast.parse`d, never compiled by MicroPython nor run (`GEN.S01`'s class). Decide ruff + mypy over
      generated output and an `mpy-cross`/Unix-port compile of every fixture's output (with `TEST.T09`).
- [ ] **GEN.T11** Determinism: same TOML + `src/` → byte-identical module/definitions/wiring plan
      (except `build_date`) across `PYTHONHASHSEED`s and host CPython 3.11-3.13 (with `SCR.T11`).
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
  follow-imports with `build/generated_src` on `mypy_path`) plus `scripts/lint.sh:13` (ruff scope).
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
      1.26 → 1.29 reflash (seed `PAR.S10`).
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
      vendored `ext/freezefs/`), MicroPython's embedded version/date, distro GCC.
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
- [ ] **CI.T08** Config-file comment cap: which config files are in the swept set (PQ6).
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
  `ci.yml:617-618`; question is only whether the message is acceptable.
- **CI.S10** Comment blocks over 3 lines in files outside CLAUDE.md's swept config list: `.gitignore`
  (from lines 27, 33, 75, 84), `tsconfig.json` (11, 29), `tsconfig.node.json` (2, 17); `.gitignore:75`
  still names the retired `run_wozi_integration.py`.
- **CI.S11** `ci.yml:13-15` + `:38-41` together may skip the web tier permanently for a change whose
  run was cancelled (confirm dorny/paths-filter's push semantics first).
- **CI.S12** The web-coverage run's test result is advisory (`ci.yml:226-228`).
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
      `validateDefinitions` strictness vs H.4's claim, degraded `/status` sources.
- [ ] **WEB.T06** Build: bundle order, import stripping, duplicate exports, inlining/escaping, the
      staging test's bite.
- [ ] **WEB.T07** Accessibility: ids, labels, drawer focus/inert, contrast (light and dark),
      colour-only information, password inputs, `color-scheme`, reduced motion.
- [ ] **WEB.T08** Security: no-`innerHTML` rule enforcement, selector injection, CSRF/DNS
      rebinding/clickjacking posture (PQ5), password `autocomplete`.
- [ ] **WEB.T09** First define the browser floor (owner input, PQ10), then check it vs features used
      (media-range syntax, `replaceChildren`, private fields, `??=`).
- [ ] **WEB.T10** (owned by `TEST.T10`) Test coverage: live PUT matrix per device (dev/ISL29125), live
      tests that skip-and-pass without the toolchain, runtime DOM validation.
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
  (`tests_scripts/test_buildgen_definitions.py:40-69`).
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
  version nor build date is rendered") — doc contradiction owned by `DOC.T10`.
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
      the mutated function, on tmpfs/scratch; ENV estimates and records the total run count first.
- [ ] **TEST.T03** `gc.collect()` and absolute heap bounds in tests/twin vs CLAUDE.md and E.8;
      root-cause any `MemoryError` a manual collect is hiding.
- [ ] **TEST.T04** Timing sensitivity: wall-clock bounds under parallelism, fixed sleeps, unbounded
      `asyncio.run()` helpers.
- [ ] **TEST.T05** (owns the mock↔twin divergences; `TWIN.T02`/`TWIN.T12` cite it) Mock ↔ twin semantic
      divergences (reset returns vs raises, WDT validation, `Pin.init` pull, IRQ edges, `scan()`, RTC
      set return).
- [ ] **TEST.T06** Meta-tests: which CLAUDE.md rules are machine-enforced vs review-only; propose
      guards for review-only ones (four-tier bus-hazard rule, nested `asyncio.run`, port/scratch-key
      disjointness, `ALL_CHECKS` completeness, `gc.collect()` in tests/twin).
- [ ] **TEST.T07** Shared mutable class-level state across tests in one process + dict-order execution.
- [ ] **TEST.T08** Duplication of helpers (raise-on-arm context managers, `run()`, `_wait_until`).
- [ ] **TEST.T09** (with `GEN.T10`) Coverage: generated modules untraced; E.5.1's false-negative
      categories re-checked.
- [ ] **TEST.T10** (owns `WEB.T10`) `tests_js/`: live tests' skip behaviour, fixture reliance on
      hand-written definitions, mock-only coverage for dev fields.
- [ ] **TEST.T11** Private-attribute coupling in tests: count SLF001-style accesses per `src/` module
      and decide whether the refactor-fragility cost is accepted.
- [ ] **TEST.T12** Runner-level vacuity: an `async def test_*` counts as PASS without running; a file
      without the footer prints nothing and exits 0; a `BaseException` mid-file aborts the rest — a
      meta-test for all three.
- [ ] **TEST.T13** `tests_scripts/` quality: tests touching the real tree (`devices/zz_test_*`), no
      per-test timeout (only the suite-wide 1200 s), no order randomisation, real firmware build
      CI-only.
- [ ] **TEST.T14** `tests_js/` determinism and isolation: `installMockFetch` leaks between tests,
      `Math.random` in the mock, fixed ports 19420/19481/19482, shared `digital_twin/config`.
- [ ] **TEST.T15** Behaviour × tier matrix per `src/` module (mock, twin, host, web, hardware),
      extending E.6.5: risky behaviours covered by one tier or none.
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
      it as knowingly outside the rule (with `SCR.T01`, `TEST.T06`, `HW.T05`).
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
      retire a guard to save effort (OR12).

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
  `src/system_service.py:159`).
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
  at retention or fragmentation.
- **TEST.S12** Absolute heap bounds against E.8's "a leak is a rate"
  (`tests/test_asy_webserver_service.py:1833`; `tests/test_digital_twin_uart_link.py`
  `_hammer_with_the_graph_running`).
- **TEST.S13** Coverage traces `src/` and `digital_twin/` only; generated `sensortask_*.py` gets none.
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
  (`tests/test_reset_call_site_invariant.py:7-11, 24`).
- **TEST.S18** Duplication: 7 copies of the Timer raise-on-arm context manager; 47 local `run()`s; 20
  files with their own `run_timed`/`_wait_until`/`_cancel`.
- **TEST.S19** Live PUT matrix covers wozi only (`tests_js/live-backend-put-matrix.test.js:58`); live
  tests skip-and-pass without the toolchain (`tests_js/live-backend.test.js:13-16`).
- **TEST.S20** Only ISL29125 has a C.11.1 conformance probe; SCD30, SGP40, BMP3xx and FRAM fakes have
  none and nothing requires one.
- **TEST.S21** E.1 says TCP port bases lie in 17400-19999, but `_webserver_concurrency_scenarios.py:77`
  allocates `19700+200*i`, reaching 20700+.
- **TEST.S22** The comment-cap gate counts physical lines, and E501 is ignored, so a docstring can pack
  a paragraph onto one 400-700-character line and pass (`digital_twin/_fault_injection.py:3`,
  `digital_twin/run_generic_integration.py:1-2`,
  `tests/test_digital_twin_run_generic_integration.py:1-2`, `buildgen/twin_wiring.py:1-2, 35-36`,
  `scripts/_digital_twin_ci_suite.py:5-7`, `scripts/_render_coverage.py:6-7`) — owner decision on a
  character bound (PQ6).
- **TEST.S23** `tests/microtest.py:17-28` counts a test as PASS whenever the call raises nothing: an
  async test would pass without running; a file with no footer exits 0 and `test.sh:374-376` records
  PASS; no instance today, nothing guards against it.
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
      `_unix_port_udp_addr_shim.py`) — still needed after the root-cause fixes?
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
      availability, raw-REPL side effects (stops `main.py` → WDT reset ~8 s later).
- [ ] **HW.T07** Bench-rig facts vs docs: desk review only compares the docs with each other (MPRLS on
      i2c0? FRAM part number on dev); which version is physically true becomes a real-hardware entry (a
      bus scan), never settled from the docs.
- [ ] **HW.T08** Hardcoded pins/timeouts/addresses in device scripts vs `devices/dev.toml`.
- [ ] **HW.T09** Structural-exception claims (E.6.6, C.8, `tests_hardware/README.md` tenth pass)
      re-derived from source.
- [ ] **HW.T10** Real-hardware entry hygiene (the queue and handover are folded into BACKLOG,
      `03f8bcf`): owner decisions filed as hardware work (F18, T4, W3, T1 — `DOC.S28`), retired row IDs
      still cited from permanent code as "queue <ID>" (`DOC.S06`), entries that state board state which
      only holds until the next sitting (BACKLOG.md:352-360).
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
      `AsyFramManager` over production's first chunks)? If not, ask the owner whether one is wanted.
- [ ] **HW.T18** Re-base HW desk findings on the 2026-09-24/25 sitting, which finished before the
      baseline: two clean default bench tiers, one clean wear-gated run (128 passed), R1/R4/R5/R6/R7/T2/
      W3/W4/W5/F1/N2/G3/G8/G12 closed or measured (`851e816`..`a9c8627`; Appendix B). Seeds written
      before it (`HW.S09`, `HW.S15`) are updated; any later sitting another session runs is folded in the
      same way.
- [ ] **HW.T19** Image identity: can a run know which tree the board's image was built from? The image
      carries only hand-bumped versions (`buildgen/version.py:7-8`) and a build date (`buildgen/codegen.py:
      351, 603`) — no commit, no dirty flag; device scripts run against whatever frozen `src/` is on board
      (`tests_hardware/harness.py:440-447`); `configured_max_connections()` "describes the TREE, not
      necessarily the image" (`harness.py:40-41`). Propose a checkable identity (commit + dirty flag in
      `build_info`, verified before a run) or record the gap (with `HW.T16`, `GEN.T14`, `PAR.T06`).
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
  `WDT(8000)` and feeding it from a 2 s `Timer` (`tests_hardware/README.md:383-385`); BACKLOG.md:720-727
  asks the owner to fold that in or keep the wrapper, and whether stale `config_HWTEST_*.cfg` files left
  on the board by earlier scripts should be removed on exit. See Appendix B for whether the script is
  still needed at all.
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
  RAM-only; CLAUDE.md:367-376 says they joined the FRAM-backed set.
- **HW.S24** `manual/manual_wifi.py:19, 30` hardcode the hotspot password `12345678`; the source of
  truth is `devices/dev.toml:7` (`HW.T11` consistency).
- **HW.S25** `role_reversal` (and `over_provisioned_image`) are informational markers, not gates
  (`tests_hardware/conftest.py:111-113`), and `run_bench_hardware_suite.sh:11` excludes only the soak
  markers — so the role-reversal scenario, with its documented stage-6 permanent-WLAN-deactivation risk
  (`HW.S10`), runs in every routine bench pass. Should it become a gate?

- **HW.S26** `flash/test_watchdog_starvation.py`'s two tests differ in oracle and style: the G3 test
  (`:54-78`) asserts `reset_cause() == WDT_RESET` through a hardcoded `_WDT_RESET = 3` (`:51`, a mirror of
  `machine.WDT_RESET` no test pins), the original (`:16-47`) asserts no reset cause; both end with the
  same closing `hard_reset()` (`:43-47`, `:75-78`), duplicated rather than shared (OR24).
- **HW.S27** New device-script facts held only locally: `uart_driver_read_never_blocks_the_loop.py:27`
  `POLL_WAIT_MS = 2` "mirrors sensortask_dev.py's own transaction rate" (a generated value, `HW.T08`);
  `reboot_fallback_starves_the_watchdog.py:24` loops to 64 "the real pool is small and fixed" while the
  measured pool is 16 (`79423dd`, commit message only — a platform fact for Part F, OR29).
- **HW.S28** Two fixes are "not yet confirmed on silicon" (BACKLOG.md:361-366): SGP40 `W13`'s one slot
  per outage needs NTP blocked past `SGPWaitTimeNTP` (default 30 backups, ~30 min, `asy_sgp40_driver.py:53`);
  the flash tier's closing `hard_reset()` needs a full flash-tier run. Both are logic already pinned by
  unit tests (`tests/test_asy_sgp40_driver.py:1068-1128`) or by the test itself (Appendix B).

Quality measure: desk findings resolved or moved to BACKLOG's real-hardware section; every
silicon-needing check is an entry there with flags and wear stated.

---

### 5.19 SEC — Security threat model (cross-cutting)

**Goal**: an explicit threat model (PQ5) and every exposure classified against it — defect, accepted
property (with the owner's decision recorded), or out of model.

Topics:
- [ ] **SEC.T01** Write the threat model: actors (LAN peer, browser page on the LAN via DNS rebinding,
      radio-range attacker in hotspot mode, local user on the dev/bench host, supply chain), assets
      (availability, config, FRAM evidence, flash/NVM endurance, credentials).
- [ ] **SEC.T02** Unauthenticated write surface: `SystemCmd` (`bootloader` = offline until physical
      intervention; `reboot`; `mempause`), `ResetErrors` (irreversible evidence wipe), SSID/PW changes,
      every config write (flash/NVM wear by alternation).
- [ ] **SEC.T03** Browser-borne attacks: CSRF (blocked by JSON content-type + no CORS?), DNS rebinding
      (no Host check), clickjacking (no X-Frame-Options/CSP).
- [ ] **SEC.T04** Radio-range: shared default hotspot password in all 6 TOMLs (accepted-risk rule in
      CLAUDE.md), captive DNS spoofing, bogus-SSID → hotspot → second streak → permanent WLAN
      deactivation (A.4 intentional; a remote DoS needing a power cycle).
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
      `mempause`/`reboot` (`XCUT.S03`), flash wear by alternating PUTs, stdout stalls (`REST.T13`).
- [ ] **SEC.T10** Information exposure and outbound traffic: what unauthenticated GETs reveal (SSID,
      hostname, versions + build date, full error histories) and every outbound destination (DHCP DNS,
      8.8.8.8/1.1.1.1 `NET.S04`, NTP host) — disposition each under PQ5.
- [ ] **SEC.T11** Trust in time and names: spoofed NTP → RTC, `TS`, FRAM backup age, notification
      window; spoofed DNS → NTP at an attacker's host; DNS id entropy (`os.urandom(2)`) and source-port
      predictability (`LWIP_RAND`) (with `NET.T03`/`T04`, `STOR.T09`).
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
      (`TEST.S11`, `TEST.S12`).
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
- [ ] **PERF.T01** Watchdog: worst-case feed gap (XCUT.T03).
- [ ] **PERF.T02** HTTP capacity: ~2.2 requests/s saturation, `max_connections` 6, slot release lag, UI
      polling rates, hidden tabs, no caching of static assets.
- [ ] **PERF.T03** `ResetErrors` sweep cost vs `outer_cap_s` and the UI timeout (BACKLOG 24/32 — R2
      measured 2026-09-25: the curve does not flatten, ~+3.5 s per reader, 88-98 % of the cap at 3
      readers; F18 at 4 — budget and design fix are the owner's; R4 the same day: every populated log
      read back 0 at three readers in 14.58 s, and the UART exerciser's `E20`/`E22`/`W10` start at three).
- [ ] **PERF.T04** Bus budgets: SCD30 50 ms sleeps under the bus lock, probe sleeps, FRAM block hold
      (~21 ms), SPI re-init per CS, VOC processing cost, CRC per-byte yield.
- [ ] **PERF.T05** Lock-hold stalls in networking (60 s sleep, 5 s connect poll, ~6.5 s NTP attempt) —
      owned by `NET.T02`; PERF records only the budget.
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
      location, "same" / "changed-documented" / "changed-undocumented" / "missing".
- [ ] **PAR.T02** Device mapping: legacy `arzi`/`neu`×3/`wozi`/`dev` → `devices/*.toml` pins and
      options.
- [ ] **PAR.T03** A.4 "confirmed intentional" behaviours still hold, one by one.
- [ ] **PAR.T04** Timing parity: supervisor period/reset delay, UI poll interval, LED sleeps, NTP
      retry.
- [ ] **PAR.T05** External REST consumers (scrapers, home automation) of the legacy routes — owner
      input.
- [ ] **PAR.T06** Migration on reflash: stored `config.json` → per-module `.cfg` (never read), legacy
      FRAM contents under the new layout, littlefs region size across 1.26 → 1.29, hostname change and
      DHCP reservations, SCD30 NVM survival, first-boot hotspot → permanent-deactivation hazard.
- [ ] **PAR.T07** Whether a reflash runbook (or a first-boot migration/format step) is wanted (PQ10).
- [ ] **PAR.T08** Filesystem residue at reflash: what a legacy unit's littlefs holds (`config.json`,
      `boot.py`, `main.py`, `*.py`, `*.mpy`; dev snapshot at `dev_legacy/README.md:667`+) and whether
      any of it can run before, or shadow, the frozen refactor `main.py`/modules (`sys.path` order `''`
      vs `.frozen`; `pyexec` lookup in `ports/rp2/main.c` at 1.29.0) (with `PLAT.T10`, `XCUT.T20`).
- [ ] **PAR.T09** Frozen-set and boot parity: legacy `python/Manifest/manifest.py` + frozen `_boot.py`
      vs the refactor's frozen set + `main.py`; mount/format behaviour on a filesystem the legacy build
      wrote (with `PAR.S10`, `TOOL.T06`).
- [ ] **PAR.T10** Web UI parity: every control, display and client-side bound in legacy
      `html_raw/{arzi,wozi,general}` mapped to the new UI or recorded as deliberately dropped
      (`PAR.S05`, `PAR.S07`, `WEB.S20`).
- [ ] **PAR.T11** HTTP behaviour across the Microdot jump (untagged ~2.0.x → v2.6.2) and 1.26 → 1.29:
      status codes for unknown routes/methods, error bodies, keep-alive, HEAD; legacy `api_helpers.py`
      codes 1-10 (e.g. 8 "LED busy", `REST.S09`) vs `api_response`'s catalogue.
- [ ] **PAR.T12** Published-value parity per sensor: from the same raw bytes, do legacy
      `python/IndividualDrivers/*` and `src/` publish the same numbers (scaling, rounding, offsets,
      filters, compensation, `None` on failure)? Desk comparison; running legacy code as an oracle needs
      the owner's permission (PQ10).
- [ ] **PAR.T13** Physical unit ↔ `devices/*.toml` mapping (L.1 names the three "ArZi neu" units);
      legacy `dev` recorded as not a parity target.
- [ ] **PAR.T14** Rollback path: if a reflashed unit must go back to the legacy 1.26 build, what does legacy
      do with the refactor's state — leftover `config_<NAME>.cfg` and a missing/stale `config.json`, the
      refactor's FRAM layout read through legacy's chunk/timestamp/status logic
      (`python/IndividualDrivers/asy_fram_manager.py:50-110`) as SGP40 VOC state, SCD30 NVM values the
      refactor wrote, and can 1.26 mount a littlefs last written by 1.29? Feeds `PAR.T07`.
- [ ] **PAR.T15** Is the parity baseline right? `PAR.T01` assumes `python/`, `modules/`, `html_raw/` at HEAD
      are what each field unit runs; the legacy build exposes no version/build ID and this checkout is
      shallow. Establish which source state each unit runs (owner input, PQ10) before any row is scored
      "changed-undocumented".

Seeds:
- **PAR.S01** `WaitTimeNTP=0` disables the VOC restore entirely; legacy restored once, immediately; the
  web label "Never wait for NTP sync" implies the legacy meaning (`src/asy_sgp40_driver.py:53, 64, 356-359`).
- **PAR.S02** `[x2]` SCD30 PUT calls every setter unconditionally; legacy wrote only when the value
  differed from the readback (or forced `AmbPres`) — NVM wear and repeated `ForceCalRef` recalibration
  (`src/asy_scd30_driver.py:257-298` vs legacy `api_helpers.py:192`).
- **PAR.S03** SGP40 resets `voc_write = WaitTimeNTP` after every stamped write, so each later backup
  waits for NTP again; legacy set it to 0 for good (`asy_sgp40_driver.py:431-441`).
- **PAR.S04** `[x2]` Supervisor: check period 3 s → 2 s (decay 1.5× faster), reset delay 5 s → 4 s,
  explicit `reboot_system()` instead of watchdog starvation; A.2 (SPECIFICATION.md:124-125) and I.4(d)
  (:5009-5010) still say "stops feeding the watchdog"; BACKLOG asks for the supervisor change "without
  changing observed behaviour".
- **PAR.S05** `/system`'s build info exists but no UI renders it (see `WEB.S20`).
- **PAR.S06** Wire changes are documented as deliberate (six routes, sparse PUT, native bool/null,
  `BMP388` → `BMP3XX`, oversampling as values not indices, `Led` prefix dropped) — but old bookmarks
  (`/sensorconfig.html` etc.) now 404; confirm acceptable.
- **PAR.S07** UI measurement poll 2 s → 3 s (definitions `landingSection` poll 3000 ms).
- **PAR.S08** Config migration: nothing in `src/`/`buildgen/` reads `config.json`; after reflash every
  unit boots with SSID `""` → hotspot; if nobody joins within the hotspot window, the second streak
  permanently deactivates WLAN until a power cycle. BACKLOG #2's "avoids this structurally" covers
  key-adding updates, not this transition.
- **PAR.S09** Legacy FRAM chunk 0 (SGP40 VOC state, no CRC, 248 B) sits where the refactor's first
  chunk now lives; expect CRC/status errors on first boot that seed misleading errcount entries (see
  CLAUDE.md's FRAM-evidence rule); VOC baseline lost (45-sample relearn).
- **PAR.S10** The littlefs region must survive a 1.26 → 1.29 swap (`MICROPY_HW_FLASH_STORAGE_BYTES`
  equal on both; B.14.3) — unverified.
- **PAR.S11** Hostname changes from `"SensorNode"`/user-set to `SensorStation<Name>` (DHCP
  reservations, DNS names, hotspot SSID).
- **PAR.S12** Legacy reboot-looped forever on a failed `fram.setup()` (WDT starved); the generated
  `build_system()` ignores `setup()` results — an undocumented, probably-better change (legacy
  `modules/sensortask-wozi.py:570-573, 604-606`).
- **PAR.S13** CLAUDE.md says the refactored wozi is "never physically flashed"; if the fielded wozi
  unit is ever reflashed, its first real flash is a production one — owner confirmation.
- **PAR.S14** Legacy `modules/sensortask-dev.py:21` carries SHTC3/MPRLS/ISL keys while
  `devices/dev.toml` wires SCD30/SGP40/BMP3xx/ISL29125 — not a parity target (CLAUDE.md: `dev` is a
  bench rig).
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
      row IDs, archive `§`, named sections — and whether a CI lint should keep it that way.
- [ ] **DOC.T03** Reference policy: permanent code citing temporary docs' row IDs (they dangle once
      rows are deleted); ID namespaces that collide visually (`F1` row vs `F.1` Part).
- [ ] **DOC.T04** Archive durability: `12640c2` reachability after merge (PQ2).
- [ ] **DOC.T05** History/narrative vs the current-state rule (tests_hardware README pass sections,
      README provenance paragraphs, CLAUDE.md incident bullets, BACKLOG item narratives, dated stamps).
- [ ] **DOC.T06** One home per fact: duplicated facts across CLAUDE.md/SPEC/BACKLOG/`tests_hardware/
      README.md`; open work scattered over several places (fewer since the queue and handover were folded
      into BACKLOG, `03f8bcf`).
- [ ] **DOC.T07** CLAUDE.md budget (~92 KB auto-loaded): rules vs facts vs narrative; relocation of the
      chroot recipe and "Known … fixed" bullets to SPEC with pointers (PQ6).
- [ ] **DOC.T08** Every dated count/number claim (86/86, ~157, 21 chunks, suite counts) — keep, make
      generated, or make tested.
- [ ] **DOC.T09** Glossary for undefined labels (WP1-WP8, measure A/B, image E6′, S3, sittings).
- [ ] **DOC.T10** Contradiction sweep (seeds below) and terminology drift.
- [ ] **DOC.T11** `DEVICE_REFERENCE.md`: which firmware does it document — the fielded legacy build or
      the refactor after reflash? Check it against that firmware (`LED.S04`, `DOC.S19`).
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
      action" triage needs; built in ENV (`ENV.T07`), kept current by DOC.
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
  point 9 (:2331) says hand-update.
- **DOC.S04** ~77 "archive §" citations resolve only against commit `12640c2`, reachable today only
  from this branch (PQ2).
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
  BACKLOG.md:876 names a nonexistent README section.
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
  — triage "settled — no action" unless the premise is wrong, 2.3)
- **DOC.S15** `update_and_install.txt` is missing from README's "single complete map";
  `dev_legacy/README.md`'s "single source of truth" status vs BACKLOG.md's board-state entry
  (BACKLOG.md:352-360; OR32.a moves the bench content to its canonical homes). The queue/handover
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
  (`modules/sensortask-wozi.py:21`).
- **DOC.S20** More sites of `PAR.S04`'s watchdog claim: BACKLOG.md:334-335 ("the only feed site") vs
  the per-setup-unit feed at `buildgen/codegen.py:465`.
- **DOC.S21** `build-*.sh` status told three ways: BACKLOG.md:876-877 "now fixed too"; B.9
  (SPECIFICATION.md:825-830) and A.3 (:133-134) "not covered"; CLAUDE.md "never gets work" — resolve
  toward CLAUDE.md's reference-only rule, never toward "covered".
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
- **DOC.S27** BACKLOG.md:388-448 keeps A6's FRAM timing script as "its only copy" inside a markdown code
  block: unlinted, untyped, never collected, outside the comment cap and every CI gate. T4's owner
  decision settles it — commit it as a device script under the normal gates, or drop it with the row.
- **DOC.S28** BACKLOG's "Real-hardware work still owed" mixes three kinds: silicon work (M1 + S3b, R13 +
  N3, the two unconfirmed fixes), owner decisions that need no board (F18, T4, W3, T1, the device-script
  loose ends at :720-727) and pointers (:464-469). Under OR5.a the decisions need answers, not a sitting;
  file each where it belongs (`HW.T10`).
- **DOC.S29** One trap of the retired queue's §6 was not carried over: "a REST reboot issued by hand
  strands the DUT in hotspot mode" — kick the AP's stations, then `hard_reset()` (~40 s)
  (`git show 2a88cc8:REAL_HARDWARE_TEST_QUEUE.md`, lines 376-383). Nearest homes: `tests_hardware/README.md:394-395`
  (fallback after a reset or flash) and BACKLOG.md:461-463 (kick-then-reset helper); OR14's "lost"
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
      its contents.
- [ ] **LIC.T05** What actually ships in the firmware image (frozen set) vs what the licence doc lists.
- [ ] **LIC.T06** What the UF2 contains beyond this repo: MicroPython (MIT), pico-sdk and lwIP (BSD-3),
      mbedTLS (Apache-2.0), cyw43-driver (its own licence), freezefs runtime if frozen — any notice
      duty? Only relevant if a UF2 leaves the owner's hands (distribution scope, PQ10).
- [ ] **LIC.T07** `datasheets/` holds vendor-copyrighted PDFs — do their redistribution terms fit the
      repo's visibility (PQ10)?
- [ ] **LIC.T08** Headers vs doc in both directions: every SPDX/attribution header in `src/` has a doc
      entry and vice versa, with matching scope (whole file vs portion).

Seeds:
- **LIC.S01** Two separate `src/asy_isl29125_driver.py` entries (THIRD_PARTY_LICENSES.md:34-39, 46-53);
  l.37 says the legacy copy is listed "below" while l.118-120 says the entry "moved up".
- **LIC.S02** THIRD_PARTY_LICENSES.md:52-53 credits "FRAM-persisted gain-ratio self-calibration"; M.1.5
  and the driver say calibration is RAM-only and user-applied.
- **LIC.S03** (touches SETTLED, see `LIC.T04`) README.md:719-724 calls the doc "every piece of vendored
  … third-party code in one place" without the `arduino/` exclusion sentence (`LIC.T04`).
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
- [x] **V9** At most 10 owner questions (PQ1-PQ10).
- [ ] **V6 Owner review** (last): PQ1-PQ10 answered; the owner declares the list complete (or keeps
      extending it) and gives the execution go-ahead explicitly.

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

**B.1 Real-hardware work still owed (BACKLOG.md:345-469)**

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
| `disallow_any_explicit` (:36-51) | `ENV.T06` | owner | Owner-deferred to its own session; OR5.a allows no open item, so either in scope or a documented limitation |
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
