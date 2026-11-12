B4 falsification, written by the agent (Tue Nov  3 11:00:51 UTC 2026)

Head `963d0de1`, base `3129bf21`, pre-audit `25caf528`, read in `S/wt-b4f` (S = the scratchpad). Line numbers are
at `963d0de1` unless marked. Datasheets used: `datasheets/bmp3xx/bst-bmp388-ds001.pdf` (read from the main checkout's
submodule; the worktree's `datasheets/` is empty). Ten runs, all through `S/u35/lead/run.sh`, labels below; one
planted break (restored, worktree clean at `963d0de1`). Probes and their inputs: `S/u35r/r1/B4/ftmp/`.

Runs: `b4f_rebuild`; `b4f_probe_i2c`; `b4f_probe_voc`; `b4f_hz_mock` (22/22 at -1 and 32768); `b4f_hz_twin` (25/25 at
both); `b4f_sizes`; `b4f_flash_twin` (FAILED, see 13); `b4f_flash_twin_planted` (passed with the planted line);
`b4f_fw`; `b4f_held` (3/3 at both). No memory marker in any test log.

## Verdicts

1. STANDS. Probe `b4f_probe_i2c`: on a deinit'd bus every I2C/I2CDevice getter and transfer answers `None`,
   `I2CDevice.setup()` raises `RuntimeError("I2C bus not initialized")` (pre-audit too), SPI transfers answer `None`,
   `configure()` with the lock held raises `RuntimeError("SPI bus not initialized ...")`, `async with SPIDevice`
   raises it and releases the lock; `recover()` (`asy_i2c_driver.py:305-312`, clear then `init(*self._args)`, no
   catch) brings the bus back. Wording notes: `recover()` did not exist at `25caf528`; and the pre-audit `None`
   checks still raise generic `OSError`s on a missing bus (e.g. `asy_bmp3xx_driver.py:551-552, 577-578`,
   `asy_isl29125_driver.py:1166-1167, 1430-1432`), exactly as at `25caf528` - only the base's added raises are gone.
   The rp2 constructor cannot fail with arguments it once took (`ports/rp2/machine_i2c.c` make_new, v1.29.0), so the
   no-bus state is unreachable in production.
2. STANDS. One `_clear_bus()` (`asy_i2c_driver.py:35-66`) for the boot clear (`:96-99`) and `_clear_locked()`
   (`:121-128`, used by `clear()` `:256-261` and `recover()`). `b4f_held`: the twin frees an SDA held at power-up at
   both GC stages. The runtime SDA-held case is covered in the mock tier only (`test_clear_of_a_held_sda_sends_nine_pulses_and_a_stop`).
3. REFUTED (narrow). "A short ACK count raises `OSError(EIO)`" fails when the STOP's zero-length write is itself
   refused: `asy_i2c_driver.py:160-162` lets that write's `OSError` escape, so the caller gets ENODEV (19), not EIO.
   `b4f_probe_i2c`: STOP refused -> `('OSError', 19)`; device NAKing its address after NACKing the register byte
   (the fake's own model) -> `('OSError', 19)`. The base pinned EIO here (`test_a_short_no_stop_write_raises_eio_even_when_its_stop_is_refused`,
   `3129bf21:tests/test_asy_i2c_driver.py:1235`), removed. One `writeto()` for address+payload, the STOP after a
   short no-stop write and `_point_at()` all hold. Impact: log text only (callers catch every `OSError`).
4. STANDS. `_read()` `:453-473`: forced mode 0x13, STATUS poll (`_STATUS_POLL_MS` 2, 300 ms bound), 6-byte burst from
   0x04 (DS001 Table 27: drdy bits reset by reading the data registers); no EVENT read anywhere in `src/`; range
   rejection (`:510-511`) goes to E11 "Read failed:" (`:257-259`); E27 at SCD30 `:89, 478`. Consequence not covered
   by any claim: see defect A.
5. REFUTED. No W73 remains, but the read path does not otherwise match the base: `_capture_frc_config()`
   (`asy_scd30_driver.py:319-327`, called first in every `_read_scd()` at `:466`) lost the base's once-per-episode
   guard (`3129bf21:src/asy_scd30_driver.py:328-329`), so an invalid store is read and refused, one CFGMGR entry each,
   every cycle - the unit's own test says so (`test_an_unreadable_frc_config_is_logged_once_per_failed_read`,
   `tests/test_asy_scd30_driver.py:2068, 2072`: `before + 5`, against the base's `before + 1`/`+ 2`). The decode
   also changed form: `_words` and one `unpack_from(">fff")` (base `:699, 865-872`) became three
   `unpack(">f", slice + slice)` (`:840-842`), equal values, more allocation.
6. STANDS (read-cycle scope). `_verify_after_failed_write()` `:877-890` returns unless the failed-write count moved;
   its failed re-read is silent (`report_if_fatal()` only, `asy_print_log.py:426-431`); `_end_calibration()` prints
   only; `_int_rearmed`/`_rearm_interrupt()`, `_MAX_DWELL_MS`/`_expire_calibration()` and the restart resets are gone;
   W32 (`:569`) and `_int_held = False` (`:439`) stay. Note: a config GET still compares the shadow every time
   (`_read_sensor_dict()` `:746`, pre-audit too), so "only after a counted failed write" holds for the read cycle.
7. STANDS. `_init_sgp()` `:305-335` re-arms the restore on every restart; `_voc_state()` gives 3 for 86,400 samples
   after a restore; `_run_restore()` `:511-515` logs W65 for every not-valid read; `_current_value`/`_COMP_MAX_AGE_S`
   gone; dated-but-unsynced reads each cycle then restores with no warning; `_check_storage()` `:279-283` keeps the
   pending restore on a failed buffer. Consequence missed in the bench tier: defect B.
8. REFUTED (narrow: stored state). `b4f_probe_voc` ran `25caf528`'s port and the head's side by side, 20,000 samples
   each of constant, random-walk, step and 0/65535-alternating input: outputs identical every sample, and the codec
   round-trips byte-identically both ways. But for the same input the stored state differs from about sample 16,400
   on (first seen at the 16,450 checkpoint, fields 17-18: `uptime_gamma`/`uptime_gating`; final 1,307,639,808 vs
   1,073,610,752), because the head keeps `_VOCALGORITHM_MEAN_VARIANCE_ESTIMATOR__FIX16_MAX = 16383`
   (`voc_algorithm.py:40-42`) where `25caf528` has 32767. Harmless to the outputs (both sigmoids saturated), but a
   backup written after ~4.5 h is not the bytes `25caf528` would write. VOCState 2 reads "settled" in the catalog
   (`buildgen/error_catalog.json:202`), the `@web` text (`asy_sgp40_driver.py:123`) and the built dev site
   (decompressed `build/generated_html/dev/frozen_html.py`).
9. STANDS (code read). Each arm catches `(OSError, MemoryError)` and makes one `pr.err()` call: BMP3XX `:334-343`,
   SCD30 `:528-537` (its pin IRQ still wired after), SGP40 `:567-576`, ISL29125 `:935-944`; no task ends. The reader
   then simply never triggers (SCD30/ISL29125 keep their pin path), as at `25caf528`.
10. STANDS. `_read_sensor_dict()` returns `None` on any snapshot raise (BMP3XX `:274-287`, ISL29125 `:736-752`), and
    `_get_dict_cfg()` answers `{"error": "unavailable"}` (`asy_base_classes.py:462-476`).
11. STANDS. `git grep` over the tree (`:!arduino`, `:!audit`) finds no BMP_CHIP_RESET/SCD_NOT_READY/ISL_CAL_TIMEOUT or
    W71/W73/W75 emitter, decoder or expectation; catalog rows 71/73/75 that remain are E codes (NTP, UART); E27 at
    `error_catalog.json:50`.
12. STANDS. All setups/deinits named answer `None`; no `src/` or generated caller reads them; `_NO_OPS`
    (`tests_scripts/test_readiness_gates.py:20`) holds exactly `("I2C","deinit")` and `("SPI","deinit")`.
13. REFUTED (the flash and bench tiers). Mock and twin pass (`b4f_hz_mock`, `b4f_hz_twin`). But the flash tier named
    in CLAUDE.md is now red by construction: `tests_hardware/flash/test_bus_concurrency.py:258`
    (`test_bus_topology_autodetect_address_and_reserved_range_sweep`, which runs the named sweep script) asserts
    `reset()` consumed its own `por_detected`; the head's `BMP3XX_I2C.reset()` (`asy_bmp3xx_driver.py:632-646`) no
    longer reads EVENT, and `bus_reader_loops.py:89` reads it right after `setup()`. `b4f_flash_twin` (`--twin`):
    FAILED at `:258`, `por_after_setup={'bmp3xx': True}`, so its later checks (ISL divergences, no errors) never run.
    Planted the base's EVENT read back after `reset()`'s ERR read (`asy_bmp3xx_driver.py:642`):
    `b4f_flash_twin_planted` passes; restored with `git checkout`. The bench file's
    `test_fram_erase_under_api_load` is hit too (defect B).
14. REFUTED. Test changes that follow from no claim above, several weakening a product check:
    - SCD30 FRC episode guard: `test_an_unreadable_frc_config_is_logged_once_per_episode` -> `..._per_failed_read` (claim 5).
    - BMP3XX reset settle 3 -> 2 ms (`asy_bmp3xx_driver.py:78-79`): `test_reset_settles_one_tick_past_the_reference_settle`
      (`3129bf21:tests/test_asy_bmp3xx_driver.py:495`) -> `test_reset_settles_the_reference_settle` (`:483`); the
      one-tick margin for `sleep_ms()` waking up to 1 ms early is gone (DS001 gives no soft-reset time; tstartup 2 ms).
    - Allocation pins removed with their mechanisms, none in a claim: `test_the_scratch_view_is_one_object_for_the_bus_life`,
      `test_a_full_buffer_transfer_hands_the_fake_the_callers_object`, the three `get_register_into` tests (I2C);
      `test_read_counts_fills_the_drivers_own_burst_buffer_in_place`, `test_get_config_snapshot_fills_one_buffer_built_at_construction`
      (ISL29125); `test_read_measurement_drops_the_crc_bytes_into_one_reused_word_buffer` (SCD30, contradicting claim 5);
      `test_read_word_decodes_one_word_in_place`, `test_a_restore_waiting_for_ntp_reuses_the_readers_one_backup_buffer`
      (SGP40); `test_no_sample_converts_a_constant`, `test_the_sample_constants_are_converted_by_f16_at_construction` (VOC).
    - The EIO guarantee (claim 3 above).
    - VOC restore validation (`test_unpack_from_refuses_a_field_outside_int32`, `test_a_restored_uptime_above_the_small_int_limit_is_clamped`):
      arguably claim 8's "unpacks as `25caf528`".
    - The checks asked about: `_reset_errors_not_undone` (`scripts/_digital_twin_scenarios.py:1644-1645`) went from
      `== 0` to `<= 1` of any non-E entry - still catches the restored history (it holds E entries), but no longer
      says the one entry is W65; `SharedBoot.acquire()` (`:378-380`) ignores `_wait_entry()`'s answer, so a boot
      whose W65 never comes is not reported there; the CI-suite Run 1 change (`_check_quiet_boot`, `_blank_backups`)
      is an exact match on the owed W65 and not weaker. The readiness exemption is mechanical (claim 12).
    - Missed consequences: defects A and B (hardware tiers not updated).
15. STANDS. `b4f_sizes`: `src/` bytecode 201,265 B at `963d0de1`, 205,681 B at `3129bf21` (-4,416); only
    `asy_spi_driver.py` grows (2,020 -> 2,073, +53). `b4f_fw`: dev image `imageFreeBytes` 51,356 B, clean tree at
    `963d0de1` (record `S/wt-b4f/build/b4f-firmware-dev.json`).

## Defects outside the claims

A. (b) Flash tier red on every BMP3XX board: `tests_hardware/flash/test_bus_concurrency.py:258` against the head's
   `reset()`; shown on the twin (`b4f_flash_twin`), cured by the base's EVENT read (`b4f_flash_twin_planted`). Either
   the assertion or `bus_reader_loops.py:89` must follow the removed EVENT read.
B. (b) Two bench tests expect every FRAM-backed log blank after `erasefram`:
   `tests_hardware/bench/test_system_commands_over_rest.py:172-174` and
   `tests_hardware/bench/test_bus_concurrency_under_api_load.py:424-426`. The head's post-erase boot logs SGP40 W65
   on the blank chunk at its first read cycle (`asy_sgp40_driver.py:511-515`; the twin pins this in
   `tests/test_digital_twin_ntp.py:481`), so both fail once that cycle has run before the errcount read (the second
   reads after a reboot under load: near certain). Bench tier only; not run.
C. (b) `SPECIFICATION.md:8952-8955` still describes SCD30's 12-byte word buffer and `unpack_from(">fff")`, which the head
   no longer has. Stale comment: `asy_isl29125_driver.py:745` ("the next snapshot refills raw") - the snapshot is a
   fresh copy now.
D. Lost by design and real, if rare (claims 4, 6, 7): a BMP3XX power cycle leaves OSR/IIR at chip defaults silently
   until a failure re-applies them (the twin test now pins that, `test_digital_twin_hot_replug.py:127-134`); the
   ISL29125 dwell/candidate ticks go wrong after 2**29 ms (~6.2 days) without a switch; the SGP40 compensates from a
   stopped SCD30's last values indefinitely.
E. Environment note: `b4f_fw` built in the shared `S/tc-int` rp2 build directory (as the lead's `b4_fw2`/`b5_fw` do).

Nothing of mine is running.
