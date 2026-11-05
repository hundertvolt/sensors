P4: does the production-mode bench test run on the frozen image? (lane D2, agent, 2026-11-04; desk check)

Subject: `bench/test_memory_stress_bench.py::test_loop_lag_under_http_load_on_every_route_stays_under_the_smallest_hard_consumer`
(`:148`), which runs `device_scripts/loop_lag_under_combined_load.py` with `mode="production"`. The bench saw
`ImportError: frozen_html` on the mounted dev entry (READING_20261029:103).

## The chain at `17688315`
1. `board.run_isolated()` renders the script (`tests_hardware/harness.py:899-913`): `import _bench_device as device`
   becomes `import sensortask_dev as device` (`harness.py:217-218`, `bench_facts.py:139`), and runs it with
   `mpremote run`: no mount.
2. In production mode the script calls `device.main(watchdog=wdt)` (`loop_lag_under_combined_load.py:36, :96`), the
   generated `main()` (`build/generated_src/sensortask_dev.py:250`).
3. The dev image freezes both modules: `stage_python_modules()` stages `sensortask_dev.py` and `build_stage_dir()`
   writes `frozen_html.py` into the same stage (`scripts/build_firmware.py:94-116`), and the manifest freezes every
   staged `.py` (`render_manifest()`, `:119-121`). The generated module's `import frozen_html`
   (`buildgen/codegen.py:380`; `sensortask_dev.py:8`) therefore resolves from `.frozen`.
4. The bench's failure came from a source mount of the dev entry over an image that had no generated modules; the
   production path mounts nothing.

## Verdict
Met at the desk, on two preconditions round 1 checks before the test:
- the board runs the final dev image (round 1 flashes it first, `round1_sheet.md` item 2);
- the board's filesystem root holds no `.py` of a frozen name: after `mpremote`'s soft reset `sys.path` is
  `['', '.frozen', '/lib']` (`py/runtime.c:147-150`, `ports/rp2/main.c:207-208`, v1.29.0), so the filesystem comes
  before `.frozen`; the boot entry's own `sys.path.insert(0, ".frozen")` does not run in the raw REPL. The standard
  board state ("no scratch files") covers it.
Its first silicon run stays owed (BACKLOG "Loop lag under combined load on the bench").

## Finding beside it (gap G2)
The flash tier's twin of this instrument,
`flash/test_memory_stress.py::test_loop_lag_under_combined_load_stays_under_the_uart_reply_budget` (`:148-152`), calls
`pytest.skip()` on silicon with no gate marker, and its node ID is not in `PERMANENT_SKIPS`
(`scripts/_hardware_verdict.py:34-37`). `_judge_skip()` (`:60-68`) then reads it "unexpected skip" and fails the
verdict, so round 1's flash runner cannot read clean even if everything else passes. Every other plain skip in
`tests_hardware/flash/` sits under a gate marker (`soak_duration`, `neopixel_sweep`, `toolchain_reverify`,
`flash_cycle`). Proposed: keep the test out of the silicon flash selection the way the verdict knows (its node ID
in `PERMANENT_SKIPS` with its reason, or a twin-only marker the verdict treats as expected), one line, lead's choice.
