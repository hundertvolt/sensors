# M2 by-mode silent-failure pass: network, time, REST, web, notification/LED (read-only)

Slice: inventory `audit/sweeps/scan_runs/20261006_mode_inventory_blind.md` §1.5 (C62-C81), §1.6 (C82-C93), §1.11
(C129-C136), §1.12 (C137-C147), §2 (T1-T28), §3 Pico W / CYW43439 (H14-H19), §4 D21-D23 and D26, §6 Network and
Clients (E1-E19): 108 IDs. Read: `src/asy_wifi_service.py`, `asy_ntp_client.py`, `asy_webserver_service.py`,
`asy_notification_service.py`, `asy_neopixel_driver.py`, `captive_dns.py`, `asy_udp_socket.py`, `asy_dns_client.py`,
`api_response.py`, `config_manager.py` (getters/setup), `build/generated_src/sensortask_dev.py` (and wozi's matching
lines), `js/poll-manager.js`, `js/render.js`, `js/main.js`, `js/app.js`, `html/index.html`, `html/definitions/dev.json`
(poll groups), `ext/microdot.py`, legacy `python/CommonDrivers/async_connect.py` (field behaviour only), pinned
MicroPython v1.29.0 (`ports/rp2/main.c`, `extmod/modlwip.c`, `extmod/cyw43_config_common.h`,
`extmod/lwip-include/lwipopts_common.h`, `lib/cyw43-driver/src/cyw43_ctrl.c`, `lib/lwip/src/core/tcp.c`). WO = merged
changes in `audit/consolidation/M_*.md`; REG = `audit/REGISTER.md` parked deltas. Line numbers are HEAD (`1b7d83d`).
Devices: WiFi, NTP, webserver, notification and NeoPixel are on all six devices (`arzi`, `dev`, `grkizi`, `klkizi`,
`schlafzi`, `wozi`); no bus is involved in this slice except where noted.

## (A) Verdict per inventory entry

| ID | verdict | evidence | note |
|---|---|---|---|
| C62 | owner | `asy_wifi_service.py:479-489`; SPEC A.4 `:277-283` "(owner, 2026-07-13, `368fa83`)" | The SEEKING streak → hotspot is the confirmed legacy fallback (legacy `async_connect.py:292-345` identical). Its console-only trace is M2-03. |
| C63 | WO | lock held across `sleep(60)`: `_run_sta_mode()` `:583-590` → `_on_sta_disconnected()` `:471-473` | M.SRC_NET.088 moves the 60 s wait outside `wifi_mode_lock`. "Never falls back to hotspot once connected" is owner (A.4, 2026-07-13). |
| C64 | WO | `network_available()` `:780-781` excludes HOTSPOT; `get_wlan_rssi()` `:756-766` raises→print each `/status` poll | M.SRC_NET.091 reads RSSI only in STA+connected. Claim "notifications off" is wrong at HEAD: `cettime()` stays valid while `Synced` (staleness unreachable, see C83); after WO .057 it stops at 3× interval → M2-02. |
| C65 | NEW | `_manage_hotspot_stations()` `:575-581`, `_hotspot_client_connected()` `:396-404` | M2-04: AP held while any station is associated; LED indistinguishable from STA-connected. |
| C66 | owner | `_hotspot_client_absent()` `:406-425` (PERIODIC), `_register_sta_connection_failure()` `:485-486` | "permanent WiFi deactivation after a second STA failure streak" (owner, 2026-07-13, SPEC A.4 `:279-281`); WO M.SRC_NET.100 adds the visible deactivated LED pattern (owner, 2026-09-29/10-02). |
| C67 | owner | `:823-824`, `_reset_wlan_connect_state()` `:304-307` | Same owner bullet ("only a physical power-cycle clears it", task-restart guard owner 2026-08-11); WO M.SRC_NET.100 pattern makes it visible. |
| C68 | owner | `:303`, `:366`, `:485-486`; legacy `async_connect.py:176` | Latch spans a successful connection, as legacy; covered by the same owner bullet and SPEC E.6.4. The hotspot-PUT trap it enables is M2-01. |
| C69 | owner | `_attempt_sta_connect()` `:441-443` sets failures = max | Legacy identical (`async_connect.py:292-294`); falls under the A.4 owner bullet. M2-01 raises it as a fine-tuning question (its fix also closes this). |
| C70 | WO | `_apply_initial_led_config()` `:318-323`; config invalid only for a directory at the path or an empty default (`config_manager.py:404-440`) | Practically unreachable; M.SRC_NET.084 keeps the persisted wrnno and shows the deactivated pattern on the LED default. |
| C71 | safe | `reconnect_wifi()` `:806-812` only sets flags; `_handle_reconnect_trigger()` `:538-556` | The 5 s grace runs on the next loop pass, after the PUT response; bounded sleeps, no lost state. |
| C72 | WO | `:833-840` give-up → task return | M.SRC_NET.102 adds the radio re-init rung under the A.U10.R01 ladder before the give-up; give-up stays persisted (M.SRC_NET.100). |
| C73 | WO | `_switch_wlan_mode()` `:278-293`; getters `:738-778` return None while locked | M.SRC_NET.098 (getters read held state), .082 (bool result, `_ap_selected`). |
| C74 | safe | `_disconnect_sta_and_wait()` `:336-351` | Bounded; timeout persisted (errno 18) and sets `hw_op_failed`, feeding the streak. |
| C75 | NEW | `_poll_sta_connect_status()` `:592-621` exits silently after 10 polls; `:482` evt only | M2-03 (a connect attempt stuck in CONNECTING/NOIP, and both phase transitions, leave no persisted trace). Repeat rule for the warnings that do exist: WO A.U3.02 / M.SRC_NET.089. |
| C76 | WO | `_radio_values()` `:704-716` persists wrnno 8 | Claim "without the user noticing" partly wrong (persisted); M.SRC_NET.080 shows the value in use on GET, .096 one radio check. |
| C77 | safe | `set_wifi_led()` `:792-804`; generated `conn.set_ext_led(neopixel)` `gen/dev:194` | Overlay is a single bool restored after every signal (`asy_neopixel_driver.py:187`); WO M.SRC_NET.078 drops `led_pin`. |
| C78 | safe | `_flash_led_off()` `:527-536` → `NeopixelDriver.on/off()` `asy_neopixel_driver.py:125-131` | Overlay writes wait on `led_overl_lock` held by a ramp; the ThreadSafeFlag coalesces to the latest state, written after the ramp. Nothing lost. |
| C79 | WO | `_networking_status()` `gen/dev:139-149` reads `get_wlan_ifconfig()`/`get_wlan_rssi()` → None when locked | M.SRC_NET.091/.098 publish one 1 Hz snapshot; .088 removes the 60 s locked hold. |
| C80 | WO | `time_counter()` `:843-860` (+1 per wake) | M.SRC_NET.101: `TickSeconds` measured time, no coalescing loss. |
| C81 | WO | `captive_dns.py:85-154`; `_configure_hotspot_ap()` `:392-394` `.done()` guard | Bind/receive failures conflated and backoff: M.SRC_NET.007; burst drops: SF-A08. |
| C82 | WO | `asy_ntp_client.py:424-444` backoff; `_now()` `:144-148` returns RTC epoch time | M.SRC_CORE.032 `utc_now()` → None pre-sync, M.SRC_SENS.089-.091; the notification's silence: SF-B17. Never-give-up backoff is owner (Part C.7.2, 2026-09-24). |
| C83 | WO | `ntp_time_hours_counter()` `:455-473`: `ntp_sec_count` is reset to 0 at every due (≤ 1× interval), so the `3×` branch `:459` is unreachable except after an `NTP_Interv_H` decrease | Claim "flips silently" refuted at HEAD (never flips; legacy `async_connect.py:450-461` same). M.SRC_NET.057 makes staleness reachable on the tick age; its consequence for LED alerts is M2-02. |
| C84 | safe | `_handle_ntp_sync_failure()` `:272-293` | A dropped ONE_SHOT retry is backstopped by the PERIODIC check's due logic `:462-473`; M.SRC_NET.051 states it. |
| C85 | WO | lock held `:433-440`; resolver `asy_dns_client.py:110-120` (DHCP + 2 built-ins × 0.5 s) + fetch 5 s ≈ 6.5 s | M.SRC_NET.043 bounds `DNSFallback` to three (lock-hold bound), .056 `async with`; lock-hold table A.U18.34. Getter/uptime effects: C79/C80. |
| C86 | safe | `_run_ntp_sync_attempt()` `:213-221`, backoff gate `:443` | By design: no network → no attempt, no backoff growth; resumes on the next due tick after STA returns. |
| C87 | SF | `_parse_ntp_reply()` `:243-270` | REG U18 rows "NTP accepts 44-47-byte replies" and "zero transmit timestamp"; codes per M.SRC_NET.049. Rejections are persisted (episode rule). |
| C88 | safe | RTC set `:262-263`; elapsed times use ticks (first pass A, "time/ticks") | Wall-clock ages across a step: negative/shifted FRAM backup age is handled by WO (M_SRC_SENS.md:1596-1606, "age < 0 or age > …" expires). `NTP_Offset_S` shifting system time is the documented field ("affects system time and all timestamps", `:73`). |
| C89 | SF | `:254-258` era step | The in-window case (raw 0 → 2036) is REG U18 "zero transmit timestamp". |
| C90 | safe | `asy_ntp_time()` `:424-427` | After a restart the sync recurs within `_retry_wait_s` (reset to 10 s by the last success, `:306-308`); RTC untouched; the restart itself is traced by the supervisor. |
| C91 | SF | `cettime()` `:384-414` | EU switch dates are legacy's (`async_connect.py:464-480`); `DSTOffset` 0 serves non-EU. Consumers idling on `None`: SF-B17. |
| C92 | WO | `ntp_force_sync()` `:416-422` keeps `Synced` | M.SRC_NET.055 clears `Synced` with the age (owner, 2026-09-29). |
| C93 | WO | `:450-453` errno 18 every 10 s | Reachable only with an invalid store (see C70); M.SRC_NET.057 keeps it persisted under the central repeat rule (A.U3.02: one slot per run). |
| C129 | WO | `asy_notification_service.py:247-266` guards | M.SRC_SENS.033: construction-time signals, guards removed. |
| C130 | safe | `auto_led_override()` `:317-330`; `PauseTime` on `/status` `gen/dev:159-162` | Visible; RAM-only across reboot noted under SF-B17. |
| C131 | WO | `:366-369` | M.SRC_SENS.037 `_in_window()` (owner, 2026-09-26: a window spanning midnight is supported). |
| C132 | SF | `:363-365` | SF-B17. Time-loss after WO staleness: M2-02. |
| C133 | WO | `:346-356` (600 s, `_store_notif_data` skipped so the last `Triggered` stays) | Reachable only with an invalid store; M.SRC_SENS.037 keeps the persisted warning every failing cycle. |
| C134 | SF | `_check_one()` `:205-208` | SF-B17. |
| C135 | WO | `request_signal()` `asy_neopixel_driver.py:145-153` spin; generated REST LED callback uses it `gen/dev:127` | M.SRC_SENS.026 (`led_signal()` refuses while busy), .027 (bounded wait, frame poll), M.SRC_NET.122 (REST uses the refusing path, "LED busy - retry later"). |
| C136 | safe | `neopixel_signal()` `:184-187` | Overlay restored after each signal; WO M.SRC_SENS.028 moves it into a `finally`. |
| C137 | WO | `_serve()` `:696-702` | Reject-when-full is owner (2026-08-12, comment `:698`); M.SRC_NET.127 traces each refusal into `HTTPDropped` (OR137.a). |
| C138 | safe | `:321-322`, `_bounded()` `:245-246`, outer cap `:708` | Every slot is released within 15 s; bounded by construction. |
| C139 | WO | `_bounded_read()` `:256-260`, `awrite()` `:268-270` | M.SRC_NET.127 traces a read-phase reset (`_WRN_HTTP_PEER_RESET`); the write-phase reset is M2-05. |
| C140 | safe | `awrite()` `:271-279` | Header block sent in one write; a cut response never ends mid-header. |
| C141 | refuted | `ext/microdot.py:1410-1419` lets write-phase exceptions reach `_serve()`, which logs them (`:716-726`, wrnno 2/3, errno 1) | Only the four muted errnos (`microdot.py:56-61`, `:689-703`) vanish: M2-05. |
| C142 | WO | `_write_guarded()` `:612-620` | M.SRC_NET.123 (guarded sources), M.WEB.020 renders `{"error":"unavailable"}` as unavailable (A.U23.11). |
| C143 | safe | `_serve_static()` `:656-661`; SPEC A.5 `:337-342` | By design for captive-portal probes; API routes are matched first (`:395-400`). |
| C144 | safe | every generated module passes `static_mount="/html"` with `import frozen_html` (`gen/dev:9`, `:220`) | A missing frozen module fails the import at boot, loudly. |
| C145 | safe | `:363-370`, `_body_as_dict()` `:784-792` | Clean, answered rejects; bounded head after M.SRC_NET.118. |
| C146 | WO | `_put_sensors()` `:425-431` | M.SRC_NET.120 answers "Invalid" for unknown sensors/keys. |
| C147 | WO | `_apply_settings_groups()` `:463-469`; `api_response.py:92-105` | M.SRC_CORE.072 keeps "a failing hook fails its group" deliberately. Residual: hooks raise only on `MemoryError` (`reconnect_wifi()`, `ntp_force_sync()` touch nothing else that raises), a design defect under the memory rule, not a separate gap. |
| T1 | WO | `_get_measurements()` `:404-411` | Staleness visible through each value's `TS`, shown as ages (M.WEB.012); pre-sync `TS` None (M.SRC_CORE.032). SCD30 restamp: SF-A04/B10. |
| T2 | SF | `_get_sensors()` `:413-418`; bus lock serialises | Contention safe (bus lock; settings GET is one-shot per page). Failure shape: SF-B8. |
| T3 | SF | `asy_scd30_driver.py:256-298` | SF-A01 (data-byte NACK answered "Valid"); compare-before-write is U4. |
| T4 | owner | `asy_scd30_driver.py:162-163`, `:278-287`; `@web ContMeas` description `:89` | "the SCD30 driver never starts continuous measurement on its own" (owner, 2026-09-26, OR70.a (3)); the frozen-value restamp after a stop is SF-A04/B10. |
| T5 | owner | `asy_sgp40_driver.py:51-53, 63` | "FRAM SGP40 backup "0 = disabled"" (owner, 2026-07-13, SPEC A.4 `:277-279`). |
| T6 | safe | `asy_sgp40_driver.py:455-462, 508-519` | Explicit dispatch command doing what it names; answered. |
| T7 | SF | `asy_bmp3xx_driver.py:251-269` | SF-A01 / SF-A05 (self-reset revert). |
| T8 | SF | `asy_isl29125_driver.py:798-830` | SF-A01 (config write NACK). |
| T9 | SF | `asy_isl29125_driver.py:1031-1037` | SF-B11 (outcome console-only). |
| T10 | NEW | generated identity group `gen/dev:203` `post_fct=conn.reconnect_wifi`; `api_response.py:94-96` | Wrong real credentials → hotspot/deactivation is owner (A.4; SPEC E.6.4). A non-credential identity PUT from the hotspot ending in DEACTIVATED is M2-01. |
| T11 | safe | `_push_wifi_led()` `:514-519` | Live push; the LED is re-asserted on the next 5 s pass (`_on_sta_connected()` `:466`). |
| T12 | WO | `_VAL_NH` `:65`, generated NTP group `gen/dev:205` | M.SRC_NET.045 shape-checks `NTPHost`, .055 clears `Synced` on a settings change; `NTP_Offset_S` semantics documented (`:73`). |
| T13 | owner | `print_log.py:53-71`; M_SPEC.md:621-627 | "an accepted debug-mode limitation (owner, 2026-09-30)", OR126.a (2). |
| T14 | safe | `cettime()` `:389-406` | Local time only. |
| T15 | WO | `_system_cmd_callback` `gen/dev:97-101` | M.SRC_CORE.010/.011 (one awaited reset path, closed stores, controlled shutdown per OR126.a (3)). |
| T16 | owner | `gen/dev:102-104` | OR52.a (3) (2026-09-26): "Unauthenticated REST writes and `bootloader` are accepted properties". |
| T17 | SF | `gen/dev:105-106` | SF-A11 (one-shot unpause), SF-B4 (aborted pause answered "Valid"). |
| T18 | WO | `asy_notification_service.py:71-78` | Midnight window: M.SRC_SENS.037. |
| T19 | WO | `gen/dev:116-127` → `request_signal()` spins up to the 15 s outer cap | M.SRC_NET.122 + M.SRC_SENS.026 (refused while busy, retry hint), .027 (bounded internal wait). |
| T20 | safe | `_dispatch_notification_pause()` `:545-565` | Range-checked, visible as `PauseTime`; RAM-only noted in SF-B17. |
| T21 | owner | `_put_status()` `:631-639` | Global only (OR70.a (7), 2026-09-26), unauthenticated (OR52.a (3)); WO M.SRC_NET.123 (per-key result), M.WEB.021 confirmation (OR140.a (3)). |
| T22 | WO | `_build_status_pieces()` `:573-603`; `gen/dev:139-149` | Lock-dependent nulls: M.SRC_NET.091/.098. |
| T23 | safe | `_serve_static()` `:649-667` | Content-Length set; WO M.SRC_NET.124 adds `Cache-Control: no-cache` and stream hold. |
| T24 | safe | `_ERROR_SHAPES` `:112-119` registered `:388-389` | Shaped 404/405. |
| T25 | SF | `captive_dns.py:85-140` | By design (answers every query from the AP subnet); queue drops: SF-A08; AAAA/ANY: M.SRC_NET.009. |
| T26 | SF | — (physical) | `Ctrl-C`: SF-A14; the rest are other slices' D-modes. |
| T27 | SF | `asy_fram_driver.py:183-186, 393` (RDID vs `max_size`) | A mismatched chip is refused loudly at setup; the RAM-only consequence is SF-B12. `max_connections`/backlog relation bounded by buildgen (H.7). |
| T28 | owner | `asy_wifi_service.py:50-53` | "accepted permanently as a known limitation (owner, 2026-09-26)" (CLAUDE.md, OR70.a (1)). |
| H14 | safe | `cyw43_ctrl.c:147-215` (20 + 50 ms reset, `cyw43_ll_bus_init`) | Bounded, far below the 8 s watchdog; failure raises → errno 12/13 persisted + `hw_op_failed` (`:370-375`, `:447-457`). Listed as a blocking call in SPEC F.2. |
| H15 | owner | `cyw43_ctrl.c:240-255`; SPEC F.2 `:3664-3672` | "(owner, 2026-09-04, `655e4f9`, paraphrase; confirmed 2026-09-26)": power cycle is the accepted recovery. |
| H16 | safe | `_trigger_sta_connect()` `:451-452`, `_configure_hotspot_ap()` `:385-386` | `pm=0xA11140` re-applied after every `active(True)` on both activation paths; a recreated WLAN always passes one of them. |
| H17 | safe | grep: no `ADC`/GPIO 23-25/29 use in `src/`, generated modules or `devices/*.toml` | Nothing to disturb today. |
| H18 | SF | physical | Peripheral upset after a 3V3 sag: SF-B9/SF-A05 (BMP3XX), ISL BOUTF handled (M.SRC_SENS.082), FRAM WEL/ID probe (M.SRC_CORE.103). |
| H19 | refuted | `main.c:181-196` sets PICOxxxx/"picoW123"; `_configure_hotspot_ap()` `:381-386` calls `active(True)` only after `config(essid=…, password=…)` succeeded in the same `try` | A failed `config()` never activates the AP, so the board defaults are never broadcast. |
| D21 | WO | `toolchain/versions.toml:41-52`; lwIP `tcp.c:1851-1869` (`tcp_alloc` kills TIME-WAIT, LAST_ACK, CLOSING, then lowest prio) | TIME-WAIT cannot starve accepts. UDP budget proved by M.SPEC.040 (`4 + LWIP_MDNS_RESPONDER` = 5, `lwipopts_common.h:70`); TCP send stall: M.SPEC.041 / SUPP_lwip. |
| D22 | safe | `:601-621`; `network_available()` `:780-781`; SPEC F.2 `:3675-3677` | AP `STAT_GOT_IP` is disambiguated by the phase; WO M.SRC_NET.077/.089 name `_STAT_JOINED_NO_IP` and stop at `GOT_IP`. |
| D23 | safe | IP read live (`ifconfig()`), server on `0.0.0.0` (`:323`); mDNS hostname on (`cyw43_config_common.h:115`, `lwipopts_common.h:60`) | Device side unaffected; the current IP is on `/status`; `<hostname>.local` survives the change. |
| D26 | WO | `main.c:141-144`; `_system_status()` `gen/dev:157` `UtcTime` unconditional | M.SRC_CORE.032 `utc_now()` None pre-sync; A.U6.21's `UTCTime` gate (M_GEN.md:229-250). |
| E1 | owner | C62/C66 path | Router absent at boot > ~9 min → DEACTIVATED: the A.4 owner bullet; console-only trace is M2-03. |
| E2 | WO | C63 | M.SRC_NET.088. |
| E3 | owner | `:607-615` | The designed fallback (A.4); warnings persisted once per episode. |
| E4 | NEW | C65 | M2-04. |
| E5 | WO | `asy_dns_client.py:20, 110` (hard-wired fallback) | M.SRC_NET.043/.046 (`DNSFallback` configurable); `NtpSynced` false visible. |
| E6 | SF | `_parse_ntp_reply()` `:243-270` | REG U18 NTP rows; LAN spoofing outside the trusted-LAN model (OR52.a (3)). |
| E7 | owner | H15 | Same owner decision. |
| E8 | safe | ESTABLISHED retries forever `:471-473`; SPEC F.2 real-hardware data (flapping self-heals ~30 s) | RSSI on `/status`. |
| E9 | safe | D23 | — |
| E10 | safe | `devices/*.toml` hostnames all distinct (`SensorStation<Device>`) | A user-chosen collision is a user configuration. |
| E11 | WO | `js/poll-manager.js:36-90` per tab; ceiling 6 | M.SRC_NET.127 (`HTTPDropped`), M.WEB.003 (visibility pause, capped back-off). |
| E12 | owner | page load = `index.html` (CSS and definitions inlined) + one `app.js` (`scripts/build_website.sh:48-83`) | Two static requests; a refusal at the ceiling is the owner's reject-when-full (2026-08-12). |
| E13 | safe | C138 | Bounded by the per-call/outer cap; trusted LAN (OR52.a (3)). |
| E14 | NEW | `ext/microdot.py:689-703` | M2-05 (write-phase reset muted, counted nowhere). |
| E15 | safe | `type_or_range_error()` `config_manager.py:145-187` (broad `except`, range check rejects `inf` from `1e999`) | MicroPython `json` has no `NaN`/`Infinity` tokens. |
| E16 | WO | `js/render.js:256-272` marks Failed, no refetch for settings sections | M.WEB.021 awaits `refreshAfterApply()` after every Apply, failed ones included, so the stored value is shown. Device side: M2-05. |
| E17 | owner | — | OR52.a (3). |
| E18 | SF | C143/T25 | Redirect by design (A.5); burst loss SF-A08; DHCP lease cap SF-A09. |
| E19 | WO | `js/main.js` | M.WEB.025 (build watch reloads), M.SRC_NET.124 (`no-cache`). |

## (B) Findings (NEW and partial)

### M2-01 An identity PUT from the hotspot that cannot connect STA ends in permanent WiFi deactivation, answered "Valid" (class 6, 7)
- **Sites**: generated identity group `build/generated_src/sensortask_dev.py:203` (same line shape in every device,
  e.g. `sensortask_wozi.py:188`): `SettingsGroup(conn, ("SSID", "PW", "Country", "Hostname"), post_fct=conn.reconnect_wifi)`;
  `src/api_response.py:94-96` fires the hook on any "Valid" field; `src/asy_wifi_service.py:538-556`
  (`_handle_reconnect_trigger()` leaves the hotspot), `:441-443` (empty SSID → `connection_failures = conn_fail_to_hotspot`),
  `:479-489` (`hotspot_started_once` latched at `:366` → `_deactivate_wlan_permanently()`).
- **Mode**: hotspot × runtime reconfiguration (pair); first boot (unconfigured unit).
- **Today**: a unit in hotspot mode whose SSID is still empty (factory, or after "Reset to defaults", OR117.a (1)) gets
  `PUT /networking {"Hostname": "x"}` (or `Country`): answered "Valid", 5 s later it leaves the AP, the first STA tick
  finds `ssid == ""`, the failure counter is already at its limit and the latch is set, so it deactivates the radio
  within about 10 s. Only a power cycle recovers. With a configured SSID but the router unreachable (the reason the
  unit is in hotspot mode), the same PUT leaves the AP and deactivates after one failed STA streak. Legacy did the same
  (`async_connect.py:194-215`, `:292-294`), but there it was reachable only through Hostname/Country. WO A.U18.38
  (M.SRC_NET.073; `codegen.py:607`) adds `HotspotPW` to this same group, so changing the known-weak default hotspot
  password from the hotspot, the natural place to do it, takes this path too; its planned L1 test asserts only "the next
  hotspot start configures it".
- **Layer below**: nothing fails below; the PUT's "Valid" is truthful about storage, and nothing reports the state the
  unit then enters (unreachable; LED pattern only after M.SRC_NET.100).
- **Effect**: all six devices (no bus involved).
- **Coverage**: owner bullet A.4 `:279-283` (owner, 2026-07-13) covers "a second STA failure streak"; SPEC E.6.4 records
  that a failed real-credential PUT from the hotspot lands in DEACTIVATED. An empty SSID is no STA attempt at all, and a
  Hostname/Country/HotspotPW-only change is no credential change; per CLAUDE.md this is a fine-tuning question, not a
  conflict. No WO change touches it.
- **Owning unit**: U18 (WiFi), with U20 for the generated group and U36 for A.4/E.6.4.
- **Smallest fix** (OR149): in `_attempt_sta_connect()`'s empty-SSID branch, set `self._conn_phase = _PHASE_HOTSPOT`
  (and `connection_failures = 0`) instead of filling the failure counter. "Not configured" then routes to the hotspot
  whatever the latch says. This is one line on existing state, and it also closes C69 (an unattended unconfigured unit
  deactivating after one hotspot window). The non-empty case changes behaviour under an owner decision, so it goes to
  BACKLOG's owner-question list. Decision: "Does a non-credential identity PUT made in hotspot mode leave the AP?"
  (a) As today: it leaves, and an unreachable router means DEACTIVATED until a power cycle, on every device.
  (b) It re-applies the AP and stays, and only an SSID/PW change leaves. No unit then goes dark from a rename or
  password change, and a Hostname change renames the AP's SSID in place.

### M2-02 After WO M.SRC_NET.057, a unit without network stops all LED alerts 3× NTPInterval after its last sync, invisibly (class 7, 4; partial WO)
- **Sites**: `src/asy_ntp_client.py:387-388` (`cettime()` returns `None` unless `Synced`); M.SRC_NET.057 (staleness on
  `_sync_age`, flips `Synced` after `_NTP_ASYNC_INTERV × NTPInterval`, default 36 h); M.SRC_NET.053 keeps the gate;
  `src/asy_notification_service.py:363-365` (no local time → no checks); `fram_ntp_callback=ntp.ntp_issynced`
  (`gen/dev:183`, FRAM backup ages become `None`).
- **Mode**: degraded running (WiFi missing: DEACTIVATED, a hotspot held by a client (M2-04), a router down in the
  ESTABLISHED retry loop) × time.
- **Today (HEAD)**: staleness is unreachable (C83), so alerts keep running on the free-running RTC. After the WO: 36 h
  after the last sync, `Synced` goes false, `cettime()` answers `None` and the monitor evaluates nothing. Timestamps
  keep working, because `utc_now()`'s validity is one-way (M.SRC_CORE.032). The RTC is still accurate to seconds
  (crystal-derived; about 2-3 s per day at 30 ppm). With no network the LED is the unit's only output, so "alerts
  stopped" reads as "air is fine". SF-B17's reason field is only reachable over the network.
- **Effect**: all six devices; SGP40 restore/backup timestamps on every device change path the same way (M3's slice).
- **Coverage**: M.SRC_NET.057 (agent, 2026-09-27; owner-reviewed, 2026-10-02) states that consumers handle `False`, but
  does not name this consequence. SF-B17 covers visibility over REST only.
- **Owning unit**: U18 (NTP), U22 (LED re-check).
- **Smallest fix**: let the consumers that need a usable wall clock test the existing one-way flag. `cettime()` gates on
  `utc_now() is not None` instead of `ntp_issynced()`, and `Synced` stays the freshness status on `/status`. This tests a
  bool that is already held, with no new state. Because the owner reviewed the staleness, it is raised as a fine-tuning
  question with two options. (a) Keep the gate, and alerts stop silently 36 h into any network loss on every device.
  (b) Gate on "clock set this boot", and alerts continue on the RTC. The second is recommended.

### M2-03 STA→hotspot fallback, permanent deactivation and a connect attempt that never reaches a verdict leave no persisted trace (class 7, 4)
- **Sites**: `src/asy_wifi_service.py:489` (`pr.one("Permanently no WLAN connection - activating hotspot!")`), `:492`
  (`pr.one(... Deactivating WLAN!)`), `:482` (failure counter `pr.evt`), `:592-621` (`_poll_sta_connect_status()`
  exits after 10 polls in IDLE/CONNECTING/NOIP with no entry); M.SRC_NET.088/.089 keep all three.
- **Mode**: WiFi (a DHCP that never answers: status stays `CYW43_LINK_NOIP`, `_STAT_OBTAINING_IP`; slow association),
  degraded running, boot loop of the STA streak.
- **Today**: a unit that fell back to the hotspot and then deactivated is recovered by a power cycle. Its FRAM WIFI
  history then holds only the connect verdicts that happened to be terminal (wrnno 4-7). For a NOIP or timeout streak it
  holds nothing at all, which goes against CLAUDE.md's "read the FRAM logs first" diagnostic rule. Live, `/status` shows
  `Mode` "AP", but DEACTIVATED shows `Mode` "STA", `Connected` false, and it is unreachable anyway.
- **Effect**: all six devices.
- **Owning unit**: U18 (codes via the U2 catalog).
- **Smallest fix**: three `wrn_s` calls on existing paths and no new state: (1) the hotspot transition, (2) the
  deactivation, (3) a `for … else:` on the poll loop with the last status. The central newest-entry rule (A.U3.02) keeps
  repeats to one slot.

### M2-04 A station associated to the hotspot holds the AP indefinitely, and the LED shows it exactly like a working STA link (class 7, 6)
- **Sites**: `src/asy_wifi_service.py:575-581`, `:396-404` (`_hotspot_client_connected()` stops the timer, `_led_on()`
  steady), `:461-466` (`_on_sta_connected()` → `_led_on()` steady); legacy identical (`async_connect.py:266-274`);
  M.SRC_NET.087 keeps `_led_on()`.
- **Mode**: hotspot and captive mode; a phone that once joined the hotspot auto-joins it again and stays.
- **Today**: while any station is associated, the unit never retries STA and is off the home LAN. That is legacy and
  field behaviour, so not changed here. An observer sees the same steady LED as "connected to the home Wi-Fi", so a
  parked phone is indistinguishable from normal operation. An associated station without a DHCP lease (SF-A09) holds the
  AP the same way.
- **Effect**: all six devices.
- **Coverage**: no WO change; no owner decision names the client-held case.
- **Owning unit**: U18 (U22 for the LED re-check).
- **Smallest fix** (visibility, behaviour unchanged): a distinct LED pattern for "hotspot, client connected" through
  M.SRC_NET.092's existing `_flash_led(on_ms, off_ms)` (one more constant pair; `_hotspot_client_connected()` starts
  that pattern instead of `_led_on()`). Whether a client may hold the AP indefinitely goes to the owner-question list:
  (a) keep, the unit stays off-LAN as long as any phone stays associated; (b) bound it to N × `hotspot_time`. Under (b),
  leaving the AP while the router is still down then meets the deactivation rule (C66), on every device.

### M2-05 A peer reset during the response write is muted by Microdot and counted nowhere (class 7, low)
- **Sites**: `ext/microdot.py:56-61, 689-703` (ECONNRESET/EPIPE during `Response.write()` → `pass`); pinned
  `extmod/modlwip.c:497-507` (`_lwip_tcp_error` sets `state = ERR_RST`), `:743-750` (next write raises ECONNRESET);
  `src/asy_webserver_service.py:268-279` (`awrite()` lets it pass through), `:256-260` (`peer_gone` set only on reads);
  M.SRC_NET.127 traces only `peer_gone`.
- **Mode**: REST clients: a client that abandons a slow response (the page's 15 s abort equals the 15 s outer cap; tab
  closed; phone sleeps) and a PUT the device applied whose answer the client never got (E16).
- **Effect**: all six devices: `HTTPDropped` (OR137.a) under-reports the drops that matter most to E16. The client side
  is covered by M.WEB.021.
- **Owning unit**: U19.
- **Smallest fix**: in `_TimeoutStreamProxy.awrite()`, `except OSError: self._peer_gone[0] = True; raise`, the same as
  `_bounded_read()`. M.SRC_NET.127's existing `if peer_gone[0]` trace then counts it. No new state; the trace wording
  becomes "before or during its response".

### M2-06 Settings sections keep a stale baseline while the page is open, and a toggle/enum equal to it is dropped from the PUT (class 4, low; found in walk C)
- **Sites**: `js/render.js:377-383` (non-live sections fetch once; M.WEB.020 keeps `stopAfterSuccess` for them),
  `:77-84` and `:119-121` (`collectGroupBody()` omits a toggle/enum equal to its baseline; M.WEB.018 keeps the rule);
  M.WEB.025's watch reads only `/status` and `/system`'s `build`.
- **Mode**: REST clients (two browsers; a page left open across another client's change, a "Reset to defaults" or a
  reboot) × runtime reconfiguration.
- **Today**: browser A turns `LEDWifiOn` off; browser B still shows On as its current value. B wants it On and presses
  Apply: the toggle equals B's stale baseline, so nothing is sent ("Nothing to submit"), while the device stays Off and
  B's caption still says On.
- **Effect**: the website on all six devices.
- **Owning unit**: U23.
- **Smallest fix**: an ordering change. Apply awaits the section's existing `refreshAfterApply()` (M.WEB.020) before
  `collectGroupBody()` reads the baselines. One GET per Apply, no new state. The in-place update leaves typed inputs
  untouched.

## (C) Scenario walks

**WiFi.** Boot → `conn.setup()` → `wlan_connect()` resets state; after a soft reset with the radio still active,
`reconn_wifi` forces a clean reconnect (`:311`). The boot `ntp_force_sync()` is consumed while STA is not up yet; it is
skipped without backoff and the next due tick retries (C86). In SEEKING: a connect attempt (≤5 s poll under the lock),
then a verdict or a silent timeout (M2-03), five failures → HOTSPOT (console only). After the first success
(ESTABLISHED), a link loss gets 60 s retries forever (WO .088 moves the wait out of the lock). Changed router
credentials therefore need a power cycle, owner-accepted (A.4). The NTP lock hold (≤6.5 s, C85) and the uptime/getter
effects (C79/C80) are WO. The `isconnected()` false positive is owner. Nothing beyond M2-01/M2-03 found.

**Hotspot and captive mode.** Entry → mode switch, AP configured only when inactive (H19 refuted), DNS task guarded,
captive redirect for unknown static paths, NTP skipped. Stations polled every 5 s: a failed query reads as "no client"
(SF-B6), a client holds the AP indefinitely and looks like STA (M2-04). Burst DNS loss is SF-A08; the lease cap is
SF-A09. Leaving: the PERIODIC timer → reconnect → STA streak → DEACTIVATED on a second failure (owner) — or, with an
identity PUT made from the hotspot, without any possible STA attempt (M2-01). RSSI raises in AP mode every `/status`
poll (console; WO .091). The pair "PUT during hotspot" is M2-01. One more pair, "hotspot timer fires while a client is
joining": a station arriving between two 5 s polls can lose the AP at the 8-minute mark. The user rejoins after the next
streak only if no deactivation follows (owner rule), so this is no separate finding.

**Time.** RTC at 2021 → TS plausible-wrong until sync (WO `utc_now()`), first sync steps forward about 5 years. Every
interval uses ticks; FRAM backup ages across a step are handled by the WO (negative age expires). `NTP_Offset_S` changes
step the clock by design. At HEAD, lowering `NTP_Interv_H` makes the `3×` branch fire once (`Synced` blips false for one
retry step); WO .057 removes that. WO .057's reachable staleness interacts with `cettime()`'s gate → M2-02. The
`HTTPDropped` window advances from `SysUptime`, so it is immune to steps (OR137.a). The `TickSeconds` users are read at
least every 10 s while relevant. No `ticks_diff` horizon is exceeded in this slice.

**REST clients.** Hammering: the ceiling of 6 refuses without an answer (owner) and WO counts it; lwIP reclaims
TIME-WAIT pcbs, so accepts never starve on them (D21). A slow client is bounded at 15 s; the zero-window send stall is
M.SPEC.041. Malformed or oversized input gets a clean answer. A client timeout on an applied PUT: the client is fixed by
M.WEB.021, the device side is M2-05. A page left open across a reboot: the banner self-heals and the build watch reloads
(M.WEB.025). Two browsers: M2-06. Captive probes: redirect by design.

**Runtime reconfiguration.** A `PUT /networking` during an NTP sync only stages config and sets flags. The NTP group's
`ntp_force_sync()` during a running attempt re-triggers it once, and the attempt then uses the new host. Turning
`LEDWifiOn` off mid-flash silences the flash task (`self.led = None`); turning it on is re-asserted within 5 s. A
notification threshold change mid-cycle applies to the remaining signals of that cycle (harmless). A post-hook failure
is reachable only through `MemoryError` (C147). The identity hook in hotspot mode is M2-01.

**Outputs.** One pixel carries the WiFi overlay, notification ramps and the REST `lightCmdLED`. The overlay is restored
after every ramp (WO moves it into a `finally`). At HEAD the REST command spins in `request_signal()` up to the outer cap;
WO .122/.026 refuse it while busy with a retry hint. A dropped internal flash still reports `Triggered` (SF-B2).
`PauseTime` is lost across a reboot (SF-B17 note). Across a reboot the pixel starts black and the WiFi state re-asserts
the overlay. LED states that look alike: STA-connected vs hotspot-with-client (M2-04). The deactivated state gets its own
pattern by WO .100.

**Degraded running (WiFi or NTP missing).** With no WiFi, sensors run, FRAM logs, NTP is skipped, and after the WO
`Synced` goes stale at 36 h, so alerts stop (M2-02) and SGP40 backups lose timestamps (M3's slice). With no NTP (DNS
blocked, bad host), `Synced` never comes, TS is `None` (WO) and alerts never run (SF-B17); the backoff caps at 600 s
(owner, C.7.2). DEACTIVATED is reached and stays without a persisted cause (M2-03).

## (D) Counts per verdict (108 IDs)

| verdict | count | IDs |
|---|---|---|
| WO | 36 | C63, C64, C70, C72, C73, C76, C79, C80, C81, C82, C83, C85, C92, C93, C129, C131, C133, C135, C137, C139, C142, C146, C147, T1, T12, T15, T18, T19, T22, D21, D26, E2, E5, E11, E16, E19 |
| safe | 31 | C71, C74, C77, C78, C84, C86, C88, C90, C130, C136, C138, C140, C143, C144, C145, T6, T11, T14, T20, T23, T24, H14, H16, H17, D22, D23, E8, E9, E10, E13, E15 |
| owner | 17 | C62, C66, C67, C68, C69, T4, T5, T13, T16, T21, T28, H15, E1, E3, E7, E12, E17 |
| SF | 17 | C87, C89, C91, C132, C134, T2, T3, T7, T8, T9, T17, T25, T26, T27, H18, E6, E18 |
| NEW | 5 | C65, C75, T10, E4, E14 (findings M2-01, M2-03, M2-04, M2-05; M2-02 and M2-06 come from the walks) |
| refuted | 2 | C141, H19 |
