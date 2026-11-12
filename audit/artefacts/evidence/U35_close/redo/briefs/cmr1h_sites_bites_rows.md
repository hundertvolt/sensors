# CMr1h: bus_hazard's last lever, the heap step, the remaining device-pick sites, the bites, the rows (lead, 2026-10-27)
Read only what your items need (owner budget direction: no whole chains): `S/u35r/briefs/redo_common.md`;
`cmr1_device_picks.md` (the owner rule); `cmr1b_device_picks_rest.md` item 4 (the bites); `cmr1d_efficiency_rest.md`
item 3 (the sites); `S/u35r/handbacks_redo/CMr1c.md`'s E.2.1 part; `CMr1g.md` (the state). The other CMr1 briefs
and hand-backs only when a point here is unclear; their rulings stand. Worktree `S/wt-u35cm2`, branch `audit/u35-cm2` at the integration
head cce274e1 (CMr1 and CO1's I2C rung fix are merged there; clean, rebuilt). Logs in `S/u35/laneC/cmr1h/`; CMr1g's in `S/u35/laneC/cmr1g/`.

## The lead's review of CMr1g (binding)
- 7534a51a and 5624046c are kept. ntp's +12 % at 32768 is the measured residual: the poll tax on rounds where a socket
  is registered, OF-243's subject, which U36 fixes at its root. The wider skip over socket rounds is declined. Do not
  build it.
- DrivenTime's 1000-round busy-loop bound is a check and is never raised.

## Items, in order (each committed green on its own)
1. bus_hazard's last lever, a bounded attempt. In the SCD30 system-command test and the erase race, drive only the
   boot: `start_tasks()`'s stagger (src/asy_system_service.py:778, 1.06 s per boot) and the timer sequencer. Leave the
   driven clock before the shutdown sequence, whose CPU-bound rounds trip the bound.
   - Keep every boot, wiring and assertion, and the erase's real wire time where that is the subject.
   - Bite: a copy whose boot wait never elapses fails.
   - Take the formal pair (base52 then head, both stages, CHECKLIST 12's load recorded). If the attempt fails, the
     residual is the added wirings' real boots, measured, with its cause.
2. The heap step: ntp's mem_alloc after a collect grows about 0.15 MB each time arzi boots again. Attribute it. Read
   `micropython.qstr_info()` and `mem_info()` before and after each boot, the qstr pool first. Show that it is bounded
   (it stops growing), or find what grows. If it is a test-process artefact, such as interned names or a module
   cache, say so with the numbers. If it would grow on silicon too (it cannot: the board boots once), say so.
3. The remaining device-pick sites (cmr1d item 3, all of them, ntp's and clock_jump's included). Class each one by
   measurement under the owner's rule (`cmr1_device_picks.md`): widen it, or keep it with its reason. A widening
   must not push a file past CHECKLIST 14 without the same efficiency work. The integration file's per-device
   skips are sites too (the lead's merge check, of 18: arzi 1, dev 4, grkizi 10, klkizi 14, schlafzi 14, wozi 7
   skipped): class every skip; a skip is kept only where that device lacks what the test drives, with its reason.
   Lane CO2 adds one test to bus_hazard's ladder section beside you: leave that section alone.
4. The four bites from cmr1b's item 4, each one failing its guard.
5. matrices.md's device-pick rows completed (no "open" row left in that section). Re-check CMr1c's E.2.1 sentence and
   give the docs pass its final text in your hand-back. Do not edit SPECIFICATION.md.

## Notes
- File edits use the Edit or Write tool. A deletion is its own Bash call. No `git stash`, no nohup.
- Every run goes through your own run wrapper (copy CMr1g's), with RUNS.md lines naming `U35 lane CMr1h`.
- Before each timing pair or heavy twin run, check `uptime` and the process list: never more than 4 heavy processes
  on the host.
- After any src or digital_twin edit, rebuild with `S/u23/rebuild.sh`. `src/` is not changed for test speed.
- Lane N11c tags waits in tests/ beside you. If you change a wait's value, name it in your hand-back.
- Commit subject `U35 lane CMr1h: <summary>`, with the two trailers. Do not push. A refused command stops you.
- Count your tool calls. At 80, commit what is green and hand back at a seam with the sites left.
- Hand-back:
  - commits;
  - per file, the times;
  - the heap attribution with numbers;
  - every site's class;
  - the bites;
  - the E.2.1 text;
  - last line "nothing of mine is running".
