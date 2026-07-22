# BACKLOG

Running knowledge base for the `improved-quality/` refactor: spec/requirements, decisions made,
functional clarifications, review findings, open questions, deferred work, security notes. See
README.md for orientation, CLAUDE.md for operating constraints.

## Final-goal requirements for the refactor (owner-specified)

Target for `improved-quality/`; not actioned until refactor work starts except where marked
**[DONE]** — the ruff/mypy/stub/test tooling below was deliberately pulled forward (see
"Sequencing").

- **Stability**: no error condition that can plausibly occur should lead to an uncaught exception;
  everything catchable gets caught and handled. Hardware watchdog is a last resort (brownout,
  interpreter-level failure), not routine recovery. Bare `except:` forbidden in refactored code —
  `except Exception:` or narrower required. Ruff's E722 is already enabled (not silenced) so
  existing bare excepts in `improved-quality/` show as tracked findings; eliminating them is still
  real refactor work.
- **No leaks, no drift**: must run indefinitely without exhausting memory/handles/counters.
  Verified via code review/design discipline (bounded buffers, no unbounded growth) — no automated
  soak test, no CI gate for this.
- **Production-level code quality [DONE for current scope]**: unit tests + mypy + ruff as both
  shell scripts and CI (GitHub Actions, `.github/workflows/ci.yml`), scoped to
  `improved-quality/`/`src/`/`tests/`. Old `improved-quality/mypy.ini`/`pycheck.sh` retired in
  favor of root `pyproject.toml` + `scripts/lint.sh`/`typecheck.sh`/`test.sh` (rationale: CLAUDE.md
  "Code quality tooling"). **Still open**: CI doesn't attempt a real firmware build yet (blocked on
  `build-*.sh`'s hardcoded `/home/nico/rpi_pico/...` path genericization — elevated from
  someday-work to a near-term prerequisite once CI existed); pre-refactor `python/`/`modules/`
  stays out of lint/type scope.
  - MicroPython stubs **[DONE]**: `micropython-rp2-rpi_pico_w-stubs` (PyPI), version
    auto-derived by `scripts/typecheck.sh` from `toolchain/versions.toml`'s `[micropython] ref`
    (currently 1.28.0), installed into gitignored `typings/` (isolated from the main dev venv —
    see CLAUDE.md for why that isolation matters). Fails loudly, not silently stale, if no
    matching stub release exists yet.
  - Ruff/mypy config **[DONE]**: stricter than default on real correctness, but no line-length
    enforcement (`ruff format` deliberately unused, deliberate style choice). mypy does NOT disable
    the `assignment` error code (the old `improved-quality/mypy.ini` did; never a deliberate
    choice).
  - No hard coverage gate **[DONE, deliberate]**: `scripts/test.sh --coverage` + non-gating CI step
    report `src/` line coverage (HTML/Cobertura/markdown); never enforced, no plan to add a
    threshold.
  - PEP 604 union syntax (`int | None`) confirmed safe at runtime on MicroPython 1.26 and 1.28.0:
    the compiler parses but never evaluates annotation expressions (documented back to 1.15/1.16
    docs, not version-specific) — see MicroPython docs "Syntax"
    (https://docs.micropython.org/en/latest/genrst/syntax.html). No `from __future__ import
    annotations` needed.
- **Self-contained venv via `uv`**: tests must run under the real MicroPython interpreter (Unix
  port), not CPython+stubs.
  - Unix-port build/verification **[DONE]**: `toolchain/setup_toolchain.py`'s `setup`/`test`
    verify the whole toolchain via an 8-step frozen-bytecode chain (freeze a test module into both
    Unix port and RP2 firmware, import it *by name* with no source `.py` on disk, clean up, rebuild
    a vanilla Unix port as the standing test rig) — see `toolchain/README.md` "Verification".
    Needs `libffi-dev` (in `versions.toml`'s `apt_packages`) for the Unix port's `ffi` module.
  - Wired into the test suite **[DONE]**: `scripts/test.sh` runs `setup` automatically the first
    time it needs the interpreter, then reuses the cache (`$PICO_TOOLCHAIN_DIR`, default
    `~/pico-toolchain`) — so `uv sync && scripts/test.sh` is the complete onboarding path, locally
    and in CI.
  - Mocking boundary: mock only at the raw bus-transaction level (`machine.I2C`/`machine.SPI`
    read/write) — drivers, Readers, `ConfigManager`, REST handlers run for real, unmocked.
    `tests/machine.py` is the concrete instance (fake `I2C`/`SPI`/`Pin`, dict-of-registers store,
    fault injection). `network`/CYW43 (WiFi) is in the same "mock it, no other way" tier — the Unix
    port has no real WiFi hardware.
- **Centralized config [DONE]**: all dev-tooling config lives in root `pyproject.toml`
  (ruff/mypy/pytest/uv) — shipped code stays frozen-bytecode-only, not an installable package.
- **Unified CRC-based data-integrity checking**: `improved-quality/crc_checks.py`'s generic
  `CRC8`/`CRC16`/`CRC32` engine (with `CRC_Pass` no-op) grew from UART → I2C sensor CRC8
  (SCD30/SGP40) → unified class → FRAM chunk protection. Confirmed intentional, evolving feature —
  keep applying it wherever data integrity matters.

### Bus/sensor error-recovery robustness (owner-specified, not yet implemented)

From hands-on field experience with deployed units:

- **Nested try/except correctness**: past crashes came from catching too early (masking) or too
  late (uncaught). Confirmed right granularity: one broad `except:` around a whole per-iteration
  multi-command read (e.g. `asy_scd30_driver.py`'s `read_scd()`), full task-death + supervisor
  respawn as the only deeper reset — don't split into finer per-command catches. Distinguish
  exception types only where genuinely different handling is needed; the one hard rule is nothing
  may ever silently slip through uncaught.
- **Live bus reconnect must be preserved**: field-tested (physically disconnect/reconnect an
  I2C/SPI wire on a live unit, sensor reconnects without reboot). Confirmed mechanism:
  task-death-and-respawn (dead reader task → supervisor restarts → fresh `setup()`) — but owner
  flagged it may be incomplete; revisit/harden during the refactor, don't assume complete.
- **Sensor/bus-specific defined-state recovery** (clocking out fixed cycles, reset
  sequences/commands) should be as complete as possible, per bus/sensor type.
  - **Correction**: `extra_clocks` is NOT an existing mechanism — appears only as an unused
    Adafruit-derived docstring line on the legacy `asy_spi_driver.py` constructor, never
    implemented anywhere (not even in `improved-quality/`). If SD-card-style post-deassert clock
    cycling is wanted, it needs designing from scratch.
  - I2C recovery is device-specific (check what each driver already does before assuming a gap);
    generalize only if a mechanism turns out to be genuinely common. *(`asy_scd30_driver.py`'s and
    `asy_sgp40_driver.py`'s reset paths reviewed so far — the latter was a confirmed real bug (see
    its own `src/` promotion entry below), not just a review with nothing found; BMP3xx's reset
    command still needs the same review.)*
  - FRAM's SPI bus gets the same bus-recovery treatment as sensor buses. **Partially done**:
    `asy_fram_driver.py`'s own `src/` promotion (see "`asy_fram_driver.py` → `src/`" below) fixed a
    real device-identification bug and added write-enable-latch/write-protect verification - the
    detection this file itself can do. Still open: an actual periodic/triggered re-probe policy
    (calling `verify_present()`, still zero callers anywhere - see "`asy_fram_manager.py` → `src/`"
    below) and task-death-and-respawn wiring both live in `asy_fram_manager.py`/a task supervisor;
    `asy_fram_manager.py` is now promoted (its own audit didn't add this wiring, out of scope for a
    quality-audit pass) but a task supervisor for FRAM specifically still isn't.
  - Keep error handling per-driver, not a shared generic retry/backoff/reset framework — sensors
    differ enough that a forced common abstraction was explicitly rejected. Only generalize what's
    genuinely common to *all* drivers (e.g. error-counter bookkeeping in
    `SensorReader._error_check()`).
- **Blocking calls need a timeout or other unblock mechanism.** Known case: SCD30 (own onboard MCU)
  has hung the bus in the field — MicroPython's cooperative scheduler can't preempt a synchronous
  `machine.I2C` call already in progress, so an asyncio-level timeout can't interrupt a genuinely
  wedged transaction. **Decided**: for a truly stuck bus/sensor, the hardware watchdog is the
  accepted backstop, not a software fix to chase; current task-supervisor error-budget behavior is
  adequate. For calls that genuinely *can* be timeout-wrapped (`socket.getaddrinfo()`, FRAM SPI,
  anything not a raw blocking `machine.I2C` call mid-transaction), standardize on one consistent
  timeout/cancellation mechanism everywhere.
- **Bus concurrency via `asyncio.Lock` + `async with` needs a coverage audit** (no gaps, no
  deadlock/starvation). Concrete progress: `asy_scd30_driver.py`/`asy_bmp3xx_driver.py`/
  `asy_sgp40_driver.py` each have a `*_DeviceSession(Lockable)` class — an outer per-sensor lock
  around the whole write-then-read transaction, with an explicit `await asyncio.sleep(0)` yield
  between phases so the bus lock isn't held across a lock-then-forget gap. Treat as the pattern to
  verify/extend. **Open question**: several setter/getter methods on these Readers were changed
  from bare pass-through coroutines to `try/except Exception: return False/None` — not verified
  whether the swallowed exception is still logged via `self.pr`, which would be a silent-failure
  risk if not.

### Code structure / style patterns for the refactor

Owner: much of this is already underway in `improved-quality/` — recorded as the bar to hold the
rest of the refactor to.

- **Define configs/behavior used at multiple sites in exactly one location.** Concrete mechanism:
  `asy_scd30_driver.py`/`asy_bmp3xx_driver.py`/`asy_sgp40_driver.py` each define per-field config
  schema tuples (`_VAL_*`) and expose `get_dict_cfg()`/`get_dict_data()` — the actual answer to the
  config-duplication problem, not fully wired end-to-end yet.
- **Handle device/sensor/functional config storage separately** — per-sensor via
  `SensorReaderConfig`'s own `config_<name>.cfg` file, already done. **Target model**: every config
  value ends up per-device, per-feature, or explicitly global, never implicitly coupled to
  something unrelated. Unresolved: network/WiFi and Neopixel config still share one ad hoc
  top-level `ConfigManager` in `sensortask-wozi.py` (confirmed intentional intermediate state) —
  needs its own clearly-scoped global config.
- **Reduce code size via inheritance** — e.g. `base_classes.py`'s `SensorReader`/
  `SensorReaderConfig`, `asy_fram_manager.py`'s `_AsyBaseFramChunk` base with
  `AsyFramChunk`/`AsyFramTimestampedChunk` subclasses.
- **Generalized startup/error-recovery** — `SensorReader._error_check()` centralizes the
  increment/decay/give-up logic every `sensortask-*.py` hand-rolls today. Mechanism:
  `get_task_starters()`/`get_timer_starters()` let `system_service.py`'s generic supervisor
  discover/start each driver's tasks without hardcoding method names.
- **Trace-log error codes inside FRAM, surviving reboot** — `print_log.py`'s
  `PrintLogHistoryStore`. **Store errors alongside console prints, not instead of them** —
  `err_s()`/`wrn_s()` both persist and still `print()`.
- **Handle FRAM more generically** — `asy_fram_manager.py`'s chunk-class hierarchy +
  `LockableBuffer`-based buffers is the intended model.
- **Prefer preallocated buffers/in-place writes over allocate-and-return, bulk bus transactions
  over per-byte loops** — recurring pattern (`asy_fram_driver.py`'s `get_values`/`set_values`,
  `asy_fram_manager.py`'s reused `LockableBuffer`s, FRAM SPI's single bulk `write()` instead of a
  per-byte loop, SGP40's persistent command/CRC buffer slices). Supports "no leaks, no drift";
  apply wherever a hot-path allocation or per-byte loop turns up.
- **Generalize hardcoded constants into parameters when consolidating duplicated code** — e.g. the
  old `TimeCounterManager`'s baked-in 50-year cap became `LockedCounter`'s `max_val` constructor
  parameter.
- **Refactor identical/similar behavior into classes**, scoped to what's genuinely common across
  drivers (error-counter bookkeeping, FRAM chunk handling, config storage) — not bus/sensor-specific
  recovery, which stays per-driver (see above).
- **Refactor long/deep flows into subfunctions with early-return** — current `sensortask-*.py` REST
  handlers and `async_connect.py`'s `wlanConnect()` are examples of what *not* to carry forward.

### Sequencing (rough priority, not a committed plan)

1. Dev/build environment setup (genericized `build-*.sh`/toolchain paths) — everything CI/firmware
   depends on this first.
2. Per-sensor config storage + other structural patterns (inheritance, FRAM chunk handling,
   error-counter bookkeeping).
3. Bus/sensor error-recovery robustness — needs the structure above to refactor into.
4. Tooling/CI (mypy/ruff, stubs, Unix-port test setup, unit tests, firmware-build CI stage) — comes
   last in principle, but mypy/ruff/stubs, the Unix-port build, `math_helpers.py`'s
   `src`/`tests` pair, and the lint/typecheck/test GitHub Actions pipeline were all pulled forward
   once `math_helpers.py` cleared the "fully reviewed" bar (scoped exception, not a resequencing).
   Extending `src/`'s scope to more files is now ongoing incremental work. Still blocked on the
   firmware-build CI stage (needs #1).

## `src/` promotion findings

File-by-file review comparing `improved-quality/` against legacy equivalents (or reading cold where
there's no legacy equivalent), checked against `src/README.md`'s promotion checklist. Real bugs,
decisions, and deferred items below; process narrative (how many review passes, "verified via
ruff/mypy/tests" after every change) is omitted — assume every change below was lint/type/test-clean
before landing.

**Cross-file wiring gaps in `improved-quality/` are known WIP, not regressions** (confirmed by
owner): `api_helpers.py` vs. `config_manager.py`'s `get_dict`/`write_config` signatures mismatch at
exactly a `# TODO what to do if...` comment — a deliberate pause point. `neopixel_signal.py` simply
hasn't been refactored yet (wrong `async_manager` import, `get_int_values`/`get_float_values`
mixup). `sensortask-wozi.py`'s misplaced `ntp_force_sync()` call inside the recurring supervisor
loop was a deliberate temporary NTP-bug fix never moved back to its one-time pre-loop position — a
known loose end. Individual files being far along doesn't mean the subsystem works end-to-end; an
integration pass reconciling call sites is still needed.

`improved-quality/microdot.py` is a confirmed *unintentional* fork (owner-confirmed) — action when
refactor work resumes: revert to match vendored upstream exactly, no behavioral additions ever.
Not touched now (`improved-quality/` source stays out of routine editing). Distinct from
`python/CommonDrivers/microdot.py`, which is verified to still match upstream exactly.

### `math_helpers.py` → `src/`

First file promoted. `wet_bulb_temperature`'s humidity lower bound was `0.5%`; Stull (2011) only
validates down to `5%` — real bug, fixed. `altitude_baro`'s 300–1250 hPa / -40–85°C range comes
from the BMP388/390 datasheet (its only caller), not the barometric formula itself. 45 tests
(`tests/test_math_helpers.py`).

### `crc_checks.py` → `src/`

Correctness verified against Sensirion's own datasheet test vectors, CRC-16/CCITT-FALSE, and
CRC-32/MPEG-2 standards. Exception handling narrowed to `ValueError` specifically (not broad
`except Exception:`). Missing negative-value/length guards added. A table-driven (256-entry LUT)
implementation was considered as a speed optimization and explicitly declined — real usage here is
small buffers (2–3 byte sensor CRC8, modest FRAM chunks), RAM cost (~1KB for CRC32) not worth it;
revisit if a future caller pushes larger buffers through. A later coverage-gap pass (commit
`eb67ea7`) added 4 tests for `check()`/`check_from()`'s init/size/start rejection paths, which had
mirrored `add()`/`add_into()`'s already-tested validation but were themselves unexercised (94%→100%
line coverage). 66 tests total (`tests/test_crc_checks.py`).

### `asy_i2c_driver.py` → `src/`

First hardware-touching file promoted — established the "raw bus-transaction calls may propagate
`OSError` uncaught" carve-out (`src/README.md` section 2): a real transaction failure is allowed to
propagate out of the low-level bus driver rather than being swallowed, matching every current
Reader's existing pattern of wrapping a whole read/write sequence in its own `try/except`.

Real bugs found and fixed:
- `I2C.deinit()` never called the real `machine.I2C.deinit()` (only dropped the Python reference) —
  true in both the legacy driver and this file, unlike `asy_spi_driver.py`'s `SPI.deinit()`, which
  already called the real thing. Fixed to match.
- `set_bits()` took a separate `endian` param independent of its own `lsb_first`; `set_register_struct()`
  took a separate `endian` param instead of deriving byte order from `reg_format`'s own prefix (like
  `get_register_struct()`'s `struct.unpack` already did) — both could silently disagree with the
  read-side byte order for a multi-byte register. No current caller ever exercised this
  (`reg_width=1` everywhere in use today). Fixed by dropping the separate `endian` param from both.
- `set_bits()` shifted `value` into the register without masking to `num_bits` width first — a
  wide `value` could silently corrupt bits above the field. Fixed via the shared `_bitmask()`
  helper.
- `writeto_then_readfrom()`/`write_then_readinto()` had one shared `stop` param for both
  legs — couldn't express the standard repeated-start register-read pattern (write without stop,
  read with stop). Fixed: split into independent `out_stop`/`in_stop`, defaults unchanged
  (`True`/`True`, pure capability addition). No current caller uses this yet; a future
  repeated-start caller must pass `out_stop=False` explicitly.
- `get_register_struct("")` (or any zero-data-field format, e.g. `"2x"`) raised an uncaught
  `IndexError` indexing `struct.unpack()`'s empty result — fixed by checking non-empty before
  indexing.
- `set_register_struct()`'s `value` was typed `int`-only, but `get_register_struct()` returns
  `int | float | bytes` — `struct.pack()` raises `TypeError` (not `ValueError`) for a type
  mismatch, previously uncaught. Fixed: widened `value` to `int | float | bytes | bytearray`,
  catch `TypeError` alongside `ValueError`.
- `writeto()`'s `str`-buffer convenience path (`bytes([ord(x) for x in buffer])`) raised an
  uncaught `ValueError` for any Unicode codepoint above 255 — confirmed reachable for in-domain
  `str` input. Fixed: catch and return `None`.

Other changes: `get_bits()`/`set_bits()` gained a range guard (`num_bits`/`start_bit`/`reg_width`
sanity-checked, previously unguarded). `scan()`/`writeto()` widened to return `None` instead of
magic defaults (`[]`/`0`) when the bus isn't initialized, matching the project's "`None` = no data"
convention — `I2CDevice` and the sensor drivers don't check these yet (flagged, not fixed; no
current caller relied on the old defaults either). Byte-order reconstruction and range-guard logic
extracted into shared `_bytes_to_int()`/`_bitfield_range_ok()`/`_bitmask()` helpers. Two no-op
params added (`I2C.__init__`/`init()`'s `timeout: int | None = None`,
register-methods' `addrsize: int | None = None`) surfacing real `machine.I2C` params this driver
didn't expose; `None` omits the kwarg rather than duplicating `machine.I2C`'s own default.
`import asyncio` replaced the redundant `from uasyncio import Lock`; no `typing` import needed at
all in the final file. Confirmed real RP2040 I2C error codes for `tests/machine.py`'s fault
injection: hardware I2C only raises `OSError(EIO)` (NAK/bus fault) or `OSError(ETIMEDOUT)`
(bus-busy/clock-stretch timeout) — not `ENODEV`, which is `SoftI2C`-specific. Documented (not
fixed) a MicroPython `struct.pack` quirk: silently zero-pads/truncates on a value/argument-count
mismatch instead of raising `struct.error` like CPython.

Deferred, flagged not fixed: `get_bits`/`set_bits`/`get_register_struct` still call the allocating
`readfrom_mem()` rather than zero-copy `readfrom_mem_into()` — no real callers yet besides the
not-yet-migrated `asy_isl29125_driver.py`; worth doing before that migration.

`tests/base_classes.py` (a minimal `Lockable` stand-in, needed because `base_classes.py` itself
wasn't promoted yet) caused a narrow "Duplicate module named base_classes" collision under an
unscoped `scripts/typecheck.sh` (CI unaffected — it passes explicit `src tests` paths). Resolved:
deleted once `base_classes.py` was itself promoted. 77 tests total
(`tests/test_asy_i2c_driver.py`).

### `asy_spi_driver.py` → `src/`

SPI's fault surface is materially different from I2C's, confirmed against MicroPython v1.28.0
source (`extmod/machine_spi.c`, `ports/rp2/machine_spi.c`): real hardware SPI `write()`/
`readinto()` have **no error return at all** (no ACK/NAK concept) — cannot raise, full stop, not
merely "in practice, let it propagate" the way I2C's `OSError` carve-out works. `write_readinto()`
is the one exception (`ValueError` for mismatched buffer lengths — a caller-input mistake, caught
and turned into `None`). `src/README.md` section 2 was written I2C-generically and updated with
this SPI-specific finding on explicit direction.

Real bugs found and fixed:
- **Most severe finding of this promotion, with a live production caller**: `SPIDevice.__aenter__`
  leaked the bus lock and left the CS pin stuck asserted permanently whenever it raised *after*
  acquiring the lock (`configure()` raising on a deinitialized bus, or task cancellation during the
  1ms post-assert settle sleep) — since `__aenter__` itself raises, `async with` never calls
  `__aexit__`. Present in the original hand-rolled file too, not introduced by this promotion's
  `Lockable` refactor. A stuck-asserted CS blocks every other device sharing the bus (CS is a
  shared-bus signal). Fixed: wrapped `__aenter__`'s post-lock-acquire steps in
  `try/except BaseException` that deasserts CS and releases the lock before re-raising.
- `SPIDevice.__aenter__` had no guard against being reached before `setup()` ran. `Pin.value(x)`
  calls `gpio_put()` unconditionally regardless of direction (confirmed via
  `ports/rp2/machine_pin.c`), so entering before `setup()` wouldn't raise — it would silently fail
  to ever assert CS on real hardware. Every real caller already calls `setup()` first (latent
  footgun, not active). Fixed: `self.uninitialized` flag (reusing `asy_fram_driver.py`'s
  `FRAM_SPI.uninitialized` naming), checked at the start of `__aenter__` with a clear
  `RuntimeError`.
- Original file was literally unimportable on the real Unix-port interpreter
  (`ImportError: no module named 'typing'`) — an unconditional `from typing import Type` plus a
  bare `try: from types import TracebackType except Exception: pass`. Resolved with zero
  typing-only imports needed at all; `SPIDevice.__aexit__` typed with plain `object` params instead
  (it only forwards them to `super().__aexit__()`, never inspects them).

Other changes: `write()`/`readinto()` were typed `int | None` but confirmed (via
`extmod/machine_spi.c`) to always return `None` on this port — narrowed to plain `None`. Dead
`except AttributeError` around `deinit()` removed (a bound method on a real `machine.SPI` object
can't raise it — `SPIDevice`'s `deinit()` already called the real thing, only the leftover `except`
needed removing). `SPIDevice` converted to subclass `Lockable`, matching `I2CDevice`'s shape.
`configure()`'s `RuntimeError`-on-unlocked-call kept as a programmer-error guard (not converted to
`None`), confirmed via explicit sign-off since this file has a live caller
(`asy_fram_driver.py`'s `FRAM_SPI`); split into two distinct error messages for clarity.
`extra_clocks` stays unimplemented (see the correction above). No register/bit-field helpers added
— SPI has no addressing concept at this layer. Protocol-driven asymmetries vs. I2C (no `probe`
param, `SPIDevice` alone overrides `__aenter__`/`__aexit__` for CS handling, no `timeout` param —
confirmed no SPI timeout concept exists on this port) are intentional, not inconsistencies. Cross-file
naming unified between this file and `asy_i2c_driver.py`: both now use `buf` for a single buffer
and `buffer_out`/`buffer_in` for the two-buffer case (found during a bird's-eye scan, reported then
resolved on direction rather than silently fixed). `tests/machine.py` extended with `class SPI` +
real `Pin.init()`/`.value()` readback (confirmed real rp2 `Pin.value()` does a genuine `gpio_get()`
readback even for an `OUT` pin) — deliberately doesn't reuse I2C's fault-injection shape, since real
SPI `write()`/`readinto()` have no fault path to inject. Two previously prose-only claims were
proven by test: rp2 hardware SPI raising `NotImplementedError` for `firstbit=SPI.LSB`, and two
different devices' CS pins never being simultaneously asserted (checked via real `Pin.value()`
during concurrent `asyncio.gather`). A module-docstring inaccuracy was later fixed: `configure()`
is an `SPI` method (not `SPIDevice`'s), and only `configure()` takes `firstbit` (not
`SPI.__init__()`/`init()`).

Deferred, flagged not fixed at the time: `FRAM_SPI.set_write_protected()`/`get_write_protected()`
(in `asy_fram_driver.py`, not itself promoted yet) had zero real callers. **Resolved during
`asy_fram_driver.py`'s own `src/` promotion** (see below): owner confirmed keeping them, brought to
the same quality bar as the rest of the file. Several methods deliberately
raise rather than return `None` (`SPI.__init__()`/`init()`'s `ValueError`, `SPIDevice.__init__()`'s
same via `Pin(cs_pin)`, `configure()`'s `RuntimeError`/`NotImplementedError`) — today's only caller
doesn't wrap any in `try/except` (fine today since correctly-`setup()`'d production code never
triggers these); future `SPIDevice` consumers must check their own upstream handling.

43 tests total (`tests/test_asy_spi_driver.py`). Baseline: `improved-quality/` unscoped lint finding
count dropped by exactly this file's own 3 pre-existing findings (320→317), no regression
elsewhere.

### Test infrastructure

`scripts/test.sh`'s `MICROPYPATH="src:tests"` silently shadowed every frozen stdlib module
(`asyncio` included) for every test file — invisible until `crc_checks.py`'s tests (the first `src/`
file needing `asyncio`) since `MICROPYPATH` *replaces* the interpreter's default `sys.path` rather
than extending it, dropping the `.frozen` entry. Fixed: `MICROPYPATH="src:tests:.frozen"`.
Confirmed but not fixed: `typing` isn't importable at all on this Unix-port build — most
`improved-quality/` files do an unconditional `from typing import ...`, which would fail
identically if executed; a latent, codebase-wide issue to address per-file at each one's own `src/`
promotion (see the `TYPE_CHECKING`-guard pattern established below for `base_classes.py`/
`config_manager.py`/`print_log.py`).

### Confirmed real bug fixes already present in `improved-quality/` (don't reintroduce)

A `NameError` typo in the legacy FRAM driver's write-protect pin setup (`_wp_pin` vs.
`self._wp_pin`); a legacy `BMP3XX_I2C.setup()` using `await` inside a non-`async def` (a literal
compile-breaking defect — worth confirming whether this method is ever reached on deployed units);
a legacy SGP40 VOC-algorithm FRAM serialization bug where `m_mox_model_sraw_std` was never included
in the packed/restored fields, so restore-from-FRAM silently never recovered it; several smaller
`api_helpers.py`/`async_connect.py`/`captive_dns.py` fixes for `None`-guard crash paths and an
unbound-local variable. **Correction, found during `asy_udp_socket.py`'s own `src/` promotion:**
that file's own `None`-guards were *not* a clean instance of this pattern - see the dedicated
write-up below for what was actually wrong with them.

### Timing values confirmed intentional, not drift

`asy_scd30_driver.py`'s `_read_register()` inter-command delay (0.005s→0.05s) and
`asy_sgp40_driver.py`'s initial serial-number-read delay (10ms→3ms) were owner-tested to produce
more stable operation. Keep; prefer measuring over assuming when tuning similar delays elsewhere.

### `base_classes.py` + `config_manager.py` + `print_log.py` → `src/`

Promoted together on owner's direction — `base_classes.py`'s `SensorReader`/`SensorReaderConfig`
depend on both, and testing against hand-written stand-ins for logging/config storage wasn't
acceptable. Resolves the "`typing` import gap" flagged above for exactly these two files.

**Real bugs found in `config_manager.py`** (both pre-existed in `base_classes_old.py`, never
exercised end-to-end before — nothing in `improved-quality/` ran on real hardware end-to-end yet,
and no tests existed against this file until now):

1. `cfg_from_str()`/`str_cfg()`'s `cfg_vals[1:-2]` (should be `[1:-1]`) stripped one character too
   many off the `"|...|"`-wrapped schema string's end. `str_cfg()` never surfaced this (only reads
   the substring before the first `:{`), but `cfg_from_str()` needs the full JSON body — the
   truncation always dropped the final `}`, so `json.loads()` always raised and `cfg_from_str()`
   always returned `{}`. Since `ConfigManager.__init__()` bails when `cfg_from_str()` returns
   empty, **`ConfigManager.valid` could never become `True` for any real caller** — every
   `SensorReaderConfig`-based sensor's persistent config storage was silently, completely
   non-functional. Fixed: corrected both slices to `[1:-1]`.
2. `check_cfg_get_default()`'s self-check of a schema's `"special"` sentinel called
   `type_or_range_error(..., check_special=use_value)` with `use_value=False` in exactly the case
   being checked — forced the special value through the full min/max range check instead of its
   own bypass shortcut, judging real, already-in-use schema constants (e.g. `AmbPres`) as invalid.
   Masked by bug #1 (never actually reached). Confirmed with owner which side was wrong (the
   validation, not the schema — a special sentinel is deliberately meant to fall outside the normal
   range). Fixed: always pass `check_special=True` to this self-check.

**Typing crash fixed across all three files**: unconditional `from typing import ...`, including
real `TypeVar(...)` calls executed at class-body evaluation time in `base_classes.py`
(`Lockable.LockableType`, `SensorReader.MeasDataType`), would have crashed immediately on import
under real MicroPython. Fixed with `try/except ImportError: TYPE_CHECKING = False` +
`if TYPE_CHECKING:`, extended to module-level `TypeVar` defs and `config_manager.py`'s
`WriteValidity` type alias (a real module-level assignment, needs the guard too). Modernized
`from uasyncio import Lock` → `import asyncio`/`asyncio.Lock()`; `typing.Dict`/`List`/`Tuple` →
builtin generics.

**FRAM boundary**: `asy_fram_manager.py` isn't itself promoted, so `SensorReader`'s FRAM-backed path
and `print_log.py`'s FRAM writes weren't exercised for real at first. `[[tool.mypy.overrides]]` for
module `asy_fram_manager` (`ignore_missing_imports = true`) added to `pyproject.toml` for the
scoped-CI-only resolution gap. `print_log.py`'s own FRAM boundary was later mocked and tested
properly: `PrintLogHistoryStore` only ever calls `AsyFramManager.get_chunk()` and, on the chunk,
`get_buffer()`/`write_into()`/`read_into()` — not the real allocator/CRC/dual-copy machinery.
`tests/_fram_mock.py` fakes just that surface; `print_log.py`'s `AsyFramManager` `TYPE_CHECKING`
import was replaced with two local `Protocol`s (`_FramManager`/`_FramChunk`), so it no longer needs
the mypy override at all (only `base_classes.py` still does). A genuine parameter-contravariance
conflict surfaced running the *unscoped* mypy pass: the real `AsyFramChunk.write_into()`/
`read_into()` narrow their `buf` parameter to a concrete buffer subtype, incompatible with a
Protocol declaring a shared precise type in parameter position — fixed by typing the Protocol's
`buf` as `Any` (this file never inspects it). `MockFramBacking` deliberately simulates data
surviving a reboot (tracks written offsets; a test constructs a second `MockAsyFramManager` around
the same backing, replaying the same `get_chunk()` sequence, to prove persistence).

**Resolved in a follow-up session**: `asy_fram_manager.py` has since cleared its own `src/`
promotion (see "`asy_fram_manager.py` → `src/`" below) - `tests/_fram_mock.py` is removed, and
`tests/test_print_log.py`/`tests/test_base_classes.py` now drive `PrintLogHistoryStore`/
`SensorReader`'s FRAM-backed paths against the real `AsyFramManager` running on
`tests/_fram_chip_fake.py`'s simulated chip, including real chip-level fault injection. The
`_FramManager`/`_FramChunk` `Protocol`s stayed (not reverted to a concrete import) - deliberate,
not just a promotion-ordering artifact: they still avoid a real runtime import cycle
(`asy_fram_manager.py` imports `PrintLogHistory` from `print_log.py`) and keep this file decoupled
from the concrete chunk classes' shapes. The now-dead `pyproject.toml` mypy override for module
`asy_fram_manager` was removed along with it.

**`print_log.py` bugs found and fixed** (across several dedicated review passes):
- `PrintLogHistoryStore._write()`/`_read()`'s `try:` block started too late — `get_buffer()`/
  `get_data_buf()` (and, in `_read()`, `read_into()`) were called *before* the `try:` began, so an
  unaudited-`asy_fram_manager.py` raise would break the "never raises" contract. Also
  `__init__`'s `fram.get_chunk(...)` call was completely unguarded. Fixed: widened both `try`
  blocks to cover their entire bodies, added `try/except Exception` around `__init__`'s
  `get_chunk()` (degrades to `self.fram = None`).
- `_store_err()`/`reset()`'s "not initialized" guard's `return` was conditioned on `self.level`,
  not just `self.initialized` — with logging **off** (production default), calling `err_s()`/
  `wrn_s()`/`reset()` before `setup()` loaded persisted state silently overwrote real
  FRAM-persisted history with a fresh default, exactly backwards from the guard's intent, masked by
  logging being off. Confirmed reachable: `SensorReader.__init__` never calls `self.pr.setup()`
  itself (sync `__init__`); it's each driver's own responsibility, easy to forget. Fixed: split the
  `return` out from the `print`, so the guard always returns when uninitialized.
- `PrintLogHistory.__init__` didn't clamp `history_length` — a negative value reaches
  `deque([_NO_ERR] * history_length, history_length)`, and a negative `maxlen` raises `ValueError`
  on real MicroPython. Fixed: clamp to `≥0`.
- A bare `struct` format string (no byte-order prefix) does **not** default to `"<"` on
  MicroPython — confirmed against v1.28.0 docs and the real interpreter: defaults to `"@"` (native
  byte order **and** native alignment/padding; `"="` isn't supported at all, unlike CPython). Never
  an actual shipped bug here (this file's field order happened to produce identical bytes either
  way), but fixed to explicit `"<H"`/`"B"*n` since reordering fields later would have silently
  introduced real padding under the old bare format.
- Segfault-class bug (see "Dangerous allocation shapes" below): `history_length` clamped to
  `[0, 0xFFFF]` before allocation, not just caught reactively.

Confirmed non-issue: unlike `ConfigManager.config_lock`, `PrintLogHistoryStore`'s in-memory state
(`err_count`, `history`) has no `asyncio.Lock` — checked and confirmed safe, since every mutation
(`err_s()`/`wrn_s()`/`reset()`/`get_log()`) completes synchronously before its one `await` point, so
concurrent calls can't interleave mid-mutation; a lock here would be inert complexity.

Simplifications: `_FramBuffer` Protocol was a redundant duplicate of `base_classes.LockableBuffer`'s
own two methods — folded away. `PrintLogHistory.hl` was dead state (nothing read it) — removed.
`"B" * len(self.history)` was rebuilt on every `_write()`/`_read()` call despite never changing
after construction — cached once as `self._history_fmt`. Eight identical diagnostic-print gates
folded into one `_diag()` helper. Renamed `PrintLogHistStore` → `PrintLogHistoryStore` project-wide
(the one abbreviation in an otherwise fully-spelled-out file). `pyproject.toml`'s own mypy-override
comment initially missed this rename (caught and fixed during a later documentation audit); the old
name still appeared in `improved-quality/system_service.py` until that file's own `src/` promotion
picked up the rename too (see "`system_service.py` → `src/`" below) - `base_classes_old.py` still
has it, out of routine-editing scope until its own refactor work reaches it.

`tests/_fram_mock.py` supports fault injection for every FRAM failure mode `print_log.py` guards
against (`raise_on_get_chunk`, `out_of_memory`, per-chunk `raise_on_get_buffer`/`broken_buffer`/
`raise_on_write`/`write_returns_false`/`raise_on_read`/`read_returns_false`). Confirmed a real
MicroPython/CPython difference along the way: resizing a `bytearray` via slice assignment while a
`memoryview` is exported over it does **not** raise `BufferError` on MicroPython's Unix port the
way it does on CPython — silently resizes, leaving the `memoryview` referencing stale state (not
load-bearing today, worth remembering).

**`config_manager.py` bugs found and fixed** (beyond the two above):
- `get_bool_values()`'s conversion-failure detection was silently broken — `bool(v)` never raises
  for any input (unlike `int()`/`float()`/`str()`), so a corrupted/wrong-typed on-disk bool value
  silently coerced instead of signaling invalid data. Fixed: explicit `isinstance(v, bool)` guard.
- `ConfigManager.__init__`: a non-string `filename` makes `os.stat()`/`open()` raise `TypeError`,
  not `OSError` — uncaught by the existing catches. `get_dict`: non-iterable `keys` raises
  `TypeError` from `for key in keys`. `write_config`: non-dict `data` raises `AttributeError` from
  `data.items()`. All three fixed by widening the relevant `except` tuples. (Two of these three are
  dead weight today per the checklist's own "don't defend against what mypy already rules out"
  rule — every real call site is statically typed already — but `write_config`'s `data` genuinely
  will face less-controlled input once a Microdot REST layer is wired up; owner decision: **keep
  all three defenses as-is**, revisit once that layer exists.)
- `write_config()`'s special-only-key branch never called `type_or_range_error` on the submitted
  value at all — a caller writing a nonsensical special-only value got `"Valid"` unconditionally.
  Confirmed with owner: "the sentinel value shall always be valid if it matches its definition,
  independent from any range/value checks" — i.e. the existing `check_special` bypass is exactly
  intended, it just needs to run for special-only keys too. Fixed: moved the
  `type_or_range_error()` call before the `not use_value` branch.
- `ConfigManager.__init__`/`write_config()`'s `json.load()`/`json.dump()` calls could in principle
  raise `MemoryError` uncaught (4 call sites total) — added to the relevant `except` tuples.
  Left honestly uncovered by a dedicated test (would need a multi-gigabyte file or stdlib
  monkeypatching, neither in this test file's style).

Confirmed non-issues (empirically checked, not assumed): `make_dict()`'s `repr()`-string parsing is
the *only* option (namedtuples have neither `_fields` nor `_asdict()` on MicroPython, both raise
`AttributeError`, unlike CPython) — but has two documented quirks: a nested-tuple field's `repr()`
containing `"("` silently drops every field after it, and a list-valued field's `repr()` containing
a comma produces a garbage extra key whose `getattr` failure drops the *whole* dict to all-`None`
(not just the corrupted field). Local variable annotations referencing `TYPE_CHECKING`-only names
are safe unquoted (MicroPython doesn't evaluate local variable annotations, unlike CPython's
module/class-level ones). `type_or_range_error`'s `bool` branch has no special-sentinel handling —
architecturally sound (`bool` has no "outside range" concept). `str` length bounds count Unicode
codepoints, not UTF-8 bytes (`len("café") == 4`). A JSON value omitted before a comma/brace (e.g.
`{"Count": , "Offset": 1.5}`) doesn't raise on this MicroPython's `json.load()` — it desyncs the
parser and silently returns a mangled dict; confirmed this degrades safely through the normal
per-key validate-then-default-fallback path (documented as a quirk, not fixed). An unpaired UTF-16
surrogate round-trips through `json.dump()`/`json.load()` without raising (MicroPython doesn't do
CPython's strict UTF-8 validation on write). Invalid UTF-8 in a config file raises `UnicodeError`,
already safely caught since `UnicodeError` **is** a `ValueError` subclass on this build. A
filename containing an embedded NUL byte gets silently truncated by MicroPython's `open()` rather
than raising — academically a behavior difference, not reachable (`config_file` is always built
from string literals). `json.dumps(float("nan"))` succeeds (writes the non-standard token `nan`),
but `json.loads("nan")` raises `ValueError` — a real read/write asymmetry, but unreachable via any
live write path since `type_or_range_error()` already rejects NaN/Inf before a value ever reaches
`_cache`/`json.dump()`.

**Schema representation replaced**: pipe-delimited-JSON-string `const()` →
`const()`-wrapped-tuple `const()`. The old `_VAL_SI = const('|"SampleInterv": {...}|')` encoding
(hand-rolled `str_cfg`/`cfg_from_str` string parsing) existed only to get `const()`'s
RAM-zero-cost property back when `const()` couldn't fold anything but ints. Checked current docs:
MicroPython 1.26.0 added float/tuple folding to `const()`; v1.28.0 docs confirm constant tuples are
compiler-optimized to not be recreated at runtime, and an underscore-prefixed `const()` name isn't
available as a global and takes zero memory during execution. Verified empirically (real
interpreter, before changing anything, later re-verified across mixed int/float/str/bool
schemas): a `const()` tuple behaves identically to the old `const()` string for "at rest" cost —
stable object identity, ~0 heap delta. The only nonzero cost (concatenating multiple named consts
at a call site) scales with total field count for both representations equally — **zero additional
memory cost** from the switch. New shape: each field a plain positional 6-tuple
`(name, type, def, min, max, special)`, concatenated with `+` (tuple, not string).
`str_cfg` → `schema_names`, `cfg_from_str` → `schema_dict`, both now plain comprehensions with no
string parsing. `improved-quality/`'s `asy_bmp3xx_driver.py`/`asy_scd30_driver.py`/
`asy_sgp40_driver.py` `_VAL_*` definitions converted too (one-time scope exception, owner-granted;
call sites needed no changes — drop-in API). Two files matched the initial grep but were confirmed
*not* real usages, left untouched: `base_classes_old.py` has its own independent, zero-importer
copy of this scheme (dead code); `sensortask-wozi.py` imports `ConfigManager` from the current
production `python/CommonDrivers/async_manager.py`, an entirely separate implementation.

`get_int_values`/`get_float_values`/`get_str_values` collapsed into one generic
`_get_converted_values(keys, converter)` helper (`get_bool_values` stays separate — `bool(v)` never
raises, so it can't reuse the same raise-to-signal-failure mechanism). Pure DRY, confirmed
zero behavior change including existing permissive-coercion quirks (`int(5.7) == 5`,
`int(True) == 1`, neither raises).

**Blocking-I/O redesign, decided directly by owner**: `get_dict`/`_get_values`/`write_config`'s
synchronous file I/O (`open()`/`json.load()`/`json.dump()`) blocks the event loop with no yield
point inside `async def` methods — the same class of concern as `async_connect.py`'s
`get_long_block_lock()` pattern. Confirmed not purely a one-time boot cost:
`asy_bmp3xx_driver.py`'s `read_loop()` calls a config getter every `SampleInterv` cycle (default
2s), not just at startup. Never actually observed to cause a problem in practice, but owner asked
for a general redesign regardless: **read the config file once at `__init__`, cache it, serve all
reads from cache** (one change to the shared `ConfigManager` class). Implemented:
`__init__` populates `self._cache`; `get_dict`/`_get_values`/typed getters read it directly (no
file I/O, no lock needed — no `await` in their bodies, so no concurrent-mutation race is possible);
`write_config` builds changes into a working copy and only assigns `self._cache = new_cache` after
the file write actually succeeds (confirmed: a genuine write failure leaves `_cache` unchanged),
still holds `config_lock` for the real file I/O. Memory cost verified empirically: ~256 bytes for
an 8-field schema (the largest real driver), negligible against 264KB SRAM. **Deliberate
consequence**: reads no longer detect the config file being deleted/corrupted out-of-band after a
valid `__init__` — `_cache` is now the sole source of truth, and a later `write_config` silently
*repairs* an externally-corrupted file from `_cache` rather than detecting/failing on it (reverse
of the pre-cache behavior). Accepted given this device is the file's only writer and manual writes
are rare. **Still open**: `write_config`'s own file write itself was never re-assessed for whether
a real RP2040 littlefs write needs `get_long_block_lock()` coordination — a hardware-timing
question this dev environment can't verify (see Open Questions #13).

`os.stat(...)[0] & 0x4000` directory check confirmed against MicroPython v1.28.0 source
(`extmod/vfs.h`): `0x4000` is `MP_S_IFDIR`, MicroPython's own port-standardized stat constant
(applied uniformly across VFS backends including littlefs), not a guessed POSIX convention.

**Real bugs found in `base_classes.py`**:
- `LockableBuffer.__init__` only guarded `data_end > size` — a negative `size`, `data_start`, or
  `data_length` wasn't checked. `bytearray(-1)` raises `MemoryError` on MicroPython (not
  `ValueError` like CPython — negative wraps to a huge unsigned allocation). A negative
  `data_start`/`data_length` that individually goes negative without tripping `data_end > size`
  silently returned a wrong-offset, wrong-length slice via Python's negative-index wraparound. Real
  call sites only ever pass non-negative literals, but the class is meant to be a safe generic
  primitive. Fixed: guard all three the same way (→ `self.buf = None`). Later widened further: a
  valid, non-negative but astronomically large `size` (e.g. `2**62`/`2**63`) can still raise
  `MemoryError`/`OverflowError` — a *real* operational risk since `asy_fram_manager.py`'s chunk
  buffer classes allocate a fresh `LockableBuffer` on every FRAM read/write over an indefinite
  uptime (heap fragmentation making a normally-small allocation fail is realistic long-run).
  Wrapped in `try/except (MemoryError, OverflowError)`.
- `SensorReader._get_dict_cfg`: `await self._get_mgr_cfg(cfg)` sat outside its own `try/except` —
  `_get_mgr_cfg` is documented as an overridable extension point that "could legitimately
  misbehave," same as the `callback` parameter one block below (which *does* wrap its call). Fixed:
  moved inside the same `try`.
- `_get_dict_cfg`'s `callback` merge path warned when the callback returned unrequested keys, but
  the `_get_mgr_cfg` merge path silently merged extras with no warning — a latent asymmetry (not
  currently observable; `SensorReaderConfig._get_mgr_cfg`'s one real override can't trigger it
  today). Fixed: added the same warning, with its own `wrnno=2` (distinguishable from the
  callback path's `wrnno=1`).
- `LockedCounter.__init__` didn't apply the same `[0, max_val]` clamp `set_value` uses — an
  out-of-range `init_value` (or negative `max_val`) sat unclamped. Fixed: clamp in `__init__` too,
  and clamp `max_val` itself to `≥0`.
- `SensorReader.reset_error_counter()` only reset `self.pr`'s persisted history, not
  `self._err_cnt_internal` (the separate consecutive-failure streak). Confirmed preserved
  pre-refactor behavior via diff (not introduced by this refactor) — but "reset the error counter"
  reading as resetting only one of two counters was judged confusing enough to fix once flagged.
  Now resets both.
- `_get_mgr_cfg`/`_get_dict_cfg` typed config values as `int | float | str | None`, omitting
  `bool` — mypy never caught it because `bool` is a subtype of `int`, but `config_manager.py`'s
  `get_dict()` (which `_get_mgr_cfg` returns directly) is correctly typed with `bool` included, and
  a real bool-schema field (`asy_scd30_driver.py`'s `SelfCal`) genuinely flows through this path.
  Fixed all four occurrences to match.
- A stale doc cross-reference: `print_log.py`'s `_HDR_FMT` comment pointed at a module-docstring
  paragraph removed by an earlier docstring trim. Re-pointed to this file.
- A stale comment: `config_manager.py`'s `write_config()` except clause still said "malformed
  json" as a catch reason, left over from before the caching redesign removed the `json.load()`
  call this function used to make on every write. Fixed to describe what's actually live
  (`AttributeError`, `MemoryError`, defensive `ValueError`).
- `base_classes.py` never stated (module docstring) that `self.pr.setup()` must be called by the
  driver itself (`SensorReader.__init__` is sync, can't call it) — already correctly implemented
  and tested, just undocumented at the module level. Added two lines.

**Harmonization**: `LockedCounter`/`LockedFlag`/`LockedValue` unified to a common
`get_value`/`set_value` shape (previously `LockedCounter` alone used `get_counter`/`set_counter`),
internal fields unified to `self.value`/`self.value_lock`. True inheritance-based dedup considered
and rejected — MicroPython has no `typing.Generic` at runtime, and the three classes' value
domains genuinely differ (confirmed: broadening `LockedValue`'s type introduces a real new mypy
error at its one caller, `asy_bmp3xx_driver.py`'s `trigger_period`). `LockedCounter`'s "never
happened" sentinel changed from magic `-1` to `None`, restoring correct `[0, max_val]` clamping —
the old asymmetric clamp (upper bound only) was intentional, relied on by
`async_connect.py`'s `last_ntp_sync.set_counter(-1)`. Every real consumer of the old `-1` idiom
migrated (owner-authorized touching these `improved-quality/` files for this one change):
`async_connect.py`'s `wifi_uptime`/`last_ntp_sync`/`ntp_synced`, `neopixel_signal.py`'s
`override_secs`, `sensortask-wozi.py`'s `task_error_counter`. **Found, deliberately not touched**:
`sensortask-wozi.py`'s `last_task_err = LockedValue(-1)` is the same idiom one level over —
converting would require broadening `LockedValue`'s type (breaks the `trigger_period` comparison
above). Explicitly deferred to the future `sensortask-*.py` functional refactor, confirmed by
owner. `LockedCounter.increment`/`decrement`'s near-duplicate blocks collapsed into a shared
private `_step(self, delta: int) -> int`.

### Dangerous allocation shapes (segfault-class bug, swept project-wide)

Confirmed against the real interpreter: `[x] * n` (list repeat — what `deque([x]*n, n)` does
internally) has **three** distinct outcomes by size, not the two `bytearray(n)` has: up to ~2**61
raises clean `MemoryError`; at/above 2**63 raises clean `OverflowError`; **in between (~2**61–2**63)
segfaults the entire interpreter process** — no `try/except` can catch this (reproduced directly,
`[0] * (2**62)` → SIGSEGV). Likely cause: list-repeat's internal `n * sizeof(pointer)` byte-count
multiplication itself overflows before being bounds-checked; `bytearray` (element size 1) has no
such intermediate multiplication, hence no gap. Fixed: `PrintLogHistory.__init__` clamps
`history_length` to `[0, 0xFFFF]` *before* attempting the allocation (proactive, not reactive —
`except MemoryError` kept as defense-in-depth below the clamp, `except OverflowError` not needed
since the clamp makes that branch unreachable). `LockableBuffer.__init__`'s existing `MemoryError`
guard widened to `(MemoryError, OverflowError)`. Swept rest of `src/` — nothing else live
(`crc_checks.py`'s `bytearray(self.num_bytes)` only ever gets hardcoded 0/1/2/4;
`asy_i2c_driver.py`/`asy_spi_driver.py` do no Python-level buffer allocation from a param at all).
`src/asy_fram_manager.py`'s `_clear_chunk` uses `bytearray(n)` directly (`_STATUS_UNINIT == 0x00`,
so identical content to the list-repeat form, without the segfault risk). `base_classes_old.py`
still carries the pre-fix list-repeat shape — dead code, out of scope (unused file).

### `asy_fram_driver.py` → `src/`

Driver for the FRAM chip (Fujitsu MB85RS64V, Adafruit's 8KB SPI FRAM breakout), sitting under
`asy_fram_manager.py` (below). Verified against the real datasheet (DS501-00015,
`datasheets/fram/`) and cross-checked against Adafruit's own `Adafruit_FRAM_SPI` reference driver.

**Current behavior/invariants:**
- `setup()`'s RDID check validates three independent fields against real hardware: manufacturer ID
  (`0x04`), continuation code (`0x7F`), and product ID (`0x0302`, correct byte order) — any
  mismatch raises `OSError`. Opcodes (`WREN`/`WRDI`/`RDSR`/`WRSR`/`READ`/`WRITE`/`RDID`), SPI mode
  0, MSB-first, and the 2-byte/3-byte address-width switch at 64KB all match Adafruit's reference
  driver; the 4-byte-address branch is dead code for this 8KB chip (`_setup_addr_buffer` trusts a
  caller-supplied `max_size` rather than validating/clamping it).
- `_write()` confirms the write-enable latch (`WEL`) actually set via `RDSR` after `WREN` before
  issuing `WRITE`, and re-verifies after `WRDI`, retrying once before only warning (not failing) on
  a stuck `WEL`. `set_write_protected()` does the same around `WRSR`, plus reads back the status
  register to confirm the write landed. `WEL` auto-clears after a completed `WRITE`/`WRSR`, not
  only after `WRDI` (per datasheet) — the explicit `WRDI`-verify-retry is defense-in-depth against
  that auto-clear itself glitching, not the only mechanism relied on.
- `WP` pin is active-low (`value=True` drives it low = protected). `set_write_protected()`
  deasserts `WP` before every `WRSR` and only restores the target level after readback-confirmed
  success, so a leftover-low `WP` from an earlier protect call can never self-lock a later unprotect
  call.
- `WPEN`/`BP0`/`BP1` are nonvolatile; `setup()` re-syncs `_wp` from a real `RDSR` rather than
  trusting the constructor's `wp=` (which is only a pre-`setup()` placeholder, always overwritten
  once `setup()` succeeds).
- `verify_present()` (a cheap re-probe reusing the RDID check, for a future health-check/retry
  policy) bounds its own lock-wait with `asyncio.wait_for(..., _VERIFY_PRESENT_LOCK_TIMEOUT_S)`
  (`const()`, 1.0s), degrading to `False` instead of hanging if `FRAM_SPI`'s outer `Lockable` lock
  is already held elsewhere.
- `get_values()`/`set_values()` accept a zero-length `buf` as a no-op — not rejected, since no real
  caller passes one and neither the datasheet nor real usage rules it out.
- Exception contract — exactly three deliberately-allowed raise paths, everything else returns
  `False`/`None`: `__init__`'s `ValueError` for a bad pin/port (fail loud once at boot); `setup()`'s
  `OSError` on failed device identification; `SPIDevice.__aenter__`'s "not set up" `RuntimeError`
  (a caller-ordering bug only — unreachable through this file's own methods, all of which check
  `uninitialized` first).

**Known gaps, kept for future use, not chased further (owner-confirmed):**
- `get_write_protected()`/`set_write_protected()`/`verify_present()` have zero callers in
  `asy_fram_manager.py` today. Whoever wires up FRAM's own bus-recovery/re-probe policy (see "Bus/
  sensor error-recovery robustness" above) must wrap them in the same `try/except Exception`
  discipline `asy_fram_manager.py` already applies to `setup()`/`get_values()`/`set_values()` — this
  driver deliberately doesn't catch its own inherited `RuntimeError` path itself.
- `get_size()` has zero callers anywhere (kept as public API — a plausible future capacity getter).
- Coverage (via `scripts/test.sh --coverage`): 90% (16/163 lines missed) — 14 are `const()`-folding
  tracer artifacts (see `tests/README.md`), 1 is `get_size()`'s zero-caller status above. The stuck-
  `WEL` warning path and the post-failure `WP`-pin restore in `set_write_protected()` are now
  covered.

46 tests (`tests/test_asy_fram_driver.py`).

### `asy_fram_manager.py` → `src/`

Central FRAM storage manager: a bump-pointer chunk allocator (`get_chunk()`/
`get_timestamped_chunk()`) on top of `asy_fram_driver.py`'s `FRAM_SPI`, giving each chunk dual-copy
redundancy, CRC-checked self-healing reads, and a status-byte busy/idle protocol that detects a
write torn by power loss. Every other FRAM-touching file (`print_log.py`'s `PrintLogHistoryStore`,
`base_classes.py`'s `SensorReader`) exercises this surface for real via
`tests/_fram_chip_fake.py`'s simulated chip - see `tests/README.md`.

**Current behavior/invariants:**
- Contract: never raises; every method returns `False`/`None` (or an all-`None`/`False` tuple for
  the timestamped variant).
- Chunk layout: `[Data 0][Status 0-1][Status 0-2][Data 1][Status 1-1][Status 1-2]`.
  `get_chunk()`/`get_timestamped_chunk()` are a bump allocator - a device's own lifetime call order
  fixes its on-chip layout, which must stay identical across firmware versions for existing stored
  data to keep decoding.
- Every chunk from one manager shares that manager's own `PrintLogHistory`, so `errno`/`wrnno`
  values must stay unique across the whole file, not just per class. Current registry: the four
  `check_idle=False` status-byte call sites (write-busy 10-11, write-idle 19-20, read-idle 39-40,
  clear-uninit 50-51) use only their 2 reachable numbers each; the one `check_idle=True` site
  (`_read_chunk`'s initial busy-set, err=30) keeps the full 7-number spread (30-36), since its two
  status bytes can genuinely disagree. `AsyFramChunk.write`'s oversized-data check is errno=84
  (distinct from the base class `clear()`'s errno=80); the externally-guarded paths are 85-88
  (`ntp_sync_callback`, and `time.mktime(time.gmtime())` - which raises `OverflowError` past rp2's
  ~2037 32-bit epoch limit, not hypothetical for a device meant to run unattended for years).
- Locking: `_op_lock` (one `asyncio.Lock` per chunk) serializes that chunk's own
  `write()`/`read()`/`clear()` end to end - two calls into the same chunk can never interleave.
  `fram`'s own lock (shared by every chunk on one manager) only serializes one block operation at a
  time, released between a chunk's own block 0 and block 1 - so different chunks' block operations
  may still interleave in that gap, though a single chunk's own operations cannot.
- Deliberate, owner-confirmed design points: "both blocks valid but different data" is a hard
  failure, not a guess - there's no generation counter to say which block is newer, so a write torn
  between blocks must be reported as corruption. Sharing one `CRC` instance per chunk is safe
  because `fram`'s lock already guarantees only one chunk's `_read_chunk`/`_write_chunk`/
  `_clear_chunk` body runs at a time. This also means the cross-block byte comparison is a second,
  CRC-independent corruption detector: even with `crc=CRC_Pass()`, a single corrupted copy still
  hits this same hard-failure path rather than reading back silently wrong - confirmed directly by
  corrupting a raw on-chip byte with no CRC in play at all.
- `AsyFramTimestampedChunk.write()`/`write_into()` return `(ntp_synced, utc, success)` - `success`
  is the third element, not first, unlike every other bool-returning method in this file. This is
  the real, in-use shape (`asy_sgp40_driver.py` already unpacks it this way) - not to be silently
  reordered.
- `AsyFramManager.__init__`'s `FRAM_SPI(...)` construction is not itself caught - consistent with
  `asy_fram_driver.py`'s fail-loud-once-at-boot exception contract for a misconfigured pin.
- SGP40 FRAM backup "0 = disabled" semantics: see Functional Clarifications above.
- `set_pause()`/`get_pause()`/`override_pause`: owner-confirmed intent is "finish all ongoing ops,
  reject new ones" - correctly what the code does, since the pause check sits *after* `_op_lock`
  acquisition, so nothing already mid-flight is interrupted. Real callers are `system_service.py`'s
  own `reboot_system()`/`reboot_bootloader()` (pause right before a deliberate reset, then a 4s
  `_RESET_DELAY` before the reset actually fires - ample margin over a real operation's
  low-single-digit-ms cost) and a REST `systemCmd` `"mempause"` command (operator-triggered pause
  for up to `_MAX_STORAGE_PAUSE`=3600s via a hardware `Timer` auto-unpause, for safe physical access
  to the chip). `system_service.py` is now itself promoted to `src/` (see "`system_service.py` →
  `src/`" below); the still-open task-supervisor/system-service wiring this note used to flag is
  which `sensortask-*.py` device files actually call `start_and_check_tasks()`/`get_task_starters()`
  end-to-end, not whether `asy_fram_manager.py`'s own pause plumbing works.
- The busy/idle protocol brackets *reads* too (not just writes), owner-confirmed deliberate:
  MB85RS64V reads are destructively read internally (confirmed in the datasheet's own endurance
  footnote), so a power loss mid-read is as real a risk as mid-write; board-level bulk capacitance
  is sized against the datasheet's power-supply falling-time (`tf`) spec as the primary mitigation,
  with this software protocol as the second layer.
- `get_chunk()`/`get_timestamped_chunk()`'s "out of memory" failure logs via `self.pr.err()`
  (console-only), deliberately not the persisting `err_s()` - owner-confirmed: an out-of-FRAM error
  can't sensibly be logged into that very FRAM, so this one path stays console-only by design, not
  an oversight.
- `get_chunk()`/`get_timestamped_chunk()` reject `size == 0` unconditionally, before any CRC or
  capacity logic runs - a chunk storing nothing is never a sensible request, regardless of which
  `crc` would've been used (owner-confirmed: reject generally at the top, not as a CRC-specific or
  timestamp-specific special case). Replaces the previous behavior, where a `size=0` chunk with
  `crc=CRC_Pass()` allocated successfully but then read back a spurious CRC error on every
  subsequent read (the streaming loop never ran, so the CRC engine never received a `run_inc()`
  call) - that quirk no longer exists; the request is refused outright instead.

**Known gaps, kept for future use, not chased further (owner-confirmed):**
- `get_crc_buf()` (both buffer classes) and `get_size()` (both chunk classes) have zero callers
  anywhere in `src/`, `tests/`, or `improved-quality/` - the same zero-real-callers category
  `asy_fram_driver.py` tracks for its own write-protect methods, just one layer up.
  `_AsyBaseFramChunk.get_pause()` (the async coroutine, distinct from `AsyFramManager.get_pause()`,
  which is used) is likewise never called.
- `asy_fram_driver.py`'s `verify_present()`/`get_write_protected()`/`set_write_protected()` still
  have zero callers from this manager - see that file's own "Known gaps" above.
- Coverage (via `scripts/test.sh --coverage`): 94% (27/463 lines missed) - every genuinely
  reachable branch is covered. What remains: 8 `const()`-folding tracer artifacts; the
  intentionally-unreachable `return False, 0` at the end of `_read_chunk` (mypy requires it; every
  real path above already returns); the zero-caller dead-code getters above; and, confirmed
  empirically against the real interpreter (not assumed), four more provably-unreachable
  defense-in-depth branches - `AsyFramTimestampedChunk.write_into()`'s `struct.pack_into` `except`
  (this build silently wraps out-of-range/negative ints for an unsigned format instead of raising,
  and `utc` is always a plain `int` per the type contract, so only a type violation mypy already
  rules out could ever trigger it) and `read_into()`'s `struct.unpack_from` `except` (the timestamp
  slice is always exactly 8 bytes when reached, and unpacking any 8 raw bytes as `"<Q"` can't fail),
  plus two `LockableBuffer`-backed `None`-guards downstream of an already-passed identical check
  earlier in the same call (`read()`'s and `write_into()`'s own copies of a check `read_into()`/
  `get_data_buf()` already made unreachable). None of the above is chased further (owner-confirmed:
  no trouble with less than 100% coverage as long as nothing left uncovered is a real gap).

89 tests (`tests/test_asy_fram_manager.py`) + 10 (`tests/test_fram_integration.py`, full-stack
integration down to the simulated raw SPI bus, including two `SensorReader`s sharing one manager,
the same manager backing two structurally different chunk types across a simulated reboot, and -
per `src/README.md` section 12's standing rule that module-level tests alone aren't enough for a
file that composes into a real chain - the torn-write/CRC/timestamp/pause failure modes above,
each reproven through the real `SensorReader` → `PrintLogHistoryStore` → chunk → `FRAM_SPI` chain
rather than by calling this file's own methods directly. Its 40-cycle stress test needs an explicit
`gc.collect()` per cycle - a Unix-port test-binary heap-timing artifact under a tight allocate-heavy
loop, not a leak in this file - don't remove it as apparent cargo-culting).

### `system_service.py` → `src/`

Generic system-housekeeping service shared by every `sensortask-*.py` device file (uptime, boot
signature, reboot/reboot-to-bootloader, storage pause, the staggered timer-startup sequence, and
the task supervisor loop). Its constructor had already moved, before this session, from the legacy
`(asy_ntp_callback, storage_pause=None, debug=False)` shape to `(asy_ntp_callback, watchdog=None,
fram=None, history_length=10, debug=None)`, matching `SensorReader`'s own `fram`/`history_length`/
`debug` shape - kept as-is (owner-confirmed), not reconciled backward.

Imports fixed to match already-promoted `src/`: `from base_classes import PrintLogHistory,
PrintLogHistStore, ...` → `from print_log import PrintLogHistory, PrintLogHistoryStore` (both moved
out of `base_classes.py` during its own promotion, and `PrintLogHistStore` was renamed
`PrintLogHistoryStore` then - see `print_log.py`'s own entry above) + `from base_classes import
LockedCounter, LockedValue` (those two did stay). `from uasyncio import ThreadSafeFlag` → `import
asyncio`/`asyncio.ThreadSafeFlag()` - confirmed directly against the built Unix-port interpreter
that `asyncio`/`uasyncio` are two import names for the *same* underlying classes (`ThreadSafeFlag`,
`Lock`, `get_event_loop` all identity-equal across both names, even though the two module objects
themselves are `is`-distinct) - safe to mix with any code elsewhere still importing from
`uasyncio`. `typing.Callable`/`Any`/`Coroutine`/`List`/`Dict` moved behind the established
`TYPE_CHECKING` guard, `List`/`Dict` → builtin `list`/`dict` generics; `AsyFramManager` import moved
`TYPE_CHECKING`-only too (never needed at runtime, only for `fram is None`).

Real gaps found and fixed (all four owner-confirmed before fixing, not guessed):

- `status_counter()`'s NTP-synced branch called `time.mktime(time.gmtime())` completely unguarded -
  `asy_fram_manager.py`'s own promotion already documented that this raises `OverflowError` past
  rp2's ~2037 32-bit epoch range. Extracted into a new `_ntp_boot_signature()` helper wrapping both
  the NTP callback and the `mktime()` call; on either failure, falls back to the same
  random-signature-after-`_NTP_WAIT_TIME` path as "never synced" (owner-confirmed: treat a failure
  like not-synced rather than retrying forever).
- The caller-supplied `ntp_is_synced()` callback and every driver-supplied task/timer starter
  (`get_task_starters()`/`get_timer_starters()`) were called with no exception guard at all - a
  single misbehaving driver could kill the whole status/supervisor task. Wrapped in `try`/`except
  Exception`, matching `base_classes.py`'s own `_get_dict_cfg` callback-guarding pattern
  (owner-confirmed to guard both the same way).
- `_timer_sequencer()` indexed `timers[counter]` with no bounds check - an empty timer-starter list
  (`start_timers([])`) raised `IndexError` on the very first call, a real "never raises" gap with no
  prior guard at all. Fixed: `start_timers()` now short-circuits straight to
  `self.timers_running.set()` for an empty list instead of ever calling `_timer_sequencer()`.
- `start_and_check_tasks()`'s per-task `starter()` call (both at startup and on every restart) was
  the same unguarded-caller-supplied-callable category as the second bullet above - extracted into
  `_start_task()`, guarded the same way, so a starter that can't even construct a `Task` degrades to
  a `None` slot (retried next cycle, same as a task that died) instead of crashing the supervisor.

`tests/machine.py` extended with fake `Timer`/`WDT`/`reset()`/`bootloader()` (previously only had
`Pin`/`I2C`/`SPI` for the two bus drivers - the Unix port's real `machine` module has none of these
either). The `Timer` fake never fires a callback on its own (no real elapsed time in a test); every
constructed instance self-registers into a class-level `Timer.all_timers` list so test code can
reach and manually `.trigger()` even an unstored, fire-and-forget instance - needed because
`_timer_sequencer()`'s own recursive chain timer is never kept as a reference, matching real
hardware's fire-and-forget IRQ pattern. `reset()`/`bootloader()` just record that they were called
instead of ending the test process, since the real calls never return at all.

Four MicroPython-specific gotchas hit while writing `tests/test_system_service.py`, each confirmed
directly against the built Unix-port interpreter rather than assumed:

- `micropython.const()` values are compiled away and unavailable as module attributes at runtime
  (see `tests/README.md`'s coverage-artifacts section for the same finding) - `_RESET_DELAY`
  (4s)/`_MAX_STORAGE_PAUSE` (3600s) are hardcoded in the tests rather than imported, the same
  treatment `test_asy_fram_manager.py` already gives real on-chip constants.
- MicroPython's real `time` module is a read-only builtin - `time.mktime = fake` raises
  `AttributeError` directly (confirmed), unlike a plain Python-level module's mutable namespace. The
  mktime-overflow test instead reassigns `system_service`'s own module-level `time` *name* to a fake
  object (a regular, mutable module global, unlike the builtin it normally points to).
- Bound-method identity isn't guaranteed - `obj.method is obj.method` can legitimately be `False`
  even for the same underlying method (each attribute access can mint a fresh bound-method object).
  The storage-pause-wiring test asserts by calling `svc.storage_pause` and checking the FRAM
  manager's own resulting pause state, not by comparing it `is manager.set_pause`.
- Cancelling a task while it's suspended inside `asyncio.sleep(N)` resolves immediately regardless
  of `N` (confirmed directly, 0ms measured) - most `start_and_check_tasks()` tests just cancel
  rather than waiting out real `_TASK_CHECK_TIME`=2s cycles. The one test that must let the
  supervisor run to completion (crossing `_TASK_FAIL_MAX` to actually trigger a reboot) instead
  monkeypatches `asyncio.sleep` itself for its duration, since both relevant consts are
  `micropython.const()`-folded and can't be shortened directly.

`improved-quality/sensortask-wozi.py`'s own `SystemService(...)` call site was still passing the
legacy `storage_pause=`/`debug=` keywords - already broken against this file's already-updated
constructor before this session started, unrelated to anything changed here. Patched (owner-
confirmed) to `SystemService(conn.ntp_issynced, watchdog=watchdog, fram=fram, debug=debug)`. Left
alone (out of scope, pre-existing, separate issues): that file's hand-rolled task-supervisor loop in
`main()` still never calls the real `start_and_check_tasks()`/`get_task_starters()` at all, and its
own `sysfunct.start_timers(timer_starters, 1000)` call passes a second positional argument
`start_timers()` has never accepted.

42 tests (`tests/test_system_service.py`): `__init__` (in-memory vs. FRAM-backed logging,
debug/history_length/watchdog forwarding), uptime/boot-signature (including all four
`_ntp_boot_signature()` branches: synced-success, callback-exception, mktime-overflow, never-synced,
plus the full `status_counter()` loop driven via repeated `ThreadSafeFlag.set()` + `sleep(0)`
pumping instead of real elapsed time), the timer-startup stagger sequence (empty/single/multi-timer,
and a starter-exception mid-sequence), reboot/reboot-to-bootloader/storage-pause (including the
real FRAM-backed integration path via `AsyFramManager`), and the task supervisor loop (watchdog
feed, no-watchdog, a dead task restarting, a starter that can't even start, and the full
give-up-and-reboot path).

#### Second pass: `machine.Timer`/`machine.WDT` verified directly against real rp2 source, not assumed

A follow-up quality review (structure/simplification/completeness/error-handling questions, not just
the initial promotion checklist) surfaced that the first pass never actually verified whether
`machine.Timer`/`machine.WDT` calls can raise - it treated them as safe by assumption. Fetched
`ports/rp2/machine_timer.c` and `ports/rp2/machine_wdt.c` directly from the v1.28.0 tag (matching
`toolchain/versions.toml`'s pin) rather than trusting a summarized web search:

- Bare `Timer()` (no args) never allocates anything - `machine_timer_make_new()` only calls the
  init helper `if (n_args > 0 || n_kw > 0)` - confirmed safe, matches `__init__`'s three bare
  `Timer()` calls.
- `Timer.deinit()` is safe unconditionally, any prior state (checks `alarm_id != ALARM_ID_INVALID`
  before cancelling) - confirmed safe, matches the unconditional `deinit()` calls already in
  `reboot_system()`/`reboot_bootloader()`.
- **`Timer.init()` (and any full `Timer(period=..., callback=...)` construction) calls
  `alarm_pool_add_alarm_in_us()` and raises `OSError(MP_ENOMEM)` if the alarm pool is exhausted** -
  a real, confirmed raise path, not hypothetical. This was unguarded in three places:
  - `_timer_sequencer()`'s own chained `Timer(...)` call (schedules the next startup step) - since
    this runs inside a Timer IRQ callback, MicroPython's own `mp_irq_dispatch()` swallows an
    uncaught exception silently and never re-fires that timer, meaning `timers_running` would never
    get `.set()` and `start_timers()` would hang forever. Fixed: wrapped in `try`/`except OSError`,
    falls through to `self.timers_running.set()` on failure instead of leaving the caller hanging.
  - `pause_permanent_storage()`'s auto-unpause `.init()` call - if this raises, storage stays paused
    with no way to auto-resume. Fixed: catches `OSError` and immediately undoes the pause
    (`storage_pause(False)`) rather than leaving it stuck.
  - `reboot_system()`/`reboot_bootloader()`'s `.init()` call - if this raises, it propagates
    uncaught, including through `start_and_check_tasks()`'s own give-up-and-reboot path, meaning
    the system's last-resort failsafe could itself crash instead of rebooting. Fixed (owner-
    confirmed: reuse the *existing* stop-feeding-the-watchdog mechanism, not a new one): a new
    `self._force_watchdog_starve` flag, set on this failure, checked alongside the existing
    `task_errors <= _TASK_FAIL_MAX` condition in `start_and_check_tasks()`'s feed step - once set,
    the watchdog is never fed again regardless of task health, so it resets the device within its
    own timeout the same way exceeding `_TASK_FAIL_MAX` already does. One-way by design, matching
    the existing give-up path's own one-way `return`.
- `WDT.feed()` (`mp_machine_wdt_feed()`) is a bare `watchdog_update()` register write - confirmed
  it genuinely cannot raise, no guard needed.

Also from this pass: `reboot_system()`/`reboot_bootloader()` were byte-for-byte identical except for
one log string and the final callback - collapsed into a shared `_reboot(message, action)` helper.
`pause_permanent_storage()`'s duration clamp (`if <=0: 0, elif >MAX: MAX`) simplified to
`min(max(duration, 0), _MAX_STORAGE_PAUSE)`, matching the exact clamp idiom `base_classes.py`'s
`LockedCounter` already established elsewhere in this codebase; its duplicated `storage_timer.deinit()`
call (present in both the zero-duration and real-duration branches) hoisted above the branch.
`get_boot_signature()`'s bare-`int`-with-`-1`/`1`-sentinel contract (no separate "is this resolved
yet" boolean exposed) was flagged as a discussion point, not changed - it matches the pre-existing
legacy behavior exactly and is deliberately treated as an opaque "unique ID," not a live status field.

`tests/machine.py`'s `Timer` fake extended with `raise_on_arm` (a shared class attribute, toggled via
a `_RaiseOnArm` context manager in the test file) to simulate this exact `OSError(ENOMEM)` path -
modeled precisely on the real gate: a bare `Timer()` with no kwargs never calls `init()` internally
and so can never raise, matching `machine_timer_make_new()`'s own `n_args/n_kw` check; any kwargs
(or an explicit `.init()` call) routes through the same raising path. 7 new tests cover all three
fixed call sites plus the dedup/simplification; total now 49
(`grep -c '^def test_' tests/test_system_service.py`).

One MicroPython/mypy interaction hit while writing these: `assert svc._force_watchdog_starve is
False` followed later by `assert svc._force_watchdog_starve is True` across an intervening method
call that mutates it made mypy report the *next* statement as unreachable - a known mypy narrowing
limitation (attribute narrowing from an `is False`/`is True` identity assert isn't invalidated by an
arbitrary method call in between, so mypy computes the intersection of `Literal[False]` and
`Literal[True]` as `Never` and treats anything after as dead code, even though the call legitimately
mutates the real attribute at runtime). Confirmed directly with a minimal repro isolating just the
two asserts plus a mutating call in between. Fixed by dropping the redundant "before" assertion
(the "after" assertion is what the test actually needs) rather than fighting the narrower.

#### Third pass: boot signature's `-1`/`1` sentinel replaced with `None` (owner-confirmed design)

A further review flagged `get_boot_signature()`'s bare-`int`-with-`-1`/`1`-sentinel contract as a
discussion point (see the second-pass entry above). Owner clarified the actual design intent, which
this codebase-review process hadn't previously had recorded anywhere: **the field exists purely so
an outside observer can detect that *this* device rebooted**, by polling and watching for the value
to change once it's left its "not ready yet" state - not for cross-device correlation, and not as a
real timestamp (the NTP-vs-random ambiguity flagged in the second pass doesn't matter for this use).
The `-1` sentinel's job was specifically to let that observer distinguish "uninitialized" from
"valid, now watch for changes" - a deliberate, load-bearing design detail, not an oversight.

This ruled out the second pass's own first suggestion (seed a random value immediately at boot,
then possibly overwrite it with the NTP timestamp once resolved): owner correctly pointed out that
overwriting a provisional random value with a timestamp *is itself an observable change*, which
would look exactly like a spurious reboot to the observer. The existing resolve-once logic (NTP if
it arrives in time, else a random fallback after `_NTP_WAIT_TIME`, latched via `start_time_set` and
never revisited) was already correct for this purpose - only the sentinel's *representation*
needed to change, not the resolution logic itself.

Fix: `self.boot_signature` moved from `LockedValue(1)` to `LockedCounter(init_value=None,
max_val=0xFFFFFFFF)` - reusing the exact same class and `max_val` already used for `self.uptime`
rather than adding a new primitive, since `LockedCounter` already has the needed "`None` = not yet
resolved, otherwise clamped into range" behavior built in and tested (`increment()`/`decrement()`
now go unused for this field, which is harmless). `status_counter()`'s initial
`set_value(-1)` became `set_value(None)`; `get_boot_signature()` simplified from a cast-returning
`-> int` to `-> int | None`, dropping the now-unnecessary `int(res)` cast entirely. `None` needs no
special handling to "propagate through the JSON API" (owner's own requirement) - it's Python's/
JSON's native "no value" representation (`null`), unlike the old sentinel which shared the plain
`int` type with real signatures.

Before finalizing, the owner raised a sharper version of the same concern from a different angle:
could `random.getrandbits(32)`'s *seed itself* be predictable/repeating across reboots (a pattern
seen on some platforms/configs), defeating the fallback's own uniqueness? Verified directly against
real source rather than assumed: `ports/rp2/mpconfigport.h` sets `MICROPY_PY_RANDOM_SEED_INIT_FUNC
(get_rand_32())` and rp2's ROM level makes `MICROPY_MODULE_BUILTIN_INIT` true, so MicroPython's
`random` module auto-seeds from `get_rand_32()` on first import, every boot - it does not fall back
to `extmod/modrandom.c`'s fixed compile-time constants (`0xeda4baba`/`69`/`233`), which is the
actual failure mode being worried about, on a port that doesn't wire up that seed function. Pico
SDK's `pico_rand` (`get_rand_32()`'s real implementation) seeds its own 128-bit PRNG state primarily
from the Ring Oscillator's physical "random bit" (`PICO_RAND_ENTROPY_SRC_ROSC`, default-on on
RP2040 since it has no hardware TRNG - that's RP2350-only), mixed with a hash of leftover RAM
content and the microsecond timer - genuine physical entropy, not a deterministic function of
uptime-since-power-on alone. Confirmed as a real, sourced fact and cited directly in a code comment
at the call site, not left as an assumption. (Separately explained for the owner: *if* the seed
really were fixed, the failure mode isn't "low odds of a repeat" - a fixed seed with the same call
sequence produces the exact same first draw with 100% certainty, since there's no entropy at all in
that hypothetical; contrast the real, properly-seeded case, where the odds of two *consecutive*
32-bit draws coinciding are 1-in-2³² ≈ 1-in-4.29-billion - a simple pairwise check, not a
birthday-paradox calculation, since only consecutive values matter for this observer's purpose.)

New test: `test_status_counter_boot_signature_never_changes_again_once_resolved` - proves the
signature stays byte-for-byte identical across many further ticks post-resolution, the specific
property this whole design depends on (a change ⟺ a reboot, never a false positive from internal
resolution). The four existing `status_counter()` tests checking the sentinel value were updated
from `== -1`/`!= -1` to `is None`/`is not None`, plus their `scenario()` return-type annotations
from `tuple[bool, int]` to `tuple[bool, int | None]`. Suite now 50 tests / 95% coverage (unchanged -
the 9 remaining misses are still exactly the same documented tracer artifacts).

#### Fourth pass: uncaught-exception audit found one real gap, plus broader test-configuration coverage

A dedicated pass re-checked every call `system_service.py` makes into another module (or into
`machine`) for a possible uncaught exception, verifying each against the actual callee source
rather than assuming: `base_classes.py`'s `LockedCounter`/`asyncio.Lock`/`asyncio.ThreadSafeFlag`
construction, `print_log.py`'s `PrintLogHistory`/`PrintLogHistoryStore` (deque `MemoryError`
already guarded to a length-0 fallback, FRAM `get_chunk()` already wrapped), `asy_fram_manager.py`'s
`set_pause()` (trivial - a `pr.evt()` call plus a bool assignment, confirmed never raises, unlike
the arbitrary caller-supplied callbacks this file already treats defensively), and
`extmod/asyncio/core.py`'s real `get_event_loop()`/`create_task()` (checked directly from the
cached toolchain source at `~/pico-toolchain/micropython/extmod/asyncio/core.py` - `get_event_loop()`
just returns the `Loop` class, and `create_task()`'s only raise path, `TypeError` for a non-coroutine
argument, is unreachable here since `self.status_counter()` is always a real coroutine object).

That audit found exactly one real, previously-missed gap: **`start_uptime_timer()`'s
`self.uptime_timer.init(...)` was the one Timer-arming call site in this file (of four total) with
no `OSError` guard** - `_reboot()`'s `reset_timer.init()`, `pause_permanent_storage()`'s
`storage_timer.init()`, and `_timer_sequencer()`'s chained `Timer(...)` construction were all
already guarded against real rp2 alarm-pool exhaustion (`ports/rp2/machine_timer.c`'s `ENOMEM`
path, per the second pass above); this one wasn't. In practice it never actually crashed past this
file's boundary - its only real caller today, `_timer_sequencer()`, already wraps every starter
call in a broad `except Exception` - but the method violated its own module docstring's "every
method returns a well-defined value and never raises" contract if ever called directly, and was
inconsistent with the other three identical-failure-mode guards already in this exact file.

Fixing the guard raised a real design question with no obviously-correct answer from the code
alone: what should happen on failure? Flagged to the owner rather than guessed, since this file
already has two different, equally-established precedents for "a Timer can't be armed" -
`_reboot()`'s force a watchdog-starve reboot (rebooting was already the intent; there's no safe
substitute action), while `pause_permanent_storage()` just aborts the action and keeps running
normally (a fully safe substitute exists: "unpaused" is exactly "never paused"). Owner chose the
`pause_permanent_storage()`-style graceful degradation: log via the non-persisting `pr.err()` and
keep running - sensors, the REST API, and every other timer/task are unaffected; only
uptime/boot-signature stay unresolved for the rest of this boot, which is a real but non-critical
observability loss, not a reason to force a reboot for what is ultimately a resource hiccup in a
non-essential subsystem.

Separately, broadened test coverage per the same review pass beyond just the new guard: an
`_ntp_boot_signature()` fault-injection test for `time.gmtime()` itself raising (not just
`mktime()` - both calls share one `try`/`except`, and only `mktime()` raising had a test before);
constructor edge cases (`history_length=0`, `history_length=-5` clamping) and one test combining
all four constructor params (`fram`+`watchdog`+`history_length`+`debug`) together, since they'd
previously only ever been tested pairwise; a FRAM-backed variant of the existing
`get_error_counter()`/`reset_error_counter()` test (previously only exercised against the in-memory
`PrintLogHistory` path, never the `PrintLogHistoryStore` one `system_service.py` itself also wires
up); a `pause_permanent_storage()` re-entrancy test (a second call before the first pending
auto-unpause timer ever fires must fully replace it, not stack two competing callbacks); and a
`reboot_system()` cross-dependency test combining FRAM presence with the reset-timer `OSError`
fallback (storage must still get paused before the failing `init()` call, independent of whether
the fallback itself succeeds). Suite now 58 tests / 95% coverage (unchanged miss count - the new
`try`/`except` lines are fully exercised; the 9 remaining misses are still the same documented
tracer artifacts).

#### Fifth pass: a silently-dropped soft-Timer callback can hang `start_timers()` forever with zero exception

A follow-up review, prompted explicitly by the owner's "these are last-resort functions - no
exceptions, no hangs" framing, went past synchronous-exception auditing (the fourth pass above)
into whether a Timer *callback*, not just its *arming*, could fail silently. Verified directly
against the real MicroPython/pico-sdk C source (not assumed): every `Timer` this file constructs
omits `hard=True` (`ports/rp2/machine_timer.c`'s `machine_timer_init_helper()` defaults
`self->ishard` to `false`), so `alarm_callback()`'s firing dispatches through
`mp_irq_dispatch(..., ishard=false)` (`shared/runtime/mpirq.c`), which for a soft callback just
calls `mp_sched_schedule(handler, parent)` - **and never checks its boolean return value**.
`mp_sched_schedule()` itself (`py/scheduler.c`) returns `false` and silently drops the callback if
MicroPython's own scheduler queue is already full - a small, fixed-depth ring buffer
(`MICROPY_SCHEDULER_DEPTH = 8` on rp2, `ports/rp2/mpconfigport.h`) shared by *every* soft
timer/IRQ callback on the whole device, not something this file (or any single file) controls.
The underlying alarm still considers itself "handled" regardless (a periodic timer reschedules its
next tick either way, self-healing after one dropped tick; a one-shot timer does not - it simply
never fires again). No exception is raised anywhere in this chain; there is no way for Python code
to detect that a specific scheduled callback was dropped rather than merely not-yet-run.

Two call sites in this file rely on a scheduled callback eventually running with no other
safeguard: `reboot_system()`/`reboot_bootloader()`'s one-shot `reset_timer` (drop ⟹ the requested
reboot silently never happens, and `_force_watchdog_starve` is never set either, since
`reset_timer.init()` itself didn't raise - that would only fire from a *failure to arm*, a
different, already-guarded failure mode from a *failure to later deliver*), and
`_timer_sequencer()`'s chained one-shot timers via `start_timers()`'s
`await self.timers_running.wait()` (drop ⟹ sequencing stops permanently and this `wait()` - called
from `main()` during device boot, before any sensor/task loop starts - hangs forever: the device
never finishes booting, with nothing to log or catch).

Flagged both to the owner rather than silently fixing, since the right response wasn't obvious
from the code alone - and **both ended up rejected, for the same underlying reason.**

An initial fix was drafted and briefly landed for `start_timers()`: wrap
`await self.timers_running.wait()` in `asyncio.wait_for(..., 5)` (a new hardcoded-seconds
`const()`), logging and setting `_force_watchdog_starve = True` on `asyncio.TimeoutError`. On
reflection (owner's explicit call), this was reverted along with its test and is **not** part of
the current file:

- **In the productive system, arming a real `machine.WDT` is one of the very first things every
  device does - always, not situationally.** A hardcoded software timeout here would just be a
  second, independent clock racing the real watchdog with no coordination between the two - "no
  hardcoded 5s brittleness vs. the WDT timeout," in the owner's words. Whichever fires first is
  arbitrary and deployment-dependent (it depends on how much wall-clock time already elapsed before
  `start_timers()` was even reached, which this file has no visibility into); the software timeout
  doesn't reliably arrive *before* the hardware one the way `_RESET_DELAY < watchdog timeout` is
  deliberately guaranteed elsewhere in this same file.
- **The scenario the fix was defending against (no watchdog configured at all) is a test-only
  configuration, not a real one.** `SystemService(watchdog=None)` exists so unit tests can exercise
  the class without a real `WDT`; every real deployment always arms one. Adding a bounded-timeout/
  `_force_watchdog_starve` mechanism whose entire justification is "what if there's no watchdog"
  is solving for a case that doesn't occur in production - complexity with no real payoff, per the
  same "don't design for a hypothetical" principle this repo already applies elsewhere.
- This is the exact same shape of rejection already recorded above for
  `reboot_system()`/`reboot_bootloader()`'s analogous candidate fix ("brittle wrt. wdt timeout
  settings") - both call sites share one root cause (a silently-droppable soft-Timer callback,
  verified from source, not hypothetical) and both were judged not worth guarding against in
  software once a real watchdog is a given, rather than a maybe.

The underlying finding (silently-droppable soft-Timer callback delivery, confirmed against real
`py/scheduler.c`/`shared/runtime/mpirq.c`/`ports/rp2/machine_timer.c` source) stays recorded here
precisely so a future session that rediscovers the same mechanism doesn't re-add either mitigation
without first knowing both were already considered and declined, for a documented reason.
`start_timers()` itself is back to its pre-this-pass shape (plain, unbounded
`await self.timers_running.wait()`); the fourth pass's independent fixes (`start_uptime_timer()`'s
`OSError` guard and its associated tests) are unaffected and remain. Suite back to 58 tests / 95%
coverage.

#### Sixth pass: `start_timers([])` didn't actually match its own fourth-pass write-up

A full re-validation against every point of `src/README.md`'s checklist (not just a fresh
exception audit) surfaced a real discrepancy between this file's documented behavior and its
actual code: the fourth pass above claims `start_timers()` "short-circuits straight to
`self.timers_running.set()` ... instead of ever calling `_timer_sequencer()`" for an empty list -
but the code still called `_timer_sequencer(timers, counter=0)` unconditionally. For `timers=[]`,
`timers[0]` raised `IndexError`, which only happened to be swallowed by `_timer_sequencer()`'s own
`except Exception` (meant for a misbehaving starter callable), not by any explicit guard. Confirmed
empirically against the real interpreter that this produced a misleading console line - `debug=1`,
`start_timers([])` logged `"Timer starter 0 failed: list index out of range"` - even though
`timers_running` still ended up `set()` correctly (no hang, no crash; `pr.err()` is console-only,
so `err_count` was never actually affected). Harmless in practice (`start_timers()` is always
called with the full multi-driver-merged list, never actually empty in real use), but a fragile,
undocumented reliance on an accident of control flow rather than an explicit one - narrowing that
`except Exception` later (e.g. to stop also swallowing a starter's own `IndexError`) would have
silently reintroduced the exact hang `_timer_sequencer()`'s own guard was added to prevent.

Fixed with the two-line guard the fourth pass already described but never actually landed:

```python
async def start_timers(self, timers: "list[Callable[[], None]]") -> None:
    if not timers:  # nothing to sequence - avoid _timer_sequencer's timers[0] on an empty list
        self.timers_running.set()
        return
    self._timer_sequencer(timers, counter=0)
    await self.timers_running.wait()
```

`test_start_timers_empty_list_sets_timers_running_without_crashing` strengthened to assert
`_timer_sequencer` is never even called for an empty list (monkeypatched on the instance), not just
that nothing crashes - the old version would have passed identically before this fix, since the
IndexError-swallowing path also "worked."

Also from this pass: three inline comment blocks exceeded `src/README.md` section 11's "≤3 lines,
prefer fewer" bar (`__init__`'s `_force_watchdog_starve` comment, `start_uptime_timer()`'s and
`_reboot()`'s `except OSError` comments - 4-5 lines each). Trimmed to fit, pointing at this file's
existing second-/fourth-pass write-ups above for the full rationale rather than duplicating it
in-file - no information lost, just relocated to where it already lived.

Suite still 58 tests (the empty-list test was strengthened in place, not added to) / 95% coverage
(one more line covered by the new explicit guard; miss count unchanged - still the same documented
tracer artifacts).

A follow-up owner request went further than the ≤3-line cap already applied above: every remaining
multi-line comment in the file (including ones already at exactly 3 lines, technically compliant)
was tightened to at most 2, and the module docstring itself condensed from two 5-6-line paragraphs
to two 3-4-line ones - same "purpose, then the never-raises contract" shape, less prose. Zero
behavior change (comment/docstring text only); re-verified lint/typecheck/58-tests-58-passing/95%
coverage identical to before this trim.

### `asy_udp_socket.py` → `src/`

Async, non-blocking UDP wrapper around one `socket.socket` (cooperative `select.poll` loop, since
MicroPython's `asyncio` has no built-in UDP-readiness primitive). Two callers, both still WIP
`improved-quality/` (out of scope to edit): `async_connect.py`'s one-shot-per-attempt NTP client
and `captive_dns.py`'s long-lived `DNSServer`.

Real bugs found and fixed (all owner-confirmed before fixing):

- **The class could not actually send or receive anything.** `sendto()`/`write()`/`recvfrom()`
  each started with `if self.sock is None: return None` - but `self.sock` is only ever created
  inside `_connect()`, which is only ever called from `ready()`, which each of those three methods
  called *after* that guard. On a fresh object `self.sock` is always `None` at that point, so every
  call short-circuited before `ready()`/`_connect()` ever ran, permanently. This is the "real bug
  fix" the note above (wrongly) credited - the deployed `python/CommonDrivers/asy_udp_socket.py`
  calls `ready()` first with no such guard, and does work. Fixed by removing the premature checks;
  each method now calls `ready()` first and narrows `self.sock is not None` only right before the
  real socket call (satisfies mypy; provably always true there, since `ready()` returning `True`
  implies `_connect()` already set `self.sock`).
- `write_and_recvfrom(msg, buf, timeout_ms, tries)`'s `for _ in range(tries): ...; return ...`
  returned unconditionally after the first iteration - `tries` never actually retried, on either
  success or failure. Neither current caller passes `tries>1`, so this was latent, not an observed
  production symptom. Fixed to loop until a response arrives or `tries` is exhausted.
- `_connect()`'s retry budget (`conn_tries`) was a one-shot, whole-object-lifetime thing, not a
  per-call thing: the entire method (socket creation *and* the retry loop) was gated behind a
  single `if self.sock is None:`, so once `conn_tries` was exhausted, every future call permanently
  short-circuited to "not connected" - no retry, no self-heal. Only `captive_dns.py`'s `DNSServer`
  is actually exposed to this (one `AsyUDPSocket` built in `__init__`, reused for the device's
  entire uptime); `async_connect.py`'s NTP client dodges it by constructing a fresh object every
  sync attempt. Fixed: if `conn_tries` is exhausted, `_connect()` now calls `disconnect()` on
  itself, tearing the failed socket down so the *next* call gets a genuinely fresh attempt.
- `sendto()` was typed `-> None` while actually returning `self.sock.sendto()`'s real `int` byte
  count at runtime - a pure annotation bug (no caller uses the return value today). Retyped
  `-> int | None`, matching `write()`'s already-correct shape.

Also, matching every other `src/` file: `from typing import Literal, Tuple` (unconditional -
`typing` has no runtime presence on the Unix-port interpreter, confirmed) moved behind the
established `TYPE_CHECKING` guard, `Tuple` → builtin `tuple`; every `except Exception:` narrowed to
`except OSError:` (confirmed via current MicroPython docs that socket-layer failures are always
`OSError`, never `socket.error`/`socket.timeout`) - this file takes none of `asy_i2c_driver.py`'s
bus-driver carve-out, since a network fault is an expected, recoverable condition here, not a
hardware bug to surface upward.

10 tests (`tests/test_asy_udp_socket.py`), all against real loopback (`127.0.0.1`) UDP sockets
under the Unix-port interpreter rather than mocking `socket`/`select` (owner-directed, matching the
`asy_spi_driver.py`/`asy_i2c_driver.py` precedent that hand-written stand-ins weren't acceptable
where the point of the file is its interaction with a real module) - covers the fixed lazy-connect
path, `sendto()`'s corrected return type, `recvfrom()`'s timeout sentinel, the fixed retry loop
(a reply dropped once then delivered, and a genuinely-exhausted-tries case), `conn_tries` retrying
within one `_connect()` call and the cross-call self-heal after exhaustion, `disconnect()`
idempotency and object reuse after it, and that `asyncio` task cancellation during a pending
`recvfrom()` isn't swallowed (confirmed directly: MicroPython's `CancelledError` subclasses
`BaseException`, not `Exception`, so none of this file's `except OSError` blocks can catch it).

One MicroPython-Unix-port-specific gotcha hit while writing the tests, unrelated to any real
driver bug: the Unix port's "standard" build rejects a plain `(host, port)` tuple in
`bind()`/`connect()`/`sendto()` outright with `TypeError: object with buffer protocol required` -
a known, long-standing Unix-port-only limitation (`micropython/micropython#6924`, open since
v1.14, still present at v1.28.0), *not* present on the real rp2 target (confirmed against the
installed `RPI_PICO_W` stub: `bind()`/`connect()` are typed to accept `tuple[str, int]` directly,
matching both real callers' actual usage - `captive_dns.py`'s literal `("0.0.0.0", 53)` and
`async_connect.py`'s already-`getaddrinfo()`-resolved NTP address). Tests work around this by
resolving loopback addresses via `socket.getaddrinfo()` before constructing an `AsyUDPSocket`,
purely to satisfy the test binary - `asy_udp_socket.py` itself never calls `getaddrinfo()`, by
design (matching CLAUDE.md's long-blocking-operation rule: DNS resolution is the caller's job,
coordinated through `async_connect.py`'s `get_long_block_lock()`).

Baseline check (section 14): full-scope `scripts/lint.sh` 228→219 errors, `scripts/typecheck.sh`
130→129 errors in 10→9 files - both drops are exactly this file's own pre-existing findings; zero
new findings elsewhere.

#### Second pass: structure/completeness/error-handling questions, not just the initial checklist

A follow-up owner review (same "structure/simplification/completeness/error-handling" framing as
`system_service.py`'s own second pass above) surfaced four more real gaps, none caught by the first
promotion pass:

- **The class could still hang or waste a full timeout on a real, already-known connection
  failure.** `ready()` only checked `event & mask`, ignoring `select.POLLERR`/`POLLHUP` entirely.
  Confirmed empirically (not just reasoned about) against the built Unix-port binary: a connected
  UDP client socket with a pending ICMP port-unreachable reports `POLLOUT|POLLERR` - **never
  `POLLIN`** - even though `recvfrom()` immediately raises `ECONNREFUSED` if called. Since POSIX
  `poll()` always reports `POLLERR`/`POLLHUP` regardless of the registered mask, `ready()` now also
  treats them as "ready", letting the caller's real socket call run and surface (and correctly
  convert) the actual `OSError` through the exception handling that already existed - instead of
  waiting out the full `timeout_ms` for a failure the kernel already knew about. Harmless-in-practice
  for both current callers today (the NTP client has a finite timeout; `captive_dns.py`'s bound,
  never-`connect()`ed server socket isn't exposed to this specific ICMP-refused shape) but a real
  contract violation - any future `mode="client"` caller with `timeout_ms<=0` would have hung
  forever on an error the OS already reported.
- **`_connect()`'s own setup code had zero exception handling - violated this file's own "never
  raises" contract.** `socket.socket()`/`setsockopt()`/`select.poll()`/`poller.register()` all ran
  *before* the retry loop's `try`/`except OSError`. A failure there (e.g. `ENOMEM` under real
  resource exhaustion - not hypothetical for a device meant to run years unattended) would have
  propagated uncaught past this file, and left any partially-created socket unclosed (a real fd
  leak). Fixed: wrapped the whole one-time setup in its own `try`/`except OSError`, sharing the same
  self-heal (`disconnect()`) and backoff as a connect/bind failure - now pulled into a
  `_RETRY_BACKOFF_S = const(0.5)` module constant used by both, so a persistent setup failure can't
  busy-loop either.
- **`wait_time_ms` was silently treated as seconds, not milliseconds.** `ready()` called
  `asyncio.sleep(wait_time_ms)` - but `asyncio.sleep()` takes seconds; MicroPython's millisecond
  variant is the separate `asyncio.sleep_ms()` (confirmed against current docs). The `_ms` suffix
  promises milliseconds, right next to `timeout_ms` which correctly *is* milliseconds already.
  Masked today only because no caller ever overrides the `wait_time_ms=0` default (unit-agnostic at
  zero) - present unchanged in the original deployed code too. Fixed to call `asyncio.sleep_ms()`.
- **Missing `async with` support**, added (`__aenter__` returns `self`, `__aexit__` calls
  `disconnect()`, returns `False` - same shape as `base_classes.py`'s `Lockable.__aexit__`, though
  `AsyUDPSocket` doesn't inherit `Lockable` since it isn't lock-based). Purely additive, zero
  behavior change to existing paths - but it's the exact acquire/use/release-in-finally shape
  `async_connect.py`'s NTP client already hand-rolls via `try`/`finally`, matching the established
  `SPIDevice` convention for this pattern.

Considered and explicitly rejected: collapsing `sendto()`/`write()` (and their `ready()`+narrow
preamble) into a shared helper - `sendto()`/`write()` call genuinely different underlying
primitives (the rp2 stub is explicit: `sendto()` "should not be connected", `write()` requires a
connected socket), so a generic helper would need either a closure (a real allocation on
MicroPython) or would lose mypy's `self.sock is not None` narrowing at the call site. Also left
alone: `SO_REUSEADDR` is applied unconditionally including for `mode="client"` sockets that never
`bind()` (harmless but purposeless there); `timeout_ms=0` behaves identically to "wait forever"
rather than "check once" (pre-existing, unexercised, inherited unchanged); no structural guard
against calling `sendto()` on a client-mode object or `write()` on a server-mode one (both real
callers already use the API correctly; guarding against a misuse that doesn't happen would just add
complexity).

5 more tests (15 total): `wait_time_ms` actually completing in tens of milliseconds rather than
multiple real seconds; `_connect()`'s setup phase not raising when `socket.socket()` itself fails
(monkeypatching `asy_udp_socket`'s own module-level `socket` name, same read-only-builtin technique
`test_system_service.py`'s time-module fakes already established) and self-healing once the fault
clears; the POLLERR fix, driven through a real ICMP-refused loopback connection exactly like the
manual repro that found the bug, asserting `recvfrom()` returns in under 1s instead of waiting out a
5s timeout; and `async with` disconnecting on both normal exit and exception. Re-verified: full-scope
lint/typecheck counts unchanged (219/129, still exactly this file's own remaining findings), all
15/15 tests passing here, zero regressions across the rest of `tests/`.

#### Third pass: real-world robustness against a genuine UDP peer, not just this module's own logic

Owner-directed: UDP is exposed to uncontrolled external input in ways the rest of `src/` isn't
(failure at init/mid-transfer/while idle, good and bad content, wrong/spoofed sources, timing that
actually matters) - researched official/public UDP best practice (POSIX `recvfrom()`/`sendto()`
semantics, Beej's Guide, connected-vs-unconnected-socket error delivery) and verified every claim
directly against this project's own MicroPython Unix-port build rather than trusting general
networking lore, per repro scripts under `/tmp/.../scratchpad/repro_udp_edge_cases.py` (not
committed - throwaway). Findings:

- **`ready()`'s `wait_time_ms` defaulted to 0, and neither real caller overrides it** -
  `captive_dns.py`'s `DNSServer` waits *forever* for the next query with this default, and
  `async_connect.py`'s NTP client waits out its full timeout on every dropped packet. Confirmed
  directly: 0 busy-polls `poller.ipoll(0)` + `asyncio.sleep_ms(0)` ~9000×/sec while idle vs ~50×/sec
  at 20ms - ~180× the CPU churn on RP2040's single cooperative core, competing with other tasks
  (e.g. Neopixel timing) for scheduler turns, for as long as the DNS server sits idle (most of its
  life). Owner-confirmed fix: default changed to `20` - adds at most 20ms latency per poll cycle to
  both real callers (neither passes this param today), imperceptible for NTP sync / DNS response.
  Verified via a monkeypatch of `asy_udp_socket`'s own module-level `asyncio` name (same read-only-
  builtin technique as the `socket` fake above) recording every `sleep_ms()` argument, proving the
  new default is what `ready()` actually calls, not just what's documented.
- **Datagram truncation is real and silent - confirmed directly, not assumed.** A datagram larger
  than the `recvfrom()` buffer is truncated to that size with zero error and zero signal that
  truncation happened (repro: sent 500 bytes, `recvfrom(10)` returned exactly 10, no exception).
  MicroPython's `socket` module doesn't expose `recvmsg()`/`MSG_TRUNC`, so this module has no way to
  detect it even if it wanted to. **Not fixed - documented as a load-bearing contract in the module
  docstring** instead: callers needing to detect truncation must size their buffer generously (both
  real callers already do: NTP uses 1024 for a 48-byte packet, DNS uses 4096) or add their own
  length-prefixed framing. Matches this module's existing "content-agnostic transport" framing -
  payload validity is the caller's job, not this file's.
- **Connected (`mode="client"`) sockets get kernel-level source filtering for free - confirmed
  directly, not assumed.** A genuine third, independent `socket.socket()` (not `AsyUDPSocket`)
  sending to a connected client's address from an unconnected/unexpected source is never delivered
  - `recvfrom()` raises `EAGAIN`, `poll()` never reports `POLLIN` - even though it targets the exact
  same local port the real connected peer uses. This is a real security property this module relies
  on rather than reimplements, now called out explicitly in the docstring: `mode="server"` sockets
  are unconnected and get no such filtering (`captive_dns.py` doesn't check `addr` on the packets it
  receives today - flagged as out of scope for this transport-only module to fix, not silently
  patched in).
- Zero-length datagrams (RFC 768 explicitly permits them) and oversized outgoing sends (>65507
  bytes, the IPv4 UDP payload ceiling) were both already handled correctly by the existing contract
  - confirmed directly (`recvfrom()` returns `(b"", addr)`, distinguishable from the `(None, None)`
  timeout sentinel; `sendto()`/`write()` catch the real `OSError(EMSGSIZE)` and return `None` like
  every other socket failure) - no code change, added as regression tests since neither case had
  one before.

Explicitly out of scope, confirmed via architecture, not silently assumed: payload-level validation
(malformed NTP headers, corrupt DNS queries) belongs to `async_connect.py`/`captive_dns.py`, not
this transport module - it never inspects content by design (see the docstring's "content-agnostic
transport" paragraph, added this pass).

**Real-hardware verification gap, flagged rather than silently generalized (per CLAUDE.md's
datasheet/platform-target rule):** every empirical claim above - the `POLLERR`/`POLLHUP` fix from
the second pass included - is verified against the MicroPython Unix-port build's socket
implementation, which shares nothing with the real rp2 target's lwIP-based TCP/IP stack beyond the
same Python-level API surface. Whether lwIP delivers ICMP port-unreachable to `poll()` the same way
the Linux kernel does, whether its UDP receive-queue/truncation/connected-socket-filtering behavior
matches exactly, is **not verified against real hardware or rp2-specific MicroPython documentation
in this session** - no rp2 hardware was available to test against. If a deployed unit ever shows
UDP behavior diverging from what's documented/tested here, this gap is the first place to look.
*(Considered closing this via a standalone on-device verification script during the sixth pass -
owner judged it too hypothetical to be worth pursuing as a real issue. Remains open, not being
actively chased; still the first place to look if real behavior ever diverges.)*

8 new tests (23 total in `tests/test_asy_udp_socket.py`), most driven through a new
`AdversarialPeer` test fixture - a genuine independent `socket.socket()`, never an `AsyUDPSocket`,
bound to its own real loopback address, used to fire real packets at the module under test rather
than mocking anything: oversized-datagram truncation, zero-length datagrams, an outgoing payload
over the UDP size ceiling, arbitrary/non-UTF8 binary content round-tripping untouched, connected-
mode source filtering against a genuine off-path sender (address discovered through a real packet
exchange, not introspection - `getsockname()` isn't available on this Unix-port build *or* the real
rp2 stub), a burst of 5 queued datagrams draining in order, a realistically-delayed genuine reply
arriving inside vs. after the timeout window, and the fixed `wait_time_ms` default verified via the
`asyncio`-recording monkeypatch. Re-verified: full-scope `scripts/lint.sh`/`scripts/typecheck.sh`
unchanged (219/129, still exactly this file's own pre-existing findings), all 23/23 passing here,
zero regressions across the rest of `tests/` (`scripts/test.sh`, all 12 files green).

#### Fourth pass: uncaught-exception audit, constructor configuration matrix, integration tests

Owner-directed: a systematic, code-first audit of every place in the file (or a function it calls)
that could raise something not already handled, followed by a full constructor-configuration test
matrix (valid and invalid parameter combinations) and integration-level tests mirroring the current
real upstream callers' exact usage. Every suspected gap below was **confirmed empirically against
the built Unix-port interpreter before being called a real finding** - repro scripts under
`/tmp/.../scratchpad/repro_exception_audit.py` and `repro_mode_hang.py` (not committed - throwaway)
- and **re-confirmed fixed the same way afterward**, not just reasoned about or trusted from the
fix's own diff.

Six real findings, all owner-approved before fixing:

- **An invalid `mode` caused a genuine, unrecoverable lockup - the most severe finding of this
  session.** `_connect()`'s retry loop's `else` branch (dead code for the two real, correct mode
  values) set `self.connected = False` but never incremented `tries` or awaited anything, so
  `while (not self.connected) and (tries < self.conn_tries):` spun forever with **zero yield
  points**. Confirmed directly: the process required a hard `kill`, even under
  `asyncio.wait_for()` - the offending coroutine never yields control back to the scheduler for
  any timeout to fire. Since MicroPython's asyncio on RP2040 is single-core cooperative, this
  would starve *every* other task sharing the loop, including whatever feeds `machine.WDT` - the
  device would eventually hard-reset via watchdog (self-healing, but masking a config typo as a
  random reboot instead of a clear error). Fixed: `mode` is now validated eagerly in `__init__`,
  raising `ValueError` immediately - impossible to reach the old lockup at all anymore.
- **A malformed `addr` (right tuple shape, wrong element types - e.g. an `int` host) raised an
  uncaught `TypeError`** from `sock.connect()`/`sock.bind()`, bypassing every `except OSError:` in
  the file. Confirmed directly. Fixed: validated eagerly in `__init__` too - but see below, this
  needed a second iteration once it broke the existing test suite.
- **A wrong-typed `conn_tries` (e.g. `None`) raised an uncaught `TypeError`** from
  `tries < self.conn_tries`. Confirmed directly. Fixed the same way.
- **`MemoryError` is not an `OSError` subclass in MicroPython** - confirmed directly
  (`issubclass(MemoryError, OSError)` is `False`), so every existing `except OSError:` in the file
  (setup, connect/bind, `sendto`/`write`/`recvfrom`, `disconnect`) was blind to allocation
  failure - a realistic condition on RP2040's 264KB SRAM for a device meant to run unattended for
  years, not a hypothetical. Fixed: every one of those `except` clauses now catches
  `(OSError, MemoryError)`.
- **`disconnect()` could get permanently stuck mid-teardown.** The whole method was one
  `try`/`except OSError`; if `poller.unregister()` raised, the exception aborted the block before
  `sock.close()`/`self.sock = None`/`self.connected = False` ever ran. Confirmed directly: the
  object was left with `sock` and `poller` both still set and `connected` still `True`, forever -
  a real fd leak with no self-heal, unlike every other failure path in this file. Fixed: `disconnect()`
  now eagerly clears `self.sock`/`self.poller`/`self.connected` *before* attempting
  `unregister()`/`close()`, each independently guarded - a failure in either step can no longer
  leave the object in a broken state.
- **`ready()`'s poll loop wasn't safe against a concurrent `disconnect()` on the same instance.**
  It only checked `self.poller is None` once, before the loop; a `disconnect()` call from another
  coroutine mid-loop (nothing in the file enforced or even documented single-caller-at-a-time)
  would null `self.poller`, and the next `self.poller.ipoll(0)` crashed with `AttributeError`.
  Confirmed directly. Fixed defensively: `ready()` now re-checks every iteration and returns
  `False` instead of crashing - matching this file's own "never raises" contract instead of
  relying on callers to never race it.

**A real conflict surfaced mid-fix, resolved by re-deriving the actual constraint instead of
guessing:** the first version of the `addr` validation (`isinstance(addr, tuple)`, strict) broke
every single existing test, because `make_addr()`'s established Unix-port workaround (see the third
pass above) returns `getaddrinfo()`'s resolved object - on this build, an opaque `bytearray`, not a
tuple. Verified directly that a genuine plain tuple still fails against this build's
`connect()`/`bind()` (`TypeError: object with buffer protocol required`, the same long-standing
Unix-port bug from the first pass) - so there was no single value that could satisfy both a strict
tuple check *and* actually work at the socket-syscall level in this test environment. Resolved by
validating tuple *contents* only when `addr` actually is a tuple (the documented, real-hardware
case), while accepting `bytes`/`bytearray` as an opaque, already-resolved sockaddr this file has no
business inspecting (matching the docstring's existing "passes addr through untouched" framing) -
correct for both real hardware (always a tuple) and this test environment (always the resolved
opaque object) without special-casing the test environment inside production code.

Explicitly scoped to the constructor: "every configuration" here means `AsyUDPSocket(addr, mode,
conn_tries)`'s own parameter space, not every argument of every method (`sendto()`'s `msg`,
`write_and_recvfrom()`'s `tries`, etc.) - those stay within this project's existing convention of
trusting mypy-checked call sites rather than adding runtime validation for scenarios neither real
caller can produce.
*(Partially revisited by the sixth pass below: `ready()`'s `mask`/`timeout_ms`/`wait_time_ms` and
`write_and_recvfrom()`'s own `tries` turned out to have a real, reproducible crash - not a
hypothetical "neither real caller can produce" scenario, but a concrete uncaught `TypeError`
bypassing this file's own except clauses - so those two got fixed. This doesn't reopen the general
"don't validate every method argument" scope decision itself; `sendto()`'s `msg`/`addr` and
`recvfrom()`'s `buf` remain deliberately unvalidated at entry, relying on the real socket call's own
`except (OSError, MemoryError, TypeError)` to convert whatever they raise - that part of this
decision still stands.)*

19 new tests (42 total): a full valid-combination sweep (`mode` × `conn_tries` including the `0`/
negative edge case) plus a pre-resolved-`bytes`-addr acceptance test; rejection tests for each of
`mode`/`addr`/`conn_tries` individually invalid (multiple values each) and three combinations of
*multiple* invalid parameters together; the `MemoryError`-catching fix exercised at every one of
its four sites (`_connect()`'s setup, `write()`, `sendto()`, `recvfrom()` - the last via a genuine
pending datagram from a real peer, so it actually reaches the real `recvfrom()` call instead of
timing out inside `ready()` first); the `disconnect()` partial-failure fix (a poller whose
`unregister()` raises); and the `ready()` concurrency fix (a poller that nulls the owning object's
`self.poller` mid-loop, simulating a genuine concurrent `disconnect()`).

**Integration-level tests**, informed by (not importing - `improved-quality/` stays out of scope
per CLAUDE.md's hard rule) the current real upstream callers, mirroring each one's exact documented
call shape rather than a snapshot of its WIP implementation (owner-directed: "take the upstream
callers as a knowledge extension of what are real use cases", resolving an explicit conflict with
the standing "tests belong once code is promoted to `src/`" convention in favor of testing the
*contract* these callers rely on):

- **NTP client pattern** (`async_connect.py`): `AsyUDPSocket(addr, mode="client")` +
  `write_and_recvfrom()` with the real 48-byte-request/1024-byte-buffer shape, `disconnect()`
  called once on success *and* unconditionally again in `finally` (proving that exact double-call
  is safe, not just idempotency in isolation) - a success round trip against a genuine responder, a
  genuinely unreachable server (proving `msg` ends up `None`, matching the real `if msg is None:`
  branch, without ever needing the caller's broad `except Exception` backstop), and a responder
  that replies with outright garbage (proving content-agnostic delivery through the exact real call
  shape, not just the generic binary-content test from the third pass).
- **DNS server pattern** (`captive_dns.py`): `AsyUDPSocket(("0.0.0.0", port), mode="server")` +
  `recvfrom(4096)` + conditional `sendto()`, including the real any-interface-bind-then-receive-
  via-127.0.0.1-targeted-traffic path (every other test in this file binds and targets `127.0.0.1`
  directly, never exercising a real `0.0.0.0` bind end-to-end). Also confirmed a real integration
  contract: `captive_dns.py`'s exact guard is `if data is not None and addr is not None:`, assuming
  the pair is always both-set or both-`None` together - proved directly that `recvfrom()` never
  returns a mismatched pair, in either the timeout or success path.
- **Fault propagation through the DNS server's processing path**: `captive_dns.py` discards
  `sendto()`'s return value entirely - a failed reply is silently swallowed one level above this
  module, never observed or logged by the real caller today. Flagged here as a real gap (not fixed
  - `captive_dns.py` is out of scope), and proved the part that *is* this module's responsibility:
  a failed `sendto()` (targeting a genuinely unreachable address) cannot corrupt the server socket
  for the next, unrelated query in the same long-lived `DNSServer` loop.
- **"Future, still to be refactored upstream modules"**: since no such code exists yet to import or
  drive, coverage here is provided by the constructor-configuration matrix and the uncaught-
  exception fixes above - a robust, well-defined public contract protects whatever calls into it
  next, current or future, rather than something that could only be proven against code that
  doesn't exist yet.

Re-verified: full-scope `scripts/lint.sh`/`scripts/typecheck.sh` still unchanged (219/129), all
42/42 passing here, zero regressions across the rest of `tests/` (`scripts/test.sh`, all 12 files
green).

#### Fifth pass: mutation-bypass, connect/disconnect concurrency, cancellation-safety of the new lock

Owner-directed follow-up audit: re-check the whole file once more for oversights, strange
behaviors, and unhandled/untested conditions - specifically targeting what the fourth pass's fix
*didn't* close. Every finding below was reproduced empirically first (repro scripts under
`/tmp/.../scratchpad/`, not committed), fixed, then re-verified the same way.

**The fourth pass's `__init__` validation only runs once, at construction - a direct
post-construction mutation of a public attribute reintroduces the exact same uncaught-exception
bugs through a different door.** Confirmed directly at four call sites: `self.addr` mutated to a
malformed tuple → uncaught `TypeError` from `sock.connect()`/`sock.bind()`; `self.conn_tries`
mutated to `None` → uncaught `TypeError`, but from an unexpected place - `tries < self.conn_tries`
is the retry loop's own *condition*, evaluated before the inner per-attempt `try` is ever entered,
so only the *outer* setup `try`/`except` covers it, and that one hadn't been widened yet either
(found by testing the fix, not just the bug - the first fix attempt still failed this exact case);
`sendto()`'s own per-call `addr` argument malformed → the same uncaught `TypeError`; `recvfrom()`'s
`buf` argument wrong-typed → uncaught `TypeError`, but only confirmed once a genuinely pending
datagram let `ready()` actually reach the real `recvfrom()` call (a first attempt at this specific
test was inconclusive - nothing was ever sent, so the timeout path returned before ever touching
the buggy call). Owner-decided fix (two options were presented - widen exception handling
further, or add validating property setters - the owner chose a hybrid): `addr`/`mode`/`conn_tries`
are now stored as `_addr`/`_mode`/`_conn_tries` (private-by-convention, signaling "not meant to be
reassigned from outside" - Python doesn't truly enforce this, so it's a naming signal, not a
guarantee), *and* every touching `except` clause (both of `_connect()`'s try blocks, plus
`sendto()`/`write()`/`recvfrom()`) now also catches `TypeError`, so the object self-heals into "never
connects" instead of crashing regardless of how it got into a bad state. Mutating `_mode` was
separately confirmed *not* to be a crash risk - `_connect()`'s branch is a plain `if/else` (client
vs. everything else) since `__init__` already guarantees only the two real values reach it, so a
corrupted `_mode` just falls through to the `bind()` path rather than hitting the old three-way
branch's dead `else`; documented and tested as defined (if surprising) behavior, not fixed further.

**A second, more severe related bug surfaced while investigating the first: a `disconnect()` call
concurrent with another coroutine's in-flight `_connect()` retry crashed with an uncaught
`AttributeError`.** `disconnect()` had no coordination with `_connect()` at all - a concurrent
`disconnect()` could null `self.sock`/`self.poller` while `_connect()`'s retry loop was still
mid-flight, so the loop's next `self.sock.connect()`/`bind()` call hit `'NoneType' object has no
attribute 'bind'`. Confirmed directly. This is the same underlying gap as the owner's separately-
approved fix for concurrent callers: **a coroutine calling a public method while another
coroutine's `_connect()` is mid-retry-backoff on the same instance got a spurious "not ready" `None`
instead of joining the in-flight attempt** (confirmed directly in the fourth pass's own write-up
above, revisited here since the owner chose to actually fix it this pass rather than just document
it). Both are closed by the same mechanism: a new per-instance `asyncio.Lock` (`self._connect_lock`)
serializes `_connect()`'s entire setup/retry phase against both itself (join semantics: a second
caller now waits for and benefits from the first's in-flight attempt, confirmed directly - a
`sendto()` call made while another coroutine's retry is still resolving now returns the real result
once that retry succeeds, not a premature `None`) and against `disconnect()` (confirmed directly: a
concurrent `disconnect()` now waits for the in-flight attempt to finish - bounded by
`conn_tries × the retry backoff` - instead of tearing it down mid-flight). `_connect()`'s own
internal self-heal call had to move to a new `_disconnect_locked()` helper (the actual teardown
logic, assuming the lock is already held) rather than calling the public `disconnect()` directly,
since `asyncio.Lock` isn't reentrant - `_connect()` calling `disconnect()` while already holding the
lock would have deadlocked. Caught and fixed before it ever shipped, by tracing through the
non-reentrancy question during design rather than after a test failure.

**Locks plus cancellation are a classic deadlock source, so this wasn't assumed safe just because
it worked in the non-cancelled case - verified directly, both directions:** cancelling a task while
it *holds* the lock (mid-retry-backoff) still correctly propagates `CancelledError` and releases the
lock (`async with`'s `__aexit__` runs on any exception unwind, including `BaseException` subclasses
like `CancelledError` - confirmed empirically, not just cited from the language spec); cancelling a
task while it's *waiting* to acquire the lock (not holding it) also propagates cleanly and leaves the
lock's internal state healthy for the next caller. Both were real risks worth checking given this
file just gained its first lock, and both came back clean - no new bug found here, but confirmed
rather than assumed, and locked in as regression tests given how easily this class of change goes
wrong.

**Also confirmed already-correct (no code change), previously untested boundary/misuse behaviors:**
`write()` called on a bound-but-unconnected `mode="server"` socket (a caller misuse this file
deliberately doesn't structurally guard against, per the second pass's "considered and rejected" -
that reasoning was never actually verified non-crashing until now) returns the `None` sentinel via
the real `OSError` it triggers, exactly like any other socket failure; zero-length outgoing sends
(`sendto(b"", ...)`) succeed, symmetric to the zero-length *receive* case from the third pass;
`recvfrom(buf=0)` against a genuinely pending datagram returns `(b"", addr)` - an extreme instance
of the already-documented truncation contract, not new behavior; `disconnect()` on a fresh,
never-`_connect()`-ed object is a clean no-op; `write_and_recvfrom(..., tries=0)` returns
`(None, None)` immediately, no crash.

14 new tests (56 total): the four mutation/malformed-argument fixes (each self-heals instead of
crashing, verified directly); the `disconnect()`-during-in-flight-retry fix (with a timing
assertion proving it genuinely waited for the retry cycle rather than either crashing or hanging
forever); the concurrent-caller-joins-the-attempt fix (B's call genuinely succeeds once A's retry
succeeds, not a redundant retry of its own); both lock-cancellation-safety proofs; and the five
already-correct boundary behaviors above. Re-verified: full-scope `scripts/lint.sh`/
`scripts/typecheck.sh` still unchanged (219/129), all 56/56 passing here, zero regressions across
the rest of `tests/` (`scripts/test.sh`, all 12 files green).

#### Sixth pass: ready()'s own polling-loop parameters, write_and_recvfrom()'s own tries parameter, and a documentation/spec re-check

Owner-directed re-audit: go through the file's own module docstring paragraph by paragraph and
re-verify each documented claim against current MicroPython 1.28.0 documentation (the refactor's
actual pinned target per `toolchain/versions.toml` - not the deployed 1.26 pin), general POSIX UDP
semantics, `asyncio` behavior, `select.poll` event-flag definitions, processing load, and the "never
raises" contract, specifically hunting for exception paths still without a test. Two real,
previously-undiscovered bugs found - both the same shape as the fifth pass's mutation-bypass
findings (a comparison/construct on a caller-supplied parameter sitting outside every method's own
`try`/`except`), just on different parameters:

**`ready()`'s own `mask`/`timeout_ms`/`wait_time_ms` parameters were completely unguarded.**
Confirmed directly: `timeout_ms=None` (or any non-numeric type) raised an uncaught `TypeError` from
`if (timeout_ms > 0) and ...` inside the poll loop; `wait_time_ms=None` raised from inside
`asyncio.sleep_ms()`'s own implementation; `mask=None` raised from `event & (mask | select.POLLERR |
select.POLLHUP)`. None of these were reachable through `sendto()`/`write()`/`recvfrom()`'s own
`except (OSError, MemoryError, TypeError)` clauses, since those only wrap the *real socket call* -
`await self.ready(...)` is called *before* that `try` block even starts, so a crash inside `ready()`
propagated straight out of every public I/O method, violating this file's own explicitly documented
"never raises" contract. Fixed by wrapping the poll loop's entire per-iteration body (the `ipoll()`
call, the event check, the timeout comparison, and the `sleep_ms()` await) in the same
`except (OSError, MemoryError, TypeError)` tuple used everywhere else in this file, returning `False`
- matching `ready()`'s own contract instead of adding a separate validation layer. Verified this
doesn't swallow cancellation: `asyncio.CancelledError` is a `BaseException` subclass, not in that
tuple, and cancelling a task mid-`sleep_ms()` inside the new `try` still propagates correctly
(confirmed directly, not assumed, given the fifth pass's lock-cancellation work already established
this file needs that kind of check taken seriously). `OSError`/`MemoryError` were included in the
same wrap for defense-in-depth consistency with the rest of the file, even though empirical testing
(registering a socket, closing it without unregistering, then calling `ipoll(0)`) found no case where
`ipoll()` itself actually raises on this project's MicroPython Unix-port build - it returns event
value `32` (Linux's `POLLNVAL`, though this `select` module doesn't expose that name as a constant at
all - confirmed via `dir(select)`) instead of raising, and that value doesn't match any bit this
file's own `mask | POLLERR | POLLHUP` check looks for, so an unregistered-but-still-closed fd would
just poll silently until timeout rather than crash or falsely report readiness - not a live bug since
`self.sock`/`self.poller` are only ever nulled together via `_disconnect_locked()`, but confirmed
rather than assumed.

**`write_and_recvfrom()`'s own `tries` parameter had the same shape of bug.** `for _ in
range(tries):` raised an uncaught `TypeError` for `tries=None` or a non-numeric `tries` (e.g. a
`str`) directly from `range()`'s own construction, and this method has no `try`/`except` of its own
around that loop at all. (Aside, confirmed while investigating: this build's `range()` is more lenient
than CPython's - `range(1.5)` doesn't raise `TypeError: 'float' object cannot be interpreted as an
integer` the way CPython does, it silently iterates by comparing the float bound directly, yielding
two iterations for `range(1.5)` - a MicroPython looseness, not a bug in this file, but worth knowing
if `tries` or similar loop-bound parameters are ever handed a float elsewhere in this codebase.) Fixed
the same way as the fifth pass's other parameter-mutation fixes: `range(tries)` is now constructed in
its own `try`/`except TypeError`, returning the method's own `(None, None)` sentinel on failure,
before the loop ever starts.

**Everything else survived re-verification with no code change needed, each checked directly rather
than assumed:** `micropython.const(0.5)` (a float, despite current MicroPython docs stating `const()`
constant-folding is scoped to integer expressions only) compiles cleanly with this project's pinned
`mpy-cross` and round-trips correctly through a real `.mpy` load - not a bug, just docs describing the
guaranteed/recommended surface more narrowly than what this compiler build actually accepts; a
negative `recvfrom(buf)` (e.g. `buf=-1`) already surfaces as a `MemoryError` from the underlying C
allocator (a huge `size_t` wraparound), which this file already catches - no new gap; a battery of
malformed `sendto()` addresses (out-of-range port, negative port, `None`, `()`, an embedded-NUL
hostname) and malformed `msg` values (`int`, `None`) all already convert cleanly to the `None`
sentinel via the existing `except (OSError, MemoryError, TypeError)`; `select.poll.register()`/
`unregister()`/`ipoll()`'s documented semantics (unsolicited `POLLERR`/`POLLHUP` reported regardless
of the requested eventmask, `ipoll()` allocation-free iteration, `unregister()` being a no-op rather
than an error for an already-unregistered stream) all match this file's actual usage; a hypothesized
"sticky POLLERR" risk (current MicroPython docs warn that `POLLERR`/`POLLHUP` "must be acted on...
otherwise subsequent calls will keep returning immediately with these flags set for that stream")
turned out not to reproduce on this build - consuming the pending error once (via the real
`recvfrom()` call raising and being caught, exactly what this file already does) clears it, confirmed
by polling again afterward and observing a normal, non-instant timeout, then a fresh send/receive
cycle working normally; MicroPython 1.28.0's `asyncio` still has no built-in UDP-readiness primitive
(`open_connection()`/`start_server()` remain TCP-only per current upstream discussion), and
`asyncio.Lock` remains documented as non-reentrant with the exact acquire/release semantics this
file's design already assumes - both matching what the module docstring already claims. The existing
`asy_udp_socket.py`↔real-rp2/lwIP-hardware verification gap flagged in the fourth pass (everything
here is Unix-port-verified, not verified against real hardware's TCP/IP stack) remains open and
unchanged - re-confirmed still accurate, not newly discovered.

6 new tests (62 total): `ready()`'s three parameter fixes (`mask`, `timeout_ms`, `wait_time_ms`) each
verified directly, plus one confirming the new `try`/`except` still lets cancellation through;
`recvfrom()` (not just `ready()` in isolation) verified to surface the fix through the real public
entry point callers actually use; `write_and_recvfrom()`'s `tries` fix verified across three malformed
values (`None`, a `str`, a `list`). Re-verified: full-scope `scripts/lint.sh`/`scripts/typecheck.sh`
still unchanged (219/129), 62/62 passing here, zero regressions across the rest of `tests/`
(`scripts/test.sh`, all 12 files green, 752 tests total).

#### `captive_dns.py` (`improved-quality/`, not promoted): source-subnet filtering fix

Owner-directed follow-up to the `asy_udp_socket.py` sixth pass's two remaining open items: the real-
hardware verification gap was judged too hypothetical to chase (dropped, not pursued); this one -
`captive_dns.py`'s `mode="server"` socket receiving from anyone with no source-address check at all
(originally flagged in the third pass, restated in the fourth) - was judged worth fixing, **with
explicit owner sign-off to touch `improved-quality/` source files for it**, an exception to the
standing hard rule against routine edits there (see CLAUDE.md).

Fix: `DNSServer.run()` now takes a `netmask` parameter alongside `server_ip`, computes the AP's own
network prefix once (`_ipv4_to_int(server_ip) & _ipv4_to_int(netmask)`), and rejects (silently
`continue`s past, no response sent) any request whose source address doesn't fall in that same
subnet - a captive-portal DNS server has no legitimate reason to answer a query from off its own AP.
`async_connect.py`'s one real call site (`self.dns_server.run(own_ip)`, hotspot startup) updated to
`self.wlan.ifconfig()[:2]` (confirmed via current MicroPython docs: `ifconfig()` returns `(ip,
subnet_mask, gateway, dns)`, in that order) and pass both. `_ipv4_to_int()` is a small, dependency-
free dotted-quad-to-int helper (no `ipaddress` module needed/assumed on MicroPython).

**A real bug surfaced during verification, not just reasoned about - confirmed directly then fixed
before this was considered done:** the first version's guard only caught `(TypeError, ValueError)`
around the new subnet-membership check. Empirically driving the real `DNSServer.run()` loop (routed
around this Unix-port test build's separate, already-documented plain-tuple-`bind()` limitation by
substituting a `getaddrinfo()`-resolved `AsyUDPSocket`, same technique `tests/test_asy_udp_socket.py`
already uses) surfaced a second, distinct Unix-port-only quirk: a socket bound via a resolved
sockaddr returns an *opaque raw sockaddr* from `recvfrom()` here too, not a `(host, port)` tuple -
`addr[0]` was a raw `int` (a sockaddr struct byte), not a string, and calling `.split(".")` on an
`int` raises `AttributeError`, not `TypeError`/`ValueError` as first assumed. This escaped the narrow
guard entirely and fell through to the loop's own broad `except Exception: ... await
asyncio.sleep(3)` - not a crash, but a real, avoidable 3-second stall of the *entire* DNS server (and
every other client waiting on it) per malformed packet. Fixed by adding `AttributeError` to the
guard's tuple, verified via `sys.print_exception()` to pin down the exact exception type rather than
guessing from the message alone. This is real, reproducible code behavior in this test environment,
not the hypothetical "any `await` could theoretically raise" class of issue - matches the owner's own
stated bar from the `asy_udp_socket.py` sixth pass for when this kind of hardening is actually worth
it. (On real rp2 hardware, `addr[0]` is expected to always be a genuine string host per the installed
stub - this guard is defense-in-depth there, not expected to ever actually fire.)

**Verification, not a permanent test file**: `captive_dns.py` stays in `improved-quality/`, not
promoted to `src/`, so this repo's established "tests belong once code is promoted" convention (see
`src/README.md`, CLAUDE.md's hard rules) means no `tests/test_captive_dns.py` was added - matching
how this fix was made (a targeted robustness patch, not a promotion). Verified instead via throwaway
repro scripts (`/tmp/.../scratchpad/`, not committed): `_ipv4_to_int()` correctness against several
realistic on-subnet/off-subnet/self/broadcast addresses; the real `DNSServer.run()` loop driven
end-to-end confirming the subnet-check math functions inside the actual receive loop and that a
malformed source address is silently ignored rather than crashing or stalling; and a full
on-subnet/off-subnet/malformed-address decision-logic pass through the real `run()` coroutine (a fake
`recvfrom()` feeding pre-shaped `(host: str, port: int)` tuples, since this Unix-port test
environment can never itself produce that shape for this specific socket configuration) confirming
exactly one of three requests gets answered - the on-subnet one - and the other two are cleanly
ignored with zero replies sent and zero crashes. Re-verified: full-scope `scripts/lint.sh` 219→220
(exactly one new finding - the new code's own `.format()` call, matching this file's pre-existing
style rather than introducing f-strings inconsistently; not a regression elsewhere),
`scripts/typecheck.sh` unchanged at 129, `scripts/test.sh` all 12 files green (752 tests, unaffected -
`captive_dns.py` isn't imported by any of them).

This resolves the third pass's "`captive_dns.py` doesn't check `addr` on the packets it receives
today - flagged as out of scope for this transport-only module to fix" note and the fourth pass's
parallel reference to the same gap - both were about `captive_dns.py`, not `asy_udp_socket.py` itself,
and are closed by this fix rather than needing any further change in `asy_udp_socket.py`.

#### `captive_dns.py`: `DNSQuery` unguarded against truncated/malformed query data

Owner-directed bird's-eye follow-up pass over the whole file after the subnet-filtering fix above,
looking specifically for more oversights of the same kind rather than assuming that fix was the only
one. Found one: `DNSQuery.__init__` parses the raw datagram (`data[2]` for the opcode nibble, then
walks length-prefixed labels starting at `data[12]`) with no bounds checking and no exception
handling at all - a datagram shorter than 3 bytes, shorter than 13 bytes, or truncated/malformed
mid-label all raise an uncaught `IndexError`; a label containing bytes that aren't valid UTF-8 raises
`UnicodeError`. `DNSQuery(data, ...)` is constructed inside `DNSServer.run()`'s own try block, *after*
the subnet-membership check, so any on-subnet client - not necessarily malicious, just a flaky Wi-Fi
client, a stray port-scanner, or a buggy resolver - reaching this with a short or malformed packet
falls through to the loop's broad `except Exception: ... await asyncio.sleep(3)`, stalling the entire
DNS server (every other client waiting on it too) for 3 seconds per bad packet. Same class of bug as
the `addr[0]`/`AttributeError` one found while verifying the subnet-filter fix, just in the
query-parsing path instead of the address-parsing path - and by the same "concrete, reproducible, not
hypothetical" bar the owner set during the `asy_udp_socket.py` sixth pass, this one clears it too:

```
MICROPYPATH="improved-quality:src:.:/root/pico-toolchain/micropython/extmod" micropython repro.py
0 RAISED IndexError bytes index out of range   # b""
1 RAISED IndexError bytes index out of range   # b"\x00"
2 RAISED IndexError bytes index out of range   # b"\x00\x00"
3 RAISED IndexError bytes index out of range   # 3 bytes, tipo==0 but len<13
4 RAISED IndexError bytes index out of range   # exactly 12 bytes
5 RAISED IndexError bytes index out of range   # length byte with no bytes following
6 RAISED IndexError bytes index out of range   # one label then truncated
7 RAISED UnicodeError                          # label containing an invalid UTF-8 byte (0xff)
```

Fix: wrapped the opcode-extraction-through-label-walk block in `try: ... except (IndexError,
UnicodeError): self.domain = ""`. Reuses the file's own existing sentinel rather than inventing a new
one - `self.domain == ""` was already how a non-standard-query (`tipo != 0`) says "don't respond"
(`response()`'s `if self.domain:` gate). Re-ran the same 8 malformed inputs after the fix: all resolve
to `domain == ""` instead of raising; a well-formed query (`"a.io"`) still parses to `"a.io."` and
still produces a valid response packet, confirming the fix doesn't change legitimate-query behavior.

Verified the same way as the subnet-filter fix - no permanent test file (`captive_dns.py` still isn't
promoted to `src/`), throwaway scratchpad repro scripts only. Re-ran full-scope
`scripts/lint.sh`/`scripts/typecheck.sh`/`scripts/test.sh`: 220/129 unchanged (no new findings from
this fix), all 12 `tests/` files green, 752 tests total, unaffected (`captive_dns.py` isn't imported
by any of them).

### `asy_sgp40_driver.py` + `voc_algorithm.py` → `src/`

Promoted together (owner-directed): `asy_sgp40_driver.py`'s `measure_index_and_raw()` is
`voc_algorithm.py`'s only real caller. Verified against the actual SGP40 datasheet (owner-provided,
`datasheets/sgp40/Sensirion_Gas_Sensors_Datasheet_SGP40.pdf`, v1.2 Feb 2022 — the earlier session
that first reviewed this file couldn't fetch it directly) and against Sensirion's original VOC
algorithm C reference (`Sensirion/embedded-sgp`, now archived, `sgp40_voc_index/
sensirion_voc_algorithm.c/.h` — the pre-NOx-generalization ancestor of the current
`gas-index-algorithm` repo, and of this file's DFRobot-derived naming): every constant, the struct
field order, and `vocalgorithm_process()`'s exact operation order matched 1:1, no discrepancies.

**Real bugs found and fixed:**
- `_init_sgp()` wrote `self.err_cnt_internal` (no leading underscore) — a dead, unused attribute
  distinct from `base_classes.py`'s real `self._err_cnt_internal`, the counter `_error_check()`
  actually reads. Same class of bug as `asy_scd30_driver.py`'s own (found in a sibling review
  session): after a give-up-and-restart cycle, the real consecutive-failure counter was never
  reset, so a freshly-restarted reader was one bad reading away from immediately giving up again.
  `asy_bmp3xx_driver.py` already had the correct spelling — confirmed via git history that the
  rename happened in `base_classes.py` while `asy_bmp3xx_driver.py` was updated to match and
  `asy_scd30_driver.py`/`asy_sgp40_driver.py` weren't. Fixed here; `asy_scd30_driver.py`'s own copy
  is that file's own promotion's problem.
- `_reset()`'s general-call soft reset was a confirmed real bug, not just a mislabeled comment: the
  datasheet (Table 17) is explicit that `soft_reset` is *"a general call... the first byte refers
  to the general call address and the second byte refers to the reset command"* — i.e. a
  single data byte `0x06` addressed to the reserved bus address `0x00`. The code instead wrote
  *two* bytes, `[0x00, 0x06]`, to the SGP40's own address (`0x59`) — never touching address `0x00`
  at all, and `0x0006` appears nowhere in the datasheet's real command table (Table 8: only
  `0x260F`/`0x280E`/`0x3615`/`0x3682`). Cross-checked against DFRobot's independent
  `DFRobot_SGP40` Python driver, which has the *identical* bug (same wrong target address) —
  confirmed this is a bug that propagated Adafruit → DFRobot → both of this project's drivers, not
  something anyone had verified against the datasheet before. Fixed to a real general call:
  `sgp40.i2c_device.i2c.writeto(0x00, b"\x06")`, still under the device session's shared-bus lock
  (a general call affects every device on the bus, not just this one) and still tolerating a NAK
  (`except OSError: pass`) — not every device needs to acknowledge a general call.
  **Shared-bus blast-radius check, prompted by a later session's "don't deviate from proven
  everyday behavior" concern**: `sensortask-wozi.py` puts `SGP40_Reader` and `BMP3xx_Reader` on
  the same physical `i2c1` bus (pins 19/18), and `sensortask-dev.py` puts `SGP40_Reader` and
  `SCD30_Reader` on the same `i2c1` bus (pins 15/14) — so this fix means every SGP40 init/restart
  now actually broadcasts a real general call onto a bus a second sensor also lives on, where the
  old buggy code never touched address `0x00` at all. Checked both shared sensors' own datasheets
  (`datasheets/bmp3xx/bst-bmp388-ds001.pdf` section 5; `datasheets/scd30/
  Sensirion_CO2_Sensors_SCD30_Interface_Description.pdf` section 1.1/1.4.10): neither documents
  I2C general-call (address `0x00`) support anywhere — BMP388's own reset is a normal addressed
  write (`softreset` 0xB6 to register 0x7E at its own address), SCD30's own reset is likewise a
  normal addressed command (`0xD304` to its own address 0x61). Per the I2C spec, general-call
  support is optional per-device; a device that doesn't implement it simply doesn't ACK, which is
  exactly the `except OSError: pass` path this fix already tolerates. So the fix's real-world
  blast radius on both units sharing a bus with SGP40 is verified negligible — worth recording
  since it wasn't checked when the fix first went in, only reasoned about structurally.
- `initialize()` dropped the "check feature set" step (command `0x20 0x2F`) entirely. Confirmed via
  the datasheet that this command isn't in Sensirion's real command table at all (only
  `sgp40_measure_raw_signal`/`sgp40_execute_self_test`/`sgp4x_turn_heater_off`/
  `sgp4x_get_serial_number` are documented), and that DFRobot's independent driver's own init
  sequence doesn't do it either — an Adafruit-only addition with a live upstream GitHub issue
  ("Feature set check may fail") reporting it rejects real hardware unpredictably. Sitting on the
  restart-after-disturbance path, this was a spurious extra failure mode for zero real validation
  benefit (self-test already positively confirms real, working SGP40 silicon). Owner-confirmed
  before removing.
- `get_raw()`'s post-measurement read delay was 500ms; the datasheet's own command table (Table 8)
  gives 25ms typ/30ms max for `sgp40_measure_raw_signal`, and DFRobot's independent driver
  hardcodes exactly 30ms — this runs once per second, forever, so the gap was a real, ongoing,
  16x-oversized cost, not a one-time init cost like the self-test's similarly-generous margin
  (datasheet 300/320ms typ/max vs. this file's 500ms, left alone). Unlike the two already-recorded
  owner-tested SGP40/SCD30 timing tweaks below, this one showed no sign of ever having been
  deliberately measured. Owner-directed fix: 100ms (>3x the datasheet's own max, well short of the
  old 500ms).
- `measure_raw()` built and immediately discarded a dead local `_compensated_read_cmd =
  bytearray([0x26, 0x0F])` — the actual command bytes were already being written directly into the
  recycled `_measure_command` buffer via `mv[0]`/`mv[1]` two lines above. Leftover from an earlier,
  non-buffer-recycling version of this method. Removed — one fewer allocation on the 1Hz hot path.
- `voc_algorithm.py`'s `_vocalgorithm__mean_variance_estimator___sigmoid__set_parameters(self, L:
  float, X0: float, K: float)` was typed `float` for all three params, but every real call site
  passes pre-`_f16()`-encoded fixed-point `int` values (matching every other analogous
  `set_parameters` method in this file, e.g. `_mox_model__set_parameters(self, SRAW_STD: int,
  SRAW_MEAN: int)`) — mypy caught the resulting real assignment-type mismatch against
  `DFRobot_vocalgorithmParams`'s `int`-inferred fields. Fixed the annotation to `int` to match both
  actual usage and every sibling method's convention; zero behavior change (annotations are never
  evaluated on MicroPython).

**Confirmed correct, not changed, after checking:**
- `_celsius_to_ticks`/`_relative_humidity_to_ticks` (datasheet Table 10) and the compensated
  measurement command's exact byte layout (Table 9) matched the datasheet's own worked examples
  exactly (`25°C→0x6666`/`-45°C→0x0000`/`130°C→0xFFFF`, `50%→0x8000`/`0%→0x0000`/`100%→0xFFFF`).
- `voc_algorithm.py`'s legacy serialization bug BACKLOG.md already recorded
  (`m_mox_model_sraw_std` missing from packed/restored fields) was already fixed in this file —
  confirmed present in the 32-field `pack_into`/`unpack_from` format string.
- `initialize()`'s remaining `serialnumber[0] != 0x0000` check is flagged, not touched: not
  documented by the datasheet (no structural breakdown of the 3-word ID given), not replicated by
  any other reference driver checked (Sensirion's own minimal `embedded-i2c-sgp40`, DFRobot's,
  `agners/micropython-sgp40`) — an unverified assumption inherited from Adafruit, same risk
  category as the feature-set check that was removed. Kept as-is (observed working on deployed
  hardware) per the same "don't change hardware-facing behavior without real-hardware testing"
  caution `_boot.py`'s `import sensortask.py` already gets — owner can revisit with real hardware
  access.
- The FRAM restore mechanism intentionally dumps/restores voc_algorithm.py's *entire* 32-field
  internal state (`vocalgorithm_proc_ser_des`), not Sensirion's own narrower `get_states()`/
  `set_states()` (mean/std only, documented for gaps up to 10 minutes after 3+ hours of runtime).
  Owner-confirmed deliberate: freezing every field, including the `uptime_gamma`/`uptime_gating`
  learning-progress counters, keeps a resumed state internally self-consistent regardless of the
  real gap length (this project's backups can legitimately span days, via `BackupMaxAge`), and
  age-gating/rejection is this driver's own responsibility (`_run_restore`'s `BackupMaxAge` check),
  not something the algorithm file itself needs to enforce. Documented in `voc_algorithm.py`'s own
  module docstring rather than silently treated as equivalent to Sensirion's narrower API.

**FRAM dependency — resolved by timing, not by this promotion's own work**: this file was
originally going to need the same `Protocol`-based decoupling `print_log.py` used, since
`asy_fram_manager.py` wasn't promoted yet when this review started. By the time this promotion
actually landed, `asy_fram_manager.py` had cleared its own `src/` promotion (see above) — so
`asy_sgp40_driver.py` imports `AsyFramManager`/`AsyFramChunkTimestampedBuffer` the same way
`asy_scd30_driver.py` already does, `TYPE_CHECKING`-only (neither name is ever used as a real
runtime value in this file — only `.get_timestamped_chunk()`/`.set_verify()`/etc. are called on an
already-constructed instance passed in from outside), matching `base_classes.py`/`print_log.py`/
`system_service.py`'s own established convention for the same "only ever used as an annotation"
shape. **Found, not fixed (out of scope, already-promoted file)**: `asy_fram_manager.py` itself
keeps a real, unconditional top-level `from asy_spi_driver import SPI` for its own `spi_bus: SPI`
parameter, despite `SPI` fitting that exact same "annotation-only" criterion — a real, live
inconsistency against the convention the other three files already established. Flagged for
whenever `asy_fram_manager.py` next gets touched, not silently fixed here.

**Other typing/style modernization** (first promotion of a `Reader`-shaped file, so the first time
these needed solving): dropped `typing.cast` entirely rather than making it MicroPython-runtime-safe
— `SGP40_Reader.get_data()`'s `NamedTuple`→`SGP40` narrowing now just reconstructs
`SGP40(*data)` (a real, safe re-validation, not a type-only assertion); `_check_storage()`'s
`tuple(cfg_values)`→`tuple[int,int,int]` narrowing now unpacks-then-repacks
(`backup_period, backup_maxage, wait_ntp = cfg_values; return ..., (backup_period, backup_maxage,
wait_ntp)`), which is both cast-free and mypy-exact, not just suppressed. `SGPResults` (a
`Tuple[int|None, int|None, int|None]` distinct from the `SGP40` namedtuple) was dropped entirely —
unlike `asy_scd30_driver.py`'s `SCDResults` (which legitimately differs from its own `SCD30`
namedtuple by carrying derived `math_helpers`-computed fields the raw read doesn't have), SGP40's
raw-read fields and its namedtuple fields are identical, so `_read_sgp()`/`_store_sgp()` now pass
a real `SGP40` end to end. `voc_algorithm.py`'s `DFRobot_vocalgorithmParams.__init__` and `reset()`
were byte-for-byte identical 32-line bodies — `__init__` now just calls `self.reset()`. Six
`_VOCALGORITHM_*` float constants (`..._TRANSITION_MEAN`, `..._TRANSITION_VARIANCE`,
`..._GATING_THRESHOLD_TRANSITION`, `..._GATING_MAX_RATIO`, `..._SIGMOID_K`, `..._LP_ALPHA`) were
plain module globals instead of `const()`-wrapped like every integer constant in the same file —
inconsistent for no reason, confirmed via BACKLOG.md's own already-established finding that
`const()` folds floats too on this target; wrapped to match. A stray `# pylint: disable=all`/
"Complex math conversion from C" comment pair (this project uses ruff, not pylint) removed as dead
tooling-reference cruft. `Tuple`/`Union` (unconditional `from typing import ...`, would crash on
real MicroPython) replaced with bare lowercase generics/`|` throughout both files, following the
now-standard `TYPE_CHECKING` guard pattern for the handful of names (`Callable`/`Coroutine`/`Any`/
`AsyFramManager`/`AsyFramChunkTimestampedBuffer`/`I2C`) that still need it.

**Integration gap, confirmed still stale, kept as a to-do (out of scope for this promotion)**:
`improved-quality/sensortask-wozi.py`'s `SGP40_Reader(...)` call site still uses the pre-refactor
API shape (`SGP40_Reader.get_default_cfg()`, `SGP40_Reader.get_params_memsize()`, a `ts_storage=`
constructor kwarg) that doesn't exist on this file's actual, current constructor — same
already-documented class of gap as `SCD30_Reader`/`BMP3xx_Reader`'s own call sites in the same
file (see "Cross-file wiring gaps... known WIP, not regressions" above). Confirmed via a fresh
`mypy` run that this is unchanged by this promotion (same three `"has no attribute
'get_default_cfg'"` errors as before, just now resolving `asy_sgp40_driver`'s real types instead of
hitting a missing-module gap). `sensortask-wozi.py` stays out of routine-editing scope
(`improved-quality/` source) regardless.

`tests/machine.py`'s fake `machine.I2C` gained a `read_queue` (a FIFO of byte strings, mirroring the
fake `machine.SPI`'s own `read_queue`/`_next_read_bytes`) — the existing fake had no way to script a
*response* to a `readfrom_into()` call at all (only `readfrom_mem`/`writeto_mem`'s register dict
did), which every existing `src/` I2C caller happened not to need but this word-oriented
command/response protocol does. FRAM-backed tests use the real `AsyFramManager` against
`tests/_fram_chip_fake.py`'s simulated chip, matching `tests/test_fram_integration.py`'s own
pattern — including a "simulated reboot" (a *second*, independently-allocating `AsyFramManager`
sharing the first's underlying `spi_bus`/chip, not the same manager instance reused, which would
bump-allocate the second `SGP40_Reader`'s chunks into fresh, never-written territory instead of
reading back the first one's) and an aged-backup test that monkeypatches
`asy_fram_manager.py`'s own `time` module reference (real `time` is a read-only builtin — same
technique `tests/test_system_service.py` already established) rather than poking the chip's raw
stored timestamp bytes directly, since that only corrupts one of the two dual-redundant copies'
CRC and gets silently healed from the other, untouched (young) copy.

39 tests (`tests/test_asy_sgp40_driver.py`) + 22 (`tests/test_voc_algorithm.py`). Coverage: 84%/88%
respectively — most of the remainder is genuinely low-value to chase further (rare `voc_algorithm.py`
`_fix16_div`/`_fix16_sqrt` internal overflow branches needing precisely-threaded fixed-point operand
values; `_run_restore`'s NTP-still-pending and timestamp-less-backup branches, needing extra FRAM
scaffolding for a fairly narrow, already-indirectly-exercised code path), not chased further
(owner-confirmed elsewhere in this doc: no trouble with less than 100% coverage as long as nothing
left uncovered is a real gap).

**Post-push CI caught two things a stray global `mypy` missed locally** (PR #19): a pre-existing
upstream MicroPython-stdlib-stubs drift unrelated to this promotion (`asyncio.gather()`'s 2-arg
form now resolves as `tuple[...]` instead of `Any`, mirroring CPython typeshed's precise-arity
overloads — fixed in `tests/test_asy_udp_socket.py`/`tests/test_asy_fram_manager.py`, kept the
latter's return annotation honest to MicroPython's real list-returning `asyncio.gather()` rather
than matching the stub, per `extmod/asyncio/funcs.py`'s own `return ts`), and a real bug in this
promotion itself: `DFRobot_vocalgorithmParams.pack_into()` accepted `bytearray | memoryview` but
its read-only mirror `unpack_from()` was narrower (`bytes | bytearray`) — inconsistent even though
`asy_sgp40_driver.py`'s `measure_index_and_raw()`/`vocalgorithm_proc_ser_des()` legitimately pass a
`memoryview` through both. Widened `unpack_from()` to `bytes | bytearray | memoryview`, matching
`struct.unpack_from()`'s real buffer-protocol-accepting behavior. **Root cause of missing this
locally**: this session had been running a stray globally-installed `mypy` (1.19.1) instead of the
project's own `uv sync`-managed `.venv` (which CI always uses fresh, currently `mypy==2.3.0`,
pinned only loosely as `"mypy"` in `pyproject.toml`) — the version gap was large enough to produce
materially different results on the exact same source. Confirmed by running `uv sync` and
re-checking with the venv's actual `mypy`, which reproduced both CI failures immediately. Take-away
for future sessions: always run lint/typecheck through `uv sync`'s `.venv`, not whatever `mypy`/
`ruff` happens to already be on `PATH` — a global install can silently diverge from what CI (and
`pyproject.toml`'s own pin) actually enforces.

#### Post-promotion architecture review (structure/setup/inheritance/sensortask-integration pass)

A second review pass over the merged-but-still-open PR, checking structure/leanness, setup,
`SensorReaderConfig`/`Lockable` inheritance correctness, coherence with the (not-yet-rewritten)
`sensortask-*.py` integration layer, sensor-specific correctness against the datasheet, and general
completeness - separate from the initial promotion pass above.

**Real bug found and fixed**: `initialize()`'s self-test check compared the *whole* returned word
against `0xD400`. Datasheet Table 13 is explicit that only the high byte is the pass/fail marker
(`0xD4` pass, `0x4B` fail) - *"0xD4 0xXX: all tests passed successfully (ignore 0xXX byte)"* - the
low byte is documented as a genuine don't-care, not guaranteed zero. The old check would have
spuriously raised "Self test failed" on real hardware the instant the chip returned a non-zero low
byte, which the datasheet explicitly permits. Inherited verbatim from the deployed driver
(`python/IndividualDrivers/asy_sgp40_driver/__init__.py:337`, same `!= 0xD400` check) - not
something this promotion introduced, but caught by finally reading Table 13's exact wording rather
than pattern-matching the deployed code's assumption. Fixed to `(self_test[0] >> 8) != 0xD4`, with a
regression test (`test_initialize_self_test_success_ignores_nonzero_low_byte`) feeding `0xD4FF` and
asserting no raise.

**Minor simplification**: `SGP40_Reader.__init__()` set `self.voc_init = 1` / `self.voc_write = 1`,
but every real code path that reads either attribute only runs after `read_loop()` → `_init_sgp()`,
which unconditionally zeroes both at its very top before any other statement - including on every
supervisor-triggered restart, which re-invokes `read_loop()` on the *same* `SGP40_Reader` instance
(`get_task_starters()` returns a bound `self.start_asy_read`, not a fresh-instance factory - see
`system_service.py`'s `starter()` call). So the `= 1` was dead: always overwritten before ever being
observed. Changed to `= 0` with a comment explaining why, avoiding the implication that either
attribute is meaningfully "armed" pre-init.

**Fixed (was flagged, now resolved on explicit request)**: `measure_raw()` called
`self.crc.add_into(...)` twice (writing the RH-ticks and temperature-ticks CRC bytes into
`self._measure_command`) without checking either call's return value. `add_into()` returns `None`
on failure (buffer too small, invalid init, etc.) - `asy_fram_manager.py`'s own `add_into()` call
site (`if await self.crc.add_into(buf, self.size) is None: ...`) already established checking this
return as the project's convention, and `SGP40_I2C`'s own `_read_word_from_command()` checks
`check_from()`'s return a few lines below in the very same class. In practice this specific call
site can't actually return `None` today - `self._measure_command` is a fixed 8-byte buffer and
`start=2`/`start=5`/`size=2` are hardcoded literals that always satisfy `add_into()`'s internal
bounds check - so this was never a live bug, just an inconsistency in defensive-checking style
within the same file. Fixed locally in `measure_raw()` (both calls now `if ... is None: return
None`), not in `crc_checks.py`/`asy_fram_manager.py` - the inconsistency was this call site's own,
not a defect in either of those shared modules. Regression test: `_AlwaysFailCRC`, a minimal fake
matching `add_into()`'s signature, is substituted in for `sgp.crc` since the real `CRC8()` can't
actually be driven to return `None` through this call site's fixed buffer shape -
`test_measure_raw_add_into_failure_returns_none_not_raise` asserts `measure_raw()` returns `None`
without ever reaching `get_raw()`'s own bus transaction.

**Real bug found and fixed (uncaught-exception audit)**: `_read_sgp()` called `await
self.comp_callback()` unwrapped - the *only* caller-supplied callback in this file not wrapped in
`try`/`except`, unlike every other caller-supplied callback in this codebase (`asy_fram_manager.py`'s
`ntp_sync_callback`, twice; `system_service.py`'s own NTP callback; `base_classes.py`'s config
callback). A full audit of every call in `asy_sgp40_driver.py` (cross-checked against
`base_classes.py`, `config_manager.py`, `asy_fram_manager.py`, `print_log.py` - all independently
confirmed "never raises" by their own module docstrings/promotion audits) found exactly this one
gap: if a real compensation source (e.g. a sibling SHTC3/BMP388 driver's own read call, threaded
through `sensortask-*.py`'s own callback) ever raised, it would propagate uncaught out of
`_read_sgp()` → `read_loop()`, crashing the whole async task instead of being counted through the
normal `_error_check()`/give-up path - the same failure mode every other caller-supplied callback in
this codebase is already deliberately guarded against. Fixed by wrapping the call in `try`/`except
Exception`, logging via `err_s(..., errno=18)` and falling back to `[None, None]` (the same shape
`_read_sgp()` already treats as "no compensation data available"). Regression test:
`test_read_sgp_comp_callback_exception_is_caught_not_propagated`.

**Sensortask-\*.py integration gap was broader than previously documented, and is now partially
fixed on explicit owner request (a one-off exception to the standing "don't edit
`sensortask-wozi.py`" hard rule - confirmed directly, not assumed).** The earlier promotion pass
flagged only `SGP40_Reader.get_default_cfg()` as missing from `sensortask-wozi.py`'s construction
call; re-reading that call in full showed the entire constructor convention was stale, not just one
classmethod. Confirmed this is unambiguously a `sensortask-wozi.py`-side staleness issue, not a
driver bug - the driver's new API (per-sensor config file, internal chunk allocation,
`AsyFramManager`-level error counters) is the deliberate, correct design; the caller just hadn't
been updated to match:

- **Fixed**: `sensortask-wozi.py` called `SGP40_Reader(i2c1, cfgmgr, sgp_comp_callback,
  ts_storage=sgp_backup, max_i2c_err=_MAX_I2C_ERR, debug=debug)` - a positional `cfgmgr` argument the
  current `SensorReaderConfig`-based constructor doesn't take at all (config is now an internal
  `ConfigManager` owned per-reader via `cfg_path`, not an external shared instance passed in), and a
  `ts_storage=` keyword for a pre-built FRAM chunk. Updated to `SGP40_Reader(i2c1, sgp_comp_callback,
  fram_storage=fram, fram_ntp_callback=conn.ntp_issynced, max_i2c_err=_MAX_I2C_ERR, debug=debug)`,
  matching the current constructor exactly; the external `sgp_backup =
  fram.get_timestamped_chunk(SGP40_Reader.get_params_memsize(), conn.ntp_issynced)` call (which also
  referenced a `get_params_memsize()` that no longer exists on `SGP40_Reader` - it's
  `VOCAlgorithm.get_params_memsize()`, called internally by the driver now) was removed entirely, since
  chunk allocation now happens inside `SGP40_Reader.__init__()` itself.
- **Fixed**: `sensortask-wozi.py`'s cfgmgr construction still merged in
  `SGP40_Reader.get_default_cfg()` (line 74), a classmethod that no longer exists - removed from the
  merge, with a comment explaining SGP40 now owns its own `config_SGP40.cfg` instead of contributing
  to the shared `config.json`.
- **Fixed**: `/system/status`'s handler called `sgp_reader.get_mem_error_counters()`, which doesn't
  exist on the current class. Traced to its origin: the deployed driver's `ts_storage` was an
  old-style FRAM chunk object with its own `get_error_counters()` (crit/uncrit/last, per-chunk). The
  refactor replaced that whole per-chunk error-counting mechanism with `asy_fram_manager.py`'s unified
  `AsyFramManager.get_error_counter()` (`self.pr.get_log("FRAM")` - same shape as every other driver's
  own `get_error_counter()`), scoped to the whole FRAM chip rather than per-chunk - a confirmed,
  correct architectural supersession, not a regression to restore in `SGP40_Reader` itself. Replaced
  the three `SGP40_MemErr_Critical`/`SGP40_MemErr_Uncritical`/`SGP40_MemErr_Last` JSON fields (which
  can no longer be computed at all - the underlying per-chunk counters don't exist anymore) with a
  single chip-wide `FRAM_ErrCnt`, sourced from `fram.get_error_counter()["FRAM"]["ErrCount"]`. This is
  a real REST JSON schema change (field removal/rename), forced by the architectural supersession, not
  an optional design choice.
- **Fixed**: `SGP40_Reader.get_error_counter()` now returns a `print_log.py`-shaped dict
  (`{"SGP40": {"ErrCount": ..., "ErrNum": [...], "ErrType": [...]}}`), not a bare int - the
  `SGP40_ErrCnt > 0` comparison in `/system/status` would have compared a dict against an int.
  Extracted `["SGP40"]["ErrCount"]` to keep the endpoint's existing flat-int JSON contract unchanged
  for external consumers. Note: `SCD30_ErrCnt`/`BMP388_ErrCnt` have the exact same
  dict-vs-int-comparison problem already, pre-existing and untouched here (`asy_scd30_driver.py`/
  `asy_bmp3xx_driver.py` in `improved-quality/` already return the same dict shape, but neither driver
  is promoted/in this task's scope) - confirmed via mypy (`Unsupported operand types for < ("int" and
  "dict[...]")`, present in the pre-edit baseline for those two, now also present for `FRAM_ErrCnt`/
  `SGP40_ErrCnt` since `print_log.py`'s `get_log()` return type (`int | list[int] | list[str]`) doesn't
  let mypy narrow `"ErrCount"` specifically to `int` without a `print_log.py`-level `TypedDict`
  change - out of scope here, left as the same accepted baseline pattern.
- `get_mem_status()` (last_backup/restored_from) was already unchanged and still matches the
  deployed driver 1:1 - no fix needed there.
- **Known gap, deliberately deferred (owner-confirmed, not an open question)**:
  `sensortask-wozi.py`'s `setSGP` REST handler validates `SGPBackupPeriod`/`SGPBackupMaxAge`/
  `SGPWaitTimeNTP` and writes them into the *shared* `config.json` via the old `cfgmgr`
  (`async_manager.ConfigManager`, a different class entirely from the driver's own
  `config_manager.ConfigManager`) - but the promoted `SGP40_Reader` reads these three values from
  its own private `config_SGP40.cfg` and exposes no setter for them at all (only `reset_voc`). The
  REST handler validates input and persists it somewhere the sensor never reads - a silent no-op
  against real hardware today. The project owner confirmed this gap was already known (not a
  surprise from this review) and is deliberately not being addressed sensor-by-sensor: per-driver
  config setters are being deferred to a single consolidated pass across every promoted sensor
  once they've all made the `src/` move, rather than adding them piecemeal here for SGP40 alone.
  Left as-is; this note exists so the eventual consolidated pass has the concrete finding on
  record rather than needing to be rediscovered.

The REST config-write gap above remains out of scope for now; the constructor/error-counter fixes
were narrowly targeted at what could be corrected mechanically, with a single, unambiguous right
answer (matching the driver's actual current API), not a broader `sensortask-wozi.py` rewrite -
every sibling reader construction in that file (SCD30/BMP3xx) still uses the old external-`cfgmgr`
convention, untouched, since neither of those drivers is promoted yet.

**Confirmed correct, no action needed**:
- `sgp4x_turn_heater_off` (`0x36 0x15`, datasheet Table 14) is unimplemented. Its documented purpose
  is exiting VOC measurement mode for low-power idle/sleep (Figure 6: *"use only for exiting
  measurement mode, e.g., putting a device into sleep"*) - this driver has no sleep/pause feature
  anywhere (it samples continuously at a fixed 1 Hz for as long as the reader task runs), so there is
  no call site that would ever need it. Not a gap given the current design.
- `WaitTimeNTP=0` disables backup/restore entirely for that boot (since `voc_init`/`voc_write` stay
  at the zero `_init_sgp()` sets them to, and every trigger condition is `> 0`) - confirmed this
  exactly matches the deployed driver's own `if 1 <= wait_ntp <= 600: ...` gate, not a behavior
  change introduced by refactoring the inline logic into separate `_check_storage`/`_run_restore`/
  `_run_backup` methods.
- Structure (4-part split: `SGP40_I2C` protocol class, `SGP40_DeviceSession` lock wrapper,
  `SGP40_Reader` framework-facing class, `VOCAlgorithm` as the algorithmic extension consumed by
  `measure_index_and_raw()`), `SensorReaderConfig`/`Lockable` inheritance (constructor argument
  order and defaults both match `base_classes.py` exactly), and the `get_task_starters()`/
  `get_timer_starters()` contract (`system_service.py`'s exact expected `Callable` shapes) were all
  re-checked and found correct - no further findings.

40 tests now (`tests/test_asy_sgp40_driver.py`, +1 for the self-test byte-check regression) - **814
total**.

#### Third review pass (exception audit, self-test bug origin, sensortask fixes, deep test coverage)

Requested explicitly by the project owner: (1) audit the whole file for uncaught exceptions,
including called functions; (2) trace the self-test byte-check bug's origin; (3) fix the flagged
`add_into()` inconsistency; (4) fix the `sensortask-wozi.py` integration gap; (5) add exhaustive
config-validation tests; (6) add full-stack integration tests (`print_log`/`base_classes`/
`asy_i2c_driver`/FRAM, success and every error type); (7) mock I2C bus success/error per the
datasheet; (8) module- and integration-level fault-propagation tests; (9) an equal-depth separate
test suite for `voc_algorithm.py`.

**Self-test bug origin (item 2)**: confirmed via `python/IndividualDrivers/asy_sgp40_driver/__init__.py:337-338`
(SPDX-tagged "Copyright (c) 2020 Bryan Siepert for Adafruit Industries") - the exact same
`if self_test[0] != 0xD400: raise RuntimeError("Self test failed")` already exists there, with no
comment or reasoning given. A plain oversight on Adafruit's own side (checking the whole word
against one specific value instead of just the documented pass/fail byte), not a deliberate
choice for some specific chip revision - inherited verbatim through this project's deployed driver,
then into the first promotion pass, until this review's Table 13 re-read caught it.

**Uncaught-exception audit (item 1)** across the whole file, cross-checking every called function's
own "never raises" contract (`base_classes.py`, `config_manager.py`, `asy_fram_manager.py`,
`print_log.py`, `voc_algorithm.py` - all independently confirmed by their own module docstrings/
promotion audits) and every `SGP40_I2C` call site from `SGP40_Reader` (both already wrapped in
`try`/`except Exception`, per the module docstring's own documented contract): found exactly one
gap, the unwrapped `comp_callback()` call (see above, now fixed) - no other uncaught-exception path
found.

**Items 3 and 4** (the `add_into()` fix and the `sensortask-wozi.py` integration fixes) are recorded
in full detail above, inline with the findings they extend.

**Items 5-9 (test coverage)** added across `tests/test_asy_sgp40_driver.py` and
`tests/test_voc_algorithm.py`:
- Config schema: every field's documented bounds/defaults, valid boundary values (min and max for
  all three fields simultaneously), a typical custom combination, single-field-invalid for each of
  the three fields independently, two-fields-invalid and all-three-invalid recombinations, wrong-type
  values, missing keys, and confirming `_init_sgp()` actually threads a valid custom `WaitTimeNTP`
  into `voc_init`/`voc_write` (not just that `get_dict_cfg()` reports it). Each test uses its own
  per-test config subdirectory (`_sgp_cfg_dir()`), not the shared `_tmp_path("")` every other test in
  the file uses, since those never write custom values - only these do, and a shared file would let
  one test's config bleed into another's.
- Full-stack integration: confirmed `SGP40_Reader.pr` is a real `PrintLogHistoryStore` when
  `fram_storage` is given, and that its error log survives a simulated reboot (a second
  `AsyFramManager` sharing the same underlying `FakeMB85RS64V` chip, replaying the identical
  allocation-call sequence) - the same "reboot" pattern this file's existing VOC-state FRAM tests
  already used, now also covering the *other* FRAM chunk this driver allocates (`pr`'s own error log,
  allocated first in construction order, ahead of `ts_storage`'s VOC-state chunk).
- I2C mocking/fault propagation: a real NAK (`fake_bus.nak_addresses.add(0x59)`, not a
  hand-constructed exception) during a measurement is caught by `_read_sgp()`'s own
  `try`/`except Exception` and counted through the normal error path - proven both at the single-call
  level and end-to-end through `read_loop()`'s give-up-after-`max_i2c_err` logic, mirroring the
  existing CRC-mismatch-based give-up test but for a real bus-level `OSError` instead of a
  hand-corrupted `RuntimeError`, since these are genuinely different fault shapes reaching the same
  `except Exception` catch. This directly proves `SGP40_I2C`'s documented "OSError allowed to
  propagate" carve-out (`src/README.md` section 2) is actually absorbed correctly by
  `SGP40_Reader`, not just asserted in a comment.
- `voc_algorithm.py`'s own dedicated integration suite (previously only exercised coupled to a full
  sensor read cycle via `asy_sgp40_driver.py`'s tests): a real `AsyFramManager` +
  `FakeMB85RS64V`-backed round trip of `pack_into()`/`unpack_from()` across a simulated reboot,
  independent of the sensor driver entirely; a hard-failure case (both redundant on-chip copies
  corrupted, matching `tests/test_asy_fram_manager.py`'s own
  `test_read_fails_when_both_blocks_have_crc_invalid_payloads` idiom) proving `read_into()` returning
  `False` never touches the live algorithm's state at all (`unpack_from()` never gets called, mirroring
  `asy_sgp40_driver.py`'s own `_run_restore()` short-circuit, now proven directly at the algorithm
  level too); and a single-copy-corruption self-heal case confirming the dual-copy redundancy still
  recovers the *exact* original state, not just "read succeeded".

Full suite: **835 tests, all passing** (`asy_sgp40_driver.py` 40→58, `voc_algorithm.py` 22→25 - see
"Current test counts" below for the per-file breakdown).

#### Fourth review pass (line-by-line re-read for oversights/dead code/untested conditions)

Requested explicitly: go through both `asy_sgp40_driver.py` and `voc_algorithm.py` again in detail
for oversights, bugs, strange/unexpected behavior, and unhandled/unplanned/accidental exceptions or
conditions with no unit test yet - independent of the earlier passes' own findings. Nothing here
was silently changed; every item below is either a new regression test locking in already-correct-
but-untested behavior, or a flagged behavioral question left for the project owner to decide (see
"Flagged, not changed" below).

**Confirmed real, previously untested conditions (now covered by new tests, no behavior change)**:
- `_run_backup()`'s genuine-FRAM-write-failure branch (`"Schreibfehler beim Backup!"`, errno=13,
  distinct from the already-tested "no NTP yet" deferral) had zero coverage. New test forces a real
  write failure via `manager.set_pause(True)` (the same clean-`False`-without-touching-the-chip
  shape a genuine hardware fault takes) and confirms it's logged and `last_backup` stays `None`.
- Both `_run_restore()`'s and `_run_backup()`'s "wait-time-NTP budget exhausted, act anyway" escape
  hatches were untested. `_run_restore()`: once `voc_init`'s countdown reaches 0 while NTP still
  hasn't synced, a valid-but-ageless backup is restored anyway *without* ever checking
  `BackupMaxAge` (recovering a possibly-unverifiable-age baseline rather than losing it). `_run_backup()`:
  the symmetric case - once `voc_write`'s countdown reaches 0, the backup is written anyway without
  a real timestamp (`last_backup` ends up `0`, the documented "backup exists, no TS" sentinel, not
  `None`). The existing `test_fram_backup_without_ntp_sync_is_deferred_not_lost` only covered the
  "still waiting" branch of the second case, never the "budget exhausted" branch of either.
- `_check_storage()`'s `backup_counter >= 100000` wraparound guard was unreachable in every previous
  test - it turns out to only ever matter when `BackupPeriod` is disabled (`0`), since any nonzero
  period's own periodic-trigger reset already fires long before 100000 (max `60*1440 = 86400` for
  the field's own valid range). New test disables `BackupPeriod`, pre-sets `backup_counter=99999`,
  and confirms it wraps to `0` rather than being left to grow unbounded.
- `_init_sgp()`'s `set_verify()` call was never checked against its actual computed value (only
  that `_init_sgp()` succeeds) - new test confirms `ts_storage.get_verify()` matches the documented
  `ceil(600/BackupPeriod)*0.1` formula for a real, non-default `BackupPeriod`.
- **A genuinely reachable, previously unexercised interaction**: `_check_storage()` can
  independently set both `serialize` and `deserialize` `True` in the *same* cycle (a restore still
  pending, `voc_init > 0`, coinciding with the periodic backup period elapsing). Both then operate
  on the *same* buffer: `_run_restore()` reads the old state into it, `vocalgorithm_proc_ser_des()`
  unpacks it, processes one new sample, and re-packs the *updated* state back into that same
  buffer, which `_run_backup()` then persists - restore and backup coherently compose in one pass.
  No existing test ever triggered both at once. New test constructs this exact coincidence and
  confirms the whole chain (restore succeeds, re-serialize succeeds, the resulting state reflects
  the restored-then-processed uptime) - this test itself initially had a bug of its own (see next
  paragraph), caught and fixed before landing.
- **NaN/Inf compensation data**: confirmed directly against the real interpreter that
  `_celsius_to_ticks()`/`_relative_humidity_to_ticks()` call `int()` on the caller-supplied
  compensation value with no validation beyond "not `None`" - `float('nan')` raises `ValueError`,
  `float('inf')`/`float('-inf')` raise `OverflowError`. Already structurally safe (both calls happen
  inside `_read_sgp()`'s own wrapping `try`/`except Exception`, counted as a normal read error, not
  propagated), but had zero test coverage for either case until now.
- `voc_algorithm.py`: MicroPython's `struct.pack_into()`/`unpack_from()` raise `ValueError` for a
  negative `offset` - confirmed directly against the real interpreter this is a genuine
  MicroPython-vs-CPython difference (CPython's `struct` treats a negative offset as relative to the
  buffer's end; MicroPython's doesn't support that convention at all). Already safe (both call
  sites are wrapped in `try`/`except Exception: return False`), but untested; no real caller in this
  codebase ever passes a negative offset today.
- `voc_algorithm.py`'s `_vocalgorithm_set_tuning_parameters()` has *zero* callers anywhere in this
  codebase (`asy_sgp40_driver.py` only ever calls `vocalgorithm_init()`/`vocalgorithm_reset()`; only
  `_vocalgorithm_get_states()`/`_vocalgorithm_set_states()` - Sensirion's own short-interruption API
  - are used, and only by tests exercising that path directly) and had zero test coverage at all.
  Kept as documented, Sensirion-mirroring dead API surface; added a smoke test confirming it
  threads values through correctly and doesn't leave the algorithm unusable, since "untested" and
  "safe" aren't the same claim and this had neither established before now.

**Confirmed harmless, not fixed (dead/vestigial code, noted for the record)**:
- `measure_index_and_raw()`'s `if raw is None or raw < 0:` guard - `raw < 0` can never actually be
  true given the current implementation (`get_raw()` returns either `None` or an unsigned 16-bit
  value from `unpack_from(">H", ...)`, never negative). Vestigial from the old Adafruit-style
  convention of returning `-1` as a sentinel for "read failed" (this driver uses `None` instead,
  which the `is None` half of the check already fully covers). Harmless dead condition, not touched.

**Fixed, per explicit owner direction** (originally flagged, not changed - now resolved): the
`self.reset` behavior above was redesigned rather than left as a documented quirk. Owner's
direction, verbatim in spirit: never drop a reset, don't need to redo the whole thing every time,
never give up retrying, every path leads to defined and clear behavior. Reset now tracks its two
independent sub-parts separately - `self._reset_fram_cleared` (has `ts_storage.clear()` succeeded
for this request) and `self._reset_algo_applied` (has `vocalgorithm_reset()` actually been applied
for this request) - both initialized `True` (nothing pending) and reset to `False` together by
`reset_voc(True)`, so a fresh explicit request always restarts full tracking rather than silently
riding on a previous request's stale bookkeeping.

`_read_sgp()` now only attempts whichever sub-part hasn't yet succeeded: the FRAM clear is skipped
once `_reset_fram_cleared` is `True` (no more redundant FRAM writes while only the algorithm side is
still blocked, e.g. on missing compensation data), and `vocalgorithm_reset()` is only actually
invoked (`reset=True` passed into `measure_index_and_raw()`) while `_reset_algo_applied` is still
`False` - the moment that call is issued, `_reset_algo_applied` is set `True` immediately, since
`vocalgorithm_reset()` runs unconditionally before `measure_raw()`'s I2C transaction and never
raises (`voc_algorithm.py`'s own contract), so it's guaranteed applied regardless of whether the
I2C measurement that follows then succeeds or fails. `self.reset` only clears to `False` once both
sub-parts are confirmed `True` in the same cycle - on both the success path and the exception path,
since the software half can complete even when the hardware measurement that follows it fails.

`reset_now = self.reset` is snapshotted once at the top of `_read_sgp()`, so a concurrent
`reset_voc()` call from another task (a REST handler) only ever affects the *next* cycle's own
snapshot - this cycle's own completion accounting can't be corrupted by a mid-cycle request from
elsewhere, matching this driver's existing single-owning-task model (see the atomicity/locking
answer this same conversation turn covered for `ts_storage`/`_voc_algorithm`, which this reset
logic doesn't add any new concurrency risk on top of).

The old test documenting "current, not endorsed" behavior
(`test_reset_flag_persists_across_a_failed_read_and_repeats_the_reset_sequence`) no longer applies
and was replaced by two tests proving the new contract directly:
`test_reset_never_drops_but_each_sub_part_completes_at_most_once` (FRAM succeeds first, while
algorithm-reset is still pending on missing compensation data; pauses FRAM storage afterward to
prove a correct implementation would *not* need to touch it again) and
`test_reset_retries_only_the_fram_half_once_the_algo_half_already_succeeded` (the mirror case -
algorithm-reset succeeds first, FRAM clear kept failing via `set_pause(True)` across multiple
cycles, `vocalgorithm_process()`'s own `muptime` counter used as an independent proof that
`vocalgorithm_reset()` was never re-applied on a later cycle).

Full suite: **848 tests, all passing** (`asy_sgp40_driver.py` 58→68, `voc_algorithm.py` 25→28 - net
+1 vs. the previous +9/+3 count, since one old test was replaced by two new ones).

#### Fifth review pass (full `src/README.md` checklist re-validation, owner-requested)

Went section-by-section through `src/README.md`'s production-quality checklist against both files
again, re-checking claims directly against the actual SGP40 datasheet PDF, current MicroPython docs
(fetched live, not from training memory), and the RP2040/Pico W target - not re-deriving prior
passes' already-closed findings.

**Fixed (trivial, zero behavior change, confirmed via existing tests)**:
- `_read_word_from_command()` checked `crc.check_from()`'s `int | None` return with a bare
  `if not await ...`, while `measure_raw()` checks the same `add_into()` contract with `is None` -
  an API-consistency mismatch within the same file (section 10). No live bug (`check_from`'s success
  value here is always `2`, never `0`, so falsy-checking never misfired), but `is None` is the
  file's own established, more defensive convention for this exact `int | None` shape. Fixed;
  `test_initialize_corrupted_response_raises_crc_error`/`test_get_raw_crc_mismatch_raises` already
  exercise the real-failure path and still pass unchanged.

**New cross-checks confirming existing code, nothing to change**:
- `asyncio.ThreadSafeFlag` (`self.trigger_event`) usage checked against current MicroPython
  asyncio docs: "only one task may wait on the flag," set-able from ISR/async context. Exactly one
  waiter (`read_loop()`), exactly one setter (the timer callback) - matches the documented contract.
- `machine.Timer` (`self.trigger_timer`, RP2 port) checked against current docs: callbacks run as
  **soft IRQ by default** (not hard) unless `hard=True` is passed. This driver doesn't pass it, so
  the callback (`lambda b: self.trigger_event.set()`) runs in the less-restrictive soft-IRQ context,
  free of hard-IRQ's no-heap-allocation constraint - already safe as written, no change needed.
- MicroPython 1.27.0/1.28.0 release notes (the version between the code's older history and the
  refactor's current `toolchain/versions.toml` pin) checked for anything touching `asyncio`,
  `struct`, or `machine.I2C`: nothing relevant surfaced (1.27/1.28 additions are ESP32-C5/P4,
  STM32U5, `machine.CAN`, PEP 750 t-strings - none touch this file's dependencies).
- CRC-8 algorithm (`crc_checks.py`'s `CRC8`, poly `0x31`/init `0xFF`) re-checked against the
  datasheet's own Table 7 C reference and worked example (`CRC(0xBEEF) = 0x92`) - `test_crc8_
  helper_matches_datasheet_example` already covers this; still matches.
- Considered, declined as unnecessary complexity: reusing `_read_word_from_command()`'s
  per-call `readdata_buffer`/`replybuffer` allocations (a 3-9 byte bytearray + list, once per
  second) the way `_command_buffer`/`_measure_command` already do. Negligible cost on a 264KB-SRAM
  target at 1Hz: not worth the added complexity for a fixed/degenerate buffer shape across three
  different call sites (`get_raw()`'s `readlen=1`, self-test's `readlen=1`, serial-number's
  `readlen=3`).

**Fixed, per explicit owner direction** (originally flagged, not changed - now resolved):
- `SGP40_I2C._celsius_to_ticks()`/`_relative_humidity_to_ticks()` (datasheet Table 10) rounded
  differently from each other: humidity rounds to nearest (`int(x + 0.5)`), temperature truncated
  toward zero (`int(x)`) - inherited unchanged from the legacy/Adafruit driver, present identically
  in both. All three of the datasheet's own worked examples (25°C→0x6666, -45°C→0x0000,
  130°C→0xFFFF, 50%→0x8000, 0%→0x0000, 100%→0xFFFF) happen to divide evenly, so this asymmetry
  never showed up in the exact-example check already recorded above ("Confirmed correct, not
  changed, after checking"). The datasheet's Table 10 formula doesn't itself mandate a rounding
  convention, so this was never "wrong vs. the datasheet," but round-to-nearest is the more
  reasonable/accurate choice of the two (minimizes conversion error vs. truncation's systematic
  downward bias) - owner's direction: pick the more reasonable variant and make both consistent.
  `_celsius_to_ticks()` now rounds to nearest too (`int(x + 0.5)`, matching
  `_relative_humidity_to_ticks()` exactly); new regression test
  `test_celsius_to_ticks_rounds_to_nearest_not_truncates` (24°C, where truncation and rounding
  disagree by 1 tick: 25839 vs. 25840) proves it. All three datasheet worked examples still pass
  unchanged (they divide evenly, so rounding doesn't move them).

#### Sixth review pass (documentation trimmed to `src/README.md` section 11's 3-line cap, owner-requested)

Both files' module docstrings and several per-function `#` comment blocks had grown past section
11's "module docstring is a short header... per-function/inline comments stay within 3 lines,
prefer fewer" rule (same trim `config_manager.py` already went through) - pure documentation
trim, zero behavior change, confirmed via `ruff check` (clean), `mypy` (same single pre-existing
`Timer()` `call-overload` finding, unchanged), and the full existing test suites (69/69, 28/28,
unchanged pass/fail set).

- `asy_sgp40_driver.py`'s module docstring: 16 lines → 10, dropping the itemized datasheet-table
  cross-reference list (I2C address, CRC-8 poly/init, Table 8/10/17 - all still verifiable in the
  code's own per-function comments and this file's earlier review-pass write-ups above) and
  folding the three-paragraph structure into two.
- `voc_algorithm.py`'s module docstring: 17 lines → 7, dropping the standalone paragraph
  contrasting `vocalgorithm_proc_ser_des()`'s full-state FRAM pack/unpack against Sensirion's own
  short-interruption-only `VocAlgorithm_get_states()`/`set_states()` API (freezing every field,
  including the `uptime_gamma`/`uptime_gating` learning-progress counters, keeps resumed state
  internally consistent regardless of gap length; restore-age gating is `asy_sgp40_driver.py`'s
  own `BackupMaxAge` config's job, not this file's) - the design rationale itself isn't lost, just
  moved here instead of restated in the file.
- Six over-limit comment blocks in `asy_sgp40_driver.py`, trimmed to ≤3 lines each, full original
  wording preserved here instead of in the file:
  - `SGP40_Reader.__init__`'s reset sub-completion tracking (4→2 lines): a pending reset has two
    independent parts - clearing the FRAM backup and applying `vocalgorithm_reset()` - which can
    complete on different cycles (e.g. FRAM clear fails once but the software reset already
    succeeded); both start "done" until `reset_voc(True)` marks them pending.
  - `_read_sgp()`'s `reset_now` snapshot (5→2 lines): a pending reset's two parts are tracked via
    `_reset_fram_cleared`/`_reset_algo_applied` so a transient fault in one retries only that part,
    never redoing an already-succeeded one; `reset_now` is snapshotted once at entry so a
    concurrent `reset_voc(True)` from another task (e.g. a REST handler) only ever affects the
    *next* cycle's own snapshot, never this one's.
  - `_read_sgp()`'s `reset_for_measure` comment (5→2 lines): the software reset is applied at most
    once per pending request, even if the FRAM half is still incomplete - `vocalgorithm_reset()`
    runs unconditionally, before `measure_raw()`'s I2C transaction, and never raises, so the moment
    `reset=True` is decided, that half is guaranteed applied regardless of whether the I2C
    measurement that follows then succeeds or fails.
  - `initialize()`'s intro comment (6→2 lines): only the serial-number read and self-test (both
    real, datasheet-documented commands, Table 8) gate success - the previous feature-set check
    (command 0x202F) isn't in the datasheet's command table, isn't done by Sensirion's own or
    DFRobot's reference drivers, and has a known real-hardware unreliability report upstream;
    dropped rather than kept as a spurious extra failure mode on the restart-after-disturbance
    path.
  - `initialize()`'s self-test byte-check comment (4→2 lines): datasheet Table 13 documents only
    the high byte as the pass/fail marker (0xD4 pass, 0x4B fail) - the low byte is explicitly
    documented as "ignore", not guaranteed zero; checking the full word against 0xD400 (inherited
    from the deployed driver) would spuriously fail whenever real hardware returns a non-zero low
    byte, which the datasheet allows.
  - `_reset()`'s general-call comment (4→2 lines): a true I2C general-call reset (datasheet
    Table 17) is a single data byte 0x06 sent to the reserved general-call address 0x00,
    broadcasting a reset to every device on the bus that supports it - not a command sent to the
    SGP40's own address; not every device needs to ACK a general call, so a NAK (`OSError`) here is
    expected, not a real failure.
- Two comment blocks already exactly at the 3-line cap were shortened further for consistency
  (the `comp_callback()` try-comment and the `_read_sgp()` exception-path comment), same
  zero-behavior-change treatment; a handful of other exactly-3-line blocks (the reset_voc()
  restart-tracking comment, the serial-number-zero comment, the measure_index_and_raw() VOC-index
  comment) were left as-is since they were already within the cap.
- `voc_algorithm.py` had no per-function comment blocks past the cap to begin with (the file's
  fixed-point port functions are largely uncommented, following the C reference 1:1 - only the
  `DFRobot_vocalgorithmParams` class-level comment existed, already at 2 lines).

### Coverage-driven completeness pass

Used `scripts/test.sh --coverage`'s line-level miss report to close real gaps: `print_log.py`
89%→90%, `config_manager.py` 99%→100%, `base_classes.py` 97%→100% (remaining misses in all three
confirmed as `micropython.const()`-folding and `@staticmethod`/decorator-line tracer artifacts —
see `tests/README.md`'s "Reading the numbers", not untested behavior). New cross-file integration
tests added in `tests/test_base_classes.py` (where `SensorReaderConfig` wires `config_manager.py` +
`print_log.py` together for real, no mocking of either): FRAM-backed logging with a real config
file, a corrupted config file repairing cleanly under a FRAM-backed logger, FRAM allocation failure
and a missing config file failing independently without either derailing the other.

### Current test counts (verify via `grep -c '^def test_' tests/test_*.py` if this looks stale)

`math_helpers.py` 45, `crc_checks.py` 66, `asy_i2c_driver.py` 77, `asy_spi_driver.py` 43,
`base_classes.py` 70, `config_manager.py` 140, `print_log.py` 46, `asy_fram_driver.py` 46,
`asy_fram_manager.py` 89, `test_fram_integration.py` 10, `system_service.py` 58,
`asy_udp_socket.py` 62, `asy_sgp40_driver.py` 69, `voc_algorithm.py` 28 — **849 total** (a "868"
total was caught and corrected as stale/arithmetically-wrong during the fifth review pass above -
the per-file counts listed here summed to 848 at that point, not 868; a live `scripts/test.sh` run
confirmed 848/848 passing, 0 failures, matching `grep -c '^def test_' tests/test_*.py`'s own count
exactly). (Previous count of 690 across 11 files predated `asy_udp_socket.py`'s promotion and was
never updated to include it — corrected during its third pass; the 23→42 jump was its fourth pass's
uncaught-exception/configuration/integration test additions; 42→56 is its fifth pass's
mutation-bypass/concurrency/cancellation-safety tests; 56→62 is its sixth pass's
ready()/write_and_recvfrom() parameter-guard tests. 752→849 is `asy_sgp40_driver.py`'s +
`voc_algorithm.py`'s entire promotion plus every subsequent review pass's test additions — see
that file pair's own `src/` promotion section above for the full per-pass breakdown, not restated
here.)

## Decided for the refactor

- `modules/_boot.py`'s `import sensortask.py` (open question #1) addressed during the refactor,
  not before — stays as-is on deployed units until then.
- Refactor targets the most recent *stable* releases (MicroPython, pico-sdk, picotool, Microdot) as
  of whenever it's actually done, and should actively adopt relevant new features, not just
  reproduce 1.26-era behavior under newer version numbers. Re-verify current docs at that time.
- Adafruit-derived driver code is fair game for the refactor to restructure/rewrite (keeping
  attribution) — unlike `microdot.py`, which stays hands-off/vendored.
- Config-schema data-loss risk (open question #8) is a non-issue in the refactor by design — the
  refactor's per-sensor config model structurally avoids the "one missing key wipes everything"
  failure mode. Not being patched on the current global-JSON codebase.
- Event-loop blocking convention (see CLAUDE.md hard rules) is now standing for all new code, not
  just the original NTP/Neopixel case.
- Neopixel warning-flash sequencing and the task-supervisor error-budget counter are both
  behaviorally correct and intentional as designed, but flagged by owner as implementable more
  efficiently — worth a cleaner implementation in the refactor without changing observed behavior.
- **Standing scope convention for exception-handling audits**: wrapping every `asyncio` primitive
  call (`asyncio.sleep()`, `Lock.acquire()`, etc.) in `try`/`except` against a theoretical internal
  `MemoryError` is overkill and outside good code standard as a blanket policy — don't chase this
  class of issue project-wide. Only worth closing when a concrete, non-hypothetical threat exists in
  a specific context (e.g. a real caller-supplied value reaching an unguarded comparison/construct,
  as the `asy_udp_socket.py` sixth pass's two actual fixes were), not just "any `await` could
  theoretically raise." Confirmed by owner directly, prompted by `asy_udp_socket.py`'s open question
  #14 (see below).
- **Per-driver REST config setters (e.g. `SGP40_Reader`'s missing `BackupPeriod`/`BackupMaxAge`/
  `WaitTimeNTP` setters, currently a silent no-op via `sensortask-wozi.py`'s `setSGP` handler
  writing to a config file the driver never reads - see "Sensortask-\*.py integration" above) are
  a known, owner-confirmed gap, deliberately not being closed sensor-by-sensor.** Addressed in one
  consolidated pass across every promoted sensor once they've all made the `src/` move, not
  piecemeal per driver as each one is promoted.
- **Mypy shall be configured to not accept `Any` types** (owner-specified). The closest existing
  mypy option is `disallow_any_explicit` (flags explicit `Any` annotations); `[tool.mypy]` in
  `pyproject.toml` currently deliberately stops short of it and the other `--strict`-only checks
  (`disallow_any_generics`, `disallow_untyped_calls`, `disallow_subclassing_any` — see that
  section's own comment). Not yet implemented — noted here as a decision, not done. **Blast radius
  check before flipping it**: as of the `asy_udp_socket.py` sixth pass, `Any` appears ~29 times
  across `src/` and in all 12 `tests/test_*.py` files (20 of those in `tests/test_asy_udp_socket.py`
  alone) — almost entirely in test-file monkeypatch/wrapper classes that duck-type a real
  MicroPython object (e.g. `_MemoryErrorSocketWrapper.__getattr__(self, name: str) -> "Any"`,
  `*a: "Any", **k: "Any"` passthrough signatures) rather than reimplementing its full interface.
  Turning this on will surface real findings across most/all of `tests/`, not just a couple of
  files — likely needs a real typing strategy for these wrappers (e.g. `Protocol` classes matching
  just the methods each wrapper actually overrides, plus `__getattr__` delegation) worked out
  first, not just a mechanical flag flip.

## Functional clarifications (confirmed by owner, not obvious from code alone)

- wozi's SCD30 `AmbPres` is intentionally static even with a live BMP388 present — SCD30 stores
  ambient-pressure compensation as a one-time-set value in its own NVM, not a live-tracked input.
- Air-quality warning LED sequencing (one color per condition, paused between flashes rather than
  combined) is exactly as intended.
- FRAM SGP40 backup "0 = disabled" semantics are intended (`SGPBackupPeriod=0` disables periodic
  backup, `SGPBackupMaxAge=0` disables staleness check) — currently undocumented user-facing.
- Permanent WiFi deactivation after a second STA failure streak (post-hotspot) is a deliberate
  safety feature (prevents an unclaimed hotspot staying open indefinitely) — physical power-cycle
  is the accepted recovery path.
- SCD30 `ForceCalRef` has a real field maintenance procedure behind it, confirmed to exist but not
  yet captured (see open question #12).
- The web UI intentionally shows raw sensor numbers only, no color-coding — the physical LED is
  the sufficient at-a-glance indicator.
- FRAM's 8KB allocation vs. SGP40's 248-byte current usage has plenty of headroom for future
  FRAM-backed features.
- SGP40 silently falling back to uncompensated VOC readings when SCD30 is down/stale, with no
  distinct "degraded" signal, is acceptable as-is — SCD30's own error counter already surfaces the
  cause.

## Open questions (need owner input or further investigation)

1. `modules/_boot.py`'s `import sensortask.py` (literal `.py`) — works reliably on real hardware,
   but MicroPython's documented freeze/import behavior says it should raise `ModuleNotFoundError`.
   Mechanism genuinely unresolved. **Do not "fix" without testing on real hardware first.**
   Addressed during the refactor, not before.
8. Config-schema migration is a real data-loss risk on the *current deployed* codebase —
   `ConfigManager` overwrites the entire config file with hardcoded defaults the moment one key is
   missing, so a firmware update adding a config key could silently wipe WiFi credentials/tuned
   values. **Decided: not patched on the current codebase** — accepted (reconfigure via web UI
   after a key-adding update). The refactor avoids this class of bug structurally (see "Decided
   for the refactor").
11. MicroPython version target vs. upstream drift — deployed units run 1.26; upstream stable is
    1.28.0 as of the last check. **Decided**: deployed code stays pinned to 1.26 until a deliberate
    reflash campaign; the refactor is where the version target moves forward. 1.27→1.28 rp2-port
    changes checked so far look RP2350-specific, not RP2040-breaking, but not exhaustively checked
    against every module — re-check whenever the refactor picks a landing version.
12. SCD30 `ForceCalRef` field procedure isn't written down anywhere — a real maintenance routine
    exists (see Functional Clarifications) but the actual steps (reference concentration, exposure
    conditions/timing, frequency) still need capturing from the owner.
13. Does `config_manager.py`'s `write_config()` need `get_long_block_lock()` coordination? Its
    `open()`+`json.dump()` has no yield point, same shape `__init__`'s read path had before the
    cache-elimination redesign closed *that* concern. Whether a real RP2040 littlefs write of a
    small config file is fast enough not to matter is a hardware-timing question this dev
    environment can't verify — needs either a real-hardware measurement or an owner call on wiring
    it in proactively.
*(Questions #2–7, #9, #10 were resolved during earlier sessions — SGP40 FRAM backup semantics,
no external schematics exist, arzi/neu's static `AmbPres` is accepted, Adafruit-derived code is
refactor-fair-game, `get_long_block_lock()` is now a general convention, `neu` reusing arzi's HTML
is fine, the hardcoded fallback-hotspot password risk is accepted for now, and `.gitignore` now
exists — see git history if the original reasoning is needed. Question #14 — `asy_udp_socket.py`'s
`_connect()`/`disconnect()` calling bare `asyncio.sleep()`/`Lock.acquire()` with no `try`/`except` of
their own — was resolved the same session it was raised: **decided not worth closing.** Wrapping
every `asyncio` primitive call in `try`/`except` against a theoretical internal `MemoryError` is
overkill and outside good practice as a blanket policy; not pursued further unless a concrete,
non-hypothetical threat in a specific context justifies it. Accepted as residual risk.)*

## Deferred / explicitly out-of-scope work

- **HTML/frontend automation & consistency** — known hand-written/brittle, not a priority; revisit
  after the Python-side refactor.
- **UART sensor integration** (`asy_uart.py`/`asy_uart_comm.py`, unused by any deployed config) —
  after the refactor of already-deployed features, not before.
- **Config-duplication centralization** (same keys hand-kept in sync across `_DEFAULT_CONFIG`, the
  REST handler, and the HTML form) — owned by the refactor, not the current codebase.
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an uninstantiated object) —
  bench rig only, not bugs to fix.
- **Unit tests against the current (pre-refactor) codebase** — not written; understand the system,
  confirm what's transferred to `improved-quality/`, write tests as part of the refactor.
- **Dev/build environment setup**: toolchain installer **done**
  (`toolchain/setup_toolchain.py`, see `toolchain/README.md`) — clones/builds a matching
  MicroPython + pico-sdk + picotool + ARM cross-compiler from scratch, updates in place. Verified
  from a genuinely clean Ubuntu 24.04 `debootstrap` chroot (no preinstalled build tools/`uv`/apt
  cache beyond `main`) for both the latest release and the deployed `v1.26.1` pin, including the
  update path and `--clean`. Hardened against ambient-environment interference: every subprocess
  gets an explicitly constructed environment (fixed `PATH` + small allowlist for compile steps;
  same + explicit proxy/CA passthrough for `git`/`apt-get`/`make submodules`) — verified
  adversarially (fake `cmake`/`gcc`/`picotool` ahead in `PATH`, garbage env vars) and against a
  locale gap (`LANG`/`LC_ALL` were being passed through, which could silently defeat the
  English-`error:`-grep failure detection via translated GCC/binutils diagnostics — fixed by
  forcing `C.UTF-8`). **Still not done**: doesn't yet genericize `build-*.sh`'s hardcoded
  `/home/nico/rpi_pico/...` path or the `py-include` symlink — that's the next step, now a real
  near-term prerequisite for the firmware-build CI stage. `update_and_install.txt` re-verified
  against current upstream docs — structurally still accurate, but missing the pico-sdk 2.0.0+
  picotool major.minor version-matching requirement (already applies today: MicroPython 1.26
  bundles pico-sdk 2.1.1) and the full apt package list (never listed at all, presumably assumed
  pre-installed). An official one-shot alternative exists
  ([`raspberrypi/pico-setup`](https://github.com/raspberrypi/pico-setup)'s `pico_setup.sh`), worth
  considering as a base.
- **CI cache-key bug found and fixed**: `.github/workflows/ci.yml`'s `unit-tests` job originally
  cached `~/pico-toolchain` keyed only on `toolchain/versions.toml`, missing that
  `build_unix_port()`'s own build flags (e.g. `MICROPY_PY_SYS_SETTRACE=1`) live in
  `toolchain/setup_toolchain.py` — a stale cached binary survived across commits that changed only
  the latter, surfacing as `scripts/test.sh --coverage` failing in CI (`"module 'sys' has no
  attribute 'settrace'"`) while passing locally. Fixed by hashing both files into the cache key —
  see `toolchain/README.md`'s "CI perspective".
- **No end-user reference for Neopixel LED colors/patterns exists** — confirmed intentional
  single-LED dual-duty design, but no legend anywhere. Worth adding, low priority.
- **FRAM SGP40 "0 = disabled" semantics need user-facing documentation** (see Functional
  Clarifications).

## Security notes

- The one real credential in this repo is the hardcoded hotspot fallback password (open question
  #9, accepted risk — only exploitable by someone in physical WiFi range of a unit that's already
  lost its real WiFi), present in both `python/CommonDrivers/async_connect.py` and
  `improved-quality/async_connect.py`.
