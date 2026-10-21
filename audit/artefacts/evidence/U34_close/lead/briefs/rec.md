# U34 records block REC (lead, 2026-10-21)

Read `S/CHECKLIST.md` (binding) and `S/u34/briefs/common_u34.md` (only its Rules). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`.

## What U34 was
U34 (LIC) had four lanes, merged into `audit/u34-int` in `S/wt-u34c`:
- lane A, attribution: THIRD_PARTY_LICENSES.md, four `src/` headers, `src/LICENSE-captive_dns`, the new
  tests_scripts/test_third_party_attribution.py, the freezefs check, README (`92ad46f`, merged `eefe5dd`);
- lane T, the type-check configuration: the explicit-`Any` baselines keep only modules that still hold it, the
  `_RESIDUAL` subset guard, the CPY001 reason, the chroot list (`f689820`, merged `a579859`);
- lane N, the UDP socket: its header, `write_and_recvfrom()` removed with its tests rewritten, SPECIFICATION.md F.2,
  A.1, B.10.1, K.9 and two Part N rows (`63971d8`, merged `b1bf1f3`);
- lane C, CI: the four Playwright cache keys gain the runner identity, pinned in test_ci_workflow.py (`0f55912`).
- The lead re-recorded the twin record on the merged lanes (`1dd6dd5`): `S/u34/lead/twin_record/trace.txt`, 122
  results unchanged, every moved hash traced. The lead's whole `tests_scripts` tier on `1dd6dd5`: 3686, 994, 887 and
  1136 passed in its four groups, 6 + 3 skipped, 0 memory-marker logs (`S/u34/int/tier_1dd6dd5/summary.txt`).
- The lead then merged U33's records head (`f3fff0e`) and U33's final head (`07035b1`, the tree of U33's pushed
  squash `83261b1`). Your base is `b00a288`, the merge of both (U33's 129 later audit paths identical to `07035b1`, nothing else moved).

Sources:
- the plan `S/u34/lane_plan.md`: P1's step table, P2's rulings R-1 to R-25, LEAD NOTES 1-7;
- the hand-backs `S/u34/handbacks/{P1,P2,A1,A2,N1,N2,T1,T2,C1}_final.md`; the call counts `S/u34/harness_counts.txt`;
- the lead's log, `S/u27/lead_todo.md` ("U34" entries), and `S/u21/RUNS.md`.

## Write (on `audit/u34-int` in `S/wt-u34c`; audit files only, one commit, subject "U34 int: the close records")
1. **`audit/sweeps/scan_runs/20261021_U34_close.md`**, modelled on U33's record in the same folder and with its
   sections:
   - every step by P1's number with its verdict: applied with its commit, landed with its anchor, check-only, parked;
   - the rulings, and the silent-failure scan per class for the changed code (lane N's `src/` change and the new test
     file; the rest is configuration and documents: say so per class);
   - each change's effect per operating mode, which the hand-backs name;
   - the working economy: each block's harness count, and the tier run once on the integration head (LEAD NOTES 5);
   - "## Gates" holds only the line `<GATES>: the lead fills this section.`;
   - "## CI" holds `<CI_U33>` (U33's squash run, the lead's) and the sentence that U34's own run is recorded in U35's
     record.
2. **`audit/REGISTER.md`.**
   - The unit row (`| U34 |`), set as U33's is: done, with the record and the evidence path
     `audit/artefacts/evidence/U34_close/`.
   - U34's rows after U33's last (U33's rows end with its CI row): the lane plan and waves, the rulings, the closed and
     moved findings, the decisions taken on the owner's behalf, the gates (`<GATES>`, the lead's), and CI on U33's
     squash (`<CI_U33>`, the lead's).
3. **`audit/sweeps/open_findings.md`.**
   - OF-208 closed at lane C `0f55912`. The first CI run after U34's push downloads the Playwright browser once, which
     the row expects (LEAD NOTES 2).
   - The explicit-`Any` residue that T1's hand-back lists, routed per U35's plan (`S/u35/lane_plan.md`, P2.4 R-15):
     - the 13 modules R-15 names go to U35;
     - `_boot_contiguity_probe` and `_uart_link_contract` go to U36;
     - `scripts._hardware_verdict` goes to U37, together with R-14's four `no-any-unimported` sites from the bare
       `_summary_block` import (U34 R-4).
     - Each row names the module, its sites (path:line from T1) and its config lines: the baseline line, the ANN401
       entry and the `_RESIDUAL` row.
     - One row per target unit is enough when the rows' file lists stay readable.
   - Any finding a U34 hand-back raised that no step closes gets its own new row with the routing rule's target: the
     next unit in `audit/work_order.json` whose files list holds its file; if none, U35 for a test file and U37 for any
     other.
4. **The evidence.**
   - `S/u34/close/assemble.sh`, modelled on `S/u33/close/assemble.sh`: U34's lanes `S/u34/lane{A,C,N,T}/`, the plan
     scratch logs, the hand-backs, the lead's files (`S/u34/lead/`, `S/u34/int/`), and `gate*/` folders when the lead
     adds them. It stages to `S/u34/close/evidence`.
   - `S/u34/close/evidence_README.md`, modelled on U33's, with `<GATE>` and `<EVCHECK>` placeholders.
   - Run assemble.sh once and report the staged count. Do not copy the evidence into the tree: the lead does.
5. **`S/u34/close/squash_msg.txt`.**
   - Subject `U34: <summary>`; at most 100 characters per line; no audit IDs and no model name.
   - The body names what changed per lane and each meaning change the commits named.
   - The trailers: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
     `Claude-Session: https://claude.ai/code/session_01BWfjT6GSD7bxCP57j86vB8`.

Before the commit, run test_citations, test_decision_vocabulary and test_legacy_paths on the head and confirm them
green. Nothing is pushed, and nothing under `S/u34/close/evidence` is committed.

## Hand-back (at most 30 lines)
The commit hash; each file written; the findings rows; the staged evidence count; anything you could not settle.
