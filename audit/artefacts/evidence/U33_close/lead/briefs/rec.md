# U33 records block REC (lead, 2026-10-21)

Read `S/CHECKLIST.md` (binding) and `S/u33/briefs/common_u33.md` (its Rules). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## What U33 was
U33 (DOC) changed documents only: BACKLOG.md, CLAUDE.md, SPECIFICATION.md, tests_hardware/README.md and the two
`tests_scripts` allowlists (four rows removed). Plan `S/u33/lane_plan.md` (P1, P2 rulings R-1 to R-24, LEAD NOTES);
hand-backs `S/u33/handbacks/{P1,P2,B1,B2,B3,S1,S2}_final.md`; lead's rulings L-1 to L-7 in `S/u33/briefs/b2.md`; the
call counts `S/u33/harness_counts.txt`; the lead's log `S/u27/lead_todo.md` (from "U33" entries) and `S/u21/RUNS.md`.
Integration: `audit/u33-int` in `S/wt-u33s`, head `0f88c8c` = U32's pushed squash `970b63b` plus U33's six files
(lane S `ade93e6` from `939f78a`, lane B `629069e`, merged `147ea3f`); the tier on `147ea3f`: 3678, 965, 899 and 1150
passed, 9 skipped, 0 memory markers (`S/u33/int/tier_147ea3f/`).

## Write (on `audit/u33-int` in `S/wt-u33s`; audit files only, one commit, subject "U33 int: the close records")
1. `audit/sweeps/scan_runs/20261021_U33_close.md`, modelled on `audit/sweeps/scan_runs/20261021_U32_close.md` (its
   sections: summary, Files and passes, Findings, Modes, Process, Gates, REGISTER rows, open findings, CI), shorter as the
   unit is: every step by P1's number with its verdict (applied with commit, landed with anchor, check-only, parked
   for hardware, held by owner question 6); the rulings; the silent-failure scan (documents only: say so per class);
   the modes each document change describes (S2 and B2 name them); the working economy (each block's harness count; the
   lead's tier-once-on-int change, LEAD NOTES 5 in U34's plan states the same rule); "## Gates" holds only the line
   `<GATES>: the lead fills this section.`; "## CI" holds `<CI_U32>` (U32's squash run, the lead's) and the sentence that
   U33's own run is recorded in U34's record.
2. `audit/REGISTER.md`: the unit row (`| U33 | DOC | not started | — |`, set as U32's row is: done, with the record and
   evidence paths `audit/artefacts/evidence/U33_close/`), and U33's rows after U32's last (`| U32 |` rows end with the
   gates row): the lane plan and waves, the rulings, the closed and moved findings, the decisions taken on the owner's
   behalf, the gates (`<GATES>`, the lead's).
3. `audit/sweeps/open_findings.md`: OF-121 closed (R-19: no edit; cite the SPECIFICATION.md sentence stating current
   state, located by text in the head); OF-226 re-pointed to U35 (R-5, its reason); OF-230 closed at `629069e` (both
   CLAUDE.md sentences; its sibling sites SPECIFICATION.md L.1 and `devices/wozi.toml:1` stay with U36, say so). Any
   finding a U33 hand-back raised that no step closes gets its own new row with the routing rule's target (B1's 4.7:
   `audit/actions/C.md`'s H76 gives the UART link warning number 11 where the code says 54, `src/asy_uart_comm.py`, and
   `buildgen/error_catalog.json`; fix that number in C.md directly in this commit, it is an audit file).
4. The evidence: `S/u33/close/assemble.sh` modelled on `S/u32/close/assemble.sh` (U33's lanes `S/u33/laneB/`,
   `S/u33/laneS/`, the plan scratch logs, the hand-backs, the lead's files, `S/u33/int/`), staging to
   `S/u33/close/evidence`; and `S/u33/close/evidence_README.md` modelled on U32's, with `<GATE>` and `<EVCHECK>`
   placeholders. Run assemble.sh once and report the staged count. Do not copy the evidence into the tree (the lead does).
5. `S/u33/close/squash_msg.txt`: subject `U33: <summary>` (at most 100 characters per line, no audit IDs, no model
   name), body naming what changed per document and each meaning change the commits named (the wozi narrowing, the E722
   bullet, B.16's declined checkers, the L.6.6 owner-decision wording), and the trailers:
   `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
   `Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8`.
Before the commit: test_citations, test_decision_vocabulary and test_legacy_paths on the head (they skip `audit/` or
read it; confirm green). Nothing pushed, nothing under `S/u33/close/evidence` committed.

## Hand-back (at most 30 lines)
The commit hash; each file written; the findings rows; the staged evidence count; anything you could not settle.
