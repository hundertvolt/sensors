B7 hand-back, written by the agent (2026-11-03)

Worktree `S/wt-b7`, branch `audit/r1-b7`, from d6bc7617. Two commits, each with its source, tests and docs:
**6c00e98e** (items 1-6 and 8-15) and **15b2175b** (item 7 in the owner's wider form). Nothing pushed or merged.
Run logs are `S/u35/lead/b7_*.log`, and the gate is `b7_gate_*.log`. Line numbers are the action list's (d6bc7617
tree) unless a commit is named.

## Items

Test runs are `S/u35/lead/b7_*.log`. "Red" means the changed test failed on the unchanged source.

1. **NP-5, the overlay rewrite: removed.** `_overlay_loop()` waits on its flag alone (`await self._overlay_start.wait()`);
   `_OVERLAY_REFRESH_MS`, its `@tunable` and Part N row, and the `wait_for_ms()` wrapper go. Went first:
   `test_the_overlay_is_rewritten_once_per_refresh_period`, `test_an_overlay_wake_leaves_one_flag_registration_and_no_task_behind`,
   twin `test_the_driver_rewrites_a_dipped_pixel_at_its_next_overlay_refresh`. New
   `test_the_overlay_task_writes_on_a_change_alone_and_any_cancel_ends_it` (cancel at 1 ms, 150 s, 300 s with the wake
   released but not run, 600 s): red (b7_red_np: a grey frame by 600 s), green after. On the driven shim the cancel part
   was not red on the old code (the shim does not reproduce the cleanup window), so the red is the frame part.
2. **NP-3, the entry sanitiser: restored to the ramp's own clamp.** `_signal_values()`, `_MAX_SIGNAL_S` go; `_clamp_byte()`
   catches NaN/inf again; the ramp floors `t` with `not t >= _MIN_SIGNAL_S`, plays +inf as one step and clamps each
   channel; both entries store `[r, g, b, t]`. `test_clamp_byte_direct` gained NaN, +inf, -inf -> 0: red (`ValueError:
   can't convert NaN to int`), green after. Went first: the 60 s cap and REST-ceiling tests. The listed frame tests
   stayed green unchanged.
3. **The internal request queues at its deadline: changed.** `while is_set() and ticks_diff(deadline, now) > 0: sleep`,
   then store, set, `return True`; the drop branch and its event line go; `_SIGNAL_WAIT_MS`'s comment states the queue.
   Changed first, all red then green: `test_request_signal_queues_at_its_deadline_when_the_signal_task_never_runs`
   (True, `_rgbt == [0, 10, 0, 0.1]`, slot set, no NEOPIXEL line), rollover `(True, True, True)`, integration
   `test_a_notification_behind_a_busy_led_queues_at_its_deadline_with_no_entry` (no entry; `_rgbt` is the flash's values:
   last wins; nothing plays).
4. **W67 and the default-sink identity: removed.** `_trigger_signal()` back to a plain await in its try (E14 on a raise);
   `_sink_is_default`, `_WRN_NOTIFY_SIGNAL_DROPPED`, catalog row 67 go; the sink is an instance method again; ruff
   ARG002 replaces ARG004 (and PLR0124, item 9) in `pyproject.toml`. Went first: the two drop-warning tests;
   `_FakeSignalCb.result` went with its last reader. Green: the sink test, the default-sink integration test, the
   buildgen generate/validate pins.
5. **NP-4's end state: the pre-audit form** (lead decision). Black and the slot's clear at the ramp's end inside the
   lock, the overlay restored after it; the start-time `_overlay_start.set()` in both tasks goes; the signal task's
   start black stays. Went first: NP `:669, :693, :721, :740, :824` with `_SupervisorPasses`; twin
   `test_a_restarted_signal_task_ends_dark_with_the_overlay_restored` with `_restart_ends_dark`, its own
   `_SupervisorPasses`/`_yields_until` and the boot machinery the file gained for it (prewarm, UDP shim, imports: the
   header is back to its pre-boot-test form); `tests/neopixel.py`'s `raise_on_write`. Mechanical, because the overlay
   task no longer writes at its start: two integration tests expect one start frame, not two; the twin Wi-Fi modes
   test's "(a)" check no longer requires a frame (`all()` over the frames written, none lit). Green: the listed ones.
6. **NP-1, NP-2's poll, the REST refusal: kept.** The listed tests green.
7. **The notification sample and its /status keys: removed, on the owner's word** (wider form, below).
8. **NT-3, the sample age: removed.** `_SAMPLE_MAX_AGE_S`, its tag and Part N row, `ts`/`now` and the check go. Went first:
   NS `:876`, `:1577`, `:1590` with `_checked_at` and `_FakeValue.TS`; twin `test_a_stopped_scd30_ends_its_alerts` with
   `_STALE_AFTER_S`, read first: it steps the wall clock past the bound before the SCD30's next cycle re-stamps its
   sample (`_store_scd()` stamps `results[3]` even with no new data), so it reproduces nothing the device meets. Its
   helpers `_sgp40_cycle`, `_MEASURE_RAW`, the `SGP40Chip` import went with it.
9. **NT-4: typing-side form.** `value: int | float | None`, `float(value)` with the pre-audit comment (a NaN compares False
   both ways); E15 stays for a raising producer. Went first: the non-numeric test, `test_check_one_never_raises`'s
   three non-numeric cases (the pre-audit list again). `:761` (NaN) now `is False`: red on the old code (None), green.
10. **NT-7, the per-episode flag: removed.** Every failing cycle persists and prints CFG_READ (the post-U10 form and
    comment). Changed first, red then green: `test_an_unreadable_own_config_logs_one_entry_and_one_line_per_cycle`
    (counted by console lines: entries equal lines, at least three per run, one ring slot, a restart changes nothing),
    `test_monitor_loop_keeps_running_on_persistent_config_read_failures_and_persists_one_slot` and
    `..._before_and_after_a_good_read_share_one_slot` (the post-U10 forms, plus: the service's count equals the
    store's own CONTRACT count since setup, one entry per failing cycle in each layer). `:1273` green.
11. **`NeopixelDriver.setup()`: answers nothing.** `test_asy_neopixel_driver.py` and `tests/test_readiness_gates.py`
    `is True` -> `is None` (mechanical; the readiness one was not on the list).
12. **NP-R1, the constructor's rate and brightness: restored** (lead decision). `neopixel_freq: int = _NEOPIXEL_FREQ_HZ`,
    `led_overl_bri: int = _LED_OVERL_BRI`, the tags on the constants kept, `_frame_ms = 1000 // neopixel_freq`. Changed
    first: `test_the_frame_rate_and_overlay_brightness_default_to_the_module_constants` (defaults the constants, the
    keywords set 40 Hz / 25 ms / 7): red (`TypeError: unexpected keyword argument`), green. Mechanical: every test that
    set `neopixel_freq`/`_frame_ms`/`_overlay_bri` from outside passes the keyword (7 sites, the rollover helper keeping
    its `@tunable` frame value).
13. **Kept as landed.** Nothing changed; the existing tests green.
14. **Not B7's**: untouched (the TS row itself went with item 7 on the owner's word).
15. **Other hunks.** NP's header states the queue past the deadline. Comment-only hunks left where they state the code
    (the overlay lock's comment now "an overlay write never cuts into a signal"). One lost function to the lead, below.

### Item 7 in the owner's wider form (2026-11-03 20:35 UTC: "As you said that code functionality can be tested without all that, we do as recommended, only keep pause time")

- `/status`'s notification block is `{"PauseTime": ...}` alone (`codegen.py`'s `_notification_status()`); the Status
  page's "Notification Status" group goes (`definitions.py`, the TS row's label and format with it); catalog
  `status.NotifyState` goes; `mockdata/samples.json`'s block is `{ "PauseTime": 0 }`. The Pause control's `statusPath`
  is unchanged.
- The service publishes no sample: `NOTIFY` is an empty namedtuple for `SensorReaderConfig`'s constructor (named as
  `_NAME`, the convention test's rule), `_FIELDS`, `_STATE_*`, `_store_notif_data()`, `get_data()`, `get_dict_data()`,
  the `utc_now`/`make_dict` imports and the loop's `any_triggered`/`state` go; the unreadable cycle stores nothing;
  `_check_one()` answers False again for a value it cannot evaluate (its pre-audit comment). Readers checked first: the
  notification is in no device's `sensors=` (so not in `/measurements`), and the emitter was the only product reader.
- Tests that went first: NS `test_the_stored_sample_has_a_timestamp_only_once_the_clock_is_set`,
  `test_the_sample_reports_why_signals_were_not_evaluated` and `_first_stored_sample()`; the per-device State scenario
  with `_Rp2Gmtime`, `_ReadableSample`, `_NOTIFY_CYCLE_ROUNDS` (its Part N row) and `_one_notification_cycle()`; twin
  `test_a_boot_without_ntp_reports_no_local_time` with `_NO_CLOCK`/`_EVALUATED` (unit `:1126, :1143` keep the no-clock
  rule); `tests_scripts` `test_the_notification_status_publishes_why_its_signals_were_not_evaluated` and
  `_STATUS_ROW_TABLES`.
- Changed first, red then green (b7_red7 / b7_green7): `_check_one()` False for a None value, a raising producer and an
  unreadable threshold (3 NS tests); the status scenario `set(notification) == {"PauseTime"}` (red on dev, the device run:
  `{'Triggered', 'TS', 'PauseTime', 'State'}`); `test_the_notification_status_is_the_pause_alone_read_from_status`
  (no status group, the emitter returns `["PauseTime"]`, the Pause control's `statusPath`).
- Reading frames or calls instead of `Triggered` (mechanical): the twin overnight-window test (red frames; the
  outside-window cycle now waits on its own local-time read, recorded by a stand-in around the boot's `ntp.cettime`,
  restored in its `finally`); twin NTP's flash wait (frames alone); the NS restart test (the monitor parked on its next
  cycle and never asked the local time, for `State == 1`); the self-heal test (a signal at 2000 flashes again once the
  config reads, for the stored State 0); the four integration `_cycle()` helpers (the loop not yet parked on its next
  cycle 1 ms before the settle ends, for "nothing stored"); the default-sink integration test lost its `Triggered`
  assert and its clock flag. `tests_js/templates.test.js` expects `ResetReason` alone; readiness gates lost the
  `get_data`/`get_dict_data` rows.
- Three host checks followed (b7_pyt_all4, fixed in 15b2175b): the status-group test now counts a key shown through a
  `statusPath` field as listed (PauseTime is shown by the Pause control only); the module-double surface test takes the
  shared interface over the subclasses that publish `get_dict_data()` (the webserver's sensors), a third element of
  `_MODULE_DOUBLES`; the measurement-module guard counts six.

## Knowledge lines (removed items)

All removed code is at d6bc7617 unless named.
- Overlay rewrite (NP-5): `_OVERLAY_REFRESH_MS` (300 s, `@tunable led.overlay_refresh_ms`) and the overlay task's
  `wait_for_ms()` around its flag wait rewrote the overlay at least every five minutes, for a WS2812 blanked by a
  supply dip; the premise was refuted on silicon (0 deviated samples in 12 x 10 min, 794,560 Wi-Fi burst packets),
  and the bounded wait lost a cancel landing in its cleanup window (8/8). The overlay writes on a change alone.
- Entry sanitiser (NP-3): `_signal_values()` clamped each colour and bounded `t` to 0.1-60 s (`_MAX_SIGNAL_S`) where
  a request entered; the ramp clamps each channel (NaN/inf to 0) and floors `t` (NaN too) as before, +inf one step;
  no 60 s cap: every caller bounds `t` (REST 0.5-60 s, `FlashDur` 0.5-10 s).
- The internal request's drop (NP, item 3): past `_SIGNAL_WAIT_MS` `request_signal()` answered False with an event
  line and kept the queued values; it now queues anyway and answers True, its values replacing any still waiting
  in the slot (last wins). Known limit: a ramp longer than 120 s (no product caller: `t` <= 60 s) has its slot
  cleared at its end, so a request that queued behind it at the deadline is lost.
- W67 `NOTIFY_SIGNAL_DROPPED` (NT-5): the notification persisted a warning when `request_signal_cb` answered False,
  telling the default sink apart by identity (`_sink_is_default`, the sink a `@staticmethod`); with the request
  queueing there is no drop. Catalog row 67 went; the W band [67, 68] stays.
- NP-4's end state: a `try`/`finally` freed the slot, wrote black and asked the overlay back on any end of a ramp,
  and both tasks re-asked the overlay at their start; the only raise inside a ramp is a failed tuple allocation
  (`write()` raises only for bad arguments). Now the ramp's end writes black and frees the slot inside the lock and
  restores the overlay after it; a supervisor restart mid-ramp writes black, replays the one flash still in the
  slot, then restores the overlay (pinned again in fix round 2, `tests/neopixel.py`'s `raise_on_write` back for it).
  A controlled shutdown or bootloader entry mid-ramp (a `reboot`, `bootloader`, `resetconfig` or `erasefram`
  command) cancels the task and leaves the last frame showing until the next boot's start frame. That is how it was at
  `25caf528` and in the deployed legacy, and a lit overlay stays shown the same way. A restarted overlay task no
  longer re-applies the overlay until the next `on()`/`off()`/`toggle()` or ramp end (as at `25caf528`; it can end
  only by a raise in its write path).
- The sample age bound (NT-3): `_SAMPLE_MAX_AGE_S` (10,800 s, `@tunable notify.sample_max_age_s`) made a producer
  sample whose `TS` was older unavailable (State 3). The premise "every producer re-stamps its sample" was refuted by
  the falsifier: a stopped SCD30 raises no RDY, runs no read cycle and kept its last values. That case is now closed at
  its source (fix round 3, 42153dc4), not by an age bound.
- The stopped SCD30's last values (fix round 3, the owner's word): `_frc_not_measuring()` republished the last sample
  with state 0, so after a `ContMeas=false` (or two missed intervals) the last CO2, Temp and Hum stayed published and
  the notification flashed on them every `FlashInterval`. Now it publishes CO2, Temp, Hum, WetBulb and DewPoint as None
  with its own TS until the next measurement (owner, 2026-11-04: "For the stopped sensor, option c, the clean
  solution"). A missed measurement (two intervals without data while still measuring) now also blanks the values
  until the next one. The old republish's code is at d228c988.
- Non-numeric and NaN refusals (NT-4): `_check_one()` logged E15 "Value not numeric" for a non-number and skipped a
  NaN (`value != value`, ruff PLR0124); every producer field is typed numeric or None, and a NaN compares False both
  ways, so it never triggers. E15 stays for a raising producer.
- The per-episode flag (NT-7): `cfg_unreadable` logged an unreadable own config once per run of failing cycles; it
  now persists and prints every failing cycle, one slot by the newest-entry rule (the post-U10 form).
- `NeopixelDriver.setup()`'s True ("ready"): read by nothing (the boot ignores the answer).
- The notification's published sample (item 7, the owner's word): `/status` carried `Triggered` (a flash this cycle),
  `TS` (the cycle's time) and `State` (0-4: evaluated, off by setting, no clock, part unavailable, own config
  unreadable; catalog `status.NotifyState`), shown on the Status page's "Notification Status" group with
  "Remaining Pause Time"; none was requested: `Triggered`/`TS` came in with da9b4abb (agent, 2026-08-05), `State` with
  U22 (2026-10-13); the deployed firmware answers only the remaining pause (`modules/sensortask-wozi.py:384`). The code
  is at 6c00e98e (`NOTIFY`, `_store_notif_data()`, `get_data()`/`get_dict_data()`, the State scenario and tests).

## Proof check (PLAN 0) on the remove items

None of the removed items had proof that it is good, so none became a shrink item. Item 1: its premise (a WS2812
blanked by a supply dip) is refuted on silicon (`bench/READING_20261029.md:35, :93`), and its bounded wait lost a
cancel. Item 2: every caller bounds the duration, and the ramp's clamp holds NaN and inf. Item 4: with item 3 nothing
is dropped. Item 5: the only raise its tests inject is one rp2's `write()` cannot produce. Item 8: its twin test was
read first and reproduces nothing the device meets (the SCD30 re-stamps its sample every cycle). Item 9: no producer
field holds a non-number, and a NaN compares False both ways. Item 10: the owner's "Pure and simple." Item 7: the
owner's word. Legacy check: as the action list states; item 12 restores the constructor's rate and brightness.

## Decisions taken (agent, 2026-11-03)

- The service passes an empty `NOTIFY` namedtuple to `SensorReaderConfig`, whose constructor takes an initial sample
  (`asy_base_classes.py` is not B7's file); it is named as `_NAME`, the convention test's rule.
- The new overlay test runs on the driven clock. It is red on the old code through its frame check; the driven shim
  does not reproduce `wait_for`'s cleanup window, so the cancel half is green on both.
- `test_memory_catalog.py` lists `_rgbt` for `led_signal()`/`request_signal()`: the list each stored request keeps
  until the next one. `_signal_values()` built and kept that list before; the scanner now sees it as a literal.
- Item 5's mechanical follow-ups: two integration tests now expect one start frame instead of two, and the twin Wi-Fi
  modes test's "(a)" check no longer requires a frame. Item 12's: seven test sites pass the keyword.
- `test_digital_twin_network_neopixel.py` loses the device-boot machinery (the prewarm, the UDP shim, the machine
  reset hook and their imports) with the only test that booted a device; its header is back to its pre-boot form.
- Item 10's per-cycle tests count the store's entries from its own count after setup (its config-file-missing
  warning).
- Item 7's host-check follow-ups, the twin window test's local-time stand-in and the clock-wake form of the four
  integration cycle helpers, as listed under item 7.

## Findings

- **To the lead (item 15, a pre-audit function lost without a recorded reason)**: the pre-audit event lines
  "Internal LED command received." / "Internal LED command started." in `request_signal()` and "External LED command
  received." in `led_signal()` (`25caf528` NP:138, :146, :152) went in U9 (`2f049a00`) with the refusal redesign. That
  commit gives no reason for them. Restored in the fix round (next line).
- **Fix round (the lead's decision on the item-15 finding)**: the three event lines are restored in **21086438**, as
  at `25caf528` NP:138, :146, :152. The two pinning tests were red first; NP is now 2,523 B (+131 B against 15b2175b,
  -42 B against d6bc7617), and `src/` is 194,820 B.
- `tests/test_asy_webserver_service.py` still uses `{"Triggered": False}` as a fake status source's answer
  (`:1197, :1207`) in generic webserver tests. No product code reads it, so it is left.
- CARRY_LATER already has the R2 line on the twin pixel's `power_dip()`/`displayed()`/`raise_on_write`.

- **Fix round 2 (from the falsification, `FALSIFY.md`; commit d228c988)**:
  - The Status page's "Notification Status" group returns with the "Remaining Pause Time" row alone, in its
    pre-audit place. The status-group test is back at its d6bc7617 form, and
    `test_the_notification_status_is_the_pause_alone_read_from_status` expects that one row. Item 7's removal of
    the group is reversed; Triggered, State and TS stay gone.
  - SPEC F.2 drops the overlay's periodic rewrite and counts five waits that map no sentinel.
  - E15's catalog text reads "a producer's get_data() raised".
  - Restart coverage:
    - `test_a_cancelled_ramp_keeps_its_slot_and_a_restarted_task_replays_it_then_restores_the_overlay`: a cancel mid-ramp
      writes nothing more and keeps the slot. The restart then writes black, the full 50-frame flash and black, then
      the overlay grey.
    - `test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry`: the real SystemService, a frame write
      failing mid-ramp, one `TASK_RAISED`, the same replay.
    - Planted break A (the ramp under `try`/`except BaseException` that clears the slot and writes black, then
      re-raises) makes both red (b7_f2_plantA: 44/46). The driver was restored with `git checkout --` afterwards.
    - `tests/neopixel.py` is back at its d6bc7617 form.
  - The sample age (claim 8) waits for the owner and is unchanged.
  - Runs on d228c988, each through `run.sh`, one after another:

    | Run | rc | Result |
    |---|---|---|
    | `b7_f2_lint` (lint_direct) | 0 | clean |
    | `b7_f2_mypy` (three passes) | 0 | clean (276 / 314 / 59 files) |
    | `b7_f2_pyt` (whole tests_scripts tier) | 0 | 7,106 passed, 6 skipped |
    | `b7_f2_npfile` (LED unit file) | 0 | 46/46 at -1 and at 32768 |
    | `b7_f2_others` (the 15 other NeoPixel/notification unit files, -1) | 0 | all passed, no memory marker |
    | `b7_f2_npm` (lint, typecheck, test:unit) | 0 | lint and typecheck clean; test:unit 1,340 passed (counts from `b7_f2_npm_unit`) |
    | `b7_f2_putmatrix` (`npm run test:put-matrix`, every case, alone) | 0 | 352 passed, 6 skipped (data-dependent: no current value or option to resubmit), 0 failed; the PauseTime action case passes again |
    | `b7_f2_sizes` | 0 | NP 2,523 B / 175 lines, NS 4,015 B / 325 lines, `src/` 194,820 B (unchanged by this round) |

- **Fix round 3 (the owner's answer on claim 8; commit 42153dc4)**:
  - `src/asy_scd30_driver.py` is B5's file; this round is the one exception the lead allowed.
  - `_frc_not_measuring()` blanks the five values; nothing else in the driver changed.
  - Tests, red on d228c988 (b7_f3_red) and green after (b7_f3_green, b7_f3_scd):
    - `test_frc_readiness_restarts_on_a_gap_an_interval_change_a_pressure_write_and_a_stop` (the stop's sample is
      `(None x5, 0, None, its TS)`).
    - `test_two_intervals_without_data_publish_not_measuring_with_no_values_until_the_next_measurement` (renamed; the
      next measurement is full again).
    - The twin `test_a_stopped_scd30_ends_its_alerts`, back without its clock step: a real reading above WarnCO2, a
      real `ContMeas` stop, the sample's CO2 None, then a monitor cycle that ends (its `_next_sleep_ms()` recorded)
      with no red frame. It was red on arzi and dev (`CO2=1700.0` published after the stop) and passes on both now.
  - Followed mechanically: `test_a_store_interleaved_with_a_republish_keeps_the_fresh_sample` expects
    `(None, 2000)`. The fresh TS is the real pin, since a stale read-then-write copy would carry TS 1000.
  - SPEC M.2 item 1 states the blanked sample.
  - Website: a None value renders "—", the marker for a value not measured yet (`js/field-format.js:93-94`). It is
    pinned for readonly fields with and without decimals (`tests_js/templates.test.js:122, :219`), so no test was
    added. The "unavailable" text is for a module whose map is `{"error": "unavailable"}`, which this is not.
  - No mock data or Part H text named the old behaviour.
  - Consequence for the lead: the SGP40 compensates with the SCD30's Temp/Hum and returns an empty sample when either
    is None (`asy_sgp40_driver.py:380-385`). So a stopped or idle SCD30 now also stops the SGP40's VOC readings
    until the SCD30 measures again; before, the SGP40 compensated with the stale values.
  - The first run of this list (b7_f3_*) found two twin-pass mypy findings in the new test: a `Returning Any`, and
    an unused `type: ignore` (the twin file is outside the main pass). I stopped it by pid after its SCD30 step,
    folded the fix into the round's commit (now 42153dc4) and reran the whole list on 42153dc4, each step through
    `run.sh`, one after another:

    | Run | rc | Result |
    |---|---|---|
    | `b7_f3b_lint` | 0 | clean |
    | `b7_f3b_mypy` (three passes) | 0 | clean (276 / 314 / 59 files) |
    | `b7_f3b_pyt` (whole tests_scripts tier) | 0 | 7,106 passed, 6 skipped |
    | `b7_f3b_scdfile` (`test_asy_scd30_driver.py`) | 0 | 130/130 at -1 and at 32768 |
    | `b7_f3b_notif` (6 notification files + `test_digital_twin_scd30.py`, -1) | 0 | all passed (62, 3, 6, 4, 2, 3, 56) |
    | `b7_f3b_twin_m1` / `_32768` (`test_digital_twin_sensortask_integration.py`, six devices) | 0 | 0 failed at both stages, the new test passing on arzi and dev |
    | `b7_f3b_sensortask` (`test_sensortask.py`, six devices) | 0 | 101/101 each |
    | `b7_f3b_hazard` (bus-hazard mock, generated and twin files) | 0 | 22/22, 39/39, 25/25 |
    | `b7_f3b_npm` (lint, typecheck, test:unit) | 0 | clean; 1,340 passed |
    | `b7_f3b_sizes` | 0 | `asy_scd30_driver` 12,405 to 12,472 B (+67 B, the owner's admitted fix), 874 to 875 lines; `src/` 194,887 B |

    No memory marker in any run.

## Gate

The gate ran on 15b2175b from 21:26 to 22:44 UTC, alone on the host, one step after another, each through `run.sh`:
- `b7_gate_unit` (`scripts/test.sh`, GC -1): rc=0, 755 s. 137 files passed, 0 failed (80 skipped; 6 deselected, the
  port-53 scenario per device that `run_digital_twin_ci.sh` runs). 5,832 tests and 7,106 `tests_scripts` tests passed.
  0 "MemoryError", 0 "memory allocation failed".
- `b7_gate_unit_32768`: rc=0, 799 s, the same counts, 0 failed, 0 / 0 markers.
- `b7_gate_twin_suite_m1` / `_32768` (dev): rc=0, 641 s / 697 s. 331 + 15 checks passed, 0 failed.
- `b7_gate_twin_harness_m1` / `_32768` (dev): rc=0, 759 s / 773 s. 65 scenarios passed, 0 failed, 2 skipped (the 0444
  file-mode probe under root; a mechanism that runs on arzi only).
- Across the four twin logs, the only lines carrying a memory marker are the suite's own "log carries none of" checks.
- `b7_gate_npm`: rc=0, 237 s. eslint and tsc clean; test:unit 26 files / 1,340 tests passed.
- Before the gate: `lint_direct.sh` and the three mypy passes were clean (b7_lint_direct, b7_mypy3/4, b7_pyt9).

## Sizes

`module_sizes.sh` (`S/u35r/r1/B7/sizes/`): `src/` 195,511 B at d6bc7617 to **194,689 B at 15b2175b (-822 B)**, 15,600
to 15,528 lines; against R0's 208,708 B, -14,019 B. Per module: `asy_neopixel_driver` 2,565 to 2,392 B (-173), 189 to
172 lines; `asy_notification_service` 4,664 to 4,015 B (-649), 380 to 325 lines. Both are now below the pre-audit
2,840 and 5,021 B. No module grew. Lines in the two commits: `src/` +71 -143; tests +194 -1,073; docs +40 -60; other
(catalog, codegen, definitions, mock data, pyproject) +5 -28.
FW: `scripts/build_firmware.py dev` (b7_fw, after the gate) gives `imageFreeBytes` **58,956 B**: d6bc7617 had 57,868 B
(B6 hand-back), so +1,088 B; R0 had 43,068 B.
