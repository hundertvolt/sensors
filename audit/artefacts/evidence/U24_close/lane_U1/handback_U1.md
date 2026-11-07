
######## SubagentHandback 2026-10-13T20:38:31.514Z
U24 lane U1 hand-back. Branch audit/u24-u1, commits 95a12e3 (W1 migration) and d00e02c (final). Base is 31d5bfc. Nothing of mine is running. The temporary `typings` symlink is removed.

**Steps (45):** 37 applied, 3 partly, 5 already landed.
- Already landed: 19 (bmp:1013-1014), 21 (bmp CHIP_SET in code() form), 29 (scd30 `_WrongLengthCRC.add_into`, start named), 166 (isl get_cfg_schema), 234 (bmp:425).
- Partly:
  - 25: B905 noqa kept, because its pyproject entry is U28's. seed_*/ready_* keep their names.
  - 172: only make_* builders made private (§1 row 76); queue_legs and calibrating_reader keep their names.
  - 191: the gate is U35's, so it is not written.
- BMP constant: wave2 ruling 2 applies; the local copy stays at bmp:98 `_EXPECTED_TEMPERATURE`.

**Deviations:**
- SGP40 init and settle waits are recorded instead of slept. The file goes from 116 s (the green-file time at U22/U23) to 8.2 s.
- SCD30's soft-reset settle is recorded instead of slept, with a new assert on the recorded wait.
- scd30:47 `_START_TRIGGER_PERIOD_MS` is pinned rather than read, so its @tunable mirror stays.
- The SCD30 wire copies are renamed `_WIRE_*`.
- The bmp/voc module-level SPI swap is gone; `_fram_builders` swaps per bus.
- The bmp bool test is renamed.
- The isl "no per-test reset" comment is fixed. Still false, outside my set: `_bus_hazard_catalog.py:49` (D), `test_asy_i2c_driver.py:50` and `test_ticks_rollover.py:412` (U4), `_uart_comm_harness.py:70`, `test_asy_uart_comm.py:138`, `test_asy_uart_driver.py:91`, `test_asy_uart_link_driver.py:52` (U3).
- For one ruff trial I swapped `pyproject.toml` in place, then restored it byte-identical.

**Seen failing first** (each with a planted bite in a scratch copy; the old test stayed green where I ran it):
- crc:372 red with init 0 treated as the default; old file 75/75.
- math dew :143 and the boundary tests for pressure, HSB, chromaticity and CCT red under planted coefficient changes.
- voc:122 red with the window check removed; old file green.
- bmp:250 red with any ID 0x50-0x61 accepted; old file green.
- RF286 (bmp:1241) red with the CHIP_SET log dropped.
- isl:1281 red with HSB S and B swapped; isl:3405 red with the PRST table swapped.
- sgp40:3224 red with a stray general call in get_raw; old sweep green.
- sgp40:213 red with the reset after self-test dropped; sgp40:307 red with the general call sent to 0x59.
- OF-53: without the helper on 9bf2274's fake, isl:1287 and :1869 are red; on F's fake 241/241.

**Results:** all 7 files green at -1, at 32768 and under settrace; 0 MemoryError. My lines in test_const_mirrors and test_microtest are all gone (const_mirrors 123 → 79 problems overall, 23 reads).

**Red checks:** test_decision_vocabulary flags stale rows I retired: `_decision_vocab_allowlist.txt` lines 220, 255, 257, 274, 276, 277, 421 (lead). The other reds are the base's (tunables: X; import_placement: F/T).

**Silent-failure scan:**
- New: class 4, "a swallow that hides an early raise" in bmp:2423, scd30:2254 and isl:4065. These sweeps swallow every exception, so a method that raises before reaching the bus still passes. Same shape as A.U24.29; no step of mine covers them, so please park them.
- Covered:
  - Class 4: old-shape inject_fault sites at bmp:1637/1653 and isl:2384/2497/3190/3204 passed on W1 only because the drivers swallowed the fake's TypeError (A.U24.78, fixed).
  - Class 4: the SGP40 sweep (step 30).
  - Class 1: the isl CONFIG-block helper (OF-53).
- The other §8 modes were checked: none found.

**Facts owed to the lead:**
- Any-baseline lines retired: pyproject.toml:454, 457, 465, 468, 469, 489. ANN401 line retired: :298. A trial removal of all seven gives clean mypy (both passes) and ruff.

**Facts owed to X and Y:** none.

**Timing:**
- Only file over 10%: voc at 32768, 29.8 s against 17.8 s base.
  - The cause is GC mark cost, not the migration. Per-collection cost is 1.40 ms against 0.79 ms, with the same survivors (heap maps identical).
  - The likely path is py/gc.c's 64-entry mark stack overflowing, followed by a full-heap rescan (gc.c:567-578, 620-637). Import layout decides it: the base file with only a no-op trailer change also takes 28.5 s.
  - I found no test-side fix. Under settrace, voc improved from 158.6 to 146.7 s.
- Other after-times (-1 / 32768 / settrace, seconds): bmp 12.9 / 13.4 / 13.3; isl 2.6 / 3.8 / 3.3; scd30 21.9 / 44.0 / 36.8; sgp40 8.2 / 11.2 / 24.8. crc and math run under 0.1 s.

**Runs:** every run exited rc 0 except the bite runs, whose failures were intended. The runs over a minute are logged in RUNS.md. Logs are in S/u24/laneU1/logs/.
