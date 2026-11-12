# CMr1b: the remaining pick sites, the three per-device defects, deduplication by identical wiring (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` first, then `S/u35r/briefs/cmr1_device_picks.md` (your task: its owner rule,
items, "Proof and checks", "Not yours" and shell sections apply) and CMr1's hand-back `S/u35r/handbacks_redo/CMr1.md`.
Base, worktree and branch named at launch; logs in `S/u35/laneC/cmr1b/`. CMr1's `devices_with()` and the wiring
scanner fixes are in your base.

## Items
1. The sites CMr1 left (its "Not done" list): bus_hazard's `_FRAM_DEVICE` (10 tests) and its sgp40/scd30 picks; fram;
   clock_jump; ntp; the scd30 and sgp40 helpers; hot_replug; launch; tests/test_digital_twin_wifi_modes.py; and the
   tests_scripts `DEVICE_NAMES[0]` sites CMr1 did not reclassify (scenarios and the rest). Each classed by measurement
   (what differs between devices, CMr1's measure.txt is a start) and widened or kept with its reason, as the parent
   brief's item 1 says.
2. The three per-device defects CM found (parent brief item 2), each shown first as the failure it causes, then fixed:
   an iteration inheriting the previous board; a port band overrun (reuse ports per word first; a widening without
   overlap, test_port_bands green, named in your hand-back); a neighbour chip's timer parking a task on a shared bus.
3. Efficiency without cutting strictness (CHECKLIST 14; the owner: "Test duration going up like this is anyhow something
   to fix - not cutting back strictness, but making it more efficient"). CMr1 measured the twin integration file's
   non-arzi jobs about +30 % and network_neopixel +12-14 %. The owner's matrix-deduplication rule (verbatim in the
   parent brief) allows one run for devices whose relevant configuration is identical: grkizi, klkizi and schlafzi
   have identical plans. Implement deduplication structurally: for each driver-specific scenario, group the devices by
   the part of their generated wiring plan (and TOML settings) that scenario reads, and run it once per distinct group,
   the group key computed at run time, never a list of names; a device that differs in any read key runs on its own.
   A test pins the grouping (two devices whose plans differ in a read key never share a run; identical ones do). Measure
   base and head back to back; state the result against CHECKLIST 14.
4. The bites CMr1 owed: network_neopixel, neopixel_wifi, fram_less_boot and `_lag_run`, each a scratch copy of one
   device's wiring regenerated, caught only by the widened test.
5. audit/b3/matrices.md: one row per pick site (file:line, class, measured reason, device set).
6. SPECIFICATION.md E.2.1's sentence (CMr1's D3 sentence, updated for item 3): hand it back for D3r.

Commit each item green on its own; past 80 tool calls hand back the rest at a seam with the remaining list. Commit
subject `U35 lane CMr1b: <summary>`, the two trailers; do not push. Last line "nothing of mine is running".
