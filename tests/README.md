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

For a `src/` file that talks to real hardware (`asy_i2c_driver.py` and `asy_spi_driver.py`), the
MicroPython Unix port's own `machine` module has no `I2C`/`SPI`/real `Pin` (confirmed directly:
only `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/`time_pulse_us`). `tests/machine.py` is a
fake `machine` module, resolved ahead of any real one because `tests` comes before `.frozen` on
`MICROPYPATH` — per BACKLOG.md's "Mocking boundary" plan, it mocks only the raw bus transactions
(`readfrom_mem`/`writeto_mem`/`readfrom_into`/`writeto`/`scan`/`deinit`), backed by a real
dict-of-registers store, so the driver's own logic (bit-packing, byte order, locking, error paths)
runs for real against it.

`tests/base_classes.py` used to be a separate, narrower case: a minimal stand-in for `Lockable`,
needed only because `base_classes.py` hadn't cleared its own `src/` promotion yet and
`improved-quality/` wasn't on this test `MICROPYPATH`. Now that `base_classes.py` (along with its
own dependencies, `config_manager.py` and `print_log.py`) is itself promoted to `src/`, that
stand-in - and the narrow, self-resolving `scripts/typecheck.sh` (no arguments) collision it used
to cause - is gone; `asy_i2c_driver.py`/`asy_spi_driver.py` resolve `Lockable` against the real
`src/base_classes.py` like any other `src/` import.

`tests/_fram_mock.py` is a third instance of the same mocking boundary, for FRAM: `print_log.py`'s
`PrintLogHistStore` only ever calls `AsyFramManager.get_chunk()` and, on the chunk it gets back,
`get_buffer()`/`write_into()`/`read_into()` - not `asy_fram_manager.py`'s actual allocator/CRC/
dual-copy-redundancy machinery, which isn't itself promoted to `src/` yet (see BACKLOG.md). Rather
than a hand-written stand-in class, `print_log.py`'s own `_FramManager`/`_FramChunk` are
`TYPE_CHECKING`-only `Protocol`s describing just that narrow surface, so `tests/_fram_mock.py`'s
fake satisfies them structurally with no inheritance relationship to the real classes at all.
`MockFramBacking` simulates the one behavior that actually matters for `PrintLogHistStore`'s
"survives a reboot" purpose: constructing a second `MockAsyFramManager` around the same
`MockFramBacking` instance and replaying the same `get_chunk()` call sequence lands on the same
offsets (matching the real bump-pointer allocator), so previously-written data reads back exactly
as a real chip's contents would across a power cycle. Remove `tests/_fram_mock.py` (and the tests
built on it in `tests/test_print_log.py`) once `asy_fram_manager.py` itself clears its own `src/`
promotion checklist and a real `AsyFramManager` becomes available under `tests/` instead.

The mock also supports fault injection covering every FRAM failure mode `print_log.py` guards
against - `MockAsyFramManager(out_of_memory=...)`/`raise_on_get_chunk=...`, and per-chunk
`.raise_on_get_buffer`/`.broken_buffer`/`.raise_on_write`/`.write_returns_false`/`.raise_on_read`/
`.read_returns_false` flags settable directly on the `_MockFramChunk` a `PrintLogHistStore`
instance exposes as its own `.fram` attribute (see `tests/_fram_mock.py`'s docstring for what each
simulates). This was what caught a real gap during `print_log.py`'s own review: `_write()`/`_read()`
originally called `get_buffer()`/`get_data_buf()` (and, in `_read()`, `read_into()`) *before* their
`try:` block started, so a raise from any of those - plausible, since `asy_fram_manager.py` isn't
itself audited yet - would have propagated uncaught instead of degrading to a clean `False` return
like every other FRAM failure here already does. Fixed by widening both `try` blocks to cover the
whole body; `.broken_buffer` (a `get_buffer()` that "succeeds" but returns an unusable, zero-length
buffer) is the regression test for exactly this - it makes `struct.pack_into`/`struct.unpack_from`
raise on the buffer's now-`None` `get_data_buf()`, which the widened `try` must catch. There's no
"corrupt the persisted bytes to make struct.unpack_from() raise" fault mode: `get_buffer()` always
hands back a freshly-sized buffer derived from the same `len(history)` used to write it, so a
length mismatch in struct's own sense can only come from `get_buffer()` itself misbehaving -
`.broken_buffer` already covers that; there's no way to reach it by varying what was previously
read back.

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
