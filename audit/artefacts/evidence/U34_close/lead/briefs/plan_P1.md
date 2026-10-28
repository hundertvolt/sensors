# U34 planning, block P1: locate every step (lead, 2026-10-21)

You are the first of two read-only planning blocks for unit U34 of a whole-project audit (vendored code, third-party
attribution, the type-check and lint configuration, the stubs, the build staging). You run no tests, builds or network
commands and change no worktree. Small `python3 -I` helper scripts go only under `S/u34/plan_scratch/`; nothing is
written anywhere else. Your final message is your record (subagents here cannot write report files): at most about 160
lines, tables welcome.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan`, a detached
worktree at `c6b8a07` (U32's final tree). Never read `arduino/` (use `':!arduino'` in every git grep and
`-- . ':!arduino'` on every git log). `legacy/` is reference-only: read it only where a step's text requires it; a step
never edits it. `ext/` may be read here; it changes only by re-vendoring an unmodified upstream tag or commit (owner,
2026-10-01, the packet's "Resolved" line at `S/u34/pk/U34.md:376`; CLAUDE.md's dependency-refresh bullet), never by an
edit, so a step whose text edits `ext/` any other way is a **conflicts** row.

## Base and the unit before it
U33 (documents only) lands between this tree and U34's base. It edits only BACKLOG.md, CLAUDE.md, SPECIFICATION.md,
tests_hardware/README.md, tests_scripts/_citation_allowlist.txt and tests_scripts/_decision_vocab_allowlist.txt; its
plan is `S/u33/lane_plan.md` (read only P1's step table rows 3, 4, 22, 29 and 30 and P2's R-2, R-3 and R-18). Where a U34
step lands in a site U33 also writes (the BACKLOG chroot list, CLAUDE.md's E722 bullet, SPECIFICATION.md B.16, the
comment-cap length rule held by BACKLOG.md owner question 6, pyproject's ignore list), say what U33 writes there, so the
U34 writer starts from U33's text, and mark the row **after U33**. Line numbers in those four documents will move.

## Inputs
- The packet `S/u34/pk/U34.md`: the standing sections, then 37 step headings ("## Step N: M.ID — title"; steps 4 and 33
  co-landing groups), each with its merged change text and site, then the carried action texts. Its line numbers are old
  and some names may be old: locate every site by its quoted text in `S/wt-u33plan`, never by line alone.
- `S/wt-u33plan/audit/order/work_order.json` (unit U34: 42 steps, 19 carried actions, 28 files; hardware rounds R1 H25
  and H73, R3 H73), `audit/REGISTER.md` (rows naming U34) and `audit/sweeps/open_findings.md` (rows targeting U34).
- The format: `S/u33/lane_plan.md` section "## P1" (U33's plan). A "landed" verdict is right only where it cites an
  anchor; many U34 steps were written for U0's dependency refresh, so check what that refresh and later units already did.

## Produce (block P2 writes the cut, waves, rulings and risks from your record)
1. COUNTS AND STEP TABLE. One row per step: step number, M.ID, the files it edits (current names), its verdict, and the
   evidence. Verdicts: **landed** (cite path:line at `c6b8a07` for each part), **part landed** (say which part is left),
   **check-only**, **to write**, **hardware** (needs the bench; parked for hardware session 1, name what it needs),
   **conflicts** (the step's text contradicts the tree, a later owner decision or a standing rule: quote both), **after
   U33** (as above), **needs upstream** (the step needs an upstream file or tag this tree does not hold: name the repo,
   tag or commit and the exact files, so the lead fetches them once). Then the totals, and the 19 carried actions placed.
   For each pinned version or hash a step names (Microdot and its stubs, freezefs, the actions' tags, ruff, mypy, the
   stubs package), give the value in the tree today and the value the step's text names.
   Mark every step that changes a real-hardware path or the frozen firmware's content (`scripts/build_firmware.py`,
   `scripts/build_frozen_html.sh`, a `src/` module): code edits are allowed, real-hardware runs are not.
2. OPEN FINDINGS: every row targeting U34, its site located at `c6b8a07`, still open or already closed by the tree, and
   the step it joins (or "own step").
3. PACKET VS CODE: stale names, moved sites, renamed symbols, parts U0-U32 already did, and anything you could not
   determine read-only (say what would settle it). Name each BACKLOG.md owner question or deferred item a step touches by
   its current number and title.

Be exact: every claim about the code cites path:line at `c6b8a07`. Where a step's site is generated code
(`buildgen/codegen.py` emits each device's `sensortask_<device>.py`), cite the emitter's line.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying which steps are left. Batch
your reads: one `grep -n` or one helper script over many sites beats one call per site. Never re-read a file you have
already read in this block.
