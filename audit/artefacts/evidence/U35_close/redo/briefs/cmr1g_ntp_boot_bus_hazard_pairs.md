# CMr1g: ntp's per-boot cost, bus_hazard, the formal pairs (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first. Then read `S/u35r/briefs/cmr1f_ntp_bus_hazard.md`: its rulings stand,
except where this sheet changes one, and its items 3-5 are yours. Also read the chain it names and the hand-backs
`S/u35r/handbacks_redo/CMr1e.md` and `CMr1f.md`. Worktree `S/wt-u35cmr1b`, branch `audit/u35-cmr1b` at a425deec
(clean). Logs in `S/u35/laneC/cmr1g/`; CMr1f's in `S/u35/laneC/cmr1f/`.

## The lead's review of CMr1f (binding)
- 6f41678e and a425deec are kept as written. The E.6.6 `twin-instrument` row is adopted by the lead (it follows the
  unretrieved-report row) and named to the owner as allow-list growth. `DrivenWall` in the construction helper is the
  right place (its reasons stand).
- The idle-poll skip may now be used in ntp too: the rule is per file, only where its cost is measured and its
  equivalence proven on that file's own rounds. Prove it as CMr1e did for hot_replug (the real poll run on every
  skipped round, waking nothing and leaving the map unchanged, at both stages). Use it only if the proof holds.
  Suite-wide use stays with the owner.
- mc_cov ended at 06:36 (RUNS.md:7759). Timing pairs are allowed from now on under CHECKLIST 12 (at most 4 heavy
  processes; check uptime and the process list before each pair and record both). N11b and CRr2b8 also run.

## Items, in order (each committed green on its own)
1. ntp's restore: about 2.7 s per boot with the skip, over 8 boots. Probe where it goes (call counts and inclusive
   time per function: build_system, the setups, FRAM init, anything else). Remove what tests nothing, for example a
   driven clock that is left unused or a real wait. Never drop a boot, a wiring or an assertion. The skip proof
   above is part of this item.
2. CMr1f's open side effect: after `DrivenWall` exits, tasks that main() spawned and `cancel_all` missed stay parked.
   Count them after each ntp test and read gc.mem_free at both stages. Show that they neither grow the heap across the
   file nor wake inside a later test, or fix that.
3. bus_hazard, as cmr1f's item 3 states (the stagger on the driven clock, the timed pause probed, the erase race and
   the FRAM tests: a lever or the measured residual with its cause).
4. The formal pairs: hot_replug, ntp, bus_hazard and clock_jump, base52 then head back to back at both stages. Each
   file ends within 10 % of base, or with its measured residual and cause.
5. If within budget: ntp's and clock_jump's device-pick sites (cmr1f item 5).

## Notes
- File edits use the Edit or Write tool. A deletion is its own Bash call.
- Every run goes through your own run wrapper (copy CMr1f's), with RUNS.md lines naming `U35 lane CMr1g`.
- After any src or digital_twin edit, rebuild with `S/u23/rebuild.sh`. `src/` is not changed for test speed.
- Commit subject `U35 lane CMr1g: <summary>`, with the two trailers. Do not push.
- A refused command stops you.
- Count your tool calls. At 80, commit what is green and hand back at a seam.
- Hand-back:
  - commits;
  - per file, the times (base, head, after), and what each change keeps and skips;
  - the bites;
  - the skip's proof for ntp;
  - the parked-task counts;
  - the site classes, if reached;
  - last line "nothing of mine is running".
