# U22 lane D final report

Branch `audit/u22-d`, worktree `scratchpad/wt-u22d`, on the integration head `6d23c7d`. One commit, `2551e0b`
("U22 lane D: SPECIFICATION.md for the Wi-Fi silent mode, the fresh-boot settings change, the stations rule, the overlay
refresh and the notification State"), with the two trailer lines. Not pushed. File: `SPECIFICATION.md` only
(+150/-72). Line numbers below are this tree's, after the commit.

## Step table

| row | M-id | status | where and note |
|---|---|---|---|
| 4 | M.SPEC.016 (1) | applied | A.4's owner list (`:459-465`). The permanent-deactivation item is now the silent-mode item, tagged with the owner's quote. "a human resubmitting credentials" is now "a Wi-Fi settings change (new credentials included), which lands in the fresh-boot state (owner, 2026-10-08)" (deviation 3). |
| 5 | M.SPEC.021 (17) | applied | A.8's `/networking` sentence (`:992-1003`) gains the fresh-boot clause and the owner's quote. Placement is deviation 4. The code-table sentence (`:956-958`) names the notification's `State` (`NotifyState`, A.4), per A-8. |
| 6 | M.SPEC.058 (15) | applied | C.7's WIFI observation sentence (`:3029-3036`) is the packet's text. The carried A.U19.14 had already landed: C.7 names "BACKLOG.md item 32" at `:2960`. W's addition is also applied: the `_error_check()` paragraph (`:3013-3016`) says that in the silent mode, an iteration with no attempt due and no failed radio or timer operation is no evidence, so the streak neither counts nor heals (agent, 2026-10-12). |
| 7 | M.SPEC.064 (6) | applied | C.8's hold table (`:3334`). The connect-attempt row names the silent attempt and W's method, `_run_silent_mode()`, and the permanent-deactivation row is gone. Following W's fact, the waiter analysis (`:3347-3348`) adds that the wait between two silent-mode attempts is outside the lock. |
| 8 | M.SPEC.082 (8) | applied | E.6.4's load-bearing finding (`:4673-4680`) is the packet's text. |
| 9 | M.SPEC.146 (5) | applied | L.3's `hotspot_time_min` row (`:8850`): consumer "`WifiService`: the hotspot window, and the silent mode's connect-attempt period (A.4)". Range clause kept. |
| 21 | M.SPEC.163 (1)-(4) | applied | (1) A.4 Wi-Fi bullet (`:419-449`), (a)-(c). (a) has deviation 3. (2) C.9: the LED flash row (`:3526`), with deviation 5, and the `PERIODIC` sentence (`:3543-3546`), which also names `_arm_hotspot_timer()` (W's C.9 fact). (3) F.1 (`:5339-5346`): `_STATIONS_UNSET` and the defect's new end. (4) Part N rows `wifi.wlan_down_settle_s` (`:10017`, Dependants only, per W's fact that the mode switch is its only site) and `wifi.led_deactivated_on_s`/`_off_s` (`:10025-10026`); IDs, values, Sites, Basis, Margin and triggers unchanged. |
| 28 | M.SPEC.014 + (1)-(5) | applied | A.4 NeoPixel/notification bullet (`:352-389`), restated whole with A.U22.01's "The pixel reports no faults …" sentence and parts (1)-(5). A-8's marked table (`:392-399`) is `<!-- catalog: status.NotifyState -->`, equal to the catalog's five texts. Deviations 1 and 2. A.S0930.13 is carried, but its A.4 watchdog paragraph sits elsewhere, so nothing lands here (plan §1). |
| F1 | M.SPEC.156 (9) | applied | Part N: `led.overlay_refresh_ms` (`:10045`) and `notify.sample_max_age_s` (`:10049`), with the packet's Basis, Margin and trigger. `sgp40.comp_max_age_s` and the client pair were already landed at `:10061` and `:10023-10024` respectively (U15/U18). |
| A-8 | (ruling) | applied | The marked table in A.4, plus the A.8 sentence (rows 5 and 28). |
| A-14 | (ruling) | applied | Part G.2 (`:6291-6296`) gains "A stale producer sample": one rule with its two sites (`_current_value()`, `_check_one()`) and both Part N IDs. No shared helper (agent, 2026-10-08). |
| Part N | §3 tags | applied | Seven rows. These are exactly the seven red lines of the integration head's `test_tunables_register.py` (listed under "Facts owed"). |
| twin file | ruling 7 | applied | E.2.1 (`:4283-4286`): `tests/test_digital_twin_wifi_modes.py` is wozi-only for the same reason as the sensortask integration file, and has a file of its own for its wall time. That is the only place the SPEC lists twin files by name. E.6.1's table names them by glob. No E.6.6 row is needed: registration goes through `COVERS_TWIN_SCENARIOS`. |
| sweep | brief | applied | Searched for every name U22 renamed or removed. No remaining hit for `_deactivate_wlan_permanently`, `WLAN_OFF`, `E65`, `_WRN_WLAN_DEACTIVATED`, `_ERR_WLAN_OFF`, "permanent deactivation", "permanently deactivat", "switched off", "until a power cycle", "deactivated WLAN", "deactivation path", `_PHASE_DEACTIVATED` or "terminal state". One further sentence that P's change made false was fixed: C.14.2 (`:3907-3909`) said `_check_one()`'s `None` is "treated as 'not triggered'"; it now reads "the signal not evaluated, published as `State` 3, A.4 — not an error". |

## Deviations (conservative, each reported for review)

1. **A.4's NeoPixel bullet keeps HEAD's construction clause.** The kept text is "(`signals=`, C.14.3): the constructor validates each in check order, prints a refusal at once and builds the combined schema, and `setup()` persists each refusal once". The packet's merged text has only "(C.14.3)".
   - The clause is true on this tree (`asy_notification_service.py:184-205`).
   - It came from U5 (`c3df14e`) and is stated nowhere else in the SPEC; C.14.3 does not carry it.
   - Dropping it would lose a true fact.
2. **NotifyState codes: the sentence points to the table.** The sentence says `State` "takes the codes of the table below". It does not repeat the five codes inline as the packet's (1) does.
   - A.8's rule gives every `/status` code table one source, and the marked table carries the same five texts as the catalog.
   - An inline second copy could drift unchecked once the marker test (a later unit) lands.
   - The sentence also names where the sample is published, `/status`'s `notification` block, per A-8 (the packet's "published" with no route).
3. **"Credentials change" becomes "Wi-Fi settings change", following the code.** This affects A.4's Wi-Fi bullet and the owner list.
   - The code sets the fresh-boot flag in `reconnect_wifi()` (`asy_wifi_service.py:965-969`). Every Wi-Fi field (`SSID`, `PW`, `Country`, `Hostname`, `HotspotPW`) fires that function (A.8, `:992`).
   - So a Hostname or Country change also lands in the fresh-boot state, not only a credentials change.
   - A.4 now reads "A change of any Wi-Fi setting that reconnects (A.8; new credentials among them)". The owner list reads "a Wi-Fi settings change (new credentials included)". The owner's quote ("Any change of credentials …") is kept verbatim.
   - E.6.4 keeps "a credentials change", which is its scenario.
   - This is a difference between the packet's wording and the code, reported as the brief asks.
4. **A.8's fresh-boot clause sits after the sentence's second owner quote**, not straight after "tries the stored network". Inserted there, it would have sat in front of the "(owner, 2026-10-08: '2. a.' …)" tag, which answers a different question. Decision-records rule 3 forbids changing a tag's scope. The text is unchanged.
5. **C.9's LED flash row: the lifetime column is completed.** It now lists the window end (`_on_hotspot_window_end()`, which `reconnect_wifi()` runs too) and the silent-mode entry as cancel paths, as the code has them (`:563-570`, `:679-681`). The packet changed only the "why" column. The old column was incomplete rather than false.
6. **Part N basis commits come from `git log -S` on this tree, not from T's report.**
   - T gave `ac3e213` for all four of its tags. `git log -S` gives `85c82b9` for the three `l2.wifi_modes_*` tags and `45f5c23` for `l4.hotspot_role_reversal_derived_wait_margin_s`. P's `7b548af` for the `l1` tag matches.
   - All of these are lane commits, which the unit's squash will drop from main's history. That is the same as U21's `a2d7ee2`/`5b6dc1b`/`8c38f9d` rows, which are not ancestors of `6d23c7d`.
   - Lead: keep them, as U21 did, or rewrite them to the squash commit.
7. **The `led.overlay_refresh_ms` row states the per-wake cost in words.** The Dependants cell says: "two short-lived tasks … built per wake, not per period", citing `extmod/asyncio/funcs.py:24-30`, which I read at v1.29.0.
   - A-13: no U22 text says "once per period".
   - It carries no byte figure; the allocation catalog row is U30's.
   - P's measured figure (896 B per wake, 64-bit Unix port) is left to U30 and the lead.
8. **One reflow with no meaning change.** The owner list's FRAM item (`:465-470`) was re-wrapped because the edit before it moved its line breaks. Its text is unchanged.

## Files outside my set

None edited, none needed. For E (no SPEC heading changed or added; the headings E may cite are unchanged):
- A.4 now holds the `NotifyState` table, the silent mode and the fresh-boot rule.
- C.8 holds the hold table.
- E.2.1 names the new twin file.
- Part N holds the seven new rows.

## Facts owed

**Part N rows added**: seven, no tag renamed or withdrawn. Every Basis is in A-23's form except the two product rows, which take the packet's basis.

| ID | Value | Sites | Basis |
|---|---|---|---|
| `led.overlay_refresh_ms` | 300000 ms | `src/asy_neopixel_driver.py` — `300000` | the default notification `FlashInterval`, about once per notification cycle (agent, 2026-10-06); Margin: a blanked pixel wrong for at most one period; trigger: a `FlashInterval` default change |
| `notify.sample_max_age_s` | 10800 s | `src/asy_notification_service.py` — `10800` | three times BMP3XX's longest `SampleInterval` (3600 s) (agent, 2026-10-06); Margin: a producer late by up to three intervals still counts; trigger: a producer's interval maximum changes |
| `l1.sensortask_notify_cycle_rounds` | 200 | `tests/_sensortask_scenarios.py` — `200` | estimated (agent, `7b548af`) — measurement owed: rounds per monitor cycle, both GC stages, slowest host, L1 |
| `l2.wifi_modes_wait_poll_s` | 0.25 s | `tests/test_digital_twin_wifi_modes.py` — `0.25` | estimated (agent, `85c82b9`) — measurement owed: elapsed at both GC stages on the slowest host, L2 |
| `l2.wifi_modes_wait_timeout_s` | 25.0 s | `tests/test_digital_twin_wifi_modes.py` — `25.0` | estimated (agent, `85c82b9`) — measurement owed: the longest transition, L2; derived path ≈ 18 s |
| `l2.wifi_modes_run_bound_s` | 200.0 s | `tests/test_digital_twin_wifi_modes.py` — `200.0` | estimated (agent, `85c82b9`) — measurement owed: elapsed on the slowest host, L2; ≈ 2× the 101.3/101.6/101.9 s T measured here |
| `l4.hotspot_role_reversal_derived_wait_margin_s` | 30.0 s | `tests_hardware/bench/test_hotspot_role_reversal.py` — `30.0` | estimated (agent, `45f5c23`) — measurement owed: each derived wait's elapsed on the dev bench, L4 |

**Rows changed (Dependants only):** `wifi.wlan_down_settle_s`, `wifi.led_deactivated_on_s`, `wifi.led_deactivated_off_s`.

**API end states as the SPEC now states them (from W's code):**
- `_PHASE_SILENT = 4`.
- `_STATIONS_UNSET = 32`.
- `_run_silent_mode() -> bool`.
- `_arm_hotspot_timer()` is the one arm path.
- `_on_hotspot_window_end()`.
- `reconnect_wifi()` sets the fresh flag.
- W80 `WLAN_SILENT`; W77 counted as no client; E65 retired.
- `NOTIFY("Triggered", "State", "TS")`; `State` 0-4.

**For the lead:**
- Allow-list lines: none added, retired or re-keyed. `test_decision_vocabulary.py` and `test_citations.py` are green on my tree, and no allow-listed SPEC sentence was touched.
- Any-baseline lines: none.
- New raises: none.
- `_ALLOWED`: no change.
- Doc facts for E: none beyond the above.

## Tests run

All on my tree, foreground, `nice -n 19`, `/home/user/sensors/.venv/bin/python -m pytest -q -p no:cacheprovider tests_scripts/<file>`. Docs only: no MicroPython file, no GC stages, no test file grown, so no wall times apply.

**Seen failing first:** `test_tunables_register.py` on the integration head, 1 failed / 14 passed. The failure was exactly the seven lines "`<site>`: `<id>` is tagged but has no SPECIFICATION.md Part N row":
- `src/asy_neopixel_driver.py:38`
- `src/asy_notification_service.py:68`
- `tests/_sensortask_scenarios.py:2374`
- `tests/test_digital_twin_wifi_modes.py:45`, `:47`, `:49`
- `tests_hardware/bench/test_hotspot_role_reversal.py:69`

After the rows: 15/15 passed.

**Baseline before editing**, all green: `test_decision_vocabulary` 6, `test_citations` 15, `test_comment_block_cap` 453, `test_legacy_paths` 3, `test_error_catalog` 33.

**After the edits**, all green:

| file | passed |
|---|---|
| `test_decision_vocabulary` | 6 |
| `test_citations` | 15 |
| `test_comment_block_cap` | 453 |
| `test_tunables_register` | 15 |
| `test_legacy_paths` | 3 |
| `test_import_placement` | 7 |
| `test_code_conventions` | 23 |
| `test_error_catalog` | 33 |
| `test_host_annotations` | 12 |
| `test_lint_ceilings` | 19 |
| `test_mypy_any_baseline` | 7 |
| `test_memory_error_gate_agreement` | 13 |

The SPEC-reading checks for the sections I edited also pass: `test_level_containment` 22, `test_lock_order` 10, `test_task_inventory` 6, `test_toml_schema_contract` 3.

`ruff check` over the eight scopes reports "All checks passed!". I did not run mypy, because no Python file changed.

**Runs:** every run was foreground and under a minute (the longest was `test_error_catalog` at 21 s), so none went into `RUNS.md`. All have exited. `ps` shows only the lead's `test_sensortask_dev.py` run in `wt-u22fold`.

**Files the lead runs on the merged tree (with E's half):**
- `test_citations.py`
- `test_decision_vocabulary.py`
- `test_comment_block_cap.py`
- `test_tunables_register.py`
- `test_error_catalog.py`
- the SPEC readers `test_task_inventory.py`, `test_toml_schema_contract.py`, `test_lock_order.py` and `test_level_containment.py`

## Silent-failure scan

**Scope.** My file (`SPECIFICATION.md`), read against the code on this tree:
- `src/asy_wifi_service.py`, `src/asy_neopixel_driver.py`, `src/asy_notification_service.py`;
- the catalog;
- the pinned `extmod/network_cyw43.c`, `lib/cyw43-driver/src/cyw43_ctrl.c` and `extmod/asyncio/funcs.py` (v1.29.0);
- the WS2812 datasheet (text extracted, glyph shift 29). It reads "Built-in electric reset circuit and power lost reset circuit" and "After the pixel power-on reset, the DIN port receive data from controller".

**Modes checked:**
- Wi-Fi: STA seeking, STA established, hotspot without and with a client, the silent mode, and the unreadable-configuration state. In each: a task restart, a settings change, and the `LEDWifiOn` push.
- LED: enabled, disabled, each Wi-Fi pattern, the overlay and its refresh, a running signal.
- Notification: each `State` code.

**Findings:**

1. **New. Class 6 (a fault without self-healing). Mode: silent mode with a period arm that keeps failing** (alarm pool exhausted, `OSError(ENOMEM)`).
   - What happens: `_run_silent_mode()` (`asy_wifi_service.py:734-750`) persists one `TIMER` error per failed arm and retries each 5 s iteration. It neither sets `_hw_op_failed` nor reports an attempt. So `_connect_loop()` runs no `_error_check()` (`:422-430`).
   - Effect: a pool that never recovers leaves the unit silent forever. It makes no attempt, is unreachable, its LED is dark, and nothing escalates in this module. The only escalation comes indirectly, through another module's failed arm (NTP's timers end their task).
   - Comparison: the hotspot mode has the same retry-only shape (C.9: "a failed hotspot-timer arm persists `TIMER` and is retried on the next cycle"), but there the unit stays visible and reachable on its hotspot.
   - Proposed smallest fix, for W's file and the lead: in the silent mode, a failed period arm sets `_hw_op_failed = True`. The streak then climbs to the restart, and the task budget to a fresh boot. W's error-handling test `test_a_failed_period_arm_is_persisted_and_retried_in_the_silent_mode` would then also pin the escalation.
   - Not fixed here: the code is not in my set. A related inconsistency, not U22's: C.7.2 says "a timer that cannot be armed is re-armed at the next opportunity, then its task ends for the supervisor", which the hotspot timer never does.
2. **Covered (W, deviation 4). Class 7 (asymmetric reporting). Mode: silent mode, radio linked between periods.**
   - The phase stays silent and the LED dark until the next period, at most one `hotspot_time_min`.
   - In that window `/status` already shows a link.
   - At the next period the link is taken as normal.
3. **Inherently safe (A-3, recorded by W). Mode: silent mode with a settings change.** No request reaches a silent unit. A reboot, including the supervisor's task-budget reboot, is a fresh boot.
4. **Inherently safe (A-4, W's regression test). Mode: unreadable configuration with a settings change.** The store refuses the write, so `reconnect_wifi()` never fires. The SPEC states that the state lasts until a reboot reads the configuration.
5. **Covered (row 28 (3), P's refresh; OF-75). Class 1 (an ignored status from the layer below). Mode: LED, a pixel blanked by a supply dip.**
   - The WS2812 has no status to read; the datasheet's power-lost reset is detected by nobody.
   - The refresh bounds the wrong overlay to one period. The SPEC now states this with the datasheet citation.
6. **Covered (P, A-5 review row `REGISTER.md:583`). Class 7. Mode: LED, notification ramps during the Wi-Fi silent mode.** The shared pixel still flashes notifications while Wi-Fi is silent.
7. **Doc-only, outside U22, not changed. Mode: a task restart in STA or the silent mode.** C.7.2's "the WiFi service's restart forces a fresh WLAN object" is imprecise:
   - A restart in STA or the silent mode runs `_handle_reconnect_trigger()`'s plain reconnect (disconnect and wait), not a new `network.WLAN()`.
   - A new interface object comes only from a mode switch, or from the participant rung before the give-up (`_recover_device()`).
   - This is pre-existing, so it is listed as a finding, not fixed (exec prompt rule 7).
8. **New (minor), reported by P and kept open here. Class 7. Mode: the notification sample on the Status page.**
   - The page labels `TS` "Last Trigger Timestamp" (`buildgen/definitions.py:701`), but `TS` is the last cycle's time, stored on every cycle, State 1 and 4 cycles included.
   - No step owns the label. The SPEC text does not repeat it.

## Follow-up round (coordinator, 2026-10-12): commit `9452be3` on top of `2551e0b`

**1. Fresh-boot scope.** The setter hook belongs to the identity group alone: `SSID`, `PW`, `Country`, `Hostname`, `HotspotPW` (`buildgen/validate.py:117`; `LEDWifiOn`'s group at `:118` has no hook).
- Checked every fresh-boot sentence I wrote against that scope.
- A.4's Wi-Fi bullet (`:428`) now reads "A change of a Wi-Fi setting that reconnects (A.8; new credentials among them)". It used to say "any".
- The owner list (`:463-465`) carries the same scope: "only a change of a Wi-Fi setting that reconnects (A.8; new credentials among them), which lands in the fresh-boot state (owner, 2026-10-08)".
- E.2.1 (`:4286-4289`) says "a reconnecting settings change landing in the fresh-boot state", where it used to say "the fresh-boot settings change".
- Already in scope, left as they are: A.8 (it names the five keys); E.6.4 ("a credentials change", a subset); the Part N `l2.wifi_modes_*` Dependants (the scenario's identity-group change).
- The owner-list FRAM item was re-wrapped, no text change.

**2. Off-branch basis hashes in Part N.** Each new hash is the on-branch commit `git log -S` gives on `65088de`. I ran the search for the row's tag line and for its constant line; the two always agreed, except for the NTP pair noted below.

| old | new | rows | command (per row; `<file>` the Sites file) |
|---|---|---|---|
| `5b6dc1b` | `65088de` | `tool.apt_step_timeout_s`, `tool.bench_bridge_recovery_arm_s`, `tool.bench_bridge_up_poll_s` | `git log -S'@tunable <id> = <literal>' --format=%h 65088de -- toolchain/setup_toolchain.py` and `-S'_<NAME> = <literal>'` |
| `8c38f9d` | `65088de` | `tool.remote_query_timeout_s`, `tool.network_step_timeout_s`, `tool.build_step_timeout_s`, `tool.node_shasums_timeout_s`, `tool.node_tarball_timeout_s` | the same, `toolchain/setup_toolchain.py` |
| `a2d7ee2` | `65088de` | the seven `l1.lwip_host_*` rows | the same, `tests/lwip_host/test_modlwip_eagain.py` |
| `64ca641` | `c11ca0a` | `l1.asy_base_classes_piece_rounds` | the same, `tests/test_asy_base_classes.py` |
| `bab72bc` | `c3df14e` | `ntp.retry_s_default`, `ntp.retry_max_s_default` | `git log -S'_DEFAULT_RETRY_S = const(10)' --format=%h 65088de -- src/asy_ntp_client.py` (and `_DEFAULT_RETRY_MAX_S = const(600)`) gives `c3df14e`; see the note |
| `8f61712` | `f1f800e` | `udp.poll_idle_ms` (not in your list, added) | the same, `src/asy_udp_socket.py` |

Notes:
- **NTP pair, the one place the searches disagree.**
  - The tag line `@tunable ntp.retry_s_default = 10` gives `01e8e3e` (U8, the tag scheme).
  - The value itself first appeared as the parameter default `retry_s: int = 10` at `c20f80b`.
  - I wrote `c3df14e` because it is the old hash's own on-branch copy: `git show bab72bc -- src/asy_ntp_client.py | git patch-id --stable` equals the same for `c3df14e` (`330c7778000a`), and both carry the same subject, "U5: config objects; max-args 8". It is also what the constant-line search returns.
  - The literal's introducing commit is ambiguous in the strict sense. If you want "keep the old hash" applied literally, revert these two cells to `bab72bc`.
- **`8f61712`** was missing from your list because its basis is written "(agent, 2026-09-30, `8f61712`)", date before hash. It meets the same off-branch criterion. It is the U18 lane-U WIP commit, squashed into `f1f800e`, and both searches give `f1f800e`. Revert it if you want the list taken as closed.
- **After the change:** the only Part N hashes not on `65088de` are my five new rows' lane hashes (`7b548af`, `85c82b9` ×3, `45f5c23`), kept as you decided. No other backticked hash anywhere in SPECIFICATION.md is off-branch.

**3. C.7.2** (`:3099-3104`). The code states it plainly, so the sentence is fixed rather than reported. It now reads: the WiFi service gives up only after its participant rung re-initialised the radio (`_recover_device()`, a fresh WLAN object, C.7), while its restart itself only disconnects a STA that is up (from the hotspot it switches to a new STA interface) and starts a fresh streak.
- Code: `_connect_loop()` resets `_err_cnt_internal`. `_reset_wlan_connect_state()` sets `_reconn_wifi` from the phase or `isconnected()`/`active()`. `_handle_reconnect_trigger()` then either runs `_wait_for_sta_disconnect()` (a disconnect and wait on the same object) or, from the hotspot, `_leave_hotspot_mode()`, whose `_switch_wlan_mode()` makes a new `network.WLAN(STA_IF)`.
- The rest of the paragraph was re-wrapped with no text change.

**Checks on `9452be3`.** Each file was run on its own at nice 19, all green:

| file | passed | file | passed |
|---|---|---|---|
| `test_decision_vocabulary` | 6 | `test_host_annotations` | 12 |
| `test_citations` | 15 | `test_lint_ceilings` | 19 |
| `test_comment_block_cap` | 453 | `test_mypy_any_baseline` | 7 |
| `test_tunables_register` | 15 | `test_memory_error_gate_agreement` | 13 |
| `test_legacy_paths` | 3 | `test_level_containment` | 22 |
| `test_import_placement` | 7 | `test_lock_order` | 10 |
| `test_code_conventions` | 23 | `test_task_inventory` | 6 |
| `test_error_catalog` | 33 | `test_toml_schema_contract` | 3 |

Every run was foreground, none longer than 21 s, and all have exited.

**Step 4.** Applied in `ec1e3ca`; see the next section.

## Step 4 (coordinator, 2026-10-12): commit `ec1e3ca` on top of `9452be3`, the final state

The coordinator accepted the NTP-pair choice (identical patch-id) and the `udp.poll_idle_ms` rewrite.

**Written from W's final `6fbbf2c` on `audit/u22-w`.** I read it with `git show`/`git diff b283d81 6fbbf2c` and did not merge it into my branch.

What the code does:
- `_run_silent_mode()` now reads: `if not self._hotspot_timer_running and not await self._arm_hotspot_timer(): self._hw_op_failed = True`.
- `_connect_loop()` runs `_error_check((None,), condition=self._hw_op_failed)` when `evidence or self._hw_op_failed`.
- So an idle silent iteration whose period arm failed counts as a failure.
- W's test `test_a_silent_period_that_cannot_be_armed_feeds_the_hardware_streak` pins the outcome:
  - the give-up comes at iteration `max_module_error + 1`;
  - `DEVICE_RECOVERY` is logged before it;
  - the restart keeps `_PHASE_SILENT`.

W's sentence matches the code. My C.7 text is wider by design: "no failed radio or timer operation" also covers a failed STA disconnect in the reconnect path, which sets `_hw_op_failed` too (`_disconnect_sta_and_wait()`).

**SPEC changes.**
- **C.7, the `_error_check()` paragraph** (`:3014-3020`). After the "neither counts nor heals" sentence it now says: a period that cannot be armed is such a failure. With no period, no attempt is ever due, so each failed arm counts, as a failed re-arm of the uptime tick does. The streak then climbs the same way while task restarts keep the silent mode (agent, 2026-10-12).
- **C.9, the timer paragraph** (`:3567-3569`). The existing "a failed hotspot-timer arm persists `TIMER` and is retried on the next cycle" gains: in the silent mode, where it leaves no attempt due, it also counts toward the WiFi task's hardware streak (C.7).
- **The hotspot mode is not stated as a rule anywhere.**

**One statement that the hotspot-mode open finding makes false (reported, not changed).** C.7.2's "Network faults recover …" paragraph (`:3146-3147`) says "a timer that cannot be armed is re-armed at the next opportunity, then its task ends for the supervisor".
- In the hotspot mode, a failed window arm never ends the task. It is retried and logged every iteration, and the window never ends. This was already so before U22.
- In the silent mode the sentence now holds, through the streak.
- C.9's specific sentence about the hotspot timer is accurate in both modes.

**Checks on `ec1e3ca`.** Each file was run on its own at nice 19, all green:

| file | passed | file | passed |
|---|---|---|---|
| `test_decision_vocabulary` | 6 | `test_host_annotations` | 12 |
| `test_citations` | 15 | `test_lint_ceilings` | 19 |
| `test_comment_block_cap` | 453 | `test_mypy_any_baseline` | 7 |
| `test_tunables_register` | 15 | `test_memory_error_gate_agreement` | 13 |
| `test_legacy_paths` | 3 | `test_level_containment` | 22 |
| `test_import_placement` | 7 | `test_lock_order` | 10 |
| `test_code_conventions` | 23 | `test_task_inventory` | 6 |
| `test_error_catalog` | 33 | `test_toml_schema_contract` | 3 |

Every run was foreground and under 21 s, and all have exited; no process of mine is left.

**Scan update.** The class-6 finding (finding 1: a silent-mode period arm that keeps failing never escalates) is closed for the silent mode by W's `6fbbf2c`, and C.7/C.9 now state that. The hotspot-mode case remains an open finding for the owner, held by the lead.

**Note for the merge.** My branch states `6fbbf2c`'s behaviour but does not contain it. The SPEC and the code agree once the lead merges W's final.

**Commits on `audit/u22-d`:** `2551e0b`, `9452be3`, `ec1e3ca`.
