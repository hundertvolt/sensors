# CLAUDE.md

Operating constraints and architecture reference for AI sessions working in this repo. See
README.md for human-facing orientation and BACKLOG.md for the open-questions/deferred-work list.

## Platform target

- Deployed units run **MicroPython 1.26** on **Raspberry Pi Pico W (1st gen / RP2040)**. Code
  ships as **frozen bytecode** compiled into the firmware — it is not loaded from the device
  filesystem at runtime, and CPython-only stdlib features/behavior cannot be assumed.
  - Upstream MicroPython has moved past 1.26 (1.28.0 was the latest stable as of the last
    doc-verification pass) — don't assume "current docs" and "1.26 behavior" are the same thing.
    When in doubt about whether an API changed between 1.26 and latest, say so explicitly rather
    than silently documenting latest-only behavior as if it applies to deployed devices.
  - **1.26 is the pin for the current, deployed codebase only.** The `improved-quality/` refactor
    is explicitly meant to move the version target forward to whatever is the most recent *stable*
    release at that time (MicroPython, pico-sdk, picotool, Microdot) and to actively use relevant
    improvements/new features those releases introduced — not just reproduce 1.26-era behavior
    under a newer version number. See BACKLOG.md's "Decided for the refactor" section.
  - **MicroPython 1.26 already bundles pico-sdk 2.1.1 as its internal `ports/rp2` submodule** —
    confirmed via web search, not training-data memory. Since pico-sdk 2.0.0, a standalone
    `picotool` build must match the pico-sdk major.minor version it's used against (enforced via
    marker files from `sudo make install`/`cmake --install`, not just having the binary on `PATH`)
    or the build fails with "Incompatible picotool installation found." This means
    `update_and_install.txt`'s standalone `pico-sdk`/`picotool` clones need to be checked out at a
    matching `2.1.x` tag *today*, not just "whatever's current" — see BACKLOG.md's "Dev/build
    environment setup" item for the full finding.
  - `machine.WDT` hard-caps at **8388ms** on RP2040. Current code uses `WDT(timeout=8000)` — only
    388ms of margin. Don't casually increase this without checking the cap still holds against
    current docs.
  - `RP2040`: dual-core Cortex-M0+ @ up to 133MHz, 264KB SRAM (6 banks), 2×I2C, 2×SPI, 2×UART,
    8×PIO state machines.
  - Pico W's littlefs partition (~848KB) is smaller than plain Pico's (~1.37MB) because Pico W's
    firmware image is larger (CYW43 driver + WiFi/BT firmware blobs baked in) — the filesystem
    occupies whatever flash remains after the firmware image, not a fixed per-board reservation.
- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.

## Hard rules

- **Do not edit `improved-quality/`.** It's the WIP refactor target — out of scope. It's useful
  read-only context for what's already been identified/addressed (it independently has
  `base_classes.py`, `config_manager.py`, `print_log.py`, `mypy.ini`, `pycheck.sh`).
- **Do not "fix" `modules/_boot.py`'s `import sensortask.py`** (literal `.py` in the import
  statement) without testing on real hardware first. It works reliably today; MicroPython's
  documented freeze/import behavior says the module should be named `sensortask` with the
  extension stripped, so this *looks* like it should raise `ModuleNotFoundError` — the mechanism
  is genuinely unresolved (see BACKLOG.md #1). Changing it blind risks breaking every deployed
  unit's autostart.
- **`python/CommonDrivers/microdot.py` is vendored third-party code** — verified to match current
  upstream Microdot exactly (`send_file()` signature, `Request.json` behavior). Don't restyle or
  "clean up" it; if you need to change its behavior, treat that as a deliberate fork decision, not
  routine editing.
- **`dev` config is a bench rig only** — its quirks (e.g. LED/Neopixel REST routes referencing an
  object that's never instantiated) are explicitly out of scope. Don't fix them as if they were
  bugs.
- **No unit tests against the current codebase.** The agreed plan is: fully understand the current
  system first, confirm what's already transferred into `improved-quality/`, and write tests as
  part of that refactor — not before, and not against the current code. This does **not**
  contradict BACKLOG.md's detailed testing requirements (pytest under a real MicroPython Unix-port
  interpreter, `uv`-managed venv, mocking boundary, etc.) — those describe what the *refactored*
  code must eventually have; they are not retroactively applicable to today's pre-refactor code.
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A real
  WiFi SSID/password was previously committed and had to be scrubbed from history — see
  BACKLOG.md's security notes. A `.gitignore` now covers per-device config/build artifacts, but
  still be deliberate about what you stage.
- **Long-blocking operations must not stall timing-sensitive work.** Any new code that blocks the
  event loop for a noticeable time (e.g. `socket.getaddrinfo()`) must not do so while
  timing-sensitive work like the Neopixel animation needs to run — either avoid the block, or
  coordinate via `async_connect.py`'s `get_long_block_lock()` pattern so timing-sensitive code runs
  before/around it. This is a standing convention for all new code, not just the original
  NTP-vs-Neopixel case it was written for.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/transferred well into `improved-quality/`. The refactor should end up
  with the *same top-level features*, just more consistent/stable — not a feature change.
- When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed upstream
  API, etc.), update the doc in the same session rather than silently working around the
  discrepancy.
- Prefer flagging genuinely ambiguous/architecturally significant decisions to the project owner
  over guessing — several open questions in BACKLOG.md exist precisely because the code's actual
  intent wasn't obvious from reading it alone.

## Pull request workflow

- **Always create a pull request with a meaningful description** when finishing work on a branch —
  summarize what changed and why, not just a file list.
- **Automatically subscribe to the pull request's activity** (review comments, CI results) right
  after opening it, so review feedback and CI failures get picked up without being asked again.

## Architecture reference

See README.md's "Architecture at a glance" section for the condensed version. Key modules if you
need to go deeper:

- `python/CommonDrivers/api_helpers.py` — generic REST validate → apply-to-sensor → persist
  pipeline, repeated by hand for every endpoint (no shared schema/route generation — see
  BACKLOG.md's config-duplication item).
- `python/CommonDrivers/async_connect.py` — WiFi STA + AP/hotspot fallback + NTP client with
  manual CET/CEST DST math (`cettime()`); exposes `get_long_block_lock()`, a shared lock
  serializing `socket.getaddrinfo()` against Neopixel animation — this pattern is now the general
  convention for long-blocking operations, see "Hard rules" above.
- `python/CommonDrivers/async_manager.py` — `ConfigManager`, `DataManager`,
  `TimeCounterManager`, `LockedValue`/`Flag`.
- `python/IndividualDrivers/asy_fram_driver.py` / `asy_fram_manager.py` — raw SPI FRAM driver +
  chunk allocator with dual-copy redundancy (arzi/neu/wozi only, not dev).
- **SCD30's `AmbPres` (ambient-pressure compensation) is stored in the sensor's own internal
  non-volatile memory as a one-time-set value, not a continuously-updated live input.** This is why
  it's a static config value on every unit — including wozi, which has a live BMP388 — and why
  `set_ambient_pressure` is called with `force=True` in the REST handler: resending the same value
  is also the SCD30's documented command to resume continuous measurement after it's been stopped.
  Don't "fix" this into a live BMP388→SCD30 feed; it's intentional, confirmed by the project owner.
- Task supervisor lives in `main()` inside each `sensortask-*.py`, not in a shared module — it's
  duplicated per device file today.
