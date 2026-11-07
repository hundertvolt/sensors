# U35 lane T, blocks T4a and T4b: B2's values in the twin suite, the folds, the settrace runs, the README (lead, 2026-10-22)

## Both blocks
- Base: the integration head the lead names when starting you (B2's measurements committed). Branch `audit/u35-t4`,
  worktree `S/wt-u35t4`, already rebuilt. Logs in `S/u35/laneT/t4/`. Commit subject `U35 lane T4<x>: <summary>`;
  decision tags "(agent, 2026-10-22)".
- Read first: `S/CHECKLIST.md`, `S/u35/briefs/common_u35.md`, the B2 hand-backs the lead names (the values you
  apply, each with its source log), `S/u35/handbacks/T3f_final.md` and `T3g_final.md` (folds (1)-(3) and their
  facts), and in `S/u35/lane_plan.md` R-26 and LEAD NOTES 4, 11, 20, 24, 35, 42, 62, 71, 83 and 84 for the items they hand
  to T4. Each step's text: `python3 -I S/u35/tools/steps.py --standing <numbers>`, its P1 row by
  `grep -n "^| <n> |" S/u35/lane_plan.md`. Check every item against the tree first: what an earlier block landed is
  "found landed", not redone.
- Your files: lane T's (`scripts/_digital_twin_ci_suite.py`, `scripts/_twin_process.py`, `scripts/run_digital_twin_ci.sh`,
  the suite's tests_scripts readers, `tests/test_digital_twin_*` files lane T held, `digital_twin/README.md`). Not
  yours: `src/`, SPECIFICATION.md (a sentence your change makes stale goes in the hand-back for D3).
- Least wear holds for the twin as for the product: no added flash-filesystem or SCD30-NVM write in any scenario
  beyond what its test owns (CLAUDE.md's wear rule); the twin's flash is a file, but the pattern is the product's.
- Every new check seen failing first; every bound bitten by a plant in a scratch copy. Never run real hardware tools;
  never read arduino/; never edit ext/ or legacy/; no git stash; kill only by a checked pid; one test run at a time
  in your worktree; port-binding runs inside `unshare -n S/u24/ns_xdg.sh`; RUNS.md lines; CHECKLIST 22's disk check.
  Do not push. About 60-80 tool calls per block; past 80, commit what is green and hand back the rest at a seam.

## T4a: the values and the checks
1. B2's values into the suite: Run 11's calibration (steps 157 (4), 165's `_mem_sampler` row as B2c decided), Run 3's
   FRAM write-count rate bound (step 160's value), each with its source cited where the value is set.
2. The `TimeStale` checks LEAD NOTES 11 gives T4 (null in Run 1, false after Run 8's first sync), if not landed.
3. Folds (1)-(3) (T3g_final.md's facts; fold (3) was blocked only on P4's `unpersisted`, which the integration head
   has at src/asy_config_manager.py), each seen failing first.
4. Steps 167, 169, 170 and 171 as their texts and P1 rows state them.
5. R-26 (OF-149, OF-188): the twin integration file once per device under `build-settrace`, one process at a time
   (arzi alone takes about 75 s plain). No change unless one reproduces; a reproduction is root-caused, never retried.
6. The carried items (LEAD NOTES 106 (a) and 116 (1)): a twin scenario of the escalation's timeout path (its entry held
   past its bound and never released: ResetReason 20, the relaunch's busy block healed and logged), deterministic, with a
   knob mode that counts the hold; and the plant proof for `_UART_LOAD_REQUEST_S` (`85caca5`): a load request reclaimed
   near the outer cap with its trace held near its bound, red on the old outer-cap-plus-one-hold timeout, green on it.
Checks: the suite's readers in tests_scripts; each changed twin file at both stages.
Hand-back (at most 35 lines): commits; per item done, found landed or left with its reason; anything stale in
SPECIFICATION.md for D3 with its line; last line "nothing of mine is running".

## T4b: digital_twin/README.md and T's checks (after T4a)
1. The README texts owed by LEAD NOTES 20, 24, 35, 42, 62, 83 and 84: Run 1's text and the "SIGINT shutdown" wording;
   `MEM_SAMPLE` (:332, :780), Run 11's byte-span window and Run 3's ceiling; `silent_wren_count` and the two
   shutdown fields; the `boot phase:` text; `_flash_stall` stalling the whole config write at its close (one direct
   write again, as the product's); the twin record's text (H3's, re-recorded at both GC stages on the merged head).
   Every sentence states the tree as it stands; nothing cites an audit ID, a lane or a temporary plan.
2. T's checks: the suite's readers, test_citations, test_decision_vocabulary, then the twin CI for dev and arzi at both
   stages (`scripts/run_digital_twin_ci.sh <device>`, one at a time, inside the namespace), zero memory markers.
Hand-back as T4a's.
