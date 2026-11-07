# T4r2: the smoke boot's exact check, the three folds, the escalation's timeout path, the UART plant (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneT/t4r2/`.
This redoes lane T's work after T4r1 that the container reset lost: T4b2 (0d466b6, lost; hand-back
`S/u35r/recovered/handbacks/T4b2_final.md`) and the never-launched T4b3. Sources, each a map to re-check on your base:
T4b2_final.md; `S/u35/briefs/blocks_t4.md` item 6; `audit/consolidation/M_SCR.md` M.SCR.018's folds (1)-(3) (search
"client_gone_mid_response_is_counted"; their text is the specification); `S/u35/lane_plan.md` LEAD NOTES 106 (a) and 116
(1); `S/u35r/recovered/lead_notes_119_148.md` note 148; `S/u35r/handbacks_redo/F2r.md` line 24; the T3f/T3g facts in
`S/u35/handbacks/T3f_final.md` and `T3g_final.md`. Check each item against your base first: "found landed" is not redone.

## Items
1. T4b2's item 1, redone: the smoke boot's presence-only check in tests/test_digital_twin_run_generic_integration.py
   becomes exact (the run ends at `WifiService.setup()`'s return; the WIFI store's own layer holds exactly ErrCount 1 and
   one entry, E CFG_PATH_IS_DIR, and exactly one printed CFGMGR_WIFI line; the service's own logger not counted). Red on
   a planted second `err_s` in a scratch copy of src/asy_config_manager.py at both stages; the old check passes it.
   T4b2's decision (end at setup's return, not BOOT_TASKS) stands: re-measure its reason (file time) before relying on it.
2. The runner's `boot phase:` line (digital_twin/run_generic_integration.py, near :473) names the FIRST boot's device in
   a multi-boot process: make it name the latest boot's device, test first; digital_twin/README.md's `boot phase:` text
   says so. A one-boot run prints the same lines as before (show it).
3. Folds (1)-(3) as M.SCR.018 specifies, in scripts/_digital_twin_scenarios.py, each seen failing first (a plant in a
   scratch copy of src/ or the runner where the scenario cannot be red on the tree), at both GC stages:
   - (1) `client_gone_mid_response_is_counted`, with the scenario-scoped SO_SNDBUF floor knob decided (agent,
     2026-10-23): off by default, set only by this scenario, pinning each accepted socket's send buffer to its floor (as
     rp2's small fixed lwIP buffer) so the largest GET body is mid-write at the reset on every host; the body's size
     asserted against the pinned buffer first; the scenario skips with its reason only if no body exceeds it. The knob
     is a fidelity change: its own test, and its README row.
   - (2) `failed_config_snapshot_is_sent_as_unavailable`, per sensor driver the device has (`--fault` with a MATCH
     only the config snapshot hits, digital_twin/launch.py's `DEVICE:OP:TIMES:MATCH`).
   - (3) `refused_config_write_is_reported_unpersisted` (the int head has `unpersisted`, src/asy_config_manager.py:329,
     and `/status`'s field: find its REST name in buildgen/codegen.py). This container runs as root, where file modes
     do not bind: the scenario decides by a write probe, not by uid, and skips with its reason when modes do not bind.
     Prove it here once by running it with the twin process stripped of CAP_DAC_OVERRIDE (`setpriv`, T3f's fact) if
     that is clean to wire scenario-scoped; else say so. Modes restored in `finally`.
4. The escalation's timeout path (blocks_t4.md item 6, LEAD NOTES 106 (a)): a deterministic scenario where the
   supervisor's entry is held past `_ESCALATION_ENTRY_WAIT_MS` and never released, so the firmware's own bound cancels
   it: the reset reads the escalation's ResetReason, and the relaunch's busy block is healed and logged. The existing
   `--test-hold-system-entry` knob gains a mode that never releases (the hold counted by the bound); the existing
   release scenario (`reset_errors_while_the_escalation_logs_...`) unchanged. Red first on a plant (e.g. the bound
   removed in a scratch src copy).
5. `_UART_LOAD_REQUEST_S`'s plant proof (LEAD NOTES 116 (1), `85caca5`): a load request reclaimed near the outer cap with
   its reclaim trace held near its bound, red on the old timeout (outer cap plus one hold), green on today's.
6. tests/test_digital_twin_uart_link.py near :193: the frame gets CRC room like the ack beside it (F2r's note).
   No behaviour change on dev (no CRC there): show the test still passes and would pass with a CRC device's sizes.

## Proof and checks
Each changed twin test file at both stages with build-standard directly, zero memory markers. Scenario runs: the suite
with your scenarios selected (`--only`/the harness's own selection), dev and arzi, both stages, inside
`unshare -n S/u24/ns_xdg.sh`, nice 19, RUNS.md lines. Your base has a changed `toolchain/`: any twin CI or
scripts/test.sh run uses a private copy `cp -a S/tc-int S/tc-t4r2` with `PICO_TOOLCHAIN_DIR` (disk check first,
deleted after, say so); never the shared toolchain for those. The full twin CI is W10's, not yours. ruff, the twin and
host mypy passes (stubs at `S/shared/typings`), the comment cap, test_citations, test_decision_vocabulary,
test_tunables_register (a new tunable gets its `# @tunable` tag and Part N row, Basis measured or estimated with the
measurement owed), and every tests_scripts reader of a changed file. Least wear: no added flash-filesystem write in any
scenario beyond what it owns; fold (3)'s write is the thing under test.

## Not yours
src/ (plants only in scratch copies), toolchain/, audit/ records, every allow-list (hand back the row you need); the
twin record (the lead's at W10). A SPEC sentence your change makes stale: hand it back for D3 with its line. Commit
subject `U35 lane T4r2: <summary>`, the two trailers; do not push. Hand-back: commits; per item done / found landed /
left with its reason; each red and green with log paths; the knobs added and their tests; times against the base;
last line "nothing of mine is running".
