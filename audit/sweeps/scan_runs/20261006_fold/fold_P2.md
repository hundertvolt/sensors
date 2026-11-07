# Fold P2 (M_SPEC, M_HW_DEV, M_HW_BENCH, M_DOCS), phase 2, 2026-10-06

116 parts in 72 entries: M_SPEC 72 parts / 36 entries, M_DOCS 12 / 10, M_HW_DEV 13 / 11, M_HW_BENCH 19 / 13.
Each part is `(N) (A-C fold, silent-failure scan SF-xx, 2026-10-06) …` in the entry's Change slot, after its last
part. Every SPEC/README/BACKLOG sentence quoted in a part cites no audit ID. Hardware parts are checks written now and
run in phase C only.

Format: `SF-xx | M-ID (part N) | file | unit | pins <source M-ID part>` ("states" for doc text that describes the source
change; "measures" for a phase-C measurement with no source part).

## SPEC (SPECIFICATION.md)

SF-B1, SF-B12, SF-M1-03 | M.SPEC.010 (12) | SPECIFICATION.md A.4 FRAM bullet | U36 (stage U16) | states M.SRC_CORE.091 (1)-(2), .092 (1), .065 (1)
SF-B10 = SF-A04 | M.SPEC.011 (5) | A.4 SCD30 not-ready bullet | U15 | states M.SRC_SENS.055 (1)
SF-M3-03 | M.SPEC.011 (6) | A.4 SCD30 read-timing bullet | U15 | no source part (fact only)
SF-M3-05 | M.SPEC.012 (1) | A.4 SGP40 bullet | U15 (stage U16) | states M.SRC_SENS.063 (2)
SF-M3-01 (SGP40) | M.SPEC.012 (2) | A.4 SGP40 bullet | U15 | states M.SRC_SENS.064 (1)
SF-B9 = SF-A05 | M.SPEC.013 (1) | A.4 BMP3XX recovery bullet | U15 | states M.SRC_SENS.043 (1), .048 (1)
SF-B17 | M.SPEC.014 (1) | A.4 NeoPixel/notification bullet | U22 | states M.SRC_SENS.037 (1), .035 (2)
SF-B2 | M.SPEC.014 (2) | A.4 NeoPixel/notification bullet | U22 | states M.SRC_SENS.034 (1)
SF-M3-09 (LED) | M.SPEC.014 (3) | A.4 NeoPixel/notification bullet | U22 | states M.SRC_SENS.025 (1)
SF-M3-01 (notification) | M.SPEC.014 (4) | A.4 NeoPixel/notification bullet | U22 | states M.SRC_SENS.035 (1)
SF-M2-02 | M.SPEC.014 (5) | A.4 notification window | U22 | states M.SRC_NET.053 (1)
SF-M2-01 | M.SPEC.017 (1) | A.4 Wi-Fi state machine | U18 | states M.SRC_NET.088 (1)
SF-M2-03 | M.SPEC.017 (2) | A.4 Wi-Fi state machine | U18 | states M.SRC_NET.088 (2), .089 (1)
SF-M2-04 | M.SPEC.017 (3) | A.4 Wi-Fi state machine | U18 | states M.SRC_NET.087 (1)
SF-B6, SF-B7 | M.SPEC.017 (4) | A.4 Wi-Fi state machine | U18 | states M.SRC_NET.093 (1), .101 (1)
SF-A09 | M.SPEC.017 (5) | A.4 Wi-Fi state machine (DHCP pool) | U18 | no source part (fact only)
SF-M4-01 (b) | M.SPEC.018 (12) | A.5 print_exception bullet | U19 | states M.SRC_NET.119 (1)
SF-M2-05 | M.SPEC.018 (13) | A.5 response-writing gap | U19 | states M.SRC_NET.118 (1)
SF-M4-01 (a), (c), (d) | M.SPEC.018 (14) | A.5 console bullet (incl. persisted-DebugLevel exits) | U19 | states M.SRC_CORE.016 (1), M.SRC_NET.119 (1)
SF-A14 | M.SPEC.020 (16) | A.7 boot entry | U20 | states M.GEN.001 (1)
SF-A14 | M.SPEC.021 (10) | A.8 ResetReason table, code 21 | U36 (stage U20) | states M.SRC_CORE.006 (2), M.GEN.034 (1)
SF-A10 | M.SPEC.021 (11) | A.8 `/status` ResetBits | U36 (stage U20) | states M.SRC_CORE.006 (1), M.GEN.008 (2), M.GEN.014 (2)
SF-B3, SF-M1-07 | M.SPEC.021 (12) | A.8 `/status` ConfigUnpersisted | U36 (stage U20) | states M.SRC_CORE.044 (1), .043 (2), .015 (1), M.GEN.008 (1)
SF-M1-04 | M.SPEC.021 (13) | A.8 ConfigFaults | U36 (stage U20) | states M.SRC_CORE.043 (1)
SF-M2-05 | M.SPEC.021 (14) | A.8 HTTPDropped | U36 (stage U19) | states M.SRC_NET.118 (1), .127 (1)
SF-B5, SF-M1-06 | M.SPEC.021 (15) | A.8 BootSignature | U36 | states M.SRC_CORE.013 (1)
SF-A11 | M.SPEC.021 (16) | A.8 mempause | U36 | states M.SRC_CORE.012 (1)
SF-M4-07 | M.SPEC.035 (8) | B.11 image record | U27 | states M.SCR.067 (1)
U36 chroot row (Node) | M.SPEC.045 (1) | B.17 recipe | U36 | no source part
U36 chroot row (git ls-files) | M.SPEC.045 (2) | B.17 recipe | U36 | no source part
SF-B1 | M.SPEC.049 (4) | C.3.1 FRAM API (`owner=`) | U16 | states M.SRC_CORE.091 (1), M.SRC_SENS.062 (1)
SF-M4-10 | M.SPEC.049 (5) | C.3.1 CS at power-off | U16 (phase-C result) | no source part (fact; bench M.HW_BENCH.101 (6))
SF-A06 (+ OE half of M.SRC_NET.221 (6)) | M.SPEC.050 (8) | C.3.2 UARTRSR OE/FE/BE | U13 | states M.SRC_NET.221 (6)-(7)
SF-B8 | M.SPEC.057 (1) | C.6 unavailable marker (modules and SYSTEM) | U19 | states M.SRC_CORE.038 (1), .017 (2), M.SRC_SENS.047/.053/.082 (1)
SF-B1 | M.SPEC.058 (12) | C.7 reflash pitfall | U16 | states M.SRC_CORE.091 (1)
SF-B12, SF-M1-03 | M.SPEC.058 (13) | C.7 RAM-only entries | U16 | states M.SRC_CORE.065 (1), .092 (1)
SF-B6, SF-B7, SF-M2-03 | M.SPEC.058 (14) | C.7 WIFI observation rule | U18 | states M.SRC_NET.093 (1), .101 (1), .088 (2), .089 (1)
SF-A12, SF-M3-06 | M.SPEC.059 (3) | C.7.1 no-logging layers print MemoryError text | U18 | states M.SRC_NET.027/.028/.030 (1), M.SRC_CORE.027 (1)
SF-B3, SF-M1-07 | M.SPEC.061 (5) | C.7.3 ConfigUnpersisted | U20 | states M.SRC_CORE.044 (1), .043 (2)
SF-M1-01 | M.SPEC.061 (6) | C.7.3 CONFIG_LOST | U11 | states M.SRC_CORE.017 (1), .043 (3), .065 (2)
SF-M1-04 | M.SPEC.061 (7) | C.7.3 directory path | U11 | states M.SRC_CORE.043 (1)
SF-A08 | M.SPEC.063 (1) | C.7.5 lwIP 4-datagram queue | U18 | states M.SRC_NET.007 (1)
SF-A11, SF-B4 | M.SPEC.066 (5) | C.9 one-shot list: the unpause deadline | U11 | states M.SRC_CORE.012 (1)
SF-B5, SF-M1-06 | M.SPEC.066 (6) | C.9 failed-arm rule, uptime exception | U11 | states M.SRC_CORE.013 (1)
SF-M4-06 | M.SPEC.079 (5) | E.3.1 retry text | U27 | states M.SCR.040 (1)
SF-A11 | M.SPEC.090 (4) | F.1 soft-Timer drop fact | U11 | states M.SRC_CORE.012 (1)
SF-M4-01 (a) | M.SPEC.093 (6) | F.1 asyncio list | U14 | states M.SRC_CORE.016 (1)
SF-M4-01 (c) | M.SPEC.093 (7) | F.1 CYW43 console-only faults | U14 | no source part (fact only)
SF-A07 | M.SPEC.097 (iv) | F.3 consumer row `con.uart_tx` | U31 (cell phase C) | no source part (measured by M.HW_DEV.160 (5))
SF-M4-09 | M.SPEC.097 (v) | F.3 budget row `stall.wlan_switch` | U31 (cell phase C) | no source part (measured by M.HW_BENCH.071 (1))
SF-A01 | M.SPEC.100 (1) | F.5.1 short ACK count | U13 | states M.SRC_SENS.011 (1), .012 (1)
SF-A02 | M.SPEC.100 (2) | F.5.1 readfrom_mem_into silent return | U13 | states M.SRC_SENS.011 (2)
SF-A03 | M.SPEC.100 (3) | F.5.1 abort cause not readable | U13 | states M.SRC_SENS.012 (2) (no code)
SF-A10 | M.SPEC.103 (1) | F.5.4 raw reset flags | U14 (stage U20) | states M.SRC_CORE.006 (1)
SF-M1-05 | M.SPEC.103 (2) | F.5.4 bootloader record outcome | phase C | no source part (bench M.HW_BENCH.083 (3))
SF-A open point (RUN pin) | M.SPEC.103 (3) | F.5.4 mem_backup across RUN reset | phase C | no source part (bench M.HW_BENCH.102 (7))
SF-M4-08 | M.SPEC.107 (8) | F.7 number-model rows | U35 | no source part (the scratch run is M.PROC's)
SF-M2-06 | M.SPEC.116 (1) | H.4 sparse-PUT row | U36 | states M.WEB.021 (1)
SF-B14 | M.SPEC.119 (1) | H.6 errcount "65535+" | U36 | states M.WEB.016 (1), M.SRC_CORE.063 (2)
SF-B8 (page) | M.SPEC.119 (2) | H.6 "unavailable" field caption | U36 | states M.WEB.014 (1), .015 (1)
SF-B8 | M.SPEC.120 (1) | H.6.1 row 11, the marker | U36 | states M.SRC_CORE.038 (1), M.WEB.001
SF-B14 | M.SPEC.120 (2) | H.6.1 row 12, the counter cap | U36 | states M.WEB.001 (1)
SF-M2-05 | M.SPEC.121 (12) | H.7 drop sentence | U19 | states M.SRC_NET.118 (1), .127 (1)
SF-A12, SF-M3-06, SF-B12, SF-M4-01 (a) | M.SPEC.129 (6) | I.4(e) loggerless prints; gated tiers at DebugLevel ≥ 1 | U30 | states M.SRC_NET.027/.028/.030 (1), M.SRC_CORE.027 (1), .063 (1), .016 (1)
SF-M3-07 | M.SPEC.136 (9) | J.6 diagnostic and ResetErrors | U17 | states M.SRC_NET.171 (1)
SF-A06 | M.SPEC.137 (8) | J.7 tier map FE/BE rows | U13 / U26 (L3 cell phase C) | states M.SRC_NET.221 (7)
SF-M3-03, SF-M3-02 (SCD30) | M.SPEC.151 (7) | M.2 soft reset vs ASC; READ_RANGE | U15 | states M.SRC_SENS.055 (2)
SF-M3-09 (SGP40) | M.SPEC.151 (8) | M.3 no reset detector | U15 | no source part (fact only)
SF-B9, SF-M3-02 (BMP3XX) | M.SPEC.151 (9) | M.4 EVENT/ERR_REG; READ_RANGE | U15 | states M.SRC_SENS.048 (1), .043 (1)-(2)
SF-B11 | M.SPEC.154 (6) | M.1.5 calibration timeout | U15 | states M.SRC_SENS.081 (1)
SF-M3-04 | M.SPEC.154 (7) | M.1.3 per-cycle comparison | U15 | states M.SRC_SENS.077 (1)
SF-M3-01, SF-M3-09, SF-M2-04 | M.SPEC.156 (9) | Part N rows (`sgp40.comp_max_age_s`, `notify.sample_max_age_s`, `led.overlay_refresh_ms`, the hotspot-client LED pair) | U15 / U22 / U18 | states M.SRC_SENS.064 (1), .035 (1), .025 (1), M.SRC_NET.077 (1)

## Docs (UART_C_PORT_CHANGELOG.md, DEVICE_REFERENCE.md, BACKLOG.md)

SF-A06 | M.DOCS.019 (1) | UART_C_PORT_CHANGELOG.md Class A order to A16 | U13 | states M.SRC_NET.221 (7)
SF-A06 (+ OE half of M.SRC_NET.221 (6)) | M.DOCS.022 (1) | UART_C_PORT_CHANGELOG.md Class A row A16 | U13 | states M.SRC_NET.221 (6)-(7)
SF-M3-07 | M.DOCS.024 (1) | UART_C_PORT_CHANGELOG.md Class B row (no C impact) | U11 | states M.SRC_NET.171 (1)
SF-B3, SF-M1-07, SF-M1-01 | M.DOCS.026 (1) | DEVICE_REFERENCE.md commissioning: Config Unpersisted, config-lost warning | U36 | states M.SRC_CORE.044 (1), .017 (1)
SF-M2-04 | M.DOCS.027 (1) | DEVICE_REFERENCE.md LED overlay: hotspot-client blink | U36 (stage U18) | states M.SRC_NET.087 (1)
SF-M3-09 (LED) | M.DOCS.027 (2) | DEVICE_REFERENCE.md overlay refresh | U36 | states M.SRC_SENS.025 (1)
SF-B17, SF-M3-01, SF-M2-02, SF-B2 | M.DOCS.027 (3) | DEVICE_REFERENCE.md notification State, stale values, window, dropped flash | U36 | states M.SRC_SENS.037 (1), .035 (1)-(2), .034 (1), M.SRC_NET.053 (1)
SF-B6, SF-B7, SF-M2-03 | M.DOCS.028 (1) | DEVICE_REFERENCE.md networking status | U18 | states M.SRC_NET.093 (1), .101 (1), .088 (2), .089 (1)
SF-M1-02, SF-M3-05 | M.DOCS.030 (1) | DEVICE_REFERENCE.md SGP40 restore rules | U16 | states M.SRC_SENS.063 (1)-(2)
all phase-C rows | M.DOCS.064 (f) | BACKLOG.md "Real-hardware work still owed" | U37 (rows with their instruments) | measures (rows for every phase-C check below)
SF-M4-06, SF-M4-07 | M.DOCS.066 (1) | BACKLOG.md chroot list, U27 paragraph | U27 | states M.SCR.040 (1), M.SCR.067 (1)
SF-M2-01, SF-M2-04 | M.DOCS.067 (1) | BACKLOG.md owner-question list (two entries) | U18 | owner questions the source parts leave open (M.SRC_NET.088 (1), .087 (1))

## L3 flash tier (tests_hardware/flash, device_scripts)

SF-M4-01 (a) | M.HW_DEV.025 (1) | tests_hardware/flash/test_task_supervisor.py | U26 (phase C) | pins M.SRC_CORE.016 (1)
SF-M4-01 (a) | M.HW_DEV.026 (1) | device_scripts/system_service_restarts_a_real_dead_task.py (`level`, `hold_console`) | U26 (phase C) | pins M.SRC_CORE.016 (1)
SF-A11, SF-B4 | M.HW_DEV.068 (7) | device_scripts/fram_pause_unpause_and_gating.py | U26 (call shape in U11) | pins M.SRC_CORE.012 (1)
SF-A01, SF-A02, SF-B9, SF-M3-04 | M.HW_DEV.080 (9) | tests_hardware/flash/test_bus_concurrency.py | U26 (phase C) | pins M.SRC_SENS.011 (1)-(2), .012 (1), .048 (1), .077 (1)
SF-A01, SF-A02, SF-B9, SF-M3-04 | M.HW_DEV.090 (1) | device_scripts/bus_topology_autodetect_and_hazard_sweep.py | U26 (phase C) | pins the same
SF-A open points (FRAM MISO, SCD30 pointer) | M.HW_DEV.131 (1) | tests_hardware/flash/test_chip_conformance.py | U26 (phase C) | measures
SF-A open point (FRAM MISO pull-up) | M.HW_DEV.132 (1) | device_scripts/fram_conformance_probe.py | U26 (phase C) | measures
SF-A open point (mem_backup across RUN) | M.HW_DEV.154 (5) | device_scripts/reset_code_invalid_record.py (`valid_record_wait`) | phase C | measures
SF-A open point (SCD30 pointer cut short) | M.HW_DEV.156 (1) | device_scripts/scd30_argument_reaction.py | phase C | measures
SF-A open point (SCD30 NVM write cut) | M.HW_DEV.156 (2) | device_scripts/scd30_argument_reaction.py (`interval_write_loop`) | phase C | measures (manual step, ≤ 21 SCD30 NVM writes behind `confirm()`)
SF-A06, SF-A07 | M.HW_DEV.159 (1) | device_scripts/uart_dma_ring_interrupts_off.py (`break`, `config_write_link`) | U26 (phase C) | pins M.SRC_NET.221 (7); measures SF-A07
SF-A06 | M.HW_DEV.160 (4) | tests_hardware/flash/test_uart_crossover.py (break mid-frame; DMA vs UARTRSR) | U26 (phase C) | pins M.SRC_NET.221 (7)
SF-A07 | M.HW_DEV.160 (5) | tests_hardware/flash/test_uart_crossover.py (`persistence_write`, 5 flash writes) | U26 (phase C) | measures

## L4 bench tier (tests_hardware/bench, manual, README)

SF-M3-08 | M.HW_BENCH.006 (4) | tests_hardware/conftest.py session start (VL805 version note) | U26 | measures
SF-M4-01 | M.HW_BENCH.012 (1) | tests_hardware/harness.py `hold_unread_s` | U26 | helper for M.HW_BENCH.083 (4)
SF-A01, SF-A02, SF-B9, SF-M3-02, SF-M3-04 | M.HW_BENCH.064 (1) | bench/test_bus_concurrency_under_api_load.py | U26 (phase C) | pins M.SRC_SENS.011 (1)-(2), .012 (1), .043 (1)-(2), .048 (1), .055 (2), .077 (1)
SF-M4-09 | M.HW_BENCH.071 (1) | bench/test_hotspot_role_reversal.py (link across the mode switch) | U26 (phase C, R1) | measures
SF-A open point (CYW43 under flash stall) | M.HW_BENCH.082 (4) | bench/test_network_resilience.py (`persistence_write`, 2 flash writes) | U26 (phase C, R3) | measures
SF-A14 | M.HW_BENCH.083 (1) | bench/test_reset_reasons.py (Ctrl-C → 21) | U26 (phase C) | pins M.GEN.001 (1), M.SRC_CORE.006 (2)
SF-A10 | M.HW_BENCH.083 (2) | bench/test_reset_reasons.py (ResetBits per kind) | U26 (phase C) | pins M.SRC_CORE.006 (1)
SF-M1-05 | M.HW_BENCH.083 (3) | bench/test_reset_reasons.py (bootloader record) | U26 (phase C) | measures
SF-M4-01 (a) | M.HW_BENCH.083 (4) | bench/test_reset_reasons.py (crash loop, non-reading host → 5) | U26 (phase C) | pins M.SRC_CORE.016 (1)
SF-M4-10 | M.HW_BENCH.101 (6) | manual/manual_bus_electrical.py (CS at power-off, scope only) | U26 (phase C, R2) | measures
SF-A10 | M.HW_BENCH.102 (5) | manual/manual_persistence.py (ResetBits after power cycles) | U26 (phase C, R2) | pins M.SRC_CORE.006 (1)
SF-A open point (SCD30 NVM write cut) | M.HW_BENCH.102 (6) | manual/manual_persistence.py (≤ 21 SCD30 NVM writes, `confirm()`) | U26 (phase C, R2) | measures
SF-A open point (mem_backup across RUN) | M.HW_BENCH.102 (7) | manual/manual_persistence.py (RUN-pin step) | U26 (phase C, R2) | measures
SF-A14, SF-A10 | M.HW_BENCH.119 (1) | tests_hardware/README.md reset-code table | U26 | states M.SRC_CORE.006 (1)-(2)
SF-M3-08 | M.HW_BENCH.125 (1) | tests_hardware/README.md Prerequisites (RP2040-E15) | U26 | no source part
SF-M4-11 | M.HW_BENCH.127 (1) | tests_hardware/README.md Bench traps (511-byte Ctrl-C) | U26 | no source part
SF-A14 | M.HW_BENCH.127 (2) | tests_hardware/README.md Bench traps (Ctrl-C ends the loop) | U26 | states M.GEN.001 (1)
SF-A07, SF-A open points | M.HW_BENCH.130 (1) | tests_hardware/README.md wear budget rows | U26 | measures (budget for .082 (4), M.HW_DEV.160 (5), .102 (6))
SF-A open points, SF-M1-05, SF-M3-03, SF-M4-10 | M.HW_BENCH.131 (1) | tests_hardware/README.md open findings | U26 | measures (one bullet per open point, removed at its round's delta)

## Needs a new entry

- `src/asy_sgp40_driver.py:1-8` (module docstring; SF-M3-09's "and the SGP40 header" half): no M entry covers it
  (M.SRC_SENS.058 starts at `:10`; F2 noted the same). Proposed: a new M_SRC_SENS entry, unit U15, "the header's last
  line states that the SGP40 has no status register, so a self-reset cannot be read (SPECIFICATION.md M.3)", within the
  3-line header cap. Not in my files; for the lead.
- None in my four files: every carrier found an existing entry.

## Source parts with no test carrier

None found at the time of this pass (grep of every SF row in M_TEST_UNIT, M_TEST_HELP, M_TSC, M_TWIN, M_WEB, M_HW_DEV,
M_HW_BENCH; P1 was still writing): each folded SF row has at least one test carrier. Rows whose only carrier is a
measurement by design: SF-A03, SF-A07, SF-A09, SF-M3-03, SF-M4-08, SF-M4-09, SF-M4-10, SF-M1-05 (no source part).

## Out of my files, noted for the lead

- SF-B13's README carriers ("FRAM persistence", "SCD30 persistence") are `digital_twin/README.md`, which M_TWIN covers
  (M.TWIN.060/.062), not M_DOCS: P1's file.
- The register's U36 chroot rows cite "A.U1.05 (the recipe's move)"; A.U1.05 is the bench bridge recipe
  (M.HW_BENCH.112). The chroot recipe moves to SPEC B.17 at U36 (M.SPEC.045, M.DOCS.106), so both rows are folded
  into M.SPEC.045, not M.DOCS.047/M.HW_BENCH.112.
- M.SRC_NET.221 (6) (OR146, the OE half) had no SPEC and no UART-changelog carrier; M.SPEC.050 (8) and M.DOCS.022 (1)
  (row A16) carry it together with SF-A06's FE/BE.
- C.7.1 (M.SPEC.059) holds the band table only after U2, so the "C.7.1 row" carriers phase 1 named for SF-B2, B9, B10,
  B11, M3-02 need no SPEC row; each code's text is its M.GEN.034 catalog row. Several of those codes (the five WIFI
  warnings, `NOTIFY_SIGNAL_DROPPED`, `ISL_CAL_TIMEOUT`, `BMP_CHIP_RESET`, `SCD_NOT_READY`, `READ_RANGE`,
  `DNS_REPLY_TRUNCATED`) rely on M.GEN.034's general "every new constant has its row" rule; only FRAM_FULL, LOG_RAM_ONLY,
  CONFIG_LOST and ResetReason 21 are listed by name in M.GEN.034 (1).
- The SF-M3-08 premise is partly covered already: at v1.29.0 the rp2 build compiles TinyUSB's RP2040-E15 workaround in
  (`lib/pico-sdk/src/rp2_common/tinyusb/CMakeLists.txt:39` sets `PICO_RP2040_USB_DEVICE_UFRAME_FIX=1`;
  `lib/tinyusb/src/portable/raspberrypi/rp2040/rp2040_usb.h:34-35`; present in the cached build's `flags.make`). So the
  VL805 check warns and records, never fails (M.HW_BENCH.006 (4), .125 (1)).

## Decisions taken on the owner's behalf (agent, 2026-10-06), for review

- SF-M4-10: the power-off CS check is written as a scope-only manual step that records "not measured" without a scope,
  and C.3.1 gains a power-off residual sentence. AC_NOTES 23 dropped a "scope CS" item earlier on AC_NOTES 11's
  power-on grounds; the power-off edge (tpd) is not covered by that reasoning. If the lead holds the drop to cover
  power-off too, M.SPEC.049 (5), M.HW_BENCH.101 (6) and the R2 row in M.DOCS.064 (f) go together.
- SF-M3-03: no bench check is specified (the Interface Description offers no ASC progress readout); the fact goes to
  SPEC A.4 and M.2, the open point to the README's open findings, and the boot-reset question to the owner-review list
  (M.PROC, not mine).
- SF-M4-01 bench form: the non-reading host is tested through the escalation script (`hold_console`, level 0) and
  `mpremote run --no-follow` plus an unread DTR-held port, asserting code 5 not 2. The L3 restart test also asserts no
  default-handler traceback at level 0.
- SF-A open point "SCD30 NVM write cut by power loss": a manual step spending up to 21 SCD30 NVM writes behind
  `confirm()`; the owner can decline it at the step.
- SF-M2-01 / SF-M2-04 owner questions are entered in BACKLOG's owner-question list at U18 unless answered in the A-C
  review first.
- SF-A10 bench asserts only the watchdog half of `ResetBits` per reset kind; the CHIP_RESET bits are recorded, never
  asserted, since that record is what a decode would wait on.
