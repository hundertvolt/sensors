T4b2 hand-back (lane T, audit/u35-t4 in S/wt-u35t4). Two commits: e2027b6 merges d7e51cc (--no-ff, then rebuild.sh rc 0), and 0d466b6 is item 1 plus a fix in the runner. Nothing is pushed or uncommitted. I stopped at the valve (about 66 tool calls) at a seam: item 2 needs more calls than were left.
[Diff stat against d7e51cc: digital_twin/run_generic_integration.py 7; tests/test_digital_twin_run_generic_integration.py 71.]

**Item 1 (T4b amendment 3): done, with a different end point.**
- The smoke boot's presence-only check (`:838`) is replaced. The run now ends where `WifiService.setup()` returns, so the WIFI store's whole setup is inside the window.
- At that point the store's own layer must hold exactly ErrCount 1 and one entry, E CFG_PATH_IS_DIR, with exactly one printed CFGMGR_WIFI line. The service's own logger is not counted (the per-layer rule).
- Bite: a planted second `err_s` in a scratch `asy_config_manager.py` turns it red at both stages. The old check passes the plant.
- Decision (agent, 2026-10-23): end at the setup's return, not at BOOT_TASKS. Running on to BOOT_TASKS adds the remaining setups: 0.87 s measured, +55 % on the file's time. A snapshot taken at BOOT_TASKS holds the same single entry. CFG_NOT_VALID is logged only after BOOT_TASKS, by a task the boot starts. Whether it falls inside the window depends on timing, so the window ends before it.
- Times: 1.45-1.53 s at -1 and 1.48-1.61 s at 32768, against the old file's 1.46-1.51 / 1.53-1.82 s measured side by side.
- **Found along the way (my file):** in a process with several boots, the runner's `boot phase:` line kept naming the first boot's device (the log showed `[sensortask_idle]` on arzi's boot). It now names the latest boot's device (run_generic_integration.py, `_boot_phase_device`). The new test failed first ("sensortask_idle"). A twin run with one boot per process prints the same lines as before.

**Item 2 (folds (1)-(3), escalation timeout scenario, `_UART_LOAD_REQUEST_S` plant): not started (valve).** Facts for fold (1), `client_gone_mid_response_is_counted`:
- This host's tcp_wmem is 4096/16384/4194304. Linux grows the server's send buffer automatically up to 4 MiB.
- dev's whole frozen site is 154,512 B, so no GET body is larger than the server's buffers. Under the conservative reading the scenario would always skip here; only the 16 KiB starting size is exceeded, and passing on that is timing luck.
- Proposed route for the next block (agent, 2026-10-23): a twin knob that pins each accepted socket's SO_SNDBUF to its floor, which also matches rp2's small fixed lwIP send buffer. Any body above about 10 KB would then be mid-write at the reset, every time. It is a fidelity change, so it needs a test and a decision.

**Items 3-5: not started (order and valve).**
- Item 3 (README): the `boot phase:` text should now say the line names the latest in-process boot's device.
- Item 4 (M.PROC.024 (2)) plan: B2b2's 2**30-period build is at S/u35/laneB/b2/t30, in the ticks30_batch.py form. One dev twin suite run per GC stage, with the wrap placed at Run 11's start offset taken from an existing log. Cost: about 45 min per stage (the last dev twin CI took 2719 s), about 1.5 h in all, plus one call to find the offset.
- Item 5 (dev and arzi twin CI at both stages): not run.

**Checks:** ruff clean. Cold twin mypy pass: 52 files, 0 issues. The 12 checks: 802 passed, 2 expected reds. The 14 run_generic_integration readers: 13 green. test_twin_wiring_contract is red at tests/test_digital_twin_machine.py:121 (N5's `_board_plan` false positive, CM2's item 1, not mine). Expected reds, unchanged: test_decision_vocabulary's orphaned README allow-list row (the lead's to delete), and test_tunables_register at SPECIFICATION.md:12234 (D3's). The integration test file: 44/44 at both stages, zero memory markers.

**Stale in SPECIFICATION.md for D3:** nothing new from this block.
**Effect per mode:** twin and tests only. Nothing changes on silicon in any mode or on any device.
**Runs:** 18 both.sh/readers runs, each with start and done lines in RUNS.md. Logs are in S/u35/laneT/t4b2/logs and S/u35/laneT/t4b2/readers. The plant is in S/u35/laneT/t4b2/plant_dbl (never committed).
**Next block starts** from 0d466b6, clean. Left: item 2 (folds, then the escalation scenario and the UART plant), item 3, item 4, then item 5's twin CI.
nothing of mine is running
