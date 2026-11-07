# T4r2c: fold (2), fold (1) with its send-buffer knob, the UART load plant (lead, 2026-10-26)
Read `S/u35r/briefs/redo_common.md` first. Base, worktree and branch named at launch; logs in `S/u35/laneT/t4r2c/`.
The third block of T4r2: read `S/u35r/briefs/t4r2_twin_scenarios.md` in full; its item 3's folds (2) and (1), its
item 5 and its "Proof and checks" and "Not yours" sections are your brief, unchanged. Fold (3) and item 4 are merged
(T4r2b, `S/u35r/handbacks_redo/T4r2b.md`, which also states why fold (2) was left red: read its "Left" section).

## Fold (2) first: the premise T4r2b found false
`--fault` MATCH cannot isolate the config snapshot's read: BMP3XX's task start applies the stored config through the
same registers (the fault spent at BOOT_TASKS, "BMP3XX Error setting config data"), ISL29125's `_verify_config` (every
cycle) and `reset()` read the same CONFIG1 burst; SCD30's (0x5403) passed on arzi but was never bitten. Re-check each
on your base. T4r2b's proposal: arm the fault after BOOT_DONE (read the pending count then) and account every read the
fault can meet in the window (the snapshot GETs plus the verify's lines) against that count, so the scenario asserts
the snapshot's `{"error":"unavailable"}` for the read that took the fault, whichever caller it was, and never passes on
a fault spent elsewhere. Its WIP: `S/u35/laneT/t4r2b/fold2_wip_harness.py`. If a driver's snapshot cannot be reached
without a read another caller shares, say so per driver with the source lines: that is the scenario's limit, recorded
in its docstring, never a looser assertion. Each driver's case red on a plant (the snapshot's unavailable marker
dropped in a scratch src copy).

## Then fold (1), then item 5
As the parent brief states; facts in T4r2's and T4r2b's hand-backs (no SO_SNDBUF knob exists in digital_twin/;
`HTTPDropped` is under `/status` networking; `_UART_LOAD_REQUEST_S` is in scripts/_digital_twin_scenarios.py).

## Notes
This container runs as root: fold (3) skips here (its write probe), so a suite run that selects only it exits 1 by the
harness's "nothing passed" rule; select it with another scenario or run under `setpriv` as T4r2b did. The scenario runs
need a private toolchain copy (`cp -a S/tc-int S/tc-t4r2c`, disk check first, keep 3 GB free, deleted after). Lint with
`S/u35/lead/lint_direct.sh` (redo_common.md). Commit each item green on its own; past 80 tool calls hand back the rest
at a seam with its facts. Other lanes share the 4-core host: nice 19, one run at a time.
