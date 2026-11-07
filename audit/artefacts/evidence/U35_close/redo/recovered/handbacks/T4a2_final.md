T4a2 hand-back (lane T, audit/u35-t4 in S/wt-u35t4, from c3d1ce6). Two commits, e1f6c5f and 2d0d34b. Nothing uncommitted, nothing pushed. I stopped at the valve (about 85 tool calls).

**Item 1, the Run 13 red: root-caused and fixed. The cause was in the twin, in my file; T4a's diff is not involved.**
- **Reproduced.** I replayed the archived cell (state_archive/13_before_run13_erasefram, the suite's own launch command, then PUT erasefram) at -1. It went red 9 times in 50 runs on c3d1ce6, every red with the PUT at least 4.1 s after spawn. On 33d9ad8 it went red 1 time in 20, at the same line. Driver: S/u35/laneT/t4a2/replay13e.py; evidence in t4a2/evidence/.
- **Why the watchdog starved.** I added a traceback print in a scratch copy. It shows a MemoryError "allocating 19568 bytes" in digital_twin/_fram_chip.py `_count_write`, raised inside the product's erase (asy_fram_manager.py:790 → the SPI write).
  - The twin's `writes_at` dict gains one key per 256-byte erase unit. Its rehash from 919 to 1223 slots needs 19,568 contiguous bytes (py/map.c:131-148, v1.29.0).
  - At -1 the red's heap had 867 KB free, but its largest free block was only 8.4 KB. In the 32768 run the largest block was 400 KB.
  - The shutdown sequence's catch-all (src/asy_system_service.py:481-484) ends the sequence there. The last feed came about 2 s after the PUT, and the would-trigger about 8 s later.
- **Why no reset followed.** The twin's watchdog only records (digital_twin/machine.py:1509-1537), and the runner's would-trigger hook only prints (run_generic_integration.py:489-491). So the process hung until wait_exit's SIGKILL at 16 s. Without a simulated reset no mem_backup file is written (:1178-1183), so the next boot reads a power-on (machine.py:849-852): ResetReason 1. On silicon the watchdog would have reset the board with record 9; a SIGINT'd red replay shows 9 in r0.
- **Fix (e1f6c5f).** `writes_at`'s table is now sized for its 2048-key cap when the chip is built (`dict.fromkeys(bytes(2048))`, then a del; py/objdict.c:288-296, map.c:281-290). A sentence in digital_twin/README.md says so.
  - The new test `test_counting_writes_at_new_addresses_allocates_nothing` counts 2048 new addresses with the heap locked. It failed first at both stages (test_digital_twin_fram.py:870, "after 0 new addresses").
- **After the fix.** Replay in the same window: 0 red in 30. Every run exited 3 within 7.0 s, with no would-trigger and zero memory markers at stored DebugLevel 1. test_digital_twin_fram 55/55, bus_hazard_concurrency 22/22, sensortask_integration on dev and wozi: all green at both stages. Boot contiguity: 36 passed. The full dev twin CI was not re-run; T4b's item 2 run covers it.

**Finding for the lead (src/, not mine).** This MemoryError was invisible to every memory gate. The shutdown's catch-all logs through the level-gated `err_s` (src/asy_system_service.py:484), and at the stored DebugLevel 0 that prints nothing; the red log carries no marker. The erase's own memory arm uses the ungated `console()` for exactly this reason (asy_fram_manager.py:785). Proposal: an ungated `console()` line for a MemoryError there, or have the suite read the errcount entry. More generally, any caught MemoryError logged by `err_s` in a level-0 twin run is invisible to the gates, because the gates read printed text only.

**Item 2 (T4b's two small items)**
- Item 4 done (2d0d34b): `:507` now runs through `untraced()`. Seen first: the file's `.incomplete` note ("tracing ended … run_generic_integration.py:702"). After: no note, and 43/43 under settrace, -1 and 32768. The test and its assertions are unchanged.
- Item 3 left. An exactly-one check at `:837` needs the run window to extend past the WIFI store's setup. `_until_a_line_from` (`:810-815`) stops at the first CFGMGR_WIFI line, so a second entry after an await would fall outside the window. Next block: end the run at BOOT_TASKS, then count, then plant a doubled entry. My edit was drafted, reverted and never committed.

**Item 3 (T4a's items 3, 6 and 9): not started (valve).**

**Expected reds, unchanged:** test_decision_vocabulary's orphaned README allow-list row (the lead's), and test_tunables_register at SPECIFICATION.md:12234-12236 (D3's). Nothing new is stale in SPECIFICATION.md.

**Checks:** ruff clean. Cold twin mypy pass: 52 files, 0 issues. The 12 checks: 802 passed, apart from the two reds above.

**Times:** test_digital_twin_fram: 0.70 s at -1 and 0.77-0.87 s at 32768, against T4a's 0.56/0.68 (the change itself about 8 ms; load spread 0.55-0.69 s). test_digital_twin_run_generic_integration: 1.38/1.50 s, against the base 1.32/1.41 s.

**Effect per mode:** twin and test only; nothing changes on silicon.

**Runs:** Replays: 3/20 and 1/10 red on c3d1ce6; 5/20 red with the traceback print; 1/20 red on 33d9ad8; 0/30 after the fix. checks.sh rc 0; the two coverage runs rc 0. The /dev/shm scratch trees are removed.
nothing of mine is running
