# Silent-failure scan, half B: our own code (classes 2, 3, 4, 6, 7)

First project-wide run of `audit/sweeps/silent_failure_scan.md` (OR147, with the OR148 operating-mode list), 2026-10-06.
The scan was read-only. Its scope: `src/`, `build/generated_src/` (regenerated with
`uv run scripts/_generate_sensortask_modules.py`, 6 devices), `digital_twin/` where it models the device, `js/`,
`html/`. Line numbers are HEAD's. "WO" means the work order (`audit/consolidation/M_*.md`) and "REG" means
`audit/REGISTER.md`. The motivating UART overrun case (M.SRC_NET.221 (6)) is already handled and is not reported again.

Devices (`devices/*.toml`): every device has fram, neopixel, notification, scd30 and sgp40. bmp3xx is on `wozi` and
`dev`. isl29125 and the two `uart_link` instances are on `dev` only. `wozi` is never flashed, so `wozi` findings show
up only in the mock and twin tiers.

## Findings not covered or partly covered by the work order

Order is severity first, then mode priority (boot, reset countdown, flash/config writes).

### B1. Foreign FRAM history after a firmware change is read as this module's own history (class 4, 3)
- **Site**: `src/asy_fram_manager.py:645-680` (bump-pointer `get_chunk()`), `src/print_log.py:226-279`. Chunk
  identity is only its address and its CRC8.
- **Mode**: after a firmware change (a reflash that adds, removes or reorders a chunk-owning module). Also boot.
- **Failure**: every logger chunk has the same size. All generated constructions use the default `history_length=10`
  (e.g. `build/generated_src/sensortask_wozi.py:167-174`), so each chunk is 2+10 data + 1 CRC + 2 status = 15 B per
  block and 30 B per chunk. If a new build inserts or removes one logger chunk ahead of others, every later logger
  chunk shifts by exactly one chunk span. Each one then lands on a neighbour's old chunk, a self-consistent dual copy
  with a valid CRC8. `PrintLogHistoryStore.setup()` → `_read()` succeeds (`print_log.py:257-271`) and loads the other
  module's ErrCount and history.
- **Today**: nobody sees it. `/status` `errcount` shows module X with module Y's old entries. Two places assume a
  foreign chunk "reads as invalid and restarts empty":
  - SPEC C.7's new pitfall text (M_SPEC.md:2075-2077)
  - A.U16.03's test (`audit/actions/U16.md:90-102`). That test rotates the image by 3 bytes, which makes every chunk
    invalid, so the aligned shift is never exercised.
  This is wrong evidence for CLAUDE.md's "read FRAM logs before clearing" rule.
- **Effect**: all six devices, on any firmware change that alters the chunk order (e.g. `dev` gaining or losing a
  driver ahead of the infra loggers). FRAM on SPI.
- **WO**: not covered. The owner rule "FRAM content need not survive a reflash" (owner, 2026-09-26, M_SPEC.md:372-373)
  allows losing the content. It does not cover mislabelling it.
- **Owning unit**: U16 (M.SRC_CORE.065/.088/.091, A.U16.03).
- **Conservative fix**:
  - Detect: put a per-chunk owner tag in the chunk header, covered by the CRC (e.g. a CRC8 or 16-bit hash of the
    logger name), or one layout signature chunk written by the manager at boot.
  - On a mismatch, treat the chunk as blank (the existing `False` branch of M.SRC_CORE.065).
  - Count and log once in FRAM's RAM logger.
  - Extend A.U16.03 with an aligned-shift case (image shifted by exactly one chunk span).

### B2. A dropped notification flash is reported as a triggered notification (class 4, 7)
- **Site**: `src/asy_notification_service.py:223-228` `_trigger_signal()` ignores the `bool` of `request_signal_cb`.
  `:370-375` sets `any_triggered = True` regardless.
- **Mode**: outputs (NeoPixel/notification) during a fault; LED busy; runtime.
- **Failure**: M.SRC_SENS.027 (U9) makes `NeopixelDriver.request_signal()` return `False` after `_SIGNAL_WAIT_MS`
  with only an `evt` console line ("Internal LED command dropped"). M.SRC_SENS.034 keeps `_trigger_signal()` "same
  shape", and M.SRC_SENS.027's Blast states "caller unchanged".
- **Today (after the WO)**: the flash is not shown. Nothing is counted or persisted. `NOTIFY.Triggered` reports
  `True` on `/measurements`. Nobody learns the warning never reached the LED.
- **Effect**: all six devices (neopixel and notification everywhere).
- **WO**: partly covered. The bounded wait exists; the result is ignored.
- **Owning unit**: U9 (LED pilot), re-checked in U22.
- **Fix**:
  - Test the bool. On `False`, `wrn_s` a new catalog code (one slot per run under the newest-entry rule) and count it.
  - `_DefaultSignalSink.request_signal()` (`:65-66`) returns `False` by design ("shouldn't blink"). It must stop
    reading as a failure, either by returning `True` ("accepted, discarded") or because the coordinator knows it holds
    the default sink. That choice is a deviation to log on the owner-review list.

### B3. A config PUT answered "Valid" whose flash write later fails is not visible to the client or in `ConfigFaults` (class 7)
- **Site**: `src/config_manager.py:299-388`. `write_config()` returns `True, {"k": "Valid"}` at staging (`:353-362`).
  `_flush_staged()` fails later (`:378-380`, errno 14) and still sets `_cache = staged` (`:384`).
- **Mode**: config persistence (flash write); full filesystem; reset countdown (a flush failing at the escalation
  flush, M.SRC_CORE.010).
- **Layer below** (v1.29.0 `lib/littlefs/lfs2.c`):
  - an errored file is never committed: `lfs2_file_close_()` skips sync when `LFS2_F_ERRED` is set (`:3250-3253`);
  - `O_TRUNC` only marks the file dirty in RAM (`:3146-3149`).
  So the old file stays intact. This is good: no corrupt file at the next boot. But the new value runs from RAM only
  and silently reverts at the next reboot.
- **Today**: the failure is persisted as `CFGMGR_<name>` errno 14 and counted. The PUT client already got "Valid".
  `/status` `ConfigFaults` (M.SRC_CORE.015/.043) lists only faults found at boot. A full filesystem fails every later
  write the same way.
- **Effect**: every schema-backed store on all six devices (littlefs on the RP2040 flash).
- **WO**: partly covered. M.SRC_CORE.044 (U11) keeps the persisted errno; M.SRC_CORE.015 (U20) covers boot faults only.
- **Fix**:
  - Set a per-store `unpersisted` flag on a failed flush and clear it on the next successful flush.
  - Report it beside `ConfigFaults` (or in it), with M.GEN.008's key text naming "running unpersisted".
  - No retry loop (C.7.3's one attempt holds).

### B4. `mempause` answers "Valid" when the auto-unpause timer could not be armed and the pause was aborted (class 7)
- **Site**:
  - `src/system_service.py:354-374`: the arm failure calls `storage_pause(value=False)` with `pr.err` only.
  - The generated `_system_cmd_callback` (`build/generated_src/sensortask_dev.py:105-106`, same in every device)
    returns `True` regardless.
- **Mode**: reset countdown / storage pause; supervision (alarm pool exhausted).
- **Today**: the REST client sees "Valid" and believes FRAM is paused for 300 s. FRAM is not paused. Nothing is
  persisted.
- **After the WO**: M.SRC_CORE.012 (U11) makes the method `-> bool` but writes "the arm failure … (abort the pause
  as today); `return True`". M.GEN.008 forwards that bool, so the end state still answers "Valid".
- **Effect**: all six devices (all declare FRAM).
- **WO**: partly covered.
- **Owning unit**: U11 (M.SRC_CORE.012).
- **Fix**: `return False` from the abort branch, so the API answers "Failed". Optionally `err_s(…, errno=_ERR_TIMER)`,
  which is allowed because the pause was aborted, so FRAM is writable.

### B5. A failed uptime tick-timer arm leaves `BootSignature` unresolved for the whole boot, console-only (class 4, 6, 7)
- **Site**:
  - `src/system_service.py:203-208`: `start_uptime_timer()` uses `pr.err` only.
  - `:376-395`: `status_counter()` waits on `uptime_event` forever.
- **Mode**: boot (timer starters); supervision (alarm pool full).
- **Today**: `Uptime` and `BootSignature` stay 0/`null` on `/status`. "Reboot detection by signature change" silently
  stops working. There is no entry and no retry.
- **After the WO**: M.SRC_CORE.013/.032 move `Uptime` onto ticks, which fixes `Uptime`. But `arm_tick_timer()`'s result
  is "unused" for SYSTEM, its failure is `pr.err` only, and `status_counter()` still waits on the flag. `BootSignature`
  stays `null` with nothing persisted. Contrast NTP (M.SRC_NET.054, retried from the task) and WiFi (M.SRC_NET.094
  `_tick_armed`).
- **Effect**: all six devices.
- **WO**: partly covered.
- **Owning unit**: U11 (M.SRC_CORE.013).
- **Fix**: use the bool. On `False`, persist `_ERR_TIMER` once and re-arm from `status_counter()` on a bounded
  `sleep`, as the NTP pattern does.

### B6. WiFi hotspot: a failed `status("stations")` query reads as "no client", which starts the hotspot shutdown timer (class 4)
- **Site**:
  - `src/asy_wifi_service.py:232-246`: `except Exception` → `pr.err`, `return []`.
  - `:575-581`: `[]` → `_hotspot_client_absent()`.
  - `:406-427`: arms `hotspot_timer` → `reconnect_wifi()`.
- **Mode**: WiFi hotspot / captive mode.
- **Today**: one failed query starts the countdown while a client may be connected and configuring the device. The
  next successful poll stops it again (`_hotspot_client_connected()`), so only a run of failures tears the AP down
  under a user. Nothing is counted (console only).
- **Effect**: all six devices (WiFi on every board).
- **WO**: not covered. M.SRC_NET.081 keeps "the `except Exception` observation arm unchanged"; M.SRC_NET.104 adds
  `report_if_fatal` only.
- **Owning unit**: U18.
- **Fix**:
  - Return `None` on a failure. `_manage_hotspot_stations()` treats `None` as "unknown": it leaves the timer state
    unchanged.
  - Persist one warning per failure run (newest-entry rule).

### B7. WiFi observation-tier failures read as valid "disconnected" data (class 4)
- **Site**: `src/asy_wifi_service.py:202-217` (`_wlan_status_or_none()` → `None`, `_wlan_isconnected_or_false()` →
  `False`), `:843-860` `time_counter()`.
- **Mode**: WiFi (mode transitions, a deinitialised WLAN); degraded running.
- **Today**: a failed query becomes `connected=False` in the 1 Hz snapshot. `WifiUptime` is reset to 0. `/status`
  shows Disconnected for a query failure. It is logged to the console only, by design ("degrade silently").
- **Effect**: all six devices.
- **WO**: partly covered (M.SRC_NET.101/.104 keep the arms; only `report_if_fatal` is added).
- **Owning unit**: U18.
- **Fix**:
  - On `None`, keep the previous snapshot instead of writing "disconnected".
  - Count failure runs (one persisted warning per run) so a stuck query becomes visible.

### B8. Config GET after a chip-read failure returns `null` fields that look like "not set" (class 4, 7)
- **Site**:
  - `src/base_classes.py:185-212`: the `_get_dict_cfg()` `except` keeps `dict.fromkeys(cfg)` → `None`.
  - `src/asy_bmp3xx_driver.py:173-178`: explicit `None` triple.
  - SCD30 chip forwarders `src/asy_scd30_driver.py:303-343`.
  - ISL29125 `_read_sensor_dict()` `:716-723`.
- **Mode**: runtime reconfiguration / a GET during a bus fault; degraded sensor.
- **Today**: the errno is persisted (3/4/22/28), but `GET /sensors` is a normal 200 whose fields are `null`. The page
  shows "—" (`js/field-format.js:16-18`), the same as a field never set.
- **Effect**:
  - SCD30 on all six devices.
  - BMP3XX on `wozi` and `dev` (bus `i2c0` on dev).
  - ISL29125 on `dev`.
- **WO**: partly covered. M.SRC_CORE.038 (U19) keeps the shape. The `{"error":"unavailable"}` marker exists only for
  `/status` sources (M.SRC_NET.123, rendered by M.WEB per A.U23.11).
- **Owning unit**: U19 (with U23 for the page).
- **Fix**: on a raised getter or callback, emit the module's GET entry as `{"error":"unavailable"}` (or add that marker
  beside the values) and reuse the page's existing unavailable rendering.

### B9. BMP3XX settings silently revert after a sensor self-reset (class 7, 6)
- **Site**:
  - `src/asy_bmp3xx_driver.py:198-` `_init_bmp()` applies the stored OSR/IIR once.
  - `_read()` `:429-446` writes only PWR_CTRL (forced mode) each cycle.
  - OSR (0x1C) and CONFIG (0x1F) are never re-checked.
- **Mode**: a peripheral that resets on its own (supply glitch); long uptime.
- **Today**: measurement continues at chip-default oversampling and filter. `GET /sensors` shows the chip's read-back
  (via `get_config_snapshot()`), so the operator sees defaults with no sign of a divergence from the stored config.
  Nothing is counted.
- **Not verified**: whether BMP3xx has a power-on-reset event flag. The datasheet PDFs in `datasheets/bmp3xx/` could
  not be rendered or extracted in this sandbox (encrypted PDF, no poppler), so the claim is left open.
- **Effect**: BMP3XX on `wozi` and `dev`.
- **WO**: not covered (ISL29125 has the equivalent: brownout plus shadow divergence, M.SRC_SENS.082; BMP3XX has
  nothing).
- **Owning unit**: U15.
- **Fix**: compare `get_config_snapshot()` with the stored config on a slow cadence (or per read, cheaply). On a
  mismatch, `wrn_s` once and re-apply, the same shape as ISL29125's `_check_divergence()`.
- **Related, SCD30**: `set_ambient_pressure()`'s value "whether … persists is undocumented" (M.SRC_SENS.057). A
  self-reset could drop the pressure compensation with no detector either.

### B10. SCD30: a "not ready" read re-stores the cached values with a fresh timestamp (class 4)
- **Site**: `src/asy_scd30_driver.py:595-605` (not ready → cache untouched); `:174-201` (`_read_scd()` takes a new
  `timestamp`; `_store_scd()` stores the old values).
- **Mode**: sensor modes (a spurious IRQ edge; the `_irq_loop` stuck-pin path); recovery and re-init; a PUT while a
  read is in progress.
- **Today**: stale CO2/T/RH are published with a current `TS`. This matches legacy behaviour (comment `:597-599`).
- **Effect**: SCD30 on all six devices.
- **WO**: partly covered. M.SRC_SENS.055/.057 (U15) make `read_measurement() -> bool` and return `new_data`, but
  `_store_scd()` is not gated on it.
- **Fix**: skip the store and keep the old `TS` when `new_data` is `False`. Count it (an `evt`, or a warning per run).
  It is not a failure for `_error_check`. This is a D.1 flag, because it differs from legacy field behaviour.

### B11. ISL29125 calibration: a run's outcome (timed out or converged) is console-only (class 7)
- **Site**: `src/asy_isl29125_driver.py:711-714` `_end_calibration()` (`pr.one` only), `:627-666`, `:1031-1039`.
- **Mode**: calibration run.
- **Today**: the client sees `GainMeas` (a candidate held for `_CAL_HOLD_MS`, then `None`) and, after the WO, the
  `CalLight` suitability code (M.SRC_SENS.072). "Still running", "timed out without a stable reading" and "finished"
  cannot be told apart over REST. `_push_calibrate` reports success unconditionally (`:828-836`, by design).
- **Effect**: `dev` only.
- **WO**: partly covered.
- **Owning unit**: U15.
- **Fix**: expose a calibration state (idle/running/converged/timed-out) next to `CalLight`, or persist a warning when
  the window closes without convergence.

### B12. FRAM allocator full or history allocation failed: the module silently runs RAM-only (class 2, 4)
- **Site**:
  - `src/asy_fram_manager.py:661-663, 703-705`: "FRAM out of memory!" `pr.err`, console only.
  - `src/print_log.py:236-242`: `_diag` only.
  - `src/print_log.py:139-144`: a `MemoryError` gives a 0-length history with no message at all.
  - SGP40 `ts_storage` `src/asy_sgp40_driver.py:180-187`.
- **Mode**: boot; FRAM allocator at its end.
- **Today**: for the shipped TOMLs the per-device scenario `fram_chunks_are_all_successfully_allocated_not_out_of_memory`
  (`tests/_sensortask_scenarios.py:419-475`) proves no chunk is `None`. That is design-time detection. At runtime, a
  `MemoryError` in the history deque is unreported, and `/status` shows a counter with an always-empty history.
- **WO**: partly covered. M.SRC_CORE.091 (U16) keeps "bookkeeping as HEAD"; M.SRC_CORE.063 (U11) does not touch
  `:140-144`.
- **Fix**:
  - `err_s` into FRAM's own RAM logger for an allocator refusal, so it is counted in `/status`.
  - `_diag` plus a flag for the 0-length history.

### B13. Twin FRAM state: a malformed or truncated state file silently becomes a blank chip, and the save is not atomic (class 4, 6)
- **Site**: `digital_twin/_fram_chip.py:57-94` (`return` on a missing marker, a short read leaves zeros, no message);
  `:96-106` (`open(…, "w")` truncates first, then streams).
- **Mode**: twin shutdown (a twin killed mid-`save_state()`); host crash.
- **Today**: the next launch starts from a factory-fresh chip without a word. Twin error-log evidence is gone, against
  CLAUDE.md's "check the twin FRAM before clearing".
- **WO**: partly covered. The fallback itself is owner-decided ("the factory-fresh chip", owner, 2026-08-13;
  M_TWIN.md:240-242). The gap is that it is silent and the write is non-atomic.
- **Owning unit**: U25.
- **Fix**:
  - Print one line naming why the load fell back.
  - Write to `state_path + ".tmp"` and `os.rename()` (atomic on the host).
  - Apply the same to `_scd30_chip.py`'s state file.

### B14. Saturated error counter: `ErrCount` sticks at 65535 and, with the newest-entry rule, repeats stop showing anywhere (class 2)
- **Site**: `src/print_log.py:161-164` (check-before-step at `_MAX_CNT`, `_diag` only); M.SRC_CORE.063 (U11) adds
  repeat-dedup.
- **Mode**: long uptime; degraded running with a persistent fault.
- **Today**: past 65,535 occurrences the counter freezes. A repeating code spends one slot, so new occurrences of that
  code are invisible in both the counter and the history until `ResetErrors`. The page shows "65535" like any value.
- **WO**: partly covered. The saturation is kept by K.28; it is not reported.
- **Owning unit**: U11, with U23 for display.
- **Fix**: the page renders the cap as "≥ 65535" (the cap in the definitions), or `get_log()` adds a `Saturated` flag.

### B15. UDP datagram truncation is documented, not detected (class 2)
- **Site**: `src/asy_udp_socket.py:168-180` `recvfrom(buf)`.
  - Callers: DNS client `_DNS_RECV_BUF = 512` (`src/asy_dns_client.py:19`), NTP 1024, captive DNS 4096 (512 after
    M.SRC_NET.007).
  - Layer below: modlwip copies at most `buf` bytes and drops the rest (cited by M.SRC_NET.030 as
    `extmod/modlwip.c:719-721`, v1.29.0).
- **Mode**: WiFi/DNS (a large reply, e.g. many A records).
- **Today**: a cut reply parses as "no usable answer". It looks like a server failure.
- **WO**: partly covered. M.SRC_NET.030 (U18/U28) states it in a comment only.
- **Fix**: treat `len(data) == buf` as truncated in the DNS client (one counted `evt`/warning, then try the next
  server). Low.

### B16. UART: the initiator cannot tell a responder's declined command from a lost frame (class 3, 7)
- **Site**: `src/asy_uart_comm.py:1016-1031, 1042-1052` (`_reject_wrn` persists W56 on the responder side); SPEC J.4
  "Rejection is signalled by withholding an ACK" (`SPECIFICATION.md:5513-5515`).
- **Mode**: UART link (idle, peer reset mid-frame).
- **Today**: both sides count something (the responder W56; the initiator its timeout code), but the initiator only
  learns it by timeout.
- **WO**: not covered, and blocked by owner decisions. "The UART wire format is not touched" (owner, 2026-09-25), and
  reconciling the C port is post-audit only.
- **Effect**: `dev` only (two instances over the crossover jumper).
- **Proposal**: no code change now. Record it for the C reconciliation list as a receiver-side candidate (e.g. a
  distinct answer frame), classified Class A.

### B17. Notification silently inactive while its producer or NTP is down (class 4, 7)
- **Site**:
  - `src/asy_notification_service.py:206-208`: value `None` → `False`, no entry (deliberate, M.SRC_SENS.035).
  - `:364-365`: `cettime()` `None` before NTP sync → no check at all.
- **Mode**: degraded running (sensor or NTP missing); boot before the first sync.
- **Today**: `Triggered=False` is indistinguishable from "no threshold exceeded". The producer's own errcount and
  NTP `Synced` show the cause separately.
- **WO**: partly covered (by design).
- **Fix** (low): add a `NOTIFY.Active` (or `Reason`) field, so the output says "not evaluated".
- **Related**: `override_secs` (`PauseTime`) is RAM-only and resets to 0 across a reboot
  (`src/asy_notification_service.py:158`). Mode: outputs across a reboot. It is visible on `/status` and low; record
  whether that is intended.

### B18. Host generator writes are not atomic (class 6, low)
- **Site**: `scripts/_generate_sensortask_modules.py:45,51`, `buildgen/generate.py:56-57`,
  `buildgen/definitions.py:533`, `scripts/build_firmware.py:56,98-99,149` (`Path.write_text`).
- **Mode**: host tooling killed mid-way.
- **Today**: a truncated `.py`/`.json` mostly fails loudly (SyntaxError or JSON parse error) and every run regenerates
  it. A truncation at a line boundary could import cleanly with missing definitions.
- **WO**: not checked in depth (outside this half's main scope).
- **Owning unit**: U20/U21.
- **Fix**: write to a temp file, then `os.replace()`.

## Checked and covered by the work order (named)

| Site / mechanism | Class / mode | Covered by |
|---|---|---|
| Pre-setup log entries overwritten when FRAM history loads (`print_log.py:267`) | 4 / boot | M.SRC_CORE.065 (merge), .063 (`_pre_setup_slots`) |
| An unreadable FRAM chunk overwritten at setup (`print_log.py:276`) | 6 / boot | M.SRC_CORE.065, .088 (tri-state) |
| Torn write between blocks (`asy_fram_manager.py:173-177`) | 3 / power loss mid FRAM chunk | detected (errno 73); M.SRC_CORE.088 keeps the hard failure, owner 2026-07-18 |
| FRAM chip lost: writes "succeed" or read as blank | 3, 6 / FRAM stops answering | M.SRC_CORE.103 (WEL anomaly → ID probe → `lost`), .092 (watch task), .082 silence while lost |
| Unreadable config file overwritten with defaults (`config_manager.py:423-427`) | 4 / boot, first boot | M.SRC_CORE.043 (ENOENT split, `writable`, `faulted`), `ConfigFaults` M.SRC_CORE.015 |
| Older-firmware config file (unknown or re-typed keys) | 4 / after a firmware change | handled at HEAD (W4/W5) and M.SRC_CORE.043 (repair, not flagged, lead ruling 2026-10-05) |
| Config write cut by a reset or power loss | 6 / flash writes | safe: littlefs never commits an errored or unsynced file (`lfs2.c:3146-3149, 3250-3253`); a PUT accepted during a commanded reset is refused by the closed stores (M.SRC_CORE.011/.038/.041) |
| PUTs and flushes in flight during the reset countdown | 7 / reset countdown | M.SRC_CORE.010 (`_reset_when_due` flush, close at reset), .011 (stores closed at acceptance) |
| Reset-timer arm failure → watchdog starve with no persisted cause | 7 / reset countdown | M.SRC_CORE.010 (reset record code 6), .006 |
| Errors logged while FRAM is paused in the countdown are lost at reset | 2 / reset countdown | by design, M.SRC_CORE.010 ("print-only: FRAM is paused"); the reset record is the persisted trace |
| `ResetErrors` answered OK when a store write fails or FRAM is paused | 7 / ResetErrors | M.SRC_NET.123 (per-key result, `gather`), M.SRC_CORE.063/.091 `reset() -> bool`; web M.WEB (A.U11.31) |
| `PUT /sensors` unknown sensor or keys silently dropped (`asy_webserver_service.py:427-430`) | 4, 7 / REST | M.SRC_NET.120 ("Invalid") |
| Settings group hook raising drops fields | 7 / REST | M.SRC_CORE.072, M.SRC_NET.120 |
| Reject-when-full and peer resets uncounted (`:697-702`) | 2, 7 / REST hammering | M.SRC_NET.127/.129 (`HTTPDropped`, 24 h window) |
| Status source failure | 7 / REST | logged errno 6; `{"error":"unavailable"}` rendered (M.SRC_NET.123, M.WEB A.U23.11) |
| Missing errcount entry rendered as `counter: 0` (`js/templates.js:245-246`) | 4 / web | M.WEB (A.U23.11 "no data") |
| External LED busy answered without a retry hint | 7 / REST | M.SRC_NET.122 (busy `descr`) |
| Timer-sequencer starter failure, console-only (`system_service.py:149-176`) | 4 / boot | M.SRC_CORE.014 (`err_s`, task context) |
| Supervisor: a dead task that returned cleanly gives no entry; no task name | 7 / supervision | M.SRC_CORE.016 (`_ERR_TASK_RETURNED`, names, `LastTaskEnd`) |
| `_TASK_FAIL_MAX` reboot trace | 7 / supervision, boot loop | errno 4 persisted before `reboot_system()` at HEAD; M.SRC_CORE.016/.006 reset reason |
| Absent or defective declared chip → restart budget → reboot loop | 6 / boot loop, sensor absent | owner-intended escalation (OR18.a, SUPP_recovery.md:92); ladder rungs first (M.SRC_CORE.037 `_init_failed()`); repeats spend one slot (M.SRC_CORE.063) |
| NTP refresh or sync-age timers fail to arm → Synced/age frozen | 4, 6 / boot | M.SRC_NET.054 (retry from task), .052/.058 (tick age) |
| Pre-sync timestamps look plausible (RTC epoch) | 4 / time before first sync | M.SRC_CORE.032 `utc_now()` → `None`; M.SRC_SENS.089/.090 |
| NTP short reply / zero timestamp accepted | 4 / time | REG parked deltas (U18) |
| UDP failed send waited out as "no reply" | 4 / DNS/NTP | M.SRC_NET.029 |
| Captive DNS receive and bind failures conflated | 7 / hotspot | M.SRC_NET.007 |
| Bus drivers' silent `return` on pack or length failures (`asy_i2c_driver.py:155-160`, `asy_spi_driver.py:93-97`) | 4 / runtime | M.SRC_SENS (SPI `write_readinto() -> bool`; I2C `set_register_struct() -> bool`, `get_register_*`) |
| VOC index 0 during the algorithm blackout looks like a value | 4 / warm-up | `VOCState` field (M_SRC_SENS.md:1504) |
| ISL29125 brownout or register divergence | 7 / peripheral self-reset | detected and re-applied at HEAD; M.SRC_SENS.082 |
| SCD30 non-finite or out-of-range words | 4 / sensor | finiteness at HEAD; range gate M.SRC_SENS.057 |
| SGP40 compensation missing → VOC stays at the old value with the old TS | 4 / degraded running | old TS shown; no restamp (store skipped) — no gap |
| UART receive overrun / ring lap | 2 / UART | M.SRC_NET.221/.222 (motivating case) |
| UART boot drain not counted | 7 / boot, peer outlived reset | deliberate, `asy_uart_comm.py:1094-1104`; printed |
| Twin Timer alarm-pool ENOMEM not modelled | fidelity | M.TWIN (alarm pool, `M_TWIN.md:1025-1061`) |
| JS poll failure | 7 / page open during reboot | banner shown and self-heals (`js/render.js:350-374`); PUT failure marks fields failed (`:256-272`) |
| JS empty `/status` PUT result shown as success | 7 | M.WEB (default-Valid removal with M.SRC_NET.123) |

## Coverage per module (classes 2, 3, 4, 6, 7)

- `src/print_log.py`: B1, B12, B14. Rest covered (M.SRC_CORE.063-.065).
- `src/base_classes.py`: B8. `Lockable.__aexit__` `except RuntimeError: pass` (`:47-50`) is kept deliberately by
  M.SRC_CORE.033. The recovery-write result is covered by M.SRC_CORE.038.
- `src/config_manager.py`: B3. Rest covered (M.SRC_CORE.043/.044/.048).
- `src/system_service.py`: B4, B5. Rest covered (M.SRC_CORE.006/.010-.016).
- `src/asy_fram_manager.py`: B1, B12. Rest covered (M.SRC_CORE.081-.092).
- `src/asy_fram_driver.py`: checked, nothing new (M.SRC_CORE.102-.107).
- `src/api_response.py`: checked, covered (M.SRC_CORE.072/.073).
- `src/crc_checks.py`, `src/framing_codecs.py`, `src/math_helpers.py`, `src/voc_algorithm.py`: pure functions with
  `None` sentinels tested by their callers. Checked, nothing found in these classes (domain refusals: M.SRC_CORE.126-.131).
- `src/asy_i2c_driver.py`, `src/asy_spi_driver.py`: checked, covered (bool contracts, M.SRC_SENS.003/.010-.012).
- `src/asy_uart_driver.py`, `src/asy_uart_comm.py`, `src/asy_uart_link_driver.py`: B16 (blocked by the wire freeze).
  Overrun covered. Counters capped by M.SRC_NET.214/.216.
- `src/asy_udp_socket.py`, `src/asy_dns_client.py`: B15. Rest covered (M.SRC_NET.020-.031).
- `src/captive_dns.py`: checked, covered (M.SRC_NET.007).
- `src/asy_ntp_client.py`: checked, covered (M.SRC_NET.042-.060, plus two REG deltas).
- `src/asy_wifi_service.py`: B6, B7.
- `src/asy_webserver_service.py`: checked, covered (M.SRC_NET.110-.132).
- `src/asy_neopixel_driver.py`: B2 (the caller side). Driver covered (M.SRC_SENS.022-.028).
- `src/asy_notification_service.py`: B2, B17.
- `src/asy_scd30_driver.py`: B10, plus the B9 note (ambient pressure).
- `src/asy_sgp40_driver.py`: checked, nothing new (backup write and read failures persisted; `_push_reset_voc` always
  True by design, C.5.2).
- `src/asy_bmp3xx_driver.py`: B8, B9.
- `src/asy_isl29125_driver.py`: B8, B11.
- `build/generated_src/sensortask_*.py` (6 devices): B4 (the `mempause` callback). `_flush_pending_configs()` is
  awaited before a commanded reboot; status builders are guarded by the webserver. Nothing else found.
- `digital_twin/`: B13. Timer/WDT/UART link fakes model the drops as counted (`machine.py:533-547`); the ENOMEM alarm
  pool is in the WO.
- `js/` + `html/`: covered by M.WEB (unavailable sources, missing errcount, ResetErrors result, busy hint). Two
  browsers editing the same value: last write wins, the other page refreshes its caption on its next poll. Nothing
  silent found. `html/index.html`: static shell, nothing.

## Modes checked

Every OR148 mode was walked for the modules above. The modes with findings:

| Mode | Findings |
|---|---|
| after a firmware change | B1 |
| boot | B5, B12 |
| reset countdown | B4; B3 for the escalation flush |
| flash/config writes and full filesystem | B3 |
| hotspot | B6 |
| WiFi transitions | B7 |
| runtime reconfiguration / GET during a fault | B8 |
| peripheral self-reset | B9 |
| sensor modes / IRQ | B10 |
| calibration | B11 |
| long uptime | B14 |
| DNS | B15 |
| UART | B16 |
| degraded running | B7, B17 |
| outputs across a reboot or fault | B2, B17 |
| twin shutdown | B13 |
| host tooling killed | B18 |

Modes checked with nothing new found:

- **first boot**: the config file is written once (OR136); blank FRAM reads as uninitialised.
- **boot loop**: covered rows above.
- **power loss mid flash**: littlefs.
- **API before every driver's `setup()`**: the webserver starts after the boot batch. A driver's own `_init_*` runs in
  its task, and a PUT racing it fails visibly (errno plus "Failed").
- **two browsers**.
