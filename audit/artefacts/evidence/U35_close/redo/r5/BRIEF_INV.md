# R5 preparation: the closure inventory (lead, 2026-11-05), read-only

## Read first
- `S/u35r/r1/common_r1.md` (binding; your labels start with `r5I_`).
- PLAN.md's R5 row: `S/u35r/plan/PLAN.md` lines 306-318. Owner rows OR5/OR5.a, OR11/OR11.a and OR52.a in
  `PROJECT_AUDIT_PLAN.md` (in the tree below).
- `S/u35r/plan/PLAN_before_rewrite.md` appendices A and B only for U37's items 01 (2), 02, 04, 05, 14 and 17.

S = `/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The tree is `S/wt-u35int` at
`3b9d7218` (read only; never write, commit or check out anything there). SPECIFICATION.md is still being edited
elsewhere: cite it by Part, not by line.

## What you make: `S/u35r/r5/INVENTORY.md`
1. **OR5.a closure table.** One row per item that is not yet in a terminal state:
   - every open finding in `S/u35r/findings/FINDINGS.md`;
   - every BACKLOG.md item;
   - every open/deferred/TODO marker in the tree's docs and code (`git grep -nIE 'TODO|FIXME|XXX|open question|deferred'`
     with `':!arduino' ':!ext' ':!legacy' ':!python' ':!audit'`), hits in prose that are not an open item excluded;
   - U37's six items above.
   Columns: id, where (file:line), one-line subject, proposed terminal state (fixed / resolved-or-stale, removed /
   decided, documented at <site> / out of scope by owner, documented as a limitation / needs the owner), evidence for
   the proposal (file:line or owner row), and whether it waits on round 1's results. Verify against the tree that an
   item is not already resolved before proposing work for it.
2. **OR11 stray-file table.** Every tracked file outside `src/ ext/ tests/ tests_js/ tests_scripts/ tests_hardware/
   digital_twin/ buildgen/ toolchain/ scripts/ js/ html/ devices/ datasheets/ legacy/ python/ modules/ arduino/ audit/
   .github/ typings/` that looks temporary, auto-created, unused or unreferenced, plus such files inside those dirs
   (scratch logs, `*.out`, stale fixtures with no reader). Columns: path, why it looks stray, its inbound references
   (`git grep -n <basename>`), what must migrate first, and OR11.a's timing (final cleanup / at the hardware
   follow-up's close / stays). Do not list `PROJECT_AUDIT_PLAN.md`, `audit/` or the changelog as removable now.
3. **Counts** at the top: rows per table and per proposed state; the items needing the owner listed by id.

## Rules
- Read-only. Write only `S/u35r/r5/INVENTORY.md` (at most about 250 lines).
- Never read `arduino/`; `':!arduino'` in every git grep and git log. Never open `/root/.claude/`. No hardware. No runs
  are needed; if one is, at most three, through `S/u35/lead/run.sh`.
- Targeted reads: grep for the anchor, then read the range.
- Budget: about 0.7 % of the week.

## Report
At most 15 lines: the file's path, the counts, the owner items, anything you could not classify. Last line: "nothing
of mine is running".
