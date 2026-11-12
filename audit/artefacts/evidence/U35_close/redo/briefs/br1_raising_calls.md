# BR1: raising.md, the never-raise modules' raising calls classified (part 1) (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first (its environment, rules, checks and shell discipline bind you). Then read,
on your worktree:
- CLAUDE.md;
- `audit/actions/U35.md` A.U35.36 (:968-990) and A.U35.41 (E.5.1 verdicts);
- `audit/b3/raising.md` and its walk `audit/b3/raising_walk.py`, in full;
- `audit/b3/e51.md` (the unreachable-branch register);
- SPECIFICATION.md F.2 (what can and cannot be timeout-wrapped, and the rule against blanket `MemoryError` wrapping
  with its narrow exception), I.4 (the memory discipline), A.5 (Microdot's per-request guarantees and the
  response-writing gap) and D.2 (the "never raises" header line).
The pinned MicroPython source is `S/tc-int/micropython` (v1.29.0): every "can raise" claim cites it.

Worktree `S/wt-u35braise`, branch `audit/u35-braise` at 36bee227, the integration head, clean and rebuilt. Logs go in
`S/u35/laneB/br1/`.

## Why
A.U35.36 requires a terminal verdict for every row: handled, with the catching `except`; unreachable, with the proof,
which makes it an E.5.1 verdict; or a defect. A defect is fixed at the right layer, with a test that injects the
raise through a substituted name and asserts the sentinel, seen failing first. On the head about 421 rows are left:
123 "not classified", 78 "open", only 8 terminal. The walk last ran on b1bf1f3. A defect here is a firmware fix, and
the owner's rule is "Firmware really complete, don't push fixes to future units".

## Items, in order
1. **Make the walk's verdicts parallel-safe, committed alone.** Other lanes will classify the other modules at the same
   time, so verdicts cannot all sit in one dict in one file. Move every hand-given verdict (today's RAISES entries, and
   any new one) into one file per module under `audit/b3/raising_verdicts/`. The walk reads them, keyed by
   (function) for a raise and by (function, callee) for a call group. Prove the move changes nothing: with the
   tool as it is and with your version, run the walk on 36bee227 and diff the two outputs (`diff` empty). Then commit
   the regenerated raising.md on the head alone. Do not change RULES' verdicts in this commit.
2. **Your modules: `asy_base_classes.py`, `asy_print_log.py`, `math_helpers.py`.** Give every row of theirs, raises
   and call groups alike, a terminal verdict in its module's verdict file, with lines. The auto-RULES rows count too:
   "open: setup-only or run-time allocation decides (I.4)" and "open: operand-type proof" are not terminal.
   - **Handled:** name the `except` that catches it and its lines, up the call chain where the caller holds it.
   - **Unreachable:** give the proof from the pinned source or the code (operand types proven, key proven present,
     buffer size proven). Add the matching e51.md row in the same commit.
   - **MemoryError rows:** classify them under F.2's rule and I.4. An allocation in the one-time boot setup is
     handled by that setup's own catch; name it. A run-time allocation of a small fixed size falls under F.2's rule
     against blanket wrapping, with that rule cited. An allocation whose size grows with input or configuration, on
     a run-time path that can propagate out of a never-raise contract, is a defect candidate.
   - **Special attention (A.U35.36):** task tops, Timer and IRQ callbacks, Microdot handlers, the response-writing gap,
     and every widened `except` (a swallowed CancelledError is A.U35.48's: name it, do not fix it).
3. **Defects.** Each one in its own commit:
   - Write the test that injects the raise through a substituted name (the module-attribute mocking used across
     tests/) and asserts the sentinel. Show it failing on the base first.
   - Make the fix at the right layer, small and local.
   - Run every importer's test file at both GC stages, with zero memory markers.
   - The module header's "never raises" line stays true.
   - If a fix would change a public return contract, an API, the UART wire format or an architectural pattern, or is
     anything but local, do not make it. Hand back with the facts, the options and your recommendation: the lead puts
     it to the owner.
4. Commit verdicts per module, each commit green: the walk re-run, `git diff` showing only your modules' rows,
   `python3 -I audit/sweeps/review_rows.py --check`, and the tests_scripts readers of audit text (test_citations,
   test_decision_vocabulary, test_comment_block_cap).

## Notes
- Not yours: `asy_config_manager.py`, `asy_system_service.py`, `asy_fram_manager.py` and `asy_fram_driver.py`. Lanes
  BR2 and BR3 start from your item-1 commit, so hand that commit's id back as soon as it exists. SendMessage it to the
  lead the moment it is committed.
- File edits use the Edit or Write tool. A deletion is its own Bash call, with a literal path or `"${var:?}"`.
- Every run goes through your own run wrapper in your log dir, modelled on `S/u35/lead/run.sh`, with RUNS.md lines
  naming `U35 lane BR1`.
- After any src edit, rebuild with `S/u23/rebuild.sh`.
- Commit subject `U35 lane BR1: <summary>`, with the two trailers. Do not push.
- A refused command stops you.
- Count your tool calls; at 80, commit what is green and hand back at a seam with the rows left.
- Hand-back:
  - commits;
  - rows by verdict per module (before, after);
  - every defect: site, test, red-first evidence and fix;
  - every e51.md row added;
  - every question for the owner, in prose;
  - last line "nothing of mine is running".
