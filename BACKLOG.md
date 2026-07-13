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
  - **MicroPython stubs**: install the published PyPI `micropython-stubs` package (or the relevant
    board/port-specific variant, e.g. an rp2-flavored one) rather than hand-rolling stub files.
  - **Ruff/mypy config**: stricter than default where it concerns actual code quality/correctness,
    but **allow any line length and don't introduce line breaks** — ruff's `--format` step should
    likely be omitted entirely rather than configured with a line-length; this is a deliberate
    style choice, not an oversight.
  - **No hard test-coverage percentage gate for now** — tests must exist and run in CI, but no
    specific minimum coverage threshold is enforced yet.
  - **PEP 604 union syntax** (`int | None`, already used in `improved-quality/base_classes.py`) is
    fine to keep using for now as typing-only; whether it actually executes correctly at runtime on
    the deployed MicroPython version is a separate concern to verify later, not urgent yet.
- **Self-contained venv via `uv`**: testing shall be possible on a generic Linux machine inside a
  venv installable via `uv sync`. **Tests run under the real MicroPython interpreter** (e.g. a
  built Unix port), not CPython — "as close to the real environment as possible" means the actual
  MicroPython runtime, not just MicroPython-flavored stubs on top of CPython.
  - **Mocking boundary**: mock only at the raw bus-transaction level (`machine.I2C`/`machine.SPI`
    read/write calls) — drivers, Reader classes, `ConfigManager`, and REST handlers should all run
    for real, unmocked, in tests. Mock higher up (e.g. whole driver classes) only if there's truly
    no other way.
- **Centralized config**: all tooling config shall live in `pyproject.toml`, as **dev-tooling
  config only** (ruff/mypy/pytest/uv sections) — the shipped code stays frozen-bytecode-only, not
  restructured into an installable package.

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
- **Dev/build environment setup (venv, pinned toolchain versions)** — deliberately not started yet.
  General direction when it does happen: track the most recent *stable* releases of
  MicroPython/pico-sdk/picotool rather than pinning to what's in the current handwritten notes;
  MicroPython's rp2 port depends on specific pico-sdk submodules (e.g. `lib/mbedtls`), which
  `update_and_install.txt` already gestures at.
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
