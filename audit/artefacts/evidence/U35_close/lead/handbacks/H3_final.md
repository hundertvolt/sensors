H3 hand-back (lane H, last block). Commit 7a7d01a on audit/u35-h (on 50e22ab), in S/wt-u35h. Nothing is uncommitted. Nothing of mine is running. I used about 70 tool calls.

Steps by verdict:
- Reader-death thread: applied. In tests_hardware/flash/test_memory_stress.py, a new `_recording()` wraps the load thread and each lag reader. A death goes into the test's failures and names its exception.
- Relay: two lines written under `## D`. One carries H2's two doc facts (README:826-834 stale, SPECIFICATION.md:12629 should name the 90 s bench timeout). One describes the record's new shape and the texts that describe it (digital_twin/README.md:607-611, tests_hardware/README.md:538, HEAP_FRAGMENTATION_MEASUREMENTS.md:282).
- Step 140 with OF-229: partly done. The code and tests are applied. The record is not re-recorded.
  - What changed: the recorder runs every instrument at -1 and at 32768. The flash tier runs once per stage, with the recorder as its pytest plugin (`--record-gc-threshold`); the plugin stages each TwinBoard a fixture yields. A run whose board never took the stage is refused. Each entry's `gc_threshold` becomes `stages {"-1", "32768"}`, and `result` is exception if any stage failed.
  - OF-229: a device script is now charged only with the outcomes of the test functions that reach it, through the module constants, helpers and fixtures they name.
  - The record run took 2059 s for both stages. It exited rc=1 with exactly one unexplained failure, which OF-229 itself unmasked: uart_idle_poll_rate.py, run by test_uart_crossover.py::test_an_idle_listener_polls_at_the_idle_rate_not_the_transaction_rate. It failed at both stages: "a listener outlived comm.clear() and was cancelled (fast, idle, fast, idle): [True, True, True, True]" (test_uart_crossover.py:156).
  - That failure was hidden behind the module-wide charge in every earlier record. U34's module reason does not name it.
  - Root cause not finished. The script (uart_idle_poll_rate.py:73-77) expects uart_listen() to end after comm.clear(). clear() (src/asy_uart_comm.py:1053-1066) only cancels the pending read. So either the twin's cancel path differs from silicon, or the listener keeps listening (a defect or a stale expectation). These are not lane H's files. I gave it no reason, because a reason could hide a defect (agent, 2026-10-21).
  - No failure appeared only at 32768.

Seen failing first, and the bites (nothing planted was committed):
- R1: the old test with a planted RuntimeError in lag-reader-0 passed, with only a thread traceback. R2/R3 (new code, -1 and 32768) and R4 (the final ParamSpec form) fail with "lag-reader-0 died: RuntimeError: planted reader death".
- T1, on the old recorder: the sibling test fails, showing "b.py: run by tests_hardware/flash/test_pair.py: test_a: failure: planted" (b.py charged with test_a's failure). The shape, refusal and plugin tests failed too.

Checks:
- ruff is clean on my 3 files. The host mypy pass is clean on a cold cache.
- The 17 scans: 874 passed, 1 red. test_tunables_register.py fails: l4.memory_stress_bench_loop_lag_script_timeout_s has no Part N row (H2's tag; it waits on D).
- Readers (scenarios, exception_handler_contract, level_containment, memory_error_gate_agreement, persistence gating/marker, twin_record, decision_vocabulary, comment_block_cap, citations): 860 passed, 2 red. Both are in test_twin_record: the hashes test and the stage-shape test. Both stay red until the record is re-recorded, which is expected.
- `pytest --collect-only tests_hardware`: rc 0, 197 of 228 collected.
- Zero MemoryError and zero "memory allocation failed" in every log.
- The datasheets/ submodule is not initialised in the worktree, so citations into it went unchecked.

Silent-failure scan (my 3 files, classes 1-7, the twin's modes):
- Class 3: the stage is detected explicitly; covered.
- Class 4: a test with no case recorded becomes "no case of it ran"; a script no test reaches runs on its own.
- A SystemExit in a thread is dropped by threading itself. No reader raises one, so this is inherently safe.
- New, class 4, not covered: other thread targets still leave only pytest's warning. In lane H's files: test_memory_stress_bench.py soak_reader (:111-124), reset_voc_periodically (:230-240), and the `_lag_load` driver for non-AssertionError (:173-186); test_end_to_end_timing.py `_client` (:92-97). In other lanes' files: bench/_load.py:324, test_boot_order_and_triggers.py:57/:95, test_bus_concurrency_under_api_load.py:93-342, test_heap_under_connection_ceiling.py:70/:140, test_modlwip_send_stall.py:167-168.
- Proposed minimal fix for those (for the lead): tests_hardware/conftest.py (lane Y) makes PytestUnhandledThreadExceptionWarning an error.

Effect: no firmware change. Every mode (STA, AP, Silent, Off, USB) and every device is unaffected. This is host tooling and the twin only, run on the bench device (dev).

Decisions (agent, 2026-10-21):
- The stage reaches the board through a pytest plugin the recorder owns, because the conftest holding the board fixture is lane Y's.
- A script no test reaches statically runs standalone through TwinBoard.
- The uart_idle_poll_rate failure gets no reason until it is root-caused.

Next: root-cause the idle-listener failure (its owner is the lane for src/asy_uart_comm.py and the UART tests). Then run S/u35/laneH/h3/record.sh and commit the record it writes. Its reasons file is S/u35/laneH/h3/reasons.json: 39 entries, with the run-by reasons rewritten per script. Or the lead does this at W6.

Allow-list rows: none needed.

Times: no unit- or twin-tier file changed. The record run took 2059 s for two stages (U34: 1032 s for one). Each loop-lag twin run took 31-32 s.

Runs, all lined in RUNS.md: R1 rc 0, R2-R4 rc 1 (the intended bites), T1 rc 1, T2 rc 1 (expected), scans17 rc 1, record rc 1, readers rc 1, collect rc 0.

Logs: S/u35/laneH/h3/ (R1-R4.log, T1/T2.log, scans17.log, record.log, readers.log, collect.log, mypy_host.log, reasons.json, record.sh, runs.sh, h3_reader.py, attr.py and attr.out).