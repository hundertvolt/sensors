# U22 lane T: final report

Branch `audit/u22-t`, worktree `scratchpad/wt-u22t`.
- **WIP:** `45f5c23`
- **Merge of `audit/u22-api` (4f8264c):** `da493fc`
- **First final:** `ac3e213` (row 51 in the old file, over A-19's line; kept in history)
- **Final:** `85c82b9` (the A-19 restructure; not pushed)

## A-19: the decision, applied (rulings.md item 7)

The first form had the three scenarios inside `tests/test_digital_twin_sensortask_integration.py` (ac3e213). It ran 211.7 / 216.1 / 220.7 s, against 61.9 / 65.0 / 70.0 s for the base copy, so it was over the 168 s line at every stage. The decision moves it into one real-time boot in a new file.

**`tests/test_digital_twin_wifi_modes.py`** holds one scenario, `test_stations_rule_settings_change_and_silent_mode_in_one_boot`. The product's waits stay untouched (option 3 rejected). Its stages, in order:
1. **(c)** In the first hotspot, a client is listed and stops the window. A chip-down stations answer then counts as no client: the window re-arms, and one `WLAN_STATIONS_UNKNOWN` slot is still one after a further check.
2. **(a)** A credentials change through the identity group lands in the fresh-boot state, and the failed streak reopens the hotspot once more. WIFI's history shows two `WLAN_TO_HOTSPOT` and no `WLAN_SILENT`. The pixel stays dark through both hotspot phases with `LEDWifiOn` off.
3. **(b)** `LEDWifiOn` is turned on through its own group: Valid, and no reconnect. The window then ends and the second streak goes silent: no hotspot, the STA interface, the LED dark. A connect-task restart keeps the mode and re-arms the period. A failed period stays silent and dark, with one attempt and one `WLAN_SILENT` slot. A later period links (STA established, timer stopped, LED lit).

Every assert of the separate form stays, with the same condition waits. Every message names its stage.

Two asserts moved, because one boot cannot hold both LED settings at once:
- The separate settings-change scenario checked darkness with `LEDWifiOn` off through its silent end. That check now ends before stage (b).
- Stage (b) checks the silent mode dark with `LEDWifiOn` *on*, as the separate silent scenario did, which is the stricter case.

The `LEDWifiOn` push (Valid, no reconnect) is a new assert.

**Times** (s, `nice -n 19`, `unshare -n`, plain / 32768 / settrace; all pass, zero `MemoryError`, zero "memory allocation failed"):

| file | times |
|---|---|
| `tests/test_digital_twin_wifi_modes.py` (new, 1 test) | 101.3 / 101.6 / 101.9 |
| `tests/test_digital_twin_sensortask_integration.py`, back to 4f8264c (15 tests) | 61.7 / 65.3 / 70.4 |

**Seen failing first:**
- The new file against 18a02f8's `asy_wifi_service.py` overlay fails at stage (c): `AssertionError: (c) an unconfirmed stations check left the window stopped` (46 s).
- (a) and (b) rest on ac3e213's separate-form runs (below).

**Old file:** `git diff 4f8264c -- tests/test_digital_twin_sensortask_integration.py` is empty. Every part of my ac3e213 edit there served the three scenarios: the imports `code`, `STAT_GOT_IP`, `set_access_point_up` and `WifiService`, the two tags, the section helpers and the three tests. So nothing stays.

**New file's rules:**
- A 3-line header.
- No import from a `test_` file. `run_generic_integration` and `sensortask_wozi` are not test files.
- No new shared module.
- In `finally`: every task cancelled (overlay, watcher, connect loop, the service's DNS and flash tasks), the window timer deinited, the access-point switch and the per-object chip-down knob restored.
- No explicit `Any`, so no `typecheck.ini` or baseline entry.
- No `pyproject.toml` entry needed: ruff is clean as is.
- Its own scratch key `wifi_modes` and its own port 19200 (passed to `build_system()`, never bound).

**Copied for U24's shared helpers**, from the old twin file unless noted:
- the module setup (`sys.path` gains `ext`, `digital_twin` and `digital_twin/unixport`; `prewarm_poll_set()`; `patch_asy_udp_socket_for_unix_port()`);
- `_boot()` (the `_boot`/`_build` pair merged: wiring plan, `WDT(run_generic_integration._WDT_TIMEOUT_MS)`, `build_system()`, `run_setups()`);
- `_wiring_plan()`, `_run_timed()` (was `run_timed`), `_cancel()`, `_wait_until()` and `_wait_until_async()`;
- `_wifi_const()`, which also exists in `tests/test_setter_microdot_integration.py` and as `_src_const()` in `tests/test_asy_wifi_service.py`;
- `_fire()`, `_first_attempt()`, `_await_hotspot_window()`, `_end_hotspot_window()`, `_stop_scenario()` and `_wifi_log()`, from ac3e213's section.

**mypy:** the twin pass checks the new file (53 files, was 52; it appears in the verbose log). The main pass's exclude `tests/test_digital_twin_.*\.py$` keeps it out: 187 and 174 files, unchanged, and never named.

**Registration:** `"wifi_modes"` is added to `COVERS_TWIN_SCENARIOS` in `tests_hardware/bench/test_hotspot_role_reversal.py`. `test_level_containment.py` passes with no edit. Its `_families()` finds `wifi_modes` by glob, and `_covered()` names the role-reversal module as its cover.

## Step table

| row | M-id | status | note |
|---|---|---|---|
| 17 | M.HW_BENCH.071 (2) | applied | Stage-8 comment set to the packet's three lines verbatim. The U26 form is not written. |
| 18 | M.HW_BENCH.073 (1) | applied | (a) `test_a_wrong_password_over_the_hotspot_reopens_the_hotspot` is `persistence_write` and sits between the invalid- and real-credentials tests. (b) `test_a_second_failed_streak_goes_silent_and_links_on_a_later_attempt` is `long_soak` with the in-test skip without `--soak-tier`, plus `persistence_write` as the AND-gate (A-6), and sits after the real-credentials test. Its waits are derived from `devices/dev.toml` and the `src/asy_wifi_service.py` constants plus one tagged margin (A-22). Collected only, never run. `destructive_last` and the merged flip-back test are U26's. |
| 42 | M.TEST_UNIT.296 (1) | applied | `test_an_identity_change_lands_the_unit_in_the_fresh_boot_state`, after the LED-only setter test. |
| 48 | M.TWIN.040 (2) | applied, with deviation 1 | `set_access_point_up(*, up)` and the per-object `WLAN.stations_chip_down`. The U25 rewrite is not written. |
| 50 | M.TWIN.132 (2) | applied | The two knob cases. The A.U22.01 case and the fake cases are U25's (A-17). |
| 51 | M.TWIN.144 (19) | applied, per A-19 | One real-time boot in the new `tests/test_digital_twin_wifi_modes.py`, stages (c), (a), (b). A-7's poke is in (c). A-18's additions: the connect-task restart in (b), and `LEDWifiOn` off through (a)'s two hotspot phases. Parts (15) and (17) are U25's. The old twin file is back at 4f8264c. |

Already landed: none of these parts.

## Deviations

1. **Keyword-only knob.** The knob is `set_access_point_up(*, up)`, not `(up: bool)`. pyproject's FBT rule makes our own boolean parameters keyword-only (`set_wifi_led(*, status)`); I fixed the inconsistency rather than add a `noqa`.
2. **Twin fake test file import.** It imports `set_access_point_up` at module top. A function-local import fails `test_import_placement`.
3. **Wi-Fi modes file import.** `tests/test_digital_twin_wifi_modes.py` imports `from network import STAT_GOT_IP, set_access_point_up` at module top (the shape the earlier in-file form needed, because test 5's local `import network` is on `_PENDING`); its `WLAN` annotation is a typing-only import.
4. **Bench (b) leaves the DUT's hotspot with `BenchBridge(ap_conn=ROLE_REVERSAL_CLIENT_CONN).ap_down()`.** NetworkManager blocks a user-deactivated profile from autoconnect (nmcli(1), "connection down"), so the radio cannot rejoin and the window can end. `bench_control.py` has no "leave the hotspot with the AP left down" primitive (see the findings).
5. **Bench (b) checks its precondition.** If the hotspot still answers with an empty SSID, it fails with a message naming the real-credentials test. With the soak runner's `-m long_soak` alone it would otherwise run without that test's write.
6. **Bench (a) derives its wrong password** from the bench's own (first character changed, same length). There is no new password literal, so no new S105 site.
7. **Bench history comparison.** `_gained_entries()` reads the entries WIFI's history gained between two reads. The history is a fixed-length window shifted by one slot per new code. When no shift fits (a reset in between), it raises rather than guess.
8. **Row 42 uses a local `_YieldOnlyAsyncio` view** of `asy_wifi_service.asyncio`, restored in `finally`. The packet names `_FastAsyncSleep`, which is local to `test_asy_wifi_service.py`; the shared helper is U24's.
9. **D.15 order** is applied to `digital_twin/network.py` (a pure reorder, AST-checked), to the twin fake test file's helpers, to the bench file's helpers (`_dut_reachable_again` moved up) and to the new Wi-Fi modes file (private helpers, alphabetical). It is not applied to the existing helpers of the setter file: its topical section headings would split, and D.15 requires removing those in a separate change first; U27 rewrites that file. My new helpers there are D.15-ordered among themselves. The sensortask integration file is back at its base.
10. **Reads by source.** Phases and `wifi.*` constants are read from source by a file-local helper (`_wifi_const`) in the Wi-Fi modes, setter and bench files.
11. **One boot for the three scenarios, per A-19** (rulings.md item 7). Stages run (c), (a), (b). `LEDWifiOn` is off for (c) and (a) and turned on through its own group before (b) (see the A-19 section for the two asserts that moved).

## Files outside my set

None edited. Needed or found:
- `tests_hardware/bench_control.py`: lacks a primitive that leaves the DUT's hotspot with the bench AP still down (deviation 4). U26.
- `digital_twin/README.md` gets the knob sentence (E, below).

## Facts owed to other lanes

### D: new tags, each needing a Part N row

Basis for all three: "estimated (agent, ac3e213) — measurement owed" unless stated.

- **`l4.hotspot_role_reversal_derived_wait_margin_s = 30.0`**
  - Sites: `tests_hardware/bench/test_hotspot_role_reversal.py` — `30.0`.
  - Dependants: the derived waits in the bench cases. `_streak_bound_s()` (the fresh-streak reopen bound) is refresh + grace + switch + settle + conn_fail_to_hotspot × (poll + refresh) + switch. The other waits are the leave wait (refresh + grace), the window-end wait (window + 2 × refresh + grace) and the relink wait (window + poll + refresh).
  - Basis: the bench's scan cadence (a `--rescan yes` nmcli call up to 15 s, plus the 2 s poll) and a link loss NetworkManager notices late. Measurement owed on R3.
  - Re-check trigger: a `wifi.*` constant, `conn_fail_to_hotspot`/`hotspot_time_min` or the bench host changes.
- **`l2.wifi_modes_wait_poll_s = 0.25`**
  - Sites: `tests/test_digital_twin_wifi_modes.py` — `0.25`.
  - Basis: the poll period of the file's condition waits, copied from `l2.sensortask_integration_wait_poll_s`. Each wait's latency is at most 0.25 s.
  - Dependants: `l2.wifi_modes_wait_timeout_s`, which is counted in its iterations.
- **`l2.wifi_modes_wait_timeout_s = 25.0`**
  - Sites: `tests/test_digital_twin_wifi_modes.py` — `25.0`.
  - Basis: the longest single transition waited for. A window end or settings change reaches the next phase within refresh 5 + grace 5 + mode switch 4 + settle 3 + one attempt (twin 0.7 s + poll), about 18 s. It is counted in poll iterations. It also bounds the scenario's short waits (the first attempt, the lit frame).
- **`l2.wifi_modes_run_bound_s = 200.0`**
  - Sites: `tests/test_digital_twin_wifi_modes.py` — `200.0`.
  - Basis: the scenario's backstop, about twice the measured 101 s and under `scripts/test.sh`'s 240 s per-file bound.

Withdrawn before reaching main: `l2.sensortask_integration_wifi_mode_wait_timeout_s` and `l2.sensortask_integration_wifi_mode_run_bound_s` existed only in ac3e213 and went with the old file's revert.

Also for D: SPEC E.2.1's wozi-only sentence (around `:4222`, on `tests/test_digital_twin_sensortask_integration.py`) may name `tests/test_digital_twin_wifi_modes.py` too, for the same reason: mandatory infrastructure only, a device-independent mechanism. The new file's header cites "SPECIFICATION.md Part E.2.1".

### API end states

**`digital_twin/network.py`**
- `set_access_point_up(*, up: bool) -> None`, over `_access_point_up = [True]`. While it is down, a completed connect ends `STAT_NO_AP_FOUND` with the unconfigured address and consumes no scripted outcome.
- `WLAN.stations_chip_down: bool` (default False). While set, `status("stations")` returns 32 `(bytes(6),)` tuples.
- `_MAX_STAS = 32` (`network_cyw43.c:377`).

**New tests**
- Twin fake: `test_a_downed_access_point_fails_every_interface_object_until_switched_back`, `test_a_chip_down_stations_answer_is_32_unfilled_entries`.
- Twin L2: the new family `wifi_modes`, file `tests/test_digital_twin_wifi_modes.py`, test `test_stations_rule_settings_change_and_silent_mode_in_one_boot`.
- Mock: `test_an_identity_change_lands_the_unit_in_the_fresh_boot_state`.
- Bench: (a) and (b), as in row 18 above.

### For the lead

- Allow-list lines: none added, retired or re-keyed.
- Any-baseline: none. I used `Callable[[str], None]`, not `[..., None]`, which the host pass counts as an explicit `Any`.
- Catalog: none.
- New raises: `HardwareTestFailureError` in the bench's `_gained_entries()`. Test helpers raise `AssertionError`.
- Frozen website: no input of the website changed.

### E

**`digital_twin/README.md`:**
- The `network.py` bullet: the two knobs as in the API end states above.
- The in-process tier passage (`:233-243`, on `tests/test_digital_twin_sensortask_integration.py`) may gain one sentence on `tests/test_digital_twin_wifi_modes.py`: the Wi-Fi modes after a hotspot, at real product time, one boot, wozi-only.

**`tests_hardware/README.md` (row 19, A-20):**
- (a) owns one flash write (the wrong password), and the real-credentials test restores it.
- (b) writes nothing. `persistence_write` is only the AND-gate on the real-credentials test's write. `long_soak` gates its length: about 19-20 min on `dev` (fresh streak bound about 101 s with the margin, rejoin, the 8 min window, the second streak, about 128 s of observation, then a relink within one period).
- (b) needs the whole module with `--soak-tier` and `--allow-persistence-writes`. The bench runner excludes `long_soak`, and the soak runner's default `-m long_soak` selects (b) without its precondition, where it fails at its precondition check.
- A candidate invocation, unverified because nothing ran on hardware: `scripts/run_bench_soak_tests.sh --tier short --allow-persistence-writes -m role_reversal`. Pytest takes the last `-m`.
- Both cases read WIFI's history before and after and never clear it.

**BACKLOG X5 row:**
- (a): about 3-4 min, one owned write.
- (b): about 20 min, 0 writes, its gate as above.
- Read the FRAM-backed logs first (CLAUDE.md).

## Tests run (all `nice -n 19`; MicroPython runs under `unshare -n`)

**Seen failing first**
- Row 50, on the pre-knob fake: `AttributeError: module 'network' has no attribute 'set_access_point_up'`; and `AssertionError: [(b'\x02\x00\x00\x00\x00\x01',)]` (the flag had no effect).
- Row 42, on 18a02f8's `asy_wifi_service.py` as an overlay: `AttributeError: 'WifiService' object has no attribute '_reconnect_fresh'`.
- Row 51, on the same overlay:
  - (a): `the streak after the hotspot window ended in phase 3, not the silent mode`
  - (b): `AttributeError ... '_reconnect_fresh'`
  - (c): `an unconfirmed stations check left the window stopped`
- Row 18: collected, unrun (phase C, R3).

**Results.** Wall times in s are plain / 32768 / settrace; every listed run passed with zero `MemoryError` and zero "memory allocation failed".

| file | before | after | after, merged tree |
|---|---|---|---|
| `tests/test_digital_twin_network_neopixel.py` (24 → 26 tests) | 11.97 / 11.95 / 12.01 | 14.76 / 14.79 / 14.84 (WIP); 14.82 / 14.84 / 14.92 (final) | 14.83 / 14.83 |
| `tests/test_setter_microdot_integration.py` (39 → 40 tests) | 3.89 / 4.13 / 4.02 | 3.91 / 4.15 / 4.07 | — |
| `tests/test_digital_twin_sensortask_integration.py` (15 tests) | 60.7 / 63.1 / 68.0 (18a02f8); 61.9 / 65.0 / 70.0 (base product) | ac3e213: 211.7 / 216.1 / 220.7 (18 tests); 85c82b9: 61.7 / 65.3 / 70.4 (back to base) | — |
| `tests/test_digital_twin_wifi_modes.py` (new, 1 test) | — | 101.3 / 101.6 / 101.9 | — |

**L0 and type checks**
- `ruff`: clean on all five files.
- `mypy`: main pass (no-args, and `src tests tests_hardware/device_scripts`), twin pass and host pass all clean, with a cold cache.
- `pytest --collect-only tests_hardware`: 120/145 collected, 25 deselected (+2, my two `persistence_write` tests).
- Green: `test_decision_vocabulary`, `test_citations`, `test_comment_block_cap`, `test_legacy_paths`, `test_import_placement`, `test_code_conventions`, `test_error_catalog`, `test_host_annotations`, `test_lint_ceilings`, `test_mypy_any_baseline`, `test_memory_error_gate_agreement`, `test_persistence_write_marker_completeness`, `test_tests_hardware_persistence_write_gating`, `test_level_containment`, `test_hardware_verdict`.
- Red, expected: `test_tunables_register`, only for the Part N rows D writes. P's `led.overlay_refresh_ms` (`src/asy_neopixel_driver.py:38`) and `notify.sample_max_age_s` (`src/asy_notification_service.py:68`); mine at `tests/test_digital_twin_wifi_modes.py:45`, `:47`, `:49` and `tests_hardware/bench/test_hotspot_role_reversal.py:69`.
- On 85c82b9, rerun: ruff on all six files; the four mypy passes (twin pass 53 files); the L0 set above with `test_level_containment` green; collect-only 120/145; the setter file 3.94 / 4.20 s at both GC stages.

**Runs.** Every run of mine was foreground, is entered in `u21/RUNS.md` and has exited. No process of mine is running; the `micropython` processes seen on the host belong to `wt-u22p` and `wt-u22w`.

**Files for you to run:**
- `tests/test_digital_twin_wifi_modes.py`, `tests/test_digital_twin_sensortask_integration.py`, `tests/test_setter_microdot_integration.py` and `tests/test_digital_twin_network_neopixel.py`, at both GC stages and under settrace;
- `pytest --collect-only tests_hardware` and the bench L0 checks above;
- `test_tunables_register` after D's rows land.

## Silent-failure scan

Scope: my files, both passes. Wi-Fi modes checked: STA seeking and established; hotspot with and without a client; the silent mode (entry, a failed period, a linking period); the unreadable-configuration state; a task restart and a settings change in each; the LED (on, off, the hotspot pattern, the overlay).

| # | site | class | mode | effect | status |
|---|---|---|---|---|---|
| 1 | rp2's stations query when the radio cannot come up | 1 | hotspot, chip down | Answers 32 unfilled entries. | Covered by the M.SRC_NET.081 (2) and M.SRC_NET.224 product (W1); now modelled in the twin (row 48) and pinned at L2 (row 51 (c)). |
| 2 | `bench_control.BenchBridge.ap_down()` | 4 | role reversal, (b) | Tolerates "not an active connection" silently. If the client profile is not active when (b) leaves, nothing blocks NetworkManager's autoconnect, so the bench could rejoin and the window never ends. | **New.** It ends in a loud timeout, not a silent pass. Fix: a bench_control primitive that leaves the hotspot with the AP left down, at U26. |
| 3 | `joined_hotspot` teardown, `leave_dut_hotspot_and_restore_bridge()` after (b) | 5/6 | flip-back after (b) | `ap_up()` re-activates an already-active `br0-wifi-ap`; NetworkManager takes it down first (`nm-manager.c`, `_internal_activate_device()`). That drops the relinked DUT, whose STA retry is 60 s, against stage 8's 90 s wait. | **New**, for M.HW_BENCH.071's U26 rewrite of stage 7/8. Not changed here: row 17 is the comment only. |
| 4 | Stage 7's restore PUT | 4 | flip-back | Best-effort: after (b), or with the DUT off its hotspot, it only prints a RESULT NOTE. | Covered: M.HW_BENCH.071 (U26), where a rejected or unreachable restore raises. |
| 5 | Test 5 (twin hotspot test) | 6 | twin process | Leaves the service's flash task and the armed 8 min hotspot-timer task alive after it ends. They run inside later tests' loops. | **New**, for M.TWIN.144's U25 rewrite of test 5. The new file cancels and deinits everything in `finally`. |
| 6 | The twin AP never reports `STAT_GOT_IP` | 3 | twin hotspot | The stations path runs only with the poke. | Covered: A.U25.72 (U25). Row 51 (c) uses A-7's poke. |
| 7 | Twin `status("rssi"/"stations")` off-mode, and `raise_on` keeping one exception instance | 1 | twin | Does not raise as cyw43 does; one instance is re-raised. | Covered: M.TWIN.040 (U25). |
| 8 | The process-global `set_access_point_up` knob | 6 | twin process | A test failing without restoring it would fail every later connect. | Inherently safe: restored in `finally` everywhere. U25's `reset_test_state()` takes it over. |
| 9 | Bench (b)'s absence check | 4 | (b) | Treats a raising scan as "absent". | Inherently safe: the decisive proof is the gained `WLAN_SILENT` slot in WIFI's history and the relink. |
| 10 | The unreadable-configuration state | — | — | Not reachable from my files. | Mock and L1 coverage are P's and W's; the twin case is staged at U25 (A-17). |
| 11 | The silent mode with a settings change | — | — | No request reaches a silent unit. | Inherently safe (A-3). |
| 12 | The silent mode with a dropped fire or a failed arm | — | — | — | W's L1 tests. |
