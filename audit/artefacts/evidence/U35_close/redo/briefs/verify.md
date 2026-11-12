# U35 recovery verification: what does U35 still owe at 656fc82? (lead, 2026-10-26)

## Why
The cloud container was reclaimed during a pause. Everything pushed survives: the audit branch at `656fc82`
(2026-10-22 18:56 UTC), whose tree outside `audit/` equals the integration head `7851668` that passed U35's gate 2
(LEAD NOTES 118). Every U35 commit after that is lost: about 25 agent blocks (B2, N4, N5, T4, CE, CF, CR, CM, F1, the
records block REC1's commit, and the stopped F2, F3, CM2). The owner (2026-10-26): "Collect everything you still find
and double verify thoroughly that you really found everything important. Don't simply trust that the recordings are
complete. In any case of doubt, rather redo the required steps."
So this check does not trust the lead's records: it re-derives, step by step, from the step texts and the tree itself,
what U35 still owes on top of `656fc82`.

## Sources (S = /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad)
- The tree: `S/wt-base` (a detached checkout of 656fc82; read only, do not edit, build or run anything heavy there).
- Each step's text: `python3 -I S/u35/tools/steps.py <n...>` (its change IDs from `audit/order/work_order.json`, each
  change's section of `audit/consolidation/M_*.md`, and its P1 row from `S/u35/lane_plan.md`). The action texts behind
  the changes: `audit/actions/U35.md` (A.U35.*) and the other `audit/actions/U*.md` a change cites.
- What was done before gate 2: `S/u35/lane_plan.md` (P1 rows at planning time, then LEAD NOTES 1-118; the wave plan
  W1-W10 at about line 840-875), the hand-backs `S/u35/handbacks/*_final.md`, the briefs `S/u35/briefs/`, and
  `S/u35/close_items.md`, `S/u35/lead_todo.md`.
- What was done after gate 2 and lost (the lead's recovered notes; incomplete by nature):
  `S/u35r/recovered/lead_notes_119_148.md`, `S/u35r/recovered/handbacks/`, `S/u35r/recovered/briefs/`,
  `S/u35r/recovered/owner_rulings_after_LN118.md`.

## Your job (your step range is in your start message)
For every step in your range, read its text and its P1 row, then check the tree at 656fc82 yourself (grep, read the
cited lines; `git -C S/wt-base log --oneline -- <file>` where history helps). Give one verdict per step:
- `LANDED` with the evidence (file:line, or the commit), every part of the step's change checked, not just its first;
- `PART` with exactly what is still owed (each missing part, its file);
- `OWED` with what the step asks for;
- `HW` for a part that only silicon can settle, with its hardware round (R0-R5) if the step names one.
Then, for each owed part, one cross-reference: the post-gate-2 block that was doing it, from the recovered notes
(B2a/B2b/B2b2/B2c, N4, N5, T4a/T4a2/T4b2/T4b3, CE/CE2/CE3, CF1/CF1b/CF1c, CR/CR2/CR3/CR4, CM/CM2/CM3/CM4, F1/F2/F3,
D3, REC1/REC2, W10), or `NO RECORD` when no recovered note or brief mentions it. `NO RECORD` items matter most: they
are what the records may have missed.
Also list anything you find in the tree that contradicts a record (a step a hand-back calls landed that is not, or the
reverse), and any part of a step whose text no block's brief covered.

## Rules
Read only. Never edit any file outside `S/u35r/verify/`, never commit, never run tests, builds, twins or `npm`; light
`python3 -I` one-off reads and greps are fine. Never read `arduino/` (`':!arduino'` in every git grep). Never run real
hardware tools. Never write a secret's value. If the permission system refuses an action, say so in the hand-back.
Write your table to `S/u35r/verify/V<k>.md` (one row per step: `| n | change IDs | verdict | evidence or what is owed
| block or NO RECORD |`), then hand back at most 60 lines: counts per verdict; every PART/OWED/HW step in one line each
with its block or NO RECORD; the contradictions; last line "nothing of mine is running". About 60-80 tool calls; batch
independent reads in one turn (CHECKLIST 17-19 in `S/CHECKLIST.md`).
