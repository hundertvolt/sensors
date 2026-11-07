CO1 hand-back, saved by the lead from the message it sent (2026-10-27). Commits 1aed8126, c1b55e87, 2e6ea0cd on audit/u35-conf.

CO1 hand-back (lane CO1, branch audit/u35-conf, worktree S/wt-u35conf). I stopped at a seam after the U10 table, at about 76 tool calls. Nothing is pushed and nothing is uncommitted (node_modules was already untracked before I started).

Commits:
- 1aed8126: walk re-run alone on 36bee227. Only the stamp moves. Rows stay 120 rung, 6 owner, 236 queue cells, 11 queue rows. Every H row the queue names is present in C.md.
- c1b55e87: race defect fixed in src/asy_i2c_driver.py, with its test and the SPEC bus-recovery bullet.
- 2e6ea0cd: U10's L1/L2 cells and proofs. The walk now carries a REVIEWED table keyed by (unit, fault path, rung), so a re-walk reproduces the cells.

Cells by table, before → after:
- U10, 23 rows:
  - L1 named: 3 → 21. The 3 cited a file that doesn't exist (tests/test_system_service.py); the real file is test_asy_system_service.py.
  - L2 named: 3 → 17.
  - Bounded / once / race-free complete: 0 → 17. In 4 more only race-free is open; 2 rows are still open.
  - Every cited file::test is biting or justified in review.md (script check). Two are justified: test_a_command_accepted_while_the_escalation_logs_keeps_its_own_reset and test_after_the_takeover_no_other_site_feeds.
- U13 (21 rows), U15 (33), U16 (21), U17 (6), U18 (16): not started, still as the record had them.

U10 cells still open (each row says so):
- the `_init_*()` participant rung: per driver, points to the U15 rows;
- `_init_*()` R3/R4: L2 and race-free;
- Timer arm R1: race-free;
- Timer arm R6: L2;
- deferred flush R1: L2 and race-free;
- FRAM verify_present: the record says it has no product caller, but src/asy_fram_manager.py:152 now calls it (chip-loss path), so the row needs re-triage against the U16 rows.

Test added: tests/test_asy_base_classes.py::test_a_bus_rung_parked_behind_a_sibling_session_is_spent_for_every_reader_on_the_bus.
- How it forces the interleaving: a sibling session holds the bus lock as the gate, with bounded condition waits and no sleep counts.
- Red on the base at its final assertion (:1493): entries ['clear', 'clear', 'recover'], 3 recoveries (S/u35/laneB/co1/red_race_base3.log). Green after the fix.
- review.md has no row for it yet (the render wasn't refreshed; `review_rows.py --check` counts it, 8534 rows). Its red on the base is its bite.

Defect:
- Site: I2C.clear()/recover() stepped `recoveries` only after the lock wait and the clear. A second reader whose rung came while the first was still queued saw no change and ran the same rung again: two clears and two BUS_RECOVERY warnings for one episode, and the first reader then skipped its controller rung.
- Fix: step `recoveries` on entry, before the lock wait. No API, wire or contract change.
- Side effect: a rung cancelled during its lock wait now counts as run, so the controller rung stays the episode's next step.
- No mpy-cross byte compare: this is a behaviour change, so the bytes differ by design.

Checks on c1b55e87 and 2e6ea0cd:
- All 22 importer test files (test_sensortask.py on all six devices), 54 jobs: rc 0 at gc -1 and 32768, zero memory markers.
- lint_direct, main and twin mypy passes, `review_rows.py --check`, and test_citations / decision_vocabulary / comment_block_cap (666 passed): all clean.
- 16 src-reading tests_scripts files: 408 passed, 2 failed, both in test_twin_record. Expected: one lists instruments with no recorded twin run (listener_close_leaves_the_pcb_pools.py, reset_code_loop_end.py, test_modlwip_listener_close.py, not files I touched), the other stale runner hashes. twin_record.json left untouched.

queue_c.md rows added: none (stamp only).

After-times for the file I grew, test_asy_base_classes.py: 0.52 s at -1, 0.61 s at 32768. Not compared with the base table.

Questions for the owner:
1. `_init_failed()` resets a reader's episode mark to the current `recoveries`. So two readers whose setups fail together each rebuild the controller, even while one rebuild is still parked on the lock. Is that intended (one rebuild per failed setup), or should a parked rebuild also count for the second reader? This blocks the race-free cell of `_init_*()` R3/R4. My recommendation: count it, the same as the fixed `_climb_ladder` path.
2. Is it acceptable that a bus rung cancelled while waiting for the lock counts as run (the fix's side effect)? My recommendation: accept it, since the controller rung still follows.

Gap in a CMr1g file: the L2 test for a reader's setup failure into `_init_failed()` naturally belongs in tests/test_digital_twin_bus_hazard_concurrency.py (its ladder section). I didn't write it.

Next block starts at U10's open cells, then U13, U15, U16, U17, U18.

Runs (all exited; logs in S/u35/laneB/co1/):
- co1_readers0 rc 0
- fix1_importers rc 0, 1175 s
- fix1_checks rc 0
- fix1_readers rc 0
- fix1_srcreaders rc 1 (test_twin_record only)
- co1_u10_readers rc 0
- plus three direct red runs of test_asy_base_classes.py on the base

nothing of mine is running
