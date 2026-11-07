# CMr1d: the widened twin files made efficient; the remaining pick sites; the bites (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cmr1b_device_picks_rest.md` (its parent
`cmr1_device_picks.md` and its owner rule apply), `cmr1c_finish.md`, and the hand-backs
`S/u35r/handbacks_redo/CMr1b.md` and `CMr1c.md`. Worktree `S/wt-u35cmr1b`, branch `audit/u35-cmr1b` at 4cf293d0
(clean). Logs in `S/u35/laneC/cmr1d/`; CMr1c's in `S/u35/laneC/cmr1c/` (times.txt, its scripts).

## The lead's review of CMr1c (binding)
- Two reorders of pre-existing code go back: clock_jump `_set_clock` and neopixel_wifi `_blocked_dir`, which were out
  of D.15 order at base. The D.15 question over the unchecked scopes is with the owner, and until it is answered
  nothing there that was already out of order is reordered. Placing CMr1b's new helpers in order stays. Prove that
  only order changed against 4cf293d0 with an AST comparison of every function.
- The four files over CHECKLIST 14 (bus_hazard +30 %, clock_jump +52 %, ntp +80 %, hot_replug +105 %) are to be made
  efficient. The owner (verbatim): "Test duration going up like this is anyhow something to fix - not cutting back
  strictness, but making it more efficient". Never drop a wiring or an assertion to get there. CMr1c measured the
  causes:
  - clock_jump: 12 boots, 1.7 s of SGP40 init waits each.
  - ntp: about 1.3 s first sync, 3 s SCD30 first measurement and 1.5 s restore cycle per restore.
  - hot_replug: about 2 s of the failure ladder per run.
  - bus_hazard: the SCD30 system-command test 9.4 -> 22.6 s, and the erase race 1.5 -> 6.1 s on dev's chip.
  CMr1c's proposal, DrivenTime for clock_jump's and ntp's boots as hot_replug's already use, is the first thing to
  try. Read how DrivenTime works and what it changes before relying on it. For each file, find where the wall clock
  goes and remove waits that test nothing: a driven clock, an event fired as the timer would fire it, a bound tagged
  per Part N. A scenario whose subject is a wait's length keeps that wait. Say per file what each change keeps and what
  it skips.
- CMr1c's batchB ran under six heavy processes. Measure every time you report under at most CHECKLIST 12's load:
  check `uptime` and the process list before, and run base and head back to back.

## Items
1. The two reorders back (AST-proved), committed alone.
2. The four files made efficient, each at both stages, with base52 and head back to back and the times stated.
   Within 10 % of base, or the measured residual with its cause (e.g. a wiring that adds a real boot).
3. CMr1c's open sites (matrices.md rows marked open): the scd30 helper :54, the sgp40 helper :239, launch :51,
   wifi_modes `_scenario_plan()`, clock_jump :275/:314/:336/:354, ntp :440/:464/:495, loop_end :238,
   run_generic_integration :933/:1031/:1072, the tests_scripts `DEVICE_NAMES[0]` sites, and fram_less_boot and
   `_lag_run`. Each one is classed by measurement and widened, or kept with its reason, under the owner's rule
   (cmr1_device_picks.md). A widening must not raise a file's time past CHECKLIST 14 without the same efficiency work.
4. Item 4's four bites (cmr1b_device_picks_rest.md), each failing its guard.
5. The matrices.md rows completed; the E.2.1 sentence re-checked (CMr1c's text).

## Notes
Commit each item green on its own, subject `U35 lane CMr1d: <summary>`, the two trailers; do not push. Shell rules
(binding): scripts as files you wrote, never `bash -c` holding rm, never nohup chains, never a `tail --pid` or other
chained wait, rm only as its own command with a literal path or "${var:?}", a timed-out run's children killed; a
refused command stops you. Past 80 tool calls, commit what is green and hand back at a seam. Hand-back: commits; per
file the times (base, head, after) and what each change keeps and skips; the sites' classes; the bites; last line
"nothing of mine is running".
