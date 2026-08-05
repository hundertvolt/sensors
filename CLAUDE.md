# CLAUDE.md

Operating constraints and architecture reference for AI sessions working in this repo. See
README.md for human-facing orientation and BACKLOG.md for the open-questions/deferred-work list.

## Datasheets

- **The `datasheets/` folder (root of the repo) holds real datasheet PDFs the project owner has
  collected for the sensors/chips this codebase drives** (currently: `bmp3xx/`, `fram/`, `pico w/`,
  `scd30/`, `sgp40/`) — read the actual PDF from here first for any hardware-interaction claim
  (register layout, opcodes, timing, electrical characteristics), rather than reconstructing it
  from training memory or web search. Read tools can open PDFs directly.
- **If a datasheet you need isn't in this folder and you can't download it yourself** (blocked
  fetch, paywall, dead link, etc.), **say so explicitly and immediately** rather than silently
  falling back to web search summaries or training memory for a claim the real datasheet would
  settle — the project owner will add it to `datasheets/` if you tell them what's missing (exact
  part number / document number is enough, a specific URL isn't required).

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
    under a newer version number.
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
  - **A soft `machine.Timer` callback (the default — no code in this repo passes `hard=True`) can
    be silently dropped, not just delayed.** Confirmed against real `py/scheduler.c`/
    `shared/runtime/mpirq.c`/`ports/rp2/machine_timer.c` source: firing dispatches via
    `mp_sched_schedule()`, which returns `False` and drops the callback if MicroPython's
    fixed-depth scheduler queue (`MICROPY_SCHEDULER_DEPTH=8` on rp2, shared by every soft
    timer/IRQ on the device) is already full — no exception anywhere in that chain, and no way for
    Python code to detect a dropped vs. not-yet-run callback. A periodic timer self-heals on the
    next tick; a one-shot timer does not fire again. A software timeout to guard against this was
    considered for `system_service.py`'s two exposed call sites (the reboot-reset timer,
    `start_timers()`'s chained sequencer) and rejected: it would just be a second, uncoordinated
    clock racing the real hardware watchdog every real deployment already arms, and the scenario it
    defends against (no watchdog configured) is test-only. Don't re-propose a software-timeout
    mitigation for this without a materially different justification.
  - **`[x] * n` (list repeat) can segfault the whole interpreter process, not just raise, for n in
    roughly 2⁶¹–2⁶³** — confirmed by direct reproduction (`[0] * (2**62)` → SIGSEGV, no `try/except`
    catches it). Below ~2⁶¹ it raises `MemoryError` like `bytearray(n)`; at/above 2⁶³ it raises
    `OverflowError`; the gap in between is the dangerous range, likely from the repeat's internal
    `n * sizeof(pointer)` byte-count multiplication overflowing before being bounds-checked (`bytearray`
    has no such intermediate multiplication, hence no gap). Any new code allocating a
    list/deque/buffer sized from external or caller-supplied input must clamp the size *before* the
    allocation, not just catch `MemoryError` reactively — see `base_classes.py`'s `LockableBuffer`/
    `print_log.py`'s `PrintLogHistory` for the established clamp-then-allocate pattern.
  - **`machine.Timer.init()` can raise `OSError(ENOMEM)` if the RP2040's alarm pool is exhausted** —
    confirmed against real `ports/rp2/machine_timer.c` source. Every `Timer.init()` call site in this
    codebase must handle it (degrade gracefully if a safe fallback exists, otherwise let the failure
    stay isolated to whatever that one timer was for) — see `system_service.py` for the established
    pattern. `Timer()`'s bare constructor and `Timer.deinit()` never allocate/raise; `WDT.feed()` is a
    bare register write and cannot raise either.
  - **`MemoryError` is not an `OSError` subclass in MicroPython** — an `except OSError:` alone is
    blind to allocation failure; anywhere an `OSError` is caught around a call that could also
    plausibly exhaust memory, catch `(OSError, MemoryError)` instead.
  - **`struct.pack()`/`pack_into()` silently zero-pad or truncate on a value/argument-count
    mismatch instead of raising**, unlike CPython. Don't rely on a mismatch surfacing as an
    exception; validate shape before packing if it matters.
- **Always check current MicroPython and Microdot documentation before asserting how an API
  behaves** — do not rely on training-data memory for either. This has already caught real
  discrepancies once; treat it as a standing requirement for every session, not a one-time step.

## Hard rules

- **Don't edit `improved-quality/`'s *source* files (drivers, managers, etc.) — they're the WIP
  refactor target, out of scope for routine editing.** This does **not** cover its dev-tooling
  config: `mypy.ini`/`pycheck.sh` were an ad hoc, trial-and-error setup the project owner
  explicitly asked to have questioned and replaced (confirmed directly, not inferred) — they've
  been retired in favor of root-level `pyproject.toml` + `scripts/lint.sh`/`scripts/typecheck.sh`
  (see "Code quality tooling" below). Source files elsewhere in `improved-quality/` remain
  read-only context until the refactor itself starts. **The project owner can authorize a scoped
  exception for a severity-justified fix** (precedent: the `ConfigManager`/`LockedValue`
  wrong-module-import bug that would have crash-looped every deployed unit's boot) — this is a
  standing, repeatable exception path, not a one-off; it still requires the owner's explicit
  authorization each time, scoped narrowly to the specific fix, not a general license to edit
  `improved-quality/` more broadly.
- **`src/` is where files land once they're fully reviewed and tested** — formula/logic
  correctness checked, input validation and exception-safety audited, unit tests written and
  passing (see "Code quality tooling" below and `tests/README.md`), unlike `improved-quality/`'s
  WIP files above. **`src/README.md` is the full checklist** for what "fully reviewed and tested"
  actually requires — apply it to every file that makes this move, not just whichever ones already
  have. **For a new sensor driver specifically, `DRIVER_SPEC.md` (repo root) is the shared
  architecture/interface spec** extracted from the three drivers already in `src/` — what shape
  the code should take (layering, naming, error handling, config schema, ...), separate from
  `src/README.md`'s "is it good enough to move" checklist. Files in `src/` aren't automatically
  re-wired into any driver's actual import path for a
  real firmware build just by moving there — `improved-quality/` files keep importing them by
  their old unqualified name unchanged (e.g. `import math_helpers`, `from crc_checks import ...`),
  which still resolves correctly both because MicroPython's frozen-module namespace is flat (it
  doesn't matter which directory the source lives in once it's actually frozen into firmware) and,
  for local dev-tooling checks today, because `pyproject.toml`'s `mypy_path` includes `src`. Treat
  `src/` files as normal, freely-editable code, not as read-only WIP context the way
  `improved-quality/` is.
- **Whenever a new file is promoted into `src/`, run a bird's-eye-view scan over the whole
  content of `src/`** — not just the new file in isolation — to check that the coding guidelines
  and `src/README.md`'s checklist (including its "API consistency, within a file and across the
  project" and "Check against current MicroPython" items) actually hold consistently across every
  file there, not just that the new file individually passes review on its own. **If the scan
  surfaces a discrepancy — one file diverging from another, or from a guideline — do not silently
  fix it.** Report it and discuss how to resolve it before changing anything, the same "flag, don't
  silently change" treatment section 1 of `src/README.md` already gives formula/behavior
  discrepancies, applied here to cross-file consistency instead.
- **Do not "fix" `modules/_boot.py`'s `import sensortask.py`** (literal `.py` in the import
  statement) without testing on real hardware first. It works reliably today; MicroPython's
  documented freeze/import behavior says the module should be named `sensortask` with the
  extension stripped, so this *looks* like it should raise `ModuleNotFoundError` — the mechanism
  is genuinely unresolved (see BACKLOG.md #1). Changing it blind risks breaking every deployed
  unit's autostart.
- **`python/CommonDrivers/microdot.py` is vendored third-party code** — verified to match current
  upstream Microdot exactly (`send_file()` signature, `Request.json` behavior). Don't restyle or
  "clean up" it; if you need to change its behavior, treat that as a deliberate fork decision, not
  routine editing. **`ext/microdot.py` is the same policy applied to the refactor target**: a plain,
  unmodified vendored copy of upstream Microdot (pinned to tag `v2.6.2`), replacing the
  `improved-quality/microdot.py` copy that had drifted into an unintentional fork (removed). No
  edits, no restyling, ever — any behavior change needed is handled by wrapping/calling it from our
  own code (see "Microdot / REST layer" below), never by touching this file. `src/` and `ext/` are
  copied flat into one directory and frozen together for the refactored firmware build, which is why
  they live at the same directory depth in the repo.
- **`dev` config is a bench rig only** — its quirks (e.g. LED/Neopixel REST routes referencing an
  object that's never instantiated) are explicitly out of scope. Don't fix them as if they were
  bugs.
- **No unit tests against the current (deployed, pre-refactor) codebase — `python/`, `modules/`.**
  The agreed plan is: fully understand the current system first, confirm what's already
  transferred into `improved-quality/`, and write tests as part of that refactor — not before, and
  not against the current code. This does **not** contradict `tests/README.md`'s testing
  requirements (tests under a real MicroPython Unix-port interpreter, `uv`-managed venv, mocking
  boundary, etc.) — those describe what the *refactored* code must eventually have. **First
  concrete instance**: `src/math_helpers.py` has a full `tests/test_math_helpers.py` suite,
  running under a real MicroPython Unix-port interpreter per that plan (see "Code quality tooling"
  below) — this rule is about not testing the old `python/`/`modules/` code, not about deferring
  all tests indefinitely.
- **Don't touch `sensors/config.json`-equivalent files or commit any real credentials.** A
  `.gitignore` covers per-device config/build artifacts, but still be deliberate about what you
  stage. **The one known real credential already in this repo**: a hardcoded hotspot fallback
  password, present in both `python/CommonDrivers/async_connect.py` (deployed, pre-refactor) and
  `src/asy_wifi_service.py` (promoted) — accepted risk (only exploitable by someone in physical
  WiFi range of a unit that's already lost its real WiFi), not something to "fix" by
  rotating/removing without the project owner's direction. `improved-quality/async_connect.py`
  itself was removed once its functionality was fully promoted to `src/asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` — no import in the repo referenced it anymore.
- **For a genuinely wedged I2C bus/sensor (e.g. SCD30 hanging mid-transaction), the hardware
  watchdog is the accepted backstop, not a software fix to chase.** MicroPython's cooperative
  scheduler can't preempt a synchronous `machine.I2C` call already in progress, so an asyncio-level
  timeout can't interrupt it either way. This is settled — don't re-propose an I2C-level timeout
  mechanism. **`socket.getaddrinfo()` turned out to belong in this same "can't be timeout-wrapped"
  bucket, not the "genuinely can" one** — confirmed against real MicroPython issue tracker reports
  (micropython#18797, micropython#8326, micropython-lib#1078): it's a raw synchronous call with no
  coroutine boundary for `asyncio.wait_for()` (or any asyncio-level timeout) to attach to, the same
  preemption gap as a wedged `machine.I2C` transaction. This is now moot for DNS specifically —
  `src/asy_ntp_client.py` no longer calls `socket.getaddrinfo()` at all; `src/asy_dns_client.py`
  resolves hostnames with its own non-blocking UDP-based resolver instead (see its own module
  docstring and BACKLOG.md). Calls that genuinely *can* be timeout-wrapped from within the asyncio
  loop — FRAM SPI transactions, `src/asy_udp_socket.py`'s own `select.poll`-driven
  `ready()`/`write_and_recvfrom(timeout_ms=..., tries=...)` — should standardize on one consistent
  timeout/cancellation mechanism; re-check any new blocking-call candidate against this same
  "does it have a coroutine boundary to attach a timeout to" question rather than assuming.
- **Don't wrap every `asyncio` primitive call (`asyncio.sleep()`, `Lock.acquire()`, etc.) in
  `try`/`except` against a theoretical internal `MemoryError` as a blanket policy** — overkill and
  outside this project's own standard. Only worth closing when a concrete, non-hypothetical threat
  exists in a specific context (a real caller-supplied value reaching an unguarded
  comparison/construct), not just "any `await` could theoretically raise."
- **Adafruit-derived driver code is fair game to restructure/rewrite** (keeping attribution) —
  unlike `python/CommonDrivers/microdot.py`/`ext/microdot.py`, which stay hands-off/vendored (see
  above).
- **Long-blocking operations must not stall timing-sensitive work.** Any new code that blocks the
  event loop for a noticeable time must not do so while timing-sensitive work like the Neopixel
  animation needs to run — either avoid the block, or coordinate so timing-sensitive code runs
  before/around it. This is a standing design principle for all new code, not tied to any one past
  case. **The `get_long_block_lock()` shared-lock mechanism itself has been retired** — its one real
  user, `socket.getaddrinfo()`, was replaced by `src/asy_dns_client.py`'s non-blocking resolver (see
  above and BACKLOG.md), so there is no longer a long-blocking network call in this codebase to
  coordinate against Neopixel timing in the first place. `asy_ntp_client.py`/`src/asy_neopixel_driver.py`/
  `src/asy_notification_service.py` (the promoted split of the former `neopixel_signal.py` - see
  below) no longer reference the lock at all. If new code reintroduces a genuinely long blocking call, a
  coordination mechanism would need to be designed fresh — don't assume the old lock still exists or
  try to resurrect/reuse it.

## Working agreements

- Long-term goal: fully understand the current (production) system in detail, then check what's
  already been addressed/transferred well into `improved-quality/`. The refactor should end up
  with the *same top-level features*, just more consistent/stable — not a feature change.
- When a fact in this file or BACKLOG.md turns out to be stale (version drift, changed upstream
  API, etc.), update the doc in the same session rather than silently working around the
  discrepancy.
- **Documentation contains current state, future targets, and rules/agreements — not the historic
  path that got there.** BACKLOG.md is active working memory (open questions, deferred work,
  in-flux decisions), not an append-only log of bugs found and fixed in already-shipped, tested
  code; once an item is resolved, it comes out, migrated to CLAUDE.md/README.md if it's a
  permanent fact worth keeping, or simply dropped if it was process narrative with no forward
  value. This already had to be corrected once (a merge re-accumulated ~800 lines of per-file
  "bug found, fixed" narrative in BACKLOG.md) — treat pruning history back out as routine
  maintenance whenever an item resolves, not a one-off cleanup.
- Prefer flagging genuinely ambiguous/architecturally significant decisions to the project owner
  over guessing — several open questions in BACKLOG.md exist precisely because the code's actual
  intent wasn't obvious from reading it alone.
- When changing a sensor driver's behavior, verify against the legacy driver's own actually-proven
  field behavior, not just judged correct against internal code-review logic in isolation.

## Code quality tooling

- **Config lives in root `pyproject.toml`** (ruff/mypy/pytest/uv, dev-tooling only — the shipped
  code stays frozen-bytecode-only, not restructured into an installable package). Run manually via
  `scripts/lint.sh` (ruff), `scripts/typecheck.sh` (mypy), and `scripts/test.sh` (unit tests, under
  a real MicroPython Unix-port interpreter — see below and `tests/README.md`); `lint.sh`/
  `typecheck.sh` assume `ruff`/`mypy` are already on `PATH` (e.g. an activated `uv sync`-created
  venv). **Wired into CI** via `.github/workflows/ci.yml` (GitHub Actions), running all three on
  every push/PR. The CI pipeline does not yet include a real firmware-build stage (see
  BACKLOG.md).
- **Scope is `improved-quality/`, `src/`, and `tests/`, for now.** The pre-refactor deployed
  codebase (`python/`, `modules/`) has no lint/type config yet; extending scope there is a separate
  future decision, not assumed by this setup.
- **Unit tests run under a real MicroPython Unix-port interpreter, not pytest/CPython** — "as close
  to the real environment as possible" means the actual runtime, not CPython plus MicroPython-
  flavored stubs (see `tests/README.md`'s "Why not pytest"). `scripts/test.sh` builds that
  interpreter on first run (`toolchain/setup_toolchain.py`'s `setup` — building/verifying the
  Unix port is just part of what `setup`/`test` already do, there's no separate `unix`
  subcommand — cached under `$PICO_TOOLCHAIN_DIR`) and shells out to it once per `tests/test_*.py`
  file; see `tests/README.md` for the full rationale and the minimal `test_*`-function runner
  (`tests/microtest.py`) used in place of CPython's `unittest`.
- **`scripts/test.sh --coverage` reports `src/` line coverage; it never gates anything** — no
  threshold is enforced anywhere, by design (confirmed directly, not a placeholder for a future
  gate). Since `coverage.py` only runs under CPython while `src/` only ever runs
  under the real MicroPython Unix-port interpreter, collection (`tests/_coverage_runner.py`,
  `sys.settrace` inside MicroPython) and rendering (`scripts/_render_coverage.py`, a second
  self-contained `uv run` script, under CPython) are two separate stages glued together through
  `coverage.py`'s own `CoverageData` API — see `tests/README.md`'s "Coverage" section for the full
  pipeline. The Unix port binary is always built with `MICROPY_PY_SYS_SETTRACE=1`
  (`build_unix_port()` in `toolchain/setup_toolchain.py`) — an inert hook check when unused, not a
  behavior change, confirmed directly — so plain `scripts/test.sh` and `--coverage` share one
  binary; `ports/rp2`'s firmware build never gets this flag. CI
  (`.github/workflows/ci.yml`) runs it as a non-gating step: a markdown summary goes to that run's
  GitHub Actions Job Summary (not the repo's main page), the HTML report is a downloadable build
  artifact (GitHub doesn't render it inline), and the Cobertura XML uploads to Codecov — which
  needs this repo registered at codecov.io plus a token/OIDC setup that hasn't happened yet, so
  that upload currently no-ops. Locally, `--coverage` only prints the output paths; nothing opens
  automatically. See README.md's "Test coverage" section for the full user-facing rundown.
- **CI hang investigation (resolved)**: `unit-tests` hung intermittently and repeatedly, always the
  same symptom — `test_asy_uart_driver.py`'s MicroPython process going completely silent for the
  rest of the job (first seen as a full 6-hour stall before `timeout-minutes` existed; see PR
  #24/#25's history). An early round of isolation (bisect-matrix runs, solo vs. concurrent-job-burst
  comparisons) pointed at GitHub Actions runner-level contention and produced three successive
  mitigations in `scripts/test.sh`/`ci.yml` (per-file `timeout`+retry, `stdbuf -oL -eL` line
  buffering, `needs: lint-and-typecheck` job sequencing) — **none of which actually stopped the
  hang**; they only turned a silent multi-hour stall into a fast, attributable ~12-13 minute
  failure. The real root cause, found by adding a diagnostic `asyncio.wait_for(5)` bound around
  the test file's own `run()` helper: ~17 tests in `test_asy_uart_driver.py` feed data via
  `feed_rx()` then call `uart.read()`/`write()` with no explicit `timeout_ms`, hitting
  `asy_uart_driver.py`'s `ready()`'s `timeout_ms=-1` (wait forever) branch — the only place in the
  whole file relying on the *real* `select.poll()` to detect readiness via `tests/machine.py`'s
  pure-Python `io.IOBase` fake UART's `ioctl()`, instead of the bounded `_StepPoller` test double
  every other test in the file already used. On GitHub Actions specifically (never locally, including
  under simulated single-core CPU contention), that real-poll/ioctl-on-a-non-fd-Python-object path
  never detects readiness at all — confirmed deterministic, not intermittent, once the diagnostic
  bound made the failure visible as `TimeoutError` instead of a silent stall. **Fix**: switched all
  17 tests to the same `_StepPoller` double, removing the dependency entirely — verified with 21/21
  clean CI jobs across three separate branches/configurations before landing on the real branch.
  The three earlier mitigations (per-file timeout/retry, stdbuf, job sequencing) are kept as a
  standing "hanging is never allowed" backstop against any *future* hang, not because they fixed
  this one — an isolation test with all three reverted, running only the `_StepPoller` fix, passed
  8/8 clean CI jobs on its own. Don't re-diagnose this specific symptom as a new code bug if it
  recurs elsewhere; do treat any *new* file/test that leaves `uart.poller` (or an equivalent
  fake-stream object) wired to a real `select.poll()` as a like-for-like risk.
- **Non-UTC-host test failures (resolved)**: on a developer machine whose system timezone isn't
  UTC, `tests/test_ntp_fram_system_integration.py`'s
  `test_fram_write_into_gets_a_real_valid_timestamp_once_the_real_ntp_chain_is_synced` and
  `test_system_service_boot_signature_resolves_via_the_real_ntp_chain_once_synced` failed every
  run (deterministic, not flaky) with a bare `AssertionError` at their final `abs(... -
  int(time.time())) < 5` line, while CI (GitHub-hosted `ubuntu-latest`, always UTC) stayed green.
  Root cause, confirmed directly against both the real MicroPython v1.28.0 Unix-port source and a
  live reproduction: the Unix port's `time.mktime()` (`ports/unix/modtime.c`) calls straight
  through to the host's real libc `mktime()`, which — per POSIX, and unlike the deployed rp2
  firmware — interprets its input `struct tm` as **local time** and converts using the process's
  `$TZ`. `src/asy_fram_manager.py`'s and `src/system_service.py`'s (and every other driver's)
  `time.mktime(time.gmtime())` idiom for "current UTC timestamp" is therefore only a true no-op
  round trip under `TZ=UTC`; under e.g. `TZ=Europe/Berlin` it silently comes back ~1 hour off
  (`tm_isdst` is forced to `0` by `gmtime()`'s 9-tuple, so it's standard-time offset, not the
  actual current DST offset), reproduced identically both with a hand-rolled snippet and by
  literally re-running the two failing tests with only `$TZ` changed (12/12 pass under `TZ=UTC`,
  the same 2/12 fail under `TZ=Europe/Berlin`, same line numbers, same "10/12 passed"). **Not a
  production bug**: confirmed directly from `ports/rp2/datetime_patch.c` that the deployed
  firmware overrides libc's `mktime()`/`localtime_r()` with `shared/timeutils`' pure, TZ-agnostic
  epoch arithmetic — real hardware has no `$TZ` concept and this idiom round-trips exactly there
  regardless. **Fix**: `scripts/test.sh` now does `export TZ=UTC` before invoking the Unix-port
  binary (for both the plain and `--coverage` passes, and every test file), pinning every local
  test run to the same UTC behavior GitHub's runners already gave for free — verified with a full
  99/99-passing `scripts/test.sh` run under `TZ=Europe/Berlin` in the calling shell after the fix.
  Don't re-diagnose a consistent (not intermittent) failure isolated to this file's two live-clock
  assertions as a new code bug — check the runner's `$TZ` first.
- **`ruff format` is deliberately not used anywhere** — line breaks are hand-chosen throughout this
  codebase; `line-length = 320` (ruff's own ceiling) plus an `E501` ignore keep this a non-issue even
  if `format` is ever run by accident. Lint rule selection (`E`/`F`/`W`/`I`/`UP`/`B`) is stricter
  than ruff's default but well short of enabling everything.
- **Bare `except:` (E722) is intentionally left enabled**, unlike the old `improved-quality/pycheck.sh`
  — the project owner wants ruff to flag existing bare excepts as a tracked to-do, not silence them
  before they're fixed (test-driven-development framing, confirmed directly).
- **Union type annotations: always PEP 604 `X | Y` (and `X | None`), never `typing.Union[...]`.**
  Confirmed safe at runtime on both the deployed 1.26 pin and the refactor's 1.28.0 target by
  testing directly against the pinned Unix-port interpreter (`int | None` in an unquoted, executed
  annotation works with no import needed) — MicroPython parses but never evaluates annotation
  expressions at all, so this isn't even a runtime-support question, just a style one. `typing.Union`
  needs `from typing import Union`, which isn't guarded by `TYPE_CHECKING` in every file that still
  uses it and would raise `ImportError` on-device if actually reached at runtime — one more reason
  `|` is strictly better here, not just newer. This is already machine-enforced: ruff's `UP007` rule
  (part of the enabled `UP` selection) flags every `Union[...]` as a finding. `src/` and `tests/`
  are already 100% `|`-style with zero `Union[...]` occurrences. The `Union[...]` usages that do
  exist today are confined to `python/` (deployed, frozen, no lint config at all) and pre-existing
  `improved-quality/` WIP files (in ruff's checked scope, already showing up as tracked `UP007`
  findings in the lint baseline) — leave those alone under the usual out-of-scope-editing hard rule;
  don't drive-by "fix" `Union` → `|` in a file you're not otherwise promoting/refactoring.
- **mypy is stricter than default, short of `--strict`** (`disallow_untyped_defs`,
  `check_untyped_defs`, `warn_return_any`, `warn_unreachable`, `strict_equality`, etc., but not
  `disallow_any_generics`/`disallow_untyped_calls`/`disallow_subclassing_any`). Does **not** disable
  the `assignment` error code — the old `improved-quality/mypy.ini` did, though that was never a
  deliberate choice.
- **MicroPython stubs**: `micropython-rp2-rpi_pico_w-stubs` (PyPI, board/version-specific, pulls in
  `micropython-stdlib-stubs`). Published by the same project as
  [`josverl/micropython-stubs`](https://github.com/josverl/micropython-stubs) — PyPI is just its
  distribution channel, not a separate/alternative stub source. **Version is auto-derived, not a
  separate hand-kept pin**: `scripts/typecheck.sh` reads `toolchain/versions.toml`'s
  `[micropython] ref` (the single source of truth for the firmware version target) and installs
  the matching `<major>.<minor>.<patch>.*` stub release, failing with a clear, actionable error
  (not a silent fallback) if `ref` isn't a plain `vX.Y.Z` tag or no matching stub release exists
  upstream yet (stub releases can lag a new MicroPython release). Installed into `typings/`
  (gitignored) — **deliberately not** a
  `pyproject.toml` `[dependency-groups]` entry, because these stubs must fully replace mypy's
  typeshed for MicroPython/CPython stdlib-name collisions (`time`, `math`, `select`, `errno`, ...
  — see `[tool.mypy]`'s `custom_typeshed_dir`), and doing that against the same venv that also
  holds mypy/ruff/pytest's own dependencies breaks type-checking of those. Keep this isolation if
  you touch the stub setup — it's load-bearing, not incidental, confirmed by testing the collision
  directly in-session.
- **`scripts/typecheck.sh`'s combined `mypy src tests` run resolves every `from machine import X`
  project-wide to `tests/machine.py`'s fake module, not the real `typings/machine.pyi` board stub**
  — confirmed directly by running `mypy src` alone (no `tests` in scope): the real stub's `Timer`
  class has no zero-argument constructor overload (every overload requires a positional `id: int`
  first argument) and doesn't declare `I2C.deinit()` at all, so an `src`-only run raises 13 errors
  across `asy_ntp_client.py`/`asy_sgp40_driver.py`/`asy_scd30_driver.py`/`asy_bmp3xx_driver.py`
  (bare `Timer()` construction) and `asy_i2c_driver.py` (`self._i2c.deinit()`) that never surface in
  the actual, documented `mypy src tests` invocation. Both are real, working MicroPython patterns
  (bare `Timer()` allocate-now/`init()`-later is valid runtime usage; `I2C.deinit()` releases the
  peripheral's pins) — this is a **gap in the third-party `micropython-rp2-rpi_pico_w-stubs`
  package**, not a bug in any promoted driver, and `tests/machine.py`'s fake happens to model both
  correctly. Net effect: harmless today, but worth knowing that the real board stub's coverage is
  incomplete for these two APIs specifically if a future `src`-only or `--strict`-adjacent
  type-check run is ever added.
- **`improved-quality/microdot.py` no longer exists** — it was a confirmed *unintentional* fork of
  vendored Microdot, removed and replaced with a fresh, unmodified sync at `ext/microdot.py`
  (pinned to tag `v2.6.2`; see "Hard rules" above and "Microdot / REST layer" below).
  `pyproject.toml`'s `extend-exclude`/`exclude` entries still reference the old
  `improved-quality/microdot.py` path — now dead/inert (matches nothing), not a functional problem
  since ruff/mypy were never pointed at `ext/` in the first place (`scripts/lint.sh` passes explicit
  `improved-quality src tests` paths, and mypy's `files` list is exactly those three directories —
  `ext/` was never in scope and needs no exclude entry of its own), but worth tidying up as cheap
  doc/config hygiene next time `pyproject.toml` is touched (see BACKLOG.md).

## Pre-push verification (clean Ubuntu 24.04)

**Before pushing any change to `pyproject.toml`, `scripts/`, `toolchain/versions.toml`, or
anything else touching the dev-tooling/build-environment setup**, verify it end-to-end inside a
genuinely clean Ubuntu 24.04 environment — not just in whatever sandbox this session happens to
be running in. A session sandbox typically already has Python 3.11+, `uv`, build tools, etc.
pre-installed, which can mask real gaps. **This already caught a real bug once**: a
`requires-python = ">=3.10"` that let `uv sync` build a venv without `tomllib` (stdlib only since
3.11), invisible in a sandbox whose default Python happened to already be 3.11+, and only found by
actually testing under a 3.10 interpreter. Treat this as a standing QA step, not a one-off — don't
skip it just because "it worked in this session's sandbox."

**Recipe** (needs root; mirrors how `toolchain/setup_toolchain.py`'s own "verified from scratch"
claims were checked — see `toolchain/README.md`'s "Evidence this actually works"):

```bash
# One-time: build a clean Ubuntu 24.04 (noble) chroot with nothing preinstalled beyond the
# minimal base - matching the OS the project's docs actually target, not this session's sandbox.
apt-get install -y debootstrap
CHROOT=/tmp/noble-chroot   # anywhere with a few hundred MB free; not part of this repo
debootstrap --variant=minbase noble "$CHROOT" http://archive.ubuntu.com/ubuntu

# Enable universe (off by default under debootstrap, on by default on every real Ubuntu ISO - see
# "Platform target" above) and wire up DNS + the usual chroot bind mounts.
cat > "$CHROOT/etc/apt/sources.list" <<'EOF'
deb http://archive.ubuntu.com/ubuntu noble main universe
deb http://archive.ubuntu.com/ubuntu noble-updates main universe
deb http://security.ubuntu.com/ubuntu noble-security main universe
EOF
cp /etc/resolv.conf "$CHROOT/etc/resolv.conf"
mount --bind /proc "$CHROOT/proc"; mount --bind /sys "$CHROOT/sys"
mount --bind /dev "$CHROOT/dev"; mount --bind /dev/pts "$CHROOT/dev/pts"

# This session's outbound HTTPS goes through a local policy proxy (see /root/.ccr/README.md if
# present) - the chroot shares the host's network namespace, so it just needs the same env
# vars/CA bundle passed through. Skip this block entirely on a plain machine with direct internet
# access (e.g. the project owner's own dev box).
if [ -f /root/.ccr/ca-bundle.crt ]; then
    mkdir -p "$CHROOT/root/.ccr"
    cp /root/.ccr/ca-bundle.crt "$CHROOT/root/.ccr/ca-bundle.crt"
    cat > "$CHROOT/root/proxy-env.sh" <<EOF
export HTTPS_PROXY="$HTTPS_PROXY" https_proxy="$HTTPS_PROXY"
export NO_PROXY="$NO_PROXY" no_proxy="$NO_PROXY"
export SSL_CERT_FILE=/root/.ccr/ca-bundle.crt CURL_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export GIT_SSL_CAINFO=/root/.ccr/ca-bundle.crt REQUESTS_CA_BUNDLE=/root/.ccr/ca-bundle.crt
export PIP_CERT=/root/.ccr/ca-bundle.crt
export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive
EOF
    # astral.sh (the official `uv` installer's domain) is blocked by this session's egress
    # policy - use `pip install uv` (README's documented alternative) instead of the curl
    # installer when testing inside this specific sandbox.
else
    echo 'export LANG=C.UTF-8 LC_ALL=C.UTF-8 DEBIAN_FRONTEND=noninteractive' > "$CHROOT/root/proxy-env.sh"
fi

chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates python3 python3-venv python3-pip sudo"
chroot "$CHROOT" /bin/bash -c "source /root/proxy-env.sh && pip install --break-system-packages uv"
# sudo is not part of debootstrap --variant=minbase, but toolchain/setup_toolchain.py's
# ensure_apt_packages() unconditionally shells out to it (see toolchain/versions.toml's
# apt_packages, used by both its `setup`/`test` subcommands) - without it, `scripts/test.sh`
# fails with "sudo: command not found" even though a real dev machine (where the calling user has
# sudo rights but isn't already root) never hits this. A plain chroot session runs as root, where
# apt-get wouldn't need sudo at all, but the script always prepends it regardless - so installing
# the package is the correct fix here, not stripping sudo from the script for a root-only case.

# Per-verification: copy the CURRENT working tree (uncommitted changes included - this is a
# pre-push gate, not a post-push audit) into the chroot, then run the exact documented workflow
# from README.md's "Code quality tooling" section.
rm -rf "$CHROOT/root/sensors"
cp -r /path/to/this/repo/checkout "$CHROOT/root/sensors"   # adjust to wherever it's actually checked out
chroot "$CHROOT" /bin/bash -c "
  source /root/proxy-env.sh
  cd /root/sensors
  rm -rf .venv typings   # don't carry over host-built artifacts
  uv sync
  source .venv/bin/activate
  scripts/lint.sh
  scripts/typecheck.sh
  scripts/test.sh   # builds the MicroPython Unix port from scratch inside the chroot (no cached
                     # ~/pico-toolchain carried over) - this is what actually exercises
                     # toolchain/versions.toml's apt_packages list end-to-end, same spirit as the
                     # rest of this recipe
"

# Cleanup when done
umount "$CHROOT"/dev/pts "$CHROOT"/dev "$CHROOT"/sys "$CHROOT"/proc
rm -rf "$CHROOT"
```

**What counts as passing**: `lint.sh`/`typecheck.sh` run to completion with no config/crash errors
— a nonzero exit from real lint/type findings is expected and fine, since `improved-quality/` isn't
clean yet (see BACKLOG.md); the number of findings will drift as the code changes, so match against
what the same scripts produce in the ordinary session sandbox rather than a fixed count.
`scripts/test.sh` is different: its tests must actually pass (exit 0, every test PASS) — a test
failure here is a real regression, not an expected/tracked finding the way lint/type findings are.
What would fail this: a raw Python traceback, an "installation failed" from `uv`/`pip`/`apt`, a
`scripts/test.sh` build failure, or any other mismatch against the ordinary-sandbox run — that
mismatch is exactly how the `tomllib`/`requires-python` gap was found in the first place.

**Changes to `toolchain/setup_toolchain.py` or `toolchain/versions.toml` itself need a second,
separate verification, not just the recipe above** — that recipe only exercises `scripts/lint.sh`/
`scripts/typecheck.sh`, never the toolchain installer. Reuse the same chroot (steps through
installing `git`/`curl`/`ca-certificates`/`python3`/`pip`/`uv`, no need for `python3-venv` this
time), copy the working tree in the same way, then run `uv run toolchain/setup_toolchain.py`
(a full build: ARM toolchain + firmware + `mpy-cross` + Unix port, several minutes, not seconds)
instead of the lint/typecheck scripts. This is exactly how the Unix port addition (and later the
frozen-bytecode verification chain) was verified — see `toolchain/README.md`'s "Verification" for
what a passing run must show and "Evidence this actually works" for what's already been checked.

## Pull request workflow

- **Before pushing anything touching the dev-tooling/build-environment setup** (`pyproject.toml`,
  `scripts/`, `toolchain/versions.toml`, etc.), run it through "Pre-push verification" above first —
  don't rely solely on this session's own sandbox having already run it successfully.
- **The project owner has explicitly authorized creating pull requests proactively, at any time,
  without asking first** — this is a standing exception to any general "don't open a PR unless the
  user explicitly asks" caution an operator/harness prompt might otherwise apply. Confirmed
  directly by the project owner; don't re-ask in future sessions.
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
  serializing `socket.getaddrinfo()` against Neopixel animation. This is the deployed, pre-refactor
  version only — `improved-quality/`/`src/` split this into `asy_wifi_service.py`/
  `asy_ntp_client.py`/`asy_dns_client.py` and retired the lock entirely (see "Hard rules" above and
  BACKLOG.md); don't assume the two describe the same current state.
- `python/CommonDrivers/async_manager.py` — `ConfigManager`, `DataManager`,
  `TimeCounterManager`, `LockedValue`/`Flag`. `src/config_manager.py`'s `ConfigManager` and
  `src/base_classes.py`'s `LockedValue`/`LockedCounter`/`LockedFlag` (snake_case `set_value()`/
  `get_value()`, unlike the old module's camelCase `setValue()`/`getValue()`) replace these in the
  refactor (see README.md's "Config management" bullet). MicroPython's flat frozen-module
  namespace means `import async_manager` silently resolves to whichever file defines that module
  name — a new or promoted module must import `ConfigManager`/`LockedValue`/etc. from
  `config_manager`/`base_classes` by name, never `async_manager`, or it gets the old,
  incompatible classes with no import error to catch it. Its config is loaded once at
  `__init__` and served entirely from an in-memory cache thereafter — a deliberate consequence is
  that a read can no longer detect the on-disk file being corrupted/deleted out-of-band after a
  valid `__init__`; the cache is the sole source of truth, and a later `write_config()` silently
  *repairs* an externally-corrupted file from it. Accepted given this device is the file's only
  writer. **Every module with user-settable configuration owns its own schema/config file** — a
  global project convention, not limited to sensor drivers; `asy_wifi_service.py`,
  `asy_ntp_client.py`, and `src/asy_notification_service.py`'s `NotificationCoordinator` each follow
  it the same way every sensor `*_Reader` does, replacing the single ad hoc top-level `ConfigManager`
  grab-bag the deployed codebase still uses. (`src/asy_neopixel_driver.py`'s `NeopixelDriver` is the
  one deliberate exception - no config schema at all, confirmed by the project owner; see its own
  entry below.) A module whose own REST/caller layer needs to call `write_config()` directly against its
  `cfgmgr` exposes the schema via a public `self.cfg_schema` attribute (see
  `asy_wifi_service.py`/`asy_ntp_client.py`) rather than the caller reaching into a private
  module-level schema constant — `base_classes.py`'s `SensorReaderConfig` doesn't provide this
  itself, so any new module needing it adds the attribute the same way.
- `python/IndividualDrivers/asy_fram_driver.py` / `asy_fram_manager.py` — raw SPI FRAM driver +
  chunk allocator with dual-copy redundancy (arzi/neu/wozi only, not dev). `src/`'s promoted
  versions keep the same design: each chunk stores two redundant copies plus a busy/idle status
  byte guarding both reads and writes (MB85RS64V reads are destructively read internally, so a
  power loss mid-read is as real a risk as mid-write); "both copies valid but different" is a hard
  failure (no generation counter to say which is newer), never silently guessed.
  `AsyFramTimestampedChunk.write()`/`write_into()` return `(ntp_synced, utc, success)` — `success`
  is the *third* element, not first, unlike every other bool-returning method in this codebase;
  don't reorder it, callers already unpack it this way. `AsyFramManager` is a bump-pointer
  allocator: `get_chunk()`/`get_timestamped_chunk()` carve out fixed offsets in call order, so a
  device's *instantiation order* of these calls is its on-chip layout and must stay identical
  across firmware versions for existing stored data to keep decoding correctly.
- **SCD30's `AmbPres` (ambient-pressure compensation) is stored in the sensor's own internal
  non-volatile memory as a one-time-set value, not a continuously-updated live input.** This is why
  it's a static config value on every unit — including wozi, which has a live BMP388 — and why
  `set_ambient_pressure` is called with `force=True` in the REST handler: resending the same value
  is also the SCD30's documented command to resume continuous measurement after it's been stopped.
  Don't "fix" this into a live BMP388→SCD30 feed; it's intentional, confirmed by the project owner.
- **`improved-quality/neopixel_signal.py` (LED hardware control + hardcoded CO2/VOC/Humidity
  threshold monitoring combined in one file) is promoted and split into two `src/` files** - the old
  file is deleted, `improved-quality/sensortask-wozi.py` wires the two replacements directly.
  - `src/asy_neopixel_driver.py`'s `NeopixelDriver` — pure LED hardware service: overlay
    switch/toggle, the dimmed ramp-up/ramp-down signal, and the internal/external
    (`request_signal()`/`led_signal()`) arbitration for the one shared physical pixel, unchanged
    from the original file's proven mechanism (`request_signal()` returns once a request is queued,
    not once its ramp finishes — preserve this exact contract if touching this file again). No
    config schema at all (confirmed by the project owner) and no namedtuple/measurement data, so it
    doesn't extend `SensorReaderConfig` — the one exception to this codebase's own `_NAME`/namedtuple
    pairing convention (see DRIVER_SPEC.md section 2). Also serves `asy_wifi_service.py`'s
    `LEDControl` Protocol (`ext_led=`) unchanged.
  - `src/asy_notification_service.py`'s `NotificationSignal` (a plain, dependency-free per-condition
    data holder) + `NotificationCoordinator(SensorReaderConfig)` (generic threshold-triggered
    signalling, replacing the old file's hardcoded three-condition logic) — owns sleep-window/
    interval/`AutoOn`/global `FlashBri`/`FlashDur`, the override/pause countdown, one combined
    `ConfigManager`, and one combined `PrintLogHistory`(Store) covering its own fields plus every
    registered `NotificationSignal`'s threshold field. **Staged registration, deferred
    construction**: `__init__()` only stashes constructor args; `register()` (sync) accepts
    `NotificationSignal`s in check-order; `finalize()` (sync, exactly once) builds the combined
    schema and is the single point `self.pr`/`self.cfgmgr` actually come into existence, via a
    delayed `super().__init__()` call — the whole mechanism achieved with zero changes to
    `ConfigManager`/`PrintLogHistory`(Store)/`base_classes.py` themselves, relying on the guarantee
    that the number/order of registered signals stays constant once `finalize()` has run (a one-time
    boot handshake). `register()`/`finalize()` are sync but can't call the async `self.pr.wrn_s()`
    directly (and `self.pr` may not exist yet pre-`finalize()`) — rejections are buffered and
    drained by `monitor_loop()` each cycle instead. `NotificationSignal.color` is a per-channel
    weight (0/1), not an absolute color — scaled by the shared `FlashBri` at trigger time, which is
    what makes one global brightness setting actually apply to every registered condition.
  - Config field names drop the "Led" prefix everywhere (`WarnCO2` not `LedWarnCO2`) — a deliberate
    wire-format change; the (already known-brittle, deferred — see BACKLOG.md) frontend isn't
    updated to match yet.
- In the deployed, pre-refactor codebase (`modules/sensortask-*.py`), the task supervisor is a
  hand-rolled loop inside each file's `main()`, not a shared module — duplicated per device file.
  `improved-quality/sensortask-wozi.py` no longer matches this: its `main()` now calls
  `system_service.py`'s real `start_and_check_tasks()`/`start_timers()` instead of reimplementing
  the loop. Don't assume the two describe the same current state.
- **Functional behaviors confirmed intentional by the project owner, not obvious from the code
  alone — don't "fix" any of these:**
  - Air-quality warning LED sequencing (one color per condition, paused between flashes rather than
    combined) is exactly as designed.
  - FRAM SGP40 backup "0 = disabled" semantics: `SGPBackupPeriod=0` disables periodic backup
    writes, `SGPBackupMaxAge=0` disables the staleness check (currently undocumented user-facing —
    see BACKLOG.md).
  - Permanent WiFi deactivation after a second STA failure streak (post-hotspot) is a deliberate
    safety feature, preventing an unclaimed hotspot from staying open indefinitely — a physical
    power-cycle is the accepted recovery path.
  - STA never automatically falls back to hotspot mode again once it has connected successfully
    even once in a task's lifetime — only a human resubmitting WiFi credentials over the REST API,
    or a full task restart, resets this. Confirmed deliberate for physically-accessible, easy-to-
    power-cycle devices, not an oversight — don't add an automatic repeat-fallback path.
  - The web UI intentionally shows raw sensor numbers only, no color-coding — the physical LED is
    the sufficient at-a-glance indicator.
  - SGP40 silently falling back to uncompensated VOC readings when SCD30 is down/stale, with no
    distinct "degraded" signal, is acceptable as-is — SCD30's own error counter already surfaces
    the cause.
  - FRAM's 8KB allocation has plenty of headroom over SGP40's current ~250-byte usage for future
    FRAM-backed features.
  - `asy_uart_driver.py` intentionally does not expose hardware flow control (`rts`/`cts`/`flow`) —
    confirmed directly, not planned for the future either. Not a gap to revisit unprompted.
  - SCD30's `get_ambient_pressure()` read-back reuses the same command word used to *set* it —
    matches every sibling getter's pattern and the legacy driver's own proven field behavior, even
    though neither Sensirion's `embedded-scd` reference driver nor their `python-i2c-scd30` driver
    documents that command as readable (their worked examples only show a write path for it). No
    alternate documented read-back path exists to switch to regardless. Leave as-is.

## Microdot / REST layer

`ext/microdot.py` is vendored, unmodified upstream Microdot (currently pinned to tag `v2.6.2` — see
"Hard rules" for the vendoring policy: it's treated as a plain external resource, no edits, no
"cleanup" of its style). The facts below were confirmed by reading its actual source directly
(`Microdot.dispatch_request()`/`handle_request()`/`Response.write()`/`Request.json` in
`ext/microdot.py`), not assumed from Microdot's docs or training memory — treat this section as the
standing reference for how much stability Microdot already gives us for free versus what our own
REST layer still has to add.

- **Every exception raised by our own code inside a route handler — including a before/after-request
  hook, and including `MemoryError` — is already caught by Microdot itself, per request, and can
  never crash the server.** `dispatch_request()` wraps the whole handler chain (before-request
  hooks → route handler → response coercion, which includes `json.dumps()` of a returned dict/list
  → after-request hooks) in one `except HTTPException` / `except Exception`. An `HTTPException`
  (from `abort()`) resolves by **numeric status code** through `self.error_handlers`; any other
  exception resolves by **exact exception class**, then by walking the class's MRO — so a single
  `@app.errorhandler(Exception)` registration is reachable as a catch-all fallback from any
  exception subtype, without needing one registration per exception type. With no handler
  registered at all (today's state, in both `improved-quality/sensortask-wozi.py` and the deployed
  `python/CommonDrivers/microdot.py` app — confirmed, neither registers any `errorhandler`),
  Microdot's own bare default response is used (`'Internal server error', 500`, or `'Not found',
  404`, etc.) — safe, but not one of our own reply shapes.
- **The one place this blanket catch does *not* cover: exceptions raised while writing the response
  itself.** `Response.write()` (and the `handle_request()` code that calls it) only catches
  `OSError`, and only mutes a short allow-list of expected socket errors (broken pipe, connection
  reset, write to an already-closed socket — `MUTED_SOCKET_ERRORS`); anything else — a non-`OSError`
  from a streamed body's `.read()`/generator, or an unmuted `OSError` — propagates all the way out of
  the per-connection handler coroutine uncaught. This is the one genuine "a reply may not be
  possible" case: by the time this code runs, the response is already (partially) in flight, so
  there is no remaining hook to convert the failure into a REST reply — the client runs into a
  timeout instead, exactly as expected/accepted.
- Microdot's own exception logging (`print_exception(exc)`, a bare MicroPython traceback dump) is
  **not** wired into this project's own `PrintLog`/FRAM-backed logging in any way. Anything caught
  by Microdot's blanket per-request catch that we want reflected in our own error counters/history
  has to come from an `@app.errorhandler` we register ourselves calling into `pr.err_s(...)` (or
  equivalent) — Microdot's default handling alone leaves no trace anywhere a deployed, headless unit
  can be expected to surface.
- `Request.json` has no internal guarding at all (`json.loads(self.body.decode())`, no try/except) —
  a malformed body or bad encoding raises straight out of the property access. Given the point
  above, this is already contained by Microdot's own blanket catch either way; guarding it ourselves
  (as `cmd_pre_check` already does, legacy and WIP alike) is about producing a precise, on-brand
  error reply instead of a generic 500, not about crash prevention.
- Request size is already bounded by Microdot itself before any handler runs:
  `Request.max_content_length` (16KB default) → 413 for an oversized body,
  `Request.max_readline` (2KB default) → guards a single request/header line. This project's JSON
  payloads are tiny; the defaults are already generous headroom on a 264KB-SRAM target, no override
  needed — just worth knowing the guard already exists rather than re-adding one at our own layer.
- The Microdot server task is already wired into `system_service.py`'s generic
  `start_and_check_tasks()` supervisor exactly like every other sensor task (see
  `improved-quality/sensortask-wozi.py`'s `main()`: `start_asy_webserver()` is one of the plain
  `task_starters`). A Microdot task that terminates — by returning or by an exception escaping it —
  is detected the same way any other dead task is (`task.done()`) and restarted automatically, with
  the same decaying failure counter and eventual full-reboot fallback as any other task.
  **"Restart Microdot if it crashes" is therefore already implemented generically — it does not need
  Microdot-specific supervisor code —** provided the failure actually terminates that task rather
  than being silently contained at a level the supervisor never observes (see BACKLOG.md for the
  still-open question of exactly what "crashes" means at the per-connection level on MicroPython's
  `asyncio`).
- **Each accepted connection runs in its own independent `asyncio.Task`** (confirmed against
  `extmod/asyncio/stream.py`'s `Server._serve()`, which calls `core.create_task(cb(s2s, s2s))` per
  accepted connection — the same isolation CPython's `asyncio.start_server()` gives). Combined with
  the blanket per-request catch above, the one confirmed gap (a non-`OSError` escaping
  `Response.write()`/`handle_request()`) only ever takes down that one client's connection Task —
  the rest of the Microdot server, including its accept loop, keeps running unaffected. "Microdot
  restarts itself when it crashes" (the task-supervisor point above) stays a backstop for a fully-
  dead server task, not something made load-bearing by this one gap.
- `errorhandler()`'s two lookup keys are independent and easy to conflate: **numeric HTTP status
  code** (`@app.errorhandler(404)`, also what `abort()`/`HTTPException` resolves through — matched
  by `exc.status_code`, never by exception class) versus **Python exception class**
  (`@app.errorhandler(SomeException)`, matched by exact class then MRO walk). Registering
  `@app.errorhandler(HTTPException)` would never fire for an `abort()` call; the status-code form is
  required for that.
- The deployed, out-of-scope `python/CommonDrivers/microdot.py` copy already implements essentially
  the same protective architecture (blanket per-request catch, exception-class + status-code error
  handlers with MRO fallback) — this safety model predates the `ext/microdot.py` v2.6.2 vendoring
  done this session, it is not a new v2.6.2-only improvement. One confirmed version-drift detail:
  the deployed copy's `HTTPException` branch invokes a registered status-code handler directly
  rather than through the async-safe `invoke_handler()` wrapper v2.6.2 uses uniformly (so a
  registered handler there would need to be a plain sync callable) — irrelevant today since neither
  app currently registers any handlers, but worth remembering if the current deployed codebase's
  REST layer is ever touched again before the refactor lands.
