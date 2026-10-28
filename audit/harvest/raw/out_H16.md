# Harvest H16 — legacy deployed tree: python/, modules/, html_raw/, build-*.sh (snapshot 2a88cc8)

All items are area PAR (parity oracle; the legacy tree is reference-only, nothing here is a to-do). Kind PAR-facts are filed under the closest COMMON.md kind (mostly LIMIT/ASSUME/SETTLED/INVAR/PLATFORM/WORKAROUND/MIRROR/DRIFT). `src/` counterparts are named in `related`.

## python/CommonDrivers/api_helpers.py
- INVAR | python/CommonDrivers/api_helpers.py:160-183 | "# 0: Success, no error ... # 8: LED is busy ... # 10: Invalid or unknown system command" | Legacy wire error-code catalogue 0-10 (6 unknown, 7 invalid LED cmd, 8 LED busy, 9 invalid pause time, 10 invalid system cmd); src `api_response._STANDARD_CODES` keeps 0-5 and adds 100 "Generic command error", codes 6-10 gone | area: PAR | related: PAR.T11, REST.S09
- DRIFT | python/CommonDrivers/api_helpers.py:129,136 | "Invalid JSON Request" / okDescr="Command exectuted" | Legacy wire `descr` strings differ from src (`"Invalid JSON request"`, `"Command executed"`, src/api_response.py:40-41) — a client matching on descr text sees a change (low) | area: PAR | related: PAR.T11
- SETTLED | python/CommonDrivers/api_helpers.py:33,42-45 | "an empty input (\"\") will be considered as valid value for \"don't change\"." | Legacy PUT semantics: `""` for any key means "Unchanged" (no write); refactor gives `""` real meaning for some keys (e.g. `PW` = open network) | area: PAR | related: NET.S17, PAR.S06
- LIMIT | python/CommonDrivers/api_helpers.py:38-41 | "json_validity[json_key] = \"Invalid\"" (key not in request) | Legacy per-key validation marks every absent key "Invalid" (non-sparse PUT; clients sent every field), contrast with the refactor's sparse PUT | area: PAR | related: PAR.S06
- INVAR | python/CommonDrivers/api_helpers.py:90-99 | "if state_val == \"On\": val = True elif state_val == \"Off\"" | Legacy wire booleans are the strings "On"/"Off" (`toSwitch()` :119-120 on GET); refactor uses native JSON bool | area: PAR | covered-by: PAR.S06
- SETTLED | python/CommonDrivers/api_helpers.py:102-114 | "if val == dst_json_value[json_key]: ... \"Unchanged\"" | Legacy skipped both the flash save and the setter when the value equalled the stored one; only a changed storage key set `any_set` (flash write); command-only keys never trigger a save | area: PAR | related: PAR.S02, SENS.T07
- LIMIT | python/CommonDrivers/api_helpers.py:66-75 | "except ValueError:" | int/float coercion catches only ValueError: a JSON `null`/list/object raises TypeError out of the handler (Microdot 500), and `int(1.9)` silently truncates to 1 (low) | area: PAR | related: PAR.T11
- LIMIT | python/CommonDrivers/api_helpers.py:47-53 | "val = str(json_in[json_key])" | Any JSON value (number, bool) is accepted for a "str" field via `str()`; the ValueError branch is unreachable (low) | area: PAR | related: NET.T07
- SETTLED | python/CommonDrivers/api_helpers.py:185-221 | "in case of sensor update errors, try to load values from sensor ... If this also fails, take default value." | Legacy sensor-setter fallback chain: setter fails → "Failed", then read back from sensor, then from config.json, then `default`; `force` re-applies even unchanged values (SCD30 AmbPres) | area: PAR | related: PAR.S02, SENS.T07
- INVAR | python/CommonDrivers/api_helpers.py:146-149 | "dst_json_value.pop(key, None)  # ignore for saving, but keep validity result" | Command-only keys are stripped before `write_config`, so they never persist | area: PAR | related: PAR.T01
- LIMIT | python/CommonDrivers/api_helpers.py:124-127 | "except: req_json = None" | Any body-parse failure (bare except) maps to code 1 | area: PAR | related: PAR.T11

## python/CommonDrivers/asy_udp_socket.py
- ASSUME | python/CommonDrivers/asy_udp_socket.py:1-5 | "no formal LICENSE in that repo, but treated as the author's own public offer of the code" | Attribution/licence assumption for the karfas AsyUDPClient-derived shape, inherited by `src/asy_udp_socket.py` | area: PAR | related: LIC
- LIMIT | python/CommonDrivers/asy_udp_socket.py:13,29-42 | "conn_tries=1" / "except Exception as e: tries += 1; await asyncio.sleep(0.5)" | Legacy connect/bind is attempted once by default, errors swallowed silently; since `self.sock` stays non-None, a failed bind is never retried and `ready()` returns False forever | area: PAR | related: NET (src/asy_udp_socket.py retry/degrade)
- LIMIT | python/CommonDrivers/asy_udp_socket.py:44-56 | "if (timeout_ms > 0) and ... await asyncio.sleep(wait_time_ms)" | `ready()` spins on `ipoll(0)` with `sleep(0)` (busy-yield) and `timeout_ms<=0` waits forever | area: PAR | related: PERF
- LIMIT | python/CommonDrivers/asy_udp_socket.py:73-77 | "for _ in range(tries): ... return await self.recvfrom(" | `write_and_recvfrom(tries=N)` returns after the first iteration: retries never happen (low) | area: PAR | related: NET
- PLATFORM | python/CommonDrivers/asy_udp_socket.py:24 | "SO_REUSEADDR, 1" | Legacy sets SO_REUSEADDR on every UDP socket (the refactor's captive DNS relies on the same) | area: PAR | related: NET

## python/CommonDrivers/captive_dns.py
- SETTLED | python/CommonDrivers/captive_dns.py:1-5 | "SPDX-FileCopyrightText: Copyright 2019 p-doyle ... see src/LICENSE-captive_dns" | Apache-2.0 derivative attribution; the referenced `src/LICENSE-captive_dns` exists at the snapshot | area: PAR | related: LIC
- LIMIT | python/CommonDrivers/captive_dns.py:13,20,35-37 | "except Exception as e: ... await asyncio.sleep(3)" | Legacy captive DNS binds 0.0.0.0:53 once; on a failed bind `recvfrom` returns (None, None), `DNSQuery(None)` raises and the loop sleeps 3 s forever (silent dead DNS) | area: PAR | related: NET (src captive_dns/asy_udp_socket degrade)
- INVAR | python/CommonDrivers/captive_dns.py:47-55,59-67 | "tipo = (data[2] >> 3) & 15  # Opcode bits" / "if self.domain:" | Only opcode-0 queries are answered; every standard query of any QTYPE gets one A record pointing at the AP IP, ANCOUNT=QDCOUNT, flags 0x8180, TTL 0x3C (60 s) | area: PAR | related: NET
- LIMIT | python/CommonDrivers/captive_dns.py:62 | "packet += self.data[12:]  # Original Domain Name Question" | The whole query tail (incl. any EDNS/additional records) is echoed before the answer while ARCOUNT is zeroed — malformed reply for EDNS queries (low) | area: PAR | related: NET
- LIMIT | python/CommonDrivers/captive_dns.py:20 | "await self.udps.recvfrom(4096)" | Receive buffer 4096 bytes per query (heap allocation per request) | area: PAR | related: MEM

## python/CommonDrivers/math_helpers.py
- INVAR | python/CommonDrivers/math_helpers.py:7 | "if (-20.0 <= temperature <= 50.0) and (0.5 <= humidity <= 99.0):" | Legacy wet-bulb (Stull) validity window −20..50 °C, 0.5..99 %RH, else None | area: PAR | related: ALGO (src/math_helpers.py:50)
- INVAR | python/CommonDrivers/math_helpers.py:21-28 | "(-40.0 <= temperature <= 50.0) and (0.1 <= humidity <= 100.0)" | Legacy dew point window and Magnus coefficient pairs (243.04/17.625 water, 272.62/22.46 ice) | area: PAR | related: ALGO (src/math_helpers.py:66-76)
- DRIFT | python/CommonDrivers/math_helpers.py:33-37 | "def altitude_baro(p0, dh, tmean): return p0 * math.exp(" | Named altitude but returns a pressure (barometric formula) — legacy-identical naming carried into src | area: PAR | covered-by: ALGO.S03
- ASSUME | python/CommonDrivers/math_helpers.py:43-49 | "a = 7.6 b = 240.7" | Below 0 °C uses 7.6/240.7 (supercooled-water pair, not ice 9.5/265.5); window −30..40 °C | area: PAR | covered-by: ALGO.S03
- LIMIT | python/CommonDrivers/math_helpers.py:57-66 | "if (-30.0 <= temperature <= 40.0): ... if rh > 100.0: rh = 100.0" | Legacy `rel_humidity` range-checks temperature only and clamps RH to 0..100; src additionally bounds `abs_hum` (src/math_helpers.py:125) (low) | area: PAR | related: ALGO.S05

## python/CommonDrivers/system_service.py
- INVAR | python/CommonDrivers/system_service.py:8-10 | "_RESET_DELAY = const(5) ... _MAX_STORAGE_PAUSE = const(3600) ... _NTP_WAIT_TIME = const(120)" | Legacy reboot delay 5 s (src 4 s, src/system_service.py:40), storage pause cap 1 h, random boot signature after 120 s without NTP | area: PAR | covered-by: PAR.S04
- SETTLED | python/CommonDrivers/system_service.py:35-51 | "self.storage_pause(True) ... self.reset_timer.init(period=_RESET_DELAY * 1000, mode=Timer.ONE_SHOT, callback=lambda b: SystemReset())" | Legacy reboot/bootloader: pause FRAM storage first, then reset from a one-shot Timer callback after 5 s | area: PAR | related: PAR.S04, CORE
- INVAR | python/CommonDrivers/system_service.py:53-67 | "if duration <= 0: duration = 0 elif duration > _MAX_STORAGE_PAUSE:" | Storage pause clamped to 0..3600 s; 0 unpauses immediately; expiry via one-shot Timer | area: PAR | related: STOR
- INVAR | python/CommonDrivers/system_service.py:72,78,85-92 | "UTC timestamp if NTP synced, random number otherwise after wait time" / "set_data([-1])" | Legacy boot signature is −1 until resolved (src: None, src/system_service.py:271), then NTP UTC timestamp or `getrandbits(32)` after 120 s | area: PAR | related: PAR.T01
- PLATFORM | python/CommonDrivers/system_service.py:18-20,30 | "self.uptime_timer = Timer()" / "period=1000, mode=Timer.PERIODIC, callback=lambda b: self.uptime_event.set()" | Legacy uptime is driven by a 1 s soft Timer → ThreadSafeFlag (ticks collapse if the loop is slow; same pattern in src) | area: PAR | related: NET.S02, PLAT

## python/CommonDrivers/async_manager.py
- INVAR | python/CommonDrivers/async_manager.py:6,22-27 | "_50_YEARS_SEC = const(1576800000)   # seconds of 50 years(!!) perfectly fits into 32bit signed" | Legacy counters (uptime, WiFi uptime, last NTP sync) saturate at 50 years instead of wrapping | area: PAR | related: CORE
- RISK | python/CommonDrivers/async_manager.py:115-129 | "if not key in data: ... valid_config = False" → "json.dump(default_config, f)" | Legacy `ConfigManager`: invalid JSON or ANY missing key overwrites the whole `config.json` with defaults — a firmware adding a key wipes WiFi and all settings | area: PAR | related: PAR.S08, PAR.T06
- RISK | python/CommonDrivers/async_manager.py:126-127,178-179 | "with open(self.config_file, \"w\") as f: json.dump(" | Legacy config writes are in-place, non-atomic (no temp+rename): a power loss mid-write leaves invalid JSON → defaults on next boot | area: PAR | related: CORE, PAR.T06
- LIMIT | python/CommonDrivers/async_manager.py:133-149 | "with open(self.config_file, \"r\") as f: data = json.load(f)" | Every legacy config read opens and parses the whole single `config.json` (no cache); every write re-reads, merges, rewrites it | area: PAR | related: PAR.T06
- INVAR | python/CommonDrivers/async_manager.py:172-177 | "if self.debug: print(\"Config data key error.\"); return False" | `write_config` refuses the whole write if any key is unknown to the stored file | area: PAR | related: CORE
- LIMIT | python/CommonDrivers/async_manager.py:81-90 | "return [self.default] * length" | `DataManager.get_data` with an invalid range returns `[default]*length` (empty list when `length=-1`) (low) | area: PAR | related: CORE

## python/CommonDrivers/async_connect.py
- INVAR | python/CommonDrivers/async_connect.py:12-16 | "_NTP_ASYNC_INTERV = const(3) ... _NTP_CHECK_INTERV = const(10) ... _NTP_CONN_TIMEOUT = const(5000) ... _NTP_SYNC_RETRIES = const(3) ... _NTP_RETRY_INTERV = const(15)" | Legacy NTP timing: 10 s check tick, 5 s per send/receive, 3 retries 15 s apart, "stale" after 3× interval | area: PAR | related: PAR.T04, NET.S03
- INVAR | python/CommonDrivers/async_connect.py:19,25 | "conn_fail_to_hotspot=5, ... wifi_refresh_sec=5, hotspot_time_min=5" | Legacy WiFi defaults: 5 failed attempts → hotspot, 5 s loop cadence, 5 min hotspot window | area: PAR | related: PAR.T04, NET
- LIMIT | python/CommonDrivers/async_connect.py:87-104 | "if self.wifi_mode_lock.locked(): return [\"\"] * 4" / "return \"---\"" | During a mode switch legacy reports not-connected, ifconfig `["","","",""]` and RSSI string `"---"` (also on any RSSI error, e.g. AP mode); src reports null | area: PAR | related: NET.S02, PAR.T01
- SETTLED | python/CommonDrivers/async_connect.py:129-135 | "await self.ntp_synced.setFalse(); await self.last_ntp_sync.set_counter(-1)" | Legacy `ntp_force_sync()` cleared Synced and last-sync (−1) | area: PAR | covered-by: NET.S06
- INVAR | python/CommonDrivers/async_connect.py:140-149 | "await asyncio.sleep(2.9) ... await asyncio.sleep(0.1)" | Legacy WiFi LED in hotspot-without-client: on 2.9 s / off 0.1 s | area: PAR | related: PAR.T04, LED.S04
- INVAR | python/CommonDrivers/async_connect.py:151-166 | "await asyncio.sleep(2) ... await asyncio.sleep(1) ... await asyncio.sleep(1)" | Legacy mode switch: disconnect, inactive, 2 s, deinit, 1 s, new WLAN, 1 s, WiFi uptime reset (NET.S08's src repeat) | area: PAR | related: NET.S08
- RISK | python/CommonDrivers/async_connect.py:183-192 | "else: # valid ... wlan_deactivated = True" | An invalid config read at `wlanConnect()` start deactivates WLAN for the task's lifetime (the local flag is never cleared; a REST reconnect does not revive it) | area: PAR | related: PAR.S08
- INVAR | python/CommonDrivers/async_connect.py:204,225 | "await asyncio.sleep(5)  # allow final tasks of calling function" / "await asyncio.sleep(3)" | Legacy reconnect waits 5 s (let the REST response go out) then 3 s settle | area: PAR | related: PAR.T04
- SETTLED | python/CommonDrivers/async_connect.py:241 | "self.wlan.config(essid=hostname, password='12345678')" | Legacy hotspot SSID = hostname, hardcoded password — the known accepted-risk credential CLAUDE.md names | area: PAR | related: SEC, PAR.S11
- LIMIT | python/CommonDrivers/async_connect.py:236-250 | "del ssid, pw, country, hostname, wifiled, valid, evtloop, own_ip" | With an invalid config read in hotspot start, `evtloop`/`own_ip` are unbound and the `del` raises NameError, ending the WiFi task (low) | area: PAR | related: NET
- PLATFORM | python/CommonDrivers/async_connect.py:243,299 | "self.wlan.config(pm = 0xa11140)  # Stromsparmodus ausschalten" | Legacy disables CYW43 power saving with the raw value 0xa11140 in both AP and STA mode | area: PAR | related: NET, PLAT
- INVAR | python/CommonDrivers/async_connect.py:266-283 | "if len(stations) > 0: # at least one client connected ... self.hotspot_timer.deinit()" | Hotspot stays up indefinitely while any client is associated; with none, a one-shot 5 min timer triggers one STA reconnect attempt ("maybe router reboot after power loss") | area: PAR | related: NET, PAR.T04
- INVAR | python/CommonDrivers/async_connect.py:292-294 | "if (ssid == \"\"):  # invalid or empty config ... connection_failures = self.conn_fail_to_hotspot  # immediate hotspot mode" | Empty SSID → immediate hotspot (factory/first-boot path) | area: PAR | related: PAR.S08
- LIMIT | python/CommonDrivers/async_connect.py:301-324 | "for i in range(10): ... elif status == network.STAT_GOT_IP: ... connection successful" | Legacy connect poll is 10×0.5 s and also does not break on GOT_IP — the full 5 s is spent on success, legacy-identical to src | area: PAR | related: NET.S07
- PLATFORM | python/CommonDrivers/async_connect.py:308 | "elif status == 2:  #  not defined by constant in class yet!" | CYW43 link status 2 (got link, no IP) had no `network.STAT_*` constant at 1.26 | area: PAR | related: PLAT
- INVAR | python/CommonDrivers/async_connect.py:343-345 | "neuer Versuch in 1 Minute... await asyncio.sleep(60)" | After one successful connect, legacy never falls back to hotspot: it retries every 60 s (+5 s loop) forever | area: PAR | related: PAR.T04, NET
- RISK | python/CommonDrivers/async_connect.py:347-362 | "Dauerhaft keine WLAN-Verbindung, keine Verbindung zu Hotspot. Deaktiviere WLAN!" | Second failure streak after a hotspot phase permanently deactivates WLAN (`wlan.deinit()`) until reboot — the legacy origin of the refactor's permanent-deactivation hazard | area: PAR | related: PAR.S08, PAR.T06
- INVAR | python/CommonDrivers/async_connect.py:377,457 | "if (not self.hotspot_mode) and (self.wlan.status() == network.STAT_GOT_IP):" | NTP is skipped in hotspot/no-IP; while unsynced every 10 s tick re-triggers a sync (effective unsynced retry cadence 10 s); the 3×15 s retries apply only when already synced | area: PAR | related: PAR.T04, NET.S03
- SETTLED | python/CommonDrivers/async_connect.py:381,389-390 | "await self.asy_long_block_lock.acquire()  # getaddrinfo may block for some time" | Legacy serialised blocking `getaddrinfo` behind the long-block lock (retired in src per F.3) and used the system resolver | area: PAR | related: NET.S04
- LIMIT | python/CommonDrivers/async_connect.py:397-407 | "except: cli = None ... finally: await cli.disconnect()" | If the NTP exchange raises, `cli` is set to None and the `finally` calls `None.disconnect()` → AttributeError ends the NTP task (supervisor restart) (low) | area: PAR | related: NET
- PLATFORM | python/CommonDrivers/async_connect.py:426-429 | "(struct.unpack(\"!I\", msg[40:44])[0]) - 2208988800 + ntp_offs" | No NTP reply validation (mode/stratum/LI/zero timestamp), era-0 only (2036 rollover), `NTP_Offset_S` added before setting the RTC | area: PAR | related: NET
- INVAR | python/CommonDrivers/async_connect.py:444-447 | "if not valid: ntp_interv = 12" | Unreadable NTP config → 12 h interval default | area: PAR | related: NET
- LIMIT | python/CommonDrivers/async_connect.py:451-461 | "if (self.ntp_sec_count < (_NTP_ASYNC_INTERV * ntp_interv * 60 * 60)):" | Counter resets at every due resync, so the 3×-interval stale rule can never fire — legacy origin of the src behaviour | area: PAR | covered-by: NET.S03
- ASSUME | python/CommonDrivers/async_connect.py:472-482 | "HHMarch = time.mktime((year,3 ,(31-(int(5*year/4+4))%7),1,0,0,0,0,0)) #Time of March change to CEST" | Legacy local time hard-codes the EU DST rule (last Sunday Mar/Oct, 01:00 UTC) for any `GMTOffset`/`DSTOffset` | area: PAR | related: NET, LED
- INVAR | python/CommonDrivers/async_connect.py:484-501 | "else: await self.wifi_uptime.set_counter(0)" / "await self.last_ntp_sync.set_counter(-1)" | WiFi uptime resets whenever status != GOT_IP; last-sync is seconds since sync, −1 when unsynced | area: PAR | related: PAR.T01, NET.S15

## python/CommonDrivers/microdot.py
- ASSUME | python/CommonDrivers/microdot.py:1-7 | "The ``microdot`` module defines a few classes that help implement HTTP-based servers" | The file carries no version, copyright or licence header; its provenance (untagged snapshot between v2.0.1 and v2.1.0, re-checked 2026-09-10) is stated only in CLAUDE.md and its licence (© 2019 Miguel Grinberg, MIT) only in THIRD_PARTY_LICENSES.md:18 (low) | area: PAR | related: PAR.T11, LIC
- SETTLED | python/CommonDrivers/microdot.py:15,601,777,789,803 | "from functools import partial" / "if max_age is not None:" / "filename.endswith('.gz')" / "self.segments = []" | The v2.1.0 markers CLAUDE.md cites for the snapshot dating are present at the snapshot (functools.partial dispatch, max_age, .gz handling, URLPattern segments) | area: PAR | related: PAR.T11

## python/IndividualDrivers/asy_bmp3xx_driver.py
- DRIFT | python/IndividualDrivers/asy_bmp3xx_driver.py:56-59 | "The previous (0, 2, 4, 8, 16, 32, 64, 128) tuple here didn't match ... see BACKLOG.md's asy_bmp3xx_driver.py entry" | The legacy driver was edited after the initial commit (2bda920, 2026-07-22): HEAD is NOT what fielded wozi runs (old tuple); and BACKLOG.md has no `asy_bmp3xx_driver.py` entry any more (dangling pointer) | area: PAR | related: PAR.T15, PAR.T12
- PLATFORM | python/IndividualDrivers/asy_bmp3xx_driver.py:204-213 | "def setup(self, sea_level_pressure: float = 1013.25) -> None: await self._i2c.setup()" | `setup()` is a plain `def` containing `await`; it works only because MicroPython compiles it as a generator that `await` can drive (CPython would reject it) — presumably, unverified at 1.26 (low) | area: PAR | related: PLAT
- INVAR | python/IndividualDrivers/asy_bmp3xx_driver.py:206-210 | "if chip_id not in (_BMP388_CHIP_ID, _BMP390_CHIP_ID):" | Legacy accepts chip ID 0x50 (BMP388) or 0x60 (BMP390), reads calibration, then soft-resets (0xB6) with no post-reset wait | area: PAR | related: SENS
- LIMIT | python/IndividualDrivers/asy_bmp3xx_driver.py:212,272-277 | "self._wait_time = 0.002" / "while await self._read_byte(_REGISTER_STATUS) & 0x60 != 0x60:" | Forced-mode read polls STATUS every 2 ms with no timeout (a sensor that never sets both DRDY bits hangs the task; WDT backstop) — legacy-identical cadence | area: PAR | related: SENS.S23
- LIMIT | python/IndividualDrivers/asy_bmp3xx_driver.py:140-141,215-223 | "Pressure = await self.bmp.get_pressure() / Temperature = await self.bmp.get_temperature()" | Each sample triggers two separate forced conversions (pressure from one, temperature from the next) | area: PAR | related: PAR.T12
- INVAR | python/IndividualDrivers/asy_bmp3xx_driver.py:162-175 | "POffs = 0.0 TOffs = 0.0 SeaLevel = 0.0 AtmTemp = 15.0" / "altitude_baro(Pressure - POffs, -SeaLevel, AtmTemp)" | Published BMP values: pressure − offset, temperature − offset, sea-level pressure from `BMPSeaLevelOffs` (a height in m) and `BMPMeanAtmTemp`; unreadable config falls back to 0/0/0/15 °C | area: PAR | related: PAR.T12, ALGO.S03
- INVAR | python/IndividualDrivers/asy_bmp3xx_driver.py:64,110-134,150-160 | "trigger_sec=1, max_i2c_err=5" / "return False    # Abbruch der Schleife führt zu System-Reset" | Legacy reader pattern (all sensors): setup/config failure or >5 net errors (leaky: −1 per good read) ends the task, which the supervisor turns into a reboot | area: PAR | related: PAR.S04, PAR.S12
- INVAR | python/IndividualDrivers/asy_bmp3xx_driver.py:258-261 | "await self._write_register_byte(_REGISTER_CONFIG, _IIR_SETTINGS.index(coef) << 1)" | Filter-coefficient write replaces the whole CONFIG register | area: PAR | related: SENS

## python/IndividualDrivers/asy_fram_driver.py
- LIMIT | python/IndividualDrivers/asy_fram_driver.py:45-47 | "if (read_buffer[0] != _SPI_MANF_ID) and (prod_id != _SPI_PROD_ID): raise OSError" | Legacy FRAM detection accepts a chip when EITHER the manufacturer ID (0x04) OR the product ID (0x0302) matches | area: PAR | related: STOR, HW
- LIMIT | python/IndividualDrivers/asy_fram_driver.py:48-50 | "self._wp_pin.init(_wp_pin.OUT)" | The WP-pin path references an undefined name and would raise NameError; no legacy unit passes `wp_pin` (low) | area: PAR | related: STOR
- INVAR | python/IndividualDrivers/asy_fram_driver.py:31,148-158 | "max_size: int=0x2000" / "if self._max_size > 0xFFFF:  # > 16bit address" | Legacy FRAM size 8 KB with 2-byte addressing (3-byte only above 64 KB) | area: PAR | related: STOR, PAR.T14
- INVAR | python/IndividualDrivers/asy_fram_driver.py:68-71,81-84 | "if not self.async_lock.locked(): ... return None" | Reads/writes are refused unless the caller already holds the chip lock (`async with fram`) — convention only | area: PAR | related: STOR
- LIMIT | python/IndividualDrivers/asy_fram_driver.py:118-127 | "for i in range(0, data_length): await spidev.write(bytearray([data[i]]))" | Legacy writes one byte per SPI call (allocation per byte) with WREN/WRDI around each write | area: PAR | related: PERF, STOR

## python/IndividualDrivers/asy_fram_manager.py
- INVAR | python/IndividualDrivers/asy_fram_manager.py:8-16,117-119 | "# [...Data 0...][Status 0-1][Status 0-2][...Data 1...][Status 1-1][Status 1-2]" | Legacy chunk layout: two copies, two status bytes each (0x00 uninit, 0x01 idle, 0x02 busy), no CRC, allocated sequentially from address 0 in constructor call order | area: PAR | covered-by: PAR.S09
- PLATFORM | python/IndividualDrivers/asy_fram_manager.py:87,96 | "ts = struct.pack(\"Q\", utc)" | Timestamped chunk prefixes an 8-byte native-endian UTC timestamp; 0 = written while unsynced | area: PAR | related: PAR.T14, STOR
- INVAR | python/IndividualDrivers/asy_fram_manager.py:77-89,97-106 | "if require_ntp: return False, None, False" / "age = time.mktime(time.gmtime()) - ts" | Unsynced writes are stored with ts=0 unless `require_ntp`; age is computed only while currently synced | area: PAR | related: PAR.S01, PAR.S03
- LIMIT | python/IndividualDrivers/asy_fram_manager.py:279-329 | "res = await fram.set_values(addr + self.size + _ADDR_STATUS_1, bytearray([_STATUS_BUSY]))" | Every legacy read writes both status bytes BUSY then IDLE (4 FRAM writes per copy read); a status byte left BUSY by a power cut marks that copy invalid (errors 21/24) | area: PAR | related: STOR, PAR.T14
- RISK | python/IndividualDrivers/asy_fram_manager.py:219-223 | "if data0 != data1: ... self.last_error = 50 ... return None" | Two valid but different copies → error 50 and no data (backup unusable for the session, not repaired) | area: PAR | related: STOR, PAR.T14
- INVAR | python/IndividualDrivers/asy_fram_manager.py:163-178,256-347 | "self.last_error = 40" / "last_error = 10 ... 33" | Legacy FRAM last-error codes 10-15 write, 20-29 read, 30-33 clear, 40 verify mismatch, 50 copy mismatch; surfaced as `SGP40_MemErr_Last` | area: PAR | related: PAR.T01, STOR
- INVAR | python/IndividualDrivers/asy_fram_manager.py:32-37,143-146 | "if (not override_pause) and (self.fram_mgr.get_pause()):" | A global pause flag (reboot, `mempause`) blocks reads, writes and clears unless overridden | area: PAR | related: STOR

## python/IndividualDrivers/asy_i2c_driver.py
- INVAR | python/IndividualDrivers/asy_i2c_driver.py:7,38-54 | "frequency=100000" / "return self._i2c.readfrom_into(address, buffer, True)" | Legacy I2C defaults to 100 kHz (every unit passes 50 kHz) and always sends STOP (no repeated start) | area: PAR | related: BUS
- LIMIT | python/IndividualDrivers/asy_i2c_driver.py:81-108,232-242 | "mem_value = self._i2c.readfrom_mem(address, reg_addr, reg_width)" | Bit/struct register helpers take no bus lock themselves; callers must hold `async with device` — convention only | area: PAR | related: BUS
- LIMIT | python/IndividualDrivers/asy_i2c_driver.py:260-280 | "self.i2c.writeto(self.device_address, b\"\")" | Probe is a zero-length write, falling back to a 1-byte read; all I2C calls are synchronous inside async wrappers (no yield during a transfer) | area: PAR | related: BUS, PLAT

## python/IndividualDrivers/asy_isl29125_driver.py
- INVAR | python/IndividualDrivers/asy_isl29125_driver.py:89-98 | "# ISLOperationMode: 0b101 = 5 = RGB ... # ISLIrCompensation = 63 = on / max (-1 = off)" | Legacy ISL29125 defaults (RGB, 10k lux, 16-bit, IR comp 63, no interrupt) — dev-only in legacy | area: PAR | related: PAR.S14
- LIMIT | python/IndividualDrivers/asy_isl29125_driver.py:140 | "if (self.irq_pin.value() == 0) and not self.irq_waiting:" | The base trigger dereferences `irq_pin` unconditionally; without an IRQ pin the trigger task raises (low) | area: PAR | related: PAR.S14
- LIMIT | python/IndividualDrivers/asy_isl29125_driver.py:324-328 | "red = await self._get_reg(0x0B, \"H\") green = ... blue = ..." | Legacy publishes raw channel counts read as three separate transactions (no lux conversion, channels not from one atomic read) | area: PAR | related: PAR.T12, PAR.S14
- LIMIT | python/IndividualDrivers/asy_isl29125_driver.py:354-356,377-379 | "values = (\"POWERDOWN\", \"GREEN_ONLY\", ...)" | Getters return string names while setters take ints, so a GET readback is not PUT-able | area: PAR | related: PAR.S14
- LIMIT | python/IndividualDrivers/asy_isl29125_driver.py:484,500 | "if not (0 <= value <= 65536):" | Threshold bound admits 65536, which cannot be packed into 16 bits (low) | area: PAR | related: PAR.S14

## python/IndividualDrivers/asy_mprls_driver.py
- INVAR | python/IndividualDrivers/asy_mprls_driver.py:143-148,237-241 | "if FiltCoeff > 0.0:  # optional first-order lowpass filter" / "psi * 68.947572932" | Legacy MPRLS: 10-90 % transfer function, 0-25 psi → hPa, optional EMA; no src counterpart (dev-only sensor) | area: PAR | related: PAR.S14
- LIMIT | python/IndividualDrivers/asy_mprls_driver.py:211-226 | "while True: ... await asyncio.sleep(0.005) # 5ms conversion time" | Busy-poll with no timeout while holding the I2C bus lock (low) | area: PAR | related: PAR.S14

## python/IndividualDrivers/asy_scd30_driver.py
- INVAR | python/IndividualDrivers/asy_scd30_driver.py:55,61,77-78,137-146 | "trigger_sec=3" / "period=500" / "# CO2 Sensor IRQ triggern falls es nicht läuft (Pin bleibt HIGH wenn nicht gelesen!)" | Legacy SCD30: read on RDY rising edge; a 500 ms timer counts RDY-high ticks and forces a read after 2×trigger_sec ticks (6 = 3 s) | area: PAR | covered-by: SENS.S08
- WORKAROUND | python/IndividualDrivers/asy_scd30_driver.py:243-246 | "await asyncio.sleep(0.2)  # not mentioned by datasheet, but required to avoid IO error" | 200 ms settle after the soft reset every read-task (re)start; removal trigger: none stated | area: PAR | related: SENS.S22
- SETTLED | python/IndividualDrivers/asy_scd30_driver.py:89-99,239-241 | "await self.scd.setup()" → "await self.reset()" | Legacy also soft-resets (0xD304) on every read-task (re)start and never issues a start-continuous command at boot (relies on the sensor's stored state) | area: PAR | related: SENS.S22
- INVAR | python/IndividualDrivers/asy_scd30_driver.py:129-134 | "await self.meas_data.set_data([CO2, Temperature, Humidity, math_helpers.wet_bulb_temperature(" | Published SCD30 tuple: CO2, T, RH, wet bulb, dew point, timestamp; temperature offset is applied only by the sensor's NVM setting, not in software | area: PAR | related: PAR.T12
- ASSUME | python/IndividualDrivers/asy_scd30_driver.py:292-296 | "return await self._read_register(_CMD_CONTINUOUS_MEASUREMENT)" | `AmbPres` GET reads back the continuous-measurement command register 0x0010 — the unverified read-back A.4 builds on | area: PAR | related: SENS.T09
- LIMIT | python/IndividualDrivers/asy_scd30_driver.py:329-335 | "if offset > 655.35: raise" / "int(offset * 100)" | Only an upper bound; a negative offset would fail in byte packing; truncation, not rounding (REST bound 0.0-655.35 keeps negatives out) | area: PAR | related: SENS.S09
- INVAR | python/IndividualDrivers/asy_scd30_driver.py:399,408 | "await asyncio.sleep(0.05)  # 3ms min delay" / "await asyncio.sleep(0.005)  # min 3 ms delay" | Legacy waits 50 ms after every command and 5 ms between register write and read | area: PAR | related: SENS.T06, PAR.T04
- LIMIT | python/IndividualDrivers/asy_scd30_driver.py:350-379 | "if await self.data_available(): await self._read_data() return self._co2" | Each of CO2/T/RH checks data-ready separately and returns the cached value when not ready (stale values re-stamped with a fresh timestamp) | area: PAR | covered-by: SENS.S08

## python/IndividualDrivers/asy_sgp40_driver/__init__.py
- RISK | python/IndividualDrivers/asy_sgp40_driver/__init__.py:339,341-352 | "self._reset()" (no await) / "# This is a general call Reset." | The legacy "general-call reset" never ran: `_reset()` is an un-awaited coroutine, and even if run it writes 0x0006 to the SGP40's own address 0x59, not general-call 0x00 — so the refactor's real broadcast (SPECIFICATION.md:2047, accepted risk) is new field behaviour, not parity | area: PAR | related: BUS, SENS
- INVAR | python/IndividualDrivers/asy_sgp40_driver/__init__.py:20-22,83,207 | "_FRAM_VERIFY_MINS = const(60)" / "int(math.ceil((10 * _FRAM_VERIFY_MINS) / backup_period) * 0.1)" | Legacy verifies an FRAM backup roughly once per hour of backups | area: PAR | related: STOR
- INVAR | python/IndividualDrivers/asy_sgp40_driver/__init__.py:84-86 | "if 1 <= wait_ntp <= 600:  # wait ntp between 1sec and 10mins" | `SGPWaitTimeNTP` 0 (or out of range) → one immediate restore attempt, contrary to the UI's "0 = never wait" meaning | area: PAR | covered-by: PAR.S01
- ASSUME | python/IndividualDrivers/asy_sgp40_driver/__init__.py:108-127 | "if age is None: if voc_init > 0: ... deserialize = None" | While NTP is unsynced a timestamped backup is retried each second; when the wait expires the backup is restored WITHOUT the max-age check; `SGPBackupMaxAge` 0 = no age limit | area: PAR | related: PAR.S01
- INVAR | python/IndividualDrivers/asy_sgp40_driver/__init__.py:132-134,141-142 | "backup_counter >= (60 * backup_period)" / "if backup_counter >= 100000:" | Backup every `60×SGPBackupPeriod` loop ticks (1 s timer); counter wraps at 100000 | area: PAR | related: XCUT.T21
- SETTLED | python/IndividualDrivers/asy_sgp40_driver/__init__.py:211-238 | "require_ntp = (voc_write > 0)" / "voc_write = 0" | Until the first synced write, backups require NTP (skipped, not errors); after it, `voc_write` stays 0 so later backups never wait again | area: PAR | covered-by: PAR.S03
- LIMIT | python/IndividualDrivers/asy_sgp40_driver/__init__.py:158-160 | "if (Temp is None) or (Hum is None): ... hat keine Kompensationsdaten!" | Without SCD30 T/RH the SGP40 is not sampled at all that second (VOC algorithm not fed) | area: PAR | related: PAR.T12
- INVAR | python/IndividualDrivers/asy_sgp40_driver/__init__.py:321-338 | "if serialnumber[0] != 0x0000:" / "if featureset[0] & 0xFF00 != 0x3200:" / "if self_test[0] != 0xD400:" | Legacy checks serial word 0 == 0, feature set 0x32xx and the full self-test word == 0xD400 (src checks the high byte only) | area: PAR | related: SENS.S21, SENS.S06
- ASSUME | python/IndividualDrivers/asy_sgp40_driver/__init__.py:367,386 | "temp_ticks = int(((temperature + 45) * 65535) / 175) & 0xFFFF" | Legacy truncates temperature ticks but rounds humidity ticks; src rounds both — a small compensation-input delta | area: PAR | related: PAR.T12
- INVAR | python/IndividualDrivers/asy_sgp40_driver/__init__.py:392-398 | "read_value = await self._read_word_from_command(delay_ms=500)" | Legacy waits 500 ms per measurement (src 100 ms, datasheet 30 ms) | area: PAR | related: SENS.S07
- TODO | python/IndividualDrivers/asy_sgp40_driver/__init__.py:474 | "# TODO: Take 2-byte command as int (0x280E, 0x0006) and packinto command buffer" | Upstream Adafruit TODO carried in the legacy driver; not a to-do here (legacy rule) (low) | area: PAR | -

## python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py
- SETTLED | python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:1-12 | "SPDX-FileCopyrightText: Copyright (c) 2010 DFRobot Co.Ltd ... * Author(s): yangfeng" | Legacy VOC algorithm is DFRobot's Python port (MIT), not Sensirion's C reference directly | area: PAR | related: ALGO, LIC
- MIRROR | python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-164 | "return struct.pack(\"31q\"," | Legacy state is 31 native-endian int64 fields (248 B, all algorithm params incl. uptime); src packs "32q" (src/voc_algorithm.py:98, 141) — the formats are not interchangeable across reflash or rollback | area: PAR | related: PAR.S09, ALGO.S02, PAR.T14
- INVAR | python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:18,384-387,414 | "_VOCALGORITHM_INITIAL_BLACKOUT = const(45)" | Legacy publishes VOC index 0 for the first 45 samples after init or reset; restoring a backup restores uptime and skips the blackout | area: PAR | related: SENS.S04
- LIMIT | python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-93,125-126 | "except: return None" | A pack failure silently yields no backup (counted as a serialise error by the reader) (low) | area: PAR | related: ALGO

## python/IndividualDrivers/asy_shtc3_driver.py
- INVAR | python/IndividualDrivers/asy_shtc3_driver.py:164-178 | "tc = Temperature - TOffs ... rh = math_helpers.rel_humidity(tc, ah)" | Legacy SHTC3 applied a software temperature offset and re-derived RH via absolute humidity, plus optional EMA — dropped with the sensor (dev-only) | area: PAR | related: PAR.S14
- LIMIT | python/IndividualDrivers/asy_shtc3_driver.py:313-315 | "return (temperature, humidity)" (on CRC mismatch) | A CRC failure returns (None, None) without raising, so the reader's `Temperature - TOffs` raises TypeError and ends the task (low) | area: PAR | related: PAR.S14

## python/IndividualDrivers/asy_spi_driver.py
- INVAR | python/IndividualDrivers/asy_spi_driver.py:39-47,129-138,140-147 | "self._spi.init(baudrate=baudrate," / "await asyncio.sleep_ms(1)" | Legacy re-inits the SPI peripheral (1 MHz, mode 0, always MSB) on every CS transaction and sleeps 1 ms after CS assert and after release | area: PAR | related: BUS, PERF
- LIMIT | python/IndividualDrivers/asy_spi_driver.py:31-37 | "self.deinit()" (in `SPI.__aexit__`) | Using the bus object itself as a context manager deinits and deletes the peripheral; only `SPIDevice` is used as one, so the path is dormant (low) | area: PAR | related: BUS

## python/IndividualDrivers/asy_uart.py
- MIRROR | python/IndividualDrivers/asy_uart.py:198-241 | "crc = crc >> 1 ... crc = crc ^ self.poly" / "struct.pack(\"H\", crc)" | Legacy CRC16 shifts right with poly 0x1021/preset 0xFFFF, little-endian, check = CRC over data+CRC == 0; src CRC16 shifts left (src/crc_checks.py:44) — a wire-level difference on the UART protocol's origin (dev-only, no field peer) | area: PAR | related: UART
- LIMIT | python/IndividualDrivers/asy_uart.py:83-99 | "add = self.uart.read(nbytes - len(msg))" | After POLLIN the legacy reads the whole remaining frame in one call — the blocking-read pattern CLAUDE.md/F.5.8 forbid in src | area: PAR | related: UART
- LIMIT | python/IndividualDrivers/asy_uart.py:10,57-72 | "poll_wait_ms=0" / "await asyncio.sleep_ms(self.poll_wait_ms)" | `ready()` polls with `sleep_ms(0)` by default — busy-yield, no idle cadence (contrast F.5.9's `poll_idle_ms`) | area: PAR | related: UART, PERF

## python/IndividualDrivers/asy_uart_comm.py
- INVAR | python/IndividualDrivers/asy_uart_comm.py:8-23,187-199 | "# Message format: [UID][CMD][SIZE][CHUNKS][CUR_CHUNK][...Payload...]" / "payload_size=48, timeout=1000" | Legacy protocol origin: 5-byte header + 48-byte zero-padded payload, 1 s timeout, UID 0..0xFE, first chunk carries the command ID | area: PAR | related: UART
- DRIFT | python/IndividualDrivers/asy_uart_comm.py:164 | "if num_chunks > 0xFF: # 16bit payload field" | Comment says 16-bit while the check and the field are 8-bit (low) | area: PAR | related: UART
- INVAR | python/IndividualDrivers/asy_uart_comm.py:38-46,205 | "timeout = int(1.5 * self.timeout)" / "if not (msg[_MSG_CMD] & exp_cmd):" | Recovery drains until 1.5×timeout of silence then blocks writes one more 1.5×timeout; command check is a bitmask (a frame with several bits set passes) | area: PAR | related: UART

## python/IndividualDrivers/neopixel_signal.py
- INVAR | python/IndividualDrivers/neopixel_signal.py:8,11,56-62 | "_MAX_OVERRIDE_TIME = const(3600)" / "neopixel_freq=20, led_overl_bri=50" | Legacy LED: 20 Hz ramp, WiFi-LED overlay white at brightness 50, auto-signal pause clamped 0..3600 s | area: PAR | related: PAR.T04, LED
- INVAR | python/IndividualDrivers/neopixel_signal.py:67-73 | "if self.ext_start_signal.is_set(): return False" | A REST LED command is rejected at once (→ code 8 "LED is busy") when one is already pending | area: PAR | covered-by: REST.S09
- INVAR | python/IndividualDrivers/neopixel_signal.py:128-150 | "self.rgbt[3] = 0.1 if self.rgbt[3] < 0.1 else self.rgbt[3]" / "async with self.asy_long_block_lock:" | Ramp up/down over `t` seconds (min 0.1 s) while holding the long-block lock, then LED off and WiFi-overlay state restored | area: PAR | related: LED, PAR.T04
- SETTLED | python/IndividualDrivers/neopixel_signal.py:164-170 | "if onMinOfDay <= curMinOfDay <= offMinOfDay:" | Auto-signal window must lie within one day (no midnight wrap; UI says so) and only runs with NTP-derived local time | area: PAR | related: LED (A.4 midnight-window decision)
- INVAR | python/IndividualDrivers/neopixel_signal.py:173-186 | "await asyncio.sleep(2 * flashDur)" | CO2 red, VOC green, humidity blue; a 2×FlashDur gap follows CO2 and VOC but not the last (humidity) warning | area: PAR | covered-by: LED.S03
- INVAR | python/IndividualDrivers/neopixel_signal.py:159-162,188-192 | "Interv = 600" / "if (rem_interv < 0.1): rem_interv = 0.1" | Interval counted from loop start (warnings included); unreadable config → auto off, 600 s | area: PAR | related: PAR.T04

## python/Manifest/manifest.py
- INVAR | python/Manifest/manifest.py:1-2 | "include(\"$(PORT_DIR)/boards/RPI_PICO_W/manifest.py\")" / "freeze(\".\")" | Legacy freezes the whole staged build directory (all CommonDrivers incl. microdot, the per-build driver set, frozen_html) on top of the stock board manifest | area: PAR | related: PAR.T09

## modules/_boot.py
- SETTLED | modules/_boot.py:16 | "import sensortask.py" | The frozen boot imports the frozen `sensortask` with a literal `.py`; never to be changed without hardware testing (CLAUDE.md hard rule, BACKLOG #1) | area: PAR | related: PAR.T09
- RISK | modules/_boot.py:4-12 | "# Try to mount the filesystem, and format the flash if it doesn't exist." / "except: vfs.VfsLfs2.mkfs(bdev, progsize=256)" | Legacy formats the littlefs (wiping `config.json`) on ANY mount exception — matters for a rollback onto a filesystem last written by 1.29 | area: PAR | related: PAR.T14, PAR.S10
- ASSUME | modules/_boot.py:16 | "import sensortask.py" | The app runs from `_boot` itself and never returns, so a filesystem `boot.py`/`main.py` on a legacy unit presumably never executed — relevant to what a reflash finds (unverified) (low) | area: PAR | related: PAR.T08

## modules/sensortask-wozi.py
- INVAR | modules/sensortask-wozi.py:20-21 | "_DEFAULT_CONFIG = const(\"{\\\"LedAutoOn\\\": true, ... \\\"SGPWaitTimeNTP\\\": 30}\")" | Legacy defaults: auto LED on 10:00-18:00, interval 300 s, FlashDur 2, Bri 200, CO2 1600, VOC 350, Hum 65; GMT/DST 3600; NTP pool.ntp.org/12 h/offset 0; SSID ""; Hostname "SensorNode"; Country DE; BMP interval 2, overs 1, filter 0, sea-level 0, atm 15 °C; SGP backup 1 min/max age 7200 min/NTP wait 30 s | area: PAR | related: PAR.T01, PAR.S11
- INVAR | modules/sensortask-wozi.py:23-27 | "_TASK_CHECK_TIME = const(3) _TASK_FAIL_INCREMENT = const(100) _TASK_FAIL_MAX = const(300)" / "_FRAM_PAUSE_SEC = const(300)" | Supervisor 3 s / +100 per restart / >300 stops feeding; `mempause` = 300 s | area: PAR | covered-by: PAR.S04
- INVAR | modules/sensortask-wozi.py:77-90 | "watchdog = WDT(timeout = 8000)" / "i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000)" | Wozi wiring: WDT 8 s at import; i2c0 SCL13/SDA12, i2c1 SCL19/SDA18, both 50 kHz; SPI0 2/3/4, FRAM CS1 8 KB; SCD30 on i2c0 RDY GP8; SGP40+BMP on i2c1; NeoPixel GP15; hotspot window 8 min — matches `devices/wozi.toml` pins at a glance | area: PAR | related: PAR.T02
- INVAR | modules/sensortask-wozi.py:86,90-91 | "sgp_backup = fram.get_timestamped_chunk(_SGP40_Memsize, conn.ntp_issynced)" / "conn.set_ext_led(pixel)" | FRAM chunk 0 is the SGP40 backup (only FRAM user); the NeoPixel doubles as the WiFi LED | area: PAR | related: PAR.S09, LED.S04
- RISK | modules/sensortask-wozi.py:100-109 | "starter = Timer(period=delay, mode=Timer.ONE_SHOT, callback=lambda b: timer_sequencer(" | Legacy staggers timer starts (1000 ms/(n+1)) through one-shot Timers held in a local only — the unreferenced-Timer GC pattern the src `_timer_sequencer` fix addressed | area: PAR | related: XCUT.S05
- INVAR | modules/sensortask-wozi.py:113-143 | "@app.get('/favicon.ico')" / "send_file('html/index.html', compressed=True, file_extension='.gz')" | Legacy static routes: `/`, `/index.html`, `/favicon.ico`, `/nettimeconfig.html`, `/sensorconfig.html`, `/systemledconfig.html`, `/style.css`, `/functions.js`, all gzip from the frozen `html/` | area: PAR | related: PAR.S06, PAR.S15
- INVAR | modules/sensortask-wozi.py:146-166 | "\"IPv4\": netConfig[0], ... \"Rssi\": Rssi" / "cfg_data[\"PW\"] = \"********\"" | GET `/net/status` {IPv4, Subnet, Gateway, DNS, Rssi}; GET `/net/config` {Country, Hostname, SSID, PW:"********"} (PW null on read error) | area: PAR | related: PAR.T01, NET.S16
- INVAR | modules/sensortask-wozi.py:168-182 | "update_valid_json(req_json, \"Hostname\", \"str\", res, 1, 63" | PUT `/net/cmd` `setNetwork`: Hostname 1-63, Country exactly 2, SSID 2-32, PW 8-63; saves then reconnects (5 s delay) | area: PAR | covered-by: NET.S17
- INVAR | modules/sensortask-wozi.py:185-219 | "system = {\"Synced\": \"On\" if synced else \"Off\", \"Unix\": time.mktime(gmt)}" | GET `/time/status` {System{Synced "On"/"Off", Unix}, UTC{...}, Local{... or "None" strings}}; PUT `setTiming`: NTP_Host 3-1024, offsets ±43200, interval 1-24 h; then force-resync | area: PAR | related: PAR.T01, NET.S06
- INVAR | modules/sensortask-wozi.py:222-248 | "\"WetBulb\": \"None\" if scd_meas[_SCD30_WetBulb] is None else" | GET `/sensors/status` groups SCD30{CO2,Temp,Hum,WetBulb,DewPoint,TS}, SGP40{VOC,Raw,TS}, BMP388{Pres,Temp,SLPres,TS}; absent values mix JSON null and the string "None" | area: PAR | covered-by: PAR.S06
- INVAR | modules/sensortask-wozi.py:250-304 | "\"SelfCal\": toSwitch(await scd_reader.get_self_calibration_enabled())" | GET `/sensors/config` reads SCD30 settings live from the sensor (all "None" on any error), BMP oversampling/filter live from the chip as values, the rest from config.json | area: PAR | related: PAR.T01
- RISK | modules/sensortask-wozi.py:316-321 | "data[\"MeasInt\"] = await scd_reader.get_measurement_interval()," | Trailing commas make the readback of MeasInt/AmbPres/Altitude/ForceCalRef/SelfCal 1-tuples, so the "Unchanged" comparison never matches: legacy wrote those to SCD30 NVM on EVERY non-empty PUT value (only TempOffs was skipped when equal; the UI sends "" for untouched fields) — same at arzi/neu :277-281 | area: PAR | related: PAR.S02, SENS.T07
- INVAR | modules/sensortask-wozi.py:322-344 | "data[\"ContMeas\"] = True  # not readable from sensor" / "# datamanager = None --> Don't write system config here" | PUT `setSCD`: TempOffs 0.0-655.35, MeasInt 2-1800, AmbPres 0 or 700-1400 (force), Altitude 0-65535, ForceCalRef 400-2000, SelfCal switch, ContMeas "Off" only → stop; nothing persisted to config.json; a failed sensor readback returns code 4 | area: PAR | related: PAR.S02, PAR.T01
- INVAR | modules/sensortask-wozi.py:346-358 | "update_valid_json(req_json, \"SGPBackupMaxAge\", \"int\", res, 0, 10080" | PUT `setSGP`: BackupPeriod 0-1440 min, MaxAge 0-10080 min, WaitTimeNTP 0-600 s, SGPResetVOC command-only ("On") | area: PAR | related: PAR.S01, PAR.T01
- INVAR | modules/sensortask-wozi.py:360-379 | "update_valid_json(req_json, \"BMPPressOvers\", \"int\", res, 0, 5, weight_fct=lambda x : 2 ** x" | PUT `setBMP`: interval 1-3600, oversampling as exponent 0-5 (GET returns the value 1-32), FiltCoeff 0-7 → 2**x−1 (HEAD; fielded wozi had 2**x with special 0), offsets P ±500, T ±10, sea-level −1000..5000, atm ±50 | area: PAR | related: PAR.S06, PAR.T15
- INVAR | modules/sensortask-wozi.py:382-395 | "return {\"pauseTime\": pausetime}" / "cfg_data[\"LedAutoOn\"] = toSwitch(" | GET `/led/status` {pauseTime}; GET `/led/config` 12 Led* keys with On/Off strings for the two switches | area: PAR | related: PAR.T01
- INVAR | modules/sensortask-wozi.py:402-419 | "default = { \"r\": 0, \"g\": 0, \"b\": 0, \"t\": 1.0 }" | `lightCmdLED`: r/g/b 0-255, t 0.5-60 s; an empty field falls back to the default (0/0/0/1.0) but an absent key is code 7; busy → code 8; nothing saved | area: PAR | related: REST.S09, REST.S10
- INVAR | modules/sensortask-wozi.py:421-453 | "update_valid_json(req_json, \"pauseTime\", \"int\", res, 0, 3600" / "\"LedAutoInterv\", \"float\", res, 60.0, 3600.0" | `pauseAutoLED` 0-3600 (bad → code 9); `setAutoLED`: hours 0-23, minutes 0-59, Bri 1-255, Interv 60-3600 s, FlashDur 0.5-10 s, CO2 0-3000, VOC 0-500, Hum 0-100 | area: PAR | related: PAR.T01, LED
- INVAR | modules/sensortask-wozi.py:455-462 | "res = await set_sensor_value(res, conn.set_wifi_led, cfgmgr, default=True" | `setWiFiLED` switch applied live and persisted | area: PAR | related: LED.S04
- INVAR | modules/sensortask-wozi.py:465-506 | "\"Error_Status\": toSwitch(ErrorStatus)," / "sgpback = \"No TS\"" | GET `/system/status` keys: Sys_Uptime, Wifi_Uptime, NTP_LastSync, Boot_Signature, Error_Status, Task_ErrCnt, Task_LastErr (task-list index), per-sensor ErrCnt, SGP40 Backup/Restore TS ("None"/"No TS"), SGP40 MemErr counters; no persistent error log | area: PAR | related: PAR.T01, PAR.S05
- INVAR | modules/sensortask-wozi.py:508-537 | "special_val=[\"reboot\", \"bootloader\", \"mempause\"]" | PUT `/system/cmd` `systemCmd` content ∈ {reboot, bootloader, mempause}; anything else code 10 | area: PAR | related: PAR.T01
- INVAR | modules/sensortask-wozi.py:540-583 | "async_onetime.append(fram.setup)" / "await asyncio.sleep(1.0 / len(task_starters))" / "await conn.ntp_force_sync() # first sync" | Boot order: fram.setup → timers staggered over 1 s → 16 tasks spread over 1 s (webserver last) → forced first NTP sync → supervisor | area: PAR | related: XCUT.T01, PAR.T04
- RISK | modules/sensortask-wozi.py:570-573,585-608 | "if task_errors > _TASK_FAIL_MAX: all_running = False" / "watchdog.feed()" | `all_running` never recovers once false: a failed `fram.setup()` or a 4th quick task restart starves the WDT → reset; a sensor whose setup keeps failing therefore reboot-loops the unit (~12 s + 8 s) | area: PAR | covered-by: PAR.S12
- DRIFT | modules/sensortask-wozi.py:604-607 | "if all_running: ... watchdog.feed()" | PAR.S12 cites `:604-606` for the feed; the feed block is `:605-607` (off by one) (low) | area: PAR | related: PAR.S12

## modules/sensortask-arzi.py
- INVAR | modules/sensortask-arzi.py:21,69-73 | "i2c1 = asy_i2c_driver.I2C(1, 27, 26, frequency=50000)" / "spi0 = asy_spi_driver.SPI(0, 2, 3, 4)" | Arzi = wozi minus BMP388 (no BMP keys, routes or counters); i2c1 on SCL27/SDA26; SPI0 2/3/4 with FRAM CS1 — matches `devices/arzi.toml` at a glance | area: PAR | related: PAR.T02

## modules/sensortask-neu.py
- INVAR | modules/sensortask-neu.py:72-73 | "spi0 = asy_spi_driver.SPI(0, 18, 19, 16)" / "fram = asy_FRAM_manager(spi0, 17, max_size=0x2000" | Neu differs from arzi only in SPI0 (SCK18/MOSI19/MISO16, FRAM CS17) and shares arzi's web UI (`build-neu.sh:12`); matches grkizi/klkizi/schlafzi TOMLs at a glance | area: PAR | related: PAR.T02, PAR.T13

## modules/sensortask-dev.py
- DRIFT | modules/sensortask-dev.py:91,97 | "sysfunct = System_Service(debug=debug)" / "SGP40_Reader(i2c1, sgpCompCallback, trigger_sec=1," | Legacy dev entry point cannot run against the current legacy drivers (missing required `asy_ntp_callback`/`asy_cfg_callback`, unknown `trigger_sec`), and `build-dev.sh` never freezes it — a stale bench file, not a parity target | area: PAR | covered-by: PAR.S14
- SETTLED | modules/sensortask-dev.py:89-90,103-104,428 | "#watchdog = WDT(timeout = 8000)" / "#pixel = Neopixel_Signal(16, ..." / "pausetime = await pixel.get_override_led()" | Dev: debug on, no watchdog, NeoPixel commented out while the LED routes still reference `pixel` — the quirk CLAUDE.md declares out of scope | area: PAR | related: PAR.S14
- INVAR | modules/sensortask-dev.py:94-100 | "i2c1 = asy_i2c_driver.I2C(1, 15, 14, frequency=50000)" / "mprls_reader = MPRLS_Reader(i2c0, ..., reset_pin=10, eoc_pin=9" | Legacy dev wiring: SHTC3+MPRLS on i2c0, SCD30 (RDY GP11)+SGP40+ISL29125 (INT GP8) on i2c1 SCL15/SDA14; no FRAM, no UART despite `build-dev.sh` freezing the UART modules | area: PAR | related: PAR.S14, HW

## build-wozi.sh / build-arzi.sh / build-neu.sh / build-dev.sh
- ASSUME | build-wozi.sh:1-3 | "this script has always assumed it's run from inside py-include/ regardless of how that directory got there" | Legacy builds assume a `py-include/` checkout inside a MicroPython tree and build whatever MicroPython ref that tree holds — the scripts pin no version (1.26 is a doc claim); same at build-arzi/neu/dev.sh:1-3 | area: PAR | related: PAR.T15, PAR.T09
- DRIFT | build-wozi.sh:1-3,40 | "PY_INCLUDE_DIR=\"$(pwd)\"" / "FROZEN_MANIFEST=\"$PY_INCLUDE_DIR/python/build/manifest.py\"" | All four scripts were edited after the initial commit (b6cb852, hardcoded `/home/nico/...` path replaced) — HEAD scripts are not byte-identical to what built the fielded firmware | area: PAR | related: PAR.T15, DOC.S21
- INVAR | build-wozi.sh:11-16 | "gzip -9 ./*" / "python3 -m freezefs -s html frozen_html.py" | Web files are gzipped then frozen with an unpinned host `freezefs` (`-s` = silent, default mount at `/html`) — so a legacy littlefs presumably holds no `/html` (unverified for the version used) | area: PAR | related: XCUT.S14, PAR.T08
- INVAR | build-wozi.sh:17-27,30-32 | "cp -r ../CommonDrivers/* ." / "cp ./modules/sensortask-wozi.py ../ports/rp2/modules/sensortask.py" | Per-unit frozen set: all CommonDrivers + I2C/SPI/FRAM/NeoPixel/SCD30/SGP40 (+BMP3xx on wozi); `_boot.py` and `sensortask.py` swapped into `ports/rp2/modules` for the build | area: PAR | related: PAR.T09
- INVAR | build-neu.sh:12,31 | "cp -r ../../../html_raw/arzi/* ." / "cp ./modules/sensortask-neu.py" | Neu builds use arzi's HTML with neu's sensortask | area: PAR | related: PAR.T10, PAR.T13
- INVAR | build-dev.sh:12,22-23,32-33 | "cp ../IndividualDrivers/asy_uart.py ." / "cd ../.. # now inside py-include" | The dev build freezes UART/SHTC3/MPRLS/ISL drivers but does not install the custom `_boot.py` or a frozen `sensortask` (stock boot) | area: PAR | related: PAR.S14

## html_raw/general/functions.js
- INVAR | html_raw/general/functions.js:27-39 | "requestData[field] = inputFields[field].value; inputFields[field].value = \"\";" | The legacy UI sends every field as a string, `""` for untouched fields (= "Unchanged" server-side), and clears inputs after Apply | area: PAR | related: PAR.T10, PAR.S02
- INVAR | html_raw/general/functions.js:48-66 | "parent.style.backgroundColor = color;" / "setTimeout(updateCurrentValues, 2000, currentValues);" | Per-field colours from the `result` map (Valid green, Unchanged grey, Invalid red, Failed lavender) and a single re-fetch 2 s after Apply | area: PAR | related: PAR.T10
- INVAR | html_raw/general/functions.js:98-112 | "if ((inputFields[key].textContent !== \"Off\") && (inputFields[key].textContent !== \"On\")) { // uninitialized" | Switch buttons start empty (sends ""), first click sets the given start state, later clicks toggle | area: PAR | related: PAR.T10
- LIMIT | html_raw/general/functions.js:70-81 | "function getColorForCode(value) {" | Defined but not called by any legacy page (low) | area: PAR | related: PAR.T10

## html_raw/general/nettimeconfig.html
- INVAR | html_raw/general/nettimeconfig.html:207-214 | "setInterval(updateCurrentValues, 500, currentTimeStatus);" | Legacy polls `/time/status` and `/net/status` every 500 ms each while the page is open | area: PAR | related: PAR.T04, PAR.S07
- INVAR | html_raw/general/nettimeconfig.html:28-48,74-110 | "<p>Valid values: 1 to 63 characters</p>" / "<input type=\"text\" id=\"input_net_pw\"/>" | UI-stated bounds mirror the handler (Hostname 1-63, SSID 2-32, PW 8-63, NTP host 3-1024, offsets ±43200, interval 1-24 h); password entered in a plain text field | area: PAR | related: PAR.T10, NET.S17

## html_raw/wozi/index.html
- INVAR | html_raw/wozi/index.html:70-71 | "setInterval(updateCurrentValues, 2000, measurements);" | Measurements page polls `/sensors/status` every 2 s and shows raw unrounded values | area: PAR | covered-by: PAR.S07

## html_raw/wozi/sensorconfig.html
- DRIFT | html_raw/wozi/sensorconfig.html:105,195 | "<p class=\"p_dyn\" id=\"shtc_result\"></p>" / "result: document.getElementById(\"sgp_result\")" | The SGP40 Apply result element id does not exist, so the result text never shows (JS error after colouring) — same in arzi and dev (low) | area: PAR | related: PAR.T10
- SETTLED | html_raw/wozi/sensorconfig.html:92 | "Wait time for NTP sync before using timestamped backups.<br>0 = never wait." | The UI's documented meaning of `SGPWaitTimeNTP` 0 | area: PAR | covered-by: PAR.S01
- INVAR | html_raw/wozi/sensorconfig.html:29-50,118,130,142 | "0 = Compensation off / use Altitude" / "2 ** <input" / "(2 ** <input ...>) - 1" | UI semantics: AmbPres starts continuous measurement; Altitude only used with AmbPres 0; oversampling/filter entered as exponents; HEAD label "(2**x)−1" differs from the fielded "2 ** x" (2bda920) | area: PAR | related: PAR.T10, PAR.T15
- LIMIT | html_raw/wozi/sensorconfig.html:239 | "updateCurrentValues(currentSensorValues);" | Sensor config values are fetched once on load (and 2 s after Apply), never polled | area: PAR | related: PAR.T10

## html_raw/wozi/systemledconfig.html
- SETTLED | html_raw/wozi/systemledconfig.html:63-66 | "Auto On and Off times must be on the <b>same day</b>.<br> Auto On must be <b>before</b> Off" | The legacy UI documents the no-midnight-wrap window as a user constraint | area: PAR | related: LED (A.4 midnight-window decision)
- INVAR | html_raw/wozi/systemledconfig.html:32-47 | "Valid values: 0 to 255<br>Default = 0" / "Valid values: 0.5 to 60.0<br>Default = 1.0" | LED command fields document defaults used when left blank | area: PAR | related: REST.S10
- INVAR | html_raw/wozi/systemledconfig.html:300-306 | "setInterval(updateCurrentValues, 500, currentStatusSys);" | `/led/status` and `/system/status` polled every 500 ms; LED config fetched once | area: PAR | related: PAR.T04, PAR.S07
- INVAR | html_raw/wozi/systemledconfig.html:174-177 | "<i>- mempause</i> pause backups for 5 minutes" | System commands exposed through a free-text field | area: PAR | related: PAR.T10

## html_raw/arzi/index.html, html_raw/arzi/sensorconfig.html, html_raw/arzi/systemledconfig.html
- INVAR | html_raw/arzi/sensorconfig.html:1-179 | (diff vs wozi) | Arzi pages = wozi pages minus every BMP388 card/field/counter; otherwise identical (also used by neu) | area: PAR | related: PAR.T10

## html_raw/dev/index.html, html_raw/dev/sensorconfig.html, html_raw/dev/systemledconfig.html
- INVAR | html_raw/dev/sensorconfig.html:109-231 | "<h2>ISL29125 - RGB Brightness</h2>" / "Valid values: -1 to 3600000" | Dev pages add SHTC3/MPRLS/ISL29125 cards (ISL auto-clear −1 off / 0 immediate / >0 ms) — bench only | area: PAR | related: PAR.S14
- DRIFT | html_raw/dev/sensorconfig.html:143-146 | "<h2>Pressure Offset [K]</h2> ... Valid values: -500.0 to 500.0 K" | MPRLS pressure offset labelled in K (low) | area: PAR | related: PAR.S14

## html_raw/general/style.css
(no parity-relevant items)

## html_raw/general/favicon.ico
- INVAR | html_raw/general/favicon.ico | (binary, 15406 B, 3 icons 16/32 px) | Served gzip-compressed at `/favicon.ico` by every legacy unit | area: PAR | covered-by: PAR.S15

## Coverage
Every file below was read in full (code and comments); "comment lines" is the helper's dump count (HTML/CSS/binary have none, their full text was read instead). Items are attributed to the file cited first.

| file | comment/doc lines read | items |
|---|---|---|
| python/CommonDrivers/api_helpers.py | 39 (+237 code lines) | 11 |
| python/CommonDrivers/asy_udp_socket.py | 5 (+84) | 5 |
| python/CommonDrivers/async_connect.py | 58 (+501) | 25 |
| python/CommonDrivers/async_manager.py | 6 (+187) | 6 |
| python/CommonDrivers/captive_dns.py | 12 (+67) | 5 |
| python/CommonDrivers/math_helpers.py | 1 (+67) | 5 |
| python/CommonDrivers/microdot.py | 582 (provenance only, per partition note) | 2 |
| python/CommonDrivers/system_service.py | 6 (+92) | 5 |
| python/IndividualDrivers/asy_bmp3xx_driver.py | 81 (+358) | 8 |
| python/IndividualDrivers/asy_fram_driver.py | 38 (+158) | 5 |
| python/IndividualDrivers/asy_fram_manager.py | 25 (+349) | 7 |
| python/IndividualDrivers/asy_i2c_driver.py | 93 (+280) | 3 |
| python/IndividualDrivers/asy_isl29125_driver.py | 166 (+570) | 5 |
| python/IndividualDrivers/asy_mprls_driver.py | 61 (+241) | 2 |
| python/IndividualDrivers/asy_scd30_driver.py | 141 (+448) | 8 |
| python/IndividualDrivers/asy_sgp40_driver/__init__.py | 173 (+528) | 11 |
| python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py | 16 (lines 1-430 read; 430-911 is the uncommented fixed-point port, scanned only) | 4 |
| python/IndividualDrivers/asy_shtc3_driver.py | 105 (+348) | 2 |
| python/IndividualDrivers/asy_spi_driver.py | 57 (+168) | 2 |
| python/IndividualDrivers/asy_uart.py | 32 (+241) | 3 |
| python/IndividualDrivers/asy_uart_comm.py | 41 (+268) | 3 |
| python/IndividualDrivers/neopixel_signal.py | 13 (+207) | 6 |
| python/Manifest/manifest.py | 0 (+2) | 1 |
| modules/_boot.py | 2 (+16) | 3 |
| modules/sensortask-arzi.py | 32 (diffed line-by-line against wozi) | 1 |
| modules/sensortask-dev.py | 34 (+632, routes/wiring read) | 3 |
| modules/sensortask-neu.py | 32 (diffed against arzi: SPI pins only) | 1 |
| modules/sensortask-wozi.py | 32 (+613) | 24 |
| html_raw/arzi/index.html | 0 (diffed against wozi) | 0 |
| html_raw/arzi/sensorconfig.html | 0 (diffed against wozi) | 1 |
| html_raw/arzi/systemledconfig.html | 0 (diffed against wozi) | 0 |
| html_raw/dev/index.html | 0 (diffed against wozi) | 0 |
| html_raw/dev/sensorconfig.html | 0 (labels/wiring read) | 2 |
| html_raw/dev/systemledconfig.html | 0 (diffed against wozi) | 0 |
| html_raw/general/favicon.ico | binary (type/size only) | 1 |
| html_raw/general/functions.js | 12 (+113) | 4 |
| html_raw/general/nettimeconfig.html | 0 (+224) | 2 |
| html_raw/general/style.css | 0 (+98) | 0 |
| html_raw/wozi/index.html | 0 (+74) | 1 |
| html_raw/wozi/sensorconfig.html | 0 (+261) | 4 |
| html_raw/wozi/systemledconfig.html | 0 (+331) | 4 |
| build-arzi.sh | 11 (diffed against wozi) | 0 |
| build-dev.sh | 11 (+45) | 1 |
| build-neu.sh | 11 (diffed against wozi) | 1 |
| build-wozi.sh | 11 (+49) | 4 |

Also used (read-only, for dating/dedup): `git log`/`git show` on commits 8c4a73d, 2bda920, b6cb852, ba80b9d, 383d17b (legacy-tree history); `src/api_response.py:39-47`, `src/system_service.py:40-42`, `src/voc_algorithm.py:98,141`, `src/crc_checks.py:44`, `src/asy_sgp40_driver.py:581-589,685-690`, `SPECIFICATION.md:237-240,2047`, `devices/*.toml` pin blocks, `ext/freezefs/archive.py:194-240`, `BACKLOG.md:405-413`.

## Totals per kind
| kind | count |
|---|---|
| INVAR | 94 |
| LIMIT | 41 |
| SETTLED | 17 |
| RISK | 10 |
| ASSUME | 9 |
| DRIFT | 9 |
| PLATFORM | 7 |
| MIRROR | 2 |
| WORKAROUND | 1 |
| TODO | 1 |
| SUPPRESS / OPENQ | 0 (legacy suppressions are upstream `pylint:` pragmas, not project gates; not recorded per partition note) |
| **total** | **191** (all area PAR) |

## Top 10
1. RISK `modules/sensortask-wozi.py:316-321` — trailing commas make SCD30 readbacks 1-tuples, so legacy wrote MeasInt/AmbPres/Altitude/ForceCalRef/SelfCal to NVM on every non-empty PUT value; changes the premise of `PAR.S02`/`SENS.T07` (same in arzi/neu `:277-281`).
2. RISK `python/IndividualDrivers/asy_sgp40_driver/__init__.py:339,341-352` — the legacy general-call reset never ran (un-awaited, and aimed at 0x59 not 0x00); the refactor's bus-wide broadcast (SPECIFICATION.md:2047) is new field behaviour, not parity.
3. DRIFT `python/IndividualDrivers/asy_bmp3xx_driver.py:56-59` (+ `modules/sensortask-wozi.py:373`, `html_raw/wozi/sensorconfig.html:142`, `build-*.sh:1-3,40`) — the legacy tree at HEAD was edited after the initial commit (2bda920, b6cb852), so it is not what fielded wozi runs; feeds `PAR.T15`.
4. RISK `python/CommonDrivers/async_manager.py:115-129` (+ `:126-127,178-179`) — legacy wipes all of `config.json` to defaults on any missing key or bad JSON, and writes non-atomically.
5. RISK `python/CommonDrivers/async_connect.py:347-362` (+ `:183-192`) — legacy origin of permanent WLAN deactivation (second failure streak, or an invalid config read at task start).
6. MIRROR `python/IndividualDrivers/asy_sgp40_driver/voc_algorithm.py:91-164` — legacy VOC state is "31q"/248 B vs src "32q"; not interchangeable across reflash or rollback (`PAR.S09`, `PAR.T14`).
7. RISK `modules/_boot.py:4-12` — legacy formats littlefs on any mount exception; the key fact for a 1.29 → 1.26 rollback (`PAR.T14`, `PAR.S10`).
8. RISK `modules/sensortask-wozi.py:570-573,585-608` — `all_running` never recovers: failed `fram.setup()` or a persistently failing sensor reboot-loops the unit (`PAR.S12`, `PAR.S04`).
9. INVAR `python/CommonDrivers/api_helpers.py:160-183` + `:33,42-45` — legacy error codes 0-10 and `""` = "Unchanged" semantics vs `src/api_response.py`'s 0-5/100 (`PAR.T11`, `NET.S17`).
10. LIMIT `python/IndividualDrivers/asy_fram_manager.py:279-329` (+ `:219-223`) — legacy reads rewrite status bytes and treat BUSY/mismatched copies as invalid; decides what a rollback does with the refactor's FRAM layout (`PAR.T14`).
