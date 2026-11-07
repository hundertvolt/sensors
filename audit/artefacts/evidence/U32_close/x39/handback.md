VERDICT X39 (U32 step 39, M.PROC.021) at 889cb5e: 15 functions held, 2 fixed, 2 recorded, 0 unsettled. Every legacy key has a place: 0 keys without one, 0 unsettled findings, 7 settled observations.
Generated modules read: S/wt-u32int/build/generated_src/sensortask_*.py (_BUILD_DATE 2026-10-21T10:59:28Z, 31 s after the 889cb5e commit time). In arzi, grkizi, klkizi and schlafzi the status sources are byte-identical to wozi's, with sensors=(scd30, sgp40), so no BMP3XX. That matches legacy arzi/neu (= wozi minus BMP388). Paths below are relative to S/wt-u32int; "gen" = build/generated_src/sensortask_wozi.py, "L" = legacy/firmware.

FUNCTION TABLE (module | function | verdict | 889cb5e site | legacy site)
BMP3xx | pressure/temp minus offset | held | src/asy_bmp3xx_driver.py:339-340 | L/python/IndividualDrivers/asy_bmp3xx_driver.py:172-173
BMP3xx | sea-level from SeaLevelOffset + MeanAtmTemp | held | asy_bmp3xx_driver.py:345, src/math_helpers.py:137-148 | asy_bmp3xx_driver.py:174, L/python/CommonDrivers/math_helpers.py:33-36
BMP3xx | bounded forced-mode wait | held (now bounded; legacy loop had no bound) | asy_bmp3xx_driver.py:78, :516, :608-622 | asy_bmp3xx_driver.py:276-277
BMP3xx | fractional trigger seconds | recorded (adaptation) in SPEC M.4 (SPECIFICATION.md:11399-11401) | asy_bmp3xx_driver.py:102, :450-456 (checked_int) | asy_bmp3xx_driver.py:91-92 int(); REST int-only L/modules/sensortask-wozi.py:367
NTP | syncs only with an STA IP | held | src/asy_wifi_service.py:985-986; src/asy_ntp_client.py:410-416 | L/python/CommonDrivers/async_connect.py:377
NTP | bounded fetch | held | asy_ntp_client.py:261, :264 (fetch_timeout_ms = gen:43, 5000) | async_connect.py:14, :399
NTP | three retries when synced | held | asy_ntp_client.py:62, :272-294 | async_connect.py:15-16, :413-421
NTP | 12 h default | held | asy_ntp_client.py:113, :364 | sensortask-wozi.py:21; async_connect.py:446-447
NTP | offset applied before the clock is set | held | asy_ntp_client.py:321, :331 | async_connect.py:426, :429
NTP | last sync as an age, with an unsynced marker | held (marker -1 is now None) | asy_ntp_client.py:449-456, :519-521 | async_connect.py:484-501, :137-138
NTP | resync after a settings change | held | buildgen/validate.py:121 -> gen:155 | sensortask-wozi.py:219
NTP | Synced cleared on a settings change | fixed by A.U18.21 | asy_ntp_client.py:551-554 (owner, 2026-09-29); SPEC C.7.2 :3575-3576 | async_connect.py:129-131
NTP | GMT/DST offsets | recorded (adaptation, no loss): read on every cettime() call, no hook | asy_ntp_client.py:523-546 (:530), :131-132; validate.py:124; SPEC A.8 :1049-1052 (hooks listed only for /networking) | sensortask-wozi.py:217-219; async_connect.py:464-482
NeoPixel | REST command refused while a command is pending | fixed by A.U9.02/A.U9.03 | src/asy_neopixel_driver.py:158-167; src/asy_webserver_service.py:739-759, :822-827; SPEC A.4 :363 (owner, 2026-09-29), A.8 :1081 (owner, 2026-10-02) | L/python/IndividualDrivers/neopixel_signal.py:67-73; sensortask-wozi.py:415-416
NeoPixel | ramp floor 0.1 s | held | asy_neopixel_driver.py:27, :61-62 | neopixel_signal.py:128
NeoPixel | overlay restored after a signal | held | asy_neopixel_driver.py:104, :125-129 | neopixel_signal.py:150
NeoPixel | Wi-Fi LED | held | asy_neopixel_driver.py:169-175, :201-203; asy_wifi_service.py:534-553, :974-983 | neopixel_signal.py:78-88; async_connect.py:112-121
NeoPixel | colours: CO2 red, VOC green, humidity blue | held | buildgen/signals.py:23-25 -> gen:144; src/asy_notification_service.py:329-331 | neopixel_signal.py:176, :181, :186
NeoPixel | interval measured from loop start | held | asy_notification_service.py:255, :298, :300-303 | neopixel_signal.py:154, :188-192

KEY TRACE (legacy key(s) | refactor place | note). Legacy = L/modules/sensortask-wozi.py:146-537; WIP = 8ec6fc1^:improved-quality/sensortask-wozi.py.
/net/status IPv4, Subnet, Gateway, DNS, Rssi | /status networking IPv4, Subnet, Gateway, DNS, RSSI (gen:102) | Rssi is now spelled RSSI (OR58.a)
/net/config Country, Hostname, SSID, PW (masked) | GET /networking (gen:153); PW masked at asy_wifi_service.py:371
/net/cmd setNetwork Hostname, Country, SSID, PW | PUT /networking, post_fct=conn.reconnect_wifi (gen:153; validate.py:119)
/time/status System.Synced (legacy On/Off; WIP bool) | /status networking NTPSynced (gen:103)
/time/status System.Unix (legacy + WIP) | /status system UnixTime = utc_now() (gen:116; A.U23.22) | null until the first sync (SPEC:985-986)
/time/status UTC.Year..Sec | /status system UTCTime (gen:66-69, :116) | MDay/Minute/Second, plus Weekday/Yearday
/time/status Local.Year..Sec | /status system LocalTime (gen:108, :116)
/time/config + /time/cmd NTP_Host, NTP_Offset_S, NTP_Interv_H | GET/PUT /networking NTPHost, NTPOffset, NTPInterval; ntp_force_sync hook (gen:155)
/time/config + /time/cmd GMTOffset, DSTOffset | GET/PUT /system (gen:160), no hook
/sensors/status SCD30 CO2, Temp, Hum, WetBulb, DewPoint, TS | /measurements SCD30, same keys (asy_scd30_driver.py:158) | "None" strings are now null
/sensors/status SGP40 VOC, Raw, TS | /measurements SGP40 (asy_sgp40_driver.py:120)
/sensors/status BMP388 Pres, Temp, SLPres, TS | /measurements BMP3XX (asy_bmp3xx_driver.py:131) | wozi only
/sensors/config + setSCD TempOffs, MeasInt, AmbPres, Altitude, ForceCalRef, SelfCal | GET/PUT /sensors SCD30 TempOffset, MeasInterval, AmbPres, Altitude, ForceCalRef, SelfCal (asy_scd30_driver.py:112-117)
setSCD ContMeas | PUT /sensors SCD30 ContMeas (asy_scd30_driver.py:108, :266-267)
SGP40 SGPBackupPeriod, SGPBackupMaxAge, SGPWaitTimeNTP | GET/PUT /sensors SGP40 BackupPeriod, BackupMaxAge, WaitTimeNTP (asy_sgp40_driver.py:98-100)
setSGP SGPResetVOC | PUT /sensors SGP40 ResetVOC, dispatch-only (asy_sgp40_driver.py:104, :208, :219)
BMP388 BMPSampleInterv, BMPPressOvers, BMPTempOvers, BMPFiltCoeff, BMPPressOffset, BMPTempOffset, BMPSeaLevelOffs, BMPMeanAtmTemp | GET/PUT /sensors BMP3XX SampleInterval, PresOvers, TempOvers, FiltCoeff, PresOffset, TempOffset, SeaLevelOffset, MeanAtmTemp (asy_bmp3xx_driver.py:102-113, :385-390)
/led/status pauseTime | /status notification PauseTime (gen:121)
/led/config + setAutoLED LedAutoOn, LedAutoOnH/M, LedAutoOffH/M, LedAutoFlashBri, LedAutoInterv, LedAutoFlashDur | GET/PUT /notification AutoOn, OnH/OnM, OffH/OffM, FlashBri, FlashInterval, FlashDur (asy_notification_service.py:99-106; gen:162)
LedWarnCO2, LedWarnVOC, LedWarnHum | GET/PUT /notification WarnCO2, WarnVOC, WarnHum (gen:48-50, :144)
LedWifiOn (/led/config, setWiFiLED) | GET/PUT /networking LEDWifiOn (gen:154; asy_wifi_service.py:73)
lightCmdLED r, g, b, t | PUT /notification LightCmdLED {R, G, B, T} (asy_webserver_service.py:136-141, :817-827)
pauseAutoLED pauseTime | PUT /notification PauseTime (asy_webserver_service.py:131, :761-776)
envelope codes busyLED / invalidLED / pauseLED / sysCmd | per-key Failed + descr "LED busy - retry later" / Invalid (asy_webserver_service.py:142, :757)
Sys_Uptime, Boot_Signature | /status system SysUptime, BootSignature (gen:111)
Wifi_Uptime | /status networking WifiUptime (gen:101)
NTP_LastSync | /status networking NTPLastSyncAge (+ NTPLastSync = sync TS) (gen:103)
SCD30_ErrCnt, SGP40_ErrCnt, BMP388_ErrCnt; WIP FRAM_ErrCnt, NOTIFY_ErrCnt | /status errcount.<SCD30/SGP40/BMP3XX/FRAM/NOTIFY>.counter (gen:192-196; asy_webserver_service.py:712-722, :1056-1067)
SGP40_Backup_TS, SGP40_Restore_TS | /status sensors.SGP40.BackupTS/RestoreTS (gen:93-95, :170) | null/0 replace "None"/"No TS" (SPEC:999-1000, owner, 2026-09-29)
SGP40_MemErr_Critical, _Uncritical, _Last | recorded equivalent: errcount.FRAM history (asy_fram_manager.py:40-60 codes) + SGP40 storage codes (asy_sgp40_driver.py:56-62) | legacy source L/python/IndividualDrivers/asy_fram_manager.py:246-249
Error_Status | recorded equivalent: errcount roll-up "N modules with errors / warnings" (js/templates.js:530-555; packet's :234-262 has drifted)
Task_ErrCnt | recorded equivalent: errcount.SYSTEM.counter (a superset; task ends are codes 42/43/44 at asy_system_service.py:51-53, :306-311)
Task_LastErr (legacy + WIP) | /status system LastTaskEnd (gen:115; asy_system_service.py:298-302, :646-650; A.U32.06; SPEC:978-983, owner, 2026-09-30) | the wrnno = n + 1 trace is gone from asy_system_service.py
/system/cmd systemCmd content reboot / bootloader / mempause | PUT /system SystemCmd (asy_webserver_service.py:122, :874-895; gen:71-82, mempause 300 s at gen:77)
static pages /, /index.html, /nettimeconfig.html, /sensorconfig.html, /systemledconfig.html, /style.css, /functions.js | one static index.html (CSS and definitions inlined) + js/app.js (asy_webserver_service.py:619-620; SPEC H.7 :7545-7549) | paths free (OR58.a)
/favicon.ico | icon inlined as a data: URI in index.html (scripts/_stage_website.py:25, :331-332; SPEC :7547, :7932; A.U23.39)

FINDINGS: none unsettled. Seven settled observations, none needing action:
O1 A PUT of GMTOffset/DSTOffset alone no longer resyncs or clears Synced; legacy's shared /time/cmd hook did both. Not a loss, since local time uses the new offset at once. Settled by A.U32.04's own "adaptation, no loss" and the current-state hook list in SPEC A.8 (:1049-1052). SPEC has no sentence naming the legacy difference; per CLAUDE.md, docs hold current state, not history.
O2 cettime() is now gated on "clock set this boot", where legacy gated on Synced, so alerts keep running through an NTP outage. Settled by SPEC A.4 :385-387 (agent, 2026-10-06) and SPEC Part F :6036-6037.
O3 While unsynced, legacy retried every 10 s tick. The refactor backs off from 10 s up to 600 s, never gives up, and keeps 3 x 15 s retries when synced. Settled by SPEC C.7.2 :3560-3570 (owner, 2026-09-24 on not ending the task).
O4 BMP3xx: SLPres is now null when PresOffset moves the pressure outside 300-1250 hPa (DERIVED_DOMAIN warning), and MeanAtmTemp's floor is now -40 (legacy REST allowed -50). Settled by SPEC M.4 :11397-11400.
O5 UTCTime and UnixTime are null until the first sync, where legacy always served the raw RTC values. Settled by SPEC A.8 :984-986 and Part F :6034-6037.
O6 GET /favicon.ico now answers 404: the frozen site holds only index.html.gz and js/app.js.gz. The icon itself still works through the inlined data: URI. Settled by OR58.a (paths free, functions kept; owner, 2026-09-26, quoted in A.U32.05) and SPEC H.7.
O7 Stale packet pointer: the colour mapping is in buildgen/signals.py:23-25 (WARN_SIGNALS; SPEC :7831-7832), not in validate as M.PROC.021 says. Read by symbol, so not a finding.
Nothing was written to the tree. Scratch: S/u32/x39/scratch/wip.py holds the extracted work-in-progress file.
