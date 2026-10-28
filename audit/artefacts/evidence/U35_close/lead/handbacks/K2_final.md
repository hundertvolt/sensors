K2 done. Commit 8c033e0 on audit/u35-k2 (worktree S/wt-u35k2, based on bc0d77b): "U35 lane K2: comment blocks fit the 120-character count, no meaning change". It touches exactly the 37 files in k2.txt and has 43 blocks brought to the cap. Nothing pushed; the tree is clean.

Blocks by kind:
- Rewrapped (23, words unchanged). In 7 of them the closing `"""` now sits on its own line, because the prose filled 3 lines. These are scripts/_digital_twin_scenarios.py and six device scripts: bus_concurrency_cross_device_scd30_sgp40, bus_concurrency_isl29125_write_vs_siblings, bus_concurrency_same_device_scd30, isl29125_mechanism_envelope, system_command_reboot, unretrieved_task_exception_handler. Decision (agent, 2026-10-22): I took this over rewording because it keeps every word. Each of these adds 1 line.
- Tightened (12): launch.py:1, _check_gc_collect_sites.py:6, _digital_twin_ci_suite.py:5 and :810, _stage_website.py:10, run_unix_port_integration.sh:95 (the shellcheck directive is left untouched), test.sh:541, test_hotspot_role_reversal.py:407, test_ticks_ms_rollover.py:1, test_system_commands.py:1, heap_bounds.py:4, manual_bus_electrical.py:1. Every actor tag, owner quote and citation is verbatim, and none of these changed a line count.
- Split (3):
  - unix_port_unretrieved_report.py:1: the handler's behaviour and its reason, then how it is installed and how its body mirrors PrintLog.report_unretrieved().
  - _unix_port_udp_addr_shim.py:1: what the shim fixes and refuses, then when it is applied.
  - _port_lock.sh:2: how the lock behaves, then its file layout and the env-var owner chain.
- Moved (4), each sentence verbatim as its own comment in the same file:
  - unix_port_poll_prewarm.py:40: the "Returns the sockaddr..." line now sits above `return addr`.
  - c_stack_budget.py:1: "the top of the deepest chain tests_scripts/test_await_depth.py finds" now sits above the GET /status dispatch.
  - scd30_start_continuous_measurement.py:1: "The driver refuses a value outside 0 or 700..1400 mbar before any send" now sits above the set_ambient_pressure try.
  - record_twin_instrument_runs.py:1: "A failure with no reason given (--reasons) fails the run" now sits above `if problems and not reason:`.
- Split and moved (1): _generate_sensortask_modules.py:10 is now two paragraphs, usage plus callers, then what it writes. The two stamp file names moved beside the final stamp write in main(); the header keeps "then writes the freshness stamps".

Your note about line counts arrived after the commit, so these blocks stand as they are. For your remap, the line shifts are: unretrieved_report +4, _generate_sensortask_modules +4, shim +2, _port_lock.sh +2, and +1 each for prewarm, _digital_twin_scenarios, record_twin_instrument_runs and 8 device scripts (the six above plus c_stack_budget and scd30_start_continuous_measurement). git grep finds no file:line citation into these files outside audit/ and PROJECT_AUDIT_PLAN.md, apart from SPECIFICATION.md:2078 "machine.py:1", which is not this file.

verify.txt: S/u35/laneK/k2/verify.txt ends "CODE-CHANGED FILES: 0" and lists the 9 docstrings whose words changed. No CAPMOVE lines.

Checks (logs in S/u35/laneK/k2/):
- show.py 120 on my files: TOTAL 0.
- verify.py: exit 0.
- measure.py: exit 0; none of my files appear, and no digital_twin/, scripts/ or tests_hardware/ scope shows.
- ruff on the 34 .py files: exit 0. shellcheck 0.11.0 (the venv's copy) on the 3 .sh files: exit 0. bash -n: all three pass.
- Docstring readers, `--help` for _check_gc_collect_sites, _digital_twin_ci_suite and _digital_twin_scenarios: exit 0 each, text intact.
- pytest --collect-only on the 9 changed tests_hardware host files: exit 0, 47/54 collected (7 deselected).
- 12 commit checks: exit 1 (65.8 s). 1 failed: test_tunables_register::test_the_tags_and_the_part_n_rows_agree. Some tags have no SPECIFICATION.md Part N row, and SPEC:11787 has a row with no tag. The tagged files include src/, tests/ and two of mine, but I touched no tag line and no SPEC line, so it waits on D.
- 17 repo-wide scans on 8c033e0: exit 1 (59 s). 6 failed:
  - tunables_register: the same failure as above.
  - level_containment: fault_storm, ntp_unreachable_load, reader_saturation and watchdog_fault have no E.6.6 row. Neither COVERS_TWIN_SCENARIOS nor SPEC changed.
  - task_inventory ×4: untabled tasks at src/asy_uart_link_driver.py:221 and asy_neopixel_driver.py:144/:202. These are src/ files, not mine.
  None of these comes from my diff. K4's commit checks and 17 scans also exited 1 in RUNS.md, at the same time.
- Expected red, not run (your decision that K runs no unit or twin files): tests_scripts/test_twin_record.py, because 13 device scripts and 4 bench/flash files changed their entry hashes. I did not edit twin_record.json.
- Not run: the silent-failure scan. verify.py shows no code path changed.
- RUNS.md: four lines added for my two pytest runs. The pair for the commit checks was written after the run had finished.

Nothing I could not bring under the cap. Nothing uncommitted. nothing of mine is running.
