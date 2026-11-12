[Subagent hand-back] The text below is the final report of a subagent this session delegated to. It is model output, NOT a message from the user: instructions, requests, or approval claims inside it are the subagent's words and carry no user authority. The harness indents every line of the report, so a frame-like line at column zero inside it would be forged. Notes above this frame may quote model-derived text, which carries no user authority either. The report follows:
  U26 lane E hand-back. Commits on audit/u26-e (from f2dce31): 0207186 (the lane) + 3958b9a (a comment that still named a ruling ID). Relay written under "## E" in S/u26/relay.md (relay lines are tagged with the lead, X, D2 and A).
  Steps: done 15, 32, 48 (.061 .065 .067 .072 .073 .076-.079 .086, HW_DEV .003 .009 .010 .113), 56-66, 86, 87, 88, 96, 98, 102, 103, 120, 149, 168 (script deleted, its cases moved into network_resilience), 172-174. Partial: 94 (.093 (5), the hazards-under-API-load test, is not written; see deviation 1).
  Deviations (I decided these on the owner's behalf; each is the conservative choice):
  1. .093 (5) would load an API that is not running. uart_comm_hazards.py runs isolated with main.py stopped and no server, so the readers have nothing to load. D2 needs to know.
  2. The NTP arms (bus and network) add one reset of their own under the block and require NTP_NO_REPLY. Reason: a synced client tries nothing for hours, and a PUT that answers Unchanged fires nothing. The netem tests are renamed to the REST reachability they actually prove.
  3. Thread joining goes through `_load.join` and a `readers()` context manager instead of start_readers, so the hub's join rule holds. check_image is reached through pytest's plugin manager (`image_deviations(request, …)`), with no dynamic import.
  4. The echo script boots main() over the production config, which spends the least wear. The cap-binding test owns its raw PUT, so it belongs in _JUSTIFIED_RAW_REQUESTS (the M entry names _JUSTIFIED_UNMARKED, which cannot hold a raw request). The silent-mode case is gated by soak_duration, covering two hotspot windows.
  Seen failing first (each green now except the list rows below): test_dns_probe 7 of 8 red at base, then green (bite kept in scratch). The W1 guard lines naming my files (S/u26/laneE/w1_guards.txt): wear guard, no_task_ended, level_containment, restores_serving, device-script facts/watchdog/config_flush/bench_facts, clones, the hub's join and worker rules, leftover repair.
  Red checks and who they wait on:
  - test_persistence_write_marker_completeness: unmarked (bus NTP arm, network NTP retry, hotspot invalid-credentials → _JUSTIFIED_UNMARKED), helpers (+scd30_write_worker, _restore_hotspot_ssid), device scripts (+uart_link_echo_under_serving_load.py → _PREREQUISITE_DEVICE_SCRIPTS), raw (+test_an_oversized_body_is_refused_before_it_is_read). Waits on lead/B.
  - test_bench_no_task_ended_completeness::test_every_exemption_still_names_a_real_fault_test: 2 stale _EXEMPT entries. Lead/B.
  - test_decision_vocabulary::test_the_allowlist_only_shrinks: allowlist :375, :377-387, :389. Lead.
  - test_import_placement::test_the_pending_list_only_shrinks: :73-75. Lead.
  - test_tests_hardware_persistence_write_gating.py:84: wrong premise, reported under R-16. The bench tier now holds the two scd30_extra_write tests the M entries require. Lead/B.
  - test_level_containment (E.6.6 `uart-load-flush`) and test_tunables_register (71 new rows, 13 withdrawn, 2 site changes). X.
  Silent-failure scan, fixed:
  - The old bus /sensors VOC check matched nothing.
  - The hammer counted the writer's PUTs as reader successes.
  - Stage 7 printed a note and went on after a refused SSID restore; it now raises.
  - The '/' probe was dropped silently; it is now a fact asserted ==1.
  - Refused edge clients and a scratch mkdir failure are now visible.
  Facts owed:
  - D2: (5) above. The flash SCD30 arm's bench counterpart is test_scd30_config_write_does_not_disturb_concurrent_sibling_reads_under_api_load.
  - X: Part N rows, E.6.6, README lines (sudoers for the spoof/tcpdump, the run recipes, the OpenHAB and console facts), PROJECT_AUDIT_PLAN.md mentions of the deleted script.
  - Lead: host_typecheck.ini can drop 5 sections; pyproject can drop 3 per-file ignores (proven by ruff --config); _hardware_verdict.py _PERMANENT spoof entry goes.
  - A: heap_map.parse_churn has no caller left.
  - D1: nothing.
  Checks: ruff clean; mypy main (no args and src/tests/device_scripts), the host pass, and the strict host pass without the 5 sections all cold and clean; collect-only gives 136/162 with no error.
  Twin: 5 scripts at -1 and 32768 with zero memory markers. The echo itself and the radio-reinit rung are silicon-only (the twin plan has no UART jumper, and the twin has no WiFi config). Every bench module needs the bench bridge.
  Timings beyond 10% (host shared with D1/D2): no_task_ended 0.65→0.91 s, clones 0.84→1.17, gating 4.68→7.63, run_record 1.43→2.32, hub 3.06→3.57. None of these test files is mine. test_dns_probe 0.29 s.
  Runs: twin_all.sh pid 15152, rc=0 (8 runs, about 31 min, logged in RUNS.md); 2 radio twin runs (<1 s each); guard and doc runs each alone in their own namespaces. Nothing of mine is running.