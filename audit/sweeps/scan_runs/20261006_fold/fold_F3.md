# Fold F3: M_SRC_NET.md and M_WEB.md (phase 1, source side)

Format: `SF-xx | M-ID (part N) | file | unit kept | test/SPEC/bench carriers needed`.

## Folded

SF-A08 | M.SRC_NET.007 (1) | src/asy_captive_dns.py | U31 kept (row U18; lands in the U18 stage) | SPEC F.5/C.7.2 sentence on the 4-datagram lwIP queue (M_SPEC); a 5+ datagram burst case in the idle-rate measurement on the twin (M.TWIN.144) and bench (M.PROC.038); L1 drain-without-sleep case (M_TEST_UNIT)
SF-B15 | M.SRC_NET.023 (1) | src/asy_dns_client.py | U18 | L1 resolver test with a 513-byte reply (warning, next server tried) (M_TEST_UNIT); catalog row `_WRN_DNS_REPLY_TRUNCATED` (M.GEN.034)
SF-A12 | M.SRC_NET.027 (1), M.SRC_NET.028 (1), M.SRC_NET.030 (1) | src/asy_udp_socket.py | U31 / U18 / U28 kept (row U18, U30; lands in the U18 stage) | L1 injected MemoryError in each arm asserting the printed "memory allocation failed" text and the unchanged sentinel (M_TEST_UNIT; the injection text must avoid the gate wording, CLAUDE.md); memory gates themselves unchanged
SF-B6 | M.SRC_NET.081 (1), M.SRC_NET.093 (1), M.SRC_NET.077 (1) | src/asy_wifi_service.py | U31 / U18 / U31 kept (row U18) | L1 raising `status("stations")`: timer state unchanged, one warning per failure (M_TEST_UNIT); twin stations-query fault (M_TWIN); catalog row (M.GEN.034)
SF-B7 | M.SRC_NET.101 (1), M.SRC_NET.077 (1) | src/asy_wifi_service.py | U18 | L1 raising `status()` in the uptime loop: snapshot, uptime and link flag kept, warning counted (M_TEST_UNIT); catalog row (M.GEN.034)
SF-M2-01 | M.SRC_NET.088 (1) | src/asy_wifi_service.py | U18 (row U18, U20) | L1 empty SSID after the hotspot ran once returns to hotspot, never DEACTIVATED (M_TEST_UNIT); twin factory-state unit over two hotspot windows (M_TWIN); SPEC A.4/E.6.4 wording (M_SPEC, U36); owner-review list entry; BACKLOG owner question on non-credential identity PUTs (not folded, owner question)
SF-M2-02 | M.SRC_NET.053 (1) | src/asy_ntp_client.py | U18 (row U18, U22) | L1 `cettime()` answers past the staleness bound once the clock was set, `None` before (M_TEST_UNIT); notification alert continues after `Synced` goes false (M_TEST_UNIT/M_TWIN); owner-review list entry
SF-M2-03 (+ by-mode M4-05) | M.SRC_NET.088 (2), M.SRC_NET.089 (1), M.SRC_NET.077 (1) | src/asy_wifi_service.py | U18 / U31 kept (row U18) | L1 persisted entries for hotspot fallback, deactivation and a NOIP/timeout poll (M_TEST_UNIT); twin DHCP-never-answers case (M_TWIN); three catalog rows (M.GEN.034)
SF-M2-04 (visibility part only) | M.SRC_NET.087 (1), M.SRC_NET.078 (1), M.SRC_NET.077 (1) | src/asy_wifi_service.py | U31 kept (row U18, U22; lands in the U18 stage) | L1 pattern swaps on client join/leave, no restart while unchanged, silent with LEDWifiOn off (M_TEST_UNIT); SPEC A.4/LED pattern table and DEVICE_REFERENCE (M_SPEC/M_DOCS); the hold-bound owner question stays in BACKLOG
SF-M2-05 | M.SRC_NET.118 (1), M.SRC_NET.127 (1) | src/asy_webserver_service.py | U31 kept (row U19; lands in the U19 stage) | L1 writer raising ECONNRESET mid-response counts one HTTPDropped and one W48 (M_TEST_UNIT); twin client closing mid-response (M_TWIN)
SF-M4-01 (part (b) only) | M.SRC_NET.119 (1), M.SRC_NET.110 (1) | src/asy_webserver_service.py | U19 | L1 handler exception at DebugLevel 0 prints nothing from Microdot and still logs through the catch-all (M_TEST_UNIT); memory-gate check that a handler MemoryError stays visible; owner-review list entry (vendoring rule)
SF-M3-07 | M.SRC_NET.171 (1) | src/asy_uart_comm.py | U11 kept (row U17) | L1 ResetErrors after valid frames then two noisy resyncs: no E89 (M_TEST_UNIT); UART changelog Class B line (M_DOCS)
SF-A06 | M.SRC_NET.221 (7) | src/asy_uart_driver.py | U13 | L1 planted FE and BE (M.TEST_UNIT.344); twin register model gains FE/BE bits (M.TWIN.169); bench FE case incl. whether DMA reads update UARTRSR (M.HW_DEV.160, phase C); UART changelog Class A (M_DOCS)
SF-B14 (page half) | M.WEB.016 (1), M.WEB.001 (1) | js/templates.js, js/api-contract.js | U36 / U23 kept (row U11, U23; lands in the U23 stage) | templates test at 65535 shows "65535+" (M.WEB.058); `tests_scripts/test_js_api_mirrors.py` pins `ERR_COUNT_CAP` (M_TSC); SPEC H.6 errcount sentence (M_SPEC)
SF-B8 (page half) | M.WEB.014 (1), M.WEB.015 (1) | js/templates.js | U23 kept (row U19, U23) | template/render tests with a `/sensors` entry sent as the marker (M.WEB.058/.054); firmware half must emit the marker in place of the field map (M_SRC_CORE/M_SRC_SENS fold) or the page will not match
SF-M2-06 | M.WEB.021 (1) | js/render.js | U24 kept (row U23; lands in the U23 stage) | render test: stale baseline toggle refreshed before collect, PUT sent (M.WEB.054); live matrix unaffected (M.WEB.061 check)

Not SF rows but in my files (register "A-C delta before U18", dependency refresh family (g)); folded with the label
"(A-C fold, dependency refresh family (g), micropython-lib `<commit>`, 2026-10-06)" so the lead can strip them if this
pass was meant for SF rows only:

U18 NTP 44-47 B | M.SRC_NET.049 (1) | src/asy_ntp_client.py | U18 | `tests/test_asy_ntp_client.py` `_truncated(44)` pin inverts, a 47-byte case added (M_TEST_UNIT)
U18 NTP zero timestamp | M.SRC_NET.049 (2) | src/asy_ntp_client.py | U18 | L1 zero transmit timestamp with stratum 2 rejected, RTC untouched (M_TEST_UNIT)

## In scope but not folded

- SF-A01, SF-A02 (I2C NACK / register-address NACK): the site `src/asy_i2c_driver.py` lives in M_SRC_SENS.md
  (`## src/asy_i2c_driver.py`), not in M_SRC_NET; not mine.
- SF-B16 (UART declined vs lost): no M entry change; post-audit C-reconciliation item under the wire freeze
  (owner, 2026-09-25).
- SF-A07, SF-M4-09 (timing-budget rows), SF-A03, SF-A09 (SPEC sentences), SF-A08's and SF-M4-01 (c)/(d)'s SPEC
  sentences: M_SPEC, not mine.
- SF-M4-01 (a) (`set_exception_handler` in `start_tasks()`): M_SRC_CORE.
- SF-M3-09 (WS2812 overlay refresh), SF-B17 (notification inactive state), SF-B2: notification/neopixel sites in
  M_SRC_SENS.
- SF-B8 firmware half, SF-B14 firmware decision, SF-B3/SF-M1-07 (`unpersisted` beside `ConfigFaults`): M_SRC_CORE (the
  page renders `ConfigFaults` and any generated key generically, so no M_WEB change is needed for them).
