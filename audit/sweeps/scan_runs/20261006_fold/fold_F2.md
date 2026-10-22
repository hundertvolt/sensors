# Fold F2 (M_SRC_SENS.md, M_TWIN.md), 2026-10-06

Numbering: an entry whose Change slot had no numbered parts gets its fold parts as (1), (2), ... after the existing text.

## Folded

SF-M1-02 | M.SRC_SENS.063 (in-place correction of `_run_restore()` + part 1) | src/asy_sgp40_driver.py | U16 kept (row U16) | L1 undated backup and dated-unsynced backup after the wait expires, both restore, nothing raises (TEST_UNIT)
SF-M3-05 | M.SRC_SENS.063 (part 2) | src/asy_sgp40_driver.py | U16 kept (row U15) | L1/L2 restart after fed samples keeps live state, boot restores (TEST_UNIT, TWIN)
SF-M3-06 (SGP40 half) | M.SRC_SENS.063 (part 3) | src/asy_sgp40_driver.py | U16 kept (row U16/U30) | L1 `None` buffer leaves the restore pending (TEST_UNIT); base half is M_SRC_CORE (F1)
SF-M3-01 (SGP40 half) | M.SRC_SENS.064 (part 1) | src/asy_sgp40_driver.py | U15 kept | L1 stale/None TS cases, L2 ContMeas off (TEST_UNIT, TWIN); Part N row `sgp40.comp_max_age_s` (SPEC)
SF-M3-01 (notification half) | M.SRC_SENS.035 (part 1) | src/asy_notification_service.py | stages U2/U5/U9/U22/U30 kept (row U22) | L1 stale TS no trigger, L2 WarnCO2 ends (TEST_UNIT, TWIN); Part N row `notify.sample_max_age_s` (SPEC)
SF-B17 | M.SRC_SENS.035 (part 2) + M.SRC_SENS.037 (part 1) | src/asy_notification_service.py | 035 stages / 037 stages kept (row U22) | L1 per State code, every NOTIFY( tuple, L2 no-NTP boot State 2 (TEST_UNIT, TWIN); mock/page row (WEB); generated defs if listed (GEN); SPEC A.4 code table + DEVICE_REFERENCE (SPEC, DOCS)
SF-B2 | M.SRC_SENS.034 (part 1) | src/asy_notification_service.py | stages U2/U10/U30/U31 kept (row U9/U22) | L1 busy drop warns, default sink silent; integration ErrCounts (TEST_UNIT); catalog row (GEN); SPEC C.7.1 (SPEC); owner-review list entry (PROC)
SF-M3-09 (LED half) | M.SRC_SENS.025 (part 1) | src/asy_neopixel_driver.py | stages U9-U22 kept (row U22) | L1 driven-clock refresh, L2 blanked twin pixel (TEST_UNIT, TWIN); Part N row `led.overlay_refresh_ms` (SPEC)
SF-A01 (choke point) | M.SRC_SENS.012 (part 1) | src/asy_i2c_driver.py | stages U5/U13/U30 kept (row U13) | L1 short count -> EIO + STOP (TEST_UNIT); fakes' short-ACK mode (TEST_HELP, TWIN); SPEC F.5.1 sentence (SPEC); four tiers re-run (HW phase C)
SF-A01 (register-write half) | M.SRC_SENS.011 (part 1) | src/asy_i2c_driver.py | U30 kept, lands in stage U13 (row U13) | L1 NACKed data byte, addrsize 8/16 (TEST_UNIT); twin I2C routes prefixed writeto to register handlers (TWIN)
SF-A02 | M.SRC_SENS.011 (part 2) | src/asy_i2c_driver.py | U30 kept, lands in stage U13 (row U13) | L1 NACKed register byte -> EIO (TEST_UNIT); twin no-stop write + readfrom_into routing (TWIN); SPEC F.5.1 sentence (SPEC); four tiers (HW phase C)
SF-A03 | M.SRC_SENS.012 (part 2) | src/asy_i2c_driver.py | kept (row U13) | no code; SPEC F.5.1/F.2 sentence only (SPEC, M_SPEC)
SF-B8 (BMP3XX driver half) | M.SRC_SENS.047 (part 1) | src/asy_bmp3xx_driver.py | U30 kept (row U19/U23) | L1 whole-module `{"error":"unavailable"}` (TEST_UNIT); base half M_SRC_CORE (F1); page M.WEB.001 (WEB)
SF-B8 (SCD30 driver half) | M.SRC_SENS.053 (part 1) | src/asy_scd30_driver.py | U15 kept (row U19/U23) | same as above
SF-B8 (ISL29125 driver half) | M.SRC_SENS.082 (part 1) | src/asy_isl29125_driver.py | U15 kept (row U19/U23) | same as above
SF-B9 = SF-A05 (reader half) | M.SRC_SENS.043 (part 1) | src/asy_bmp3xx_driver.py | stages kept (row U15) | L1 por -> warn + re-apply, failed re-apply fails cycle (TEST_UNIT); twin EVENT model (TWIN); four bus-hazard tiers (TEST_UNIT, TWIN, HW phase C); catalog row (GEN); SPEC M.4/C.7.1 (SPEC)
SF-B9 = SF-A05 (protocol half) | M.SRC_SENS.048 (part 1) | src/asy_bmp3xx_driver.py | U31 kept (row U15) | L1 take_por_detected, reset consumes por, fatal_err, 8-byte burst (TEST_UNIT); twin EVENT/ERR_REG in burst (TWIN); hazard catalog EVENT read (TEST_HELP)
SF-M3-02 (BMP3XX half) | M.SRC_SENS.043 (part 2) | src/asy_bmp3xx_driver.py | stages kept (row U15) | L1 new code, streak unchanged (TEST_UNIT); catalog row (GEN); owner-review list (PROC)
SF-M3-02 (SCD30 half) | M.SRC_SENS.055 (part 2) | src/asy_scd30_driver.py | U15 kept | same as above
SF-B10 = SF-A04 | M.SRC_SENS.055 (part 1) | src/asy_scd30_driver.py | U15 kept | L1 five not-ready reads warn once, cleared by new data (TEST_UNIT); L2 RDY stuck high (TWIN); catalog row (GEN); owner-review list for the restamp D.1 question (PROC)
SF-B11 | M.SRC_SENS.081 (part 1) | src/asy_isl29125_driver.py | U15 kept | L1 timeout warns once, converged silent (TEST_UNIT); L2 twin calibration (TWIN); catalog row (GEN); SPEC M.1.5/C.7.1 (SPEC)
SF-M3-04 | M.SRC_SENS.077 (part 1) | src/asy_isl29125_driver.py | U15 kept | L1 corrupted CONFIG byte without failed write (TEST_UNIT); four bus-hazard tiers for the per-cycle snapshot (TEST_UNIT, TWIN, HW phase C)
U15 temp-offset row (no SF number) | M.SRC_SENS.050 (part 1, "already the end state") | src/asy_scd30_driver.py | stages kept | none new (A.U4.05's tests carry it)
SF-B13 (FRAM half) | M.TWIN.011 (part 1) | digital_twin/_fram_chip.py | U25 kept | L2 fallback-print and atomic-save cases (TWIN); README "FRAM persistence" (DOCS)
SF-B13 (SCD30 half) | M.TWIN.013 (part 1) | digital_twin/_scd30_chip.py | U25 kept | L2 fallback-print and atomic-save cases (TWIN); README "SCD30 persistence" (DOCS)

Every folded entry's `Blast carried by` gained a "(SF-xx: ... — tests in M_TEST_UNIT/M_TWIN per phase 2)" note.

## In scope but not folded here (reason)

- SF-M3-09, SGP40 header half: no M entry covers `src/asy_sgp40_driver.py:1-8` (the module docstring; M.SRC_SENS.058
  starts at :10). The SPEC M.3 sentence is M_SPEC's; the header sentence needs an entry or the lead's placement.
- SF-M3-03 (SCD30 soft reset vs ASC): the register row's fix is a SPEC sentence, a bench check and an owner-review
  entry. None lands in my files (the `SelfCal` description change in the scan run text was not taken; the register
  row names SPEC only).
- SF-B8 base half (`_get_dict_cfg()` turning a `None` into `{name: {"error": "unavailable"}}`): `src/base_classes.py`,
  M.SRC_CORE.038 — F1's. My three driver halves depend on it and state the exact shape (in place of the field map,
  never beside values; M.WEB.001 `isUnavailable()`).
- SF-M3-06 base half (`LockableBuffer` logs `str(e)`): `src/base_classes.py`, M_SRC_CORE (F1).
- SF-M2-02 (`cettime()` gate) and SF-M2-04 (LED pattern via the WiFi flash task): sites in `asy_ntp_client.py` /
  `asy_wifi_service.py`, M_SRC_NET.

## Decisions taken on the owner's behalf (agent, 2026-10-06), for review

- SF-M1-02: the corrected chain restores an undated backup at once (HEAD and legacy) and persists the existing
  `_WRN_SGP_RESTORED_NO_TS` for a dated backup with unknown age.
- SF-B2: the default sink is recognised by identity of a `@staticmethod` (`py/runtime.c:1149-1151`; bound methods
  carry no `__self__`).
- SF-M3-01: one fixed bound, 10800 s (3 x BMP3XX's 3600 s maximum SampleInterval), in both consumers, tunable-tagged.
- SF-M3-09: the overlay refresh is the overlay task's bounded wait (300000 ms), not a notification-side call.
- SF-B9/A05: a failed re-apply after `por_detected` fails the read cycle into the existing ladder; ERR_REG is read
  by starting the data burst at 0x02 (contiguous).
- SF-B10/A04: threshold 5 consecutive not-ready reads, mirroring ISL29125's `_PERIODIC_ONLY_WARN_AT`.
- New catalog codes, numbered at execution (M.GEN.034): `_WRN_NOTIFY_SIGNAL_DROPPED`, `_WRN_ISL_CAL_TIMEOUT`,
  `_WRN_BMP_CHIP_RESET`, `_WRN_SCD_NOT_READY`, shared `_ERR_READ_RANGE`.
