# WR1: the device picks read each bus's own construction; the twin shared bus is built as generated (lead, 2026-10-27)
Read `S/u35r/briefs/redo_common.md` (all of it; "Quality comes first" and "Efficiency" are binding, and it says how
you hand back). Then, on your worktree:
- `tests/_twin_devices.py` in full (`wiring_read()`, `distinct_wirings()`, `devices_with()`), and SPECIFICATION.md E.2.1;
- `tests/test_digital_twin_bus_hazard_concurrency.py`'s `_shared_bus()` and the `l2.bus_hazard_concurrency_shared_bus_
  timeout_us` tag with its Part N row;
- `tests/test_asy_uart_link_driver.py`'s `_shipped_rates()`, which already reads a bus's generated construction;
- `src/asy_i2c_driver.py`'s use of `timeout` (`_DEFAULT_TIMEOUT_US`, `_scl_released`), and `digital_twin/machine.py`'s
  `I2C.__init__`;
- the lead's probe, `S/u35/lead/probe/wiring_bus_probe.py` and its log.

Worktree and base: in your launch message. Logs go in `S/u35/laneC/wr1/`.

## The finding (N11e, checked by the lead)
- `wiring_read()` reads a driver's construction, the constants it names, and each touched bus's pins and occupants. It
  does not read the bus's own construction line (`i2c0 = asy_i2c_driver.I2C(0, 13, 12, frequency=50000, timeout=
  200000)`). So two devices that differ only in a bus's frequency, timeout or UART poll rates count as one wiring, and a
  test runs on only one of them. The I2C timeout is live in `src/`: it bounds the SCL-release wait of the bus clear.
- The lead's probe added each touched bus's construction line to the read. Over 14 call shapes (no drivers, every single
  driver, the five multi-driver tuples in use), the picks did not change. The gap is latent today; a TOML that changes
  only a bus setting would hide behind it.
- `_shared_bus()` says it builds the bus "as its generated module builds it", but always passes `frequency=50000,
  timeout=200000`. In the generated modules, one bus per device has `timeout=200000` and the other none (the 50000 us
  default).

## Items, in order (each committed green on its own)
1. **`wiring_read()` reads each touched bus's construction.** For every I2C bus, SPI bus and UART bus a named driver sits
   on, add that bus's generated construction statement to the read.
   - Red first: a test with a scratch tree (point `_TREE` at a copy of the generated modules, not the real one) where
     two devices differ only in one bus's timeout. It fails on today's code (one pick) and passes on the fix (two).
   - Every `distinct_wirings()` call site's pick, before and after, on today's tree: list them all, including
     `*_READ`, `*drivers` and `driver` in a loop. Any changed pick is a stop: hand it to the lead with the reason.
   - SPECIFICATION.md E.2.1: the sentence that says what a wiring read covers, made true.
2. **`_shared_bus()` builds the bus as the device's generated module does.** Read the bus's construction line the way
   `_shipped_rates()` reads a UART's, and pass its frequency and timeout, leaving out what the line leaves out.
   - If the constant goes, the `l2.bus_hazard_concurrency_shared_bus_timeout_us` tag and its Part N row go with it.
   - Bite: a plant that keeps the fixed values fails a check you add, for example the built bus's `freq` and `timeout`
     against the generated line's.
   - Then find every other bus construction with literal settings in `tests/` and `digital_twin/` (the lead counts 8
     `asy_i2c_driver.I2C(` / `asy_spi_driver.SPI(` / `asy_uart_driver.UART(` sites). Each one either reads its device's
     construction, or its comment says that it is a harness bus, not a device's.
3. **Checks:**
   - `tests/test_digital_twin_bus_hazard_concurrency.py` on every device it runs on, at both stages, with zero memory
     markers (the formal pair);
   - every file that imports `_twin_devices`, at both stages: run them all, since the picks feed every twin file;
   - `tests_scripts/test_twin_wiring_contract.py` and every `@tunable` reader;
   - lint_direct, the six mypy passes, and the three audit checks; review rows if a test's text changed.

## Notes
- Comment blocks are at most 3 prose lines. Text outside `audit/` cites no audit IDs.
- Port-binding runs go in `unshare -n S/u24/ns_xdg.sh`, nice 19, as redo_common says.
- Run to the end; hand back early only as redo_common says.

## Hand-back (the file, per redo_common)
- Commits; the red-first evidence and the bites; the before/after picks per call site; item 2's site list; the runs at
  both stages with wall times; the checks. Last line: "nothing of mine is running".
