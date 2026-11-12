# CMr1f: ntp and bus_hazard made efficient; the idle-poll skip's own test; the formal pairs (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cmr1e_efficiency_rest.md` and `cmr1d_efficiency_rest.md`
(their rulings apply), the parents `cmr1b_device_picks_rest.md` and `cmr1_device_picks.md` (the owner's rule), and the
hand-backs `S/u35r/handbacks_redo/CMr1d.md` and `CMr1e.md`. Worktree `S/wt-u35cmr1b`, branch `audit/u35-cmr1b` at
02506cc5 (clean). Logs in `S/u35/laneC/cmr1f/`; CMr1e's in `S/u35/laneC/cmr1e/` (its probes, until_ntp_skip.log,
skip_bh_m1.log, its run wrapper).

## The lead's review of CMr1e (binding)
- 02506cc5 is kept. The lead checked the cause in the pinned v1.29.0 source. In `extmod/modselect.c`
  poll_set_poll_until_ready_or_timeout(), the POSIX branch (:344-381) sets t = MICROPY_PY_SELECT_IOCTL_CALL_PERIOD_MS
  (1 ms, :58) whenever any pollable is not an fd, whatever the timeout. The branch rp2 compiles (:383-397) polls once
  and returns at timeout 0. The skip stays in the one file where it was measured. Applying it suite-wide, or the C
  override in toolchain/, is a toolchain-level change and is not taken in U35. The lead puts it to the owner in the
  report.
- Owed, test-only with added coverage (the lead's call): a direct test of `_poll_unless_idle`. Cover:
  - dt 0 with only clear flags registered: the real wait is not called;
  - a set flag: it is called;
  - a non-flag stream: it is called;
  - dt > 0: it is called;
  - an empty map at dt 0: say what the real wait would do there, with lines.
  Bite: each case fails a copy with that branch removed.
- `_DrivenWall` is new code in this unit (f2fd7565). With ntp as its second user, it moves to one shared place,
  never a third copy (Part G reuse). Put it in a twin-test helper both files can import, keeping import direction
  sane: a unit-test helper does not start importing digital_twin modules for it. The per-file
  `_driven`/`_driven_modules` idiom stays as ruled.

## Items, in order (each committed green on its own)
1. The `_poll_unless_idle` test.
2. ntp: build the driven-clock lever CMr1e found (main(), the generated module, the responder's and asy_udp_socket's
   sleeps all on one clock). A scenario whose subject is a wait's length keeps that wait. Say what each change keeps
   and what it skips, and give it a bite that fails it.
3. bus_hazard:
   - the SCD30 system-command test's boots, with `start_tasks()`'s stagger (src/asy_system_service.py:778) on the
     driven clock, unless the stagger is the subject;
   - the timed pause, probed;
   - the erase race and the ten FRAM tests: a lever, or the measured residual with its cause.
4. The formal pairs, once mc_cov has its done line: hot_replug, ntp, bus_hazard and clock_jump, base52 then head back
   to back at both stages, under CHECKLIST 12's load (check uptime and the process list before each pair; record both).
   Each file ends within 10 % of base, or with its measured residual and cause.
5. If within budget: cmr1d item 3's sites in ntp (:440/:464/:495) and clock_jump (:275/:314/:336/:354; the lines
   refer to 4cf293d0), classed by measurement and widened or kept with the reason, under the owner's rule. Their
   classes go in your hand-back. Do not edit audit/b3/matrices.md: another lane owns its open row.

## Notes
- Lane N11 tags waits on another branch and leaves your files alone.
- File edits use the Edit or Write tool. A deletion is its own Bash call.
- Every run goes through your own run wrapper in your log dir (copy CMr1e's), with RUNS.md lines naming
  `U35 lane CMr1f`.
- After any src or digital_twin edit, rebuild with `S/u23/rebuild.sh`.
- Commit subject `U35 lane CMr1f: <summary>`, with the two trailers. Do not push. A refused command stops you.
- Count your tool calls; at 80, commit what is green and hand back at a seam.
- Hand-back:
  - commits;
  - per file, the times (base, head, after) and what each change keeps and skips;
  - the bites;
  - any digital_twin/ file changed, with its equivalence evidence;
  - the site classes, if reached;
  - last line "nothing of mine is running".
