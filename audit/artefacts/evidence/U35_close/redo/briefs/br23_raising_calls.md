# BR2 and BR3: raising.md, parts 2 and 3 (lead, 2026-10-27)
Your task is `S/u35r/briefs/br1_raising_calls.md`'s items 2-4, for your own modules only. Its reading list, its
"Why", its verdict rules, its defect rules and its notes all apply. Item 1 is done, by BR1's 651d3e79:
- hand verdicts live in `audit/b3/raising_verdicts/<module>.json`, as
  {"raises": {function: {verdict, proof}}, "calls": {"function::callee": {can_raise, verdict, proof}}};
- a call verdict splits that function's calls out of the module-wide group;
- the walk refuses a stale key and then writes nothing;
- every hand "unreachable" is rendered into a block in e51.md's header, and e51_sweep.py's render keeps that block;
- `--check` verifies without writing.
Read the new `audit/b3/raising_walk.py` in full before using it. Edit only your modules' JSON files. Then re-run the
walk, which regenerates raising.md and e51.md's block. When the lead merges the three lanes, it re-runs the walk over
the merged JSON files, so a conflict in the generated text is never resolved by hand.

| Lane | Modules | Worktree, branch (at 651d3e79, rebuilt) | Logs | RUNS.md name |
|---|---|---|---|---|
| BR2 | `asy_config_manager.py`, `asy_system_service.py` | `S/wt-u35braise2`, `audit/u35-braise2` | `S/u35/laneB/br2/` | `U35 lane BR2` |
| BR3 | `asy_fram_manager.py`, `asy_fram_driver.py` | `S/wt-u35braise3`, `audit/u35-braise3` | `S/u35/laneB/br3/` | `U35 lane BR3` |

- BR1 classifies asy_base_classes, asy_print_log and math_helpers at the same time. A call into one of those that
  the walk marks "transitive" takes that module's own rows. Do not classify those rows in your files.
- A defect fix in src touches your modules only. If the right layer is in another lane's module, hand it back
  instead.
- Also check, for every commit: `S/wt-base/.venv/bin/python3 -I audit/sweeps/e51_sweep.py --check` and
  `python3 -I audit/b3/raising_walk.py --check` (see the walk for its arguments).
- Commit subject `U35 lane BR2: <summary>` or `U35 lane BR3: <summary>`, with the two trailers. Do not push. No
  `git stash`.
