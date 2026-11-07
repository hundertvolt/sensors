# U35 lane D, block D3g: SPECIFICATION.md after the gate fixes (lead, 2026-10-22; docs only, beside H4 and gate 2)

- Base: `c398332` (the integration head with the gate fixes merged). Branch `audit/u35-d3g`, worktree `S/wt-u35d3g`.
  Logs in `S/u35/laneD/d3g/`. One commit, subject `U35 lane D3g: <summary>`; decision tags "(agent, 2026-10-22)".
  Your file: SPECIFICATION.md only. Line numbers below are at `c398332`.
- Read first: `S/CHECKLIST.md` (binding), `S/u35/briefs/common_u35.md` (its Rules), the hand-backs
  `S/u35/handbacks/G1b_final.md`, `G2_final.md` and `G3_final.md` (their "for D3" lines), and LEAD NOTES 106, 110,
  111 and 113 in `S/u35/lane_plan.md` (the decisions and the reasons the text must carry). Check every sentence against
  the code at `c398332` (`git diff 069b9fe c398332 -- src/` is the whole firmware change) before you write it.
- A host task re-records the twin record and then the gate runs on this host: run nothing but the docs checks below,
  under `nice -n 19`, with RUNS.md lines.

## Write (each sentence states the tree as it stands; no history, no audit ID, lane or temporary plan)
1. The FRAM protocol paragraph (:184-191) and the chunk paragraph after it (:192-207): a chunk write reads block 1's
   status pair first (one READ, its own CS cycle) and writes a copy that is not idle before the other, so the write
   path never leaves both copies marked; a failed status read is logged (FRAM_STATUS_READ) and block 1 goes first.
   Every CS cycle still stays (one is added, none removed). The status cells' operation counts per read and per write
   (:206-208) as the code now does them, and the endurance figure as `tests/test_asy_fram_wire_trace.py` pins it.
   Keep the owner's decisions there exactly as written: actor, date, qualifier, scope and the "don't fix it" on a
   read's busy mark (CLAUDE.md's decision-record rule (3)).
2. The error-log cost paragraph (:209 on): the both-copies-marked loss stays accepted (owner, 2026-09-11; confirmed
   2026-09-26), unchanged in actor and scope; the mechanism sentence now says it arises when an abrupt reset lands in a
   read (or a read's repair write) while the other copy is already marked. The "roughly 1 abrupt restart in 8" figure
   was measured on the earlier write order: leave the figure's sentence exactly as it is and hand back its line; block
   B2c re-measures it and D3 writes the number.
3. A.8 and the connection paragraphs (about :8258-8284; `con.http_call` at :6588 and `web.per_call_timeout_s` at
   about :11773): a refused connection closes within one per-call timeout; every trace the connection task awaits
   before its close (the refusal, a refused head, a peer reset, the three reclaim arms) is held at most one per-call
   timeout, and an entry cut short stays in RAM for the logger's next write; the task's top-level catch keeps a direct
   error trace, the one pre-close trace not bounded, with LEAD NOTES 113's reason. Correct the "already persisted"
   sentence (:8258-8262) to what the arms now do.
4. G2's lines: `l2.scenario_request_timeout_s`'s basis (about :12216) beside the UART load's derived client timeout
   (the device's outer cap plus one flash hold, read from `src/`), and the "no failed transfer" sentence (about :9785),
   each as G2_final.md and the tree say.
5. Grep SPECIFICATION.md for every sentence quoting the old escalation-timeout message (`src/asy_system_service.py`
   :580's former wording) or naming where FRAM_STATUS_READ is raised; bring each in line with the tree.
Checks before the commit: test_citations, test_decision_vocabulary, test_legacy_paths, test_tunables_register and
every tests_scripts reader of a section you changed (grep tests_scripts for the section's heading or key). Never run
real hardware tools; never read arduino/; never edit ext/ or legacy/; no git stash; do not push. About 40-60 tool
calls; past 80, commit what is green and hand back the rest.

Hand-back (at most 30 lines): the commit; per item, landed or left with its reason; the 1-in-8 sentence's line for
B2c and D3; anything else stale you found outside your items, with its line; last line "nothing of mine is running".
