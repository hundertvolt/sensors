D2 hand-back (lane D's last block; branch audit/u32-d, worktree S/wt-u32d; nothing pushed, nothing uncommitted, nothing of mine running).
Commits: 9a275f0 merges the wave-1 integration 0c52fb0 with --no-ff (message reworded to the lane subject plus the two trailers). Rebuild rc 0 (arzi dev grkizi klkizi schlafzi wozi). f0166f8 holds the D2 step group in one commit, SPECIFICATION.md only.
Steps:
- 14 applied as R-10's one clause: A.7's collector paragraph names `_collect_task_names()`, the `<logger name>.<starter name>` form, and that `start_tasks()` requires the names. The rest of the rewrite stays U36's.
- 15 applied: F.1's opening points to README.md, "Moving a legacy unit to this firmware".
- R-11 applied: A.8 gives `LastTaskEnd`'s meaning, quoting the owner's 2026-09-30 answer "(a) Yes: publish it as `LastTaskEnd` in `/status`." with the question "Keep showing which task ended last on the API?" (source PROJECT_AUDIT_PLAN.md:526). H.5's format list gains `lasttaskend`. H.5.1's Status list gains the System Status row "Task Last Ended", in the group where legacy showed "Task last error" (legacy systemledconfig.html:149-157). J.6 gains a paragraph on the dropped-frame wording of the listen and the three waits; checked against asy_uart_comm.py:571, :707, :753 and :1015. Errnos 22 and 81 unchanged; it cites changelog rows B78 and B85.
- Relay lines "for D2", all applied:
  - C.9's Shutdown and Reset cells now name `_shutdown_sequence()` and `_reset_when_due()` (asy_system_service.py:398-408, :470-478). C.9's intro now points to the rule and to test_task_tops.py.
  - G.2's mirror list gains the FIELD_FORMATS / `_FORMATS` / `_FIELD_FORMATS` pin.
  - A.7 :747 and the dependency graph now read `SgpBackup(fram, _clock_was_set)`.
  - L.2 lists `_clock_was_set()` and the task names.
  - G.2 gains a "Task top" entry: `create_task()` targets and `start_server()` callbacks (with `_serve()`, no L1 lines cited), the owner's 2026-10-21 words, the question marked paraphrase, the two inherent caveats.
  - F.1's "nothing at 0" paragraph records the level-0 answer, quoting the words and the question.
- Checks 13 and 40 are landed: build_firmware.py:206 has `--device-toml`; legacy/ has an empty diff from 72b1281.
Decisions (agent, 2026-10-21): (a) the rule in G.2 as a catalog entry, with pointers from C.9 and F.1; (b) two more stale facts fixed: I.4's SystemService boot list (task names built once; the task-end record allocates nothing) and the second `ntp.ntp_issynced` in A.7's dependency graph; (c) the Reset row's "RAM ring" -> "RAM log"; (d) one commit, one file, one step group.
Seen failing / bites: none (doc only). Effect per mode: none.
Checks: the 12 doc checks plus the SPEC readers (lock_order, memory_catalog, task_inventory, threat_model_statement, timing_budget, toml_schema_contract, level_containment, task_tops): 893 passed in 1m26s. The 17 scans on f0166f8: 873 passed in 69s. One warning each: datasheets/ submodule not initialised (test_citations.py:236). Whole tests_scripts tier: 6674 passed, 9 skipped, 1 failed (test_twin_record, expected), 0 memory markers. Skips: 6 opt-in slow firmware builds (test_build_firmware.py:709), 3 html-validate (no node_modules).
Silent-failure scan over the new text by mode: none found; a top whose logging call fails is the owner's accepted caveat.
Relay lines written: none. Times: no test file grown. Logs in S/u32/laneD/ (merge_w1.log, rebuild_d2.log, precommit_d2.log, repo_scans_d2.log, tier_d2/). Edit script S/u32/laneD/tools/d2_edits.py. RUNS.md: tier lines carry tier.sh's "U29 lead" label, a note names them as D2's.
Open for the lead: after L1 merges, check that G.2's "Task top" entry and C.9's Per-connection row still match `_serve()`'s top.
