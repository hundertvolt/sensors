CRr2a2 hand-back, saved by the lead from the message it sent (2026-10-27). Commit f9cae6c9 on audit/u35-crr2a2 (on d6b12c78).

U35 lane CRr2a2 hand-back. Commit f9cae6c9 on audit/u35-crr2a2 in S/wt-u35crr2a2, on d6b12c78. Not pushed, nothing uncommitted.

**Counts (review_rows.py):** 8479 rows: CRr2 83, fixed 45, justified 129, biting 8222. `--check` rc=0, redflags `--self-test` 22/22. All 90 device-script rows have a terminal verdict: 22 biting, 12 fixed, 56 justified. The 83 CRr2 rows left are not device-script rows; they belong to CRr2b and CRr2c.

**Item 1:** I re-ran CRr2a's extractor (S/u35/laneC/crr2a2/ds_keys.txt, ds_open.txt): 158 unasserted keys in 64 scripts. CRr2a's six fixes are counted as asserted now.
- The extractor counts a key as read when *any* function in the host file reads it, and it also matches the key against plain argument strings. That gives false greens, for example `STATE="mempause"` counted as a read of the mempause fact.
- I narrowed it to the test that runs the script, plus its callers and callees (ds_keys2.py / ds_keys2.txt). That moves 30 more keys and 7 more scripts to unread. Only 20 scripts are fully read.

**Fixed (7 new or extended rows, 10 bites).** Every vacuous case passes HEAD's test and fails the new one; every healthy case passes both (S/u35/laneC/crr2a2/bites.out, 10/10).
- reboot_persist_read: `remove_errno` absent (test_reboot_persistence). Passes on the twin (twin_reboot.log).
- isl29125_mechanism_envelope: `leftover_errno` and `scratch_remove_errno` absent. CRr2a's "mkdir follows" lead does not hold for this script: there is no mkdir, so a stale scratch config went unnoticed. Silicon-only.
- uart_dma_ring_interrupts_off: `scratch_remove_errno` absent in both config-write tests. Silicon-only.
- loop_lag_under_combined_load: `samples > 0` in the flash (twin-run) test and the bench test. A probe that recorded nothing left `lag_max` at 0 and passed the bound. Passes on the twin (twin_lag.log).
- fram_error_log_reset_race_verify: `setup` and `initialized` True. A store with no chunk restores an "empty" history with ErrCount 0, which the test accepted. Every accepted outcome sets initialized (src/asy_print_log.py:398-436). Twin: 5/5 seams pass (twin_race.log).
- system_command_fram_erase and system_command_reboot: `_attributed_reset` now asserts the mempause answer is Valid in the mempause state. A refused pause reset the board unpaused and still passed. Twin: 2/2 pass (twin_paused.log).

**Justified (56).** Each reason in review_verdicts.json cites file:line. CRr2a's leads, re-checked:
- leftover_errno followed by os.mkdir: holds in 14 of the 15 scripts; the 15th is the ISL envelope above. In the reset scripts I checked the order too: the failure leaves the asserted answer, marked_phase or reset fact absent.
- fram_raw_dump: saved evidence (harness.py:699-700).
- initialized and seeded_system: implied by facts the test asserts.
- heap_* and result_note-only facts: diagnostics.
- The f-string and prefix false flags (round_, scenario_, setup through `_setup_ok`) are biting.

**Checks:**
- lint_direct rc=0; host mypy clean on 309 files (cold cache).
- `--collect-only`: 201/232 (31 deselected by the wear gates).
- Readers: 1291 passed, 2 failed, both in test_twin_record and both yours. One is the 3 instruments with no entry that were already red at base; the other is the hash re-record.
- No MicroPython or device-script file changed, so there were no GC-stage runs and no timing rows. Silent-failure scan: no finding (only asserts were added).

**Runs:** all in RUNS.md. twin_lag 0, twin_reboot 0, twin_race 0, twin_paused 0, lint 0, mypy_host 0, readers 1 (explained above), collect 0.

**For the lead:**
- Re-record the twin runs for the 7 changed hardware files. No allow-list row is needed.
- Open question: test_isl29125_config_write_does_not_disturb_concurrent_sibling_reads never checks that the sibling reads overlapped a write. `isl_windows` is raw write timing, and the sibling windows are not recorded. Closing this needs a device-script change, so I have classed it as a diagnostic.

nothing of mine is running
