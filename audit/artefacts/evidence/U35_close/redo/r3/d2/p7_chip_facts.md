P7: the chip facts against the final drivers' waits and defaults (lane D2, agent, 2026-11-04)

Drivers at `17688315`. Datasheets read from `/home/user/datasheets/` (the private repository; its copies of the
SGP40 and SCD30 PDFs are byte-identical to the stale folder's); page = PDF page. Bench facts:
`S/u35r/bench/READING_20261029.md:76-78`. Verdict per fact: holds, or a finding.

## SGP40 (Sensirion SGP40 datasheet, version 1.2, February 2022)
| fact | source | final driver (`src/asy_sgp40_driver.py`) | verdict |
|---|---|---|---|
| serial number: 0x3682, 9 bytes, three words each followed by its CRC, max 1 ms | Table 8 (p. 12), Table 16 (p. 14), section 3.4 (p. 10) | `initialize()` sends 0x36 0x82, waits `_SERIAL_READ_WAIT_MS` 3 ms, reads 9 bytes into `_reply_buffer = bytearray(9)`, CRC-checks each word (`_read_words()`) | holds |
| the serial's structure | section 3.4 (p. 10) gives none | word 0 must be 0x0000: legacy's field-proven check, not a datasheet fact | holds as a legacy rule; dev's word 0 is round 1's read (`sgp40_conformance_probe.py` emits `A01_serial`) |
| CRC-8: polynomial 0x31, init 0xFF, final XOR 0x00 | Table 7 (p. 12) | `asy_crc_checks.py:4` (CRC8 0x31/0xFF), `CRC8()` per word | holds |
| self-test: 0x280E, max 320 ms; high byte 0xD4 pass, 0x4B fail, low byte ignored | Table 8 (p. 12), Table 13 (p. 14) | `_SELF_TEST_WAIT_MS` 500 ms; `(self_test >> 8) != _SELF_TEST_PASS` (0xD4) | holds |
| measure raw: 0x260F, max 30 ms | Table 8 (p. 12) | `_MEASURE_WAIT_MS` 100 ms | holds |
| heater off: 0x3615, max 1 ms | Table 8 (p. 12), Table 14 (p. 14) | `_HEATER_OFF_MAX_MS` 1 ms (B4 dropped the "+ 1") | holds: a `sleep_ms(1)` may end up to one tick early, and the next command to the chip is the next read cycle (1 s) |
| general-call soft reset 0x00 0x06; reset time max 0.6 ms | Table 17 (p. 14), Table 3 (p. 5) | `_reset()` writes 0x06 to 0x00, NAK tolerated, waits `_GENERAL_CALL_RESET_WAIT_S` 1 s | holds |
| address 0x59 | section 4.2 (p. 11) | `_SGP40_ADDR` 0x59 | holds |
| 24 h learning time | Info Note VOC Index (p. 1) | `_VOC_SETTLED_SAMPLES` 86400 at the 1 s period | holds |

## SCD30 (Interface Description, version 1.0, May 2020)
| fact | source | final driver (`src/asy_scd30_driver.py`) and dev's TOML | verdict |
|---|---|---|---|
| I2C at most 100 kHz, 50 kHz or less recommended | section 1.1 (p. 2) | dev `[bus.i2c1] frequency = 50000` | holds |
| clock stretching 30 ms, 150 ms once a day | section 1.1 (p. 2) | dev `[bus.i2c1] timeout = 200000` (200 ms) | holds |
| boot-up under 2 s | section 1.1 (p. 2) | `_SOFT_RESET_WAIT_MS` 2500 | holds |
| a read header more than 3 ms after the command | sections 1.4.4 (p. 10), 1.4.5 (p. 11) | `_CMD_RESPONSE_WAIT_MS` 50 after every command and register write | holds |
| interval 2-1800 s, stored in NVM | section 1.4.3 (p. 9) | `_MEAS_INTERVAL_MIN/MAX` 2/1800, `_VAL_MEAS_INTERVAL` | holds |
| FRC reference 400-2000 ppm; reads back 400 after a power-up (volatile) | FRC subsection (p. 14) | `_FORCED_RECAL_MIN/MAX` 400/2000 | holds; the bench's "FRC 400" is that power-up default, not a stored value |
| temperature offset, altitude and ASC stored in NVM; soft reset reloads them | sections 1.4.6 (p. 13), 1.4.7 (p. 15), 1.4.8 (p. 16), 1.4.10 (p. 17) | no chip field has a default (`_VAL_TEMP_OFFSET` etc. carry `None`), so the boot writes none; the setup's soft reset keeps them | holds: the bench's 4.00 C, 0 m, ASC off survive, and every value lies inside the schema's range (0-655.35, 0-65535, bool) |
| continuous-measurement status is NVM | section 1.4.1 (p. 8) | the product's setup sends no 0x0010 (only an `AmbPres` PUT does) | holds: a boot writes no NVM |
| data-ready gap: median 2,143 ms, max 2,250 ms at a 2 s interval | bench (READING:76-77) | reads on the RDY rising edge; FRC readiness counts a missed measurement only past `3 * interval` half-ticks (3.0 s at 2 s) and "not measuring" past `4 * interval` (4.0 s) | holds, 750 ms margin to the missed-measurement mark |
| at most 20 not-ready polls at 100 ms in a row | bench (READING:77) | a not-ready `read_measurement()` leaves the cache and answers `False`; the cycle carries the cached values, so it counts no failure and climbs no rung | holds |
| a missed RDY edge | — | the 500 ms tick reads after `_trigger_half_ticks` = 2 x `trigger_s` (dev 3 s) of the pin high | holds at L1; its L2 cell is gap G1 (`u35_52_rungs.md`) |
