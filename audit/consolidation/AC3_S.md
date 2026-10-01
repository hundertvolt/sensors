# A-C3 Part S: Site trace (IN PROGRESS — working ledger, final text follows)

# notes (action | file | class | reason | amendment)
A.C.06 | tests_hardware/bench/test_uart_link_crc16.py | D-RUN | R4 runs it; created by M.HW_BENCH.094 (A.S0930.06)
A.C.10 | devices/*.toml (6) | D-DELTA | round deltas; M.PROC.036 Blast carries "TOML origin comments ... as deltas" (OR106.a)
A.C.10 | BACKLOG.md | A-FROM | M.DOCS.064 body/Unit carries phase-C removals; DOCS ledger maps A.C.10 -> M.DOCS.064; From lacks it
A.S0930.04 | tests/_field_sweep.py | D-ART | "…_field_sweep.py" abbreviates tests/test_digital_twin_uart_field_sweep.py = M.TWIN.156 (exact)
A.S0930.22 | tests/test_asy_fram_manager.py | A-RES | case (3) lands in test_system_service.py (M.TEST_UNIT.306); Resolved names only config_manager
A.S0930.26 | tests/test_sensortask_<device>.py | D-NOEDIT | wrappers register via register_for_device() (HEAD tests/test_sensortask_wozi.py:4-6); replaced at U24 by M.TEST_UNIT.337
A.S0930.29 | tests_hardware/bench/config_files_{dump,restore}.py | D-ART | bare names are device scripts: M.HW_DEV.100/.101
A.S0930.34 | tests_scripts/test_digital_twin_ci_suite_*.py | GAP | (4) deadline-helper L0 case carried nowhere -> M.TSC.165
A.S0930.35 | CLAUDE.md | D-REF | cites CLAUDE.md's nested-asyncio.run rule; no edit
A.SDEP.07 | ext/freezefs/{LICENSE,__main__,archive,ffsextract,ffsmount}.py | GAP | re-vendor of the files themselves carried by no change (M.PROC.008 (d) names only SCR/TSC/DOCS carriers) -> new GEN change beside M.GEN.051
A.SDEP.08 | audit, ext, datasheets | D-REF | grep exclusions
A.SDEP.08 | CLAUDE.md, pyproject.toml | D-RECHECK | re-read-only claims under (4); M.PROC.008 family (e) runs the full re-check; an edit only if the fact moved (delta)
A.SDEP.15 | src/asy_ntp_client.py, asy_scd30_driver.py, asy_sgp40_driver.py, system_service.py | D-READ | W10 symptom sites; only the bmp3xx/isl29125 comments are edit sites
A.SDEP.19 | toolchain/setup_toolchain.py | D-READ | W33: retries stay; reason text lives in CLAUDE.md/SPEC/action.yml, none in setup_toolchain.py
A.U0.35 | src/asy_scd30_driver.py (B03 :162-163) | A-FROM | superseded by A.U15.04's comment in M.SRC_SENS.054 (fixes the dangling pointer); From lacks A.U0.35
A.U0.38 | audit/dprov/D1.md (D1.22) | GAP | audit-file reclass carried nowhere -> M.PROC.003 (8)
A.U1.04/.05/.06 | tests_hardware/README.md | D-SECTION | carried by M.HW_BENCH.111/.112/.113 under the file's heading
A.U1.07 | dev_legacy/README.md | D-READ | source text
A.U1.11 | modules/_boot.py, modules/sensortask.py | D-REF | names in the CLAUDE.md rule text
A.U10.07 | buildgen/codegen.py | D-READ | "read-only here"
A.U10.18 | src/asy_fram_manager.py | D-NOUSE | no renamed lock name occurs in the file at HEAD (grep)
A.U10.21 | src/asy_notification_service.py | A-FROM | M.SRC_SENS.033 Change/Resolved carry setup()->bool; From lacks A.U10.21
A.U10.26 | src/asy_webserver_service.py | D-READ | "read-only: already conform"
A.U10.31 | src/asy_notification_service.py, asy_uart_link_driver.py, print_log.py | GAP | quoted annotations (HEAD 3/3/1 per A.U10.31) no carrier -> M.SRC_SENS.030, M.SRC_NET.211, M.SRC_CORE.060
A.U10.31 | src/asy_sgp40_driver.py | A-FROM | M.SRC_SENS.061 carries (_ConstValue unquoted); From lacks
A.U10.31 | src/asy_dns_client.py, asy_fram_driver.py, asy_udp_socket.py, crc_checks.py, framing_codecs.py, voc_algorithm.py | D-NOSITE | glob "every src/*.py"; A.U10.31's own count lists no quoted annotation there
A.U10.33 | src/config_manager.py, print_log.py, asy_fram_driver.py | GAP | D.15 reorder (ConfigManager; PrintLog/PrintLogHistory/PrintLogHistoryStore; FRAM_SPI) no carrier -> new SRC_CORE change(s)
A.U10.33 | src/asy_bmp3xx_driver.py, asy_neopixel_driver.py, asy_notification_service.py, asy_scd30_driver.py, asy_sgp40_driver.py | GAP | only M_SRC_SENS convention line 14; no merged change (no step) -> new SRC_SENS change
