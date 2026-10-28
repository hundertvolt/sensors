IN+LV hand-back, written by the lane (Wed Oct 28 02:10:51 UTC 2026)

Branch `audit/u35-inlv`, worktree `S/wt-u35inlv`, base 60467ce7. Not pushed. Logs and plant evidence are in `S/u35/laneB/inlv/`.

## Commits (each one green on its own)
1. `49f629e4`: item 1. `levels_walk.py` re-run on the base, the walk's own output only.
2. `c618a62f`: item 2. The bite check made mechanical, in `audit/b3/levels_walk.py` (extended, with no new file).
3. `beeff7a9`: item 3. The six catalog codes. OF-245 closed (the only edit to `audit/sweeps/open_findings.md`).
4. `d2e96297`: item 4. Schema-bound rows, plus the new sweeps and L0 tests.
5. `771786a4`: item 5. Functional and system integration rows, plus two gap tests.
6. `e61eb21f`: item 7. levels.md: the scope header, a reason for every `-`, hand-named cells, the narrowings.
7. `cba18a8c`: item 8. The multi-chunk SET ladder.
8. `3f9c5705`: a comment reworded, no change in meaning. `test_decision_vocabulary.py` read "accepted" as decision vocabulary.

Item 6 (the reverse map) is held for the lead's decision; see below.

## Records: before and after
- **levels.md**
  - Before, at e1ad71f: 137 rows, every one "open: confirm the cells bite".
  - Item 1, at 60467ce7: 138 rows, still all open.
  - Now: 138 rows, 136 closed and 2 open. Each open row is an L3 cell whose only test is a CRr2 row (`tests_hardware/flash/test_memory_stress.py::test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget`): `buildgen/model.py` and the generated-module row.
  - The 690 level cells:
    - 267 bite;
    - 346 `-` with a stated reason;
    - 71 "mentioned only in …" with a reason;
    - 4 `-` on L2 that the booted note and the functional rows cover;
    - 2 open.
  - The two entry-point rows are written:
    - `_main`: L0 111 tests, L1 5, L2 8, L3 2 named by hand (`test_reboot_persistence.py::test_boot_import_mechanism_actually_boots_the_real_system` biting; `test_watchdog_starvation.py::test_watchdog_starvation_triggers_a_real_hardware_reset` is CRr2), L4 2 named by hand (`test_reset_reasons.py`).
    - `_main_noautostart`: L0 56 tests and L1 2. L2, L3 and L4 carry reasons: the hardware tiers flash only the autostart image, and checking the no-autostart one on silicon would cost an extra flash cycle.
- **intent.md**
  - Before: 236 rows, 6 of them "no test" gaps; the schema, None/NaN and integration-layer rows unwritten.
  - Item 1: 237 rows, 0 gaps by reference.
  - Now, all biting:
    - 237 Items rows (28 module rows and 209 catalog-code rows), the six codes carrying their plant evidence;
    - 238 schema-bound rows (218 schema cases and 20 `@limits` cases);
    - 28 functional rows;
    - 32 system rows (11 REST routes, each on every device, and 21 A.2/A.4 features).
  - The header says that combinations of fields are CM3's and recovery paths are conformance.md's (cited, not repeated).

## The reader's no-change proof
The walk now names test functions (comments and docstrings blanked), joins each with review.md's verdict, and follows helpers within the same file. A bare stem counts only where it names the module: an import, or a word inside a string. A stem that another file shares is dropped: the stems of `tests/`'s fakes at L1, and buildgen's generic stems.

The proof:
- On every run, the walk searches every file at the level, not only the files in the old cell.
- It fails unless each new cell's files lie inside the old file-level reference cell.
- That held on the base and on every later head (the log line is "superset: …").

One correction rides along: the "booted on N devices" note now counts devices (6 for asy_base_classes), where it had counted generated modules (12).

## The six codes and OF-245
Each code's naming test is on the head, from F2r's `c56b366b`. A plant at the code's log site, in a private copy put first on MICROPYPATH, fails that test at gc -1 and at 32768, with zero memory markers:
- `src/asy_base_classes.py`, `errno=_ERR_<code>` swapped to `_ERR_CALLBACK`:
  - CFG_SNAPSHOT_RAISED at :497 fails `test_a_raising_pre_write_read_is_logged_as_cfg_snapshot_raised` and `test_set_dict_cfg_old_value_snapshot_read_exception_falls_back_to_default`;
  - CFG_SET_RAISED at :507 fails `test_a_raising_store_write_is_logged_as_cfg_set_raised`;
  - PUSH_RAISED at :535 fails `test_a_raising_push_is_logged_as_push_raised`;
  - RECOVERY_READ_RAISED at :673 fails `test_a_raising_recovery_read_back_is_logged_as_recovery_read_raised`;
  - RECOVERY_WRITE_RAISED at :688 fails `test_a_raising_recovery_write_is_logged_as_recovery_write_raised` and `test_set_dict_cfg_recover_failed_push_correction_write_exception_is_caught`.
- UART_WRONG_KIND: `src/asy_uart_comm.py:909`, `return _ERR_UART_WRONG_KIND` changed to `_ERR_UART_FRAME_INVALID` (the code the listener's fault at :574 logs). It fails `test_an_ack_arriving_at_a_listener_is_logged_as_the_wrong_kind` and `test_an_undefined_command_is_distinguished_from_a_valid_but_unexpected_one`.

Every code has a path that logs it, so nothing is removed. OF-245's row is closed with this evidence.

## Tests added, each seen failing first
- **Schema sweeps.** `tests/_schema_cases.py` (new) derives each declared field's domain edges from the source text. Four new L1 sweeps use it, one `test_a_put_takes_each_declared_field_inside_its_domain_and_refuses_it_outside` in each of the bmp3xx, scd30, sgp40 and isl29125 driver tests. A fifth covers SGP40's compensation read path: `test_a_compensation_sample_inside_its_declared_domain_is_measured_and_one_outside_is_not`.
  - Each sweep lists every case that answered against its domain: refused outside, Valid or Unchanged inside.
  - 22 plants, each breaking one check class:
    - checked_int and checked_float, the min edge, the max edge and the range check removed;
    - set membership removed, and set membership ignored;
    - the special scalar;
    - the minimum and the special together;
    - the bool type check, and the bool branch;
    - None admitted;
    - SGP40's Temp and Hum checks, and its None skip;
    - ContMeas;
    - one bound moved per driver.
  - Every one of the 218 schema rows is reported by a plant of its own class at both stages, with zero markers (`S/u35/laneB/inlv/plants5.json`).
- **L0 `@limits` tests**, red first in a private tree copy:
  - New `test_isl29125_trigger_s_outside_legal_range_rejected` and `test_isl29125_trigger_s_in_legal_range_is_fine`. Removing the tag builds 0, 3601 and -1; moving it to 1..3599 refuses 3600, and to 2..3600 refuses 1.
  - `test_every_limited_field_defaults_inside_its_own_domain`, which stands in for "None", since TOML has no null. A trigger_s default of 0, or an address default of 0x78, fails it.
- **`tests/test_asy_sgp40_driver.py::test_a_backup_period_of_zero_never_triggers_a_backup`**: with the `cfg_values[0] > 0` guard at :287 removed, it fails at both stages.
- **`tests/test_asy_scd30_driver.py::test_each_config_getter_reads_its_own_word_and_the_ambient_pressure_the_set_word`**: with :773 reading another word, it fails at both stages.
- **No new test**: a plant adding `flow=` to `src/asy_uart_driver.py:494` fails `test_valid_construction_on_both_real_uart_ports`, which therefore holds the no-flow-control row.
- **Helper edit**: `tests/_src_const.py`'s `py_value()` also reads an annotated binding. All its users were run at both stages.

## Defects
None in product code. Two findings in the tooling:
- `audit/sweeps/redflags.py`'s `collect()` skips `tests/lwip_host/test_*.py` (two L1 files under E.6.1), so review.md has no rows for them. They sit in no cell, so nothing here depends on them. Owner: the CRr / REC2 records.
- `tests_scripts/test_twin_record.py` has 2 failures: an instrument with no entry, and stale hashes. Both are present on an unmodified copy of 60467ce7 (`base_twin_record.log`), and this lane changes no file they hash. They wait on W10's re-record.

## The reverse map (OR25.a (2)): held for the lead
1204 test functions are reached by no row:

| tier | unreached |
|---|---|
| L0 host | 723 |
| L1 | 270 |
| L3 flash | 59 |
| L0 web | 58 |
| L4 bench | 47 |
| manual | 21 |
| device scripts | 20 |
| L2 | 6 |

They come from 203 files. Top files: `tests/test_asy_uart_comm.py` 62, `tests_scripts/test_digital_twin_ci_suite_errcount.py` 58, `tests/test_fakes.py` 55, `tests_scripts/test_bench_harness_helpers.py` 42, `tests/test_shared_helpers.py` 35, `tests_scripts/test_bench_log_check.py` 30.

That is well over 150, so per the brief nothing was tied. The sample of 20 (seeded random):
- `tests/test_asy_uart_comm.py`: `test_a_non_integer_size_returns_a_sentinel_instead_of_raising`, `test_a_raising_message_callback_does_not_kill_the_listen_loop`
- `tests/test_fakes.py`: `test_a_neopixel_fill_len_and_timing_follow_the_library`
- `tests/test_microtest_hooks.py`: `test_a_test_leaving_tasks_parked_fails_and_the_next_test_finds_the_scheduler_empty`, `test_sys_path_and_the_gc_threshold_are_back_after_each_test_in_either_order`
- `tests/test_untraced.py`: `test_with_a_tracer_set_the_call_runs_untraced_and_the_tracer_comes_back`
- `tests_hardware/bench/test_scd30_frc_readiness_baseline.py`: `test_scd30_frc_readiness_baseline`
- `tests_scripts/test_bench_control_restore.py`: `test_the_source_port_block_is_undone_and_proven_absent`
- `tests_scripts/test_bench_harness_helpers.py`: `test_wait_for_script_server_stops_waiting_for_the_script_when_its_test_ends`
- `tests_scripts/test_bench_log_check.py`: `test_collection_refuses_a_malformed_marker_naming_each_test`
- `tests_scripts/test_decision_vocabulary.py`: `test_decision_vocabulary_names_its_actor_or_is_allow_listed`
- `tests_scripts/test_device_script_bench_facts.py`: `test_the_device_module_comes_only_through_the_rendered_import`
- `tests_scripts/test_digital_twin_ci_suite_ceiling.py`: `test_the_route_set_is_every_get_route_of_the_devices_api_reference`
- `tests_scripts/test_digital_twin_ci_suite_errcount.py`: `test_a_planted_warning_fails_run_1_whose_errcount_is_kept_before_the_reset`
- `tests_scripts/test_firmware_write_sites.py`: `test_the_scan_flags_a_write`
- `tests_scripts/test_readiness_gates.py`: `test_the_flagged_classes_are_the_fram_spi_uart_and_logging_ones`
- `tests_scripts/test_request_timeout_ceiling.py`: `test_the_ceiling_holder_starts_nothing_when_the_script_server_never_answers`
- `tests_scripts/test_suppression_form.py`: `test_every_inline_noqa_states_its_reason`
- `tests_scripts/test_threshold_runner.py`: `test_the_same_file_run_directly_is_the_reactive_default`
- `tests_scripts/test_website_tokens.py`: `test_every_colour_pair_meets_its_contrast_minimum`

**Proposed method (lead's decision):**
1. **Follow helpers across files.** Count a test that uses a name imported from a helper module (`tests/_*.py`, `tests_scripts/_*.py`, `conftest.py` fixtures, `tests_js/_*.js`) whose own code drives the subject. Most of `test_asy_uart_comm.py` drives the module only through `tests/_uart_comm_harness.py`. Because this widens cells, the walk's superset proof would be restated: the old cells must sit inside the new ones, rather than the other way round.
2. **Add matrix rows for the test infrastructure that the tiers themselves test.** These are `tests/`'s fakes and helpers, the `tests_hardware/*.py` harness, the `tests_scripts/_*.py` and `tests_js/_*.js` helpers, `html/`, `devices/*.toml`, `buildgen/error_catalog.json` and the CI suite's runs.
3. **Tie the repo-wide L0 scans to "cross-file invariant" intent rows.** These are the comment cap, citations, decision vocabulary, suppression form, conventions and tokens. Recognise them mechanically: a scan globs a scope root and names no subject.
4. **Tie what remains by hand,** or list each one with its duplicate. Never remove one in-lane. I expect the remainder to fall under about 150.

## Held items and their owners
- The item 6 ties: the lead, given the proposal above.
- levels.md's 2 open L3 cells, and the ladder's L3 cell (`test_uart_crossover.py::test_the_link_keeps_transferring_while_every_other_subsystem_is_busy`): CRr2 (hw_no_log rows).
- review.md has no rows for `tests/lwip_host/`: CRr / REC2.
- The ladder's L2 extension is not owed: `tests/test_digital_twin_uart_link.py:750` already sends a 140-byte, three-chunk SET while the graph runs. UM4's merge is not in this base either way.
- A.U26.87's commit `0c0ad52c` has an empty `src/` diff against its parent.

## Checks on the final head (3f9c5705)
- Every changed test file at both GC stages, with zero memory markers: bmp3xx, scd30, sgp40 and isl29125 driver tests, `test_asy_system_service`, `test_generated_boot_entry`, `test_reset_call_site_invariant`, `test_shared_helpers`. No PER_DEVICE file and no `src/` file changed.
- `review_rows.py` re-rendered, then `--check`: 8612 rows, CRr2 63, fixed 67, justified 129, biting 8353.
- lint_direct: rc=0.
- The six mypy passes: clean.
- `raising_walk --check`, `e51_sweep --check --self-test` and `review_rows --check`: pass.
- The readers (test_citations, test_decision_vocabulary, test_comment_block_cap): 675 passed.
- The whole tests_scripts tier: 7071 passed, 9 skipped and 2 failed, in 8m58s. The 2 failures are the stale `test_twin_record.py` failures above, present on the base too.
- After-times, -1 / 32768:

  | file | -1 now | 32768 now | base |
  |---|---|---|---|
  | scd30 | 22.7 s | 28.8 s | 22.5 / 28.5 |
  | bmp3xx | 13.9 s | 14.0 s | 13.86 (-1) |
  | sgp40 | 8.3 s | 9.4 s | 7.9 (-1) |
  | isl29125 | 2.6 s | 2.9 s | 2.5 (-1) |

  None is slower by more than 10 %. The SCD30 sweep runs under FastAsyncSleep; without it, it took 34 s.

## Decisions (agent, 2026-10-27/28)
- **Stricter bite rule.** A cell counts only test functions; a stem counts only as an import or a word inside a string, and a stem shared with another file is dropped.
- **Sweep criterion.** An in-domain case must answer Valid or Unchanged, not just "not Invalid". The weaker check had passed through a broken store answering "Failed", so all the plants were run again under this one.
- **Crediting.** A row is credited only to a plant of its own check class.
- **Confirmed behaviours.** A confirmed behaviour that lives inside one module is closed at the lowest level that proves it.

## Deviations
- The lead's base timing table (`S/u24/base_times.tsv`) is not in this container. The base times above come from this lane's own runs of the base files.
- The first plant batch was stopped by pid, because its sweeps stopped at the first failure; the collecting version replaced it. RUNS.md records the stop.

nothing of mine is running
