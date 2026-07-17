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
    (calling the new `verify_present()`) and task-death-and-respawn wiring both live in
    `asy_fram_manager.py`/a task supervisor, neither promoted yet.
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
the same backing, replaying the same `get_chunk()` sequence, to prove persistence). **Remove
`tests/_fram_mock.py` once `asy_fram_manager.py` itself clears `src/` promotion.**

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
(the one abbreviation in an otherwise fully-spelled-out file) — **note: `pyproject.toml`'s own
mypy-override comment still uses the old name, missed by this rename.**

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
**Found, not touched** (both `improved-quality/` source, out of routine-editing scope): the
identical shape in `improved-quality/asy_fram_manager.py`'s `bytearray([_STATUS_UNINIT] * (self.size
+ ...))` (bounded by real hardware capacity at every call site — dev-time-literal, not a live attack
surface) and dead code carrying the pre-fix version in unused `base_classes_old.py`.

### `asy_fram_driver.py` → `src/`

Driver for the actual FRAM chip (Fujitsu MB85RS64V, Adafruit's 8KB SPI FRAM breakout) sitting under
`asy_fram_manager.py` (not itself promoted yet - see above). Verified against the real datasheet
(DS501-00015) and cross-checked against Adafruit's own `Adafruit_FRAM_SPI` reference driver for the
same chip, per owner request to specifically check hardware-interaction correctness and
bus-disturbance recovery, not just style.

**Real bug found and fixed, with a live production caller**: `setup()`'s RDID device-identification
check had two compounding bugs, present since the legacy driver (not introduced by any promotion).
The datasheet's RDID response order is Manufacturer ID / continuation code / Product ID 1st byte
(more significant) / Product ID 2nd byte - confirmed as `0x04, 0x7F, 0x03, 0x02` for this chip from
two independent sources (the datasheet text and Adafruit's own driver's `getDeviceID()` byte
handling). The old code computed `prod_id = (read_buffer[3] << 8) + read_buffer[2]` - the two
product-ID bytes swapped - so `prod_id` could never actually equal `_SPI_PROD_ID` (0x0302) against
real hardware. That alone would have made every `setup()` call fail - except the surrounding
check was `if (manf_id_wrong) and (prod_id_wrong): raise`, using `and` where it should have used
`or`. Since the manufacturer byte (0x04) genuinely does match, the `and` short-circuited and the
(already-broken) product-ID comparison never actually gated anything: `setup()` silently accepted
any device whose first RDID byte was 0x04, regardless of the rest of the response - including a
corrupted RDID transfer from a bus disturbance right at startup, the exact failure mode owner asked
this review to harden against. Fixed: correct byte order, `and` → `or`, and added a check on the
continuation-code byte (0x7F, also fixed for this chip) for a third independent field. Owner
confirmed the fix before it was applied (this changes real accept/reject behavior, per
`src/README.md` section 1's discrepancy-flagging rule).

**Bus-disturbance recovery added, scoped to what this file can actually observe**: raw RP2040 SPI
`write()`/`readinto()` genuinely cannot report a transfer fault (no ACK/NAK, confirmed in
`asy_spi_driver.py`'s own promotion) - data-integrity recovery (CRC, dual-copy redundancy) already
lives one layer up in `asy_fram_manager.py`, out of scope here. Two things this file *can* observe
were added, both per owner's explicit "whatever is required in this scope" direction:
- `_write()` now reads the status register (RDSR) after `WREN` to confirm the write-enable latch
  actually set before proceeding to `WRITE` - a disturbed `WREN` opcode would otherwise be silently
  ignored by the chip, and the subsequent `WRITE` would silently no-op too. Also re-checks after
  `WRDI`, retrying once (cheap, idempotent) before only warning if `WEL` is still stuck - a stuck
  `WEL` leaves the chip continuously writable, not itself a "did the payload write happen" failure,
  so it doesn't fail the write.
- `set_write_protected()` (kept - see below) now reads back the status register after `WRSR` and
  reports failure if it doesn't match, since that one transaction is the only way this chip's
  write-protect state can actually change, and is otherwise unverified. **Second real bug found
  this way, by the CI run of this same promotion's own new tests**: the pre-existing
  `set_write_protected()` never issued `WREN` before `WRSR` at all - present since the legacy
  driver, invisible until now because this method had zero real callers (see below). The status
  register's own `WEL` bit is documented as gating writes to "FRAM array and status register" both
  - i.e. `WRSR` needs `WEL` set first, exactly like `WRITE` does - so every call to this method
  would have silently no-op'd on real hardware. Fixed: `WREN` + the same `WEL`-verification `_write()`
  already does, before `WRSR`; an unconditional `WRDI` after, regardless of outcome, so `WEL` is
  never left asserted. (The new readback check itself is what caught this - it turned "silently
  does nothing" into a loud, reproducible test failure instead of a bug that could have shipped
  unnoticed a second time.)
- New `verify_present()`: a re-probe entry point (reuses the fixed RDID check) for a future
  health-check/retry policy to call after suspecting a disturbance - cheaper than a full `setup()`
  (skips `wp_pin` re-init), and on failure reverts `uninitialized = True` so every other method
  safely refuses until a fresh `setup()` succeeds, same self-healing state `setup()`'s own `OSError`
  already relies on. Wiring an actual periodic/triggered call to this into `asy_fram_manager.py` or
  a task supervisor is future work (needs `asy_fram_manager.py` promoted first) - this file only
  exposes the primitive.

**Kept, brought to full quality bar (owner-confirmed, previously "zero real callers" per the
`asy_spi_driver.py` promotion writeup above)**: `get_write_protected()`/`set_write_protected()` -
real hardware feature (BP0/BP1 block-protect + WPEN in the status register), plausible future use.
`set_write_protected()`'s return type changed `None` → `bool` (matches `set_values()`'s own
success/failure convention - a real API-consistency gap, `src/README.md` section 10) now that it
does real verification worth reporting. Zero existing callers anywhere in the codebase, confirmed
via `grep`, so this is a pure signature strengthening, not a breaking change.

**Also fixed** (style-only, no behavior change): a stray CircuitPython-style docstring on
`get_write_protected()` - inconsistent with every other `src/` file's "comments, never per-method
docstrings" convention (`src/README.md` section 11) - condensed into a `#` comment during the
post-promotion bird's-eye scan across `src/` this file's own addition triggered (per CLAUDE.md's
hard rule); no other cross-file discrepancy found.

**Resolved in a follow-up session**, once the project owner added the real datasheet PDF to the
new `datasheets/fram/` folder (see CLAUDE.md's "Datasheets" section - this file's own promotion is
what prompted adding it, after the original session hit a WebSearch/WebFetch rate limit trying to
fetch it from the web): confirmed directly from DS501-00015-4v0-E's "STATUS REGISTER" section, WEL
bit description - "WEL is reset after the following operations. After power ON. After WRDI command
recognition. At the rising edge of CS after WRSR command recognition. At the rising edge of CS
after WRITE command recognition." So yes, both a completed `WRITE` and a completed `WRSR` auto-clear
`WEL`, not just `WRDI`. `tests/_fram_chip_fake.py` updated to model this exactly; the previously
conservative fake (only `WREN`/`WRDI` changed `WEL`) is now accurate by default, with two new
opt-in fault-injection flags (`disturb_write_autoclear`/`disturb_wrsr_autoclear`) that suppress the
auto-clear specifically so `_write()`'s/`set_write_protected()`'s own explicit `WRDI`-verification/
retry path - genuine defense-in-depth against that auto-clear mechanism itself glitching, not
merely "the only thing that clears WEL" as originally believed - stays exercised by a real
simulated fault instead of becoming unreachable now that the normal case already clears `WEL`
before the explicit `WRDI` even runs. No driver code changes needed; the explicit `WRDI` calls
were already correct (if now confirmed usually redundant in the non-fault path) and are kept as
that defense-in-depth. 27/27 tests still pass with the corrected fake.

**Second finding from the same datasheet read, fixed after owner confirmation**: the real
`WP` pin is active-low per the "WRITING PROTECT" table (`WP=0` is what makes the status register
itself additionally locked when `WPEN=1`; `WP=1` leaves it changeable) - the same active-low
convention as `CS`/`HOLD` on this chip. `FRAM_SPI`'s `wp_pin` handling drove
`self._wp_pin.value(value)` directly (`value=True` -> pin driven `HIGH`), backwards from what the
datasheet's table says is needed to actually lock the status register. Owner confirmed the fix:
`setup()`/`set_write_protected()` now drive the pin to `not value`, and `get_write_protected()`
reads `not bool(self._wp_pin.value())`, so `value=True` (protect) now genuinely drives `WP` low
and locks the status register, matching the class's own stated "enables hardware-level
protection" intent. Zero real callers existed either way, so this is a pure correctness fix, not
a behavior change for any real caller.

Testing: a fourth mocking-boundary instance, `tests/_fram_chip_fake.py` - a stateful fake MB85RS64V
sitting on top of `tests/machine.py`'s dumb fake SPI bus, interpreting the exact opcode/CS-session
shapes `FRAM_SPI` itself produces (RDID/RDSR/WRSR/WREN/WRDI/READ/WRITE), with fault-injection knobs
(`drop_wren`/`drop_next_wrdi`/`drop_wrsr`/`disturb_write_autoclear`/`disturb_wrsr_autoclear`/
`rdid_response`) for simulating a disturbance eating one specific transaction's effect. 29 tests in
`tests/test_asy_fram_driver.py`, including direct regressions for the RDID byte-order/`and`-vs-`or`
bug, the new WEL/write-protect verification paths, and the `WP`-pin-polarity fix. No
`pyproject.toml`/CI changes needed - both already scope by directory (`src`, `tests`), not an
explicit file list.

**Follow-up leanness pass** (owner-requested structure/simplification review): `_write()` and
`set_write_protected()` had near-duplicate WREN-verify/WRDI-verify-retry sequences, and
`set_write_protected()`'s trailing WRDI never checked or warned on a stuck `WEL` the way
`_write()`'s did - an inconsistency, not just duplication. Extracted shared
`_send_opcode()`/`_wel_is_set()`/`_enable_write()`/`_disable_write()` helpers; both methods now use
the same preamble/epilogue, and a stuck `WEL` after `set_write_protected()` is warned the same way
(status: still returns success - a stuck latch is a housekeeping issue, not a "did the protection
change happen" issue, same reasoning as `_write()`'s own stuck-WEL case). Also renamed
`setup_addr_buffer` -> `_setup_addr_buffer`: it had zero external callers (confirmed via grep) and
was the one public-looking method with no real external API role, inconsistent with every other
internal helper in the file being `_`-prefixed. Added one line to the module docstring noting the
chip's own internal CS pull-up (a disconnected CS wire reads deselected on real hardware, not
floating-asserted - a bus-disturbance case this file never needs to defend against itself).

**Noted, not changed**: `get_size()` also has zero callers anywhere in the codebase today (checked
via grep - `AsyFramChunk`/`AsyFramTimestampedChunk` have their own same-named but unrelated
`get_size()`). Unlike `setup_addr_buffer`, left as public API surface rather than flagged as dead
code - a trivial, obviously-useful capacity getter for any future consumer of this
byte-addressed-storage abstraction, not something with an ambiguous "should this even exist"
question the way the write-protect methods had. `get_values()`/`set_values()` also don't reject a
zero-length `buf` (a no-op read/write) - deliberately not restricted: real callers
(`asy_fram_manager.py`) never pass one, the datasheet doesn't document 0-byte `WRITE` behavior
either way, and rejecting a domain no real caller ever exercises would be defensive code for a
case that isn't known to actually be invalid (see `src/README.md` section 4's "don't add checks
just in case").

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
`base_classes.py` 72, `config_manager.py` 140, `print_log.py` 50, `asy_fram_driver.py` 28 — **521
total**.

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
