# BACKLOG

Open questions and explicitly deferred work, with reasoning, so nothing here gets re-litigated
from scratch in a future session. See README.md for orientation and CLAUDE.md for operating
constraints.

## Final-goal requirements for the refactor (owner-specified, not yet implemented)

These are additional requirements for what the `improved-quality/` refactor must eventually
deliver. Recorded here as a target/spec — not implemented yet, not to be actioned until the
refactor work itself starts:

- **Stability / robustness**: thorough error handling throughout — no error condition that can
  plausibly occur in real operation should lead to an uncaught exception; anything that might
  happen should be caught and handled explicitly. The hardware watchdog is a last resort only
  (e.g. undefined state after an electrical brownout, a MicroPython interpreter-level failure),
  not a routine recovery mechanism for expected error conditions.
  - **Bare `except:` is forbidden in the refactored code** — `except Exception:` (or a narrower/
    specific exception type) is required everywhere. This is stricter than
    `improved-quality/pycheck.sh`'s current ruff config, which ignores E722 (bare except); that
    ignore should be dropped for the refactor.
- **No leaks, no drift**: the system should be able to theoretically run indefinitely without
  exhausting any resource (memory, handles, counters, etc.). **Verified via design discipline, not
  an automated soak test** — no dedicated long-running/memory-tracking test is required in CI for
  this; it's enforced through code review and patterns (bounded buffers, no unbounded growth),
  not a CI gate.
- **Production-level code quality**: unit tests, mypy, and ruff shall all be available both as
  shell command scripts and as a CI pipeline in GitLab, which **shall also attempt a real firmware
  build** (running the equivalent of `build-*.sh`, with the full micropython/pico-sdk/picotool
  toolchain) as a pipeline stage, not just lint/type-check/unit-test.
  - **Done (manual scripts only, not CI yet)**: root `pyproject.toml` + `scripts/lint.sh` +
    `scripts/typecheck.sh`, scoped to `improved-quality/` only for now (see CLAUDE.md's "Code
    quality tooling" section for the full rationale). `improved-quality/mypy.ini` and
    `improved-quality/pycheck.sh` — an ad hoc, trial-and-error setup — have been retired in favor
    of this. **Still open**: wiring an equivalent GitLab CI pipeline, extending scope to the
    pre-refactor codebase (`python/`, `modules/`), and unit tests (blocked on CLAUDE.md's "No unit
    tests against the current codebase" rule and on the MicroPython Unix-port setup below).
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
  - **No hard test-coverage percentage gate for now** — tests must exist and run in CI, but no
    specific minimum coverage threshold is enforced yet.
  - **PEP 604 union syntax** (`int | None`, already used in `improved-quality/base_classes.py`) is
    fine to keep using for now as typing-only; whether it actually executes correctly at runtime on
    the deployed MicroPython version is a separate concern to verify later, not urgent yet.
- **Self-contained venv via `uv`**: testing shall be possible on a generic Linux machine inside a
  venv installable via `uv sync`. **Tests run under the real MicroPython interpreter** (e.g. a
  built Unix port), not CPython — "as close to the real environment as possible" means the actual
  MicroPython runtime, not just MicroPython-flavored stubs on top of CPython.
  - **How `uv` and the Unix port connect**: `uv sync` itself only manages the CPython-side tooling
    (pytest, ruff, mypy, etc.) — it can't install a compiled MicroPython binary. The plan is a
    setup script that builds/installs the MicroPython Unix port interpreter if it isn't already
    present, ideally triggered automatically from `uv` (e.g. a `uv run` entry point or a hook), so
    `uv sync` remains the single onboarding command even though it's delegating that one step out.
  - **Mocking boundary**: mock only at the raw bus-transaction level (`machine.I2C`/`machine.SPI`
    read/write calls) — drivers, Reader classes, `ConfigManager`, and REST handlers should all run
    for real, unmocked, in tests. Mock higher up (e.g. whole driver classes) only if there's truly
    no other way.
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
  commands) — depends on the bus type and sensor. Some of this already exists (e.g.
  `asy_spi_driver.py`'s `extra_clocks` parameter cycles the bus after CS deassert); the refactor
  should make sure this is used as completely/consistently as possible across all buses and
  sensors, not just where it happens to exist today.
  - **I2C recovery is device-specific, not bus-generic**: unlike SPI's `extra_clocks`, I2C recovery
    (retry + sensor reset commands) is expected to vary per device — check what each individual
    driver already does before assuming a gap. If a genuinely generalizable I2C-side mechanism
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
   interpreter setup script, unit tests, GitLab CI including the firmware-build stage) — comes
   last since it's meaningfully easier to write tests and wire up CI against the settled
   post-refactor structure than against a moving target. **Partial exception, done out of order**:
   manual-only mypy/ruff config + MicroPython stubs (see "Production-level code quality" above)
   were pulled forward ahead of this sequencing, scoped to `improved-quality/` as it stands today —
   CI wiring, unit tests, and extending scope still follow this sequencing.

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
    `mpy-cross/build`, `ports/rp2/build-<board>`) without touching the git clones, then proceeds
    through the normal build+verify flow — bringing the toolchain back to a from-scratch build
    state on demand without re-cloning multi-gigabyte source trees. Verified: a fresh install,
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
