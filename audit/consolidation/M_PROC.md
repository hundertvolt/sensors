# A-C merge PROC (HEAD 546cdd8)

Cluster PROC: the 81 actions whose Site names no repo file the site index parses (CLUSTERS.md "## PROC"). The per-file
method is applied per procedure: the 81 actions are grouped by the procedure or moment they belong to, and each group
gets one merged procedure (ordered steps, unit or moment, preconditions, products and their consumers, gates). Each
action was read in full (`audit/actions/*.md`), with AC_NOTES 1-43, owner rows OR1-OR133 (OR129 verbatim intent;
OR131/OR132/OR133 firm), every finished `M_*.md`'s gaps and ledger rows naming these actions, and the phase-C inventory
H01-H83 (`audit/actions/C.md`).

Three kinds of action sit in this cluster:
- **Procedures** (35 actions): runs, measurements, audit working files, scans, rounds and the close, merged below with
  the owner steps and the gaps other merges handed to PROC or phase C into M.PROC.001-M.PROC.044.
- **Real file edits the index missed** (45 actions): their Site names files without a path prefix the index parses
  (`base_classes.py:…`, "Site and change", `.gitignore`, `legacy/`, `mockdata/`, "SPECIFICATION.md Part N"). 38 are
  already merged by the clusters that own the files (their ledger rows name the M-IDs; section "File edits carried
  elsewhere", which also names the residual pieces no merge holds yet); four touch paths no cluster owns and are carried
  here (`legacy/` relocation, `legacy/README.md`, `.gitignore`: M.PROC.014, M.PROC.015, M.PROC.019); three are SPEC Part N
  Dependants texts whose test-site tags are merged elsewhere and whose Part N text goes to SPEC (Gaps).
- **Withdrawn** (1 action): A.U24.35.

Every permanent text a procedure writes and every commit message cites no audit ID (G9/R12, AC_NOTES 4); IDs stay in
audit files. Hardware runs only with the owner's go-ahead given in the executing conversation (CLAUDE.md); subagents and
child sessions inherit none.

## P1 — The frame every executing session works in (all units)

### M.PROC.001 Every unit runs inside one non-interference and sync frame
- **From**: A.U0.04 (non-interference rules), A.SDEP.23 (2) (per-action citation re-check as the first step), OR6.a
  (sync point after each unit; cited by A.U37.01), AC_NOTES 4 (commit messages), AC_NOTES 34-second ("every action
  citing a pinned upstream line carries 're-check against the refreshed pin'"), OR133 (runner exit 2).
- **Site**: `audit/REGISTER.md` header, new "Non-interference" section (audit file); every executing session U0-U37,
  B3, B5, phase C.
- **Change**: the register header states, and every session applies:
  (1) **Isolation**: one worktree per executing agent (`git worktree add`); auditors and verifiers never write in the
  checkout; worktrees and scratch branches are recorded in the register header when created and removed when their
  unit closes (A.U37.03 (3) deletes only the recorded ones); a private toolchain copy only when the shared one is locked
  longer than the agent can wait, with its own `setcap`.
  (2) **Locks**: every port-binding command (`scripts/test.sh`, `npm test`, twin runs, `run_digital_twin_ci.sh`) runs
  under `flock /tmp/sensors-audit-ports.lock` until the product's own per-port locks exist (M.SCR.012, U24/U27), then
  under those; firmware builds under `flock /tmp/sensors-audit-toolchain.lock` until A.U21.22's toolchain lock exists,
  then under it. Two port-binding suites never overlap (CLAUDE.md "Two suites that both bind real ports").
  (3) **Evidence before a rerun**: the twin's FRAM log is read first (CLAUDE.md FRAM rule applies to the twin); then
  `digital_twin/fram_state.json`, `digital_twin/scd30_state.json`, `digital_twin/mem_backup_state.json` (M.TWIN.050),
  `digital_twin_ci_logs/`, `htmlcov*/`, `coverage*.xml`, `coverage_summary*.md` and failed-run output move to
  `audit/archive/<UTC timestamp>/`; the last three archives per kind are kept; a run whose evidence a register entry or
  round record cites is copied into that entry first (the A.C.01 (3) precedent), so rotation never drops cited
  evidence. The pre-run step deletes only pure scratch; evidence is moved, never deleted.
  (4) **Repeats**: fault planting and repeat runs are budgeted before they start, run on tmpfs, at most ~20 repeats and
  only as confirmation; a timing failure under contention stays unconfirmed until reproduced alone; a retry is never a
  fix (OR37.a (2)).
  (5) **Per action, first step**: when the dependency refresh moved a pin (M.PROC.013), the action's upstream line
  citations and version literals are mapped to the refreshed pin before it runs; a changed premise revises the action
  first (a wrong premise goes to A-C as a delta with its register fix); permanent text cites the new tag's lines.
  (6) **Per unit, sync point** (OR6.a): commit (messages cite no audit ID; an ID belongs in the action's Why/Depends or
  a `[src: …]` note), push, the full suite (M.PROC.002) on the unit's tip, CI green observed through the PR event
  subscription only (owner: "Do hooks only"), the register's unit row and PR #107's status note updated. A runner's exit
  2 is a usage or setting error of the invocation (OR133, firm), fixed in the invocation, never read as a test result.
  (7) **Side obligations per unit** (CLAUDE.md; A.U37.04 checks them at close): a `src/` file added → the bird's-eye
  `src/` scan recorded; `src/asy_uart_comm.py` changed → its Class A/B entry in `UART_C_PORT_CHANGELOG.md` in the same
  commit; a build-environment file changed (`pyproject.toml`, `uv.lock`, `package*.json`, `.nvmrc`, the two `.ini`,
  `scripts/`, `toolchain/`, `.github/`) → its line in BACKLOG's chroot list in the same unit (and the chroot recipe run
  when the sandbox can build one); a new doc → README "Further reading".
- **Resolved**: A.U0.04 (3)'s "(last 3 kept, never deleted beyond that)" and "evidence is moved, never deleted" read
  together as rotation of the archive with cited evidence copied first (A.C.01 (3)'s rule for the hardware archive) —
  agent decision D1.
- **Unit**: U0 (written before the first executing agent, G10/R04); applies to every later unit, B3, B5 and phase C.
- **Depends**: —
- **Blast carried by**: the permanent port and archive rules → M.SCR.012/M.SCR.003 (HR130/HR193's product locks and
  archive); CLAUDE.md parallel-agents agreement → A.U37.08 (DOCS); citation mapping procedure → M.PROC.013.
- **Kind**: rule

### M.PROC.002 One full-suite command set for every gate
- **From**: A.SDEP.02 (the per-family command set and its extra baseline rows), A.U37.07 (2) (the pass's suite),
  A.SDEP.20 (same commands after the refresh), A.U0.06 (the baseline's commands; read, its record shape kept),
  A.U35.02 (the campaign's runs; read, merged in M.SCR.006/.024/.060).
- **Site**: `audit/artefacts/ENV/baseline.md` (its command list, audit file); every gate that says "the full suite".
- **Change**: "the full suite" means, serialized under the locks of M.PROC.001 (2), each command in the form the tree
  under test carries (a form introduced by a later unit replaces the earlier one from that unit on):
  L0 `uv run pytest tests_scripts`; `npm run lint`, `npm run typecheck`, `npm run lint:html`, `npm run lint:css`,
  `npm run lint:html:built` (from the unit that adds it, M.WEB.071/M.SCR.020), `npm test` (every shard, the live PUT
  matrix included); L1 `scripts/test.sh` and `GC_THRESHOLD=32768 scripts/test.sh`, then `scripts/test.sh --coverage`
  (coverage advisory, its test result gating, SPEC E.5.3); L2 `scripts/run_digital_twin_ci.sh <device>` for every
  derived device (both GC stages and the scenario harness inside it, M.SCR.061); L3/L4 `uv run pytest tests_hardware
  --collect-only` (board-free); `scripts/lint.sh` (ruff, shellcheck, actionlint, zizmor); `scripts/typecheck.sh` (all
  three passes); every device's firmware built and verified (`scripts/build_firmware.py <device>` for each derived device,
  through `RUN_SLOW_FIRMWARE_BUILD=1 uv run pytest tests_scripts/test_build_firmware.py -k
  test_real_firmware_build_produces_a_valid_uf2` while that is the verified form); when the change touches `toolchain/`
  or the MicroPython pin, also `uv run toolchain/setup_toolchain.py test`; the cross-browser smoke
  (`scripts/setup_cross_browser_toolchain.sh`, then `node scripts/cross_browser_smoke.mjs`) where the sandbox can run
  it, else CI's `web-cross-browser-smoke` job. Pass: zero failures; counts collected/passed/skipped/deselected equal to
  the reference column or each difference explained; zero `MemoryError` / `memory allocation failed` markers at both
  GC stages in the unit and twin gates; lint 0 and each mypy pass 0; `tsc`, ESLint, Stylelint, html-validate 0; wall
  clock, host peak RAM, host SSD writes and image sizes recorded, a figure worse than the reference beyond run-to-run
  spread (one repeat on the reference worktree, inside M.PROC.001 (4)'s budget) root-caused, never accepted silently.
- **Resolved**: the gates named their command sets differently (A.U0.06 omits `lint:html`, `lint:css`, the per-device
  firmware build, `setup_toolchain.py test` and the smoke; A.U37.07 omits `lint:html:built` and the smoke). One set,
  defined once, is the OR24 consistency reading; A.SDEP.02 itself offers moving its extra rows into the baseline ("A-C
  may instead move them into A.U0.06") — they move (M.PROC.007), so every column measures the same commands. Agent
  decision D2.
- **Unit**: U0 (defined with the baseline); used by M.PROC.007, .009, .012, every sync point (M.PROC.001 (6)), B3
  (M.PROC.022), B5 (M.PROC.032), phase C's lower levels (M.SCR.006 runs its L0-L2 subset).
- **Depends**: M.PROC.001.
- **Blast carried by**: the runners' own behaviour → M.SCR.006/.024/.035/.061; SPEC E.6.1 level ladder → A.U7.01
  (SPEC).
- **Kind**: rule, test

## P2 — U0: the baseline (B0)

### M.PROC.003 U0 runs in one fixed order
- **From**: A.SDEP.01 (Site: "after A.U0.06 … before A.U0.07-A.U0.60 are executed"), A.U0.03, A.U0.04, A.U0.05,
  A.U0.15, AC_NOTES 34-second ("A-C adds the U0 step and orders it before every B1 action"), OR129.a (1), OR131.a
  (Microdot stubs in U0's re-vendor), M_TOOL gap 11 (W32 outcome and dorny in U0).
- **Site**: the register header's U0 row; `audit/artefacts/ENV/` (audit files).
- **Change**: U0 executes in this order, each step's record in `audit/artefacts/ENV/`: (1) A.U0.02 — baseline SHA and
  anchor move (DOCS-indexed; procedure as written); (2) M.PROC.001 — the frame; (3) M.PROC.004 — toolchain, reference
  corpus, extractor; (4) M.PROC.005 — audit apparatus; (5) M.PROC.007 — the baseline measured (A.U0.06 plus the extra
  rows); (6) the dependency refresh, P3 (M.PROC.008-M.PROC.013), family by family, ending with the post-refresh baseline
  (M.PROC.012); (7) M.PROC.006 — the history trace (read-only, any time after (1)); (8) A.U0.01 and A.U0.07-A.U0.60 —
  the U0 code and doc actions, whose allow-lists (A.U0.08/A.U0.09) are built after (6) so the texts the refresh wrote are
  already in the tree. Nothing of B1 (U1 onward) starts before (6) is closed in its record and CI is green on it.
- **Resolved**: A.SDEP.01 puts the refresh "right after the baseline is recorded" (OR129.a (1)) — before A.U0.07-.60;
  AC_NOTES 34-second asks A-C to order it before every B1 action; both hold in this order.
- **Unit**: U0.
- **Depends**: —
- **Blast carried by**: each step's own merge (named); BACKLOG owner-question list (hold-backs) → A.U0.12 (DOCS).
- **Kind**: rule

### M.PROC.004 Build the toolchain and both corpora; the extractor fails loudly
- **From**: A.U0.03, A.SDEP.24 (second checkout at the refreshed tags; plan text DOCS-indexed), AC_NOTES 37 (the
  datasheets are still in-tree in U0).
- **Site**: new `audit/sweeps/extract_datasheets.py` (audit file); the session scratchpad (corpus checkouts).
- **Change**: (1) Toolchain: `uv run toolchain/setup_toolchain.py setup` (`test` on an existing install); confirm both
  Unix ports with `scripts/test.sh`'s own probe (`hasattr(sys, "settrace")`): `build-standard` → plain,
  `build-settrace` → settrace; no third variant. (2) Corpus, read-only: MicroPython `v1.29.0` with `lib/lwip`,
  `lib/pico-sdk`, `lib/cyw43-driver`, `lib/micropython-lib` initialised (`git submodule update --init` for the four);
  Microdot at `v2.6.2` (the scratch `microdot/` at `v2.7.0` is switched); `Sensirion/gas-index-algorithm`. As soon as the
  refresh names new tags (M.PROC.008 families (d), (e)), a second checkout at those tags joins it; the first stays for
  the citation mapping (M.PROC.013). (3) `extract_datasheets.py <outdir>`: exit 1 with a message naming `datasheets/`
  when it is an uninitialised submodule or holds no PDF (OR80.a); per PDF `<outdir>/<chip dir>__<stem>.txt` via pypdf
  (`PdfReader`, `decrypt("")` when encrypted, `extract_text()` per page joined by newlines); prints each unreadable PDF
  and each chip named in `devices/*.toml`/`src/asy_*_driver.py` with no datasheet directory. Run as `uv run --with pypdf
  --with cryptography audit/sweeps/extract_datasheets.py <scratch>`; not in the dev group, not in `lint.sh`. After U28
  moves the datasheets (M.PROC.018) a session runs `git submodule update --init datasheets` first. (4) Egress failures go
  to the OR4.a list in the register header.
- **Resolved**: —
- **Unit**: U0 (step (3) of M.PROC.003; the second checkout inside step (6)).
- **Depends**: M.PROC.001.
- **Blast carried by**: the builds `scripts/test.sh` uses later (no file change); ENV.T03/ENV.T11 plan text → A.SDEP.24
  (DOCS, `PROJECT_AUDIT_PLAN.md`).
- **Kind**: code (audit file), rule

### M.PROC.005 Commit the missing audit apparatus
- **From**: A.U0.05.
- **Site**: `audit/sweeps/packet.py` (new), `audit/sweeps/validate_plan.py:43-80` (`v3()`), `audit/sweeps/resolve_refs.py`
  (new), `audit/do_not_reopen.md` (new) — audit files.
- **Change**: as A.U0.05 (1)-(4): `packet.py <unit>` assembles plan 4.4's auditor context verbatim plus the unit's
  register blocks and files; `v3()` checks the quoted fragment occurs within lo−5…hi+5 of the anchor at the SHA (using
  `harvest_check.check()`'s normalisation, imported), reporting "moved to :N"; `resolve_refs.py` resolves every
  `path:line`, `Part X.Y` and BACKLOG citation in the living docs at HEAD and prints the unresolved (feeds A.U0.08's
  allow-list); `do_not_reopen.md` from DECISION_PROVENANCE's answered lists and OR54-OR73 only, one row per entry
  (decision, actor and date, the correction owed), reopened entries omitted (`NTP_Host` 1,024 bound, OR70.a (4)).
  `packet.py` also names, for each unit, the A-C merged changes landing in it (the work order, OR106.a).
- **Resolved**: the A-C list is the B1/B2 work order (OR106.a); a packet built from the unit files alone would miss
  merged end states, so the packet carries the unit's M-IDs — agent decision D3.
- **Unit**: U0 (step (4)).
- **Depends**: M.PROC.001.
- **Blast carried by**: A.U0.08's allow-list input (TSC M.TSC citations section).
- **Kind**: code (audit file)

### M.PROC.006 Trace the owner paragraphs the 2026-07-30 merges dropped
- **From**: A.U0.15.
- **Site**: new `audit/artefacts/ENV/history_trace.md` (audit file).
- **Change**: as A.U0.15: re-derive the set over merges `f455d34`, `8d89ff5`, `7a7f4b6` (BACKLOG.md-only; the second
  parent's added lines absent from the merge and not added by the first parent, grouped into paragraphs, filtered to
  "owner", "owner-requested", "owner-confirmed", "Owner direction"); reproduce the 78-paragraph count or explain the
  difference from the 60-line quick count; one row per paragraph (merge, `<merge>^2:BACKLOG.md:<line>`, quote, outcome
  stands / resolved-migrated (where) / pruned as history / lost / drifted, evidence at HEAD), with the pre-filled
  outcomes A.U0.15 lists and the H1 outcomes of `audit/pass3/H1.md`. A "lost" row with no register home is a delta to
  A-C (OR106.a), routed to its owning unit before that unit runs.
- **Resolved**: —
- **Unit**: U0 (step (7)).
- **Depends**: A.U0.02 (baseline SHA).
- **Blast carried by**: restorations → the units each row names; G6/R28, G6/R24 rows → their SRC_NET merges.
- **Kind**: doc (audit file)

### M.PROC.007 Measure the B0 baseline once, every command, both GC stages
- **From**: A.U0.06 (procedure; its ENV.T02 plan-text edit is DOCS-indexed), A.SDEP.02's extra baseline rows (moved
  here, M.PROC.002), AC_NOTES 38 (the uv version current at B0 recorded in the environment line).
- **Site**: baseline worktree at the A.U0.02 SHA; `audit/artefacts/ENV/baseline.md` (audit file).
- **Change**: M.PROC.002's full suite once on the baseline worktree, each MicroPython level at `-1` then at
  `GC_THRESHOLD=32768` (the twin runner does both internally; the per-stage figures from its two log subdirectories).
  Per level: files; tests collected/passed/failed/skipped/deselected; wall clock; host peak RAM (1 s `MemAvailable`
  sampler plus the runner's max RSS); host SSD writes as the `/proc/diskstats` sectors-written delta of the worktree's
  device (`test.sh` expected near ~46 MB; far above is a finding for U24/U27); `src/` line coverage and what the
  generated code and host build chain lack; lint and each mypy pass's count with its checked-file count and every file
  excluded from a pass that no other pass names; `disallow_any_explicit` and `disallow_any_unimported` counts per pass
  (each of the three mypy invocations re-run with the flag added; measured only, not switched on); the 25 ANN401
  per-file exemptions listed; per-device image sizes and `.bss`/`.data`/GC-heap from `firmware.elf`; the environment —
  MicroPython ref, both Unix-port variant probes, every tool version against its pin, and `uv --version` (the value
  A.U28.02 later pins, AC_NOTES 38). One repeat of each level gives the run-to-run spread. The record has a "B0" column
  that M.PROC.012 extends.
- **Resolved**: A.SDEP.02's extra rows join the baseline (M.PROC.002 Resolved).
- **Unit**: U0 (step (5)).
- **Depends**: A.U0.02, M.PROC.001, M.PROC.002, M.PROC.004.
- **Blast carried by**: the write figure → Part N tunables (A.U8, SPEC); ENV.T02 text → A.U0.06 (DOCS); uv pin →
  M.TOOL.024.
- **Kind**: test (audit file)

## P3 — U0: the dependency refresh (OR129, LEAD/R33)

OR129 (owner, 2026-09-30), the intent every step below serves: "Check all external dependencies for updates - both
modules, repos and tooling, just everything. - If you find updates, carefully check what was changed. - Solve possible
breaking changes without any regressions. - Check for opportunities, improvements, fixes we can profit from and update
our code accordingly. - Check especially for fixes we needed to implement workarounds for, if they were solved upstream,
apply and fix no longer needed workarounds to clean implementations. … adhere to our existing guidelines and rules".

### M.PROC.008 The refresh: one record, one family per commit, before any B1 change
- **From**: A.SDEP.01, AC_NOTES 34-second, M_TOOL gap 11 (A.SDEP.19's W32 outcome fixes the local `uses:` form;
  A.SDEP.05 executes A.U28.13 in U0), OR131.a (Microdot stubs in the same re-vendor), M_WEB gap 8
  (`@eslint-community/eslint-plugin-eslint-comments` moved into family (b), M.WEB.071), SUPP_deps "Co-landing" 1-19.
- **Site**: U0 step (6) (M.PROC.003); worktree and branch per M.PROC.001; record `audit/artefacts/ENV/dependency_refresh.md`
  (audit file, beside `baseline.md`).
- **Change**: (1) **Record**: one row per inventory line D1-D28 (`SUPP_deps.md` "Inventory at HEAD") plus every
  workaround W01-W45: pin site, value before, newest stable found (with the command that found it, run at execution),
  changelog/diff range read, decision (moved / held back / already newest / not applicable) with its reason, the
  family's gate result (M.PROC.009), the commit. (2) **Order**, one family per commit so a regression bisects to one
  family, each commit's gate green and CI green before the next starts:
  (a) Python tools and `uv.lock` — A.SDEP.03 (M.TOOL.022/.024/.025/.028/.078, M.SCR.029/.069); the lock merge check on
  every lock rewrite (installed `ruff`/`mypy`/`zizmor`/`actionlint`/`shellcheck` versions equal the pins; every dev
  `specifier` agrees with its `[[package]] version`); `uv --version` and the `coverage` version recorded (A.U28.02 and
  A.U24.72 pin them later from this record).
  (b) Node, npm, Playwright — A.SDEP.04 (M.WEB.070-.073, M.TOOL.069, M.SCR.064/.073), A.U28.23's `@types/node`-major rule
  applied in this commit, the eslint-comments plugin added here (M.WEB.071); `npm audit` read.
  (c) GitHub Actions — A.SDEP.05 (M.TOOL.001/.005/.006/.020): first-party tags; dorny moved to a v4 commit here (A.U28.13
  pulled forward); Codecov not refreshed (A.U28.15 removes it); the runner image recorded.
  (d) Vendored code — A.SDEP.06 Microdot re-vendored as an unmodified tag with upstream's `typings/microdot/` stubs
  byte-identical in `ext/typings/microdot/` in the same commit (M.GEN.051, M.GEN.050; OR131.a, firm); A.SDEP.07 freezefs
  at upstream `main`, recorded by commit (M.SCR.072, M.TSC hash test, M_DOCS THIRD_PARTY entry).
  (e) MicroPython with everything it pulls in, then the stubs — A.SDEP.08 (M.TOOL.073, platform re-check (4) in full,
  the measurements (5)), A.SDEP.09 (M.SCR.027, M.TOOL.077); this commit also carries every override-anchor
  re-derivation the new tag forces (A.SDEP.11 (b), A.SDEP.13 (b), A.SDEP.14), since a drifted anchor fails `setup`.
  (f) Workaround checks A.SDEP.11-A.SDEP.19 (catalog W01-W45; each retirement its own commit), their edits merged by the
  owning clusters (the A.SDEP.11-.19 ledger rows of M_TOOL, M_SCR, M_TWIN, M_SRC_NET, M_SRC_SENS, M_GEN, M_TEST_UNIT,
  M_TEST_HELP, M_HW_BENCH, M_WEB); W32's outcome (actionlint accepting `uses: $/…` or not) is recorded first in this
  family and fixes the local `uses:` form every later `.github` edit writes (M.TOOL.001/.002/.020/.022).
  (g) Derived-code upstreams — M.PROC.010.
  Then the runtime-fact re-check (M.PROC.011), the post-refresh baseline (M.PROC.012) and the citation re-scan
  (M.PROC.013 (1)). (3) **Newest** = the newest stable release of the family (no pre-release, release candidate or
  preview; Node: the newest Active LTS line; MicroPython: a plain `vX.Y.Z`, as `latest_stable_micropython_ref()` selects,
  and only one whose `micropython-rp2-rpi_pico_w-stubs` release exists, else held back); untagged upstream commits are
  noted only. (4) **Hold-back**: a dependency whose newest release breaks a check that cannot be fixed within the rules
  (vendored code never edited, no test-only artefact in product code, no weakened gate) stays at the newest release that
  passes; recorded in the register as a decision on the owner's behalf (OR2.c) and in BACKLOG's owner-question list
  (A.U0.12) with the dependency, the failing release, the reason and "re-checked at the next refresh"; M.PROC.031 re-reads
  it. (5) **Routing**: breaking-change fixes and workaround retirements land in this step; an adoption that changes
  behaviour or structure beyond that (a new upstream API, an upstream fix to derived code) is a delta for its owning unit
  (OR106.a) with the upstream reference; a change that would alter an owner-decided behaviour (W05 `TCP_NODELAY`, W17
  two Unix binaries, W28 power-cycle backstop, W38 boot `gc.collect()`/threshold) is parked for the owner's review
  (harmonization 1), never a stop. (6) **No hardware**: nothing is flashed and no `mpremote` runs; a firmware pin move is
  validated in phase C (BACKLOG entry of A.SDEP.08 (6), phase C row H60).
- **Resolved**: the U0 placement (OR129.a (1)) against A.SDEP.24's corpus dependency: A.SDEP.08 makes the new-tag
  checkout itself (its step (1)), so the refresh does not wait for the plan text. The family texts that write permanent
  records (A.SDEP.21: F.5 record and F.5.10, CLAUDE.md "Last run", BACKLOG chroot, hardware and owner-question entries,
  THIRD_PARTY) are DOCS/SPEC merges landing in the same U0 commits.
- **Unit**: U0 (step (6) of M.PROC.003); before the first B1 action.
- **Depends**: M.PROC.007 (the B0 column), A.U0.02, M.PROC.001.
- **Blast carried by**: per family as named; A.SDEP.21 records → M_DOCS (THIRD_PARTY, BACKLOG, CLAUDE.md) and M_SPEC
  (F.5, F.5.10); BACKLOG chroot entry naming the eslint-comments plugin → A.SDEP.21 (DOCS, M_WEB gap 8); A.SDEP.22's
  CLAUDE.md practice bullet → DOCS.
- **Kind**: rule

### M.PROC.009 One check gate per family commit, against the B0 column
- **From**: A.SDEP.02.
- **Site**: every family commit of M.PROC.008; results in the refresh record.
- **Change**: after each family commit, M.PROC.002's full suite (the `setup_toolchain.py test` row for families (a) and
  (e)), judged against the B0 column with M.PROC.002's pass criteria. New findings from an upgraded checker (ruff, mypy,
  ESLint, `tsc`, Stylelint, html-validate, shellcheck, actionlint, zizmor) are listed one by one in the record and each
  decided: fix the code, or the narrowest suppression the tool offers with its reason in the existing place
  (`pyproject.toml` ignore list with a comment; the per-rule entries of `eslint.config.js`, `.stylelintrc.json`,
  `.htmlvalidate.json`; `zizmor.yml`) — never a blanket disable, never a version held back to avoid a finding. The
  family commit is pushed and CI goes green before the next family starts. When the sandbox can build a chroot,
  families (a) and (e) also run CLAUDE.md's two-leg chroot recipe, and (e) the installer leg; otherwise the BACKLOG chroot
  entry (A.SDEP.21 (3), DOCS) records them as owed.
- **Resolved**: —
- **Unit**: U0 (inside M.PROC.008).
- **Depends**: M.PROC.007, M.PROC.008.
- **Blast carried by**: the suppression placements → M.TOOL.025/.028/.030, M.WEB.070; twin state archived first →
  M.PROC.001 (3).
- **Kind**: test

### M.PROC.010 Read the derived-code upstreams for fixes to the kept parts
- **From**: A.SDEP.10.
- **Site**: D28; the derivation records in `THIRD_PARTY_LICENSES.md` (read only).
- **Change**: as A.SDEP.10: for each non-archived upstream (Adafruit BMP3XX, SCD30, SGP40, FRAM; micropython-lib
  `ntptime.py`; Sensirion `gas-index-algorithm`; `DFRobot/DFRobot_SGP40`'s `DFRobot_SGP40_VOCAlgorithm.py`; p-doyle
  captive portal) the commit log since the recorded derivation point (else since the file's first commit here, `git log
  --follow --diff-filter=A`) is read for changes to the kept parts (register maps, command codes, CRC, conversion
  formulas, timing, opcodes, the `0x1B` query and epoch delta, the algorithm constants and fixed-point steps, the
  `DNSQuery` byte layout); archived or inspiration-only upstreams are recorded "archived / not a copy — nothing to take".
  Each applicable upstream fix is verified against the chip's datasheet and becomes a delta for its owning unit (U12
  `voc_algorithm.py`, U15 drivers, U16 FRAM, U18 NTP/captive DNS) — a formula change with D.1's flag-don't-silently-change
  treatment; never a drive-by change here. THIRD_PARTY gains nothing unless a fix is taken (then U34 records the new
  upstream reference).
- **Resolved**: —
- **Unit**: U0 (family (g)).
- **Depends**: M.PROC.008.
- **Blast carried by**: delta items (their own units); M.SRC_SENS.001/.009 (the drivers' upstream notes, read).
- **Kind**: rule

### M.PROC.011 Re-read the MicroPython runtime facts that shape code at the new tag
- **From**: A.SDEP.17.
- **Site**: SPEC F.1, F.2, F.5.1, F.5.7-F.5.9 and the code each shapes (W18-W28, W37-W40, W42).
- **Change**: only when family (e) moved the pin (else: the issue states of micropython#9455, #9505, #18797 and 19704
  are read and recorded only). Each fact re-read at its source and the code shape it forces re-judged, as A.SDEP.17
  lists: W18 nested `asyncio.run()` (rule stays; symptom text follows the source), W19 async generators (support → a
  U19/U30 delta, memory measured first), W20 starred displays and `await` in comprehensions (text only), W21
  `struct.pack()` truncation (validation stays), W22 soft-timer drop (`PERIODIC` stays), W23 `[x] * n` range (clamp
  stays), W24 UART `deinit()` rooting (construction stays; comment and F.5.7 say whether it is load-bearing), W25
  UART per-byte wait (owner's no-block rule keeps the clamp and the yield; F.5.8/F.5.9 text follows the source), W26
  I2C/SPI `deinit()` and static singletons (a change is a U13/U14 delta with a phase-C check: F.5.1, wrapper comments,
  both fakes, `bus_deinit_is_a_noop_on_real_hardware.py`, the controller re-init rung of A.U13.R01), W27
  `getaddrinfo()` timeout (F.2 text only), W28 CYW43 `isconnected()` false positive (F.2 line only; the power-cycle
  recovery is owner-settled), W37 rp2 boot order (`main.py` entry stays), W38 the allocator API (any change parked for the
  owner, harmonization 1), W39 `json.loads()` separators (helper may stay; U24 delta), W40 `stream.py` re-concatenation
  (U25 delta, memory measured first), W42 the 100 ms `stations` settle (removal only on A.U18.43's trigger, phase C row
  H82). Every changed fact is a delta for the unit owning its text and code, with its tests named in A.SDEP.17's Blast;
  no `UART_C_PORT_CHANGELOG.md` entry (W24/W25 touch `asy_uart_driver.py` comments only).
- **Resolved**: W42 co-lands with A.U18.43 (1) (its trigger) — merged in M.SRC_NET.190 (read).
- **Unit**: U0 (after family (e)); the deltas in their units.
- **Depends**: M.PROC.008 family (e).
- **Blast carried by**: M.HW_DEV.049/.074, M.HW_BENCH.030/.131, M.SRC_NET.190, M.SRC_SENS.001/.009,
  M.TEST_HELP.008/.023, M.TWIN.016/.019/.024/.070 (the conditional text and code per item); SPEC F.1/F.2/F.5.x texts →
  M_SPEC (conditional: only a flipped fact changes them); CLAUDE.md `:650-664` and the UART no-block mechanism sentence →
  DOCS (conditional).
- **Kind**: rule, doc

### M.PROC.012 Measure the post-refresh baseline every later unit compares against
- **From**: A.SDEP.20.
- **Site**: `audit/artefacts/ENV/baseline.md` (audit file).
- **Change**: after the last family commit, M.PROC.007's measurement once more on the refreshed tree (same commands,
  same serialization, same repeat for spread); the record gains the column "after the dependency refresh" beside "B0",
  each delta attributed to the family that caused it (from M.PROC.009's per-family results). From B1 on every unit's
  before/after (OR39.a (3), OR30.a (3) run times, LEAD/R07 image sizes) is taken against this column; the B0 column
  stays as the pre-refresh reference. When no dependency moved, the record says so and the B0 column serves both.
- **Resolved**: —
- **Unit**: U0 (last of step (6)).
- **Depends**: M.PROC.008-M.PROC.011.
- **Blast carried by**: U8's tunables write figure takes the refreshed value (A.U8, SPEC Part N); B3's `timing.md`
  (M.PROC.022) and the final report (M.PROC.034) read both columns.
- **Kind**: test (audit file)

### M.PROC.013 Re-check every pinned-upstream citation against the refreshed pin
- **From**: A.SDEP.23.
- **Site**: `audit/actions/*.md`, `SUPP_lwip.md`, `AC_NOTES.md`, the A-C merges `audit/consolidation/M_*.md` (audit
  files); the counts table in `SUPP_deps.md` (216 actions / 660 citations at `d6557c5`).
- **Change**: only when families (d)/(e) moved a pin (MicroPython and its submodules, Microdot, freezefs, the stubs);
  otherwise the record says "no pin moved; citations stand" and this is done. (1) Once, right after the refresh: the
  citation scanner of A.SDEP.23 (1) re-run over the action files, `SUPP_lwip.md`, `AC_NOTES.md` and the A-C merges, plus
  the version literals naming a moved pin (`v1.29.0`, `v2.6.2`, the submodule SHAs `98a542c`, `77dcd25`, `055d642`,
  `0bebf8b`, `ee4bb8f`, the stub post-releases, the tool versions actions quote such as A.U28.02's `pytest==9.1.1`/
  `mpremote==1.29.0`, A.U19.18's sha256 table, A.U34.08's freezefs commit); v1.28.0-marked facts are skipped. The result
  is a per-action list. (2) Per action, as its first step (M.PROC.001 (5)): each citation mapped by `git diff -U0 <old>
  <new> -- <path>` (submodules `git -C lib/<sub> diff -U0`; Microdot `git diff -U0 v2.6.2 <tag> --
  src/microdot/microdot.py`; freezefs the two recorded commits; stubs `diff -U0` of the two `typings/` trees); shifted
  unchanged text → the line updated in the working copy of the action; changed text → the premise re-read and the action
  revised before it runs (a wrong premise → A-C delta with its register fix); a version literal → the refreshed value
  from the record. Permanent text cites the new tag's lines. (3) Actions whose purpose the refresh settled close with the
  evidence (e.g. A.U21.09-A.U21.11 under A.SDEP.13 (a); A.U21.16 when A.SDEP.12 applies it).
- **Resolved**: the A-C merges carry upstream line citations too (e.g. M.GEN.051's Microdot facts, M.SRC_NET's lwIP
  lines); the scan covers them so the work order and its constituents move together — agent decision D4.
- **Unit**: U0 (step (1)); step (2) in every later unit.
- **Depends**: M.PROC.008 families (d)/(e); M.PROC.004 (both corpora).
- **Blast carried by**: audit files only; register fixes where a premise changed (lead, per wave).
- **Kind**: rule (audit file)

## P4 — Unit-specific procedures and the no-cluster files (B1/B2)

### M.PROC.014 U1: move the legacy tree byte-identical, dissolve `dev_legacy/`
- **From**: A.U1.01 (firmware set → `legacy/firmware/`), A.U1.02 (dev snapshot → `legacy/dev_drivers/`; indexed to
  `README.md` by a parser hit on its Site text, no README edit of its own — carried here), A.U1.08 (`git rm
  dev_legacy/README.md`).
- **Site**: repo root `python/` (23 files), `modules/` (5), `html_raw/` (13), `build-arzi.sh`, `build-dev.sh`,
  `build-neu.sh`, `build-wozi.sh` (mode 100755), `update_and_install.txt` (46 tracked files); `dev_legacy/` (31 files
  except `README.md`); `dev_legacy/README.md` (678 lines).
- **Change**: one U1 commit: (1) `mkdir -p legacy/firmware legacy/dev_drivers`; `git mv python modules html_raw
  build-arzi.sh build-dev.sh build-neu.sh build-wozi.sh update_and_install.txt legacy/firmware/` — relative layout kept,
  so each `build-<device>.sh` still works unedited when `legacy/firmware/` is the `py-include` directory of a MicroPython
  checkout; git modes kept (the four scripts stay executable). (2) `git mv dev_legacy/<each of the 31 files>
  legacy/dev_drivers/`, flat, names unchanged, the two `.cfg` files included (`/config_*.cfg` is root-anchored and does
  not match them; both are tracked). (3) `git rm dev_legacy/README.md` — every line accounted for (A.U1.08's map: :30-62,
  :64-108 (three observations), :595-665 → `tests_hardware/README.md` (M.HW_BENCH.111-.113, .125); :110-141 and
  :525-528 likewise; :545-593 → the manual bridge recipe (M.HW_BENCH.112); :667-678 → `legacy/README.md` (M.PROC.015);
  the rest dropped, `:537-543` because it contradicts CLAUDE.md's FRAM rule). (4) No file content changes. Verification
  in the commit: `git diff --cached -M --summary` shows 77 `rename … (100%)` lines (46 + 31), one `delete mode` line
  (`dev_legacy/README.md`) and one `create mode` (`legacy/README.md`), nothing else for these paths. (5) The same commit
  carries every repath of a moved path (G8/R48 "paths change in the same commit"): the U1 stages of A.U1.09-A.U1.27 in
  their clusters (M.TOOL.011/.012/.026/.066, M.SCR.025, M.SRC_NET.081/.083, M.GEN.052, M.HW_DEV.051, M.HW_BENCH.111-.113,
  M.TWIN.027, M_DOCS U1 stages, M.PROC.019 (1) and (4)) and A.U1.09's old-path check (TSC), and drops every
  `tests_scripts/_citation_allowlist.txt`/`_decision_vocab_allowlist.txt` entry for `dev_legacy/README.md` and for each
  sentence A.U1.10-A.U1.21 rewrites (M.TSC allow-list sections).
- **Resolved**: OR32 ("all legacy code … located in one /legacy folder, containing structured subfolders", owner,
  2026-09-25) is the one change the legacy tree ever gets; CLAUDE.md's "legacy tree … never gets work" holds for content
  (byte-identical moves). A.U1.02 sits in no cluster's file list; carrying it with A.U1.01/A.U1.08 keeps the dissolution in
  one commit.
- **Unit**: U1.
- **Depends**: — (U0 closed).
- **Blast carried by**: as (5); README "Further reading" `legacy/README.md` entry → A.U1.13 (M.HW_BENCH.113 / DOCS); SPEC
  A.1/A.3/B.9/B.11 repaths → A.U1.14-A.U1.18 (SPEC); CLAUDE.md legacy rule repath → A.U1.10 (DOCS).
- **Kind**: code

### M.PROC.015 U1: `legacy/README.md` holds legacy descriptions only
- **From**: A.U1.03; A.U32.04's register fix (the reflash runbook lives in README.md; `legacy/README.md` gets no
  pointer, U32 Register fix 1).
- **Site**: new file `legacy/README.md`.
- **Change**: one header block, then exactly these sections and nothing else (text per A.U1.03 (1)-(5)): (1) **What
  this is** — reference-only, never edited, linted, type-checked, tested, built in CI or completed (owner, 2026-09-11);
  may run in a scratch directory as a published-value reference, nothing committed (owner, 2026-09-26); the move is the
  one change it ever got (owner, 2026-09-25). (2) **`firmware/`** — the firmware the owner's legacy units run, on
  MicroPython **1.24.1** (owner, 2026-09-26: "all legacy real devices run 1.24.1"): the subfolders and files listed in
  A.U1.03 (2), and how the build runs (moved from SPEC B.11, A.U1.16): each `build-<device>.sh` assembles `python/build/`,
  swaps `modules/_boot.py`/`sensortask-<device>.py` into upstream's `ports/rp2/modules/`, runs `make -C ports/rp2
  BOARD=RPI_PICO_W FROZEN_MANIFEST=<path>`, copies `firmware.uf2`, restores `_boot.py`; it expects this directory to be
  the `py-include` directory inside a MicroPython checkout; the scripts pin no MicroPython version. (3) **`dev_drivers/`**
  — the dev unit's on-device filesystem captured 2026-08-27 over `mpremote` (`e05f015`) on 1.24.1, with
  `dev_legacy/README.md:667-678`'s note (`sensortask-dev.py` internally inconsistent: wrong `asy_FRAM_manager` import
  name, an absent SHTC3, a Neopixel pin that is not the real one; `sensortask_test.py` the more consistent reference).
  (4) **Baseline** — legacy HEAD is the comparison baseline for legacy-vs-refactor questions (owner, 2026-09-26).
  (5) **Edits after the 2026-07-13 import (`8c4a73d`)**, complete per `git log` over the legacy paths: `2bda920`
  (2026-07-22, BMP3xx IIR coefficient encoding — the only behavioural one), `b6cb852` (2026-08-20, build paths),
  `ba80b9d`/`383d17b` (2026-08-20, attribution comments), `7a27ca1`/`a297b0f` (the "SUPERSEDED" preamble of
  `update_and_install.txt`; its "1.26" is stale, the units run 1.24.1). No bench, wiring, host-network or `src/`
  content; no reflash-runbook pointer (U32 places the runbook in README.md). No audit ID and no `[src: …]` note in the
  file.
- **Resolved**: A.U1.03's Blast left the runbook's home open; U32 settled it in README.md with no pointer here (U32
  Register fix 1, recorded at A.U32.04's unit).
- **Unit**: U1 (in M.PROC.014's commit).
- **Depends**: M.PROC.014.
- **Blast carried by**: A.U1.09's tracked-file assertion (TSC); README "Further reading" entry → A.U1.13 (DOCS/
  M.HW_BENCH.113); SPEC A.1 → A.U1.14 (SPEC); CLAUDE.md legacy rule → A.U1.10 (DOCS).
- **Kind**: doc, rule

### M.PROC.016 U14: diff the effective `MICROPY_*` settings of the three refreshed builds
- **From**: A.U14.29; SUPP_deps "Co-landing" 11 (A.U14.29 diffs the builds of the refreshed pin).
- **Site**: the builds M.PROC.004/M.PROC.008 (e) leave (`RPI_PICO_W` firmware, Unix `build-standard`,
  `build-settrace`); output to the audit scratch area (no commit of the raw diff).
- **Change**: as A.U14.29: per build, the exact compiler command for `py/runtime.c` (rp2 `make -C ports/rp2
  BOARD=RPI_PICO_W V=1` or `compile_commands.json`; Unix `make -C ports/unix VARIANT=… V=1`) with `-c … -o …` replaced by
  `-dM -E`, the `#define MICROPY_*`/`MP_*` lines kept and sorted; rp2 diffed against each Unix build and the two Unix
  builds against each other (settrace and `MICROPY_ASYNC_KBD_INTR` the expected differences). Every differing setting that
  changes a construct used in `src/`, `ext/microdot.py` or the generated modules becomes an F.7 row; the rest one F.7
  sentence "differ, used by nothing here".
- **Resolved**: Site said "B0 tool run"; the co-landing note moves it onto the refreshed pin, so it runs in U14 before
  A.U14.28 writes F.7 (both from the same builds). If no pin moved, the B0 builds are the same builds.
- **Unit**: U14 (before A.U14.28).
- **Depends**: M.PROC.004, M.PROC.008 (e).
- **Blast carried by**: F.7 rows and sentence → A.U14.28 (SPEC).
- **Kind**: test (audit tool run)

### M.PROC.017 U17: a Part J ↔ code traceability table, re-checked after U17 lands
- **From**: A.U17.12.
- **Site**: new `audit/trace/UART_PART_J.md` (audit working file; deleted with `audit/` at phase D).
- **Change**: the table `| Part J statement (quoted) | code site | test (level) | status |`, one row per normative
  statement, seeded with A.U17.12's desk-check rows; at execution re-checked after A.U17.03, A.U17.06, A.U17.13,
  A.U17.16 land, reading code sites by symbol (function or constant name) — the U10 renames and class reorder
  (M.SRC_NET merges of A.U10.18/.33/.44) move every `asy_uart_comm.py` line the seed cites. Rows other units change carry
  that unit's action (J.5 warning text A.U3.08; J.6 poll default A.U13.17; J.9 errno alignment A.U2.20/A.U2.22); a row
  whose code does not hold is a finding of that unit (OR12.a), and, for a protocol-level divergence, a Class A entry.
- **Resolved**: line drift from U10 — read by symbol (agent decision D5).
- **Unit**: U17 (after its code actions).
- **Depends**: A.U17.03, A.U17.06, A.U17.13, A.U17.16; the U10 renames.
- **Blast carried by**: audit file only; its findings are the U17 actions named in its rows (M.SRC_NET/M.TEST_UNIT).
- **Kind**: doc (audit file)

### M.PROC.018 Owner step before U28: push access to the private datasheets repository
- **From**: AC_NOTES 37; A.U36.545's "Owner step (before A.U28.35)"; OR80.a, OR95.a.
- **Site**: the owner's GitHub repository `hundertvolt/datasheets`; the A-C review list (M.PROC.035) and U28's start.
- **Change**: (1) Shown to the owner at the A-C review, and asked again at U28's start if not yet confirmed: confirm the
  Claude GitHub App's grant on `hundertvolt/datasheets` includes write (push), so the executing session can create the
  default branch `main` and push the 21 PDFs (OR95.a verified read only, 2026-09-29). (2) Executor order in U28: populate
  commit pushed to `hundertvolt/datasheets` first; only after that push succeeded, `git rm -r datasheets` and `git
  submodule add https://github.com/hundertvolt/datasheets.git datasheets` in one commit (A.U28.35, M.TOOL.020 CI
  checkouts unchanged); if the push is refused, A.U28.35 and A.U36.545 stop and are reported to the owner — nothing is
  removed from the tree. (3) From then on a session needing a datasheet runs `git submodule update --init datasheets`
  first (M.PROC.004 (3)).
- **Resolved**: —
- **Unit**: owner step before U28; executed in U28.
- **Depends**: —
- **Blast carried by**: the move → A.U28.35 (TOOL M.TOOL.020; HW_BENCH/SRC_SENS/TWIN read); README/CLAUDE.md/SPEC A.6
  text → A.U36.545 (DOCS, SPEC); THIRD_PARTY → U34 (DOCS).
- **Kind**: rule (owner step)

### M.PROC.019 `.gitignore`: current facts, outside writers named, the cap kept
- **From**: A.U28.33 (main text); A.U1.21 (`:3`, `:22-23`, `:34` repaths — `:34` absorbed by the rewrite); A.U0.29 (E09
  wording of `:75-79`, capped here); A.U14.10 (`:38` restamp — superseded, the stamp leaves); A.U36.036 (4) (the
  sentinel parenthesis points at SPEC F.1); A.U28.15 (`:65`, `:68` go with Codecov/XML); A.U24.72 (`htmlcov_generated/`,
  `htmlcov_host/`, `coverage_summary_generated.md`, `coverage_summary_host.md`); A.U27.15 (MICROPYPATH sentence) and
  AC_NOTES 38 / M_SCR gap 2 (f) ("keep one"); A.U25.32 (`digital_twin/mem_backup_state.json`, M_TWIN LEAD gap);
  A.SDEP.04 (`:9-12` re-checked against the refreshed Vitest); A.SDEP.08 (4) (`:36-38` re-stamp — superseded with
  A.U14.10's); A.U27.35 (`:29-30` "fully regenerated" holds).
- **Site**: `.gitignore:1-3, :5-7, :22-25, :27-31, :33-42, :53-55, :62-70, :75-82, :84-89` (no cluster owns the file).
- **Change**: end state (every comment block ≤ 3 lines; ignore semantics unchanged except as named):
  (1) `:1-3` → `# A legacy unit's settings file, real Wi-Fi credentials included, only ever copied into this tree by`
  / `# hand (owner, 2026-09-29) - never commit one.` / `config.json` / `legacy/firmware/modules/config.json`.
  (2) `:5-6` "same "dev-tooling only" split as .venv/ above" → "… as the .venv/ entry below".
  (3) `:9-14` Vitest block kept; after family (b) the comment states the directory the refreshed Vitest writes, and
  `.vitest-attachments/` stays only while that comment can name an install that writes it.
  (4) `:22-25` → `# Legacy build output (see legacy/firmware/build-*.sh)` / `legacy/firmware/python/build/` / `*.uf2`
  (`firmware.uf2` goes: `*.uf2` covers it).
  (5) `:27-30` → `# buildgen's per-device build tree (SPECIFICATION.md Part L: generation is build-time only, nothing`
  / `# committed), also scripts/build_firmware.py's default --output and the kept build work dirs;` / ``# `rm -rf build/`
  cleans all of it.`` then `build/`.
  (6) `:33-41` → `# scripts/build_frozen_html.sh output (SPECIFICATION.md Part A.9), regenerated by scripts/test.sh, never`
  / `# committed. Not named ".frozen/": imports under that prefix go to the compiled-in frozen table` / `# (SPECIFICATION.md
  F.1), so a real directory there is unimportable.` then `frozen_modules/` — no MICROPYPATH sentence (the layouts are
  stated once, in `scripts/micropypath.toml`, M.SCR.009), no legacy-build clause, no version stamp.
  (7) `:53-54` → `# Nested checkouts the agent tool (Claude Code) creates for isolated sessions - written from outside`
  / `# this repo's tooling, never repo content (owner, 2026-09-29).` then `.claude/worktrees/`.
  (8) `:62-70` → the comment kept (2 lines, `SPECIFICATION.md Part E.5`); entries `htmlcov/`, `coverage_summary.md`,
  `htmlcov_digital_twin/`, `coverage_summary_digital_twin.md`, `htmlcov_generated/`, `coverage_summary_generated.md`,
  `htmlcov_host/`, `coverage_summary_host.md`, `.coverage` (`coverage.xml`, `coverage_digital_twin.xml` go).
  (9) `:75-82` → `# The twin entry points' persistent run state (digital_twin/launch.py, run_generic_integration.py): FRAM`
  / `# and SCD30 state flushed only at shutdown (owner, 2026-08-12), the mem_backup record kept from a simulated reset`
  / `# to the next launch, and their config_*.cfg files - regenerable, never committed.` then
  `digital_twin/fram_state.json`, `digital_twin/scd30_state.json`, `digital_twin/mem_backup_state.json`,
  `digital_twin/config/`.
  (10) `:84-88` → `# config_*.cfg spilled into the repo root when a device script runs host-side against the twin's`
  / ``# fakes (cfg_path=""): config_WIFI.cfg can hold a real SSID/password, so `git add -A` must never pick`` /
  `# one up.`
  then `/config_*.cfg`.
  Lines `:44-51`, `:57-60`, `:72-73`, `:91-93` unchanged.
- **Resolved**: A.U27.15 rewrites the MICROPYPATH sentence to point at `scripts/micropypath.toml`, A.U28.33 drops it;
  AC_NOTES 38 "keep one" and M_SCR gap 2 (f): A.U28.33's capped text wins and the sentence goes, since M.SCR.009 states
  the layouts in their one home. A.U14.10/A.SDEP.08 restamp `:38`'s version; the rewrite removes the stamp and A.U36.036
  (4) points at F.1, where the fact is version-stamped once. A.U0.29's E09 wording and A.U28.33's cap merge into (9), which
  also names the mem-backup state (M.TWIN.050's third default path; written on a simulated reset and consumed by
  the next launch, M_TWIN `:1996`).
- **Unit**: U28, with stages: U1 (A.U1.21's `:3`, `:22-23` repaths, in M.PROC.014's commit); U25 (the
  `mem_backup_state.json` line with A.U25.32); U24 (A.U24.72's four entries); U28 (the rest, A.U28.15's removals).
- **Depends**: M.PROC.014 (U1 stage); M.SCR.009 (U27); A.U25.32 (M.TWIN.050); A.U24.72 (M.SCR.038/.044); A.U28.15
  (M.TOOL.015/.021).
- **Blast carried by**: A.U6.15's variant scan covers `.gitignore` (TSC; the new text names no variant); BACKLOG chroot
  list: none (no tool reads comments); `.gitignore` is in no lint scope.
- **Kind**: doc, code

### M.PROC.020 U29: scan the whole history for secrets once; disposition every hit
- **From**: A.U29.04; OR127/OR127.a (arduino/ excluded, firm).
- **Site**: one-time script `audit/sec_history_scan.py` (audit scratch, deleted with `audit/` at phase D); results into
  the closing report and SPEC A.11 row 15's sentence (A.U29.01).
- **Change**: as A.U29.04 (1)-(5): (1) completeness — `git rev-parse --is-shallow-repository` prints `false` (else
  `git fetch --unshallow`), `git fetch origin '+refs/heads/*:refs/remotes/origin/*' '+refs/tags/*:refs/tags/*' --prune`,
  refs and commits counted; (2) passes over added lines only (`git log --all -p --no-color --format=@@%h -- .
  ':!arduino'`, every `git log` with that pathspec): (a) secret-shaped file names ever added, (b) token shapes, (c)
  password/PSK/secret/token/key-named string literals ≥ 8 chars (each distinct value once, first commit and path), (d)
  SSID literals classified real/placeholder, (e) high-entropy tokens for review, (f) bench identifiers (MACs, private
  IPv4); (3) GitHub's view: `gh api repos/hundertvolt/sensors/secret-scanning/alerts --paginate` (or the GitHub
  connector's secret-scanning call), the result recorded including "disabled"/403; an alert under `arduino/` recorded by
  count only; (4) disposition per hit (accepted hotspot default; bench throwaway; placeholder; bench identifier; anything
  else parked for the owner with its commit list and the two remedies — never rotated or rewritten by the executor); the
  report names commit, path, line and shape, never a secret's value; (5) the A.11 row 15 sentence written from the result.
  Compare with the preliminary pass at `58c72c9` recorded in A.U29.04.
- **Resolved**: OR127 (owner, 2026-09-30): "No, it stays fully out of the audit" — `arduino/` excluded by path, nothing
  read there.
- **Unit**: U29 (after U26's deletions of the tracked PSK copy and identifiers).
- **Depends**: A.U29.01 (row 15), A.U26.19 (M.HW_DEV.112), A.U21.20, A.U26.49.
- **Blast carried by**: SPEC A.11 row 15 → A.U29.01 (SPEC); CLAUDE.md bullet's history-scan clause → A.U29.03 (DOCS);
  the forward guards → A.U28.29/A.U28.31 (TOOL) and `.gitignore` (M.PROC.019); enabling secret scanning → the owner
  review list (M.PROC.035). Network: needs the execution sandbox's egress (fetch, GitHub API) — not hardware.
- **Kind**: code (one-time, audit scratch), doc

### M.PROC.021 U32: re-run the legacy-function check at the sync point
- **From**: A.U32.04.
- **Site**: the audit working record (`audit/`; nothing permanent); read: the three modules at the U32 tip and the
  legacy files at their `legacy/firmware/` paths (M.PROC.014).
- **Change**: A.U32.04's desk check repeated against the then-current code after U9/U15/U18 land, each function marked
  held / fixed by / recorded: BMP3xx (offset subtraction, sea-level formula, bounded forced-mode wait — held; fractional
  trigger seconds — the adaptation recorded in SPEC M.4 by A.U15.26); NTP (STA-IP gate, bounded fetch and retries, 12 h
  default, offset-before-clock, age with unsynced marker, resync after a settings change — held; `Synced` cleared on a
  settings change — fixed by A.U18.21; live GMT/DST — adaptation, no loss); NeoPixel (pending-command refusal — fixed by
  A.U9.02/A.U9.03; ramp floor, overlay restore, Wi-Fi LED, colour mapping, interval from loop start — held). Sites are
  read by symbol (U10/U18/U20 renames and moves shift every cited line: e.g. the colour mapping now lives in
  validate per M.GEN.013). Only owner questions and fixes are written (OR48.a (3) "no list or permanent record").
- **Resolved**: line drift — read by symbol (D5).
- **Unit**: U32 (sync point).
- **Depends**: A.U9.02, A.U9.03, A.U15.26, A.U18.21; M.PROC.014.
- **Blast carried by**: the fixes' own tests (A.U9.02/A.U9.03, A.U15.26, A.U18.21 — their clusters); M.GEN.009/.013
  (read, colour mapping held).
- **Kind**: test (audit check)

## P5 — B3: the test-integrity campaign (U35)

### M.PROC.022 Open the B3 working files; the campaign ends when every row is terminal
- **From**: A.U35.01.
- **Site**: new `audit/b3/` (audit working files, deleted with `audit/` at phase D).
- **Change**: each file with a one-paragraph header naming its requirement and its completion criterion: `review.md`
  (one row per test: file:line, name, level, verdict biting/weak/blank, red flag, fix or "biting as is"), `faults.md`
  (module, fault, site, catching tests, survivor → action), `intent.md` and `levels.md` (M.PROC.023), `matrices.md`
  (assembly dimensions; actor × resource), `timing.md` (per level and stage: wall clock, peak RSS, host SSD writes, test
  counts; B0 and post-refresh columns from M.PROC.007/.012), `load.md` (resource × level cells and the OR49.a (3)
  entries), `e51.md`, `raising.md` (M.PROC.025), `conformance.md` (M.PROC.026/.027), `queue_c.md` (M.PROC.029). A defect
  any file records goes the OR12.a path (fix with a regression test first, or an owner question), never a note alone,
  and passes A-C as a delta before it is applied (OR106.a). Complete when every row of every file is terminal (biting,
  fixed, or justified with its reason).
- **Resolved**: —
- **Unit**: U35 (start of B3).
- **Depends**: B2 complete (U10-U34); M.PROC.012 (the post-refresh column).
- **Blast carried by**: the OR49.a (3) entries → M.PROC.034 (report, PR description); the campaign's runs → M.SCR.006/
  .024/.060 (A.U35.02).
- **Kind**: rule

### M.PROC.023 Map intent per layer and every file to the levels that test it
- **From**: A.U35.07.
- **Site**: `audit/b3/intent.md`, `audit/b3/levels.md`.
- **Change**: as A.U35.07 (1)-(2): the intent map per layer (function, module, functional integration, system
  integration), one row per intent item with its cited source, mechanically derived where possible (an `ast` walk of
  every `raise`/`except`/catalog-code site, each schema field's bounds, `None`, NaN/±inf for float fields), each mapped to
  biting tests; an unmapped item gets a test at the lowest layer that can prove it; a test proving no item is tied or
  removed with a register entry (OR33.a); every module has a direct row and a real-chain row. The file × level matrix
  covers every file of `src/`, the generated modules, `buildgen/`, `toolchain/`, `scripts/`, `digital_twin/`, `js/` and
  CI against L0-L4; a gap is filled at the lowest level that can prove it; single-device narrowings name the row covering
  the other devices. New tests land in their owning tier's file, each with its `audit/b3/` row.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: A.U35.03, A.U35.04; A.U2.01 (catalog), A.U25.48 (derived devices), A.U7.24 (containment test).
- **Blast carried by**: new tests per gap (deltas, their tiers); SPEC E.2.1 "stay wozi-only" → U36 (SPEC).
- **Kind**: test

### M.PROC.024 Cross a real 2**30 tick wrap with a scratch Unix build
- **From**: A.U35.32.
- **Site**: scratch only — a copy of the pinned (post-refresh) Unix-port build under the scratchpad, never `toolchain/`,
  never committed; `audit/sweeps/ticks30_build.sh` (deleted at close).
- **Change**: as A.U35.32: `build-ticks30` with `CFLAGS_EXTRA='-DMICROPY_PY_TIME_TICKS_PERIOD=(1<<30)'` and a scratch
  patch to `mp_hal_ticks_ms()`/`mp_hal_ticks_us()` adding a start offset read from `TICKS30_WRAP_IN_MS`, re-applied to
  the refreshed pin's `unix_mphal.c` (sites re-mapped per M.PROC.013); (1) every L1 file using ticks at both GC stages,
  three runs per file per stage with the wrap at a quarter, half and three quarters of that file's measured wall clock
  (`timing.md`); (2) the twin suite per derived device with the wrap inside Run 11's window; (3) a failure is a G5/R10
  defect fixed with an L1 test using `Ticks30Time`. Recorded in `timing.md`; nothing kept. Runs on tmpfs inside
  M.PROC.001 (4)'s repeat budget (three runs per file is confirmation-scale).
- **Resolved**: —
- **Unit**: U35.
- **Depends**: A.U14.32, A.U14.33, A.U14.34, A.U17.06, A.U15.35, A.U35.23; M.PROC.012.
- **Blast carried by**: SPEC F.1's sentence "wrap safety was run once on a 2**30-period Unix build started just before
  the wrap (agent, <date>)" → SPEC (A.U14.32's text, U35 stage; Gaps); fixes → their tiers.
- **Kind**: test

### M.PROC.025 Map every raising call in the never-raise modules
- **From**: A.U35.36.
- **Site**: the seven modules as B2 leaves them (`asy_base_classes.py`, `asy_config_manager.py`, `asy_print_log.py`,
  `asy_system_service.py`, `asy_fram_manager.py`, `asy_fram_driver.py` outside its one-time init/setup errors,
  `math_helpers.py`); `audit/b3/raising.md`; the pinned (refreshed) MicroPython sources.
- **Change**: per module an `ast` walk lists every call outside a `try` that catches it and every `raise`; each
  classified from the pinned source (e.g. `bytearray(n)` → `MemoryError`/`OverflowError`, `json.dump` → `OSError`/
  `MemoryError`/`ValueError`, `struct.pack_into` → `ValueError`, `open()` → `OSError`, unproven dict/list indexing) as
  handled (the catching `except`), unreachable (with the proof — an E.5.1 verdict), or a defect, fixed at the right layer
  with a test injecting the raise through a substituted module name and asserting the sentinel. Special attention: task
  tops, Timer/IRQ callbacks, Microdot handlers and the response-writing gap (SPEC A.5), every widened `except`.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: M.PROC.022; B2's code actions on these modules (M.SRC_CORE merges).
- **Blast carried by**: M.SRC_CORE.130 (math_helpers catches kept and exercised, read); the module headers' "never
  raises" line (SPEC D.2) stays true; fixes → SRC_CORE/TEST_UNIT deltas.
- **Kind**: test

### M.PROC.026 Every recovery rung is tested at every level that reaches it
- **From**: A.U35.52; OR113.a (2) ("Apply this idea throughout!").
- **Site**: `audit/b3/conformance.md`; `SUPP_recovery.md`'s rung tables and the actions it names.
- **Change**: one row per (fault path, rung R1-R7) with the test reaching it at L1, L2, L3 and L4, or "not reachable at
  <level>: <reason>" (e.g. no held-line injection at L4, OR45.a (3)); each row names the test proving the rung bounded
  (driven clock or iteration bound), logged once per event (one entry, a repeat raising the count only, OR35.b) and
  race-free (a forced interleaving with a concurrent sibling, OR109.a). A missing cell gets its test at the lowest level
  that can prove it; L3/L4 cells join `queue_c.md` (M.PROC.029). The supervisor rungs' failure classes are A.U35.30/.31.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: the rung actions (A.U10.R01, A.U13.R01-R02, A.U14.R01, A.U14.17, A.U15.R01-R05, A.U16.R01-R03, A.U17.33,
  A.U18.R01, A.U25.36, A.U26.34); A.U35.30, A.U35.31.
- **Blast carried by**: SPEC F.2 ladder text naming where each rung is tested → A.U14.R01 (SPEC, U36 places it).
- **Kind**: test

### M.PROC.027 The owner's latest test demands are met at every level
- **From**: A.U35.53; AC_NOTES 21, 24; OR115.a, OR116.a/OR123.a, OR118.a/OR122.a, OR120.a (3), OR126.a (3), OR130.a.
- **Site**: `audit/b3/conformance.md`.
- **Change**: a checklist per owner row × level × test type, each cell the test (file:name) after B2, run in the B3
  campaign at both GC stages: (1) OR115 — each modlwip hammer test asserts its reach (an `EAGAIN` observed while a
  zero-timeout poll reported writable); A.U21.13's one-time unpatched control run executed here (not in CI): tests (1),
  (2), (3), (7) fail on the unpatched copy, recorded in `faults.md`; A.U19.24's L1 reach is the fake's `EAGAIN` count; a
  failed bound on the patched copy goes to the owner per AC_NOTES 21 (a POLLOUT back-off as a change to OR114). (2)
  OR116/OR123 — the CRC16 arm at L1, L2 (twin pair, both modes), L3 (the device-script pair over the jumper), L4 (the
  reflash run, phase C R4). (3) OR122.a — `resetconfig`, `erasefram`, `reboot`, `bootloader`: function, refusal and error
  paths, near-miss words refused as "Invalid", the OR119.a states raced deterministically, bus and storage hazards,
  watchdog takeover/healthy/hung-step, power loss per step, both GC stages — L0/L1/L2 run here, L3/L4 queued. (4) OR130 —
  the two supervisor feed sites pinned by the L0 site check, the escalation's single feed at L1, and twin Run 3's
  escalation showing `feed_count` stop after it. A missing cell gets its test in the file the supplement names.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: A.U21.11-A.U21.14, A.U19.24, A.S0930.01-A.S0930.08, A.S0930.20-A.S0930.29, A.S0930.34-A.S0930.40,
  A.U31.07, A.U10.08, A.U25.36, A.U35.02, A.U35.04, A.U35.30.
- **Blast carried by**: the website dropdown tests → A.S0930.20 (WEB); the CRC16 Class B entry → A.S0930.07 (DOCS);
  missing cells (deltas).
- **Kind**: test

### M.PROC.028 Measure the test-tier tunables still marked "estimated"
- **From**: A.U35.56.
- **Site**: SPEC Part N test-tier rows (`l0.`-`l4.`) whose Basis reads "estimated"; the tagged literals in `tests/`,
  `tests_scripts/`, `tests_js/`, `digital_twin/`, `tests_hardware/`, `scripts/`; `audit/b3/timing.md`.
- **Change**: per row by A.U8.02's kind: a hang bound or `wait_for` limit — measured per test file, 20 runs under
  `TEST_PARALLELISM=32` on tmpfs at both GC stages, each run printing the healthy duration of every tagged bound in that
  file (one timing line per tag through A.U8.02's tag IDs); the value set to the stated margin over the measured maximum,
  Basis "measured (agent, <date>): max <x> over 20 runs at 32× parallelism"; a poll step or retry count — Basis "design
  choice" with its reason; a wait the driven clock replaced (A.U35.13-.15) — the row goes with its literal; an `l3.`/`l4.`
  row — joins `queue_c.md` and keeps "estimated" until phase C (listed in the release note). A tighter measured bound is
  adopted only with its measurement recorded (OR30.a (3)); a looser one is adopted and the test's retried-pass record
  (A.U7.04) checked for the cause. Every value change is a B3 delta (OR106.a) landing tag and row together
  (`tests_scripts/test_tunables_register.py` keeps them agreeing).
- **Resolved**: 20 runs per stage are a measurement inside M.PROC.001 (4)'s budget of ~20 repeats, on tmpfs (no host-SSD
  wear, CLAUDE.md host-I/O rule).
- **Unit**: U35.
- **Depends**: A.U8.01-A.U8.03, the U8C/U8C2 tag actions, A.U35.02, A.U35.13-A.U35.15, A.U7.04.
- **Blast carried by**: Part N rows → SPEC (B3 deltas; Gaps); tagged literals → their tiers' clusters (deltas);
  `l3.`/`l4.` rows → M.PROC.029, phase C (A.C.10, M.HW_BENCH.050/.120); release-note list → A.U37.12 (DOCS).
- **Kind**: test, doc

### M.PROC.029 Prepare B3's real-hardware items for the phase-C rounds
- **From**: A.U35.54.
- **Site**: `audit/b3/queue_c.md` (handed to U37, which writes BACKLOG's "Real-hardware work still owed").
- **Change**: the B3 items needing silicon, each with level, gate, twin-first record and the property it proves: the
  silicon arm of the hardware `MemoryError` gates (A.U35.05 (3) → R1, M.PROC.037); the lone-BMP3xx general call
  (A.U35.21, flash, R1); the torn-write expectation on the bench reset race (A.U35.40, bench, `persistence_write`, R3); the
  silicon-only interaction, recombination and rung cells (A.U35.08, A.U35.09, M.PROC.026; R1 H71); the OR115 phase-C
  reproduction then the override (A.U21.14; R4 H39); the OR116 CRC16 L3 script and L4 reflash run (A.S0930.05/.06; R1
  H37, R4 H38); the four `SystemCmd` words on the board (A.S0930.28/.29/.39/.40; R1-R3 H13/H14); the two-image GC proof
  (R7 H45); the bench trigger timestamps for the read stagger (R5 H19); the speed-probe bands on the bench Pi4 with no
  board (A.U35.23; R0 H56); the `l3.`/`l4.` tunable rows (M.PROC.028; R1/R4/R5 H55). Per round: lower levels first on the
  same commit, FRAM logs read and saved first, standard board state at start and end, wear gates default-off unless the
  round's plan names one. Every row maps to a `C.md` inventory row H01-H83; a row with none is added to both (A.U37.05).
  Nothing here runs in B3.
- **Resolved**: —
- **Unit**: U35.
- **Depends**: A.U35.49 (twin-first records); the actions listed.
- **Blast carried by**: BACKLOG's owed section → A.U37.05 (DOCS); the rounds → P7.
- **Kind**: hardware (preparation)

## P6 — U37: the close of execution (B5)

### M.PROC.030 U37 runs in one fixed order
- **From**: A.U37.01; OR129.a (1) (the second dependency check at B5).
- **Site**: the register header's U37 row; `audit/b5/close.md` (audit file).
- **Change**: in order: (1) cleanup — A.U37.02 (empty allow-lists removed: M.TSC/M.TOOL/M.TWIN carriers), A.U37.03 (stray
  files, recorded worktrees and scratch branches); (2) the second dependency check, M.PROC.031; (3) the closing documents
  — A.U37.04 (knowledge base, twin fidelity, side obligations), A.U37.05 (BACKLOG owed list from `C.md` and
  `queue_c.md`), A.U37.06 (BACKLOG end state), A.U37.08 (CLAUDE.md agreements), A.U37.10 (golden fixtures), A.U37.11 (the
  release version `2.0`, agent decision on the owner's behalf), A.U37.12 (release note, naming the pins of (2)); (4) the
  re-verification passes, M.PROC.032, until one ends all green; (5) M.PROC.033 (register terminal, owner-row and
  test-integrity trace); (6) M.PROC.034 (final report) and M.PROC.035 (owner review); then U37's sync point (M.PROC.001
  (6)). Phase C follows (P7), each round with its own go-ahead; its deltas pass A-C (OR106.a) and are followed by one more
  pass (M.PROC.043 (3)); then phase D (M.PROC.044). Any change after step (4), a phase-C delta included, re-opens step (4)
  for one pass before the next step runs.
- **Resolved**: —
- **Unit**: U37.
- **Depends**: U0-U36 closed; A-C's list applied.
- **Blast carried by**: each step's merge (named); the closing documents → M_DOCS (A.U37.04-.06, .08, .11, .12), M.GEN.018/
  .021/.033 (A.U37.10/.11 code).
- **Kind**: rule (audit file)

### M.PROC.031 U37: check for releases made during execution
- **From**: A.SDEP.25.
- **Site**: U37 step (2); the refresh record (audit file).
- **Change**: for every inventory line D1-D28 and every pin execution added (`[stubs]` in `versions.toml`, A.U27.02;
  `[tool.uv] required-version`, A.U28.02; the `coverage` pin, A.U24.72/A.U28.02; the dorny commit, A.U28.13; the Microdot
  hash table, A.U19.18; the freezefs commit, A.U34.08; A.U21.03's toolchain-record fields), the pinned value is compared
  with the newest stable found by M.PROC.008's commands; every hold-back of M.PROC.008 (4) and every F.5.10 upstream item
  (issue 19704 included) re-read. Nothing new → one line in the record, and CLAUDE.md's "Last run" line re-dated. A new
  release → that family's step and the workaround checks it touches run for it, with U37's re-verification passes
  (M.PROC.032) as the check gate in place of M.PROC.009; the permanent records updated (A.SDEP.21's sites); a MicroPython
  move extends phase C's hardware entry to the newer pin (row H60); the permanent texts citing the moved source re-checked
  by A.SDEP.08 (4)'s platform re-check; M.PROC.013 (2) applies to every action not yet executed. The release note
  (A.U37.12) names the pins the release ships with.
- **Resolved**: —
- **Unit**: U37 (step (2)).
- **Depends**: U0-U36 executed; M.PROC.008-M.PROC.013.
- **Blast carried by**: CLAUDE.md "Last run" re-date and F.5/F.5.10, BACKLOG records → A.SDEP.21 sites (DOCS/SPEC, U37
  stage — Gaps); pins → M.TOOL.024/.061/.073/.077/.078, M.SCR.027 (re-check, U37 stage); release note → A.U37.12 (DOCS).
- **Kind**: rule, code, doc

### M.PROC.032 Re-verify every rule until one pass ends all green
- **From**: A.U37.07; OR9/OR9.a.
- **Site**: the whole tree at the tip; `audit/b5/pass-<n>.md` per pass (audit files).
- **Change**: a pass is: (1) the rule sweep — every CLAUDE.md hard rule and working agreement, every SPECIFICATION.md
  Part's normative statements (D's checklist, G's catalog with its G.3 shape-grep, I.4's memory scheme, J's UART contract,
  L's schema and TOML rules), OR51's pre-merge gate and OR24.a's consistency, the plan 4.2 lenses per area, applied file
  by file to every file changed since the previous pass and, in the first pass, to every in-scope file; (2) M.PROC.002's
  full suite, zero `MemoryError`/`memory allocation failed` markers in every gate at both GC stages; (3) push and CI
  green, watched through the event subscription only. A finding is fixed in the pass (tests first where behaviour
  changes, OR12.a) and the pass continues; the next pass starts after this one completes. U37's step (4) ends when a
  pass records no finding, every level green and CI green; no cap on passes; each pass's findings list kept for the
  report.
- **Resolved**: A.U37.07 (2)'s command list and the other gates' lists are one set (M.PROC.002, D2).
- **Unit**: U37 (step (4)); again after the last phase-C delta (M.PROC.043 (3)) and after phase D's deletion commit
  (A.U37.15's suite run).
- **Depends**: A.U37.02-A.U37.06, A.U37.08, A.U37.10-A.U37.12, M.PROC.031.
- **Blast carried by**: per finding (its cluster's files; a `src/asy_uart_comm.py` change gets its changelog entry).
- **Kind**: test, rule

### M.PROC.033 Every register entry terminal; every owner row and test-integrity item traced
- **From**: A.U37.09, A.U37.17.
- **Site**: `audit/REGISTER.md`, `audit/pass2/*.md` State lines, `audit/pass2/INDEX.md` (regenerated by
  `audit/sweeps/pass2_index.py`), `audit/CONSOLIDATION.md` section 4, `audit/b5/close.md`; the coverage report of the last
  pass.
- **Change**: (1) every `AF-*` entry has one terminal 4.5 status with `re-verified@HEAD`; only `moved-to-hardware` stays
  open, each naming its `C.md` row, closing in phase C (M.PROC.043 (2)); a `plausible` entry is a finding of the pass;
  every pass-2 State reads "holds" with its action or commit, or names its phase-C row; every unit `closed@<sha>`; every
  area lists all 18 lenses "applied" or "N/A, because …"; every rejected seed with real rediscovery risk has its permanent
  note. (2) Every owner row OR1-OR133 (with each .a/.b/.c; the DoD's "OR1-OR83" read as the current last row) maps to its
  register entries or is marked audit-process-only, and is met at the tip or names its phase-C row; unmet rows are pass
  findings. (3) `git diff --stat <audit baseline>..HEAD -- tests tests_scripts tests_hardware tests_js digital_twin` and
  `git log -p` over the same paths read for deleted test functions and removed or loosened assertions: each has a
  register entry saying why (OR33.a), else a finding. (4) The last pass's unexecuted lines in `src/`, generated code and
  the build chain each covered or on U35's reason list; a new one is a finding.
- **Resolved**: A.U37.17's DoD range predates OR84-OR133; read as OR1-OR133 (its own text).
- **Unit**: U37 (step (5)).
- **Depends**: M.PROC.032 (its last pass and coverage run).
- **Blast carried by**: audit files only; findings → M.PROC.032.
- **Kind**: rule (audit file)

### M.PROC.034 Report the end of execution in chat and in PR #107
- **From**: A.U37.13.
- **Site**: the chat reply closing B5; PR #107's description (`mcp__github__update_pull_request`).
- **Change**: one report: the release note (A.U37.12); the load-test entries from `audit/b3/load.md` in OR49.a (3)'s five
  fields (gap closed, load applied, where the limit sits, how it degrades, that it recovers); before/after tables from
  `timing.md` and the baseline record (both columns, M.PROC.007/.012) per level and GC stage (counts, wall clock, peak
  memory, coverage per `src/` file, generated code and host build chain, image sizes per device); the re-verification
  passes and their finding counts; the owner-review list (M.PROC.035); the phase-C plan (`C.md`'s eight rounds, their
  go-ahead requirement and wear budgets, M.PROC.036); what remains owed (BACKLOG's four kinds). The PR description is
  replaced, ending with the attribution lines the session reminder names; no audit ID in the release-note part.
- **Resolved**: —
- **Unit**: U37 (step (6)).
- **Depends**: M.PROC.032, M.PROC.033, A.U37.12, M.PROC.035.
- **Blast carried by**: none in the tree.
- **Kind**: doc (report)

### M.PROC.035 The owner reviews every decision taken on the owner's behalf
- **From**: A.U37.14; AC_NOTES 16, 21, 24, 34-second, 37; A.U29.04 (3) (secret scanning setting); A.U34.11 (TOOL's PROC
  routing: the `disallow_any_unimported` count parked for the owner); OR2.c.
- **Site**: the register header's owner-review list; `audit/actions/AC_NOTES.md`; every permanent text carrying a reviewed
  decision (found by its own text, grep).
- **Change**: (1) Two reviews: at the A-C review (before execution, OR106.a: the go-ahead is given on the merged list),
  every "Agent decisions for the OR2.c review" section of the A-C merges and every AC_NOTES lead decision marked for the
  owner is shown; at B5's end, the list is assembled from the register header, every `on-behalf: yes` entry, every OR12.a/
  OR13.a/OR24.a logged change, the refresh's hold-backs and parked items (M.PROC.008 (4)-(5)), the GitHub secret-scanning
  repository setting (M.PROC.020 — a setting, never changed by the executor), A.U34.11's parked count, and this unit's own
  decision, the release version `2.0` (A.U37.11, agent, 2026-09-30) — each in the owner's format (a decision in ≤ 10
  words, then options each with its consequence, OR51.a (3)); items the owner already answered (OR126.a (5): the U17 Q1,
  border-cue and hang-cause corrections; OR119.a (5)) are listed as reviewed, not asked again. (2) Per answer: kept → each
  permanent "(agent, <date>)" on it becomes "(agent, <date>; owner-reviewed, <answer date>)"; overruled → the owner's
  words with "(owner, <date>)" replace it and the change goes the normal path (tests first, then a pass, M.PROC.032).
  (3) Every AC_NOTES item confirmed landed (its action executed or its conflict merged as noted) before `audit/` is
  deleted; AC_NOTES goes with `audit/` at phase D.
- **Resolved**: —
- **Unit**: A-C review (part 1, before execution); U37 step (6) (the rest).
- **Depends**: M.PROC.033; LEAD/R16's rule text (U36, DOCS).
- **Blast carried by**: per overruled decision (its cluster); the decision-vocabulary check accepts the reviewed form
  (A.U0.09, TSC).
- **Kind**: rule, doc

## P7 — Phase C: the hardware rounds on the dev bench

Standing for every step below (CLAUDE.md, C.md header): nothing runs on a board, the bench Pi or the bench network
without the owner's go-ahead given in that round's own conversation — "a go-ahead given to a different session, or to an
earlier session that already ended, does not carry over"; "once granted, it covers the rest of that same conversation";
subagents and child sessions inherit none. Only `dev` is ever flashed, with a dev-native image built from its own TOML
through its own generated entry point; `wozi` and the four field units are never flashed or connected. The FRAM error
logs are read and saved before anything writes to the board (CLAUDE.md FRAM rule; its first-chunk caveat stated in every
record). Wear spends only what the round's plan names, behind its marker.

### M.PROC.036 Phase C runs R0-R7 in one order under one frame
- **From**: A.C.11 (1) (inventory rows delivered or re-queued), H01-H83 (`C.md` inventory), A.U37.01 (phase C after U37);
  read for the order: A.C.01-A.C.06, A.C.10, A.C.12-A.C.17, A.C.19 (merged into their files by HW_BENCH/HW_DEV/SCR/TWIN:
  M.HW_BENCH.006/.060/.123 frame, .120 bench facts, .102 power-cycle steps, .075 lwIP pair, .083/.119 reset codes,
  .130 budget table; M.HW_DEV.010/.055/.152/.154; M.SCR.006/.030-.034).
- **Site**: round records `audit/c/R<n>.md` (audit working files, deleted at phase D); the dev bench; the bench Pi4.
- **Change**: (1) **Every round** (A.C.01, permanent text in `tests_hardware/README.md` "How a round runs",
  M.HW_BENCH.123): go-ahead quoted with its date at the top of the record, then the plan — rows in order, each with its
  expected outcome, its wear (flash writes, SCD30 NVM writes, flash cycles; FRAM is not wear) and the twin parameter or
  fidelity row it confirms; bench host network checked (uplink route; `br0`'s MAC equals the uplink's real MAC, a mismatch
  stops the round for the owner, never auto-repaired) and B.13's recovery switch armed, confirmed, polled after and
  disarmed around every step that touches `br0` or a slave (bridge creation, the manual recipe, every bench-tier run);
  evidence first (`fram_evidence_saved`: `/status` over `--dut-ip` before any raw-REPL entry, then the raw FRAM dump;
  copied into the round record); lower levels on the recorded commit (`scripts/_run_lower_levels.sh`; never
  `--skip-lower-levels` for a reported result); the image built with `scripts/build_firmware.py <bench device>` (the bench
  device from data, never `wozi`) with its image record, flashed through the one `reflash()` helper as the round's
  planned prerequisite write; the image proof (`board_image`) and the standard state (`standard_state`) at start and end;
  default flash tier then default bench tier (`scripts/run_bench_hardware_suite.sh`), each verdict's deselected count
  recorded; a gated run only after a clean default run of the same image record in the same conversation; ad-hoc scripts
  under `timeout`, retries capped; the board left on the round's release image in the standard state, the final
  `errcount`, every `ResetReason` seen, the boot log and every figure with its image recorded. An unanticipated red stops
  the round at that row and is reported with its evidence; nothing is retried to green, no bound widened, no hardware item
  decided in the session (OR2.c). A rare event is triggered by a small dedicated script or recorded "not reproducible"
  with what was tried (LEAD/R27). (2) **After each round** (A.C.10): findings pass A-C as a delta before they are applied
  (OR106.a); the twin and its fidelity rows change only on solid silicon evidence (OR17.a (3)); a measured Part N row takes
  Basis "measured (dev, <date>, <image build date>)"; the `ResetErrors` bench budget becomes a tagged constant from R1's
  figures (M.HW_BENCH.050); each delivered BACKLOG owed row leaves with every citation of it; lower levels touched by a
  delta run at both GC stages before the next round. (3) **Order**: R0 host (A.C.02: no board; host record, sudo/
  `--preserve-env`/`nmcli edit`/picotool checks, uv version equals `[tool.uv] required-version`, `env --tier bench` with
  the installer's armed recovery — the fresh-bridge proof only if the go-ahead names it —, stale packages reported and
  removed only if the go-ahead names them, the GCC ≥ 14 mbedtls build if no trixie chroot did it, the speed probe ×10 with
  no board, the owner's DHCP-keying and BME688 confirmations, step timings and the host lwIP hammer); R1 first contact
  then the release candidate's default run (A.C.03: first contact read-only — REST bodies, `reset_cause()`, raw FRAM dump,
  every `config_*.cfg`, the CRC32 "before" probe — then the default tiers, the R1 rows of the inventory, the measurements
  of A.C.03 (4), M.PROC.038's hand rows H78-H81, and last M.PROC.037); R2 operator round (A.C.04, M.PROC.039's budget
  stated first: M1 rig geometry, manual rungs, the power-cycle and power-cut steps, scope rows only if the owner provides
  a scope, the browser pass with the head capture, the field units' TOML check by the owner without flashing); R3 gated
  wear run (A.C.05: `--allow-persistence-write`, then with `--allow-scd30-extra-write`, then `--allow-neopixel-sweep
  --allow-persistence-write`; the role reversal's destructive stage 6 last, its USB recovery named before it); R4 the
  `flash_cycle` rows (A.C.06: the lwIP pair — control image first, then the override on the release image —, the CRC16
  reflash run, the reflash smoke test, `--allow-toolchain-reverify` once, H82 only if planned, M.PROC.038); R5 soak
  (M.PROC.040); R6 rollover (M.PROC.041); R7 release proof, last (M.PROC.042). Inventory rows marked "co-land" run inside
  their round's suite run; "own" rows are the round's steps. H76 (the UART babbling peer) stays owed (owner, 2026-09-25);
  H77 is withdrawn (AC_NOTES 11, 23). (4) **A moved firmware pin** (refresh or M.PROC.031): R1 and R5 run on the pin the
  tree carries, with the F.5 on-target confirmations and `sys.implementation` (row H60); a failure on the moved pin goes
  to the owner with the choice to hold the pin back (OR129.a (5)).
- **Resolved**: the per-round go-ahead (CLAUDE.md) against the one-conversation gated-after-default rule (G1/R02): a new
  conversation or a changed image runs the default tiers again first (owner D1, 2026-09-22) — C.md's settled reading,
  kept.
- **Unit**: phase C (after U37's sync point, before phase D).
- **Depends**: M.PROC.030; A.C.01's listed actions executed; M.PROC.029 (`queue_c.md`).
- **Blast carried by**: the instruments → HW_BENCH/HW_DEV/SCR merges named in From; the permanent results → A.C.10's
  sites (SPEC F/I/C/H/M/B.14, Part N, `tests_hardware/README.md` bench facts and rig, `error_log_helpers.py` budget,
  TOML origin comments, BACKLOG owed rows) as deltas; twin parameters → M.TWIN.010/.012/.013/.040/.059 (A.C.10).
- **Kind**: hardware, rule

### M.PROC.037 R1, last: the hardware allocation gates fail on a real caught failure
- **From**: A.C.18; A.U35.05 (3) (the silicon arm), A.U20.04 (caught failure prints `memory allocation failed`).
- **Site**: a throwaway worktree of R1's commit (planted device script and one planted flash and one planted bench test,
  never committed); the flash and bench runners.
- **Change**: after R1's clean verdict is recorded: (1) in the throwaway worktree, a planted script allocates 4 KiB blocks
  into a list until `MemoryError`, prints `str(e)` (the product's logging form), releases the list and prints `DONE`; one
  planted flash test and one planted bench test run it through `run_isolated()`; the plant satisfies every L0
  device-script guard (watchdog armed and fed, header, facts from `BENCH`) and carries no marker (it persists nothing).
  (2) `scripts/run_flash_hardware_suite.sh -k <planted>` and `scripts/run_bench_hardware_suite.sh -k <planted>
  --image-record <R1's image record>` from that worktree, without `--skip-lower-levels` (the plant does not change any
  lower level, so they pass and the runners reach the board). (3) Both verdicts must be red naming the allocation marker
  (`MEMORY_ERROR_MARKERS`), and the printed text must contain `memory allocation failed` on silicon (the emergency
  exception buffer in effect). Expected red, recorded as such in R1's record; a green verdict is a gate defect, fixed in
  the gate as a delta (A.U35.05), never by changing the plant. (4) Worktree removed; the board's end state checked by the
  session fixtures. Wear: none.
- **Resolved**: a planted script tripping an L0 guard would stop the runner before the board and never reach the gate
  under test; the plant is written to pass the guards rather than skipping lower levels (a skipped run reports NOT CLEAN,
  which would mask the red the check exists for) — agent decision D6.
- **Unit**: phase C, R1 (end).
- **Depends**: A.U20.04, A.U26.47, A.U35.05, A.C.03 (R1's clean verdict).
- **Blast carried by**: the gate itself → M.HW_BENCH.016 (marker set) and M.SCR.030/.031/.034 (runners, verdict); the twin
  arm → A.U35.05 (3) (SCR M.SCR.047).
- **Kind**: test, hardware

### M.PROC.038 The hand-run rows H78-H82: instruments and records
- **From**: M_HW_BENCH GAP-B8 (H78-H82 "own step"/"own record" with no instrument in any action); A.C.03 (4), A.C.06 (5)
  (read); A.U2.13 (H78), A.U10.13 (H79), A.U9.04 (H80), SUPP_recovery closing note (H81), A.U18.43/A.SDEP.17 W42 (H82).
- **Site**: the round records `audit/c/R1.md`, `audit/c/R4.md`; ad-hoc scripts and commands saved verbatim in the record
  (none committed).
- **Change**: each row is run by hand under the armed network switch where it touches the bench network, each script
  under `timeout` with retries capped, and recorded with its image: (H78, R1) with the board serving, the bench Pi blocks
  the DUT's UDP 123 through `bench_control`'s fault helper (the same mechanism the bench network tests use) for longer than
  the `SGPWaitTimeNTP` read from `GET /sensors`, then unblocks; twice; `GET /status` after each shows one SGP40 entry
  (today's wrnno 35 / `W13`, the catalog name after U2) per outage and `ErrCount` rising per backup; zero wear. (H79, R1)
  after the default tiers, one read-only script under `timeout` builds each driver of the bench device over its bench-facts
  bus and address, feeds the watchdog, and times 100 product reads per driver; the maximum per driver is the
  `stagger.min_read_separation_ms` input (A.U10.13). (H80, R1) with the bench API load running (the bench tier's load
  helper), `lightCmdLED` PUTs (dispatch-only, persist nothing) with known ramp times; the ramp's start and end are taken
  from the product's DebugLevel-5 console lines captured on arrival through the boot-log capture path; the longest wall time
  is the `_MAX_SIGNAL_S` input (A.U9.04); if the image logs no such line, the row is recorded "no instrument on this image".
  (H81, R1) the failure count at which each rung fired, read from the rung tests' recorded facts of the default run
  (participant 2nd, bus clear 3rd, controller 4th failure; FRAM probe 2nd; three identification attempts); a rung test that
  does not report its count is recorded so. (H82, R4, only if the round's plan names it) a local-only image built in a
  throwaway worktree with the 100 ms settle before `status("stations")` removed, flashed through `reflash()`, the bench
  joining and leaving the DUT's hotspot ten times inside the armed switch, the station count read each time and compared
  with the joined count; the round's standard image reflashed at once (2 flash cycles in R4's budget). A row whose result
  should be repeatable comes back as an A.C.10 delta (a gated bench test in HW_BENCH), not as a permanent ad-hoc script.
- **Resolved**: GAP-B8's "the round runs them by hand under the armed switch" adopted; the instruments above are the
  concrete hand steps — agent decision D7.
- **Unit**: phase C, R1 (H78-H81), R4 (H82).
- **Depends**: M.PROC.036; R1's default run (H79-H81 read its outputs).
- **Blast carried by**: Part N rows `stagger.min_read_separation_ms`, `_MAX_SIGNAL_S`, the ladder thresholds → A.C.10 deltas
  (SPEC); the `stations` settle removal → A.U18.43's trigger (SRC_NET, delta); BACKLOG "Not yet confirmed on silicon" (1)
  → A.U37.05 (DOCS).
- **Kind**: hardware

### M.PROC.039 R2's plan states its write budget before the operator starts
- **From**: M_HW_BENCH GAP-B9; A.C.04 (Blast "Wear"), M.HW_BENCH.102 (the manual steps' writes), A.C.17.
- **Site**: `audit/c/R2.md` (the plan section, written before step (1) of A.C.04).
- **Change**: R2's plan lists, before the owner starts, every write the round spends, with the step that spends it:
  `manual_persistence.py`'s flash-config step — 2 flash writes (the value and its restore); its SCD30 NVM step — 2 SCD30
  NVM writes (`MeasInterval` changed and restored, stated in the step before it runs, M.HW_BENCH.102 (2)); the
  config-write power cut (A.C.17) — ≤ 60 scratch flash writes and 3 removals over its three repetitions; the `resetconfig`
  power cut — the deletions it completes plus one restore write per config file; the `erasefram` power cut — FRAM erases
  only (FRAM is not wear, listed for the evidence they overwrite: evidence saved first); power cycles — none; the browser
  pass — none (a no-op Apply answers "Unchanged"). The operator confirms the budget in the conversation before step (1);
  any step that would spend beyond it stops for the owner.
- **Resolved**: A.C.04's Wear line omitted the SCD30 NVM step M.HW_BENCH.102 (2) adds; the budget names it.
- **Unit**: phase C, R2.
- **Depends**: M.PROC.036; A.C.03 (clean default run of the same image).
- **Blast carried by**: `tests_hardware/README.md` budget table → M.HW_BENCH.130 (its manual rows list the same writes).
- **Kind**: hardware, rule

### M.PROC.040 R5: the soak durations on top of a clean bench run
- **From**: A.C.07.
- **Site**: `scripts/run_bench_soak_tests.sh --duration {short,mid,long}` (M.SCR.032); `audit/c/R5.md`.
- **Change**: on the release-candidate image, after a clean default bench run of that same image record in the same
  conversation (the soak runner runs no lower levels): `--duration short` — SGP40 cadence (A.U15.20); `--duration mid` —
  the liveness tests (A.U26.35); `--duration long` (6 h, S4) — the liveness tests with the request-failure rate measured
  (`l4.soak_request_failure_rate`), the trigger spacing over the window at `DebugLevel` 5 with the stagger read from the
  generated module (A.U26.41 (2)), and the FRC readiness windows (A.U26.84) with the room stable and unoccupied; each figure
  recorded with its image. A moved pin adds nothing beyond running on it (H60). Wear: none.
- **Resolved**: —
- **Unit**: phase C, R5.
- **Depends**: A.C.03; A.U15.20, A.U26.35, A.U26.41, A.U26.84.
- **Blast carried by**: Part N rows (`sens.scd30_frc_*`, `l4.soak_*`), SPEC C.9.1's measured separation → A.C.10 deltas
  (SPEC); the trigger distribution vs the twin's sequencer → A.C.10 (TWIN).
- **Kind**: hardware

### M.PROC.041 R6: the 12.4-day rollover run, the board touched by nothing else
- **From**: A.C.08.
- **Site**: `tests_hardware/bench/test_ticks_ms_rollover.py` (M.HW_BENCH.089) with `--allow-multi-day-rollover`;
  `audit/c/R6.md`.
- **Change**: on the release-candidate image, after R5, with no other round running on the board for the window: started
  through the clean-run wrapper with the rollover floor — `scripts/_require_clean_hardware_run.sh --runner rollover
  --levels "rollover (not a level)" --marker-floor "multi_day_rollover" tests_hardware/bench/test_ticks_ms_rollover.py
  --allow-multi-day-rollover` (no runner selects the marker: the flash and bench floors exclude it, the soak floor is
  `soak_duration`) — detached on the bench Pi under `timeout` of the window plus margin; the network switch armed across
  the session-start fixtures (the stale-credential scan may take the AP slave down) and disarmed once the hourly REST
  polls begin (they change no network state); runs until `SysUptime` passes `2**30 / 1000 + 3600` s. If the conversation
  that started it ends, nothing further is sent to the board or the bench network until a new conversation's go-ahead
  names R6, which then reads the runner's log and verdict. If a later delta changes tick-handling code (grep `ticks_` in
  the delta), the owner decides whether R6 repeats; the record names the image it proved. Wear: none.
- **Resolved**: no runner selects `multi_day_rollover` (M.SCR.030/.031 floors exclude it, M.SCR.032's floor is
  `soak_duration`); R6 calls the clean-run wrapper directly, as the soak runner does, so the verdict is a recorded clean
  run — agent decision D8; SCR is asked to name the path in a runner or the README recipe (Gaps).
- **Unit**: phase C, R6.
- **Depends**: M.PROC.040; A.U26.29, A.U26.36, A.U26.74.
- **Blast carried by**: the driven-time proofs are L1/L2 (LEAD/R04); BACKLOG's G6 row removed → A.C.10 (DOCS).
- **Kind**: hardware

### M.PROC.042 R7, last: the two-image GC proof on the final tree
- **From**: A.C.09; A.U8.06 (UART tunables on both images); OR40.a (3).
- **Site**: `audit/c/R7.md`; the no-threshold image from a throwaway worktree; the release image from the final commit.
- **Change**: only after every phase-C delta is applied and one re-verification pass on that tree ended all green
  (M.PROC.043 (3)): (1) the no-threshold image — the final commit in a throwaway worktree with the boot-entry generator's
  emitted `gc.threshold(32768)` line removed (`buildgen/codegen.py` `generate_boot_entry_source()`, the line under `#
  @tunable gc.threshold_bytes`, M.GEN.001; never committed), built (record `dirty: true`), flashed, then the full default
  flash and bench tiers with `--image-record` at that worktree's record: zero allocation markers in both hardware gates;
  (2) the release image built from the final commit, flashed, the full default flash and bench tiers again; the UART
  tunables' figures recorded on both images. The record lists the timestamped boot log, the trigger distribution (R5's
  long run if the tree has not changed since, else `scripts/run_bench_soak_tests.sh --duration long` on this image),
  every `ResetReason` observed across R1-R7 with its cause, the bench Pi's stale-package list re-checked (A.C.02 (4)), and
  the F17 verdict: every reset of phase C attributed — F17 closes; any unexplained reset is a new finding with its code
  (G1/R02). The board ends on the release image in the standard state. Wear: 2 image flashes (planned prerequisite
  writes, OR40.a (3)) plus two default runs' pinned prerequisites.
- **Resolved**: —
- **Unit**: phase C, R7 (last).
- **Depends**: M.PROC.036-M.PROC.041, M.PROC.043 (1)-(3).
- **Blast carried by**: SPEC I.4(f) release-proof record, BACKLOG item 44 and the S4/F17 rows removed → A.C.10 deltas
  (SPEC, DOCS); the image check → M.HW_BENCH.060.
- **Kind**: hardware

### M.PROC.043 Close phase C
- **From**: A.C.11.
- **Site**: the inventory H01-H83; BACKLOG "Real-hardware work still owed"; the register's `moved-to-hardware` entries.
- **Change**: (1) every inventory row delivered (its round record names the verdict) or, only by the owner's decision in a
  round conversation, re-queued as a BACKLOG owed row with its reason; H76 stays owed (owner, 2026-09-25). (2) Every
  `moved-to-hardware` register entry becomes terminal from its round result. (3) After the last delta of R1-R6: one
  re-verification pass (M.PROC.032) ends all green on the final tree; then R7 (M.PROC.042); a finding in R7 is a delta,
  then the pass and R7 repeat. (4) The owner is told the hardware phase is complete and gives the agreement that opens
  phase D.
- **Resolved**: —
- **Unit**: phase C (close).
- **Depends**: M.PROC.036-M.PROC.041.
- **Blast carried by**: BACKLOG owed section (only re-queued rows and H76 remain) → A.C.10/A.U37.05 (DOCS).
- **Kind**: rule, hardware

## P8 — Phase D

### M.PROC.044 One merge into `main`, the release tag, the audit branch kept
- **From**: A.U37.16; A.U37.15 (read: the deletion commit precedes it, DOCS-indexed).
- **Site**: PR #107; `main`; the tag.
- **Change**: with the owner's agreement that the audit is finished (asked in that conversation, quoted in the PR), after
  A.U37.15's deletion commit and its full-suite run: (1) `main` confirmed unmoved since the audit baseline (`git
  merge-base --is-ancestor origin/main HEAD`; if it moved, the owner is asked before anything); (2) PR #107 merged by a
  merge commit (`merge_method: merge`, never squash); (3) on the merge commit `uv sync` and the installed `ruff --version`/
  `mypy --version` (and every pinned tool) checked against `pyproject.toml`'s pins (CLAUDE.md `uv.lock` rule); (4) an
  annotated tag `v<FIRMWARE_VERSION>` (`v2.0` unless the owner review changed it, M.PROC.035) on the merge commit, the
  release note as its message, pushed; (5) no audit worktree, scratch branch or extra tag remains (A.U37.03 (3)); the audit
  branch itself is deleted only if the owner's agreement names it — otherwise it stays.
- **Resolved**: —
- **Unit**: phase D.
- **Depends**: A.U37.15; M.PROC.043 (4).
- **Blast carried by**: none in the tree; the release-merge check → M.TOOL.078 (read).
- **Kind**: rule (phase D)

## File edits carried elsewhere (the index missed their sites; each owning cluster merged them)

Checked by reading every finished merge's ledger and From lines (2026-10-01). "Residual" names what no merge carries yet.

| action | what it edits | carried by | residual |
|---|---|---|---|
| A.S0930.32 | `_request_shutdown()` re-check; escalation re-check; two L1 tests | M.SRC_CORE.011, .016; M.TEST_UNIT.306 | — |
| A.U2.25 | `mockdata` history codes; L0 mockdata check | M.WEB.045; M.TSC.088 | — |
| A.U3.15 | mock histories newest-entry rule; L0 check | M.WEB.045; M.TSC.088 | — |
| A.U5.02 | every module constructor's `log` tail | M.SRC_CORE (8), M.SRC_NET (12), M.SRC_SENS (10), M.TEST_UNIT, M.TEST_HELP.035, M.HW_DEV (15+), M.HW_BENCH.134, M.TWIN.064, M.GEN | AC_NOTES 1's C.7.1 cite follows A.U2.22 (SPEC) |
| A.U6.07 | `js/app.js` device list from the manifest | M.WEB.031, .059; M.GEN.060 | — |
| A.U6.11 | cross-browser smoke over every device; probe module | M.SCR.023, .063; M.TOOL.010, .019; M.WEB.073 | new L0 `test_cross_browser_smoke_probe.py` (TSC, Gaps) |
| A.U6.14 | `test_build_website_sh.py` devices from data | M.TSC.035, M.TSC.002 | — |
| A.U6.17 | `alwaysExecuted` grammar, generator, tags, mock, matrices, gate | M.GEN.015/.017/.046, M.SRC_SENS.051, M.WEB.004/.005/.041/.060/.063, M.TSC.159 | — |
| A.U8C.120 | SPEC Part N Dependants (`tests/` sites) | test-site tags: M.TWIN.124/.132/.144; M.TEST_UNIT (holds; one row withdrawn at .090) | Part N text (SPEC, Gaps) |
| A.U8C.121 | SPEC Part N Dependants (`tests_hardware/` sites) | tags per file: M.HW_DEV, M.SCR.065 | Part N text (SPEC, Gaps) |
| A.U8C2.51 | SPEC Part N Dependants (derived sites) | M.TEST_UNIT.309 | Part N text (SPEC, Gaps) |
| A.U10.18 | lock names, `async with`, `_locked` suffix | M.GEN.005, M.SRC_CORE (6), M.SRC_NET (14+), M.SRC_SENS (5), M.TEST_UNIT (13+), M.TWIN.102 | Class B UART line → DOCS (changelog) |
| A.U10.21 | one `setup() -> bool` contract | M.GEN.010, M.SRC_CORE (9), M.SRC_NET.169/.215, M.SRC_SENS (10), M.TEST_UNIT | — |
| A.U10.29 | foldable constants `const()`; `CMD_ACK`/`CMD_GET` private | M.GEN.015, M.SRC_CORE.101/.120, M.SRC_NET (10), M.TEST_UNIT.168/.282/.285 | — |
| A.U10.33 | class member order (D.15), AST-verified | M.SRC_CORE (6), M.SRC_NET (9), M.SRC_SENS (5) | — |
| A.U10.35 | test-only public attributes private | M.SRC_CORE (13+), M.SRC_NET (14+), M.SRC_SENS (12), M.TEST_HELP.028/.034, M.TEST_UNIT, M.HW_DEV.142/.143, M.SCR.026, M_TWIN convention | — |
| A.U10.39 | `_VAL_` names follow keys; private schemas | M.GEN.025, M.SRC_CORE (5), M.SRC_NET (14+), M.SRC_SENS (12), M.TEST_UNIT (5), M.HW_DEV.142 | — |
| A.U10.44 | starter and task-coroutine names | M.SRC_NET (14+), M.SRC_SENS (9), M.TEST_HELP.034, M.TEST_UNIT, M.HW_DEV (4), M.HW_BENCH.135, M.TWIN.102/.144 | — |
| A.U10.45 | raise-message form; sorted except tuples | M.SRC_CORE (12), M.SRC_NET (12), M.SRC_SENS (8), M.TEST_UNIT.054/.126 | — |
| A.U19.19 | SPEC A.5 Microdot pin-move checklist | M.SPEC.018 | — |
| A.U20.26 | `@web-group` full inventory test | M.TSC.159 | — |
| A.U20.32 | explicit `Any` out of `buildgen/` | M.GEN (11), M.TOOL.030/.033 | — |
| A.U23.46 | `it`, not `test`, in the live-backend file | M.WEB.063 | — |
| A.U23.47 | `Any` out of the website-build Python tests | M.TSC.170, M.TEST_UNIT.332, M.TOOL.033, M.SCR.028, M.TWIN.136 | — |
| A.U24.38 | "no exception" tests assert their effect | M.TEST_UNIT (11), M.TWIN.100/.142, M.HW_BENCH.030 | — |
| A.U24.39 | boundary/type-only checks become value checks | M.TEST_UNIT (10), M.TSC (`test_buildgen_generate.py:125`) | — |
| A.U24.56 | test-file decision text residue | M.TEST_UNIT.044/.212/.265/.280, M.TWIN.140, M.WEB.058 (A28 via A.U0.28) | — |
| A.U24.62 | bool-vs-int comments | M.TEST_UNIT (6), M.SRC_SENS.022 | — |
| A.U25.38 | CI-suite waits poll | M.SCR.016/.050/.053/.054/.058, M.TWIN.064 | — |
| A.U25.65 | `digital_twin/README.md` current facts | M.TWIN.064/.067/.071/.075/.144 | BACKLOG item name it points at (DOCS) |
| A.U25.66 | CI-suite assertion defaults fail closed | M.SCR.047, .055; M.TSC.165 | — |
| A.U25.73 | chip-fake ranges cite datasheet pages | M.TWIN (7) | — |
| A.U26.45 | no variant name in the hardware levels | M.HW_BENCH (9), M.HW_DEV.036/.045/.111/.112 | — |
| A.U26.51 | `COVERS_TWIN_SCENARIOS` per module; E.6 rows | M.HW_BENCH (14), M.HW_DEV (12), M.TSC.102 | E.6 exception rows (SPEC, Gaps) |
| A.U26.65 | harness workarounds name defect, bound, trigger; Workarounds table | M.HW_BENCH (8, incl. .128) | CLAUDE.md version-bump line naming the table (DOCS, U36) |
| A.U26.69 | hazard loops yield; bounded failure record; L0 check | M.HW_DEV (12) | new L0 loop-await check (TSC, Gaps) |
| A.U26.76 | explicit `Any` out of the hardware levels | M.HW_BENCH (10), M.HW_DEV (4) | — |
| A.U27.06 | frozen website reproducible | M.SCR.071/.072, M.GEN.021, M.TSC (`test_build_frozen_html_sh.py`) | — |
| A.U27.33 | shell-script safety convention | M.SCR (15), M.TSC.035 | new L0 `test_shell_conventions.py` (TSC, Gaps) |
| A.U28.26 | lock-pinned Chromium default | M.WEB.074, M.SCR.064 | — |
| A.U31.12 | I2C probe settle in whole ms | M.SRC_SENS.007/.013 | — |

## Gaps for other clusters

1. **SPEC — Part N Dependants (A.U8C.120, A.U8C.121, A.U8C2.51)**: the three actions' Dependants text has no SPEC merged
   change yet. Write it as the end state the other merges leave, not as the U8C lists stand: drop
   `l1.asy_notification_service_override_tick_s` (withdrawn with its literal, M.TEST_UNIT.090) and
   `l2.network_neopixel_never_connects_wait_s` (the wait is gone, M.TWIN.132 and M_TWIN `:2717-2726`); under
   `wdt.timeout_ms` name `l3.device_script_feed_step_ms` instead of the per-script `*_wdt_feed_every`,
   `l3.sgp40_fram_backup_restore_wdt_feed_interval_s` and `l3.fram_pause_unpause_and_gating_feed_step_s` rows (M_HW_DEV
   GAP-D2); rows "deferred U26 — listed if U26 keeps it" follow M_HW_DEV/M_HW_BENCH's end state; each entry states the
   relation in words with no audit ID.
2. **SPEC — the procedures' permanent sentences**: F.7 rows and the "differ, used by nothing here" sentence from the
   refreshed-pin diff (M.PROC.016 → A.U14.28); F.1's "wrap safety was run once on a 2**30-period Unix build started just
   before the wrap (agent, <date>)" (M.PROC.024, A.U14.32's text, U35 stage); Part N Basis/value updates from M.PROC.028
   (B3 deltas) and from phase C (A.C.10 deltas); E.6 exception rows of A.U26.51 (with A.U7.25); the conditional F.1/F.2/
   F.5.x texts of M.PROC.011 and, at U37, a second F.5 record if M.PROC.031 moves the pin.
3. **DOCS**: (a) CLAUDE.md "Last run" re-dated at U37 by M.PROC.031 even when nothing moved (A.SDEP.21's site, U37
   stage); (b) the version-bump practice line naming `tests_hardware/README.md`'s Workarounds table (A.U26.65 → U36); (c)
   A.U25.65's BACKLOG pointer (the item name `digital_twin/README.md:453-456` cites must exist, or the sentence goes); (d)
   the hold-back and parked entries of M.PROC.008 (4)-(5) in BACKLOG's owner-question list (A.U0.12); (e) A.U1.02 is
   indexed to `README.md` by a parser hit on its Site text: it edits no README line and is carried by M.PROC.014 — DOCS's
   ledger should point there; (f) `legacy/README.md` and `.gitignore` are carried here (M.PROC.015, M.PROC.019), not by
   DOCS; the README "Further reading" entry for `legacy/README.md` is A.U1.13's.
4. **TSC — new files** (M_TSC's new-file sections, not written at the time of reading): `tests_scripts/
   test_cross_browser_smoke_probe.py` (A.U6.11: every device's definitions yield an in-range int probe field; a file with
   none throws); the device-script loop check of A.U26.69 (every `while`/`for` in an `async def` of a device script awaits
   on every looping branch, with a synthetic bite); `tests_scripts/test_shell_conventions.py` and the
   `run_unix_port_integration.sh --device` value/unknown-device cases of A.U27.33 (exit 2, OR133); A.U1.09's old-path
   check also asserting `legacy/README.md` tracked and `dev_legacy/` absent (M.PROC.014/.015).
5. **SCR (and HW_BENCH)**: no runner selects `multi_day_rollover` (M.SCR.030/.031 floors exclude it, M.SCR.032's floor is
   `soak_duration`). M.PROC.041 starts R6 through `_require_clean_hardware_run.sh --runner rollover --marker-floor
   "multi_day_rollover" …` directly; either a runner mode (e.g. the soak runner's `--rollover`) or M.HW_BENCH.126's README
   rollover recipe naming that invocation should make the path a documented one.
6. **HW_BENCH**: M.HW_BENCH.130's budget table's manual rows list the SCD30 `MeasInterval` step's two NVM writes
   (M.HW_BENCH.102 (2)), which A.C.04's Wear line omitted; R2's plan states them (M.PROC.039).
7. **CLUSTERS.md / orchestrator**: `.gitignore`, `legacy/` (and the dissolved `dev_legacy/`) sit in no cluster; PROC
   carries them (M.PROC.014, .015, .019). M_TWIN's and M_SCR's "LEAD gap" for `.gitignore` (`mem_backup_state.json`, the
   MICROPYPATH sentence) is closed by M.PROC.019.

## Adherence findings

- **M.PROC.001-.013 (U0 and the refresh)**: OR129 (every dependency, read the changes, no regression, take the fixes,
  retire solved workarounds, follow the rules) → held: one family per commit, a gate per family against B0, hold-back
  only under the standing rules, adoptions as deltas, owner-decided behaviours parked (harmonization 1); `ext/` only
  re-vendored unmodified (OR131.a, firm); tools stay pinned with the lock merge check on every rewrite (CLAUDE.md `uv.lock`
  rule); no hardware in U0 (OR129.a (6)); commit messages cite no audit ID (AC_NOTES 4). Breach found: none.
- **M.PROC.002 (one suite)**: memory rule — both GC stages, zero markers in every gate, both marker forms → held; OR133
  (exit 2 is a usage error) → held; host-I/O rule (no mass churn; repeats on tmpfs) → held.
- **M.PROC.014/.015 (`legacy/`)**: CLAUDE.md legacy rule → held (byte-identical moves, OR32 the owner's one change;
  `modules/_boot.py`'s import untouched); no audit ID or `[src: …]` note in `legacy/README.md` → held; paths change in the
  same commit (G8/R48) → held via (5).
- **M.PROC.019 (`.gitignore`)**: 3-line cap per block → held (every block ≤ 3 lines after the merge, four HEAD blocks over
  the cap folded); no device-variant literal (A.U6.15) → held (`build-wozi.sh` reference leaves); no history narrative →
  held except the Vitest block's "moved from" clause, kept as the current reason for two entries and re-judged after
  family (b) (M.PROC.019 (3)); no credentials → held; ignore semantics unchanged except the two Codecov/XML entries and
  `firmware.uf2` (covered by `*.uf2`).
- **M.PROC.018/.020 (datasheets, secret scan)**: `arduino/` never read (OR127.a) → held; no real credential removed or
  rotated without the owner (CLAUDE.md credentials rule) → held; the datasheet move only after a successful push → held.
- **M.PROC.022-.029 (B3)**: no sampling (OR107.a) → held (every row terminal); a defect goes OR12.a and A-C as a delta →
  held; no test deleted or weakened without a register entry (OR33.a) → held (M.PROC.023, .033 (3)).
- **M.PROC.030-.035 (U37)**: OR9.a (pass until all green, no cap) → held; OR2.c/LEAD/R16 review form → held; release
  version `2.0` stays an agent decision on the review list → held.
- **M.PROC.036-.043 (phase C)**: go-ahead per round conversation; FRAM logs read and saved before any write or clearing;
  wear only behind its marker with the budget stated before the round; dead-man's switch armed around every `br0`/slave
  change; `br0` MAC pin checked, never auto-repaired; only `dev` flashed with a dev-native image; local-only images
  reverted at once; lower levels first, never skipped for a reported result → held. Breach found and fixed: R2's budget
  missed the SCD30 NVM step (M.PROC.039); R6 had no runner path (M.PROC.041, D8); H78-H82 had no instrument
  (M.PROC.038, D7).
- **M.PROC.044 (phase D)**: `main` frozen, one merge commit, tag only with the owner's agreement, the `uv.lock` pin check on
  the merge commit, audit branch kept unless named → held.

## Owner questions

None. Every conflict in this cluster is settled by an owner row (OR129/OR129.a, OR127, OR131, OR133, OR80.a/OR95.a,
OR40.a (3), OR126.a), AC_NOTES (4, 21, 24, 34-second, 37, 38), a finished merge's gap, or an action's own text; the
agent decisions below go to the OR2.c review.

## Agent decisions for the OR2.c review

- **D1** (M.PROC.001 (3)): the audit archive keeps the last three runs per kind; evidence a register entry or round
  record cites is copied into it before rotation (A.C.01 (3)'s rule), so "never deleted" holds for cited evidence.
- **D2** (M.PROC.002, M.PROC.007): one full-suite command set for every gate; A.SDEP.02's extra rows (html/css lint,
  per-device firmware build, `setup_toolchain.py test`, cross-browser smoke) join the B0 baseline instead of a separate
  pre-refresh run.
- **D3** (M.PROC.005): `packet.py` also lists the A-C merged changes landing in the unit, since the merged list is the
  work order (OR106.a).
- **D4** (M.PROC.013): the post-refresh citation scan also covers the A-C merges, which quote upstream lines too.
- **D5** (M.PROC.017, M.PROC.021): the U17 traceability table and the U32 legacy check read code sites by symbol, since
  the U10 renames and reorder move every cited line.
- **D6** (M.PROC.037): R1's deliberate red runs its plant through the runners without `--skip-lower-levels`, the plant
  written to pass every L0 device-script guard, so the hardware gate under test is what turns red.
- **D7** (M.PROC.038): concrete hand-run instruments for H78-H82 (bench NTP block, a timed read script, console-stamped
  LED ramps, rung-test facts, a ten-cycle `stations` check on a reverted local image).
- **D8** (M.PROC.041): R6 starts the rollover test through the clean-run wrapper with a `multi_day_rollover` floor, since
  no runner selects it.
- **D9** (M.PROC.014, .015, .019): PROC carries the files no cluster owns (`legacy/`, `dev_legacy/`, `.gitignore`)
  rather than leaving them to the lead.

## Ledger

| action ID | merged into M-ID / dropped (reason) |
|---|---|
| A.C.07 | M.PROC.040 |
| A.C.08 | M.PROC.041 |
| A.C.09 | M.PROC.042 |
| A.C.11 | M.PROC.043 (the order of (3) also in M.PROC.036, .042) |
| A.C.18 | M.PROC.037 |
| A.SDEP.01 | M.PROC.008 (placement in M.PROC.003) |
| A.SDEP.02 | M.PROC.009 (command set and extra baseline rows in M.PROC.002, M.PROC.007) |
| A.SDEP.10 | M.PROC.010 |
| A.SDEP.17 | M.PROC.011 (conditional texts and code carried by the clusters named there; SPEC/DOCS texts, Gaps 2-3) |
| A.SDEP.20 | M.PROC.012 |
| A.SDEP.23 | M.PROC.013 (per-action step in M.PROC.001 (5)) |
| A.SDEP.25 | M.PROC.031 |
| A.S0930.32 | carried elsewhere: M.SRC_CORE.011, M.SRC_CORE.016, M.TEST_UNIT.306 (no PROC change) |
| A.U0.03 | M.PROC.004 |
| A.U0.04 | M.PROC.001 |
| A.U0.05 | M.PROC.005 |
| A.U0.15 | M.PROC.006 |
| A.U1.01 | M.PROC.014 |
| A.U1.03 | M.PROC.015 |
| A.U1.08 | M.PROC.014 |
| A.U10.18 | carried elsewhere: M.GEN.005, M.SRC_CORE/M.SRC_NET/M.SRC_SENS/M.TEST_UNIT/M.TWIN.102 (table) |
| A.U10.21 | carried elsewhere: M.GEN.010, M.SRC_CORE/M.SRC_NET/M.SRC_SENS/M.TEST_UNIT (table) |
| A.U10.29 | carried elsewhere: M.GEN.015, M.SRC_CORE.101/.120, M.SRC_NET, M.TEST_UNIT (table) |
| A.U10.33 | carried elsewhere: M.SRC_CORE, M.SRC_NET, M.SRC_SENS (table) |
| A.U10.35 | carried elsewhere: M.SRC_CORE, M.SRC_NET, M.SRC_SENS, M.TEST_HELP.028/.034, M.TEST_UNIT, M.HW_DEV.142/.143, M.SCR.026 (table) |
| A.U10.39 | carried elsewhere: M.GEN.025, M.SRC_CORE, M.SRC_NET, M.SRC_SENS, M.TEST_UNIT, M.HW_DEV.142 (table) |
| A.U10.44 | carried elsewhere: M.SRC_NET, M.SRC_SENS, M.TEST_HELP.034, M.TEST_UNIT, M.HW_DEV, M.HW_BENCH.135, M.TWIN.102/.144 (table) |
| A.U10.45 | carried elsewhere: M.SRC_CORE, M.SRC_NET, M.SRC_SENS, M.TEST_UNIT.054/.126 (table) |
| A.U14.29 | M.PROC.016 (F.7 rows: SPEC via A.U14.28, Gap 2) |
| A.U17.12 | M.PROC.017 |
| A.U19.19 | carried elsewhere: M.SPEC.018 |
| A.U2.25 | carried elsewhere: M.WEB.045, M.TSC.088 |
| A.U20.26 | carried elsewhere: M.TSC.159 |
| A.U20.32 | carried elsewhere: M.GEN (11 changes), M.TOOL.030/.033 |
| A.U23.46 | carried elsewhere: M.WEB.063 |
| A.U23.47 | carried elsewhere: M.TSC.170, M.TEST_UNIT.332, M.TOOL.033, M.SCR.028, M.TWIN.136 |
| A.U24.35 | dropped (withdrawn by its unit; content carried by A.U25.31 (1) → M.TWIN.016) |
| A.U24.38 | carried elsewhere: M.TEST_UNIT (11), M.TWIN.100/.142, M.HW_BENCH.030 |
| A.U24.39 | carried elsewhere: M.TEST_UNIT (10), M.TSC (`test_buildgen_generate.py` section) |
| A.U24.56 | carried elsewhere: M.TEST_UNIT.044/.212/.265/.280, M.TWIN.140, M.WEB.058 |
| A.U24.62 | carried elsewhere: M.TEST_UNIT (6), M.SRC_SENS.022 |
| A.U25.38 | carried elsewhere: M.SCR.016/.050/.053/.054/.058, M.TWIN.064 |
| A.U25.65 | carried elsewhere: M.TWIN.064/.067/.071/.075/.144 (BACKLOG pointer, Gap 3 (c)) |
| A.U25.66 | carried elsewhere: M.SCR.047, M.SCR.055, M.TSC.165 |
| A.U25.73 | carried elsewhere: M.TWIN.010/.012/.013/.014/.072/.142/.150 |
| A.U26.45 | carried elsewhere: M.HW_BENCH (9), M.HW_DEV.036/.045/.111/.112 |
| A.U26.51 | carried elsewhere: M.HW_BENCH (14), M.HW_DEV (12), M.TSC.102 (E.6 rows, Gap 2) |
| A.U26.65 | carried elsewhere: M.HW_BENCH.011/.013/.017/.021/.064/.071/.127/.128 (CLAUDE.md line, Gap 3 (b)) |
| A.U26.69 | carried elsewhere: M.HW_DEV (12) (L0 check, Gap 4) |
| A.U26.76 | carried elsewhere: M.HW_BENCH (10), M.HW_DEV.011/.046/.047/.119 |
| A.U27.06 | carried elsewhere: M.SCR.071, M.SCR.072, M.GEN.021, M.TSC (`test_build_frozen_html_sh.py` section) |
| A.U27.33 | carried elsewhere: M.SCR (15), M.TSC.035 (new L0 file, Gap 4) |
| A.U28.26 | carried elsewhere: M.WEB.074, M.SCR.064 |
| A.U28.33 | M.PROC.019 |
| A.U29.04 | M.PROC.020 (tracked-copy deletion is M.HW_DEV.112's) |
| A.U3.15 | carried elsewhere: M.WEB.045, M.TSC.088 |
| A.U31.12 | carried elsewhere: M.SRC_SENS.007, M.SRC_SENS.013 |
| A.U32.04 | M.PROC.021 |
| A.U35.01 | M.PROC.022 |
| A.U35.07 | M.PROC.023 |
| A.U35.32 | M.PROC.024 (F.1 sentence, Gap 2) |
| A.U35.36 | M.PROC.025 |
| A.U35.52 | M.PROC.026 |
| A.U35.53 | M.PROC.027 |
| A.U35.54 | M.PROC.029 |
| A.U35.56 | M.PROC.028 (Part N rows and tagged literals as B3 deltas, Gap 2) |
| A.U37.01 | M.PROC.030 |
| A.U37.07 | M.PROC.032 |
| A.U37.09 | M.PROC.033 |
| A.U37.13 | M.PROC.034 |
| A.U37.14 | M.PROC.035 |
| A.U37.16 | M.PROC.044 |
| A.U37.17 | M.PROC.033 |
| A.U5.02 | carried elsewhere: M.SRC_CORE, M.SRC_NET, M.SRC_SENS, M.TEST_UNIT, M.TEST_HELP.035, M.HW_DEV, M.HW_BENCH.134, M.TWIN.064, M.GEN (table) |
| A.U6.07 | carried elsewhere: M.WEB.031, M.WEB.059, M.GEN.060 |
| A.U6.11 | carried elsewhere: M.SCR.023, M.SCR.063, M.TOOL.010/.019, M.WEB.073 (new L0 file, Gap 4) |
| A.U6.14 | carried elsewhere: M.TSC.035, M.TSC.002 |
| A.U6.17 | carried elsewhere: M.GEN.015/.017/.046, M.SRC_SENS.051, M.WEB.004/.005/.041/.060/.063, M.TSC.159 |
| A.U8C.120 | test-site tags carried elsewhere (M.TWIN.124/.132/.144; M.TEST_UNIT holds, one row withdrawn at .090); Part N text → SPEC (Gap 1) |
| A.U8C.121 | test-site tags carried elsewhere (M.HW_DEV, M.SCR.065); Part N text → SPEC (Gap 1) |
| A.U8C2.51 | test-site tags carried elsewhere (M.TEST_UNIT.309); Part N text → SPEC (Gap 1) |
| A.U1.02 (extra: indexed to README.md, no README edit) | M.PROC.014 |

Read for order or context, not constituents (their own clusters merge them): A.U0.01, A.U0.02, A.U0.06 (procedure merged
into M.PROC.007; ENV.T02 text DOCS), A.C.01-A.C.06, A.C.10, A.C.12-A.C.17, A.C.19, A.SDEP.03-A.SDEP.09, A.SDEP.11-A.SDEP.16,
A.SDEP.18, A.SDEP.19, A.SDEP.21, A.SDEP.22, A.SDEP.24, A.U28.35, A.U36.545, A.U37.02-A.U37.06, A.U37.08, A.U37.10-A.U37.12,
A.U37.15.
