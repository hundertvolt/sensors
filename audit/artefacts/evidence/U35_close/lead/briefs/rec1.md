# U35 records block REC1: everything final through the gate-fix round (lead, 2026-10-22)

Read `S/CHECKLIST.md` (binding) and `S/u35/briefs/common_u35.md` (only its Rules). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## Why now, and the seam
U35's records are too large for one block, so they split at a natural seam. You write everything that is final now:
waves W1 to W6 and LEAD NOTES 1 to 111. A later block, REC2, fills the placeholders after the full gate on the merged
head, B2, T4, D3, the final merge, Run 11, the tier and CI. Use exactly these placeholders, each on its own line or
cell: `<G3>` (block G3 and the G2+G3 merge: under the lead's review now), `<GATE2>`, `<B2>`, `<T4>`, `<D3>`,
`<W10>` (final merge, Run 11, tier) and `<CI_U35>`. A G3 task is running tests on this host now: run no test,
build or twin yourself except the three docs checks at the end, under `nice -n 19`.

## Base
Branch `audit/u35-rec` in `S/wt-u35rec`, at `a81a65a` (the integration head: 069b9fe + G1a `02e3be8` + G1c
`a81a65a`). Audit files only; one commit, subject "U35 int: the close records, first part". Line numbers you cite are
at `a81a65a`; say so once in the record (REC2 re-checks them on the final head).

## Sources
- `S/u35/lane_plan.md`: P1a-P1d's step tables, P2's cut, waves and rulings (P2.4, R-1 on), LEAD NOTES 1 to 111.
- `S/u35/handbacks/*_final.md` (about 90), `S/u35/harness_counts.txt`, `S/u35/lead/close_items.md` (the lead's list
  of what the records must carry: every item there lands, or is marked for REC2 with its reason).
- `S/u27/lead_todo.md` ("U35" entries), `S/u21/RUNS.md`, `S/u35/gate1/` (gate 1's logs; its evidence folder).
- Models: U34's record `audit/sweeps/scan_runs/20261021_U34_close.md`, U34's REGISTER rows (`audit/REGISTER.md`,
  the `| U34 |` rows after U33's), `S/u34/briefs/rec.md` (U34's records brief) and `S/u34/close/assemble.sh`.

## Write
1. `audit/sweeps/scan_runs/20261022_U35_close.md`, with U34's sections. Every step by P1's number with its verdict
   (applied with its commit, landed with its anchor, check-only, parked, or `<B2>`/`<T4>`/`<D3>` where that block owns
   it); the rulings; the silent-failure scan per class for the changed code; each change's effect per operating mode
   from the hand-backs; the working economy (each block's harness count); "## Gates" holds gate 1 (LEAD NOTES 105: its
   three reds, each root cause and fix, G1a, G1b, G1c, G2, `<G3>`) then `<GATE2>`; "## CI" holds CI on U34's squash
   (run 39665515089, pull_request, 46 of 46 jobs success on `49fde7b`, 19:53-20:19 UTC; `S/u27/lead_todo.md` 20:20)
   and `<CI_U35>`.
2. `audit/REGISTER.md`: the unit row `| U35 |` set as U34's (state `<W10>` until REC2). U35's rows after U34's CI
   row: the lane plan and waves; the rulings; closed and moved findings; decisions taken on the owner's behalf; the
   owner's decisions in U35, each with its words and its question as the LEAD NOTES quote them, word for word,
   never paraphrased unless marked "paraphrase" (least wear as a central rule, the config write, the screening, the
   UART link exception, the cleanups' no-regression condition and provenance rule, the order after U35, and every
   earlier U35 owner answer the LEAD NOTES quote); close_items.md's nine REGISTER items; the gates (gate 1 now,
   `<GATE2>`); CI (`<CI_U35>`). LEAD NOTES 111 is an agent decision accepted by the owner with its quote: record it
   so, never as an owner decision.
3. `audit/sweeps/open_findings.md`: every finding a U35 hand-back or LEAD NOTE routed, one row each (or one per
   target unit when the file lists stay readable), by the routing rule: the next unit in
   `audit/order/work_order.json` whose files list holds its file; if none, U35 for a test file and U37 otherwise.
   U36's rows carry the finding and its route only, nothing more (the owner deferred U36 and asked for no U36
   preparation: LEAD NOTES 108). Close the rows U35 closed (OF-225 per close_items.md; OF-236 per LEAD NOTES 20;
   every other row naming U35 the hand-backs close), each with its commit.
4. `S/u35/close/assemble.sh`, modelled on U34's: U35's lanes `S/u35/lane*/`, plan scratch logs, hand-backs, the
   lead's files, `gate*/`. Logs only: no code, no copy of a tracked file; no secret value; the hotspot default and the
   bench LAN's third octet masked as U34's script does. Do not run it (REC2 does, with the final logs).
5. `S/u35/close/squash_msg_draft.txt`: subject `U35: <summary>`, lines at most 100 characters, no audit IDs and no
   model name; the body names what changed per lane and every meaning change the commits named, with `<G3>`,
   `<B2>`, `<T4>`, `<D3>` paragraphs left as placeholders; the two trailers from CHECKLIST.

Priority if the budget runs short: 2, 3, 1, 5, 4. About 60-80 tool calls; past 80, commit what is written and hand
back the rest at a seam. Before the commit run `tests_scripts/test_citations.py`, `test_decision_vocabulary.py` and
`test_legacy_paths.py` on your head (`nice -n 19`, RUNS.md lines) and confirm them green. Never read arduino/; never
edit ext/ or legacy/; no git stash; do not push; touch no other worktree.

## Hand-back (at most 35 lines)
The commit hash; each file written; the new and closed findings rows by unit; every agent decision taken on the
owner's behalf in U35 that touches a flash-filesystem or SCD30-NVM write (CHECKLIST 24: those go to the owner as
questions, never as decided), each with its LEAD NOTE; what you left for REC2 beyond the placeholders and why;
anything you could not settle; last line "nothing of mine is running".
