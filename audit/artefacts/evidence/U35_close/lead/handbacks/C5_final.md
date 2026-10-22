C5 hand-back (lane C, last block). One commit, 0174a87 on audit/u35-c, on top of 7442273. Nothing uncommitted, nothing pushed, nothing of mine running. About 33 tool calls.

**Steps (all applied in 0174a87)**
- Fold: `test_the_clock_stays_valid_when_the_sync_goes_stale` is now part of `test_refresh_marks_the_sync_stale_three_intervals_after_the_last_success` in tests/test_asy_ntp_client.py. One 1081-tick drive now does both jobs. Every assertion is kept: the Synced change list, and `ntp_clock_valid()` still True after the stale transition. I kept the test's name because audit/consolidation/M_TEST_UNIT.md cites it.
- buildgen/graph.py: two trailing comments, no code change. The sgp40/notification edge now reads "sgp40 built with ntp.ntp_clock_valid, notification with ntp.cettime". The sysfunct edge (`deps["sysfunct"].add("ntp")`) gains "built with ntp.ntp_issynced". The generated module emits no change.
- D.15 over C's files: tests/test_shared_helpers.py was out of order. C1 put `_fresh_path`/`_clean_path`/`_swept` after `_times`; the file was in order at the base. I moved them into the helper group. It is a pure reorder: the top-level AST nodes are identical (88/88). _cancel_sweep, _ntp_frames, dns, ntp, graph.py and the two src files were already in order.

**Bite and fold times** (logs in S/u35/laneC/c5/b/)
- C4's stale-clock bite (S/u35/laneC/c4/bite_stale_clears, `ntp_clock_valid` returning `ntp_issynced`) still fails only the folded test: 190/191.
- NTP paired times, 0547def base vs head, alternating, two each. Base at -1: 23.76/23.66 s; head: 23.66/23.77 s, no growth. Base at 32768: 24.15/24.19 s; head: 24.33/24.26 s, +0.12 s (+0.5 %). Settrace head: 25.21 s.
- C4's +2.6 s is gone (C4's head was 26.14/26.27 and 26.74/26.76). The small 32768 rest is about the size of the noise between runs.

**Checks** (all rc 0, zero memory markers at -1, 32768 and settrace)
- Pre-commit, over all 16 Python files lane C changed since the base:
  - ruff clean; the 4 mypy passes clean (264/230/52/306 files); eslint, tsc and lint-ceilings pass.
  - The 12 checks plus 29 pure readers (the buildgen tests and graph.py's readers): 3071 passed, 1 failed. The red is test_twin_record `test_every_entrys_hashes_are_the_current_files`, expected.
- MicroPython at -1/32768: dns 47, shared_helpers 43, driven_time 19, udp_socket 65, webserver_connections 24. Settrace: ntp, dns, shared_helpers.
- The 17 repo-wide scans: 877 passed. The one warning is the uninitialised datasheets submodule.
- Readers, each in its own process, all pass: microtest, radio_shape_corpus, digital_twin_scenarios, offline_ntp_config, bench_harness_helpers, twin_never_needs_tests_on_its_path, threshold_runner.
- JS: templates 122/122, definitions-mockdata-coverage 12/12.
- No src/ change in this block, so C4's mpy-cross compare stands. No allow-list row is orphaned (the removed test name occurred only in its own file).
- Silent-failure scan over my three files, all 7 classes and all modes: none found. In `_swept`, catching the AssertionError and returning its text is how the test reports a failure, not a swallowed failure.
- Per mode and device: test and comment changes only, so no effect in STA, AP, Silent, Off or USB, on any device.

**For the lead: D.15 breaks in other lanes' files** (not edited; my checker uses test_code_conventions' own D.15 key)
- tests/test_driven_time.py (F's file): `_sleeper` sits where `_periodic` belongs. Lane C caused this: C1 introduced it in 3700186, and it is still there at 0547def.
- Already out of order at base f3fff0e, so not lane C's doing:
  - Q's files: tests/test_asy_udp_socket.py (`_make_addr`), tests/test_asy_webserver_connections.py (`_port`).
  - U's files: buildgen/codegen.py (class `_Ctx` `src_dir`; module `_lit`), buildgen/definitions.py (`_load_catalog`), tests_scripts/test_buildgen_generate.py (`_runtime_module_names`), tests_scripts/test_buildgen_definitions.py (the `src_dir` fixture).

**Decisions (agent, 2026-10-21)**
- Each NTP check in graph.py is named at the edge that uses it. Writing ntp_issynced on the sgp40/notification edge would be wrong, because neither is built with it.
- I timed the base from a temporary worktree at 0547def, rebuilt with S/u23/rebuild.sh. It has been removed, and the settrace coverage files were deleted.

**Runs**: RUNS.md has start and done lines for precommit.sh (rc 0; the one red is twin_record, expected) and batch pid 5317 (rc 0). Summaries: S/u35/laneC/c5/precommit.out and S/u35/laneC/c5/batch.sum. Relay: no line written. C4's `node_modules` link stays in S/wt-u35c.