WR1 hand-back, written by the lane (2026-10-28T00:15Z)

Branch audit/u35-wr1 in S/wt-u35wr1, base 8858db43. Not pushed. The tree is clean: nothing is uncommitted. Logs are in S/u35/laneC/wr1/.

## Commits
- e9fd66dd, item 1. `wiring_read()` now also reads the construction statement of every I2C bus, SPI bus and UART pair a named driver sits on, plus the constants those statements name. It fails, naming the bus, if the generated module builds a touched bus anything other than once. SPECIFICATION.md E.2.1 now says what a wiring read covers, and "the device" a scenario runs on becomes "the devices", which is what the picks are.
- 48aa1356, item 2. `tests/_twin_devices.py` gains `bus_construction()` and `bus_keywords()`.
  - `_shared_bus()` passes the generated statement's keywords and leaves out what the statement leaves out.
  - `_SHARED_BUS_TIMEOUT_US` is gone, together with its tag `l2.bus_hazard_concurrency_shared_bus_timeout_us` and its Part N row.
  - New test: `test_each_shared_bus_is_built_as_its_generated_construction_builds_it`.
  - Further sites changed are listed under "Item 2 sites" below.
- 34aab45e: audit/b3/review.md re-rendered. It now has 8598 rows; the 4 new rows are all "biting as is". Every other change is a line number (checked with a number-stripped sort diff).

## Red first (each seen failing on the code before the change)
- `red_contract.log`, on today's `_twin_devices`: 5 failed.
  - The 4 new rows "its bus's timeout / frequency / SPI bus's construction / UART bus's poll rate" fail at contract :418 with one pick where two are expected.
  - The copy test fails at :454 the same way. It is a real generated module written twice, with one I2C timeout changed.
- `red_missing_bus.log`: on the pre-item-1 code, the missing-construction test fails with "DID NOT RAISE".
- `red_keywords.log`: on e9fd66dd, the keywords test fails with `AttributeError: no attribute 'bus_construction'`.

## Bites (scratch copies; nothing planted was committed)
- bite1, a plant that reads every bus's construction (not only the touched ones). Three checks fail: the row "another driver's bus's timeout", the row "a UART bus no named driver sits on", and the copy test's off-bus assert.
- bite2b, a plant where `_shared_bus` keeps the fixed values. The new test fails: "wozi i2c1: built (1, 19, 18, 50000, 200000), generated 'i2c1 = asy_i2c_driver.I2C(1, 19, 18, frequency=50000)'".
- bite2c, a plant where `bus_keywords` returns `{}` (a `_twin_devices` copy placed beside the test copy). The new test fails: "dev i2c1: built (1, 15, 14, 100000, None) ...".

## Picks before and after, per call site (picks_before.log and picks_after.log, diff empty: 30 of 30 the same)
- bus_hazard :119 `_FRAM_DEVICES` (fram), fram :948, sensortask_integration :338 via :799/:935, network_neopixel :681, wifi_modes :323, sensortask_integration :338 via :983/:1001/:1030 (neopixel, fram): arzi, dev, grkizi
- bus_hazard :808, sgp40 :362/:368/:385, hot_replug :146 `_replug(sgp40)`: arzi, dev, wozi
- bus_hazard :1268, scd30 :715/:723/:731/:739/:745/:753, hot_replug :146 `_replug(scd30)`, ntp :577, sensortask_integration :338 via :1245: arzi, dev
- clock_jump :356, hot_replug :241, hot_replug :146 `_replug(bmp3xx)`, launch :331/:345/:358/:370 `*_READ`: dev, wozi
- hot_replug :146 `_replug(isl29125)`, sensortask_integration :338 via :841: dev
- clock_jump :365/:398/:407/:416, loop_end :258, ntp :538/:545/:552/:561/:568, run_generic_integration :1041, sensortask_integration :338 via :1104/:1128/:1162/:1192, neopixel_wifi_integration :115 (before its neopixel filter): arzi, dev, grkizi, wozi
- sensortask_integration :338 via :600 and via :1302/:1366: arzi, dev, wozi

## Item 2 sites (every asy-driver bus construction on the twin; decisions marked (agent, 2026-10-27))
- These now read the device's construction: bus_hazard `_shared_bus`; `isl29125_autorange` :74 (it lacked dev i2c1's timeout); scd30 :153 (it lacked the arzi i2c0 and dev i2c1 timeouts); sgp40 :291 (it ran at the driver's 100 kHz default, which no device uses).
  - `test_asy_uart_link_driver` `_shipped_rates()` now uses `bus_keywords()` instead of its own parse. The values are unchanged, and the file's exact 22440 ms figure still holds.
- These already read the build: uart_link :286 (it copies the built bus's settings; UM4's file, not touched).
- Comments now say these are harness buses: `machine_uart` :52/:53 and `_uart_comm_harness` :85/:86.
- Left unchanged (agent, 2026-10-27):
  - SPI sites at fram :206, fram_crash_points :59 and generic_wiring :187. The SPI driver takes pins only, so there is no setting to drift.
  - `digital_twin/launch.py` :228/:232. It builds machine-level buses in the src-free CLI from a plan file, with no generated module at hand.
  - About 65 mock-tier sites in 20 files (unit tests, `_bus_hazard_catalog` :580, `_fram_builders` :19). They are built on tests/machine.py fakes that wire no device, so they are harness buses by construction. Lead: say if you want a comment at each.

## Runs at both GC stages (pairs_item2: 100 runs, 1508 s in total)
- 25 files: the 24 `_twin_devices` importers plus machine_uart. The five PER_DEVICE files ran on all 6 devices.
- All rc=0, 0 failed, 0 memory markers. Skips are the pick skips and did not change.
- bus_hazard_concurrency: 25/25 at -1 in 109.3 s, 25/25 at 32768 in 114.7 s. The new test takes 0.27 s; no other file grew. There is no per-file base table in this container, so there is no base time to compare against.

## Checks (e9fd66dd and the 48aa1356 tree)
- lint_direct rc=0.
- The six mypy passes are clean (274/57/312/1/1/1).
- The 19 readers pass (1029). The walk, e51 `--check --self-test` and `review_rows --check` all return rc=0.
- The whole tests_scripts tier on 34aab45e (PICO_TOOLCHAIN_DIR=S/tc-int, whose input hashes equal this tree's): 7053 passed, 9 skipped, 2 failed. The 2 failures are the twin_record pair (`test_every_instrument_has_an_entry`, `test_every_entrys_hashes_are_the_current_files`), which name only tests_hardware files. My diff touches none.
- Silent-failure scan of my files, all classes: none found. A touched bus with no construction used to be skipped silently and now fails loudly. A non-integer or unparsable setting raises.

## Effects
- These are test-only changes: no firmware, generated or build file, and no wear. They make no difference in any operating mode.
- Per device, the twin buses now carry each device's settings: wozi i2c1 is shared at the 50 ms default instead of 200 ms; dev i2c1 and arzi i2c0 gain timeout=200000; sgp40 now runs at 50 kHz on every device.

## Notes for the lead
- `test_digital_twin_sensortask_integration.py` is not changed; CMr1m's file did not need a change for this item.
- N15 (60467ce7) changes none of my files. My twin pairs ran on 8858db43 plus my commits.
- RUNS.md has 40 RUNNING lines and 40 done lines for U35 WR1. The scratch bite copies are deleted.

nothing of mine is running
