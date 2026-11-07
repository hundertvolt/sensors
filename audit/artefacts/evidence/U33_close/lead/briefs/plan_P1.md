# U33 planning, block P1: locate every step (lead, 2026-10-21)

You are the first of two read-only planning blocks for unit U33 (DOC) of a whole-project audit. You run no tests, builds
or network commands and change no worktree. Small `python3 -I` helper scripts go only under `S/u33/plan_scratch/`;
nothing is written anywhere else. Your final message is your record (subagents here cannot write report files): at most
about 150 lines, tables welcome.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan`, a detached
worktree at `c6b8a07`, U32's final tree (U33's base will be U32's squash of exactly this tree). Never read `arduino/` (use
`':!arduino'` in every git grep and `-- . ':!arduino'` on every git log), never `ext/`; `legacy/` is reference-only: read
it only if a step's text requires it, and a step can never edit it (the legacy tree never gets work of any kind).

## Inputs
- The packet `S/u33/pk/U33.md`: standing sections (the silent-failure scan, the operating modes, the register deltas),
  then 30 step headings ("## Step N: M.ID — title", step 1 a co-landing group of two), each with its merged change text
  and site, then the carried action texts. Its line numbers are old and some file names may be old bare names (U32's
  packet had `src/system_service.py` for `src/asy_system_service.py`): locate every site by its quoted text in
  `S/wt-u33plan`, never by line alone.
- `S/wt-u33plan/audit/order/work_order.json` (unit U33: 31 steps, 15 carried actions, 21 files; hardware round R1 H22),
  `audit/REGISTER.md` (rows naming U33, e.g. SF-M4-11 at :850) and `audit/sweeps/open_findings.md` (rows targeting U33:
  OF-121, OF-226, OF-230 and any other).
- The format: `S/u32/lane_plan.md` section "## P1" (U32's plan), and what the later units learned about landed steps:
  a "landed" verdict was right only where it cited an anchor.

## Produce (sections 1, 6 and 7 of the plan; block P2 writes the cut, waves, rulings and risks from your record)
1. COUNTS AND STEP TABLE. One row per step: step number, M.ID, the files it edits (current names), its verdict, and the
   evidence. Verdicts: **landed** (the change is already in the tree: cite path:line at `c6b8a07` for each part), **part
   landed** (say which part is left), **check-only** (nothing to edit, a check to run), **to write**, **hardware**
   (needs the bench; parked for hardware session 1, name what it needs), **conflicts** (the step's text contradicts the
   tree, a later owner decision or a standing rule: quote both). Then the totals, and the 15 carried actions placed.
   Many U33 steps are documents (BACKLOG.md, CLAUDE.md, SPECIFICATION.md, tests_hardware/README.md): for each, quote the
   current text it replaces or the heading it adds under, so a writer can apply it without re-searching. Mark every
   step touching `src/asy_uart_comm.py`, `src/asy_uart_link_driver.py` or `UART_C_PORT_CHANGELOG.md` with whether it
   changes any emitted byte, accept/reject rule or recovery timing: the UART wire format is never changed (owner,
   2026-09-25: "the UART wire format is not touched"), so such a part is a **conflicts** row. Mark every step that runs
   or changes a real-hardware path (`tests_hardware/flash/`, `tests_hardware/bench/`, the runners in `scripts/`): code
   edits are allowed, real-hardware runs are not (only `--collect-only` and the twin).
2. OPEN FINDINGS: every row targeting U33, its site located at `c6b8a07`, still open or already closed by the tree, and
   the step it joins (or "own step").
3. PACKET VS CODE: stale names, moved sites, renamed symbols, parts U23-U32 already did, and anything you could not
   determine read-only (say what would settle it). For BACKLOG.md steps, name each owner question or deferred item the
   step touches by its current number and title (U32 entered owner question 7).

Be exact: every claim about the code cites path:line at `c6b8a07`. Where a step's site is generated code
(`buildgen/codegen.py` emits each device's `sensortask_<device>.py`), cite the emitter's line, not a generated file.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying which steps are left. Batch
your reads: one `grep -n` or one helper script over many sites beats one call per site. Never re-read a file you have
already read in this block.
