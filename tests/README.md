# tests/

Unit tests for `src/` (fully-reviewed code moved out of `improved-quality/` — see CLAUDE.md).

## Why not pytest

Tests run under a **real MicroPython interpreter** (the Unix port), not CPython — "as close to the
real environment as possible" means the actual MicroPython runtime, not CPython plus
MicroPython-flavored stubs.
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
reuses it afterwards. `SKIP_APT=1 scripts/test.sh` skips that first-run apt-get install if the
required system packages (see `toolchain/versions.toml`) are already present. To run a single
test file directly once the interpreter is built:

```
MICROPYPATH="src:tests:.frozen" ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py
```

`.frozen` is required in `MICROPYPATH` (not just `src:tests`) because MicroPython's `MICROPYPATH`
env var replaces the interpreter's default `sys.path` rather than extending it, and the default
path is what makes frozen-in modules (`asyncio` included) importable at all. `math_helpers.py`
never surfaced this since it doesn't use `asyncio`; confirmed directly against the built
interpreter for `crc_checks.py`, which does.

## Hardware-touching files: mock at the raw bus-transaction level only

For a `src/` file that talks to real hardware (`asy_i2c_driver.py` and `asy_spi_driver.py`), the
MicroPython Unix port's own `machine` module has no `I2C`/`SPI`/real `Pin` (confirmed directly:
only `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us`). `tests/machine.py` is a
fake `machine` module, resolved ahead of any real one because `tests` comes before `.frozen` on
`MICROPYPATH`. Per this project's mocking-boundary convention, it mocks only the raw bus
transactions (`readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan`/`deinit`), backed by a real
dict-of-registers store, so the driver's own logic (bit-packing, byte order, locking, error paths)
runs for real against it.

`tests/base_classes.py` used to be a separate, narrower case: a minimal stand-in for `Lockable`,
needed only because `base_classes.py` hadn't cleared its own `src/` promotion yet and
`improved-quality/` wasn't on this test `MICROPYPATH`. Now that `base_classes.py` (along with its
own dependencies, `config_manager.py` and `print_log.py`) is itself promoted to `src/`, that
stand-in - and the narrow, self-resolving `scripts/typecheck.sh` (no arguments) collision it used
to cause - is gone; `asy_i2c_driver.py`/`asy_spi_driver.py` resolve `Lockable` against the real
`src/base_classes.py` like any other `src/` import.

`tests/test_print_log.py`/`tests/test_base_classes.py` are a third instance of the same mocking
boundary, for FRAM: they now drive `print_log.py`'s `PrintLogHistoryStore` (and, through it,
`base_classes.py`'s `SensorReader`) against the real `AsyFramManager` (`asy_fram_manager.py`, now
itself promoted to `src/`), running against `tests/_fram_chip_fake.py`'s simulated MB85RS64V chip
- the same fake `asy_fram_driver.py`'s own tests use, driven by `tests/machine.py`'s fake SPI.
`PrintLogHistoryStore` only ever calls `AsyFramManager.get_chunk()` and, on the chunk it gets back,
`get_buffer()`/`write_into()`/`read_into()`; `print_log.py`'s own `_FramManager`/`_FramChunk` stay
`TYPE_CHECKING`-only `Protocol`s describing just that narrow surface (kept even now that the real
class is promoted, to avoid a runtime import cycle and stay decoupled from its concrete shape - see
`print_log.py`'s own module docstring). "Survives a reboot" is proven by constructing a second
`AsyFramManager` whose underlying `FRAM_SPI` is pointed at the *same* `FakeMB85RS64V` instance and
replaying the same `get_chunk()` call sequence - genuinely round-tripping through the real
dual-copy+CRC on-chip format, the same as a real chip's contents surviving a power cycle.

Real chip-level fault injection (`tests/_fram_chip_fake.py`'s `drop_wren` etc., and directly poking
simulated on-chip bytes to model a torn write or exhausted dual-copy redundancy) covers every FRAM
failure mode still reachable through the real, audited `AsyFramManager` - a hardware-reported
failure `write_into()`/`read_into()` already turn into a clean `False`, no catch needed. Two
Protocol-level scenarios no longer have a real-class equivalent at all: `asy_fram_manager.py`'s own
`src/` promotion audit confirmed `get_chunk()` never raises and `_write_chunk()`/`_read_chunk()`
wrap their entire bodies in `try`/`except`, so `write_into()`/`read_into()` can no longer actually
raise through it. Those two are still proven via a minimal local `_RaisingFramChunk`/
`_RaisingFramManager` fake (structurally satisfying the same Protocol, not inheriting from the real
classes) in each test file - defense-in-depth against the Protocol contract in the abstract, not
against what this one concrete implementation currently guarantees. This was what caught a real gap
during `print_log.py`'s own review: `_write()`/`_read()` originally called `get_buffer()`/
`get_data_buf()` (and, in `_read()`, `read_into()`) *before* their `try:` block started, so a raise
from any of those would have propagated uncaught instead of degrading to a clean `False` return
like every other FRAM failure here already does. Fixed by widening both `try` blocks to cover the
whole body.

## Coverage

```
scripts/test.sh --coverage
```

Reports line coverage of `src/` only (not `tests/`'s own helper/mock modules). See
`README.md`'s "Code quality tooling" for the usage example and output paths
(`htmlcov/index.html`, `coverage.xml`, `coverage_summary.md`).

Since `coverage.py` only runs under CPython and `src/` only ever runs under the real MicroPython
Unix-port interpreter (see "Why not pytest" above), coverage collection and reporting are two
separate stages, not one tool doing both:

1. `tests/_coverage_runner.py` runs *inside* MicroPython, wrapping each `test_*.py` file with
   `sys.settrace` — verified directly against a real build (not assumed from CPython
   documentation): MicroPython's `sys.settrace` reports the same `(frame, event)` shape closely
   enough that a CPython-style line tracer records exactly the executed-line set `coverage.py`
   itself would expect. It records every line executed whose `co_filename` starts with `src/`
   (so `tests/machine.py` and the test files themselves are never counted) and dumps the result
   as JSON.
2. `scripts/_render_coverage.py` (a separate, self-contained `uv run` script, like
   `toolchain/setup_toolchain.py`) runs under CPython afterwards, merges every test file's JSON
   dump, feeds the result into `coverage.py` via its `CoverageData.add_lines()` API — a
   documented integration point for exactly this "foreign coverage source" case — and lets
   `coverage.py`'s own report engine render the HTML/XML/markdown output from data it never
   collected first-hand.

The one MicroPython Unix port binary (`ports/unix/build-standard/`) backs both plain
`scripts/test.sh` and `scripts/test.sh --coverage` — it's always built with
`MICROPY_PY_SYS_SETTRACE=1` (`build_unix_port()` in `toolchain/setup_toolchain.py`), so there's no
separate coverage-only interpreter to build or cache. Compiling settrace support in adds an inert
hook check in the bytecode dispatch loop when `sys.settrace()` is never called — a negligible,
behavior-neutral cost for a plain (non-coverage) test run, confirmed directly by running the full
suite both ways and comparing results. `ports/rp2`'s firmware build never gets this flag; it's
dev/test tooling only, entirely separate from what ships to real hardware.

No coverage threshold is enforced anywhere — CI reports the numbers, it never fails the build
over them.

### Reading the numbers: three systematic false-negative patterns, not missed test cases

A below-100% file isn't automatically a missed-test hint - three patterns recur across every
`src/` file's "missed" line list and are artifacts of this specific tracing pipeline, confirmed
directly against a real build (`sys.settrace` during both class-body execution and a plain
function call, dumping the traced `(lineno, co_name)` pairs):

- **`micropython.const(...)` assignments are compiled away entirely** — MicroPython folds the
  named constant into every place it's used at compile time, so the assignment statement itself
  never becomes bytecode and never fires a `line` trace event, e.g. `print_log.py`'s
  `_LOG_OFF = const(0)` block. `coverage.py`'s own static analysis (run separately, under CPython,
  by `scripts/_render_coverage.py`) still lists these as executable source lines, so they always
  show as 0-hit misses despite being fully "exercised" in the only sense that's meaningful for a
  folded constant.
- **A decorated function's traced `line` event lands on the decorator line, not the `def` line
  underneath it** — confirmed by tracing a class body's own execution (where a bare `def foo():`
  correctly traces as its own `def`-line hit, but a `@staticmethod`-decorated one traces the
  `@staticmethod` line instead). `coverage.py`'s CPython-based line map still expects a hit on the
  `def` line (matching Python's own `ast` module), so every `@staticmethod`/`@classmethod`
  definition's `def` line shows as missed even when the method is called throughout the suite -
  see e.g. `print_log.py`'s `level_off()`/`level_err()`/etc. or `asy_i2c_driver.py`'s
  `_bitfield_range_ok()`/`_bitmask()`/`_bytes_to_int()`/`_readfrom_mem()`/`_writeto_mem()`. The
  method's own body line (e.g. the `return` statement) is traced normally and shows as covered.
- **A bare `while True:` header never fires its own `line` trace event, at any iteration** —
  confirmed directly (a minimal repro traced every other statement in the loop body across four
  iterations, but never once traced the `while True:` line itself): the always-true condition is
  folded away at compile time into an unconditional jump, the same spirit as the `const()` folding
  above but for a control-flow statement rather than an assignment. Found via `system_service.py`'s
  own `src/` promotion (`status_counter()`'s and `start_and_check_tasks()`'s outer loops), both
  otherwise fully exercised by `tests/test_system_service.py`.

Separately (not a tracer artifact, but also not a missed-test hint): several `except` branches
across `src/` guard against outcomes that are provably unreachable given the guarantees the rest
of the same function already establishes before reaching them - e.g. `crc_checks.py`'s
`add()`/`add_into()` wrap `pack_into()` in a `try` for a `ValueError` that can't fire because the
CRC value is always masked (`crc &= self.all_set`) into exactly the range `self.fmt` encodes, or
`_crc()`'s own `if self.poly is None: return crc` guard, which every current caller already
checks for before ever calling `_crc()`. Writing a test to reach one of these would mean
monkeypatching `struct.pack_into`/an internal method to lie about its own success - testing the
mock, not the driver - so these are left as documented dead code (defense-in-depth against a
future caller violating today's invariants) rather than chased for a coverage number.
`math_helpers.py`'s five `except (ValueError, ArithmeticError)` blocks are the same category: each
function's own domain guard (checked *before* the `try`) already rejects every input - including
NaN/Inf, per `tests/test_math_helpers.py`'s own `*_nan_and_inf_return_none` tests - that could
otherwise reach a math-domain error inside it.
