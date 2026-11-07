# R3 brief, phase B, lane M: the runs and A1 (lead, 2026-11-04 16:21 UTC)

Read first: `S/u35r/r1/common_r1.md` (binding; labels start with `r3m_`), `S/u35r/r3/ROWS.md` (phase A's table; your
rows are named below), `S/u35r/r3/ACTION_LIST.md` (the lead's decisions, binding), PLAN.md's R3 row
(`S/u35r/plan/PLAN.md`). Two read-only lanes (D1, D2) work at the same time in `S/wt-u35int`; they run only static
walks of seconds. You own every test run; run them one at a time, each through `S/u35/lead/run.sh`.

- Worktree `S/wt-r3`, branch `audit/r3`, at `17688315`. Its `node_modules` is a symlink: never stage it.
- `tests_hardware` runs only with `--collect-only` or against the twin. Before the instrument runner starts, read
  `scripts/record_twin_instrument_runs.py` and confirm it drives the twin only; if anything in it could reach a board
  or the host's network config, stop and say so in the hand-back.
- Working records go to `S/u35r/r3/m/`, scratch to `S/u35r/r3/m/ftmp/` (delete it before the hand-back). The tree is
  restored after every run that writes into it (`git status` clean apart from your commit).

## The runs, in order (ROWS.md section 3, items 1-6; record label, rc and wall clock of each)
1. `pytest tests_hardware --collect-only` (P2): the count, every error.
2. The coverage run on the final tree, then `e51_sweep.py` classes each unexecuted line of `src/`, the generated code
   and the host tools (rows OR16 (3), OR22, OR23, OR25 (3)) into `m/coverage.md`. A line classed dead is listed with
   its evidence and never removed (owner).
3. The plant run over the sites R1 and R2 changed, in the owner's scope ("complex measurement tests"), with the
   changed check-style triggers (OR16 (4), OR19 (3), OR21 (1)): `m/plants.md`. A survivor is a gap.
4. The twin instrument runner, both stages (OR29.a (4)): move `tests_hardware/twin_record.json` to `m/`; each red is
   reproduced and classed (a) product defect, (b) twin fidelity, (c) test; the exceptions listed with reasons.
5. The per-file live-heap probe over `tests/` (OR38, R1's B36 method): `m/heap.md`; a file that grows per test is a
   gap.
6. The bench probes on the twin through a throwaway script (P6): `m/probes.md`; each disagreement is a proposed
   fidelity-table row (A10).

## Then A1 (ACTION_LIST item 2)
- From `S/u35r/paused_pub/lane_ldcm3.patch.gz`: the full soft-callback queue test, seen red on a planted break, then
  green. The DNS flood only inside a boot the exclusive port-53 leg already makes, with no new boot and no timeout
  change; otherwise not added, and say why in one line.
- One commit on `audit/r3` (message rules as in common_r1.md, no audit IDs). While fixing, only the file you changed
  runs. No full gate yet: the gate comes after the fix round.

## Gaps
No other test, file or doc line is added (ACTION_LIST item 3). Each gap goes to the hand-back with its evidence and the
proposed test in one line; the lead admits them and sends you the fix round as a message.

## Hand-back
`S/u35r/r3/HANDBACK_M.md` (first line "R3 lane M hand-back, written by the agent (<date -u>)"): each run's label, rc
and wall clock; the rows each closes; the gaps; the dead lines; A1's commit and its added lines. Your final message:
the path, five lines of totals, and last "nothing of mine is running".
