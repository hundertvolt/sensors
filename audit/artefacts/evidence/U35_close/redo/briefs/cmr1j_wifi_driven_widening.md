# CMr1j: a driven clock for the Wi-Fi scenarios, then the widening (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then CMr1i's hand-back `S/u35r/handbacks_redo/CMr1i.md` (items 1-3: the technique, the reach table, the times).
`cmr1_device_picks.md` (the owner rule) when classing. Worktree and base: in your launch message. Logs in
`S/u35/laneC/cmr1j/`; CMr1i's (the patch, the probes) in `S/u35/laneC/cmr1i/`.

## The lead's review of CMr1i (binding)
- 84a9f1e4 is kept: the 18 s is one supervisor check per command after the first, a harness artefact, fixed with
  the supervisor started after release() as main() starts it; the pair shows the gain.
- The widening is required by the owner's rule ("these tests should go for all devices", deduplicated by wiring).
  A slower file is fixed by efficiency, never by keeping a test on one device (owner: "Test duration is to be fixed
  by efficiency, not by cutting strictness"). So the efficiency work comes first, and the widening then lands
  whatever the time; the growth left is a measured residual with its cause, for the owner's report.
- The reach question is the lead's (test-only, adds coverage, no wear; CHECKLIST 1d), decided conservatively
  (agent, 2026-10-27): traffic from the booted task graph running beside the subject counts as reach. The device's
  behaviour during the test (its log, its stamps, its timing) includes it. So clock_jump :372, ntp :442 and
  loop_end's 8 tests are W; a test that touches no wired part after its boot (:304, :816) stays I.

## Items, in order (each committed green on its own, a formal pair where a time changed)
1. The four integration scenarios (DHCP trace, radio re-select, DNS idle rate, hotspot fallback): put asy_wifi_service
   and asy_captive_dns on a driven clock in them (the bus_hazard technique; `_SteppedAsyncio` and `_IDLE_WINDOW_S`
   are where the real waits are). Every assertion and wiring is kept; a bite for each driven wait (a copy whose wait
   never elapses fails). Formal pair on dev and grkizi, base then head, both stages, the load recorded.
2. Apply `cmr1i/item2_widening.patch` on top. Formal pair again (the patch's skip counts: arzi 1, dev 1, grkizi 6,
   klkizi 14, schlafzi 14, wozi 7); the residual against 5a8c6e35's file named with its cause.
3. test_digital_twin_wifi_modes.py `_scenario_plan()`: the same driven clock if its waits allow, then widen to its
   set (arzi, dev, grkizi). Formal pair.
4. loop_end :236's 8 tests: widen to the distinct wirings of what its booted graph reaches, efficiency first where a
   boot dominates. Formal pair.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; per item the bites and the formal pairs (both stages, load); the residuals with causes; the matrices rows
for your sites, ready to paste (CMr1i.md's format); the E.2.1 text if it changed; last line
"nothing of mine is running".
