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
MICROPYPATH="src:tests" ~/pico-toolchain/micropython/ports/unix/build-standard/micropython tests/test_math_helpers.py
```
