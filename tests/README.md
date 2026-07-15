# tests/

Unit tests for `src/` (fully-reviewed code moved out of `improved-quality/` — see CLAUDE.md).

## Why not pytest

Per BACKLOG.md's "Self-contained venv via `uv`" requirement, tests run under a **real
MicroPython interpreter** (the Unix port), not CPython — "as close to the real environment as
possible" means the actual MicroPython runtime, not CPython plus MicroPython-flavored stubs.
Since pytest itself only runs under CPython, it isn't the test runner here: `scripts/test.sh`
instead shells out to a built MicroPython Unix-port binary directly, once per `tests/test_*.py`
file, and checks its exit code. `pytest` stays available in `pyproject.toml`'s dev dependency
group for possible future CPython-side orchestration, but nothing here uses it yet.

## Test framework

`microtest.py` is a minimal collector/runner (find every `test_*` function in a module, call it,
report PASS/FAIL, exit non-zero on any failure) — not CPython's `unittest`, which isn't part of
the MicroPython Unix port's default "standard" build. Test files just use plain `assert`.

## Running

```
scripts/test.sh
```

Builds the MicroPython Unix port on first run (via `uv run toolchain/setup_toolchain.py`'s
`setup` — building/verifying the Unix port is just part of what `setup`/`test` already do, see
`toolchain/README.md` — cached under `$PICO_TOOLCHAIN_DIR`, default `~/pico-toolchain`) and
reuses it afterwards. To run a single test file directly once the interpreter is built:

```
MICROPYPATH="src:tests:.frozen" ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py
```

`.frozen` is required in `MICROPYPATH` (not just `src:tests`) because MicroPython's `MICROPYPATH`
env var replaces the interpreter's default `sys.path` rather than extending it, and the default
path is what makes frozen-in modules (`asyncio` included) importable at all. `math_helpers.py`
never surfaced this since it doesn't use `asyncio`; confirmed directly against the built
interpreter for `crc_checks.py`, which does.

## Hardware-touching files: mock at the raw bus-transaction level only

For a `src/` file that talks to real hardware (`asy_i2c_driver.py` and, eventually,
`asy_spi_driver.py`), the MicroPython Unix port's own `machine` module has no `I2C`/`SPI`/real
`Pin` (confirmed directly: only `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us`).
`tests/machine.py` is a fake `machine` module, resolved ahead of any real one because `tests`
comes before `.frozen` on `MICROPYPATH` — per BACKLOG.md's "Mocking boundary" plan, it mocks only
the raw bus transactions (`readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan`/`deinit`),
backed by a real dict-of-registers store, so the driver's own logic (bit-packing, byte order,
locking, error paths) runs for real against it. Extend this same file (don't add a second,
differently-shaped mock) when `asy_spi_driver.py` goes through its own `src/` promotion.

`tests/base_classes.py` is a separate, narrower case: a minimal stand-in for
`improved-quality/base_classes.py`'s `Lockable`, needed only because that file hasn't cleared its
own `src/` promotion yet and `improved-quality/` isn't on this test `MICROPYPATH`. See
BACKLOG.md's `asy_i2c_driver.py` entry for why this exists and the narrow, self-resolving
`scripts/typecheck.sh` (no arguments) collision it causes until `base_classes.py` is itself
promoted and this stand-in is deleted.
