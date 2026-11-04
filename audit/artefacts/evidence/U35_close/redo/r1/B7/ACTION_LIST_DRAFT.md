B7 LED: action list draft (agent, Tue Nov  3 19:37:39 UTC 2026)

Base: `S/wt-b7` (`audit/r1-b7`) at `d6bc7617` (B1-B6 merged); line numbers are that tree's. Pre-audit `25caf528`,
post-U10 `8d44fd14^`. Files: `src/asy_neopixel_driver.py` ("NP"), `src/asy_notification_service.py` ("NS"); the
`State` field's sites in `buildgen/codegen.py`, `buildgen/definitions.py`, `buildgen/error_catalog.json`,
`mockdata/samples.json` and the tests. `review_hunks.py 25caf528 d6bc7617` leaves 36 unmarked hunks in NP (9) and NS
(27), saved as `B7/review_hunks_src.out`; items 1-13 name them by mechanism, item 15 takes any they miss. B1 already
dropped the `report_if_fatal()` calls (NT-8); B2 converted NS `setup()`. No clarification is open for B7.
Each item: what (file:line) / decision / basis / test (the pinning tests that go first, by file:line).

**1. NP-5, the 300 s overlay rewrite.** `_OVERLAY_REFRESH_MS` with `@tunable led.overlay_refresh_ms` NP:36-39; the
`wait_for_ms()` wrapper and its WS2812 comment NP:79-84.
- Decision: restore `await self._overlay_start.wait()` (`25caf528` NP:72): -5 lines, and the lost cancel goes with it.
- Basis: owner 2026-10-28 05:58 (LN358): "Where do the hardcoded 5 minutes come from? ... If it is and a closer look
  still holds, it's rather a structural issue and not something to patch over like that."; 06:37 (LN362): "hardcoded
  delay checks like this are a very bad, very awkward pattern". Premise refuted on silicon: 0 deviated samples in
  12 x 10 min, 794,560 Wi-Fi burst packets (`bench/READING_20261029.md:35, :93`). Its cascade defect: a cancel in
  `wait_for`'s cleanup window is lost, 8/8 (`S/u35/lead/probe/np_verify/`; C.md NP-5; REPORT 3); DECREV 3.2; G4R05.
- Test: go first: `tests/test_asy_neopixel_driver.py:275` (one rewrite per period), `:317` (the wrapper's per-wake
  tasks), `tests/test_digital_twin_network_neopixel.py:610`. New, red today: overlay on, nothing pending, no frame in
  2 x 300,000 ms of driven time, and a cancel at any instant of the wait (the old refresh instant included) ends the
  task (the probe's `np_lost_cancel.py` case). Green: `:162-245`, `:1083`. Comments naming the refresh wait
  (`:876`, `:1038-1039`) mechanical.

**2. NP-3, the entry sanitiser.** `_signal_values()` NP:48-57 and its calls NP:149, :167; `_MAX_SIGNAL_S` NP:28;
`_clamp_byte()` without its catch NP:44-45; the ramp reading pre-clamped values NP:99-104.
- Decision: restore the per-channel clamp with its NaN/inf catch (`25caf528` NP:29, :36-40) and the ramp's own floor
  and clamp (`:162-173`: `not t >= _MIN_SIGNAL_S`, +inf's `OverflowError` as one step, `_clamp_byte()` per channel);
  the 60 s cap and the move to the entry go; both entries store `[r, g, b, t]` as given.
- Basis: brief and plancheck R1 B7.3 (FIX); callers bound every value (REST `_LIGHT_CMD_FIELDS` t 0.5-60; NS FlashBri
  1-255 x weight 0/1, FlashDur 0.5-10, NS:105-107); S2-G1-19 (H, typing); legacy floor `neopixel_signal.py:128`.
- Test: change first: `test_clamp_byte_direct` `:958` gains NaN, +inf, -inf -> 0 (red: `int(nan)` raises today). Go
  first: `:1057` (60 s cap), `:1101` (cap equals the REST ceiling). Green with unchanged frames: `:433, :440, :449,
  :534, :548, :972, :979, :986, :1005, :1022, :1064` (+inf at 20 Hz: one step either way); `:968`'s heading mechanical.

**3. The internal request queues at its deadline (a behaviour change).** `request_signal()` NP:165-176: the drop
branch NP:170-172 with its event line; `_SIGNAL_WAIT_MS`'s comment NP:33.
- Decision: change: wait while the slot is set and the deadline is ahead (the frame poll), then store the values, set
  the slot, `return True` (pre-audit answer); the comment: twice the REST ceiling of t (60 s), and past it the
  request queues anyway. Known limit for the knowledge line: a ramp past 120 s (no product caller) loses the request.
- Basis: approved text `led-request-internal-queue`: "waits for the running signal up to a deadline and then queues,
  as legacy queued it, but bounded"; owner note 2026-10-02 06:05: "Fine, and this for a reason: internal LED commands
  are guaranteed to be bounded by number and frequency, they won't flood the device."; DECREV 4.4 ("queue, not drop,
  at the deadline. W67 then goes."); plancheck B7.5; legacy `neopixel_signal.py:113-120`.
- Test: change first, red: `test_asy_neopixel_driver.py:619` (True, `_rgbt` the request's values, the slot set, no
  "dropped" line); `tests/test_ticks_rollover.py:685-692` (`(True, True, True)`, "queued at it");
  `tests/test_notification_neopixel_integration.py:208` (no entry; nothing plays without a signal task). Green:
  `:390, :414, :515, :644`, `test_ticks_rollover.py:695`.

**4. NT-5, W67 and the default-sink identity.** `_WRN_NOTIFY_SIGNAL_DROPPED` NS:58; `_trigger_signal()`'s `ok` and W67
NS:332, :336-337; `_sink_is_default` NS:211-212; the sink's `@staticmethod` NS:93-96; catalog W67
`buildgen/error_catalog.json:162`; `pyproject.toml:244-246` (ARG004).
- Decision: remove; `_trigger_signal()` back to `25caf528` NS:223-228 (plain await in its try, E14 on a raise); the
  sink an instance method again (`25caf528` NS:65-66), ruff ARG002; the W band `[67, 68]` stays (B4 kept W71/W73's).
- Basis: DECREV 4.4; S2-G1-17, S2-G4-9 (NT-5 C of the drop). **User-visible**: a catalog row the site's errcount
  table shows; no owner agreement recorded for W67 itself; per the lead's B6 ruling (2026-11-03: "A log code is no
  `/status` key or website element (the site lists only logged codes)") not an owner item.
- Test: go first: NS tests `tests/test_asy_notification_service.py:648, :677`, item 3's `:208`; green: `:641`,
  `test_notification_neopixel_integration.py:266`, `tests_scripts/test_buildgen_generate.py:1094, :1261`,
  `test_buildgen_validate.py:1331`; `tests_scripts/test_error_catalog.py` makes the row go with its last site.

**5. NP-4, the end state (settled here).** The signal task's `try`/`finally` NP:98, :115-119; the start-sets NP:77,
:94.
- Decision: restore `25caf528` NP:155-187 (the logger setup stays in `setup()`, U10): black and the slot's clear at
  the ramp's end inside the lock, the overlay restored after it; the start's black write stays (agent, 2026-11-03;
  **to the lead**). If the lead keeps NP-4: as landed, its tests stay, twin `:140`'s refresh wake goes with item 1.
- Basis: the scans differ: C.md NP-4 H "a mid-ramp cancel happens only at shutdown or a supervisor restart, and the
  worst consequence is one replayed flash"; G4 section 9 keeps it with no analysis; SCAN2 section 5's rare-but-real
  list does not name it. The only raise inside a ramp is a failed tuple allocation (A.U22.01: `write()` raises only
  for bad arguments, `extmod/machine_bitstream.c:39-60`, v1.29.0); its backstop is the supervisor's restart, which
  writes black and replays the one flash, then restores the overlay. `led-task-defined-state` is a routine item with
  no answer; owner 2026-11-03: "Generally target low complexity" (-4 lines, two states fewer).
- Test: go first: `test_asy_neopixel_driver.py:669, :693, :721, :740, :824`; twin
  `test_digital_twin_network_neopixel.py:104-160` with `:677`; `tests/neopixel.py`'s `raise_on_write` (`:12, :27,
  :48-49`) then has no reader and goes. Green: `:359, :367, :383, :591, :1083`.

**6. NP-1, NP-2's bounded frame poll, the REST refusal.** `led_signal()` NP:148-155 (refused while the slot is set,
its event line); the poll NP:169-173; the REST callback `buildgen/codegen.py:260-263` (B8's file).
- Decision: keep. Basis: OR102 "5. a"; review `led-request-internal-queue` (2026-10-02); G4 section 9; plancheck
  B7.K. Test: `test_asy_neopixel_driver.py:477, :491, :515, :573` green.

**7. NT-2, the `State` field and its sites.** NS:72-77 (`_STATE_*`), :133-137 (`NOTIFY`, `_FIELDS`), :201, the state
sites :279, :283, :289, :293, :298, `_store_notif_data(state=)` :326-327, the unreadable cycle's stored sample
:272; `/status` key `buildgen/codegen.py:305`; Status-page row "Evaluation State" `buildgen/definitions.py:691-695`
and the TS description's "(see Evaluation State)" :698; catalog `status.NotifyState`
`buildgen/error_catalog.json:209-215`; `mockdata/samples.json:21`.
- Decision: remove, **to the owner**. `NOTIFY` is `("Triggered", "TS")` again; the unreadable cycle stores nothing
  (`25caf528` NS:354-356), so TS stays at the last readable cycle. If kept: code 3's text loses "stale or not
  numeric" (items 8, 9) and `_check_one()` keeps its None arm.
- Basis: NT-2 H, D-G22 H, S2-G3-8, S2-G4X-2 ("no owner decision on the codes"); DECREV 3.1 ("a new API field with no
  owner decision and no other reader"). **User-visible** (a `/status` key, a Status-page row, its code table): no owner
  agreement to remove it is recorded; the approved `/status` list predates it and has no State (review
  `status-fields-added-and-left-out`, 2026-10-02 05:49: "Sounds good, ..."). Blast radius: about 25 NS lines, 1
  emitter line, 5 definitions lines, a 5-row table; only `/status` reads it.
- Test: go first: `tests/_sensortask_scenarios.py:3414-3448` (all 6 devices) with `_Rp2Gmtime`, `_ReadableSample`,
  `_NOTIFY_CYCLE_ROUNDS` and its `@tunable` (:3390-3411) and `_one_notification_cycle()` (:1304-1317); NS `:1523`;
  twin `test_digital_twin_sensortask_integration.py:1372` with `:121-123` (unit `:1126, :1143` keep the no-clock
  rule); `tests_scripts/test_buildgen_definitions.py:370-385`. Mechanical: its `:541`, `:699` (`_STATUS_ROW_TABLES`
  empties: the map goes), `tests_js/templates.test.js:591` (`["ResetReason"]`), `tests/test_readiness_gates.py:295`,
  the `_datastruct[1] is None` asserts (`test_notification_neopixel_integration.py:73`, `_scd30_integration.py:57`,
  `_scd30_sgp40_integration.py:64`, `_sgp40_integration.py:67`).

**8. NT-3, the 10,800 s sample age.** `_SAMPLE_MAX_AGE_S` with `@tunable notify.sample_max_age_s` NS:68-71; `ts`, `now`
and the check NS:226, :230-234.
- Decision: remove (the pre-audit read, `25caf528` NS:198-208).
- Basis: C.md NT-3 H, S2-G1-18, DECREV 3.1 ("`_store_scd()` stamps `utc_now()` every cycle, so they never fire; the
  owner on hardcoded delay checks"); owner LN362 (item 1); review `stale-as-fresh-every-driver` ok (2026-10-02).
- Test: go first: NS `:876, :1577, :1590`; twin `test_digital_twin_sensortask_integration.py:1311` with
  `_STALE_AFTER_S` `:124-125`, read first: it steps the wall clock past the bound and starts the monitor before the
  SCD30's next cycle, which re-stamps its cached sample even with ContMeas off (`asy_scd30_driver.py:465-482,
  :497-511`), so the device never meets it.

**9. NT-4, the non-numeric and NaN refusals.** NS:237-239 (E15 "Value not numeric"), NS:240-241; `value: object`
NS:221; `_check_one() -> bool | None` NS:217.
- Decision: typing-side form: `value: "int | float | None"`, `float(value)` (`25caf528` NS:198, :218);
  `_check_one()` answers a bool again (with item 7); E15 stays for a raising producer; `pyproject.toml`'s PLR0124 goes.
- Basis: PLAN R1 ("a narrowing branch that can never run becomes a typing-side form"); S2-G1-19 (NT-4 H); owner
  2026-10-27 on typing-only checks; a NaN compares False both ways, so it never triggers without the check.
- Test: go first: NS `:853`; green: `:761` (NaN never triggers), `:775`; mechanical (None -> False): `:788, :799,
  :828, :840`.

**10. NT-7, the per-episode flag.** `cfg_unreadable` NS:254, :269-271, :274.
- Decision: remove: each failing cycle calls `wrn_s(..., wrnno=_WRN_CFG_READ)`, one slot by the newest-entry rule,
  one console line per cycle (the post-U10 form, `8d44fd14^` NS:261-263).
- Basis: PLAN R1, OR35.b "Pure and simple."; OR35.a "Console logs actually should keep printing all."; S2-G4-8,
  DECREV 3.6, G4R07; B2 removed its flags the same way.
- Test: change first, red: `:1389` (counted by its console lines, since item 7 stops the unreadable cycle's store:
  one count and one line per cycle, one slot), `:1356`, `:1430` (the count per cycle, one slot); `:1273, :1466` green.

**11. The `setup()` bools.** `NeopixelDriver.setup() -> bool` NP:181-185; NS `setup()` NS:376-380 (B2, `8019a9ef`).
- Decision: NP answers nothing ("True = ready" goes); NS keeps B2's form.
- Basis: PLAN R1 (test-only product code), CARRY_LATER (B3-B7 line), OR36; the boot ignores it (codegen.py:311-313).
- Test: `test_asy_neopixel_driver.py:877` `is True` -> `is None` (mechanical).

**12. NP-R1, the constructor's rate and brightness (legacy).** `_NEOPIXEL_FREQ_HZ`, `_LED_OVERL_BRI` NP:29-32 and
NP:70, :73-74, in place of `neopixel_freq`/`led_overl_bri` (`25caf528` NP:44-52; legacy `neopixel_signal.py:11`).
- Decision: restore both keyword parameters with the constants as defaults (the post-U10 signature, `8d44fd14^`
  NP:66-74, tags kept), **to the lead**.
- Basis: removed in U17 (`c11ca0aa`, 2026-10-08, A.U17.27 "no device passed other values", agent) before the owner's
  library rule (2026-10-23: "Always regard the modules as libraries, not every feature must be immediately used, as
  long as it is a real feature"); C.md NP-R1 H. No TOML key appears (`buildgen/buildspec.py:18, :34`).
- Test: change first, red: `test_asy_neopixel_driver.py:123` (the keywords set the rate and brightness; defaults the
  constants); `scripts/_digital_twin_scenarios.py:133` reads `_NEOPIXEL_FREQ_HZ` unchanged.

**13. Kept as landed.** NT-1 `_in_window()` NS:140-144 and AutoOn's text NS:117 (OR69 "6. a"); NT-6 `TickSeconds`
pause NS:214, :306-317, :369-370 (OR104); construction-time signals and `_refusal()` NS:166-215 (U5, OR46.b); U22's
removal of the test-only `last_value`/`triggered` (OR36); catalog constants NS:51-57 (U3); the `@tunable` constants
NS:62-67 and NP:26-27, :34-35 (U8); whole-ms waits in loops NP:74, :110, :114, :173 and NS:297, :301-304 (U31; PLAN
R1); U10 names, member order and typing; `log=` (U5); the logger setup in `setup()` (A.U10.10); `reset_error_counter()
-> bool` NP:178-179 (U11, ResetErrors' per-field answer, B2's reset path); `set_override_led() -> bool` NS:372-374
(U10's setter contract, `tests_scripts/test_setter_contract.py:235-252`); `request_signal() -> bool`, always True
(pre-audit; library rule); the `FlashInterval` key (review `rest-key-scheme` ok). Test: existing.

**14. Not B7's.** The TS row's label "Last Cycle Time" and `"format": "epoch"` (`definitions.py:697`, `656fc82f`,
`f5c82557`): B8's website list. The LED and pause callbacks' emitters (`codegen.py:260-268`): B8.

**15. Every other hunk** against the pre-audit text: restore it, or name it to the lead; comment-only hunks stay where
they state the current code; NP's header (NP:1-3) says the request queues past its deadline.

Proof check (PLAN 0): items 1-5 and 7-10 have no observed or reproduced failure the device meets, no measured gain
and no owner approval; item 1's premise is refuted on silicon; item 3 follows the owner's approved text. The NP-4
tests inject a write raise rp2's `write()` cannot produce; item 8's twin test needs a wall-clock step ahead of the
producer's re-stamp. No item but 4 and 7 removes a `/status` key, a website element or a catalog row the site shows.
Legacy check (OR48.a), `legacy/firmware/python/IndividualDrivers/neopixel_signal.py`: `led_signal()` :67-73 changed
by NP-1 (OR102 "5. a"); `_led_int_signal_starter()` :113-120 bounded (item 3); the 0.1 s floor :128 kept (item 2);
`set_override_led()`/`get_override_led()` :56-65 kept; `auto_led_override()` :194-207 measured (OR104);
`airquality_auto_signal()` :152-192 overnight (OR69), its 600 s fallback kept; the constructor's rate and brightness
:11 lost (item 12, to the lead); `get_long_block_lock()` retired (SPEC F.3). Nothing else lost.

Shared files (B7 first; the lead re-bases B8): catalog W67 and `status.NotifyState`; `codegen.py:305`'s `"State"`;
`definitions.py:691-695` and :698's clause. Docs in the same commit: SPECIFICATION.md A.4 `:366-413` (the queue,
the clamp at the ramp, no cap, no refresh, no age bound, no State or drop warning, item 5's end state; the NotifyState
table `:406-413`), `:1032`, `:4651`, G.2 `:7627-7629`, I `:8910-8913` (no `_signal_values()`, no wrapper tasks),
Part N `:12021` (signal_wait_ms text), `:12022`, `:12026`, `:12224` (rows go), `:12019-12020` with item 12;
BACKLOG.md's build-environment list for the `pyproject.toml` edit. One knowledge line per removed item. Gate: the npm
three (shared website files). Proposed CARRY_LATER line, R2: the twin pixel's `power_dip()`, `displayed()` and
`raise_on_write` (`digital_twin/neopixel.py:23, :33, :50-67`, README `:162`) keep only their self-tests
(`test_digital_twin_network_neopixel.py:599, :693`) after items 1 and 5 (B4's precedent).

## For the owner
- Item 7: remove the notification `State` field (`/status` key, Status-page row "Evaluation State", its 5-code
  table, mock data); no recorded agreement to remove it.

## For the lead
- Item 5: NP-4 settled as the pre-audit end (agent); the alternative keeps it as landed.
- Item 12: a legacy constructor feature lost on an agent reason older than the library rule; restore proposed.
- Item 4: W67 treated under the lead's B6 ruling (a log code is no website element), not as an owner item.
- Item 3: the queued request replaces values still waiting in the slot (last wins), as an overwrite at the deadline.
