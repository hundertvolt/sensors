# `digital_twin/` — hardware simulator for the wozi prototype

Step 3 of `FINAL_WIRING_PLAN.md`'s five-step final-wiring effort. A set of fake `machine`/`network`/
`neopixel` modules, sitting at the same raw I2C/SPI bus-transaction mocking boundary
`tests/machine.py` establishes for unit tests, but built for a different purpose: real-time-firing
`Timer`s and randomized-but-plausible sensor values, so Step 5 can run the full assembled
`src/sensortask_wozi.py` prototype under the real MicroPython Unix-port interpreter and have it
behave like it's attached to real hardware — not just satisfy a hand-driven test double.

**Not `tests/machine.py`, does not import it, and is never imported by anything in `tests/`.**
Kept completely separate so nothing here can accidentally affect the deterministic unit-test suite
`scripts/test.sh` runs by default (`MICROPYPATH="src:tests:frozen_modules:.frozen"` — the
`frozen_modules` segment was added in Step 4, see below). See `FINAL_WIRING_PLAN.md`'s Step 3
section for the full design rationale and the owner Q&A round that settled it.

## What's here

- `machine.py` — `Pin`/`I2C`/`SPI`/`Timer`/`WDT`/`RTC`. `Timer` fires for real on a wall-clock
  schedule via an internal `asyncio` task (not `_thread` — see the module's own docstring and
  `FINAL_WIRING_PLAN.md` for why). `I2C`/`SPI` wire the real "wozi" variant's bus layout exactly
  (see `machine.py`'s own docstring): `I2C(0, ...)` carries the SCD30 at `0x61`, `I2C(1, ...)`
  carries the SGP40 at `0x59` and BMP3xx at `0x77`, `SPI(0, ...)` carries the FRAM chip. Any other
  address NAKs — a real bus with a fixed, known set of devices on it, not an unbounded fixture.
- `_sgp40_chip.py` / `_scd30_chip.py` / `_bmp3xx_chip.py` — one chip fake per sensor, each verified
  against its own datasheet in `datasheets/` for the raw transaction shape and sensible value
  ranges. `_scd30_chip.py`'s RDY pin fires a real rising edge on its own internal measurement-
  interval cadence, exercising the real driver's normal IRQ-driven path.
- `_fram_chip.py` — the MB85RS64V FRAM chip's SPI opcode protocol (WREN/WRDI/RDSR/WRSR/READ/WRITE/
  RDID), plus explicit `save_state()`/on-construction load JSON persistence (see "FRAM persistence"
  below).
- `_crc8.py` / `_fault_injection.py` — small shared helpers (CRC-8 for SGP40/SCD30's word protocol;
  a generic op-keyed fault-injection queue, mirroring `tests/machine.py`'s own
  `inject_fault()`/`_maybe_raise()` convention) used by more than one chip fake.
- `network.py` / `neopixel.py` — independent, deliberately duplicated (not reused) copies of
  `tests/network.py`/`tests/neopixel.py`'s own fakes, for full runtime independence from `tests/`.
  `network.py`'s one real behavioral difference: `WLAN.connect()` transitions to a successful,
  connected state immediately, so a live run's WiFi polling loop doesn't wait forever the way the
  unit-test fixture (deliberately inert, hand-driven by test code) would.

Every chip fake exposes a `.fault` (`FaultInjector`) surface for provoking a bus NAK/CRC-corruption/
timeout on demand — off/clean by default.

## Swapping the twin in for a Unix-port run (Step 5)

`src/sensortask_wozi.py` needs **zero twin-awareness** — no `if` branch anywhere distinguishing real
hardware from simulated. The swap is pure `MICROPYPATH` ordering, the same mechanism
`tests/machine.py` already uses transparently for the unit-test suite:

```bash
scripts/build_frozen_html.sh   # one-time (or whenever html_stub/ changes): builds frozen_modules/frozen_html.py
MICROPYPATH="src:digital_twin:frozen_modules:.frozen" <micropython-unix-port-binary> boot_entry/wozi_boot.py
```

`frozen_modules` is required here too, added in Step 4 (landed after this doc's original Step 3
text) — `src/sensortask_wozi.py` now does an unconditional module-level `import frozen_html`, which
resolves from that segment (see `scripts/build_frozen_html.sh`'s own comment for why it can't be
`.frozen` itself). Omitting it fails the run at import time with `ImportError: no module named
'frozen_html'` before any twin code ever runs. `digital_twin` sits between `src` and
`frozen_modules`/`.frozen` — never together with plain `tests` on the same `MICROPYPATH` (that would
let `tests/machine.py`/`tests/network.py`/`tests/neopixel.py` shadow this package's own same-named
modules, or vice versa, depending on ordering — the two are meant to never be on the same path at
once). This is a **separate** invocation from `scripts/test.sh`'s own
`"src:tests:frozen_modules:.frozen"` — Step 5's own session is expected to add a dedicated entry
point (e.g. `scripts/run_digital_twin.sh`) for this, not extend `scripts/test.sh` itself.

### FRAM persistence

The FRAM twin reads back exactly what was written, including across process restarts, but only
ever writes to disk on an **explicit** call — never automatically, to avoid unnecessary write
cycles on an SSD-hosted state file. Whatever entry point Step 5 writes should:

```python
import asyncio
import machine  # digital_twin/machine.py, once MICROPYPATH is set as above

machine.configure_fram_state_path("digital_twin_fram_state.json")  # before constructing spi0
try:
    asyncio.run(main())
finally:
    machine.flush_fram()
```

Omitting `configure_fram_state_path()` (or passing `None`) runs the FRAM twin in-memory only, which
is what every unit test in `tests/test_digital_twin_fram.py` does by constructing `FramChip`
directly (that file never goes through `machine.SPI` at all).

## Running the twin's own tests

Its unit tests live in `tests/test_digital_twin_*.py` (matching every other `src/` module's own
test-file convention), but reach this package via a per-file `sys.path.insert(0, "digital_twin")` —
the same confirmed-safe pattern `tests/test_setter_microdot_integration.py` already uses for
`ext/microdot.py` — rather than a `scripts/test.sh`/`MICROPYPATH` change, so they run under the
exact same default invocation as every other test file:

```bash
scripts/test.sh   # discovers and runs them like any other tests/test_*.py - MICROPYPATH is set
                   # internally per test file (currently "src:tests:frozen_modules:.frozen"),
                   # not read from the calling shell's environment
```

All tests are deterministic — no wall-clock waiting, except one short-period/generous-timeout smoke
test in `tests/test_digital_twin_machine.py` (`test_timer_fires_for_real_on_a_short_period`) that
proves the real-time scheduling mechanism itself works at all, not a precise-cadence assertion.

## Adding a new chip fake

**Required whenever a new sensor driver lands in `src/`** (see `SPECIFICATION.md` C.11's own
checklist item for this — do it the same session the driver is promoted, not deferred) — the
digital twin exists to track the *whole* real driver portfolio, not just the three sensors it
started with. For a new **I2C** sensor this is a small, mechanical addition:

1. Read the sensor's own datasheet first (`CLAUDE.md`'s standing "read the PDF first" rule, `datasheets/`)
   and add a new `_<name>_chip.py` alongside `_scd30_chip.py`/`_sgp40_chip.py`/`_bmp3xx_chip.py`,
   matching their established shape:
   - a `FaultInjector` (`self.fault`, see `_fault_injection.py`) for provoking a bus NAK/
     CRC-corruption/timeout on demand;
   - a `random_source` constructor seam (default `None` → falls back to the real `random` module)
     so tests can script deterministic values, and `digital_twin/launch.py --seed` can reseed every
     chip's walk from one shared source (via `machine.configure_random_source()` or the simpler
     `random.seed()` `launch.py` itself actually uses — see that file's own comment for why);
   - datasheet-sourced `min_*`/`max_*` range constructor arguments, plus the bounded-random-walk
     `*_step` bound every existing chip fake now uses (draw the initial value at construction,
     step-and-clamp on every later reading) — the step bound itself is a **not**-datasheet-derived
     physical-plausibility judgment call, document it as such in the docstring, same as the three
     existing chips do;
   - `handle_writeto()`/`handle_readfrom_into()` (word/CRC-framed protocols like SCD30/SGP40) or
     `handle_writeto_mem()`/`handle_readfrom_mem()` (register-addressed protocols like BMP3xx's)
     answering the *exact* raw transaction shape the real `*_I2C` driver class sends — confirmed
     directly against that file's own source, never assumed.
2. Wire it into `machine.py`'s `_wire_i2c_devices()`: add the new chip to the `dict` for whichever
   bus id (`0` or `1`) the real wiring puts it on (cross-check `src/sensortask_wozi.py`'s
   `build_system()` for the real pin/address assignment), or add a new `if id == N:` branch if it
   lands on a bus id neither SCD30 nor SGP40/BMP3xx already use.
3. Add `tests/test_digital_twin_<name>.py` — deterministic unit tests of the chip fake in isolation
   (no real `machine.I2C` involved, matching every existing `tests/test_digital_twin_{sgp40,scd30,
   bmp3xx}.py`) — then extend `tests/test_digital_twin_machine.py`'s own dispatch tests if the new
   chip shares a bus id those tests already probe.
4. Update this file's "What's here" list and `machine.py`'s own module docstring (the "Bus wiring
   mirrors..." paragraph) to mention the new chip, and consider whether `digital_twin/launch.py`'s
   own `_sensor_loop()`/`_FAULT_DEVICE_OPS` should read from it too.

**A new SPI sensor is not automatically supported yet if it would share an already-occupied SPI bus
id with the FRAM chip.** `_wire_spi_device()`/`machine.SPI` currently wire **one fixed device per
bus id** (matching the wozi prototype's own single-FRAM-on-`spi0` reality) — real multi-device SPI
chip-select is bit-banged by the caller (`asy_spi_driver.py`'s `SPIDevice`, not `machine.SPI`
itself), so a future twin `SPI.write()`/`readinto()` would need to start routing by which CS `Pin`
is currently asserted low, the way `machine.I2C` already routes by address. Not built now because no
such driver exists yet — flagged here rather than left to surprise whoever adds the first one.

## Code quality tooling

`digital_twin/` is in `pyproject.toml`'s ruff/mypy scope, same as `src/`/`tests/` (not
`improved-quality/`'s tracked-debt exemption - this scope is expected to stay fully clean).
`scripts/lint.sh` covers it directly (`ruff check improved-quality src tests digital_twin`).
`scripts/typecheck.sh` runs it as a **second, separate** mypy invocation
(`digital_twin/typecheck.ini`, always run regardless of `"$@"`) rather than folding it into the
main `[tool.mypy]` pass - mypy resolves each bare `machine`/`network`/`neopixel` module name to
exactly one file per run, so this package's own fakes and the real board stubs (`typings/`) can
never both be checked correctly in one invocation. `digital_twin/machine.py`/`network.py`/
`neopixel.py` and `digital_twin/launch.py`/every `tests/test_digital_twin_*.py` are excluded from
the main pass for exactly this reason (see `pyproject.toml`'s own `[tool.mypy]` exclude comment for
the full account, including a real `mypy src tests`-only finding this design caught) and checked
correctly by the dedicated pass instead - see `digital_twin/typecheck.ini`'s own docstring.

## Known gaps / follow-ups for later sessions

- **BMP3xx's fixed calibration block is not sourced from a real chip.** It's a real-shaped,
  hand-picked set of raw coefficient bytes, verified (`FINAL_WIRING_PLAN.md`'s Step 3 section) to
  round-trip cleanly through the real compensation formula across this twin's whole sensible range
  — not literal factory-trim data off actual silicon, which this project doesn't have access to.
- **Fault injection is a bus/chip-level generic queue, not a fine-grained per-condition simulator.**
  `tests/_fram_chip_fake.py`'s own WEL-corruption-specific knobs (`drop_wren`,
  `disturb_write_autoclear`, ...) were purpose-built for `FRAM_SPI`'s own defense-in-depth unit
  tests (already covered by `tests/test_asy_fram_driver.py`) and weren't reproduced here.
