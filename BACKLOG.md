# BACKLOG

The project's running knowledge base for the `improved-quality/` refactor and anything else worth
recording so it doesn't get re-litigated from scratch in a future session: the refactor's
final-goal requirements, decisions already made, functional clarifications, review findings, open
questions, explicitly deferred work, and security notes — not just open questions and deferred
work, despite the filename. See README.md for orientation and CLAUDE.md for operating constraints.

## Final-goal requirements for the refactor (owner-specified, mostly not yet implemented)

These are additional requirements for what the `improved-quality/` refactor must eventually
deliver. Recorded here as a target/spec — mostly not implemented yet, not to be actioned until the
refactor work itself starts, **except where marked done below**: the manual-only ruff/mypy/stub
tooling was deliberately pulled forward ahead of the refactor (see "Rough suggested sequencing"
below for why that's a scoped exception, not a change in overall approach):

- **Stability / robustness**: thorough error handling throughout — no error condition that can
  plausibly occur in real operation should lead to an uncaught exception; anything that might
  happen should be caught and handled explicitly. The hardware watchdog is a last resort only
  (e.g. undefined state after an electrical brownout, a MicroPython interpreter-level failure),
  not a routine recovery mechanism for expected error conditions.
  - **Bare `except:` is forbidden in the refactored code** — `except Exception:` (or a narrower/
    specific exception type) is required everywhere. The current ruff config (root
    `pyproject.toml`, see "Production-level code quality" below) already doesn't ignore E722 —
    bare excepts still present in `improved-quality/` today show up as flagged findings rather
    than being silenced. Actually eliminating them is still real refactor work, not a config
    change; the old `improved-quality/pycheck.sh` (which did ignore E722) is gone, retired in
    favor of this.
- **No leaks, no drift**: the system should be able to theoretically run indefinitely without
  exhausting any resource (memory, handles, counters, etc.). **Verified via design discipline, not
  an automated soak test** — no dedicated long-running/memory-tracking test is required in CI for
  this; it's enforced through code review and patterns (bounded buffers, no unbounded growth),
  not a CI gate.
- **Production-level code quality**: unit tests, mypy, and ruff shall all be available both as
  shell command scripts and as a CI pipeline, which **shall also attempt a real firmware build**
  (running the equivalent of `build-*.sh`, with the full micropython/pico-sdk/picotool toolchain)
  as a pipeline stage, not just lint/type-check/unit-test. **This repo is GitHub-hosted, not
  GitLab** — earlier revisions of this doc said "GitLab CI"; that was never actually checked
  against where the repo lives and has been corrected throughout to GitHub Actions.
  - **Done**: root `pyproject.toml` + `scripts/lint.sh` + `scripts/typecheck.sh` +
    `scripts/test.sh`, scoped to `improved-quality/`, `src/`, and `tests/` (see CLAUDE.md's "Code
    quality tooling" section for the full rationale). `improved-quality/mypy.ini` and
    `improved-quality/pycheck.sh` — an ad hoc, trial-and-error setup — have been retired in favor
    of this. A GitHub Actions pipeline (`.github/workflows/ci.yml`) runs all three on every
    push/PR. Unit tests exist for `src/math_helpers.py` (the first file moved out of
    `improved-quality/`), running under a real MicroPython Unix-port interpreter built by
    `toolchain/setup_toolchain.py`'s `setup`/`test` (no separate `unix` subcommand — building the
    Unix port is just part of what those already do) — see "Self-contained venv via `uv`" below
    and `tests/README.md`. **Still open**: the CI pipeline doesn't yet attempt a real firmware build
    (still blocked on the `build-*.sh`/hardcoded-path genericization below), and scope hasn't
    been extended to the pre-refactor codebase (`python/`, `modules/`) — CLAUDE.md's "No unit
    tests against the current codebase" rule still applies there.
  - **This elevates the build/dev-environment setup item** (see "Deferred / explicitly
    out-of-scope work" below) **from someday-work to a real near-term prerequisite**: CI can't
    build firmware while `build-*.sh`/`update_and_install.txt` still assume a hardcoded
    `/home/nico/rpi_pico/...` layout. Genericizing that setup needs to happen before/alongside
    building this CI stage, not after.
  - **MicroPython stubs**: **done** — `micropython-rp2-rpi_pico_w-stubs` (PyPI, board/version
    specific; pulls in `micropython-stdlib-stubs`), installed by `scripts/typecheck.sh` into a
    gitignored `typings/` directory kept deliberately separate from the main dev venv (see
    CLAUDE.md for why — it's load-bearing, not incidental). Version is auto-derived from
    `toolchain/versions.toml`'s `[micropython] ref` (the single source of truth for the firmware
    target — currently 1.28.0), not a second hand-kept pin; a mismatch (malformed `ref`, or no
    published stub release yet for that firmware version) fails loudly with an actionable error
    rather than silently falling back to something stale.
  - **Ruff/mypy config**: **done** for the scope above — stricter than default where it concerns
    actual code quality/correctness, but **allow any line length and don't introduce line
    breaks** — ruff's `--format` step is omitted entirely rather than configured with a
    line-length; this is a deliberate style choice, not an oversight.
    - **mypy does NOT disable the `assignment` error code** (done — the old
      `improved-quality/mypy.ini`'s `disable_error_code = assignment` was never a deliberate
      choice and has been dropped in the new `pyproject.toml` config).
  - **No hard test-coverage percentage gate** — **done**: `scripts/test.sh --coverage` and a
    non-gating CI step (`.github/workflows/ci.yml`) report `src/` line coverage (HTML, Cobertura
    XML uploaded to Codecov, and a markdown summary posted to the Job Summary) — see
    `tests/README.md`'s "Coverage" section and README.md's "Test coverage". This was a deliberate
    choice, confirmed directly, not a placeholder for a future gate: coverage is reported, never
    enforced, and there's no plan to add a threshold later.
  - **PEP 604 union syntax** (`int | None`, already used in `improved-quality/base_classes.py`) is
    confirmed safe at runtime on MicroPython, including the deployed 1.26 pin and the refactor's
    1.28.0 target: MicroPython's compiler parses but never evaluates annotation expressions (a
    documented space-saving tradeoff, confirmed present as far back as the 1.15/1.16 docs, not a
    new/version-specific behavior) — see "Syntax" in the MicroPython docs
    (https://docs.micropython.org/en/latest/genrst/syntax.html). This means `float.__or__`/
    `UnionType` support is irrelevant here; the `X | None` text is simply never executed. No
    `from __future__ import annotations` needed either. Verified by web search against current
    MicroPython docs during the `src/math_helpers.py` review — no longer an open question.
- **Self-contained venv via `uv`**: testing shall be possible on a generic Linux machine inside a
  venv installable via `uv sync`. **Tests run under the real MicroPython interpreter** (e.g. a
  built Unix port), not CPython — "as close to the real environment as possible" means the actual
  MicroPython runtime, not just MicroPython-flavored stubs on top of CPython.
  - **How `uv` and the Unix port connect**: `uv sync` itself only manages the CPython-side tooling
    (pytest, ruff, mypy, etc.) — it can't install a compiled MicroPython binary. **Building/
    verifying the interpreter itself is done** — `toolchain/setup_toolchain.py`'s `setup`/`test`
    now verify the whole toolchain via an 8-step frozen-bytecode chain
    (`run_verification_sequence()`), not a one-off manual check: freeze a small test module into
    both the Unix port and the RP2 firmware (via the same `freeze()`/`FROZEN_MANIFEST` mechanism
    this repo's own `python/Manifest/manifest.py` already uses — `mpy-cross`-compiled bytecode is
    architecture-independent, so the same frozen module works in either build), import it *by
    name* inside the built Unix port binary with no source `.py` file anywhere on disk (proving
    it's genuinely compiled into the executable, not read from a filesystem path at runtime),
    build the RP2 firmware the same way (build-only — there's no RP2 hardware here to run it on,
    so a clean build with zero errors/warnings is the whole check), clean up both frozen-module
    builds, then rebuild a vanilla Unix port as the standing test rig kept afterward. This is now
    the standing, automatic verification every `setup`/`test` run performs — see
    `toolchain/README.md`'s "Verification" for the exact step order. Relevant if the test suite
    ever wants this project's own drivers frozen into a Unix-port test build rather than run from
    loose `.py` files. Needs one additional apt package (`libffi-dev`, for the Unix port's `ffi`
    module), now in `versions.toml`'s `apt_packages`. Verified end-to-end: a fresh install (both
    the latest release and the deployed `v1.26.1` pin), the in-place update path (`v1.26.1` →
    `v1.28.0`), `--clean` (confirmed it wipes `ports/unix/build-standard` too), a from-scratch run
    on a genuinely clean Ubuntu 24.04 (`debootstrap` chroot, same rigor as the toolchain's existing
    "Evidence this actually works") — see `toolchain/README.md` for details. **Still open**: this
    only builds/verifies the Unix port binary, it isn't wired into `uv sync`/pytest yet (no
    automatic "run this before tests" trigger) — that and the mocking boundary below remain future
    work, blocked on CLAUDE.md's "No unit tests against the current codebase" rule same as before.
  - **Wired into the actual test suite**: `scripts/test.sh` runs `toolchain/setup_toolchain.py`
    (plain `setup`) automatically the first time it needs the Unix-port interpreter — there is no
    separate `unix` subcommand; building/verifying the Unix port is just part of what `setup`/
    `test` already do (see the bullet above) — then reuses the cached build (under
    `$PICO_TOOLCHAIN_DIR`, default `~/pico-toolchain`, the same location and source checkout
    `setup`/`test` use for the RP2040 build) on later runs, so a plain `scripts/test.sh` after
    `uv sync` is still the complete onboarding path, matching this bullet's original "ideally
    triggered automatically" goal. **First concrete test suite**: `tests/test_math_helpers.py`
    (45 cases, see CLAUDE.md's `src/` hard rule) runs this way both manually and in CI
    (`.github/workflows/ci.yml`'s `unit-tests` job) — the "blocked on CLAUDE.md's 'No unit tests
    against the current codebase' rule" caveat this bullet previously had no longer applies to
    `src/`, only to the pre-refactor `python/`/`modules/` code as that rule always intended (see
    CLAUDE.md). **Still open**: expanding test coverage beyond `math_helpers.py`/`crc_checks.py`/
    `asy_i2c_driver.py` remains future work.
  - **Mocking boundary**: mock only at the raw bus-transaction level (`machine.I2C`/`machine.SPI`
    read/write calls) — drivers, Reader classes, `ConfigManager`, and REST handlers should all run
    for real, unmocked, in tests. Mock higher up (e.g. whole driver classes) only if there's truly
    no other way. **First built and exercised, not just planned**: `tests/machine.py` (a fake
    `I2C`/`Pin`, added for `asy_i2c_driver.py`'s own `src/` promotion — see the finding below) is
    the concrete instance of this plan. It backs a real dict-of-registers store so
    `get_bits`/`set_bits`/`get_register_struct`/`set_register_struct` round-trip through actual
    `readfrom_mem`/`writeto_mem` calls instead of canned return values, and lets a test flag an
    address as NAK'ing (`nak_addresses`) to exercise real `OSError` propagation. Confirmed
    directly: the MicroPython Unix port's own built-in `machine` module (used by `scripts/test.sh`)
    has no `I2C`/`SPI`/real `Pin` (only `PinBase`/`Signal`/`mem8`/`mem16`/`mem32`/`idle`/
    `time_pulse_us`) and does not shadow a same-named module earlier on `MICROPYPATH` (verified: a
    file-based `tests/machine.py` placed before `.frozen` on the path is what actually gets
    imported) — so this mock is the only way any I2C/SPI-touching file can be tested at all under
    this project's real-interpreter testing requirement. `asy_spi_driver.py`'s own future `src/`
    promotion should extend this same file with a fake `SPI` class rather than inventing a second,
    differently-shaped mock.
    - **`network`/CYW43 (WiFi) is in the same "mock it, no other way" tier as the physical
      buses** — the MicroPython Unix port has no real WiFi hardware at all, so `async_connect.py`'s
      WiFi-dependent logic needs `network` mocked to be testable in the automated suite, the same
      way I2C/SPI get mocked at the hardware boundary.
- **Centralized config**: all tooling config shall live in `pyproject.toml`, as **dev-tooling
  config only** (ruff/mypy/pytest/uv sections) — the shipped code stays frozen-bytecode-only, not
  restructured into an installable package. **Done** — root `pyproject.toml`, see above.
- **Unified CRC-based data-integrity checking**, generalized and kept as a standing feature, not a
  one-off: `improved-quality/crc_checks.py`'s generic `CRC8`/`CRC16`/`CRC32` engine (with a
  `CRC_Pass` no-op for when it's not needed) grew organically — first added for UART data
  integrity, then applied to the I2C sensors' own documented CRC8 protocol (SCD30, SGP40), then
  unified into one shared class, then extended to protect FRAM-stored chunks (error-log history,
  SGP40 VOC-algorithm backup state) — and should keep being applied everywhere data integrity
  matters, not left as an incidental byproduct of past feature work.

### Bus/sensor error-recovery robustness (owner-specified, not yet implemented)

Additional requirements specifically about exception handling and bus/sensor fault recovery, from
hands-on field experience with the current deployed units:

- **Nested try/except correctness**: past firmware crashes have come from nested try/except blocks
  that either caught too early (masking the real problem, handling it wrong) or let exceptions
  propagate too far (not caught where they needed to be). The refactor needs deliberate focus on
  getting these constructs' actual behavior right, not just present.
  - **Catch granularity confirmed**: today's pattern in e.g. `asy_scd30_driver.py`'s `read_scd()` —
    one broad `except:` around a whole per-iteration multi-command read, with full task-death +
    supervisor-respawn as the only deeper reset — is confirmed as the right granularity. Don't
    split into finer per-command catches within one iteration.
  - **Exception types**: distinguish exception types only where genuinely different handling is
    required; otherwise treat uniformly. The one hard rule: **nothing may ever silently slip
    through uncaught** — this is about handling appropriately, not about never discriminating.
- **Live bus reconnect must be preserved**: field-tested by physically disconnecting and
  reconnecting an I2C/SPI wire on a live unit — it was possible to handle entirely in software
  (exception handling, responses, retry) and have the sensor reconnect live once the cable was
  reinserted, without a reboot. This property must survive the refactor.
  - **Recovery mechanism confirmed, but treat as a basis to revisit, not gospel**: the
    task-death-and-respawn path (dead reader task → supervisor restarts it → fresh `setup()`/reset)
    is confirmed as what has been making live reconnect work — but the project owner flagged it may
    be incomplete, and it should be revisited/hardened during the actual refactor work rather than
    assumed complete.
- **Sensor/bus-specific defined-state recovery should be as complete as possible**: sensor
  firmware/bus stacks can end up in an undefined state, and there are bus/sensor-specific ways to
  force a defined state again (e.g. clocking out a fixed number of cycles, reset sequences, reset
  commands) — depends on the bus type and sensor. **Correction (found while prepping the SPI
  driver's own `src/` promotion): `extra_clocks` is not an existing mechanism.** It appears exactly
  once, as an Adafruit CircuitPython `busdevice`-derived docstring line on
  `python/IndividualDrivers/asy_spi_driver.py`'s constructor ("the minimum number of clock cycles
  to cycle the bus after CS is high... Used for SD cards") — never a real constructor parameter,
  never implemented, not even in the legacy driver, and not present at all in
  `improved-quality/asy_spi_driver.py`. This was previously (incorrectly) cited here as an example
  of already-existing bus-recovery cycling; it isn't. If SD-card-style post-deassert clock cycling
  is still wanted for SPI, it needs to be designed and implemented from scratch, not "made more
  consistent" from an existing example — there is no existing example.
  - **I2C recovery is device-specific, not bus-generic**: I2C recovery (retry + sensor reset
    commands) is expected to vary per device — check what each individual driver already does
    before assuming a gap. If a genuinely generalizable I2C-side mechanism
    turns up (e.g. common to several sensors), it's fine to add to the shared bus driver; otherwise
    keep it device-specific. *(Follow-up needed: this session only read `asy_scd30_driver.py`'s
    reset path in depth — SGP40's `_reset()` and BMP3xx's reset command still need the same
    review before concluding what's generalizable.)*
  - **FRAM's SPI bus gets the same bus-recovery treatment as sensor buses** — no special-casing
    needed there; the project owner already handles many corrupted-memory situations at the data
    level (dual-copy redundancy), and applying the same bus-level recovery techniques on top is
    fine.
  - **Keep error handling per-driver, not a shared generic framework**: despite the goal of
    consistency, a shared retry/backoff/reset policy object across all Readers was explicitly
    rejected — sensors (especially I2C ones) differ enough that per-driver hand-rolled handling is
    preferred over forcing a common abstraction.
    - **How this squares with "refactor identical/similar behavior into classes" below**: only
      generalize what's genuinely common to *all* drivers (e.g. the error-counter
      increment/decay bookkeeping already generalized in `SensorReader._error_check()`) — bus/
      sensor-specific retry, backoff, and reset-sequence logic stays in the specific driver.
      Don't force fragmentation by over-abstracting, but don't force a shared policy object onto
      genuinely device-specific recovery logic either.
- **Blocking calls must have a timeout or other unblock mechanism**: calls previously assumed safe
  turned out to block in practice — a real source of unexpected errors. The refactor should
  re-check this specifically: any call that can block should have an explicit timeout or another
  way to guarantee it can't hang indefinitely.
  - **Known real-world case**: the SCD30 (which has its own onboard microcontroller) has been
    observed to hang the bus — suspected to be the SCD30's own firmware getting stuck, not the
    RP2040's I2C peripheral. Since MicroPython's cooperative scheduler can't preempt a synchronous
    `machine.I2C` call already in progress, an asyncio-level timeout cannot actually interrupt a
    transaction that's genuinely wedged mid-flight.
  - **Decided**: for a truly stuck bus/sensor (the SCD30-hang case), **the hardware watchdog is the
    accepted backstop** — not something to chase a software-only fix for. No respawn-rate cap/
    backoff is needed beyond the existing task-supervisor error-budget; current behavior there is
    considered adequate.
  - **For calls that genuinely can be timeout-wrapped** (e.g. `socket.getaddrinfo()`, FRAM SPI
    transactions, anything not a raw blocking `machine.I2C` call mid-transaction), **standardize on
    one consistent timeout/cancellation mechanism** applied everywhere such a call exists, rather
    than a different bespoke approach per call site.
- **Bus concurrency via `asyncio.Lock` + `async with` needs a coverage audit**: the current pattern
  (one lock per physical bus, acquired per-transaction via `I2CDevice`/`SPIDevice`'s `async with`)
  is believed to be the right general approach, but the refactor should specifically verify these
  locks truly cover the complete bus access with no gaps, and that they can't block each other
  (e.g. deadlock, or one long-held lock starving an unrelated bus user).
  - **Concrete progress already visible**: `improved-quality/asy_scd30_driver.py`,
    `asy_bmp3xx_driver.py`, and `asy_sgp40_driver.py` each introduced a `*_DeviceSession(Lockable)`
    class — an outer per-sensor lock wrapping the whole multi-step transaction (write a command,
    then read the reply), with an explicit `await asyncio.sleep(0)` yield between the write and
    read phases so the underlying bus lock isn't held across a lock-then-forget gap. This is the
    actual mechanism this audit item was asking for; treat it as the pattern to verify/extend
    rather than starting the audit from scratch.

  - **Open question surfaced by this pattern's rollout**: several low-level setter/getter
    forwarding methods on these same Reader classes were changed from bare pass-through coroutines
    to `try/except Exception: return False/None`. That satisfies "nothing may slip through
    uncaught," but it wasn't verified whether the swallowed exception is still logged via
    `self.pr` — if it silently becomes a `False`/`None` with no log trace, that's a silent-failure
    risk that cuts against the robustness goal rather than fulfilling it. Needs checking before
    this pattern is treated as settled.

### Code structure / style patterns for the refactor (owner-specified, not yet implemented)

Additional style and structure patterns the refactor is expected to apply throughout. The project
owner noted **much of this is already done in `improved-quality/`** — recorded here as the
patterns to hold the rest of the refactor to, not as new/unstarted work:

- **Define configs and behavior used at multiple sites in exactly one location** — no
  hand-copied constants/logic repeated per device or per sensor (this is the same spirit as the
  existing config-duplication concern in "Deferred / explicitly out-of-scope work" below, now
  elevated to a general structural principle, not just a config-keys issue).
  - **Concrete mechanism already emerging**: `asy_scd30_driver.py`/`asy_bmp3xx_driver.py`/
    `asy_sgp40_driver.py` each define per-field config schema strings (`_VAL_*`, e.g. type/min/max/
    default metadata) and expose `get_dict_cfg()`/`get_dict_data()` to export them. This is the
    actual answer to the "config-duplication centralization" deferred item below — a single
    per-driver schema that validation, storage, and (eventually) the REST/HTML layers can all read
    from, instead of hand-keeping `_DEFAULT_CONFIG`, the REST handler, and the HTML form in sync.
    Not fully wired end-to-end yet (see the "Findings" section below), but the mechanism itself is
    the right direction to keep building on.
- **Handle device / sensor / functional config storage separately** — already visible in
  `improved-quality/base_classes.py`'s `SensorReaderConfig`, which gives each sensor its own
  `config_<name>.cfg` file via a per-instance `ConfigManager`, rather than one monolithic
  device-wide config file (see also the "Config-schema data-loss risk" item above, which this
  directly supersedes for the refactor).
  - **Target model, per the project owner**: every config value should end up **per-device,
    per-feature, or explicitly global — but never implicitly coupled to something unrelated.**
    Per-sensor config (via `SensorReaderConfig`) already satisfies the per-device/per-feature case.
    What's not yet resolved is the *explicitly-global-but-detached* case: cross-cutting settings
    like network/WiFi and the Neopixel LED currently still end up sharing one ad hoc top-level
    `ConfigManager` instance in `sensortask-wozi.py` (itself confirmed to be an intentional
    intermediate state, not finished) — that shared instance should become its own clearly-scoped
    global config, not an implicit grab-bag, once this part of the refactor is picked back up.
- **Reduce code size, improve readability, especially via inheritance** — e.g.
  `improved-quality/base_classes.py`'s `SensorReader`/`SensorReaderConfig` hierarchy, and
  `asy_fram_manager.py`'s `_AsyBaseFramChunk` base class with `AsyFramChunk`/
  `AsyFramTimestampedChunk` subclasses.
- **Generalized startup / error-recovery behavior** — e.g. `SensorReader._error_check()` in
  `base_classes.py` centralizes the increment/decrement-error-counter-and-decide-to-die logic that
  every current `sensortask-*.py` driver hand-rolls separately today.
  - **Concrete mechanism**: each Reader implements a uniform `get_task_starters()`/
    `get_timer_starters()` pair, which is how `system_service.py`'s generic task supervisor
    discovers and starts each driver's tasks/timers without the device file needing to hardcode
    method names — this is the specific interface that makes the generalization above actually
    pluggable rather than just "shared code that still has to be wired up by hand."
- **Trace-log error codes inside FRAM, surviving a reboot** — implemented via `PrintLogHistStore`
  (`print_log.py`), which persists an error/warning code history + count into a FRAM chunk,
  restored on `setup()`.
- **Store errors alongside console prints, not instead of them** — `PrintLog`/`PrintLogHistory`'s
  `err_s()`/`wrn_s()` both persist the error code *and* still `print()` it; logging isn't meant to
  replace the existing debug-print visibility.
- **Handle FRAM more generically and consistently** — `improved-quality/asy_fram_manager.py`'s
  chunk-class hierarchy (see inheritance point above) plus `LockableBuffer`-based buffer types is
  the intended generalized model, vs. the current codebase's more ad hoc FRAM chunk handling.
- **Prefer preallocated buffers and in-place writes over allocate-and-return, and bulk bus
  transactions over per-byte loops** — a recurring embedded-resource-discipline pattern spotted
  independently in multiple files, worth stating as its own principle rather than leaving it
  implicit in each one: `asy_fram_driver.py`'s `get_values`/`set_values` moved from returning a
  fresh `bytearray` per call to filling a caller-supplied buffer in place; `asy_fram_manager.py`'s
  `LockableBuffer`-based chunk buffers are reused rather than reallocated per read/write; the FRAM
  SPI driver's `_write()` moved from writing one byte at a time in a loop to a single bulk
  `spidev.write(data)` inside one CS assertion; SGP40's command/CRC buffers write into slices of a
  persistent buffer instead of building new lists per call. Directly supports the "no leaks, no
  drift" final-goal requirement above (less heap churn, less GC pressure) and reduces per-call bus
  transaction overhead — apply this pattern wherever a hot-path allocation or per-byte loop is
  found elsewhere in the refactor, not just in the files it's already landed in.
- **Generalize hardcoded constants into parameters when consolidating duplicated code, not just the
  logic itself** — e.g. going from `base_classes_old.py` to the current `base_classes.py`, the old
  `TimeCounterManager`'s baked-in 50-year-in-seconds wraparound cap became the new generic
  `LockedCounter`'s `max_val` constructor parameter, with call sites (e.g. `system_service.py`)
  now passing the bound explicitly (`LockedCounter(max_val=0xFFFFFFFF)`). When folding
  similar/duplicated classes together elsewhere in the refactor, check whether they also embed a
  constant that should become a parameter instead of being carried over as-is.
- **Refactor identical/similar behavior into classes** — same evidence as the inheritance point
  above; this is a general principle to keep applying, not a one-off. **Scope it to what's
  genuinely common across drivers** (e.g. error-counter bookkeeping, FRAM chunk handling, config
  storage) — this doesn't extend to forcing a shared framework onto bus/sensor-specific error
  recovery, which is deliberately kept per-driver (see the "Bus/sensor error-recovery robustness"
  section above for why).
- **Refactor long/deep program flows into subfunctions with an early-return scheme** — a general
  style requirement for the remaining refactor work (e.g. the current codebase's deeply nested
  `sensortask-*.py` REST handlers and `async_connect.py`'s `wlanConnect()` are examples of what
  *not* to carry forward as-is).

### Rough suggested sequencing

A rough priority order across everything above, so this doesn't read as one flat unordered list —
not a committed project plan, just a sensible dependency-aware starting point for whenever the
refactor work actually begins:

1. **Dev/build environment setup** (genericized `build-*.sh`/toolchain paths) — everything else
   that touches CI or a real firmware build depends on this existing first.
2. **Per-sensor config storage** and the other code-structure patterns (inheritance-based
   `SensorReader`/`SensorReaderConfig`, generalized FRAM chunk handling, generalized
   startup/error-counter bookkeeping) — foundational structure that the robustness work below
   builds on top of.
3. **Bus/sensor error-recovery robustness** (nested try/except correctness, live reconnect,
   defined-state recovery, timeout handling, lock-coverage audit) — depends on the structural
   pieces above existing to refactor *into*, rather than bolting robustness onto the old shape.
4. **Tooling and CI** (mypy/ruff config, MicroPython stubs, the `uv`-managed venv + Unix-port
   interpreter setup script, unit tests, GitHub Actions CI including the firmware-build stage) —
   comes last since it's meaningfully easier to write tests and wire up CI against the settled
   post-refactor structure than against a moving target. **Partial exception, done out of order**:
   manual-only mypy/ruff config + MicroPython stubs (see "Production-level code quality" above)
   were pulled forward ahead of this sequencing, scoped to `improved-quality/` as it stands today.
   The Unix-port build (now just part of `setup_toolchain.py`'s `setup`/`test`, no separate
   subcommand — see "Self-contained venv via `uv`" above), a first `src/`/`tests/` unit-test pair
   (`math_helpers.py`), and a lint/type-check/unit-test GitHub Actions pipeline were similarly
   pulled forward once `math_helpers.py` became the first file to reach the "fully reviewed" bar
   `src/` requires (see "Production-level code quality" above) — scoped the same way, not a full
   move-up of this whole sequencing item. `crc_checks.py` cleared the same bar shortly after (see
   "Findings" below) — extending `src/`'s scope to more files is now an ongoing, incremental part
   of this pulled-forward work, not a one-off tied to a single file. **Still blocked on this
   sequencing**: the firmware-build CI stage (blocked on the `build-*.sh` path genericization,
   same as before).

## Findings from reviewing `improved-quality/` against this spec

A file-by-file pass comparing every file in `improved-quality/` against its legacy equivalent (and,
for files with no legacy equivalent, reading them cold), then matching the differences against
everything else in this document. Confirms most of the "Code structure / style patterns" section
above is genuinely underway, but surfaces some new items:

- **Cross-file wiring is currently incomplete, but each instance turned out to be a known,
  explainable WIP state, not a surprise regression** — confirmed by the project owner:
  - `api_helpers.py`'s mismatch against `config_manager.py`'s current `get_dict`/`write_config`
    signatures is exactly where the project owner paused this file's refactor — there's a `# TODO
    what to do if...`-style comment marking the spot, left mid-thought for unrelated reasons. It's
    the natural place to pick the refactor back up, not a bug that snuck in unnoticed.
  - `neopixel_signal.py` simply **hasn't been refactored yet** — its wrong `async_manager` import
    and `get_int_values`/`get_float_values` mixup are exactly what you'd expect from an
    untouched-since-copy file sitting next to already-modernized siblings, not a defect.
  - `sensortask-wozi.py`'s misplaced `ntp_force_sync()` call inside the recurring supervisor loop
    was a **deliberate temporary fix for an NTP client bug**, made in-place during debugging and
    never moved back to its proper one-time pre-loop position afterward — a known loose end to
    revert, not an accidental regression. The other constructor-argument mismatches in this file
    remain as-described: `sensortask-wozi.py` is confirmed to be in an intentional intermediate
    state (see the config-model note below), not finished wiring.
  - **Takeaway unchanged**: individual files being "far along" doesn't mean the subsystem works
    end-to-end yet. An integration pass reconciling call sites against current signatures is still
    needed before treating any of these files as done — but every gap found so far has a known,
    benign explanation rather than being a mystery to root-cause.
- **`improved-quality/microdot.py` fork — confirmed, not just decided**: the project owner
  confirmed this was unintentional drift. **Action when refactor work resumes: revert
  `improved-quality/microdot.py` to match the vendored upstream copy exactly** — no behavioral
  additions of our own in this file, ever. Not changed now, since `improved-quality/` isn't to be
  edited outside dedicated refactor work (see CLAUDE.md's hard rules).
- **CRC integrity checking is confirmed as an intentional, evolving feature — promoted to a
  final-goal requirement** (see "Final-goal requirements for the refactor" above for the actual
  goal entry). History, per the project owner: originated as CRC-checking added for UART
  functionality; then applied to the I2C sensors (SCD30/SGP40) once their own CRC8 protocol
  requirement was noticed; then unified into one shared `crc_checks.py` class; then extended to
  FRAM chunk integrity as well. Not an accidental byproduct — keep generalizing it as a goal, not
  just something to leave alone.
- **`crc_checks.py` moved to `src/`**: cleared the full `src/README.md` checklist — correctness
  verified against Sensirion's own datasheet test vectors (already quoted in
  `asy_sgp40_driver.py`'s docstring) plus the public CRC-16/CCITT-FALSE and CRC-32/MPEG-2
  standards, exception handling narrowed to the specific MicroPython-confirmed failure mode
  (`ValueError`, not a broad `except Exception:`), missing negative-value/length guards added,
  `tests/test_crc_checks.py` added and passing under the real MicroPython Unix-port interpreter.
  A table-driven (256-entry lookup table per width) CRC implementation was considered as a speed
  optimization over the current bit-banged loop and explicitly declined for now: real usage here
  is small buffers (2-3 byte sensor CRC8 checks, modest FRAM chunks), so the RAM cost (up to ~1KB
  for a CRC32 table) wasn't judged worth it against a gain that likely doesn't matter at this data
  volume — revisit if a future caller pushes meaningfully larger buffers through this engine.
- **`asy_i2c_driver.py` moved to `src/`**: cleared the full `src/README.md` checklist, including its
  new "raw bus-transaction calls may propagate `OSError`" carve-out (see that file's section 2) —
  this is the first hardware-touching file to go through `src/` promotion, so several findings here
  are new precedent, not just this-file fixes:
  - **Real correctness fix, confirmed against current MicroPython docs**: `I2C.deinit()` never
    called the actual `machine.I2C.deinit()` (confirmed to exist and deactivate the hardware bus) —
    it only dropped the Python reference, in both the legacy `python/` driver and this file, unlike
    `asy_spi_driver.py`'s `SPI.deinit()`, which already called the real thing. Fixed to match SPI's
    existing pattern. `asy_spi_driver.py` itself was **not** touched (out of scope for this session,
    per the project owner) but its own future review should drop its now-redundant
    `try/except AttributeError` around the real `deinit()` call for the same reason this file's was
    removed — a bound method on a real `machine.SPI`/`machine.I2C` object doesn't raise
    `AttributeError`.
  - **`scan()`/`writeto()` widened to return `None`** instead of a magic default (`[]`/`0`) when the
    bus isn't initialized, matching the project's established "`None` = no data, never a disguised
    magic value" convention (`crc_checks.py`, `math_helpers.py`). `get_register_struct()` already
    followed this convention. **Follow-up needed, tracked here per the project owner's request**:
    `I2CDevice` and the three sensor drivers (`asy_scd30_driver.py`, `asy_sgp40_driver.py`,
    `asy_bmp3xx_driver.py`) don't currently check these return values at all (none of their current
    callers depended on the old magic defaults either, so this was backward-compatible today) — a
    future pass through those files should explicitly handle a `None` here rather than silently
    relying on downstream code tolerating it by accident. Several methods stayed `-> None`
    (`readfrom_into`, `set_bits`, `write_then_readinto`, `writeto_then_readfrom`) and so still can't
    signal "did nothing, bus uninitialized" to a caller at all — same underlying gap, flagged rather
    than silently redesigning further beyond what was asked this session.
  - **Real latent bug fixed**: `set_bits()` took a separate `endian` parameter (independent of its
    own `lsb_first` parameter) for the write-back, and `set_register_struct()` took a separate
    `endian` parameter instead of deriving byte order from `reg_format`'s own prefix character (like
    `get_register_struct()`'s `struct.unpack` already did) — both could silently disagree with the
    read-side byte order for a multi-byte register. Neither was ever exercised by a real caller
    (every current `get_bits`/`set_bits` call site uses `reg_width=1`, where byte order is moot;
    `get_register_struct`/`set_register_struct` have no callers yet at all, only the not-yet-ported
    `python/IndividualDrivers/asy_isl29125_driver.py`), but both are real API-contract bugs waiting
    for `reg_width > 1`/a mismatched format string. Fixed by dropping the separate `endian`
    parameter from both — `set_bits()` now derives byte order from `lsb_first` alone, and
    `set_register_struct()` from `reg_format`'s own prefix via `struct.pack()` (symmetric with
    `get_register_struct()`'s `struct.unpack()`).
  - **`get_bits()`/`set_bits()` gained a range guard** (`num_bits`/`start_bit`/`reg_width`
    sanity-checked before touching the bus) — previously unguarded, a genuine "no validity range
    check at all" gap per `src/README.md` section 1, not just a hypothetical.
  - **`import asyncio` + `from uasyncio import Lock` (both, redundantly) → `asyncio.Lock()`**, and
    `from typing import Literal, List` dropped entirely (no `TYPE_CHECKING` guard needed — the
    `endian` fix above removed the only `Literal` usage, and `List[int]` became the builtin
    `list[int]`), leaving this file with no `typing` import at all.
  - **`tests/base_classes.py` added: a minimal, behavior-faithful stand-in for
    `improved-quality/base_classes.py`'s `Lockable`**, needed because `I2CDevice` subclasses it but
    `base_classes.py` itself hasn't cleared its own `src/` promotion yet (and `improved-quality/`
    isn't on the test `MICROPYPATH`, deliberately — see CLAUDE.md). Must be reconciled or deleted
    once `base_classes.py` is itself promoted to `src/`. **Known, narrow, self-resolving side
    effect**: while both files coexist, a plain unscoped `scripts/typecheck.sh` (no arguments) fails
    with `Duplicate module named "base_classes"`, since mypy's default `files` scope
    (`improved-quality`, `src`, `tests` together) finds two same-named top-level modules with
    neither directory using `__init__.py`/namespace packages. **CI is unaffected**: its
    `lint-and-typecheck` job passes `scripts/typecheck.sh src tests` explicitly (excluding
    `improved-quality/` from the scan already, for unrelated pre-existing-findings reasons — see
    `.github/workflows/ci.yml`), which resolves `base_classes` against the `tests/` stand-in cleanly
    with no ambiguity. Not fixed via a `pyproject.toml` `exclude` (the `microdot.py` precedent)
    because that would need the full "Pre-push verification" clean-chroot pass for a collision this
    narrow and temporary; documented instead so a locally-run unscoped typecheck isn't mysterious.
    **Resolved**: `base_classes.py` (with its own runtime dependencies `config_manager.py` and
    `print_log.py`) has since been promoted to `src/` in full - see its own entry below - so
    `tests/base_classes.py` has been deleted and this collision no longer exists.
  - **Follow-up pass: deep asyncio/locking/bus-fault test coverage, a real bug found and fixed,
    and the file simplified afterward** (all while genuinely green, not just planned). Extended
    `tests/machine.py` with real RP2040 error codes (confirmed against
    `ports/rp2/machine_i2c.c`: hardware I2C only ever raises `OSError(EIO)` for a NAK/general bus
    fault or `OSError(ETIMEDOUT)` for a bus-busy/clock-stretch timeout — not the `ENODEV` this
    mock originally guessed, which is a `SoftI2C`-specific code path this driver doesn't use),
    per-operation fault injection (so one leg of a multi-step operation, e.g. the read half of
    `writeto_then_readfrom`, can fail independently of the other — modeling a transfer
    interrupted partway through), and exact-length `readfrom_mem` (real hardware always returns
    precisely `nbytes`, never a short read). 31 new tests added (60 total for this file) covering
    single- vs. multi-transfer sessions, asyncio interlock across concurrent tasks/devices
    (`asyncio.gather` + a `max_concurrent` counter, confirmed always `1`), interrupted transfers
    via both raised exceptions and real task cancellation (confirmed directly that MicroPython's
    asyncio still runs `__aexit__` via `CancelledError` propagating through `async with`, same as
    CPython), reentrant-acquisition deadlock bounded by `asyncio.wait_for` (confirmed this times
    out with `TimeoutError` and still cleans up the lock afterward), deinit/reinit mid-session,
    and buffer/slice edge cases. **Real bug found this way, not hypothetical**:
    `get_register_struct("")` (or any zero-data-field format, e.g. pad-bytes-only `"2x"`, which
    still has `calcsize() > 0`) raised an uncaught `IndexError` from indexing `struct.unpack()`'s
    empty result tuple — a genuine "never raises" contract violation for a legitimate (if
    degenerate) input, not excluded by the type contract. Fixed by checking the unpack result is
    non-empty before indexing, rather than adding `IndexError` to the existing `except ValueError`
    (clearer, and avoids conflating "malformed format" with "well-formed format, zero fields").
    Also documented (comment + regression test, not silently changed) a related MicroPython-only
    `struct.pack` quirk found via the same testing pass: it silently zero-pads/truncates a value
    or argument-count mismatch instead of raising `struct.error` like CPython — relevant to
    `set_register_struct`, which is deliberately single-value-only. With the expanded suite
    genuinely passing, the file was then simplified with zero behavior change (verified by the
    same suite staying green throughout): `get_bits()`/`set_bits()`'s duplicated byte-order
    reconstruction loop and range-guard condition extracted into shared
    `_bytes_to_int()`/`_bitfield_range_ok()`/`_bitmask()` helpers (the loop was the file's
    trickiest algorithm and worth having in exactly one place, not two copies that could drift
    the way the earlier `endian`/`lsb_first` split once did), and `I2CDevice`'s
    `readinto`/`write`/`write_then_readinto` stopped redundantly pre-resolving `end=None` to
    `len(buffer)` themselves, since `I2C`'s own methods already do that same computation one call
    down.
  - **Follow-up architecture review pass**: asked directly "is this file in good shape /
    complete / reasonable / efficient / anything missing or badly implemented" after the above
    landed. Found and fixed two more real issues, plus added two forward-compatible no-op
    parameters:
    - **Real bug, found and fixed**: `set_bits()` shifted `value` into the register without
      masking it to `num_bits` width first (`reg |= value << start_bit`) — a caller passing a
      `value` wider than the field silently corrupted the bits immediately above it instead of
      being confined to the intended field. No current caller ever passes an out-of-range value
      (same "unused by any migrated driver yet" category as the rest of the bit-field API), but
      nothing prevented a future one from doing so. Fixed by masking `value` to `num_bits` before
      the shift, reusing the existing `_bitmask()` helper.
    - **Real design flaw, found and fixed**: `writeto_then_readfrom()`/`write_then_readinto()`
      took one shared `stop` parameter applied to *both* legs of the transaction. This can
      express "two fully separate transactions" (`stop=True` on both) or "neither leg ever
      releases the bus" (`stop=False` on both, never useful) — but **not** the standard
      repeated-start register-read pattern that most I2C sensors actually use (write the
      register pointer *without* a stop, then read *with* one), since a single shared flag can't
      set the two legs differently. Fixed by splitting into independent `out_stop`/`in_stop`
      (matching the file's existing `out_start`/`out_end`/`in_start`/`in_end` naming), defaults
      unchanged (`True`/`True`) so this is a pure capability addition, not a behavior change.
      **Follow-up required, tracked here per the project owner's request**: no current caller
      uses this method yet (same category as `get_bits`/`get_register_struct`), but any future
      caller that adopts it for a real repeated-start sequence must pass `out_stop=False`
      explicitly — the default remains two separate transactions, not a repeated start.
    - **Two parameters added as pure no-ops for now**: `I2C.__init__()`/`init()` gained
      `timeout: int | None = None`, and the register-level methods
      (`get_bits`/`set_bits`/`get_register_struct`/`set_register_struct`, both on `I2C` and
      `I2CDevice`) gained `addrsize: int | None = None` — both real parameters `machine.I2C`
      itself exposes (`timeout` on the constructor, `addrsize` on `readfrom_mem`/`writeto_mem`)
      that this driver didn't surface at all. `None` omits the kwarg entirely rather than
      duplicating `machine.I2C`'s own default value in this code (which could silently drift if
      upstream ever changed its own default) — genuinely zero behavior change until a caller
      actually passes a value, via two small `_readfrom_mem()`/`_writeto_mem()` forwarding
      helpers shared by all four register-level methods.
    - **Considered and explicitly deferred, not forgotten**: `get_bits`/`set_bits`/
      `get_register_struct` still call the allocating `machine.I2C.readfrom_mem()` rather than
      the zero-copy `readfrom_mem_into()` that real `machine.I2C` also provides (relevant to
      `src/README.md` section 4's buffer-reuse requirement) — flagged but not fixed this pass
      since these methods have zero real callers today (only `asy_isl29125_driver.py`, not yet
      migrated, would exercise them frequently). Worth doing before that migration, not before.
  - **Second follow-up pass, asked directly "any more bugs/unsecured conditions/surprises
    overlooked" after the above**: found and fixed two more real, previously-uncaught exception
    gaps, both confirmed empirically against the real interpreter rather than assumed:
    - **`set_register_struct()`'s `value` was typed `int`-only, but `get_register_struct()`
      returns `int | float | bytes` — a real read/write asymmetry, not just a type-annotation
      nicety.** Confirmed directly: `struct.pack()` raises `TypeError` (not `ValueError`) for
      any value/format type mismatch (e.g. an int against a bytes-type format like `"4s"`, or
      vice versa) — previously uncaught, a genuine "never raises" violation for a call that *was*
      in-contract under the old int-only signature. Also confirmed an actual fractional float
      (not just an int auto-coerced to float, which already worked) was rejected by mypy despite
      `struct.pack` handling it correctly at runtime. Fixed by widening `value` to
      `int | float | bytes | bytearray` (the `bytearray` addition matches `writeto()`'s own
      existing buffer-type convention) and catching `TypeError` alongside `ValueError`.
    - **`writeto()`'s `str`-buffer convenience path (`bytes([ord(x) for x in buffer])`) raised an
      uncaught `ValueError` for any real Unicode codepoint above 255** — confirmed directly
      (`bytes([ord(x) for x in "aሴb"])` → `"bytes value out of range"`). The `str` type itself
      places no such restriction, so this was reachable for fully in-domain input, not a
      hypothetical. Fixed by catching the conversion's `ValueError` and returning `None`, the
      established convention for a non-hardware failure.
    - 5 new regression tests added at the time (project-wide total climbed to 183). Neither method
      has a real caller yet, so zero production impact, but both were genuinely reachable
      exception gaps, not defensive coding against something that can't happen. **Current count as
      of the file's most recent change (a comment-conciseness pass, no test/logic changes): 77
      tests for this file, 184 project-wide** (`math_helpers.py` 45 + `crc_checks.py` 62 +
      `asy_i2c_driver.py` 77) — one more than this bullet's original snapshot, from a test added in
      a later pass than the one this bullet narrates. Treat this parenthetical, not the "76/183"
      above, as the current figure; update it again the next time any test file's count changes.
- **`asy_spi_driver.py` moved to `src/`**: cleared the full `src/README.md` checklist, following the
  same methodology as `asy_i2c_driver.py`'s promotion above (see the retired
  `SPI_DRIVER_PROMOTION_PLAYBOOK.md`, which set up the process this entry executed) — but several
  SPI-specific findings turned out **not** to transfer unchanged from the I2C session, confirmed
  fresh against current MicroPython v1.28.0 source (`extmod/machine_spi.c`, `ports/rp2/
  machine_spi.c`, `ports/rp2/machine_pin.c`) rather than assumed:
  - **SPI's fault surface is materially different from I2C's, not just narrower**: real RP2040
    hardware SPI transfers (`spi_write_blocking()`/`spi_write_read_blocking()`, reached via
    `mp_machine_spi_transfer()`) have **no error return at all** once the bus is constructed - SPI
    has no ACK/NAK concept, so `write()`/`readinto()` genuinely cannot raise, full stop, not merely
    "in practice, let it propagate" the way I2C's `OSError` carve-out works. `write_readinto()` is
    the one exception, and it's a different shape entirely: `machine.SPI.write_readinto()` itself
    raises a real `ValueError` if its two buffers differ in length
    (`mp_machine_spi_write_readinto()`, shared by hardware and soft SPI alike, confirmed reachable
    from real hardware SPI's own method table, not just SoftSPI) - a caller-input mistake, not a
    hardware fault, so it's caught and turned into `None` (this project's established
    non-hardware-failure convention) rather than taking the `OSError` carve-out. **`src/README.md`
    section 2 itself was written generically for "`machine.I2C`/`machine.SPI`" as if the same
    NAK/timeout surface applies to both - flagged and, on explicit direction, updated with a
    paragraph documenting this SPI-specific finding** rather than silently left to look uniform.
  - **`write()`/`readinto()`'s declared return type was wrong, not just imprecise**: both were typed
    `int | None`, but confirmed against `extmod/machine_spi.c` that `write()`/`readinto()`/
    `write_readinto()` always return `mp_const_none` on this port (only WiPy differs) - narrowed to
    plain `None`, a real correctness-vs-documentation fix even though the runtime value never
    actually changed.
  - **The original file was confirmed literally unimportable on the real MicroPython Unix-port test
    interpreter** (`ImportError: no module named 'typing'`) before this session's fix - not a style
    nit. Its unconditional `from typing import Type` plus a bare `try: from types import
    TracebackType except Exception: pass` (exactly the anti-pattern `src/README.md` section 6 warns
    against) both had to go. Resolved with zero typing-only imports needed in the final file at
    all - `SPIDevice.__aexit__`'s override ended up typed `(self, exc_type: object, exc_val:
    object, exc_tb: object) -> bool` instead of pulling in `Type`/`TracebackType`, since it only
    ever forwards these three params to `super().__aexit__()` and never inspects them; `object` is
    always Liskov-substitutable against whatever `Lockable.__aexit__` mypy resolves (the real
    `base_classes.py` or `tests/base_classes.py`'s narrower stand-in), so this is strictly more
    robust than importing precise types would have been, not just a workaround.
  - **`deinit()`'s dead `except AttributeError`** - predicted by the I2C session's own finding entry
    above, now confirmed and removed: `machine.SPI.deinit()` is a bound method on a real
    constructed `_SPI` object, so it can't raise `AttributeError`. Unlike I2C's original bug (which
    never called the real `machine.I2C.deinit()` at all), SPI's `deinit()` already called the real
    thing; only the leftover `except` clause needed removing.
  - **`SPIDevice` converted to subclass `Lockable`**, matching `I2CDevice`'s shape - a bigger
    structural change here than I2C ever needed (`I2CDevice` already subclassed `Lockable` from day
    one). `SPIDevice.__aenter__`/`__aexit__` now wrap `super().__aenter__()`/`super().__aexit__()`
    around the extra CS-pin/`configure()` steps instead of hand-rolling the acquire/
    release-with-`RuntimeError`-swallow logic `Lockable` already provides identically. Confirmed via
    explicit sign-off given `SPIDevice` (unlike `I2CDevice`) has a live production caller
    (`asy_fram_driver.py`'s `FRAM_SPI`).
  - **Real bug found and fixed, the most severe finding of this promotion, with a live production
    caller**: `SPIDevice.__aenter__` leaked the bus lock - and left the CS pin stuck asserted -
    permanently, whenever it raised after acquiring the lock. This happens whenever `configure()`
    raises because the bus was deinitialized since the last session, or via task cancellation during
    the 1ms post-assert settle sleep: since `__aenter__` itself then raises, `async with` never
    calls `__aexit__`, so nothing ever released what `__aenter__` had already acquired. Present in
    the original file too (the hand-rolled version had the identical gap), not introduced by the
    `Lockable` refactor. A stuck-asserted CS is worse than just this device being stuck - it blocks
    every *other* device sharing the same physical SPI bus too, since CS is a shared-bus signal, not
    a per-device one. Fixed by wrapping `__aenter__`'s post-lock-acquire steps in a
    `try/except BaseException` that deasserts CS and releases the lock before re-raising. Two
    regression tests added proving the fix: one via `configure()` raising on a deinitialized bus,
    one via real task cancellation during the settle sleep (confirmed the lock and CS pin are both
    released, not leaked, in both cases; confirmed a later session can still acquire the lock
    afterward).
  - **`configure()`'s `RuntimeError`-on-unlocked-call path kept as a programmer-error guard**, not
    converted to a no-op/`None` - matching the precedent that one-time-setup/precondition violations
    may raise while ongoing operational calls use the `None`-sentinel convention, confirmed via
    explicit sign-off (`SPIDevice` has a live caller, unlike most of I2C's still-unused surface, so
    this was re-asked rather than assumed). Split into two distinct messages (`"SPI bus not
    initialized - call init() first"` vs. `"First acquire async lock!"`) since the original single
    message was misleading for the bus-not-initialized branch - a pure diagnostics improvement, zero
    behavior change.
  - **`extra_clocks` stays unimplemented** - already corrected earlier in this document (see the
    "Bus/sensor error-recovery robustness" section above): it was never a real mechanism even in the
    legacy driver, just an aspirational docstring line, and this promotion didn't resurrect it -
    holding to the same "quality/shape promotion, not a feature addition" constraint the I2C session
    held to throughout.
  - **No register/bit-field/struct helpers added** - confirmed SPI's actual shape at this bus-driver
    layer is simpler than I2C's (raw `write`/`readinto`/`write_readinto` only, no
    register/addressing concept), so no I2C-shaped `get_bits`/`set_bits`/`get_register_struct`/
    `set_register_struct` equivalents were invented for it.
  - **Protocol-driven asymmetries confirmed intentional, not inconsistencies to fix**:
    `SPIDevice.setup()` has no `probe` parameter or ACK-based device-presence check (SPI has no
    addressing/ACK concept, so no equivalent probe is possible at this layer, unlike
    `I2CDevice.setup(probe=True)`); `I2CDevice` never overrides `__aenter__`/`__aexit__` at all while
    `SPIDevice` must (CS-pin assert/deassert has no I2C equivalent); no `timeout`-equivalent
    parameter was added to `SPI.__init__`/`init()` (confirmed via `ports/rp2/machine_spi.c`'s
    constructor argument table: no timeout concept exists for SPI on this port at all, unlike I2C's
    genuine `timeout` kwarg - nothing real to surface).
  - **Cross-file naming inconsistency found in `asy_i2c_driver.py` itself during the bird's-eye scan
    (`CLAUDE.md`'s hard rule), reported rather than silently fixed, then resolved on explicit
    direction**: `I2C`'s bus-level methods (`readfrom_into`/`writeto`) used `buffer` while
    `I2CDevice`'s device-level methods already used `buf`; separately, `I2CDevice.write_then_
    readinto` used `out_buffer`/`in_buffer` (reversed word order) while the bus-level
    `I2C.writeto_then_readfrom` it forwards to - and both of `asy_spi_driver.py`'s
    `write_readinto` variants - already used `buffer_out`/`buffer_in`. Both files now consistently
    use `buf` for a single buffer and `buffer_out`/`buffer_in` for the two-buffer case; no test
    needed updating (none referenced the old names by keyword).
  - **Mock: `tests/machine.py` extended with `class SPI`**, per the standing "extend, don't
    replace" plan, plus `Pin.init()`/`.value()` readback support (previously a minimal I2C-only
    SCL/SDA stand-in with no readback at all - confirmed against `ports/rp2/machine_pin.c` that real
    rp2 `Pin.value()` does a genuine `gpio_get()` readback even for an OUT pin, so this is a
    faithful mock, not a guess). Deliberately does **not** reuse `I2C`'s `inject_fault`/`busy`/
    `nak_addresses` fault-injection shape: research confirmed real hardware SPI `write()`/
    `readinto()` have no fault path to inject at all, and the one real SPI exception
    (`write_readinto()`'s buffer-length `ValueError`) is deterministic from the buffers a test
    passes in, needing no injection mechanism to trigger.
  - **Real bug found and fixed in a second, later architecture-review pass** (asked directly "is
    this file in good shape / complete / reasonable / efficient / anything missing or badly
    implemented" after the above had already landed and shipped, same open-ended-review pattern
    the I2C file went through): `SPIDevice.__aenter__` had no guard against being reached before
    `setup()` ever ran. `setup()` is what configures `cs_pin` as an output; before that, `Pin`'s
    direction is whatever the hardware reset default is. Confirmed against `ports/rp2/
    machine_pin.c` that `Pin.value(x)` calls `gpio_put()` **unconditionally**, regardless of the
    pin's current direction - so entering before `setup()` wouldn't raise at all, it would just
    silently fail to ever assert CS on real hardware (the output-latch register gets written, but
    isn't electrically visible until direction is later set to `OUT`, which never happens without
    `setup()`). Every real caller today (`asy_fram_driver.py`) already calls `setup()` first, so
    this was a latent footgun, not an active bug - unlike the `__aenter__` lock/CS-leak bug above,
    which did have live impact. `I2CDevice` has no equivalent gap (I2C's bus pins are configured
    once in the bus constructor, not deferred to a separate per-device setup step), so this is
    genuinely specific to SPI's two-step constructor/`setup()` split, not something inherited
    unchanged from I2C's own review. Fixed by adding a `self.uninitialized` flag (reusing
    `asy_fram_driver.py`'s own `FRAM_SPI.uninitialized` naming/pattern for consistency rather than
    inventing a new convention), set `True` in `__init__` and `False` at the end of `setup()`,
    checked at the very start of `__aenter__` with a clear `RuntimeError` before anything is
    acquired - fails loudly instead of silently misbehaving.
  - **Third pass, asked directly "any more bugs/unsecured conditions/surprises overlooked" after
    the above** (same explicit-second-look pattern the I2C file went through): found no further
    driver bugs, but found two claims that were previously asserted only in prose/comments, never
    actually proven by a test - closed both:
    - The module docstring's claim that rp2 hardware SPI raises `NotImplementedError` for
      `firstbit=SPI.LSB` (sourced from `ports/rp2/machine_spi.c`) was untestable as written: the
      fake `SPI` in `tests/machine.py` silently accepted `LSB` regardless. Extended the fake's
      `init()` to reject it the same way real hardware does, then added a regression test - so a
      wrong citation here would now actually fail a test, not just look plausible in a comment.
    - No test proved CS pins of two *different* devices sharing a bus are never simultaneously
      asserted - the existing concurrency tests (`test_two_devices_sharing_a_bus_never_run_
      concurrently` etc.) only checked an abstract `max_concurrent` counter, not the actual
      hardware signal the whole locking scheme exists to protect. Added a test checking both
      devices' real `Pin.value()` state directly during a concurrent `asyncio.gather`.
  - **43 tests added** (`tests/test_asy_spi_driver.py`; project-wide total climbs to 227 = 45
    `math_helpers.py` + 62 `crc_checks.py` + 77 `asy_i2c_driver.py` + 43 `asy_spi_driver.py`),
    written before the refactor and run against the original file first (per the explicit
    tests-first instruction this pattern is based on) - which is how the `typing` import bug above
    was caught concretely, not just reasoned about. Covers: init/deinit and real-hardware-deinit
    idempotency, `configure()`'s three distinct raise paths (`RuntimeError` x2, plus
    `NotImplementedError` for `firstbit=LSB`), `write`/`readinto`/`write_readinto` forwarding and
    the one real raise path (including zero-length buffers and buffer-length mismatches in both
    directions), a dedicated regression test proving the disconnected-wire/no-ACK case is
    genuinely undetectable (zero-filled data back, no exception, not just an untested claim), CS
    pin assert/deassert sequencing verified via real `Pin.value()` readback across every exit path
    (normal, exception inside session, double-exit/pre-released lock, task cancellation,
    `__aenter__` failure itself, and now also entering before `setup()`), CS pins of two different
    devices proven never simultaneously asserted, `configure()` re-applied fresh every session
    (confirmed correct behavior, not a bug, since the bus may be shared with a
    differently-configured device - evaluated during the architecture-review pass and deliberately
    left unchanged), deinit/reinit mid-session, asyncio interlock (2 and 4 concurrent devices, plus
    the same device from two concurrent tasks), reentrant-acquisition deadlock bounded by
    `wait_for`, and both `__aenter__` bug fixes (lock/CS-leak, and the setup()-ordering guard).
  - **Not fixed, flagged for a future pass**: `FRAM_SPI.set_write_protected()`/
    `get_write_protected()` (in `asy_fram_driver.py`, not itself promoted this session) have zero
    real callers today - same category as several of I2C's still-unused register-helper methods,
    not touched.
  - **Baseline verified, no regression**: `improved-quality/`'s lint finding count was 320 at this
    session's start (unchanged from the count recorded at the end of the I2C session above,
    confirmed before touching anything), and 317 after this file's promotion - a net **decrease** of
    exactly the 3 pre-existing findings this file itself had, not a regression anywhere else.
  - **Fourth pass, a full re-walk of `src/README.md`'s checklist after the PR was already open**:
    found one real docstring inaccuracy, flagged and fixed on explicit direction rather than
    silently - the module docstring attributed `configure()` to `SPIDevice` (it's an `SPI` method,
    only ever called *from* `SPIDevice.__aenter__`) and attributed the `firstbit=SPI.LSB`
    `NotImplementedError` to `SPI.__init__()/init()`, which take no `firstbit` parameter at all -
    only `configure()` does. Also tightened the module docstring to essentials and capped every
    function's comments at 3 lines, on request; zero behavior change, verified via a full
    mypy/lint/test re-run before pushing.
  - **Follow-up needed for the later refactor stages, as with `asy_i2c_driver.py` above**: this
    file's own contract deliberately lets several methods raise rather than return `None` -
    `SPI.__init__()`/`init()` (`ValueError` for a bad pin/port number), `SPIDevice.__init__()`
    (same, via its own `Pin(cs_pin)`), and `configure()` (`RuntimeError` for an uninitialized or
    unlocked bus, `NotImplementedError` for `firstbit=SPI.LSB`) - all deliberate "fail loudly"
    programmer-error guards, not swallowed into `None`. Today's only caller
    (`asy_fram_driver.py`'s `FRAM_SPI`) doesn't wrap any of these in a `try/except` - fine today
    since none of these should ever trigger in correct, already-`setup()`'d production code, but
    not verified against every call site the way `src/README.md` section 2 requires for the I2C
    `OSError` carve-out. As the refactor adds more `SPIDevice` consumers, each one's own upstream
    handling must be checked so a genuine one-time-setup failure fails loudly at boot (as intended)
    rather than an unrelated later call somehow reaching one of these raises uncaught and crashing
    the task supervisor - matching the same "nothing may ever silently slip through uncaught" hard
    rule already recorded under "Bus/sensor error-recovery robustness" above.
- **Test infrastructure gap found and fixed, while adding `crc_checks.py`'s tests**:
  `scripts/test.sh`'s `MICROPYPATH="src:tests"` silently shadowed every frozen-Python stdlib
  module (`asyncio` included) for every test file — invisible until now because `math_helpers.py`
  (previously the only tested `src/` file) doesn't use `asyncio`. MicroPython's `MICROPYPATH` env
  var *replaces* the interpreter's default `sys.path` rather than extending it, dropping the
  `.frozen` path entry that resolves frozen-in modules. Fixed by adding `.frozen` to the path
  (`MICROPYPATH="src:tests:.frozen"`), verified against the real interpreter with both
  `test_crc_checks.py` and `test_math_helpers.py` passing, no regression. Separately confirmed but
  explicitly **not** fixed (out of scope for this session): `typing` is not an importable module
  on this same Unix-port build at all — most of `improved-quality/`'s files do an unconditional
  `from typing import ...`, which would fail identically if actually executed under this
  interpreter; only `print_log.py`/`base_classes.py` already guard part of their typing imports
  behind `if TYPE_CHECKING:` (for a different reason — circular-import avoidance, not this gap).
  This is a latent, codebase-wide issue worth addressing when those files go through their own
  `src/` promotion, not something to patch piecemeal now. Also worth flagging for future sessions
  in this same sandbox: the globally pre-installed `ruff`/`mypy` here were stale (0.15.8/1.19.1)
  compared to what a fresh `uv sync` actually installs (0.15.21/2.3.0, matching CI) — the
  chroot-based pre-push verification caught this via a mypy finding-count mismatch (146 vs. 144
  errors in unrelated pre-existing `improved-quality/` files) that had nothing to do with the
  actual change being verified.
- **Timing-value changes are confirmed intentional, not drift**: the project owner tested and found
  both changed delays — `asy_scd30_driver.py`'s `_read_register()` inter-command delay (0.005s →
  0.05s) and `asy_sgp40_driver.py`'s initial serial-number-read delay (10ms → 3ms) — to produce
  more stable operation. No further action needed; keep these values, and prefer measuring rather
  than assuming when tuning similar delays elsewhere in the refactor.
- **Confirmed real bug fixes already present in `improved-quality/`** (good evidence the refactor
  is improving correctness, not just style) — worth knowing these exist so they aren't
  accidentally reintroduced: a `NameError`-causing typo in the legacy FRAM driver's write-protect
  pin setup (`_wp_pin` used instead of `self._wp_pin`); a legacy `BMP3XX_I2C.setup()` that uses
  `await` inside a non-`async def` (a literal compile-breaking defect — worth confirming whether
  this method is ever actually reached on deployed units, i.e. whether it's dead code today); a
  legacy SGP40 VOC-algorithm FRAM serialization bug where `m_mox_model_sraw_std` was never
  included in the packed/restored fields, so restore-from-FRAM silently never recovered that value;
  and a handful of smaller `api_helpers.py`/`async_connect.py`/`captive_dns.py`/`asy_udp_socket.py`
  fixes for `None`-guard crash paths and an unbound-local variable on an unhandled branch.
- **Per-sensor vs. device-level config — not a contradiction, just an unfinished third tier**: see
  the "Target model" note under "Handle device / sensor / functional config storage separately"
  above — per-sensor config is done, the remaining gap is giving the currently-shared
  network/Neopixel config in `sensortask-wozi.py` its own clearly-scoped global home instead of one
  ad hoc `ConfigManager` instance.
- **`base_classes.py`, `config_manager.py`, and `print_log.py` all moved to `src/` together**:
  `base_classes.py` was the requested target, but its two runtime dependencies (not FRAM-related,
  not `TYPE_CHECKING`-only - unlike its `AsyFramManager` reference) had to go through the same
  checklist alongside it, on explicit direction from the project owner, or `SensorReader`/
  `SensorReaderConfig` would only ever be testable against hand-written stand-ins for their own
  logging/config storage. Resolves the "latent, codebase-wide `typing` import gap" flagged in this
  same section above as future work for exactly these two files.
  - **Two real, previously-undetected bugs found and fixed in `config_manager.py`** - both existed
    unchanged in `base_classes_old.py` too, and neither had ever actually been exercised end-to-end
    before this session's tests (see below for why):
    1. `cfg_from_str()`/`str_cfg()`'s `cfg_vals[1:-2]` (should be `[1:-1]`) stripped one character
       too many off the end of the `"|...|"`-wrapped schema string - `str_cfg()` never surfaced this
       (it only ever reads the substring *before* the first `:{`, which the extra truncation never
       reaches), but `cfg_from_str()` needs the full, well-formed JSON body: the truncation always
       dropped the final `}`, so `json.loads()` always raised on malformed/unbalanced braces and
       `cfg_from_str()` always returned `{}` - for every real schema string, not just an edge case.
       Since `ConfigManager.__init__()` bails out immediately when `cfg_from_str()` returns empty
       (`"- Defaults are empty, config is not valid!"`), this meant **`ConfigManager.valid` could
       never become `True` for any real caller in current `improved-quality/` code** - every
       `SensorReaderConfig`-based sensor's persistent config storage has been silently, completely
       non-functional. Never noticed because nothing in `improved-quality/` runs on real hardware
       end-to-end yet (see the "Cross-file wiring is currently incomplete" finding above) and no
       tests existed against this file before now. Fixed by correcting both slices to `[1:-1]`
       (verified by hand-reconstructing the JSON both ways - `[1:-2]` produces unbalanced braces,
       `[1:-1]` parses correctly - and confirmed no observable behavior of `str_cfg()` changes,
       since its truncation bug was already inert).
    2. `check_cfg_get_default()`'s self-check of a schema's `"special"` sentinel value (used for
       fields like `asy_scd30_driver.py`'s real `AmbPres`, `special: 0` outside its physical
       `700-1400` hPa range, meaning "compensation disabled") called
       `type_or_range_error(special_val, defaults, check_special=use_value)` with `use_value=False`
       in exactly the case being checked - forcing the special value through the *full* min/max
       range check instead of letting it take its own "equals the special sentinel, auto-valid"
       shortcut. This made `check_cfg_get_default()` judge `AmbPres`'s real, already-in-use schema
       constant as invalid, which (masked by bug #1 above always returning empty defaults first)
       had never actually been reached either. **Confirmed with the project owner which side was
       wrong** (the validation, not the schema - a special sentinel is deliberately meant to fall
       outside the normal range, that's the whole point of having one) rather than guessing. Fixed
       by always passing `check_special=True` to this self-check; the ordinary (non-special)
       default-value path is unaffected since `type_or_range_error`'s special-bypass branch only
       ever fires when the checked value actually equals the special sentinel.
  - **The pre-existing, unconditional `from typing import ...` in all three files - including real
    `TypeVar(...)` calls executed at class-body evaluation time in `base_classes.py`
    (`Lockable.LockableType`, `SensorReader.MeasDataType`) - would have crashed immediately on
    import under the real MicroPython interpreter**, confirmed the same way `asy_i2c_driver.py`'s
    promotion first found this class of bug. Fixed with the same `try/except ImportError:
    TYPE_CHECKING = False` + `if TYPE_CHECKING:` pattern already established there, extended to
    cover module-level `TypeVar(...)` definitions (moved out of the `Lockable`/`SensorReader` class
    bodies, since the actual value only matters to mypy, never at runtime) and `config_manager.py`'s
    `WriteValidity` type alias (a real module-level assignment, not just an annotation, so it also
    has to live inside `if TYPE_CHECKING:` rather than just being written with a string-quoted
    annotation). Also modernized `from uasyncio import Lock` → `import asyncio` / `asyncio.Lock()`
    throughout, matching `asy_i2c_driver.py`/`asy_spi_driver.py`'s precedent, and switched
    `typing.Dict`/`List`/`Tuple` to the builtin generics (`dict`/`list`/`tuple`) per ruff's own
    `UP006`/`UP035` rules, which are real, always-available runtime names needing no
    `TYPE_CHECKING` guard at all (unlike `Any`/`Literal`/`NamedTuple`/`TypeVar`, which do).
  - **Cross-file consequence of giving `Lockable.__aexit__` its first-ever precise real type**:
    `asy_spi_driver.py`'s `SPIDevice.__aexit__` override was typed with loose `object` parameters,
    specifically because `Lockable.__aexit__` previously only existed as `tests/base_classes.py`'s
    narrow stand-in (see that entry above) - its own comment claimed this was Liskov-safe "either
    way." Once the real, precisely-typed `Lockable.__aexit__` existed, forwarding those
    `object`-typed locals into `super().__aexit__(...)` no longer type-checked. Found via this
    session's own bird's-eye-view scan across `src/` (see CLAUDE.md's hard rule) and confirmed with
    the project owner before touching a file this session wasn't otherwise reviewing. Fixed by
    retyping `SPIDevice.__aexit__`'s three parameters to match `Lockable.__aexit__` exactly (same
    `TYPE_CHECKING`-guarded `TracebackType` import pattern), zero behavior change.
  - **FRAM stayed the one deliberately-deferred boundary at first pass, as expected going in**:
    `asy_fram_manager.py` hasn't itself cleared `src/` promotion, so neither `SensorReader`'s
    FRAM-backed path nor `print_log.py`'s `PrintLogHistStore._write()`/`_read()` were exercised for
    real at first - only the in-memory paths were. mypy's scoped `src tests` CI run (which excludes
    `improved-quality/`, so `asy_fram_manager` isn't on its search path) would otherwise newly fail
    on the `TYPE_CHECKING`-only `AsyFramManager` import both files had; added a
    `[[tool.mypy.overrides]]` entry for module `asy_fram_manager` with `ignore_missing_imports =
    true` in `pyproject.toml` rather than suppressing the call sites individually - the plain
    unscoped run already resolved it fine (`improved-quality/` is walked directly), so this
    override only matters for the scoped case. **This `pyproject.toml` change has not yet been run
    through the "Pre-push verification" clean-Ubuntu-24.04-chroot recipe** (CLAUDE.md) - low risk
    (a single, well-documented mypy override, no new dependencies or build-tool changes) but
    flagged here rather than silently skipped.
  - **`print_log.py`'s FRAM boundary since mocked and tested, as part of that file's own dedicated
    review pass** (`base_classes.py`'s `SensorReader` FRAM-backed path is a separate file/pass and
    stays deferred): `PrintLogHistStore` only ever calls `AsyFramManager.get_chunk()` and, on the
    chunk it returns, `get_buffer()`/`write_into()`/`read_into()` - not the real allocator/CRC/
    dual-copy-redundancy machinery `asy_fram_manager.py` actually implements underneath those calls.
    `tests/_fram_mock.py` fakes just that narrow surface (see `tests/README.md` for the full
    rationale), and `print_log.py`'s own `AsyFramManager` `TYPE_CHECKING` import was replaced with
    two local `Protocol`s (`_FramManager`/`_FramChunk`) describing exactly that surface, so the mock
    satisfies it structurally with no inheritance relationship to the real classes needed - this
    also means `print_log.py` no longer needs the `asy_fram_manager` mypy override above at all
    (only `base_classes.py` still does).
    - **A genuine parameter-contravariance conflict surfaced while typing this, caught by running
      the *unscoped* mypy pass (not just the scoped CI one) before considering this done**: the real
      `AsyFramChunk.write_into()`/`read_into()` (in `asy_fram_manager.py`) each narrow their `buf`
      parameter to that class's own concrete buffer subtype (`AsyFramChunkBuffer`), which is fine
      for `get_buffer()`'s covariant *return* but makes the real class structurally incompatible
      with a `_FramChunk` protocol whose `write_into`/`read_into` declared a shared, precise buffer
      protocol type in *parameter* position (contravariant) - mypy correctly flagged this as a new,
      real error in `base_classes.py`'s `SensorReader.__init__` (`PrintLogHistStore(fram, ...)`)
      under the unscoped run only (scoped CI stayed green throughout, since `asy_fram_manager` isn't
      resolved there at all). Fixed by typing `write_into`/`read_into`'s `buf` parameter as `Any` in
      the protocol instead: this file never inspects `buf` itself, only round-trips whatever its own
      `get_buffer()` call just returned, so the precise buffer type was never part of the real
      contract worth enforcing there. Re-verified 0 new errors anywhere after the fix (unscoped
      finding count dropped, from 157 to 149, entirely from `print_log.py` no longer being typed
      against the real `AsyFramManager`/`AsyFramChunk` classes at all).
    - **`MockFramBacking` (in `tests/_fram_mock.py`) deliberately simulates data surviving a reboot,
      not just a single read/write round-trip**: it tracks which offsets have actually been written
      (not just their bytes), and a test constructs a second `MockAsyFramManager` around the same
      `MockFramBacking` instance, replaying the same `get_chunk()` call sequence - landing on the
      same offsets, same as the real bump-pointer allocator would - to prove data set by one
      `PrintLogHistStore` instance is recovered by a completely fresh one. This directly exercises
      the feature's whole stated purpose ("Trace-log error codes inside FRAM, surviving a reboot",
      above), not just that the mock's read/write plumbing works in isolation.
    - **Remove `tests/_fram_mock.py` (and the `PrintLogHistStore` tests built on it in
      `tests/test_print_log.py`) once `asy_fram_manager.py` itself clears its own `src/` promotion
      checklist** and a real, tested `AsyFramManager` becomes available under `tests/` instead - at
      that point the same tests should be re-pointed at the real class rather than kept alongside
      it.
  - **A dedicated follow-up pass on `print_log.py` (structure/leanness/exception-safety review,
    requested directly rather than moving straight to the next file) found and fixed a real
    exception-safety gap, plus two leaner-but-safe simplifications**:
    - **Real bug: `PrintLogHistStore._write()`/`_read()`'s `try:` block started too late.**
      `get_buffer()`/`get_data_buf()` (both methods) and, in `_read()`, `read_into()` too, were all
      called *before* the `try:` began - only the `struct.pack_into`/`struct.unpack_from`/
      `write_into()` calls were actually protected. Since `asy_fram_manager.py` isn't itself
      audited yet, a raise from any of those unprotected calls would have propagated straight out
      of `_write()`/`_read()`, breaking the "never raises" contract these two methods exist
      specifically to uphold. Found via a systematic, line-by-line audit of every call in the file
      (not just the FRAM path - `PrintLog`/`PrintLogHistory`'s own methods were checked too; the
      only other raise-shaped surface is `err`/`wrn`/`one`/`evt`/`all`/`err_s`/`wrn_s`'s
      `print(*args, **kwargs)` forwarding, which can raise `TypeError` for a genuinely invalid
      kwarg name - left as-is, since every real caller in this codebase passes only valid
      `print()` kwargs and wrapping it would silently hide an actual caller bug rather than guard
      against a reachable operational failure). Also found: `PrintLogHistStore.__init__`'s
      `fram.get_chunk(...)` call was completely unguarded, the same unaudited-FRAM-boundary risk
      at construction time. Fixed by widening `_write()`/`_read()`'s `try:` blocks to cover their
      entire bodies and adding the same `try`/`except Exception` around `__init__`'s `get_chunk()`
      call (an unexpected raise there now degrades to `self.fram = None`, same as the already-
      handled "out of memory" `None` return). Verified via `tests/_fram_mock.py`'s new
      `.broken_buffer` fault (a `get_buffer()` that "succeeds" but returns a buffer whose
      `get_data_buf()` is `None`, making `struct.pack_into`/`struct.unpack_from` raise
      `TypeError`) - this reproduces the exact bug shape and is now caught cleanly by both methods.
    - **Simplification: `print_log.py`'s separate `_FramBuffer` Protocol was a redundant
      duplicate of `base_classes.LockableBuffer`'s own two methods** (`get_buf()`/`get_data_buf()`).
      Verified directly (not assumed) that importing `LockableBuffer` under `TYPE_CHECKING`
      instead doesn't create a circular-import problem for mypy - scoped and unscoped runs both
      stay clean, 0 new errors in either file. Folded away; `_FramChunk.get_buffer()` now returns
      `LockableBuffer` directly.
    - **Simplification: `PrintLogHistory.hl` (set from `history_length` in `__init__`) was dead
      state** - nothing anywhere in the repo (including `base_classes_old.py`, where the same line
      also exists unused) ever reads `self.hl`; every real use is `len(self.history)` instead.
      Removed.
    - **`tests/_fram_mock.py` gained fault injection for every simulated FRAM failure mode**:
      `MockAsyFramManager(raise_on_get_chunk=...)` alongside the existing `out_of_memory=...`, and
      per-chunk `.raise_on_get_buffer`/`.broken_buffer`/`.raise_on_write`/`.write_returns_false`/
      `.raise_on_read`/`.read_returns_false` flags, settable directly on the `_MockFramChunk`
      instance a `PrintLogHistStore` exposes as its own `.fram` (tests narrow `store.fram`'s type
      from the production `_FramChunk` Protocol to the concrete mock via
      `assert isinstance(store.fram, _MockFramChunk)`, keeping the tests themselves fully typed
      rather than reaching for `# type: ignore`). A `.corrupt(bytes)` helper (write wrong-length
      data directly, bypassing `write_into()`, to make a later `struct.unpack_from()` raise) was
      designed, tried, and deliberately **not** kept: `get_buffer()` always hands back a
      freshly-sized buffer derived from the same `len(history)` used to write it, so struct's own
      length check can only ever fail via `get_buffer()` itself misbehaving - already covered by
      `.broken_buffer` - never via what was previously persisted at that offset. Confirmed this
      empirically (not just by reasoning about it) before removing it, and along the way confirmed
      a genuine MicroPython/CPython behavioral difference worth recording: resizing a `bytearray`
      via slice assignment while a `memoryview` is exported over it does **not** raise
      `BufferError` on MicroPython's Unix port the way it does on CPython - it silently resizes,
      leaving the existing `memoryview` referencing stale state. Not load-bearing for anything in
      `src/` today, but worth keeping in mind for any future code that resizes a buffer with an
      outstanding `memoryview` over it.
    - Added 18 new tests (21 -> 39 in `tests/test_print_log.py`; 317 -> 335 tests repo-wide):
      exact-boundary `errno`/`wrnno` values for both the error and warning sub-ranges (previously
      only tested well past the boundary, not exactly at it), an `err_count` cap-transition test,
      a `history_length=0` construction edge case (confirmed safe first via a standalone script
      under the real MicroPython interpreter: bounded-`deque` `append()`/`extend()` never raise on
      overflow, even at `maxlen=0`), and one test per FRAM fault-injection mode above, including
      `setup()`'s both-paths-fail branch and an `err_s()`-survives-a-write-failure test proving
      in-memory state still updates even when persistence silently fails underneath it.
  - **`tests/base_classes.py` (the `Lockable` stand-in) deleted**, its documented
    `scripts/typecheck.sh`-with-no-arguments "Duplicate module" collision resolved along with it;
    `asy_i2c_driver.py`/`asy_spi_driver.py` now resolve `Lockable` against the real
    `src/base_classes.py`. `tests/test_base_classes.py`, `tests/test_config_manager.py`, and
    `tests/test_print_log.py` added (84 tests total), all running under the real MicroPython
    Unix-port interpreter alongside the existing suites - full repo run: 311 tests passing.
  - **Baseline verified, no regression**: CI-scoped `scripts/typecheck.sh src tests` was already
    fully clean before this session (0 issues, 12 files) and is fully clean after (0 issues, 17
    files, with the override above); CI-scoped `scripts/lint.sh` (`ruff check src tests`) stays
    fully clean. Unscoped `mypy`'s previously-blocking "Duplicate module named base_classes" crash
    is gone; the unscoped `ruff check improved-quality src tests` finding count dropped from 317 to
    265 - entirely attributable to these three files' lines leaving `improved-quality/`'s scan, not
    to any fix within `improved-quality/` itself.
  - **A second, requested-directly re-review pass on `print_log.py`** ("any oversights, bugs,
    strange or unexpected behaviors, uncaught exceptions or conditions with yet no unit test")
    found and fixed two more real gaps, neither an exception this time - both logic bugs:
    - **Real bug: `_store_err()`/`reset()`'s "not initialized yet" guard's `return` was
      conditioned on `self.level`, not just on `self.initialized`.** The code read
      `if not self.initialized and self.level > _LOG_OFF: print(...); return` - a single `if`, so
      with logging *off* (`self.level == _LOG_OFF`, the common production default) the condition
      is `False` even when genuinely uninitialized, and execution fell through to `_write()`
      anyway. For `PrintLogHistory` this is harmless (`_write()` is a no-op returning `True`), but
      for `PrintLogHistStore` it meant calling `err_s()`/`wrn_s()`/`reset()` before `setup()` had
      loaded (or established) the persisted state would silently overwrite real FRAM-persisted
      history with a freshly-constructed, not-yet-loaded in-memory default - exactly backwards from
      the guard's own intent, and only masked by logging being off. Confirmed reachable in this
      repo's own real caller: `base_classes.py`'s `SensorReader.__init__` never calls
      `self.pr.setup()` itself (by design - `__init__` can't be `async`); the required call lives in
      each sensor driver's own async setup routine (e.g.
      `improved-quality/asy_sgp40_driver.py:113`'s `await self.pr.setup()  # required for all logged
      warnings and errors`) - a driver author forgetting that call would previously have failed
      silently whenever `level` was off instead of every time, an inconsistent, log-level-dependent
      failure mode. Fixed by splitting the `return` out from the `print`, so the guard now always
      returns when uninitialized regardless of `self.level`; only the diagnostic message is
      level-gated. Verified directly against the mock FRAM backing (`manager.backing._written_offsets`
      stays empty across an unset-up `err_s()`/`reset()` call, where it previously gained an entry).
    - **Real bug: `PrintLogHistory.__init__` didn't clamp `history_length`.** A negative value (a
      valid `int`, so within what `set_level()`'s own "clamp, don't reject" convention elsewhere in
      this same file already treats as normal input) reaches `deque([_NO_ERR] * history_length,
      history_length)` - confirmed directly against the real MicroPython Unix-port interpreter that
      a negative `maxlen` raises `ValueError` there (`deque([], -1)` also raises), breaking the
      constructor for a typed-valid input the file's own sibling method already knows how to handle
      gracefully. Fixed by clamping `history_length = max(history_length, 0)` before first use,
      matching `set_level()`'s convention.
    - **6 new tests** (39 -> 45 in `tests/test_print_log.py`; 335 -> 341 repo-wide): a
      negative-`history_length`-is-clamped test; an `err_s()`/`reset()`-before-`setup()`-with-
      logging-off test at the `PrintLogHistory` level (in-memory counting/recording still happens);
      the same two scenarios again at the `PrintLogHistStore` level, asserting nothing reaches the
      mocked FRAM backing; and a `history_length=0` construction test through the full FRAM
      write/read round-trip (confirmed directly this doesn't crash `get_buffer()`/`pack_into`/
      `unpack_from` at either end - the struct format collapses to just `"H"`).
    - No other uncaught-exception or untested-branch gaps found on this pass: re-walked every
      method again (`PrintLog`'s five logging methods, `set_level`, `PrintLogHistory`'s `setup`/
      `_store_err`/`err_s`/`wrn_s`/`reset`/`get_log`, `PrintLogHistStore`'s `__init__`/`setup`/
      `_write`/`_read`) against both normal and boundary/malformed-but-typed input; nothing else
      surfaced.
  - **A third pass, this time validating `print_log.py` paragraph-by-paragraph against
    `src/README.md`'s full promotion checklist** (rather than a general "find bugs" sweep) surfaced
    one more real, if latent, correctness finding under section 1 ("correct against real
    documentation"), plus a couple of zero-behavior-change improvements under sections 4/8:
    - **Real (if inert-until-now) finding: a bare `struct` format string (no byte-order prefix) does
      not default to `"<"` on MicroPython.** Confirmed directly against both the MicroPython
      1.28.0 docs and the real Unix-port interpreter: a no-prefix format string defaults to `"@"`
      (native byte order **and** native alignment/padding) - `struct.calcsize("BH")` (no prefix) is
      `4` (one padding byte inserted before `H`), matching `"@BH"`, not `"<BH"`'s `3`. This is easy
      to miss since MicroPython's own struct docs mostly describe themselves as "a subset of
      CPython's" without spelling out this default explicitly, and it also doesn't support `"="`
      at all (`calcsize("=HBBB")` raises `ValueError: bad typecode`, unlike CPython). For
      `print_log.py`'s own field order (one `"H"` first, then all `"B"`s), `"@"` vs `"<"` produced
      byte-identical layouts either way - `"H"` is always aligned at offset `0`, and `"B"` fields
      never need alignment - so this was never an actual bug in the shipped behavior, and nothing
      real depends on today's exact bytes yet (`python/`'s currently-deployed codebase has no
      equivalent FRAM-history feature at all; only `improved-quality/base_classes_old.py`, not yet
      itself promoted, shares this exact pre-existing pattern). Still fixed to an explicit `"<H"`/
      `"B"*n` (little-endian, no padding) rather than left as a coincidentally-safe implicit
      default, since reordering the fields later (`"B"*n` before `"H"`, say) would have silently
      introduced real padding under the old bare format. Added a dedicated regression test
      asserting the exact on-the-wire byte layout after `_write()`.
    - **Two zero-behavior-change improvements** (section 8: general improvement pass, section 4:
      resource discipline): `"B" * len(self.history)` was rebuilt - a fresh string allocation - on
      every single `_write()`/`_read()` call, even though `len(self.history)` never changes after
      construction (`deque`'s `maxlen` is fixed for the object's lifetime); now cached once as
      `self._hist_fmt` in `__init__`, alongside a `PrintLogHistStore`-level `_HDR_FMT`/`_HDR_SIZE`
      pair (`"<H"`/`2`, computed once at class-definition time) replacing the repeated inline
      `struct.calcsize("H")` calls. Separately, the eight identical `if self.level > _LOG_OFF:
      print(...)` diagnostic gates scattered across `_store_err`/`reset`/`PrintLogHistStore.__init__`/
      `PrintLogHistStore.setup` were folded into one `_diag()` helper on `PrintLogHistory` - purely
      DRY, single source of truth for the gating threshold, verified behaviorally identical (full
      suite passes unchanged) rather than assumed.
    - **Confirmed, not just assumed, one subtlety while re-reading every `return` by eye (section
      7)**: `_write()`'s `return bool(await self.fram.write_into(buf))` casts to `bool` explicitly,
      while `_read()`'s equivalent `if not await self.fram.read_into(buf): return False` doesn't.
      This is correct, not an inconsistency: `_write()` forwards `write_into()`'s raw return value
      as its own, so the cast is what actually makes its `-> bool` contract hold given
      `asy_fram_manager.py` isn't itself audited to guarantee a real `bool`; `_read()` never
      forwards `read_into()`'s value directly (it always re-derives its own `True`/`False`), so
      there's nothing to cast there.
    - Added 1 new test (45 -> 46 in `tests/test_print_log.py`; 341 -> 342 repo-wide) for the
      explicit byte-order layout above. Every other section of the checklist (0, 2-3, 5-6, 9-14)
      was re-checked against the current file and confirmed already satisfied - typing, exception-
      safety, non-blocking behavior, and test coverage needed no further changes this pass.
  - **A paragraph-by-paragraph pass validating `config_manager.py` against `src/README.md`'s full
    checklist** surfaced one real bug (section 2/10) and confirmed several suspects as non-issues:
    - **Real finding: `get_bool_values()`'s conversion-failure detection was silently broken.**
      `get_int_values`/`get_float_values`/`get_str_values` all rely on `int()`/`float()`/`str()`
      raising on a genuinely wrong-typed stored value, caught by the surrounding `try/except` to
      return `None` - but `bool(v)` **never raises for any input** (`bool("notabool")` is `True`,
      no exception), so a corrupted/wrong-typed on-disk value for a `bool` field (e.g. from a
      partial write) silently coerced to `True`/`False` instead of correctly signaling invalid data
      like its three siblings. Fixed by replacing the `bool(v)` comprehension with an explicit
      `isinstance(v, bool)` guard clause (no `try` needed - `isinstance` can't raise, matching
      section 11's preferred guard-clause-over-try shape) that rejects the whole read if any stored
      value isn't actually a `bool`. Zero behavior change for any correctly-typed value already in
      a config file - only the previously-mishandled corruption case changes, from silent wrong data
      to the correctly-signaled `None`.
    - **Confirmed, not assumed: `make_dict()`'s repr()-string parsing is the *only* option here, not
      an avoidable hack.** Tested directly against the real MicroPython Unix-port interpreter:
      `namedtuple` instances have neither `_fields` nor `_asdict()` (both raise `AttributeError`) on
      MicroPython, unlike CPython - so parsing `repr(nt)` for field names is required, not a fragile
      shortcut that should be replaced.
    - **Confirmed, not assumed: local variable annotations referencing `TYPE_CHECKING`-only names
      are safe unquoted at runtime.** `data: dict[str, Any] | None = ...` and
      `dict_results: WriteValidity = ...` both reference names that only exist when `TYPE_CHECKING`
      is `True` (always `False` at runtime) - verified directly on the real interpreter that
      MicroPython does not evaluate local variable annotations at runtime (unlike CPython's module/
      class-level annotations), so this doesn't raise `NameError`, extending section 6's existing
      "annotations aren't evaluated" finding (previously confirmed only for parameter/return
      position) to local variable annotations too.
    - **Considered and ruled out as non-issues**: `type_or_range_error`'s `bool` branch has no
      `special`-sentinel handling, unlike `int`/`float`/`str` - looked like an inconsistency, but
      `special` exists to bypass an otherwise-enforced min/max range, and a 2-valued `bool` has no
      "outside the range" concept to escape, so this is architecturally sound (and unreached by any
      current driver schema: only `asy_scd30_driver.py`'s `SelfCal` bool field exists, with
      `special: null`). Also considered `ConfigManager.__init__`'s `json.dump` catching only
      `OSError` while `write_config`'s catches `(OSError, ValueError)` for the same underlying call
      - not a gap: `write_config`'s broader tuple is there because `json.load` shares that function's
      *same* try block, while `__init__`'s write-only try block genuinely only needs `OSError`.
    - **Documented two inherent quirks with a one-line comment each (section 1's "document, don't
      silently fix" for a non-bug quirk), previously unstated**: `str_cfg`/`cfg_from_str`'s schema
      parsing assumes `"||"` never appears inside a field's own value (true for every current driver
      schema); `make_dict`'s repr-parsing assumes no field's own `repr()` contains `"("` (true while
      every real namedtuple field is a scalar).
    - Added 3 new tests (40 -> 43 in `tests/test_config_manager.py`; 342 -> 345 repo-wide): a
      regression test for the `get_bool_values` fix (a corrupted-on-disk-type case correctly returns
      `None`), plus `get_float_values`/`get_str_values` conversion-failure-path parity tests that
      `get_int_values` already had but its siblings didn't.
  - **A dedicated follow-up pass expanding `config_manager.py`'s test coverage** (requested
    directly: instantiation, validation, sentinel values, corrupted/missing config, file/I/O
    errors, edge cases, parameter combinations) added 39 new tests (43 -> 82 in
    `tests/test_config_manager.py`; 345 -> 384 repo-wide), all empirically verified against the
    real MicroPython Unix-port interpreter before being written down (not assumed), covering:
    - `type_or_range_error`/`check_cfg_get_default` parameter combinations previously untested:
      missing/wrong-typed `min`/`max` bounds, a malformed (wrong-typed) `special` value poisoning
      the check regardless of `check_special` (real behavior, but unreachable through either real
      caller since `check_cfg_get_default`'s own self-check already rejects such a schema first),
      `check_special=False` crossed with a well-typed `special`, the zero-length string boundary,
      every additional `bool` wrong-type case, an extra/unexpected schema key, a field with both a
      real `def` and a reachable `special` together, and a bool special-only field.
    - Three confirmed-not-assumed parsing quirks, each pinned with a regression test showing the
      *actual* (measured) behavior rather than an idealized one, per section 1's "document, don't
      silently fix" for a non-bug quirk: `str_cfg("||")` returns `['']` while `cfg_from_str("||")`
      returns `{}` for the same degenerate input; a duplicate schema field name is kept twice by
      `str_cfg` but collapses to the last occurrence in `cfg_from_str`; and - a real, if
      unreached, silent-data-corruption case - a str-type field whose own default value contains
      literally `"||"` has that substring itself corrupted by `cfg_from_str`'s blind
      `.replace("||", ", ")` (confirmed directly: `"a||b"` becomes `"a, b"` in the parsed default),
      not just misparsed. Also pinned `make_dict`'s nested-tuple-field quirk (a field whose own
      value's `repr()` contains `"("` silently drops every field after it, confirmed directly:
      `Nested((1, 2), 3)` loses field `b` entirely, no exception).
    - `ConfigManager.__init__` scenarios previously untested: a valid-JSON-but-non-dict file
      (array, bare scalar), a genuinely empty (0-byte) file, a file that is a valid but completely
      empty dict (every key missing at once, not just one), multiple simultaneously out-of-range
      values (confirming each field defaults independently, not just the first), three flavors of
      wrong-*type* stored value (string/list/`null`) as distinct from merely out-of-range, a stale
      special-only key left behind by a schema change (confirmed it's caught by the "unexpected
      keys remaining" cleanup, not by the per-key loop, since special-only keys are never popped
      from `data`), an extraneous key and a missing key in the same file, and a nonexistent parent
      directory (the one way to exercise both of `__init__`'s two separate `OSError` catches in a
      single run - the initial `os.stat`/read failure and the fallback write failure - since every
      other test's tmp directory already exists).
    - `get_dict`/typed-getter scenarios previously untested: an empty `keys` list, multiple keys
      where one is missing (confirmed: no partial result - the whole call returns `None`, not a
      dict missing just the bad key), the file being deleted or corrupted *after* a valid
      `ConfigManager` already exists (as opposed to every prior corruption test, which corrupted
      the file *before* construction), an unknown key reaching a typed getter's `KeyError` path
      (previously only exercised through `get_dict`, never through `get_int_values` etc.), and an
      empty schema string correctly yielding `[]` rather than `None`.
    - `write_config` scenarios previously untested: an empty `data` dict (a no-op success, not an
      error), all four `WriteValidity` outcomes (`Valid`/`Unchanged`/`Invalid`/`Failed`) exercised
      together in one call to confirm they don't interfere with each other and only the genuinely-
      valid change persists, a malformed schema entry for one key hard-aborting the *entire* call
      (confirmed: even an already-valid key's result is discarded, matching `__init__`'s own all-
      or-nothing treatment of a malformed schema - not a partial-failure design), a stored value
      that had drifted to an invalid type self-healing back to valid once a good value is written
      through it, and the file being corrupted after a valid `ConfigManager` already exists (as
      opposed to a bad file at construction time).
    - **One real gap surfaced, flagged rather than silently fixed (genuinely ambiguous, not a
      clear single-function bug)**: `write_config`'s special-only-key branch (`if not use_value:
      dict_results[key] = "Valid"; continue`) never calls `type_or_range_error` on the submitted
      value at all, unlike every normally-stored key - so a caller writing e.g.
      `{"Special": "not even an int"}` for a special-only field gets back `"Valid"` unconditionally,
      with no indication the value was nonsensical for that field's declared type. Pinned with
      `test_write_config_special_only_value_skips_type_validation_quirk`. Not fixed here: whether a
      special-only value *should* be type/range-checked even though it's never persisted depends on
      how a future caller (`api_helpers.py`'s REST pipeline, not yet promoted to `src/` and still
      using the old pre-refactor `ConfigManager`) is meant to interpret that "Valid" status for a
      command-only key - needs the project owner's input, not a guess.

## Decided for the refactor

- **`modules/_boot.py`'s `import sensortask.py`** (see open question #1 below) will be addressed
  as part of the `improved-quality/` refactor, not before. Until then it stays as-is on the
  current codebase — don't "fix" it on deployed units' code path.
- **The refactor targets the most recent *stable* releases**, not a re-pin of today's versions.
  This means MicroPython, pico-sdk, picotool, and Microdot should all move forward to their
  current stable releases as of whenever the refactor is actually done, and the refactor should
  actively adopt relevant improvements/new features those releases introduced (e.g. newer
  `machine`/`asyncio` capabilities, manifest/freeze changes, Microdot v2 features) rather than
  just reproducing today's 1.26-era behavior on newer version numbers. Re-verify current docs at
  that time rather than relying on this file's version notes, which will have aged.
- **Adafruit-derived driver code is fair game for the refactor.** Unlike `microdot.py` (genuinely
  vendored, hands-off), the low-level chip drivers carrying Adafruit CircuitPython headers have
  already been substantially modified (adapted to async) and can be freely restructured/rewritten,
  keeping attribution where due.
- **Config-schema data-loss risk is a non-issue in the refactor by design**, not something that
  needs a migration/merge fix bolted onto the current global-JSON `ConfigManager`: the refactor's
  config model is already per-sensor rather than one global file, which structurally avoids the
  "one missing key wipes everything" failure mode. The current deployed codebase's behavior is
  left as-is (see open question #8) — this isn't being patched pre-refactor.
- **Event-loop blocking convention**: any future long-running/blocking operation must not stall
  timing-sensitive work (e.g. Neopixel animation timing) — either avoid blocking the loop for a
  noticeable time in the first place, or have the blocking operation coordinate (e.g. via a shared
  lock, following the existing `get_long_block_lock()` pattern in `async_connect.py`) so
  timing-sensitive code gets to run before/around it rather than stalling alongside it. This is now
  a standing convention for new code, not just the original NTP/Neopixel case — see CLAUDE.md.
- **Neopixel warning-flash sequencing and the task-supervisor error-budget counter are both
  behaviorally correct and intentional as designed** (see "Functional clarifications" below) but
  both were flagged by the project owner as implementable more efficiently — worth a cleaner
  implementation in the refactor without changing the observed behavior.

## Functional clarifications

Confirmed by the project owner in a dedicated Q&A round, covering behavior that wasn't obvious
from reading the code alone:

- **wozi's SCD30 `AmbPres` is intentionally static, even with a live BMP388 present.** The SCD30
  stores ambient-pressure compensation in its own internal non-volatile memory as a one-time-set
  value — it isn't designed to track a continuously-updated live barometric reading. So BMP388's
  live pressure correctly is *not* auto-fed into it on any unit; this isn't a gap, on arzi/neu or
  wozi.
- **Air-quality warning LED sequencing is exactly as intended**: one color mapped to each condition
  (CO2/VOC/humidity), with a pause between flashes rather than combining simultaneous warnings into
  one signal. Confirmed correct as designed (see refactor efficiency note above).
- **FRAM SGP40 backup "0 = disabled" semantics are intended**: `SGPBackupPeriod=0` disables
  periodic backup writes, `SGPBackupMaxAge=0` disables the staleness check. Currently undocumented
  anywhere user-facing — see the new deferred-work item below.
- **Permanent WiFi deactivation after a second STA failure streak (post-hotspot) is a deliberate
  safety feature**, not a gap: it exists specifically so an unclaimed hotspot doesn't stay open
  indefinitely. A physical power-cycle is the accepted recovery path for a unit that reaches this
  state.
- **SCD30 `ForceCalRef` forced recalibration has a real field maintenance procedure behind it** —
  confirmed to exist, but the procedure itself wasn't captured in this session. Still needs writing
  down (see new open question below).
- **The web UI intentionally shows raw sensor numbers only, no color-coded readings** — the
  physical LED is considered the sufficient at-a-glance air-quality indicator; this is not a
  missing feature.
- **FRAM's 8KB allocation vs. SGP40's 248-byte current usage has plenty of confirmed headroom** for
  future FRAM-backed sensors/features.
- **SGP40 silently falling back to uncompensated VOC readings when SCD30 is down/stale, with no
  distinct "degraded" signal, is acceptable as-is** — SCD30's own error counter already surfaces
  the underlying cause; a separate flag isn't needed.

## Open questions (need the project owner's input or further investigation)

1. **`modules/_boot.py` — `import sensortask.py`** (literal `.py` in the import statement).
   Confirmed working reliably on real hardware for a long time (that's how the task autostarts),
   but MicroPython's documented freeze/import behavior (`freeze()`/`module()` strip the `.py`
   extension from the import name — reconfirmed against current `manifest.rst`) says the module
   should be named `sensortask`, so `import sensortask.py` looks like it should raise
   `ModuleNotFoundError` under standard dotted-import semantics. Mechanism is genuinely unclear —
   not yet root-caused against MicroPython's import source. **Do not "fix" this without testing on
   real hardware first** — it works today. **Resolution timing decided:** addressed during the
   `improved-quality/` refactor, not before (see "Decided for the refactor" above).
2. ~~**SGP40 FRAM backup/restore semantics**~~ — **RESOLVED** by reading
   `asy_sgp40_driver/__init__.py` and `voc_algorithm.py` in full. Confirmed: the FRAM timestamped
   chunk holds the VOC algorithm's serialized internal state
   (`vocalgorithm_proc_ser_des()` → `self.params.pack()`/`.unpack()`), restored on startup via
   `read_sgp()`'s `deserialize` path. A restored backup is discarded if it has no timestamp beyond
   one wait cycle, or if its age exceeds `backup_maxage` minutes; loading also waits up to
   `wait_ntp` seconds for NTP sync before trusting a timestamped backup. Periodic writes happen
   every `backup_period` minutes. Working assumption from the original notes was correct.
3. ~~**Physical wiring / schematics**~~ — **RESOLVED**: no external schematic/PCB design exists.
   Pin assignments encoded in each `sensortask-*.py` are the sole source of truth for wiring.
4. ~~**Ambient-pressure compensation on arzi/neu**~~ — **RESOLVED**: accepted limitation. wozi has
   a live BMP388; arzi/neu intentionally rely on a manually-set static `AmbPres` config value
   instead, and that's fine as-is — not something to address.
5. ~~**Treatment of Adafruit-derived driver code**~~ — **DECIDED**: fair game for the refactor to
   rewrite/restructure (see "Decided for the refactor" above). Only `microdot.py` remains
   genuinely hands-off/vendored.
6. ~~**Scope of `asy_long_block_lock`**~~ — **DECIDED**: this is now a general convention, not an
   ad hoc one-off (see "Decided for the refactor" above and CLAUDE.md) — long-blocking operations
   must not stall timing-sensitive work like Neopixel animation; new code should coordinate around
   that rather than just accepting simultaneous stalls.
7. ~~**`neu` reuses `arzi`'s HTML**~~ — **RESOLVED**: confirmed fine as-is. arzi's pages are
   generic/hostname-driven enough that reuse on neu units is intentional and correct, not a gap.
8. **Config-schema migration is a real data-loss risk on the current deployed codebase** —
   `ConfigManager` overwrites the *entire* config file with hardcoded defaults the moment even one
   key is missing relative to the current firmware's `_DEFAULT_CONFIG`, meaning a firmware update
   that adds a new config key onto a unit with an older `config.json` would silently wipe WiFi
   credentials and tuned calibration values. **Decided**: not being patched on the current
   codebase — accepted as today's workflow (reconfigure via the web UI after a key-adding update).
   The refactor avoids this class of bug entirely by moving to per-sensor config files instead of
   one global file (see "Decided for the refactor" above), so no migration-logic fix is planned
   there either — it just won't be a global-overwrite risk anymore.
9. ~~**Hardcoded fallback-hotspot password**~~ — **DECIDED**: accept the risk for now. Identical
   hardcoded AP-fallback password (`async_connect.py`, and duplicated in
   `improved-quality/async_connect.py`) stays as-is on the current codebase; only exploitable by
   someone in physical WiFi range of a unit that has already lost its real WiFi. Any fix (making it
   configurable/randomized) is deferred to the refactor, not applied now.
10. ~~**No `.gitignore` exists at all**~~ — **RESOLVED**: added (see repo root `.gitignore`).
11. **MicroPython version target vs. upstream drift** — deployed units run 1.26; upstream stable
    is now 1.28.0 (as of the last verification pass). **Decided:** the currently-deployed code
    stays pinned to 1.26 until a deliberate reflash campaign; the refactor is where the version
    target actually moves forward (see "Decided for the refactor" above) — this item now just
    tracks that the move hasn't happened yet, not whether it should. 1.27→1.28 rp2-port changes
    checked so far look RP2350-specific (DMA/PIO/pin-alt-function fixes), not RP2040-breaking, but
    this hasn't been exhaustively checked against every module in this codebase, and will need
    re-checking again at whatever point the refactor actually picks a version to land on.
12. **SCD30 `ForceCalRef` field procedure isn't written down anywhere yet.** Confirmed a real
    maintenance routine exists for using it (see "Functional clarifications" above), but the actual
    steps (reference concentration, exposure conditions/timing, how often it's done) still need to
    be captured from the project owner and documented — currently only the REST field itself exists
    in code with no procedure attached.

## Deferred / explicitly out-of-scope work (with reasoning)

- **HTML/frontend automation & consistency** — known to be hand-written, inefficient, and brittle
  by the project owner. Not a priority. Revisit *after* the Python-side refactor is done, then aim
  for automatic/consistent generation.
- **UART sensor integration** (`asy_uart.py`/`asy_uart_comm.py`, currently unused by any deployed
  config) — address only after the refactor of already-deployed features is complete. Not before.
- **Config-duplication centralization** (the same config keys currently have to be kept in sync by
  hand across `_DEFAULT_CONFIG`, the REST handler, and the HTML form) — acknowledged as a real
  weakness, explicitly owned by the `improved-quality/` refactor. Not a concern for the current
  codebase.
- **`dev` config quirks** (e.g. LED/Neopixel REST routes referencing an object that's never
  instantiated since Neopixel task starters are commented out) — explicitly told to ignore, it's a
  bench rig only.
- **Unit tests** — not to be written against the current codebase. The plan is: fully understand
  how the current system works first, confirm what's already been well-transferred into
  `improved-quality/`, and write tests as part of that refactor, not before.
- **Dev/build environment setup (venv, pinned toolchain versions)** — **toolchain installer done**:
  `toolchain/setup_toolchain.py` (run via `uv run toolchain/setup_toolchain.py`, see
  `toolchain/README.md`) now clones/builds a matching MicroPython + pico-sdk + picotool + ARM
  cross-compiler from scratch, and updates an existing install in place (re-run the same command
  after bumping `toolchain/versions.toml`'s MicroPython ref, or pass `--latest`). Verified in this
  repo's sandbox: a clean install of the latest stable MicroPython (v1.28.0) and of the currently-
  deployed pin (v1.26.1) each build a standard, unchanged `RPI_PICO_W` firmware image with zero
  compiler errors/warnings, build a working `mpy-cross`, and successfully cross-compile a sample
  `.py`; updating an existing v1.26.1 install to v1.28.0 via the same command was also verified
  (including a real bug caught and fixed along the way — building `mpy-cross` before syncing
  submodules left stale submodule pins from the old version, producing a spurious "-dirty" version
  string; fixed by syncing submodules first).
  - **This whole entry predates the Unix port build.** Everything below narrates the toolchain's
    development history at the time it happened, when there were only the three checks above (no
    Unix port). Verification has since been restructured twice — first adding a 4th check (build
    the Unix port, run a sample script on it), then replaced entirely by the 8-step frozen-bytecode
    chain described in "Self-contained venv via uv" in "Final-goal requirements for the refactor"
    above, which is the current, up-to-date description and has its own verification evidence.
    Left as-is here rather than rewritten, since it's a historical record of what was verified
    when — just don't read "three checks" (or "a 4th check") below as describing the toolchain's
    current state.
  - **Still not done**: this only covers the generic toolchain, not this project's own firmware
    build. `build-*.sh`/`FROZEN_MANIFEST`'s hardcoded `/home/nico/rpi_pico/...` path and the
    `py-include` symlink wiring (see root README's "Build process") still need genericizing to
    actually point at a `toolchain/setup_toolchain.py`-provisioned tree — that's the natural next
    step, not yet started.
  - The CI requirement that it also attempt a real firmware build (see "Final-goal requirements for
    the refactor" above) makes that remaining step a real near-term prerequisite, not just a
    nice-to-have, once picked back up.
  - **Re-verified from scratch on a genuinely clean Ubuntu 24.04 system**, not just a fresh
    directory inside an already-provisioned sandbox: built a `debootstrap`-based `noble` chroot
    with nothing preinstalled beyond the minimal base (no build tools, no `git`/`sudo`/`uv`, no apt
    cache beyond the `main` component) and ran the installer inside it end-to-end. Passed all three
    checks for both the latest release and the `v1.26.1` pin, and the update path (existing
    `v1.26.1` install → re-run targeting latest) worked too. One genuine prerequisite surfaced:
    `debootstrap`'s default `sources.list` only enables `main`, and `gcc-arm-none-eabi` (plus its
    newlib packages) lives in `universe` — not a script bug, since every official Ubuntu 24.04
    image ships with `universe` enabled already, but worth the explicit callout for anyone building
    from a deliberately minimal base. Documented in `toolchain/README.md` and the root README.
  - **Added a `test` subcommand** (`uv run toolchain/setup_toolchain.py test`) alongside `setup`,
    for exactly the CI-firmware-build requirement above: it re-runs the same three verification
    checks against whatever is already installed at `--toolchain-dir`, but never touches apt or
    git remotes, so it's fast (~30s vs. minutes for `setup`) and fully offline/reproducible.
    Verified working against a `setup`-provisioned install, and verified it fails with a clear,
    actionable message (not a confusing build error) when pointed at a directory with no toolchain
    installed yet. No CI pipeline exists to wire it into yet — this just makes the eventual wiring
    a drop-in rather than a redesign.
  - **Hardened against ambient-environment interference.** Every subprocess call now gets an
    explicitly constructed environment (fixed `PATH` plus a small variable allowlist for the
    actual compile steps; the same plus explicit proxy/CA passthrough for `git`/`apt-get` and the
    rp2 port's `make submodules` target, which does both a git fetch and an internal cmake
    configure pass) instead of inheriting the caller's shell wholesale — see "Environment
    isolation" in `toolchain/README.md` for the full breakdown of what's allowed through and why.
    Verified adversarially: ran both `setup` and `test` with `CC`/`CXX` pointed at `/bin/false`,
    garbage `CFLAGS`/`MAKEFLAGS`, a bogus `PICO_SDK_PATH`/`CMAKE_INSTALL_PREFIX`, and fake
    `cmake`/`arm-none-eabi-gcc`/`picotool` scripts placed ahead in `PATH` — all real interference
    a machine with other locally-installed tooling could plausibly have. Confirmed one genuine bug
    this way before the fix: `make submodules` was left on fully-ambient environment on the theory
    that only `git`/`apt-get` needed real env, but that target's own internal `cmake` configure
    pass picked up the fake `cmake` and failed, which is exactly why `network_env()` exists as a
    distinct, explicit combination rather than a binary ambient/clean split.
  - **A real installer run on the project owner's own machine surfaced a second locale-related
    gap in this isolation, missed by the adversarial test above**: `LANG`/`LC_ALL` were still
    being allowlisted through from the caller's shell, visible as German-localized `git`/`apt`
    output in that run's log. Since `build_firmware()`/`build_mpy_cross()` detect failure by
    grepping build output for the literal English `error:`/`warning:` (the only signal `make`/
    `gcc` give beyond exit code), and GCC/binutils diagnostics can be translated via gettext
    catalogs on a system where the caller's locale has one installed, this could have silently
    defeated that detection on some machines. Fixed by forcing `LANG=C.UTF-8`/`LC_ALL=C.UTF-8` in
    `build_env()` instead of passing them through; re-verified by re-running `setup` with
    `LANG=de_DE.UTF-8` set in the calling shell and confirming output stayed in English and all
    three checks still passed.
  - **Added `--clean`** (`uv run toolchain/setup_toolchain.py --clean`), prompted directly by the
    project owner noticing that a repeat `setup` run doesn't recompile `mpy-cross` at all when
    its source hasn't changed (correct, deliberate behavior — the firmware build always wipes its
    own build dir first for the same reason, but `mpy-cross`'s is otherwise left alone to rebuild
    incrementally). `--clean` wipes every build-artifact directory (`picotool/build`,
    `mpy-cross/build`, `ports/rp2/build-<board>`, and — since the Unix port build was added —
    `ports/unix/build-standard`) without touching the git clones, then proceeds through the
    normal build+verify flow — bringing the toolchain back to a from-scratch build state on
    demand without re-cloning multi-gigabyte source trees. Verified: a fresh install,
    then a normal re-run (confirmed `mpy-cross` skips recompilation, matching the observed
    behavior), then `--clean` (confirmed it wipes the build dirs and `mpy-cross` fully recompiles
    again), all ending with all three checks passing.
  - **`update_and_install.txt` re-verified against current (2026) upstream docs — structurally
    still accurate, but missing one real, currently-relevant gotcha.** The three-separate-clones
    approach (`pico-sdk`, `picotool`, `micropython`), the `lib/mbedtls` submodule-init step, the
    `libusb-1.0-0-dev` dependency, and the picotool `cmake -DPICO_SDK_PATH=... && make && sudo make
    install` steps are all still exactly right per current
    [`picotool/BUILDING.md`](https://github.com/raspberrypi/picotool/blob/master/BUILDING.md) and
    the MicroPython
    [`ports/rp2/README.md`](https://github.com/micropython/micropython/blob/master/ports/rp2/README.md)
    (`make -C mpy-cross` from the repo root, then `make BOARD=RPI_PICO_W submodules`/`clean`/build
    from `ports/rp2`).
    - **New requirement since pico-sdk 2.0.0, not covered by the current notes**: a standalone
      `picotool` build must have a matching major.minor version to the pico-sdk it's built
      against (enforced via install marker files, not just `PATH`) — a version mismatch now fails
      the build outright with "Incompatible picotool installation found"
      ([pico-sdk#1990](https://github.com/raspberrypi/pico-sdk/issues/1990)). **This already
      applies today, not just at refactor time**: MicroPython 1.26 (the currently deployed pin)
      bundles pico-sdk **2.1.1** as its internal submodule, so anyone rebuilding the toolchain from
      `update_and_install.txt` right now needs the standalone `pico-sdk`/`picotool` clones checked
      out at a matching `2.1.x` tag, or the build breaks. Whatever MicroPython version the refactor
      eventually lands on will pin its own matching pico-sdk version — check it fresh at that time
      rather than assuming `2.1.1` still applies.
    - **Toolchain packages were never listed in the notes at all** (and still aren't a gap
      introduced by drift, just a pre-existing one): `build-essential`, `cmake`, `pkg-config`,
      `git`, and the ARM cross-compiler (`gcc-arm-none-eabi`, `libnewlib-arm-none-eabi`,
      `libstdc++-arm-none-eabi-newlib` on Debian/Ubuntu) are all still required but were presumably
      assumed pre-installed. Worth listing explicitly once this becomes a real setup script.
    - **An official one-shot alternative exists**:
      [`raspberrypi/pico-setup`](https://github.com/raspberrypi/pico-setup)'s `pico_setup.sh`
      installs the toolchain, clones pico-sdk, and builds/installs picotool in one script — worth
      considering as a base for the genericized setup script instead of hand-rolling the same
      steps.
- **No end-user reference for Neopixel LED colors/patterns exists.** The single physical LED does
  double duty (steady WiFi-status indicator + transient warning/external-command flash), confirmed
  intentional, but there's no legend anywhere (HTML UI, printed label) explaining what each
  color/pattern means. Worth adding one, low priority.
- **FRAM SGP40 "0 = disabled" semantics need user-facing documentation** — confirmed intended
  behavior (see "Functional clarifications" above), just not written down anywhere a unit's admin
  would see it (API docs, HTML tooltip, etc.).

## Security notes

- A real WiFi SSID/password (and a device hostname revealing its physical location) were committed
  in `modules/config.json` in the repo's original initial commit (in a previous copy of this
  project, before it was reimported into this repo). The password was confirmed already
  stale/rotated by the project owner. The history was scrubbed in that prior repo; this repo was
  imported fresh specifically to leave that incident behind. Full sweep of this repo's working
  tree turned up no API keys, tokens, private keys, or email addresses beyond the one item below.
- The one other real credential is the hardcoded hotspot fallback password (item #9 above,
  accepted-for-now) — still present in both `python/CommonDrivers/async_connect.py` and
  `improved-quality/async_connect.py`.
