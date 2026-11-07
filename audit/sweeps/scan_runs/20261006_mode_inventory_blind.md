# C — Operating-mode / special-situation inventory (blind derivation)

Derived from primary sources only: `src/*.py`, `build/generated_src/sensortask_*.py` (regenerated
2026-10-06), `devices/*.toml`, `js/`, `digital_twin/`, `buildgen/`, `scripts/`, `toolchain/`, the
pinned MicroPython v1.29.0 tree at `/root/pico-toolchain/micropython`, and the datasheet text
extracts. `audit/`, `PROJECT_AUDIT_PLAN.md` and `arduino/` were not read. SPECIFICATION.md/CLAUDE.md
were consulted only for platform facts and to cite owner-accepted behaviour.

Format: one line per mode: **mode**, source citation, why it is risky (what can be lost or go
unnoticed). "(RU)" = reachability unverified. `gen/<dev>` = `build/generated_src/sensortask_<dev>.py`.

---

## 1. Code state (src/ + generated modules)

### 1.1 Boot / supervisor (`system_service.py`, generated `main()`/`build_system()`)
- C1. **WDT armed at the top of `build_system()` before any setup** — gen/dev:172 — every later construction/setup step races an 8 s budget; any escaping exception lands in the REPL with an armed WDT (reset loop).
- C2. **Grouped one-time `setup()` batch with per-unit `feed_watchdog()` + `gc.collect()`** — gen/dev:230-260 — a single unit exceeding ~8 s (e.g. first-boot config writes + slow flash) is a watchdog reset with no log.
- C3. **Gap between last setup feed and first supervisor feed** (`start_timers()` ~1 s, `ntp_force_sync()`, `pr.setup()`, staggered task starts + per-task `gc.collect()`) — gen/dev:301-308, system_service.py:217-227 — unfed window at boot; only bounded by luck/timing, not by code.
- C4. **Timer sequencer pending (`timers_running` not yet set)** — system_service.py:149-176,210-215 — `start_timers()` awaits a flag set only by the last ONE_SHOT sequencer callback; a dropped callback hangs boot before the supervisor ever feeds the WDT (reset loop). (RU)
- C5. **Sequencer arm failure → "stopping early"** — system_service.py:170-175 — remaining timer starters (sensor triggers, uptime, NTP) silently never start; tasks wait on flags forever without errors (only a non-persisted `pr.err`).
- C6. **Uptime timer arm failure** — system_service.py:203-208 — uptime frozen at 0, boot signature never resolves; non-persisted log only.
- C7. **`task_errors` accumulator 0..>300 (+100 per dead task, −1 per healthy 2 s cycle)** — system_service.py:228-256 — four task deaths within ~200 s ⇒ reboot; a permanently failing sensor init yields a reboot every ~8–10 s (boot loop). 
- C8. **Supervisor decided reboot (`task_errors > _TASK_FAIL_MAX`)** — system_service.py:249-254 — loop returns (stops feeding), no `flush_pending()` of staged config, FRAM paused only via `_reboot()`.
- C9. **`_force_watchdog_starve` (one-way)** — system_service.py:97,118-130 — set when the reset timer cannot be armed; device keeps running sensors/HTTP for up to 8 s with storage paused, then WDT reset.
- C10. **Reset timer armed, 4 s pre-reset window (`_RESET_DELAY`)** — system_service.py:40,126 — API still serves and accepts PUTs; new staged config flushes may be cut by the reset.
- C11. **Reset timer is ONE_SHOT soft callback** — system_service.py:126 — a dropped scheduler entry means the commanded reboot never happens and storage stays paused forever (supervisor keeps feeding the WDT).
- C12. **Storage pause (`storage_pause(True)`), timed (`pause_permanent_storage`, ≤3600 s) or open-ended (`_reboot`)** — system_service.py:118-124,354-374 — all FRAM error-log writes and SGP40 backups refused; failures are only RAM-logged.
- C13. **Auto-unpause timer ONE_SHOT** — system_service.py:366-370 — dropped callback ⇒ FRAM paused permanently until reboot, silently.
- C14. **Boot signature unresolved (None) → NTP UTC → or random after 120 s** — system_service.py:92-93,376-395 — consumers cannot tell "not yet resolved" from "uptime timer dead"; a later NTP sync never replaces a random signature.
- C15. **`start_time_set` latch** — system_service.py:91,383-395 — once set, boot signature never revisited even if NTP time later jumps.
- C16. **Level-setter registry empty until `set_level_setters()`** — system_service.py:109,325-339 — DebugLevel changes before registration reach no logger.
- C17. **DebugLevel 0–5 runtime state (`_current_debug_level`)** — system_service.py:59,105,288-297 — level ≥3 multiplies synchronous `print()` calls (see D-USB modes); level 0 hides every non-persisted `pr.err()` observation.
- C18. **Task-starter failure path (starter raises → slot None, retried each 2 s cycle)** — system_service.py:178-183,232-238 — counts as a dead task every cycle ⇒ fast reboot loop.
- C19. **Task ended "cancelled" vs "exception" vs clean return** — system_service.py:185-197 — clean returns (e.g. read_loop `return False`) are logged only as generic wrnno n+1; cause lives only in the module's own log.
- C20. **Generated `_system_cmd_callback` dispatch (`reboot`/`bootloader` flush pending configs; `mempause` = fixed 300 s)** — gen/dev:97-109 — reboot/bootloader wait on `flush_pending()` with no timeout.

### 1.2 Logging / error history (`print_log.py`)
- C21. **Logger uninitialized (before `pr.setup()`)** — print_log.py:146,173-176 — errors are counted in RAM but not persisted; on `setup()` the FRAM `_read()` overwrites `err_count` and pushes the pre-setup ring entries out (lost).
- C22. **`PrintLogHistoryStore` with no FRAM chunk (allocation failed / FRAM absent)** — print_log.py:236-242,244-246 — `_write()` always False; history RAM-only, `_diag` only prints if level>0.
- C23. **FRAM setup of logger failed (`_read()` and `_write()` both fail)** — print_log.py:273-279 — `initialized` stays False forever: every later error is RAM-only, no persisted trace of that fact.
- C24. **`reset()` whose FRAM write fails** — print_log.py:213-223 — RAM ring cleared, FRAM keeps old history which reappears after reboot (ResetErrors appears not to stick).
- C25. **`err_count` saturated at 0xFFFF** — print_log.py:65,161-164 — counter stops moving; new errors still enter ring but count is frozen.
- C26. **Ring of 10 slots per logger; `repeat=True` entries counted but take no slot** — print_log.py:141,167-172 — an episode of repeated faults leaves only its first code; interleaved distinct codes evict older evidence.
- C27. **Invalid errno (> range) dropped from ring** — print_log.py:169-172 — counted but code never visible.
- C28. **Log level OFF (0) on all loggers** — print_log.py:53,154-156 — every `pr.err()`-only (observation-tier) failure is completely silent.

### 1.3 Config storage (`config_manager.py`, `base_classes.py`)
- C29. **ConfigManager `valid=False` (setup not run, file is a directory, empty/invalid defaults)** — config_manager.py:226,241-243,305-307,420-439 — every get returns None, every write "Failed"; downstream modules interpret as "missing config" (WiFi deactivates, SGP40/BMP/ISL init fail ⇒ restart loop).
- C30. **Config file missing (first boot / after mkfs)** — config_manager.py:423-426,459-460 — defaults written; warn wrnno 3 indistinguishable from a deleted user config.
- C31. **Config file malformed JSON / non-dict** — config_manager.py:411-419 — user values silently replaced by defaults and rewritten (warning only).
- C32. **Per-key type/range error on load** — config_manager.py:447-451 — that key reverts to default; rewrite.
- C33. **Unknown keys in file (schema shrank after upgrade)** — config_manager.py:461-463 — keys deleted on rewrite.
- C34. **Load-time coercion rewrite (int↔float)** — config_manager.py:453-457 — a flash write at every boot where needed.
- C35. **Setup-time default write fails ("running unpersisted")** — config_manager.py:475-485 — config valid in RAM only; reverts after reboot; one attempt only.
- C36. **Staged-but-unflushed config (`_staged`, `_pending_flush`)** — config_manager.py:231-238,353-354 — GET shows the new value before it is on flash; power loss in this window loses it silently.
- C37. **Superseded staged snapshot (rapid successive PUTs)** — config_manager.py:369-373 — older flush task becomes a no-op; correctness depends on identity check.
- C38. **Deferred flush failed (errno 14), `_cache` adopted anyway** — config_manager.py:374-388 — device runs a value that will vanish at next boot.
- C39. **Write with no change ("Unchanged") ⇒ no staging, no post hooks** — config_manager.py:342-350, api_response.py:73-77 — resubmitting identical WiFi credentials does not trigger a reconnect.
- C40. **Command-only (special-alone) field** — config_manager.py:190-208,334-337 — "Valid" though nothing stored; push failure has no persisted rollback.
- C41. **Push-callback failure → `_recover_failed_push` chain (live getter → pre-write snapshot → schema default)** — base_classes.py:338-397 — persisted value may be rewritten to a default the user never chose.
- C42. **`_get_mgr_cfg` raised during pre-write snapshot** — base_classes.py:309-315 — recovery falls back to schema default.
- C43. **`_err_cnt_internal` consecutive-failure streak (0..max_module_error+1)** — base_classes.py:218-230 — streak > max ⇒ task returns ⇒ supervisor +100; decrement only on success (`pr.err`, not persisted).
- C44. **`_error_check(condition=False)` path (SGP40 uncompensated, WiFi no hw failure)** — base_classes.py:221 — None data does not count as an error at all.
- C45. **Last-good measurement retained in `_datastruct` when reads fail** — scd30:189-191, bmp3xx:227-229, sgp40:449-451 — /measurements keeps serving an old value (with its old TS) indefinitely after a sensor dies.
- C46. **`Lockable.__aexit__` swallows RuntimeError on double release** — base_classes.py:47-51 — a lock-protocol bug becomes invisible.

### 1.4 FRAM (`asy_fram_driver.py`, `asy_fram_manager.py`)
- C47. **FRAM driver `initialized=False` (setup raised: not found / ID mismatch / unknown size)** — asy_fram_driver.py:381-398, asy_fram_manager.py:731-738 — every chunk op refused; all FRAM-backed logs become RAM-only.
- C48. **`verify_present()` failure reverts `initialized=False`** — asy_fram_driver.py:400-432 — FRAM silently disabled for rest of boot (if anything calls it).
- C49. **Chip write-protected (BP0|BP1|WPEN nonvolatile, re-synced at setup)** — asy_fram_driver.py:64-66,217-231,385-388 — writes AND reads (busy marker write) refused; logs RAM-only; wrnno 84 lands in the in-memory FRAM logger.
- C50. **WEL not set / WEL stuck** — asy_fram_driver.py:200-216,345-350 — write aborted or warned; warnings go to the non-persisted FRAM-manager logger.
- C51. **Chunk block status BUSY left set (reset mid-read or mid-write)** — asy_fram_manager.py:29-31,223-268,293-358 — block unreadable until rewritten; both blocks busy ⇒ whole chunk lost (owner-accepted for logs).
- C52. **Both blocks valid but different (torn between blocks)** — asy_fram_manager.py:173-177 — hard read failure; logger then overwrites with an empty ring (history lost).
- C53. **Block 0 invalid, block 1 valid → repair write** — asy_fram_manager.py:136-157 — a repair write happening during a read; if it fails data is refused.
- C54. **Uninitialized chunk (status 0x00)** — asy_fram_manager.py:235-239,306-308 — blank-chip path; a factory-fresh chip filled with non-0x00 bytes reads as "error" not "blank" (RU).
- C55. **FRAM pause (`_pause`) gate** — asy_fram_manager.py:96-100,128-132,391-393,726-729 — first refusal per episode persisted (but to the RAM-only FRAM logger), repeats silent.
- C56. **Bump allocator exhausted ("FRAM out of memory")** — asy_fram_manager.py:661-663,703-705 — later chunk owners silently get None (RAM-only logging) — `pr.err` only.
- C57. **Write-verify counter (`verify_counter` vs `_verify`)** — asy_fram_manager.py:114-124 — verification only every Nth write; a bad write between verifies is undetected until a read.
- C58. **CRC8 on error-log chunks (1-in-256 false accept)** — print_log.py:238 — after a layout shift (reflash/instance reorder) or bit rot, garbage can restore as a plausible history.
- C59. **Timestamped chunk written without NTP (TS=0 "uninit")** — asy_fram_manager.py:544-566 — backup has no age; later restored regardless of BackupMaxAge.
- C60. **Timestamp computation overflow (≥2038)** — asy_fram_manager.py:546-552,610-614 — backups lose timestamps / ages permanently.
- C61. **FRAM chunk errors logged to `AsyFramManager.pr` which is a plain in-memory `PrintLogHistory`** — asy_fram_manager.py:622,672,716 — all FRAM-layer faults vanish on reboot (FRAM is not in the persisted errcount set).

### 1.5 WiFi (`asy_wifi_service.py`)
- C62. **`_PHASE_STA_SEEKING`** — asy_wifi_service.py:122 — failures count toward `conn_fail_to_hotspot`.
- C63. **`_PHASE_STA_ESTABLISHED` disconnected → retry every 60 s forever, holding `wifi_mode_lock` during the 60 s sleep** — asy_wifi_service.py:123,469-477,583-590 — NTP sync, wifi uptime counter and lock-checking getters stall/return None for 60 s each cycle; never falls back to hotspot.
- C64. **`_PHASE_HOTSPOT` (AP mode, captive DNS, hotspot timer)** — asy_wifi_service.py:125,353-431,568-581 — NTP impossible, notifications off, RSSI query raises.
- C65. **Hotspot with ≥1 client: timer stopped, AP kept indefinitely** — asy_wifi_service.py:396-404 — a phone that auto-joins keeps the device off the home network forever.
- C66. **Hotspot with no client → PERIODIC hotspot timer (`hotspot_time_min`) → reconnect** — asy_wifi_service.py:406-430 — leaves AP; second failure streak then deactivates WLAN (C67).
- C67. **`_PHASE_DEACTIVATED` (terminal; survives task restarts)** — asy_wifi_service.py:126,304-307,491-501,823-824 — no network at all until power cycle; loop ignores `reconn_wifi`; sensors keep running unreachable.
- C68. **`hotspot_started_once` latch (reset only on task (re)start, not on leaving AP)** — asy_wifi_service.py:185,303,366,485-489 — a second failure streak after any hotspot episode is terminal.
- C69. **Empty SSID ("not configured") ⇒ immediate hotspot** — asy_wifi_service.py:441-443 — factory/after-mkfs state; combined with C66/C68 the unconfigured device deactivates after one unattended hotspot window.
- C70. **Missing LED config (cfgmgr invalid) at task start ⇒ DEACTIVATED** — asy_wifi_service.py:318-325 — any config-layer failure permanently kills networking.
- C71. **`reconn_wifi` flag (set by PUT post-hook / hotspot timeout / task-start state)** — asy_wifi_service.py:172,311,538-556,806-812 — 5 s + 3 s blind sleeps; mode switches deinit/recreate the WLAN object.
- C72. **`hw_op_failed` streak → task return (errno 17)** — asy_wifi_service.py:186,833-840 — supervisor +100; repeated WLAN driver exceptions feed the reboot accumulator.
- C73. **WLAN mode switch in progress (`_switch_wlan_mode`: disconnect, active(False), 2 s, deinit, 1 s, new WLAN, 1 s)** — asy_wifi_service.py:278-293 — wifi uptime reset; getters see a deinitialised object; holds lock ~4 s.
- C74. **STA disconnect wait (≤10 s, bounded)** — asy_wifi_service.py:336-351 — timeout logged errno 18 but proceeds.
- C75. **Connect poll results: wrong password / no AP / connect fail / undefined status (episode-suppressed warnings)** — asy_wifi_service.py:592-630 — only first occurrence per episode takes a slot.
- C76. **Stored radio value over byte bound ⇒ silently uses default** — asy_wifi_service.py:704-716 — device may connect with default hostname/country without user noticing.
- C77. **`led` None vs `led_pin` vs `ext_led` (LedWifiOn)** — asy_wifi_service.py:792-804 — status-LED overlay state shared with the notification pixel.
- C78. **`_flash_led_off` task (hotspot, no client)** — asy_wifi_service.py:527-536 — competes with notification signals on the same pixel.
- C79. **Getters return None while `wifi_mode_lock` is held** — asy_wifi_service.py:738-787 — /status networking fields go null during NTP sync / 60 s retry / mode switches.
- C80. **`time_counter` coalesced ticks (ThreadSafeFlag) when lock held** — asy_wifi_service.py:843-860 — WifiUptime undercounts.
- C81. **DNS server task (captive) created/cancelled with hotspot** — asy_wifi_service.py:389-394,299-301,329-331 — orphaned or duplicated only if `.done()` logic misjudges; port-53 bind failure loops with backoff forever.

### 1.6 NTP / time (`asy_ntp_client.py`)
- C82. **Unsynced (`Synced=False`), exponential backoff 10 s→600 s** — asy_ntp_client.py:106-107,424-444,464-466 — timestamps stay on the 2021 power-on epoch; notifications and timestamped backups disabled.
- C83. **Synced → stale after 3×`NTP_Interv_H` without success (≤72 h)** — asy_ntp_client.py:37,455-459 — flips to unsynced silently: notifications stop, `cettime()` None.
- C84. **Synced-but-failing retries (3 × 15 s ONE_SHOT), then "Maximum retries"** — asy_ntp_client.py:272-293 — ONE_SHOT retry may be dropped; regular cycle covers it.
- C85. **NTP sync holding `wifi_mode_lock` for DNS (≤3×timeout) + UDP fetch (5 s)** — asy_ntp_client.py:431-440 — WiFi state machine and 1 Hz wifi counter block for up to ~6.5 s.
- C86. **Network not available ⇒ attempt skipped (no backoff change)** — asy_ntp_client.py:213-221 — in AP/deactivated modes NTP never runs.
- C87. **Reply rejected: LI=3 / stratum 0 (KoD) / implausible (<2025 or >2100) / malformed** — asy_ntp_client.py:243-270 — episode-suppressed; time stays wrong.
- C88. **RTC set from NTP (step change, possibly ±12 h via `NTP_Offset_S`)** — asy_ntp_client.py:66,253,263 — all `time.time()`-based ages/TS jump; offset deliberately shifts "UTC" itself.
- C89. **NTP era reinterpretation (<2025 ⇒ +2^32 s)** — asy_ntp_client.py:254-257 — a bogus small timestamp is lifted into 2161 then rejected; one in plausibility window accepted.
- C90. **`asy_ntp_time` task restart resets `Synced=False`** — asy_ntp_client.py:424-427 — a task restart drops sync until the next attempt.
- C91. **`cettime()` European DST rule, local-time None when unsynced or config missing** — asy_ntp_client.py:384-414 — non-EU rules wrong; consumers silently idle.
- C92. **`ntp_force_sync()` (boot, NTP settings PUT)** — asy_ntp_client.py:416-422 — LastSyncAge set None; resets backoff.
- C93. **NTP interval config missing ⇒ default 12 h (errno 18 every 10 s tick)** — asy_ntp_client.py:450-453 — floods history with a repeated errno (no repeat flag).

### 1.7 SCD30 (`asy_scd30_driver.py`)
- C94. **Continuous measurement not started by firmware (factory-new chip, or after ContMeas=Off)** — asy_scd30_driver.py:161-163,425-435 — no RDY edges ⇒ `read_loop` never runs a read; CO2/T/RH stay None or stale, no error ever logged.
- C95. **Data-ready = 0 at trigger ⇒ cached values re-stamped with a fresh TS** — asy_scd30_driver.py:174-187,595-611 — stale readings presented as new.
- C96. **IRQ-pin fallback (`scd_timer_triggers` ≥ 2×trigger_sec at 500 ms) when RDY stays high** — asy_scd30_driver.py:411-420 — counter only counts high samples and resets only on a read; covers stuck-high, not stuck-low.
- C97. **SCD30 init: soft reset + 2.5 s on every task (re)start** — asy_scd30_driver.py:161-172,585-589 — measurement restarts; ASC/FRC unaffected but data gap.
- C98. **NVM-persisted settings writes (MeasInt, AmbPres/start, Altitude, TempOffs, SelfCal)** — asy_scd30_driver.py:534-575 — each REST PUT is an on-chip NVM write; endurance unspecified.
- C99. **AmbPres=0 ⇒ compensation off & (re)starts continuous measurement** — asy_scd30_driver.py:59,546-554 — a "disable" value has the side effect of starting measurement.
- C100. **Non-finite CO2/T/RH words ⇒ failed read** — asy_scd30_driver.py:624-627 — counts toward streak; restarts.
- C101. **Volatile FRC readback (400 after power cycle)** — asy_scd30_driver.py:505-508 — UI shows 400 regardless of last calibration.

### 1.8 SGP40 (`asy_sgp40_driver.py`, `voc_algorithm.py`)
- C102. **Compensation source value None ⇒ read skipped, no error, algorithm unfed** — asy_sgp40_driver.py:257-281 — VOC silently absent whenever SCD30 has no data; VOC algorithm misses 1 Hz samples.
- C103. **Restore pending (`voc_init` countdown = WaitTimeNTP) / NTP wait for timestamped backup** — asy_sgp40_driver.py:214-217,357-361,380-387 — restore postponed up to 600 s.
- C104. **WaitTimeNTP=0 ⇒ `voc_init` stays 0 ⇒ no restore ever** — asy_sgp40_driver.py:357-361 — "never wait" config also means "never restore".
- C105. **Restore on every task restart (not only boot)** — asy_sgp40_driver.py:331-361 — an older FRAM backup can overwrite the live in-RAM algorithm state.
- C106. **Backup without timestamp (wrnno 13 once per episode) / restored "without timestamp" ignores BackupMaxAge** — asy_sgp40_driver.py:380-383,443-446 — stale baseline restored after long power-off.
- C107. **Backup too old ⇒ not restored** — asy_sgp40_driver.py:391-393 — 45-sample warm-up + 24 h learning restart.
- C108. **BackupPeriod=0 ⇒ backups off; BackupMaxAge=0 ⇒ any age accepted** — asy_sgp40_driver.py:51-53,221 — special values change semantics.
- C109. **Pending VOC reset with two independent sub-parts (`_reset_fram_cleared`, `_reset_algo_applied`)** — asy_sgp40_driver.py:190-195,242-307,508-519 — FRAM clear retried each cycle forever if FRAM paused/protected.
- C110. **VOC algorithm warm-up (index 0 for first 45 samples, learning 24 h)** — SPECIFICATION A.4 note; voc_algorithm.py — post-boot/post-reset index meaningless but served as a number.
- C111. **SGP40 init: serial/self-test (320 ms heater) + general-call reset to 0x00** — asy_sgp40_driver.py:586-594,670-695 — broadcast reset hits every device on that bus on every SGP40 task start.
- C112. **Temperature/RH ticks masked `& 0xFFFF`** — asy_sgp40_driver.py:597-609 — T<−45 °C/>130 °C or RH<0/>100 % wraps to an arbitrary compensation value, silently.
- C113. **`ts_storage` None (no FRAM / no ntp callback / alloc failed)** — asy_sgp40_driver.py:175-187 — backups disabled with only `pr.err`.

### 1.9 BMP3xx (`asy_bmp3xx_driver.py`)
- C114. **Forced-mode cycle with STATUS poll timeout 300 ms** — asy_bmp3xx_driver.py:63,429-447 — counts as failed read.
- C115. **Out-of-operating-range result (p∉[300,1250] hPa, T∉[−40,85] °C) ⇒ failed read** — asy_bmp3xx_driver.py:57-61,486-487 — environmental extremes become task restarts and feed the reboot accumulator.
- C116. **Calibration block implausible (all bytes equal)** — asy_bmp3xx_driver.py:516 — init fails ⇒ restart loop.
- C117. **Init re-applies OSR/IIR from cfgmgr; nothing re-applies after a chip POR** — asy_bmp3xx_driver.py:198-225 — a mid-run chip reset reverts OSR/IIR to defaults silently.
- C118. **Comp config read failure ⇒ hard-coded fallback offsets** — asy_bmp3xx_driver.py:231-234 — user offsets silently dropped from data.
- C119. **Trigger period counter (`trigger_counter` vs `trigger_period`)** — asy_bmp3xx_driver.py:271-278 — period change mid-count.

### 1.10 ISL29125 (`asy_isl29125_driver.py`)
- C120. **Auto-range vs fixed range; active range low/high** — asy_isl29125_driver.py:240-245,569-612 — range switch writes two registers; partial failure retried next cycle.
- C121. **Settle window after configure (`_settle_until_ms`), bounded wait ×2** — asy_isl29125_driver.py:614-623,1292-1293,1383 — after >2^29 ms (~6.2 d) with no configure() call `time_to_settle_ms()` returns ~6 days: read loop sleeps for days, data frozen, no error.
- C122. **AutoRangeDwell gate via `ticks_diff(now, _last_switch_ms)`** — asy_isl29125_driver.py:586 — after ~6.2 d without a switch the diff goes negative ⇒ switch-down suppressed for the next half-period.
- C123. **Calibration run (`_calibrating`, 120 s window) and candidate hold (600 s)** — asy_isl29125_driver.py:97-102,627-714,1031-1037 — `_cal_meas` never cleared; ticks wrap makes an old candidate "fresh" again ~6.2 d later.
- C124. **Brownout seen (BOUTF) ⇒ recover/re-apply, `_brownout_seen` latch** — asy_isl29125_driver.py:248,396-404,465-479 — one cycle without data; re-apply failure errno 33.
- C125. **Shadow-vs-chip divergence after failed write ⇒ re-apply** — asy_isl29125_driver.py:481-493,745-755 — divergence only checked after a write failure or config read.
- C126. **All-ones bus-fault pattern confirmed by ID re-read** — asy_isl29125_driver.py:406-409 — failed read.
- C127. **Periodic-only range decisions (interrupt line dead) — warn after 5** — asy_isl29125_driver.py:109,442-455 — dead INT line detected only indirectly.
- C128. **Overrange flag (saturation with no mitigation left)** — asy_isl29125_driver.py:424 — data published as valid with a flag.

### 1.11 Notification / LED (`asy_notification_service.py`, `asy_neopixel_driver.py`)
- C129. **Not finalized (guards return empty/defaults)** — asy_notification_service.py:247-266 — ordering bug would hide all notifications silently.
- C130. **AutoOn off / override active (`override_secs` countdown ≤3600 s)** — asy_notification_service.py:269-330 — alerts suppressed.
- C131. **Active window check `on ≤ now ≤ off` (no midnight wrap)** — asy_notification_service.py:366-369 — windows spanning midnight never trigger (owner-recorded open defect).
- C132. **No local time (unsynced, config missing) ⇒ no checks at all** — asy_notification_service.py:363-365 — alerting silently stops with NTP.
- C133. **Own config read failure ⇒ 600 s interval, nothing evaluated** — asy_notification_service.py:346-356 — alerting off, single persisted warning.
- C134. **Signal source value None ⇒ not triggered** — asy_notification_service.py:194-208 — dead sensor ⇔ "air is fine".
- C135. **Neopixel arbitration: internal `request_signal` spin (`sleep(0)`) while a ramp runs; external `led_signal` refused if pending** — asy_neopixel_driver.py:84,137-153 — busy-spin of the loop during long ramps (t≤60 s via lightCmdLED); dropped external commands.
- C136. **Overlay (WiFi LED) restored after each signal** — asy_neopixel_driver.py:155-187 — overlay and notification contend for one pixel.

### 1.12 Webserver (`asy_webserver_service.py`)
- C137. **Open connections counter vs `max_connections` (reject-when-full, closed with no response)** — asy_webserver_service.py:358,692-702 — UI sees resets; an over-ceiling burst looks like a dead device.
- C138. **Per-call 5 s timeout / outer 15 s cap per connection** — asy_webserver_service.py:321-322,234-279,707-726 — slow clients hold slots up to 15 s.
- C139. **`peer_gone` (reset seen on read) ⇒ writes muted** — asy_webserver_service.py:243,256-260,268-270 — response silently dropped.
- C140. **Header buffering until blank line** — asy_webserver_service.py:242,271-278 — a cut response never ends mid-header.
- C141. **Unhandled route exception ⇒ shaped 500 + errno 4** — asy_webserver_service.py:671-676 — exceptions during response writing escape this path (Microdot gap).
- C142. **Status-source failure ⇒ `{"error":"unavailable"}` per section** — asy_webserver_service.py:612-629 — partial /status looks successful (200).
- C143. **Captive-portal redirect for every unknown static path while hotspot active** — asy_webserver_service.py:649-667 — typos/404s become redirects in AP mode.
- C144. **Static mount absent (None) ⇒ no static routes** — asy_webserver_service.py:395-400 — UI missing entirely.
- C145. **Body > 2048 B ⇒ 413; non-dict/malformed JSON ⇒ ERR envelope** — asy_webserver_service.py:311,363-370,784-792 — clean reject.
- C146. **Unknown sensor / non-dict sub-object silently ignored in PUT /sensors** — asy_webserver_service.py:425-431 — client gets "OK" with missing keys.
- C147. **Settings-group post hook exception ⇒ whole group "Failed"** — asy_webserver_service.py:463-469 — values may already be persisted though reported Failed.

### 1.13 UART link (`asy_uart_comm.py`, `asy_uart_driver.py`, `asy_uart_link_driver.py`; dev only)
- C148. **Init error latched (`_init_errno`: bad payload/timeout/role/alloc/rxbuf)** — asy_uart_comm.py:107-131,211-222,351-355 — every call refuses with that errno.
- C149. **Busy / re-entry refused (`_busy`)** — asy_uart_comm.py:200,366,828,851 — concurrent caller gets an error, not a wait.
- C150. **Resync (drain, hold-off writes, `_in_resync`)** — asy_uart_comm.py:534-588 — writes blocked for 1.5×timeout; nested faults extend drain.
- C151. **Drain bound hit (peer never stops sending)** — asy_uart_comm.py:540-563 — link permanently resyncing.
- C152. **Blind resyncs (bytes but never a valid frame) ⇒ "link unintelligible"** — asy_uart_comm.py:575-582 — parameter mismatch (baud/payload/CRC) diagnosed, never negotiated.
- C153. **Fault streak / repeated identical errno stops persisting** — asy_uart_comm.py:204-206,315-347 — long outages leave one entry.
- C154. **Peer-initiated frame where ACK expected (simultaneous initiation, out of contract)** — asy_uart_comm.py:128,648-652 — collision has no arbitration.
- C155. **Driver cancel request latched / unacknowledged** — asy_uart_driver.py:69-101,241-256 — wedged holder only counted.
- C156. **Idle vs transaction poll rates (`poll_idle_ms` 50 vs `poll_wait_ms` 2)** — asy_uart_driver.py:64-68 — latency trade-off.
- C157. **UID wrap 0..0xFE** — asy_uart_comm.py:81,161 — duplicate-detection relies on 255-cycle window.
- C158. **Transfers/Failures counters reset by ResetErrors** — asy_uart_link_driver.py:150-160 — bench statistics wiped together with logs.

### 1.14 Misc primitives
- C159. **UDP socket not connected (bind/connect failed) ⇒ `ready()` False forever, sentinel results** — asy_udp_socket.py:68-118 — DNS server spins in warning+backoff; NTP/DNS just "no reply".
- C160. **DNS resolver fallback to 8.8.8.8/1.1.1.1 after DHCP server** — asy_dns_client.py:20,110-130 — on a firewalled LAN every NTP attempt costs extra timeouts under the WiFi lock.
- C161. **Captive DNS backoff 0.5→5 s on receive failures; 3 s pause on exceptions** — captive_dns.py:23-27,118-136 — captive portal unresponsive during backoff.
- C162. **`LockableBuffer.buf=None` on allocation failure** — base_classes.py:60-72 — FRAM chunk ops return False (degraded persistence) under heap pressure.

---

## 2. External triggers (REST routes, PUT commands, config fields)

- T1. **GET /measurements** — asy_webserver_service.py:372,404-411 — serves retained last-good values (C45) without staleness flag besides TS.
- T2. **GET /sensors** (live I2C reads of SCD30/BMP/ISL config registers via callbacks) — asy_webserver_service.py:413-418; scd30:244-249 — every UI poll performs bus transactions competing with sensor reads.
- T3. **PUT /sensors SCD30 TempOffs/MeasInt/AmbPres/Altitude/ForceCalRef/SelfCal** — asy_scd30_driver.py:257-298 — direct NVM writes on the chip, no local persistence, no rollback.
- T4. **PUT /sensors SCD30 ContMeas=false (dispatch-only)** — asy_scd30_driver.py:89,278-287 — stops measurement persistently (chip NVM); only AmbPres restarts it.
- T5. **PUT /sensors SGP40 BackupPeriod/BackupMaxAge/WaitTimeNTP** — asy_sgp40_driver.py:51-53 — semantics of 0 differ per field.
- T6. **PUT /sensors SGP40 SGPResetVOC=true (dispatch-only)** — asy_sgp40_driver.py:59,455-462,508-519 — clears FRAM backup and resets algorithm (24 h learning lost).
- T7. **PUT /sensors BMP3xx SampleInterv/PressOvers/TempOvers/FiltCoeff/offsets** — asy_bmp3xx_driver.py:74-84,251-269 — push failure triggers C41 recovery.
- T8. **PUT /sensors ISL29125 (Resolution, RangeAuto, Range, AutoRangeThresh/Dwell, IrComp*, FiltCoeff, GainRatio)** — asy_isl29125_driver.py:116-139,798-830 — each push reconfigures and restarts conversion (settle window).
- T9. **PUT /sensors ISL29125 calibrate (dispatch-only)** — asy_isl29125_driver.py:828-833,1031-1037 — starts 120 s calibration window.
- T10. **PUT /networking SSID/PW/Country/Hostname ⇒ post hook `reconnect_wifi()` (only if a field is "Valid")** — gen/dev:203, asy_wifi_service.py:806-812 — device drops off the network ~8 s; wrong credentials lead toward hotspot/deactivation.
- T11. **PUT /networking LedWifiOn (live push)** — asy_wifi_service.py:189,514-519 — status LED overlay toggles.
- T12. **PUT /networking NTP_Host/NTP_Offset_S/NTP_Interv_H ⇒ `ntp_force_sync()`** — gen/dev:205, asy_ntp_client.py:65-67 — offset shifts system "UTC"; bad host ⇒ unsynced.
- T13. **PUT /system DebugLevel** — system_service.py:59,309-323 — raises console output volume (USB stall risk, D-modes).
- T14. **PUT /system GMTOffset/DSTOffset** — asy_ntp_client.py:68-69 — local time only.
- T15. **PUT /system SystemCmd=reboot** — gen/dev:99-101, system_service.py:348-349 — flush pending configs, pause FRAM, reset in 4 s (ONE_SHOT).
- T16. **PUT /system SystemCmd=bootloader** — gen/dev:102-104, system_service.py:351-352 — device enters BOOTSEL and stays there (no watchdog in bootrom) until physical intervention; unauthenticated.
- T17. **PUT /system SystemCmd=mempause** — gen/dev:105-106, system_service.py:354-374 — FRAM writes refused 300 s (ONE_SHOT unpause).
- T18. **PUT /notification OnH/OnM/OffH/OffM/FlashBri/Interv/FlashDur/AutoOn/Warn* thresholds** — asy_notification_service.py:71-78 — windows spanning midnight silently inert.
- T19. **PUT /notification lightCmdLED {r,g,b,t} (dispatch-only)** — gen/dev:116-127 — ramp up to 60 s holds the pixel lock; concurrent requests spin.
- T20. **PUT /notification PauseTime 0..3600 (dispatch-only)** — asy_webserver_service.py:98-105,545-565 — suppresses alerts.
- T21. **PUT /status ResetErrors=true** — asy_webserver_service.py:631-639 — irreversibly clears every persisted error history (and UART counters).
- T22. **GET /status** — asy_webserver_service.py:569-603 — reads every logger; status sources may be null while WiFi lock held.
- T23. **GET / and /<path> static (frozen VFS, `.gz`)** — asy_webserver_service.py:643-667 — redirect in AP mode.
- T24. **Unregistered method/path ⇒ 404/405 shaped** — asy_webserver_service.py:112-119 — fine.
- T25. **Captive DNS queries on port 53 (AP mode only)** — captive_dns.py:85-140 — every on-subnet name resolves to the device.
- T26. **Physical triggers: USB REPL Ctrl-C/Ctrl-D, BOOTSEL button, RUN pin** — main.c:224-301 — see D-modes.
- T27. **Build-time config: `devices/*.toml` (`conn_fail_to_hotspot`, `hotspot_time_min`, `max_connections`, bus timeout/frequency, FRAM `max_size`, CS pins, `irq_pull_up`)** — devices/wozi.toml:7-96; gen/*: build_system — a `max_size` that does not match the fitted chip makes FRAM "not found" (all logs RAM-only).
- T28. **Hotspot password (build default "12345678", HotspotPW field not exposed in web groups)** — asy_wifi_service.py:50-53 — known credential; AP joinable by anyone nearby, giving T15–T21 access.

---

## 3. Chip lifecycles (datasheets)

### RP2040
- H1. **Power-on reset (DVDD ≥ 0.957 V for t_POR)** — RP2040 DS §2.12.2 — RTC restarts at 2021-01-01 (main.c:139-142); all RAM/watchdog-scratch state lost.
- H2. **Brown-out on DVDD (1.1 V core, threshold 0.86 V)** — RP2040 DS §2.12.3 — only core-voltage collapse is detected; a 3.3 V rail sag that resets/upsets peripherals (FRAM, sensors) does not reset the MCU.
- H3. **Watchdog reset (PSM WDSEL everything except oscillators); counter decrements twice per tick (E1, ≤8.3 s)** — RP2040 DS §4.7.1-4.7.3, errata E1 — indistinguishable from other resets in firmware (no reset-cause logging).
- H4. **Watchdog scratch registers survive soft/watchdog resets, cleared by RUN/POR** — RP2040 DS §4.7.4 — unused; no breadcrumb across reboots.
- H5. **Watchdog-boot / USB-boot via scratch magic (bootloader entry)** — RP2040 DS §2.8.1.1, `machine.bootloader` — BOOTSEL mode has no application watchdog: stuck until power cycle/flash.
- H6. **RUN pin low ⇒ held in reset** — RP2040 DS §2.8 boot sequence — external reset.
- H7. **GPIO pads reset with pull-down enabled (PDE=1)** — RP2040 DS §2.19 PADS_BANK0 — during reset/boot, FRAM CS (active-low) and other chip selects are pulled low until `setup()` drives them (FRAM selected during power transitions). (RU — breakout pull-ups unknown)
- H8. **XIP flash access stalls while flash is programmed/erased (interrupts off)** — RP2040 DS §2.6; F.2 — CYW43/UART/USB/timer service suspended during each littlefs write.
- H9. **UART RX FIFO 32 entries; overrun when not serviced** — RP2040 DS §4.2 — config writes or long syncs drop link bytes (dev UART link).
- H10. **I2C controller: clock stretching, timeouts, no bus recovery** — RP2040 DS §4.3 — slave holding SDA low wedges the bus until a full reset.
- H11. **USB device: E2 (endpoint abort NAK forever), E5 (no exit from RESET on busy bus), E15 (hang with VL805 xHCI — the Raspberry Pi 4 bench host), E16 (status sync)** — RP2040 errata — USB CDC can wedge permanently; with a host attached and DTR set, `print()` then blocks (see D9).
- H12. **DMA abort premature (E13), PIO used by CYW43 SPI and NeoPixel** — RP2040 errata E13 — (RU) affects driver internals only.
- H13. **Ring oscillator / clock source changes, DORMANT/SLEEP not used** — RP2040 DS §2.11 — not entered by firmware (no mode).

### Pico W board / CYW43439
- H14. **CYW43 firmware upload at `wlan.active(True)` (synchronous bus init)** — lib/cyw43-driver/src/cyw43_ctrl.c:148-215 (`cyw43_ensure_up` → `cyw43_ll_bus_init`) — loop blocked during each STA/AP (re)activation; failure ⇒ exception ⇒ `hw_op_failed`.
- H15. **CYW43 rejoin/disassoc pending states, link-down while `isconnected()` true (firmware false positive)** — lib/cyw43-driver/src/cyw43_ctrl.c:240-255 (pend_disassoc/pend_rejoin); SPEC F.2 — device believes it is connected; owner-accepted (power cycle recovers).
- H16. **CYW43 bus sleep / power-save (firmware sets pm=0xA11140 to disable)** — asy_wifi_service.py:386,452 — reverts on WLAN re-creation until re-applied.
- H17. **WL_GPIO1 SMPS PS pin / GPIO29 shared VSYS ADC & wireless SPI** — Pico W DS pinout table — reading ADC3 disturbs WiFi (firmware does not, but any future use would).
- H18. **VSYS 1.8–5.5 V buck-boost; VBUS diode-OR** — Pico W DS §2.1/§4 — supply sag affects 3V3 rail feeding FRAM/sensors.
- H19. **AP mode default SSID/password set by `main.c` before user config ("PICOxxxx"/"picoW123")** — main.c:184-197 — if `wlan.config()` fails the AP may come up with the board defaults. (RU)

### W25Q16JV (program flash / littlefs)
- H20. **Program/erase in progress; power loss mid-erase/program** — W25Q16JV DS §6.3-6.4, §8 — partially erased sector; littlefs must detect (CRC/metadata pairs).
- H21. **Write inhibit below V_WI and t_PUW after power-up** — W25Q16JV DS §6.4 — writes during brown-out are dropped, not erred.
- H22. **Nonvolatile status-register protection bits (BP, TB, SEC, CMP, SRP)** — W25Q16JV DS §7.1 — a set BP range makes littlefs writes fail (OSError) persistently. (RU)
- H23. **Endurance 100 k P/E per sector** — W25Q16JV DS features — boot-time config rewrites (C34) and any reboot loop with rewrites consume cycles.

### FRAM (MB85RS64V 8 KB on most devices, MB85RS2MTA 256 KB on dev)
- H24. **MB85RS64V supply 3.0–5.5 V** — MB85RS64V DS p.1, recommended conditions — on a 3.3 V rail, a dip below 3.0 V is out of spec while the RP2040 (IOVDD ≥1.8 V) keeps running and writing.
- H25. **Power on/off sequencing: CS must track VDD (t_pu 0.6 ms, t_pd 400 ns, ramp ≥1 ms/V)** — MB85RS64V DS "POWER ON/OFF SEQUENCE" — combined with H7, a CS pulled low during power transitions risks an accidental command. (RU)
- H26. **Destructive readout: every read is read-then-restore** — MB85RS64V DS endurance note; SPEC A.4 — power loss mid-read can corrupt the cell, hence busy marker on reads.
- H27. **Nonvolatile BP0/BP1/WPEN, WP pin, HOLD pin** — MB85RS64V/2MTA DS status register — protected chip refuses writes (and therefore reads in this design).
- H28. **MB85RS2MTA SLEEP mode (t_REC 400 µs)** — MB85RS2MTA DS SLEEP — not used; a spurious SLEEP opcode would make the chip ignore commands until CS toggles (RU).
- H29. **WEL auto-clear after WRITE/WRSR; WEL reset at power-up** — both FRAM DS — handled by verify/retry.

### SCD30
- H30. **Continuous-measurement status stored in NVM (resumes after power cycle; off if stopped)** — SCD30 Interface Description §1.4.1 — the firmware never starts it (C94).
- H31. **Measurement interval / ASC / temp offset / altitude stored in NVM** — SCD30 ID §1.4.3, §1.4.6, temp-offset and altitude sections — values outlive firmware/config resets; UI shows chip, not local, state.
- H32. **ASC needs ≥7 days of continuous operation with daily fresh air; FRC supersedes ASC** — SCD30 ID §1.4.6 — frequent reboots/stops prevent calibration; values drift silently.
- H33. **Clock stretching 30 ms normal, 150 ms once a day (internal calibration)** — SCD30 ID p.2 — bus timeout must be ≥150 ms (generator requires 200 ms); other devices on that bus stall.
- H34. **No repeated start; read header >3 ms after write** — SCD30 ID p.2, §1.4.4 — handled via separate transactions.
- H35. **Boot time < 2 s; soft reset reloads calibration** — SCD30 ID §1.4.10 — reads during boot fail.
- H36. **Data-ready flag clears on readout; data not read is overwritten** — SCD30 ID §1.4.1, §1.4.4 — two readers would steal each other's sample.
- H37. **RDY pin high while data ready** — SCD30 DS pin table — stuck high ⇔ data unread; stuck low ⇔ measurement off/miswired (undetected).

### SGP40
- H38. **Power-up 0.6 ms into idle; measurement mode keeps heater on while polled each second** — SGP40 DS §3.2, Table 7 — if the read task dies the heater is left in measurement mode until the next command (RU).
- H39. **General-call soft reset (0x06 to 0x00) resets all devices on the bus** — SGP40 DS Table 17 — firmware uses it on every init (C111).
- H40. **Self-test 320 ms, serial number read** — SGP40 DS Tables 8/12/13 — init latency; failure ⇒ restart loop.
- H41. **VOC algorithm requires 1 Hz sampling; 24 h learning; index 0 during first samples** — SGP40 DS §3.2; VOC Index info note — gaps/outages degrade index silently.
- H42. **Compensation ranges (T −45..130 °C, RH 0..100 %)** — SGP40 DS Table 10 — out-of-range inputs wrap in firmware (C112).

### BMP384/388/390
- H43. **POR ⇒ sleep mode with default config; `por_detected` event bit** — BMP388 DS §3.3, event register — firmware never reads `por_detected`; OSR/IIR silently revert.
- H44. **Forced mode single conversion, ERR_REG fatal_err/cmd_err/conf_err** — BMP388 DS §3.3.2, ERR_REG — only cmd_err checked at reset; conf_err would leave forced mode unconverted ⇒ status timeout.
- H45. **Supply POR thresholds (VDD/VDDIO) and ramp ≥10 ms** — BMP388 DS power-on section — fast ramps can leave chip unreset (RU).
- H46. **Operating range −40..85 °C, 300..1250 hPa** — BMP3xx DS Table 2 — firmware converts out-of-range into failures (C115).

### ISL29125
- H47. **Bidirectional POR (powers down into Reset below threshold), BOUTF=1 after power-up** — ISL29125 DS "Power-On Reset", reg 0x08 B2 — config wiped to 0x00, detected only via BOUTF each cycle.
- H48. **Reset command 0x46 to reg 0x00 (all registers default)** — ISL29125 DS reg map — used by driver reset.
- H49. **STOP mid-byte resets serial interface without effect** — ISL29125 DS "Stop Condition" — a broken transaction silently does nothing (write lost, shadow diverges).
- H50. **INT pin open-drain, cleared by reading status (0x08)** — ISL29125 DS interrupt section — status read is destructive; two readers lose the flag; external pull-up required when `irq_pull_up=False` (dev).
- H51. **SYNC mode (INT becomes input) / CONVEN** — ISL29125 DS Table 7/13 — must stay 0; a corrupted CONFIG1 bit would invert INT semantics.

### WS2812 / NeoPixel
- H52. **Latch on >50 µs low (reset code); pixel keeps last colour while powered** — WS2812 DS timing — after an MCU crash/reset/hang the LED shows the last colour (e.g. a warning) indefinitely.
- H53. **Data input V_IH ≈ 0.7·VDD (3.3 V data vs 5 V pixel supply)** — WS2812 DS electrical — marginal logic level ⇒ random colours under noise (RU).
- H54. **Bit-banged timing with interrupts disabled during `pixel.write()`** — neopixel module — short IRQ-off windows per write; ramps write 20×/s.

---

## 4. MicroPython runtime transitions (pinned v1.29.0)

- D1. **Hard boot sequence: `_boot.py` (littlefs mount or mkfs) → `boot.py` from FS → frozen `main.py`** — ports/rp2/main.c:224-243, ports/rp2/modules/_boot.py — a corrupt/unmountable littlefs is silently reformatted (all config files lost → factory defaults).
- D2. **Filesystem `boot.py` present** — main.c:229-240, shared/runtime/pyexec.c:743-753 — runs before the firmware; if it raises, `main.py` is skipped (ret==0) and the device idles in the REPL with no WDT running. (RU — would need a leftover file, e.g. from legacy deployments)
- D3. **Frozen `main.py` takes precedence over a FS `main.py`** — pyexec.c:744-747 — a stray FS `main.py` is ignored (good), but cannot be used for recovery either.
- D4. **`main()` raises / returns ⇒ `finally: asyncio.new_event_loop()` ⇒ REPL** — buildgen/codegen.py:696-708 — WDT already armed ⇒ watchdog reset 8 s later; traceback only on USB console.
- D5. **KeyboardInterrupt from USB REPL (Ctrl-C)** — pyexec_frozen_module(..., true) main.c / pyexec.c:756-760 — stops the event loop; WDT not fed ⇒ reset in ≤8 s; interactive debugging impossible without disabling WDT.
- D6. **Soft reset (Ctrl-D): network/UART/PIO/DMA/pins/soft timers deinit, lwIP NOT re-initialised, cyw43 not re-inited, RTC kept, WDT keeps running** — main.c:248-293,163-171 — re-run of `main.py` re-creates WDT; lwIP state from before survives.
- D7. **`gc_sweep_all()` at soft reset** — main.c:288 — finalisers (`Timer.__del__`) run.
- D8. **USB CDC not connected: output written to FIFO, overwritten** — shared/tinyusb/mp_usbd_cdc.c:111-118 — logs lost (expected).
- D9. **USB CDC connected (DTR) but host not draining: `print()` blocks up to 500 ms per call** — mp_usbd_cdc.c:124-137, ports/rp2/mphalport.h:36 — at higher DebugLevel the event loop stalls repeatedly: timers queue up, watchdog margin shrinks.
- D10. **Scheduler queue (depth 8) full ⇒ soft Timer/Pin IRQ callbacks silently dropped** — ports/rp2/mpconfigport.h:131; shared/runtime/mpirq.c:103-106 — PERIODIC timers self-heal; ONE_SHOTs (reset, auto-unpause, sequencer, NTP retry) are lost forever.
- D11. **Exception in a hard IRQ ⇒ timer disabled ("don't run again")** — ports/rp2/machine_timer.c:50-61 — not used (all soft), but a future `hard=True` would self-disable.
- D12. **Alarm pool (default 16 alarms) exhausted ⇒ `Timer.init()` OSError(ENOMEM)** — machine_timer.c:107,117; pico_time default MAX_TIMERS 16 — dev arms ~13 concurrently; each site degrades differently (C5/C6/C9/C13).
- D13. **ThreadSafeFlag coalescing** — extmod/asyncio — multiple sets before a wait collapse into one: 1 Hz counters undercount after stalls.
- D14. **GC: reactive at threshold(-1) default vs `gc.threshold(32768)` set by `main.py`** — codegen.py:704 — allocation failures in fragmented heap (“memory allocation failed”) caught-and-degraded in many sites.
- D15. **Heap exhaustion / fragmentation over long uptime** — SPEC Part I; asy_webserver_service.py:107-110 — partial responses, FRAM buffer allocation failure (C162), task death (supervisor restarts).
- D16. **`MemoryError` not an `OSError`** — SPEC F.1 — any `except OSError` site lets MemoryError escape to the supervisor.
- D17. **`asyncio.TimeoutError` not an `OSError`** — SPEC F.1 — mis-ordered handlers miss it.
- D18. **Synchronous blocking calls (machine.I2C transfers up to bus timeout, SPI, flash writes, `wlan.active/connect/deinit`)** — SPEC F.2 — cannot be timed out; watchdog is the only backstop.
- D19. **littlefs: commit on close (old content survives power loss), ENOSPC on full FS** — extmod/vfs_lfs; config_manager.py:374-388 — full disk ⇒ "running unpersisted" forever. (RU — FS is large relative to configs)
- D20. **Flash program/erase disables interrupts port-wide** — config_manager.py:302-304 comment; SPEC F.2 — HTTP/WiFi/UART/USB stall during every config write.
- D21. **lwIP pool limits (TCP PCB 9, listen 8, UDP PCB 5, PBUF 16, MEM 12000)** — toolchain/versions.toml [lwip] — TIME_WAIT pcbs and AP-mode UDP users (DHCP server, DNS server, mDNS) can exhaust pools; accept/bind failures. (RU)
- D22. **Network stack states: STA idle/connecting/obtaining IP/got IP/wrong password/no AP/fail; AP up** — asy_wifi_service.py:592-621 — `STAT_GOT_IP` also on AP interface.
- D23. **DHCP lease renewal / IP change** — lwIP DHCP — clients bookmarked to old IP lose device; nothing logs it. (RU)
- D24. **`time.ticks_ms()` period 2^30 ms (~12.4 d); `ticks_diff` valid < 2^29 ms (~6.2 d)** — SPEC F.1 — ISL29125 settle/dwell/calibration gates break after long idle (C121–C123).
- D25. **`time.mktime()`/`gmtime()` overflow past ~2037 on rp2** — src comments (e.g. asy_scd30_driver.py:177, system_service.py:145) — every sensor read computes a timestamp first ⇒ all reads fail in 2038+.
- D26. **RTC epoch 2021-01-01 at hard boot until NTP** — main.c:139-142 — all TS fields plausible-looking but wrong.
- D27. **`json.dumps()` never raises; emits `nan`/`inf`** — SPEC F.1 — any unguarded non-finite value breaks the whole UI page.
- D28. **`struct.pack` silently truncates** — SPEC F.1 — FRAM header packing of out-of-range values.
- D29. **Frozen bytecode line numbers ≠ source (TYPE_CHECKING strip)** — SPEC F.1; scripts/build_firmware.py:52-56 — on-device tracebacks mislead.
- D30. **Unix-port-only transitions (SIGINT heap lock, nested `asyncio.run()` segfault, poll on non-fd objects)** — SPEC F.6, CLAUDE.md — twin/test artefacts, not firmware.

---

## 5. Lifecycle

- L1. **Factory / first boot on a new Pico W** — _boot.py (mkfs), config_manager.py:459-460 — every config file created with defaults (empty SSID ⇒ hotspot), FRAM blank, SCD30 factory state (measurement possibly off).
- L2. **First boot after FS loss (mkfs)** — D1 — identical to factory except FRAM/SCD30 NVM keep old state: FRAM error history from a previous life is shown as current.
- L3. **Normal boot (configured)** — gen/*:main — WDT → construct → setup batch → timers → NTP trigger → tasks.
- L4. **Boot during network outage** — asy_wifi_service.py:479-489 — 5 failed attempts ⇒ hotspot ⇒ (no client) ⇒ STA again ⇒ permanent deactivation (C67/C68).
- L5. **Warm-up phase (first minutes)** — SCD30 2.5 s reset, SGP40 45-sample warm-up + restore wait ≤600 s, NTP unsynced, boot signature unresolved ≤120 s — data served but not yet meaningful.
- L6. **Steady state, STA connected, NTP synced** — baseline.
- L7. **Long uptime > 6.2 d (ticks half-period)** — D24 — ISL29125 gates invert (C121–C123).
- L8. **Long uptime > 12.4 d (ticks wrap)** — D24 — any future subtraction-based tick math breaks.
- L9. **Long uptime: counter saturation (err_count 0xFFFF; uptime/LastSyncAge/WifiUptime 0xFFFFFFFF ≈136 y)** — print_log.py:65; system_service.py:80; asy_ntp_client.py:209 — error counts frozen first.
- L10. **Long uptime: heap fragmentation** — D15.
- L11. **Year ≥ 2038 (or NTP reply in 2038–2100 window)** — asy_ntp_client.py:52-53, D25 — sensor reads all fail ⇒ restart/reboot loop; RTC reset to 2021 on reboot, re-set by NTP ⇒ endless.
- L12. **NTP era rollover 2036 (handled by era reinterpretation)** — asy_ntp_client.py:48,254-257.
- L13. **Commanded reboot** — T15, C10-C11.
- L14. **Supervisor reboot** — C7-C8.
- L15. **Watchdog reset (any stall ≥ 8 s, C1–C4, D4, D5, D9)** — H3 — no reset cause recorded; FRAM writes in flight torn (C51/C52).
- L16. **Brown-out / power loss (abrupt)** — H1/H2/H20/H24 — torn FRAM chunks, staged config lost (C36), SCD30/ISL/BMP reset independently.
- L17. **Boot loop (any persistent cause: missing sensor, config dir, 2038, exception in build_system)** — C7, C29, L11, D4 — each boot rewrites logs, each abrupt reset risks torn chunks; evidence erased by the loop itself.
- L18. **Bootloader (BOOTSEL) entry and stay** — T16, H5 — device offline until physical action.
- L19. **Firmware upgrade (UF2 reflash, FS preserved)** — scripts/build_firmware.py — configs survive; schema changes rewrite files (C32/C33); FRAM chunk layout may shift (instance order) ⇒ CRC failures or CRC8 false accepts (C58); SCD30 NVM keeps old settings.
- L20. **Upgrade from legacy firmware (1.24/1.26, old FS contents: `config.json`, legacy `boot.py`/`main.py`)** — CLAUDE.md legacy notes; D2/D3 — stray FS files can preempt startup. (RU)
- L21. **Firmware/website version string unchanged across builds ("2.0b0"; only build date differs)** — buildgen/version.py — two different images are indistinguishable by version.
- L22. **Reflash with different `max_size`/CS pin vs fitted FRAM** — T27 — FRAM "not found", all logs RAM-only.
- L23. **Hardware-test scripts run against a deployed board's FRAM** — CLAUDE.md FRAM caveat — chunk 0 overwritten / fabricated history.
- L24. **Shutdown: none (power removal only); `stop_*_timer()` methods unused** — system_service.py:264-265 et al. — no graceful flush except the REST reboot path.

---

## 6. Environment

### Network
- E1. **Router/AP absent at boot** — L4.
- E2. **Router reboot while device established** — C63 — 60 s retries forever (good), but NTP/getters starve during lock-held sleeps.
- E3. **Wrong password / AP not found / auth timeout** — C75 — streak toward hotspot.
- E4. **Phone/laptop auto-joining the device hotspot** — C65 — AP held forever.
- E5. **DHCP gives no/bad DNS server, or DNS blocked; fallback public resolvers firewalled** — C160 — NTP never syncs; backoff to 600 s.
- E6. **NTP server returns KoD/unsynchronised/bogus time; LAN NTP spoofing** — C87/L11 — time wrong or 2038 trap.
- E7. **CYW43 link false-positive (`isconnected()` true, no traffic)** — H15 — device unreachable, owner-accepted.
- E8. **Weak RSSI / flapping link** — SPEC F.2 data — rejoins; NTP failures.
- E9. **IP change via DHCP** — D23.
- E10. **Multiple devices with same hostname/default hostname** — asy_wifi_service.py:48 — name collisions on the LAN. (RU)

### Clients
- E11. **Several browser tabs/devices polling concurrently** — js/poll-manager.js:40-87 (per-tab serial queue only) — server ceiling 6; extra connections reset (C137).
- E12. **Page load burst (index + assets) vs connection ceiling / backlog** — asy_webserver_service.py:318-320,353 — partial UI loads.
- E13. **Slow / stalled client (Slowloris, mobile in AP mode)** — C138 — slots held 15 s.
- E14. **Client disconnects mid-response** — C139 — silent.
- E15. **Malformed/oversized JSON, wrong types, bool-for-int, NaN/inf via 1e999** — config_manager.py:121-187; C145 — rejected; ints accept integral floats.
- E16. **PUT timeout on the client while the device applied it** — js/poll-manager.js:7-33, js/render.js:225-274 — UI reports Failed for an applied change.
- E17. **Unauthenticated LAN/hotspot client issuing reboot/bootloader/mempause/ResetErrors** — T15–T21 — no authentication on any route.
- E18. **Captive-portal probes from phones in AP mode** — C143/T25 — every probe answered with redirect.
- E19. **Static UI served from a different firmware/website build (cached in browser)** — js/main.js — definitions/fields mismatch with backend. (RU)

### Power / host / USB
- E20. **3.3 V rail sag (heavy WiFi TX bursts, weak USB supply)** — H2/H18/H24 — peripherals misbehave without MCU reset.
- E21. **USB host attached and draining / attached not draining / detached** — D8/D9.
- E22. **Raspberry Pi 4 (VL805) as USB host** — errata E15 — unrecoverable USB device hang.
- E23. **Power cycling during a config write or FRAM op** — L16.

### Physical / sensor environment
- E24. **Condensing humidity (RH ≥ 100 %)** — C112 — SGP40 compensation wraps.
- E25. **Temperature outside BMP −40..85 °C or SCD30/SGP40 ranges** — C115, H42 — restarts / bad compensation.
- E26. **Bright light saturation / darkness on ISL29125** — C120/C128 — range switching; Overrange.
- E27. **Stable light for > 6 days (no range switch) / fixed-range config** — C121/C122.
- E28. **No fresh air for ASC (7-day requirement)** — H32 — CO2 drift.
- E29. **Sensor unplugged / replugged (hot)** — SPEC F.2 — task respawn re-probes; bus wedge escalates to reboot.
- E30. **I2C bus wedged by a slave (SDA low)** — H10 — all devices on bus fail; restarts don't reconstruct the peripheral ⇒ reboot loop.

---

## 7. Host side (twin, build tooling, tests)

- S1. **`_generate_sensortask_modules.py` interrupted mid-loop (non-atomic `write_text`)** — scripts/_generate_sensortask_modules.py:45,51 — truncated/partial module or a mix of fresh and stale device modules in `build/generated_src/`.
- S2. **Stale generated module for a removed/renamed device remains** — same file, out dir never cleaned — tests can import an obsolete device module.
- S3. **`build_date` from wall clock** — buildgen/version.py — non-reproducible images; dirty trees not encoded in version.
- S4. **`build_firmware.py` stages the working tree (uncommitted edits included)** — scripts/build_firmware.py:64-108 — a flashed image may not correspond to any commit.
- S5. **mpy-cross build dir wiped then rebuilt; interruption leaves no mpy-cross** — scripts/build_firmware.py:153-158 — next build rebuilds (recoverable) but a concurrent build would break.
- S6. **`setup_toolchain` checkout to a new ref / interrupted clone or fetch** — toolchain/setup_toolchain.py:183-217 — half-updated checkout reused; `rmtree(build_dir)` steps leave no build.
- S7. **Offline run (`setup` needs network; `test` subcommand offline)** — setup_toolchain.py:550-605 — network-dependent steps fail mid-way.
- S8. **`uv sync` third-party download flake (actionlint-py)** — CLAUDE.md, ci.yml retry — masquerades as test failure.
- S9. **`uv.lock` merged line-wise ⇒ pins bypassed silently** — CLAUDE.md — tool versions drift, `uv lock --check` passes.
- S10. **Twin FRAM/SCD30 state flushed only in `finally`** — digital_twin/README "FRAM persistence"; _fram_chip.py:96-106 — SIGKILL/timeout loses state; interrupted save leaves a truncated file that `_load_state()` partially loads or treats as blank without error.
- S11. **Twin writes config files into committed `digital_twin/config/`** — digital_twin/run_generic_integration.py:31,359 — running the twin dirties the tree / mutates committed fixtures.
- S12. **Two suites binding real ports concurrently (twin HTTP/DNS vs `npm test`)** — CLAUDE.md — cross-talk failures that look like code defects.
- S13. **SIGINT into Unix-port GC (heap lock), shutdown-only exit-1 flake** — SPEC F.6, B.14.1 — mitigated by override; regression if override not applied.
- S14. **`scripts/test.sh` per-file retry on timeout (3 attempts); MemoryError grep only on deciding attempt** — scripts/test.sh:311-383 — intermittent hangs are masked as passes.
- S15. **Backgrounded pytest tier with EXIT-trap cleanup; `setcap` needing sudo** — scripts/test.sh:238-290 — killed runs can leave stray processes / unprivileged runs fail late.
- S16. **Coverage build (`build-settrace`) inflates allocations 4–5×** — CLAUDE.md, SPEC E.5.2 — allocation findings under `--coverage` are not representative.
- S17. **Unix-port vs rp2 differences (double vs single float, 64-bit struct sizes, TZ-dependent mktime, ticks period 2^62)** — SPEC F.1, CLAUDE.md — host tests cannot exercise rp2 rollover/overflow modes (C121, D25).
- S18. **Hardware-tier deselection by opt-in gates (flash_cycle, persistence_write, long_soak)** — CLAUDE.md — "clean" run excludes deselected wear-critical paths.
- S19. **Dirty working tree in the bench chroot recipe (copies uncommitted files)** — CLAUDE.md build-environment recipe — verification of a state that is not committed.

---

## 8. Dangerous pairs (rare mode × rare mode that share a resource or overlap in time)

- P1. **Loop stall ≥ ~1 s (D9 USB CDC block, D20 flash write, H14 CYW43 upload, H33 150 ms stretches stacking) × ONE_SHOT timer due (C11 reset, C13 unpause, C4 sequencer, C84 NTP retry)** — scheduler queue (depth 8) overflows with the ~9 periodic 1 Hz/2 Hz callbacks and drops the one-shot: commanded reboot never happens with FRAM paused forever, or boot hangs until WDT.
- P2. **Factory/unconfigured device (L1, C69) × nobody joins the hotspot within `hotspot_time_min` (C66) × `hotspot_started_once` latch (C68)** — WiFi permanently deactivated (C67); needs a power cycle; nothing on the device explains why.
- P3. **Router outage at boot (L4) × outage longer than 5 attempts + hotspot window** — same terminal deactivation, on configured devices after a household power cut where the Pico boots faster than the router.
- P4. **SCD30 measurement off (C94/T4/H30) × SGP40 compensation wired to SCD30 (C102) × notifications (C134)** — CO2, VOC and alerts all silently absent; zero errors logged anywhere.
- P5. **SCD30 data-ready 0 at trigger (C95) × notification thresholds (C134)** — stale CO2 re-stamped as fresh keeps (or never clears) an alert.
- P6. **SGP40 task restart (general call, C111/H39) × concurrent SCD30/ISL29125/BMP transaction on the same bus (dev i2c1, wozi i2c1)** — sibling devices reset mid-transaction or lose configuration (ISL shadow diverges; BMP OSR revert, C117/H43); detection only indirect.
- P7. **Permanently failing sensor init (E29/E30) × supervisor accumulator (C7)** — reboot every ~8–10 s; each abrupt WDT/reset (P8) risks torn FRAM chunks, and the boot loop erases the error history that would explain it (C21, C52).
- P8. **Abrupt reset (L15/L16) × FRAM chunk write/read in flight (C51/C52)** — whole per-module error history lost (owner-accepted 1-in-8) exactly when an investigation needs it.
- P9. **Firmware reflash with changed instance order (L19) × CRC8 log chunks (C58)** — 1/256 per chunk chance of a plausible fabricated error history read as evidence.
- P10. **Config flash write (C36/D20) × power loss** — just-accepted change lost silently; GET had already shown it (owner-accepted window).
- P11. **Config flash write (D20) × dev UART link traffic (H9, C150)** — RX FIFO overrun during IRQ-off window ⇒ frame loss ⇒ resync storms.
- P12. **NTP sync holding `wifi_mode_lock` ≤6.5 s (C85) × STA 60 s retry holding the same lock (C63)** — NTP waits up to 60 s per attempt; status getters null; wifi uptime frozen.
- P13. **WiFi deactivated/hotspot (C64/C67) × NTP staleness after 3×interval (C83)** — notifications silently stop ~36 h later (C132) while LED and sensors keep running.
- P14. **Hotspot/no-NTP period (C82) × SGP40 backup written without timestamp (C59/C106) × long power-off** — stale VOC baseline restored with no age check.
- P15. **Long uptime > 6.2 d (L7) × ISL29125 fixed range or stable light (E27)** — read loop sleeps ~6 days in `_settle_wait()` (C121): lux/RGB frozen at last values, no error, every ~12.4-day cycle.
- P16. **Long uptime (L7) × completed ISL29125 calibration (C123)** — stale `GainMeas` candidate reappears as fresh; a user copying it applies a wrong gain ratio.
- P17. **RH > 100 % condensation (E24) × SGP40 humidity tick wrap (C112)** — VOC compensation at ~0 %RH, silently skewed index precisely in humid episodes.
- P18. **Year 2038 or bogus NTP reply (L11/E6) × every sensor read stamping time first (D25)** — all readers fail ⇒ reboot loop; RTC reset to 2021 on hard boot and NTP re-arms the trap each time.
- P19. **Config layer invalid (C29: file became a directory, FS damage) × WiFi LED-config read at task start (C70)** — permanent deactivation plus sensor init failures ⇒ unreachable reboot-looping device.
- P20. **littlefs unmountable ⇒ mkfs (D1) × P2** — a filesystem fault becomes "factory reset + WiFi permanently off after 8 minutes".
- P21. **USB host attached but not draining (D9, E22) × DebugLevel ≥ 3 (C17/T13)** — every log line blocks 500 ms ⇒ WDT starvation reboot loop that disappears when the cable is unplugged.
- P22. **Mempause (T17) or open-ended reboot pause (C12) × ResetErrors (T21)** — RAM rings cleared, FRAM untouched; old history reappears after the next reboot (C24) and looks like new faults.
- P23. **Bootloader command (T16) × unauthenticated hotspot with known password (T28, E17)** — anyone nearby can take a unit offline until physical access.
- P24. **Reboot command (T15) × PUT during the 4 s reset window (C10)** — newly staged config flush cut by reset (not covered by `flush_pending()`, which ran before).
- P25. **Alarm-pool exhaustion (D12) × timer starter order** — whichever starter fails silently loses its sensor trigger; with C5 the remaining starters never run.
- P26. **3.3 V sag (E20, H24) × FRAM write** — MB85RS64V out of its 3.0 V minimum while the MCU continues; dual-copy may catch it, but both copies written in the same sag window are both bad.
- P27. **GPIO pull-down CS during reset (H7) × FRAM power sequencing (H25)** — chip selected through power transitions; spurious command risk. (RU)
- P28. **BMP3xx POR mid-run (H43) × persisted OSR/IIR config** — chip runs defaults while config and UI claim otherwise; nothing re-applies until a task restart.
- P29. **Many clients / captive probes (E11/E18) × lwIP PCB pool (D21) × max_connections (C137)** — API appears dead in AP mode exactly when a user is trying to configure the device.
- P30. **WLAN mode switch blocking (H14/C73) × NeoPixel ramp and UART poll timing** — visible LED stutter and UART timeouts during every STA↔AP transition.
- P31. **SCD30 daily 150 ms clock stretch (H33) × i2c bus without 200 ms timeout (wozi/arzi i2c1, dev i2c0)** — only the SCD30 bus carries the 200 ms timeout; any future co-location breaks silently (generator-enforced today).
- P32. **FRAM absent/disabled (C47/L22) × any investigation of a reset** — no persisted evidence exists at all, while `/status errcount` still looks normal.
- P33. **Twin killed before `finally` (S10) × persistence-across-reboot checks** — truncated state file loaded as partial/blank FRAM, producing false pass/fail on persistence scenarios.
- P34. **Test retry on timeout (S14) × intermittent hang introduced by a change** — regression passes CI on attempt 2.
