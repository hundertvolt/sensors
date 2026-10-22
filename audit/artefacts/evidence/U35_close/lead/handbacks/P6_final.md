U35 P6 hand-back, lane P (its last block), S/wt-u35p. Head 480d4cf, on 596e7ff. Nothing is uncommitted and nothing of mine is running. I used about 60 tool calls.

Verdicts: both of P5's test_microtest reds are fixed. test_microtest: 24 passed.
- asyncio.run(): applied. tests/_async_harness.py gains run_to_interrupt() after run_timed() (D.15 order). It runs the coroutine until a KeyboardInterrupt ends it, then takes the fresh event loop the boot entry's `finally` takes (buildgen/codegen.py:894; core.py:314 drops both queues), and clears cur_task, which the interrupted loop leaves set (core.py:181). The interrupt tests no longer have a local runner or the asyncio.core import. Their three call sites keep every assertion. The module docstring now names both runners; that is its one change of meaning, and the commit says so.
- json.loads: applied. A module helper, _decoded(text: AnyStr), takes :2461 and the eight files.docs sites. The file holds 2 calls again (the helper and the decoder stand-in). The allow-list is untouched.

Decision (agent, 2026-10-22): run_to_interrupt() refuses to nest, using run()'s own check and its _NESTED message. The harness's runners all refuse, and a nested asyncio.run() is the port's known crash. A new test pins the refusal: test_the_interrupt_runner_refuses_to_nest_inside_a_running_loop in tests/test_asy_config_manager.py. Its natural home is tests/test_async_harness.py, but no lane holds that file, so the lead may move the test there.

Seen failing first: the new test failed at :3542 (the refusal assertion) on the helper without the check. Log: p6/seen/nest_unguarded_m1.log.
Bites, all still biting through the moved helper (p6/bites/*.log):
- kbd fails both interrupt tests (:3514, :3525);
- sleep fails :2859 (P4's :2860, one line up after the import was removed);
- nolog fails both failing-close cases at :3316;
- direct (no sibling file, no rename), a fourth bite I added, fails the parked-flush test at :3496.

Runs (each in S/u21/RUNS.md; batch pids 732 and 28586 both exited rc=0; mem=0 everywhere, and no log holds either memory marker):
- test_asy_config_manager: 246/246 at both stages, 0.14/0.20 s (base 0.18/0.31). test_async_harness: 17/17, 0.06/0.07 s. Neither file is slower.
- All 73 direct harness readers at both stages: green. Plus test_sensortask and test_digital_twin_construction per device, and twin sensortask_integration and timer_pool per device: green apart from the red below.
- My batch 1 ran the two PER_DEVICE twin files without TEST_DEVICE, which raised at import (my error). Batch 2 re-ran them per device at both stages: all green.
- The twin integration logs hold 10 Tracebacks each. They come from the injected "status fault" in the supervisor tests, which pass; that is expected output.
- Static checks: ruff clean; mypy main (no args, and src tests device_scripts) and the twin pass clean.
- tests_scripts: the readers (46 files, one process) 2308 passed, 6 skipped; the 12 commit checks and the 17 scans each have 1 red.

Red checks:
- test_tunables_register on config.flush_slice_bytes (src/asy_config_manager.py:71). Known; it waits on D's Part N row.
- test_sensortask 90/91 on all six devices at both stages, at tests/_sensortask_scenarios.py:939 (lane V's _DirWrites). Known.

Scan: nothing new. The refusal raises, the interrupt is the returned bool and all three sites assert it, other exceptions propagate, and leftover tasks hit microtest's after-each parked check.
Effect: test code only. Nothing changes on any device or in STA, AP, Silent, Off or USB.
Facts owed: none beyond the test's placement above. No allow-list row is orphaned.

Logs: S/u35/laneP/p6/ (batch.tsv, batch2.tsv, readers.log, scans17.log, logs/, seen/, bites/).