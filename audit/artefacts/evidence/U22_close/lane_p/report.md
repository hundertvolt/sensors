# U22 lane P final report

Branch `audit/u22-p`, worktree `scratchpad/wt-u22p`. Commits: `e262800` (WIP P1), `40a34b0` (merge of `audit/u22-api`
@ `4f8264c`), `7b548af` (final). Not pushed.

## Step table

| # | M-id | state | note |
|---|---|---|---|
| 22 | M.SRC_SENS.028 | applied (P1) | `_signal_loop()` sets `_overlay_start` after its black start frame (`src/asy_neopixel_driver.py:104`); (c) already landed (the `finally` order, `:125-129`) |
| 23 | M.SRC_SENS.035 | applied (P1) | attribute writes gone; `_check_one() -> bool \| None`, `None` on every path that does not evaluate the signal (raised read, missing, stale, non-numeric, NaN, unreadable threshold); stale check in SGP40's predicate shape (A-14) with `_SAMPLE_MAX_AGE_S = const(10800)` (`src/asy_notification_service.py:68-69`); `report_if_fatal` is U30 |
| 24 | M.SRC_SENS.033 | applied (P1) | `last_value`/`triggered` and their comment gone; callbacks `Callable[[int, int, int, float], Awaitable[bool]]` / `Callable[[], Awaitable[_LocalTime \| None]]`; default `NOTIFY(Triggered=False, State=None, TS=None)`; construction-time service, `_sink_is_default` already landed |
| 25 | M.SRC_SENS.020 | applied (P1) | `TYPE_CHECKING` block: `Callable`, `Any` out, `TaskStarter` beside `ErrorSource, TimerStarter`; runtime imports already landed |
| 26 | M.SCR.028 | nothing at U22 | `scripts/typecheck.sh` not edited; main pass clean with the six modules out of the baseline |
| 27 | M.SRC_SENS.025 | applied (P1) | `_overlay_loop()` sets the flag once before `while True:`; bounded wait `asyncio.wait_for_ms(..., _OVERLAY_REFRESH_MS)` with `except asyncio.TimeoutError: pass`, constant `:38-39`, comment with the datasheet fact `:89-90` (OF-75, A-16); `get_task_starters() -> "list[TaskStarter]"`; starters, sources, loggers, `reset_error_counter() -> bool` already landed |
| 29 | M.SRC_SENS.030 | applied (P1) | `Coroutine`/`Any` out, `Awaitable` in, `TaskStarter` beside `TimerStarter, ValueRef`, `_ValueSource.get_data() -> object`; the `_TicksMs` comment is U27's, `report_if_fatal` U30's |
| 30 | M.SRC_SENS.034 | already landed / nothing more | no explicit `Any` in its functions; SF-B2's part landed (`:84-94` static sink, `:210` `_sink_is_default`, the tested bool, `_WRN_NOTIFY_SIGNAL_DROPPED = const(67)`); `_next_sleep_ms()` U31 |
| 31 | M.SRC_SENS.036 | applied (P1) | `get_task_starters() -> "list[TaskStarter]"`; `set_override_led()` stays `-> bool` returning `True` (A-9) |
| 32 | M.TEST_HELP.006 | nothing at U22 | `tests/neopixel.py` untouched; the restart cases use its `raise_on_write` as is |
| 33 | M.TEST_UNIT.078 | applied (P1) | `run(coro: "Coroutine[object, object, T]")`, `Any` gone; builders, driven time, `_frame_ms` are U24/U31/U35 |
| 34 | M.TEST_UNIT.079 | applied (P1) | `test_the_overlay_is_rewritten_once_per_refresh_period` under `_DrivenClock` (A-12: `_YieldOnlyAsyncio.wait_for_ms` and `TimeoutError`); "existing counts hold" re-checked: the repeated-on test passes unchanged; `== 31` is U35's |
| 35 | M.TEST_UNIT.080 | applied (P1) | `test_a_restarted_overlay_task_reapplies_the_overlay`, `test_a_signal_task_ended_mid_ramp_restarts_dark_and_restores_the_overlay`, `test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry` (real `SystemService`, its 2 s pass gated by the test) |
| 36 | M.TEST_UNIT.082 | applied (P1) | `run()` per A-11, `Any` gone (`Coroutine` stays: `run()`'s annotation needs it); U24/U35 builders not written |
| 37 | M.TEST_UNIT.084 | applied (P1) | scenario returns typed `WriteValidity` and `get_dict_cfg()`'s declared type: `JsonDict` does not fit, since `get_dict_cfg()` is not retyped on this tree (deviation 2) |
| 38 | M.TEST_UNIT.086 | applied (P1) | the `signal.triggered` assert goes; (1) the threshold-read failure asserts `None`; read-log helpers return `ErrorLog`; the rest already landed |
| 39 | M.TEST_UNIT.087 | applied (P1) | attribute asserts gone; `test_check_one_returns_the_most_recent_trigger_state` (guard); (1) `None` on the raising source, `None`, non-numeric and NaN values; (2) `test_a_stale_producer_sample_is_not_evaluated` |
| 40 | M.TEST_UNIT.274 | applied (P1) | typing (`JsonDict` body, the errcount entry read as `(counter, history)`); the rest U9-U35 stages |
| 41 | M.TEST_UNIT.276 | applied (P1) | typing (`_HourMinute` Protocol for the local-time callback); the rest staged |
| 44 | M.TEST_UNIT.347 | applied | `test_the_silent_mode_leaves_a_real_neopixel_driver_dark_until_a_link` |
| 45 | M.TOOL.030 | applied | `"src/asy_notification_service.py" = ["ARG004"]` (A-10); the comments stay |
| 46 | M.TOOL.033 | applied | six modules out of the baseline |
| F2 | M.SRC_SENS.037 | applied (P1) | `NOTIFY = namedtuple("NOTIFY", ("Triggered", "State", "TS"))`, `_FIELDS` follows; one `state` per cycle, the config-failure branch stores too; `_store_notif_data(*, any_triggered, state)`; codes as named constants `_STATE_*` with the one comment line (`:70-75`) |
| F3 | M.TEST_UNIT.088 | applied (P1) | `test_the_sample_reports_why_signals_were_not_evaluated` (every code, AutoOn off / paused / outside the window, no time / raising clock, one value missing / one of two); construction default `(False, None, None)`; `tests/test_readiness_gates.py` 3-tuple and dict; the self-heal test now pins State 4 then 0 |
| F4 | M.TEST_HELP.041 (8) | applied | `webserver_status_notification_state_says_why_signals_were_not_evaluated` on `/status` (A-8, A-21): none before a cycle, 2 before the first sync, 0 after it with readable producers |
| X1 | M.WEB.045 (1) | applied | `mockdata/samples.json` `status.notification.State: 0` |
| X3 | (A-8) | applied | `buildgen/codegen.py` `_notification_status()` adds `"State": data.State`; `buildgen/definitions.py` State row with `_status_codes("NotifyState", ...)`; L0 `test_the_notification_status_publishes_why_its_signals_were_not_evaluated`, and the codes check learns the row's table (`_STATUS_ROW_TABLES`) |
| X4 | (A-18) | applied | guard `test_the_no_configuration_pattern_blinks_a_real_neopixel_driver_and_obeys_led_wifi_on`; the networking scenario asserts `_reconnect_fresh` after the identity PUT (and not after LEDWifiOn) |
| OF-75 | open finding | applied (P1) | closed by row 27's refresh; comment `src/asy_neopixel_driver.py:89-90` states the datasheet fact with no audit ID |
| - | (lead, 2026-10-12) | applied | `tests/test_notification_sgp40_integration.py:240`, `tests/test_notification_scd30_integration.py:240`: the exact list `[(0, 0, 0), (0, 0, 0)]`, comment re-derived |

## Deviations

1. Rows 34, 35, 37-39 and F3 landed in P1, not after the base. Each behaviour change needed its test seen failing on the
   code before the fix, so the tests went into the same commit as the change.
2. Row 37 / A-11: the scenarios return `WriteValidity` and `get_dict_cfg()`'s declared
   `dict[str, dict[str, int | float | str | bool | None]]`, not `JsonDict`. The tree does not retype `get_dict_cfg()`,
   and dict invariance makes `JsonDict` a type error. This is the action's own fallback.
3. X3 needed one test-side table map, `_STATUS_ROW_TABLES = {"State": "NotifyState"}`. Without it
   `test_every_field_codes_table_equals_its_catalog_status_table` would look up a table named after the row key, which does
   not exist for this row. The check is not weakened: the row's codes are still compared with the catalog table.
4. F4 swaps the NTP client's `time` for an rp2-shaped `gmtime` (`_Rp2Gmtime`) inside the scenario. `cettime()` answers
   only in rp2's 8-field shape, so on the Unix port no synced cycle can reach State 0 any other way. This is the third
   copy of that stand-in (`tests/test_notification_neopixel_integration.py`, `tests/test_digital_twin_sensortask_integration.py`).
   U24's shared helpers are the place to fold them; nothing new is created here.
5. F4's readable producers are a test-local `_ReadableSample` stored with each producer's `_set_meas_data()`, because
   MicroPython's namedtuple has no `_fields`/`_replace` (probed on the Unix port).

## Files outside my set

None edited. I regenerated `build/generated_src/` in my worktree (allowed). The lead rebuilt `frozen_modules/`/`build/generated_html/`.

## Facts owed

### For D (SPECIFICATION.md)
- `@tunable` added (none renamed or withdrawn):
  - `led.overlay_refresh_ms = 300000`: Sites `src/asy_neopixel_driver.py` `_OVERLAY_REFRESH_MS`. Basis: the default
    notification `FlashInterval`, about once per notification cycle (agent, 2026-10-06). Re-check trigger: a
    `FlashInterval` default change.
  - `notify.sample_max_age_s = 10800`: Sites `src/asy_notification_service.py` `_SAMPLE_MAX_AGE_S`. Basis: three times the
    longest configurable producer interval (BMP3XX `SampleInterval` 3600 s), so a slow producer is never cut off (agent,
    2026-10-06). Margin: a producer late by up to three intervals still counts. Re-check trigger: a producer's
    interval maximum changes.
  - `l1.sensortask_notify_cycle_rounds = 200`: Sites `tests/_sensortask_scenarios.py` `_NOTIFY_CYCLE_ROUNDS`. Basis:
    estimated (agent, 7b548af), a hang guard in scheduler rounds; a monitor cycle that flashes nothing stores its sample
    within a few rounds.
- API end states: `NOTIFY` fields `("Triggered", "State", "TS")`; State codes 0 every signal evaluated, 1 off by
  setting (AutoOn off, paused, outside the window), 2 no local time, 3 evaluated in part (a value unavailable, stale or
  not numeric), 4 own configuration unreadable (the catalog's `status.NotifyState` texts); a config-failure cycle now
  stores `(False, 4, TS)`; `_check_one() -> bool | None`. A producer sample whose `TS` is older than
  `notify.sample_max_age_s` is unavailable; one with no `TS` counts as current. Each (re)start of either LED task writes a
  defined state: the signal task black, then the overlay restored; the overlay task the current overlay. The overlay is
  rewritten at least once per `led.overlay_refresh_ms` with no change pending, and a running ramp holds the lock, so a
  rewrite never cuts into a signal. `/status` `notification` keys: `Triggered, State, TS, PauseTime`; the Status page row
  is "Evaluation State" with the NotifyState codes.
- A-13: the bounded wait allocates per overlay wake, not once per period. Measured on the 64-bit Unix port
  (build-standard, gc off across one wake, same harness): 1504-1600 B per wake against HEAD's 608-704 B, so 896 B per
  wake for the waiter task, runner task, their coroutines and the `CancelledError(status, result)`. The figure is
  short-lived and collectable, and the structural guard shows no task outlives a wake or a cancel. rp2 (32-bit) is
  roughly half; that is an estimate, not measured. Wakes: up to two per second in a connect poll, one per flash phase.
  Retained growth: none.
- Yield bounds re-derived (A-13). `tests/test_neopixel_wifi_integration.py`:
  - `_PHASE_YIELDS = 4` is twice the least that keeps every phase written. Measured: 2 with the bounded wait and 2 with
    HEAD's plain flag wait; 1 drops phases in four tests.
  - `_PATTERN_YIELDS = 8 * _PHASE_YIELDS` is unchanged at 32, four whole cycles.
  - `_run_until`'s comment states the three hops of a real wake (waiter, runner, overlay task).

  `tests/test_asy_neopixel_driver.py`: `_run_until`'s comment states two yields per overlay wake under `_DrivenClock`
  (the waiter, then the wait's own check); every overlay-write bound there is 20.
- `ruff`: RUF100 has nothing to report and ruff stays clean with ANN401 gone from the notification's entry. That is the
  trial-removal proof.

### For E
- BACKLOG chroot list (X2): "`pyproject.toml` lint and type config only: the notification module's per-file ruff entry
  narrows to ARG004 and six modules leave the explicit-Any baseline; no build impact". This matches what landed.
- `/status`'s notification block gains `State` (DEVICE_REFERENCE/README wherever the `/status` keys are listed).

### For the lead
- Allow-list lines: none added, none re-keyed by P. Any-baseline lines removed: `asy_neopixel_driver`,
  `asy_notification_service`, `test_asy_neopixel_driver`, `test_asy_notification_service`,
  `test_neopixel_wifi_integration`, `test_notification_neopixel_integration`. New raises: none. `_ALLOWED`: no change.
- Red checks on my worktree: `test_tunables_register.py`, only on the three tags above vs D's Part N rows (exact lines:
  `src/asy_neopixel_driver.py:38`, `src/asy_notification_service.py:68`, `tests/_sensortask_scenarios.py:2374`).
- Website inputs changed (definitions row, sample key, status key). Reported 17:3x and rebuilt by the lead in wt-u22p;
  rebuild again in wt-u22api after the merge. The web tier (`npm test`, e.g. `definitions-mockdata-coverage`) is yours.
- Files the lead must run on the merged tree:
  - the twin in-process files (`test_digital_twin_sensortask_integration.py`,
    `test_digital_twin_real_website_integration.py`, `test_digital_twin_run_generic_integration.py`,
    `test_digital_twin_bus_hazard_concurrency.py`, `test_digital_twin_uart_link.py`)
  - `test_asy_webserver_service.py`
  - `test_digital_twin_boot_contiguity.py` (L0)
  - the six twins and `npm test`
  - the six-device firmware build (driver and notification bytecode grew)

## Tests run (nice -n 19; e = gc default, f = threshold 32768, cov = settrace; zero MemoryError / "memory allocation failed" lines in every log)

All on the final tree `7b548af`, every run rc=0:

| file | e | f | cov | note |
|---|---|---|---|---|
| `test_asy_neopixel_driver` | 53/53 | 53/53 | 53/53 | |
| `test_asy_notification_service` | 66/66 | 66/66 | 66/66 | |
| `test_notification_neopixel_integration` | 6/6 | 6/6 | 6/6 | |
| `test_neopixel_wifi_integration` | 8/8 | 8/8 | 8/8 | under `unshare -n` |
| `test_readiness_gates` | 14/14 | 14/14 | 14/14 | under `unshare -n` |
| `test_notification_sgp40_integration` | 3/3 | 3/3 | 3/3 | under `unshare -n` |
| `test_notification_scd30_integration` | 4/4 | 4/4 | 4/4 | under `unshare -n` |
| `test_notification_fram_integration` | 3/3 | 3/3 | 3/3 | |
| `test_notification_scd30_sgp40_integration` | 2/2 | 2/2 | 2/2 | |
| 6 `test_sensortask_<device>` | 89/89 each | 89/89 each | 89/89 each | under `unshare -n` |
| `test_bus_hazard_generated` | 36/36 | 36/36 | - | |
| `test_ticks_rollover` | 22/22 | 22/22 | - | |
| `test_reset_call_site_invariant` | 2/2 | 2/2 | - | |

- L0, all green except the expected `test_tunables_register` red: `test_buildgen_definitions` (250),
  `test_buildgen_generate` (330), `test_api_reference`, `test_error_catalog`, `test_definitions_js_mirrors`,
  `test_measurement_field_tuple_agreement`, `test_driver_shape`, `test_buildgen_source_agreement`,
  `test_generate_sensortask_modules`, `test_lock_order`, `test_exception_handler_contract`, `test_decision_vocabulary`,
  `test_citations`, `test_comment_block_cap`, `test_legacy_paths`, `test_import_placement`, `test_code_conventions`,
  `test_host_annotations`, `test_lint_ceilings`, `test_mypy_any_baseline`, `test_memory_error_gate_agreement`,
  `test_fault_or_warning_never_both`.
- ruff over the eight scopes: clean. mypy: the main pass (no-args and `src tests tests_hardware/device_scripts`), the
  twin pass and the host pass all clean.
- The two `:240` files gave the same exact two-frame list in three separate runs (e, f, settrace). Root cause: the
  asyncio run queue is a stable pairing heap (`py/pairheap.c` meld is stable, `extmod/modasyncio.c` keys by ticks),
  so the order is FIFO. The overlay task starts first, the signal task writes its black and sets the flag before the
  overlay's waiter runs, and the waiter then consumes one flag. So it is one overlay write plus the signal start frame,
  every time, long inside the 0.2 s.

## Seen failing first

On the code before the fix:
- driver
  - refresh: against the old driver plus the constant alone, `refreshed == [grey]` fails.
  - wake guard: 0 tasks created, 6 expected.
  - overlay restart: `[]` instead of `[grey]`.
  - signal restart and supervisor restart: `[black]` instead of `[black, grey]`.
- notification
  - threshold read, `None` value, raising source, non-numeric value and NaN: each returned `False`, not `None`.
  - stored sample: `TypeError: unexpected keyword argument 'state'`.
  - F3: the construction default is a 2-tuple.
  - self-heal: a failing cycle stored nothing.
  - stale: against the old service plus the constant alone, the `(stale, inside, untimed)` assert fails.
- readiness gate: the 2-tuple.

After the base:
- L0 State row: 6/6 devices fail.
- F4: `KeyError: State`.
- X4 flag assert: `AttributeError: '_reconnect_fresh'` against the pre-W1 Wi-Fi service.
- Row 44: `ended is True` fails against the pre-W1 Wi-Fi service.
- The two `:240` asserts failed on the P1 tree. That is the WIP's report; with the exact list they pass in all three binaries.

Guards (passed at once): `test_check_one_returns_the_most_recent_trigger_state`, X4's no-configuration pixel case, the
rewritten non-numeric driver case.

## Wall times (s, nice -n 19; before = 18a02f8 for the LED files, the merge base's scenario library for the device files)

LED and notification files (before = `18a02f8`, 2026-10-08; after = `7b548af`):

| file | e before → after | f before → after | settrace before → after |
|---|---|---|---|
| `test_asy_neopixel_driver` | 8.83 → 9.50 | 8.88 → 9.55 | 8.90 → 9.64 |
| `test_asy_notification_service` | 19.02 → 19.07 | 19.14 → 19.23 | 19.17 → 19.28 |
| `test_notification_neopixel_integration` | 6.47 → 6.44 | 6.50 → 6.46 | 6.53 → 6.51 |
| `test_neopixel_wifi_integration` | 2.02 → 2.82 | 2.29 → 3.15 | 2.40 → 3.65 |
| `test_readiness_gates` | 0.13 → 0.17 | 0.21 → 0.25 | 0.18 → 0.22 |
| `test_notification_sgp40_integration` (assert only) | 3.04 → 2.99 | 3.25 → 3.26 | - → 4.25 |
| `test_notification_scd30_integration` (assert only) | 4.50 → 4.50 | 4.57 → 4.56 | - → 4.55 |

Device files grew by one scenario each. After (`7b548af`), at the same time as other lanes' runs on the host:

| device | e | f | settrace |
|---|---|---|---|
| wozi | 52.60 | 69.94 | 103.74 |
| dev | 76.69 | 103.01 | 134.18 |
| arzi | 46.95 | 64.01 | 90.51 |
| grkizi | 46.40 | 63.48 | 90.81 |
| klkizi | 46.36 | 65.51 | 93.27 |
| schlafzi | 47.03 | 63.81 | 93.18 |

Before, only e is available, from the P1 tree on the same day: wozi 53.19, dev 74.73, arzi 46.12, grkizi 45.76,
klkizi 55.34, schlafzi 48.66. So the growth at e is within run-to-run noise.

The before f and settrace device runs are **not taken**. My first attempt was invalid: the device test files were
symlinked into a scratch tree, MicroPython puts the script's real directory first on `sys.path`, and so the worktree's
new scenario library ran. I caught it (the State scenario appeared in the "before" log) and stopped it by pid. The
re-run with real file copies was stopped by pid at the hand-back with no result.

Every file stays under the 240 s per-file bound; the largest is dev under settrace at 134 s. The lead's gate timing is
the measurement of record.

## Runs started (all exited, confirmed with ps; entered in u21/RUNS.md)

All runs were foreground except the one background batch, and every one exited. Logs are in `scratchpad/u22p_runs/`.

**2026-10-08 (before the cut)**
- Baselines: 5 LED files at e/f/cov.
- Tests-first runs of the driver and notification files.
- `u22p_seen` scratch-tree runs: the old product plus the two constants alone.
- After-change runs; ruff; mypy main pass on both scopes.

**2026-10-12, P1 re-validation**
- Regenerated the device modules. 5 LED files at e/f/cov.
- 4 notification integration files at e/f. That run found the two `:240` reds, which were reported.
- Consumers at e: ticks_rollover, bus_hazard_generated, reset_call_site_invariant, the 6 `test_sensortask_*`.
- ruff; mypy, both scopes; the 12 pre-commit L0 files; driver e/f re-run. Commit `e262800`.

**2026-10-12, P2**
- Merged `audit/u22-api`; regenerated (twice).
- The two `:240` files at e/f/cov.
- `test_buildgen_definitions` (`-k`, then the whole file); `test_buildgen_generate`, `test_api_reference`,
  `test_error_catalog`.
- wozi at e three times: F4 seen failing twice, the first being my own PUT-assert bug; then after X3.
- Pixel integration file: r44 run, then `_PHASE_YIELDS` probes at 3, 2 and 1 (restored to 4).
- `u22p_seen2` (pre-W1 Wi-Fi service): the pixel integration file and wozi.
- `u22p_seen3` (HEAD driver, `_PHASE_YIELDS = 1`).
- ruff over the eight scopes; all four mypy passes. Two allocation-measurement runs of under 1 s.
- Affected L0 set, 20 files. Final 9 files at e/f/cov. Commit `7b548af`.
- Background batch, pid 11099: the 6 device files at e/f/cov on the final tree and on the before tree;
  bus_hazard_generated, ticks_rollover and reset_call_site_invariant at e/f.

Scratch trees `u22p_seen*` and `u22p_before` are removed at the end. A `ps` check showed no micropython, pytest or mypy
process left.

The stopped batches (pid 11099 at 18:19:28, pid 16979 at the hand-back) are marked STOPPED in RUNS.md. The `wt-u22p` agent row (17:29:24) is the lead's to close.

## Silent-failure scan (by site and by mode, over my files)

Files: `src/asy_neopixel_driver.py`, `src/asy_notification_service.py`, the notification block of `buildgen/codegen.py`
and `buildgen/definitions.py`, `mockdata/samples.json`, and the generated `_notification_status()` of all six devices.
I read the layer below at the pin for each call: `extmod/asyncio/funcs.py`, `core.py`, `event.py`, `task.py`, the
`modasyncio.c` pairing heap, `py/objnamedtuple.c`, and the WS2812 datasheet.

**By site, class by class**

1. Ignored status: the WS2812 has none to read. `NeoPixel.write()` is one `machine.bitstream()` call with no result,
   and the datasheet's power-lost reset is detected by nobody. Covered by row 27's periodic rewrite.
   Inherently safe otherwise.
2. Bounded storage: none added. The stored sample gains one slot, with no ring and no queue.
3. Detection left to chance: a blanked pixel was fixed only by the next state change. Row 27 now bounds it at 300 s,
   tested under driven time.
4. Swallowed failures:
   - The overlay wait's `TimeoutError` is swallowed by design, since the timeout is the refresh.
   - `_check_one()`'s unevaluated paths returned `False`, a failure that looked like data. They now return `None` and
     surface as State 3 (rows 23 and F2).
   - The config-failure cycle stored nothing. It now stores State 4 (F2).
   - A stale producer sample counted as current. It is now unavailable, State 3 (row 23).
   - The default sink's `False` is still "no LED", already covered by SF-B2.
5. Windows:
   - Each overlay wake now allocates about 896 B (64-bit Unix) for its runner and waiter tasks. These are temporary,
     and the structural guard shows nothing is retained. The allocation catalog row is U30's (A-13).
   - An NTP step forward past a producer's last `TS` reads as stale until that producer's next sample, at most one of
     its intervals. It self-heals; inherently bounded.
   - A step backward gives a negative age, which counts as current.
6. Faults without self-healing:
   - An ended overlay or signal task restarts into a defined state (rows 22 and 27), tested at L1 including under a
     real supervisor.
   - A `MemoryError` inside the bounded wait ends the overlay task, the supervisor restarts it with one SYSTEM entry,
     and the restart re-applies the overlay. Inherently handled.
7. Asymmetric reporting:
   - `/status` now tells why nothing flashed (F4 and X3).
   - **New, minor:** the Status page labels `TS` "Last Trigger Timestamp" (`buildgen/definitions.py:701`). It is the
     last cycle's time, stored on every cycle and now on config-failure cycles too. A reader can take a State-4 or
     State-1 cycle's time for a trigger. No step owns the label, so it is not changed; proposed "Last Cycle Time",
     for D/E or the lead.

**By mode**

- **LED.**
  - Enabled and disabled: `set_wifi_led(False)` leaves the overlay off, so the refresh rewrites black.
  - Each Wi-Fi pattern: the hotspot, the client and the no-configuration pattern on a real pixel, the last of these new
    in X4.
  - The silent mode: dark through entry, a silent attempt's `_led_toggle()`/`_led_on()` and `LEDWifiOn`, lit at the
    link (row 44).
  - The overlay alone; a running signal (the refresh waits for the lock); a refused, queued or expired request (landed
    U9 tests).
  - A task restart of either LED task, and a blanked pixel (the refresh).

  No finding beyond the label above. **Pair noted:** notification ramps still play on the shared pixel during the Wi-Fi
  silent mode. A-5 reads "completely silent" as the Wi-Fi LED's own behaviour; the owner's review row (`REGISTER.md:583`)
  covers it.
- **Wi-Fi, as far as my files take part** (the state machine is W's):
  - STA seeking: toggles at 0.5 s, each a wake with a temporary allocation.
  - Established: steady.
  - Hotspot with and without a client: patterns.
  - Silent: dark.
  - Unreadable configuration: its pattern obeys `LEDWifiOn`.

  A task restart in each runs `_reset_wlan_connect_state()`'s `_led_off()`, then the initial LED config; the overlay
  task follows whatever the service last set. A settings change in each goes through `reconnect_wifi()`: the flash is
  cancelled, the LED is left as the cancel left it, and the next attempt's toggle redraws it within one 5 s loop. The
  generated hook's fresh flag is pinned on every device (X4). No finding.
- **Notification.**
  - Each State code is tested at L1, and codes 2 and 0 per device on `/status`.
  - A stale or missing producer gives 3. A busy LED gives W67 (landed). The default sink gives nothing, by design.
  - The monitor task dead between supervisor passes: State and TS keep the last cycle's values. TS's age and SYSTEM's
    task-end entry show it, so it is inherently visible.
  - A service whose every signal was refused at setup reports State 0 over zero signals. Its W44/W45 refusals are
    persisted at setup and show in errcount. Inherently visible; no change.
- **Long uptime and heap:** the per-wake allocation is collectable and nothing is retained. **Boot:** the overlay task's
  first write is the current overlay, black at boot. **Reconfiguration:** a `FlashInterval` change does not change the
  refresh period, which is fixed. Re-check trigger: the default `FlashInterval`, Part N.
