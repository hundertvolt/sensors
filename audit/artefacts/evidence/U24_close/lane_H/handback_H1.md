
######## SubagentHandback 2026-10-13T16:42:40.586Z
WIP 2006fed (audit/u24-h on e75d363, 21 files, all in files_H.txt). H1 = 15 changes applied, 0 already landed; steps 50/281/9/253/108/308/109/294/96/289/315/117/302/329 + the verify-only 97/98/283 wait for <API>. I could not write the record file S/u24/laneH/report.md: the harness blocks report .md files from a subagent. This hand-back is the record. Evidence is in S/u24/laneH/{logs,seen_failing,sweep}/.

PUBLISHED AS LANDED:
- microtest: `Skip`, `after_each(fn)`, `run(namespace)`. Tests run in sorted order.
  - A test that returns a value fails with "returned a value - an async def test_* or a stray return; microtest runs synchronous functions only".
  - A `SimulatedRebootError` (looked up on whichever `machine` is loaded) fails only that test, with "reset reached without a catch".
  - Any other BaseException prints "ABORT <name>:", then "P/T passed, F failed, S skipped - aborted at <name>, later tests not run", and exits 1.
  - After each test: "FAIL <name>: left a task parked on the scheduler" (the run queue and stream waits are cancelled and drained by one main-less run_until_complete), then the hooks ("FAIL <name>: teardown: <repr>"), then `sys.path[:]` and `gc.threshold()` are restored and `asy_base_classes._utc_valid` goes back to False. The `_fatal` reset is U30's and is not written.
- `_async_harness`: `run(coro, limit_s=None)`, `run_timed(coro, timeout_s)`, `async cancel(task)`, `async cancel_all(tasks, settle_yields=0)`, `CoroutineOf[T]` (TYPE_CHECKING only).
  - A nested call raises RuntimeError("run() called from inside a coroutine - build the fixture in the test's synchronous scope").
  - Both create_task names are tracked; unfinished tasks are cancelled and awaited.
  - A child that fails during its cancellation is re-raised when the run itself passed.
  - A BaseException that escapes the loop resets `cur_task`, so a later run() can start.
- `_src_const`: `src_consts(path) -> dict` (cached; evaluates every module-level `X = const(...)`, all 791 in src/), `src_const(path, name)` (KeyError "<name> is not a const() in <path>"), `NTP_EPOCH_DELTA`.
- `_strict_json`: `check_strict_json()` now refuses a duplicate key, including escaped spellings; new `strict_loads(body) -> object`.
- `_generated_tree.require_fresh()`: raises RuntimeError("build/generated_src/ is missing or stale - run: uv run scripts/_generate_sensortask_modules.py").
- Generator stamps, both taken before generating and both written last via tmp+rename:
  - `build/generated_src/.inputs_stamp.json` = `{"inputs": {repo-relative path: int mtime}}` over `devices/*.toml` (zz_test_ excluded), `buildgen/*.py`, `buildgen/error_catalog.json` and `src/*.py`.
  - `build/generated_src/definitions/inputs_stamp.json` = `{"tomls": {device stem: sha256 hex of the file bytes}}`.
- Shared doubles:
  - `RaiseOnArm(exc=OSError)` (restores the previous values on exit)
  - `FastAsyncSleep(clock=None)`: patches sleep and sleep_ms; `.slept`, `.of(task)`, `.CAP`=512, `.dropped`
  - `FakeTime(hour, minute)`
  - `DrivenTime(*modules, now=0, strict=False)`, a Ticks30Time
  - `Rp2Gmtime()`
  - `async tick(flag, times=1, clock=None, step_ms=1000)`
  - `make_fram_manager(max_size=0x2000, part=FakeMB85RS64V, *, chip=None, history_length=None) -> (manager, chip)`
  - `make_ntp_reply(unix_seconds)`
  - `FakeNtpServer(port, *, poll_ms, poll_tries)` with `async serve_once(reply|None) -> None` and `close()`
  - `record_prints(pr=None, *, echo=False)`, a context manager with `.lines`, `.kwargs`, `.text()`
  - `FixedRandom(uniform_values=None, *, randint_values=None, getrandbits_values=None, value=None)` with `.calls`
  - `_protocols`: `I2CLike`, `UARTLike`, `WLANLike`, `WriterLike`

DEVIATIONS:
- `OverflowingTime` is not created. Its copies went at U10/U14 (41b47f1, 1cff5a2) and nothing uses it.
- FakeNtpServer's poll budget is passed by the caller, so the tagged values stay where they are and no new @tunable is needed. The bool return stays U35's.
- `record_prints` shadows `asy_print_log.print`, the `_PrintRecorder` group's shape, so it also catches `console()`. It records arguments, not `(level, args)`.
- `cancel_all` gained the `settle_yields` keyword (the NeoPixel copy's trailing yield).

SEEN FAILING FIRST:
- test_microtest_hooks: "no attribute 'after_each'"; the probe path seen by test_c; test_b_finds_it_empty FAIL; the flag-reset plant FAIL.
- test_async_harness: ImportError; with the guard planted out, the child gets "Segmentation fault" (status 35584); with a no-op reap planted, 4 FAILs.
- test_shared_helpers: each of the 11 modules missing (missing_modules.log); skeletons fail 22 of 28; a src_const plant fails 3.
- test_strict_json: "can't import name strict_loads", then `{"a":1,"a":2}` accepted.
- tests_scripts/test_microtest: 4 FAILED (an async test PASSes, no ABORT, the reset traceback, hash order).
- test_generated_tree: 5 FAILED (no module); a planted mtime check fails the touched case.
- The generator stamp test fails (the last renames were index.json and api).
- Guards (passed on the skeleton or plant, so they test nothing new): the fast-sleep restore, every src const evaluates, nested objects keep their own keys.

CHECKS:
- My 4 tests/ files pass at -1, 32768 and settrace (49 tests), with 0 MemoryError.
- test_strict_json: ~0.02 s before and after at every stage. A strict check of a 3.4 KB body costs the same (1373 ms before vs 1286 ms after, for 50 checks).
- tests_scripts: test_microtest 8/8, test_generated_tree 5/5, test_generate_sensortask_modules 8/8, threshold runner 9/9, coverage runner 12/12; the 12 before-commit checks 631 passed.
- ruff clean. Main mypy clean both ways; twin pass clean. The host pass has only the expected `_render_coverage.py:15`.

RED UNTIL WAVE 2 (one -1 sweep of every tests/test_*.py, sweep/summary.tsv): 45 files fail only on "left a task parked", by owner:
- U3: api_response, base_classes, config_manager, system_service, uart_link_driver, digital_twin_uart_link
- U2: ntp_client, webserver_service, wifi_service, neopixel_wifi, ntp_fram_system, ntp_wifi_dns, setter_microdot
- U4: notification_service
- U1: isl29125_driver
- F: digital_twin_machine
- D: 10 twin files, plus the 18 per-device wrappers through D's three scenario libraries

`test_asy_uart_comm.py` is red for a different reason, which needs action on a fake. Sorted order exposes an order dependence: `test_a_delimited_frame_of_the_wrong_length_counts_as_discarded` passes alone and fails after 13 of the 17 earlier tests. It also fails with the base runner changed only to sorted order. Root cause: leaked rp2 DMA channels (`machine._DMA_CHANNELS`). `rp2.DMA.reset_registry()` before it makes it pass. This needs F's reset_test_state to cover them, or U3 to reset them; tests/rp2.py is in no lane's set.

FACTS:
- X: E.2 as published above. E.3: a direct run can now refuse a stale tree (`require_fresh`; the callers come in wave 2). No @tunable added. E.1, E.5, L.5 and A.4 come after API.
- Y: the "Known segfault cause" bullet is not made false at H1, because a raw `asyncio.run()` still crashes. Measured: no parked task is needed. The nested call returns with `cur_task` None (core.py:200), and the outer coroutine's next await segfaults; S/u24/laneH/nested/no_parked.py.
- Lead: rebuild after merging. The new `definitions/inputs_stamp.json` sits in vitest's glob, which J's loader already skips. No Any-baseline, ANN401 or host_typecheck.ini line is retired yet; `_coverage_runner` and `_shared_rest_roundtrip` come after API.
- Lead, new findings:
  - The stamp's input set leaves out `ext/` and the generator script itself.
  - Stamps work in whole seconds, so an edit within the same second goes unseen; the next generation closes this.

RUNS (all exited; RUNS.md closed):
- rebuild 25722, rc 0
- skeleton run 26536, killed by pid: it waited out an unpatched 3600 s sleep, which was expected
- before-commit checks, rc 0
- rebuild, rc 0
- sweep 710, rc 0
- waiters 1691, 2401, 5205 and 8747

Nothing of mine is running.
