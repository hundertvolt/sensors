# CMr1k: the clock and NTP widenings, the driver-only sites, the last sites, the bites (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; its "Efficiency" section is binding and says how you hand back),
then `S/u35r/briefs/cmr1j_wifi_driven_widening.md`'s "lead's review" (binding here too: the efficiency-first rule
and the reach ruling), then CMr1i's hand-back `S/u35r/handbacks_redo/CMr1i.md` items 3-5. `cmr1b_device_picks_rest.md`
item 4 for the bites. Worktree and base: in your launch message. Logs in `S/u35/laneC/cmr1k/`.

## Items, in order (each committed green on its own, a formal pair where a time changed)
1. clock_jump :328, :350, :372 and ntp :442, :456 and the :506 test (lines at 5a8c6e35; re-locate): widen each to
   the distinct wirings of what it reaches (the booted graph's traffic counts). Efficiency first where a boot or a
   real wait dominates (the bus_hazard technique, CMr1i item 1). Formal pair per file.
2. test_digital_twin_scd30.py:54 `_reader_on_the_twin_bus()` (set arzi, dev) and test_digital_twin_sgp40.py:239
   `_sgp40_bus()` (set arzi, dev, wozi): each caller loops over its set with a per-iteration
   `machine.reset_peripherals()`. Formal pair per file.
3. test_digital_twin_launch.py:51 `device_with("bmp3xx")`: measure its reach on its main() runs (CMr1i's probe), class
   it, widen if W. digital_twin/run_generic_integration.py (CMr1c's :933/:1031/:1072; re-locate): class each, widen
   a W one (digital_twin/ is yours for these sites only).
4. The four bites from cmr1b's item 4: network_neopixel, neopixel_wifi, fram_less_boot, `_lag_run`.
4b. The boot link (lead, CHECKLIST 1d, test-only): tests/test_digital_twin_ntp.py's `_booted()` captures the previous
   boot's webserver in `earlier`, which with a stale asyncio `child_last` keeps every earlier boot alive (147,424 B
   per re-boot; `S/u35r/handbacks_redo/HP1.md` item 2). Hold its `id()` instead, keep the comparison; grep the twin
   tests for any other boot-to-boot link and cut it the same way. Show the per-re-boot step at 0 at both stages.
5. matrices.md's device-pick rows: CMr1i's ready rows, yours, and lane CMr1j's (its hand-back, if it has landed on
   your base; else name the rows still to paste). No "open" row is left that you can close.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
Commits; per site its class with the measured reason; the bites; the formal pairs (both stages, load); the residuals
with causes; the matrices rows written or still to paste; last line "nothing of mine is running".
