# R5 lane A: the closure rows that need neither the bench nor the owner (lead, 2026-11-05)

## Read first, in order
1. `S/u35r/r1/common_r1.md` (binding; your labels start with `r5A_`).
2. `S/u35r/plan/PLAN.md` sections 0 and 4, and its R5 row.
3. `S/u35r/r5/INVENTORY.md` (your row table; its state legend binds you).

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Where you work
- Worktree `S/wt-r5a`, branch `audit/r5a`, at `932510fc` (the integration head, R4's docs merged). Commit locally;
  never push.
- You may write: `BACKLOG.md`; the doc sites a row's state names (`SPECIFICATION.md`, `CLAUDE.md`, `README.md`,
  `tests_hardware/README.md`, `digital_twin/README.md`, `UART_C_PORT_CHANGELOG.md`); comments in `scripts/` and
  `tests*/` where a row says so; `tests_scripts/test_comment_block_cap.py` and `tests_scripts/test_counter_steps.py`
  for r5I_X3.
- Never touch: `src/`, `buildgen/`, `toolchain/`, `devices/`, `js/`, `html/` (round 1's image and the wear block must
  stay byte-identical); SPEC's Part 0, Part K and K.0, and `.claude/skills/` (two proof runs read them as frozen); the
  two allow-lists.

## Your rows
Every row of INVENTORY section 1 whose W column is **N** and whose state is **F, R, D or O**, plus r5I_X1-X3, except:
- r5I_F9, r5I_B01 and r5I_U02 (code and allow-lists: a later unit), and r5I_U01 (a dependency check: a later unit);
- every row in state N (the owner's), and every row with W = Y or part (they wait on round 1).

For each row, bring it to its terminal state at the head:
- **F / R:** check the fix or the staleness at the cited site; the BACKLOG item comes out (CLAUDE.md's working
  agreement: BACKLOG holds open work only). A row whose fix is not in fact at the head is listed, not fixed.
- **D:** the decision stands at the site named, in one short sentence with its "(owner, date)" or "(agent, date)";
  then the BACKLOG item comes out, or shrinks to a pointer only where other open work still cites it.
- **O:** the limitation is stated at its doc site; an owner-deferred goal stays in BACKLOG with its reason, one line.
- A row that would need a change in a file you may not write, or more than 15 added lines, is listed, not done.

## Rules
- OR27.a: facts, rules and agreements, never history; every rewrite keeps its meaning; a rule that looks drifted is
  listed for the owner, not reworded. Owner words stay verbatim.
- Facts you keep or move are checked against the head (file:line).
- Low complexity: removing is the default; never add a ledger, table or new section to the docs.

## Checks and limits
- At most six runs, all light; the host's heavy slot is taken, so no gate, no whole tier, no build. Run: the comment
  cap, citations, decision vocabulary, THR facts, tool help if README changed, the UART changelog test if it changed;
  for r5I_X3, `S/u35/lead/lint_direct.sh` and the host mypy pass. A citation or vocabulary failure caused only by an
  allow-listed sentence you removed is expected: list it.
- Size: net negative; stop and say why if your additions pass +60 lines.
- Budget: about 1 % of the week; stop at a clean commit when you reach it.

## Report
Write it to `S/u35r/r5/HANDBACK_R5A.md` and return its path. At most 30 lines: commits, lines in/out per file; per row
id its terminal state and site (or "listed: why"); the drifted rules; the checks with expected failures counted. Last
line: "nothing of mine is running".
