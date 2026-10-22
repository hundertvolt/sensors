
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

######## SubagentHandback 2026-10-13T17:59:33.720Z
U24 lane H, final hand-back. Commits on audit/u24-h, not pushed: H1 2006fed, merge of api1 1e880da (same tree as 876bc9e), final 639a6e4. The lead said this hand-back is the record, so no report.md was written.
Steps (30): 26 applied, 1 partly, 3 verify-only and already landed.
- Partly: 99 — only H's members .002/.043/.044.
- Already landed: 97 at buildgen/generate.py:71 and :131; 98 at scripts/build_firmware.py:93; 283 at tests/_error_codes.py:24. All three are the U24 parts in end form; the U26/U27 parts are not due at U24.
- Lead items 0-2 are done.
Item 0, why H1 said "ruff clean": I ran ruff before reworking WLANLike into overloads for mypy. After the rework I re-ran only mypy and pytest, so the claim did not cover the committed tree. Fixed with `# noqa: FBT001` citing network.WLAN.active()'s positional bool. ruff now passes over all eight scopes after the last edit.
Coordinator item (coverage prefix): a traced run of tests/test_neopixel_wifi_integration.py records 0 `build/generated_src/` lines before (26 files, 2666 lines) and 99 after, all in sensortask_arzi.py (27 files, 2765 lines). rc=1 both times, from the F reds. The prefix sits at tests/_coverage_runner.py:22.
Seen failing first (each case passed, or was missing, before its change):
- item 1: an edit to the generator script was still FRESH.
- item 2: a TOML edit inside the generation's own second was still FRESH.
- the 8 planted scan cases (50/302/329); the 5 planted mirrors (281).
- 9/253: EACCES on rmdir was swallowed, and a second TmpScratch with the same key was accepted.
- 108/109: a file with no trailer exited 0; `sys.exit("x")` raised in int(); a raising file left no dump; a generated module had no table.
- 96: a planted alias reset and a generated WDT passed. 289: the missing file, a raising stub main(), the KeyboardInterrupt record.
- 117: the json.loads scan flagged _shared_rest_roundtrip.
- My own checks also caught two bugs before commit: the scan's parse cache was keyed on path, so the planted clean forms failed (now keyed on file text); the scratch-key scan flagged TmpScratch's own live-key test (now it skips test functions).
Red until wave 2, by design (the trailer floor holds: 97 files ≥ 80):
- tests_scripts/test_microtest.py:246 `assert sites == {}`: 77 asyncio.run sites in 64 files — D 19, U4 15, U2 12, U3 10, U1 6, F 2.
- :253 json.loads counts: 203 over the allow-list — D _sensortask_scenarios +76; U2 webserver_service +102, setter_microdot +22, neopixel_wifi +2, webserver_connections +1.
- :257 public doubles and builders: 90 in 33 files — U4 12 files, U2 7, U1 5, U3 5, D 2, F 2.
- tests_scripts/test_const_mirrors.py:119 `assert problems == []`: 123 mirrors in 27 files — U1 44, U2 32, D 21, U3 16 (machine.py 3 included, per files_U3), U4 8, F 1 (_uart_link_contract), and tests/rp2.py 1, which is in no file list. test_voc_algorithm's `_FIELDS` only shares a name with a src/ const: rename it or pin it. The next line, :120 `reads >= 1`, would also fail today (0 src_const() bindings found).
- Parked-task check: 44 files red. D 28 (10 own files plus 18 per-device files built on its scenario libraries), U2 7, U3 6, U1 1 (isl29125), U4 1 (notification_service), F 1 (dt_machine).
New reds since the H1 sweep (18 files with different counts) all come from F1's fakes:
- machine.reset() now never returns, which microtest reports as "reset reached without a catch".
- Changes to the Pin IRQ, RTC, SPI firstbit, I2C, UART pin and WLAN fakes.
On a git archive of api1, five of these files (setter_microdot, system_service, sgp40, wifi, sensortask_wozi) gave the same FAIL sets as my tree, so none of the 18 is from lane H. MemoryError count: 0 in all 97 files.
Facts owed:
- X: E.1 cleanup raises every failure but absence, and a key is live once per process (also scanned across files). E.2: the value check, ABORT line, after_each hooks plus parked check, canonical trailer, sorted order. E.3: a stale tree is refused. E.5: an incomplete file fails both runners, and the traced set includes build/generated_src/. L.5: each boot entry is executed at L1 (A.4 file name sensortask_<d>_main.py). No @tunable was added.
- Y: relayed earlier, unchanged.
- Lead:
  - build/generated_src/.inputs_stamp.json is now {"inputs": {path: sha256}} over the generator script, buildgen/, src/, ext/, the error catalog, the toolchain overrides and versions, and the TOMLs. definitions/inputs_stamp.json is unchanged, so only the guard needs a rebuild.
  - The Any-baseline loses pyproject.toml:442 `"_coverage_runner",` and :445 `"_shared_rest_roundtrip",`. A probe with both lines removed shows only F's 37 errors.
  - No ANN401 or host_typecheck.ini lines change.
  - New public helpers: _src_const.py_value(path, name), _generated_tree.devices(), _shared_rest_roundtrip.drain_json(body).
Deviations (agent, 2026-10-13):
- Content hashes instead of st_mtime_ns: MicroPython's os.stat()[8] has whole seconds only (extmod/vfs_posix.c:380).
- The boot-entry timeout comes from py_value("buildgen/validate.py", "_WDT_TIMEOUT_MS") because codegen has no const() for it. The threshold is read from the entry's own gc.threshold() line.
- The boot-entry test injects its own print recorder instead of using record_prints.
- The harness resets cur_task and cleans up leftover tasks after a run.
- The payload helper takes a Mapping.
Silent-failure scan, two new findings, nothing else uncovered:
- Class 4 (twin and tooling): tests/_ntp_frames.py:37 treats any OSError from recvfrom as a spurious wake-up.
- Class 4 (stale module for a removed device): scripts/_generate_sensortask_modules.py leaves a removed device's modules in build/generated_src/ while require_fresh() passes. Lane H's own readers derive devices() from devices/*.toml, so they skip them.
Runs and exits:
- final.sh: 8 files × (-1, 32768, settrace), all passed, mem 0.
- tests_scripts runs: 6 touched files rc=1 (the 4 expected reds plus 2 since fixed); runner/generator files rc=0 (44 passed); 12 before-commit checks rc=0 (635 passed).
- mypy: main pass 37 errors in 11 files, all F's consumers; twin and host passes clean.
- Sweep of 97 files rc 0; api1 attribution ×5; coverage prefix ×2.
- Every RUNS.md line is closed, ps shows nothing of mine running, and the typings symlink is removed.
