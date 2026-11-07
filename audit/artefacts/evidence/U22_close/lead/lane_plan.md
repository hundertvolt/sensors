# U22 (LED re-check, widened by OR151/OR152) lane plan, v1 (against `wt-u22fold`, HEAD `18a02f8` = U0..U21 closed + the U22 start fold)

Source: `u22/pk/U22_steps.md` (51 numbered steps; the fold parts landing here `:165-268`; carried action texts
`:3246-3634`), `u22/pk/U22.md` (auditor packet, LED harvest `:977-1228`), `u22/pk/lanes.txt` (25 overlap groups),
`wt-u22fold/audit/actions/U22.md` (pilot re-check table `:14-33`, A.U22.01-.04, ledger `:195-201`, open points `:213`),
the fold ledgers `## U22 start fold (2026-10-08)` in `audit/consolidation/M_{DOCS,GEN,HW_BENCH,SPEC,SRC_NET,TEST_UNIT,TSC,TWIN}.md`,
register rows `audit/REGISTER.md:582` (OR151 reading), `:583` ("completely silent"), `:661` (OR151), `:662` (OR152),
`:663` (U26 parked delta), `:234`, `:267`, `:598`, `:613`, `:630`, `:632`, `:642`, `:650`, open findings
`audit/sweeps/open_findings.md:83` (OF-75), `:87` (OF-79), `u22/brief_fold.md` (the fold's scope and its open points),
`u21/lane_plan.md` and `u21/rulings.md` (form). **Every `file:line` below is `wt-u22fold`'s** unless it says "A-L HEAD"
or names the pinned checkout (`/root/pico-toolchain/micropython`, `v1.29.0`; read-only). No U22 path is renamed by
`u11/renames.txt`. Facts marked **(unverified)** could not be checked by reading.

Pinned-source facts this plan relies on (each read for this plan): `WLAN.scan()` waits up to 10 s in
`mp_event_wait_ms()` (`extmod/network_cyw43.c:236-246`), past the 8,388 ms watchdog; `status("stations")` starts
`num_stas` at 32 and returns that many 1-tuples (`extmod/network_cyw43.c:371-388`), and `cyw43_wifi_ap_get_stas()`
returns without touching it when `cyw43_ensure_up()` fails, zeroes it only when the ioctl fails
(`lib/cyw43-driver/src/cyw43_ctrl.c:717-730`); `asyncio.wait_for()` runs `aw` in a runner task and cancels it on
timeout (`extmod/asyncio/funcs.py:7-55`); a task cancel removes a `ThreadSafeFlag` waiter from the `IOQueue`, which
unregisters it from the poller (`extmod/modasyncio.c:208-236`, `extmod/asyncio/core.py:90-110`). The WS2812 datasheet
is readable after a text extraction with a +29 glyph shift (`datasheets/ws2812/WS2812.pdf`): Features, "Built-in
electric reset circuit and power lost reset circuit"; General description, "After the pixel power-on reset, the DIN
port receive data from controller" (OF-75, A-16).

Lanes: **W** (the Wi-Fi service: `src/asy_wifi_service.py` and its unit test, the catalog, the fault-or-warning
allow-list), **P** (the pixel and the notification: both LED modules, their four test files, the notification
`State` published through the generator, `pyproject.toml`), **T** (the tiers that follow W outside its own test file:
the twin's WLAN model and both twin test files, the request-path L1 test, the bench role-reversal file, edit only),
**D** (SPECIFICATION.md, last), **E** (every other doc, last). Waves: **W, P, T** (wave 1, three at once; T's and
P's W-dependent parts start on the API base, §3), then **D, E** (wave 2, together, last).

Standing rules for every lane (as U16-U21): locate each site by its quoted text (packet lines are A-L HEAD); drop any
part already in end form and report it with its line (§6); a change needed only for tree consistency is the smallest
one that keeps today's behaviour; a sentence U22 makes false is corrected at U22 by its owner lane; nothing under
`tests_hardware/` runs (only `pytest --collect-only tests_hardware`); every new or rewritten comment block is at most 3
prose lines; no audit ID or undefined label in permanent text outside `audit/`; decision tags "(owner|agent,
YYYY-MM-DD)" with the owner's words quoted where a text states his decision; a check is never weakened; allow-lists and
pending lists only shrink. `ext/`, `legacy/` and `arduino/` are not touched (`arduino/` never read). The UART wire
format is untouched (no U22 step names `src/asy_uart_*.py`). Staged later-unit parts (U24-U36) are not written.
No toolchain build: U22 changes no C, no override, no Unix variant, no toolchain file (§8).

## 0. Deviations (from the packet's literal staging and its 25 overlap groups), and why

| change | reason |
|---|---|
| packet lanes 4, 18 (`asy_wifi_service.py`, `test_asy_wifi_service.py`), 1 (the catalog), 20 (`test_fault_or_warning_never_both.py`) → **W** | the state machine and its unit test are one module + its test; the catalog's W80 rename and E65 retirement must land with W's constants (`test_error_catalog.py` pairs each `src/` constant with its row), and the allow-list entry goes with the function it names |
| packet lanes 9, 13, 12 (driver, its test, `tests/neopixel.py`), 15 (`test_neopixel_wifi_integration.py`), 10, 14, 16 (notification, its test, `test_notification_neopixel_integration.py`), 19 (`pyproject.toml`), 11 (`scripts/typecheck.sh`) → **P** | the LED pilot re-check is A.U22.01/.02/.04 across both LED modules and their four test files; A.U22.04 also owns the `pyproject.toml` entries (ruff ANN401, the mypy baseline). `tests/neopixel.py` and `scripts/typecheck.sh` get no U22 edit (rows 26, 32) |
| P also takes the notification `State` publication: `buildgen/codegen.py` (`_notification_status()`, one key), `buildgen/definitions.py` (one row), `mockdata/samples.json` (one key), `tests/_sensortask_scenarios.py`, `tests/test_readiness_gates.py` | no packet step names these files, but M.SRC_SENS.037 (1), M.WEB.045 (1) and M.TEST_HELP.041 (8) land at U22 and need them (A-8); `tests_scripts/test_buildgen_definitions.py:245-254` fails a generated status key no definitions row lists, so codegen and definitions move together |
| packet lanes 7 (bench role reversal), 21 (`digital_twin/network.py`), 23, 24 (both twin test files), 17 (`test_setter_microdot_integration.py`) → **T** | every tier that follows W outside W's own file; each consumes W's contract (§3), so one lane owns the consumers; the setter test is the mock tier's request path into the fresh-boot hook |
| packet lanes 3 (SPEC) → **D**; 0 (`README.md`), 2 (`tests_hardware/README.md`), 5 (`DEVICE_REFERENCE.md`), 6 (`CLAUDE.md`), 22 (`digital_twin/README.md`) → **E** | docs last, as U19-U21; `digital_twin/README.md` goes to E (one owner per shared doc), T relays the knob names |
| lane 8 ("(no file)") = row 19 (M.HW_BENCH.124) → **E** | its site names no file ("the role-reversal text (HEAD in 'Known assumptions' and the fourth pass …)"); both passages are in `tests_hardware/README.md` (`:746-756`, `:1028-1031`), which E owns |
| two U22 stages the packet omits: M.WEB.045 (1) (the sample's `State`) → P; M.DOCS.066's U22 paragraph (BACKLOG's chroot list, A.U22.04's lint/type config) → E | found by a scan of every `M_*.md` change naming `U22` against the packet's steps (§1 rows X1, X2) |
| OF-79 is not taken at U22 (A-15) | its sites (`buildgen/codegen.py:197`'s SGP40 wiring, the NTP client, SGP40's restore wait) are outside every U22 step, and its `UTCTime` half waits for the owner's answer to the U18 review row (`REGISTER.md:513`) |

## 1. Step table

"landed" = in end form on the tree, report the line; "none @U22" = the step's U22 part is empty; "(W1)"/"(P1)" = the
part lands in that lane's WIP commit (§3). Lines are `wt-u22fold`'s.

| # | M-id | U22 part (one line) | files edited at U22 | lane |
|---|---|---|---|---|
| 1 | M.DOCS.060 | (1): `README.md:779`'s parenthesis "the stage-6 permanent-WLAN-deactivation risk" → "the role reversal's stage-6 fallback"; `:801`'s list drops that item; the rest of the map is U36/U37 | `README.md` | E |
| 2 | M.GEN.034 | (2): W80 (`buildgen/error_catalog.json:181`) name `WLAN_SILENT`, number kept, text "a second STA failure streak after the hotspot ran; Wi-Fi goes silent: no hotspot, the LED dark, one connect attempt every hotspot_time_min until a link"; E65 (`:81`) `"retired": true`, its text kept (as rows 16, 24, 43); W77 (`:178`) text "the hotspot's station list could not be read (the query raised, or the chip-down 32-entry answer); counted as no client"; plus the `status.NotifyState` table of A-8 | `buildgen/error_catalog.json` | W (W1) |
| 3 | M.HW_BENCH.110 | (1): `tests_hardware/README.md:15-16` "the stage-6 permanent-WLAN-\ndeactivation risk" → "the role reversal's stage-6 fallback"; the header rewrite is U36 | `tests_hardware/README.md` | E |
| 4 | M.SPEC.016 | (1): the owner-confirmed list (`SPECIFICATION.md:411-425`): the permanent-deactivation item (`:415-418`) → the silent-mode item; "only a human resubmitting credentials or a full task restart resets this" (`:419-420`) → "only a credentials change, which lands in the fresh-boot state (owner, 2026-10-08), or a full task restart resets this" | `SPECIFICATION.md` | D |
| 5 | M.SPEC.021 | (17): A.8's `/networking` sentence (`:947-953`) gains after "tries the stored network" the fresh-boot clause with the owner's quote; A.8's code-table sentence (`:911-916`) names `NotifyState` (A.4) per A-8 | `SPECIFICATION.md` | D |
| 6 | M.SPEC.058 | (15): C.7's WifiService sentence (`:2977-2982`) → the packet's text (a failed stations check counted as no client, the silent attempts in the attempt tier, "the entry into the silent mode" for "the permanent deactivation"); A.U19.14 landed (`DEVICE_REFERENCE.md:137`, BACKLOG item 24 gone, `SPECIFICATION.md:2912` names item 32) | `SPECIFICATION.md` | D |
| 7 | M.SPEC.064 | (6): the hold table (`:3279-3288`) loses "permanent deactivation \| 2 s, once" (`:3285`); the connect-attempt row (`:3281`) names the silent attempt and W's method (§3) | `SPECIFICATION.md` | D |
| 8 | M.SPEC.082 | (8): E.6.4's load-bearing finding (`:4612-4615`) → the packet's text | `SPECIFICATION.md` | D |
| 9 | M.SPEC.146 | (5): L.3's `hotspot_time_min` row (`:8777`) consumer → "`WifiService`: the hotspot window, and the silent mode's connect-attempt period (A.4)"; range clause kept | `SPECIFICATION.md` | D |
| 10 | M.SRC_NET.077 | (2): `_ERR_WLAN_OFF` (`asy_wifi_service.py:50`) goes; `_WRN_WLAN_DEACTIVATED` (`:61`) → `_WRN_WLAN_SILENT = const(80)`; `_PHASE_SILENT = const(4)` after `:196` with its comment; `_PHASE_DEACTIVATED`'s comment (`:196`) → the no-configuration text; the LED pair's comment (`:175`) → the no-configuration text, names `_LED_DEACTIVATED_ON_S`/`_OFF_S` and tags kept (the `_MS` names are U31's, A-25); `_STATIONS_UNSET = const(32)` beside `_STAT_JOINED_NO_IP` (`:201`) with the packet's trailing comment, untagged (N.1 platform fact) | `src/asy_wifi_service.py` | W (W1) |
| 11 | M.DOCS.027 | (4): the overlay bullet (`DEVICE_REFERENCE.md:11-18`) takes the no-configuration and silent clauses in place of "Wi-Fi switched off (a second failure streak … until a power cycle" and "the switched-off one included"; (2), (3) and the rewrite are U36 | `DEVICE_REFERENCE.md` | E |
| 12 | M.SRC_NET.081 | (2): `_get_hotspot_stations()` (`:273-287`) answers `None` for a raise (landed, (1)) and for exactly `_STATIONS_UNSET` entries; the `except` comment (`:281`) and one comment line at the count test per the packet; `async with` (U10), comments (U18) landed | `src/asy_wifi_service.py` | W (W1) |
| 13 | M.SRC_NET.087 | (2): `_hotspot_timeout_loop()` (`:501-504`) dispatches by phase: silent → `_silent_attempt_due = True` (a fire while one is due adds none); every other phase → `_on_hotspot_window_end()` (A-2); rename, client pattern, `(MemoryError, OSError)` arm landed (`:477-504`, (1) U18) | `src/asy_wifi_service.py` | W (W1) |
| 14 | M.SRC_NET.223 | (1)-(7): the silent mode in `_register_sta_connection_failure()` (`:649-659`), `_deactivate_wlan_permanently()` (`:411-421`) deleted; one silent attempt per period on the window's `PERIODIC` timer (`_run_silent_mode()`, A-2); the dark guard in `_led_on()`/`_led_toggle()`/`_run_led_pattern()` (`:515-536`, `:694-702`); restarts keep it (`_reset_wlan_connect_state()` `:661-682`, `_handle_reconnect_trigger()` `:451-469`, `_on_sta_disconnected()` `:560-569`, A-3); the fresh-boot flag set by `reconnect_wifi()` (`:918-924`) and honoured by `_handle_reconnect_trigger()`; the private window-end trigger; the two flags in `__init__`'s state block (`:262-267`) | `src/asy_wifi_service.py` | W (W1) |
| 15 | M.DOCS.110 | networking-status sentence (`DEVICE_REFERENCE.md:38-40`) → the packet's text | `DEVICE_REFERENCE.md` | E |
| 16 | M.DOCS.111 | `CLAUDE.md:333-335` "the hotspot role-reversal scenario's stage-6 permanent-WLAN-deactivation risk" → "… stage-6 fallback (a failed credential reopens the DUT's hotspot once, then its silent mode)"; the commit names this as the one meaning change (decision-records rule (3)) | `CLAUDE.md` | E |
| 17 | M.HW_BENCH.071 | (2): the stage-8 comment (`tests_hardware/bench/test_hotspot_role_reversal.py:148-150`) → the packet's three lines; the U26 form (restore on every path, `recover_by_reset`) not written | `tests_hardware/bench/test_hotspot_role_reversal.py` | T |
| 18 | M.HW_BENCH.073 | (1): two new tests on HEAD's file, by definition order: (a) `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` (`persistence_write`, after `:424`'s invalid-credentials test and before the real-credentials test `:438`), (b) `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt` (opt-in, after it; gate A-6); new `l4.hotspot_role_reversal_*` tags; the `destructive_last` marker and the merged flip-back test are U26 | same | T |
| 19 | M.HW_BENCH.124 | (1): `tests_hardware/README.md:746-756`'s "A permanent-WLAN-deactivation risk …" item → the packet's "What a failed stage-6 credential does" item, plus one clause naming rows 18's two cases and (b)'s gate (A-20); `:1028-1031`'s "… permanent-WLAN-deactivation risk" → "… to stay off that scenario's hotspot fallback" | `tests_hardware/README.md` | E |
| 20 | M.SRC_NET.224 | `_manage_hotspot_stations()` (`:542-551`): `None` → `wrn_s("Hotspot stations unknown, counted as no client", wrnno=_WRN_WLAN_STATIONS_UNKNOWN)`, then `_hotspot_client_absent()`; one comment line at the branch | `src/asy_wifi_service.py` | W (W1) |
| 21 | M.SPEC.163 | (1)-(4): A.4's Wi-Fi bullet (`:376-410`): (a) `:392-397`, (b) `:397-398`, (c) `:403-405`; C.9: the LED-flash row (`:3472`) and the `PERIODIC` sentence (`:3489-3490`); F.1's CYW43 values (`:5270-5280`) gain `_STATIONS_UNSET` and the defect's new end; Part N rows `wifi.wlan_down_settle_s` (`:9944`), `wifi.led_deactivated_on_s`/`_off_s` (`:9952-9953`) | `SPECIFICATION.md` | D |
| 22 | M.SRC_SENS.028 | A.U22.01 (b): `_signal_loop()`'s start (`asy_neopixel_driver.py:95-96`) gains `self._overlay_start.set()` after the black write; (c) landed (`:117-121`); `sleep_ms` is U31 | `src/asy_neopixel_driver.py` | P (P1) |
| 23 | M.SRC_SENS.035 | A.U22.02: the attribute writes go (`asy_notification_service.py:221-222, :226-227, :229, :231, :236, :241`); (1) the stale-sample check with `_SAMPLE_MAX_AGE_S = const(10800)` (`# @tunable notify.sample_max_age_s = 10800`, A-14); (2) `-> bool \| None`, `None` on every unevaluated path; `report_if_fatal` is U30 | `src/asy_notification_service.py` | P (P1) |
| 24 | M.SRC_SENS.033 | A.U22.02: `last_value`, `triggered` and their comment (`:152-154`) go; A.U22.04: the two callback parameters (`:170-171`) → `Callable[[int, int, int, float], Awaitable[bool]]`, `Callable[[], Awaitable[_LocalTime \| None]]`; construction-time service, no guards, `_sink_is_default` landed (`:167-206`); the defaults read `NOTIFY(Triggered=False, State=None, TS=None)` (row F2) | `src/asy_notification_service.py` | P (P1) |
| 25 | M.SRC_SENS.020 | A.U22.04: `asy_neopixel_driver.py:21-26`'s `TYPE_CHECKING` block drops `Callable`, `Any`, imports `TaskStarter` beside `ErrorSource, TimerStarter`; runtime imports landed (`:7-14`) | `src/asy_neopixel_driver.py` | P (P1) |
| 26 | M.SCR.028 | none @U22: `scripts/typecheck.sh` is not edited; its main pass stays green with the six modules out of the baseline (row 46) | - | - |
| 27 | M.SRC_SENS.025 | A.U22.01 (a): `_overlay_loop()` (`:85-92`) sets `_overlay_start` once before `while True:`; (1) the bounded refresh wait with `_OVERLAY_REFRESH_MS = const(300000)` (`# @tunable led.overlay_refresh_ms = 300000`) and its comment (A-13); A.U22.04: `get_task_starters()` (`:123-124`) → `list[TaskStarter]`; starters, error sources, loggers, `reset_error_counter() -> bool` landed (`:126-185`) | `src/asy_neopixel_driver.py` | P (P1) |
| 28 | M.SPEC.014 | the A.4 NeoPixel/notification bullet (`SPECIFICATION.md:352-371`) restated whole as the packet's text (A.U22.01's "The pixel reports no faults …" sentence included), plus (1) `State` (with A-8's marked table), (2) the dropped-flash sentence, (3) the refresh sentence, (4) the stale-sample sentence, (5) the window-needs-local-time sentence; A.S0930.13 carried: its A.4 watchdog paragraph is landed elsewhere (none here) | `SPECIFICATION.md` | D |
| 29 | M.SRC_SENS.030 | A.U22.04: `asy_notification_service.py:22-47`: `Coroutine`, `Any` out, `Awaitable` in, `TaskStarter` beside `TimerStarter, ValueRef`; `_ValueSource.get_data() -> object` (`:47`); the `_TicksMs` comment (`:26-27`) is U27's; `report_if_fatal` U30 | `src/asy_notification_service.py` | P (P1) |
| 30 | M.SRC_SENS.034 | A.U22.04 (types only); SF-B2's part (1) landed (`:74-84` static sink, `:203` `_sink_is_default`, `:313-320` the tested bool, `:56` `_WRN_NOTIFY_SIGNAL_DROPPED = const(67)`, catalog `:173`); `_next_sleep_ms()` U31 | `src/asy_notification_service.py` | P (P1) |
| 31 | M.SRC_SENS.036 | A.U22.04: `get_task_starters()` (`:322-323`) → `list[TaskStarter]`; `set_override_led()` stays `-> bool` returning `True` (`:355-357`, register `:267`, A-9) | `src/asy_notification_service.py` | P (P1) |
| 32 | M.TEST_HELP.006 | none @U22: the GRB byte store is U24; A.U22.01's L1 cases use the existing `raise_on_write` (`tests/neopixel.py:26`) as is | - | - |
| 33 | M.TEST_UNIT.078 | A.U22.04 typing (`tests/test_asy_neopixel_driver.py:15-26`): `run(coro: "Coroutine[object, object, T]")`, `Any` gone (A-11); driven time, builders, `_frame_ms` are U24/U31/U35 | `tests/test_asy_neopixel_driver.py` | P (P1) |
| 34 | M.TEST_UNIT.079 | (1) `test_the_overlay_is_rewritten_once_per_refresh_period` under the file's `_DrivenClock` (A-12); A.U22.01's "existing counts hold" re-checked (`:254` repeated-on, the `== 31` count is U35's) | same | P |
| 35 | M.TEST_UNIT.080 | A.U22.01's three L1 cases after `:700`: `test_a_restarted_overlay_task_reapplies_the_overlay`, `test_a_signal_task_ended_mid_ramp_restarts_dark_and_restores_the_overlay`, `test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry`; the A.U9 cases landed (`:461-700`) | same | P |
| 36 | M.TEST_UNIT.082 | A.U22.04 typing (`tests/test_asy_notification_service.py:15-28`): `run()` per A-11, `Any`/`Coroutine` gone; the U24/U35 builders not written | `tests/test_asy_notification_service.py` | P (P1) |
| 37 | M.TEST_UNIT.084 | A.U22.04: the scenario return types `:331, :377, :463, :535, :572` (`dict[str, Any]`) → `JsonDict`/`WriteValidity` per the call they return (A-11) | same | P (P1) |
| 38 | M.TEST_UNIT.086 | A.U22.02: `:678` (`signal.triggered is False`) goes; (1) the threshold-read failure asserts `_check_one()` is `None`; the read-log helpers `:659, :738` → `ErrorLog` | same | P |
| 39 | M.TEST_UNIT.087 | A.U22.02: `:827-828`, `:842-843` go; `:864-876` → `test_check_one_returns_the_most_recent_trigger_state`; (1) `None` asserts on every unevaluated path; (2) `test_a_stale_producer_sample_is_not_evaluated` | same | P |
| 40 | M.TEST_UNIT.274 | A.U22.04 typing (`tests/test_neopixel_wifi_integration.py:24-35`) | `tests/test_neopixel_wifi_integration.py` | P (P1) |
| 41 | M.TEST_UNIT.276 | A.U22.04 typing (`tests/test_notification_neopixel_integration.py`, the `TYPE_CHECKING` block and `run()`) | `tests/test_notification_neopixel_integration.py` | P (P1) |
| 42 | M.TEST_UNIT.296 | (1) `test_an_identity_change_lands_the_unit_in_the_fresh_boot_state` on HEAD's `_simulated_set_network_endpoint()`/`_grouped_set()` (`tests/test_setter_microdot_integration.py:132-160`), after `:303`; the mode switch stubbed inline as `tests/test_asy_wifi_service.py:2271-2280` stubs it | `tests/test_setter_microdot_integration.py` | T |
| 43 | M.TEST_UNIT.346 | (1)-(7): the new families beside their sections and the HEAD tests rewritten in place (`:1610` comment, `:1697`, `:1764`, `:2067`, `:2132`, `:2283`, `:2294`, `:2305`, `:2425`, `:2459`, `:2614`, `:1639`, the U19 integration's W80 code `:3376`, E65 at `:2076` goes with its test); §9 lists each | `tests/test_asy_wifi_service.py` | W |
| 44 | M.TEST_UNIT.347 | `test_the_silent_mode_leaves_a_real_neopixel_driver_dark_until_a_link` beside the hotspot-pattern tests (`tests/test_neopixel_wifi_integration.py:151-224`), on W1 | `tests/test_neopixel_wifi_integration.py` | P |
| 45 | M.TOOL.030 | A.U22.04: `pyproject.toml:294` `["ANN401", "ARG004"]` → `["ARG004"]` (the packet's `ARG002` is stale, A-10); the category-5 comment (`:289-290`) names no file and stays for `:295-298`, the ARG004 reason (`:292-293`) stays | `pyproject.toml` | P |
| 46 | M.TOOL.033 | A.U22.04: the baseline list (`pyproject.toml:436-500`) loses `asy_neopixel_driver` (`:446`), `asy_notification_service` (`:447`), `test_asy_neopixel_driver` (`:465`), `test_asy_notification_service` (`:466`), `test_neopixel_wifi_integration` (`:483`), `test_notification_neopixel_integration` (`:485`) | `pyproject.toml` | P |
| 47 | M.TSC.231 | the `_deactivate_wlan_permanently` entry (`tests_scripts/test_fault_or_warning_never_both.py:48`) and its reason go; a new pair the scan reports is triaged with the lead (the mixed-kind table follows the code) | `tests_scripts/test_fault_or_warning_never_both.py` | W (W1) |
| 48 | M.TWIN.040 | (2) on HEAD's per-construction model (`digital_twin/network.py:57-152`): module-level `set_access_point_up(up: bool)` over `_access_point_up = [True]`, honoured at a completed `_run_connect()` (`:93-106`) with no scripted outcome consumed; per-object `stations_chip_down = False` answering 32 `(bytes(6),)` tuples from `status("stations")` (`:137-144`); each with the packet's twin-only comment; the U25 rewrite not written | `digital_twin/network.py` | T |
| 49 | M.TWIN.058 | (1): the `network.py` bullet (`digital_twin/README.md:119-130`) gains one sentence on the two knobs after its `ifconfig()` sentence; carried A.SDEP.08 (no newer tag, D1), A.U0.31, A.U14.28 (F.7 `SPECIFICATION.md:6022`), A.U7.01 (E.6.1 `:4548`): landed or later units' (§6) | `digital_twin/README.md` | E |
| 50 | M.TWIN.132 | (2): `test_a_downed_access_point_fails_every_interface_object_until_switched_back`, `test_a_chip_down_stations_answer_is_32_unfilled_entries` (switch restored in `finally`); the A.U22.01 L2 restart case and the fake cases are U25 (A-17) | `tests/test_digital_twin_network_neopixel.py` | T |
| 51 | M.TWIN.144 | (19) (a)-(c) on HEAD's file and seams (`sensortask_wozi`, the `_connection_failures` shortcut, `conn._hotspot_timer.callback(conn._hotspot_timer)`), condition waits only, the switch restored in `finally`; plus A-18's two cheap additions; (15) and (17) are U25 | `tests/test_digital_twin_sensortask_integration.py` | T |
| F1 | M.SPEC.156 | (9): new Part N rows `led.overlay_refresh_ms = 300000` and `notify.sample_max_age_s = 10800` (Sites, Basis, Margin, Re-check trigger as the packet states them, in the N.1 basis form, A-23); `sgp40.comp_max_age_s` and the client pair landed (U15/U18) | `SPECIFICATION.md` | D |
| F2 | M.SRC_SENS.037 | (1): `NOTIFY = namedtuple("NOTIFY", ("Triggered", "State", "TS"))` (`asy_notification_service.py:124`) and `_FIELDS` (`:125`) follow; `_monitor_loop()` (`:244-282`) computes and stores one `state` per cycle, the config-failure branch storing too; `_store_notif_data(*, any_triggered, state)` (`:310-311`); the one-line code comment | `src/asy_notification_service.py` | P (P1) |
| F3 | M.TEST_UNIT.088 | (1): `test_the_sample_reports_why_signals_were_not_evaluated`, one case per `State` code, the construction defaults `NOTIFY(False, None, None)`; no `NOTIFY(` tuple exists in `tests/` (grep), so "every tuple gains the field" is empty; `tests/test_readiness_gates.py:297-298` (`(False, None)` and the `get_dict_data` dict) gain `State` | `tests/test_asy_notification_service.py`, `tests/test_readiness_gates.py` | P |
| F4 | M.TEST_HELP.041 | (8), U22 part: a per-device scenario asserting `GET /status`'s `notification.State` (2 before the first sync, 0 once synced with readable producers) — `/status`, not `/measurements` (A-8); beside `tests/_sensortask_scenarios.py:2343`'s notification assert | `tests/_sensortask_scenarios.py` | P |
| X1 | M.WEB.045 | (1), U22 part (not in the packet): `mockdata/samples.json:21` `status.notification` gains `"State": 0` | `mockdata/samples.json` | P |
| X2 | M.DOCS.066 | U22 stage (not in the packet): BACKLOG's chroot list (`BACKLOG.md` "Deferred / explicitly out-of-scope work", before "Kept here as the running list …" `:652`) gains the U22 paragraph: "`pyproject.toml` lint and type config only: the notification module's per-file ruff entry narrows to ARG004 and six modules leave the explicit-Any baseline; no build impact" | `BACKLOG.md` | E |
| X3 | (A-8) | `buildgen/codegen.py:650` `_notification_status()` gains `"State": data.State`; `buildgen/definitions.py:693-697` gains a `State` readonly row with `codes` from `_status_codes("NotifyState", …)` (`:155-163`); its L0 case in `tests_scripts/test_buildgen_definitions.py` | `buildgen/codegen.py`, `buildgen/definitions.py`, `tests_scripts/test_buildgen_definitions.py` | P |
| X4 | (A-18) | one mock case on the real pixel for the no-configuration pattern and its `LEDWifiOn` rule (the one Wi-Fi LED mode with no mock-tier test at HEAD); one assert in `tests/_sensortask_scenarios.py:1669-1679` that the identity PUT also sets W's fresh-boot flag (the full generated wiring of the hook) | `tests/test_neopixel_wifi_integration.py`, `tests/_sensortask_scenarios.py` | P |
| X5 | (A-20) | BACKLOG "Real-hardware work still owed" (`:256-373`) gains one row for row 18's two cases (R3; (a) one owned flash write, (b) about two `hotspot_time_min` windows, its gate; read the FRAM-backed logs first, CLAUDE.md) | `BACKLOG.md` | E |
| OF-75 | open finding | closed by row 27's (1) (the refresh) with the datasheet read (A-16); the comment cites no audit ID | (row 27) | P |
| OF-79 | open finding | not taken at U22; re-targeted per A-15 with its reason | - | lead |

Register rows naming U22: `:234` (U9: attribute writes go at U22) = rows 23, 24, 38, 39; `:267` (`set_override_led()`
stays `bool`) = row 31, A-9; `:598` SF-B2 = landed (row 30) + row 28 (2)'s SPEC sentence; `:613` SF-B17 = rows 23 (2),
F2, F3, F4, X1, X3, 28 (1); `:630` SF-M2-02 = landed (`src/asy_ntp_client.py:513-519`) + row 28 (5)'s sentence;
`:632` SF-M2-04 = landed at U18 (`asy_wifi_service.py:170-173, :495-499`); `:642` SF-M3-01 = rows 23 (1), 28 (4), F1
(SGP40 half landed `src/asy_sgp40_driver.py:85-88, :178-183`); `:650` SF-M3-09 = rows 27 (1), 34, 28 (3), F1;
`:661`/`:662` OR151/OR152 = rows 2, 4-21, 42-44, 47-51; `:582`/`:583` = A-4, A-5; `:663` (U26: how the bench reads the
STA mode) = not U22 (row 17 edits only the stage-8 comment). The action file's pilot table (`U22.md:14-33`): A.U9.01-.06,
.08-.11 hold (landed U9-U11), A.U9.07 dropped, A.U22.03 withdrawn (OR126.a (4)); U22's own parts are rows 22-25, 27,
29-31, 33-41, 45-46.

## 2. Lanes

Sizes: step parts and rough edit volume. W is the critical path (the state machine and ~40 tests); P and T start at
once with their W-independent parts and take W's on the API base (§3).

### W — the Wi-Fi service (9 rows; `asy_wifi_service.py` ~+140/−35, ~38 new and ~12 rewritten L1 tests)
Files: `src/asy_wifi_service.py`, `tests/test_asy_wifi_service.py`, `buildgen/error_catalog.json`,
`tests_scripts/test_fault_or_warning_never_both.py`. Rows 2, 10, 12-14, 20, 43, 47.
- W1 (WIP, first, against §3): tests first — the core cases of §9's W list written and seen failing on the tree;
  then the whole product change (rows 10, 12-14, 20), the catalog (row 2 and A-8's table), row 47, and the HEAD tests
  the change turns red rewritten in place (row 43 (7)), so W1's own file and `test_error_catalog.py` are green.
- Then W2: the remaining families of row 43 (§9), the lane's own runs of every file that constructs a `WifiService`
  (§8), D.15 order last.

### P — the pixel and the notification (≈27 rows; driver ~+15/−6, notification ~+45/−25, ~20 new L1 tests, ~25 test edits)
Files: `src/asy_neopixel_driver.py`, `tests/test_asy_neopixel_driver.py`, `tests/test_neopixel_wifi_integration.py`,
`src/asy_notification_service.py`, `tests/test_asy_notification_service.py`,
`tests/test_notification_neopixel_integration.py`, `pyproject.toml`, `buildgen/codegen.py`, `buildgen/definitions.py`,
`tests_scripts/test_buildgen_definitions.py`, `mockdata/samples.json`, `tests/_sensortask_scenarios.py`,
`tests/test_readiness_gates.py`. Rows 22-25, 27, 29-31, 33-41, 44-46, F2-F4, X1, X3, X4, OF-75.
- P1 (WIP, first): the driver (rows 22, 25, 27 with A-13) with `_YieldOnlyAsyncio`'s `wait_for_ms`/`TimeoutError`
  (A-12) in the same commit; A.U22.02 and A.U22.04 in the notification (rows 23, 24, 29-31), the stale check and the
  `None` returns (row 23), `State` (F2) with `tests/test_readiness_gates.py:297-298` following it (the 2-tuple and the
  `get_dict_data` expectation turn red the moment the field lands); every LED test file green again at both GC stages.
- Then (on the API base for the W-dependent parts): the A.U22.01 and refresh tests (rows 34, 35), the notification
  tests (rows 37-39, F3), row 44 and X4 (W's silent mode), X3/X1/F4 (W's `NotifyState` table), `pyproject.toml`
  (rows 45, 46) once every one of the six files is `Any`-free, the yields re-check of A-13.

### T — the tiers that follow W (6 rows; twin model ~+35, ~7 new twin/L1 tests, 2 new bench tests)
Files: `digital_twin/network.py`, `tests/test_digital_twin_network_neopixel.py`,
`tests/test_digital_twin_sensortask_integration.py`, `tests/test_setter_microdot_integration.py`,
`tests_hardware/bench/test_hotspot_role_reversal.py`. Rows 17, 18, 42, 48, 50, 51.
- At once: the two twin knobs and their fake cases (rows 48, 50), the bench edits (rows 17, 18; `pytest
  --collect-only tests_hardware` and the bench L0 checks only, §8).
- On the API base: row 51's (a)-(c) and A-18's additions, row 42; measured file times (A-19).

### D — SPECIFICATION.md (10 rows, last)
Rows 4-9, 21, 28, F1; A-8's `NotifyState` marked table in A.4 and A.8's code-table sentence; Part N rows for every
tag of §3 (`led.overlay_refresh_ms`, `notify.sample_max_age_s`, each new `l1.*`/`l2.*`/`l4.*` tag the lanes report);
C.8's connect-attempt row names W's method; F.1 names `_STATIONS_UNSET`.

### E — other docs (8 rows, last, with D)
Files: `README.md` (row 1), `tests_hardware/README.md` (rows 3, 19), `DEVICE_REFERENCE.md` (rows 11, 15), `CLAUDE.md`
(row 16), `digital_twin/README.md` (row 49), `BACKLOG.md` (X2, X5). CLAUDE.md's edit is the one meaning change and says
so; the others are "no meaning change" beyond the two requirements.

## 3. Cross-lane contract and WIP-commit order

The state machine is W's alone (rows 10, 12-14, 20). What P and T may rely on before W1 lands: the names and values
below, nothing else; their W-dependent tests are written against this table and run only on the API base.

| from → to | what the consumer must assume |
|---|---|
| W → T, P, D (W1) | **phases** (`asy_wifi_service.py`, read with a file-local source read, never a hard-coded mirror without a keep-in-sync comment): `_PHASE_STA_SEEKING = 0`, `_PHASE_STA_ESTABLISHED = 1`, `_PHASE_HOTSPOT = 2`, `_PHASE_DEACTIVATED = 3` (now only "no readable Wi-Fi configuration"), `_PHASE_SILENT = 4`; `is_hotspot_active()` is `False` while silent; the snapshot's `Mode` is `"STA"` while silent |
| W → T, P (W1) | **flags and members** (A-2): `self._reconnect_fresh: bool` (set by `reconnect_wifi()` beside `_reconn_wifi`, cleared by `_handle_reconnect_trigger()`), `self._silent_attempt_due: bool` (set by the watcher while silent, consumed by `_run_silent_mode()`), `_on_hotspot_window_end() -> None` (the watcher's call outside the silent mode: deinit the timer, cancel the flash, `_reconn_wifi = True`, no fresh flag), `async _run_silent_mode() -> None` (one `_connect_loop()` iteration while silent: arm the window's `PERIODIC` timer through `_arm_hotspot_timer()` if not running, then one attempt if due), `_arm_hotspot_timer() -> bool` (the one arm path, shared with `_hotspot_client_absent()`; `False` after a persisted `_ERR_TIMER`) |
| W → T, P (W1) | **behaviour**: the second streak's last failure (`_hotspot_started_once` true) enters `_PHASE_SILENT`, persists one W80, cancels the flash task, calls `_led_off()`, makes no `disconnect()`/`active(False)`/`deinit()`; while silent `_led_on()`, `_led_toggle()`, `_run_led_pattern()` light nothing and `_led_off()` acts; the first attempt is due one period after entry; a due attempt that links gives `_on_sta_connected()` (`_PHASE_STA_ESTABLISHED`, LED as `LEDWifiOn` says) and deinits the timer; one that fails leaves the mode, no streak; a task restart keeps `_PHASE_SILENT` and the next iteration re-arms; `reconnect_wifi()` + one loop iteration from the hotspot, the silent mode or a link gives `_connection_failures == 0`, `_hotspot_started_once is False`, `_PHASE_STA_SEEKING`; a pending settings trigger beside a window end gives the fresh-boot state |
| W → T, P, D (W1) | **stations**: `_get_hotspot_stations()` returns `None` for a raise or exactly `_STATIONS_UNSET = 32` entries, the list otherwise (`[]` included); `None` persists one W77 and runs `_hotspot_client_absent()` |
| W → all (W1) | **catalog** (`buildgen/error_catalog.json`): W80 `WLAN_SILENT` (`_WRN_WLAN_SILENT = const(80)`), E65 `WLAN_OFF` retired (no `src/` constant, no live site), W77 text as row 2; `status.NotifyState` = `{"0": {"text": "every signal evaluated"}, "1": {"text": "not evaluated by setting (AutoOn off, paused, or outside the window)"}, "2": {"text": "not evaluated: no local time (no NTP sync yet this boot, or the clock callback failed)"}, "3": {"text": "evaluated in part (a value unavailable, stale or not numeric)"}, "4": {"text": "the service's own configuration unreadable"}}` (M.SPEC.014 (1)'s texts); tests name codes through `tests/_error_codes.py`'s `code()` only (`test_no_test_tier_keeps_its_own_copy_of_a_code`) |
| W → D, E | the W80 and W77 console texts ("No WLAN connection after the hotspot ran - silent mode, one connect attempt per hotspot period"; "Hotspot stations unknown, counted as no client"); the method holding the silent attempt for C.8's hold-table row; any new `l1.asy_wifi_service_*` tag with value and basis |
| P → D, E, lead | `NOTIFY` field order `("Triggered", "State", "TS")`; the five `State` codes as the catalog table; `led.overlay_refresh_ms = 300000` and `notify.sample_max_age_s = 10800` with Sites; the measured per-wake allocation of the refresh (A-13); the `_PHASE_YIELDS`/`_PATTERN_YIELDS`/`_run_until` bounds it re-derived (A-13); that `definitions.py` and `samples.json` changed, so the lead rebuilds the frozen website (`frozen_modules/`, `build/`) before any full-graph run |
| P → T | none required: T's in-process cases see the refreshed overlay as black frames while silent (no new frame colour) |
| T → D, E | the knob names `set_access_point_up(up)`, `stations_chip_down`; the bench test names, their markers and gate (A-6), each new `l4.hotspot_role_reversal_*` / `l2.sensortask_integration_*` / `l2.network_neopixel_*` tag with value and basis; the measured twin file times (A-19) |
| all → lead | allow-list lines their rewrites retire or re-key (shrink only: at least `_decision_vocab_allowlist.txt:323`, the `:1610` comment W rewrites to five phases); every run started and confirmed exited; per-file times at both GC stages and under settrace for every grown file |

**WIP order:** W1 and P1 written in parallel; T starts its W-independent parts. Each hands back "WIP <hash>". The
lead merges W1 and P1 into one API base `audit/u22-api`, regenerates the device modules
(`scripts/_generate_sensortask_modules.py`), rebuilds the frozen website (P1 changes no definitions yet, so this is a
no-op until X3 lands; it is re-done after P's final hand-back), runs ruff, the three mypy passes and the L0 files W
and P touched, and resumes W, P and T on the base. D and E start once W, P and T have handed back, with the facts
relayed. **Squash group** (the lead): the unit lands as one commit.

**Red checks on a lane's own worktree before the base merges (report the exact line, never work around):**
`test_tunables_register.py` (every new tag in P and T vs D's Part N rows), `test_error_catalog.py` and
`tests/_error_codes.py`-based asserts in T and P before W1 (`WLAN_SILENT`, `NotifyState` unknown),
`test_buildgen_definitions.py` and the module generation in P before W1 (`_status_codes("NotifyState")` raises
`BuildError`), `test_decision_vocabulary.py`/`test_citations.py` (re-keyed comments vs the lead's allow-lists),
`test_mypy_any_baseline.py` and the main mypy pass while P has removed a module from the baseline its file has not
cleared, `test_code_conventions.py` (D.15) until each lane's last edit.

## 4. Shared files: single owner

| file | owner | others report to it |
|---|---|---|
| `SPECIFICATION.md` | D | all |
| `CLAUDE.md`, `BACKLOG.md`, `README.md`, `DEVICE_REFERENCE.md`, `tests_hardware/README.md`, `digital_twin/README.md` | E | all |
| `buildgen/error_catalog.json` (the catalog) | W | P (the `NotifyState` table text, §3) |
| `pyproject.toml` | P | - (no other lane edits it; no dependency moves, so `uv.lock` is nobody's) |
| `buildgen/codegen.py`, `buildgen/definitions.py`, `mockdata/samples.json`, `tests/_sensortask_scenarios.py`, `tests/test_readiness_gates.py` | P | W (the fresh flag name for X4) |
| `tests_scripts/test_fault_or_warning_never_both.py` (the mixed-kind table) | W | lead reviews (shrink by one) |
| allow-lists (`tests_scripts/_decision_vocab_allowlist.txt`, `_citation_allowlist.txt`) | lead | all (shrink only; `_citation_allowlist.txt:89` keys `asy_notification_service.py`'s docstring, which no U22 row edits) |
| `tests/network.py`, `tests/machine.py`, `tests/neopixel.py`, `digital_twin/neopixel.py`, `digital_twin/machine.py` | nobody (no U22 edit: the scan double for row 43 (5) is test-local; `Timer.trigger()`/`drop()`/`arms` exist at `tests/machine.py:1039-1083`) | - |
| `.github/workflows/ci.yml`, `scripts/*` | nobody | - |
| hazard tiers (`tests/test_bus_hazard_multi_device.py`, the twin hazard file, the two hardware ones) | nobody | U22 adds no device and no bus user; the shared resources it touches (`wifi_mode_lock`, the WIFI/NOTIFY FRAM logs, the heap) are covered by W's non-blocking and resilience tests and D's hold table (§8) |
| `/root/pico-toolchain` | nobody (read-only; no rebuild is needed at U22) | - |
| `frozen_modules/`, `build/` (the frozen website, the generated modules) | lead | P reports every definitions/sample change |
| `ext/`, `legacy/`, `arduino/` | nobody | - |

## 5. Rulings needed (default given; conservative, reversible)

1. **A-1 lane cut.** Default: W, P, T in wave 1 (three agents, disjoint files), D and E in wave 2, last.
   Alternative: P split into L (driver + its tests) and N (notification + publication), T moved to wave 2 with D/E
   waiting on it — more lanes, T later on the critical path.
2. **A-2 the members M.SRC_NET.223 (7) leaves "decided at execution".** The contract needs them before W1. Default: the
   §3 names; the silent attempt is a method of its own (`_run_silent_mode()`, called from `_connect_loop()`'s dispatch
   beside `_run_hotspot_mode()`/`_run_sta_mode()`, `asy_wifi_service.py:397-400`), so `_run_sta_mode()` keeps its 5 s
   seeking meaning; the dark guard reads the phase inside `_led_on()`, `_led_toggle()` and `_run_led_pattern()`, not by
   holding the LED handle back, because `_attempt_sta_connect()` (`:319-320`) and the `LEDWifiOn` push (`:616-621`)
   call `set_wifi_led()` on every attempt and would re-select it; the window's arm is extracted from
   `_hotspot_client_absent()` (`:478-492`) into `_arm_hotspot_timer()` so both callers share one arm path and one
   `_ERR_TIMER` wording (D.10). Each reason goes into the commit message. Alternative: the guard as a held-back handle;
   the attempt as a `_run_sta_mode()` branch.
3. **A-3 what else must keep the silent mode, which the packet names only in part.** On the tree a task restart sets
   `_reconn_wifi` from `isconnected()`/`active()` (`:676-680`), and `_handle_reconnect_trigger()` sets
   `_PHASE_STA_SEEKING` for every non-hotspot reconnect (`:458-462`), so a restart in the silent mode would leave it
   although M.SRC_NET.223 (4) says the restart keeps it. Default: the plain-reconnect branch keeps a silent phase unless
   the fresh flag is set; `_on_sta_disconnected()` (`:560-569`) registers no failure while silent (the packet's (2));
   `_attempt_sta_connect()`'s empty-SSID branch (`:326-330`) gets no guard: the silent mode is entered only with a
   configured SSID and no request reaches a silent unit, recorded as "inherently safe" in the scan.
4. **A-4 the missing-configuration state (the fold's open point; owner-review row `REGISTER.md:582`).** Default: the
   fold's reading (OR151 names the second streak only; `_PHASE_DEACTIVATED` stays for an unreadable configuration with
   its own pattern). A settings change cannot reach it: an invalid store refuses every write
   (`src/asy_config_manager.py:582-584`), so the identity hook never fires, and the loop skips everything while
   deactivated (`asy_wifi_service.py:383-387`); W adds one regression pinning both (a `reconnect_wifi()` while
   deactivated changes nothing; the refused PUT leaves the phase). Listed for the owner review with the fold's row.
5. **A-5 "completely silent" (the fold's open point; `REGISTER.md:583`).** Default: the fold's reading — the LED and the
   radio's visible behaviour; each silent attempt's verdict warning persists (one slot under the repeat rule, FRAM
   writes are not wear, owner, 2026-09-26). W's resilience test pins the slot count.
6. **A-6 the gate of the ~18 min bench case (M.HW_BENCH.073 (1) (b), "decided at execution"; the fold's open point).**
   (b) needs the real-credentials test's write in the same session: without it the stored SSID is stage 0's empty one,
   which returns to the hotspot every window and never goes silent, so (b) would fail. Default: `@pytest.mark.long_soak`
   with the in-test skip when `--soak-tier` is absent (`tests_hardware/flash/test_memory_stress.py:99-103`; the verdict
   counts that skip as expected, `scripts/_hardware_verdict.py:24-28`), **and** `@pytest.mark.persistence_write` as the
   AND-gate on its precondition (deselected and counted without `--allow-persistence-writes`; its comment says it owns
   no write and runs on the preceding test's, and the README row of X5 says "0 writes"); no conftest, marker or flag
   change. Alternatives: a marker and flag of its own (a `tests_hardware/conftest.py` edit and the marker tables U26
   owns, SF-U0-08); `long_soak` alone (a soak run without write permission then fails (b) for a missing precondition).
7. **A-7 the twin AP for (19) (c).** HEAD's twin AP never reports a link (`digital_twin/network.py:137-144` returns
   `_status`, IDLE), so `_run_hotspot_mode()` (`asy_wifi_service.py:684-692`) never reaches the stations check in the
   twin and (c) cannot run. Default: (c) sets the selected AP object's `_status = network.STAT_GOT_IP` itself once
   `conn._ap_selected` (a test-local poke on the fake, with a ≤ 3-line comment naming the twin's AP-mode gap the README
   states, `digital_twin/README.md:128-130`); the U25 model (A.U25.72) retires the poke. Alternative: bring A.U25.72's
   AP rule into `network.py` now (every twin hotspot run then sees `STAT_GOT_IP`: test 5, the CI suite's Run 7).
8. **A-8 where `State` is published.** The packet says `/measurements`; on the tree the notification is not a
   `sensors=` route source (`buildgen/codegen.py:559-560`; `tests/_sensortask_scenarios.py:1578`), so its sample reaches
   only `/status`'s `notification` block (`codegen.py:645-651`), whose fields the hand-written "Notification Status"
   group lists (`buildgen/definitions.py:693-697`). Default: `"State": data.State` in `_notification_status()`, a
   `State` readonly row with `codes` inlined from a new catalog table `status.NotifyState` (`_status_codes()`,
   `definitions.py:155-163`), `samples.json`'s `status.notification.State` 0, SPEC A.4's marked table and A.8's
   code-table sentence naming it — A.8 says every `/status` code table has the catalog as its one source
   (`SPECIFICATION.md:911-916`). No `js/` edit (the renderer reads definitions generically). Alternatives: a raw number
   with a description (no table; A.8's rule then has an exception); publication deferred to U23 (F4's scenario not
   writable at U22).
9. **A-9 `set_override_led()` stays `-> bool` returning `True`** (`asy_notification_service.py:355-357`; register
   `:267`: the setter contract, C.5.2); M.SRC_SENS.036's `-> None` is not written.
10. **A-10 the notification's ruff entry** is `["ANN401", "ARG004"]` on the tree (`pyproject.toml:294`; the sink became
    a static method at U9), so the end is `["ARG004"]`, not the packet's `["ARG002"]`; ruff's RUF100 proves the
    narrowing (the trial removal of G8/R62).
11. **A-11 typing without U24's shared aliases.** Default: each test file's own `run(coro: "Coroutine[object, object,
    T]")` (A.U22.04's own fallback); `JsonDict` from `asy_base_classes` for config bodies, `WriteValidity` for
    per-field results, `ErrorLog` for log reads (M.TEST_UNIT.084 Resolved: `get_dict_cfg()` is typed with `JsonDict`).
    The main mypy pass with no args and with `src tests tests_hardware/device_scripts` is clean with the six modules out
    of the baseline before row 46 lands.
12. **A-12 "under driven time" without `tests/_driven_time.py`** (U35; absent, as are `_async_harness.py`,
    `_fast_sleep.py`, `_src_const.py`, `_fake_time.py`). Default: each file's local idiom — the driver test's
    `_DrivenClock`/`_YieldOnlyAsyncio` (`tests/test_asy_neopixel_driver.py:67-106`), which **must** gain `wait_for_ms`
    (a yield loop that returns when the awaited flag is set, raises `asyncio.TimeoutError` once the driven `now` passes
    the deadline, cancelling the inner task) and `TimeoutError` in P1, or every `_DrivenClock` test that starts the
    overlay task fails at once with an `AttributeError`; the notification test's `_FastAsyncSleep` (`:117`) and its
    fake clock; the Wi-Fi test's `_FastAsyncSleep` and the fake `Timer`'s `trigger()`/`drop()`/`arms`.
13. **A-13 the refresh allocates per overlay wake, not "once per period".** `wait_for_ms(flag.wait(), T)` builds a
    runner task, the promoted `aw` task and, on the normal path, a `CancelledError(status, result)`
    (`extmod/asyncio/funcs.py:7-22, :24-51`) on every wake — every `on()`/`off()`/`toggle()`: up to two a second during
    a connect poll, one per phase of a flash pattern. Short-lived and collectable, but the packet's sentence is wrong,
    and each wake now takes more loop rounds before the frame is written (the runner, then the waiter), which can
    starve the yield-bounded waits (`tests/test_neopixel_wifi_integration.py:92-93` `_PHASE_YIELDS = 4`,
    `_PATTERN_YIELDS = 32`; `_run_until(…, 20|40)` in the driver test). Default: keep the packet's design (no new task,
    timer or wiring); P proves structurally that a wake leaves nothing behind (after a wake the asyncio IO queue holds
    only the overlay's one flag registration and no runner task is left pending), records the bytes one wake allocates
    on the Unix port as a single measured figure (not an assertion), and re-derives each yield bound from the new hop
    count, stated in its comment (a bound re-derived for a longer path, not a weakened check); no text written at U22
    says "once per period" (the allocation catalog row is U30's).
    Alternative: a `PERIODIC` `machine.Timer` setting the flag every five minutes (no per-wake allocation; one alarm
    from rp2's pool and a timer starter on the driver).
14. **A-14 the stale-sample predicate.** SGP40 already has one (`src/asy_sgp40_driver.py:178-183`, `_current_value()`:
    `now is not None and isinstance(ts, int) and now - ts > _COMP_MAX_AGE_S`). Default: the notification's check is
    written in exactly that shape (an `int` `TS` only, the same bound value) and both sites are named in Part G's
    catalog as one rule (Part G.3's scan); no shared helper at U22 (it would edit `asy_sgp40_driver.py` and
    `asy_base_classes.py`, outside U22's files). Alternative: one shared helper in `asy_base_classes.py` beside
    `utc_now()`, both callers moved.
15. **A-15 OF-79** (`open_findings.md:87`, target U22). Its sites are `buildgen/codegen.py:197`
    (`SgpBackup(fram, ntp.ntp_issynced)`), `asy_fram_manager.py:552-556, :586-590` (the callback decides the
    timestamp), SGP40's restore wait (`asy_sgp40_driver.py:540-547`) and `codegen.py:635` (`UTCTime`), none in a U22
    step; the `UTCTime` half waits for the owner's answer to the U18 review row (`REGISTER.md:513`). Default: not
    taken; re-targeted to U32 (M.GEN.008, the generated status and callback block's unit), state "open", reason "outside
    U22's modules; UTCTime waits on the A-20 review answer; the SGP40 half is one generated wiring line passing a
    clock-set callable". Alternative: P takes the SGP40 half now (a clock-set getter, the wiring line, an L0 line, the
    SGP40 twin reboot tests re-run).
16. **A-16 OF-75 closes** with row 27 (1): the datasheet confirms a power-lost reset and that the pixel takes its colour
    only from new data after a power-on reset (`datasheets/ws2812/WS2812.pdf`, Features and General description, read
    for this plan); the code comment states the fact without an audit ID; OF-75 closed with U22's commit.
17. **A-17 twin cases the packet stages at U25.** Default: as staged — the A.U22.01 L2 restart case (M.TWIN.132 Unit:
    "the A.U22.01 case — its product half is U22's"), the no-configuration pattern on the twin pixel (A.U18.30's case),
    the raising stations query with its parameter filter ((17), M.TWIN.040 (1)); U22 covers them at L1 (rows 35, 43)
    and at the mock tier (X4). Alternative: the A.U22.01 case now on HEAD's seams (the twin fake has `raise_on_write`,
    `digital_twin/neopixel.py:21`).
18. **A-18 the mode matrix of §9 at the twin tier.** Default, two cheap additions inside row 51's cases rather than new
    boots: (a) restarts the connect task once while silent (cancel, `conn.start_asy_connect()`) and asserts the phase
    and the dark pixel kept and the period re-armed (the only twin proof of a restart in the new mode); (b) runs with
    `LEDWifiOn` off and asserts the pixel stays dark through both hotspot phases (the disabled LED at the twin tier).
    The mock tier's cross-module seams per mode are covered (X4 adds the one missing: the no-configuration pattern on a
    real pixel); restarts are module-internal transitions with no cross-module seam, so the unit tier carries them
    beside the twin's silent one. Alternative: one more twin boot per mode and restart (≈ 30-60 s each, §7).
19. **A-19 the twin file's time.** Row 51 adds three real-time scenarios to a file under the 240 s per-file limit
    (`scripts/test.sh:93-94`, no per-file overrides by rule, `:414`). Default: every streak uses HEAD's
    `_connection_failures` shortcut (set after the fresh-boot reset, else it is overwritten), every wait is a condition
    wait; T measures the file at both GC stages and under settrace; above 168 s (70 %) at any of the three, the lead
    decides between merging (b) into (a) (one boot: settings change, reopen, window end, silent, relink) and a new twin
    file (a new `test_digital_twin_*` family for `tests_scripts/test_level_containment.py:20-30`: it then needs the
    role-reversal file's `COVERS_TWIN_SCENARIOS` entry, T's, or an E.6.6 row, D's). Alternative: merge now.
20. **A-20 BACKLOG, two rows the packet does not name.** X2 (M.DOCS.066's U22 paragraph, omitted by the packet) and X5
    (an owed-hardware row for row 18's two cases, as U21 added its rows); and one clause in row 19's README item naming
    (a), (b) and (b)'s gate, since the README is the reference for the gates.
21. **A-21 F4 at `/status`.** M.TEST_HELP.041 (8) says "the notification sample on `/measurements`"; per A-8 the
    scenario asserts `GET /status`'s `notification.State`. X4's extra assert in the networking scenario pins the
    generated wiring of the fresh-boot hook on every device.
22. **A-22 how the bench test reads the device.** `bench_device()`, `harness.hotspot_password()` and `recover_by_reset`
    are U26's (absent). Default: (a)/(b) read `devices/dev.toml`'s `conn_fail_to_hotspot`/`hotspot_time_min` with
    `tomllib` under `harness.configured_max_connections(device="dev")`'s convention (`tests_hardware/harness.py:37`) and
    the `wifi.*` constants from `src/asy_wifi_service.py` by a file-local source read; (a)'s derived wait is
    `conn_fail_to_hotspot × (connect poll + refresh) + grace + mode switch + settle + one hotspot start`, plus a tagged
    margin; U26 swaps in its helpers.
23. **A-23 Part N basis wording** for every new row: "estimated (agent, <commit>) — measurement owed: …"
    (`test_tunables_register.py`'s estimated-basis rule) unless measured; the two product rows take the packet's basis.
24. **A-24 E65's row** keeps its name and text with `"retired": true` (as `:40, :134, :153`); `test_error_catalog.py`'s
    retired check then proves no live site.
25. **A-25 constant names at U22.** The packet's M.SRC_NET.077 text names `_LED_DEACTIVATED_ON_MS` and other `_MS`
    constants (U31's form); the tree is in seconds (`asy_wifi_service.py:146-181`). W writes only (2)'s changes on
    HEAD's names.
26. **A-26 allow-list rows the lanes re-key.** `_decision_vocab_allowlist.txt:323` keys `tests/test_asy_wifi_service.py:1610`
    ("All four _conn_phase values are exercised deliberately"), which W rewrites to five: the lead re-keys or drops
    the row (shrink only). No other row keys a comment a U22 lane must rewrite (grep of both lists).
27. **A-27 the commit wording of the CLAUDE.md edit** (row 16): "the one meaning change, following the owner's
    requirements of 2026-10-08"; every other doc edit "no meaning change" beyond OR151/OR152.

## 6. What U13-U21 changed in U22's files, and parts already landed

`git -C wt-u22fold log --oneline 1cff5a2..HEAD -- <file>` (`1cff5a2` is U14's commit, so the range is U14's fix to U21):
- `src/asy_wifi_service.py`: `f1f800e` (U18: the snapshot, every transition persisted, the client pattern, the stations
  `None`), `f5c8255` (U19), `f76385a` (U20). `src/asy_neopixel_driver.py`: `c11ca0a` (U17), `f5c8255` (U19).
  `src/asy_notification_service.py`: none in the range.
- tests: `test_asy_wifi_service.py` `f1f800e f5c8255 f76385a`; `test_asy_neopixel_driver.py` `2977c4e c11ca0a`;
  `test_asy_notification_service.py` `2977c4e f76385a`; `test_neopixel_wifi_integration.py` `c11ca0a f1f800e f5c8255
  f76385a`; `test_notification_neopixel_integration.py` `c11ca0a`; `test_setter_microdot_integration.py` `5689e2f
  f1f800e f5c8255`; `test_digital_twin_sensortask_integration.py` `5689e2f f1f800e f76385a`;
  `test_digital_twin_network_neopixel.py`, `tests/neopixel.py`, `tests/network.py`, `digital_twin/network.py`,
  `digital_twin/neopixel.py`: none. `tests_scripts/test_fault_or_warning_never_both.py`: `5689e2f 2977c4e f1f800e f5c8255`.
- `tests_hardware/bench/test_hotspot_role_reversal.py`: `f5c8255 f76385a`. `buildgen/error_catalog.json`: `5689e2f
  2977c4e c11ca0a f1f800e f5c8255 f76385a`. `pyproject.toml`: `5689e2f c11ca0a f1f800e f5c8255 f76385a 65088de`.
  `scripts/typecheck.sh`: `65088de`.
- docs: `SPECIFICATION.md` (12 commits), `CLAUDE.md` (6), `BACKLOG.md` (9), `README.md` (`8618e7f c11ca0a 65088de`),
  `DEVICE_REFERENCE.md` (`5689e2f 2977c4e f1f800e f5c8255`), `tests_hardware/README.md` (6), `digital_twin/README.md` (5).

Landed (report the line, do not redo): A.U22.01 (c), the `finally` order (`asy_neopixel_driver.py:117-121`); SF-B2
(`asy_notification_service.py:74-84, :203, :313-320`, `_WRN_NOTIFY_SIGNAL_DROPPED` `:56`, catalog `:173`); SF-M2-02's
code (`asy_ntp_client.py:513-519`); SF-M2-04's client pattern (`asy_wifi_service.py:170-173, :495-499, :694-702`);
SF-M3-01's SGP40 half (`asy_sgp40_driver.py:85-88, :178-183`); M.SRC_NET.081 (1) (`:273-287`); M.SRC_NET.087's rename
and arm (`:477-504`); M.SRC_NET.077 (1)'s five warnings (`:58-62`), `_STAT_JOINED_NO_IP` (`:201`), `_PM_NO_POWERSAVE`
(`:204`); M.SRC_SENS.033's construction-time service (`:167-206`); M.SRC_SENS.025's starters, `get_error_sources() ->
"list[ErrorSource]"` (`:141`), unquoted `get_loggers()` (`:147`), `reset_error_counter() -> bool` (`:184`); M.SRC_SENS.020's
runtime imports and `ErrorSource, TimerStarter` (`:7-26`); M.SRC_SENS.030's `TickSeconds, utc_now`, `LogConfig`
(`:13-15`); the A.U9 arbitration tests (`tests/test_asy_neopixel_driver.py:461-700`) and the setup and starters tests
(`:701`, `:959`); A.U19.14 (`DEVICE_REFERENCE.md:137`, BACKLOG item 24 gone, `SPECIFICATION.md:2912`); A.S0930.13
(`src/asy_system_service.py:197, :216, :365`); A.U7.01 (`SPECIFICATION.md:4548`; `tests_hardware/README.md:3`'s
backend wording is M.HW_BENCH.110's U36 part); A.U14.28 (F.7, `:6022`); A.SDEP.08 ("already newest", D1); A.U0.31
partly (`digital_twin/_http_client.py:1`, three README tags; the README's `:119` "deliberately duplicated" site is
M.TWIN.058's U36 text, not U22's); DEVICE_REFERENCE's window and refusal sentences (`:22-24`).

## 7. Deferred-in items; build environment; what CI runs and the time it adds

Deferred into U22: U9's attribute removal (register `:234`); U18's SF-M2-02 sentence and SF-M2-04's LED (code landed,
docs here); U15's SF-M3-01 notification half; OF-75; OF-79 (moved on, A-15); the fold's two owner requirements.

Build environment: `pyproject.toml` changes lint and type configuration only (rows 45, 46); E writes X2 in the chroot
list. No dependency, pin, script, toolchain or CI file changes; no Unix-port or firmware rebuild of the toolchain is
needed (`/root/pico-toolchain` read-only for every lane). The firmware image grows by the new bytecode (a few hundred
bytes to ~1 KB, **(unverified)**); the lead's six-device build reads the size line against the filesystem boundary.

What changes in CI (no `ci.yml` edit), with estimates the lanes replace by measurements (single files at `nice -n 19`):
- **L1 unit** (`unit-tests`, `unit-tests-gc-threshold`, `unit-tests-coverage`): W ~+38 tests under `_FastAsyncSleep`
  and the fake `Timer`, the 500-period case included, est. +8-15 s per stage; P ~+20 tests, est. +3-5 s; per-device
  `test_sensortask_<device>.py` ×6 gain F4/X4 asserts, est. +0.2 s each.
- **Mock** (the L1 cross-module files): rows 42, 44, X4, est. +1-2 s per stage.
- **L2 twin in-process** (`tests/test_digital_twin_*.py`, inside `scripts/test.sh`): row 51's three scenarios run in
  real time (5 s loop refresh, 4 s mode switch, 5 + 3 s reconnect grace and settle), est. +90-150 s for
  `test_digital_twin_sensortask_integration.py` per stage, more under settrace's CPU share: the unit's largest time
  cost and its main risk (A-19); row 50's fake cases < 1 s. The twin CI suite (`run_digital_twin_ci.sh`,
  `digital-twin-e2e`) runs unchanged scenarios: ~0.
- **L0**: the fault-or-warning list shrinks by one; definitions/catalog cases +1-2: ~+1 s.
- **Web**: `definitions-mockdata-coverage.test.js` sees one more field (X1/X3): ~0.
- **L3/L4**: nothing runs; R3 grows by (a) (~3-4 min with the reopened hotspot's rejoin) and the opt-in (b) (~18 min,
  two windows on `dev`).

Steps → CI jobs: rows 10-14, 20, 22-25, 27, 29-31, F2 change frozen product code (`firmware-build-verify` rebuilds every
image; `digital-twin-e2e` boots it); rows 43, 33-39, F3, 40-41, 44, 42, X4, F4 add or change L1 files (`unit-tests`,
`unit-tests-gc-threshold`, `unit-tests-coverage`); rows 50, 51 change L2 files run by the same three jobs; rows 45, 46
change `lint-and-typecheck` (ruff's per-file entry, mypy's baseline); rows 2, 47, X3 change L0 (`unit-tests`' backgrounded
pytest tier) and, with X1, the generated definitions the web jobs read; rows 17, 18 change only collect-only
(`tests_hardware` is never run by CI); docs rows change only the L0 doc checks.

## 8. Pitfalls specific to U22

- **Every mode, every tier (the brief's first pitfall):** §9's matrix is the checklist; a lane that finds a cell
  uncovered reports it with the reason, never leaves it implied.
- **The restart path into the silent mode (A-3):** `_reset_wlan_connect_state()`, then `_apply_initial_led_config()`,
  then `_handle_reconnect_trigger()` on the restart's own `_reconn_wifi` — all three must keep `_PHASE_SILENT`; an
  unreadable config at that restart still gives `_PHASE_DEACTIVATED` (`:308-313`), which is right.
- **The watchdog:** a silent attempt is one ordinary STA attempt (synchronous `network.country()`/`hostname()`/
  `active(True)`/`connect()`, then a 10 × 0.5 s awaited poll) under `wifi_mode_lock`; the supervisor's feed is a
  separate task, so nothing new blocks it. `WLAN.scan()` is never called (it waits up to 10 s in
  `mp_event_wait_ms()`, `network_cyw43.c:236-246`, past 8,388 ms; F.2); W's row 43 (5) pins it by source text and by a
  test-local radio `scan` that fails the test.
- **Non-blocking (CLAUDE.md "Long-blocking operations"):** the wait between periods holds no lock and yields every
  5 s iteration; W's non-blocking test proves a second task takes `wifi_mode_lock` within one iteration.
- **The hotspot timer is shared:** the window's `PERIODIC` timer (`:484-488`) is the silent period too; every
  deinit site (`_handle_reconnect_trigger()`, `_hotspot_client_connected()`, `_reset_wlan_connect_state()`, the
  window-end trigger, the link) also clears `_hotspot_timer_running`; a dropped soft callback re-fires one period later
  (C.9); `Timer.init()`'s `OSError(ENOMEM)` and `MemoryError` are each persisted once per failure and retried.
- **Memory (both GC stages, zero `MemoryError`, no `gc.collect()` props):** the silent mode allocates per period only
  the attempt's config reads; the refresh allocates per overlay wake (A-13); `State` adds one slot to each `NOTIFY`
  tuple. Retained growth is proven structurally (timer arms, history slots, no task or list left), never by a
  heap reading after a collection or by brute-force scale. Injected `MemoryError`s keep `_RaiseOnArm`'s wording, clear
  of "MemoryError" and "memory allocation failed" in the output. `tests_scripts/test_digital_twin_boot_contiguity.py`
  (the boot survivors, L0) re-runs on the merged tree (W adds two attributes to a boot survivor).
- **`ThreadSafeFlag` waits under `select.poll()` (F.7 row 12):** the refresh's runner task waits on the flag; a test
  that cancels the overlay task awaits it (as `_cancel_all()` does) so the waiter unregisters; every `uart.poller`-style
  double stays bounded; a test that cancels mid-wait gives the cancelled runner one `sleep(0)` before the next
  `asyncio.run()`.
- **No nested `asyncio.run()`:** row 42 and every helper that runs setup run it at synchronous test scope.
- **Yield-bounded waits (A-13):** re-derive `_PHASE_YIELDS`, `_PATTERN_YIELDS` and the `_run_until()` bounds from
  the new hop count after the refresh lands; never replace them by wall-clock sleeps.
- **The twin's WLAN model follows the product in the same unit:** row 48's two knobs land with W's product; the AP
  link poke is test-local (A-7); `tests/test_digital_twin_real_website_integration.py:28-29`'s phase mirrors and
  `tests/_sensortask_scenarios.py:50-51`'s stay valid (values 0-3 unchanged, 4 added).
- **The twin's shortcut:** `_connection_failures` set after the fresh-boot reset (`_handle_reconnect_trigger()`
  zeroes it), as HEAD's comment at `test_digital_twin_sensortask_integration.py:898-905` already warns for the restart.
- **The UART wire format is untouched**; no U22 file is a UART module.
- **FRAM-backed logs:** W80, W77 and the attempt verdicts persist into WIFI's FRAM-backed history; the bench cases
  read it and never clear it (stage 5's `reset_all_error_logs()` runs earlier in the module, so (a)/(b) compare
  before/after snapshots); in phase C the FRAM logs are read before any `ResetErrors` (CLAUDE.md), stated in X5.
- **The comment cap (≤ 3 prose lines per block);** tag lines are data; the packet's owner quotes in comments keep the
  "(owner, 2026-10-08: '…')" form.
- **No audit ID in permanent text** (no "OR151", "SF-M3-09", "OF-75", "W1"); decision tags on every decision sentence.
- **`tests_hardware/`:** nothing runs; T runs `uv run pytest --collect-only tests_hardware -q`,
  `test_persistence_write_marker_completeness.py` (a's PUT is marked; `joined_hotspot` stays in
  `_KNOWN_PERSISTING_HELPERS`), `test_tests_hardware_persistence_write_gating.py` (its probe collects only
  `tests_hardware/flash/test_bus_concurrency.py`, `:11`, so its count of 7 is unchanged), `test_level_containment.py` (`COVERS_TWIN_SCENARIOS` unchanged), `test_tunables_register.py` (the new `l4.*`
  tags) and `test_hardware_verdict.py`.
- **The persistence-write rules for the bench cases:** (a) owns one flash write (the wrong password), marked; (b) owns
  none and carries the marker only as the AND-gate of A-6, said in its comment; the stage-0/stage-7 prerequisite writes
  stay unmarked (the owner's owns-vs-reached-through rule, 2026-09-18).
- **A check is never weakened; allow-lists only shrink:** the fault-or-warning table loses one row; a new mixed pair
  goes through the lead with its reason; the decision-vocabulary row of A-26 is re-keyed or dropped by the lead.
- **Two port-binding suites never run together:** `npm test` (the web tier) and `scripts/test.sh` are the lead's;
  lanes run single files under `unshare -n` (`u21/CONCURRENCY.md` rule 5), the twin in-process file included.
- **The shared toolchain is read-only for lanes;** no rebuild is expected at U22 (no C, override, variant or toolchain
  change); the generated device modules are regenerated in each lane's worktree after a `src/` or `buildgen/` change.
- **The silent-failure scan** (standing check) covers the changed files in these modes, each named in the record:
  STA seeking and established, hotspot without and with a client, the silent mode (entry, each period, a failed and a
  linking attempt, a dropped fire, a failed arm), the unreadable-config state, a task restart and a settings change in
  each, the `LEDWifiOn` push in each, the chip-down stations answer, a radio that never comes up, the LED (overlay
  on/off, each pattern, a running signal, a refused/queued/expired request, a task restart, a blanked pixel), the
  notification (each `State` code, a stale or missing producer, a busy LED, the default sink), and the pairs: a window
  end beside a settings change, a period fire during a reconnect, a restart during the window-end streak, a refresh
  during a ramp.

## 9. Test plan, timing, and the checks the lead re-runs on the merged tree

### 9.1 Mode coverage (the brief's matrix; "+" = added at U22, `HEAD` = existing, staged = later unit)

| mode | unit (L1) | mock (L1, cross-module) | twin (L2) |
|---|---|---|---|
| STA seeking (streak, attempt verdicts) | HEAD (`test_asy_wifi_service.py:1911-2023`, `:2123`, `:2938`) | HEAD (`test_neopixel_wifi_integration.py:65` toggle/on/off) | HEAD (test 5's streak, CI Run 7) |
| STA established (60 s retry, never the hotspot) | HEAD (`:2105`, `:2393`) + row 43 (1) (after a silent link) | HEAD (`test_ntp_wifi_dns_integration.py:450-492`) | HEAD (every booted test links) + row 51 (a)'s relink |
| hotspot, no client | HEAD (`:1738-1857`, `:2481-2580`) | HEAD (`test_neopixel_wifi_integration.py:151`) | HEAD (test 5) + row 51 (b) |
| hotspot with a client; stations rule | HEAD (`:1721`, `:2466`) + row 43 (1)/(2)/(4)/(7) (unconfirmed = no client, 32 entries) | HEAD (`:174`) | + row 51 (c) (A-7) |
| silent | + row 43 (1)-(6) | + row 44 | + row 51 (a) |
| unreadable config (deactivated) | HEAD (`:1066-1146`, `:2204`, `:3020`) + A-4's regression | + X4 | staged U25 (A-17) |
| task restart in each | HEAD (hotspot `:2697`, deactivated `:2614`, seeking/established `:2624`, `:3042`) + silent (row 43 (3)) | n/a by A-18 | + silent (A-18 in row 51 (a)) |
| settings change in each | + row 43 (1) (hotspot, silent, established) + A-4 (refused while deactivated) | + row 42 (hotspot, established), X4 (every device's wiring) | + row 51 (b) (hotspot) |
| `LEDWifiOn` push in each | HEAD (`:1066-1185`) + row 43 (6) (silent) | HEAD (`:206`) + row 44 | + A-18 in row 51 (b) (off) |
| LED: overlay on/off/toggle, each Wi-Fi pattern, LED disabled | HEAD (FakeLED tests `:785-1146`) + row 43 (6) | HEAD (`:65-224`) + rows 44, X4 | HEAD (test 5 writes) + row 51 (a)/(b) |
| LED: signal ramp, refusal, queue, deadline, cancel | HEAD (`test_asy_neopixel_driver.py:299-700`) | HEAD (`test_notification_neopixel_integration.py`) | HEAD (the midnight-window flash test `:490`) |
| LED: task restart; blanked pixel refresh | + rows 35, 34 | - | staged U25/U35 (A-17; M.TWIN.132 (1)) |
| notification `State`, stale sample | + F3, row 39 (2) | + F4 (per device, `/status`) | staged U25 (M.TWIN.144 (11), (12)) |

### 9.2 Tests by lane, tier and owner test type; how each is seen failing first

Every new test is written before its product change and run once on the tree first; the failing line is recorded in
the hand-back. A test that passes at once is a guard and is named as one.
- **W, L1** `tests/test_asy_wifi_service.py` (row 43; the owner's types for OR151):
  function (1): the second streak enters the silent mode once; one attempt per fired period and a link is a normal
  connection; a failed silent attempt stays silent with no streak; no attempt between periods; the identity hook from
  the hotspot, the silent mode and a link lands in the fresh-boot state; the window end keeps its meaning; a settings
  trigger beside a window end wins; the watcher dispatches by phase; the unfilled stations answer is a failed check; an
  unconfirmed check counts as no client — each fails on the tree at `_src_const("_PHASE_SILENT")` (not found) or at
  the phase assert (`_PHASE_DEACTIVATED`), the missing fresh flag, or the stations `None`/timer assert.
  error handling (2): the period arm raising `OSError(ENOMEM)` and `MemoryError` (one `E TIMER` each, retried, mode
  kept); the silent attempt's `connect()` raising (`WLAN_STA_START`, the hardware streak, the give-up and restart keep
  the mode); the stations query raising under a client — fail on the tree (no silent mode; the timer left as it was).
  resilience (3): 500 periods against a radio that never links (500 attempts, one `WLAN_NO_AP` slot after the
  `WLAN_SILENT` one, `arms` 1, no flash or DNS task, the same used slots after period 1 and 500); a restart in the
  silent mode; a restart in the window-end streak (as HEAD: a guard); a dropped fire recovered — fail on the tree
  except the named guard.
  self-healing (4): three end-to-end integrations under `_HotspotRadio`, `_FastAsyncSleep`, `_ParkedFlag` with the loop
  and the watcher as tasks — the unit goes silent after its second streak and rejoins when the router returns; new
  credentials over the hotspot reopen it once more; an unfilled stations answer never holds the hotspot — fail on the
  tree at the deactivated phase / the second hotspot / the held window.
  non-blocking (5): no `.scan(` in the source and a failing test-local radio `scan` (a guard: passes on the tree); the
  silent wait holds no lock and yields (fails on the tree: no silent mode).
  LED (6): dark through the silent attempt and `set_wifi_led(status=True)`, lit at the link, dark with `LEDWifiOn` off;
  the no-configuration pattern holds (HEAD's test, a guard).
  regression (7): the HEAD tests rewritten in place (row 43's list), A-4's regression. Est. +8-15 s per stage.
- **P, L1** `tests/test_asy_neopixel_driver.py`: rows 35's three restart cases (fail on the tree: no overlay re-apply
  at a restarted task), row 34's refresh case under `_DrivenClock` (fails: no rewrite after the period), the per-wake
  structural proof of A-13. `tests/test_asy_notification_service.py`: F3's five `State` cases (fail: no field),
  row 39 (2) stale sample (fails: evaluated), rows 38/39 (1) `None` asserts (fail: `False`), A.U22.02's removals (the
  assert lines go; `test_check_one_returns_the_most_recent_trigger_state` a guard). Typing: each module's removal from
  the baseline is first seen failing in the main mypy pass, then cleared. Est. +3-5 s.
- **P, mock** `tests/test_neopixel_wifi_integration.py`: row 44 (fails: the deactivated pattern blinks), X4's
  no-configuration case (a guard on the tree's behaviour, new coverage). `tests/_sensortask_scenarios.py`: F4 (fails:
  no `State` key), X4's fresh-flag assert (fails: no flag). `tests/test_readiness_gates.py`: the two expectations
  (fail on the tree's 2-tuple). L0 `tests_scripts/test_buildgen_definitions.py`: the `State` row with its codes (fails:
  no row). Est. +1-2 s.
- **T, mock** `tests/test_setter_microdot_integration.py`: row 42 (fails: no fresh flag; `_hotspot_started_once`
  stays true).
- **T, L2** `tests/test_digital_twin_network_neopixel.py`: row 50's two knob cases (fail: no knob).
  `tests/test_digital_twin_sensortask_integration.py`: row 51 (a) with A-18's restart, (b) with `LEDWifiOn` off, (c)
  with A-7's poke — each fails on the tree (deactivated after the second streak; no second hotspot; the timer stays
  stopped). Est. +90-150 s per stage (A-19).
- **T, L4 (collect-only)**: row 18 (a), (b) — unrun here; seen failing first is impossible without a board, so the
  hand-back says "collected, unrun, phase C R3"; their L0 checks (§8) run.
- **E, D**: no tests; `test_citations.py`, `test_decision_vocabulary.py`, `test_comment_block_cap.py`,
  `test_tunables_register.py`, `test_error_catalog.py` (the `NotifyState` table's shape) on the merged tree.

### 9.3 Checks the lead re-runs on the merged tree

1. `scripts/lint.sh` (ruff with the narrowed per-file entry, RUF100) and `scripts/typecheck.sh` (main pass no-args and
   `src tests tests_hardware/device_scripts`, twin pass for `digital_twin/network.py` and the twin test files, host pass
   for `buildgen/` and `tests_scripts/`); `test_mypy_any_baseline.py`.
2. Regenerate the device modules; rebuild the frozen website (definitions and samples changed).
3. L0 once: `test_error_catalog.py`, `test_fault_or_warning_never_both.py`, `test_buildgen_definitions.py`,
   `test_api_reference.py`, `test_tunables_register.py`, `test_citations.py`, `test_decision_vocabulary.py` (allow-lists
   regenerated, shrink only), `test_code_conventions.py`, `test_comment_block_cap.py`,
   `test_digital_twin_boot_contiguity.py`, the bench L0 checks of §8; tier time against the 1200 s bound.
4. `scripts/test.sh` and `GC_THRESHOLD=32768 scripts/test.sh` (each in its own worktree and `unshare -n`), and
   `scripts/test.sh --coverage`: zero `MemoryError`/"memory allocation failed"; the twin in-process file's time against
   A-19's 168 s.
5. The six twins (`run_digital_twin_ci.sh <device>`) and `npm test` per gate_v10's layout (the web tier sees X1/X3).
6. The six-device firmware build once (the frozen modules changed; the image size line).
7. `uv run pytest --collect-only tests_hardware -q` (board-free).
8. No audit ID in the touched permanent text; every new comment block ≤ 3 lines; OF-75 closed with its line; OF-79
   re-targeted per A-15; the register's fold rows marked landed; the scan record names every mode of §8's last bullet.
9. CI after push: `unit-tests`/`unit-tests-gc-threshold`/`unit-tests-coverage` per-file times for the twin in-process
   file, the web jobs for the definitions change, `firmware-build-verify` for every device's image.
