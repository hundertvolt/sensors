# CO1: conformance.md's recovery rungs, every cell named (part 1) (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first (its environment, rules, checks and shell discipline bind you; CHECKLIST 1's
ban on `git stash` included). Then, on your worktree:
- CLAUDE.md;
- `audit/actions/U35.md`: A.U35.52 (:1379-1396), and A.U35.30/.31 (the supervisor rungs' failure classes);
- `audit/actions/SUPP_recovery.md` (the rung tables and their R-actions);
- `audit/b3/conformance.md` and its walk `audit/b3/conformance_walk.py`, in full;
- `audit/b3/queue_c.md` (where L3/L4 cells go);
- SPECIFICATION.md F.2's recovery ladder and E.6 (the levels L0-L4);
- `audit/b3/review.md`'s header (a cell's test must bite: review.md holds each test's verdict).

Worktree `S/wt-u35conf`, branch `audit/u35-conf` at 36bee227 (the integration head, clean, rebuilt). Logs go in
`S/u35/laneB/co1/`.

## Why
A.U35.52 needs one row per (fault path, rung R1-R7). Each row names the test that reaches it at L1, L2, L3 and L4,
or "not reachable at <level>: <reason>". Each row also names the test proving the rung:
- bounded (a driven clock or an iteration bound);
- logged once per event (one entry; a repeat raises only the count);
- race-free (a forced interleaving with a concurrent sibling session, never a sleep count).
On the head all 120 rung rows are open (L1 115 cells, L2 116). A missing cell gets its test at the lowest level that
can prove it. A rung that fails one of these properties is a recovery defect, and so a firmware fix in U35 under the
owner's rule "Firmware really complete, don't push fixes to future units".

## Items, in order
1. Re-run the walk on the head, committed alone; the record was built on an older tree.
2. Fill the rung rows' L1 and L2 cells, with the bounded, logged-once and race-free columns, rung table by rung table
   (U10, U13, U15, U16, U17, U18). Order: the cells whose test exists first, each one cited by file::test and checked
   to bite (review.md's verdict, or your own red-on-a-plant where review.md has none). Then the gaps.
   - A cell's L3/L4 entry is a queue_c.md row, as the walk does.
   - A gap gets its test at the lowest level that proves it, seen failing first on a plant, both GC stages, zero
     memory markers. Forced interleavings use a gate or barrier fake, never a sleep count.
3. **Defects.** A rung that is unbounded, logs more than once per event, or races is a defect:
   - write the test that shows it, seen failing on the base;
   - make a small, local fix;
   - run every importer's test file at both stages, each fix in its own commit.
   - If a fix would change a public contract, an API, the UART wire format or an architectural pattern, or is not
     local, do not make it. Hand back with the facts, the options and your recommendation.
4. Commit per rung table, each commit green:
   - the walk re-run, if the walk produces those cells;
   - `python3 -I audit/sweeps/review_rows.py --check`;
   - the readers of audit text (test_citations, test_decision_vocabulary, test_comment_block_cap);
   - lint and the mypy passes for any test or src file changed.

## Notes
- Not yours: A.U35.50 (the bus-hazard rows), A.U35.51 (the wear-gate table), A.U35.53 (the owner rows). They are a
  later block, in other sections of the same file. Leave them.
- Lanes BR (raising.md) and CMr (twin files) run beside you. CMr1g edits tests/test_digital_twin_ntp.py,
  _bus_hazard_concurrency.py, _hot_replug.py and _clock_jump.py. A gap test belongs in a new test file or another
  file, never in those four. Name in your hand-back any gap whose natural home is one of them.
- File edits use the Edit or Write tool. A deletion is its own Bash call. No `git stash`.
- Every run goes through your own run wrapper in your log dir, modelled on `S/u35/lead/run.sh`, with RUNS.md lines
  naming `U35 lane CO1`. Before each heavy run, check `uptime` and the process list: never more than 4 heavy
  processes on the host.
- After any src edit, rebuild with `S/u23/rebuild.sh`.
- Commit subject `U35 lane CO1: <summary>`, with the two trailers. Do not push. A refused command stops you.
- Count your tool calls. At 80, commit what is green and hand back at a seam, with the rows left.
- Hand-back:
  - commits;
  - cells by state per rung table (before, after);
  - every test added, with its red-first evidence;
  - every defect: site, test and fix;
  - every queue_c.md row added;
  - every question for the owner, in prose;
  - last line "nothing of mine is running".
