# Diagnosis unit: the bench's three twin logs from the final 4a (lead, 2026-11-06)

## Read first
`S/u35r/r1/common_r1.md` (binding; labels `dx4a_`). S =
`/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad`. The logs are on the bench branch,
commit `c8887b35`, under `audit/artefacts/evidence/U35_close/redo/hw_round1/logs_final_4a/` (read them with
`git -C S/wt-u35int show c8887b35:<path>`): `scenarios_dev_gc32768.log`, `arzi_gc_threshold_32768_run11_soak.log`,
`arzi_gc_threshold_neg1_run4_bus_fault_persistence_sweep.log`. They were run by the bench host (a Raspberry Pi 4, load
about 8 during the final 4a) on the tree of `b7533307`; the integration tree `S/wt-u35int` (head `8ea29293`) is the
current code. FINDINGS 12.24 (`S/u35r/findings/FINDINGS.md`) is the first item's record so far.

## What to answer (read-only; at most four runs, light ones, or heavy under `S/u35/lead/heavy.lock` one at a time)
1. **`scenarios[dev]` `failed_config_snapshot_is_sent_as_unavailable` at GC 32768:** "SCD30: 1 GET(s) sent the
   marker and the verify took 0 of 2 faults (38.6s)"; it passes alone. The root cause from the log and the scenario's
   code (`scripts/_digital_twin_scenarios.py`): what the check waits for, what the twin did instead, and whether host
   load alone explains it (a timing assumption in the scenario) or the product misbehaves. Reproduce here if you can
   (the scenario under parallel load), and say whether today's tree still carries the cause.
2. **The two arzi feed gaps:** `largest_feed_gap_ms=6795` (run 4 at -1, 11 feeds in about 9 s) and 6290 (run 11's
   soak at 32768), against the 8,000 ms watchdog and the suite's 0.75 near-reset share. Where in the run each gap
   sits (the boot's unfed stretches, a flush, a collection, a stall), from the logs and the suite's own gap report;
   whether the suite flagged them and why the run still passed or failed; and whether the gap is the host's load or
   a property of the firmware that the board would also show.
3. For each: the smallest fix (test, twin or scenario side: say it; `src/`: propose it), or "host load only" with the
   evidence that proves it.

## Never
Never edit any tree; never read `arduino/`; never open `/root/.claude/`. No hardware. Never weaken a check.

## Limits
Write only `S/u35r/r5/DX4A.md` (and scratch under your own `ftmp/`). Budget about 0.7 % of the week. Hand back by 10:00
UTC.

## Hand-back
`S/u35r/r5/DX4A.md`, at most 30 lines, and return its path. Last line: "nothing of mine is running".
