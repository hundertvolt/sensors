BR2 hand-back, saved by the lead from the message it sent (2026-10-27). Commits ad1fae73, a4f0ccea, 8cf55c6b, 05a75a80, fb9942a8, 1f5c555b on audit/u35-braise2 (from 651d3e79).

BR2 hand-back (asy_config_manager.py, asy_system_service.py). Worktree S/wt-u35braise2, branch audit/u35-braise2 from 651d3e79. Not pushed, nothing uncommitted (node_modules untracked as before).

Commits: ad1fae73 (D1 gate), a4f0ccea (D2 mempause deadline), 8cf55c6b (D3 boot signature), 05a75a80 (test annotations for mypy, no behaviour change), fb9942a8 (config_manager verdicts), 1f5c555b (system_service verdicts). The last two were redone via `git reset --soft` because my first subjects carried wrong counts; final tree byte-identical.

Rows (before -> after):
- asy_config_manager.py: 1 of 68 groups terminal (const) -> 92 call groups: handled 56, unreachable 36; no defect. 11 transitive groups into asy_print_log (self.pr.*, make_logger, report_if_fatal) left to BR1.
- asy_system_service.py: 1 terminal (+3 ticks rows "inherently safe") of 86 -> 96 call groups: handled 46, unreachable 48, defect 2 (fixed); raise :396 handled. 16 transitive groups into asy_print_log/asy_base_classes (pr.*, make_logger, report_if_fatal, _uptime.read, utc_now, arm_tick_timer, _boot_signature.set/get_value) left to BR1.
- Each JSON has a conventions entry naming the catching except per caller kind (boot entry main.py:38 / codegen.py:867, Microdot ext/microdot.py:1533 + errorhandler :791, _log_dead_task :326, _run_system_cmd asy_webserver_service.py:908).
- e51.md: 84 rows rendered into its block by the walk (36 + 48), one per unreachable group.

Defects (all "a raise leaves lasting state"; each fix small and local, no return contract or API changed):
- D1 _request_shutdown(): _shutdown set before `await self._storage.erase_ready()`. A raise there (at least the MemoryError of its coroutine) wedged the gate for the boot: later commands answered from the stale gate (erasefram "Valid" with nothing run, others "Failed"), every mempause refused. Fix :394-396: except BaseException resets _shutdown and re-raises, so _run_system_cmd still answers Failed and persists it. Test test_a_raising_preflight_leaves_the_gate_as_a_refusal_does, red first at :1589 (_shutdown stayed 8).
- D2 _status_loop() cleared _unpause_at before set_pause(False), which can raise before its store: storage then stayed paused for the boot. Same order in pause_permanent_storage(0) (no production caller; generated callback passes 300; fixed for consistency). Both now clear the deadline after the unpause (:532, :714). Tests ..._keeps_its_deadline_for_the_restarted_loop (red :2699) and ..._immediate_unpause_that_raises_keeps_the_pending_deadline (red :2714).
- D3 _start_time_set was set after pr.one("...boot signature set..."). A raise there let the supervisor's restart draw a second signature, which clients read as a reboot. Flag now set right after set_value() (:538, :544). Test ..._never_lets_the_restarted_loop_draw_a_second_signature, red :2746 (2429757366 then 92846308). Fact owed to BR1: its pr.one() row is D3's trigger.

Checks:
- Green: tests/test_asy_system_service.py 203/203 at -1 and 32768 (27.3->28.5 s and 29.4->30.0 s, under 10% growth); all 22 importer files, 72 jobs incl. PER_DEVICE devices, both stages, 0 memory markers; mypy src tests (shared typings) clean; lint_direct.sh rc 0 (run inside the venv); ruff; raising_walk.py --check; test_citations, test_decision_vocabulary, test_comment_block_cap, test_fatal_report_sites (685 passed).
- RED, waits on lead: `e51_sweep.py --check` since ad1fae73. audit/sweeps/e51_hits.json holds pre-edit asy_system_service.py line numbers (4 lines inserted at :389-396; lines moved at :532/:538/:544/:714): many "no verdict" sites and 1 stale (the E.5.1 row old :454, now :458). Needs a coverage re-dump or remap; not my file.
- RED, waits on lead: `review_rows.py --check` flags "tests/test_asy_system_service.py::test_a_raising_preflight_leaves_the_gate_as_a_refusal_does helper_swallows". The except MemoryError there asserts the propagated raise; needs a row in the register.
- Not run: tests_scripts/test_twin_record.py (expected red on any src change); mpy-cross byte compare (LEAD NOTES 7).

Notes for the lead:
- The walk files lambda bodies (the two Timer callbacks' .set()) under the enclosing try; they run in the scheduler (proved in the rows).
- f.write was marked "transitive" only by a name collision; classified.
- An acceptance-line pr.evt raise answers "Failed" for an accepted command (consistent state, F.2 class, BR1's row).

Decisions (agent, 2026-10-27): D1 uses restore-and-re-raise rather than catch-and-refuse, keeping the persisted errno-14 record with no new catalog code. Modes: D1 and D3 every mode and device; D2 only where FRAM is wired. Owner questions: none.

Runs (all exits as expected): d1_red 1, d1_green 0, d2_red 1, d2_green 0, d3_red 1, d3_green 0, importers 0 (1047 s), d_mypyfix 0, readers 0. RUNS.md lines for all wrapped runs. Logs: S/u35/laneB/br2/.

nothing of mine is running
