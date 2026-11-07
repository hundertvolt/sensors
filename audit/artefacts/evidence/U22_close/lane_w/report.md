# U22 lane W final report

Branch `audit/u22-w`. Commits: WIP W1 `247cc03`, the merge of `audit/u22-api` (`4f8264c`) `5ecadf9`, W2 final
`b283d81`, fix round `6fbbf2c` (final). Files: `src/asy_wifi_service.py`, `tests/test_asy_wifi_service.py`, `buildgen/error_catalog.json`,
`tests_scripts/test_fault_or_warning_never_both.py`. No other file was edited.

## Step table

| row | M-id | status | note |
|---|---|---|---|
| 2 | M.GEN.034 (2) | applied | W80 is now `WLAN_SILENT` with its number kept and the row 2 text. E65 `WLAN_OFF` is `"retired": true` with its name and text kept (A-24). W77 has the row 2 text. A-8's `status.NotifyState` table is added with §3's five texts, verbatim. |
| 10 | M.SRC_NET.077 (2) | applied | Removed: `_ERR_WLAN_OFF`. Renamed: `_WRN_WLAN_DEACTIVATED` → `_WRN_WLAN_SILENT = const(80)`. Added: `_PHASE_SILENT = const(4)` with the packet's comment. The `_PHASE_DEACTIVATED` and `_LED_DEACTIVATED_ON_S` comments now say "no readable Wi-Fi configuration"; the LED pair keeps its `_S` names and tags (A-25). Added beside `_STAT_JOINED_NO_IP`: `_STATIONS_UNSET = const(32)`, untagged, with the packet's trailing comment; citations re-read at v1.29.0: `network_cyw43.c:377-380`, `cyw43_ctrl.c:719-723`. |
| 12 | M.SRC_NET.081 (2) | applied | `_get_hotspot_stations()` answers `None` for a raise or for exactly `_STATIONS_UNSET` entries; any other list, `[]` included, is returned as read. Both comments are the packet's. Deviation 5 below. |
| 13 | M.SRC_NET.087 (2) | applied | `_hotspot_timeout_loop()` dispatches by phase. Silent: it sets `_silent_attempt_due = True`, and a fire while one is due adds none. Every other phase: `_on_hotspot_window_end()`. |
| 14 | M.SRC_NET.223 (1)-(7) | applied | Follows the defaults of A-2 and A-3. Two additions: the scan finding below (`_run_silent_mode() -> bool` and the loop's idle-iteration streak rule), and deviations 1-4 and 6. |
| 20 | M.SRC_NET.224 | applied | A `None` answer persists `wrn_s("Hotspot stations unknown, counted as no client", wrnno=_WRN_WLAN_STATIONS_UNKNOWN)`, then runs `_hotspot_client_absent()`. The packet's comment line sits at the branch. |
| 43 | M.TEST_UNIT.346 (1)-(7) | applied | 260 tests (base 232). Every family is listed under "Tests" below. |
| 47 | M.TSC.231 | applied | The `_deactivate_wlan_permanently` pair and its reason are gone. The scan finds no new mixed pair: `test_fault_or_warning_never_both.py` passes 11/11 on W1 and on the final tree. |

Nothing from the W rows had already landed on the base tree. HEAD's other deactivated tests (the no-configuration
state) hold unchanged, as the plan says.

## API end states (for T, P, D)

- Phases: `_PHASE_STA_SEEKING = 0`, `_PHASE_STA_ESTABLISHED = 1`, `_PHASE_HOTSPOT = 2`, `_PHASE_DEACTIVATED = 3` (only "no readable Wi-Fi configuration"), `_PHASE_SILENT = 4`. While silent, `is_hotspot_active()` is `False` and the snapshot's `Mode` is `"STA"`.
- Flags in `__init__`'s state block: `self._reconnect_fresh` (set by `reconnect_wifi()`, read and cleared by `_handle_reconnect_trigger()`) and `self._silent_attempt_due` (set by the watcher while silent; cleared at each silent entry and by the attempt in `_run_silent_mode()`).
- Methods:
  - `_on_hotspot_window_end() -> None`: deinits the timer, clears `_hotspot_timer_running`, cancels the flash and sets `_reconn_wifi`; it does not set the fresh flag.
  - `reconnect_wifi()`: calls `_on_hotspot_window_end()`, then sets `_reconnect_fresh = True`.
  - `async _arm_hotspot_timer() -> bool` (**async**, deviation 1): the one arm path, shared by `_hotspot_client_absent()` and `_run_silent_mode()`. It returns `False` after a persisted `_ERR_TIMER`.
  - `async _run_silent_mode() -> bool` (**bool**, deviation 2): `True` when an attempt ran. It arms the period if none runs. When one is due, it makes one attempt under `wifi_mode_lock`: `_attempt_sta_connect()` unless `isconnected()` already, then `_handle_sta_connection_result()`. A link deinits the timer.
- Stations: `_get_hotspot_stations()` returns `None` for a raise or for exactly 32 entries. A `None` persists one W77 and runs `_hotspot_client_absent()`.
- Console texts: W80 "No WLAN connection after the hotspot ran - silent mode, one connect attempt per hotspot period"; W77 "Hotspot stations unknown, counted as no client".

## Deviations (each conservative and reversible; decided on the owner's behalf, agent, 2026-10-08/12)

1. `_arm_hotspot_timer()` is `async`, because it awaits the persisted `_ERR_TIMER`. §3 writes it without `async`.
2. `_run_silent_mode()` returns `bool` instead of §3's `-> None`. This closes the scan finding (class 6 in the scan record below): an idle silent iteration made no radio call, yet it decremented the hardware streak, so a connect that always raises never reached the device rung or the give-up. `_connect_loop()` now runs `_error_check()` only when the iteration made an attempt or `_hw_op_failed` is set (for example, a failed uptime-tick re-arm); an idle silent iteration neither counts nor heals the streak. No other phase changes. **Doc fact for D (C.7's `_error_check()` bullet / C.8):** "in the silent mode an iteration with no attempt due is no evidence: the streak neither counts nor heals".
3. Silent-entry order: phase, the due flag cleared, the flash cancelled and `_led_off()` all come before the W80 `wrn_s`. The packet lists the `wrn_s` first. This matches the sibling hotspot branch in the same function, and the dark guard is active before the first await.
4. `_run_silent_mode()` attempts only `if not isconnected()`, the same shape as `_run_sta_mode()`. A radio that linked by itself is therefore taken as a link at the next period.
5. In the stations read, the stub's `type: ignore` moved from the `return` to the typed read (`stations: list[tuple[bytes]] = ...  # type: ignore[assignment]`), because `len()` needs the list type. Its two comment lines moved with it.
6. `reconnect_wifi()` reuses `_on_hotspot_window_end()` instead of repeating its four statements. The comment is the packet's two lines plus one saying so.
7. Tests: the A-4 regression drives the real request-path hook runner `asy_api_response.handle_set_cmd()`. The U19 integration test's local `until`/`next_stations_check` moved to module level as `_until`/`_next_stations_check`, and `_hotspot_client`/`_stop_all` are shared with the three new integrations. This is a refactor; behaviour is unchanged.
8. The W1 comment in `_run_silent_mode()` contained the text `.scan(`, which the new non-blocking guard (no `.scan(` in the source) caught in W2. Reworded.

## Facts owed to other lanes

- **D** (SPECIFICATION.md):
  - `@tunable` tags: none added, renamed or withdrawn, in `src/` or in the test file. Every new loop bound in the tests is a literal yield count.
  - `wifi.wlan_down_settle_s`: its only site is now `_switch_wlan_mode()`, because the deactivation site is gone. Row 21 should name only that site.
  - `wifi.led_deactivated_on_s`/`_off_s`: the no-configuration pattern; names and values unchanged.
  - F.1: `_STATIONS_UNSET = 32` (`network_cyw43.c:377-380`, `cyw43_ctrl.c:719-723`, v1.29.0).
  - C.8 hold table: `_run_silent_mode()` holds `wifi_mode_lock` only for the attempt (the connect and its ≤ 10 × 0.5 s poll), never across the wait between periods.
  - C.9: the window's `PERIODIC` timer is also the silent period, armed through `_arm_hotspot_timer()`.
  - Streak rule: deviation 2.
- **E**: the console texts above; the silent mode and the fresh-boot state as §3 states them. Nothing else changed.
- **Lead**:
  - The allow-list rows the rewrite retired, `_decision_vocab_allowlist.txt:322` and `:323`, were already dropped in `4f8264c`. No other allow-list or citation row keys a comment I rewrote.
  - No new mixed fault-or-warning pair.
  - New raises in `src/`: none.
  - Any-baseline: `test_mypy_any_baseline.py` is green on the final tree. The new test code uses `Any` only where the fake `network.WLAN` needs it (`_RaisingConnectWLAN.build`, `_silent_attempt`'s `sta`), in the file's existing idiom.
- **Website inputs**: the catalog changed (W80's name and text, W77's text, E65 retired, the `NotifyState` table), so every device's generated definitions (`errcount` codes) change. They are regenerated in this worktree. `frozen_modules/frozen_html.py` holds none of these texts (grep), but the lead's rebuild before full-graph runs still applies.
- **T**: nothing beyond §3. `_run_silent_mode()` now returns a `bool`, which a caller can ignore. The streak rule matters only to a twin case that makes a silent attempt raise.

## Tests

### Written first and seen failing on the tree

**W1.** The new test file ran against the unchanged product (a copy with `_PHASE_SILENT = 4`, `_STATIONS_UNSET = 32`). Result: 20 failed, 224 passed (`u22w_runs/seen_failing_w1.log`, lines in `seen_failing_w1_lines.txt`).

- AttributeErrors on the missing members: `_run_silent_mode`, `_on_hotspot_window_end`, `_reconnect_fresh`, `_silent_attempt_due`, `_arm_hotspot_timer`.
- Phase asserts: `_PHASE_DEACTIVATED` where `_PHASE_SILENT` was expected.
- Stations: a failed check ran no transition, and the 32-entry answer was read as a list.
- `KeyError: WLAN_SILENT` in the U19 integration.

**W2.** The new tests ran against the pre-change module (`18a02f8`'s `asy_wifi_service.py` ahead on MICROPYPATH). Result: 13 failed, 2 passed (`seen_failing_w2_lines.txt`).

- AttributeError `_run_silent_mode` in the error-handling, resilience, non-blocking and LED cases.
- Integration 1: "the second streak must go silent". Integration 2: "the hotspot must reopen". Integration 3: "the unfilled answer must arm the window".
- The stations-raise case: `[False, False, False]` where `[False, True, False]` was expected.

**The streak plant.** The rewritten raising-attempt test ran against the W2-pre-edit module and failed with "the streak never reached its give-up", streak `[0, 0, 0, 0]`. The history alternated E62/E1 with no rung. It passes after the edit.

### Guards (pass at once)

- `test_is_hotspot_active_false_in_silent_phase` and the dynamic case's silent row.
- `test_a_restart_in_the_window_end_streak_still_clears_the_hotspot_use`.
- `test_a_settings_change_cannot_reach_the_no_configuration_state` (A-4).
- The text half of `test_the_wifi_service_never_scans`; its run half needs the silent mode.

### Mutation bites on the final product

Each mutation made its named tests fail. Run with `u22w_tools/mut.sh`; logs in `u22w_runs/mut/*`.

| mutation | tests that failed |
|---|---|
| each of the three dark guards removed | the LED-helper test (both LED tests for the toggle guard) |
| `_on_sta_disconnected()`'s silent guard removed | the entry and failed-attempt tests |
| the keep-silent condition in `_handle_reconnect_trigger()` removed | the reset sibling |
| the 32-entry check removed | the three stations tests |
| the fresh flag ignored, or not set | the identity, settings-beside-window-end and reconnect tests |
| the dispatch made always window-end | the watcher and period tests |
| the link's deinit removed | the period test |
| the watcher calling `reconnect_wifi()` | the window-end tests |
| the entry's due-flag clear removed | the first-attempt test |
| the lock held over the refresh wait | the non-blocking test |
| re-arm every iteration | the 500-period test |
| the restart dropping the silent phase | the restart test and the raising-attempt test |
| the unknown branch not running absent | the stations-raise test and integration 3 |

### Families of row 43 (all in `tests/test_asy_wifi_service.py`)

- **(1) Function.**
  - `test_a_second_streak_enters_the_silent_mode_once`
  - `test_a_silent_period_runs_one_attempt_and_a_link_is_a_normal_connection`
  - `test_a_failed_silent_attempt_stays_silent_without_a_streak`
  - `test_no_attempt_runs_between_periods`
  - `test_the_identity_hook_lands_in_the_fresh_boot_state` (sources: hotspot, silent, established, and seeking within the window-end streak)
  - `test_the_window_end_keeps_its_meaning`
  - `test_a_settings_trigger_beside_a_window_end_wins`
  - `test_the_watcher_dispatches_by_phase`
  - `test_get_hotspot_stations_reads_the_unfilled_answer_as_a_failed_check`
  - `test_an_unconfirmed_stations_check_counts_as_no_client`
- **(2) Error handling.**
  - `test_a_failed_period_arm_is_persisted_and_retried_in_the_silent_mode` (`OSError` ENOMEM and `MemoryError` through `_RaiseOnArm`, so no "MemoryError" text reaches the output)
  - `test_a_raising_silent_attempt_feeds_the_hardware_streak_and_keeps_the_mode` (real period cadence; device rung, give-up and restart all keep silent)
  - `test_a_raising_stations_query_under_a_client_arms_the_window_until_the_next_good_check`
- **(3) Resilience.**
  - `test_500_silent_periods_stay_silent_and_bounded` (500 attempts; slots `[WLAN_SILENT, WLAN_NO_AP]` after periods 1 and 500; `ErrCount` 501; `arms` 1; no flash or DNS task; one interface)
  - `test_a_restart_in_the_silent_mode_keeps_it_dark_and_re_arms_the_period`
  - `test_a_restart_in_the_window_end_streak_still_clears_the_hotspot_use` (guard)
  - `test_a_dropped_silent_period_fire_is_recovered_by_the_next_period`
  - `test_the_first_silent_attempt_waits_one_period_after_the_entry`
- **(4) Self-healing**, on the running loop and watcher tasks under `_HotspotRadio`:
  - `test_integration_a_unit_goes_silent_after_its_second_streak_and_rejoins_when_the_router_returns`
  - `test_integration_new_credentials_over_the_hotspot_reopen_it_once_more`
  - `test_integration_an_unfilled_stations_answer_never_holds_the_hotspot`
- **(5) Non-blocking.**
  - `test_the_wifi_service_never_scans` (source text, plus a recorded radio `scan` that must stay unused)
  - `test_the_silent_wait_holds_no_lock_and_yields` (a counter and a lock-taker both advance between every two iterations; the attempt holds the lock)
- **(6) LED.**
  - `test_the_silent_mode_keeps_the_led_dark_until_a_link` (LEDWifiOn on and off)
  - `test_no_led_helper_lights_while_silent`
  - `test_turning_the_wifi_led_on_while_silent_lights_nothing_until_the_link` (the LEDWifiOn push while silent)
  - HEAD's no-configuration pattern tests hold.
- **(7) Regression.**
  - Rewritten in place:
    - `..._goes_silent_when_hotspot_already_tried`
    - `test_an_unconfigured_unit_never_goes_silent_over_two_hotspot_windows`
    - `test_a_configured_ssid_whose_second_streak_fails_goes_silent`
    - `test_the_first_streak_persists_its_fallback_and_the_second_its_silent_entry_once`
    - the 32-entry case in `test_get_hotspot_stations_answers_none_...`
    - `test_a_failed_stations_query_counts_as_no_client`
    - `test_reconnect_wifi_sets_the_trigger_...`, which also asserts the fresh flag
    - `test_hotspot_timeout_watcher_ends_the_window_when_woken`
    - the comments at the watcher tests
    - the U19 test's W80 code is now `WLAN_SILENT`
  - Added: the silent reset sibling, and the silent case in `is_hotspot_active()` with its section comment ("All five").
  - Deleted with its function: `test_deactivate_wlan_permanently_...`.
  - A-4's regression: `test_a_settings_change_cannot_reach_the_no_configuration_state`.

### Wall times at `nice -n 19`, `tests/test_asy_wifi_service.py`

| tree | stage e (gc -1) | stage f (32768) | settrace | result |
|---|---|---|---|---|
| base `18a02f8` | 20.1 s | 21.1 s | 20.5 s | 232/232 |
| W1 `247cc03` (re-run after the restart) | 20.1 s | 20.5 s | 20.0 s | 245/245 |
| W2 final | 19.9 s | 21.5 s | 20.7 s | 260/260 |

Zero MemoryError, zero "memory allocation failed", zero tracebacks and zero unretrieved-task reports at every stage.

### Every file that constructs a `WifiService`, final W2 src, both GC stages

| file | e (gc -1) | f (32768) |
|---|---|---|
| `test_neopixel_wifi_integration.py` | 6/6 passed, 1.6 s | 6/6 passed, 1.9 s |
| `test_ntp_fram_system_integration.py` | 12/12 passed, 7.9 s | 12/12 passed, 8.1 s |
| `test_ntp_wifi_dns_integration.py` | 13/13 passed, 1.5 s | 13/13 passed, 1.6 s |
| `test_readiness_gates.py` | 14/14 passed, 0.2 s | 14/14 passed, 0.3 s |
| `test_setter_microdot_integration.py` | 39/39 passed, 3.9 s | 39/39 passed, 4.2 s |
| `test_sensortask_arzi.py` | 88/88 passed, 46.4 s | 88/88 passed, 64.0 s |
| `test_sensortask_dev.py` | 88/88 passed, 73.7 s | 88/88 passed, 102.3 s |
| `test_sensortask_grkizi.py` | 88/88 passed, 44.9 s | 88/88 passed, 61.8 s |
| `test_sensortask_klkizi.py` | 88/88 passed, 45.4 s | 88/88 passed, 62.6 s |
| `test_sensortask_schlafzi.py` | 88/88 passed, 46.5 s | 88/88 passed, 61.0 s |
| `test_sensortask_wozi.py` | 88/88 passed, 52.4 s | 88/88 passed, 70.0 s |
| `test_digital_twin_bus_hazard_concurrency.py` | 20/20 passed, 154.6 s | 20/20 passed, 158.4 s |
| `test_digital_twin_real_website_integration.py` | 9/9 passed, 11.4 s | 9/9 passed, 12.7 s |
| `test_digital_twin_run_generic_integration.py` | 26/26 passed, 1.4 s | 26/26 passed, 1.5 s |
| `test_digital_twin_sensortask_integration.py` | 15/15 passed, 61.6 s | 15/15 passed, 64.9 s |
| `test_digital_twin_uart_link.py` | 19/19 passed, 69.8 s | 19/19 passed, 83.1 s |
| `test_digital_twin_construction_arzi.py` | 3/3 passed, 3.2 s | 3/3 passed, 3.6 s |
| `test_digital_twin_webserver_concurrency_arzi.py` | 20/20 passed, 41.6 s | 20/20 passed, 45.8 s |
| `test_digital_twin_construction_dev.py` | 3/3 passed, 3.6 s | 3/3 passed, 4.3 s |
| `test_digital_twin_webserver_concurrency_dev.py` | 20/20 passed, 45.6 s | 20/20 passed, 52.8 s |
| `test_digital_twin_construction_grkizi.py` | 3/3 passed, 3.2 s | 3/3 passed, 3.7 s |
| `test_digital_twin_webserver_concurrency_grkizi.py` | 20/20 passed, 42.0 s | 20/20 passed, 46.0 s |
| `test_digital_twin_construction_klkizi.py` | 3/3 passed, 3.2 s | 3/3 passed, 3.6 s |
| `test_digital_twin_webserver_concurrency_klkizi.py` | 20/20 passed, 42.2 s | 20/20 passed, 46.1 s |
| `test_digital_twin_construction_schlafzi.py` | 3/3 passed, 3.3 s | 3/3 passed, 3.6 s |
| `test_digital_twin_webserver_concurrency_schlafzi.py` | 20/20 passed, 41.3 s | 20/20 passed, 45.9 s |
| `test_digital_twin_construction_wozi.py` | 3/3 passed, 3.3 s | 3/3 passed, 3.9 s |
| `test_digital_twin_webserver_concurrency_wozi.py` | 20/20 passed, 42.9 s | 20/20 passed, 47.9 s |

All 56 runs exited rc=0, with zero MemoryError and zero "memory allocation failed". The only unretrieved-task
reports are the 10 in `test_digital_twin_sensortask_integration.py` at each stage: `RuntimeError("injected status
fault")`, which that file plants in `SystemService`'s status loop by design. The U21 gate1 log has the same 10.
`test_digital_twin_bus_hazard_concurrency.py` took 154.6 s and 158.4 s under the shared load (64-66 % of the 240 s
bound). It is not my file and I did not change it, but the lead should know. An earlier stage-e pass of the first 7
files, all green, was stopped by pid because the streak edit superseded it. These files were run on W2's final
src, before the commit; the commit changed no file they read.

### L0 and tools, final tree

- `tests_scripts/test_digital_twin_boot_contiguity.py` (§8: two new attributes on a boot survivor): 32 passed, 5 skipped. The skips are "<device> builds no UART link", the expected per-device skips. 15 s.
- 14 of the 15 L0 files in `u22w_runs/precommit_w2.log` are green: `test_error_catalog` (33), `test_fault_or_warning_never_both` (11), `test_decision_vocabulary` (6), `test_citations` (15), `test_comment_block_cap` (452), `test_legacy_paths`, `test_import_placement`, `test_code_conventions` (23; D.15 member order holds, the last check run), `test_host_annotations`, `test_lint_ceilings`, `test_mypy_any_baseline`, `test_memory_error_gate_agreement`, `test_buildgen_definitions` (244), `test_api_reference` (75).
- The one red is `test_tunables_register`, and only on P's two tags awaiting D's Part N rows: `src/asy_neopixel_driver.py:38: led.overlay_refresh_ms is tagged but has no SPECIFICATION.md Part N row`; `src/asy_notification_service.py:68: notify.sample_max_age_s is tagged but has no SPECIFICATION.md Part N row`. The §3 "Red checks" list names this one.
- ruff is clean on my three Python files. mypy with a cold cache is clean on all four passes (main no-args 187 files, `src tests tests_hardware/device_scripts` 174, host 199, twin 52), through the temporary `typings` link to `wt-u8/typings`, which is removed before each commit.
- One deviation from the run rules: a second `pytest -rs` of `test_digital_twin_boot_contiguity.py`, run only to read the skip reasons, ran without `unshare -n`. It was 15 s at nice 19, exited and found no failure. It is reported here and was not repeated.

## Silent-failure scan (classes 1-7; `src/asy_wifi_service.py`, the catalog, the allow-list test, the test file)

**Modes checked:**
- STA seeking (each verdict, raise, no-verdict poll); STA established (60 s retry, the `isconnected()` false positive: CLAUDE.md's power-cycle backstop, unchanged).
- Hotspot without a client (arm, failed arm, dropped fire, window end); hotspot with a client (stations rule, a raise under a client, the chip-down answer).
- Silent: entry, each period, a failed and a linking attempt, a dropped fire, a failed arm, a radio that never comes up.
- The unreadable-config state.
- A task restart and a settings change in each; the `LEDWifiOn` push while silent; the LED enabled and disabled in each pattern; the NeoPixel overlay as the `ext_led` (silent drives only `off()`, so the overlay shows dark).
- Pairs: a window end beside a settings change; a period fire during a reconnect; a restart during the window-end streak.

**Findings:**

1. **New, closed here (class 6; mode: silent + radio never up).** Idle silent iterations decremented the hardware streak, so an always-raising `connect()` was persisted every period but never recovered: no device rung, no give-up, silent until a power cycle, with the history churning E62/E1 pairs.
   - Fix: deviation 2. The plant test was seen failing first.
   - Covering step: M.SRC_NET.223 (2) (owns the silent branch).
   - After the fix, the escalation is the existing one: rung, give-up, supervisor restart (silent kept), and the task-failure ceiling's reboot, which is a fresh boot.
2. **Inherently safe (class 3; hotspot with clients).** Could 32 genuine stations be read as the chip-down answer? No. The Pico W datasheet §3.8 says "SoftAP (Up to 4 clients)" (`datasheets/pico w/RP-008312-DS-2-pico-w-datasheet.pdf`), and the driver caps the real answer at the firmware's `maxassoc` (`lib/cyw43-driver/src/cyw43_ll.c:2311-2333`, v1.29.0). A real answer of 32 cannot occur.
3. **Inherently safe (A-3; silent).** `_attempt_sta_connect()`'s empty-SSID branch: the silent mode is entered only after a streak of real attempts (an empty SSID makes none), and no request reaches a silent unit. Recorded, not guarded, as A-3 rules.
4. **Inherently safe (class 4; silent).** The `_handle_sta_connection_result()` value is discarded in `_run_silent_mode()`. It is always `False` there: silent is never ESTABLISHED, and the link path returns `False`. Commented at the line.
5. **Covered (class 5; silent).** A dropped soft callback (full scheduler queue) delays the attempt one period, because `PERIODIC` re-fires (test). A stale due mark left by a fresh reconnect out of the silent mode is cleared at the next entry (test).
6. **Covered (class 1; silent).** A failed period arm (ENOMEM or `MemoryError`) persists one E17 per failure and is retried each iteration (test). The stations query raising is persisted as W77 and counted as no client (tests).
7. **Not a finding (class 7; silent).** `/status` cannot tell silent from seeking (`Mode` "STA", `Connected` false), but no client can reach a silent unit. After the link, the FRAM-backed WIFI history shows W80 and the attempt verdicts.
8. **Covered by the existing design (class 2; long uptime).** The WIFI history ring keeps the newest entries. A silent run spends one slot per verdict code (newest-entry rule; `ErrCount` counts every event). The 500-period test pins the slot count.
9. **Watchdog and non-blocking.** No scan, by source text and by a recorded radio. The lock is free between periods, and both a counter and a lock-taker advance every iteration (test). The silent attempt is one ordinary attempt (synchronous `country`/`hostname`/`active`/`config`/`connect`, then an awaited ≤ 5 s poll), so it starves nothing.

## Runs started (all exited; entered in `u21/RUNS.md`)

Every run below was started by me, ran in my own worktree only, and was confirmed exited (`ps` shows nothing of mine).

- 2026-10-08 (W1):
  - baselines of `test_asy_wifi_service.py` at e, f and settrace;
  - the W1 seen-failing run;
  - 2 full-file runs, each at e, f and settrace;
  - the pre-commit L0 set, file by file;
  - the four mypy passes;
  - the mutation runs `m0`-`m11` (selected tests, through `u22w_tools/mut.sh` and `sel_runner.py`).
- 2026-10-12 (resume): the W1 re-run at e, f and settrace, mypy ×4, and the L0 set before commit `247cc03`.
- 2026-10-12 (W2):
  - full-file runs at e (several during development) and the final e, f and settrace;
  - the W2 seen-failing run against `18a02f8`'s module;
  - the streak plant before and after the fix;
  - mutations `m9` and `m12`-`m15`;
  - the stage-e consumer pass (pid 7672), stopped by pid after 7 green files;
  - the consumer set at both stages (pid 9417, 56 runs, exited);
  - boot contiguity ×2;
  - the L0 set;
  - mypy ×4 and ruff.
- Logs are in `scratchpad/u22w_runs/`; the helper scripts are in `scratchpad/u22w_tools/`.

**Files the lead must run on the merged tree:**
- `tests/test_asy_wifi_service.py` and the 28 consumer files above;
- `tests_scripts/test_digital_twin_boot_contiguity.py`;
- `test_error_catalog.py`, `test_fault_or_warning_never_both.py`, `test_buildgen_definitions.py`, `test_api_reference.py`;
- `test_decision_vocabulary.py` and `test_citations.py`.

The generated definitions change (the catalog), so regenerate the device modules.

## Fix round: `6fbbf2c` (final), on top of `b283d81`

**The fault.** Lane D's scan found it; the lead checked it against the code. It is class 6 (never heals), in the silent mode.

- When `_run_silent_mode()`'s period arm failed (`Timer.init()` refusing with ENOMEM), the failure was persisted as `_ERR_TIMER` and retried every iteration, but `_hw_op_failed` was never set.
- With no period armed, no attempt is ever due, so `_run_silent_mode()` returned `False` every time and W2's streak gate skipped `_error_check()`.
- Result: a silent, unreachable unit with no escalation until a power cycle.

**The fix (agent, 2026-10-12).** A failed silent-mode arm sets `self._hw_op_failed = True` inside `_run_silent_mode()`. This matches the failed uptime-tick re-arm in the same loop. The streak then counts the failed arm and reaches the device rung and the give-up, and the supervisor's restart keeps the silent mode, as for an always-raising `connect()`.
- `_arm_hotspot_timer()` and the hotspot mode's caller `_hotspot_client_absent()` are unchanged.
- The comment is two lines and carries the tag.

**The test (tests first).** `test_a_silent_period_that_cannot_be_armed_feeds_the_hardware_streak` sits in the silent-mode resilience family, beside the raising-attempt case.
- **Setup:** it enters the silent mode through `_register_sta_connection_failure()` with `_RaiseOnArm()` refusing every arm, then runs `_connect_loop()`.
- **Asserts:**
  - the loop returns (the give-up);
  - iterations equal `_err_cnt_internal`, which equals `max_module_error + 1`;
  - the history holds `E TIMER`, `W DEVICE_RECOVERY`, `E GIVE_UP` and `E WLAN_GIVE_UP`;
  - the phase stays silent;
  - once the pool has room, a restart keeps the silent mode and arms the period.
- **Seen failing on `b283d81`:** "the streak never reached its give-up" after 400 loop iterations. The history was only `[WLAN_SILENT, TIMER]` (one TIMER slot whose count kept rising), with no rung and no give-up.

**The hotspot mode (answer only; no change).** The same never-heals pattern holds there for the window:
- **What happens:** a failed arm in `_hotspot_client_absent()` persists E17 and is retried every iteration, but never sets `_hw_op_failed`. The hotspot iteration is evidence, so the streak heals each iteration and never escalates. With no window armed, the window never ends, so STA is never retried automatically: a router back after a power loss is not rejoined.
- **Does the hotspot stay reachable?** Yes. The AP is already up and the captive DNS runs, so a phone that joins it reaches the web page. There it sees the TIMER entries in the WIFI history at `/status`, and can resubmit credentials, which `reconnect_wifi()` turns into the fresh-boot state.
- **The other exits:** a reboot, or a failed uptime-tick re-arm (which does set `_hw_op_failed`). Both draw on the same alarm pool, so exhaustion may well hit the tick too, but nothing guarantees it.
- **Open finding:** for the owner.

**C.7 fact for D (one sentence).** In the silent mode, an iteration with no attempt due neither counts nor heals the hardware streak, unless its period arm (or the uptime tick's re-arm) failed: that failure counts as the iteration's hardware failure.

**Runs** (nice 19, `unshare -n`, one at a time, all exited and logged in `u21/RUNS.md`):

| run | GC -1 | GC 32768 | settrace |
|---|---|---|---|
| `tests/test_asy_wifi_service.py` | 261/261, 19.8 s | 261/261, 21.6 s | 261/261, 20.7 s |
| `tests/test_neopixel_wifi_integration.py` | 6/6, 1.5 s | 6/6, 1.9 s | - |
| `tests/test_digital_twin_wifi_modes.py` | 1/1, 101.3 s | 1/1, 101.6 s | - |

- `test_asy_wifi_service.py`: zero MemoryError, "memory allocation failed", tracebacks or unretrieved reports.
- `test_digital_twin_wifi_modes.py` exists only on `audit/u22-api`. I did not merge it. It ran in my own temporary checkout of `audit/u22-api` at `0a21a54`, whose `asy_wifi_service.py` differs from this commit's only by the fix. That checkout had the lead's `frozen_modules/frozen_html.py` copied in (read only) and its device modules regenerated, and it was removed after the runs.
- ruff: clean. mypy main pass, cold cache: clean in both scopes (no-args 187 files; `src tests tests_hardware/device_scripts` 174).
- The pre-commit L0 set is green except `test_tunables_register`, which is red only on D's rows: `led.overlay_refresh_ms` and `notify.sample_max_age_s` have no Part N row on this branch, because nothing was merged.
