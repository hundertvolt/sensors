# U35 planning, block P1<x>: locate the steps of your range (lead, 2026-10-21)

You are one of four read-only location blocks (P1a to P1d) for unit U35 of a whole-project audit: the largest unit
(182 steps over 131 files: the error and logging contract, the twin and its CI suite, the bus-hazard tests, the web
client's request path and loop, many `src/` and `tests/` files). You run no tests, builds or network commands and change no
worktree. Small `python3 -I` helper scripts go only under `S/u35/plan_scratch/<x>/`; nothing is written anywhere else.
Your final message is your record (subagents here cannot write report files): at most about 160 lines, tables welcome.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. Code: `S/wt-u33plan`, detached at
`1dd6dd5` (U34's integration head: U32's code, U33's documents, U34's four lanes). Two files differ in U35's base,
which also carries U32's two gate fixes: read `tests/test_asy_neopixel_driver.py` and `tests_js/shell.test.js` as
`git -C S/wt-u33plan show 970b63b:<path>`. Never read `arduino/` (`':!arduino'` in every git grep, `-- . ':!arduino'` on
every git log). `legacy/` is reference-only: read it only where a step's text requires it. `ext/` is never edited.

## Your range
P1a: steps 1-45. P1b: steps 46-110. P1c: steps 111-144. P1d: steps 145-179 (step headings "## Step N: ..." in
`S/u35/pk/U35.md`; co-landing groups count as one step). Read the packet's standing sections (lines 1-244: the
silent-failure scan, the operating modes, the register deltas, the fold parts), then only your range's steps, and of
the carried action texts (from the line "# Carried action texts", about :7860) only those your steps name.

## Inputs
- `S/wt-u33plan/audit/order/work_order.json` (unit U35: 182 steps, 72 carried actions, 131 files; hardware rounds R0
  H56, R1 H29 H43 H44 H55 H71 H73 H83, R3 H68 H73, R4 H55, R5 H55), `audit/REGISTER.md` and
  `audit/sweeps/open_findings.md` (rows targeting U35 whose site falls in your range's files).
- The format: `S/u34/lane_plan.md` "## P1" (U34's step table). A "landed" verdict is right only where it cites an anchor;
  many U35 steps were partly done by U10-U34, so check the tree, never the packet's own claim.

## Produce (for your range only; block P2 joins the four records)
1. STEP TABLE. One row per step: number, M.ID, the files it edits (current names), verdict and evidence. Verdicts:
   **landed** (cite path:line at `1dd6dd5` for each part), **part landed** (say what is left, quoting the current text it
   replaces), **check-only**, **to write** (quote the current text or name the heading it goes under), **hardware** (needs the
   bench; parked for hardware session 1: name the round), **conflicts** (the step contradicts the tree, a later owner
   decision or a standing rule: quote both). Mark every step touching `src/asy_uart_comm.py`, `src/asy_uart_link_driver.py`
   or `UART_C_PORT_CHANGELOG.md` with whether it changes an emitted byte, an accept/reject rule or a recovery timing (the
   UART wire format is never changed: owner, 2026-09-25, "the UART wire format is not touched"; such a part is a
   conflicts row). Mark every step that adds or removes a `# @tunable` tag, an `error_catalog.json` row or a twin-record
   input.
2. The carried actions your steps name, each placed on a step.
3. OPEN FINDINGS whose site is in your range's files: located, still open or closed by the tree, joining which step.
4. PACKET VS CODE: stale names, moved sites, renamed symbols, parts earlier units did, and anything not determinable
   read-only (say what would settle it).
5. FILES: the list of files your steps edit, each with the step numbers, so P2 can cut lanes by file family.

Be exact: every claim about the code cites path:line at `1dd6dd5`. Where a step's site is generated code
(`buildgen/codegen.py` emits each device's `sensortask_<device>.py`), cite the emitter's line.

## Working economy (binding)
About 60-80 tool calls; at 80 you stop at a clean seam and hand back what is done, saying which steps are left. Batch
reads; one `grep -n` or one helper script over many sites beats one call per site. Never re-read what you hold.
