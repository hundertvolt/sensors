# Fold P1 (phase 2 carriers: M_TEST_UNIT, M_TEST_HELP, M_TSC, M_TWIN test side), 2026-10-06

Each part is in the entry's `- **Change**:` slot as `(N) (A-C fold, silent-failure scan SF-xx, 2026-10-06) ...`
(refresh family (g) parts carry F3's label). Entry units are kept; the unit column gives the entry's unit and, where
the part lands elsewhere, its stage ("staged with" when the entry is earlier). `From`, `Depends`, `Blast` untouched.

SF-xx | M-ID (part N) | file | unit | pins <source M-ID part>
SF-A11 and SF-B5 | M.TEST_UNIT.301 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.008 (1)
SF-B5 and SF-M1-06 | M.TEST_UNIT.303 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.013 (1)
SF-A11 | M.TEST_UNIT.305 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.010 (1)
SF-A11 and SF-B4 | M.TEST_UNIT.307 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.012 (1), .011 (7)
SF-A11 | M.TEST_UNIT.308 (part 1) | M_TEST_UNIT | U3 entry; staged with U11 | pins M.SRC_CORE.012 (1)
SF-B3 and SF-M1-07 | M.TEST_UNIT.309 (part 1) | M_TEST_UNIT | U20 | pins M.SRC_CORE.015 (1)
SF-M4-01 (a) | M.TEST_UNIT.309 (part 2) | M_TEST_UNIT | U20 entry; stage U11 | pins M.SRC_CORE.016 (1)
SF-A10 | M.TEST_UNIT.310 (part 1) | M_TEST_UNIT | U11 entry; stage U13 | pins M.SRC_CORE.006 (1)
SF-A14 | M.TEST_UNIT.310 (part 2) | M_TEST_UNIT | U11 entry; stage U20 | pins M.SRC_CORE.006 (2)
SF-M1-01 | M.TEST_UNIT.311 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.017 (1), .005 (1), .043 (3), .065 (2)
SF-B8 (SYSTEM half) | M.TEST_UNIT.311 (part 2) | M_TEST_UNIT | U11 | pins M.SRC_CORE.017 (2)
SF-M1-07 and SF-M1-01 | M.TEST_UNIT.253 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.043 (2), (3)
SF-M1-04 | M.TEST_UNIT.254 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.043 (1)
SF-B3 | M.TEST_UNIT.257 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.044 (1)
SF-M3-06 | M.TEST_UNIT.223 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_CORE.027 (1)
SF-B8 (base half) | M.TEST_UNIT.230 (part 1) | M_TEST_UNIT | U11 entry; stage U19 | pins M.SRC_CORE.038 (1)
SF-B12 | M.TEST_UNIT.290 (part 1) | M_TEST_UNIT | U11 | pins M.SRC_CORE.063 (1)
SF-M1-03 and SF-B12 | M.TEST_UNIT.291 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_CORE.065 (1)
SF-M1-01 | M.TEST_UNIT.291 (part 2) | M_TEST_UNIT | U16 entry; staged with U11 | pins M.SRC_CORE.065 (2)
SF-B1 | M.TEST_UNIT.040 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_CORE.091 (1)
SF-B12 | M.TEST_UNIT.040 (part 2) | M_TEST_UNIT | U16 | pins M.SRC_CORE.091 (2), .092 (1)
SF-B1 and SF-B12 | M.TEST_UNIT.029 (part 1) | M_TEST_UNIT | U24 entry; stage U16 | pins M.SRC_CORE.091 (1), (2)
SF-B1 | M.TEST_UNIT.049 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_CORE.091 (1)
SF-B1 | M.TEST_UNIT.050 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_CORE.091 (1)
SF-A01 and SF-A02 | M.TEST_UNIT.053 (part 1) | M_TEST_UNIT | U13 | pins M.SRC_SENS.012 (1), .011 (1), .011 (2)
SF-A02 | M.TEST_UNIT.055 (part 1) | M_TEST_UNIT | U30 entry; stage U13 | pins M.SRC_SENS.011 (2)
SF-B9 = SF-A05 (protocol half) | M.TEST_UNIT.010 (part 1) | M_TEST_UNIT | U31 entry; stage U15 | pins M.SRC_SENS.048 (1)
SF-B9 = SF-A05 (reader half) | M.TEST_UNIT.017 (part 1) | M_TEST_UNIT | U15 | pins M.SRC_SENS.043 (1)
SF-M3-02 (BMP3XX half) | M.TEST_UNIT.017 (part 2) | M_TEST_UNIT | U15 | pins M.SRC_SENS.043 (2)
SF-B8 (BMP3XX half) | M.TEST_UNIT.016 (part 1) | M_TEST_UNIT | U35 entry; stage U19 | pins M.SRC_SENS.047 (1)
SF-A01 | M.TEST_UNIT.019 (part 1) | M_TEST_UNIT | U15 entry; stage U13 | pins M.SRC_SENS.011 (1)
SF-M3-02 (SCD30 half) | M.TEST_UNIT.116 (part 1) | M_TEST_UNIT | U15 | pins M.SRC_SENS.055 (2)
SF-B10 = SF-A04 | M.TEST_UNIT.122 (part 1) | M_TEST_UNIT | U15 | pins M.SRC_SENS.055 (1)
SF-B8 (SCD30 half) | M.TEST_UNIT.120 (part 1) | M_TEST_UNIT | U4 entry; stage U19 | pins M.SRC_SENS.053 (1)
SF-A01 and SF-A02 | M.TEST_UNIT.059 (part 1) | M_TEST_UNIT | U15 entry; stage U13 | pins M.SRC_SENS.011 (1), (2)
SF-B8 (ISL29125 half) | M.TEST_UNIT.067 (part 1) | M_TEST_UNIT | U2 entry; stage U19 | pins M.SRC_SENS.082 (1)
SF-M3-04 | M.TEST_UNIT.073 (part 1) | M_TEST_UNIT | U2 entry; stage U15 | pins M.SRC_SENS.077 (1)
SF-B11 | M.TEST_UNIT.071 (part 1) | M_TEST_UNIT | U15 | pins M.SRC_SENS.081 (1)
SF-M3-01 (SGP40 half) | M.TEST_UNIT.130 (part 1) | M_TEST_UNIT | U15 | pins M.SRC_SENS.064 (1)
SF-M3-06 (SGP40 half) | M.TEST_UNIT.131 (part 1) | M_TEST_UNIT | U15 entry; staged with U16 | pins M.SRC_SENS.063 (3)
SF-B1 and SF-B12 (SGP40 halves) | M.TEST_UNIT.136 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_SENS.062 (1)
SF-M1-02 | M.TEST_UNIT.138 (part 1) | M_TEST_UNIT | U16 | pins M.SRC_SENS.063 (1)
SF-M3-05 | M.TEST_UNIT.138 (part 2) | M_TEST_UNIT | U16 | pins M.SRC_SENS.063 (2)
SF-B17 | M.TEST_UNIT.087 (part 1) | M_TEST_UNIT | U9 entry; stage U22 | pins M.SRC_SENS.035 (2)
SF-M3-01 (notification half) | M.TEST_UNIT.087 (part 2) | M_TEST_UNIT | U9 entry; stage U22 | pins M.SRC_SENS.035 (1)
SF-B17 | M.TEST_UNIT.086 (part 1) | M_TEST_UNIT | U3 entry; stage U22 | pins M.SRC_SENS.035 (2)
SF-B17 | M.TEST_UNIT.088 (part 1) | M_TEST_UNIT | U35 entry; stage U22 | pins M.SRC_SENS.037 (1)
SF-B2 | M.TEST_UNIT.088 (part 2) | M_TEST_UNIT | U35 entry; stage U9 | pins M.SRC_SENS.034 (1)
SF-B2 | M.TEST_UNIT.277 (part 1) | M_TEST_UNIT | U9 | pins M.SRC_SENS.034 (1)
SF-M3-09 (LED half) | M.TEST_UNIT.079 (part 1) | M_TEST_UNIT | U10 entry; stage U22 | pins M.SRC_SENS.025 (1)
SF-A08 | M.TEST_UNIT.244 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.007 (1)
SF-A08 | M.TEST_UNIT.189 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.007 (1), .028
SF-A12 | M.TEST_UNIT.191 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.027 (1), .028 (1), .030 (1)
SF-B15 | M.TEST_UNIT.028 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.023 (1)
refresh (g) 9ec1830 | M.TEST_UNIT.104 (part 1) | M_TEST_UNIT | U14 entry; stage U18 | pins M.SRC_NET.049 (1)
refresh (g) 5139530 | M.TEST_UNIT.104 (part 2) | M_TEST_UNIT | U14 entry; stage U18 | pins M.SRC_NET.049 (2)
SF-M2-02 | M.TEST_UNIT.107 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.053 (1)
SF-B7 | M.TEST_UNIT.211 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.101 (1)
SF-M2-04 | M.TEST_UNIT.213 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.087 (1), .078 (1)
SF-B6 | M.TEST_UNIT.216 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.081 (1), .093 (1)
SF-M2-01 | M.TEST_UNIT.217 (part 1) | M_TEST_UNIT | U18 | pins M.SRC_NET.088 (1)
SF-M2-03 | M.TEST_UNIT.217 (part 2) | M_TEST_UNIT | U18 | pins M.SRC_NET.088 (2), .089 (1)
SF-M2-05 | M.TEST_UNIT.202 (part 1) | M_TEST_UNIT | U19 | pins M.SRC_NET.118 (1), .127 (1)
SF-M4-01 (b) | M.TEST_UNIT.208 (part 1) | M_TEST_UNIT | U19 | pins M.SRC_NET.119 (1), .110 (1)
SF-M3-07 | M.TEST_UNIT.161 (part 1) | M_TEST_UNIT | U17 entry; staged with U11 | pins M.SRC_NET.171 (1)
SF-A06 | M.TEST_UNIT.344 (part 1) | M_TEST_UNIT | U13 | pins M.SRC_NET.221 (7)
SF-A14 | M.TEST_UNIT.269 (part 1) | M_TEST_UNIT | U24 | pins M.GEN.001 (1), M.SRC_CORE.006 (2)
SF-B9 = SF-A05 and SF-M3-04 | M.TEST_UNIT.234 (part 1) | M_TEST_UNIT | U35 entry; stage U15 | pins M.SRC_SENS.048 (1), .043 (1), .077 (1)
SF-A01 and SF-A02 | M.TEST_UNIT.236 (part 1) | M_TEST_UNIT | U35 entry; stage U13 | pins M.SRC_SENS.012 (1), .011 (1), (2)
SF-A10 | M.TEST_HELP.011 (part 5) | M_TEST_HELP | stage U13 | pins M.SRC_CORE.006 (1)
SF-A01 and SF-A02 | M.TEST_HELP.013 (part 1) | M_TEST_HELP | U24 entry; stage U13 | pins M.SRC_SENS.012 (1), .011 (1), (2)
SF-A01 and SF-A02 | M.TEST_HELP.015 (part 1) | M_TEST_HELP | U24 entry; stage U13 | pins M.SRC_SENS.011 (1), (2)
SF-A06 | M.TEST_HELP.069 (part 5) | M_TEST_HELP | U13 | pins M.SRC_NET.221 (7)
SF-B9 = SF-A05 and SF-M3-04 | M.TEST_HELP.026 (part 11) | M_TEST_HELP | U24 entry; stage U15 | pins M.SRC_SENS.048 (1), .077 (1)
SF-B1 | M.TEST_HELP.036 (part 7) | M_TEST_HELP | U24 entry; stage U16 | pins M.SRC_CORE.091 (1), M.SRC_SENS.062 (1)
SF-B3, SF-M1-07, SF-A10, SF-B8, SF-B17 | M.TEST_HELP.041 (part 8) | M_TEST_HELP | U24 entry; stages U19, U20, U22 | pins M.GEN.008 (1), (2), M.SRC_CORE.038 (1), .017 (2), M.SRC_SENS.037 (1)
SF-B1 | M.TSC.092 (part 1) | M_TSC | U16 | pins M.SRC_CORE.091 (1)
SF-A14 | M.TSC.045 (part 1) | M_TSC | U20 | pins M.GEN.001 (1)
SF-B14 | M.TSC.100 (part 1) | M_TSC | U23 | pins M.SRC_CORE.063 (2), M.WEB.001 (1)
SF-M4-06 | M.TSC.135 (part 1) | M_TSC | U27 | pins M.SCR.040 (1)
SF-M4-07 | M.TSC.032 (part 1) | M_TSC | U27 | pins M.SCR.067 (1)
SF-M4-01 (a) | M.TSC.108 (part 1) | M_TSC | U26 entry; stage U11 | pins M.SRC_CORE.016 (1)
SF-B9 = SF-A05, SF-M3-02, SF-B10 | M.TSC.111 (part 1) | M_TSC | U3 entry; stage U15 | pins M.SRC_SENS.043 (1), (2), .055 (1), (2)
SF-B12, SF-M1-03, SF-M1-01, SF-A14, SF-B2, SF-B6, SF-B7, SF-B9, SF-B10, SF-B11, SF-B15, SF-M2-03, SF-M3-02 | M.TSC.088 (part 11) | M_TSC | U36 entry; stages with each code | pins M.GEN.034 (1)
SF-B3, SF-M1-07, SF-A10 | M.TSC.086 (part 1) | M_TSC | U35 entry; stage U20 | pins M.GEN.008 (1), (2), M.GEN.014 (1), (2)
SF-M3-09, SF-M3-01 | M.TSC.147 (part 1) | M_TSC | U8 entry; stages U22, U15 | pins M.SRC_SENS.025 (1), .035 (1), .064 (1)
SF-A10 | M.TWIN.032 (part 1) | M_TWIN | U25 entry; stage U13 | pins M.SRC_CORE.006 (1)
SF-A01 and SF-A02 | M.TWIN.024 (part 1) | M_TWIN | U25 entry; stage U13 | pins M.SRC_SENS.012 (1), .011 (1), (2)
SF-B9 = SF-A05 | M.TWIN.010 (part 1) | M_TWIN | U25 entry; stage U15 | pins M.SRC_SENS.048 (1), .043 (1)
SF-B10 = SF-A04 | M.TWIN.013 (part 1) | M_TWIN | U25 | pins M.SRC_SENS.055 (1)
SF-B6, SF-M2-03 | M.TWIN.040 (part 1) | M_TWIN | U25 | pins M.SRC_NET.093 (1), .089 (1)
SF-M3-09 (LED half) | M.TWIN.042 (part 1) | M_TWIN | U25 | pins M.SRC_SENS.025 (1)
SF-A06 | M.TWIN.169 (part 1) | M_TWIN | U13 | pins M.SRC_NET.221 (7)
SF-B13 | M.TWIN.062 (part 1) | M_TWIN | U25 | pins M.TWIN.011 (1), M.TWIN.013 (1)
SF-B13 (FRAM half) | M.TWIN.110 (part 1) | M_TWIN | U25 | pins M.TWIN.011 (1)
SF-B13 (SCD30 half) | M.TWIN.142 (part 1) | M_TWIN | U25 | pins M.TWIN.013 (1)
SF-B10 = SF-A04 | M.TWIN.142 (part 2) | M_TWIN | U25 | pins M.SRC_SENS.055 (1)
SF-B9 = SF-A05 | M.TWIN.100 (part 1) | M_TWIN | U25 entry; stage U15 | pins M.SRC_SENS.048 (1)
SF-B9 = SF-A05 | M.TWIN.116 (part 1) | M_TWIN | U25 | pins M.SRC_SENS.043 (1)
SF-B11 | M.TWIN.122 (part 1) | M_TWIN | U25 entry; stage U15 | pins M.SRC_SENS.081 (1)
SF-A01, SF-A02, SF-B9 = SF-A05, SF-M3-04, SF-B1 | M.TWIN.102 (part 1) | M_TWIN | U25 entry; stages U13, U15, U16 | pins M.SRC_SENS.012 (1), .011 (1), (2), .048 (1), .077 (1), M.SRC_CORE.091 (1)
SF-A01 and SF-A02 | M.TWIN.126 (part 1) | M_TWIN | U25 entry; stage U13 | pins M.SRC_SENS.012 (1), .011 (2)
SF-A10 | M.TWIN.128 (part 1) | M_TWIN | U25 | pins M.SRC_CORE.006 (1)
SF-M3-09 (LED half) | M.TWIN.132 (part 1) | M_TWIN | U35 entry; stage U25 | pins M.SRC_SENS.025 (1)
SF-A06 | M.TWIN.130 (part 1) | M_TWIN | U25 entry; stage U13 | pins M.SRC_NET.221 (7)
SF-B5 and SF-M1-06 | M.TWIN.152 (part 6) | M_TWIN | U25 | pins M.SRC_CORE.013 (1)
SF-A11 and SF-B4 | M.TWIN.152 (part 7) | M_TWIN | U25 | pins M.SRC_CORE.012 (1)
SF-M2-02 | M.TWIN.168 (part 5) | M_TWIN | U25 | pins M.SRC_NET.053 (1)
SF-M3-01 | M.TWIN.144 (part 11) | M_TWIN | U35 entry; stage U25 | pins M.SRC_SENS.035 (1), .064 (1)
SF-B17 | M.TWIN.144 (part 12) | M_TWIN | U35 entry; stage U25 | pins M.SRC_SENS.037 (1)
SF-M3-05 | M.TWIN.144 (part 13) | M_TWIN | U35 entry; stage U25 | pins M.SRC_SENS.063 (2)
SF-B8 | M.TWIN.144 (part 14) | M_TWIN | U35 entry; stage U25 | pins M.SRC_SENS.047 (1), .053 (1), .082 (1)
SF-M2-01 | M.TWIN.144 (part 15) | M_TWIN | U35 entry; stage U25 | pins M.SRC_NET.088 (1)
SF-M2-03 | M.TWIN.144 (part 16) | M_TWIN | U35 entry; stage U25 | pins M.SRC_NET.088 (2), .089 (1)
SF-B6 | M.TWIN.144 (part 17) | M_TWIN | U35 entry; stage U25 | pins M.SRC_NET.093 (1)
SF-A08 | M.TWIN.144 (part 18) | M_TWIN | U35 entry; stage U25 | pins M.SRC_NET.007 (1)

## Needs a new entry

None. Every carrier named by the phase-1 folds for my files maps to an existing entry.

## Source parts with no test carrier (or none in my files)

- M.WEB.014 (1), M.WEB.015 (1) (SF-B8 page half), M.WEB.016 (1) (SF-B14 "65535+"), M.WEB.021 (1) (SF-M2-06): their
  tests are `tests_js/` (M.WEB.058 templates, M.WEB.054 render, M.WEB.061 live matrix), entries in M_WEB, which neither
  P1 nor P2 edits; no carrier part exists there yet. M.WEB.001 (1) is pinned at L0 (M.TSC.100 (1)).
- M.SRC_SENS.012 (2) (SF-A03): no code, SPEC sentence only (P2). M.SRC_SENS.050 (1): "already the end state", none new.
- M.SRC_NET.077 (1) (the five WIFI codes, the LED pair): no part of its own; exercised by M.TEST_UNIT.211/.213/.216/
  .217 (1)-(2) and the catalog check M.TSC.088 (11).
- Owed in M_SCR (not P1's or P2's files): SF-M1-01 the twin CI suite's Run 1 stays clean (M.SCR.049, no tolerance
  list); host-harness scenarios (`scripts/_digital_twin_scenarios.py`) for SF-M2-05 (client closing mid-response,
  `HTTPDropped` +1), SF-B8 (`GET /sensors` marker over HTTP) and SF-B3 (`ConfigUnpersisted` over HTTP); the in-process
  twin cases cover the module side (M.TWIN.144 (14)) and L1 covers the REST side (M.TEST_HELP.041 (8)).
- Owed in M_WEB: mock rows for `ConfigUnpersisted`, `ResetBits`, NOTIFY `State`, ResetReason 21 label (M.WEB.045 /
  mockdata), as the phase-1 notes say.

## Hardware tiers owed (for P2 / lead; none written here)

- Four-tier shared-bus rule: SF-A01/SF-A02 (changed I2C call form), SF-B9 (BMP3XX per-cycle EVENT read, dev i2c0 and
  wozi i2c1), SF-M3-04 (ISL29125 per-cycle CONFIG snapshot, dev i2c1): L3 `tests_hardware/flash/test_bus_concurrency.py`
  + `device_scripts/bus_topology_autodetect_and_hazard_sweep.py` and L4 `bench/test_bus_concurrency_under_api_load.py`
  re-run (phase C). L1 = M.TEST_UNIT.234 (1)/.236 (1), L2 = M.TWIN.102 (1).
- FRAM (shared resource) SF-B1: every chunk an older image wrote reads blank once after the reflash (bench expectation,
  and CLAUDE.md's FRAM-log caveat); the five device scripts that build their own manager must pass `owner=`
  (`fram_manager_roundtrip.py`, `bus_deinit_is_a_noop_on_real_hardware.py`, `fram_write_protect_roundtrip.py`,
  `fram_busy_status_lockout.py`, `fram_pause_unpause_and_gating.py`); L3/L4 FRAM hazard runs re-run. FRAM writes are not
  wear, no marker.
- SF-A11/SF-B4: `fram_pause_unpause_and_gating.py`'s real-Timer step becomes the deadline (HW_DEV).
- SF-A10/SF-A14/SF-M1-05: bench reset-kind rows (`ResetBits` per reset kind: power-on, RUN pin, watchdog, `reboot`,
  bootloader) and Ctrl-C → `ResetReason` 21 (HW_BENCH, phase C); the bootrom's REASON after `bootloader()` is open
  (M.TEST_HELP.011 (5) leaves it to the bench).
- SF-A06: M.HW_DEV.160's FE case (and whether DMA reads update UARTRSR), phase C.
- SF-M4-01: bench non-reading host (HW_BENCH); M.TSC.108 (1) also reads the flash/bench harness's boot level.
- Config file (shared resource) SF-B3/SF-M1-07/SF-M1-04: a refused flash write cannot be produced on silicon without
  wear; I see no L3/L4 owed beyond the existing REST PUT round trips (P2 to confirm). SF-M1-01 (reformatted filesystem):
  a bench check would need a deliberate reformat (a flash write, behind `persistence_write`) — P2/lead to decide.

## Points for the lead (agent, 2026-10-06; conservative options taken)

- Unit seams in phase-1 parts: M.SRC_SENS.062 (1) is U15 but passes M.SRC_CORE.091 (1)'s U16 `owner=` keyword (test
  placed in U16, M.TEST_UNIT.136 (1)); SF-B8's driver halves (M.SRC_SENS.053/.082 U15, .047 U30) return `None` before
  the base half (M.SRC_CORE.038 (1), U19) turns it into the marker — all SF-B8 test parts are staged U19;
  M.SRC_CORE.006 (1) deferred its register-access form to M.SRC_NET.221 (6) (U13) — settled by the lead, see "Seams
  applied" below.
- `owner=` is keyword-only with no default, so every direct chunk call in tests and device scripts breaks without it:
  swept in M.TEST_UNIT.040 (1) (file list), M.TEST_HELP.036 (7), M.TWIN.102 (1); device scripts are P2's.
- The CRC seed changes the FRAM wire-trace goldens' CRC bytes (not the transfer counts): M.TEST_UNIT.049 (1)/.050 (1).
- SF-A01/A02 fakes: I chose an opt-in register route per address in both fakes (unit `register_device()`, twin
  `REGISTER_ADDRSIZE`) so raw-command chips keep their read queue and the twin's fault vocabulary (`writeto_mem` keys)
  holds; unit tests naming `*_mem` ops move to the real calls (M.TEST_UNIT.019/.055/.059/.017).
- Several existing assertions invert and are folded as such: `_check_one()` `False` → `None` (M.TEST_UNIT.086/.087),
  SCD30/ISL/BMP "GET after a failing snapshot shows None" (M.TEST_UNIT.120/.067/.016), the cancelled-flash LED test
  (M.TEST_UNIT.213 (1)), `cettime()` "not synced" (M.TEST_UNIT.107 (1)), `_truncated(44)` (M.TEST_UNIT.104 (1)),
  M.TWIN.152's (2) inverted and (4) retired, M.TEST_UNIT.208's `microdot.print_exception` replacement.
- M.TSC.111 (1): the folded warnings beside errors in one function (`_read_bmp()` certainly) need allow-list entries
  at landing; the others only if the scan pairs them.
- M.TWIN.062 (1) is a `digital_twin/README.md` text part (DOCS in phase-1's note) placed in M_TWIN because that README's
  entry lives there and P2 does not edit M_TWIN.
- Real-time limits at L2: M.TWIN.152 (7) (300 s mempause) and M.TWIN.132 (1) (300 s overlay refresh) and M.TWIN.144
  (15) (hotspot windows) each name a driven/fired path and, failing that, rest the timing half on L1 (decided at
  execution, logged).

## Seams applied (lead's decisions, 2026-10-06)

- M.SRC_CORE.006 (1) (SF-A10) is "Stage U13, after M.SRC_NET.221 (6)": M.TEST_UNIT.310 (1), M.TEST_HELP.011 (5) and
  M.TWIN.032 (1) moved to stage U13; the reset registers join the `mem32` object M.TEST_HELP.069/M.TWIN.169 create for
  the UART block (no U11 fake). M.TWIN.128 (1) stays U25.
- SF-B8 driver halves "Stage U19, with M.SRC_CORE.038 (1)": the SF-B8 test parts were already staged U19 (no edit).
- M.SRC_SENS.062 (1) "Stage U16, with M.SRC_CORE.091 (1)": M.TEST_UNIT.136 (1) already U16 (no edit).

## Follow-up (M_WEB, M_SCR), 2026-10-06

SF-xx | M-ID (part N) | file | unit | pins <source M-ID part>
SF-B14 | M.WEB.058 (part 1) | M_WEB | U32 entry; stage U23 | pins M.WEB.016 (1)
SF-B8 (page half) | M.WEB.058 (part 2) | M_WEB | U32 entry; stage U23 | pins M.WEB.014 (1), M.WEB.015 (1)
SF-M2-06 | M.WEB.054 (part 1) | M_WEB | U24 entry; stage U23 | pins M.WEB.021 (1)
SF-B8 (page half) | M.WEB.054 (part 2) | M_WEB | U24 entry; stage U23 | pins M.WEB.015 (1)
SF-M2-06 | M.WEB.062 (part 1) | M_WEB | U27 entry; stage U23 | pins M.WEB.021 (1)
SF-B3, SF-M1-07, SF-A10, SF-B17 | M.WEB.045 (part 1) | M_WEB | U32 entry; stages U20, U22 | pins M.GEN.008 (1), (2), M.SRC_SENS.037 (1)
SF-M1-01 | M.SCR.049 (part 1) | M_SCR | U35 (L1 carries the detector from U11, M.TEST_UNIT.311 (1)) | pins M.SRC_CORE.017 (1), .043 (3), .065 (2)
SF-M2-05 | M.SCR.018 (part 1) | M_SCR | U35 entry; stage U25 | pins M.SRC_NET.118 (1), .127 (1)
SF-B8 | M.SCR.018 (part 2) | M_SCR | U35 entry; stage U25 | pins M.SRC_CORE.038 (1), M.SRC_SENS.047 (1), .053 (1), .082 (1)
SF-B3 | M.SCR.018 (part 3) | M_SCR | U35 entry; stage U25 | pins M.SRC_CORE.044 (1), .015 (1), M.GEN.008 (1)

With these, the "Owed in M_SCR" and "Owed in M_WEB" items above are carried: tests_js parts in M.WEB.058/.054/.062,
the sample rows in M.WEB.045 (the mock server serves `samples.json`, so no `js/mock-server.js` change is needed), the
twin CI suite in M.SCR.049 (1), the host-harness scenarios in M.SCR.018 (1)-(3). Every source fold part now has a
test carrier except M.SRC_SENS.012 (2) (no code) and M.SRC_SENS.050 (nothing new).
