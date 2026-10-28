# INV: what the audit added to the firmware, for the owner's keep-or-remove decision (lead, 2026-10-28)
Read-only. No edit in the repo, no test run, no lane worktree. The owner's standing target (2026-10-28): clean and
minimal firmware code; nothing built on hypothetical findings; no patches; anything beyond the legacy firmware's
behaviour is the owner's decision. This inventory gives the facts for that decision. It recommends nothing.

## Range and scope
- Range: the audit's start `25caf528` (2026-09-25) to the integration head `497b3eda`, in the integration worktree
  `S/wt-u35int` (read it there; never write to it).
- Your file group is in your launch message. "Firmware" is `src/`, the generated device modules
  (`build/generated_src/`, produced by buildgen from `devices/*.toml`) and buildgen itself.
- Legacy reference: `legacy/firmware/python/` (read-only; it is what the field units run).
- Never read `arduino/` (use `':!arduino'` on every git grep/log). `ext/` is vendored and out of scope. Never open
  anything under `/root/.claude/` or any agent transcript.

## What counts as an addition
- An addition is any new mechanism, or any change of behaviour: a task, a timer, a retry, a timeout or timed wait,
  a periodic action, a guard or validation branch, a fallback, a state, a config field, a log entry type, an error
  path, a buffer or caching scheme, a lock, a widened or narrowed accept rule.
- These are not additions: rewording, comments, renames, typing, restyling, and moving code between files with its
  behaviour unchanged. Say in one line per file that you checked for them.
- Read diffs, not whole files: `git log --format='%h %ad %s' --date=short 25caf528..497b3eda -- <file>`, then
  `git show <h> -- <file>` per commit, or `git diff 25caf528 497b3eda -- <file>` for a file whose history is long.
  For a file renamed in the range, diff against its old name.

## One row per addition
| field | content |
|---|---|
| where | file:line range at 497b3eda |
| what | one line: the behaviour, as the device sees it |
| commits | the commit(s) that brought it (short hashes) |
| origin | the finding or decision behind it: the audit record (`audit/sweeps/open_findings.md` OF-rows, `audit/consolidation/M_*.md` items, SPECIFICATION.md Part N's "Basis" for a tunable, the commit subject) and any decision tag in the code, `(owner, date)` or `(agent, date)` |
| evidence | O: an owner decision (quote it, verbatim, with its source; `S/u35r/recovered/owner_rulings_after_LN118.md`, SPECIFICATION.md and CLAUDE.md hold them). F: an observed failure of the earlier behaviour (bench, field, or a test that failed on the earlier code; name where). H: hypothetical, found by reading or a scan with no observed failure. Say which, and quote the line that shows it. |
| legacy | does the legacy firmware have this behaviour? yes / no / partly, with legacy path:line |
| form | design (part of the module's structure) or patch (a local fix around a symptom); one line why |
| depends on | another addition it exists to protect, support or work around (a cascade), or none |
| device cost | code lines; tasks, timers, timed waits and allocations it adds at run time; per-wake or per-request cost if any |
| simplest alternative | one line: what the code would be without it (often the legacy form) |

## Efficiency
- Grep for anchors, then read line ranges. The audit records are large: grep them by file name or OF number.
- No speculation: a field you cannot establish from the sources says "not found" and what you searched.
- One pass per file. Do not re-derive a mechanism's correctness; this is about origin, evidence and cost.

## Hand-back
- Write `S/u35r/inventory/<GROUP>.md` (first line "<GROUP> inventory, written by the lane (<date -u>)"): the
  rows grouped by file, then per-file totals (rows by evidence class, code lines by evidence class), then the
  cascades you found (chains of additions that exist for each other).
- Your final message: the path, and one line of counts per evidence class (O/F/H) with their code lines.
- Last line: "nothing of mine is running".
