# U18 lane D notes

## Baseline (d8ea34c) checks
- test_decision_vocabulary: allowlist_only_shrinks red (3 stale lines: web_tag.py, wifi_service.py, test_asy_wifi_service.py) - lead's
- test_citations red: SPEC 3x digital_twin/_unix_port_udp_addr_shim.py (D fixes)
- test_tunables_register red: udp.poll_wait_ms/poll_idle_ms no row; conn_tries_default/round_trip_tries_default/ready_poll_ms rows no tag (D fixes)

## Verified facts at pin (v1.29.0, lwIP 77dcd25, cyw43 055d642)
- mdns.c:2820 udp_new_ip_type; dhcp.c:279 dhcp_pcb=udp_new(); dhcpserver.c:94 udp_new(); dns.c:890; opt.h:1189 LWIP_DNS_SECURE
- dhcp.c:1388-1391 pcb_allocated -> dhcp_dec_pcb_refcount (in dhcp_release_and_stop, reached by dhcp_stop :1412) [packet said 1386-1389]
- cyw43_ctrl.c:118-127 cyw43_deinit -> tcpip_deinit both itfs; cyw43_lwip.c:251-257 dhcp_stop / dhcp_server_deinit
- LWIP_MDNS_RESPONDER 1 (lwipopts_common.h:60), MEMP_NUM_UDP_PCB (4+1) :70
- modlwip.c:1257 udp_connect; udp.c:261-311 udp_input local+remote match, else unconnected pcb [packet 262-292]
- machine_i2c.c:105-115 construction: i2c_init + gpio function + pulls, no pulses [packet 110-118]

## Marked for re-check after merges (code body still old on base)
- C.7.1 no-logging layers: asy_dns_client writes through caller's pr
- F.1 cettime gate (utc_now, fold 106(1)) - N
- C.8 hold table bounds (W 53 one step at GOT_IP; NTP 7.1/9.1 s)
- C.9 task table rows: LED flash -> _run_led_pattern() (W), captive DNS creator (W 45f), CaptiveDNS.run top (C)
- C.9 NTP rearm, WiFi tick rearm (N 31/33, W 45k/45m), wall-clock tests in NTP file (A.U18.26)
- A.4 Wi-Fi bullet (all W behaviour)
- G.2 UDP entry (two-rate ready() - U)
- F.5.9 UDP paragraph
- DR LED patterns / networking status
- Part N rows (all lanes)
- K: console() Part G row; LOG_RAM_ONLY run rule at A.4 (:222-227) and C.7 (:2145-2149); RegionBuffer bullet (:5315-5317) "and prints the error's text once through console()"
- T: BACKLOG build-env: pyproject mypy_path, typecheck.ini mypy_path, _render_coverage.py **/*.py
- F.7 row 1: every test file/twin runner patches at import (T contract) - verify after merges
- C.7.4 GET sentence + C.4.4 _cfg_overlay: W's _cfg_overlay (step 40) - verify
- C.7.5: C lane's run() drain + DNSQuery drop rules + NODATA; U's two-rate ready() - verify
- C.7 (10)/(11): every UDPSocket user persists teardown (C's captive DNS); WIFI persisted set (W 45c fold, 52, 53, 45j, 45n); resolver refusals (R 5g)
- C.7.1: resolver W16 truncation (R fold) present? console() through K
- C.7.2: Synced staleness (N 32b), PUT clears Synced (N 32a), E72 (N 5m) - verify; A.11 cite replaced by CLAUDE.md (no A.11 exists)
- C.8 hold table: W's 53 (one step at GOT_IP), 52 (60 s outside lock), 76 (_recover_device via _select_wifi_mode), uptime loop name; C 5b cancel re-raise; W 45i LED flash cancel; verify test_lock_order
- C.9: NTP _rearm_failed_timers (N 31/33) at sync trigger; WiFi tick re-arm in _connect_loop (W 45m/45k); hotspot timer E17 (W 45g); task table rows; NTP wall-clock tests
- F.1 CYW43: _STAT_JOINED_NO_IP/_PM_NO_POWERSAVE names land in W 45c - verify
- A.8 (no step; U18 makes false): /networking GET keys, /status networking snapshot, RSSI null outside STA (W 45h), UTCTime vs NTPSynced, DNSFallback fires nothing - verify
- F.5.9 UDP para: U's two-rate ready() - verify; deviation: 'bounded by the build' dropped (no TOML sets UDP rates)
- G.2: console() row and RegionBuffer console (K final); UDP entry (U)
- I.2: resolver 513 (R fold 5h(1)), captive 512 (C 5b), NTP 48 (N1 done) - verify
- A.4 Wi-Fi bullet: verify all against W final (empty SSID, client pattern 1.5/1.5, deactivated 0.1/2.9 LED gating, W79/W80/W81, unknown obs, _recover_device rung)
- DR: overlay bullet written in full end state (deviation: U36 rewrite pulled forward - HEAD 'on/off only' contradicts); verify patterns vs W final; networking status section vs W/N
- tests_hardware/README.md:1092 recv_fail_backoff_s local name (C's run() rewrite) - verify
- R final d109f9c: C.7.1 agent sentence on owner-review list (R records)
- B.15 mypy_path sentences (main + twin) updated (no step; U18 makes false)

## Silent-failure scan (docs lane; modes NET first)
- SF-D1 class 2, hotspot with clients: AP DHCP 8 leases/24 h, 9th client ignored (dhcpserver.c:234-236): documented A.4 (step 48 fold 5), accepted (agent). covered: M.SPEC.017 (5).
- SF-D2 class 2, hotspot/load (captive DNS burst): lwIP 4-datagram queue drops uncounted (modlwip.c:456-468): no Python counter possible; drain by construction; C.7.5 states it. covered: M.SPEC.063 (1).
- SF-D3 class 1, hotspot with failing chip: status("stations") returns 32 uninitialised entries if cyw43_ensure_up fails (network_cyw43.c:377-388): stated F.1; reachable only when status()==GOT_IP, which needs the chip up, so practically unreachable on the stations path; covered: M.SPEC.158.
- SF-D4 class 7, NTP stale: /status UTCTime null while LocalTime keeps answering after Synced goes stale (A-20): A.8/F.1 state it; owner-review list (lead).
- SF-D5 class 7, DNSFallback empty: website cannot send empty, API only (DR, web tag): covered by A.U18.10's U23 register line.
- SF-D6 class 6, hotspot with client: unbounded hold - owner question 1 entered (SF-M2-04).
- SF-D7 class 6, hotspot non-credential PUT: router down -> two streaks -> deactivated until power cycle: owner question 2 entered.
- (non-scan finding) BACKLOG "Mypy shall be configured to disallow Any" item stale: main pass has disallow_any_explicit = true (pyproject.toml:413) - not U18's site; report.
