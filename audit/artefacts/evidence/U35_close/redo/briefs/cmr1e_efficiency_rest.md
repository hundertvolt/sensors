# CMr1e: the three widened twin files still slow; then the remaining pick sites, bites and rows (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cmr1d_efficiency_rest.md` (its rulings and items apply;
yours are what is still open there), its parents `cmr1b_device_picks_rest.md` and `cmr1_device_picks.md` (the owner's
rule), and the hand-backs `S/u35r/handbacks_redo/CMr1c.md` and `CMr1d.md`. Worktree `S/wt-u35cmr1b`, branch
`audit/u35-cmr1b` at f2fd7565 (clean). Logs in `S/u35/laneC/cmr1e/`; CMr1d's in `S/u35/laneC/cmr1d/` (times.txt,
load.txt, its probes and scripts).

## The lead's review of CMr1d (binding)
- e7d9f4a3 and f2fd7565 are kept as written. The `_driven`/`_driven_modules` copy in clock_jump follows the per-file
  idiom that timer_pool and hot_replug already carried, identically, at base. It stays, and nothing is consolidated
  now (that would move pre-existing code in an unchecked scope). The lead names it in the owner report.
- hot_replug's residual is not accepted yet. `digital_twin/` is this project's own test infrastructure and is yours to
  make efficient; `src/` is not changed for test speed. Find where each FRAM-persisted entry's 70-100 ms goes, by call
  counts and per-function probes rather than wall times under load. If the twin's SPI fake or FRAM chip model is the
  cost, make it efficient while keeping everything observable unchanged: the bytes stored, every transaction's result,
  every fault the twin injects. Prove it with the twin's FRAM tests at both stages, plus an equivalence check that
  replays one recorded transaction stream through the old and new model and compares the chip state byte for byte.
  If the cost is src's own work per entry, cite the lines and change nothing. If it would also be wasteful on silicon,
  report that as a finding for the lead.
- The same lever applies to bus_hazard's erase race (dev's 256 KiB erase through the twin) and its ten FRAM tests.
  The SCD30 system-command test's boots: drive `start_tasks()`'s stagger (`src/asy_system_service.py:778`) on the
  driven clock, as clock_jump's boots now are, unless the test's subject is that stagger. Probe the timed pause.
- ntp runs the real main() with real UDP to the responder. Read how the responder and the sockets interact with a
  driven clock before choosing a lever; CMr1c's wait list is in `S/u35/laneC/cmr1c/probe_ntp.log`. A scenario whose
  subject is a wait's length keeps that wait.

## Items, in order
1. Item 2 for ntp, hot_replug and bus_hazard: each at both stages, base52 and head back to back, times stated. Each
   ends within 10 % of base, or with its measured residual and cause. Say per file what each change keeps and skips.
   Give each change a bite that fails it.
2. If within budget: cmr1d's items 3, 4 and 5 in that order. cmr1d's line numbers refer to 4cf293d0; clock_jump's
   have moved since f2fd7565.

## Load and timings
The lead's `mc_cov` (a full `scripts/test.sh --coverage` on int) started at 05:46. Take no timing pair while it runs:
its RUNS.md "U35 lead mc_cov" RUNNING line has no done line yet, or a scripts/test.sh process is listed. Meanwhile,
work on probes, call counts, code and correctness runs. Before each timing pair, check `uptime` and the process list
against CHECKLIST 12 and record both.

## Notes
File edits with the Edit or Write tool. A deletion is its own Bash call. Every run goes through your own run wrapper in
your log dir, modelled on `S/u35/lead/run.sh` (namespace, nice 19, disk check, RUNS.md lines), with its RUNS.md lines
naming `U35 lane CMr1e`. After any src or digital_twin edit, the worktree's build follows `S/u23/rebuild.sh`. Commit each
item green on its own, subject `U35 lane CMr1e: <summary>`, the two trailers; do not push. A refused command stops you.
Past 80 tool calls, commit what is green and hand back at a seam. Hand-back: commits; per file the times (base, head,
after) and what each change keeps and skips; the bites; any digital_twin/ file changed and its equivalence evidence;
the sites' classes if reached; last line "nothing of mine is running".
