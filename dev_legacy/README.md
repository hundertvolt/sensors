# dev_legacy

Two things live in this directory:

1. **The current, maintained single source of truth for the physical "dev" RP2040 bench unit** —
   wiring, chip identities, confirmed-working status, current bench state, and the mpremote
   workflow for testing `src/` drivers against it. Kept up to date as real-hardware sessions learn
   more; historic debugging narrative is pruned once resolved, not accumulated (see CLAUDE.md's
   documentation-maintenance working agreement).
2. **A historical, frozen-in-time snapshot** of this same unit's onboard filesystem as it was on
   2026-08-27 (the "Legacy on-device filesystem snapshot" section at the end) — kept as reference
   for `src/` promotion work. Not itself reviewed, promoted, or covered by lint/type/test config.

As of 2026-08-28 this unit runs **MicroPython 1.28.0** (matching `toolchain/versions.toml`'s
`[micropython] ref` — the refactor/`src/` target, not the deployed-fleet 1.26 pin) with an
**empty flash filesystem** — it was reflashed and wiped at some point after the 2026-08-27
snapshot below was taken, and no longer represents deployed-fleet (1.26, `python/`/`modules/`)
behavior. It's now used purely as a live test bench for the promoted `src/` drivers, exercised via
`mpremote mount` (see "Testing real hardware from a session" below) rather than by flashing files
onto it.

## Hardware wiring (single source of truth)

Derived from the original 2026-08-27 snapshot's code, then verified against the actual physical
board by the project owner — this table is the authoritative source for wiring this specific
unit, not any code that references it.

| Bus | Pins |
| --- | --- |
| I2C0 | scl=GPIO13, sda=GPIO12, freq=50000 |
| I2C1 | scl=GPIO15, sda=GPIO14, freq=50000 |
| SPI0 | sck=GPIO2, mosi=GPIO3, miso=GPIO4 |

| Device | Bus | Pins / notes |
| --- | --- | --- |
| FRAM | SPI0 | CS=GPIO5 (physical pin 7) — chip is a **MB85RS2MTA**, 256 KB (`max_size=0x40000`); deployed `wozi` uses CS=GPIO1, an **MB85RS64V**, 8 KB (`max_size=0x2000`) |
| BMP3xx | I2C0 | address 0x77 (driver default); physically a **BMP384** |
| SGP40 | I2C1 | address-only (0x59 default), no extra pins |
| SCD30 | I2C1 | interrupt/RDY = GPIO11 |
| MPRLS | I2C0 | reset_pin=GPIO10, eoc_pin=GPIO7 |
| ISL29125 | I2C1 | irq_pin=GPIO6 |
| BME688 (BSEC) | UART0 | tx=GPIO16, rx=GPIO17, 115200 baud — not I2C/SPI |
| Neopixel | — | **GPIO18** (physical pin 24); deployed `wozi` uses GPIO15, a different pin again |
| SHTC3 | — | **not present** on this board (some legacy code wires it, but it's not actually connected) |

### Bench-only jumper: UART0↔UART1 crossover (kept for future tests)

GP0 (physical pin 1) is jumpered to GP9 (physical pin 12), and GP1 (physical pin 2) is jumpered to
GP8 (physical pin 11) — confirmed by the project owner directly on the board. This is a TX↔RX
crossover between the board's own UART0 and UART1 peripherals, used to test two `UART_Comm`
instances talking to each other on the same board rather than to any external device. Not a
sensor/peripheral wiring — a deliberate bench-only loopback jumper, kept in place for further
tests. (`dev_legacy/uart_test.py` in the legacy snapshot below exercises exactly this: UART0
tx=GPIO0/rx=GPIO1 and UART1 tx=GPIO8/rx=GPIO9, matching the physical crossover.)

## Confirmed working — real-hardware test session (2026-08-28)

All currently-wired peripherals were exercised end-to-end against the promoted `src/` drivers on
this bench unit:

- **Neopixel** (GPIO18): confirmed at both the raw `neopixel.NeoPixel` level (red/green/blue/off)
  and through the real `NeopixelDriver` class — direct pixel writes, and three chained 10s
  dim-up/dim-down pulses fired back-to-back via `request_signal()`, correctly serialized in order
  by its own internal lock/event, with no explicit sequencing needed by the caller.
- **SCD30** (I2C1, IRQ=GPIO11): CO2/temperature/humidity all read correctly through the real
  `SCD30_Reader`. The interrupt-sync startup (`scd_init_irq()`'s real-edge + self-healing
  500ms-timer fallback) was verified reliable under every combination of prior data-ready-flag
  state — cleared or left stale before a stop/restart cycle — always resyncing within ~3s and
  never hanging. `stop_continuous_measurement()` shows one grace-period reading completing roughly
  1s after the stop command before the sensor genuinely goes idle (not documented by Sensirion,
  but consistent with an in-flight conversion finishing) — expect this if a future test polls
  data-ready right after issuing stop.
- **SGP40 + VOC algorithm + FRAM** (I2C1): raw/VOC-index reads confirmed; the algorithm's
  documented 45-cycle blackout (`VOCAlgorithm`'s `_VOCALGORITHM_INITIAL_BLACKOUT`) was observed
  exactly — `VOC=0` through cycle 46, real values from cycle 47 on, climbing as the raw signal
  settled. Backup-to-FRAM, restart-from-scratch, restore-from-FRAM (immediately continuing from
  the restored state rather than cold-starting), and reset-including-FRAM (verified via a third
  fresh reader finding nothing to restore) were all confirmed through the real
  `SGP40_Reader`/`AsyFramManager` code paths.
- **FRAM** (SPI0, MB85RS2MTA, 256 KB): full-range write/read-back swept clean across all
  power-of-two address boundaries, confirming the `_KNOWN_PRODUCT_IDS`-keyed chip-identification
  fix (see `SPECIFICATION.md` Part C.3.1) and the driver's own addressing scheme both handle the
  256 KB chip correctly, not just the smaller 8 KB one.
- **BMP384**: breakout had a broken 3.3V trace, running parasitically off the I2C pull-ups until
  repaired 2026-08-28. Retested immediately after with the unmodified, promoted
  `src/asy_bmp3xx_driver.py` — 5/5 clean reads, no `EIO`, stable values (~999.1-999.3 hPa,
  ~26.2°C). The broken trace was the sole root cause; driver code, MicroPython version, and the
  RP2040 I2C peripheral were never at fault.

## Current bench state (as of 2026-08-28)

Facts a future session should know before assuming anything about what's currently on this board:

- Flash filesystem is **empty** — no autostart script, no config files. `src/` drivers are tested
  by mounting the repo (or a precompiled `.mpy` scratch dir) over serial, not by flashing.
- **FRAM currently holds test data, not meaningful production data**: the full 256 KB was
  overwritten by the FRAM range-sweep test's pattern bytes, and a since-cleared SGP40 VOC-backup
  chunk sits at `base_addr=0`. Treat any pre-existing FRAM content as garbage until deliberately
  re-provisioned.
- **SCD30 temperature offset is currently 1.5°C**, not the sensor's power-on default of 0.0°C —
  changed during this session's config test and never reverted (it's NVM-persisted, so it will
  still read 1.5°C after a power cycle). Ambient pressure and altitude compensation are both 0
  (disabled/default). Continuous measurement is currently running.
- **SGP40's VOC algorithm is currently freshly reset** (FRAM backup cleared, blackout re-engaged)
  — a fresh read will start back at `VOC=0` for the first ~45 cycles.

## Testing real hardware from a session (mpremote workflow)

`scripts/mpremote_connect.sh` (see README.md's "Real hardware access" section) wraps `mpremote
connect <device>`; `exec`/`run`/`mount` stay RAM-only, `cp`/`rm`/`mkdir`/`rmdir` write flash.

- Since this bench unit's flash is empty, a `src/` module needs `mpremote mount src <exec|run>
  ...` (or `mount` a directory of precompiled `.mpy` files, see below) to become importable —
  nothing needs to be flashed onto the device first.
- **Light dependency closures** (e.g. `asy_neopixel_driver.py`, or
  `asy_fram_driver.py`+`asy_spi_driver.py`) import fine straight from mounted raw `.py` source.
- **Heavier closures** (anything pulling in `asy_fram_manager.py`, `asy_scd30_driver.py`, or
  `asy_sgp40_driver.py`+`voc_algorithm.py`) can raise `MemoryError` mid-import even with ~200 KB
  free — importing over a remote mount compiles from source on-device with no bytecode caching,
  unlike the frozen-bytecode firmware build. Fix: precompile the needed closure to `.mpy` with the
  toolchain's own `mpy-cross` (`$HOME/pico-toolchain/micropython/mpy-cross/build/mpy-cross`,
  version-matched to the device's firmware — check `mpy-cross --version`'s `mpy vX.Y` against the
  device's `sys.implementation` before trusting it) into a scratch directory, then `mpremote mount
  <that dir> run ...` instead of mounting `src/` directly.
- `micropython.const()` names can't be imported across modules under either approach — they're
  compiled away at the definition site (SPECIFICATION.md Part E.5.1). Inline the literal value in
  the test script instead of importing the constant.
- `SensorReaderConfig`-based modules (e.g. `SGP40_Reader`) carry a `cfgmgr`
  (`config_manager.ConfigManager`) whose own `setup()` does real flash file I/O. For a diagnostic
  script that must not write to the RP2040's own flash, prime `reader.cfgmgr.valid = True` and
  `reader.cfgmgr._cache = {...}` directly instead of calling `cfgmgr.setup()` — every read
  (`get_int_values()` etc.) is a pure in-memory `_cache` lookup once `valid` is set.
- `AsyFramManager` is a bump-pointer allocator (CLAUDE.md). Simulating "the module restarted, FRAM
  persisted" requires constructing a **fresh** `AsyFramManager` per simulated restart, so its
  single chunk allocation lands back at the same `base_addr` — not a fresh reader sharing one
  already-allocated manager instance, which would allocate a second, non-overlapping chunk.

## Legacy on-device filesystem snapshot (2026-08-27, historical)

Verbatim snapshot of this bench unit's onboard filesystem *as it was on 2026-08-27*, pulled over
USB serial via `mpremote` (`scripts/mpremote_connect.sh cp -r :. dev_legacy/`), back when the unit
still ran MicroPython 1.24.1 and held on-device code changes that were never copied to any host
machine. No longer live (the flash is now empty, see above) — kept purely as reference for future
`src/` promotion work.

`sensortask-dev.py` itself is stale/non-functional as captured (wrong `asy_FRAM_manager` import
name, wires SHTC3 that isn't there, hardcodes a Neopixel pin that isn't the real one) —
`sensortask_test.py` is the more internally-consistent reference for what was actually running,
though the wiring table above is the ground truth for either.
