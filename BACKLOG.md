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
    generalize only if a mechanism turns out to be genuinely common. *(Only `asy_scd30_driver.py`'s
    reset path reviewed so far — SGP40's `_reset()` and BMP3xx's reset command still need the same
    review.)*
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
`api_helpers.py`/`async_connect.py`/`captive_dns.py`/`asy_udp_socket.py` fixes for `None`-guard
crash paths and an unbound-local variable.

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
`asy_fram_manager.py` 89, `test_fram_integration.py` 10, `system_service.py` 49 — **681 total**.

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
exists — see git history if the original reasoning is needed.)*

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
