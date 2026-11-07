
######## SubagentHandback 2026-10-13T16:59:44.000Z
U24 lane T: final hand-back. The record could not go to S/u24/laneT/report.md: this harness refuses .md report files from subagents, so the full record follows the summary below.

SUMMARY (≤30 lines)
1. Commit: 5c4d72a "U24 lane T: derived devices, module-level suites and typed JSON in the host tier" on audit/u24-t (base e75d363). Not pushed. Tree clean, `typings` symlink removed, nothing of mine running, every RUNS.md line of mine closed.
2. Steps (45): applied 32, partly 2 (263, 298), already landed 7 (56, 61, 268, 274, 303, 304, 313), nothing at U24 3 (62, 63, 270), blocked 1 (264). Also applied: OF-113, OF-117, OF-120, A.U24.50 (3).
3. Seen failing first (log names are in S/u24/laneT):
 - devices_with: test_device_tomls::test_devices_with_selects_by_each_tomls_own_instances (ImportError at HEAD).
 - A.U24.51: test_bench_harness_helpers::test_configured_max_connections_…_for_every_device failed with a zz_test_ plant at HEAD; with the same plant after the change, 43 passed.
 - A.U24.66: a scratch copy of test_no_variant_literals with the 21 entries removed is red at HEAD and green after.
 - A.U24.75: test_code_conventions::test_no_pytest_suite_groups_its_tests_in_a_class.
 - A.U24.13: a scratch probe showed the twin `machine` left in sys.modules.
 - A.U24.57: 2 cases. OF-117: 1 case. OF-120: 1 case. A.S0930.20 (1): test_a_service_word_the_command_does_not_offer_fails. A.S0930.20 (6): 3 cases. A.U24.39: 3 build-date cases. A.U24.36/.55 (2): new GET route not smoked, plus 4 non-strict-JSON bodies accepted.
 - Guards, shown to bite instead: A.U24.40 (anchor drop), A.U24.44 (missing file, then a planted provider swap), A.U24.50 (3) keyword floor, section-key check.
 - OF-113: count 0 at HEAD; the bite (hostname dropped) fails at case 0.
4. Red checks:
 - host mypy `scripts/_render_coverage.py:15: Unused "type: ignore" comment`: the base's known red, not edited.
 - test_no_variant_literals::test_every_not_yet_cleaned_entry_still_carries_a_literal: 21 stale entries, lead's.
 - test_import_placement: "_PENDING entries that no longer occur", 15 entries, lead's.
 - test_decision_vocabulary::test_the_allowlist_only_shrinks: _decision_vocab_allowlist.txt:567 is stale, lead's.
5. Facts for the lead:
 - _NOT_YET_CLEANED retire test_no_variant_literals.py:107-126 and :128.
 - _PENDING retire test_import_placement.py:123, 126, 127, 135-141, 147, 153, 191-193.
 - Allow-list: retire _decision_vocab_allowlist.txt:567.
 - Any-baseline / host_typecheck.ini: retire :62-63, :65-66, :68-69, :77-78, :80-81.
 - ANN401: retire pyproject.toml:309 (test_buildgen_twin_wiring.py).
 - Timing on touched files: 255.9 s → 259.7 s (+3.8 s; two new files add 3.2 s), well inside the 1200 s tier.
6. Facts for X:
 - C.8: the host tier selects devices only through _devices.py (DEVICE_NAMES, device_toml(), devices_with(driver)). Fixtures are named "fixture" and no tests_scripts test file names a variant.
 - E.2.2: test_buildgen_pico_gpio.py is the pin-table home.
 - E.2.3: pytest suites are module-level, with no class Test*, checked by test_code_conventions.
 - @tunable: none added. OF-113's `_VALID_CASES = 30` is untagged, like `_CASES`.
7. Runs since resume (all closed): mypy trial ×2 rc1/rc0; mid2 rc0; fuzz arm rc0; fuzz bite rc1 (intended); host mypy real rc1, trial rc1, final rc1 (base red only); after rc0 (35 files green); precommit rc0 (17 files; reds above); final rc0. Earlier: rebuild rc0, host baseline rc1, before rc0, mid1 rc0, twin probe rc0, generated_boot rc0.
8. Incident (earlier, before resume): I ran `pkill -f plant_loop.sh`, which broke the kill-by-pid rule. It matched only my own shell (exit 144); no other process was affected.

FULL RECORD
Steps (U24 part, lane T files):
- 53 M.TSC.029 applied: test_build_firmware.py uses _FIXTURE_DEVICE/_A_DEVICE.
- 54 .037 applied: defaults labels "fixture".
- 55 .040 applied: _system_cmd_problems/_system_cmd_words read _SYSTEM_CMDS by ast, checked per device, with a bite. Deviation: the "no confirmation key" clause is superseded by the owner's 2026-10-01 decision ("The API stays single command."; the page asks before either), pinned by test_every_command_and_the_error_reset_ask_before_they_are_sent.
- 56 M.GEN.005 verified only: in end form at buildgen/codegen.py:430-498. No feed and no gc.collect are emitted; begin_boot() is at :439.
- 58 .050 applied: new test_buildgen_pico_gpio.py; 17 items moved out of test_buildgen_validate.
- 59 .082 applied: the control pair is derived by instance count rather than DEVICE_NAMES[:2] (deviation).
- 60 .084 applied.
- 61 .091 already landed: test_fram_chunk_crc_sites.py:51, bite at :59-70.
- 62 .095 nothing at U24 (the claim holds): the f9 soak collects at tests/test_asy_webserver_service.py:2664,2668 are outside test_gc_collect_sites.py's src/ and buildgen/ scope (:11, :43-57).
- 63 .099 report only (see 5).
- 65 .116 applied: _RELAYED_BOARD_FILES, _lwip_anchors_found, count assertion and drop bite.
- 66 .121 applied.
- 67 .155 applied: _inside_a_while, own_feed_reference_findings.
- 68 .160 applied.
- 263 .004 partly: Any is cleared in definitions, error_catalog, bench_harness_helpers, twin_wiring and generated_boot (typed accessors _str/_obj/_objs/_sections/_groups/_fields, TypeGuard). host mypy is clean with those five sections removed (trial ini).
- 264 .013 blocked: the recursive local TomlDoc raises 1609 host-mypy findings in 5 files, 161 of them in test_buildgen_error_contract.py, which is outside my set. _toml_fixtures.py:11,16 keep Any. The `:37` key is already trigger_s.
- 265 .031 applied: staged_device module fixture over DEVICE_NAMES.
- 266 .038 applied.
- 267 .047 applied: new test_ntp_generated_wiring.py.
- 268 .048 already landed: test_buildgen_generate.py:293-313.
- 269 .054 applied: _on_path() pops only the modules loaded from digital_twin/ (popping all would split stdlib modules; agent decision). The plan proof now goes through configure_wiring(plan read back from JSON) for every device, as run_generic_integration.py:297-299 does. configure_i2c_wiring accepts only two named profiles; its own load path stays covered in tests/test_digital_twin_bus_hazard_concurrency.py:238-295 (deviation).
- 270 .014 nothing at U24: A.U24.13 says conftest.py:18 is unchanged; U27 removes it.
- 271 .021 applied.
- 272 .002 applied.
- 274 .035, 303 .126, 313 .171 already landed: the scanner finds no literal in these files.
- 275, 277, 278, 280, 309, 310, 311, 296, 312 applied: neutral fixtures and derived sets.
- 276 .044 applied (build date must be UTC-aware and within a minute).
- 279 .055 applied (two loops parametrized).
- 295 .079 applied.
- 297 .085 applied: set-claim comments now state the mechanism with no count or name. I made the same fix in 5 more of my files that said "six".
- 298 .086 partly: ROUTES' GET paths are read by ast, JSON is strict (duplicate keys and NaN/Infinity refused), and each device's own section keys are checked. Boot markers in order are not written: boot_phase() writes the watchdog scratch region (src/asy_system_service.py:599-600) and nothing logs a marker, so the twin log has none (probe: probe/twin_dev.log).
- 300 .106 applied.
- 301 .114 applied: 69 class-held test functions became 69 module functions, 261 items before and after, ids 1:1. The file now collects 262 with the new anchor test.
- 304 .130 already landed: test_strip_type_checking.py:30-31 is source text under test.
- 314 .175 applied.
- OF-113: test_buildgen_fuzz.py gains test_a_real_device_rewritten_only_in_order_or_name_builds. It runs 30 cases (device cycled; 1-3 of reverse/shuffle instances, reverse buses, reverse keys, rename), each of which must generate. Arm time 0.63 s on its own.
- OF-117/OF-120/A.U24.50 (3): as in 3.

Other edits:
- _toml_fixtures.py is put in D.15 order (pure reorder, AST-checked) and its docstring now names with_uart_pair.
- Test-file helpers keep the tier's per-section placement, since D.15 is machine-checked only over src/ (agent decision, conservative).
- _devices.py: the docstring does not name scripts/_devices.sh, because that file does not exist; bench_device() is U26's.
- Files outside my set touched: none. Read only: digital_twin/machine.py, run_generic_integration.py, src/asy_system_service.py, buildgen/codegen.py, tests/test_asy_webserver_service.py.

GC stages: n/a. The tier is CPython pytest; every run grepped clean of MemoryError and "memory allocation failed" (mem=0 in every row).

Wall times at nice 19, before → after (s):
- bench_harness 2.3→2.2; build_firmware 17.4→13.3; defaults 0.5→0.4; definitions 6.3→6.6; registry 0.7→0.5; frozen 6.1→5.4; fuzz 10.3→10.2.
- generate 21.2→27.4; graph 1.5→2.2; limits 0.7→0.9; pico_gpio new 1.0; requires 0.9→1.0; tag_comments 0.5→0.5; twin_wiring 1.8→2.2; validate 25.3→23.7; value_wiring 0.8→0.7; web_tag 0.9→1.0; wiring 0.9→1.0.
- code_conventions 3.6→4.5; device_tomls 1.2→1.3; boot_contiguity 15.2→14.3; ceiling 3.0→3.0; errcount 0.7→0.6; soak 0.4→0.5; generated_boot 23.3→23.5; error_catalog 28.1→25.7; import_graph 18.3→18.7.
- tuple_agreement 0.7→0.6; overrides 3.4→2.5; ntp_wiring new 2.2; body_cap 1.6→1.4; timeout_ceiling 2.7→2.6; hw_conftest 0.3→0.3; ticks_wrap 40.3→37.9; watchdog_feed 15.0→19.9.
- Tables: S/u24/laneT/runs/{before,after,precommit,final}.tsv.

Silent-failure scan (my files, all classes):
- No swallowed failure found. Each except either records a failure or is bounded by a timeout (generated_boot :150 poll loop → TimeoutError).
- New vacuity guards: the fuzz arm asserts its count, ntp wiring asserts one call each, the section-key check, the keyword floor.
- Class 3 observation, new, not changed: per-device skips when a property is absent (definitions :238, :327, :480, :716; boot_contiguity :329) would all skip if no device had the property.

