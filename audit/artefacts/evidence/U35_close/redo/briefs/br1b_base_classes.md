# BR1b: raising.md, asy_base_classes.py (lead, 2026-10-27)
Your task is `S/u35r/briefs/br1_raising_calls.md`'s items 2-4, for `asy_base_classes.py` only. Read
`S/u35r/briefs/redo_common.md` first, then that brief and every file it names, then BR1's hand-back
`S/u35r/handbacks_redo/BR1.md`. Read `audit/b3/raising_verdicts/asy_print_log.json` and `math_helpers.json` as the
worked form: each verdict cites lines, its "conventions" key, its proofs from v1.29.0. Worktree `S/wt-u35braise`,
branch `audit/u35-braise` at 32a62f28 (clean). Logs go in `S/u35/laneB/br1b/`. BR1's helper
`S/u35/laneB/br1/groups.py <tree> <module>` prints the exact keys a verdict file needs.

## The lead's review of BR1 (binding)
- 651d3e79, 5023bcf7 and 32a62f28 are kept as written: no defect in math_helpers or asy_print_log, 44 unreachable rows
  rendered into e51.md's header block. The block's place in the header is accepted.
- The "conventions" key stays per file for now. After BR1-3 merge, the lead has the walk render it, so leave the walk
  alone.
- Its header question (asy_print_log's "Never raises" holds only modulo a MemoryError at call entry on an exhausted
  heap, G.2's task-top caveat) goes to the docs pass: no src change.

## Items, in order
1. BR1's stale lines, in their own commit:
   - the handled `_checked_write_results` raise proof cites callers :507/:689 (excepts :508/:690), but the call
     sites are now :514/:696;
   - the walk's three debug print keys (507, 689, 795).
   Re-locate each one on the head and fix it. The walk's `--check` passes, and the diff shows only those lines.
2. Every one of asy_base_classes.py's 120 call groups gets a terminal verdict, under br1's rules (handled with its
   except, unreachable with its proof plus the e51 block row, or a defect fixed with its red-first test).
   - Special attention:
     - the reader base's task tops and Timer callbacks;
     - `Lockable` and the locked-value helpers;
     - the config snapshot and recovery paths (CFG_SNAPSHOT_RAISED, RECOVERY_READ_RAISED and RECOVERY_WRITE_RAISED
       log there);
     - every widened `except`.
   - Commit per class of functions, each commit green with the same checks as BR1's.
3. Defects: br1's item 3 rules. A fix outside asy_base_classes.py is not yours; hand it back.

## Notes
- File edits use the Edit or Write tool. A deletion is its own Bash call. No `git stash`, no nohup.
- Runs go through BR1's wrapper, copied to your log dir, with RUNS.md lines naming `U35 lane BR1b`.
- After any src edit, rebuild with `S/u23/rebuild.sh`.
- Commit subject `U35 lane BR1b: <summary>`, with the two trailers. Do not push. A refused command stops you.
- Count your tool calls. At 80, commit what is green and hand back at a seam, with the groups left.
- Hand-back:
  - commits;
  - rows by verdict (before, after);
  - every defect;
  - the e51 rows added;
  - any question for the owner, in prose;
  - last line "nothing of mine is running".
