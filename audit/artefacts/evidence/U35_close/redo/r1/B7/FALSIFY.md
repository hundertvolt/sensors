B7 falsification, written by the agent (Tue Nov  3 23:46 UTC 2026)

Commit `21086438` (worktree `S/wt-b7f`, left clean at `21086438`; nothing committed). Six runs, all through
`S/u35/lead/run.sh`: `b7f_rebuild`, `b7f_probe` (my probe `S/u35r/r1/B7/f/probe/b7f_probe.py`), `b7f_neo` (the LED
unit file at both GC stages: 44/44 each), `b7f_plantA` (planted break A plus the unit file and the probe; restored with
`git checkout -- src/asy_neopixel_driver.py`), `b7f_sizes`, `b7f_fw` (`S/u35r/r1/B7/f/probe/fw3.sh`: dev's image at the
tree, at `15b2175b` and at `d6bc7617` by planting those revisions' differing files, every one restored by its trap).

Chip facts: the WS2812 datasheet is **not available to me**. The worktree's `datasheets/` submodule is not checked
out, and `/home/user/sensors/datasheets/` has no WS2812 file (bmp3xx, fram, isl29125, pico w, scd30 and sgp40 only).
So "a WS2812 shows its last latched frame until new data arrives" is unverified against the PDF. I rely on it only for
claim 5, and the run there shows the firmware writes no frame after the cancel either way. SCD30 facts come from
`S/ds/Sensirion_CO2_Sensors_SCD30_Datasheet.txt:211` ("RDY Data ready pin. High when data is ready for read-out") and
`S/ds/Sensirion_CO2_Sensors_SCD30_Interface_Description.txt:312-313` (1.4.2, "Stops the continuous measurement").

## Per claim

1. **REFUTED.** `SPECIFICATION.md:6607-6608` still says, in F.2's "one timeout mechanism" paragraph about
   `asyncio.wait_for_ms()`: "the NeoPixel overlay's periodic rewrite takes its refresh cadence as its timeout". So a
   periodic rewrite and its `wait_for_ms()` remain in SPECIFICATION.md. The sentence came in at `72b12815` and was never
   touched, and its "Six waits map no sentinel" count (:6602-6603) included that wait. The rest of the claim holds:
   - `src/` and buildgen have no `_OVERLAY_REFRESH_MS` and no overlay `wait_for_ms()`. `src/asy_neopixel_driver.py:68-75`
     waits on the flag alone. Part N has no `led.overlay_refresh_ms` row.
   - The cancel half holds: `test_the_overlay_task_writes_on_a_change_alone_and_any_cancel_ends_it`
     (`tests/test_asy_neopixel_driver.py:246-268`) passed at both stages (`b7f_neo`).
   - Minor wording point: the task also writes when nothing changed. Every `on()` writes, even when the overlay is
     already on, and so does every ramp's end (:108). SPEC A.4's "on a change alone (... a ramp's end)" is the exact
     statement.
2. **STANDS.**
   - `_clamp_byte` (:39-43): NaN raises `ValueError` and ±inf `OverflowError` in `int()`, and both map to 0. The test is
     at `tests/test_asy_neopixel_driver.py:706`.
   - The ramp's floor `not t >= 0.1` (:84-85) catches NaN and -inf, and +inf plays as one step (:86-89). Both are
     covered by tests, which passed in `b7f_neo`. `_MAX_SIGNAL_S` is gone.
   - REST bounds T to 0.5-60 and R/G/B to 0-255 (`src/asy_webserver_service.py:134-139`). The chained comparison in
     `checked_float` / `checked_int` (`src/asy_config_manager.py:165,179`) refuses NaN and inf.
   - `FlashDur` is 0.5-10 (`src/asy_notification_service.py:100`), and a stored value is validated at load
     (`asy_config_manager.py:541-548`).
   - The colour weights are 0/1, fixed in `buildgen/signals.py:22-26`, and `FlashBri` is 1-255.
3. **STANDS.**
   - `request_signal` (:155-163) waits while the slot is set and the deadline is ahead, then always stores, sets and
     answers True.
   - Past the deadline it overwrites the slot, so the last request wins. A running ramp read its values at its start
     (:83, :92-94), so it is unaffected, and its end-of-ramp `clear()` (:107) drops the late request. That is the only
     way a request is lost.
   - Only the notification monitor calls it (`asy_notification_service.py:288`). That caller is sequential, and
     `led_signal` refuses while the slot is set, so the slot is held by at most one ramp of 60 s or less (REST) ahead
     of the request.
   - Caveat, not a refutation: the 120 s is wall time. A requested 60 s ramp that loop lag stretched past 2× would
     lose the queued flash. Part N's `led.signal_wait_ms` row still owes that measurement.
4. **STANDS.**
   - `git grep` (excluding `arduino/` and `audit/`) finds no `NOTIFY_SIGNAL_DROPPED`, `_sink_is_default` or
     "signal dropped" in src, tests, buildgen, js, html, mockdata or docs.
   - `buildgen/error_catalog.json:15` keeps notify's W bands `[[44, 47], [67, 68]]`, and `SPECIFICATION.md:3734`
     agrees.
   - `_trigger_signal` (:285-290) logs `_ERR_CALLBACK` (E14) on a raise, the same site and shape as
     `25caf528:src/asy_notification_service.py:223-228`. Its `errno=13` there is the pre-catalog local number;
     `25caf528` has no `error_catalog.json`.
5. **REFUTED** (the last sentence; `b7f_probe` P1).
   - The setup was a real `SystemService` supervising the driver's two tasks, then a `LightCmdLED`-shaped
     `led_signal(0, 200, 0, 10.0)`, then `reboot_bootloader()` 1.5 s later.
   - Result: accepted, the shutdown cancelled the signal task mid-ramp, and the reset was armed. The last frame at the
     arm was **(0, 78, 0)**, no frame followed in the next second, and the slot was still set.
   - Why: the controlled shutdown cancels every supervised task (`src/asy_system_service.py:439-447`) and then runs
     `machine.bootloader()` after `_RESET_DELAY` 4 s (:470, :63). Nothing writes black, so the pixel stays at a
     mid-ramp colour for as long as the unit sits in BOOTSEL. After a `reboot`, `resetconfig` or `erasefram` it stays
     lit until the next boot's signal task writes its start frame.
   - Planted break A (`b7f_plantA`: a cancel or failure clears the slot and writes black, the `d6bc7617` `finally`'s
     effect) gives (0, 0, 0) at the arm. That `finally` (`d6bc7617:src/asy_neopixel_driver.py:115-119`) is what this
     unit removed. `25caf528` and the deployed legacy (`legacy/firmware/python/CommonDrivers/system_service.py:44-51`
     resets with the ramp still running) behave the same as `21086438`, so this is a reintroduced defect.
   - The rest stands. The end-of-ramp order (:105-108) holds. P2 checked a restart mid-ramp: a cancel left (10, 0, 0)
     with the slot set, and the restarted task wrote black first, replayed all 50 red frames, then black, then the
     overlay grey.
6. **STANDS.**
   - `led_signal` (:137-144) refuses while the slot is set, whether queued or running. The test
     `test_led_signal_is_refused_at_once_while_a_ramp_runs_and_nothing_is_queued` passed.
   - The REST callback `buildgen/codegen.py:260-264` is untouched (the `d6bc7617..21086438` codegen diff is the status
     callback only), and `src/asy_webserver_service.py` is unchanged.
7. **STANDS.**
   - `_notification_status` returns `{"PauseTime": ...}` alone (`buildgen/codegen.py:301-305`).
   - In the rebuilt `build/generated_src/definitions/{dev,wozi}.json`, PauseTime appears once: in the notification
     section, `kind` number, `statusPath` `["notification","PauseTime"]`.
   - The notification instance was never in `sensors=` (`build/generated_src/sensortask_dev.py:161`,
     `sensortask_wozi.py:147`).
   - No `Triggered`, `State`, `TS`-row or `NotifyState` remains outside `audit/`.
   - `NOTIFY()` with no fields is stored as `_datastruct` and nothing generic reads it.
8. **REFUTED** (`b7f_probe` P3).
   - Run: a real `SCD30_Reader` read 2000 ppm (sample TS 1800000000), then a real `PUT ContMeas false` answered
     `{'ContMeas': 'Valid'}`. The sample stayed `(2000.0, ..., FRCState 0, None, TS 1800000000)`, and the next
     notification cycle flashed red: 49 frames, peak (200, 0, 0).
   - Why: with continuous measurement stopped, RDY never rises. The read cycle runs only on RDY's rising edge
     (`src/asy_scd30_driver.py:538-541`) or while RDY is held high (:434-449), so the stopped SCD30 neither re-stamps nor
     clears its sample. `_frc_not_measuring` republishes it "with its own TS" (:376-379).
   - Had a cycle run anyway (data-ready 0), the probe shows it re-stamps the old 2000 ppm with the new TS (:828-829,
     :508-511). Either way the stopped SCD30 drives a flash every `FlashInterval` indefinitely, from a value measured
     before the stop.
   - At `d6bc7617` the three-hour age bound ended exactly this case, which is what the removed twin test
     `test_a_stopped_scd30_ends_its_alerts` pinned. The premise "every producer re-stamps its sample every cycle" is
     false for a stopped SCD30.
9. **STANDS.**
   - Every TOML wires CO2/Hum (SCD30) and VOC (SGP40), all numbers or None. buildgen allows only `get_data()` fields
     of TOML instances (`buildgen/validate.py:904-942`), and none of those holds a string.
   - A NaN compares False both ways (:220-221; `test_check_one_nan_value_never_triggers`).
   - E15 is logged for a raising producer (:207-210).
   - Notes: the catalog text for E15 still reads "or returned a non-numeric field" (`buildgen/error_catalog.json:39`;
     see claim 15). `test_check_one_never_raises` dropped its non-numeric inputs, and `_check_one` now does raise for
     them (`float()` at :220 is outside the `try`). That is consistent with this claim.
10. **STANDS.**
    - :236-243 log W13 on every failing cycle. By the newest-entry rule (`src/asy_print_log.py:176-184`) each call
      counts and writes through but takes one slot, and `wrn_s` prints its line (:251-255).
    - `test_an_unreadable_own_config_logs_one_entry_and_one_line_per_cycle` pins this.
    - Edge, not product-reachable: a cache missing only a threshold key logs one E26 per signal per cycle (:213-215).
11. **STANDS.** `setup()` (:168-171) returns None. `SetupFct` answers are "never read"
    (`src/asy_base_classes.py:50`), and `run_setups` (`asy_system_service.py:687-690`) ignores them. No other caller
    reads the value (`git grep`).
12. **STANDS.** The constructor (:47-53) defaults to `_NEOPIXEL_FREQ_HZ` / `_LED_OVERL_BRI`. `_build_args_neopixel`
    (`buildgen/codegen.py:543-546`) passes the pin and the FRAM kwarg only. `ALLOWED_INSTANCE_FIELDS["neopixel"]` is
    `{"pin"}` (`buildgen/buildspec.py`), and `@tunable` tags feed the Part N register, not the TOML.
13. **STANDS.** The three lines are at :138, :156 and :162, the same positions as `25caf528` (`led_signal`'s first
    statement; `request_signal`'s first statement and after the set).
14. **REFUTED.**
    - Planted break A (`b7f_plantA`) changes only the abnormal path: a cancelled or failed ramp frees the slot and goes
      dark, so a restart replays nothing. The probe confirms the break took effect (P2 replayed 0 red frames, P1 was
      dark at the arm), yet `tests/test_asy_neopixel_driver.py` passed 44/44.
    - The restart behaviour that claim 5 asserts is therefore pinned by no test. The tests that pinned the restart path
      were removed, not changed, and nothing replaced them. They are not in the claim's list:
      - `test_cancelling_the_signal_task_mid_ramp_leaves_the_pixel_dark_and_the_slot_free`
      - `test_a_frame_write_failing_mid_ramp_ends_the_task_with_the_slot_free`
      - `test_a_restarted_overlay_task_reapplies_the_overlay`
      - `test_a_signal_task_ended_mid_ramp_restarts_dark_and_restores_the_overlay`
      - `test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry`
      - the twin's `test_a_restarted_signal_task_ends_dark_with_the_overlay_restored`
    - The supervisor's restart of the LED signal task, with its one SYSTEM entry, now has no test at any tier.
    - `test_a_stopped_scd30_ends_its_alerts` went together with a behaviour that was real (claim 8).
    - The other changes the brief named are mechanical:
      - the status-group test (set equality; duplicates are caught by `_duplicate`)
      - the module-double surface (the role filter widens the allowed set by exactly `get_data` / `get_dict_data`,
        computed from the six other `SensorReaderConfig` subclasses)
      - the measurement guard (six `_FIELDS` modules, exact)
      - the Wi-Fi "(a)" check: with only the overlay task started and `_led` None from the connect loop's LED config,
        no frame is written, so the guard had to go. The check is now vacuous but still fails on any lit frame.
      - the one-start-frame expectations
      - the drop and State tests
15. **REFUTED.** Three stale descriptions remain:
    - `SPECIFICATION.md:6607-6608`: the overlay's periodic rewrite (claim 1).
    - `SPECIFICATION.md:8291`: the put-matrix's `PauseTime` probe has "the remaining time read on the status page", but
      the Status page has no such row since `15b2175b`.
    - `buildgen/error_catalog.json:39`: E15's text "or returned a non-numeric field". That case was removed, and the
      only other E15 site, `asy_sgp40_driver.py:301`, logs a raise only. The website shows this text.

    BACKLOG.md has nothing stale for these items.
16. **STANDS** (`b7f_sizes`, `b7f_fw`).
    - `src/` bytecode: `d6bc7617` 195,511 B, `15b2175b` 194,689 B (-822 B), `21086438` 194,820 B.
    - Against `d6bc7617`, only the two modules changed, and both shrank: LED 2,565 → 2,392 B, notification
      4,664 → 4,015 B. `21086438` changes the LED module alone, 2,392 → 2,523 B, with three inserted source lines.
    - Dev `imageFreeBytes`: `15b2175b` 58,956 B, `d6bc7617` 57,868 B. The head itself reads 58,772 B.

## Outside the claims

- **(b) defect in the deliverable: the `web-put-matrix` CI job's PauseTime case now throws.**
  - `tests_js/live-backend-put-matrix.test.js:87` reads the remaining pause from the Status page through
    `statusGroupKey(defs, "PauseTime")`.
  - That function (:270-277) throws "the status section has no group for PauseTime", because no status group lists a
    readonly PauseTime any more. jq over the rebuilt `build/generated_src/definitions/{dev,wozi}.json` finds none.
  - The case is driven (`ACTION_PROBES.PauseTime`, :83-92; the job is `.github/workflows/ci.yml:188-223`), and the file
    is not in `npm run test:unit`, so the gate cannot see it.
  - Shown statically. I did not run the browser tier.
- **The owner's wording on the Status page row.** The recorded decision (owner rulings, 2026-11-03 20:35: "Triggered,
  State and TS leave /status with the Status page's 'Notification Status' group ... PauseTime stays where it is")
  removed the page's "Remaining Pause Time" row as well. That row was present at `25caf528` and `d6bc7617`. The value is
  still shown in the Notification section's pause control through `statusPath`, as legacy's LED page showed it. Worth one
  line to the owner, since "only keep pause time" can also be read as keeping that row.
- **Reintroduced, matching `25caf528`/legacy: a restarted overlay task no longer rewrites the overlay.**
  `d6bc7617`'s start-of-loop `_overlay_start.set()` is gone, and `test_a_restarted_overlay_task_reapplies_the_overlay`
  went with it. The overlay task can end only by a raise in its write path (an allocation), so this is low weight.
- **Leftover twin knobs.** `digital_twin/neopixel.py:23,33,60-67` keeps `raise_on_write` and `power_dip` / `displayed`,
  and `digital_twin/README.md:162` documents `power_dip()`. Since the refresh and restart tests went, only the fake's own
  self-tests use them (`tests/test_digital_twin_network_neopixel.py:515-524,535-542`). The unit fake's `raise_on_write`
  was removed, so the two fakes now differ.
